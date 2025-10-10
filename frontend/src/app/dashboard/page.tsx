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
  const [selectedStates, setSelectedStates] = useState<string[]>([])
  const [highMatchOnly, setHighMatchOnly] = useState(false)
  const [fundingMin, setFundingMin] = useState<number | undefined>(undefined)
  const [fundingMax, setFundingMax] = useState<number | undefined>(undefined)
  const [dueInDays, setDueInDays] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState<'match' | 'amount' | 'deadline'>('match')
  const [savingGrants, setSavingGrants] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 12

  useEffect(() => {
    fetchGrants()
  }, [])

  // Re-apply filters/sorting whenever raw data or filter controls change
  // Also reset to page 1 whenever a filter/sort/raw data changes
  // Reset page to 1 when any filter/sort/raw data changes
  useEffect(() => {
    setCurrentPage(1)
  }, [rawGrants, filter, selectedStates, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy])

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

    if (selectedStates.length > 0) {
      const lowerStates = selectedStates.map(s => s.toLowerCase())
      list = list.filter(g => {
        const text = `${g.description || ''} ${g.contact || ''}`.toLowerCase()
        return lowerStates.some(s => text.includes(s) || (g.funder || '').toLowerCase().includes(s))
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
  }, [rawGrants, filter, selectedStates, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy])

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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading grant opportunities...</p>
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
            <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 mb-4">Discover Grant Opportunities</h1>
            <p className="max-w-3xl mx-auto text-lg md:text-xl text-slate-700 mb-6 leading-relaxed">
              We surface funding opportunities matched to your organization automatically. Results refresh periodically —
              use the filters to narrow results, sort by match or funding, and save opportunities to your pipeline.
            </p>
            {/* Buttons removed as requested */}
            <p className="text-sm text-gray-500 mt-6">Tip: try "High match only" to surface the best-fit opportunities first.</p>
          </div>
        </div>

        {/* Stats Bar */}
  <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6 mb-8 w-full">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 items-stretch">
            {/* Total Opportunities */}
            <div className="bg-indigo-50/60 rounded-lg p-4 flex flex-col justify-center items-center md:items-start border border-transparent">
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wider mb-1">Total Opportunities</p>
              <p className="text-2xl md:text-3xl font-extrabold text-slate-900">{filteredGrants.length}</p>
              <p className="text-sm text-slate-500 mt-1">Opportunities discovered</p>
            </div>

            {/* Total Funding */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-indigo-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Total Funding</p>
              <p className="text-2xl md:text-3xl font-extrabold text-indigo-700">{formatCurrency(filteredGrants.reduce((sum, g) => sum + (g.amount || 0), 0))}</p>
              <p className="text-sm text-slate-500 mt-1">Across all displayed opportunities</p>
            </div>

            {/* High Match Count */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-green-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">High Match</p>
              <p className="text-2xl md:text-3xl font-extrabold text-green-600">{filteredGrants.filter(g => g.match_score >= 85).length}</p>
              <p className="text-sm text-slate-500 mt-1">Opportunities ≥ 85% match</p>
            </div>

            {/* High-match Funding */}
            <div className="bg-white rounded-lg p-4 flex flex-col justify-center items-center md:items-start border-l-4 border-green-100 pl-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">High-match Funding</p>
              <p className="text-2xl md:text-3xl font-extrabold text-green-600">{formatCurrency(filteredGrants.filter(g => g.match_score >= 85).reduce((sum, g) => sum + (g.amount || 0), 0))}</p>
              <p className="text-sm text-slate-500 mt-1">Funding for top-fit opportunities</p>
            </div>

          </div>
        </div>

        <div className="lg:flex lg:items-start lg:space-x-8">
          {/* Left sidebar - Filters */}
          <aside className="w-full lg:w-72 flex-shrink-0">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Filter by source</h4>
              <div className="mb-4">
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

              <h4 className="text-sm font-semibold text-gray-700 mb-2">Filter by state</h4>
              <p className="text-xs text-gray-500 mb-2">Type state abbreviations or names, comma separated</p>
              <input
                value={selectedStates.join(', ')}
                onChange={(e) => setSelectedStates(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm mb-4 focus:ring-1 focus:ring-indigo-100"
                placeholder="e.g. CA, NY, Texas"
              />

              <label className="flex items-center space-x-2 text-sm mb-3">
                <input type="checkbox" checked={highMatchOnly} onChange={(e) => setHighMatchOnly(e.target.checked)} className="h-4 w-4" />
                <span className="text-gray-700">High match only (85%+)</span>
              </label>

              <div className="mb-2 text-sm font-medium text-gray-700">Funding range</div>
              <div className="grid grid-cols-2 gap-2 mb-3">
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

              <div className="mb-4">
                <label className="text-sm font-medium text-gray-700">Due in (days)</label>
                <input
                  type="number"
                  value={dueInDays ?? ''}
                  onChange={(e) => setDueInDays(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-md text-sm"
                  placeholder="e.g. 30"
                />
              </div>

              {/* Sort moved to top-right of results */}
            </div>

            {/* Optional: other sidebar content (legend, tips) */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 text-sm text-slate-600">
              Tip: click a grant to view details or use Save to add it to your pipeline.
            </div>
          </aside>

          {/* Main content - Grant List */}
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
                    <div key={grant.id} className={`bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-lg hover:border-indigo-300 transition-all duration-200 ${grant.match_score >= 85 ? 'border-l-4 border-green-200 pl-5' : ''}`}>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1 pr-4">
                          <h3 className="text-lg font-semibold text-gray-900 mb-1 line-clamp-2">{grant.title}</h3>
                          <p className="text-sm text-gray-600 font-medium">{grant.funder}</p>
                        </div>
                        <div className="flex flex-col items-end space-y-1">
                          <span
                            className={`px-3 py-1 rounded-md text-xs font-bold ${getMatchColor(grant.match_score)}`}
                            title="Estimated match score"
                            aria-label={`Approximate match ${grant.match_score} percent`}
                          >
                            ≈{grant.match_score}%
                          </span>
                          <p className="text-xl font-bold text-indigo-700">
                            {formatCurrency(grant.amount)}
                          </p>
                          <p className="text-xs text-gray-500 font-medium">{formatDate(grant.deadline)}</p>
                        </div>
                      </div>

                      <p className="text-sm text-gray-700 mb-3 leading-relaxed line-clamp-3">{grant.description}</p>

                      <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 rounded-md text-xs font-bold ${getSourceBadge(grant.source)}`}>
                            {getSourceLabel(grant.source)}
                          </span>
                          <span className="text-xs text-gray-500">{formatDate(grant.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <a
                            href={grant.application_url}
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
                            onClick={() => handleSaveGrant(grant.id)}
                            disabled={savingGrants.has(grant.id)}
                            className="px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-md hover:shadow-lg text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
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
    </div>
  )
}
