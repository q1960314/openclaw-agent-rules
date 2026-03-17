# 实时数据源集成文档

**版本：** v1.0  
**日期：** 2026-03-12  
**状态：** ✅ 已完成集成

---

## 一、背景与目标

### 1.1 问题
Tushare 实时数据接口存在以下限制：
- 需要积分，有调用次数限制
- 部分高级接口需要付费
- 单点故障风险

### 1.2 目标
构建多数据源备用机制，实现：
1. **AkShare 实时接口集成** - 免费、开源
2. **新浪财经爬虫集成** - HTTP 接口、稳定
3. **东方财富爬虫集成** - 资金流向、板块排名
4. **数据源切换机制** - 自动降级、高可用

---

## 二、架构设计

### 2.1 数据源优先级

```
┌─────────────────────────────────────────┐
│          实时数据请求                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  优先级 1: Tushare (如有 Token)          │
│  - 最稳定、数据质量高                    │
│  - 缺点：需要积分                        │
└──────────────┬──────────────────────────┘
               │ 失败
               ▼
┌─────────────────────────────────────────┐
│  优先级 2: AkShare                       │
│  - 免费、基于东方财富接口                │
│  - 功能：实时行情、板块、热榜            │
└──────────────┬──────────────────────────┘
               │ 失败
               ▼
┌─────────────────────────────────────────┐
│  优先级 3: 新浪爬虫                       │
│  - HTTP 接口、无需认证                    │
│  - 功能：实时行情、分钟线                │
└──────────────┬──────────────────────────┘
               │ 失败
               ▼
┌─────────────────────────────────────────┐
│  优先级 4: 东财爬虫                       │
│  - HTTP 接口、无需认证                    │
│  - 功能：资金流向、板块排名              │
└─────────────────────────────────────────┘
```

### 2.2 模块结构

```
modules/data_sources/
├── base.py                    # 数据源基类
├── tushare_source.py          # Tushare 数据源
├── akshare_realtime.py        # 【新增】AkShare 实时数据源
├── sina_crawler.py            # 【新增】新浪财经爬虫
├── eastmoney_crawler.py       # 【新增】东方财富爬虫
├── realtime_manager.py        # 【新增】实时数据管理器
├── factory.py                 # 数据源工厂
└── __init__.py                # 模块导出
```

---

## 三、接口说明

### 3.1 AkShare 实时数据源

**文件：** `modules/data_sources/akshare_realtime.py`

#### 核心接口

| 方法 | 说明 | 返回类型 |
|------|------|----------|
| `get_realtime_spot()` | 获取 A 股实时行情（全市场） | `pd.DataFrame` |
| `get_realtime_by_code(code)` | 获取单只股票实时行情 | `Dict` |
| `get_industry_board_realtime()` | 获取行业板块实时行情 | `pd.DataFrame` |
| `get_concept_board_realtime()` | 获取概念板块实时行情 | `pd.DataFrame` |
| `get_hot_rank()` | 获取股票热榜（人气排名） | `pd.DataFrame` |

#### 使用示例

```python
from modules.data_sources import AkShareRealtimeSource

# 初始化
source = AkShareRealtimeSource({})
source.connect()

# 获取全市场实时行情
df = source.get_realtime_spot()
print(df[['ts_code', 'name', 'price', 'pct_change']].head())

# 获取单只股票
data = source.get_realtime_by_code("000001.SZ")
print(f"平安银行：¥{data['price']} ({data['pct_change']}%)")

# 获取行业板块
board_df = source.get_industry_board_realtime()
print(board_df[['board_name', 'pct_change']].head())

source.disconnect()
```

---

### 3.2 新浪财经爬虫

**文件：** `modules/data_sources/sina_crawler.py`

#### 核心接口

| 方法 | 说明 | 返回类型 |
|------|------|----------|
| `get_realtime_by_code(code)` | 获取单只股票实时行情 | `Dict` |
| `get_realtime_batch(codes)` | 批量获取实时行情 | `Dict` |
| `get_minute_data(code, period, count)` | 获取分钟线数据 | `pd.DataFrame` |

#### 使用示例

```python
from modules.data_sources import SinaCrawlerSource

source = SinaCrawlerSource({})
source.connect()

# 获取单只股票
data = source.get_realtime_by_code("000001.SZ")
print(f"{data['name']}: ¥{data['price']}")

# 获取 5 分钟线
df = source.get_minute_data("000001.SZ", period='5', count=100)
print(df[['trade_time', 'open', 'high', 'low', 'close']].tail())

source.disconnect()
```

---

### 3.3 东方财富爬虫

**文件：** `modules/data_sources/eastmoney_crawler.py`

#### 核心接口

| 方法 | 说明 | 返回类型 |
|------|------|----------|
| `get_stock_moneyflow(code)` | 获取单只股票资金流向 | `Dict` |
| `get_industry_board_rank(top_n)` | 获取行业板块排名 | `pd.DataFrame` |
| `get_concept_board_rank(top_n)` | 获取概念板块排名 | `pd.DataFrame` |
| `get_main_money_rank(top_n)` | 获取主力资金净流入排名 | `pd.DataFrame` |

#### 使用示例

```python
from modules.data_sources import EastmoneyCrawlerSource

source = EastmoneyCrawlerSource({})
source.connect()

# 获取资金流向
flow = source.get_stock_moneyflow("000001")
print(f"主力净流入：{flow['main_net_inflow']:.2f}万元")

# 获取行业板块排名
df = source.get_industry_board_rank(top_n=20)
print(df[['rank', 'board_name', 'pct_change', 'main_net_inflow']])

# 获取主力资金排名
df = source.get_main_money_rank(top_n=20)
print(df[['rank', 'ts_code', 'name', 'main_net_inflow']])

source.disconnect()
```

---

### 3.4 实时数据管理器（核心）

**文件：** `modules/data_sources/realtime_manager.py`

#### 核心函数

```python
def get_realtime_data(stock_code: str) -> Optional[Dict[str, Any]]
```

**功能：** 自动按优先级切换数据源获取实时行情

**返回字段：**
- `ts_code`: 股票代码
- `name`: 股票名称
- `price`: 最新价
- `pct_change`: 涨跌幅
- `change`: 涨跌额
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `pre_close`: 昨收价
- `volume`: 成交量
- `amount`: 成交额
- `source`: 数据来源（tushare/akshare/sina/eastmoney）

#### 使用示例

```python
from modules.data_sources import get_realtime_data, get_realtime_manager

# 方式 1：使用便捷函数
data = get_realtime_data("000001")
if data:
    print(f"{data['ts_code']}: ¥{data['price']} ({data['pct_change']}%)")
    print(f"数据源：{data['source']}")

# 方式 2：使用管理器（可配置）
config = {
    'TUSHARE_TOKEN': 'your_token',  # 可选
    'REALTIME_CACHE_TIMEOUT': 30,
}
manager = get_realtime_manager(config)

# 批量获取
batch_data = manager.get_realtime_batch(["000001", "600519", "300750"])
for code, data in batch_data.items():
    print(f"{code}: {data['price']}")

# 获取统计
stats = manager.get_stats()
print(f"总请求：{stats['total_requests']}")
print(f"各数据源成功：{stats['success_by_source']}")
```

---

## 四、集成到主代码

### 4.1 修改抓取逻辑

在 `fetch_data_optimized.py` 中添加实时数据源导入：

```python
# 在文件开头添加
from modules.data_sources import (
    get_realtime_data,
    get_realtime_manager,
    AkShareRealtimeSource,
)
```

### 4.2 添加数据源配置

在 `config.yaml` 中添加：

```yaml
# 实时数据源配置
REALTIME_DATA:
  enabled: true
  priority:
    - tushare
    - akshare
    - sina
    - eastmoney
  cache_timeout: 30  # 缓存超时时间（秒）
  timeout: 10  # 请求超时时间（秒）
  max_retry: 3  # 最大重试次数
```

### 4.3 实时抓取模式

修改 `AUTO_RUN_MODE = "实时抓取"` 时的逻辑：

```python
if AUTO_RUN_MODE == "实时抓取":
    # 使用实时数据源
    realtime_data = get_realtime_data(stock_code)
    if realtime_data:
        # 处理实时数据
        process_realtime_quote(realtime_data)
```

---

## 五、测试验证

### 5.1 运行测试

```bash
cd /home/admin/.openclaw/agents/master
source venv/bin/activate
python tests/test_realtime_sources.py
```

### 5.2 测试报告

测试报告保存在：`tests/realtime_source_test_report.md`

### 5.3 测试结果

| 数据源 | 实时行情 | 板块数据 | 资金流向 | 稳定性 |
|--------|----------|----------|----------|--------|
| Tushare | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| AkShare | ✅ | ✅ | ❌ | ⭐⭐⭐⭐ |
| 新浪 | ✅ | ❌ | ❌ | ⭐⭐⭐ |
| 东财 | ⚠️ | ✅ | ✅ | ⭐⭐⭐⭐ |

**注：** 
- ✅ = 完全支持
- ⚠️ = 部分支持
- ❌ = 不支持
- 稳定性评级基于网络环境

---

## 六、故障排查

### 6.1 常见问题

#### 问题 1：AkShare 连接失败
**原因：** 网络问题或东方财富接口限流  
**解决：**
```python
# 增加重试次数
config = {'SINA_MAX_RETRY': 5}
# 增加请求间隔
config = {'SINA_REQUEST_DELAY': 0.5}
```

#### 问题 2：新浪 403 错误
**原因：** User-Agent 被识别  
**解决：** 已自动添加浏览器 headers

#### 问题 3：东财数据为空
**原因：** 接口参数变化  
**解决：** 检查 API URL 和参数

### 6.2 日志查看

```bash
# 查看实时数据源日志
tail -f logs/quant_info.log | grep -E "AkShare|Sina|Eastmoney|Realtime"
```

---

## 七、性能优化建议

### 7.1 缓存策略
- 实时行情缓存 30 秒
- 板块数据缓存 60 秒
- 资金流向缓存 60 秒

### 7.2 并发控制
- 单线程请求，避免 IP 被封
- 请求间隔 0.1-0.5 秒
- 批量获取时使用线程池

### 7.3 降级策略
```python
# 当主数据源失败率 > 50% 时，自动降级
if failure_rate > 0.5:
    priority_order.remove(failed_source)
```

---

## 八、后续扩展

### 8.1 计划支持的数据源
- [ ] 腾讯财经
- [ ] 同花顺
- [ ] 通达信

### 8.2 计划支持的功能
- [ ] Level-2 行情
- [ ] 逐笔成交
- [ ] 委托队列
- [ ] 实时 K 线

---

## 九、合规声明

**本模块仅用于量化研究回测，不构成任何投资建议。**

- 所有数据来源于公开接口
- 遵守各平台 robots.txt 协议
- 控制请求频率，避免对服务器造成压力
- 投资有风险，入市需谨慎

---

## 十、交付清单

- [x] AkShare 实时接口集成 (`akshare_realtime.py`)
- [x] 新浪财经爬虫集成 (`sina_crawler.py`)
- [x] 东方财富爬虫集成 (`eastmoney_crawler.py`)
- [x] 数据源切换机制 (`realtime_manager.py`)
- [x] 模块导出更新 (`__init__.py`)
- [x] 测试脚本 (`tests/test_realtime_sources.py`)
- [x] 集成文档 (`REALTIME_DATA_SOURCE_INTEGRATION.md`)

---

**完成时间：** 2026-03-12  
**执行人：** 数据采集员智能体  
**审核状态：** 待 Master 审核
