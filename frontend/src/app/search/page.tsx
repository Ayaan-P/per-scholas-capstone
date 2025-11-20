'use client'

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'

interface Opportunity {
  id: string
  title: string
  funder: string
  amount: number
  deadline: string
  match_score: number
  description: string
  requirements: string[]
  contact: string
  application_url: string
  created_at?: string
  saved_at?: string
}

interface LocationPair {
  state: string
  city: string
}

export default function SearchPage() {
  const [isSearching, setIsSearching] = useState(false)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [searchPrompt, setSearchPrompt] = useState('')
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set())
  const [recentPostsOnly, setRecentPostsOnly] = useState(false)
  const [aiSearchEnabled, setAiSearchEnabled] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [schedulerFrequency, setSchedulerFrequency] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [locations, setLocations] = useState<LocationPair[]>([
    { state: 'California', city: 'Los Angeles/San Francisco' },
    { state: 'New York', city: 'New York/Newark' },
    { state: 'Texas', city: 'Dallas/Houston' }
  ])
  const [newState, setNewState] = useState('')
  const [newCity, setNewCity] = useState('')

  useEffect(() => {
    const fetchSchedulerSettings = async () => {
      try {
        const response = await fetch(`${api.baseURL}/api/scheduler/settings`)
        if (response.ok) {
          const data = await response.json()
          if (data.scheduler_frequency) {
            setSchedulerFrequency(data.scheduler_frequency)
          }
          if (data.selected_states && data.selected_cities) {
            const loadedLocations = data.selected_states.map((state: string, index: number) => ({
              state: state,
              city: data.selected_cities[index] || ''
            }))
            setLocations(loadedLocations)
          }
        }
      } catch (error) {
        console.error('Failed to load scheduler settings:', error)
      }
    }
    fetchSchedulerSettings()
  }, [])

  const saveOpportunity = async (opportunityId: string) => {
    setSavingIds(prev => new Set(prev).add(opportunityId))
    try {
      await api.saveOpportunity(opportunityId)
      // Refresh opportunities after save
      setTimeout(() => {
        setSavingIds(prev => {
          const newSet = new Set(prev)
          newSet.delete(opportunityId)
          return newSet
        })
      }, 1500)
    } catch (error) {
      alert('Failed to save opportunity')
      setSavingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(opportunityId)
        return newSet
      })
    }
  }

  const searchOpportunities = async () => {
    if (!searchPrompt.trim()) {
      alert('Please enter a search prompt')
      return
    }

    setIsSearching(true)

    try {
      // Start search job
      const response = await api.searchOpportunities({ prompt: searchPrompt })

      const { job_id } = await response.json()

      // Poll for job completion
      const pollJob = async () => {
        const jobResponse = await api.getJob(job_id)
        const jobData = await jobResponse.json()

        if (jobData.status === 'completed') {
          setOpportunities(jobData.result.opportunities)
          setIsSearching(false)
        } else if (jobData.status === 'failed') {
          alert('Search failed: ' + jobData.error)
          setIsSearching(false)
        } else {
          // Still running, poll again
          setTimeout(pollJob, 2000)
        }
      }

      setTimeout(pollJob, 1000)
    } catch (error) {
      alert('Failed to start search')
      setIsSearching(false)
    }
  }

  const getMatchColor = (score: number) => {
    if (score >= 80) return { bg: 'bg-green-600', text: 'text-white', lightBg: 'bg-green-50' }
    if (score >= 70) return { bg: 'bg-yellow-500', text: 'text-white', lightBg: 'bg-yellow-50' }
    return { bg: 'bg-gray-400', text: 'text-white', lightBg: 'bg-gray-50' }
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
    if (!dateStr || dateStr === 'Invalid Date') return 'TBD'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const addLocation = () => {
    if (!newState.trim() || !newCity.trim()) {
      alert('Please enter both state and city')
      return
    }
    setLocations([...locations, { state: newState, city: newCity }])
    setNewState('')
    setNewCity('')
  }

  const removeLocation = (index: number) => {
    setLocations(locations.filter((_, i) => i !== index))
  }

  const saveSchedulerSettings = async () => {
    try {
      if (locations.length === 0) {
        alert('Please add at least one location')
        return
      }

      const selectedStates = locations.map(loc => loc.state)
      const selectedCities = locations.map(loc => loc.city)

      const response = await fetch(`${api.baseURL}/api/scheduler/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scheduler_frequency: schedulerFrequency,
          selected_states: selectedStates,
          selected_cities: selectedCities,
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Save settings error:', response.status, errorText)
        throw new Error(`Failed to save settings: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('Scheduler settings saved:', data)
      alert('Scheduler settings saved successfully!')
      setShowSettings(false)
    } catch (error) {
      console.error('Error saving settings:', error)
      alert(`Failed to save settings: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  // Filter opportunities based on recent posts filter
  const filteredOpportunities = recentPostsOnly 
    ? opportunities.filter(o => {
        const twoWeeksAgo = new Date()
        twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14)
        const createdAt = o.created_at || o.saved_at
        if (!createdAt) return false
        const created = new Date(createdAt)
        return created >= twoWeeksAgo
      })
    : opportunities

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-10">
            <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="bg-perscholas-secondary p-2 sm:p-2.5 rounded-xl">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  AI-Powered Opportunity Discovery
                </h2>
              </div>

              <div className="flex items-center gap-3">
                {/* Settings Button */}
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                  title="Open settings"
                >
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </button>

                {/* AI Search Toggle */}
                <label className={`flex items-center justify-between px-2 sm:px-4 py-2 rounded-lg border cursor-pointer transition-all whitespace-nowrap ${
                  aiSearchEnabled
                    ? 'border-perscholas-secondary bg-blue-50'
                    : 'border-gray-300 bg-gray-50'
                }`}>
                  <span className={`text-xs sm:text-sm font-medium mr-2 sm:mr-3 ${aiSearchEnabled ? 'text-perscholas-secondary' : 'text-gray-600'}`}>
                    AI {aiSearchEnabled ? 'On' : 'Off'}
                  </span>
                  <input
                    type="checkbox"
                    checked={aiSearchEnabled}
                    onChange={(e) => setAiSearchEnabled(e.target.checked)}
                    className="w-4 h-4 text-perscholas-secondary rounded focus:ring-2 focus:ring-perscholas-secondary/20"
                  />
                </label>
              </div>
            </div>

            <p className="text-gray-600 text-base sm:text-lg mt-2">
              Deploy an agent to discover funding opportunities tailored to your specific needs. Be specific about focus areas, funding amounts, and deadlines for best results.
            </p>

            {/* Settings Panel */}
            {showSettings && (
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <h3 className="font-semibold text-gray-900 mb-4">Search Settings</h3>

                <div className="space-y-6">
                  {/* Scheduler Frequency */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Scheduler Frequency
                    </label>
                    <select
                      value={schedulerFrequency}
                      onChange={(e) => setSchedulerFrequency(e.target.value as 'daily' | 'weekly' | 'monthly')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">How often the AI search will run automatically</p>
                  </div>

                  {/* Target Locations - Customizable */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Target Locations
                    </label>

                    {/* Current Locations List */}
                    {locations.length > 0 && (
                      <div className="border border-gray-200 rounded-lg p-3 bg-white mb-4 max-h-40 overflow-y-auto">
                        {locations.map((loc, idx) => (
                          <div key={idx} className="flex items-center justify-between py-2 px-2 hover:bg-gray-50 rounded">
                            <span className="text-sm text-gray-700">{loc.state} - {loc.city}</span>
                            <button
                              onClick={() => removeLocation(idx)}
                              className="text-red-500 hover:text-red-700 text-xs font-medium transition-colors"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add New Location */}
                    <div className="space-y-2 mb-4">
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          placeholder="State (e.g., California)"
                          value={newState}
                          onChange={(e) => setNewState(e.target.value)}
                          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                        />
                        <input
                          type="text"
                          placeholder="City (e.g., San Francisco)"
                          value={newCity}
                          onChange={(e) => setNewCity(e.target.value)}
                          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent"
                        />
                      </div>
                      <button
                        onClick={addLocation}
                        className="w-full px-3 py-2 text-sm border border-perscholas-secondary text-perscholas-secondary hover:bg-blue-50 rounded-lg font-medium transition-colors"
                      >
                        Add Location
                      </button>
                    </div>

                    <p className="text-xs text-gray-500">{locations.length} location{locations.length !== 1 ? 's' : ''} configured</p>
                  </div>
                </div>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={saveSchedulerSettings}
                    className="px-4 py-2 bg-perscholas-secondary hover:bg-perscholas-dark text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Save Settings
                  </button>
                  <button
                    onClick={() => setShowSettings(false)}
                    className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 rounded-lg text-sm font-medium transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Search Input Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 mb-8">
          <div className="space-y-6">
            <div>
              <label htmlFor="search-prompt" className="block text-sm font-semibold text-gray-900 mb-3">
                Search Criteria
              </label>
              <textarea
                id="search-prompt"
                value={searchPrompt}
                onChange={(e) => setSearchPrompt(e.target.value)}
                placeholder="Example: Find federal grants for cybersecurity workforce development programs targeting underserved communities in urban areas, amount $100K-$500K, due within 90 days"
                className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-secondary focus:border-transparent resize-none h-24 text-sm"
                disabled={isSearching}
              />
              <p className="text-xs text-gray-500 mt-2">
                Tip: Include funding amount range, timeline, target populations, and specific focus areas for best results.
              </p>
            </div>

            <button
              onClick={searchOpportunities}
              disabled={isSearching || !searchPrompt.trim() || !aiSearchEnabled}
              className="w-full bg-perscholas-secondary hover:bg-perscholas-dark disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2"
            >
              {isSearching ? (
                <>
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Agent Searching...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Deploy AI Search
                </>
              )}
            </button>
          </div>

          {isSearching && (
            <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-xl">
              <div className="flex items-center space-x-3 mb-4">
                <div className="bg-perscholas-secondary p-1.5 rounded-lg flex-shrink-0">
                  <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <span className="text-perscholas-secondary font-semibold">
                  Agent executing search strategy...
                </span>
              </div>
              <div className="space-y-2 text-sm text-gray-700 ml-8">
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Connecting to GRANTS.gov and foundation databases</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Applying semantic analysis for Per Scholas mission alignment</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-perscholas-secondary">✓</span>
                  <span>Scoring opportunities by fit, feasibility, and timeline</span>
                </div>
              </div>
              <div className="mt-4 text-xs text-gray-500 ml-8">
                Processing time: 2-3 minutes for comprehensive analysis
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        {opportunities.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  Discovery Results
                </h2>
                <p className="text-gray-600 text-sm mt-1">
                  {filteredOpportunities.length} of {opportunities.length} opportunities shown
                </p>
              </div>
              
              {/* Recent Posts Filter - Only shows when there are search results */}
              <div className="flex-shrink-0">
                <label className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                  recentPostsOnly
                    ? 'border-blue-500 bg-blue-50 hover:bg-blue-100'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}>
                  <span className={`text-sm font-medium ${recentPostsOnly ? 'text-blue-700' : 'text-gray-700'} mr-3`}>Recent Posts Only (2 weeks)</span>
                  <input
                    type="checkbox"
                    checked={recentPostsOnly}
                    onChange={(e) => setRecentPostsOnly(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500/20"
                  />
                </label>
              </div>
            </div>

            <div className="space-y-6">
              {filteredOpportunities.map((opp) => {
                const colors = getMatchColor(opp.match_score)
                const isSaving = savingIds.has(opp.id)

                return (
                  <div
                    key={opp.id}
                    className="border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow duration-200"
                  >
                    {/* Header with Title and Match Score */}
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 leading-snug mb-1">
                          {opp.title}
                        </h3>
                        <p className="text-sm text-gray-600 font-medium">{opp.funder}</p>
                      </div>
                      <div className={`${colors.bg} ${colors.text} px-3.5 py-1.5 rounded-lg text-sm font-semibold flex-shrink-0 whitespace-nowrap`}>
                        {opp.match_score}% Match
                      </div>
                    </div>

                    {/* Key Metrics */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-6 mb-6 pb-6 border-b border-gray-200">
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Funding Amount</span>
                        <span className="text-base sm:text-lg font-bold text-green-600">{formatCurrency(opp.amount)}</span>
                      </div>
                      <div className="sm:text-center">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Deadline</span>
                        <span className="text-base sm:text-lg font-bold text-gray-900">{formatDate(opp.deadline)}</span>
                      </div>
                      <div className="sm:text-right">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Grant ID</span>
                        <span className="text-xs sm:text-sm font-mono text-gray-700 break-words">{opp.id.slice(0, 12)}...</span>
                      </div>
                    </div>

                    {/* Description */}
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-gray-900 mb-2">Overview</h4>
                      <p className="text-sm text-gray-700 leading-relaxed">{opp.description}</p>
                    </div>

                    {/* Requirements */}
                    {opp.requirements && opp.requirements.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 mb-3">Key Requirements</h4>
                        <div className="space-y-2">
                          {opp.requirements.slice(0, 4).map((req, idx) => (
                            <div key={idx} className="flex items-start gap-2">
                              <span className="text-orange-600 font-bold mt-0.5 flex-shrink-0">•</span>
                              <span className="text-sm text-gray-700">{req}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Contact */}
                    {opp.contact && (
                      <div className="mb-6 pb-6 border-b border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Contact</h4>
                        <a href={`mailto:${opp.contact}`} className="text-sm text-perscholas-secondary hover:underline">
                          {opp.contact}
                        </a>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="grid grid-cols-1 sm:flex gap-3">
                      {opp.application_url && (
                        <a
                          href={opp.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-center sm:justify-start gap-2 border border-perscholas-secondary text-perscholas-secondary px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          View Opportunity
                        </a>
                      )}
                      <button
                        onClick={() => saveOpportunity(opp.id)}
                        disabled={isSaving}
                        className="flex items-center justify-center sm:justify-start gap-2 bg-perscholas-secondary hover:bg-perscholas-dark disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors w-full sm:w-auto"
                      >
                        {isSaving ? (
                          <>
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Saving...
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Save to Opportunities
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {opportunities.length === 0 && !isSearching && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-16 text-center">
            <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-2xl flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">
              Ready to Discover Opportunities
            </h3>
            <p className="text-gray-600 text-lg mb-8">
              Enter your search criteria above to deploy the AI agent and discover funding opportunities tailored to Per Scholas.
            </p>
            <a
              href="/opportunities"
              className="inline-flex items-center gap-2 bg-perscholas-secondary text-white px-8 py-3 rounded-lg font-semibold hover:bg-perscholas-dark transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              View Saved Opportunities
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
