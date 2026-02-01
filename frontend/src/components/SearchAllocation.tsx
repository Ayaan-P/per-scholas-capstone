'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../utils/supabaseClient'

interface AllocationData {
  total_credits: number
  monthly_credits_used: number
  plan_name: string
  monthly_credits: number
}

export function SearchAllocation({ onUpgrade }: { onUpgrade?: () => void }) {
  const { isAuthenticated } = useAuth()
  const [allocation, setAllocation] = useState<AllocationData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) return

    const fetchAllocation = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const token = session?.access_token

        if (!token) return

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

        const creditRes = await fetch(`${apiUrl}/api/credits/balance`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const creditData = await creditRes.json()

        const subRes = await fetch(`${apiUrl}/api/credits/subscription`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const subData = await subRes.json()

        setAllocation({
          total_credits: creditData.total_credits,
          monthly_credits_used: creditData.monthly_credits_used,
          plan_name: subData.plan_name,
          monthly_credits: subData.monthly_credits,
        })
      } catch (error) {
      } finally {
        setLoading(false)
      }
    }

    fetchAllocation()
  }, [isAuthenticated])

  if (!isAuthenticated || loading || !allocation) return null

  const remaining = allocation.total_credits
  const monthly = allocation.monthly_credits
  const percentUsed = ((allocation.monthly_credits_used / monthly) * 100)
  const isFreeUser = allocation.plan_name === 'free'

  return (
    <div className="bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Monthly Search Allocation</h3>
          <p className="text-xs text-gray-600 mt-1">
            {isFreeUser ? 'Free plan' : 'Pro plan'}
          </p>
        </div>
        {isFreeUser && onUpgrade && (
          <button
            onClick={onUpgrade}
            className="text-xs font-semibold text-perscholas-primary hover:text-perscholas-dark underline"
          >
            Upgrade
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            {remaining} of {monthly} searches available
          </span>
          <span className="text-xs font-medium text-gray-600">
            {Math.round(percentUsed)}% used
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              percentUsed >= 90 ? 'bg-red-500' :
              percentUsed >= 70 ? 'bg-yellow-500' :
              'bg-green-500'
            }`}
            style={{ width: `${percentUsed}%` }}
          />
        </div>
      </div>

      {/* Info Text */}
      <div className="text-xs text-gray-700 bg-white bg-opacity-50 rounded p-2">
        {remaining === 0 ? (
          <span className="text-red-600 font-medium">
            ⚠️ No searches available this month. Purchase more credits or wait for your monthly reset.
          </span>
        ) : remaining <= 2 ? (
          <span className="text-yellow-600 font-medium">
            ⚠️ Only {remaining} search{remaining === 1 ? '' : 'es'} remaining. Consider purchasing more.
          </span>
        ) : (
          <span>
            You have <strong>{remaining} search{remaining === 1 ? '' : 'es'}</strong> allocated for this month.
            {isFreeUser && ' Upgrade to Pro for 10 searches/month.'}
          </span>
        )}
      </div>

      {/* Monthly Reset Info */}
      <div className="text-xs text-gray-600 flex items-center gap-2">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Credits reset monthly
      </div>
    </div>
  )
}
