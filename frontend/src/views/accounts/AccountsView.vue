<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  CircleCheck,
  CopyDocument,
  Download,
  Edit,
  Key,
  Plus,
  Promotion,
  RefreshRight,
  Remove,
  Search,
  Select,
  Switch,
  User,
  Warning,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type ElTable } from "element-plus";
import {
  addAccount,
  checkQRLoginStatus,
  deleteAccount,
  getAccountDetail,
  generateQRLogin,
  getAccountDetails,
  getAllAIReplySettings,
  getAIReplySettings,
  passwordLogin,
  refreshAccountProfile,
  updateAccountAutoConfirm,
  updateAccountCookie,
  updateAccountLoginInfo,
  updateAccountRemark,
  updateAccountStatus,
  updateAIReplySettings,
  type AIReplySettings,
} from "@/api/accounts";
import {
  getDefaultReply,
  getKeywordCounts,
  updateDefaultReply,
} from "@/api/keywords";
import type { AccountDetail } from "@/types";

type ModalType =
  | "qrcode"
  | "password"
  | "manual"
  | "edit"
  | "default-reply"
  | "ai-settings"
  | null;

interface AccountWithMeta extends AccountDetail {
  keywordCount?: number;
  aiEnabled?: boolean;
}

const loading = ref(true);
const saving = ref(false);
const accounts = ref<AccountWithMeta[]>([]);
const selectedRows = ref<AccountWithMeta[]>([]);
const activeModal = ref<ModalType>(null);
const currentAccount = ref<AccountWithMeta | null>(null);
const refreshingProfileId = ref<string | null>(null);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);
const keyword = ref("");
const statusFilter = ref<"all" | "enabled" | "disabled">("all");
const aiFilter = ref<"all" | "enabled" | "disabled">("all");

const qrCodeUrl = ref("");
const qrStatus = ref<
  "loading" | "ready" | "scanned" | "success" | "expired" | "error"
>("loading");
const qrPollingId = ref<number | null>(null);
const qrSessionId = ref("");

const passwordSubmitting = ref(false);
const manualSubmitting = ref(false);
const aiLoading = ref(false);
const defaultReplyLoading = ref(false);

const passwordForm = reactive({
  account: "",
  password: "",
  showBrowser: false,
});

const manualForm = reactive({
  id: "",
  cookie: "",
});

const editForm = reactive({
  note: "",
  cookie: "",
  autoConfirm: false,
  username: "",
  loginPassword: "",
  showBrowser: false,
});

const defaultReplyForm = reactive({
  enabled: true,
  replyContent: "",
  replyImageUrl: "",
  replyOnce: false,
});

const aiForm = reactive({
  enabled: false,
  maxDiscountPercent: 10,
  maxDiscountAmount: 100,
  maxBargainRounds: 3,
  customPrompts: "",
});

const accountCountText = computed(
  () =>
    `当前展示 ${filteredAccounts.value.length} / ${accounts.value.length} 个账号`,
);
const selectedAccountIds = computed(() =>
  selectedRows.value.map((account) => account.id).filter(Boolean),
);
const activeFilterCount = computed(() => {
  let count = 0;
  if (keyword.value.trim()) count += 1;
  if (statusFilter.value !== "all") count += 1;
  if (aiFilter.value !== "all") count += 1;
  return count;
});
const filteredAccounts = computed(() => {
  const query = keyword.value.trim().toLowerCase();

  return accounts.value.filter((account) => {
    if (statusFilter.value === "enabled" && account.enabled === false) {
      return false;
    }
    if (statusFilter.value === "disabled" && account.enabled !== false) {
      return false;
    }

    if (aiFilter.value === "enabled" && !account.aiEnabled) {
      return false;
    }
    if (aiFilter.value === "disabled" && account.aiEnabled) {
      return false;
    }

    if (!query) {
      return true;
    }

    const target = [
      account.id,
      getDisplayName(account),
      account.note || "",
      account.username || "",
      account.enabled !== false ? "启用" : "禁用",
      account.aiEnabled ? "ai开启" : "ai关闭",
    ]
      .join(" ")
      .toLowerCase();

    return target.includes(query);
  });
});

const exportRows = computed(() =>
  filteredAccounts.value.map((account) => ({
    id: account.id,
    nickname: getDisplayName(account),
    enabled: account.enabled !== false ? "启用" : "禁用",
    ai_enabled: account.aiEnabled ? "开启" : "关闭",
    keyword_count: String(account.keywordCount || 0),
    auto_confirm: account.auto_confirm ? "开启" : "关闭",
    auto_reply_once_per_customer: account.auto_reply_once_per_customer
      ? "开启"
      : "关闭",
    note: account.note || "",
    username: account.username || "",
  })),
);

const selectedExportRows = computed(() =>
  selectedRows.value.map((account) => ({
    id: account.id,
    nickname: getDisplayName(account),
    enabled: account.enabled !== false ? "启用" : "禁用",
    ai_enabled: account.aiEnabled ? "开启" : "关闭",
    keyword_count: String(account.keywordCount || 0),
    auto_confirm: account.auto_confirm ? "开启" : "关闭",
    auto_reply_once_per_customer: account.auto_reply_once_per_customer
      ? "开启"
      : "关闭",
    note: account.note || "",
    username: account.username || "",
  })),
);

const getDisplayName = (account: AccountWithMeta) => {
  return account.xianyu_nickname?.trim() || account.id;
};

const getAvatarText = (account: AccountWithMeta) => {
  return getDisplayName(account).trim().charAt(0) || "账";
};

const resetPasswordForm = () => {
  passwordForm.account = "";
  passwordForm.password = "";
  passwordForm.showBrowser = false;
};

const resetManualForm = () => {
  manualForm.id = "";
  manualForm.cookie = "";
};

const resetEditForm = () => {
  editForm.note = "";
  editForm.cookie = "";
  editForm.autoConfirm = false;
  editForm.username = "";
  editForm.loginPassword = "";
  editForm.showBrowser = false;
};

const resetDefaultReplyForm = () => {
  defaultReplyForm.enabled = true;
  defaultReplyForm.replyContent = "";
  defaultReplyForm.replyImageUrl = "";
  defaultReplyForm.replyOnce = false;
};

const resetAiForm = () => {
  aiForm.enabled = false;
  aiForm.maxDiscountPercent = 10;
  aiForm.maxDiscountAmount = 100;
  aiForm.maxBargainRounds = 3;
  aiForm.customPrompts = "";
};

const clearQrPolling = () => {
  if (qrPollingId.value) {
    window.clearInterval(qrPollingId.value);
    qrPollingId.value = null;
  }
};

const closeModal = () => {
  activeModal.value = null;
  currentAccount.value = null;
  saving.value = false;
  passwordSubmitting.value = false;
  manualSubmitting.value = false;
  aiLoading.value = false;
  defaultReplyLoading.value = false;
  qrCodeUrl.value = "";
  qrStatus.value = "loading";
  qrSessionId.value = "";
  clearQrPolling();
  resetPasswordForm();
  resetManualForm();
  resetEditForm();
  resetDefaultReplyForm();
  resetAiForm();
};

const loadAccounts = async () => {
  loading.value = true;
  try {
    const [accountDetails, aiSettingsMap, keywordCounts] = await Promise.all([
      getAccountDetails(),
      getAllAIReplySettings().catch(
        () => ({}) as Record<string, AIReplySettings>,
      ),
      getKeywordCounts().catch(() => ({} as Record<string, number>)),
    ]);

    const enriched = accountDetails.map((account) => ({
      ...account,
      keywordCount: keywordCounts[account.id] || 0,
      aiEnabled:
        aiSettingsMap[account.id]?.ai_enabled ??
        aiSettingsMap[account.id]?.enabled ??
        false,
    }));

    accounts.value = enriched;
  } catch {
    accounts.value = [];
    ElMessage.error("账号列表加载失败");
  } finally {
    loading.value = false;
  }
};

const handleSelectionChange = (rows: AccountWithMeta[]) => {
  selectedRows.value = rows;
};

const clearSelection = () => {
  selectedRows.value = [];
  tableRef.value?.clearSelection();
};

const handleSelectFilteredAccounts = () => {
  if (!filteredAccounts.value.length) {
    ElMessage.warning("当前没有可勾选的账号");
    return;
  }

  tableRef.value?.clearSelection();
  filteredAccounts.value.forEach((account) => {
    tableRef.value?.toggleRowSelection(account, true);
  });
  ElMessage.success(`已勾选 ${filteredAccounts.value.length} 个账号`);
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
  return `accounts-${scope}-${time}.${extension}`;
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
    ElMessage.warning("当前没有可导出的账号");
    return;
  }

  downloadTextFile(
    buildExportFilename("filtered", "json"),
    JSON.stringify(exportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${exportRows.value.length} 个筛选账号`);
};

const handleExportFilteredCsv = () => {
  if (!exportRows.value.length) {
    ElMessage.warning("当前没有可导出的账号");
    return;
  }

  exportAsCsv(exportRows.value, "filtered");
  ElMessage.success(`已导出 ${exportRows.value.length} 个筛选账号`);
};

const handleExportSelectedJson = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的账号");
    return;
  }

  downloadTextFile(
    buildExportFilename("selected", "json"),
    JSON.stringify(selectedExportRows.value, null, 2),
    "application/json;charset=utf-8",
  );
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 个勾选账号`);
};

const handleExportSelectedCsv = () => {
  if (!selectedExportRows.value.length) {
    ElMessage.warning("请先勾选要导出的账号");
    return;
  }

  exportAsCsv(selectedExportRows.value, "selected");
  ElMessage.success(`已导出 ${selectedExportRows.value.length} 个勾选账号`);
};

const handleCopySelectedAccountIds = async () => {
  if (!selectedAccountIds.value.length) {
    ElMessage.warning("请先勾选账号");
    return;
  }

  try {
    await navigator.clipboard.writeText(selectedAccountIds.value.join("\n"));
    ElMessage.success(`已复制 ${selectedAccountIds.value.length} 个账号 ID`);
  } catch {
    ElMessage.error("复制失败");
  }
};

const openQrLogin = async () => {
  activeModal.value = "qrcode";
  qrStatus.value = "loading";
  clearQrPolling();

  try {
    const result = await generateQRLogin();
    if (!result.success || !result.qr_code_url || !result.session_id) {
      qrStatus.value = "error";
      ElMessage.error(result.message || "生成二维码失败");
      return;
    }

    qrCodeUrl.value = result.qr_code_url;
    qrSessionId.value = result.session_id;
    qrStatus.value = "ready";
    qrPollingId.value = window.setInterval(async () => {
      try {
        const statusResult = await checkQRLoginStatus(
          result.session_id as string,
        );
        if (!statusResult.success && statusResult.status !== "expired") {
          return;
        }

        if (
          statusResult.status === "scanned" ||
          statusResult.status === "processing"
        ) {
          qrStatus.value = "scanned";
          return;
        }

        if (
          statusResult.status === "success" ||
          statusResult.status === "already_processed"
        ) {
          qrStatus.value = "success";
          clearQrPolling();
          ElMessage.success(
            statusResult.account_info?.account_id
              ? `账号 ${statusResult.account_info.account_id} 登录成功`
              : "扫码登录成功",
          );
          await loadAccounts();
          window.setTimeout(() => {
            closeModal();
          }, 1200);
          return;
        }

        if (statusResult.status === "expired") {
          qrStatus.value = "expired";
          clearQrPolling();
          return;
        }

        if (statusResult.status === "cancelled") {
          clearQrPolling();
          ElMessage.warning("用户已取消扫码");
          closeModal();
        }
      } catch {
        // keep polling
      }
    }, 2000);
  } catch {
    qrStatus.value = "error";
    ElMessage.error("生成二维码失败");
  }
};

const submitPasswordLogin = async () => {
  if (!passwordForm.account.trim() || !passwordForm.password.trim()) {
    ElMessage.warning("请输入账号和密码");
    return;
  }

  passwordSubmitting.value = true;
  try {
    const result = await passwordLogin({
      account_id: passwordForm.account.trim(),
      account: passwordForm.account.trim(),
      password: passwordForm.password,
      show_browser: passwordForm.showBrowser,
    });

    if (result.success) {
      ElMessage.success("登录请求已提交，请稍后刷新账号列表");
      closeModal();
      window.setTimeout(() => {
        void loadAccounts();
      }, 3000);
      return;
    }

    ElMessage.error(result.message || result.detail || "账号密码登录失败");
  } catch {
    ElMessage.error("账号密码登录失败");
  } finally {
    passwordSubmitting.value = false;
  }
};

const submitManualAdd = async () => {
  if (!manualForm.id.trim()) {
    ElMessage.warning("请输入账号 ID");
    return;
  }
  if (!manualForm.cookie.trim()) {
    ElMessage.warning("请输入 Cookie");
    return;
  }

  manualSubmitting.value = true;
  try {
    const result = await addAccount({
      id: manualForm.id.trim(),
      cookie: manualForm.cookie.trim(),
    });
    if (result.success || result.msg === "success") {
      ElMessage.success("账号添加成功");
      await loadAccounts();
      closeModal();
      return;
    }
    ElMessage.error(result.message || result.detail || "添加账号失败");
  } catch {
    ElMessage.error("添加账号失败");
  } finally {
    manualSubmitting.value = false;
  }
};

const openEditModal = async (account: AccountWithMeta) => {
  try {
    const detail = await getAccountDetail(account.id);
    const mergedAccount: AccountWithMeta = {
      ...account,
      ...detail,
      keywordCount: account.keywordCount,
      aiEnabled: account.aiEnabled,
    };

    currentAccount.value = mergedAccount;
    editForm.note = mergedAccount.note || "";
    editForm.cookie = mergedAccount.cookie || "";
    editForm.autoConfirm = Boolean(mergedAccount.auto_confirm);
    editForm.username = mergedAccount.username || "";
    editForm.loginPassword = mergedAccount.login_password || "";
    editForm.showBrowser = Boolean(mergedAccount.show_browser);
    activeModal.value = "edit";
  } catch {
    ElMessage.error("账号详情加载失败");
  }
};

const submitEdit = async () => {
  if (!currentAccount.value) return;

  saving.value = true;
  try {
    const tasks: Promise<unknown>[] = [];
    const account = currentAccount.value;

    if (editForm.note.trim() !== (account.note || "")) {
      tasks.push(updateAccountRemark(account.id, editForm.note.trim()));
    }
    if (
      editForm.cookie.trim() &&
      editForm.cookie.trim() !== (account.cookie || "")
    ) {
      tasks.push(updateAccountCookie(account.id, editForm.cookie.trim()));
    }
    if (Boolean(editForm.autoConfirm) !== Boolean(account.auto_confirm)) {
      tasks.push(
        updateAccountAutoConfirm(account.id, Boolean(editForm.autoConfirm)),
      );
    }

    const loginChanged =
      editForm.username !== (account.username || "") ||
      editForm.loginPassword !== (account.login_password || "") ||
      Boolean(editForm.showBrowser) !== Boolean(account.show_browser);

    if (loginChanged) {
      tasks.push(
        updateAccountLoginInfo(account.id, {
          username: editForm.username,
          login_password: editForm.loginPassword,
          show_browser: editForm.showBrowser,
        }),
      );
    }

    await Promise.all(tasks);
    ElMessage.success("账号信息已更新");
    await loadAccounts();
    closeModal();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const openDefaultReplyModal = async (account: AccountWithMeta) => {
  currentAccount.value = account;
  activeModal.value = "default-reply";
  defaultReplyLoading.value = true;
  resetDefaultReplyForm();

  try {
    const result = await getDefaultReply(account.id);
    defaultReplyForm.enabled = result.enabled ?? true;
    defaultReplyForm.replyContent = result.reply_content || "";
    defaultReplyForm.replyImageUrl = result.reply_image_url || "";
    defaultReplyForm.replyOnce = result.reply_once || false;
  } catch {
    ElMessage.warning("默认回复配置加载失败");
  } finally {
    defaultReplyLoading.value = false;
  }
};

const submitDefaultReply = async () => {
  if (!currentAccount.value) return;

  saving.value = true;
  try {
    await updateDefaultReply(
      currentAccount.value.id,
      defaultReplyForm.replyContent,
      defaultReplyForm.enabled,
      defaultReplyForm.replyOnce,
      defaultReplyForm.replyImageUrl,
    );
    ElMessage.success("默认回复已保存");
    closeModal();
  } catch {
    ElMessage.error("默认回复保存失败");
  } finally {
    saving.value = false;
  }
};

const toggleEnabled = async (account: AccountWithMeta) => {
  try {
    await updateAccountStatus(account.id, !account.enabled);
    ElMessage.success(account.enabled ? "账号已禁用" : "账号已启用");
    await loadAccounts();
  } catch {
    ElMessage.error("状态切换失败");
  }
};

const handleDelete = async (account: AccountWithMeta) => {
  try {
    await ElMessageBox.confirm(`确定删除账号 ${account.id} 吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await deleteAccount(account.id);
    ElMessage.success("账号已删除");
    await loadAccounts();
  } catch {
    // ignore cancel
  }
};

const handleRefreshProfile = async (account: AccountWithMeta) => {
  refreshingProfileId.value = account.id;
  try {
    const result = await refreshAccountProfile(account.id);
    if (result.success) {
      ElMessage.success("闲鱼头像和昵称已刷新");
      await loadAccounts();
    } else {
      ElMessage.warning(result.message || "刷新资料失败");
    }
  } catch {
    ElMessage.error("刷新资料失败");
  } finally {
    refreshingProfileId.value = null;
  }
};

const handleToggleAi = async (account: AccountWithMeta) => {
  const nextEnabled = !account.aiEnabled;
  try {
    await updateAIReplySettings(account.id, { ai_enabled: nextEnabled });
    account.aiEnabled = nextEnabled;
    ElMessage.success(`AI 回复已${nextEnabled ? "开启" : "关闭"}`);
  } catch {
    ElMessage.error("AI 回复状态更新失败");
  }
};

const openAiSettings = async (account: AccountWithMeta) => {
  currentAccount.value = account;
  activeModal.value = "ai-settings";
  aiLoading.value = true;
  resetAiForm();

  try {
    const result = await getAIReplySettings(account.id);
    aiForm.enabled = result.ai_enabled ?? result.enabled ?? false;
    aiForm.maxDiscountPercent = result.max_discount_percent ?? 10;
    aiForm.maxDiscountAmount = result.max_discount_amount ?? 100;
    aiForm.maxBargainRounds = result.max_bargain_rounds ?? 3;
    aiForm.customPrompts = result.custom_prompts ?? "";
  } catch {
    ElMessage.warning("AI 设置加载失败");
  } finally {
    aiLoading.value = false;
  }
};

const submitAiSettings = async () => {
  if (!currentAccount.value) return;

  saving.value = true;
  try {
    await updateAIReplySettings(currentAccount.value.id, {
      enabled: aiForm.enabled,
      max_discount_percent: aiForm.maxDiscountPercent,
      max_discount_amount: aiForm.maxDiscountAmount,
      max_bargain_rounds: aiForm.maxBargainRounds,
      custom_prompts: aiForm.customPrompts,
    });
    const target = accounts.value.find(
      (item) => item.id === currentAccount.value?.id,
    );
    if (target) {
      target.aiEnabled = aiForm.enabled;
    }
    ElMessage.success("AI 设置已保存");
    closeModal();
  } catch {
    ElMessage.error("AI 设置保存失败");
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  await loadAccounts();
});

onBeforeUnmount(() => {
  clearQrPolling();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">账号管理</h1>
      </div>
      <div class="page-actions">
        <el-button :icon="RefreshRight" @click="loadAccounts">
          刷新列表
        </el-button>
      </div>
    </section>

    <section class="entry-panel">
      <div class="section-label">
        <el-icon><Plus /></el-icon>
        <span>接入方式</span>
      </div>
      <div class="account-entry-grid">
        <button class="entry-card primary" type="button" @click="openQrLogin">
          <span class="entry-icon"
            ><el-icon><User /></el-icon
          ></span>
          <span>
            <strong>扫码登录</strong>
            <small>推荐方式，直接接入后端扫码登录能力</small>
          </span>
        </button>

        <button
          class="entry-card"
          type="button"
          @click="activeModal = 'password'"
        >
          <span class="entry-icon"
            ><el-icon><Key /></el-icon
          ></span>
          <span>
            <strong>账号密码</strong>
            <small>使用账号密码触发后端登录流程</small>
          </span>
        </button>

        <button
          class="entry-card"
          type="button"
          @click="activeModal = 'manual'"
        >
          <span class="entry-icon"
            ><el-icon><Plus /></el-icon
          ></span>
          <span>
            <strong>手动输入</strong>
            <small>直接录入账号 ID 与 Cookie</small>
          </span>
        </button>
      </div>
    </section>

    <section class="filter-bar">
      <div class="section-label">
        <el-icon><Search /></el-icon>
        <span>筛选与批量操作</span>
      </div>
      <div class="inline-form">
        <el-form-item label="搜索账号">
          <el-input
            v-model="keyword"
            clearable
            :prefix-icon="Search"
            placeholder="搜索账号 ID、昵称、备注或登录账号"
          />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="statusFilter" style="width: 180px">
            <el-option label="全部状态" value="all" />
            <el-option label="仅启用" value="enabled" />
            <el-option label="仅禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="AI 状态">
          <el-select v-model="aiFilter" style="width: 180px">
            <el-option label="全部 AI" value="all" />
            <el-option label="仅 AI 开启" value="enabled" />
            <el-option label="仅 AI 关闭" value="disabled" />
          </el-select>
        </el-form-item>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">{{ accountCountText }}</div>
          <div class="toolbar-submeta">
            支持导出筛选结果、复制账号 ID 和勾选批量处理
          </div>
        </div>
        <div class="table-toolbar-actions">
          <el-tag v-if="selectedRows.length" type="success" effect="plain">
            已勾选 {{ selectedRows.length }} 个
          </el-tag>
          <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
            启用 {{ activeFilterCount }} 个筛选
          </el-tag>
          <el-tag type="primary" effect="plain"
            >已接入启停、编辑、默认回复和 AI 设置</el-tag
          >
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
            :disabled="!filteredAccounts.length"
            @click="handleSelectFilteredAccounts"
          >
            勾选筛选结果
          </el-button>
          <el-button
            link
            :icon="CopyDocument"
            :disabled="!selectedRows.length"
            @click="handleCopySelectedAccountIds"
          >
            复制账号 ID
          </el-button>
          <el-button
            link
            type="danger"
            :disabled="!selectedRows.length"
            @click="clearSelection"
          >
            清空勾选
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredAccounts"
        style="width: 100%; margin-top: 16px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" />
        <el-table-column label="闲鱼账号" min-width="260">
          <template #default="{ row }">
            <div class="account-cell">
              <img
                v-if="row.xianyu_avatar_url"
                :src="row.xianyu_avatar_url"
                :alt="getDisplayName(row)"
                class="account-avatar"
              />
              <div v-else class="account-avatar fallback">
                {{ getAvatarText(row) }}
              </div>
              <div class="cell-title">
                <div class="cell-title-main">{{ getDisplayName(row) }}</div>
                <div class="cell-title-sub mono">ID: {{ row.id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="关键词" width="110">
          <template #default="{ row }">
            <span>{{ row.keywordCount || 0 }} 个</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.enabled !== false ? 'success' : 'info'"
              effect="plain"
            >
              {{ row.enabled !== false ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="AI 回复" width="110">
          <template #default="{ row }">
            <el-button
              link
              :type="row.aiEnabled ? 'primary' : 'info'"
              @click="handleToggleAi(row)"
            >
              {{ row.aiEnabled ? "已开启" : "已关闭" }}
            </el-button>
          </template>
        </el-table-column>

        <el-table-column label="自动确认" width="110">
          <template #default="{ row }">
            <el-tag
              :type="row.auto_confirm ? 'success' : 'info'"
              effect="plain"
            >
              {{ row.auto_confirm ? "开启" : "关闭" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="只回一次" width="130">
          <template #default="{ row }">
            <span>{{
              row.auto_reply_once_per_customer ? "开启" : "关闭"
            }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="340" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                link
                type="primary"
                :icon="Promotion"
                @click="openAiSettings(row)"
                >AI 设置</el-button
              >
              <el-button
                link
                type="success"
                :icon="CircleCheck"
                @click="openDefaultReplyModal(row)"
                >默认回复</el-button
              >
              <el-button
                link
                type="info"
                :icon="RefreshRight"
                :loading="refreshingProfileId === row.id"
                @click="handleRefreshProfile(row)"
              >
                刷新资料
              </el-button>
              <el-button
                link
                type="primary"
                :icon="Edit"
                @click="openEditModal(row)"
                >编辑</el-button
              >
              <el-button
                link
                :type="row.enabled !== false ? 'warning' : 'success'"
                :icon="Switch"
                @click="toggleEnabled(row)"
              >
                {{ row.enabled !== false ? "禁用" : "启用" }}
              </el-button>
              <el-button
                link
                type="danger"
                :icon="Remove"
                @click="handleDelete(row)"
                >删除</el-button
              >
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无账号数据，请先添加账号" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      :model-value="activeModal === 'qrcode'"
      title="扫码登录"
      width="420px"
      @close="closeModal"
    >
      <div class="dialog-stack center">
        <el-skeleton v-if="qrStatus === 'loading'" :rows="4" animated />
        <template v-else-if="qrStatus === 'ready' || qrStatus === 'scanned'">
          <img :src="qrCodeUrl" alt="扫码登录二维码" class="qr-image" />
          <p class="text-muted">
            {{
              qrStatus === "scanned"
                ? "已扫码，等待手机确认"
                : "请使用闲鱼 App 扫描二维码"
            }}
          </p>
        </template>
        <template v-else-if="qrStatus === 'success'">
          <el-result
            icon="success"
            title="登录成功"
            sub-title="账号已接入，列表即将刷新"
          />
        </template>
        <template v-else-if="qrStatus === 'expired'">
          <el-result
            icon="warning"
            title="二维码已过期"
            sub-title="请重新生成二维码"
          >
            <template #extra>
              <el-button type="primary" @click="openQrLogin"
                >重新生成</el-button
              >
            </template>
          </el-result>
        </template>
        <template v-else>
          <el-result icon="error" title="生成二维码失败" sub-title="请稍后重试">
            <template #extra>
              <el-button type="primary" @click="openQrLogin">重试</el-button>
            </template>
          </el-result>
        </template>
      </div>
    </el-dialog>

    <el-dialog
      :model-value="activeModal === 'password'"
      title="账号密码登录"
      width="460px"
      @close="closeModal"
    >
      <el-form label-position="top">
        <el-form-item label="账号">
          <el-input
            v-model="passwordForm.account"
            placeholder="请输入闲鱼账号/手机号"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="passwordForm.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="调试选项">
          <el-switch v-model="passwordForm.showBrowser" />
          <span class="switch-label">显示浏览器</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button
          type="primary"
          :loading="passwordSubmitting"
          @click="submitPasswordLogin"
          >提交</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      :model-value="activeModal === 'manual'"
      title="手动添加账号"
      width="560px"
      @close="closeModal"
    >
      <el-form label-position="top">
        <el-form-item label="账号 ID">
          <el-input v-model="manualForm.id" placeholder="请输入账号 ID" />
        </el-form-item>
        <el-form-item label="Cookie">
          <el-input
            v-model="manualForm.cookie"
            type="textarea"
            :rows="7"
            placeholder="请粘贴完整 Cookie"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button
          type="primary"
          :loading="manualSubmitting"
          @click="submitManualAdd"
          >添加账号</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      :model-value="activeModal === 'edit'"
      title="编辑账号"
      width="720px"
      @close="closeModal"
    >
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="editForm.note" placeholder="添加备注信息" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Cookie">
          <el-input
            v-model="editForm.cookie"
            type="textarea"
            :rows="5"
            placeholder="更新 Cookie 值"
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="自动确认发货">
              <el-switch v-model="editForm.autoConfirm" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="显示浏览器">
              <el-switch v-model="editForm.showBrowser" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="登录账号">
              <el-input
                v-model="editForm.username"
                placeholder="手机号或用户名"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="登录密码">
              <el-input
                v-model="editForm.loginPassword"
                type="password"
                show-password
                placeholder="登录密码"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit"
          >保存</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      :model-value="activeModal === 'default-reply'"
      title="默认回复配置"
      width="680px"
      @close="closeModal"
    >
      <el-skeleton v-if="defaultReplyLoading" :rows="6" animated />
      <el-form v-else label-position="top">
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
            :rows="6"
            placeholder="当没有匹配到关键词时，使用此默认回复"
          />
        </el-form-item>
        <el-form-item label="回复图片 URL">
          <el-input
            v-model="defaultReplyForm.replyImageUrl"
            placeholder="可选，填写回复图片 URL"
          />
        </el-form-item>
        <div class="tips-box">
          <el-icon><Warning /></el-icon>
          <span
            >支持变量：`{send_user_name}`、`{send_user_id}`、`{send_message}`</span
          >
        </div>
      </el-form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitDefaultReply"
          >保存</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      :model-value="activeModal === 'ai-settings'"
      title="AI 回复设置"
      width="720px"
      @close="closeModal"
    >
      <el-skeleton v-if="aiLoading" :rows="7" animated />
      <el-form v-else label-position="top">
        <el-form-item label="启用 AI 回复">
          <el-switch v-model="aiForm.enabled" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="最大折扣（%）">
              <el-input-number
                v-model="aiForm.maxDiscountPercent"
                :min="0"
                :max="100"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大减价（元）">
              <el-input-number
                v-model="aiForm.maxDiscountAmount"
                :min="0"
                :max="99999"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大议价轮数">
              <el-input-number
                v-model="aiForm.maxBargainRounds"
                :min="1"
                :max="10"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="自定义提示词（JSON）">
          <el-input
            v-model="aiForm.customPrompts"
            type="textarea"
            :rows="8"
            placeholder='{"classify":"分类提示词","price":"议价提示词","default":"默认提示词"}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAiSettings"
          >保存</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #0f172a;
}

.entry-panel,
.filter-bar {
  margin-top: 24px;
}

.filter-bar {
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
  margin-top: 12px;
}

.inline-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.inline-form :deep(.el-input),
.inline-form :deep(.el-select) {
  width: 220px;
}

.account-entry-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 28px;
}

.entry-card {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.entry-card:hover {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.28);
  box-shadow: 0 16px 28px -24px rgba(37, 99, 235, 0.45);
}

.entry-card.primary {
  background: linear-gradient(
    135deg,
    rgba(37, 99, 235, 0.08),
    rgba(59, 130, 246, 0.04)
  );
}

.entry-card strong {
  display: block;
  color: #0f172a;
}

.entry-card small {
  display: block;
  margin-top: 6px;
  color: #64748b;
  line-height: 1.5;
}

.entry-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 18px;
  flex-shrink: 0;
}

.account-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
}

.account-avatar.fallback {
  display: grid;
  place-items: center;
  background: #e2e8f0;
  color: #334155;
  font-weight: 600;
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

.dialog-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-stack.center {
  align-items: center;
  text-align: center;
}

.switch-label {
  margin-left: 10px;
  color: #64748b;
}

.qr-image {
  width: 220px;
  height: 220px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.tips-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
}

@media (max-width: 1080px) {
  .account-entry-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .inline-form :deep(.el-input),
  .inline-form :deep(.el-select) {
    width: 100%;
  }
}
</style>
