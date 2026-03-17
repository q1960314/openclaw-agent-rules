# ==============================================
# 【实时数据源管理器】多数据源切换机制
# ==============================================
# 功能：实现 Tushare → AkShare → 新浪 → 东财 的优先级切换
# 核心函数：get_realtime_data(stock_code)
# ==============================================

import logging
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

from .tushare_source import TushareSource
from .akshare_realtime import AkShareRealtimeSource
from .sina_crawler import SinaCrawlerSource
from .eastmoney_crawler import EastmoneyCrawlerSource

logger = logging.getLogger("quant_system")


class RealtimeDataManager:
    """
    【实时数据源管理器】
    实现多数据源优先级切换机制
    优先级：Tushare → AkShare → 新浪 → 东财
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化实时数据源管理器
        :param config: 配置字典
        """
        self.config = config or {}
        
        # 数据源优先级配置
        self.priority_order = self.config.get('REALTIME_PRIORITY', [
            'tushare',
            'akshare',
            'sina',
            'eastmoney'
        ])
        
        # 数据源实例缓存
        self._sources: Dict[str, Any] = {}
        
        # 数据源状态
        self._source_status: Dict[str, bool] = {}
        
        # 统计信息
        self._stats = {
            'total_requests': 0,
            'success_by_source': {},
            'fallback_count': 0,
            'last_request_time': None,
        }
        
        # 初始化数据源
        self._init_sources()
    
    def _init_sources(self):
        """初始化所有数据源"""
        logger.info("🔄 初始化实时数据源管理器...")
        
        # Tushare 数据源
        try:
            tushare_config = {
                'TUSHARE_TOKEN': self.config.get('TUSHARE_TOKEN', ''),
                'TUSHARE_API_URL': self.config.get('TUSHARE_API_URL', 'http://api.tushare.pro'),
                'FETCH_OPTIMIZATION': self.config.get('FETCH_OPTIMIZATION', {}),
            }
            self._sources['tushare'] = TushareSource(tushare_config)
            logger.info("✅ Tushare 数据源初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ Tushare 数据源初始化失败：{e}")
            self._sources['tushare'] = None
        
        # AkShare 实时数据源
        try:
            ak_config = {
                'REALTIME_CACHE_TIMEOUT': self.config.get('REALTIME_CACHE_TIMEOUT', 30),
            }
            self._sources['akshare'] = AkShareRealtimeSource(ak_config)
            logger.info("✅ AkShare 实时数据源初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ AkShare 数据源初始化失败：{e}")
            self._sources['akshare'] = None
        
        # 新浪爬虫数据源
        try:
            sina_config = {
                'SINA_TIMEOUT': self.config.get('SINA_TIMEOUT', 10),
                'SINA_MAX_RETRY': self.config.get('SINA_MAX_RETRY', 3),
                'REALTIME_CACHE_TIMEOUT': self.config.get('REALTIME_CACHE_TIMEOUT', 30),
            }
            self._sources['sina'] = SinaCrawlerSource(sina_config)
            logger.info("✅ 新浪爬虫数据源初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 新浪数据源初始化失败：{e}")
            self._sources['sina'] = None
        
        # 东财爬虫数据源
        try:
            eastmoney_config = {
                'EASTMONEY_TIMEOUT': self.config.get('EASTMONEY_TIMEOUT', 10),
                'EASTMONEY_MAX_RETRY': self.config.get('EASTMONEY_MAX_RETRY', 3),
                'REALTIME_CACHE_TIMEOUT': self.config.get('REALTIME_CACHE_TIMEOUT', 60),
            }
            self._sources['eastmoney'] = EastmoneyCrawlerSource(eastmoney_config)
            logger.info("✅ 东财爬虫数据源初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 东财数据源初始化失败：{e}")
            self._sources['eastmoney'] = None
        
        logger.info(f"✅ 实时数据源管理器初始化完成，共{len([s for s in self._sources.values() if s])}个可用数据源")
    
    def _ensure_connected(self, source_name: str) -> bool:
        """确保数据源已连接"""
        if source_name not in self._sources:
            return False
        
        source = self._sources[source_name]
        if source is None:
            return False
        
        if not source.is_connected():
            logger.info(f"🔄 正在连接 {source_name} 数据源...")
            if not source.connect():
                logger.warning(f"⚠️ {source_name} 数据源连接失败")
                self._source_status[source_name] = False
                return False
        
        self._source_status[source_name] = True
        return True
    
    def get_realtime_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【核心接口】获取单只股票实时行情（带优先级切换）
        
        :param stock_code: 股票代码（如 "000001" 或 "000001.SZ"）
        :return: 行情字典，包含 ts_code, name, price, pct_change 等字段
        
        优先级：
        1. Tushare（最稳定，但有积分限制）
        2. AkShare（免费，基于东方财富接口）
        3. 新浪爬虫（免费，HTTP 接口）
        4. 东财爬虫（免费，HTTP 接口）
        """
        self._stats['total_requests'] += 1
        self._stats['last_request_time'] = datetime.now()
        
        last_error = None
        
        for source_name in self.priority_order:
            try:
                # 确保数据源已连接
                if not self._ensure_connected(source_name):
                    logger.warning(f"⚠️ {source_name} 数据源不可用，跳过")
                    continue
                
                logger.debug(f"🔄 尝试从 {source_name} 获取 {stock_code} 实时行情...")
                
                # 根据不同数据源调用对应接口
                if source_name == 'tushare':
                    data = self._get_from_tushare(stock_code)
                elif source_name == 'akshare':
                    data = self._get_from_akshare(stock_code)
                elif source_name == 'sina':
                    data = self._get_from_sina(stock_code)
                elif source_name == 'eastmoney':
                    data = self._get_from_eastmoney(stock_code)
                else:
                    logger.warning(f"⚠️ 未知数据源：{source_name}")
                    continue
                
                if data is not None:
                    # 记录成功统计
                    self._stats['success_by_source'][source_name] = \
                        self._stats['success_by_source'].get(source_name, 0) + 1
                    
                    logger.info(f"✅ 从 {source_name} 成功获取 {stock_code} 实时行情")
                    return data
                else:
                    logger.debug(f"⚠️ {source_name} 返回数据为空")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ {source_name} 获取失败：{e}")
                continue
        
        # 所有数据源都失败
        self._stats['fallback_count'] += 1
        logger.error(f"❌ 所有数据源获取 {stock_code} 实时行情失败")
        return None
    
    def _get_from_tushare(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从 Tushare 获取实时行情"""
        source = self._sources['tushare']
        if source is None:
            return None
        
        # Tushare 使用 daily 接口获取最新数据
        try:
            df = source.fetch_daily_data(
                ts_code=stock_code,
                start_date=datetime.now().strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d")
            )
            
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'ts_code': stock_code,
                    'name': row.get('ts_code', ''),
                    'price': float(row.get('close', 0)),
                    'pct_change': float(row.get('pct_chg', 0)),
                    'change': float(row.get('close', 0)) - float(row.get('pre_close', 0)),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'pre_close': float(row.get('pre_close', 0)),
                    'volume': float(row.get('vol', 0)),
                    'amount': float(row.get('amount', 0)),
                    'source': 'tushare',
                }
            return None
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取失败：{e}")
            return None
    
    def _get_from_akshare(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从 AkShare 获取实时行情"""
        source = self._sources['akshare']
        if source is None:
            return None
        
        try:
            data = source.get_realtime_by_code(stock_code)
            if data:
                data['source'] = 'akshare'
                return data
            return None
        except Exception as e:
            logger.warning(f"⚠️ AkShare 获取失败：{e}")
            return None
    
    def _get_from_sina(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从新浪获取实时行情"""
        source = self._sources['sina']
        if source is None:
            return None
        
        try:
            data = source.get_realtime_by_code(stock_code)
            if data:
                data['source'] = 'sina'
                return data
            return None
        except Exception as e:
            logger.warning(f"⚠️ 新浪获取失败：{e}")
            return None
    
    def _get_from_eastmoney(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从东财获取实时行情（通过资金流向接口）"""
        source = self._sources['eastmoney']
        if source is None:
            return None
        
        try:
            # 东财主要用于资金流向，行情数据需要结合其他接口
            moneyflow = source.get_stock_moneyflow(stock_code)
            if moneyflow:
                moneyflow['source'] = 'eastmoney'
                return moneyflow
            return None
        except Exception as e:
            logger.warning(f"⚠️ 东财获取失败：{e}")
            return None
    
    def get_realtime_batch(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        【核心接口】批量获取股票实时行情
        :param stock_codes: 股票代码列表
        :return: 行情字典 {code: data}
        """
        results = {}
        
        for code in stock_codes:
            data = self.get_realtime_data(code)
            if data:
                results[code] = data
            time.sleep(0.1)  # 避免请求过快
        
        return results
    
    def get_industry_board_realtime(self) -> pd.DataFrame:
        """
        【核心接口】获取行业板块实时行情
        :return: DataFrame
        """
        # 优先使用 AkShare
        if self._ensure_connected('akshare'):
            df = self._sources['akshare'].get_industry_board_realtime()
            if not df.empty:
                return df
        
        # 备选东财
        if self._ensure_connected('eastmoney'):
            df = self._sources['eastmoney'].get_industry_board_rank()
            if not df.empty:
                return df
        
        return pd.DataFrame()
    
    def get_hot_rank(self) -> pd.DataFrame:
        """
        【核心接口】获取股票热榜
        :return: DataFrame
        """
        if self._ensure_connected('akshare'):
            return self._sources['akshare'].get_hot_rank()
        return pd.DataFrame()
    
    def get_moneyflow(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【核心接口】获取股票资金流向
        :param stock_code: 股票代码
        :return: 资金流向字典
        """
        # 优先使用东财
        if self._ensure_connected('eastmoney'):
            return self._sources['eastmoney'].get_stock_moneyflow(stock_code)
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_requests': self._stats['total_requests'],
            'success_by_source': self._stats['success_by_source'],
            'fallback_count': self._stats['fallback_count'],
            'last_request_time': str(self._stats['last_request_time']),
            'source_status': self._source_status,
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            'total_requests': 0,
            'success_by_source': {},
            'fallback_count': 0,
            'last_request_time': None,
        }
    
    def disconnect_all(self):
        """断开所有数据源连接"""
        for source_name, source in self._sources.items():
            if source:
                source.disconnect()
        logger.info("🔌 所有实时数据源已断开")


# ==================== 便捷函数 ====================

# 全局管理器实例（单例）
_global_manager: Optional[RealtimeDataManager] = None


def get_realtime_manager(config: Dict[str, Any] = None) -> RealtimeDataManager:
    """获取全局实时数据管理器（单例）"""
    global _global_manager
    if _global_manager is None:
        _global_manager = RealtimeDataManager(config)
    return _global_manager


def get_realtime_data(stock_code: str, config: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    【便捷函数】获取单只股票实时行情
    优先级：Tushare → AkShare → 新浪 → 东财
    """
    manager = get_realtime_manager(config)
    return manager.get_realtime_data(stock_code)


def get_realtime_batch(stock_codes: List[str], config: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
    """【便捷函数】批量获取实时行情"""
    manager = get_realtime_manager(config)
    return manager.get_realtime_batch(stock_codes)


def get_industry_board_realtime(config: Dict[str, Any] = None) -> pd.DataFrame:
    """【便捷函数】获取行业板块实时行情"""
    manager = get_realtime_manager(config)
    return manager.get_industry_board_realtime()


def get_hot_rank(config: Dict[str, Any] = None) -> pd.DataFrame:
    """【便捷函数】获取股票热榜"""
    manager = get_realtime_manager(config)
    return manager.get_hot_rank()


def get_moneyflow(stock_code: str, config: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """【便捷函数】获取股票资金流向"""
    manager = get_realtime_manager(config)
    return manager.get_moneyflow(stock_code)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("【实时数据源管理器测试】")
    print("=" * 60)
    
    # 配置
    config = {
        'TUSHARE_TOKEN': '',  # 填入你的 Tushare Token
        'REALTIME_CACHE_TIMEOUT': 30,
    }
    
    manager = RealtimeDataManager(config)
    
    print("\n1️⃣ 测试实时行情（优先级切换）...")
    test_codes = ["000001", "600519", "300750"]
    
    for code in test_codes:
        print(f"\n  测试 {code}...")
        data = manager.get_realtime_data(code)
        if data:
            print(f"  ✅ {code}: {data.get('name', 'N/A')} 价格={data.get('price', 'N/A')} "
                  f"涨跌幅={data.get('pct_change', 'N/A')}% 数据源={data.get('source', 'N/A')}")
        else:
            print(f"  ❌ {code}: 获取失败")
    
    print("\n2️⃣ 测试行业板块...")
    board_df = manager.get_industry_board_realtime()
    if not board_df.empty:
        print(f"✅ 行业板块：{len(board_df)}个")
        print(board_df[['board_name', 'pct_change']].head())
    
    print("\n3️⃣ 测试统计信息...")
    stats = manager.get_stats()
    print(f"总请求数：{stats['total_requests']}")
    print(f"各数据源成功次数：{stats['success_by_source']}")
    print(f"降级次数：{stats['fallback_count']}")
    
    manager.disconnect_all()
    print("\n✅ 测试完成")
