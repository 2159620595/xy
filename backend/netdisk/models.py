from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from .database import Base


class AdminUser(Base):
    __tablename__ = 'admin_users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    tenant_id = Column(String, default='tenant_001')
    role = Column(String, default='admin')


class AdminLoginLog(Base):
    __tablename__ = 'admin_login_logs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default='tenant_001')
    username = Column(String, index=True, default='')
    status = Column(String, index=True)  # "成功" | "失败"
    ip_address = Column(String, index=True, default='unknown')
    user_agent = Column(String, default='')
    login_source = Column(String, default='主后台登录')
    request_path = Column(String, default='/api/auth/login')
    reason = Column(String, default='')
    risk_level = Column(String, index=True, default='正常')
    risk_flags = Column(String, default='')
    log_message = Column(String, default='')
    created_at = Column(Integer, index=True)


class DiskAccount(Base):
    __tablename__ = 'disk_accounts'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    username = Column(String)
    cookie = Column(String)
    status = Column(Integer, default=1)  # 1=正常 0=失效
    weight = Column(Integer, default=1)
    vip_level = Column(String, default='普通用户')
    avatar_url = Column(String, default='')
    region = Column(String, default='')
    proxy_url = Column(String, nullable=True)  # 绑定的独享代理IP

    cdkeys = relationship('CdKey', back_populates='account')


class CdKey(Base):
    __tablename__ = 'cdkeys'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    key_code = Column(String, unique=True, index=True)
    duration = Column(Integer)  # 授权天数
    status = Column(Integer, default=0)  # 0=未使用 1=已使用 2=已作废
    max_uses = Column(Integer, default=0)  # 0=不限次数
    use_count = Column(Integer, default=0)  # 已授权次数
    expires_at = Column(Integer, nullable=True)  # Unix 时间戳，首次打开时写入
    account_id = Column(Integer, ForeignKey('disk_accounts.id'), nullable=True)

    account = relationship('DiskAccount', back_populates='cdkeys')


class DeviceKickLog(Base):
    __tablename__ = 'device_kick_logs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    key_code = Column(String, index=True)
    account_name = Column(String)
    account_group = Column(String, default='vip')
    status = Column(String)  # "成功" | "失败"
    action = Column(String)  # "扫码登录" | "踢出设备"
    ip_address = Column(String, default='unknown')
    device_name = Column(String, default='未知设备')
    location = Column(String, default='未知位置')
    qr_location = Column(String, default='')
    created_at = Column(Integer)  # 时间戳
    error_msg = Column(String, default='')


class XianyuUser(Base):
    __tablename__ = 'xianyu_users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, default='')
    password_hash = Column(String, default='')
    is_admin = Column(Boolean, default=False)
    allowed_ip = Column(String, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuCookie(Base):
    __tablename__ = 'xianyu_cookies'

    id = Column(Integer, primary_key=True, index=True)
    cookie_id = Column(String, unique=True, index=True)
    owner_username = Column(String, index=True, default='')
    cookie_value = Column(Text, default='')
    login_username = Column(String, default='')
    login_password = Column(Text, default='')
    display_name = Column(String, default='')
    remark = Column(String, default='')
    enabled = Column(Boolean, default=True)
    show_browser = Column(Boolean, default=False)
    auto_confirm = Column(Boolean, default=True)
    auto_comment = Column(Boolean, default=False)
    pause_duration = Column(Integer, default=0)
    avatar_url = Column(String, default='')
    goofish_user_id = Column(String, index=True, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    ck_validation_status = Column(String, default='')
    ck_validation_message = Column(Text, default='')
    ck_verification_url = Column(Text, default='')
    ck_validation_checked_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuStoreState(Base):
    __tablename__ = 'xianyu_store_states'

    id = Column(Integer, primary_key=True, index=True)
    store_key = Column(String, unique=True, index=True, default='default')
    schema_version = Column(String, default='v3-structured-db')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuItemReply(Base):
    __tablename__ = 'xianyu_item_replies'

    id = Column(Integer, primary_key=True, index=True)
    reply_key = Column(String, unique=True, index=True, default='')
    owner_username = Column(String, index=True, default='')
    cookie_id = Column(String, index=True, default='')
    item_id = Column(String, index=True, default='')
    item_title = Column(String, default='')
    reply_content = Column(Text, default='')
    enabled = Column(Boolean, default=True)
    reply_once = Column(Boolean, default=False)
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuCard(Base):
    __tablename__ = 'xianyu_cards'

    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String, index=True, default='')
    name = Column(String, default='')
    card_type = Column(String, default='text')
    description = Column(Text, default='')
    delivery_template = Column(Text, default='')
    product_info_template = Column(Text, default='')
    usage_info = Column(Text, default='')
    usage_tutorial = Column(Text, default='')
    usage_notice = Column(Text, default='')
    enabled = Column(Boolean, default=True)
    delay_seconds = Column(Integer, default=0)
    is_multi_spec = Column(Boolean, default=False)
    spec_name = Column(String, default='')
    spec_value = Column(String, default='')
    spec_name_2 = Column(String, default='')
    spec_value_2 = Column(String, default='')
    api_config = Column(Text, default='')
    text_content = Column(Text, default='')
    data_content = Column(Text, default='')
    image_url = Column(Text, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuDeliveryRule(Base):
    __tablename__ = 'xianyu_delivery_rules'

    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String, index=True, default='')
    keyword = Column(String, index=True, default='')
    item_id = Column(String, index=True, default='')
    card_id = Column(Integer, nullable=True)
    delivery_count = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    description = Column(Text, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuMessageDeliveryRule(Base):
    __tablename__ = 'xianyu_message_delivery_rules'

    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String, index=True, default='')
    cookie_id = Column(String, index=True, default='')
    item_id = Column(String, index=True, default='')
    keyword = Column(String, index=True, default='')
    card_id = Column(Integer, nullable=True)
    delivery_count = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    description = Column(Text, default='')
    send_once = Column(Boolean, default=True)
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuMessageDeliveryRecord(Base):
    __tablename__ = 'xianyu_message_delivery_records'

    id = Column(Integer, primary_key=True, index=True)
    record_key = Column(String, unique=True, index=True, default='')
    owner_username = Column(String, index=True, default='')
    cookie_id = Column(String, index=True, default='')
    chat_id = Column(String, index=True, default='')
    peer_user_id = Column(String, default='')
    item_id = Column(String, index=True, default='')
    source_message_id = Column(String, index=True, default='')
    rule_id = Column(String, index=True, default='')
    keyword = Column(String, default='')
    card_id = Column(String, default='')
    delivery_preview = Column(Text, default='')
    created_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class XianyuDeliveryLog(Base):
    __tablename__ = 'xianyu_delivery_logs'

    id = Column(Integer, primary_key=True, index=True)
    log_key = Column(String, unique=True, index=True, default='')
    owner_username = Column(String, index=True, default='')
    cookie_id = Column(String, index=True, default='')
    chat_id = Column(String, index=True, default='')
    order_id = Column(String, index=True, default='')
    status = Column(String, index=True, default='')
    scene = Column(String, index=True, default='')
    card_name = Column(String, default='')
    reason = Column(Text, default='')
    created_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class JudianUser(Base):
    __tablename__ = 'judian_users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    allowed_ip = Column(String, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class JudianAccount(Base):
    __tablename__ = 'judian_accounts'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String, unique=True, index=True, default='')
    owner_username = Column(String, index=True, default='')
    display_name = Column(String, default='')
    login_email = Column(String, index=True, default='')
    login_password = Column(Text, default='')
    mobile_login_link = Column(Text, default='')
    session_token = Column(Text, default='')
    user_sig = Column(Text, default='')
    status = Column(String, index=True, default='pending')
    remark = Column(String, default='')
    enabled = Column(Boolean, default=True)
    diamond_quantity = Column(Integer, default=0)
    diamond_quantity_updated_at = Column(String, default='')
    last_login_at = Column(String, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class JudianCard(Base):
    __tablename__ = 'judian_cards'

    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String, index=True, default='')
    name = Column(String, default='')
    card_type = Column(String, default='text')
    description = Column(Text, default='')
    enabled = Column(Boolean, default=True)
    text_content = Column(Text, default='')
    data_content = Column(JSON, default=dict)
    link_url = Column(Text, default='')
    delivery_template = Column(Text, default='')
    usage_info = Column(Text, default='')
    usage_notice = Column(Text, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class JudianCdKey(Base):
    __tablename__ = 'judian_cdkeys'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    owner_username = Column(String, index=True, default='')
    account_id = Column(String, index=True, default='')
    card_id = Column(Integer, nullable=True)
    duration = Column(Integer, default=30)
    status = Column(String, index=True, default='unused')
    max_uses = Column(Integer, default=0)
    use_count = Column(Integer, default=0)
    expires_at = Column(Integer, nullable=True)
    latest_session_id = Column(String, index=True, default='')
    latest_order_id = Column(String, index=True, default='')
    remark = Column(String, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)



class JudianScanSession(Base):
    __tablename__ = 'judian_scan_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    owner_username = Column(String, index=True, default='')
    account_id = Column(String, index=True, default='')
    order_id = Column(String, index=True, default='')
    scene = Column(String, default='cdkey_redeem')
    qr_content = Column(Text, default='')
    mobile_login_link = Column(Text, default='')
    unlock_url = Column(Text, default='')
    status = Column(String, index=True, default='pending')
    message = Column(String, default='')
    expires_at = Column(Integer, nullable=True)
    confirmed_at = Column(Integer, nullable=True)
    result_payload = Column(JSON, default=dict)
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
    payload = Column(JSON, default=dict)


class JudianBatchPurchaseTask(Base):
    __tablename__ = 'judian_batch_purchase_tasks'

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, unique=True, index=True)
    session_id = Column(String, index=True, default='')
    owner_username = Column(String, index=True, default='')
    account_id = Column(String, index=True, default='')
    cdkey_code = Column(String, index=True, default='')
    status = Column(String, index=True, default='pending')
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    total_consumed_diamond = Column(Integer, default=0)
    current_index = Column(Integer, default=0)
    current_trade_no = Column(String, index=True, default='')
    message = Column(String, default='')
    result_payload = Column(JSON, default=dict)
    payload = Column(JSON, default=dict)
    created_at = Column(String, default='')
    updated_at = Column(String, default='')



class JudianOrder(Base):
    __tablename__ = 'judian_orders'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    owner_username = Column(String, index=True, default='')
    account_id = Column(String, index=True, default='')
    item_id = Column(String, default='')
    item_title = Column(String, default='')
    buyer_id = Column(String, default='')
    buyer_nick = Column(String, default='')
    amount = Column(String, default='')
    quantity = Column(Integer, default=1)
    order_status = Column(String, default='pending')
    delivery_rule_id = Column(Integer, nullable=True)
    delivery_card_id = Column(Integer, nullable=True)

    delivery_content_preview = Column(Text, default='')
    delivery_link = Column(Text, default='')
    delivery_payload = Column(JSON, default=dict)
    raw_payload = Column(JSON, default=dict)
    delivered_at = Column(String, default='')
    created_at = Column(String, default='')
    updated_at = Column(String, default='')
