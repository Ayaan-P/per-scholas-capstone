'use client'

import './globals.css'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isActive = (path: string) => {
    return pathname === path || pathname?.startsWith(path)
  }

  return (
    <html lang="en">
      <head>
        <title>Per Scholas | Fundraising Intelligence Platform</title>
        <meta name="description" content="Enterprise-grade AI platform for funding opportunity discovery and proposal generation" />
      </head>
      <body className="bg-gray-50 min-h-screen">
        <header className="bg-white shadow-sm border-b sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4 sm:py-6">
              {/* Logo - Mobile Responsive */}
              <div className="flex items-center space-x-2 sm:space-x-4">
                <a href="/dashboard" className="flex items-center space-x-2 sm:space-x-4">
                  <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-perscholas-primary">Per Scholas</h1>
                  <div className="hidden sm:block h-6 sm:h-8 w-px bg-gray-300"></div>
                  <span className="hidden md:block text-base lg:text-lg font-medium text-gray-700">
                    Fundraising Intelligence Platform
                  </span>
                </a>
              </div>

              {/* Desktop Navigation */}
              <nav className="hidden md:flex items-center space-x-6">
                <a
                  href="/dashboard"
                  className={`font-medium transition-colors ${
                    isActive('/dashboard')
                      ? 'text-perscholas-primary font-bold border-b-2 border-perscholas-primary pb-1'
                      : 'text-gray-600 hover:text-perscholas-primary'
                  }`}
                >
                  Discover
                </a>
                <a
                  href="/opportunities"
                  className={`font-medium transition-colors ${
                    isActive('/opportunities')
                      ? 'text-perscholas-primary font-bold border-b-2 border-perscholas-primary pb-1'
                      : 'text-gray-600 hover:text-perscholas-primary'
                  }`}
                >
                  Opportunities
                </a>
                <a
                  href="/search"
                  className={`font-medium transition-colors ${
                    isActive('/search')
                      ? 'text-perscholas-primary font-bold border-b-2 border-perscholas-primary pb-1'
                      : 'text-gray-600 hover:text-perscholas-primary'
                  }`}
                >
                  AI Search
                </a>
              </nav>

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
                  <a
                    href="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/dashboard')
                        ? 'text-perscholas-primary font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-perscholas-primary hover:bg-gray-50'
                    }`}
                  >
                    Discover
                  </a>
                  <a
                    href="/opportunities"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/opportunities')
                        ? 'text-perscholas-primary font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-perscholas-primary hover:bg-gray-50'
                    }`}
                  >
                    Opportunities
                  </a>
                  <a
                    href="/search"
                    onClick={() => setMobileMenuOpen(false)}
                    className={`font-medium transition-colors px-4 py-2 rounded-lg ${
                      isActive('/search')
                        ? 'text-perscholas-primary font-bold bg-blue-50'
                        : 'text-gray-600 hover:text-perscholas-primary hover:bg-gray-50'
                    }`}
                  >
                    AI Search
                  </a>
                </nav>
              </div>
            )}
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  )
}