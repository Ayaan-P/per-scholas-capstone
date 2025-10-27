'use client'

import { useState, useEffect, useMemo } from 'react'
import { api } from '../../utils/api'

interface ScrapedGrant {
  id: string
  opportunity_id: string
  title: string
  funder: string
  amount: number
  deadline: string
  match_score: number
  description: string
  requirements: any[]
  contact: string
  application_url: string
  source: string
  status: string
  created_at: string
  updated_at: string
}

export default function Dashboard() {
  const [rawGrants, setRawGrants] = useState<ScrapedGrant[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [keywordSearch, setKeywordSearch] = useState<string>('')
  const [highMatchOnly, setHighMatchOnly] = useState(false)
  const [fundingMin, setFundingMin] = useState<number | undefined>(undefined)
  const [fundingMax, setFundingMax] = useState<number | undefined>(undefined)
  const [dueInDays, setDueInDays] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState<'match' | 'amount' | 'deadline'>('match')
  const [savingGrants, setSavingGrants] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 9
  const [showBackToTop, setShowBackToTop] = useState(false)
  const [selectedDescription, setSelectedDescription] = useState<{ title: string; description: string } | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)

  useEffect(() => {
    fetchGrants()
  }, [])

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

  useEffect(() => {
    setCurrentPage(1)
  }, [rawGrants, filter, keywordSearch, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy])

  const fetchGrants = async () => {
    try {
      setLoading(true)
      const response = await api.getScrapedGrants()

      if (response.ok) {
        const data = await response.json()
        const fetched: ScrapedGrant[] = data.grants || []
        // Filter to only show Grants.gov grants
        const filteredGrants = fetched.filter(grant => grant.source === 'grants_gov')
        setRawGrants(filteredGrants)
      }
    } catch (error) {
      console.error('Failed to fetch grants:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredGrants = useMemo(() => {
    let list = [...rawGrants]

    if (filter !== 'all') list = list.filter(g => g.source === filter)

    if (keywordSearch.trim()) {
      const keywords = keywordSearch.toLowerCase().trim()
      list = list.filter(g => {
        const searchText = `${g.title || ''} ${g.description || ''} ${g.funder || ''} ${g.contact || ''}`.toLowerCase()
        return searchText.includes(keywords)
      })
    }

    if (highMatchOnly) list = list.filter(g => g.match_score >= 85)

    if (fundingMin !== undefined) list = list.filter(g => (g.amount || 0) >= (fundingMin || 0))
    if (fundingMax !== undefined) list = list.filter(g => (g.amount || 0) <= (fundingMax || 0))

    if (dueInDays !== undefined) {
      const now = new Date()
      const maxDate = new Date(now.getTime() + (dueInDays * 24 * 60 * 60 * 1000))
      list = list.filter(g => {
        if (!g.deadline) return false
        const d = new Date(g.deadline)
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
  }, [rawGrants, filter, keywordSearch, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy])

  const handleSaveGrant = async (grantId: string) => {
    try {
      setSavingGrants(prev => new Set(prev).add(grantId))
      const response = await api.saveScrapedGrant(grantId)

      if (response.ok) {
        const data = await response.json()
        setRawGrants(prev => prev.filter(g => g.id !== grantId))
        if (data.status === 'already_saved') {
          alert(data.message)
        } else {
          alert('Grant saved to your pipeline!')
        }
      } else {
        alert('Failed to save grant')
      }
    } catch (error) {
      console.error('Failed to save grant:', error)
      alert('Failed to save grant')
    } finally {
      setSavingGrants(prev => {
        const next = new Set(prev)
        next.delete(grantId)
        return next
      })
    }
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

  const getMatchColor = (score: number) => {
    if (score >= 85) return 'bg-green-600'
    if (score >= 70) return 'bg-perscholas-accent'
    return 'bg-gray-400'
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

  const totalPages = Math.max(1, Math.ceil(filteredGrants.length / itemsPerPage))
  const startIndex = (currentPage - 1) * itemsPerPage
  const paged = filteredGrants.slice(startIndex, startIndex + itemsPerPage)
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
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm animate-pulse">
                    <div className="h-6 bg-gray-200 rounded w-3/4 mb-3"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                    <div className="space-y-2 mb-4">
                      <div className="h-3 bg-gray-200 rounded"></div>
                      <div className="h-3 bg-gray-200 rounded"></div>
                      <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                    </div>
                    <div className="h-10 bg-gray-200 rounded"></div>
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
            <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
              <div className="bg-perscholas-primary p-2 sm:p-2.5 rounded-xl">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                Discover Funding
              </h2>
            </div>
            <p className="text-gray-600 text-base sm:text-lg">
              Browse opportunities matched to your organization. Save promising grants to unlock AI-powered insights.
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 sm:mb-8 grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm hover:shadow-lg hover:border-blue-200 hover:-translate-y-1 transition-all duration-300 cursor-pointer animate-fadeIn" style={{ animationDelay: '100ms' }}>
            <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1 sm:mb-2">Opportunities</p>
            <p className="text-2xl sm:text-3xl font-bold text-gray-900">{filteredGrants.length}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm hover:shadow-lg hover:border-green-200 hover:-translate-y-1 transition-all duration-300 cursor-pointer animate-fadeIn" style={{ animationDelay: '150ms' }}>
            <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1 sm:mb-2">High Match $</p>
            <p className="text-xl sm:text-3xl font-bold text-green-600 truncate">
              {formatCurrency(filteredGrants.filter(g => g.match_score >= 85).reduce((sum, g) => sum + (g.amount || 0), 0))}
            </p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm hover:shadow-lg hover:border-yellow-200 hover:-translate-y-1 transition-all duration-300 cursor-pointer animate-fadeIn" style={{ animationDelay: '200ms' }}>
            <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1 sm:mb-2">High Match</p>
            <p className="text-2xl sm:text-3xl font-bold text-perscholas-accent">{filteredGrants.filter(g => g.match_score >= 85).length}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm hover:shadow-lg hover:border-purple-200 hover:-translate-y-1 transition-all duration-300 cursor-pointer animate-fadeIn" style={{ animationDelay: '250ms' }}>
            <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1 sm:mb-2">Avg Match Score</p>
            <p className="text-2xl sm:text-3xl font-bold text-perscholas-secondary">
              {filteredGrants.length > 0
                ? Math.round(filteredGrants.reduce((sum, g) => sum + (g.match_score || 0), 0) / filteredGrants.length)
                : 0}%
            </p>
          </div>
        </div>

        {/* Mobile Filter Button */}
        <div className="lg:hidden mb-4 animate-fadeIn" style={{ animationDelay: '300ms' }}>
          <button
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className="w-full flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md hover:border-perscholas-primary/30 active:scale-98 transition-all"
          >
            <div className="flex items-center gap-2">
              <div className="relative">
                <svg className="w-5 h-5 text-perscholas-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
              {/* Filters Card */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-perscholas-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  Quick Filters
                </h3>

                <div className="space-y-4">
                  {/* High Match Toggle */}
                  <label className="flex items-center justify-between p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors">
                    <span className="text-sm font-medium text-gray-700">High Match Only</span>
                    <input
                      type="checkbox"
                      checked={highMatchOnly}
                      onChange={(e) => setHighMatchOnly(e.target.checked)}
                      className="w-4 h-4 text-perscholas-primary rounded focus:ring-2 focus:ring-perscholas-primary/20"
                    />
                  </label>

                  {/* Source Filter */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Source</label>
                    <select
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary bg-white"
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

                  {/* Keyword Search */}
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
                        className="w-full pl-10 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary"
                        placeholder="Keywords..."
                      />
                    </div>
                  </div>

                  {/* Funding Range */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Funding Range</label>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        value={fundingMin ?? ''}
                        onChange={(e) => setFundingMin(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Min"
                        className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary"
                      />
                      <input
                        type="number"
                        value={fundingMax ?? ''}
                        onChange={(e) => setFundingMax(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Max"
                        className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary"
                      />
                    </div>
                  </div>

                  {/* Due Date */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Due Within (days)</label>
                    <input
                      type="number"
                      value={dueInDays ?? ''}
                      onChange={(e) => setDueInDays(e.target.value ? Number(e.target.value) : undefined)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary"
                      placeholder="e.g. 30"
                    />
                  </div>

                  {/* Sort */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-2 block">Sort By</label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary bg-white"
                    >
                      <option value="match">Match Score</option>
                      <option value="amount">Funding Amount</option>
                      <option value="deadline">Due Date</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Tips */}
              <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
                <div className="flex items-start gap-3">
                  <div className="bg-perscholas-secondary p-1.5 rounded-lg flex-shrink-0">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-perscholas-dark mb-1">Discovery Tips</p>
                    <p className="text-xs text-gray-700 leading-relaxed">
                      Save grants to unlock AI insights, match reasoning, and semantic analysis of past RFPs.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {filteredGrants.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-20 text-center">
                <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-2xl flex items-center justify-center">
                  <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">No opportunities found</h3>
                <p className="text-gray-600 text-lg">Try adjusting your filters or check back soon for new grants.</p>
              </div>
            ) : (
              <div>
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5 mb-8">
                  {paged.map((grant, index) => (
                    <div
                      key={grant.id}
                      className="group bg-white border border-gray-200 rounded-xl p-5 hover:shadow-xl hover:border-perscholas-primary/50 hover:-translate-y-1 transition-all duration-300 h-full flex flex-col animate-fadeIn"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      {/* Title Row with Match Score */}
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-base font-bold text-gray-900 mb-1 line-clamp-2 leading-tight group-hover:text-perscholas-primary transition-colors">
                            {grant.title}
                          </h3>
                          <p className="text-xs text-gray-600 truncate">{grant.funder}</p>
                        </div>
                        <div className={`flex-shrink-0 ${getMatchColor(grant.match_score)} text-white px-3 py-1.5 rounded-full text-xs font-bold shadow-sm`}>
                          {grant.match_score}%
                        </div>
                      </div>

                      {/* Key Metrics Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 mb-3 p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="text-xs text-gray-500 mb-0.5">Funding</p>
                          <p className="text-sm font-bold text-green-600">{formatCurrency(grant.amount)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 mb-0.5">Deadline</p>
                          <p className="text-sm font-bold text-gray-900">{formatDate(grant.deadline)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 mb-0.5">Source</p>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getSourceBadge(grant.source)}`}>
                            {getSourceLabel(grant.source)}
                          </span>
                        </div>
                      </div>

                      {/* Description */}
                      <div className="mb-3 flex-grow">
                        <p className="text-xs text-gray-600 leading-relaxed line-clamp-3">
                          {grant.description}
                        </p>
                        {grant.description && grant.description.length > 200 && (
                          <button
                            onClick={() => setSelectedDescription({ title: grant.title, description: grant.description })}
                            className="text-xs text-perscholas-primary font-medium hover:text-perscholas-dark mt-1.5 inline-flex items-center gap-1 group"
                          >
                            Read full description
                            <svg className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </button>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                        {grant.application_url && (
                          <a
                            href={grant.application_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 text-center border-2 border-gray-300 text-gray-700 px-3 py-2.5 sm:py-2 rounded-lg text-xs font-semibold hover:border-gray-400 hover:bg-gray-50 transition-colors"
                          >
                            View RFP
                          </a>
                        )}
                        <button
                          onClick={() => handleSaveGrant(grant.id)}
                          disabled={savingGrants.has(grant.id)}
                          className="flex-1 bg-perscholas-primary text-white px-3 py-2.5 sm:py-2 rounded-lg text-xs font-semibold hover:bg-perscholas-dark hover:scale-105 hover:shadow-md active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                        >
                          {savingGrants.has(grant.id) ? (
                            <span className="flex items-center justify-center gap-2">
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Saving...
                            </span>
                          ) : (
                            <span className="flex items-center justify-center gap-2">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                              Save
                            </span>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
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
                            ? 'bg-perscholas-primary text-white border-perscholas-primary shadow-md'
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

      {/* Back to Top */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 bg-perscholas-primary text-white p-4 rounded-full shadow-2xl hover:shadow-xl hover:scale-110 transition-all duration-300 z-40 group"
          aria-label="Back to top"
        >
          <svg className="w-5 h-5 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      )}

      {/* Description Modal */}
      {selectedDescription && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setSelectedDescription(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col animate-scaleIn"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-5 flex items-start justify-between">
              <div className="flex-1 pr-4">
                <h3 className="text-lg font-semibold text-gray-900 leading-snug">{selectedDescription.title}</h3>
                <p className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Full Description</p>
              </div>
              <button
                onClick={() => setSelectedDescription(null)}
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded-lg"
                aria-label="Close"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
              <div className="bg-white rounded-lg p-6 border border-gray-200">
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {selectedDescription.description}
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 bg-white px-6 py-4 flex justify-end">
              <button
                onClick={() => setSelectedDescription(null)}
                className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
