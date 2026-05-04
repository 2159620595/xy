<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Promotion, RefreshRight, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { getAdminStats } from "@/api/admin";
import { getAccountDetails } from "@/api/accounts";
import { getKeywordCounts } from "@/api/keywords";
import { getOrders } from "@/api/orders";
import { useAuthStore } from "@/stores/auth";
import type { AccountDetail, AdminStats, DashboardStats } from "@/types";

const authStore = useAuthStore();

const loading = ref(true);
const accounts = ref<AccountDetail[]>([]);
const adminStats = ref<AdminStats | null>(null);
const stats = ref<DashboardStats>({
  totalAccounts: 0,
  totalKeywords: 0,
  activeAccounts: 0,
  totalOrders: 0,
});

const loadDashboard = async () => {
  loading.value = true;
  try {
    const [accountsData, keywordCounts] = await Promise.all([
      getAccountDetails(),
      getKeywordCounts().catch(() => ({} as Record<string, number>)),
    ]);
    const accountsWithKeywords = accountsData.map((account) => ({
      ...account,
      keywordCount: keywordCounts[account.id] || 0,
    }));

    let totalKeywords = 0;
    let activeAccounts = 0;

    accountsWithKeywords.forEach((account) => {
      const isEnabled = account.enabled !== false;
      if (isEnabled) {
        activeAccounts += 1;
        totalKeywords += account.keywordCount || 0;
      }
    });

    accounts.value = accountsWithKeywords;
    stats.value = {
      totalAccounts: accountsWithKeywords.length,
      totalKeywords,
      activeAccounts,
      totalOrders: 0,
    };

    try {
      const ordersResult = await getOrders();
      stats.value = {
        ...stats.value,
        totalOrders: ordersResult.success
          ? ordersResult.total || ordersResult.data.length
          : 0,
      };
    } catch {
      stats.value = {
        ...stats.value,
        totalOrders: 0,
      };
    }

    if (authStore.user?.is_admin) {
      try {
        const adminResult = await getAdminStats();
        adminStats.value = adminResult.success
          ? adminResult.data || null
          : null;
      } catch {
        adminStats.value = null;
      }
    } else {
      adminStats.value = null;
    }
  } catch {
    accounts.value = [];
    stats.value = {
      totalAccounts: 0,
      totalKeywords: 0,
      activeAccounts: 0,
      totalOrders: 0,
    };
    ElMessage.error("仪表盘数据加载失败");
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await loadDashboard();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-description">
          当前已接入真实账号、关键词和订单统计，继续围绕核心迁移链路推进。
        </p>
      </div>
      <div class="page-actions">
        <el-tag size="large" type="primary" effect="plain">
          当前用户：{{ authStore.user?.username || "未登录" }}
        </el-tag>
        <el-button
          :icon="RefreshRight"
          :loading="loading"
          @click="loadDashboard"
          >刷新数据</el-button
        >
      </div>
    </section>

    <el-card v-if="authStore.user?.is_admin && adminStats" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><Promotion /></el-icon>
          <span>全局统计（管理员）</span>
        </div>
      </template>
      <div class="admin-stats-grid">
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.total_users }}</div>
          <div class="text-muted">总用户数</div>
        </div>
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.total_cookies }}</div>
          <div class="text-muted">总账号数</div>
        </div>
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.active_cookies }}</div>
          <div class="text-muted">活跃账号</div>
        </div>
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.total_cards }}</div>
          <div class="text-muted">总卡券数</div>
        </div>
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.total_keywords }}</div>
          <div class="text-muted">总关键词</div>
        </div>
        <div class="admin-stat-card">
          <div class="admin-stat-value">{{ adminStats.total_orders }}</div>
          <div class="text-muted">总订单数</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><User /></el-icon>
          <span>账号详情</span>
        </div>
      </template>
      <el-table v-loading="loading" :data="accounts" style="width: 100%">
        <el-table-column label="账号 ID" min-width="220">
          <template #default="{ row }">
            <span>{{
              row.xianyu_nickname
                ? `${row.id}（${row.xianyu_nickname}）`
                : row.id
            }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关键词数量" width="120">
          <template #default="{ row }">
            <span>{{ row.keywordCount || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag
              :type="
                row.enabled !== false
                  ? (row.keywordCount || 0) > 0
                    ? 'success'
                    : 'info'
                  : 'danger'
              "
              effect="plain"
            >
              {{
                row.enabled !== false
                  ? (row.keywordCount || 0) > 0
                    ? "活跃"
                    : "无关键词"
                  : "已禁用"
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后更新" min-width="180">
          <template #default="{ row }">
            <span>{{
              row.updated_at ? new Date(row.updated_at).toLocaleString() : "-"
            }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无账号数据" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.admin-stats-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.admin-stat-card {
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  text-align: center;
}

.admin-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

@media (max-width: 960px) {
  .admin-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
