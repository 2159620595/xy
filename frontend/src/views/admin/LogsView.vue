<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  CircleCheckFilled,
  Download,
  InfoFilled,
  RefreshRight,
  WarningFilled,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  clearSystemLogs,
  exportLogs,
  getSystemLogs,
  type SystemLog,
} from "@/api/admin";

const limitOptions = [
  { value: 50, label: "50 条" },
  { value: 100, label: "100 条" },
  { value: 200, label: "200 条" },
  { value: 500, label: "500 条" },
];

const loading = ref(true);
const exporting = ref(false);
const logs = ref<SystemLog[]>([]);
const levelFilter = ref("");
const moduleFilter = ref("");
const limit = ref(100);

const filteredLogs = computed(() =>
  logs.value.filter((log) => {
    const matchesLevel = !levelFilter.value || log.level === levelFilter.value;
    const matchesModule =
      !moduleFilter.value || log.module === moduleFilter.value;
    return matchesLevel && matchesModule;
  }),
);
const moduleOptions = computed(() =>
  Array.from(
    new Set(logs.value.map((log) => log.module).filter((value) => !!value)),
  ).sort((left, right) => left.localeCompare(right, "zh-CN")),
);
const errorCount = computed(
  () => logs.value.filter((log) => log.level === "error").length,
);
const warningCount = computed(
  () => logs.value.filter((log) => log.level === "warning").length,
);
const infoCount = computed(
  () => logs.value.filter((log) => log.level === "info").length,
);
const overviewMetrics = computed(() => [
  {
    label: "当前日志",
    value: String(logs.value.length),
    description: "系统日志总量",
    tone: "primary",
  },
  {
    label: "错误",
    value: String(errorCount.value),
    description: "需优先关注的异常日志",
    tone: "danger",
  },
  {
    label: "警告",
    value: String(warningCount.value),
    description: "可能影响功能稳定性的风险提示",
    tone: "warning",
  },
  {
    label: "信息",
    value: String(infoCount.value),
    description: "普通运行状态和流程记录",
    tone: "info",
  },
]);

const loadLogs = async () => {
  loading.value = true;
  try {
    const result = await getSystemLogs({ limit: limit.value });
    logs.value = result.data || [];
  } catch {
    ElMessage.error("加载系统日志失败");
    logs.value = [];
  } finally {
    loading.value = false;
  }
};

const handleExport = async () => {
  if (exporting.value) return;
  exporting.value = true;
  try {
    const { blob, filename } = await exportLogs();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success("日志导出成功");
  } catch {
    ElMessage.error("导出日志失败");
  } finally {
    exporting.value = false;
  }
};

const handleClear = async () => {
  try {
    await ElMessageBox.confirm(
      "确定要清空所有系统日志吗？此操作不可恢复。",
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
    await clearSystemLogs();
    ElMessage.success("日志已清空");
    await loadLogs();
  } catch {
    ElMessage.error("清空失败");
  }
};

const getTagType = (level: SystemLog["level"]) => {
  if (level === "error") return "danger";
  if (level === "warning") return "warning";
  return "info";
};

const formatDateTime = (value: string) => {
  if (!value) return "未知时间";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

onMounted(async () => {
  await loadLogs();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">系统日志</h1>
        <p class="page-description">
          查看系统运行日志，支持按级别过滤、导出和清空。
        </p>
      </div>
      <div class="page-actions">
        <el-button
          :icon="Download"
          :loading="exporting"
          type="primary"
          @click="handleExport"
        >
          导出日志
        </el-button>
        <el-button type="danger" plain @click="handleClear">清空日志</el-button>
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
        <el-icon><InfoFilled /></el-icon>
        <span>筛选条件</span>
      </div>
      <div class="filter-row">
        <div class="filter-tabs">
          <el-tag
            v-for="level in ['', 'info', 'warning', 'error']"
            :key="level || 'all'"
            class="clickable-tag"
            :type="levelFilter === level ? 'primary' : 'info'"
            :effect="levelFilter === level ? 'dark' : 'plain'"
            @click="levelFilter = level"
          >
            {{
              level === ""
                ? "全部"
                : level === "info"
                  ? "信息"
                  : level === "warning"
                    ? "警告"
                    : "错误"
            }}
          </el-tag>
        </div>

        <div class="filter-controls">
          <el-form-item label="模块">
            <el-select
              v-model="moduleFilter"
              clearable
              placeholder="全部模块"
              style="width: 220px"
            >
              <el-option
                v-for="moduleName in moduleOptions"
                :key="moduleName"
                :label="moduleName"
                :value="moduleName"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="显示条数">
            <el-select v-model="limit" style="width: 120px" @change="loadLogs">
              <el-option
                v-for="option in limitOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
        </div>
      </div>
      <div class="filter-summary">
        <el-tag
          v-if="levelFilter"
          :type="getTagType(levelFilter as SystemLog['level'])"
          effect="plain"
        >
          当前过滤：{{
            levelFilter === "error"
              ? "错误"
              : levelFilter === "warning"
                ? "警告"
                : "信息"
          }}
        </el-tag>
        <el-tag v-if="moduleFilter" type="info" effect="plain">
          当前模块：{{ moduleFilter }}
        </el-tag>
        <el-tag type="info" effect="plain"
          >当前展示 {{ filteredLogs.length }} 条</el-tag
        >
        <span class="text-muted">支持按日志级别和模块快速过滤最近系统日志</span>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">
            当前展示 {{ filteredLogs.length }} 条日志
          </div>
          <div class="toolbar-submeta">
            最近日志按级别分层展示，便于快速识别错误和警告
          </div>
        </div>
        <div class="toolbar-tags">
          <el-tag type="info" effect="plain">按文件尾部最近日志读取</el-tag>
          <el-tag
            v-if="levelFilter"
            :type="getTagType(levelFilter as SystemLog['level'])"
            effect="plain"
          >
            当前过滤：{{
              levelFilter === "error"
                ? "错误"
                : levelFilter === "warning"
                  ? "警告"
                  : "信息"
            }}
          </el-tag>
          <el-tag v-if="moduleFilter" type="info" effect="plain">
            模块：{{ moduleFilter }}
          </el-tag>
        </div>
      </div>

      <div v-loading="loading" class="log-list">
        <template v-if="filteredLogs.length">
          <div v-for="log in filteredLogs" :key="log.id" class="log-item">
            <div class="log-head">
              <div class="log-badges">
                <el-tag :type="getTagType(log.level)" effect="plain">
                  {{
                    log.level === "error"
                      ? "错误"
                      : log.level === "warning"
                        ? "警告"
                        : "信息"
                  }}
                </el-tag>
                <el-tag type="info" effect="plain">{{ log.module }}</el-tag>
                <span class="log-time">{{
                  formatDateTime(log.created_at)
                }}</span>
              </div>
              <div class="log-icon">
                <el-icon v-if="log.level === 'error'"
                  ><WarningFilled
                /></el-icon>
                <el-icon v-else-if="log.level === 'warning'"
                  ><InfoFilled
                /></el-icon>
                <el-icon v-else><CircleCheckFilled /></el-icon>
              </div>
            </div>
            <pre class="log-message">{{ log.message }}</pre>
          </div>
        </template>
        <el-empty v-else description="暂无日志记录" />
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

.metric-panel--danger .metric-dot {
  background: #ef4444;
}

.metric-panel--warning .metric-dot {
  background: #f59e0b;
}

.metric-panel--info .metric-dot {
  background: #0ea5e9;
}

.metric-description {
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.filter-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.clickable-tag {
  cursor: pointer;
}

.filter-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-controls {
  display: flex;
  align-items: flex-end;
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

.log-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.log-item {
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: #fff;
}

.log-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.log-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.log-time {
  color: #94a3b8;
  font-size: 12px;
}

.log-icon {
  color: #64748b;
}

.log-message {
  margin: 12px 0 0;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, "SFMono-Regular", monospace;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 768px) {
}
</style>
