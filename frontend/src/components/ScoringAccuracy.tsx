'use client'

import { useState, useEffect } from 'react'
import { api } from '../utils/api'

interface AccuracyMetrics {
  precision: number
  recall: number
  sample_size: number
  insufficient_data?: boolean
}

interface AccuracyData {
  org_id: string
  current_version: string
  total_scored: number
  feedback_count: number
  accuracy: AccuracyMetrics
  evolution_count: number
}

export default function ScoringAccuracy() {
  const [data, setData] = useState<AccuracyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    loadAccuracy()
  }, [])

  const loadAccuracy = async () => {
    try {
      const response = await api.getScoringAccuracy()
      if (response.ok) {
        const accuracyData = await response.json()
        setData(accuracyData)
      } else {
        setError(true)
      }
    } catch (e) {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  if (loading || error || !data) {
    return null // Silent fail
  }

  const { accuracy, feedback_count, evolution_count } = data

  if (accuracy.insufficient_data) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🧠</span>
          <div>
            <h4 className="font-semibold text-gray-900">Agent Learning</h4>
            <p className="text-sm text-gray-600">
              Your agent is gathering data to improve grant matching. {feedback_count} interactions so far.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const precisionPct = Math.round(accuracy.precision * 100)
  const recallPct = Math.round(accuracy.recall * 100)
  const overallScore = Math.round((accuracy.precision + accuracy.recall) / 2 * 100)

  let statusColor = 'yellow'
  let statusEmoji = '📊'
  let statusText = 'Learning'

  if (overallScore >= 80) {
    statusColor = 'green'
    statusEmoji = '✨'
    statusText = 'Highly Accurate'
  } else if (overallScore >= 60) {
    statusColor = 'blue'
    statusEmoji = '🎯'
    statusText = 'Improving'
  }

  return (
    <div className={`bg-${statusColor}-50 border border-${statusColor}-200 rounded-lg p-4`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{statusEmoji}</span>
          <div>
            <h4 className="font-semibold text-gray-900">Agent {statusText}</h4>
            <p className="text-sm text-gray-600">
              {overallScore}% accuracy • {feedback_count} interactions • {evolution_count} improvements
            </p>
          </div>
        </div>
        
        <div className="flex gap-3 text-xs">
          <div className="text-center">
            <div className="font-semibold text-gray-900">{precisionPct}%</div>
            <div className="text-gray-500">Precision</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-gray-900">{recallPct}%</div>
            <div className="text-gray-500">Recall</div>
          </div>
        </div>
      </div>
      
      {evolution_count > 0 && (
        <p className="text-xs text-gray-600 mt-2">
          💡 Your agent has evolved its scoring algorithm {evolution_count} time{evolution_count > 1 ? 's' : ''} based on your feedback.
        </p>
      )}
    </div>
  )
}
