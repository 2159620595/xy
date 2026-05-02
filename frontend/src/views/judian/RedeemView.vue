<template>
  <div class="redeem-page">
    <header class="redeem-page__topbar">
      <div class="redeem-page__brand">
        <div class="redeem-page__brand-mark">聚</div>
        <div>
          <div class="redeem-page__brand-title">聚点扫码解锁 VIP</div>
          <div class="redeem-page__brand-subtitle">
            公开兑换页 · 摄像头扫码购买
          </div>
        </div>
      </div>
      <div class="redeem-page__status-pill">
        <span class="redeem-page__status-dot" />
        服务在线
      </div>
    </header>

    <main class="redeem-page__main">
      <section v-if="state === 'loading'" class="panel panel--loading">
        <div class="skeleton skeleton--title" />
        <div class="skeleton skeleton--text" />
        <div class="skeleton skeleton--grid" />
      </section>

      <section v-else-if="state === 'error'" class="panel panel--error">
        <div class="error-code">{{ errCode }}</div>
        <div class="error-title">页面暂时无法展示</div>
        <div class="error-message">{{ errMsg }}</div>
        <button class="action-button action-button--primary" @click="loadPage">
          重新检测
        </button>
      </section>

      <template v-else>
        <section class="panel hero-panel">
          <div>
            <div class="eyebrow">聚点卡密已校验</div>
            <h1 class="hero-title">
              {{ redeemInfo.account.displayName || "未命名聚点账号" }}
            </h1>
            <p class="hero-desc">
              绑定账号：{{ redeemInfo.account.accountId || "—" }}
              <span class="hero-sep">·</span>
              卡密状态：{{ cardStatusText }}
              <span class="hero-sep">·</span>
              解锁会话：{{ sessionStatusText }}
            </p>
          </div>
          <div class="hero-badge" :class="heroBadgeClass">
            {{ accountStatusText }}
          </div>
        </section>

        <section class="stats-grid">
          <article class="panel stat-card">
            <div class="stat-label">剩余时间</div>
            <div
              class="stat-value"
              :class="{ 'stat-value--danger': countdown === '已过期' }"
            >
              {{ countdown }}
            </div>
            <div class="stat-help">{{ countdownHelpText }}</div>
          </article>

          <article class="panel stat-card">
            <div class="stat-label">剩余额度（钻石）</div>
            <div
              class="stat-value"
              :title="usedDiamondText + ' / ' + totalDiamondText"
            >
              {{ remainingDiamondText }}
            </div>
            <div class="stat-progress">
              <div
                class="stat-progress__bar"
                :style="{ width: remainingPercent + '%' }"
              />
            </div>
            <div class="stat-meta">
              <span>{{ usedDiamondText }}</span>
              <span class="stat-meta__sep">/</span>
              <span>{{ totalDiamondText }}</span>
              <button
                class="stat-action"
                :disabled="syncingState"
                @click="syncCurrentState"
              >
                {{ syncingState ? "同步中…" : "同步额度" }}
              </button>
            </div>
          </article>
        </section>

        <section class="scan-layout">
          <article class="panel scan-panel">
            <div class="panel-title">扫码解锁</div>
            <div class="scan-panel__desc">
              打开你要解锁的 App /
              页面，展示购买二维码后，点击下方按钮调用后置摄像头扫码；识别到有效订单后，系统会立即使用已保存的远端
              token 自动扣钻。
            </div>

            <div
              class="scan-status-card"
              :class="{ 'scan-status-card--success': isUnlockCompleted }"
            >
              <div class="scan-status-card__label">当前会话状态</div>
              <div class="scan-status-card__value">{{ sessionStatusText }}</div>
              <div class="scan-status-card__help">{{ sessionMessage }}</div>
            </div>

            <div
              v-if="displayedResultMessage"
              class="result-message result-message--inline"
            >
              {{ displayedResultMessage }}
            </div>

            <div
              v-if="currentBatchTask"
              class="batch-progress-card"
              :class="`batch-progress-card--${batchStatusClass}`"
            >
              <div class="batch-progress-card__header">
                <div>
                  <div class="scan-status-card__label">批量下单进度</div>
                  <div class="batch-progress-card__title">
                    {{ batchStatusText }}
                  </div>
                </div>
                <div class="batch-progress-card__header-actions">
                  <div class="batch-progress-card__meta">
                    {{ batchProgressText }}
                  </div>
                  <button
                    v-if="canCancelBatchTask"
                    class="action-button action-button--danger batch-progress-card__action"
                    :disabled="batchCancelling"
                    @click="cancelBatchTask"
                  >
                    {{ batchCancelling ? "正在取消..." : "取消任务" }}
                  </button>
                </div>
              </div>
              <div class="batch-progress-card__desc">
                {{ currentBatchTask.message || "等待批量任务开始处理" }}
              </div>
              <div class="batch-progress-bar">
                <div
                  class="batch-progress-bar__inner"
                  :style="{ width: batchPercent + '%' }"
                />
              </div>
              <div class="batch-progress-stats">
                <span>成功 {{ batchDisplayedSuccessCount }}</span>
                <span>失败 {{ batchDisplayedFailedCount }}</span>
                <span v-if="batchDisplayedCanceledCount > 0"
                  >已取消 {{ batchDisplayedCanceledCount }}</span
                >
                <span>待处理 {{ batchDisplayedPendingCount }}</span>
                <span v-if="batchRequiredDiamond > 0"
                  >预计 {{ batchRequiredText }}</span
                >
                <span>累计 {{ batchConsumedText }}</span>
              </div>
              <div
                v-if="currentBatchTask.currentTradeNo"
                class="batch-progress-current"
              >
                当前单号：{{ currentBatchTask.currentTradeNo }}
              </div>
              <div v-if="batchItems.length" class="batch-progress-list">
                <div
                  v-for="item in batchItems"
                  :key="`${item.index}-${item.tradeNo || item.orderNo || 'empty'}`"
                  class="batch-progress-item"
                  :class="`batch-progress-item--${getBatchItemDisplayStatus(item)}`"
                >
                  <div class="batch-progress-item__top">
                    <span>第 {{ item.index }} 单</span>
                    <span>{{ getBatchItemStatusText(item) }}</span>
                  </div>
                  <div class="batch-progress-item__code">
                    {{
                      item.tradeNo ||
                      item.orderNo ||
                      (item.status === "failed" ? "未创建订单" : "未识别单号")
                    }}
                  </div>
                  <div class="batch-progress-item__message">
                    {{ item.message || "等待处理" }}
                  </div>
                  <details
                    v-if="item.detailText"
                    class="batch-progress-item__detail"
                  >
                    <summary class="batch-progress-item__detail-summary">
                      查看成功详情
                    </summary>
                    <pre class="batch-progress-item__raw">{{
                      item.detailText
                    }}</pre>
                  </details>
                  <div
                    v-if="item.consumedDiamond > 0"
                    class="batch-progress-item__message"
                  >
                    本单扣钻：{{ item.consumedDiamond }} 钻
                  </div>
                </div>
              </div>
            </div>

            <div v-if="currentOrder" class="mini-order-grid">
              <div class="mini-order-item">
                <span class="order-label">订单号</span>
                <span class="order-value order-value--mono">{{
                  currentOrder.tradeNo || currentOrder.orderId || "—"
                }}</span>
              </div>
              <div class="mini-order-item">
                <span class="order-label">需支付钻石</span>
                <span class="order-value order-value--accent"
                  >{{ currentOrder.diamond || 0 }} 钻</span
                >
              </div>
              <div class="mini-order-item">
                <span class="order-label">订单状态</span>
                <span class="order-value">{{ orderStatusText }}</span>
              </div>
              <div class="mini-order-item">
                <span class="order-label">备注</span>
                <span class="order-value">{{
                  currentOrder.remark || "暂无备注"
                }}</span>
              </div>
            </div>

            <button
              class="action-button action-button--primary scan-primary-button"
              :disabled="
                cameraBusy ||
                scanSubmitting ||
                batchSubmitting ||
                isBatchBusy ||
                isCardReadOnly
              "
              @click="openCamera"
            >
              {{
                cameraBusy
                  ? "摄像头启动中..."
                  : isBatchCanceling
                    ? "批量任务取消中"
                    : isBatchRunning
                      ? "批量下单进行中"
                      : "打开后置摄像头扫码"
              }}
            </button>

            <div class="actions-row actions-row--stack">
              <button
                class="action-button action-button--primary action-button--secondary"
                :disabled="
                  isCardReadOnly ||
                  scanSubmitting ||
                  batchSubmitting ||
                  batchCancelling ||
                  isBatchCanceling
                "
                @click="handleBatchPrimaryAction"
              >
                {{
                  batchSubmitting
                    ? "批量下单提交中..."
                    : batchCancelling
                      ? "正在取消批量任务..."
                      : canCancelBatchTask
                        ? "取消批量任务"
                        : isBatchCanceling
                          ? "批量任务取消中..."
                          : isBatchRunning
                            ? "批量任务执行中..."
                            : "批量下单"
                }}
              </button>
              <button
                class="action-button"
                :disabled="pageRefreshing || isCardReadOnly"
                @click="refreshSession"
              >
                {{ pageRefreshing ? "创建中..." : "新建会话" }}
              </button>
            </div>

            <div
              class="upload-dropzone"
              :class="{
                'upload-dropzone--disabled':
                  scanSubmitting ||
                  batchSubmitting ||
                  isBatchBusy ||
                  isCardReadOnly,
              }"
              @click="openQrImagePicker"
            >
              <div class="upload-dropzone__icon">⌁</div>
              <div class="upload-dropzone__title">
                {{
                  scanSubmitting ? "图片识别中..." : "点击这里识别或上传图片"
                }}
              </div>
              <div class="upload-dropzone__tip">
                支持从相册选择聚点购买二维码图片，识别成功后会自动提交订单并继续扣钻
              </div>
            </div>
            <input
              ref="qrImageInputRef"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleQrImageChange"
            />

            <div class="paste-panel">
              <div class="paste-panel__title">粘贴二维码</div>
              <div class="paste-panel__desc">
                支持直接粘贴二维码链接/文本，也支持从剪贴板粘贴二维码图片。
              </div>
              <textarea
                v-model.trim="pastedQrText"
                class="paste-panel__textarea"
                placeholder="在这里粘贴二维码链接、tradeNo、orderNo，或直接 Ctrl+V / 长按粘贴二维码图片"
                :disabled="
                  isCardReadOnly ||
                  scanSubmitting ||
                  batchSubmitting ||
                  isBatchBusy ||
                  clipboardReading
                "
                @paste="handlePasteIntoTextarea"
              />
              <div class="actions-row">
                <button
                  class="action-button"
                  :disabled="
                    isCardReadOnly ||
                    scanSubmitting ||
                    batchSubmitting ||
                    isBatchBusy ||
                    clipboardReading ||
                    !pastedQrText
                  "
                  @click="submitPastedQrText"
                >
                  {{ scanSubmitting ? "识别中..." : "提交粘贴内容" }}
                </button>
                <button
                  class="action-button"
                  :disabled="
                    scanSubmitting ||
                    batchSubmitting ||
                    isBatchBusy ||
                    clipboardReading
                  "
                  @click="readClipboardPayload"
                >
                  {{ clipboardReading ? "读取剪贴板中..." : "读取剪贴板" }}
                </button>
              </div>
            </div>
          </article>
        </section>
      </template>
    </main>

    <Teleport to="body">
      <div
        class="camera-overlay"
        :class="{ 'camera-overlay--show': showCameraModal }"
        @click.self="closeCamera"
      >
        <div class="camera-modal">
          <div class="camera-modal__header">
            <div>
              <div class="camera-modal__title">后置摄像头扫码</div>
              <div class="camera-modal__subtitle">请把镜头对准购买二维码</div>
            </div>
            <button class="camera-modal__close" @click="closeCamera">×</button>
          </div>
          <div class="camera-frame">
            <video
              ref="videoRef"
              autoplay
              playsinline
              webkit-playsinline
              muted
              class="camera-frame__video"
            />
            <div class="camera-frame__mask"></div>
            <div class="camera-frame__line"></div>
          </div>
          <div class="camera-tip">{{ cameraTip }}</div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        class="confirm-overlay"
        :class="{ 'confirm-overlay--show': showBatchOrderModal }"
        @click.self="closeBatchOrderModal"
      >
        <div class="confirm-modal">
          <div class="confirm-modal__header">
            <div>
              <div class="confirm-modal__title">批量下单</div>
              <div class="confirm-modal__subtitle">
                输入动漫共和国账号密码，选择快捷数量后即可批量下单
              </div>
            </div>
            <button
              class="confirm-modal__close"
              :disabled="batchSubmitting || isBatchBusy"
              @click="closeBatchOrderModal"
            >
              ×
            </button>
          </div>

          <label class="batch-order-field">
            <span class="batch-order-field__label">动漫共和国账号</span>
            <input
              v-model.trim="batchOrderAccount"
              class="batch-order-field__input"
              type="text"
              autocomplete="username"
              :disabled="batchSubmitting || isBatchBusy"
            />
          </label>

          <label class="batch-order-field">
            <span class="batch-order-field__label">动漫共和国密码</span>
            <input
              v-model="batchOrderPassword"
              class="batch-order-field__input"
              type="password"
              autocomplete="current-password"
              :disabled="batchSubmitting || isBatchBusy"
              @keydown.enter.prevent="submitBatchOrder"
            />
          </label>

          <div class="batch-order-field">
            <span class="batch-order-field__label">下单数量</span>
            <div class="batch-package-options">
              <button
                v-for="option in BATCH_PACKAGE_OPTIONS"
                :key="option.value"
                type="button"
                class="batch-package-option"
                :class="{
                  'batch-package-option--active':
                    batchCountPreset === option.value,
                }"
                :disabled="batchSubmitting || isBatchBusy"
                @click="applyBatchCountPreset(option)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <label v-if="batchCountPreset === 'custom'" class="batch-order-field">
            <span class="batch-order-field__label">自定义数量</span>
            <input
              v-model.number="batchOrderCount"
              class="batch-order-field__input"
              type="number"
              min="1"
              max="365"
              step="1"
              inputmode="numeric"
              placeholder="请输入天卡数量"
              :disabled="batchSubmitting || isBatchBusy"
              @change="handleBatchCountCommit"
              @blur="handleBatchCountCommit"
              @keydown.enter.prevent="handleBatchCountCommit"
            />
          </label>

          <div class="batch-preview-card">
            <div class="batch-preview-card__title">下单预估</div>
            <div class="batch-preview-grid">
              <div class="batch-preview-item">
                <span class="order-label">当前剩余额度</span>
                <span class="order-value">{{ batchRemainingQuotaText }}</span>
              </div>
              <div class="batch-preview-item">
                <span class="order-label">当前选择</span>
                <span class="order-value">{{ batchSelectedTypeText }}</span>
              </div>
              <div class="batch-preview-item">
                <span class="order-label">预计预扣</span>
                <span class="order-value order-value--accent">{{
                  batchPreviewRequiredText
                }}</span>
              </div>
            </div>
            <div
              class="batch-preview-card__hint"
              :class="batchPreviewHintClass"
            >
              {{ batchPreviewHintText }}
            </div>
          </div>

          <div class="actions-row confirm-actions">
            <button
              class="action-button"
              :disabled="batchSubmitting || isBatchBusy"
              @click="closeBatchOrderModal"
            >
              取消
            </button>
            <button
              class="action-button action-button--primary"
              :disabled="
                batchSubmitting ||
                isBatchBusy ||
                batchPreviewLoading ||
                !batchCanSubmit
              "
              @click="submitBatchOrder"
            >
              {{
                batchSubmitting
                  ? "批量下单提交中..."
                  : isBatchCanceling
                    ? "批量任务取消中..."
                    : isBatchRunning
                      ? "批量任务执行中..."
                      : batchPreviewLoading
                        ? "正在校验额度..."
                        : "立即开始"
              }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        class="confirm-overlay"
        :class="{ 'confirm-overlay--show': showConfirmModal }"
        @click.self="closeConfirmModal"
      >
        <div class="confirm-modal">
          <div class="confirm-modal__header">
            <div>
              <div class="confirm-modal__title">重新自动扣钻</div>
              <div class="confirm-modal__subtitle">
                确认后会校验订单信息，并立即使用已保存的远端 token 自动支付
              </div>
            </div>
            <button
              class="confirm-modal__close"
              :disabled="confirmSubmitting"
              @click="closeConfirmModal"
            >
              ×
            </button>
          </div>

          <div class="confirm-card">
            <div class="confirm-card__amount">重新尝试该订单？</div>
            <div class="confirm-card__desc">{{ confirmDialogDescription }}</div>
          </div>

          <div class="confirm-grid">
            <div class="order-item">
              <span class="order-label">应用</span>
              <span class="order-value">{{
                currentOrder?.appName || currentOrder?.itemTitle || "未知应用"
              }}</span>
            </div>
            <div class="order-item">
              <span class="order-label">账户当前余额</span>
              <span class="order-value">{{ liveAccountDiamondText }}</span>
            </div>
            <div class="order-item order-item--full">
              <span class="order-label">订单备注</span>
              <span class="order-value">{{
                currentOrder?.remark || "暂无备注"
              }}</span>
            </div>
          </div>

          <div class="actions-row confirm-actions">
            <button
              class="action-button"
              :disabled="confirmSubmitting"
              @click="closeConfirmModal"
            >
              取消
            </button>
            <button
              class="action-button action-button--primary"
              :disabled="confirmSubmitting"
              @click="confirmOrder"
            >
              {{ confirmSubmitting ? "正在自动扣钻..." : "立即重试" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div class="toast" :class="{ 'toast--show': toastVisible }">
        {{ toastMessage }}
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        class="pay-result-overlay"
        :class="{ 'pay-result-overlay--show': showPayResult }"
        @click.self="closePayResult"
      >
        <div class="pay-result-modal">
          <div class="pay-result__header">
            <div>
              <div class="pay-result__title">扣钻完成</div>
              <div class="pay-result__subtitle">以下为本次扣钻详情</div>
            </div>
            <button class="pay-result__close" @click="closePayResult">×</button>
          </div>
          <div class="pay-result-grid">
            <div class="pay-result-item">
              <span class="label">应用</span
              ><span class="value">{{
                currentOrder?.appName || currentOrder?.itemTitle || "未知应用"
              }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">支付结果</span
              ><span class="value">{{ payResultStatusText }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">支付单号</span
              ><span class="value value--mono">{{
                currentOrder?.tradeNo || currentOrder?.orderId || "—"
              }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">业务单号</span
              ><span class="value value--mono">{{
                currentOrder?.orderNo || "—"
              }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">本次消耗</span
              ><span class="value value--accent">{{
                consumedDiamondText
              }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">扣前余额</span
              ><span class="value">{{ beforeDiamondText }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">扣后余额</span
              ><span class="value">{{ afterDiamondText }}</span>
            </div>
            <div class="pay-result-item">
              <span class="label">订单时间</span
              ><span class="value">{{
                currentOrder?.createTime || currentSession?.confirmedAt || "—"
              }}</span>
            </div>
            <div class="pay-result-item pay-result-item--full">
              <span class="label">扫码返回</span
              ><span class="value">{{ scanResultMessage || "—" }}</span>
            </div>
            <div class="pay-result-item pay-result-item--full">
              <span class="label">备注</span
              ><span class="value">{{ resultMessage || "—" }}</span>
            </div>
          </div>
          <div class="pay-result-actions">
            <button class="action-button" @click="closePayResult">
              知道了
            </button>
            <button
              class="action-button action-button--primary"
              :disabled="pageRefreshing"
              @click="refreshSession"
            >
              {{ pageRefreshing ? "刷新中…" : "刷新会话" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { judianApi } from "@/api/judian";

const route = useRoute();
const router = useRouter();

const state = ref("loading");

const errCode = ref(404);
const errMsg = ref("");
const nowTimestamp = ref(Math.floor(Date.now() / 1000));
const toastMessage = ref("");
const toastVisible = ref(false);
const redeemInfo = ref(createEmptyRedeemInfo());
const pageRefreshing = ref(false);
const syncingState = ref(false);
const scanSubmitting = ref(false);
const batchSubmitting = ref(false);
const batchCancelling = ref(false);
const confirmSubmitting = ref(false);
const cameraBusy = ref(false);
const clipboardReading = ref(false);

const showCameraModal = ref(false);
const showBatchOrderModal = ref(false);
const showConfirmModal = ref(false);
const DEFAULT_BATCH_PACKAGE_TYPE = "day";
const BATCH_PACKAGE_OPTIONS = [
  { label: "天卡", value: "day", count: 1 },
  { label: "周卡", value: "week", count: 7 },
  { label: "月卡", value: "month", count: 30 },
  { label: "季卡", value: "quarter", count: 90 },
  { label: "年卡", value: "year", count: 365 },
  { label: "自定义", value: "custom", count: 0 },
];
const batchCountPreset = ref("day");
const batchOrderCount = ref(1);
const batchOrderAccount = ref("");
const batchOrderPassword = ref("");
const batchPreviewLoading = ref(false);
const batchPreview = ref(createEmptyBatchPreview());
const cameraTip = ref("请将摄像头对准聚点购买二维码");
const videoRef = ref(null);
const qrImageInputRef = ref(null);
const showPayResult = ref(false);
const pastedQrText = ref("");

const DEFAULT_POLL_INTERVAL_MS = 10000;
const BATCH_RUNNING_POLL_INTERVAL_MS = 5000;

let clockTimer = null;
let toastTimer = null;
let cameraStream = null;
let cameraAnimation = null;
let liveSyncTimer = null;
let lastPayResultKey = "";
let qrDecoder = null;
let qrDecoderPromise = null;

const currentSession = computed(() => redeemInfo.value.session || null);
const currentSessionId = computed(() =>
  String(currentSession.value?.sessionId || ""),
);
const currentOrder = computed(() => currentSession.value?.order || null);
const currentBatchTask = computed(() => redeemInfo.value.batchTask || null);
const batchItems = computed(() =>
  Array.isArray(currentBatchTask.value?.items)
    ? currentBatchTask.value.items
    : [],
);
const resultPayload = computed(() => currentSession.value?.resultPayload || {});
const resultMessage = computed(
  () => resultPayload.value?.rendered_message || "",
);
const scanResultMessage = computed(() =>
  String(resultPayload.value?.scanResult?.message || ""),
);
const payResultStatusText = computed(() =>
  isConfirmedUnlockSuccess(resultPayload.value) ? "已确认成功" : "处理中",
);
function hasExplicitJudianPaySuccess(payPayload) {
  return (
    payPayload &&
    typeof payPayload === "object" &&
    payPayload.success === true &&
    payPayload.settledByPolling !== true
  );
}
function hasRealDiamondDecrease(payload) {
  const consumed = Number(payload?.consumedDiamond ?? 0);
  if (consumed > 0) return true;
  const before = Number(payload?.beforeDiamond ?? -1);
  const after = Number(payload?.afterDiamond ?? payload?.diamondQuantity ?? -1);
  return before >= 0 && after >= 0 && after < before;
}
function isConfirmedUnlockSuccess(payload) {
  return (
    hasExplicitJudianPaySuccess(payload?.payPayload) &&
    hasRealDiamondDecrease(payload)
  );
}
const isBatchCanceling = computed(
  () =>
    currentBatchTask.value?.cancelRequested === true && !isBatchTerminal.value,
);
const batchTaskStatus = computed(() =>
  String(currentBatchTask.value?.status || ""),
);
const isBatchTerminal = computed(() =>
  ["completed", "failed", "canceled"].includes(batchTaskStatus.value),
);
const isBatchRunning = computed(() => batchTaskStatus.value === "running");
const isBatchBusy = computed(
  () => isBatchRunning.value || isBatchCanceling.value,
);
const liveBatchConsumedDiamond = computed(() => {
  if (!isBatchRunning.value) return 0;
  const totalConsumed = Math.max(
    0,
    Number(currentBatchTask.value?.totalConsumedDiamond || 0),
  );
  const syncedConsumed = Math.max(
    0,
    Number(currentBatchTask.value?.payload?.syncedConsumedDiamond || 0),
  );
  return Math.max(0, totalConsumed - syncedConsumed);
});
const canCancelBatchTask = computed(() => {
  const status = batchTaskStatus.value;
  if (!["pending", "running"].includes(status)) return false;
  return currentBatchTask.value?.cancelRequested !== true;
});
const isUnlockCompleted = computed(() =>
  isConfirmedUnlockSuccess(resultPayload.value),
);
const displayedResultMessage = computed(() =>
  isUnlockCompleted.value ? resultMessage.value : "",
);

const confirmDialogDescription = computed(() => {
  const order = currentOrder.value;
  if (!order)
    return "系统会先校验订单，再立即使用已保存的远端 token 自动完成扣钻。";
  const parts = [
    order.appName || order.itemTitle || "",
    order.orderNo ? `业务单号 ${order.orderNo}` : "",
    order.tradeNo ? `支付单号 ${order.tradeNo}` : "",
  ].filter(Boolean);
  return (
    parts.join(" · ") ||
    "系统会先校验订单，再立即使用已保存的远端 token 自动完成扣钻。"
  );
});

const cardStatusText = computed(() => {
  const status = String(redeemInfo.value.status || "");
  if (status === "expired") return "已过期";
  if (status === "void") return "已作废";
  if (status === "active") return "已启用";
  return "待领取";
});

const sessionStatusText = computed(() => {
  if (batchTaskStatus.value === "canceled") return "批量任务已取消";
  if (isBatchCanceling.value) return "批量任务取消中";
  if (isBatchRunning.value) return "批量下单中";
  if (isUnlockCompleted.value) return "已完成解锁";
  const status = String(currentSession.value?.status || "pending");
  if (status === "completed") return "结果待确认";
  if (status === "failed") return "处理失败";
  if (status === "confirmed") return "自动扣钻中";
  if (status === "scanned") return "已识别订单";
  return "等待扫码";
});

const sessionMessage = computed(() => {
  if (isCardReadOnly.value) {
    return `卡密已${cardInvalidReasonText.value}，当前处于 7 天存活期内，仅保留 0 权限展示，无法支付。`;
  }
  return currentSession.value?.message || "请先打开摄像头扫码";
});

const accountStatusText = computed(() => {
  const account = redeemInfo.value.account || {};
  if (account.enabled === false) return "账号已停用";
  if (account.status === "active") return "会话正常";
  if (account.status === "disabled") return "账号已停用";
  if (account.status === "pending") return "待登录";
  return "状态未知";
});

const heroBadgeClass = computed(() => {
  const text = accountStatusText.value;
  if (text === "会话正常") return "hero-badge--success";
  if (text === "账号已停用") return "hero-badge--danger";
  return "hero-badge--warning";
});

const isCardReadOnly = computed(() => redeemInfo.value.canPay === false);
const cardInvalidReasonText = computed(() => {
  const reason = String(
    redeemInfo.value.invalidReason || redeemInfo.value.status || "",
  );
  if (reason === "void") return "作废";
  if (reason === "expired") return "过期";
  return "失效";
});

const countdown = computed(() => {
  const survivalExpiresAt = Number(redeemInfo.value.survivalExpiresAt || 0);
  if (isCardReadOnly.value && survivalExpiresAt > nowTimestamp.value) {
    return `存活期 ${formatDurationText(survivalExpiresAt - nowTimestamp.value)}`;
  }
  const expiresAt = Number(redeemInfo.value.expiresAt || 0);
  if (!expiresAt) return "尚未开始";
  const left = expiresAt - nowTimestamp.value;
  if (left <= 0) return "已过期";
  return formatDurationText(left);
});

const countdownHelpText = computed(() => {
  if (!isCardReadOnly.value) return "卡密首次打开后开始计时";
  return `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天查看存活期，到期后彻底失效`;
});

const remainingDiamondText = computed(() => {
  const remainingQuota = Number(redeemInfo.value.remainingQuota);
  if (isCardReadOnly.value) return "0 钻";
  if (Number.isFinite(remainingQuota) && remainingQuota >= 0) {
    return `${Math.max(0, remainingQuota)} 钻`;
  }
  const maxUses = Number(redeemInfo.value.maxUses || 0);
  const used =
    Number(redeemInfo.value.useCount || 0) + liveBatchConsumedDiamond.value;
  if (maxUses <= 0) return "不限";
  const left = Math.max(0, maxUses - used);
  return `${left} 钻`;
});

const totalDiamondText = computed(() => {
  const maxUses = Number(redeemInfo.value.maxUses || 0);
  return maxUses > 0 ? `${maxUses} 钻` : "不限";
});

const usedDiamondText = computed(() => {
  const maxUses = Number(redeemInfo.value.maxUses || 0);
  if (isCardReadOnly.value && maxUses > 0) {
    return `${maxUses} 钻`;
  }
  const used =
    Number(redeemInfo.value.useCount || 0) + liveBatchConsumedDiamond.value;
  return `${used} 钻`;
});

const remainingPercent = computed(() => {
  if (isCardReadOnly.value) return 0;
  const maxUses = Number(redeemInfo.value.maxUses || 0);
  const used =
    Number(redeemInfo.value.useCount || 0) + liveBatchConsumedDiamond.value;
  if (maxUses <= 0) return 100;
  const left = Math.max(0, maxUses - used);
  return Math.max(0, Math.min(100, Math.round((left / maxUses) * 100)));
});
const liveAccountDiamondText = computed(() => {
  const currentDiamond = Number(redeemInfo.value.account?.diamondQuantity || 0);
  const left = Math.max(0, currentDiamond - liveBatchConsumedDiamond.value);
  return `${left} 钻`;
});

const orderStatusText = computed(() => {
  if (isUnlockCompleted.value) return "已支付";
  const status = String(currentOrder.value?.status || "");
  if (status === "completed") return "结果待确认";
  if (status === "failed") return "支付失败";
  if (status === "confirmed") return "自动支付中";
  if (status === "scanned") return "已识别";
  return currentOrder.value ? "待自动支付" : "暂无订单";
});

const canConfirmUnlock = computed(
  () =>
    !isCardReadOnly.value &&
    !isUnlockCompleted.value &&
    ["scanned", "confirmed"].includes(
      String(currentSession.value?.status || ""),
    ),
);
const batchStatusText = computed(() => {
  const status = batchTaskStatus.value;
  if (status === "canceled") return "批量任务已取消";
  if (isBatchCanceling.value) return "批量任务取消中";
  if (status === "completed") return "批量下单已完成";
  if (status === "failed") return "批量下单失败";
  if (status === "running") return "批量下单进行中";
  return "暂无批量任务";
});
const batchStatusClass = computed(() => {
  const status = batchTaskStatus.value;
  if (status === "canceled") return "warning";
  if (isBatchCanceling.value) return "warning";
  if (status === "completed") return "success";
  if (status === "failed") return "failed";
  return "running";
});
const batchPercent = computed(() => {
  const total = Number(currentBatchTask.value?.totalCount || 0);
  const processed = Number(currentBatchTask.value?.processedCount || 0);
  if (total <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((processed / total) * 100)));
});
const batchProgressText = computed(() => {
  const total = Number(currentBatchTask.value?.totalCount || 0);
  const processed = Number(currentBatchTask.value?.processedCount || 0);
  return total > 0 ? `${processed} / ${total}` : "0 / 0";
});
const batchConsumedText = computed(
  () => `${Number(currentBatchTask.value?.totalConsumedDiamond || 0)} 钻`,
);
const batchRequiredDiamond = computed(() =>
  Number(currentBatchTask.value?.requiredDiamond || 0),
);
const batchRequiredText = computed(
  () => `${Math.max(0, batchRequiredDiamond.value)} 钻`,
);
const batchDisplayedSuccessCount = computed(
  () =>
    batchItems.value.filter((item) => item.confirmedSuccess === true).length,
);
const batchDisplayedFailedCount = computed(
  () =>
    batchItems.value.filter((item) => String(item.status || "") === "failed")
      .length,
);
const batchDisplayedCanceledCount = computed(() =>
  Math.max(
    0,
    Number(currentBatchTask.value?.canceledCount || 0) ||
      batchItems.value.filter(
        (item) => String(item.status || "") === "canceled",
      ).length,
  ),
);
const batchDisplayedPendingCount = computed(() =>
  Math.max(0, Number(currentBatchTask.value?.pendingCount || 0)),
);
function getBatchItemDisplayStatus(item) {
  if (String(item?.status || "") === "canceled") return "canceled";
  if (item?.confirmedSuccess === true) return "completed";
  if (String(item?.status || "") === "failed") return "failed";
  return "pending";
}
function getBatchItemStatusText(item) {
  if (String(item?.status || "") === "canceled") return "已取消";
  if (item?.confirmedSuccess === true) return "成功";
  if (String(item?.status || "") === "failed") return "失败";
  if (String(item?.status || "") === "completed") return "待确认";
  return "处理中";
}
const batchSelectedOption = computed(
  () =>
    BATCH_PACKAGE_OPTIONS.find(
      (option) => option.value === batchCountPreset.value,
    ) || BATCH_PACKAGE_OPTIONS[0],
);
const batchSelectedTypeText = computed(() => {
  const count = Math.floor(Number(batchOrderCount.value || 0));
  if (batchCountPreset.value === "custom")
    return `自定义 ${Math.max(0, count)} 单`;
  return `${batchSelectedOption.value?.label || "天卡"} · ${Math.max(0, count)} 单`;
});
const batchRemainingQuotaText = computed(() => {
  const remainingQuota =
    Number(batchPreview.value.remainingQuota) - liveBatchConsumedDiamond.value;
  if (remainingQuota < 0) return "不限";
  return `${Math.max(0, remainingQuota)} 钻`;
});
const batchPreviewRequiredText = computed(
  () => `${Math.max(0, Number(batchPreview.value.requiredDiamond || 0))} 钻`,
);
const batchCanSubmit = computed(() => {
  const count = Math.floor(Number(batchOrderCount.value || 0));
  if (!Number.isFinite(count) || count < 1 || count > 365) return false;
  if (isCardReadOnly.value) return false;
  return batchPreview.value.canSubmit !== false;
});
const batchPreviewHintClass = computed(() => {
  if (batchPreviewLoading.value) return "";
  return batchCanSubmit.value
    ? "batch-preview-card__hint--ok"
    : "batch-preview-card__hint--danger";
});
const batchPreviewHintText = computed(() => {
  if (batchPreviewLoading.value) return "正在校验额度...";
  if (isCardReadOnly.value) {
    return `卡密已${cardInvalidReasonText.value}，当前处于 7 天存活期内，仅保留 0 权限展示，无法支付。`;
  }
  if (batchPreview.value.error) return batchPreview.value.error;
  if (batchPreview.value.canSubmit) {
    return `当前额度充足，本次预计预扣 ${batchPreviewRequiredText.value}。`;
  }
  if (batchPreview.value.enoughDiamond === false) {
    return `账号余额不足，请更换账号或减少数量。`;
  }
  if (batchPreview.value.enoughQuota === false) {
    return `卡密额度不足，本次预计预扣 ${batchPreviewRequiredText.value}，当前剩余额度 ${batchRemainingQuotaText.value}。`;
  }
  return "请输入数量后自动校验额度。";
});
const shouldAutoSync = computed(() => {
  if (state.value !== "ready" || !currentSessionId.value) return false;
  if (isBatchCanceling.value) return true;
  if (isBatchRunning.value) return true;
  return ["pending", "scanned", "confirmed"].includes(
    String(currentSession.value?.status || ""),
  );
});
const autoSyncIntervalMs = computed(() =>
  isBatchBusy.value ? BATCH_RUNNING_POLL_INTERVAL_MS : DEFAULT_POLL_INTERVAL_MS,
);

onMounted(() => {
  document.addEventListener("visibilitychange", handleVisibilityChange);
  document.addEventListener("paste", handleGlobalPaste);
  clockTimer = window.setInterval(() => {
    nowTimestamp.value = Math.floor(Date.now() / 1000);
  }, 1000);
  removeLegacyPayResultDom();
  loadPage();
});

watch(
  () => [route.query.code, route.query.session],
  () => {
    stopLiveSync();
    loadPage();
  },
);

watch(
  () => [
    state.value,
    currentSessionId.value,
    currentSession.value?.status,
    currentBatchTask.value?.status,
    currentBatchTask.value?.processedCount,
  ],
  () => {
    restartLiveSync();
  },
);

onUnmounted(() => {
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  document.removeEventListener("paste", handleGlobalPaste);
  stopLiveSync();
  if (clockTimer) {
    clearInterval(clockTimer);
    clockTimer = null;
  }
  if (toastTimer) {
    clearTimeout(toastTimer);
    toastTimer = null;
  }
  closeCamera();
});

function handleVisibilityChange() {
  if (typeof document !== "undefined" && !document.hidden) {
    if (shouldAutoSync.value) {
      syncCurrentState({ silent: true }).catch(() => {});
    }
    restartLiveSync();
  }
}

function stopLiveSync() {
  if (liveSyncTimer) {
    clearInterval(liveSyncTimer);
    liveSyncTimer = null;
  }
}

function restartLiveSync() {
  stopLiveSync();
  if (typeof window === "undefined" || !shouldAutoSync.value) return;
  liveSyncTimer = window.setInterval(() => {
    if (typeof document !== "undefined" && document.hidden) return;
    if (
      pageRefreshing.value ||
      syncingState.value ||
      scanSubmitting.value ||
      batchSubmitting.value ||
      confirmSubmitting.value
    )
      return;
    syncCurrentState({ silent: true }).catch(() => {});
  }, autoSyncIntervalMs.value);
}

function createEmptyRedeemInfo() {
  return {
    code: "",
    status: "unused",
    duration: 0,
    expiresAt: null,
    useCount: 0,
    maxUses: 0,
    remainingQuota: -1,
    canPay: true,
    invalidReason: "",
    invalidSinceAt: null,
    survivalExpiresAt: null,
    withinSurvival: true,
    remark: "",
    account: {
      accountId: "",
      displayName: "",
      status: "pending",
      enabled: true,
      diamondQuantity: 0,
      lastLoginAt: "",
      remark: "",
    },
    session: {
      sessionId: "",
      status: "pending",
      message: "请打开后置摄像头，对准聚点购买二维码完成扫码",
      orderId: "",
      qrContent: "",
      mobileLoginLink: "",
      unlockUrl: "",
      expiresAt: "",
      confirmedAt: "",
      resultPayload: {},
      order: null,
    },
    batchTask: null,
  };
}

function createEmptyBatchPreview() {
  return {
    vipId: "",
    count: 1,
    unitDiamond: 0,
    requiredDiamond: 0,
    availableDiamond: 0,
    remainingQuota: -1,
    enoughDiamond: true,
    enoughQuota: true,
    canSubmit: true,
    error: "",
  };
}

function formatDurationText(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds || 0)));
  const days = Math.floor(safeSeconds / 86400);
  const hours = Math.floor((safeSeconds % 86400) / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  const hhmmss = [hours, minutes, seconds]
    .map((item) => String(item).padStart(2, "0"))
    .join(":");
  return days > 0 ? `${days}天 ${hhmmss}` : hhmmss;
}

function normalizeOrder(order) {
  if (!order) return null;
  return {
    orderId: String(order.orderId || ""),
    tradeNo: String(order.tradeNo || order.orderId || ""),
    orderNo: String(order.orderNo || ""),
    appName: String(order.appName || ""),
    createTime: String(order.createTime || ""),
    status: String(order.status || "pending"),
    diamond: Number(order.diamond || 0),
    remark: String(order.remark || ""),
    timeOut: Number(order.timeOut || 0),
    itemTitle: String(order.itemTitle || ""),
    raw: order.raw || {},
  };
}

function normalizeSession(session) {
  const resultPayload = session?.resultPayload || {};
  return {
    sessionId: String(session?.sessionId || ""),
    status: String(session?.status || "pending"),
    message: String(
      session?.message || "请打开后置摄像头，对准聚点购买二维码完成扫码",
    ),
    orderId: String(session?.orderId || ""),
    qrContent: String(session?.qrContent || ""),
    mobileLoginLink: String(session?.mobileLoginLink || ""),
    unlockUrl: String(session?.unlockUrl || ""),
    expiresAt: String(session?.expiresAt || ""),
    confirmedAt: String(session?.confirmedAt || ""),
    resultPayload: {
      rendered_message: String(resultPayload.rendered_message || ""),
      confirmedSuccess: resultPayload.confirmedSuccess === true,
      explicitPaySuccess: resultPayload.explicitPaySuccess === true,
      balanceDecreased: resultPayload.balanceDecreased === true,
      tradeNo: String(resultPayload.tradeNo || ""),
      orderNo: String(resultPayload.orderNo || ""),
      beforeDiamond: Number(resultPayload.beforeDiamond || 0),
      afterDiamond: Number(
        resultPayload.afterDiamond ?? resultPayload.diamondQuantity ?? 0,
      ),
      consumedDiamond: Number(resultPayload.consumedDiamond || 0),
      diamondQuantity: Number(
        resultPayload.diamondQuantity || resultPayload.afterDiamond || 0,
      ),
      scanResult: {
        message: String(resultPayload.scanResult?.message || ""),
      },
      payPayload: resultPayload.payPayload || {},
      beforeFundPayload: resultPayload.beforeFundPayload || {},
      fundPayload: resultPayload.fundPayload || {},
    },
    order: normalizeOrder(session?.order),
  };
}

function normalizeBatchTask(batchTask) {
  if (!batchTask) return null;
  const items = Array.isArray(batchTask.items) ? batchTask.items : [];
  const payload = batchTask.payload || {};
  return {
    batchId: String(batchTask.batchId || ""),
    sessionId: String(batchTask.sessionId || ""),
    status: String(batchTask.status || "pending"),
    message: String(batchTask.message || ""),
    totalCount: Number(batchTask.totalCount || 0),
    processedCount: Number(batchTask.processedCount || 0),
    successCount: Number(batchTask.successCount || 0),
    failedCount: Number(batchTask.failedCount || 0),
    pendingCount: Number(batchTask.pendingCount || 0),
    canceledCount: Number(batchTask.canceledCount || 0),
    totalConsumedDiamond: Number(batchTask.totalConsumedDiamond || 0),
    currentIndex: Number(batchTask.currentIndex || 0),
    currentTradeNo: String(batchTask.currentTradeNo || ""),
    createdAt: String(batchTask.createdAt || ""),
    updatedAt: String(batchTask.updatedAt || ""),
    cancelRequested: batchTask.cancelRequested === true,
    cancelRequestedAt: String(batchTask.cancelRequestedAt || ""),
    requiredDiamond: Number(payload.requiredDiamond || 0),
    beforeDiamond: Number(payload.beforeDiamond ?? -1),
    afterDiamond: Number(payload.afterDiamond ?? -1),
    payload,
    items: items.map((item, index) => ({
      rawResponse: item?.rawResponse || {},
      detailText: formatPaymentDetail(item?.rawResponse),
      index: Number(item?.index || index + 1),
      status: String(item?.status || "pending"),
      tradeNo: String(item?.tradeNo || ""),
      orderNo: String(item?.orderNo || ""),
      message: String(item?.message || ""),
      consumedDiamond: Number(item?.consumedDiamond || 0),
      explicitPaySuccess: item?.explicitPaySuccess === true,
      balanceDecreased: item?.balanceDecreased === true,
      confirmedSuccess: item?.confirmedSuccess === true,
      sessionStatus: String(item?.sessionStatus || ""),
      orderStatus: String(item?.orderStatus || ""),
    })),
  };
}

function formatRawResponse(value) {
  if (!value || typeof value !== "object") return "";
  if (!Object.keys(value).length) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "";
  }
}

function formatPaymentDetail(payload) {
  if (!payload || typeof payload !== "object") return "";
  const orderInfo = payload?.orderInfo || {};
  const scanResult = payload?.scanResult || {};
  const detail = {};
  const confirmedSuccess = payload?.confirmedSuccess === true;
  const explicitPaySuccess = payload?.explicitPaySuccess === true;
  const balanceDecreased = payload?.balanceDecreased === true;
  const tradeNo = String(payload?.tradeNo || orderInfo?.tradeNo || "").trim();
  const orderNo = String(payload?.orderNo || orderInfo?.orderNo || "").trim();
  const consumedDiamond = Number(payload?.consumedDiamond || 0);
  const beforeDiamond = Number(
    payload?.beforeDiamond ?? payload?.beforeFund ?? -1,
  );
  const afterDiamond = Number(
    payload?.afterDiamond ?? payload?.afterFund ?? -1,
  );
  const scanMessage = String(scanResult?.message || "").trim();
  const orderRemark = String(orderInfo?.remark || "").trim();
  const orderCreateTime = String(orderInfo?.createTime || "").trim();

  detail.支付结果 = confirmedSuccess ? "已确认成功" : "待确认";
  if (consumedDiamond > 0) detail.本次消耗 = `${consumedDiamond} 钻`;
  if (tradeNo) detail.支付单号 = tradeNo;
  if (orderNo) detail.业务单号 = orderNo;
  if (orderCreateTime) detail.订单时间 = orderCreateTime;
  if (scanMessage) detail.扫码返回 = scanMessage;
  if (orderRemark) detail.订单备注 = orderRemark;
  if (explicitPaySuccess) detail.接口确认 = "成功";
  if (balanceDecreased) detail.余额校验 = "已扣减";

  return formatRawResponse(detail);
}

function mergeRedeemInfo(partial) {
  const next = { ...redeemInfo.value };

  if (partial?.code !== undefined)
    next.code = String(partial.code || next.code || "");
  if (partial?.status !== undefined)
    next.status = String(partial.status || next.status || "unused");
  if (partial?.duration !== undefined)
    next.duration = Number(partial.duration ?? next.duration ?? 0);
  if (partial?.expiresAt !== undefined)
    next.expiresAt =
      partial.expiresAt != null && partial.expiresAt !== ""
        ? Number(partial.expiresAt)
        : null;
  if (partial?.useCount !== undefined)
    next.useCount = Number(partial.useCount ?? next.useCount ?? 0);
  if (partial?.maxUses !== undefined)
    next.maxUses = Number(partial.maxUses ?? next.maxUses ?? 0);
  if (partial?.remainingQuota !== undefined)
    next.remainingQuota = Number(partial.remainingQuota ?? next.remainingQuota);
  if (partial?.canPay !== undefined) next.canPay = partial.canPay !== false;
  if (partial?.invalidReason !== undefined)
    next.invalidReason = String(partial.invalidReason || "");
  if (partial?.invalidSinceAt !== undefined)
    next.invalidSinceAt =
      partial.invalidSinceAt != null && partial.invalidSinceAt !== ""
        ? Number(partial.invalidSinceAt)
        : null;
  if (partial?.survivalExpiresAt !== undefined)
    next.survivalExpiresAt =
      partial.survivalExpiresAt != null && partial.survivalExpiresAt !== ""
        ? Number(partial.survivalExpiresAt)
        : null;
  if (partial?.withinSurvival !== undefined)
    next.withinSurvival = partial.withinSurvival !== false;

  if (partial?.remark !== undefined)
    next.remark = String(partial.remark || next.remark || "");

  if (partial?.account) {
    const account = partial.account || {};
    next.account = {
      ...next.account,
      ...(account.accountId !== undefined
        ? { accountId: String(account.accountId || "") }
        : {}),
      ...(account.displayName !== undefined
        ? { displayName: String(account.displayName || "") }
        : {}),
      ...(account.status !== undefined
        ? { status: String(account.status || "pending") }
        : {}),
      ...(account.enabled !== undefined
        ? { enabled: account.enabled !== false }
        : {}),
      ...(account.diamondQuantity !== undefined
        ? { diamondQuantity: Number(account.diamondQuantity || 0) }
        : {}),
      ...(account.lastLoginAt !== undefined
        ? { lastLoginAt: String(account.lastLoginAt || "") }
        : {}),
      ...(account.remark !== undefined
        ? { remark: String(account.remark || "") }
        : {}),
    };
  }

  if (partial?.session) {
    const normalizedSession = normalizeSession(partial.session);
    const normalizedOrder =
      normalizedSession.order ||
      (partial?.order ? normalizeOrder(partial.order) : null);
    next.session = {
      ...next.session,
      ...normalizedSession,
      resultPayload: normalizedSession.resultPayload || {},
      order: normalizedOrder,
    };
  } else if (partial?.order) {
    next.session = {
      ...next.session,
      order: normalizeOrder(partial.order),
    };
  }

  if (partial?.batchTask !== undefined) {
    next.batchTask = normalizeBatchTask(partial.batchTask);
  }

  redeemInfo.value = next;
}

function getCurrentCode() {
  return String(route.query.code || redeemInfo.value.code || "").trim();
}

function applyRedeemPayload(payload) {
  if (!payload) return;
  mergeRedeemInfo(payload);
  if (payload?.session || payload?.order) {
    maybeOpenPayResult(payload);
  }
}

function showError(code, message) {
  stopLiveSync();
  showBatchOrderModal.value = false;
  showConfirmModal.value = false;
  closeCamera();
  errCode.value = Number(code || 500);
  errMsg.value = message || "请求失败，请稍后重试";
  state.value = "error";
}

function extractErrorStatus(error, fallback = 500) {
  const status = Number(error?.response?.status || 0);
  return Number.isFinite(status) && status > 0 ? status : fallback;
}

function extractErrorMessage(error, fallback = "请求失败，请稍后重试") {
  const response = error?.response || {};
  const data = response?.data;
  const status = extractErrorStatus(error, 0);
  const statusText = String(response?.statusText || "").trim();

  const normalizeText = (value) => {
    if (typeof value !== "string") return "";
    const text = value.trim();
    if (!text) return "";
    if (text.startsWith("<")) {
      const titleMatch = text.match(/<title>([^<]+)<\/title>/i);
      return String(titleMatch?.[1] || "").trim();
    }
    return text;
  };

  const detail = data?.detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item.trim();
        const message = String(item?.msg || item?.message || "").trim();
        const location = Array.isArray(item?.loc)
          ? item.loc.filter(Boolean).join(".")
          : "";
        if (location && message) return `${location}: ${message}`;
        return message;
      })
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }

  const candidates = [
    normalizeText(detail),
    normalizeText(data?.message),
    normalizeText(data?.error),
    normalizeText(typeof data === "string" ? data : ""),
    normalizeText(error?.message),
  ].filter(Boolean);

  if (candidates.length) return candidates[0];
  if (status && statusText)
    return `${fallback}（HTTP ${status} ${statusText}）`;
  if (status) return `${fallback}（HTTP ${status}）`;
  return fallback;
}

async function loadPage() {
  const code = getCurrentCode();
  if (!code) {
    showError(400, "缺少卡密参数 ?code=xxx");
    return;
  }

  if (state.value !== "loading") pageRefreshing.value = true;
  state.value = "loading";
  try {
    const sessionId = String(route.query.session || "").trim();
    const { data } = await judianApi.publicRedeemInfo(code, sessionId);
    applyRedeemPayload(data);
    state.value = "ready";

    if (route.query.session) {
      const nextQuery = { ...route.query };
      delete nextQuery.session;
      router.replace({ query: nextQuery }).catch(() => {});
    }
  } catch (error) {
    const status = extractErrorStatus(error, 500);
    const detail = extractErrorMessage(error, "网络错误，请刷新后重试");
    showError(status, detail);
  } finally {
    pageRefreshing.value = false;
  }
}

async function syncCurrentState(options = {}) {
  const { silent = false } = options;
  const code = getCurrentCode();
  if (!code) {
    if (!silent) showToast("缺少卡密参数，无法同步状态");
    return;
  }

  if (!silent) syncingState.value = true;
  try {
    const sessionId = currentSessionId.value;
    const { data } = sessionId
      ? await judianApi.publicUnlockDetail(sessionId)
      : await judianApi.publicRedeemInfo(code, "");
    applyRedeemPayload(data);
    state.value = "ready";
  } catch (error) {
    const status = extractErrorStatus(error, 500);
    const detail = extractErrorMessage(error, "同步状态失败");
    if ([404, 409, 410].includes(status)) {
      showError(status, detail);
      return;
    }
    if (!silent) {
      showToast(detail);
    }
  } finally {
    if (!silent) syncingState.value = false;
  }
}

async function refreshSession() {
  const code = getCurrentCode();
  if (!code) {
    showToast("缺少卡密参数，无法新建会话");
    return;
  }

  pageRefreshing.value = true;
  try {
    const { data } = await judianApi.publicRedeemInfo(code, "", true);
    applyRedeemPayload(data);
    showBatchOrderModal.value = false;
    showConfirmModal.value = false;
    showPayResult.value = false;
    closeCamera();

    if (route.query.session) {
      const nextQuery = { ...route.query };
      delete nextQuery.session;
      router.replace({ query: nextQuery }).catch(() => {});
    }

    showToast("已创建新的解锁会话");
  } catch (error) {
    const detail = extractErrorMessage(error, "新建会话失败");
    showToast(detail);
  } finally {
    pageRefreshing.value = false;
  }
}

async function openCamera() {
  if (isCardReadOnly.value) {
    showToast(
      `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天存活期，无法支付`,
    );
    return;
  }
  if (cameraBusy.value) return;
  if (window.isSecureContext === false) {
    showToast("必须使用 HTTPS 或 localhost 才能调用摄像头");
    return;
  }

  cameraBusy.value = true;
  cameraTip.value = "正在加载扫码组件...";
  showCameraModal.value = true;

  const getMedia = async (constraints) => {
    if (navigator.mediaDevices?.getUserMedia) {
      return navigator.mediaDevices.getUserMedia(constraints);
    }
    const legacy =
      navigator.getUserMedia ||
      navigator.webkitGetUserMedia ||
      navigator.mozGetUserMedia ||
      navigator.msGetUserMedia;
    if (!legacy) throw new Error("当前浏览器不支持调用摄像头 API");
    return new Promise((resolve, reject) =>
      legacy.call(navigator, constraints, resolve, reject),
    );
  };

  try {
    const decoderPromise = ensureQrDecoder();
    try {
      cameraStream = await getMedia({
        video: { facingMode: { ideal: "environment" } },
      });
    } catch {
      cameraStream = await getMedia({ video: true });
    }
    await decoderPromise;

    const video = videoRef.value;
    if (!video) throw new Error("未找到视频节点");
    video.setAttribute("playsinline", "true");
    video.setAttribute("webkit-playsinline", "true");
    video.muted = true;
    video.srcObject = cameraStream;
    video.onplay = () => {
      cameraTip.value = "请将摄像头对准购买二维码";
      cameraAnimation = window.requestAnimationFrame(scanVideoFrame);
    };
    await video.play();
  } catch (error) {
    console.error("[judian-redeem] camera open failed:", error);
    cameraTip.value = "无法访问摄像头，请检查浏览器权限";
    showToast("摄像头打开失败，请改用批量下单按钮");
    closeCamera();
  } finally {
    cameraBusy.value = false;
  }
}

function closeCamera() {
  showCameraModal.value = false;
  if (cameraAnimation) {
    window.cancelAnimationFrame(cameraAnimation);
    cameraAnimation = null;
  }
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  const video = videoRef.value;
  if (video) {
    video.onplay = null;
    video.srcObject = null;
  }
}

function scanVideoFrame() {
  const video = videoRef.value;
  if (!showCameraModal.value || !video) return;
  if (!qrDecoder) {
    cameraAnimation = window.requestAnimationFrame(scanVideoFrame);
    return;
  }

  if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (context) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
      const result = qrDecoder(imageData.data, canvas.width, canvas.height, {
        inversionAttempts: "dontInvert",
      });
      if (result?.data) {
        closeCamera();
        submitScan(result.data, "camera_scan");
        return;
      }
    }
  }

  cameraAnimation = window.requestAnimationFrame(scanVideoFrame);
}

async function submitScan(qrText, submitSource = "manual") {
  if (isCardReadOnly.value) {
    showToast(
      `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天存活期，无法支付`,
    );
    return;
  }
  const sessionId = String(currentSession.value?.sessionId || "");
  if (!sessionId) {
    showToast("当前解锁会话不存在，请刷新页面后重试");
    return;
  }

  scanSubmitting.value = true;
  try {
    const { data } = await judianApi.publicUnlockScan(sessionId, {
      qrText,
      submitSource,
    });
    applyRedeemPayload(data);
    showConfirmModal.value = false;
    showToast(data?.message || "订单已识别，系统正在自动扣钻");
  } catch (error) {
    try {
      const { data } = await judianApi.publicUnlockDetail(sessionId);
      applyRedeemPayload(data);
    } catch {}

    const detail = extractErrorMessage(
      error,
      "二维码识别失败，请确认扫到的是包含 tradeNo 的聚点购买二维码",
    );
    showToast(detail);
  } finally {
    scanSubmitting.value = false;
  }
}

function openQrImagePicker() {
  if (
    isCardReadOnly.value ||
    scanSubmitting.value ||
    batchSubmitting.value ||
    isBatchRunning.value
  ) {
    return;
  }
  qrImageInputRef.value?.click();
}

function isEditableTarget(target) {
  if (!target || typeof target.closest !== "function") return false;
  if (target.isContentEditable) return true;
  return Boolean(
    target.closest(
      'input, textarea, select, [contenteditable="true"], [contenteditable=""]',
    ),
  );
}

function loadImageElementFromFile(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("图片加载失败"));
    };
    image.src = objectUrl;
  });
}

async function ensureQrDecoder() {
  if (qrDecoder) {
    return qrDecoder;
  }
  if (!qrDecoderPromise) {
    qrDecoderPromise = import("jsqr")
      .then((module) => {
        qrDecoder = module.default;
        return qrDecoder;
      })
      .finally(() => {
        qrDecoderPromise = null;
      });
  }
  return qrDecoderPromise;
}

async function decodeQrFromImageSource(source) {
  const decode = await ensureQrDecoder();
  const image = await loadImageElementFromFile(source);
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth || image.width;
  canvas.height = image.naturalHeight || image.height;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("无法读取图片内容");
  }
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
  const result = decode(imageData.data, canvas.width, canvas.height, {
    inversionAttempts: "attemptBoth",
  });
  if (!result?.data) {
    throw new Error("未识别到二维码，请换一张清晰的二维码图片");
  }
  return String(result.data || "").trim();
}

async function processQrText(text, submitSource = "manual") {
  const normalized = String(text || "").trim();
  if (!normalized) {
    throw new Error("未读取到可用的二维码内容");
  }
  pastedQrText.value = normalized;
  await submitScan(normalized, submitSource);
}

async function processQrImageBlob(blob, submitSource = "image_upload") {
  const qrText = await decodeQrFromImageSource(blob);
  await processQrText(qrText, submitSource);
}

async function handleQrImageChange(event) {
  const input = event?.target;
  const file = input?.files?.[0];
  if (!file) return;
  input.value = "";

  if (!String(file.type || "").startsWith("image/")) {
    showToast("请选择图片文件");
    return;
  }
  if (isCardReadOnly.value) {
    showToast(
      `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天存活期，无法支付`,
    );
    return;
  }

  try {
    scanSubmitting.value = true;
    await processQrImageBlob(file, "image_upload");
  } catch (error) {
    showToast(error?.message || "图片识别失败");
  } finally {
    scanSubmitting.value = false;
  }
}

async function submitPastedQrText() {
  if (isCardReadOnly.value) {
    showToast(
      `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天存活期，无法支付`,
    );
    return;
  }
  if (!pastedQrText.value) {
    showToast("请先粘贴二维码文本或链接");
    return;
  }
  try {
    await processQrText(pastedQrText.value, "paste_text");
  } catch (error) {
    showToast(error?.message || "粘贴内容识别失败");
  }
}

async function handlePasteIntoTextarea(event) {
  if (isCardReadOnly.value) {
    event?.preventDefault?.();
    return;
  }
  const clipboard = event?.clipboardData;
  if (!clipboard) return;

  const imageItem = Array.from(clipboard.items || []).find((item) =>
    String(item.type || "").startsWith("image/"),
  );
  if (imageItem) {
    event.preventDefault();
    const file = imageItem.getAsFile();
    if (!file) {
      showToast("剪贴板图片读取失败");
      return;
    }
    try {
      scanSubmitting.value = true;
      await processQrImageBlob(file, "clipboard_image");
    } catch (error) {
      showToast(error?.message || "剪贴板图片识别失败");
    } finally {
      scanSubmitting.value = false;
    }
    return;
  }

  const text = String(clipboard.getData("text/plain") || "").trim();
  if (!text) return;
  event.preventDefault();
  pastedQrText.value = text;
  try {
    await processQrText(text, "clipboard_text");
  } catch (error) {
    showToast(error?.message || "粘贴内容识别失败");
  }
}

async function handleGlobalPaste(event) {
  if (
    isCardReadOnly.value ||
    scanSubmitting.value ||
    batchSubmitting.value ||
    isBatchBusy.value ||
    clipboardReading.value
  ) {
    return;
  }

  const target = event?.target;
  if (isEditableTarget(target)) {
    return;
  }

  const clipboard = event?.clipboardData;
  if (!clipboard) return;

  const imageItem = Array.from(clipboard.items || []).find((item) =>
    String(item.type || "").startsWith("image/"),
  );
  if (imageItem) {
    const file = imageItem.getAsFile();
    if (!file) return;
    event.preventDefault();
    try {
      scanSubmitting.value = true;
      await processQrImageBlob(file, "clipboard_image");
    } catch (error) {
      showToast(error?.message || "剪贴板图片识别失败");
    } finally {
      scanSubmitting.value = false;
    }
    return;
  }

  const text = String(clipboard.getData("text/plain") || "").trim();
  if (!text) return;
  event.preventDefault();
  pastedQrText.value = text;
  try {
    await processQrText(text, "clipboard_text");
  } catch (error) {
    showToast(error?.message || "粘贴内容识别失败");
  }
}

async function readClipboardPayload() {
  if (
    scanSubmitting.value ||
    batchSubmitting.value ||
    isBatchBusy.value ||
    clipboardReading.value
  ) {
    return;
  }

  if (window.isSecureContext === false) {
    showToast("需要 HTTPS 或 localhost 才能读取系统剪贴板");
    return;
  }

  clipboardReading.value = true;
  try {
    const clipboardApi = navigator?.clipboard;
    if (!clipboardApi) {
      throw new Error("当前浏览器不支持读取系统剪贴板");
    }

    if (typeof clipboardApi.read === "function") {
      const items = await clipboardApi.read();
      for (const item of items) {
        const imageType = item.types.find((type) =>
          String(type || "").startsWith("image/"),
        );
        if (imageType) {
          const blob = await item.getType(imageType);
          await processQrImageBlob(blob, "clipboard_image");
          return;
        }
      }
    }

    if (typeof clipboardApi.readText === "function") {
      const text = String((await clipboardApi.readText()) || "").trim();
      if (text) {
        await processQrText(text, "clipboard_text");
        return;
      }
    }

    throw new Error("剪贴板里没有可用的二维码文本或图片");
  } catch (error) {
    showToast(error?.message || "读取剪贴板失败");
  } finally {
    clipboardReading.value = false;
  }
}

function openBatchOrderModal() {
  if (isCardReadOnly.value) {
    showToast(
      `卡密已${cardInvalidReasonText.value}，当前仅保留 7 天存活期，无法支付`,
    );
    return;
  }
  if (batchSubmitting.value || batchCancelling.value || isBatchBusy.value)
    return;
  batchOrderCount.value = Math.min(
    365,
    Math.max(1, Number(batchOrderCount.value || 1) || 1),
  );
  batchPreviewLoading.value = false;
  batchPreview.value = {
    ...createEmptyBatchPreview(),
    canSubmit: false,
  };
  showBatchOrderModal.value = true;
  refreshBatchPreview().catch(() => {});
}

function closeBatchOrderModal() {
  if (batchSubmitting.value || batchCancelling.value || isBatchBusy.value)
    return;
  batchOrderPassword.value = "";
  batchPreviewLoading.value = false;
  showBatchOrderModal.value = false;
}

function handleBatchPrimaryAction() {
  if (
    batchSubmitting.value ||
    batchCancelling.value ||
    isBatchCanceling.value
  ) {
    return;
  }
  if (canCancelBatchTask.value) {
    cancelBatchTask();
    return;
  }
  openBatchOrderModal();
}

function applyBatchCountPreset(option) {
  batchCountPreset.value = option.value;
  if (option.value !== "custom") {
    batchOrderCount.value = option.count;
  }
  if (showBatchOrderModal.value) {
    refreshBatchPreview().catch(() => {});
  }
}

function handleBatchCountCommit() {
  batchOrderCount.value = Math.min(
    365,
    Math.max(1, Math.floor(Number(batchOrderCount.value || 1) || 1)),
  );
  if (!showBatchOrderModal.value) return;
  refreshBatchPreview().catch(() => {});
}

async function refreshBatchPreview() {
  const sessionId = String(currentSession.value?.sessionId || "");
  const count = Math.floor(Number(batchOrderCount.value || 0));
  if (!sessionId) {
    batchPreviewLoading.value = false;
    batchPreview.value = {
      ...createEmptyBatchPreview(),
      canSubmit: false,
      error: "当前解锁会话不存在，请刷新页面后重试。",
    };
    return;
  }
  if (!Number.isFinite(count) || count < 1 || count > 365) {
    batchPreviewLoading.value = false;
    batchPreview.value = {
      ...createEmptyBatchPreview(),
      canSubmit: false,
      error: "请输入 1 到 365 之间的订单数量。",
    };
    return;
  }

  batchPreviewLoading.value = true;
  try {
    const { data } = await judianApi.publicUnlockBatchPreview(sessionId, {
      count,
      packageType: DEFAULT_BATCH_PACKAGE_TYPE,
    });
    const preview = data?.preview || {};
    batchPreview.value = {
      vipId: String(preview.vipId || ""),
      count: Number(preview.count || count),
      unitDiamond: Number(preview.unitDiamond || 0),
      requiredDiamond: Number(preview.requiredDiamond || 0),
      availableDiamond: Number(
        preview.availableDiamond ??
          redeemInfo.value.account?.diamondQuantity ??
          0,
      ),
      remainingQuota: Number(preview.remainingQuota ?? -1),
      enoughDiamond: preview.enoughDiamond !== false,
      enoughQuota: preview.enoughQuota !== false,
      canSubmit: preview.canSubmit !== false,
      error: "",
    };
  } catch (error) {
    const responseStatus = Number(error?.response?.status || 0);
    const rawDetail = String(error?.response?.data?.detail || "").trim();
    batchPreview.value = {
      ...createEmptyBatchPreview(),
      availableDiamond: Number(redeemInfo.value.account?.diamondQuantity || 0),
      remainingQuota:
        Number(redeemInfo.value.maxUses || 0) > 0
          ? Math.max(
              0,
              Number(redeemInfo.value.maxUses || 0) -
                Number(redeemInfo.value.useCount || 0),
            )
          : -1,
      canSubmit: false,
      error:
        responseStatus === 404 || rawDetail.toLowerCase() === "not found"
          ? "预估接口未生效，请重启后端服务后再试。"
          : extractErrorMessage(error, "额度校验失败，请稍后重试。"),
    };
  } finally {
    batchPreviewLoading.value = false;
  }
}

async function submitBatchOrder() {
  const sessionId = String(currentSession.value?.sessionId || "");
  if (!sessionId) {
    showToast("当前解锁会话不存在，请刷新页面后重试");
    return;
  }
  if (isBatchRunning.value) {
    showToast("当前已有批量下单任务正在执行，请稍后查看进度");
    return;
  }
  if (isBatchCanceling.value) {
    showToast("批量任务正在取消，请等待当前状态同步完成");
    return;
  }
  const count = Math.floor(Number(batchOrderCount.value || 0));
  if (!Number.isFinite(count) || count < 1 || count > 365) {
    showToast("请输入 1 到 365 之间的订单数量");
    return;
  }
  const account = String(batchOrderAccount.value || "").trim();
  const password = String(batchOrderPassword.value || "").trim();
  if (!account) {
    showToast("请输入动漫共和国账号");
    return;
  }
  if (!password) {
    showToast("请输入动漫共和国密码");
    return;
  }
  if (batchCountPreset.value === "custom" && count < 1) {
    showToast("请输入自定义数量");
    return;
  }
  if (batchPreviewLoading.value) {
    showToast("正在校验额度，请稍等");
    return;
  }
  if (!batchCanSubmit.value) {
    showToast(batchPreviewHintText.value);
    return;
  }

  batchSubmitting.value = true;
  try {
    const { data } = await judianApi.publicUnlockBatchPurchase(sessionId, {
      count,
      account,
      password,
      packageType: DEFAULT_BATCH_PACKAGE_TYPE,
      countPreset: String(batchCountPreset.value || ""),
      submitSource: "batch_script",
    });
    applyRedeemPayload(data);
    batchOrderPassword.value = "";
    showBatchOrderModal.value = false;
    showToast(`已提交 ${count} 单批量下单任务，页面将自动刷新执行进度`);
  } catch (error) {
    try {
      const { data } = await judianApi.publicUnlockDetail(sessionId);
      applyRedeemPayload(data);
    } catch {}

    const detail = extractErrorMessage(error, "批量下单提交失败，请稍后重试");
    showToast(detail);
  } finally {
    batchSubmitting.value = false;
  }
}

async function cancelBatchTask() {
  const sessionId = String(currentSession.value?.sessionId || "");
  if (!sessionId) {
    showToast("当前解锁会话不存在，请刷新页面后重试");
    return;
  }
  if (!canCancelBatchTask.value || batchCancelling.value) return;

  batchCancelling.value = true;
  try {
    const { data } = await judianApi.publicUnlockBatchCancel(sessionId);
    applyRedeemPayload(data);
    showToast(data?.message || "已请求取消批量任务");
  } catch (error) {
    try {
      const { data } = await judianApi.publicUnlockDetail(sessionId);
      applyRedeemPayload(data);
    } catch {}
    showToast(extractErrorMessage(error, "取消批量任务失败，请稍后重试"));
  } finally {
    batchCancelling.value = false;
  }
}

function openConfirmModal() {
  if (confirmSubmitting.value) return;
  if (!canConfirmUnlock.value || !currentOrder.value) {
    showToast("请先完成扫码并识别订单");
    return;
  }
  showConfirmModal.value = true;
}

function closeConfirmModal() {
  if (confirmSubmitting.value) return;
  showConfirmModal.value = false;
}

async function confirmOrder() {
  const sessionId = String(currentSession.value?.sessionId || "");
  if (!sessionId) {
    showToast("当前会话不存在，请刷新页面后重试");
    return;
  }
  if (!canConfirmUnlock.value) {
    showToast("请先完成扫码并识别订单");
    return;
  }

  showConfirmModal.value = false;
  confirmSubmitting.value = true;
  try {
    const confirmRes = await judianApi.publicUnlockConfirm(sessionId);
    applyRedeemPayload(confirmRes.data);
    showToast(confirmRes.data?.message || "已重新触发自动扣钻");
  } catch (error) {
    try {
      const { data } = await judianApi.publicUnlockDetail(sessionId);
      applyRedeemPayload(data);
    } catch {}

    const detail = extractErrorMessage(error, "自动扣钻失败，请稍后重试");
    showToast(detail);
  } finally {
    confirmSubmitting.value = false;
  }
}

function beforeDiamond() {
  return Number(resultPayload.value?.beforeDiamond ?? 0);
}
function afterDiamond() {
  return Number(
    resultPayload.value?.afterDiamond ??
      resultPayload.value?.diamondQuantity ??
      0,
  );
}
function consumedDiamond() {
  const consumed = Number(resultPayload.value?.consumedDiamond ?? 0);
  if (consumed > 0) return consumed;
  const before = beforeDiamond();
  const after = afterDiamond();
  return before > 0 && after >= 0 && after <= before
    ? Math.max(0, before - after)
    : 0;
}
const beforeDiamondText = computed(() => `${beforeDiamond()} 钻`);
const afterDiamondText = computed(() => `${afterDiamond()} 钻`);
const consumedDiamondText = computed(() => `${consumedDiamond()} 钻`);

function maybeOpenPayResult(payload) {
  const batchTask = payload?.batchTask || redeemInfo.value.batchTask || null;
  if (Number(batchTask?.totalCount || 0) > 1) return;
  const session = payload?.session || redeemInfo.value.session || {};
  const result = session?.resultPayload || {};
  const success = isConfirmedUnlockSuccess(result);
  const sessionKey = [
    String(session?.sessionId || ""),
    Number(result?.beforeDiamond || 0),
    Number(result?.afterDiamond || 0),
    Number(result?.consumedDiamond || 0),
    String(result?.rendered_message || ""),
  ].join(":");
  if (success && sessionKey && sessionKey !== lastPayResultKey) {
    lastPayResultKey = sessionKey;
    showPayResult.value = true;
  }
}

function closePayResult() {
  showPayResult.value = false;
}

function removeLegacyPayResultDom() {
  try {
    const overlay = document.querySelector(".pay-result-overlay");
    if (overlay && overlay.parentElement)
      overlay.parentElement.removeChild(overlay);
    document
      .querySelectorAll(".pay-result-modal, .pay-result-actions")
      .forEach((el) => el.remove());
  } catch {}
}

function showToast(message) {
  toastMessage.value = message;
  toastVisible.value = true;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toastVisible.value = false;
  }, 2400);
}
</script>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  width: 100%;
  min-height: 100%;
  margin: 0;
  background: #0c0f16;
}

:global(body) {
  overflow-x: hidden;
}

.redeem-page {
  width: 100%;
  min-height: 100vh;
  padding: 0 16px 56px;
  background:
    radial-gradient(circle at top, rgba(245, 158, 11, 0.16), transparent 26%),
    radial-gradient(
      circle at bottom left,
      rgba(37, 99, 235, 0.14),
      transparent 24%
    ),
    linear-gradient(180deg, #0c0f16 0%, #101521 100%);
  color: #edf2ff;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.redeem-page__topbar,
.redeem-page__main {
  width: min(680px, 100%);
  margin: 0 auto;
}

.redeem-page__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 22px 0 18px;
}

.redeem-page__brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.redeem-page__brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  color: #1f2937;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 10px 24px rgba(251, 191, 36, 0.2);
}

.redeem-page__brand-title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.redeem-page__brand-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #7f8cab;
}

.redeem-page__status-pill,
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.redeem-page__status-pill {
  background: rgba(13, 31, 20, 0.92);
  color: #7ef0a4;
  border: 1px solid rgba(34, 197, 94, 0.24);
}

.redeem-page__status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.8);
}

.panel {
  background: rgba(19, 22, 31, 0.96);
  border: 1px solid #1e2235;
  border-radius: 20px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
}

.panel--loading,
.panel--error {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 28px;
}

.skeleton {
  border-radius: 12px;
  background: linear-gradient(
    90deg,
    rgba(30, 34, 53, 0.82),
    rgba(44, 50, 76, 0.92),
    rgba(30, 34, 53, 0.82)
  );
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite linear;
}

.skeleton--title {
  width: 220px;
  height: 24px;
  margin-bottom: 12px;
}

.skeleton--text {
  width: 320px;
  max-width: 100%;
  height: 14px;
  margin-bottom: 22px;
}

.skeleton--grid {
  width: 100%;
  height: 132px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.error-code {
  font-size: 72px;
  font-weight: 800;
  line-height: 1;
  color: #313852;
}

.error-title {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 700;
}

.error-message {
  margin: 8px 0 22px;
  color: #8f9dbd;
  line-height: 1.7;
}

.hero-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 22px;
}

.eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #fbbf24;
}

.hero-title {
  margin: 8px 0 6px;
  font-size: 23px;
  line-height: 1.2;
  color: #fff;
}

.hero-desc {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #8d9aba;
  line-height: 1.6;
}

.hero-sep {
  margin: 0;
  color: #4c566f;
}

.hero-badge--success {
  background: rgba(13, 31, 20, 0.92);
  color: #7ef0a4;
  border: 1px solid rgba(34, 197, 94, 0.24);
}

.hero-badge--warning {
  background: rgba(39, 30, 0, 0.92);
  color: #fcd277;
  border: 1px solid rgba(245, 158, 11, 0.24);
}

.hero-badge--danger {
  background: rgba(45, 18, 18, 0.92);
  color: #fda4a4;
  border: 1px solid rgba(248, 113, 113, 0.2);
}

.stats-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-card {
  padding: 16px;
}

.stat-progress {
  margin-top: 10px;
  height: 6px;
  border-radius: 999px;
  background: #0f1524;
  border: 1px solid #1f2940;
  overflow: hidden;
}
.stat-progress__bar {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #34d399);
}
.stat-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #7f8cab;
}
.stat-meta__sep {
  color: #4c566f;
}
.stat-action {
  margin-left: auto;
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid #2a3552;
  background: #161d2d;
  color: #b7c2e6;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.stat-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.stat-action:hover:not(:disabled) {
  border-color: #385189;
  background: #1a2234;
}

.stat-label {
  font-size: 12px;
  color: #7f8cab;
}

.stat-value {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 800;
  line-height: 1.25;
  color: #fff;
  word-break: break-word;
}

.stat-value--danger {
  color: #f87171;
}

.stat-help {
  margin-top: 8px;
  font-size: 11px;
  color: #5f6c8b;
  line-height: 1.6;
}

.scan-layout {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.scan-panel,
.order-panel,
.detail-panel,
.result-panel {
  padding: 20px;
}

.panel-title {
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.scan-panel__desc {
  margin-bottom: 14px;
  color: #8d9aba;
  font-size: 13px;
  line-height: 1.75;
}

.scan-status-card {
  padding: 16px;
  border-radius: 16px;
  background: #101726;
  border: 1px solid #1f2940;
  margin-bottom: 14px;
}

.scan-status-card__label,
.order-label,
.detail-label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  color: #7382a6;
}

.scan-status-card__value {
  font-size: 19px;
  font-weight: 800;
  color: #fff;
}

.scan-status-card__help {
  margin-top: 6px;
  color: #8d9aba;
  font-size: 13px;
  line-height: 1.65;
}

.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.scan-primary-button {
  width: 100%;
  margin-bottom: 10px;
}

.actions-row--stack {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.action-button {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid #2a3552;
  background: #161d2d;
  color: #edf2ff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.12s ease,
    border-color 0.12s ease,
    background 0.12s ease,
    opacity 0.12s ease;
}

.action-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #385189;
  background: #1a2234;
}

.action-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-button--primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28);
}

.action-button--primary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.action-button--secondary {
  background: linear-gradient(135deg, #0f766e, #0f9d8a);
  border-color: #0f9d8a;
  box-shadow: 0 10px 24px rgba(15, 157, 138, 0.24);
}

.action-button--secondary:hover:not(:disabled) {
  background: linear-gradient(135deg, #0d675f, #0d8777);
  border-color: #0d8777;
}

.action-button--danger {
  background: linear-gradient(135deg, #b91c1c, #dc2626);
  border-color: #dc2626;
  box-shadow: 0 10px 24px rgba(220, 38, 38, 0.22);
}

.action-button--danger:hover:not(:disabled) {
  background: linear-gradient(135deg, #991b1b, #b91c1c);
  border-color: #b91c1c;
}

.batch-progress-card {
  margin-bottom: 14px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid #26324d;
  background: #101726;
}

.batch-progress-card--running {
  border-color: rgba(96, 165, 250, 0.35);
}

.batch-progress-card--success {
  border-color: rgba(34, 197, 94, 0.35);
}

.batch-progress-card--warning {
  border-color: rgba(251, 191, 36, 0.4);
}

.batch-progress-card--failed {
  border-color: rgba(248, 113, 113, 0.4);
}

.batch-progress-card__header,
.batch-progress-item__top,
.batch-progress-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.batch-progress-card__title {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}

.batch-progress-card__meta {
  font-size: 13px;
  font-weight: 700;
  color: #93c5fd;
}

.batch-progress-card__header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-progress-card__action {
  min-width: 88px;
  padding: 8px 12px;
  font-size: 12px;
}

.batch-progress-card__desc,
.batch-progress-current,
.batch-progress-item__message {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.65;
  color: #93a1bf;
}

.batch-progress-item__detail {
  margin-top: 8px;
}

.batch-progress-item__detail-summary {
  cursor: pointer;
  color: #93c5fd;
  font-size: 12px;
  user-select: none;
}

.batch-progress-item__raw {
  margin-top: 8px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(2, 6, 23, 0.72);
  border: 1px solid rgba(59, 130, 246, 0.18);
  color: #bfdbfe;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.batch-progress-bar {
  margin-top: 12px;
  height: 8px;
  border-radius: 999px;
  background: #192235;
  overflow: hidden;
}

.batch-progress-bar__inner {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #60a5fa);
  transition: width 0.2s ease;
}

.batch-progress-stats {
  margin-top: 10px;
  flex-wrap: wrap;
  justify-content: flex-start;
  font-size: 12px;
  color: #c7d2fe;
}

.batch-progress-list {
  margin-top: 12px;
  display: grid;
  gap: 10px;
  max-height: 260px;
  overflow: auto;
}

.batch-progress-item {
  padding: 12px;
  border-radius: 14px;
  background: #0d1422;
  border: 1px solid #1e2940;
}

.batch-progress-item--completed {
  border-color: rgba(34, 197, 94, 0.3);
}

.batch-progress-item--failed {
  border-color: rgba(248, 113, 113, 0.35);
}

.batch-progress-item--canceled {
  border-color: rgba(251, 191, 36, 0.35);
}

.batch-progress-item__top {
  font-size: 12px;
  font-weight: 700;
  color: #dbeafe;
}

.batch-progress-item__code {
  margin-top: 6px;
  font-size: 13px;
  font-family: Consolas, "SFMono-Regular", monospace;
  color: #fff;
  word-break: break-all;
}

.upload-dropzone {
  padding: 18px;
  border-radius: 16px;
  border: 1.5px dashed #2a3552;
  background: #111827;
  text-align: center;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}

.upload-dropzone--active,
.upload-dropzone:hover {
  border-color: #2563eb;
  background: #151d31;
}

.upload-dropzone--disabled {
  opacity: 0.7;
}

.upload-dropzone__icon {
  margin-bottom: 8px;
  font-size: 24px;
  color: #60a5fa;
}

.upload-dropzone__title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.upload-dropzone__tip {
  margin-top: 8px;
  font-size: 12px;
  color: #7f8cab;
  line-height: 1.7;
}

.paste-panel {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  background: #101726;
  border: 1px solid #1f2940;
}

.paste-panel__title {
  font-size: 13px;
  font-weight: 800;
  color: #fff;
}

.paste-panel__desc {
  margin-top: 6px;
  font-size: 12px;
  color: #7f8cab;
  line-height: 1.7;
}

.paste-panel__textarea {
  width: 100%;
  min-height: 104px;
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #2a3552;
  background: #0d1422;
  color: #fff;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.paste-panel__textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.16);
}

.paste-panel__textarea:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.batch-order-field {
  display: block;
  margin-top: 14px;
}

.batch-order-field__label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #dbeafe;
}

.batch-order-field__input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid #2a3552;
  background: #0d1422;
  color: #fff;
  font-size: 16px;
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.batch-order-field__input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.16);
}

.batch-order-field__input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.batch-package-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.batch-package-option {
  height: 42px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  background: rgba(15, 23, 42, 0.96);
  color: #dbeafe;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}

.batch-package-option:hover:not(:disabled) {
  border-color: rgba(96, 165, 250, 0.5);
  transform: translateY(-1px);
}

.batch-package-option--active {
  border-color: #3b82f6;
  background: linear-gradient(
    135deg,
    rgba(29, 78, 216, 0.78),
    rgba(37, 99, 235, 0.55)
  );
  color: #fff;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.2);
}

.batch-package-option:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.batch-preview-card {
  margin-top: 12px;
  padding: 14px;
  border-radius: 16px;
  background: #101726;
  border: 1px solid #1f2940;
}

.batch-preview-card__title {
  font-size: 13px;
  font-weight: 800;
  color: #fff;
}

.batch-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.batch-preview-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: #0d1422;
  border: 1px solid #1e2940;
}

.batch-preview-card__hint {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.7;
  color: #8d9aba;
}

.batch-preview-card__hint--ok {
  color: #86efac;
}

.batch-preview-card__hint--danger {
  color: #fca5a5;
}

.order-grid,
.detail-list,
.confirm-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mini-order-item,
.order-item,
.detail-item {
  padding: 14px 15px;
  border-radius: 16px;
  background: #101726;
  border: 1px solid #1f2940;
}

.order-item--full,
.detail-item--full {
  grid-column: 1 / -1;
}

.order-value,
.detail-value {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #edf2ff;
  line-height: 1.65;
  word-break: break-word;
}

.order-value--mono,
.detail-value--mono {
  font-family: Consolas, "SFMono-Regular", monospace;
}

.order-value--accent {
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
}

.order-panel .actions-row,
.detail-panel .actions-row {
  margin-top: 14px;
}

.empty-block {
  padding: 22px 16px;
  border-radius: 16px;
  background: #101726;
  border: 1px dashed #2a3552;
  text-align: center;
}

.empty-block__title {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.empty-block__desc {
  margin-top: 8px;
  color: #7f8cab;
  font-size: 13px;
  line-height: 1.7;
}

.result-panel,
.detail-panel {
  margin-top: 10px;
}

.result-message {
  padding: 16px;
  border-radius: 16px;
  background: rgba(13, 31, 20, 0.94);
  border: 1px solid rgba(34, 197, 94, 0.24);
  color: #b7f5cb;
  font-size: 13px;
  line-height: 1.8;
  font-weight: 600;
}

.result-message--inline {
  margin-bottom: 14px;
}

.mini-order-grid,
.pay-result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.pay-result-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.76);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  z-index: 320;
}

.pay-result-overlay--show {
  opacity: 1;
  pointer-events: auto;
}

.pay-result-modal {
  width: min(540px, 100%);
  padding: 20px;
  border-radius: 20px;
  background: #13161f;
  border: 1px solid #1e2235;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
}

.pay-result__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.pay-result__title {
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}

.pay-result__subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #7f8cab;
}

.pay-result__close {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: none;
  background: #1f293d;
  color: #cbd5e1;
  font-size: 20px;
  cursor: pointer;
}

.pay-result-item {
  padding: 14px 15px;
  border-radius: 16px;
  background: #101726;
  border: 1px solid #1f2940;
}

.pay-result-item .label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  color: #7382a6;
}

.pay-result-item .value {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #edf2ff;
  line-height: 1.65;
  word-break: break-word;
}

.pay-result-item .value--mono {
  font-family: Consolas, "SFMono-Regular", monospace;
}

.pay-result-item .value--accent {
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
}

.pay-result-item--full {
  grid-column: 1 / -1;
}

.pay-result-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.confirm-overlay,
.camera-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.74);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  z-index: 300;
}

.confirm-overlay--show,
.camera-overlay--show {
  opacity: 1;
  pointer-events: auto;
}

.confirm-modal,
.camera-modal {
  border-radius: 20px;
  background: #13161f;
  border: 1px solid #1e2235;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
}

.confirm-modal {
  width: min(520px, 100%);
  padding: 20px;
  max-height: min(720px, calc(100vh - 32px));
  max-height: min(720px, calc(100dvh - 32px));
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.camera-modal {
  width: min(380px, 100%);
  padding: 18px;
}

.confirm-modal__header,
.camera-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.confirm-modal__header {
  position: sticky;
  top: 0;
  z-index: 1;
  padding-bottom: 10px;
  background: #13161f;
}

.confirm-modal__title,
.camera-modal__title {
  font-size: 15px;
  font-weight: 800;
  color: #fff;
}

.confirm-modal__subtitle,
.camera-modal__subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #7f8cab;
  line-height: 1.6;
}

.confirm-card {
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(
    135deg,
    rgba(37, 99, 235, 0.18),
    rgba(96, 165, 250, 0.08)
  );
  border: 1px solid rgba(37, 99, 235, 0.24);
}

.confirm-card__amount {
  font-size: 20px;
  font-weight: 800;
  color: #fff;
}

.confirm-card__desc {
  margin-top: 8px;
  color: #d5deef;
  line-height: 1.7;
  font-size: 13px;
}

.confirm-actions {
  margin-top: 16px;
  justify-content: flex-end;
}

.confirm-modal__close,
.camera-modal__close {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: none;
  background: #1f293d;
  color: #cbd5e1;
  font-size: 20px;
  cursor: pointer;
}

.camera-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 16px;
  background: #000;
}

.camera-frame__video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-frame__mask {
  position: absolute;
  inset: 18%;
  border: 2px solid rgba(37, 99, 235, 0.8);
  border-radius: 16px;
  box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.34);
}

.camera-frame__line {
  position: absolute;
  left: 18%;
  right: 18%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #22c55e, transparent);
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.72);
  animation: scan-line 2s linear infinite;
}

@keyframes scan-line {
  0% {
    top: 22%;
  }
  50% {
    top: 78%;
  }
  100% {
    top: 22%;
  }
}

.camera-tip {
  margin-top: 12px;
  text-align: center;
  color: #7f8cab;
  font-size: 13px;
}

.toast {
  position: fixed;
  left: 50%;
  bottom: 26px;
  transform: translateX(-50%) translateY(12px);
  opacity: 0;
  pointer-events: none;
  transition: all 0.2s ease;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  color: #111827;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.24);
  z-index: 400;
}

.toast--show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .redeem-page {
    padding: 0 10px calc(20px + env(safe-area-inset-bottom));
  }

  .redeem-page__topbar {
    gap: 8px;
    padding: 12px 0 10px;
  }

  .redeem-page__topbar,
  .hero-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-panel,
  .scan-panel,
  .stat-card,
  .confirm-modal,
  .camera-modal,
  .pay-result-modal {
    padding: 12px;
  }

  .hero-title {
    margin: 6px 0 4px;
    font-size: 18px;
  }

  .hero-desc {
    gap: 4px;
    font-size: 11px;
    line-height: 1.5;
  }

  .hero-badge {
    justify-content: center;
  }

  .redeem-page__brand-mark {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    font-size: 14px;
  }

  .redeem-page__brand-title {
    font-size: 13px;
  }

  .redeem-page__brand-subtitle {
    margin-top: 1px;
    font-size: 10px;
  }

  .redeem-page__status-pill {
    padding: 5px 10px;
    font-size: 11px;
  }

  .stats-grid,
  .mini-order-grid,
  .order-grid,
  .detail-list,
  .confirm-grid,
  .batch-preview-grid,
  .pay-result-grid,
  .batch-package-options,
  .actions-row--stack,
  .pay-result-actions {
    grid-template-columns: 1fr;
  }

  .stat-meta {
    flex-wrap: wrap;
    gap: 6px;
    font-size: 11px;
  }

  .stat-action {
    width: 100%;
    margin-left: 0;
    justify-content: center;
  }

  .stat-card {
    border-radius: 16px;
  }

  .stat-label,
  .scan-status-card__label,
  .order-label {
    font-size: 11px;
  }

  .stat-value {
    font-size: 20px;
    line-height: 1.2;
  }

  .stat-help,
  .scan-panel__desc,
  .scan-status-card__help,
  .batch-progress-card__desc,
  .batch-progress-current,
  .batch-progress-item__message {
    font-size: 11px;
    line-height: 1.5;
  }

  .panel-title {
    font-size: 15px;
  }

  .scan-layout,
  .mini-order-grid,
  .actions-row,
  .batch-progress-list {
    gap: 10px;
  }

  .batch-progress-card,
  .scan-status-card,
  .mini-order-item,
  .batch-progress-item {
    border-radius: 14px;
  }

  .actions-row {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
    min-height: 42px;
    padding: 10px 14px;
    font-size: 13px;
  }

  .scan-primary-button {
    min-height: 46px;
  }

  .upload-dropzone {
    padding: 16px 12px;
  }

  .camera-overlay,
  .confirm-overlay,
  .pay-result-overlay {
    padding: 12px;
    align-items: flex-end;
  }

  .camera-modal,
  .confirm-modal,
  .pay-result-modal {
    width: min(100%, 420px);
    border-radius: 16px;
  }

  .confirm-modal {
    max-height: calc(100dvh - 24px - env(safe-area-inset-bottom));
    padding-bottom: calc(16px + env(safe-area-inset-bottom));
  }

  .camera-frame {
    aspect-ratio: 0.92;
  }

  .redeem-page__status-pill {
    align-self: flex-start;
  }

  .toast {
    width: calc(100vw - 24px);
    max-width: 420px;
    border-radius: 16px;
    text-align: center;
  }
}
</style>
