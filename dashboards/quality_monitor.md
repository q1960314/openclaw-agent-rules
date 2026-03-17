# 📊 数据质量监控面板

**版本：** v1.0  
**创建时间：** 2026-03-12  
**更新频率：** 实时/每日

---

## 🎯 核心指标概览

| 指标 | 当前值 | 目标值 | 状态 | 趋势 |
|------|--------|--------|------|------|
| **综合质量评分** | {{overall_score}} | ≥90 | {{overall_status}} | {{overall_trend}} |
| 完整性得分 | {{completeness_score}} | ≥95 | {{completeness_status}} | {{completeness_trend}} |
| 准确性得分 | {{accuracy_score}} | ≥95 | {{accuracy_status}} | {{accuracy_trend}} |
| 股票列表完整性 | {{stock_completeness}}% | 100% | {{stock_status}} | {{stock_trend}} |
| 日期连续性 | {{date_continuity}}% | ≥98% | {{date_status}} | {{date_trend}} |
| 问题数据数量 | {{issues_count}} | 0 | {{issues_status}} | {{issues_trend}} |

---

## 📈 质量趋势图

### 综合质量趋势（近 30 天）

```
日期        完整性  准确性  综合
2026-02-11   98      97      97.5
2026-02-12   98      97      97.5
2026-02-13   97      96      96.5
...
2026-03-12   {{completeness_score}}  {{accuracy_score}}  {{overall_score}}
```

**趋势分析：**
- 完整性：{{completeness_trend_analysis}}
- 准确性：{{accuracy_trend_analysis}}
- 综合：{{overall_trend_analysis}}

---

## 📊 完整性监控

### 1.1 股票列表完整性

| 指标 | 数值 | 状态 |
|------|------|------|
| 官方股票数 | {{official_count}} | - |
| 本地股票数 | {{local_count}} | - |
| 缺失股票数 | {{missing_count}} | {{missing_status}} |
| 多余股票数 | {{extra_count}} | {{extra_status}} |
| **完整性** | **{{completeness_rate}}%** | {{completeness_badge}} |

#### 缺失股票 TOP10
| 股票代码 | 股票名称 | 缺失天数 | 优先级 |
|----------|----------|----------|--------|
{{missing_stocks_table}}

---

### 1.2 日期连续性

| 指标 | 数值 | 状态 |
|------|------|------|
| 实际交易日 | {{actual_days}} | - |
| 预期交易日 | {{expected_days}} | - |
| 缺失交易日 | {{missing_days}} | {{missing_days_status}} |
| **连续性** | **{{continuity_rate}}%** | {{continuity_badge}} |

#### 缺失交易日分布
| 缺失天数范围 | 股票数量 | 占比 |
|--------------|----------|------|
| 1-5 天 | {{missing_1_5}} | {{missing_1_5_rate}}% |
| 6-10 天 | {{missing_6_10}} | {{missing_6_10_rate}}% |
| 11-20 天 | {{missing_11_20}} | {{missing_11_20_rate}}% |
| >20 天 | {{missing_above_20}} | {{missing_above_20_rate}}% |

---

### 1.3 字段完整性

| 字段 | 存在率 | 空值率 | 状态 |
|------|--------|--------|------|
| ts_code | {{ts_code_exist_rate}}% | {{ts_code_null_rate}}% | {{ts_code_badge}} |
| trade_date | {{trade_date_exist_rate}}% | {{trade_date_null_rate}}% | {{trade_date_badge}} |
| open | {{open_exist_rate}}% | {{open_null_rate}}% | {{open_badge}} |
| high | {{high_exist_rate}}% | {{high_null_rate}}% | {{high_badge}} |
| low | {{low_exist_rate}}% | {{low_null_rate}}% | {{low_badge}} |
| close | {{close_exist_rate}}% | {{close_null_rate}}% | {{close_badge}} |
| vol | {{vol_exist_rate}}% | {{vol_null_rate}}% | {{vol_badge}} |

---

## 🎯 准确性监控

### 2.1 价格合理性

| 指标 | 数值 | 状态 |
|------|------|------|
| 检查记录数 | {{price_check_records}} | - |
| 价格错误数 | {{price_errors}} | {{price_errors_status}} |
| 逻辑错误数 | {{logic_errors}} | {{logic_errors_status}} |
| **错误率** | **{{price_error_rate}}%** | {{price_error_badge}} |

#### 价格错误分布
| 错误类型 | 数量 | 占比 |
|----------|------|------|
| 价格<0 | {{price_below_zero}} | {{price_below_zero_rate}}% |
| 价格>10000 | {{price_above_max}} | {{price_above_max_rate}}% |
| high < low | {{high_less_low}} | {{high_less_low_rate}}% |
| high < open/close | {{high_less_open_close}} | {{high_less_open_close_rate}}% |

---

### 2.2 涨跌幅准确性

| 指标 | 数值 | 状态 |
|------|------|------|
| 计算记录数 | {{calc_change_records}} | - |
| 正常涨跌幅 | {{normal_changes}} | - |
| 异常涨跌幅 | {{abnormal_changes}} | {{abnormal_status}} |
| **异常率** | **{{abnormal_rate}}%** | {{abnormal_badge}} |

#### 异常涨跌幅明细（前 20 条）
| 股票代码 | 交易日期 | 涨跌幅 | 市场类型 | 状态 |
|----------|----------|--------|----------|------|
{{abnormal_changes_table}}

---

### 2.3 涨跌停价验证

| 市场 | 限制幅度 | 涨停次数 | 跌停次数 | 超限次数 | 有效率 |
|------|----------|----------|----------|----------|--------|
| 主板 | 10% | {{main_limit_up}} | {{main_limit_down}} | {{main_invalid}} | {{main_valid_rate}}% |
| 创业板 | 20% | {{chinext_limit_up}} | {{chinext_limit_down}} | {{chinext_invalid}} | {{chinext_valid_rate}}% |
| 科创板 | 20% | {{star_limit_up}} | {{star_limit_down}} | {{star_invalid}} | {{star_valid_rate}}% |

---

## ⚠️ 异常数据监控

### 3.1 异常数据分布

| 异常类型 | P0 级 | P1 级 | P2 级 | 合计 |
|----------|-------|-------|-------|------|
| 完整性异常 | {{p0_integrity}} | {{p1_integrity}} | {{p2_integrity}} | {{total_integrity}} |
| 准确性异常 | {{p0_accuracy}} | {{p1_accuracy}} | {{p2_accuracy}} | {{total_accuracy}} |
| 一致性异常 | {{p0_consistency}} | {{p1_consistency}} | {{p2_consistency}} | {{total_consistency}} |
| **合计** | **{{total_p0}}** | **{{total_p1}}** | **{{total_p2}}** | **{{grand_total}}** |

---

### 3.2 待处理异常清单

#### P0 级（立即处理）
| 异常 ID | 类型 | 影响股票 | 发现时间 | 处理状态 |
|---------|------|----------|----------|----------|
{{p0_issues_table}}

#### P1 级（24 小时内处理）
| 异常 ID | 类型 | 影响股票 | 发现时间 | 处理状态 |
|---------|------|----------|----------|----------|
{{p1_issues_table}}

#### P2 级（7 天内处理）
| 异常 ID | 类型 | 影响股票 | 发现时间 | 处理状态 |
|---------|------|----------|----------|----------|
{{p2_issues_table}}

---

## 📋 质量报告历史

### 最近 10 次检查

| 检查时间 | 完整性 | 准确性 | 综合 | 评级 | 问题数 | 报告 |
|----------|--------|--------|------|------|--------|------|
{{report_history_table}}

---

## 🔧 快速操作

### 运行数据质量检查

```bash
# 完整检查（抽样 10 只股票）
python scripts/data_quality_validator.py

# 检查指定股票
python scripts/data_quality_validator.py --stock 000001.SZ

# 检查特定项目
python scripts/data_quality_validator.py --check price_validity
```

### 查看历史报告

```bash
# 查看最新报告
ls -lt data/quality_reports/ | head -10

# 查看特定报告
cat data/quality_reports/quality_report_20260312_020000.md
```

### 导出质量数据

```bash
# 导出 JSON 格式
python scripts/data_quality_validator.py --output json

# 导出 CSV 格式
python scripts/data_quality_validator.py --output csv
```

---

## 📊 质量分级标准

### 综合评级

| 评级 | 分数范围 | 说明 | 处理建议 |
|------|----------|------|----------|
| **A** | 90-100 | 优秀 | 正常使用 |
| **B** | 80-89 | 良好 | 可正常使用，关注小问题 |
| **C** | 70-79 | 一般 | 建议修复后使用 |
| **D** | 60-69 | 较差 | 需要全面修复 |
| **F** | <60 | 不合格 | 禁止使用，立即修复 |

### 单项指标标准

| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| 完整性 | ≥98% | ≥95% | ≥90% | <90% |
| 准确性 | ≥98% | ≥95% | ≥90% | <90% |
| 连续性 | ≥99% | ≥97% | ≥95% | <95% |
| 错误率 | <0.1% | <0.5% | <1% | ≥1% |

---

## 📈 质量目标

### 2026 年 Q1 目标

| 指标 | 当前值 | 目标值 | 差距 |
|------|--------|--------|------|
| 综合质量评分 | {{current_overall}} | 95 | {{overall_gap}} |
| 完整性得分 | {{current_completeness}} | 98 | {{completeness_gap}} |
| 准确性得分 | {{current_accuracy}} | 97 | {{accuracy_gap}} |
| P0 级异常 | {{current_p0}} | 0 | {{p0_gap}} |
| P1 级异常 | {{current_p1}} | <5 | {{p1_gap}} |

### 改进计划

1. **短期（1 周内）**
   - 修复所有 P0 级异常
   - 补充缺失股票数据
   - 优化数据抓取逻辑

2. **中期（1 个月内）**
   - 降低 P1 级异常至<5 个
   - 提升完整性至≥98%
   - 建立自动化监控

3. **长期（1 季度内）**
   - 综合质量稳定在 A 级
   - 建立数据质量预警机制
   - 实现零 P0 级异常

---

## 📎 附录

### A. 监控指标说明

1. **完整性得分**
   - 计算公式：(股票完整性×40% + 日期连续性×30% + 字段完整性×30%)
   - 数据来源：data_quality_validator.py

2. **准确性得分**
   - 计算公式：(价格合理性×40% + 涨跌幅准确性×30% + 涨跌停验证×30%)
   - 数据来源：data_quality_validator.py

3. **综合得分**
   - 计算公式：(完整性×50% + 准确性×50%)
   - 评级标准：A(≥90), B(≥80), C(≥70), D(≥60), F(<60)

### B. 数据更新说明

- **更新频率：** 每日 02:00 自动更新
- **数据来源：** data/quality_reports/ 目录下的最新报告
- **手工更新：** 运行 `python scripts/data_quality_validator.py`

### C. 告警阈值

| 指标 | 警告阈值 | 严重阈值 |
|------|----------|----------|
| 综合得分 | <85 | <70 |
| 完整性 | <95% | <90% |
| 准确性 | <95% | <90% |
| P0 级异常 | >0 | >5 |
| P1 级异常 | >10 | >20 |

---

**监控面板维护：** master-quant 生态  
**最后更新：** 2026-03-12  
**下次更新：** 2026-03-13 02:00  
**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎
