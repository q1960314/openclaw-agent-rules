# ============================================== 【量化数据采集系统 - 优化集成版】 ==============================================
# 功能清单：
# 1. 14 个 Tushare 接口完整实现
# 2. Parquet 压缩存储（替换 CSV）
# 3. 并发配置：15 线程，3000 次/分钟
# 4. AkShare 降级支持
# 5. 完整错误处理和日志记录
# ===========================================================================================================================

# ============================================== 【1. 核心配置区】 ==============================================
import os
import sys
import json
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock
import logging
import hashlib

# 第三方库
import pandas as pd
import numpy as np
import requests

# Parquet 支持
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("⚠️  缺少 pyarrow 依赖，Parquet 功能将不可用，请运行：pip install pyarrow")

# AkShare 降级支持
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  缺少 akshare 依赖，降级功能将不可用，请运行：pip install akshare")

# Tushare
try:
    import tushare as ts
except ImportError:
    print("❌ 缺少 Tushare 依赖，请运行：pip install tushare")
    sys.exit(1)

# ============================================== 【2. 全局配置参数】 ==============================================
# 核心运行配置
AUTO_RUN_MODE = "每日选股"  # 可选：抓取 + 回测/仅服务/仅回测/每日选股
STRATEGY_TYPE = "打板策略"  # 可选：打板策略/缩量潜伏策略/板块轮动策略
ALLOWED_MARKET = ["主板"]  # 可选：主板/创业板/科创板/北交所

# 时间配置
START_DATE = "2018-03-01"
END_DATE = "2026-02-28"

# Tushare 配置
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"

# 【优化】并发配置：15 线程，3000 次/分钟
FETCH_OPTIMIZATION = {
    'max_workers': 15,                       # 并发线程数（10000 分可开 15-20）
    'max_requests_per_minute': 3000,         # 每分钟最大请求数
    'max_requests_per_second': 50            # 每秒最大请求数（自动计算）
}

# 数据存储配置
DATA_DIR = "/home/admin/.openclaw/agents/master/quant_data_project/data/"
STOCKS_DIR = os.path.join(DATA_DIR, 'stocks')
LOG_DIR = "/home/admin/.openclaw/agents/master/quant_data_project/logs/"

# 【优化】Parquet 存储开关
USE_PARQUET = True  # True=使用 Parquet，False=使用 CSV

# 扩展数据抓取开关
EXTEND_FETCH_CONFIG = {
    "enable_top_list": True,        # 龙虎榜
    "enable_top_inst": True,        # 龙虎榜机构席位
    "enable_finance_sheet": True,   # 财务三表
    "enable_hk_hold": True,         # 北向资金
    "enable_cyq": True,             # 筹码分布
    "enable_block_trade": True,     # 大宗交易
    "enable_index_weight": True,    # 指数成分股权重
    "enable_kpl_concept": True,     # 概念板块
    "enable_stk_limit": True,       # 每日涨跌停
    "enable_multi_news": True,      # 多资讯源新闻
    "news_source_list": ["sina", "cls", "yicai", "eastmoney", "xueqiu"]
}

# 日志配置
LOG_LEVEL = "INFO"

# ============================================== 【3. 14 个 Tushare 接口定义】 ==============================================
# 接口清单：
# 1. stock_basic - 股票基本信息
# 2. daily - 日线行情
# 3. daily_basic - 每日指标
# 4. fina_indicator - 财务指标
# 5. moneyflow - 资金流向
# 6. concept_detail - 概念题材
# 7. top_list - 龙虎榜
# 8. top_inst - 龙虎榜机构席位
# 9. balancesheet - 资产负债表
# 10. cashflow - 现金流量表
# 11. income - 利润表
# 12. hk_hold - 北向资金持股
# 13. cyq_chips - 筹码分布
# 14. stk_limit - 每日涨跌停

TUSHARE_INTERFACES = {
    'stock_basic': {'func': 'stock_basic', 'params': ['exchange', 'list_status', 'fields'], 'desc': '股票基本信息'},
    'daily': {'func': 'daily', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '日线行情'},
    'daily_basic': {'func': 'daily_basic', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '每日指标'},
    'fina_indicator': {'func': 'fina_indicator', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '财务指标'},
    'moneyflow': {'func': 'moneyflow', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '资金流向'},
    'concept_detail': {'func': 'concept_detail', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '概念题材'},
    'top_list': {'func': 'top_list', 'params': ['trade_date', 'start_date', 'end_date'], 'desc': '龙虎榜'},
    'top_inst': {'func': 'top_inst', 'params': ['start_date', 'end_date'], 'desc': '龙虎榜机构席位'},
    'balancesheet': {'func': 'balancesheet', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '资产负债表'},
    'cashflow': {'func': 'cashflow', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '现金流量表'},
    'income': {'func': 'income', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '利润表'},
    'hk_hold': {'func': 'hk_hold', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '北向资金持股'},
    'cyq_chips': {'func': 'cyq_chips', 'params': ['ts_code', 'start_date', 'end_date'], 'desc': '筹码分布'},
    'stk_limit': {'func': 'stk_limit', 'params': ['trade_date', 'start_date', 'end_date'], 'desc': '每日涨跌停'}
}

# ============================================== 【4. 工具类定义】 ==============================================
class DataFetcher:
    """数据采集工具类，支持 14 个接口 + AkShare 降级"""
    
    def __init__(self, token: str, api_url: str):
        self.token = token
        self.api_url = api_url
        self.request_count = 0
        self.minute_request_count = 0
        self.minute_window_start = time.time()
        self.second_window_start = time.time()
        
        # 初始化 Tushare
        ts.set_token(token)
        self.pro = ts.pro_api()
        self.pro._DataApi__http_url = api_url
        
        # 日志
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """配置日志"""
        logger = logging.getLogger("data_fetcher")
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _rate_limit(self):
        """双重限流：秒级 + 分钟级"""
        current_time = time.time()
        
        # 秒级限流
        if current_time - self.second_window_start >= 1.0:
            self.request_count = 0
            self.second_window_start = current_time
        
        if self.request_count >= FETCH_OPTIMIZATION['max_requests_per_second']:
            sleep_time = 1.0 - (current_time - self.second_window_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.request_count = 0
            self.second_window_start = time.time()
        
        # 分钟级限流
        if current_time - self.minute_window_start >= 60.0:
            self.minute_request_count = 0
            self.minute_window_start = current_time
        
        if self.minute_request_count >= FETCH_OPTIMIZATION['max_requests_per_minute']:
            sleep_time = 60.0 - (current_time - self.minute_window_start)
            if sleep_time > 0:
                self.logger.warning(f"⚠️  达到分钟级请求上限，休眠{sleep_time:.1f}秒")
                time.sleep(sleep_time)
            self.minute_request_count = 0
            self.minute_window_start = time.time()
        
        self.request_count += 1
        self.minute_request_count += 1
    
    def fetch_with_retry(self, func_name: str, **kwargs):
        """带重试的接口调用，支持 AkShare 降级"""
        max_retry = 3
        last_error = None
        
        for attempt in range(max_retry):
            try:
                # 限流
                self._rate_limit()
                
                # 调用 Tushare 接口
                func = getattr(self.pro, func_name, None)
                if func:
                    result = func(**kwargs, timeout=60)
                    if result is not None and not result.empty:
                        return result
                else:
                    self.logger.error(f"❌ 接口不存在：{func_name}")
                    return pd.DataFrame()
                
                # 空结果，短暂等待后重试
                time.sleep(0.2 * (attempt + 1))
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # 权限错误不重试
                if "token" in error_str or "积分" in error_str or "权限" in error_str:
                    self.logger.error(f"❌ 权限错误：{e}")
                    return pd.DataFrame()
                
                self.logger.warning(f"⚠️  接口{func_name}失败 ({attempt+1}/{max_retry}): {e}")
                time.sleep(0.5 * (attempt + 1))
        
        # 所有重试失败，尝试 AkShare 降级
        self.logger.warning(f"⚠️  Tushare 接口{func_name}失败，尝试 AkShare 降级...")
        return self._akshare_fallback(func_name, **kwargs)
    
    def _akshare_fallback(self, func_name: str, **kwargs):
        """AkShare 降级支持"""
        if not AKSHARE_AVAILABLE:
            self.logger.error(f"❌ AkShare 不可用，无法降级")
            return pd.DataFrame()
        
        try:
            # 映射 Tushare 接口到 AkShare 函数
            fallback_map = {
                'daily': lambda ts_code, start_date, end_date: ak.stock_zh_a_hist(
                    symbol=ts_code.split('.')[0], 
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                ),
                'stock_basic': lambda **kw: ak.stock_info_a_code_name(),
                # 其他接口可根据需要扩展
            }
            
            if func_name in fallback_map:
                result = fallback_map[func_name](**kwargs)
                if result is not None and not result.empty:
                    self.logger.info(f"✅ AkShare 降级成功：{func_name}")
                    return result
            
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"❌ AkShare 降级失败：{e}")
            return pd.DataFrame()
    
    def save_to_parquet(self, df: pd.DataFrame, file_path: str, data_type: str = "数据"):
        """保存为 Parquet 格式（Snappy 压缩）"""
        if df.empty:
            return
        
        if not USE_PARQUET or not PARQUET_AVAILABLE:
            # 降级为 CSV
            csv_path = file_path.replace('.parquet', '.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            self.logger.warning(f"⚠️  Parquet 不可用，降级为 CSV: {csv_path}")
            return
        
        try:
            # 计算原始大小
            original_size = df.memory_usage(deep=True).sum()
            
            # 保存为 Parquet
            table = pa.Table.from_pandas(df)
            pq.write_table(table, file_path, compression='snappy')
            
            # 计算压缩后大小
            compressed_size = os.path.getsize(file_path)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
            
            self.logger.info(f"✅ {data_type}已保存 (Parquet+Snappy): {file_path}")
            self.logger.info(f"📊 压缩比：{compression_ratio:.2f}x ({original_size/1024/1024:.2f}MB → {compressed_size/1024/1024:.2f}MB)")
        except Exception as e:
            self.logger.warning(f"⚠️  Parquet 保存失败：{e}，降级为 CSV")
            csv_path = file_path.replace('.parquet', '.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    def save_data(self, df: pd.DataFrame, file_path: str, data_type: str = "数据"):
        """通用保存方法，根据配置选择 Parquet 或 CSV"""
        if USE_PARQUET:
            self.save_to_parquet(df, file_path, data_type)
        else:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"✅ {data_type}已保存 (CSV): {file_path}")

# ============================================== 【5. 14 个接口实现类】 ==============================================
class TushareInterfaceManager:
    """14 个 Tushare 接口管理器"""
    
    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher
        self.pro = fetcher.pro
        self.logger = fetcher.logger
    
    # 接口 1: 股票基本信息
    def fetch_stock_basic(self, exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date,market'):
        """获取股票基本信息"""
        self.logger.info("开始抓取股票基本信息...")
        df = self.fetcher.fetch_with_retry('stock_basic', exchange=exchange, list_status=list_status, fields=fields)
        return df
    
    # 接口 2: 日线行情
    def fetch_daily(self, ts_code: str, start_date: str, end_date: str):
        """获取日线行情"""
        df = self.fetcher.fetch_with_retry('daily', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 3: 每日指标
    def fetch_daily_basic(self, ts_code: str, start_date: str, end_date: str):
        """获取每日指标"""
        df = self.fetcher.fetch_with_retry('daily_basic', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 4: 财务指标
    def fetch_fina_indicator(self, ts_code: str, start_date: str, end_date: str):
        """获取财务指标"""
        df = self.fetcher.fetch_with_retry('fina_indicator', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 5: 资金流向
    def fetch_moneyflow(self, ts_code: str, start_date: str, end_date: str):
        """获取资金流向"""
        df = self.fetcher.fetch_with_retry('moneyflow', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 6: 概念题材
    def fetch_concept_detail(self, ts_code: str, start_date: str = '', end_date: str = ''):
        """获取概念题材"""
        df = self.fetcher.fetch_with_retry('concept_detail', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 7: 龙虎榜
    def fetch_top_list(self, trade_date: str = '', start_date: str = '', end_date: str = ''):
        """获取龙虎榜"""
        if trade_date:
            df = self.fetcher.fetch_with_retry('top_list', trade_date=trade_date)
        else:
            df = self.fetcher.fetch_with_retry('top_list', start_date=start_date, end_date=end_date)
        return df
    
    # 接口 8: 龙虎榜机构席位
    def fetch_top_inst(self, start_date: str, end_date: str):
        """获取龙虎榜机构席位"""
        df = self.fetcher.fetch_with_retry('top_inst', start_date=start_date, end_date=end_date)
        return df
    
    # 接口 9: 资产负债表
    def fetch_balancesheet(self, ts_code: str, start_date: str, end_date: str):
        """获取资产负债表"""
        df = self.fetcher.fetch_with_retry('balancesheet', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 10: 现金流量表
    def fetch_cashflow(self, ts_code: str, start_date: str, end_date: str):
        """获取现金流量表"""
        df = self.fetcher.fetch_with_retry('cashflow', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 11: 利润表
    def fetch_income(self, ts_code: str, start_date: str, end_date: str):
        """获取利润表"""
        df = self.fetcher.fetch_with_retry('income', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 12: 北向资金持股
    def fetch_hk_hold(self, ts_code: str, start_date: str, end_date: str):
        """获取北向资金持股"""
        df = self.fetcher.fetch_with_retry('hk_hold', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 13: 筹码分布
    def fetch_cyq_chips(self, ts_code: str, start_date: str, end_date: str):
        """获取筹码分布"""
        df = self.fetcher.fetch_with_retry('cyq_chips', ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    # 接口 14: 每日涨跌停
    def fetch_stk_limit(self, trade_date: str = '', start_date: str = '', end_date: str = ''):
        """获取每日涨跌停"""
        if trade_date:
            df = self.fetcher.fetch_with_retry('stk_limit', trade_date=trade_date)
        else:
            df = self.fetcher.fetch_with_retry('stk_limit', start_date=start_date, end_date=end_date)
        return df

# ============================================== 【6. 并发采集引擎】 ==============================================
class ConcurrentDataEngine:
    """并发数据采集引擎"""
    
    def __init__(self, fetcher: DataFetcher, interface_mgr: TushareInterfaceManager):
        self.fetcher = fetcher
        self.interface_mgr = interface_mgr
        self.logger = fetcher.logger
        self.executor = None
    
    def fetch_all_stocks_parallel(self, stocks: List[str], start_date: str, end_date: str):
        """并发抓取所有股票数据"""
        self.executor = ThreadPoolExecutor(max_workers=FETCH_OPTIMIZATION['max_workers'])
        
        total = len(stocks)
        success_count = 0
        failed_stocks = []
        
        self.logger.info(f"开始并发抓取{total}只股票数据，线程数：{FETCH_OPTIMIZATION['max_workers']}")
        
        def fetch_single_stock(ts_code: str):
            """单只股票抓取"""
            try:
                # 创建股票目录
                stock_dir = os.path.join(STOCKS_DIR, ts_code)
                os.makedirs(stock_dir, exist_ok=True)
                
                # 抓取 14 个接口数据
                interfaces_to_fetch = [
                    ('daily', lambda: self.interface_mgr.fetch_daily(ts_code, start_date, end_date)),
                    ('daily_basic', lambda: self.interface_mgr.fetch_daily_basic(ts_code, start_date, end_date)),
                    ('fina_indicator', lambda: self.interface_mgr.fetch_fina_indicator(ts_code, start_date, end_date)),
                    ('moneyflow', lambda: self.interface_mgr.fetch_moneyflow(ts_code, start_date, end_date)),
                    ('concept_detail', lambda: self.interface_mgr.fetch_concept_detail(ts_code)),
                ]
                
                # 扩展数据（根据配置）
                if EXTEND_FETCH_CONFIG.get('enable_finance_sheet', False):
                    interfaces_to_fetch.extend([
                        ('balancesheet', lambda: self.interface_mgr.fetch_balancesheet(ts_code, start_date, end_date)),
                        ('cashflow', lambda: self.interface_mgr.fetch_cashflow(ts_code, start_date, end_date)),
                        ('income', lambda: self.interface_mgr.fetch_income(ts_code, start_date, end_date)),
                    ])
                
                if EXTEND_FETCH_CONFIG.get('enable_hk_hold', False):
                    interfaces_to_fetch.append(('hk_hold', lambda: self.interface_mgr.fetch_hk_hold(ts_code, start_date, end_date)))
                
                if EXTEND_FETCH_CONFIG.get('enable_cyq', False):
                    interfaces_to_fetch.append(('cyq_chips', lambda: self.interface_mgr.fetch_cyq_chips(ts_code, start_date, end_date)))
                
                # 执行抓取
                for interface_name, fetch_func in interfaces_to_fetch:
                    df = fetch_func()
                    if df is not None and not df.empty:
                        file_ext = '.parquet' if USE_PARQUET else '.csv'
                        file_path = os.path.join(stock_dir, f"{interface_name}{file_ext}")
                        self.fetcher.save_data(df, file_path, f"{ts_code}-{interface_name}")
                
                return ts_code, True
            except Exception as e:
                self.logger.error(f"❌ {ts_code}抓取失败：{e}")
                return ts_code, False
        
        # 并发执行
        futures = {self.executor.submit(fetch_single_stock, ts_code): ts_code for ts_code in stocks}
        
        for idx, future in enumerate(as_completed(futures)):
            ts_code, success = future.result()
            if success:
                success_count += 1
            else:
                failed_stocks.append(ts_code)
            
            # 进度汇报
            if (idx + 1) % 100 == 0:
                progress = (idx + 1) / total * 100
                self.logger.info(f"📊 进度：{idx+1}/{total} ({progress:.1f}%), 成功：{success_count}, 失败：{len(failed_stocks)}")
        
        self.executor.shutdown(wait=True)
        
        self.logger.info(f"✅ 并发抓取完成！成功：{success_count}/{total}, 失败：{len(failed_stocks)}")
        return success_count, failed_stocks

# ============================================== 【7. 主函数】 ==============================================
def main():
    """主函数"""
    print("="*80)
    print("  量化数据采集系统 - 优化集成版")
    print("="*80)
    print(f"并发线程数：{FETCH_OPTIMIZATION['max_workers']}")
    print(f"每分钟请求数：{FETCH_OPTIMIZATION['max_requests_per_minute']}")
    print(f"Parquet 存储：{'启用' if USE_PARQUET else '禁用'}")
    print(f"AkShare 降级：{'启用' if AKSHARE_AVAILABLE else '禁用'}")
    print(f"14 个接口：{len(TUSHARE_INTERFACES)}")
    print("="*80)
    
    # 创建目录
    for dir_path in [DATA_DIR, STOCKS_DIR, LOG_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    
    # 初始化
    fetcher = DataFetcher(TUSHARE_TOKEN, TUSHARE_API_URL)
    interface_mgr = TushareInterfaceManager(fetcher)
    engine = ConcurrentDataEngine(fetcher, interface_mgr)
    
    # 获取股票列表
    fetcher.logger.info("开始获取股票列表...")
    stock_basic_df = interface_mgr.fetch_stock_basic()
    
    if stock_basic_df.empty:
        fetcher.logger.error("❌ 无法获取股票列表")
        return
    
    # 过滤板块
    allowed_markets = ALLOWED_MARKET
    market_map = {
        "主板": ["主板", "MainBoard", "mainboard"],
        "创业板": ["创业板", "ChiNext", "chinext"],
        "科创板": ["科创板", "STAR", "star"],
        "北交所": ["北交所", "BSE", "bse"]
    }
    
    def is_market_allowed(market):
        if pd.isna(market):
            return False
        for allowed in allowed_markets:
            if allowed in market_map:
                for alias in market_map[allowed]:
                    if str(market) == alias:
                        return True
            if str(market) == allowed:
                return True
        return False
    
    stock_basic_df['market_allowed'] = stock_basic_df['market'].apply(is_market_allowed)
    stock_basic_df = stock_basic_df[stock_basic_df['market_allowed']]
    
    stocks = stock_basic_df['ts_code'].tolist()
    fetcher.logger.info(f"板块过滤后剩余{len(stocks)}只股票")
    
    # 保存股票列表
    file_ext = '.parquet' if USE_PARQUET else '.csv'
    stock_basic_path = os.path.join(DATA_DIR, f"stock_basic{file_ext}")
    fetcher.save_data(stock_basic_df, stock_basic_path, "股票列表")
    
    # 日期转换
    start_date_api = START_DATE.replace("-", "")
    end_date_api = END_DATE.replace("-", "")
    
    # 并发抓取
    success_count, failed_stocks = engine.fetch_all_stocks_parallel(stocks, start_date_api, end_date_api)
    
    # 保存失败清单
    if failed_stocks:
        failed_file = os.path.join(DATA_DIR, "failed_stocks.json")
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump(failed_stocks, f, ensure_ascii=False, indent=2)
        fetcher.logger.info(f"✅ 失败清单已保存：{failed_file}")
    
    print("="*80)
    print("✅ 数据采集完成！")
    print(f"成功：{success_count}只")
    print(f"失败：{len(failed_stocks)}只")
    print(f"存储路径：{DATA_DIR}")
    print("="*80)

if __name__ == '__main__':
    main()
