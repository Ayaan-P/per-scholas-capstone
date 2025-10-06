import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Per Scholas | Fundraising Intelligence Platform',
  description: 'Enterprise-grade AI platform for funding opportunity discovery and proposal generation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <header className="bg-white shadow-sm border-b">
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
                  <a href="/dashboard" className="text-gray-600 hover:text-perscholas-primary font-medium">
                    Dashboard
                  </a>
                  <a href="/opportunities" className="text-gray-600 hover:text-perscholas-primary font-medium">
                    Opportunities
                  </a>
                  <a href="/proposals" className="text-gray-600 hover:text-perscholas-primary font-medium">
                    Proposals
                  </a>
                  <a href="/analytics" className="text-gray-600 hover:text-perscholas-primary font-medium">
                    Analytics
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