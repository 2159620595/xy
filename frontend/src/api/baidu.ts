import netdiskRequest from '@/utils/netdisk-request'

export const baiduApi = {
  getQr: () => netdiskRequest.get('/baidu/get_qr'),
  checkStatus: (sign: string) => netdiskRequest.get(`/baidu/check_status?sign=${encodeURIComponent(sign)}`),
  getAccounts: () => netdiskRequest.get('/account/assign'),
  deleteAccount: (id: number | string) => netdiskRequest.delete(`/account/${id}`),
  updateCookie: (id: number | string, data: Record<string, unknown>) =>
    netdiskRequest.put(`/account/${id}/update`, data),
  updateProxy: (id: number | string, proxy_url: string) =>
    netdiskRequest.put(`/account/${id}/update`, { proxy_url }),
  getDevices: (id: number | string) => netdiskRequest.get(`/account/${id}/devices`, { timeout: 30000 }),
  lockDevice: (accountId: number | string, deviceId: string) =>
    netdiskRequest.post(`/account/${accountId}/devices/${deviceId}/lock`),
  getCdKeys: () => netdiskRequest.get('/cdkey/list'),
  generateCdKeys: (accountId: number | string, count: number, days: number, maxUses = 0) =>
    netdiskRequest.post(
      `/cdkey/generate?account_id=${accountId}&count=${count}&days=${days}&max_uses=${maxUses}`,
    ),
  deleteCdKey: (id: number | string) => netdiskRequest.delete(`/cdkey/${id}`),
  cleanExpiredKeys: () => netdiskRequest.delete('/cdkey/clean_expired'),
  addByCookie: (cookie: string) => netdiskRequest.post('/account/add_by_cookie', { cookie }),
  getDeviceLogs: () => netdiskRequest.get('/device_logs', { timeout: 30000 }),
  getDeviceHistory: () => netdiskRequest.get('/device_history', { timeout: 30000 }),
}

export const authApi = {
  getLoginLogs: (params?: Record<string, unknown>) =>
    netdiskRequest.get('/auth/login-logs', {
      params,
    }),
}
