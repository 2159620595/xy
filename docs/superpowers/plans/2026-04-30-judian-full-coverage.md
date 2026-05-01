# 聚点全业务诊断与测试补齐首轮 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为聚点前后端主要业务建立首轮可重复执行的验证基线，补齐最小自动化测试和冒烟验证，并只修复阻塞测试或影响主链路的高风险问题。

**Architecture:** 首轮不做聚点系统重构，而是按链路分层补验证。前端先在 `judian-auth.ts`、`judian.ts` 和 `RedeemView.vue` 建最小测试切口；后端在 `backend/judian/judian_backend/__init__.py` 周边建立最小 `unittest` 入口；真实远端依赖通过 `test-vip.js` 的冒烟命令补足。每个任务都先写测试或验证用例，再决定是否需要最小代码修复。

**Tech Stack:** Vue 3, TypeScript, Vitest, Vue Test Utils, jsdom, FastAPI, Python unittest, FastAPI TestClient, Node.js

---

## File Map

- Create: `docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md`
- Create: `frontend/src/utils/judian-auth.test.ts`
- Create: `frontend/src/views/judian/RedeemView.test.ts`
- Create: `backend/judian/tests/__init__.py`
- Create: `backend/judian/tests/test_app_endpoints.py`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/api/judian.test.ts`
- Modify: `frontend/src/utils/judian-auth.ts`
- Modify: `frontend/src/api/judian.ts`
- Modify: `frontend/src/views/judian/RedeemView.vue`
- Modify: `backend/judian/judian_backend/__init__.py`
- Inspect: `backend/judian/scripts/test-vip.js`

### Task 1: 建立聚点专项报告骨架和覆盖矩阵

**Files:**

- Create: `docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md`
- Inspect: `frontend/src/api/judian.ts`
- Inspect: `frontend/src/utils/judian-auth.ts`
- Inspect: `frontend/src/views/judian/RedeemView.vue`
- Inspect: `backend/judian/judian_backend/__init__.py`
- Inspect: `backend/judian/scripts/test-vip.js`

- [ ] **Step 1: 创建聚点专项报告文件**

```md
# 聚点全业务诊断与测试报告

## 范围

- `frontend/src/api/judian.ts`
- `frontend/src/utils/judian-auth.ts`
- `frontend/src/views/judian/`
- `backend/judian/judian_backend/__init__.py`
- `backend/judian/scripts/test-vip.js`

## 业务链路清单

| 链路           | 入口文件                                    | 验证方式                | 当前状态 |
| -------------- | ------------------------------------------- | ----------------------- | -------- |
| 会话校验与同步 | `frontend/src/utils/judian-auth.ts`         | Vitest                  | 待补     |
| 管理端 API     | `frontend/src/api/judian.ts`                | Vitest                  | 已有少量 |
| 公开兑换页     | `frontend/src/views/judian/RedeemView.vue`  | Vitest + Vue Test Utils | 待补     |
| 后端接口       | `backend/judian/judian_backend/__init__.py` | unittest + TestClient   | 待补     |
| 远端动作脚本   | `backend/judian/scripts/test-vip.js`        | 冒烟命令                | 待整理   |

## 自动化测试结果

## 冒烟测试结果

## 已修复问题

## 未覆盖与受限项
```

- [ ] **Step 2: 运行静态盘点命令并补全覆盖矩阵**

Run:

```powershell
git -C "d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass" grep -n "judian" -- frontend/src
git -C "d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass" grep -n "@app\." -- backend/judian/judian_backend/__init__.py
git -C "d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass" grep -n "onepath\|smoke\|login\|list\|buy\|status\|autopay\|batch" -- backend/judian/scripts/test-vip.js
```

Expected: 能把聚点链路映射到具体文件和动作名称，报告中的“业务链路清单”不再留空。

- [ ] **Step 3: 提交报告骨架**

```bash
git add docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md
git commit -m "docs: add judian coverage report skeleton"
```

### Task 2: 为聚点会话链路补最小前端测试

**Files:**

- Create: `frontend/src/utils/judian-auth.test.ts`
- Modify: `frontend/src/utils/judian-auth.ts`

- [ ] **Step 1: 写 `judian-auth` 失败测试**

Create `frontend/src/utils/judian-auth.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearJudianSession,
  ensureJudianSession,
  getJudianToken,
  verifyStoredJudianSession,
} from "./judian-auth";

const replaceMock = vi.fn();

const installLocationMock = () => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      pathname: "/judian/accounts",
      search: "?tab=main",
      replace: replaceMock,
    },
  });
};

describe("verifyStoredJudianSession", () => {
  beforeEach(() => {
    localStorage.clear();
    replaceMock.mockReset();
    installLocationMock();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns false when remote verify rejects", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(verifyStoredJudianSession("token-1")).resolves.toBe(false);
  });
});

describe("ensureJudianSession", () => {
  beforeEach(() => {
    localStorage.clear();
    replaceMock.mockReset();
    installLocationMock();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearJudianSession();
  });

  it("stores token after successful bootstrap", async () => {
    localStorage.setItem(
      "user_info",
      JSON.stringify({ username: "admin", role: "admin" }),
    );
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ authenticated: false }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          token: "fresh-token",
          username: "admin",
          is_admin: true,
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(ensureJudianSession()).resolves.toBe(true);
    expect(getJudianToken()).toBe("fresh-token");
  });

  it("clears main auth and redirects on bootstrap 401", async () => {
    localStorage.setItem(
      "user_info",
      JSON.stringify({ username: "admin", role: "admin" }),
    );
    localStorage.setItem("auth_token", "main-token");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "expired" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(ensureJudianSession(true)).resolves.toBe(false);
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(replaceMock).toHaveBeenCalledWith(
      "/login?redirect=%2Fjudian%2Faccounts%3Ftab%3Dmain",
    );
  });
});
```

- [ ] **Step 2: 运行测试，确认首轮红灯**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/utils/judian-auth.test.ts
```

Expected: FAIL。优先接受的失败原因是某个会话恢复断言不成立，或 `window.location` 模拟下的跳转行为与测试预期不一致。

- [ ] **Step 3: 按失败结果做最小修复**

Only if the test fails on real behavior, adjust `frontend/src/utils/judian-auth.ts` with the smallest possible change. Prefer code in this shape:

```ts
const redirectToLogin = () => {
  if (
    typeof window === "undefined" ||
    window.location.pathname.startsWith("/login")
  ) {
    return;
  }

  const redirect = `${window.location.pathname}${window.location.search || ""}`;
  window.location.replace(`/login?redirect=${encodeURIComponent(redirect)}`);
};
```

If the assertions already pass after writing the test, do not modify production code. Commit the characterization test only.

- [ ] **Step 4: 运行测试确认转绿**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/utils/judian-auth.test.ts
```

Expected: PASS，3 个测试全部通过。

- [ ] **Step 5: 提交会话链路测试**

```bash
git add frontend/src/utils/judian-auth.test.ts frontend/src/utils/judian-auth.ts
git commit -m "test: cover judian session bootstrap flows"
```

### Task 3: 扩展聚点 API 测试并锁定公共接口边界

**Files:**

- Modify: `frontend/src/api/judian.test.ts`
- Modify: `frontend/src/api/judian.ts`

- [ ] **Step 1: 先扩展失败测试**

Replace `frontend/src/api/judian.test.ts` with:

```ts
import { describe, expect, it } from "vitest";
import {
  JUDIAN_API_BASE,
  JUDIAN_API_TIMEOUT_MS,
  JUDIAN_LOGIN_API_TIMEOUT_MS,
  judianApi,
  judianPublicClient,
} from "./judian";

describe("judian clients", () => {
  it("keeps authenticated client timeout aligned", () => {
    expect(judianApi.client.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the same timeout for public client", () => {
    expect(judianPublicClient.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the shared base url for both clients", () => {
    expect(judianApi.client.defaults.baseURL).toBe(JUDIAN_API_BASE);
    expect(judianPublicClient.defaults.baseURL).toBe(JUDIAN_API_BASE);
  });

  it("keeps login and relogin on the longer timeout", () => {
    const loginRequest = judianApi.loginAccount({
      loginEmail: "a@example.com",
      loginPassword: "b",
    });
    const reloginRequest = judianApi.reloginAccount(1);

    expect(loginRequest.config.timeout).toBe(JUDIAN_LOGIN_API_TIMEOUT_MS);
    expect(reloginRequest.config.timeout).toBe(JUDIAN_LOGIN_API_TIMEOUT_MS);
  });
});
```

- [ ] **Step 2: 运行测试，确认当前实现无法直接满足全部断言**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/api/judian.test.ts
```

Expected: FAIL。优先接受的失败原因是请求对象上拿不到 `config.timeout`，或某个接口仍未显式暴露一致的客户端配置。

- [ ] **Step 3: 做最小实现修复**

If the timeout assertions fail because request promises do not expose config, refactor only the API factory shape instead of touching business behavior. Preferred minimal extraction:

```ts
export const judianApi = {
  client: judianClient,
  loginAccountConfig: { timeout: JUDIAN_LOGIN_API_TIMEOUT_MS },
  reloginAccountConfig: { timeout: JUDIAN_LOGIN_API_TIMEOUT_MS },
  loginAccount: (data: Record<string, unknown>) =>
    judianClient.post("/accounts/login", data, judianApi.loginAccountConfig),
  reloginAccount: (rowId: number | string) =>
    judianClient.post(
      `/accounts/${rowId}/relogin`,
      null,
      judianApi.reloginAccountConfig,
    ),
};
```

Then align the test with the exported config objects:

```ts
expect(judianApi.loginAccountConfig.timeout).toBe(JUDIAN_LOGIN_API_TIMEOUT_MS);
expect(judianApi.reloginAccountConfig.timeout).toBe(
  JUDIAN_LOGIN_API_TIMEOUT_MS,
);
```

If the original assertions already pass with a cleaner inspection path, keep the current API shape and only commit the expanded test.

- [ ] **Step 4: 重新运行 API 测试**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/api/judian.test.ts
```

Expected: PASS，聚点 API 边界断言全部通过。

- [ ] **Step 5: 提交 API 测试与最小修复**

```bash
git add frontend/src/api/judian.test.ts frontend/src/api/judian.ts
git commit -m "test: lock judian api client boundaries"
```

### Task 4: 为公开兑换页补最小组件测试入口

**Files:**

- Create: `frontend/src/views/judian/RedeemView.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/views/judian/RedeemView.vue`

- [ ] **Step 1: 先写页面失败测试**

Create `frontend/src/views/judian/RedeemView.test.ts`:

```ts
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RedeemView from "./RedeemView.vue";

const replaceMock = vi.fn(() => Promise.resolve());
const routeState = { query: { code: "CARD-001" } };
const publicRedeemInfo = vi.fn();

vi.mock("vue-router", () => ({
  useRoute: () => routeState,
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/api/judian", () => ({
  judianApi: {
    publicRedeemInfo,
    publicUnlockDetail: vi.fn(),
    publicUnlockScan: vi.fn(),
    publicUnlockBatchDetail: vi.fn(),
    publicUnlockBatchPreview: vi.fn(),
    publicUnlockBatchPurchase: vi.fn(),
    publicUnlockBatchCancel: vi.fn(),
    publicUnlockConfirm: vi.fn(),
    publicUnlockComplete: vi.fn(),
  },
}));

const readyPayload = {
  code: "CARD-001",
  status: "active",
  duration: 30,
  maxUses: 1,
  useCount: 0,
  account: {
    accountId: "acc-1",
    displayName: "测试聚点账号",
    status: "active",
    enabled: true,
    diamondQuantity: 120,
  },
  session: {
    sessionId: "session-1",
    status: "pending",
    message: "等待扫码",
    order: null,
    resultPayload: {},
  },
};

describe("RedeemView", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    publicRedeemInfo.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders ready state after redeem payload loads", async () => {
    publicRedeemInfo.mockResolvedValue({ data: readyPayload });

    const wrapper = mount(RedeemView);
    await flushPromises();

    expect(wrapper.text()).toContain("测试聚点账号");
    expect(wrapper.text()).toContain("扫码解锁");
  });

  it("renders error state when redeem request fails", async () => {
    publicRedeemInfo.mockRejectedValue({
      response: { status: 500, statusText: "Internal Server Error" },
      message: "boom",
    });

    const wrapper = mount(RedeemView);
    await flushPromises();

    expect(wrapper.text()).toContain("页面暂时无法展示");
    expect(wrapper.text()).toContain("重新检测");
  });
});
```

- [ ] **Step 2: 补最小测试依赖与环境**

Modify `frontend/package.json`:

```json
{
  "devDependencies": {
    "@types/node": "^24.12.2",
    "@vitejs/plugin-vue": "^6.0.6",
    "@vue/test-utils": "^2.4.6",
    "@vue/tsconfig": "^0.9.1",
    "jsdom": "^26.1.0",
    "typescript": "~6.0.2",
    "vite": "^8.0.9",
    "vitest": "^3.2.4",
    "vue-tsc": "^3.2.7"
  }
}
```

Modify `frontend/vite.config.ts`:

```ts
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    globals: true,
  },
  base: buildBase,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

- [ ] **Step 3: 安装依赖并运行测试确认红灯**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm install
npm run test -- src/views/judian/RedeemView.test.ts
```

Expected: FAIL。优先接受的失败原因是组件在 jsdom 下触发了未处理浏览器 API，或当前页面状态渲染与断言不一致。

- [ ] **Step 4: 做最小页面修复**

Only patch the smallest seam the test exposes. Preferred changes are limited to browser-only guards and extracted helpers. Example:

```ts
const isSecureCameraContext = () =>
  typeof window !== "undefined" && window.isSecureContext !== false;

async function openCamera() {
  if (cameraBusy.value) return;
  if (!isSecureCameraContext()) {
    showToast("必须使用 HTTPS 或 localhost 才能调用摄像头");
    return;
  }
  // existing logic...
}
```

If the ready/error tests pass after wiring test infra, do not modify `RedeemView.vue`. Commit the characterization test and infra only.

- [ ] **Step 5: 重新运行页面测试**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/views/judian/RedeemView.test.ts
```

Expected: PASS，页面最小状态切面可重复验证。

- [ ] **Step 6: 提交页面测试入口**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/views/judian/RedeemView.test.ts frontend/src/views/judian/RedeemView.vue
git commit -m "test: add minimal judian redeem view coverage"
```

### Task 5: 为聚点后端建立最小 `unittest` 入口

**Files:**

- Create: `backend/judian/tests/__init__.py`
- Create: `backend/judian/tests/test_app_endpoints.py`
- Modify: `backend/judian/judian_backend/__init__.py`

- [ ] **Step 1: 先写后端失败测试**

Create `backend/judian/tests/test_app_endpoints.py`:

```py
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.judian.judian_backend.__init__ import (
    app,
    get_current_user,
)


class VerifyEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: {
            "username": "tester",
            "is_admin": True,
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_verify_returns_authenticated_payload(self):
        response = self.client.get("/verify")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "username": "tester",
                "is_admin": True,
            },
        )


class PublicBatchPreviewEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch(
        "backend.judian.judian_backend.__init__.build_public_batch_purchase_preview",
        return_value={"count": 2, "requiredDiamond": 20},
    )
    @patch(
        "backend.judian.judian_backend.__init__.get_public_unlock_session_or_404",
        return_value=(object(), object(), object()),
    )
    def test_batch_preview_wraps_preview_payload(self, unlock_mock, preview_mock):
        response = self.client.get(
            "/public/unlock/session-1/batch/preview",
            params={"count": 2, "vip_id": "vip-1", "package_type": "month"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "preview": {"count": 2, "requiredDiamond": 20},
            },
        )
        unlock_mock.assert_called_once()
        preview_mock.assert_called_once()
```

- [ ] **Step 2: 运行测试，确认当前红灯**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass
python -m unittest backend.judian.tests.test_app_endpoints -v
```

Expected: FAIL。优先接受的失败原因是导入链过重、测试包路径缺失，或某个接口依赖未被正确隔离。

- [ ] **Step 3: 做最小后端修复**

If imports fail because test package is missing, add:

```py
# backend/judian/tests/__init__.py
```

If endpoint code cannot be imported without import-time side effects, isolate only the minimal import seam in `backend/judian/judian_backend/__init__.py`. Prefer this shape:

```py
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Do not refactor route logic unless a concrete failing test requires it.

- [ ] **Step 4: 重新运行后端测试**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass
python -m unittest backend.judian.tests.test_app_endpoints -v
```

Expected: PASS，至少 `verify` 和 `batch/preview` 两条后端链路可本地验证。

- [ ] **Step 5: 提交后端最小测试入口**

```bash
git add backend/judian/tests/__init__.py backend/judian/tests/test_app_endpoints.py backend/judian/judian_backend/__init__.py
git commit -m "test: add minimal judian backend endpoint coverage"
```

### Task 6: 整理并执行聚点冒烟命令

**Files:**

- Modify: `docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md`
- Inspect: `backend/judian/scripts/test-vip.js`

- [ ] **Step 1: 把首轮必跑命令写进报告**

Append to `docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md`:

````md
## 首轮冒烟命令

~~~bash
cd backend/judian/scripts
node test-vip.js smoke --pretty
node test-vip.js list --pretty
node test-vip.js login --account <account> --password <password> --pretty
node test-vip.js status --order-no <orderNo> --pretty
~~~

## 记录模板

| 命令                              | 前置条件   | 成功标准                     | 实际结果 | 备注 |
| --------------------------------- | ---------- | ---------------------------- | -------- | ---- |
| `node test-vip.js smoke --pretty` | 网络可达   | 能返回 host 探测结果         | 待运行   |      |
| `node test-vip.js list --pretty`  | host 可用  | 能返回套餐列表或明确失败原因 | 待运行   |      |
| `node test-vip.js login ...`      | 测试账号   | 能拿到 token 或明确失败原因  | 待运行   |      |
| `node test-vip.js status ...`     | 已知订单号 | 能返回订单状态               | 待运行   |      |
````

- [ ] **Step 2: 先运行无账号依赖的命令**

Run:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\backend\judian\scripts
node test-vip.js smoke --pretty
node test-vip.js list --pretty
```

Expected: 至少能得到远端可用性、host 解析结果或明确的错误信息，而不是脚本崩溃。

- [ ] **Step 3: 视凭据情况运行账号相关命令**

Run only if credentials are available:

```powershell
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\backend\judian\scripts
node test-vip.js login --account <account> --password <password> --pretty
node test-vip.js status --order-no <orderNo> --pretty
```

Expected: 输出真实 JSON 结果或可复查失败信息，并把结果写回报告表格。

- [ ] **Step 4: 更新报告中的自动化测试与冒烟结论**

Update these sections in `docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md`:

```md
## 自动化测试结果

- `npm run test -- src/utils/judian-auth.test.ts`
- `npm run test -- src/api/judian.test.ts`
- `npm run test -- src/views/judian/RedeemView.test.ts`
- `python -m unittest backend.judian.tests.test_app_endpoints -v`

## 已修复问题

- 示例：`judian-auth.ts` 跳转保护与测试预期不一致，已对齐为可重复验证的行为
- 示例：`RedeemView.vue` 在 jsdom 下触发浏览器专属 API，已补最小保护

## 未覆盖与受限项

- 真实支付、真实订单、真实账号依赖仍以受限冒烟方式验证
```

- [ ] **Step 5: 做最终验证并提交报告**

Run:

```powershell
git -C d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass diff --check
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass\frontend
npm run test -- src/utils/judian-auth.test.ts src/api/judian.test.ts src/views/judian/RedeemView.test.ts
Set-Location d:\hms\Desktop\闲鱼上线版\.worktrees\stability-performance-first-pass
python -m unittest backend.judian.tests.test_app_endpoints -v
```

Expected: `diff --check` 无报错，前端测试通过，后端测试通过；若账号类冒烟命令受限，则在报告中明确记为“受限未跑”。

- [ ] **Step 6: 提交最终报告**

```bash
git add docs/superpowers/reports/2026-04-30-judian-full-coverage-report.md
git commit -m "docs: record judian coverage verification results"
```

## Self-Review

- Spec coverage: 已覆盖前端会话、前端 API、公开兑换页、后端接口、冒烟脚本与报告产物。
- Placeholder scan: 计划中没有 `TODO`、`TBD`、`类似 Task N` 这类占位语；账号类命令以“仅在凭据可用时运行”明确限制条件。
- Type consistency: 前端测试文件、后端测试文件、报告文件和命令路径均使用仓库中的真实路径；后端命令统一使用 `python -m unittest`，避免假设仓库已有 `pytest`。
