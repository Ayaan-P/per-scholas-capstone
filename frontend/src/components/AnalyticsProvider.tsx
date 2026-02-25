'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { initAnalytics, trackPage, identify, reset } from '@/lib/analytics'
import { useAuth } from '@/context/AuthContext'

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { user, isAuthenticated } = useAuth()

  // Initialize analytics on mount
  useEffect(() => {
    initAnalytics('fundfish')
  }, [])

  // Track page views on route changes
  useEffect(() => {
    if (pathname) {
      // Map pathname to friendly page name
      const pageName = getPageName(pathname)
      trackPage(pageName, {
        query: searchParams?.toString() || ''
      })
    }
  }, [pathname, searchParams])

  // Identify user when auth state changes
  useEffect(() => {
    if (isAuthenticated && user) {
      identify(user.id, {
        email: user.email,
        organization: user.user_metadata?.organization_name || '',
        created_at: user.created_at
      })
    } else if (!isAuthenticated) {
      reset()
    }
  }, [isAuthenticated, user])

  return <>{children}</>
}

// Helper to map paths to friendly page names
function getPageName(pathname: string): string {
  const routes: Record<string, string> = {
    '/': 'Home',
    '/login': 'Login',
    '/signup': 'Signup',
    '/dashboard': 'Dashboard',
    '/search': 'Grant Search',
    '/opportunities': 'Opportunities',
    '/proposals': 'Proposals',
    '/onboarding': 'Onboarding',
    '/settings': 'Settings',
    '/about': 'About',
    '/analytics': 'Analytics',
    '/blog': 'Blog',
  }
  if (pathname.startsWith('/blog/')) return `Blog Post: ${pathname.replace('/blog/', '')}`
  return routes[pathname] || pathname
}
