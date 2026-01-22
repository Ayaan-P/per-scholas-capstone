'use client'

export const dynamic = 'force-dynamic'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    router.push('/dashboard')
  }, [router])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center animate-fade-in">
        {/* Logo-style loading spinner */}
        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-2xl bg-perscholas-primary/10 flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-perscholas-primary animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          {/* Rotating ring */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-20 h-20 border-2 border-perscholas-primary/20 border-t-perscholas-primary rounded-full animate-spin"></div>
          </div>
        </div>
        <p className="text-gray-600 font-medium">Loading FundFish...</p>
      </div>
    </div>
  )
}
