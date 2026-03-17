# ==============================================
# 【优化】数据源工厂类 - factory.py
# ==============================================
# 功能：统一管理数据源的创建、注册、切换
# 职责：工厂模式、数据源注册表、配置管理
# ==============================================

import logging
from typing import Dict, Any, Optional, Type
from .base import DataSource
from .tushare_source import TushareSource

# 【预留】导入其他数据源（待实现）
# from .wind_source import WindSource
# from .joinquant_source import JoinQuantSource

logger = logging.getLogger("quant_system")


class DataSourceFactory:
    """
    【优化】数据源工厂类
    使用工厂模式统一管理所有数据源的创建和配置
    
    核心功能：
    1. 数据源注册：注册支持的数据源类型
    2. 数据源创建：根据配置创建对应数据源实例
    3. 数据源切换：支持运行时切换数据源
    4. 配置管理：管理不同数据源的配置参数
    """
    
    # 【优化】数据源注册表
    _data_source_registry: Dict[str, Type[DataSource]] = {
        'tushare': TushareSource,
        # 'wind': WindSource,      # 【预留】Wind 数据源
        # 'joinquant': JoinQuantSource,  # 【预留】JoinQuant 数据源
    }
    
    # 【优化】数据源实例缓存
    _instances: Dict[str, DataSource] = {}
    
    @classmethod
    def register(cls, name: str, data_source_class: Type[DataSource]):
        """
        【优化】注册新的数据源类型
        :param name: 数据源名称（如 'wind', 'joinquant'）
        :param data_source_class: 数据源类（必须继承 DataSource）
        """
        if not issubclass(data_source_class, DataSource):
            raise TypeError(f"数据源类必须继承 DataSource 基类")
        
        cls._data_source_registry[name.lower()] = data_source_class
        logger.info(f"✅ 注册数据源：{name}")
    
    @classmethod
    def create(cls, source_type: str, config: Dict[str, Any]) -> DataSource:
        """
        【优化】创建数据源实例
        :param source_type: 数据源类型（'tushare', 'wind', 'joinquant' 等）
        :param config: 数据源配置字典
        :return: 数据源实例
        """
        source_type = source_type.lower()
        
        # 检查是否已创建实例（单例模式）
        if source_type in cls._instances:
            logger.info(f"🔄 复用已存在的 {source_type} 数据源实例")
            return cls._instances[source_type]
        
        # 检查是否已注册
        if source_type not in cls._data_source_registry:
            available = list(cls._data_source_registry.keys())
            raise ValueError(
                f"❌ 未知的数据源类型：{source_type}\n"
                f"已注册的数据源：{available}"
            )
        
        # 创建新实例
        data_source_class = cls._data_source_registry[source_type]
        instance = data_source_class(config)
        
        # 校验配置
        if not instance.validate_config():
            raise ValueError(f"❌ {source_type} 数据源配置校验失败")
        
        # 缓存实例
        cls._instances[source_type] = instance
        
        logger.info(f"✅ 创建 {source_type} 数据源成功")
        return instance
    
    @classmethod
    def get(cls, source_type: str) -> Optional[DataSource]:
        """
        【优化】获取已创建的数据源实例
        :param source_type: 数据源类型
        :return: 数据源实例（不存在则返回 None）
        """
        return cls._instances.get(source_type.lower())
    
    @classmethod
    def switch(cls, source_type: str, config: Dict[str, Any]) -> DataSource:
        """
        【优化】切换数据源（断开旧连接，创建新连接）
        :param source_type: 目标数据源类型
        :param config: 新数据源配置
        :return: 新数据源实例
        """
        source_type = source_type.lower()
        
        # 断开所有现有连接
        cls.disconnect_all()
        
        # 创建新数据源
        return cls.create(source_type, config)
    
    @classmethod
    def disconnect(cls, source_type: str):
        """
        【优化】断开指定数据源连接
        :param source_type: 数据源类型
        """
        source_type = source_type.lower()
        if source_type in cls._instances:
            cls._instances[source_type].disconnect()
            del cls._instances[source_type]
            logger.info(f"🔌 断开 {source_type} 数据源连接")
    
    @classmethod
    def disconnect_all(cls):
        """【优化】断开所有数据源连接"""
        for source_type, instance in list(cls._instances.items()):
            instance.disconnect()
        
        cls._instances.clear()
        logger.info("🔌 断开所有数据源连接")
    
    @classmethod
    def list_available(cls) -> list:
        """
        【优化】列出所有已注册的数据源类型
        :return: 数据源类型列表
        """
        return list(cls._data_source_registry.keys())
    
    @classmethod
    def list_active(cls) -> list:
        """
        【优化】列出所有已激活（已创建）的数据源
        :return: 已激活的数据源类型列表
        """
        return list(cls._instances.keys())
    
    @classmethod
    def get_status(cls, source_type: str) -> Dict[str, Any]:
        """
        【优化】获取指定数据源的状态
        :param source_type: 数据源类型
        :return: 状态字典
        """
        instance = cls.get(source_type)
        if instance:
            return instance.get_status()
        else:
            return {
                'name': source_type,
                'connected': False,
                'status': 'not_created',
                'message': '数据源实例未创建'
            }
    
    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        """
        【优化】获取所有数据源的状态
        :return: 所有数据源的状态字典
        """
        status = {}
        
        # 已激活的数据源
        for source_type in cls._instances:
            status[source_type] = cls.get_status(source_type)
        
        # 未激活的已注册数据源
        for source_type in cls._data_source_registry:
            if source_type not in status:
                status[source_type] = {
                    'name': source_type,
                    'connected': False,
                    'status': 'registered',
                    'message': '数据源已注册但未创建'
                }
        
        return status


# ==============================================
# 【优化】数据源配置管理
# ==============================================

class DataSourceConfig:
    """
    【优化】数据源配置管理器
    统一管理所有数据源的配置参数
    """
    
    # 【优化】默认配置（从 config_manager 继承）
    DEFAULT_CONFIG = {
        'tushare': {
            'TUSHARE_TOKEN': '',  # 从 config_manager.TUSHARE_TOKEN 获取
            'TUSHARE_API_URL': '',  # 从 config_manager.TUSHARE_API_URL 获取
            'FETCH_OPTIMIZATION': {},  # 从 config_manager.FETCH_OPTIMIZATION 获取
        },
        # 【预留】Wind 配置
        'wind': {
            'WIND_CODE': '',
            'WIND_PASSWORD': '',
            'WIND_SERVER': '127.0.0.1',
            'WIND_PORT': 9900,
        },
        # 【预留】JoinQuant 配置
        'joinquant': {
            'JQ_USERNAME': '',
            'JQ_PASSWORD': '',
        }
    }
    
    @classmethod
    def get_config(cls, source_type: str, global_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        【优化】获取指定数据源的配置
        :param source_type: 数据源类型
        :param global_config: 全局配置字典（来自 config_manager）
        :return: 数据源配置字典
        """
        source_type = source_type.lower()
        
        if source_type == 'tushare':
            return {
                'TUSHARE_TOKEN': global_config.get('TUSHARE_TOKEN', ''),
                'TUSHARE_API_URL': global_config.get('TUSHARE_API_URL', ''),
                'FETCH_OPTIMIZATION': global_config.get('FETCH_OPTIMIZATION', {}),
            }
        
        elif source_type == 'wind':
            return {
                'WIND_CODE': global_config.get('WIND_CODE', ''),
                'WIND_PASSWORD': global_config.get('WIND_PASSWORD', ''),
                'WIND_SERVER': global_config.get('WIND_SERVER', '127.0.0.1'),
                'WIND_PORT': global_config.get('WIND_PORT', 9900),
            }
        
        elif source_type == 'joinquant':
            return {
                'JQ_USERNAME': global_config.get('JQ_USERNAME', ''),
                'JQ_PASSWORD': global_config.get('JQ_PASSWORD', ''),
            }
        
        else:
            logger.warning(f"⚠️ 未知数据源类型：{source_type}，返回空配置")
            return {}
    
    @classmethod
    def validate_all(cls, global_config: Dict[str, Any]) -> Dict[str, bool]:
        """
        【优化】校验所有数据源配置
        :param global_config: 全局配置字典
        :return: 校验结果字典（数据源类型 -> 是否合法）
        """
        results = {}
        
        for source_type in cls._get_available_types():
            config = cls.get_config(source_type, global_config)
            
            # 创建临时实例进行校验
            try:
                instance = DataSourceFactory.create(source_type, config)
                results[source_type] = True
                # 立即断开（不缓存）
                DataSourceFactory.disconnect(source_type)
            except Exception as e:
                logger.warning(f"⚠️ {source_type} 数据源配置校验失败：{e}")
                results[source_type] = False
        
        return results
    
    @classmethod
    def _get_available_types(cls) -> list:
        """获取所有已注册的数据源类型"""
        return list(DataSourceFactory._data_source_registry.keys())
