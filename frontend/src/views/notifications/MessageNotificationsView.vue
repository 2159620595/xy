<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  CopyDocument,
  Delete,
  Download,
  Plus,
  RefreshRight,
  Search,
  Select,
  SwitchButton,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import { getAccountDetails } from "@/api/accounts";
import {
  deleteAccountNotifications,
  deleteMessageNotification,
  getMessageNotifications,
  getNotificationChannels,
  setMessageNotification,
} from "@/api/notifications";
import type { AccountDetail, MessageNotification, NotificationChannel } from "@/types";

const loading = ref(true);
const saving = ref(false);
const dialogVisible = ref(false);
const notifications = ref<MessageNotification[]>([]);
const channels = ref<NotificationChannel[]>([]);
const accounts = ref<AccountDetail[]>([]);
const selectedRows = ref<MessageNotification[]>([]);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);
const bulkDeleting = ref(false);
const keyword = ref("");
const statusFilter = ref<"all" | "enabled" | "disabled">("all");

const form = reactive({
  accountId: "",
  channelId: "",
  enabled: true,
});

const totalCount = computed(() => notifications.value.length);
const filteredNotifications = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  return notifications.value.filter((item) => {
    if (statusFilter.value === "enabled" && !item.enabled) {
      return false;
    }
    if (statusFilter.value === "disabled" && item.enabled) {
      return false;
    }

    if (!query) {
      return true;
    }

    const target = [
      item.cookie_id,
      getAccountLabel(item.cookie_id),
      item.channel_name || getChannelLabel(item.channel_id),
      item.channel_id,
      item.enabled ? "启用" : "禁用",
    ]
      .join(" ")
      .toLowerCase();

    return target.includes(query);
  });
});
const selectedNotificationIds = computed(() =>
  selectedRows.value
    .map((item) => String(item.id || ""))
    .filter((id) => Boolean(id)),
);
const selectedAccountIds = computed(() =>
  selectedRows.value.map((item) => item.cookie_id).filter(Boolean),
);
const selectedExportRows = computed(() =>
  selectedRows.value.map((item) => ({
    cookie_id: item.cookie_id,
    account_label: getAccountLabel(item.cookie_id),
    channel_id: String(item.channel_id),
    channel_name: item.channel_name || getChannelLabel(item.channel_id),
    enabled: item.enabled ? "启用" : "禁用",
  })),
);
const exportRows = computed(() =>
  filteredNotifications.value.map((item) => ({
    cookie_id: item.cookie_id,
    account_label: getAccountLabel(item.cookie_id),
    channel_id: String(item.channel_id),
    channel_name: item.channel_name || getChannelLabel(item.channel_id),
    enabled: item.enabled ? "启用" : "禁用",
  })),
);

const getAccountLabel = (cookieId: string) => {
  const account = accounts.value.find((item) => item.id === cookieId);
  if (!account) return cookieId;
  return account.xianyu_nickname
    ? `${cookieId}（${account.xianyu_nickname}）`
    : cookieId;
};

const getChannelLabel = (channelId: number) => {
  const channel = channels.value.find((item) => Number(item.id) === channelId);
  return channel?.name || `渠道 ${channelId}`;
};

const resetForm = () => {
  form.accountId = "";
  form.channelId = "";
  form.enabled = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

const openDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const loadData = async () => {
  loading.value = true;
  try {
    const [notificationResult, channelResult, accountResult] = await Promise.all([
      getMessageNotifications(),
      getNotificationChannels(),
      getAccountDetails(),
    ]);
    notifications.value = notificationResult.data || [];
    channels.value = channelResult.data || [];
    accounts.value = accountResult;
  } catch {
    ElMessage.error("加载消息通知失败");
    notifications.value = [];
  } finally {
    loading.value = false;
  }
};

const handleSelectionChange = (rows: MessageNotification[]) => {
  selectedRows.value = rows;
};

const clearSelection = () => {
  selectedRows.value = [];
  tableRef.value?.clearSelection();
};

const handleSelectFilteredRows = () => {
  if (!filteredNotifications.value.length) {
    ElMessage.warning("当前没有可勾选的通知规则");
    return;
  }

  tableRef.value?.clearSelection();
  filteredNotifications.value.forEach((row) => {
    tableRef.value?.toggleRowSelection(row, true);
  });
  ElMessage.success(`已勾选 ${filteredNotifications.value.length} 条通知规则`);
};

const downloadTextFile = (
  filename: string,
  content: string,
  mimeType: string,
) => {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

const buildExportFilename = (
  scope: "filtered" | "selected",
  extension: "json" | "csv",
) => {
  const time = new Date().toISOString().replace(/[:.]/g, "-");
  return `message-notifications-${scope}-${time}.${extension}`;
};

const escapeCsvCell = (value: string) => `"${value.replace(/"/g, '""')}"`;

const exportAsCsv = (
  rows: Array<Record<string, string>>,
  scope: "filtered" | "selected",
) => {
  const fields = Object.keys(rows[0] || {});
  const header = fields.map(escapeCsvCell).join(",");
  const body = rows
    .map((row) => fields.map((field) => escapeCsvCell(row[field] || "")).join(","))
    .join("\n");

  downloadTextFile(
    buildExportFilename(scope, "csv"),
    `${header}\n${body}`,
    "text/csv;charset=utf-8",
  );
};

const handleExportFilteredJson = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的通知规则");
    return;
  }

  downloadTextFile(
    buildExportFilename("filtered", "json"),
    JSON.stringify(exportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${exportRows.value.length} 条筛选规则`);
};

const handleExportFilteredCsv = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的通知规则");
    return;
  }

  exportAsCsv(exportRows.value, "filtered");
  ElMessage.success(`已导出 ${exportRows.value.length} 条筛选规则`);
};

const handleExportSelectedJson = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的规则");
    return;
  }

  downloadTextFile(
    buildExportFilename("selected", "json"),
    JSON.stringify(selectedExportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选规则`);
};

const handleExportSelectedCsv = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的规则");
    return;
  }

  exportAsCsv(selectedExportRows.value, "selected");
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选规则`);
};

const handleCopySelectedAccounts = async () => {
  if (!selectedAccountIds.value.length) {
    ElMessage.warning("请先勾选规则");
    return;
  }

  try {
    await navigator.clipboard.writeText(selectedAccountIds.value.join("\n"));
    ElMessage.success(`已复制 ${selectedAccountIds.value.length} 个账号标识`);
  } catch {
    ElMessage.error("复制失败");
  }
};

const handleSubmit = async () => {
  if (!form.accountId) {
    ElMessage.warning("请选择账号");
    return;
  }
  if (!form.channelId) {
    ElMessage.warning("请选择通知渠道");
    return;
  }

  saving.value = true;
  try {
    await setMessageNotification(
      form.accountId,
      Number(form.channelId),
      form.enabled,
    );
    ElMessage.success("通知已添加");
    closeDialog();
    await loadData();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const handleToggle = async (row: MessageNotification) => {
  try {
    await setMessageNotification(row.cookie_id, row.channel_id, !row.enabled);
    ElMessage.success(row.enabled ? "通知已禁用" : "通知已启用");
    await loadData();
  } catch {
    ElMessage.error("操作失败");
  }
};

const handleDisable = async (row: MessageNotification) => {
  try {
    await ElMessageBox.confirm(
      "确定要删除这条消息通知吗？删除后需要重新绑定账号与通知渠道。",
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  if (!row.id) {
    ElMessage.error("当前通知缺少 ID，暂时无法删除");
    return;
  }

  try {
    await deleteMessageNotification(String(row.id));
    ElMessage.success("通知已删除");
    await loadData();
  } catch {
    ElMessage.error("操作失败");
  }
};

const handleBatchDelete = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning("请先勾选要删除的规则");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定删除 ${selectedRows.value.length} 条消息通知规则吗？`,
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

  bulkDeleting.value = true;
  let successCount = 0;
  let failedMessage = "";

  try {
    for (const row of selectedRows.value) {
      if (!row.id) {
        failedMessage = "部分规则缺少 ID，无法继续删除";
        break;
      }

      try {
        await deleteMessageNotification(String(row.id));
        successCount += 1;
      } catch {
        failedMessage = `规则 ${row.cookie_id} / ${row.channel_id} 删除失败`;
        break;
      }
    }

    if (failedMessage) {
      ElMessage.error(`已删除 ${successCount} 条，剩余删除中断：${failedMessage}`);
    } else {
      ElMessage.success(`已批量删除 ${successCount} 条通知规则`);
    }

    clearSelection();
    await loadData();
  } finally {
    bulkDeleting.value = false;
  }
};

const handleDeleteAccountRules = async (cookieId: string) => {
  try {
    await ElMessageBox.confirm(
      `确定删除账号 ${getAccountLabel(cookieId)} 的全部消息通知规则吗？`,
      "账号规则删除确认",
      {
        type: "warning",
        confirmButtonText: "删除全部",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  try {
    await deleteAccountNotifications(cookieId);
    ElMessage.success("该账号的消息通知规则已删除");
    clearSelection();
    await loadData();
  } catch {
    ElMessage.error("删除失败");
  }
};

onMounted(async () => {
  await loadData();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">消息通知</h1>
        <p class="page-description">将账号与通知渠道绑定，启用后可按账号接收消息通知。</p>
      </div>
      <div class="page-actions">
        <el-button :icon="Plus" type="primary" @click="openDialog">添加通知</el-button>
        <el-button :icon="RefreshRight" @click="loadData">刷新</el-button>
      </div>
    </section>

    <el-card shadow="never">
      <div class="inline-form">
        <el-form-item label="搜索规则">
          <el-input
            v-model="keyword"
            clearable
            :prefix-icon="Search"
            placeholder="搜索账号、渠道或状态"
          />
        </el-form-item>
        <el-form-item label="状态筛选">
          <el-select v-model="statusFilter" style="width: 180px">
            <el-option label="全部状态" value="all" />
            <el-option label="仅启用" value="enabled" />
            <el-option label="仅禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </div>

      <div class="table-toolbar">
        <div class="toolbar-meta">
          当前展示 {{ filteredNotifications.length }} / {{ totalCount }} 条通知规则
        </div>
        <div class="table-toolbar-actions">
          <el-tag v-if="selectedRows.length" type="success" effect="plain">
            已勾选 {{ selectedRows.length }} 条
          </el-tag>
          <el-tag type="primary" effect="plain">规则绑定在账号维度</el-tag>
          <el-button link :icon="Download" @click="handleExportFilteredJson">
            导出筛选 JSON
          </el-button>
          <el-button link :icon="Download" @click="handleExportFilteredCsv">
            导出筛选 CSV
          </el-button>
          <el-button
            link
            :icon="Download"
            :disabled="!selectedRows.length"
            @click="handleExportSelectedJson"
          >
            导出勾选 JSON
          </el-button>
          <el-button
            link
            :icon="Download"
            :disabled="!selectedRows.length"
            @click="handleExportSelectedCsv"
          >
            导出勾选 CSV
          </el-button>
          <el-button link :icon="Select" :disabled="!filteredNotifications.length" @click="handleSelectFilteredRows">
            勾选筛选结果
          </el-button>
          <el-button
            link
            :icon="CopyDocument"
            :disabled="!selectedRows.length"
            @click="handleCopySelectedAccounts"
          >
            复制勾选账号
          </el-button>
          <el-button
            link
            type="danger"
            :disabled="!selectedRows.length"
            @click="clearSelection"
          >
            清空勾选
          </el-button>
          <el-button
            link
            type="danger"
            :icon="Delete"
            :disabled="!selectedNotificationIds.length"
            :loading="bulkDeleting"
            @click="handleBatchDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredNotifications"
        style="width: 100%; margin-top: 16px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" />
        <el-table-column label="账号" min-width="220">
          <template #default="{ row }">
            <span>{{ getAccountLabel(row.cookie_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="通知渠道" min-width="180">
          <template #default="{ row }">
            <span>{{ row.channel_name || getChannelLabel(row.channel_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain">
              {{ row.enabled ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="220" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="SwitchButton" @click="handleToggle(row)">
                {{ row.enabled ? "禁用" : "启用" }}
              </el-button>
              <el-button link :icon="Delete" @click="handleDeleteAccountRules(row.cookie_id)">
                删账号规则
              </el-button>
              <el-button link type="danger" :icon="Delete" @click="handleDisable(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无消息通知配置" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="添加消息通知"
      width="620px"
      destroy-on-close
      @closed="closeDialog"
    >
      <el-form label-position="top">
        <el-form-item label="选择账号">
          <el-select v-model="form.accountId" placeholder="请选择账号" style="width: 100%">
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

        <el-form-item label="选择通知渠道">
          <el-select v-model="form.channelId" placeholder="请选择通知渠道" style="width: 100%">
            <el-option
              v-for="channel in channels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="启用此通知">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
