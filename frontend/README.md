# 前端整合说明

`frontend` 是当前整合版主项目的前端源码，不再是独立部署的小项目。

## 当前关系

- 前端源码目录：`frontend/`
- 前端构建产物：`../static/`
- 主后端入口：`../Start.py`
- 主后端服务：`../reply_server.py`
- 网盘/聚店子应用挂载前缀：`/netdisk_api`

## 开发启动

1. 先启动后端：

```bash
python Start.py
```

2. 再启动前端开发服务器：

```bash
cd frontend
npm install
npm run dev
```

默认开发地址是 `http://localhost:5173`。

本地开发时，Vite 已代理以下请求到 `http://localhost:8080`：

- `/api`
- `/netdisk_api`
- 旧主系统相关接口前缀，如 `/login`、`/admin`、`/cookies` 等

## 构建发布

执行下面命令后，前端会直接构建到主项目的 `static/` 目录，供 `reply_server.py` 直接托管：

```bash
cd frontend
$env:FRONTEND_OUT_DIR="../backend/static"
$env:FRONTEND_BUILD_BASE="/static/"
npm run build
```

如果只是独立产出到 `dist/`，直接执行 `npm run build` 即可。
集成构建时必须同时设置 `FRONTEND_BUILD_BASE=/static/`，否则生成的资源链接会指向 `/assets/...`，被后端 SPA 回退路由错误返回成 `index.html`。

## 环境变量

可参考 `frontend/.env.example`：

```env
VITE_API_BASE_URL=/_proxy
# 留空时会自动拼接为 /_proxy/netdisk_api/api
VITE_NETDISK_API_BASE=
# 留空时会自动拼接为 /_proxy/netdisk_api/judian_api
VITE_JUDIAN_API_BASE=
VITE_JUDIAN_API_TIMEOUT_MS=30000
VITE_JUDIAN_LOGIN_API_TIMEOUT_MS=60000
```

如果前端和后端不在同一域名下部署，再按实际网关地址覆盖这几个变量。
如果部署到 Vercel 且未显式设置 `VITE_API_BASE_URL`，前端会默认回退到 `/_proxy`，对应 `vercel.json` 的公网转发规则；网盘和聚店接口也会随之自动走 `/_proxy/netdisk_api/...`。
