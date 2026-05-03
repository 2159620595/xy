#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闲鱼滑块验证 - 增强反检测版本 v3
基于最新的反检测技术，专门针对闲鱼、淘宝、阿里平台的滑块验证

【v3 核心修复与新增】

★ BUG 修复（关键！导致只滑到 71% 的根本原因）
  _generate_physics_trajectory 原来直接用 speed_factor 乘以单步理论长度，
  但三段速度曲线各段均值远小于 1.0，导致累计位移只有目标的 ~71%。
  v3 改为：先生成归一化速度权重（sum=1.0），再统一乘以目标距离，
  保证累计 x 严格等于 distance（误差 < 0.1px）。

★ 新增 PyAutoGUI + 贝塞尔曲线备用拖拽引擎
  当 Playwright 连续失败时自动切换到 PyAutoGUI 直接操作系统鼠标，
  完全绕过浏览器自动化协议层检测。
  贝塞尔曲线：使用三阶/四阶控制点生成更自然的鼠标路径。
  安装: pip install pyautogui

★ 新增 OpenCV 滑块缺口识别（可选增强）
  对验证码截图做边缘检测 + 模板匹配，精确定位缺口 x 坐标，
  比固定计算"轨道宽 - 按钮宽"更准确。
  安装: pip install opencv-python

★ 轨迹归一化修复（v2 遗留 bug）
  - 速度权重归一化，累计距离保证精确
  - 超调量上限从 distance*0.06 改为固定 max 8px，防止大距离时超调过大

★ patchright 优先（继承 v2）
  安装: pip install patchright && python -m patchright install chromium

★ UA 更新至 Chrome 134-136（继承 v2）

★ WebGL / AudioContext / Canvas 指纹伪装（继承 v2）
"""

import time
import random
import json
import os
import math
import traceback
import threading
import tempfile
import shutil
import io
import base64
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Callable
from loguru import logger
from collections import defaultdict

# ── OpenCV（可选，用于缺口识别） ──────────────────────────────────────────
try:
    import cv2
    import numpy as np
    _OPENCV_AVAILABLE = True
except ImportError:
    _OPENCV_AVAILABLE = False
    logger.warning("OpenCV 未安装，缺口识别功能不可用。pip install opencv-python")

# ── PyAutoGUI（可选，用于系统级鼠标备用拖拽） ─────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = False   # 关闭移到角落报错
    pyautogui.PAUSE    = 0       # 关闭全局步间延迟（手动控制）
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False
    logger.warning("PyAutoGUI 未安装，系统鼠标备用引擎不可用。pip install pyautogui")

# ========================================================
# 优先使用 patchright（原生修复 Runtime.enable 泄漏和自动化指纹）
# 若未安装则回退到标准 playwright
# 安装: pip install patchright && python -m patchright install chromium
# ========================================================
try:
    from patchright.sync_api import sync_playwright, ElementHandle
    _USING_PATCHRIGHT = True
    # patchright 在启动时会打印版本信息，静默处理
except ImportError:
    from playwright.sync_api import sync_playwright, ElementHandle
    _USING_PATCHRIGHT = False

# 导入配置
try:
    from config import SLIDER_VERIFICATION
    SLIDER_MAX_CONCURRENT = SLIDER_VERIFICATION.get('max_concurrent', 3)
    SLIDER_WAIT_TIMEOUT = SLIDER_VERIFICATION.get('wait_timeout', 60)
except ImportError:
    # 如果无法导入配置，使用默认值
    SLIDER_MAX_CONCURRENT = 3
    SLIDER_WAIT_TIMEOUT = 60

# 使用loguru日志库，与主程序保持一致


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_verbose_slider_logging_enabled() -> bool:
    return _as_bool(os.getenv("VERBOSE_SLIDER_LOGGING"), False)


def _log_slider_traceback(user_id: str, context: str) -> None:
    if _is_verbose_slider_logging_enabled():
        logger.debug(f"【{user_id}】{context}详细堆栈:\n{traceback.format_exc()}")
        return

    logger.debug(
        f"【{user_id}】{context}详细堆栈已省略；设置 VERBOSE_SLIDER_LOGGING=1 可查看完整堆栈"
    )

# 全局并发控制
class SliderConcurrencyManager:
    """滑块验证并发管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.max_concurrent = SLIDER_MAX_CONCURRENT  # 从配置文件读取最大并发数
            self.wait_timeout = SLIDER_WAIT_TIMEOUT  # 从配置文件读取等待超时时间
            self.active_instances = {}  # 活跃实例
            self.waiting_queue = []  # 等待队列
            self.instance_lock = threading.Lock()
            self._initialized = True
            logger.info(f"滑块验证并发管理器初始化: 最大并发数={self.max_concurrent}, 等待超时={self.wait_timeout}秒")
    
    def can_start_instance(self, user_id: str) -> bool:
        """检查是否可以启动新实例"""
        with self.instance_lock:
            return len(self.active_instances) < self.max_concurrent
    
    def wait_for_slot(self, user_id: str, timeout: int = None) -> bool:
        """等待可用槽位"""
        if timeout is None:
            timeout = self.wait_timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.instance_lock:
                if len(self.active_instances) < self.max_concurrent:
                    return True
            
            # 检查是否在等待队列中
            with self.instance_lock:
                if user_id not in self.waiting_queue:
                    self.waiting_queue.append(user_id)
                    # 提取纯用户ID用于日志显示
                    pure_user_id = self._extract_pure_user_id(user_id)
                    logger.info(f"【{pure_user_id}】进入等待队列，当前队列长度: {len(self.waiting_queue)}")
            
            # 等待1秒后重试
            time.sleep(1)
        
        # 超时后从队列中移除
        with self.instance_lock:
            if user_id in self.waiting_queue:
                self.waiting_queue.remove(user_id)
                # 提取纯用户ID用于日志显示
                pure_user_id = self._extract_pure_user_id(user_id)
                logger.warning(f"【{pure_user_id}】等待超时，从队列中移除")
        
        return False
    
    def register_instance(self, user_id: str, instance):
        """注册实例"""
        with self.instance_lock:
            self.active_instances[user_id] = {
                'instance': instance,
                'start_time': time.time()
            }
            # 从等待队列中移除
            if user_id in self.waiting_queue:
                self.waiting_queue.remove(user_id)
    
    def unregister_instance(self, user_id: str):
        """注销实例"""
        with self.instance_lock:
            if user_id in self.active_instances:
                del self.active_instances[user_id]
                # 提取纯用户ID用于日志显示
                pure_user_id = self._extract_pure_user_id(user_id)
                logger.info(f"【{pure_user_id}】实例已注销，当前活跃: {len(self.active_instances)}")
    
    def _extract_pure_user_id(self, user_id: str) -> str:
        """提取纯用户ID（移除时间戳部分）"""
        if '_' in user_id:
            # 检查最后一部分是否为数字（时间戳）
            parts = user_id.split('_')
            if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) >= 10:
                # 最后一部分是时间戳，移除它
                return '_'.join(parts[:-1])
            else:
                # 不是时间戳格式，使用原始ID
                return user_id
        else:
            # 没有下划线，直接使用
            return user_id
    
    def get_stats(self):
        """获取统计信息"""
        with self.instance_lock:
            return {
                'active_count': len(self.active_instances),
                'max_concurrent': self.max_concurrent,
                'available_slots': self.max_concurrent - len(self.active_instances),
                'queue_length': len(self.waiting_queue),
                'waiting_users': self.waiting_queue.copy()
            }

# 全局并发管理器实例
concurrency_manager = SliderConcurrencyManager()

# 策略统计管理器
class RetryStrategyStats:
    """重试策略成功率统计管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.stats_lock = threading.Lock()
            self.strategy_stats = {
                'attempt_1_default': {'total': 0, 'success': 0, 'fail': 0},
                'attempt_2_cautious': {'total': 0, 'success': 0, 'fail': 0},
                'attempt_3_fast': {'total': 0, 'success': 0, 'fail': 0},
                'attempt_3_slow': {'total': 0, 'success': 0, 'fail': 0},
            }
            self.stats_file = 'trajectory_history/strategy_stats.json'
            self._load_stats()
            self._initialized = True
            logger.info("策略统计管理器初始化完成")
    
    def _load_stats(self):
        """从文件加载统计数据"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    self.strategy_stats.update(loaded_stats)
                logger.info(f"已加载历史策略统计数据: {self.stats_file}")
        except Exception as e:
            logger.warning(f"加载策略统计数据失败: {e}")
    
    def _save_stats(self):
        """保存统计数据到文件"""
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.strategy_stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存策略统计数据失败: {e}")
    
    def record_attempt(self, attempt: int, strategy_type: str, success: bool):
        """记录一次尝试结果
        
        Args:
            attempt: 尝试次数 (1, 2, 3)
            strategy_type: 策略类型 ('default', 'cautious', 'fast', 'slow')
            success: 是否成功
        """
        with self.stats_lock:
            key = f'attempt_{attempt}_{strategy_type}'
            if key not in self.strategy_stats:
                self.strategy_stats[key] = {'total': 0, 'success': 0, 'fail': 0}
            
            self.strategy_stats[key]['total'] += 1
            if success:
                self.strategy_stats[key]['success'] += 1
            else:
                self.strategy_stats[key]['fail'] += 1
            
            # 每次记录后保存
            self._save_stats()
    
    def get_stats_summary(self):
        """获取统计摘要"""
        with self.stats_lock:
            summary = {}
            for key, stats in self.strategy_stats.items():
                if stats['total'] > 0:
                    success_rate = (stats['success'] / stats['total']) * 100
                    summary[key] = {
                        'total': stats['total'],
                        'success': stats['success'],
                        'fail': stats['fail'],
                        'success_rate': f"{success_rate:.2f}%"
                    }
            return summary
    
    def log_summary(self):
        """输出统计摘要到日志"""
        summary = self.get_stats_summary()
        if summary and _is_verbose_slider_logging_enabled():
            logger.info("=" * 60)
            logger.info("📊 重试策略成功率统计")
            logger.info("=" * 60)
            for key, stats in summary.items():
                logger.info(f"{key:25s} | 总计:{stats['total']:4d} | 成功:{stats['success']:4d} | 失败:{stats['fail']:4d} | 成功率:{stats['success_rate']}")
            logger.info("=" * 60)

# 全局策略统计实例
strategy_stats = RetryStrategyStats()

class XianyuSliderStealth:
    
    def __init__(self, user_id: str = "default", enable_learning: bool = True, headless: bool = True):
        self.user_id = user_id
        self.enable_learning = enable_learning
        self.headless = headless  # 是否使用无头模式
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        
        # 提取纯用户ID（移除时间戳部分）
        self.pure_user_id = concurrency_manager._extract_pure_user_id(user_id)
        
        # 检查日期限制
        if not self._check_date_validity():
            raise Exception(f"【{self.pure_user_id}】日期验证失败，功能已过期")
        
        # 为每个实例创建独立的临时目录
        self.temp_dir = tempfile.mkdtemp(prefix=f"slider_{user_id}_")
        logger.debug(f"【{self.pure_user_id}】创建临时目录: {self.temp_dir}")
        
        # 等待可用槽位（排队机制）
        logger.info(f"【{self.pure_user_id}】检查并发限制...")
        if not concurrency_manager.wait_for_slot(self.user_id):
            stats = concurrency_manager.get_stats()
            logger.error(f"【{self.pure_user_id}】等待槽位超时，当前活跃: {stats['active_count']}/{stats['max_concurrent']}")
            raise Exception(f"滑块验证等待槽位超时，请稍后重试")
        
        # 注册实例
        concurrency_manager.register_instance(self.user_id, self)
        stats = concurrency_manager.get_stats()
        logger.info(f"【{self.pure_user_id}】实例已注册，当前并发: {stats['active_count']}/{stats['max_concurrent']}")
        
        # 轨迹学习相关属性
        
        self.success_history_file = f"trajectory_history/{self.pure_user_id}_success.json"
        self.trajectory_params = {
            "total_steps_range": [18, 28],  # 放慢节奏，避免极速直冲
            "base_delay_range": [0.03, 0.08],  # 单步停顿 30-80ms
            "jitter_x_range": [0, 2],  # 小幅横向抖动
            "jitter_y_range": [-2, 2],  # 轻微纵向抖动
            "slow_factor_range": [2, 4],  # 末段放缓
            "acceleration_phase": 0.35,  # 前段加速
            "fast_phase": 0.45,  # 中段匀速
            "slow_start_ratio_base": 1.03,  # 轻微超调后回正
            "completion_usage_rate": 0.25,
            "avg_completion_steps": 2.0,
            "trajectory_length_stats": [],
            "learning_enabled": False
        }
        
        # 保存最后一次使用的轨迹参数（用于分析优化）
        self.last_trajectory_params = {}

        if self.enable_learning:
            self.trajectory_params = self._optimize_trajectory_params()
            logger.info(f"【{self.pure_user_id}】当前轨迹参数: {self.trajectory_params}")
    
    def _check_date_validity(self) -> bool:
        """检查日期有效性 - 已禁用
        
        Returns:
            bool: 始终返回 True
        """
        return True
        
    def init_browser(self):
        """初始化浏览器 - 增强反检测版本"""
        try:
            # 启动 Playwright / Patchright
            logger.debug(f"【{self.pure_user_id}】启动{'Patchright' if _USING_PATCHRIGHT else 'Playwright'}...")
            self.playwright = sync_playwright().start()
            logger.debug(f"【{self.pure_user_id}】{'Patchright' if _USING_PATCHRIGHT else 'Playwright'} 启动成功")
            
            # 随机选择浏览器特征
            browser_features = self._get_random_browser_features()
            
            # 优先使用系统 Chromium，避免容器内回退到缺失的 Playwright 浏览器目录
            chromium_candidates = [
                os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
            ]
            chromium_executable = next(
                (path for path in chromium_candidates if path and os.path.exists(path)),
                None
            )

            launch_options = {
                "headless": self.headless,
                "ignore_default_args": ["--enable-automation"],
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--start-maximized",  # 窗口最大化
                    f"--window-size={browser_features['window_size']}",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-infobars",
                    f"--lang={browser_features['lang']}",
                    f"--accept-lang={browser_features['accept_lang']}",
                    "--disable-blink-features",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-default-browser-check",
                    "--disable-logging",
                    "--disable-permissions-api",
                    "--disable-notifications",
                    "--disable-popup-blocking",
                    "--disable-prompt-on-repost",
                    "--disable-hang-monitor",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-background-mode",
                    "--disable-domain-reliability",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-field-trial-config",
                    "--disable-background-networking",
                    "--disable-back-forward-cache",
                    "--disable-breakpad",
                    "--disable-component-update",
                    "--force-color-profile=srgb",
                    "--metrics-recording-only",
                    "--password-store=basic",
                    "--use-mock-keychain",
                    "--no-service-autorun",
                    "--export-tagged-pdf",
                    "--disable-search-engine-choice-screen",
                    "--unsafely-disable-devtools-self-xss-warnings",
                    "--edge-skip-compat-layer-relaunch",
                    "--allow-pre-commit-input"
                ]
            }
            if chromium_executable:
                launch_options["executable_path"] = chromium_executable
                logger.debug(f"【{self.pure_user_id}】使用系统Chromium: {chromium_executable}")
            else:
                logger.warning(f"【{self.pure_user_id}】未找到系统Chromium，将使用Playwright默认浏览器")

            # 启动浏览器，使用随机特征
            logger.debug(f"【{self.pure_user_id}】启动浏览器，headless模式: {self.headless}")
            self.browser = self.playwright.chromium.launch(**launch_options)
            
            # 验证浏览器已启动
            if not self.browser or not self.browser.is_connected():
                raise Exception("浏览器启动失败或连接已断开")
            logger.debug(f"【{self.pure_user_id}】浏览器启动成功，已连接: {self.browser.is_connected()}")
            
            # 创建上下文，使用随机特征
            logger.debug(f"【{self.pure_user_id}】创建浏览器上下文...")
            
            # 🔑 关键优化：添加更多真实浏览器特征
            context_options = {
                'user_agent': browser_features['user_agent'],
                'locale': browser_features['locale'],
                'timezone_id': browser_features['timezone_id'],
                # 🔑 添加真实的权限设置
                'permissions': ['geolocation', 'notifications'],
                # 🔑 添加真实的色彩方案
                'color_scheme': random.choice(['light', 'dark', 'no-preference']),
                # 🔑 添加HTTP凭据
                'http_credentials': None,
                # 🔑 忽略HTTPS错误（某些情况下更真实）
                'ignore_https_errors': False,
            }
            
            # 根据模式配置viewport和no_viewport
            if not self.headless:
                # 有头模式：使用 no_viewport=True 支持窗口最大化
                # 注意：使用no_viewport时，不能设置device_scale_factor、is_mobile、has_touch
                context_options['no_viewport'] = True  # 移除viewport限制，支持--start-maximized
                self.context = self.browser.new_context(**context_options)
            else:
                # 无头模式：使用固定viewport
                context_options.update({
                    'viewport': {'width': browser_features['viewport_width'], 'height': browser_features['viewport_height']},
                    'device_scale_factor': browser_features['device_scale_factor'],
                    'is_mobile': browser_features['is_mobile'],
                    'has_touch': browser_features['has_touch'],
                })
                self.context = self.browser.new_context(**context_options)
            
            # 验证上下文已创建
            if not self.context:
                raise Exception("浏览器上下文创建失败")
            logger.debug(f"【{self.pure_user_id}】浏览器上下文创建成功")
            
            # 创建新页面
            logger.debug(f"【{self.pure_user_id}】创建新页面...")
            self.page = self.context.new_page()
            
            # 验证页面已创建
            if not self.page:
                raise Exception("页面创建失败")
            logger.debug(f"【{self.pure_user_id}】页面创建成功（{'最大化窗口模式' if not self.headless else '无头模式'}）")
            
            # 添加增强反检测脚本
            logger.debug(f"【{self.pure_user_id}】添加反检测脚本...")
            self.page.add_init_script(self._get_stealth_script(browser_features))
            browser_source = "system-chromium" if chromium_executable else "playwright-default"
            logger.info(
                f"【{self.pure_user_id}】浏览器初始化完成 "
                f"(headless={self.headless}, browser={browser_source})"
            )
            
            return self.page
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】初始化浏览器失败: {e}")
            _log_slider_traceback(self.pure_user_id, "初始化浏览器失败")
            # 确保在异常时也清理已创建的资源
            self._cleanup_on_init_failure()
            raise
    
    def _cleanup_on_init_failure(self):
        """初始化失败时的清理"""
        try:
            if hasattr(self, 'page') and self.page:
                self.page.close()
                self.page = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】清理页面时出错: {e}")
        
        try:
            if hasattr(self, 'context') and self.context:
                self.context.close()
                self.context = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】清理上下文时出错: {e}")
        
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
                self.browser = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】清理浏览器时出错: {e}")
        
        try:
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】清理Playwright时出错: {e}")
    
    def _load_success_history(self) -> List[Dict[str, Any]]:
        """加载历史成功数据"""
        try:
            if not os.path.exists(self.success_history_file):
                return []
            
            with open(self.success_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                logger.info(f"【{self.pure_user_id}】加载历史成功数据: {len(history)}条记录")
                return history
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】加载历史数据失败: {e}")
            return []
    
    def _save_success_record(self, trajectory_data: Dict[str, Any]):
        """保存成功记录"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.success_history_file), exist_ok=True)
            
            # 加载现有历史
            history = self._load_success_history()
            
            # 添加新记录 - 只保存必要参数，不保存完整轨迹点（节省内存和磁盘空间）
            record = {
                "timestamp": time.time(),
                "user_id": self.pure_user_id,
                "distance": trajectory_data.get("distance", 0),
                "total_steps": trajectory_data.get("total_steps", 0),
                "base_delay": trajectory_data.get("base_delay", 0),
                "jitter_x_range": trajectory_data.get("jitter_x_range", [0, 0]),
                "jitter_y_range": trajectory_data.get("jitter_y_range", [0, 0]),
                "slow_factor": trajectory_data.get("slow_factor", 0),
                "acceleration_phase": trajectory_data.get("acceleration_phase", 0),
                "fast_phase": trajectory_data.get("fast_phase", 0),
                "slow_start_ratio": trajectory_data.get("slow_start_ratio", 0),
                # 【优化】不再保存完整轨迹点，节省 90% 存储空间
                # "trajectory_points": trajectory_data.get("trajectory_points", []),
                "trajectory_point_count": len(trajectory_data.get("trajectory_points", [])),  # 只记录数量
                "final_left_px": trajectory_data.get("final_left_px", 0),
                "completion_used": trajectory_data.get("completion_used", False),
                "completion_steps": trajectory_data.get("completion_steps", 0),
                "success": True
            }
            
            history.append(record)
            
            # 只保留最近100条成功记录
            if len(history) > 100:
                history = history[-100:]
            
            # 保存到文件
            with open(self.success_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            logger.info(f"【{self.pure_user_id}】保存成功记录: 距离{record['distance']}px, 步数{record['total_steps']}, 轨迹点{record['trajectory_point_count']}个")
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】保存成功记录失败: {e}")
    
    def _optimize_trajectory_params(self) -> Dict[str, Any]:
        """基于历史成功数据优化轨迹参数"""
        try:
            if not self.enable_learning:
                return self.trajectory_params
            
            history = self._load_success_history()
            if len(history) < 1:
                logger.info(f"【{self.pure_user_id}】历史成功数据不足({len(history)}条)，使用默认参数")
                return self.trajectory_params
            
            # 计算成功记录的平均值
            total_steps_list = [record["total_steps"] for record in history]
            base_delay_list = [record["base_delay"] for record in history]
            slow_factor_list = [record["slow_factor"] for record in history]
            acceleration_phase_list = [record["acceleration_phase"] for record in history]
            fast_phase_list = [record["fast_phase"] for record in history]
            slow_start_ratio_list = [record["slow_start_ratio"] for record in history]
            
            # 基于完整轨迹数据的学习
            completion_usage_rate = 0
            avg_completion_steps = 0
            trajectory_length_stats = []
            
            if len(history) > 0:
                # 计算补全使用率
                completion_used_count = sum(1 for record in history if record.get("completion_used", False))
                completion_usage_rate = completion_used_count / len(history)
                
                # 计算平均补全步数
                completion_steps_list = [record.get("completion_steps", 0) for record in history if record.get("completion_used", False)]
                if completion_steps_list:
                    avg_completion_steps = sum(completion_steps_list) / len(completion_steps_list)
                
                # 分析轨迹长度分布
                trajectory_lengths = [len(record.get("trajectory_points", [])) for record in history]
                if trajectory_lengths:
                    trajectory_length_stats = [min(trajectory_lengths), max(trajectory_lengths), sum(trajectory_lengths) / len(trajectory_lengths)]
            
            # 计算平均值和标准差
            def safe_avg(values):
                return sum(values) / len(values) if values else 0
            
            def safe_std(values):
                if len(values) < 2:
                    return 0
                avg = safe_avg(values)
                variance = sum((x - avg) ** 2 for x in values) / len(values)
                return variance ** 0.5
            
            # 基于成功样本做温和收敛，避免把参数压到极端值
            avg_steps = safe_avg(total_steps_list)
            std_steps = safe_std(total_steps_list)
            steps_min = max(18, int(avg_steps - max(2, std_steps * 1.2)))
            steps_max = min(36, int(avg_steps + max(4, std_steps * 1.6)))
            if steps_min >= steps_max:
                steps_min = max(18, int(avg_steps))
                steps_max = min(36, steps_min + 4)
            
            avg_delay = safe_avg(base_delay_list)
            std_delay = safe_std(base_delay_list)
            delay_min = max(0.04, round(avg_delay - max(0.008, std_delay * 1.2), 4))
            delay_max = min(0.12, round(avg_delay + max(0.015, std_delay * 1.6), 4))
            if delay_min >= delay_max:
                delay_min = max(0.04, round(avg_delay, 4))
                delay_max = min(0.12, round(delay_min + 0.02, 4))
            
            avg_slow = safe_avg(slow_factor_list)
            std_slow = safe_std(slow_factor_list)
            slow_min = max(2, int(avg_slow - max(1, std_slow)))
            slow_max = min(8, int(avg_slow + max(2, std_slow * 1.5)))
            if slow_min >= slow_max:
                slow_min = max(2, int(avg_slow))
                slow_max = min(8, slow_min + 2)
            
            optimized_params = {
                "total_steps_range": [steps_min, steps_max],
                "base_delay_range": [delay_min, delay_max],
                "jitter_x_range": [0, 3],
                "jitter_y_range": [-2, 3],
                "slow_factor_range": [slow_min, slow_max],
                "acceleration_phase": max(0.25, min(0.45, safe_avg(acceleration_phase_list))),
                "fast_phase": max(0.35, min(0.55, safe_avg(fast_phase_list))),
                "slow_start_ratio_base": max(1.01, min(1.05, safe_avg(slow_start_ratio_list))),
                "completion_usage_rate": completion_usage_rate,
                "avg_completion_steps": avg_completion_steps,
                "trajectory_length_stats": trajectory_length_stats,
                "learning_enabled": True
            }
            
            logger.info(f"【{self.pure_user_id}】基于{len(history)}条成功记录优化轨迹参数: 步数{optimized_params['total_steps_range']}, 延迟{optimized_params['base_delay_range']}")

            return optimized_params
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】优化轨迹参数失败: {e}")
            return self.trajectory_params

    def _build_attempt_trajectory_params(self, attempt: int) -> tuple[str, Dict[str, Any]]:
        """根据重试次数构造更稳妥的轨迹参数。"""
        params = {}
        for key, value in self.trajectory_params.items():
            params[key] = value.copy() if isinstance(value, list) else value

        strategy = "manual_stealth"
        if attempt == 2:
            strategy = "cautious"
            params["total_steps_range"] = [
                min(42, params["total_steps_range"][0] + 4),
                min(48, params["total_steps_range"][1] + 6),
            ]
            params["base_delay_range"] = [
                min(0.16, round(params["base_delay_range"][0] * 1.25 + 0.01, 4)),
                min(0.18, round(params["base_delay_range"][1] * 1.35 + 0.015, 4)),
            ]
            params["slow_factor_range"] = [
                max(2, params["slow_factor_range"][0]),
                min(10, params["slow_factor_range"][1] + 1),
            ]
        elif attempt >= 3:
            strategy = "slow"
            params["total_steps_range"] = [
                min(46, params["total_steps_range"][0] + 8),
                min(54, params["total_steps_range"][1] + 10),
            ]
            params["base_delay_range"] = [
                min(0.18, round(params["base_delay_range"][0] * 1.5 + 0.015, 4)),
                min(0.22, round(params["base_delay_range"][1] * 1.6 + 0.02, 4)),
            ]
            params["slow_factor_range"] = [
                max(3, params["slow_factor_range"][0] + 1),
                min(12, params["slow_factor_range"][1] + 2),
            ]

        if params["total_steps_range"][0] >= params["total_steps_range"][1]:
            params["total_steps_range"][1] = params["total_steps_range"][0] + 2
        if params["base_delay_range"][0] >= params["base_delay_range"][1]:
            params["base_delay_range"][1] = round(params["base_delay_range"][0] + 0.02, 4)

        return strategy, params

    def _reset_slider_challenge(self) -> bool:
        """在重试前点击验证码容器，显式重置 challenge。"""
        selectors = [
            ".nc-container",
            "#baxia-dialog-content",
            ".captcha-tips",
            ".nc_wrapper",
            "#nocaptcha",
        ]
        contexts = []
        if hasattr(self, "_detected_slider_frame") and self._detected_slider_frame is not None:
            contexts.append(self._detected_slider_frame)
        contexts.append(self.page)

        for context in contexts:
            if not context:
                continue
            for selector in selectors:
                try:
                    element = context.query_selector(selector)
                    if element and element.is_visible():
                        element.click(force=True, timeout=2000)
                        wait_seconds = random.uniform(0.8, 1.3)
                        logger.info(
                            f"【{self.pure_user_id}】重试前已点击验证码容器重置 challenge: "
                            f"{selector}，等待{wait_seconds:.2f}秒"
                        )
                        time.sleep(wait_seconds)
                        return True
                except Exception:
                    continue

        logger.debug(f"【{self.pure_user_id}】未找到可点击的验证码重置容器")
        return False
    
    def _get_cookies_after_success(self):
        """滑块验证成功后获取cookie"""
        try:
            logger.info(f"【{self.pure_user_id}】开始获取滑块验证成功后的页面cookie...")
            
            # 检查当前页面URL
            current_url = self.page.url
            logger.info(f"【{self.pure_user_id}】当前页面URL: {current_url}")
            
            # 检查页面标题
            page_title = self.page.title()
            logger.info(f"【{self.pure_user_id}】当前页面标题: {page_title}")
            
            # 等待一下确保cookie完全更新
            time.sleep(1)
            
            # 获取浏览器中的所有cookie
            cookies = self.context.cookies()
            
            if cookies:
                # 将cookie转换为字典格式
                new_cookies = {}
                for cookie in cookies:
                    new_cookies[cookie['name']] = cookie['value']
                
                logger.info(f"【{self.pure_user_id}】滑块验证成功后已获取cookie，共{len(new_cookies)}个cookie")
                
                # 记录所有cookie的详细信息
                logger.info(f"【{self.pure_user_id}】获取到的所有cookie: {list(new_cookies.keys())}")
                
                # 只提取x5sec相关的cookie
                filtered_cookies = {}
                
                # 筛选出x5相关的cookies（包括x5sec, x5step等）
                for cookie_name, cookie_value in new_cookies.items():
                    cookie_name_lower = cookie_name.lower()
                    if cookie_name_lower.startswith('x5') or 'x5sec' in cookie_name_lower:
                        filtered_cookies[cookie_name] = cookie_value
                        logger.info(f"【{self.pure_user_id}】x5相关cookie已获取: {cookie_name} = {cookie_value}")
                
                logger.info(f"【{self.pure_user_id}】找到{len(filtered_cookies)}个x5相关cookies: {list(filtered_cookies.keys())}")
                
                if filtered_cookies:
                    logger.info(f"【{self.pure_user_id}】返回过滤后的x5相关cookie: {list(filtered_cookies.keys())}")
                    return filtered_cookies
                else:
                    logger.warning(f"【{self.pure_user_id}】未找到x5相关cookie")
                    return None
            else:
                logger.warning(f"【{self.pure_user_id}】未获取到任何cookie")
                return None
                
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】获取滑块验证成功后的cookie失败: {str(e)}")
            return None
    
    def _save_cookies_to_file(self, cookies):
        """保存cookie到文件"""
        try:
            # 确保目录存在
            cookie_dir = f"slider_cookies/{self.user_id}"
            os.makedirs(cookie_dir, exist_ok=True)
            
            # 保存cookie到JSON文件
            cookie_file = f"{cookie_dir}/cookies_{int(time.time())}.json"
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            logger.info(f"【{self.pure_user_id}】Cookie已保存到文件: {cookie_file}")
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】保存cookie到文件失败: {str(e)}")
    
    def _get_random_browser_features(self):
        """获取随机浏览器特征"""
        # 随机选择窗口大小（使用更大的尺寸以适应最大化）
        window_sizes = [
            "1920,1080", "1920,1200", "2560,1440", "1680,1050", "1600,900"
        ]
        
        # 随机选择语言
        languages = [
            ("zh-CN", "zh-CN,zh;q=0.9,en;q=0.8"),
            ("zh-CN", "zh-CN,zh;q=0.9"),
            ("zh-CN", "zh-CN,zh;q=0.8,en;q=0.6")
        ]
        
        # 随机选择用户代理 —— 保持与 2025/2026 年主流 Chrome 版本一致
        # 旧版本 (118-120) 已被 NC 风控系统标记为可疑，务必使用新版本
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        ]
        
        window_size = random.choice(window_sizes)
        lang, accept_lang = random.choice(languages)
        user_agent = random.choice(user_agents)
        
        # 解析窗口大小
        width, height = map(int, window_size.split(','))
        
        return {
            'window_size': window_size,
            'lang': lang,
            'accept_lang': accept_lang,
            'user_agent': user_agent,
            'locale': lang,
            'viewport_width': width,
            'viewport_height': height,
            'device_scale_factor': random.choice([1.0, 1.25, 1.5]),
            'is_mobile': False,
            'has_touch': False,
            'timezone_id': 'Asia/Shanghai'
        }
    
    def _get_stealth_script(self, browser_features):
        """获取增强反检测脚本"""
        user_agent = json.dumps(browser_features['user_agent'])
        locale = json.dumps(browser_features['locale'])
        timezone_id = json.dumps(browser_features['timezone_id'])
        vendor = json.dumps("Google Inc.")
        platform = json.dumps("Win32")

        return f"""
            (() => {{
                const defineGetter = (obj, prop, value) => {{
                    try {{
                        Object.defineProperty(obj, prop, {{
                            get: () => value,
                            configurable: true,
                        }});
                    }} catch (e) {{}}
                }};

                const removeAutomationKeys = (target) => {{
                    for (const key of Object.keys(target)) {{
                        const lowerKey = key.toLowerCase();
                        if (
                            key.startsWith('cdc_') ||
                            key.startsWith('$cdc_') ||
                            key.startsWith('wdc_') ||
                            key.startsWith('$wdc_') ||
                            lowerKey.includes('selenium') ||
                            lowerKey.includes('webdriver')
                        ) {{
                            try {{
                                delete target[key];
                            }} catch (e) {{}}
                        }}
                    }}
                }};

                defineGetter(Navigator.prototype, 'webdriver', undefined);
                try {{ delete navigator.webdriver; }} catch (e) {{}}
                try {{ delete Navigator.prototype.webdriver; }} catch (e) {{}}

                defineGetter(navigator, 'languages', [{locale}, 'zh-CN', 'zh', 'en-US']);
                defineGetter(navigator, 'language', {locale});
                defineGetter(navigator, 'platform', {platform});
                defineGetter(navigator, 'vendor', {vendor});
                defineGetter(navigator, 'userAgent', {user_agent});
                defineGetter(navigator, 'maxTouchPoints', 0);
                defineGetter(navigator, 'hardwareConcurrency', 4);
                defineGetter(navigator, 'deviceMemory', 8);

                try {{
                    Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
                        value: function() {{
                            const options = {{
                                locale: {locale},
                                calendar: 'gregory',
                                numberingSystem: 'latn',
                                timeZone: {timezone_id},
                                year: 'numeric',
                                month: 'numeric',
                                day: 'numeric'
                            }};
                            return options;
                        }},
                        configurable: true,
                    }});
                }} catch (e) {{}}

                if (!window.chrome) {{
                    Object.defineProperty(window, 'chrome', {{
                        value: {{
                            runtime: {{}},
                            app: {{}},
                            csi: () => ({{}}),
                            loadTimes: () => ({{}})
                        }},
                        configurable: true,
                    }});
                }}

                removeAutomationKeys(window);
                ['__playwright', '__pw_manual', '__pw_original', 'playwright', 'webdriver'].forEach((key) => {{
                    try {{ delete window[key]; }} catch (e) {{}}
                }});

                if (navigator.permissions && navigator.permissions.query) {{
                    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
                    navigator.permissions.query = (parameters) => {{
                        if (parameters && parameters.name === 'notifications') {{
                            return Promise.resolve({{ state: Notification.permission }});
                        }}
                        return originalQuery(parameters);
                    }};
                }}

                // ========================================================
                // WebGL 指纹伪装（NC 风控通过 UNMASKED_RENDERER 识别虚拟机）
                // ========================================================
                const _webglParamHandler = {{
                    apply: function(target, ctx, args) {{
                        const param = args[0];
                        // UNMASKED_VENDOR_WEBGL
                        if (param === 37445) return 'Intel Inc.';
                        // UNMASKED_RENDERER_WEBGL
                        if (param === 37446) return 'Intel Iris OpenGL Engine';
                        return Reflect.apply(target, ctx, args);
                    }}
                }};
                try {{
                    const origGP = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = new Proxy(origGP, _webglParamHandler);
                    const origGP2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = new Proxy(origGP2, _webglParamHandler);
                }} catch(e) {{}}

                // ========================================================
                // AudioContext 指纹伪装（细微随机偏移，每次不同）
                // ========================================================
                try {{
                    const _audioNoise = (Math.random() * 0.0001) - 0.00005;
                    const origCreateAnalyser = AudioContext.prototype.createAnalyser;
                    AudioContext.prototype.createAnalyser = function() {{
                        const analyser = origCreateAnalyser.call(this);
                        const origGetFloatFrequency = analyser.getFloatFrequencyData.bind(analyser);
                        analyser.getFloatFrequencyData = function(array) {{
                            origGetFloatFrequency(array);
                            for (let i = 0; i < array.length; i++) {{
                                array[i] += _audioNoise;
                            }}
                        }};
                        return analyser;
                    }};
                }} catch(e) {{}}

                // ========================================================
                // Canvas 指纹伪装（细微随机像素偏移）
                // ========================================================
                try {{
                    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(type) {{
                        const ctx2d = this.getContext('2d');
                        if (ctx2d) {{
                            const imageData = ctx2d.getImageData(0, 0, this.width, this.height);
                            const data = imageData.data;
                            // 仅修改少量像素，避免影响验证码识别
                            for (let i = 0; i < Math.min(data.length, 32); i += 4) {{
                                data[i] ^= 1;
                            }}
                            ctx2d.putImageData(imageData, 0, 0);
                        }}
                        return origToDataURL.apply(this, arguments);
                    }};
                }} catch(e) {{}}
            }})();
        """
    
    def _bezier_curve(self, p0, p1, p2, p3, t):
        """三次贝塞尔曲线 - 生成更自然的轨迹"""
        return (1-t)**3 * p0 + 3*(1-t)**2*t * p1 + 3*(1-t)*t**2 * p2 + t**3 * p3
    
    def _easing_function(self, t, mode='easeOutQuad'):
        """缓动函数 - 模拟真实人类滑动的速度变化"""
        if mode == 'easeOutQuad':
            return t * (2 - t)
        elif mode == 'easeInOutCubic':
            return 4*t**3 if t < 0.5 else 1 - pow(-2*t + 2, 3) / 2
        elif mode == 'easeOutBack':
            c1 = 1.70158
            c3 = c1 + 1
            return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
        else:
            return t
    
    # ══════════════════════════════════════════════════════════════════════════
    # 贝塞尔曲线工具（静态方法，供轨迹生成使用）
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _bezier_point(t: float, control_points: list) -> tuple:
        """De Casteljau 算法计算任意阶贝塞尔曲线上的点"""
        pts = [list(p) for p in control_points]
        n = len(pts)
        for r in range(1, n):
            for i in range(n - r):
                pts[i][0] = (1 - t) * pts[i][0] + t * pts[i + 1][0]
                pts[i][1] = (1 - t) * pts[i][1] + t * pts[i + 1][1]
        return pts[0][0], pts[0][1]

    @staticmethod
    def _gen_bezier_trajectory(distance: float, steps: int) -> list:
        """
        用四阶贝塞尔曲线生成 (x, y) 绝对坐标列表。
        控制点模拟真人拖动：
          P0 = (0, 0)       起点
          P1 = 随机偏左     早期加速阶段控制点
          P2 = 随机偏右     中期匀速阶段控制点
          P3 = 随机轻微超调 减速末端
          P4 = (distance,0) 终点
        """
        # 随机控制点（Y 轴轻微抖动，X 轴引导速度曲线）
        cp = [
            [0,            0],
            [distance * random.uniform(0.08, 0.18),  random.gauss(0, 3)],
            [distance * random.uniform(0.35, 0.55),  random.gauss(0, 4)],
            [distance * random.uniform(0.78, 0.92),  random.gauss(0, 2)],
            [distance + random.gauss(0, 1.5),        random.gauss(0, 1)],
        ]

        points = []
        for i in range(steps + 1):
            t = i / steps
            x, y = XianyuSliderStealth._bezier_point(t, cp)
            points.append((x, y))
        return points

    def _generate_physics_trajectory(self, distance: float):
        """
        ★ v3 完全重写 ★ — 归一化速度权重，保证累计距离精确等于 distance

        v2 的 bug：speed_factor 三段均值 << 1.0，导致 sum(step_x) ≈ distance * 0.71
        v3 修复：先生成归一化权重 weights（sum=1.0），再乘以 target，
                 最后单独处理超调和回位，两部分各自精确。

        轨迹结构
        ─────────────────────────────────────────────
        forward  : 正向推进到 distance + overshoot
        settle   : 回位到 distance（超调回位）
        inertia  : 松手后微颤（标记 x='inertia'）
        """
        # ── 步数：正态分布采样 ──
        lo, hi = self.trajectory_params["total_steps_range"]
        steps = int(random.gauss((lo + hi) / 2, 2))
        steps = max(lo, min(hi, steps))

        # ── 基础延迟：对数正态采样 ──
        d_lo, d_hi = self.trajectory_params["base_delay_range"]
        base_delay = max(d_lo, min(d_hi, random.gauss((d_lo + d_hi) / 2, (d_hi - d_lo) / 5)))

        # ── 超调量：固定上限 8px，避免大距离时过冲 ──
        overshoot = min(random.gauss(4.5, 1.2), 8.0)
        overshoot = max(overshoot, 1.5)
        target_fwd = distance + overshoot          # 正向目标（含超调）

        settle_n  = random.randint(2, 4)           # 回位步数
        forward_n = max(steps - settle_n, 8)       # 正向步数

        acc_end  = int(forward_n * self.trajectory_params.get("acceleration_phase", 0.30))
        fast_end = int(forward_n * (self.trajectory_params.get("acceleration_phase", 0.30)
                                    + self.trajectory_params.get("fast_phase", 0.45)))

        # ── 生成原始速度权重（未归一化）──
        raw_weights = []
        raw_delays  = []
        raw_jitter_y = []

        for i in range(forward_n):
            if i < acc_end:
                # 加速段：指数增长
                phase = (i + 1) / max(acc_end, 1)
                w = phase ** 1.8 * random.lognormvariate(0, 0.12)
                d = random.lognormvariate(math.log(max(base_delay * 1.4, 1e-6)), 0.28)
                d = max(base_delay * 0.9, min(base_delay * 2.2, d))
                jy = random.gauss(0, 1.2) + math.sin(i / forward_n * math.pi) * 0.6

            elif i < fast_end:
                # 匀速段：速度在 1.0 附近对数正态抖动
                w = random.lognormvariate(0, 0.10)          # 均值=1.0
                d = random.lognormvariate(math.log(max(base_delay, 1e-6)), 0.16)
                d = max(base_delay * 0.65, min(base_delay * 1.5, d))
                jy = random.gauss(0, 0.8)

            else:
                # 减速段：指数衰减
                phase = (i - fast_end) / max(forward_n - fast_end, 1)
                w = max(0.04, (1.0 - phase) ** 1.7) * random.lognormvariate(0, 0.12)
                d = random.lognormvariate(math.log(max(base_delay * 1.25, 1e-6)), 0.22)
                d = max(base_delay * 0.8, min(base_delay * 2.0, d))
                jy = random.gauss(0, 0.4)

            raw_weights.append(max(w, 1e-5))
            raw_delays.append(d)
            raw_jitter_y.append(jy)

        # ── 归一化：保证 sum(dx) = target_fwd ──────────────────────────────────
        total_w = sum(raw_weights)
        trajectory = []
        for i in range(forward_n):
            dx  = (raw_weights[i] / total_w) * target_fwd
            trajectory.append((round(dx, 4), round(raw_jitter_y[i], 3), round(raw_delays[i], 4)))

        # ── 超调回位段 ──────────────────────────────────────────────────────────
        # 每步均匀回退 overshoot/settle_n，确保最终累计等于 distance
        step_back = overshoot / settle_n
        for i in range(settle_n):
            back_x = -step_back * random.lognormvariate(0, 0.06)   # 轻微随机，但总和 ≈ -overshoot
            delay  = random.uniform(0.07, 0.13)
            trajectory.append((round(back_x, 4), round(random.gauss(0, 0.7), 3), round(delay, 4)))

        # ── 松手后惯性漂移（x='inertia' 标记，在 mouse.up() 之后执行）──
        inertia_n = random.randint(2, 4)
        for _ in range(inertia_n):
            trajectory.append(('inertia', round(random.gauss(0, 0.45), 3),
                                round(random.uniform(0.025, 0.065), 4)))

        # ── 调试：验证归一化 ──
        real_sum = sum(p[0] for p in trajectory if p[0] != 'inertia')
        logger.info(
            f"【{self.pure_user_id}】✅ 归一化轨迹：{steps}步，"
            f"目标{distance:.1f}px，理论累计{real_sum:.2f}px "
            f"（误差{abs(real_sum - distance):.2f}px），"
            f"超调{overshoot:.1f}px，延迟{base_delay:.3f}s"
        )
        return trajectory
    
    def generate_human_trajectory(self, distance: float):
        """生成人类化滑动轨迹。"""
        try:
            logger.info(f"【{self.pure_user_id}】📐 使用人工节奏轨迹生成滑块动作")
            trajectory = self._generate_physics_trajectory(distance)

            # 保存轨迹数据
            self.current_trajectory_data = {
                "distance": distance,
                "model": "manual_stealth",
                "total_steps": len(trajectory),
                "base_delay": trajectory[0][2] if trajectory else 0,
                "jitter_x_range": self.trajectory_params["jitter_x_range"],
                "jitter_y_range": self.trajectory_params["jitter_y_range"],
                "slow_factor": self.trajectory_params["slow_factor_range"][1],
                "acceleration_phase": self.trajectory_params["acceleration_phase"],
                "fast_phase": self.trajectory_params["fast_phase"],
                "slow_start_ratio": self.trajectory_params["slow_start_ratio_base"],
                "trajectory_points": trajectory.copy(),
                "final_left_px": 0,
                "completion_used": False,
                "completion_steps": 0
            }
            
            return trajectory
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】生成轨迹时出错: {str(e)}")
            return []
    
    def _pyautogui_bezier_drag(self, start_x: int, start_y: int, distance: float) -> bool:
        """
        PyAutoGUI + 贝塞尔曲线备用拖拽引擎。

        完全走系统鼠标事件，绕过浏览器 CDP 协议层的自动化特征检测。
        需要: pip install pyautogui

        注意：headless 模式下 PyAutoGUI 无法操作浏览器窗口，
              只在 headless=False 时生效。
        """
        if not _PYAUTOGUI_AVAILABLE:
            logger.warning(f"【{self.pure_user_id}】PyAutoGUI 未安装，跳过备用引擎")
            return False

        try:
            logger.info(f"【{self.pure_user_id}】🖱️  PyAutoGUI+贝塞尔 备用引擎启动")

            # 生成贝塞尔路径（绝对屏幕坐标）
            steps = random.randint(28, 45)
            bezier_pts = self._gen_bezier_trajectory(distance, steps)

            # 移动到起点
            pyautogui.moveTo(start_x, start_y, duration=random.uniform(0.08, 0.18))
            time.sleep(random.uniform(0.05, 0.12))

            # 按下
            pyautogui.mouseDown(button='left')
            time.sleep(random.uniform(0.08, 0.18))

            # 按贝塞尔路径逐步移动
            for i, (bx, by) in enumerate(bezier_pts):
                abs_x = start_x + bx
                abs_y = start_y + by

                # 对数正态延迟：每步间隔不均匀
                if i < steps * 0.3:
                    step_delay = random.lognormvariate(-2.8, 0.30)   # 加速段：慢一点
                elif i < steps * 0.75:
                    step_delay = random.lognormvariate(-3.2, 0.18)   # 匀速段：快
                else:
                    step_delay = random.lognormvariate(-2.5, 0.28)   # 减速段：慢

                step_delay = max(0.012, min(0.12, step_delay))
                pyautogui.moveTo(int(abs_x), int(abs_y), duration=0)
                time.sleep(step_delay)

            # 松手前停顿
            time.sleep(random.uniform(0.10, 0.20))
            pyautogui.mouseUp(button='left')

            # 惯性漂移（松手后微动）
            cx, cy = pyautogui.position()
            for _ in range(random.randint(2, 3)):
                drift_x = cx + random.gauss(0, 0.6)
                drift_y = cy + random.gauss(0, 0.4)
                pyautogui.moveTo(int(drift_x), int(drift_y), duration=0)
                time.sleep(random.uniform(0.03, 0.06))

            logger.info(f"【{self.pure_user_id}】🖱️  PyAutoGUI 贝塞尔拖拽完成")
            return True

        except Exception as e:
            logger.error(f"【{self.pure_user_id}】PyAutoGUI 拖拽失败: {e}")
            try:
                pyautogui.mouseUp(button='left')
            except:
                pass
            return False

    def _opencv_detect_gap(self) -> Optional[float]:
        """
        OpenCV 缺口识别：对验证码截图做边缘检测，返回缺口 x 坐标（相对滑轨）。
        需要: pip install opencv-python

        工作原理：
          1. 截取整页截图
          2. 裁剪出滑轨区域
          3. Canny 边缘检测 + 模板匹配 找到最强边缘纵向变化的 x 坐标
          4. 返回缺口中心 x（即滑块需要移动到的距离）

        如果无法识别则返回 None，调用方继续使用 DOM 计算距离。
        """
        if not _OPENCV_AVAILABLE:
            return None

        try:
            # 截图转 numpy
            screenshot_bytes = self.page.screenshot()
            img_arr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if img is None:
                return None

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 找验证码容器边界（用 JS 获取坐标，比硬编码更可靠）
            rect = self.page.evaluate("""
                () => {
                    const track = document.querySelector('#nc_1_n1t') ||
                                  document.querySelector('.nc_scale');
                    if (!track) return null;
                    const r = track.getBoundingClientRect();
                    return {x: r.x, y: r.y, w: r.width, h: r.height};
                }
            """)
            if not rect or rect['w'] < 10:
                return None

            # 扩大裁剪区域，覆盖验证码图片（滑轨上方）
            pad_top  = 80   # 验证码图片一般在滑轨上方 ~80px
            pad_bot  = int(rect['h']) + 10
            x1 = max(0, int(rect['x']))
            y1 = max(0, int(rect['y']) - pad_top)
            x2 = min(img.shape[1], int(rect['x'] + rect['w']))
            y2 = min(img.shape[0], int(rect['y']) + pad_bot)

            region = gray[y1:y2, x1:x2]
            if region.size == 0:
                return None

            # Canny 边缘检测
            edges = cv2.Canny(region, 80, 200)

            # 按列统计边缘像素数，找边缘密度峰值（即缺口左边缘）
            col_sum = edges.sum(axis=0).astype(float)

            # 平滑避免噪声
            kernel_size = max(3, int(rect['w'] * 0.02))
            if kernel_size % 2 == 0:
                kernel_size += 1
            col_smooth = cv2.GaussianBlur(
                col_sum.reshape(1, -1),
                (1, kernel_size), 0
            ).flatten()

            # 排除滑块自身（前 50px 一般是滑块按钮）
            button_w = 42
            search_start = button_w
            search_end   = max(search_start + 10, len(col_smooth) - 5)
            region_search = col_smooth[search_start:search_end]

            if len(region_search) == 0:
                return None

            peak_idx = int(np.argmax(region_search)) + search_start

            # peak_idx 是相对于 region 的 x，转为相对于滑轨起点的距离
            # 缺口宽度约 42px（滑块按钮宽），取缺口中心
            gap_distance = peak_idx - button_w // 2
            gap_distance = max(5.0, min(gap_distance, rect['w'] - button_w))

            logger.info(
                f"【{self.pure_user_id}】🔍 OpenCV 缺口识别: 峰值列={peak_idx}，"
                f"缺口距离={gap_distance:.1f}px"
            )
            return float(gap_distance)

        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】OpenCV 缺口识别失败（使用 DOM 距离）: {e}")
            return None

    def simulate_slide(self, slider_button: ElementHandle, trajectory,
                       use_pyautogui: bool = False,
                       start_x: float = 0, start_y: float = 0,
                       distance: float = 0):
        """
        模拟滑动 — v3 版本

        执行顺序：
          主路径：Playwright mouse（协议层）
          备用路径：PyAutoGUI + 贝塞尔（系统鼠标，仅 headless=False 有效）

        trajectory 格式（增量 dx）：
          (dx: float, dy: float, delay: float)  正常点
          ('inertia', dy: float, delay: float)  松手后惯性点
        """
        try:
            logger.info(f"【{self.pure_user_id}】开始执行滑动 (引擎={'PyAutoGUI' if use_pyautogui else 'Playwright'})...")

            time.sleep(random.uniform(0.12, 0.28))

            # 获取滑块位置
            button_box = slider_button.bounding_box()
            if not button_box:
                logger.error(f"【{self.pure_user_id}】无法获取滑块按钮位置")
                return False

            sx = button_box["x"] + button_box["width"] / 2
            sy = button_box["y"] + button_box["height"] / 2

            # ── PyAutoGUI 备用引擎 ──────────────────────────────────────────────
            if use_pyautogui and _PYAUTOGUI_AVAILABLE and distance > 0:
                return self._pyautogui_bezier_drag(int(sx), int(sy), distance)

            # ── Playwright 主引擎 ────────────────────────────────────────────────

            # 阶段 1：从偏左位置靠近滑块
            try:
                pre_x = sx + random.uniform(-38, -12)
                pre_y = sy + random.uniform(-18, 18)
                self.page.mouse.move(pre_x, pre_y, steps=random.randint(6, 11))
                time.sleep(random.uniform(0.07, 0.18))
                self.page.mouse.move(sx, sy, steps=random.randint(3, 5))
                time.sleep(random.uniform(0.05, 0.13))
            except Exception as e:
                logger.warning(f"【{self.pure_user_id}】移动到滑块失败: {e}")

            # 阶段 2：悬停确认
            try:
                slider_button.hover(timeout=2000)
                time.sleep(max(0.07, random.gauss(0.14, 0.03)))
            except Exception as e:
                logger.warning(f"【{self.pure_user_id}】悬停失败: {e}")

            # 阶段 3：按下
            try:
                self.page.mouse.move(sx, sy)
                time.sleep(random.uniform(0.04, 0.10))
                self.page.mouse.down()
                time.sleep(random.uniform(0.07, 0.18))
            except Exception as e:
                logger.error(f"【{self.pure_user_id}】按下鼠标失败: {e}")
                return False

            # 阶段 4：执行轨迹
            normal_pts  = [(x, y, d) for x, y, d in trajectory if x != 'inertia']
            inertia_pts = [(y, d)    for x, y, d in trajectory if x == 'inertia']

            try:
                t0 = time.time()
                cur_x = sx
                cur_y = sy
                cumul = 0.0

                for i, (dx, dy, delay) in enumerate(normal_pts):
                    cumul += dx
                    cur_x = sx + cumul
                    cur_y = sy + dy

                    # steps 对数正态，避免固定步长特征
                    mv_steps = max(1, min(5, int(random.lognormvariate(1.0, 0.28))))
                    self.page.mouse.move(cur_x, cur_y, steps=mv_steps)

                    # 延迟加 ±6% 对数正态噪声
                    actual = max(0.007, delay * random.lognormvariate(0, 0.06))
                    time.sleep(actual)

                    # 最后一步记录 style.left
                    if i == len(normal_pts) - 1:
                        try:
                            import re
                            sty = slider_button.get_attribute("style") or ""
                            m = re.search(r'left:\s*([\d.]+)px', sty)
                            if m and hasattr(self, 'current_trajectory_data'):
                                self.current_trajectory_data["final_left_px"] = float(m.group(1))
                                logger.info(f"【{self.pure_user_id}】最终 left: {m.group(1)}px")
                        except:
                            pass

                # 刮刮乐停顿
                if self.is_scratch_captcha():
                    time.sleep(random.uniform(0.28, 0.48))

                # 释放前停顿
                time.sleep(random.uniform(0.09, 0.20))
                self.page.mouse.up()

                # 阶段 5：松手后惯性漂移（在 up 之后！）
                pts = inertia_pts if inertia_pts else [(random.gauss(0, 0.3), random.uniform(0.03, 0.05)) for _ in range(2)]
                for (dy_i, delay_i) in pts:
                    cur_x += random.gauss(0, 0.45)
                    cur_y += dy_i
                    self.page.mouse.move(cur_x, cur_y, steps=1)
                    time.sleep(delay_i)

                # 触发 click（某些 NC 版本需要）
                try:
                    slider_button.evaluate(
                        f"(el) => el.dispatchEvent(new MouseEvent('click', "
                        f"{{bubbles:true,cancelable:true,clientX:{cur_x},clientY:{cur_y}}}))"
                    )
                except:
                    pass

                logger.info(
                    f"【{self.pure_user_id}】滑动完成: 耗时={time.time()-t0:.2f}s，"
                    f"终点=({cur_x:.1f},{cur_y:.1f})，累计={cumul:.1f}px"
                )
                return True

            except Exception as e:
                logger.error(f"【{self.pure_user_id}】轨迹执行失败: {e}\n{traceback.format_exc()}")
                try:
                    self.page.mouse.up()
                except:
                    pass
                return False

        except Exception as e:
            logger.error(f"【{self.pure_user_id}】simulate_slide 异常: {e}\n{traceback.format_exc()}")
            return False
    
    def _simulate_human_page_behavior(self):
        """模拟人类在验证页面的前置行为 - 极速模式已禁用"""
        # 极速模式：不进行页面行为模拟，直接开始滑动
        pass
    
    def find_slider_elements(self, fast_mode=False):
        """查找滑块元素（支持在主页面和所有frame中查找）
        
        Args:
            fast_mode: 快速模式，不使用wait_for_selector，减少等待时间（当已确认滑块存在时使用）
        """
        try:
            # 快速等待页面稳定（快速模式下跳过）
            if not fast_mode:
                time.sleep(0.1)
            
            # ===== 【优化】优先在 frames 中快速查找最常见的滑块组合 =====
            # 根据实际日志，滑块按钮和轨道通常在同一个 frame 中
            # 按钮: #nc_1_n1z, 轨道: #nc_1_n1t
            logger.debug(f"【{self.pure_user_id}】优先在frames中快速查找常见滑块组合...")
            try:
                frames = self.page.frames
                for idx, frame in enumerate(frames):
                    try:
                        # 优先查找最常见的按钮选择器
                        button_element = frame.query_selector("#nc_1_n1z")
                        if button_element and button_element.is_visible():
                            # 在同一个 frame 中查找轨道
                            track_element = frame.query_selector("#nc_1_n1t")
                            if track_element and track_element.is_visible():
                                # 找到容器（可以用按钮或其他选择器）
                                container_element = frame.query_selector("#baxia-dialog-content")
                                if not container_element:
                                    container_element = frame.query_selector(".nc-container")
                                if not container_element:
                                    # 如果找不到容器，用按钮作为容器标识
                                    container_element = button_element
                                
                                logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 快速找到完整滑块组合！")
                                logger.info(f"【{self.pure_user_id}】  - 按钮: #nc_1_n1z")
                                logger.info(f"【{self.pure_user_id}】  - 轨道: #nc_1_n1t")
                                
                                # 保存frame引用
                                self._detected_slider_frame = frame
                                return container_element, button_element, track_element
                    except Exception as e:
                        logger.debug(f"【{self.pure_user_id}】Frame {idx} 快速查找失败: {e}")
                        continue
            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】frames 快速查找出错: {e}")
            
            # ===== 如果快速查找失败，使用原来的完整查找逻辑 =====
            logger.debug(f"【{self.pure_user_id}】快速查找未成功，使用完整查找逻辑...")
            
            # 定义滑块容器选择器（支持多种类型）
            container_selectors = [
                "#nc_1_n1z",  # 滑块按钮也可以作为容器标识
                "#baxia-dialog-content",
                ".nc-container",
                ".nc_wrapper",
                ".nc_scale",
                "[class*='nc-container']",
                # 刮刮乐类型滑块
                "#nocaptcha",
                ".scratch-captcha-container",
                ".scratch-captcha-question-bg",
                # 通用选择器
                "[class*='slider']",
                "[class*='captcha']"
            ]
            
            # 查找滑块容器
            slider_container = None
            found_frame = None
            
            # 如果检测时已经知道滑块在哪个frame中，直接在该frame中查找
            if hasattr(self, '_detected_slider_frame'):
                if self._detected_slider_frame is not None:
                    # 在已知的frame中查找
                    logger.info(f"【{self.pure_user_id}】已知滑块在frame中，直接在frame中查找...")
                    target_frame = self._detected_slider_frame
                    for selector in container_selectors:
                        try:
                            element = target_frame.query_selector(selector)
                            if element:
                                try:
                                    if element.is_visible():
                                        logger.info(f"【{self.pure_user_id}】在已知Frame中找到滑块容器: {selector}")
                                        slider_container = element
                                        found_frame = target_frame
                                        break
                                except:
                                    # 如果无法检查可见性，也尝试使用
                                    logger.info(f"【{self.pure_user_id}】在已知Frame中找到滑块容器（无法检查可见性）: {selector}")
                                    slider_container = element
                                    found_frame = target_frame
                                    break
                        except Exception as e:
                            logger.debug(f"【{self.pure_user_id}】已知Frame选择器 {selector} 未找到: {e}")
                            continue
                else:
                    # _detected_slider_frame 是 None，表示在主页面
                    logger.info(f"【{self.pure_user_id}】已知滑块在主页面，直接在主页面查找...")
                    for selector in container_selectors:
                        try:
                            element = self.page.wait_for_selector(selector, timeout=1000)
                            if element:
                                logger.info(f"【{self.pure_user_id}】在已知主页面找到滑块容器: {selector}")
                                slider_container = element
                                found_frame = self.page
                                break
                        except Exception as e:
                            logger.debug(f"【{self.pure_user_id}】主页面选择器 {selector} 未找到: {e}")
                            continue
            
            # 如果已知位置中没找到，或者没有已知位置，先尝试在主页面查找
            if not slider_container:
                for selector in container_selectors:
                    try:
                        element = self.page.wait_for_selector(selector, timeout=1000)  # 减少超时时间，快速跳过
                        if element:
                            logger.info(f"【{self.pure_user_id}】在主页面找到滑块容器: {selector}")
                            slider_container = element
                            found_frame = self.page
                            break
                    except Exception as e:
                        logger.debug(f"【{self.pure_user_id}】主页面选择器 {selector} 未找到: {e}")
                        continue
            
            # 如果主页面没找到，在所有frame中查找
            if not slider_container and self.page:
                try:
                    frames = self.page.frames
                    logger.info(f"【{self.pure_user_id}】主页面未找到滑块，开始在所有frame中查找（共{len(frames)}个frame）...")
                    for idx, frame in enumerate(frames):
                        try:
                            for selector in container_selectors:
                                try:
                                    # 在frame中使用query_selector，因为frame可能不支持wait_for_selector
                                    element = frame.query_selector(selector)
                                    if element:
                                        # 检查元素是否可见
                                        try:
                                            if element.is_visible():
                                                logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块容器: {selector}")
                                                slider_container = element
                                                found_frame = frame
                                                break
                                        except:
                                            # 如果无法检查可见性，也尝试使用
                                            logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块容器（无法检查可见性）: {selector}")
                                            slider_container = element
                                            found_frame = frame
                                            break
                                except Exception as e:
                                    logger.debug(f"【{self.pure_user_id}】Frame {idx} 选择器 {selector} 未找到: {e}")
                                    continue
                            if slider_container:
                                break
                        except Exception as e:
                            logger.debug(f"【{self.pure_user_id}】检查Frame {idx} 时出错: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】获取frame列表时出错: {e}")
            
            if not slider_container:
                logger.error(f"【{self.pure_user_id}】未找到任何滑块容器（主页面和所有frame都已检查）")
                return None, None, None
            
            # 定义滑块按钮选择器（支持多种类型）
            button_selectors = [
                # nc 系列滑块
                "#nc_1_n1z",
                ".nc_iconfont",
                ".btn_slide",
                # 刮刮乐类型滑块
                "#scratch-captcha-btn",
                ".scratch-captcha-slider .button",
                # 通用选择器
                "[class*='slider']",
                "[class*='btn']",
                "[role='button']"
            ]
            
            # 查找滑块按钮（在找到容器的同一个frame中查找）
            slider_button = None
            search_frame = found_frame if found_frame and found_frame != self.page else self.page
            
            # 如果容器是在主页面找到的，按钮也应该在主页面查找
            # 如果容器是在frame中找到的，按钮也应该在同一个frame中查找
            for selector in button_selectors:
                try:
                    element = None
                    if fast_mode:
                        # 快速模式：直接使用 query_selector，不等待
                        element = search_frame.query_selector(selector)
                    else:
                        # 正常模式：使用 wait_for_selector
                        if search_frame == self.page:
                            element = self.page.wait_for_selector(selector, timeout=3000)
                        else:
                            # 在frame中先尝试wait_for_selector（如果支持）
                            try:
                                # 尝试使用wait_for_selector（Playwright的frame支持）
                                element = search_frame.wait_for_selector(selector, timeout=3000)
                            except:
                                # 如果不支持wait_for_selector，使用query_selector并等待
                                time.sleep(0.5)  # 等待元素加载
                                element = search_frame.query_selector(selector)
                    
                    if element:
                        # 检查元素是否可见，但不要因为不可见就放弃
                        try:
                            is_visible = element.is_visible()
                            if not is_visible:
                                logger.debug(f"【{self.pure_user_id}】找到元素但不可见: {selector}，继续尝试其他选择器")
                                element = None
                        except Exception as vis_e:
                            # 如果无法检查可见性，仍然使用该元素
                            logger.debug(f"【{self.pure_user_id}】无法检查元素可见性: {vis_e}，继续使用该元素")
                            pass
                    
                    if element:
                        frame_info = "主页面" if search_frame == self.page else f"Frame"
                        logger.info(f"【{self.pure_user_id}】在{frame_info}找到滑块按钮: {selector}")
                        slider_button = element
                        break
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】选择器 {selector} 未找到: {e}")
                    continue
            
            # 如果在找到容器的frame中没找到按钮，尝试在所有frame中查找
            # 无论容器是在主页面还是frame中找到的，如果按钮找不到，都应该在所有frame中查找
            if not slider_button:
                logger.warning(f"【{self.pure_user_id}】在找到容器的位置未找到按钮，尝试在所有frame中查找...")
                try:
                    frames = self.page.frames
                    for idx, frame in enumerate(frames):
                        # 如果容器是在frame中找到的，跳过已经检查过的frame
                        if found_frame and found_frame != self.page and frame == found_frame:
                            continue
                        # 如果容器是在主页面找到的，跳过主页面（因为已经检查过了）
                        if found_frame == self.page and frame == self.page:
                            continue
                            
                        for selector in button_selectors:
                            try:
                                element = None
                                if fast_mode:
                                    # 快速模式：直接使用 query_selector
                                    element = frame.query_selector(selector)
                                else:
                                    # 正常模式：先尝试wait_for_selector
                                    try:
                                        element = frame.wait_for_selector(selector, timeout=2000)
                                    except:
                                        time.sleep(0.3)  # 等待元素加载
                                        element = frame.query_selector(selector)
                                
                                if element:
                                    try:
                                        is_visible = element.is_visible()
                                        if is_visible:
                                            logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块按钮: {selector}")
                                            slider_button = element
                                            found_frame = frame  # 更新found_frame
                                            break
                                        else:
                                            logger.debug(f"【{self.pure_user_id}】在Frame {idx} 找到元素但不可见: {selector}")
                                    except:
                                        # 如果无法检查可见性，仍然使用该元素
                                        logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块按钮（无法检查可见性）: {selector}")
                                        slider_button = element
                                        found_frame = frame  # 更新found_frame
                                        break
                            except Exception as e:
                                logger.debug(f"【{self.pure_user_id}】Frame {idx} 选择器 {selector} 查找失败: {e}")
                                continue
                        if slider_button:
                            break
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】在所有frame中查找按钮时出错: {e}")
            
            # 如果还是没找到，尝试在主页面查找（如果之前没在主页面查找过）
            if not slider_button and found_frame != self.page:
                logger.warning(f"【{self.pure_user_id}】在所有frame中未找到按钮，尝试在主页面查找...")
                for selector in button_selectors:
                    try:
                        element = None
                        if fast_mode:
                            # 快速模式：直接使用 query_selector
                            element = self.page.query_selector(selector)
                        else:
                            # 正常模式：使用 wait_for_selector
                            element = self.page.wait_for_selector(selector, timeout=2000)
                        
                        if element:
                            try:
                                if element.is_visible():
                                    logger.info(f"【{self.pure_user_id}】在主页面找到滑块按钮: {selector}")
                                    slider_button = element
                                    found_frame = self.page  # 更新found_frame
                                    break
                                else:
                                    logger.debug(f"【{self.pure_user_id}】在主页面找到元素但不可见: {selector}")
                            except:
                                # 如果无法检查可见性，仍然使用该元素
                                logger.info(f"【{self.pure_user_id}】在主页面找到滑块按钮（无法检查可见性）: {selector}")
                                slider_button = element
                                found_frame = self.page  # 更新found_frame
                                break
                    except Exception as e:
                        logger.debug(f"【{self.pure_user_id}】主页面选择器 {selector} 查找失败: {e}")
                        continue
            
            # 如果还是没找到，尝试使用更宽松的查找方式（不检查可见性）
            if not slider_button:
                logger.warning(f"【{self.pure_user_id}】使用宽松模式查找滑块按钮（不检查可见性）...")
                # 先在所有frame中查找
                try:
                    frames = self.page.frames
                    for idx, frame in enumerate(frames):
                        for selector in button_selectors[:3]:  # 只使用前3个最常用的选择器
                            try:
                                element = frame.query_selector(selector)
                                if element:
                                    logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块按钮（宽松模式）: {selector}")
                                    slider_button = element
                                    found_frame = frame
                                    break
                            except:
                                continue
                        if slider_button:
                            break
                except:
                    pass
                
                # 如果还是没找到，在主页面查找
                if not slider_button:
                    for selector in button_selectors[:3]:
                        try:
                            element = self.page.query_selector(selector)
                            if element:
                                logger.info(f"【{self.pure_user_id}】在主页面找到滑块按钮（宽松模式）: {selector}")
                                slider_button = element
                                found_frame = self.page
                                break
                        except:
                            continue
            
            if not slider_button:
                logger.error(f"【{self.pure_user_id}】未找到任何滑块按钮（主页面和所有frame都已检查，包括宽松模式）")
                return slider_container, None, None
            
            # 定义滑块轨道选择器
            track_selectors = [
                "#nc_1_n1t",
                ".nc_scale",
                ".nc_1_n1t",
                "[class*='track']",
                "[class*='scale']"
            ]
            
            # 查找滑块轨道（在找到按钮的同一个frame中查找，因为按钮和轨道应该在同一个位置）
            slider_track = None
            # 使用找到按钮的frame来查找轨道
            track_search_frame = found_frame if found_frame and found_frame != self.page else self.page
            
            for selector in track_selectors:
                try:
                    element = None
                    if fast_mode:
                        # 快速模式：直接使用 query_selector
                        element = track_search_frame.query_selector(selector)
                    else:
                        # 正常模式：使用 wait_for_selector
                        if track_search_frame == self.page:
                            element = self.page.wait_for_selector(selector, timeout=3000)
                        else:
                            # 在frame中使用query_selector
                            element = track_search_frame.query_selector(selector)
                    
                    if element:
                        try:
                            if not element.is_visible():
                                element = None
                        except:
                            pass
                    
                    if element:
                        frame_info = "主页面" if track_search_frame == self.page else f"Frame"
                        logger.info(f"【{self.pure_user_id}】在{frame_info}找到滑块轨道: {selector}")
                        slider_track = element
                        break
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】选择器 {selector} 未找到: {e}")
                    continue
            
            # 如果在找到按钮的frame中没找到轨道，先点击frame激活它，然后再查找
            if not slider_track and track_search_frame and track_search_frame != self.page:
                logger.warning(f"【{self.pure_user_id}】在已知Frame中未找到轨道，尝试点击frame激活后再查找...")
                try:
                    # 点击frame以激活它，让轨道出现
                    # 尝试点击frame中的容器或按钮来激活
                    if slider_container:
                        try:
                            slider_container.click(timeout=1000)
                            logger.info(f"【{self.pure_user_id}】已点击滑块容器以激活frame")
                            time.sleep(0.3)  # 等待轨道出现
                        except:
                            pass
                    elif slider_button:
                        try:
                            slider_button.click(timeout=1000)
                            logger.info(f"【{self.pure_user_id}】已点击滑块按钮以激活frame")
                            time.sleep(0.3)  # 等待轨道出现
                        except:
                            pass
                    
                    # 再次在同一个frame中查找轨道
                    for selector in track_selectors:
                        try:
                            element = track_search_frame.query_selector(selector)
                            if element:
                                try:
                                    if element.is_visible():
                                        logger.info(f"【{self.pure_user_id}】点击frame后在Frame中找到滑块轨道: {selector}")
                                        slider_track = element
                                        break
                                except:
                                    # 如果无法检查可见性，也尝试使用
                                    logger.info(f"【{self.pure_user_id}】点击frame后在Frame中找到滑块轨道（无法检查可见性）: {selector}")
                                    slider_track = element
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】点击frame后查找轨道时出错: {e}")
                
                # 如果点击frame后还是没找到，尝试在所有frame中查找
                if not slider_track:
                    logger.warning(f"【{self.pure_user_id}】点击frame后仍未找到轨道，尝试在所有frame中查找...")
                    try:
                        frames = self.page.frames
                        for idx, frame in enumerate(frames):
                            if frame == track_search_frame:
                                continue  # 跳过已经检查过的frame
                            for selector in track_selectors:
                                try:
                                    element = frame.query_selector(selector)
                                    if element:
                                        try:
                                            if element.is_visible():
                                                logger.info(f"【{self.pure_user_id}】在Frame {idx} 找到滑块轨道: {selector}")
                                                slider_track = element
                                                break
                                        except:
                                            pass
                                except:
                                    continue
                            if slider_track:
                                break
                    except Exception as e:
                        logger.debug(f"【{self.pure_user_id}】在所有frame中查找轨道时出错: {e}")
            
            # 如果还是没找到，尝试在主页面查找
            if not slider_track:
                logger.warning(f"【{self.pure_user_id}】在所有frame中未找到轨道，尝试在主页面查找...")
                for selector in track_selectors:
                    try:
                        element = self.page.wait_for_selector(selector, timeout=1000)
                        if element:
                            logger.info(f"【{self.pure_user_id}】在主页面找到滑块轨道: {selector}")
                            slider_track = element
                            break
                    except:
                        continue
            
            if not slider_track:
                logger.error(f"【{self.pure_user_id}】未找到任何滑块轨道（主页面和所有frame都已检查）")
                return slider_container, slider_button, None
            
            # 保存找到滑块的frame引用，供后续验证使用
            if found_frame and found_frame != self.page:
                self._detected_slider_frame = found_frame
                logger.info(f"【{self.pure_user_id}】保存滑块frame引用，供后续验证使用")
            elif found_frame == self.page:
                # 如果是在主页面找到的，设置为None
                self._detected_slider_frame = None
            
            return slider_container, slider_button, slider_track
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】查找滑块元素时出错: {str(e)}")
            return None, None, None
    
    def is_scratch_captcha(self):
        """检测是否为刮刮乐类型验证码"""
        try:
            page_content = self.page.content()
            # 检测刮刮乐特征（更精确的判断）
            # 必须包含明确的刮刮乐特征词
            scratch_required = ['scratch-captcha', 'scratch-captcha-btn', 'scratch-captcha-slider']
            has_scratch_feature = any(keyword in page_content for keyword in scratch_required)
            
            # 或者包含刮刮乐的指令文字
            scratch_instructions = ['Release the slider', 'pillows', 'fully appears', 'after', 'appears']
            has_scratch_instruction = sum(1 for keyword in scratch_instructions if keyword in page_content) >= 2
            
            is_scratch = has_scratch_feature or has_scratch_instruction
            
            if is_scratch:
                logger.info(f"【{self.pure_user_id}】🎨 检测到刮刮乐类型验证码")
            
            return is_scratch
        except Exception as e:
            logger.debug(f"【{self.pure_user_id}】检测刮刮乐类型时出错: {e}")
            return False
    
    def calculate_slide_distance(self, slider_button: ElementHandle, slider_track: ElementHandle):
        """计算滑动距离 - 增强精度，支持刮刮乐

        优先使用 JavaScript getBoundingClientRect 获取 CSS 像素级精确值，
        Playwright mouse 事件坐标就是 CSS 像素，不需要乘以 devicePixelRatio。
        """
        try:
            # 获取滑块按钮位置和大小
            button_box = slider_button.bounding_box()
            if not button_box:
                logger.error(f"【{self.pure_user_id}】无法获取滑块按钮位置")
                return 0
            
            # 获取滑块轨道位置和大小
            track_box = slider_track.bounding_box()
            if not track_box:
                logger.error(f"【{self.pure_user_id}】无法获取滑块轨道位置")
                return 0
            
            # 🎨 检测是否为刮刮乐类型
            is_scratch = self.is_scratch_captcha()
            
            # 优先使用 JavaScript 精确计算（CSS 像素，与 mouse 事件坐标系一致）
            try:
                result = self.page.evaluate("""
                    () => {
                        const selectors = [
                            ['#nc_1_n1z', '#nc_1_n1t'],
                            ['.nc_iconfont', '.nc_scale'],
                            ['#scratch-captcha-btn', '.scratch-captcha-slider'],
                        ];
                        for (const [btnSel, trkSel] of selectors) {
                            const btn = document.querySelector(btnSel);
                            const trk = document.querySelector(trkSel);
                            if (btn && trk) {
                                const bRect = btn.getBoundingClientRect();
                                const tRect = trk.getBoundingClientRect();
                                // CSS 像素距离，Playwright mouse 不需要 dpr 换算
                                return {
                                    distance: tRect.width - bRect.width,
                                    buttonWidth: bRect.width,
                                    trackWidth: tRect.width,
                                    dpr: window.devicePixelRatio || 1
                                };
                            }
                        }
                        return null;
                    }
                """)
                
                if result and result.get('distance', 0) > 0:
                    precise_distance = result['distance']
                    logger.info(
                        f"【{self.pure_user_id}】JS精确距离: {precise_distance:.2f}px "
                        f"(轨道{result['trackWidth']:.1f}px - 按钮{result['buttonWidth']:.1f}px, "
                        f"DPR={result['dpr']})"
                    )
                    
                    if is_scratch:
                        scratch_ratio = random.uniform(0.25, 0.35)
                        final = precise_distance * scratch_ratio
                        logger.warning(f"【{self.pure_user_id}】🎨 刮刮乐：{scratch_ratio*100:.1f}% = {final:.2f}px")
                        return final
                    
                    # 微小高斯偏移（真人不会精确到小数点后）
                    return precise_distance + random.gauss(0, 0.4)

            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】JS精确计算失败，用bounding_box后备: {e}")
            
            # 后备方案：bounding_box
            slide_distance = track_box["width"] - button_box["width"]
            
            if is_scratch:
                scratch_ratio = random.uniform(0.25, 0.35)
                slide_distance = slide_distance * scratch_ratio
                logger.warning(f"【{self.pure_user_id}】🎨 刮刮乐（后备）：{slide_distance:.2f}px")
            else:
                slide_distance += random.gauss(0, 0.4)
            
            logger.info(
                f"【{self.pure_user_id}】后备距离: {slide_distance:.2f}px "
                f"(轨道{track_box['width']}px, 按钮{button_box['width']}px)"
            )
            return slide_distance
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】计算滑动距离时出错: {str(e)}")
            return 0
    
    def check_verification_success_fast(self, slider_button: ElementHandle):
        """检查验证结果 - 极速模式"""
        try:
            logger.info(f"【{self.pure_user_id}】检查验证结果（极速模式）...")
            
            # 确定滑块所在的frame（如果已知）
            target_frame = None
            if hasattr(self, '_detected_slider_frame') and self._detected_slider_frame is not None:
                target_frame = self._detected_slider_frame
                logger.info(f"【{self.pure_user_id}】在已知Frame中检查验证结果")
                # 先检查frame是否还存在（未被分离）
                try:
                    # 尝试访问frame的属性来检查是否被分离
                    _ = target_frame.url if hasattr(target_frame, 'url') else None
                except Exception as frame_check_error:
                    error_msg = str(frame_check_error).lower()
                    # 如果frame被分离（detached），说明验证成功，容器已消失
                    if 'detached' in error_msg or 'disconnected' in error_msg:
                        logger.info(f"【{self.pure_user_id}】✓ Frame已被分离，验证成功")
                        return True
            else:
                target_frame = self.page
                logger.info(f"【{self.pure_user_id}】在主页面检查验证结果")
            
            # 等待一小段时间让验证结果出现
            time.sleep(0.3)
            
            # 核心逻辑：首先检查frame容器状态
            # 如果容器消失，直接返回成功；如果容器还在，检查失败提示
            def check_container_status():
                """检查容器状态，返回(存在, 可见)"""
                try:
                    if target_frame == self.page:
                        container = self.page.query_selector(".nc-container")
                    else:
                        # 检查frame是否还存在（未被分离）
                        try:
                            # 再次检查frame是否被分离
                            _ = target_frame.url if hasattr(target_frame, 'url') else None
                            container = target_frame.query_selector(".nc-container")
                        except Exception as frame_error:
                            error_msg = str(frame_error).lower()
                            # 如果frame被分离（detached），说明容器已经不存在
                            if 'detached' in error_msg or 'disconnected' in error_msg:
                                logger.info(f"【{self.pure_user_id}】Frame已被分离，容器不存在")
                                return (False, False)
                            # 其他错误，继续尝试
                            raise frame_error
                    
                    if container is None:
                        return (False, False)  # 容器不存在
                    
                    try:
                        is_visible = container.is_visible()
                        return (True, is_visible)
                    except Exception as vis_error:
                        vis_error_msg = str(vis_error).lower()
                        # 如果元素被分离，说明容器不存在
                        if 'detached' in vis_error_msg or 'disconnected' in vis_error_msg:
                            logger.info(f"【{self.pure_user_id}】容器元素已被分离，容器不存在")
                            return (False, False)
                        # 无法检查可见性，假设存在且可见
                        return (True, True)
                except Exception as e:
                    error_msg = str(e).lower()
                    # 如果frame或元素被分离，说明容器不存在
                    if 'detached' in error_msg or 'disconnected' in error_msg:
                        logger.info(f"【{self.pure_user_id}】Frame或容器已被分离，容器不存在")
                        return (False, False)
                    # 其他错误，保守处理，假设存在
                    logger.warning(f"【{self.pure_user_id}】检查容器状态时出错: {e}")
                    return (True, True)
            
            # 第一次检查容器状态
            container_exists, container_visible = check_container_status()
            
            # 如果容器不存在或不可见，直接返回成功
            if not container_exists or not container_visible:
                logger.info(f"【{self.pure_user_id}】✓ 滑块容器已消失（不存在或不可见），验证成功")
                return True
            
            # 容器还在，需要等待更长时间并检查失败提示
            logger.info(f"【{self.pure_user_id}】滑块容器仍存在且可见，等待验证结果...")
            time.sleep(1.2)  # 等待验证结果
            
            # 再次检查容器状态
            container_exists, container_visible = check_container_status()
            
            # 如果容器消失了，返回成功
            if not container_exists or not container_visible:
                logger.info(f"【{self.pure_user_id}】✓ 滑块容器已消失，验证成功")
                return True
            
            # 容器还在，检查是否有验证失败提示
            logger.info(f"【{self.pure_user_id}】滑块容器仍存在，检查验证失败提示...")
            if self.check_verification_failure():
                logger.warning(f"【{self.pure_user_id}】检测到验证失败提示，验证失败")
                return False
            
            # 容器还在，但没有失败提示，可能还在验证中或验证失败
            # 再等待一小段时间后再次检查
            time.sleep(0.5)
            container_exists, container_visible = check_container_status()
            
            if not container_exists or not container_visible:
                logger.info(f"【{self.pure_user_id}】✓ 滑块容器已消失，验证成功")
                return True
            
            # 容器仍然存在，且没有失败提示，可能是验证失败但没有显示失败提示
            # 或者验证还在进行中，但为了不无限等待，返回失败
            logger.warning(f"【{self.pure_user_id}】滑块容器仍存在且可见，且未检测到失败提示，但验证可能失败")
            return False
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】检查验证结果时出错: {str(e)}")
            return False
    
    def check_page_changed(self):
        """检查页面是否改变"""
        try:
            # 检查页面标题是否改变
            current_title = self.page.title()
            logger.info(f"【{self.pure_user_id}】当前页面标题: {current_title}")
            
            # 如果标题不再是验证码相关，说明页面已改变
            if "captcha" not in current_title.lower() and "验证" not in current_title and "拦截" not in current_title:
                logger.info(f"【{self.pure_user_id}】页面标题已改变，验证成功")
                return True
            
            # 检查URL是否改变
            current_url = self.page.url
            logger.info(f"【{self.pure_user_id}】当前页面URL: {current_url}")
            
            # 如果URL不再包含验证码相关参数，说明页面已改变
            if "captcha" not in current_url.lower() and "action=captcha" not in current_url:
                logger.info(f"【{self.pure_user_id}】页面URL已改变，验证成功")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】检查页面改变时出错: {e}")
            return False
    
    def check_verification_failure(self):
        """检查验证失败提示

        核心逻辑：
          1. 优先在 NC 容器内用 JS 取文字，匹配失败关键词（最精确）
          2. 备用：用 text= 精确文本选择器（只匹配失败文字，不会误判）
          3. 不再使用 .nc-lang-cnt 等宽泛选择器！
             原因：.nc-lang-cnt 同时包含正常指引文字"请按住滑块，拖动到最右边"，
                   会导致每次滑动后都被误判为失败。
        """
        try:
            logger.info(f"【{self.pure_user_id}】检查验证失败提示...")

            # 等待失败提示出现（NC 失败动画约 800ms）
            time.sleep(1.0)

            # ── 方法 1：JS 获取容器文字，精确匹配失败关键词 ──────────────
            # 在已知 frame 或主页面执行 JS
            target_frame = getattr(self, '_detected_slider_frame', None) or self.page
            try:
                container_text = target_frame.evaluate("""
                    () => {
                        const selectors = [
                            '.nc-container',
                            '#baxia-dialog-content',
                            '.nc_wrapper',
                            '#nocaptcha'
                        ];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el) return el.innerText || '';
                        }
                        return '';
                    }
                """)
                if container_text:
                    # 只匹配真正的失败文字，不匹配正常操作提示
                    failure_keywords = [
                        "验证失败",
                        "点击框体重试",
                        "请重试",
                        "验证码错误",
                        "滑动验证失败",
                        "操作太快",
                        "网络异常",
                    ]
                    # 明确排除正常指引文字（防止误判）
                    normal_instructions = [
                        "请按住滑块",
                        "拖动到最右边",
                        "向右滑动",
                        "请拖动滑块",
                    ]
                    is_normal = any(n in container_text for n in normal_instructions)

                    if not is_normal:
                        for kw in failure_keywords:
                            if kw in container_text:
                                logger.info(f"【{self.pure_user_id}】容器内检测到失败关键词: [{kw}]，容器文字: {container_text[:60]}")
                                return True
            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】JS容器文字提取失败: {e}")

            # ── 方法 2：精确文本选择器（不使用宽泛的类名） ───────────────
            # 只匹配确定是失败提示的文字，不匹配 .nc-lang-cnt 这类宽泛选择器
            precise_failure_selectors = [
                "text=验证失败，点击框体重试",
                "text=验证失败",
                "text=点击框体重试",
                "text=操作太快，请稍后重试",
                "text=网络异常，请稍后重试",
            ]

            for selector in precise_failure_selectors:
                try:
                    element = target_frame.query_selector(selector)
                    if element and element.is_visible():
                        try:
                            text = element.text_content() or ""
                        except:
                            text = ""
                        logger.info(f"【{self.pure_user_id}】精确选择器命中失败提示: {selector}，文本: {text[:50]}")
                        return True
                except:
                    continue

            logger.info(f"【{self.pure_user_id}】未找到验证失败提示，判定为未失败")
            return False

        except Exception as e:
            logger.error(f"【{self.pure_user_id}】检查验证失败时出错: {e}")
            return False
    
    def _analyze_failure(self, attempt: int, slide_distance: float, trajectory_data: dict):
        """分析失败原因并记录"""
        try:
            failure_reason = {
                "attempt": attempt,
                "slide_distance": slide_distance,
                "total_steps": trajectory_data.get("total_steps", 0),
                "base_delay": trajectory_data.get("base_delay", 0),
                "final_left_px": trajectory_data.get("final_left_px", 0),
                "completion_used": trajectory_data.get("completion_used", False),
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录失败信息
            logger.warning(f"【{self.pure_user_id}】第{attempt}次尝试失败 - 距离:{slide_distance}px, "
                         f"步数:{failure_reason['total_steps']}, "
                         f"最终位置:{failure_reason['final_left_px']}px")
            
            return failure_reason
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】分析失败原因时出错: {e}")
            return {}
    
    def solve_slider(self, max_retries: int = 3, fast_mode: bool = False):
        """处理滑块验证 — v3（集成 OpenCV 缺口识别 + PyAutoGUI 备用引擎）

        策略：
          第 1 次：Playwright + 归一化轨迹（OpenCV 距离优先）
          第 2 次：Playwright + 更保守参数
          第 3 次：PyAutoGUI + 贝塞尔曲线（如可用），否则继续 Playwright
        """
        failure_records = []

        for attempt in range(1, max_retries + 1):
            try:
                current_strategy, attempt_params = self._build_attempt_trajectory_params(attempt)
                self.trajectory_params = attempt_params
                logger.info(f"【{self.pure_user_id}】开始处理滑块验证... (第{attempt}/{max_retries}次尝试)")
                logger.info(
                    f"【{self.pure_user_id}】当前策略: {current_strategy}, "
                    f"steps={attempt_params['total_steps_range']}, "
                    f"delay={attempt_params['base_delay_range']}"
                )

                # 非首次：等待 + 重置
                if attempt > 1:
                    retry_delay = random.uniform(1.0, 1.8)
                    logger.debug(f"【{self.pure_user_id}】等待{retry_delay:.2f}秒后重试...")
                    time.sleep(retry_delay)
                    self._reset_slider_challenge()

                # ── 1. 查找滑块元素 ──────────────────────────────────────────
                slider_container, slider_button, slider_track = self.find_slider_elements(fast_mode=fast_mode)
                if not all([slider_container, slider_button, slider_track]):
                    logger.error(f"【{self.pure_user_id}】滑块元素查找失败")
                    continue

                # ── 2. 计算滑动距离（OpenCV 优先 → DOM 后备）───────────────
                opencv_dist = self._opencv_detect_gap()
                if opencv_dist and opencv_dist > 10:
                    slide_distance = opencv_dist
                    logger.info(f"【{self.pure_user_id}】🔍 使用 OpenCV 缺口距离: {slide_distance:.1f}px")
                else:
                    slide_distance = self.calculate_slide_distance(slider_button, slider_track)
                    if slide_distance <= 0:
                        logger.error(f"【{self.pure_user_id}】滑动距离计算失败")
                        continue

                # ── 3. 生成归一化轨迹 ──────────────────────────────────────
                trajectory = self.generate_human_trajectory(slide_distance)
                if not trajectory:
                    logger.error(f"【{self.pure_user_id}】轨迹生成失败")
                    continue

                # ── 4. 执行滑动 ────────────────────────────────────────────
                # 最后一次且 PyAutoGUI 可用且非 headless → 切换备用引擎
                use_pyautogui = (
                    attempt == max_retries
                    and _PYAUTOGUI_AVAILABLE
                    and not getattr(self, 'headless', True)
                )
                if use_pyautogui:
                    logger.warning(f"【{self.pure_user_id}】🖱️  切换 PyAutoGUI 备用引擎（第{attempt}次）")

                button_box = slider_button.bounding_box() or {}
                sx = button_box.get("x", 0) + button_box.get("width", 0) / 2
                sy = button_box.get("y", 0) + button_box.get("height", 0) / 2

                if not self.simulate_slide(
                    slider_button, trajectory,
                    use_pyautogui=use_pyautogui,
                    start_x=sx, start_y=sy,
                    distance=slide_distance
                ):
                    logger.error(f"【{self.pure_user_id}】滑动模拟失败")
                    continue

                # ── 5. 检查结果 ────────────────────────────────────────────
                if self.check_verification_success_fast(slider_button):
                    logger.info(f"【{self.pure_user_id}】✅ 滑块验证成功! (第{attempt}次尝试)")
                    strategy_stats.record_attempt(attempt, current_strategy, success=True)
                    if self.enable_learning and hasattr(self, 'current_trajectory_data'):
                        self._save_success_record(self.current_trajectory_data)
                    strategy_stats.log_summary()
                    return True
                else:
                    logger.warning(f"【{self.pure_user_id}】❌ 第{attempt}次验证失败")
                    strategy_stats.record_attempt(attempt, current_strategy, success=False)
                    if hasattr(self, 'current_trajectory_data'):
                        failure_info = self._analyze_failure(attempt, slide_distance, self.current_trajectory_data)
                        failure_records.append(failure_info)
                    if attempt < max_retries:
                        continue

            except Exception as e:
                logger.error(f"【{self.pure_user_id}】第{attempt}次处理出错: {e}")
                if attempt < max_retries:
                    continue

        # 所有尝试都失败
        logger.error(f"【{self.pure_user_id}】滑块验证失败，已尝试{max_retries}次")
        try:
            if hasattr(self, 'page') and self.page:
                screenshots_dir = "static/uploads/images"
                os.makedirs(screenshots_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = os.path.join(screenshots_dir, f"slider_fail_{self.pure_user_id}_{timestamp}.jpg")
                self.page.screenshot(path=screenshot_path, full_page=False)
                logger.info(f"【{self.pure_user_id}】失败截图: {screenshot_path.replace(chr(92), '/')}")
        except Exception as screenshot_e:
            logger.warning(f"【{self.pure_user_id}】保存截图出错: {screenshot_e}")

        if failure_records and _is_verbose_slider_logging_enabled():
            logger.info(f"【{self.pure_user_id}】失败分析摘要:")
            for record in failure_records:
                logger.info(f"  - 第{record['attempt']}次: 距离{record['slide_distance']}px, "
                            f"步数{record.get('total_steps','?')}步, 最终位置{record.get('final_left_px','N/A')}px")

        strategy_stats.log_summary()
        return False
    
    def close_browser(self):
        """安全关闭浏览器并清理资源"""
        logger.debug(f"【{self.pure_user_id}】开始清理资源...")
        
        # 清理页面
        try:
            if hasattr(self, 'page') and self.page:
                self.page.close()
                logger.debug(f"【{self.pure_user_id}】页面已关闭")
                self.page = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】关闭页面时出错: {e}")
        
        # 清理上下文
        try:
            if hasattr(self, 'context') and self.context:
                self.context.close()
                logger.debug(f"【{self.pure_user_id}】上下文已关闭")
                self.context = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】关闭上下文时出错: {e}")
        
        # 【修复】同步关闭浏览器，确保资源真正释放
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()  # 直接同步关闭，不使用异步任务
                logger.debug(f"【{self.pure_user_id}】浏览器已关闭")
                self.browser = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】关闭浏览器时出错: {e}")
        
        # 【修复】同步停止Playwright，确保资源真正释放
        try:
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()  # 直接同步停止，不使用异步任务
                logger.info(f"【{self.pure_user_id}】Playwright已停止")
                self.playwright = None
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】停止Playwright时出错: {e}")
        
        # 清理临时目录
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.debug(f"【{self.pure_user_id}】临时目录已清理: {self.temp_dir}")
                self.temp_dir = None  # 设置为None，防止重复清理
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】清理临时目录时出错: {e}")
        
        # 注销实例（最后执行，确保其他清理完成）
        try:
            concurrency_manager.unregister_instance(self.user_id)
            stats = concurrency_manager.get_stats()
            logger.info(f"【{self.pure_user_id}】实例已注销，当前并发: {stats['active_count']}/{stats['max_concurrent']}，等待队列: {stats['queue_length']}")
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】注销实例时出错: {e}")
        
        logger.info(f"【{self.pure_user_id}】资源清理完成")
    
    def __del__(self):
        """析构函数，确保资源释放（保险机制）"""
        try:
            # 检查是否有未关闭的浏览器
            if hasattr(self, 'browser') and self.browser:
                logger.warning(f"【{self.pure_user_id}】析构函数检测到未关闭的浏览器，执行清理")
                self.close_browser()
        except Exception as e:
            # 析构函数中不要抛出异常
            logger.debug(f"【{self.pure_user_id}】析构函数清理时出错: {e}")
    
    # ==================== Playwright 登录辅助方法 ====================
    
    def _check_login_success_by_element(self, page) -> bool:
        """通过页面元素检测登录是否成功
        
        Args:
            page: Page对象
        
        Returns:
            bool: 登录成功返回True，否则返回False
        """
        try:
            # 检查目标元素
            selector = '.rc-virtual-list-holder-inner'
            logger.info(f"【{self.pure_user_id}】========== 检查登录状态（通过页面元素） ==========")
            logger.info(f"【{self.pure_user_id}】检查选择器: {selector}")
            
            # 查找元素
            element = page.query_selector(selector)
            
            if element:
                # 获取元素的子元素数量
                child_count = element.evaluate('el => el.children.length')
                inner_html = element.inner_html()
                inner_text = element.inner_text() if element.is_visible() else ""
                
                logger.info(f"【{self.pure_user_id}】找到目标元素:")
                logger.info(f"【{self.pure_user_id}】  - 子元素数量: {child_count}")
                logger.info(f"【{self.pure_user_id}】  - 是否可见: {element.is_visible()}")
                logger.info(f"【{self.pure_user_id}】  - innerText长度: {len(inner_text)}")
                logger.info(f"【{self.pure_user_id}】  - innerHTML长度: {len(inner_html)}")
                
                # 判断是否有数据：子元素数量大于0
                if child_count > 0:
                    logger.success(f"【{self.pure_user_id}】✅ 登录成功！检测到列表有 {child_count} 个子元素")
                    logger.info(f"【{self.pure_user_id}】================================================")
                    return True
                else:
                    logger.debug(f"【{self.pure_user_id}】列表为空，登录未完成")
                    logger.info(f"【{self.pure_user_id}】================================================")
                    return False
            else:
                logger.debug(f"【{self.pure_user_id}】未找到目标元素: {selector}")
                logger.info(f"【{self.pure_user_id}】================================================")
                return False
                
        except Exception as e:
            logger.debug(f"【{self.pure_user_id}】检查登录状态时出错: {e}")
            import traceback
            logger.debug(f"【{self.pure_user_id}】错误堆栈: {traceback.format_exc()}")
            return False
    
    def _check_login_error(self, page) -> tuple:
        """检测登录是否出现错误（如账密错误）
        
        Args:
            page: Page对象
        
        Returns:
            tuple: (has_error, error_message) - 是否有错误，错误消息
        """
        try:
            logger.debug(f"【{self.pure_user_id}】检查登录错误...")
            
            # 检测账密错误
            error_selectors = [
                '.login-error-msg',  # 主要的错误消息类
                '[class*="error-msg"]',  # 包含error-msg的类
                'div:has-text("账密错误")',  # 包含"账密错误"文本的div
                'text=账密错误',  # 直接文本匹配
            ]
            
            # 在主页面和所有frame中查找
            frames_to_check = [page] + page.frames
            
            for frame in frames_to_check:
                try:
                    for selector in error_selectors:
                        try:
                            element = frame.query_selector(selector)
                            if element and element.is_visible():
                                error_text = element.inner_text()
                                logger.error(f"【{self.pure_user_id}】❌ 检测到登录错误: {error_text}")
                                return True, error_text
                        except:
                            continue
                            
                    # 也检查页面HTML中是否包含错误文本
                    try:
                        content = frame.content()
                        if '账密错误' in content or '账号密码错误' in content or '用户名或密码错误' in content:
                            logger.error(f"【{self.pure_user_id}】❌ 页面内容中检测到账密错误")
                            return True, "账密错误"
                    except:
                        pass
                        
                except:
                    continue
            
            return False, None
            
        except Exception as e:
            logger.debug(f"【{self.pure_user_id}】检查登录错误时出错: {e}")
            return False, None
    
    def _detect_qr_code_verification(self, page) -> tuple:
        """检测是否存在二维码/人脸验证（排除滑块验证）
        
        Args:
            page: Page对象
        
        Returns:
            tuple: (has_qr, qr_frame) - 是否有二维码/人脸验证，验证frame
                   (False, None) - 如果检测到滑块验证，会先处理滑块，然后返回
        """
        try:
            logger.info(f"【{self.pure_user_id}】检测二维码/人脸验证...")
            
            # 先检查是否是滑块验证，如果是滑块验证，立即处理并返回
            slider_selectors = [
                '#nc_1_n1z',
                '.nc-container',
                '.nc_scale',
                '.nc-wrapper',
                '.nc_iconfont',
                '[class*="nc_"]'
            ]
            
            # 在主页面和所有frame中检查滑块
            frames_to_check = [page] + list(page.frames)
            for frame in frames_to_check:
                try:
                    for selector in slider_selectors:
                        try:
                            element = frame.query_selector(selector)
                            if element and element.is_visible():
                                logger.info(f"【{self.pure_user_id}】检测到滑块验证元素，立即处理滑块: {selector}")
                                # 检测到滑块验证，记录是在哪个frame中找到的
                                frame_info = "主页面" if frame == page else f"Frame: {frame.url if hasattr(frame, 'url') else '未知'}"
                                logger.info(f"【{self.pure_user_id}】滑块元素位置: {frame_info}")
                                
                                # 保存找到滑块的frame，供find_slider_elements使用
                                # 如果是在frame中找到的，保存frame引用；如果在主页面找到，保存None
                                if frame == page:
                                    self._detected_slider_frame = None  # 主页面
                                else:
                                    self._detected_slider_frame = frame  # 保存frame引用
                                
                                # 检测到滑块验证，立即处理
                                logger.warning(f"【{self.pure_user_id}】检测到滑块验证，开始自动处理...")
                                slider_success = self.solve_slider(max_retries=3)
                                if slider_success:
                                    logger.success(f"【{self.pure_user_id}】✅ 滑块验证成功！")
                                    time.sleep(3)  # 等待滑块验证后的状态更新
                                else:
                                    # 3次失败后，刷新页面重试
                                    logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理3次都失败，刷新页面后重试...")
                                    try:
                                        self.page.reload(wait_until="domcontentloaded", timeout=30000)
                                        logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                        time.sleep(2)
                                        slider_success = self.solve_slider(max_retries=3)
                                        if not slider_success:
                                            logger.error(f"【{self.pure_user_id}】❌ 刷新后滑块验证仍然失败")
                                        else:
                                            logger.success(f"【{self.pure_user_id}】✅ 刷新后滑块验证成功！")
                                            time.sleep(3)
                                    except Exception as e:
                                        logger.error(f"【{self.pure_user_id}】❌ 页面刷新失败: {e}")
                                
                                # 清理临时变量
                                if hasattr(self, '_detected_slider_frame'):
                                    delattr(self, '_detected_slider_frame')
                                
                                # 返回 False, None 表示不是二维码/人脸验证（已处理滑块）
                                return False, None
                        except:
                            continue
                except:
                    continue
            
            # 检测所有frames中的二维码/人脸验证
            # 首先检查是否有 alibaba-login-box iframe（人脸验证或短信验证）
            try:
                iframes = page.query_selector_all('iframe')
                for iframe in iframes:
                    try:
                        iframe_id = iframe.get_attribute('id')
                        if iframe_id == 'alibaba-login-box':
                            logger.info(f"【{self.pure_user_id}】✅ 检测到 alibaba-login-box iframe（人脸验证/短信验证）")
                            frame = iframe.content_frame()
                            if frame:
                                logger.info(f"【{self.pure_user_id}】人脸验证/短信验证Frame URL: {frame.url if hasattr(frame, 'url') else '未知'}")
                                
                                # 尝试自动点击"其他验证方式"，然后找到"通过拍摄脸部"的验证按钮
                                face_verify_url = self._get_face_verification_url(frame)
                                if face_verify_url:
                                    logger.info(f"【{self.pure_user_id}】✅ 获取到人脸验证链接: {face_verify_url}")
                                    
                                    # 截图并保存
                                    screenshot_path = None
                                    try:
                                        # 等待页面加载完成
                                        time.sleep(2)
                                        
                                        # 先删除该账号的旧截图
                                        import glob
                                        screenshots_dir = "static/uploads/images"
                                        os.makedirs(screenshots_dir, exist_ok=True)
                                        old_screenshots = glob.glob(os.path.join(screenshots_dir, f"face_verify_{self.pure_user_id}_*.jpg"))
                                        for old_file in old_screenshots:
                                            try:
                                                os.remove(old_file)
                                                logger.info(f"【{self.pure_user_id}】删除旧的验证截图: {old_file}")
                                            except Exception as e:
                                                logger.warning(f"【{self.pure_user_id}】删除旧截图失败: {e}")
                                        
                                        # 尝试截取iframe元素的截图
                                        screenshot_bytes = None
                                        try:
                                            # 获取iframe元素并截图
                                            iframe_element = page.query_selector('iframe#alibaba-login-box')
                                            if iframe_element:
                                                screenshot_bytes = iframe_element.screenshot()
                                                logger.info(f"【{self.pure_user_id}】已截取iframe元素")
                                            else:
                                                # 如果找不到iframe，截取整个页面
                                                screenshot_bytes = page.screenshot(full_page=False)
                                                logger.info(f"【{self.pure_user_id}】已截取整个页面")
                                        except Exception as e:
                                            logger.warning(f"【{self.pure_user_id}】截取iframe失败，尝试截取整个页面: {e}")
                                            screenshot_bytes = page.screenshot(full_page=False)
                                        
                                        if screenshot_bytes:
                                            # 生成带时间戳的文件名并直接保存
                                            from datetime import datetime
                                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                            filename = f"face_verify_{self.pure_user_id}_{timestamp}.jpg"
                                            file_path = os.path.join(screenshots_dir, filename)
                                            
                                            try:
                                                with open(file_path, 'wb') as f:
                                                    f.write(screenshot_bytes)
                                                # 返回相对路径
                                                screenshot_path = file_path.replace('\\', '/')
                                                logger.info(f"【{self.pure_user_id}】✅ 人脸验证截图已保存: {screenshot_path}")
                                            except Exception as e:
                                                logger.error(f"【{self.pure_user_id}】保存截图失败: {e}")
                                                screenshot_path = None
                                        else:
                                            logger.warning(f"【{self.pure_user_id}】⚠️ 截图失败，无法获取截图数据")
                                    except Exception as e:
                                        logger.error(f"【{self.pure_user_id}】截图时出错: {e}")
                                        import traceback
                                        logger.debug(traceback.format_exc())
                                    
                                    # 创建一个特殊的frame对象，包含截图路径
                                    class VerificationFrame:
                                        def __init__(self, original_frame, verify_url, screenshot_path=None):
                                            self._original_frame = original_frame
                                            self.verify_url = verify_url
                                            self.screenshot_path = screenshot_path
                                        
                                        def __getattr__(self, name):
                                            return getattr(self._original_frame, name)
                                    
                                    return True, VerificationFrame(frame, face_verify_url, screenshot_path)
                                
                                return True, frame
                    except Exception as e:
                        logger.debug(f"【{self.pure_user_id}】检查iframe时出错: {e}")
                        continue
            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】检查alibaba-login-box iframe时出错: {e}")
            
            for idx, frame in enumerate(page.frames):
                try:
                    frame_url = frame.url
                    logger.debug(f"【{self.pure_user_id}】检查Frame {idx} 是否有二维码: {frame_url}")
                    
                    # 检查frame URL是否包含 mini_login（人脸验证或短信验证页面）
                    if 'mini_login' in frame_url:
                        # 进一步确认不是滑块验证
                        is_slider = False
                        for selector in slider_selectors:
                            try:
                                element = frame.query_selector(selector)
                                if element and element.is_visible():
                                    is_slider = True
                                    break
                            except:
                                continue
                        
                        if not is_slider:
                            logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 检测到 mini_login 页面（人脸验证/短信验证）")
                            logger.info(f"【{self.pure_user_id}】人脸验证/短信验证Frame URL: {frame_url}")
                            return True, frame
                    
                    # 检查frame的父iframe是否是alibaba-login-box
                    try:
                        # 尝试通过frame的父元素查找
                        frame_element = frame.frame_element()
                        if frame_element:
                            parent_iframe_id = frame_element.get_attribute('id')
                            if parent_iframe_id == 'alibaba-login-box':
                                logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 检测到 alibaba-login-box（人脸验证/短信验证）")
                                logger.info(f"【{self.pure_user_id}】人脸验证/短信验证Frame URL: {frame_url}")
                                return True, frame
                    except:
                        pass
                    
                    # 先检查这个frame是否是滑块验证
                    is_slider_frame = False
                    for selector in slider_selectors:
                        try:
                            element = frame.query_selector(selector)
                            if element and element.is_visible():
                                logger.debug(f"【{self.pure_user_id}】Frame {idx} 包含滑块验证元素，跳过")
                                is_slider_frame = True
                                break
                        except:
                            continue
                    
                    if is_slider_frame:
                        continue  # 跳过滑块验证的frame
                    
                    # 二维码验证的选择器（更精确，避免误判滑块验证）
                    qr_selectors = [
                        'img[alt*="二维码"]',
                        'img[alt*="扫码"]',
                        'img[src*="qrcode"]',
                        'canvas[class*="qrcode"]',
                        '.qr-code',
                        '#qr-code',
                        '[class*="qr-code"]',
                        '[id*="qr-code"]'
                    ]
                    
                    # 检查是否有真正的二维码图片（不是滑块验证中的qrcode类）
                    for selector in qr_selectors:
                        try:
                            element = frame.query_selector(selector)
                            if element and element.is_visible():
                                # 进一步验证：检查是否包含滑块元素，如果包含则跳过
                                has_slider_in_frame = False
                                for slider_sel in slider_selectors:
                                    try:
                                        slider_elem = frame.query_selector(slider_sel)
                                        if slider_elem and slider_elem.is_visible():
                                            has_slider_in_frame = True
                                            break
                                    except:
                                        continue
                                
                                if not has_slider_in_frame:
                                    logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 检测到二维码验证: {selector}")
                                    logger.info(f"【{self.pure_user_id}】二维码Frame URL: {frame_url}")
                                    return True, frame
                        except:
                            continue
                    
                    # 人脸验证的关键词（更精确）
                    face_keywords = ['拍摄脸部', '人脸验证', '人脸识别', '面部验证', '请进行人脸验证', '请完成人脸识别']
                    try:
                        frame_content = frame.content()
                        # 检查是否包含人脸验证关键词，但不包含滑块相关关键词
                        has_face_keyword = False
                        for keyword in face_keywords:
                            if keyword in frame_content:
                                has_face_keyword = True
                                break
                        
                        # 如果包含人脸验证关键词，且不包含滑块关键词，则认为是人脸验证
                        if has_face_keyword:
                            slider_keywords = ['滑块', '拖动', 'nc_', 'nc-container']
                            has_slider_keyword = any(keyword in frame_content for keyword in slider_keywords)
                            
                            if not has_slider_keyword:
                                logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 检测到人脸验证")
                                logger.info(f"【{self.pure_user_id}】人脸验证Frame URL: {frame_url}")
                                return True, frame
                    except:
                        pass
                        
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】检查Frame {idx} 失败: {e}")
                    continue
            
            logger.info(f"【{self.pure_user_id}】未检测到二维码/人脸验证")
            return False, None
            
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】检测二维码/人脸验证时出错: {e}")
            return False, None
    
    def _get_face_verification_url(self, frame) -> str:
        """在alibaba-login-box frame中，点击'其他验证方式'，然后找到'通过拍摄脸部'的验证按钮，获取链接"""
        try:
            logger.info(f"【{self.pure_user_id}】开始查找人脸验证链接...")
            
            # 等待frame加载完成
            time.sleep(2)
            
            # 查找"其他验证方式"链接并点击
            other_verify_clicked = False
            try:
                # 尝试通过文本内容查找所有链接
                all_links = frame.query_selector_all('a')
                for link in all_links:
                    try:
                        text = link.inner_text()
                        if '其他验证方式' in text or ('其他' in text and '验证' in text):
                            logger.info(f"【{self.pure_user_id}】找到'其他验证方式'链接，点击中...")
                            link.click()
                            time.sleep(2)  # 等待页面切换
                            other_verify_clicked = True
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】查找'其他验证方式'链接时出错: {e}")
            
            if not other_verify_clicked:
                logger.warning(f"【{self.pure_user_id}】未找到'其他验证方式'链接，可能已经在验证方式选择页面")
            
            # 等待页面加载
            time.sleep(2)
            
            # 查找"通过拍摄脸部"相关的验证按钮，获取href并点击按钮
            face_verify_url = None
            
            # 方法1: 使用JavaScript精确查找，获取href并点击按钮（根据HTML结构：li > div.desc包含"通过 拍摄脸部" + a.ui-button包含"立即验证"）
            try:
                href = frame.evaluate("""
                    () => {
                        // 查找所有li元素
                        const listItems = document.querySelectorAll('li');
                        for (let li of listItems) {
                            // 查找包含"通过 拍摄脸部"或"通过拍摄脸部"的desc div，但不能包含"手机"
                            const descDiv = li.querySelector('div.desc');
                            if (descDiv && !descDiv.innerText.includes('手机') && (descDiv.innerText.includes('通过 拍摄脸部') || descDiv.innerText.includes('通过拍摄脸部') || descDiv.innerText.includes('拍摄脸部'))) {
                                // 在同一li中查找"立即验证"按钮
                                const verifyButton = li.querySelector('a.ui-button, a.ui-button-small, button');
                                if (verifyButton && verifyButton.innerText && verifyButton.innerText.includes('立即验证')) {
                                    // 获取按钮的href属性
                                    const href = verifyButton.href || verifyButton.getAttribute('href') || null;
                                    // 点击按钮
                                    verifyButton.click();
                                    // 返回href
                                    return href;
                                }
                            }
                        }
                        return null;
                    }
                """)
                if href:
                    face_verify_url = href
                    logger.info(f"【{self.pure_user_id}】通过JavaScript找到'通过拍摄脸部'验证按钮的href并已点击: {face_verify_url}")
            except Exception as e:
                logger.debug(f"【{self.pure_user_id}】方法1（JavaScript）查找失败: {e}")
            
            # 方法2: 如果方法1失败，使用Playwright API查找并点击
            if not face_verify_url:
                try:
                    # 查找所有li元素
                    list_items = frame.query_selector_all('li')
                    for li in list_items:
                        try:
                            # 查找desc div
                            desc_div = li.query_selector('div.desc')
                            if desc_div:
                                desc_text = desc_div.inner_text()
                                if '手机' not in desc_text and ('通过 拍摄脸部' in desc_text or '通过拍摄脸部' in desc_text or '拍摄脸部' in desc_text):
                                    logger.info(f"【{self.pure_user_id}】找到'通过拍摄脸部'选项（方法2）")
                                    # 在同一li中查找验证按钮
                                    verify_button = li.query_selector('a.ui-button, a.ui-button-small, button')
                                    if verify_button:
                                        button_text = verify_button.inner_text()
                                        if '立即验证' in button_text:
                                            # 获取按钮的href属性
                                            href = verify_button.get_attribute('href')
                                            if href:
                                                face_verify_url = href
                                                logger.info(f"【{self.pure_user_id}】找到'通过拍摄脸部'验证按钮的href: {face_verify_url}")
                                                # 点击按钮
                                                logger.info(f"【{self.pure_user_id}】点击'立即验证'按钮...")
                                                verify_button.click()
                                                logger.info(f"【{self.pure_user_id}】已点击'立即验证'按钮")
                                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"【{self.pure_user_id}】方法2查找失败: {e}")
            
            if face_verify_url:
                # 如果是相对路径，转换为绝对路径
                if not face_verify_url.startswith('http'):
                    base_url = frame.url.split('/iv/')[0] if '/iv/' in frame.url else 'https://passport.goofish.com'
                    if face_verify_url.startswith('/'):
                        face_verify_url = base_url + face_verify_url
                    else:
                        face_verify_url = base_url + '/' + face_verify_url
                
                return face_verify_url
            else:
                logger.warning(f"【{self.pure_user_id}】未找到人脸验证链接，返回原始frame URL")
                return frame.url if hasattr(frame, 'url') else None
                
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】获取人脸验证链接时出错: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def login_with_password_playwright(
        self,
        account: str,
        password: str,
        show_browser: bool = False,
        notification_callback: Optional[Callable] = None,
        return_verification_result: bool = False,
    ) -> dict:
        """使用Playwright进行密码登录（新方法，替代DrissionPage）
        
        Args:
            account: 登录账号（必填）
            password: 登录密码（必填）
            show_browser: 是否显示浏览器窗口（默认False为无头模式）
            notification_callback: 可选的通知回调函数，用于发送二维码/人脸验证通知（接受错误消息字符串作为参数）
        
        Returns:
            dict: Cookie字典，失败返回None
        """
        try:
            # 检查日期有效性
            if not self._check_date_validity():
                logger.error(f"【{self.pure_user_id}】日期验证失败，无法执行登录")
                return None
            
            # 验证必需参数
            if not account or not password:
                logger.error(f"【{self.pure_user_id}】账号或密码不能为空")
                return None
            
            browser_mode = "有头" if show_browser else "无头"
            logger.info(f"【{self.pure_user_id}】开始{browser_mode}模式密码登录流程（使用Playwright）...")
            logger.info(f"【{self.pure_user_id}】账号: {account}")
            logger.info("=" * 60)
            
            # 启动浏览器（使用持久化上下文）
            import os
            user_data_dir = os.path.join(os.getcwd(), 'browser_data', f'user_{self.pure_user_id}')
            os.makedirs(user_data_dir, exist_ok=True)
            logger.info(f"【{self.pure_user_id}】使用用户数据目录: {user_data_dir}")
            debug_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_dir = os.path.join('static', 'uploads', 'images', 'password_login_debug')
            os.makedirs(debug_dir, exist_ok=True)
            logger.info(f"【{self.pure_user_id}】密码登录调试目录: {debug_dir}")
            
            # 设置浏览器启动参数
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--lang=zh-CN',  # 设置浏览器语言为中文
            ]
            
            # 在启动Playwright之前，重新检查和设置浏览器路径
            # 确保使用正确的浏览器版本（避免版本不匹配问题）
            import sys
            from pathlib import Path
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe，检查exe同目录下的浏览器
                exe_dir = Path(sys.executable).parent
                playwright_dir = exe_dir / 'playwright'
                
                if playwright_dir.exists():
                    chromium_dirs = list(playwright_dir.glob('chromium-*'))
                    # 找到第一个完整的浏览器目录
                    for chromium_dir in chromium_dirs:
                        chrome_exe = chromium_dir / 'chrome-win' / 'chrome.exe'
                        if chrome_exe.exists() and chrome_exe.stat().st_size > 0:
                            # 清除旧的环境变量，使用实际存在的浏览器
                            if 'PLAYWRIGHT_BROWSERS_PATH' in os.environ:
                                old_path = os.environ['PLAYWRIGHT_BROWSERS_PATH']
                                if old_path != str(playwright_dir):
                                    logger.info(f"【{self.pure_user_id}】清除旧的环境变量: {old_path}")
                                    del os.environ['PLAYWRIGHT_BROWSERS_PATH']
                            # 设置正确的环境变量
                            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(playwright_dir)
                            logger.info(f"【{self.pure_user_id}】已设置PLAYWRIGHT_BROWSERS_PATH: {playwright_dir}")
                            logger.info(f"【{self.pure_user_id}】使用浏览器版本: {chromium_dir.name}")
                            break
            
            # 启动浏览器
            playwright = sync_playwright().start()
            context = playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=not show_browser,
                args=browser_args,
                viewport={'width': 1980, 'height': 1024},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                locale='zh-CN',  # 设置浏览器区域为中文
                accept_downloads=True,
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'  # 设置HTTP Accept-Language header为中文
                }
            )
            logger.info(f"【{self.pure_user_id}】已设置浏览器语言为中文（zh-CN）")
            
            browser = context.browser
            page = context.new_page()
            logger.info(f"【{self.pure_user_id}】浏览器已成功启动（{browser_mode}模式）")

            def _sanitize_debug_stage(stage: str) -> str:
                safe_stage = []
                for ch in str(stage):
                    if ch.isalnum() or ch in ('-', '_'):
                        safe_stage.append(ch)
                    else:
                        safe_stage.append('_')
                return ''.join(safe_stage).strip('_') or 'unknown'

            def _capture_login_debug(stage: str, note: str = "") -> Optional[str]:
                try:
                    frame_urls = []
                    try:
                        frame_urls = [getattr(frame, 'url', '') for frame in page.frames[:5]]
                    except Exception:
                        pass

                    logger.info(
                        f"【{self.pure_user_id}】调试阶段={stage}; "
                        f"url={page.url}; title={page.title()}; "
                        f"frames={len(page.frames)}; note={note or '无'}"
                    )
                    if frame_urls:
                        logger.info(f"【{self.pure_user_id}】调试Frame URL样本: {frame_urls}")

                    screenshot_name = (
                        f"password_login_{self.pure_user_id}_{debug_run_id}_"
                        f"{_sanitize_debug_stage(stage)}.png"
                    )
                    screenshot_path = os.path.join(debug_dir, screenshot_name)
                    page.screenshot(path=screenshot_path, full_page=True, timeout=15000)
                    logger.info(f"【{self.pure_user_id}】调试截图已保存: {screenshot_path}")
                    return screenshot_path.replace("\\", "/")
                except Exception as debug_err:
                    logger.warning(f"【{self.pure_user_id}】记录调试信息失败(stage={stage}): {debug_err}")
                    return None
            
            try:
                # 访问登录页面
                login_url = "https://www.goofish.com/im"
                logger.info(f"【{self.pure_user_id}】访问登录页面: {login_url}")
                logger.info(f"【{self.pure_user_id}】开始页面导航，等待 networkidle...")
                page.goto(login_url, wait_until='networkidle', timeout=60000)
                logger.info(f"【{self.pure_user_id}】页面导航完成")
                
                # 等待页面加载
                wait_time = 2 if not show_browser else 2
                logger.info(f"【{self.pure_user_id}】等待页面加载（{wait_time}秒）...")
                time.sleep(wait_time)
                
                # 页面诊断信息
                logger.info(f"【{self.pure_user_id}】========== 页面诊断信息 ==========")
                logger.info(f"【{self.pure_user_id}】当前URL: {page.url}")
                logger.info(f"【{self.pure_user_id}】页面标题: {page.title()}")
                logger.info(f"【{self.pure_user_id}】=====================================")
                _capture_login_debug("page_loaded", "登录页初始状态")
                
                # 【步骤1】查找登录frame（闲鱼登录通常在iframe中）
                logger.info(f"【{self.pure_user_id}】查找登录frame...")
                login_frame = None
                found_login_form = False
                
                # 等待页面和iframe加载完成
                logger.info(f"【{self.pure_user_id}】等待页面和iframe加载...")
                time.sleep(1)  # 增加等待时间，确保iframe加载完成
                
                # 先尝试在主页面查找登录表单
                logger.info(f"【{self.pure_user_id}】在主页面查找登录表单...")
                main_page_selectors = [
                    '#fm-login-id',
                    'input[name="fm-login-id"]',
                    'input[placeholder*="手机号"]',
                    'input[placeholder*="邮箱"]',
                    '.fm-login-id',
                    '#J_LoginForm input[type="text"]'
                ]
                for selector in main_page_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element and element.is_visible():
                            logger.info(f"【{self.pure_user_id}】✓ 在主页面找到登录表单元素: {selector}")
                            # 主页面找到登录表单，使用page作为login_frame
                            login_frame = page
                            found_login_form = True
                            break
                    except:
                        continue
                
                # 如果主页面没找到，再在iframe中查找
                if not found_login_form:
                    iframes = page.query_selector_all('iframe')
                    logger.info(f"【{self.pure_user_id}】找到 {len(iframes)} 个 iframe")
                    
                    # 尝试在iframe中查找登录表单
                    for idx, iframe in enumerate(iframes):
                        try:
                            frame = iframe.content_frame()
                            if frame:
                                # 等待iframe内容加载
                                try:
                                    frame.wait_for_selector('#fm-login-id', timeout=3000)
                                except:
                                    pass
                                
                                # 检查是否有登录表单
                                login_selectors = [
                                    '#fm-login-id',
                                    'input[name="fm-login-id"]',
                                    'input[placeholder*="手机号"]',
                                    'input[placeholder*="邮箱"]'
                                ]
                                for selector in login_selectors:
                                    try:
                                        element = frame.query_selector(selector)
                                        if element and element.is_visible():
                                            logger.info(f"【{self.pure_user_id}】✓ 在Frame {idx} 找到登录表单: {selector}")
                                            login_frame = frame
                                            found_login_form = True
                                            break
                                    except:
                                        continue
                                
                                if found_login_form:
                                    break
                                else:
                                    # Frame存在但没有登录表单，可能是滑块验证frame
                                    logger.debug(f"【{self.pure_user_id}】Frame {idx} 未找到登录表单")
                        except Exception as e:
                            logger.debug(f"【{self.pure_user_id}】检查Frame {idx}时出错: {e}")
                            continue
                
                # 【情况1】找到frame且找到登录表单 → 正常登录流程
                if found_login_form:
                    logger.info(f"【{self.pure_user_id}】找到登录表单，开始正常登录流程...")
                
                # 【情况2】找到frame但未找到登录表单 → 可能已登录，直接检测滑块
                elif len(iframes) > 0:
                    logger.warning(f"【{self.pure_user_id}】找到iframe但未找到登录表单，可能已登录，检测滑块...")
                    
                    # 先将page和context保存到实例变量（供solve_slider使用）
                    original_page = self.page
                    original_context = self.context
                    original_browser = self.browser
                    original_playwright = self.playwright
                    
                    self.page = page
                    self.context = context
                    self.browser = browser
                    self.playwright = playwright
                    
                    try:
                        # 检测滑块元素（在主页面和所有frame中查找）
                        slider_selectors = [
                            '#nc_1_n1z',
                            '.nc-container',
                            '.nc_scale',
                            '.nc-wrapper'
                        ]
                        
                        has_slider = False
                        detected_slider_frame = None
                        
                        # 先在主页面查找
                        for selector in slider_selectors:
                            try:
                                element = page.query_selector(selector)
                                if element and element.is_visible():
                                    logger.info(f"【{self.pure_user_id}】✅ 在主页面检测到滑块验证元素: {selector}")
                                    has_slider = True
                                    detected_slider_frame = None  # None表示主页面
                                    break
                            except:
                                continue
                        
                        # 如果主页面没找到，在所有frame中查找
                        if not has_slider:
                            for idx, iframe in enumerate(iframes):
                                try:
                                    frame = iframe.content_frame()
                                    if frame:
                                        # 等待frame内容加载
                                        try:
                                            frame.wait_for_load_state('domcontentloaded', timeout=2000)
                                        except:
                                            pass
                                        
                                        for selector in slider_selectors:
                                            try:
                                                element = frame.query_selector(selector)
                                                if element and element.is_visible():
                                                    logger.info(f"【{self.pure_user_id}】✅ 在Frame {idx} 检测到滑块验证元素: {selector}")
                                                    has_slider = True
                                                    detected_slider_frame = frame
                                                    break
                                            except:
                                                continue
                                        
                                        if has_slider:
                                            break
                                except Exception as e:
                                    logger.debug(f"【{self.pure_user_id}】检查Frame {idx}时出错: {e}")
                                    continue
                        
                        if has_slider:
                            # 设置检测到的frame，供solve_slider使用
                            self._detected_slider_frame = detected_slider_frame
                            
                            logger.warning(f"【{self.pure_user_id}】检测到滑块验证，开始处理...")
                            time.sleep(3)
                            slider_success = self.solve_slider(max_retries=3)
                            
                            if not slider_success:
                                # 3次失败后，刷新页面重试
                                logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理3次都失败，刷新页面后重试...")
                                try:
                                    page.reload(wait_until="domcontentloaded", timeout=30000)
                                    logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                    time.sleep(2)
                                    slider_success = self.solve_slider(max_retries=3)
                                    if not slider_success:
                                        logger.error(f"【{self.pure_user_id}】❌ 刷新后滑块验证仍然失败")
                                        return None
                                    else:
                                        logger.success(f"【{self.pure_user_id}】✅ 刷新后滑块验证成功！")
                                except Exception as e:
                                    logger.error(f"【{self.pure_user_id}】❌ 页面刷新失败: {e}")
                                    return None
                            else:
                                logger.success(f"【{self.pure_user_id}】✅ 滑块验证成功！")
                            
                            # 等待页面加载和状态更新（第一次等待3秒）
                            logger.info(f"【{self.pure_user_id}】等待3秒，让页面加载完成...")
                            time.sleep(3)
                            
                            # 第一次检查登录状态
                            login_success = self._check_login_success_by_element(page)
                            
                            # 如果第一次没检测到，再等待5秒后重试
                            if not login_success:
                                logger.info(f"【{self.pure_user_id}】第一次检测未发现登录状态，等待5秒后重试...")
                                time.sleep(5)
                                login_success = self._check_login_success_by_element(page)
                            
                            if login_success:
                                logger.success(f"【{self.pure_user_id}】✅ 滑块验证后登录成功")
                                
                                # 只有在登录成功后才获取Cookie
                                cookies_dict = {}
                                try:
                                    cookies_list = context.cookies()
                                    for cookie in cookies_list:
                                        cookies_dict[cookie.get('name', '')] = cookie.get('value', '')
                                    
                                    logger.info(f"【{self.pure_user_id}】成功获取Cookie，包含 {len(cookies_dict)} 个字段")
                                    
                                    if cookies_dict:
                                        logger.success("✅ Cookie有效")
                                        return cookies_dict
                                    else:
                                        logger.error("❌ Cookie为空")
                                        return None
                                except Exception as e:
                                    logger.error(f"【{self.pure_user_id}】获取Cookie失败: {e}")
                                    return None
                            else:
                                logger.warning(f"【{self.pure_user_id}】⚠️ 滑块验证后登录状态不明确，不获取Cookie")
                                return None
                        else:
                            logger.info(f"【{self.pure_user_id}】未检测到滑块验证")
                            
                            # 未检测到滑块时，检查是否已登录
                            if self._check_login_success_by_element(page):
                                logger.success(f"【{self.pure_user_id}】✅ 检测到已登录状态")
                                
                                # 只有在登录成功后才获取Cookie
                                cookies_dict = {}
                                try:
                                    cookies_list = context.cookies()
                                    for cookie in cookies_list:
                                        cookies_dict[cookie.get('name', '')] = cookie.get('value', '')
                                    
                                    logger.info(f"【{self.pure_user_id}】成功获取Cookie，包含 {len(cookies_dict)} 个字段")
                                    
                                    if cookies_dict:
                                        logger.success("✅ Cookie有效")
                                        return cookies_dict
                                    else:
                                        logger.error("❌ Cookie为空")
                                        return None
                                except Exception as e:
                                    logger.error(f"【{self.pure_user_id}】获取Cookie失败: {e}")
                                    return None
                            else:
                                logger.warning(f"【{self.pure_user_id}】⚠️ 未检测到滑块且未登录，不获取Cookie")
                                return None
                    
                    finally:
                        # 恢复原始值
                        self.page = original_page
                        self.context = original_context
                        self.browser = original_browser
                        self.playwright = original_playwright
                
                # 【情况3】未找到frame → 检查是否已登录
                else:
                    logger.warning(f"【{self.pure_user_id}】未找到任何iframe，检查是否已登录...")
                    
                    # 等待一下让页面完全加载
                    time.sleep(2)
                    
                    # 检查是否已登录（只有过了滑块才会有这个元素）
                    if self._check_login_success_by_element(page):
                        logger.success(f"【{self.pure_user_id}】✅ 检测到已登录状态")
                        
                        # 获取Cookie
                        cookies_dict = {}
                        try:
                            cookies_list = context.cookies()
                            for cookie in cookies_list:
                                cookies_dict[cookie.get('name', '')] = cookie.get('value', '')
                            
                            if cookies_dict:
                                logger.success("✅ 登录成功！Cookie有效")
                                return cookies_dict
                            else:
                                logger.error("❌ Cookie为空")
                                return None
                        except Exception as e:
                            logger.error(f"【{self.pure_user_id}】获取Cookie失败: {e}")
                            return None
                    else:
                        logger.error(f"【{self.pure_user_id}】❌ 未找到登录表单且未检测到已登录")
                        return None
                
                # 点击密码登录标签
                logger.info(f"【{self.pure_user_id}】查找密码登录标签...")
                try:
                    password_tab = login_frame.query_selector('a.password-login-tab-item')
                    if password_tab:
                        logger.info(f"【{self.pure_user_id}】✓ 找到密码登录标签，点击中...")
                        password_tab.click()
                        time.sleep(1.5)
                except Exception as e:
                    logger.warning(f"【{self.pure_user_id}】查找密码登录标签失败: {e}")
                
                # 输入账号
                logger.info(f"【{self.pure_user_id}】输入账号: {account}")
                time.sleep(1)
                
                account_input = login_frame.query_selector('#fm-login-id')
                if account_input:
                    logger.info(f"【{self.pure_user_id}】✓ 找到账号输入框")
                    account_input.fill(account)
                    logger.info(f"【{self.pure_user_id}】✓ 账号已输入")
                    time.sleep(random.uniform(0.5, 1.0))
                else:
                    logger.error(f"【{self.pure_user_id}】✗ 未找到账号输入框")
                    return None
                
                # 输入密码
                logger.info(f"【{self.pure_user_id}】输入密码...")
                password_input = login_frame.query_selector('#fm-login-password')
                if password_input:
                    password_input.fill(password)
                    logger.info(f"【{self.pure_user_id}】✓ 密码已输入")
                    time.sleep(random.uniform(0.5, 1.0))
                else:
                    logger.error(f"【{self.pure_user_id}】✗ 未找到密码输入框")
                    _capture_login_debug("password_input_missing", "未找到密码输入框")
                    return None
                
                # 勾选用户协议
                logger.info(f"【{self.pure_user_id}】查找并勾选用户协议...")
                try:
                    agreement_checkbox = login_frame.query_selector('#fm-agreement-checkbox')
                    if agreement_checkbox:
                        is_checked = agreement_checkbox.evaluate('el => el.checked')
                        if not is_checked:
                            agreement_checkbox.click()
                            time.sleep(0.3)
                            logger.info(f"【{self.pure_user_id}】✓ 用户协议已勾选")
                except Exception as e:
                    logger.warning(f"【{self.pure_user_id}】勾选用户协议失败: {e}")
                
                # 点击登录按钮
                logger.info(f"【{self.pure_user_id}】点击登录按钮...")
                time.sleep(1)
                
                login_button = login_frame.query_selector('button.password-login')
                if login_button:
                    logger.info(f"【{self.pure_user_id}】✓ 找到登录按钮")
                    login_button.click()
                    logger.info(f"【{self.pure_user_id}】✓ 登录按钮已点击")
                    _capture_login_debug("after_login_click", "已点击登录按钮")
                else:
                    logger.error(f"【{self.pure_user_id}】✗ 未找到登录按钮")
                    _capture_login_debug("login_button_missing", "未找到登录按钮")
                    return None
                
                # 【关键】点击登录后，等待一下再检测滑块
                logger.info(f"【{self.pure_user_id}】========== 登录后监控 ==========")
                logger.info(f"【{self.pure_user_id}】等待页面响应...")
                time.sleep(3)
                
                # 【核心】检测是否有滑块验证 → 如果有，调用 solve_slider() 处理
                logger.info(f"【{self.pure_user_id}】检测是否有滑块验证...")
                
                # 先将page和context保存到实例变量（供solve_slider使用）
                original_page = self.page
                original_context = self.context
                original_browser = self.browser
                original_playwright = self.playwright
                
                self.page = page
                self.context = context
                self.browser = browser
                self.playwright = playwright
                
                try:
                    # 检查页面内容是否包含滑块相关元素
                    page_content = page.content()
                    has_slider = False
                    
                    # 检测滑块元素
                    slider_selectors = [
                        '#nc_1_n1z',
                        '.nc-container',
                        '.nc_scale',
                        '.nc-wrapper'
                    ]
                    
                    for selector in slider_selectors:
                        try:
                            element = page.query_selector(selector)
                            if element and element.is_visible():
                                logger.info(f"【{self.pure_user_id}】✅ 检测到滑块验证元素: {selector}")
                                has_slider = True
                                break
                        except:
                            continue
                    
                    if has_slider:
                        logger.warning(f"【{self.pure_user_id}】检测到滑块验证，开始处理...")
                        
                        # 【复用】直接调用 solve_slider() 方法处理滑块
                        slider_success = self.solve_slider(max_retries=3)
                        
                        if slider_success:
                            logger.success(f"【{self.pure_user_id}】✅ 滑块验证成功！")
                        else:
                            # 3次失败后，刷新页面重试
                            logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理3次都失败，刷新页面后重试...")
                            try:
                                page.reload(wait_until="domcontentloaded", timeout=30000)
                                logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                time.sleep(2)
                                slider_success = self.solve_slider(max_retries=3)
                                if not slider_success:
                                    logger.error(f"【{self.pure_user_id}】❌ 刷新后滑块验证仍然失败")
                                    return None
                                else:
                                    logger.success(f"【{self.pure_user_id}】✅ 刷新后滑块验证成功！")
                            except Exception as e:
                                logger.error(f"【{self.pure_user_id}】❌ 页面刷新失败: {e}")
                                return None
                    else:
                        logger.info(f"【{self.pure_user_id}】未检测到滑块验证")
                    
                    # 等待登录完成
                    logger.info(f"【{self.pure_user_id}】等待登录完成...")
                    time.sleep(5)
                    
                    # 再次检查是否有滑块验证（可能在等待过程中出现）
                    logger.info(f"【{self.pure_user_id}】等待1秒后检查是否有滑块验证...")
                    time.sleep(1)
                    has_slider_after_wait = False
                    for selector in slider_selectors:
                        try:
                            element = page.query_selector(selector)
                            if element and element.is_visible():
                                logger.info(f"【{self.pure_user_id}】✅ 等待后检测到滑块验证元素: {selector}")
                                has_slider_after_wait = True
                                break
                        except:
                            continue
                    
                    if has_slider_after_wait:
                        logger.warning(f"【{self.pure_user_id}】检测到滑块验证，开始处理...")
                        slider_success = self.solve_slider(max_retries=3)
                        if slider_success:
                            logger.success(f"【{self.pure_user_id}】✅ 滑块验证成功！")
                            time.sleep(3)  # 等待滑块验证后的状态更新
                        else:
                            # 3次失败后，刷新页面重试
                            logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理3次都失败，刷新页面后重试...")
                            try:
                                page.reload(wait_until="domcontentloaded", timeout=30000)
                                logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                time.sleep(2)
                                slider_success = self.solve_slider(max_retries=3)
                                if not slider_success:
                                    logger.error(f"【{self.pure_user_id}】❌ 刷新后滑块验证仍然失败")
                                    return None
                                else:
                                    logger.success(f"【{self.pure_user_id}】✅ 刷新后滑块验证成功！")
                                    time.sleep(3)
                            except Exception as e:
                                logger.error(f"【{self.pure_user_id}】❌ 页面刷新失败: {e}")
                                return None
                    
                    # 检查登录状态
                    logger.info(f"【{self.pure_user_id}】等待1秒后检查登录状态...")
                    time.sleep(1)
                    login_success = self._check_login_success_by_element(page)
                    
                    if login_success:
                        logger.success(f"【{self.pure_user_id}】✅ 登录验证成功！")
                    else:
                        # 检查是否有账密错误
                        logger.info(f"【{self.pure_user_id}】等待1秒后检查是否有账密错误...")
                        time.sleep(1)
                        has_error, error_message = self._check_login_error(page)
                        if has_error:
                            logger.error(f"【{self.pure_user_id}】❌ 登录失败：{error_message}")
                            # 抛出异常，包含错误消息，让调用者能够获取
                            raise Exception(error_message if error_message else "登录失败，请检查账号密码是否正确")
                        
                        # 【重要】检测是否需要二维码/人脸验证（排除滑块验证）
                        # 注意：_detect_qr_code_verification 如果检测到滑块，会立即处理滑块
                        logger.info(f"【{self.pure_user_id}】等待1秒后检测是否需要二维码/人脸验证...")
                        time.sleep(1)
                        logger.info(f"【{self.pure_user_id}】检测是否需要二维码/人脸验证...")
                        has_qr, qr_frame = self._detect_qr_code_verification(page)
                        
                        # 如果检测到滑块并已处理，再次检查登录状态
                        if not has_qr:
                            # 滑块可能已被处理，再次检查登录状态
                            logger.info(f"【{self.pure_user_id}】等待1秒后再次检查登录状态...")
                            time.sleep(1)
                            login_success_after_slider = self._check_login_success_by_element(page)
                            if login_success_after_slider:
                                logger.success(f"【{self.pure_user_id}】✅ 滑块验证后，登录验证成功！")
                                login_success = True
                            else:
                                # 滑块验证后仍未登录成功，继续检测二维码/人脸验证（此时应该不会再检测到滑块）
                                logger.info(f"【{self.pure_user_id}】等待1秒后继续检测是否需要二维码/人脸验证...")
                                time.sleep(1)
                                logger.info(f"【{self.pure_user_id}】滑块验证后，继续检测是否需要二维码/人脸验证...")
                                has_qr, qr_frame = self._detect_qr_code_verification(page)
                        
                        if has_qr:
                            logger.warning(f"【{self.pure_user_id}】⚠️ 检测到二维码/人脸验证")
                            logger.info(f"【{self.pure_user_id}】请在浏览器中完成二维码/人脸验证")
                            verification_debug_screenshot = _capture_login_debug("verification_detected", "检测到二维码或人脸验证")
                            
                            # 获取验证链接URL和截图路径
                            frame_url = None
                            screenshot_path = None
                            if qr_frame:
                                try:
                                    # 检查是否有验证链接（从VerificationFrame对象）
                                    if hasattr(qr_frame, 'verify_url') and qr_frame.verify_url:
                                        frame_url = qr_frame.verify_url
                                        logger.info(f"【{self.pure_user_id}】使用获取到的人脸验证链接: {frame_url}")
                                    else:
                                        frame_url = qr_frame.url if hasattr(qr_frame, 'url') else None
                                    
                                    # 检查是否有截图路径（从VerificationFrame对象）
                                    if hasattr(qr_frame, 'screenshot_path') and qr_frame.screenshot_path:
                                        screenshot_path = qr_frame.screenshot_path
                                        logger.info(f"【{self.pure_user_id}】使用获取到的人脸验证截图: {screenshot_path}")
                                except Exception as e:
                                    logger.warning(f"【{self.pure_user_id}】获取frame信息失败: {e}")
                                    import traceback
                                    logger.debug(traceback.format_exc())

                            if not screenshot_path and verification_debug_screenshot:
                                screenshot_path = verification_debug_screenshot
                            
                            # 显示验证信息
                            if screenshot_path:
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)
                                logger.warning(f"【{self.pure_user_id}】二维码/人脸验证截图:")
                                logger.warning(f"【{self.pure_user_id}】{screenshot_path}")
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)
                            elif frame_url:
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)
                                logger.warning(f"【{self.pure_user_id}】二维码/人脸验证链接:")
                                logger.warning(f"【{self.pure_user_id}】{frame_url}")
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)
                            else:
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)
                                logger.warning(f"【{self.pure_user_id}】二维码/人脸验证已检测到，但无法获取验证信息")
                                logger.warning(f"【{self.pure_user_id}】请在浏览器中查看验证页面")
                                logger.warning(f"【{self.pure_user_id}】" + "=" * 60)

                            if return_verification_result:
                                logger.warning(f"【{self.pure_user_id}】按配置立即返回验证需求结果，不继续阻塞等待")
                                return {
                                    "__password_login_status": "verification_required",
                                    "verification_type": "qr_or_face",
                                    "verification_url": frame_url,
                                    "verification_screenshot_path": screenshot_path,
                                    "message": "账号密码登录需要扫码或人脸验证",
                                }
                            
                            logger.info(f"【{self.pure_user_id}】请在浏览器中完成验证，程序将持续等待...")
                            
                            # 【重要】发送通知给客户
                            if notification_callback:
                                try:
                                    if screenshot_path or frame_url:
                                        # 构造清晰的通知消息
                                        if screenshot_path:
                                            
                                            notification_msg = (
                                                f"⚠️ 账号密码登录需要人脸验证\n\n"
                                                f"账号: {self.pure_user_id}\n"
                                                f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                                f"请登录自动化网站，访问账号管理模块，进行对应账号的人脸验证"
                                                f"在验证期间，闲鱼自动回复暂时无法使用。"
                                            )
                                        else:
                                            notification_msg = (
                                                f"⚠️ 账号密码登录需要人脸验证\n\n"
                                                f"账号: {self.pure_user_id}\n"
                                                f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                                f"请点击验证链接完成验证:\n{frame_url}\n\n"
                                                f"在验证期间，闲鱼自动回复暂时无法使用。"
                                            )
                                        
                                        logger.info(f"【{self.pure_user_id}】准备发送人脸验证通知，截图路径: {screenshot_path}, URL: {frame_url}")
                                        
                                        # 如果回调是异步函数，使用 asyncio.run 在新的事件循环中运行
                                        import asyncio
                                        import inspect
                                        if inspect.iscoroutinefunction(notification_callback):
                                            # 在新的线程中运行异步回调，避免阻塞
                                            def run_async_callback():
                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)
                                                try:
                                                    # 传递通知消息、截图路径和URL给回调
                                                    # 参数顺序：message, screenshot_path, verification_url
                                                    loop.run_until_complete(notification_callback(notification_msg, screenshot_path, frame_url))
                                                    logger.info(f"【{self.pure_user_id}】✅ 异步通知回调已执行")
                                                except Exception as async_err:
                                                    logger.error(f"【{self.pure_user_id}】异步通知回调执行失败: {async_err}")
                                                    import traceback
                                                    logger.error(traceback.format_exc())
                                                finally:
                                                    loop.close()
                                            
                                            import threading
                                            thread = threading.Thread(target=run_async_callback)
                                            thread.start()
                                            logger.info(f"【{self.pure_user_id}】异步通知线程已启动")
                                            # 不等待线程完成，让通知在后台发送
                                        else:
                                            # 同步回调直接调用（传递通知消息、截图路径和URL）
                                            notification_callback(notification_msg, None, frame_url, screenshot_path)
                                            logger.info(f"【{self.pure_user_id}】✅ 同步通知回调已执行")
                                    else:
                                        logger.warning(f"【{self.pure_user_id}】无法获取验证信息，跳过通知发送")
                                        
                                except Exception as notify_err:
                                    logger.error(f"【{self.pure_user_id}】发送人脸验证通知失败: {notify_err}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                            else:
                                logger.warning(f"【{self.pure_user_id}】⚠️ notification_callback 未提供，无法发送通知")
                                logger.warning(f"【{self.pure_user_id}】请确保调用 login_with_password_playwright 时传入 notification_callback 参数")
                            
                            # 持续等待用户完成二维码/人脸验证
                            logger.info(f"【{self.pure_user_id}】等待二维码/人脸验证完成...")
                            check_interval = 10  # 每10秒检查一次
                            max_wait_time = 450  # 最多等待7.5分钟
                            waited_time = 0
                            
                            while waited_time < max_wait_time:
                                time.sleep(check_interval)
                                waited_time += check_interval
                                if waited_time == check_interval or waited_time % 30 == 0:
                                    _capture_login_debug(
                                        f"verification_wait_{waited_time}s",
                                        f"等待二维码/人脸验证中 {waited_time}/{max_wait_time} 秒"
                                    )
                                
                                # 先检测是否有滑块，如果有就处理
                                try:
                                    logger.debug(f"【{self.pure_user_id}】检测是否存在滑块...")
                                    slider_detected = False
                                    
                                    # 快速检测滑块元素（不等待，仅检测）
                                    slider_selectors = [
                                        "#nc_1_n1z",
                                        ".nc-container",
                                        "#baxia-dialog-content",
                                        ".nc_wrapper",
                                        "#nocaptcha"
                                    ]
                                    
                                    # 先在主页面检测
                                    for selector in slider_selectors:
                                        try:
                                            element = page.query_selector(selector)
                                            if element and element.is_visible():
                                                slider_detected = True
                                                logger.info(f"【{self.pure_user_id}】🔍 检测到滑块元素: {selector}")
                                                break
                                        except:
                                            pass
                                    
                                    # 如果主页面没找到，检查所有frame
                                    if not slider_detected:
                                        try:
                                            frames = page.frames
                                            for frame in frames:
                                                for selector in slider_selectors:
                                                    try:
                                                        element = frame.query_selector(selector)
                                                        if element and element.is_visible():
                                                            slider_detected = True
                                                            logger.info(f"【{self.pure_user_id}】🔍 在frame中检测到滑块元素: {selector}")
                                                            break
                                                    except:
                                                        pass
                                                if slider_detected:
                                                    break
                                        except:
                                            pass
                                    
                                    # 如果检测到滑块，尝试处理
                                    if slider_detected:
                                        logger.info(f"【{self.pure_user_id}】⚡ 检测到滑块，开始自动处理...")
                                        time.sleep(3)
                                        try:
                                            # 调用滑块处理方法（使用快速模式，因为已确认滑块存在）
                                            # 最多尝试3次，因为同一个页面连续失败3次后就不会成功了
                                            if self.solve_slider(max_retries=3, fast_mode=True):
                                                logger.success(f"【{self.pure_user_id}】✅ 滑块处理成功！")
                                                
                                                # 滑块处理成功后，刷新页面
                                                try:
                                                    logger.info(f"【{self.pure_user_id}】🔄 滑块处理成功，刷新页面...")
                                                    page.reload(wait_until="domcontentloaded", timeout=30000)
                                                    logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                                    # 刷新后短暂等待，让页面稳定
                                                    time.sleep(2)
                                                except Exception as reload_err:
                                                    logger.warning(f"【{self.pure_user_id}】⚠️ 页面刷新失败: {reload_err}")
                                            else:
                                                # 3次都失败了，刷新页面后再尝试一次
                                                logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理3次都失败，刷新页面后重试...")
                                                try:
                                                    logger.info(f"【{self.pure_user_id}】🔄 刷新页面以重置滑块状态...")
                                                    page.reload(wait_until="domcontentloaded", timeout=30000)
                                                    logger.info(f"【{self.pure_user_id}】✅ 页面刷新完成")
                                                    time.sleep(2)
                                                    
                                                    # 刷新后再次尝试处理滑块（给一次机会）
                                                    logger.info(f"【{self.pure_user_id}】🔄 页面刷新后，再次尝试处理滑块...")
                                                    if self.solve_slider(max_retries=3, fast_mode=True):
                                                        logger.success(f"【{self.pure_user_id}】✅ 刷新后滑块处理成功！")
                                                    else:
                                                        logger.error(f"【{self.pure_user_id}】❌ 刷新后滑块处理仍然失败，继续等待...")
                                                except Exception as reload_err:
                                                    logger.warning(f"【{self.pure_user_id}】⚠️ 页面刷新失败: {reload_err}")
                                        except Exception as slider_err:
                                            logger.warning(f"【{self.pure_user_id}】⚠️ 滑块处理出错: {slider_err}")
                                            logger.debug(traceback.format_exc())
                                except Exception as e:
                                    logger.debug(f"【{self.pure_user_id}】滑块检测时出错: {e}")
                                
                                # 检查登录状态（通过页面元素）
                                try:
                                    if self._check_login_success_by_element(page):
                                        logger.success(f"【{self.pure_user_id}】✅ 验证成功，登录状态已确认！")
                                        login_success = True
                                        break
                                    else:
                                        logger.info(f"【{self.pure_user_id}】等待验证中... (已等待{waited_time}秒/{max_wait_time}秒)")
                                except Exception as e:
                                    logger.debug(f"【{self.pure_user_id}】检查登录状态时出错: {e}")
                            
                            # 删除截图（无论成功或失败）
                            if screenshot_path:
                                try:
                                    import glob
                                    # 删除该账号的所有验证截图
                                    screenshots_dir = "static/uploads/images"
                                    all_screenshots = glob.glob(os.path.join(screenshots_dir, f"face_verify_{self.pure_user_id}_*.jpg"))
                                    for screenshot_file in all_screenshots:
                                        try:
                                            if os.path.exists(screenshot_file):
                                                os.remove(screenshot_file)
                                                logger.info(f"【{self.pure_user_id}】✅ 已删除验证截图: {screenshot_file}")
                                            else:
                                                logger.warning(f"【{self.pure_user_id}】⚠️ 截图文件不存在: {screenshot_file}")
                                        except Exception as e:
                                            logger.warning(f"【{self.pure_user_id}】⚠️ 删除截图失败: {e}")
                                except Exception as e:
                                    logger.error(f"【{self.pure_user_id}】删除截图时出错: {e}")
                            
                            if login_success:
                                logger.info(f"【{self.pure_user_id}】二维码/人脸验证已完成")
                            else:
                                _capture_login_debug("verification_timeout", f"等待验证超时 {max_wait_time} 秒")
                                logger.error(f"【{self.pure_user_id}】❌ 等待验证超时（{max_wait_time}秒）")
                                return None
                        else:
                            logger.info(f"【{self.pure_user_id}】未检测到二维码/人脸验证")
                            # 再次检查登录状态，确保登录成功
                            logger.info(f"【{self.pure_user_id}】等待1秒后再次检查登录状态...")
                            time.sleep(1)
                            login_success = self._check_login_success_by_element(page)
                            if not login_success:
                                _capture_login_debug("login_not_confirmed", "未检测到二维码/人脸验证且登录状态未确认")
                                logger.error(f"【{self.pure_user_id}】❌ 登录状态未确认，无法获取Cookie")
                                return None
                            else:
                                logger.success(f"【{self.pure_user_id}】✅ 登录状态已确认")
                    
                    # 【重要】只有在 login_success = True 的情况下，才获取Cookie
                    if not login_success:
                        _capture_login_debug("login_failed_before_cookie", "登录未成功，跳过Cookie获取")
                        logger.error(f"【{self.pure_user_id}】❌ 登录未成功，无法获取Cookie")
                        return None
                    
                    # 获取Cookie
                    logger.info(f"【{self.pure_user_id}】等待1秒后获取Cookie...")
                    time.sleep(1)
                    cookies_dict = {}
                    try:
                        cookies_list = context.cookies()
                        for cookie in cookies_list:
                            cookies_dict[cookie.get('name', '')] = cookie.get('value', '')
                        
                        logger.info(f"【{self.pure_user_id}】成功获取Cookie，包含 {len(cookies_dict)} 个字段")
                        
                        # 打印关键Cookie字段
                        important_keys = ['unb', '_m_h5_tk', '_m_h5_tk_enc', 'cookie2', 't', 'sgcookie', 'cna']
                        logger.info(f"【{self.pure_user_id}】关键Cookie字段检查:")
                        for key in important_keys:
                            if key in cookies_dict:
                                val = cookies_dict[key]
                                logger.info(f"【{self.pure_user_id}】  ✅ {key}: {'存在' if val else '为空'} (长度: {len(str(val)) if val else 0})")
                            else:
                                logger.info(f"【{self.pure_user_id}】  ❌ {key}: 缺失")
                        
                        logger.info("=" * 60)
                        
                        if cookies_dict:
                            _capture_login_debug("cookie_obtained", f"成功获取Cookie字段数={len(cookies_dict)}")
                            logger.success("✅ 登录成功！Cookie有效")
                            return cookies_dict
                        else:
                            _capture_login_debug("cookie_empty", "获取到Cookie列表但为空")
                            logger.error("❌ 未获取到Cookie")
                            return None
                    except Exception as e:
                        _capture_login_debug("cookie_fetch_error", f"获取Cookie失败: {e}")
                        logger.error(f"【{self.pure_user_id}】获取Cookie失败: {e}")
                        return None
                
                finally:
                    # 恢复原始值
                    self.page = original_page
                    self.context = original_context
                    self.browser = original_browser
                    self.playwright = original_playwright
            
            finally:
                # 关闭浏览器
                try:
                    context.close()
                    playwright.stop()
                    logger.info(f"【{self.pure_user_id}】浏览器已关闭，缓存已保存")
                except Exception as e:
                    logger.warning(f"【{self.pure_user_id}】关闭浏览器时出错: {e}")
                    try:
                        playwright.stop()
                    except:
                        pass
        
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】密码登录流程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def login_with_password_headful(self, account: str = None, password: str = None, show_browser: bool = False):
        """通过浏览器进行密码登录并获取Cookie (使用DrissionPage)
        
        Args:
            account: 登录账号（必填）
            password: 登录密码（必填）
            show_browser: 是否显示浏览器窗口（默认False为无头模式）
                         True: 有头模式，登录后等待5分钟（可手动处理验证码）
                         False: 无头模式，登录后等待10秒
            
        Returns:
            dict: 获取到的cookie字典，失败返回None
        """
        page = None
        try:
            # 检查日期有效性
            if not self._check_date_validity():
                logger.error(f"【{self.pure_user_id}】日期验证失败，无法执行登录")
                return None
            
            # 验证必需参数
            if not account or not password:
                logger.error(f"【{self.pure_user_id}】账号或密码不能为空")
                return None
            
            browser_mode = "有头" if show_browser else "无头"
            logger.info(f"【{self.pure_user_id}】开始{browser_mode}模式密码登录流程（使用DrissionPage）...")
            
            # 导入 DrissionPage
            try:
                from DrissionPage import ChromiumPage, ChromiumOptions
                logger.info(f"【{self.pure_user_id}】DrissionPage导入成功")
            except ImportError:
                logger.error(f"【{self.pure_user_id}】DrissionPage未安装，请执行: pip install DrissionPage")
                return None
            
            # 配置浏览器选项
            logger.info(f"【{self.pure_user_id}】配置浏览器选项（{browser_mode}模式）...")
            co = ChromiumOptions()
            
            # 根据 show_browser 参数决定是否启用无头模式
            if not show_browser:
                co.headless()
                logger.info(f"【{self.pure_user_id}】已启用无头模式")
            else:
                logger.info(f"【{self.pure_user_id}】已启用有头模式（浏览器可见）")
            
            # 设置浏览器参数（反检测）
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-setuid-sandbox')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-blink-features=AutomationControlled')
            co.set_argument('--disable-infobars')
            co.set_argument('--disable-extensions')
            co.set_argument('--disable-popup-blocking')
            co.set_argument('--disable-notifications')
            
            # 无头模式需要的额外参数
            if not show_browser:
                co.set_argument('--disable-gpu')
                co.set_argument('--disable-software-rasterizer')
            else:
                # 有头模式窗口最大化
                co.set_argument('--start-maximized')
            
            # 设置用户代理
            browser_features = self._get_random_browser_features()
            co.set_user_agent(browser_features['user_agent'])
            
            # 设置中文语言
            co.set_argument('--lang=zh-CN')
            logger.info(f"【{self.pure_user_id}】已设置浏览器语言为中文（zh-CN）")
            
            # 禁用自动化特征检测
            co.set_pref('excludeSwitches', ['enable-automation'])
            co.set_pref('useAutomationExtension', False)
            
            # 创建浏览器页面，添加重试机制
            logger.info(f"【{self.pure_user_id}】启动DrissionPage浏览器（{browser_mode}模式）...")
            max_retries = 3
            retry_count = 0
            page = None
            
            while retry_count < max_retries and page is None:
                try:
                    if retry_count > 0:
                        logger.info(f"【{self.pure_user_id}】第 {retry_count + 1} 次尝试启动浏览器...")
                        time.sleep(2)  # 等待2秒后重试
                    
                    page = ChromiumPage(addr_or_opts=co)
                    logger.info(f"【{self.pure_user_id}】浏览器已成功启动（{browser_mode}模式）")
                    break
                    
                except Exception as browser_error:
                    retry_count += 1
                    logger.warning(f"【{self.pure_user_id}】浏览器启动失败 (尝试 {retry_count}/{max_retries}): {str(browser_error)}")
                    
                    if retry_count >= max_retries:
                        logger.error(f"【{self.pure_user_id}】浏览器启动失败，已达到最大重试次数")
                        logger.error(f"【{self.pure_user_id}】可能的原因：")
                        logger.error(f"【{self.pure_user_id}】1. Chrome/Chromium 浏览器未正确安装或路径不正确")
                        logger.error(f"【{self.pure_user_id}】2. 远程调试端口被占用，请关闭其他Chrome实例")
                        logger.error(f"【{self.pure_user_id}】3. 系统资源不足")
                        logger.error(f"【{self.pure_user_id}】建议：")
                        logger.error(f"【{self.pure_user_id}】- 检查Chrome浏览器是否已安装")
                        logger.error(f"【{self.pure_user_id}】- 关闭所有Chrome浏览器窗口后重试")
                        logger.error(f"【{self.pure_user_id}】- 检查任务管理器中是否有残留的chrome.exe进程")
                        raise
                    
                    # 尝试清理可能残留的Chrome进程
                    try:
                        import subprocess
                        import platform
                        if platform.system() == 'Windows':
                            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                                         capture_output=True, timeout=5)
                            logger.info(f"【{self.pure_user_id}】已尝试清理残留Chrome进程")
                    except Exception as cleanup_error:
                        logger.debug(f"【{self.pure_user_id}】清理进程时出错: {cleanup_error}")
            
            if page is None:
                logger.error(f"【{self.pure_user_id}】无法启动浏览器")
                return None
            
            # 访问登录页面
            target_url = "https://www.goofish.com/im"
            logger.info(f"【{self.pure_user_id}】访问登录页面: {target_url}")
            page.get(target_url)
            
            # 等待页面加载
            logger.info(f"【{self.pure_user_id}】等待页面加载...")
            time.sleep(5)
            
            # 检查页面状态
            logger.info(f"【{self.pure_user_id}】========== 页面诊断信息 ==========")
            current_url = page.url
            logger.info(f"【{self.pure_user_id}】当前URL: {current_url}")
            page_title = page.title
            logger.info(f"【{self.pure_user_id}】页面标题: {page_title}")
            
            
            logger.info(f"【{self.pure_user_id}】====================================")
            
            # 查找并点击密码登录标签
            logger.info(f"【{self.pure_user_id}】查找密码登录标签...")
            password_tab_selectors = [
                '.password-login-tab-item',
                'text:密码登录',
                'text:账号密码登录',
            ]
            
            password_tab_found = False
            for selector in password_tab_selectors:
                try:
                    tab = page.ele(selector, timeout=3)
                    if tab:
                        logger.info(f"【{self.pure_user_id}】找到密码登录标签: {selector}")
                        tab.click()
                        logger.info(f"【{self.pure_user_id}】密码登录标签已点击")
                        time.sleep(2)
                        password_tab_found = True
                        break
                except:
                    continue
            
            if not password_tab_found:
                logger.warning(f"【{self.pure_user_id}】未找到密码登录标签，可能页面默认就是密码登录模式")
            
            # 查找登录表单
            logger.info(f"【{self.pure_user_id}】开始检测登录表单...")
            username_selectors = [
                '#fm-login-id',
                'input:name=fm-login-id',
                'input:placeholder^=手机',
                'input:placeholder^=账号',
                'input:type=text',
                '#TPL_username_1',
            ]
            
            login_input = None
            for selector in username_selectors:
                try:
                    login_input = page.ele(selector, timeout=2)
                    if login_input:
                        logger.info(f"【{self.pure_user_id}】找到登录表单: {selector}")
                        break
                except:
                    continue
            
            if not login_input:
                logger.error(f"【{self.pure_user_id}】未找到登录表单")
                return None
            
            # 输入账号
            logger.info(f"【{self.pure_user_id}】输入账号: {account}")
            try:
                login_input.click()
                time.sleep(0.5)
                login_input.input(account)
                logger.info(f"【{self.pure_user_id}】账号已输入")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"【{self.pure_user_id}】输入账号失败: {str(e)}")
                return None
            
            # 输入密码
            logger.info(f"【{self.pure_user_id}】输入密码...")
            password_selectors = [
                '#fm-login-password',
                'input:name=fm-login-password',
                'input:type=password',
                'input:placeholder^=密码',
                '#TPL_password_1',
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = page.ele(selector, timeout=2)
                    if password_input:
                        logger.info(f"【{self.pure_user_id}】找到密码输入框: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                logger.error(f"【{self.pure_user_id}】未找到密码输入框")
                return None
            
            try:
                password_input.click()
                time.sleep(0.5)
                password_input.input(password)
                logger.info(f"【{self.pure_user_id}】密码已输入")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"【{self.pure_user_id}】输入密码失败: {str(e)}")
                return None
            
            # 勾选协议（可选）
            logger.info(f"【{self.pure_user_id}】查找并勾选用户协议...")
            agreement_selectors = [
                '#fm-agreement-checkbox',
                'input:type=checkbox',
            ]
            
            for selector in agreement_selectors:
                try:
                    checkbox = page.ele(selector, timeout=1)
                    if checkbox and not checkbox.states.is_checked:
                        checkbox.click()
                        logger.info(f"【{self.pure_user_id}】用户协议已勾选")
                        time.sleep(0.5)
                        break
                except:
                    continue
            
            # 点击登录按钮
            logger.info(f"【{self.pure_user_id}】点击登录按钮...")
            login_button_selectors = [
                '@class=fm-button fm-submit password-login ',
                '.fm-button.fm-submit.password-login',
                'button.password-login',
                '.password-login',
                'button.fm-submit',
                'text:登录',
            ]
            
            login_button_found = False
            for selector in login_button_selectors:
                try:
                    button = page.ele(selector, timeout=2)
                    if button:
                        logger.info(f"【{self.pure_user_id}】找到登录按钮: {selector}")
                        button.click()
                        logger.info(f"【{self.pure_user_id}】登录按钮已点击")
                        login_button_found = True
                        break
                except:
                    continue
            
            if not login_button_found:
                logger.warning(f"【{self.pure_user_id}】未找到登录按钮，尝试按Enter键...")
                try:
                    password_input.input('\n')  # 模拟按Enter
                    logger.info(f"【{self.pure_user_id}】已按Enter键")
                except Exception as e:
                    logger.error(f"【{self.pure_user_id}】按Enter键失败: {str(e)}")
            
            # 等待登录完成
            logger.info(f"【{self.pure_user_id}】等待登录完成...")
            time.sleep(5)
            
            # 检查当前URL和标题
            current_url = page.url
            logger.info(f"【{self.pure_user_id}】登录后URL: {current_url}")
            page_title = page.title
            logger.info(f"【{self.pure_user_id}】登录后页面标题: {page_title}")
            
            # 根据浏览器模式决定等待时间
            # 有头模式：等待5分钟（用户可能需要手动处理验证码等）
            # 无头模式：等待10秒
            if show_browser:
                wait_seconds = 300  # 5分钟
                logger.info(f"【{self.pure_user_id}】有头模式：等待5分钟让Cookie完全生成（期间可手动处理验证码等）...")
            else:
                wait_seconds = 10
                logger.info(f"【{self.pure_user_id}】无头模式：等待10秒让Cookie完全生成...")
            
            time.sleep(wait_seconds)
            logger.info(f"【{self.pure_user_id}】等待完成，准备获取Cookie")
            
            # 获取Cookie
            logger.info(f"【{self.pure_user_id}】开始获取Cookie...")
            cookies_raw = page.cookies()
            
            # 将cookies转换为字典格式
            cookies = {}
            if isinstance(cookies_raw, list):
                # 如果返回的是列表格式，转换为字典
                for cookie in cookies_raw:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        cookies[cookie['name']] = cookie['value']
                    elif isinstance(cookie, tuple) and len(cookie) >= 2:
                        cookies[cookie[0]] = cookie[1]
            elif isinstance(cookies_raw, dict):
                # 如果已经是字典格式，直接使用
                cookies = cookies_raw
            
            if cookies:
                logger.info(f"【{self.pure_user_id}】成功获取 {len(cookies)} 个Cookie")
                logger.info(f"【{self.pure_user_id}】Cookie名称列表: {list(cookies.keys())}")
                
                # 打印完整的Cookie
                logger.info(f"【{self.pure_user_id}】完整Cookie内容:")
                for name, value in cookies.items():
                    # 对长cookie值进行截断显示
                    if len(value) > 50:
                        display_value = f"{value[:25]}...{value[-25:]}"
                    else:
                        display_value = value
                    logger.info(f"【{self.pure_user_id}】  {name} = {display_value}")
                
                # 将cookie转换为字符串格式
                cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                logger.info(f"【{self.pure_user_id}】Cookie字符串格式: {cookie_str[:200]}..." if len(cookie_str) > 200 else f"【{self.pure_user_id}】Cookie字符串格式: {cookie_str}")
                
                logger.info(f"【{self.pure_user_id}】登录成功，准备关闭浏览器")
                
                return cookies
            else:
                logger.error(f"【{self.pure_user_id}】未获取到任何Cookie")
                return None
                
        except Exception as e:
            logger.error(f"【{self.pure_user_id}】密码登录流程出错: {str(e)}")
            import traceback
            logger.error(f"【{self.pure_user_id}】详细错误信息: {traceback.format_exc()}")
            return None
        finally:
            # 关闭浏览器
            logger.info(f"【{self.pure_user_id}】关闭浏览器...")
            try:
                if page:
                    page.quit()
                    logger.info(f"【{self.pure_user_id}】DrissionPage浏览器已关闭")
            except Exception as e:
                logger.warning(f"【{self.pure_user_id}】关闭浏览器时出错: {e}")
    
    # ══════════════════════════════════════════════════════════════════════
    # "挤爆了" 自动恢复
    # 日志特征: ret=FAIL_SYS_USER_VALIDATE | RGV587_ERROR::SM::哎哟喂,被挤爆啦
    # 手动步骤: 打开闲鱼网页版 → 点消息 → 过滑块 → 更新 cookie
    # 自动化:   直接导航到消息页触发滑块 → 过了就取 cookie → 写回调用方
    # ══════════════════════════════════════════════════════════════════════

    # 挤爆了时尝试的 URL 序列（依次触发 NC 滑块）
    _JIBAO_RECOVERY_URLS = [
        "https://www.goofish.com/im",          # 消息页（最可能触发）
        "https://www.goofish.com/",            # 首页
        "https://h5api.m.goofish.com/",        # h5 接口（有时直接过）
    ]

    def _navigate_and_wait_content(self, url: str, timeout: int = 20000) -> str:
        """导航到 url，返回页面文本内容；失败返回空串"""
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            time.sleep(random.uniform(0.4, 0.9))
            return self.page.content()
        except Exception as e:
            logger.warning(f"【{self.pure_user_id}】导航 {url} 失败: {e}")
            return ""

    def _has_captcha(self, content: str = "") -> bool:
        """判断当前页面是否有滑块验证码"""
        if not content:
            try:
                content = self.page.content()
            except:
                return False
        return any(kw in content for kw in ["验证码", "captcha", "滑块", "slider", "nc_1_n1z", "nocaptcha"])

    def _wait_for_cookies_stable(self, key: str = "x5sec", timeout: float = 8.0) -> dict:
        """
        等待验证成功后 cookie 稳定，最多等 timeout 秒。
        检测到 key 相关 cookie 出现即返回。
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass
            cookies = self.context.cookies()
            result = {c['name']: c['value'] for c in cookies}
            if any(key in k.lower() for k in result):
                return result
            time.sleep(0.5)
        # 超时也返回当前所有 cookie
        return {c['name']: c['value'] for c in self.context.cookies()}

    def _extract_x5_cookies(self, all_cookies: dict) -> dict:
        """从完整 cookie 字典中提取 x5 相关 cookie"""
        filtered = {k: v for k, v in all_cookies.items()
                    if k.lower().startswith('x5') or 'x5sec' in k.lower()}
        logger.info(f"【{self.pure_user_id}】x5 cookie: {list(filtered.keys())}")
        return filtered or None

    def handle_jibao_recovery(self, existing_cookies: dict = None) -> tuple:
        """
        "挤爆了"自动恢复入口。

        流程：
          1. 初始化浏览器（注入已有 cookie，保持登录态）
          2. 依次尝试消息页 / 首页，等待 NC 滑块出现
          3. 调用 solve_slider() 过验证
          4. 取回更新后的 cookie（重点：x5sec）
          5. 返回 (success: bool, cookies: dict)

        调用方式（在 XianyuAutoAsync.refresh_token 的挤爆了分支）：
            slider = XianyuSliderStealth(user_id, headless=True)
            ok, new_cookies = slider.handle_jibao_recovery(existing_cookies=current_cookie_dict)
            if ok and new_cookies:
                # 写回数据库 / 内存
                self.update_config_cookies(new_cookies)
        """
        logger.warning(f"【{self.pure_user_id}】🚨 挤爆了自动恢复启动")
        cookies = None

        try:
            if not self._check_date_validity():
                return False, None

            self.init_browser()

            # ── 注入已有 cookie，保持登录态（不需要重新登录）──────────────
            if existing_cookies:
                try:
                    cookie_list = []
                    for name, value in existing_cookies.items():
                        cookie_list.append({
                            "name":   name,
                            "value":  str(value),
                            "domain": ".goofish.com",
                            "path":   "/",
                        })
                    self.context.add_cookies(cookie_list)
                    logger.info(f"【{self.pure_user_id}】已注入 {len(cookie_list)} 个已有 cookie")
                except Exception as e:
                    logger.warning(f"【{self.pure_user_id}】注入 cookie 失败（继续）: {e}")

            # ── 依次尝试各页面，找到触发滑块的那个 ──────────────────────
            triggered = False
            for url in self._JIBAO_RECOVERY_URLS:
                logger.info(f"【{self.pure_user_id}】尝试导航: {url}")
                content = self._navigate_and_wait_content(url)

                if self._has_captcha(content):
                    logger.info(f"【{self.pure_user_id}】✅ 在 {url} 触发了滑块验证")
                    triggered = True
                    break

                # 没有验证码但页面正常加载 → 可能已经不需要验证了
                if "闲鱼" in content or "goofish" in content.lower():
                    logger.info(f"【{self.pure_user_id}】页面正常，无需验证（挤爆已自动解除？）")
                    # 取一下 cookie 更新一下
                    all_cks = self._wait_for_cookies_stable(timeout=3.0)
                    cookies = self._extract_x5_cookies(all_cks)
                    return True, cookies

            if not triggered:
                # 最后兜底：直接打开原始 punish URL 让 NC 弹出来
                logger.warning(f"【{self.pure_user_id}】常规页面未触发滑块，尝试直接访问 punish 端点")
                punish_url = (
                    "https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/"
                    "_____tmd_____/punish"
                )
                content = self._navigate_and_wait_content(punish_url, timeout=15000)
                if self._has_captcha(content):
                    triggered = True
                    logger.info(f"【{self.pure_user_id}】✅ punish 端点触发了滑块验证")

            if not triggered:
                logger.error(f"【{self.pure_user_id}】所有 URL 均未触发滑块，恢复失败")
                return False, None

            # ── 人类行为模拟：短暂停顿再做滑块（不要立即开始）──────────
            time.sleep(random.uniform(0.8, 1.5))

            # ── 执行滑块验证 ────────────────────────────────────────────
            success = self.solve_slider(max_retries=3)

            if success:
                logger.info(f"【{self.pure_user_id}】✅ 挤爆了恢复：滑块验证成功")
                # 等待 cookie 稳定
                all_cks = self._wait_for_cookies_stable(timeout=8.0)
                cookies = self._extract_x5_cookies(all_cks)
                if cookies:
                    logger.info(f"【{self.pure_user_id}】✅ 获取到新 x5 cookie，共 {len(cookies)} 个")
                else:
                    # x5 没拿到也返回全量 cookie，让调用方自行过滤
                    logger.warning(f"【{self.pure_user_id}】未找到 x5 cookie，返回全量 cookie")
                    cookies = all_cks
                return True, cookies
            else:
                logger.error(f"【{self.pure_user_id}】挤爆了恢复：滑块验证失败")
                return False, None

        except Exception as e:
            logger.error(f"【{self.pure_user_id}】handle_jibao_recovery 异常: {e}\n{traceback.format_exc()}")
            return False, None
        finally:
            self.close_browser()

    def run(self, url: str):
        """
        运行主流程，返回 (成功状态, cookie数据)。

        url 可以是：
          - 普通验证 URL（原有逻辑）
          - 'jibao_recovery'（触发挤爆了自动恢复流程）
        """
        # ── 特殊指令：挤爆了恢复 ────────────────────────────────────────
        if url == "jibao_recovery":
            return self.handle_jibao_recovery()

        cookies = None
        try:
            if not self._check_date_validity():
                logger.error(f"【{self.pure_user_id}】日期验证失败，无法执行")
                return False, None

            self.init_browser()

            logger.debug(f"【{self.pure_user_id}】导航到URL: {url}")
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.warning(f"【{self.pure_user_id}】页面加载异常，尝试继续: {e}")
                time.sleep(2)

            time.sleep(random.uniform(0.3, 0.8))

            # 模拟简单人类行为
            self.page.mouse.move(640, 360)
            time.sleep(random.uniform(0.02, 0.05))
            self.page.mouse.wheel(0, random.randint(200, 500))
            time.sleep(random.uniform(0.02, 0.05))

            page_title = self.page.title()
            logger.debug(f"【{self.pure_user_id}】页面标题: {page_title}")

            content = self.page.content()
            if self._has_captcha(content):
                logger.info(f"【{self.pure_user_id}】检测到验证码页面，开始滑块验证")
                success = self.solve_slider()

                if success:
                    logger.info(f"【{self.pure_user_id}】滑块验证成功")
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"【{self.pure_user_id}】等待页面加载时出错: {e}")

                    try:
                        cookies = self._get_cookies_after_success()
                    except Exception as e:
                        logger.warning(f"【{self.pure_user_id}】获取cookie时出错: {e}")
                else:
                    logger.warning(f"【{self.pure_user_id}】滑块验证失败")

                return success, cookies
            else:
                logger.debug(f"【{self.pure_user_id}】页面无验证码，直接返回")
                return True, None

        except Exception as e:
            logger.error(f"【{self.pure_user_id}】执行过程中出错: {e}")
            return False, None
        finally:
            self.close_browser()

def get_slider_stats():
    """获取滑块验证并发统计信息"""
    return concurrency_manager.get_stats()

if __name__ == "__main__":
    # 简单的命令行示例
    import sys
    if len(sys.argv) < 2:
        print("用法: python xianyu_slider_stealth.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    # 第三个参数可以指定 headless 模式，默认为 True（无头）
    headless = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    slider = XianyuSliderStealth("test_user", enable_learning=True, headless=headless)
    try:
        success, cookies = slider.run(url)
        print(f"验证结果: {'成功' if success else '失败'}") 
        if cookies:
            print(f"获取到 {len(cookies)} 个cookies")
    except Exception as e:
        print(f"验证异常: {e}")