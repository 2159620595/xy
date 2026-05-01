<template>
  <section class="netdisk-cdkeys">
    <el-card shadow="never">
      <template #header>批量生成卡密</template>
      <el-form label-position="top" class="netdisk-cdkeys__form">
        <el-row :gutter="16">
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="绑定账户">
              <el-select v-model="form.accountId" placeholder="选择网盘账号">
                <el-option
                  v-for="item in accountOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                  :disabled="item.disabled"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="12" :md="4">
            <el-form-item label="授权天数">
              <el-input-number v-model="form.days" :min="1" :max="3650" />
            </el-form-item>
          </el-col>
          <el-col :xs="12" :md="4">
            <el-form-item label="生成数量">
              <el-input-number v-model="form.count" :min="1" :max="100" />
            </el-form-item>
          </el-col>
          <el-col :xs="12" :md="4">
            <el-form-item label="授权次数">
              <el-input-number v-model="form.maxUses" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :xs="12" :md="4" class="netdisk-cdkeys__submit-col">
            <el-button
              type="primary"
              :loading="generating"
              :disabled="!form.accountId"
              @click="handleGenerate"
            >
              立即生成
            </el-button>
          </el-col>
        </el-row>
      </el-form>

      <el-alert type="info" :closable="false" style="margin-top: 12px">
        <template #default>
          <span style="font-size: 13px">
            兑换接口地址：
            <el-tag size="small" style="font-family: monospace; margin: 0 4px">
              GET {{ currentOrigin }}/netdisk/redeem?code=卡密串码
            </el-tag>
            返回对应账号的 Cookie 及授权天数
          </span>
        </template>
      </el-alert>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="netdisk-cdkeys__header">
          <span>卡密库存管理</span>
          <el-space wrap>
            <el-select
              v-model="filterAccount"
              placeholder="筛选网盘账号"
              clearable
              style="width: 180px"
            >
              <el-option
                v-for="item in filterAccountOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-select
              v-model="filterStatus"
              placeholder="筛选状态"
              clearable
              style="width: 120px"
            >
              <el-option
                v-for="item in statusOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-button @click="loadKeys">刷新列表</el-button>
            <el-button type="warning" plain @click="confirmCleanExpired">
              清理过期/作废卡密
            </el-button>
          </el-space>
        </div>
      </template>

      <el-table :data="filteredAndSortedTableData" stripe v-loading="loading">
        <el-table-column label="卡密串码" min-width="180">
          <template #default="{ row }">
            <span class="netdisk-cdkeys__code">{{ row.key_code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="绑定账号" min-width="160">
          <template #default="{ row }">
            {{ resolveAccountName(row.account_id) }}
          </template>
        </el-table-column>
        <el-table-column label="授权天数" width="120">
          <template #default="{ row }">{{ row.duration }} 天</template>
        </el-table-column>
        <el-table-column label="授权次数" width="140">
          <template #default="{ row }">
            {{ row.use_count || 0 }} / {{ row.max_uses > 0 ? row.max_uses : '不限' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="resolveStatusType(row.status)">
              {{ statusMap[row.status]?.label || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="240" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button size="small" text type="primary" @click="copyCode(row.key_code)">
                复制
              </el-button>
              <el-button
                size="small"
                text
                type="primary"
                :disabled="row.status === 2"
                @click="copyRedeemUrl(row.key_code)"
              >
                兑换链接
              </el-button>
              <el-button
                size="small"
                text
                type="success"
                :disabled="row.status === 2"
                @click="openRedeemUrl(row.key_code)"
              >
                打开页面
              </el-button>
              <el-button
                size="small"
                text
                type="danger"
                :disabled="row.status === 2"
                @click="confirmVoid(row)"
              >
                作废
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { baiduApi } from '@/api/baidu'

const loading = ref(false)
const generating = ref(false)
const tableData = ref([])
const accounts = ref([])

const currentOrigin =
  typeof window !== 'undefined' ? window.location.origin : ''

const resolveRedeemUrl = (code) =>
  `${currentOrigin}/netdisk/redeem?code=${encodeURIComponent(code)}`

const form = ref({ accountId: null, days: 30, count: 10, maxUses: 0 })

const filterAccount = ref(null)
const filterStatus = ref(null)

const accountOptions = computed(() =>
  accounts.value.map((a) => ({
    label: `${a.username}（${a.vip_level}）`,
    value: a.id,
    disabled: a.status !== 1,
  })),
)

const filterAccountOptions = computed(() =>
  accounts.value.map((a) => ({
    label: `${a.username}（${a.vip_level}）`,
    value: a.id,
  })),
)

const statusOptions = [
  { label: '未使用', value: 0 },
  { label: '已授权', value: 1 },
  { label: '已作废', value: 2 },
]

const filteredAndSortedTableData = computed(() => {
  let data = [...tableData.value]
  
  // 1. 筛选网盘账号
  if (filterAccount.value !== null) {
    data = data.filter((item) => item.account_id === filterAccount.value)
  }
  
  // 2. 筛选状态
  if (filterStatus.value !== null) {
    data = data.filter((item) => item.status === filterStatus.value)
  }
  
  // 3. 排序：未使用排在前面，已授权和报废排后面；同状态下最新的卡密在前
  data.sort((a, b) => {
    if (a.status !== b.status) {
      return a.status - b.status
    }
    return b.id - a.id
  })
  
  return data
})

// ── 状态映射 ─────────────────────────────────────────────────
const statusMap = {
  0: { label: '未使用', type: 'success' },
  1: { label: '已授权', type: 'warning' },
  2: { label: '已作废', type: 'danger' },
}

// ── 方法 ───────────────────────────────────────────────────
const loadAccounts = async () => {
  const res = await baiduApi.getAccounts()
  accounts.value = res.data || []
}

const resolveAccountName = (accountId) => {
  const acc = accounts.value.find((item) => item.id === accountId)
  return acc ? acc.username : '—'
}

const resolveStatusType = (status) =>
  statusMap[status]?.type === 'danger' ? 'danger' : statusMap[status]?.type || 'info'

const loadKeys = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getCdKeys()
    tableData.value = res.data || []
  } catch {
    ElMessage.error('获取卡密列表失败')
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (!form.value.accountId) return ElMessage.warning('请先选择绑定账户')
  generating.value = true
  try {
    await baiduApi.generateCdKeys(
      form.value.accountId,
      form.value.count,
      form.value.days,
      form.value.maxUses,
    )
    ElMessage.success(`成功生成 ${form.value.count} 张卡密`)
    loadKeys()
  } catch {
    ElMessage.error('生成失败，请重试')
  } finally {
    generating.value = false
  }
}

const handleVoid = async (row) => {
  try {
    await baiduApi.deleteCdKey(row.id)
    ElMessage.success('卡密已作废')
    loadKeys()
  } catch {
    ElMessage.error('操作失败')
  }
}

const confirmVoid = async (row) => {
  try {
    await ElMessageBox.confirm('确认作废该卡密？操作不可撤销。', '作废确认', {
      type: 'warning',
    })
    await handleVoid(row)
  } catch {
    // User cancelled.
  }
}

const copyCode = async (code) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(code)
    } else {
      fallbackCopy(code)
    }
    ElMessage.success('卡密已复制')
  } catch (err) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const copyRedeemUrl = async (code) => {
  const url = resolveRedeemUrl(code)
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      fallbackCopy(url)
    }
    ElMessage.success('兑换链接已复制')
  } catch (err) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const openRedeemUrl = (code) => {
  window.open(resolveRedeemUrl(code), '_blank', 'noopener')
}

const fallbackCopy = (text) => {
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-999999px'
  textArea.style.top = '-999999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  try {
    document.execCommand('copy')
  } catch (err) {
    console.error('fallback copy failed', err)
  }
  document.body.removeChild(textArea)
}

const handleCleanExpired = async () => {
  try {
    const res = await baiduApi.cleanExpiredKeys()
    ElMessage.success(res.data.msg || '清理成功')
    loadKeys()
  } catch (e) {
    ElMessage.error('清理失败')
  }
}

const confirmCleanExpired = async () => {
  try {
    await ElMessageBox.confirm(
      '确认要清理并彻底删除所有已经过期或作废的卡密吗？操作不可逆。',
      '清理确认',
      { type: 'warning' },
    )
    await handleCleanExpired()
  } catch {
    // User cancelled.
  }
}

onMounted(() => {
  loadAccounts()
  loadKeys()
})
</script>

<style scoped>
.netdisk-cdkeys {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
}

.netdisk-cdkeys__form :deep(.el-input-number),
.netdisk-cdkeys__form :deep(.el-select) {
  width: 100%;
}

.netdisk-cdkeys__submit-col {
  display: flex;
  align-items: flex-end;
}

.netdisk-cdkeys__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.netdisk-cdkeys__code {
  font-family: monospace;
}

@media (max-width: 960px) {
  .netdisk-cdkeys__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
