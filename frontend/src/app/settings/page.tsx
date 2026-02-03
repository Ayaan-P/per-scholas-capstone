'use client'

export const dynamic = 'force-dynamic'

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { ProtectedRoute } from '../../components/ProtectedRoute'
import { CreditBalance } from '../../components/CreditBalance'
import { UpgradeModal } from '../../components/UpgradeModal'
import { DocumentUploader } from '../../components/DocumentUploader'
import { ExtractedInfoReview } from '../../components/ExtractedInfoReview'

interface KeyProgram {
  name: string
  description?: string
}

interface KeyPartnership {
  name: string
}

interface FundingPriority {
  name: string
  priority?: number
}

interface ImpactMetric {
  metric_name: string
  current_value?: string
  target_value?: string
  unit?: string
}

interface PreviousGrant {
  funder: string
  amount: number
  year: number
  outcome?: string
}

interface SuccessStory {
  title: string
  description?: string
}

interface OrganizationConfig {
  id?: string
  name: string
  mission: string
  organization_type: string
  ein?: string
  tax_exempt_status: string
  years_established?: number
  annual_budget?: number
  staff_size?: number
  board_size?: number
  website_url?: string
  contact_email?: string
  contact_phone?: string

  primary_focus_area: string
  secondary_focus_areas: string[]
  key_programs: KeyProgram[]
  service_regions: string[]
  expansion_plans?: string
  target_populations: string[]
  languages_served: string[]

  key_partnerships: KeyPartnership[]
  accreditations: string[]

  preferred_grant_size_min?: number
  preferred_grant_size_max?: number
  preferred_grant_types: string[]
  funding_priorities: FundingPriority[]
  custom_search_keywords: string[]
  excluded_keywords: string[]

  key_impact_metrics: ImpactMetric[]
  previous_grants: PreviousGrant[]
  donor_restrictions?: string
  grant_writing_capacity: string
  matching_fund_capacity: number
  success_stories: SuccessStory[]
}

const ORGANIZATION_TYPES = ['nonprofit', 'social-enterprise', 'government', 'educational-institution', 'faith-based', 'community-based', 'other']
const TAX_EXEMPT_STATUSES = ['pending', '501c3', '501c6', '501c7', 'other', 'none']
const GRANT_WRITING_CAPACITIES = ['limited', 'moderate', 'advanced']
const FOCUS_AREA_OPTIONS = ['education', 'health', 'environment', 'arts', 'social-services', 'workforce-development', 'technology', 'housing', 'economic-development', 'international', 'other']
const GRANT_TYPES = ['project-based', 'general-support', 'capacity-building', 'research', 'capital', 'equipment']
const POPULATION_OPTIONS = ['K-12 students', 'higher education', 'youth', 'seniors', 'low-income families', 'underrepresented communities', 'women', 'veterans', 'immigrants', 'rural', 'urban', 'LGBTQ', 'persons-with-disabilities']
const LANGUAGE_OPTIONS = ['English', 'Spanish', 'French', 'Mandarin', 'Vietnamese', 'Arabic', 'Korean', 'Tagalog', 'Russian', 'Other']

interface ListItem {
  name?: string
  description?: string
  [key: string]: string | number | boolean | undefined
}

interface TextInputProps {
  label: string
  value: string | number | undefined
  onChange: (value: string) => void
  placeholder?: string
  type?: 'text' | 'number' | 'email' | 'url' | 'tel'
  helpText?: string
}

interface TextAreaProps {
  label: string
  value: string | undefined
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  helpText?: string
}

interface SelectInputProps {
  label: string
  value: string | undefined
  onChange: (value: string) => void
  options: string[]
  helpText?: string
}

const TextInput = ({ label, value, onChange, placeholder, type = 'text', helpText }: TextInputProps) => (
  <div>
    <label className="block text-sm font-semibold text-gray-900 mb-1.5">{label}</label>
    {helpText && <p className="text-xs text-gray-500 mb-2">{helpText}</p>}
    <input
      type={type}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="input-premium w-full"
    />
  </div>
)

const TextArea = ({ label, value, onChange, placeholder, rows = 3, helpText }: TextAreaProps) => (
  <div>
    <label className="block text-sm font-semibold text-gray-900 mb-1.5">{label}</label>
    {helpText && <p className="text-xs text-gray-500 mb-2">{helpText}</p>}
    <textarea
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="input-premium w-full resize-none"
    />
  </div>
)

const SelectInput = ({ label, value, onChange, options, helpText }: SelectInputProps) => (
  <div>
    <label className="block text-sm font-semibold text-gray-900 mb-1.5">{label}</label>
    {helpText && <p className="text-xs text-gray-500 mb-2">{helpText}</p>}
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      className="input-premium w-full"
    >
      <option value="">Select {label}</option>
      {options.map((opt: string) => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  </div>
)

export default function SettingsPage() {
  const [config, setConfig] = useState<OrganizationConfig>({
    name: 'Your Organization',
    mission: '',
    organization_type: 'nonprofit',
    tax_exempt_status: 'pending',
    primary_focus_area: '',
    secondary_focus_areas: [],
    key_programs: [],
    service_regions: [],
    target_populations: [],
    languages_served: ['English'],
    key_partnerships: [],
    accreditations: [],
    preferred_grant_types: [],
    funding_priorities: [],
    custom_search_keywords: [],
    excluded_keywords: [],
    key_impact_metrics: [],
    previous_grants: [],
    grant_writing_capacity: 'moderate',
    matching_fund_capacity: 0,
    success_stories: [],
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [activeTab, setActiveTab] = useState('basic')
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false)

  // Document import state
  const [existingDocuments, setExistingDocuments] = useState<any[]>([])
  const [uploadedDocIds, setUploadedDocIds] = useState<string[]>([])
  const [extractionResult, setExtractionResult] = useState<any>(null)
  const [extracting, setExtracting] = useState(false)
  const [applying, setApplying] = useState(false)
  const [docError, setDocError] = useState('')

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await api.getOrganizationConfig()
        if (response.ok) {
          const data = await response.json()
          setConfig({ ...config, ...data })
        } else if (response.status === 404) {
          // 404 is expected for new organizations - auto-create default config
          try {
            const saveResponse = await api.saveOrganizationConfig({
              name: 'New Organization',
              mission: '',
              focus_areas: [],
              impact_metrics: {},
              programs: [],
              target_demographics: []
            })
            if (saveResponse.ok) {
              const data = await saveResponse.json()
              setConfig({ ...config, ...data })
            }
          } catch (error) {
          }
        } else {
        }
      } catch (error) {
      } finally {
        setLoading(false)
      }
    }

    const fetchDocuments = async () => {
      try {
        const response = await api.getOrganizationDocuments()
        if (response.ok) {
          const data = await response.json()
          setExistingDocuments(data.documents || [])
        } else if (response.status === 404) {
          // No documents yet
        }
      } catch (error) {
      }
    }

    fetchConfig()
    fetchDocuments()
  }, [])

  // Auto-save config when it changes (debounced)
  useEffect(() => {
    if (loading) return

    const timer = setTimeout(async () => {
      try {
        await api.saveOrganizationConfig(config)
      } catch (error) {
      }
    }, 1000) // Debounce for 1 second

    return () => clearTimeout(timer)
  }, [config, loading])

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await api.saveOrganizationConfig(config)
      if (response.ok) {
        setMessage('Organization profile saved successfully!')
        setTimeout(() => setMessage(''), 3000)
      } else {
        setMessage('Failed to save configuration')
      }
    } catch (error) {
      setMessage('Error saving configuration')
    } finally {
      setSaving(false)
    }
  }

  const addArrayItem = (field: string, item: string) => {
    if (item.trim()) {
      setConfig(prev => ({
        ...prev,
        [field]: [...(prev[field as keyof OrganizationConfig] as any[]), item]
      }))
    }
  }

  const removeArrayItem = (field: string, index: number) => {
    setConfig(prev => ({
      ...prev,
      [field]: (prev[field as keyof OrganizationConfig] as any[]).filter((_, i) => i !== index)
    }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-2 border-perscholas-primary/20 border-t-perscholas-primary rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600 font-medium">Loading organization profile...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ProtectedRoute>
      <UpgradeModal
        isOpen={upgradeModalOpen}
        onClose={() => setUpgradeModalOpen(false)}
        reason="upgrade"
      />
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Page Header */}
          <div className="mb-8 animate-fade-in">
            <div className="card-elevated p-6 sm:p-8">
              <div className="flex items-center gap-4 mb-3">
                <div className="bg-perscholas-primary p-3 rounded-xl shadow-md">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl sm:text-3xl font-bold text-perscholas-primary">Settings</h1>
                  <p className="text-gray-600 text-sm sm:text-base">Manage your organization profile and preferences</p>
                </div>
              </div>
            </div>
          </div>

          {/* Credits Section */}
          <div className="card-premium p-6 mb-6 animate-fade-in" style={{ animationDelay: '100ms' }}>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex-1">
                <h2 className="text-lg font-bold text-gray-900 mb-1">Search Credits</h2>
                <p className="text-gray-600 text-sm">Manage your search credits and upgrade your plan</p>
              </div>
              <div className="flex items-center gap-4">
                <CreditBalance />
                <button
                  onClick={() => setUpgradeModalOpen(true)}
                  className="btn-primary px-6 py-2.5"
                >
                  Buy Credits
                </button>
              </div>
            </div>
          </div>

          <div className="card-elevated p-6 sm:p-8 animate-fade-in" style={{ animationDelay: '150ms' }}>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Organization Profile</h2>
            <p className="text-gray-600 mb-8 text-sm">Help us understand your organization so we can match you with the best funding opportunities</p>

            {message && (
              <div className="mb-6 p-4 rounded-xl bg-green-50 border border-green-200 text-green-800 flex items-center gap-3 animate-fade-in">
                <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium">{message}</span>
              </div>
            )}

            {/* Tabs */}
            <div className="flex flex-wrap gap-1 mb-8 p-1 bg-gray-100 rounded-xl">
              {['import', 'basic', 'mission', 'programs', 'funding', 'impact'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2.5 font-medium transition-all duration-200 capitalize rounded-lg text-sm ${
                    activeTab === tab
                      ? 'bg-white text-perscholas-primary shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

          {/* IMPORT TAB */}
          {activeTab === 'import' && (
            <div className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                <h3 className="font-semibold text-blue-900 mb-2">Quick Profile Setup</h3>
                <p className="text-sm text-blue-800">
                  Upload your organization documents (annual reports, 990 forms, grant proposals, mission statements)
                  and we'll automatically extract your profile information using AI.
                </p>
              </div>

              {docError && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 flex items-center gap-3">
                  <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm">{docError}</span>
                  <button onClick={() => setDocError('')} className="ml-auto text-red-600 hover:text-red-800">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              )}

              {!extractionResult ? (
                <>
                  <DocumentUploader
                    onUploadComplete={(docs) => {
                      const newIds = docs.filter(d => d.id).map(d => d.id as string)
                      setUploadedDocIds(prev => [...prev, ...newIds])
                      // Refresh document list
                      api.getOrganizationDocuments().then(res => {
                        if (res.ok) res.json().then(data => setExistingDocuments(data.documents || []))
                      })
                    }}
                    onError={(err) => setDocError(err)}
                    existingDocuments={existingDocuments}
                    onDeleteDocument={async (docId) => {
                      try {
                        const res = await api.deleteOrganizationDocument(docId)
                        if (res.ok) {
                          setExistingDocuments(prev => prev.filter(d => d.id !== docId))
                          setUploadedDocIds(prev => prev.filter(id => id !== docId))
                        }
                      } catch (err) {
                        setDocError('Failed to delete document')
                      }
                    }}
                  />

                  {(uploadedDocIds.length > 0 || existingDocuments.length > 0) && (
                    <div className="flex justify-end pt-4">
                      <button
                        onClick={async () => {
                          setExtracting(true)
                          setDocError('')
                          try {
                            const docIds = uploadedDocIds.length > 0
                              ? uploadedDocIds
                              : existingDocuments.map(d => d.id)
                            const res = await api.extractOrganizationInfo(docIds)
                            if (res.ok) {
                              const data = await res.json()
                              setExtractionResult(data)
                            } else {
                              const err = await res.json()
                              setDocError(err.detail || 'Extraction failed')
                            }
                          } catch (err) {
                            setDocError('Failed to extract organization info')
                          } finally {
                            setExtracting(false)
                          }
                        }}
                        disabled={extracting}
                        className="btn-primary px-6 py-3 flex items-center gap-2"
                      >
                        {extracting && (
                          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        )}
                        {extracting ? 'Extracting...' : 'Extract Organization Info'}
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <ExtractedInfoReview
                  extracted={extractionResult.extracted}
                  confidence={extractionResult.confidence}
                  mergePreview={extractionResult.merge_preview}
                  sourceDocuments={extractionResult.source_documents}
                  loading={applying}
                  onCancel={() => {
                    setExtractionResult(null)
                    setUploadedDocIds([])
                  }}
                  onApply={async (resolvedConflicts) => {
                    setApplying(true)
                    try {
                      const res = await api.applyExtractedData(
                        extractionResult.extracted,
                        resolvedConflicts,
                        uploadedDocIds.length > 0 ? uploadedDocIds : existingDocuments.map(d => d.id)
                      )
                      if (res.ok) {
                        const data = await res.json()
                        if (data.profile) {
                          setConfig(prev => ({ ...prev, ...data.profile }))
                        }
                        setMessage('Organization profile updated from documents!')
                        setTimeout(() => setMessage(''), 3000)
                        setExtractionResult(null)
                        setUploadedDocIds([])
                        setActiveTab('basic')
                      } else {
                        const err = await res.json()
                        setDocError(err.detail || 'Failed to apply changes')
                      }
                    } catch (err) {
                      setDocError('Failed to apply extracted data')
                    } finally {
                      setApplying(false)
                    }
                  }}
                />
              )}
            </div>
          )}

          {/* BASIC INFO TAB */}
          {activeTab === 'basic' && (
            <div className="space-y-6">
              <TextInput
                label="Organization Name *"
                value={config.name}
                onChange={(v: string) => setConfig({...config, name: v})}
                placeholder="Your organization name"
              />

              <SelectInput
                label="Organization Type *"
                value={config.organization_type}
                onChange={(v: string) => setConfig({...config, organization_type: v})}
                options={ORGANIZATION_TYPES}
                helpText="What type of organization are you?"
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextInput
                  label="EIN (Employer ID Number)"
                  value={config.ein}
                  onChange={(v: string) => setConfig({...config, ein: v})}
                  placeholder="XX-XXXXXXX"
                  helpText="Your federal tax ID"
                />

                <SelectInput
                  label="Tax Exempt Status"
                  value={config.tax_exempt_status}
                  onChange={(v: string) => setConfig({...config, tax_exempt_status: v})}
                  options={TAX_EXEMPT_STATUSES}
                  helpText="Your IRS designation"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextInput
                  label="Years Established"
                  value={config.years_established}
                  onChange={(v: string) => setConfig({...config, years_established: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 2010"
                  type="number"
                  helpText="Year your organization was founded"
                />

                <TextInput
                  label="Annual Budget (USD)"
                  value={config.annual_budget}
                  onChange={(v: string) => setConfig({...config, annual_budget: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 500000"
                  type="number"
                  helpText="Your organization's annual operating budget"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextInput
                  label="Staff Size"
                  value={config.staff_size}
                  onChange={(v: string) => setConfig({...config, staff_size: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 15"
                  type="number"
                  helpText="Full-time and part-time staff"
                />

                <TextInput
                  label="Board Size"
                  value={config.board_size}
                  onChange={(v: string) => setConfig({...config, board_size: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 8"
                  type="number"
                  helpText="Number of board members"
                />
              </div>

              <TextInput
                label="Website"
                value={config.website_url}
                onChange={(v: string) => setConfig({...config, website_url: v})}
                placeholder="https://yourorg.org"
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextInput
                  label="Contact Email"
                  value={config.contact_email}
                  onChange={(v: string) => setConfig({...config, contact_email: v})}
                  placeholder="grants@yourorg.org"
                  type="email"
                />

                <TextInput
                  label="Contact Phone"
                  value={config.contact_phone}
                  onChange={(v: string) => setConfig({...config, contact_phone: v})}
                  placeholder="(555) 123-4567"
                />
              </div>
            </div>
          )}

          {/* MISSION TAB */}
          {activeTab === 'mission' && (
            <div className="space-y-6">
              <TextArea
                label="Organization Mission *"
                value={config.mission}
                onChange={(v: string) => setConfig({...config, mission: v})}
                placeholder="Describe your organization's core mission and purpose"
                rows={4}
                helpText="What problem does your organization solve? What change do you seek?"
              />

              <SelectInput
                label="Primary Focus Area *"
                value={config.primary_focus_area}
                onChange={(v: string) => setConfig({...config, primary_focus_area: v})}
                options={FOCUS_AREA_OPTIONS}
                helpText="Your organization's main field of work"
              />

              <TextArea
                label="Service Regions *"
                value={config.service_regions.join(', ')}
                onChange={(v: string) => setConfig({...config, service_regions: v.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., Los Angeles, CA and San Diego, CA"
                rows={2}
                helpText="Cities, counties, or regions you serve (comma-separated)"
              />

              <TextArea
                label="Expansion Plans"
                value={config.expansion_plans}
                onChange={(v: string) => setConfig({...config, expansion_plans: v})}
                placeholder="Describe any geographic or program expansion plans"
                rows={3}
                helpText="Where or how do you plan to grow?"
              />

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Languages Served</label>
                <p className="text-xs text-gray-500 mb-3">Select all languages your organization uses to serve beneficiaries</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <label key={lang} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={config.languages_served.includes(lang)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setConfig({...config, languages_served: [...config.languages_served, lang]})
                          } else {
                            setConfig({...config, languages_served: config.languages_served.filter(l => l !== lang)})
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm text-gray-700">{lang}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* PROGRAMS TAB */}
          {activeTab === 'programs' && (
            <div className="space-y-6">
              <TextArea
                label="Target Populations"
                value={config.target_populations.join(', ')}
                onChange={(v: string) => setConfig({...config, target_populations: v.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., K-12 students, low-income families, youth"
                rows={2}
                helpText="Who does your organization serve? (comma-separated)"
              />

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-3">Key Programs</label>
                <p className="text-xs text-gray-500 mb-4">Describe the main programs your organization offers</p>
                <div className="space-y-3 mb-4">
                  {config.key_programs.map((prog: KeyProgram, index: number) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex justify-between items-start mb-3">
                        <h4 className="font-medium text-gray-900">{prog.name || 'Unnamed Program'}</h4>
                        <button onClick={() => removeArrayItem('key_programs', index)} className="text-red-600 hover:text-red-800 text-sm">Remove</button>
                      </div>
                      <p className="text-sm text-gray-600">{prog.description || 'No description'}</p>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const name = prompt('Program name:')
                    if (name) {
                      const desc = prompt('Program description:')
                      setConfig({...config, key_programs: [...config.key_programs, {name, description: desc || ''}]})
                    }
                  }}
                  className="btn-secondary px-4 py-2 text-sm"
                >
                  Add Program
                </button>
              </div>

              <TextArea
                label="Key Partnerships"
                value={config.key_partnerships.map(p => p.name || p).join(', ')}
                onChange={(v: string) => setConfig({...config, key_partnerships: v.split(',').map(s => ({name: s.trim()})).filter(s => s.name)})}
                placeholder="e.g., Local School District, Community Center, National Alliance"
                rows={2}
                helpText="Organizations you partner with (comma-separated)"
              />

              <TextArea
                label="Accreditations & Certifications"
                value={config.accreditations.join(', ')}
                onChange={(v: string) => setConfig({...config, accreditations: v.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., COE, B-Corp, ISO certification"
                rows={2}
                helpText="Professional certifications and accreditations (comma-separated)"
              />
            </div>
          )}

          {/* FUNDING TAB */}
          {activeTab === 'funding' && (
            <div className="space-y-6">
              <SelectInput
                label="Grant Writing Capacity"
                value={config.grant_writing_capacity}
                onChange={(v: string) => setConfig({...config, grant_writing_capacity: v})}
                options={GRANT_WRITING_CAPACITIES}
                helpText="How many grant proposals can your organization manage?"
              />

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm space-y-2">
                <div><strong>Limited:</strong> Can handle 1-2 grant proposals per quarter</div>
                <div><strong>Moderate:</strong> Can handle 3-5 grant proposals per quarter</div>
                <div><strong>Advanced:</strong> Can handle 6+ complex grant proposals per quarter</div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextInput
                  label="Min Ideal Grant Size (USD)"
                  value={config.preferred_grant_size_min}
                  onChange={(v: string) => setConfig({...config, preferred_grant_size_min: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 25000"
                  type="number"
                  helpText="Smallest grant worth pursuing"
                />

                <TextInput
                  label="Max Ideal Grant Size (USD)"
                  value={config.preferred_grant_size_max}
                  onChange={(v: string) => setConfig({...config, preferred_grant_size_max: v ? parseInt(v) : undefined})}
                  placeholder="e.g., 500000"
                  type="number"
                  helpText="Largest grant you can manage"
                />
              </div>

              <TextInput
                label="Matching Fund Capacity (%)"
                value={config.matching_fund_capacity}
                onChange={(v: string) => setConfig({...config, matching_fund_capacity: parseFloat(v) || 0})}
                placeholder="e.g., 25"
                type="number"
                helpText="What % of grant awards can you match with local funding?"
              />

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Preferred Grant Types</label>
                <p className="text-xs text-gray-500 mb-3">Select the types of funding your organization prefers</p>
                <div className="grid grid-cols-2 gap-3">
                  {GRANT_TYPES.map((type) => (
                    <label key={type} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={config.preferred_grant_types.includes(type)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setConfig({...config, preferred_grant_types: [...config.preferred_grant_types, type]})
                          } else {
                            setConfig({...config, preferred_grant_types: config.preferred_grant_types.filter(t => t !== type)})
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm text-gray-700">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <TextArea
                label="Custom Search Keywords"
                value={config.custom_search_keywords.join(', ')}
                onChange={(v: string) => setConfig({...config, custom_search_keywords: v.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., trauma-informed, LGBTQ-affirming, culturally-responsive"
                rows={2}
                helpText="Keywords that describe your approach or values (comma-separated)"
              />

              <TextArea
                label="Excluded Keywords"
                value={config.excluded_keywords.join(', ')}
                onChange={(v: string) => setConfig({...config, excluded_keywords: v.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., military, weapons, fossil-fuel"
                rows={2}
                helpText="Keywords to exclude from grant matching (comma-separated)"
              />

              <TextArea
                label="Donor Restrictions"
                value={config.donor_restrictions}
                onChange={(v: string) => setConfig({...config, donor_restrictions: v})}
                placeholder="e.g., No government funds, No corporate funders"
                rows={3}
                helpText="Any restrictions on funding sources you'll accept"
              />
            </div>
          )}

          {/* IMPACT TAB */}
          {activeTab === 'impact' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-3">Key Impact Metrics</label>
                <p className="text-xs text-gray-500 mb-4">Track the metrics that matter most to your organization</p>
                <div className="space-y-2 mb-4">
                  {config.key_impact_metrics.map((metric: ImpactMetric, index: number) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{metric.metric_name}</div>
                        <div className="text-sm text-gray-600">{metric.current_value} / {metric.target_value} {metric.unit}</div>
                      </div>
                      <button onClick={() => removeArrayItem('key_impact_metrics', index)} className="text-red-600 hover:text-red-800 text-sm ml-4">Remove</button>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const name = prompt('Metric name (e.g., "Students Graduated"):')
                    if (name) {
                      const current = prompt('Current value:')
                      const target = prompt('Target value:')
                      const unit = prompt('Unit (e.g., students, hours, dollars):', 'units')
                      setConfig({...config, key_impact_metrics: [...config.key_impact_metrics, {metric_name: name, current_value: current, target_value: target, unit}]})
                    }
                  }}
                  className="btn-secondary px-4 py-2 text-sm"
                >
                  Add Metric
                </button>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-3">Success Stories</label>
                <p className="text-xs text-gray-500 mb-4">Share impact stories that demonstrate your organization's work</p>
                <div className="space-y-3 mb-4">
                  {config.success_stories.map((story: SuccessStory, index: number) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-gray-900">{story.title || 'Untitled Story'}</h4>
                        <button onClick={() => removeArrayItem('success_stories', index)} className="text-red-600 hover:text-red-800 text-sm">Remove</button>
                      </div>
                      <p className="text-sm text-gray-600">{story.description || 'No description'}</p>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const title = prompt('Story title:')
                    if (title) {
                      const desc = prompt('Story description:')
                      setConfig({...config, success_stories: [...config.success_stories, {title, description: desc || ''}]})
                    }
                  }}
                  className="btn-secondary px-4 py-2 text-sm"
                >
                  Add Story
                </button>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-3">Previous Grants</label>
                <p className="text-xs text-gray-500 mb-4">Document successful grants your organization has received</p>
                <div className="space-y-2 mb-4">
                  {config.previous_grants.map((grant: PreviousGrant, index: number) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">${grant.amount?.toLocaleString()} from {grant.funder}</div>
                        <div className="text-sm text-gray-600">{grant.year} - {grant.outcome || 'success'}</div>
                      </div>
                      <button onClick={() => removeArrayItem('previous_grants', index)} className="text-red-600 hover:text-red-800 text-sm ml-4">Remove</button>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const funder = prompt('Funder name:')
                    if (funder) {
                      const amount = prompt('Grant amount:')
                      const year = prompt('Year:')
                      if (amount && year) {
                        setConfig({...config, previous_grants: [...config.previous_grants, {funder, amount: parseInt(amount), year: parseInt(year), outcome: 'success'}]})
                      }
                    }
                  }}
                  className="btn-secondary px-4 py-2 text-sm"
                >
                  Add Grant
                </button>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="flex gap-4 mt-12 pt-8 border-t border-gray-200">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </span>
              ) : (
                'Save Organization Profile'
              )}
            </button>
          </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}
