<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  Delete,
  Download,
  Edit,
  MagicStick,
  Picture,
  RefreshRight,
  Select,
  Upload,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import { getAccountDetails } from "@/api/accounts";
import {
  batchDeleteItemDefaultReply,
  batchDeleteItems,
  batchSaveItemDefaultReply,
  deleteItem,
  deleteItemDefaultReply,
  fetchAllItemsFromAccount,
  getItemDefaultReply,
  getItems,
  polishItem,
  relistItem,
  saveItemDefaultReply,
  uploadItemDefaultReplyImage,
  updateItem,
} from "@/api/items";
import type { AccountDetail, ApiResponse, Item } from "@/types";

type StatusFilter =
  | "all"
  | "on_sale"
  | "sold"
  | "off_shelf"
  | "removed"
  | "draft";

const loading = ref(true);
const fetching = ref(false);
const actionLoading = ref<string | null>(null);
const batchAction = ref<"relist" | "polish" | null>(null);
const itemDeletingKey = ref<string | null>(null);
const batchDeletingItems = ref(false);
const accounts = ref<AccountDetail[]>([]);
const items = ref<Item[]>([]);
const selectedRows = ref<Item[]>([]);
const selectedAccount = ref("");
const searchKeyword = ref("");
const statusFilter = ref<StatusFilter>("all");
const editDialogVisible = ref(false);
const editSaving = ref(false);
const editingItem = ref<Item | null>(null);
const defaultReplyDialogVisible = ref(false);
const defaultReplyLoading = ref(false);
const defaultReplySaving = ref(false);
const defaultReplyDeleting = ref(false);
const defaultReplyImageUploading = ref(false);
const currentReplyItem = ref<Item | null>(null);
const defaultReplyImageInput = ref<HTMLInputElement | null>(null);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);
const batchDefaultReplyDialogVisible = ref(false);
const batchDefaultReplySaving = ref(false);
const batchDefaultReplyDeleting = ref(false);
const defaultReplyStatusMap = ref<
  Record<string, { configured: boolean; enabled: boolean }>
>({});

const editForm = ref({
  title: "",
  price: "",
  category: "",
  status: "",
  detail: "",
  primaryImage: "",
  autoRelist: false,
  autoPolish: false,
  autoPolishInterval: 24,
});

const defaultReplyForm = ref({
  replyContent: "",
  replyImage: "",
  enabled: true,
  replyOnce: false,
});

const batchDefaultReplyForm = ref({
  replyContent: "",
  replyImage: "",
  enabled: true,
  replyOnce: false,
});

const statusTabs: Array<{ label: string; value: StatusFilter }> = [
  { label: "全部", value: "all" },
  { label: "发布中", value: "on_sale" },
  { label: "已卖出", value: "sold" },
  { label: "已下架", value: "off_shelf" },
  { label: "已删除", value: "removed" },
  { label: "草稿", value: "draft" },
];

const normalizeStatus = (item: Item) => {
  const rawStatus = String(
    item.item_status || item.item_detail_parsed?.item_status || "",
  ).trim();
  if (rawStatus === "0" || rawStatus === "on_sale") return "on_sale";
  if (rawStatus === "1" || rawStatus === "draft") return "draft";
  if (rawStatus === "2" || rawStatus === "sold" || rawStatus === "sold_out")
    return "sold";
  if (rawStatus === "3" || rawStatus === "off_shelf") return "off_shelf";
  if (rawStatus === "removed") return "removed";
  return rawStatus;
};

const getItemStatusText = (item: Item) => {
  const statusMap: Record<string, string> = {
    on_sale: "在售",
    sold: "已售",
    off_shelf: "已下架",
    removed: "已删除",
    draft: "草稿",
  };
  return statusMap[normalizeStatus(item)] || "未知";
};

const getStatusTagType = (item: Item) => {
  const statusTypeMap: Record<
    string,
    "" | "success" | "warning" | "danger" | "info"
  > = {
    on_sale: "success",
    sold: "warning",
    off_shelf: "info",
    removed: "danger",
    draft: "",
  };
  return statusTypeMap[normalizeStatus(item)] || "info";
};

const getItemTitle = (item: Item) => item.item_title || item.title || "-";

const getItemDescription = (item: Item) => item.item_detail || item.desc || "";

const getItemCategoryText = (item: Item) => {
  return (
    String(item.item_detail_parsed?.category_name || "").trim() ||
    String(item.item_category || "").trim() ||
    String(item.item_detail_parsed?.category_id || "").trim() ||
    "-"
  );
};

const getItemPrimaryImage = (item: Item) => {
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

const getAccountLabel = (cookieId: string) => {
  const account = accounts.value.find((item) => item.id === cookieId);
  if (!account) return cookieId;
  return account.xianyu_nickname
    ? `${cookieId}（${account.xianyu_nickname}）`
    : cookieId;
};

const getDefaultReplyKey = (item: Item) => `${item.cookie_id}:${item.item_id}`;

const getDefaultReplyStatusType = (item: Item) => {
  const status = defaultReplyStatusMap.value[getDefaultReplyKey(item)];
  if (!status) return "info";
  if (!status.configured) return "info";
  return status.enabled ? "success" : "warning";
};

const getDefaultReplyStatusText = (item: Item) => {
  const status = defaultReplyStatusMap.value[getDefaultReplyKey(item)];
  if (!status) return "默认回复";
  if (!status.configured) return "未配置";
  return status.enabled ? "已启用" : "已停用";
};

const selectedCount = computed(() => selectedRows.value.length);
const selectedItemIds = computed(() =>
  selectedRows.value.map((item) => item.item_id).filter(Boolean),
);
const activeFilterCount = computed(() => {
  let count = 0;
  if (selectedAccount.value) count += 1;
  if (searchKeyword.value.trim()) count += 1;
  if (statusFilter.value !== "all") count += 1;
  return count;
});
const selectedRowsGroupedByCookie = computed(() => {
  const groups = new Map<string, Item[]>();
  selectedRows.value.forEach((item) => {
    const cookieId = item.cookie_id;
    if (!cookieId) return;
    const list = groups.get(cookieId) || [];
    list.push(item);
    groups.set(cookieId, list);
  });
  return groups;
});
const selectedCookieCount = computed(
  () => selectedRowsGroupedByCookie.value.size,
);
const isAllFilteredSelected = computed(() => {
  if (!filteredItems.value.length) return false;
  const selectedKeys = new Set(selectedRows.value.map(getDefaultReplyKey));
  return filteredItems.value.every((item) =>
    selectedKeys.has(getDefaultReplyKey(item)),
  );
});

const filteredItems = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  return items.value.filter((item) => {
    if (
      statusFilter.value !== "all" &&
      normalizeStatus(item) !== statusFilter.value
    ) {
      return false;
    }

    if (!keyword) {
      return true;
    }

    const target = [getItemTitle(item), getItemDescription(item), item.item_id]
      .join(" ")
      .toLowerCase();
    return target.includes(keyword);
  });
});

const exportRows = computed(() =>
  filteredItems.value.map((item) => ({
    cookie_id: item.cookie_id,
    item_id: item.item_id,
    title: getItemTitle(item),
    status: getItemStatusText(item),
    category: getItemCategoryText(item),
    price: String(item.item_price || item.price || ""),
    auto_relist: item.auto_relist_enabled ? "已开启" : "已关闭",
    auto_polish: item.auto_polish_enabled
      ? `每 ${item.auto_polish_interval_hours || 24} 小时`
      : "已关闭",
    default_reply: getDefaultReplyStatusText(item),
  })),
);

const selectedExportRows = computed(() =>
  selectedRows.value.map((item) => ({
    cookie_id: item.cookie_id,
    item_id: item.item_id,
    title: getItemTitle(item),
    status: getItemStatusText(item),
    category: getItemCategoryText(item),
    price: String(item.item_price || item.price || ""),
    auto_relist: item.auto_relist_enabled ? "已开启" : "已关闭",
    auto_polish: item.auto_polish_enabled
      ? `每 ${item.auto_polish_interval_hours || 24} 小时`
      : "已关闭",
    default_reply: getDefaultReplyStatusText(item),
  })),
);

const loadAccounts = async () => {
  try {
    accounts.value = await getAccountDetails();
  } catch {
    ElMessage.warning("账号列表加载失败");
  }
};

const loadItems = async () => {
  loading.value = true;
  try {
    const result = await getItems(selectedAccount.value || undefined);
    items.value = result.data || [];
  } catch {
    ElMessage.error("商品列表加载失败");
    items.value = [];
  } finally {
    loading.value = false;
  }
};

const handleSelectionChange = (rows: Item[]) => {
  selectedRows.value = rows;
};

const clearTableSelection = () => {
  selectedRows.value = [];
  tableRef.value?.clearSelection();
};

const handleSelectFilteredItems = () => {
  if (!filteredItems.value.length) {
    ElMessage.warning("当前没有可勾选的商品");
    return;
  }

  tableRef.value?.clearSelection();
  filteredItems.value.forEach((item) => {
    tableRef.value?.toggleRowSelection(item, true);
  });
  ElMessage.success(`已勾选当前筛选结果 ${filteredItems.value.length} 个商品`);
};

const handleToggleSelectAllFiltered = () => {
  if (!filteredItems.value.length) {
    ElMessage.warning("当前没有可勾选的商品");
    return;
  }

  if (isAllFilteredSelected.value) {
    clearTableSelection();
    ElMessage.success("已取消当前列表全选");
    return;
  }

  handleSelectFilteredItems();
};

const getBatchActionGroups = () =>
  Array.from(selectedRowsGroupedByCookie.value.entries()).map(
    ([cookieId, rows]) => ({
      cookieId,
      itemIds: rows.map((item) => item.item_id).filter(Boolean),
      rows,
    }),
  );

const getBatchResponseCount = (
  response: ApiResponse,
  field: "success_count" | "fail_count",
) => {
  const data =
    response.data && typeof response.data === "object"
      ? (response.data as Record<string, unknown>)
      : undefined;
  const dataValue = data?.[field];
  if (typeof dataValue === "number") return dataValue;
  const topLevelValue = (response as unknown as Record<string, unknown>)[field];
  return typeof topLevelValue === "number" ? topLevelValue : 0;
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
  return `items-${scope}-${time}.${extension}`;
};

const escapeCsvCell = (value: string) => `"${value.replace(/"/g, '""')}"`;

const exportAsCsv = (
  rows: Array<Record<string, string>>,
  scope: "filtered" | "selected",
) => {
  const fields = Object.keys(rows[0] || {});
  const header = fields.map(escapeCsvCell).join(",");
  const body = rows
    .map((row) =>
      fields.map((field) => escapeCsvCell(row[field] || "")).join(","),
    )
    .join("\n");

  downloadTextFile(
    buildExportFilename(scope, "csv"),
    `${header}\n${body}`,
    "text/csv;charset=utf-8",
  );
};

const handleExportFilteredJson = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的商品");
    return;
  }

  downloadTextFile(
    buildExportFilename("filtered", "json"),
    JSON.stringify(exportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${exportRows.value.length} 个筛选商品`);
};

const handleExportFilteredCsv = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的商品");
    return;
  }

  exportAsCsv(exportRows.value, "filtered");
  ElMessage.success(`已导出 ${exportRows.value.length} 个筛选商品`);
};

const handleExportSelectedJson = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的商品");
    return;
  }

  downloadTextFile(
    buildExportFilename("selected", "json"),
    JSON.stringify(selectedExportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 个勾选商品`);
};

const handleExportSelectedCsv = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的商品");
    return;
  }

  exportAsCsv(selectedExportRows.value, "selected");
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 个勾选商品`);
};

const handleCopySelectedItemIds = async () => {
  if (!selectedItemIds.value.length) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  try {
    await navigator.clipboard.writeText(selectedItemIds.value.join("\n"));
    ElMessage.success(`已复制 ${selectedItemIds.value.length} 个商品 ID`);
  } catch {
    ElMessage.error("复制失败");
  }
};

const resetEditForm = () => {
  editForm.value = {
    title: "",
    price: "",
    category: "",
    status: "",
    detail: "",
    primaryImage: "",
    autoRelist: false,
    autoPolish: false,
    autoPolishInterval: 24,
  };
};

const openEditDialog = (item: Item) => {
  editingItem.value = item;
  editForm.value = {
    title: getItemTitle(item) === "-" ? "" : getItemTitle(item),
    price: item.item_price || item.price || "",
    category:
      getItemCategoryText(item) === "-" ? "" : getItemCategoryText(item),
    status: String(
      item.item_status || item.item_detail_parsed?.item_status || "",
    ),
    detail: getItemDescription(item),
    primaryImage: getItemPrimaryImage(item),
    autoRelist: Boolean(item.auto_relist_enabled),
    autoPolish: Boolean(item.auto_polish_enabled),
    autoPolishInterval: item.auto_polish_interval_hours || 24,
  };
  editDialogVisible.value = true;
};

const closeEditDialog = () => {
  editDialogVisible.value = false;
  editingItem.value = null;
  resetEditForm();
};

const handleSaveEdit = async () => {
  if (!editingItem.value) return;

  editSaving.value = true;
  try {
    const response = await updateItem(
      editingItem.value.cookie_id,
      editingItem.value.item_id,
      {
        item_title: editForm.value.title,
        item_price: editForm.value.price,
        item_category: editForm.value.category,
        item_status: editForm.value.status,
        item_detail: editForm.value.detail,
        primary_image_url: editForm.value.primaryImage,
        auto_relist_enabled: editForm.value.autoRelist,
        auto_polish_enabled: editForm.value.autoPolish,
        auto_polish_interval_hours: editForm.value.autoPolishInterval,
      },
    );

    if (!response.success) {
      throw new Error(
        response.detail || response.message || response.msg || "商品更新失败",
      );
    }

    ElMessage.success("商品信息已更新");
    closeEditDialog();
    await loadItems();
  } catch (error) {
    const message = error instanceof Error ? error.message : "商品更新失败";
    ElMessage.error(message);
  } finally {
    editSaving.value = false;
  }
};

const runItemAction = async (
  key: string,
  action: () => Promise<void>,
  successMessage: string,
  fallbackMessage: string,
) => {
  actionLoading.value = key;
  try {
    await action();
    ElMessage.success(successMessage);
    await loadItems();
  } catch {
    ElMessage.error(fallbackMessage);
  } finally {
    actionLoading.value = null;
  }
};

const handleRelist = async (item: Item) => {
  await runItemAction(
    `relist:${getDefaultReplyKey(item)}`,
    async () => {
      const response = await relistItem(item.cookie_id, item.item_id);
      if (!response.success) {
        throw new Error();
      }
    },
    "商品已执行上架",
    "商品上架失败",
  );
};

const handlePolish = async (item: Item) => {
  await runItemAction(
    `polish:${getDefaultReplyKey(item)}`,
    async () => {
      const response = await polishItem(item.cookie_id, item.item_id);
      if (!response.success) {
        throw new Error();
      }
    },
    "商品已执行擦亮",
    "商品擦亮失败",
  );
};

const handleBatchRelist = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  batchAction.value = "relist";
  let successCount = 0;
  let failCount = 0;

  for (const item of selectedRows.value) {
    try {
      const response = await relistItem(item.cookie_id, item.item_id);
      if (response.success) {
        successCount += 1;
      } else {
        failCount += 1;
      }
    } catch {
      failCount += 1;
    }
  }

  batchAction.value = null;
  ElMessage[failCount ? "warning" : "success"](
    `批量上架完成：成功 ${successCount}，失败 ${failCount}`,
  );
  clearTableSelection();
  await loadItems();
};

const handleBatchPolish = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  batchAction.value = "polish";
  let successCount = 0;
  let failCount = 0;

  for (const item of selectedRows.value) {
    try {
      const response = await polishItem(item.cookie_id, item.item_id);
      if (response.success) {
        successCount += 1;
      } else {
        failCount += 1;
      }
    } catch {
      failCount += 1;
    }
  }

  batchAction.value = null;
  ElMessage[failCount ? "warning" : "success"](
    `批量擦亮完成：成功 ${successCount}，失败 ${failCount}`,
  );
  clearTableSelection();
  await loadItems();
};

const handleDeleteItem = async (item: Item) => {
  try {
    await ElMessageBox.confirm(
      `确定删除商品 ${getItemTitle(item)}（${item.item_id}）吗？`,
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

  itemDeletingKey.value = getDefaultReplyKey(item);
  try {
    const response = await deleteItem(item.cookie_id, item.item_id);
    if (!response.success) {
      throw new Error(
        response.detail || response.message || response.msg || "商品删除失败",
      );
    }

    ElMessage.success("商品已删除");
    await loadItems();
  } catch (error) {
    const message = error instanceof Error ? error.message : "商品删除失败";
    ElMessage.error(message);
  } finally {
    itemDeletingKey.value = null;
  }
};

const handleBatchDeleteItems = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning("请先勾选要删除的商品");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定批量删除 ${selectedRows.value.length} 个商品吗？`,
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

  batchDeletingItems.value = true;
  try {
    const response = await batchDeleteItems(
      selectedRows.value.map((item) => ({
        cookie_id: item.cookie_id,
        item_id: item.item_id,
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
      Math.max(selectedRows.value.length - successCount, 0);
    ElMessage[failedCount ? "warning" : "success"](
      `批量删除完成：成功 ${successCount}，失败 ${failedCount}`,
    );
    clearTableSelection();
    await loadItems();
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量删除失败";
    ElMessage.error(message);
  } finally {
    batchDeletingItems.value = false;
  }
};

const resetDefaultReplyForm = () => {
  defaultReplyForm.value = {
    replyContent: "",
    replyImage: "",
    enabled: true,
    replyOnce: false,
  };
};

const resetBatchDefaultReplyForm = () => {
  batchDefaultReplyForm.value = {
    replyContent: "",
    replyImage: "",
    enabled: true,
    replyOnce: false,
  };
};

const openDefaultReplyDialog = async (item: Item) => {
  currentReplyItem.value = item;
  defaultReplyDialogVisible.value = true;
  defaultReplyLoading.value = true;
  resetDefaultReplyForm();

  try {
    const response = await getItemDefaultReply(item.cookie_id, item.item_id);
    if (response.success && response.data) {
      defaultReplyForm.value = {
        replyContent: response.data.reply_content || "",
        replyImage: response.data.reply_image || "",
        enabled: response.data.enabled ?? true,
        replyOnce: response.data.reply_once ?? false,
      };
      defaultReplyStatusMap.value[getDefaultReplyKey(item)] = {
        configured: true,
        enabled: response.data.enabled ?? true,
      };
    } else {
      defaultReplyStatusMap.value[getDefaultReplyKey(item)] = {
        configured: false,
        enabled: true,
      };
    }
  } catch {
    defaultReplyStatusMap.value[getDefaultReplyKey(item)] = {
      configured: false,
      enabled: true,
    };
  } finally {
    defaultReplyLoading.value = false;
  }
};

const closeDefaultReplyDialog = () => {
  defaultReplyDialogVisible.value = false;
  currentReplyItem.value = null;
  resetDefaultReplyForm();
};

const triggerDefaultReplyImageInput = () => {
  defaultReplyImageInput.value?.click();
};

const handleDefaultReplyImageUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];

  if (!file || !currentReplyItem.value) {
    return;
  }

  defaultReplyImageUploading.value = true;
  try {
    const result = await uploadItemDefaultReplyImage(
      currentReplyItem.value.cookie_id,
      currentReplyItem.value.item_id,
      file,
    );
    if (!result.success || !result.image_url) {
      throw new Error(result.message || "图片上传失败");
    }
    defaultReplyForm.value.replyImage = result.image_url;
    ElMessage.success("图片上传成功");
  } catch (error) {
    const message = error instanceof Error ? error.message : "图片上传失败";
    ElMessage.error(message);
  } finally {
    defaultReplyImageUploading.value = false;
    if (input) {
      input.value = "";
    }
  }
};

const handleSaveDefaultReply = async () => {
  if (!currentReplyItem.value) return;

  defaultReplySaving.value = true;
  try {
    const response = await saveItemDefaultReply(
      currentReplyItem.value.cookie_id,
      currentReplyItem.value.item_id,
      {
        reply_content: defaultReplyForm.value.replyContent,
        reply_image_url: defaultReplyForm.value.replyImage || undefined,
        enabled: defaultReplyForm.value.enabled,
        reply_once: defaultReplyForm.value.replyOnce,
      },
    );
    if (!response.success) {
      throw new Error(
        response.detail || response.message || response.msg || "保存失败",
      );
    }

    defaultReplyStatusMap.value[getDefaultReplyKey(currentReplyItem.value)] = {
      configured: true,
      enabled: defaultReplyForm.value.enabled,
    };
    ElMessage.success("商品默认回复保存成功");
    closeDefaultReplyDialog();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "商品默认回复保存失败";
    ElMessage.error(message);
  } finally {
    defaultReplySaving.value = false;
  }
};

const handleDeleteDefaultReply = async () => {
  if (!currentReplyItem.value) return;

  try {
    await ElMessageBox.confirm(
      "确定要删除该商品的默认回复配置吗？",
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

  defaultReplyDeleting.value = true;
  try {
    const response = await deleteItemDefaultReply(
      currentReplyItem.value.cookie_id,
      currentReplyItem.value.item_id,
    );
    if (!response.success) {
      throw new Error(
        response.detail || response.message || response.msg || "删除失败",
      );
    }

    defaultReplyStatusMap.value[getDefaultReplyKey(currentReplyItem.value)] = {
      configured: false,
      enabled: true,
    };
    ElMessage.success("商品默认回复已删除");
    closeDefaultReplyDialog();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "商品默认回复删除失败";
    ElMessage.error(message);
  } finally {
    defaultReplyDeleting.value = false;
  }
};

const openBatchDefaultReplyDialog = () => {
  if (!selectedCount.value) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  resetBatchDefaultReplyForm();
  batchDefaultReplyDialogVisible.value = true;
};

const closeBatchDefaultReplyDialog = () => {
  batchDefaultReplyDialogVisible.value = false;
  resetBatchDefaultReplyForm();
};

const handleBatchSaveDefaultReply = async () => {
  if (!selectedCount.value) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  batchDefaultReplySaving.value = true;
  try {
    let successCount = 0;
    let failCount = 0;

    for (const group of getBatchActionGroups()) {
      const response = await batchSaveItemDefaultReply(group.cookieId, {
        item_ids: group.itemIds,
        reply_content: batchDefaultReplyForm.value.replyContent,
        reply_image_url: batchDefaultReplyForm.value.replyImage || undefined,
        enabled: batchDefaultReplyForm.value.enabled,
        reply_once: batchDefaultReplyForm.value.replyOnce,
      });

      if (!response.success) {
        throw new Error(
          response.detail || response.message || response.msg || "批量保存失败",
        );
      }

      successCount += getBatchResponseCount(response, "success_count");
      failCount += getBatchResponseCount(response, "fail_count");
    }

    for (const item of selectedRows.value) {
      defaultReplyStatusMap.value[getDefaultReplyKey(item)] = {
        configured: true,
        enabled: batchDefaultReplyForm.value.enabled,
      };
    }

    ElMessage[failCount ? "warning" : "success"](
      `批量保存完成：成功 ${successCount}，失败 ${failCount}`,
    );
    closeBatchDefaultReplyDialog();
    clearTableSelection();
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量保存失败";
    ElMessage.error(message);
  } finally {
    batchDefaultReplySaving.value = false;
  }
};

const handleBatchDeleteDefaultReply = async () => {
  if (!selectedCount.value) {
    ElMessage.warning("请先勾选商品");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedCount.value} 个商品默认回复配置吗？`,
      "批量删除确认",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  batchDefaultReplyDeleting.value = true;
  try {
    let successCount = 0;
    let failCount = 0;

    for (const group of getBatchActionGroups()) {
      const response = await batchDeleteItemDefaultReply(
        group.cookieId,
        group.itemIds,
      );
      if (!response.success) {
        throw new Error(
          response.detail || response.message || response.msg || "批量删除失败",
        );
      }

      successCount += getBatchResponseCount(response, "success_count");
      failCount += getBatchResponseCount(response, "fail_count");
    }

    for (const item of selectedRows.value) {
      defaultReplyStatusMap.value[getDefaultReplyKey(item)] = {
        configured: false,
        enabled: true,
      };
    }

    ElMessage[failCount ? "warning" : "success"](
      `批量删除完成：成功 ${successCount}，失败 ${failCount}`,
    );
    clearTableSelection();
    closeBatchDefaultReplyDialog();
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量删除失败";
    ElMessage.error(message);
  } finally {
    batchDefaultReplyDeleting.value = false;
  }
};

const handleFetchItems = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning("请先选择账号后再获取商品");
    return;
  }

  fetching.value = true;
  try {
    const result = await fetchAllItemsFromAccount(selectedAccount.value);
    if (result.success) {
      ElMessage.success(result.message || "已触发账号商品同步");
      await loadItems();
    } else {
      ElMessage.error(result.detail || result.message || "获取商品失败");
    }
  } catch {
    ElMessage.error("获取商品失败");
  } finally {
    fetching.value = false;
  }
};

watch(selectedAccount, async () => {
  await loadItems();
});

onMounted(async () => {
  await Promise.all([loadAccounts(), loadItems()]);
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">商品管理</h1>
        <p class="page-description">
          本轮继续补齐编辑、上架、擦亮和默认回复配置，先覆盖最高频的日常操作。
        </p>
      </div>
      <div class="page-actions">
        <el-button
          :icon="Upload"
          :loading="batchAction === 'relist'"
          :disabled="!selectedRows.length || batchAction === 'polish'"
          @click="handleBatchRelist"
        >
          批量上架
        </el-button>
        <el-button
          :icon="MagicStick"
          :loading="batchAction === 'polish'"
          :disabled="!selectedRows.length || batchAction === 'relist'"
          @click="handleBatchPolish"
        >
          批量擦亮
        </el-button>
        <el-button
          :icon="Picture"
          :disabled="!selectedRows.length"
          @click="openBatchDefaultReplyDialog"
        >
          批量设置自动回复
        </el-button>
        <el-button
          :icon="Delete"
          :disabled="!selectedRows.length"
          @click="handleBatchDeleteDefaultReply"
        >
          批量删回复
        </el-button>
        <el-button
          type="danger"
          plain
          :icon="Delete"
          :loading="batchDeletingItems"
          :disabled="!selectedRows.length"
          @click="handleBatchDeleteItems"
        >
          批量删商品
        </el-button>
        <el-button :icon="RefreshRight" @click="loadItems">刷新列表</el-button>
        <el-button
          type="primary"
          :icon="Download"
          :loading="fetching"
          @click="handleFetchItems"
        >
          获取商品
        </el-button>
      </div>
    </section>

    <section class="filter-bar">
      <div class="filter-title">
        <el-icon><Select /></el-icon>
        <span>筛选条件</span>
      </div>
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

        <el-form-item label="搜索商品">
          <el-input
            v-model="searchKeyword"
            clearable
            placeholder="搜索商品标题、描述或商品 ID"
          />
        </el-form-item>
      </div>

      <div class="status-tabs">
        <el-tag
          v-for="tab in statusTabs"
          :key="tab.value"
          class="status-tab"
          :effect="statusFilter === tab.value ? 'dark' : 'plain'"
          @click="statusFilter = tab.value"
        >
          {{ tab.label }}
        </el-tag>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">
            当前展示 {{ filteredItems.length }} /
            {{ items.length }} 个商品，已勾选 {{ selectedRows.length }} 个
          </div>
          <div class="toolbar-submeta">
            支持全选当前列表、一键批量设置自动回复，也支持逐个单独设置
          </div>
        </div>
        <div class="table-toolbar-actions">
          <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
            启用 {{ activeFilterCount }} 个筛选
          </el-tag>
          <el-tag type="primary" effect="plain">
            已补齐编辑、上架、擦亮和默认回复配置
          </el-tag>
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
          <el-button
            link
            :icon="Select"
            :disabled="!filteredItems.length"
            @click="handleToggleSelectAllFiltered"
          >
            {{ isAllFilteredSelected ? "取消全选当前列表" : "全选当前列表" }}
          </el-button>
          <el-button
            link
            :icon="Edit"
            :disabled="!selectedRows.length"
            @click="handleCopySelectedItemIds"
          >
            复制商品 ID
          </el-button>
          <el-button
            link
            type="danger"
            :disabled="!selectedRows.length"
            @click="clearTableSelection"
          >
            清空勾选
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredItems"
        :row-key="getDefaultReplyKey"
        style="width: 100%; margin-top: 16px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" reserve-selection />

        <el-table-column label="账号" min-width="180">
          <template #default="{ row }">
            <span>{{ getAccountLabel(row.cookie_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="商品 ID" min-width="160">
          <template #default="{ row }">
            <a
              class="mono item-link"
              :href="`https://www.goofish.com/item?id=${row.item_id}`"
              target="_blank"
              rel="noreferrer"
            >
              {{ row.item_id }}
            </a>
          </template>
        </el-table-column>

        <el-table-column label="主图" width="96">
          <template #default="{ row }">
            <el-image
              v-if="getItemPrimaryImage(row)"
              :src="getItemPrimaryImage(row)"
              fit="cover"
              class="item-image"
              preview-teleported
              :preview-src-list="[getItemPrimaryImage(row)]"
            />
            <span v-else class="text-muted">无图</span>
          </template>
        </el-table-column>

        <el-table-column label="商品信息" min-width="260">
          <template #default="{ row }">
            <div class="cell-title">
              <div class="cell-title-main">{{ getItemTitle(row) }}</div>
              <div
                v-if="getItemDescription(row)"
                class="cell-title-sub text-ellipsis"
              >
                {{ getItemDescription(row) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row)" effect="plain">{{
              getItemStatusText(row)
            }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="分类" min-width="140">
          <template #default="{ row }">
            <span>{{ getItemCategoryText(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="价格" width="120">
          <template #default="{ row }">
            <span>{{ row.item_price || row.price || "-" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="多规格" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.is_multi_spec || row.has_sku ? 'warning' : 'info'"
              effect="plain"
            >
              {{ row.is_multi_spec || row.has_sku ? "已开启" : "已关闭" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="多数量发货" width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.multi_quantity_delivery ? 'success' : 'info'"
              effect="plain"
            >
              {{ row.multi_quantity_delivery ? "已开启" : "已关闭" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="自动上架" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.auto_relist_enabled ? 'success' : 'info'"
              effect="plain"
            >
              {{ row.auto_relist_enabled ? "已开启" : "已关闭" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="自动擦亮" width="140">
          <template #default="{ row }">
            <span>
              {{
                row.auto_polish_enabled
                  ? `每 ${row.auto_polish_interval_hours || 24} 小时`
                  : "已关闭"
              }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="默认回复" width="110">
          <template #default="{ row }">
            <el-tag :type="getDefaultReplyStatusType(row)" effect="plain">
              {{ getDefaultReplyStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="280" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                link
                type="primary"
                :icon="Edit"
                @click="openEditDialog(row)"
              >
                编辑
              </el-button>
              <el-button
                link
                type="success"
                :icon="Upload"
                :loading="actionLoading === `relist:${getDefaultReplyKey(row)}`"
                @click="handleRelist(row)"
              >
                上架
              </el-button>
              <el-button
                link
                type="warning"
                :icon="MagicStick"
                :loading="actionLoading === `polish:${getDefaultReplyKey(row)}`"
                @click="handlePolish(row)"
              >
                擦亮
              </el-button>
              <el-button link @click="openDefaultReplyDialog(row)">
                默认回复
              </el-button>
              <el-button
                link
                type="danger"
                :icon="Delete"
                :loading="itemDeletingKey === getDefaultReplyKey(row)"
                @click="handleDeleteItem(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无商品数据" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="editDialogVisible"
      title="编辑商品"
      width="720px"
      destroy-on-close
      @closed="closeEditDialog"
    >
      <el-form label-position="top">
        <el-form-item label="商品标题">
          <el-input v-model="editForm.title" placeholder="请输入商品标题" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="价格">
              <el-input
                v-model="editForm.price"
                placeholder="例如：99 或 ¥99"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input
                v-model="editForm.category"
                placeholder="请输入商品分类"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="状态">
          <el-input
            v-model="editForm.status"
            placeholder="例如：on_sale、sold、0、2"
          />
        </el-form-item>

        <el-form-item label="主图 URL">
          <el-input v-model="editForm.primaryImage" placeholder="https://..." />
        </el-form-item>

        <el-form-item label="商品详情">
          <el-input
            v-model="editForm.detail"
            type="textarea"
            :rows="5"
            placeholder="请输入商品详情"
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="销售自动上架">
              <el-switch v-model="editForm.autoRelist" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="自动擦亮">
              <el-switch v-model="editForm.autoPolish" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="擦亮间隔（小时）">
              <el-input-number
                v-model="editForm.autoPolishInterval"
                :min="1"
                :max="720"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="handleSaveEdit"
          >保存</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      v-model="defaultReplyDialogVisible"
      title="商品默认回复配置"
      width="680px"
      destroy-on-close
      @closed="closeDefaultReplyDialog"
    >
      <el-skeleton v-if="defaultReplyLoading" :rows="6" animated />

      <template v-else>
        <el-form label-position="top">
          <el-form-item label="商品信息">
            <div class="reply-item-summary">
              <div class="reply-item-title">
                {{ currentReplyItem ? getItemTitle(currentReplyItem) : "-" }}
              </div>
              <div class="reply-item-meta">
                {{ currentReplyItem?.item_id || "-" }} /
                {{ currentReplyItem?.cookie_id || "-" }}
              </div>
            </div>
          </el-form-item>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="启用默认回复">
                <el-switch v-model="defaultReplyForm.enabled" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="只回复一次">
                <el-switch v-model="defaultReplyForm.replyOnce" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="回复内容">
            <el-input
              v-model="defaultReplyForm.replyContent"
              type="textarea"
              :rows="5"
              placeholder="支持变量：{send_user_name}、{send_user_id}、{send_message}、{item_id}"
            />
          </el-form-item>

          <el-form-item label="回复图片 URL">
            <div class="reply-image-actions">
              <el-input
                v-model="defaultReplyForm.replyImage"
                placeholder="可选，填写图片 URL"
              />
              <input
                ref="defaultReplyImageInput"
                type="file"
                accept="image/*"
                class="hidden-file-input"
                @change="handleDefaultReplyImageUpload"
              />
              <el-button
                :icon="Upload"
                :loading="defaultReplyImageUploading"
                @click="triggerDefaultReplyImageInput"
              >
                上传图片
              </el-button>
            </div>
            <el-image
              v-if="defaultReplyForm.replyImage"
              :src="defaultReplyForm.replyImage"
              class="reply-preview-image"
              fit="cover"
              :preview-src-list="[defaultReplyForm.replyImage]"
              preview-teleported
            />
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <el-button
          type="danger"
          plain
          :disabled="defaultReplyLoading || !currentReplyItem"
          :loading="defaultReplyDeleting"
          @click="handleDeleteDefaultReply"
        >
          删除配置
        </el-button>
        <el-button @click="closeDefaultReplyDialog">取消</el-button>
        <el-button
          type="primary"
          :disabled="defaultReplyLoading"
          :loading="defaultReplySaving"
          @click="handleSaveDefaultReply"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchDefaultReplyDialogVisible"
      title="批量设置默认回复"
      width="680px"
      destroy-on-close
      @closed="closeBatchDefaultReplyDialog"
    >
      <el-form label-position="top">
        <el-form-item label="批量范围">
          <div class="reply-item-summary">
            <div class="reply-item-title">
              已选择 {{ selectedCount }} 个商品
            </div>
            <div class="reply-item-meta">
              涉及 {{ selectedCookieCount }} 个账号
            </div>
          </div>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="启用默认回复">
              <el-switch v-model="batchDefaultReplyForm.enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="只回复一次">
              <el-switch v-model="batchDefaultReplyForm.replyOnce" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="回复内容">
          <el-input
            v-model="batchDefaultReplyForm.replyContent"
            type="textarea"
            :rows="5"
            placeholder="支持变量：{send_user_name}、{send_user_id}、{send_message}、{item_id}"
          />
        </el-form-item>

        <el-form-item label="回复图片 URL">
          <el-input
            v-model="batchDefaultReplyForm.replyImage"
            placeholder="可选，填写统一回复图片 URL"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button
          type="danger"
          plain
          :loading="batchDefaultReplyDeleting"
          :disabled="!selectedCount"
          @click="handleBatchDeleteDefaultReply"
        >
          批量删除
        </el-button>
        <el-button @click="closeBatchDefaultReplyDialog">取消</el-button>
        <el-button
          type="primary"
          :loading="batchDefaultReplySaving"
          :disabled="!selectedCount"
          @click="handleBatchSaveDefaultReply"
        >
          批量保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #0f172a;
}

.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
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

.inline-form :deep(.el-select),
.inline-form :deep(.el-input) {
  width: 220px;
}

.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.status-tab {
  cursor: pointer;
}

.item-link {
  color: #2563eb;
}

.item-image {
  width: 56px;
  height: 56px;
  border-radius: 12px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.table-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-submeta {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.reply-item-summary {
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
}

.reply-item-title {
  font-weight: 600;
  color: #0f172a;
}

.reply-item-meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.reply-image-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.reply-preview-image {
  width: 88px;
  height: 88px;
  margin-top: 12px;
  border-radius: 14px;
}

.hidden-file-input {
  display: none;
}

@media (max-width: 768px) {
  .inline-form :deep(.el-select),
  .inline-form :deep(.el-input) {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .reply-image-actions {
    flex-direction: column;
  }
}
</style>
