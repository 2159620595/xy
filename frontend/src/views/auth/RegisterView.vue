<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Hide, Key, Message, Promotion, User, View } from "@element-plus/icons-vue";
import {
  generateCaptcha,
  getRegistrationStatus,
  register,
  sendVerificationCode,
  verifyCaptcha,
} from "@/api/auth";
import type { RegisterRequest } from "@/types";

const router = useRouter();

const loading = ref(false);
const registrationEnabled = ref(true);
const showPassword = ref(false);
const captchaImage = ref("");
const captchaVerified = ref(false);
const countdown = ref(0);
const verifying = ref(false);
const sessionId = `session_${Math.random().toString(36).slice(2, 11)}_${Date.now()}`;

const form = reactive({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
  captchaCode: "",
  verificationCode: "",
});

const emailValid = computed(() =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()),
);

const loadCaptcha = async () => {
  try {
    const result = await generateCaptcha(sessionId);
    if (result.success && result.captcha_image) {
      captchaImage.value = result.captcha_image;
      captchaVerified.value = false;
      form.captchaCode = "";
    }
  } catch {
    ElMessage.error("加载验证码失败");
  }
};

const handleVerifyCaptchaAuto = async () => {
  if (form.captchaCode.length !== 4 || verifying.value) return;

  verifying.value = true;
  try {
    const result = await verifyCaptcha(sessionId, form.captchaCode);
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

const validateFormForCode = () => {
  if (!form.username.trim()) {
    ElMessage.warning("请先输入用户名");
    return false;
  }
  if (!form.email.trim()) {
    ElMessage.warning("请先输入邮箱地址");
    return false;
  }
  if (!emailValid.value) {
    ElMessage.warning("请输入正确的邮箱格式");
    return false;
  }
  if (!form.password) {
    ElMessage.warning("请先输入密码");
    return false;
  }
  if (form.password.length < 6) {
    ElMessage.warning("密码长度至少 6 位");
    return false;
  }
  if (!form.confirmPassword) {
    ElMessage.warning("请先确认密码");
    return false;
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning("两次输入的密码不一致");
    return false;
  }
  if (!captchaVerified.value) {
    ElMessage.warning("请先完成图形验证码验证");
    return false;
  }
  return true;
};

const handleSendCode = async () => {
  if (!validateFormForCode() || countdown.value > 0) return;

  try {
    const result = await sendVerificationCode(
      form.email.trim(),
      "register",
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

const handleSubmit = async () => {
  if (!form.username || !form.email || !form.password || !form.confirmPassword) {
    ElMessage.error("请填写所有必填项");
    return;
  }
  if (!emailValid.value) {
    ElMessage.error("请输入正确的邮箱格式");
    return;
  }
  if (!form.verificationCode) {
    ElMessage.error("请输入邮箱验证码");
    return;
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.error("两次输入的密码不一致");
    return;
  }
  if (form.password.length < 6) {
    ElMessage.error("密码长度至少 6 位");
    return;
  }

  loading.value = true;
  try {
    const payload: RegisterRequest = {
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
      verification_code: form.verificationCode.trim(),
      session_id: sessionId,
    };
    const result = await register(payload);
    if (result.success) {
      ElMessage.success("注册成功，请登录");
      await router.push("/login");
    } else {
      ElMessage.error(result.message || result.detail || "注册失败");
    }
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
        ? ((error.response.data as { detail?: string; message?: string }).detail ||
            (error.response.data as { detail?: string; message?: string }).message)
        : undefined;

    ElMessage.error(message || "注册失败，请检查网络连接");
  } finally {
    loading.value = false;
  }
};

watch(countdown, (value, _, onCleanup) => {
  if (value <= 0) return;
  const timer = window.setTimeout(() => {
    countdown.value -= 1;
  }, 1000);
  onCleanup(() => window.clearTimeout(timer));
});

watch(
  () => form.captchaCode,
  async (value) => {
    if (value.length === 4 && !captchaVerified.value && !verifying.value) {
      await handleVerifyCaptchaAuto();
    }
  },
);

onMounted(async () => {
  try {
    const result = await getRegistrationStatus();
    registrationEnabled.value = result.enabled;
    if (result.enabled) {
      await loadCaptcha();
    }
  } catch {
    registrationEnabled.value = true;
    await loadCaptcha();
  }
});
</script>

<template>
  <div class="register-page">
    <el-card v-if="registrationEnabled" class="register-card" shadow="never">
      <div class="register-header">
        <div class="register-badge">
          <el-icon><Promotion /></el-icon>
        </div>
        <h1>用户注册</h1>
        <p>创建账号后即可登录 Vue 管理台，使用账号管理、商品搜索和通知能力。</p>
      </div>

      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="邮箱地址">
          <el-input
            v-model="form.email"
            placeholder="name@example.com"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="至少 6 位字符"
            :prefix-icon="Key"
          >
            <template #suffix>
              <el-button
                link
                type="primary"
                class="icon-button"
                @click="showPassword = !showPassword"
              >
                <el-icon><component :is="showPassword ? Hide : View" /></el-icon>
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            :type="showPassword ? 'text' : 'password'"
            placeholder="请再次输入密码"
            :prefix-icon="Key"
          />
        </el-form-item>

        <el-form-item label="图形验证码">
          <div class="captcha-row">
            <el-input
              v-model="form.captchaCode"
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
              v-model="form.verificationCode"
              maxlength="6"
              placeholder="6 位数字验证码"
              :prefix-icon="Key"
            />
            <el-button
              :disabled="!captchaVerified || !form.email || countdown > 0"
              @click="handleSendCode"
            >
              {{ countdown > 0 ? `${countdown}s` : "发送" }}
            </el-button>
          </div>
        </el-form-item>

        <el-button
          type="primary"
          class="submit-button"
          :loading="loading"
          @click="handleSubmit"
        >
          注 册
        </el-button>
      </el-form>

      <div class="bottom-tip">
        已有账号？
        <router-link to="/login" class="link-text">立即登录</router-link>
      </div>
    </el-card>

    <el-card v-else class="register-card state-card" shadow="never">
      <h2>注册功能已关闭</h2>
      <p>管理员已关闭注册功能，如需账号请联系管理员。</p>
      <el-button type="primary" @click="router.push('/login')">返回登录</el-button>
    </el-card>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 24%),
    linear-gradient(180deg, #eff6ff, #f8fafc);
}

.register-card {
  width: 100%;
  max-width: 520px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 60px -32px rgba(15, 23, 42, 0.28);
}

.register-header {
  margin-bottom: 18px;
  text-align: center;
}

.register-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  font-size: 24px;
}

.register-header h1 {
  margin: 0;
  font-size: 28px;
}

.register-header p {
  margin: 10px 0 0;
  color: #64748b;
  line-height: 1.6;
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

.bottom-tip {
  margin-top: 20px;
  text-align: center;
  color: #64748b;
  font-size: 14px;
}

.link-text {
  color: #2563eb;
  font-weight: 600;
}

.state-card {
  text-align: center;
}

.state-card h2 {
  margin: 0;
  font-size: 24px;
}

.state-card p {
  margin: 12px 0 24px;
  color: #64748b;
}

.icon-button {
  padding: 0;
}

@media (max-width: 640px) {
  .register-page {
    padding: 16px;
  }

  .captcha-row {
    grid-template-columns: 1fr;
  }

  .captcha-image {
    width: 100%;
  }
}
</style>
