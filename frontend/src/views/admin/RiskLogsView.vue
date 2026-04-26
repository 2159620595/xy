<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RefreshRight, Warning, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { clearRiskLogs, getRiskLogs, type RiskLog } from "@/api/admin";
import { getAccounts } from "@/api/accounts";
import type { Account } from "@/types";

const loading = ref(true);
const logs = ref<RiskLog[]>([]);
const accounts = ref<Account[]>([]);
const selectedAccount = ref("");
const selectedRiskType = ref("");

const loadAccounts = async () => {
  try {
    accounts.value = await getAccounts();
  } catch {
    accounts.value = [];
  }
};

const loadLogs = async () => {
  loading.value = true;
  try {
    const result = await getRiskLogs({
      cookie_id: selectedAccount.value || undefined,
    });
    logs.value = result.data || [];
  } catch {
    ElMessage.error("加载风控日志失败");
    logs.value = [];
  } finally {
    loading.value = false;
  }
};

const getStatusType = (status: string) => {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  if (status === "processing") return "warning";
  return "info";
};

const getStatusText = (status: string) => {
  if (status === "success") return "成功";
  if (status === "failed") return "失败";
  if (status === "processing") return "处理中";
  return status || "-";
};

const filteredLogs = computed(() =>
  selectedRiskType.value
    ? logs.value.filter((log) => log.risk_type === selectedRiskType.value)
    : logs.value,
);
const riskTypeOptions = computed(() =>
  Array.from(new Set(logs.value.map((log) => log.risk_type).filter(Boolean))),
);
const successCount = computed(
  () =>
    filteredLogs.value.filter((log) => log.processing_status === "success")
      .length,
);
const failedCount = computed(
  () =>
    filteredLogs.value.filter((log) => log.processing_status === "failed")
      .length,
);
const processingCount = computed(
  () =>
    filteredLogs.value.filter((log) => log.processing_status === "processing")
      .length,
);
const activeFilterCount = computed(() => {
  let count = 0;
  if (selectedAccount.value) count += 1;
  if (selectedRiskType.value) count += 1;
  return count;
});
const overviewMetrics = computed(() => [
  {
    label: "当前日志",
    value: String(filteredLogs.value.length),
    description: "筛选后展示的风控日志数量",
    tone: "primary",
  },
  {
    label: "处理成功",
    value: String(successCount.value),
    description: "已完成处理且结果成功",
    tone: "success",
  },
  {
    label: "处理失败",
    value: String(failedCount.value),
    description: "需要重点复盘的失败事件",
    tone: "danger",
  },
  {
    label: "处理中",
    value: String(processingCount.value),
    description: "仍在处理链路中的事件",
    tone: "warning",
  },
]);

const formatDateTime = (value?: string) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const handleClear = async () => {
  try {
    await ElMessageBox.confirm(
      "确定要清空风控日志吗？此操作不可恢复。",
      "清空确认",
      {
        type: "warning",
        confirmButtonText: "清空",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  try {
    const result = await clearRiskLogs(selectedAccount.value || undefined);
    if (result.success) {
      ElMessage.success("日志已清空");
      await loadLogs();
    } else {
      ElMessage.error(result.message || "清空失败");
    }
  } catch {
    ElMessage.error("清空失败");
  }
};

watch(selectedAccount, async () => {
  await loadLogs();
});

onMounted(async () => {
  await Promise.all([loadAccounts(), loadLogs()]);
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">风控日志</h1>
        <p class="page-description">
          查看账号风控事件、处理结果和错误信息，支持按账号筛选。
        </p>
      </div>
      <div class="page-actions">
        <el-button type="danger" plain :icon="Delete" @click="handleClear"
          >清空日志</el-button
        >
        <el-button :icon="RefreshRight" @click="loadLogs">刷新</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <el-card
        v-for="metric in overviewMetrics"
        :key="metric.label"
        shadow="never"
        class="metric-card metric-panel"
        :class="`metric-panel--${metric.tone}`"
      >
        <div class="metric-panel-top">
          <div class="metric-label">{{ metric.label }}</div>
          <span class="metric-dot" />
        </div>
        <div class="metric-value">{{ metric.value }}</div>
        <div class="metric-description">{{ metric.description }}</div>
      </el-card>
    </section>

    <section class="filter-bar">
      <div class="filter-title">
        <el-icon><RefreshRight /></el-icon>
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
        <el-form-item label="风控类型">
          <el-select
            v-model="selectedRiskType"
            clearable
            placeholder="全部类型"
          >
            <el-option label="全部类型" value="" />
            <el-option
              v-for="riskType in riskTypeOptions"
              :key="riskType"
              :label="riskType"
              :value="riskType"
            />
          </el-select>
        </el-form-item>
      </div>
      <div class="filter-summary">
        <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
          已启用 {{ activeFilterCount }} 个筛选
        </el-tag>
        <el-tag type="info" effect="plain"
          >日志总量 {{ logs.length }} 条</el-tag
        >
        <span class="text-muted">支持按账号和风控类型聚焦异常处理链路</span>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">
            当前展示 {{ filteredLogs.length }} / {{ logs.length }} 条风控日志
          </div>
          <div class="toolbar-submeta">
            重点关注失败和处理中事件，便于快速排查异常账号
          </div>
        </div>
        <div class="toolbar-tags">
          <el-tag v-if="selectedAccount" type="primary" effect="plain">
            已按账号过滤
          </el-tag>
          <el-tag v-if="selectedRiskType" type="danger" effect="plain">
            类型：{{ selectedRiskType }}
          </el-tag>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredLogs"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column prop="cookie_id" label="账号 ID" min-width="180" />
        <el-table-column label="风控类型" min-width="120">
          <template #default="{ row }">
            <el-tag type="danger" effect="plain">{{ row.risk_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="message"
          label="事件描述"
          min-width="220"
          show-overflow-tooltip
        />
        <el-table-column
          prop="processing_result"
          label="处理结果"
          min-width="220"
          show-overflow-tooltip
        />
        <el-table-column label="处理状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.processing_status)" effect="plain">
              {{ getStatusText(row.processing_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="error_message"
          label="错误信息"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span>{{ row.error_message || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180">
          <template #default="{ row }">
            <span>{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="180">
          <template #default="{ row }">
            <span>{{ formatDateTime(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无风控日志" />
        </template>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <div class="tip-card">
        <el-icon><Warning /></el-icon>
        <span
          >该页面展示的是管理员视角下的全局风控日志，便于快速定位异常账号与处理链路。</span
        >
      </div>
    </el-card>
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
  gap: 12px;
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

.inline-form :deep(.el-input),
.inline-form :deep(.el-select) {
  width: 220px;
}

.metric-panel {
  position: relative;
  overflow: hidden;
}

.metric-panel::after {
  content: "";
  position: absolute;
  inset: auto -24px -24px auto;
  width: 88px;
  height: 88px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.06);
}

.metric-panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.metric-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #cbd5e1;
}

.metric-panel--primary .metric-dot {
  background: #2563eb;
}

.metric-panel--success .metric-dot {
  background: #22c55e;
}

.metric-panel--danger .metric-dot {
  background: #ef4444;
}

.metric-panel--warning .metric-dot {
  background: #f59e0b;
}

.metric-description {
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.filter-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-tags {
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

.tip-card {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .inline-form :deep(.el-input),
  .inline-form :deep(.el-select) {
    width: 100%;
  }
}
</style>
