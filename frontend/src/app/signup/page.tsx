'use client'

export const dynamic = 'force-dynamic'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../../context/AuthContext'
import { supabase } from '../../utils/supabaseClient'
import Link from 'next/link'
import Image from 'next/image'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [organizationName, setOrganizationName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { signUp, isAuthenticated } = useAuth()

  // Redirect if already logged in
  if (isAuthenticated) {
    router.push('/dashboard')
    return null
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate inputs
    if (!email || !password || !confirmPassword || !organizationName) {
      setError('Please fill in all fields')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long')
      return
    }

    setLoading(true)

    try {
      console.log('[Signup] Starting signup process...')
      await signUp(email, password, organizationName)
      console.log('[Signup] Signup successful, waiting for auth state...')

      // Wait a bit for auth state to be updated
      await new Promise(resolve => setTimeout(resolve, 500))

      // After signup, the user is automatically signed in
      // Initialize user profile in the backend
      const session = await supabase.auth.getSession()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      console.log('[Signup] Session after signup:', {
        hasSession: !!session.data.session,
        email: session.data.session?.user?.email,
        accessToken: !!session.data.session?.access_token,
        expiresAt: session.data.session?.expires_at
      })

      if (!session.data.session?.access_token) {
        console.warn('[Signup] No access token found in session, continuing anyway...')
      }

      const initResponse = await fetch(`${apiUrl}/api/auth/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.data.session?.access_token || ''}`
        },
        body: JSON.stringify({
          email,
          organization_name: organizationName,
          mission: ''
        })
      })

      console.log('[Signup] Initialize response:', {
        status: initResponse.status,
        ok: initResponse.ok
      })

      if (!initResponse.ok) {
        console.error('[Signup] Failed to initialize user:', initResponse.status, await initResponse.text())
      }

      // Redirect to onboarding for new users
      console.log('[Signup] Signup flow complete, redirecting to onboarding')
      router.push('/onboarding')
    } catch (err: any) {
      setError(err.message || 'Failed to create account. Please try again.')
      console.error('Sign up error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md card-elevated p-8 animate-fade-in">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="flex justify-center mb-5">
            <div className="relative group">
              <div className="absolute inset-0 bg-perscholas-primary/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"></div>
              <Image
                src="/logo.png"
                alt="FundFish Logo"
                width={70}
                height={70}
                className="relative h-[70px] w-auto transition-transform duration-300 group-hover:scale-105"
              />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-perscholas-primary mb-2">Get Started</h1>
          <p className="text-gray-600">Create your FundFish account</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 flex items-start gap-3 animate-shake">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">{error}</span>
          </div>
        )}

        <form onSubmit={handleSignUp} className="space-y-5">
          {/* Organization Name */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Organization Name
            </label>
            <input
              type="text"
              value={organizationName}
              onChange={(e) => setOrganizationName(e.target.value)}
              placeholder="Your Organization"
              required
              disabled={loading}
              className="input-premium w-full disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@organization.org"
              required
              disabled={loading}
              className="input-premium w-full disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              minLength={8}
              className="input-premium w-full disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-2">Minimum 8 characters</p>
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              minLength={8}
              className="input-premium w-full disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Sign Up Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary py-3.5 text-base disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating account...
              </span>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-white text-gray-500">Already have an account?</span>
          </div>
        </div>

        {/* Sign In Link */}
        <Link
          href="/login"
          className="block w-full btn-secondary py-3 text-center"
        >
          Sign In
        </Link>
      </div>
    </div>
  )
}
