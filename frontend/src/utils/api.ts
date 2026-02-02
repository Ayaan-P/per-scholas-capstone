import { supabase } from './supabaseClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Helper to get auth headers
async function getAuthHeaders() {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  return headers
}

// Helper to get auth token only (without content-type)
async function getAuthToken() {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

// Wrapper for authenticated fetch calls
async function authenticatedFetch(url: string, options: RequestInit = {}) {
  const headers = await getAuthHeaders()
  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...headers,
    ...(options.headers || {})
  }
  return fetch(url, {
    ...options,
    headers: mergedHeaders
  })
}

export const api = {
  baseURL: API_BASE_URL,

  // Opportunities
  searchOpportunities: async (data: any) => {
    const headers = await getAuthHeaders()
    return fetch(`${API_BASE_URL}/api/search-opportunities`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    })
  },

  getOpportunities: () =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities`),

  saveOpportunity: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/save`, {
      method: 'POST',
      body: JSON.stringify({})
    }),

  deleteOpportunity: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}`, {
      method: 'DELETE'
    }),

  updateOpportunityDescription: (opportunityId: string, description: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/description`, {
      method: 'PATCH',
      body: JSON.stringify({ description })
    }),

  updateOpportunityNotes: (opportunityId: string, notes: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/notes`, {
      method: 'PATCH',
      body: JSON.stringify({ notes })
    }),

  generateOpportunitySummary: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/generate-summary`, {
      method: 'POST'
    }),

  getSimilarRfps: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/rfps/similar/${opportunityId}`),

  uploadRfp: async (file: File, title?: string, funder?: string, deadline?: string) => {
    const token = await getAuthToken()
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    if (funder) formData.append('funder', funder)
    if (deadline) formData.append('deadline', deadline)

    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    return fetch(`${API_BASE_URL}/api/rfps/upload`, {
      method: 'POST',
      headers,
      body: formData
    })
  },

  loadRfps: () =>
    authenticatedFetch(`${API_BASE_URL}/api/rfps/load`, {
      method: 'POST',
      body: JSON.stringify({})
    }),

  addOpportunityToRfpDb: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/add-to-rfp-db`, {
      method: 'POST'
    }),

  // Jobs
  getJob: (jobId: string) =>
    fetch(`${API_BASE_URL}/api/jobs/${jobId}`),

  // Proposals
  getProposals: () =>
    authenticatedFetch(`${API_BASE_URL}/api/proposals`),

  generateProposal: (data: any) =>
    authenticatedFetch(`${API_BASE_URL}/api/proposals/generate`, {
      method: 'POST',
      body: JSON.stringify(data)
    }),

  updateProposalStatus: (proposalId: string, status: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/proposals/${proposalId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status })
    }),

  // Dashboard
  getDashboardStats: () =>
    authenticatedFetch(`${API_BASE_URL}/api/dashboard/stats`),

  getDashboardActivity: () =>
    authenticatedFetch(`${API_BASE_URL}/api/dashboard/activity`),

  // Analytics
  getAnalytics: (timeRange: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/analytics?range=${timeRange}`),

  // Scraped Grants (authenticated to get personalized match scores)
  getScrapedGrants: async (params?: { source?: string; limit?: number; offset?: number }) =>
    authenticatedFetch(`${API_BASE_URL}/api/scraped-grants?${new URLSearchParams(params as any).toString()}`),

  saveScrapedGrant: (grantId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/scraped-grants/${grantId}/save`, {
      method: 'POST',
      body: JSON.stringify({})
    }),

  getSchedulerStatus: () =>
    fetch(`${API_BASE_URL}/api/scheduler/status`),

  // Feedback
  submitOpportunityFeedback: (opportunityId: string, feedbackType: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ 
        feedback_type: feedbackType
      })
    }),

  getOpportunityFeedback: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/feedback`),

  dismissOpportunity: (opportunityId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/dismiss`, {
      method: 'POST'
    }),

  // Organization Config
  getOrganizationConfig: () =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/config`),

  saveOrganizationConfig: (config: any) =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/config`, {
      method: 'POST',
      body: JSON.stringify(config)
    }),

  // Organization Documents
  uploadOrganizationDocuments: async (files: File[]) => {
    const token = await getAuthToken()
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))

    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    // Don't set Content-Type for FormData - browser will set multipart/form-data automatically

    return fetch(`${API_BASE_URL}/api/organization/documents/upload`, {
      method: 'POST',
      headers,
      body: formData
    })
  },

  extractOrganizationInfo: (documentIds: string[]) =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/documents/extract`, {
      method: 'POST',
      body: JSON.stringify({ document_ids: documentIds })
    }),

  applyExtractedData: (extractedData: any, resolvedConflicts: any, sourceDocumentIds: string[]) =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/documents/apply`, {
      method: 'POST',
      body: JSON.stringify({
        extracted_data: extractedData,
        resolved_conflicts: resolvedConflicts,
        source_document_ids: sourceDocumentIds
      })
    }),

  getOrganizationDocuments: () =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/documents`),

  deleteOrganizationDocument: (documentId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/documents/${documentId}`, {
      method: 'DELETE'
    }),

  // Categories
  getCategories: () =>
    fetch(`${API_BASE_URL}/api/categories`),

  getCategoryDetail: (categoryId: number) =>
    fetch(`${API_BASE_URL}/api/categories/${categoryId}`)
}