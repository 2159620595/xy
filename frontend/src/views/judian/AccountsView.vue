<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="lastUpdatedText"
  >
    <template #actions>
      <el-space>
        <el-button :loading="loading" @click="loadAccounts">刷新列表</el-button>
      </el-space>
    </template>

    <el-card shadow="never">
      <template #header>登录聚点账号</template>
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        当前已接入真实后端。提交邮箱和密码后，会按聚点安卓端协议登录远端，并同步会话 Token、UserSig 与钻石余额。
      </el-alert>

      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="9">
            <el-form-item label="登录邮箱">
              <el-input v-model="form.loginEmail" placeholder="请输入聚点登录邮箱" @keyup.enter="submitLogin" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="7">
            <el-form-item label="登录密码">
              <el-input
                v-model="form.loginPassword"
              type="password"
                show-password
              placeholder="请输入登录密码"
              @keyup.enter="submitLogin"
            />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="4">
            <el-form-item label="显示名称">
              <el-input v-model="form.displayName" placeholder="可选" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="4">
            <el-form-item label="备注">
              <el-input v-model="form.remark" placeholder="可选" />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-actions">
          <el-space>
            <el-button @click="resetForm">清空</el-button>
            <el-button type="primary" :loading="submitting" @click="submitLogin">账号密码登录</el-button>
          </el-space>
        </div>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>账号池管理</template>
      <el-table :data="accounts" stripe v-loading="loading">
        <el-table-column prop="accountId" label="账号 ID" width="120" />
        <el-table-column prop="displayName" label="显示名称" min-width="160" />
        <el-table-column label="登录邮箱" min-width="220">
          <template #default="{ row }">
            {{ maskText(row.loginEmail, 3, 9) }}
          </template>
        </el-table-column>
        <el-table-column label="钻石数量" width="120">
          <template #default="{ row }">
            <span class="diamond-value">{{ Number(row.diamondQuantity || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="diamondQuantityUpdatedAt" label="钻石刷新" min-width="180" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="resolveStatusType(row.status)">
              {{ resolveStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="最近登录" min-width="180" />
        <el-table-column label="Session Token" min-width="220">
          <template #default="{ row }">
            {{ maskText(row.sessionToken, 6, 6) }}
          </template>
        </el-table-column>
        <el-table-column label="UserSig" min-width="180">
          <template #default="{ row }">
            {{ maskText(row.userSig, 6, 6) }}
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch
              :model-value="resolveEnabledDraft(row)"
              :loading="Boolean(row._enabledSaving)"
              @update:model-value="updateEnabledDraft(row, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="360" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag
                v-if="hasEnabledDraftChanged(row)"
                type="warning"
                effect="plain"
              >
                待保存
              </el-tag>
              <el-button
                size="small"
                type="primary"
                plain
                :disabled="!hasEnabledDraftChanged(row)"
                :loading="Boolean(row._enabledSaving)"
                @click="saveEnabledDraft(row)"
              >
                保存启用
              </el-button>
              <el-button
                size="small"
                :disabled="!hasEnabledDraftChanged(row) || Boolean(row._enabledSaving)"
                @click="resetEnabledDraft(row)"
              >
                撤销
              </el-button>
              <el-button
                size="small"
                type="primary"
                text
                :loading="reloginId === row.id"
                :disabled="Boolean(row._enabledSaving)"
                @click="handleRelogin(row)"
              >
                账密登录
              </el-button>
              <el-button
                size="small"
                type="danger"
                text
                :disabled="Boolean(row._enabledSaving)"
                @click="confirmDelete(row)"
              >
                删除
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </JudianPageLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { judianApi } from '@/api/judian'
import JudianPageLayout from '@/components/judian/PageLayout.vue'
import { getJudianSectionMeta } from '@/views/judian/shared/page-meta'

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

function resolveStatusLabel(status) {
  return statusMap[status]?.label || '未知'
}

function resolveStatusType(status) {
  return statusMap[status]?.type === 'default' ? 'info' : statusMap[status]?.type || 'info'
}

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
      ElMessage.error(extractErrorMessage(error))
    }
  } finally {
    loading.value = false
  }
}

async function submitLogin() {
  if (!looksLikeEmail(form.loginEmail)) {
    ElMessage.warning('请输入正确的邮箱格式')
    return
  }
  if (!String(form.loginPassword || '').trim()) {
    ElMessage.warning('请输入登录密码')
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
    ElMessage.success(data?.message || `已登录：${data?.item?.displayName || form.loginEmail}`)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function handleRelogin(row) {
  reloginId.value = row.id
  try {
    const { data } = await judianApi.reloginAccount(row.id)
    await loadAccounts({ silent: true })
    ElMessage.success(data?.message || `${row.displayName} 已重新登录`)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    reloginId.value = null
  }
}

async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除账号 ${row.displayName}？`, '删除确认', {
      type: 'warning',
    })
    await handleDelete(row)
  } catch {
    // User cancelled.
  }
}

async function handleDelete(row) {
  try {
    await judianApi.deleteAccount(row.id)
    await loadAccounts({ silent: true })
    ElMessage.success('账号已删除')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
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
    ElMessage.success(nextEnabled ? '账号已启用' : '账号已停用')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    row._enabledSaving = false
  }
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.form-actions {
  display: flex;
  justify-content: flex-end;
}

.diamond-value {
  font-weight: 600;
  color: #2563eb;
}
</style>

