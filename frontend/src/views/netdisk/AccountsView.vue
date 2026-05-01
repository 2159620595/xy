<template>
  <section class="netdisk-accounts">
    <el-card shadow="never">
      <template #header>
        <div class="netdisk-accounts__header">
          <div>
            <div class="netdisk-accounts__title">网盘账号池管理</div>
            <div class="netdisk-accounts__desc">管理百度网盘账号、Cookie、代理和设备信息</div>
          </div>
          <el-space wrap>
            <el-button :loading="loading" @click="loadAccounts">刷新列表</el-button>
            <el-button @click="handleExportAll">导出全部CK</el-button>
            <el-button @click="showCkAddModal = true">CK 添加账户</el-button>
            <el-button type="primary" @click="handleOpenQr">扫码添加账户</el-button>
          </el-space>
        </div>
      </template>

      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column label="账号名称" min-width="220">
          <template #default="{ row }">
            <div class="account-cell">
              <img
                v-if="row.avatar_url"
                :src="row.avatar_url"
                alt=""
                class="account-cell__avatar"
              />
              <div v-else class="account-cell__avatar account-cell__avatar--placeholder">
                {{ row.username?.[0] || '?' }}
              </div>
              <span>{{ row.username || '未命名账号' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '失效' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vip_level" label="会员等级" min-width="120" />
        <el-table-column label="绑定代理" width="130" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.proxy_url" type="info">已绑定代理</el-tag>
            <span v-else class="text-muted">无</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="360" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button size="small" text type="primary" @click="handleExportCookie(row)">
                导出CK
              </el-button>
              <el-button size="small" text type="warning" @click="handleOpenUpdateCookie(row)">
                更新/绑定代理
              </el-button>
              <el-button size="small" text type="primary" @click="handleOpenDevices(row)">
                设备管理
              </el-button>
              <el-button size="small" text type="danger" @click="confirmDelete(row)">
                删除
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="showQrModal"
      title="百度网盘官方扫码登录"
      width="360px"
      :close-on-click-modal="false"
      @closed="handleModalClose"
    >
      <div class="qr-dialog">
        <div v-loading="qrLoading" class="qr-dialog__body">
          <img
            v-if="currentQr"
            :src="currentQr"
            alt="登录二维码"
            class="qr-dialog__image"
            :class="{ 'is-scanned': isScanned }"
          />
          <el-empty v-else-if="!qrLoading" description="二维码生成失败" />
          <div v-if="isScanned" class="qr-dialog__overlay">已扫码，请在手机确认</div>
        </div>
        <div class="qr-dialog__tip">
          <p v-if="qrLoading">正在安全连接百度服务器...</p>
          <p v-else-if="isScanned" class="qr-dialog__tip--success">手机端等待确认中</p>
          <p v-else>请使用 <b>百度网盘 App</b> 扫码</p>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showCookieModal" title="更新账号信息" width="480px">
      <el-form label-position="top">
        <el-form-item label="Cookie 字符串">
          <div class="dialog-help">粘贴该账号的完整 Cookie 字符串，可留空表示不更新 Cookie</div>
          <el-input
            v-model="newCookie"
            type="textarea"
            placeholder="BDUSS=xxx; STOKEN=xxx; ..."
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </el-form-item>
        <el-form-item label="独立代理 IP">
          <div class="dialog-help">可选，格式示例：`http://user:pass@ip:port`</div>
          <el-input
            v-model="newProxy"
            placeholder="例如：http://abc:123@114.114.114.114:8888"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-space>
          <el-button @click="showCookieModal = false">取消</el-button>
          <el-button type="primary" :loading="cookieUpdating" @click="confirmUpdateCookie">
            确认保存
          </el-button>
        </el-space>
      </template>
    </el-dialog>

    <el-dialog v-model="showCkAddModal" title="通过 Cookie 添加账户" width="500px">
      <el-form label-position="top">
        <el-form-item label="百度 Cookie">
          <div class="dialog-help">必须包含 `BDUSS`，系统会自动识别账号信息</div>
          <el-input
            v-model="ckAddValue"
            type="textarea"
            placeholder="BDUSS=xxxxx; STOKEN=xxxxx; ..."
            :autosize="{ minRows: 4, maxRows: 8 }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-space>
          <el-button @click="showCkAddModal = false">取消</el-button>
          <el-button type="primary" :loading="ckAdding" @click="handleAddByCookie">
            确认添加
          </el-button>
        </el-space>
      </template>
    </el-dialog>

    <el-dialog v-model="showDeviceModal" title="设备管理" width="800px">
      <div v-loading="devicesLoading" class="device-dialog">
        <div v-if="devices.length > 0" class="device-grid">
          <div v-for="dev in devices" :key="dev.device_id" class="device-card">
            <div class="device-card__main">
              <div class="device-card__icon">
                <img :src="resolveDeviceIcon(dev)" alt="" @error="handleImageError" />
              </div>
              <div class="device-card__info">
                <div class="device-card__name">{{ dev.device_name || '未知设备' }}</div>
                <div class="device-card__meta">{{ dev.os || '未知系统' }}</div>
                <div class="device-card__meta">IP: {{ dev.ip || '未知' }}</div>
                <el-tag size="small" :type="dev.status === '在线' ? 'success' : 'danger'">
                  {{ dev.status }}
                </el-tag>
              </div>
            </div>

            <div class="device-card__aside">
              <div class="device-card__meta">未使用: {{ dev.unused_days || 0 }} 天</div>
              <div class="device-card__meta">
                时间: {{ formatDeviceTime(dev.last_used) }}
              </div>
              <div class="device-card__actions">
                <el-button
                  v-if="dev.is_current"
                  size="small"
                  type="success"
                  plain
                  disabled
                >
                  当前设备
                </el-button>
                <el-button
                  v-else-if="dev.status === '在线'"
                  size="small"
                  type="primary"
                  :loading="lockingDeviceId === dev.device_id"
                  @click="confirmLockDevice(dev.device_id)"
                >
                  锁定
                </el-button>
                <el-button v-else size="small" type="danger" plain disabled>
                  已锁定
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!devicesLoading" description="暂无设备数据或获取失败" />
      </div>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { baiduApi } from '@/api/baidu'

const loading = ref(false)
const qrLoading = ref(false)
const showQrModal = ref(false)
const currentQr = ref('')
const isScanned = ref(false)
const tableData = ref([])

const showCookieModal = ref(false)
const showCkAddModal = ref(false)
const ckAddValue = ref('')
const ckAdding = ref(false)
const newCookie = ref('')
const newProxy = ref('')
const cookieUpdating = ref(false)
const editingAccount = ref(null)

const showDeviceModal = ref(false)
const devicesLoading = ref(false)
const devices = ref([])
const currentDeviceAccountId = ref(null)
const lockingDeviceId = ref(null)

let pollingActive = false
let currentSign = ''

const DEVICE_ICON_MAP = [
  { match: (text) => text.includes('mac'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/mac.png' },
  { match: (text) => text.includes('android'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/android.png' },
  { match: (text) => text.includes('iphone'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/iphone.png' },
  { match: (text) => text.includes('ipad'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/ipad.png' },
  { match: (text) => text.includes('windows') || text.includes('edge'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/ie.png' },
  { match: (text) => text.includes('chrome'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png' },
  { match: (text) => text.includes('safari'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/safari.png' },
]

const extractErrorMessage = (error, fallback) =>
  error?.response?.data?.detail || error?.response?.data?.message || fallback

const fallbackCopy = (text) => {
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-999999px'
  textArea.style.top = '-999999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  document.execCommand('copy')
  document.body.removeChild(textArea)
}

const copyText = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  fallbackCopy(text)
}

const resolveDeviceIcon = (device) => {
  if (device.icon) return device.icon
  const text = `${device.os || ''} ${device.device_name || ''}`.toLowerCase()
  return DEVICE_ICON_MAP.find((candidate) => candidate.match(text))?.icon
    || 'https://ndstatic.cdn.bcebos.com/diskDevice/pc.png'
}

const handleImageError = (event) => {
  const target = event.target
  if (target instanceof HTMLImageElement) {
    target.style.display = 'none'
  }
}

const formatDeviceTime = (timestamp) => {
  if (!timestamp) return '未知'
  return new Date(timestamp * 1000).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
}

const handleExportAll = () => {
  if (!tableData.value.length) {
    ElMessage.warning('暂无账号数据')
    return
  }

  const lines = tableData.value
    .map((row, index) => `# 账号${index + 1}：${row.username}（${row.vip_level}）\n${row.cookie}`)
    .join('\n\n' + '-'.repeat(60) + '\n\n')

  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `全部账号Cookie_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.txt`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${tableData.value.length} 个账号的 Cookie`)
}

const loadAccounts = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getAccounts()
    tableData.value = res.data || []
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取账号列表失败'))
  } finally {
    loading.value = false
  }
}

const handleAddByCookie = async () => {
  if (!ckAddValue.value.trim()) {
    ElMessage.warning('请粘贴 Cookie 内容')
    return
  }

  ckAdding.value = true
  try {
    const res = await baiduApi.addByCookie(ckAddValue.value.trim())
    ElMessage.success(res.data.msg || '添加成功')
    showCkAddModal.value = false
    ckAddValue.value = ''
    await loadAccounts()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '添加失败，请检查 Cookie 是否有效'))
  } finally {
    ckAdding.value = false
  }
}

const confirmDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除账号「${row.username}」？`, '删除确认', {
      type: 'warning',
    })
    await handleDelete(row)
  } catch {
    // User cancelled.
  }
}

const handleDelete = async (row) => {
  try {
    await baiduApi.deleteAccount(row.id)
    ElMessage.success(`账号「${row.username}」已删除`)
    await loadAccounts()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '删除失败，请重试'))
  }
}

const handleExportCookie = async (row) => {
  if (!row.cookie) {
    ElMessage.warning('该账号暂无 Cookie')
    return
  }

  const lines = [
    `账号：${row.username}`,
    `会员等级：${row.vip_level}`,
    `状态：${row.status === 1 ? '正常' : '失效'}`,
    '',
    'Cookie：',
    row.cookie,
  ].join('\n')

  try {
    await copyText(row.cookie)
    ElMessage.success(`已复制「${row.username}」的 Cookie`)
  } catch {
    ElMessage.warning('复制失败，已继续下载文件')
  }

  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${row.username}_cookie.txt`
  link.click()
  URL.revokeObjectURL(url)
}

const handleOpenUpdateCookie = (row) => {
  editingAccount.value = row
  newCookie.value = ''
  newProxy.value = row.proxy_url || ''
  showCookieModal.value = true
}

const confirmUpdateCookie = async () => {
  if (!editingAccount.value) return

  const cookieStr = newCookie.value.trim()
  const proxyStr = newProxy.value.trim()

  if (!cookieStr && proxyStr === (editingAccount.value.proxy_url || '')) {
    ElMessage.warning('没有任何更改')
    return
  }

  cookieUpdating.value = true
  try {
    const payload = {}
    if (cookieStr) payload.cookie = cookieStr
    if (proxyStr !== (editingAccount.value.proxy_url || '')) {
      payload.proxy_url = proxyStr
    }

    await baiduApi.updateCookie(editingAccount.value.id, payload)
    ElMessage.success(`账号「${editingAccount.value.username}」信息已保存`)
    showCookieModal.value = false
    await loadAccounts()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存失败，请重试'))
  } finally {
    cookieUpdating.value = false
  }
}

const handleOpenDevices = async (row) => {
  currentDeviceAccountId.value = row.id
  showDeviceModal.value = true
  devicesLoading.value = true
  devices.value = []

  try {
    const res = await baiduApi.getDevices(row.id)
    devices.value = res.data || []
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取设备列表失败'))
    showDeviceModal.value = false
  } finally {
    devicesLoading.value = false
  }
}

const handleLockDevice = async (deviceId) => {
  if (!currentDeviceAccountId.value) return

  lockingDeviceId.value = deviceId
  try {
    await baiduApi.lockDevice(currentDeviceAccountId.value, deviceId)
    ElMessage.success('设备已成功踢出/锁定')
    const res = await baiduApi.getDevices(currentDeviceAccountId.value)
    devices.value = res.data || []
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '锁定失败，请重试'))
  } finally {
    lockingDeviceId.value = null
  }
}

const confirmLockDevice = async (deviceId) => {
  try {
    await ElMessageBox.confirm('确认要强制踢出该设备吗？', '锁定确认', {
      type: 'warning',
    })
    await handleLockDevice(deviceId)
  } catch {
    // User cancelled.
  }
}

const handleOpenQr = async () => {
  currentQr.value = ''
  isScanned.value = false
  qrLoading.value = true
  showQrModal.value = true

  try {
    const { data } = await baiduApi.getQr()
    currentSign = data.sign
    currentQr.value = data.imgurl || ''
    qrLoading.value = !currentQr.value
    pollingActive = true
    performPolling()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '初始化百度安全通道失败'))
    showQrModal.value = false
  }
}

const performPolling = async () => {
  if (!pollingActive || !currentSign) return

  try {
    const { data } = await baiduApi.checkStatus(currentSign)
    if (data.status === 'ready') {
      if (data.sign) currentSign = data.sign
      currentQr.value = data.imgurl || currentQr.value
      qrLoading.value = !currentQr.value
      setTimeout(performPolling, 1200)
      return
    }

    if (data.status === 'success') {
      ElMessage.success(`欢迎回来，${data.username}！`)
      showQrModal.value = false
      await loadAccounts()
      return
    }

    if (data.status === 'pending') {
      qrLoading.value = !currentQr.value
      setTimeout(performPolling, currentQr.value ? 2000 : 1200)
      return
    }

    if (data.status === 'scanned') {
      isScanned.value = true
    } else if (data.status === 'failed') {
      ElMessage.warning(data.msg || '登录失败，请重试')
      showQrModal.value = false
      return
    }

    setTimeout(performPolling, 2000)
  } catch {
    setTimeout(performPolling, 5000)
  }
}

const handleModalClose = () => {
  pollingActive = false
  currentSign = ''
  isScanned.value = false
}

onMounted(loadAccounts)
onUnmounted(() => {
  pollingActive = false
})
</script>

<style scoped>
.netdisk-accounts {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
}

.netdisk-accounts__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.netdisk-accounts__title {
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.netdisk-accounts__desc,
.text-muted,
.dialog-help,
.device-card__meta {
  color: #909399;
  font-size: 13px;
}

.account-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-cell__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.account-cell__avatar--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e5e7eb;
  color: #606266;
  font-size: 13px;
}

.qr-dialog {
  text-align: center;
}

.qr-dialog__body {
  position: relative;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-dialog__image {
  width: 220px;
  height: 220px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.qr-dialog__image.is-scanned {
  opacity: 0.3;
}

.qr-dialog__overlay {
  position: absolute;
  color: #67c23a;
  font-weight: 600;
}

.qr-dialog__tip {
  margin-top: 16px;
  color: #606266;
  font-size: 14px;
}

.qr-dialog__tip--success {
  color: #67c23a;
}

.device-dialog {
  min-height: 200px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.device-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  transition: box-shadow 0.2s ease;
}

.device-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.device-card__main {
  display: flex;
  gap: 12px;
  flex: 1;
}

.device-card__icon {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 50%;
  overflow: hidden;
  background: #f5f7fa;
  flex-shrink: 0;
}

.device-card__icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.device-card__info,
.device-card__aside {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.device-card__name {
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.device-card__aside {
  min-width: 140px;
  align-items: flex-end;
  text-align: right;
}

.device-card__actions {
  margin-top: 8px;
}

@media (max-width: 960px) {
  .netdisk-accounts__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .device-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .device-card {
    flex-direction: column;
  }

  .device-card__aside {
    min-width: 0;
    align-items: flex-start;
    text-align: left;
  }
}
</style>
