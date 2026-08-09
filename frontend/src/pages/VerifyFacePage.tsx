import { useState, useRef, type FC } from 'react'
import { WebcamPreview, type WebcamRef } from '../components/WebcamPreview'
import { verifyFace, type FaceVerifyResponse } from '../lib/api'

interface VerifyFacePageProps {
  accessToken?: string
  email?: string
  onVerificationSuccess: () => void
  onLogout: () => void
  onGoToLogin?: () => void
}

export const VerifyFacePage: FC<VerifyFacePageProps> = ({
  accessToken,
  email,
  onVerificationSuccess,
  onLogout,
  onGoToLogin,
}) => {
  const webcamRef = useRef<WebcamRef | null>(null)

  const [statusText, setStatusText] = useState<string>('Starting camera...')
  const [isCameraReady, setIsCameraReady] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<FaceVerifyResponse | null>(null)

  const handleStatusChange = (status: string, ready: boolean) => {
    // Only update status if not in the middle of active verification or showing result
    if (!loading && !result) {
      setStatusText(status)
      setIsCameraReady(ready)
    }
  }

  const handleCaptureAndVerify = async () => {
    setError(null)
    if (!accessToken) {
      setError('Authentication session not found. Please log in first.')
      return
    }

    if (!webcamRef.current) return

    setStatusText('Capturing...')
    let capturedBlob: Blob | null = null

    try {
      capturedBlob = await webcamRef.current.captureFrame()
      if (!capturedBlob) {
        setStatusText('Camera ready')
        setError('Failed to capture frame from webcam. Please ensure your camera is enabled.')
        return
      }
    } catch (captureErr) {
      console.warn('Frame capture error:', captureErr)
      setStatusText('Camera ready')
      setError('Could not capture photo from camera. Please try again.')
      return
    }

    setLoading(true)
    setStatusText('Verifying face...')

    try {
      const verifyResponse = await verifyFace(capturedBlob, accessToken)
      setStatusText('Verification complete')
      setResult(verifyResponse)

      // Stop camera stream once a result is obtained
      webcamRef.current?.stopCamera()
    } catch (err: any) {
      console.error('Face verification request error:', err)
      setStatusText('Camera ready')
      setError(err.message || 'Face verification failed. Please try again.')
      // Keep camera live so user can adjust and re-attempt
    } finally {
      setLoading(false)
    }
  }

  const handleTryAgain = () => {
    setResult(null)
    setError(null)
    setStatusText('Starting camera...')
    setIsCameraReady(false)
    // Restart camera stream
    webcamRef.current?.restartCamera()
  }

  // If user is not authenticated, show sign-in prompt
  if (!accessToken) {
    return (
      <div className="auth-card placeholder-card">
        <div className="auth-header text-center">
          <div className="step-badge">
            <span className="step-num">Authentication Required</span>
          </div>
          <h2 className="card-title">Session Expired</h2>
          <p className="card-subtitle">
            Please sign in with your email and password before performing face verification.
          </p>
        </div>

        <div className="placeholder-actions">
          <button
            type="button"
            className="submit-btn primary"
            onClick={onGoToLogin || onLogout}
            id="btn-return-login"
          >
            <span>Go to Login</span>
          </button>
        </div>
      </div>
    )
  }

  // SUCCESS STATE: verified === true
  if (result && result.verified) {
    return (
      <div className="auth-card success-card">
        <div className="success-icon-wrapper">
          <div className="success-pulse-ring"></div>
          <div className="success-icon-circle">
            <svg className="success-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        </div>

        <div className="auth-header text-center">
          <h2 className="card-title text-success">✓ Identity Verified</h2>
          <div className="match-score-badge success">
            <span className="match-score-label">Face Match:</span>
            <span className="match-score-value">{result.match_score.toFixed(1)}%</span>
          </div>
          <p className="card-subtitle success-desc">
            Your identity has been successfully verified.
          </p>
        </div>

        <div className="success-info-box">
          <div className="info-item">
            <span className="info-dot"></span>
            <span>Biometric profile matched registered credentials</span>
          </div>
          {email && (
            <div className="info-item">
              <span className="info-dot"></span>
              <span>Account: <strong>{email}</strong></span>
            </div>
          )}
        </div>

        <div className="success-actions">
          <button
            type="button"
            className="submit-btn primary"
            onClick={onVerificationSuccess}
            id="btn-continue-dashboard"
          >
            <span>Continue to Dashboard →</span>
          </button>
        </div>
      </div>
    )
  }

  // FAILED STATE: verified === false
  if (result && !result.verified) {
    return (
      <div className="auth-card verification-failed-card">
        <div className="failed-icon-wrapper">
          <div className="failed-icon-circle">
            <svg className="failed-cross-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </div>
        </div>

        <div className="auth-header text-center">
          <h2 className="card-title text-danger">✕ Face Verification Failed</h2>
          <div className="match-score-badge failed">
            <span className="match-score-label">Face Match:</span>
            <span className="match-score-value">{result.match_score.toFixed(1)}%</span>
          </div>
          <p className="card-subtitle failed-desc">
            The captured face does not match your registered face.
          </p>
        </div>

        <div className="failed-actions">
          <button
            type="button"
            className="submit-btn primary"
            onClick={handleTryAgain}
            id="btn-try-again-face"
          >
            <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 4v6h6M23 20v-6h-6"></path>
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
            </svg>
            <span>Try Again</span>
          </button>

          <button
            type="button"
            className="secondary-btn logout-btn"
            onClick={onLogout}
            id="btn-verify-logout"
          >
            <span>Sign Out</span>
          </button>
        </div>

        <div className="privacy-notice">
          <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          <span>
            Security Alert: Access to the dashboard is blocked until biometric verification passes. Ensure good lighting and remove items obstructing your face.
          </span>
        </div>
      </div>
    )
  }

  // ACTIVE CAMERA CAPTURE / VERIFY VIEW
  return (
    <div className="auth-card face-card">
      <div className="auth-header">
        <div className="step-badge">
          <span className="step-num">Step 2 of 2</span>
          <span className="step-title">Biometric Verification</span>
        </div>
        <h2 className="card-title">Verify Your Identity</h2>
        <p className="card-subtitle">
          Please position your face inside the camera frame.
        </p>
      </div>

      {/* Status Bar */}
      <div className="biometric-status-bar">
        <div className={`status-pill ${loading ? 'processing' : isCameraReady ? 'ready' : 'waiting'}`}>
          <span className="pulse-dot"></span>
          <span className="status-label">{statusText}</span>
        </div>
      </div>

      {/* Alert Error Box */}
      {error && (
        <div className="alert-box error" role="alert">
          <svg className="alert-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Camera Viewport Area */}
      <div className="camera-frame-wrapper">
        <WebcamPreview
          ref={webcamRef}
          onStatusChange={handleStatusChange}
          onError={(msg) => setError(msg)}
        />
      </div>

      {/* Actions */}
      <div className="face-actions">
        <button
          type="button"
          className="submit-btn primary capture-btn"
          onClick={handleCaptureAndVerify}
          disabled={!isCameraReady || loading}
          id="btn-capture-verify"
        >
          {loading ? (
            <span className="spinner-wrapper">
              <span className="spinner"></span>
              <span>Verifying Face Biometrics...</span>
            </span>
          ) : (
            <>
              <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
              </svg>
              <span>Capture &amp; Verify</span>
            </>
          )}
        </button>

        <button
          type="button"
          className="secondary-btn logout-btn"
          onClick={() => {
            webcamRef.current?.stopCamera()
            onLogout()
          }}
          disabled={loading}
          id="btn-verify-cancel-logout"
        >
          <span>Sign Out / Cancel</span>
        </button>
      </div>

      <div className="privacy-notice">
        <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>
          Biometric Protection: The captured verification frame is processed strictly in memory and is never stored on any server or disk.
        </span>
      </div>
    </div>
  )
}
