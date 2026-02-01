'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log to error reporting service in production
  }, [error])

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">🐟</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Something went wrong</h2>
        <p className="text-gray-600 mb-6">
          We hit a snag. This has been noted and we&apos;re working on it.
        </p>
        <button
          onClick={reset}
          className="btn-primary px-6 py-3 rounded-lg font-medium"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
