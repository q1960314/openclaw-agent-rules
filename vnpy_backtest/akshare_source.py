# -*- coding: utf-8 -*-
"""
Akshare数据源 v1.0
免费数据源，用于补充Tushare无权限的接口

主要功能：
1. 分钟线数据（Tushare需要高积分权限）
2. 实时行情
3. 板块数据

Akshare文档：https://akshare.akfamily.xyz/
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("✅ Akshare已加载")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("⚠️ Akshare未安装，部分功能不可用。安装: pip install akshare")


class AkshareDataSource:
    """
    Akshare数据源
    
    免费接口：
    1. 分钟线数据 - stock_zh_a_hist_min_em
    2. 实时行情 - stock_zh_a_spot_em
    3. 板块数据 - stock_board_concept_name_em
    4. 龙虎榜 - stock_lhb_detail_em
    """
    
    def __init__(self):
        if not AKSHARE_AVAILABLE:
            raise ImportError("Akshare未安装，请运行: pip install akshare")
        
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 缓存5分钟
    
    # ==================== 分钟线数据 ====================
    
    def get_minute_data(self, 
                        ts_code: str, 
                        period: str = '1',
                        start_date: str = None,
                        end_date: str = None) -> pd.DataFrame:
        """
        获取分钟线数据
        
        Args:
            ts_code: 股票代码 (如 '000001.SZ' 或 '000001')
            period: 周期 ('1', '5', '15', '30', '60')
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            分钟线DataFrame
        """
        # 处理股票代码
        symbol = ts_code.split('.')[0] if '.' in ts_code else ts_code
        
        cache_key = f"min_{symbol}_{period}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 使用东方财富分钟线接口
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period=period,
                adjust=''  # 不复权
            )
            
            if df is not None and not df.empty:
                # 标准化列名
                df = self._normalize_minute_columns(df)
                df['ts_code'] = ts_code
                
                # 缓存
                self._cache[cache_key] = df
                self._cache_time[cache_key] = datetime.now()
                
                logger.info(f"获取分钟线: {ts_code}, {len(df)}条")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取分钟线失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def _normalize_minute_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化分钟线列名"""
        column_map = {
            '时间': 'datetime',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
        }
        
        df = df.rename(columns=column_map)
        
        # 转换日期时间
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['trade_date'] = df['datetime'].dt.strftime('%Y%m%d')
            df['trade_time'] = df['datetime'].dt.strftime('%H:%M')
        
        return df
    
    # ==================== 实时行情 ====================
    
    def get_realtime_quote(self, ts_code: str = None) -> pd.DataFrame:
        """
        获取实时行情
        
        Args:
            ts_code: 股票代码，为空则获取全部
            
        Returns:
            实时行情DataFrame
        """
        cache_key = "realtime_quotes"
        if self._is_cache_valid(cache_key):
            df = self._cache[cache_key]
            if ts_code:
                symbol = ts_code.split('.')[0] if '.' in ts_code else ts_code
                df = df[df['代码'] == symbol]
            return df
        
        try:
            df = ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                # 缓存
                self._cache[cache_key] = df
                self._cache_time[cache_key] = datetime.now()
                
                # 筛选
                if ts_code:
                    symbol = ts_code.split('.')[0] if '.' in ts_code else ts_code
                    df = df[df['代码'] == symbol]
                
                logger.info(f"获取实时行情: {len(df)}只股票")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_price(self, ts_code: str) -> Optional[float]:
        """
        获取实时价格
        
        Args:
            ts_code: 股票代码
            
        Returns:
            当前价格
        """
        df = self.get_realtime_quote(ts_code)
        if not df.empty and '最新价' in df.columns:
            return float(df.iloc[0]['最新价'])
        return None
    
    # ==================== 板块数据 ====================
    
    def get_concept_sectors(self) -> pd.DataFrame:
        """
        获取概念板块列表
        
        Returns:
            板块DataFrame
        """
        cache_key = "concept_sectors"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            df = ak.stock_board_concept_name_em()
            
            if df is not None and not df.empty:
                self._cache[cache_key] = df
                self._cache_time[cache_key] = datetime.now()
                logger.info(f"获取概念板块: {len(df)}个")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取概念板块失败: {e}")
            return pd.DataFrame()
    
    def get_sector_stocks(self, sector_name: str) -> pd.DataFrame:
        """
        获取板块成分股
        
        Args:
            sector_name: 板块名称
            
        Returns:
            成分股DataFrame
        """
        cache_key = f"sector_{sector_name}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            df = ak.stock_board_concept_cons_em(symbol=sector_name)
            
            if df is not None and not df.empty:
                self._cache[cache_key] = df
                self._cache_time[cache_key] = datetime.now()
                logger.info(f"获取板块成分: {sector_name}, {len(df)}只")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取板块成分失败 {sector_name}: {e}")
            return pd.DataFrame()
    
    # ==================== 龙虎榜数据 ====================
    
    def get_longhubao(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            龙虎榜DataFrame
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        cache_key = f"lhb_{trade_date}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            df = ak.stock_lhb_detail_em(start_date=trade_date, end_date=trade_date)
            
            if df is not None and not df.empty:
                self._cache[cache_key] = df
                self._cache_time[cache_key] = datetime.now()
                logger.info(f"获取龙虎榜: {trade_date}, {len(df)}条")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取龙虎榜失败 {trade_date}: {e}")
            return pd.DataFrame()
    
    # ==================== 涨跌停数据 ====================
    
    def get_limit_up_list(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取涨停股票列表
        
        Args:
            trade_date: 交易日期
            
        Returns:
            涨停股DataFrame
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = ak.stock_zt_pool_em(date=trade_date)
            
            if df is not None and not df.empty:
                logger.info(f"获取涨停股: {trade_date}, {len(df)}只")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取涨停股失败 {trade_date}: {e}")
            return pd.DataFrame()
    
    def get_limit_down_list(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取跌停股票列表
        
        Args:
            trade_date: 交易日期
            
        Returns:
            跌停股DataFrame
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = ak.stock_zt_pool_dtgc_em(date=trade_date)
            
            if df is not None and not df.empty:
                logger.info(f"获取跌停股: {trade_date}, {len(df)}只")
            
            return df if df is not None else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取跌停股失败 {trade_date}: {e}")
            return pd.DataFrame()
    
    # ==================== 缓存管理 ====================
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache:
            return False
        if key not in self._cache_time:
            return False
        
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_time.clear()
        logger.info("缓存已清空")
    
    # ==================== 辅助方法 ====================
    
    def get_stock_info(self, ts_code: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            ts_code: 股票代码
            
        Returns:
            股票信息字典
        """
        symbol = ts_code.split('.')[0] if '.' in ts_code else ts_code
        
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                info = dict(zip(df['item'], df['value']))
                return info
        except Exception as e:
            logger.warning(f"获取股票信息失败 {ts_code}: {e}")
        
        return {}


# ==================== 统一数据源接口 ====================

class HybridDataSource:
    """
    混合数据源
    
    优先使用Tushare（积分权限内）
    无权限时自动切换到Akshare
    """
    
    def __init__(self, tushare_pro=None, tushare_token: str = None):
        """
        初始化
        
        Args:
            tushare_pro: Tushare pro对象
            tushare_token: Tushare token
        """
        self.tushare_pro = tushare_pro
        self.tushare_token = tushare_token
        self.akshare = AkshareDataSource() if AKSHARE_AVAILABLE else None
        
        # 无权限接口列表
        self._no_permission_interfaces = set()
    
    def get_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线数据"""
        # 日线数据Tushare有权限
        if self.tushare_pro:
            try:
                df = self.tushare_pro.daily(
                    ts_code=ts_code,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', '')
                )
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"Tushare日线失败: {e}")
        
        return pd.DataFrame()
    
    def get_minute_data(self, 
                        ts_code: str, 
                        period: str = '1',
                        start_date: str = None,
                        end_date: str = None) -> pd.DataFrame:
        """
        获取分钟线数据
        
        Tushare需要高积分权限，优先使用Akshare
        """
        if self.akshare:
            return self.akshare.get_minute_data(ts_code, period, start_date, end_date)
        return pd.DataFrame()
    
    def get_realtime_quote(self, ts_code: str = None) -> pd.DataFrame:
        """获取实时行情"""
        if self.akshare:
            return self.akshare.get_realtime_quote(ts_code)
        return pd.DataFrame()
    
    def get_limit_up_list(self, trade_date: str = None) -> pd.DataFrame:
        """获取涨停股列表"""
        # Tushare优先
        if self.tushare_pro and 'limit_list' not in self._no_permission_interfaces:
            try:
                df = self.tushare_pro.limit_list_d(trade_date=trade_date)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                if '权限' in str(e) or 'permission' in str(e).lower():
                    self._no_permission_interfaces.add('limit_list')
                logger.warning(f"Tushare涨停股失败: {e}")
        
        # Akshare备用
        if self.akshare:
            return self.akshare.get_limit_up_list(trade_date)
        
        return pd.DataFrame()


# ==================== 测试 ====================

if __name__ == "__main__":
    if AKSHARE_AVAILABLE:
        source = AkshareDataSource()
        
        # 测试实时行情
        print("测试实时行情...")
        df = source.get_realtime_quote("000001")
        if not df.empty:
            print(df.head())
        
        # 测试分钟线
        print("\n测试分钟线...")
        df = source.get_minute_data("000001", period='5')
        if not df.empty:
            print(df.head())
        
        # 测试涨停股
        print("\n测试涨停股...")
        df = source.get_limit_up_list()
        if not df.empty:
            print(df.head())
    else:
        print("Akshare未安装")