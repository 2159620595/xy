import axios, { type AxiosInstance } from 'axios'

const SESSION_REUSE_WINDOW_MS = 2 * 60 * 1000

const normalizeBase = (value: string | undefined, fallback: string) => {
  const text = String(value || fallback || '').trim().replace(/\/+$/, '')
  return text || fallback
}

const NETDISK_API_BASE = normalizeBase(import.meta.env.VITE_NETDISK_API_BASE, '/netdisk_api/api')

let bootstrapPromise: Promise<boolean> | null = null
let trustedAt = 0

const readMainUser = () => {
  const raw = localStorage.getItem('user_info')
  if (!raw) return null
  try {
    return JSON.parse(raw) as { username?: string; role?: string }
  } catch {
    return null
  }
}

const redirectToLogin = () => {
  if (typeof window === 'undefined' || window.location.pathname.startsWith('/login')) return
  const redirect = `${window.location.pathname}${window.location.search || ''}`
  window.location.replace(`/login?redirect=${encodeURIComponent(redirect)}`)
}

export const ensureNetdiskSession = async (force = false) => {
  if (!force && Date.now() - trustedAt < SESSION_REUSE_WINDOW_MS) {
    return true
  }
  if (bootstrapPromise) return bootstrapPromise

  bootstrapPromise = (async () => {
    const mainUser = readMainUser()
    if (!mainUser?.username) return false

    try {
      const response = await axios.post(
        `${NETDISK_API_BASE}/netdisk/session`,
        {
          username: mainUser.username,
          role: mainUser.role || 'admin',
        },
        {
          withCredentials: true,
        },
      )
      if (response.data?.success) {
        trustedAt = Date.now()
        return true
      }
      return false
    } catch (error: any) {
      if (error?.response?.status === 401) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_info')
        redirectToLogin()
      }
      return false
    }
  })()

  try {
    return await bootstrapPromise
  } finally {
    bootstrapPromise = null
  }
}

const buildAdminClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: NETDISK_API_BASE,
    timeout: 30000,
    withCredentials: true,
  })

  client.interceptors.request.use(async (config) => {
    await ensureNetdiskSession()
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalConfig = error?.config
      if (error?.response?.status === 401 && originalConfig && !originalConfig.__netdiskRetried) {
        originalConfig.__netdiskRetried = true
        const synced = await ensureNetdiskSession(true)
        if (synced) {
          return client(originalConfig)
        }
      }

      if (error?.response?.status === 401) {
        redirectToLogin()
      }
      return Promise.reject(error)
    },
  )

  return client
}

export const netdiskRequest = buildAdminClient()

export const netdiskPublicRequest = axios.create({
  baseURL: NETDISK_API_BASE,
  timeout: 30000,
  withCredentials: true,
})

export default netdiskRequest
