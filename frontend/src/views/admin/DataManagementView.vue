<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  ArrowDown,
  CircleCheck,
  CopyDocument,
  Download,
  Document,
  FolderOpened,
  Delete,
  RefreshRight,
  Search,
  Select,
  Upload,
  View,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import {
  clearTableData,
  deleteTableRecord,
  getBackupFiles,
  getTableData,
  reloadSystemCache,
  uploadDatabaseBackup,
} from "@/api/admin";
const tableOptions = [
  { value: "default_replies", label: "默认回复表" },
  { value: "keywords", label: "关键词表" },
  { value: "cookies", label: "账号表" },
  { value: "cards", label: "卡券表" },
  { value: "orders", label: "订单表" },
  { value: "item_info", label: "商品信息表" },
  { value: "notification_channels", label: "通知渠道表" },
  { value: "delivery_rules", label: "发货规则表" },
  { value: "risk_control_logs", label: "风控日志表" },
] as const;

const COLUMN_STORAGE_KEY = "admin_data_management_visible_columns";

const selectedTable =
  ref<(typeof tableOptions)[number]["value"]>("default_replies");
const loading = ref(false);
const clearing = ref(false);
const deletingRecordId = ref("");
const bulkDeleting = ref(false);
const primaryKeyQuery = ref("");
const rowKeywordQuery = ref("");
const columnQuery = ref("");
const uploading = ref(false);
const reloadingCache = ref(false);
const loadingBackups = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const detailDrawerVisible = ref(false);
const detailRowTitle = ref("");
const detailRowJson = ref("");
const selectedColumns = ref<string[]>([]);
const selectedRows = ref<Record<string, unknown>[]>([]);
const compareDrawerVisible = ref(false);
const compareOnlyDifferences = ref(true);
const tableData = ref<Record<string, unknown>[]>([]);
const columns = ref<string[]>([]);
const count = ref(0);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);
const backups = ref<
  Array<{
    filename: string;
    size_mb: number;
    modified_time: string;
  }>
>([]);
const lastRestoreResult = ref<{
  filename: string;
  userCount?: number;
  restoredAt: string;
} | null>(null);

const recordPrimaryKeyMap: Partial<
  Record<(typeof tableOptions)[number]["value"], string>
> = {
  default_replies: "id",
  keywords: "id",
  cookies: "id",
  cards: "id",
  orders: "order_id",
  item_info: "id",
  notification_channels: "id",
  delivery_rules: "id",
};

const recordPrimaryKey = computed(
  () => recordPrimaryKeyMap[selectedTable.value] || "",
);
const selectedTableLabel = computed(
  () =>
    tableOptions.find((item) => item.value === selectedTable.value)?.label ||
    selectedTable.value,
);
const canDeleteSingleRecord = computed(() => Boolean(recordPrimaryKey.value));
const canOperateRows = computed(() => columns.value.length > 0);
const canCompareRows = computed(() => selectedRows.value.length === 2);
const pagedDeletableRows = computed(() =>
  pagedRows.value.filter((row) => Boolean(getRecordId(row))),
);
const deletableSelectedRows = computed(() =>
  selectedRows.value.filter((row) => Boolean(getRecordId(row))),
);
const canBulkDeleteRows = computed(
  () => canDeleteSingleRecord.value && deletableSelectedRows.value.length > 0,
);
const canSelectCurrentPageRows = computed(
  () => canDeleteSingleRecord.value && pagedDeletableRows.value.length > 0,
);
const selectedRecordIds = computed(() =>
  deletableSelectedRows.value
    .map((row) => getRecordId(row))
    .filter((id) => Boolean(id)),
);
const filteredRecordIds = computed(() =>
  filteredRows.value.map((row) => getRecordId(row)).filter((id) => Boolean(id)),
);
const filteredColumns = computed(() => {
  const query = columnQuery.value.trim().toLowerCase();
  if (!query) {
    return columns.value;
  }

  return columns.value.filter((column) => column.toLowerCase().includes(query));
});
const displayColumns = computed(() => {
  const selected = selectedColumns.value.length
    ? selectedColumns.value
    : columns.value;
  return filteredColumns.value.filter((column) => selected.includes(column));
});
const filteredRows = computed(() => {
  const primaryKeyKeyword = primaryKeyQuery.value.trim();
  const rowKeyword = rowKeywordQuery.value.trim().toLowerCase();

  return tableData.value.filter((row) => {
    if (primaryKeyKeyword && recordPrimaryKey.value) {
      if (!getRecordId(row).includes(primaryKeyKeyword)) {
        return false;
      }
    }

    if (rowKeyword) {
      const values = columns.value.length
        ? columns.value.map((column) =>
            formatCellValue(row[column]).toLowerCase(),
          )
        : Object.values(row).map((value) =>
            formatCellValue(value).toLowerCase(),
          );

      if (!values.some((value) => value.includes(rowKeyword))) {
        return false;
      }
    }

    return true;
  });
});
const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredRows.value.slice(start, start + pageSize.value);
});
const latestBackup = computed(() => backups.value[0] || null);
const backupCount = computed(() => backups.value.length);
const matchedCount = computed(() => filteredRows.value.length);
const visibleColumnCount = computed(
  () => displayColumns.value.length || columns.value.length,
);
const activeFilterCount = computed(() => {
  let count = 0;

  if (primaryKeyQuery.value.trim()) count += 1;
  if (rowKeywordQuery.value.trim()) count += 1;
  if (columnQuery.value.trim()) count += 1;
  if (
    columns.value.length &&
    selectedColumns.value.length > 0 &&
    selectedColumns.value.length !== columns.value.length
  ) {
    count += 1;
  }

  return count;
});
const totalPages = computed(() =>
  Math.max(Math.ceil(matchedCount.value / pageSize.value), 1),
);
const hiddenRowsCount = computed(() =>
  Math.max(filteredRows.value.length - pagedRows.value.length, 0),
);
const allColumnsSelected = computed(
  () =>
    columns.value.length > 0 &&
    selectedColumns.value.length === columns.value.length,
);
const exportRows = computed(() =>
  filteredRows.value.map((row) => {
    const nextRow: Record<string, string> = {};
    const fields = displayColumns.value.length
      ? displayColumns.value
      : columns.value;

    fields.forEach((field) => {
      nextRow[field] = formatCellValue(row[field], true);
    });

    return nextRow;
  }),
);
const selectedExportRows = computed(() =>
  selectedRows.value.map((row) => {
    const nextRow: Record<string, string> = {};
    const fields = displayColumns.value.length
      ? displayColumns.value
      : columns.value;

    fields.forEach((field) => {
      nextRow[field] = formatCellValue(row[field], true);
    });

    return nextRow;
  }),
);
const compareRows = computed(() =>
  selectedRows.value.slice(0, 2).map((row, index) => ({
    title: getRecordId(row)
      ? `记录 ${index + 1} / ${getRecordId(row)}`
      : `记录 ${index + 1}`,
    row,
  })),
);
const compareFields = computed(() => {
  const [left, right] = selectedRows.value;
  if (!left || !right) {
    return [];
  }

  const fieldSource = displayColumns.value.length
    ? displayColumns.value
    : columns.value;

  return fieldSource
    .map((field) => {
      const leftValue = formatCellValue(left[field], true);
      const rightValue = formatCellValue(right[field], true);
      const same = leftValue === rightValue;

      return {
        field,
        leftValue,
        rightValue,
        same,
      };
    })
    .filter((item) => (compareOnlyDifferences.value ? !item.same : true));
});

const getRecordId = (row: Record<string, unknown>) => {
  if (!recordPrimaryKey.value) return "";
  const value = row[recordPrimaryKey.value];
  if (value === null || value === undefined || value === "") return "";
  return String(value);
};

const formatDateTime = (value?: string) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const formatCellValue = (value: unknown, pretty = false) => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, pretty ? 2 : 0);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

const getCellPreview = (value: unknown) => {
  const text = formatCellValue(value);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
};

const getStoredVisibleColumns = (
  tableName: string,
  availableColumns: string[],
) => {
  const raw = localStorage.getItem(COLUMN_STORAGE_KEY);
  if (!raw) {
    return [...availableColumns];
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, string[]>;
    const stored = parsed[tableName] || [];
    const valid = stored.filter((column) => availableColumns.includes(column));
    return valid.length ? valid : [...availableColumns];
  } catch {
    return [...availableColumns];
  }
};

const persistVisibleColumns = (tableName: string, nextColumns: string[]) => {
  const raw = localStorage.getItem(COLUMN_STORAGE_KEY);
  let parsed: Record<string, string[]> = {};

  if (raw) {
    try {
      parsed = JSON.parse(raw) as Record<string, string[]>;
    } catch {
      parsed = {};
    }
  }

  parsed[tableName] = nextColumns;
  localStorage.setItem(COLUMN_STORAGE_KEY, JSON.stringify(parsed));
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

const buildExportFilename = (extension: "json" | "csv") => {
  const time = new Date().toISOString().replace(/[:.]/g, "-");
  return `${selectedTable.value}-${time}.${extension}`;
};

const handleTableChange = async () => {
  primaryKeyQuery.value = "";
  rowKeywordQuery.value = "";
  columnQuery.value = "";
  currentPage.value = 1;
  compareDrawerVisible.value = false;
  await loadTableData();
};

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
};

const resolveErrorMessage = (error: unknown, fallback: string) =>
  error &&
  typeof error === "object" &&
  "response" in error &&
  error.response &&
  typeof error.response === "object" &&
  "data" in error.response &&
  error.response.data &&
  typeof error.response.data === "object"
    ? ((error.response.data as { detail?: string }).detail ?? fallback)
    : fallback;

const handleCopyRecordId = async (row: Record<string, unknown>) => {
  const recordId = getRecordId(row);
  if (!recordId) {
    ElMessage.warning("当前记录缺少主键，无法复制");
    return;
  }

  await copyText(recordId);
  ElMessage.success("主键已复制");
};

const handleCopyRowJson = async (row: Record<string, unknown>) => {
  await copyText(JSON.stringify(row, null, 2));
  ElMessage.success("记录 JSON 已复制");
};

const handlePreviewRow = (row: Record<string, unknown>) => {
  detailRowTitle.value = getRecordId(row)
    ? `${selectedTableLabel.value} / ${getRecordId(row)}`
    : selectedTableLabel.value;
  detailRowJson.value = JSON.stringify(row, null, 2);
  detailDrawerVisible.value = true;
};

const clearSelectedRows = () => {
  selectedRows.value = [];
  compareDrawerVisible.value = false;
  tableRef.value?.clearSelection();
};

const handleSelectCurrentPageRows = () => {
  if (!canSelectCurrentPageRows.value) {
    ElMessage.warning("当前页没有可勾选的记录");
    return;
  }

  tableRef.value?.clearSelection();
  pagedDeletableRows.value.forEach((row) => {
    tableRef.value?.toggleRowSelection(row, true);
  });
  ElMessage.success(`已勾选当前页 ${pagedDeletableRows.value.length} 条记录`);
};

const handleSelectionChange = (rows: Record<string, unknown>[]) => {
  selectedRows.value = rows;
};

const handleOpenCompare = () => {
  if (!canCompareRows.value) {
    ElMessage.warning("请先勾选两条记录再进行对比");
    return;
  }

  compareDrawerVisible.value = true;
};

const resetVisibleColumns = () => {
  selectedColumns.value = [...columns.value];
};

const handleSelectAllColumns = () => {
  selectedColumns.value = [...columns.value];
};

const handleInvertColumns = () => {
  if (!columns.value.length) {
    return;
  }

  const nextColumns = columns.value.filter(
    (column) => !selectedColumns.value.includes(column),
  );

  selectedColumns.value = nextColumns.length ? nextColumns : [...columns.value];
};

const handleExportJson = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的筛选结果");
    return;
  }

  downloadTextFile(
    buildExportFilename("json"),
    JSON.stringify(exportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success("已导出 JSON");
};

const handleExportSelectedJson = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的记录");
    return;
  }

  downloadTextFile(
    buildExportFilename("json"),
    JSON.stringify(selectedExportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选记录`);
};

const escapeCsvCell = (value: string) => `"${value.replace(/"/g, '""')}"`;

const handleExportCsv = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的筛选结果");
    return;
  }

  const fields = displayColumns.value.length
    ? displayColumns.value
    : columns.value;
  const header = fields.map(escapeCsvCell).join(",");
  const body = exportRows.value
    .map((row) =>
      fields.map((field) => escapeCsvCell(row[field] || "")).join(","),
    )
    .join("\n");

  downloadTextFile(
    buildExportFilename("csv"),
    `${header}\n${body}`,
    "text/csv;charset=utf-8",
  );
  ElMessage.success("已导出 CSV");
};

const handleExportSelectedCsv = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的记录");
    return;
  }

  const fields = displayColumns.value.length
    ? displayColumns.value
    : columns.value;
  const header = fields.map(escapeCsvCell).join(",");
  const body = selectedExportRows.value
    .map((row) =>
      fields.map((field) => escapeCsvCell(row[field] || "")).join(","),
    )
    .join("\n");

  downloadTextFile(
    buildExportFilename("csv"),
    `${header}\n${body}`,
    "text/csv;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选记录`);
};

const handleExportCommand = (
  command:
    | "export-json"
    | "export-csv"
    | "export-selected-json"
    | "export-selected-csv",
) => {
  switch (command) {
    case "export-json":
      handleExportJson();
      break;
    case "export-csv":
      handleExportCsv();
      break;
    case "export-selected-json":
      handleExportSelectedJson();
      break;
    case "export-selected-csv":
      handleExportSelectedCsv();
      break;
  }
};

const handleSelectionCommand = (
  command:
    | "select-current-page"
    | "copy-selected-record-ids"
    | "copy-filtered-record-ids"
    | "clear-selected-rows",
) => {
  switch (command) {
    case "select-current-page":
      handleSelectCurrentPageRows();
      break;
    case "copy-selected-record-ids":
      void handleCopySelectedRecordIds();
      break;
    case "copy-filtered-record-ids":
      void handleCopyFilteredRecordIds();
      break;
    case "clear-selected-rows":
      clearSelectedRows();
      break;
  }
};

const handleColumnCommand = (command: "reset" | "select-all" | "invert") => {
  switch (command) {
    case "reset":
      resetVisibleColumns();
      break;
    case "select-all":
      handleSelectAllColumns();
      break;
    case "invert":
      handleInvertColumns();
      break;
  }
};

const handleCopySelectedRecordIds = async () => {
  if (!selectedRecordIds.value.length) {
    ElMessage.warning("请先勾选带主键的记录");
    return;
  }

  await copyText(selectedRecordIds.value.join("\n"));
  ElMessage.success(`已复制 ${selectedRecordIds.value.length} 条勾选主键`);
};

const handleCopyFilteredRecordIds = async () => {
  if (!canDeleteSingleRecord.value) {
    ElMessage.warning("当前表未识别主键，无法复制主键列表");
    return;
  }
  if (!filteredRecordIds.value.length) {
    ElMessage.warning("当前没有可复制的筛选主键");
    return;
  }

  await copyText(filteredRecordIds.value.join("\n"));
  ElMessage.success(`已复制 ${filteredRecordIds.value.length} 条筛选主键`);
};

const loadBackups = async (showError = false) => {
  loadingBackups.value = true;
  try {
    const result = await getBackupFiles();
    backups.value = (result.backups || []).map((item) => ({
      filename: item.filename,
      size_mb: item.size_mb,
      modified_time: item.modified_time,
    }));
  } catch {
    backups.value = [];
    if (showError) {
      ElMessage.error("加载备份列表失败");
    }
  } finally {
    loadingBackups.value = false;
  }
};

const loadTableData = async () => {
  loading.value = true;
  try {
    const result = await getTableData(selectedTable.value);
    tableData.value = result.data || [];
    columns.value = result.columns || [];
    selectedColumns.value = getStoredVisibleColumns(
      selectedTable.value,
      result.columns || [],
    );
    count.value = result.count || 0;
    await nextTick();
    clearSelectedRows();
  } catch {
    tableData.value = [];
    columns.value = [];
    selectedColumns.value = [];
    count.value = 0;
    ElMessage.error("加载数据失败");
  } finally {
    loading.value = false;
  }
};

const handleClearTable = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要清空 ${selectedTableLabel.value} 吗？当前共有 ${count.value} 条记录，此操作不可恢复。`,
      "高风险操作",
      {
        type: "warning",
        confirmButtonText: "清空",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  clearing.value = true;
  try {
    await clearTableData(selectedTable.value);
    ElMessage.success("清空成功");
    await loadTableData();
  } catch (error) {
    const message = resolveErrorMessage(error, "清空失败");
    ElMessage.error(message);
  } finally {
    clearing.value = false;
  }
};

const handleReloadCache = async () => {
  reloadingCache.value = true;
  try {
    const result = await reloadSystemCache();
    ElMessage.success(result.message || "系统缓存已刷新");
  } catch {
    ElMessage.error("刷新缓存失败");
  } finally {
    reloadingCache.value = false;
  }
};

const handleDeleteRecord = async (row: Record<string, unknown>) => {
  const recordId = getRecordId(row);
  if (!recordId) {
    ElMessage.warning("当前记录缺少主键，无法删除");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除 ${selectedTableLabel.value} 中主键为 ${recordId} 的记录吗？此操作不可恢复。`,
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

  deletingRecordId.value = recordId;
  try {
    await deleteTableRecord(selectedTable.value, recordId);
    ElMessage.success("记录已删除");
    await loadTableData();
  } catch (error) {
    const message = resolveErrorMessage(error, "删除失败");
    ElMessage.error(message);
  } finally {
    deletingRecordId.value = "";
  }
};

const handleDeleteSelectedRows = async () => {
  const rows = deletableSelectedRows.value;
  if (!rows.length) {
    ElMessage.warning("请先勾选可删除的记录");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要批量删除 ${rows.length} 条记录吗？此操作不可恢复，建议先确认备份。`,
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
    for (const row of rows) {
      const recordId = getRecordId(row);
      if (!recordId) {
        continue;
      }

      try {
        await deleteTableRecord(selectedTable.value, recordId);
        successCount += 1;
      } catch (error) {
        failedMessage = resolveErrorMessage(error, `记录 ${recordId} 删除失败`);
        break;
      }
    }

    if (failedMessage) {
      ElMessage.error(
        `已删除 ${successCount} 条，剩余删除中断：${failedMessage}`,
      );
    } else {
      ElMessage.success(`已批量删除 ${successCount} 条记录`);
    }

    await loadTableData();
  } finally {
    bulkDeleting.value = false;
  }
};

const handleBackupFileChange = async (uploadFile: { raw?: File }) => {
  const file = uploadFile.raw;
  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".db")) {
    ElMessage.warning("仅支持上传 .db 数据库备份文件");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `即将使用备份文件 ${file.name} 恢复数据库。该操作会覆盖当前数据库内容，是否继续？`,
      "数据库恢复确认",
      {
        type: "warning",
        confirmButtonText: "继续恢复",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  uploading.value = true;
  try {
    const result = await uploadDatabaseBackup(file);
    if (result.success) {
      lastRestoreResult.value = {
        filename: result.backup_file || file.name,
        userCount: result.user_count,
        restoredAt: new Date().toISOString(),
      };
      ElMessage.success(result.message || "数据库恢复成功");
      await Promise.all([loadBackups(), loadTableData()]);
    } else {
      ElMessage.error(result.message || result.detail || "恢复失败");
    }
  } catch (error) {
    const message = resolveErrorMessage(error, "恢复失败");
    ElMessage.error(message);
  } finally {
    uploading.value = false;
  }
};

onMounted(async () => {
  await Promise.all([loadTableData(), loadBackups()]);
});

watch([primaryKeyQuery, rowKeywordQuery, pageSize], () => {
  currentPage.value = 1;
});

watch([matchedCount, totalPages], () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

watch([selectedColumns, selectedTable], () => {
  if (!columns.value.length) {
    return;
  }

  const validColumns = selectedColumns.value.filter((column) =>
    columns.value.includes(column),
  );
  persistVisibleColumns(selectedTable.value, validColumns);
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">数据管理</h1>
        <p class="page-description">
          浏览指定表数据、执行清空、刷新缓存和上传数据库备份恢复。
        </p>
      </div>
      <div class="page-actions">
        <el-tag type="warning" effect="plain"> 高风险区域 </el-tag>
        <el-button
          :icon="RefreshRight"
          :loading="reloadingCache"
          @click="handleReloadCache"
        >
          刷新缓存
        </el-button>
      </div>
    </section>

    <section class="control-bar">
      <div class="section-label">
        <el-icon><Select /></el-icon>
        <span>表控制</span>
      </div>
      <div class="data-toolbar">
        <div class="toolbar-block">
          <div class="block-label">选择数据表</div>
          <el-select
            v-model="selectedTable"
            class="table-select"
            @change="handleTableChange"
          >
            <el-option
              v-for="option in tableOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <div class="block-tip">
            切换后会自动刷新字段、可见列配置和勾选状态
          </div>
        </div>

        <div class="toolbar-side">
          <el-alert
            title="清空表、删除记录和数据库恢复都属于高风险操作，执行前请先确认备份。"
            type="warning"
            :closable="false"
            show-icon
          />
          <div class="action-cluster">
            <el-tag type="primary" effect="plain">共 {{ count }} 条记录</el-tag>
            <el-tag type="info" effect="plain"
              >字段 {{ columns.length }} 个</el-tag
            >
            <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
              启用 {{ activeFilterCount }} 个筛选
            </el-tag>
            <el-button
              :icon="RefreshRight"
              :loading="loading"
              @click="loadTableData"
            >
              刷新数据
            </el-button>
            <el-button
              type="danger"
              plain
              :icon="Delete"
              :disabled="count === 0"
              :loading="clearing"
              @click="handleClearTable"
            >
              清空表
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <el-card shadow="never" class="table-panel">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">当前表：{{ selectedTableLabel }}</div>
          <div class="toolbar-submeta">
            显示 {{ matchedCount }} 条匹配记录 /
            {{ visibleColumnCount }} 个可见字段
          </div>
        </div>
        <div class="table-toolbar-actions">
          <div class="toolbar-status-tags">
            <el-tag v-if="selectedRows.length" type="success" effect="plain">
              已勾选 {{ selectedRows.length }} 条
            </el-tag>
            <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
              启用 {{ activeFilterCount }} 个筛选
            </el-tag>
            <el-tag v-if="hiddenRowsCount > 0" type="info" effect="plain">
              已隐藏 {{ hiddenRowsCount }} 条
            </el-tag>
          </div>
          <div class="toolbar-main-actions">
            <el-button
              link
              :icon="View"
              :disabled="!canCompareRows"
              @click="handleOpenCompare"
            >
              对比记录
            </el-button>
            <el-dropdown trigger="click" @command="handleExportCommand">
              <el-button link :icon="Download">
                导出
                <el-icon class="toolbar-chevron"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="export-json">
                    导出 JSON
                  </el-dropdown-item>
                  <el-dropdown-item command="export-csv">
                    导出 CSV
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="export-selected-json"
                    :disabled="!selectedRows.length"
                  >
                    导出勾选 JSON
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="export-selected-csv"
                    :disabled="!selectedRows.length"
                  >
                    导出勾选 CSV
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown trigger="click" @command="handleSelectionCommand">
              <el-button link :icon="CopyDocument">
                选择与复制
                <el-icon class="toolbar-chevron"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    command="select-current-page"
                    :disabled="!canSelectCurrentPageRows"
                  >
                    勾选当前页
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="copy-selected-record-ids"
                    :disabled="!selectedRecordIds.length"
                  >
                    复制勾选主键
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="copy-filtered-record-ids"
                    :disabled="
                      !canDeleteSingleRecord || !filteredRecordIds.length
                    "
                  >
                    复制筛选主键
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="clear-selected-rows"
                    :disabled="!selectedRows.length"
                  >
                    清空勾选
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              link
              type="danger"
              :icon="Delete"
              :disabled="!canBulkDeleteRows"
              :loading="bulkDeleting"
              @click="handleDeleteSelectedRows"
            >
              批量删除
            </el-button>
          </div>
        </div>
      </div>

      <div class="filter-panel">
        <div class="record-filter-row">
          <el-input
            v-if="canDeleteSingleRecord"
            v-model="primaryKeyQuery"
            clearable
            :prefix-icon="Search"
            :placeholder="`按主键 ${recordPrimaryKey} 快速定位记录`"
          />
          <el-input
            v-model="rowKeywordQuery"
            clearable
            :prefix-icon="Search"
            placeholder="按任意字段内容全文筛选"
          />
          <el-input
            v-model="columnQuery"
            clearable
            :prefix-icon="Search"
            placeholder="按列名筛选展示字段"
          />
          <el-select
            v-model="selectedColumns"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择要显示的字段"
          >
            <el-option
              v-for="column in columns"
              :key="column"
              :label="column"
              :value="column"
            />
          </el-select>
        </div>

        <div class="filter-actions">
          <el-dropdown trigger="click" @command="handleColumnCommand">
            <el-button link :icon="Select">
              字段操作
              <el-icon class="toolbar-chevron"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="reset">重置字段</el-dropdown-item>
                <el-dropdown-item
                  command="select-all"
                  :disabled="allColumnsSelected"
                >
                  全选字段
                </el-dropdown-item>
                <el-dropdown-item command="invert">反选字段</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <span class="text-muted filter-tip">
            支持主键定位、全文检索和字段筛选，导出时可选择全部筛选结果或仅导出勾选记录
          </span>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="pagedRows"
        style="width: 100%; margin-top: 16px"
        max-height="640"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" fixed="left" />
        <el-table-column
          v-for="column in displayColumns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="140"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="mono">{{ getCellPreview(row[column]) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="canOperateRows"
          label="操作"
          width="280"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link :icon="View" @click="handlePreviewRow(row)">
                详情
              </el-button>
              <el-button
                v-if="canDeleteSingleRecord"
                link
                :icon="CopyDocument"
                :disabled="!getRecordId(row)"
                @click="handleCopyRecordId(row)"
              >
                复制主键
              </el-button>
              <el-button
                link
                :icon="CopyDocument"
                @click="handleCopyRowJson(row)"
              >
                复制 JSON
              </el-button>
              <el-button
                v-if="canDeleteSingleRecord"
                link
                type="danger"
                :icon="Delete"
                :disabled="!getRecordId(row)"
                :loading="deletingRecordId === getRecordId(row)"
                @click="handleDeleteRecord(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="该表暂无数据" />
        </template>
      </el-table>

      <div class="pagination-row">
        <div class="text-muted">
          当前显示第 {{ currentPage }} 页，共 {{ matchedCount }} 条记录、{{
            displayColumns.length
          }}
          个字段
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :total="matchedCount"
          :page-sizes="[10, 20, 50, 100]"
        />
      </div>
    </el-card>

    <section class="backup-grid">
      <el-card shadow="never" class="backup-panel">
        <template #header>
          <div class="card-title">
            <el-icon><Upload /></el-icon>
            <span>数据库恢复</span>
          </div>
        </template>
        <div class="upload-box">
          <div class="text-muted">
            仅支持上传 `.db` 文件，后端会先校验再替换数据库，属于高风险操作。
          </div>
          <el-alert
            title="恢复成功后会重新初始化数据库连接，建议立即检查账号、订单等核心表是否正常。"
            type="info"
            :closable="false"
            show-icon
          />
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept=".db"
            :on-change="handleBackupFileChange"
          >
            <el-button type="primary" :icon="Upload" :loading="uploading">
              上传并恢复备份
            </el-button>
          </el-upload>
          <div v-if="lastRestoreResult" class="restore-result">
            <div class="restore-title">
              <el-icon><CircleCheck /></el-icon>
              <span>最近一次恢复成功</span>
            </div>
            <div class="text-muted">
              备份文件：{{ lastRestoreResult.filename }}
            </div>
            <div class="text-muted">
              恢复时间：{{ formatDateTime(lastRestoreResult.restoredAt) }}
            </div>
            <div class="text-muted">
              用户校验：
              {{ lastRestoreResult.userCount ?? 0 }} 个用户
            </div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="backup-panel">
        <template #header>
          <div class="card-title">
            <el-icon><FolderOpened /></el-icon>
            <span>服务器备份列表</span>
          </div>
        </template>
        <div class="table-toolbar">
          <div class="toolbar-meta">
            共 {{ backupCount }} 个备份文件
            <span v-if="latestBackup"
              >，最新更新 {{ latestBackup.modified_time }}</span
            >
          </div>
          <el-button
            link
            :icon="RefreshRight"
            :loading="loadingBackups"
            @click="loadBackups(true)"
          >
            刷新列表
          </el-button>
        </div>
        <div
          v-if="backups.length"
          v-loading="loadingBackups"
          class="backup-list"
        >
          <div
            v-for="(backup, index) in backups"
            :key="backup.filename"
            class="backup-item"
          >
            <div class="backup-item-head">
              <div class="backup-name">{{ backup.filename }}</div>
              <el-tag v-if="index === 0" type="success" effect="plain"
                >最新</el-tag
              >
            </div>
            <div class="text-muted">{{ backup.size_mb }} MB</div>
            <div class="text-muted">更新时间：{{ backup.modified_time }}</div>
          </div>
        </div>
        <el-empty v-else :image-size="96" description="暂无备份文件" />
        <div class="backup-tip">
          <el-icon><Document /></el-icon>
          <span
            >建议在执行清空表、批量删除或恢复数据库前，先确认服务器已有最新备份。</span
          >
        </div>
      </el-card>
    </section>

    <el-drawer
      v-model="detailDrawerVisible"
      :title="detailRowTitle || '记录详情'"
      size="42%"
      destroy-on-close
    >
      <div class="drawer-actions">
        <el-button link :icon="CopyDocument" @click="copyText(detailRowJson)">
          复制 JSON
        </el-button>
      </div>
      <pre class="json-preview">{{ detailRowJson }}</pre>
    </el-drawer>

    <el-drawer
      v-model="compareDrawerVisible"
      title="记录对比"
      size="58%"
      destroy-on-close
    >
      <div class="compare-toolbar">
        <div class="compare-meta">
          <div
            v-for="item in compareRows"
            :key="item.title"
            class="compare-chip"
          >
            {{ item.title }}
          </div>
        </div>
        <el-switch
          v-model="compareOnlyDifferences"
          active-text="仅看差异"
          inactive-text="显示全部"
        />
      </div>

      <el-empty
        v-if="!compareFields.length"
        description="当前没有可展示的差异字段"
      />
      <el-table v-else :data="compareFields" style="width: 100%">
        <el-table-column
          prop="field"
          label="字段"
          min-width="180"
          fixed="left"
        />
        <el-table-column label="记录 1" min-width="260">
          <template #default="{ row }">
            <pre class="compare-value">{{ row.leftValue }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="记录 2" min-width="260">
          <template #default="{ row }">
            <pre class="compare-value">{{ row.rightValue }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-tag :type="row.same ? 'success' : 'warning'" effect="plain">
              {{ row.same ? "一致" : "不同" }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<style scoped>
.control-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
}

.section-label,
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.data-toolbar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1 1 320px;
  min-width: min(320px, 100%);
}

.block-label {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.block-tip {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.table-select {
  width: min(320px, 100%);
}

.toolbar-side {
  display: flex;
  flex: 1 1 420px;
  flex-direction: column;
  gap: 12px;
  min-width: min(360px, 100%);
}

.action-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.backup-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.table-toolbar-actions {
  display: flex;
  flex: 1 1 420px;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.toolbar-status-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar-main-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar-chevron {
  margin-left: 4px;
  font-size: 12px;
}

.toolbar-submeta {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.82);
}

.record-filter-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-tip {
  min-width: 240px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.upload-box {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backup-item {
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 28px -28px rgba(15, 23, 42, 0.45);
}

.backup-item-head,
.restore-title,
.backup-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.backup-name {
  color: #0f172a;
  font-weight: 600;
  word-break: break-all;
}

.restore-result {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 14px;
  background: rgba(240, 253, 244, 0.9);
}

.backup-tip {
  justify-content: flex-start;
  margin-top: 16px;
  color: #64748b;
  line-height: 1.7;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.compare-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.compare-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.compare-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.json-preview {
  margin: 0;
  padding: 16px;
  border-radius: 14px;
  background: #0f172a;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, "SFMono-Regular", monospace;
  font-size: 13px;
  line-height: 1.7;
}

.compare-value {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, "SFMono-Regular", monospace;
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 1200px) {
  .record-filter-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .record-filter-row {
    grid-template-columns: 1fr;
  }

  .table-toolbar-actions,
  .toolbar-status-tags,
  .toolbar-main-actions {
    align-items: flex-start;
    justify-content: flex-start;
  }

  .pagination-row {
    align-items: flex-start;
  }

  .filter-panel {
    padding: 14px;
  }
}
</style>
