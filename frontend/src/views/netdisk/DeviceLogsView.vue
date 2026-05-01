<template>
  <div class="device-logs-shell">
    <div class="device-logs-panel">
      <div class="device-type-tabs">
        <button
          v-for="item in deviceTypeTabs"
          :key="item.value"
          type="button"
          class="device-type-tabs__item"
          :class="{ 'is-active': activeDeviceType === item.value }"
          @click="activeDeviceType = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="device-logs-intro">
        <span class="device-logs-intro__title">功能介绍：</span>
        <div>
          【退出登录】该设备会退出当前账号登录状态，需要重新输入账号密码登录。<br />
          【锁定】网页端设备仅可被锁定，锁定后无法进行任何操作，可以短信验证码方式解锁。
        </div>
      </div>

      <div v-if="activeTab === 'devices'" class="device-toolbar">
        <el-space wrap>
          <el-select v-model="filterAccount" clearable placeholder="筛选账号" style="width: 160px">
            <el-option v-for="item in accountOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filterStatus" clearable placeholder="筛选状态" style="width: 130px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filterUnused" clearable placeholder="闲置时间" style="width: 120px">
            <el-option v-for="item in unusedOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :loading="loading" @click="loadLogs">刷新</el-button>
        </el-space>

        <el-button
          v-if="kickableDevices.length > 0"
          type="primary"
          :loading="batchKicking"
          @click="confirmBatchKick"
        >
          一键踢出匹配设备 ({{ kickableDevices.length }})
        </el-button>
      </div>

      <div v-else class="device-toolbar">
        <el-space wrap>
          <el-select v-model="filterAccount" clearable placeholder="筛选账号" style="width: 160px">
            <el-option v-for="item in accountOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :loading="loadingHistory" @click="loadHistory">刷新</el-button>
        </el-space>
      </div>

      <div
        v-loading="activeTab === 'devices' ? loading : loadingHistory"
        class="device-logs-content"
      >
        <div v-if="activeTab === 'devices'">
          <template v-if="filteredTableData.length > 0">
            <div class="device-logs-title">已登录设备 ({{ filteredTableData.length }})</div>
            <div class="device-card-grid">
              <div
                v-for="log in filteredTableData"
                :key="log.id"
                class="device-card"
              >
                <div class="device-card__main">
                  <div class="device-card__icon">
                    <img
                      :src="resolveDeviceIcon(log)"
                      alt=""
                      @error="handleImageError"
                    />
                  </div>
                  <div class="device-card__info">
                    <div class="device-card__name">{{ log.device_name || '未知设备' }}</div>
                    <div class="device-card__meta">
                      <span>{{ log.location || '未知端' }}</span>
                      <span v-if="log.account_name" class="device-card__badge">
                        {{ log.account_name }}
                      </span>
                      <el-tooltip
                        :content="buildDeviceTooltip(log)"
                        placement="top"
                      >
                        <span
                          v-if="log.unused_days > 0"
                          class="device-card__unused"
                        >
                          (闲置{{ log.unused_days }}天)
                        </span>
                        <el-icon v-else class="device-card__help-icon">
                          <InfoFilled />
                        </el-icon>
                      </el-tooltip>
                    </div>
                  </div>
                </div>
                <div class="device-card__actions">
                  <template v-if="log.action === '当前使用设备' || log.is_current">
                    <span class="device-card__status-text">本机</span>
                  </template>
                  <el-button
                    v-else-if="log.button"
                    size="small"
                    type="primary"
                    :loading="lockingId === log.id"
                    @click="confirmLockDevice(log)"
                  >
                    {{ log.button }}
                  </el-button>
                  <span v-else class="device-card__status-text">{{ log.status }}</span>
                </div>
              </div>
            </div>
          </template>
          <el-empty
            v-else-if="!loading"
            description="暂无匹配设备"
          />
        </div>

        <div v-else>
          <template v-if="filteredHistoryData.length > 0">
            <div class="device-history-tip">显示所有账号最近6个月的使用记录</div>
            <div v-for="group in groupedHistoryData" :key="group.date" class="device-history-group">
              <div class="device-history-group__title">{{ group.date }}</div>
              <div class="device-history-list">
                <div v-for="log in group.items" :key="log.id" class="device-history-item">
                  <div class="device-history-item__main">
                    <div class="device-history-item__icon">
                      <img :src="resolveDeviceIcon(log)" alt="" @error="handleImageError" />
                    </div>
                    <div>
                      <div class="device-history-item__name">
                        {{ log.device_name || '未知设备' }}
                        <span v-if="log.account_name" class="device-history-item__badge">
                          {{ log.account_name }}
                        </span>
                      </div>
                      <div class="device-history-item__meta">{{ log.location || '未知端' }}</div>
                      <div class="device-history-item__meta">({{ log.ip_address }})</div>
                    </div>
                  </div>
                  <div class="device-history-item__time">{{ formatTime(log.created_at) }}</div>
                </div>
              </div>
            </div>
          </template>
          <el-empty
            v-else-if="!loadingHistory"
            description="暂无使用记录"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { baiduApi } from '@/api/baidu'

const route = useRoute()
const loading = ref(false)
const tableData = ref([])
const lockingId = ref(null)

const activeTab = ref(route.name === 'DeviceHistory' ? 'history' : 'devices')
const activeDeviceType = ref('client')

const historyData = ref([])
const loadingHistory = ref(false)

const filterAccount = ref(null)
const filterStatus = ref(null)
const filterUnused = ref(null)
const deviceTypeTabs = [
  { label: '客户端设备', value: 'client' },
  { label: '网页版设备', value: 'web' },
  { label: '智能端设备', value: 'smart' },
]

// Watch route to sync activeTab
watch(() => route.name, (newName) => {
  if (newName === 'DeviceHistory') {
    activeTab.value = 'history'
    if (historyData.value.length === 0) {
      loadHistory()
    }
  } else if (newName === 'DeviceLog') {
    activeTab.value = 'devices'
  }
})

const getDeviceCategory = (item) => {
  const loc = (item.location || '').toLowerCase()
  const name = (item.device_name || '').toLowerCase()
  const combined = loc + ' ' + name
  
  if (combined.includes('chrome') || combined.includes('firefox') || combined.includes('safari') || combined.includes('edge') || combined.includes('ie') || combined.includes('web') || combined.includes('网页') || combined.includes('浏览器')) {
    return 'web'
  }
  if (combined.includes('tv') || combined.includes('speaker') || combined.includes('智能') || combined.includes('电视') || combined.includes('音箱') || combined.includes('watch') || combined.includes('手表') || combined.includes('car') || combined.includes('车载')) {
    return 'smart'
  }
  return 'client'
}

const accountOptions = computed(() => {
  const source = activeTab.value === 'devices' ? tableData.value : historyData.value
  const accounts = new Set(source.map(item => item.account_name).filter(Boolean))
  return Array.from(accounts).map(name => ({ label: name, value: name }))
})

const statusOptions = [
  { label: '在线 (包含下线锁定等状态)', value: '在线' },
  { label: '当前设备', value: '当前使用设备' }
]

const unusedOptions = [
  { label: '未使用 ≥ 1天', value: 1 },
  { label: '未使用 ≥ 3天', value: 3 },
  { label: '未使用 ≥ 7天', value: 7 },
  { label: '未使用 ≥ 30天', value: 30 }
]

const getUnusedDays = (item) => {
  if (item.unused_days !== undefined) {
    return item.unused_days;
  }
  if (item.error_msg && item.error_msg.includes('天未用')) {
    return parseInt(item.error_msg) || 0;
  }
  return 0;
}

const filteredTableData = computed(() => {
  return tableData.value.filter(item => {
    if (getDeviceCategory(item) !== activeDeviceType.value) return false
    
    if (filterAccount.value && item.account_name !== filterAccount.value) return false
    if (filterStatus.value) {
      if (filterStatus.value === '在线') {
        if (item.action === '当前使用设备' || item.is_current) return false;
      } else if (filterStatus.value === '当前使用设备') {
        if (item.action !== '当前使用设备' && !item.is_current) return false;
      } else if (item.status !== filterStatus.value) {
        return false
      }
    }
    if (filterUnused.value !== null) {
      const unused = getUnusedDays(item);
      if (unused < filterUnused.value) return false;
    }
    return true
  })
})

const filteredHistoryData = computed(() => {
  return historyData.value.filter(item => {
    if (getDeviceCategory(item) !== activeDeviceType.value) return false
    
    if (filterAccount.value && item.account_name !== filterAccount.value) return false
    return true
  })
})

const groupedHistoryData = computed(() => {
  const groups = {}
  
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterdayStart = todayStart - 86400000
  
  filteredHistoryData.value.forEach(log => {
    const logTime = log.created_at * 1000
    let groupKey = ''
    
    if (logTime >= todayStart) {
      groupKey = '今天'
    } else if (logTime >= yesterdayStart) {
      groupKey = '昨天'
    } else {
      const d = new Date(logTime)
      groupKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    }
    
    if (!groups[groupKey]) {
      groups[groupKey] = []
    }
    groups[groupKey].push(log)
  })
  
  return Object.keys(groups).map(key => {
    return {
      date: key,
      items: groups[key]
    }
  }).sort((a, b) => {
    if (a.date === '今天') return -1
    if (b.date === '今天') return 1
    if (a.date === '昨天') return -1
    if (b.date === '昨天') return 1
    return b.date.localeCompare(a.date)
  })
})

const formatTime = (timestamp) => {
  const d = new Date(timestamp * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const DEVICE_ICON_MAP = [
  { match: (text) => text.includes('mac'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/mac.png' },
  { match: (text) => text.includes('android'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/android.png' },
  { match: (text) => text.includes('iphone'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/iphone.png' },
  { match: (text) => text.includes('ipad'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/ipad.png' },
  { match: (text) => text.includes('windows') || text.includes('edge'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/ie.png' },
  { match: (text) => text.includes('chrome'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png' },
  { match: (text) => text.includes('firefox'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/firefox.png' },
  { match: (text) => text.includes('safari'), icon: 'https://ndstatic.cdn.bcebos.com/diskDevice/safari.png' },
]

const resolveDeviceIcon = (item) => {
  if (item.icon) return item.icon
  const text = `${item.location || ''} ${item.device_name || ''} ${item.os || ''}`.toLowerCase()
  return DEVICE_ICON_MAP.find((candidate) => candidate.match(text))?.icon
    || 'https://ndstatic.cdn.bcebos.com/diskDevice/pc.png'
}

const handleImageError = (event) => {
  const target = event.target
  if (target instanceof HTMLImageElement) {
    target.style.display = 'none'
  }
}

const buildDeviceTooltip = (item) =>
  `IP: ${item.ip_address || '未知'} | 最近使用: ${
    item.created_at
      ? new Date(item.created_at * 1000).toLocaleString('zh-CN', { hour12: false })
      : '未知'
  }`

const kickableDevices = computed(() => {
  return filteredTableData.value.filter(item => item.button && item.account_id && item.device_id && !item.is_current)
})

const batchKicking = ref(false)
const handleBatchKick = async () => {
  batchKicking.value = true
  let successCount = 0
  let failCount = 0
  
  for (const log of kickableDevices.value) {
    try {
      await baiduApi.lockDevice(log.account_id, log.device_id)
      successCount++
    } catch (e) {
      failCount++
    }
  }
  
  ElMessage.info(`批量踢出完成：成功 ${successCount} 个，失败 ${failCount} 个`)
  batchKicking.value = false
  loadLogs()
}

const confirmBatchKick = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要一键踢出当前筛选出的 ${kickableDevices.value.length} 个在线设备吗？`,
      '批量踢出确认',
      { type: 'warning' },
    )
    await handleBatchKick()
  } catch {
    // User cancelled.
  }
}

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getDeviceLogs()
    tableData.value = res.data || []
  } catch (err) {
    ElMessage.error('获取记录失败，请检查后端服务是否正常运行')
    console.error(err)
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  loadingHistory.value = true
  try {
    const res = await baiduApi.getDeviceHistory()
    historyData.value = res.data || []
  } catch (err) {
    ElMessage.error('获取历史记录失败')
    console.error(err)
  } finally {
    loadingHistory.value = false
  }
}

onMounted(() => {
  if (activeTab.value === 'devices') {
    loadLogs()
  } else {
    loadHistory()
  }
})

const handleLockDevice = async (log) => {
  if (!log.account_id || !log.device_id) {
    ElMessage.warning('该记录缺少设备识别参数，无法踢出')
    return
  }
  
  lockingId.value = log.id
  try {
    await baiduApi.lockDevice(log.account_id, log.device_id)
    ElMessage.success('设备已成功踢出/锁定')
    loadLogs()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '锁定失败，请重试')
  } finally {
    lockingId.value = null
  }
}

const confirmLockDevice = async (log) => {
  try {
    await ElMessageBox.confirm('确认要踢出该设备吗？', '锁定确认', {
      type: 'warning',
    })
    await handleLockDevice(log)
  } catch {
    // User cancelled.
  }
}
</script>

<style scoped>
.device-logs-shell {
  background: #f5f6f7;
  min-height: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.device-logs-panel {
  background: #fff;
  min-height: 600px;
  padding: 30px 40px;
}

.device-type-tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 12px;
  margin-bottom: 24px;
}

.device-type-tabs__item {
  position: relative;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: #666;
  font-size: 15px;
  padding: 0;
}

.device-type-tabs__item.is-active {
  color: #333;
  font-weight: 500;
}

.device-type-tabs__item.is-active::after {
  content: '';
  position: absolute;
  bottom: -13px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  border-radius: 2px;
  background: #333;
}

.device-logs-intro {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding: 12px 16px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  background: #fafafa;
  color: #666;
  font-size: 12px;
  line-height: 1.6;
}

.device-logs-intro__title {
  flex-shrink: 0;
  color: #333;
  font-weight: 700;
}

.device-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 12px 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fdfdfd;
}

.device-logs-content {
  min-height: 260px;
}

.device-logs-title {
  margin-bottom: 16px;
  color: #333;
  font-size: 15px;
  font-weight: 700;
}

.device-card-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.device-card {
  width: 380px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fff;
  transition: box-shadow 0.2s ease;
}

.device-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.device-card__main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.device-card__icon,
.device-history-item__icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.device-card__icon {
  width: 48px;
  height: 48px;
}

.device-history-item__icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.device-card__icon img,
.device-history-item__icon img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.device-card__info {
  min-width: 0;
}

.device-card__name,
.device-history-item__name {
  color: #333;
  font-weight: 500;
}

.device-card__name {
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-card__meta,
.device-history-item__meta {
  color: #999;
  font-size: 12px;
}

.device-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.device-card__badge,
.device-history-item__badge {
  display: inline-block;
  border-radius: 4px;
  font-size: 11px;
}

.device-card__badge {
  background: #f0f0f0;
  color: #666;
  padding: 1px 6px;
}

.device-history-item__badge {
  margin-left: 8px;
  background: #eef7ff;
  color: #06a7ff;
  border: 1px solid #d4eeff;
  padding: 2px 6px;
  font-weight: 400;
}

.device-card__unused {
  color: #f28b46;
  font-size: 11px;
}

.device-card__help-icon {
  color: #ccc;
  cursor: help;
}

.device-card__actions {
  display: flex;
  align-items: center;
}

.device-card__status-text {
  color: #999;
  font-size: 12px;
}

.device-history-tip {
  margin-bottom: 24px;
  color: #999;
  font-size: 12px;
}

.device-history-group {
  margin-bottom: 32px;
}

.device-history-group__title {
  margin-bottom: 16px;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.device-history-list {
  border-top: 1px solid #f0f0f0;
}

.device-history-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.device-history-item__main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.device-history-item__time {
  color: #999;
  font-size: 13px;
}

@media (max-width: 960px) {
  .device-logs-panel {
    padding: 20px 16px;
  }

  .device-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .device-card {
    width: 100%;
  }

  .device-history-item {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .device-type-tabs {
    gap: 16px;
    flex-wrap: wrap;
  }

  .device-card {
    flex-direction: column;
  }
}
</style>
