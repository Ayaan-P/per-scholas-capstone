'use client'

import { useState, useEffect } from 'react'
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
  const [grants, setGrants] = useState<ScrapedGrant[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [savingGrants, setSavingGrants] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchGrants()
  }, [filter])

  const fetchGrants = async () => {
    try {
      setLoading(true)
      const params = filter !== 'all' ? { source: filter } : {}
      const response = await api.getScrapedGrants(params)

      if (response.ok) {
        const data = await response.json()
        // Sort by match score descending
        const sortedGrants = (data.grants || []).sort((a: ScrapedGrant, b: ScrapedGrant) => b.match_score - a.match_score)
        setGrants(sortedGrants)
      }
    } catch (error) {
      console.error('Failed to fetch grants:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveGrant = async (grantId: string) => {
    try {
      setSavingGrants(prev => new Set(prev).add(grantId))
      const response = await api.saveScrapedGrant(grantId)

      if (response.ok) {
        const data = await response.json()
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Grant Opportunities</h1>
          <p className="text-gray-600 text-lg">
            Automatically discovered funding opportunities • Updated every 6-12 hours
          </p>
        </div>

        {/* Stats Bar */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-8 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Total Opportunities</p>
              <p className="text-3xl font-bold text-gray-900">{grants.length}</p>
            </div>
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Total Funding</p>
              <p className="text-3xl font-bold text-perscholas-primary">
                {formatCurrency(grants.reduce((sum, g) => sum + (g.amount || 0), 0))}
              </p>
            </div>
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">High Match</p>
              <p className="text-3xl font-bold text-green-600">
                {grants.filter(g => g.match_score >= 85).length}
              </p>
            </div>
            <div className="text-center md:text-left">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Avg Match</p>
              <p className="text-3xl font-bold text-gray-900">
                {grants.length > 0
                  ? Math.round(grants.reduce((sum, g) => sum + g.match_score, 0) / grants.length)
                  : 0}%
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-8 flex items-center space-x-4">
          <label className="text-sm font-semibold text-gray-700">Filter by source:</label>
          <div className="flex flex-wrap gap-2">
            {['all', 'grants_gov', 'sam_gov', 'state', 'local'].map((src) => (
              <button
                key={src}
                onClick={() => setFilter(src)}
                className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  filter === src
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-perscholas-primary hover:bg-gray-50'
                }`}
              >
                {src === 'all' ? 'All Sources' : getSourceLabel(src)}
              </button>
            ))}
          </div>
        </div>

        {/* Grant List */}
        {grants.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md border border-gray-200 p-16 text-center">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">No grants found</h3>
            <p className="text-gray-600 text-lg">The automated scraper is running. Check back soon for new opportunities.</p>
          </div>
        ) : (
          <div className="space-y-5">
            {grants.map((grant) => (
              <div
                key={grant.id}
                className="bg-white rounded-xl shadow-md border border-gray-200 p-8 hover:shadow-xl hover:border-perscholas-primary/30 transition-all duration-200"
              >
                <div className="flex justify-between items-start mb-5">
                  <div className="flex-1 pr-8">
                    <div className="mb-3">
                      <h3 className="text-2xl font-bold text-gray-900 mb-2">{grant.title}</h3>
                      <p className="text-base text-gray-600 font-medium">{grant.funder}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <span className={`px-4 py-2 rounded-lg text-sm font-bold shadow-sm ${getMatchColor(grant.match_score)}`}>
                      {grant.match_score}% Match
                    </span>
                    <p className="text-3xl font-bold text-perscholas-primary">
                      {formatCurrency(grant.amount)}
                    </p>
                    <p className="text-sm text-gray-500 font-medium">
                      Due {formatDate(grant.deadline)}
                    </p>
                  </div>
                </div>

                <p className="text-gray-700 mb-5 leading-relaxed line-clamp-2">{grant.description}</p>

                {grant.requirements && grant.requirements.length > 0 && (
                  <div className="mb-5 bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-semibold text-gray-700 mb-2">Key Requirements:</p>
                    <ul className="space-y-1.5">
                      {grant.requirements.slice(0, 3).map((req: string, idx: number) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-start">
                          <span className="text-perscholas-primary mr-2 mt-0.5">•</span>
                          <span>{req}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex justify-between items-center pt-5 border-t border-gray-200">
                  <div className="flex items-center space-x-3">
                    <span className={`px-3 py-1.5 rounded-lg text-xs font-bold ${getSourceBadge(grant.source)}`}>
                      {getSourceLabel(grant.source)}
                    </span>
                    <span className="text-xs text-gray-500 font-medium">
                      Added {formatDate(grant.created_at)}
                    </span>
                  </div>
                  <div className="flex space-x-3">
                    <a
                      href={grant.application_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-5 py-2.5 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-all text-sm font-semibold"
                    >
                      View Details
                    </a>
                    <button
                      onClick={() => handleSaveGrant(grant.id)}
                      disabled={savingGrants.has(grant.id)}
                      className="px-6 py-2.5 bg-gradient-to-r from-perscholas-primary to-blue-600 text-white rounded-lg hover:shadow-lg hover:scale-105 transition-all text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      {savingGrants.has(grant.id) ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
