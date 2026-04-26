import { del, get, post, put } from "@/utils/request";
import type { Account, AccountDetail, ApiResponse } from "@/types";

interface BackendAccountListItem {
  id: string;
  enabled: boolean;
  auto_confirm: boolean;
  auto_reply_once_per_customer?: boolean;
  remark?: string;
  pause_duration?: number;
  xianyu_nickname?: string;
  xianyu_avatar_url?: string;
}

interface BackendAccountDetail extends BackendAccountListItem {
  value?: string;
  username?: string;
  password?: string;
  login_password?: string;
  show_browser?: boolean;
}

const mapAccount = (item: BackendAccountListItem): Account => ({
  id: item.id,
  enabled: item.enabled,
  auto_confirm: item.auto_confirm,
  auto_reply_once_per_customer: item.auto_reply_once_per_customer,
  note: item.remark,
  pause_duration: item.pause_duration,
  xianyu_nickname: item.xianyu_nickname,
  xianyu_avatar_url: item.xianyu_avatar_url,
  use_ai_reply: false,
  use_default_reply: false,
});

const mapAccountDetail = (item: BackendAccountDetail): AccountDetail => ({
  ...mapAccount(item),
  cookie: item.value,
  username: item.username,
  login_password: item.login_password ?? item.password,
  show_browser: item.show_browser,
});

export const getAccounts = async (): Promise<Account[]> => {
  const data = await get<BackendAccountListItem[]>("/cookies/details");
  return data.map((item) => mapAccount(item));
};

export const getAccountDetails = async (): Promise<AccountDetail[]> => {
  const data = await get<BackendAccountListItem[]>("/cookies/details");
  return data.map((item) => mapAccount(item));
};

export const getAccountDetail = async (id: string): Promise<AccountDetail> => {
  const data = await get<BackendAccountDetail>(`/cookie/${id}/details`);
  return mapAccountDetail(data);
};

export const addAccount = (data: {
  id: string;
  cookie: string;
}): Promise<ApiResponse> => {
  return post("/cookies", { id: data.id, value: data.cookie });
};

export const updateAccountCookie = (
  id: string,
  value: string,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}`, { id, value });
};

export const updateAccountStatus = (
  id: string,
  enabled: boolean,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/status`, { enabled });
};

export const updateAccountRemark = (
  id: string,
  remark: string,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/remark`, { remark });
};

export const updateAccountAutoConfirm = (
  id: string,
  autoConfirm: boolean,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/auto-confirm`, { auto_confirm: autoConfirm });
};

export const updateAccountPauseDuration = (
  id: string,
  pauseDuration: number,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/pause-duration`, {
    pause_duration: pauseDuration,
  });
};

export const updateAccountAutoReplyOncePerCustomer = (
  id: string,
  enabled: boolean,
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/auto-reply-once-per-customer`, {
    enabled,
  });
};

export const updateAccountLoginInfo = (
  id: string,
  data: {
    username?: string;
    login_password?: string;
    show_browser?: boolean;
  },
): Promise<ApiResponse> => {
  return put(`/cookies/${id}/login-info`, data);
};

export const deleteAccount = (id: string): Promise<ApiResponse> => {
  return del(`/cookies/${id}`);
};

export const passwordLogin = (data: {
  account_id: string;
  account: string;
  password: string;
  show_browser?: boolean;
}): Promise<ApiResponse> => {
  return post("/password-login", data);
};

export const generateQRLogin = (): Promise<{
  success: boolean;
  session_id?: string;
  qr_code_url?: string;
  message?: string;
}> => {
  return post("/qr-login/generate");
};

export const checkQRLoginStatus = async (
  sessionId: string,
): Promise<{
  success: boolean;
  status:
    | "pending"
    | "scanned"
    | "success"
    | "expired"
    | "cancelled"
    | "verification_required"
    | "processing"
    | "already_processed"
    | "error";
  message?: string;
  account_info?: {
    account_id: string;
    is_new_account: boolean;
  };
}> => {
  const result = await get<{
    status: string;
    message?: string;
    account_info?: { account_id: string; is_new_account: boolean };
  }>(`/qr-login/check/${sessionId}`);
  return {
    success: result.status !== "error",
    status: result.status as
      | "pending"
      | "scanned"
      | "success"
      | "expired"
      | "cancelled"
      | "verification_required"
      | "processing"
      | "already_processed"
      | "error",
    message: result.message,
    account_info: result.account_info,
  };
};

export interface AIReplySettings {
  ai_enabled: boolean;
  model_name?: string;
  api_key?: string;
  base_url?: string;
  max_discount_percent?: number;
  max_discount_amount?: number;
  max_bargain_rounds?: number;
  custom_prompts?: string;
  enabled?: boolean;
}

export const getAIReplySettings = (
  cookieId: string,
): Promise<AIReplySettings> => {
  return get(`/ai-reply-settings/${cookieId}`);
};

export const updateAIReplySettings = (
  cookieId: string,
  settings: Partial<AIReplySettings>,
): Promise<ApiResponse> => {
  const payload: Record<string, unknown> = {
    ai_enabled: settings.ai_enabled ?? settings.enabled ?? false,
    model_name: settings.model_name ?? "qwen-plus",
    api_key: settings.api_key ?? "",
    base_url:
      settings.base_url ?? "https://dashscope.aliyuncs.com/compatible-mode/v1",
    max_discount_percent: settings.max_discount_percent ?? 10,
    max_discount_amount: settings.max_discount_amount ?? 100,
    max_bargain_rounds: settings.max_bargain_rounds ?? 3,
    custom_prompts: settings.custom_prompts ?? "",
  };
  return put(`/ai-reply-settings/${cookieId}`, payload);
};

export const getAllAIReplySettings = (): Promise<
  Record<string, AIReplySettings>
> => {
  return get("/ai-reply-settings");
};

export interface AccountRefreshProfileResponse {
  success: boolean;
  message?: string;
  cookie_id?: string;
  nickname?: string;
  avatar_url?: string;
}

export const refreshAccountProfile = (
  id: string,
): Promise<AccountRefreshProfileResponse> => {
  return post(`/cookie/${id}/refresh-profile`);
};
