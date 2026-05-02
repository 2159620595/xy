<template>
  <JudianPageLayout
    :title="sectionMeta.title"
    :description="sectionMeta.description"
    :stats="stats"
    :last-updated-text="lastUpdatedText"
  >
    <template #actions>
      <el-space>
        <el-button :loading="loading" @click="loadPage">刷新列表</el-button>
      </el-space>
    </template>

    <el-card shadow="never" class="cdkey-generate-card">
      <template #header>批量生成卡密</template>
      <el-alert
        v-if="!accountOptions.length"
        type="warning"
        :closable="false"
        class="cdkey-card-alert"
      >
        当前还没有可用的聚点账号，请先去“账户登录”页面完成真实账号登录。
      </el-alert>
      <el-alert v-else type="info" :closable="false" class="cdkey-card-alert">
        以下卡密数据直接写入聚点真实数据库；生成后会立即出现在库存列表，并可用于后续兑换流程。
      </el-alert>

      <el-form label-position="top" class="cdkey-generate-form">
        <div class="cdkey-generate-grid">
          <el-form-item
            label="卡密规格"
            class="cdkey-generate-field cdkey-generate-field--spec"
          >
            <div class="cdkey-spec-picker">
              <el-space wrap>
                <el-button
                  v-for="item in specOptions"
                  :key="item.value"
                  size="small"
                  :type="
                    activeSpecPreset === item.value ? 'primary' : 'default'
                  "
                  :plain="activeSpecPreset !== item.value"
                  @click="applySpecPreset(item)"
                >
                  {{ item.label }}
                </el-button>
              </el-space>
              <span class="cdkey-spec-picker__hint"
                >按 5 钻 = 1 天自动换算，可继续手动微调</span
              >
            </div>
          </el-form-item>
          <el-form-item
            label="绑定账户"
            class="cdkey-generate-field cdkey-generate-field--account"
          >
            <el-select v-model="form.accountId" placeholder="请选择聚点账号">
              <el-option
                v-for="item in accountOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="授权天数"
            class="cdkey-generate-field cdkey-generate-field--number"
          >
            <el-input-number
              v-model="form.duration"
              :min="1"
              :max="365"
              style="width: 100%"
              @change="handleDurationChange"
            />
          </el-form-item>
          <el-form-item
            label="生成数量"
            class="cdkey-generate-field cdkey-generate-field--number"
          >
            <el-input-number
              v-model="form.count"
              :min="1"
              :max="50"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item
            label="使用额度（钻石）"
            class="cdkey-generate-field cdkey-generate-field--number"
          >
            <el-input-number
              v-model="form.maxUses"
              :min="0"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item
            label="备注"
            class="cdkey-generate-field cdkey-generate-field--remark"
          >
            <el-input v-model="form.remark" placeholder="例如：直播间活动" />
          </el-form-item>
        </div>

        <div class="cdkey-generate-actions">
          <div class="cdkey-generate-actions__inner">
            <el-button size="small" @click="resetForm">重置</el-button>
            <el-button
              size="small"
              type="primary"
              :loading="generating"
              :disabled="!accountOptions.length"
              @click="handleGenerate"
            >
              立即生成
            </el-button>
          </div>
        </div>
      </el-form>
    </el-card>

    <el-card shadow="never" class="cdkey-table-card">
      <template #header>
        <div class="cdkey-card-header">
          <span>卡密库存管理</span>
          <el-space class="cdkey-toolbar" wrap>
            <el-input
              v-model="searchKeyword"
              clearable
              placeholder="搜索卡密/备注/订单号/会话号"
              style="width: 240px"
            />
            <el-select
              v-model="exportSpec"
              placeholder="导出规格"
              style="width: 200px"
            >
              <el-option
                v-for="item in exportSpecOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-button
              type="primary"
              plain
              @click="handleExportUnusedCodesBySpec"
            >
              导出原卡密
            </el-button>
            <el-button
              type="info"
              plain
              @click="handleExportUnusedRedeemUrlsBySpec"
            >
              导出访问卡密
            </el-button>
            <el-select
              v-model="filterAccount"
              placeholder="筛选账户"
              clearable
              style="width: 180px"
            >
              <el-option
                v-for="item in filterAccountOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-select
              v-model="filterStatus"
              placeholder="筛选状态"
              clearable
              style="width: 140px"
            >
              <el-option
                v-for="item in statusOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-button type="warning" plain @click="confirmCleanInactive">
              清理过期/作废卡密
            </el-button>
          </el-space>
        </div>
      </template>

      <el-table
        class="cdkey-table"
        :data="pagedRows"
        stripe
        v-loading="loading"
      >
        <el-table-column label="卡密串码" min-width="180">
          <template #default="{ row }">
            <span class="cdkey-code">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="绑定账号" min-width="180">
          <template #default="{ row }">
            {{ resolveAccountName(row.accountId) }}
          </template>
        </el-table-column>
        <el-table-column label="授权天数" width="140">
          <template #default="{ row }">
            {{ resolveDurationText(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column label="已使用进度" min-width="220">
          <template #default="{ row }">
            <div class="cdkey-usage-progress">
              <div class="cdkey-usage-progress__summary">
                {{ resolveUsageProgress(row).summary }}
              </div>
              <template v-if="!resolveUsageProgress(row).unlimited">
                <el-progress
                  :percentage="resolveUsageProgress(row).percentage"
                  :status="resolveUsageProgress(row).status"
                  :show-text="false"
                  :stroke-width="14"
                />
              </template>
              <div class="cdkey-usage-progress__meta">
                {{ resolveUsageProgress(row).meta }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="resolveStatusType(row.status)">
              {{ statusMap[row.status]?.label || "未知" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" min-width="180" />
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column label="操作" min-width="280" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button
                size="small"
                text
                type="primary"
                @click="copyCode(row.code)"
              >
                复制
              </el-button>
              <el-button
                size="small"
                text
                type="primary"
                @click="copyRedeemUrl(row.code)"
              >
                兑换链接
              </el-button>
              <el-button
                size="small"
                text
                type="success"
                @click="previewRedeem(row.code)"
              >
                打开页面
              </el-button>
              <el-button
                size="small"
                text
                type="info"
                @click="openUsageDetail(row)"
              >
                使用详情
              </el-button>
              <el-button
                size="small"
                text
                type="danger"
                :disabled="row.status === 'void'"
                @click="confirmVoid(row)"
              >
                作废
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[20, 50, 100, 200]"
          :total="filteredRows.length"
        />
        <div class="pagination-text">
          第 {{ currentPage }} / {{ totalPages || 1 }} 页
        </div>
      </div>
    </el-card>

    <el-dialog
      v-model="usageDetailVisible"
      title="卡密使用详情"
      width="920px"
      class="cdkey-detail-dialog"
    >
      <template v-if="detailRow">
        <div class="cdkey-detail-summary">
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">卡密</span>
            <span
              class="cdkey-detail-summary__value cdkey-detail-summary__value--mono"
            >
              {{ detailRow.code || "—" }}
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">绑定账号</span>
            <span class="cdkey-detail-summary__value">
              {{ resolveAccountName(detailRow.accountId) }}
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">最近订单</span>
            <span
              class="cdkey-detail-summary__value cdkey-detail-summary__value--mono"
            >
              {{ detailRow.latestOrderId || "—" }}
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">最近会话</span>
            <span
              class="cdkey-detail-summary__value cdkey-detail-summary__value--mono"
            >
              {{ detailRow.latestSessionId || "—" }}
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">售后批次</span>
            <span class="cdkey-detail-summary__value">
              {{ detailRecords.length }} 批
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">累计次数</span>
            <span class="cdkey-detail-summary__value">
              {{ detailTotalSuccessCount }} 次
            </span>
          </div>
          <div class="cdkey-detail-summary__item">
            <span class="cdkey-detail-summary__label">最近存证时间</span>
            <span class="cdkey-detail-summary__value">
              {{ detailRow.latestSuccessPaymentAt || "—" }}
            </span>
          </div>
        </div>

        <el-alert
          v-if="!detailRecords.length"
          type="info"
          :closable="false"
          class="cdkey-detail-empty"
        >
          这张卡密目前还没有售后存证记录。
        </el-alert>

        <div v-else class="cdkey-detail-content">
          <div class="cdkey-detail-section">
            <div class="cdkey-detail-section__header">
              <div class="cdkey-detail-section__title">最近售后记录</div>
              <div class="cdkey-detail-section__meta">
                共 {{ detailRecords.length }} 批 /
                {{ detailTotalSuccessCount }} 次
              </div>
            </div>
            <div class="cdkey-detail-records">
              <div
                v-for="(record, index) in detailVisibleRecords"
                :key="record.recordKey || `${record.tradeNo}-${index}`"
                class="cdkey-detail-record"
              >
                <div class="cdkey-detail-record__header">
                  <span>
                    批次 {{ index + 1 }}
                    {{
                      Number(record.successCount || 0) > 1
                        ? ` · ${Number(record.successCount || 0)}次`
                        : ""
                    }}
                  </span>
                  <el-tag
                    size="small"
                    :type="
                      record.paymentResult?.confirmedSuccess
                        ? 'success'
                        : 'warning'
                    "
                  >
                    {{
                      record.paymentResult?.confirmedSuccess
                        ? "已确认成功"
                        : "待核实"
                    }}
                  </el-tag>
                </div>
                <div class="cdkey-detail-record__grid">
                  <div class="cdkey-detail-record__item">
                    <span class="cdkey-detail-record__label">存证时间</span>
                    <span class="cdkey-detail-record__value">
                      {{ record.savedAt || "—" }}
                    </span>
                  </div>
                  <div class="cdkey-detail-record__item">
                    <span class="cdkey-detail-record__label">订单号</span>
                    <span
                      class="cdkey-detail-record__value cdkey-detail-summary__value--mono"
                    >
                      {{
                        formatAfterSalesIdSummary(
                          record.orderNo,
                          record.orderNos,
                        )
                      }}
                    </span>
                  </div>
                  <div class="cdkey-detail-record__item">
                    <span class="cdkey-detail-record__label">tradeNo</span>
                    <span
                      class="cdkey-detail-record__value cdkey-detail-summary__value--mono"
                    >
                      {{
                        formatAfterSalesIdSummary(
                          record.tradeNo,
                          record.tradeNos,
                        )
                      }}
                    </span>
                  </div>
                  <div class="cdkey-detail-record__item">
                    <span class="cdkey-detail-record__label">消耗钻石</span>
                    <span class="cdkey-detail-record__value">
                      {{ record.consumedDiamond ?? 0 }}
                    </span>
                  </div>
                </div>
                <details class="cdkey-detail-record__extra">
                  <summary class="cdkey-detail-record__json-summary">
                    查看更多明细
                  </summary>
                  <div class="cdkey-detail-record__grid">
                    <div class="cdkey-detail-record__item">
                      <span class="cdkey-detail-record__label">会话号</span>
                      <span
                        class="cdkey-detail-record__value cdkey-detail-summary__value--mono"
                      >
                        {{ record.sessionId || "—" }}
                      </span>
                    </div>
                    <div class="cdkey-detail-record__item">
                      <span class="cdkey-detail-record__label">提交方式</span>
                      <span class="cdkey-detail-record__value">
                        {{ formatAfterSalesSubmitSource(record) }}
                      </span>
                    </div>
                    <div class="cdkey-detail-record__item">
                      <span class="cdkey-detail-record__label">下单详情</span>
                      <span class="cdkey-detail-record__value">
                        {{ formatAfterSalesRequestDetail(record) }}
                      </span>
                    </div>
                    <div class="cdkey-detail-record__item">
                      <span class="cdkey-detail-record__label">扫码返回</span>
                      <span class="cdkey-detail-record__value">
                        {{ record.paymentResult?.scanResult?.message || "—" }}
                      </span>
                    </div>
                  </div>
                </details>
                <details class="cdkey-detail-record__json-block">
                  <summary class="cdkey-detail-record__json-summary">
                    查看成功 JSON ·
                    {{ formatAfterSalesJsonSummary(record) }}（{{
                      Math.max(1, Number(record.successCount || 0))
                    }}次）
                  </summary>
                  <pre class="cdkey-detail-json cdkey-detail-record__json">{{
                    formatAfterSalesSuccessJson(record)
                  }}</pre>
                </details>
              </div>
            </div>
            <div
              v-if="detailRecords.length > DETAIL_RECORDS_PREVIEW_COUNT"
              class="cdkey-detail-records__actions"
            >
              <el-button
                size="small"
                text
                type="primary"
                @click="detailRecordsExpanded = !detailRecordsExpanded"
              >
                {{
                  detailRecordsExpanded
                    ? `收起（共 ${detailRecords.length} 批）`
                    : `查看更多（已展示 ${detailVisibleRecords.length} / 共 ${detailRecords.length} 批）`
                }}
              </el-button>
            </div>
          </div>

          <div class="cdkey-detail-section">
            <div class="cdkey-detail-section__header">
              <div class="cdkey-detail-section__title">
                最近一次原始支付 JSON
              </div>
              <el-space wrap>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :disabled="!detailLatestRecord"
                  @click="copyLatestTradeAndOrder"
                >
                  复制 tradeNo / orderNo
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  plain
                  :disabled="!detailRow"
                  @click="exportCurrentAfterSalesJson"
                >
                  导出售后 JSON
                </el-button>
              </el-space>
            </div>
            <details class="cdkey-detail-json-block">
              <summary class="cdkey-detail-record__json-summary">
                展开原始支付 JSON ·
                {{ formatAfterSalesPrimarySummary(detailLatestRecord) }}
              </summary>
              <pre class="cdkey-detail-json">{{
                formatJson(detailLatestPayment)
              }}</pre>
            </details>
          </div>
        </div>
      </template>
    </el-dialog>
  </JudianPageLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { judianApi } from "@/api/judian";
import JudianPageLayout from "@/components/judian/PageLayout.vue";
import { getJudianSectionMeta } from "@/views/judian/shared/page-meta";

const LEGACY_MOCK_STORAGE_KEY = "judian_frontend_mock_state_v1";
const DIAMONDS_PER_DAY = 5;
const DETAIL_RECORDS_PREVIEW_COUNT = 1;
const specOptions = [
  { label: "天卡", value: "day", duration: 1 },
  { label: "周卡", value: "week", duration: 7 },
  { label: "月卡", value: "month", duration: 30 },
  { label: "季卡", value: "season", duration: 90 },
  { label: "年卡", value: "year", duration: 365 },
].map((item) => ({
  ...item,
  maxUses: item.duration * DIAMONDS_PER_DAY,
}));

const sectionMeta = getJudianSectionMeta("cdkeys");
const loading = ref(false);
const generating = ref(false);
const accounts = ref([]);
const cdkeys = ref([]);
const lastUpdatedText = ref("");
const exportSpec = ref("month");
const filterAccount = ref(null);
const filterStatus = ref(null);
const searchKeyword = ref("");
const usageDetailVisible = ref(false);
const detailRow = ref(null);
const detailRecordsExpanded = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);

const form = reactive({
  accountId: null,
  duration: 1,
  count: 10,
  maxUses: 5,
  remark: "",
});

const statusMap = {
  unused: { label: "待领取", type: "success" },
  active: { label: "已领取", type: "warning" },
  expired: { label: "已过期", type: "error" },
  void: { label: "已作废", type: "default" },
};

const accountOptions = computed(() =>
  accounts.value
    .filter((item) => item.enabled)
    .map((item) => ({
      label: `${item.displayName}（${item.accountId}）`,
      value: item.accountId,
    })),
);

const filterAccountOptions = computed(() =>
  accounts.value.map((item) => ({
    label: `${item.displayName}（${item.accountId}）`,
    value: item.accountId,
  })),
);

const statusOptions = Object.entries(statusMap).map(([value, item]) => ({
  label: item.label,
  value,
}));

const exportSpecOptions = computed(() =>
  specOptions.map((item) => {
    const count = cdkeys.value.filter(
      (row) => row.status === "unused" && matchesSpecPreset(row, item),
    ).length;
    return {
      label: `${item.label}（${count} 张）`,
      value: item.value,
    };
  }),
);

const activeSpecPreset = computed(() => {
  const duration = Number(form.duration || 0);
  const maxUses = Number(form.maxUses || 0);
  return (
    specOptions.find(
      (item) => item.duration === duration && item.maxUses === maxUses,
    )?.value || null
  );
});

const filteredRows = computed(() =>
  cdkeys.value.filter((item) => {
    if (filterAccount.value && item.accountId !== filterAccount.value)
      return false;
    if (filterStatus.value && item.status !== filterStatus.value) return false;
    if (searchKeyword.value) {
      const keyword = String(searchKeyword.value).trim().toLowerCase();
      if (keyword && !buildCdkeySearchText(item).includes(keyword))
        return false;
    }
    return true;
  }),
);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)),
);

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredRows.value.slice(start, start + pageSize.value);
});

const stats = computed(() => {
  const rows = cdkeys.value || [];
  const available = rows.filter((item) =>
    ["unused", "active"].includes(item.status),
  ).length;
  const invalid = rows.filter((item) =>
    ["expired", "void"].includes(item.status),
  ).length;
  const boundAccounts = new Set(
    rows.map((item) => item.accountId).filter(Boolean),
  ).size;

  return [
    {
      label: "卡密总数",
      value: String(rows.length),
      help: "当前数据库中的聚点卡密库存数量",
    },
    {
      label: "可用卡密",
      value: String(available),
      help: "待领取或已领取状态的真实卡密数量",
    },
    {
      label: "失效卡密",
      value: String(invalid),
      help: "已过期或已作废、建议清理的真实卡密",
    },
    {
      label: "绑定账号",
      value: String(boundAccounts),
      help: "当前卡密已经覆盖到的聚点账号数量",
    },
  ];
});

function cleanupLegacyMockStorage() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LEGACY_MOCK_STORAGE_KEY);
}

function extractErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "请求失败，请稍后重试"
  );
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function resolveAccountName(accountId) {
  const target = accounts.value.find((item) => item.accountId === accountId);
  return target
    ? `${target.displayName}（${target.accountId}）`
    : accountId || "—";
}

function resolveRedeemUrl(code) {
  const baseOrigin =
    typeof window !== "undefined" ? window.location.origin : "";
  return `${baseOrigin}/judian/redeem?code=${encodeURIComponent(code)}`;
}

function resolveSpecLabel(duration) {
  const matched = specOptions.find(
    (item) => item.duration === Number(duration || 0),
  );
  return matched?.label || "";
}

function resolveDurationText(duration) {
  const specLabel = resolveSpecLabel(duration);
  return specLabel ? `${specLabel} · ${duration} 天` : `${duration} 天`;
}

function resolveStatusType(status) {
  return statusMap[status]?.type === "default"
    ? "info"
    : statusMap[status]?.type || "info";
}

function matchesSpecPreset(row, spec) {
  return (
    Number(row?.duration || 0) === Number(spec?.duration || 0) &&
    Number(row?.maxUses || 0) === Number(spec?.maxUses || 0)
  );
}

function calculateMaxUsesByDuration(duration) {
  return Math.max(0, Number(duration || 0)) * DIAMONDS_PER_DAY;
}

function applySpecPreset(item) {
  form.duration = item.duration;
  form.maxUses = item.maxUses;
}

function handleDurationChange(value) {
  const duration = Math.max(1, Number(value || 1));
  form.duration = duration;
  form.maxUses = calculateMaxUsesByDuration(duration);
}

function resolveUsageProgress(row) {
  const maxUses = Math.max(0, Number(row.maxUses || 0));
  const used = Math.max(0, Number(row.useCount || 0));
  if (maxUses <= 0) {
    return {
      unlimited: true,
      summary: `已使用 ${used} 钻`,
      meta: "总额度：不限",
    };
  }
  const remaining = Math.max(0, maxUses - used);
  const percentage = Math.max(
    0,
    Math.min(100, Math.round((used / maxUses) * 100)),
  );
  return {
    unlimited: false,
    percentage,
    summary: `${used} / ${maxUses} 钻`,
    meta: `剩余 ${remaining} 钻`,
    status:
      percentage >= 100
        ? "exception"
        : percentage >= 80
          ? "warning"
          : "success",
  };
}

function normalizeSearchText(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function getAfterSalesBatchId(record) {
  return (
    record?.batchId ||
    record?.batchContext?.batchId ||
    record?.paymentResult?.cdkeyInfo?.batchId ||
    ""
  );
}

function resolveAfterSalesAggregateKey(record, index) {
  const detail = record?.requestDetail || {};
  const batchId = getAfterSalesBatchId(record);
  if (batchId) {
    return `batch:${batchId}`;
  }

  const mode = String(detail.mode || "")
    .trim()
    .toLowerCase();
  const itemIndex = Number(detail.itemIndex || 0);
  if (
    itemIndex > 0 &&
    (mode === "script_batch_order" || mode === "item_batch_order")
  ) {
    return [
      "session-batch",
      record?.sessionId || "",
      record?.savedAt || "",
      detail.countPreset || "",
      detail.packageType || "",
      detail.vipId || "",
      detail.count || "",
    ].join(":");
  }

  return `single:${record?.recordKey || record?.tradeNo || record?.orderNo || index}`;
}

function aggregateAfterSalesRecords(records) {
  const normalizedRecords = Array.isArray(records)
    ? [...records].reverse()
    : [];
  const aggregated = [];
  const grouped = new Map();

  normalizedRecords.forEach((record, index) => {
    const detail =
      record?.requestDetail || record?.paymentResult?.requestDetail || {};
    const batchContext =
      record?.batchContext || record?.paymentResult?.batchContext || {};
    const paymentResult = record?.paymentResult || null;
    const key = resolveAfterSalesAggregateKey(
      {
        ...record,
        requestDetail: detail,
        batchContext,
        paymentResult,
      },
      index,
    );

    if (!grouped.has(key)) {
      const initialRecord = {
        ...record,
        requestDetail: Object.keys(batchContext).length ? batchContext : detail,
        batchContext,
        paymentResult,
        batchId: getAfterSalesBatchId(record),
        successCount: 1,
        successRecords: paymentResult ? [paymentResult] : [],
        tradeNos: record?.tradeNo ? [record.tradeNo] : [],
        orderNos: record?.orderNo ? [record.orderNo] : [],
      };
      grouped.set(key, initialRecord);
      aggregated.push(initialRecord);
      return;
    }

    const current = grouped.get(key);
    current.successCount += 1;
    current.consumedDiamond =
      Number(current.consumedDiamond || 0) +
      Number(record?.consumedDiamond || 0);
    if (paymentResult) {
      current.successRecords.push(paymentResult);
      current.paymentResult = current.paymentResult || paymentResult;
    }
    if (record?.tradeNo && !current.tradeNos.includes(record.tradeNo)) {
      current.tradeNos.push(record.tradeNo);
    }
    if (record?.orderNo && !current.orderNos.includes(record.orderNo)) {
      current.orderNos.push(record.orderNo);
    }
  });

  return aggregated;
}

function extractAfterSalesRecords(row) {
  const records = Array.isArray(row?.afterSalesRecords)
    ? row.afterSalesRecords
    : [];
  if (records.length) {
    return aggregateAfterSalesRecords(records);
  }
  if (row?.latestSuccessPayment) {
    return [
      {
        recordKey:
          row.latestSuccessPayment.tradeNo ||
          row.latestSuccessPayment.orderNo ||
          row.code ||
          "",
        savedAt: row.latestSuccessPaymentAt || "",
        sessionId: row.latestSuccessPayment?.cdkeyInfo?.sessionId || "",
        tradeNo: row.latestSuccessPayment.tradeNo || "",
        orderNo: row.latestSuccessPayment.orderNo || "",
        consumedDiamond: Number(row.latestSuccessPayment.consumedDiamond || 0),
        paymentResult: row.latestSuccessPayment,
        successCount: 1,
        successRecords: [row.latestSuccessPayment],
        tradeNos: row.latestSuccessPayment.tradeNo
          ? [row.latestSuccessPayment.tradeNo]
          : [],
        orderNos: row.latestSuccessPayment.orderNo
          ? [row.latestSuccessPayment.orderNo]
          : [],
      },
    ];
  }
  return [];
}

function buildCdkeySearchText(row) {
  const records = extractAfterSalesRecords(row);
  const recordTexts = records.flatMap((record) => [
    record?.recordKey,
    record?.savedAt,
    record?.sessionId,
    record?.tradeNo,
    record?.orderNo,
    record?.paymentResult?.scanResult?.message,
    record?.paymentResult?.remoteUser?.account,
    record?.paymentResult?.remoteUser?.nickName,
    record?.submitSourceLabel,
    record?.requestDetail?.mode,
    record?.requestDetail?.countPreset,
    record?.requestDetail?.count,
    record?.requestDetail?.itemIndex,
  ]);
  return [
    row?.code,
    row?.remark,
    row?.accountId,
    row?.latestOrderId,
    row?.latestSessionId,
    row?.latestSuccessPaymentAt,
    ...recordTexts,
  ]
    .map(normalizeSearchText)
    .filter(Boolean)
    .join(" ");
}

const afterSalesSourceLabelMap = {
  manual: "手动提交",
  camera_scan: "扫码识别",
  image_upload: "图片上传",
  paste_text: "粘贴文本",
  clipboard_image: "剪贴板图片",
  clipboard_text: "剪贴板文本",
  batch_items: "批量下单",
  batch_script: "批量脚本",
};

const batchCountPresetLabelMap = {
  day: "天卡",
  week: "周卡",
  month: "月卡",
  quarter: "季卡",
  year: "年卡",
  custom: "自定义",
};

function getAfterSalesRequestDetail(record) {
  return record?.requestDetail || record?.paymentResult?.requestDetail || {};
}

function formatAfterSalesSubmitSource(record) {
  const detail = getAfterSalesRequestDetail(record);
  const source =
    record?.submitSource ||
    record?.paymentResult?.submitSource ||
    detail?.submitSource ||
    "";
  return (
    record?.submitSourceLabel ||
    record?.paymentResult?.submitSourceLabel ||
    afterSalesSourceLabelMap[source] ||
    "—"
  );
}

function formatBatchCountPreset(value) {
  const key = String(value || "")
    .trim()
    .toLowerCase();
  return batchCountPresetLabelMap[key] || key || "";
}

function formatAfterSalesPlanLabel(record) {
  const detail = getAfterSalesRequestDetail(record);
  const preset = String(detail.countPreset || "")
    .trim()
    .toLowerCase();
  const count = Number(detail.count || 0);
  const packageType = String(detail.packageType || "")
    .trim()
    .toLowerCase();

  if (preset === "custom" && count > 0) {
    return `${count}天`;
  }

  if (preset) {
    return formatBatchCountPreset(preset);
  }

  if (packageType) {
    return formatBatchCountPreset(packageType);
  }

  return "";
}

function formatAfterSalesRequestDetail(record) {
  const detail = getAfterSalesRequestDetail(record);
  if (!detail || typeof detail !== "object") {
    return "—";
  }
  const parts = [];
  const mode = String(detail.mode || "")
    .trim()
    .toLowerCase();
  if (mode === "script_batch_order") {
    parts.push("批量脚本");
  } else if (mode === "item_batch_order") {
    parts.push("批量逐单");
  } else if (mode === "single_unlock") {
    parts.push("普通下单");
  }

  const planLabel = formatAfterSalesPlanLabel(record);
  if (planLabel) {
    parts.push(planLabel);
  }

  const successCount = Number(record?.successCount || 0);
  if (successCount > 1) {
    parts.push(`${successCount}次`);
  } else {
    const itemIndex = Number(detail.itemIndex || 0);
    if (itemIndex > 0) {
      parts.push(`第 ${itemIndex} 单`);
    }
  }

  if (detail.vipId) {
    parts.push(`VIP ${detail.vipId}`);
  }

  return parts.join(" · ") || "—";
}

function formatAfterSalesSuccessJson(record) {
  if (
    Array.isArray(record?.successRecords) &&
    record.successRecords.length > 1
  ) {
    return formatJson({
      successCount: Number(
        record.successCount || record.successRecords.length || 0,
      ),
      consumedDiamond: Number(record.consumedDiamond || 0),
      tradeNos: record.tradeNos || [],
      orderNos: record.orderNos || [],
      records: record.successRecords,
    });
  }
  return formatJson(
    record?.paymentResult || record?.successRecords?.[0] || record || null,
  );
}

function formatAfterSalesIdSummary(primaryValue, values) {
  const normalizedValues = Array.isArray(values)
    ? values.map((item) => String(item || "").trim()).filter(Boolean)
    : [];
  const firstValue = String(primaryValue || normalizedValues[0] || "").trim();
  if (!firstValue) {
    return "—";
  }
  if (normalizedValues.length <= 1) {
    return firstValue;
  }
  return `${firstValue} 等 ${normalizedValues.length} 个`;
}

function formatAfterSalesJsonSummary(record) {
  const tradeText = formatAfterSalesIdSummary(
    record?.tradeNo,
    record?.tradeNos,
  );
  const orderText = formatAfterSalesIdSummary(
    record?.orderNo,
    record?.orderNos,
  );
  if (tradeText === "—" && orderText === "—") {
    return "暂无编号";
  }
  if (tradeText === "—") {
    return `orderNo ${orderText}`;
  }
  if (orderText === "—") {
    return `tradeNo ${tradeText}`;
  }
  return `tradeNo ${tradeText} / orderNo ${orderText}`;
}

function formatAfterSalesPrimarySummary(record) {
  const tradeText = formatAfterSalesIdSummary(
    record?.tradeNo,
    record?.tradeNos,
  );
  if (tradeText !== "—") {
    return `tradeNo ${tradeText}`;
  }
  const orderText = formatAfterSalesIdSummary(
    record?.orderNo,
    record?.orderNos,
  );
  if (orderText !== "—") {
    return `orderNo ${orderText}`;
  }
  return "暂无编号";
}

const detailRecords = computed(() => extractAfterSalesRecords(detailRow.value));
const detailVisibleRecords = computed(() =>
  detailRecordsExpanded.value
    ? detailRecords.value
    : detailRecords.value.slice(0, DETAIL_RECORDS_PREVIEW_COUNT),
);

const detailTotalSuccessCount = computed(() =>
  detailRecords.value.reduce(
    (total, record) => total + Math.max(1, Number(record?.successCount || 0)),
    0,
  ),
);

const detailLatestPayment = computed(
  () =>
    detailRow.value?.latestSuccessPayment ||
    detailRecords.value[0]?.paymentResult ||
    null,
);

const detailLatestRecord = computed(() => detailRecords.value[0] || null);

watch([filterAccount, filterStatus, searchKeyword, pageSize], () => {
  currentPage.value = 1;
});

watch(
  () => filteredRows.value.length,
  (length) => {
    const nextTotalPages = Math.max(1, Math.ceil(length / pageSize.value));
    if (currentPage.value > nextTotalPages) {
      currentPage.value = nextTotalPages;
    }
  },
);

watch(detailRow, () => {
  detailRecordsExpanded.value = false;
});

function formatJson(value) {
  if (!value) {
    return "暂无数据";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function copyLatestTradeAndOrder() {
  const record = detailLatestRecord.value;
  if (!record) {
    ElMessage.warning("当前没有可复制的售后记录");
    return;
  }
  const tradeNos =
    Array.isArray(record.tradeNos) && record.tradeNos.length
      ? record.tradeNos
      : [record.tradeNo || "—"];
  const orderNos =
    Array.isArray(record.orderNos) && record.orderNos.length
      ? record.orderNos
      : [record.orderNo || "—"];
  const text = [
    `tradeNo: ${tradeNos.join(", ")}`,
    `orderNo: ${orderNos.join(", ")}`,
  ].join("\n");
  await copyText(text);
  ElMessage.success("tradeNo / orderNo 已复制");
}

function buildAfterSalesExportFilename(row) {
  const code = String(row?.code || "unknown").trim() || "unknown";
  const dateText = new Date().toLocaleDateString("zh-CN").replace(/\//g, "-");
  return `聚点卡密售后记录_${code}_${dateText}.json`;
}

function exportCurrentAfterSalesJson() {
  if (!detailRow.value) {
    ElMessage.warning("当前没有可导出的卡密记录");
    return;
  }
  const exportPayload = {
    code: detailRow.value.code || "",
    accountId: detailRow.value.accountId || "",
    latestOrderId: detailRow.value.latestOrderId || "",
    latestSessionId: detailRow.value.latestSessionId || "",
    latestSuccessPaymentAt: detailRow.value.latestSuccessPaymentAt || "",
    latestSuccessPayment: detailRow.value.latestSuccessPayment || null,
    afterSalesRecords: detailRecords.value,
  };
  downloadTextFile(
    `${formatJson(exportPayload)}\n`,
    buildAfterSalesExportFilename(detailRow.value),
  );
  ElMessage.success("当前卡密售后 JSON 已导出");
}

function buildExportFilename(spec) {
  const dateText = new Date().toLocaleDateString("zh-CN").replace(/\//g, "-");
  return `聚点未使用卡密_${spec.label}_${spec.duration}天_${dateText}.txt`;
}

function buildRedeemExportFilename(spec) {
  const dateText = new Date().toLocaleDateString("zh-CN").replace(/\//g, "-");
  return `聚点访问卡密_${spec.label}_${spec.duration}天_${dateText}.txt`;
}

function getUnusedRowsBySpec() {
  const spec = specOptions.find((item) => item.value === exportSpec.value);
  if (!spec) {
    ElMessage.warning("请选择要导出的规格");
    return null;
  }
  const rows = cdkeys.value.filter(
    (row) => row.status === "unused" && matchesSpecPreset(row, spec),
  );
  if (!rows.length) {
    ElMessage.warning(`暂无可导出的${spec.label}未使用卡密`);
    return null;
  }
  return { spec, rows };
}

function resetForm() {
  form.accountId = accountOptions.value[0]?.value || null;
  form.duration = 1;
  form.count = 10;
  form.maxUses = 5;
  form.remark = "";
}

async function loadPage() {
  loading.value = true;
  try {
    cleanupLegacyMockStorage();
    const [accountsResponse, cdkeysResponse] = await Promise.all([
      judianApi.listAccounts(),
      judianApi.listCdKeys(),
    ]);
    accounts.value = Array.isArray(accountsResponse?.data?.items)
      ? accountsResponse.data.items
      : [];
    cdkeys.value = Array.isArray(cdkeysResponse?.data?.items)
      ? cdkeysResponse.data.items
      : [];
    const latestCandidates = [
      cdkeys.value[0]?.updatedAt,
      cdkeys.value[0]?.createdAt,
      accounts.value[0]?.updatedAt,
      accounts.value[0]?.lastLoginAt,
    ]
      .filter(Boolean)
      .sort();
    lastUpdatedText.value = latestCandidates.at(-1) || "暂无数据";
    if (!form.accountId && accountOptions.value.length) {
      form.accountId = accountOptions.value[0].value;
    }
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  } finally {
    loading.value = false;
  }
}

async function handleGenerate() {
  if (!form.accountId) {
    ElMessage.warning("请先选择绑定账号");
    return;
  }
  generating.value = true;
  try {
    const { data } = await judianApi.generateCdKeys({
      accountId: form.accountId,
      duration: form.duration,
      count: form.count,
      maxUses: form.maxUses,
      remark: form.remark,
    });
    await loadPage();
    resetForm();
    ElMessage.success(data?.message || `已生成 ${data?.total || 0} 张聚点卡密`);
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  } finally {
    generating.value = false;
  }
}

function handleExportUnusedCodesBySpec() {
  const result = getUnusedRowsBySpec();
  if (!result) {
    return;
  }
  const { spec, rows } = result;
  const content = rows
    .map((row) => row.code)
    .filter(Boolean)
    .join("\n");
  downloadTextFile(content, buildExportFilename(spec));
  ElMessage.success(`已导出 ${rows.length} 张${spec.label}原卡密`);
}

function handleExportUnusedRedeemUrlsBySpec() {
  const result = getUnusedRowsBySpec();
  if (!result) {
    return;
  }
  const { spec, rows } = result;
  const content = rows
    .map((row) => row.code)
    .filter(Boolean)
    .map((code) => resolveRedeemUrl(code))
    .join("\n");
  downloadTextFile(content, buildRedeemExportFilename(spec));
  ElMessage.success(`已导出 ${rows.length} 条${spec.label}访问卡密链接`);
}

async function copyCode(code) {
  await copyText(code);
  ElMessage.success("卡密已复制");
}

async function copyRedeemUrl(code) {
  await copyText(resolveRedeemUrl(code));
  ElMessage.success("兑换链接已复制");
}

async function previewRedeem(code) {
  window.open(resolveRedeemUrl(code), "_blank", "noopener");
}

function openUsageDetail(row) {
  detailRow.value = row;
  detailRecordsExpanded.value = false;
  usageDetailVisible.value = true;
}

async function handleVoid(row) {
  try {
    await judianApi.updateCdKey(row.id, { status: "void" });
    await loadPage();
    ElMessage.success("卡密已作废");
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

async function confirmVoid(row) {
  try {
    await ElMessageBox.confirm(`确认作废卡密 ${row.code}？`, "作废确认", {
      type: "warning",
    });
    await handleVoid(row);
  } catch {
    // User cancelled.
  }
}

async function handleCleanInactive() {
  try {
    const { data } = await judianApi.cleanInactiveCdKeys();
    await loadPage();
    ElMessage.success(
      data?.message || `已清理 ${data?.removed || 0} 张失效卡密`,
    );
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

async function confirmCleanInactive() {
  try {
    await ElMessageBox.confirm(
      "确认要清理所有已过期或已作废的真实卡密吗？",
      "清理确认",
      {
        type: "warning",
      },
    );
    await handleCleanInactive();
  } catch {
    // User cancelled.
  }
}

onMounted(loadPage);
</script>

<style scoped>
.cdkey-generate-card,
.cdkey-table-card {
  border-radius: 12px;
}

.cdkey-card-alert {
  margin-bottom: 10px;
}

.cdkey-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cdkey-generate-card :deep(.el-card__body),
.cdkey-table-card :deep(.el-card__body) {
  padding-top: 12px;
}

.cdkey-generate-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.cdkey-generate-form :deep(.el-form-item__label) {
  margin-bottom: 4px;
}

.cdkey-generate-grid {
  display: grid;
  grid-template-columns:
    minmax(260px, 2.3fr) repeat(3, minmax(92px, 0.82fr))
    minmax(180px, 1.2fr);
  column-gap: 10px;
  row-gap: 6px;
  align-items: end;
}

.cdkey-generate-field {
  min-width: 0;
}

.cdkey-generate-field--spec {
  grid-column: 1 / -1;
}

.cdkey-spec-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cdkey-spec-picker__hint {
  color: #64748b;
  font-size: 11px;
  line-height: 1.4;
}

.cdkey-generate-actions {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.cdkey-generate-actions__inner {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.cdkey-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
}

.cdkey-table :deep(.el-table__cell) {
  padding-top: 8px;
  padding-bottom: 8px;
}

.cdkey-code {
  font-family: monospace;
  font-weight: 600;
}

.cdkey-usage-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cdkey-usage-progress__summary {
  font-weight: 600;
  font-size: 13px;
}

.cdkey-usage-progress__meta {
  color: #64748b;
  font-size: 11px;
  line-height: 1.4;
}

.cdkey-detail-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.cdkey-detail-summary__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
}

.cdkey-detail-summary__label,
.cdkey-detail-record__label {
  font-size: 12px;
  color: #64748b;
}

.cdkey-detail-summary__value,
.cdkey-detail-record__value {
  font-size: 13px;
  color: #111827;
  line-height: 1.5;
  word-break: break-all;
}

.cdkey-detail-summary__value--mono {
  font-family: monospace;
}

.cdkey-detail-empty {
  margin-bottom: 10px;
}

.cdkey-detail-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cdkey-detail-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cdkey-detail-section__title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.cdkey-detail-section__meta {
  font-size: 12px;
  color: #64748b;
}

.cdkey-detail-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.cdkey-detail-records {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cdkey-detail-records__actions {
  display: flex;
  justify-content: center;
  margin-top: 2px;
  padding-top: 2px;
}

.cdkey-detail-record {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}

.cdkey-detail-record__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: 600;
}

.cdkey-detail-record__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.cdkey-detail-record__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cdkey-detail-record__extra {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
}

.cdkey-detail-record__json-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
}

.cdkey-detail-record__json-summary {
  cursor: pointer;
  color: #2563eb;
  font-size: 12px;
  user-select: none;
}

.cdkey-detail-record__json {
  max-height: 240px;
}

.cdkey-detail-json-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cdkey-detail-json {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  max-height: 420px;
  white-space: pre-wrap;
  word-break: break-word;
}

.pagination-wrap {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.pagination-text {
  font-size: 12px;
  color: #64748b;
}

.cdkey-generate-card :deep(.el-button),
.cdkey-table-card :deep(.el-button) {
  min-height: 34px;
}

.cdkey-generate-card :deep(.el-input-number),
.cdkey-generate-card :deep(.el-select),
.cdkey-generate-card :deep(.el-input) {
  width: 100%;
}

@media (max-width: 1400px) {
  .cdkey-generate-grid {
    grid-template-columns:
      minmax(220px, 1.9fr) repeat(2, minmax(96px, 0.95fr)) minmax(96px, 0.95fr)
      minmax(160px, 1.15fr);
  }
}

@media (max-width: 1100px) {
  .cdkey-generate-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cdkey-generate-field--account,
  .cdkey-generate-field--remark {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .cdkey-generate-card,
  .cdkey-table-card {
    border-radius: 10px;
  }

  .cdkey-card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .cdkey-generate-card :deep(.el-card__body),
  .cdkey-table-card :deep(.el-card__body) {
    padding-top: 10px;
  }

  .cdkey-generate-grid {
    grid-template-columns: 1fr;
    row-gap: 4px;
  }

  .cdkey-generate-field--account,
  .cdkey-generate-field--remark {
    grid-column: auto;
  }

  .cdkey-generate-actions,
  .cdkey-toolbar {
    justify-content: flex-start;
  }

  .cdkey-generate-actions__inner {
    width: 100%;
    gap: 8px;
  }

  .cdkey-generate-actions__inner :deep(.el-button),
  .cdkey-toolbar :deep(.el-button) {
    min-height: 34px;
    padding: 0 10px;
  }

  .cdkey-toolbar {
    width: 100%;
    gap: 6px;
  }

  .pagination-wrap {
    align-items: flex-start;
  }

  .cdkey-detail-summary,
  .cdkey-detail-record__grid {
    grid-template-columns: 1fr;
  }

  .cdkey-toolbar :deep(.el-select),
  .cdkey-toolbar :deep(.el-input),
  .cdkey-toolbar :deep(.el-button),
  .cdkey-generate-actions__inner :deep(.el-button) {
    width: 100%;
  }

  .cdkey-table :deep(.el-table__cell) {
    padding-top: 7px;
    padding-bottom: 7px;
    font-size: 12px;
  }

  .cdkey-usage-progress {
    gap: 4px;
  }

  .cdkey-usage-progress__summary {
    font-size: 13px;
  }

  .cdkey-usage-progress__meta,
  .cdkey-spec-picker__hint {
    font-size: 11px;
  }
}
</style>
