'use client'

import Link from 'next/link'
import Image from 'next/image'

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-perscholas-primary to-perscholas-dark text-white">
        <div className="max-w-4xl mx-auto px-6 py-16 sm:py-24">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-white/80 hover:text-white mb-8 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>

          <h1 className="text-4xl sm:text-5xl font-bold mb-6">About FundFish</h1>
          <p className="text-xl sm:text-2xl text-white/90 leading-relaxed">
            An AI-powered platform helping nonprofits discover funding opportunities and focus on what matters most: their mission.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6 py-12 sm:py-16">

        {/* The Vision */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Vision</h2>
          <div className="prose prose-lg text-gray-600">
            <p>
              FundFish is a smart, efficient system that acts as a digital scout for nonprofit fundraising teams.
              We proactively find and prioritize funding opportunities, transforming the grant discovery process
              from reactive and manual to proactive and data-driven.
            </p>
            <p>
              By automating the tedious task of searching for relevant Requests For Proposals (RFPs) and
              matching them to your organization's mission, we save valuable time—previously estimated at
              over 20 hours per week per fundraiser. This allows teams to focus on building critical
              relationships and securing more funding to expand their impact.
            </p>
          </div>
        </section>

        {/* The Problem We Solve */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">The Problem We Solve</h2>
          <div className="bg-white rounded-2xl border border-gray-200 p-8">
            <div className="grid sm:grid-cols-3 gap-6 text-center">
              <div>
                <div className="text-4xl font-bold text-perscholas-primary mb-2">20+</div>
                <p className="text-gray-600">Hours per week spent on manual opportunity research</p>
              </div>
              <div>
                <div className="text-4xl font-bold text-perscholas-primary mb-2">5-20</div>
                <p className="text-gray-600">Hours to draft each new proposal from scratch</p>
              </div>
              <div>
                <div className="text-4xl font-bold text-perscholas-primary mb-2">1000s</div>
                <p className="text-gray-600">Of untapped funding opportunities missed</p>
              </div>
            </div>
          </div>
          <p className="mt-6 text-gray-600">
            Nonprofit fundraising teams face a significant challenge with manual processes. Identifying
            and nurturing potential funding opportunities is incredibly time-consuming, limiting capacity
            to explore the numerous untapped federal, state, and local funding opportunities available.
          </p>
        </section>

        {/* Key Features */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">What FundFish Does</h2>
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Intelligent Opportunity Discovery</h3>
                  <p className="text-gray-600">
                    AI agents continuously scan federal databases (Grants.gov, SAM.gov), state programs,
                    and foundation opportunities to identify RFPs that align with your organization's goals.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Smart Match Scoring</h3>
                  <p className="text-gray-600">
                    Each opportunity is scored based on alignment with your mission, programs, target
                    populations, and funding preferences—so you can prioritize the best fits.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">AI-Powered Insights</h3>
                  <p className="text-gray-600">
                    Get detailed summaries, winning strategies from similar past RFPs, and actionable
                    recommendations for each opportunity you save.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Document Intelligence</h3>
                  <p className="text-gray-600">
                    Upload your organization's documents—annual reports, 990s, past proposals—and let
                    AI extract key information to build your profile and improve matching accuracy.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Origin Story */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">How FundFish Was Created</h2>
          <div className="bg-gradient-to-br from-perscholas-primary/5 to-perscholas-secondary/5 rounded-2xl border border-perscholas-primary/20 p-8">
            <p className="text-gray-700 mb-6">
              FundFish was born from a partnership between <strong>Per Scholas</strong> and
              <strong> Northwestern University's</strong> MBAi/MSAi capstone program in Fall 2025.
            </p>
            <p className="text-gray-700 mb-6">
              <strong>Per Scholas</strong> is a national nonprofit dedicated to enhancing economic mobility
              by providing tuition-free IT training and job placement services to individuals from diverse
              backgrounds. As they continue to grow and scale, securing diverse funding sources is critical
              to supporting their mission and expanding their impact.
            </p>
            <p className="text-gray-700 mb-6">
              The Per Scholas fundraising team identified a critical challenge: their manual processes for
              finding and pursuing grant opportunities were limiting their capacity to grow. They partnered
              with Northwestern to explore how AI could help.
            </p>
            <p className="text-gray-700">
              The result was FundFish—a production web app that Per Scholas CEO Plinio Ayala called
              <em> "a potential game changer"</em> for how the organization operates.
            </p>
          </div>
        </section>

        {/* The Team */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">The Team</h2>

          <div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="font-medium text-gray-900">Ray Freire</p>
                <p className="text-sm text-gray-500">MBAi Candidate, Kellogg School of Management</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="font-medium text-gray-900">Julia Schwieterman</p>
                <p className="text-sm text-gray-500">MBAi Candidate, Kellogg School of Management</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="font-medium text-gray-900">Meena Singh</p>
                <p className="text-sm text-gray-500">MBAi Candidate, Kellogg School of Management</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="font-medium text-gray-900">Ayaan Pupala</p>
                <p className="text-sm text-gray-500">MSAi Candidate, McCormick School of Engineering</p>
              </div>
            </div>
          </div>

        </section>

        {/* Recognition */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Recognition</h2>
          <div className="bg-white rounded-2xl border border-gray-200 p-8">
            <blockquote className="text-lg text-gray-700 italic mb-4">
              "This was one of the best projects I've seen in the past few years."
            </blockquote>
            <p className="text-gray-500">— Sanjay Sood, Industry Advisor</p>
          </div>
          <p className="mt-6 text-gray-600">
            The project was selected for feature coverage by Northwestern University and presented
            at the 2025 Capstone Showcase to industry sponsors and faculty.
          </p>
        </section>

        {/* CTA */}
        <section className="text-center">
          <div className="bg-gradient-to-br from-perscholas-primary to-perscholas-dark rounded-2xl p-8 sm:p-12 text-white">
            <h2 className="text-2xl sm:text-3xl font-bold mb-4">Ready to discover funding opportunities?</h2>
            <p className="text-white/80 mb-8 max-w-lg mx-auto">
              Join FundFish and let AI help you find grants that match your mission.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/signup"
                className="px-8 py-3 bg-white text-perscholas-primary font-semibold rounded-xl hover:bg-gray-100 transition-colors"
              >
                Get Started Free
              </Link>
              <Link
                href="/dashboard"
                className="px-8 py-3 border-2 border-white/30 text-white font-semibold rounded-xl hover:bg-white/10 transition-colors"
              >
                Browse Grants
              </Link>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-16">
        <div className="max-w-4xl mx-auto px-6 py-8 text-center text-gray-500 text-sm">
          <p>FundFish is a product of <a href="https://dytto.app" target="_blank" rel="noopener noreferrer" className="text-perscholas-primary hover:text-perscholas-dark transition-colors font-medium">dytto</a>.</p>
        </div>
      </footer>
    </div>
  )
}
