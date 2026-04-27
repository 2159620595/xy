# syntax=docker/dockerfile:1.4
# ↑ 启用 BuildKit 扩展语法（支持 --mount=type=cache）

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
    # ✅ 不再设置 PLAYWRIGHT_DOWNLOAD_HOST，改为运行时按需判断
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    DOCKER_ENV=true \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    # ✅ 告诉 playwright 优先使用系统 chromium（apt 已装），跳过自动下载
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# 换源
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

WORKDIR /app

# ==================== Python Builder Stage ====================
FROM base AS builder

# ✅ --mount=type=cache 让 apt 包列表在多次构建间复用，不重复下载索引
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates

# ✅ venv 存在则跳过创建，只升级 pip
RUN if [ ! -f /opt/venv/bin/python ]; then \
        echo "Creating virtualenv..."; \
        python -m venv /opt/venv; \
    else \
        echo "Virtualenv already exists, skipping creation."; \
    fi && \
    /opt/venv/bin/pip install --upgrade pip

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

COPY backend/requirements.txt ./backend/requirements.txt

# ✅ --mount=type=cache 让 pip 下载缓存跨构建复用（不再用 --no-cache-dir）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r backend/requirements.txt

COPY . .


# ==================== Runtime Stage ====================
FROM base AS runtime

LABEL maintainer="zhinianboke" \
      version="2.2.0" \
      description="闲鱼自动回复系统 - 企业级多用户版本，支持自动发货和免拼发货" \
      repository="https://github.com/zhinianboke/xianyu-auto-reply" \
      license="仅供学习使用，禁止商业用途" \
      author="zhinianboke" \
      build-date="" \
      vcs-ref=""

# ✅ --mount=type=cache 让 apt 缓存跨构建复用，避免重复下载 deb 包
# ✅ 判断 chromium 是否已安装，已装则跳过（层缓存失效时的防护）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if command -v chromium >/dev/null 2>&1; then \
        echo "chromium already installed ($(chromium --version)), skipping apt install."; \
    else \
        echo "Installing system packages..." && \
        apt-get update && \
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
            libglib2.0-0; \
    fi

ENV NODE_PATH=/usr/lib/node_modules

# ✅ 判断 Node.js 是否已安装，已装则跳过下载；未装则镜像优先，失败 fallback 官方
RUN if command -v node >/dev/null 2>&1; then \
        echo "Node.js $(node --version) already installed, skipping download."; \
    else \
        set -e; \
        NODE_DIST_URL_PRIMARY="https://npmmirror.com/mirrors/node/latest-v20.x"; \
        NODE_DIST_URL_FALLBACK="https://nodejs.org/dist/latest-v20.x"; \
        ARCH="$(uname -m)"; \
        case "$ARCH" in \
            x86_64)       NODE_PLATFORM="linux-x64"    ;; \
            aarch64|arm64) NODE_PLATFORM="linux-arm64"  ;; \
            armv7l)        NODE_PLATFORM="linux-armv7l" ;; \
            *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
        esac; \
        fetch_small() { curl --http1.1 -fSL --retry 8 --retry-connrefused --retry-delay 2 \
            --retry-all-errors --connect-timeout 20 --max-time 900 \
            --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
        fetch_large() { curl --http1.1 -fSL -C - --retry 8 --retry-connrefused --retry-delay 2 \
            --retry-all-errors --connect-timeout 20 --max-time 900 \
            --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
        tmpdir="$(mktemp -d)"; \
        cd "$tmpdir"; \
        SHASUMS_FILE=""; NODE_DIST_URL=""; \
        if fetch_small "$NODE_DIST_URL_PRIMARY/SHASUMS256.txt" SHASUMS256.primary.txt; then \
            NODE_DIST_URL="$NODE_DIST_URL_PRIMARY"; SHASUMS_FILE="SHASUMS256.primary.txt"; \
        elif fetch_small "$NODE_DIST_URL_FALLBACK/SHASUMS256.txt" SHASUMS256.fallback.txt; then \
            NODE_DIST_URL="$NODE_DIST_URL_FALLBACK"; SHASUMS_FILE="SHASUMS256.fallback.txt"; \
        else \
            echo "Failed to download SHASUMS256.txt from both mirrors" >&2; exit 1; \
        fi; \
        NODE_TARBALL="$(awk -v p="$NODE_PLATFORM" '$2 ~ ("node-v[0-9.]+-" p "\\.tar\\.xz$"){print $2; exit}' "$SHASUMS_FILE")"; \
        [ -n "$NODE_TARBALL" ] || { echo "Cannot determine tarball for $NODE_PLATFORM" >&2; exit 1; }; \
        EXPECTED_SHA="$(awk -v t="$NODE_TARBALL" '$2==t{print $1;exit}' "$SHASUMS_FILE")"; \
        [ -n "$EXPECTED_SHA" ] || { echo "Cannot find SHA256 for $NODE_TARBALL" >&2; exit 1; }; \
        if fetch_large "$NODE_DIST_URL/$NODE_TARBALL" "$NODE_TARBALL" && \
           echo "$EXPECTED_SHA $NODE_TARBALL" | sha256sum -c -; then \
            : ; \
        else \
            echo "Primary download failed or checksum mismatch, trying other mirror..."; \
            if [ "$NODE_DIST_URL" = "$NODE_DIST_URL_PRIMARY" ]; then \
                OTHER_URL="$NODE_DIST_URL_FALLBACK"; OTHER_SUMS="SHASUMS256.fallback.txt"; \
            else \
                OTHER_URL="$NODE_DIST_URL_PRIMARY"; OTHER_SUMS="SHASUMS256.primary.txt"; \
            fi; \
            [ -f "$OTHER_SUMS" ] || fetch_small "$OTHER_URL/SHASUMS256.txt" "$OTHER_SUMS"; \
            EXPECTED_SHA="$(awk -v t="$NODE_TARBALL" '$2==t{print $1;exit}' "$OTHER_SUMS")"; \
            rm -f "$NODE_TARBALL"; \
            fetch_large "$OTHER_URL/$NODE_TARBALL" "$NODE_TARBALL"; \
            echo "$EXPECTED_SHA $NODE_TARBALL" | sha256sum -c -; \
        fi; \
        tar -xJf "$NODE_TARBALL" -C /usr/local --strip-components=1; \
        cd /; rm -rf "$tmpdir"; \
        echo "Node.js installed: $(node --version), npm: $(npm --version)"; \
    fi

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

# ✅ 判断 node_modules 是否存在且比 package-lock.json 新，是则跳过 npm ci
RUN SCRIPTS_DIR="/app/backend/judian/scripts"; \
    if [ -d "$SCRIPTS_DIR/node_modules" ] && \
       [ "$SCRIPTS_DIR/node_modules" -nt "$SCRIPTS_DIR/package-lock.json" ]; then \
        echo "node_modules already up to date, skipping npm ci."; \
    else \
        echo "Running npm ci..."; \
        npm ci --prefix "$SCRIPTS_DIR" --omit=dev --no-audit --no-fund; \
    fi

# ✅ 系统 chromium 存在直接用，跳过 playwright 下载
RUN if command -v chromium >/dev/null 2>&1; then \
        echo "Using system chromium: $(chromium --version), skipping playwright download."; \
    else \
        echo "System chromium not found, downloading via playwright..."; \
        chromium_dir=$(find "${PLAYWRIGHT_BROWSERS_PATH}" -maxdepth 1 -name "chromium-*" -type d 2>/dev/null | head -1); \
        if [ -n "$chromium_dir" ]; then \
            echo "Playwright chromium already exists at $chromium_dir, skipping."; \
        else \
            PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright \
                playwright install chromium \
            || PLAYWRIGHT_DOWNLOAD_HOST="" playwright install chromium; \
        fi; \
    fi

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# 创建必要的目录并设置权限
RUN mkdir -p /app/backend/logs /app/backend/data /app/backend/backups \
             /app/backend/static/uploads/images && \
    chmod 777 /app/backend/logs /app/backend/data /app/backend/backups \
              /app/backend/static/uploads /app/backend/static/uploads/images

RUN echo "ulimit -c 0" >> /etc/profile

RUN chmod +x /app/backend/entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["/app/backend/entrypoint.sh"]
