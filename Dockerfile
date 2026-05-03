# syntax=docker/dockerfile:1.4

FROM python:3.11-slim-bookworm AS base

ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    DOCKER_ENV=true \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

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

# ==================== Builder Stage ====================
FROM base AS builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates

RUN if [ ! -f /opt/venv/bin/python ]; then \
        python -m venv /opt/venv; \
    fi && \
    /opt/venv/bin/pip install --upgrade pip

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

COPY backend/requirements.txt ./backend/requirements.txt

# 安装项目依赖
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r backend/requirements.txt

# ★ 新增 opencv-python-headless（服务器无桌面，headless 版体积更小）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install opencv-python-headless

COPY . .


# ==================== Runtime Stage ====================
FROM base AS runtime

LABEL maintainer="zhinianboke" \
      version="2.2.0" \
      description="闲鱼自动回复系统 - 企业级多用户版本，支持自动发货和免拼发货" \
      repository="https://github.com/zhinianboke/xianyu-auto-reply" \
      license="仅供学习使用，禁止商业用途" \
      author="zhinianboke"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if command -v chromium >/dev/null 2>&1; then \
        echo "chromium already installed ($(chromium --version)), skipping."; \
    else \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            curl ca-certificates xz-utils tzdata \
            libjpeg-dev libpng-dev libfreetype6-dev \
            fonts-dejavu-core fonts-liberation \
            libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 \
            libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
            libgbm1 libxss1 libasound2 libatspi2.0-0 \
            libgtk-3-0 libgdk-pixbuf2.0-0 \
            libxcursor1 libxi6 libxrender1 libxext6 \
            libx11-6 libxft2 libxinerama1 libxtst6 \
            libappindicator3-1 libx11-xcb1 libxfixes3 \
            xdg-utils chromium xvfb x11vnc fluxbox \
            libgl1 libglib2.0-0 \
            fonts-wqy-zenhei fonts-wqy-microhei fonts-noto-cjk \
            fonts-noto-color-emoji fonts-unifont \
            xfonts-scalable fonts-ipafont-gothic fonts-freefont-ttf; \
    fi

ENV NODE_PATH=/usr/lib/node_modules

RUN if command -v node >/dev/null 2>&1; then \
        echo "Node.js $(node --version) already installed, skipping."; \
    else \
        set -e; \
        NODE_DIST_URL_PRIMARY="https://npmmirror.com/mirrors/node/latest-v20.x"; \
        NODE_DIST_URL_FALLBACK="https://nodejs.org/dist/latest-v20.x"; \
        ARCH="$(uname -m)"; \
        case "$ARCH" in \
            x86_64)        NODE_PLATFORM="linux-x64"    ;; \
            aarch64|arm64) NODE_PLATFORM="linux-arm64"  ;; \
            armv7l)        NODE_PLATFORM="linux-armv7l" ;; \
            *) echo "Unsupported: $ARCH" >&2; exit 1 ;; \
        esac; \
        fetch_s() { curl --http1.1 -fSL --retry 8 --retry-connrefused --retry-delay 2 \
            --retry-all-errors --connect-timeout 20 --max-time 900 \
            --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
        fetch_l() { curl --http1.1 -fSL -C - --retry 8 --retry-connrefused --retry-delay 2 \
            --retry-all-errors --connect-timeout 20 --max-time 900 \
            --speed-time 30 --speed-limit 1024 -o "$2" "$1"; }; \
        tmpdir="$(mktemp -d)"; cd "$tmpdir"; \
        if fetch_s "$NODE_DIST_URL_PRIMARY/SHASUMS256.txt" sha.txt; then \
            NODE_URL="$NODE_DIST_URL_PRIMARY"; \
        elif fetch_s "$NODE_DIST_URL_FALLBACK/SHASUMS256.txt" sha.txt; then \
            NODE_URL="$NODE_DIST_URL_FALLBACK"; \
        else echo "Cannot fetch SHASUMS256.txt" >&2; exit 1; fi; \
        TAR="$(awk -v p="$NODE_PLATFORM" '$2 ~ ("node-v[0-9.]+-" p "\\.tar\\.xz$"){print $2;exit}' sha.txt)"; \
        SHA="$(awk -v t="$TAR" '$2==t{print $1;exit}' sha.txt)"; \
        fetch_l "$NODE_URL/$TAR" "$TAR" && echo "$SHA $TAR" | sha256sum -c -; \
        tar -xJf "$TAR" -C /usr/local --strip-components=1; \
        cd /; rm -rf "$tmpdir"; \
        echo "Node $(node --version) / npm $(npm --version)"; \
    fi

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

RUN SCRIPTS_DIR="/app/backend/judian/scripts"; \
    if [ -d "$SCRIPTS_DIR/node_modules" ] && \
       [ "$SCRIPTS_DIR/node_modules" -nt "$SCRIPTS_DIR/package-lock.json" ]; then \
        echo "node_modules up to date, skipping npm ci."; \
    else \
        npm ci --prefix "$SCRIPTS_DIR" --omit=dev --no-audit --no-fund; \
    fi

RUN python -m playwright install --with-deps chromium

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# ★ 替换滑块验证文件为 v3（修复：71%距离bug、nc-lang-cnt误判、归一化轨迹）
COPY backend/utils/xianyu_slider_stealth.py /app/backend/utils/xianyu_slider_stealth.py

RUN mkdir -p /app/backend/logs /app/backend/data /app/backend/backups \
             /app/backend/static/uploads/images && \
    chmod 777 /app/backend/logs /app/backend/data /app/backend/backups \
              /app/backend/static/uploads /app/backend/static/uploads/images

RUN echo "ulimit -c 0" >> /etc/profile && \
    chmod +x /app/backend/entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["/app/backend/entrypoint.sh"]