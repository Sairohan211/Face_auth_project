import { useEffect, type FC } from 'react'
import { LoginForm } from '../components/LoginForm'
import { warmupServer } from '../lib/api'

interface LoginPageProps {
  onLoginSuccess: (authData: { userId: string; email: string; accessToken: string; emailVerified?: boolean }) => void
  onSwitchToRegister: () => void
}


export const LoginPage: FC<LoginPageProps> = ({ onLoginSuccess, onSwitchToRegister }) => {
  useEffect(() => {
    warmupServer()
  }, [])

  return (
    <div className="login-flow-wrapper">
      <LoginForm
        onSuccess={onLoginSuccess}
        onSwitchToRegister={onSwitchToRegister}
      />
    </div>
  )
}
