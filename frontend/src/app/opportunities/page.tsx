'use client'

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'

interface Opportunity {
  id: string
  opportunity_id?: string
  title: string
  funder: string
  amount: number
  deadline: string
  match_score: number
  description: string
  requirements: string[] | any
  contact: string
  application_url: string
  created_at?: string
  saved_at?: string
  status?: string
}

interface SimilarRfp {
  id: number
  title: string
  category: string
  content: string
  similarity_score: number
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

      if (!response.ok) {
        console.error('Failed to fetch opportunities')
        setOpportunities([])
        return
      }

      const data = await response.json()
      setOpportunities(data.opportunities || [])
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
      setOpportunities([])
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (opportunityId: string, action: 'pursue' | 'assign' | 'dismiss') => {
    // Mock action for demo
    alert(`Action "${action}" on opportunity ${opportunityId}`)
    // In real implementation, would call API to update status
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
    if (score >= 85) return 'bg-green-100 text-green-800'
    if (score >= 70) return 'bg-yellow-100 text-yellow-800'
    return 'bg-gray-100 text-gray-800'
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading opportunities...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Saved Opportunities</h1>
          <p className="text-gray-600 text-lg">
            Your curated pipeline • Scored and ranked opportunities
          </p>
        </div>

        {/* Stats Bar */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-8 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Total Saved</p>
              <p className="text-3xl font-bold text-gray-900">{opportunities.length}</p>
            </div>
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Total Value</p>
              <p className="text-3xl font-bold text-perscholas-primary">
                {formatCurrency(opportunities.reduce((sum, o) => sum + (o.amount || 0), 0))}
              </p>
            </div>
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">High Match</p>
              <p className="text-3xl font-bold text-green-600">
                {opportunities.filter(o => o.match_score >= 85).length}
              </p>
            </div>
          </div>
        </div>

        {/* Opportunities List */}
        {opportunities.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md border border-gray-200 p-16 text-center">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">No saved opportunities yet</h3>
            <p className="text-gray-600 text-lg mb-8">Save grants from the dashboard to track them here</p>
            <a
              href="/dashboard"
              className="inline-block bg-gradient-to-r from-perscholas-primary to-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all"
            >
              View Dashboard
            </a>
          </div>
        ) : (
          <div className="space-y-5">
            {opportunities.map((opp) => (
              <div
                key={opp.id}
                className="bg-white rounded-xl shadow-md border border-gray-200 p-8 hover:shadow-xl hover:border-perscholas-primary/30 transition-all duration-200"
              >
                <div className="flex justify-between items-start mb-5">
                  <div className="flex-1 pr-8">
                    <div className="mb-3">
                      <h3 className="text-2xl font-bold text-gray-900 mb-2">{opp.title}</h3>
                      <p className="text-base text-gray-600 font-medium">{opp.funder}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <span className={`px-4 py-2 rounded-lg text-sm font-bold shadow-sm ${getMatchColor(opp.match_score)}`}>
                      {opp.match_score}% Match
                    </span>
                    <p className="text-3xl font-bold text-perscholas-primary">
                      {formatCurrency(opp.amount)}
                    </p>
                    <p className="text-sm text-gray-500 font-medium">
                      Due {formatDate(opp.deadline)}
                    </p>
                  </div>
                </div>

                <p className="text-gray-700 mb-5 leading-relaxed line-clamp-2">{opp.description}</p>

                {opp.requirements && Array.isArray(opp.requirements) && opp.requirements.length > 0 && (
                  <div className="mb-5 bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-semibold text-gray-700 mb-2">Key Requirements:</p>
                    <ul className="space-y-1.5">
                      {opp.requirements.slice(0, 3).map((req: string, idx: number) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-start">
                          <span className="text-perscholas-primary mr-2 mt-0.5">•</span>
                          <span>{req}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex justify-between items-center pt-5 border-t border-gray-200">
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-gray-500 font-medium">
                      Saved {formatDate(opp.saved_at || opp.created_at || '')}
                    </span>
                  </div>
                  <div className="flex space-x-3">
                    <button
                      onClick={() => handleAction(opp.id, 'dismiss')}
                      className="px-5 py-2.5 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:border-red-400 hover:bg-red-50 hover:text-red-700 transition-all text-sm font-semibold"
                    >
                      Dismiss
                    </button>
                    <button
                      onClick={() => handleAction(opp.id, 'assign')}
                      className="px-5 py-2.5 bg-white border-2 border-perscholas-primary text-perscholas-primary rounded-lg hover:bg-perscholas-primary hover:text-white transition-all text-sm font-semibold"
                    >
                      Assign
                    </button>
                    <button
                      onClick={() => handleAction(opp.id, 'pursue')}
                      className="px-6 py-2.5 bg-gradient-to-r from-perscholas-primary to-blue-600 text-white rounded-lg hover:shadow-lg hover:scale-105 transition-all text-sm font-semibold"
                    >
                      Pursue
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}