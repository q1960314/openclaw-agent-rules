# ==============================================
# 【优化】数据源基类 - base.py
# ==============================================
# 功能：定义数据源抽象接口，所有数据源插件必须继承实现
# 职责：统一接口规范、生命周期管理、错误处理框架
# ==============================================

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd
import logging

logger = logging.getLogger("quant_system")


class DataSource(ABC):
    """
    【优化】数据源抽象基类
    所有数据源插件必须继承此类并实现所有抽象方法
    
    设计原则：
    1. 接口统一：所有数据源提供一致的方法签名
    2. 插件化：支持动态加载/卸载数据源
    3. 可扩展：新增数据源只需继承实现，不影响现有代码
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据源
        :param config: 数据源配置字典
        """
        self.config = config
        self.name = self.__class__.__name__
        self._initialized = False
        self._connection = None
        
        logger.info(f"🔌 初始化数据源：{self.name}")
    
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
    
    def validate_config(self) -> bool:
        """
        【虚方法】校验数据源配置
        子类可重写此方法实现自定义配置校验
        :return: 配置是否合法
        """
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        【虚方法】获取数据源状态信息
        子类可重写此方法返回自定义状态
        :return: 状态字典
        """
        return {
            'name': self.name,
            'connected': self.is_connected(),
            'type': self.__class__.__name__
        }
    
    def __enter__(self):
        """上下文管理器：进入时连接"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出时断开连接"""
        self.disconnect()
