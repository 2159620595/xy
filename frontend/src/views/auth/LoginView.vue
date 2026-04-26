<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Key, Message, Moon, Sunny, User } from "@element-plus/icons-vue";
import {
  generateCaptcha,
  getLoginInfoStatus,
  getRegistrationStatus,
  login,
  sendVerificationCode,
  verifyCaptcha,
} from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import type { LoginRequest } from "@/types";

type LoginType = "username" | "email-password" | "email-code";

const router = useRouter();
const authStore = useAuthStore();

const loginType = ref<LoginType>("username");
const loading = ref(false);
const registrationEnabled = ref(true);
const showDefaultLogin = ref(true);
const isDark = ref(false);

const username = ref("");
const password = ref("");
const email = ref("");
const emailPassword = ref("");
const emailForCode = ref("");
const captchaCode = ref("");
const verificationCode = ref("");

const captchaImage = ref("");
const captchaVerified = ref(false);
const countdown = ref(0);
const verifying = ref(false);
const sessionId = `session_${Math.random().toString(36).slice(2, 11)}_${Date.now()}`;

const pageThemeClass = computed(() =>
  isDark.value ? "theme-dark" : "theme-light",
);

const toggleTheme = () => {
  isDark.value = !isDark.value;
  document.documentElement.classList.toggle("dark", isDark.value);
  localStorage.setItem("theme", isDark.value ? "dark" : "light");
};

const loadCaptcha = async () => {
  try {
    const result = await generateCaptcha(sessionId);
    if (result.success && result.captcha_image) {
      captchaImage.value = result.captcha_image;
      captchaVerified.value = false;
      captchaCode.value = "";
    }
  } catch {
    ElMessage.error("加载验证码失败");
  }
};

const handleVerifyCaptchaAuto = async () => {
  if (captchaCode.value.length !== 4 || verifying.value) return;

  verifying.value = true;
  try {
    const result = await verifyCaptcha(sessionId, captchaCode.value);
    if (result.success) {
      captchaVerified.value = true;
      ElMessage.success("验证码验证成功");
    } else {
      captchaVerified.value = false;
      await loadCaptcha();
      ElMessage.error("验证码错误");
    }
  } catch {
    ElMessage.error("验证失败");
  } finally {
    verifying.value = false;
  }
};

const handleSendCode = async () => {
  if (!captchaVerified.value || !emailForCode.value || countdown.value > 0)
    return;

  try {
    const result = await sendVerificationCode(
      emailForCode.value,
      "login",
      sessionId,
    );
    if (result.success) {
      countdown.value = 60;
      ElMessage.success("验证码已发送");
    } else {
      ElMessage.error(result.message || result.detail || "发送失败");
    }
  } catch {
    ElMessage.error("发送验证码失败");
  }
};

const fillDefaultCredentials = () => {
  loginType.value = "username";
  username.value = "admin";
  password.value = "admin123";
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    let loginData: LoginRequest = {};

    if (loginType.value === "username") {
      if (!username.value || !password.value) {
        ElMessage.error("请输入用户名和密码");
        return;
      }
      loginData = {
        username: username.value,
        password: password.value,
      };
    } else if (loginType.value === "email-password") {
      if (!email.value || !emailPassword.value) {
        ElMessage.error("请输入邮箱和密码");
        return;
      }
      loginData = {
        email: email.value,
        password: emailPassword.value,
      };
    } else {
      if (!emailForCode.value || !verificationCode.value) {
        ElMessage.error("请输入邮箱和验证码");
        return;
      }
      loginData = {
        email: emailForCode.value,
        verification_code: verificationCode.value,
      };
    }

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

watch(loginType, async (nextType) => {
  if (nextType === "email-code") {
    await loadCaptcha();
  }
});

watch(countdown, (value, _, onCleanup) => {
  if (value <= 0) return;
  const timer = window.setTimeout(() => {
    countdown.value -= 1;
  }, 1000);
  onCleanup(() => window.clearTimeout(timer));
});

watch(captchaCode, async (value) => {
  if (
    loginType.value === "email-code" &&
    value.length === 4 &&
    !captchaVerified.value &&
    !verifying.value
  ) {
    await handleVerifyCaptchaAuto();
  }
});

onMounted(async () => {
  const savedTheme = localStorage.getItem("theme");
  isDark.value = savedTheme === "dark";
  document.documentElement.classList.toggle("dark", isDark.value);

  if (authStore.isAuthenticated) {
    await router.replace("/dashboard");
    return;
  }

  const [registrationStatus, loginInfoStatus] = await Promise.allSettled([
    getRegistrationStatus(),
    getLoginInfoStatus(),
  ]);

  if (registrationStatus.status === "fulfilled") {
    registrationEnabled.value = registrationStatus.value.enabled;
  }
  if (loginInfoStatus.status === "fulfilled") {
    showDefaultLogin.value = loginInfoStatus.value.enabled;
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

        <el-tabs v-model="loginType" stretch>
          <el-tab-pane label="账号登录" name="username" />
          <el-tab-pane label="邮箱密码" name="email-password" />
          <el-tab-pane label="验证码" name="email-code" />
        </el-tabs>

        <el-form label-position="top" @submit.prevent="handleSubmit">
          <template v-if="loginType === 'username'">
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
          </template>

          <template v-else-if="loginType === 'email-password'">
            <el-form-item label="邮箱地址">
              <el-input
                v-model="email"
                placeholder="name@example.com"
                :prefix-icon="Message"
              />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="emailPassword"
                placeholder="请输入密码"
                type="password"
                :prefix-icon="Key"
                show-password
              />
            </el-form-item>
          </template>

          <template v-else>
            <el-form-item label="邮箱地址">
              <el-input
                v-model="emailForCode"
                placeholder="name@example.com"
                :prefix-icon="Message"
              />
            </el-form-item>
            <el-form-item label="图形验证码">
              <div class="captcha-row">
                <el-input
                  v-model="captchaCode"
                  maxlength="4"
                  placeholder="输入验证码"
                  :disabled="captchaVerified"
                />
                <img
                  v-if="captchaImage"
                  :src="captchaImage"
                  alt="验证码"
                  class="captcha-image"
                  @click="loadCaptcha"
                />
              </div>
              <div
                class="captcha-tip"
                :class="{ success: captchaVerified, pending: verifying }"
              >
                {{
                  captchaVerified
                    ? "验证码校验成功"
                    : verifying
                      ? "验证码校验中..."
                      : "点击图片可刷新验证码"
                }}
              </div>
            </el-form-item>
            <el-form-item label="邮箱验证码">
              <div class="captcha-row">
                <el-input
                  v-model="verificationCode"
                  maxlength="6"
                  placeholder="6位数字验证码"
                  :prefix-icon="Key"
                />
                <el-button
                  type="default"
                  :disabled="!captchaVerified || !emailForCode || countdown > 0"
                  @click="handleSendCode"
                >
                  {{ countdown > 0 ? `${countdown}s` : "发送" }}
                </el-button>
              </div>
            </el-form-item>
          </template>

          <el-button
            class="submit-button"
            type="primary"
            :loading="loading"
            @click="handleSubmit"
          >
            登 录
          </el-button>
        </el-form>

        <div v-if="registrationEnabled" class="register-tip">
          还没有账号？
          <router-link to="/register">立即注册</router-link>
        </div>

        <div
          v-if="showDefaultLogin"
          class="demo-login"
          @click="fillDefaultCredentials"
        >
          <div>
            <p>演示账号</p>
            <strong>admin / admin123</strong>
          </div>
          <span>一键填充</span>
        </div>
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
  top: 16px;
  right: 16px;
  z-index: 10;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
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
  padding: 96px 64px;
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
  font-size: 24px;
  font-weight: 700;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: #2563eb;
  font-size: 24px;
}

.hero-content h1 {
  margin: 0 0 16px;
  font-size: 44px;
  line-height: 1.2;
}

.hero-content p {
  margin: 0;
  font-size: 18px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.72);
}

.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 460px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 60px -32px rgba(15, 23, 42, 0.28);
}

.theme-dark :deep(.el-card) {
  --el-card-bg-color: #0f172a;
  --el-border-color-lighter: rgba(148, 163, 184, 0.15);
  --el-text-color-primary: #f8fafc;
  --el-text-color-regular: #cbd5e1;
}

.theme-dark :deep(.el-tabs__item) {
  color: #cbd5e1;
}

.theme-dark :deep(.el-tabs__item.is-active) {
  color: #60a5fa;
}

.theme-dark :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.72);
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.16) inset;
}

.card-header {
  margin-bottom: 16px;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
}

.card-header p {
  margin: 6px 0 0;
  color: #64748b;
}

.captcha-row {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 12px;
  width: 100%;
}

.captcha-image {
  width: 120px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  object-fit: cover;
  cursor: pointer;
}

.captcha-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.captcha-tip.success {
  color: #16a34a;
}

.captcha-tip.pending {
  color: #2563eb;
}

.submit-button {
  width: 100%;
  margin-top: 8px;
}

.register-tip {
  margin-top: 20px;
  text-align: center;
  color: #64748b;
  font-size: 14px;
}

.register-tip :deep(a) {
  color: #2563eb;
  font-weight: 600;
}

.demo-login {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  cursor: pointer;
  transition: background 0.2s ease;
}

.demo-login:hover {
  background: #eff6ff;
}

.theme-dark .demo-login {
  background: rgba(30, 41, 59, 0.7);
}

.demo-login p {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 13px;
}

.demo-login strong {
  font-size: 14px;
}

.demo-login span {
  color: #2563eb;
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 1080px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    display: none;
  }

  .form-panel {
    padding: 56px 20px 20px;
  }
}

@media (max-width: 640px) {
  .captcha-row {
    grid-template-columns: 1fr;
  }

  .captcha-image {
    width: 100%;
  }
}
</style>
