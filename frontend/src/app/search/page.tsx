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
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set())

  const saveOpportunity = async (opportunityId: string) => {
    setSavingIds(prev => new Set(prev).add(opportunityId))
    try {
      await api.saveOpportunity(opportunityId)
      // Refresh opportunities after save
      setTimeout(() => {
        setSavingIds(prev => {
          const newSet = new Set(prev)
          newSet.delete(opportunityId)
          return newSet
        })
      }, 1500)
    } catch (error) {
      alert('Failed to save opportunity')
      setSavingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(opportunityId)
        return newSet
      })
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
    if (score >= 85) return { bg: 'bg-green-600', text: 'text-white', lightBg: 'bg-green-50' }
    if (score >= 70) return { bg: 'bg-yellow-500', text: 'text-white', lightBg: 'bg-yellow-50' }
    return { bg: 'bg-gray-400', text: 'text-white', lightBg: 'bg-gray-50' }
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
    if (!dateStr || dateStr === 'Invalid Date') return 'TBD'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-10">
            <div className="flex items-center gap-2 sm:gap-3 mb-3">
              <div className="bg-perscholas-secondary p-2 sm:p-2.5 rounded-xl">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                AI-Powered Opportunity Discovery
              </h2>
            </div>
            <p className="text-gray-600 text-base sm:text-lg mt-2">
              Deploy an agent to discover funding opportunities tailored to your specific needs. Be specific about focus areas, funding amounts, and deadlines for best results.
            </p>
          </div>
        </div>

        {/* Search Input Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 mb-8">
          <div className="space-y-6">
            <div>
              <label htmlFor="search-prompt" className="block text-sm font-semibold text-gray-900 mb-3">
                Search Criteria
              </label>
              <textarea
                id="search-prompt"
                value={searchPrompt}
                onChange={(e) => setSearchPrompt(e.target.value)}
                placeholder="Example: Find federal grants for cybersecurity workforce development programs targeting underserved communities in urban areas, amount $100K-$500K, due within 90 days"
                className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent resize-none h-24 text-sm"
                disabled={isSearching}
              />
              <p className="text-xs text-gray-500 mt-2">
                Tip: Include funding amount range, timeline, target populations, and specific focus areas for best results.
              </p>
            </div>

            <button
              onClick={searchOpportunities}
              disabled={isSearching || !searchPrompt.trim()}
              className="w-full bg-perscholas-secondary hover:bg-perscholas-dark disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2"
            >
              {isSearching ? (
                <>
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Agent Searching...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Deploy AI Search Agent
                </>
              )}
            </button>
          </div>

          {isSearching && (
            <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-xl">
              <div className="flex items-center space-x-3 mb-4">
                <div className="bg-perscholas-secondary p-1.5 rounded-lg flex-shrink-0">
                  <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <span className="text-perscholas-secondary font-semibold">
                  Agent executing search strategy...
                </span>
              </div>
              <div className="space-y-2 text-sm text-gray-700 ml-8">
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Connecting to GRANTS.gov and foundation databases</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Applying semantic analysis for Per Scholas mission alignment</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Scoring opportunities by fit, feasibility, and timeline</span>
                </div>
              </div>
              <div className="mt-4 text-xs text-gray-500 ml-8">
                Processing time: 2-3 minutes for comprehensive analysis
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        {opportunities.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  Discovery Results
                </h2>
                <p className="text-gray-600 text-sm mt-1">
                  {opportunities.length} opportunities discovered
                </p>
              </div>
            </div>

            <div className="space-y-6">
              {opportunities.map((opp) => {
                const colors = getMatchColor(opp.match_score)
                const isSaving = savingIds.has(opp.id)

                return (
                  <div
                    key={opp.id}
                    className="border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow duration-200"
                  >
                    {/* Header with Title and Match Score */}
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 leading-snug mb-1">
                          {opp.title}
                        </h3>
                        <p className="text-sm text-gray-600 font-medium">{opp.funder}</p>
                      </div>
                      <div className={`${colors.bg} ${colors.text} px-3.5 py-1.5 rounded-lg text-sm font-semibold flex-shrink-0 whitespace-nowrap`}>
                        {opp.match_score}% Match
                      </div>
                    </div>

                    {/* Key Metrics */}
                    <div className="grid grid-cols-3 gap-6 mb-6 pb-6 border-b border-gray-200">
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Funding Amount</span>
                        <span className="text-lg font-bold text-green-600">{formatCurrency(opp.amount)}</span>
                      </div>
                      <div className="text-center">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Deadline</span>
                        <span className="text-lg font-bold text-gray-900">{formatDate(opp.deadline)}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Grant ID</span>
                        <span className="text-sm font-mono text-gray-700 break-words">{opp.id.slice(0, 12)}...</span>
                      </div>
                    </div>

                    {/* Description */}
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-gray-900 mb-2">Overview</h4>
                      <p className="text-sm text-gray-700 leading-relaxed">{opp.description}</p>
                    </div>

                    {/* Requirements */}
                    {opp.requirements && opp.requirements.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 mb-3">Key Requirements</h4>
                        <div className="space-y-2">
                          {opp.requirements.slice(0, 4).map((req, idx) => (
                            <div key={idx} className="flex items-start gap-2">
                              <span className="text-orange-600 font-bold mt-0.5 flex-shrink-0">•</span>
                              <span className="text-sm text-gray-700">{req}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Contact */}
                    {opp.contact && (
                      <div className="mb-6 pb-6 border-b border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Contact</h4>
                        <a href={`mailto:${opp.contact}`} className="text-sm text-perscholas-secondary hover:underline">
                          {opp.contact}
                        </a>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-3 flex-wrap">
                      {opp.application_url && (
                        <a
                          href={opp.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 border border-perscholas-secondary text-perscholas-secondary px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          View Opportunity
                        </a>
                      )}
                      <button
                        onClick={() => saveOpportunity(opp.id)}
                        disabled={isSaving}
                        className="flex items-center gap-2 bg-perscholas-secondary hover:bg-perscholas-dark disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                      >
                        {isSaving ? (
                          <>
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Saving...
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Save to Pipeline
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {opportunities.length === 0 && !isSearching && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-16 text-center">
            <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-2xl flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">
              Ready to Discover Opportunities
            </h3>
            <p className="text-gray-600 text-lg mb-8">
              Enter your search criteria above to deploy the AI agent and discover funding opportunities tailored to Per Scholas.
            </p>
            <a
              href="/opportunities"
              className="inline-flex items-center gap-2 bg-perscholas-secondary text-white px-8 py-3 rounded-lg font-semibold hover:bg-perscholas-dark transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              View Saved Opportunities
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
