# ==============================================
# 【优化】量化系统模块包 - __init__.py
# ==============================================
# 功能：模块包初始化，统一导出接口
# ==============================================

"""
【优化】量化系统模块化架构

模块说明：
- config_manager: 配置管理模块
- data_fetcher: 数据抓取模块
- storage_manager: 存储管理模块
- data_validator: 数据校验模块
- strategy_core: 策略核心模块
- backtest_engine: 回测引擎模块

使用示例：
    from modules import config_manager
    from modules import data_fetcher
    from modules import storage_manager
    from modules import data_validator
    from modules import strategy_core
    from modules import backtest_engine
"""

__version__ = "1.0.0"
__author__ = "quant-system"

# 导入所有模块（延迟导入，避免循环引用）
from . import config_manager
from . import data_fetcher
from . import storage_manager
from . import data_validator
from . import strategy_core
from . import backtest_engine

# 统一导出主要类
from .config_manager import config_manager, ConfigManager
from .data_fetcher import DataFetcher
from .storage_manager import StorageManager
from .data_validator import DataValidator
from .strategy_core import StrategyCore
from .backtest_engine import BacktestEngine

__all__ = [
    # 配置管理
    'config_manager',
    'ConfigManager',
    
    # 数据抓取
    'DataFetcher',
    
    # 存储管理
    'StorageManager',
    
    # 数据校验
    'DataValidator',
    
    # 策略核心
    'StrategyCore',
    
    # 回测引擎
    'BacktestEngine',
    
    # 模块引用
    'config_manager',
    'data_fetcher',
    'storage_manager',
    'data_validator',
    'strategy_core',
    'backtest_engine',
]
