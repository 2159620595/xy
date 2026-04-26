import { del, get, post, put } from "@/utils/request";
import type {
  ApiResponse,
  MessageNotification,
  NotificationChannel,
} from "@/types";

interface BackendChannel {
  id: number;
  name: string;
  type: string;
  config: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

interface BackendNotification {
  id: number;
  channel_id: number;
  enabled: boolean;
  channel_name?: string;
  channel_type?: string;
  channel_config?: string;
}

const serializeChannelConfig = (
  config: NotificationChannel["config"] | unknown,
): string => {
  if (typeof config === "string") {
    return config;
  }
  if (config && typeof config === "object") {
    try {
      return JSON.stringify(config);
    } catch {
      return "{}";
    }
  }
  return "{}";
};

export const getNotificationChannels = async (): Promise<{
  success: boolean;
  data?: NotificationChannel[];
}> => {
  const result = await get<BackendChannel[]>("/notification-channels");
  const channels: NotificationChannel[] = (result || []).map((item) => {
    let parsedConfig: Record<string, unknown> | undefined;

    if (item.config) {
      try {
        parsedConfig = JSON.parse(item.config) as Record<string, unknown>;
      } catch {
        parsedConfig = undefined;
      }
    }

    return {
      id: String(item.id),
      name: item.name,
      type: item.type as NotificationChannel["type"],
      config: parsedConfig,
      enabled: item.enabled,
      created_at: item.created_at,
      updated_at: item.updated_at,
    };
  });

  return { success: true, data: channels };
};

export const addNotificationChannel = (
  data: Partial<NotificationChannel>,
): Promise<ApiResponse> => {
  return post("/notification-channels", {
    ...data,
    config: serializeChannelConfig(data.config),
  });
};

export const updateNotificationChannel = (
  channelId: string,
  data: Partial<NotificationChannel>,
): Promise<ApiResponse> => {
  const payload: Record<string, unknown> = { ...data };

  if ("config" in data) {
    payload.config = serializeChannelConfig(data.config);
  }

  return put(`/notification-channels/${channelId}`, payload);
};

export const deleteNotificationChannel = (
  channelId: string,
): Promise<ApiResponse> => {
  return del(`/notification-channels/${channelId}`);
};

export const testNotificationChannel = async (
  channelId: string,
): Promise<ApiResponse> => {
  try {
    return await post<ApiResponse>(`/notification-channels/${channelId}/test`);
  } catch (error: unknown) {
    const axiosError = error as {
      response?: { data?: { detail?: string; message?: string } };
    };
    const detail =
      axiosError.response?.data?.detail || axiosError.response?.data?.message;
    return { success: false, message: detail || "通知渠道测试失败" };
  }
};

export const getMessageNotifications = async (): Promise<{
  success: boolean;
  data?: MessageNotification[];
}> => {
  const result = await get<Record<string, BackendNotification[]>>(
    "/message-notifications",
  );
  const notifications: MessageNotification[] = [];

  for (const [cookieId, channelList] of Object.entries(result || {})) {
    if (!Array.isArray(channelList)) continue;

    for (const item of channelList) {
      notifications.push({
        id: item.id,
        cookie_id: cookieId,
        channel_id: item.channel_id,
        channel_name: item.channel_name,
        enabled: item.enabled,
      });
    }
  }

  return { success: true, data: notifications };
};

export const setMessageNotification = (
  cookieId: string,
  channelId: number,
  enabled: boolean,
): Promise<ApiResponse> => {
  return post(`/message-notifications/${cookieId}`, {
    channel_id: channelId,
    enabled,
  });
};

export const deleteMessageNotification = (
  notificationId: string,
): Promise<ApiResponse> => {
  return del(`/message-notifications/${notificationId}`);
};

export const deleteAccountNotifications = (
  cookieId: string,
): Promise<ApiResponse> => {
  return del(`/message-notifications/account/${cookieId}`);
};
