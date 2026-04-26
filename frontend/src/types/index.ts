export interface User {
  user_id: number
  username: string
  is_admin: boolean
  email?: string
  cookie_count?: number
  card_count?: number
}

export interface LoginRequest {
  username?: string
  password?: string
  email?: string
  verification_code?: string
  geetest_challenge?: string
  geetest_validate?: string
  geetest_seccode?: string
}

export interface RegisterRequest {
  username: string
  password: string
  email: string
  verification_code: string
  session_id: string
}

export interface LoginResponse {
  success: boolean
  message?: string
  token?: string
  user_id?: number
  username?: string
  is_admin?: boolean
}

export interface ApiResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  msg?: string
  detail?: string
}

export interface Account {
  id: string
  cookie?: string
  enabled: boolean
  use_ai_reply: boolean
  use_default_reply: boolean
  auto_confirm: boolean
  auto_reply_once_per_customer?: boolean
  note?: string
  pause_duration?: number
  xianyu_nickname?: string
  xianyu_avatar_url?: string
  created_at?: string
  updated_at?: string
}

export interface AccountDetail extends Account {
  username?: string
  login_password?: string
  show_browser?: boolean
  keywordCount?: number
}

export interface Keyword {
  id?: string
  cookie_id?: string
  keyword: string
  reply: string
  item_id?: string
  type?: 'text' | 'image' | 'item' | 'normal'
  image_url?: string
  fuzzy_match?: boolean
  created_at?: string
  updated_at?: string
}

export interface ItemImage {
  id?: string | number
  image_url: string
  thumbnail_url?: string
  sort_order?: number
  is_primary?: boolean
}

export interface Item {
  id: string | number
  cookie_id: string
  item_id: string
  seller_nick?: string
  title?: string
  item_title?: string
  desc?: string
  item_description?: string
  item_detail?: string
  item_category?: string
  item_status?: string
  primary_image_url?: string
  price?: string
  item_price?: string
  has_sku?: boolean
  is_multi_spec?: number | boolean
  multi_quantity_delivery?: number | boolean
  auto_relist_enabled?: number | boolean
  auto_polish_enabled?: number | boolean
  auto_polish_interval_hours?: number
  last_polish_at?: string
  images?: ItemImage[]
  item_detail_parsed?: {
    item_status?: string | number
    category_id?: string | number
    category_name?: string
    pic_info?: {
      picUrl?: string
      url?: string
    }
    [key: string]: unknown
  }
  created_at?: string
  updated_at?: string
}

export interface ItemReply {
  id?: string
  cookie_id: string
  item_id: string
  title?: string
  item_title?: string
  content?: string
  reply?: string
  reply_content?: string
  reply_once?: boolean
  primary_image_url?: string
  image_url?: string
  thumbnail_url?: string
  created_at?: string
  updated_at?: string
}

export type OrderStatus =
  | 'processing'
  | 'pending_ship'
  | 'processed'
  | 'shipped'
  | 'completed'
  | 'refunding'
  | 'refund_cancelled'
  | 'cancelled'
  | 'closed'
  | 'unknown'

export interface OrderStatusOption {
  value: '' | OrderStatus
  label: string
}

export interface Order {
  id?: string
  order_id: string
  cookie_id: string
  item_id?: string
  buyer_id?: string
  chat_id?: string
  sku_info?: string
  spec_name?: string
  spec_value?: string
  quantity?: number | string
  amount?: string
  status: OrderStatus
  is_bargain?: boolean
  created_at?: string
  updated_at?: string
}

export interface PaginatedOrderResponse {
  success: boolean
  data: Order[]
  total: number
  total_pages: number
  page?: number
  page_size?: number
}

export interface CardData {
  id?: number
  name: string
  type: 'api' | 'text' | 'data' | 'image'
  description?: string
  enabled?: boolean
  delay_seconds?: number
  is_multi_spec?: boolean
  spec_name?: string
  spec_value?: string
  api_config?: {
    url: string
    method: string
    timeout?: number
    headers?: string
    params?: string
  }
  text_content?: string
  data_content?: string
  image_url?: string
  created_at?: string
  updated_at?: string
  user_id?: number
}

export interface DeliveryRule {
  id: number
  keyword: string
  item_id?: string
  item_title?: string
  item_price?: string
  primary_image_url?: string
  card_id: number
  delivery_count: number
  enabled: boolean
  description?: string
  delivery_times?: number
  card_name?: string
  card_type?: string
  is_multi_spec?: boolean
  spec_name?: string
  spec_value?: string
  created_at?: string
  updated_at?: string
}

export interface DeliveryRecord {
  id: number
  rule_id: number
  user_id?: number
  cookie_id?: string
  order_id?: string
  chat_id?: string
  item_id?: string
  item_title?: string
  buyer_id?: string
  card_id?: number
  card_name?: string
  card_type?: string
  sent_count?: number
  delivery_content?: string
  created_at?: string
}

export interface SearchResultItem {
  item_id: string
  title: string
  price: string
  seller_name?: string
  item_url?: string
  main_image?: string
  publish_time?: string
  tags?: string[]
  area?: string
  want_count?: number
}

export interface NotificationChannel {
  id: string
  cookie_id?: string
  name: string
  type:
    | 'qq'
    | 'dingtalk'
    | 'feishu'
    | 'bark'
    | 'email'
    | 'webhook'
    | 'wechat'
    | 'telegram'
  channel_type?: string
  channel_name?: string
  channel_config?: string
  config?: Record<string, unknown>
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface MessageNotification {
  id?: number
  cookie_id: string
  channel_id: number
  channel_name?: string
  enabled: boolean
}

export interface SystemSettings {
  ai_model?: string
  ai_api_key?: string
  ai_api_url?: string
  ai_base_url?: string
  default_reply?: string
  registration_enabled?: boolean
  show_default_login_info?: boolean
  login_captcha_enabled?: boolean
  smtp_server?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  smtp_from?: string
  smtp_use_tls?: boolean
  smtp_use_ssl?: boolean
  qq_reply_secret_key?: string
  [key: string]: unknown
}

export interface DashboardStats {
  totalAccounts: number
  totalKeywords: number
  activeAccounts: number
  totalOrders: number
}

export interface AdminStats {
  total_users: number
  total_cookies: number
  total_cards: number
  total_keywords: number
  total_orders: number
  active_cookies: number
}
