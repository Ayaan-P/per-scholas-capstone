'use client'

import { useState, useEffect } from 'react'
import { api } from '../../lib/api'

interface AnalyticsData {
  searchMetrics: {
    totalSearches: number
    successfulSearches: number
    avgOpportunitiesPerSearch: number
    avgMatchScore: number
  }
  opportunityMetrics: {
    totalOpportunities: number
    savedOpportunities: number
    totalFundingValue: number
    avgFundingAmount: number
  }
  proposalMetrics: {
    totalProposals: number
    submittedProposals: number
    approvedProposals: number
    successRate: number
  }
  timeSeriesData: {
    date: string
    searches: number
    opportunities: number
    proposals: number
  }[]
  topFunders: {
    name: string
    opportunityCount: number
    totalFunding: number
  }[]
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('30d')

  useEffect(() => {
    fetchAnalytics()
  }, [timeRange])

  const fetchAnalytics = async () => {
    try {
      const response = await api.getAnalytics(timeRange)
      const data = await response.json()
      setAnalytics(data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setLoading(false)
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

  const formatPercentage = (value: number) => {
    return `${Math.round(value)}%`
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary"></div>
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No analytics data available</h3>
          <p className="text-gray-600">Start using the platform to see analytics</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics</h1>
              <p className="text-gray-600">Track your fundraising intelligence performance</p>
            </div>
            <div>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 bg-white text-sm"
              >
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
                <option value="1y">Last year</option>
              </select>
            </div>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Search Metrics */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Searches</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics?.searchMetrics?.totalSearches || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-green-600 font-medium">
                  {formatPercentage(((analytics?.searchMetrics?.successfulSearches || 0) / (analytics?.searchMetrics?.totalSearches || 1)) * 100)}
                </span>
                <span className="text-gray-500 ml-2">success rate</span>
              </div>
            </div>
          </div>

          {/* Opportunity Metrics */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-perscholas-primary rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Opportunities Found</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics?.opportunityMetrics?.totalOpportunities || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-green-600 font-medium">
                  {analytics?.opportunityMetrics?.savedOpportunities || 0}
                </span>
                <span className="text-gray-500 ml-2">saved</span>
              </div>
            </div>
          </div>

          {/* Funding Metrics */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Funding Value</dt>
                  <dd className="text-lg font-medium text-gray-900">{formatCurrency(analytics?.opportunityMetrics?.totalFundingValue || 0)}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-gray-600 font-medium">
                  {formatCurrency(analytics?.opportunityMetrics?.avgFundingAmount || 0)}
                </span>
                <span className="text-gray-500 ml-2">avg per opportunity</span>
              </div>
            </div>
          </div>

          {/* Proposal Metrics */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Proposals Generated</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics?.proposalMetrics?.totalProposals || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-green-600 font-medium">
                  {formatPercentage(analytics?.proposalMetrics?.successRate || 0)}
                </span>
                <span className="text-gray-500 ml-2">approval rate</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Activity Chart */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Activity Over Time</h3>
            <div className="h-64 flex items-end justify-between space-x-1">
              {(analytics?.timeSeriesData || []).map((data, index) => (
                <div key={index} className="flex-1 flex flex-col items-center">
                  <div className="w-full flex flex-col items-center space-y-1">
                    {/* Searches */}
                    <div
                      className="w-full bg-blue-500 rounded-t"
                      style={{ height: `${(data.searches / Math.max(...(analytics?.timeSeriesData || []).map(d => d.searches + d.opportunities + d.proposals))) * 200}px` }}
                    ></div>
                    {/* Opportunities */}
                    <div
                      className="w-full bg-perscholas-primary"
                      style={{ height: `${(data.opportunities / Math.max(...(analytics?.timeSeriesData || []).map(d => d.searches + d.opportunities + d.proposals))) * 200}px` }}
                    ></div>
                    {/* Proposals */}
                    <div
                      className="w-full bg-purple-500 rounded-b"
                      style={{ height: `${(data.proposals / Math.max(...(analytics?.timeSeriesData || []).map(d => d.searches + d.opportunities + d.proposals))) * 200}px` }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-2 transform -rotate-45">
                    {new Date(data.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-center space-x-6 mt-4">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span className="text-sm text-gray-600">Searches</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-perscholas-primary rounded mr-2"></div>
                <span className="text-sm text-gray-600">Opportunities</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-purple-500 rounded mr-2"></div>
                <span className="text-sm text-gray-600">Proposals</span>
              </div>
            </div>
          </div>

          {/* Top Funders */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Funders</h3>
            <div className="space-y-4">
              {(analytics?.topFunders || []).map((funder, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-sm font-medium text-gray-600">{index + 1}</span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">{funder.name}</div>
                      <div className="text-xs text-gray-500">{funder.opportunityCount} opportunities</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">{formatCurrency(funder.totalFunding)}</div>
                    <div className="text-xs text-gray-500">total funding</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Performance Insights */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Insights</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-perscholas-primary mb-2">
                {formatPercentage(analytics?.searchMetrics?.avgMatchScore || 0)}
              </div>
              <div className="text-sm text-gray-600">Average Match Score</div>
              <div className="text-xs text-gray-500 mt-1">Quality of opportunity alignment</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600 mb-2">
                {(analytics?.searchMetrics?.avgOpportunitiesPerSearch || 0).toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">Opportunities per Search</div>
              <div className="text-xs text-gray-500 mt-1">Search efficiency metric</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600 mb-2">
                {formatPercentage(((analytics?.opportunityMetrics?.savedOpportunities || 0) / (analytics?.opportunityMetrics?.totalOpportunities || 1)) * 100)}
              </div>
              <div className="text-sm text-gray-600">Save Rate</div>
              <div className="text-xs text-gray-500 mt-1">Opportunities saved vs found</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}