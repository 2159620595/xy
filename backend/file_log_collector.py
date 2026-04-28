#!/usr/bin/env python3
"""
基于文件监控的日志收集器
"""

import os
import re
import time
import threading
from collections import deque
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from app_logging import find_latest_log_file, get_log_relative_path, get_logger

logger = get_logger("file_log_collector")

class FileLogCollector:
    """基于文件监控的日志收集器"""

    LOG_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| "
        r"(?P<level>\w+)\s*\| "
        r"(?P<source>[^|]+?) \| "
        r"(?P<file>[^:]+):(?P<function>[^:]+):(?P<line>\d+) \| "
        r"(?P<process>[^|]+?) \| "
        r"(?P<thread>[^-]+?) - "
        r"(?P<message>.*)"
    )

    def __init__(self, max_logs: int = 2000):
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.Lock()

        # 当前监控的 info 日志文件
        self.log_file: str | None = None
        self.last_position = 0

        # 启动文件监控
        self.setup_file_monitoring()

    def setup_file_monitoring(self):
        """设置文件监控"""
        self.refresh_log_file(reset_position=True)

        # 启动文件监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_file, daemon=True)
        self.monitor_thread.start()

    def refresh_log_file(self, reset_position: bool = False) -> None:
        latest_log_file = find_latest_log_file("info")
        latest_log_path = str(latest_log_file) if latest_log_file else None

        if latest_log_path != self.log_file:
            self.log_file = latest_log_path
            self.last_position = 0
            if self.log_file:
                logger.debug(f"日志收集器切换到文件: {self.log_file}")
            return

        if reset_position:
            self.last_position = 0

    def monitor_file(self):
        """监控日志文件变化"""
        while True:
            try:
                self.refresh_log_file()
                if self.log_file and os.path.exists(self.log_file):
                    # 获取文件大小
                    file_size = os.path.getsize(self.log_file)

                    if file_size < self.last_position:
                        self.last_position = 0

                    if file_size > self.last_position:
                        # 读取新增内容
                        with open(self.log_file, 'r', encoding='utf-8') as f:
                            f.seek(self.last_position)
                            new_lines = f.readlines()
                            self.last_position = f.tell()

                        # 解析新增的日志行
                        for line in new_lines:
                            self.parse_log_line(line.strip())

                time.sleep(0.5)  # 每0.5秒检查一次

            except Exception:
                time.sleep(1)  # 出错时等待1秒

    def parse_log_line(self, line: str):
        """解析日志行"""
        if not line:
            return

        try:
            match = self.LOG_PATTERN.match(line)
            if match:
                payload = match.groupdict()
                try:
                    timestamp = datetime.strptime(payload["timestamp"], '%Y-%m-%d %H:%M:%S.%f')
                except Exception:
                    timestamp = datetime.now()

                log_entry = {
                    "timestamp": timestamp.isoformat(),
                    "level": payload["level"].strip(),
                    "source": payload["source"].strip(),
                    "file": payload["file"].strip(),
                    "function": payload["function"].strip(),
                    "line": int(payload["line"]),
                    "process": payload["process"].strip(),
                    "thread": payload["thread"].strip(),
                    "message": payload["message"],
                }

                with self.lock:
                    self.logs.append(log_entry)

                return

        except Exception:
            pass

        try:
            # 如果解析失败，作为普通消息处理
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "source": "system",
                "file": "",
                "function": "unknown",
                "line": 0,
                "process": "",
                "thread": "",
                "message": line
            }

            with self.lock:
                self.logs.append(log_entry)

        except Exception:
            pass

    def get_logs(self, lines: int = 200, level_filter: str = None, source_filter: str = None) -> List[Dict]:
        """获取日志记录"""
        with self.lock:
            logs_list = list(self.logs)

        # 应用过滤器
        if level_filter:
            normalized_level = str(level_filter).upper()
            logs_list = [log for log in logs_list if log['level'] == normalized_level]

        if source_filter:
            logs_list = [log for log in logs_list if source_filter.lower() in log['source'].lower()]

        # 返回最后N行
        return logs_list[-lines:] if len(logs_list) > lines else logs_list

    def clear_logs(self):
        """清空日志"""
        with self.lock:
            self.logs.clear()

    def get_stats(self) -> Dict:
        """获取日志统计信息"""
        with self.lock:
            total_logs = len(self.logs)

            # 统计各级别日志数量
            level_counts = {}
            source_counts = {}

            for log in self.logs:
                level = log['level']
                source = log['source']

                level_counts[level] = level_counts.get(level, 0) + 1
                source_counts[source] = source_counts.get(source, 0) + 1

            relative_log_file = None
            if self.log_file:
                try:
                    relative_log_file = get_log_relative_path(self.log_file)
                except Exception:
                    relative_log_file = self.log_file

            return {
                "total_logs": total_logs,
                "level_counts": level_counts,
                "source_counts": source_counts,
                "max_capacity": self.max_logs,
                "log_file": relative_log_file
            }


# 全局文件日志收集器实例
_file_collector = None
_file_collector_lock = threading.Lock()


def get_file_log_collector() -> FileLogCollector:
    """获取全局文件日志收集器实例"""
    global _file_collector
    
    if _file_collector is None:
        with _file_collector_lock:
            if _file_collector is None:
                _file_collector = FileLogCollector(max_logs=2000)
    
    return _file_collector


def setup_file_logging():
    """设置文件日志系统"""
    collector = get_file_log_collector()
    logger.info("文件日志收集器已启动")
    return collector


if __name__ == "__main__":
    # 测试文件日志收集器
    collector = setup_file_logging()
    
    # 生成一些测试日志
    from loguru import logger
    
    logger.info("文件日志收集器测试开始")
    logger.debug("这是调试信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.info("文件日志收集器测试结束")
    
    # 等待文件写入和监控
    time.sleep(2)
    
    # 获取日志
    logs = collector.get_logs(10)
    print(f"收集到 {len(logs)} 条日志:")
    for log in logs:
        print(f"  [{log['level']}] {log['source']}: {log['message']}")
    
    # 获取统计信息
    stats = collector.get_stats()
    print(f"\n统计信息: {stats}")
