<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Bell,
  ChatDotRound,
  CollectionTag,
  CreditCard,
  DataBoard,
  Document,
  Goods,
  InfoFilled,
  Monitor,
  Opportunity,
  Setting,
  ShoppingCart,
  SwitchButton,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  collapsed: boolean;
  isMobile: boolean;
  mobileOpen: boolean;
}>();

const emit = defineEmits<{
  navigate: [];
}>();

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activePath = computed(() => route.path);

const menuGroups = computed(() => {
  const groups = [
    {
      title: "工作台",
      items: [
        { path: "/dashboard", label: "仪表盘", icon: DataBoard },
        { path: "/accounts", label: "账号管理", icon: User },
        { path: "/items", label: "商品管理", icon: Goods },
        { path: "/orders", label: "订单管理", icon: ShoppingCart },
      ],
    },
    {
      title: "自动化",
      items: [
        { path: "/cards", label: "卡券管理", icon: CreditCard },
        { path: "/delivery", label: "自动发货", icon: SwitchButton },
        { path: "/keywords", label: "关键词管理", icon: CollectionTag },
        { path: "/item-replies", label: "自动回复", icon: ChatDotRound },
        { path: "/notification-channels", label: "通知渠道", icon: Bell },
        {
          path: "/message-notifications",
          label: "消息通知",
          icon: Opportunity,
        },
      ],
    },
    {
      title: "整合生态",
      items: [
        { path: "/netdisk/dashboard", label: "网盘控制台", icon: Monitor },
        { path: "/netdisk/accounts", label: "网盘账号池", icon: User },
        { path: "/netdisk/cdkeys", label: "网盘卡密", icon: CreditCard },
        { path: "/netdisk/device-logs", label: "网盘设备记录", icon: Monitor },
        { path: "/netdisk/login-logs", label: "网盘登录审计", icon: Document },
        { path: "/judian/dashboard", label: "聚店控制台", icon: DataBoard },
        { path: "/judian/accounts", label: "聚店账户", icon: User },
        { path: "/judian/cdkeys", label: "聚店卡密", icon: CreditCard },
      ],
    },
    {
      title: "系统",
      items: [
        { path: "/settings", label: "系统设置", icon: Setting },
        { path: "/about", label: "关于系统", icon: InfoFilled },
        { path: "/disclaimer", label: "免责声明", icon: Document },
      ],
    },
  ];

  if (authStore.user?.is_admin) {
    groups.push({
      title: "管理端",
      items: [
        { path: "/admin/users", label: "用户管理", icon: User },
        { path: "/admin/logs", label: "系统日志", icon: Monitor },
        { path: "/admin/risk-logs", label: "风控日志", icon: Monitor },
        { path: "/admin/data", label: "数据管理", icon: DataBoard },
      ],
    });
  }

  return groups;
});

const handleSelect = () => {
  emit("navigate");
};

const handleLogout = async () => {
  authStore.clearAuth();
  ElMessage.success("已退出登录");
  emit("navigate");
  await router.replace("/login");
};
</script>

<template>
  <aside
    class="app-sidebar"
    :class="{
      collapsed: props.collapsed,
      mobile: props.isMobile,
      'mobile-open': props.mobileOpen,
    }"
  >
    <div class="brand">
      <div class="brand-mark">
        <div class="brand-icon">XY</div>
      </div>
      <div v-if="!props.collapsed" class="brand-copy">
        <div class="brand-title">闲鱼自动回复</div>
      </div>
    </div>

    <div class="sidebar-scroll">
      <div
        v-for="group in menuGroups"
        :key="group.title"
        class="menu-group"
        :class="{ compact: props.collapsed }"
      >
        <div v-if="!props.collapsed" class="menu-group-title">
          {{ group.title }}
        </div>
        <el-menu
          class="sidebar-menu"
          :default-active="activePath"
          :collapse="props.collapsed"
          router
          @select="handleSelect"
        >
          <el-menu-item
            v-for="item in group.items"
            :key="item.path"
            :index="item.path"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.label }}</template>
          </el-menu-item>
        </el-menu>
      </div>
    </div>

    <el-button
      class="logout-button"
      :icon="SwitchButton"
      type="danger"
      plain
      @click="handleLogout"
    >
      <span v-if="!props.collapsed">退出登录</span>
    </el-button>
  </aside>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 256px;
  min-height: 100vh;
  padding: 12px 10px 12px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.95)),
    linear-gradient(180deg, #0f172a, #111827);
  color: #e2e8f0;
  border-right: 1px solid rgba(148, 163, 184, 0.08);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.02);
  transition:
    width 0.2s ease,
    padding 0.2s ease;
}

.app-sidebar.collapsed {
  width: 72px;
  padding-inline: 10px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.38);
}

.brand-mark {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.brand-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 11px;
  background: linear-gradient(135deg, #3b82f6, #2563eb 55%, #0ea5e9);
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: 0 18px 30px -20px rgba(37, 99, 235, 0.85);
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  font-size: 13px;
  font-weight: 700;
}

.sidebar-scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.sidebar-scroll::-webkit-scrollbar {
  width: 5px;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
}

.menu-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-group.compact {
  gap: 0;
}

.menu-group-title {
  padding: 0 10px;
  color: rgba(226, 232, 240, 0.52);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.sidebar-menu {
  border: none;
  background: transparent;
}

.sidebar-menu :deep(.el-menu) {
  border-right: none;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 36px;
  margin-bottom: 4px;
  padding-inline: 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: rgba(226, 232, 240, 0.82);
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(59, 130, 246, 0.14);
  border-color: rgba(96, 165, 250, 0.14);
  transform: translateX(1px);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  color: #eff6ff;
  background: linear-gradient(
    135deg,
    rgba(37, 99, 235, 0.92),
    rgba(59, 130, 246, 0.82)
  );
  border-color: rgba(147, 197, 253, 0.22);
  box-shadow: 0 12px 22px -22px rgba(37, 99, 235, 0.95);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 16px;
}

.logout-button {
  width: 100%;
  margin-top: 10px;
}

.app-sidebar.collapsed .logout-button {
  padding-inline: 0;
}

.app-sidebar.collapsed .sidebar-menu :deep(.el-menu-item) {
  justify-content: center;
  padding-inline: 0;
}

@media (max-width: 1023px) {
  .app-sidebar {
    height: 100vh;
  }
}
</style>
