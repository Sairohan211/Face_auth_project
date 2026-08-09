import { useState, type FC } from 'react'
import { RegisterForm } from '../components/RegisterForm'
import { VerifyEmailPage } from './VerifyEmailPage'
import { FaceCapture } from '../components/FaceCapture'
import { RegistrationSuccess } from '../components/RegistrationSuccess'

interface PendingUserData {
  userId: string
  email: string
  fullName: string
  accessToken?: string
}

interface AuthData {
  userId: string
  email: string
  fullName: string
  accessToken: string
}

interface RegisterPageProps {
  onSuccess?: (data: { userId: string; email: string; fullName: string; accessToken: string }) => void
  onSwitchToLogin?: () => void
}


export const RegisterPage: FC<RegisterPageProps> = ({ onSuccess, onSwitchToLogin }) => {
  const [currentStep, setCurrentStep] = useState<'account' | 'verify-email' | 'face' | 'success'>('account')
  const [pendingUser, setPendingUser] = useState<PendingUserData | null>(null)
  const [authData, setAuthData] = useState<AuthData | null>(null)

  const handleAccountCreated = (data: { userId: string; email: string; fullName: string; accessToken: string }) => {
    setPendingUser(data)
    if (onSuccess) {
      onSuccess(data)
    } else {
      setCurrentStep('verify-email')
    }
  }


  const handleEmailVerified = (verifiedData: AuthData) => {
    setAuthData(verifiedData)
    setCurrentStep('face')
  }

  const handleFaceRegistered = () => {
    setCurrentStep('success')
  }

  const handleCancelFace = () => {
    // Return to start of registration
    setCurrentStep('account')
  }

  return (
    <div className="registration-flow-wrapper">
      <div className="flow-content">
        {currentStep === 'account' && (
          <RegisterForm
            onSuccess={handleAccountCreated}
            onSwitchToLogin={onSwitchToLogin}
          />
        )}

        {currentStep === 'verify-email' && pendingUser && (
          <VerifyEmailPage
            email={pendingUser.email}
            fullName={pendingUser.fullName}
            userId={pendingUser.userId}
            onVerificationSuccess={handleEmailVerified}
            onBackToRegister={() => setCurrentStep('account')}
            onSwitchToLogin={onSwitchToLogin}
          />
        )}

        {currentStep === 'face' && authData && (
          <FaceCapture
            userId={authData.userId}
            fullName={authData.fullName}
            accessToken={authData.accessToken}
            onSuccess={handleFaceRegistered}
            onCancel={handleCancelFace}
          />
        )}

        {currentStep === 'success' && (
          <RegistrationSuccess
            onGoToLogin={onSwitchToLogin}
          />
        )}
      </div>
    </div>
  )
}
