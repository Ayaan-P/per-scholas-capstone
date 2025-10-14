'use client'

import './globals.css'
import { usePathname } from 'next/navigation'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()

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
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center space-x-4">
                <a href="/dashboard" className="flex items-center space-x-4">
                  <h1 className="text-3xl font-bold text-perscholas-primary">Per Scholas</h1>
                  <div className="h-8 w-px bg-gray-300"></div>
                  <span className="text-lg font-medium text-gray-700">
                    Fundraising Intelligence Platform
                  </span>
                </a>
              </div>
              <div className="flex items-center space-x-6">
                <nav className="flex space-x-6">
                  <a 
                    href="/dashboard" 
                    className={`font-medium transition-colors ${
                      isActive('/dashboard') 
                        ? 'text-indigo-600 font-bold border-b-2 border-indigo-600 pb-1' 
                        : 'text-gray-600 hover:text-perscholas-primary'
                    }`}
                  >
                    Discover
                  </a>
                  <a 
                    href="/opportunities" 
                    className={`font-medium transition-colors ${
                      isActive('/opportunities') 
                        ? 'text-indigo-600 font-bold border-b-2 border-indigo-600 pb-1' 
                        : 'text-gray-600 hover:text-perscholas-primary'
                    }`}
                  >
                    Opportunities
                  </a>
                </nav>
              </div>
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  )
}