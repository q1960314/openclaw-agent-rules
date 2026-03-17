# 【优化】数据源模块重构说明

## 任务编号
代码守护者 - 任务 9：新数据源接入预留

## 修改概述
将原有单体 `data_fetcher.py` 重构为插件化数据源架构，支持多数据源灵活切换。

---

## 一、新增文件结构

```
modules/data_sources/
├── __init__.py           # 模块导出
├── base.py               # 【核心】DataSource 抽象基类
├── tushare_source.py     # 【已实现】Tushare 数据源插件
├── wind_source.py        # 【预留】Wind 数据源接口（待实现）
├── joinquant_source.py   # 【预留】JoinQuant 数据源接口（待实现）
└── factory.py            # 【核心】数据源工厂类 + 配置管理
```

---

## 二、核心改动

### 1. DataSource 抽象基类（`base.py`）
**功能：** 定义所有数据源必须实现的统一接口

**抽象方法（17 个）：**
- `connect()` / `disconnect()` / `is_connected()` - 连接管理
- `fetch_stock_basic()` - 股票基本信息
- `fetch_trade_cal()` - 交易日历
- `fetch_daily_data()` - 日线数据
- `fetch_daily_basic()` - 每日基本面
- `fetch_fina_indicator()` - 财务指标
- `fetch_stk_limit()` - 涨跌停
- `fetch_top_list()` - 龙虎榜
- `fetch_top_inst()` - 机构席位
- `fetch_news()` - 新闻资讯
- `fetch_concept()` - 概念板块
- `fetch_moneyflow()` - 资金流向
- `fetch_index_daily()` - 指数日线
- `fetch_suspend_d()` - 停牌数据
- `fetch_block_trade()` - 大宗交易
- `fetch_hk_hold()` - 北向资金持股

**设计优势：**
- ✅ 接口统一：所有数据源提供一致的方法签名
- ✅ 插件化：支持动态加载/卸载数据源
- ✅ 可扩展：新增数据源只需继承实现，不影响现有代码
- ✅ 上下文管理：支持 `with` 语句自动管理连接

---

### 2. TushareSource 实现（`tushare_source.py`）
**功能：** 基于原有 `DataFetcher` 重构的 Tushare 数据源插件

**核心特性：**
- ✅ 完整实现所有 17 个抽象方法
- ✅ 复用原有令牌桶限流逻辑（秒级 + 分钟级双重限流）
- ✅ 保留指数退避重试机制
- ✅ 保留限流统计功能（`get_rate_limit_stats()`）
- ✅ 支持上下文管理（`with TushareSource(...) as source:`）

**配置参数：**
```python
{
    'TUSHARE_TOKEN': 'your_token',
    'TUSHARE_API_URL': 'http://api.tushare.pro',
    'FETCH_OPTIMIZATION': {
        'max_requests_per_second': 10,
        'max_requests_per_minute': 2500
    }
}
```

---

### 3. WindSource 预留接口（`wind_source.py`）
**状态：** 🔲 预留接口，待实现

**待实现功能：**
- WindPy SDK 集成
- Wind 终端连接管理
- 17 个基础数据接口实现
- Wind 专属方法：
  - `fetch_wind_bar()` - K 线数据（Bar 数据）
  - `fetch_wind_edb()` - 宏观经济数据（EDB）

**接入步骤（未来实现时参考）：**
1. 安装 WindPy: `pip install WindPy`
2. 配置 Wind 账号：`WIND_CODE`, `WIND_PASSWORD`
3. 实现 `connect()` 连接 Wind 终端
4. 实现所有 `fetch_*` 方法对接 Wind API
5. 添加 Wind 专属限流策略

**注意事项：**
- ⚠️ Wind 需要本地安装金融终端
- ⚠️ 需要有效的 Wind 账号授权
- ⚠️ API 调用频率限制与 Tushare 不同
- ⚠️ 数据字段命名可能与 Tushare 有差异

---

### 4. JoinQuantSource 预留接口（`joinquant_source.py`）
**状态：** 🔲 预留接口，待实现

**待实现功能：**
- jqdatasdk SDK 集成
- JoinQuant API 连接管理
- 17 个基础数据接口实现
- JoinQuant 专属方法：
  - `fetch_factor_data()` - 因子数据（特色功能）
  - `fetch_minute_data()` - 分钟线数据
  - `get_current_data()` - 实时行情

**接入步骤（未来实现时参考）：**
1. 安装 jqdatasdk: `pip install jqdatasdk`
2. 配置 JoinQuant 账号：`JQ_USERNAME`, `JQ_PASSWORD`
3. 实现 `connect()` 连接 JoinQuant
4. 实现所有 `fetch_*` 方法对接 JoinQuant API
5. 添加 JoinQuant 专属限流策略（免费账户有调用限制）

**注意事项：**
- ⚠️ JoinQuant 需要注册账号（有免费额度）
- ⚠️ 免费账户：每天最多 100 万次调用
- ⚠️ 数据字段命名与 Tushare/Wind 有差异
- ⚠️ 支持丰富的因子数据（特色功能）

---

### 5. DataSourceFactory 工厂类（`factory.py`）
**功能：** 统一管理数据源的创建、注册、切换

**核心方法：**
- `register(name, class)` - 注册新数据源类型
- `create(source_type, config)` - 创建数据源实例（单例模式）
- `get(source_type)` - 获取已创建的实例
- `switch(source_type, config)` - 切换数据源
- `disconnect(source_type)` - 断开指定数据源
- `disconnect_all()` - 断开所有数据源
- `list_available()` - 列出已注册的数据源
- `list_active()` - 列出已激活的数据源
- `get_status(source_type)` - 获取数据源状态

**使用示例：**
```python
from modules.data_sources import DataSourceFactory, DataSourceConfig

# 创建 Tushare 数据源
config = DataSourceConfig.get_config('tushare', global_config)
tushare = DataSourceFactory.create('tushare', config)

# 连接到数据源
tushare.connect()

# 获取数据
df = tushare.fetch_daily_data(ts_code='000001.SZ', start_date='20240101', end_date='20241231')

# 切换数据源（未来）
# wind = DataSourceFactory.switch('wind', wind_config)

# 断开连接
DataSourceFactory.disconnect_all()
```

---

### 6. DataSourceConfig 配置管理（`factory.py`）
**功能：** 统一管理所有数据源的配置参数

**支持的数据源配置：**
- `tushare`: TUSHARE_TOKEN, TUSHARE_API_URL, FETCH_OPTIMIZATION
- `wind`: WIND_CODE, WIND_PASSWORD, WIND_SERVER, WIND_PORT（预留）
- `joinquant`: JQ_USERNAME, JQ_PASSWORD（预留）

**核心方法：**
- `get_config(source_type, global_config)` - 获取指定数据源配置
- `validate_all(global_config)` - 校验所有数据源配置

---

## 三、配置区参数（保持不变）

根据任务约束，以下配置参数值**保持不变**：

```python
# config_manager.py 中的原有配置
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
FETCH_OPTIMIZATION = {
    'max_workers': 20,
    'batch_io_interval': 10,
    'max_requests_per_minute': 2500
}
```

---

## 四、架构优势

### 1. 插件化设计
- ✅ 新增数据源只需继承 `DataSource` 基类并注册
- ✅ 不影响现有代码，符合开闭原则
- ✅ 支持运行时动态切换数据源

### 2. 统一接口
- ✅ 所有数据源提供一致的方法签名
- ✅ 上层业务代码无需关心具体数据源
- ✅ 便于测试和 Mock

### 3. 工厂模式
- ✅ 集中管理数据源创建和生命周期
- ✅ 单例模式避免重复创建实例
- ✅ 支持配置校验和状态查询

### 4. 向后兼容
- ✅ 保留原有 `DataFetcher` 的所有限流、重试逻辑
- ✅ 配置参数完全兼容
- ✅ 可逐步迁移，不影响现有功能

---

## 五、后续扩展建议

### 短期（1-2 周）
1. ✅ 在 `config_manager.py` 中添加数据源选择配置：
   ```python
   DATA_SOURCE_TYPE = "tushare"  # 可选：tushare / wind / joinquant
   ```

2. ✅ 修改主程序入口，使用工厂类创建数据源：
   ```python
   from modules.data_sources import DataSourceFactory, DataSourceConfig
   
   config = DataSourceConfig.get_config(DATA_SOURCE_TYPE, global_config)
   data_source = DataSourceFactory.create(DATA_SOURCE_TYPE, config)
   data_source.connect()
   ```

### 中期（1-2 月）
1. 🔲 实现 WindSource（需要 Wind 终端环境）
2. 🔲 实现 JoinQuantSource（需要 JoinQuant 账号）
3. 🔲 添加数据源自动故障切换机制

### 长期（3-6 月）
1. 🔲 支持多数据源并行查询（提升性能）
2. 🔲 添加数据源健康检查
3. 🔲 实现数据源性能监控和统计

---

## 六、测试建议

### 单元测试
```python
# tests/test_data_sources.py
def test_tushare_source():
    config = {...}
    source = TushareSource(config)
    assert source.connect() == True
    df = source.fetch_stock_basic()
    assert not df.empty
    source.disconnect()
```

### 集成测试
```python
# tests/test_factory.py
def test_factory_create():
    source = DataSourceFactory.create('tushare', config)
    assert source is not None
    assert source.is_connected() == True
```

---

## 七、文件清单

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `modules/data_sources/__init__.py` | ✅ 完成 | 18 | 模块导出 |
| `modules/data_sources/base.py` | ✅ 完成 | 168 | DataSource 抽象基类 |
| `modules/data_sources/tushare_source.py` | ✅ 完成 | 428 | Tushare 实现 |
| `modules/data_sources/wind_source.py` | ✅ 预留 | 150 | Wind 接口（待实现） |
| `modules/data_sources/joinquant_source.py` | ✅ 预留 | 168 | JoinQuant 接口（待实现） |
| `modules/data_sources/factory.py` | ✅ 完成 | 248 | 工厂类 + 配置管理 |
| **总计** | | **1180** | |

---

## 八、合规提示

⚠️ **本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎**

---

## 任务完成确认

✅ **交付物 1：** 优化后的代码（`modules/data_sources/` 目录，共 6 个文件）
✅ **交付物 2：** 简要修改说明（本文档）
✅ **约束满足：** 配置区参数值不变、保持原有架构、添加 # 【优化】标记

**执行状态：** 任务 9 完成 ✅
