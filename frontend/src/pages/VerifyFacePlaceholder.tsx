import { type FC } from 'react'

interface VerifyFacePlaceholderProps {
  email?: string
  onLogout: () => void
}

export const VerifyFacePlaceholder: FC<VerifyFacePlaceholderProps> = ({ email, onLogout }) => {
  return (
    <div className="auth-card placeholder-card">
      <div className="auth-header text-center">
        <div className="step-badge">
          <span className="step-num">Step 2 of 2</span>
          <span className="step-title">Biometric Verification</span>
        </div>
        <h2 className="card-title">Verify Your Identity</h2>
        <p className="card-subtitle">
          Your password has been verified.
          <br />
          Face verification is the next step.
        </p>
      </div>

      <div className="biometric-placeholder-visual">
        <div className="biometric-icon-container">
          <svg className="biometric-face-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
            <circle cx="9" cy="9" r="1"></circle>
            <circle cx="15" cy="9" r="1"></circle>
            <path d="M8 15s1.5 2 4 2 4-2 4-2"></path>
          </svg>
          <div className="scan-line-horizontal"></div>
        </div>

        {email && (
          <div className="verified-user-pill">
            <span className="user-dot"></span>
            <span>Authenticated as <strong>{email}</strong></span>
          </div>
        )}
      </div>

      <div className="placeholder-actions">
        <button
          type="button"
          className="submit-btn primary"
          onClick={() => {
            alert('Step 2 (Face Verification) engine will be implemented in the next step!')
          }}
          id="btn-continue-face-verify"
        >
          <span>Continue to Face Verification →</span>
        </button>

        <button
          type="button"
          className="secondary-btn logout-btn"
          onClick={onLogout}
          id="btn-logout"
        >
          <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Sign Out / Log Out</span>
        </button>
      </div>

      <div className="privacy-notice">
        <svg className="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>
          Biometric Protection: Password authentication confirmed. Camera access is strictly prevented until you initiate face verification.
        </span>
      </div>
    </div>
  )
}
