import { del, get, post } from '@/utils/request'
import type { ApiResponse, Order, OrderStatus, PaginatedOrderResponse } from '@/types'

export interface OrderDetail extends Order {
  spec_name?: string
  spec_value?: string
}

const KNOWN_ORDER_STATUSES: OrderStatus[] = [
  'processing',
  'pending_ship',
  'processed',
  'shipped',
  'completed',
  'refunding',
  'refund_cancelled',
  'cancelled',
  'closed',
  'unknown',
]

const normalizeOrderStatus = (status?: string): OrderStatus => {
  if (!status) return 'unknown'
  return KNOWN_ORDER_STATUSES.includes(status as OrderStatus) ? (status as OrderStatus) : 'unknown'
}

const getOrderKey = (order: Pick<Order, 'order_id' | 'cookie_id'>) =>
  order.order_id && order.cookie_id ? `${order.order_id}::${order.cookie_id}` : order.order_id || ''

const normalizeAmount = (amount: Order['amount']) => {
  if (amount === null || amount === undefined) return ''
  return String(amount).trim()
}

const normalizeOrder = (order: Order): Order => ({
  ...order,
  id: order.id || getOrderKey(order),
  order_id: order.order_id || order.id || '',
  item_id: order.item_id || '',
  buyer_id: order.buyer_id || '',
  quantity:
    typeof order.quantity === 'string' ? Number(order.quantity || 0) || 0 : (order.quantity ?? 0),
  amount: normalizeAmount(order.amount),
  status: normalizeOrderStatus(order.status),
})

export const getOrders = async (
  cookieId?: string,
  status?: string,
  keyword?: string,
  page = 1,
  pageSize = 20,
): Promise<PaginatedOrderResponse> => {
  const params = new URLSearchParams()
  if (cookieId) params.append('cookie_id', cookieId)
  if (status) params.append('status', status)
  if (keyword?.trim()) params.append('keyword', keyword.trim())
  params.append('page', String(page))
  params.append('page_size', String(pageSize))

  try {
    const result = await get<{
      success?: boolean
      orders?: Order[]
      data?: Order[]
      total?: number
      total_pages?: number
      page?: number
      page_size?: number
    }>(
      `/api/orders?${params.toString()}`,
    )
    const orders = (result.orders || result.data || []).map(normalizeOrder)
    const total = result.total ?? orders.length
    const totalPages = result.total_pages ?? Math.ceil(total / pageSize) ?? 0
    return {
      success: result.success ?? true,
      data: orders,
      total,
      total_pages: totalPages,
      page: result.page ?? page,
      page_size: result.page_size ?? pageSize,
    }
  } catch {
    return { success: false, data: [], total: 0, total_pages: 0 }
  }
}

export const getOrderDetail = async (
  orderId: string,
  cookieId?: string,
): Promise<{ success: boolean; data?: OrderDetail }> => {
  try {
    const suffix = cookieId ? `?cookie_id=${encodeURIComponent(cookieId)}` : ''
    const result = await get<{ order?: OrderDetail; data?: OrderDetail }>(`/api/orders/${orderId}${suffix}`)
    const detail = result.order || result.data
    return {
      success: true,
      data: detail ? (normalizeOrder(detail) as OrderDetail) : undefined,
    }
  } catch {
    return { success: false }
  }
}

export const deleteOrder = async (orderId: string, cookieId?: string): Promise<ApiResponse> => {
  try {
    const suffix = cookieId ? `?cookie_id=${encodeURIComponent(cookieId)}` : ''
    await del(`/api/orders/${orderId}${suffix}`)
    return { success: true, message: '删除成功' }
  } catch {
    return { success: false, message: '删除失败' }
  }
}

export const fetchOrdersFromAccount = async (
  cookieId: string,
): Promise<ApiResponse<{ fetched_count?: number; saved_count?: number }>> => {
  try {
    const result = await post<{
      success?: boolean
      message?: string
      fetched_count?: number
      saved_count?: number
    }>('/api/orders/fetch', { cookie_id: cookieId })

    return {
      success: Boolean(result.success),
      message: result.message,
      data: {
        fetched_count: result.fetched_count,
        saved_count: result.saved_count,
      },
    }
  } catch {
    return { success: false, message: '获取订单失败' }
  }
}
