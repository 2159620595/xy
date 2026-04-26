import { get, post, put } from "@/utils/request";
import type { ApiResponse, Keyword } from "@/types";

export const getKeywords = (cookieId: string): Promise<Keyword[]> => {
  return get(`/keywords-with-item-id/${cookieId}`);
};

export const saveKeywords = (
  cookieId: string,
  keywords: Keyword[],
): Promise<ApiResponse> => {
  const textKeywords = keywords
    .filter((item) => item.type !== "image")
    .map((item) => ({
      keyword: item.keyword,
      reply: item.reply || "",
      item_id: item.item_id || "",
    }));

  return post(`/keywords-with-item-id/${cookieId}`, { keywords: textKeywords });
};

export const addKeyword = async (
  cookieId: string,
  data: Partial<Keyword>,
): Promise<ApiResponse> => {
  const keywords = await getKeywords(cookieId);
  const exists = keywords.some(
    (item) =>
      item.keyword === data.keyword &&
      (item.item_id || "") === (data.item_id || ""),
  );

  if (exists) {
    return { success: false, message: "该关键词已存在" };
  }

  keywords.push({
    keyword: data.keyword || "",
    reply: data.reply || "",
    item_id: data.item_id || "",
    type: "text",
  } as Keyword);

  return saveKeywords(cookieId, keywords);
};

export const updateKeyword = async (
  cookieId: string,
  oldKeyword: string,
  oldItemId: string,
  data: Partial<Keyword>,
): Promise<ApiResponse> => {
  const keywords = await getKeywords(cookieId);
  const index = keywords.findIndex(
    (item) =>
      item.keyword === oldKeyword && (item.item_id || "") === (oldItemId || ""),
  );

  if (index === -1) {
    return { success: false, message: "关键词不存在" };
  }

  if (data.keyword !== oldKeyword || data.item_id !== oldItemId) {
    const duplicate = keywords.some(
      (item, currentIndex) =>
        currentIndex !== index &&
        item.keyword === data.keyword &&
        (item.item_id || "") === (data.item_id || ""),
    );
    if (duplicate) {
      return { success: false, message: "该关键词已存在" };
    }
  }

  keywords[index] = { ...keywords[index], ...data };
  return saveKeywords(cookieId, keywords);
};

export const deleteKeyword = async (
  cookieId: string,
  keyword: string,
  itemId: string,
): Promise<ApiResponse> => {
  const keywords = await getKeywords(cookieId);
  const filtered = keywords.filter(
    (item) =>
      !(item.keyword === keyword && (item.item_id || "") === (itemId || "")),
  );

  if (filtered.length === keywords.length) {
    return { success: false, message: "关键词不存在" };
  }

  return saveKeywords(cookieId, filtered);
};

export const getDefaultReply = (
  cookieId: string,
): Promise<{
  enabled?: boolean;
  reply_content?: string;
  reply_once?: boolean;
  reply_image_url?: string;
}> => {
  return get(`/default-reply/${cookieId}`);
};

export const updateDefaultReply = (
  cookieId: string,
  replyContent: string,
  enabled = true,
  replyOnce = false,
  replyImageUrl = "",
): Promise<ApiResponse> => {
  return put(`/default-reply/${cookieId}`, {
    enabled,
    reply_content: replyContent,
    reply_once: replyOnce,
    reply_image_url: replyImageUrl,
  });
};

export const exportKeywords = async (cookieId: string): Promise<Blob> => {
  const token = localStorage.getItem("auth_token");
  const response = await fetch(`/keywords-export/${cookieId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("导出失败");
  }

  return response.blob();
};

export const importKeywords = async (
  cookieId: string,
  file: File,
): Promise<ApiResponse<{ added: number; updated: number }>> => {
  const formData = new FormData();
  formData.append("file", file);
  return post<ApiResponse<{ added: number; updated: number }>>(
    `/keywords-import/${cookieId}`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
};

export const addImageKeyword = async (
  cookieId: string,
  keyword: string,
  image: File,
  itemId?: string,
): Promise<
  ApiResponse<{ keyword: string; image_url: string; item_id?: string }>
> => {
  const formData = new FormData();
  formData.append("keyword", keyword);
  formData.append("image", image);

  if (itemId) {
    formData.append("item_id", itemId);
  }

  return post(`/keywords/${cookieId}/image`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
