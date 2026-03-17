#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
量化交易系统 - 日志系统优化模块
==============================================
功能：
  - 中文日志输出
  - 日志分级（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 日志文件轮转（按时间/大小）
  - 彩色控制台输出
  - 结构化日志支持

作者：量化系统团队
版本：v1.0
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# 导入彩色输出模块
try:
    from cli_utils import Colors, colorize, supports_color
except ImportError:
    # 简化版本（当 cli_utils 不可用时）
    class Colors:
        RESET = ""
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        CYAN = ""
        MAGENTA = ""
        WHITE = ""
        BOLD = ""
        DIM = ""
    
    def colorize(text, color):
        return text
    
    def supports_color():
        return False


# ============================================ 【日志级别映射】 ============================================

LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'WARN': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
}

# ============================================ 【中文日志级别显示】 ============================================

LEVEL_NAME_CN = {
    logging.DEBUG: "调试",
    logging.INFO: "信息",
    logging.WARNING: "警告",
    logging.ERROR: "错误",
    logging.CRITICAL: "严重",
}

LEVEL_COLOR = {
    logging.DEBUG: Colors.CYAN,
    logging.INFO: Colors.GREEN,
    logging.WARNING: Colors.YELLOW,
    logging.ERROR: Colors.RED,
    logging.CRITICAL: Colors.BG_RED + Colors.WHITE + Colors.BOLD,
}

# ============================================ 【日志格式配置】 ============================================

# 标准格式（详细）
FORMAT_STANDARD = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
)

# 简洁格式（控制台用）
FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"

# 中文格式
FORMAT_CHINESE = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)

# JSON 格式（结构化日志）
FORMAT_JSON = (
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "file": "%(filename)s", '
    '"line": %(lineno)d, "message": "%(message)s"}'
)

# 日期格式
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================ 【彩色日志格式化器】 ============================================

class ColoredFormatter(logging.Formatter):
    """
    支持彩色输出的日志格式化器
    根据日志级别自动添加颜色
    """
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '%',
        use_color: bool = True
    ):
        super().__init__(fmt, datefmt, style)
        self.use_color = use_color and supports_color()
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取原始格式化的日志
        log_text = super().format(record)
        
        # 如果不支持颜色或禁用，返回原文本
        if not self.use_color:
            return log_text
        
        # 根据级别添加颜色
        color = LEVEL_COLOR.get(record.levelno, Colors.WHITE)
        log_text = colorize(log_text, color)
        
        # 为级别标签添加背景色（ERROR 和 CRITICAL）
        if record.levelno >= logging.ERROR:
            levelname = self.formatLevelName(record.levelname)
            log_text = log_text.replace(record.levelname, levelname)
        
        return log_text
    
    def formatLevelName(self, levelname: str) -> str:
        """格式化级别名称（添加中文）"""
        level_map = {
            'DEBUG': '🔍 调试',
            'INFO': 'ℹ️  信息',
            'WARNING': '⚠️  警告',
            'ERROR': '❌ 错误',
            'CRITICAL': '🔴 严重',
        }
        return level_map.get(levelname, levelname)


# ============================================ 【JSON 格式化器】 ============================================

class JSONFormatter(logging.Formatter):
    """
    JSON 格式日志输出
    用于结构化日志收集和分析
    """
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'file': record.filename,
            'line': record.lineno,
            'function': record.funcName,
            'message': record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


# ============================================ 【日志系统配置类】 ============================================

class LoggerConfig:
    """
    日志系统配置管理器
    提供统一的日志配置接口
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        name: str = "quant_system",
        level: str = "INFO",
        log_dir: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count_info: int = 30,
        backup_count_error: int = 7,
        use_color: bool = True,
        log_to_console: bool = True,
        log_to_file: bool = True,
        json_format: bool = False
    ):
        """
        初始化日志配置
        
        Args:
            name: 日志记录器名称
            level: 日志级别（DEBUG/INFO/WARNING/ERROR）
            log_dir: 日志文件目录
            max_bytes: 单个日志文件最大大小（字节）
            backup_count_info: INFO 日志保留文件数
            backup_count_error: ERROR 日志保留文件数
            use_color: 是否启用彩色输出
            log_to_console: 是否输出到控制台
            log_to_file: 是否输出到文件
            json_format: 是否使用 JSON 格式
        """
        if self._initialized:
            return
        
        self.name = name
        self.level = LOG_LEVEL_MAP.get(level.upper(), logging.INFO)
        self.log_dir = Path(log_dir)
        self.max_bytes = max_bytes
        self.backup_count_info = backup_count_info
        self.backup_count_error = backup_count_error
        self.use_color = use_color
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.json_format = json_format
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志记录器
        self.logger = self._setup_logger()
        
        self._initialized = True
    
    def _setup_logger(self) -> logging.Logger:
        """配置日志记录器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        logger.handlers.clear()  # 清除已有 handler
        
        # 选择格式化器
        if self.json_format:
            formatter = JSONFormatter()
        else:
            formatter = ColoredFormatter(
                fmt=FORMAT_CHINESE,
                datefmt=DATE_FORMAT,
                use_color=self.use_color
            )
        
        # 添加控制台 handler
        if self.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 添加文件 handler
        if self.log_to_file:
            self._add_file_handlers(logger, formatter)
        
        # 添加异常处理
        self._add_exception_handler(logger)
        
        return logger
    
    def _add_file_handlers(self, logger: logging.Logger, formatter: logging.Formatter):
        """添加文件处理器"""
        # INFO 日志（按大小轮转）
        info_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "quant_info.log",
            maxBytes=self.max_bytes,
            backupCount=self.backup_count_info,
            encoding='utf-8'
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        logger.addHandler(info_handler)
        
        # ERROR 日志（单独文件）
        error_formatter = ColoredFormatter(
            fmt=FORMAT_CHINESE,
            datefmt=DATE_FORMAT,
            use_color=False  # 文件日志不使用颜色
        )
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "quant_error.log",
            maxBytes=self.max_bytes,
            backupCount=self.backup_count_error,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)
        
        # 按天轮转的日志（可选）
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / "quant_daily.log",
            when='D',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        daily_handler.setLevel(logging.DEBUG)
        daily_handler.setFormatter(formatter)
        logger.addHandler(daily_handler)
    
    def _add_exception_handler(self, logger: logging.Logger):
        """添加异常捕获处理器"""
        import traceback
        
        def exception_handler(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                return
            
            logger.critical(
                "未捕获的异常",
                extra={
                    'extra_data': {
                        'exception_type': str(exc_type),
                        'exception_value': str(exc_value),
                        'traceback': ''.join(traceback.format_exception(
                            exc_type, exc_value, exc_traceback
                        ))
                    }
                }
            )
        
        sys.excepthook = exception_handler
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger
    
    def set_level(self, level: str):
        """动态设置日志级别"""
        self.level = LOG_LEVEL_MAP.get(level.upper(), logging.INFO)
        self.logger.setLevel(self.level)
        
        for handler in self.logger.handlers:
            handler.setLevel(self.level)
    
    def get_log_files(self) -> Dict[str, Path]:
        """获取所有日志文件路径"""
        return {
            'info': self.log_dir / "quant_info.log",
            'error': self.log_dir / "quant_error.log",
            'daily': self.log_dir / "quant_daily.log",
        }
    
    def cleanup_old_logs(self, keep_days: int = 30):
        """清理旧日志文件"""
        import time
        
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    self.logger.info(f"已清理旧日志：{log_file}")
                except Exception as e:
                    self.logger.warning(f"清理日志失败：{log_file}, 错误：{e}")


# ============================================ 【便捷日志函数】 ============================================

# 全局日志实例
_default_logger = None

def get_logger(
    name: str = "quant_system",
    level: str = "INFO",
    **kwargs
) -> logging.Logger:
    """
    获取日志记录器（便捷函数）
    
    Args:
        name: 日志名称
        level: 日志级别
        **kwargs: 其他配置参数
    
    Returns:
        logging.Logger: 日志记录器
    """
    global _default_logger
    
    if _default_logger is None:
        config = LoggerConfig(name=name, level=level, **kwargs)
        _default_logger = config.get_logger()
    
    return _default_logger


def debug(msg: str, *args, **kwargs):
    """记录 DEBUG 级别日志"""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """记录 INFO 级别日志"""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """记录 WARNING 级别日志"""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """记录 ERROR 级别日志"""
    get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """记录 CRITICAL 级别日志"""
    get_logger().critical(msg, *args, **kwargs)


def exception(msg: str, *args, exc_info=True, **kwargs):
    """记录异常日志"""
    get_logger().exception(msg, *args, exc_info=exc_info, **kwargs)


# ============================================ 【上下文日志装饰器】 ============================================

def log_function_call(logger: Optional[logging.Logger] = None):
    """
    函数调用日志装饰器
    自动记录函数入口、出口和异常
    
    用法：
        @log_function_call()
        def my_function():
            pass
    """
    def decorator(func):
        import functools
        import traceback
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log = logger or get_logger()
            
            # 记录函数入口
            log.debug(f"▶️  进入函数：{func.__name__}")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录函数出口
                log.debug(f"✅ 退出函数：{func.__name__}")
                
                return result
            
            except Exception as e:
                # 记录异常
                log.error(
                    f"❌ 函数异常：{func.__name__}, 错误：{str(e)}",
                    extra={'extra_data': {'traceback': traceback.format_exc()}}
                )
                raise
        
        return wrapper
    return decorator


# ============================================ 【性能计时上下文】 ============================================

class log_timer:
    """
    性能计时上下文管理器
    记录代码块执行时间
    
    用法：
        with log_timer("数据处理"):
            # 执行代码
            pass
    """
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️  开始：{self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.debug(f"✅ 完成：{self.operation}, 耗时：{elapsed:.3f}秒")
        else:
            self.logger.error(f"❌ 失败：{self.operation}, 耗时：{elapsed:.3f}秒")
        
        return False


# ============================================ 【测试入口】 ============================================

if __name__ == "__main__":
    # 测试日志系统
    print("=" * 60)
    print("日志系统测试")
    print("=" * 60)
    print()
    
    # 初始化日志
    logger = get_logger(
        name="test_logger",
        level="DEBUG",
        log_dir="test_logs",
        use_color=True
    )
    
    # 测试各等级日志
    logger.debug("🔍 这是一条调试日志")
    logger.info("ℹ️  这是一条信息日志")
    logger.warning("⚠️  这是一条警告日志")
    logger.error("❌ 这是一条错误日志")
    logger.critical("🔴 这是一条严重日志")
    
    # 测试异常日志
    try:
        raise ValueError("测试异常")
    except Exception:
        logger.exception("捕获到异常")
    
    # 测试装饰器
    @log_function_call(logger)
    def test_function(x, y):
        return x + y
    
    print()
    print("测试装饰器:")
    result = test_function(10, 20)
    print(f"结果：{result}")
    
    # 测试计时器
    print()
    print("测试计时器:")
    with log_timer("测试操作", logger):
        import time
        time.sleep(0.5)
    
    # 显示日志文件
    print()
    config = LoggerConfig()
    log_files = config.get_log_files()
    print("日志文件位置:")
    for name, path in log_files.items():
        print(f"  {name}: {path}")
    
    print()
    print_success("日志系统测试完成！")
