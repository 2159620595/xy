<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { Delete, Plus, RefreshRight } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import { getAccounts } from "@/api/accounts";
import {
  addItemReply,
  batchDeleteItemReplies,
  deleteItemReply,
  fetchAllItemsFromAccount,
  getItemReplies,
  getItems,
  updateItemReply,
} from "@/api/items";
import type { Account, Item, ItemReply } from "@/types";

type ItemReplyTableRow = ItemReply & {
  hasReply: boolean;
};

const loading = ref(true);
const saving = ref(false);
const fetchingItems = ref(false);
const itemsLoading = ref(false);
const batchDeleting = ref(false);
const batchSaving = ref(false);
const dialogVisible = ref(false);
const batchDialogVisible = ref(false);
const accounts = ref<Account[]>([]);
const replies = ref<ItemReply[]>([]);
const items = ref<Item[]>([]);
const selectedRows = ref<ItemReplyTableRow[]>([]);
const selectedAccount = ref("");
const replyStatusFilter = ref<"all" | "configured" | "unconfigured">("all");
const editingReply = ref<ItemReply | null>(null);
const dialogAccountId = ref("");
const itemSearchKeyword = ref("");
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);

const form = ref({
  itemId: "",
  title: "",
  reply: "",
  replyOnce: false,
});
const batchForm = ref({
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

const tableRows = computed<ItemReplyTableRow[]>(() => {
  const rows: ItemReplyTableRow[] = [];
  const replyMap = new Map(
    replies.value.map((reply) => [
      `${reply.cookie_id}::${reply.item_id}`,
      reply,
    ]),
  );

  items.value.forEach((item) => {
    const key = `${item.cookie_id}::${item.item_id}`;
    const reply = replyMap.get(key);

    rows.push({
      ...reply,
      cookie_id: item.cookie_id,
      item_id: item.item_id,
      title: reply?.title || item.item_title || item.title || "",
      item_title: reply?.item_title || item.item_title || item.title || "",
      reply: reply?.reply || reply?.reply_content || reply?.content || "",
      reply_content:
        reply?.reply_content || reply?.reply || reply?.content || "",
      reply_once: Boolean(reply?.reply_once),
      primary_image_url: reply?.primary_image_url || item.primary_image_url,
      image_url: reply?.image_url,
      thumbnail_url: reply?.thumbnail_url,
      created_at: reply?.created_at,
      updated_at: reply?.updated_at,
      hasReply: Boolean(reply),
    });

    replyMap.delete(key);
  });

  replyMap.forEach((reply) => {
    rows.push({
      ...reply,
      title: reply.title || reply.item_title || "",
      item_title: reply.item_title || reply.title || "",
      reply: reply.reply || reply.reply_content || reply.content || "",
      reply_content: reply.reply_content || reply.reply || reply.content || "",
      hasReply: true,
    });
  });

  return rows;
});

const filteredTableRows = computed(() => {
  if (replyStatusFilter.value === "configured") {
    return tableRows.value.filter((row) => row.hasReply);
  }
  if (replyStatusFilter.value === "unconfigured") {
    return tableRows.value.filter((row) => !row.hasReply);
  }
  return tableRows.value;
});

const selectedReplyRows = computed(() =>
  selectedRows.value.filter((row) => row.hasReply),
);
const selectedCount = computed(() => selectedRows.value.length);
const selectedRowsGroupedByCookie = computed(() => {
  const groups = new Map<string, ItemReplyTableRow[]>();
  selectedRows.value.forEach((row) => {
    if (!row.cookie_id) return;
    const list = groups.get(row.cookie_id) || [];
    list.push(row);
    groups.set(row.cookie_id, list);
  });
  return groups;
});
const selectedCookieCount = computed(
  () => selectedRowsGroupedByCookie.value.size,
);
const isAllFilteredSelected = computed(() => {
  if (!filteredTableRows.value.length) return false;
  const selectedKeys = new Set(selectedRows.value.map(getReplyRowKey));
  return filteredTableRows.value.every((row) =>
    selectedKeys.has(getReplyRowKey(row)),
  );
});

const canBatchDelete = computed(() => selectedReplyRows.value.length > 0);

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

const getLinkedItem = (row: Pick<ItemReply, "cookie_id" | "item_id">) => {
  return items.value.find(
    (item) => item.cookie_id === row.cookie_id && item.item_id === row.item_id,
  );
};

const getReplyContent = (row: ItemReplyTableRow) =>
  row.reply || row.reply_content || row.content || "未设置";

const getReplyTitle = (row: ItemReplyTableRow) => {
  return (
    row.title ||
    row.item_title ||
    getLinkedItem(row)?.item_title ||
    getLinkedItem(row)?.title ||
    "-"
  );
};

const getReplyImage = (row: ItemReplyTableRow) => {
  const linkedItem = getLinkedItem(row);
  return (
    row.primary_image_url ||
    row.thumbnail_url ||
    row.image_url ||
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

const getReplyRowKey = (row: Pick<ItemReply, "cookie_id" | "item_id">) =>
  `${row.cookie_id}:${row.item_id}`;

const handleSelectionChange = (rows: ItemReplyTableRow[]) => {
  selectedRows.value = rows;
};

const clearSelection = () => {
  selectedRows.value = [];
  tableRef.value?.clearSelection();
};

const handleSelectFilteredRows = async () => {
  if (!filteredTableRows.value.length) {
    ElMessage.warning("当前列表没有可勾选的商品");
    return;
  }

  await nextTick();
  filteredTableRows.value.forEach((row) => {
    tableRef.value?.toggleRowSelection(row, true);
  });
};

const handleToggleSelectAllFiltered = async () => {
  if (!filteredTableRows.value.length) {
    ElMessage.warning("当前列表没有可勾选的商品");
    return;
  }

  if (isAllFilteredSelected.value) {
    clearSelection();
    ElMessage.success("已取消当前列表全选");
    return;
  }

  await handleSelectFilteredRows();
  ElMessage.success(`已选中当前列表 ${filteredTableRows.value.length} 个商品`);
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
  dialogAccountId.value = selectedAccount.value;
  resetForm();
  dialogVisible.value = true;
  if (!items.value.length) {
    await loadItems(selectedAccount.value);
  }
};

const openEditDialog = (row: ItemReplyTableRow) => {
  editingReply.value = row.hasReply ? row : null;
  dialogAccountId.value = row.cookie_id;
  form.value = {
    itemId: row.item_id,
    title: row.title || row.item_title || "",
    reply: row.hasReply ? getReplyContent(row) : "",
    replyOnce: Boolean(row.reply_once),
  };
  dialogVisible.value = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  editingReply.value = null;
  dialogAccountId.value = "";
  resetForm();
};

const resetBatchForm = () => {
  batchForm.value = {
    reply: "",
    replyOnce: false,
  };
};

const openBatchDialog = () => {
  if (!selectedCount.value) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  resetBatchForm();
  batchDialogVisible.value = true;
};

const closeBatchDialog = () => {
  batchDialogVisible.value = false;
  resetBatchForm();
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
    cookie_id:
      editingReply.value?.cookie_id ||
      dialogAccountId.value ||
      selectedAccount.value,
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
        dialogAccountId.value || selectedAccount.value,
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

const handleBatchSubmit = async () => {
  if (!selectedCount.value) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  const replyContent = batchForm.value.reply.trim();
  if (!replyContent) {
    ElMessage.warning("请输入回复内容");
    return;
  }

  batchSaving.value = true;
  try {
    const results = await Promise.allSettled(
      selectedRows.value.map((row) =>
        updateItemReply(row.cookie_id, row.item_id, {
          reply_content: replyContent,
          reply_once: batchForm.value.replyOnce,
        }),
      ),
    );

    const successCount = results.filter(
      (result) => result.status === "fulfilled",
    ).length;
    const failedCount = results.length - successCount;

    if (!successCount) {
      throw new Error("批量保存失败");
    }

    ElMessage[failedCount ? "warning" : "success"](
      `批量保存完成：成功 ${successCount}，失败 ${failedCount}`,
    );
    closeBatchDialog();
    clearSelection();
    await loadReplies();
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量保存失败";
    ElMessage.error(message);
  } finally {
    batchSaving.value = false;
  }
};

const handleDelete = async (reply: ItemReplyTableRow) => {
  if (!reply.hasReply) {
    ElMessage.warning("该商品还没有配置回复");
    return;
  }

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

const handleBatchDelete = async () => {
  if (!canBatchDelete.value) {
    ElMessage.warning("请先勾选已配置回复的商品");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定批量删除 ${selectedReplyRows.value.length} 条商品回复吗？`,
      "批量删除确认",
      {
        type: "warning",
        confirmButtonText: "批量删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  batchDeleting.value = true;
  try {
    const response = await batchDeleteItemReplies(
      selectedReplyRows.value.map((row) => ({
        cookie_id: row.cookie_id,
        item_id: row.item_id,
      })),
    );
    if (!response.success) {
      throw new Error(
        response.detail || response.message || response.msg || "批量删除失败",
      );
    }

    const successCount = response.data?.success_count ?? 0;
    const failedCount =
      response.data?.failed_count ??
      Math.max(selectedReplyRows.value.length - successCount, 0);
    ElMessage[failedCount ? "warning" : "success"](
      `批量删除完成：成功 ${successCount}，失败 ${failedCount}`,
    );
    clearSelection();
    await loadReplies();
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量删除失败";
    ElMessage.error(message);
  } finally {
    batchDeleting.value = false;
  }
};

watch(selectedAccount, async (value) => {
  clearSelection();
  await Promise.all([loadReplies(), loadItems(value || undefined)]);
});

watch(replyStatusFilter, () => {
  clearSelection();
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
        <el-button
          type="primary"
          plain
          :disabled="!selectedCount"
          @click="openBatchDialog"
        >
          批量设置回复
        </el-button>
        <el-button
          type="danger"
          plain
          :icon="Delete"
          :loading="batchDeleting"
          :disabled="!canBatchDelete"
          @click="handleBatchDelete"
        >
          批量删除
        </el-button>
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

        <el-form-item label="回复状态">
          <el-select v-model="replyStatusFilter" placeholder="全部状态">
            <el-option label="全部" value="all" />
            <el-option label="仅看已配置" value="configured" />
            <el-option label="仅看未配置" value="unconfigured" />
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
        <div class="toolbar-meta">
          当前显示 {{ filteredTableRows.length }} 个商品，共
          {{ tableRows.length }} 个商品，已配置
          {{ replies.length }} 条商品回复，已勾选
          {{ selectedCount }} 个商品，其中已配置
          {{ selectedReplyRows.length }} 条
        </div>
        <div class="toolbar-actions">
          <el-button link type="primary" @click="handleToggleSelectAllFiltered">
            {{ isAllFilteredSelected ? "取消当前列表全选" : "全选当前列表" }}
          </el-button>
          <el-button link :disabled="!selectedCount" @click="clearSelection">
            清空勾选
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredTableRows"
        :row-key="getReplyRowKey"
        style="width: 100%; margin-top: 16px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" reserve-selection />
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
            <span
              class="text-ellipsis"
              :class="{ 'text-muted': !row.hasReply }"
            >
              {{ getReplyContent(row) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="回复限制" width="140">
          <template #default="{ row }">
            <el-tag
              :type="
                row.hasReply ? (row.reply_once ? 'warning' : 'info') : 'info'
              "
              effect="plain"
            >
              {{
                row.hasReply
                  ? row.reply_once
                    ? "每客户一次"
                    : "不限制"
                  : "未设置"
              }}
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
              <el-button link type="primary" @click="openEditDialog(row)">{{
                row.hasReply ? "编辑" : "设置回复"
              }}</el-button>
              <el-button
                v-if="row.hasReply"
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
          <el-empty description="暂无商品数据，请先同步商品" />
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
            :model-value="
              dialogAccountId || editingReply?.cookie_id || selectedAccount
            "
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

    <el-dialog
      v-model="batchDialogVisible"
      title="批量设置商品回复"
      width="640px"
      destroy-on-close
      @closed="closeBatchDialog"
    >
      <el-form label-position="top">
        <el-form-item label="批量范围">
          <div class="reply-item-summary">
            <div class="reply-item-title">已选择 {{ selectedCount }} 个商品</div>
            <div class="reply-item-meta">
              涉及 {{ selectedCookieCount }} 个账号，保存后会覆盖这些商品当前回复
            </div>
          </div>
        </el-form-item>

        <el-form-item label="回复内容">
          <el-input
            v-model="batchForm.reply"
            type="textarea"
            :rows="5"
            placeholder="支持变量：{send_user_name}、{send_user_id}、{send_message}、{item_id}"
          />
        </el-form-item>

        <el-form-item label="每客户只回复一次">
          <el-switch v-model="batchForm.replyOnce" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeBatchDialog">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="handleBatchSubmit"
          >批量保存</el-button
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

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-meta {
  color: #606266;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.reply-item-summary {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: var(--el-fill-color-lighter);
}

.reply-item-title {
  color: #0f172a;
  font-weight: 600;
}

.reply-item-meta {
  margin-top: 4px;
  color: #606266;
  font-size: 13px;
}

@media (max-width: 768px) {
  .inline-form :deep(.el-select) {
    width: 100%;
  }
}
</style>
