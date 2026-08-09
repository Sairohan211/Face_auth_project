import { useRef, useState, type FC } from 'react'
import { WebcamPreview, type WebcamRef } from './WebcamPreview'
import { registerFace } from '../lib/api'

interface FaceCaptureProps {
  userId: string
  fullName: string
  accessToken: string
  onSuccess: () => void
  onCancel?: () => void
}

export const FaceCapture: FC<FaceCaptureProps> = ({
  fullName,
  accessToken,
  onSuccess,
  onCancel,
}) => {
  const webcamRef = useRef<WebcamRef | null>(null)

  const [statusText, setStatusText] = useState<string>('Starting camera...')
  const [isCameraReady, setIsCameraReady] = useState(false)
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null)
  const [capturedPreviewUrl, setCapturedPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStatusChange = (status: string, ready: boolean) => {
    setStatusText(status)
    setIsCameraReady(ready)
  }

  const handleCapture = async () => {
    setError(null)
    if (!webcamRef.current) return

    try {
      const blob = await webcamRef.current.captureFrame()
      if (!blob) {
        setError('Failed to capture frame from webcam. Please try again.')
        return
      }

      // Stop camera feed while reviewing captured photo
      webcamRef.current.stopCamera()

      const previewUrl = URL.createObjectURL(blob)
      setCapturedBlob(blob)
      setCapturedPreviewUrl(previewUrl)
      setStatusText('Face captured. Review and submit.')
    } catch (err: any) {
      console.error('Capture error:', err)
      setError('An error occurred while capturing frame.')
    }
  }

  const handleRetake = () => {
    if (capturedPreviewUrl) {
      URL.revokeObjectURL(capturedPreviewUrl)
    }
    setCapturedBlob(null)
    setCapturedPreviewUrl(null)
    setError(null)
    setStatusText('Starting camera...')
    // Restart camera stream
    webcamRef.current?.restartCamera()
  }

  const handleSubmit = async () => {
    if (!capturedBlob) {
      setError('No captured face image to submit. Please capture a photo first.')
      return
    }

    setLoading(true)
    setError(null)
    setStatusText('Processing face...')

    try {
      // 1. Send captured face image blob to Backend Face Registration API
      const result = await registerFace(capturedBlob, accessToken)

      if (result.success) {
        setStatusText('Face registered successfully')
        // Clean up preview URL
        if (capturedPreviewUrl) {
          URL.revokeObjectURL(capturedPreviewUrl)
        }
        // Clean up camera stream
        webcamRef.current?.stopCamera()
        // Transition to success screen
        onSuccess()
      } else {
        throw new Error(result.message || 'Face registration failed.')
      }
    } catch (err: any) {
      console.error('Face registration error:', err)
      setStatusText('Registration failed')
      setError(err.message || 'Face registration failed. Please ensure your face is well-lit and clearly visible.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-card face-card">
      <div className="auth-header">
        <div className="step-badge">
          <span className="step-num">Step 2 of 2</span>
          <span className="step-title">Biometric Enrollment</span>
        </div>
        <h2 className="card-title">Register your face</h2>
        <p className="card-subtitle">
          Hello <strong>{fullName}</strong>, position your face in the center of the frame in a well-lit area.
        </p>
      </div>

      {/* Status Bar */}
      <div className="biometric-status-bar">
        <div className={`status-pill ${loading ? 'processing' : isCameraReady || capturedBlob ? 'ready' : 'waiting'}`}>
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

      {/* Camera / Snapshot Preview Area */}
      <div className="camera-frame-wrapper">
        {capturedPreviewUrl ? (
          <div className="captured-preview-container">
            <img
              src={capturedPreviewUrl}
              alt="Captured face preview"
              className="captured-image-preview"
            />
            <div className="preview-badge">Preview</div>
          </div>
        ) : (
          <WebcamPreview
            ref={webcamRef}
            onStatusChange={handleStatusChange}
            onError={(msg) => setError(msg)}
          />
        )}
      </div>

      {/* Actions */}
      <div className="face-actions">
        {!capturedBlob ? (
          <button
            type="button"
            className="submit-btn primary capture-btn"
            onClick={handleCapture}
            disabled={!isCameraReady || loading}
            id="btn-capture-face"
          >
            <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <circle cx="12" cy="13" r="4"></circle>
            </svg>
            <span>Capture Face</span>
          </button>
        ) : (
          <div className="action-button-group">
            <button
              type="button"
              className="secondary-btn"
              onClick={handleRetake}
              disabled={loading}
              id="btn-retake-face"
            >
              <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 4v6h6M23 20v-6h-6"></path>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
              </svg>
              <span>Retake Photo</span>
            </button>

            <button
              type="button"
              className="submit-btn primary"
              onClick={handleSubmit}
              disabled={loading}
              id="btn-submit-face"
            >
              {loading ? (
                <span className="spinner-wrapper">
                  <span className="spinner"></span>
                  <span>Processing Biometrics...</span>
                </span>
              ) : (
                <span>Confirm & Register Face ✓</span>
              )}
            </button>
          </div>
        )}

        {onCancel && !loading && (
          <button
            type="button"
            className="text-subtle-btn"
            onClick={() => {
              webcamRef.current?.stopCamera()
              onCancel()
            }}
          >
            Cancel and Return
          </button>
        )}
      </div>

      <div className="privacy-notice">
        <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>
          Privacy Protected: Raw photographs are never stored in the cloud. Only a one-way mathematical biometric representation is generated locally.
        </span>
      </div>
    </div>
  )
}
