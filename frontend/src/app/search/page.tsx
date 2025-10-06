'use client'

import { useState } from 'react'
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
}

export default function SearchPage() {
  const [isSearching, setIsSearching] = useState(false)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [searchPrompt, setSearchPrompt] = useState('')

  const saveOpportunity = async (opportunityId: string) => {
    try {
      await api.saveOpportunity(opportunityId)
      alert('Opportunity saved to database!')
    } catch (error) {
      alert('Failed to save opportunity')
    }
  }

  const searchOpportunities = async () => {
    if (!searchPrompt.trim()) {
      alert('Please enter a search prompt')
      return
    }

    setIsSearching(true)

    try {
      // Start search job
      const response = await api.searchOpportunities({ prompt: searchPrompt })

      const { job_id } = await response.json()

      // Poll for job completion
      const pollJob = async () => {
        const jobResponse = await api.getJob(job_id)
        const jobData = await jobResponse.json()

        if (jobData.status === 'completed') {
          setOpportunities(jobData.result.opportunities)
          setIsSearching(false)
        } else if (jobData.status === 'failed') {
          alert('Search failed: ' + jobData.error)
          setIsSearching(false)
        } else {
          // Still running, poll again
          setTimeout(pollJob, 2000)
        }
      }

      setTimeout(pollJob, 1000)
    } catch (error) {
      alert('Failed to start search')
      setIsSearching(false)
    }
  }

  const getMatchColor = (score: number) => {
    if (score >= 85) return 'bg-green-50 text-green-700 border border-green-200'
    if (score >= 70) return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
    return 'bg-red-50 text-red-700 border border-red-200'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">
            Intelligent Opportunity Discovery
          </h2>

          <div className="space-y-6">
            <div>
              <label htmlFor="search-prompt" className="block text-sm font-medium text-gray-700 mb-2">
                Search Prompt for Claude Code Agent
              </label>
              <textarea
                id="search-prompt"
                value={searchPrompt}
                onChange={(e) => setSearchPrompt(e.target.value)}
                placeholder="Example: Find federal grants for cybersecurity workforce development programs targeting underserved communities in urban areas, amount $100K-$500K, due within 90 days"
                className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-primary focus:border-transparent resize-none h-24"
                disabled={isSearching}
              />
              <p className="text-sm text-gray-500 mt-2">
                Be specific about focus areas, funding amounts, deadlines, and target populations for best results.
              </p>
            </div>

            <button
              onClick={searchOpportunities}
              disabled={isSearching || !searchPrompt.trim()}
              className="bg-perscholas-primary hover:bg-opacity-90 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-8 py-4 rounded-full font-medium transition-all duration-200 text-lg shadow-sm hover:shadow-md"
            >
              {isSearching ? 'Claude Code Agent Searching...' : 'Deploy AI Search Agent'}
            </button>
          </div>

          {isSearching && (
            <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center space-x-3 mb-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-perscholas-primary"></div>
                <span className="text-perscholas-primary text-lg font-medium">
                  Claude Code agent executing search strategy...
                </span>
              </div>
              <div className="space-y-2 text-sm text-gray-600">
                <div>• Connecting to GRANTS.gov and foundation databases</div>
                <div>• Applying semantic analysis for Per Scholas mission alignment</div>
                <div>• Scoring opportunities by fit, feasibility, and timeline</div>
                <div>• Generating actionable recommendations</div>
              </div>
              <div className="mt-4 text-xs text-gray-500">
                Processing time: 2-3 minutes for comprehensive analysis
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        {opportunities.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold text-gray-900">
                Discovery Results
              </h2>
              <span className="text-sm text-gray-500">
                {opportunities.length} opportunities found
              </span>
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

                  <div className="space-y-4 mb-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-gray-600 font-medium text-lg">{opp.funder}</div>
                        <div className="text-sm text-gray-500 mt-1">Grant ID: {opp.id}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-600">
                          ${opp.amount.toLocaleString()}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {opp.deadline && opp.deadline !== 'Invalid Date' ? (
                            <>Deadline: {opp.deadline}</>
                          ) : (
                            'No deadline specified'
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold text-gray-900 mb-2">Description</h4>
                      <p className="text-gray-700 leading-relaxed text-sm">{opp.description}</p>
                    </div>

                    {opp.requirements && opp.requirements.length > 0 && (
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <h4 className="font-semibold text-gray-900 mb-2">Key Requirements</h4>
                        <ul className="space-y-1 text-sm text-gray-700">
                          {opp.requirements.map((req, idx) => (
                            <li key={idx} className="flex items-start">
                              <span className="text-blue-500 mr-2">•</span>
                              {req}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {opp.contact && (
                      <div className="text-sm text-gray-600">
                        <span className="font-medium">Contact:</span> {opp.contact}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-4 flex-wrap">
                    {opp.application_url && (
                      <a
                        href={opp.application_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="border border-perscholas-primary text-perscholas-primary px-6 py-2 rounded-full text-sm font-medium hover:bg-gray-50 transition-colors"
                      >
                        View on Grants.gov ↗
                      </a>
                    )}
                    <button
                      onClick={() => saveOpportunity(opp.id)}
                      className="bg-perscholas-primary text-white px-6 py-2 rounded-full text-sm font-medium hover:bg-opacity-90 transition-colors"
                    >
                      Save to Database
                    </button>
                    <button className="border border-gray-300 text-gray-700 px-6 py-2 rounded-full text-sm font-medium hover:bg-gray-50 transition-colors">
                      Generate Proposal
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {opportunities.length === 0 && !isSearching && (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-3">
              Ready to Deploy AI Search Agent
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Enter a specific search prompt above to discover relevant funding opportunities using Claude Code's intelligent analysis.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
