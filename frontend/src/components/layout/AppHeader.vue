<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Compass, Expand, Fold, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  collapsed: boolean
  isMobile: boolean
}>()

const emit = defineEmits<{
  toggleSidebar: []
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const pageTitle = computed(() => String(route.meta.title || '闲鱼管理系统'))
const pageDescription = computed(() => String(route.meta.description || 'Vue 3 + Element Plus 管理台'))
const layoutStateLabel = computed(() => {
  if (props.isMobile) return '移动端导航'
  return props.collapsed ? '紧凑导航' : '展开导航'
})
const currentRole = computed(() => (authStore.user?.is_admin ? '管理员' : '普通用户'))
const userInitial = computed(() => String(authStore.user?.username || 'U').slice(0, 1).toUpperCase())

const handleLogout = async () => {
  authStore.clearAuth()
  ElMessage.success('已退出登录')
  await router.replace('/login')
}
</script>

<template>
  <header class="app-header">
    <div class="header-main">
      <div class="header-left">
        <el-button
          class="sidebar-trigger"
          :icon="props.collapsed && !props.isMobile ? Expand : Fold"
          circle
          @click="emit('toggleSidebar')"
        />
        <div class="header-copy">
          <div class="header-meta">
            <span class="meta-badge">
              <el-icon><Compass /></el-icon>
              {{ layoutStateLabel }}
            </span>
            <span class="meta-divider" />
            <span class="meta-text">当前页面</span>
          </div>
          <div class="header-title-row">
            <div class="header-title">{{ pageTitle }}</div>
            <el-tag effect="plain" class="header-inline-tag">{{ currentRole }}</el-tag>
          </div>
          <div class="header-description">{{ pageDescription }}</div>
        </div>
      </div>

      <div class="header-right">
        <div class="header-status-card">
          <div class="status-label">系统状态</div>
          <div class="status-value">迁移进行中</div>
        </div>
        <div class="user-card">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-meta">
            <div class="user-name">{{ authStore.user?.username || '未命名用户' }}</div>
            <div class="user-role">{{ currentRole }}</div>
          </div>
        </div>
        <el-button type="danger" plain :icon="SwitchButton" @click="handleLogout">退出登录</el-button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 20px 24px 0;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
  box-shadow:
    0 24px 48px -34px rgba(15, 23, 42, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.sidebar-trigger {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.92);
  box-shadow: 0 10px 18px -18px rgba(15, 23, 42, 0.8);
}

.header-copy {
  min-width: 0;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 12px;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-weight: 600;
}

.meta-divider {
  width: 1px;
  height: 14px;
  background: rgba(148, 163, 184, 0.32);
}

.meta-text {
  white-space: nowrap;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.header-title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.header-description {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.header-status-card {
  min-width: 118px;
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
}

.status-label {
  color: #64748b;
  font-size: 12px;
}

.status-value {
  margin-top: 4px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 700;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 8px 10px 8px 8px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #eff6ff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 12px 24px -18px rgba(37, 99, 235, 0.9);
}

.user-meta {
  min-width: 88px;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.user-role {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.header-inline-tag {
  border-radius: 999px;
}

@media (max-width: 960px) {
  .app-header {
    padding: 16px 16px 0;
  }

  .header-main {
    padding: 14px 16px;
  }

  .header-meta {
    flex-wrap: wrap;
  }

  .header-title {
    font-size: 20px;
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }

  .header-status-card {
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .header-main {
    border-radius: 20px;
  }

  .user-card {
    flex: 1;
  }
}
</style>
