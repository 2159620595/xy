import { del, get, post, put } from "@/utils/request";
import type { ApiResponse, CardData } from "@/types";

export const getCards = async (): Promise<{
  success: boolean;
  data?: CardData[];
}> => {
  const result = await get<CardData[] | { cards?: CardData[] }>("/cards");
  const data = Array.isArray(result) ? result : (result.cards ?? []);
  return { success: true, data };
};

export const createCard = (
  data: Omit<CardData, "id" | "created_at" | "updated_at" | "user_id">,
): Promise<{ id: number; message: string }> => {
  return post("/cards", data);
};

export const updateCard = (
  cardId: string,
  data: Partial<CardData>,
): Promise<ApiResponse> => {
  return put(`/cards/${cardId}`, data);
};

export const deleteCard = (cardId: string): Promise<ApiResponse> => {
  return del(`/cards/${cardId}`);
};
