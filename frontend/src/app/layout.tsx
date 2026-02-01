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
          <title>FundFish | AI Fundraising for Nonprofits</title>
          <meta name="description" content="AI-powered grant discovery, proposal writing, and fundraising intelligence for nonprofits. Find funding faster with FundFish." />
          <meta name="keywords" content="nonprofit fundraising, grant discovery, AI grants, proposal writing, funding opportunities, nonprofit technology" />
          <meta name="author" content="FundFish" />
          <meta name="robots" content="index, follow" />
          <link rel="canonical" href="https://fundfish.pro" />

          {/* Open Graph */}
          <meta property="og:type" content="website" />
          <meta property="og:url" content="https://fundfish.pro" />
          <meta property="og:title" content="FundFish | AI Fundraising for Nonprofits" />
          <meta property="og:description" content="AI-powered grant discovery, proposal writing, and fundraising intelligence for nonprofits. Find funding faster with FundFish." />
          <meta property="og:image" content="https://fundfish.pro/logo.png" />
          <meta property="og:site_name" content="FundFish" />

          {/* Twitter Card */}
          <meta name="twitter:card" content="summary_large_image" />
          <meta name="twitter:title" content="FundFish | AI Fundraising for Nonprofits" />
          <meta name="twitter:description" content="AI-powered grant discovery, proposal writing, and fundraising intelligence for nonprofits." />
          <meta name="twitter:image" content="https://fundfish.pro/logo.png" />

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
