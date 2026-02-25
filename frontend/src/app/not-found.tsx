import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">🔍</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Page not found</h2>
        <p className="text-gray-600 mb-6">
          This page swam away. Let&apos;s get you back on track.
        </p>
        <Link
          href="/"
          className="btn-primary px-6 py-3 rounded-lg font-medium inline-block"
        >
          Back to home
        </Link>
      </div>
    </div>
  )
}
