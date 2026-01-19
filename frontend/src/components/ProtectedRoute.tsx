'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '../context/AuthContext'
import { useEffect, useState } from 'react'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()
  const [showContent, setShowContent] = useState(false)

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login')
    } else if (!loading && isAuthenticated) {
      setShowContent(true)
    }
  }, [isAuthenticated, loading, router])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!showContent) {
    return null
  }

  return <>{children}</>
}
