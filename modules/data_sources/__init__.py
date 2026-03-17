# ==============================================
# 【优化】数据源模块 - data_sources
# ==============================================
# 功能：统一数据源接口管理，支持多数据源插件化接入
# 职责：数据源抽象、插件注册、工厂模式创建
# ==============================================

from .base import DataSource
from .tushare_source import TushareSource
from .factory import DataSourceFactory

# 【新增】实时数据源
from .akshare_realtime import AkShareRealtimeSource
from .sina_crawler import SinaCrawlerSource
from .eastmoney_crawler import EastmoneyCrawlerSource
from .realtime_manager import (
    RealtimeDataManager,
    get_realtime_data,
    get_realtime_batch,
    get_industry_board_realtime,
    get_hot_rank,
    get_moneyflow,
)

# 预留接口（未来实现）
# from .wind_source import WindSource
# from .joinquant_source import JoinQuantSource

__all__ = [
    'DataSource',
    'TushareSource',
    'DataSourceFactory',
    # 实时数据源
    'AkShareRealtimeSource',
    'SinaCrawlerSource',
    'EastmoneyCrawlerSource',
    'RealtimeDataManager',
    'get_realtime_data',
    'get_realtime_batch',
    'get_industry_board_realtime',
    'get_hot_rank',
    'get_moneyflow',
    # 'WindSource',      # 【预留】Wind 数据源接口
    # 'JoinQuantSource', # 【预留】JoinQuant 数据源接口
]
