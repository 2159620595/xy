<template>
  <section class="netdisk-login-logs">
    <el-card shadow="never">
      <template #header>登录审计筛选</template>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="时间范围">
              <el-select v-model="filters.hours">
                <el-option
                  v-for="item in hoursOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="结果状态">
              <el-select v-model="filters.status" clearable placeholder="全部状态">
                <el-option
                  v-for="item in statusOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="风险等级">
              <el-select v-model="filters.risk_level" clearable placeholder="全部等级">
                <el-option
                  v-for="item in riskLevelOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="用户名">
              <el-input
                v-model="filters.username"
                placeholder="按用户名筛选"
                @keyup.enter="loadLoginLogs"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="登录 IP">
              <el-input
                v-model="filters.ip_address"
                placeholder="按 IP 模糊搜索"
                @keyup.enter="loadLoginLogs"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-form-item label="操作">
              <el-space wrap>
                <el-button type="primary" :loading="loading" @click="loadLoginLogs">
                  查询
                </el-button>
                <el-button @click="resetFilters">重置</el-button>
              </el-space>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <el-alert type="info" :closable="false">
        系统已启用管理员登录加固：密码哈希存储、连续失败自动锁定、成功登录新 IP / 高频失败后成功风险标记。
      </el-alert>
    </el-card>

    <div class="netdisk-login-logs__stats">
      <el-card
        v-for="item in statistics"
        :key="item.label"
        shadow="never"
        class="netdisk-login-logs__stat-card"
      >
        <div class="netdisk-login-logs__stat-label">{{ item.label }}</div>
        <div class="netdisk-login-logs__stat-value">{{ item.value }}</div>
        <div class="stat-help">{{ item.help }}</div>
      </el-card>
    </div>

    <div class="netdisk-login-logs__summary">
      <el-card shadow="never">
        <template #header>可疑 IP</template>
        <el-empty
          v-if="!suspiciousIpRows.length && !loading"
          description="当前筛选范围内未发现高频失败 IP"
        />
        <el-table v-else :data="suspiciousIpRows" stripe v-loading="loading">
          <el-table-column prop="ip_address" label="IP 地址" min-width="220" />
          <el-table-column prop="fail_count" label="失败次数" width="120" />
          <el-table-column label="最后出现时间" min-width="200">
            <template #default="{ row }">
              {{ formatTime(row.last_seen) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>当前锁定对象</template>
        <el-empty
          v-if="!activeLocks.length && !loading"
          description="当前没有处于锁定中的账号或 IP"
        />
        <el-table v-else :data="activeLocks" stripe v-loading="loading">
          <el-table-column prop="scope_label" label="锁定对象" min-width="240" />
          <el-table-column prop="remaining_minutes" label="剩余分钟" width="120" />
          <el-table-column label="解锁时间" min-width="200">
            <template #default="{ row }">
              {{ formatTime(row.locked_until) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="netdisk-login-logs__header">
          <span>登录日志明细</span>
          <el-space wrap>
            <el-tag type="warning" effect="plain">
              当前范围：{{ currentWindowLabel }}
            </el-tag>
            <el-tag type="info" effect="plain">
              锁定规则：{{ lockRuleText }}
            </el-tag>
            <el-button :loading="loading" @click="loadLoginLogs">刷新</el-button>
          </el-space>
        </div>
      </template>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column label="时间" min-width="180" fixed="left">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '成功' ? 'success' : 'danger'">
              {{ row.status || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="110">
          <template #default="{ row }">
            <el-tag :type="resolveRiskTagType(row.risk_level)">
              {{ row.risk_level || '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="tenant_id" label="租户" width="140" />
        <el-table-column prop="ip_address" label="登录 IP" width="160" />
        <el-table-column prop="risk_flags" label="风险标签" min-width="220" />
        <el-table-column prop="login_source" label="登录来源" width="120" />
        <el-table-column prop="request_path" label="接口路径" min-width="180" />
        <el-table-column prop="reason" label="原因 / 说明" min-width="240" />
        <el-table-column prop="log_message" label="完整日志" min-width="460" show-overflow-tooltip />
        <el-table-column prop="user_agent" label="浏览器标识" min-width="360" show-overflow-tooltip />
      </el-table>
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/baidu'

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
    ElMessage.error('登录日志加载失败，请稍后重试')
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
  if (level === '高危') return 'danger'
  if (level === '关注') return 'warning'
  return 'info'
}

function formatTime(timestamp) {
  const value = Number(timestamp || 0)
  if (!value) return '-'
  return new Date(value * 1000).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.netdisk-login-logs {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.netdisk-login-logs__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.netdisk-login-logs__stat-card {
  min-height: 116px;
}

.netdisk-login-logs__stat-label {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 10px;
}

.netdisk-login-logs__stat-value {
  color: #0f172a;
  font-size: 26px;
  font-weight: 700;
}

.netdisk-login-logs__summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.netdisk-login-logs__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stat-help {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

@media (max-width: 1080px) {
  .netdisk-login-logs__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .netdisk-login-logs__summary {
    grid-template-columns: 1fr;
  }

  .netdisk-login-logs__header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .netdisk-login-logs__stats {
    grid-template-columns: 1fr;
  }
}
</style>
