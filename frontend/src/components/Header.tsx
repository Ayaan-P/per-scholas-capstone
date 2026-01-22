'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '../context/AuthContext'
import { useState, useEffect } from 'react'
import Image from 'next/image'

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, signOut, isAuthenticated, loading } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Debug: Log when auth state changes
  useEffect(() => {
    console.log('[Header] Auth state changed:', { isAuthenticated, email: user?.email, loading })
  }, [isAuthenticated, user?.email, loading])

  const isActive = (path: string) => {
    return pathname === path || pathname?.startsWith(path)
  }

  const handleSignOut = async () => {
    try {
      await signOut()
      setMobileMenuOpen(false)
      router.push('/login')
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <header className="glass shadow-premium border-b border-gray-100/50 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-3 sm:py-4">
          {/* Logo */}
          <div className="flex items-center space-x-2 sm:space-x-4">
            <a href={isAuthenticated ? "/dashboard" : "/"} className="flex items-center space-x-2 sm:space-x-4 group">
              <div className="relative">
                <Image src="/logo.png" alt="FundFish Logo" width={40} height={40} className="h-8 sm:h-10 w-auto transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-perscholas-primary">fundfish</h1>
            </a>
          </div>

          {/* Desktop Navigation */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center space-x-2">
              <a
                href="/dashboard"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/dashboard')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Discover
              </a>
              <a
                href="/opportunities"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/opportunities')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Opportunities
              </a>
              <a
                href="/search"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/search')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                AI Search
              </a>
              <a
                href="/settings"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/settings')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Settings
              </a>
            </nav>
          )}

          {/* Auth Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-gray-600 px-3 py-1.5 bg-gray-100 rounded-full">{user?.email}</span>
                <button
                  onClick={handleSignOut}
                  className="btn-ghost text-red-600 hover:bg-red-50 hover:text-red-700"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <a href="/login" className="btn-ghost">
                  Sign In
                </a>
                <a href="/signup" className="btn-primary">
                  Get Started
                </a>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 py-4 animate-slide-up">
            <nav className="flex flex-col space-y-2">
              {isAuthenticated && (
                <>
                  <a
                    href="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/dashboard')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Discover
                  </a>
                  <a
                    href="/opportunities"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/opportunities')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Opportunities
                  </a>
                  <a
                    href="/search"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/search')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    AI Search
                  </a>
                  <a
                    href="/settings"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/settings')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Settings
                  </a>
                </>
              )}
              {isAuthenticated ? (
                <>
                  <div className="px-4 py-2 text-sm text-gray-600 border-t border-gray-200 mt-2">
                    {user?.email}
                  </div>
                  <button
                    onClick={handleSignOut}
                    className="mx-2 px-4 py-2 text-left text-red-600 hover:text-red-700 font-semibold rounded-xl hover:bg-red-50 transition-all duration-200"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <a
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mx-2 btn-ghost"
                  >
                    Sign In
                  </a>
                  <a
                    href="/signup"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mx-2 btn-primary"
                  >
                    Get Started
                  </a>
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}
