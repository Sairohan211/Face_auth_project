import { useState, type FormEvent, type FC } from 'react'
import { loginAccount, type LoginResponse } from '../lib/api'
import { supabase } from '../lib/supabase'

interface LoginFormProps {
  onSuccess: (authData: { userId: string; email: string; accessToken: string; emailVerified?: boolean }) => void
  onSwitchToRegister?: () => void
}

const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/

export const LoginForm: FC<LoginFormProps> = ({ onSuccess, onSwitchToRegister }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      errors.email = 'Email address is required.'
    } else if (!EMAIL_REGEX.test(trimmedEmail)) {
      errors.email = 'Please enter a valid email address.'
    }

    if (!password) {
      errors.password = 'Password is required.'
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

      // 1. Call FastAPI backend login endpoint POST /api/auth/login
      // Password is not verified manually on the frontend
      const loginRes: LoginResponse = await loginAccount({
        email: cleanEmail,
        password: password,
      })

      if (!loginRes.success || !loginRes.access_token) {
        throw new Error(loginRes.message || 'Login failed.')
      }

      // 2. Set Supabase session in client if session tokens are returned
      if (loginRes.session?.refresh_token && loginRes.session?.access_token) {
        try {
          await supabase.auth.setSession({
            access_token: loginRes.session.access_token,
            refresh_token: loginRes.session.refresh_token,
          })
        } catch (sessionErr) {
          console.warn('Could not set Supabase client session:', sessionErr)
        }
      }

      // 3. Move to next step with access token and email verification state
      onSuccess({
        userId: loginRes.user_id,
        email: cleanEmail,
        accessToken: loginRes.access_token,
        emailVerified: loginRes.email_verified,
      })

    } catch (err: any) {
      console.error('Login error:', err)
      setFormError(err.message || 'Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-header">
        <div className="step-badge">
          <span className="step-num">Step 1 of 2</span>
          <span className="step-title">Password Authentication</span>
        </div>
        <h2 className="card-title">Welcome back</h2>
        <p className="card-subtitle">
          Sign in with your email and password to begin biometric verification.
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
          <label htmlFor="loginEmail" className="form-label">
            Email Address <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="loginEmail"
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
          <label htmlFor="loginPassword" className="form-label">
            Password <span className="req">*</span>
          </label>
          <div className="input-wrapper">
            <input
              id="loginPassword"
              type={showPassword ? 'text' : 'password'}
              className={`form-input with-toggle ${fieldErrors.password ? 'has-error' : ''}`}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
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

        <button
          type="submit"
          className="submit-btn primary"
          disabled={loading}
          id="btn-login-submit"
        >
          {loading ? (
            <span className="spinner-wrapper">
              <span className="spinner"></span>
              <span>Authenticating...</span>
            </span>
          ) : (
            <span>Verify Password & Continue →</span>
          )}
        </button>
      </form>

      <div className="auth-footer">
        <p>
          Don't have an account?{' '}
          <button
            type="button"
            className="link-btn"
            onClick={onSwitchToRegister}
            id="btn-switch-to-register"
          >
            Create an Account
          </button>
        </p>
      </div>
    </div>
  )
}
