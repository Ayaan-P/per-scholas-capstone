'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
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
  const itemsPerPage = 12
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    fetchGrants()
  }, [])

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

  // Reset page to 1 when any filter/sort/raw data changes
  useEffect(() => {
    setCurrentPage(1)
  }, [rawGrants, filter, keywordSearch, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy])

  const fetchGrants = async () => {
    try {
      setLoading(true)
      // Fetch all scraped grants and apply client-side filters
      const response = await api.getScrapedGrants({ limit: 200 })

      if (response.ok) {
        const data = await response.json()
        const fetched: ScrapedGrant[] = data.grants || []
        // store raw grants for client-side filtering
        setRawGrants(fetched)
      }
    } catch (error) {
      console.error('Failed to fetch grants:', error)
    } finally {
      setLoading(false)
    }
  }

  // Compute filtered + sorted grants on demand (no duplicate state)
  const filteredGrants = useMemo(() => {
    let list = [...rawGrants]

    if (filter !== 'all') list = list.filter(g => g.source === filter)

    // Apply keyword search filter
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
        // remove from rawGrants so it won't appear in filtered results
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

  // Pagination calculations
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading grant opportunities...</p>
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
              Discover Grant Opportunities
            </h2>
            <p className="text-gray-600">
              AI-powered funding discovery. We surface opportunities matched to your organization automatically.
              Use filters to narrow results and save opportunities to your pipeline.
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            {/* Total Opportunities */}
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Opportunities</p>
              <p className="text-3xl font-bold text-gray-900">{filteredGrants.length}</p>
              <p className="text-sm text-gray-500 mt-1">Discovered</p>
            </div>

            {/* Total Funding */}
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Funding</p>
              <p className="text-3xl font-bold text-green-600">{formatCurrency(filteredGrants.reduce((sum, g) => sum + (g.amount || 0), 0))}</p>
              <p className="text-sm text-gray-500 mt-1">Available</p>
            </div>

            {/* High Match Count */}
            <div>
              <p className="text-sm text-gray-500 mb-1">High Match</p>
              <p className="text-3xl font-bold" style={{ color: '#fec14f' }}>{filteredGrants.filter(g => g.match_score >= 85).length}</p>
              <p className="text-sm text-gray-500 mt-1">≥ 85% fit</p>
            </div>

            {/* High Match Funding */}
            <div>
              <p className="text-sm text-gray-500 mb-1">High Match Funding</p>
              <p className="text-3xl font-bold" style={{ color: '#fec14f' }}>
                {formatCurrency(filteredGrants.filter(g => g.match_score >= 85).reduce((sum, g) => sum + (g.amount || 0), 0))}
              </p>
              <p className="text-sm text-gray-500 mt-1">≥ 85% fit</p>
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
                    Searching across grant content...
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

          {/* Main content - Grant List */}
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
            {filteredGrants.length === 0 ? (
              <div className="bg-white rounded-xl shadow-md border border-gray-200 p-16 text-center max-w-4xl mx-auto">
                <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">No grants found</h3>
                <p className="text-gray-600 text-lg">The automated scraper is running. Check back soon for new opportunities.</p>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto w-full">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {paged.map((grant) => (
                    <div key={grant.id} className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-white flex flex-col h-full">
                      <div className="mb-3">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1 pr-3 min-w-0">
                            <h3 className="text-base font-semibold text-gray-900 mb-1 line-clamp-2 leading-tight">{grant.title}</h3>
                          </div>
                          <div className="flex flex-col items-end space-y-1.5 flex-shrink-0">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getMatchColor(grant.match_score)}`}
                              title="Match score"
                            >
                              {grant.match_score}%
                            </span>
                            <div className="text-lg font-bold text-green-600">
                              {formatCurrency(grant.amount)}
                            </div>
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <div className="text-xs text-gray-600 font-medium truncate">{grant.funder}</div>
                          <div className="text-xs text-gray-500 flex-shrink-0 ml-3">
                            <span className="font-medium">Due:</span> {formatDate(grant.deadline)}
                          </div>
                        </div>
                      </div>

                      <div className="bg-gray-50 p-3 rounded-lg mb-3 flex-grow">
                        <p className="text-xs text-gray-700 leading-relaxed line-clamp-3">{grant.description}</p>
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                        <div className="flex items-center gap-2 text-xs text-gray-500 min-w-0">
                          {grant.source && (
                            <span className={`px-2 py-0.5 rounded-full text-xs ${getSourceBadge(grant.source)}`}>
                              {getSourceLabel(grant.source)}
                            </span>
                          )}
                          <span className="truncate">Added {formatDate(grant.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {grant.application_url && (
                            <a
                              href={grant.application_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="border border-perscholas-primary text-perscholas-primary px-4 py-1.5 rounded-full text-xs font-medium hover:bg-gray-50 transition-colors whitespace-nowrap"
                            >
                              Learn More
                            </a>
                          )}
                          <button
                            onClick={() => handleSaveGrant(grant.id)}
                            disabled={savingGrants.has(grant.id)}
                            className="bg-perscholas-primary text-white px-4 py-1.5 rounded-full text-xs font-medium hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                          >
                            {savingGrants.has(grant.id) ? 'Saving...' : 'Save'}
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
                    onClick={() => setCurrentPage(p => Math.min(Math.max(1, Math.ceil(filteredGrants.length / itemsPerPage)), p + 1))}
                    disabled={currentPage >= Math.ceil(filteredGrants.length / itemsPerPage)}
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
