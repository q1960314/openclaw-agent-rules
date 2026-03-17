# ==============================================
# 【实时数据源】AkShare 实时数据接口集成
# ==============================================
# 功能：提供 A 股实时行情、板块实时数据、热榜数据
# 接口：
#   - ak.stock_zh_a_spot_em() - 实时行情
#   - ak.stock_board_industry_name_em() - 板块实时
#   - ak.stock_hot_rank_em() - 热榜实时
# ==============================================

import time
import logging
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import DataSource

logger = logging.getLogger("quant_system")


class AkShareRealtimeSource(DataSource):
    """
    【实时数据源】AkShare 实时行情数据源
    基于东方财富接口，提供 A 股实时行情数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 AkShare 实时数据源
        :param config: 配置字典
        """
        super().__init__(config)
        
        self.cache = {}
        self.cache_timeout = config.get('REALTIME_CACHE_TIMEOUT', 30)  # 缓存超时时间（秒）
        self._ak = None
    
    @property
    def ak(self):
        """延迟加载 AkShare"""
        if self._ak is None:
            self._init_akshare()
        return self._ak
    
    def _init_akshare(self):
        """初始化 AkShare"""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("✅ AkShare 库加载成功")
        except ImportError as e:
            logger.error(f"❌ AkShare 库导入失败：{e}")
            self._ak = None
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            if self._ak is None:
                self._init_akshare()
            
            if self._ak is not None:
                # 测试连接：获取实时行情
                test_df = self._ak.stock_zh_a_spot_em()
                if test_df is not None and not test_df.empty:
                    self._initialized = True
                    self._connection = self._ak
                    logger.info("✅ AkShare 实时数据源连接成功")
                    return True
            
            logger.error("❌ AkShare 实时数据源连接失败")
            return False
        except Exception as e:
            logger.error(f"❌ AkShare 连接异常：{e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.cache.clear()
        self._connection = None
        self._initialized = False
        logger.info("🔌 AkShare 实时数据源已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._initialized and self._ak is not None
    
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
    
    # ==================== 实时行情接口 ====================
    
    def get_realtime_spot(self) -> pd.DataFrame:
        """
        【核心接口】获取 A 股实时行情（全市场）
        :return: DataFrame(代码，名称，最新价，涨跌幅，成交量，成交额...)
        """
        try:
            cache_key = "realtime_spot"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                logger.debug("📦 使用缓存的实时行情数据")
                return cached_data
            
            logger.info("🔄 正在获取 A 股实时行情...")
            df = self.ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                # 标准化列名
                df = self._standardize_spot_columns(df)
                self._set_cached(cache_key, df)
                logger.info(f"✅ AkShare 获取实时行情成功，共{len(df)}只股票")
                return df
            else:
                logger.warning("⚠️ AkShare 实时行情数据为空")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ AkShare 获取实时行情失败：{e}")
            return pd.DataFrame()
    
    def get_realtime_by_code(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【核心接口】获取单只股票实时行情
        :param stock_code: 股票代码（如 "000001" 或 "000001.SZ"）
        :return: 行情字典
        """
        try:
            # 从全市场数据中筛选
            spot_df = self.get_realtime_spot()
            if spot_df.empty:
                return None
            
            # 标准化代码格式
            code = stock_code.replace(".", "").replace("_", "")
            
            # 匹配股票代码
            if '代码' in spot_df.columns:
                match = spot_df[spot_df['代码'].str.contains(code, na=False)]
            elif '代码' in spot_df.columns:
                match = spot_df[spot_df['代码'].str.contains(code, na=False)]
            else:
                match = pd.DataFrame()
            
            if not match.empty:
                row = match.iloc[0]
                return row.to_dict()
            else:
                logger.warning(f"⚠️ 未找到股票 {stock_code} 的实时行情")
                return None
        except Exception as e:
            logger.error(f"❌ AkShare 获取单只股票行情失败：{e}")
            return None
    
    def _standardize_spot_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化实时行情列名"""
        # 东方财富接口列名映射
        column_map = {
            '序号': 'index',
            '代码': 'ts_code',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '最高': 'high',
            '最低': 'low',
            '今开': 'open',
            '昨收': 'pre_close',
            '量比': 'volume_ratio',
            '换手率': 'turnover_ratio',
            '市盈率 - 动态': 'pe_ttm',
            '市净率': 'pb',
            '总市值': 'total_mv',
            '流通市值': 'circ_mv',
            '涨速': 'speed',
            '55 日均价': 'ma55',
            '60 日均价': 'ma60',
            '年初至今涨跌幅': 'ytd_pct',
        }
        
        # 重命名列
        for old_name, new_name in column_map.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 转换数值类型
        numeric_cols = ['price', 'pct_change', 'change', 'volume', 'amount', 
                       'amplitude', 'high', 'low', 'open', 'pre_close',
                       'volume_ratio', 'turnover_ratio', 'pe_ttm', 'pb',
                       'total_mv', 'circ_mv', 'speed', 'ma55', 'ma60', 'ytd_pct']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    # ==================== 板块实时接口 ====================
    
    def get_industry_board_realtime(self) -> pd.DataFrame:
        """
        【核心接口】获取行业板块实时行情
        :return: DataFrame(板块名称，板块代码，最新价，涨跌幅，领涨股...)
        """
        try:
            cache_key = "industry_board_realtime"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            logger.info("🔄 正在获取行业板块实时行情...")
            df = self.ak.stock_board_industry_name_em()
            
            if df is not None and not df.empty:
                # 标准化列名
                df = self._standardize_board_columns(df)
                self._set_cached(cache_key, df)
                logger.info(f"✅ AkShare 获取行业板块实时行情成功，共{len(df)}个板块")
                return df
            else:
                logger.warning("⚠️ AkShare 行业板块数据为空")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ AkShare 获取行业板块数据失败：{e}")
            return pd.DataFrame()
    
    def get_concept_board_realtime(self) -> pd.DataFrame:
        """
        【核心接口】获取概念板块实时行情
        :return: DataFrame(板块名称，板块代码，最新价，涨跌幅，领涨股...)
        """
        try:
            cache_key = "concept_board_realtime"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            logger.info("🔄 正在获取概念板块实时行情...")
            df = self.ak.stock_board_concept_name_em()
            
            if df is not None and not df.empty:
                df = self._standardize_board_columns(df)
                self._set_cached(cache_key, df)
                logger.info(f"✅ AkShare 获取概念板块实时行情成功，共{len(df)}个板块")
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ AkShare 获取概念板块数据失败：{e}")
            return pd.DataFrame()
    
    def _standardize_board_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化板块列名"""
        column_map = {
            '序号': 'index',
            '板块代码': 'board_code',
            '板块名称': 'board_name',
            '板块指数': 'index_price',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '成交量': 'volume',
            '成交额': 'amount',
            '领涨股票': 'lead_stock',
            '领涨股票 - 涨跌幅': 'lead_stock_pct',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
        }
        
        for old_name, new_name in column_map.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        return df
    
    # ==================== 热榜接口 ====================
    
    def get_hot_rank(self) -> pd.DataFrame:
        """
        【核心接口】获取股票热榜（人气排名）
        :return: DataFrame(排名，代码，名称，最新价，涨跌幅，换手率...)
        """
        try:
            cache_key = "hot_rank"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            logger.info("🔄 正在获取股票热榜...")
            df = self.ak.stock_hot_rank_em()
            
            if df is not None and not df.empty:
                logger.info(f"✅ AkShare 获取股票热榜成功，共{len(df)}只股票")
                self._set_cached(cache_key, df)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ AkShare 获取股票热榜失败：{e}")
            return pd.DataFrame()
    
    # ==================== 实现基类抽象方法 ====================
    # 以下为兼容基类接口的适配方法，实时数据源主要提供实时接口
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """获取股票基本信息（复用实时行情）"""
        return self.get_realtime_spot()
    
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """交易日历（暂不支持）"""
        logger.warning("⚠️ AkShare 实时数据源不支持交易日历接口")
        return pd.DataFrame()
    
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """日线数据（暂不支持）"""
        logger.warning("⚠️ AkShare 实时数据源不支持日线数据接口")
        return pd.DataFrame()
    
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """每日基本面（复用实时行情）"""
        return self.get_realtime_spot()
    
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """财务指标（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """涨跌停数据（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """龙虎榜（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """机构席位（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """新闻数据（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """概念板块"""
        return self.get_concept_board_realtime()
    
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """资金流向（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """指数日线（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """停牌数据（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """大宗交易（暂不支持）"""
        return pd.DataFrame()
    
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """北向资金持股（暂不支持）"""
        return pd.DataFrame()
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        return {
            'name': 'AkShareRealtimeSource',
            'connected': self.is_connected(),
            'type': 'realtime',
            'cache_size': len(self.cache),
            'cache_timeout': self.cache_timeout,
        }


# ==================== 便捷函数 ====================

def ak_realtime_spot() -> pd.DataFrame:
    """便捷函数：获取 A 股实时行情"""
    source = AkShareRealtimeSource({})
    if source.connect():
        return source.get_realtime_spot()
    return pd.DataFrame()


def ak_realtime_by_code(stock_code: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取单只股票实时行情"""
    source = AkShareRealtimeSource({})
    if source.connect():
        return source.get_realtime_by_code(stock_code)
    return None


def ak_industry_board() -> pd.DataFrame:
    """便捷函数：获取行业板块实时行情"""
    source = AkShareRealtimeSource({})
    if source.connect():
        return source.get_industry_board_realtime()
    return pd.DataFrame()


def ak_hot_rank() -> pd.DataFrame:
    """便捷函数：获取股票热榜"""
    source = AkShareRealtimeSource({})
    if source.connect():
        return source.get_hot_rank()
    return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("【AkShare 实时数据源测试】")
    print("=" * 60)
    
    source = AkShareRealtimeSource({})
    if source.connect():
        print("\n1️⃣ 测试实时行情...")
        spot_df = source.get_realtime_spot()
        if not spot_df.empty:
            print(f"✅ 实时行情：{len(spot_df)}只股票")
            print(spot_df[['ts_code', 'name', 'price', 'pct_change']].head())
        
        print("\n2️⃣ 测试行业板块...")
        board_df = source.get_industry_board_realtime()
        if not board_df.empty:
            print(f"✅ 行业板块：{len(board_df)}个板块")
            print(board_df[['board_name', 'index_price', 'pct_change']].head())
        
        print("\n3️⃣ 测试热榜...")
        hot_df = source.get_hot_rank()
        if not hot_df.empty:
            print(f"✅ 热榜：{len(hot_df)}只股票")
            print(hot_df.head())
        
        source.disconnect()
    else:
        print("❌ 连接失败")
