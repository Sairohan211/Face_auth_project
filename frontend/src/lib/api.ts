/**
 * API client helper for FaceAuthSystem backend endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export interface RegisterPayload {
  full_name: string
  email: string
  password: string
}

export interface RegisterResponse {
  success: boolean
  message: string
  user_id: string
  email?: string
}

export interface VerifyEmailPayload {
  email: string
  otp: string
}

export interface VerifyEmailResponse {
  success: boolean
  message: string
}

export interface ResendOtpPayload {
  email: string
}

export interface ResendOtpResponse {
  success: boolean
  message: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface SessionInfo {
  access_token: string
  token_type: string
  expires_in?: number
  expires_at?: number
  refresh_token?: string
}

export interface UserProfile {
  id: string
  full_name: string
  email: string
  email_verified: boolean
  created_at: string
}

export interface LoginResponse {
  success: boolean
  message: string
  user_id: string
  access_token: string
  token_type: string
  expires_in?: number
  refresh_token?: string
  email_verified?: boolean
  session?: SessionInfo
}


export interface FaceRegisterResponse {
  success: boolean
  message: string
}

export interface FaceVerifyResponse {
  success: boolean
  verified: boolean
  match_score: number
  similarity: number
  message: string
}


/**
 * Calls backend POST /api/auth/register
 */
export async function registerAccount(payload: RegisterPayload): Promise<RegisterResponse> {
  const url = `${API_BASE_URL}/api/auth/register`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    let errorDetail = data?.detail || data?.message || 'Registration failed. Please try again.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as RegisterResponse
}

/**
 * Calls backend POST /api/auth/verify-email
 */
export async function verifyEmailApi(payload: VerifyEmailPayload): Promise<VerifyEmailResponse> {
  const url = `${API_BASE_URL}/api/auth/verify-email`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    let errorDetail = data?.detail || data?.message || 'Invalid or expired verification code.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as VerifyEmailResponse
}

/**
 * Calls backend POST /api/auth/resend-otp
 */
export async function resendOtpApi(payload: ResendOtpPayload): Promise<ResendOtpResponse> {
  const url = `${API_BASE_URL}/api/auth/resend-otp`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    let errorDetail = data?.detail || data?.message || 'Could not resend verification code.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as ResendOtpResponse
}

/**
 * Calls backend POST /api/auth/login
 */
export async function loginAccount(payload: LoginPayload): Promise<LoginResponse> {
  const url = `${API_BASE_URL}/api/auth/login`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Invalid email or password.')
    }
    let errorDetail = data?.detail || data?.message || 'Login failed. Please try again.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as LoginResponse
}

/**
 * Calls protected backend POST /api/face/register with multipart/form-data
 */
export async function registerFace(imageBlob: Blob, accessToken: string): Promise<FaceRegisterResponse> {
  const url = `${API_BASE_URL}/api/face/register`
  const formData = new FormData()
  formData.append('file', imageBlob, 'face_capture.jpg')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Please verify your email before registering your face.')
    }
    let errorDetail = data?.detail || data?.message || 'Face registration failed.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as FaceRegisterResponse
}

/**
 * Calls protected backend POST /api/face/verify with multipart/form-data
 */
export async function verifyFace(imageBlob: Blob, accessToken: string): Promise<FaceVerifyResponse> {
  const url = `${API_BASE_URL}/api/face/verify`
  const formData = new FormData()
  formData.append('file', imageBlob, 'verify_capture.jpg')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized: Authentication session has expired. Please sign in again.')
    }
    let errorDetail = data?.detail || data?.message || 'Face verification failed.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as FaceVerifyResponse
}

/**
 * Calls protected backend GET /api/auth/me to retrieve full user profile
 */
export async function getMyProfile(accessToken: string): Promise<UserProfile> {
  const url = `${API_BASE_URL}/api/auth/me`
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    let errorDetail = data?.detail || data?.message || 'Failed to retrieve profile.'
    if (Array.isArray(errorDetail)) {
      errorDetail = errorDetail.map((d: any) => d?.msg || JSON.stringify(d)).join(', ')
    }
    throw new Error(errorDetail)
  }

  return data as UserProfile
}

