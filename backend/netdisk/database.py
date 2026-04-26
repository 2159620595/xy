import os
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    try:
        parsed_value = int(raw_value) if raw_value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed_value if parsed_value > 0 else default


def _read_database_url() -> tuple[str, str]:
    """整合生态优先读取生态库配置，再兼容旧版单库模式。"""
    for env_name in ("DATABASE_URL_ECO", "DATABASE_URL"):
        value = (os.environ.get(env_name) or "").strip()
        if value:
            return value, env_name
    raise ValueError(
        "环境变量 DATABASE_URL_ECO 或 DATABASE_URL 未配置！请至少提供一个 PostgreSQL 连接串。"
    )


# 使用环境变量配置 PostgreSQL，整合生态优先走独立生态库
POSTGRES_URL, POSTGRES_ENV_NAME = _read_database_url()

# 兼容 SQLAlchemy 对 postgres:// 的解析要求
if POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif POSTGRES_URL.startswith("postgresql://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

SQLALCHEMY_DATABASE_URL = POSTGRES_URL
DB_POOL_SIZE = _read_positive_int("DB_POOL_SIZE", 10)
DB_MAX_OVERFLOW = _read_positive_int("DB_MAX_OVERFLOW", 20)
DB_POOL_TIMEOUT = _read_positive_int("DB_POOL_TIMEOUT", 5)
DB_CONNECT_TIMEOUT = _read_positive_int("DB_CONNECT_TIMEOUT", 5)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    connect_args={"connect_timeout": DB_CONNECT_TIMEOUT},
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_database_ready = True
_database_unavailable_reason = ""


def mark_database_ready() -> None:
    global _database_ready, _database_unavailable_reason
    _database_ready = True
    _database_unavailable_reason = ""



def mark_database_unavailable(reason: str | None = None) -> None:
    global _database_ready, _database_unavailable_reason
    _database_ready = False
    _database_unavailable_reason = str(reason or "").strip()



def is_database_ready() -> bool:
    return _database_ready



def get_database_unavailable_reason() -> str:
    return _database_unavailable_reason



def ensure_database_ready() -> None:
    if _database_ready:
        return
    detail = _database_unavailable_reason or "网盘数据库暂不可用，请稍后重试"
    raise HTTPException(status_code=503, detail=detail)



def get_db():
    ensure_database_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
