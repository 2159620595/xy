from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

from urllib.parse import parse_qs, urlparse, urlsplit



import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from backend.netdisk import models
    from backend.netdisk.database import SessionLocal, get_db
except ModuleNotFoundError:
    from netdisk import models
    from netdisk.database import SessionLocal, get_db

app = FastAPI(title='Judian API')
security = HTTPBearer(auto_error=False)
JWT_SECRET = os.environ.get('JUDIAN_JWT_SECRET') or f"{os.environ.get('API_SECRET_KEY', 'judian-secret')}-judian"
DEFAULT_TRUSTED_UI_ORIGINS = str(os.environ.get('CORS_ALLOW_ORIGINS', '') or '').strip()
JUDIAN_DEFAULT_TRUSTED_UI_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'https://woshishabi.xyz',
    'https://www.woshishabi.xyz',
]


RSA_PRIVATE_KEY_STR = 'MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAK2obrvkb/npsEjqvvuJcVgGigOcdtvjGMGggufULIf6u4otOsofcBHdk3QZ2H/0qnf9Na7q6wmmE1+kuWJlEUO1/G/coBLrb3J3H7W6L2QR0dIYccEnD1P5qRaXdJvSWgSRIqzPQcP1A1a9BTwiDpQ9v77NTWGqi4JfbY24eI5TAgMBAAECgYABQd9vX9OJuS3sETsJwjB+ZSm5pffcVrQWrs1T1V7vKxsRgItU7E5Y6sRHCmrdXk2fqccqOYwzGS85uY0YD8hEtK580SCz1XKAgVqe/loPi7lYJH1W1xN29WWtS1JjNSN5HnPlWwQbGwkTxo1Om9u/SJ/fYphVXriwLP8bP+VCWQJBANOQJtRABQS4OYAHyyVbW6RBZ5d64Y/Kjhf1ZlIKRa9QDWCRlNg6XrJ0tZ5xt9RK1SDRZDniu6Eku3YHuI0/CJkCQQDSIhpNbDbS1554x1dO7oZATdufL+JVjZa/o6tqizslo5aoD7ahREuOh7e1mI4yDqmaA6jSsRL9OyG4a11lN8XLAkEAxe/kpEiRaW0DPyoLgpQLFY6r4Snyx5l3gCr05GT/9ZosKeGLJRLXbpeLJQa4O0MYTHAcGZxsd8PqL+/hVyVWYQJBAMFucxfiDXV41oAHv+8A0sRO52RaB9cJR0ORvjGNiRzUwdJi5JL+8y548DtR+1NI/AayZ63LItfInvnMm2SZOpECQFtjgv08sKNyKgFKOumAl55A4/Ai4LX7w1US2HGAeOJwL8G6nipePA8KbGBzjvXH9Lfr8GEuy1DdCxYcxhwnmWg='

RSA_PUBLIC_KEY_STR = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDkmujpECrpxvCCF5iHnXDhSb4a8OODNg7x2dUggK0JNWzbw3Oz30aIZxzXm0dfVTRhuO+Upv0gtkwx5WVW1oLzwxAcQwmWx5G0F5B3yglsGZoDJZwgZmp7zrowOkyR59zKy4CHwbjwcxaSBVXtJ/NIZ21x63p663Nxjj1ZTIkl3wIDAQAB'

LOGIN_URL = 'http://111.230.160.82/v2/user/login'
USER_INFO_URL = 'http://111.230.160.82/user/info'
FUND_URL = 'http://111.230.160.82/user/fund/getFund'
ORDER_SCAN_URL = 'http://64.120.95.181:2026/pc/order/scan'

ORDER_INFO_URL = 'http://111.230.160.82/order/info/getApiOrder'
ORDER_PAY_URL = 'http://111.230.160.82/v2/order/info/payApiOrder'
BATCH_VIP_PRICE_LIST_URL = 'http://bkbf.xn--vhqr42drhf5k7b.com/pc/vip_price/list'
REMOTE_TIMEOUT_SECONDS = 20
REMOTE_SUPPLEMENTAL_TIMEOUT_SECONDS = 8
ANDROID_MODELS = ['22041211AC', 'SM-G9910', 'KB2000', 'V2049A', 'M2102K1C']
PUBLIC_WEB_APP_ID = '4150439554430627'
PUBLIC_WEB_APP_VERSION = '1.1.9'
PUBLIC_WEB_INTERNAL_VERSION = '1.0.0'
PUBLIC_WEB_PLATFORM = '3'
PUBLIC_WEB_REQUEST_VERSION = '2024-09-24'
PUBLIC_WEB_AUTH_KEY = b'ziISjqkXPsGUMRNGyWigxDGtJbfTdcGv'
PUBLIC_WEB_AUTH_IV = b'WonrnVkxeIxDcFbv'

ACCOUNT_ID_PATTERN = re.compile(r'(\d+)$')
_JUDIAN_SCHEMA_READY = False


class JudianRemoteError(RuntimeError):
    """聚点远端接口调用失败。"""


class JudianSessionRequest(BaseModel):
    username: str
    role: str | None = 'admin'


class JudianAccountLoginRequest(BaseModel):
    id: int | None = None
    loginEmail: str
    loginPassword: str
    displayName: str | None = ''
    remark: str | None = ''


class JudianAccountUpdateRequest(BaseModel):
    loginEmail: str | None = None
    loginPassword: str | None = None
    displayName: str | None = None
    remark: str | None = None
    enabled: bool | None = None


class JudianCdKeyRedeemRequest(BaseModel):
    code: str


class JudianCdKeyGenerateRequest(BaseModel):
    accountId: str
    duration: int = 30
    count: int = 1
    maxUses: int = 1
    remark: str | None = ''


class JudianCdKeyUpdateRequest(BaseModel):
    status: str | None = None
    remark: str | None = None


class JudianCdKeyClaimRequest(BaseModel):
    accountId: str | None = None
    cardId: int | None = None
    count: int = 1
    markStatus: str | None = 'active'


class JudianCdKeyImportRequest(BaseModel):
    accountId: str
    codes: list[str] | None = None
    content: str | None = None
    duration: int = 1
    maxUses: int = 5
    cardId: int | None = None
    remark: str | None = ''


class JudianCardCodesImportFromNetdiskRequest(BaseModel):
    cardId: int
    remark: str | None = ''
    limit: int | None = 500


class JudianCardCodesImportFromJudianRequest(BaseModel):
    cardId: int
    accountId: str | None = None
    status: str | None = 'unused'
    remark: str | None = ''
    limit: int | None = 500

class JudianCardCreateRequest(BaseModel):
    name: str
    cardType: str | None = 'text'
    description: str | None = ''
    remark: str | None = ''
    enabled: bool | None = True
    deliveryTemplate: str | None = ''
    productInfoTemplate: str | None = ''
    usageInfo: str | None = ''
    usageTutorial: str | None = ''
    notice: str | None = ''
    textContent: str | None = ''
    bulkContent: str | None = ''
    delaySeconds: int | None = 0
    autoGenerateRules: bool | None = False
    multiSpec: bool | None = False
    specName: str | None = ''
    specValue: str | None = ''
    specName2: str | None = ''
    specValue2: str | None = ''
    apiConfig: str | None = ''
    imageUrl: str | None = ''
    linkUrl: str | None = ''





class JudianCdKeyImportFromNetdiskRequest(BaseModel):
    accountId: str
    duration: int = 1
    maxUses: int = 5
    cardId: int | None = None
    remark: str | None = ''
    limit: int | None = 500


class JudianPublicUnlockScanRequest(BaseModel):
    qrText: str | None = ''
    tradeNo: str | None = ''
    orderNo: str | None = ''


class JudianPublicBatchPurchaseItemRequest(BaseModel):
    qrText: str | None = ''
    tradeNo: str | None = ''
    orderNo: str | None = ''


class JudianPublicBatchPurchaseRequest(BaseModel):
    items: list[JudianPublicBatchPurchaseItemRequest] | None = None
    count: int | None = None
    account: str | None = None
    password: str | None = None
    vipId: str | None = None
    packageType: str | None = None




def now_text() -> str:

    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_judian_schema(db: Session | None = None) -> None:
    global _JUDIAN_SCHEMA_READY
    if _JUDIAN_SCHEMA_READY:
        return

    owns_session = db is None
    session = db or SessionLocal()
    try:
        models.Base.metadata.create_all(bind=session.get_bind())
        _JUDIAN_SCHEMA_READY = True
    finally:
        if owns_session:
            session.close()


def normalize_origin_value(value: str | None) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    try:
        parsed = urlsplit(text if '://' in text else f'https://{text}')
    except Exception:
        return ''
    scheme = str(parsed.scheme or 'https').strip().lower()
    netloc = str(parsed.netloc or '').strip().lower()
    if scheme not in {'http', 'https'} or not netloc:
        return ''
    return f'{scheme}://{netloc}'


def parse_origin_allowlist(value: str | None) -> list[str]:
    raw_text = str(value or '')
    if not raw_text.strip():
        return []
    normalized: list[str] = []
    for part in re.split(r'[\n,;]+', raw_text):
        origin = normalize_origin_value(part)
        if origin and origin not in normalized:
            normalized.append(origin)
    return normalized


def get_request_origin_candidates(request: Request | None) -> list[str]:
    if request is None:
        return []
    candidates: list[str] = []
    for header_name in ('origin', 'referer'):
        origin = normalize_origin_value(request.headers.get(header_name))
        if origin and origin not in candidates:
            candidates.append(origin)
    return candidates


def get_trusted_ui_origins() -> list[str]:
    trusted = parse_origin_allowlist(DEFAULT_TRUSTED_UI_ORIGINS)
    for origin in parse_origin_allowlist(os.environ.get('JUDIAN_TRUSTED_UI_ORIGINS', '')):
        if origin not in trusted:
            trusted.append(origin)
    return trusted


def is_request_from_trusted_ui(request: Request | None) -> bool:
    trusted_origins = get_trusted_ui_origins()
    if not trusted_origins:
        return False
    return any(candidate in trusted_origins for candidate in get_request_origin_candidates(request))


def resolve_client_ip(request: Request | None) -> str:
    if request is None:
        return ''
    forwarded_for = str(request.headers.get('x-forwarded-for') or '').strip()
    if forwarded_for:
        first_ip = forwarded_for.split(',')[0].strip()
        if first_ip:
            return first_ip
    real_ip = str(request.headers.get('x-real-ip') or '').strip()
    if real_ip:
        return real_ip
    client = getattr(request, 'client', None)
    host = getattr(client, 'host', '') if client else ''
    return str(host or '').strip()



def create_token(username: str, is_admin: bool) -> str:
    payload = {
        'sub': username,
        'username': username,
        'is_admin': bool(is_admin),
        'exp': int(time.time()) + 7 * 24 * 3600,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')
    sign = hmac.new(JWT_SECRET.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).hexdigest()
    return f'{body}.{sign}'


def decode_token(token: str) -> dict[str, Any]:
    try:
        body, sign = token.rsplit('.', 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail='聚点登录无效') from exc
    expected = hmac.new(JWT_SECRET.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sign):
        raise HTTPException(status_code=401, detail='聚点登录无效')
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)).decode('utf-8'))
    except Exception as exc:
        raise HTTPException(status_code=401, detail='聚点登录无效') from exc
    if int(payload.get('exp') or 0) < int(time.time()):
        raise HTTPException(status_code=401, detail='聚点登录已过期')
    return payload


def upsert_judian_user(db: Session, username: str, *, is_admin: bool, request: Request | None = None) -> models.JudianUser:
    ensure_judian_schema(db)
    row = db.query(models.JudianUser).filter_by(username=username).first()
    now = now_text()
    current_ip = resolve_client_ip(request)
    if row is None:
        row = models.JudianUser(
            username=username,
            is_admin=bool(is_admin),
            allowed_ip=current_ip,
            created_at=now,
            updated_at=now,
            payload={},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    row.is_admin = bool(is_admin)
    if current_ip and not str(row.allowed_ip or '').strip():
        row.allowed_ip = current_ip
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def issue_judian_session(username: str, role: str | None = None, request: Request | None = None) -> dict[str, Any] | None:
    username = (username or '').strip()
    if not username:
        return None

    db = SessionLocal()
    try:
        is_admin = (role or 'admin') == 'admin'
        user = upsert_judian_user(db, username, is_admin=is_admin, request=request)
        return {
            'success': True,
            'token': create_token(username, bool(user.is_admin)),
            'message': '聚点会话同步成功',
            'user_id': user.id,
            'username': user.username,
            'is_admin': bool(user.is_admin),
        }
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ensure_judian_schema(db)
    username = str(request.headers.get('x-judian-username') or '').strip() or 'admin'
    user = db.query(models.JudianUser).filter_by(username=username).first()
    if user is None:
        user = upsert_judian_user(db, username, is_admin=True, request=request)
    elif not bool(user.is_admin):
        user.is_admin = True
        user.updated_at = now_text()
        db.commit()
        db.refresh(user)

    return {
        'username': username,
        'sub': username,
        'is_admin': True,
    }


def resolve_claim_api_token(request: Request) -> str:
    auth_value = str(request.headers.get('authorization') or '').strip()
    if auth_value.lower().startswith('bearer '):
        return auth_value[7:].strip()
    return str(
        request.headers.get('x-api-key')
        or request.query_params.get('token')
        or ''
    ).strip()


def ensure_claim_api_authorized(request: Request) -> None:
    expected_token = str(os.environ.get('JUDIAN_CLAIM_API_TOKEN') or '').strip()
    if not expected_token:
        return
    provided_token = resolve_claim_api_token(request)
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail='卡密领取接口鉴权失败')


def owner_scoped_account_query(db: Session, user: dict[str, Any]):
    query = db.query(models.JudianAccount)
    if user.get('is_admin'):
        return query
    return query.filter_by(owner_username=str(user.get('username') or '').strip())


def owner_scoped_cdkey_query(db: Session, user: dict[str, Any]):
    query = db.query(models.JudianCdKey)
    if user.get('is_admin'):
        return query
    return query.filter_by(owner_username=str(user.get('username') or '').strip())


def owner_scoped_card_query(db: Session, user: dict[str, Any]):
    query = db.query(models.JudianCard)
    if user.get('is_admin'):
        return query
    return query.filter_by(owner_username=str(user.get('username') or '').strip())


def parse_card_content_lines(value: Any) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for raw_line in str(value or '').replace('\r\n', '\n').split('\n'):
        line = raw_line.strip().replace('\u3000', ' ')
        if not line or line in seen:
            continue
        seen.add(line)
        rows.append(line)
    return rows


def build_card_data_content(body: JudianCardCreateRequest, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = dict(existing or {})
    content_text = str(body.bulkContent or '').replace('\r\n', '\n').strip()
    codes = parse_card_content_lines(content_text)
    return {
        **previous,
        'contentText': content_text,
        'codes': codes,
        'productInfoTemplate': str(body.productInfoTemplate or '').strip(),
        'delaySeconds': int(body.delaySeconds or 0),
        'autoGenerateRules': bool(body.autoGenerateRules or False),
        'multiSpec': bool(body.multiSpec or False),
        'specName': str(body.specName or '').strip(),
        'specValue': str(body.specValue or '').strip(),
        'specName2': str(body.specName2 or '').strip(),
        'specValue2': str(body.specValue2 or '').strip(),
        'usageTutorial': str(body.usageTutorial or '').strip(),
        'apiConfig': str(body.apiConfig or '').strip(),
        'imageUrl': str(body.imageUrl or '').strip(),
        'updatedAt': now_text(),
        'source': str(previous.get('source') or 'manual').strip() or 'manual',
    }


def serialize_card(row: models.JudianCard) -> dict[str, Any]:
    data_content = dict_like(row.data_content)
    stored_codes = data_content.get('codes') if isinstance(data_content.get('codes'), list) else []
    codes = [str(item or '').strip() for item in stored_codes if str(item or '').strip()]
    content_text = pick_text(data_content.get('contentText'), '\n'.join(codes))
    card_type = row.card_type or 'text'
    multi_spec = bool(data_content.get('multiSpec'))
    auto_generate_rules = bool(data_content.get('autoGenerateRules'))
    image_url = pick_text(data_content.get('imageUrl'), row.link_url)
    return {
        'id': row.id,
        'ownerUsername': row.owner_username or '',
        'name': row.name or '',
        'type': card_type,
        'cardType': card_type,
        'description': row.description or '',
        'enabled': bool(row.enabled),
        'textContent': row.text_content or '',
        'dataContent': content_text,
        'dataContentCount': len(codes),
        'linkUrl': row.link_url or '',
        'imageUrl': image_url,
        'deliveryTemplate': row.delivery_template or '',
        'productInfoTemplate': pick_text(data_content.get('productInfoTemplate')),
        'usageInfo': row.usage_info or '',
        'usageTutorial': pick_text(data_content.get('usageTutorial')),
        'usageNotice': row.usage_notice or '',
        'delaySeconds': pick_int(data_content.get('delaySeconds')),
        'autoGenerateRules': auto_generate_rules,
        'generateDeliveryRule': auto_generate_rules,
        'multiSpec': multi_spec,
        'isMultiSpec': multi_spec,
        'specName': pick_text(data_content.get('specName')),
        'specValue': pick_text(data_content.get('specValue')),
        'specName2': pick_text(data_content.get('specName2')),
        'specValue2': pick_text(data_content.get('specValue2')),
        'apiConfig': pick_text(data_content.get('apiConfig')),
        'createdAt': row.created_at or '',
        'updatedAt': row.updated_at or '',
        'created_at': row.created_at or '',
        'updated_at': row.updated_at or '',
        'payload': dict_like(row.payload),
        'rawDataContent': data_content,
    }



def get_account_or_404(db: Session, user: dict[str, Any], row_id: int) -> models.JudianAccount:
    row = owner_scoped_account_query(db, user).filter_by(id=row_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail='聚点账号不存在')
    return row


def get_cdkey_or_404(db: Session, user: dict[str, Any], row_id: int) -> models.JudianCdKey:
    row = owner_scoped_cdkey_query(db, user).filter_by(id=row_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail='聚点卡密不存在')
    return row


def get_card_or_404(db: Session, user: dict[str, Any], row_id: int) -> models.JudianCard:
    row = owner_scoped_card_query(db, user).filter_by(id=row_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail='聚点卡券不存在')
    return row


def next_local_account_id(db: Session) -> str:


    max_number = 10000
    for (account_id,) in db.query(models.JudianAccount.account_id).all():
        matched = ACCOUNT_ID_PATTERN.search(str(account_id or ''))
        if matched:
            max_number = max(max_number, int(matched.group(1)))
    return f'JD{max_number + 1:05d}'


def build_headers() -> dict[str, str]:
    return {
        'User-Agent': f"Dalvik/2.1.0 (Linux; U; Android {random.randint(10, 14)}; {random.choice(ANDROID_MODELS)} Build/UP1A.231005.007)",
        'App-Version': '2.0.4',
        'App-Number': hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16],
        'System-Type': 'Android',
    }


def encrypt_public_web_auth(text: str) -> str:
    encoded_text = base64.b64encode(str(text or '').encode('utf-8'))
    cipher = AES.new(PUBLIC_WEB_AUTH_KEY, AES.MODE_CBC, PUBLIC_WEB_AUTH_IV)
    encrypted = cipher.encrypt(pad(encoded_text, AES.block_size))
    return base64.b64encode(encrypted).decode()


def build_public_web_headers(token: str = '') -> dict[str, Any]:
    timestamp = int(time.time() * 1000)
    auth = '-'.join([
        PUBLIC_WEB_APP_VERSION,
        str(timestamp),
        PUBLIC_WEB_PLATFORM,
        PUBLIC_WEB_INTERNAL_VERSION,
        sys.platform,
    ])
    headers: dict[str, Any] = {
        'Content-Type': 'application/json',
        'ts': str(timestamp),
        'X-VERSION': PUBLIC_WEB_REQUEST_VERSION,
        'APPID': PUBLIC_WEB_APP_ID,
        'Authentication': encrypt_public_web_auth(auth),
        'system': '3' if os.name == 'nt' else '4',
    }
    normalized_token = str(token or '').strip()
    if normalized_token:
        headers['X-Token'] = normalized_token
    return headers


def aes_encrypt(text: str, key: str) -> str:
    cipher = AES.new(key.encode(), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(text.encode(), AES.block_size))).decode()


def aes_decrypt(key: str, ciphertext: str) -> str:
    cipher = AES.new(key.encode(), AES.MODE_ECB)
    return unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size).decode()


def rsa_decrypt(ciphertext: str) -> str:
    private_key = serialization.load_der_private_key(
        base64.b64decode(RSA_PRIVATE_KEY_STR),
        password=None,
        backend=default_backend(),
    )
    return private_key.decrypt(base64.b64decode(ciphertext), rsa_padding.PKCS1v15()).decode()


def get_secret(aes_key: str) -> str:
    public_key = serialization.load_der_public_key(
        base64.b64decode(RSA_PUBLIC_KEY_STR),
        backend=default_backend(),
    )
    return base64.b64encode(public_key.encrypt(aes_key.encode(), rsa_padding.PKCS1v15())).decode()


def extract_remote_value(payload: Any, *keys: str) -> str:
    if not isinstance(payload, dict):
        return ''

    for key in keys:
        value = payload.get(key)
        if value not in (None, ''):
            return str(value)

    for nested_key in ('data', 'user', 'userInfo', 'profile', 'result'):
        nested = payload.get(nested_key)
        if isinstance(nested, dict):
            value = extract_remote_value(nested, *keys)
            if value:
                return value

    return ''


def ensure_remote_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        text = response.text[:160].strip()
        raise JudianRemoteError(f'聚点远端返回了非 JSON 响应：{text or response.status_code}') from exc
    if not isinstance(payload, dict):
        raise JudianRemoteError('聚点远端响应结构异常')
    return payload


def remote_login(login_email: str, login_password: str) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(build_headers())
    aes_key = uuid.uuid4().hex[:16]
    request_payload = {
        'account': login_email,
        'appKey': 'android',
        'code': login_password,
        'inviteCode': '',
        'type': 2,
    }

    try:
        response = session.post(
            LOGIN_URL,
            data=aes_encrypt(json.dumps(request_payload, separators=(',', ':')), aes_key),
            headers={'Secret': get_secret(aes_key)},
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点登录请求失败：{exc}') from exc

    payload = ensure_remote_json(response)
    response_secret = str(response.headers.get('Secret') or '').strip()
    encrypted_data = payload.get('data')
    if not response_secret or not encrypted_data:
        detail = payload.get('msg') or payload.get('message') or '聚点登录失败'
        raise JudianRemoteError(str(detail))

    try:
        response_key = rsa_decrypt(response_secret)
        decrypted = aes_decrypt(response_key, str(encrypted_data))
        login_payload = json.loads(decrypted)
    except Exception as exc:
        raise JudianRemoteError('聚点登录响应解密失败') from exc

    access_token = str(login_payload.get('accessToken') or '').strip()
    if not access_token:
        detail = login_payload.get('msg') or payload.get('msg') or payload.get('message') or '聚点登录失败'
        raise JudianRemoteError(str(detail))

    session.headers.update({'Authorization': f'Bearer {access_token}'})
    return {
        'session': session,
        'token': access_token,
        'login_payload': login_payload,
        'raw_payload': payload,
        'request_headers': {key: str(value) for key, value in session.headers.items()},
    }


def remote_get_user_info(session: requests.Session, *, timeout: int | float = REMOTE_TIMEOUT_SECONDS) -> dict[str, Any]:
    aes_key = str(uuid.uuid4()).replace('-', '')[:16]
    try:
        response = session.get(
            USER_INFO_URL,
            headers={'Secret': get_secret(aes_key)},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点账号资料同步失败：{exc}') from exc

    return ensure_remote_json(response)


def remote_get_fund(session: requests.Session, *, timeout: int | float = REMOTE_TIMEOUT_SECONDS) -> tuple[int, dict[str, Any]]:
    aes_key = str(uuid.uuid4()).replace('-', '')[:16]
    try:
        response = session.get(
            FUND_URL,
            headers={'Secret': get_secret(aes_key)},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点钻石余额同步失败：{exc}') from exc

    payload = ensure_remote_json(response)
    message = pick_text(
        payload.get('msg'),
        payload.get('message'),
        extract_remote_value(payload, 'msg', 'message'),
    )
    if should_refresh_public_remote_session(message):
        raise JudianRemoteError(message or '聚点远端登录已失效')

    quantity = payload.get('data', {}).get('quantity', 0)
    try:
        diamond_quantity = int(quantity)
    except (TypeError, ValueError):
        diamond_quantity = 0
    return diamond_quantity, payload


def remote_get_public_vip_plans(*, timeout: int | float = REMOTE_SUPPLEMENTAL_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
    script_root = get_batch_script_root()
    script_path = os.path.join(script_root, 'test-vip.js')
    if os.path.isfile(script_path):
        try:
            completed = subprocess.run(
                ['node', 'test-vip.js', 'list'],
                cwd=script_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=max(10, int(timeout) + 6),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            result_payload = try_parse_script_json_output(str(completed.stdout or ''))
            if completed.returncode == 0:
                plans = result_payload.get('data')
                if isinstance(plans, list):
                    return [item for item in plans if isinstance(item, dict)]
                message = pick_text(
                    result_payload.get('msg'),
                    result_payload.get('message'),
                    str(completed.stderr or '').strip(),
                )
                raise JudianRemoteError(message or '批量下单脚本未返回可用套餐列表')
        except Exception:
            pass

    session = requests.Session()
    session.headers.update(build_public_web_headers())
    try:
        response = session.get(
            BATCH_VIP_PRICE_LIST_URL,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点套餐列表获取失败：{exc}') from exc

    try:
        payload = response.json()
    except ValueError as exc:
        text = str(response.text or '').strip()[:160]
        raise JudianRemoteError(f'聚点套餐列表返回了非 JSON 响应：{text or response.status_code}') from exc

    if isinstance(payload, dict):
        code = str(payload.get('code') or '').strip()
        if code and code not in {'200', '20000'}:
            message = pick_text(payload.get('msg'), payload.get('message'))
            raise JudianRemoteError(message or f'聚点套餐列表请求失败，code={code}')

    if isinstance(payload, dict):
        plans = payload.get('data')
    else:
        plans = payload
    if not isinstance(plans, list):
        raise JudianRemoteError('聚点套餐列表响应结构异常')
    return [item for item in plans if isinstance(item, dict)]


def extract_public_vip_plan_diamond_cost(plan: dict[str, Any]) -> int:
    return max(
        0,
        pick_int(
            plan.get('coin'),
            plan.get('coins'),
            plan.get('diamond'),
            plan.get('diamond_quantity'),
            plan.get('price'),
        ),
    )


def match_public_vip_plan_type(plan: dict[str, Any], package_type: str) -> bool:
    normalized_type = str(package_type or '').strip().lower()
    if not normalized_type:
        return False
    title = pick_text(plan.get('title'), plan.get('name')).lower().replace(' ', '')
    face_value = pick_int(plan.get('face_value'), plan.get('faceValue'), plan.get('duration'))
    if normalized_type == 'day':
        return face_value == 1 or any(keyword in title for keyword in ('1天', '天卡', '日卡'))
    if normalized_type == 'week':
        return face_value == 7 or any(keyword in title for keyword in ('7天', '周卡'))
    if normalized_type == 'month':
        return face_value in {30, 31} or any(keyword in title for keyword in ('30天', '月卡'))
    if normalized_type == 'quarter':
        return face_value in {90, 91, 92} or any(keyword in title for keyword in ('90天', '季卡'))
    if normalized_type == 'year':
        return face_value in {365, 366} or any(keyword in title for keyword in ('365天', '年卡'))
    return False


def pick_public_batch_vip_plan(
    plans: list[dict[str, Any]],
    *,
    vip_id: str = '',
    package_type: str = '',
) -> dict[str, Any]:
    explicit_vip_id = str(vip_id or '').strip()
    if explicit_vip_id:
        for plan in plans:
            if pick_text(plan.get('id')) == explicit_vip_id:
                return plan
        raise HTTPException(status_code=400, detail=f'未找到 vip_id={explicit_vip_id} 的套餐')

    normalized_type = str(package_type or '').strip().lower()
    if normalized_type and normalized_type != 'custom':
        for plan in plans:
            if match_public_vip_plan_type(plan, normalized_type):
                return plan
        type_label_map = {
            'day': '天卡',
            'week': '周卡',
            'month': '月卡',
            'quarter': '季卡',
            'year': '年卡',
        }
        raise HTTPException(
            status_code=400,
            detail=f'当前未找到{type_label_map.get(normalized_type, "所选")}套餐，请改用自定义填写 VIP ID',
        )

    return plans[0]


def resolve_public_batch_required_diamond(count: int, *, vip_id: str = '', package_type: str = '') -> tuple[str, int, int]:
    target_count = max(1, int(count))
    try:
        plans = remote_get_public_vip_plans()
    except JudianRemoteError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not plans:
        raise HTTPException(status_code=502, detail='未获取到可购买套餐，无法校验批量扣费额度')
    selected_plan = pick_public_batch_vip_plan(plans, vip_id=vip_id, package_type=package_type)
    vip_id = pick_text(selected_plan.get('id'))
    unit_diamond = extract_public_vip_plan_diamond_cost(selected_plan)
    if unit_diamond <= 0:
        raise HTTPException(
            status_code=502,
            detail=f'套餐 vip_id={vip_id or "unknown"} 未返回有效钻石单价，无法校验批量扣费额度',
        )
    return vip_id, unit_diamond, unit_diamond * target_count


def build_public_batch_purchase_preview(
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    *,
    count: int,
    vip_id: str = '',
    package_type: str = '',
) -> dict[str, Any]:
    resolved_vip_id, unit_diamond, required_diamond = resolve_public_batch_required_diamond(
        count,
        vip_id=vip_id,
        package_type=package_type,
    )
    available_diamond = max(0, resolve_account_diamond_quantity(account))
    max_uses = pick_int(cdkey_row.max_uses)
    used_uses = pick_int(cdkey_row.use_count)
    remaining_quota = -1 if max_uses <= 0 else max(0, max_uses - used_uses)
    enough_diamond = available_diamond >= required_diamond
    enough_quota = remaining_quota < 0 or remaining_quota >= required_diamond
    can_submit = enough_diamond and enough_quota
    return {
        'vipId': resolved_vip_id,
        'packageType': str(package_type or '').strip().lower(),
        'count': max(1, int(count)),
        'unitDiamond': unit_diamond,
        'requiredDiamond': required_diamond,
        'availableDiamond': available_diamond,
        'remainingQuota': remaining_quota,
        'enoughDiamond': enough_diamond,
        'enoughQuota': enough_quota,
        'canSubmit': can_submit,
    }


def ensure_public_cdkey_quota_sufficient(cdkey_row: models.JudianCdKey, required_diamond: int) -> None:
    required = max(0, pick_int(required_diamond))
    max_uses = pick_int(cdkey_row.max_uses)
    if max_uses <= 0 or required <= 0:
        return
    used_uses = pick_int(cdkey_row.use_count)
    remaining_quota = max(0, max_uses - used_uses)
    if required > remaining_quota:
        raise HTTPException(status_code=400, detail=f'卡密额度不足，需 {required} 钻，剩余 {remaining_quota} 钻')


def apply_public_cdkey_consumption(
    cdkey_row: models.JudianCdKey,
    consumed_diamond: int,
    *,
    latest_order_id: str = '',
) -> None:
    consumed = max(0, pick_int(consumed_diamond))
    cdkey_row.use_count = int(cdkey_row.use_count or 0) + consumed
    if int(cdkey_row.max_uses or 0) > 0 and int(cdkey_row.use_count or 0) >= int(cdkey_row.max_uses or 0):
        cdkey_row.status = 'expired'
    else:
        cdkey_row.status = 'active'
    if latest_order_id:
        cdkey_row.latest_order_id = latest_order_id
    cdkey_row.updated_at = now_text()


def apply_public_account_diamond_snapshot(account: models.JudianAccount, after_diamond: int) -> None:
    account.diamond_quantity = max(0, pick_int(after_diamond))
    account.diamond_quantity_updated_at = now_text()
    account.updated_at = now_text()


def resolve_public_batch_latest_trade_no(items_result: list[dict[str, Any]]) -> str:
    for item in reversed(items_result):
        if str(item.get('status') or '') == 'completed':
            return pick_text(item.get('tradeNo'), item.get('orderNo'))
    for item in reversed(items_result):
        trade_no = pick_text(item.get('tradeNo'), item.get('orderNo'))
        if trade_no:
            return trade_no
    return ''


def apply_public_batch_script_consumption(
    batch_task_row: models.JudianBatchPurchaseTask,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    *,
    items_result: list[dict[str, Any]],
    result_payload: dict[str, Any],
    total_consumed_diamond: int,
) -> None:
    payload = dict_like(batch_task_row.payload)
    if payload.get('localDiamondSynced') is True:
        return

    consumed = max(0, pick_int(total_consumed_diamond))
    before_diamond = max(
        0,
        pick_int(
            result_payload.get('availableDiamond'),
            payload.get('beforeDiamond'),
            account.diamond_quantity,
        ),
    )
    after_diamond = max(0, before_diamond - consumed)
    latest_trade_no = resolve_public_batch_latest_trade_no(items_result)

    apply_public_account_diamond_snapshot(account, after_diamond)
    apply_public_cdkey_consumption(cdkey_row, consumed, latest_order_id=latest_trade_no)

    batch_task_row.payload = {
        **payload,
        'localDiamondSynced': True,
        'beforeDiamond': before_diamond,
        'afterDiamond': after_diamond,
    }
    batch_task_row.result_payload = {
        **dict_like(batch_task_row.result_payload),
        'beforeDiamond': before_diamond,
        'afterDiamond': after_diamond,
        'consumedDiamond': consumed,
    }




def dict_like(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def pick_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ''


def pick_int(*values: Any) -> int:
    for value in values:
        if value in (None, ''):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def pick_nullable_int(*values: Any) -> int | None:
    for value in values:
        if value in (None, ''):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def get_account_payload(row: models.JudianAccount) -> dict[str, Any]:

    return dict_like(row.payload)


def normalize_login_email(value: Any) -> str:
    return str(value or '').strip().lower()


def find_existing_account_by_login_email(db: Session, user: dict[str, Any], login_email: str) -> models.JudianAccount | None:
    normalized_email = normalize_login_email(login_email)
    if not normalized_email:
        return None

    rows = owner_scoped_account_query(db, user).order_by(models.JudianAccount.updated_at.desc(), models.JudianAccount.id.desc()).all()
    for row in rows:
        if normalize_login_email(resolve_account_login_email(row)) == normalized_email:
            return row
    return None


def resolve_account_login_email(row: models.JudianAccount) -> str:

    payload = get_account_payload(row)
    remote_user_info = dict_like(payload.get('remote_user_info'))
    remote_login = dict_like(payload.get('remoteLogin'))
    remote_login_decoded = dict_like(payload.get('remoteLoginDecoded'))
    legacy_remote_login = dict_like(payload.get('remote_login_payload'))
    return pick_text(
        row.login_email,
        payload.get('login_account'),
        payload.get('email'),
        remote_user_info.get('account'),
        extract_remote_value(remote_login_decoded, 'account', 'email', 'loginEmail'),
        extract_remote_value(remote_login, 'account', 'email', 'loginEmail'),
        extract_remote_value(legacy_remote_login, 'account', 'email', 'loginEmail'),
    )


def resolve_account_login_password(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    return pick_text(row.login_password, payload.get('login_password'))


def resolve_account_display_name(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    remote_user_info = dict_like(payload.get('remote_user_info'))
    return pick_text(row.display_name, remote_user_info.get('nickName'), remote_user_info.get('nickname'))


def resolve_account_session_token(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    remote_login = dict_like(payload.get('remoteLogin'))
    remote_login_decoded = dict_like(payload.get('remoteLoginDecoded'))
    legacy_remote_login = dict_like(payload.get('remote_login_payload'))
    return pick_text(
        row.session_token,
        payload.get('remote_token'),
        extract_remote_value(remote_login_decoded, 'accessToken', 'token'),
        extract_remote_value(remote_login, 'accessToken', 'token'),
        extract_remote_value(legacy_remote_login, 'accessToken', 'token'),
    )


def resolve_account_user_sig(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    remote_login = dict_like(payload.get('remoteLogin'))
    remote_login_decoded = dict_like(payload.get('remoteLoginDecoded'))
    legacy_remote_login = dict_like(payload.get('remote_login_payload'))
    return pick_text(
        row.user_sig,
        payload.get('remote_user_sig'),
        extract_remote_value(remote_login_decoded, 'userSig', 'user_sig', 'imUserSig', 'imUserSign'),
        extract_remote_value(remote_login, 'userSig', 'user_sig', 'imUserSig', 'imUserSign'),
        extract_remote_value(legacy_remote_login, 'userSig', 'user_sig', 'imUserSig', 'imUserSign'),
    )


def resolve_account_last_login_at(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    remote_login = dict_like(payload.get('remoteLogin'))
    remote_login_decoded = dict_like(payload.get('remoteLoginDecoded'))
    legacy_remote_login = dict_like(payload.get('remote_login_payload'))
    return pick_text(
        row.last_login_at,
        payload.get('last_login_at'),
        extract_remote_value(remote_login_decoded, 'accessTime', 'lastLoginAt', 'last_login_at'),
        extract_remote_value(remote_login, 'accessTime', 'lastLoginAt', 'last_login_at'),
        extract_remote_value(legacy_remote_login, 'accessTime', 'lastLoginAt', 'last_login_at'),
    )


def resolve_account_diamond_quantity_updated_at(row: models.JudianAccount) -> str:
    payload = get_account_payload(row)
    return pick_text(
        row.diamond_quantity_updated_at,
        payload.get('diamond_quantity_updated_at'),
        payload.get('last_login_at'),
    )


def resolve_account_diamond_quantity(row: models.JudianAccount) -> int:
    payload = get_account_payload(row)
    remote_fund = dict_like(payload.get('remoteFund'))
    legacy_remote_fund = dict_like(payload.get('remote_fund_payload'))
    row_quantity = pick_int(row.diamond_quantity)
    payload_quantity = pick_int(
        payload.get('diamond_quantity'),
        extract_remote_value(remote_fund, 'quantity'),
        extract_remote_value(legacy_remote_fund, 'quantity'),
    )
    if row_quantity > 0:
        return row_quantity
    if payload_quantity > 0:
        return payload_quantity
    return row_quantity


def serialize_account(row: models.JudianAccount) -> dict[str, Any]:
    return {
        'id': row.id,
        'accountId': pick_text(row.account_id),
        'displayName': resolve_account_display_name(row),
        'loginEmail': resolve_account_login_email(row),
        'remark': row.remark or '',
        'enabled': bool(row.enabled),
        'status': row.status or 'pending',
        'diamondQuantity': resolve_account_diamond_quantity(row),
        'diamondQuantityUpdatedAt': resolve_account_diamond_quantity_updated_at(row),
        'sessionToken': resolve_account_session_token(row),
        'userSig': resolve_account_user_sig(row),
        'lastLoginAt': resolve_account_last_login_at(row),
        'createdAt': row.created_at or '',
        'updatedAt': row.updated_at or '',
    }


def serialize_public_account(row: models.JudianAccount) -> dict[str, Any]:
    return {
        'accountId': pick_text(row.account_id),
        'displayName': resolve_account_display_name(row),
        'status': row.status or 'pending',
        'enabled': bool(row.enabled),
        'diamondQuantity': resolve_account_diamond_quantity(row),
        'diamondQuantityUpdatedAt': resolve_account_diamond_quantity_updated_at(row),
        'lastLoginAt': resolve_account_last_login_at(row),
        'remark': row.remark or '',
    }



def generate_cdkey_code(db: Session) -> str:
    while True:
        code = ''.join(random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(16))
        if db.query(models.JudianCdKey).filter_by(code=code).first() is None:
            return code


def serialize_cdkey(row: models.JudianCdKey) -> dict[str, Any]:
    return {
        'id': row.id,
        'code': row.code,
        'ownerUsername': row.owner_username or '',
        'accountId': row.account_id or '',
        'cardId': row.card_id,
        'duration': int(row.duration or 0),
        'status': row.status or 'unused',
        'maxUses': int(row.max_uses or 0),
        'useCount': int(row.use_count or 0),
        'expiresAt': row.expires_at or '',
        'latestSessionId': row.latest_session_id or '',
        'latestOrderId': row.latest_order_id or '',
        'remark': row.remark or '',
        'createdAt': row.created_at or '',
        'updatedAt': row.updated_at or '',
    }


def claim_cdkeys_for_delivery(
    request: Request,
    db: Session,
    user: dict[str, Any],
    *,
    account_id: str = '',
    card_id: int | None = None,
    count: int = 1,
    mark_status: str = 'active',
) -> dict[str, Any]:
    ensure_claim_api_authorized(request)

    normalized_account_id = str(account_id or '').strip()
    normalized_mark_status = str(mark_status or 'active').strip().lower() or 'active'
    if normalized_mark_status not in {'unused', 'active', 'expired', 'void'}:
        raise HTTPException(status_code=400, detail='领取后状态不合法')

    target_count = max(1, min(50, int(count or 1)))
    query = owner_scoped_cdkey_query(db, user).filter(models.JudianCdKey.status == 'unused')
    if normalized_account_id:
        query = query.filter(models.JudianCdKey.account_id == normalized_account_id)
    if card_id is not None:
        query = query.filter(models.JudianCdKey.card_id == int(card_id))

    rows = query.order_by(models.JudianCdKey.created_at.asc(), models.JudianCdKey.id.asc()).limit(target_count).all()
    if not rows:
        raise HTTPException(status_code=404, detail='暂无可领取的聚点卡密')

    now = now_text()
    client_ip = resolve_client_ip(request)
    for row in rows:
        payload = dict_like(row.payload)
        row.status = normalized_mark_status
        row.updated_at = now
        row.payload = {
            **payload,
            'claimCount': pick_int(payload.get('claimCount')) + 1,
            'lastClaimAt': now,
            'lastClaimIp': client_ip,
            'lastClaimSource': 'api',
        }

    db.commit()
    for row in rows:
        db.refresh(row)

    codes = [row.code for row in rows if str(row.code or '').strip()]
    delivery_content = '\n'.join(codes)
    first_item = serialize_cdkey(rows[0])
    return {
        'success': True,
        'message': f'成功领取 {len(rows)} 张聚点卡密',
        'total': len(rows),
        'count': len(rows),
        'code': codes[0] if codes else '',
        'codes': codes,
        'deliveryContent': delivery_content,
        'content': delivery_content,
        'item': first_item,
        'items': [serialize_cdkey(row) for row in rows],
    }


def build_dashboard_activities(accounts: list[models.JudianAccount], cdkeys: list[models.JudianCdKey]) -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []

    for row in accounts:
        display_name = resolve_account_display_name(row) or pick_text(row.account_id, f'账号#{row.id}')
        last_login_at = resolve_account_last_login_at(row)
        updated_at = pick_text(row.updated_at, last_login_at, row.created_at)
        if last_login_at:
            activities.append({
                'type': 'success',
                'title': '聚点账号登录',
                'description': f'{display_name} 已同步会话、UserSig 与钻石余额',
                'createdAt': last_login_at,
            })
        elif updated_at:
            status = str(row.status or 'pending')
            if status == 'disabled':
                activity_type = 'warning'
                activity_title = '聚点账号停用'
                activity_desc = f'{display_name} 当前已停用'
            else:
                activity_type = 'info'
                activity_title = '聚点账号更新'
                activity_desc = f'{display_name} 的账号资料已更新'
            activities.append({
                'type': activity_type,
                'title': activity_title,
                'description': activity_desc,
                'createdAt': updated_at,
            })

    for row in cdkeys:
        created_at = pick_text(row.updated_at, row.created_at)
        if not created_at:
            continue
        status = str(row.status or 'unused')
        code = row.code or f'卡密#{row.id}'
        account_id = row.account_id or '未绑定账号'
        if status == 'void':
            activity_type = 'warning'
            activity_title = '卡密已作废'
            activity_desc = f'{code} 已从账号 {account_id} 的库存中作废'
        elif status == 'expired':
            activity_type = 'error'
            activity_title = '卡密已过期'
            activity_desc = f'{code} 已过期，请及时清理'
        elif status == 'active':
            activity_type = 'info'
            activity_title = '卡密已领取'
            activity_desc = f'{code} 当前已进入使用链路'
        else:
            activity_type = 'success'
            activity_title = '生成卡密'
            activity_desc = f'{code} 已绑定到账号 {account_id}'
        activities.append({
            'type': activity_type,
            'title': activity_title,
            'description': activity_desc,
            'createdAt': created_at,
        })

    activities.sort(key=lambda item: str(item.get('createdAt') or ''), reverse=True)
    return activities[:20]


def apply_remote_login_result(

    db: Session,
    row: models.JudianAccount | None,
    *,
    owner_username: str,
    login_email: str,
    login_password: str,
    display_name: str,
    remark: str,
) -> models.JudianAccount:
    login_result = remote_login(login_email, login_password)
    token = str(login_result.get('token') or '').strip()
    user_info_payload: dict[str, Any] = {}
    fund_payload: dict[str, Any] = {}
    diamond_quantity = pick_int(getattr(row, 'diamond_quantity', 0) if row is not None else 0)

    if token:
        def load_user_info() -> dict[str, Any]:
            return remote_get_user_info(
                build_remote_runtime_session(token),
                timeout=REMOTE_SUPPLEMENTAL_TIMEOUT_SECONDS,
            )

        def load_fund() -> tuple[int, dict[str, Any]]:
            return remote_get_fund(
                build_remote_runtime_session(token),
                timeout=REMOTE_SUPPLEMENTAL_TIMEOUT_SECONDS,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            user_info_future = executor.submit(load_user_info)
            fund_future = executor.submit(load_fund)
            try:
                user_info_payload = user_info_future.result()
            except Exception:
                user_info_payload = {}
            try:
                diamond_quantity, fund_payload = fund_future.result()
            except Exception:
                fund_payload = {}

    now = now_text()
    login_payload = login_result['login_payload']
    remote_user_info = dict_like(user_info_payload.get('data'))


    existing_payload: dict[str, Any] = {}
    existing_user_sig = ''
    existing_display_name = ''
    if row is not None:
        existing_payload = dict(get_account_payload(row))
        existing_user_sig = resolve_account_user_sig(row)
        existing_display_name = resolve_account_display_name(row)

    if row is None:
        row = models.JudianAccount(
            owner_username=owner_username,
            account_id='',
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()

    if not str(row.account_id or '').strip():
        row.account_id = extract_remote_value(
            remote_user_info,
            'id',
            'userId',
            'uid',
            'accountId',
            'memberId',
        ) or extract_remote_value(login_payload, 'accountId', 'userId', 'uid', 'id', 'memberId') or next_local_account_id(db)

    next_user_sig = pick_text(
        extract_remote_value(login_payload, 'userSig', 'user_sig', 'imUserSig', 'imUserSign'),
        extract_remote_value(remote_user_info, 'userSig', 'user_sig', 'imUserSig', 'imUserSign'),
        existing_user_sig,
    )

    row.owner_username = owner_username
    row.display_name = display_name or extract_remote_value(remote_user_info, 'nickName', 'nickname') or existing_display_name or row.display_name or login_email.split('@')[0] or '聚点账号'
    row.login_email = login_email
    row.login_password = login_password
    row.remark = remark
    row.session_token = login_result['token']
    row.user_sig = next_user_sig
    row.status = 'disabled' if row.enabled is False else 'active'
    row.diamond_quantity = diamond_quantity
    row.diamond_quantity_updated_at = now
    row.last_login_at = now
    row.updated_at = now

    merged_payload = dict(existing_payload)
    merged_payload.update({
        'login_account': login_email,
        'email': login_email,
        'login_password': login_password,
        'remoteLogin': login_result['raw_payload'],
        'remoteLoginDecoded': login_payload,
        'remoteLoginRequestHeaders': login_result.get('request_headers') or {},
        'remote_session_headers': login_result.get('request_headers') or {},
        'remote_user_info': remote_user_info,
        'remote_token': login_result['token'],
        'last_login_at': now,
        'remoteFund': fund_payload,
        'remote_fund_payload': fund_payload,
        'diamond_quantity': diamond_quantity,
        'diamond_quantity_updated_at': now,
    })
    if next_user_sig:
        merged_payload['remote_user_sig'] = next_user_sig
    row.payload = merged_payload

    db.commit()
    db.refresh(row)
    return row









def get_public_cdkey_or_404(db: Session, code: str) -> models.JudianCdKey:
    ensure_judian_schema(db)
    code = str(code or '').strip()
    if not code:
        raise HTTPException(status_code=400, detail='缺少卡密参数 ?code=xxx')
    row = db.query(models.JudianCdKey).filter_by(code=code).first()
    if row is None:
        raise HTTPException(status_code=404, detail='聚点卡密不存在')
    return row



def get_public_account_or_404(db: Session, row: models.JudianCdKey) -> models.JudianAccount:
    account = db.query(models.JudianAccount).filter_by(account_id=row.account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail='绑定的聚点账号不存在')
    return account


def ensure_public_cdkey_ready(db: Session, row: models.JudianCdKey) -> models.JudianAccount:
    if row.status == 'void':
        raise HTTPException(status_code=410, detail='聚点卡密已作废')

    account = get_public_account_or_404(db, row)
    if account.enabled is False:
        raise HTTPException(status_code=503, detail='关联聚点账号不可用')

    now = int(time.time())

    if row.expires_at is None:
        row.expires_at = now + int(row.duration or 0) * 86400
        if row.status == 'unused':
            row.status = 'active'
        row.updated_at = now_text()

    if row.expires_at and now > int(row.expires_at):
        row.status = 'expired'
        row.updated_at = now_text()
        db.commit()
        raise HTTPException(status_code=410, detail='聚点卡密已过期')

    if int(row.max_uses or 0) > 0 and int(row.use_count or 0) >= int(row.max_uses or 0):
        row.status = 'void'
        row.updated_at = now_text()
        db.commit()
        raise HTTPException(status_code=410, detail=f'卡密额度已用尽（{row.max_uses} 钻）')

    db.commit()
    db.refresh(row)
    return account



def serialize_public_order(row: models.JudianOrder | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict_like(row.raw_payload)
    remote_data = dict_like(payload.get('data'))
    return {
        'orderId': row.order_id or '',
        'tradeNo': pick_text(remote_data.get('tradeNo'), row.order_id),
        'orderNo': pick_text(remote_data.get('orderNo')),
        'appName': pick_text(remote_data.get('appName'), remote_data.get('title'), row.item_title),
        'createTime': pick_text(remote_data.get('createTime'), row.created_at),
        'status': row.order_status or 'pending',
        'diamond': pick_int(remote_data.get('diamond'), row.amount),
        'remark': pick_text(remote_data.get('remark'), row.delivery_content_preview),
        'timeOut': pick_int(remote_data.get('timeOut'), remote_data.get('timeout')),
        'itemTitle': pick_text(remote_data.get('title'), row.item_title),
        'raw': payload,
    }



def serialize_public_cdkey_summary(row: models.JudianCdKey) -> dict[str, Any]:
    return {
        'code': row.code,
        'status': row.status or 'active',
        'duration': int(row.duration or 0),
        'expiresAt': int(row.expires_at or 0) if row.expires_at else None,
        'useCount': int(row.use_count or 0),
        'maxUses': int(row.max_uses or 0),
        'remark': row.remark or '',
    }



def serialize_public_session(row: models.JudianScanSession, order: models.JudianOrder | None = None) -> dict[str, Any]:

    return {
        'sessionId': row.session_id,
        'status': row.status or 'pending',
        'message': row.message or '',
        'orderId': row.order_id or '',
        'qrContent': row.qr_content or '',
        'mobileLoginLink': row.mobile_login_link or '',
        'unlockUrl': row.unlock_url or '',
        'expiresAt': int(row.expires_at) if row.expires_at else None,
        'confirmedAt': int(row.confirmed_at) if row.confirmed_at else None,
        'resultPayload': dict_like(row.result_payload),
        'order': serialize_public_order(order),
    }


def serialize_public_batch_task(row: models.JudianBatchPurchaseTask | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict_like(row.payload)
    result_payload = dict_like(row.result_payload)
    items = result_payload.get('items')
    if not isinstance(items, list):
        items = []
    return {
        'batchId': row.batch_id or '',
        'sessionId': row.session_id or '',
        'status': row.status or 'pending',
        'message': row.message or '',
        'totalCount': int(row.total_count or 0),
        'processedCount': int(row.processed_count or 0),
        'successCount': int(row.success_count or 0),
        'failedCount': int(row.failed_count or 0),
        'pendingCount': int(row.pending_count or 0),
        'totalConsumedDiamond': int(row.total_consumed_diamond or 0),
        'currentIndex': int(row.current_index or 0),
        'currentTradeNo': row.current_trade_no or '',
        'createdAt': row.created_at or '',
        'updatedAt': row.updated_at or '',
        'items': items,
        'payload': payload,
    }


def get_latest_public_batch_task(
    db: Session,
    session_row: models.JudianScanSession,
) -> models.JudianBatchPurchaseTask | None:
    ensure_judian_schema(db)
    target_session_id = str(session_row.session_id or '').strip()
    if not target_session_id:
        return None
    return (
        db.query(models.JudianBatchPurchaseTask)
        .filter_by(session_id=target_session_id)
        .order_by(models.JudianBatchPurchaseTask.id.desc())
        .first()
    )


def build_public_unlock_response(
    db: Session,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    session_row: models.JudianScanSession,
    order_row: models.JudianOrder | None = None,
    *,
    batch_task_row: models.JudianBatchPurchaseTask | None = None,
) -> dict[str, Any]:
    if order_row is None and session_row.order_id:
        order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first()
    if batch_task_row is None:
        batch_task_row = get_latest_public_batch_task(db, session_row)
    return {
        'success': True,
        'code': cdkey_row.code,
        'status': cdkey_row.status or 'active',
        'duration': int(cdkey_row.duration or 0),
        'expiresAt': int(cdkey_row.expires_at or 0) if cdkey_row.expires_at else None,
        'useCount': int(cdkey_row.use_count or 0),
        'maxUses': int(cdkey_row.max_uses or 0),
        'remark': cdkey_row.remark or '',
        'account': serialize_public_account(account),
        'session': serialize_public_session(session_row, order_row),
        'batchTask': serialize_public_batch_task(batch_task_row),
    }




def has_public_unlock_success_result(value: Any) -> bool:
    payload = dict_like(value)
    payload = dict_like(value)
    payload = dict_like(value)
    if not payload:
        return False

    text = str(payload.get('rendered_message') or payload.get('renderedMessage') or '').strip()
    if text:
        return True

    try:
        consumed = int(payload.get('consumedDiamond') or -1)
        after = int(payload.get('afterDiamond') or -1)
        before = int(payload.get('beforeDiamond') or -1)
        if consumed >= 0:
            return True
        if after >= 0 and before >= 0:
            return True
    except (TypeError, ValueError):
        pass

    pay_payload = dict_like(payload.get('payPayload'))
    fund_payload = dict_like(payload.get('fundPayload'))
    if pay_payload.get('success') is True or pay_payload.get('settledByPolling') is True:
        return True
    if fund_payload:
        return True

    return False


def append_unique_text(items: list[str], *values: Any) -> None:
    for value in values:
        text = str(value or '').strip()
        if text and text not in items:
            items.append(text)


def extract_trade_tokens_from_text(text: Any) -> list[str]:
    raw_text = str(text or '').strip()
    candidates: list[str] = []
    if not raw_text:
        return candidates

    if not raw_text.startswith('http') and '?' not in raw_text:
        append_unique_text(candidates, raw_text)

    try:
        parsed = urlparse(raw_text)
        params = parse_qs(parsed.query)
    except ValueError:
        parsed = None
        params = {}

    for key in ('tradeNo', 'jdTokenNo', 'orderNo', 'trade_no', 'no'):
        values = params.get(key) if params else None
        if values:
            append_unique_text(candidates, *values)

    if parsed:
        path_part = str(parsed.path or '').rstrip('/').split('/')[-1].strip()
        if path_part and len(path_part) > 5:
            append_unique_text(candidates, path_part)

    patterns = [
        r'Pay\("([^"]+)"\)',
        r"Pay\('([^']+)'\)",
        r'tradeNo["\']?\s*[:=]\s*["\']?([^"\'&\s]+)',
        r'jdTokenNo["\']?\s*[:=]\s*["\']?([^"\'&\s]+)',
        r'orderNo["\']?\s*[:=]\s*["\']?([^"\'&\s]+)',
        r'(AI\d{10,})',
        r'(?<!\d)(\d{14,})(?!\d)',
    ]
    for pattern in patterns:
        for matched in re.finditer(pattern, raw_text):
            append_unique_text(candidates, matched.group(1))

    return candidates


def extract_public_trade_candidate(qr_text: str, trade_no: str = '', order_no: str = '') -> tuple[str, str, str]:
    raw_text = str(qr_text or '').strip()
    scan_url = raw_text if raw_text.startswith('http') else ''
    candidates: list[str] = []
    append_unique_text(candidates, trade_no, order_no)
    append_unique_text(candidates, *extract_trade_tokens_from_text(raw_text))

    if not candidates:
        raise HTTPException(status_code=400, detail='二维码中未识别到订单标识，请确认扫到的是聚点购买二维码')

    trade_candidate = candidates[0]
    order_candidate = str(order_no or '').strip() or (candidates[1] if len(candidates) > 1 else trade_candidate)
    return trade_candidate, order_candidate, scan_url



def extract_pay_trade_no(text: str) -> str:
    raw_text = str(text or '')
    patterns = [
        r'Pay\("([^"]+)"\)',
        r"Pay\('([^']+)'\)",
        r'tradeNo["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'orderNo["\']?\s*[:=]\s*["\'](AI[^"\']+)["\']',
        r'(AI\d{10,})',
    ]
    for pattern in patterns:
        matched = re.search(pattern, raw_text)
        if matched:
            return str(matched.group(1)).strip()
    return ''




def build_remote_runtime_session(token: str) -> requests.Session:
    token = str(token or '').strip()
    if not token:
        raise HTTPException(status_code=503, detail='聚点账号当前没有可用会话，请先在后台重新登录账号')
    session = requests.Session()
    session.headers.update(build_headers())
    session.headers.update({'Authorization': f'Bearer {token}'})
    return session



def remote_scan_qr_notify(session: requests.Session, order_no: str, scan_url: str = '') -> dict[str, Any]:
    target_order_no = str(order_no or '').strip()
    target_url = str(scan_url or '').strip() if str(scan_url or '').strip().startswith('http') else ''
    if not target_url:
        if not target_order_no:
            return {'status': 'warn', 'message': '缺少扫码通知所需订单号，已跳过通知步骤'}
        target_url = f'{ORDER_SCAN_URL}/{target_order_no}?jdTokenNo={target_order_no}'

    try:
        response = session.get(
            target_url,
            headers={
                'User-Agent': 'Judian Android',
                'X-Requested-With': 'com.fywl.fygjx',
            },
            timeout=5,
        )
    except requests.RequestException as exc:
        return {'status': 'error', 'message': f'扫码通知请求失败：{exc}'}

    body = str(response.text or '').strip()
    if response.status_code != 200:
        return {'status': 'error', 'message': f'扫码通知失败，HTTP {response.status_code}', 'statusCode': response.status_code}

    if body.startswith('<'):
        real_trade_no = extract_pay_trade_no(body)
        result = {'status': 'ok' if real_trade_no else 'warn', 'message': '扫码页返回跳转脚本' if real_trade_no else '扫码页返回 HTML，但未解析出真实 tradeNo'}
        if real_trade_no:
            result['tradeNo'] = real_trade_no
        result['rawText'] = body[:300]
        return result

    try:
        payload = response.json()
    except ValueError:
        real_trade_no = extract_pay_trade_no(body)
        result = {
            'status': 'error' if any(word in body for word in ('错误', '失败', '不存在')) else 'ok',
            'message': body[:100] or '扫码通知返回了非 JSON 文本',
            'rawText': body[:300],
        }
        if real_trade_no:
            result['tradeNo'] = real_trade_no
        return result

    real_trade_no = extract_pay_trade_no(json.dumps(payload, ensure_ascii=False))
    if isinstance(payload, dict) and real_trade_no and 'tradeNo' not in payload:
        payload['tradeNo'] = real_trade_no
    return payload if isinstance(payload, dict) else {'status': 'ok', 'message': '扫码通知成功'}



def get_public_remote_session(db: Session, account: models.JudianAccount, *, force_relogin: bool = False) -> tuple[models.JudianAccount, requests.Session]:

    if not force_relogin:
        token = resolve_account_session_token(account)
        if token:
            return account, build_remote_runtime_session(token)

    login_email = resolve_account_login_email(account)
    login_password = resolve_account_login_password(account)
    if not login_email or not login_password:
        raise HTTPException(status_code=503, detail='当前聚点账号未保存可用账密，无法自动完成扫码解锁')

    try:
        saved = apply_remote_login_result(
            db,
            account,
            owner_username=str(account.owner_username or '').strip(),
            login_email=login_email,
            login_password=login_password,
            display_name=str(account.display_name or '').strip(),
            remark=str(account.remark or '').strip(),
        )
    except JudianRemoteError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return saved, build_remote_runtime_session(resolve_account_session_token(saved))








def remote_get_order_info(session: requests.Session, trade_no: str) -> dict[str, Any]:
    target = str(trade_no or '').strip()
    if not target:
        raise JudianRemoteError('缺少可用的 tradeNo，无法查询聚点订单')
    aes_key = uuid.uuid4().hex[:16]
    try:
        response = session.get(
            ORDER_INFO_URL,
            params={'tradeNo': target},
            headers={'Secret': get_secret(aes_key)},
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点订单查询失败：{exc}') from exc
    payload = ensure_remote_json(response)
    message = pick_text(
        payload.get('msg'),
        payload.get('message'),
        extract_remote_value(payload, 'msg', 'message'),
    )
    if should_refresh_public_remote_session(message):
        raise JudianRemoteError(message or '聚点远端登录已失效')
    return payload



def is_public_order_payload_success(payload: Any) -> bool:
    payload_dict = dict_like(payload)
    order_data = dict_like(payload_dict.get('data'))
    if not order_data:
        return False

    message = pick_text(
        payload_dict.get('msg'),
        payload_dict.get('message'),
        extract_remote_value(payload_dict, 'msg', 'message'),
    )
    code_text = str(payload_dict.get('code') or payload_dict.get('status') or '').strip().lower()
    if payload_dict.get('success') is False:
        return False
    if code_text in {'300', '400', '401', '402', '403', '404', '500', 'error', 'fail', 'failed'}:
        return False
    if any(keyword in message for keyword in ('失败', '错误', '不存在', '无效', '失效', '异地登录', '未登录')):
        return False
    return True


def should_refresh_public_remote_session(message: str) -> bool:
    text = str(message or '').strip()
    if not text:
        return False
    return any(keyword in text for keyword in (
        '异地登录',
        '未登录',
        '重新登录',
        '登录失效',
        '登录已失效',
        '登录已过期',
        'token 已失效',
        'token失效',
        '会话失效',
        '正在登录',
        '请登录',
    ))



def build_public_remote_token_expired_detail() -> str:
    return '聚点远端登录已失效，系统自动重登后仍不可用，请联系管理员在后台检查账号状态'



def build_public_runtime_session_from_saved_token(account: models.JudianAccount) -> requests.Session:
    token = resolve_account_session_token(account)
    if not token:
        raise HTTPException(status_code=503, detail='当前聚点账号没有已保存的远端 token，请联系管理员先在后台重新登录账号')
    return build_remote_runtime_session(token)



def get_http_exception_detail(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return pick_text(detail.get('detail'), detail.get('message'), detail.get('msg')) or json.dumps(detail, ensure_ascii=False)
    return str(detail or '').strip()



def run_public_remote_action_with_relogin(
    db: Session,
    account: models.JudianAccount,
    action: Callable[[requests.Session], Any],
) -> tuple[models.JudianAccount, requests.Session, Any]:
    current_account = account
    force_relogin = False

    while True:
        current_account, remote_session = get_public_remote_session(db, current_account, force_relogin=force_relogin)
        try:
            result = action(remote_session)
            return current_account, remote_session, result
        except JudianRemoteError as exc:
            if not force_relogin and should_refresh_public_remote_session(str(exc)):
                force_relogin = True
                continue
            raise
        except HTTPException as exc:
            if not force_relogin and should_refresh_public_remote_session(get_http_exception_detail(exc)):
                force_relogin = True
                continue
            raise



def raise_public_remote_error(detail: str, *, default_status_code: int = 502) -> None:
    message = str(detail or '').strip()
    if should_refresh_public_remote_session(message):
        raise HTTPException(status_code=503, detail=build_public_remote_token_expired_detail())
    lowered = message.lower()
    if any(keyword in message for keyword in ('不足', '余额', '失效', '不存在', '无效', '已支付')) or any(keyword in lowered for keyword in ('insufficient',)):
        raise HTTPException(status_code=400, detail=message or '聚点订单状态异常')
    raise HTTPException(status_code=default_status_code, detail=message or '聚点远端请求失败，请稍后重试')




def ensure_public_order_payload_or_raise(order_payload: dict[str, Any], *, default_detail: str = '当前订单已失效，请重新扫码') -> dict[str, Any]:
    if is_public_order_payload_success(order_payload):
        return order_payload
    detail = pick_text(
        order_payload.get('msg'),
        order_payload.get('message'),
        extract_remote_value(order_payload, 'msg', 'message'),
    ) or default_detail
    raise_public_remote_error(detail, default_status_code=400)



def build_public_order_query_candidates(qr_text: str, trade_candidate: str, order_candidate: str, scan_result: Any = None) -> list[str]:

    candidates: list[str] = []
    append_unique_text(candidates, trade_candidate, order_candidate)
    append_unique_text(candidates, *extract_trade_tokens_from_text(qr_text))

    result_payload = dict_like(scan_result)
    for key in ('tradeNo', 'jdTokenNo', 'orderNo', 'no'):
        append_unique_text(candidates, result_payload.get(key))
    append_unique_text(candidates, *extract_trade_tokens_from_text(result_payload.get('rawText')))
    append_unique_text(candidates, *extract_trade_tokens_from_text(result_payload.get('message')))
    if result_payload:
        append_unique_text(candidates, *extract_trade_tokens_from_text(json.dumps(result_payload, ensure_ascii=False)))
    return candidates


def resolve_public_order_payload(
    session: requests.Session,
    *,
    qr_text: str,
    trade_candidate: str,
    order_candidate: str,
    scan_result: Any = None,
    max_attempts_per_candidate: int = 2,
    sleep_seconds: float = 0.6,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    candidates = build_public_order_query_candidates(qr_text, trade_candidate, order_candidate, scan_result)
    if not candidates:
        raise HTTPException(status_code=400, detail='二维码中未识别到订单标识，请确认扫到的是聚点购买二维码')

    trace: list[dict[str, Any]] = []
    had_invalid_payload = False
    last_invalid_message = ''
    last_remote_error = ''

    for candidate in candidates:
        for attempt_index in range(max_attempts_per_candidate):
            try:
                payload = remote_get_order_info(session, candidate)
            except JudianRemoteError as exc:
                last_remote_error = str(exc)
                trace.append({
                    'candidate': candidate,
                    'attempt': attempt_index + 1,
                    'ok': False,
                    'error': last_remote_error,
                })
            else:
                message = pick_text(
                    payload.get('msg'),
                    payload.get('message'),
                    extract_remote_value(payload, 'msg', 'message'),
                )
                order_data = dict_like(payload.get('data'))
                is_success = is_public_order_payload_success(payload)
                trace.append({
                    'candidate': candidate,
                    'attempt': attempt_index + 1,
                    'ok': is_success,
                    'hasData': bool(order_data),
                    'message': message[:120],
                })
                if is_success:
                    return candidate, payload, trace
                had_invalid_payload = True
                if message:
                    last_invalid_message = message

            if attempt_index < max_attempts_per_candidate - 1:
                time.sleep(sleep_seconds)

    if had_invalid_payload:
        raise_public_remote_error(last_invalid_message or '未查询到有效订单，请确认二维码是否已过期或扫码链路是否已失效', default_status_code=400)
    raise_public_remote_error(last_remote_error or '聚点订单查询失败，请稍后重试', default_status_code=502)




def remote_pay_order(session: requests.Session, trade_no: str) -> dict[str, Any]:
    target = str(trade_no or '').strip()
    if not target:
        raise JudianRemoteError('缺少可用的 tradeNo，无法发起支付')
    aes_key = uuid.uuid4().hex[:16]
    try:
        response = session.post(
            ORDER_PAY_URL,
            json={'tradeNo': target},
            headers={
                'Secret': get_secret(aes_key),
                'Content-Type': 'application/json; charset=utf-8',
            },
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JudianRemoteError(f'聚点支付请求失败：{exc}') from exc
    payload = ensure_remote_json(response)
    message = pick_text(payload.get('msg'), payload.get('message'), extract_remote_value(payload, 'msg', 'message'))
    code_text = str(payload.get('code') or payload.get('status') or '').strip().lower()
    if payload.get('success') is False or code_text in {'400', '401', '402', '403', '500', 'error', 'fail', 'failed'} or '失败' in message or '不足' in message:
        raise JudianRemoteError(message or '聚点支付失败')
    return payload



def is_retryable_pay_message(message: str) -> bool:
    text = str(message or '').strip()
    if not text:
        return False
    return any(keyword in text for keyword in ('正在登录', '订单已支付', '处理中', '请稍后'))



def wait_public_payment_settle(
    session: requests.Session,
    trade_no: str,
    *,
    before_diamond: int,
    max_attempts: int = 8,
    sleep_seconds: float = 1.0,
) -> tuple[bool, int, dict[str, Any], dict[str, Any]]:
    after_diamond = int(before_diamond)
    last_order_payload: dict[str, Any] = {}
    last_fund_payload: dict[str, Any] = {}
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(sleep_seconds)
        try:
            after_diamond, last_fund_payload = remote_get_fund(session)
        except JudianRemoteError:
            pass
        try:
            last_order_payload = remote_get_order_info(session, trade_no)
        except JudianRemoteError:
            pass
        if int(after_diamond) < int(before_diamond):
            return True, int(after_diamond), last_order_payload, last_fund_payload
    return False, int(after_diamond), last_order_payload, last_fund_payload



def execute_public_unlock_payment(
    db: Session,
    session_row: models.JudianScanSession,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    order_row: models.JudianOrder | None = None,
    *,
    remote_session: requests.Session | None = None,
) -> dict[str, Any]:
    if not session_row.order_id:
        raise HTTPException(status_code=400, detail='当前会话还没有有效订单，无法完成解锁')

    if order_row is None:
        order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first()
    if order_row is None:
        raise HTTPException(status_code=400, detail='当前订单尚未同步，请重新扫码后再尝试支付')

    if str(session_row.status or '') == 'completed' or str(order_row.order_status or '') == 'completed' or has_public_unlock_success_result(session_row.result_payload):
        result_payload = dict_like(session_row.result_payload)
        rendered_message = pick_text(result_payload.get('rendered_message'), '该订单已完成支付，VIP 已解锁')
        after_diamond = pick_int(result_payload.get('afterDiamond'), result_payload.get('diamondQuantity'), account.diamond_quantity)
        return {
            'success': True,
            **serialize_public_cdkey_summary(cdkey_row),
            'message': rendered_message,
            'session': serialize_public_session(session_row, order_row),
            'order': serialize_public_order(order_row),
            'account': serialize_public_account(account),
            'renderedMessage': rendered_message,
            'beforeDiamond': pick_int(result_payload.get('beforeDiamond')),
            'afterDiamond': after_diamond,
            'consumedDiamond': pick_int(result_payload.get('consumedDiamond')),
        }


    runtime_account = account
    runtime_session = remote_session
    force_relogin = False

    # 在发起支付前校验卡密剩余额度是否足够本次订单
    try:
        order_amount = pick_int(order_row.amount)
    except Exception:
        order_amount = 0
    try:
        ensure_public_cdkey_quota_sufficient(cdkey_row, order_amount)
    except HTTPException as exc:
        session_row.status = 'confirmed'
        session_row.message = str(exc.detail or '卡密额度不足')
        session_row.updated_at = now_text()
        order_row.order_status = 'confirmed'
        order_row.updated_at = now_text()
        db.commit()
        db.refresh(session_row)
        db.refresh(order_row)
        raise

    while True:
        if runtime_session is None:
            runtime_account, runtime_session = get_public_remote_session(db, runtime_account, force_relogin=force_relogin)

        before_diamond = resolve_account_diamond_quantity(runtime_account)
        before_fund_payload: dict[str, Any] = {}

        try:
            before_diamond, before_fund_payload = remote_get_fund(runtime_session)
            pay_payload = remote_pay_order(runtime_session, session_row.order_id)
            after_diamond, after_fund_payload = remote_get_fund(runtime_session)
            account = runtime_account
            break
        except JudianRemoteError as exc:
            detail = str(exc)
            if should_refresh_public_remote_session(detail) and not force_relogin:
                force_relogin = True
                runtime_session = None
                continue
            if is_retryable_pay_message(detail):
                settled, after_diamond, settle_order_payload, after_fund_payload = wait_public_payment_settle(
                    runtime_session,
                    session_row.order_id,
                    before_diamond=before_diamond,
                )
                if settled:
                    pay_payload = {
                        'success': True,
                        'msg': detail,
                        'settledByPolling': True,
                    }
                    if settle_order_payload:
                        order_row.raw_payload = {
                            **dict_like(order_row.raw_payload),
                            'settleOrderPayload': settle_order_payload,
                        }
                    account = runtime_account
                    break

                session_row.status = 'confirmed'
                session_row.message = '自动支付处理中，请稍候刷新查看结果'
                session_row.updated_at = now_text()
                order_row.order_status = 'confirmed'
                order_row.updated_at = now_text()
                db.commit()
                db.refresh(session_row)
                db.refresh(order_row)
                db.refresh(runtime_account)
                account = runtime_account
                # 再次进行额度保护：若本次扣后余额下降表征消费额度大于剩余额度，则不返回 pending，直接提示额度不足
                order_amount = pick_int(order_row.amount)
                ensure_public_cdkey_quota_sufficient(cdkey_row, order_amount)
                return {
                    'success': True,
                    'pending': True,
                    **serialize_public_cdkey_summary(cdkey_row),
                    'message': '自动支付处理中，请稍候刷新查看结果',
                    'session': serialize_public_session(session_row, order_row),
                    'order': serialize_public_order(order_row),
                    'account': serialize_public_account(runtime_account),
                }


            failure_message = build_public_remote_token_expired_detail() if should_refresh_public_remote_session(detail) else (detail or '自动支付失败，请稍后重试')
            session_row.status = 'confirmed'
            session_row.message = failure_message
            session_row.updated_at = now_text()
            order_row.order_status = 'confirmed'
            order_row.updated_at = now_text()
            db.commit()
            db.refresh(session_row)
            db.refresh(order_row)
            db.refresh(runtime_account)
            account = runtime_account
            raise_public_remote_error(detail, default_status_code=502)



    consumed_diamond = max(0, int(before_diamond) - int(after_diamond))

    order_row.order_status = 'completed'
    order_row.updated_at = now_text()
    order_row.raw_payload = {
        **dict_like(order_row.raw_payload),
        'beforeFundPayload': before_fund_payload,
        'payPayload': pay_payload,
        'fundPayload': after_fund_payload,
    }

    apply_public_account_diamond_snapshot(account, after_diamond)
    apply_public_cdkey_consumption(cdkey_row, consumed_diamond, latest_order_id=session_row.order_id or '')

    rendered_message = f'解锁成功，本次消耗 {consumed_diamond} 钻。'

    session_row.status = 'completed'
    session_row.message = '已自动完成扣钻，VIP 已解锁'
    session_row.confirmed_at = session_row.confirmed_at or int(time.time())
    session_row.updated_at = now_text()
    session_row.result_payload = {
        'rendered_message': rendered_message,
        'payPayload': pay_payload,
        'beforeFundPayload': before_fund_payload,
        'fundPayload': after_fund_payload,
        'beforeDiamond': before_diamond,
        'afterDiamond': after_diamond,
        'diamondQuantity': after_diamond,
        'consumedDiamond': consumed_diamond,
    }

    session_row.payload = {
        **dict_like(session_row.payload),
        'cdkeyCode': cdkey_row.code,
        'tradeNo': session_row.order_id,
        'autoPay': True,
    }

    db.commit()
    db.refresh(session_row)
    db.refresh(cdkey_row)
    db.refresh(order_row)
    db.refresh(account)
    return {
        'success': True,
        **serialize_public_cdkey_summary(cdkey_row),
        'message': rendered_message,
        'session': serialize_public_session(session_row, order_row),
        'order': serialize_public_order(order_row),
        'account': serialize_public_account(account),
        'renderedMessage': rendered_message,
        'beforeDiamond': before_diamond,
        'afterDiamond': after_diamond,
        'consumedDiamond': consumed_diamond,
    }




def build_public_unlock_url(code: str, session_id: str) -> str:


    safe_code = str(code or '').strip()
    safe_session = str(session_id or '').strip()
    if safe_code:
        return f'/judian/redeem?code={safe_code}&session={safe_session}'
    return f'/judian/unlock?session={safe_session}'



def get_or_create_public_unlock_session(
    db: Session,
    row: models.JudianCdKey,
    account: models.JudianAccount,
    session_id: str = '',
    *,
    force_new: bool = False,
) -> models.JudianScanSession:
    ensure_judian_schema(db)
    session_row = None
    requested_session_id = str(session_id or '').strip()
    if not force_new and requested_session_id:
        session_row = db.query(models.JudianScanSession).filter_by(session_id=requested_session_id, account_id=row.account_id).first()
    if not force_new and session_row is None and row.latest_session_id:
        session_row = db.query(models.JudianScanSession).filter_by(session_id=row.latest_session_id).first()


    reusable_statuses = {'pending', 'scanned', 'confirmed'}
    if session_row is not None and str(session_row.status or 'pending') not in reusable_statuses:
        session_row = None

    now = now_text()
    now_ts = int(time.time())
    if session_row is None:
        session_row = models.JudianScanSession(
            session_id=f'jd_unlock_{uuid.uuid4().hex[:16]}',
            owner_username=row.owner_username or account.owner_username or '',
            account_id=row.account_id or '',
            order_id='',
            scene='cdkey_redeem',
            qr_content='',
            mobile_login_link=account.mobile_login_link or '',
            unlock_url='',
            status='pending',
            message='请打开后置摄像头，对准聚点购买二维码完成扫码',
            expires_at=now_ts + 1800,
            confirmed_at=None,
            result_payload={},
            created_at=now,
            updated_at=now,
            payload={'cdkeyCode': row.code},
        )

        db.add(session_row)
        db.flush()

    session_row.owner_username = row.owner_username or account.owner_username or session_row.owner_username
    session_row.account_id = row.account_id or session_row.account_id
    session_row.mobile_login_link = account.mobile_login_link or session_row.mobile_login_link or ''
    session_row.unlock_url = build_public_unlock_url(row.code, session_row.session_id)
    session_row.payload = {
        **dict_like(session_row.payload),
        'cdkeyCode': row.code or '',
    }
    session_row.updated_at = now

    row.latest_session_id = session_row.session_id
    row.updated_at = now
    db.commit()
    db.refresh(row)
    db.refresh(session_row)
    return session_row



def get_public_unlock_session_or_404(db: Session, session_id: str) -> tuple[models.JudianScanSession, models.JudianCdKey, models.JudianAccount]:
    ensure_judian_schema(db)
    target = str(session_id or '').strip()
    if not target:
        raise HTTPException(status_code=400, detail='缺少 session 参数')
    session_row = db.query(models.JudianScanSession).filter_by(session_id=target).first()
    if session_row is None:
        raise HTTPException(status_code=404, detail='解锁会话不存在或已失效')

    session_payload = dict_like(session_row.payload)
    session_cdkey_code = pick_text(
        session_payload.get('cdkeyCode'),
        session_payload.get('cdkey_code'),
    )

    cdkey_row = None
    if session_cdkey_code:
        cdkey_row = db.query(models.JudianCdKey).filter_by(code=session_cdkey_code).first()

    if cdkey_row is None:
        cdkey_row = db.query(models.JudianCdKey).filter_by(latest_session_id=session_row.session_id).first()

    if cdkey_row is None and session_row.account_id:
        account_cdkeys = (
            db.query(models.JudianCdKey)
            .filter_by(account_id=session_row.account_id)
            .order_by(models.JudianCdKey.updated_at.desc(), models.JudianCdKey.id.desc())
            .all()
        )
        if len(account_cdkeys) == 1:
            cdkey_row = account_cdkeys[0]
        elif len(account_cdkeys) > 1:
            raise HTTPException(status_code=409, detail='当前解锁会话关联了多张卡密，请重新通过卡密链接进入后重试')
    if cdkey_row is None:
        raise HTTPException(status_code=404, detail='解锁会话关联卡密不存在')

    # 如果卡密额度已用尽，直接报错；否则返回账号并继续
    if str(session_row.status or '') == 'completed':
        account = get_public_account_or_404(db, cdkey_row)
    else:
        account = ensure_public_cdkey_ready(db, cdkey_row)
    if str(session_row.account_id or '').strip() and str(session_row.account_id or '').strip() != str(account.account_id or '').strip():
        raise HTTPException(status_code=409, detail='解锁会话与当前卡密绑定账号不一致')
    return session_row, cdkey_row, account




def upsert_public_order(db: Session, session_row: models.JudianScanSession, cdkey_row: models.JudianCdKey, order_payload: dict[str, Any], *, trade_no: str, account: models.JudianAccount) -> models.JudianOrder:
    target_order_id = str(trade_no or '').strip()
    row = db.query(models.JudianOrder).filter_by(order_id=target_order_id).first()
    if row is None:
        row = models.JudianOrder(
            order_id=target_order_id,
            owner_username=cdkey_row.owner_username or account.owner_username or '',
            account_id=account.account_id or '',
            created_at=now_text(),
            updated_at=now_text(),
        )
        db.add(row)

    remote_data = dict_like(order_payload.get('data'))
    row.owner_username = cdkey_row.owner_username or account.owner_username or row.owner_username
    row.account_id = account.account_id or row.account_id
    row.item_id = pick_text(remote_data.get('itemId'), remote_data.get('goodsId'), row.item_id)
    row.item_title = pick_text(remote_data.get('title'), remote_data.get('appName'), remote_data.get('remark'), row.item_title)
    row.buyer_id = pick_text(remote_data.get('buyerId'), remote_data.get('userId'), row.buyer_id)
    row.buyer_nick = pick_text(remote_data.get('buyerNick'), remote_data.get('nickName'), row.buyer_nick)
    row.amount = str(pick_int(remote_data.get('diamond'), row.amount))
    row.quantity = max(1, pick_int(remote_data.get('quantity'), row.quantity, 1))
    row.order_status = session_row.status or row.order_status or 'pending'
    row.delivery_rule_id = pick_nullable_int(remote_data.get('deliveryRuleId'), row.delivery_rule_id)
    row.delivery_card_id = pick_nullable_int(remote_data.get('deliveryCardId'), row.delivery_card_id)
    row.delivery_content_preview = pick_text(remote_data.get('remark'), row.delivery_content_preview)
    row.delivery_link = pick_text(remote_data.get('deliveryLink'), row.delivery_link)
    row.delivery_payload = dict_like(remote_data.get('deliveryPayload'))
    row.raw_payload = order_payload
    row.updated_at = now_text()
    return row


def process_public_unlock_scan(
    db: Session,
    session_row: models.JudianScanSession,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    *,
    qr_text: str = '',
    trade_no: str = '',
    order_no: str = '',
) -> tuple[models.JudianAccount, requests.Session, models.JudianOrder]:
    trade_candidate, order_candidate, scan_url = extract_public_trade_candidate(qr_text, trade_no, order_no)

    def load_scan_order(runtime_session: requests.Session):
        scan_result = remote_scan_qr_notify(runtime_session, order_candidate or trade_candidate, scan_url)
        scan_message = pick_text(
            dict_like(scan_result).get('msg'),
            dict_like(scan_result).get('message'),
        )
        if should_refresh_public_remote_session(scan_message):
            raise HTTPException(status_code=503, detail=scan_message or build_public_remote_token_expired_detail())

        effective_trade_no, order_payload, order_query_trace = resolve_public_order_payload(
            runtime_session,
            qr_text=qr_text,
            trade_candidate=trade_candidate,
            order_candidate=order_candidate,
            scan_result=scan_result,
        )
        order_payload = ensure_public_order_payload_or_raise(order_payload)
        return scan_result, effective_trade_no, order_payload, order_query_trace

    account, remote_session, scan_context = run_public_remote_action_with_relogin(db, account, load_scan_order)
    scan_result, effective_trade_no, order_payload, order_query_trace = scan_context
    order_data = dict_like(order_payload.get('data'))

    previous_order_id = str(session_row.order_id or '').strip()
    session_row.order_id = effective_trade_no
    session_row.qr_content = str(qr_text or '').strip() or session_row.qr_content or effective_trade_no
    session_row.status = 'scanned'
    session_row.message = '订单已同步，正在使用已保存 token 自动扣钻'
    session_row.confirmed_at = None
    if previous_order_id != effective_trade_no or has_public_unlock_success_result(session_row.result_payload):
        session_row.result_payload = {}
    timeout_seconds = pick_int(order_data.get('timeOut'), order_data.get('timeout'))
    session_row.expires_at = int(time.time()) + timeout_seconds if timeout_seconds > 0 else session_row.expires_at
    session_row.updated_at = now_text()
    session_row.payload = {
        **dict_like(session_row.payload),
        'cdkeyCode': cdkey_row.code,
        'tradeCandidate': trade_candidate,
        'tradeNo': effective_trade_no,
        'orderNo': pick_text(order_data.get('orderNo'), order_candidate),
        'scanUrl': scan_url,
        'scanResult': scan_result,
        'orderPayload': order_payload,
        'orderQueryTrace': order_query_trace,
        'autoPay': True,
    }

    order_row = upsert_public_order(db, session_row, cdkey_row, order_payload, trade_no=effective_trade_no, account=account)
    order_row.order_status = 'scanned'
    cdkey_row.latest_order_id = effective_trade_no
    cdkey_row.updated_at = now_text()
    db.commit()
    db.refresh(session_row)
    db.refresh(cdkey_row)
    db.refresh(order_row)
    db.refresh(account)
    return account, remote_session, order_row


def normalize_public_batch_purchase_items(body: JudianPublicBatchPurchaseRequest) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for raw_item in body.items or []:
        qr_text = str((raw_item.qrText if raw_item else '') or '').strip()
        trade_no = str((raw_item.tradeNo if raw_item else '') or '').strip()
        order_no = str((raw_item.orderNo if raw_item else '') or '').strip()
        if not any([qr_text, trade_no, order_no]):
            continue
        normalized.append({
            'qrText': qr_text,
            'tradeNo': trade_no,
            'orderNo': order_no,
        })
    if not normalized:
        raise HTTPException(status_code=400, detail='请至少提供一条可识别的订单数据')
    if len(normalized) > 50:
        raise HTTPException(status_code=400, detail='批量购买单次最多支持 50 条订单')
    return normalized


def normalize_public_batch_order_count(body: JudianPublicBatchPurchaseRequest) -> int:
    count = pick_int(body.count)
    if count <= 0:
        raise HTTPException(status_code=400, detail='请输入大于 0 的批量下单数量')
    if count > 365:
        raise HTTPException(status_code=400, detail='批量下单单次最多支持 365 单')
    return count


def create_public_batch_purchase_task(
    db: Session,
    session_row: models.JudianScanSession,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    items: list[dict[str, str]],
) -> models.JudianBatchPurchaseTask:
    latest_task = get_latest_public_batch_task(db, session_row)
    if latest_task is not None and str(latest_task.status or '') == 'running':
        raise HTTPException(status_code=409, detail='当前会话已有批量购买任务在执行，请稍后查看进度')
    now = now_text()
    row = models.JudianBatchPurchaseTask(
        batch_id=f'jd_batch_{uuid.uuid4().hex[:16]}',
        session_id=session_row.session_id or '',
        owner_username=cdkey_row.owner_username or account.owner_username or '',
        account_id=account.account_id or '',
        cdkey_code=cdkey_row.code or '',
        status='running',
        total_count=len(items),
        processed_count=0,
        success_count=0,
        failed_count=0,
        pending_count=len(items),
        total_consumed_diamond=0,
        current_index=0,
        current_trade_no='',
        message='批量购买进行中',
        result_payload={'items': []},
        payload={'items': items},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    session_row.status = 'confirmed'
    session_row.message = f'批量购买任务已创建，待处理 {len(items)} 单'
    session_row.confirmed_at = None
    session_row.result_payload = {
        **dict_like(session_row.result_payload),
        'latestBatchId': row.batch_id,
    }
    session_row.updated_at = now
    session_row.payload = {
        **dict_like(session_row.payload),
        'latestBatchId': row.batch_id,
        'batchMode': True,
    }
    db.commit()
    db.refresh(row)
    db.refresh(session_row)
    return row


def create_public_batch_script_task(
    db: Session,
    session_row: models.JudianScanSession,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    count: int,
    *,
    vip_id: str = '',
    package_type: str = '',
    unit_diamond: int = 0,
    required_diamond: int = 0,
) -> models.JudianBatchPurchaseTask:
    latest_task = get_latest_public_batch_task(db, session_row)
    if latest_task is not None and str(latest_task.status or '') == 'running':
        raise HTTPException(status_code=409, detail='当前会话已有批量任务在执行，请稍后查看进度')
    now = now_text()
    row = models.JudianBatchPurchaseTask(
        batch_id=f'jd_batch_{uuid.uuid4().hex[:16]}',
        session_id=session_row.session_id or '',
        owner_username=cdkey_row.owner_username or account.owner_username or '',
        account_id=account.account_id or '',
        cdkey_code=cdkey_row.code or '',
        status='running',
        total_count=count,
        processed_count=0,
        success_count=0,
        failed_count=0,
        pending_count=count,
        total_consumed_diamond=0,
        current_index=0,
        current_trade_no='',
        message='批量下单脚本启动中',
        result_payload={'items': []},
        payload={
            'mode': 'script_batch_order',
            'count': count,
            'scriptPath': get_batch_script_display_path(),
            'vipId': vip_id,
            'packageType': str(package_type or '').strip().lower(),
            'unitDiamond': max(0, int(unit_diamond or 0)),
            'requiredDiamond': max(0, int(required_diamond or 0)),
        },
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    session_row.message = f'批量下单任务已创建，待处理 {count} 单'
    session_row.result_payload = {
        **dict_like(session_row.result_payload),
        'latestBatchId': row.batch_id,
    }
    session_row.updated_at = now
    session_row.payload = {
        **dict_like(session_row.payload),
        'latestBatchId': row.batch_id,
        'batchMode': True,
        'batchModeType': 'script_batch_order',
    }
    db.commit()
    db.refresh(row)
    db.refresh(session_row)
    return row


def make_public_batch_failed_items(count: int, message: str) -> list[dict[str, Any]]:
    return [
        {
            'index': index,
            'status': 'failed',
            'tradeNo': '',
            'orderNo': '',
            'message': message,
            'consumedDiamond': 0,
            'sessionStatus': 'failed',
            'orderStatus': '',
        }
        for index in range(1, max(1, int(count)) + 1)
    ]


def get_batch_script_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def get_batch_script_path() -> str:
    return os.path.join(get_batch_script_root(), 'test-vip.js')


def get_batch_script_display_path() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    script_path = get_batch_script_path()
    try:
        return os.path.relpath(script_path, project_root)
    except ValueError:
        return script_path


def resolve_public_batch_script_credentials(account: models.JudianAccount, body: JudianPublicBatchPurchaseRequest) -> tuple[str, str]:
    login_email = pick_text(body.account, resolve_account_login_email(account))
    login_password = pick_text(body.password, resolve_account_login_password(account))
    if not login_email or not login_password:
        raise HTTPException(status_code=400, detail='当前账号未保存动漫共和国登录账号或密码，无法执行批量下单脚本')
    return login_email, login_password


def build_public_batch_script_command(login_email: str, login_password: str, count: int, *, vip_id: str = '') -> tuple[list[str], str]:
    script_root = get_batch_script_root()
    script_path = get_batch_script_path()
    if not os.path.isfile(script_path):
        raise HTTPException(status_code=500, detail=f'未找到批量下单脚本: {script_path}')
    command = [
        'node',
        'test-vip.js',
        'batch',
        '--account',
        login_email,
        '--password',
        login_password,
        '--count',
        str(max(1, int(count))),
        '--confirm-buy',
        '--progress-jsonl',
    ]
    if vip_id:
        command.extend(['--vip-id', str(vip_id)])
    return command, script_root


BATCH_SCRIPT_EVENT_PREFIX = '__JD_BATCH_EVENT__'
BATCH_SCRIPT_RESULT_PREFIX = '__JD_BATCH_RESULT__'


def parse_public_batch_script_prefixed_json_line(text: str, prefix: str) -> dict[str, Any]:
    line = str(text or '').strip()
    if not line.startswith(prefix):
        return {}
    payload_text = line[len(prefix):].strip()
    if not payload_text:
        return {}
    try:
        payload = json.loads(payload_text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def try_parse_script_json_output(stdout_text: str) -> dict[str, Any]:
    text = str(stdout_text or '').strip()
    if not text:
        return {}
    for line in reversed(text.splitlines()):
        payload = parse_public_batch_script_prefixed_json_line(line, BATCH_SCRIPT_RESULT_PREFIX)
        if payload:
            return payload
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start:end + 1])
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}
    return {}


def merge_public_batch_progress_items(items_result: list[dict[str, Any]], next_item: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    target_index = max(1, pick_int(next_item.get('index'), 1))
    for item in items_result:
        if not isinstance(item, dict):
            continue
        item_index = max(1, pick_int(item.get('index'), 1))
        if item_index == target_index:
            continue
        normalized.append(dict_like(item))
    normalized.append({
        'index': target_index,
        'status': str(next_item.get('status') or 'failed'),
        'tradeNo': pick_text(next_item.get('tradeNo')),
        'orderNo': pick_text(next_item.get('orderNo')),
        'message': pick_text(next_item.get('message')),
        'consumedDiamond': max(0, pick_int(next_item.get('consumedDiamond'))),
        'sessionStatus': pick_text(next_item.get('sessionStatus')),
        'orderStatus': pick_text(next_item.get('orderStatus')),
    })
    normalized.sort(key=lambda item: max(1, pick_int(item.get('index'), 1)))
    return normalized


def build_public_batch_progress_item_from_script_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get('type') or '').strip().lower()
    index = max(1, pick_int(event.get('index'), 1))
    if event_type == 'buy_item' and event.get('ok') is False:
        return {
            'index': index,
            'status': 'failed',
            'tradeNo': '',
            'orderNo': pick_text(event.get('orderNo')),
            'message': pick_text(event.get('error'), '创建订单失败'),
            'consumedDiamond': 0,
            'sessionStatus': 'failed',
            'orderStatus': 'failed',
        }
    if event_type != 'autopay_item':
        return None
    if event.get('ok') is True:
        return {
            'index': index,
            'status': 'completed',
            'tradeNo': pick_text(event.get('tradeNo')),
            'orderNo': pick_text(event.get('orderNo')),
            'message': pick_text(event.get('message'), '自动支付成功'),
            'consumedDiamond': max(0, pick_int(event.get('consumedDiamond'))),
            'sessionStatus': 'completed',
            'orderStatus': 'completed',
        }
    return {
        'index': index,
        'status': 'failed',
        'tradeNo': pick_text(event.get('tradeNo')),
        'orderNo': pick_text(event.get('orderNo')),
        'message': pick_text(event.get('error'), '自动支付失败'),
        'consumedDiamond': 0,
        'sessionStatus': 'failed',
        'orderStatus': 'failed',
    }


def apply_public_batch_script_progress_event(
    db: Session,
    batch_task_row: models.JudianBatchPurchaseTask,
    session_row: models.JudianScanSession,
    event: dict[str, Any],
) -> models.JudianBatchPurchaseTask:
    event_type = str(event.get('type') or '').strip().lower()
    total = max(1, pick_int(event.get('total'), batch_task_row.total_count, 1))
    index = max(0, pick_int(event.get('index'), 0))
    current_trade_no = pick_text(event.get('tradeNo'), event.get('orderNo'))
    existing_items = dict_like(batch_task_row.result_payload).get('items')
    items_result = [dict_like(item) for item in existing_items] if isinstance(existing_items, list) else []

    if event_type == 'buy_phase_started':
        batch_task_row.message = f'批量下单脚本创建订单中，共 {total} 单'
        batch_task_row.current_index = 0
        batch_task_row.current_trade_no = ''
    elif event_type == 'autopay_phase_started':
        batch_task_row.message = f'批量下单脚本自动支付中，共 {total} 单'
        batch_task_row.current_index = int(batch_task_row.processed_count or 0)
        batch_task_row.current_trade_no = ''
    elif event_type == 'buy_item' and event.get('ok') is True:
        batch_task_row.message = f'第 {index}/{total} 单已创建，等待自动支付'
        batch_task_row.current_index = index
        batch_task_row.current_trade_no = current_trade_no
    else:
        item_result = build_public_batch_progress_item_from_script_event(event)
        if item_result is None:
            return batch_task_row
        items_result = merge_public_batch_progress_items(items_result, item_result)
        message = (
            f'已完成 {len(items_result)}/{int(batch_task_row.total_count or total)} 单'
            if str(item_result.get('status') or '') == 'completed'
            else f'第 {index}/{total} 单失败：{item_result["message"]}'
        )
        batch_task_row = finalize_public_batch_task(
            db,
            batch_task_row,
            status='running',
            message=message,
            items_result=items_result,
            current_index=index,
            current_trade_no=pick_text(item_result.get('tradeNo'), item_result.get('orderNo'), current_trade_no),
        )
        session_row.updated_at = now_text()
        session_row.result_payload = {
            **dict_like(session_row.result_payload),
            'latestBatchId': batch_task_row.batch_id,
        }
        db.commit()
        db.refresh(session_row)
        return batch_task_row

    batch_task_row.result_payload = {
        **dict_like(batch_task_row.result_payload),
        'items': items_result,
        'lastEvent': event,
    }
    batch_task_row.updated_at = now_text()
    session_row.updated_at = batch_task_row.updated_at
    session_row.result_payload = {
        **dict_like(session_row.result_payload),
        'latestBatchId': batch_task_row.batch_id,
    }
    db.commit()
    db.refresh(batch_task_row)
    db.refresh(session_row)
    return batch_task_row


def build_public_batch_items_from_script_result(result_payload: dict[str, Any], fallback_count: int) -> tuple[list[dict[str, Any]], int]:
    count = max(
        pick_int(result_payload.get('count')),
        fallback_count,
    )
    if str(result_payload.get('phase') or '') == 'precheck':
        message = pick_text(result_payload.get('message'), '批量下单前置校验失败')
        return make_public_batch_failed_items(count, message), 0

    buy_result = dict_like(result_payload.get('buyResult'))
    auto_pay_result = dict_like(result_payload.get('autoPayResult'))
    buy_orders = buy_result.get('orders')
    auto_items = auto_pay_result.get('items')
    buy_orders = buy_orders if isinstance(buy_orders, list) else []
    auto_items = auto_items if isinstance(auto_items, list) else []
    buy_map = {
        max(1, pick_int(item.get('index'))): dict_like(item)
        for item in buy_orders
        if isinstance(item, dict)
    }
    pay_map = {
        max(1, pick_int(item.get('index'))): dict_like(item)
        for item in auto_items
        if isinstance(item, dict)
    }

    items_result: list[dict[str, Any]] = []
    total_consumed_diamond = 0
    for index in range(1, count + 1):
        buy_item = buy_map.get(index, {})
        pay_item = pay_map.get(index, {})
        create_result = dict_like(buy_item.get('createResult'))
        pay_result = dict_like(pay_item.get('result'))
        pay_ok = pay_item.get('ok') is True
        pay_failed = pay_item.get('ok') is False
        buy_ok = buy_item.get('ok') is True
        buy_failed = buy_item.get('ok') is False
        consumed = max(0, pick_int(pay_result.get('consumedDiamond')))
        total_consumed_diamond += consumed
        if pay_ok:
            status = 'completed'
            message = pick_text(
                pay_result.get('scanResult', {}).get('message') if isinstance(pay_result.get('scanResult'), dict) else '',
                '自动支付成功',
            )
            session_status = 'completed'
            order_status = 'completed'
        elif pay_failed:
            status = 'failed'
            message = pick_text(pay_item.get('error'), '自动支付失败')
            session_status = 'failed'
            order_status = 'failed'
        elif buy_failed:
            status = 'failed'
            message = pick_text(buy_item.get('error'), '创建订单失败')
            session_status = 'failed'
            order_status = 'failed'
        elif buy_ok:
            status = 'failed'
            message = '订单已创建，但未拿到自动支付结果'
            session_status = 'failed'
            order_status = 'created'
        else:
            status = 'failed'
            message = '脚本未返回该订单的处理结果'
            session_status = 'failed'
            order_status = ''
        items_result.append({
            'index': index,
            'status': status,
            'tradeNo': pick_text(pay_result.get('tradeNo'), create_result.get('orderNo')),
            'orderNo': pick_text(pay_result.get('orderNo'), create_result.get('orderNo')),
            'message': message,
            'consumedDiamond': consumed,
            'sessionStatus': session_status,
            'orderStatus': order_status,
        })
    return items_result, total_consumed_diamond


def finalize_public_batch_task(
    db: Session,
    row: models.JudianBatchPurchaseTask,
    *,
    status: str,
    message: str,
    items_result: list[dict[str, Any]],
    current_index: int | None = None,
    current_trade_no: str | None = None,
    total_consumed_diamond: int | None = None,
) -> models.JudianBatchPurchaseTask:
    total_count = int(row.total_count or 0)
    processed_count = len(items_result)
    success_count = sum(1 for item in items_result if str(item.get('status') or '') == 'completed')
    failed_count = sum(1 for item in items_result if str(item.get('status') or '') == 'failed')
    pending_count = max(0, total_count - processed_count)
    computed_consumed = sum(max(0, pick_int(item.get('consumedDiamond'))) for item in items_result)
    row.status = status
    row.message = message
    row.processed_count = processed_count
    row.success_count = success_count
    row.failed_count = failed_count
    row.pending_count = pending_count
    row.current_index = int(current_index if current_index is not None else processed_count)
    row.current_trade_no = str(current_trade_no if current_trade_no is not None else row.current_trade_no or '')
    row.total_consumed_diamond = computed_consumed if total_consumed_diamond is None else max(0, int(total_consumed_diamond))
    row.result_payload = {
        **dict_like(row.result_payload),
        'items': items_result,
    }
    row.updated_at = now_text()
    db.commit()
    db.refresh(row)
    return row


def run_public_batch_purchase(
    db: Session,
    session_row: models.JudianScanSession,
    cdkey_row: models.JudianCdKey,
    account: models.JudianAccount,
    batch_task_row: models.JudianBatchPurchaseTask,
) -> tuple[dict[str, Any], models.JudianBatchPurchaseTask]:
    source_items = dict_like(batch_task_row.payload).get('items')
    items: list[dict[str, str]] = source_items if isinstance(source_items, list) else []
    results: list[dict[str, Any]] = []

    for index, item in enumerate(items, start=1):
        batch_task_row.current_index = index
        batch_task_row.current_trade_no = str(item.get('tradeNo') or item.get('orderNo') or '')
        batch_task_row.message = f'正在处理第 {index}/{len(items)} 单'
        batch_task_row.updated_at = now_text()
        db.commit()
        db.refresh(batch_task_row)

        try:
            runtime_account, remote_session, order_row = process_public_unlock_scan(
                db,
                session_row,
                cdkey_row,
                account,
                qr_text=str(item.get('qrText') or ''),
                trade_no=str(item.get('tradeNo') or ''),
                order_no=str(item.get('orderNo') or ''),
            )
            payment_result = execute_public_unlock_payment(
                db,
                session_row,
                cdkey_row,
                runtime_account,
                order_row,
                remote_session=remote_session,
            )
            account = runtime_account
            item_result = {
                'index': index,
                'status': 'completed',
                'tradeNo': order_row.order_id or str(item.get('tradeNo') or ''),
                'orderNo': pick_text(dict_like(order_row.raw_payload).get('data', {}).get('orderNo') if isinstance(dict_like(order_row.raw_payload).get('data'), dict) else '', item.get('orderNo')),
                'message': str(payment_result.get('message') or payment_result.get('renderedMessage') or '处理成功'),
                'consumedDiamond': max(0, pick_int(payment_result.get('consumedDiamond'))),
                'sessionStatus': session_row.status or '',
                'orderStatus': order_row.order_status or '',
            }
        except HTTPException as exc:
            item_result = {
                'index': index,
                'status': 'failed',
                'tradeNo': str(item.get('tradeNo') or ''),
                'orderNo': str(item.get('orderNo') or ''),
                'message': str(exc.detail or '处理失败'),
                'consumedDiamond': 0,
                'sessionStatus': session_row.status or '',
                'orderStatus': '',
            }
            results.append(item_result)
            batch_task_row = finalize_public_batch_task(
                db,
                batch_task_row,
                status='failed',
                message=f'第 {index} 单处理失败：{item_result["message"]}',
                items_result=results,
                current_index=index,
                current_trade_no=item_result['tradeNo'],
            )
            session_row.status = 'failed'
            session_row.message = batch_task_row.message
            session_row.updated_at = now_text()
            session_row.result_payload = {
                **dict_like(session_row.result_payload),
                'latestBatchId': batch_task_row.batch_id,
                'batchFailedIndex': index,
            }
            db.commit()
            db.refresh(session_row)
            return build_public_unlock_response(
                db,
                cdkey_row,
                account,
                session_row,
                batch_task_row=batch_task_row,
            ), batch_task_row
        except Exception as exc:
            item_result = {
                'index': index,
                'status': 'failed',
                'tradeNo': str(item.get('tradeNo') or ''),
                'orderNo': str(item.get('orderNo') or ''),
                'message': str(exc or '处理失败'),
                'consumedDiamond': 0,
                'sessionStatus': session_row.status or '',
                'orderStatus': '',
            }
            results.append(item_result)
            batch_task_row = finalize_public_batch_task(
                db,
                batch_task_row,
                status='failed',
                message=f'第 {index} 单处理失败：{item_result["message"]}',
                items_result=results,
                current_index=index,
                current_trade_no=item_result['tradeNo'],
            )
            session_row.status = 'failed'
            session_row.message = batch_task_row.message
            session_row.updated_at = now_text()
            session_row.result_payload = {
                **dict_like(session_row.result_payload),
                'latestBatchId': batch_task_row.batch_id,
                'batchFailedIndex': index,
            }
            db.commit()
            db.refresh(session_row)
            return build_public_unlock_response(
                db,
                cdkey_row,
                account,
                session_row,
                batch_task_row=batch_task_row,
            ), batch_task_row

        results.append(item_result)
        batch_task_row = finalize_public_batch_task(
            db,
            batch_task_row,
            status='running',
            message=f'已完成 {len(results)}/{len(items)} 单',
            items_result=results,
            current_index=index,
            current_trade_no=item_result['tradeNo'],
        )

    batch_task_row = finalize_public_batch_task(
        db,
        batch_task_row,
        status='completed',
        message=f'批量购买完成，共处理 {len(results)} 单',
        items_result=results,
        current_index=len(results),
        current_trade_no=str(results[-1].get('tradeNo') or '') if results else '',
    )
    session_row.status = 'completed'
    session_row.message = batch_task_row.message
    session_row.updated_at = now_text()
    session_row.result_payload = {
        **dict_like(session_row.result_payload),
        'latestBatchId': batch_task_row.batch_id,
        'batchCompletedCount': len(results),
        'batchConsumedDiamond': int(batch_task_row.total_consumed_diamond or 0),
    }
    db.commit()
    db.refresh(session_row)
    return build_public_unlock_response(
        db,
        cdkey_row,
        account,
        session_row,
        batch_task_row=batch_task_row,
    ), batch_task_row


def run_public_batch_purchase_job(session_id: str, batch_id: str) -> None:
    db = SessionLocal()
    try:
        ensure_judian_schema(db)
        session_row = db.query(models.JudianScanSession).filter_by(session_id=str(session_id or '').strip()).first()
        batch_task_row = db.query(models.JudianBatchPurchaseTask).filter_by(batch_id=str(batch_id or '').strip()).first()
        if session_row is None or batch_task_row is None:
            return
        cdkey_row = db.query(models.JudianCdKey).filter_by(code=batch_task_row.cdkey_code).first()
        if cdkey_row is None:
            batch_task_row = finalize_public_batch_task(
                db,
                batch_task_row,
                status='failed',
                message='批量任务关联卡密不存在',
                items_result=[],
            )
            session_row.status = 'failed'
            session_row.message = batch_task_row.message
            session_row.updated_at = now_text()
            db.commit()
            return
        account = get_public_account_or_404(db, cdkey_row)
        run_public_batch_purchase(db, session_row, cdkey_row, account, batch_task_row)
    except Exception as exc:
        try:
            failed_task = db.query(models.JudianBatchPurchaseTask).filter_by(batch_id=str(batch_id or '').strip()).first()
            failed_session = db.query(models.JudianScanSession).filter_by(session_id=str(session_id or '').strip()).first()
            existing_items = []
            if failed_task is not None:
                existing_items = dict_like(failed_task.result_payload).get('items')
                if not isinstance(existing_items, list):
                    existing_items = []
                failed_task = finalize_public_batch_task(
                    db,
                    failed_task,
                    status='failed',
                    message=str(exc or '批量购买执行失败'),
                    items_result=existing_items,
                )
                if failed_session is not None:
                    failed_session.status = 'failed'
                    failed_session.message = failed_task.message
                    failed_session.updated_at = now_text()
                    db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def run_public_batch_script_job(session_id: str, batch_id: str, login_email: str, login_password: str) -> None:
    db = SessionLocal()
    try:
        ensure_judian_schema(db)
        session_row = db.query(models.JudianScanSession).filter_by(session_id=str(session_id or '').strip()).first()
        batch_task_row = db.query(models.JudianBatchPurchaseTask).filter_by(batch_id=str(batch_id or '').strip()).first()
        if session_row is None or batch_task_row is None:
            return
        cdkey_row = db.query(models.JudianCdKey).filter_by(code=batch_task_row.cdkey_code).first()
        if cdkey_row is None:
            failed_items = make_public_batch_failed_items(
                int(batch_task_row.total_count or 1),
                '批量任务关联卡密不存在',
            )
            batch_task_row = finalize_public_batch_task(
                db,
                batch_task_row,
                status='failed',
                message='批量任务关联卡密不存在',
                items_result=failed_items,
            )
            session_row.message = batch_task_row.message
            session_row.updated_at = now_text()
            db.commit()
            return
        account = get_public_account_or_404(db, cdkey_row)

        count = max(1, pick_int(dict_like(batch_task_row.payload).get('count')))
        payload = dict_like(batch_task_row.payload)
        vip_id = pick_text(payload.get('vipId'))
        package_type = pick_text(payload.get('packageType')).lower()
        required_diamond = max(0, pick_int(dict_like(batch_task_row.payload).get('requiredDiamond')))
        if required_diamond <= 0:
            vip_id, unit_diamond, required_diamond = resolve_public_batch_required_diamond(
                count,
                vip_id=vip_id,
                package_type=package_type,
            )
            batch_task_row.payload = {
                **dict_like(batch_task_row.payload),
                'vipId': vip_id,
                'packageType': package_type,
                'unitDiamond': unit_diamond,
                'requiredDiamond': required_diamond,
            }
            db.commit()
            db.refresh(batch_task_row)
        ensure_public_cdkey_quota_sufficient(cdkey_row, required_diamond)
        command, script_root = build_public_batch_script_command(
            login_email,
            login_password,
            count,
            vip_id=vip_id,
        )
        batch_task_row.message = f'批量下单脚本执行中，共 {count} 单，预计扣除 {required_diamond} 钻'
        batch_task_row.updated_at = now_text()
        db.commit()
        db.refresh(batch_task_row)

        process = subprocess.Popen(
            command,
            cwd=script_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        timeout_seconds = max(60, count * 45)
        stdout_lines: list[str] = []
        stdout_queue: queue.Queue[str] = queue.Queue()

        def consume_script_output() -> None:
            if process.stdout is None:
                return
            try:
                for raw_line in process.stdout:
                    stdout_queue.put(str(raw_line))
            finally:
                try:
                    process.stdout.close()
                except Exception:
                    pass

        reader_thread = threading.Thread(target=consume_script_output, daemon=True)
        reader_thread.start()
        deadline = time.time() + timeout_seconds
        timed_out = False
        while True:
            wait_timeout = max(0.1, min(0.5, deadline - time.time()))
            try:
                line = stdout_queue.get(timeout=wait_timeout)
                stdout_lines.append(line)
                event_payload = parse_public_batch_script_prefixed_json_line(line, BATCH_SCRIPT_EVENT_PREFIX)
                if event_payload:
                    batch_task_row = apply_public_batch_script_progress_event(
                        db,
                        batch_task_row,
                        session_row,
                        event_payload,
                    )
                continue
            except queue.Empty:
                if process.poll() is not None:
                    break
                if time.time() >= deadline:
                    timed_out = True
                    process.kill()
                    break
        reader_thread.join(timeout=2)
        while not stdout_queue.empty():
            line = stdout_queue.get_nowait()
            stdout_lines.append(line)
            event_payload = parse_public_batch_script_prefixed_json_line(line, BATCH_SCRIPT_EVENT_PREFIX)
            if event_payload:
                batch_task_row = apply_public_batch_script_progress_event(
                    db,
                    batch_task_row,
                    session_row,
                    event_payload,
                )
        if timed_out:
            raise RuntimeError(f'批量下单脚本执行超时，超过 {timeout_seconds} 秒')
        stdout_text = ''.join(stdout_lines)
        stderr_text = ''
        result_payload = try_parse_script_json_output(stdout_text)
        if process.returncode not in (0, None) and not result_payload:
            lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
            raise RuntimeError(pick_text(lines[-1] if lines else '', '批量下单脚本执行失败'))

        items_result, total_consumed_diamond = build_public_batch_items_from_script_result(result_payload, count)
        final_ok = result_payload.get('ok') is True and all(
            str(item.get('status') or '') == 'completed' for item in items_result
        )
        final_message = pick_text(
            result_payload.get('message'),
            f'批量下单完成，共处理 {len(items_result)} 单' if final_ok else '批量下单执行结束，存在失败订单',
        )
        batch_task_row.payload = {
            **dict_like(batch_task_row.payload),
            'command': ['node', 'test-vip.js', 'batch', '--count', str(count)],
            'cwd': script_root,
        }
        batch_task_row.result_payload = {
            'items': items_result,
            'scriptResult': result_payload,
            'stdout': stdout_text[-12000:],
            'stderr': stderr_text[-12000:],
        }
        apply_public_batch_script_consumption(
            batch_task_row,
            cdkey_row,
            account,
            items_result=items_result,
            result_payload=result_payload,
            total_consumed_diamond=total_consumed_diamond,
        )
        batch_task_row = finalize_public_batch_task(
            db,
            batch_task_row,
            status='completed' if final_ok else 'failed',
            message=final_message,
            items_result=items_result,
            current_index=len(items_result),
            current_trade_no=str(items_result[-1].get('tradeNo') or items_result[-1].get('orderNo') or '') if items_result else '',
            total_consumed_diamond=total_consumed_diamond,
        )
        session_row.message = batch_task_row.message
        session_row.updated_at = now_text()
        session_row.result_payload = {
            **dict_like(session_row.result_payload),
            'latestBatchId': batch_task_row.batch_id,
            'batchCompletedCount': len(items_result),
            'batchConsumedDiamond': int(batch_task_row.total_consumed_diamond or 0),
        }
        db.commit()
    except Exception as exc:
        try:
            failed_task = db.query(models.JudianBatchPurchaseTask).filter_by(batch_id=str(batch_id or '').strip()).first()
            failed_session = db.query(models.JudianScanSession).filter_by(session_id=str(session_id or '').strip()).first()
            if failed_task is not None:
                count = max(1, pick_int(dict_like(failed_task.payload).get('count'), failed_task.total_count, 1))
                existing_items = dict_like(failed_task.result_payload).get('items')
                if not isinstance(existing_items, list) or not existing_items:
                    existing_items = make_public_batch_failed_items(count, str(exc or '批量下单脚本执行失败'))
                failed_task = finalize_public_batch_task(
                    db,
                    failed_task,
                    status='failed',
                    message=str(exc or '批量下单脚本执行失败'),
                    items_result=existing_items,
                )
                failed_task.result_payload = {
                    **dict_like(failed_task.result_payload),
                    'stderr': pick_text(dict_like(failed_task.result_payload).get('stderr'), str(exc or '')),
                }
                if failed_session is not None:
                    failed_session.message = failed_task.message
                    failed_session.updated_at = now_text()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()



@app.get('/cdkey/redeem')
def redeem_cdkey(code: str, session: str | None = None, refresh: int = 0, db: Session = Depends(get_db)):
    row = get_public_cdkey_or_404(db, code)
    account = ensure_public_cdkey_ready(db, row)
    session_row = get_or_create_public_unlock_session(db, row, account, session or '', force_new=bool(refresh))
    order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first() if session_row.order_id else None
    return build_public_unlock_response(db, row, account, session_row, order_row)


@app.get('/public/unlock/{session_id}')
def public_unlock_detail(session_id: str, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first() if session_row.order_id else None
    return build_public_unlock_response(db, cdkey_row, account, session_row, order_row)


@app.get('/public/unlock/{session_id}/batch')
def public_unlock_batch_detail(session_id: str, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    batch_task_row = get_latest_public_batch_task(db, session_row)
    if batch_task_row is None:
        raise HTTPException(status_code=404, detail='当前会话暂无批量购买任务')
    order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first() if session_row.order_id else None
    return build_public_unlock_response(
        db,
        cdkey_row,
        account,
        session_row,
        order_row,
        batch_task_row=batch_task_row,
    )


@app.get('/public/unlock/{session_id}/batch/preview')
def public_unlock_batch_preview(
    session_id: str,
    count: int,
    vip_id: str = '',
    package_type: str = '',
    db: Session = Depends(get_db),
):
    _session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    target_count = max(1, int(count))
    return {
        'success': True,
        'preview': build_public_batch_purchase_preview(
            cdkey_row,
            account,
            count=target_count,
            vip_id=vip_id,
            package_type=package_type,
        ),
    }


@app.post('/public/unlock/{session_id}/scan')
def public_unlock_scan(session_id: str, body: JudianPublicUnlockScanRequest, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    account, remote_session, order_row = process_public_unlock_scan(
        db,
        session_row,
        cdkey_row,
        account,
        qr_text=body.qrText or '',
        trade_no=body.tradeNo or '',
        order_no=body.orderNo or '',
    )
    return execute_public_unlock_payment(
        db,
        session_row,
        cdkey_row,
        account,
        order_row,
        remote_session=remote_session,
    )


@app.post('/public/unlock/{session_id}/batch')
def public_unlock_batch_purchase(session_id: str, body: JudianPublicBatchPurchaseRequest, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    if body.count is not None and not (body.items or []):
        count = normalize_public_batch_order_count(body)
        login_email, login_password = resolve_public_batch_script_credentials(account, body)
        package_type = pick_text(body.packageType).lower()
        vip_id, unit_diamond, required_diamond = resolve_public_batch_required_diamond(
            count,
            vip_id=pick_text(body.vipId),
            package_type=package_type,
        )
        ensure_public_cdkey_quota_sufficient(cdkey_row, required_diamond)
        batch_task_row = create_public_batch_script_task(
            db,
            session_row,
            cdkey_row,
            account,
            count,
            vip_id=vip_id,
            package_type=package_type,
            unit_diamond=unit_diamond,
            required_diamond=required_diamond,
        )
        worker = threading.Thread(
            target=run_public_batch_script_job,
            args=(session_row.session_id, batch_task_row.batch_id, login_email, login_password),
            daemon=True,
        )
        worker.start()
    else:
        items = normalize_public_batch_purchase_items(body)
        batch_task_row = create_public_batch_purchase_task(db, session_row, cdkey_row, account, items)
        worker = threading.Thread(
            target=run_public_batch_purchase_job,
            args=(session_row.session_id, batch_task_row.batch_id),
            daemon=True,
        )
        worker.start()
    order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first() if session_row.order_id else None
    return build_public_unlock_response(
        db,
        cdkey_row,
        account,
        session_row,
        order_row,
        batch_task_row=batch_task_row,
    )


@app.post('/public/unlock/{session_id}/confirm')
def public_unlock_confirm(session_id: str, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    if not session_row.order_id:
        raise HTTPException(status_code=400, detail='当前会话还没有识别到订单，请先扫码')

    def load_order(runtime_session: requests.Session):
        order_payload = remote_get_order_info(runtime_session, session_row.order_id)
        return ensure_public_order_payload_or_raise(order_payload)

    try:
        account, remote_session, order_payload = run_public_remote_action_with_relogin(db, account, load_order)
    except JudianRemoteError as exc:
        raise_public_remote_error(str(exc), default_status_code=502)

    order_row = upsert_public_order(db, session_row, cdkey_row, order_payload, trade_no=session_row.order_id, account=account)
    order_row.order_status = 'confirmed'
    session_row.status = 'confirmed'
    session_row.message = '订单校验完成，正在使用已保存 token 自动扣钻'
    session_row.confirmed_at = int(time.time())
    session_row.updated_at = now_text()

    db.commit()
    db.refresh(session_row)
    db.refresh(order_row)
    db.refresh(account)
    return execute_public_unlock_payment(
        db,
        session_row,
        cdkey_row,
        account,
        order_row,
        remote_session=remote_session,
    )


@app.post('/public/unlock/{session_id}/complete')
def public_unlock_complete(session_id: str, db: Session = Depends(get_db)):
    session_row, cdkey_row, account = get_public_unlock_session_or_404(db, session_id)
    order_row = db.query(models.JudianOrder).filter_by(order_id=session_row.order_id).first() if session_row.order_id else None
    return execute_public_unlock_payment(db, session_row, cdkey_row, account, order_row)





@app.get('/verify')
def verify(user: dict[str, Any] = Depends(get_current_user)):
    return {
        'authenticated': True,
        'username': user['username'],
        'is_admin': bool(user.get('is_admin')),
    }



@app.get('/dashboard/summary')
def dashboard_summary(user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    account_rows = owner_scoped_account_query(db, user).order_by(models.JudianAccount.updated_at.desc(), models.JudianAccount.id.desc()).all()
    cdkey_rows = owner_scoped_cdkey_query(db, user).order_by(models.JudianCdKey.updated_at.desc(), models.JudianCdKey.id.desc()).all()

    serialized_accounts = [serialize_account(row) for row in account_rows]
    serialized_cdkeys = [serialize_cdkey(row) for row in cdkey_rows]
    active_count = sum(1 for item in serialized_accounts if item['status'] == 'active' and item['sessionToken'])
    enabled_count = sum(1 for item in serialized_accounts if item['enabled'])
    total_diamonds = sum(int(item['diamondQuantity'] or 0) for item in serialized_accounts)
    available_cdkeys = sum(1 for item in serialized_cdkeys if item['status'] in {'unused', 'active'})
    invalid_cdkeys = sum(1 for item in serialized_cdkeys if item['status'] in {'expired', 'void'})
    key_status_summary = [
        {
            'status': status,
            'label': label,
            'count': sum(1 for item in serialized_cdkeys if item['status'] == status),
            'description': description,
        }
        for status, label, description in [
            ('unused', '待领取', '尚未领取、可继续发放的真实卡密'),
            ('active', '已领取', '已经进入使用链路的真实卡密'),
            ('expired', '已过期', '已过期、建议清理的真实卡密'),
            ('void', '已作废', '手动作废后不再继续使用的卡密'),
        ]
    ]
    top_accounts = sorted(serialized_accounts, key=lambda item: int(item['diamondQuantity'] or 0), reverse=True)[:8]
    activities = build_dashboard_activities(account_rows, cdkey_rows)
    last_updated_at = max(
        [str(item.get('createdAt') or '') for item in activities]
        + [str(item['updatedAt'] or item['lastLoginAt'] or '') for item in serialized_accounts]
        + [str(item['updatedAt'] or item['createdAt'] or '') for item in serialized_cdkeys]
        + [''],
    )
    return {
        'accounts': len(serialized_accounts),
        'activeSessions': active_count,
        'enabledAccounts': enabled_count,
        'totalDiamonds': total_diamonds,
        'cdkeys': len(serialized_cdkeys),
        'availableCdkeys': available_cdkeys,
        'invalidCdkeys': invalid_cdkeys,
        'topAccounts': top_accounts,
        'keyStatusSummary': key_status_summary,
        'activities': activities,
        'lastUpdatedAt': last_updated_at,
    }


@app.get('/accounts')
def list_accounts(user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = owner_scoped_account_query(db, user).order_by(models.JudianAccount.updated_at.desc(), models.JudianAccount.id.desc()).all()
    return {
        'items': [serialize_account(row) for row in rows],
        'total': len(rows),
    }


@app.get('/cards')
def list_cards(user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = owner_scoped_card_query(db, user).order_by(models.JudianCard.updated_at.desc(), models.JudianCard.id.desc()).all()
    return {
        'items': [serialize_card(row) for row in rows],
        'total': len(rows),
    }


def save_card_from_request(
    db: Session,
    user: dict[str, Any],
    body: JudianCardCreateRequest,
    row: models.JudianCard | None = None,
) -> models.JudianCard:
    name = str(body.name or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='请填写卡券名称')

    now = now_text()
    owner_username = str(user.get('username') or '').strip()
    card_type = str(body.cardType or 'text').strip() or 'text'
    existing_data_content = dict_like(row.data_content) if row is not None else {}
    existing_payload = dict_like(row.payload) if row is not None else {}
    image_url = str(body.imageUrl or '').strip()
    link_url = str(body.linkUrl or '').strip()

    if row is None:
        row = models.JudianCard(
            owner_username=owner_username,
            created_at=now,
            updated_at=now,
            payload={},
        )
        db.add(row)

    row.owner_username = owner_username
    row.name = name
    row.card_type = card_type
    row.description = str(body.description or '').strip()
    row.enabled = True if body.enabled is None else bool(body.enabled)
    row.text_content = str(body.textContent or '').strip()
    row.data_content = build_card_data_content(body, existing_data_content)
    row.link_url = image_url or link_url
    row.delivery_template = str(body.deliveryTemplate or '').strip()
    row.usage_info = str(body.usageInfo or '').strip()
    row.usage_notice = str(body.notice or str(body.remark or '')).strip()
    row.updated_at = now
    row.payload = {
        **existing_payload,
        'remark': str(body.remark or '').strip(),
        'editorSource': 'judian-standalone-delivery',
        'updatedAt': now,
    }
    if not str(row.created_at or '').strip():
        row.created_at = now
    return row


@app.get('/cards/{card_id}')
def get_card(card_id: int, user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_card_or_404(db, user, card_id)
    return serialize_card(row)


@app.post('/cards')
def create_card(body: JudianCardCreateRequest, user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    row = save_card_from_request(db, user, body)
    db.commit()
    db.refresh(row)
    return {
        'message': '卡券创建成功',
        'id': row.id,
        'card_id': row.id,
        'item': serialize_card(row),
        'card': serialize_card(row),
    }


@app.put('/cards/{card_id}')
def update_card(card_id: int, body: JudianCardCreateRequest, user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_card_or_404(db, user, card_id)
    save_card_from_request(db, user, body, row)
    db.commit()
    db.refresh(row)
    return {
        'message': '卡券更新成功',
        'item': serialize_card(row),
        'card': serialize_card(row),
    }


@app.delete('/cards/{card_id}')
def delete_card(card_id: int, user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_card_or_404(db, user, card_id)
    db.delete(row)
    db.commit()
    return {
        'message': '卡券删除成功',
        'success': True,
    }


@app.get('/cdkeys')
def list_cdkeys(user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):

    rows = owner_scoped_cdkey_query(db, user).order_by(models.JudianCdKey.created_at.desc(), models.JudianCdKey.id.desc()).all()
    return {
        'items': [serialize_cdkey(row) for row in rows],
        'total': len(rows),
    }


@app.get('/cdkeys/claim')
def claim_cdkeys_by_query(
    request: Request,
    accountId: str | None = None,
    cardId: int | None = None,
    count: int = 1,
    markStatus: str = 'active',
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return claim_cdkeys_for_delivery(
        request,
        db,
        user,
        account_id=str(accountId or '').strip(),
        card_id=cardId,
        count=count,
        mark_status=markStatus,
    )


@app.post('/cdkeys/claim')
def claim_cdkeys_by_body(
    body: JudianCdKeyClaimRequest,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return claim_cdkeys_for_delivery(
        request,
        db,
        user,
        account_id=str(body.accountId or '').strip(),
        card_id=body.cardId,
        count=body.count,
        mark_status=str(body.markStatus or 'active'),
    )


@app.get('/cdkeys/claim/text', response_class=PlainTextResponse)
def claim_cdkeys_text_by_query(
    request: Request,
    accountId: str | None = None,
    cardId: int | None = None,
    count: int = 1,
    markStatus: str = 'active',
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = claim_cdkeys_for_delivery(
        request,
        db,
        user,
        account_id=str(accountId or '').strip(),
        card_id=cardId,
        count=count,
        mark_status=markStatus,
    )
    return str(result.get('deliveryContent') or '').strip()


@app.post('/cdkeys/claim/text', response_class=PlainTextResponse)
def claim_cdkeys_text_by_body(
    body: JudianCdKeyClaimRequest,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = claim_cdkeys_for_delivery(
        request,
        db,
        user,
        account_id=str(body.accountId or '').strip(),
        card_id=body.cardId,
        count=body.count,
        mark_status=str(body.markStatus or 'active'),
    )
    return str(result.get('deliveryContent') or '').strip()


@app.post('/cdkeys/import')
def import_cdkeys(
    body: JudianCdKeyImportRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = str(body.accountId or '').strip()
    if not account_id:
        raise HTTPException(status_code=400, detail='请选择需要绑定的聚点账号')

    account = owner_scoped_account_query(db, user).filter_by(account_id=account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail='绑定的聚点账号不存在')
    if not bool(account.enabled):
        raise HTTPException(status_code=400, detail='当前聚点账号已停用，无法导入卡密')

    # 解析 codes 列表
    codes: list[str] = []
    if body.codes:
        codes.extend([str(x or '').strip() for x in body.codes])
    content = str(body.content or '').strip()
    if content:
        for line in content.splitlines():
            code = line.strip().replace('\u3000', ' ')
            if code:
                codes.append(code)
    # 去重
    seen = set()
    codes = [c for c in codes if c and not (c in seen or seen.add(c))]
    if not codes:
        raise HTTPException(status_code=400, detail='请提供待导入的卡密列表')

    duration = max(1, min(365, int(body.duration or 1)))
    max_uses = max(0, int(body.maxUses or 0))
    remark = str(body.remark or '').strip()
    card_id = body.cardId

    now = now_text()
    owner_username = str(account.owner_username or user.get('username') or '').strip()

    created = 0
    skipped = 0
    items: list[models.JudianCdKey] = []

    for code in codes:
        exists = db.query(models.JudianCdKey).filter_by(code=code).first()
        if exists is not None:
            skipped += 1
            continue
        row = models.JudianCdKey(
            code=code,
            owner_username=owner_username,
            account_id=account_id,
            card_id=card_id,
            duration=duration,
            status='unused',
            max_uses=max_uses,
            use_count=0,
            expires_at=None,
            latest_session_id='',
            latest_order_id='',
            remark=remark,
            created_at=now,
            updated_at=now,
            payload={},
        )
        db.add(row)
        items.append(row)
        created += 1

    db.commit()
    for row in items:
        db.refresh(row)

    return {
        'message': f'导入完成：新增 {created}，跳过 {skipped}',
        'created': created,
        'skipped': skipped,
        'items': [serialize_cdkey(row) for row in items],
        'total': created,
    }


@app.post('/cdkeys/import/netdisk')
def import_cdkeys_from_netdisk(
    body: JudianCdKeyImportFromNetdiskRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = str(body.accountId or '').strip()
    if not account_id:
        raise HTTPException(status_code=400, detail='请选择需要绑定的聚点账号')

    account = owner_scoped_account_query(db, user).filter_by(account_id=account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail='绑定的聚点账号不存在')
    if not bool(account.enabled):
        raise HTTPException(status_code=400, detail='当前聚点账号已停用，无法导入卡密')

    duration = max(1, min(365, int(body.duration or 1)))
    max_uses = max(0, int(body.maxUses or 0))
    remark = str(body.remark or '').strip()
    card_id = body.cardId

    # 从网盘系统读取未使用卡密
    query = db.query(models.CdKey).filter(models.CdKey.status == 0)  # 0=未使用
    if isinstance(body.limit, int) and body.limit > 0:
        query = query.limit(int(body.limit))
    source_rows = query.all()

    now = now_text()
    owner_username = str(account.owner_username or user.get('username') or '').strip()
    created = 0
    skipped = 0
    items: list[models.JudianCdKey] = []

    for src in source_rows:
        code = str(src.key_code or '').strip()
        if not code:
            continue
        exists = db.query(models.JudianCdKey).filter_by(code=code).first()
        if exists is not None:
            skipped += 1
            continue
        row = models.JudianCdKey(
            code=code,
            owner_username=owner_username,
            account_id=account_id,
            card_id=card_id,
            duration=duration,
            status='unused',
            max_uses=max_uses,
            use_count=0,
            expires_at=None,
            latest_session_id='',
            latest_order_id='',
            remark=remark,
            created_at=now,
            updated_at=now,
            payload={},
        )
        db.add(row)
        items.append(row)
        created += 1

    db.commit()
    for row in items:
        db.refresh(row)

    return {
        'message': f'导入完成：新增 {created}，跳过 {skipped}',
        'created': created,
        'skipped': skipped,
        'items': [serialize_cdkey(row) for row in items],
        'total': created,
    }


@app.post('/cards/{card_id}/import/judian')
def import_card_codes_from_judian(
    card_id: int,
    body: JudianCardCodesImportFromJudianRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 校验卡片归属
    card = owner_scoped_card_query(db, user).filter_by(id=int(card_id)).first()
    if card is None:
        raise HTTPException(status_code=404, detail='发货模板不存在')
    if not bool(card.enabled):
        raise HTTPException(status_code=400, detail='当前发货模板已停用，无法导入')

    # 读取聚点卡密（默认仅未使用）
    query = owner_scoped_cdkey_query(db, user)
    if body.accountId:
        query = query.filter_by(account_id=str(body.accountId).strip())
    status_text = str(body.status or 'unused').strip().lower()
    if status_text in {'unused', 'active', 'expired', 'void'}:
        query = query.filter(models.JudianCdKey.status == status_text)
    limit = int(body.limit or 500)
    if limit > 0:
        query = query.limit(limit)
    source_rows = query.all()

    # 合并到 card.data_content.codes 数组
    data_content = dict_like(card.data_content)
    existing_codes = set(map(str, (data_content.get('codes') or [])))
    appended = 0
    for src in source_rows:
        code = str(src.code or '').strip()
        if not code or code in existing_codes:
            continue
        existing_codes.add(code)
        appended += 1
    data_content['codes'] = list(existing_codes)
    data_content['source'] = 'judian'
    data_content['updatedAt'] = now_text()
    card.data_content = data_content
    card.updated_at = now_text()

    db.commit()
    db.refresh(card)
    return {
        'message': f'已从聚点卡密导入到发货模板内容：新增 {appended} 个卡密',
        'appended': appended,
        'card': serialize_card(card),
    }


@app.post('/cards/{card_id}/import/netdisk')
def import_card_codes_from_netdisk(
    card_id: int,
    body: JudianCardCodesImportFromNetdiskRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 校验卡片归属
    card = owner_scoped_card_query(db, user).filter_by(id=int(card_id)).first()
    if card is None:
        raise HTTPException(status_code=404, detail='发货模板不存在')
    if not bool(card.enabled):
        raise HTTPException(status_code=400, detail='当前发货模板已停用，无法导入')

    # 读取网盘未使用卡密
    query = db.query(models.CdKey).filter(models.CdKey.status == 0)
    limit = int(body.limit or 500)
    if limit > 0:
        query = query.limit(limit)
    source_rows = query.all()

    # 合并到 card.data_content.codes 数组
    data_content = dict_like(card.data_content)
    existing_codes = set(map(str, (data_content.get('codes') or [])))
    appended = 0
    for src in source_rows:
        code = str(src.key_code or '').strip()
        if not code or code in existing_codes:
            continue
        existing_codes.add(code)
        appended += 1
    data_content['codes'] = list(existing_codes)
    data_content['source'] = 'netdisk'
    data_content['updatedAt'] = now_text()
    card.data_content = data_content
    card.updated_at = now_text()

    db.commit()
    db.refresh(card)
    return {
        'message': f'已导入到发货模板内容：新增 {appended} 个卡密',
        'appended': appended,
        'card': serialize_card(card),
    }


@app.post('/cdkeys')
def generate_cdkeys(
    body: JudianCdKeyGenerateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = str(body.accountId or '').strip()
    if not account_id:
        raise HTTPException(status_code=400, detail='请选择需要绑定的聚点账号')

    account = owner_scoped_account_query(db, user).filter_by(account_id=account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail='绑定的聚点账号不存在')
    if not bool(account.enabled):
        raise HTTPException(status_code=400, detail='当前聚点账号已停用，无法生成卡密')

    duration = max(1, min(365, int(body.duration or 30)))
    count = max(1, min(50, int(body.count or 1)))
    max_uses = max(0, int(body.maxUses or 0))
    remark = str(body.remark or '').strip()
    now = now_text()
    owner_username = str(account.owner_username or user.get('username') or '').strip()
    rows: list[models.JudianCdKey] = []

    for _ in range(count):
        row = models.JudianCdKey(
            code=generate_cdkey_code(db),
            owner_username=owner_username,
            account_id=account_id,
            duration=duration,
            status='unused',
            max_uses=max_uses,
            use_count=0,
            expires_at=None,

            latest_session_id='',
            latest_order_id='',
            remark=remark,
            created_at=now,
            updated_at=now,
            payload={},
        )
        db.add(row)
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return {
        'message': f'已生成 {len(rows)} 张聚点卡密',
        'items': [serialize_cdkey(row) for row in rows],
        'total': len(rows),
    }


@app.put('/cdkeys/{row_id}')
def update_cdkey(
    row_id: int,
    body: JudianCdKeyUpdateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_cdkey_or_404(db, user, row_id)
    if body.status is not None:
        next_status = str(body.status or '').strip().lower()
        if next_status not in {'unused', 'active', 'expired', 'void'}:
            raise HTTPException(status_code=400, detail='聚点卡密状态不合法')
        row.status = next_status
    if body.remark is not None:
        row.remark = str(body.remark or '').strip()
    row.updated_at = now_text()
    db.commit()
    db.refresh(row)
    return {
        'message': '聚点卡密更新成功',
        'item': serialize_cdkey(row),
    }


@app.delete('/cdkeys/inactive')
def clean_inactive_cdkeys(user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = owner_scoped_cdkey_query(db, user).filter(models.JudianCdKey.status.in_(['expired', 'void'])).all()
    removed = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return {
        'message': f'已清理 {removed} 张失效卡密',
        'removed': removed,
        'success': True,
    }



@app.post('/accounts/login')
def login_account(
    body: JudianAccountLoginRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    login_email = str(body.loginEmail or '').strip()
    login_password = str(body.loginPassword or '').strip()
    display_name = str(body.displayName or '').strip()
    remark = str(body.remark or '').strip()

    if not login_email or '@' not in login_email:
        raise HTTPException(status_code=400, detail='请输入正确的聚点登录邮箱')
    if not login_password:
        raise HTTPException(status_code=400, detail='请输入聚点登录密码')

    row = None
    if body.id is not None:
        row = get_account_or_404(db, user, body.id)
    else:
        row = find_existing_account_by_login_email(db, user, login_email)


    try:
        saved = apply_remote_login_result(
            db,
            row,
            owner_username=str(user.get('username') or '').strip(),
            login_email=login_email,
            login_password=login_password,
            display_name=display_name,
            remark=remark,
        )
    except JudianRemoteError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        'message': '聚点账号登录成功',
        'item': serialize_account(saved),
    }


@app.post('/accounts/{row_id}/relogin')
def relogin_account(
    row_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_account_or_404(db, user, row_id)
    login_email = resolve_account_login_email(row)
    login_password = resolve_account_login_password(row)
    if not login_email or not login_password:
        raise HTTPException(status_code=400, detail='当前账号未保存可用的账密信息，无法重新登录')


    try:
        saved = apply_remote_login_result(
            db,
            row,
            owner_username=row.owner_username,
            login_email=login_email,
            login_password=login_password,
            display_name=str(row.display_name or '').strip(),
            remark=str(row.remark or '').strip(),
        )
    except JudianRemoteError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        'message': '聚点账号已重新登录',
        'item': serialize_account(saved),
    }



@app.put('/accounts/{row_id}')
def update_account(
    row_id: int,
    body: JudianAccountUpdateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_account_or_404(db, user, row_id)

    if body.loginEmail is not None:
        login_email = str(body.loginEmail or '').strip()
        if not login_email or '@' not in login_email:
            raise HTTPException(status_code=400, detail='请输入正确的聚点登录邮箱')
        row.login_email = login_email
    if body.loginPassword is not None:
        row.login_password = str(body.loginPassword or '').strip()
    if body.displayName is not None:
        next_display_name = str(body.displayName or '').strip()
        row.display_name = next_display_name or row.display_name or row.login_email.split('@')[0]
    if body.remark is not None:
        row.remark = str(body.remark or '').strip()
    if body.enabled is not None:
        row.enabled = bool(body.enabled)
        row.status = 'disabled' if not row.enabled else ('active' if str(row.session_token or '').strip() else 'pending')

    row.updated_at = now_text()
    db.commit()
    db.refresh(row)
    return {
        'message': '聚点账号更新成功',
        'item': serialize_account(row),
    }


@app.delete('/accounts/{row_id}')
def delete_account(
    row_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_account_or_404(db, user, row_id)
    db.delete(row)
    db.commit()
    return {
        'message': '聚点账号已删除',
        'success': True,
    }


async def startup_judian_runtime() -> None:
    ensure_judian_schema()
    return None


async def shutdown_judian_runtime() -> None:
    return None
