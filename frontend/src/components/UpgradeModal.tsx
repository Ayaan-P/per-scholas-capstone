'use client'

import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../utils/supabaseClient'

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  reason?: 'insufficient_credits' | 'upgrade'
}

export function UpgradeModal({ isOpen, onClose, reason = 'upgrade' }: UpgradeModalProps) {
  const { user } = useAuth()
  const [selectedOption, setSelectedOption] = useState<'pro' | '10' | '20' | '100'>('pro')
  const [loading, setLoading] = useState(false)

  const options = [
    {
      id: 'pro' as const,
      name: 'Pro Plan',
      price: '$10/month',
      credits: '10 searches',
      description: 'Monthly recurring subscription',
      color: 'bg-blue-50 border-blue-300',
      highlight: true,
    },
    {
      id: '10' as const,
      name: '10 Credits',
      price: '$10',
      credits: '10 one-time searches',
      description: 'Use anytime',
      color: 'bg-gray-50 border-gray-300',
    },
    {
      id: '20' as const,
      name: '20 Credits',
      price: '$20',
      credits: '20 one-time searches',
      description: 'Better value',
      color: 'bg-gray-50 border-gray-300',
    },
    {
      id: '100' as const,
      name: '100 Credits',
      price: '$100',
      credits: '100 one-time searches',
      description: 'Best value',
      color: 'bg-gray-50 border-gray-300',
    },
  ]

  const handleCheckout = async () => {
    if (!user) return

    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      if (!token) {
        throw new Error('Not authenticated')
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      if (selectedOption === 'pro') {
        // Upgrade subscription
        const response = await fetch(`${apiUrl}/api/credits/subscription/upgrade`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            plan: 'pro',
            success_url: `${window.location.origin}/dashboard?subscription=success`,
            cancel_url: `${window.location.origin}/dashboard?subscription=cancelled`,
          }),
        })

        const data = await response.json()
        if (data.checkout_url) {
          window.location.href = data.checkout_url
        }
      } else {
        // Purchase credits package
        const packageMap = {
          '10': '10_credits',
          '20': '20_credits',
          '100': '100_credits',
        }

        const response = await fetch(`${apiUrl}/api/credits/purchase/checkout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            package_id: packageMap[selectedOption as keyof typeof packageMap],
            success_url: `${window.location.origin}/dashboard?purchase=success`,
            cancel_url: `${window.location.origin}/dashboard?purchase=cancelled`,
          }),
        })

        const data = await response.json()
        if (data.checkout_url) {
          window.location.href = data.checkout_url
        }
      }
    } catch (error) {
      console.error('Checkout error:', error)
      alert('Failed to start checkout. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const selectedData = options.find((o) => o.id === selectedOption)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {reason === 'insufficient_credits' ? 'Need More Searches?' : 'Upgrade Your Plan'}
            </h2>
            {reason === 'insufficient_credits' && (
              <p className="text-gray-600 text-sm mt-1">
                You've used all your monthly searches. Purchase more credits or upgrade to Pro.
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Options Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {options.map((option) => (
              <button
                key={option.id}
                onClick={() => setSelectedOption(option.id)}
                className={`relative p-4 rounded-lg border-2 transition-all ${
                  selectedOption === option.id
                    ? 'border-perscholas-primary bg-blue-50'
                    : option.color + ' border-gray-300 hover:border-gray-400'
                }`}
              >
                {option.highlight && selectedOption !== option.id && (
                  <div className="absolute top-2 right-2 bg-perscholas-primary text-white text-xs font-semibold px-2 py-1 rounded">
                    Popular
                  </div>
                )}

                {selectedOption === option.id && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-perscholas-primary text-white rounded-full flex items-center justify-center text-sm">
                    ✓
                  </div>
                )}

                <div className="text-left">
                  <h3 className="font-semibold text-gray-900">{option.name}</h3>
                  <p className="text-2xl font-bold text-perscholas-primary mt-2">{option.price}</p>
                  <p className="text-sm text-gray-600 mt-1">{option.credits}</p>
                  <p className="text-xs text-gray-500 mt-2">{option.description}</p>
                </div>
              </button>
            ))}
          </div>

          {/* Features */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <h4 className="font-semibold text-gray-900 text-sm">What's included:</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              {selectedOption === 'pro' ? (
                <>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    10 searches per month
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Automatic monthly reset
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Cancel anytime
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Priority support
                  </li>
                </>
              ) : (
                <>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    {selectedOption === '10'
                      ? '10 one-time searches'
                      : selectedOption === '20'
                      ? '20 one-time searches'
                      : '100 one-time searches'}
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Use anytime, no expiration
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Combine with monthly credits
                  </li>
                </>
              )}
            </ul>
          </div>

          {/* CTA */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCheckout}
              disabled={loading}
              className="flex-1 px-4 py-3 bg-perscholas-primary text-white rounded-lg hover:bg-perscholas-dark disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center gap-2"
            >
              {loading && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              )}
              {loading ? 'Processing...' : 'Continue to Payment'}
            </button>
          </div>

          {/* Security Note */}
          <p className="text-xs text-gray-600 text-center">
            💳 Powered by Stripe. Your payment information is secure and encrypted.
          </p>
        </div>
      </div>
    </div>
  )
}
