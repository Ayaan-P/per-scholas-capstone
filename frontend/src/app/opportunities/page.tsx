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
  // LLM Enhancement fields from saved_opportunities table
  llm_summary?: string
  detailed_match_reasoning?: string
  tags?: string[]
  similar_past_proposals?: any[]
  llm_enhanced_at?: string
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
  const [expandedSummaries, setExpandedSummaries] = useState<{ [key: string]: boolean }>({})
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
    if (score >= 85) return 'bg-green-50 text-green-700 border border-green-200'
    if (score >= 70) return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
    return 'bg-red-50 text-red-700 border border-red-200'
  }

  const getSourceBadge = (source: string) => {
    const sourceColors: { [key: string]: string } = {
      'grants_gov': 'bg-blue-100 text-blue-800',
      'california': 'bg-amber-100 text-amber-800',
      'sam_gov': 'bg-purple-100 text-purple-800',
      'state': 'bg-green-100 text-green-800',
      'local': 'bg-orange-100 text-orange-800',
    }
    return sourceColors[source] || 'bg-gray-100 text-gray-800'
  }

  const getSourceLabel = (source: string) => {
    const labels: { [key: string]: string } = {
      'grants_gov': 'Grants.gov',
      'california': 'California',
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading saved opportunities...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              My Saved Opportunities
            </h2>
            <p className="text-gray-600">
              Your curated funding pipeline. Filter, sort, and manage opportunities you've saved from the discovery dashboard.
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            {/* Total Saved */}
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Saved</p>
              <p className="text-3xl font-bold text-gray-900">{filteredOpportunities.length}</p>
              <p className="text-sm text-gray-500 mt-1">Opportunities</p>
            </div>

            {/* Total Funding */}
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Funding</p>
              <p className="text-3xl font-bold text-green-600">{formatCurrency(filteredOpportunities.reduce((sum, o) => sum + (o.amount || 0), 0))}</p>
              <p className="text-sm text-gray-500 mt-1">Available</p>
            </div>

            {/* High Match Count */}
            <div>
              <p className="text-sm text-gray-500 mb-1">High Match</p>
              <p className="text-3xl font-bold" style={{ color: '#fec14f' }}>{filteredOpportunities.filter(o => o.match_score >= 85).length}</p>
              <p className="text-sm text-gray-500 mt-1">≥ 85% fit</p>
            </div>

            {/* Average Match */}
            <div>
              <p className="text-sm text-gray-500 mb-1">Avg Match Score</p>
              <p className="text-3xl font-bold" style={{
                color: filteredOpportunities.length > 0
                  ? Math.round(filteredOpportunities.reduce((sum, o) => sum + (o.match_score || 0), 0) / filteredOpportunities.length) >= 85
                    ? '#10b981'
                    : Math.round(filteredOpportunities.reduce((sum, o) => sum + (o.match_score || 0), 0) / filteredOpportunities.length) >= 70
                      ? '#fec14f'
                      : '#ef4444'
                  : '#111827'
              }}>
                {filteredOpportunities.length > 0
                  ? Math.round(filteredOpportunities.reduce((sum, o) => sum + (o.match_score || 0), 0) / filteredOpportunities.length)
                  : 0}%
              </p>
              <p className="text-sm text-gray-500 mt-1">Overall</p>
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
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-gray-200"
                >
                  <option value="all">All Sources</option>
                  <option value="grants_gov">Grants.gov</option>
                  <option value="california">California Grants Portal</option>
                  <option value="sam_gov">SAM.gov</option>
                  <option value="state">Other State</option>
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
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-gray-200"
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
                    className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-gray-200"
                  />
                  <input
                    type="number"
                    value={fundingMax ?? ''}
                    onChange={(e) => setFundingMax(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Max"
                    className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-gray-200"
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
                  className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:ring-1 focus:ring-gray-200"
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
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-gray-200">
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
                  className="inline-block bg-perscholas-primary text-white px-8 py-3 rounded-full font-semibold hover:bg-opacity-90 transition-all"
                >
                  Go to Dashboard
                </a>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto w-full">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {paged.map((opportunity) => (
                    <div key={opportunity.id} className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-white flex flex-col h-full">
                      {/* Header with title, funder, and key metrics */}
                      <div className="mb-3">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1 pr-3 min-w-0">
                            <h3 className="text-base font-semibold text-gray-900 mb-1 line-clamp-2 leading-tight">{opportunity.title}</h3>
                          </div>
                          <div className="flex flex-col items-end space-y-1.5 flex-shrink-0">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getMatchColor(opportunity.match_score)}`}
                              title="Match score"
                            >
                              {opportunity.match_score}%
                            </span>
                            <div className="text-lg font-bold text-green-600">
                              {formatCurrency(opportunity.amount)}
                            </div>
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <div className="text-xs text-gray-600 font-medium truncate">{opportunity.funder}</div>
                          <div className="text-xs text-gray-500 flex-shrink-0 ml-3">
                            <span className="font-medium">Due:</span> {formatDate(opportunity.deadline)}
                          </div>
                        </div>
                      </div>

                      {/* AI Summary - Expandable */}
                      <div className="bg-gray-50 p-3 rounded-lg mb-2">
                        {opportunity.llm_summary && (
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <svg className="w-3.5 h-3.5" style={{ color: '#009ee0' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                            </svg>
                            <span className="text-xs font-semibold" style={{ color: '#009ee0' }}>AI SUMMARY</span>
                          </div>
                        )}
                        <p className={`text-xs text-gray-700 leading-relaxed ${!expandedSummaries[opportunity.id] ? 'line-clamp-3' : ''}`}>
                          {opportunity.llm_summary || opportunity.description}
                        </p>
                        {opportunity.llm_summary && opportunity.llm_summary.length > 200 && (
                          <button
                            onClick={() => setExpandedSummaries({ ...expandedSummaries, [opportunity.id]: !expandedSummaries[opportunity.id] })}
                            className="text-xs hover:underline mt-1.5 font-medium"
                            style={{ color: '#009ee0' }}
                          >
                            {expandedSummaries[opportunity.id] ? '← Show less' : 'Read more →'}
                          </button>
                        )}
                      </div>

                      {/* Tags */}
                      {opportunity.tags && opportunity.tags.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1.5">
                          {opportunity.tags.slice(0, 3).map((tag, idx) => (
                            <span key={idx} className="px-2 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: '#e0f2fe', color: '#00476e', borderColor: '#00476e', borderWidth: '1px' }}>
                              {tag}
                            </span>
                          ))}
                          {opportunity.tags.length > 3 && (
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-xs">
                              +{opportunity.tags.length - 3} more
                            </span>
                          )}
                        </div>
                      )}

                      {/* Match Reasoning - Inline Expandable */}
                      {opportunity.detailed_match_reasoning && (
                        <div className="mb-2">
                          <button
                            onClick={() => toggleSummary(opportunity.id)}
                            className="text-xs font-medium flex items-center gap-1 hover:underline"
                            style={{ color: '#009ee0' }}
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {expandedOpportunity === opportunity.id ? 'Hide' : 'Why this matches'}
                          </button>
                          {expandedOpportunity === opportunity.id && (
                            <div className="mt-2 p-3 rounded-lg space-y-2" style={{ backgroundColor: '#e0f2fe', borderColor: '#009ee0', borderWidth: '1px' }}>
                              {opportunity.detailed_match_reasoning.split('\n').map((paragraph, idx) => {
                                // Check if it's a bullet point or numbered list
                                const isBullet = paragraph.trim().match(/^[-•*]\s+/)
                                const isNumbered = paragraph.trim().match(/^\d+\.\s+/)
                                const isHeader = paragraph.trim().match(/^[A-Z][^.!?]*:$/) || paragraph.trim().match(/^#{1,3}\s+/)

                                if (!paragraph.trim()) return null

                                // Function to render text with bold formatting
                                const renderWithBold = (text: string) => {
                                  const parts = text.split(/(\*\*.*?\*\*)/)
                                  return parts.map((part, i) => {
                                    if (part.startsWith('**') && part.endsWith('**')) {
                                      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
                                    }
                                    return part
                                  })
                                }

                                if (isHeader) {
                                  return (
                                    <p key={idx} className="text-xs font-semibold text-gray-900 mt-2 first:mt-0">
                                      {renderWithBold(paragraph.replace(/^#{1,3}\s+/, ''))}
                                    </p>
                                  )
                                } else if (isBullet) {
                                  return (
                                    <div key={idx} className="flex gap-2 text-xs text-gray-700 leading-relaxed">
                                      <span className="flex-shrink-0" style={{ color: '#009ee0' }}>•</span>
                                      <span>{renderWithBold(paragraph.replace(/^[-•*]\s+/, ''))}</span>
                                    </div>
                                  )
                                } else if (isNumbered) {
                                  return (
                                    <div key={idx} className="flex gap-2 text-xs text-gray-700 leading-relaxed mt-1">
                                      <span className="flex-shrink-0 font-medium" style={{ color: '#009ee0' }}>{paragraph.match(/^\d+\./)?.[0]}</span>
                                      <span>{renderWithBold(paragraph.replace(/^\d+\.\s+/, ''))}</span>
                                    </div>
                                  )
                                } else {
                                  return (
                                    <p key={idx} className="text-xs text-gray-700 leading-relaxed">
                                      {renderWithBold(paragraph)}
                                    </p>
                                  )
                                }
                              })}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Fallback: Old AI Summary for opportunities without LLM enhancement */}
                      {!opportunity.detailed_match_reasoning && expandedOpportunity === opportunity.id && (
                        <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                          {loadingSummary[opportunity.id] ? (
                            <div className="flex items-center justify-center py-8">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                              <p className="ml-3 text-blue-600 font-medium">Generating AI summary...</p>
                            </div>
                          ) : summaries[opportunity.id] ? (
                            <div className="space-y-4">
                              {/* Overview */}
                              <div>
                                <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  What This Grant Funds
                                </h4>
                                <p className="text-sm text-gray-700 leading-relaxed">{summaries[opportunity.id].overview}</p>
                              </div>

                              {/* Key Details */}
                              <div>
                                <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                  </svg>
                                  Key Details & Requirements
                                </h4>
                                <ul className="space-y-2">
                                  {summaries[opportunity.id].key_details.map((detail, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start">
                                      <span className="text-blue-600 mr-2 mt-0.5">•</span>
                                      <span>{detail}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Funding Priorities */}
                              <div>
                                <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                                  </svg>
                                  Funding Priorities
                                </h4>
                                <ul className="space-y-2">
                                  {summaries[opportunity.id].funding_priorities.map((priority, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start">
                                      <span className="text-blue-600 mr-2 mt-0.5">→</span>
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

                      {/* Bottom section with metadata and actions */}
                      <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-auto">
                        <div className="flex items-center gap-2 text-xs text-gray-500 min-w-0">
                          {opportunity.source && (
                            <span className={`px-2 py-0.5 rounded-full text-xs ${getSourceBadge(opportunity.source)}`}>
                              {getSourceLabel(opportunity.source)}
                            </span>
                          )}
                          <span className="truncate">Saved {formatDate(opportunity.saved_at || opportunity.created_at || '')}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {opportunity.application_url && (
                            <a
                              href={opportunity.application_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="border border-perscholas-primary text-perscholas-primary px-4 py-1.5 rounded-full text-xs font-medium hover:bg-gray-50 transition-colors whitespace-nowrap"
                            >
                              Learn More
                            </a>
                          )}
                          <button
                            onClick={() => generateProposal(opportunity)}
                            className="bg-perscholas-primary text-white px-4 py-1.5 rounded-full text-xs font-medium hover:bg-opacity-90 transition-colors whitespace-nowrap"
                          >
                            Generate
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
                        className={`px-3 py-1 rounded-md text-sm border ${p === currentPage ? 'bg-perscholas-primary text-white border-perscholas-primary' : 'bg-white border-gray-200'}`}
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
          className="fixed bottom-8 right-8 bg-perscholas-primary text-white p-4 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-300 z-40 group"
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