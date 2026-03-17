# ==============================================
# 【优化】插件管理器 - plugin_manager.py
# ==============================================
# 功能：统一管理所有插件的生命周期、依赖解析、热插拔
# 职责：插件加载/卸载、依赖检查、状态监控、错误恢复
# ==============================================

import os
import sys
import importlib
import logging
from typing import Dict, Any, Optional, List, Type
from pathlib import Path
from threading import RLock
import time

from .plugin_base import PluginBase, PluginState, PluginInfo

logger = logging.getLogger("quant_system")


class PluginManager:
    """
    【优化】插件管理器单例
    统一管理所有插件的完整生命周期
    
    核心功能：
    1. 插件注册：注册插件类和插件路径
    2. 插件加载：动态加载插件文件
    3. 依赖解析：自动解析和加载依赖插件
    4. 生命周期管理：统一控制插件的加载/初始化/激活/停用/卸载
    5. 状态监控：实时监控插件状态，支持健康检查
    6. 错误恢复：插件崩溃时自动隔离，不影响其他插件
    
    线程安全：
    - 使用 RLock 保证多线程安全
    - 支持并发加载多个插件
    """
    
    _instance = None
    _lock = RLock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化插件管理器"""
        if self._initialized:
            return
        self._initialized = True
        
        # 插件注册表：name -> PluginBase 实例
        self._plugins: Dict[str, PluginBase] = {}
        
        # 插件路径注册表：name -> 文件路径
        self._plugin_paths: Dict[str, str] = {}
        
        # 插件类注册表：name -> PluginBase 子类
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}
        
        # 插件锁
        self._plugin_lock = RLock()
        
        # 插件目录
        self._plugin_dir = Path(__file__).parent
        
        logger.info("✅ 插件管理器初始化完成")
    
    @classmethod
    def get_instance(cls) -> 'PluginManager':
        """获取插件管理器单例"""
        return cls()
    
    # ==================== 插件注册 ====================
    
    def register_plugin_class(self, plugin_class: Type[PluginBase], name: str = None) -> bool:
        """
        【优化】注册插件类
        :param plugin_class: 插件类（必须继承 PluginBase）
        :param name: 插件名称（可选，默认使用类名）
        :return: 是否注册成功
        """
        try:
            if not issubclass(plugin_class, PluginBase):
                logger.error(f"❌ 插件类必须继承 PluginBase 基类：{plugin_class}")
                return False
            
            plugin_name = name or plugin_class.__name__
            
            with self._plugin_lock:
                self._plugin_classes[plugin_name] = plugin_class
            
            logger.info(f"✅ 注册插件类：{plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 注册插件类失败：{e}", exc_info=True)
            return False
    
    def register_plugin_path(self, name: str, path: str) -> bool:
        """
        【优化】注册插件文件路径
        :param name: 插件名称
        :param path: 插件文件路径（.py 文件）
        :return: 是否注册成功
        """
        with self._plugin_lock:
            if not os.path.exists(path):
                logger.error(f"❌ 插件文件不存在：{path}")
                return False
            
            self._plugin_paths[name] = path
            logger.info(f"✅ 注册插件路径：{name} -> {path}")
            return True
    
    # ==================== 插件加载 ====================
    
    def load_plugin(self, plugin_path: str, auto_init: bool = True) -> Optional[PluginBase]:
        """
        【优化】动态加载插件文件
        :param plugin_path: 插件文件路径（绝对路径或相对于 plugins 目录）
        :param auto_init: 是否自动初始化（加载后立即初始化）
        :return: 插件实例（失败返回 None）
        """
        try:
            # 解析路径
            if not os.path.isabs(plugin_path):
                plugin_path = str(self._plugin_dir / plugin_path)
            
            if not os.path.exists(plugin_path):
                logger.error(f"❌ 插件文件不存在：{plugin_path}")
                return None
            
            logger.info(f"📦 开始加载插件：{plugin_path}")
            
            # 动态导入模块
            module_name = Path(plugin_path).stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            
            if spec is None or spec.loader is None:
                logger.error(f"❌ 无法加载插件模块：{plugin_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找插件类（查找继承 PluginBase 的类）
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr is not PluginBase):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.error(f"❌ 插件文件中未找到 PluginBase 子类：{plugin_path}")
                return None
            
            # 创建插件实例
            # 假设插件类有 get_plugin_info() 静态方法
            if hasattr(plugin_class, 'get_plugin_info'):
                plugin_info = plugin_class.get_plugin_info()
            else:
                plugin_info = PluginInfo(
                    name=module_name,
                    version="1.0.0",
                    plugin_type="extension"
                )
            
            plugin_instance = plugin_class(plugin_info)
            
            # 注册插件
            with self._plugin_lock:
                self._plugins[plugin_info.name] = plugin_instance
                self._plugin_paths[plugin_info.name] = plugin_path
                self._plugin_classes[plugin_info.name] = plugin_class
            
            # 加载插件
            if not plugin_instance.load():
                return None
            
            # 自动初始化
            if auto_init:
                if not plugin_instance.initialize():
                    return None
            
            logger.info(f"✅ 插件加载成功：{plugin_info.name}")
            return plugin_instance
            
        except Exception as e:
            logger.error(f"❌ 加载插件失败：{e}", exc_info=True)
            return None
    
    def load_all_plugins(self, plugin_dir: str = None, auto_init: bool = True) -> int:
        """
        【优化】批量加载插件目录下的所有插件
        :param plugin_dir: 插件目录路径（默认使用 plugins 目录）
        :param auto_init: 是否自动初始化
        :return: 成功加载的插件数量
        """
        if plugin_dir is None:
            plugin_dir = str(self._plugin_dir)
        
        success_count = 0
        
        # 扫描所有 .py 文件（排除 __init__.py 和 plugin_base.py 等）
        exclude_files = {'__init__.py', 'plugin_base.py', 'plugin_manager.py'}
        
        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and filename not in exclude_files:
                plugin_path = os.path.join(plugin_dir, filename)
                
                # 跳过子目录的 __init__.py
                if os.path.isdir(plugin_path):
                    continue
                
                try:
                    if self.load_plugin(plugin_path, auto_init):
                        success_count += 1
                except Exception as e:
                    logger.error(f"❌ 加载插件 {filename} 失败：{e}")
        
        logger.info(f"✅ 批量加载完成：成功 {success_count} 个插件")
        return success_count
    
    # ==================== 插件卸载 ====================
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        【优化】卸载指定插件
        :param plugin_name: 插件名称
        :return: 是否卸载成功
        """
        with self._plugin_lock:
            if plugin_name not in self._plugins:
                logger.error(f"❌ 插件不存在：{plugin_name}")
                return False
            
            plugin = self._plugins[plugin_name]
            
            try:
                # 执行卸载流程
                success = plugin.unload()
                
                if success:
                    # 从注册表移除
                    del self._plugins[plugin_name]
                    if plugin_name in self._plugin_paths:
                        del self._plugin_paths[plugin_name]
                    
                    logger.info(f"✅ 插件卸载成功：{plugin_name}")
                    return True
                else:
                    logger.error(f"❌ 插件卸载失败：{plugin_name}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ 卸载插件异常：{e}", exc_info=True)
                return False
    
    def unload_all_plugins(self) -> int:
        """
        【优化】卸载所有插件
        :return: 成功卸载的插件数量
        """
        success_count = 0
        
        with self._plugin_lock:
            plugin_names = list(self._plugins.keys())
        
        for name in plugin_names:
            if self.unload_plugin(name):
                success_count += 1
        
        logger.info(f"✅ 批量卸载完成：成功 {success_count} 个插件")
        return success_count
    
    # ==================== 插件激活/停用 ====================
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """
        【优化】激活指定插件
        :param plugin_name: 插件名称
        :return: 是否激活成功
        """
        with self._plugin_lock:
            if plugin_name not in self._plugins:
                logger.error(f"❌ 插件不存在：{plugin_name}")
                return False
            
            plugin = self._plugins[plugin_name]
            
            if plugin.get_state() not in [PluginState.LOADED, PluginState.INACTIVE]:
                logger.error(f"❌ 插件状态不正确，无法激活：{plugin_name} ({plugin.get_state().value})")
                return False
            
            return plugin.activate()
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        【优化】停用指定插件
        :param plugin_name: 插件名称
        :return: 是否停用成功
        """
        with self._plugin_lock:
            if plugin_name not in self._plugins:
                logger.error(f"❌ 插件不存在：{plugin_name}")
                return False
            
            plugin = self._plugins[plugin_name]
            
            if not plugin.is_active():
                logger.warning(f"⚠️  插件未激活，无需停用：{plugin_name}")
                return True
            
            return plugin.deactivate()
    
    def activate_all_plugins(self) -> int:
        """
        【优化】激活所有已加载的插件
        :return: 成功激活的插件数量
        """
        success_count = 0
        
        with self._plugin_lock:
            for name, plugin in self._plugins.items():
                if plugin.get_state() in [PluginState.LOADED, PluginState.INACTIVE]:
                    if plugin.activate():
                        success_count += 1
        
        logger.info(f"✅ 批量激活完成：成功 {success_count} 个插件")
        return success_count
    
    def deactivate_all_plugins(self) -> int:
        """
        【优化】停用所有活跃的插件
        :return: 成功停用的插件数量
        """
        success_count = 0
        
        with self._plugin_lock:
            for name, plugin in self._plugins.items():
                if plugin.is_active():
                    if plugin.deactivate():
                        success_count += 1
        
        logger.info(f"✅ 批量停用完成：成功 {success_count} 个插件")
        return success_count
    
    # ==================== 插件查询 ====================
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        【优化】获取插件实例
        :param plugin_name: 插件名称
        :return: 插件实例（不存在返回 None）
        """
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """获取所有插件实例"""
        with self._plugin_lock:
            return self._plugins.copy()
    
    def list_plugins(self) -> List[str]:
        """列出所有已加载的插件名称"""
        with self._plugin_lock:
            return list(self._plugins.keys())
    
    def get_plugin_status(self, plugin_name: str) -> Dict[str, Any]:
        """
        【优化】获取插件状态
        :param plugin_name: 插件名称
        :return: 状态字典
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.get_stats()
        else:
            return {
                'name': plugin_name,
                'state': 'not_found',
                'error_message': '插件不存在'
            }
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件的状态"""
        status = {}
        with self._plugin_lock:
            for name, plugin in self._plugins.items():
                status[name] = plugin.get_stats()
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """
        【优化】健康检查
        :return: 健康检查报告
        """
        total = len(self._plugins)
        active = sum(1 for p in self._plugins.values() if p.is_active())
        error = sum(1 for p in self._plugins.values() if p.is_error())
        
        return {
            'total_plugins': total,
            'active_plugins': active,
            'error_plugins': error,
            'healthy': error == 0,
            'timestamp': time.time(),
        }
    
    # ==================== 依赖管理 ====================
    
    def check_dependencies(self, plugin_name: str) -> bool:
        """
        【优化】检查插件依赖是否满足
        :param plugin_name: 插件名称
        :return: 依赖是否满足
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False
        
        dependencies = plugin.info.dependencies
        
        for dep in dependencies:
            if dep not in self._plugins:
                logger.error(f"❌ 插件 {plugin_name} 依赖缺失：{dep}")
                return False
            
            dep_plugin = self._plugins[dep]
            if not dep_plugin.is_active():
                logger.error(f"❌ 插件 {plugin_name} 依赖未激活：{dep}")
                return False
        
        return True
    
    def load_with_dependencies(self, plugin_path: str, auto_init: bool = True) -> Optional[PluginBase]:
        """
        【优化】加载插件并自动加载依赖
        :param plugin_path: 插件文件路径
        :param auto_init: 是否自动初始化
        :return: 插件实例
        """
        # 先加载插件（不初始化）
        plugin = self.load_plugin(plugin_path, auto_init=False)
        
        if not plugin:
            return None
        
        # 检查并加载依赖
        for dep_name in plugin.info.dependencies:
            if dep_name not in self._plugins:
                logger.info(f"📦 加载依赖插件：{dep_name}")
                # 假设依赖插件在同一目录
                dep_path = str(self._plugin_dir / f"{dep_name}.py")
                if not self.load_plugin(dep_path, auto_init=False):
                    logger.error(f"❌ 加载依赖失败：{dep_name}")
                    return None
        
        # 所有依赖加载完成，初始化插件
        if auto_init:
            if not plugin.initialize():
                return None
        
        return plugin
    
    # ==================== 配置管理 ====================
    
    def update_plugin_config(self, plugin_name: str, new_config: Dict[str, Any]) -> bool:
        """
        【优化】更新插件配置
        :param plugin_name: 插件名称
        :param new_config: 新配置字典
        :return: 是否更新成功
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            logger.error(f"❌ 插件不存在：{plugin_name}")
            return False
        
        return plugin.on_config_change(new_config)
    
    # ==================== 心跳机制 ====================
    
    def tick_all_plugins(self) -> None:
        """
        【优化】触发所有活跃插件的心跳
        定期调用（如每秒），执行周期性任务
        """
        with self._plugin_lock:
            for plugin in self._plugins.values():
                if plugin.is_active():
                    try:
                        plugin.on_tick()
                    except Exception as e:
                        logger.error(f"❌ 插件 {plugin.info.name} 心跳异常：{e}", exc_info=True)
