import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { replaceMock, routeState, publicRedeemInfo } = vi.hoisted(() => ({
  replaceMock: vi.fn(() => Promise.resolve()),
  routeState: { query: { code: "CARD-001" } },
  publicRedeemInfo: vi.fn(),
}));

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

import RedeemView from "./RedeemView.vue";

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
