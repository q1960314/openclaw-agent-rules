# ============================================== 【全局统一配置区：所有要改的参数全在这里】 ==============================================
# ============================================ 【1. 核心运行配置 - 最常用，每次运行必看】 ============================================
# --------------------------- 1.1 运行模式选择 ---------------------------
# 【可选模式】：
# "抓取+回测" ：先从Tushare抓取最新数据，再自动跑回测（最常用，首次使用建议先跑这个）
# "仅服务"   ：仅启动Flask后端API服务，不执行抓取/回测/选股
# "仅回测"   ：不重新抓取数据，直接用本地已缓存的数据跑回测（速度快）
# "每日选股" ：抓取最新1个交易日数据，执行实盘选股（适合每天收盘后用）
AUTO_RUN_MODE = "每日选股"
# --------------------------- 1.2 策略类型选择 ---------------------------
# 【可选策略】：
# "打板策略"   ：原23维评分策略，追涨停板用，新手首选，但风险较高
# "缩量潜伏策略" ：涨停后缩量回调低吸，不追高，风险相对较低
# "板块轮动策略" ：电风扇行情专用，抓板块轮动机会
STRATEGY_TYPE = "打板策略"
# --------------------------- 1.3 板块筛选配置 ---------------------------
# 【可选板块】："主板", "创业板", "科创板", "北交所"
# 【配置示例】：
#  只选主板：ALLOWED_MARKET = ["主板"]
#  选主板和创业板：ALLOWED_MARKET = ["主板", "创业板"]
#  所有板块：ALLOWED_MARKET = ["主板", "创业板", "科创板", "北交所"]
# 【注意】：这里选什么板块，就只会抓取什么板块的股票，不会浪费时间抓全市场
ALLOWED_MARKET = ["主板"]
# ============================================ 【2. 时间配置 - 抓取/回测/选股通用】 ============================================
START_DATE = "2018-03-01"  # 全量回测/抓取的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-02-28"    # 全量回测/抓取的结束日期（格式：YYYY-MM-DD）
# ============================================ 【3. 消息推送配置】 ============================================
WECHAT_ROBOT_ENABLED = True
WECHAT_ROBOT_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4f8c1eb8-1240-4fde-933f-a783e99b90dd"
# ============================================ 【4. 交易核心参数 - 回测/选股通用】 ============================================
INIT_CAPITAL = 5000              # 初始本金（单位：元，回测用）
MAX_HOLD_DAYS = 3                 # 最长持股天数（单位：天，超过就强制卖出）
STOP_LOSS_RATE = 0.06             # 基础止损比例（默认6%，亏损超过这个比例就止损）
STOP_PROFIT_RATE = 0.12           # 基础止盈比例（默认12%，盈利超过这个比例就止盈）
COMMISSION_RATE = 0.00025         # 佣金比例（万2.5，即0.025%）
MIN_COMMISSION = 5                 # 最低佣金（5元/笔，不足5元按5元收，A股实盘规则）
STAMP_TAX_RATE = 0.001            # 印花税（卖出千1，仅卖出收取，买入不收，A股实盘规则）
SINGLE_STOCK_POSITION = 0.2        # 单只股票最大仓位占比（20%，即最多用20%的钱买一只股票）
INDUSTRY_POSITION = 0.3            # 单行业最大仓位占比（30%，避免单一行业风险）
MAX_HOLD_STOCKS = 5                # 最大持仓股票数（5只，分散风险）
MAX_DRAWDOWN_STOP = 0.15           # 账户最大回撤≥15%，强制清仓空仓休息
DRAWDOWN_STOP_DAYS = 3             # 清仓后空仓休息天数（3天）
MAX_TRADE_RATIO = 0.05             # 单次买入量≤当日成交量5%（避免冲击成本，A股合规）
PRICE_ADJUST = "front"              # 复权类型：front(前复权)/back(后复权)/none(不复权)，回测建议用前复权
SLIPPAGE_RATE = 0.005               # 实盘滑点：单边0.5%，即买入时多花0.5%，卖出时少卖0.5%
# ============================================ 【5. 前置筛选配置 - 全量修复配置关联】 ============================================
# 【注意】Tushare官方标准：amount单位为千元，vol单位为手，所有数值已严格校准
FILTER_CONFIG = {
    "min_amount": 300000,        # 最低成交额（千元，300000千元=30亿元，保证流动性）
    "min_turnover": 3,           # 最低换手率（%，3%以上保证股性活跃）
    "exclude_st": True,           # 是否排除ST/*ST/退市整理股票（True=排除，避免踩雷）
    "exclude_suspend": True,      # 是否排除停牌股票（True=排除，避免资金占用）
    "max_fetch_retry": 3,         # 单只股票最大抓取重试次数（3次，超过标记为永久失败）
    "permanent_failed_expire": 30,  # 永久失败过期天数
    # 【优化 D2】智能重试配置
    "smart_retry_enabled": True,        # 开启智能重试
    "smart_retry_days": 7,              # 优质标的重试间隔（7 天）
    "fundamental_check": True           # 重试前检查基本面 # 永久失败股票自动过期天数（30天后重新尝试抓取）
}
# ============================================ 【6. 评分规则 - 选股+回测通用】 ============================================
# 【优化 S2】动态权重配置
MARKET_CONDITION = "normal"  # 市场状态：bull/bear/normal
DYNAMIC_WEIGHT_MULTIPLIER = {
    "bull": 1.2,    # 牛市放大进攻因子权重
    "bear": 0.8,    # 熊市放大防守因子权重
    "normal": 1.0   # 正常市场
}

CORE_CONFIG = {
    "pass_score": 12,
    # 【优化 S2】动态权重使能
    "enable_dynamic_weight": True,  # 你的策略及格分调低，因为是精准买点筛选
    "strategy_pass_score": {
        "打板策略": 18,
        "缩量潜伏策略": 12,  # 你的策略专属及格分
        "板块轮动策略": 17
    },
    "items": {
        # ----------------------
        # 【你的缩量潜伏策略核心高分项】
        # ----------------------
        "缩量到首板1/3以内": [3, "current_vol_ratio <= 0.33", {"打板策略": 0, "缩量潜伏策略": 3, "板块轮动策略": 0}],
        "缩量到首板1/3~1/2": [2, "current_vol_ratio > 0.33 and current_vol_ratio <= 0.5", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "精准回踩支撑位±1%": [3, "abs(price_to_support_ratio) <= 0.01", {"打板策略": 0, "缩量潜伏策略": 3, "板块轮动策略": 0}],
        "回踩支撑位±2%": [2, "abs(price_to_support_ratio) > 0.01 and abs(price_to_support_ratio) <= 0.02", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "首板放量≥2倍": [2, "board_vol_growth >= 2", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "首板放量≥1.5倍": [1, "board_vol_growth >= 1.5 and board_vol_growth < 2", {"打板策略": 0, "缩量潜伏策略": 1, "板块轮动策略": 0}],
        "回调天数3-5天": [2, "days_after_board >=3 and days_after_board <=5", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "回调天数6-10天": [1, "days_after_board >=6 and days_after_board <=10", {"打板策略": 0, "缩量潜伏策略": 1, "板块轮动策略": 0}],
        "流通市值50亿-200亿": [1, "float_market_cap >= 50 and float_market_cap <= 200", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "成交额≥1亿": [1, "amount >= 100000", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "无减持公告": [1, "no_reduction == 1", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "无监管问询": [1, "no_inquiry == 1", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        # ----------------------
        # 原有打板策略核心项（保留不变）
        # ----------------------
        "连板高度≥3板": [2, "up_down_times >= 3", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0.5}],
        "连板高度2板": [1, "up_down_times == 2", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0.5}],
        "机构净买入≥5000万": [2, "inst_buy >= 5000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1.5}],
        "游资净买入≥3000万": [2, "youzi_buy >= 3000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1}],
        "主线行业匹配": [2, "is_main_industry == 1", {"打板策略": 1, "缩量潜伏策略": 0, "板块轮动策略": 2}],
        "热点题材≥2个": [2, "concept_count >= 2", {"打板策略": 1, "缩量潜伏策略": 0, "板块轮动策略": 2}],
        "换手率3%-10%": [1, "turnover_ratio >= 3 and turnover_ratio <= 10", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1}],
        "封单金额≥1亿": [1, "order_amount >= 10000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
        "非尾盘封板": [1, "first_limit_time <= '14:30'", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
        "炸板次数≤3次": [1, "break_limit_times <= 3", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
    }
}
# ============================================ 【7. 三大策略专属筛选配置】 ============================================
STRATEGY_CONFIG = {
    "打板策略": {
        "type": "link",                # 策略类型：link=连板策略，first=首板策略
        "min_order_ratio": 0.03,        # 最低封单比（3%，封单太少容易炸板）
        "max_break_times": 1,           # 最大炸板次数（1次，炸板太多说明股性弱）
        "link_board_range": [2, 4],      # 连板高度范围（2-4板，太低没辨识度，太高风险大）
        "exclude_late_board": True,      # 是否排除尾盘封板（True=排除，尾盘封板通常是偷袭）
        "stop_loss_rate": 0.06,           # 止损比例（默认6%，亏损超过这个比例就止损）
        "stop_profit_rate": 0.12,         # 止盈比例（默认12%，盈利超过这个比例就止盈）
        "max_hold_days": 2                 # 最长持股天数（单位：天，超过就强制卖出）
    },
    # ----------------------
    # 【完全贴合你需求】首板后缩量回调潜伏策略
    # ----------------------
    "缩量潜伏策略": {
        "type": "first_board_pullback",  # 策略类型：首板回调潜伏
        # 【核心规则】首板要求
        "first_board_limit": True,        # 必须是阶段首次涨停
        "board_volume_growth": 1.5,       # 涨停当天成交量必须是前5日均值的1.5倍以上（放量涨停，确认主力进场）
        # 【核心规则】缩量要求
        "shrink_volume_ratio": [1/3, 1/2],# 回调期间缩量到首板成交量的1/3~1/2（你要的核心规则）
        "shrink_days_range": [3, 10],     # 首板后3~10天内完成缩量回调（时间范围）
        # 【核心规则】回调支撑位
        "pullback_support_level": 0.5,     # 回调支撑位：0.5=首板1/2分位，0.33=首板1/3分位（你可以直接改这个数字）
        "support_tolerance": 0.02,         # 支撑位容错：±2%，避免精准卡点错过买点
        # 【交易规则】止损止盈
        "stop_loss_rate": 0.03,            # 止损：跌破首板最低价3%止损（比打板策略更严格）
        "stop_profit_rate": 0.15,          # 止盈：反弹15%或触及首板涨停价止盈
        "max_hold_days": 8,                # 最长持股8天，短线快进快出
        "rotate_days": 1                   # 每日选股，每日更新买点
    },
    "板块轮动策略": {
        "type": "industry",            # 策略类型：industry=行业轮动策略
        "rotate_days": 3,               # 轮动调仓天数（每3天调一次仓）
        "stop_loss_rate": 0.05,         # 轮动策略专属止损（5%，比打板策略更严格）
        "stop_profit_rate": 0.1,        # 轮动策略专属止盈（10%，比打板策略更保守）
        "main_trend": True,              # 是否只做主线行业（True=只抓热点板块）
        "fund_inflow_top": 30,           # 只选资金流入前30的行业
        "max_hold_days": 3                 # 最长持股天数（单位：天，超过就强制卖出）
    }
}
# ============================================ 【8. 今日选股专属配置】 ============================================
STOCK_PICK_CONFIG = {
    "min_pick_score": 16,        # 选股最低评分（16分以上才考虑）
    "max_output_count": 10,       # 最大输出股票数（10只，太多看不过来）
    "only_main_board": True,      # 是否只选主板（True=只选主板，和ALLOWED_MARKET配合）
    "export_excel": True,          # 是否导出Excel选股清单（True=导出）
    "export_score_detail": True,   # 是否导出评分明细（True=导出，方便分析为什么选这只）
    "fetch_days": 1                # 每日选股抓取天数（仅需最新1天，节省请求次数）
}
# ============================================ 【9. 后端核心配置 - 一般不用改】 ============================================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
API_BASE_URL = f"http://localhost:{SERVER_PORT}/api"
# 【注意】你的Token完全未修改，保留你的原始值
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
FETCH_EXTEND_DATA = True
VISUALIZATION = False
LOG_LEVEL = "INFO"
# ============================================ 【10. 抓取性能优化配置 - 针对你10000分超高积分专属优化】 ============================================
# 【配置说明】针对你10000分的超高积分，大幅提升抓取效率
# 并发线程数：15（10000分可开10-20）
# 每分钟最大请求数：3000（预留2000次缓冲，避免触发限流，你可以根据实际情况继续调高到4000-5000）
FETCH_OPTIMIZATION = {
    'max_workers': 20,            # 并发线程数，10000分可开15-20
    'batch_io_interval': 10,      
    'max_requests_per_minute': 4000 # 每分钟最大请求数，10000分可设3000-5000
}
# ============================================ 【11. 扩展数据抓取开关 - 新增多资讯源配置】 ============================================
EXTEND_FETCH_CONFIG = {
    "enable_top_list": True,        # 龙虎榜每日明细
    "enable_top_inst": True,        # 龙虎榜机构席位明细
    "enable_finance_sheet": True,   # 财务三表
    "enable_hk_hold": True,         # 北向资金
    "enable_cyq": True,             # 筹码分布
    "enable_block_trade": True,     # 大宗交易
    "enable_index_weight": True,    # 指数成分股权重
    "enable_kpl_concept": True,     # 概念板块
    "enable_stk_limit": True,       # 【新增】每日涨跌停数据
    
    # ----------------------
    # 【新增】多资讯源配置
    # ----------------------
    # 【优化 D6】默认开启多资讯源，财联社必开
"enable_multi_news": True,       # 开启多资讯源抓取
    # 你需要开启的资讯源，可自由增删，对应Tushare的src参数
    "news_source_list": [
        "sina",         # 新浪财经
        "cls",          # 财联社（短线核心，必开）
        "yicai",        # 第一财经
        "eastmoney",    # 东方财富
        "xueqiu",       # 雪球
        "10jqka",       # 同花顺
        "ifeng",        # 凤凰财经
        "jrj",          # 金融界
        "yuncaijing",   # 云财经
        "wallstreetcn"  # 华尔街见闻
    ]
}
# ============================================== 【配置区结束，下面代码不用动】 ==============================================

# ============================================== 【基础初始化 + 全局工具 - 导入移至最顶部】 ==============================================
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
import tracemalloc  # 【优化 R1】内存追踪
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

# Windows控制台中文乱码适配
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
    print("❌ 缺少Flask依赖，请运行：pip install flask flask-cors")
    sys.exit(1)

try:
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
except ImportError:
    print("❌ 缺少Tushare依赖，请运行：pip install tushare")
    sys.exit(1)

# 【优化】添加 openpyxl 依赖检查，避免回测报告导出失败
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
        print("⚠️  缺少Matplotlib依赖，可视化功能将关闭，请运行：pip install matplotlib")
        VISUALIZATION = False

# 路径配置
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

# 【修复】Tushare API日期格式转换，移至导入之后
START_DATE_API = START_DATE.replace("-", "")
END_DATE_API = END_DATE.replace("-", "")
LATEST_DATE = datetime.now().strftime("%Y%m%d")
LATEST_START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

# 线程安全锁（可重入锁，避免嵌套锁死锁）
GLOBAL_LOCK = RLock()
TASK_STATUS_LOCK = RLock()
CONFIG_LOCK = RLock()
EXECUTOR_LOCK = RLock()
APP_RUNNING_LOCK = RLock()

# 全局状态 - 统一规范初始化
APP_RUNNING = True
GLOBAL_EXECUTOR: Optional[ThreadPoolExecutor] = None  # 明确类型和初始值
FLASK_SERVER = None

# 板块映射
MARKET_MAP = {
    "主板": ["主板", "MainBoard", "mainboard", "主板/中小板", "上交所主板", "深交所主板"],
    "创业板": ["创业板", "ChiNext", "chinext", "深交所创业板"],
    "科创板": ["科创板", "STAR", "star", "上交所科创板"],
    "北交所": ["北交所", "BSE", "bse", "北京证券交易所"]
}

def is_market_allowed(stock_market, allowed_markets):
    """判断股票板块是否在允许的列表中"""
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
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except:
            return True

def find_available_port(start_port, max_attempts=10):
    """
    【优化 R2】端口自动切换，寻找可用端口
    """
    for attempt in range(max_attempts):
        test_port = start_port + attempt
        if not is_port_in_use(test_port):
            logger.info(f"✅ 找到可用端口：{test_port}")
            return test_port
    logger.error(f"❌ 无法找到可用端口（{start_port}-{start_port + max_attempts}）")
    return None

# 日志配置
def setup_logging():
    """配置日志系统，分级输出"""
    # 【优化 L4】增加结构化日志配置
    LOG_JSON_PATH = os.path.join(LOG_DIR, "quant_structured.log")
    logger = logging.getLogger("quant_system")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()  # 清除默认handler，避免重复输出
    
    # 日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ERROR日志：按天轮转，保留7天
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
    
    # INFO日志：按天轮转，保留30天
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
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# 配置检查
def check_config():
    """全面检查配置参数合法性"""
    logger.info("开始校验配置参数合法性...")
    try:
        # 时间格式检查
        start = datetime.strptime(START_DATE, "%Y-%m-%d")
        end = datetime.strptime(END_DATE, "%Y-%m-%d")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
    except Exception as e:
        logger.error(f"❌ 时间配置错误：{e}，请检查格式是否为YYYY-MM-DD")
        sys.exit(1)
    
    # 交易参数检查
    if not (0 < STOP_LOSS_RATE < 1) or not (0 < STOP_PROFIT_RATE < 1):
        logger.error("❌ 止损/止盈比例必须在0-1之间")
        sys.exit(1)
    if INIT_CAPITAL < 100:
        logger.error("❌ 初始本金不能低于100元")
        sys.exit(1)
    
    # 运行模式检查
    if AUTO_RUN_MODE not in ["抓取+回测", "仅服务", "仅回测", "每日选股"]:
        logger.error(f"❌ 运行模式错误，仅支持：抓取+回测/仅服务/仅回测/每日选股，当前：{AUTO_RUN_MODE}")
        sys.exit(1)
    
    # 策略类型检查
    if STRATEGY_TYPE not in STRATEGY_CONFIG.keys():
        logger.error(f"❌ 策略类型错误，仅支持：{list(STRATEGY_CONFIG.keys())}，当前：{STRATEGY_TYPE}")
        sys.exit(1)
    
    # 端口检查
    if SERVER_PORT < 1024 or SERVER_PORT > 65535:
        logger.error("❌ 端口号必须在1024-65535之间")
        sys.exit(1)
    
    # 计算每秒请求数，适配分钟级限流
    FETCH_OPTIMIZATION['max_requests_per_second'] = max(1, FETCH_OPTIMIZATION['max_requests_per_minute'] // 60)
    
    logger.info("✅ 配置参数校验通过！")
    return True

check_config()

# 全局配置缓存（全量锁保护）
_GLOBAL_CONFIG_CACHE = None

def load_config():
    """加载全局配置，带锁保护避免竞态条件"""
    global _GLOBAL_CONFIG_CACHE
    with CONFIG_LOCK:
        if _GLOBAL_CONFIG_CACHE is None:
            _GLOBAL_CONFIG_CACHE = {
                'token': TUSHARE_TOKEN,
                'api_url': TUSHARE_API_URL,
                'start_date': START_DATE_API,
                'end_date': END_DATE_API,
                'output_dir': OUTPUT_DIR,
                'stocks_dir': STOCKS_DIR
            }
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                        _GLOBAL_CONFIG_CACHE.update(loaded_config)
                except Exception as e:
                    logger.warning(f"加载配置文件失败，使用默认配置：{e}")
        return _GLOBAL_CONFIG_CACHE.copy()

def save_config(config):
    """保存全局配置，带锁保护"""
    global _GLOBAL_CONFIG_CACHE
    with CONFIG_LOCK:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        _GLOBAL_CONFIG_CACHE = config.copy()

# ============================================== 【工具类 - 移至前面避免前置引用】 ==============================================
# 【优化 L3】异常分类定义
class DataFetchError(Exception):
    """数据抓取异常"""
    pass

class PermissionError(Exception):
    """权限异常"""
    pass

class LogicError(Exception):
    """逻辑异常"""
    pass

class NetworkError(Exception):
    """网络异常"""
    pass

class Utils:
    def __init__(self, pro, config):
        self.pro = pro
        self.config = config
        self.trade_cal = self.get_trade_cal()
        self.request_count = 0
        self.window_start = time.time()
        self.minute_request_count = 0
        self.minute_window_start = time.time()
    
    def get_trade_cal(self):
        """获取交易日历"""
        try:
            cal = self.pro.trade_cal(exchange='', start_date=START_DATE_API, end_date=END_DATE_API)
            # 【调试】打印接口返回
            logger.info(f"[调试] 交易日历接口返回：\n{cal}")
            if cal is not None and not cal.empty:
                # ✅ 修复：根据测试输出，字段名是 cal_date
                if 'cal_date' in cal.columns and 'is_open' in cal.columns:
                    cal['cal_date'] = pd.to_datetime(cal['cal_date'], format="%Y%m%d")
                    # 筛选出开市的日期，并转为列表
                    cal = cal[cal['is_open'] == 1]['cal_date'].tolist()
                    logger.info(f"✅ 加载交易日历完成，共{len(cal)}个交易日")
                    return cal
            logger.warning("⚠️  交易日历数据格式异常，使用空列表")
            return []
        except Exception as e:
            logger.warning(f"⚠️  获取交易日历失败：{e}，使用空列表")
            return []
    
    def get_prev_trade_date(self, date):
        """获取指定日期的前一个交易日"""
        date = pd.to_datetime(date)
        if not self.trade_cal:
            prev_date = date - timedelta(days=1)
            while prev_date.weekday() >= 5:
                prev_date -= timedelta(days=1)
            return prev_date
        if date not in self.trade_cal:
            valid_dates = [d for d in self.trade_cal if d < date]
            if not valid_dates:
                return date - timedelta(days=1)
            date = max(valid_dates)
        prev_dates = [d for d in self.trade_cal if d < date]
        return max(prev_dates) if prev_dates else date - timedelta(days=1)
    
    def is_trade_day(self, check_date=None):
        """判断指定日期是否为交易日"""
        if check_date is None:
            check_date = datetime.now()
        check_date = pd.to_datetime(check_date).normalize()
        if not self.trade_cal:
            return check_date.weekday() < 5
        return check_date in self.trade_cal
    
    def _rate_limit(self):
        """分钟级+秒级双重令牌桶限流，严格遵守Tushare规则"""
        # 秒级限流
        self.request_count += 1
        current_time = time.time()
        elapsed = current_time - self.window_start
        if elapsed >= 1.0:
            self.request_count = 1
            self.window_start = current_time
        if self.request_count > FETCH_OPTIMIZATION['max_requests_per_second']:
            sleep_time = 1.0 - elapsed
            time.sleep(sleep_time)
            self.request_count = 1
            self.window_start = time.time()
        
        # 分钟级限流（核心，避免Tushare封禁）
        self.minute_request_count += 1
        minute_elapsed = current_time - self.minute_window_start
        if minute_elapsed >= 60.0:
            self.minute_request_count = 1
            self.minute_window_start = current_time
        if self.minute_request_count > FETCH_OPTIMIZATION['max_requests_per_minute']:
            sleep_time = 60.0 - minute_elapsed
            logger.warning(f"⚠️  达到分钟级请求上限，休眠{sleep_time:.1f}秒")
            time.sleep(sleep_time)
            self.minute_request_count = 1
            self.minute_window_start = time.time()
    
    def request_retry(self, func, *args, **kwargs):
        """
        接口请求重试，带指数退避+限流+错误码处理
        :param func: Tushare接口函数
        :param args: 位置参数
        :param kwargs: 关键字参数，可传入timeout
        :return: 接口返回数据DataFrame
        """
        silent = kwargs.pop('silent', False)
        max_retry = kwargs.pop('max_retry', FILTER_CONFIG['max_fetch_retry'])
        timeout = kwargs.pop('timeout', 60)  # 默认超时60秒
        last_exception = None
        
        for i in range(max_retry):
            if not get_app_running():
                return pd.DataFrame()
            try:
                self._rate_limit()
                result = func(*args, **kwargs, timeout=timeout)
                if result is not None and not result.empty:
                    return result
                else:
                    time.sleep(0.2 * (i + 1))
                    continue
