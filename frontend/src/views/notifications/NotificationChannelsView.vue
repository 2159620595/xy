<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  Bell,
  Connection,
  DocumentCopy,
  Edit,
  MagicStick,
  Message,
  Plus,
  Promotion,
  RefreshRight,
  Search,
  Setting,
  Share,
  SwitchButton,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  addNotificationChannel,
  deleteNotificationChannel,
  getNotificationChannels,
  testNotificationChannel,
  updateNotificationChannel,
} from "@/api/notifications";
import type { NotificationChannel } from "@/types";

type ChannelType = NotificationChannel["type"];

const channelTypes: Array<{
  type: ChannelType;
  label: string;
  desc: string;
  placeholder: string;
}> = [
  {
    type: "dingtalk",
    label: "钉钉通知",
    desc: "钉钉机器人消息",
    placeholder:
      '{"webhook_url":"https://oapi.dingtalk.com/robot/send?access_token=..."}',
  },
  {
    type: "feishu",
    label: "飞书通知",
    desc: "飞书机器人消息",
    placeholder:
      '{"webhook_url":"https://open.feishu.cn/open-apis/bot/v2/hook/..."}',
  },
  {
    type: "bark",
    label: "Bark 通知",
    desc: "iOS 推送通知",
    placeholder:
      '{"device_key":"xxx","server_url":"https://api.day.app"}',
  },
  {
    type: "email",
    label: "邮件通知",
    desc: "SMTP 邮件发送",
    placeholder:
      '{"smtp_server":"...","smtp_port":587,"email_user":"...","email_password":"...","recipient_email":"..."}',
  },
  {
    type: "webhook",
    label: "Webhook",
    desc: "自定义 HTTP 请求",
    placeholder: '{"webhook_url":"https://..."}',
  },
  {
    type: "wechat",
    label: "微信通知",
    desc: "企业微信机器人",
    placeholder:
      '{"webhook_url":"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."}',
  },
  {
    type: "telegram",
    label: "Telegram",
    desc: "Telegram 机器人",
    placeholder: '{"bot_token":"...","chat_id":"..."}',
  },
  {
    type: "qq",
    label: "QQ 通知",
    desc: "QQ 消息推送",
    placeholder: '{"recipient":"...","api_key":"..."}',
  },
];

const loading = ref(true);
const saving = ref(false);
const testingChannelId = ref("");
const dialogVisible = ref(false);
const filterKeyword = ref("");
const channels = ref<NotificationChannel[]>([]);
const editingChannel = ref<NotificationChannel | null>(null);
const selectedType = ref<ChannelType | null>(null);

const form = reactive({
  name: "",
  config: "",
  enabled: true,
});

const configuredCount = computed(() => channels.value.length);
const filteredChannels = computed(() => {
  const query = filterKeyword.value.trim().toLowerCase();
  if (!query) {
    return channels.value;
  }

  return channels.value.filter((channel) =>
    [channel.name, channel.type, channel.channel_name]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query)),
  );
});

const getChannelByType = (type: ChannelType) =>
  channels.value.find((item) => item.type === type);

const getSelectedTypeTemplate = () => {
  return channelTypes.find((item) => item.type === selectedType.value)?.placeholder || "";
};

const resetForm = () => {
  form.name = "";
  form.config = "";
  form.enabled = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  editingChannel.value = null;
  selectedType.value = null;
  resetForm();
};

const loadChannels = async () => {
  loading.value = true;
  try {
    const result = await getNotificationChannels();
    channels.value = result.data || [];
  } catch {
    ElMessage.error("加载通知渠道失败");
    channels.value = [];
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = (type: ChannelType) => {
  const matched = channelTypes.find((item) => item.type === type);
  selectedType.value = type;
  editingChannel.value = null;
  form.name = matched?.label || "";
  form.config = matched?.placeholder || "";
  form.enabled = true;
  dialogVisible.value = true;
};

const openEditDialog = (channel: NotificationChannel) => {
  selectedType.value = channel.type;
  editingChannel.value = channel;
  form.name = channel.name;
  form.config = JSON.stringify(channel.config || {}, null, 2);
  form.enabled = channel.enabled;
  dialogVisible.value = true;
};

const fillConfigTemplate = () => {
  const template = getSelectedTypeTemplate();
  if (!template) {
    return;
  }
  form.config = template;
  ElMessage.success("已填入配置模板");
};

const formatConfigJson = () => {
  if (!form.config.trim()) {
    ElMessage.warning("请先输入配置内容");
    return;
  }

  try {
    form.config = JSON.stringify(JSON.parse(form.config), null, 2);
    ElMessage.success("JSON 已格式化");
  } catch {
    ElMessage.error("当前内容不是有效的 JSON");
  }
};

const copyConfigTemplate = async () => {
  const template = getSelectedTypeTemplate();
  if (!template) {
    ElMessage.warning("当前渠道没有可复制的模板");
    return;
  }

  try {
    await navigator.clipboard.writeText(template);
    ElMessage.success("模板已复制");
  } catch {
    ElMessage.error("复制失败，请手动复制");
  }
};

const handleSubmit = async () => {
  if (!form.name.trim()) {
    ElMessage.warning("请输入渠道名称");
    return;
  }
  if (!selectedType.value) return;

  let config: Record<string, unknown> = {};
  if (form.config.trim()) {
    try {
      config = JSON.parse(form.config) as Record<string, unknown>;
    } catch {
      ElMessage.error("配置 JSON 格式错误");
      return;
    }
  }

  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      type: selectedType.value,
      config,
      enabled: form.enabled,
    };

    if (editingChannel.value) {
      await updateNotificationChannel(editingChannel.value.id, payload);
      ElMessage.success("渠道已更新");
    } else {
      await addNotificationChannel(payload);
      ElMessage.success("渠道已添加");
    }

    closeDialog();
    await loadChannels();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const handleToggleEnabled = async (channel: NotificationChannel) => {
  try {
    await updateNotificationChannel(channel.id, {
      name: channel.name,
      config: channel.config,
      enabled: !channel.enabled,
    });
    ElMessage.success(channel.enabled ? "渠道已禁用" : "渠道已启用");
    await loadChannels();
  } catch {
    ElMessage.error("操作失败");
  }
};

const handleDelete = async (channel: NotificationChannel) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除通知渠道“${channel.name}”吗？`,
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

  try {
    await deleteNotificationChannel(channel.id);
    ElMessage.success("删除成功");
    await loadChannels();
  } catch {
    ElMessage.error("删除失败");
  }
};

const handleTest = async (channel: NotificationChannel) => {
  testingChannelId.value = channel.id;
  try {
    const result = await testNotificationChannel(channel.id);
    if (result.success) {
      ElMessage.success(result.message || "测试消息发送成功");
    } else {
      ElMessage.warning(result.message || "测试发送失败");
    }
  } finally {
    testingChannelId.value = "";
  }
};

onMounted(async () => {
  await loadChannels();
});
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">通知渠道</h1>
        <p class="page-description">管理钉钉、飞书、邮件、Webhook 等通知渠道，为消息通知页提供可绑定的发送通道。</p>
      </div>
      <div class="page-actions">
        <el-button :icon="RefreshRight" @click="loadChannels">刷新</el-button>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">当前已配置 {{ configuredCount }} 个通知渠道</div>
        <el-tag type="primary" effect="plain">配置后可在消息通知页面绑定账号</el-tag>
      </div>

      <div class="channel-grid">
        <div
          v-for="item in channelTypes"
          :key="item.type"
          class="channel-type-card"
          :class="{ configured: Boolean(getChannelByType(item.type)) }"
        >
          <div class="channel-type-top">
            <div class="channel-type-icon">
              <el-icon>
                <component
                  :is="
                    item.type === 'email'
                      ? Message
                      : item.type === 'webhook'
                        ? Share
                        : item.type === 'telegram'
                          ? Promotion
                          : item.type === 'bark'
                            ? Bell
                            : item.type === 'qq'
                              ? Connection
                              : Setting
                  "
                />
              </el-icon>
            </div>
            <div>
              <div class="channel-type-title">{{ item.label }}</div>
              <div class="channel-type-desc">{{ item.desc }}</div>
            </div>
          </div>

          <div v-if="getChannelByType(item.type)" class="channel-type-actions">
            <el-button size="small" @click="openEditDialog(getChannelByType(item.type)!)">
              编辑
            </el-button>
            <el-button
              size="small"
              :type="getChannelByType(item.type)?.enabled ? 'success' : 'info'"
              plain
              @click="handleToggleEnabled(getChannelByType(item.type)!)"
            >
              {{ getChannelByType(item.type)?.enabled ? "已启用" : "已禁用" }}
            </el-button>
          </div>

          <el-button
            v-else
            type="primary"
            plain
            size="small"
            :icon="Plus"
            @click="openCreateDialog(item.type)"
          >
            配置
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">已配置渠道列表</div>
        <el-input
          v-model="filterKeyword"
          class="channel-filter"
          clearable
          :prefix-icon="Search"
          placeholder="搜索渠道名称或类型"
        />
      </div>

      <el-table
        v-loading="loading"
        :data="filteredChannels"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column prop="name" label="渠道名称" min-width="180" />
        <el-table-column label="渠道类型" min-width="140">
          <template #default="{ row }">
            <span>{{ channelTypes.find((item) => item.type === row.type)?.label || row.type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain">
              {{ row.enabled ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-button link type="success" :icon="SwitchButton" @click="handleToggleEnabled(row)">
                {{ row.enabled ? "禁用" : "启用" }}
              </el-button>
              <el-button
                link
                :icon="Promotion"
                :loading="testingChannelId === row.id"
                @click="handleTest(row)"
              >
                测试
              </el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无通知渠道，请先配置通知方式" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingChannel ? '编辑通知渠道' : '新增通知渠道'"
      width="720px"
      destroy-on-close
      @closed="closeDialog"
    >
      <el-form label-position="top">
        <el-form-item label="渠道名称">
          <el-input
            v-model="form.name"
            :placeholder="selectedType ? `如：${channelTypes.find((item) => item.type === selectedType)?.label}` : '请输入渠道名称'"
          />
        </el-form-item>

        <el-form-item label="渠道类型">
          <el-tag type="primary" effect="plain">
            {{ channelTypes.find((item) => item.type === selectedType)?.label || "-" }}
          </el-tag>
        </el-form-item>

        <el-form-item label="配置 JSON">
          <div class="config-actions">
            <el-button link :icon="MagicStick" @click="fillConfigTemplate">填入模板</el-button>
            <el-button link :icon="DocumentCopy" @click="copyConfigTemplate">复制模板</el-button>
            <el-button link :icon="Edit" @click="formatConfigJson">格式化 JSON</el-button>
          </div>
          <el-input
            v-model="form.config"
            type="textarea"
            :rows="8"
            :placeholder="channelTypes.find((item) => item.type === selectedType)?.placeholder"
          />
        </el-form-item>

        <el-form-item label="启用此渠道">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.channel-filter {
  width: 260px;
  max-width: 100%;
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.channel-type-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
}

.channel-type-card.configured {
  border-color: rgba(59, 130, 246, 0.26);
  background: rgba(239, 246, 255, 0.8);
}

.channel-type-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.channel-type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
  font-size: 18px;
}

.channel-type-title {
  color: #0f172a;
  font-weight: 600;
}

.channel-type-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.channel-type-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.config-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
</style>
