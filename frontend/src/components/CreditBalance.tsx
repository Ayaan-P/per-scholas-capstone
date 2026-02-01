'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../utils/supabaseClient'

interface CreditData {
  total_credits: number
  monthly_credits_used: number
  monthly_reset_date: string
}

interface SubscriptionData {
  plan_name: string
  monthly_credits: number
  status: string
}

export function CreditBalance() {
  const { isAuthenticated } = useAuth()
  const [credits, setCredits] = useState<CreditData | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) return

    const fetchCredits = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const token = session?.access_token

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

        const response = await fetch(`${apiUrl}/api/credits/balance`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (response.ok) {
          const data = await response.json()
          setCredits(data)
        }

        const subResponse = await fetch(`${apiUrl}/api/credits/subscription`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (subResponse.ok) {
          const subData = await subResponse.json()
          setSubscription(subData)
        }
      } catch (error) {
      } finally {
        setLoading(false)
      }
    }

    fetchCredits()
  }, [isAuthenticated])

  if (!isAuthenticated || loading) return null

  const searchesRemaining = credits ? credits.total_credits : 0
  const planName = subscription?.plan_name === 'pro' ? 'Pro' : 'Free'

  return (
    <div className="flex items-center gap-3">
      <div className="flex flex-col items-end">
        <div className="text-sm font-semibold text-perscholas-primary">
          {searchesRemaining} searches
        </div>
        <div className="text-xs text-gray-600">
          {planName} tier
        </div>
      </div>
      <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center border border-blue-200">
        <span className="text-lg font-bold text-perscholas-primary">{searchesRemaining}</span>
      </div>
    </div>
  )
}

