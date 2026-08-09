import { type FC } from 'react'
import { LoginForm } from '../components/LoginForm'

interface LoginPageProps {
  onLoginSuccess: (authData: { userId: string; email: string; accessToken: string; emailVerified?: boolean }) => void
  onSwitchToRegister: () => void
}


export const LoginPage: FC<LoginPageProps> = ({ onLoginSuccess, onSwitchToRegister }) => {
  return (
    <div className="login-flow-wrapper">
      <LoginForm
        onSuccess={onLoginSuccess}
        onSwitchToRegister={onSwitchToRegister}
      />
    </div>
  )
}
