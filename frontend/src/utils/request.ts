import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/auth'

const request = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

request.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      try {
        useAuthStore().clearAuth()
      } catch {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_info')
      }
    }
    return Promise.reject(error)
  },
)

export const get = async <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  const response = await request.get<T>(url, config)
  return response.data
}

export const post = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.post<T>(url, data, config)
  return response.data
}

export const put = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.put<T>(url, data, config)
  return response.data
}

export const del = async <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  const response = await request.delete<T>(url, config)
  return response.data
}

export default request
