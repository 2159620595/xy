# 全链路稳定性与性能首轮优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先产出一份可复查的全链路诊断结论，再以最小前端改动修复 3 个已经识别出的高价值稳定性问题：Judian 公共接口缺少统一超时、Judian 会话 `fetch` 缺少显式超时、Netdisk 会话引导 `axios.post` 缺少显式超时。

**Architecture:** 首轮不做跨系统重构，只在前端请求层做小范围收敛。先把静态诊断结果写入文档，再增加一个专用的超时工具文件，统一 `fetch` 和 `axios` 的超时来源，最后把该工具接入 `judian-auth`、`netdisk-request` 和 `api/judian` 三条链路，并用最小单元测试和构建验证收口。

**Tech Stack:** Vue 3, TypeScript, Axios, Fetch API, Vite, Vitest

---

## File Map

- Create: `docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md`
- Create: `frontend/src/utils/http-timeout.ts`
- Create: `frontend/src/utils/http-timeout.test.ts`
- Create: `frontend/src/api/judian.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/src/utils/request.ts`
- Modify: `frontend/src/utils/judian-auth.ts`
- Modify: `frontend/src/utils/netdisk-request.ts`
- Modify: `frontend/src/api/judian.ts`

### Task 1: 写出首轮诊断报告

**Files:**

- Create: `docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md`
- Inspect: `frontend/src/utils/request.ts`
- Inspect: `frontend/src/utils/judian-auth.ts`
- Inspect: `frontend/src/utils/netdisk-request.ts`
- Inspect: `frontend/src/api/judian.ts`
- Inspect: `backend/reply_server.py`
- Inspect: `backend/Start.py`

- [ ] **Step 1: 创建诊断报告文件**

```md
# 首轮稳定性与性能诊断

## 范围

- `frontend/`
- `backend/Start.py`
- `backend/reply_server.py`
- `backend/judian/`
- `backend/netdisk/`

## 已确认的高优先问题

1. `frontend/src/api/judian.ts`
   - Judian 公共兑换与批量解锁接口直接使用裸 `axios`
   - 当前没有复用 `JUDIAN_API_TIMEOUT_MS`
   - 风险：公网请求在异常链路下可能长时间挂起，页面反馈慢

2. `frontend/src/utils/judian-auth.ts`
   - `verifyStoredJudianSession()` 和 `ensureJudianSession()` 直接使用裸 `fetch`
   - 当前没有显式超时控制
   - 风险：聚店会话校验或同步异常时会卡住调用链

3. `frontend/src/utils/netdisk-request.ts`
   - `ensureNetdiskSession()` 内部使用裸 `axios.post`
   - 当前没有显式 `timeout`
   - 风险：网盘会话引导在后端抖动时会长时间占用页面等待

## 暂不进入首轮实现的问题

- `backend/reply_server.py` 体积大，适合后续拆专项
- `backend/Start.py` 启动职责较多，但首轮不动启动流程
- 主后端和网盘后端已有局部缓存，不在没有运行证据的情况下盲改

## 首轮落地项

1. 增加前端统一超时工具
2. 为 Judian 会话校验和会话同步补显式超时
3. 为 Netdisk 会话引导补显式超时
4. 为 Judian 公共接口切换到带超时的共享客户端
```

- [ ] **Step 2: 运行静态排查命令并核对文档内容**

Run:

```powershell
Get-Content frontend/src/utils/request.ts
Get-Content frontend/src/utils/judian-auth.ts
Get-Content frontend/src/utils/netdisk-request.ts
Get-Content frontend/src/api/judian.ts
```

Expected: 能直接看到 3 处问题中的裸 `fetch` / 裸 `axios` 调用仍存在，并且报告中的文件路径与问题描述一致。

- [ ] **Step 3: 提交诊断报告**

```bash
git add docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md
git commit -m "docs: add first-pass stability diagnosis report"
```

### Task 2: 增加统一超时工具和最小测试

**Files:**

- Create: `frontend/src/utils/http-timeout.ts`
- Create: `frontend/src/utils/http-timeout.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/src/utils/request.ts`

- [ ] **Step 1: 先写失败测试**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_REQUEST_TIMEOUT_MS,
  createTimeoutController,
  parseTimeoutMs,
} from "./http-timeout";

describe("parseTimeoutMs", () => {
  it("falls back for empty values", () => {
    expect(parseTimeoutMs("", 30000)).toBe(30000);
    expect(parseTimeoutMs(undefined, 30000)).toBe(30000);
  });

  it("accepts positive integers", () => {
    expect(parseTimeoutMs("15000", 30000)).toBe(15000);
    expect(parseTimeoutMs(45000, 30000)).toBe(45000);
  });

  it("rejects zero and invalid values", () => {
    expect(parseTimeoutMs("0", 30000)).toBe(30000);
    expect(parseTimeoutMs("-1", 30000)).toBe(30000);
    expect(parseTimeoutMs("abc", 30000)).toBe(30000);
  });
});

describe("createTimeoutController", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("aborts when timeout expires", () => {
    vi.useFakeTimers();
    const { signal } = createTimeoutController(25);
    expect(signal.aborted).toBe(false);
    vi.advanceTimersByTime(25);
    expect(signal.aborted).toBe(true);
  });

  it("does not arm a timer for non-positive timeout", () => {
    const { signal, cancel } = createTimeoutController(0);
    expect(signal.aborted).toBe(false);
    cancel();
  });
});

describe("DEFAULT_REQUEST_TIMEOUT_MS", () => {
  it("is a positive integer", () => {
    expect(DEFAULT_REQUEST_TIMEOUT_MS).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: 安装并配置最小测试命令**

Modify `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "devDependencies": {
    "@types/node": "^24.12.2",
    "@vitejs/plugin-vue": "^6.0.6",
    "@vue/tsconfig": "^0.9.1",
    "typescript": "~6.0.2",
    "vite": "^8.0.9",
    "vitest": "^3.2.4",
    "vue-tsc": "^3.2.7"
  }
}
```

- [ ] **Step 3: 运行测试，确认当前失败**

Run:

```powershell
Set-Location frontend
npm install
npm run test -- src/utils/http-timeout.test.ts
```

Expected: FAIL，提示 `Cannot find module './http-timeout'` 或导出符号不存在。

- [ ] **Step 4: 写最小实现**

Create `frontend/src/utils/http-timeout.ts`:

```ts
const DEFAULT_FALLBACK_TIMEOUT_MS = 30000;

export const parseTimeoutMs = (
  value: string | number | undefined,
  fallback: number,
) => {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
};

export const DEFAULT_REQUEST_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env.VITE_API_TIMEOUT_MS,
  DEFAULT_FALLBACK_TIMEOUT_MS,
);

export const createTimeoutController = (timeoutMs: number) => {
  const controller = new AbortController();
  if (!(timeoutMs > 0)) {
    return {
      signal: controller.signal,
      cancel: () => {},
    };
  }

  const timer = globalThis.setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  return {
    signal: controller.signal,
    cancel: () => globalThis.clearTimeout(timer),
  };
};
```

Modify `frontend/src/utils/request.ts`:

```ts
import { DEFAULT_REQUEST_TIMEOUT_MS } from "@/utils/http-timeout";

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_REQUEST_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
  },
});
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```powershell
Set-Location frontend
npm run test -- src/utils/http-timeout.test.ts
```

Expected: PASS，`parseTimeoutMs` 和 `createTimeoutController` 全部通过。

- [ ] **Step 6: 提交超时工具**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/utils/http-timeout.ts frontend/src/utils/http-timeout.test.ts frontend/src/utils/request.ts
git commit -m "feat: add shared frontend request timeout helpers"
```

### Task 3: 把超时工具接入 Judian 与 Netdisk 关键链路

**Files:**

- Modify: `frontend/src/utils/judian-auth.ts`
- Modify: `frontend/src/utils/netdisk-request.ts`
- Modify: `frontend/src/api/judian.ts`
- Create: `frontend/src/api/judian.test.ts`

- [ ] **Step 1: 先写失败测试**

Create `frontend/src/api/judian.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { JUDIAN_API_TIMEOUT_MS, judianApi, judianPublicClient } from "./judian";

describe("judian clients", () => {
  it("keeps authenticated client timeout aligned", () => {
    expect(judianApi.client.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the same timeout for public client", () => {
    expect(judianPublicClient.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run:

```powershell
Set-Location frontend
npm run test -- src/api/judian.test.ts
```

Expected: FAIL，提示 `judianPublicClient` 尚未导出，或者公共客户端超时不一致。

- [ ] **Step 3: 实现最小改动**

Modify `frontend/src/utils/judian-auth.ts`:

```ts
import {
  DEFAULT_REQUEST_TIMEOUT_MS,
  createTimeoutController,
} from "@/utils/http-timeout";

export async function verifyStoredJudianSession(token: string) {
  if (!token) return false;
  const { signal, cancel } = createTimeoutController(
    DEFAULT_REQUEST_TIMEOUT_MS,
  );
  try {
    const response = await fetch(JUDIAN_VERIFY_URL, {
      method: "GET",
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal,
    });
    if (!response.ok) return false;
    const data = await response.json();
    return Boolean(data?.authenticated);
  } catch {
    return false;
  } finally {
    cancel();
  }
}
```

Continue in the same file for session bootstrap:

```ts
const { signal, cancel } = createTimeoutController(DEFAULT_REQUEST_TIMEOUT_MS);
try {
  const response = await fetch(JUDIAN_SESSION_BOOTSTRAP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username: mainUser.username,
      role: mainUser.role || "admin",
    }),
    signal,
  });
  const data = await response.json().catch(() => null);
  // 保留原有响应处理逻辑
} catch {
  return false;
} finally {
  cancel();
}
```

Modify `frontend/src/utils/netdisk-request.ts`:

```ts
import { NETDISK_API_BASE_URL } from "@/utils/request";
import { DEFAULT_REQUEST_TIMEOUT_MS } from "@/utils/http-timeout";

const response = await axios.post(
  `${NETDISK_API_BASE}/netdisk/session`,
  {
    username: mainUser.username,
    role: mainUser.role || "admin",
  },
  {
    timeout: DEFAULT_REQUEST_TIMEOUT_MS,
    withCredentials: true,
  },
);
```

Modify `frontend/src/api/judian.ts`:

```ts
export const judianPublicClient = axios.create({
  baseURL: JUDIAN_API_BASE,
  timeout: JUDIAN_API_TIMEOUT_MS,
});

export const judianApi = {
  client: judianClient,
  // ...
  publicRedeemInfo: (code: string, sessionId?: string, forceRefresh = false) =>
    judianPublicClient.get("/cdkey/redeem", {
      params: { code, session: sessionId || "", refresh: forceRefresh ? 1 : 0 },
    }),
  publicUnlockDetail: (sessionId: string) =>
    judianPublicClient.get(`/public/unlock/${sessionId}`),
  publicUnlockBatchDetail: (sessionId: string) =>
    judianPublicClient.get(`/public/unlock/${sessionId}/batch`),
  publicUnlockBatchPreview: (
    sessionId: string,
    params: { count: number; vipId?: string; packageType?: string },
  ) =>
    judianPublicClient.get(`/public/unlock/${sessionId}/batch/preview`, {
      params: {
        count: params.count,
        vip_id: params.vipId || "",
        package_type: params.packageType || "",
      },
    }),
  publicUnlockScan: (sessionId: string, data: Record<string, unknown>) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/scan`, data),
  publicUnlockBatchPurchase: (
    sessionId: string,
    data: Record<string, unknown>,
  ) => judianPublicClient.post(`/public/unlock/${sessionId}/batch`, data),
  publicUnlockBatchCancel: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/batch/cancel`),
  publicUnlockConfirm: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/confirm`),
  publicUnlockComplete: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/complete`),
};
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
Set-Location frontend
npm run test -- src/utils/http-timeout.test.ts src/api/judian.test.ts
```

Expected: PASS，公共客户端和登录态客户端的超时配置一致，超时工具测试继续通过。

- [ ] **Step 5: 构建前端做回归验证**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: PASS，`vue-tsc` 和 `vite build` 都成功。

- [ ] **Step 6: 提交链路修复**

```bash
git add frontend/src/utils/judian-auth.ts frontend/src/utils/netdisk-request.ts frontend/src/api/judian.ts frontend/src/api/judian.test.ts
git commit -m "fix: add explicit timeouts for judian and netdisk request flows"
```

### Task 4: 更新诊断报告并做最终核对

**Files:**

- Modify: `docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md`

- [ ] **Step 1: 在诊断报告中补充已完成项**

Append to `docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md`:

```md
## 首轮已落地修复

1. 新增 `frontend/src/utils/http-timeout.ts`
   - 统一前端默认请求超时
   - 为 `fetch` 请求提供显式取消能力

2. 修复 `frontend/src/utils/judian-auth.ts`
   - 会话校验与会话同步现在有显式超时

3. 修复 `frontend/src/utils/netdisk-request.ts`
   - 网盘会话引导请求现在有显式超时

4. 修复 `frontend/src/api/judian.ts`
   - 聚店公共兑换与批量解锁接口改为复用共享客户端
   - 公共接口与鉴权接口超时配置一致

## 验证

- `npm run test -- src/utils/http-timeout.test.ts src/api/judian.test.ts`
- `npm run build`
```

- [ ] **Step 2: 运行最终核对命令**

Run:

```powershell
git diff --check
Set-Location frontend
npm run test -- src/utils/http-timeout.test.ts src/api/judian.test.ts
npm run build
```

Expected: 无空白错误；测试通过；前端构建通过。

- [ ] **Step 3: 提交最终报告更新**

```bash
git add docs/superpowers/reports/2026-04-30-stability-performance-diagnosis.md
git commit -m "docs: record first-pass stability fixes"
```

## Self-Review

- Spec coverage:
  - “全链路诊断优先” 由 Task 1 和 Task 4 覆盖
  - “首轮只修 1 到 3 个低风险问题” 由 Task 3 的 3 个请求层修复覆盖
  - “可验证” 由 Task 2、Task 3、Task 4 的测试与构建命令覆盖
- Placeholder scan:
  - 没有 `TODO`、`TBD`、`适当处理` 这类空泛表述
  - 每个代码变更步骤都给了目标代码块
- Type consistency:
  - 新工具统一命名为 `parseTimeoutMs`、`createTimeoutController`、`DEFAULT_REQUEST_TIMEOUT_MS`
  - `judianPublicClient` 在测试和实现中的导出名称一致
