'use client'

import { useState, useMemo } from 'react'

interface FieldInfo {
  value: any
  confidence?: number
}

interface ConflictInfo {
  existing: any
  extracted: any
  confidence: number
}

interface MergePreview {
  new_fields: Record<string, FieldInfo>
  conflicts: Record<string, ConflictInfo>
  unchanged: Record<string, FieldInfo>
}

interface ExtractedInfoReviewProps {
  extracted: Record<string, any>
  confidence: Record<string, number>
  mergePreview: MergePreview
  sourceDocuments: string[]
  onApply: (resolvedConflicts: Record<string, any>) => void
  onCancel: () => void
  loading?: boolean
}

// Field display names
const FIELD_LABELS: Record<string, string> = {
  name: 'Organization Name',
  ein: 'EIN',
  organization_type: 'Organization Type',
  tax_exempt_status: 'Tax Exempt Status',
  years_established: 'Year Established',
  annual_budget: 'Annual Budget',
  staff_size: 'Staff Size',
  board_size: 'Board Size',
  website_url: 'Website',
  contact_email: 'Contact Email',
  contact_phone: 'Contact Phone',
  mission: 'Mission Statement',
  primary_focus_area: 'Primary Focus Area',
  secondary_focus_areas: 'Secondary Focus Areas',
  service_regions: 'Service Regions',
  languages_served: 'Languages Served',
  key_programs: 'Key Programs',
  target_populations: 'Target Populations',
  key_partnerships: 'Key Partnerships',
  accreditations: 'Accreditations',
  preferred_grant_size_min: 'Min Grant Size',
  preferred_grant_size_max: 'Max Grant Size',
  grant_writing_capacity: 'Grant Writing Capacity',
  key_impact_metrics: 'Impact Metrics',
  success_stories: 'Success Stories',
  previous_grants: 'Previous Grants',
}

// Group fields by category
const FIELD_GROUPS: Record<string, string[]> = {
  'Basic Info': ['name', 'ein', 'organization_type', 'tax_exempt_status', 'years_established', 'annual_budget', 'staff_size', 'board_size', 'website_url', 'contact_email', 'contact_phone'],
  'Mission & Focus': ['mission', 'primary_focus_area', 'secondary_focus_areas', 'service_regions', 'languages_served'],
  'Programs': ['key_programs', 'target_populations', 'key_partnerships', 'accreditations'],
  'Funding': ['preferred_grant_size_min', 'preferred_grant_size_max', 'grant_writing_capacity'],
  'Impact': ['key_impact_metrics', 'success_stories', 'previous_grants'],
}

export function ExtractedInfoReview({
  extracted,
  confidence,
  mergePreview,
  sourceDocuments,
  onApply,
  onCancel,
  loading = false
}: ExtractedInfoReviewProps) {
  // Track conflict resolutions (true = use extracted, false = keep existing)
  const [conflictResolutions, setConflictResolutions] = useState<Record<string, boolean>>({})

  // Calculate stats
  const stats = useMemo(() => ({
    newFields: Object.keys(mergePreview.new_fields).length,
    conflicts: Object.keys(mergePreview.conflicts).length,
    unchanged: Object.keys(mergePreview.unchanged).length,
  }), [mergePreview])

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'Not provided'
    if (Array.isArray(value)) {
      if (value.length === 0) return 'None'
      if (typeof value[0] === 'object') {
        return value.map(v => v.name || v.title || JSON.stringify(v)).join(', ')
      }
      return value.join(', ')
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    if (typeof value === 'number') {
      // Format currency if it looks like money
      if (value > 1000) {
        return '$' + value.toLocaleString()
      }
      return value.toString()
    }
    return String(value)
  }

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-green-600 bg-green-50'
    if (conf >= 0.5) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const handleApply = () => {
    // Build resolved conflicts object
    const resolved: Record<string, any> = {}
    for (const [field, useExtracted] of Object.entries(conflictResolutions)) {
      if (useExtracted) {
        resolved[field] = mergePreview.conflicts[field].extracted
      }
      // If false (keep existing), don't include in resolved - it won't be updated
    }
    onApply(resolved)
  }

  const renderFieldValue = (field: string, value: any, conf?: number) => {
    const formattedValue = formatValue(value)
    const isLong = formattedValue.length > 100

    return (
      <div className="flex-1">
        <div className={`text-sm ${isLong ? 'whitespace-pre-wrap' : ''}`}>
          {isLong ? (
            <details>
              <summary className="cursor-pointer text-gray-700">
                {formattedValue.substring(0, 100)}...
              </summary>
              <p className="mt-2 text-gray-600 bg-gray-50 p-2 rounded">{formattedValue}</p>
            </details>
          ) : (
            <span className="text-gray-700">{formattedValue}</span>
          )}
        </div>
        {conf !== undefined && (
          <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${getConfidenceColor(conf)}`}>
            {Math.round(conf * 100)}% confident
          </span>
        )}
      </div>
    )
  }

  const renderFieldsByGroup = () => {
    return Object.entries(FIELD_GROUPS).map(([groupName, fields]) => {
      const groupNewFields = fields.filter(f => f in mergePreview.new_fields)
      const groupConflicts = fields.filter(f => f in mergePreview.conflicts)

      if (groupNewFields.length === 0 && groupConflicts.length === 0) return null

      return (
        <div key={groupName} className="space-y-3">
          <h4 className="font-medium text-gray-800 border-b border-gray-200 pb-2">{groupName}</h4>

          {/* New fields */}
          {groupNewFields.map(field => (
            <div key={field} className="flex items-start gap-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <span className="text-green-600 text-lg">+</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-700">{FIELD_LABELS[field] || field}</p>
                {renderFieldValue(field, mergePreview.new_fields[field].value, mergePreview.new_fields[field].confidence)}
              </div>
              <span className="text-xs text-green-600 font-medium">NEW</span>
            </div>
          ))}

          {/* Conflicts */}
          {groupConflicts.map(field => {
            const conflict = mergePreview.conflicts[field]
            const useExtracted = conflictResolutions[field] ?? true // Default to using extracted

            return (
              <div key={field} className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700">{FIELD_LABELS[field] || field}</p>
                  <span className="text-xs text-yellow-600 font-medium">CONFLICT</span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Existing value */}
                  <button
                    onClick={() => setConflictResolutions(prev => ({ ...prev, [field]: false }))}
                    className={`p-3 rounded-lg border-2 text-left transition-all ${
                      !useExtracted
                        ? 'border-perscholas-primary bg-blue-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <p className="text-xs text-gray-500 mb-1">Current value:</p>
                    <p className="text-sm text-gray-700">{formatValue(conflict.existing)}</p>
                    {!useExtracted && (
                      <span className="inline-block mt-2 text-xs text-perscholas-primary font-medium">Selected</span>
                    )}
                  </button>

                  {/* Extracted value */}
                  <button
                    onClick={() => setConflictResolutions(prev => ({ ...prev, [field]: true }))}
                    className={`p-3 rounded-lg border-2 text-left transition-all ${
                      useExtracted
                        ? 'border-perscholas-primary bg-blue-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <p className="text-xs text-gray-500 mb-1">From documents:</p>
                    <p className="text-sm text-gray-700">{formatValue(conflict.extracted)}</p>
                    <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded ${getConfidenceColor(conflict.confidence)}`}>
                      {Math.round(conflict.confidence * 100)}% confident
                    </span>
                    {useExtracted && (
                      <span className="inline-block mt-2 ml-2 text-xs text-perscholas-primary font-medium">Selected</span>
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )
    })
  }

  const hasChanges = stats.newFields > 0 || stats.conflicts > 0

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm font-medium">
            {stats.newFields}
          </span>
          <span className="text-sm text-gray-600">New fields</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-yellow-100 text-yellow-600 flex items-center justify-center text-sm font-medium">
            {stats.conflicts}
          </span>
          <span className="text-sm text-gray-600">Conflicts</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-sm font-medium">
            {stats.unchanged}
          </span>
          <span className="text-sm text-gray-600">Unchanged</span>
        </div>
      </div>

      {/* Source Documents */}
      <div className="text-sm text-gray-500">
        Extracted from: {sourceDocuments.join(', ')}
      </div>

      {/* No Changes Message */}
      {!hasChanges && (
        <div className="p-6 text-center bg-gray-50 rounded-lg">
          <p className="text-gray-600">No new information found in the uploaded documents.</p>
          <p className="text-sm text-gray-500 mt-2">
            Your profile already contains the information from these documents, or no extractable data was found.
          </p>
        </div>
      )}

      {/* Field Groups */}
      {hasChanges && (
        <div className="space-y-6">
          {renderFieldsByGroup()}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          onClick={onCancel}
          disabled={loading}
          className="flex-1 px-4 py-3 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleApply}
          disabled={loading || !hasChanges}
          className="flex-1 px-4 py-3 bg-perscholas-primary text-white rounded-lg hover:bg-perscholas-dark disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center gap-2"
        >
          {loading && (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
          {loading ? 'Saving...' : hasChanges ? 'Apply Changes' : 'No Changes to Apply'}
        </button>
      </div>
    </div>
  )
}
