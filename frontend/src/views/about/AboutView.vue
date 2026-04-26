<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  Bell,
  ChatDotRound,
  Connection,
  Discount,
  CreditCard,
  DataBoard,
  Goods,
  Link,
  Monitor,
  PictureRounded,
  Promotion,
  Service,
  UserFilled,
} from "@element-plus/icons-vue";

const previewImage = ref("");
const previewVisible = ref(false);
const version = ref("加载中...");
const unavailableImages = ref<string[]>([]);

const features = [
  { title: "多账号管理", desc: "同时管理多个账号", icon: UserFilled },
  { title: "智能回复", desc: "关键词自动回复", icon: ChatDotRound },
  { title: "AI 助手", desc: "复杂场景下辅助生成回复", icon: Service },
  { title: "商品管理", desc: "统一管理商品信息", icon: Goods },
  { title: "自动发货", desc: "支持卡密发货", icon: Promotion },
  { title: "通知推送", desc: "支持多渠道通知", icon: Bell },
  { title: "数据统计", desc: "账号订单汇总分析", icon: DataBoard },
];

const groupImages = [
  { title: "微信群", path: "/static/wechat-group.png", icon: ChatDotRound },
  { title: "QQ群", path: "/static/qq-group.png", icon: Connection },
];

const contributors = [
  {
    name: "zhinianboke",
    role: "项目作者",
    url: "https://github.com/zhinianboke",
  },
  {
    name: "legeling",
    role: "前端重构",
    url: "https://github.com/legeling",
  },
];

const projectLinks = [
  {
    title: "GitHub 仓库",
    desc: "查看源码、Issue 和发布记录",
    url: "https://github.com/zhinianboke/xianyu-auto-reply",
    icon: Link,
  },
  {
    title: "划算云服务器",
    desc: "项目文档中关联的外部站点",
    url: "https://www.hsykj.com",
    icon: Monitor,
  },
];

const badges = computed(() => [
  { label: version.value, type: "success" as const },
  { label: "Vue 3 + Element Plus", type: "primary" as const },
  { label: "多账号自动化", type: "warning" as const },
]);

const openPreview = (path: string) => {
  previewImage.value = path;
  previewVisible.value = true;
};

const markImageUnavailable = (path: string) => {
  if (!unavailableImages.value.includes(path)) {
    unavailableImages.value.push(path);
  }
};

const isImageUnavailable = (path: string) => unavailableImages.value.includes(path);

onMounted(async () => {
  try {
    const response = await fetch("/static/version.txt");
    if (!response.ok) {
      version.value = "未知版本";
      return;
    }
    const text = await response.text();
    if (text.trim().startsWith("v")) {
      version.value = text.trim();
    } else {
      version.value = "未知版本";
    }
  } catch {
    version.value = "未知版本";
  }
});
</script>

<template>
  <div class="about-page">
    <section class="hero-card">
      <div class="hero-icon">
        <el-icon><CreditCard /></el-icon>
      </div>
      <h1>闲鱼自动回复管理系统</h1>
      <p>智能管理闲鱼店铺的账号、商品、回复、发货与通知流程。</p>
      <div class="hero-badges">
        <el-tag
          v-for="badge in badges"
          :key="badge.label"
          size="large"
          :type="badge.type"
          effect="plain"
        >
          {{ badge.label }}
        </el-tag>
      </div>
    </section>

    <section class="app-page">
      <div class="about-grid">
        <el-card v-for="group in groupImages" :key="group.title" shadow="never">
          <template #header>
            <div class="card-title">
              <el-icon><component :is="group.icon" /></el-icon>
              <span>{{ group.title }}</span>
            </div>
          </template>
          <div class="group-card-body">
            <div
              v-if="!isImageUnavailable(group.path)"
              class="group-image-wrap"
              @click="openPreview(group.path)"
            >
              <img
                :src="group.path"
                :alt="group.title"
                class="group-image"
                @error="markImageUnavailable(group.path)"
              />
            </div>
            <el-empty v-else :image-size="88" description="二维码未配置" />
            <div class="text-muted">点击二维码可放大预览</div>
          </div>
        </el-card>
      </div>

      <el-card shadow="never">
        <template #header>
          <div class="card-title">
            <el-icon><PictureRounded /></el-icon>
            <span>核心能力</span>
          </div>
        </template>
        <div class="feature-grid">
          <div v-for="feature in features" :key="feature.title" class="feature-card">
            <div class="feature-icon">
              <el-icon><component :is="feature.icon" /></el-icon>
            </div>
            <div>
              <div class="feature-title">{{ feature.title }}</div>
              <div class="text-muted">{{ feature.desc }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-title">
            <el-icon><Discount /></el-icon>
            <span>贡献者</span>
          </div>
        </template>
        <div class="contributor-grid">
          <a
            v-for="contributor in contributors"
            :key="contributor.name"
            :href="contributor.url"
            target="_blank"
            rel="noreferrer"
            class="contributor-card"
          >
            <div class="contributor-name">{{ contributor.name }}</div>
            <div class="text-muted">{{ contributor.role }}</div>
          </a>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-title">
            <el-icon><Connection /></el-icon>
            <span>相关链接</span>
          </div>
        </template>
        <div class="link-grid">
          <a
            v-for="link in projectLinks"
            :key="link.title"
            :href="link.url"
            target="_blank"
            rel="noreferrer"
            class="link-card"
          >
            <div class="link-card-title">
              <el-icon><component :is="link.icon" /></el-icon>
              <span>{{ link.title }}</span>
            </div>
            <div class="text-muted">{{ link.desc }}</div>
          </a>
        </div>
      </el-card>

      <div class="about-footer">Made for the open source community.</div>
    </section>

    <el-dialog
      v-model="previewVisible"
      title="二维码预览"
      width="420px"
      align-center
      destroy-on-close
    >
      <img v-if="previewImage" :src="previewImage" alt="预览图" class="preview-image" />
    </el-dialog>
  </div>
</template>

<style scoped>
.about-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  padding: 36px 24px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 30%),
    linear-gradient(135deg, #eff6ff, #f8fafc);
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  font-size: 28px;
}

.hero-card h1 {
  margin: 0;
  color: #0f172a;
  font-size: 32px;
}

.hero-card p {
  margin: 10px 0 18px;
  color: #64748b;
}

.hero-badges {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.about-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.group-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  text-align: center;
}

.group-image-wrap {
  width: 180px;
  height: 180px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  cursor: pointer;
}

.group-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: #f8fafc;
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: #fff;
  color: #2563eb;
  box-shadow: 0 8px 24px -18px rgba(15, 23, 42, 0.48);
}

.feature-title {
  color: #0f172a;
  font-weight: 600;
}

.link-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.contributor-grid,
.link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.contributor-card,
.link-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 12px;
  background: #eff6ff;
}

.contributor-card {
  border-color: rgba(148, 163, 184, 0.2);
  background: #f8fafc;
}

.contributor-name,
.link-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0f172a;
  font-weight: 600;
}

.preview-image {
  width: 100%;
  border-radius: 16px;
}

.about-footer {
  text-align: center;
  color: #64748b;
  font-size: 13px;
}
</style>
