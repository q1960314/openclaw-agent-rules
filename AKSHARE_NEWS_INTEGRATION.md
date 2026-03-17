# AkShare 新闻接口集成文档

## ✅ 集成完成内容

### 1. 代码修改

已在 `fetch_data_optimized.py` 中完成以下集成：

#### 1.1 导入 AkShare 库
```python
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("✅ AkShare 库已加载，支持多源新闻抓取")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("⚠️  AkShare 未安装，新闻接口功能将禁用，请运行：pip install akshare")
```

#### 1.2 新增配置开关
在 `EXTEND_FETCH_CONFIG` 中添加：
```python
"enable_akshare_news": False,     # 开启 AkShare 新闻抓取
"akshare_news_sources": [
    "stock_news_em",              # 东方财富个股新闻
    "news_economic_baidu",        # 百度经济日历
    "stock_news_main_cx",         # 财新数据
    "news_cctv"                   # 新闻联播
]
```

#### 1.3 新增新闻抓取方法
在 `Utils` 类中添加 `fetch_akshare_news()` 方法，支持：
- **ak.stock_news_em()** - 东方财富个股新闻（需指定股票代码）
- **ak.news_economic_baidu()** - 百度经济日历（支持日期范围）
- **ak.stock_news_main_cx()** - 财新数据
- **ak.news_cctv()** - 新闻联播

#### 1.4 集成到抓取流程
在 `fetch_worker()` 函数中添加 AkShare 新闻抓取逻辑：
- 进度显示：96%
- 自动保存到 `akshare_news_all.csv`（Parquet 格式）
- 支持增量抓取和去重

### 2. 测试脚本

已创建 `test_akshare_news.py` 测试脚本，可单独测试 4 个新闻源。

## 📦 安装要求

### 系统要求
- **Python 版本**: Python 3.8+（推荐 Python 3.9+）
- **当前环境**: Python 3.6.8 ⚠️ **需要升级**

### 依赖安装
```bash
# 升级 Python 到 3.9+（根据系统选择合适方式）
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 安装 AkShare
pip install akshare

# 验证安装
python -c "import akshare as ak; print('AkShare 版本:', ak.__version__)"
```

## 🔧 使用方法

### 1. 开启 AkShare 新闻抓取

编辑 `fetch_data_optimized.py`，修改配置：
```python
EXTEND_FETCH_CONFIG = {
    # ... 其他配置 ...
    "enable_akshare_news": True,   # 改为 True 开启
    "akshare_news_sources": [
        "stock_news_em",
        "news_economic_baidu",
        "stock_news_main_cx",
        "news_cctv"
    ]
}
```

### 2. 运行数据抓取

```bash
# 运行完整抓取流程（包含 AkShare 新闻）
python fetch_data_optimized.py
```

### 3. 单独测试新闻接口

```bash
# 运行测试脚本
python test_akshare_news.py
```

## 📊 新闻源说明

### 1. 东方财富个股新闻 (stock_news_em)
- **用途**: 获取特定个股的新闻公告
- **参数**: 需要股票代码（如 "000001"）
- **字段**: 标题、内容、发布时间、来源等
- **使用场景**: 个股舆情分析、利空利好过滤

### 2. 百度经济日历 (news_economic_baidu)
- **用途**: 获取宏观经济事件和日历
- **参数**: 开始日期、结束日期
- **字段**: 事件名称、时间、影响度等
- **使用场景**: 宏观环境分析、系统性风险预警

### 3. 财新数据 (stock_news_main_cx)
- **用途**: 财新财经新闻
- **参数**: 无
- **字段**: 标题、内容、发布时间等
- **使用场景**: 高质量财经新闻获取

### 4. 新闻联播 (news_cctv)
- **用途**: CCTV 新闻联播内容
- **参数**: 无
- **字段**: 标题、内容、播放时间等
- **使用场景**: 政策导向分析、宏观新闻

## 📁 输出文件

### 新闻数据存储位置
```
data/
└── akshare_news_all.csv (或 .parquet)
```

### 数据字段（示例）
```
- title: 新闻标题
- content: 新闻内容
- datetime: 发布时间
- news_source: 新闻来源（stock_news_em 等）
- crawl_time: 抓取时间
```

## ⚠️ 注意事项

### 1. Python 版本兼容性
- **当前环境**: Python 3.6.8 ❌ 不兼容
- **最低要求**: Python 3.8+ ✅
- **建议**: 使用 Python 3.9 或 3.10

### 2. 网络要求
- AkShare 接口需要访问外网
- 确保防火墙允许 HTTP/HTTPS 请求
- 建议在稳定网络环境下运行

### 3. 接口限流
- AkShare 部分接口有访问频率限制
- 建议批量抓取时添加适当延迟
- 代码已内置重试机制

### 4. 数据去重
- 自动根据标题 + 时间去重
- 增量抓取时会合并旧数据
- 避免重复新闻影响分析

## 🐛 故障排查

### 问题 1: AkShare 未安装
```
错误：No module named 'akshare'
解决：pip install akshare
```

### 问题 2: Python 版本过低
```
错误：No matching distribution found for akshare
解决：升级 Python 到 3.8+
```

### 问题 3: 接口超时
```
错误：Request timeout
解决：检查网络连接，增加超时时间
```

### 问题 4: 无数据返回
```
警告：无数据返回
解决：检查日期范围、股票代码是否正确
```

## 📈 后续优化建议

1. **新闻情感分析**: 集成 NLP 模型，自动识别利好/利空
2. **关键词过滤**: 根据关键词筛选重要新闻
3. **新闻关联**: 将新闻与具体股票关联
4. **定时抓取**: 设置定时任务，自动更新新闻
5. **存储优化**: 使用数据库存储，支持复杂查询

## ✅ 验证清单

- [x] AkShare 导入逻辑已添加
- [x] EXTEND_FETCH_CONFIG 配置已更新
- [x] fetch_akshare_news() 方法已实现
- [x] 4 个新闻源接口已集成
- [x] 抓取流程已集成（进度 96%）
- [x] 数据保存逻辑已实现
- [x] 测试脚本已创建
- [ ] Python 环境升级（需要用户操作）
- [ ] AkShare 安装（需要用户操作）
- [ ] 实际运行测试（需要用户操作）

## 📝 更新日志

**2026-03-12**: 
- ✅ 完成 AkShare 新闻接口集成
- ✅ 添加 4 个新闻源支持
- ✅ 创建测试脚本
- ✅ 编写集成文档

---

**合规提示**: 本功能仅为量化研究数据抓取使用，不构成任何投资建议，投资有风险，入市需谨慎。
