import { get, post } from '@/utils/request'
import type { ApiResponse, LoginRequest, LoginResponse, RegisterRequest } from '@/types'

export const login = (data: LoginRequest): Promise<LoginResponse> => {
  return post('/login', data)
}

export const verifyToken = (): Promise<{
  authenticated: boolean
  user_id?: number
  username?: string
  is_admin?: boolean
}> => {
  return get('/verify')
}

export const getRegistrationStatus = async (): Promise<{ enabled: boolean }> => {
  try {
    const settings = await get<Record<string, unknown>>('/system-settings/public')
    const value = settings.registration_enabled
    return { enabled: value === true || value === 'true' || value === 1 || value === '1' }
  } catch {
    return { enabled: true }
  }
}

export const getLoginInfoStatus = async (): Promise<{ enabled: boolean }> => {
  try {
    const settings = await get<Record<string, unknown>>('/system-settings/public')
    const value = settings.show_default_login_info
    return { enabled: value === true || value === 'true' || value === 1 || value === '1' }
  } catch {
    return { enabled: true }
  }
}

export const generateCaptcha = (sessionId: string): Promise<{ success: boolean; captcha_image?: string }> => {
  return post('/generate-captcha', { session_id: sessionId })
}

export const verifyCaptcha = (sessionId: string, captchaCode: string): Promise<{ success: boolean }> => {
  return post('/verify-captcha', { session_id: sessionId, captcha_code: captchaCode })
}

export const sendVerificationCode = (
  email: string,
  type: string,
  sessionId: string,
): Promise<ApiResponse> => {
  return post('/send-verification-code', { email, type, session_id: sessionId })
}

export const register = (data: RegisterRequest): Promise<ApiResponse> => {
  return post('/register', data)
}
