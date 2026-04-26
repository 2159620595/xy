<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import {
  Delete,
  Edit,
  Plus,
  RefreshRight,
  Switch,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { createCard, deleteCard, getCards, updateCard } from "@/api/cards";
import { post } from "@/utils/request";
import type { CardData } from "@/types";

type CardFormType = "" | "api" | "text" | "data" | "image";

const loading = ref(true);
const saving = ref(false);
const cards = ref<CardData[]>([]);
const dialogVisible = ref(false);
const editingCardId = ref<number | null>(null);
const imagePreview = ref("");

const form = reactive({
  name: "",
  type: "" as CardFormType,
  description: "",
  delaySeconds: 0,
  enabled: true,
  isMultiSpec: false,
  specName: "",
  specValue: "",
  apiUrl: "",
  apiMethod: "GET",
  apiTimeout: 10,
  apiHeaders: "",
  apiParams: "",
  textContent: "",
  dataContent: "",
  imageUrl: "",
  imageFile: null as File | null,
});

const cardTypeOptions = [
  { label: "API 接口", value: "api" },
  { label: "固定文字", value: "text" },
  { label: "批量数据", value: "data" },
  { label: "图片", value: "image" },
];

const apiMethodOptions = [
  { label: "GET", value: "GET" },
  { label: "POST", value: "POST" },
];

const postParams = [
  "order_id",
  "item_id",
  "item_detail",
  "order_amount",
  "order_quantity",
  "spec_name",
  "spec_value",
  "cookie_id",
  "buyer_id",
];

const metrics = computed(() => [
  { label: "总卡券数", value: cards.value.length },
  { label: "API 卡券", value: cards.value.filter((item) => item.type === "api").length },
  { label: "文本卡券", value: cards.value.filter((item) => item.type === "text").length },
  { label: "批量卡券", value: cards.value.filter((item) => item.type === "data").length },
]);

const getCardTypeLabel = (type?: string) => {
  const map: Record<string, string> = {
    api: "API",
    text: "文本",
    data: "批量",
    image: "图片",
  };
  return map[type || ""] || "-";
};

const getCardTypeTag = (
  type?: string,
): "" | "success" | "warning" | "danger" | "info" => {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    api: "primary" as never,
    text: "success",
    data: "warning",
    image: "info",
  };
  return map[type || ""] || "info";
};

const getCardPreview = (card: CardData) => {
  if (card.type === "text") return card.text_content || "-";
  if (card.type === "data") {
    const count =
      card.data_content
        ?.split("\n")
        .map((line) => line.trim())
        .filter(Boolean).length || 0;
    return count ? `剩余 ${count} 条` : "-";
  }
  if (card.type === "api") return card.api_config?.url || "-";
  if (card.type === "image") return card.image_url || "-";
  return "-";
};

const resetForm = () => {
  form.name = "";
  form.type = "";
  form.description = "";
  form.delaySeconds = 0;
  form.enabled = true;
  form.isMultiSpec = false;
  form.specName = "";
  form.specValue = "";
  form.apiUrl = "";
  form.apiMethod = "GET";
  form.apiTimeout = 10;
  form.apiHeaders = "";
  form.apiParams = "";
  form.textContent = "";
  form.dataContent = "";
  form.imageUrl = "";
  form.imageFile = null;
  imagePreview.value = "";
  editingCardId.value = null;
};

const loadCards = async () => {
  loading.value = true;
  try {
    const result = await getCards();
    cards.value = result.data || [];
  } catch {
    cards.value = [];
    ElMessage.error("加载卡券列表失败");
  } finally {
    loading.value = false;
  }
};

const openAddDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (card: CardData) => {
  resetForm();
  editingCardId.value = card.id ?? null;
  form.name = card.name || "";
  form.type = (card.type || "") as CardFormType;
  form.description = card.description || "";
  form.delaySeconds = card.delay_seconds || 0;
  form.enabled = card.enabled !== false;
  form.isMultiSpec = Boolean(card.is_multi_spec);
  form.specName = card.spec_name || "";
  form.specValue = card.spec_value || "";
  form.apiUrl = card.api_config?.url || "";
  form.apiMethod = card.api_config?.method || "GET";
  form.apiTimeout = card.api_config?.timeout || 10;
  form.apiHeaders = card.api_config?.headers || "";
  form.apiParams = card.api_config?.params || "";
  form.textContent = card.text_content || "";
  form.dataContent = card.data_content || "";
  form.imageUrl = card.image_url || "";
  imagePreview.value = card.image_url || "";
  dialogVisible.value = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

const handleImageChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error("图片大小不能超过 5MB");
    input.value = "";
    return;
  }

  form.imageFile = file;
  const reader = new FileReader();
  reader.onload = () => {
    imagePreview.value = String(reader.result || "");
  };
  reader.readAsDataURL(file);
};

const insertParam = (paramName: string) => {
  let jsonObj: Record<string, string> = {};
  if (form.apiParams.trim()) {
    try {
      jsonObj = JSON.parse(form.apiParams) as Record<string, string>;
    } catch {
      jsonObj = {};
    }
  }
  jsonObj[paramName] = `{${paramName}}`;
  form.apiParams = JSON.stringify(jsonObj, null, 2);
};

const validateForm = () => {
  if (!form.name.trim()) {
    ElMessage.warning("请输入卡券名称");
    return false;
  }
  if (!form.type) {
    ElMessage.warning("请选择卡券类型");
    return false;
  }
  if (form.type === "api" && !form.apiUrl.trim()) {
    ElMessage.warning("请输入 API 地址");
    return false;
  }
  if (form.type === "text" && !form.textContent.trim()) {
    ElMessage.warning("请输入固定文字内容");
    return false;
  }
  if (form.type === "data" && !form.dataContent.trim()) {
    ElMessage.warning("请输入批量数据");
    return false;
  }
  if (form.type === "image" && !form.imageFile && !form.imageUrl) {
    ElMessage.warning("请先上传图片");
    return false;
  }
  if (form.isMultiSpec && (!form.specName.trim() || !form.specValue.trim())) {
    ElMessage.warning("多规格卡券需要填写规格名称和规格值");
    return false;
  }

  if (form.apiHeaders.trim()) {
    try {
      JSON.parse(form.apiHeaders);
    } catch {
      ElMessage.warning("请求头必须是有效 JSON");
      return false;
    }
  }
  if (form.apiParams.trim()) {
    try {
      JSON.parse(form.apiParams);
    } catch {
      ElMessage.warning("请求参数必须是有效 JSON");
      return false;
    }
  }
  return true;
};

const handleSubmit = async () => {
  if (!validateForm()) return;

  saving.value = true;
  try {
    let imageUrl = form.imageUrl;
    if (form.type === "image" && form.imageFile) {
      const uploadForm = new FormData();
      uploadForm.append("image", form.imageFile);
      const result = await post<{ image_url: string }>("/upload-image", uploadForm, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      imageUrl = result.image_url;
    }

    const payload: Omit<CardData, "id" | "created_at" | "updated_at" | "user_id"> = {
      name: form.name.trim(),
      type: form.type as CardData["type"],
      description: form.description.trim() || undefined,
      enabled: form.enabled,
      delay_seconds: form.delaySeconds,
      is_multi_spec: form.isMultiSpec,
      spec_name: form.isMultiSpec ? form.specName.trim() : undefined,
      spec_value: form.isMultiSpec ? form.specValue.trim() : undefined,
    };

    if (form.type === "api") {
      payload.api_config = {
        url: form.apiUrl.trim(),
        method: form.apiMethod,
        timeout: form.apiTimeout,
        headers: form.apiHeaders.trim() || undefined,
        params: form.apiParams.trim() || undefined,
      };
    } else if (form.type === "text") {
      payload.text_content = form.textContent.trim();
    } else if (form.type === "data") {
      payload.data_content = form.dataContent.trim();
    } else if (form.type === "image") {
      payload.image_url = imageUrl;
    }

    if (editingCardId.value) {
      await updateCard(String(editingCardId.value), payload);
      ElMessage.success("卡券更新成功");
    } else {
      await createCard(payload);
      ElMessage.success("卡券创建成功");
    }

    closeDialog();
    await loadCards();
  } catch {
    ElMessage.error(editingCardId.value ? "更新卡券失败" : "创建卡券失败");
  } finally {
    saving.value = false;
  }
};

const toggleCardStatus = async (card: CardData) => {
  try {
    await updateCard(String(card.id), { enabled: !card.enabled });
    ElMessage.success(card.enabled ? "卡券已禁用" : "卡券已启用");
    await loadCards();
  } catch {
    ElMessage.error("卡券状态更新失败");
  }
};

const removeCard = async (card: CardData) => {
  try {
    await ElMessageBox.confirm(`确定删除卡券“${card.name}”吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await deleteCard(String(card.id));
    ElMessage.success("卡券已删除");
    await loadCards();
  } catch {
    // ignore cancel
  }
};

loadCards();
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">卡券管理</h1>
        <p class="page-description">
          管理自动发货使用的 API、文本、批量和图片卡券，并补齐多规格配置能力。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="RefreshRight" @click="loadCards">刷新列表</el-button>
        <el-button type="primary" :icon="Plus" @click="openAddDialog">
          添加卡券
        </el-button>
      </div>
    </section>

    <section class="metric-grid">
      <el-card v-for="item in metrics" :key="item.label" shadow="never" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </el-card>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">当前共 {{ cards.length }} 张卡券</div>
        <el-tag type="primary" effect="plain">已接入新增、编辑、启停、删除和图片上传</el-tag>
      </div>

      <el-table v-loading="loading" :data="cards" style="width: 100%; margin-top: 16px">
        <el-table-column label="名称" min-width="180">
          <template #default="{ row }">
            <div class="cell-title">
              <div class="cell-title-main">{{ row.name }}</div>
              <div v-if="row.description" class="cell-title-sub">{{ row.description }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getCardTypeTag(row.type)" effect="plain">
              {{ getCardTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="内容预览" min-width="220">
          <template #default="{ row }">
            <template v-if="row.type === 'image' && row.image_url">
              <div class="image-preview-cell">
                <el-image
                  :src="row.image_url"
                  fit="cover"
                  class="preview-thumb"
                  :preview-src-list="[row.image_url]"
                  preview-teleported
                />
                <span class="cell-title-sub">点击可预览</span>
              </div>
            </template>
            <template v-else>
              <span class="text-muted">{{ getCardPreview(row) }}</span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="延时" width="100">
          <template #default="{ row }">
            {{ row.delay_seconds || 0 }} 秒
          </template>
        </el-table-column>

        <el-table-column label="规格" min-width="140">
          <template #default="{ row }">
            <span v-if="row.is_multi_spec">
              {{ row.spec_name || "-" }}: {{ row.spec_value || "-" }}
            </span>
            <span v-else class="text-muted">普通卡券</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled !== false ? 'success' : 'info'" effect="plain">
              {{ row.enabled !== false ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="220" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-button
                link
                :type="row.enabled !== false ? 'warning' : 'success'"
                :icon="Switch"
                @click="toggleCardStatus(row)"
              >
                {{ row.enabled !== false ? "禁用" : "启用" }}
              </el-button>
              <el-button link type="danger" :icon="Delete" @click="removeCard(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无卡券数据" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingCardId ? '编辑卡券' : '添加卡券'"
      width="760px"
      destroy-on-close
      @closed="closeDialog"
    >
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="卡券名称">
              <el-input v-model="form.name" placeholder="例如：会员卡、兑换码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="卡券类型">
              <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
                <el-option
                  v-for="item in cardTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="延时发货（秒）">
              <el-input-number v-model="form.delaySeconds" :min="0" :max="3600" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="可选，填写卡券说明"
          />
        </el-form-item>

        <el-divider>内容配置</el-divider>

        <template v-if="form.type === 'api'">
          <el-row :gutter="16">
            <el-col :span="16">
              <el-form-item label="API 地址">
                <el-input v-model="form.apiUrl" placeholder="https://api.example.com/get-card" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="请求方法">
                <el-select v-model="form.apiMethod" style="width: 100%">
                  <el-option
                    v-for="item in apiMethodOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="超时时间（秒）">
                <el-input-number v-model="form.apiTimeout" :min="1" :max="60" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="请求头（JSON）">
            <el-input
              v-model="form.apiHeaders"
              type="textarea"
              :rows="3"
              placeholder='{"Authorization":"Bearer token"}'
            />
          </el-form-item>

          <el-form-item label="请求参数（JSON）">
            <el-input
              v-model="form.apiParams"
              type="textarea"
              :rows="4"
              placeholder='{"item_id":"{item_id}"}'
            />
            <div class="param-helper">
              <span class="cell-title-sub">常用变量：</span>
              <el-tag
                v-for="param in postParams"
                :key="param"
                class="param-tag"
                effect="plain"
                @click="insertParam(param)"
              >
                {{ param }}
              </el-tag>
            </div>
          </el-form-item>
        </template>

        <el-form-item v-else-if="form.type === 'text'" label="固定文字内容">
          <el-input
            v-model="form.textContent"
            type="textarea"
            :rows="6"
            placeholder="请输入固定文字内容"
          />
        </el-form-item>

        <el-form-item v-else-if="form.type === 'data'" label="批量数据内容">
          <el-input
            v-model="form.dataContent"
            type="textarea"
            :rows="8"
            placeholder="一行一条数据，例如卡密或兑换码"
          />
        </el-form-item>

        <template v-else-if="form.type === 'image'">
          <el-form-item label="上传图片">
            <input type="file" accept="image/*" @change="handleImageChange" />
          </el-form-item>
          <div v-if="imagePreview" class="dialog-image-preview">
            <el-image
              :src="imagePreview"
              fit="cover"
              class="preview-large"
              :preview-src-list="[imagePreview]"
              preview-teleported
            />
          </div>
        </template>

        <el-divider>多规格配置</el-divider>

        <el-form-item label="启用多规格">
          <el-switch v-model="form.isMultiSpec" />
        </el-form-item>

        <el-row v-if="form.isMultiSpec" :gutter="16">
          <el-col :span="12">
            <el-form-item label="规格名称">
              <el-input v-model="form.specName" placeholder="例如：套餐、颜色、尺寸" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规格值">
              <el-input v-model="form.specValue" placeholder="例如：30天、红色、XL" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.image-preview-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-thumb {
  width: 48px;
  height: 48px;
  border-radius: 12px;
}

.dialog-image-preview {
  margin-bottom: 16px;
}

.preview-large {
  width: 120px;
  height: 120px;
  border-radius: 16px;
}

.param-helper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.param-tag {
  cursor: pointer;
}
</style>
