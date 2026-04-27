<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  Delete,
  Plus,
  RefreshRight,
  Search,
  UserFilled,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { deleteUser, getUsers } from "@/api/admin";
import { useAuthStore } from "@/stores/auth";
import type { User } from "@/types";

const authStore = useAuthStore();

const loading = ref(true);
const keyword = ref("");
const roleFilter = ref("");
const deletingUserId = ref<number | null>(null);
const createUserDialogVisible = ref(false);
const users = ref<User[]>([]);

const filteredUsers = computed(() => {
  const query = keyword.value.trim().toLowerCase();

  return users.value.filter((user) => {
    const matchRole =
      roleFilter.value === ""
        ? true
        : roleFilter.value === "admin"
          ? user.is_admin
          : !user.is_admin;

    if (!matchRole) {
      return false;
    }

    if (!query) {
      return true;
    }

    return [user.username, user.email, String(user.user_id)]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });
});

const adminCount = computed(
  () => users.value.filter((user) => user.is_admin).length,
);
const regularCount = computed(() => users.value.length - adminCount.value);
const configuredEmailCount = computed(
  () => users.value.filter((user) => Boolean(user.email)).length,
);
const totalAccountCount = computed(() =>
  users.value.reduce((sum, user) => sum + (user.cookie_count || 0), 0),
);
const activeFilterCount = computed(() => {
  let count = 0;
  if (keyword.value.trim()) count += 1;
  if (roleFilter.value) count += 1;
  return count;
});
const overviewMetrics = computed(() => [
  {
    label: "用户总数",
    value: String(users.value.length),
    description: "当前系统已注册的全部用户",
    tone: "primary",
  },
  {
    label: "管理员",
    value: String(adminCount.value),
    description: "拥有后台访问和管理权限",
    tone: "warning",
  },
  {
    label: "普通用户",
    value: String(regularCount.value),
    description: "当前业务侧普通使用账号",
    tone: "info",
  },
  {
    label: "已配置邮箱",
    value: String(configuredEmailCount.value),
    description: "可用于邮箱登录或验证",
    tone: "success",
  },
  {
    label: "关联闲鱼账号",
    value: String(totalAccountCount.value),
    description: "全部用户绑定的账号总量",
    tone: "default",
  },
  {
    label: "筛选条件",
    value: String(activeFilterCount.value),
    description:
      activeFilterCount.value > 0 ? "当前已启用筛选条件" : "当前未启用筛选",
    tone: "danger",
  },
]);

const loadUsers = async () => {
  loading.value = true;
  try {
    const result = await getUsers();
    users.value = result.data || [];
  } catch {
    users.value = [];
    ElMessage.error("加载用户列表失败");
  } finally {
    loading.value = false;
  }
};

const openCreateUserDialog = () => {
  createUserDialogVisible.value = true;
};

const handleDelete = async (userId: number) => {
  try {
    await ElMessageBox.confirm(
      "确定要删除这个用户吗？此操作会一并移除其关联数据。",
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deletingUserId.value = userId;
  try {
    await deleteUser(userId);
    ElMessage.success("删除成功");
    await loadUsers();
  } catch (error) {
    const message =
      error &&
      typeof error === "object" &&
      "response" in error &&
      error.response &&
      typeof error.response === "object" &&
      "data" in error.response &&
      error.response.data &&
      typeof error.response.data === "object"
        ? ((error.response.data as { detail?: string }).detail ?? "删除失败")
        : "删除失败";
    ElMessage.error(message);
  } finally {
    deletingUserId.value = null;
  }
};

onMounted(async () => {
  await loadUsers();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-description">
          查看系统用户、账号与卡券占用情况，快速定位异常账号并执行删除。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Plus" type="primary" @click="openCreateUserDialog">
          添加用户
        </el-button>
        <el-button :icon="RefreshRight" @click="loadUsers">刷新</el-button>
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
        <el-icon><Search /></el-icon>
        <span>筛选条件</span>
      </div>
      <div class="inline-form">
        <el-form-item label="搜索用户">
          <el-input
            v-model="keyword"
            clearable
            :prefix-icon="Search"
            placeholder="用户名 / 邮箱 / ID"
          />
        </el-form-item>
        <el-form-item label="角色筛选">
          <el-select v-model="roleFilter" clearable placeholder="全部角色">
            <el-option label="全部角色" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </div>
      <div class="filter-summary">
        <el-tag v-if="activeFilterCount > 0" type="warning" effect="plain">
          已启用 {{ activeFilterCount }} 个筛选
        </el-tag>
        <el-tag type="info" effect="plain">
          当前展示 {{ filteredUsers.length }} / {{ users.length }} 个用户
        </el-tag>
        <span class="text-muted"
          >支持按用户名、邮箱、ID 和角色快速定位用户</span
        >
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div>
          <div class="toolbar-meta">
            当前展示 {{ filteredUsers.length }} / {{ users.length }} 个用户
          </div>
          <div class="toolbar-submeta">
            删除用户会同步清理关联数据，当前登录管理员账号不可自删
          </div>
        </div>
        <div class="toolbar-tags">
          <el-tag type="info" effect="plain">当前不开放公开注册</el-tag>
          <el-tag type="warning" effect="plain"
            >删除用户会同步清理关联数据</el-tag
          >
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredUsers"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column prop="user_id" label="ID" width="90" />
        <el-table-column label="用户名" min-width="220">
          <template #default="{ row }">
            <div class="cell-title">
              <span class="cell-title-main">{{ row.username }}</span>
              <span class="cell-title-sub">
                {{ row.is_admin ? "拥有后台管理权限" : "普通业务用户" }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="240">
          <template #default="{ row }">
            <div class="cell-title">
              <span class="cell-title-main">{{ row.email || "-" }}</span>
              <span class="cell-title-sub">
                {{ row.email ? "已配置登录邮箱" : "未配置邮箱" }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'warning' : 'info'" effect="plain">
              {{ row.is_admin ? "管理员" : "普通用户" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="闲鱼账号" width="110" align="center">
          <template #default="{ row }">
            <span>{{ row.cookie_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="卡券数" width="100" align="center">
          <template #default="{ row }">
            <span>{{ row.card_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              :icon="Delete"
              :disabled="row.user_id === authStore.user?.user_id"
              :loading="deletingUserId === row.user_id"
              @click="handleDelete(row.user_id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无用户数据" />
        </template>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <div class="tip-card">
        <el-icon><UserFilled /></el-icon>
        <span>
          当前登录管理员账号不可自删；当前版本不开放公开注册，管理员页负责巡检、筛选和清理异常用户。
        </span>
      </div>
    </el-card>

    <el-dialog
      v-model="createUserDialogVisible"
      title="添加用户"
      width="560px"
      destroy-on-close
    >
      <div class="create-user-guide">
        <el-alert
          title="当前系统已关闭公开注册"
          type="warning"
          :closable="false"
          show-icon
        />

        <div class="guide-block">
          <div class="guide-title">当前状态</div>
          <div class="guide-text">
            登录页和公开注册页都已收起，前台用户无法再通过注册链接自助创建账号。
          </div>
        </div>

        <div class="guide-block">
          <div class="guide-title">新增用户</div>
          <div class="guide-text">
            如需继续提供管理员创建用户能力，需要后端补充管理接口，或由你指定新的后台新增方案。
          </div>
        </div>
      </div>
    </el-dialog>
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

.metric-panel--warning .metric-dot {
  background: #f59e0b;
}

.metric-panel--info .metric-dot {
  background: #0ea5e9;
}

.metric-panel--success .metric-dot {
  background: #22c55e;
}

.metric-panel--danger .metric-dot {
  background: #ef4444;
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

.toolbar-submeta {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.create-user-guide {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guide-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.guide-text {
  color: #64748b;
  line-height: 1.7;
}

.guide-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.guide-tip {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
  color: #64748b;
  line-height: 1.7;
}

.toolbar-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
