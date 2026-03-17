# ==============================================
# 【实时数据源】东方财富爬虫集成
# ==============================================
# 功能：提供实时资金流向、实时板块排名
# 接口：
#   - 资金流向 API
#   - 板块排名 API
#   - 主力资金 API
# ==============================================

import time
import logging
import pandas as pd
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from threading import Lock

from .base import DataSource

logger = logging.getLogger("quant_system")


class EastmoneyCrawlerSource(DataSource):
    """
    【实时数据源】东方财富爬虫
    基于东方财富 HTTP API，提供资金流向和板块排名数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化东财爬虫数据源
        :param config: 配置字典
        """
        super().__init__(config)
        
        # API 配置
        self.moneyflow_url = "http://push2.eastmoney.com/api/qt/stock/get"
        self.board_rank_url = "http://nufm.dfcfw.com/EM_Fund2099/QF_StockEm2099/js/JS.js"
        self.main_money_url = "http://push2.eastmoney.com/api/qt/clist/get"
        
        # 请求配置
        self.timeout = config.get('EASTMONEY_TIMEOUT', 10)
        self.max_retry = config.get('EASTMONEY_MAX_RETRY', 3)
        self.request_delay = config.get('EASTMONEY_REQUEST_DELAY', 0.2)
        
        # 缓存配置
        self.cache = {}
        self.cache_timeout = config.get('REALTIME_CACHE_TIMEOUT', 60)
        
        # 限流
        self._lock = Lock()
        self.last_request_time = 0
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/',
        }
    
    def connect(self) -> bool:
        """建立连接（测试）"""
        try:
            # 测试获取资金流向
            test_data = self.get_stock_moneyflow("000001")
            if test_data is not None:
                self._initialized = True
                logger.info("✅ 东方财富爬虫连接成功")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 东方财富爬虫连接失败：{e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.cache.clear()
        self._initialized = False
        logger.info("🔌 东方财富爬虫已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._initialized
    
    def _rate_limit(self):
        """请求限流"""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
            self.last_request_time = time.time()
    
    def _format_stock_code(self, stock_code: str) -> str:
        """
        格式化股票代码为东财格式
        :param stock_code: 原始代码
        :return: 东财格式（如 "0.000001" 或 "1.600000"）
        """
        code = stock_code.replace(".", "").replace("_", "").strip()
        
        # 判断市场：0=深市，1=沪市
        if code.startswith('6'):
            return f"1.{code}"
        elif code.startswith('0') or code.startswith('3'):
            return f"0.{code}"
        elif code.startswith('4') or code.startswith('8'):
            return f"0.{code}"  # 北交所
        else:
            return f"0.{code}"
    
    # ==================== 资金流向接口 ====================
    
    def get_stock_moneyflow(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【核心接口】获取单只股票资金流向
        :param stock_code: 股票代码
        :return: 资金流向字典
        """
        try:
            sina_code = self._format_stock_code(stock_code)
            
            params = {
                'secid': sina_code,
                'fields': 'f62,f184,f181,f182,f183,f185,f186,f187',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            }
            
            self._rate_limit()
            response = requests.get(self.moneyflow_url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data or not data['data']:
                return None
            
            flow_data = data['data']
            
            result = {
                'ts_code': stock_code,
                'main_net_inflow': flow_data.get('f62', 0) / 10000,  # 主力净流入（万元）
                'super_large_net_inflow': flow_data.get('f184', 0) / 10000,  # 超大单净流入
                'large_net_inflow': flow_data.get('f181', 0) / 10000,  # 大单净流入
                'medium_net_inflow': flow_data.get('f182', 0) / 10000,  # 中单净流入
                'small_net_inflow': flow_data.get('f183', 0) / 10000,  # 小单净流入
                'super_large_ratio': flow_data.get('f185', 0),  # 超大单占比
                'large_ratio': flow_data.get('f186', 0),  # 大单占比
                'medium_ratio': flow_data.get('f187', 0),  # 中单占比
                'small_ratio': 100 - flow_data.get('f185', 0) - flow_data.get('f186', 0) - flow_data.get('f187', 0),
            }
            
            return result
        except Exception as e:
            logger.warning(f"⚠️ 东财获取 {stock_code} 资金流向失败：{e}")
            return None
    
    def get_stocks_moneyflow_batch(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        【核心接口】批量获取股票资金流向
        :param stock_codes: 股票代码列表
        :return: 资金流向字典 {code: data}
        """
        results = {}
        
        for code in stock_codes:
            data = self.get_stock_moneyflow(code)
            if data:
                results[code] = data
            time.sleep(self.request_delay)
        
        return results
    
    # ==================== 板块排名接口 ====================
    
    def get_industry_board_rank(self, top_n: int = 50) -> pd.DataFrame:
        """
        【核心接口】获取行业板块排名（实时）
        :param top_n: 获取前 N 个板块
        :return: DataFrame(排名，板块名称，涨跌幅，资金流入...)
        """
        try:
            cache_key = "eastmoney_industry_rank"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 使用板块资金流向接口
            params = {
                'pn': '1',
                'pz': str(top_n),
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f62',
                'fs': 'm:90 t:3',
                'fields': 'f12,f14,f2,f3,f62,f184,f185,f186',
            }
            
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            
            self._rate_limit()
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data or 'diff' not in data['data']:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['data']['diff'])
            
            # 重命名列
            df = df.rename(columns={
                'f12': 'board_code',
                'f14': 'board_name',
                'f2': 'index_price',
                'f3': 'pct_change',
                'f62': 'main_net_inflow',
                'f184': 'super_large_net_inflow',
                'f185': 'super_large_ratio',
                'f186': 'large_ratio',
            })
            
            # 添加排名
            df['rank'] = range(1, len(df) + 1)
            
            # 单位转换（元转万元）
            for col in ['main_net_inflow', 'super_large_net_inflow']:
                if col in df.columns:
                    df[col] = df[col] / 10000
            
            self._set_cached(cache_key, df)
            
            logger.info(f"✅ 东财获取行业板块排名成功，共{len(df)}个板块")
            return df
        except Exception as e:
            logger.error(f"❌ 东财获取行业板块排名失败：{e}")
            return pd.DataFrame()
    
    def get_concept_board_rank(self, top_n: int = 50) -> pd.DataFrame:
        """
        【核心接口】获取概念板块排名（实时）
        :param top_n: 获取前 N 个板块
        :return: DataFrame
        """
        try:
            cache_key = "eastmoney_concept_rank"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            params = {
                'pn': '1',
                'pz': str(top_n),
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f62',
                'fs': 'm:90 t:2',
                'fields': 'f12,f14,f2,f3,f62',
            }
            
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            
            self._rate_limit()
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data or 'diff' not in data['data']:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['data']['diff'])
            df = df.rename(columns={
                'f12': 'board_code',
                'f14': 'board_name',
                'f2': 'index_price',
                'f3': 'pct_change',
                'f62': 'main_net_inflow',
            })
            
            df['rank'] = range(1, len(df) + 1)
            df['main_net_inflow'] = df['main_net_inflow'] / 10000
            
            self._set_cached(cache_key, df)
            
            logger.info(f"✅ 东财获取概念板块排名成功，共{len(df)}个板块")
            return df
        except Exception as e:
            logger.error(f"❌ 东财获取概念板块排名失败：{e}")
            return pd.DataFrame()
    
    # ==================== 主力资金接口 ====================
    
    def get_main_money_rank(self, top_n: int = 50) -> pd.DataFrame:
        """
        【核心接口】获取主力资金净流入排名
        :param top_n: 获取前 N 只股票
        :return: DataFrame(排名，代码，名称，主力净流入，超大单净流入...)
        """
        try:
            cache_key = "eastmoney_main_money_rank"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            params = {
                'pn': '1',
                'pz': str(top_n),
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f62',
                'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
                'fields': 'f12,f14,f2,f3,f62,f184,f185,f186',
            }
            
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            
            self._rate_limit()
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data or 'diff' not in data['data']:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['data']['diff'])
            df = df.rename(columns={
                'f12': 'ts_code',
                'f14': 'name',
                'f2': 'price',
                'f3': 'pct_change',
                'f62': 'main_net_inflow',
                'f184': 'super_large_net_inflow',
                'f185': 'super_large_ratio',
                'f186': 'large_ratio',
            })
            
            df['rank'] = range(1, len(df) + 1)
            
            # 单位转换
            for col in ['main_net_inflow', 'super_large_net_inflow']:
                if col in df.columns:
                    df[col] = df[col] / 10000
            
            self._set_cached(cache_key, df)
            
            logger.info(f"✅ 东财获取主力资金排名成功，共{len(df)}只股票")
            return df
        except Exception as e:
            logger.error(f"❌ 东财获取主力资金排名失败：{e}")
            return pd.DataFrame()
    
    # ==================== 缓存管理 ====================
    
    def _get_cached(self, key: str) -> Optional[pd.DataFrame]:
        """获取缓存数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_timeout:
                return data
            else:
                del self.cache[key]
        return None
    
    def _set_cached(self, key: str, data: pd.DataFrame):
        """设置缓存数据"""
        self.cache[key] = (data, time.time())
    
    # ==================== 实现基类抽象方法 ====================
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """获取股票基本信息（不支持）"""
        return pd.DataFrame()
    
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """交易日历（不支持）"""
        return pd.DataFrame()
    
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """日线数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """每日基本面（不支持）"""
        return pd.DataFrame()
    
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """财务指标（不支持）"""
        return pd.DataFrame()
    
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """涨跌停数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """龙虎榜（不支持）"""
        return pd.DataFrame()
    
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """机构席位（不支持）"""
        return pd.DataFrame()
    
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """新闻数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """概念板块"""
        return self.get_concept_board_rank()
    
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """资金流向（需要股票代码列表）"""
        stock_codes = kwargs.get('stock_codes', [])
        if stock_codes:
            results = self.get_stocks_moneyflow_batch(stock_codes)
            return pd.DataFrame(results).T if results else pd.DataFrame()
        return pd.DataFrame()
    
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """指数日线（不支持）"""
        return pd.DataFrame()
    
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """停牌数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """大宗交易（不支持）"""
        return pd.DataFrame()
    
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """北向资金持股（不支持）"""
        return pd.DataFrame()
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        return {
            'name': 'EastmoneyCrawlerSource',
            'connected': self.is_connected(),
            'type': 'realtime',
            'cache_size': len(self.cache),
            'timeout': self.timeout,
        }


# ==================== 便捷函数 ====================

def eastmoney_moneyflow(stock_code: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取单只股票资金流向"""
    source = EastmoneyCrawlerSource({})
    if source.connect():
        return source.get_stock_moneyflow(stock_code)
    return None


def eastmoney_industry_rank(top_n: int = 50) -> pd.DataFrame:
    """便捷函数：获取行业板块排名"""
    source = EastmoneyCrawlerSource({})
    if source.connect():
        return source.get_industry_board_rank(top_n)
    return pd.DataFrame()


def eastmoney_main_money_rank(top_n: int = 50) -> pd.DataFrame:
    """便捷函数：获取主力资金排名"""
    source = EastmoneyCrawlerSource({})
    if source.connect():
        return source.get_main_money_rank(top_n)
    return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("【东方财富爬虫测试】")
    print("=" * 60)
    
    source = EastmoneyCrawlerSource({})
    if source.connect():
        print("\n1️⃣ 测试平安银行资金流向...")
        data = source.get_stock_moneyflow("000001")
        if data:
            print(f"✅ 主力净流入：{data['main_net_inflow']:.2f}万元")
        
        print("\n2️⃣ 测试行业板块排名...")
        df = source.get_industry_board_rank(top_n=10)
        if not df.empty:
            print(f"✅ 行业板块 TOP10:")
            print(df[['rank', 'board_name', 'pct_change', 'main_net_inflow']])
        
        print("\n3️⃣ 测试主力资金排名...")
        df = source.get_main_money_rank(top_n=10)
        if not df.empty:
            print(f"✅ 主力资金 TOP10:")
            print(df[['rank', 'ts_code', 'name', 'main_net_inflow']])
        
        source.disconnect()
    else:
        print("❌ 连接失败")
