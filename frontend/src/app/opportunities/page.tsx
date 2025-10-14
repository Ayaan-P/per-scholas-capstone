'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
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
  source?: string
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

interface OpportunitySummary {
  overview: string
  key_details: string[]
  funding_priorities: string[]
}

export default function OpportunitiesPage() {
  const [rawOpportunities, setRawOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [highMatchOnly, setHighMatchOnly] = useState(false)
  const [fundingMin, setFundingMin] = useState<number | undefined>(undefined)
  const [fundingMax, setFundingMax] = useState<number | undefined>(undefined)
  const [dueInDays, setDueInDays] = useState<number | undefined>(undefined)
  const [keywordSearch, setKeywordSearch] = useState<string>('')
  const [sortBy, setSortBy] = useState<'match' | 'amount' | 'deadline'>('match')
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 12
  const [expandedOpportunity, setExpandedOpportunity] = useState<string | null>(null)
  const [summaries, setSummaries] = useState<{ [key: string]: OpportunitySummary }>({})
  const [loadingSummary, setLoadingSummary] = useState<{ [key: string]: boolean }>({})
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    fetchOpportunities()
  }, [])

  // Reset page to 1 when any filter/sort/raw data changes
  useEffect(() => {
    setCurrentPage(1)
  }, [rawOpportunities, filter, highMatchOnly, fundingMin, fundingMax, dueInDays, keywordSearch, sortBy])

  // Show/hide back to top button based on scroll position
  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 400)
    }
    
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const fetchOpportunities = async () => {
    try {
      setLoading(true)
      const response = await api.getOpportunities()

      if (!response.ok) {
        console.error('Failed to fetch opportunities')
        setRawOpportunities([])
        return
      }

      const data = await response.json()
      setRawOpportunities(data.opportunities || [])
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
      setRawOpportunities([])
    } finally {
      setLoading(false)
    }
  }

  // Compute filtered + sorted opportunities on demand
  const filteredOpportunities = useMemo(() => {
    let list = [...rawOpportunities]

    // Apply source filter
    if (filter !== 'all') {
      list = list.filter(o => o.source === filter)
    }

    // Apply keyword search filter
    if (keywordSearch.trim()) {
      const keywords = keywordSearch.toLowerCase().trim()
      list = list.filter(o => {
        const searchText = `${o.title || ''} ${o.description || ''} ${o.funder || ''} ${o.contact || ''}`.toLowerCase()
        return searchText.includes(keywords)
      })
    }

    if (highMatchOnly) list = list.filter(o => o.match_score >= 85)

    if (fundingMin !== undefined) list = list.filter(o => (o.amount || 0) >= (fundingMin || 0))
    if (fundingMax !== undefined) list = list.filter(o => (o.amount || 0) <= (fundingMax || 0))

    if (dueInDays !== undefined) {
      const now = new Date()
      const maxDate = new Date(now.getTime() + (dueInDays * 24 * 60 * 60 * 1000))
      list = list.filter(o => {
        if (!o.deadline) return false
        const d = new Date(o.deadline)
        return d <= maxDate
      })
    }

    if (sortBy === 'match') {
      list.sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
    } else if (sortBy === 'amount') {
      list.sort((a, b) => (b.amount || 0) - (a.amount || 0))
    } else if (sortBy === 'deadline') {
      list.sort((a, b) => {
        const da = a.deadline ? new Date(a.deadline).getTime() : Infinity
        const db = b.deadline ? new Date(b.deadline).getTime() : Infinity
        return da - db
      })
    }

    return list
  }, [rawOpportunities, filter, highMatchOnly, fundingMin, fundingMax, dueInDays, keywordSearch, sortBy])

  const handleAction = async (opportunityId: string, action: 'pursue' | 'assign' | 'dismiss') => {
    // Mock action for demo
    alert(`Action "${action}" on opportunity ${opportunityId}`)
    // In real implementation, would call API to update status
  }

  const toggleSummary = async (opportunityId: string) => {
    if (expandedOpportunity === opportunityId) {
      setExpandedOpportunity(null)
      return
    }

    setExpandedOpportunity(opportunityId)

    // If we don't have the summary yet, fetch it
    if (!summaries[opportunityId]) {
      setLoadingSummary({ ...loadingSummary, [opportunityId]: true })
      
      try {
        const response = await api.generateOpportunitySummary(opportunityId)
        if (response.ok) {
          const data = await response.json()
          setSummaries({ ...summaries, [opportunityId]: data.summary })
        } else {
          console.error('Failed to fetch summary')
        }
      } catch (error) {
        console.error('Error fetching summary:', error)
      } finally {
        setLoadingSummary({ ...loadingSummary, [opportunityId]: false })
      }
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

  // Pagination calculations
  const totalPages = Math.max(1, Math.ceil(filteredOpportunities.length / itemsPerPage))
  const startIndex = (currentPage - 1) * itemsPerPage
  const paged = filteredOpportunities.slice(startIndex, startIndex + itemsPerPage)
  const windowSize = 5
  let pageStart = Math.max(1, currentPage - Math.floor(windowSize / 2))
  let pageEnd = Math.min(totalPages, pageStart + windowSize - 1)
  if (pageEnd - pageStart < windowSize - 1) {
    pageStart = Math.max(1, pageEnd - windowSize + 1)
  }
  const pages: number[] = []
  for (let i = pageStart; i <= pageEnd; i++) pages.push(i)

  const getMatchColor = (score: number) => {
    if (score >= 85) return 'bg-green-100 text-green-800'
    if (score >= 70) return 'bg-yellow-100 text-yellow-800'
    return 'bg-gray-100 text-gray-800'
  }

  const getSourceBadge = (source: string) => {
    const sourceColors: { [key: string]: string } = {
      'grants_gov': 'bg-blue-100 text-blue-800',
      'sam_gov': 'bg-purple-100 text-purple-800',
      'state': 'bg-green-100 text-green-800',
      'local': 'bg-orange-100 text-orange-800',
    }
    return sourceColors[source] || 'bg-gray-100 text-gray-800'
  }

  const getSourceLabel = (source: string) => {
    const labels: { [key: string]: string } = {
      'grants_gov': 'Grants.gov',
      'sam_gov': 'SAM.gov',
      'state': 'State',
      'local': 'Local',
    }
    return labels[source] || source
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
    if (!dateStr || dateStr === 'Historical') return dateStr
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading saved opportunities...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="bg-white rounded-2xl px-6 py-10 text-center shadow-sm border border-gray-100">
            <div className="flex items-center justify-center mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mr-4 shadow-lg">
                <svg className="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900">My Saved Opportunities</h1>
            </div>
            <p className="max-w-3xl mx-auto text-lg md:text-xl text-slate-700 mb-6 leading-relaxed">
              Your curated funding pipeline. Filter, sort, and manage opportunities you've saved from the discovery dashboard.
              Generate proposals and track your progress toward securing funding.
            </p>
            <p className="text-sm text-gray-500 mt-6">Tip: use filters to focus on high-priority opportunities or those due soon.</p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6 mb-8 w-full">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 items-stretch">
            {/* Total Saved */}
            <div className="bg-indigo-50/60 rounded-lg p-4 flex flex-col justify-center items-center md:items-start border border-transparent">
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wider mb-1">Total Saved</p>
              <p className="text-2xl md:text-3xl font-extrabold text-slate-900">{filteredOpportunities.length}</p>
              <p className="text-sm text-slate-500 mt-1">Opportunities in pipeline</p>
            </div>

            {/* Total Funding */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-indigo-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Total Funding</p>
              <p className="text-2xl md:text-3xl font-extrabold text-indigo-700">{formatCurrency(filteredOpportunities.reduce((sum, o) => sum + (o.amount || 0), 0))}</p>
              <p className="text-sm text-slate-500 mt-1">Across saved opportunities</p>
            </div>

            {/* High Match Count */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-green-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">High Match</p>
              <p className="text-2xl md:text-3xl font-extrabold text-green-600">{filteredOpportunities.filter(o => o.match_score >= 85).length}</p>
              <p className="text-sm text-slate-500 mt-1">Opportunities ≥ 85% match</p>
            </div>

            {/* High-match Funding */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-green-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">High-match Funding</p>
              <p className="text-2xl md:text-3xl font-extrabold text-green-600">{formatCurrency(filteredOpportunities.filter(o => o.match_score >= 85).reduce((sum, o) => sum + (o.amount || 0), 0))}</p>
              <p className="text-sm text-slate-500 mt-1">Funding for top-fit opportunities</p>
            </div>
          </div>
        </div>

        <div className="lg:flex lg:items-start lg:space-x-8">
          {/* Left sidebar - Filters */}
          <aside className="w-full lg:w-72 flex-shrink-0">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
              {/* Source Filter */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Filter by source</h4>
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="all">All Sources</option>
                  <option value="grants_gov">Grants.gov</option>
                  <option value="sam_gov">SAM.gov</option>
                  <option value="state">State</option>
                  <option value="local">Local</option>
                </select>
              </div>

              {/* Keyword Search */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Keyword search</h4>
                <input
                  type="text"
                  value={keywordSearch}
                  onChange={(e) => setKeywordSearch(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-indigo-100"
                  placeholder="Search in title, description, funder..."
                />
                {keywordSearch && (
                  <p className="text-xs text-gray-500 mt-2">
                    Searching across opportunity content...
                  </p>
                )}
              </div>

              {/* High Match Filter */}
              <div className="mb-6">
                <label className="flex items-center space-x-2 text-sm">
                  <input type="checkbox" checked={highMatchOnly} onChange={(e) => setHighMatchOnly(e.target.checked)} className="h-4 w-4" />
                  <span className="text-gray-700">High match only (85%+)</span>
                </label>
              </div>

              {/* Funding Range */}
              <div className="mb-6">
                <div className="mb-2 text-sm font-medium text-gray-700">Funding range</div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    value={fundingMin ?? ''}
                    onChange={(e) => setFundingMin(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Min"
                    className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-indigo-100"
                  />
                  <input
                    type="number"
                    value={fundingMax ?? ''}
                    onChange={(e) => setFundingMax(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Max"
                    className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-indigo-100"
                  />
                </div>
              </div>

              {/* Due Date Filter */}
              <div className="mb-4">
                <label className="text-sm font-medium text-gray-700 mb-2 block">Due in (days)</label>
                <input
                  type="number"
                  value={dueInDays ?? ''}
                  onChange={(e) => setDueInDays(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:ring-1 focus:ring-indigo-100"
                  placeholder="e.g. 30"
                />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 text-sm text-slate-600">
              <p className="mb-2 font-semibold text-gray-700">💡 Filter Tips:</p>
              <ul className="space-y-1 text-xs">
                <li>• Use keyword search to find specific terms</li>
                <li>• Filter by match score to prioritize</li>
                <li>• Set funding range to match your needs</li>
                <li>• Check "Due in" for upcoming deadlines</li>
              </ul>
            </div>
          </aside>

          {/* Main content - Opportunity List */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-4">
              <div></div>
              <div className="flex items-center space-x-3">
                <label className="text-sm text-gray-600">Sort by</label>
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-indigo-100">
                  <option value="match">Match Score</option>
                  <option value="amount">Funding Amount</option>
                  <option value="deadline">Due Date</option>
                </select>
              </div>
            </div>
            {filteredOpportunities.length === 0 ? (
              <div className="bg-white rounded-xl shadow-md border border-gray-200 p-16 text-center max-w-4xl mx-auto">
                <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">No saved opportunities yet</h3>
                <p className="text-gray-600 text-lg mb-8">Save grants from the dashboard to track them here</p>
                <a
                  href="/dashboard"
                  className="inline-block bg-gradient-to-r from-indigo-600 to-indigo-700 text-white px-8 py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all"
                >
                  Go to Dashboard
                </a>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto w-full">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {paged.map((opportunity) => (
                    <div key={opportunity.id} className={`bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-lg hover:border-indigo-300 transition-all duration-200 ${opportunity.match_score >= 85 ? 'border-l-4 border-green-200 pl-5' : ''}`}>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1 pr-4">
                          <h3 className="text-lg font-semibold text-gray-900 mb-1 line-clamp-2">{opportunity.title}</h3>
                          <p className="text-sm text-gray-600 font-medium">{opportunity.funder}</p>
                        </div>
                        <div className="flex flex-col items-end space-y-1">
                          <span
                            className={`px-3 py-1 rounded-md text-xs font-bold ${getMatchColor(opportunity.match_score)}`}
                            title="Match score"
                            aria-label={`Match score ${opportunity.match_score} percent`}
                          >
                            {opportunity.match_score}%
                          </span>
                          <p className="text-xl font-bold text-indigo-700">
                            {formatCurrency(opportunity.amount)}
                          </p>
                          <p className="text-xs text-gray-500 font-medium">{formatDate(opportunity.deadline)}</p>
                        </div>
                      </div>

                      <p className="text-sm text-gray-700 mb-3 leading-relaxed line-clamp-3">{opportunity.description}</p>

                      {/* AI Summary Button */}
                      <button
                        onClick={() => toggleSummary(opportunity.id)}
                        className="w-full mb-3 px-4 py-2 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 text-purple-700 rounded-lg hover:from-purple-100 hover:to-indigo-100 text-sm font-semibold transition-all flex items-center justify-center space-x-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span>{expandedOpportunity === opportunity.id ? 'Hide AI Summary' : 'View AI Summary'}</span>
                      </button>

                      {/* Expanded AI Summary */}
                      {expandedOpportunity === opportunity.id && (
                        <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                          {loadingSummary[opportunity.id] ? (
                            <div className="flex items-center justify-center py-8">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                              <p className="ml-3 text-purple-600 font-medium">Generating AI summary...</p>
                            </div>
                          ) : summaries[opportunity.id] ? (
                            <div className="space-y-4">
                              {/* Overview */}
                              <div>
                                <h4 className="text-sm font-bold text-purple-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  What This Grant Funds
                                </h4>
                                <p className="text-sm text-gray-700 leading-relaxed">{summaries[opportunity.id].overview}</p>
                              </div>

                              {/* Key Details */}
                              <div>
                                <h4 className="text-sm font-bold text-purple-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                  </svg>
                                  Key Details & Requirements
                                </h4>
                                <ul className="space-y-2">
                                  {summaries[opportunity.id].key_details.map((detail, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start">
                                      <span className="text-purple-600 mr-2 mt-0.5">•</span>
                                      <span>{detail}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Funding Priorities */}
                              <div>
                                <h4 className="text-sm font-bold text-purple-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                                  </svg>
                                  Funding Priorities
                                </h4>
                                <ul className="space-y-2">
                                  {summaries[opportunity.id].funding_priorities.map((priority, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start">
                                      <span className="text-purple-600 mr-2 mt-0.5">→</span>
                                      <span>{priority}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-600 text-center py-4">Unable to load summary. Please try again.</p>
                          )}
                        </div>
                      )}

                      <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                        <div className="flex items-center space-x-2">
                          {opportunity.source && (
                            <span className={`px-2 py-1 rounded-md text-xs font-bold ${getSourceBadge(opportunity.source)}`}>
                              {getSourceLabel(opportunity.source)}
                            </span>
                          )}
                          <span className="text-xs text-gray-500">{formatDate(opportunity.saved_at || opportunity.created_at || '')}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <a
                            href={opportunity.application_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 bg-white border border-indigo-100 text-indigo-600 rounded-md hover:bg-indigo-50 text-xs font-semibold"
                          >
                            <span className="inline-flex items-center space-x-2">
                              <span>Learn More</span>
                              <svg className="w-3 h-3 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 13v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" />
                              </svg>
                            </span>
                          </a>
                          <button
                            onClick={() => generateProposal(opportunity)}
                            className="px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-md hover:shadow-lg text-xs font-semibold"
                          >
                            Generate Proposal
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination controls */}
                <div className="mt-6 flex items-center justify-center space-x-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1.5 rounded-md border border-gray-200 bg-white text-sm disabled:opacity-50"
                  >
                    Previous
                  </button>

                  <div className="flex items-center space-x-1">
                    {pageStart > 1 && (
                      <button onClick={() => setCurrentPage(1)} className="px-2 py-1 rounded-md text-sm border border-gray-200 bg-white">1</button>
                    )}
                    {pageStart > 2 && <span className="px-2">…</span>}
                    {pages.map(p => (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`px-3 py-1 rounded-md text-sm border ${p === currentPage ? 'bg-indigo-600 text-white' : 'bg-white'}`}
                      >
                        {p}
                      </button>
                    ))}
                    {pageEnd < totalPages - 1 && <span className="px-2">…</span>}
                    {pageEnd < totalPages && (
                      <button onClick={() => setCurrentPage(totalPages)} className="px-2 py-1 rounded-md text-sm border border-gray-200 bg-white">{totalPages}</button>
                    )}
                  </div>

                  <button
                    onClick={() => setCurrentPage(p => Math.min(Math.max(1, Math.ceil(filteredOpportunities.length / itemsPerPage)), p + 1))}
                    disabled={currentPage >= Math.ceil(filteredOpportunities.length / itemsPerPage)}
                    className="px-3 py-1.5 rounded-md border border-gray-200 bg-white text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Back to Top Button */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 bg-gradient-to-r from-purple-600 to-purple-700 text-white p-4 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-300 z-40 group"
          aria-label="Back to top"
        >
          <svg className="w-6 h-6 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      )}
    </div>
  )
}