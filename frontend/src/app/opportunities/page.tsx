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
  winning_strategies?: string[]
  key_themes?: string[]
  recommended_metrics?: string[]
  considerations?: string[]
  similar_past_proposals?: any[]
  llm_enhanced_at?: string

  // UNIVERSAL COMPREHENSIVE FIELDS (work across all grant sources)
  contact_name?: string
  contact_phone?: string
  contact_description?: string
  eligibility_explanation?: string
  cost_sharing?: boolean
  cost_sharing_description?: string
  additional_info_url?: string
  additional_info_text?: string
  archive_date?: string
  forecast_date?: string
  close_date_explanation?: string
  expected_number_of_awards?: string
  award_floor?: number
  award_ceiling?: number
  attachments?: Array<{
    title: string
    url: string
    type: string
  }>
  version?: string
  last_updated_date?: string
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
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [dismissingOpportunities, setDismissingOpportunities] = useState<Set<string>>(new Set())
  const [addingToRfpDb, setAddingToRfpDb] = useState<Set<string>>(new Set())
  const [rfpDbSuccessMessage, setRfpDbSuccessMessage] = useState<{ [key: string]: string }>({})
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadingRfp, setUploadingRfp] = useState(false)
  const [uploadResult, setUploadResult] = useState<any>(null)

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
    if (!confirm('Are you sure you want to dismiss this opportunity? This action cannot be undone.')) {
      return
    }

    // Add to dismissing set
    setDismissingOpportunities(prev => new Set(prev).add(opportunityId))

    try {
      const response = await api.deleteOpportunity(opportunityId)

      if (response.ok) {
        // Remove from opportunities list with a slight delay for visual feedback
        setTimeout(() => {
          setRawOpportunities(prev => prev.filter(opp => opp.id !== opportunityId))
          setDismissingOpportunities(prev => {
            const newSet = new Set(prev)
            newSet.delete(opportunityId)
            return newSet
          })
        }, 300)
      } else {
        alert('Failed to dismiss opportunity')
        setDismissingOpportunities(prev => {
          const newSet = new Set(prev)
          newSet.delete(opportunityId)
          return newSet
        })
      }
    } catch (error) {
      console.error('Failed to dismiss opportunity:', error)
      alert('Failed to dismiss opportunity')
      setDismissingOpportunities(prev => {
        const newSet = new Set(prev)
        newSet.delete(opportunityId)
        return newSet
      })
    }
  }

  const handleAddToRfpDb = async (opportunityId: string) => {
    // Add to loading set
    setAddingToRfpDb(prev => new Set(prev).add(opportunityId))

    try {
      const response = await api.addOpportunityToRfpDb(opportunityId)
      const data = await response.json()

      console.log('RFP DB Response:', { status: response.status, data })

      if (response.ok) {
        if (data.status === 'already_exists') {
          console.log('Setting already exists message for', opportunityId)
          // Show message that it already exists
          setRfpDbSuccessMessage(prev => ({
            ...prev,
            [opportunityId]: '✓ Already in training database'
          }))
        } else {
          console.log('Setting success message for', opportunityId)
          // Show success message
          setRfpDbSuccessMessage(prev => ({
            ...prev,
            [opportunityId]: '✓ Added to training database!'
          }))
        }

        // Clear message after 3 seconds
        setTimeout(() => {
          setRfpDbSuccessMessage(prev => {
            const newMessages = { ...prev }
            delete newMessages[opportunityId]
            return newMessages
          })
        }, 3000)
      } else {
        console.error('Response not OK:', response.status, data)
        alert(`Failed to add to training database: ${data.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to add to RFP database:', error)
      alert('Failed to add to training database')
    } finally {
      setAddingToRfpDb(prev => {
        const newSet = new Set(prev)
        newSet.delete(opportunityId)
        return newSet
      })
    }
  }

  const handleUploadRfp = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setUploadingRfp(true)
    setUploadResult(null)

    const formData = new FormData(event.currentTarget)
    const file = formData.get('file') as File

    if (!file) {
      alert('Please select a PDF file')
      setUploadingRfp(false)
      return
    }

    try {
      const response = await fetch(`${api.baseURL}/api/rfps/upload`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (response.ok) {
        setUploadResult(data)
        // Refresh opportunities to show the new upload
        setTimeout(() => {
          fetchOpportunities()
        }, 1500)
      } else {
        alert(`Upload failed: ${data.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Upload error:', error)
      alert('Failed to upload RFP. Please try again.')
    } finally {
      setUploadingRfp(false)
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
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
          {/* Header Skeleton */}
          <div className="mb-6 sm:mb-8">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-10 animate-pulse">
              <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                <div className="bg-gray-200 p-2 sm:p-2.5 rounded-xl w-10 h-10"></div>
                <div className="h-8 bg-gray-200 rounded w-48"></div>
              </div>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          </div>

          {/* Stats Skeleton */}
          <div className="mb-6 sm:mb-8 grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm animate-pulse">
                <div className="h-3 bg-gray-200 rounded w-20 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-24"></div>
              </div>
            ))}
          </div>

          {/* Content Skeleton */}
          <div className="lg:flex lg:gap-6">
            <aside className="hidden lg:block lg:w-80 flex-shrink-0 mb-6 lg:mb-0">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-32 mb-4"></div>
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-10 bg-gray-200 rounded"></div>
                  ))}
                </div>
              </div>
            </aside>

            <div className="flex-1 min-w-0">
              <div className="space-y-6">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm animate-pulse">
                    <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                    <div className="space-y-2 mb-4">
                      <div className="h-3 bg-gray-200 rounded"></div>
                      <div className="h-3 bg-gray-200 rounded"></div>
                      <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                    </div>
                    <div className="h-12 bg-gray-200 rounded"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-10">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="bg-perscholas-secondary p-2 sm:p-2.5 rounded-xl">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  Saved Opportunities
                </h2>
              </div>
              <button
                onClick={() => setShowUploadModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-perscholas-secondary text-white rounded-lg hover:bg-perscholas-dark transition-colors font-medium text-sm sm:text-base"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="hidden sm:inline">Upload RFP</span>
                <span className="sm:hidden">Upload</span>
              </button>
            </div>
            <p className="text-gray-600 text-base sm:text-lg">
              Review and analyze your saved opportunities with AI-powered insights, match reasoning, and similar past proposals.
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 sm:mb-8 grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Pipeline</p>
            <p className="text-2xl sm:text-3xl font-bold text-gray-900">{filteredOpportunities.length}</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Total Value</p>
            <p className="text-xl sm:text-3xl font-bold text-green-600 truncate">{formatCurrency(filteredOpportunities.reduce((sum, o) => sum + (o.amount || 0), 0))}</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">High Match</p>
            <p className="text-2xl sm:text-3xl font-bold text-perscholas-accent">{filteredOpportunities.filter(o => o.match_score >= 85).length}</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Avg Match</p>
            <p className="text-2xl sm:text-3xl font-bold text-perscholas-primary">
              {filteredOpportunities.length > 0
                ? Math.round(filteredOpportunities.reduce((sum, o) => sum + (o.match_score || 0), 0) / filteredOpportunities.length)
                : 0}%
            </p>
          </div>
        </div>

        {/* Mobile Filter Button */}
        <div className="lg:hidden mb-4">
          <button
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className="w-full flex items-center justify-between bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-2">
              <div className="relative">
                <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                {(highMatchOnly || filter !== 'all' || keywordSearch || fundingMin || fundingMax || dueInDays) && (
                  <span className="absolute -top-2 -right-2 flex h-4 w-4">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-perscholas-accent opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-4 w-4 bg-perscholas-accent items-center justify-center">
                      <span className="text-white text-xs font-bold">!</span>
                    </span>
                  </span>
                )}
              </div>
              <span className="font-bold text-gray-900">Filters & Search</span>
            </div>
            <svg className={`w-5 h-5 text-gray-600 transition-transform duration-300 ${showMobileFilters ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        <div className="lg:flex lg:gap-6">
          {/* Left Sidebar */}
          <aside className={`lg:w-80 flex-shrink-0 mb-6 lg:mb-0 ${showMobileFilters ? 'block' : 'hidden lg:block'}`}>
            <div className="lg:sticky lg:top-6 space-y-4">
              {/* Filters */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  Refine Pipeline
                </h3>

                <div className="space-y-4">
                  <label className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                    highMatchOnly
                      ? 'border-green-500 bg-green-50 hover:bg-green-100'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}>
                    <span className={`text-sm font-medium ${highMatchOnly ? 'text-green-700' : 'text-gray-700'}`}>High Match Only</span>
                    <input
                      type="checkbox"
                      checked={highMatchOnly}
                      onChange={(e) => setHighMatchOnly(e.target.checked)}
                      className="w-4 h-4 text-green-600 rounded focus:ring-2 focus:ring-green-500/20"
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
                      <option value="ny_dol">NY Department of Labor</option>
                      <option value="state">State</option>
                      <option value="local">Local</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Search</label>
                    <div className="relative">
                      <svg className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${
                        keywordSearch ? 'text-perscholas-secondary' : 'text-gray-400'
                      }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        value={keywordSearch}
                        onChange={(e) => setKeywordSearch(e.target.value)}
                        className={`w-full pl-10 pr-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-perscholas-secondary/20 focus:border-perscholas-secondary transition-all ${
                          keywordSearch ? 'border-perscholas-secondary bg-blue-50' : 'border-gray-200'
                        }`}
                        placeholder="Keywords..."
                      />
                      {keywordSearch && (
                        <button
                          onClick={() => setKeywordSearch('')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                          aria-label="Clear search"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
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

                  {/* Clear Filters Button */}
                  {(highMatchOnly || filter !== 'all' || keywordSearch || fundingMin || fundingMax || dueInDays) && (
                    <button
                      onClick={() => {
                        setHighMatchOnly(false)
                        setFilter('all')
                        setKeywordSearch('')
                        setFundingMin(undefined)
                        setFundingMax(undefined)
                        setDueInDays(undefined)
                      }}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 active:scale-95 transition-all"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      Clear All Filters
                    </button>
                  )}
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
                  {paged.map((opportunity, index) => {
                    const isExpanded = expandedOpportunity === opportunity.id
                    const colors = getMatchColor(opportunity.match_score)

                    return (
                      <div
                        key={opportunity.id}
                        className={`bg-white border rounded-xl transition-shadow duration-200 ${
                          dismissingOpportunities.has(opportunity.id)
                            ? 'opacity-50 pointer-events-none'
                            : ''
                        } ${
                          isExpanded ? 'border-perscholas-secondary shadow-md' : 'border-gray-200 shadow-sm hover:shadow-md'
                        }`}
                      >
                        {/* Card Header */}
                        <div className="p-6">
                          {/* Title Row with Match Score */}
                          <div className="flex items-start justify-between gap-4 mb-3">
                            <div className="flex-1 min-w-0">
                              <h3 className="text-lg font-semibold text-gray-900 leading-snug mb-1.5">
                                {opportunity.title}
                              </h3>
                              <p className="text-sm text-gray-600 font-medium">{opportunity.funder}</p>
                            </div>
                            <div className="relative group flex-shrink-0">
                              <div className={`${colors.bg} text-white px-3.5 py-1.5 rounded-lg text-sm font-semibold cursor-pointer transition-all duration-200`}>
                                {opportunity.match_score}% Match
                              </div>
                              {/* Hover overlay with feedback buttons - positioned below */}
                              <div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10 flex items-center gap-1 p-1">
                                {rfpDbSuccessMessage[opportunity.id] ? (
                                  <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-green-600">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    Added
                                  </div>
                                ) : addingToRfpDb.has(opportunity.id) ? (
                                  <div className="px-3 py-1.5">
                                    <svg className="animate-spin h-4 w-4 text-perscholas-secondary" fill="none" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                  </div>
                                ) : (
                                  <>
                                    <button
                                      onClick={() => handleAddToRfpDb(opportunity.id)}
                                      className="p-2 hover:bg-green-50 rounded-md transition-colors"
                                      title="Good match - Add to training"
                                    >
                                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                      </svg>
                                    </button>
                                    <div className="w-px h-6 bg-gray-200"></div>
                                    <button
                                      onClick={() => handleDismiss(opportunity.id)}
                                      className="p-2 hover:bg-red-50 rounded-md transition-colors"
                                      title="Bad match - Remove"
                                    >
                                      <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                                      </svg>
                                    </button>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Key Metrics */}
                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div className="flex flex-col">
                              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Funding Amount</span>
                              <span className="text-lg font-bold text-green-600">{formatCurrency(opportunity.amount)}</span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Due Date</span>
                              <span className="text-lg font-bold text-gray-900">{formatDate(opportunity.deadline)}</span>
                            </div>
                          </div>

                          {/* Source Badge */}
                          {opportunity.source && (
                            <div className="mb-4">
                              <span className={`inline-flex items-center px-3 py-1.5 rounded-md text-xs font-semibold border ${getSourceBadge(opportunity.source)}`}>
                                {getSourceLabel(opportunity.source)}
                              </span>
                            </div>
                          )}

                          {/* Summary */}
                          {opportunity.llm_summary && (
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Summary</p>
                              <p className="text-sm text-gray-700 leading-relaxed">
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
                          <div className="flex flex-col sm:flex-row gap-2.5 pt-4 border-t border-gray-100">
                            <button
                              onClick={() => toggleExpanded(opportunity.id)}
                              className="flex-1 flex items-center justify-center gap-2 bg-perscholas-secondary text-white px-4 py-2.5 rounded-lg font-medium hover:bg-perscholas-primary transition-colors text-sm"
                            >
                              <svg className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                              {isExpanded ? 'Hide Details' : 'View Full Details'}
                            </button>
                            {opportunity.application_url && (
                              <a
                                href={opportunity.application_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-2 border border-gray-300 text-gray-700 px-4 py-2.5 rounded-lg font-medium hover:bg-gray-50 hover:border-gray-400 transition-colors text-sm"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                                Apply Now
                              </a>
                            )}
                            <button
                              onClick={() => handleDismiss(opportunity.id)}
                              disabled={dismissingOpportunities.has(opportunity.id)}
                              className="border border-red-200 text-red-600 px-4 py-2.5 rounded-lg font-medium hover:bg-red-50 hover:border-red-300 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {dismissingOpportunities.has(opportunity.id) ? (
                                <span className="flex items-center justify-center gap-2">
                                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                  Removing...
                                </span>
                              ) : (
                                'Remove'
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Expanded Analysis */}
                        {isExpanded && (
                          <div className="border-t border-gray-100 bg-gray-50 p-6 space-y-5">

                            {/* FULL DESCRIPTION - "About" Section */}
                            {opportunity.description && (
                              <div className="bg-white rounded-xl p-6 border border-gray-200">
                                <h4 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  About This Opportunity
                                </h4>
                                <div className="text-sm text-gray-700 leading-relaxed space-y-3">
                                  {opportunity.description.split('\n\n').map((para, idx) => (
                                    <p key={idx}>{para}</p>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* KEY DETAILS - Structured Information */}
                            <div className="bg-white rounded-xl p-6 border border-gray-200">
                              <h4 className="text-lg font-bold text-gray-900 mb-4">Key Details</h4>

                              <div className="space-y-6">

                                {/* Applicant Eligibility */}
                                {opportunity.eligibility_explanation && (
                                  <div className="border-l-4 border-perscholas-secondary pl-4">
                                    <h5 className="text-sm font-bold text-perscholas-dark mb-2">Applicant Eligibility</h5>
                                    <p className="text-sm text-gray-700">{opportunity.eligibility_explanation}</p>
                                  </div>
                                )}

                                {/* Required Registrations - Always show for federal grants */}
                                {opportunity.source === 'grants_gov' && (
                                  <div className="border-l-4 border-blue-500 pl-4">
                                    <h5 className="text-sm font-bold text-perscholas-dark mb-2">Required Registrations</h5>
                                    <ul className="text-sm text-gray-700 space-y-1">
                                      <li className="flex items-start gap-2">
                                        <span className="text-blue-600 font-bold">•</span>
                                        <span>Be registered in SAM prior to submission</span>
                                      </li>
                                      <li className="flex items-start gap-2">
                                        <span className="text-blue-600 font-bold">•</span>
                                        <span>Provide a valid UEI number in application</span>
                                      </li>
                                      <li className="flex items-start gap-2">
                                        <span className="text-blue-600 font-bold">•</span>
                                        <span>Obtain a CAGE Code</span>
                                      </li>
                                      <li className="flex items-start gap-2">
                                        <span className="text-blue-600 font-bold">•</span>
                                        <span>Maintain active SAM registration throughout award period</span>
                                      </li>
                                    </ul>
                                  </div>
                                )}

                                {/* Project Requirements */}
                                {opportunity.requirements && opportunity.requirements.length > 0 && (
                                  <div className="border-l-4 border-orange-500 pl-4">
                                    <h5 className="text-sm font-bold text-perscholas-dark mb-2">Project Requirements</h5>
                                    <ul className="text-sm text-gray-700 space-y-1">
                                      {opportunity.requirements.map((req: string, idx: number) => (
                                        <li key={idx} className="flex items-start gap-2">
                                          <span className="text-orange-600 font-bold">•</span>
                                          <span>{req}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Financing & Timeline */}
                                <div className="border-l-4 border-green-500 pl-4">
                                  <h5 className="text-sm font-bold text-perscholas-dark mb-2">Financing & Timeline Requirements</h5>
                                  <div className="space-y-2 text-sm">
                                    <div>
                                      <span className="font-semibold text-gray-600">Submission Deadline:</span>
                                      <span className="ml-2 text-gray-900 font-medium">{formatDate(opportunity.deadline)}</span>
                                    </div>
                                    {opportunity.award_floor && opportunity.award_ceiling && (
                                      <div>
                                        <span className="font-semibold text-gray-600">Award Range:</span>
                                        <span className="ml-2 text-gray-900">
                                          {formatCurrency(opportunity.award_floor)} - {formatCurrency(opportunity.award_ceiling)}
                                        </span>
                                      </div>
                                    )}
                                    {opportunity.expected_number_of_awards && (
                                      <div>
                                        <span className="font-semibold text-gray-600">Expected Awards:</span>
                                        <span className="ml-2 text-gray-900">{opportunity.expected_number_of_awards}</span>
                                      </div>
                                    )}
                                    {opportunity.cost_sharing !== undefined && (
                                      <div>
                                        <span className="font-semibold text-gray-600">Cost Sharing:</span>
                                        <span className={`ml-2 ${opportunity.cost_sharing ? 'text-orange-600' : 'text-green-600'} font-medium`}>
                                          {opportunity.cost_sharing ? 'Required' : 'Not Required'}
                                        </span>
                                        {opportunity.cost_sharing_description && (
                                          <p className="text-gray-600 mt-1">{opportunity.cost_sharing_description}</p>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </div>

                                {/* Additional Information */}
                                {opportunity.additional_info_text && (
                                  <div className="border-l-4 border-purple-500 pl-4">
                                    <h5 className="text-sm font-bold text-perscholas-dark mb-2">Additional Information</h5>
                                    <p className="text-sm text-gray-700">{opportunity.additional_info_text}</p>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* TIMELINE */}
                            {(opportunity.forecast_date || opportunity.deadline || opportunity.archive_date) && (
                              <div className="bg-white rounded-xl p-6 border border-gray-200">
                                <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                  </svg>
                                  Timeline
                                </h4>
                                <div className="space-y-3">
                                  {opportunity.forecast_date && (
                                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                      <span className="text-sm font-medium text-gray-600">FOA Selection Period Opens</span>
                                      <span className="text-sm font-bold text-gray-900">{formatDate(opportunity.forecast_date)}</span>
                                    </div>
                                  )}
                                  {opportunity.deadline && (
                                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                      <span className="text-sm font-medium text-gray-600">Final Application Deadline</span>
                                      <span className="text-sm font-bold text-perscholas-accent">{formatDate(opportunity.deadline)}</span>
                                    </div>
                                  )}
                                  {opportunity.archive_date && (
                                    <div className="flex justify-between items-center py-2">
                                      <span className="text-sm font-medium text-gray-600">Archive Date</span>
                                      <span className="text-sm font-bold text-gray-900">{formatDate(opportunity.archive_date)}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* CONTACTS */}
                            {(opportunity.contact || opportunity.contact_name || opportunity.contact_phone) && (
                              <div className="bg-white rounded-xl p-6 border border-gray-200">
                                <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                  </svg>
                                  Contacts
                                </h4>
                                <div className="space-y-2 text-sm">
                                  {opportunity.contact_name && (
                                    <div>
                                      <span className="font-semibold text-gray-600">Name:</span>
                                      <span className="ml-2 text-gray-900">{opportunity.contact_name}</span>
                                    </div>
                                  )}
                                  {opportunity.contact_phone && (
                                    <div>
                                      <span className="font-semibold text-gray-600">Phone:</span>
                                      <a href={`tel:${opportunity.contact_phone}`} className="ml-2 text-perscholas-secondary hover:underline">
                                        {opportunity.contact_phone}
                                      </a>
                                    </div>
                                  )}
                                  {opportunity.contact && (
                                    <div>
                                      <span className="font-semibold text-gray-600">Email:</span>
                                      <a href={`mailto:${opportunity.contact}`} className="ml-2 text-perscholas-secondary hover:underline">
                                        {opportunity.contact}
                                      </a>
                                    </div>
                                  )}
                                  {opportunity.contact_description && (
                                    <p className="text-gray-600 mt-2">{opportunity.contact_description}</p>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* ATTACHMENTS */}
                            {opportunity.attachments && opportunity.attachments.length > 0 && (
                              <div className="bg-white rounded-xl p-6 border border-gray-200">
                                <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                                  </svg>
                                  Attachments
                                </h4>
                                <div className="space-y-2">
                                  {opportunity.attachments.map((attachment, idx) => (
                                    <a
                                      key={idx}
                                      href={attachment.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                                    >
                                      <div className="bg-perscholas-secondary p-2 rounded">
                                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                      </div>
                                      <div className="flex-1">
                                        <p className="text-sm font-semibold text-gray-900">{attachment.title}</p>
                                        <p className="text-xs text-gray-500 uppercase">{attachment.type}</p>
                                      </div>
                                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                      </svg>
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}

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

                            {/* Structured LLM Insights */}
                            {(opportunity.winning_strategies?.length > 0 ||
                              opportunity.key_themes?.length > 0 ||
                              opportunity.recommended_metrics?.length > 0 ||
                              opportunity.considerations?.length > 0) && (
                              <div className="mb-6 space-y-4">
                                {/* Winning Strategies */}
                                {opportunity.winning_strategies?.length > 0 && (
                                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-5 border border-green-200">
                                    <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                      </svg>
                                      Winning Strategies from Similar Proposals
                                    </h4>
                                    <ul className="space-y-2">
                                      {opportunity.winning_strategies.map((strategy, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-gray-800 leading-relaxed">
                                          <span className="flex-shrink-0 text-green-600 font-bold">•</span>
                                          <span>{strategy}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Key Themes */}
                                {opportunity.key_themes?.length > 0 && (
                                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-5 border border-blue-200">
                                    <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                      <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                                      </svg>
                                      Key Themes to Incorporate
                                    </h4>
                                    <ul className="space-y-2">
                                      {opportunity.key_themes.map((theme, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-gray-800 leading-relaxed">
                                          <span className="flex-shrink-0 text-blue-600 font-bold">•</span>
                                          <span>{theme}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Recommended Metrics */}
                                {opportunity.recommended_metrics?.length > 0 && (
                                  <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-5 border border-purple-200">
                                    <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                      <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                      </svg>
                                      Recommended Metrics to Highlight
                                    </h4>
                                    <ul className="space-y-2">
                                      {opportunity.recommended_metrics.map((metric, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-gray-800 leading-relaxed">
                                          <span className="flex-shrink-0 text-purple-600 font-bold">•</span>
                                          <span>{metric}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Considerations */}
                                {opportunity.considerations?.length > 0 && (
                                  <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-5 border border-amber-200">
                                    <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                      <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                      </svg>
                                      Important Considerations
                                    </h4>
                                    <ul className="space-y-2">
                                      {opportunity.considerations.map((consideration, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-gray-800 leading-relaxed">
                                          <span className="flex-shrink-0 text-amber-600 font-bold">•</span>
                                          <span>{consideration}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
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

                            {/* Similar RFPs Section */}
                            {opportunity.similar_past_proposals && opportunity.similar_past_proposals.length > 0 ? (
                              <div className="bg-white rounded-xl p-5 border border-gray-200">
                                <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                  </svg>
                                  Similar Past RFPs
                                </h4>
                                <p className="text-xs text-gray-600 mb-4">
                                  Historical proposals similar to this opportunity based on semantic analysis:
                                </p>
                                <div className="space-y-3">
                                  {opportunity.similar_past_proposals.map((rfp: any, idx: number) => (
                                    <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-perscholas-secondary transition-colors">
                                      <div className="flex items-start justify-between gap-3 mb-2">
                                        <h5 className="text-sm font-semibold text-gray-900 flex-1">
                                          {rfp.title || 'Untitled Proposal'}
                                        </h5>
                                        <div className="flex items-center gap-2">
                                          {rfp.similarity_score && (
                                            <span className="text-xs font-bold text-perscholas-secondary bg-blue-50 px-2 py-1 rounded-md">
                                              {Math.round(rfp.similarity_score * 100)}% match
                                            </span>
                                          )}
                                          {rfp.id && (
                                            <a
                                              href={`${api.baseURL}/api/proposals/${rfp.id}/download`}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="text-xs font-medium text-perscholas-secondary hover:text-perscholas-dark flex items-center gap-1 px-2 py-1 rounded-md hover:bg-blue-50 transition-colors"
                                            >
                                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                              </svg>
                                              View PDF
                                            </a>
                                          )}
                                        </div>
                                      </div>
                                      {rfp.category && (
                                        <p className="text-xs text-gray-600 mb-1">
                                          <span className="font-medium">Category:</span> {rfp.category}
                                        </p>
                                      )}
                                      {rfp.rfp_name && (
                                        <p className="text-xs text-gray-600 mb-1">
                                          <span className="font-medium">RFP:</span> {rfp.rfp_name}
                                        </p>
                                      )}
                                      {rfp.outcome && (
                                        <p className="text-xs text-gray-600 mb-1">
                                          <span className="font-medium">Outcome:</span>
                                          <span className={`ml-1 font-semibold ${rfp.outcome === 'won' ? 'text-green-600' : 'text-gray-500'}`}>
                                            {rfp.outcome === 'won' ? '✓ Won' : rfp.outcome}
                                          </span>
                                        </p>
                                      )}
                                      {rfp.award_amount && (
                                        <p className="text-xs text-gray-600">
                                          <span className="font-medium">Award Amount:</span> {formatCurrency(rfp.award_amount)}
                                        </p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <div className="bg-blue-50 rounded-xl p-5 border border-blue-200">
                                <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
                                  <svg className="w-5 h-5 text-perscholas-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                  </svg>
                                  Similar Past RFPs
                                </h4>
                                <p className="text-sm text-gray-700">
                                  No similar historical RFPs found yet. As you save more opportunities, our semantic analysis will identify patterns and surface relevant past proposals.
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-center gap-1 sm:gap-2 flex-wrap">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-3 sm:px-4 py-2 rounded-lg border border-gray-200 bg-white text-xs sm:text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>

                  <div className="flex items-center gap-1">
                    {pageStart > 1 && (
                      <>
                        <button onClick={() => setCurrentPage(1)} className="px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">1</button>
                        {pageStart > 2 && <span className="px-1 sm:px-2 text-gray-400 text-xs sm:text-sm">…</span>}
                      </>
                    )}
                    {pages.map(p => (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium border transition-colors ${
                          p === currentPage
                            ? 'bg-perscholas-secondary text-white border-perscholas-secondary shadow-md'
                            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                    {pageEnd < totalPages - 1 && <span className="px-1 sm:px-2 text-gray-400 text-xs sm:text-sm">…</span>}
                    {pageEnd < totalPages && (
                      <button onClick={() => setCurrentPage(totalPages)} className="px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">{totalPages}</button>
                    )}
                  </div>

                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    className="px-3 sm:px-4 py-2 rounded-lg border border-gray-200 bg-white text-xs sm:text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Upload RFP Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold text-gray-900">Upload RFP Document</h3>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setUploadResult(null)
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {!uploadResult ? (
              <form onSubmit={handleUploadRfp} className="space-y-6">
                <div>
                  <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                    PDF Document
                  </label>
                  <input
                    type="file"
                    id="file"
                    name="file"
                    accept=".pdf"
                    required
                    className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent p-2"
                  />
                  <p className="mt-1 text-xs text-gray-500">Upload an RFP PDF for AI analysis</p>
                </div>

                <div>
                  <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                    Title (Optional)
                  </label>
                  <input
                    type="text"
                    id="title"
                    name="title"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                    placeholder="AI will extract if not provided"
                  />
                </div>

                <div>
                  <label htmlFor="funder" className="block text-sm font-medium text-gray-700 mb-2">
                    Funder (Optional)
                  </label>
                  <input
                    type="text"
                    id="funder"
                    name="funder"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                    placeholder="AI will extract if not provided"
                  />
                </div>

                <div>
                  <label htmlFor="deadline" className="block text-sm font-medium text-gray-700 mb-2">
                    Deadline (Optional)
                  </label>
                  <input
                    type="date"
                    id="deadline"
                    name="deadline"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowUploadModal(false)
                      setUploadResult(null)
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploadingRfp}
                    className="flex-1 px-4 py-2 bg-perscholas-secondary text-white rounded-lg hover:bg-perscholas-dark transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {uploadingRfp ? (
                      <>
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Analyzing...
                      </>
                    ) : (
                      'Upload & Analyze'
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="flex-1">
                      <h4 className="font-bold text-green-900 mb-1">RFP Analyzed Successfully!</h4>
                      <p className="text-sm text-green-800">{uploadResult.message}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Title</p>
                    <p className="text-sm font-semibold text-gray-900">{uploadResult.title}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Funder</p>
                    <p className="text-sm font-semibold text-gray-900">{uploadResult.funder}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Match Score</p>
                    <p className="text-2xl font-bold text-perscholas-secondary">{uploadResult.match_score}%</p>
                  </div>
                  {uploadResult.llm_summary && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase mb-1">AI Summary</p>
                      <p className="text-sm text-gray-700">{uploadResult.llm_summary}</p>
                    </div>
                  )}
                  {uploadResult.tags && uploadResult.tags.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase mb-2">Tags</p>
                      <div className="flex flex-wrap gap-2">
                        {uploadResult.tags.map((tag: string, idx: number) => (
                          <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => {
                    setShowUploadModal(false)
                    setUploadResult(null)
                  }}
                  className="w-full px-4 py-2 bg-perscholas-secondary text-white rounded-lg hover:bg-perscholas-dark transition-colors font-medium"
                >
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}

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
