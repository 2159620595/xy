import { del, get, post, put } from "@/utils/request";
import type { ApiResponse, Item, ItemReply } from "@/types";

export const getItems = async (
  cookieId?: string,
): Promise<{ success: boolean; data: Item[] }> => {
  const url = cookieId ? `/items/cookie/${cookieId}` : "/items";
  const result = await get<{ items?: Item[] } | Item[]>(url);
  const items = Array.isArray(result) ? result : (result.items ?? []);
  return { success: true, data: items };
};

export const fetchAllItemsFromAccount = (
  cookieId: string,
): Promise<ApiResponse> => {
  return post("/items/get-all-from-account", { cookie_id: cookieId });
};

export const updateItem = (
  cookieId: string,
  itemId: string,
  data: Partial<Item>,
): Promise<ApiResponse> => {
  return put(`/items/${cookieId}/${itemId}`, data);
};

export const relistItem = (
  cookieId: string,
  itemId: string,
): Promise<ApiResponse> => {
  return post(`/items/${cookieId}/${itemId}/relist`);
};

export const polishItem = (
  cookieId: string,
  itemId: string,
): Promise<ApiResponse> => {
  return post(`/items/${cookieId}/${itemId}/polish`);
};

export interface ItemDefaultReplyConfig {
  item_id: string;
  reply_content: string;
  reply_image?: string;
  enabled: boolean;
  reply_once: boolean;
}

export const getItemDefaultReply = (
  cookieId: string,
  itemId: string,
): Promise<ApiResponse<ItemDefaultReplyConfig>> => {
  return get(`/items/${cookieId}/${itemId}/default-reply`);
};

export const saveItemDefaultReply = (
  cookieId: string,
  itemId: string,
  data: {
    reply_content: string;
    reply_image_url?: string;
    enabled: boolean;
    reply_once: boolean;
  },
): Promise<ApiResponse> => {
  return put(`/items/${cookieId}/${itemId}/default-reply`, data);
};

export const uploadItemDefaultReplyImage = (
  cookieId: string,
  itemId: string,
  image: File,
): Promise<{ success: boolean; image_url?: string; message?: string }> => {
  const formData = new FormData();
  formData.append("image", image);
  return post(
    `/items/${cookieId}/${itemId}/default-reply/upload-image`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
};

export const deleteItemDefaultReply = (
  cookieId: string,
  itemId: string,
): Promise<ApiResponse> => {
  return del(`/items/${cookieId}/${itemId}/default-reply`);
};

export const batchSaveItemDefaultReply = (
  cookieId: string,
  data: {
    item_ids: string[];
    reply_content: string;
    reply_image_url?: string;
    enabled: boolean;
    reply_once: boolean;
  },
): Promise<ApiResponse> => {
  return post(`/items/${cookieId}/batch-default-reply`, data);
};

export const batchDeleteItemDefaultReply = (
  cookieId: string,
  itemIds: string[],
): Promise<ApiResponse> => {
  return post(`/items/${cookieId}/batch-delete-default-reply`, {
    item_ids: itemIds,
  });
};

export const getItemReplies = async (
  cookieId?: string,
): Promise<{ success: boolean; data: ItemReply[] }> => {
  const suffix = cookieId ? `/cookie/${cookieId}` : "";
  const result = await get<{ items?: ItemReply[] } | ItemReply[]>(
    `/itemReplays${suffix}`,
  );
  const list = Array.isArray(result) ? result : (result.items ?? []);
  return {
    success: true,
    data: list.map((item) => ({
      ...item,
      title: item.title || item.item_title || "",
      reply: item.reply || item.reply_content || item.content || "",
    })),
  };
};

export const addItemReply = (
  cookieId: string,
  itemId: string,
  data: Partial<ItemReply>,
): Promise<ApiResponse> => {
  return put(`/item-reply/${cookieId}/${itemId}`, data);
};

export const updateItemReply = (
  cookieId: string,
  itemId: string,
  data: Partial<ItemReply>,
): Promise<ApiResponse> => {
  return put(`/item-reply/${cookieId}/${itemId}`, data);
};

export const deleteItemReply = (
  cookieId: string,
  itemId: string,
): Promise<ApiResponse> => {
  return del(`/item-reply/${cookieId}/${itemId}`);
};
