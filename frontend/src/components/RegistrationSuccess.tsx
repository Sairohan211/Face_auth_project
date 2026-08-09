import { type FC } from 'react'

interface RegistrationSuccessProps {
  onGoToLogin?: () => void
}

export const RegistrationSuccess: FC<RegistrationSuccessProps> = ({ onGoToLogin }) => {
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
        <h2 className="card-title text-success">✓ Registration Complete</h2>
        <p className="card-subtitle success-desc">
          Your account and face have been registered successfully.
        </p>
      </div>

      <div className="success-info-box">
        <div className="info-item">
          <span className="info-dot"></span>
          <span>Account created & verified</span>
        </div>
        <div className="info-item">
          <span className="info-dot"></span>
          <span>512-D Face biometric profile encrypted</span>
        </div>
        <div className="info-item">
          <span className="info-dot"></span>
          <span>Ready for biometric authentication</span>
        </div>
      </div>

      <div className="success-actions">
        <button
          type="button"
          className="submit-btn primary"
          onClick={() => {
            if (onGoToLogin) {
              onGoToLogin()
            } else {
              alert('Registration complete! Login interface will be available in the next step.')
            }
          }}
          id="btn-go-to-login"
        >
          <span>Go to Login →</span>
        </button>
      </div>
    </div>
  )
}
