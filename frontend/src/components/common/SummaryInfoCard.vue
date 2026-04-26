<script setup lang="ts">
import type { Component } from "vue";

export type SummaryTone =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info";

export interface SummaryInfoItem {
  label: string;
  value: string;
  tone?: SummaryTone;
}

defineProps<{
  title: string;
  icon?: Component;
  items: SummaryInfoItem[];
}>();
</script>

<template>
  <el-card shadow="never" class="summary-info-card">
    <template #header>
      <div class="card-title">
        <el-icon v-if="icon"><component :is="icon" /></el-icon>
        <span>{{ title }}</span>
      </div>
    </template>

    <div class="info-stack">
      <div v-for="item in items" :key="item.label" class="info-row">
        <span class="info-label">{{ item.label }}</span>
        <strong :class="item.tone ? `value-tone--${item.tone}` : ''">
          {{ item.value }}
        </strong>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.summary-info-card {
  display: flex;
  flex-direction: column;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.info-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.82);
}

.info-label {
  color: #64748b;
  font-size: 13px;
}

.info-row strong {
  color: #0f172a;
  text-align: right;
}

.value-tone--primary {
  color: #2563eb;
}

.value-tone--success {
  color: #15803d;
}

.value-tone--warning {
  color: #b45309;
}

.value-tone--danger {
  color: #dc2626;
}

.value-tone--info {
  color: #0369a1;
}

@media (max-width: 768px) {
  .info-row {
    flex-direction: column;
  }

  .info-row strong {
    text-align: left;
  }
}
</style>
