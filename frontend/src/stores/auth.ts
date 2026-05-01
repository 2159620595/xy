import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { User } from '@/types'
import {
  clearJudianSessionStorage,
  getMainToken,
  readStoredJson,
} from '@/utils/session'
const readStoredUser = () => readStoredJson<User>('user_info')

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getMainToken() || null)
  const user = ref<User | null>(readStoredUser())
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))

  const setAuth = (nextToken: string, nextUser: User) => {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem('auth_token', nextToken)
    localStorage.setItem('user_info', JSON.stringify(nextUser))
    initialized.value = true
  }

  const clearSession = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    initialized.value = true
  }

  const clearAuth = () => {
    clearSession()
    clearJudianSessionStorage()
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
