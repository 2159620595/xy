<template>
  <n-space vertical size="large" style="padding: 24px">
    <!-- 生成卡密 -->
    <n-card title="批量生成卡密">
      <n-form :model="form" label-placement="left" label-width="80px">
        <n-grid :cols="5" :x-gap="16">
          <n-form-item-gi label="绑定账户">
            <n-select
              v-model:value="form.accountId"
              :options="accountOptions"
              placeholder="选择网盘账号"
              style="min-width: 180px"
            />
          </n-form-item-gi>
          <n-form-item-gi label="授权天数">
            <n-input-number v-model:value="form.days" :min="1" :max="3650" />
          </n-form-item-gi>
          <n-form-item-gi label="生成数量">
            <n-input-number v-model:value="form.count" :min="1" :max="100" />
          </n-form-item-gi>
          <n-form-item-gi label="授权次数">
            <n-input-number v-model:value="form.maxUses" :min="0" placeholder="0=不限" />
          </n-form-item-gi>
          <n-form-item-gi>
            <n-button
              type="primary"
              :loading="generating"
              :disabled="!form.accountId"
              @click="handleGenerate"
            >
              立即生成
            </n-button>
          </n-form-item-gi>
        </n-grid>
      </n-form>

      <!-- 兑换地址说明 -->
      <n-alert type="info" style="margin-top: 12px" :show-icon="false">
        <span style="font-size: 13px">
          兑换接口地址：
          <n-tag size="small" style="font-family: monospace; margin: 0 4px">
            GET {{ currentOrigin }}/netdisk/redeem?code=卡密串码
          </n-tag>
          返回对应账号的 Cookie 及授权天数
        </span>
      </n-alert>
    </n-card>

    <!-- 卡密列表 -->
    <n-card title="卡密库存管理">
      <template #header-extra>
        <n-space>
          <n-select
            v-model:value="filterAccount"
            :options="filterAccountOptions"
            placeholder="筛选网盘账号"
            style="width: 180px"
            clearable
          />
          <n-select
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="筛选状态"
            style="width: 120px"
            clearable
          />
          <n-button @click="loadKeys" secondary>刷新列表</n-button>
          <n-popconfirm @positive-click="handleCleanExpired">
            <template #trigger>
              <n-button type="warning" secondary>清理过期/作废卡密</n-button>
            </template>
            确认要清理并彻底删除所有已经过期或作废的卡密吗？操作不可逆。
          </n-popconfirm>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="filteredAndSortedTableData"
        :loading="loading"
        :pagination="{ pageSize: 15 }"
      />
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, h, computed, onMounted } from 'vue'
import { NTag, NButton, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { baiduApi } from '@/api/baidu'

const message = useMessage()
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
  2: { label: '已作废', type: 'error' },
}

// ── 表格列 ──────────────────────────────────────────────────
const columns = [
  {
    title: '卡密串码',
    key: 'key_code',
    align: 'center',
    render: (r) => h('span', { style: 'font-family:monospace' }, r.key_code),
  },
  {
    title: '绑定账号',
    key: 'account_id',
    align: 'center',
    render: (r) => {
      const acc = accounts.value.find((a) => a.id === r.account_id)
      return acc ? acc.username : '—'
    },
  },
  { title: '授权天数', key: 'duration', align: 'center', render: (r) => `${r.duration} 天` },
  {
    title: '授权次数',
    key: 'usage',
    align: 'center',
    render: (r) => {
      const max = r.max_uses > 0 ? r.max_uses : '不限'
      const cur = r.use_count || 0
      return `${cur} / ${max}`
    }
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render: (r) => {
      const s = statusMap[r.status] || { label: '未知', type: 'default' }
      return h(NTag, { type: s.type, bordered: false, size: 'small' }, { default: () => s.label })
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render: (r) =>
      h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            // 复制卡密
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'info',
                onClick: () => copyCode(r.key_code),
              },
              { default: () => '复制' },
            ),
            // 复制兑换链接
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'primary',
                disabled: r.status === 2,
                onClick: () => copyRedeemUrl(r.key_code),
              },
              { default: () => '兑换链接' },
            ),
            // 跳转按钮
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'success',
                disabled: r.status === 2,
                onClick: () => window.open(resolveRedeemUrl(r.key_code), '_blank'),
              },
              { default: () => '打开页面' },
            ),
            // 作废（带确认）
            h(
              NPopconfirm,
              { onPositiveClick: () => handleVoid(r) },
              {
                trigger: () =>
                  h(
                    NButton,
                    {
                      size: 'small',
                      quaternary: true,
                      type: 'error',
                      disabled: r.status === 2,
                    },
                    { default: () => '作废' },
                  ),
                default: () => '确认作废该卡密？操作不可撤销',
              },
            ),
          ],
        },
      ),
  },
]

// ── 方法 ───────────────────────────────────────────────────
const loadAccounts = async () => {
  const res = await baiduApi.getAccounts()
  accounts.value = res.data || []
}

const loadKeys = async () => {
  loading.value = true
  try {
    const res = await baiduApi.getCdKeys()
    tableData.value = res.data || []
  } catch {
    message.error('获取卡密列表失败')
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (!form.value.accountId) return message.warning('请先选择绑定账户')
  generating.value = true
  try {
    await baiduApi.generateCdKeys(
      form.value.accountId,
      form.value.count,
      form.value.days,
      form.value.maxUses,
    )
    message.success(`成功生成 ${form.value.count} 张卡密`)
    loadKeys()
  } catch {
    message.error('生成失败，请重试')
  } finally {
    generating.value = false
  }
}

const handleVoid = async (row) => {
  try {
    await baiduApi.deleteCdKey(row.id)
    message.success('卡密已作废')
    loadKeys()
  } catch {
    message.error('操作失败')
  }
}

const copyCode = async (code) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(code)
    } else {
      fallbackCopy(code)
    }
    message.success('卡密已复制')
  } catch (err) {
    message.error('复制失败，请手动复制')
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
    message.success('兑换链接已复制')
  } catch (err) {
    message.error('复制失败，请手动复制')
  }
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
    message.success(res.data.msg || '清理成功')
    loadKeys()
  } catch (e) {
    message.error('清理失败')
  }
}

onMounted(() => {
  loadAccounts()
  loadKeys()
})
</script>
