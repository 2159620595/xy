import { buildApiUrl, get, post, put } from "@/utils/request";
import type { ApiResponse, SystemSettings } from "@/types";
import { getMainToken } from "@/utils/session";

export const getSystemSettings = async (): Promise<{
  success: boolean;
  data?: SystemSettings;
}> => {
  const data = await get<Record<string, unknown>>("/system-settings");
  const booleanFields = [
    "registration_enabled",
    "show_default_login_info",
    "login_captcha_enabled",
    "smtp_use_tls",
    "smtp_use_ssl",
  ];

  const converted: SystemSettings = {};
  for (const [key, value] of Object.entries(data)) {
    converted[key] = booleanFields.includes(key)
      ? value === true || value === "true"
      : value;
  }

  return { success: true, data: converted };
};

export const updateSystemSettings = async (
  data: Partial<SystemSettings>,
): Promise<ApiResponse> => {
  const tasks = Object.entries(data)
    .filter(([, value]) => value !== undefined && value !== null)
    .map(([key, value]) => {
      let stringValue: string;
      if (typeof value === "boolean") {
        stringValue = value ? "true" : "false";
      } else if (typeof value === "number") {
        stringValue = String(value);
      } else {
        stringValue = String(value ?? "");
      }
      return put(`/system-settings/${key}`, { value: stringValue });
    });

  try {
    await Promise.all(tasks);
    return { success: true, message: "设置已保存" };
  } catch {
    return { success: false, message: "保存设置失败" };
  }
};

export const testAIConnection = async (
  cookieId?: string,
): Promise<ApiResponse> => {
  if (!cookieId) {
    return { success: false, message: "请先选择一个账号进行测试" };
  }

  try {
    const result = await post<{
      success?: boolean;
      message?: string;
      reply?: string;
    }>(`/ai-reply-test/${cookieId}`, {
      message: "你好，这是一条测试消息",
    });

    if (result.reply) {
      return { success: true, message: `AI 回复: ${result.reply}` };
    }
    return {
      success: result.success ?? true,
      message: result.message || "AI 连接测试成功",
    };
  } catch (error: unknown) {
    const axiosError = error as {
      response?: { data?: { detail?: string; message?: string } };
    };
    const detail =
      axiosError.response?.data?.detail || axiosError.response?.data?.message;
    return { success: false, message: detail || "AI 连接测试失败" };
  }
};

export const testEmailSend = async (email: string): Promise<ApiResponse> => {
  try {
    return await post<ApiResponse>(
      `/system-settings/test-email?email=${encodeURIComponent(email)}`,
    );
  } catch (error: unknown) {
    const axiosError = error as {
      response?: { data?: { detail?: string; message?: string } };
    };
    const detail =
      axiosError.response?.data?.detail || axiosError.response?.data?.message;
    return { success: false, message: detail || "发送测试邮件失败" };
  }
};

export const changePassword = (data: {
  current_password: string;
  new_password: string;
}): Promise<ApiResponse> => {
  return post("/change-password", data);
};

export const uploadDatabaseBackup = async (file: File): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append("backup_file", file);
  return post("/admin/backup/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const reloadSystemCache = (): Promise<ApiResponse> => {
  return post("/admin/reload-cache");
};

export const exportUserBackup = async (): Promise<{
  blob: Blob;
  filename: string;
}> => {
  const token = getMainToken();
  if (!token) {
    throw new Error("未登录");
  }

  const response = await fetch(buildApiUrl("/backup/export"), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("导出失败");
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition") || "";
  const match = contentDisposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || "xianyu_backup.json";
  return { blob, filename };
};

export const importUserBackup = async (file: File): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  return post("/backup/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
