'use client'

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'

interface Opportunity {
  id: string
  title: string
  funder: string
  amount: number
  deadline: string
  match_score: number
  description: string
  requirements: string[]
  contact: string
  application_url: string
  created_at: string
}

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchOpportunities()
  }, [])

  const fetchOpportunities = async () => {
    try {
      const response = await api.getOpportunities()
      const data = await response.json()
      setOpportunities(data.opportunities)
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateProposal = async (opportunity: Opportunity) => {
    try {
      const response = await api.generateProposal({
        opportunity_id: opportunity.id,
        opportunity_title: opportunity.title,
        funder: opportunity.funder,
        funding_amount: opportunity.amount,
        deadline: opportunity.deadline,
        description: opportunity.description,
        requirements: opportunity.requirements
      })

      if (response.ok) {
        const data = await response.json()
        alert(`Proposal generation started! Job ID: ${data.job_id}`)
        // Could redirect to proposals page or show progress
        window.location.href = '/proposals'
      } else {
        alert('Failed to start proposal generation')
      }
    } catch (error) {
      console.error('Failed to generate proposal:', error)
      alert('Failed to generate proposal')
    }
  }

  const getMatchColor = (score: number) => {
    if (score >= 85) return 'bg-green-50 text-green-700 border border-green-200'
    if (score >= 70) return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
    return 'bg-red-50 text-red-700 border border-red-200'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Saved Opportunities</h1>
          <p className="text-gray-600">Your curated funding opportunities database</p>
        </div>

        {opportunities.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">No saved opportunities yet</h3>
            <p className="text-gray-600 mb-6">Start by running a search to discover funding opportunities</p>
            <a
              href="/"
              className="bg-perscholas-primary text-white px-6 py-3 rounded-full font-medium hover:bg-opacity-90 transition-colors"
            >
              Start Search
            </a>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold text-gray-900">
                {opportunities.length} Opportunities
              </h2>
              <button
                onClick={fetchOpportunities}
                className="text-perscholas-primary hover:text-perscholas-secondary font-medium"
              >
                Refresh
              </button>
            </div>

            <div className="grid gap-6">
              {opportunities.map((opp) => (
                <div key={opp.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-xl font-semibold text-gray-900">
                      {opp.title}
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getMatchColor(opp.match_score)}`}>
                      {opp.match_score}% fit
                    </span>
                  </div>

                  <div className="space-y-3 mb-6">
                    <div className="text-gray-600 font-medium">{opp.funder}</div>

                    <div className="flex justify-between items-center text-sm">
                      <span className="text-lg font-semibold text-gray-900">
                        ${opp.amount.toLocaleString()}
                      </span>
                      <span className="text-gray-500">
                        Deadline: {new Date(opp.deadline).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-gray-700 leading-relaxed">{opp.description}</p>

                    {opp.requirements && opp.requirements.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Requirements:</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                          {opp.requirements.map((req, idx) => (
                            <li key={idx}>{req}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-4 items-center justify-between">
                    <div className="text-sm text-gray-500">
                      Contact: {opp.contact}
                    </div>
                    <div className="flex gap-4">
                      <a
                        href={opp.application_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="border border-perscholas-primary text-perscholas-primary px-6 py-2 rounded-full text-sm font-medium hover:bg-gray-50 transition-colors"
                      >
                        Apply Now
                      </a>
                      <button
                        onClick={() => generateProposal(opp)}
                        className="bg-perscholas-primary text-white px-6 py-2 rounded-full text-sm font-medium hover:bg-opacity-90 transition-colors"
                      >
                        Generate Proposal
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 text-xs text-gray-400">
                    Saved: {new Date(opp.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}