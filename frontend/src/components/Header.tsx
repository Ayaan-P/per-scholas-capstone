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
            <Link href="/" className="flex items-center space-x-2 sm:space-x-4 group">
              <div className="relative">
                <Image src="/logo.png" alt="FundFish Logo" width={40} height={40} className="h-8 sm:h-10 w-auto rounded-xl transition-transform duration-300 group-hover:scale-110" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-perscholas-primary">fundfish</h1>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-2">
            {isAuthenticated ? (
              <>
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
                  href="/chat"
                  className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
                    isActive('/chat')
                      ? 'bg-perscholas-primary text-white shadow-md'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                  }`}
                >
                  Agent
                </Link>
              </>
            ) : (
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
            )}
          </nav>

          {/* Auth Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {isAuthenticated ? (
              <>
                <Link
                  href="/settings"
                  className={`p-2 rounded-xl transition-all duration-200 ${
                    isActive('/settings')
                      ? 'text-perscholas-primary bg-gray-100'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-perscholas-primary'
                  }`}
                  title="Settings"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </Link>
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
              {isAuthenticated ? (
                <>
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
                    href="/chat"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/chat')
                        ? 'text-blue-600 font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
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
              ) : (
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
