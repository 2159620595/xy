<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Delete, Plus, RefreshRight } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAccounts } from "@/api/accounts";
import {
  addItemReply,
  deleteItemReply,
  fetchAllItemsFromAccount,
  getItemReplies,
  getItems,
  updateItemReply,
} from "@/api/items";
import type { Account, Item, ItemReply } from "@/types";

const loading = ref(true);
const saving = ref(false);
const fetchingItems = ref(false);
const itemsLoading = ref(false);
const dialogVisible = ref(false);
const accounts = ref<Account[]>([]);
const replies = ref<ItemReply[]>([]);
const items = ref<Item[]>([]);
const selectedAccount = ref("");
const editingReply = ref<ItemReply | null>(null);
const itemSearchKeyword = ref("");

const form = ref({
  itemId: "",
  title: "",
  reply: "",
  replyOnce: false,
});

const selectedItemOptions = computed(() => {
  const keyword = itemSearchKeyword.value.trim().toLowerCase();
  return items.value
    .filter((item) => {
      if (!keyword) return true;
      return `${item.item_id} ${item.item_title || item.title || ""}`
        .toLowerCase()
        .includes(keyword);
    })
    .map((item) => ({
      value: item.item_id,
      label:
        item.item_title || item.title
          ? `${item.item_id}（${item.item_title || item.title}）`
          : item.item_id,
    }));
});

const getItemPrimaryImage = (item?: Item | null) => {
  if (!item) return "";
  const primaryImage =
    item.images?.find((image) => image.is_primary) || item.images?.[0];
  return (
    item.primary_image_url ||
    primaryImage?.thumbnail_url ||
    primaryImage?.image_url ||
    item.item_detail_parsed?.pic_info?.picUrl ||
    item.item_detail_parsed?.pic_info?.url ||
    ""
  );
};

const getLinkedItem = (reply: ItemReply) => {
  return items.value.find(
    (item) =>
      item.cookie_id === reply.cookie_id && item.item_id === reply.item_id,
  );
};

const getReplyContent = (reply: ItemReply) =>
  reply.reply || reply.reply_content || reply.content || "-";

const getReplyTitle = (reply: ItemReply) => {
  return (
    reply.title ||
    reply.item_title ||
    getLinkedItem(reply)?.item_title ||
    getLinkedItem(reply)?.title ||
    "-"
  );
};

const getReplyImage = (reply: ItemReply) => {
  const linkedItem = getLinkedItem(reply);
  return (
    reply.primary_image_url ||
    reply.thumbnail_url ||
    reply.image_url ||
    getItemPrimaryImage(linkedItem)
  );
};

const getAccountLabel = (cookieId: string) => {
  const account = accounts.value.find((item) => item.id === cookieId);
  if (!account) return cookieId;
  return account.xianyu_nickname
    ? `${cookieId}（${account.xianyu_nickname}）`
    : cookieId;
};

const loadReplies = async () => {
  loading.value = true;
  try {
    const result = await getItemReplies(selectedAccount.value || undefined);
    replies.value = result.data || [];
  } catch {
    replies.value = [];
    ElMessage.error("商品回复列表加载失败");
  } finally {
    loading.value = false;
  }
};

const loadAccounts = async () => {
  try {
    accounts.value = await getAccounts();
  } catch {
    ElMessage.warning("账号列表加载失败");
  }
};

const loadItems = async (cookieId?: string) => {
  itemsLoading.value = true;
  try {
    const result = await getItems(cookieId);
    items.value = result.data || [];
  } catch {
    items.value = [];
  } finally {
    itemsLoading.value = false;
  }
};

const handleFetchItems = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning("请先选择账号");
    return;
  }

  fetchingItems.value = true;
  try {
    const result = await fetchAllItemsFromAccount(selectedAccount.value);
    if (result.success) {
      ElMessage.success(result.message || "获取商品完成");
      await loadItems(selectedAccount.value);
    } else {
      ElMessage.error(result.detail || result.message || "获取商品失败");
    }
  } catch {
    ElMessage.error("获取商品失败");
  } finally {
    fetchingItems.value = false;
  }
};

const resetForm = () => {
  form.value = {
    itemId: "",
    title: "",
    reply: "",
    replyOnce: false,
  };
  itemSearchKeyword.value = "";
};

const openAddDialog = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning("请先选择账号");
    return;
  }

  editingReply.value = null;
  resetForm();
  dialogVisible.value = true;
  if (!items.value.length) {
    await loadItems(selectedAccount.value);
  }
};

const openEditDialog = (reply: ItemReply) => {
  editingReply.value = reply;
  form.value = {
    itemId: reply.item_id,
    title: reply.title || reply.item_title || "",
    reply: getReplyContent(reply) === "-" ? "" : getReplyContent(reply),
    replyOnce: Boolean(reply.reply_once),
  };
  dialogVisible.value = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  editingReply.value = null;
  resetForm();
};

const handleItemChange = (value: string) => {
  const matched = items.value.find((item) => item.item_id === value);
  form.value.itemId = value;
  if (matched && !form.value.title) {
    form.value.title = matched.item_title || matched.title || "";
  }
};

const handleSubmit = async () => {
  if (!form.value.itemId.trim()) {
    ElMessage.warning("请选择商品");
    return;
  }

  if (!form.value.reply.trim()) {
    ElMessage.warning("请输入回复内容");
    return;
  }

  saving.value = true;
  const payload = {
    cookie_id: editingReply.value?.cookie_id || selectedAccount.value,
    item_id: form.value.itemId.trim(),
    title: form.value.title.trim() || undefined,
    reply_content: form.value.reply.trim(),
    reply_once: form.value.replyOnce,
  };

  try {
    if (editingReply.value) {
      await updateItemReply(
        editingReply.value.cookie_id,
        editingReply.value.item_id,
        payload,
      );
      ElMessage.success("回复已更新");
    } else {
      await addItemReply(
        selectedAccount.value,
        form.value.itemId.trim(),
        payload,
      );
      ElMessage.success("回复已添加");
    }
    closeDialog();
    await loadReplies();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const handleDelete = async (reply: ItemReply) => {
  try {
    await ElMessageBox.confirm("确定要删除这条商品回复吗？", "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await deleteItemReply(reply.cookie_id, reply.item_id);
    ElMessage.success("删除成功");
    await loadReplies();
  } catch {
    // ignore cancel
  }
};

watch(selectedAccount, async (value) => {
  await Promise.all([loadReplies(), loadItems(value || undefined)]);
});

onMounted(async () => {
  await Promise.all([loadAccounts(), loadReplies(), loadItems()]);
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">自动回复</h1>
        <p class="page-description">
          按账号管理商品自动回复，并支持设置每个客户在单个商品下只自动回复一次。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="RefreshRight" @click="loadReplies"
          >刷新列表</el-button
        >
        <el-button type="primary" :icon="Plus" @click="openAddDialog"
          >添加回复</el-button
        >
      </div>
    </section>

    <section class="filter-bar">
      <div class="filter-title">筛选条件</div>
      <div class="inline-form">
        <el-form-item label="筛选账号">
          <el-select v-model="selectedAccount" clearable placeholder="所有账号">
            <el-option label="所有账号" value="" />
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="
                account.xianyu_nickname
                  ? `${account.id}（${account.xianyu_nickname}）`
                  : account.id
              "
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <div class="fetch-block">
          <div class="fetch-label">商品缓存</div>
          <div class="fetch-actions">
            <span class="text-muted"
              >当前已缓存 {{ items.length }} 个商品用于主图匹配</span
            >
            <el-button
              :loading="fetchingItems"
              :disabled="!selectedAccount"
              @click="handleFetchItems"
            >
              同步该账号商品
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">当前共 {{ replies.length }} 条商品回复</div>
        <el-tag type="primary" effect="plain"
          >主图按 cookie_id + item_id 关联商品</el-tag
        >
      </div>

      <el-table
        v-loading="loading"
        :data="replies"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column label="账号" min-width="180">
          <template #default="{ row }">
            <span>{{ getAccountLabel(row.cookie_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="商品 ID" min-width="150">
          <template #default="{ row }">
            <span class="mono">{{ row.item_id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="主图" width="96">
          <template #default="{ row }">
            <el-image
              v-if="getReplyImage(row)"
              :src="getReplyImage(row)"
              fit="cover"
              class="item-image"
              preview-teleported
              :preview-src-list="[getReplyImage(row)]"
            />
            <span v-else class="text-muted">无图</span>
          </template>
        </el-table-column>

        <el-table-column label="商品标题" min-width="240">
          <template #default="{ row }">
            <span class="text-ellipsis">{{ getReplyTitle(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="回复内容" min-width="280">
          <template #default="{ row }">
            <span class="text-ellipsis">{{ getReplyContent(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="回复限制" width="140">
          <template #default="{ row }">
            <el-tag :type="row.reply_once ? 'warning' : 'info'" effect="plain">
              {{ row.reply_once ? "每客户一次" : "不限制" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            <span>{{
              row.created_at ? new Date(row.created_at).toLocaleString() : "-"
            }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openEditDialog(row)"
                >编辑</el-button
              >
              <el-button
                link
                type="danger"
                :icon="Delete"
                @click="handleDelete(row)"
                >删除</el-button
              >
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无商品回复数据" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingReply ? '编辑商品回复' : '添加商品回复'"
      width="640px"
      destroy-on-close
      @closed="closeDialog"
    >
      <el-form label-position="top">
        <el-form-item label="所属账号">
          <el-input
            :model-value="editingReply?.cookie_id || selectedAccount"
            disabled
          />
        </el-form-item>

        <el-form-item :label="editingReply ? '商品 ID' : '选择商品'">
          <template v-if="editingReply">
            <el-input :model-value="form.itemId" disabled />
          </template>
          <template v-else>
            <el-input
              v-model="itemSearchKeyword"
              placeholder="先搜索商品标题或商品 ID"
              clearable
              :disabled="itemsLoading"
            />
            <el-select
              :model-value="form.itemId"
              placeholder="请选择商品"
              filterable
              style="width: 100%; margin-top: 12px"
              :loading="itemsLoading"
              @update:model-value="handleItemChange"
            >
              <el-option
                v-for="option in selectedItemOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </template>
        </el-form-item>

        <el-form-item label="商品标题（可选）">
          <el-input
            v-model="form.title"
            placeholder="用于备注商品标题，默认会尝试自动填充"
          />
        </el-form-item>

        <el-form-item label="回复内容">
          <el-input
            v-model="form.reply"
            type="textarea"
            :rows="5"
            placeholder="支持变量：{send_user_name}、{send_user_id}、{send_message}、{item_id}"
          />
        </el-form-item>

        <el-form-item label="每客户只回复一次">
          <el-switch v-model="form.replyOnce" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit"
          >保存</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  margin-top: 12px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
}

.filter-title {
  margin-bottom: 12px;
  color: #0f172a;
  font-weight: 600;
}

.inline-form {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.inline-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.inline-form :deep(.el-select) {
  width: 220px;
}

.fetch-block {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.fetch-label {
  margin-bottom: 10px;
  color: #606266;
  font-size: 14px;
}

.fetch-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 40px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.item-image {
  width: 56px;
  height: 56px;
  border-radius: 12px;
}

@media (max-width: 768px) {
  .inline-form :deep(.el-select) {
    width: 100%;
  }
}
</style>
