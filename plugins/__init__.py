# ==============================================
# 【优化】插件系统 - plugins/__init__.py
# ==============================================
# 功能：插件系统包初始化，统一导出接口
# 职责：插件基类、插件管理器、策略/数据源接口导出
# ==============================================

"""
【优化】量化系统插件化架构

插件系统说明：
- 所有插件必须继承 PluginBase 基类
- 支持动态加载/卸载插件
- 支持插件热插拔
- 插件间松耦合，通过管理器通信

插件分类：
1. 策略插件 (Strategy Plugin): 实现交易策略逻辑
2. 数据源插件 (Data Source Plugin): 实现数据接入
3. 扩展插件 (Extension Plugin): 其他功能扩展

使用示例：
    from plugins import PluginManager, PluginBase
    from plugins.strategy_plugin import StrategyPlugin
    from plugins.data_source_plugin import DataSourcePlugin
    
    # 获取插件管理器单例
    manager = PluginManager.get_instance()
    
    # 加载插件
    manager.load_plugin('plugins/strategies/my_strategy.py')
    
    # 获取策略插件
    strategy = manager.get_plugin('my_strategy')
"""

__version__ = "1.0.0"
__author__ = "quant-system"

# 导入核心组件
from .plugin_base import PluginBase, PluginState, PluginInfo
from .plugin_manager import PluginManager
from .strategy_plugin import StrategyPlugin
from .data_source_plugin import DataSourcePlugin

# 统一导出
__all__ = [
    # 核心类
    'PluginBase',
    'PluginState',
    'PluginInfo',
    'PluginManager',
    
    # 插件接口
    'StrategyPlugin',
    'DataSourcePlugin',
]
