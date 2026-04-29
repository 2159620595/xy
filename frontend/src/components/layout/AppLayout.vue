<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Expand, Fold } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import NaiveProviders from '@/components/common/NaiveProviders.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'

const MOBILE_BREAKPOINT = 1024

const route = useRoute()
const collapsed = ref(false)
const isMobile = ref(false)
const mobileSidebarOpen = ref(false)

const sidebarCollapsed = computed(() => (isMobile.value ? false : collapsed.value))

const syncViewport = () => {
  if (typeof window === 'undefined') return

  const nextIsMobile = window.innerWidth < MOBILE_BREAKPOINT
  isMobile.value = nextIsMobile

  if (!nextIsMobile) {
    mobileSidebarOpen.value = false
  }
}

const toggleSidebar = () => {
  if (isMobile.value) {
    mobileSidebarOpen.value = !mobileSidebarOpen.value
    return
  }

  collapsed.value = !collapsed.value
}

const closeMobileSidebar = () => {
  mobileSidebarOpen.value = false
}

watch(
  () => route.fullPath,
  () => {
    if (isMobile.value) {
      closeMobileSidebar()
    }
  },
)

onMounted(() => {
  syncViewport()
  window.addEventListener('resize', syncViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
})
</script>

<template>
  <NaiveProviders>
    <div class="layout-shell">
      <transition name="layout-fade">
        <div
          v-if="isMobile && mobileSidebarOpen"
          class="layout-overlay"
          @click="closeMobileSidebar"
        />
      </transition>

      <div
        class="layout-sidebar"
        :class="{
          collapsed: sidebarCollapsed,
          mobile: isMobile,
          'mobile-open': mobileSidebarOpen,
        }"
      >
        <AppSidebar
          :collapsed="sidebarCollapsed"
          :is-mobile="isMobile"
          :mobile-open="mobileSidebarOpen"
          @navigate="closeMobileSidebar"
        />
      </div>

      <div class="layout-main">
        <el-button
          class="layout-sidebar-trigger"
          :icon="sidebarCollapsed && !isMobile ? Expand : Fold"
          circle
          @click="toggleSidebar"
        />
        <main class="layout-content">
          <div class="content-inner">
            <router-view />
          </div>
        </main>
      </div>
    </div>
  </NaiveProviders>
</template>

<style scoped>
.layout-shell {
  position: relative;
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.12), transparent 28%),
    radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.08), transparent 24%),
    #f4f7fb;
}

.layout-overlay {
  position: fixed;
  inset: 0;
  z-index: 39;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(4px);
}

.layout-sidebar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: 100vh;
  flex: 0 0 auto;
  transition: transform 0.28s ease;
}

.layout-main {
  position: relative;
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.layout-sidebar-trigger {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 30;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 36px -24px rgba(15, 23, 42, 0.5);
}

.layout-content {
  flex: 1;
  padding: 72px 24px 24px;
}

.content-inner {
  width: 100%;
  max-width: 1680px;
  margin: 0 auto;
}

.layout-fade-enter-active,
.layout-fade-leave-active {
  transition: opacity 0.2s ease;
}

.layout-fade-enter-from,
.layout-fade-leave-to {
  opacity: 0;
}

@media (max-width: 1023px) {
  .layout-sidebar-trigger {
    top: 14px;
    left: 14px;
  }

  .layout-sidebar {
    position: fixed;
    left: 0;
    transform: translateX(-100%);
    box-shadow: 0 24px 48px -28px rgba(15, 23, 42, 0.65);
  }

  .layout-sidebar.mobile-open {
    transform: translateX(0);
  }

  .layout-content {
    padding: 68px 16px 16px;
  }
}
</style>
