'use client'

import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
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
    }
  }

  return (
    <header className="glass shadow-premium border-b border-gray-100/50 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-3 sm:py-4">
          {/* Logo */}
          <div className="flex items-center space-x-2 sm:space-x-4">
            <Link href={isAuthenticated ? "/dashboard" : "/"} className="flex items-center space-x-2 sm:space-x-4 group">
              <div className="relative">
                <Image src="/logo.png" alt="FundFish Logo" width={40} height={40} className="h-8 sm:h-10 w-auto transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-perscholas-primary">fundfish</h1>
            </Link>
          </div>

          {/* Desktop Navigation */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center space-x-2">
              <Link
                href="/dashboard"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/dashboard')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Discover
              </Link>
              <Link
                href="/opportunities"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/opportunities')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Opportunities
              </Link>
              <Link
                href="/proposals"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/proposals')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Proposals
              </Link>
              <Link
                href="/chat"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center gap-1.5 ${
                  isActive('/chat')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Agent
              </Link>
              <Link
                href="/settings"
                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                  isActive('/settings')
                    ? 'bg-perscholas-primary text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                }`}
              >
                Settings
              </Link>
            </nav>
          )}

          {/* Auth Actions */}
          <div className="hidden md:flex items-center space-x-3">
            <Link
              href="/about"
              className={`px-3 py-2 rounded-xl font-medium text-sm transition-all duration-200 ${
                isActive('/about')
                  ? 'text-perscholas-primary'
                  : 'text-gray-500 hover:text-perscholas-primary'
              }`}
            >
              About
            </Link>
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
                <Link href="/login" className="btn-ghost">
                  Sign In
                </Link>
                <Link href="/signup" className="btn-primary">
                  Get Started
                </Link>
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
                  <Link
                    href="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/dashboard')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Discover
                  </Link>
                  <Link
                    href="/opportunities"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/opportunities')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Opportunities
                  </Link>
                  <Link
                    href="/proposals"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/proposals')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Proposals
                  </Link>
                  <Link
                    href="/chat"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg flex items-center gap-2 ${
                      isActive('/chat')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Agent
                  </Link>
                  <Link
                    href="/settings"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/settings')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    Settings
                  </Link>
                </>
              )}
                <Link
                href="/about"
                onClick={() => setMobileMenuOpen(false)}
                className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                  isActive('/about')
                    ? 'text-blue-600 font-bold bg-blue-50'
                    : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                }`}
              >
                About
              </Link>
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
                  <Link
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mx-2 btn-ghost"
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/signup"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mx-2 btn-primary"
                  >
                    Get Started
                  </Link>
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}
