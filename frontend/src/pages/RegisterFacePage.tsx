import { type FC } from 'react'
import { FaceCapture } from '../components/FaceCapture'

interface RegisterFacePageProps {
  userId?: string
  fullName?: string
  accessToken?: string
  onSuccess: () => void
  onCancel: () => void
  onGoToRegister: () => void
}

export const RegisterFacePage: FC<RegisterFacePageProps> = ({
  userId,
  fullName = 'User',
  accessToken,
  onSuccess,
  onCancel,
  onGoToRegister,
}) => {
  // If user tries to access /register-face without verified session credentials
  if (!accessToken || !userId) {
    return (
      <div className="auth-card placeholder-card">
        <div className="auth-header text-center">
          <div className="step-badge">
            <span className="step-num">Step 2 of 2</span>
            <span className="step-title">Biometric Enrollment</span>
          </div>
          <h2 className="card-title">Verification Required</h2>
          <p className="card-subtitle">
            Please register your account and verify your email OTP before enrolling your face.
          </p>
        </div>

        <div className="placeholder-actions">
          <button
            type="button"
            className="submit-btn primary"
            onClick={onGoToRegister}
            id="btn-go-to-register"
          >
            <span>Go to Registration →</span>
          </button>
        </div>

        <div className="privacy-notice">
          <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          <span>
            Security Protected: Direct access to face enrollment is restricted until email verification is confirmed.
          </span>
        </div>
      </div>
    )
  }

  return (
    <FaceCapture
      userId={userId}
      fullName={fullName}
      accessToken={accessToken}
      onSuccess={onSuccess}
      onCancel={onCancel}
    />
  )
}
