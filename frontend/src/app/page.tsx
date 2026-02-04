'use client'

export const dynamic = 'force-dynamic'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../context/AuthContext'
import Image from 'next/image'

export default function Home() {
  const router = useRouter()
  const { isAuthenticated, loading } = useAuth()

  // If already logged in, redirect to dashboard
  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, loading, router])

  // Show landing page for unauthenticated users
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-16 h-16 border-2 border-perscholas-primary/20 border-t-perscholas-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (isAuthenticated) {
    return null // Will redirect via useEffect
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-blue-50/30 to-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-32">
        {/* Background decoration */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-perscholas-secondary/5 rounded-full blur-3xl translate-x-1/3 -translate-y-1/3" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-perscholas-accent/10 rounded-full blur-3xl -translate-x-1/3 translate-y-1/3" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-4xl mx-auto">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 bg-perscholas-primary/5 border border-perscholas-primary/10 rounded-full px-4 py-1.5 mb-8">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-perscholas-primary">AI-Powered Grant Discovery</span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 mb-6 leading-[1.1]">
              Find grants that{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-perscholas-primary to-perscholas-secondary">
                actually match
              </span>{' '}
              your mission
            </h1>

            {/* Subheadline */}
            <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
              FundFish uses AI to scan thousands of funding opportunities and match them to your nonprofit&apos;s profile — so you spend less time searching and more time winning grants.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/signup"
                className="inline-flex items-center justify-center gap-2 bg-perscholas-primary hover:bg-perscholas-dark text-white font-semibold text-lg px-8 py-4 rounded-xl shadow-premium hover:shadow-premium-lg transition-all duration-300 transform hover:-translate-y-0.5"
              >
                Start Free
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </a>
              <a
                href="/login"
                className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-700 font-semibold text-lg px-8 py-4 rounded-xl border border-gray-200 shadow-card hover:shadow-card-hover transition-all duration-300"
              >
                Sign In
              </a>
            </div>

            {/* Social proof */}
            <p className="mt-8 text-sm text-gray-400">
              Free tier includes 5 AI searches/month · No credit card required
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              How FundFish works
            </h2>
            <p className="text-lg text-gray-500 max-w-2xl mx-auto">
              Three steps from signup to a pipeline full of matched opportunities.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
            {/* Step 1 */}
            <div className="relative group">
              <div className="flex flex-col items-center text-center p-8 rounded-2xl border border-gray-100 bg-white shadow-card hover:shadow-card-hover transition-all duration-300">
                <div className="w-14 h-14 rounded-2xl bg-perscholas-primary/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <svg className="w-7 h-7 text-perscholas-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                <div className="text-xs font-bold text-perscholas-primary/60 uppercase tracking-wider mb-2">Step 1</div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">Set up your profile</h3>
                <p className="text-gray-500 leading-relaxed">
                  Tell us about your nonprofit — mission, programs, budget, and target populations. Upload documents and we&apos;ll auto-extract the rest.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="relative group">
              <div className="flex flex-col items-center text-center p-8 rounded-2xl border border-gray-100 bg-white shadow-card hover:shadow-card-hover transition-all duration-300">
                <div className="w-14 h-14 rounded-2xl bg-perscholas-secondary/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <svg className="w-7 h-7 text-perscholas-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div className="text-xs font-bold text-perscholas-secondary/60 uppercase tracking-wider mb-2">Step 2</div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">AI discovers grants</h3>
                <p className="text-gray-500 leading-relaxed">
                  Our AI agents scan Grants.gov, state databases, and foundation directories — then score each opportunity against your profile.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="relative group">
              <div className="flex flex-col items-center text-center p-8 rounded-2xl border border-gray-100 bg-white shadow-card hover:shadow-card-hover transition-all duration-300">
                <div className="w-14 h-14 rounded-2xl bg-perscholas-accent/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <svg className="w-7 h-7 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="text-xs font-bold text-yellow-600/60 uppercase tracking-wider mb-2">Step 3</div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">Win more funding</h3>
                <p className="text-gray-500 leading-relaxed">
                  Review matched opportunities, generate AI-drafted proposals, and track your pipeline — all from one dashboard.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 sm:py-28 bg-gray-50/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Built for nonprofit teams
            </h2>
            <p className="text-lg text-gray-500 max-w-2xl mx-auto">
              Everything you need to find, evaluate, and apply for grants — powered by AI.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: '🤖',
                title: 'AI Grant Matching',
                desc: 'Personalized match scores based on your mission, budget, programs, and demographics.',
              },
              {
                icon: '📡',
                title: 'Auto-Discovery',
                desc: 'Scheduled scrapers pull from Grants.gov, state portals, and foundation databases daily.',
              },
              {
                icon: '📝',
                title: 'Proposal Generator',
                desc: 'AI drafts full grant proposals tailored to each funder\'s requirements and priorities.',
              },
              {
                icon: '📊',
                title: 'Pipeline Dashboard',
                desc: 'Track opportunities from discovery to submission. See funding totals and match trends.',
              },
              {
                icon: '📄',
                title: 'Document Intelligence',
                desc: 'Upload your org documents — AI extracts mission, programs, and metrics automatically.',
              },
              {
                icon: '🔒',
                title: 'Secure & Private',
                desc: 'Your data stays yours. Auth-protected API, encrypted at rest, no data sharing.',
              },
            ].map((feature, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl p-6 border border-gray-100 shadow-card hover:shadow-card-hover transition-all duration-300"
              >
                <div className="text-3xl mb-4">{feature.icon}</div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 sm:py-28">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="bg-gradient-to-br from-perscholas-primary to-perscholas-dark rounded-3xl p-10 sm:p-16 shadow-premium-xl relative overflow-hidden">
            {/* Decoration */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

            <div className="relative">
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                Stop searching. Start winning.
              </h2>
              <p className="text-blue-100 text-lg mb-8 max-w-xl mx-auto">
                Join nonprofits using FundFish to discover grants faster, write better proposals, and secure more funding.
              </p>
              <a
                href="/signup"
                className="inline-flex items-center justify-center gap-2 bg-white hover:bg-blue-50 text-perscholas-primary font-bold text-lg px-10 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-0.5"
              >
                Get Started Free
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Image src="/logo.png" alt="FundFish" width={28} height={28} className="h-7 w-auto" />
              <span className="font-bold text-perscholas-primary">fundfish</span>
              <span className="text-gray-400 text-sm ml-2">· AI fundraising for nonprofits</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-400">
              <Link href="/about" className="hover:text-gray-600 transition-colors">About</Link>
              <Link href="/login" className="hover:text-gray-600 transition-colors">Sign In</Link>
              <span>© {new Date().getFullYear()} FundFish</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
