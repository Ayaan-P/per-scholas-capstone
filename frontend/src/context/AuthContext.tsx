'use client'

import { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react'
import { User } from '@supabase/supabase-js'
import { supabase } from '../utils/supabaseClient'

interface AuthContextType {
  user: User | null
  loading: boolean
  signUp: (email: string, password: string) => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    console.log('[Auth] Provider mounted, initializing...')

    // Check if user is logged in on mount
    const checkUser = async () => {
      try {
        console.log('[Auth] Checking session...')
        const { data: { session } } = await supabase.auth.getSession()
        console.log('[Auth] Session check result:', {
          hasSession: !!session,
          email: session?.user?.email,
          expiresAt: session?.expires_at
        })
        setUser(session?.user ?? null)
        setLoading(false)
      } catch (error) {
        console.error('[Auth] Error checking auth state:', error)
        setLoading(false)
      }
    }

    checkUser()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        console.log('[Auth] Auth state event fired:', {
          event,
          hasSession: !!session,
          email: session?.user?.email,
          expiresAt: session?.expires_at
        })
        setUser(session?.user ?? null)
        setLoading(false)
      }
    )

    return () => {
      console.log('[Auth] Provider unmounting, cleaning up listener')
      subscription?.unsubscribe()
    }
  }, [])

  const signUp = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password
    })
    if (error) throw error
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    if (error) throw error
  }, [])

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    signUp,
    signIn,
    signOut,
    isAuthenticated: !!user
  }), [user, loading, signUp, signIn, signOut])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
