<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="lastUpdatedText"
  >
    <template #actions>
      <n-space>
        <n-button secondary :loading="loading" @click="loadPage">刷新列表</n-button>
      </n-space>
    </template>

    <n-card title="批量生成卡密" size="small" class="cdkey-generate-card">
      <n-alert
        v-if="!accountOptions.length"
        type="warning"
        :show-icon="false"
        class="cdkey-card-alert"
      >
        当前还没有可用的聚点账号，请先去“账户登录”页面完成真实账号登录。
      </n-alert>
      <n-alert v-else type="info" :show-icon="false" class="cdkey-card-alert">
        以下卡密数据直接写入聚点真实数据库；生成后会立即出现在库存列表，并可用于后续兑换流程。
      </n-alert>

      <n-form label-placement="top" :show-feedback="false" class="cdkey-generate-form">
        <div class="cdkey-generate-grid">
          <n-form-item label="卡密规格" class="cdkey-generate-field cdkey-generate-field--spec">
            <div class="cdkey-spec-picker">
              <n-space size="small" wrap>
                <n-button
                  v-for="item in specOptions"
                  :key="item.value"
                  size="small"
                  :type="activeSpecPreset === item.value ? 'primary' : 'default'"
                  :secondary="activeSpecPreset === item.value"
                  @click="applySpecPreset(item)"
                >
                  {{ item.label }}
                </n-button>
              </n-space>
              <span class="cdkey-spec-picker__hint">按 5 钻 = 1 天自动换算，可继续手动微调</span>
            </div>
          </n-form-item>
          <n-form-item label="绑定账户" class="cdkey-generate-field cdkey-generate-field--account">
            <n-select
              v-model:value="form.accountId"
              :options="accountOptions"
              placeholder="请选择聚点账号"
            />
          </n-form-item>
          <n-form-item label="授权天数" class="cdkey-generate-field cdkey-generate-field--number">
            <n-input-number
              v-model:value="form.duration"
              :min="1"
              :max="365"
              style="width: 100%"
              @update:value="handleDurationChange"
            />
          </n-form-item>
          <n-form-item label="生成数量" class="cdkey-generate-field cdkey-generate-field--number">
            <n-input-number v-model:value="form.count" :min="1" :max="50" style="width: 100%" />
          </n-form-item>
          <n-form-item
            label="使用额度（钻石）"
            class="cdkey-generate-field cdkey-generate-field--number"
          >
            <n-input-number v-model:value="form.maxUses" :min="0" style="width: 100%" />
          </n-form-item>
          <n-form-item label="备注" class="cdkey-generate-field cdkey-generate-field--remark">
            <n-input v-model:value="form.remark" placeholder="例如：直播间活动" />
          </n-form-item>
        </div>

        <div class="cdkey-generate-actions">
          <div class="cdkey-generate-actions__inner">
            <n-button size="small" @click="resetForm">重置</n-button>
            <n-button
              size="small"
              type="primary"
              :loading="generating"
              :disabled="!accountOptions.length"
              @click="handleGenerate"
            >
              立即生成
            </n-button>
          </div>
        </div>
      </n-form>
    </n-card>

    <n-card title="卡密库存管理" size="small">
      <template #header-extra>
        <n-space>
          <n-select
            v-model:value="exportSpec"
            :options="exportSpecOptions"
            placeholder="导出规格"
            style="width: 200px"
          />
          <n-button type="primary" secondary @click="handleExportUnusedCodesBySpec"
            >导出原卡密</n-button
          >
          <n-button type="info" secondary @click="handleExportUnusedRedeemUrlsBySpec"
            >导出访问卡密</n-button
          >
          <n-select
            v-model:value="filterAccount"
            :options="filterAccountOptions"
            placeholder="筛选账户"
            clearable
            style="width: 180px"
          />
          <n-select
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="筛选状态"
            clearable
            style="width: 140px"
          />
          <n-popconfirm @positive-click="handleCleanInactive">
            <template #trigger>
              <n-button type="warning" secondary>清理过期/作废卡密</n-button>
            </template>
            确认要清理所有已过期或已作废的真实卡密吗？
          </n-popconfirm>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="filteredRows"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        :bordered="false"
      />
    </n-card>
  </JudianPageLayout>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NPopconfirm, NProgress, NSpace, NTag, useMessage } from 'naive-ui'

import { judianApi } from '@/api/judian'
import JudianPageLayout from '@/components/judian/PageLayout.vue'
import { getJudianSectionMeta } from '@/views/judian/shared/page-meta'

const LEGACY_MOCK_STORAGE_KEY = 'judian_frontend_mock_state_v1'
const DIAMONDS_PER_DAY = 5
const PUBLIC_REDEEM_ORIGIN = 'https://www.woshishabi.xyz'
const specOptions = [
  { label: '天卡', value: 'day', duration: 1 },
  { label: '周卡', value: 'week', duration: 7 },
  { label: '月卡', value: 'month', duration: 30 },
  { label: '季卡', value: 'season', duration: 90 },
  { label: '年卡', value: 'year', duration: 365 },
].map((item) => ({
  ...item,
  maxUses: item.duration * DIAMONDS_PER_DAY,
}))

const message = useMessage()
const sectionMeta = getJudianSectionMeta('cdkeys')
const loading = ref(false)
const generating = ref(false)
const accounts = ref([])
const cdkeys = ref([])
const lastUpdatedText = ref('')
const exportSpec = ref('month')
const filterAccount = ref(null)
const filterStatus = ref(null)

const form = reactive({
  accountId: null,
  duration: 1,
  count: 10,
  maxUses: 5,
  remark: '',
})

const statusMap = {
  unused: { label: '待领取', type: 'success' },
  active: { label: '已领取', type: 'warning' },
  expired: { label: '已过期', type: 'error' },
  void: { label: '已作废', type: 'default' },
}

const accountOptions = computed(() =>
  accounts.value
    .filter((item) => item.enabled)
    .map((item) => ({
      label: `${item.displayName}（${item.accountId}）`,
      value: item.accountId,
    })),
)

const filterAccountOptions = computed(() =>
  accounts.value.map((item) => ({
    label: `${item.displayName}（${item.accountId}）`,
    value: item.accountId,
  })),
)

const statusOptions = Object.entries(statusMap).map(([value, item]) => ({
  label: item.label,
  value,
}))

const exportSpecOptions = computed(() =>
  specOptions.map((item) => {
    const count = cdkeys.value.filter(
      (row) => row.status === 'unused' && matchesSpecPreset(row, item),
    ).length
    return {
      label: `${item.label}（${count} 张）`,
      value: item.value,
    }
  }),
)

const activeSpecPreset = computed(() => {
  const duration = Number(form.duration || 0)
  const maxUses = Number(form.maxUses || 0)
  return (
    specOptions.find((item) => item.duration === duration && item.maxUses === maxUses)?.value ||
    null
  )
})

const filteredRows = computed(() =>
  cdkeys.value.filter((item) => {
    if (filterAccount.value && item.accountId !== filterAccount.value) return false
    if (filterStatus.value && item.status !== filterStatus.value) return false
    return true
  }),
)

const stats = computed(() => {
  const rows = cdkeys.value || []
  const available = rows.filter((item) => ['unused', 'active'].includes(item.status)).length
  const invalid = rows.filter((item) => ['expired', 'void'].includes(item.status)).length
  const boundAccounts = new Set(rows.map((item) => item.accountId).filter(Boolean)).size

  return [
    { label: '卡密总数', value: String(rows.length), help: '当前数据库中的聚点卡密库存数量' },
    { label: '可用卡密', value: String(available), help: '待领取或已领取状态的真实卡密数量' },
    { label: '失效卡密', value: String(invalid), help: '已过期或已作废、建议清理的真实卡密' },
    { label: '绑定账号', value: String(boundAccounts), help: '当前卡密已经覆盖到的聚点账号数量' },
  ]
})

const columns = [
  {
    title: '卡密串码',
    key: 'code',
    width: 180,
    render: (row) => h('span', { style: 'font-family: monospace; font-weight: 600' }, row.code),
  },
  {
    title: '绑定账号',
    key: 'accountId',
    width: 180,
    render: (row) => resolveAccountName(row.accountId),
  },
  {
    title: '授权天数',
    key: 'duration',
    width: 120,
    render: (row) => {
      const specLabel = resolveSpecLabel(row.duration)
      return specLabel ? `${specLabel} · ${row.duration} 天` : `${row.duration} 天`
    },
  },
  {
    title: '已使用进度',
    key: 'usage',
    width: 220,
    render: (row) => {
      const usage = resolveUsageProgress(row)
      if (usage.unlimited) {
        return h('div', { class: 'cdkey-usage-progress' }, [
          h('div', { class: 'cdkey-usage-progress__summary' }, usage.summary),
          h('div', { class: 'cdkey-usage-progress__meta' }, usage.meta),
        ])
      }
      return h('div', { class: 'cdkey-usage-progress' }, [
        h('div', { class: 'cdkey-usage-progress__summary' }, usage.summary),
        h(NProgress, {
          type: 'line',
          percentage: usage.percentage,
          height: 14,
          borderRadius: 3,
          showIndicator: false,
          status: usage.status,
          railStyle: { background: 'rgba(255,255,255,0.08)' },
        }),
        h('div', { class: 'cdkey-usage-progress__meta' }, usage.meta),
      ])
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) =>
      h(
        NTag,
        { type: statusMap[row.status]?.type || 'default', bordered: false, size: 'small' },
        { default: () => statusMap[row.status]?.label || '未知' },
      ),
  },
  { title: '创建时间', key: 'createdAt', width: 180 },
  { title: '备注', key: 'remark' },
  {
    title: '操作',
    key: 'actions',
    width: 280,
    render: (row) =>
      h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'info',
                onClick: () => copyCode(row.code),
              },
              { default: () => '复制' },
            ),
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'primary',
                onClick: () => copyRedeemUrl(row.code),
              },
              { default: () => '兑换链接' },
            ),
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'success',
                onClick: () => previewRedeem(row.code),
              },
              { default: () => '打开页面' },
            ),
            h(
              NPopconfirm,
              { onPositiveClick: () => handleVoid(row) },
              {
                trigger: () =>
                  h(
                    NButton,
                    {
                      size: 'small',
                      quaternary: true,
                      type: 'error',
                      disabled: row.status === 'void',
                    },
                    { default: () => '作废' },
                  ),
                default: () => `确认作废卡密 ${row.code}？`,
              },
            ),
          ],
        },
      ),
  },
]

function cleanupLegacyMockStorage() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(LEGACY_MOCK_STORAGE_KEY)
}

function extractErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    '请求失败，请稍后重试'
  )
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

function resolveAccountName(accountId) {
  const target = accounts.value.find((item) => item.accountId === accountId)
  return target ? `${target.displayName}（${target.accountId}）` : accountId || '—'
}

function resolveRedeemUrl(code) {
  return `${PUBLIC_REDEEM_ORIGIN}/judian/redeem?code=${code}`
}

function resolveSpecLabel(duration) {
  const matched = specOptions.find((item) => item.duration === Number(duration || 0))
  return matched?.label || ''
}

function matchesSpecPreset(row, spec) {
  return (
    Number(row?.duration || 0) === Number(spec?.duration || 0) &&
    Number(row?.maxUses || 0) === Number(spec?.maxUses || 0)
  )
}

function calculateMaxUsesByDuration(duration) {
  return Math.max(0, Number(duration || 0)) * DIAMONDS_PER_DAY
}

function applySpecPreset(item) {
  form.duration = item.duration
  form.maxUses = item.maxUses
}

function handleDurationChange(value) {
  const duration = Math.max(1, Number(value || 1))
  form.duration = duration
  form.maxUses = calculateMaxUsesByDuration(duration)
}

function resolveUsageProgress(row) {
  const maxUses = Math.max(0, Number(row.maxUses || 0))
  const used = Math.max(0, Number(row.useCount || 0))
  if (maxUses <= 0) {
    return {
      unlimited: true,
      summary: `已使用 ${used} 钻`,
      meta: '总额度：不限',
    }
  }
  const remaining = Math.max(0, maxUses - used)
  const percentage = Math.max(0, Math.min(100, Math.round((used / maxUses) * 100)))
  return {
    unlimited: false,
    percentage,
    summary: `${used} / ${maxUses} 钻`,
    meta: `剩余 ${remaining} 钻`,
    status: percentage >= 100 ? 'error' : percentage >= 80 ? 'warning' : 'success',
  }
}

function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function buildExportFilename(spec) {
  const dateText = new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')
  return `聚点未使用卡密_${spec.label}_${spec.duration}天_${dateText}.txt`
}

function buildRedeemExportFilename(spec) {
  const dateText = new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')
  return `聚点访问卡密_${spec.label}_${spec.duration}天_${dateText}.txt`
}

function getUnusedRowsBySpec() {
  const spec = specOptions.find((item) => item.value === exportSpec.value)
  if (!spec) {
    message.warning('请选择要导出的规格')
    return null
  }
  const rows = cdkeys.value.filter((row) => row.status === 'unused' && matchesSpecPreset(row, spec))
  if (!rows.length) {
    message.warning(`暂无可导出的${spec.label}未使用卡密`)
    return null
  }
  return { spec, rows }
}

function resetForm() {
  form.accountId = accountOptions.value[0]?.value || null
  form.duration = 1
  form.count = 10
  form.maxUses = 5
  form.remark = ''
}

async function loadPage() {
  loading.value = true
  try {
    cleanupLegacyMockStorage()
    const [accountsResponse, cdkeysResponse] = await Promise.all([
      judianApi.listAccounts(),
      judianApi.listCdKeys(),
    ])
    accounts.value = Array.isArray(accountsResponse?.data?.items) ? accountsResponse.data.items : []
    cdkeys.value = Array.isArray(cdkeysResponse?.data?.items) ? cdkeysResponse.data.items : []
    const latestCandidates = [
      cdkeys.value[0]?.updatedAt,
      cdkeys.value[0]?.createdAt,
      accounts.value[0]?.updatedAt,
      accounts.value[0]?.lastLoginAt,
    ]
      .filter(Boolean)
      .sort()
    lastUpdatedText.value = latestCandidates.at(-1) || '暂无数据'
    if (!form.accountId && accountOptions.value.length) {
      form.accountId = accountOptions.value[0].value
    }
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  if (!form.accountId) {
    message.warning('请先选择绑定账号')
    return
  }
  generating.value = true
  try {
    const { data } = await judianApi.generateCdKeys({
      accountId: form.accountId,
      duration: form.duration,
      count: form.count,
      maxUses: form.maxUses,
      remark: form.remark,
    })
    await loadPage()
    resetForm()
    message.success(data?.message || `已生成 ${data?.total || 0} 张聚点卡密`)
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    generating.value = false
  }
}

function handleExportUnusedCodesBySpec() {
  const result = getUnusedRowsBySpec()
  if (!result) {
    return
  }
  const { spec, rows } = result
  const content = rows
    .map((row) => row.code)
    .filter(Boolean)
    .join('\n')
  downloadTextFile(content, buildExportFilename(spec))
  message.success(`已导出 ${rows.length} 张${spec.label}原卡密`)
}

function handleExportUnusedRedeemUrlsBySpec() {
  const result = getUnusedRowsBySpec()
  if (!result) {
    return
  }
  const { spec, rows } = result
  const content = rows
    .map((row) => row.code)
    .filter(Boolean)
    .map((code) => resolveRedeemUrl(code))
    .join('\n')
  downloadTextFile(content, buildRedeemExportFilename(spec))
  message.success(`已导出 ${rows.length} 条${spec.label}访问卡密链接`)
}

async function copyCode(code) {
  await copyText(code)
  message.success('卡密已复制')
}

async function copyRedeemUrl(code) {
  await copyText(resolveRedeemUrl(code))
  message.success('兑换链接已复制')
}

async function previewRedeem(code) {
  window.open(resolveRedeemUrl(code), '_blank', 'noopener')
}

async function handleVoid(row) {
  try {
    await judianApi.updateCdKey(row.id, { status: 'void' })
    await loadPage()
    message.success('卡密已作废')
  } catch (error) {
    message.error(extractErrorMessage(error))
  }
}

async function handleCleanInactive() {
  try {
    const { data } = await judianApi.cleanInactiveCdKeys()
    await loadPage()
    message.success(data?.message || `已清理 ${data?.removed || 0} 张失效卡密`)
  } catch (error) {
    message.error(extractErrorMessage(error))
  }
}

onMounted(loadPage)
</script>

<style scoped>
.cdkey-generate-card,
.cdkey-table-card {
  border-radius: 14px;
}

.cdkey-card-alert {
  margin-bottom: 12px;
}

.cdkey-generate-form :deep(.n-form-item) {
  margin-bottom: 0;
}

.cdkey-generate-form :deep(.n-form-item-label) {
  padding-bottom: 6px;
}

.cdkey-generate-grid {
  display: grid;
  grid-template-columns: minmax(260px, 2.3fr) repeat(3, minmax(92px, 0.82fr)) minmax(180px, 1.2fr);
  column-gap: 12px;
  row-gap: 8px;
  align-items: end;
}

.cdkey-generate-field {
  min-width: 0;
}

.cdkey-generate-field--spec {
  grid-column: 1 / -1;
}

.cdkey-spec-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cdkey-spec-picker__hint {
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  line-height: 1.4;
}

.cdkey-generate-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.cdkey-generate-actions__inner {
  display: inline-flex;
  gap: 10px;
  flex-wrap: wrap;
}

.cdkey-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.cdkey-table-card :deep(.n-card-header) {
  padding-bottom: 12px;
}

.cdkey-table :deep(.n-data-table-th),
.cdkey-table :deep(.n-data-table-td) {
  padding-top: 10px;
  padding-bottom: 10px;
}

.cdkey-usage-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cdkey-usage-progress__summary {
  font-weight: 600;
}

.cdkey-usage-progress__meta {
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  line-height: 1.4;
}

@media (max-width: 1400px) {
  .cdkey-generate-grid {
    grid-template-columns:
      minmax(220px, 1.9fr) repeat(2, minmax(96px, 0.95fr)) minmax(96px, 0.95fr)
      minmax(160px, 1.15fr);
  }
}

@media (max-width: 1100px) {
  .cdkey-generate-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cdkey-generate-field--account,
  .cdkey-generate-field--remark {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .cdkey-generate-grid {
    grid-template-columns: 1fr;
  }

  .cdkey-generate-field--account,
  .cdkey-generate-field--remark {
    grid-column: auto;
  }

  .cdkey-generate-actions,
  .cdkey-toolbar {
    justify-content: flex-start;
  }

  .cdkey-generate-actions__inner {
    width: 100%;
  }
}
</style>
