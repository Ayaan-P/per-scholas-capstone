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
    <header className="bg-white shadow-sm border-b sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4 sm:py-6">
          {/* Logo */}
          <div className="flex items-center space-x-2 sm:space-x-4">
            <a href={isAuthenticated ? "/dashboard" : "/"} className="flex items-center space-x-2 sm:space-x-4">
              <Image src="/logo.png" alt="FundFish Logo" width={40} height={40} className="h-8 sm:h-10 w-auto" />
              <h1 className="text-xl sm:text-2xl font-bold" style={{color: '#c2e9ff'}}>fundfish</h1>
            </a>
          </div>

          {/* Desktop Navigation */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center space-x-6">
              <a
                href="/dashboard"
                className={`font-medium transition-colors ${
                  isActive('/dashboard')
                    ? 'text-blue-600 font-bold border-b-2 border-blue-600 pb-1'
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Discover
              </a>
              <a
                href="/opportunities"
                className={`font-medium transition-colors ${
                  isActive('/opportunities')
                    ? 'text-blue-600 font-bold border-b-2 border-blue-600 pb-1'
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Opportunities
              </a>
              <a
                href="/search"
                className={`font-medium transition-colors ${
                  isActive('/search')
                    ? 'text-blue-600 font-bold border-b-2 border-blue-600 pb-1'
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                AI Search
              </a>
              <a
                href="/settings"
                className={`font-medium transition-colors ${
                  isActive('/settings')
                    ? 'text-blue-600 font-bold border-b-2 border-blue-600 pb-1'
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Settings
              </a>
            </nav>
          )}

          {/* Auth Actions */}
          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-gray-600">{user?.email}</span>
                <button
                  onClick={handleSignOut}
                  className="px-4 py-2 text-gray-700 hover:text-blue-600 font-medium"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <a href="/login" className="px-4 py-2 text-gray-700 hover:text-blue-600 font-medium">
                  Sign In
                </a>
                <a href="/signup" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
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
          <div className="md:hidden border-t border-gray-200 py-4">
            <nav className="flex flex-col space-y-4">
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
                  <div className="px-4 py-2 text-sm text-gray-600 border-t border-gray-200">
                    {user?.email}
                  </div>
                  <button
                    onClick={handleSignOut}
                    className="px-4 py-2 text-left text-red-600 hover:text-red-700 font-medium"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <a
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="px-4 py-2 text-gray-700 hover:text-blue-600 font-medium"
                  >
                    Sign In
                  </a>
                  <a
                    href="/signup"
                    onClick={() => setMobileMenuOpen(false)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
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
