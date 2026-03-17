# ==============================================
# 【优化】数据源插件接口 - data_source_plugin.py
# ==============================================
# 功能：定义数据源插件的抽象接口，规范数据源实现
# 职责：数据接入、连接管理、数据抓取、限流控制
# ==============================================

from abc import abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd
import logging
from datetime import datetime

from .plugin_base import PluginBase, PluginInfo, PluginState

logger = logging.getLogger("quant_system")


class DataSourcePlugin(PluginBase):
    """
    【优化】数据源插件基类
    所有数据源插件必须继承此类并实现核心方法
    
    设计原则：
    1. 接口统一：所有数据源提供一致的方法签名
    2. 插件化：支持动态加载/卸载数据源
    3. 可扩展：新增数据源只需继承实现，不影响现有代码
    4. 连接池：支持连接复用和并发控制
    
    数据源生命周期：
    加载 → 初始化 → 连接 → [数据抓取] → 断开 → 卸载
    
    注意：
    - 此接口与 modules/data_sources/base.py 中的 DataSource 基类兼容
    - 新增数据源插件可以选择继承此类或 DataSource
    - 插件化的 DataSourcePlugin 提供更完整的生命周期管理
    """
    
    def __init__(self, plugin_info: PluginInfo):
        """
        初始化数据源插件
        :param plugin_info: 插件元信息
        """
        super().__init__(plugin_info)
        
        # 数据源配置
        self.source_config: Dict[str, Any] = {}
        
        # 连接状态
        self._connected = False
        self._connection = None
        
        # 限流配置
        self.max_requests_per_second = 10
        self.max_requests_per_minute = 100
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_bytes = 0
    
    # ==================== 抽象方法（必须实现） ====================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        【抽象方法】建立数据源连接
        :return: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        【抽象方法】断开数据源连接
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        【抽象方法】检查连接状态
        :return: 是否已连接
        """
        pass
    
    @abstractmethod
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取股票基本信息
        :param kwargs: 参数（如 exchange, fields 等）
        :return: 股票列表 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取交易日历
        :param kwargs: 参数（如 start_date, end_date, exchange 等）
        :return: 交易日历 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取日线数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 日线数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取每日基本面数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 每日基本面数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取财务指标数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 财务指标数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取涨跌停数据
        :param kwargs: 参数（如 trade_date 等）
        :return: 涨跌停数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取龙虎榜数据
        :param kwargs: 参数（如 trade_date 等）
        :return: 龙虎榜数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取机构席位数据
        :param kwargs: 参数（如 trade_date 等）
        :return: 机构席位数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取新闻资讯数据
        :param kwargs: 参数（如 src, start_date, end_date 等）
        :return: 新闻数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取概念板块数据
        :param kwargs: 参数（如 ts_code 等）
        :return: 概念板块数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取资金流向数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 资金流向数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取指数日线数据
        :param kwargs: 参数（如 index_code, start_date, end_date 等）
        :return: 指数日线数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取停牌数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 停牌数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取大宗交易数据
        :param kwargs: 参数（如 trade_date 等）
        :return: 大宗交易数据 DataFrame
        """
        pass
    
    @abstractmethod
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """
        【抽象方法】获取北向资金持股数据
        :param kwargs: 参数（如 ts_code, start_date, end_date 等）
        :return: 北向资金持股数据 DataFrame
        """
        pass
    
    # ==================== 虚方法（可选重写） ====================
    
    def validate_config(self) -> bool:
        """
        【虚方法】校验数据源配置
        子类可重写此方法实现自定义配置校验
        :return: 配置是否合法
        """
        logger.debug(f"🔍 数据源 {self.info.name} 配置校验")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        【虚方法】获取数据源状态信息
        子类可重写此方法返回自定义状态
        :return: 状态字典
        """
        return {
            'name': self.info.name,
            'connected': self._connected,
            'type': self.__class__.__name__,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
        }
    
    def on_connect(self) -> bool:
        """
        【虚方法】连接成功回调
        在连接建立后调用
        默认实现返回 True，子类可重写
        
        :return: 是否成功
        """
        logger.debug(f"🔌 数据源 {self.info.name} 连接成功")
        return True
    
    def on_disconnect(self) -> bool:
        """
        【虚方法】断开连接回调
        在连接断开后调用
        默认实现返回 True，子类可重写
        
        :return: 是否成功
        """
        logger.debug(f"🔌 数据源 {self.info.name} 断开连接")
        return True
    
    def rate_limit(self) -> None:
        """
        【虚方法】限流控制
        在每次请求前调用，用于控制请求频率
        默认实现为空，子类可重写添加限流逻辑
        """
        pass
    
    def on_request(self, api_name: str, params: Dict[str, Any]) -> None:
        """
        【虚方法】请求前回调
        在发送请求前调用
        默认实现记录日志，子类可重写
        
        :param api_name: API 名称
        :param params: 请求参数
        """
        logger.debug(f"📡 数据源请求：{api_name}, 参数：{params}")
    
    def on_response(self, api_name: str, data: pd.DataFrame, success: bool) -> None:
        """
        【虚方法】响应后回调
        在收到响应后调用
        默认实现更新统计，子类可重写
        
        :param api_name: API 名称
        :param data: 响应数据
        :param success: 是否成功
        """
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            if data is not None:
                self.total_bytes += data.memory_usage(deep=True).sum()
        else:
            self.failed_requests += 1
    
    # ==================== 生命周期方法重写 ====================
    
    def on_load(self) -> bool:
        """
        【优化】数据源加载流程
        加载数据源专属配置
        """
        try:
            logger.info(f"📦 加载数据源插件：{self.info.name}")
            return True
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 数据源 {self.info.name} 加载异常：{e}", exc_info=True)
            return False
    
    def on_init(self) -> bool:
        """
        【优化】数据源初始化流程
        校验配置，准备连接
        """
        try:
            # 校验配置
            if not self.validate_config():
                self._error_message = "配置校验失败"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 数据源 {self.info.name} 配置校验失败")
                return False
            
            self.set_state(PluginState.INACTIVE)
            logger.info(f"✅ 数据源 {self.info.name} 初始化完成")
            return True
            
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 数据源 {self.info.name} 初始化异常：{e}", exc_info=True)
            return False
    
    def on_activate(self) -> bool:
        """
        【优化】数据源激活流程
        建立连接
        """
        try:
            # 调用基类激活
            if not super().on_activate():
                return False
            
            # 建立连接
            if not self.connect():
                self._error_message = "连接失败"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 数据源 {self.info.name} 连接失败")
                return False
            
            # 连接成功回调
            if not self.on_connect():
                self._error_message = "on_connect() 返回 False"
                self.set_state(PluginState.ERROR)
                return False
            
            self._connected = True
            logger.info(f"🟢 数据源 {self.info.name} 已激活并连接")
            return True
            
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 数据源 {self.info.name} 激活异常：{e}", exc_info=True)
            return False
    
    def on_deactivate(self) -> bool:
        """
        【优化】数据源停用流程
        断开连接
        """
        try:
            # 断开连接
            if self._connected:
                self.disconnect()
                self._connected = False
                
                # 断开连接回调
                if not self.on_disconnect():
                    self._error_message = "on_disconnect() 返回 False"
                    return False
            
            # 调用基类停用
            return super().on_deactivate()
            
        except Exception as e:
            self._error_message = str(e)
            logger.error(f"❌ 数据源 {self.info.name} 停用异常：{e}", exc_info=True)
            return False
    
    # ==================== 工具方法 ====================
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """
        设置数据源配置
        :param config: 配置字典
        """
        self.source_config = config
        logger.info(f"⚙️  数据源 {self.info.name} 配置已更新")
    
    def get_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self.source_config.copy()
    
    def set_rate_limit(self, rps: int, rpm: int) -> None:
        """
        设置限流参数
        :param rps: 每秒最大请求数
        :param rpm: 每分钟最大请求数
        """
        self.max_requests_per_second = rps
        self.max_requests_per_minute = rpm
        logger.info(f"⚙️  数据源 {self.info.name} 限流：{rps} RPS, {rpm} RPM")
    
    def get_connection(self):
        """获取底层连接对象"""
        return self._connection
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据源统计信息
        :return: 统计信息字典
        """
        base_stats = super().get_stats()
        
        base_stats.update({
            'connected': self._connected,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'total_bytes': self.total_bytes,
            'success_rate': self.successful_requests / max(1, self.total_requests),
            'max_rps': self.max_requests_per_second,
            'max_rpm': self.max_requests_per_minute,
        })
        
        return base_stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_bytes = 0
        logger.info(f"✅ 数据源 {self.info.name} 统计已重置")
    
    def __enter__(self):
        """上下文管理器：进入时连接"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出时断开连接"""
        self.disconnect()
    
    def __repr__(self) -> str:
        return f"DataSourcePlugin(name={self.info.name}, connected={self._connected})"


# ==============================================
# 【优化】与 modules/data_sources/base.py 的兼容性说明
# ==============================================
#
# 此 DataSourcePlugin 类与 modules/data_sources/base.py 中的 DataSource 基类：
#
# 1. 功能对比：
#    - DataSource: 轻量级数据源接口，适合简单场景
#    - DataSourcePlugin: 完整的插件化数据源，支持生命周期管理
#
# 2. 选择建议：
#    - 新增数据源：推荐继承 DataSourcePlugin（功能更完整）
#    - 已有数据源：可继续使用 DataSource（如 TushareSource）
#    - 需要热插拔：必须使用 DataSourcePlugin
#
# 3. 兼容性：
#    - 两者方法签名完全一致，可以互换使用
#    - DataSourcePlugin 额外提供插件生命周期管理
#    - 可以通过适配器模式互相转换
#
# ==============================================
