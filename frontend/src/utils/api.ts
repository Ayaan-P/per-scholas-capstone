import { supabase } from './supabaseClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Helper to get auth headers
async function getAuthHeaders() {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  }

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
  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers || {})
    }
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
    fetch(`${API_BASE_URL}/api/rfps/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    }),

  addOpportunityToRfpDb: (opportunityId: string) =>
    fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/add-to-rfp-db`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }),

  // Jobs
  getJob: (jobId: string) =>
    fetch(`${API_BASE_URL}/api/jobs/${jobId}`),

  // Proposals
  getProposals: () =>
    fetch(`${API_BASE_URL}/api/proposals`),

  generateProposal: (data: any) =>
    fetch(`${API_BASE_URL}/api/proposals/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),

  updateProposalStatus: (proposalId: string, status: string) =>
    fetch(`${API_BASE_URL}/api/proposals/${proposalId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }),

  // Dashboard
  getDashboardStats: () =>
    fetch(`${API_BASE_URL}/api/dashboard/stats`),

  getDashboardActivity: () =>
    fetch(`${API_BASE_URL}/api/dashboard/activity`),

  // Analytics
  getAnalytics: (timeRange: string) =>
    fetch(`${API_BASE_URL}/api/analytics?range=${timeRange}`),

  // Scraped Grants
  getScrapedGrants: (params?: { source?: string; limit?: number; offset?: number }) =>
    fetch(`${API_BASE_URL}/api/scraped-grants?${new URLSearchParams(params as any).toString()}`),

  saveScrapedGrant: (grantId: string) =>
    authenticatedFetch(`${API_BASE_URL}/api/scraped-grants/${grantId}/save`, {
      method: 'POST',
      body: JSON.stringify({})
    }),

  getSchedulerStatus: () =>
    fetch(`${API_BASE_URL}/api/scheduler/status`),

  // Feedback
  submitOpportunityFeedback: (opportunityId: string, feedbackType: string) =>
    fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        feedback_type: feedbackType,
        user_id: 'current_user'
      })
    }),

  getOpportunityFeedback: (opportunityId: string) =>
    fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/feedback`),

  dismissOpportunity: (opportunityId: string) =>
    fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/dismiss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }),

  // Organization Config
  getOrganizationConfig: () =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/config`),

  saveOrganizationConfig: (config: any) =>
    authenticatedFetch(`${API_BASE_URL}/api/organization/config`, {
      method: 'POST',
      body: JSON.stringify(config)
    }),

  // Categories
  getCategories: () =>
    fetch(`${API_BASE_URL}/api/categories`),

  getCategoryDetail: (categoryId: number) =>
    fetch(`${API_BASE_URL}/api/categories/${categoryId}`)
}