import mixpanel from 'mixpanel-browser'

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN || ''
let initialized = false

export function initAnalytics(projectName: string = 'fundfish') {
  if (initialized || typeof window === 'undefined') return
  
  if (MIXPANEL_TOKEN) {
    mixpanel.init(MIXPANEL_TOKEN, {
      debug: process.env.NODE_ENV === 'development',
      track_pageview: false, // We handle this manually
      persistence: 'localStorage',
    })
    initialized = true
  }
}

export function track(event: string, properties?: Record<string, unknown>) {
  if (!initialized || !MIXPANEL_TOKEN) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] track:', event, properties)
    }
    return
  }
  mixpanel.track(event, properties)
}

export function trackPage(pageName: string, properties?: Record<string, unknown>) {
  track('Page View', { page: pageName, ...properties })
}

export function identify(userId: string, traits?: Record<string, unknown>) {
  if (!initialized || !MIXPANEL_TOKEN) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] identify:', userId, traits)
    }
    return
  }
  mixpanel.identify(userId)
  if (traits) {
    mixpanel.people.set(traits)
  }
}

export function reset() {
  if (!initialized || !MIXPANEL_TOKEN) return
  mixpanel.reset()
}
