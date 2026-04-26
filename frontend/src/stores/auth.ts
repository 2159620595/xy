import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { User } from '@/types'

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'user_info'

const readStoredUser = () => {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as User
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(readStoredUser())
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))

  const setAuth = (nextToken: string, nextUser: User) => {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
    initialized.value = true
  }

  const clearSession = () => {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    initialized.value = true
  }

  const clearAuth = () => {
    clearSession()
    localStorage.removeItem('judian_auth_token')
    localStorage.removeItem('judian_user_info')
  }

  const markInitialized = () => {
    initialized.value = true
  }

  return {
    token,
    user,
    initialized,
    isAuthenticated,
    setAuth,
    clearSession,
    clearAuth,
    markInitialized,
  }
})
