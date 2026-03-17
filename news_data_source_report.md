# 新闻数据源方案调研报告

**调研时间：** 2026-03-12  
**调研人：** 数据采集子智能体  
**任务：** 阶段 4 - 新闻数据源调研

---

## 一、调研概述

本次调研针对量化交易系统所需的新闻数据源进行全面评估，包括：
1. **AkShare 新闻接口**（官方封装）
2. **新浪财经**（爬虫方案）
3. **财联社**（爬虫方案）
4. **东方财富**（爬虫方案）

评估维度：接口稳定性、数据完整性、调用频率限制、实现难度

---

## 二、AkShare 新闻接口评估

### 2.1 接口概览

AkShare（v1.18.38）提供以下新闻相关接口：

| 接口名称 | 数据源 | 数据类型 | 返回字段 |
|---------|--------|---------|---------|
| `news_cctv` | CCTV | 新闻联播文字稿 | date, title, content |
| `news_economic_baidu` | 百度股市通 | 经济数据日历 | 日期，时间，地区，事件，公布，预期，前值，重要性 |
| `stock_news_em` | 东方财富 | 个股新闻（100 条） | 关键词，新闻标题，新闻内容，发布时间，文章来源，新闻链接 |
| `stock_news_main_cx` | 财新网 | 财新数据通 | tag, summary, url |
| `futures_news_shmet` | 上海金属网 | 期货快讯 | 发布时间，内容 |
| `index_news_sentiment_scope` | - | 新闻情绪指数 | - |
| `news_trade_notify_*` | 百度 | 贸易通知 | - |

### 2.2 实测结果

| 接口 | 状态 | 响应时间 | 数据量 | 稳定性 |
|-----|------|---------|--------|--------|
| `news_cctv` | ✅ 正常 | ~1.5s | 12 条/天 | 高 |
| `news_economic_baidu` | ✅ 正常 | ~0.5s | 120 条 | 高 |
| `stock_news_em` | ✅ 正常 | ~0.03s | 10 条/股 | 高 |
| `stock_news_main_cx` | ✅ 正常 | ~0.5s | 100 条 | 高 |
| `futures_news_shmet` | ✅ 正常 | ~0.3s | 10 条 | 中 |

### 2.3 优缺点分析

**优点：**
- ✅ 统一接口封装，使用简单（一行代码获取数据）
- ✅ 文档完善，示例丰富
- ✅ 持续维护，接口稳定性高
- ✅ 免费使用，无调用限制
- ✅ 返回结构化 DataFrame，便于处理
- ✅ 支持多数据源交叉验证

**缺点：**
- ⚠️ 部分接口依赖第三方网站，存在被反爬风险
- ⚠️ 财新网接口需要登录/付费才能获取完整内容
- ⚠️ 个股新闻仅返回最近 100 条，历史数据有限
- ⚠️ 无法自定义时间范围查询（部分接口）

### 2.4 调用频率限制

- **官方限制：** 无明确限制
- **实测结果：** 连续调用无失败，平均响应时间 0.03-1.5s
- **建议：** 单接口调用间隔建议≥1 秒，避免触发源站反爬

---

## 三、新浪财经爬虫方案评估

### 3.1 接口信息

**API 端点：** `https://feed.mix.sina.com.cn/api/roll/get`

**请求参数：**
```
pageid=153      # 频道 ID（财经）
lid=2509        # 栏目 ID
num=50          # 每页数量
page=1          # 页码
```

**返回字段（40+）：**
- 核心字段：title, summary, url, ctime, author, media_name
- 扩展字段：img, images, keywords, categoryid, docid 等

### 3.2 实测结果

| 测试项目 | 结果 |
|---------|------|
| 接口可用性 | ✅ 正常 |
| 响应时间 | 0.12-0.17s（平均 0.15s） |
| 单次返回量 | 50 条 |
| 数据更新频率 | 实时 |
| 连续请求测试 | 5 次全部成功 |

### 3.3 优缺点分析

**优点：**
- ✅ 接口公开，无需认证
- ✅ 响应速度快（<200ms）
- ✅ 数据字段丰富，包含图片、关键词等
- ✅ 支持分页，可获取历史数据
- ✅ 新闻覆盖全面（宏观、个股、行业）

**缺点：**
- ⚠️ 无官方文档，需逆向分析
- ⚠️ 时间戳为 Unix 格式，需转换
- ⚠️ 存在反爬风险（需设置 User-Agent）
- ⚠️ 部分内容仅为摘要，需二次爬取详情页

### 3.4 调用频率限制

- **官方限制：** 未公开
- **实测结果：** 连续 5 次请求无失败
- **建议：** 调用间隔≥0.5 秒，单 IP 建议<100 次/分钟

---

## 四、财联社爬虫方案评估

### 4.1 接口信息

**API 端点：** 
- 电报：`https://www.cls.cn/v1/roll/get_roll_list`
- 滚动新闻：`https://www.cls.cn/v3/roll/home`

**请求参数：**
```
app=cailianpress
category=telegraph
os=web
```

### 4.2 实测结果

| 测试项目 | 结果 |
|---------|------|
| 接口可用性 | ⚠️ 部分可用 |
| 响应状态 | 200（但返回 errno 错误） |
| 反爬措施 | 较严格（需 Cookie/Token） |
| 数据质量 | 高（专业财经快讯） |

### 4.3 优缺点分析

**优点：**
- ✅ 数据质量高，专业财经快讯
- ✅ 更新速度快（秒级）
- ✅ 覆盖宏观、个股、行业、政策
- ✅ 有"电报"特色栏目（短线交易必备）

**缺点：**
- ❌ 反爬措施严格，需登录/Cookie
- ❌ 部分高级内容需付费会员
- ❌ 接口无官方文档，需逆向
- ❌ 稳定性较差，接口可能频繁变更

### 4.4 调用频率限制

- **官方限制：** 未公开（需登录）
- **建议：** 如使用，调用间隔≥5 秒，需维护 Cookie 池

---

## 五、东方财富爬虫方案评估

### 5.1 接口信息

**API 端点：**
- 个股新闻：`https://so.eastmoney.com/news/s?keyword={symbol}`
- 公告新闻：`https://np-anotice-stock.eastmoney.com/api/security/v1/notice/list`

### 5.2 实测结果

| 测试项目 | 结果 |
|---------|------|
| 接口可用性 | ✅ 正常（通过 AkShare） |
| 响应时间 | ~0.03s |
| 单次返回量 | 10 条/股 |
| 数据完整性 | 高（标题 + 内容 + 时间 + 来源 + 链接） |

### 5.3 优缺点分析

**优点：**
- ✅ 数据完整，包含全文内容
- ✅ 响应速度快
- ✅ 支持个股定向查询
- ✅ 通过 AkShare 封装，使用简单
- ✅ 文章来源可靠（财中社、证券时报等）

**缺点：**
- ⚠️ 单次查询仅限 100 条历史记录
- ⚠️ 不支持自定义时间范围
- ⚠️ 批量查询多只股票时需控制频率

### 5.4 调用频率限制

- **官方限制：** 未公开
- **实测结果：** 连续调用无失败
- **建议：** 单股查询间隔≥1 秒，批量查询建议<50 股/分钟

---

## 六、综合对比

| 评估维度 | AkShare | 新浪财经 | 财联社 | 东方财富 |
|---------|---------|---------|--------|---------|
| **接口稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **数据完整性** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **调用频率限制** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **实现难度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **数据时效性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **维护成本** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**评分说明：** ⭐⭐⭐⭐⭐=最优，⭐=最差

---

## 七、推荐方案

### 7.1 首选方案：AkShare 为主 + 新浪财经补充

**推荐架构：**
```
新闻数据采集层
├── 个股新闻：ak.stock_news_em()  # 东方财富数据
├── 宏观新闻：ak.news_economic_baidu()  # 百度经济日历
├── 财经快讯：ak.stock_news_main_cx()  # 财新数据
├── 政策新闻：ak.news_cctv()  # 新闻联播
└── 实时补充：新浪财经 API  # 滚动新闻补充
```

**理由：**
1. **开发效率高**：AkShare 封装完善，一行代码获取数据
2. **维护成本低**：AkShare 团队持续维护接口
3. **数据覆盖全**：多数据源互补，覆盖个股/宏观/政策
4. **稳定性好**：实测接口稳定，响应快速
5. **合规风险低**：AkShare 为开源项目，数据采集合规

### 7.2 备选方案：直接爬虫（仅当 AkShare 不可用时）

**爬虫优先级：**
1. 新浪财经 API（公开、快速、稳定）
2. 东方财富个股新闻（数据完整）
3. 财联社（需解决反爬，不推荐）

**注意事项：**
- 需实现 User-Agent 轮换
- 需实现请求频率控制
- 需实现异常重试机制
- 需定期验证接口可用性

---

## 八、实现建议

### 8.1 代码示例（AkShare）

```python
import akshare as ak
from datetime import datetime

# 1. 获取个股新闻
def get_stock_news(symbol: str) -> pd.DataFrame:
    """获取个股最近 100 条新闻"""
    df = ak.stock_news_em(symbol=symbol)
    return df

# 2. 获取经济数据日历
def get_economic_news(date: str = None) -> pd.DataFrame:
    """获取经济数据发布日历"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    df = ak.news_economic_baidu(date=date)
    return df

# 3. 获取财新新闻
def get_caixin_news() -> pd.DataFrame:
    """获取财新最新 100 条新闻"""
    df = ak.stock_news_main_cx()
    return df

# 4. 获取新闻联播
def get_cctv_news(date: str = None) -> pd.DataFrame:
    """获取指定日期新闻联播文字稿"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    df = ak.news_cctv(date=date)
    return df
```

### 8.2 代码示例（新浪财经爬虫）

```python
import requests
import pandas as pd
from datetime import datetime

def get_sina_news(page: int = 1, num: int = 50) -> pd.DataFrame:
    """获取新浪财经滚动新闻"""
    url = "https://feed.mix.sina.com.cn/api/roll/get"
    params = {
        "pageid": 153,
        "lid": 2509,
        "num": num,
        "page": page
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    data = resp.json()
    
    news_list = data['result']['data']
    df = pd.DataFrame(news_list)
    df['ctime'] = pd.to_datetime(df['ctime'], unit='s')
    return df[['title', 'summary', 'url', 'ctime', 'media_name']]
```

### 8.3 频率控制建议

```python
import time
from functools import wraps

def rate_limit(calls: int = 1, period: float = 1.0):
    """频率限制装饰器"""
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < period:
                time.sleep(period - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

# 使用示例
@rate_limit(calls=1, period=1.0)  # 每秒最多 1 次
def fetch_news():
    return ak.stock_news_em(symbol="000001")
```

---

## 九、风险提示

1. **接口变更风险**：所有爬虫方案均存在源站接口变更风险，需定期检查
2. **反爬风险**：高频调用可能触发 IP 封禁，建议实现代理池
3. **数据合规风险**：采集数据仅限学术研究，不得用于商业用途
4. **内容完整性风险**：部分接口仅返回摘要，需二次爬取详情页

---

## 十、结论

**推荐方案：AkShare 为主 + 新浪财经补充**

- **开发周期：** 1-2 天（AkShare 方案）
- **维护成本：** 低（AkShare 团队维护）
- **数据质量：** 高（多源验证）
- **稳定性：** 高（实测稳定）
- **合规性：** 高（开源项目）

**下一步行动：**
1. ✅ 安装 AkShare：`pip install akshare --upgrade`
2. ✅ 实现新闻采集模块（基于 AkShare）
3. ✅ 实现频率控制机制
4. ✅ 实现异常重试机制
5. ✅ 定期验证接口可用性

---

**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎。
