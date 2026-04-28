from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable

from loguru import logger as _logger

_CONFIG_LOCK = Lock()
_CONFIGURED = False
_RUNTIME_CONFIG: Dict[str, Any] = {}

_DEFAULT_NOISY_KEYWORDS = (
    "WebSocket目标地址:",
    "WebSocket连接建立成功，开始初始化...",
    "WebSocket初始化完成！",
    "准备启动后台任务 - 当前状态:",
    "启动心跳任务...",
    "启动Token刷新任务...",
    "启动暂停记录清理任务...",
    "启动Cookie刷新任务...",
    "✅ 所有后台任务状态:",
    "开始监听WebSocket消息...",
    "WebSocket连接状态正常，等待服务器消息...",
    "准备进入消息循环...",
    "已进入心跳阶段，开始等待心跳收发",
    "心跳循环收到取消信号",
    "心跳循环在重试等待时收到取消信号",
    "心跳循环已取消，正在退出...",
    "心跳循环已退出",
    "Cookie刷新循环收到取消信号",
    "Cookie刷新循环在重试等待时收到取消信号",
    "Cookie刷新循环已取消，正在退出...",
    "Cookie刷新循环已退出",
    "开始执行Cookie刷新任务...",
    "开始Cookie刷新任务，暂时暂停心跳以避免连接冲突...",
    "开始验证Cookie有效性（使用真实API调用）...",
    "测试图片上传API（使用测试图片实际上传）...",
    "已创建测试图片:",
    "重新启动心跳任务",
)


class InterceptHandler(logging.Handler):
    """Forward stdlib logging records to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _normalize_level(value: Any, default: str) -> str:
    text = str(value or default).strip().upper()
    if text in {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}:
        return text
    return default


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_log_root(config: Dict[str, Any]) -> Path:
    raw_path = (
        config.get("root_dir")
        or config.get("dir")
        or os.getenv("LOG_DIR")
        or "logs"
    )
    root = Path(str(raw_path))
    if not root.is_absolute():
        root = Path.cwd() / root
    return root.resolve()


def _build_runtime_config(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    user_config = dict(config or {})
    default_level = _normalize_level(user_config.get("level"), "INFO")
    console_level = _normalize_level(
        user_config.get("console_level") or os.getenv("LOG_LEVEL"),
        default_level,
    )

    runtime_config: Dict[str, Any] = {
        "level": default_level,
        "console_level": console_level,
        "error_level": _normalize_level(user_config.get("error_level"), "ERROR"),
        "rotation": str(user_config.get("rotation") or "1 day"),
        "retention": str(user_config.get("retention") or "14 days"),
        "compression": user_config.get("compression") or "zip",
        "encoding": str(user_config.get("encoding") or "utf-8"),
        "enqueue": _as_bool(user_config.get("enqueue"), True),
        "console_quiet_noisy": _as_bool(user_config.get("console_quiet_noisy"), True),
        "quiet_uvicorn_access": _as_bool(user_config.get("quiet_uvicorn_access"), False),
        "info_filename": str(user_config.get("info_filename") or "info_{time:YYYY-MM-DD}.log"),
        "error_filename": str(user_config.get("error_filename") or "error_{time:YYYY-MM-DD}.log"),
        "console_format": user_config.get(
            "console_format",
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[component]}</cyan> | "
            "<blue>{file.name}</blue>:<blue>{function}</blue>:<blue>{line}</blue> | "
            "<magenta>{thread.name}:{thread.id}</magenta> - "
            "<level>{message}</level>",
        ),
        "file_format": user_config.get(
            "file_format",
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{extra[component]} | {file.name}:{function}:{line} | "
            "{process.name}:{process.id} | {thread.name}:{thread.id} - {message}",
        ),
    }
    runtime_config["root_dir"] = _resolve_log_root(user_config)
    runtime_config["info_dir"] = runtime_config["root_dir"] / "info"
    runtime_config["error_dir"] = runtime_config["root_dir"] / "error"
    return runtime_config


def _record_patcher(record: Dict[str, Any]) -> None:
    component = str(record["extra"].get("component") or "").strip()
    record["extra"]["component"] = component or record.get("name") or "app"


def _safe_console_sink(message: Any) -> None:
    text = str(message)
    stream = sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
    stream.flush()


def _should_emit_console_log(record: Dict[str, Any]) -> bool:
    if record["level"].no >= logging.WARNING:
        return True

    if _RUNTIME_CONFIG.get("quiet_uvicorn_access") and record["name"].startswith("uvicorn.access"):
        return False

    if not _RUNTIME_CONFIG.get("console_quiet_noisy", True):
        return True

    message = str(record["message"])
    return not any(keyword in message for keyword in _DEFAULT_NOISY_KEYWORDS)


def _configure_stdlib_logging(level: str) -> None:
    intercept_handler = InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(level)

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "asyncio",
        "httpx",
    ):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers = [intercept_handler]
        std_logger.propagate = False
        std_logger.setLevel(level)


def configure_logging(config: Dict[str, Any] | None = None, force: bool = False) -> Dict[str, Any]:
    global _CONFIGURED

    with _CONFIG_LOCK:
        if _CONFIGURED and not force:
            return dict(_RUNTIME_CONFIG)

        runtime_config = _build_runtime_config(config)
        runtime_config["info_dir"].mkdir(parents=True, exist_ok=True)
        runtime_config["error_dir"].mkdir(parents=True, exist_ok=True)

        _logger.remove()
        _logger.configure(extra={"component": "app"}, patcher=_record_patcher)

        _logger.add(
            _safe_console_sink,
            level=runtime_config["console_level"],
            format=runtime_config["console_format"],
            colorize=True,
            enqueue=runtime_config["enqueue"],
            backtrace=False,
            diagnose=False,
            filter=_should_emit_console_log,
        )
        _logger.add(
            str(runtime_config["info_dir"] / runtime_config["info_filename"]),
            level=runtime_config["level"],
            rotation=runtime_config["rotation"],
            retention=runtime_config["retention"],
            compression=runtime_config["compression"],
            format=runtime_config["file_format"],
            encoding=runtime_config["encoding"],
            enqueue=runtime_config["enqueue"],
            backtrace=False,
            diagnose=False,
        )
        _logger.add(
            str(runtime_config["error_dir"] / runtime_config["error_filename"]),
            level=runtime_config["error_level"],
            rotation=runtime_config["rotation"],
            retention=runtime_config["retention"],
            compression=runtime_config["compression"],
            format=runtime_config["file_format"],
            encoding=runtime_config["encoding"],
            enqueue=runtime_config["enqueue"],
            backtrace=True,
            diagnose=False,
        )

        _configure_stdlib_logging(runtime_config["level"])
        _RUNTIME_CONFIG.clear()
        _RUNTIME_CONFIG.update(runtime_config)
        _CONFIGURED = True
        return dict(_RUNTIME_CONFIG)


def get_logger(component: str | None = None):
    if component:
        return _logger.bind(component=component)
    return _logger


def get_logging_config() -> Dict[str, Any]:
    if _CONFIGURED:
        return dict(_RUNTIME_CONFIG)
    return _build_runtime_config()


def get_log_root() -> Path:
    return Path(get_logging_config()["root_dir"])


def get_log_dir(level: str = "info") -> Path:
    normalized_level = str(level or "info").strip().lower()
    config = get_logging_config()
    return Path(config["error_dir"] if normalized_level == "error" else config["info_dir"])


def list_log_files(level: str | None = None, include_archives: bool = True) -> list[Path]:
    levels: Iterable[str] = (str(level).strip().lower(),) if level else ("info", "error")
    files: list[Path] = []

    for item in levels:
        log_dir = get_log_dir(item)
        if not log_dir.exists():
            continue
        for path in log_dir.iterdir():
            if not path.is_file():
                continue
            if path.suffix == ".log" or (include_archives and path.suffix == ".zip"):
                files.append(path)

    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files


def find_latest_log_file(level: str = "info") -> Path | None:
    for path in list_log_files(level=level, include_archives=False):
        if path.suffix == ".log":
            return path
    return None


def get_log_relative_path(path: str | Path) -> str:
    target = Path(path).resolve()
    return target.relative_to(get_log_root()).as_posix()


def resolve_log_file(file_name: str) -> Path:
    if not file_name:
        raise FileNotFoundError("missing log file name")

    log_root = get_log_root()
    requested = Path(file_name)
    if requested.is_absolute():
        target = requested.resolve()
    else:
        target = (log_root / requested).resolve()

    try:
        target.relative_to(log_root)
        if target.exists() and target.is_file():
            return target
    except ValueError:
        pass

    basename = requested.name
    matches = [path for path in list_log_files(include_archives=True) if path.name == basename]
    if len(matches) == 1:
        return matches[0]

    raise FileNotFoundError(file_name)
