export default function DashboardLoading() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Stats skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-3" />
            <div className="h-8 bg-gray-200 rounded w-16" />
          </div>
        ))}
      </div>
      {/* Table skeleton */}
      <div className="bg-white rounded-xl p-6">
        <div className="h-6 bg-gray-200 rounded w-48 mb-6" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 py-4 border-b border-gray-100 animate-pulse">
            <div className="h-4 bg-gray-200 rounded flex-1" />
            <div className="h-4 bg-gray-200 rounded w-24" />
            <div className="h-4 bg-gray-200 rounded w-20" />
          </div>
        ))}
      </div>
    </div>
  )
}
