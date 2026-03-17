# ==============================================
# 【优化】插件基类 - plugin_base.py
# ==============================================
# 功能：定义所有插件的抽象基类，规范插件生命周期和接口
# 职责：插件状态管理、生命周期回调、元数据管理、错误处理框架
# ==============================================

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

logger = logging.getLogger("quant_system")


class PluginState(Enum):
    """
    【优化】插件状态枚举
    定义插件的生命周期状态
    """
    UNLOADED = "unloaded"          # 未加载
    LOADING = "loading"            # 加载中
    LOADED = "loaded"              # 已加载
    INITIALIZING = "initializing"  # 初始化中
    ACTIVE = "active"              # 活跃状态（可正常工作）
    INACTIVE = "inactive"          # 非活跃状态（已加载但未激活）
    ERROR = "error"                # 错误状态
    UNLOADING = "unloading"        # 卸载中
    STOPPED = "stopped"            # 已停止


class PluginInfo:
    """
    【优化】插件元信息类
    存储插件的基本信息和配置
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        plugin_type: str = "base",
        dependencies: List[str] = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化插件信息
        :param name: 插件名称（唯一标识）
        :param version: 插件版本号
        :param author: 插件作者
        :param description: 插件描述
        :param plugin_type: 插件类型（strategy/data_source/extension）
        :param dependencies: 依赖的插件列表
        :param config: 插件配置字典
        """
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.plugin_type = plugin_type
        self.dependencies = dependencies or []
        self.config = config or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'plugin_type': self.plugin_type,
            'dependencies': self.dependencies,
            'config': self.config,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"PluginInfo(name={self.name}, version={self.version}, type={self.plugin_type})"


class PluginBase(ABC):
    """
    【优化】插件抽象基类
    所有插件必须继承此类并实现核心方法
    
    设计原则：
    1. 生命周期管理：统一插件的加载/初始化/激活/停用/卸载流程
    2. 状态追踪：实时追踪插件状态，便于调试和监控
    3. 错误处理：统一的错误处理框架，避免插件崩溃影响系统
    4. 可扩展：支持插件热插拔，不影响其他插件
    
    生命周期流程：
    UNLOADED → LOADING → LOADED → INITIALIZING → ACTIVE
                                         ↓
                                    INACTIVE ← (可切换)
                                         ↓
                                    UNLOADING → STOPPED
    """
    
    def __init__(self, plugin_info: PluginInfo):
        """
        初始化插件基类
        :param plugin_info: 插件元信息
        """
        self.info = plugin_info
        self._state = PluginState.UNLOADED
        self._error_message: Optional[str] = None
        self._load_time: Optional[float] = None
        self._init_time: Optional[float] = None
        self._last_active_time: Optional[float] = None
        
        logger.info(f"🔌 创建插件：{self.info.name} v{self.info.version}")
    
    # ==================== 抽象方法（必须实现） ====================
    
    @abstractmethod
    def on_init(self) -> bool:
        """
        【抽象方法】插件初始化回调
        在插件加载完成后调用，用于初始化内部状态
        
        :return: 是否初始化成功
        """
        pass
    
    @abstractmethod
    def on_activate(self) -> bool:
        """
        【抽象方法】插件激活回调
        在插件被激活时调用，开始正常工作
        
        :return: 是否激活成功
        """
        pass
    
    @abstractmethod
    def on_deactivate(self) -> bool:
        """
        【抽象方法】插件停用回调
        在插件被停用时调用，暂停工作但保持加载状态
        
        :return: 是否停用成功
        """
        pass
    
    # ==================== 虚方法（可选重写） ====================
    
    def on_load(self) -> bool:
        """
        【虚方法】插件加载回调
        在插件被加载到系统时调用，用于资源预加载
        默认实现返回 True，子类可重写
        
        :return: 是否加载成功
        """
        logger.debug(f"📦 插件 {self.info.name} 加载")
        return True
    
    def on_unload(self) -> bool:
        """
        【虚方法】插件卸载回调
        在插件被卸载时调用，清理所有资源
        默认实现返回 True，子类可重写
        
        :return: 是否卸载成功
        """
        logger.debug(f"📦 插件 {self.info.name} 卸载")
        return True
    
    # ==================== 生命周期管理方法（虚方法，可选重写） ====================
    
    def on_start(self) -> bool:
        """
        【虚方法】插件启动回调
        在插件激活后调用，用于启动后台任务等
        默认实现返回 True，子类可重写
        
        :return: 是否启动成功
        """
        logger.debug(f"🟢 插件 {self.info.name} 启动")
        return True
    
    def on_stop(self) -> bool:
        """
        【虚方法】插件停止回调
        在插件停用时调用，用于停止后台任务等
        默认实现返回 True，子类可重写
        
        :return: 是否停止成功
        """
        logger.debug(f"🔴 插件 {self.info.name} 停止")
        return True
    
    def on_tick(self) -> None:
        """
        【虚方法】插件心跳回调
        定期调用（如每秒），用于执行周期性任务
        默认实现为空，子类可重写
        """
        pass
    
    def on_config_change(self, new_config: Dict[str, Any]) -> bool:
        """
        【虚方法】配置变更回调
        当插件配置被修改时调用
        默认实现更新配置，子类可重写添加自定义逻辑
        
        :param new_config: 新配置字典
        :return: 是否接受配置变更
        """
        self.info.config.update(new_config)
        self.info.updated_at = datetime.now()
        logger.info(f"⚙️  插件 {self.info.name} 配置已更新")
        return True
    
    # ==================== 状态管理方法 ====================
    
    def get_state(self) -> PluginState:
        """获取当前插件状态"""
        return self._state
    
    def set_state(self, state: PluginState) -> None:
        """
        设置插件状态
        :param state: 目标状态
        """
        old_state = self._state
        self._state = state
        logger.debug(f"🔄 插件 {self.info.name} 状态变更：{old_state.value} → {state.value}")
    
    def is_active(self) -> bool:
        """检查插件是否处于活跃状态"""
        return self._state == PluginState.ACTIVE
    
    def is_error(self) -> bool:
        """检查插件是否处于错误状态"""
        return self._state == PluginState.ERROR
    
    def get_error_message(self) -> Optional[str]:
        """获取错误信息"""
        return self._error_message
    
    def clear_error(self) -> None:
        """清除错误状态"""
        self._error_message = None
        if self._state == PluginState.ERROR:
            self.set_state(PluginState.INACTIVE)
    
    # ==================== 生命周期执行方法 ====================
    
    def load(self) -> bool:
        """
        【优化】执行插件加载流程
        :return: 是否加载成功
        """
        try:
            self.set_state(PluginState.LOADING)
            start_time = time.time()
            
            # 调用加载回调
            success = self.on_load()
            
            if success:
                self._load_time = time.time() - start_time
                self.set_state(PluginState.LOADED)
                logger.info(f"✅ 插件 {self.info.name} 加载成功，耗时 {self._load_time:.3f}s")
                return True
            else:
                self._error_message = "on_load() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 插件 {self.info.name} 加载失败：{self._error_message}")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 插件 {self.info.name} 加载异常：{e}", exc_info=True)
            return False
    
    def initialize(self) -> bool:
        """
        【优化】执行插件初始化流程
        :return: 是否初始化成功
        """
        try:
            self.set_state(PluginState.INITIALIZING)
            start_time = time.time()
            
            # 调用初始化回调
            success = self.on_init()
            
            if success:
                self._init_time = time.time() - start_time
                self.set_state(PluginState.INACTIVE)
                logger.info(f"✅ 插件 {self.info.name} 初始化成功，耗时 {self._init_time:.3f}s")
                return True
            else:
                self._error_message = "on_init() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 插件 {self.info.name} 初始化失败：{self._error_message}")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 插件 {self.info.name} 初始化异常：{e}", exc_info=True)
            return False
    
    def activate(self) -> bool:
        """
        【优化】执行插件激活流程
        :return: 是否激活成功
        """
        try:
            # 调用激活回调
            success = self.on_activate()
            
            if success:
                # 调用启动回调
                success = self.on_start()
                
                if success:
                    self.set_state(PluginState.ACTIVE)
                    self._last_active_time = time.time()
                    logger.info(f"🟢 插件 {self.info.name} 已激活")
                    return True
                else:
                    self._error_message = "on_start() 返回 False"
                    self.set_state(PluginState.ERROR)
                    logger.error(f"❌ 插件 {self.info.name} 启动失败：{self._error_message}")
                    return False
            else:
                self._error_message = "on_activate() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 插件 {self.info.name} 激活失败：{self._error_message}")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 插件 {self.info.name} 激活异常：{e}", exc_info=True)
            return False
    
    def deactivate(self) -> bool:
        """
        【优化】执行插件停用流程
        :return: 是否停用成功
        """
        try:
            # 调用停止回调
            success = self.on_stop()
            
            if success:
                # 调用停用回调
                success = self.on_deactivate()
                
                if success:
                    self.set_state(PluginState.INACTIVE)
                    logger.info(f"🔴 插件 {self.info.name} 已停用")
                    return True
                else:
                    self._error_message = "on_deactivate() 返回 False"
                    logger.error(f"❌ 插件 {self.info.name} 停用失败：{self._error_message}")
                    return False
            else:
                self._error_message = "on_stop() 返回 False"
                logger.error(f"❌ 插件 {self.info.name} 停止失败：{self._error_message}")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            logger.error(f"❌ 插件 {self.info.name} 停用异常：{e}", exc_info=True)
            return False
    
    def unload(self) -> bool:
        """
        【优化】执行插件卸载流程
        :return: 是否卸载成功
        """
        try:
            self.set_state(PluginState.UNLOADING)
            
            # 如果当前是活跃状态，先停用
            if self.is_active():
                self.deactivate()
            
            # 调用卸载回调
            success = self.on_unload()
            
            if success:
                self.set_state(PluginState.STOPPED)
                logger.info(f"✅ 插件 {self.info.name} 已卸载")
                return True
            else:
                self._error_message = "on_unload() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 插件 {self.info.name} 卸载失败：{self._error_message}")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 插件 {self.info.name} 卸载异常：{e}", exc_info=True)
            return False
    
    # ==================== 工具方法 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取插件统计信息
        :return: 统计信息字典
        """
        return {
            'name': self.info.name,
            'version': self.info.version,
            'type': self.info.plugin_type,
            'state': self._state.value,
            'load_time': self._load_time,
            'init_time': self._init_time,
            'last_active_time': self._last_active_time,
            'error_message': self._error_message,
        }
    
    def __repr__(self) -> str:
        return f"PluginBase(name={self.info.name}, state={self._state.value})"
