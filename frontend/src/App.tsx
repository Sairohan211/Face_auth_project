import { useState, useEffect, type FC } from 'react'
import './App.css'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { RegisterFacePage } from './pages/RegisterFacePage'
import { VerifyFacePage } from './pages/VerifyFacePage'
import { DashboardPage } from './pages/DashboardPage'
import { RegistrationSuccess } from './components/RegistrationSuccess'
import { supabase } from './lib/supabase'

export interface AuthenticatedUser {
  userId: string
  email: string
  fullName?: string
  accessToken: string
}

const App: FC = () => {
  // Normalize current path
  const getInitialPath = (): string => {
    const p = window.location.pathname.toLowerCase()
    if (
      p === '/register' ||
      p === '/verify-email' ||
      p === '/register-face' ||
      p === '/verify-face' ||
      p === '/dashboard' ||
      p === '/login'
    ) {
      return p
    }
    return '/login'
  }

  const [currentPath, setCurrentPath] = useState<string>(getInitialPath)
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null)
  const [pendingRegistrationEmail, setPendingRegistrationEmail] = useState<string>('')
  const [registrationSuccess, setRegistrationSuccess] = useState(false)

  const navigate = (path: string) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path)
    }
    setCurrentPath(path)
  }

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const p = window.location.pathname.toLowerCase()
      if (
        p === '/register' ||
        p === '/verify-email' ||
        p === '/register-face' ||
        p === '/verify-face' ||
        p === '/dashboard' ||
        p === '/login'
      ) {
        setCurrentPath(p)
      } else {
        setCurrentPath('/login')
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Check existing Supabase session on initial load
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user && session.access_token) {
        setCurrentUser({
          userId: session.user.id,
          email: session.user.email || '',
          fullName: session.user.user_metadata?.full_name || '',
          accessToken: session.access_token,
        })
      }
    })
  }, [])

  const handleLoginSuccess = (authData: AuthenticatedUser & { emailVerified?: boolean }) => {
    setCurrentUser(authData)
    // Email verification bypassed for demo -> navigate straight to biometric verification
    navigate('/verify-face')
  }

  const handleAccountCreated = (data: { userId: string; email: string; fullName: string; accessToken: string }) => {
    setPendingRegistrationEmail(data.email)
    setCurrentUser({
      userId: data.userId,
      email: data.email,
      fullName: data.fullName,
      accessToken: data.accessToken,
    })
    // Directly go to face registration stage
    navigate('/register-face')
  }

  const handleEmailVerificationSuccess = (authData: { userId: string; email: string; fullName: string; accessToken: string }) => {
    setCurrentUser({
      userId: authData.userId,
      email: authData.email,
      fullName: authData.fullName,
      accessToken: authData.accessToken,
    })
    navigate('/register-face')
  }

  const handleFaceRegistrationSuccess = () => {
    setRegistrationSuccess(true)
  }

  const handleVerificationSuccess = () => {
    navigate('/dashboard')
  }

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut()
    } catch (err) {
      console.warn('Sign out error:', err)
    }
    setCurrentUser(null)
    setPendingRegistrationEmail('')
    setRegistrationSuccess(false)
    navigate('/login')
  }

  return (
    <div className="container">
      {/* Brand Header Navigation */}
      <header className="brand-header">
        <div className="logo-badge">
          <span className="logo-dot"></span>
          FaceAuthSystem
        </div>
      </header>

      {/* Main Routed Page */}
      <main className="content-wrapper">
        {currentPath === '/login' && (
          <LoginPage
            onLoginSuccess={handleLoginSuccess}
            onSwitchToRegister={() => navigate('/register')}
          />
        )}

        {currentPath === '/register' && (
          <RegisterPage
            onSuccess={handleAccountCreated}
            onSwitchToLogin={() => navigate('/login')}
          />
        )}

        {currentPath === '/verify-email' && (
          <VerifyEmailPage
            email={pendingRegistrationEmail || currentUser?.email || ''}
            fullName={currentUser?.fullName}
            userId={currentUser?.userId}
            accessToken={currentUser?.accessToken}
            onVerificationSuccess={handleEmailVerificationSuccess}
            onBackToRegister={() => navigate('/register')}
            onSwitchToLogin={() => navigate('/login')}
          />
        )}

        {currentPath === '/register-face' && (
          registrationSuccess ? (
            <RegistrationSuccess onGoToLogin={() => {
              setRegistrationSuccess(false)
              navigate('/login')
            }} />
          ) : (
            <RegisterFacePage
              userId={currentUser?.userId}
              fullName={currentUser?.fullName || 'User'}
              accessToken={currentUser?.accessToken}
              onSuccess={handleFaceRegistrationSuccess}
              onCancel={() => navigate('/register')}
              onGoToRegister={() => navigate('/register')}
            />
          )
        )}


        {currentPath === '/verify-face' && (
          <VerifyFacePage
            accessToken={currentUser?.accessToken}
            email={currentUser?.email}
            onVerificationSuccess={handleVerificationSuccess}
            onLogout={handleLogout}
            onGoToLogin={() => navigate('/login')}
          />
        )}

        {currentPath === '/dashboard' && (
          <DashboardPage
            email={currentUser?.email}
            onLogout={handleLogout}
          />
        )}
      </main>

      <footer className="footer">
        © 2026 FaceAuthSystem. Multi-factor biometric authentication.
      </footer>
    </div>
  )
}

export default App
