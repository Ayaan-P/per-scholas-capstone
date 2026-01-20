import { Suspense } from 'react'
import SearchPageContent from './search-content'

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div>Loading...</div></div>}>
      <SearchPageContent />
    </Suspense>
  )
}
