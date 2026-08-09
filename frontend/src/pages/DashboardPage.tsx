import { type FC } from 'react'

interface DashboardPageProps {
  email?: string
  onLogout: () => void
}

export const DashboardPage: FC<DashboardPageProps> = ({ email, onLogout }) => {
  return (
    <div className="auth-card dashboard-card">
      <div className="auth-header text-center">
        <div className="status-pill ready">
          <span className="pulse-dot"></span>
          <span className="status-label">Authenticated & Verified</span>
        </div>
        <h2 className="card-title text-success">Welcome to Dashboard</h2>
        <p className="card-subtitle">
          Multi-factor biometric authentication successfully completed.
        </p>
      </div>

      <div className="dashboard-user-box">
        <div className="dashboard-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="dashboard-avatar-icon">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>
        <div className="dashboard-user-details">
          <span className="dashboard-user-label">Logged-in User</span>
          <span className="dashboard-user-email">{email || 'User'}</span>
        </div>
      </div>

      <div className="dashboard-security-summary">
        <div className="security-item">
          <span className="security-icon success">✓</span>
          <div className="security-text">
            <strong>Password Authentication</strong>
            <span>Supabase secure token session active</span>
          </div>
        </div>
        <div className="security-item">
          <span className="security-icon success">✓</span>
          <div className="security-text">
            <strong>Face Biometric Verification</strong>
            <span>Cosine similarity threshold satisfied</span>
          </div>
        </div>
      </div>

      <div className="dashboard-actions">
        <button
          type="button"
          className="secondary-btn logout-btn"
          onClick={onLogout}
          id="btn-dashboard-logout"
        >
          <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Sign Out / Log Out</span>
        </button>
      </div>
    </div>
  )
}
