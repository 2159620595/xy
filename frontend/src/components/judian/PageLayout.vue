<template>
  <section class="judian-page-layout">
    <el-card shadow="never" class="judian-hero-card">
      <div class="judian-hero-card__content">
        <div class="judian-hero-card__main">
          <div class="judian-hero-card__eyebrow">聚点联盟</div>
          <div class="judian-hero-card__title-row">
            <h2>{{ title }}</h2>
            <el-tag round type="primary">Element Plus 版</el-tag>
          </div>
          <p>{{ description }}</p>
          <div v-if="lastUpdatedText" class="judian-hero-card__meta">
            最后更新：{{ lastUpdatedText }}
          </div>
        </div>
        <div v-if="$slots.actions" class="judian-hero-card__actions">
          <slot name="actions" />
        </div>
      </div>
    </el-card>

    <div v-if="stats.length" class="judian-stats-grid">
      <el-card
        v-for="item in stats"
        :key="item.label"
        shadow="never"
        class="judian-stat-card"
      >
        <div class="judian-stat-card__label">{{ item.label }}</div>
        <div class="judian-stat-card__value">{{ item.value }}</div>
        <div class="judian-stat-card__help">{{ item.help }}</div>
      </el-card>
    </div>

    <div class="judian-page-layout__content">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
  lastUpdatedText: {
    type: String,
    default: '',
  },
  stats: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.judian-page-layout {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
}

.judian-hero-card {
  background: linear-gradient(135deg, #f8fbff 0%, #f3f6fb 55%, #eef4ff 100%);
  border: 1px solid #e5edf9;
}

.judian-hero-card :deep(.el-card__body),
.judian-stat-card :deep(.el-card__body) {
  padding: 20px;
}

.judian-hero-card__content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.judian-hero-card__main {
  min-width: 0;
}

.judian-hero-card__eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #2563eb;
  margin-bottom: 8px;
}

.judian-hero-card__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.judian-hero-card__title-row h2 {
  font-size: 24px;
  line-height: 1.2;
  color: #111827;
}

.judian-hero-card__main p {
  max-width: 780px;
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
}

.judian-hero-card__meta {
  margin-top: 14px;
  font-size: 12px;
  color: #6b7280;
}

.judian-hero-card__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
}

.judian-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.judian-stat-card {
  border: 1px solid #eef2f7;
}

.judian-page-layout__content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.judian-stat-card__label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 10px;
}

.judian-stat-card__value {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 700;
  color: #111827;
  margin-bottom: 8px;
}

.judian-stat-card__help {
  font-size: 12px;
  line-height: 1.6;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .judian-hero-card__content {
    flex-direction: column;
  }

  .judian-hero-card__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
