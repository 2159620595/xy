<script setup lang="ts">
export type MetricTone =
  | "primary"
  | "success"
  | "info"
  | "warning"
  | "danger"
  | "default";

export interface OverviewMetricItem {
  label: string;
  value: string | number;
  description?: string;
  tone?: MetricTone;
}

defineProps<{
  items: OverviewMetricItem[];
}>();
</script>

<template>
  <section class="metric-grid">
    <el-card
      v-for="item in items"
      :key="item.label"
      shadow="never"
      class="metric-card metric-panel"
      :class="`metric-panel--${item.tone || 'default'}`"
    >
      <div class="metric-panel-top">
        <div class="metric-label">{{ item.label }}</div>
        <span class="metric-dot" />
      </div>
      <div class="metric-value">{{ item.value }}</div>
      <div v-if="item.description" class="metric-description">
        {{ item.description }}
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.metric-panel {
  position: relative;
  overflow: hidden;
}

.metric-panel :deep(.el-card__body) {
  min-height: 96px;
}

.metric-panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.metric-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #cbd5e1;
  flex-shrink: 0;
}

.metric-panel--primary .metric-dot {
  background: #2563eb;
}

.metric-panel--success .metric-dot {
  background: #22c55e;
}

.metric-panel--info .metric-dot {
  background: #0ea5e9;
}

.metric-panel--warning .metric-dot {
  background: #f59e0b;
}

.metric-panel--danger .metric-dot {
  background: #ef4444;
}

.metric-description {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}
</style>
