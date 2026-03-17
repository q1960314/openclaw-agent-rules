# 【优化】量化系统插件化架构说明文档

## 一、插件系统概述

### 1.1 设计目标

本次插件化改造旨在实现：
- **模块化**：将策略、数据源等核心功能模块化，支持独立开发和维护
- **热插拔**：支持动态加载/卸载插件，无需重启系统
- **可扩展**：新增功能只需开发新插件，不影响现有代码
- **松耦合**：插件间通过管理器通信，降低依赖关系
- **易测试**：插件可独立测试，便于单元测试和集成测试

### 1.2 插件分类

系统支持三类插件：

| 插件类型 | 基类 | 用途 | 示例 |
|---------|------|------|------|
| **策略插件** | `StrategyPlugin` | 实现交易策略逻辑 | 打板策略、缩量潜伏策略、板块轮动策略 |
| **数据源插件** | `DataSourcePlugin` | 实现数据接入 | Tushare、Wind、JoinQuant |
| **扩展插件** | `PluginBase` | 其他功能扩展 | 消息推送、数据可视化、报告生成 |

---

## 二、目录结构

```
plugins/
├── __init__.py                    # 包初始化，统一导出接口
├── plugin_base.py                 # 插件基类（所有插件必须继承）
├── plugin_manager.py              # 插件管理器（单例，管理所有插件）
├── strategy_plugin.py             # 策略插件接口（继承 PluginBase）
├── data_source_plugin.py          # 数据源插件接口（继承 PluginBase）
│
├── limit_up_strategy.py           # 【示例】打板策略插件
├── tushare_source_plugin.py       # 【示例】Tushare 数据源插件
│
└── README.md                      # 本文档
```

---

## 三、核心组件详解

### 3.1 插件基类 `PluginBase`

**位置：** `plugins/plugin_base.py`

**核心功能：**
- 定义插件生命周期（加载→初始化→激活→停用→卸载）
- 管理插件状态（UNLOADED/LOADING/LOADED/ACTIVE/ERROR 等）
- 提供错误处理框架
- 记录插件统计信息

**生命周期流程：**
```
UNLOADED → LOADING → LOADED → INITIALIZING → ACTIVE
                                        ↓
                                   INACTIVE ← (可切换)
                                        ↓
                                   UNLOADING → STOPPED
```

**必须实现的抽象方法：**
```python
@abstractmethod
def on_load(self) -> bool:
    """插件加载回调"""
    pass

@abstractmethod
def on_init(self) -> bool:
    """插件初始化回调"""
    pass

@abstractmethod
def on_activate(self) -> bool:
    """插件激活回调"""
    pass

@abstractmethod
def on_deactivate(self) -> bool:
    """插件停用回调"""
    pass

@abstractmethod
def on_unload(self) -> bool:
    """插件卸载回调"""
    pass
```

**可选重写的虚方法：**
```python
def on_start(self) -> bool:
    """插件启动回调（激活后调用）"""
    return True

def on_stop(self) -> bool:
    """插件停止回调（停用前调用）"""
    return True

def on_tick(self) -> None:
    """心跳回调（定期调用）"""
    pass

def on_config_change(self, new_config: Dict[str, Any]) -> bool:
    """配置变更回调"""
    return True
```

---

### 3.2 插件管理器 `PluginManager`

**位置：** `plugins/plugin_manager.py`

**核心功能：**
- 插件注册（类注册、路径注册）
- 插件加载（动态导入、实例化）
- 依赖解析（自动加载依赖插件）
- 生命周期管理（统一控制所有插件）
- 状态监控（健康检查、统计信息）
- 错误恢复（插件崩溃时自动隔离）

**单例使用：**
```python
from plugins import PluginManager

# 获取管理器单例
manager = PluginManager.get_instance()

# 或使用快捷方式
manager = PluginManager()  # 自动返回单例
```

**常用方法：**

```python
# 1. 加载单个插件
plugin = manager.load_plugin('plugins/limit_up_strategy.py')

# 2. 批量加载所有插件
count = manager.load_all_plugins()

# 3. 激活插件
manager.activate_plugin('limit_up_strategy')

# 4. 获取插件实例
plugin = manager.get_plugin('limit_up_strategy')

# 5. 获取所有插件状态
status = manager.get_all_status()

# 6. 健康检查
health = manager.health_check()

# 7. 卸载插件
manager.unload_plugin('limit_up_strategy')
```

---

### 3.3 策略插件接口 `StrategyPlugin`

**位置：** `plugins/strategy_plugin.py`

**继承关系：** `PluginBase` → `StrategyPlugin`

**核心功能：**
- 定义策略信号生成接口
- 管理持仓状态
- 支持回测/实盘模式切换
- 提供风险控制框架

**必须实现的抽象方法：**
```python
@abstractmethod
def generate_signals(
    self,
    market_data: Dict[str, pd.DataFrame],
    current_positions: Dict[str, Position]
) -> List[Signal]:
    """生成交易信号"""
    pass

@abstractmethod
def on_bar(self, data: Dict[str, Any]) -> None:
    """K 线回调"""
    pass

@abstractmethod
def on_order_filled(self, order: Dict[str, Any]) -> None:
    """订单成交回调"""
    pass
```

**可选重写的方法：**
```python
def on_init_strategy(self) -> bool:
    """策略初始化"""
    return True

def on_start_strategy(self) -> bool:
    """策略启动"""
    return True

def on_stop_strategy(self) -> bool:
    """策略停止"""
    return True

def risk_check(self, signal: Signal) -> bool:
    """风险检查"""
    return True

def get_strategy_params(self) -> Dict[str, Any]:
    """获取策略参数"""
    return {}

def set_strategy_params(self, params: Dict[str, Any]) -> bool:
    """设置策略参数"""
    return True
```

---

### 3.4 数据源插件接口 `DataSourcePlugin`

**位置：** `plugins/data_source_plugin.py`

**继承关系：** `PluginBase` → `DataSourcePlugin`

**核心功能：**
- 定义统一的数据源接口
- 管理数据源连接
- 提供限流控制框架
- 记录请求统计

**必须实现的抽象方法：**
```python
@abstractmethod
def connect(self) -> bool:
    """建立连接"""
    pass

@abstractmethod
def disconnect(self) -> None:
    """断开连接"""
    pass

@abstractmethod
def is_connected(self) -> bool:
    """检查连接状态"""
    pass

# 数据抓取方法（18 个）
@abstractmethod
def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
    pass

@abstractmethod
def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
    pass

# ... 其他 16 个方法
```

**可选重写的方法：**
```python
def validate_config(self) -> bool:
    """校验配置"""
    return True

def rate_limit(self) -> None:
    """限流控制"""
    pass

def on_request(self, api_name: str, params: Dict[str, Any]) -> None:
    """请求前回调"""
    pass

def on_response(self, api_name: str, data: pd.DataFrame, success: bool) -> None:
    """响应后回调"""
    pass
```

---

## 四、开发指南

### 4.1 开发策略插件

**步骤 1：创建插件文件**
```python
# plugins/my_strategy.py
from plugins.plugin_base import PluginInfo
from plugins.strategy_plugin import StrategyPlugin, Signal, SignalType

class MyStrategyPlugin(StrategyPlugin):
    """我的策略插件"""
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        return PluginInfo(
            name="my_strategy",
            version="1.0.0",
            author="your_name",
            description="我的策略描述",
            plugin_type="strategy",
            config={
                "param1": 100,
                "param2": 0.05,
            }
        )
    
    def on_init_strategy(self) -> bool:
        # 初始化策略
        return True
    
    def generate_signals(self, market_data, current_positions) -> List[Signal]:
        # 生成信号逻辑
        signals = []
        # ... 你的策略逻辑
        return signals
    
    def on_bar(self, data: Dict[str, Any]) -> None:
        # K 线回调
        pass
    
    def on_order_filled(self, order: Dict[str, Any]) -> None:
        # 订单成交回调
        pass
```

**步骤 2：测试插件**
```python
from plugins import PluginManager

manager = PluginManager.get_instance()

# 加载插件
plugin = manager.load_plugin('plugins/my_strategy.py')

# 激活插件
manager.activate_plugin('my_strategy')

# 获取插件
strategy = manager.get_plugin('my_strategy')

# 测试信号生成
market_data = {...}  # 准备测试数据
signals = strategy.generate_signals(market_data, {})
print(f"生成 {len(signals)} 个信号")
```

---

### 4.2 开发数据源插件

**步骤 1：创建插件文件**
```python
# plugins/my_data_source.py
from plugins.plugin_base import PluginInfo
from plugins.data_source_plugin import DataSourcePlugin

class MyDataSourcePlugin(DataSourcePlugin):
    """我的数据源插件"""
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        return PluginInfo(
            name="my_data_source",
            version="1.0.0",
            author="your_name",
            description="我的数据源描述",
            plugin_type="data_source",
            config={
                "api_key": "",
                "api_url": "https://api.example.com",
            }
        )
    
    def connect(self) -> bool:
        # 建立连接
        self._connected = True
        return True
    
    def disconnect(self) -> None:
        # 断开连接
        self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        # 获取股票列表
        # ... 你的数据源 API 调用
        return df
    
    # ... 实现其他 17 个数据抓取方法
```

---

### 4.3 插件依赖管理

**声明依赖：**
```python
@staticmethod
def get_plugin_info() -> PluginInfo:
    return PluginInfo(
        name="dependent_plugin",
        dependencies=["base_plugin1", "base_plugin2"],  # 依赖列表
        # ...
    )
```

**加载带依赖的插件：**
```python
# 自动加载依赖
plugin = manager.load_with_dependencies('plugins/dependent_plugin.py')
```

---

## 五、最佳实践

### 5.1 插件命名规范

- 文件名：小写 + 下划线（如 `my_strategy.py`）
- 类名：大写开头 + Plugin 后缀（如 `MyStrategyPlugin`）
- 插件名称：小写 + 下划线（如 `my_strategy`）

### 5.2 错误处理

```python
def generate_signals(self, market_data, current_positions) -> List[Signal]:
    try:
        # 你的逻辑
        signals = []
        return signals
    except Exception as e:
        logger.error(f"❌ 策略生成信号失败：{e}", exc_info=True)
        return []  # 返回空列表，避免崩溃
```

### 5.3 日志记录

```python
logger.info(f"✅ 插件 {self.info.name} 初始化完成")
logger.debug(f"🔍 处理数据：{len(data)} 条")
logger.warning(f"⚠️  数据不足，跳过")
logger.error(f"❌ 发生错误：{e}")
```

### 5.4 性能优化

- 避免在 `on_tick()` 中执行耗时操作
- 使用缓存减少重复计算
- 大数据量时分批处理
- 异步处理非关键任务

---

## 六、与现有架构的兼容性

### 6.1 与 modules/data_sources/base.py 的关系

**DataSourcePlugin** 与 **DataSource** 基类：

| 特性 | DataSource | DataSourcePlugin |
|------|------------|------------------|
| 定位 | 轻量级数据源接口 | 完整的插件化数据源 |
| 生命周期 | 简单连接管理 | 完整的插件生命周期 |
| 热插拔 | ❌ 不支持 | ✅ 支持 |
| 依赖管理 | ❌ 无 | ✅ 支持 |
| 状态监控 | ❌ 基础 | ✅ 完整统计 |

**选择建议：**
- 新增数据源：推荐继承 `DataSourcePlugin`（功能更完整）
- 已有数据源：可继续使用 `DataSource`（如 `TushareSource`）
- 需要热插拔：必须使用 `DataSourcePlugin`

### 6.2 与 modules/strategy_core.py 的关系

**StrategyPlugin** 与 **StrategyCore**：

- `StrategyCore`：原有策略核心逻辑
- `StrategyPlugin`：插件化的策略接口

**迁移路径：**
1. 保留 `StrategyCore` 作为策略逻辑实现
2. 创建 `StrategyPlugin` 包装器，调用 `StrategyCore`
3. 逐步将策略逻辑迁移到插件架构

---

## 七、示例代码

### 7.1 完整使用示例

```python
from plugins import PluginManager, SignalType

# 1. 获取管理器
manager = PluginManager.get_instance()

# 2. 加载所有插件
count = manager.load_all_plugins()
print(f"加载了 {count} 个插件")

# 3. 激活所有插件
manager.activate_all_plugins()

# 4. 获取策略插件
strategy = manager.get_plugin('limit_up_strategy')

# 5. 生成信号
market_data = {
    'daily': daily_df,
    'top_list': top_list_df,
    'stock_basic': stock_basic_df,
}
signals = strategy.generate_signals(market_data, {})

# 6. 处理信号
for signal in signals:
    if signal.signal_type == SignalType.BUY:
        print(f"买入信号：{signal.ts_code} @ {signal.price}")
    elif signal.signal_type == SignalType.SELL:
        print(f"卖出信号：{signal.ts_code} @ {signal.price}")

# 7. 健康检查
health = manager.health_check()
print(f"健康状态：{'健康' if health['healthy'] else '异常'}")

# 8. 停用所有插件
manager.deactivate_all_plugins()

# 9. 卸载所有插件
manager.unload_all_plugins()
```

### 7.2 心跳机制示例

```python
import time

# 启动心跳循环
while True:
    try:
        # 触发所有插件心跳
        manager.tick_all_plugins()
        time.sleep(1)  # 每秒一次
    except KeyboardInterrupt:
        break

# 清理
manager.deactivate_all_plugins()
manager.unload_all_plugins()
```

---

## 八、故障排查

### 8.1 插件加载失败

**问题：** `load_plugin()` 返回 `None`

**排查步骤：**
1. 检查文件路径是否正确
2. 检查插件类是否继承 `PluginBase`
3. 查看日志中的错误信息
4. 确保 `get_plugin_info()` 方法存在

### 8.2 插件状态异常

**问题：** 插件状态为 `ERROR`

**排查步骤：**
1. 调用 `plugin.get_error_message()` 获取错误信息
2. 检查插件依赖是否满足
3. 查看配置文件是否正确
4. 检查资源是否充足（内存、文件句柄等）

### 8.3 插件无法激活

**问题：** `activate_plugin()` 返回 `False`

**排查步骤：**
1. 检查插件状态是否为 `LOADED` 或 `INACTIVE`
2. 检查 `on_activate()` 是否返回 `True`
3. 检查 `on_start()` 是否返回 `True`
4. 查看日志中的详细错误

---

## 九、未来扩展

### 9.1 计划中的功能

- [ ] 插件市场：支持在线安装/更新插件
- [ ] 插件沙箱：隔离插件运行环境
- [ ] 插件版本管理：支持多版本共存
- [ ] 插件性能分析： profiling 工具
- [ ] 插件热更新：无需重启更新插件

### 9.2 扩展插件类型

- **因子插件**：实现自定义因子计算
- **风控插件**：实现风险控制逻辑
- **报告插件**：生成交易报告
- **通知插件**：推送交易通知

---

## 十、总结

本次插件化改造为量化系统带来了：

✅ **模块化**：功能独立，易于维护  
✅ **可扩展**：新增功能无需修改核心代码  
✅ **热插拔**：动态加载/卸载，无需重启  
✅ **松耦合**：插件间独立，降低依赖  
✅ **易测试**：插件可独立测试  

**下一步：**
1. 将现有策略改造为插件
2. 将现有数据源改造为插件
3. 开发更多功能插件
4. 完善插件文档和示例

---

**文档版本：** 1.0.0  
**更新时间：** 2026-03-11  
**维护者：** quant-system
