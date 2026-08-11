import { useState, type FormEvent, type FC } from 'react'
import { registerAccount } from '../lib/api'
import { supabase } from '../lib/supabase'

interface RegisterFormProps {
  onSuccess: (data: { userId: string; email: string; fullName: string; accessToken: string }) => void
  onSwitchToLogin?: () => void
}

const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/

export const RegisterForm: FC<RegisterFormProps> = ({ onSuccess, onSwitchToLogin }) => {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    if (!fullName.trim()) {
      errors.fullName = 'Full name is required.'
    }

    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      errors.email = 'Email address is required.'
    } else if (!EMAIL_REGEX.test(trimmedEmail)) {
      errors.email = 'Please enter a valid email address.'
    }

    if (!password) {
      errors.password = 'Password is required.'
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters.'
    }

    if (!confirmPassword) {
      errors.confirmPassword = 'Confirm your password.'
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!validate()) {
      return
    }

    setLoading(true)

    try {
      const cleanEmail = email.trim().toLowerCase()
      const cleanName = fullName.trim()

      // 1. Create user account via Backend API (sets email_verified=False, sends Resend OTP)
      const registerRes = await registerAccount({
        full_name: cleanName,
        email: cleanEmail,
        password: password,
      })

      if (!registerRes.success || !registerRes.user_id) {
        throw new Error(registerRes.message || 'Account registration failed.')
      }

      // 2. Sign in to establish browser Supabase session
      let userToken = ''
      try {
        const { data: authData } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password: password,
        })
        if (authData.session?.access_token) {
          userToken = authData.session.access_token
        }
      } catch (authErr) {
        console.warn('Session acquisition notice:', authErr)
      }

      // 3. Navigate to Email OTP Verification (email verification required before face enrollment)
      onSuccess({
        userId: registerRes.user_id,
        email: cleanEmail,
        fullName: cleanName,
        accessToken: userToken,
      })
    } catch (err: any) {
      console.error('Registration error:', err)
      setFormError(err.message || 'An unexpected error occurred during registration.')
    } finally {
      setLoading(false)
    }
  }



  return (
    <div className="auth-card">
      <div className="auth-header">
        <div className="step-badge">
          <span className="step-num">Step 1 of 2</span>
          <span className="step-title">Account Creation</span>
        </div>
        <h2 className="card-title">Create your account</h2>
        <p className="card-subtitle">
          Enter your details below to get started with biometric protection.
        </p>
      </div>

      {formError && (
        <div className="alert-box error" role="alert">
          <svg className="alert-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span>{formError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="auth-form">
        <div className="form-group">
          <label htmlFor="fullName" className="form-label">
            Full Name <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="fullName"
              type="text"
              className={`form-input ${fieldErrors.fullName ? 'has-error' : ''}`}
              placeholder="e.g. Alex Johnson"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={loading}
              autoComplete="name"
              required
            />
          </div>
          {fieldErrors.fullName && <span className="field-error">{fieldErrors.fullName}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="email" className="form-label">
            Email Address <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="email"
              type="email"
              className={`form-input ${fieldErrors.email ? 'has-error' : ''}`}
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              autoComplete="email"
              required
            />
          </div>
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="password" className="form-label">
            Password <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className={`form-input with-toggle ${fieldErrors.password ? 'has-error' : ''}`}
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="new-password"
              required
            />
            <button
              type="button"
              className="toggle-password-btn"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              tabIndex={-1}
            >
              {showPassword ? (
                <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              ) : (
                <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              )}
            </button>
          </div>
          {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword" className="form-label">
            Confirm Password <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              className={`form-input ${fieldErrors.confirmPassword ? 'has-error' : ''}`}
              placeholder="Re-enter password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              autoComplete="new-password"
              required
            />
          </div>
          {fieldErrors.confirmPassword && (
            <span className="field-error">{fieldErrors.confirmPassword}</span>
          )}
        </div>

        <button
          type="submit"
          className="submit-btn primary"
          disabled={loading}
          id="btn-register-submit"
        >
          {loading ? (
            <span className="spinner-wrapper">
              <span className="spinner"></span>
              <span>Creating Account...</span>
            </span>
          ) : (
            <span>Continue to Face Registration →</span>
          )}

        </button>
      </form>

      {onSwitchToLogin && (
        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <button
              type="button"
              className="link-btn"
              onClick={onSwitchToLogin}
            >
              Sign In
            </button>
          </p>
        </div>
      )}
    </div>
  )
}
