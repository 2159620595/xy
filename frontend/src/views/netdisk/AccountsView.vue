<template>
  <n-space vertical size="large" style="padding: 24px">
    <n-card title="网盘账号池管理">
      <template #header-extra>
        <n-space>
          <n-button @click="loadAccounts" :loading="loading" secondary>刷新列表</n-button>
          <n-button secondary @click="handleExportAll"> 导出全部CK </n-button>
          <n-button @click="showCkAddModal = true" secondary> CK 添加账户 </n-button>
          <n-button type="primary" @click="handleOpenQr">
            <template #icon><i class="i-carbon-qr-code"></i></template>
            扫码添加账户
          </n-button>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
      />
    </n-card>

    <!-- 扫码弹窗 -->
    <n-modal
      v-model:show="showQrModal"
      preset="card"
      title="百度网盘官方扫码登录"
      style="width: 360px"
      :mask-closable="false"
      @after-leave="handleModalClose"
    >
      <div style="text-align: center; padding: 10px">
        <n-spin :show="qrLoading">
          <div
            style="
              min-height: 220px;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
            "
          >
            <img
              v-if="currentQr"
              :src="currentQr"
              style="width: 220px; height: 220px; border: 1px solid #f0f0f0; border-radius: 8px"
              :style="{ opacity: isScanned ? 0.3 : 1 }"
            />
            <n-empty v-else-if="!qrLoading" description="二维码生成失败" />
            <div v-if="isScanned" style="position: absolute; color: #18a058; font-weight: bold">
              <p>已扫码，请在手机确认</p>
            </div>
          </div>
          <div style="margin-top: 16px; color: #666; font-size: 14px">
            <p v-if="qrLoading">正在安全连接百度服务器...</p>
            <p v-else-if="isScanned" style="color: #18a058">√ 手机端等待确认中</p>
            <p v-else>请使用 <b>百度网盘 App</b> 扫码</p>
          </div>
        </n-spin>
      </div>
    </n-modal>

    <!-- 更新 Cookie 弹窗 -->
    <n-modal v-model:show="showCookieModal" preset="card" title="更新账号信息" style="width: 480px">
      <n-space vertical>
        <n-text depth="3" style="font-size: 13px">
          粘贴该账号的完整 Cookie 字符串（可选，不更新请留空）
        </n-text>
        <n-input
          v-model:value="newCookie"
          type="textarea"
          placeholder="BDUSS=xxx; STOKEN=xxx; ..."
          :autosize="{ minRows: 3, maxRows: 6 }"
        />
        <n-text depth="3" style="font-size: 13px; margin-top: 12px">
          绑定独立代理 IP（可选，异地风控防护，格式：http://user:pass@ip:port）
        </n-text>
        <n-input
          v-model:value="newProxy"
          type="text"
          placeholder="例如：http://abc:123@114.114.114.114:8888"
        />
        <n-space justify="end" style="margin-top: 16px">
          <n-button @click="showCookieModal = false">取消</n-button>
          <n-button type="primary" :loading="cookieUpdating" @click="confirmUpdateCookie">
            确认保存
          </n-button>
        </n-space>
      </n-space>
    </n-modal>
  </n-space>
  <!-- CK 添加账户弹窗 -->
  <n-modal
    v-model:show="showCkAddModal"
    preset="card"
    title="通过 Cookie 添加账户"
    style="width: 500px"
  >
    <n-space vertical>
      <n-text depth="3" style="font-size: 13px">
        粘贴完整的百度 Cookie 字符串（必须包含 BDUSS），系统会自动识别账号信息
      </n-text>
      <n-input
        v-model:value="ckAddValue"
        type="textarea"
        placeholder="BDUSS=xxxxx; STOKEN=xxxxx; ..."
        :autosize="{ minRows: 4, maxRows: 8 }"
      />
      <n-space justify="end">
        <n-button @click="showCkAddModal = false">取消</n-button>
        <n-button type="primary" :loading="ckAdding" @click="handleAddByCookie">
          确认添加
        </n-button>
      </n-space>
    </n-space>
  </n-modal>

  <!-- 设备管理弹窗 -->
  <n-modal
    v-model:show="showDeviceModal"
    preset="card"
    title="设备管理"
    style="width: 800px; background-color: #f7f9fc;"
    :mask-closable="true"
  >
    <n-spin :show="devicesLoading" style="min-height: 200px">
      <div v-if="devices.length > 0" style="display: flex; flex-wrap: wrap; gap: 16px; padding: 4px">
        <div v-for="dev in devices" :key="dev.device_id" style="width: calc(50% - 8px); border: 1px solid #ebedf0; border-radius: 8px; padding: 16px; display: flex; justify-content: space-between; align-items: center; background: #fff; transition: all 0.3s;" @mouseover="$event.currentTarget.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)'" @mouseout="$event.currentTarget.style.boxShadow='none'">
          <div style="display: flex; align-items: flex-start; gap: 12px; flex: 1;">
              <div style="width:50px;height:50px;border-radius:50%;overflow:hidden;flex-shrink:0;margin-right:8px;background:#f5f5f5;display:flex;align-items:center;justify-content:center;padding:4px">
                <img v-if="dev.icon" :src="dev.icon" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                <template v-else>
                  <img v-if="dev.os && dev.os.includes('Mac')" src="https://ndstatic.cdn.bcebos.com/diskDevice/mac.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.os && dev.os.includes('Android')" src="https://ndstatic.cdn.bcebos.com/diskDevice/android.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.os && dev.os.includes('iPhone')" src="https://ndstatic.cdn.bcebos.com/diskDevice/iphone.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.os && dev.os.includes('iPad')" src="https://ndstatic.cdn.bcebos.com/diskDevice/ipad.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.os && (dev.os.includes('Windows') || dev.os.includes('Edge'))" src="https://ndstatic.cdn.bcebos.com/diskDevice/ie.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.os && dev.os.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.device_name && dev.device_name.includes('Chrome')" src="https://ndstatic.cdn.bcebos.com/diskDevice/chrome.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else-if="dev.device_name && dev.device_name.includes('Safari')" src="https://ndstatic.cdn.bcebos.com/diskDevice/safari.png" style="width:100%;height:100%;object-fit:contain;" @error="(e) => e.target.style.display='none'" />
                  <img v-else src="https://ndstatic.cdn.bcebos.com/diskDevice/pc.png" style="width:100%;height:100%;object-fit:contain;" />
                </template>
              </div>
              <div style="flex:1">
                <div style="font-weight: 500; font-size: 14px; margin-bottom: 4px; color: #333; display: flex; align-items: center; gap: 8px;">
                  {{ dev.device_name || '未知设备' }}
                </div>
                <div style="font-size: 12px; color: #666; margin-bottom: 4px;">{{ dev.os || '未知系统' }}</div>
                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">IP: {{ dev.ip || '未知' }}</div>
                
                <div style="display: flex; align-items: center; gap: 4px; font-size: 12px; padding: 2px 8px; background-color: #f5f5f5; border-radius: 12px; width: fit-content;">
                  <span style="color: #666;">状态:</span>
                  <span :style="{ color: dev.status === '在线' ? '#18a058' : '#d03050' }">{{ dev.status }}</span>
                </div>
              </div>
          </div>
          
          <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between; height: 100%; min-width: 140px;">
            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">未使用: {{ dev.unused_days || 0 }}天</div>
            <div style="font-size: 12px; color: #999; margin-bottom: auto;">
              时间: {{ dev.last_used ? new Date(dev.last_used * 1000).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-') : '未知' }}
            </div>
            
            <div style="margin-top: 16px;">
              <n-button 
                v-if="dev.is_current" 
                type="primary"
                color="#8DE0B8"
                size="small" 
                round 
                style="color: #fff; border: none; font-weight: 500; pointer-events: none; padding: 0 16px; margin-top: 8px;"
              >当前设备</n-button>
              
              <n-popconfirm v-else-if="dev.status === '在线'" @positive-click="handleLockDevice(dev.device_id)">
                <template #trigger>
                  <n-button 
                    color="#5C9DFB"
                    size="small" 
                    round 
                    style="color: #fff; border: none; font-weight: 500; padding: 0 20px; margin-top: 8px;"
                    :loading="lockingDeviceId === dev.device_id"
                  >锁定</n-button>
                </template>
                确认要强制踢出该设备吗？
              </n-popconfirm>
              
              <n-button 
                v-else 
                color="#F3B0B0"
                size="small" 
                round 
                style="color: #fff; border: none; font-weight: 500; pointer-events: none; padding: 0 20px; margin-top: 8px;"
              >已锁定</n-button>
            </div>
          </div>
        </div>
      </div>
      <n-empty v-else-if="!devicesLoading" description="暂无设备数据或获取失败" style="margin: 40px 0;" />
    </n-spin>
  </n-modal>
</template>

<script setup>
import { ref, h, onMounted, onUnmounted } from 'vue'
import { NTag, NButton, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { baiduApi } from '@/api/baidu'

const message = useMessage()
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

// ── 表格列 ──────────────────────────────────────────────────
const columns = [
  {
    title: '账号名称',
    key: 'username',
    align: 'center',
    render: (row) =>
      h('div', { style: 'display:flex;align-items:center;gap:8px;justify-content:center' }, [
        row.avatar_url
          ? h('img', {
              src: row.avatar_url,
              style: 'width:28px;height:28px;border-radius:50%;object-fit:cover;flex-shrink:0',
            })
          : h(
              'div',
              {
                style:
                  'width:28px;height:28px;border-radius:50%;background:#e0e0e0;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0',
              },
              row.username?.[0] || '?',
            ),
        h('span', row.username),
      ]),
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render: (row) =>
      h(
        NTag,
        { type: row.status === 1 ? 'success' : 'error', bordered: false },
        { default: () => (row.status === 1 ? '正常' : '失效') },
      ),
  },
  { title: '会员等级', key: 'vip_level', align: 'center' },
  { 
    title: '绑定代理', 
    key: 'proxy_url', 
    align: 'center',
    render: (row) => row.proxy_url ? h(NTag, { type: 'info', size: 'small', bordered: false }, { default: () => '已绑定代理' }) : h('span', {style: 'color:#999'}, '无')
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render: (row) =>
      h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            // 导出 CK 按钮
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'info',
                onClick: () => handleExportCookie(row),
              },
              { default: () => '导出CK' },
            ),
            // 更新 按钮
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'warning',
                onClick: () => handleOpenUpdateCookie(row),
              },
              { default: () => '更新/绑定代理' },
            ),
            // 设备管理
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'info',
                onClick: () => handleOpenDevices(row),
              },
              { default: () => '设备管理' },
            ),
            // 删除按钮（带二次确认）
            h(
              NPopconfirm,
              { onPositiveClick: () => handleDelete(row) },
              {
                trigger: () =>
                  h(
                    NButton,
                    { size: 'small', quaternary: true, type: 'error' },
                    { default: () => '删除' },
                  ),
                default: () => `确认删除账号「${row.username}」？`,
              },
            ),
          ],
        },
      ),
  },
]

// ── 账号列表 ────────────────────────────────────────────────
const handleExportAll = () => {
  if (!tableData.value.length) return message.warning('暂无账号数据')
  const lines = tableData.value
    .map((row, i) => `# 账号${i + 1}：${row.username}（${row.vip_level}）\n${row.cookie}`)
    .join('\n\n' + '-'.repeat(60) + '\n\n')

  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `全部账号Cookie_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
  message.success(`已导出 ${tableData.value.length} 个账号的 Cookie`)
}

const loadAccounts = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getAccounts()
    tableData.value = res.data || []
  } catch {
    message.error('获取账号列表失败')
  } finally {
    loading.value = false
  }
}

// ── CK 添加账户 ───────────────────────────────────────────────
const handleAddByCookie = async () => {
  if (!ckAddValue.value.trim()) return message.warning('请粘贴 Cookie 内容')
  ckAdding.value = true
  try {
    const res = await baiduApi.addByCookie(ckAddValue.value.trim())
    message.success(res.data.msg || '添加成功')
    showCkAddModal.value = false
    ckAddValue.value = ''
    loadAccounts()
  } catch (e) {
    message.error(e?.response?.data?.detail || '添加失败，请检查 Cookie 是否有效')
  } finally {
    ckAdding.value = false
  }
}

// ── 删除 ────────────────────────────────────────────────────
const handleDelete = async (row) => {
  try {
    await baiduApi.deleteAccount(row.id)
    message.success(`账号「${row.username}」已删除`)
    loadAccounts()
  } catch {
    message.error('删除失败，请重试')
  }
}

// ── 导出 Cookie ─────────────────────────────────────────────
const handleExportCookie = (row) => {
  if (!row.cookie) return message.warning('该账号暂无 Cookie')
  // 构建导出内容
  const lines = [
    `账号：${row.username}`,
    `会员等级：${row.vip_level}`,
    `状态：${row.status === 1 ? '正常' : '失效'}`,
    ``,
    `Cookie：`,
    row.cookie,
  ].join('\n')

  // 复制到剪贴板
  navigator.clipboard.writeText(row.cookie).then(() => {
    message.success(`已复制「${row.username}」的 Cookie`)
  })

  // 同时下载为 txt 文件
  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${row.username}_cookie.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// ── 更新 Cookie 和 代理 ─────────────────────────────────────────────
const handleOpenUpdateCookie = (row) => {
  editingAccount.value = row
  newCookie.value = ''
  newProxy.value = row.proxy_url || ''
  showCookieModal.value = true
}

const confirmUpdateCookie = async () => {
  const cookieStr = newCookie.value.trim()
  const proxyStr = newProxy.value.trim()
  
  if (!cookieStr && !proxyStr && !editingAccount.value.proxy_url) {
    message.warning('没有任何更改')
    return
  }
  
  cookieUpdating.value = true
  try {
    const payload = {}
    if (cookieStr) payload.cookie = cookieStr
    if (proxyStr || proxyStr === '') payload.proxy_url = proxyStr
    
    await baiduApi.updateCookie(editingAccount.value.id, payload)
    message.success(`账号「${editingAccount.value.username}」信息已保存`)
    showCookieModal.value = false
    loadAccounts()
  } catch {
    message.error('保存失败，请重试')
  } finally {
    cookieUpdating.value = false
  }
}

// ── 设备管理 ──────────────────────────────────────────────────
const handleOpenDevices = async (row) => {
  currentDeviceAccountId.value = row.id
  showDeviceModal.value = true
  devicesLoading.value = true
  devices.value = []
  
  try {
    const res = await baiduApi.getDevices(row.id)
    devices.value = res.data || []
  } catch (e) {
    message.error(e?.response?.data?.detail || '获取设备列表失败')
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
    message.success('设备已成功踢出/锁定')
    
    // 重新获取设备列表
    const res = await baiduApi.getDevices(currentDeviceAccountId.value)
    devices.value = res.data || []
  } catch (e) {
    message.error(e?.response?.data?.detail || '锁定失败，请重试')
  } finally {
    lockingDeviceId.value = null
  }
}

// ── 扫码登录 ────────────────────────────────────────────────
const handleOpenQr = async () => {
  currentQr.value = ''
  isScanned.value = false
  qrLoading.value = true
  showQrModal.value = true
  try {
    const { data } = await baiduApi.getQr()
    currentQr.value = data.imgurl
    currentSign = data.sign
    qrLoading.value = false
    pollingActive = true
    performPolling()
  } catch {
    message.error('初始化百度安全通道失败')
    showQrModal.value = false
  }
}

const performPolling = async () => {
  if (!pollingActive || !currentSign) return
  try {
    const { data } = await baiduApi.checkStatus(currentSign)
    if (data.status === 'success') {
      message.success(`欢迎回来，${data.username}！`)
      showQrModal.value = false
      loadAccounts()
      return
    }
    if (data.status === 'scanned') isScanned.value = true
    else if (data.status === 'failed') {
      message.warning(data.msg || '登录失败，请重试')
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
