import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg2


TABLE_COMMENTS = {
    "users": "用户表（系统账号）",
    "email_verifications": "邮箱验证码记录表",
    "captcha_codes": "图形验证码记录表",
    "cookies": "闲鱼Cookie账号表",
    "keywords": "关键词自动回复规则表",
    "cookie_status": "Cookie启用状态表",
    "ai_reply_settings": "AI回复配置表",
    "ai_conversations": "AI对话历史表",
    "ai_item_cache": "AI商品信息缓存表",
    "cards": "卡券/发货内容资源表",
    "orders": "订单记录表",
    "item_info": "商品信息表",
    "item_images": "商品图片表",
    "delivery_rules": "自动发货规则表",
    "default_replies": "默认回复配置表（账号级/商品级）",
    "item_replay": "指定商品回复表",
    "default_reply_records": "默认回复发送记录表",
    "delivery_records": "自动发货明细记录表",
    "notification_channels": "通知渠道配置表",
    "system_settings": "系统设置表",
    "message_notifications": "消息通知绑定表",
    "user_settings": "用户设置表",
    "risk_control_logs": "风控处理日志表",
    "token_cache": "Token缓存表（IM Token/Device ID）",
}


COMMON_COLUMN_COMMENTS = {
    "id": "主键ID",
    "user_id": "用户ID",
    "cookie_id": "Cookie账号ID",
    "username": "用户名",
    "email": "邮箱",
    "password": "密码",
    "password_hash": "密码哈希（SHA256）",
    "nickname": "昵称",
    "is_active": "是否启用",
    "enabled": "是否启用",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "remark": "备注",
    "description": "描述",
    "item_id": "商品ID",
    "item_title": "商品标题",
    "chat_id": "会话ID",
    "order_id": "订单ID",
    "keyword": "关键词",
    "reply": "回复内容",
    "type": "类型",
    "value": "值",
    "key": "键",
    "config": "配置JSON",
    "name": "名称",
    "code": "验证码",
    "expires_at": "过期时间",
    "used": "是否已使用",
    "content": "内容",
    "status": "状态",
    "image_url": "图片URL",
}


TABLE_COLUMN_COMMENTS = {
    "ai_conversations": {
        "role": "对话角色",
        "content": "对话内容",
        "intent": "识别意图",
        "bargain_count": "议价轮次",
    },
    "ai_item_cache": {
        "data": "商品缓存数据JSON",
        "price": "商品价格",
        "description": "商品描述",
        "last_updated": "最后更新时间",
    },
    "cookies": {
        "value": "Cookie原始内容",
        "password": "登录密码",
        "auto_confirm": "是否自动确认",
        "pause_duration": "暂停时长（秒）",
        "show_browser": "是否显示浏览器",
        "xianyu_nickname": "闲鱼昵称",
        "xianyu_avatar_url": "闲鱼头像URL",
    },
    "captcha_codes": {
        "session_id": "会话标识",
    },
    "keywords": {
        "reply": "关键词回复内容",
        "type": "回复类型",
        "image_url": "图片URL",
    },
    "ai_reply_settings": {
        "ai_enabled": "是否启用AI回复",
        "model_name": "AI模型名称",
        "api_key": "AI接口密钥",
        "base_url": "AI接口地址",
        "max_discount_percent": "最大降价百分比",
        "max_discount_amount": "最大降价金额",
        "max_bargain_rounds": "最大议价轮数",
        "custom_prompts": "自定义提示词",
    },
    "cards": {
        "type": "卡片类型",
        "api_config": "API配置",
        "text_content": "文本内容",
        "data_content": "数据内容",
        "image_url": "图片URL",
        "delay_seconds": "延迟秒数",
        "is_multi_spec": "是否多规格",
        "spec_name": "规格名",
        "spec_value": "规格值",
    },
    "orders": {
        "buyer_id": "买家ID",
        "spec_name": "规格名",
        "spec_value": "规格值",
        "quantity": "购买数量",
        "amount": "订单金额",
        "order_status": "订单状态",
        "is_bargain": "是否议价订单",
    },
    "item_info": {
        "item_description": "商品描述",
        "item_category": "商品分类",
        "item_price": "商品价格",
        "item_detail": "商品详情",
        "is_multi_spec": "是否多规格",
        "seller_nick": "卖家昵称",
        "primary_image_url": "主图URL",
        "item_status": "商品状态",
        "auto_relist_enabled": "是否自动重新上架",
        "auto_polish_enabled": "是否自动擦亮",
        "auto_polish_interval_hours": "自动擦亮间隔小时",
        "last_polish_at": "最后擦亮时间",
        "last_relist_at": "最后重新上架时间",
        "multi_quantity_delivery": "是否多数量发货",
    },
    "item_images": {
        "thumbnail_url": "缩略图URL",
        "sort_order": "排序序号",
        "is_primary": "是否主图",
    },
    "delivery_rules": {
        "card_id": "卡券ID",
        "delivery_count": "单次发货数量",
        "delivery_times": "已发货次数",
    },
    "delivery_records": {
        "rule_id": "规则ID",
        "card_id": "卡券ID",
        "card_name": "卡券名称",
        "card_type": "卡券类型",
        "sent_count": "已发送数量",
        "delivery_content": "发货内容",
    },
    "default_replies": {
        "reply_content": "默认回复内容",
        "reply_image_url": "默认回复图片URL",
        "reply_once": "是否仅回复一次",
    },
    "default_reply_records": {
        "replied_at": "回复时间",
    },
    "notification_channels": {
        "type": "通知渠道类型",
    },
    "message_notifications": {
        "channel_id": "通知渠道ID",
    },
    "token_cache": {
        "token": "IM Token",
        "device_id": "设备ID",
        "expire_at": "过期时间",
    },
    "risk_control_logs": {
        "event_type": "事件类型",
        "event_description": "事件描述",
        "processing_result": "处理结果",
        "processing_status": "处理状态",
        "error_message": "错误信息",
    },
}


def load_dotenv_if_present(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = (raw_line or "").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = (key or "").strip()
            if not key or key in os.environ:
                continue
            value = (value or "").strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value
    except Exception:
        return


def read_primary_database_url() -> str:
    for env_name in ("DATABASE_URL_XIANYU", "DATABASE_URL"):
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value
    return ""


def validate_pg_url(pg_url: str) -> None:
    if not pg_url:
        raise SystemExit("缺少 PostgreSQL 连接串，请配置 DATABASE_URL_XIANYU 或兼容变量 DATABASE_URL")
    parsed = urlparse(pg_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise SystemExit(f"PostgreSQL 连接串协议不正确: {parsed.scheme}")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def quote_literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def build_column_comment(table_name: str, column_name: str) -> str:
    table_specific = TABLE_COLUMN_COMMENTS.get(table_name, {})
    if column_name in table_specific:
        return table_specific[column_name]
    if column_name in COMMON_COLUMN_COMMENTS:
        return COMMON_COLUMN_COMMENTS[column_name]
    if column_name.startswith("is_"):
        return f"是否{column_name[3:]}"
    if column_name.endswith("_at"):
        return f"{column_name[:-3]}时间"
    if column_name.endswith("_id"):
        return f"{column_name[:-3]}ID"
    return f"{column_name}字段"


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    load_dotenv_if_present(base_dir)

    pg_url = read_primary_database_url()
    validate_pg_url(pg_url)

    conn = psycopg2.connect(pg_url, connect_timeout=10)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )
        existing_tables = {r[0] for r in cur.fetchall()}

        applied = 0
        skipped = 0
        for table_name, comment in TABLE_COMMENTS.items():
            if table_name not in existing_tables:
                print(f"[SKIP] {table_name}: 表不存在")
                skipped += 1
                continue
            sql = (
                f"COMMENT ON TABLE public.{quote_ident(table_name)} "
                f"IS {quote_literal(comment)}"
            )
            cur.execute(sql)
            print(f"[OK] {table_name}: {comment}")
            applied += 1

        conn.commit()
        print(f"完成：已注释 {applied} 张表，跳过 {skipped} 张表")

        # 列注释
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name = ANY(%s)
            ORDER BY table_name, ordinal_position
            """,
            (list(TABLE_COMMENTS.keys()),),
        )
        columns = cur.fetchall()

        col_applied = 0
        for table_name, column_name in columns:
            comment = build_column_comment(table_name, column_name)
            sql = (
                f"COMMENT ON COLUMN public.{quote_ident(table_name)}.{quote_ident(column_name)} "
                f"IS {quote_literal(comment)}"
            )
            cur.execute(sql)
            col_applied += 1
        conn.commit()
        print(f"完成：已注释字段 {col_applied} 个")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
