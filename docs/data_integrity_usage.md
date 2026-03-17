# 数据完整性校验功能使用说明

## 【优化】功能概述

在 `modules/data_validator.py` 中新增了数据完整性校验功能，包括：

1. **字段完整性检查** - 检查必填字段是否存在
2. **记录数检查** - 检查数据量是否合理
3. **交易日连续性检查** - 对比交易日历检查数据连续性
4. **数据完整性报告** - 生成完整的校验报告

## 新增方法

### 1. `check_field_completeness(df, strategy_type=None)`

**功能：** 字段完整性检查

**参数：**
- `df`: 待检查的 DataFrame
- `strategy_type`: 策略类型（可选），支持："打板策略"、"缩量潜伏策略"、"板块轮动策略"

**返回：** 字典，包含：
- `is_complete`: 是否完整（bool）
- `missing_base_fields`: 缺失的基础字段列表
- `missing_strategy_fields`: 缺失的策略特定字段列表
- `null_ratio_by_field`: 每个字段的空值比例
- `critical_null_fields`: 关键字段的空值问题

**示例：**
```python
from modules.data_validator import DataValidator

validator = DataValidator()
result = validator.check_field_completeness(df, strategy_type='打板策略')

if not result['is_complete']:
    print(f"缺失字段：{result['missing_base_fields']}")
    print(f"空值问题：{result['critical_null_fields']}")
```

### 2. `check_record_count(df, date_range=None)`

**功能：** 记录数检查

**参数：**
- `df`: 待检查的 DataFrame
- `date_range`: 日期范围元组 (start_date, end_date)

**返回：** 字典，包含：
- `is_reasonable`: 是否合理（bool）
- `total_records`: 总记录数
- `total_stocks`: 股票数量
- `records_per_stock`: 每只股票的记录数
- `expected_records`: 预期记录数
- `coverage_ratio`: 覆盖率
- `insufficient_stocks`: 记录数不足的股票列表
- `abnormal_stocks`: 记录数异常的股票列表

**示例：**
```python
result = validator.check_record_count(df, date_range=('2024-01-01', '2024-12-31'))

if not result['is_reasonable']:
    print(f"覆盖率：{result['coverage_ratio']*100:.2f}%")
    print(f"记录数不足的股票：{len(result['insufficient_stocks'])}只")
```

### 3. `check_trading_day_continuity(df, trade_calendar=None)`

**功能：** 交易日连续性检查

**参数：**
- `df`: 待检查的 DataFrame
- `trade_calendar`: 交易日历列表（datetime 对象列表）

**返回：** 字典，包含：
- `is_continuous`: 是否连续（bool）
- `total_trading_days`: 实际交易日数
- `expected_trading_days`: 预期交易日数
- `missing_days`: 缺失的交易日列表
- `extra_days`: 多余的日期列表
- `gap_periods`: 中断期列表
- `continuity_ratio`: 连续性比例

**示例：**
```python
# 获取交易日历
from modules.data_fetcher import DataFetcher
fetcher = DataFetcher()
trade_calendar = fetcher.fetch_trade_cal('20240101', '20241231')

result = validator.check_trading_day_continuity(df, trade_calendar=trade_calendar)

if not result['is_continuous']:
    print(f"缺失 {len(result['missing_days'])} 个交易日")
    print(f"连续性比例：{result['continuity_ratio']*100:.2f}%")
```

### 4. `validate_data_integrity(df, strategy_type=None, trade_calendar=None, date_range=None)`

**功能：** 数据完整性综合校验（整合所有检查）

**参数：**
- `df`: 待验证的 DataFrame
- `strategy_type`: 策略类型
- `trade_calendar`: 交易日历列表
- `date_range`: 日期范围元组

**返回：** 字典，包含：
- `is_valid`: 是否通过验证（bool）
- `timestamp`: 校验时间戳
- `field_completeness`: 字段完整性检查结果
- `record_count`: 记录数检查结果
- `trading_continuity`: 连续性检查结果
- `overall_score`: 综合得分（0-100）
- `issues`: 问题列表
- `recommendations`: 改进建议列表

**示例：**
```python
result = validator.validate_data_integrity(
    df, 
    strategy_type='打板策略',
    trade_calendar=trade_calendar,
    date_range=('2024-01-01', '2024-12-31')
)

print(f"综合得分：{result['overall_score']}/100")
print(f"校验结果：{'✅ 通过' if result['is_valid'] else '❌ 未通过'}")

for issue in result['issues']:
    print(f"[{issue['severity']}] {issue['type']}: {issue['details']}")
```

### 5. `generate_integrity_report(df, strategy_type=None, trade_calendar=None, date_range=None)`

**功能：** 生成数据完整性报告（文本格式）

**参数：** 同 `validate_data_integrity`

**返回：** 格式化的文本报告

**示例：**
```python
report = validator.generate_integrity_report(
    df, 
    strategy_type='打板策略',
    trade_calendar=trade_calendar,
    date_range=('2024-01-01', '2024-12-31')
)

print(report)
```

## 配置参数

在 `DataValidator.__init__()` 中可配置以下参数：

```python
# 【优化】数据完整性校验配置
self.required_fields = {
    'base': ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'],
    '打板策略': ['ts_code', 'trade_date', 'close', 'vol', 'limit', 'up_down_times', 'order_amount', 'break_limit_times'],
    '缩量潜伏策略': ['ts_code', 'trade_date', 'close', 'vol', 'high', 'low', 'limit'],
    '板块轮动策略': ['ts_code', 'trade_date', 'close', 'vol', 'industry', 'is_main_industry']
}
self.min_records_per_stock = 60  # 每只股票最小记录数（约 3 个月交易日）
self.max_gap_days = 5  # 允许的最大交易日中断天数
```

## 使用场景

### 场景 1：数据抓取后校验

```python
from modules.data_validator import DataValidator
from modules.data_fetcher import DataFetcher

# 抓取数据
fetcher = DataFetcher()
df = fetcher.fetch_daily_data('000001.SZ', '20240101', '20241231')

# 校验数据完整性
validator = DataValidator()
result = validator.validate_data_integrity(df, strategy_type='打板策略')

if not result['is_valid']:
    print("数据完整性校验失败，需要补充数据")
    for rec in result['recommendations']:
        print(f"建议：{rec}")
```

### 场景 2：回测前数据校验

```python
# 回测前校验数据完整性
trade_calendar = fetcher.fetch_trade_cal('20240101', '20241231')
report = validator.generate_integrity_report(
    df, 
    strategy_type='打板策略',
    trade_calendar=trade_calendar,
    date_range=('2024-01-01', '2024-12-31')
)

print(report)

# 只有校验通过才进行回测
if validator.validate_data_integrity(df)['is_valid']:
    run_backtest(df)
else:
    print("数据不完整，请先补充数据")
```

### 场景 3：定期数据质量检查

```python
# 每周运行一次数据完整性检查
def weekly_data_check():
    validator = DataValidator()
    fetcher = DataFetcher()
    
    # 加载所有数据
    df = load_all_data()
    
    # 获取交易日历
    trade_calendar = fetcher.fetch_trade_cal('20240101', '20241231')
    
    # 生成报告
    report = validator.generate_integrity_report(
        df, 
        strategy_type='打板策略',
        trade_calendar=trade_calendar
    )
    
    # 保存报告
    with open('data_integrity_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report
```

## 报告示例

```
======================================================================
【数据完整性校验报告】
======================================================================
生成时间：2024-03-11 01:30:00
综合得分：85/100
校验结果：✅ 通过

----------------------------------------------------------------------
【1. 字段完整性检查】
----------------------------------------------------------------------
状态：✅ 完整
📊 字段空值统计：
   - vol: 2.35%
   - close: 0.50%

----------------------------------------------------------------------
【2. 记录数检查】
----------------------------------------------------------------------
状态：✅ 合理
总记录数：1500 行
股票数量：5 只
预期记录数：1210 行
覆盖率：123.97%

----------------------------------------------------------------------
【3. 交易日连续性检查】
----------------------------------------------------------------------
状态：✅ 连续
实际交易日：242 天
预期交易日：242 天
连续性比例：100.00%

----------------------------------------------------------------------
【4. 问题汇总与建议】
----------------------------------------------------------------------
✅ 未发现明显问题

======================================================================
```

## 注意事项

1. **配置区参数值不变** - 所有配置参数保持原有值
2. **保持原有架构** - 不改变原有代码架构，仅新增功能
3. **# 【优化】标记** - 所有新增代码都添加了 `# 【优化】` 标记
4. **依赖** - 需要 `pandas`、`numpy` 库支持
5. **交易日历** - 连续性检查需要交易日历数据，可通过 `DataFetcher.fetch_trade_cal()` 获取

## 测试

运行测试脚本验证功能：

```bash
cd /home/admin/.openclaw/agents/master
python3 tests/test_data_integrity.py
```

## 修改说明

### 修改文件
- `modules/data_validator.py` - 新增数据完整性校验功能

### 新增方法
1. `check_field_completeness()` - 字段完整性检查
2. `check_record_count()` - 记录数检查
3. `check_trading_day_continuity()` - 交易日连续性检查
4. `validate_data_integrity()` - 综合校验
5. `generate_integrity_report()` - 生成报告

### 配置参数
- `required_fields` - 必填字段配置（按策略类型区分）
- `min_records_per_stock` - 每只股票最小记录数
- `max_gap_days` - 允许的最大交易日中断天数

【合规提示】本功能仅用于量化研究回测，不构成任何投资建议，投资有风险，入市需谨慎
