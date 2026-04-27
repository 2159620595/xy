# 使用Python 3.11作为基础镜像
FROM python:3.11-slim-bookworm AS base

ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
    PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    DOCKER_ENV=true \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN set -e; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|http://deb.debian.org/debian|https://${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
      sed -i "s|http://security.debian.org/debian-security|https://${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
      sed -i "s|http://deb.debian.org/debian-security|https://${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i "s|http://deb.debian.org/debian|https://${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list; \
      sed -i "s|http://security.debian.org/debian-security|https://${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list; \
      sed -i "s|http://deb.debian.org/debian-security|https://${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list; \
    fi

# 设置工作目录
WORKDIR /app

# ==================== Python Builder Stage ====================
FROM base AS builder

# 安装基础依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

# 复制requirements.txt并安装Python依赖
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制项目文件
COPY . .

# 项目已完全开源，无需编译二进制模块

# Runtime stage: only keep what is needed to run the app
FROM base AS runtime

# 设置标签信息
LABEL maintainer="zhinianboke" \
      version="2.2.0" \
      description="闲鱼自动回复系统 - 企业级多用户版本，支持自动发货和免拼发货" \
      repository="https://github.com/zhinianboke/xianyu-auto-reply" \
      license="仅供学习使用，禁止商业用途" \
      author="zhinianboke" \
      build-date="" \
      vcs-ref=""

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        xz-utils \
        tzdata \
        # 图像处理依赖
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        fonts-dejavu-core \
        fonts-liberation \
        # Playwright浏览器依赖
        libnss3 \
        libnspr4 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libxss1 \
        libasound2 \
        libatspi2.0-0 \
        libgtk-3-0 \
        libgdk-pixbuf2.0-0 \
        libxcursor1 \
        libxi6 \
        libxrender1 \
        libxext6 \
        libx11-6 \
        libxft2 \
        libxinerama1 \
        libxtst6 \
        libappindicator3-1 \
        libx11-xcb1 \
        libxfixes3 \
        xdg-utils \
        chromium \
        xvfb \
        x11vnc \
        fluxbox \
        # OpenCV运行时依赖
        libgl1 \
        libglib2.0-0 \
        && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV NODE_PATH=/usr/lib/node_modules

# Install Node.js from a China mirror to speed up downloads in CI.
RUN set -e; \
    NODE_DIST_URL_PRIMARY="https://npmmirror.com/mirrors/node/latest-v20.x"; \
    NODE_DIST_URL_FALLBACK="https://nodejs.org/dist/latest-v20.x"; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
      x86_64) NODE_PLATFORM="linux-x64" ;; \
      aarch64|arm64) NODE_PLATFORM="linux-arm64" ;; \
      armv7l) NODE_PLATFORM="linux-armv7l" ;; \
      *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac; \
    fetch_small() { curl --http1.1 -fSL --retry 8 --retry-connrefused --retry-delay 2 --retry-all-errors --connect-timeout 20 --max-time 900 --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
    fetch_large() { curl --http1.1 -fSL -C - --retry 8 --retry-connrefused --retry-delay 2 --retry-all-errors --connect-timeout 20 --max-time 900 --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
    tmpdir="$(mktemp -d)"; \
    cd "$tmpdir"; \
    SHASUMS_FILE=""; \
    NODE_DIST_URL=""; \
    if fetch_small "$NODE_DIST_URL_PRIMARY/SHASUMS256.txt" SHASUMS256.primary.txt; then \
      NODE_DIST_URL="$NODE_DIST_URL_PRIMARY"; \
      SHASUMS_FILE="SHASUMS256.primary.txt"; \
    elif fetch_small "$NODE_DIST_URL_FALLBACK/SHASUMS256.txt" SHASUMS256.fallback.txt; then \
      NODE_DIST_URL="$NODE_DIST_URL_FALLBACK"; \
      SHASUMS_FILE="SHASUMS256.fallback.txt"; \
    else \
      echo "Failed to download SHASUMS256.txt from both primary and fallback mirrors" >&2; \
      exit 1; \
    fi; \
    NODE_TARBALL="$(awk -v platform="$NODE_PLATFORM" '$2 ~ ("node-v[0-9.]+-" platform "\\.tar\\.xz$"){print $2; exit}' "$SHASUMS_FILE")"; \
    if [ -z "$NODE_TARBALL" ]; then echo "Failed to determine Node.js tarball for platform: $NODE_PLATFORM" >&2; exit 1; fi; \
    EXPECTED_SHA="$(awk -v tar="$NODE_TARBALL" '$2 == tar {print $1; exit}' "$SHASUMS_FILE")"; \
    if [ -z "$EXPECTED_SHA" ]; then echo "Failed to find expected SHA256 for: $NODE_TARBALL" >&2; exit 1; fi; \
    if fetch_large "$NODE_DIST_URL/$NODE_TARBALL" "$NODE_TARBALL"; then \
      if echo "$EXPECTED_SHA  $NODE_TARBALL" | sha256sum -c -; then \
        :; \
      else \
        rm -f "$NODE_TARBALL"; \
        fetch_small "$NODE_DIST_URL/$NODE_TARBALL" "$NODE_TARBALL"; \
        echo "$EXPECTED_SHA  $NODE_TARBALL" | sha256sum -c -; \
      fi; \
    else \
      if [ "$NODE_DIST_URL" = "$NODE_DIST_URL_PRIMARY" ]; then OTHER_URL="$NODE_DIST_URL_FALLBACK"; OTHER_SHASUMS="SHASUMS256.fallback.txt"; else OTHER_URL="$NODE_DIST_URL_PRIMARY"; OTHER_SHASUMS="SHASUMS256.primary.txt"; fi; \
      if [ ! -f "$OTHER_SHASUMS" ]; then fetch_small "$OTHER_URL/SHASUMS256.txt" "$OTHER_SHASUMS"; fi; \
      EXPECTED_SHA_OTHER="$(awk -v tar="$NODE_TARBALL" '$2 == tar {print $1; exit}' "$OTHER_SHASUMS")"; \
      if [ -z "$EXPECTED_SHA_OTHER" ]; then echo "Failed to find expected SHA256 for: $NODE_TARBALL (other mirror)" >&2; exit 1; fi; \
      rm -f "$NODE_TARBALL"; \
      fetch_large "$OTHER_URL/$NODE_TARBALL" "$NODE_TARBALL"; \
      if echo "$EXPECTED_SHA_OTHER  $NODE_TARBALL" | sha256sum -c -; then \
        :; \
      else \
        rm -f "$NODE_TARBALL"; \
        fetch_small "$OTHER_URL/$NODE_TARBALL" "$NODE_TARBALL"; \
        echo "$EXPECTED_SHA_OTHER  $NODE_TARBALL" | sha256sum -c -; \
      fi; \
    fi; \
    tar -xJf "$NODE_TARBALL" -C /usr/local --strip-components=1; \
    cd /; \
    rm -rf "$tmpdir"; \
    node --version; \
    npm --version

# 设置时区        
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 验证Node.js安装并设置环境变量
RUN node --version && npm --version

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

RUN npm ci --prefix /app/backend/judian/scripts --omit=dev --no-audit --no-fund

RUN chromium_dir=$(find "${PLAYWRIGHT_BROWSERS_PATH}" -maxdepth 1 -name "chromium-*" -type d 2>/dev/null | head -1); \
    if [ -n "$chromium_dir" ]; then \
        echo "Playwright chromium already exists at $chromium_dir, skipping download."; \
    else \
        echo "Playwright chromium not found, downloading..." && \
        playwright install chromium \
        || (echo "Mirror failed, falling back to official..." && \
            PLAYWRIGHT_DOWNLOAD_HOST="" playwright install chromium); \
    fi

# 创建必要的目录并设置权限
RUN mkdir -p /app/backend/logs /app/backend/data /app/backend/backups /app/backend/static/uploads/images && \
    chmod 777 /app/backend/logs /app/backend/data /app/backend/backups /app/backend/static/uploads /app/backend/static/uploads/images

# 配置系统限制，防止core文件生成
RUN echo "ulimit -c 0" >> /etc/profile

# 注意: 为了简化权限问题，使用root用户运行
# 在生产环境中，建议配置适当的用户映射

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

RUN chmod +x /app/backend/entrypoint.sh

# 启动命令
CMD ["/app/backend/entrypoint.sh"]
