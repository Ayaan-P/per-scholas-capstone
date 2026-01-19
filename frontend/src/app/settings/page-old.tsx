'use client'

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { ProtectedRoute } from '../../components/ProtectedRoute'

interface OrganizationConfig {
  id?: string
  name: string
  mission: string
  focus_areas: string[]
  impact_metrics: Record<string, string | number>
  programs: string[]
  target_demographics: string[]
}

export default function SettingsPage() {
  const [config, setConfig] = useState<OrganizationConfig>({
    name: 'Your Organization',
    mission: '',
    focus_areas: [],
    impact_metrics: {},
    programs: [],
    target_demographics: []
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [newFocusArea, setNewFocusArea] = useState('')
  const [newProgram, setNewProgram] = useState('')
  const [newDemographic, setNewDemographic] = useState('')
  const [newMetricKey, setNewMetricKey] = useState('')
  const [newMetricValue, setNewMetricValue] = useState('')

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await api.getOrganizationConfig()
        if (response.ok) {
          const data = await response.json()
          setConfig(data)
        }
      } catch (error) {
        console.error('Failed to load organization config:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await api.saveOrganizationConfig(config)

      if (response.ok) {
        setMessage('Organization configuration saved successfully!')
        setTimeout(() => setMessage(''), 3000)
      } else {
        setMessage('Failed to save configuration')
      }
    } catch (error) {
      setMessage('Error saving configuration')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const addFocusArea = () => {
    if (newFocusArea.trim()) {
      setConfig(prev => ({
        ...prev,
        focus_areas: [...prev.focus_areas, newFocusArea]
      }))
      setNewFocusArea('')
    }
  }

  const removeFocusArea = (index: number) => {
    setConfig(prev => ({
      ...prev,
      focus_areas: prev.focus_areas.filter((_, i) => i !== index)
    }))
  }

  const addProgram = () => {
    if (newProgram.trim()) {
      setConfig(prev => ({
        ...prev,
        programs: [...prev.programs, newProgram]
      }))
      setNewProgram('')
    }
  }

  const removeProgram = (index: number) => {
    setConfig(prev => ({
      ...prev,
      programs: prev.programs.filter((_, i) => i !== index)
    }))
  }

  const addDemographic = () => {
    if (newDemographic.trim()) {
      setConfig(prev => ({
        ...prev,
        target_demographics: [...prev.target_demographics, newDemographic]
      }))
      setNewDemographic('')
    }
  }

  const removeDemographic = (index: number) => {
    setConfig(prev => ({
      ...prev,
      target_demographics: prev.target_demographics.filter((_, i) => i !== index)
    }))
  }

  const addMetric = () => {
    if (newMetricKey.trim() && newMetricValue) {
      setConfig(prev => ({
        ...prev,
        impact_metrics: {
          ...prev.impact_metrics,
          [newMetricKey]: newMetricValue
        }
      }))
      setNewMetricKey('')
      setNewMetricValue('')
    }
  }

  const removeMetric = (key: string) => {
    setConfig(prev => ({
      ...prev,
      impact_metrics: Object.fromEntries(
        Object.entries(prev.impact_metrics).filter(([k]) => k !== key)
      )
    }))
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center text-gray-500">Loading organization settings...</div>
      </div>
    )
  }

  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Organization Settings</h1>

        {message && (
          <div className="mb-6 p-4 rounded-lg bg-blue-50 border border-blue-200 text-blue-800">
            {message}
          </div>
        )}

        {/* Organization Name */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Organization Name
          </label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig({ ...config, name: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Your Organization"
          />
        </div>

        {/* Mission */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Organization Mission
          </label>
          <textarea
            value={config.mission}
            onChange={(e) => setConfig({ ...config, mission: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Describe your organization's mission"
            rows={3}
          />
        </div>

        {/* Focus Areas */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Focus Areas
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newFocusArea}
              onChange={(e) => setNewFocusArea(e.target.value)}
              placeholder="Add focus area"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addFocusArea}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {config.focus_areas.map((area, index) => (
              <span key={index} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full flex items-center gap-2">
                {area}
                <button
                  onClick={() => removeFocusArea(index)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Programs */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Programs
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newProgram}
              onChange={(e) => setNewProgram(e.target.value)}
              placeholder="Add program"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addProgram}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add
            </button>
          </div>
          <ul className="space-y-2">
            {config.programs.map((prog, index) => (
              <li key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                {prog}
                <button
                  onClick={() => removeProgram(index)}
                  className="text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Target Demographics */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Target Demographics
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newDemographic}
              onChange={(e) => setNewDemographic(e.target.value)}
              placeholder="Add demographic"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addDemographic}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {config.target_demographics.map((demo, index) => (
              <span key={index} className="bg-green-100 text-green-800 px-3 py-1 rounded-full flex items-center gap-2">
                {demo}
                <button
                  onClick={() => removeDemographic(index)}
                  className="text-green-600 hover:text-green-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Impact Metrics */}
        <div className="mb-8">
          <label className="block text-sm font-semibold text-gray-900 mb-2">
            Impact Metrics
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newMetricKey}
              onChange={(e) => setNewMetricKey(e.target.value)}
              placeholder="Metric name (e.g., 'graduates')"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              value={newMetricValue}
              onChange={(e) => setNewMetricValue(e.target.value)}
              placeholder="Metric value (e.g., '1000+')"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addMetric}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add
            </button>
          </div>
          <div className="space-y-2">
            {Object.entries(config.impact_metrics).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                <span>{key}: {value}</span>
                <button
                  onClick={() => removeMetric(key)}
                  className="text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Save Button */}
        <div className="flex gap-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  )
}
