<template>
  <div style="background: #f5f6f7; min-height: 100%; border-radius: 8px; overflow: hidden;">
    <!-- 主体内容 -->
    <div style="background: #fff; display: flex; min-height: 600px;">
      
      <!-- 右侧内容区 -->
      <div style="flex: 1; padding: 30px 40px; min-width: 0;">
        
        <!-- 标签页模拟 -->
        <div style="display: flex; gap: 32px; border-bottom: 1px solid #f0f0f0; padding-bottom: 12px; margin-bottom: 24px;">
          <div 
            @click="activeDeviceType = 'client'"
            :style="{ fontSize: '15px', fontWeight: activeDeviceType === 'client' ? '500' : '400', color: activeDeviceType === 'client' ? '#333' : '#666', position: 'relative', cursor: 'pointer' }"
          >
            客户端设备
            <div v-if="activeDeviceType === 'client'" style="position: absolute; bottom: -13px; left: 50%; transform: translateX(-50%); width: 20px; height: 3px; background: #333; border-radius: 2px;"></div>
          </div>
          <div 
            @click="activeDeviceType = 'web'"
            :style="{ fontSize: '15px', fontWeight: activeDeviceType === 'web' ? '500' : '400', color: activeDeviceType === 'web' ? '#333' : '#666', position: 'relative', cursor: 'pointer' }"
          >
            网页版设备
            <div v-if="activeDeviceType === 'web'" style="position: absolute; bottom: -13px; left: 50%; transform: translateX(-50%); width: 20px; height: 3px; background: #333; border-radius: 2px;"></div>
          </div>
          <div 
            @click="activeDeviceType = 'smart'"
            :style="{ fontSize: '15px', fontWeight: activeDeviceType === 'smart' ? '500' : '400', color: activeDeviceType === 'smart' ? '#333' : '#666', position: 'relative', cursor: 'pointer' }"
          >
            智能端设备
            <div v-if="activeDeviceType === 'smart'" style="position: absolute; bottom: -13px; left: 50%; transform: translateX(-50%); width: 20px; height: 3px; background: #333; border-radius: 2px;"></div>
          </div>
        </div>

        <!-- 提示框 -->
        <div style="background: #fafafa; border: 1px solid #f0f0f0; border-radius: 4px; padding: 12px 16px; font-size: 12px; color: #666; margin-bottom: 24px; display: flex; align-items: flex-start; gap: 8px;">
          <span style="font-weight: bold; color: #333; flex-shrink: 0;">功能介绍：</span>
          <div style="line-height: 1.6;">
            【退出登录】该设备会退出当前账号登录状态，需要重新输入账号密码登录。<br>
            【锁定】网页端设备仅可被锁定，锁定后无法进行任何操作，可以短信验证码方式解锁。
          </div>
        </div>

        <!-- 筛选区域 (因为需要多账号管理保留) -->
        <div v-if="activeTab === 'devices'" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; background: #fdfdfd; padding: 12px 16px; border-radius: 8px; border: 1px solid #f0f0f0;">
          <n-space style="align-items: center;">
            <n-select v-model:value="filterAccount" :options="accountOptions" placeholder="筛选账号" clearable style="width: 160px" size="small" />
            <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="筛选状态" clearable style="width: 130px" size="small" />
            <n-select v-model:value="filterUnused" :options="unusedOptions" placeholder="闲置时间" clearable style="width: 120px" size="small" />
            <n-button @click="loadLogs" :loading="loading" size="small" secondary>刷新</n-button>
          </n-space>
          
          <n-popconfirm @positive-click="handleBatchKick" v-if="kickableDevices.length > 0">
            <template #trigger>
              <n-button type="info" color="#06a7ff" :loading="batchKicking" size="small" style="border-radius: 16px; padding: 0 16px;">
                一键踢出匹配设备 ({{ kickableDevices.length }})
              </n-button>
            </template>
            确定要一键踢出当前筛选出的 {{ kickableDevices.length }} 个在线设备吗？
          </n-popconfirm>
        </div>

        <div v-else style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; background: #fdfdfd; padding: 12px 16px; border-radius: 8px; border: 1px solid #f0f0f0;">
          <n-space style="align-items: center;">
            <n-select v-model:value="filterAccount" :options="accountOptions" placeholder="筛选账号" clearable style="width: 160px" size="small" />
            <n-button @click="loadHistory" :loading="loadingHistory" size="small" secondary>刷新</n-button>
          </n-space>
        </div>

        <!-- 列表 -->
        <n-spin :show="activeTab === 'devices' ? loading : loadingHistory">
          <!-- 在线设备试图 -->
          <div v-if="activeTab === 'devices'">
            <div v-if="filteredTableData.length > 0">
              <div style="font-size: 15px; font-weight: bold; color: #333; margin-bottom: 16px;">
                已登录设备 ({{ filteredTableData.length }})
              </div>

              <div style="display: flex; flex-wrap: wrap; gap: 24px;">
                <div v-for="log in filteredTableData" :key="log.id" style="width: 380px; border: 1px solid #f0f0f0; border-radius: 8px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s; background: #fff;" @mouseover="$event.currentTarget.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)'" @mouseout="$event.currentTarget.style.boxShadow='none'">
                  
                  <div style="display: flex; align-items: center; gap: 16px;">
                    <!-- Icon -->
                    <div style="width: 48px; height: 48px; display: flex; align-items: center; justify-content: center;">
                      <img v-if="log.icon" :src="log.icon" style="max-width: 100%; max-height: 100%; object-fit: contain;" @error="(e) => e.target.style.display='none'" />
                      <template v-else>
                        <img v-if="log.location && log.location.includes('Mac')" src="https://ndstatic.cdn.bcebos.com/diskDevice/mac.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.location && log.location.includes('Android')" src="https://ndstatic.cdn.bcebos.com/diskDevice/android.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.location && log.location.includes('iPhone')" src="https://ndstatic.cdn.bcebos.com/diskDevice/iphone.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.location && log.location.includes('iPad')" src="https://ndstatic.cdn.bcebos.com/diskDevice/ipad.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.location && (log.location.includes('Windows') || log.location.includes('Edge'))" src="https://ndstatic.cdn.bcebos.com/diskDevice/ie.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.location && log.location.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.device_name && log.device_name.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.device_name && log.device_name.includes('Firefox')" src="https://ndstatic.cdn.bcebos.com/diskDevice/firefox.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else-if="log.device_name && log.device_name.includes('Safari')" src="https://ndstatic.cdn.bcebos.com/diskDevice/safari.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        <img v-else src="https://ndstatic.cdn.bcebos.com/diskDevice/pc.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                      </template>
                    </div>

                    <!-- Info -->
                    <div style="max-width: 180px;">
                      <div style="font-size: 15px; color: #333; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500;">
                        {{ log.device_name || '未知设备' }}
                      </div>
                      <div style="font-size: 12px; color: #999; display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
                        <span>{{ log.location || '未知端' }}</span>
                        <span v-if="log.account_name" style="background: #f0f0f0; padding: 1px 6px; border-radius: 4px; font-size: 10px; color: #666; display: inline-block;">{{ log.account_name }}</span>
                        <n-tooltip v-if="log.unused_days > 0" trigger="hover">
                          <template #trigger>
                            <span style="color: #f28b46; font-size: 11px;">(闲置{{ log.unused_days }}天)</span>
                          </template>
                          IP: {{ log.ip_address }} | 最近使用: {{ log.created_at ? new Date(log.created_at * 1000).toLocaleString('zh-CN', { hour12: false }) : '未知' }}
                        </n-tooltip>
                        <n-tooltip v-else trigger="hover">
                          <template #trigger>
                            <n-icon size="12" style="color: #ccc; cursor: help;"><InfoCircleOutlined /></n-icon>
                          </template>
                          IP: {{ log.ip_address }} | 最近使用: {{ log.created_at ? new Date(log.created_at * 1000).toLocaleString('zh-CN', { hour12: false }) : '未知' }}
                        </n-tooltip>
                      </div>
                    </div>
                  </div>

                  <!-- Button -->
                  <div>
                    <div v-if="log.action === '当前使用设备' || log.is_current" style="font-size: 12px; color: #999; text-align: right; padding-right: 8px;">
                      本机
                    </div>
                    <n-button 
                      v-else-if="log.button" 
                      type="info"
                      color="#06a7ff"
                      size="small" 
                      style="border-radius: 16px; padding: 0 16px; font-size: 12px;"
                      @click="handleLockDevice(log)"
                      :loading="lockingId === log.id"
                    >{{ log.button }}</n-button>
                    <div v-else style="font-size: 12px; color: #999; text-align: right; padding-right: 8px;">
                      {{ log.status }}
                    </div>
                  </div>

                </div>
              </div>
            </div>
            <n-empty v-else-if="!loading" description="暂无匹配设备" style="margin: 80px 0;" />
          </div>

          <!-- 使用记录视图 -->
          <div v-else>
            <div v-if="filteredHistoryData.length > 0">
              <div style="font-size: 12px; color: #999; margin-bottom: 24px;">
                显示所有账号最近6个月的使用记录
              </div>
              
              <div v-for="group in groupedHistoryData" :key="group.date" style="margin-bottom: 32px;">
                <div style="font-size: 16px; font-weight: 500; color: #333; margin-bottom: 16px;">
                  {{ group.date }}
                </div>
                
                <div style="border-top: 1px solid #f0f0f0;">
                  <div v-for="log in group.items" :key="log.id" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid #f0f0f0; transition: background 0.2s;" @mouseover="$event.currentTarget.style.background='#fafafa'" @mouseout="$event.currentTarget.style.background='transparent'">
                    
                    <div style="display: flex; align-items: center; gap: 16px;">
                      <!-- Icon -->
                      <div style="width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <img v-if="log.icon" :src="log.icon" style="max-width: 100%; max-height: 100%; object-fit: contain;" @error="(e) => e.target.style.display='none'" />
                        <template v-else>
                          <img v-if="log.location && log.location.includes('Mac')" src="https://ndstatic.cdn.bcebos.com/diskDevice/mac.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.location && log.location.includes('Android')" src="https://ndstatic.cdn.bcebos.com/diskDevice/android.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.location && log.location.includes('iPhone')" src="https://ndstatic.cdn.bcebos.com/diskDevice/iphone.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.location && log.location.includes('iPad')" src="https://ndstatic.cdn.bcebos.com/diskDevice/ipad.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.location && (log.location.includes('Windows') || log.location.includes('Edge'))" src="https://ndstatic.cdn.bcebos.com/diskDevice/ie.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.location && log.location.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.device_name && log.device_name.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.device_name && log.device_name.includes('Firefox')" src="https://ndstatic.cdn.bcebos.com/diskDevice/firefox.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else-if="log.device_name && log.device_name.includes('Safari')" src="https://ndstatic.cdn.bcebos.com/diskDevice/safari.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                          <img v-else src="https://ndstatic.cdn.bcebos.com/diskDevice/pc.png" style="max-width:100%;max-height:100%;object-fit:contain;" />
                        </template>
                      </div>

                      <!-- Info -->
                      <div>
                        <div style="font-size: 14px; font-weight: 500; color: #333; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
                          {{ log.device_name || '未知设备' }}
                          <span v-if="log.account_name" style="background: #eef7ff; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #06a7ff; font-weight: normal; border: 1px solid #d4eeff;">{{ log.account_name }}</span>
                        </div>
                        <div style="font-size: 12px; color: #999; margin-bottom: 2px;">
                          {{ log.location || '未知端' }}
                        </div>
                        <div style="font-size: 12px; color: #999;">
                          ({{ log.ip_address }})
                        </div>
                      </div>
                    </div>

                    <!-- Time -->
                    <div style="font-size: 13px; color: #999;">
                      {{ formatTime(log.created_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <n-empty v-else-if="!loadingHistory" description="暂无使用记录" style="margin: 80px 0;" />
          </div>
        </n-spin>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { InfoCircleOutlined } from '@vicons/antd'
import { baiduApi } from '@/api/baidu'

const route = useRoute()
const message = useMessage()
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
  const source = activeTab.value === 'devices' ? tableData.value : historyData.value;
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
  
  message.info(`批量踢出完成：成功 ${successCount} 个，失败 ${failCount} 个`)
  batchKicking.value = false
  loadLogs()
}

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getDeviceLogs()
    tableData.value = res.data || []
  } catch (err) {
    message.error('获取记录失败，请检查后端服务是否正常运行')
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
    message.error('获取历史记录失败')
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
    message.warning('该记录缺少设备识别参数，无法踢出')
    return
  }
  
  lockingId.value = log.id
  try {
    await baiduApi.lockDevice(log.account_id, log.device_id)
    message.success('设备已成功踢出/锁定')
    loadLogs()
  } catch (e) {
    message.error(e?.response?.data?.detail || '锁定失败，请重试')
  } finally {
    lockingId.value = null
  }
}
</script>
