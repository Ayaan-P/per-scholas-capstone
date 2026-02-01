'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../utils/supabaseClient'
import { api } from '../../utils/api'

const STEPS = [
  { id: 'welcome', title: 'Welcome' },
  { id: 'about', title: 'Your Organization' },
  { id: 'mission', title: 'Mission & Focus' },
  { id: 'ready', title: 'Ready to Go' },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [orgName, setOrgName] = useState('')

  // Form data
  const [formData, setFormData] = useState({
    name: '',
    organization_type: '',
    mission: '',
    primary_focus_area: '',
    annual_budget: '',
    service_regions: [] as string[],
  })

  const [regionInput, setRegionInput] = useState('')

  useEffect(() => {
    // Check if user is authenticated and if they already have a profile
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        router.push('/login')
        return
      }

      // Check if user already has org config with mission (indicates completed setup)
      try {
        const response = await api.getOrganizationConfig()
        if (response.ok) {
          const config = await response.json()
          // If they have a mission set, they've likely completed onboarding
          if (config.mission && config.mission.length > 0) {
            router.push('/dashboard')
            return
          }
          // Pre-fill form with any existing data
          if (config.name) setFormData(prev => ({ ...prev, name: config.name }))
          if (config.organization_type) setFormData(prev => ({ ...prev, organization_type: config.organization_type }))
        }
      } catch (e) {
        // No config yet, that's fine
      }

      // Get org name from metadata if available
      const meta = session.user.user_metadata
      if (meta?.organization_name) {
        setOrgName(meta.organization_name)
        setFormData(prev => ({ ...prev, name: meta.organization_name }))
      }
    }
    checkAuth()
  }, [router])

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleComplete = async () => {
    setLoading(true)
    try {
      // Save organization config
      const configData = {
        ...formData,
        annual_budget: formData.annual_budget ? parseInt(formData.annual_budget) : null,
        onboarding_completed: true,
      }

      const response = await api.saveOrganizationConfig(configData)
      if (response.ok) {
        router.push('/dashboard')
      } else {
        router.push('/dashboard')
      }
    } catch (error) {
      router.push('/dashboard')
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = () => {
    router.push('/dashboard')
  }

  const addRegion = () => {
    if (regionInput.trim() && !formData.service_regions.includes(regionInput.trim())) {
      setFormData(prev => ({
        ...prev,
        service_regions: [...prev.service_regions, regionInput.trim()]
      }))
      setRegionInput('')
    }
  }

  const removeRegion = (region: string) => {
    setFormData(prev => ({
      ...prev,
      service_regions: prev.service_regions.filter(r => r !== region)
    }))
  }

  const renderStep = () => {
    switch (STEPS[currentStep].id) {
      case 'welcome':
        return (
          <div className="text-center max-w-xl mx-auto">
            <div className="w-20 h-20 bg-gradient-to-br from-perscholas-primary to-perscholas-secondary rounded-2xl flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Welcome to FundFish
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              We help nonprofits discover funding opportunities that match their mission. Our AI scans thousands of grants daily so you don't have to.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left mb-8">
              <div className="bg-gray-50 rounded-xl p-5">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">AI-Powered Discovery</h3>
                <p className="text-sm text-gray-600">Grants matched to your specific mission and programs</p>
              </div>

              <div className="bg-gray-50 rounded-xl p-5">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-3">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Federal & Local Grants</h3>
                <p className="text-sm text-gray-600">Access Grants.gov, SAM.gov, state databases, and more</p>
              </div>

              <div className="bg-gray-50 rounded-xl p-5">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Smart Insights</h3>
                <p className="text-sm text-gray-600">AI summaries and winning strategies for each grant</p>
              </div>
            </div>
          </div>
        )

      case 'about':
        return (
          <div className="max-w-lg mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">Tell us about your organization</h2>
            <p className="text-gray-600 mb-8 text-center">This helps us find grants that are right for you.</p>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Organization Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent"
                  placeholder="e.g., Community Youth Foundation"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Organization Type</label>
                <select
                  value={formData.organization_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, organization_type: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent"
                >
                  <option value="">Select type...</option>
                  <option value="nonprofit">501(c)(3) Nonprofit</option>
                  <option value="educational-institution">Educational Institution</option>
                  <option value="government">Government Agency</option>
                  <option value="social-enterprise">Social Enterprise</option>
                  <option value="faith-based">Faith-Based Organization</option>
                  <option value="community-based">Community-Based Organization</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Annual Budget (approximate)</label>
                <select
                  value={formData.annual_budget}
                  onChange={(e) => setFormData(prev => ({ ...prev, annual_budget: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent"
                >
                  <option value="">Select range...</option>
                  <option value="100000">Under $100,000</option>
                  <option value="500000">$100,000 - $500,000</option>
                  <option value="1000000">$500,000 - $1 million</option>
                  <option value="5000000">$1 - $5 million</option>
                  <option value="10000000">$5 - $10 million</option>
                  <option value="50000000">$10 - $50 million</option>
                  <option value="100000000">$50 million+</option>
                </select>
              </div>
            </div>
          </div>
        )

      case 'mission':
        return (
          <div className="max-w-lg mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">What's your mission?</h2>
            <p className="text-gray-600 mb-8 text-center">This is how we match you to the right opportunities.</p>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Primary Focus Area</label>
                <select
                  value={formData.primary_focus_area}
                  onChange={(e) => setFormData(prev => ({ ...prev, primary_focus_area: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent"
                >
                  <option value="">Select focus area...</option>
                  <option value="education">Education</option>
                  <option value="workforce-development">Workforce Development</option>
                  <option value="health">Health & Wellness</option>
                  <option value="youth-development">Youth Development</option>
                  <option value="community-development">Community Development</option>
                  <option value="social-services">Social Services</option>
                  <option value="environment">Environment</option>
                  <option value="arts-culture">Arts & Culture</option>
                  <option value="housing">Housing</option>
                  <option value="economic-development">Economic Development</option>
                  <option value="technology">Technology</option>
                  <option value="civil-rights">Civil Rights & Advocacy</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mission Statement (optional)</label>
                <textarea
                  value={formData.mission}
                  onChange={(e) => setFormData(prev => ({ ...prev, mission: e.target.value }))}
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent resize-none"
                  placeholder="Describe what your organization does and who you serve..."
                />
                <p className="text-xs text-gray-500 mt-1">The more detail you provide, the better our matching will be.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Regions You Serve</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={regionInput}
                    onChange={(e) => setRegionInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRegion())}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-perscholas-primary focus:border-transparent"
                    placeholder="e.g., New York City, California"
                  />
                  <button
                    type="button"
                    onClick={addRegion}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                  >
                    Add
                  </button>
                </div>
                {formData.service_regions.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.service_regions.map(region => (
                      <span key={region} className="inline-flex items-center gap-1 px-3 py-1 bg-perscholas-primary/10 text-perscholas-primary rounded-full text-sm">
                        {region}
                        <button onClick={() => removeRegion(region)} className="hover:text-perscholas-dark">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )

      case 'ready':
        return (
          <div className="text-center max-w-xl mx-auto">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">You're all set!</h2>
            <p className="text-lg text-gray-600 mb-8">
              We'll start matching grants to {formData.name || 'your organization'} right away. You can always update your profile in Settings.
            </p>

            <div className="bg-gray-50 rounded-xl p-6 text-left mb-8">
              <h3 className="font-semibold text-gray-900 mb-4">What's next:</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-perscholas-primary rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">1</span>
                  </div>
                  <span className="text-gray-700">Browse grants on your dashboard - we've already found some for you</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-perscholas-primary rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">2</span>
                  </div>
                  <span className="text-gray-700">Save promising grants to unlock AI insights and strategies</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-perscholas-primary rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">3</span>
                  </div>
                  <span className="text-gray-700">Upload documents in Settings to improve your match accuracy</span>
                </li>
              </ul>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex flex-col">
      {/* Progress bar */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Step {currentStep + 1} of {STEPS.length}</span>
            <button
              onClick={handleSkip}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Skip for now
            </button>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-perscholas-primary to-perscholas-secondary transition-all duration-300"
              style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl animate-fadeIn" key={currentStep}>
          {renderStep()}
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white border-t border-gray-200">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={`px-6 py-2.5 rounded-xl font-medium transition-all ${
              currentStep === 0
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Back
          </button>

          {currentStep === STEPS.length - 1 ? (
            <button
              onClick={handleComplete}
              disabled={loading}
              className="px-8 py-2.5 bg-perscholas-primary text-white rounded-xl font-medium hover:bg-perscholas-dark transition-colors disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Go to Dashboard'}
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="px-8 py-2.5 bg-perscholas-primary text-white rounded-xl font-medium hover:bg-perscholas-dark transition-colors"
            >
              Continue
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
