<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Key, Message, Moon, Sunny, User } from "@element-plus/icons-vue";
import { login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import type { LoginRequest } from "@/types";

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(false);
const isDark = ref(false);

const username = ref("");
const password = ref("");

const pageThemeClass = computed(() =>
  isDark.value ? "theme-dark" : "theme-light",
);

const toggleTheme = () => {
  isDark.value = !isDark.value;
  document.documentElement.classList.toggle("dark", isDark.value);
  localStorage.setItem("theme", isDark.value ? "dark" : "light");
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    if (!username.value || !password.value) {
      ElMessage.error("请输入用户名和密码");
      return;
    }

    const loginData: LoginRequest = {
      username: username.value,
      password: password.value,
    };

    const result = await login(loginData);
    if (
      result.success &&
      result.token &&
      result.user_id &&
      result.username !== undefined
    ) {
      authStore.setAuth(result.token, {
        user_id: result.user_id,
        username: result.username,
        is_admin: Boolean(result.is_admin),
      });
      ElMessage.success("登录成功");
      await router.push("/dashboard");
    } else {
      ElMessage.error(result.message || "登录失败");
    }
  } catch {
    ElMessage.error("登录失败，请检查网络连接");
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  const savedTheme = localStorage.getItem("theme");
  isDark.value = savedTheme === "dark";
  document.documentElement.classList.toggle("dark", isDark.value);

  if (authStore.isAuthenticated) {
    await router.replace("/dashboard");
  }
});
</script>

<template>
  <div class="login-page" :class="pageThemeClass">
    <button class="theme-switcher" type="button" @click="toggleTheme">
      <el-icon v-if="isDark"><Sunny /></el-icon>
      <el-icon v-else><Moon /></el-icon>
    </button>

    <div class="hero-panel">
      <div class="hero-mask"></div>
      <div class="hero-content">
        <div class="brand">
          <div class="brand-icon">
            <el-icon><Message /></el-icon>
          </div>
          <span>闲鱼管理系统</span>
        </div>
        <h1>高效专业的闲鱼自动化管理平台</h1>
        <p>自动回复、智能客服、订单管理、数据分析，一站式解决闲鱼运营难题。</p>
      </div>
    </div>

    <div class="form-panel">
      <el-card class="login-card" shadow="never">
        <div class="card-header">
          <h2>登录</h2>
          <p>欢迎回来，请登录您的账号</p>
        </div>

        <el-form label-position="top" @submit.prevent="handleSubmit">
          <el-form-item label="用户名">
            <el-input
              v-model="username"
              placeholder="请输入用户名"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="password"
              placeholder="请输入密码"
              type="password"
              :prefix-icon="Key"
              show-password
            />
          </el-form-item>

          <el-button
            class="submit-button"
            type="primary"
            :loading="loading"
            @click="handleSubmit"
          >
            登 录
          </el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  background: #f8fafc;
  color: #0f172a;
}

.theme-dark {
  background: #020617;
  color: #e2e8f0;
}

.theme-switcher {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 10;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.theme-dark .theme-switcher {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
}

.hero-panel {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a, #111827 60%, #1d4ed8);
}

.hero-mask {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(
      circle at top right,
      rgba(59, 130, 246, 0.35),
      transparent 30%
    ),
    radial-gradient(
      circle at bottom left,
      rgba(14, 165, 233, 0.2),
      transparent 35%
    );
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 520px;
  padding: 80px 56px;
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  font-size: 22px;
  font-weight: 700;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #2563eb;
  font-size: 22px;
}

.hero-content h1 {
  margin: 0 0 12px;
  font-size: 40px;
  line-height: 1.2;
}

.hero-content p {
  margin: 0;
  font-size: 16px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.72);
}

.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 430px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 60px -32px rgba(15, 23, 42, 0.28);
}

.login-card :deep(.el-card__body) {
  padding: 24px;
}

.theme-dark :deep(.el-card) {
  --el-card-bg-color: #0f172a;
  --el-border-color-lighter: rgba(148, 163, 184, 0.15);
  --el-text-color-primary: #f8fafc;
  --el-text-color-regular: #cbd5e1;
}

.theme-dark :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.72);
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.16) inset;
}

:deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-form-item__label) {
  padding-bottom: 6px;
  line-height: 1.3;
}

:deep(.el-input__wrapper) {
  min-height: 40px;
  border-radius: 10px;
}

.card-header {
  margin-bottom: 14px;
}

.card-header h2 {
  margin: 0;
  font-size: 22px;
}

.card-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
}

.submit-button {
  width: 100%;
  min-height: 40px;
  margin-top: 4px;
  border-radius: 10px;
}

@media (max-width: 1080px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    display: none;
  }

  .form-panel {
    align-items: flex-start;
    padding: 48px 16px 16px;
  }
}

@media (max-width: 640px) {
  .theme-switcher {
    top: 10px;
    right: 10px;
    width: 34px;
    height: 34px;
  }

  .form-panel {
    padding: 44px 12px 12px;
  }

  .login-card {
    max-width: 100%;
    border-radius: 16px;
  }

  .login-card :deep(.el-card__body) {
    padding: 18px 16px 16px;
  }

  :deep(.el-form-item) {
    margin-bottom: 12px;
  }

  :deep(.el-input__wrapper) {
    min-height: 38px;
  }

  .card-header {
    margin-bottom: 12px;
  }

  .card-header h2 {
    font-size: 20px;
  }

  .card-header p,
  .card-header p {
    font-size: 12px;
  }

  .submit-button {
    min-height: 38px;
  }
}
</style>
