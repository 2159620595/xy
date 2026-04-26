import { del, get, post, put } from "@/utils/request";
import type { ApiResponse, DeliveryRecord, DeliveryRule } from "@/types";

export const getDeliveryRules = async (): Promise<{
  success: boolean;
  data?: DeliveryRule[];
}> => {
  const result = await get<DeliveryRule[] | { rules?: DeliveryRule[] }>(
    "/delivery-rules",
  );
  const data = Array.isArray(result) ? result : (result.rules ?? []);
  return { success: true, data };
};

export const addDeliveryRule = (
  data: Partial<DeliveryRule>,
): Promise<ApiResponse> => {
  return post("/delivery-rules", data);
};

export const updateDeliveryRule = (
  ruleId: string,
  data: Partial<DeliveryRule>,
): Promise<ApiResponse> => {
  return put(`/delivery-rules/${ruleId}`, data);
};

export const deleteDeliveryRule = (ruleId: string): Promise<ApiResponse> => {
  return del(`/delivery-rules/${ruleId}`);
};

export const getDeliveryRuleRecords = async (
  ruleId: string,
  limit = 50,
): Promise<{ success: boolean; data?: DeliveryRecord[] }> => {
  const result = await get<{ records?: DeliveryRecord[] }>(
    `/delivery-rules/${ruleId}/records?limit=${limit}`,
  );
  return { success: true, data: result.records ?? [] };
};
