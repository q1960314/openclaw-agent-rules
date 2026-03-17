# 📊 数据质量检查报告

**报告编号：** {{report_id}}  
**生成时间：** {{timestamp}}  
**检查范围：** {{check_scope}}  
**数据版本：** {{data_version}}

---

## 📋 执行摘要

| 指标 | 数值 | 状态 |
|------|------|------|
| 检查股票数量 | {{total_stocks}} | - |
| 数据记录总数 | {{total_records}} | - |
| 发现问题数量 | {{issues_count}} | {{issues_status}} |
| 完整性得分 | {{completeness_score}} | {{completeness_status}} |
| 准确性得分 | {{accuracy_score}} | {{accuracy_status}} |
| **综合质量评分** | **{{overall_score}}** | **{{quality_grade}}** |

### 质量评级说明
- **A (90-100 分)**: 数据质量优秀，可直接用于策略回测
- **B (80-89 分)**: 数据质量良好，少量问题不影响整体使用
- **C (70-79 分)**: 数据质量一般，建议修复后使用
- **D (60-69 分)**: 数据质量较差，需要全面修复
- **F (<60 分)**: 数据质量不合格，不建议使用

---

## 1️⃣ 数据完整性检查

### 1.1 股票列表完整性

**检查目标：** 对比 Tushare 官方股票列表，确保无缺失

| 指标 | 数值 |
|------|------|
| 本地股票数量 | {{local_stock_count}} |
| 官方股票数量 | {{official_stock_count}} |
| 缺失股票数量 | {{missing_stock_count}} |
| 多余股票数量 | {{extra_stock_count}} |
| **完整性比例** | **{{stock_completeness_rate}}%** |

#### 缺失股票清单（前 50 只）
{{missing_stocks_list}}

#### 多余股票清单（可能已退市）
{{extra_stocks_list}}

---

### 1.2 日期连续性检查

**检查目标：** 确保交易日数据无缺失

| 指标 | 数值 |
|------|------|
| 实际交易日数 | {{actual_trading_days}} |
| 预期交易日数 | {{expected_trading_days}} |
| 缺失交易日数 | {{missing_days_count}} |
| **连续性比例** | **{{continuity_rate}}%** |

#### 缺失交易日（前 20 天）
{{missing_dates_list}}

#### 长期间断（>5 个交易日）
{{gap_periods_list}}

---

### 1.3 字段完整性检查

**检查目标：** 确保必填字段无缺失、空值率合理

#### 基础字段检查
| 字段 | 存在性 | 空值率 | 状态 |
|------|--------|--------|------|
| ts_code | {{ts_code_exists}} | {{ts_code_null_rate}}% | {{ts_code_status}} |
| trade_date | {{trade_date_exists}} | {{trade_date_null_rate}}% | {{trade_date_status}} |
| open | {{open_exists}} | {{open_null_rate}}% | {{open_status}} |
| high | {{high_exists}} | {{high_null_rate}}% | {{high_status}} |
| low | {{low_exists}} | {{low_null_rate}}% | {{low_status}} |
| close | {{close_exists}} | {{close_null_rate}}% | {{close_status}} |
| vol | {{vol_exists}} | {{vol_null_rate}}% | {{vol_status}} |

#### 策略特定字段检查
{{strategy_fields_table}}

---

## 2️⃣ 数据准确性验证

### 2.1 价格合理性检查

**检查目标：** 验证价格在有效范围内，开高低收关系正确

| 指标 | 数值 |
|------|------|
| 检查记录数 | {{price_check_records}} |
| 价格超出范围记录 | {{price_out_of_range_count}} |
| 价格逻辑错误记录 | {{price_logic_error_count}} |
| **错误率** | **{{price_error_rate}}%** |

#### 价格范围统计
| 价格类型 | <0.01 数量 | >10000 数量 |
|----------|-----------|------------|
| open | {{open_below_min}} | {{open_above_max}} |
| high | {{high_below_min}} | {{high_above_max}} |
| low | {{low_below_min}} | {{low_above_max}} |
| close | {{close_below_min}} | {{close_above_max}} |

---

### 2.2 成交量/额匹配检查

**检查目标：** 验证成交量与成交额变化方向一致

| 指标 | 数值 |
|------|------|
| 检查记录数 | {{volume_check_records}} |
| 匹配记录数 | {{matched_records}} |
| 不匹配记录数 | {{mismatched_records}} |
| **匹配率** | **{{match_rate}}%** |

---

### 2.3 涨跌幅计算正确性

**检查目标：** 验证涨跌幅计算准确，无异常值

| 指标 | 数值 |
|------|------|
| 计算涨跌幅记录数 | {{calc_change_records}} |
| 正常涨跌幅记录 | {{normal_change_records}} |
| 异常涨跌幅记录 | {{abnormal_change_records}} |
| **异常率** | **{{abnormal_change_rate}}%** |

#### 异常涨跌幅分布
| 涨跌幅范围 | 记录数 | 占比 |
|------------|--------|------|
| >20% | {{change_above_20}} | {{change_above_20_rate}}% |
| 15%-20% | {{change_15_20}} | {{change_15_20_rate}}% |
| <-20% | {{change_below_neg_20}} | {{change_below_neg_20_rate}}% |
| <-15% | {{change_below_neg_15}} | {{change_below_neg_15_rate}}% |

---

## 3️⃣ 异常数据检测

### 3.1 涨停/跌停价验证

**检查目标：** 验证涨跌停价格符合市场规则

| 指标 | 数值 |
|------|------|
| 检查记录数 | {{limit_check_records}} |
| 涨停记录数 | {{limit_up_count}} |
| 跌停记录数 | {{limit_down_count}} |
| 超出涨跌停限制 | {{invalid_limit_count}} |
| **有效率** | **{{limit_valid_rate}}%** |

#### 分市场涨跌停限制
| 市场 | 限制幅度 | 涨停次数 | 跌停次数 |
|------|----------|----------|----------|
| 主板 | 10% | {{main_limit_up}} | {{main_limit_down}} |
| 创业板 | 20% | {{chinext_limit_up}} | {{chinext_limit_down}} |
| 科创板 | 20% | {{star_limit_up}} | {{star_limit_down}} |

---

### 3.2 停牌数据标记

**检查目标：** 识别并标记停牌期间数据

| 指标 | 数值 |
|------|------|
| 总交易日数 | {{total_trading_days}} |
| 停牌天数 | {{suspension_days}} |
| **停牌率** | **{{suspension_rate}}%** |

#### 长期停牌期间（>10 天）
{{suspension_periods_list}}

---

### 3.3 除权除息处理

**检查目标：** 识别除权除息事件，确保价格连续性

| 指标 | 数值 |
|------|------|
| 疑似除权除息事件 | {{dividend_events_count}} |
| 价格跳空幅度>15% | {{price_drop_events}} |

#### 疑似除权除息日期
{{dividend_dates_list}}

---

## 4️⃣ 问题数据清单

### 4.1 高优先级问题（需立即修复）

| 序号 | 问题类型 | 影响股票 | 问题描述 | 建议措施 |
|------|----------|----------|----------|----------|
{{high_priority_issues}}

### 4.2 中优先级问题（建议修复）

| 序号 | 问题类型 | 影响股票 | 问题描述 | 建议措施 |
|------|----------|----------|----------|----------|
{{medium_priority_issues}}

### 4.3 低优先级问题（可择机修复）

| 序号 | 问题类型 | 影响股票 | 问题描述 | 建议措施 |
|------|----------|----------|----------|----------|
{{low_priority_issues}}

---

## 5️⃣ 修复建议

### 5.1 立即执行（P0）

{{p0_recommendations}}

### 5.2 近期执行（P1）

{{p1_recommendations}}

### 5.3 长期优化（P2）

{{p2_recommendations}}

---

## 6️⃣ 数据质量趋势

### 6.1 历史对比

| 检查日期 | 完整性得分 | 准确性得分 | 综合得分 | 评级 |
|----------|------------|------------|----------|------|
{{historical_comparison}}

### 6.2 质量趋势图

{{quality_trend_chart}}

---

## 📎 附录

### A. 检查配置

- 数据源：{{data_source}}
- 检查时间范围：{{check_date_range}}
- 抽样比例：{{sample_rate}}%
- 检查脚本版本：{{script_version}}

### B. 技术说明

1. **完整性计算方式：** 
   - 股票列表完整性 = (1 - 缺失股票数/官方股票数) × 100%
   - 日期连续性 = (1 - 缺失交易日数/预期交易日数) × 100%
   - 字段完整性 = 基础字段存在性 × 60% + 策略字段存在性 × 40%

2. **准确性计算方式：**
   - 价格合理性 = 100 - (错误记录数/总记录数 × 100)
   - 涨跌幅准确性 = 100 - (异常涨跌幅记录数/总记录数 × 100)
   - 综合准确性 = 价格合理性 × 50% + 涨跌幅准确性 × 50%

3. **综合评分计算：**
   - 综合得分 = 完整性得分 × 50% + 准确性得分 × 50%

### C. 参考标准

- Tushare 官方数据标准
- 证券交易所交易规则
- 量化回测数据质量要求

---

**报告生成工具：** 数据验证与质检系统 v1.0  
**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎

---

*报告结束*
