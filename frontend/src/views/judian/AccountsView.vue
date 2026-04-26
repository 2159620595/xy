<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="lastUpdatedText"
  >
    <template #actions>
      <n-space>
        <n-button secondary :loading="loading" @click="loadAccounts">刷新列表</n-button>
      </n-space>
    </template>

    <n-card title="登录聚点账号" size="small">
      <n-alert type="info" :show-icon="false" style="margin-bottom: 16px">
        当前已接入真实后端。提交邮箱和密码后，会按聚点安卓端协议登录远端，并同步会话 Token、UserSig 与钻石余额。
      </n-alert>

      <n-form label-placement="top" :show-feedback="false">
        <n-grid :cols="24" :x-gap="16">
          <n-form-item-gi :span="9" label="登录邮箱">
            <n-input v-model:value="form.loginEmail" placeholder="请输入聚点登录邮箱" @keyup.enter="submitLogin" />
          </n-form-item-gi>
          <n-form-item-gi :span="7" label="登录密码">
            <n-input
              v-model:value="form.loginPassword"
              type="password"
              show-password-on="click"
              placeholder="请输入登录密码"
              @keyup.enter="submitLogin"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="4" label="显示名称">
            <n-input v-model:value="form.displayName" placeholder="可选" />
          </n-form-item-gi>
          <n-form-item-gi :span="4" label="备注">
            <n-input v-model:value="form.remark" placeholder="可选" />
          </n-form-item-gi>
        </n-grid>

        <n-space justify="end">
          <n-button @click="resetForm">清空</n-button>
          <n-button type="primary" :loading="submitting" @click="submitLogin">账号密码登录</n-button>
        </n-space>
      </n-form>
    </n-card>

    <n-card title="账号池管理" size="small">
      <n-data-table
        :columns="columns"
        :data="accounts"
        :loading="loading"
        :pagination="{ pageSize: 8 }"
        :bordered="false"
      />
    </n-card>
  </JudianPageLayout>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NPopconfirm, NSpace, NSwitch, NTag, useMessage } from 'naive-ui'

import { judianApi } from '@/api/judian'
import JudianPageLayout from '@/components/judian/PageLayout.vue'
import { getJudianSectionMeta } from '@/views/judian/shared/page-meta'

const message = useMessage()
const sectionMeta = getJudianSectionMeta('accounts')
const loading = ref(false)
const submitting = ref(false)
const reloginId = ref(null)
const accounts = ref([])
const lastUpdatedText = ref('')

const form = reactive({
  loginEmail: '',
  loginPassword: '',
  displayName: '',
  remark: '',
})

const statusMap = {
  active: { label: '活跃', type: 'success' },
  pending: { label: '待登录', type: 'warning' },
  disabled: { label: '已停用', type: 'default' },
}

const stats = computed(() => {
  const rows = accounts.value
  return [
    { label: '账号总数', value: String(rows.length), help: '当前聚点账号池中的账号总数' },
    { label: '活跃会话', value: String(rows.filter((item) => item.status === 'active' && item.sessionToken).length), help: '已成功登录并拿到远端会话的账号数' },
    { label: '启用账号', value: String(rows.filter((item) => item.enabled).length), help: '当前允许继续发卡与解锁的聚点账号数' },
    { label: '总钻石', value: String(rows.reduce((sum, item) => sum + Number(item.diamondQuantity || 0), 0)), help: '账号池同步回来的钻石余额总和' },
  ]
})

const columns = [
  { title: '账号 ID', key: 'accountId', width: 120 },
  { title: '显示名称', key: 'displayName', width: 160 },
  {
    title: '登录邮箱',
    key: 'loginEmail',
    width: 220,
    render: (row) => maskText(row.loginEmail, 3, 9),
  },
  {
    title: '钻石数量',
    key: 'diamondQuantity',
    width: 120,
    render: (row) => h('span', { style: 'font-weight: 600; color: #2563eb' }, Number(row.diamondQuantity || 0)),
  },
  { title: '钻石刷新', key: 'diamondQuantityUpdatedAt', width: 180 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(
      NTag,
      { type: statusMap[row.status]?.type || 'default', bordered: false, size: 'small' },
      { default: () => statusMap[row.status]?.label || '未知' },
    ),
  },
  { title: '最近登录', key: 'lastLoginAt', width: 180 },
  {
    title: 'Session Token',
    key: 'sessionToken',
    width: 220,
    render: (row) => maskText(row.sessionToken, 6, 6),
  },
  {
    title: 'UserSig',
    key: 'userSig',
    width: 180,
    render: (row) => maskText(row.userSig, 6, 6),
  },
  {
    title: '启用',
    key: 'enabled',
    width: 90,
    render: (row) => h(NSwitch, {
      value: resolveEnabledDraft(row),
      disabled: Boolean(row._enabledSaving),
      'onUpdate:value': (value) => updateEnabledDraft(row, value),
    }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 420,
    render: (row) => h(
      NSpace,
      { justify: 'center', size: 8, wrap: true },
      {
        default: () => [
          hasEnabledDraftChanged(row)
            ? h(NTag, { size: 'small', type: 'warning', bordered: false }, { default: () => '待保存' })
            : null,
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              secondary: true,
              disabled: !hasEnabledDraftChanged(row),
              loading: Boolean(row._enabledSaving),
              onClick: () => saveEnabledDraft(row),
            },
            { default: () => '保存启用' },
          ),
          h(
            NButton,
            {
              size: 'small',
              disabled: !hasEnabledDraftChanged(row) || Boolean(row._enabledSaving),
              onClick: () => resetEnabledDraft(row),
            },
            { default: () => '撤销' },
          ),
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'primary',
              loading: reloginId.value === row.id,
              disabled: Boolean(row._enabledSaving),
              onClick: () => handleRelogin(row),
            },
            { default: () => '账密登录' },
          ),
          h(
            NPopconfirm,
            { onPositiveClick: () => handleDelete(row) },
            {
              trigger: () => h(
                NButton,
                { size: 'small', quaternary: true, type: 'error', disabled: Boolean(row._enabledSaving) },
                { default: () => '删除' },
              ),
              default: () => `确认删除账号 ${row.displayName}？`,
            },
          ),
        ].filter(Boolean),
      },
    ),
  },
]

function looksLikeEmail(value) {
  return /^\S+@\S+\.\S+$/.test(String(value || '').trim())
}

function maskText(value, prefix = 4, suffix = 4) {
  const text = String(value || '').trim()
  if (!text) return '—'
  if (text.length <= prefix + suffix) return text
  return `${text.slice(0, prefix)}***${text.slice(-suffix)}`
}

function extractErrorMessage(error) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || '请求失败，请稍后重试'
}

function resolveEnabledDraft(row) {
  return row?._draftEnabled ?? Boolean(row?.enabled)
}

function hasEnabledDraftChanged(row) {
  return resolveEnabledDraft(row) !== Boolean(row?.enabled)
}

function updateEnabledDraft(row, value) {
  row._draftEnabled = value
}

function resetEnabledDraft(row) {
  row._draftEnabled = Boolean(row?.enabled)
}

function resetForm() {
  form.loginEmail = ''
  form.loginPassword = ''
  form.displayName = ''
  form.remark = ''
}

async function loadAccounts(options = {}) {
  const { silent = false } = options
  loading.value = true
  try {
    const { data } = await judianApi.listAccounts()
    const rows = (Array.isArray(data?.items) ? data.items : []).map((row) => ({
      ...row,
      _draftEnabled: Boolean(row.enabled),
      _enabledSaving: false,
    }))
    accounts.value = rows
    lastUpdatedText.value = rows[0]?.updatedAt || rows[0]?.lastLoginAt || '暂无数据'
  } catch (error) {
    if (!silent) {
      message.error(extractErrorMessage(error))
    }
  } finally {
    loading.value = false
  }
}

async function submitLogin() {
  if (!looksLikeEmail(form.loginEmail)) {
    message.warning('请输入正确的邮箱格式')
    return
  }
  if (!String(form.loginPassword || '').trim()) {
    message.warning('请输入登录密码')
    return
  }

  submitting.value = true
  try {
    const { data } = await judianApi.loginAccount({
      loginEmail: form.loginEmail,
      loginPassword: form.loginPassword,
      displayName: form.displayName,
      remark: form.remark,
    })
    await loadAccounts({ silent: true })
    resetForm()
    message.success(data?.message || `已登录：${data?.item?.displayName || form.loginEmail}`)
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function handleRelogin(row) {
  reloginId.value = row.id
  try {
    const { data } = await judianApi.reloginAccount(row.id)
    await loadAccounts({ silent: true })
    message.success(data?.message || `${row.displayName} 已重新登录`)
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    reloginId.value = null
  }
}

async function handleDelete(row) {
  try {
    await judianApi.deleteAccount(row.id)
    await loadAccounts({ silent: true })
    message.success('账号已删除')
  } catch (error) {
    message.error(extractErrorMessage(error))
  }
}

async function saveEnabledDraft(row) {
  if (!hasEnabledDraftChanged(row) || row._enabledSaving) return
  row._enabledSaving = true
  try {
    const nextEnabled = resolveEnabledDraft(row)
    await judianApi.updateAccount(row.id, { enabled: nextEnabled })
    row.enabled = nextEnabled
    row.status = nextEnabled ? (String(row.sessionToken || '').trim() ? 'active' : 'pending') : 'disabled'
    row._draftEnabled = nextEnabled
    message.success(nextEnabled ? '账号已启用' : '账号已停用')
  } catch (error) {
    message.error(extractErrorMessage(error))
  } finally {
    row._enabledSaving = false
  }
}

onMounted(() => {
  loadAccounts()
})
</script>

