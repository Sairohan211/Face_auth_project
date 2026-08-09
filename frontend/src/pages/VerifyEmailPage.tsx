import { useState, useEffect, useRef, type FC, type FormEvent, type KeyboardEvent, type ClipboardEvent } from 'react'
import { verifyEmailApi, resendOtpApi } from '../lib/api'

interface VerifyEmailPageProps {
  email: string
  fullName?: string
  userId?: string
  accessToken?: string
  onVerificationSuccess: (authData: { userId: string; email: string; fullName: string; accessToken: string }) => void
  onBackToRegister?: () => void
  onSwitchToLogin?: () => void
}

export const VerifyEmailPage: FC<VerifyEmailPageProps> = ({
  email,
  fullName = '',
  userId = '',
  accessToken = '',
  onVerificationSuccess,
  onBackToRegister,
  onSwitchToLogin,
}) => {
  const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [statusText, setStatusText] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successInfo, setSuccessInfo] = useState<string | null>(null)
  const [resendCooldown, setResendCooldown] = useState<number>(60)
  const [isSuccess, setIsSuccess] = useState(false)

  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // Resend cooldown timer
  useEffect(() => {
    let timer: any = null
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => Math.max(0, prev - 1))
      }, 1000)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [resendCooldown])

  // Focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus()
  }, [])

  const handleDigitChange = (index: number, value: string) => {
    // Only accept numeric characters (0-9)
    const cleanValue = value.replace(/[^0-9]/g, '')

    if (!cleanValue) {
      const updated = [...otpDigits]
      updated[index] = ''
      setOtpDigits(updated)
      return
    }

    // Pick last character
    const char = cleanValue.slice(-1)
    const updated = [...otpDigits]
    updated[index] = char
    setOtpDigits(updated)
    setErrorMessage(null)

    // Move to next input if available
    if (index < 5 && char) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      // Move focus back to previous box on backspace if current is empty
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault()
    // Extract only digits from clipboard
    const pasted = e.clipboardData.getData('text').trim().replace(/[^0-9]/g, '')
    if (!pasted) return

    const chars = pasted.slice(0, 6).split('')
    const updated = [...otpDigits]
    chars.forEach((c, idx) => {
      if (idx < 6) updated[idx] = c
    })
    setOtpDigits(updated)
    setErrorMessage(null)

    const nextIndex = Math.min(chars.length, 5)
    inputRefs.current[nextIndex]?.focus()
  }

  const fullOtpCode = otpDigits.join('').trim()

  const handleVerify = async (e?: FormEvent) => {
    if (e) e.preventDefault()
    setErrorMessage(null)
    setSuccessInfo(null)

    if (fullOtpCode.length < 6) {
      setErrorMessage('Invalid or expired verification code.')
      return
    }

    if (!email) {
      setErrorMessage('Missing registration email. Please return to registration.')
      return
    }

    setLoading(true)
    setStatusText('Verifying...')

    try {
      // 1. Verify OTP via FastAPI POST /api/auth/verify-email
      await verifyEmailApi({
        email: email.trim().toLowerCase(),
        otp: fullOtpCode,
      })

      // 2. Success: Mark verified state
      setStatusText('Email verified ✓')
      setIsSuccess(true)

      // 3. Move to face registration with verified session data
      onVerificationSuccess({
        userId: userId,
        email: email.trim().toLowerCase(),
        fullName: fullName,
        accessToken: accessToken,
      })
    } catch (err: any) {
      console.error('OTP verification error:', err)
      setStatusText('Verification failed')
      setErrorMessage(err.message || 'Invalid or expired verification code.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (resendCooldown > 0 || resending) return

    setErrorMessage(null)
    setSuccessInfo(null)
    setResending(true)
    setStatusText('Sending code...')

    try {
      // Call FastAPI POST /api/auth/resend-otp
      await resendOtpApi({
        email: email.trim().toLowerCase(),
      })

      setStatusText('Code sent ✓')
      setSuccessInfo('A new verification code has been sent.')
      setResendCooldown(60)
    } catch (err: any) {
      console.error('Resend OTP error:', err)
      setStatusText('')
      setErrorMessage(err.message || 'Could not resend verification code. Please try again.')
    } finally {
      setResending(false)
    }
  }


  // If email is missing, show fallback to registration
  if (!email) {
    return (
      <div className="auth-card placeholder-card">
        <div className="auth-header text-center">
          <div className="step-badge">
            <span className="step-num">Step 1.5 of 2</span>
            <span className="step-title">Email Verification</span>
          </div>
          <h2 className="card-title">Registration Required</h2>
          <p className="card-subtitle">
            Please register your account to receive a verification OTP code.
          </p>
        </div>

        <div className="placeholder-actions">
          <button
            type="button"
            className="submit-btn primary"
            onClick={onBackToRegister || onSwitchToLogin}
            id="btn-return-register"
          >
            <span>Go to Registration</span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-card otp-card">
      <div className="auth-header text-center">
        <div className="step-badge">
          <span className="step-num">Step 1.5 of 2</span>
          <span className="step-title">Email Verification</span>
        </div>
        <h2 className="card-title">Verify Your Email</h2>
        <p className="card-subtitle">
          We've sent a 6-digit verification code to:
          <br />
          <strong className="text-highlight">{email}</strong>
          <br />
          <span className="sub-instruction">Enter the code below to continue.</span>
        </p>
      </div>

      {statusText && (
        <div className="biometric-status-bar">
          <div className={`status-pill ${isSuccess ? 'ready' : loading || resending ? 'processing' : statusText === 'Code sent ✓' ? 'ready' : 'waiting'}`}>
            <span className="pulse-dot"></span>
            <span className="status-label">{statusText}</span>
          </div>
        </div>
      )}

      {successInfo && (
        <div className="alert-box success" role="status">
          <span className="success-icon">✓</span>
          <span>{successInfo}</span>
        </div>
      )}

      {errorMessage && (
        <div className="alert-box error" role="alert">
          <svg className="alert-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleVerify} className="otp-form">
        <div className="form-group">
          <div className="otp-input-group" onPaste={handlePaste}>
            {otpDigits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputRefs.current[index] = el
                }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                className={`otp-digit-input ${digit ? 'filled' : ''} ${errorMessage ? 'has-error' : ''}`}
                value={digit}
                onChange={(e) => handleDigitChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                disabled={loading || isSuccess}
                autoComplete="one-time-code"
                aria-label={`Digit ${index + 1}`}
              />
            ))}
          </div>
        </div>

        <div className="otp-actions">
          <button
            type="submit"
            className="submit-btn primary"
            disabled={loading || fullOtpCode.length < 6 || isSuccess}
            id="btn-verify-otp"
          >
            {loading ? (
              <span className="spinner-wrapper">
                <span className="spinner"></span>
                <span>Verifying...</span>
              </span>
            ) : (
              <span>Verify Email</span>
            )}
          </button>

          <button
            type="button"
            className="secondary-btn resend-btn"
            onClick={handleResend}
            disabled={resendCooldown > 0 || resending || loading || isSuccess}
            id="btn-resend-otp"
          >
            {resending ? (
              <span>Sending code...</span>
            ) : resendCooldown > 0 ? (
              <span>Resend Code ({resendCooldown}s)</span>
            ) : (
              <span>Resend Code</span>
            )}
          </button>
        </div>
      </form>

      <div className="otp-footer-links">
        {onBackToRegister && (
          <button
            type="button"
            className="text-subtle-btn"
            onClick={onBackToRegister}
            id="btn-back-to-register"
          >
            ← Back to registration
          </button>
        )}

        {onSwitchToLogin && (
          <p className="auth-footer-text">
            Already verified your account?{' '}
            <button
              type="button"
              className="link-btn"
              onClick={onSwitchToLogin}
            >
              Sign In
            </button>
          </p>
        )}
      </div>

      <div className="privacy-notice">
        <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>
          Multi-Factor Security: Email verification confirms your identity before proceeding to local biometric enrollment.
        </span>
      </div>
    </div>
  )
}
