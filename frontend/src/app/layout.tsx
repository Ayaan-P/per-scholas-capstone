'use client'

import './globals.css'
import { AuthProvider } from '../context/AuthContext'
import { Header } from '../components/Header'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <html lang="en">
        <head>
          <title>FundFish | Fundraising Intelligence Platform</title>
          <meta name="description" content="Enterprise-grade AI platform for funding opportunity discovery and proposal generation for nonprofits" />
          <link rel="icon" href="/logo.png" />
          <link rel="apple-touch-icon" href="/logo.png" />
        </head>
        <body className="bg-gray-50 min-h-screen">
          <Header />
          <main>{children}</main>
        </body>
      </html>
    </AuthProvider>
  )
}
