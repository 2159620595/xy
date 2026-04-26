<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="dashboard.lastUpdatedAt || '尚未生成'"
  >
    <template #actions>
      <n-space>
        <n-button secondary :loading="loading" @click="refreshPage">刷新数据</n-button>
      </n-space>
    </template>

    <n-alert type="info" :show-icon="false">
      以下数据直接来自聚点真实后端与数据库，包含账号钻石余额、卡密库存状态和最近操作记录。
    </n-alert>

    <div class="judian-dashboard-grid">
      <n-card title="账号钻石排行" size="small">
        <n-data-table
          :columns="rankingColumns"
          :data="rankingRows"
          :pagination="{ pageSize: 6 }"
          :bordered="false"
        />
      </n-card>

      <n-card title="卡密状态概览" size="small">
        <n-data-table
          :columns="keyColumns"
          :data="keyStatusRows"
          :pagination="false"
          :bordered="false"
        />
      </n-card>
    </div>

    <n-card title="最近操作记录" size="small">
      <n-data-table
        :columns="activityColumns"
        :data="activityRows"
        :pagination="{ pageSize: 8 }"
        :bordered="false"
      />
    </n-card>
  </JudianPageLayout>
</template>

<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { NTag, useMessage } from 'naive-ui'

import { judianApi } from '@/api/judian'
import JudianPageLayout from '@/components/judian/PageLayout.vue'
import { getJudianSectionMeta } from '@/views/judian/shared/page-meta'

const LEGACY_MOCK_STORAGE_KEY = 'judian_frontend_mock_state_v1'

const message = useMessage()
const loading = ref(false)
const dashboard = ref({
  accounts: 0,
  activeSessions: 0,
  enabledAccounts: 0,
  totalDiamonds: 0,
  cdkeys: 0,
  availableCdkeys: 0,
  invalidCdkeys: 0,
  topAccounts: [],
  keyStatusSummary: [],
  activities: [],
  lastUpdatedAt: '',
})
const sectionMeta = getJudianSectionMeta('dashboard')

const accountStatusTypeMap = {
  active: 'success',
  pending: 'warning',
  disabled: 'default',
}

const activityTypeMap = {
  success: 'success',
  info: 'info',
  warning: 'warning',
  error: 'error',
}

const keyStatusTypeMap = {
  unused: 'success',
  active: 'warning',
  expired: 'error',
  void: 'default',
}

const rankingRows = computed(() => dashboard.value.topAccounts || [])
const keyStatusRows = computed(() => dashboard.value.keyStatusSummary || [])
const activityRows = computed(() => dashboard.value.activities || [])

const stats = computed(() => [
  { label: '聚点账号', value: String(dashboard.value.accounts || 0), help: '当前数据库中的聚点账号总数' },
  { label: '活跃会话', value: String(dashboard.value.activeSessions || 0), help: '已成功登录并持有可用会话的账号数量' },
  { label: '总钻石', value: String(dashboard.value.totalDiamonds || 0), help: '所有聚点账号同步回来的真实钻石余额汇总' },
  { label: '可用卡密', value: String(dashboard.value.availableCdkeys || 0), help: '状态为待领取或已领取的真实卡密数量' },
])

const rankingColumns = [
  { title: '账号 ID', key: 'accountId' },
  { title: '显示名称', key: 'displayName' },
  {
    title: '状态',
    key: 'status',
    render: (row) => h(
      NTag,
      { type: accountStatusTypeMap[row.status] || 'default', bordered: false, size: 'small' },
      { default: () => row.status === 'active' ? '活跃' : row.status === 'pending' ? '待登录' : '已停用' },
    ),
  },
  { title: '钻石数量', key: 'diamondQuantity' },
  { title: '最近登录', key: 'lastLoginAt' },
]

const keyColumns = [
  {
    title: '状态',
    key: 'label',
    render: (row) => h(
      NTag,
      { type: keyStatusTypeMap[row.status] || 'default', bordered: false, size: 'small' },
      { default: () => row.label },
    ),
  },
  { title: '数量', key: 'count' },
  { title: '说明', key: 'description' },
]

const activityColumns = [
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: (row) => h(
      NTag,
      { type: activityTypeMap[row.type] || 'default', bordered: false, size: 'small' },
      { default: () => row.type === 'success' ? '成功' : row.type === 'warning' ? '提醒' : row.type === 'error' ? '异常' : '信息' },
    ),
  },
  { title: '标题', key: 'title', width: 160 },
  { title: '说明', key: 'description' },
  { title: '时间', key: 'createdAt', width: 180 },
]

function cleanupLegacyMockStorage() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(LEGACY_MOCK_STORAGE_KEY)
}

function extractErrorMessage(error) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || '请求失败，请稍后重试'
}

async function refreshPage() {
  loading.value = true
  try {
    cleanupLegacyMockStorage()
    const { data } = await judianApi.getDashboardSummary()
    dashboard.value = {
      accounts: Number(data?.accounts || 0),
      activeSessions: Number(data?.activeSessions || 0),
      enabledAccounts: Number(data?.enabledAccounts || 0),
      totalDiamonds: Number(data?.totalDiamonds || 0),
      cdkeys: Number(data?.cdkeys || 0),
      availableCdkeys: Number(data?.availableCdkeys || 0),
      invalidCdkeys: Number(data?.invalidCdkeys || 0),
      topAccounts: Array.isArray(data?.topAccounts) ? data.topAccounts : [],
      keyStatusSummary: Array.isArray(data?.keyStatusSummary) ? data.keyStatusSummary : [],
      activities: Array.isArray(data?.activities) ? data.activities : [],
      lastUpdatedAt: data?.lastUpdatedAt || '',
    }
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    loading.value = false
  }
}

onMounted(refreshPage)
</script>

<style scoped>
.judian-dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 960px) {
  .judian-dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
