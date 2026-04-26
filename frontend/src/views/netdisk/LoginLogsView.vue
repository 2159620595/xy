<template>
  <n-space vertical size="large">
    <n-card title="登录审计筛选" :bordered="false">
      <n-grid cols="1 s:2 m:4 l:6" responsive="screen" :x-gap="16" :y-gap="12">
        <n-gi>
          <n-form-item label="时间范围" label-placement="top">
            <n-select v-model:value="filters.hours" :options="hoursOptions" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="结果状态" label-placement="top">
            <n-select v-model:value="filters.status" :options="statusOptions" clearable placeholder="全部状态" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="风险等级" label-placement="top">
            <n-select v-model:value="filters.risk_level" :options="riskLevelOptions" clearable placeholder="全部等级" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="用户名" label-placement="top">
            <n-input v-model:value="filters.username" placeholder="按用户名筛选" @keyup.enter="loadLoginLogs" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="登录 IP" label-placement="top">
            <n-input v-model:value="filters.ip_address" placeholder="按 IP 模糊搜索" @keyup.enter="loadLoginLogs" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="操作" label-placement="top">
            <n-space>
              <n-button type="primary" :loading="loading" @click="loadLoginLogs">查询</n-button>
              <n-button @click="resetFilters">重置</n-button>
            </n-space>
          </n-form-item>
        </n-gi>
      </n-grid>
      <n-alert type="info" :show-icon="false">
        系统已启用管理员登录加固：密码哈希存储、连续失败自动锁定、成功登录新 IP / 高频失败后成功风险标记。
      </n-alert>
    </n-card>

    <n-grid cols="1 s:2 m:3 l:6" responsive="screen" :x-gap="12" :y-gap="12">
      <n-gi v-for="item in statistics" :key="item.label">
        <n-card size="small" :bordered="false">
          <n-statistic :label="item.label" :value="item.value" />
          <div class="stat-help">{{ item.help }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-card title="可疑 IP" :bordered="false">
          <n-empty v-if="!suspiciousIpRows.length && !loading" description="当前筛选范围内未发现高频失败 IP" />
          <n-data-table
            v-else
            :columns="suspiciousColumns"
            :data="suspiciousIpRows"
            :loading="loading"
            :pagination="false"
            size="small"
          />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="当前锁定对象" :bordered="false">
          <n-empty v-if="!activeLocks.length && !loading" description="当前没有处于锁定中的账号或 IP" />
          <n-data-table
            v-else
            :columns="activeLockColumns"
            :data="activeLocks"
            :loading="loading"
            :pagination="false"
            size="small"
          />
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="登录日志明细" :bordered="false">
      <template #header-extra>
        <n-space>
          <n-tag size="small" type="warning" round>当前范围：{{ currentWindowLabel }}</n-tag>
          <n-tag size="small" type="info" round>锁定规则：{{ lockRuleText }}</n-tag>
          <n-button secondary :loading="loading" @click="loadLoginLogs">刷新</n-button>
        </n-space>
      </template>
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        :scroll-x="1860"
        size="small"
      />
    </n-card>
  </n-space>
</template>

<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { NTag, useMessage } from 'naive-ui'
import { authApi } from '@/api/baidu'

const message = useMessage()
const loading = ref(false)
const tableData = ref([])
const summary = ref({
  total: 0,
  success: 0,
  failed: 0,
  unique_ip_count: 0,
  attention_count: 0,
  high_risk_count: 0,
  suspicious_ip_count: 0,
  top_failed_ips: [],
  active_locks: [],
  window_hours: 168,
  lock_threshold: 5,
  lock_window_minutes: 15,
  lock_duration_minutes: 30,
})

const filters = ref({
  hours: 168,
  status: null,
  risk_level: null,
  username: '',
  ip_address: '',
})

const hoursOptions = [
  { label: '近 24 小时', value: 24 },
  { label: '近 3 天', value: 72 },
  { label: '近 7 天', value: 168 },
  { label: '近 30 天', value: 720 },
  { label: '全部时间', value: 0 },
]

const statusOptions = [
  { label: '成功', value: '成功' },
  { label: '失败', value: '失败' },
]

const riskLevelOptions = [
  { label: '正常', value: '正常' },
  { label: '关注', value: '关注' },
  { label: '高危', value: '高危' },
]

const currentWindowLabel = computed(() => {
  const matched = hoursOptions.find((item) => item.value === filters.value.hours)
  return matched?.label || '自定义范围'
})

const lockRuleText = computed(() => `连续 ${summary.value.lock_threshold} 次失败 / ${summary.value.lock_window_minutes} 分钟窗口 / 锁定 ${summary.value.lock_duration_minutes} 分钟`)

const statistics = computed(() => [
  { label: '总登录次数', value: summary.value.total, help: '当前筛选窗口内的管理员登录总次数' },
  { label: '成功登录', value: summary.value.success, help: '用于确认最近是否存在正常运维登录' },
  { label: '失败登录', value: summary.value.failed, help: '失败次数过高通常需要重点关注' },
  { label: '风险关注', value: summary.value.attention_count, help: '被标记为关注的新 IP 或异常切换登录' },
  { label: '高危登录', value: summary.value.high_risk_count, help: '高频失败后成功或叠加多个风险特征' },
  { label: '涉及 IP / 可疑 IP', value: `${summary.value.unique_ip_count} / ${summary.value.suspicious_ip_count}`, help: '可疑 IP 判定规则为失败次数不少于 3 次' },
])

const suspiciousIpRows = computed(() => summary.value.top_failed_ips || [])
const activeLocks = computed(() => summary.value.active_locks || [])

const suspiciousColumns = [
  { title: 'IP 地址', key: 'ip_address', width: 220 },
  { title: '失败次数', key: 'fail_count', width: 120 },
  {
    title: '最后出现时间',
    key: 'last_seen',
    width: 200,
    render: (row) => formatTime(row.last_seen),
  },
]

const activeLockColumns = [
  { title: '锁定对象', key: 'scope_label', minWidth: 240 },
  { title: '剩余分钟', key: 'remaining_minutes', width: 120 },
  {
    title: '解锁时间',
    key: 'locked_until',
    width: 200,
    render: (row) => formatTime(row.locked_until),
  },
]

const columns = [
  {
    title: '时间',
    key: 'created_at',
    width: 180,
    fixed: 'left',
    render: (row) => formatTime(row.created_at),
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: row.status === '成功' ? 'success' : 'error' }, { default: () => row.status || '-' }),
  },
  {
    title: '风险等级',
    key: 'risk_level',
    width: 110,
    render: (row) => h(NTag, { size: 'small', type: resolveRiskTagType(row.risk_level) }, { default: () => row.risk_level || '正常' }),
  },
  { title: '用户名', key: 'username', width: 140 },
  { title: '租户', key: 'tenant_id', width: 140 },
  { title: '登录 IP', key: 'ip_address', width: 160 },
  {
    title: '风险标签',
    key: 'risk_flags',
    width: 220,
    render: (row) => row.risk_flags || '-',
  },
  { title: '登录来源', key: 'login_source', width: 120 },
  { title: '接口路径', key: 'request_path', width: 180 },
  {
    title: '原因 / 说明',
    key: 'reason',
    width: 240,
    render: (row) => row.reason || '-',
  },
  {
    title: '完整日志',
    key: 'log_message',
    minWidth: 460,
    ellipsis: {
      tooltip: true,
    },
    render: (row) => row.log_message || '-',
  },
  {
    title: '浏览器标识',
    key: 'user_agent',
    minWidth: 360,
    ellipsis: {
      tooltip: true,
    },
    render: (row) => row.user_agent || '-',
  },
]

onMounted(() => {
  loadLoginLogs()
})

async function loadLoginLogs() {
  loading.value = true
  try {
    const { data } = await authApi.getLoginLogs({
      limit: 200,
      hours: filters.value.hours,
      status: filters.value.status || undefined,
      risk_level: filters.value.risk_level || undefined,
      username: filters.value.username || undefined,
      ip_address: filters.value.ip_address || undefined,
    })
    tableData.value = Array.isArray(data?.logs) ? data.logs : []
    summary.value = {
      total: Number(data?.summary?.total || 0),
      success: Number(data?.summary?.success || 0),
      failed: Number(data?.summary?.failed || 0),
      unique_ip_count: Number(data?.summary?.unique_ip_count || 0),
      attention_count: Number(data?.summary?.attention_count || 0),
      high_risk_count: Number(data?.summary?.high_risk_count || 0),
      suspicious_ip_count: Number(data?.summary?.suspicious_ip_count || 0),
      top_failed_ips: Array.isArray(data?.summary?.top_failed_ips) ? data.summary.top_failed_ips : [],
      active_locks: Array.isArray(data?.summary?.active_locks) ? data.summary.active_locks : [],
      window_hours: Number(data?.summary?.window_hours ?? filters.value.hours),
      lock_threshold: Number(data?.summary?.lock_threshold || 5),
      lock_window_minutes: Number(data?.summary?.lock_window_minutes || 15),
      lock_duration_minutes: Number(data?.summary?.lock_duration_minutes || 30),
    }
  } catch (error) {
    console.error('加载登录日志失败:', error)
    message.error('登录日志加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = {
    hours: 168,
    status: null,
    risk_level: null,
    username: '',
    ip_address: '',
  }
  loadLoginLogs()
}

function resolveRiskTagType(level) {
  if (level === '高危') return 'error'
  if (level === '关注') return 'warning'
  return 'default'
}

function formatTime(timestamp) {
  const value = Number(timestamp || 0)
  if (!value) return '-'
  return new Date(value * 1000).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.stat-help {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}
</style>
