<template>
  <div class="rp-root">
    <!-- Top bar -->
    <header class="rp-topbar">
      <div class="rp-brand">
        <div class="rp-brand-mark">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 1L14 4.5V11.5L8 15L2 11.5V4.5L8 1Z" fill="white" fill-opacity="0.9" />
          </svg>
        </div>
        <span class="rp-brand-name">网盘助手</span>
      </div>
      <div class="rp-ping">
        <span class="rp-ping-dot" />
        <span>服务正常</span>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="state === 'loading'" class="rp-center">
      <div class="rp-skeleton-card">
        <div class="sk-line" style="width: 40%; height: 20px; margin-bottom: 12px" />
        <div class="sk-line" style="width: 65%; height: 14px; margin-bottom: 32px" />
        <div class="sk-line" style="height: 52px" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="state === 'error'" class="rp-center">
      <div class="rp-error-card">
        <div class="rp-error-code">{{ errCode }}</div>
        <div class="rp-error-msg">{{ errMsg }}</div>
      </div>
    </div>

    <!-- Main -->
    <main v-else-if="state === 'ready'" class="rp-main">
      <!-- Hero -->
      <div class="rp-hero">
        <div class="rp-hero-left">
          <div class="rp-avatar-wrap">
            <img v-if="info.avatar_url" :src="info.avatar_url" class="rp-avatar-img" />
            <div v-else class="rp-avatar-fallback">{{ info.username?.[0] || '?' }}</div>
          </div>
          <div>
            <h1 class="rp-username">{{ info.username }}</h1>
            <div class="rp-hero-meta">
              <span class="rp-vip-tag" :class="vipClass">{{ info.vip_level || '普通用户' }}</span>
              <span class="rp-meta-sep">·</span>
              <span class="rp-meta-text"
                >授权 <b>{{ info.duration }}</b> 天</span
              >
            </div>
          </div>
        </div>
        <div class="rp-status-pill">
          <span class="rp-ping-dot" />
          账号正常
        </div>
      </div>

      <!-- Stats -->
      <div class="rp-stats">
        <div class="rp-stat">
          <div class="rp-stat-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div>
            <div class="rp-stat-val rp-countdown" :class="{ expired: countdown === '已过期' }">
              {{ countdown || '计算中...' }}
            </div>
            <div class="rp-stat-key">剩余时间</div>
          </div>
        </div>
        <div class="rp-stat-div" />
        <div class="rp-stat">
          <div class="rp-stat-icon amber">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div>
            <div class="rp-stat-val" style="font-size: 13px">{{ usageText }}</div>
            <div class="rp-stat-key">授权次数</div>
          </div>
        </div>
        <div class="rp-stat-div" />
        <div class="rp-stat">
          <div class="rp-stat-icon green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div>
            <div class="rp-stat-val">正常</div>
            <div class="rp-stat-key">账号状态</div>
          </div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="rp-actions">
        <button class="rp-action" @click="deleteFiles">
          <div class="rp-action-icon red">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
              <path d="M10 11v6M14 11v6" />
              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
            </svg>
          </div>
          <span>删除文件</span>
        </button>
        <button class="rp-action" @click="switchAccount">
          <div class="rp-action-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 1l4 4-4 4" />
              <path d="M3 11V9a4 4 0 0 1 4-4h14" />
              <path d="M7 23l-4-4 4-4" />
              <path d="M21 13v2a4 4 0 0 1-4 4H3" />
            </svg>
          </div>
          <span>自助换号</span>
        </button>
        <button class="rp-action" @click="openRisk">
          <div class="rp-action-icon green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
          </div>
          <span>解除风险</span>
        </button>
      </div>

      <!-- CTA -->
      <button class="rp-cta" @click="openCamera" style="border-radius: 14px; width: 100%; max-width: 520px; height: 50px; gap: 9px; font-size: 15px; line-height: 18px; letter-spacing: normal; color: #FFFFFF;">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </svg>
        调用摄像头扫码登录
      </button>

      <!-- Drop zone：上传百度网盘登录页的二维码截图 -->
      <div
        class="rp-drop"
        :class="{ active: isDragging }"
        @click="$refs.fileInputRef.click()"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <svg
          class="rp-drop-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <polyline points="16 16 12 12 8 16" />
          <line x1="12" y1="12" x2="12" y2="21" />
          <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
        </svg>
        <div class="rp-drop-text">
          截图 <b style="color: #60a5fa">pan.baidu.com 的登录二维码</b> 拖拽/粘贴 到此处<br />
          <span style="font-size: 11px; color: #374151">系统将自动用本账号完成扫码确认</span>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleFileChange"
        />
      </div>

      <!-- Notice -->
      <div class="rp-notice">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          style="flex-shrink: 0; margin-top: 1px"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        使用百度网盘 App 扫描二维码，或将截图拖拽、粘贴到本页面自动识别
      </div>
    </main>

    <!-- Camera Modal -->
    <Teleport to="body">
      <div class="rp-overlay" :class="{ show: showCameraModal }" @click.self="closeCamera">
        <div class="rp-modal" style="width: 340px; padding: 20px;">
          <div class="rp-modal-head">
            <span class="rp-modal-title">调用摄像头扫码</span>
            <button class="rp-modal-close" @click="closeCamera">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="rp-qr-frame">
            <video ref="videoRef" autoplay playsinline webkit-playsinline muted style="width: 100%; height: 100%; object-fit: cover;"></video>
            <div class="rp-scan-line"></div>
          </div>
          <div class="rp-qr-tip">{{ qrTip }}</div>
        </div>
      </div>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <div class="rp-toast" :class="{ show: toastOn }">{{ toastMsg }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import jsQR from 'jsqr'
import { netdiskPublicRequest as request } from '@/utils/netdisk-request'

const route = useRoute()

const state = ref('loading')
const errCode = ref(404)
const errMsg = ref('')
const info = ref({ username: '', vip_level: '', duration: 0, cookie: '', avatar_url: '' })
const isDragging = ref(false)
const fileInputRef = ref(null)

const showCameraModal = ref(false)
const videoRef = ref(null)
let stream = null
let scanAnimation = null

const qrTip = ref('请将摄像头对准百度网盘登录二维码')
const toastMsg = ref('')
const toastOn = ref(false)

let toastTimer = null
let countdownTimer = null

const countdown = ref('') // 剩余时间字符串
const usageText = ref('') // 使用次数文字

const vipClass = computed(() => ({
  'vip-svip': info.value.vip_level === 'SVIP',
  'vip-vip': info.value.vip_level === 'VIP',
  'vip-free': !['SVIP', 'VIP'].includes(info.value.vip_level),
}))

onMounted(async () => {
  window.addEventListener('paste', handlePaste)
  
  const code = route.query.code
  if (!code) {
    showErr(400, '缺少卡密参数 ?code=xxx')
    return
  }
  try {
    const res = await request.get(`/cdkey/redeem?code=${code}`)
    const data = res.data
    info.value = data
    state.value = 'ready'
    startCountdown(data.expires_at, data.use_count, data.max_uses)
  } catch (err) {
    const detail = err.response?.data?.detail || '网络错误，请刷新重试'
    const status = err.response?.status || 500
    showErr(status, detail)
  }
})
onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  closeCamera()
  clearInterval(countdownTimer)
})

function startCountdown(expiresAt, useCount, maxUses) {
  // 授权次数显示
  if (maxUses > 0) {
    usageText.value = `已授权 ${useCount} / ${maxUses} 次`
  } else {
    usageText.value = `已授权 ${useCount} 次（不限次）`
  }

  if (!expiresAt) {
    countdown.value = '尚未开始计时'
    return
  }

  function tick() {
    const left = expiresAt - Math.floor(Date.now() / 1000)
    if (left <= 0) {
      countdown.value = '已过期'
      clearInterval(countdownTimer)
      return
    }
    const d = Math.floor(left / 86400)
    const h = Math.floor((left % 86400) / 3600)
    const m = Math.floor((left % 3600) / 60)
    const s = left % 60
    countdown.value =
      d > 0
        ? `${d}天 ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
        : `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  tick()
  countdownTimer = setInterval(tick, 1000)
}

function showErr(code, msg) {
  errCode.value = code
  errMsg.value = msg
  state.value = 'error'
}

function deleteFiles() {
  window.open('https://pan.baidu.com/disk/home#/all', '_blank')
}
async function switchAccount() {
  const code = route.query.code
  if (!code) return toast('卡密参数缺失')
  toast('正在换号...')
  try {
    const res = await request.post(`/cdkey/switch?code=${code}`)
    const data = res.data
    // 更新页面显示
    info.value = { ...info.value, ...data }
    toast(`已切换到：${data.username} ✓`)
  } catch (err) {
    const detail = err.response?.data?.detail || '换号失败，请重试'
    toast(detail)
  }
}
function copyInjectCode() {
  const cookie = info.value.cookie
  if (!cookie) return toast('暂无 Cookie')
  // 生成注入脚本：设置所有 cookie 并刷新
  const pairs = cookie
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
  const lines = pairs.map((pair) => {
    const [k, ...rest] = pair.split('=')
    const v = rest.join('=')
    return `document.cookie="${k.trim()}=${v};domain=.baidu.com;path=/;expires="+new Date(Date.now()+86400*30*1000).toUTCString();`
  })
  const script = lines.join('\n') + '\nlocation.reload();'
  navigator.clipboard.writeText(script).then(() => toast('注入代码已复制，粘贴到控制台运行 ✓'))
}

function copyCookie() {
  if (!info.value.cookie) return toast('暂无 Cookie')
  navigator.clipboard.writeText(info.value.cookie).then(() => toast('Cookie 已复制 ✓'))
}
function openPan() {
  window.open('https://pan.baidu.com/disk/home', '_blank')
}
function openRisk() {
  window.open('https://pan.baidu.com/disk/home#/all?vip=1', '_blank')
}

async function openCamera() {
  if (window.isSecureContext === false) {
    toast('安全限制：必须使用 HTTPS 协议或 localhost 访问才能调用摄像头')
    return
  }
  
  showCameraModal.value = true
  qrTip.value = '正在加载摄像头...'
  
  const getMedia = async (constraints) => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      return await navigator.mediaDevices.getUserMedia(constraints)
    }
    const getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia
    if (!getUserMedia) throw new Error('当前浏览器不支持调用摄像头 API')
    return await new Promise((resolve, reject) => {
      getUserMedia.call(navigator, constraints, resolve, reject)
    })
  }

  try {
    try {
      // 优先请求后置摄像头（ideal 兼容性更好）
      stream = await getMedia({ video: { facingMode: { ideal: 'environment' } } })
    } catch (e) {
      // 失败则降级请求任意摄像头
      stream = await getMedia({ video: true })
    }
    
    if (videoRef.value) {
      const video = videoRef.value
      // iOS / 微信内嵌 WebView 播放兼容
      video.setAttribute('playsinline', 'true')
      video.setAttribute('webkit-playsinline', 'true')
      video.muted = true
      
      try {
        video.srcObject = stream
      } catch (error) {
        video.src = window.URL?.createObjectURL(stream) || window.webkitURL?.createObjectURL(stream)
      }
      
      video.onplay = () => {
        qrTip.value = '请将摄像头对准百度网盘登录二维码'
        requestAnimationFrame(tick)
      }
      video.play().catch(e => console.warn('自动播放失败:', e))
    }
  } catch (err) {
    console.error('Camera Access Error:', err)
    qrTip.value = '无法访问摄像头或浏览器不支持'
    toast('无法访问摄像头，请检查系统权限或更换浏览器')
    setTimeout(closeCamera, 2000)
  }
}

function closeCamera() {
  showCameraModal.value = false
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (scanAnimation) {
    cancelAnimationFrame(scanAnimation)
    scanAnimation = null
  }
  if (videoRef.value) {
    videoRef.value.onplay = null
  }
}

function tick() {
  if (!videoRef.value || videoRef.value.readyState === videoRef.value.HAVE_ENOUGH_DATA) {
    const video = videoRef.value
    if (video && video.videoWidth > 0) {
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const qrResult = jsQR(imageData.data, canvas.width, canvas.height, {
        inversionAttempts: "dontInvert",
      })
      if (qrResult) {
        closeCamera()
        handleQrText(qrResult.data)
        return
      }
    }
  }
  if (showCameraModal.value) {
    scanAnimation = requestAnimationFrame(tick)
  }
}

function handleDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file?.type.startsWith('image/')) decodeQr(file)
  else toast('请上传图片文件')
}
function handleFileChange(e) {
  const f = e.target.files?.[0]
  if (f) decodeQr(f)
}

function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.indexOf('image') !== -1) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        decodeQr(file)
        break
      }
    }
  }
}

async function decodeQr(file) {
  toast('正在识别二维码...')
  try {
    // 用 jsQR 解码，比 ZXing 更简单稳定
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.src = url
    await new Promise((r) => {
      img.onload = r
    })
    const canvas = document.createElement('canvas')
    canvas.width = img.width
    canvas.height = img.height
    canvas.getContext('2d').drawImage(img, 0, 0)
    URL.revokeObjectURL(url)
    const imageData = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height)
    const qrResult = jsQR(imageData.data, canvas.width, canvas.height)
    if (!qrResult) throw new Error('no qr found')
    
    handleQrText(qrResult.data)
  } catch (e) {
    console.error(e)
    toast('识别失败，请确认是百度官方 App 的二维码截图')
  }
}

async function handleQrText(text) {
  console.log('[QR decoded]', text)

  // 从二维码 URL 中提取 sign
  const m =
    text.match(/sign=([a-zA-Z0-9_-]{10,})/i) ||
    text.match(/authsid=([a-zA-Z0-9_-]{10,})/i) ||
    text.match(/([a-f0-9]{32})/)

  if (!m) {
    toast('未识别到登录凭证，请确认是百度官方二维码')
    return
  }

  const sign = m[1]
  const code = route.query.code
  if (!code) {
    toast('卡密参数缺失')
    return
  }

  toast('识别成功，正在用账号扫码确认...')
  try {
    const res = await request.post(`/cdkey/scan_qr?code=${code}&sign=${sign}`)
    const data = res.data
    if (data.status === 'success') {
      toast('✓ ' + data.msg)
    } else {
      toast('✗ ' + (data.msg || '扫码失败'))
    }
  } catch (err) {
    const detail = err.response?.data?.detail || err.response?.data?.msg || '网络错误，请重试'
    toast('✗ ' + detail)
  }
}

function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement('script')
    s.src = src
    s.onload = res
    s.onerror = rej
    document.head.appendChild(s)
  })
}

function toast(msg) {
  toastMsg.value = msg
  toastOn.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastOn.value = false
  }, 2500)
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

.rp-root {
  min-height: 100vh;
  background: #0c0e14;
  color: #e2e4ec;
  font-family: 'Outfit', 'PingFang SC', sans-serif;
  padding: 0 16px 64px;
}

/* Topbar */
.rp-topbar {
  max-width: 520px;
  margin: 0 auto;
  padding: 22px 0 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rp-brand {
  display: flex;
  align-items: center;
  gap: 9px;
}
.rp-brand-mark {
  width: 30px;
  height: 30px;
  background: #2563eb;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rp-brand-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.04em;
}
.rp-ping {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}
.rp-ping-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: blink 2s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* Layout */
.rp-center {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
.rp-main {
  max-width: 520px;
  margin: 0 auto;
}

/* Hero */
.rp-hero {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 20px;
  padding: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  animation: fade 0.4s ease;
}
@keyframes fade {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.rp-hero-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.rp-avatar-wrap {
  width: 50px;
  height: 50px;
  flex-shrink: 0;
}
.rp-avatar-img {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #1e2235;
}
.rp-avatar-fallback {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #1a2040;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  color: #5b7cf7;
  border: 2px solid #1e2235;
}
.rp-username {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 6px;
}
.rp-hero-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.rp-vip-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 99px;
}
.vip-svip {
  background: #271e00;
  color: #f59e0b;
  border: 1px solid #92400e;
}
.vip-vip {
  background: #14143d;
  color: #818cf8;
  border: 1px solid #312e81;
}
.vip-free {
  background: #161b24;
  color: #6b7280;
  border: 1px solid #374151;
}
.rp-meta-sep {
  color: #374151;
}
.rp-meta-text {
  font-size: 13px;
  color: #6b7280;
}
.rp-meta-text b {
  color: #e2e4ec;
}
.rp-status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #0d1f14;
  border: 1px solid #14532d;
  border-radius: 99px;
  padding: 5px 12px;
  font-size: 12px;
  color: #22c55e;
  font-weight: 500;
  flex-shrink: 0;
}

/* Stats */
.rp-stats {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 16px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  animation: fade 0.4s ease 0.06s both;
}
.rp-stat {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 4px;
}
.rp-stat-div {
  width: 1px;
  height: 30px;
  background: #1e2235;
  flex-shrink: 0;
}
.rp-stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.rp-stat-icon svg {
  width: 16px;
  height: 16px;
}
.rp-stat-icon.blue {
  background: #1a2040;
  color: #60a5fa;
}
.rp-action-icon.red {
  background: #2d1212;
  color: #f87171;
}
.rp-action-icon.blue {
  background: #1a2040;
  color: #60a5fa;
}
.rp-action-icon.green {
  background: #0d1f14;
  color: #34d399;
}
.rp-stat-icon.amber {
  background: #231a08;
  color: #fbbf24;
}
.rp-stat-icon.green {
  background: #0d1f14;
  color: #34d399;
}
.rp-stat-val {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}
.rp-countdown {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
}
.rp-countdown.expired {
  color: #f87171;
}
.rp-stat-key {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

/* Actions */
.rp-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 10px;
  animation: fade 0.4s ease 0.12s both;
}
.rp-action {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 14px;
  padding: 15px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.1s;
  font-family: inherit;
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
}
.rp-action:hover {
  background: #1a1e2e;
  border-color: #2563eb55;
}
.rp-action:active {
  transform: scale(0.97);
}
.rp-action-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: #1a2040;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #60a5fa;
}
.rp-action-icon svg {
  width: 17px;
  height: 17px;
}

/* CTA */
.rp-cta {
  width: 100%;
  height: 50px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 14px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  transition:
    background 0.15s,
    transform 0.1s;
  margin-bottom: 10px;
  animation: fade 0.4s ease 0.18s both;
  letter-spacing: 0.02em;
}
.rp-cta:hover {
  background: #1d4ed8;
}
.rp-cta:active {
  transform: scale(0.99);
}

/* Drop */
.rp-drop {
  background: #13161f;
  border: 1.5px dashed #1e2235;
  border-radius: 14px;
  padding: 22px;
  text-align: center;
  cursor: pointer;
  transition:
    border-color 0.2s,
    background 0.2s;
  margin-bottom: 10px;
  animation: fade 0.4s ease 0.22s both;
}
.rp-drop.active {
  border-color: #2563eb;
  background: #151c35;
}
.rp-drop-svg {
  width: 28px;
  height: 28px;
  color: #374151;
  display: block;
  margin: 0 auto 8px;
  stroke: #374151;
}
.rp-drop-text {
  font-size: 13px;
  color: #4b5563;
}
.rp-drop-link {
  color: #2563eb;
  font-weight: 500;
}

/* Notice */
.rp-inject-wrap {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 10px;
  animation: fade 0.4s ease 0.2s both;
}
.rp-inject-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 600;
  color: #e2e4ec;
  margin-bottom: 12px;
}
.rp-inject-title svg {
  color: #60a5fa;
  flex-shrink: 0;
}
.rp-inject-steps {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.rp-step {
  font-size: 12px;
  color: #9ca3af;
  background: #1e2235;
  padding: 4px 10px;
  border-radius: 6px;
}
.rp-step-sep {
  font-size: 11px;
  color: #374151;
}
.rp-inject-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.rp-inject-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #2563eb;
  border: none;
  border-radius: 9px;
  padding: 9px 16px;
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.rp-inject-btn:hover {
  background: #1d4ed8;
}
.rp-inject-btn.outline {
  background: #1e2235;
  border: 1px solid #374151;
  color: #9ca3af;
}
.rp-inject-btn.outline:hover {
  background: #252a3e;
  color: #e2e4ec;
}
.rp-inject-tip {
  font-size: 11px;
  color: #4b5563;
}
.rp-notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 12px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
  animation: fade 0.4s ease 0.26s both;
}
.rp-notice svg {
  stroke: #4b5563;
}

/* Skeleton */
.rp-skeleton-card {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 20px;
  padding: 28px;
  width: 100%;
  max-width: 520px;
}
.sk-line {
  background: linear-gradient(90deg, #1e2235 25%, #252a3e 50%, #1e2235 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
  border-radius: 8px;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

/* Error */
.rp-error-card {
  text-align: center;
}
.rp-error-code {
  font-size: 72px;
  font-weight: 700;
  color: #1e2235;
}
.rp-error-msg {
  font-size: 15px;
  color: #6b7280;
  margin-top: 12px;
}

/* Modal overlay */
.rp-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}
.rp-overlay.show {
  opacity: 1;
  pointer-events: all;
}
.rp-modal {
  background: #13161f;
  border: 1px solid #1e2235;
  border-radius: 20px;
  padding: 24px;
  width: 300px;
  text-align: center;
  transform: translateY(10px);
  transition: transform 0.2s;
}
.rp-overlay.show .rp-modal {
  transform: none;
}
.rp-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.rp-modal-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}
.rp-modal-close {
  background: #1e2235;
  border: none;
  border-radius: 8px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.rp-modal-close:hover {
  background: #252a3e;
  color: #e2e4ec;
}
.rp-qr-frame {
  width: 100%;
  aspect-ratio: 1;
  margin: 0 auto 12px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #1e2235;
  background: #000;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rp-scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
  animation: scan 2s infinite linear;
}
@keyframes scan {
  0% { top: 0; }
  50% { top: 100%; }
  100% { top: 0; }
}
.rp-qr-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: opacity 0.3s;
}
.rp-qr-img.scanned {
  opacity: 0.15;
}
.rp-qr-overlay {
  position: absolute;
  inset: 0;
  background: rgba(12, 14, 20, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #22c55e;
}
.rp-spin-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.rp-ring {
  width: 30px;
  height: 30px;
  border: 2.5px solid #1e2235;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.rp-spin-txt {
  font-size: 12px;
  color: #6b7280;
}
.rp-qr-tip {
  font-size: 13px;
  color: #6b7280;
  min-height: 20px;
  margin-bottom: 12px;
}
.rp-refresh {
  background: #1e2235;
  border: none;
  border-radius: 10px;
  padding: 8px 18px;
  color: #9ca3af;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition:
    background 0.15s,
    color 0.15s;
}
.rp-refresh:hover {
  background: #252a3e;
  color: #e2e4ec;
}

/* Toast */
.rp-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  color: #111;
  border-radius: 99px;
  padding: 9px 20px;
  font-size: 13px;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  z-index: 300;
  white-space: nowrap;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}
.rp-toast.show {
  opacity: 1;
}
</style>
