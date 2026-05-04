<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Download,
  InfoFilled,
  Picture,
  Plus,
  RefreshRight,
  Upload,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAccounts } from '@/api/accounts'
import { getItems } from '@/api/items'
import {
  addImageKeyword,
  addKeyword,
  deleteKeyword,
  exportKeywords,
  getKeywords,
  importKeywords,
  updateKeyword,
} from '@/api/keywords'
import type { Account, Item, Keyword } from '@/types'

const loading = ref(true)
const saving = ref(false)
const importing = ref(false)
const exporting = ref(false)
const imageSaving = ref(false)
const previewVisible = ref(false)
const textDialogVisible = ref(false)
const imageDialogVisible = ref(false)

const accounts = ref<Account[]>([])
const items = ref<Item[]>([])
const keywords = ref<Keyword[]>([])
const selectedAccount = ref('')
const previewImageUrl = ref('')
const editingKeyword = ref<Keyword | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)

const textForm = reactive({
  keyword: '',
  reply: '',
  itemId: '',
})

const imageForm = reactive({
  keyword: '',
  itemId: '',
  file: null as File | null,
  preview: '',
})

const accountOptions = computed(() =>
  accounts.value.map((account) => ({
    label: account.xianyu_nickname ? `${account.id}（${account.xianyu_nickname}）` : account.id,
    value: account.id,
  })),
)

const keywordCountText = computed(() => `当前共 ${keywords.value.length} 个关键词`)

const getItemLabel = (itemId?: string) => {
  if (!itemId) return '通用关键词'
  const matched = items.value.find((item) => item.item_id === itemId)
  const title = matched?.title || matched?.item_title || ''
  return title ? `${itemId}（${title}）` : itemId
}

const resetTextForm = () => {
  textForm.keyword = ''
  textForm.reply = ''
  textForm.itemId = ''
}

const resetImageForm = () => {
  imageForm.keyword = ''
  imageForm.itemId = ''
  imageForm.file = null
  imageForm.preview = ''
  if (imageInput.value) {
    imageInput.value.value = ''
  }
}

const loadAccounts = async () => {
  try {
    const result = await getAccounts()
    accounts.value = result
    if (!selectedAccount.value && result.length > 0) {
      selectedAccount.value = result[0].id
    }
  } catch {
    ElMessage.error('账号列表加载失败')
  }
}

const loadItems = async () => {
  if (!selectedAccount.value) {
    items.value = []
    return
  }
  try {
    const result = await getItems(selectedAccount.value)
    items.value = result.data || []
  } catch {
    items.value = []
  }
}

const loadKeywords = async () => {
  if (!selectedAccount.value) {
    keywords.value = []
    loading.value = false
    return
  }

  loading.value = true
  try {
    const result = await getKeywords(selectedAccount.value)
    keywords.value = Array.isArray(result) ? result : []
  } catch {
    keywords.value = []
    ElMessage.error('关键词列表加载失败')
  } finally {
    loading.value = false
  }
}

const loadPageData = async () => {
  if (!selectedAccount.value) {
    items.value = []
    keywords.value = []
    loading.value = false
    return
  }

  // 优先加载关键词，避免与商品列表并发竞争后端数据库锁。
  await loadKeywords()
  await loadItems()
}

const openAddTextDialog = () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }
  editingKeyword.value = null
  resetTextForm()
  textDialogVisible.value = true
}

const openEditTextDialog = (keyword: Keyword) => {
  if (keyword.type === 'image') {
    ElMessage.warning('图片关键词不支持编辑，请删除后重新添加')
    return
  }
  editingKeyword.value = keyword
  textForm.keyword = keyword.keyword
  textForm.reply = keyword.reply || ''
  textForm.itemId = keyword.item_id || ''
  textDialogVisible.value = true
}

const submitTextKeyword = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }
  if (!textForm.keyword.trim()) {
    ElMessage.warning('请输入关键词')
    return
  }

  saving.value = true
  try {
    const payload = {
      keyword: textForm.keyword.trim(),
      reply: textForm.reply.trim(),
      item_id: textForm.itemId,
    }

    const result = editingKeyword.value
      ? await updateKeyword(
          selectedAccount.value,
          editingKeyword.value.keyword,
          editingKeyword.value.item_id || '',
          payload,
        )
      : await addKeyword(selectedAccount.value, payload)

    if (result.success === false) {
      ElMessage.error(result.message || '保存失败')
      return
    }

    ElMessage.success(editingKeyword.value ? '关键词已更新' : '关键词已添加')
    textDialogVisible.value = false
    resetTextForm()
    await loadKeywords()
  } catch {
    ElMessage.error('保存关键词失败')
  } finally {
    saving.value = false
  }
}

const openImageKeywordDialog = () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }
  resetImageForm()
  imageDialogVisible.value = true
}

const handleImageChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    target.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5MB')
    target.value = ''
    return
  }

  imageForm.file = file
  const reader = new FileReader()
  reader.onload = (readerEvent) => {
    imageForm.preview = String(readerEvent.target?.result || '')
  }
  reader.readAsDataURL(file)
}

const submitImageKeyword = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }
  if (!imageForm.keyword.trim()) {
    ElMessage.warning('请输入关键词')
    return
  }
  if (!imageForm.file) {
    ElMessage.warning('请先选择图片')
    return
  }

  imageSaving.value = true
  try {
    const result = await addImageKeyword(
      selectedAccount.value,
      imageForm.keyword.trim(),
      imageForm.file,
      imageForm.itemId || undefined,
    )

    if (!result.success) {
      ElMessage.error(result.message || '添加图片关键词失败')
      return
    }

    ElMessage.success('图片关键词添加成功')
    imageDialogVisible.value = false
    resetImageForm()
    await loadKeywords()
  } catch {
    ElMessage.error('添加图片关键词失败')
  } finally {
    imageSaving.value = false
  }
}

const removeKeyword = async (keyword: Keyword) => {
  try {
    await ElMessageBox.confirm(`确定删除关键词“${keyword.keyword}”吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })

    await deleteKeyword(selectedAccount.value, keyword.keyword, keyword.item_id || '')
    ElMessage.success('关键词已删除')
    await loadKeywords()
  } catch {
    // ignore cancel
  }
}

const handleExport = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }

  exporting.value = true
  try {
    const blob = await exportKeywords(selectedAccount.value)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    const date = new Date().toISOString().slice(0, 10)
    link.href = url
    link.download = `keywords_${selectedAccount.value}_${date}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const triggerImport = () => {
  if (!selectedAccount.value) {
    ElMessage.warning('请先选择账号')
    return
  }
  importInput.value?.click()
}

const handleImport = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !selectedAccount.value) return

  importing.value = true
  try {
    const result = await importKeywords(selectedAccount.value, file)
    const payload = result as ApiLikeImportResult
    if (payload.success === false) {
      ElMessage.error(payload.message || '导入失败')
      return
    }

    ElMessage.success(`导入成功：新增 ${payload.data?.added ?? payload.added ?? 0} 条，更新 ${payload.data?.updated ?? payload.updated ?? 0} 条`)
    await loadKeywords()
  } catch {
    ElMessage.error('导入关键词失败')
  } finally {
    importing.value = false
    target.value = ''
  }
}

type ApiLikeImportResult = {
  success?: boolean
  message?: string
  added?: number
  updated?: number
  data?: {
    added?: number
    updated?: number
  }
}

watch(selectedAccount, async () => {
  await loadPageData()
})

onMounted(async () => {
  await loadAccounts()
  if (!selectedAccount.value) {
    loading.value = false
  }
})
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">关键词管理</h1>
        <p class="page-description">管理文本关键词、图片关键词以及按商品绑定的自动回复规则。</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" :icon="Plus" @click="openAddTextDialog">添加文本关键词</el-button>
        <el-button type="primary" plain :icon="Picture" @click="openImageKeywordDialog">添加图片关键词</el-button>
        <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
        <el-button :icon="Upload" :loading="importing" @click="triggerImport">导入</el-button>
        <el-button :icon="RefreshRight" @click="loadKeywords">刷新</el-button>
        <input
          ref="importInput"
          type="file"
          accept=".xlsx,.xls"
          class="hidden-input"
          @change="handleImport"
        />
      </div>
    </section>

    <el-card shadow="never">
      <div class="inline-form">
        <el-form-item label="选择账号">
          <el-select v-model="selectedAccount" placeholder="请选择账号" clearable filterable>
            <el-option
              v-for="account in accountOptions"
              :key="account.value"
              :label="account.label"
              :value="account.value"
            />
          </el-select>
        </el-form-item>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="tips-box">
        <el-icon><InfoFilled /></el-icon>
        <div>
          <div class="tips-title">支持变量替换</div>
          <div class="tips-content">
            <span>`{send_user_name}` 用户昵称</span>
            <span>`{send_user_id}` 用户 ID</span>
            <span>`{send_message}` 用户消息内容</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">{{ keywordCountText }}</div>
        <el-tag type="primary" effect="plain">已接通文本/图片关键词和导入导出</el-tag>
      </div>

      <el-table v-loading="loading" :data="keywords" style="width: 100%; margin-top: 16px">
        <el-table-column label="关键词" min-width="180">
          <template #default="{ row }">
            <code class="keyword-chip">{{ row.keyword }}</code>
          </template>
        </el-table-column>

        <el-table-column label="商品 ID" min-width="220">
          <template #default="{ row }">
            <span>{{ getItemLabel(row.item_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="回复内容" min-width="320">
          <template #default="{ row }">
            <template v-if="row.type === 'image'">
              <el-button
                v-if="row.image_url"
                link
                type="primary"
                @click="
                  previewImageUrl = row.image_url || '';
                  previewVisible = true;
                "
              >
                查看大图
              </el-button>
              <span v-else class="text-muted">无图片</span>
            </template>
            <template v-else>
              <span class="text-ellipsis">{{ row.reply || '不回复' }}</span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'image' ? 'primary' : 'info'" effect="plain">
              {{ row.type === 'image' ? '图片' : '文本' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openEditTextDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="removeKeyword(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty :description="selectedAccount ? '暂无关键词数据' : '请先选择一个账号'" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="textDialogVisible"
      :title="editingKeyword ? '编辑关键词' : '添加关键词'"
      width="680px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="所属账号">
          <el-input :model-value="selectedAccount" disabled />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="textForm.keyword" placeholder="请输入关键词" />
        </el-form-item>
        <el-form-item label="绑定商品（可选）">
          <el-select v-model="textForm.itemId" placeholder="通用关键词（所有商品）" clearable filterable style="width: 100%">
            <el-option
              v-for="item in items"
              :key="item.item_id"
              :label="`${item.item_id} - ${item.title || item.item_title || '未命名商品'}`"
              :value="item.item_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="回复内容">
          <el-input
            v-model="textForm.reply"
            type="textarea"
            :rows="6"
            placeholder="留空表示匹配到关键词但不自动回复"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="textDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitTextKeyword">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="imageDialogVisible" title="添加图片关键词" width="720px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="关键词">
          <el-input v-model="imageForm.keyword" placeholder="例如：图片、照片、实拍图" />
        </el-form-item>
        <el-form-item label="绑定商品（可选）">
          <el-select v-model="imageForm.itemId" placeholder="通用关键词（所有商品）" clearable filterable style="width: 100%">
            <el-option
              v-for="item in items"
              :key="item.item_id"
              :label="`${item.item_id} - ${item.title || item.item_title || '未命名商品'}`"
              :value="item.item_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="上传图片">
          <div class="image-upload-box" @click="imageInput?.click()">
            <template v-if="imageForm.preview">
              <img :src="imageForm.preview" alt="预览" class="image-preview" />
              <div class="image-upload-tip">点击更换图片</div>
            </template>
            <template v-else>
              <el-icon class="upload-icon"><Picture /></el-icon>
              <div>点击选择图片</div>
              <div class="text-muted">支持 JPG、PNG、GIF，不超过 5MB</div>
            </template>
          </div>
          <input
            ref="imageInput"
            type="file"
            accept="image/*"
            class="hidden-input"
            @change="handleImageChange"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="imageDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="imageSaving" @click="submitImageKeyword">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" title="图片预览" width="720px" destroy-on-close>
      <div class="preview-shell">
        <img :src="previewImageUrl" alt="关键词图片预览" class="preview-image" />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.hidden-input {
  display: none;
}

.tips-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #eff6ff;
  color: #1d4ed8;
}

.tips-title {
  font-weight: 600;
}

.tips-content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 6px;
  color: #2563eb;
  font-size: 13px;
}

.keyword-chip {
  padding: 4px 8px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.image-upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 220px;
  padding: 20px;
  border: 2px dashed rgba(148, 163, 184, 0.35);
  border-radius: 16px;
  background: #f8fafc;
  cursor: pointer;
}

.upload-icon {
  font-size: 28px;
  color: #64748b;
}

.image-preview {
  max-width: 100%;
  max-height: 220px;
  border-radius: 14px;
  object-fit: contain;
}

.image-upload-tip {
  color: #2563eb;
  font-size: 13px;
}

.preview-shell {
  display: flex;
  justify-content: center;
  align-items: center;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 16px;
  object-fit: contain;
}
</style>
