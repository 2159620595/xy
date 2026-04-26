<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  CopyDocument,
  Download,
  Key,
  Message,
  RefreshRight,
  Setting,
  Upload,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { getAccounts } from "@/api/accounts";
import {
  changePassword,
  exportUserBackup,
  getSystemSettings,
  importUserBackup,
  reloadSystemCache,
  testAIConnection,
  testEmailSend,
  updateSystemSettings,
  uploadDatabaseBackup,
} from "@/api/settings";
import { useAuthStore } from "@/stores/auth";
import type { Account, SystemSettings } from "@/types";

const authStore = useAuthStore();

const loading = ref(true);
const saving = ref(false);
const testingAI = ref(false);
const changingPassword = ref(false);
const uploadingBackup = ref(false);
const reloadingCache = ref(false);
const settings = ref<SystemSettings | null>(null);
const accounts = ref<Account[]>([]);
const testAccountId = ref("");

const backupInputRef = ref<HTMLInputElement | null>(null);
const userBackupInputRef = ref<HTMLInputElement | null>(null);

const passwordForm = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isAdmin = authStore.user?.is_admin ?? false;

const loadSettings = async () => {
  if (!isAdmin) {
    loading.value = false;
    return;
  }

  loading.value = true;
  try {
    const result = await getSystemSettings();
    settings.value = result.data || {};
  } catch {
    ElMessage.error("加载系统设置失败");
  } finally {
    loading.value = false;
  }
};

const loadAccounts = async () => {
  if (!isAdmin) return;
  try {
    const result = await getAccounts();
    accounts.value = result;
    if (!testAccountId.value && result.length) {
      testAccountId.value = result[0].id;
    }
  } catch {
    accounts.value = [];
  }
};

const saveSettings = async () => {
  if (!settings.value) return;
  saving.value = true;
  try {
    const result = await updateSystemSettings(settings.value);
    if (result.success) {
      ElMessage.success("系统设置已保存");
    } else {
      ElMessage.error(result.message || "保存失败");
    }
  } catch {
    ElMessage.error("保存系统设置失败");
  } finally {
    saving.value = false;
  }
};

const copyText = async (value?: string) => {
  if (!value) {
    ElMessage.warning("没有可复制的内容");
    return;
  }
  await navigator.clipboard.writeText(value);
  ElMessage.success("已复制到剪贴板");
};

const handleTestAI = async () => {
  if (!testAccountId.value) {
    ElMessage.warning("请先选择测试账号");
    return;
  }

  testingAI.value = true;
  try {
    if (settings.value) {
      await updateSystemSettings(settings.value);
    }
    const result = await testAIConnection(testAccountId.value);
    if (result.success) {
      ElMessage.success(result.message || "AI 连接测试成功");
    } else {
      ElMessage.error(result.message || "AI 连接测试失败");
    }
  } finally {
    testingAI.value = false;
  }
};

const handleTestEmail = async () => {
  const email = window.prompt("请输入测试邮箱地址");
  if (!email) return;

  const result = await testEmailSend(email);
  if (result.success) {
    ElMessage.success(result.message || "测试邮件发送成功");
  } else {
    ElMessage.error(result.message || "测试邮件发送失败");
  }
};

const handleChangePassword = async () => {
  if (!passwordForm.currentPassword) {
    ElMessage.warning("请输入当前密码");
    return;
  }
  if (!passwordForm.newPassword) {
    ElMessage.warning("请输入新密码");
    return;
  }
  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning("新密码长度不能少于 6 位");
    return;
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }

  changingPassword.value = true;
  try {
    const result = await changePassword({
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
    });
    if (result.success) {
      ElMessage.success("密码修改成功");
      passwordForm.currentPassword = "";
      passwordForm.newPassword = "";
      passwordForm.confirmPassword = "";
    } else {
      ElMessage.error(result.message || "密码修改失败");
    }
  } catch {
    ElMessage.error("密码修改失败");
  } finally {
    changingPassword.value = false;
  }
};

const triggerBackupRestore = () => {
  backupInputRef.value?.click();
};

const triggerUserBackupImport = () => {
  userBackupInputRef.value?.click();
};

const handleRestoreBackup = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.name.endsWith(".db")) {
    ElMessage.error("只支持 .db 数据库备份文件");
    input.value = "";
    return;
  }
  if (!window.confirm("恢复数据库会覆盖当前数据，确定继续吗？")) {
    input.value = "";
    return;
  }

  uploadingBackup.value = true;
  try {
    const result = await uploadDatabaseBackup(file);
    if (result.success) {
      ElMessage.success(result.message || "数据库恢复成功");
    } else {
      ElMessage.error(result.message || "数据库恢复失败");
    }
  } finally {
    uploadingBackup.value = false;
    input.value = "";
  }
};

const handleReloadCache = async () => {
  reloadingCache.value = true;
  try {
    const result = await reloadSystemCache();
    if (result.success) {
      ElMessage.success(result.message || "缓存刷新成功");
    } else {
      ElMessage.error(result.message || "缓存刷新失败");
    }
  } finally {
    reloadingCache.value = false;
  }
};

const handleExportUserBackup = async () => {
  try {
    const { blob, filename } = await exportUserBackup();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch {
    ElMessage.error("导出备份失败");
  }
};

const handleImportUserBackup = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.name.endsWith(".json")) {
    ElMessage.error("只支持 .json 备份文件");
    input.value = "";
    return;
  }

  try {
    const result = await importUserBackup(file);
    if (result.success) {
      ElMessage.success(result.message || "用户备份导入成功");
    } else {
      ElMessage.error(result.message || "用户备份导入失败");
    }
  } finally {
    input.value = "";
  }
};

onMounted(async () => {
  await Promise.all([loadSettings(), loadAccounts()]);
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-description">
          {{
            isAdmin
              ? "配置全局参数、测试 AI/邮件并管理备份恢复。"
              : "当前账号可在这里修改登录密码。"
          }}
        </p>
      </div>
      <div v-if="isAdmin" class="page-actions">
        <el-button :icon="RefreshRight" @click="loadSettings">刷新</el-button>
        <el-button type="primary" :loading="saving" @click="saveSettings"
          >保存设置</el-button
        >
      </div>
    </section>

    <template v-if="isAdmin">
      <div class="settings-grid">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>基础设置</span>
              <el-icon><Setting /></el-icon>
            </div>
          </template>

          <el-skeleton v-if="loading" :rows="6" animated />
          <el-form v-else-if="settings" label-position="top">
            <div class="switch-item">
              <div>
                <div class="cell-title-main">允许用户注册</div>
                <div class="cell-title-sub">控制注册入口是否开放</div>
              </div>
              <el-switch v-model="settings.registration_enabled" />
            </div>

            <div class="switch-item">
              <div>
                <div class="cell-title-main">显示默认登录信息</div>
                <div class="cell-title-sub">在登录页展示默认账号密码提示</div>
              </div>
              <el-switch v-model="settings.show_default_login_info" />
            </div>

            <div class="switch-item">
              <div>
                <div class="cell-title-main">登录滑动验证码</div>
                <div class="cell-title-sub">开启后账号密码登录需要验证码</div>
              </div>
              <el-switch v-model="settings.login_captcha_enabled" />
            </div>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>AI 设置</span>
              <el-icon><Setting /></el-icon>
            </div>
          </template>

          <el-skeleton v-if="loading" :rows="8" animated />
          <el-form v-else-if="settings" label-position="top">
            <el-form-item label="AI 接口地址">
              <el-input
                v-model="settings.ai_api_url"
                placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              />
            </el-form-item>
            <el-form-item label="AI API Key">
              <div class="copyable-field">
                <el-input
                  v-model="settings.ai_api_key"
                  type="password"
                  show-password
                />
                <el-button
                  :icon="CopyDocument"
                  @click="copyText(String(settings.ai_api_key || ''))"
                />
              </div>
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="settings.ai_model" placeholder="qwen-plus" />
            </el-form-item>
            <el-form-item label="测试账号">
              <div class="copyable-field">
                <el-select
                  v-model="testAccountId"
                  placeholder="请选择账号"
                  style="width: 100%"
                >
                  <el-option
                    v-for="account in accounts"
                    :key="account.id"
                    :label="account.id"
                    :value="account.id"
                  />
                </el-select>
                <el-button :loading="testingAI" @click="handleTestAI"
                  >测试 AI</el-button
                >
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>SMTP 配置</span>
              <el-icon><Message /></el-icon>
            </div>
          </template>

          <el-skeleton v-if="loading" :rows="8" animated />
          <el-form v-else-if="settings" label-position="top">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="SMTP 服务器">
                  <el-input
                    v-model="settings.smtp_server"
                    placeholder="smtp.qq.com"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SMTP 端口">
                  <el-input-number
                    v-model="settings.smtp_port"
                    :min="1"
                    :max="65535"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="发件邮箱">
                  <el-input
                    v-model="settings.smtp_user"
                    placeholder="your-email@example.com"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="邮箱密码/授权码">
                  <div class="copyable-field">
                    <el-input
                      v-model="settings.smtp_password"
                      type="password"
                      show-password
                    />
                    <el-button
                      :icon="CopyDocument"
                      @click="copyText(String(settings.smtp_password || ''))"
                    />
                  </div>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="发件人显示名">
              <el-input
                v-model="settings.smtp_from"
                placeholder="闲鱼自动回复系统"
              />
            </el-form-item>

            <div class="switch-group">
              <div class="switch-item">
                <div>
                  <div class="cell-title-main">启用 TLS</div>
                  <div class="cell-title-sub">通常使用 587 端口</div>
                </div>
                <el-switch v-model="settings.smtp_use_tls" />
              </div>

              <div class="switch-item">
                <div>
                  <div class="cell-title-main">启用 SSL</div>
                  <div class="cell-title-sub">通常使用 465 端口</div>
                </div>
                <el-switch v-model="settings.smtp_use_ssl" />
              </div>
            </div>

            <el-button @click="handleTestEmail">发送测试邮件</el-button>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>数据备份</span>
              <el-icon><Download /></el-icon>
            </div>
          </template>

          <div class="backup-section">
            <div>
              <div class="cell-title-main">用户数据备份</div>
              <div class="cell-title-sub">
                导出或导入当前用户的账号、关键词、卡券等数据
              </div>
            </div>
            <div class="page-actions">
              <el-button :icon="Download" @click="handleExportUserBackup"
                >导出备份</el-button
              >
              <el-button :icon="Upload" @click="triggerUserBackupImport"
                >导入备份</el-button
              >
              <input
                ref="userBackupInputRef"
                class="hidden-input"
                type="file"
                accept=".json"
                @change="handleImportUserBackup"
              />
            </div>
          </div>

          <el-divider />

          <div class="backup-section">
            <div>
              <div class="cell-title-main">数据库恢复</div>
              <div class="cell-title-sub">
                管理员可上传数据库备份并刷新系统缓存
              </div>
            </div>
            <div class="page-actions">
              <el-button
                :icon="Upload"
                :loading="uploadingBackup"
                @click="triggerBackupRestore"
              >
                恢复数据库
              </el-button>
              <el-button
                :icon="RefreshRight"
                :loading="reloadingCache"
                @click="handleReloadCache"
              >
                刷新缓存
              </el-button>
              <input
                ref="backupInputRef"
                class="hidden-input"
                type="file"
                accept=".db"
                @change="handleRestoreBackup"
              />
            </div>
          </div>
        </el-card>
      </div>
    </template>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
          <el-icon><Key /></el-icon>
        </div>
      </template>

      <el-form label-position="top" class="password-form">
        <el-form-item label="当前密码">
          <el-input
            v-model="passwordForm.currentPassword"
            type="password"
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          :loading="changingPassword"
          @click="handleChangePassword"
        >
          修改密码
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.switch-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.switch-item:last-child {
  border-bottom: none;
}

.copyable-field {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
}

.copyable-field :deep(.el-input) {
  flex: 1;
}

.backup-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.hidden-input {
  display: none;
}

.password-form {
  max-width: 560px;
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
