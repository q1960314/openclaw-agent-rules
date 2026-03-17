# 数据完整性校验功能 - 修改说明

## 任务概述
执行任务 6：数据完整性校验，为量化交易系统添加数据质量保障功能。

## 修改文件
- **modules/data_validator.py** (779 行，新增约 500 行)

## 新增功能

### 1. 字段完整性检查 ✅
**方法：** `check_field_completeness(df, strategy_type=None)`

**功能：**
- 检查基础必填字段是否存在（ts_code, trade_date, open, high, low, close, vol）
- 检查策略特定字段是否存在（按策略类型区分）
- 计算每个字段的空值比例
- 标记关键字段的空值问题（空值率>5%）

**配置：**
```python
self.required_fields = {
    'base': ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'],
    '打板策略': ['ts_code', 'trade_date', 'close', 'vol', 'limit', 'up_down_times', 'order_amount', 'break_limit_times'],
    '缩量潜伏策略': ['ts_code', 'trade_date', 'close', 'vol', 'high', 'low', 'limit'],
    '板块轮动策略': ['ts_code', 'trade_date', 'close', 'vol', 'industry', 'is_main_industry']
}
```

### 2. 记录数检查 ✅
**方法：** `check_record_count(df, date_range=None)`

**功能：**
- 统计总记录数和股票数量
- 计算每只股票的记录数
- 根据日期范围计算预期记录数
- 检查记录数不足的股票（<60 条）
- 检测记录数异常的股票（可能重复）
- 计算数据覆盖率

**配置：**
```python
self.min_records_per_stock = 60  # 每只股票最小记录数（约 3 个月交易日）
```

### 3. 交易日连续性检查 ✅
**方法：** `check_trading_day_continuity(df, trade_calendar=None)`

**功能：**
- 对比交易日历检查数据连续性
- 找出缺失的交易日
- 找出多余的日期（数据有但日历没有）
- 检测日期中断期
- 计算连续性比例

**配置：**
```python
self.max_gap_days = 5  # 允许的最大交易日中断天数
```

### 4. 数据完整性综合校验 ✅
**方法：** `validate_data_integrity(df, strategy_type=None, trade_calendar=None, date_range=None)`

**功能：**
- 整合所有完整性检查
- 计算综合得分（0-100 分）
- 生成问题列表（按严重程度分类）
- 生成改进建议列表

**评分规则：**
- 字段不完整：-40 分
- 记录数不合理：-30 分
- 连续性不满足：-30 分

### 5. 数据完整性报告生成 ✅
**方法：** `generate_integrity_report(df, strategy_type=None, trade_calendar=None, date_range=None)`

**功能：**
- 生成格式化的文本报告
- 包含所有检查结果
- 显示详细统计信息
- 列出问题和建议

## 使用示例

```python
from modules.data_validator import DataValidator
from modules.data_fetcher import DataFetcher

# 初始化
validator = DataValidator()
fetcher = DataFetcher()

# 获取数据和交易日历
df = fetcher.fetch_all_stocks_data()
trade_calendar = fetcher.fetch_trade_cal('20240101', '20241231')

# 执行完整性校验
result = validator.validate_data_integrity(
    df, 
    strategy_type='打板策略',
    trade_calendar=trade_calendar,
    date_range=('2024-01-01', '2024-12-31')
)

# 查看结果
print(f"综合得分：{result['overall_score']}/100")
print(f"校验结果：{'✅ 通过' if result['is_valid'] else '❌ 未通过'}")

# 生成详细报告
report = validator.generate_integrity_report(
    df, 
    strategy_type='打板策略',
    trade_calendar=trade_calendar
)
print(report)
```

## 约束遵守情况

✅ **配置区参数值不变** - 未修改 config_manager.py 中的任何参数
✅ **保持原有架构** - 保持 DataValidator 类结构，仅新增方法
✅ **添加 # 【优化】标记** - 所有新增代码都有标记

## 交付物

1. ✅ **优化后的代码** - `modules/data_validator.py`
2. ✅ **使用说明文档** - `docs/data_integrity_usage.md`
3. ✅ **测试脚本** - `tests/test_data_integrity.py`
4. ✅ **修改说明** - 本文档

## 技术细节

### 导入依赖
```python
from datetime import datetime, timedelta  # 新增 timedelta
```

### 初始化配置
```python
# 【优化】数据完整性校验配置
self.required_fields = {...}  # 必填字段配置
self.min_records_per_stock = 60  # 最小记录数
self.max_gap_days = 5  # 最大中断天数
```

### 报告格式
报告包含 4 个主要部分：
1. 字段完整性检查
2. 记录数检查
3. 交易日连续性检查
4. 问题汇总与建议

## 后续建议

1. **集成到数据抓取流程** - 在 `data_fetcher.py` 抓取完成后自动调用
2. **集成到回测流程** - 在回测前进行数据完整性校验
3. **定期校验任务** - 设置每周/每月自动校验任务
4. **告警机制** - 当校验不通过时发送告警通知

## 测试验证

- ✅ 语法检查通过（`python3 -m py_compile`）
- ✅ 代码结构完整（779 行，11 个方法）
- ✅ 符合原有代码风格
- ✅ 所有方法有详细文档字符串

---

**修改时间：** 2024-03-11 01:30
**修改人：** 代码守护者（子智能体）
**任务来源：** 策略专家方案 - 任务 6 数据完整性校验

【合规提示】本功能仅用于量化研究回测，不构成任何投资建议，投资有风险，入市需谨慎
