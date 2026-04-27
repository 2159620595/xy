import { buildApiUrl, del, get, post } from '@/utils/request'
import type { AdminStats, ApiResponse, User } from '@/types'

interface BackendUser {
  id: number
  username: string
  email?: string
  is_admin: boolean
  cookie_count?: number
  card_count?: number
}

export interface SystemLog {
  id: string
  level: 'info' | 'warning' | 'error'
  message: string
  module: string
  created_at: string
}

export interface RiskLog {
  id: string
  cookie_id: string
  risk_type: string
  message: string
  processing_result: string
  processing_status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface TableData {
  success: boolean
  data: Record<string, unknown>[]
  columns: string[]
  count: number
}

export interface LogFileInfo {
  name: string
  size: number
  modified_at: string
  modified_ts: number
}

export interface BackupFileInfo {
  filename: string
  size: number
  size_mb: number
  created_time: string
  modified_time: string
}

const normalizeLogLevel = (rawLevel?: string): SystemLog['level'] => {
  if (rawLevel === 'ERROR') return 'error'
  if (rawLevel === 'WARNING') return 'warning'
  return 'info'
}

const systemLogPattern =
  /^(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?)\s+\|\s+([A-Z]+)\s+\|\s+(.+?)\s+-\s+([\s\S]+)$/

const extractBracketModule = (message: string): string | null => {
  const match = message.trim().match(/^\[([^\]]+)\]/)
  return match?.[1]?.trim() || null
}

const normalizeModuleName = (rawSource?: string, rawMessage = ''): string => {
  const bracketModule = extractBracketModule(rawMessage)
  if (bracketModule) return bracketModule

  const source = String(rawSource || '').trim()
  if (!source) return 'system'

  const sourceName = source.split(':')[0]?.trim() || 'system'
  if (sourceName.endsWith('.__init__')) {
    return sourceName.slice(0, -'.__init__'.length) || 'system'
  }
  return sourceName
}

const parseSystemLogLine = (line: string, index: number): SystemLog => {
  const trimmed = line.trim()
  const match = trimmed.match(systemLogPattern)

  if (!match) {
    return {
      id: String(index),
      level: normalizeLogLevel(
        trimmed.includes('| ERROR |')
          ? 'ERROR'
          : trimmed.includes('| WARNING |')
            ? 'WARNING'
            : 'INFO',
      ),
      message: trimmed,
      module: normalizeModuleName('', trimmed),
      created_at: '',
    }
  }

  const [, timestamp, level, source, message] = match

  return {
    id: `${timestamp}-${index}`,
    level: normalizeLogLevel(level),
    message: message.trim(),
    module: normalizeModuleName(source, message),
    created_at: timestamp.trim(),
  }
}

export const getUsers = async (): Promise<{ success: boolean; data?: User[] }> => {
  const result = await get<{ users: BackendUser[] }>('/admin/users')
  return {
    success: true,
    data: (result.users || []).map((user) => ({
      user_id: user.id,
      username: user.username,
      email: user.email,
      is_admin: user.is_admin,
      cookie_count: user.cookie_count,
      card_count: user.card_count,
    })),
  }
}

export const deleteUser = (userId: number): Promise<ApiResponse> => {
  return del(`/admin/users/${userId}`)
}

export const getSystemLogs = async (params?: {
  page?: number
  limit?: number
  level?: string
}): Promise<{ success: boolean; data?: SystemLog[]; total?: number }> => {
  const query = new URLSearchParams()
  if (params?.page) query.set('page', String(params.page))
  if (params?.limit) query.set('lines', String(params.limit))
  if (params?.level) query.set('level', params.level.toUpperCase())

  const result = await get<{ logs?: string[]; total_lines?: number }>(
    `/admin/logs?${query.toString()}`,
  )

  return {
    success: true,
    data: (result.logs || []).map((log, index) => parseSystemLogLine(log, index)),
    total: result.total_lines,
  }
}

export const clearSystemLogs = (): Promise<ApiResponse> => {
  return post('/logs/clear')
}

export const getRiskLogs = async (params?: {
  page?: number
  limit?: number
  cookie_id?: string
}): Promise<{ success: boolean; data?: RiskLog[]; total?: number }> => {
  const query = new URLSearchParams()
  if (params?.page) query.set('page', String(params.page))
  if (params?.limit) query.set('limit', String(params.limit))
  if (params?.cookie_id) query.set('cookie_id', params.cookie_id)

  const result = await get<{
    success: boolean
    data?: Array<{
      id: number
      cookie_id: string
      event_type: string
      event_description: string
      processing_result: string
      processing_status: string
      error_message: string | null
      created_at: string
      updated_at: string
      cookie_name: string
    }>
    total?: number
  }>(`/admin/risk-control-logs?${query.toString()}`)

  return {
    success: true,
    data: (result.data || []).map((item) => ({
      id: String(item.id),
      cookie_id: item.cookie_id || item.cookie_name,
      risk_type: item.event_type,
      message: item.event_description || '',
      processing_result: item.processing_result || '',
      processing_status: item.processing_status || '',
      error_message: item.error_message,
      created_at: item.created_at,
      updated_at: item.updated_at || '',
    })),
    total: result.total,
  }
}

export const clearRiskLogs = async (cookieId?: string): Promise<ApiResponse> => {
  const query = cookieId ? `?cookie_id=${encodeURIComponent(cookieId)}` : ''
  return del(`/admin/risk-control-logs${query}`)
}

export const getTableData = async (tableName: string): Promise<TableData> => {
  return get<TableData>(`/admin/data/${tableName}`)
}

export const clearTableData = (tableName: string): Promise<ApiResponse> => {
  return del(`/admin/data/${tableName}`)
}

export const deleteTableRecord = (
  tableName: string,
  recordId: string,
): Promise<ApiResponse> => {
  return del(`/admin/data/${tableName}/${recordId}`)
}

export const reloadSystemCache = (): Promise<ApiResponse> => {
  return post('/admin/reload-cache')
}

export const getBackupFiles = (): Promise<{
  backups: BackupFileInfo[]
  total: number
}> => {
  return get('/admin/backup/list')
}

export const uploadDatabaseBackup = async (
  file: File,
): Promise<ApiResponse & { backup_file?: string; user_count?: number }> => {
  const formData = new FormData()
  formData.append('backup_file', file)
  return post('/admin/backup/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getLogFiles = async (): Promise<{
  success: boolean
  files: LogFileInfo[]
}> => {
  return get('/admin/log-files')
}

export const exportLogs = async (): Promise<{ blob: Blob; filename: string }> => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    throw new Error('未登录')
  }

  const list = await getLogFiles()
  const latest = list.files?.[0]
  if (!latest?.name) {
    throw new Error('暂无日志文件')
  }

  const response = await fetch(
    buildApiUrl(`/admin/logs/export?file=${encodeURIComponent(latest.name)}`),
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!response.ok) {
    throw new Error('导出失败')
  }

  return {
    blob: await response.blob(),
    filename: latest.name,
  }
}

export const getAdminStats = async (): Promise<{
  success: boolean
  data?: AdminStats
}> => {
  try {
    const data = await get<AdminStats>('/admin/stats')
    return { success: true, data }
  } catch {
    return { success: false }
  }
}
