<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="dashboard.lastUpdatedAt || '尚未生成'"
  >
    <template #actions>
      <el-space>
        <el-button :loading="loading" @click="refreshPage">刷新数据</el-button>
      </el-space>
    </template>

    <el-alert type="info" :closable="false">
      以下数据直接来自聚点真实后端与数据库，包含账号钻石余额、卡密库存状态和最近操作记录。
    </el-alert>

    <div class="judian-dashboard-grid">
      <el-card shadow="never">
        <template #header>账号钻石排行</template>
        <el-table :data="rankingRows" stripe>
          <el-table-column prop="accountId" label="账号 ID" min-width="120" />
          <el-table-column prop="displayName" label="显示名称" min-width="160" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="accountStatusTypeMap[row.status] || 'info'">
                {{
                  row.status === 'active'
                    ? '活跃'
                    : row.status === 'pending'
                      ? '待登录'
                      : '已停用'
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="diamondQuantity" label="钻石数量" width="120" />
          <el-table-column prop="lastLoginAt" label="最近登录" min-width="180" />
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>卡密状态概览</template>
        <el-table :data="keyStatusRows" stripe>
          <el-table-column label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="keyStatusTypeMap[row.status] || 'info'">
                {{ row.label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="count" label="数量" width="100" />
          <el-table-column prop="description" label="说明" min-width="180" />
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>最近操作记录</template>
      <el-table :data="activityRows" stripe>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="activityTypeMap[row.type] || 'info'">
              {{
                row.type === 'success'
                  ? '成功'
                  : row.type === 'warning'
                    ? '提醒'
                    : row.type === 'error'
                      ? '异常'
                      : '信息'
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="description" label="说明" min-width="220" />
        <el-table-column prop="createdAt" label="时间" min-width="180" />
      </el-table>
    </el-card>
  </JudianPageLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { judianApi } from '@/api/judian'
import JudianPageLayout from '@/components/judian/PageLayout.vue'
import { getJudianSectionMeta } from '@/views/judian/shared/page-meta'

const LEGACY_MOCK_STORAGE_KEY = 'judian_frontend_mock_state_v1'

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
  disabled: 'info',
}

const activityTypeMap = {
  success: 'success',
  info: 'info',
  warning: 'warning',
  error: 'danger',
}

const keyStatusTypeMap = {
  unused: 'success',
  active: 'warning',
  expired: 'danger',
  void: 'info',
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
    ElMessage.error(extractErrorMessage(error))
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
