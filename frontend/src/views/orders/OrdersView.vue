<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  CopyDocument,
  Delete,
  DocumentCopy,
  Download,
  RefreshRight,
  Select,
  View,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import { getAccountDetails } from "@/api/accounts";
import {
  deleteOrder,
  fetchOrdersFromAccount,
  getOrderDetail,
  getOrders,
  type OrderDetail,
} from "@/api/orders";
import type {
  AccountDetail,
  Order,
  OrderStatus,
  OrderStatusOption,
} from "@/types";

const PAGE_SIZE = 20;
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const fetching = ref(false);
const detailLoading = ref(false);
const deletingOrderKey = ref<string | null>(null);
const accounts = ref<AccountDetail[]>([]);
const orders = ref<Order[]>([]);
const selectedAccount = ref("");
const selectedStatus = ref<OrderStatusOption["value"]>("");
const searchKeyword = ref("");
const currentPage = ref(1);
const total = ref(0);
const totalPages = ref(0);
const detailDialogVisible = ref(false);
const orderDetail = ref<OrderDetail | null>(null);
const searchTimer = ref<number | null>(null);
const hydratingFromRoute = ref(true);
const suppressFilterWatch = ref(false);
const syncingRouteQuery = ref(false);
const selectedOrders = ref<Order[]>([]);
const bulkDeleting = ref(false);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);

const orderStatusOptions: OrderStatusOption[] = [
  { value: "", label: "所有状态" },
  { value: "processing", label: "处理中" },
  { value: "pending_ship", label: "待发货" },
  { value: "processed", label: "已处理" },
  { value: "shipped", label: "已发货" },
  { value: "completed", label: "已完成" },
  { value: "refunding", label: "退款中" },
  { value: "refund_cancelled", label: "退款撤销" },
  { value: "closed", label: "已关闭" },
  { value: "unknown", label: "未知" },
];

const statusMeta: Record<
  OrderStatus,
  { label: string; type: "" | "success" | "warning" | "danger" | "info" }
> = {
  processing: { label: "处理中", type: "warning" },
  pending_ship: { label: "待发货", type: "info" },
  processed: { label: "已处理", type: "info" },
  shipped: { label: "已发货", type: "success" },
  completed: { label: "已完成", type: "success" },
  refunding: { label: "退款中", type: "warning" },
  refund_cancelled: { label: "退款撤销", type: "info" },
  cancelled: { label: "已关闭", type: "danger" },
  closed: { label: "已关闭", type: "danger" },
  unknown: { label: "未知", type: "" },
};

const getStatusLabel = (status: OrderStatus) => {
  return statusMeta[status]?.label || statusMeta.unknown.label;
};

const getStatusTagType = (status: OrderStatus) => {
  return statusMeta[status]?.type || statusMeta.unknown.type;
};

const getAccountLabel = (cookieId?: string) => {
  if (!cookieId) return "-";
  const account = accounts.value.find((item) => item.id === cookieId);
  if (!account) return cookieId;
  return account.xianyu_nickname
    ? `${cookieId}（${account.xianyu_nickname}）`
    : cookieId;
};

const formatDateTime = (value?: string) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN");
};

const formatOrderAmount = (value?: string | number | null) => {
  if (value === null || value === undefined) return "-";
  const text = String(value).trim();
  if (!text) return "-";

  const normalized = text.replace(/[¥￥,\s]/g, "");
  const amount = Number(normalized);
  if (Number.isFinite(amount)) {
    return `¥${amount.toFixed(2)}`;
  }

  return text.startsWith("¥") || text.startsWith("￥") ? text : `¥${text}`;
};

const getItemUrl = (itemId?: string) => {
  if (!itemId) return "";
  return `https://www.goofish.com/item?id=${itemId}`;
};

const getOrderRowKey = (order: Pick<Order, "order_id" | "cookie_id">) =>
  `${order.order_id}::${order.cookie_id || ""}`;

const selectedOrderIds = computed(() =>
  selectedOrders.value.map((order) => order.order_id).filter(Boolean),
);
const canBatchDelete = computed(() => selectedOrderIds.value.length > 0);
const activeFilterCount = computed(() => {
  let count = 0;
  if (selectedAccount.value) count += 1;
  if (selectedStatus.value) count += 1;
  if (searchKeyword.value.trim()) count += 1;
  return count;
});
const exportRows = computed(() =>
  orders.value.map((order) => ({
    order_id: order.order_id,
    item_id: order.item_id || "",
    buyer_id: order.buyer_id || "",
    quantity: String(order.quantity ?? 0),
    amount: String(order.amount || ""),
    status: getStatusLabel(order.status),
    is_bargain: order.is_bargain ? "是" : "否",
    cookie_id: order.cookie_id || "",
    created_at: formatDateTime(order.created_at),
    updated_at: formatDateTime(order.updated_at),
  })),
);
const selectedExportRows = computed(() =>
  selectedOrders.value.map((order) => ({
    order_id: order.order_id,
    item_id: order.item_id || "",
    buyer_id: order.buyer_id || "",
    quantity: String(order.quantity ?? 0),
    amount: String(order.amount || ""),
    status: getStatusLabel(order.status),
    is_bargain: order.is_bargain ? "是" : "否",
    cookie_id: order.cookie_id || "",
    created_at: formatDateTime(order.created_at),
    updated_at: formatDateTime(order.updated_at),
  })),
);

const normalizeQueryValue = (value: unknown) => {
  if (Array.isArray(value)) {
    return String(value[0] || "");
  }
  return typeof value === "string" ? value : "";
};

const buildRouteQuery = () => {
  const query: Record<string, string> = {};
  if (selectedAccount.value) {
    query.account = selectedAccount.value;
  }
  if (selectedStatus.value) {
    query.status = selectedStatus.value;
  }
  if (searchKeyword.value.trim()) {
    query.keyword = searchKeyword.value.trim();
  }
  if (currentPage.value > 1) {
    query.page = String(currentPage.value);
  }
  return query;
};

const syncRouteQuery = async () => {
  const nextQuery = buildRouteQuery();
  const currentQuery = {
    account: normalizeQueryValue(route.query.account),
    status: normalizeQueryValue(route.query.status),
    keyword: normalizeQueryValue(route.query.keyword),
    page: normalizeQueryValue(route.query.page),
  };

  const normalizedNextQuery = {
    account: nextQuery.account || "",
    status: nextQuery.status || "",
    keyword: nextQuery.keyword || "",
    page: nextQuery.page || "",
  };

  if (JSON.stringify(currentQuery) === JSON.stringify(normalizedNextQuery)) {
    return;
  }

  syncingRouteQuery.value = true;
  try {
    await router.replace({
      path: route.path,
      query: nextQuery,
    });
  } finally {
    syncingRouteQuery.value = false;
  }
};

const applyRouteQueryState = () => {
  suppressFilterWatch.value = true;

  const account = normalizeQueryValue(route.query.account);
  const status = normalizeQueryValue(
    route.query.status,
  ) as OrderStatusOption["value"];
  const keyword = normalizeQueryValue(route.query.keyword);
  const page = Number(normalizeQueryValue(route.query.page) || "1");

  selectedAccount.value = account;
  selectedStatus.value = orderStatusOptions.some(
    (item) => item.value === status,
  )
    ? status
    : "";
  searchKeyword.value = keyword;
  currentPage.value = Number.isFinite(page) && page > 0 ? page : 1;

  suppressFilterWatch.value = false;
};

const clearSearchTimer = () => {
  if (searchTimer.value) {
    window.clearTimeout(searchTimer.value);
    searchTimer.value = null;
  }
};

const clearSelectedOrders = () => {
  selectedOrders.value = [];
  tableRef.value?.clearSelection();
};

const handleSelectionChange = (rows: Order[]) => {
  selectedOrders.value = rows;
};

const handleSelectCurrentPage = () => {
  if (!orders.value.length) {
    ElMessage.warning("当前页没有可勾选的订单");
    return;
  }

  tableRef.value?.clearSelection();
  orders.value.forEach((order) => {
    tableRef.value?.toggleRowSelection(order, true);
  });
  ElMessage.success(`已勾选当前页 ${orders.value.length} 条订单`);
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
  scope: "current-page" | "selected",
  extension: "json" | "csv",
) => {
  const time = new Date().toISOString().replace(/[:.]/g, "-");
  return `orders-${scope}-${time}.${extension}`;
};

const escapeCsvCell = (value: string) => `"${value.replace(/"/g, '""')}"`;

const exportAsCsv = (
  rows: Array<Record<string, string>>,
  scope: "current-page" | "selected",
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

const handleExportCurrentJson = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前页没有可导出的订单");
    return;
  }

  downloadTextFile(
    buildExportFilename("current-page", "json"),
    JSON.stringify(exportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出当前页 ${exportRows.value.length} 条订单`);
};

const handleExportCurrentCsv = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前页没有可导出的订单");
    return;
  }

  exportAsCsv(exportRows.value, "current-page");
  ElMessage.success(`已导出当前页 ${exportRows.value.length} 条订单`);
};

const handleExportSelectedJson = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的订单");
    return;
  }

  downloadTextFile(
    buildExportFilename("selected", "json"),
    JSON.stringify(selectedExportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选订单`);
};

const handleExportSelectedCsv = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的订单");
    return;
  }

  exportAsCsv(selectedExportRows.value, "selected");
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 条勾选订单`);
};

const triggerSearch = async (immediate = false) => {
  clearSearchTimer();
  if (immediate || !searchKeyword.value.trim()) {
    currentPage.value = 1;
    await loadOrders(1);
    return;
  }

  searchTimer.value = window.setTimeout(() => {
    currentPage.value = 1;
    void loadOrders(1);
    searchTimer.value = null;
  }, 300);
};

const loadAccounts = async () => {
  try {
    accounts.value = await getAccountDetails();
  } catch {
    accounts.value = [];
    ElMessage.warning("账号列表加载失败");
  }
};

const loadOrders = async (page = currentPage.value) => {
  loading.value = true;
  try {
    const result = await getOrders(
      selectedAccount.value || undefined,
      selectedStatus.value || undefined,
      searchKeyword.value || undefined,
      page,
      PAGE_SIZE,
    );

    if (!result.success) {
      throw new Error();
    }

    orders.value = result.data || [];
    total.value = result.total || 0;
    totalPages.value = result.total_pages || 0;
    currentPage.value = page;
    await syncRouteQuery();
  } catch {
    orders.value = [];
    total.value = 0;
    totalPages.value = 0;
    ElMessage.error("订单列表加载失败");
  } finally {
    loading.value = false;
  }
};

const handleRefresh = async () => {
  await loadOrders(currentPage.value);
};

const handleCopyOrderId = async (orderId: string) => {
  try {
    await navigator.clipboard.writeText(orderId);
    ElMessage.success("订单号已复制");
  } catch {
    ElMessage.error("复制失败");
  }
};

const handleCopySelectedOrderIds = async () => {
  if (!selectedOrderIds.value.length) {
    ElMessage.warning("请先勾选订单");
    return;
  }

  try {
    await navigator.clipboard.writeText(selectedOrderIds.value.join("\n"));
    ElMessage.success(`已复制 ${selectedOrderIds.value.length} 条订单号`);
  } catch {
    ElMessage.error("复制失败");
  }
};

const handleResetFilters = async () => {
  clearSearchTimer();
  suppressFilterWatch.value = true;
  selectedAccount.value = "";
  selectedStatus.value = "";
  searchKeyword.value = "";
  currentPage.value = 1;
  suppressFilterWatch.value = false;
  await loadOrders(1);
};

const handleFetchOrders = async () => {
  if (!selectedAccount.value) {
    ElMessage.warning("请先选择账号后再获取订单");
    return;
  }

  fetching.value = true;
  try {
    const result = await fetchOrdersFromAccount(selectedAccount.value);
    if (!result.success) {
      ElMessage.error(result.message || "获取订单失败");
      return;
    }

    const fetchedCount = result.data?.fetched_count ?? 0;
    const savedCount = result.data?.saved_count ?? 0;
    ElMessage.success(
      result.message ||
        `成功抓取 ${fetchedCount} 条订单，保存 ${savedCount} 条`,
    );
    await loadOrders(1);
  } catch {
    ElMessage.error("获取订单失败");
  } finally {
    fetching.value = false;
  }
};

const handleShowDetail = async (order: Order) => {
  detailDialogVisible.value = true;
  detailLoading.value = true;
  orderDetail.value = null;

  try {
    const result = await getOrderDetail(order.order_id, order.cookie_id);
    if (!result.success || !result.data) {
      throw new Error();
    }
    orderDetail.value = result.data;
  } catch {
    detailDialogVisible.value = false;
    ElMessage.error("订单详情加载失败");
  } finally {
    detailLoading.value = false;
  }
};

const handleDelete = async (order: Order) => {
  try {
    await ElMessageBox.confirm(
      `确定删除订单 ${order.order_id} 吗？`,
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

  deletingOrderKey.value = getOrderRowKey(order);
  try {
    const result = await deleteOrder(order.order_id, order.cookie_id);
    if (!result.success) {
      ElMessage.error(result.message || "删除失败");
      return;
    }

    ElMessage.success("订单已删除");
    const nextPage =
      orders.value.length === 1 && currentPage.value > 1
        ? currentPage.value - 1
        : currentPage.value;
    await loadOrders(nextPage);
  } catch {
    ElMessage.error("删除失败");
  } finally {
    deletingOrderKey.value = null;
  }
};

const handleBatchDelete = async () => {
  if (!selectedOrders.value.length) {
    ElMessage.warning("请先勾选要删除的订单");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定批量删除 ${selectedOrders.value.length} 条订单吗？`,
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
    for (const order of selectedOrders.value) {
      const result = await deleteOrder(order.order_id, order.cookie_id);
      if (!result.success) {
        failedMessage = result.message || `订单 ${order.order_id} 删除失败`;
        break;
      }
      successCount += 1;
    }

    if (failedMessage) {
      ElMessage.error(
        `已删除 ${successCount} 条，剩余删除中断：${failedMessage}`,
      );
    } else {
      ElMessage.success(`已批量删除 ${successCount} 条订单`);
    }

    const nextPage =
      orders.value.length === successCount && currentPage.value > 1
        ? currentPage.value - 1
        : currentPage.value;
    clearSelectedOrders();
    await loadOrders(nextPage);
  } finally {
    bulkDeleting.value = false;
  }
};

watch([selectedAccount, selectedStatus], async () => {
  if (hydratingFromRoute.value || suppressFilterWatch.value) {
    return;
  }
  currentPage.value = 1;
  await loadOrders(1);
});

watch(searchKeyword, () => {
  if (hydratingFromRoute.value || suppressFilterWatch.value) {
    return;
  }
  void triggerSearch(false);
});

watch(
  () => route.query,
  async () => {
    if (syncingRouteQuery.value) {
      return;
    }
    applyRouteQueryState();
    if (!hydratingFromRoute.value) {
      await loadOrders(currentPage.value);
    }
  },
  { deep: true },
);

onMounted(async () => {
  applyRouteQueryState();
  await Promise.all([loadAccounts(), loadOrders(currentPage.value)]);
  hydratingFromRoute.value = false;
});

onBeforeUnmount(() => {
  clearSearchTimer();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">订单管理</h1>
        <p class="page-description">
          查看本地订单列表，支持按账号和状态筛选，并可主动抓取真实订单。
        </p>
      </div>
      <div class="page-actions">
        <el-button
          :icon="RefreshRight"
          :loading="loading"
          @click="handleRefresh"
        >
          刷新列表
        </el-button>
        <el-button
          type="primary"
          :icon="Download"
          :loading="fetching"
          @click="handleFetchOrders"
        >
          获取订单
        </el-button>
      </div>
    </section>

    <section class="filter-bar">
      <div class="inline-form">
        <div class="filter-title">
          <el-icon><Select /></el-icon>
          <span>筛选条件</span>
        </div>
        <el-form-item label="筛选账号">
          <el-select v-model="selectedAccount" clearable placeholder="所有账号">
            <el-option label="所有账号" value="" />
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="getAccountLabel(account.id)"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="订单状态">
          <el-select v-model="selectedStatus" placeholder="所有状态">
            <el-option
              v-for="status in orderStatusOptions"
              :key="status.value || 'all'"
              :label="status.label"
              :value="status.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="搜索订单">
          <el-input
            v-model="searchKeyword"
            clearable
            placeholder="搜索订单号、商品 ID 或买家 ID，回车立即搜索"
            @keyup.enter="triggerSearch(true)"
            @clear="triggerSearch(true)"
          />
        </el-form-item>

        <div class="filter-actions">
          <el-button @click="handleResetFilters">重置筛选</el-button>
        </div>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">
            当前页展示 {{ orders.length }} 条，累计 {{ total }} 条订单
          </div>
          <div class="toolbar-submeta">
            支持分页导出、路由保留筛选和批量删除订单
          </div>
        </div>
        <div class="table-toolbar-actions">
          <el-tag v-if="selectedOrders.length" type="success" effect="plain">
            已勾选 {{ selectedOrders.length }} 条
          </el-tag>
          <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
            启用 {{ activeFilterCount }} 个筛选
          </el-tag>
          <el-tag type="primary" effect="plain">
            已接通筛选、详情、抓取、删除和分页
          </el-tag>
          <el-button link :icon="Download" @click="handleExportCurrentJson">
            导出当前页 JSON
          </el-button>
          <el-button link :icon="Download" @click="handleExportCurrentCsv">
            导出当前页 CSV
          </el-button>
          <el-button
            link
            :icon="Download"
            :disabled="!selectedOrders.length"
            @click="handleExportSelectedJson"
          >
            导出勾选 JSON
          </el-button>
          <el-button
            link
            :icon="Download"
            :disabled="!selectedOrders.length"
            @click="handleExportSelectedCsv"
          >
            导出勾选 CSV
          </el-button>
          <el-button
            link
            :icon="Select"
            :disabled="!orders.length"
            @click="handleSelectCurrentPage"
          >
            勾选当前页
          </el-button>
          <el-button
            link
            :icon="CopyDocument"
            :disabled="!selectedOrders.length"
            @click="handleCopySelectedOrderIds"
          >
            复制勾选订单号
          </el-button>
          <el-button
            link
            type="danger"
            :disabled="!selectedOrders.length"
            @click="clearSelectedOrders"
          >
            清空勾选
          </el-button>
          <el-button
            link
            type="danger"
            :icon="Delete"
            :disabled="!canBatchDelete"
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
        :data="orders"
        :row-key="getOrderRowKey"
        style="width: 100%; margin-top: 16px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" fixed="left" />
        <el-table-column label="订单号" min-width="200">
          <template #default="{ row }">
            <span class="mono">{{ row.order_id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="商品 ID" min-width="150">
          <template #default="{ row }">
            <a
              v-if="row.item_id"
              class="mono item-link"
              :href="getItemUrl(row.item_id)"
              target="_blank"
              rel="noreferrer"
            >
              {{ row.item_id }}
            </a>
            <span v-else class="mono">-</span>
          </template>
        </el-table-column>

        <el-table-column label="买家 ID" min-width="160">
          <template #default="{ row }">
            <span class="mono">{{ row.buyer_id || "-" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="数量" width="90">
          <template #default="{ row }">
            <span>{{ row.quantity ?? 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="金额" width="120">
          <template #default="{ row }">
            <span class="amount-text">{{ formatOrderAmount(row.amount) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" effect="plain">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="小刀" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_bargain ? 'warning' : 'info'" effect="plain">
              {{ row.is_bargain ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="所属账号" min-width="180">
          <template #default="{ row }">
            <span>{{ getAccountLabel(row.cookie_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                link
                :icon="DocumentCopy"
                @click="handleCopyOrderId(row.order_id)"
              >
                复制
              </el-button>
              <el-button
                link
                type="primary"
                :icon="View"
                @click="handleShowDetail(row)"
              >
                详情
              </el-button>
              <el-button
                link
                type="danger"
                :icon="Delete"
                :loading="deletingOrderKey === getOrderRowKey(row)"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无订单数据" />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :page-size="PAGE_SIZE"
          :current-page="currentPage"
          :total="total"
          @current-change="loadOrders"
        />
        <div class="text-muted">
          第 {{ currentPage }} / {{ totalPages || 1 }} 页
        </div>
      </div>
    </el-card>

    <el-dialog
      v-model="detailDialogVisible"
      title="订单详情"
      width="760px"
      destroy-on-close
    >
      <el-skeleton v-if="detailLoading" :rows="8" animated />

      <template v-else-if="orderDetail">
        <div class="detail-grid">
          <el-card shadow="never">
            <template #header>基本信息</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="订单号">
                <span class="mono">{{ orderDetail.order_id }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="所属账号">
                {{ getAccountLabel(orderDetail.cookie_id) }}
              </el-descriptions-item>
              <el-descriptions-item label="商品 ID">
                <a
                  v-if="orderDetail.item_id"
                  class="mono item-link"
                  :href="getItemUrl(orderDetail.item_id)"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ orderDetail.item_id }}
                </a>
                <span v-else class="mono">-</span>
              </el-descriptions-item>
              <el-descriptions-item label="买家 ID">
                <span class="mono">{{ orderDetail.buyer_id || "-" }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="会话 ID">
                <span class="mono">{{ orderDetail.chat_id || "-" }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="订单状态">
                <el-tag
                  :type="getStatusTagType(orderDetail.status)"
                  effect="plain"
                >
                  {{ getStatusLabel(orderDetail.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="小刀订单">
                {{ orderDetail.is_bargain ? "是" : "否" }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never">
            <template #header>商品信息</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="规格名称">
                {{ orderDetail.spec_name || "-" }}
              </el-descriptions-item>
              <el-descriptions-item label="规格值">
                {{ orderDetail.spec_value || "-" }}
              </el-descriptions-item>
              <el-descriptions-item label="SKU 信息">
                {{ orderDetail.sku_info || "-" }}
              </el-descriptions-item>
              <el-descriptions-item label="数量">
                {{ orderDetail.quantity ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="金额">
                <span class="amount-text">{{
                  formatOrderAmount(orderDetail.amount)
                }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never">
            <template #header>时间信息</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="创建时间">
                {{ formatDateTime(orderDetail.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="更新时间">
                {{ formatDateTime(orderDetail.updated_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>
      </template>

      <el-empty v-else description="暂无详情数据" />

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
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
  color: #e2e8f0;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.amount-text {
  color: #d97706;
  font-weight: 600;
}

.item-link {
  color: #2563eb;
}

.pagination-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  align-items: end;
  gap: 16px;
  flex-wrap: wrap;
}

.inline-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.inline-form :deep(.el-form-item__label) {
  color: #cbd5e1;
}

.inline-form :deep(.el-select),
.inline-form :deep(.el-input) {
  width: 220px;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
}

@media (max-width: 900px) {
  .inline-form :deep(.el-select),
  .inline-form :deep(.el-input) {
    width: 100%;
  }
}
</style>
