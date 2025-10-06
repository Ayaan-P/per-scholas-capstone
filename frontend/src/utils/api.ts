const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export const api = {
  baseURL: API_BASE_URL,

  // Opportunities
  searchOpportunities: (data: any) =>
    fetch(`${API_BASE_URL}/api/search-opportunities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),

  getOpportunities: () =>
    fetch(`${API_BASE_URL}/api/opportunities`),

  saveOpportunity: (opportunityId: string) =>
    fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    }),

  getSimilarRfps: (opportunityId: string) =>
    fetch(`${API_BASE_URL}/api/rfps/similar/${opportunityId}`),

  loadRfps: () =>
    fetch(`${API_BASE_URL}/api/rfps/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
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
    fetch(`${API_BASE_URL}/api/scraped-grants/${grantId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }),

  getSchedulerStatus: () =>
    fetch(`${API_BASE_URL}/api/scheduler/status`)
}