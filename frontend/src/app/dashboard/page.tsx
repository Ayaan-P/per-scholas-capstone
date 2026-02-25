'use client'

export const dynamic = 'force-dynamic'

import { useState, useEffect, useMemo } from 'react'
import { api } from '../../utils/api'
import { useAuth } from '../../context/AuthContext'

interface ScrapedGrant {
  id: string
  opportunity_id: string
  title: string
  funder: string
  amount: number
  deadline: string
  match_score: number
  description: string
  requirements: string[]
  contact: string
  application_url: string
  source: string
  status: string
  org_status?: string        // Pipeline status in org_grants (active, saved, in_progress, submitted, won, lost)
  org_grant_id?: string      // org_grants row id
  created_at: string
  updated_at: string
  posted_date?: string
  category_id?: number
}

// Pipeline status config
const PIPELINE_STATUSES = [
  { value: 'active',      label: 'Active',       emoji: '📋', color: 'text-gray-600 bg-gray-100 border-gray-200' },
  { value: 'saved',       label: 'Saved',        emoji: '🔖', color: 'text-blue-700 bg-blue-50 border-blue-200' },
  { value: 'in_progress', label: 'In Progress',  emoji: '✍️', color: 'text-yellow-700 bg-yellow-50 border-yellow-200' },
  { value: 'submitted',   label: 'Submitted',    emoji: '📤', color: 'text-purple-700 bg-purple-50 border-purple-200' },
  { value: 'won',         label: 'Won',          emoji: '🏆', color: 'text-green-700 bg-green-50 border-green-200' },
  { value: 'lost',        label: 'Lost',         emoji: '❌', color: 'text-red-700 bg-red-50 border-red-200' },
]

interface Category {
  id: number
  name: string
  description: string
  color: string
  icon?: string
}

export default function Dashboard() {
  const { isAuthenticated } = useAuth()
  const [rawGrants, setRawGrants] = useState<ScrapedGrant[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [keywordSearch, setKeywordSearch] = useState<string>('')
  const [highMatchOnly, setHighMatchOnly] = useState(false)
  const [recentPostsOnly, setRecentPostsOnly] = useState(false)
  const [fundingMin, setFundingMin] = useState<number | undefined>(undefined)
  const [fundingMax, setFundingMax] = useState<number | undefined>(undefined)
  const [dueInDays, setDueInDays] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState<'match' | 'amount' | 'deadline'>('deadline')
  const [tableSortBy, setTableSortBy] = useState<'match' | 'title' | 'funder' | 'amount' | 'deadline' | 'source' | 'created_at'>('deadline')
  const [tableSortOrder, setTableSortOrder] = useState<'asc' | 'desc'>('desc')
  const [savingGrants, setSavingGrants] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 15
  const [showBackToTop, setShowBackToTop] = useState(false)
  const [selectedDescription, setSelectedDescription] = useState<{ title: string; description: string } | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Set<string>>(new Set())
  const [feedbackCounts, setFeedbackCounts] = useState<Record<string, {positive: number, negative: number}>>({})
  const [dismissingGrants, setDismissingGrants] = useState<Set<string>>(new Set())
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<Set<number>>(new Set())
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [grantStatuses, setGrantStatuses] = useState<Record<string, string>>({})  // grantId -> current pipeline status
  const [updatingStatus, setUpdatingStatus] = useState<Set<string>>(new Set())
  const [pipelineStatusFilter, setPipelineStatusFilter] = useState<string>('all')  // pipeline tab filter (auth only)

  useEffect(() => {
    fetchGrants(isAuthenticated)
    fetchCategories()
  }, [isAuthenticated])

  // Update sort defaults based on auth status
  useEffect(() => {
    if (isAuthenticated) {
      // When authenticated, default to match score sorting
      setSortBy('match')
      setTableSortBy('match')
    } else {
      // When not authenticated, use deadline sorting (match scores are hidden)
      if (sortBy === 'match') setSortBy('deadline')
      if (tableSortBy === 'match') setTableSortBy('deadline')
    }
  }, [isAuthenticated])

  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 400)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const fetchCategories = async () => {
    try {
      const response = await api.getCategories()
      if (response.ok) {
        const data = await response.json()
        setCategories(data.categories || [])
      }
    } catch (error) {
    }
  }

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  useEffect(() => {
    setCurrentPage(1)
  }, [rawGrants, keywordSearch, highMatchOnly, fundingMin, fundingMax, dueInDays, sortBy, selectedCategories, pipelineStatusFilter])

  function getPostedDateValue(grant: ScrapedGrant) {
    const value = grant.created_at || grant.updated_at || ''
    return value ? new Date(value).getTime() : 0
  }

  function getPostedDateLabel(grant: ScrapedGrant) {
    const value = grant.created_at || grant.updated_at || ''
    return value ? formatDate(value) : '—'
  }

  const fetchGrants = async (authenticated: boolean) => {
    try {
      setLoading(true)
      setHasMore(false)
      // Use org-specific scored grants for authenticated users, global pool for anonymous
      const response = authenticated 
        ? await api.getMyGrants({ limit: 150, offset: 0 })
        : await api.getScrapedGrants({ limit: 150, offset: 0 })

      if (response.ok) {
        const data = await response.json()
        const fetched: ScrapedGrant[] = data.grants || []
        setRawGrants(fetched)
        setHasMore(data.has_more === true)
        // Initialize pipeline statuses from org_status
        const statuses: Record<string, string> = {}
        fetched.forEach(g => {
          if (g.org_status) statuses[g.id] = g.org_status
        })
        setGrantStatuses(statuses)
      }
    } catch (error) {
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateGrantStatus = async (grantId: string, newStatus: string) => {
    if (!isAuthenticated) return
    setUpdatingStatus(prev => new Set(prev).add(grantId))
    try {
      const response = await api.updateGrantStatus(grantId, newStatus)
      if (response.ok) {
        setGrantStatuses(prev => ({ ...prev, [grantId]: newStatus }))
        // If dismissing via status, remove from list
        if (newStatus === 'dismissed') {
          setRawGrants(prev => prev.filter(g => g.id !== grantId))
        }
      }
    } catch (error) {
      // silent fail
    } finally {
      setUpdatingStatus(prev => {
        const next = new Set(prev)
        next.delete(grantId)
        return next
      })
    }
  }

  const loadMoreGrants = async () => {
    if (loadingMore || !hasMore) return
    try {
      setLoadingMore(true)
      const offset = rawGrants.length
      const response = isAuthenticated
        ? await api.getMyGrants({ limit: 150, offset })
        : await api.getScrapedGrants({ limit: 150, offset })

      if (response.ok) {
        const data = await response.json()
        const fetched: ScrapedGrant[] = data.grants || []
        setRawGrants(prev => [...prev, ...fetched])
        setHasMore(data.has_more === true)
      }
    } catch (error) {
    } finally {
      setLoadingMore(false)
    }
  }

  const filteredGrants = useMemo(() => {
    let list = [...rawGrants]

    // Filter out dismissed grants first
    list = list.filter(g => g.status !== 'dismissed')

    // Pipeline status tab filter (authenticated users only)
    if (pipelineStatusFilter !== 'all') {
      list = list.filter(g => {
        const ps = grantStatuses[g.id] || g.org_status || 'active'
        return ps === pipelineStatusFilter
      })
    }

    if (selectedCategories.size > 0) {
      list = list.filter(g => g.category_id && selectedCategories.has(g.category_id))
    }

    if (keywordSearch.trim()) {
      const keywords = keywordSearch.toLowerCase().trim()
      list = list.filter(g => {
        const searchText = `${g.title || ''} ${g.description || ''} ${g.funder || ''} ${g.contact || ''}`.toLowerCase()
        return searchText.includes(keywords)
      })
    }


    if (recentPostsOnly) {
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      list = list.filter(g => {
        const createdAt = g.created_at || g.updated_at
        if (!createdAt) return false
        const created = new Date(createdAt)
        return created >= oneWeekAgo
      })
    }

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

    // Use table sorting when in table view, otherwise use grid sorting
    if (viewMode === 'table') {
      const sortField = tableSortBy
      const order = tableSortOrder === 'asc' ? 1 : -1
      
      if (sortField === 'match') {
        list.sort((a, b) => order * ((b.match_score || 0) - (a.match_score || 0)))
      } else if (sortField === 'title') {
        list.sort((a, b) => order * (a.title || '').localeCompare(b.title || ''))
      } else if (sortField === 'funder') {
        list.sort((a, b) => order * (a.funder || '').localeCompare(b.funder || ''))
      } else if (sortField === 'amount') {
        list.sort((a, b) => order * ((b.amount || 0) - (a.amount || 0)))
      } else if (sortField === 'deadline') {
        list.sort((a, b) => {
          const da = a.deadline ? new Date(a.deadline).getTime() : Infinity
          const db = b.deadline ? new Date(b.deadline).getTime() : Infinity
          return order * (da - db)
        })
      } else if (sortField === 'source') {
        list.sort((a, b) => order * (a.source || '').localeCompare(b.source || ''))
      } else if (sortField === 'created_at') {
        list.sort((a, b) => {
          const aDate = getPostedDateValue(a)
          const bDate = getPostedDateValue(b)
          return order * (bDate - aDate)
        })
      }
    } else {
      // Grid view sorting
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
    }

    return list
  }, [rawGrants, keywordSearch, highMatchOnly, recentPostsOnly, fundingMin, fundingMax, dueInDays, sortBy, viewMode, tableSortBy, tableSortOrder, selectedCategories, pipelineStatusFilter, grantStatuses])

  const handleTableSort = (column: 'match' | 'title' | 'funder' | 'amount' | 'deadline' | 'source' | 'created_at') => {
    if (tableSortBy === column) {
      // Toggle sort order if clicking the same column
      setTableSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      // Set new column and default to descending for match/amount, ascending for text
      setTableSortBy(column)
      setTableSortOrder(column === 'match' || column === 'amount' || column === 'created_at' ? 'desc' : 'asc')
    }
    setCurrentPage(1) // Reset to first page when sorting
  }

  const handleSaveGrant = async (grantId: string) => {
    // Redirect to signup if not authenticated
    if (!isAuthenticated) {
      window.location.href = '/signup'
      return
    }

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
      alert('Failed to save grant')
    } finally {
      setSavingGrants(prev => {
        const next = new Set(prev)
        next.delete(grantId)
        return next
      })
    }
  }

  const submitFeedback = async (grantId: string, isPositive: boolean) => {
    try {
      // If it's negative feedback, show dismiss confirmation
      if (!isPositive) {
        const shouldDismiss = confirm('This will mark the opportunity as "Poor Match" and remove it from your dashboard permanently. Continue?')
        if (shouldDismiss) {
          await dismissGrant(grantId)
          return
        } else {
          return // User cancelled
        }
      }

      const response = await api.submitOpportunityFeedback(grantId, isPositive ? 'positive' : 'negative')

      if (response.ok) {
        setFeedbackSubmitted(prev => new Set(prev).add(grantId))
        // Optionally refresh feedback counts
        fetchFeedbackCounts(grantId)
      } else {
        alert('Failed to submit feedback')
      }
    } catch (error) {
      alert('Failed to submit feedback')
    }
  }

  const dismissGrant = async (grantId: string) => {
    try {
      setDismissingGrants(prev => new Set(prev).add(grantId))
      
      // Submit negative feedback first
      await api.submitOpportunityFeedback(grantId, 'negative')
      
      // Then dismiss the opportunity
      const response = await api.dismissOpportunity(grantId)

      if (response.ok) {
        // Remove from the current list with a slight delay for visual feedback
        setTimeout(() => {
          setRawGrants(prev => prev.filter(grant => grant.id !== grantId))
          setDismissingGrants(prev => {
            const newSet = new Set(prev)
            newSet.delete(grantId)
            return newSet
          })
        }, 500)
      } else {
        alert('Failed to dismiss opportunity')
        setDismissingGrants(prev => {
          const newSet = new Set(prev)
          newSet.delete(grantId)
          return newSet
        })
      }
    } catch (error) {
      alert('Failed to dismiss opportunity')
      setDismissingGrants(prev => {
        const newSet = new Set(prev)
        newSet.delete(grantId)
        return newSet
      })
    }
  }

  const fetchFeedbackCounts = async (grantId: string) => {
    try {
      const response = await api.getOpportunityFeedback(grantId)
      if (response.ok) {
        const counts = await response.json()
        setFeedbackCounts(prev => ({...prev, [grantId]: counts}))
      }
    } catch (error) {
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

  function formatDate(dateStr: string) {
    if (!dateStr || dateStr === 'Historical') return dateStr
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const getMatchColor = (score: number) => {
    if (score >= 80) return 'bg-green-600'
    if (score >= 65) return 'bg-perscholas-accent'
    return 'bg-gray-400'
  }

  const getSourceBadge = (source: string) => {
    const sourceColors: { [key: string]: string } = {
      'grants_gov': 'bg-blue-50 text-blue-700 border-blue-200',
      'sam_gov': 'bg-purple-50 text-purple-700 border-purple-200',
      'dol_workforce': 'bg-indigo-50 text-indigo-700 border-indigo-200',
      'usa_spending': 'bg-cyan-50 text-cyan-700 border-cyan-200',
      'ny_dol': 'bg-teal-50 text-teal-700 border-teal-200',
      'state': 'bg-green-50 text-green-700 border-green-200',
      'local': 'bg-orange-50 text-orange-700 border-orange-200',
      'user_upload': 'bg-violet-50 text-violet-700 border-violet-200',
      'ai_search': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'manual': 'bg-yellow-50 text-yellow-700 border-yellow-200',
      'saved': 'bg-slate-50 text-slate-700 border-slate-200',
      'uploaded': 'bg-violet-50 text-violet-700 border-violet-200',
      'search': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'agent': 'bg-emerald-50 text-emerald-700 border-emerald-200'
    }
    return sourceColors[source] || 'bg-gray-50 text-gray-700 border-gray-200'
  }

  const getSourceLabel = (source: string) => {
    const labels: { [key: string]: string } = {
      'grants_gov': 'Grants.gov',
      'sam_gov': 'SAM.gov',
      'dol_workforce': 'DOL Workforce',
      'usa_spending': 'Federal Database',
      'ny_dol': 'NY Department of Labor',
      'state': 'State Government',
      'local': 'Local Government',
      'user_upload': 'User Upload',
      'ai_search': 'AI Search',
      'manual': 'Manual Entry',
      'saved': 'Saved Opportunity',
      'uploaded': 'User Upload',
      'search': 'AI Search',
      'agent': 'AI Search'
    }
    return labels[source] || source.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
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
    <div className="min-h-screen">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <div className="card-elevated p-6 sm:p-10 animate-fade-in">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-perscholas-primary p-3 rounded-xl shadow-md">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-3xl sm:text-4xl font-bold text-perscholas-primary">
                    Comprehensive Grants Database
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">Updated daily</p>
                </div>
              </div>
              {!isAuthenticated && (
                <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                  <a
                    href="/signup"
                    className="btn-primary whitespace-nowrap text-center"
                  >
                    Get Started
                  </a>
                  <a
                    href="/login"
                    className="btn-secondary whitespace-nowrap text-center"
                  >
                    Sign In
                  </a>
                </div>
              )}
            </div>
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <p className="text-sm text-gray-700 leading-relaxed">
                {isAuthenticated ? (
                  <><span className="font-semibold text-perscholas-primary">Save any grant</span> to your pipeline to unlock AI-powered matching, summaries, and insights.</>
                ) : (
                  <><span className="font-semibold text-perscholas-primary">Sign up to save grants</span> and unlock AI-powered matching, summaries, and insights in your personal pipeline.</>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 sm:mb-8 grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <div className="card-premium p-5 sm:p-6 animate-fadeIn" style={{ animationDelay: '100ms' }}>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Total Grants</p>
            <p className="text-3xl sm:text-4xl font-bold text-gray-900">{filteredGrants.length}</p>
          </div>

          <div className="card-premium p-5 sm:p-6 animate-fadeIn" style={{ animationDelay: '150ms' }}>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Total Funding</p>
            <p className="text-2xl sm:text-3xl font-bold text-green-600 truncate">
              {formatCurrency(filteredGrants.reduce((sum, g) => sum + (g.amount || 0), 0))}
            </p>
          </div>

          <div className="card-premium p-5 sm:p-6 animate-fadeIn" style={{ animationDelay: '200ms' }}>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Avg Award</p>
            <p className="text-2xl sm:text-3xl font-bold text-perscholas-primary">
              {filteredGrants.length > 0
                ? formatCurrency(filteredGrants.reduce((sum, g) => sum + (g.amount || 0), 0) / filteredGrants.length)
                : '$0'}
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
                {(recentPostsOnly || keywordSearch || fundingMin || fundingMax || dueInDays || selectedCategories.size > 0) && (
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
              <div className="card-elevated p-6">
                <h3 className="text-lg font-bold text-perscholas-primary mb-6 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  Filters
                </h3>

                <div className="space-y-6">
                  {/* Quick Filters Section */}
                  <div className="space-y-3">
                    <p className="text-sm font-bold text-gray-900">Quick Filters</p>

                    <label className={`flex items-center justify-between p-4 rounded-xl border-2 cursor-pointer transition-all ${
                      recentPostsOnly
                        ? 'border-perscholas-primary bg-perscholas-primary/5'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-md flex items-center justify-center ${
                          recentPostsOnly ? 'bg-perscholas-primary' : 'bg-gray-200'
                        }`}>
                          {recentPostsOnly && (
                            <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                        <span className={`text-sm font-semibold ${recentPostsOnly ? 'text-perscholas-primary' : 'text-gray-700'}`}>
                          Recent Only (1 week)
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={recentPostsOnly}
                        onChange={(e) => setRecentPostsOnly(e.target.checked)}
                        className="sr-only"
                      />
                    </label>
                  </div>

                  <div className="border-t border-gray-100 pt-6"></div>

                  {/* Categories Filter */}
                  {categories.length > 0 && (
                    <div>
                      <label className="text-xs font-semibold text-gray-700 mb-2 block">Categories</label>
                      <div className="space-y-2">
                        {categories.map((category) => (
                          <label key={category.id} className="flex items-start gap-2 p-2 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors">
                            <input
                              type="checkbox"
                              checked={selectedCategories.has(category.id)}
                              onChange={(e) => {
                                const newSet = new Set(selectedCategories)
                                if (e.target.checked) {
                                  newSet.add(category.id)
                                } else {
                                  newSet.delete(category.id)
                                }
                                setSelectedCategories(newSet)
                              }}
                              className="w-4 h-4 text-perscholas-primary rounded focus:ring-2 focus:ring-perscholas-primary/20 flex-shrink-0 mt-0.5"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-medium text-gray-900">{category.name}</p>
                              {category.description && (
                                <p className="text-xs text-gray-600 line-clamp-2">{category.description}</p>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Keyword Search */}
                  <div>
                    <label className="text-sm font-bold text-gray-900 mb-3 block">Search Keywords</label>
                    <div className="relative">
                      <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        value={keywordSearch}
                        onChange={(e) => setKeywordSearch(e.target.value)}
                        className="input-premium w-full pl-12"
                        placeholder="Search opportunities..."
                      />
                    </div>
                  </div>

                  {/* Funding Range */}
                  <div>
                    <label className="text-sm font-bold text-gray-900 mb-3 block">Funding Range</label>
                    <div className="grid grid-cols-2 gap-3">
                      <input
                        type="number"
                        value={fundingMin ?? ''}
                        onChange={(e) => setFundingMin(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Min $"
                        className="input-premium"
                      />
                      <input
                        type="number"
                        value={fundingMax ?? ''}
                        onChange={(e) => setFundingMax(e.target.value ? Number(e.target.value) : undefined)}
                        placeholder="Max $"
                        className="input-premium"
                      />
                    </div>
                  </div>

                  {/* Due Date */}
                  <div>
                    <label className="text-sm font-bold text-gray-900 mb-3 block">Due Within</label>
                    <div className="relative">
                      <input
                        type="number"
                        value={dueInDays ?? ''}
                        onChange={(e) => setDueInDays(e.target.value ? Number(e.target.value) : undefined)}
                        className="input-premium w-full"
                        placeholder="Days (e.g., 30)"
                      />
                    </div>
                  </div>

                  {/* Sort - Only show in grid view */}
                  {viewMode === 'grid' && (
                    <div>
                      <label className="text-sm font-bold text-gray-900 mb-3 block">Sort By</label>
                      <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as any)}
                        className="input-premium w-full"
                      >
                        <option value="amount">Funding Amount</option>
                        <option value="deadline">Due Date</option>
                      </select>
                    </div>
                  )}

                  {/* Clear Filters Button */}
                  {(recentPostsOnly || keywordSearch || fundingMin || fundingMax || dueInDays || selectedCategories.size > 0) && (
                    <div className="pt-6 border-t border-gray-100">
                      <button
                        onClick={() => {
                          setKeywordSearch('')
                          setRecentPostsOnly(false)
                          setFundingMin(undefined)
                          setFundingMax(undefined)
                          setDueInDays(undefined)
                          setSelectedCategories(new Set())
                        }}
                        className="w-full btn-secondary py-3 flex items-center justify-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Clear All Filters
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* How it works */}
              <div id="how-it-works" className="bg-gradient-to-br from-perscholas-primary/5 to-perscholas-secondary/5 rounded-xl border border-perscholas-primary/20 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="bg-perscholas-primary p-1.5 rounded-lg">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <p className="text-sm font-bold text-gray-900">How it works</p>
                </div>
                <div className="space-y-3 text-xs text-gray-700">
                  <div className="flex gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-perscholas-primary text-white text-xs font-bold flex items-center justify-center">1</span>
                    <p><span className="font-semibold">AI agents scan</span> thousands of grants daily from federal databases, foundations, and more.</p>
                  </div>
                  <div className="flex gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-perscholas-primary text-white text-xs font-bold flex items-center justify-center">2</span>
                    <p><span className="font-semibold">Smart matching</span> scores each grant based on your organization's mission and focus areas.</p>
                  </div>
                  <div className="flex gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-perscholas-primary text-white text-xs font-bold flex items-center justify-center">3</span>
                    <p><span className="font-semibold">Save &amp; unlock insights</span> — get AI summaries, winning strategies, and similar past RFPs.</p>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {/* Pipeline Status Filter Tabs — authenticated users only */}
            {isAuthenticated && (
              <div className="mb-4 flex items-center gap-1 flex-wrap bg-white border border-gray-200 rounded-xl p-1 shadow-sm">
                {[
                  { value: 'all',         label: 'All',         emoji: '📊' },
                  { value: 'active',      label: 'Active',      emoji: '📋' },
                  { value: 'saved',       label: 'Saved',       emoji: '🔖' },
                  { value: 'in_progress', label: 'In Progress', emoji: '✍️' },
                  { value: 'submitted',   label: 'Submitted',   emoji: '📤' },
                  { value: 'won',         label: 'Won',         emoji: '🏆' },
                  { value: 'lost',        label: 'Lost',        emoji: '❌' },
                ].map(tab => {
                  const count = tab.value === 'all'
                    ? rawGrants.filter(g => g.status !== 'dismissed').length
                    : rawGrants.filter(g => {
                        if (g.status === 'dismissed') return false
                        const ps = grantStatuses[g.id] || g.org_status || 'active'
                        return ps === tab.value
                      }).length
                  return (
                    <button
                      key={tab.value}
                      onClick={() => { setPipelineStatusFilter(tab.value); setCurrentPage(1) }}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        pipelineStatusFilter === tab.value
                          ? 'bg-perscholas-primary text-white shadow-sm'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <span>{tab.label}</span>
                      {count > 0 && (
                        <span className={`ml-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${
                          pipelineStatusFilter === tab.value
                            ? 'bg-white/20 text-white'
                            : 'bg-gray-100 text-gray-500'
                        }`}>{count}</span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}

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
            ) : viewMode === 'grid' ? (
              <div>
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5 mb-8">
                  {paged.map((grant, index) => (
                    <div
                      key={grant.id}
                      className={`group card-premium p-6 h-full flex flex-col animate-fadeIn ${
                        dismissingGrants.has(grant.id) ? 'opacity-50 scale-95' : ''
                      }`}
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      {/* Header: Title + Match Score */}
                      <h3 className="text-base font-bold text-gray-900 line-clamp-2 leading-tight group-hover:text-perscholas-primary transition-colors mb-2">
                        {grant.title}
                      </h3>

                      {/* Provider */}
                      <p className="text-sm font-medium text-perscholas-primary mb-3">{grant.funder}</p>

                      {/* Description */}
                      <div className="mb-4 flex-grow">
                        <p className="text-sm text-gray-600 leading-relaxed line-clamp-4">
                          {grant.description}
                        </p>
                        {grant.description && grant.description.length > 250 && (
                          <button
                            onClick={() => setSelectedDescription({ title: grant.title, description: grant.description })}
                            className="text-xs text-perscholas-primary font-medium hover:text-perscholas-dark mt-2 inline-flex items-center gap-1"
                          >
                            Read more
                            <svg className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </button>
                        )}
                      </div>

                      {/* Metrics */}
                      <div className="flex items-center justify-between text-sm mb-4 py-2 px-3 bg-gray-50 rounded-lg">
                        <span className="font-semibold text-green-600">{formatCurrency(grant.amount)}</span>
                        <span className="text-gray-500">Due {formatDate(grant.deadline)}</span>
                      </div>

                      {/* Actions */}
                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                        {grant.application_url && (
                          <a
                            href={grant.application_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 text-center btn-secondary py-2.5"
                          >
                            View RFP
                          </a>
                        )}
                        <button
                          onClick={() => handleSaveGrant(grant.id)}
                          disabled={savingGrants.has(grant.id)}
                          className="flex-1 btn-primary py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
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
                              {isAuthenticated ? 'Save' : 'Sign up to Save'}
                            </span>
                          )}
                        </button>
                      </div>

                      {/* Pipeline Status — Only show when authenticated */}
                      {isAuthenticated && (
                        <div className="mt-4 pt-4 border-t border-gray-100">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-gray-500 shrink-0">Pipeline status:</span>
                            <select
                              value={grantStatuses[grant.id] || 'active'}
                              onChange={e => handleUpdateGrantStatus(grant.id, e.target.value)}
                              disabled={updatingStatus.has(grant.id)}
                              className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-perscholas-primary focus:border-transparent disabled:opacity-50 cursor-pointer"
                            >
                              {PIPELINE_STATUSES.map(s => (
                                <option key={s.value} value={s.value}>
                                  {s.label}
                                </option>
                              ))}
                              <option value="dismissed">Dismiss</option>
                            </select>
                          </div>
                        </div>
                      )}

                      {/* Feedback Section - Only show when authenticated */}
                      {isAuthenticated && (
                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-medium text-gray-700">Is this a good match?</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            {feedbackSubmitted.has(grant.id) ? (
                              <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                                Thanks for your feedback!
                              </span>
                            ) : (
                              <>
                                <button
                                  onClick={() => submitFeedback(grant.id, true)}
                                  className="flex items-center space-x-1 px-2 py-1 rounded-full border border-green-200 text-green-700 hover:bg-green-50 transition-colors text-xs"
                                >
                                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                                  </svg>
                                  <span>Good</span>
                                </button>
                                <button
                                  onClick={() => submitFeedback(grant.id, false)}
                                  disabled={dismissingGrants.has(grant.id)}
                                  className="flex items-center space-x-1 px-2 py-1 rounded-full border border-red-200 text-red-700 hover:bg-red-50 transition-colors text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  {dismissingGrants.has(grant.id) ? (
                                    <>
                                      <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                      </svg>
                                      <span>Removing...</span>
                                    </>
                                  ) : (
                                    <>
                                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                                      </svg>
                                      <span>Poor Match</span>
                                    </>
                                  )}
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      )}
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

                {/* Load More from Server */}
                {hasMore && currentPage >= totalPages && (
                  <div className="flex justify-center mt-6">
                    <button
                      onClick={loadMoreGrants}
                      disabled={loadingMore}
                      className="btn-secondary px-8 py-3 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loadingMore ? (
                        <>
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Loading more grants...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          Load More Grants
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* Table View */
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="w-full overflow-x-auto">
                  <table className="w-full" style={{ tableLayout: 'auto' }}>
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors" onClick={() => handleTableSort('title')}>
                          <div className="flex items-center gap-1.5">
                            <span className="hidden sm:inline">Title</span>
                            <span className="sm:hidden">Name</span>
                            {tableSortBy === 'title' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors hidden lg:table-cell" onClick={() => handleTableSort('funder')}>
                          <div className="flex items-center gap-1.5">
                            <span>Funder</span>
                            {tableSortBy === 'funder' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors whitespace-nowrap" onClick={() => handleTableSort('amount')}>
                          <div className="flex items-center gap-1.5">
                            <span className="hidden sm:inline">Funding</span>
                            <span className="sm:hidden">$</span>
                            {tableSortBy === 'amount' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors whitespace-nowrap" onClick={() => handleTableSort('deadline')}>
                          <div className="flex items-center gap-1.5">
                            <span className="hidden sm:inline">Deadline</span>
                            <span className="sm:hidden">Due</span>
                            {tableSortBy === 'deadline' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors whitespace-nowrap" onClick={() => handleTableSort('created_at')}>
                          <div className="flex items-center gap-1.5">
                            <span>Added</span>
                            {tableSortBy === 'created_at' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors whitespace-nowrap" onClick={() => handleTableSort('source')}>
                          <div className="flex items-center gap-1.5">
                            <span>Source</span>
                            {tableSortBy === 'source' && (
                              <svg className={`w-3 h-3 ${tableSortOrder === 'asc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            )}
                          </div>
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider hidden xl:table-cell">
                          Description
                        </th>
                        <th className="px-1.5 sm:px-2 py-2 sm:py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider whitespace-nowrap">
                          <span className="hidden sm:inline">Actions</span>
                          <span className="sm:hidden">Act</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {paged.map((grant) => (
                        <tr key={grant.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <div className="text-xs sm:text-sm font-semibold text-gray-900 truncate max-w-[100px] sm:max-w-[200px]" title={grant.title}>
                              {grant.title}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3 hidden lg:table-cell">
                            <div className="text-xs sm:text-sm text-gray-600 truncate max-w-[150px]" title={grant.funder}>
                              {grant.funder}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <div className="text-xs sm:text-sm font-bold text-green-600 whitespace-nowrap">
                              {formatCurrency(grant.amount)}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <div className="text-xs sm:text-sm text-gray-900 whitespace-nowrap">
                              {formatDate(grant.deadline)}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <div className="text-xs sm:text-sm text-blue-600 whitespace-nowrap">
                              {getPostedDateLabel(grant)}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <span className={`inline-flex items-center px-1.5 sm:px-2 py-0.5 rounded text-xs font-semibold border ${getSourceBadge(grant.source)}`}>
                              {getSourceLabel(grant.source)}
                            </span>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3 hidden xl:table-cell">
                            <div>
                              <p className="text-xs text-gray-600 line-clamp-1" title={grant.description}>
                                {grant.description}
                              </p>
                              {grant.description && grant.description.length > 80 && (
                                <button
                                  onClick={() => setSelectedDescription({ title: grant.title, description: grant.description })}
                                  className="text-xs text-perscholas-primary font-medium hover:text-perscholas-dark mt-0.5"
                                >
                                  More
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="px-1.5 sm:px-2 py-2 sm:py-3">
                            <div className="flex items-center justify-center gap-0.5 sm:gap-1.5">
                              {grant.application_url && (
                                <a
                                  href={grant.application_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-1.5 sm:px-2 py-0.5 sm:py-1 border border-gray-300 text-gray-700 rounded text-xs font-medium hover:bg-gray-50 transition-colors"
                                  title="View RFP"
                                >
                                  <span className="hidden sm:inline">RFP</span>
                                  <span className="sm:hidden">RFP</span>
                                </a>
                              )}
                              <button
                                onClick={() => handleSaveGrant(grant.id)}
                                disabled={savingGrants.has(grant.id)}
                                className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-perscholas-primary text-white rounded text-xs font-medium hover:bg-perscholas-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                                title={isAuthenticated ? 'Save Grant' : 'Sign up to save'}
                              >
                                {savingGrants.has(grant.id) ? (
                                  <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                ) : (
                                  <span className="flex items-center gap-1">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span className="hidden sm:inline">{isAuthenticated ? 'Save' : 'Sign up'}</span>
                                  </span>
                                )}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Table Pagination */}
                {filteredGrants.length > itemsPerPage && (
                  <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
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
                    <div className="mt-2 text-center text-xs text-gray-600">
                      Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredGrants.length)} of {filteredGrants.length} grants
                    </div>
                    {/* Load More from Server */}
                    {hasMore && currentPage >= totalPages && (
                      <div className="flex justify-center mt-4">
                        <button
                          onClick={loadMoreGrants}
                          disabled={loadingMore}
                          className="btn-secondary px-8 py-3 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {loadingMore ? (
                            <>
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Loading more grants...
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                              Load More Grants
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                )}
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
