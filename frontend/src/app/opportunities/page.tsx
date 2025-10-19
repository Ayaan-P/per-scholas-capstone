'use client'

import { useState, useEffect, useMemo } from 'react'
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
  llm_summary?: string
  detailed_match_reasoning?: string
  tags?: string[]
  similar_past_proposals?: any[]
  llm_enhanced_at?: string
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
  const itemsPerPage = 6
  const [expandedOpportunity, setExpandedOpportunity] = useState<string | null>(null)
  const [summaries, setSummaries] = useState<{ [key: string]: OpportunitySummary }>({})
  const [loadingSummary, setLoadingSummary] = useState<{ [key: string]: boolean }>({})
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    fetchOpportunities()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [rawOpportunities, filter, highMatchOnly, fundingMin, fundingMax, dueInDays, keywordSearch, sortBy])

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

  const filteredOpportunities = useMemo(() => {
    let list = [...rawOpportunities]

    if (filter !== 'all') {
      list = list.filter(o => o.source === filter)
    }

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

  const handleDismiss = async (opportunityId: string) => {
    if (!confirm('Are you sure you want to dismiss this opportunity?')) {
      return
    }

    try {
      const response = await api.deleteOpportunity(opportunityId)

      if (response.ok) {
        setRawOpportunities(prev => prev.filter(opp => opp.id !== opportunityId))
      } else {
        alert('Failed to dismiss opportunity')
      }
    } catch (error) {
      console.error('Failed to dismiss opportunity:', error)
      alert('Failed to dismiss opportunity')
    }
  }

  const toggleExpanded = async (opportunityId: string) => {
    if (expandedOpportunity === opportunityId) {
      setExpandedOpportunity(null)
      return
    }

    setExpandedOpportunity(opportunityId)

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

  const getMatchColor = (score: number) => {
    if (score >= 85) return { bg: 'bg-green-600', text: 'text-green-700', border: 'border-green-200', lightBg: 'bg-green-50' }
    if (score >= 70) return { bg: 'bg-perscholas-accent', text: 'text-yellow-700', border: 'border-yellow-200', lightBg: 'bg-yellow-50' }
    return { bg: 'bg-gray-400', text: 'text-gray-700', border: 'border-gray-200', lightBg: 'bg-gray-50' }
  }

  const getSourceBadge = (source: string) => {
    const sourceColors: { [key: string]: string } = {
      'grants_gov': 'bg-blue-50 text-blue-700 border-blue-200',
      'sam_gov': 'bg-purple-50 text-purple-700 border-purple-200',
      'state': 'bg-green-50 text-green-700 border-green-200',
      'local': 'bg-orange-50 text-orange-700 border-orange-200',
    }
    return sourceColors[source] || 'bg-gray-50 text-gray-700 border-gray-200'
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-gray-200 border-t-perscholas-secondary mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading your pipeline...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-10">
            <div className="flex items-center gap-3 mb-3">
              <div className="bg-perscholas-secondary p-2.5 rounded-xl">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900">
                My Pipeline
              </h2>
            </div>
            <p className="text-gray-600 text-lg">
              Deep dive into saved opportunities with AI-powered insights, match analysis, and similar past RFPs.
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <p className="text-sm font-medium text-gray-600 mb-2">Pipeline</p>
            <p className="text-3xl font-bold text-gray-900">{filteredOpportunities.length}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <p className="text-sm font-medium text-gray-600 mb-2">Total Value</p>
            <p className="text-3xl font-bold text-green-600">{formatCurrency(filteredOpportunities.reduce((sum, o) => sum + (o.amount || 0), 0))}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <p className="text-sm font-medium text-gray-600 mb-2">High Match</p>
            <p className="text-3xl font-bold text-perscholas-accent">{filteredOpportunities.filter(o => o.match_score >= 85).length}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <p className="text-sm font-medium text-gray-600 mb-2">Avg Match</p>
            <p className="text-3xl font-bold text-perscholas-primary">
              {filteredOpportunities.length > 0
                ? Math.round(filteredOpportunities.reduce((sum, o) => sum + (o.match_score || 0), 0) / filteredOpportunities.length)
                : 0}%
            </p>
          </div>
        </div>

        <div className="lg:flex lg:gap-6">
          {/* Left Sidebar */}
          <aside className="lg:w-80 flex-shrink-0 mb-6 lg:mb-0">
            <div className="sticky top-6 space-y-4">
              {/* Filters */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  Refine Pipeline
                </h3>

                <div className="space-y-4">
                  <label className="flex items-center justify-between p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors">
                    <span className="text-sm font-medium text-gray-700">High Match Only</span>
                    <input
                      type="checkbox"
                      checked={highMatchOnly}
                      onChange={(e) => setHighMatchOnly(e.target.checked)}
                      className="w-4 h-4 text-perscholas-secondary rounded focus:ring-2 focus:ring-perscholas-secondary/20"
                    />
                  </label>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Source</label>
                    <select
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary bg-white"
                    >
                      <option value="all">All Sources</option>
                      <option value="grants_gov">Grants.gov</option>
                      <option value="sam_gov">SAM.gov</option>
                      <option value="dol_workforce">DOL Workforce Development</option>
                      <option value="usa_spending">Federal Spending Database</option>
                      <option value="state">State</option>
                      <option value="local">Local</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Search</label>
                    <div className="relative">
                      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        value={keywordSearch}
                        onChange={(e) => setKeywordSearch(e.target.value)}
                        className="w-full pl-10 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary"
                        placeholder="Keywords..."
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Funding Range</label>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        value={fundingMin ?? ''}
                        onChange={(e) => setFundingMin(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Min"
                        className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary"
                      />
                      <input
                        type="number"
                        value={fundingMax ?? ''}
                        onChange={(e) => setFundingMax(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Max"
                        className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Due Within (days)</label>
                    <input
                      type="number"
                      value={dueInDays ?? ''}
                      onChange={(e) => setDueInDays(e.target.value ? Number(e.target.value) : undefined)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary"
                      placeholder="e.g. 30"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Sort By</label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary bg-white"
                    >
                      <option value="match">Match Score</option>
                      <option value="amount">Funding Amount</option>
                      <option value="deadline">Due Date</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* AI Insights Info */}
              <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
                <div className="flex items-start gap-3">
                  <div className="bg-perscholas-secondary p-1.5 rounded-lg flex-shrink-0">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-perscholas-dark mb-1">AI Analysis Active</p>
                    <p className="text-xs text-gray-700 leading-relaxed">
                      Expand opportunities to view AI summaries, match reasoning, and similar RFPs.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {filteredOpportunities.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-20 text-center">
                <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-2xl flex items-center justify-center">
                  <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">No saved opportunities yet</h3>
                <p className="text-gray-600 text-lg mb-8">Save grants from the dashboard to analyze them here</p>
                <a
                  href="/dashboard"
                  className="inline-flex items-center gap-2 bg-perscholas-primary text-white px-8 py-3 rounded-lg font-semibold hover:bg-perscholas-dark transition-all"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Discover Grants
                </a>
              </div>
            ) : (
              <div>
                <div className="space-y-6 mb-8">
                  {paged.map((opportunity) => {
                    const isExpanded = expandedOpportunity === opportunity.id
                    const colors = getMatchColor(opportunity.match_score)

                    return (
                      <div
                        key={opportunity.id}
                        className={`bg-white border rounded-2xl shadow-sm hover:shadow-md transition-all duration-300 ${
                          isExpanded ? 'border-perscholas-secondary shadow-lg' : 'border-gray-200'
                        }`}
                      >
                        {/* Card Header */}
                        <div className="p-6">
                          {/* Title Row with Match Score */}
                          <div className="flex items-start justify-between gap-4 mb-4">
                            <div className="flex-1 min-w-0">
                              <h3 className="text-xl font-bold text-gray-900 leading-tight mb-1">
                                {opportunity.title}
                              </h3>
                              <p className="text-sm text-gray-600">{opportunity.funder}</p>
                            </div>
                            <div className={`flex-shrink-0 ${colors.bg} text-white px-4 py-2 rounded-full shadow-sm`}>
                              <span className="font-bold">{opportunity.match_score}%</span>
                            </div>
                          </div>

                          {/* Key Metrics - Simplified Grid */}
                          <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
                            <div>
                              <p className="text-xs text-gray-500 mb-1">Funding</p>
                              <p className="text-lg font-bold text-green-600">{formatCurrency(opportunity.amount)}</p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 mb-1">Deadline</p>
                              <p className="text-lg font-bold text-gray-900">{formatDate(opportunity.deadline)}</p>
                            </div>
                            {opportunity.source && (
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Source</p>
                                <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${getSourceBadge(opportunity.source)}`}>
                                  {getSourceLabel(opportunity.source)}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* AI Summary - Always Full Display */}
                          {opportunity.llm_summary && (
                            <div className={`${colors.lightBg} border ${colors.border} rounded-xl p-4 mb-4`}>
                              <div className="flex items-start gap-2 mb-2">
                                <svg className="w-4 h-4 text-perscholas-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                <p className="text-xs font-bold text-perscholas-dark">AI INSIGHT</p>
                              </div>
                              <p className={`text-sm ${colors.text} leading-relaxed`}>
                                {opportunity.llm_summary}
                              </p>
                            </div>
                          )}

                          {/* Tags */}
                          {opportunity.tags && opportunity.tags.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-4">
                              {opportunity.tags.slice(0, isExpanded ? undefined : 5).map((tag, idx) => (
                                <span
                                  key={idx}
                                  className="px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-perscholas-dark border border-perscholas-dark"
                                >
                                  {tag}
                                </span>
                              ))}
                              {!isExpanded && opportunity.tags.length > 5 && (
                                <span className="px-3 py-1 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-xs font-medium">
                                  +{opportunity.tags.length - 5} more
                                </span>
                              )}
                            </div>
                          )}

                          {/* Action Buttons */}
                          <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
                            <button
                              onClick={() => toggleExpanded(opportunity.id)}
                              className="flex-1 flex items-center justify-center gap-2 bg-perscholas-secondary text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-perscholas-primary hover:shadow-lg transition-all"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isExpanded ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"} />
                              </svg>
                              {isExpanded ? 'Hide Reasoning' : 'View Reasoning'}
                            </button>
                            {opportunity.application_url && (
                              <a
                                href={opportunity.application_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 border-2 border-gray-300 text-gray-700 px-5 py-2.5 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                                Open
                              </a>
                            )}
                            <button
                              onClick={() => handleDismiss(opportunity.id)}
                              className="border-2 border-red-300 text-red-600 px-5 py-2.5 rounded-lg font-semibold hover:bg-red-50 transition-colors"
                            >
                              Dismiss
                            </button>
                          </div>
                        </div>

                        {/* Expanded Analysis */}
                        {isExpanded && (
                          <div className="border-t border-gray-100 bg-gray-50 p-6">
                            {/* Match Reasoning */}
                            {opportunity.detailed_match_reasoning && (
                              <div className="mb-6">
                                <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  Why This Matches Your Organization
                                </h4>
                                <div className="bg-white rounded-xl p-5 border border-gray-200 space-y-3">
                                  {opportunity.detailed_match_reasoning.split('\n').map((paragraph, idx) => {
                                    const isBullet = paragraph.trim().match(/^[-•*]\s+/)
                                    const isNumbered = paragraph.trim().match(/^\d+\.\s+/)
                                    const isHeader = paragraph.trim().match(/^[A-Z][^.!?]*:$/) || paragraph.trim().match(/^#{1,3}\s+/)

                                    if (!paragraph.trim()) return null

                                    const renderWithBold = (text: string) => {
                                      const parts = text.split(/(\*\*.*?\*\*)/)
                                      return parts.map((part, i) => {
                                        if (part.startsWith('**') && part.endsWith('**')) {
                                          return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>
                                        }
                                        return part
                                      })
                                    }

                                    if (isHeader) {
                                      return (
                                        <p key={idx} className="text-sm font-bold text-perscholas-dark mt-3 first:mt-0">
                                          {renderWithBold(paragraph.replace(/^#{1,3}\s+/, ''))}
                                        </p>
                                      )
                                    } else if (isBullet) {
                                      return (
                                        <div key={idx} className="flex gap-3 text-sm text-gray-700 leading-relaxed">
                                          <span className="flex-shrink-0 text-perscholas-secondary font-bold">•</span>
                                          <span>{renderWithBold(paragraph.replace(/^[-•*]\s+/, ''))}</span>
                                        </div>
                                      )
                                    } else if (isNumbered) {
                                      return (
                                        <div key={idx} className="flex gap-3 text-sm text-gray-700 leading-relaxed">
                                          <span className="flex-shrink-0 font-bold text-perscholas-secondary">{paragraph.match(/^\d+\./)?.[0]}</span>
                                          <span>{renderWithBold(paragraph.replace(/^\d+\.\s+/, ''))}</span>
                                        </div>
                                      )
                                    } else {
                                      return (
                                        <p key={idx} className="text-sm text-gray-700 leading-relaxed">
                                          {renderWithBold(paragraph)}
                                        </p>
                                      )
                                    }
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Fallback: Legacy Summary */}
                            {!opportunity.detailed_match_reasoning && (
                              <div className="mb-6">
                                {loadingSummary[opportunity.id] ? (
                                  <div className="flex items-center justify-center py-12 bg-white rounded-xl border border-gray-200">
                                    <div className="text-center">
                                      <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-perscholas-secondary mx-auto mb-3"></div>
                                      <p className="text-sm text-perscholas-secondary font-medium">Generating AI analysis...</p>
                                    </div>
                                  </div>
                                ) : summaries[opportunity.id] ? (
                                  <div className="bg-white rounded-xl p-5 border border-gray-200 space-y-4">
                                    <div>
                                      <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
                                        <svg className="w-4 h-4 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Overview
                                      </h4>
                                      <p className="text-sm text-gray-700 leading-relaxed">{summaries[opportunity.id].overview}</p>
                                    </div>
                                    <div>
                                      <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
                                        <svg className="w-4 h-4 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                        </svg>
                                        Key Details
                                      </h4>
                                      <ul className="space-y-2">
                                        {summaries[opportunity.id].key_details.map((detail, idx) => (
                                          <li key={idx} className="text-sm text-gray-700 flex gap-2">
                                            <span className="text-perscholas-secondary">•</span>
                                            <span>{detail}</span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                    <div>
                                      <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
                                        <svg className="w-4 h-4 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                                        </svg>
                                        Funding Priorities
                                      </h4>
                                      <ul className="space-y-2">
                                        {summaries[opportunity.id].funding_priorities.map((priority, idx) => (
                                          <li key={idx} className="text-sm text-gray-700 flex gap-2">
                                            <span className="text-perscholas-secondary">→</span>
                                            <span>{priority}</span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  </div>
                                ) : null}
                              </div>
                            )}

                            {/* Similar RFPs Placeholder */}
                            <div className="bg-blue-50 rounded-xl p-5 border border-blue-200">
                              <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
                                <svg className="w-5 h-5 text-perscholas-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                </svg>
                                Similar Past RFPs
                              </h4>
                              <p className="text-sm text-gray-700">
                                Semantic analysis of past proposals coming soon. This will surface similar RFPs you've worked on, success patterns, and proposal templates.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-4 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>

                  <div className="flex items-center gap-1">
                    {pageStart > 1 && (
                      <>
                        <button onClick={() => setCurrentPage(1)} className="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">1</button>
                        {pageStart > 2 && <span className="px-2 text-gray-400">…</span>}
                      </>
                    )}
                    {pages.map(p => (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          p === currentPage
                            ? 'bg-perscholas-secondary text-white border-perscholas-secondary shadow-md'
                            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                    {pageEnd < totalPages - 1 && <span className="px-2 text-gray-400">…</span>}
                    {pageEnd < totalPages && (
                      <button onClick={() => setCurrentPage(totalPages)} className="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">{totalPages}</button>
                    )}
                  </div>

                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    className="px-4 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Back to Top */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 bg-perscholas-secondary text-white p-4 rounded-full shadow-2xl hover:shadow-xl hover:scale-110 transition-all duration-300 z-40 group"
          aria-label="Back to top"
        >
          <svg className="w-5 h-5 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      )}
    </div>
  )
}
