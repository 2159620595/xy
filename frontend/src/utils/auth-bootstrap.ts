import { verifyToken } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

let bootstrapPromise: Promise<void> | null = null

export const initializeAuth = async () => {
  const authStore = useAuthStore()

  if (authStore.initialized) {
    return
  }

  if (bootstrapPromise) {
    return bootstrapPromise
  }

  bootstrapPromise = (async () => {
    if (!authStore.token) {
      authStore.clearSession()
      return
    }

    try {
      const result = await verifyToken()
      if (result.authenticated && result.user_id && result.username !== undefined) {
        authStore.setAuth(authStore.token, {
          user_id: result.user_id,
          username: result.username,
          is_admin: Boolean(result.is_admin),
        })
        return
      }
    } catch {
      // Let the store fall back to a signed-out state when verification fails.
    }

    authStore.clearSession()
  })()

  try {
    await bootstrapPromise
  } finally {
    bootstrapPromise = null
    authStore.markInitialized()
  }
}
