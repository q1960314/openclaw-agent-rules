# ==============================================
# 量化系统 - 主入口文件
# 【优化】模块化重构版本
# ==============================================
# 功能：系统主入口，整合所有模块
# 职责：初始化、路由分发、服务启动
# ==============================================

# ============================================== 【模块导入 - 【优化】标记】 ==============================================
# 【优化】导入自定义模块
from modules.config_manager import (
    # 配置参数（保持原值不变）
    AUTO_RUN_MODE, STRATEGY_TYPE, ALLOWED_MARKET,
    START_DATE, END_DATE,
    WECHAT_ROBOT_ENABLED, WECHAT_ROBOT_URL,
    INIT_CAPITAL, MAX_HOLD_DAYS, STOP_LOSS_RATE, STOP_PROFIT_RATE,
    COMMISSION_RATE, MIN_COMMISSION, STAMP_TAX_RATE,
    SINGLE_STOCK_POSITION, INDUSTRY_POSITION, MAX_HOLD_STOCKS,
    MAX_DRAWDOWN_STOP, DRAWDOWN_STOP_DAYS, MAX_TRADE_RATIO,
    PRICE_ADJUST, SLIPPAGE_RATE,
    FILTER_CONFIG, MARKET_CONDITION, DYNAMIC_WEIGHT_MULTIPLIER,
    CORE_CONFIG, STRATEGY_CONFIG, STOCK_PICK_CONFIG,
    SERVER_HOST, SERVER_PORT, API_BASE_URL,
    TUSHARE_TOKEN, TUSHARE_API_URL,
    FETCH_EXTEND_DATA, VISUALIZATION, LOG_LEVEL,
    FETCH_OPTIMIZATION, EXTEND_FETCH_CONFIG,
    # 配置管理器
    config_manager, ConfigManager
)
from modules.data_fetcher import DataFetcher
from modules.storage_manager import StorageManager
from modules.data_validator import DataValidator
from modules.strategy_core import StrategyCore
from modules.backtest_engine import BacktestEngine

# 【优化】保留原有基础导入
import os
import sys
import json
import time
import random
import uuid
import logging
import logging.handlers
import threading
import signal
import socket
import gc
import tracemalloc
from datetime import datetime, timedelta
from typing import Optional, Callable, Tuple, Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
from copy import deepcopy
from threading import Thread, Lock, RLock
import pandas as pd
import numpy as np
import requests
from tqdm import tqdm

# Windows 控制台中文乱码适配
if sys.platform.startswith('win'):
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass

# 依赖检查
try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("❌ 缺少 Flask 依赖，请运行：pip install flask flask-cors")
    sys.exit(1)

try:
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
except ImportError:
    print("❌ 缺少 Tushare 依赖，请运行：pip install tushare")
    sys.exit(1)

# 【优化】添加 openpyxl 依赖检查
try:
    import openpyxl
except ImportError:
    print("⚠️  缺少 openpyxl 依赖，回测报告导出将失败，请运行：pip install openpyxl")

if VISUALIZATION:
    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        print("⚠️  缺少 Matplotlib 依赖，可视化功能将关闭，请运行：pip install matplotlib")
        VISUALIZATION = False

# ============================================== 【路径配置 - 【优化】标记】 ==============================================
# 【优化】路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'data')
STOCKS_DIR = os.path.join(BASE_DIR, 'data_all_stocks')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CHART_DIR = os.path.join(BASE_DIR, 'charts')
FAILED_STOCKS_FILE = os.path.join(OUTPUT_DIR, 'failed_stocks.json')
FETCH_PROGRESS_FILE = os.path.join(OUTPUT_DIR, 'fetch_progress.json')
PERMANENT_FAILED_FILE = os.path.join(OUTPUT_DIR, 'permanent_failed_stocks.json')

# 目录创建
for dir_path in [OUTPUT_DIR, STOCKS_DIR, LOG_DIR, CHART_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

# 【优化】API 日期格式
START_DATE_API = START_DATE.replace("-", "")
END_DATE_API = END_DATE.replace("-", "")
LATEST_DATE = datetime.now().strftime("%Y%m%d")
LATEST_START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

# ============================================== 【全局状态 - 【优化】标记】 ==============================================
# 【优化】线程安全锁
GLOBAL_LOCK = RLock()
TASK_STATUS_LOCK = RLock()
CONFIG_LOCK = RLock()
EXECUTOR_LOCK = RLock()
APP_RUNNING_LOCK = RLock()

# 全局状态
APP_RUNNING = True
GLOBAL_EXECUTOR: Optional[ThreadPoolExecutor] = None
FLASK_SERVER = None

# ============================================== 【板块映射 - 【优化】标记】 ==============================================
# 【优化】板块映射（保持原有逻辑）
MARKET_MAP = {
    "主板": ["主板", "MainBoard", "mainboard", "主板/中小板", "上交所主板", "深交所主板"],
    "创业板": ["创业板", "ChiNext", "chinext", "深交所创业板"],
    "科创板": ["科创板", "STAR", "star", "上交所科创板"],
    "北交所": ["北交所", "BSE", "bse", "北京证券交易所"]
}

def is_market_allowed(stock_market, allowed_markets):
    """【优化】判断股票板块是否在允许的列表中"""
    if pd.isna(stock_market) or stock_market is None:
        return False
    stock_market_str = str(stock_market).strip()
    for allowed in allowed_markets:
        if allowed in MARKET_MAP:
            for alias in MARKET_MAP[allowed]:
                if stock_market_str == alias:
                    return True
        if stock_market_str == allowed:
            return True
    return False

def is_port_in_use(port):
    """【优化】检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except:
            return True

def find_available_port(start_port, max_attempts=10):
    """【优化 R2】端口自动切换"""
    for attempt in range(max_attempts):
        test_port = start_port + attempt
        if not is_port_in_use(test_port):
            logger.info(f"✅ 找到可用端口：{test_port}")
            return test_port
    logger.error(f"❌ 无法找到可用端口（{start_port}-{start_port + max_attempts}）")
    return None

# ============================================== 【日志配置 - 【优化】标记】 ==============================================
# 【优化 L4】日志配置
def setup_logging():
    """【优化】配置日志系统，分级输出"""
    LOG_JSON_PATH = os.path.join(LOG_DIR, "quant_structured.log")
    logger = logging.getLogger("quant_system")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ERROR 日志
    error_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "quant_error.log"),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # INFO 日志
    info_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "quant_info.log"),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)
    
    # 控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ============================================== 【配置检查 - 【优化】标记】 ==============================================
# 【优化】配置检查（使用配置管理器）
def check_config():
    """【优化】全面检查配置参数合法性"""
    return config_manager.check_config()

check_config()

# ============================================== 【全局状态管理 - 【优化】标记】 ==============================================
def get_app_running():
    """【优化】获取 APP 运行状态"""
    with APP_RUNNING_LOCK:
        return APP_RUNNING

def set_app_running(value):
    """【优化】设置 APP 运行状态"""
    global APP_RUNNING
    with APP_RUNNING_LOCK:
        APP_RUNNING = value

# ============================================== 【永久失败股票管理 - 【优化】标记】 ==============================================
def load_permanent_failed():
    """【优化】加载永久失败股票清单"""
    storage = StorageManager(BASE_DIR)
    return storage.load_permanent_failed()

def save_permanent_failed(permanent_failed):
    """【优化】保存永久失败股票清单"""
    storage = StorageManager(BASE_DIR)
    storage.save_permanent_failed(permanent_failed)

def add_permanent_failed(ts_code, reason=""):
    """【优化】添加股票到永久失败清单"""
    storage = StorageManager(BASE_DIR)
    storage.add_permanent_failed(ts_code, reason)

# ============================================== 【信号处理 - 【优化】标记】 ==============================================
def signal_handler(signum, frame):
    """【优化】处理退出信号"""
    global FLASK_SERVER, GLOBAL_EXECUTOR
    logger.info("🛑 收到退出信号，正在优雅关闭程序...")
    set_app_running(False)
    
    with EXECUTOR_LOCK:
        if GLOBAL_EXECUTOR is not None:
            try:
                GLOBAL_EXECUTOR.shutdown(wait=False)
                logger.info("✅ 线程池已关闭")
                GLOBAL_EXECUTOR = None
            except Exception as e:
                logger.warning(f"线程池关闭异常：{e}")
    
    if FLASK_SERVER is not None:
        try:
            FLASK_SERVER.shutdown()
            logger.info("✅ Flask 服务已关闭")
        except Exception as e:
            logger.warning(f"Flask 服务关闭异常：{e}")
    
    gc.collect()
    logger.info("✅ 程序已安全退出")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================== 【API 初始化 - 【优化】标记】 ==============================================
def get_pro_api(config):
    """【优化】初始化 Tushare API"""
    ts.set_token(config['token'])
    pro = ts.pro_api()
    pro._DataApi__http_url = config['api_url']
    return pro, config

# ============================================== 【Flask 后端 - 【优化】保留原有功能】 ==============================================
flask_app = Flask(__name__)
CORS(flask_app)
TASK_QUEUE = Queue()
TASK_STATUS = {}

@flask_app.route('/')
def index():
    """【优化】首页"""
    return f"量化系统后端 API 服务已启动！当前模式：{AUTO_RUN_MODE} | 当前策略：{STRATEGY_TYPE}"

@flask_app.route('/api/health', methods=['GET'])
def health_check():
    """【优化】健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mode': AUTO_RUN_MODE,
        'strategy': STRATEGY_TYPE,
        'running': get_app_running()
    })

@flask_app.route('/api/config', methods=['GET'])
def get_config_api():
    """【优化】获取配置"""
    config = config_manager.load_config()
    return jsonify({
        'token': config['token'][:10] + '...' if len(config['token']) > 10 else config['token'],
        'api_url': config['api_url'],
        'start_date': config['start_date'],
        'end_date': config['end_date'],
        'strategy_type': STRATEGY_TYPE
    })

@flask_app.route('/api/config', methods=['POST'])
def update_config_api():
    """【优化】更新配置"""
    data = request.json
    config = config_manager.load_config()
    config.update(data)
    config_manager.save_config(config)
    return jsonify({'success': True})

@flask_app.route('/api/fetch', methods=['POST'])
def start_fetch_api():
    """【优化】启动抓取"""
    data = request.json
    task_id = str(uuid.uuid4())
    TASK_QUEUE.put({
        'id': task_id,
        'config': data.get('config', config_manager.load_config()),
        'fetch_type': data.get('fetch_type', 'full')
    })
    with TASK_STATUS_LOCK:
        TASK_STATUS[task_id] = {'status': 'queued', 'progress': 0, 'message': '任务已排队'}
    return jsonify({'task_id': task_id, 'status': 'queued'})

@flask_app.route('/api/fetch/<task_id>', methods=['GET'])
def get_fetch_status_api(task_id):
    """【优化】获取抓取状态"""
    with TASK_STATUS_LOCK:
        status = TASK_STATUS.get(task_id, {'status': 'not_found'})
    return jsonify(status)

# ============================================== 【主程序入口 - 【优化】标记】 ==============================================
def run_by_mode():
    """
    【优化】根据运行模式执行不同流程
    支持：抓取 + 回测/仅服务/仅回测/每日选股
    """
    logger.info(f"开始执行运行模式：{AUTO_RUN_MODE}")
    
    if AUTO_RUN_MODE == "仅服务":
        # 仅启动 Flask 服务
        logger.info("启动 Flask 后端服务...")
        flask_app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, threaded=True)
        return
    
    elif AUTO_RUN_MODE == "抓取 + 回测":
        logger.info("执行【抓取 + 回测】模式...")
        # TODO: 实现抓取和回测逻辑
        logger.info("抓取 + 回测模式待实现")
        return
    
    elif AUTO_RUN_MODE == "仅回测":
        logger.info("执行【仅回测】模式...")
        # TODO: 实现回测逻辑
        logger.info("仅回测模式待实现")
        return
    
    elif AUTO_RUN_MODE == "每日选股":
        logger.info("执行【每日选股】模式...")
        # TODO: 实现每日选股逻辑
        logger.info("每日选股模式待实现")
        return
    
    else:
        logger.error(f"❌ 无效的运行模式：{AUTO_RUN_MODE}")
        return

def main():
    """
    【优化】主程序入口
    """
    print("="*80)
    print("  量化系统 - 模块化重构版")
    print("="*80)
    print(f"当前运行模式：{AUTO_RUN_MODE} | 当前策略：{STRATEGY_TYPE}")
    print(f"服务地址：http://localhost:{SERVER_PORT}")
    print(f"并发线程数：{FETCH_OPTIMIZATION['max_workers']}")
    print(f"多资讯源抓取：{EXTEND_FETCH_CONFIG.get('enable_multi_news', False)}")
    print("="*80)
    
    try:
        # 执行主流程
        run_by_mode()
        
        logger.info("✅ 主程序执行完成，正在清理资源...")
        set_app_running(False)
        
        # 清理线程池
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    logger.info("✅ 线程池已关闭")
                    GLOBAL_EXECUTOR = None
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        gc.collect()
        logger.info("✅ 所有资源已清理，程序退出")
    
    except KeyboardInterrupt:
        logger.info("🛑 程序被用户手动终止（Ctrl+C）")
        print("\n" + "="*80)
        print("程序已手动停止，感谢使用！")
        print("="*80)
        set_app_running(False)
        
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    GLOBAL_EXECUTOR = None
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        gc.collect()
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ 程序运行异常：{str(e)}", exc_info=True)
        print("="*80)
        print(f"程序运行出错：{str(e)}")
        print(f"请查看日志文件排查问题：logs/quant_error.log")
        print("="*80)
        
        set_app_running(False)
        
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    GLOBAL_EXECUTOR = None
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        gc.collect()
        sys.exit(1)

if __name__ == "__main__":
    main()
