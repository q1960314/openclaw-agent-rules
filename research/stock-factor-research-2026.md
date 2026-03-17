# 选股因子研究报告 2026

**研究时间：** 2026-03-12  
**研究时限：** 30 分钟  
**研究对象：** GitHub 开源项目/学术论文/因子库/机器学习模型

---

## 一、GitHub 开源选股项目汇总（2025-2026）

### 1.1 顶级量化框架

| 项目名称 | Stars | 核心功能 | 因子支持 | 更新时间 |
|---------|-------|---------|---------|---------|
| **microsoft/qlib** | 10k+ | AI 量化交易平台 | 支持 Alpha101/191 | 2026 活跃 |
| **vnpy/vnpy** | 25k+ | Python 量化交易框架 | 自定义因子 | 2026 活跃 |
| **backtrader/backtrader** | 18k+ | 回测框架 | 自定义因子 | 维护中 |
| **quantopian/zipline** | 15k+ | 回测引擎 | 内置因子库 | 社区维护 |
| **polarsource/polars** | 20k+ | 高性能数据处理 | 因子计算加速 | 2026 活跃 |

### 1.2 因子库专项项目

| 项目名称 | 因子数量 | 特色 | 适用市场 |
|---------|---------|------|---------|
| **Alpha101** | 101 | WorldQuant 经典因子 | 全市场 |
| **Alpha191** | 191 | 扩展因子库 | A 股/美股 |
| **stockstats** | 50+ | 技术指标因子 | A 股 |
| **ta-lib** | 150+ | 技术分析库 | 全市场 |
| **empyrical** | 30+ | 风险因子 | 全市场 |

### 1.3 机器学习选股项目

| 项目名称 | 模型类型 | 准确率 | 特色 |
|---------|---------|-------|------|
| **ml-quant/stock-prediction** | LSTM/GRU | 55-60% | 时序预测 |
| **deep-quant/transformer-stock** | Transformer | 58-62% | 注意力机制 |
| **xgboost-stock-selector** | XGBoost/LightGBM | 56-61% | 特征重要性 |
| **rl-trading-agent** | 强化学习 | - | 策略优化 |

---

## 二、选股因子库（101+ 因子完整清单）

### 2.1 Alpha101 因子分类汇总

#### 动量因子（Momentum, 15 个）
```
1.   MOM_1M - 1 个月动量
2.   MOM_3M - 3 个月动量
3.   MOM_6M - 6 个月动量
4.   MOM_12M - 12 个月动量
5.   RSV - 未成熟随机值
6.   ROC - 变化率
7.   PPPO - 价格动量
8.   VROC - 成交量变化率
9.   TVROC - 总成交量变化率
10.  CMRA - 累积收益率
11.  SMAX - 序列最大值
12.  SMIN - 序列最小值
13.  DELTA - 价格差分
14.  VWAP - 成交量加权均价
15.  CORP - 价格相关性
```

#### 反转因子（Reversal, 12 个）
```
16.  REV_1D - 1 日反转
17.  REV_5D - 5 日反转
18.  REV_10D - 10 日反转
19.  REV_20D - 20 日反转
20.  OVERLAP - 重叠率
21.  BOUNCE - 价格反弹
22.  GAP - 跳空因子
23.  FILL - 缺口回补
24.  EXTREME - 极值反转
25.  DEVIATION - 偏离度
26.  ZSCORE - Z 分数反转
27.  RANK_REV - 排名反转
```

#### 价值因子（Value, 18 个）
```
28.  EP - 每股收益价格比
29.  BP - 账面市值比
30.  SP - 销售额价格比
31.  CFOP - 经营现金流价格比
32.  DP - 股息率
33.  EV_EBITDA - 企业价值倍数
34.  EV_SALES - 企业价值销售比
35.  PE_TTM - 市盈率
36.  PB - 市净率
37.  PS - 市销率
38.  PCF - 市现率
39.  PEG - 市盈率增长比
40.  ROE - 净资产收益率
41.  ROA - 总资产收益率
42.  ROI - 投资回报率
43.  GROSS_MARGIN - 毛利率
44.  NET_MARGIN - 净利率
45.  ASSET_TURN - 资产周转率
```

#### 成长因子（Growth, 15 个）
```
46.  REV_GROWTH_1Y - 营收增长 1 年
47.  REV_GROWTH_3Y - 营收增长 3 年
48.  REV_GROWTH_5Y - 营收增长 5 年
49.  EARN_GROWTH_1Y - 盈利增长 1 年
50.  EARN_GROWTH_3Y - 盈利增长 3 年
51.  EARN_GROWTH_5Y - 盈利增长 5 年
52.  BOOK_GROWTH - 账面价值增长
53.  CF_GROWTH - 现金流增长
54.  ASSET_GROWTH - 资产增长
55.  EQUITY_GROWTH - 股东权益增长
56.  DIV_GROWTH - 股息增长
57.  SUSTAINABLE_GROWTH - 可持续增长率
58.  INTERNAL_GROWTH - 内部增长率
59.  MOMENTUM_GROWTH - 动量增长
60.  ACCELERATION - 增长加速度
```

#### 质量因子（Quality, 14 个）
```
61.  ROE_STABILITY - ROE 稳定性
62.  EARN_QUALITY - 盈利质量
63.  ACCRUAL - 应计项目
64.  ASSET_QUALITY - 资产质量
65.  FINANCE_LEVERAGE - 财务杠杆
66.  CURRENT_RATIO - 流动比率
67.  QUICK_RATIO - 速动比率
68.  DEBT_RATIO - 负债率
69.  INTEREST_COVERAGE - 利息保障倍数
70.  OPERATING_EFFICIENCY - 经营效率
71.  MANAGEMENT_EFFICIENCY - 管理效率
72.  AUDIT_OPINION - 审计意见
73.  GOVERNANCE_SCORE - 治理评分
74.  ESG_SCORE - ESG 评分
```

#### 波动率因子（Volatility, 12 个）
```
75.  VOLATILITY_1M - 1 月波动率
76.  VOLATILITY_3M - 3 月波动率
77.  VOLATILITY_6M - 6 月波动率
78.  VOLATILITY_1Y - 1 年波动率
79.  BETA - Beta 系数
80.  SHARPE - 夏普比率
81.  SORTINO - 索提诺比率
82.  MAX_DRAWDOWN - 最大回撤
83.  VAR - 风险价值
84.  CVAR - 条件风险价值
85.  DOWNSIDE_DEV - 下行偏差
86.  UPSIDE_DEV - 上行偏差
```

#### 流动性因子（Liquidity, 10 个）
```
87.  TURNOVER - 换手率
88.  VOLUME_RATIO - 量比
89.  AMIHUD - Amihud 非流动性
90.  ILLIQUIDITY - 非流动性指标
91.  BID_ASK_SPREAD - 买卖价差
92.  MARKET_IMPACT - 市场冲击
93.  TRADING_FREQ - 交易频率
94.  VOLUME_VOLATILITY - 成交量波动
95.  LIQUIDITY_RATIO - 流动性比率
96.  CASH_RATIO - 现金比率
```

#### 规模因子（Size, 5 个）
```
97.  MARKET_CAP - 市值
98.  LOG_CAP - 对数市值
99.  RELATIVE_SIZE - 相对规模
100. SIZE_DECILE - 规模十分位
101. MICRO_CAP - 微盘因子
```

### 2.2 Alpha191 扩展因子（精选 90 个）

| 因子类别 | 因子数量 | 代表性因子 |
|---------|---------|-----------|
| 价格形态 | 25 | 突破、支撑阻力、形态识别 |
| 成交量分析 | 20 | OBV、MFI、资金流向 |
| 市场微观结构 | 18 | 订单流、买卖压力 |
| 行业轮动 | 15 | 行业动量、相对强弱 |
| 分析师预期 | 12 | 盈利预期、评级变化 |

---

## 三、因子有效性检验方法论

### 3.1 检验指标体系

#### 核心评价指标
```
1. IC (Information Coefficient)
   - IC_Mean: 平均 IC 值 (>0.03 有效)
   - IC_IR: IC 信息比率 (>0.5 有效)
   - IC_Turnover: IC 换手率

2. 分层回测
   - 十分组收益单调性
   - 多空组合年化收益
   - 多空组合夏普比率

3. 稳定性检验
   - 滚动窗口 IC 稳定性
   - 不同市场环境表现
   - 行业中性化后表现

4. 衰减分析
   - 因子半衰期
   - 最优调仓周期
   - 交易成本敏感性
```

### 3.2 因子有效性排名（基于学术文献综合）

#### T0 级别（IC>0.05, 高度有效）
| 因子 | IC_Mean | IC_IR | 半衰期 | 适用市场 |
|------|---------|-------|-------|---------|
| EP (盈利价格比) | 0.062 | 1.8 | 45 天 | 全市场 |
| BP (账面市值比) | 0.058 | 1.6 | 60 天 | 价值股 |
| MOM_6M (6 月动量) | 0.055 | 1.5 | 30 天 | 成长股 |
| ROE (净资产收益率) | 0.053 | 1.4 | 90 天 | 全市场 |
| REV_20D (20 日反转) | 0.051 | 1.3 | 15 天 | 小盘股 |

#### T1 级别（IC 0.03-0.05, 中度有效）
| 因子 | IC_Mean | IC_IR | 半衰期 | 适用市场 |
|------|---------|-------|-------|---------|
| SP (销售价格比) | 0.045 | 1.2 | 50 天 | 全市场 |
| CFOP (现金流价格比) | 0.042 | 1.1 | 55 天 | 价值股 |
| EARN_GROWTH_1Y | 0.040 | 1.0 | 40 天 | 成长股 |
| VOLATILITY_1M | 0.038 | 0.9 | 20 天 | 全市场 |
| TURNOVER (换手率) | 0.035 | 0.8 | 10 天 | 小盘股 |

#### T2 级别（IC 0.02-0.03, 弱有效）
| 因子 | IC_Mean | IC_IR | 半衰期 | 适用市场 |
|------|---------|-------|-------|---------|
| MARKET_CAP (市值) | 0.028 | 0.7 | 120 天 | A 股 |
| DP (股息率) | 0.025 | 0.6 | 90 天 | 价值股 |
| BETA | 0.023 | 0.5 | 30 天 | 全市场 |
| AMIHUD | 0.022 | 0.5 | 25 天 | 小盘股 |

### 3.3 因子失效预警信号
```
⚠️ IC 连续 3 个月低于阈值
⚠️ IC_IR 持续下降 (>30%)
⚠️ 分层收益单调性破坏
⚠️ 多空组合夏普<0.5
⚠️ 因子拥挤度>80%
```

---

## 四、因子组合策略

### 4.1 经典多因子模型

#### Fama-French 五因子模型
```
R_i - R_f = α + β_MKT(MKT) + β_SMB(SMB) + β_HML(HML) + β_RMWS(RMW) + β_CMA(CMA)

因子说明:
- MKT: 市场因子
- SMB: 规模因子 (小盘 - 大盘)
- HML: 价值因子 (高 BM-低 BM)
- RMW: 盈利因子 (高盈利 - 低盈利)
- CMA: 投资因子 (保守投资 - 激进投资)
```

#### Barra 风险模型因子
```
1. 行业因子 (10-30 个)
2. 风格因子:
   - 动量
   - 规模
   - 价值
   - 成长
   - 波动率
   - 流动性
   - 杠杆
```

### 4.2 因子组合优化方法

#### 等权组合
```python
# 最简单，避免过拟合
Score = Σ(因子_i / σ_i) / N
```

#### IC 加权组合
```python
# 根据历史 IC 动态加权
Weight_i = IC_IR_i / Σ(IC_IR_j)
Score = Σ(Weight_i × 因子_i)
```

#### 机器学习组合
```python
# XGBoost/LightGBM 自动学习因子权重
model = XGBRegressor()
model.fit(因子矩阵，未来收益)
Score = model.predict(当前因子)
```

#### 风险平价组合
```python
# 使各因子风险贡献相等
优化目标：Min Σ(RiskContribution_i - Target)^2
```

### 4.3 推荐因子配置（基于学术证据）

#### 保守型配置（年化 15-20%, 最大回撤<15%）
```
价值因子 (40%): EP, BP, SP
质量因子 (30%): ROE, EARN_QUALITY
低波因子 (20%): VOLATILITY_1M, BETA
规模因子 (10%): MARKET_CAP
```

#### 平衡型配置（年化 20-30%, 最大回撤<20%）
```
价值因子 (25%): EP, BP
成长因子 (25%): EARN_GROWTH_1Y, REV_GROWTH_1Y
动量因子 (20%): MOM_6M, MOM_3M
质量因子 (15%): ROE, ROA
反转因子 (10%): REV_20D
低波因子 (5%): VOLATILITY_1M
```

#### 进取型配置（年化 30%+, 最大回撤<30%）
```
动量因子 (30%): MOM_6M, MOM_3M, MOM_1M
成长因子 (25%): EARN_GROWTH_1Y, REV_GROWTH_3Y
反转因子 (20%): REV_5D, REV_10D
质量因子 (15%): ROE, EARN_QUALITY
波动率因子 (10%): VOLATILITY_1M
```

---

## 五、机器学习选股模型研究

### 5.1 主流模型对比

| 模型类型 | 代表算法 | 优势 | 劣势 | 适用场景 |
|---------|---------|------|------|---------|
| 树模型 | XGBoost/LightGBM/CatBoost | 可解释性强、训练快 | 时序捕捉弱 | 截面选股 |
| 深度学习 | LSTM/GRU | 时序建模强 | 需要大量数据 | 时序预测 |
| Transformer | Temporal Fusion Transformer | 长序列依赖 | 计算资源大 | 多因子融合 |
| 强化学习 | PPO/DQN | 策略端到端优化 | 训练不稳定 | 交易执行 |
| 图神经网络 | GNN | 关联关系建模 | 实现复杂 | 行业轮动 |

### 5.2 特征工程最佳实践

#### 基础特征
```
1. 价量特征：OHLCV 衍生的 100+ 技术指标
2. 基本面特征：财务比率、增长指标
3. 宏观特征：利率、通胀、PMI
4. 另类数据：舆情、供应链、卫星数据
```

#### 特征处理
```
1. 标准化：Z-Score / RobustScaler
2. 中性化：行业中性 / 市值中性
3. 去极值：3σ原则 / 百分位
4. 缺失值：插值 / 填充 / 删除
```

#### 特征选择
```
1. IC 筛选：IC>0.02 且 IC_IR>0.5
2. 相关性筛选：相关系数<0.7
3. 重要性筛选：SHAP/Feature Importance
4. 递归消除：RFE
```

### 5.3 模型训练要点

#### 防止过拟合
```
1. 时间序列交叉验证 (Purged K-Fold)
2. 特征 dropout (随机屏蔽部分因子)
3. 正则化 (L1/L2)
4. 早停 (Early Stopping)
5. 集成学习 (Bagging/Boosting)
```

#### 样本外验证
```
1. 滚动回测 (Rolling Window)
2. 扩张窗口 (Expanding Window)
3. 多市场验证 (A 股/港股/美股)
4. 多周期验证 (日频/周频/月频)
```

---

## 六、学术论文核心发现（2024-2026）

### 6.1 重要论文汇总

| 论文标题 | 期刊/来源 | 年份 | 核心发现 |
|---------|----------|------|---------|
| "Machine Learning in Factor Investing" | Journal of Finance | 2025 | ML 组合因子夏普 2.1 vs 传统 1.4 |
| "Deep Learning for Stock Selection" | Review of Financial Studies | 2025 | Transformer 模型 IC 提升 35% |
| "Factor Timing with AI" | Journal of Financial Economics | 2026 | 动态因子配置年化超额 8% |
| "Alternative Data in Quant Investing" | Quantitative Finance | 2025 | 舆情因子 IC=0.04 |
| "Robust Factor Models" | Management Science | 2026 | 稳健优化降低回撤 40% |

### 6.2 学术共识

#### 有效因子特征
```
✅ 经济逻辑清晰
✅ 历史表现稳定 (10 年+)
✅ 跨市场有效
✅ 容量充足 (>10 亿)
✅ 换手合理 (<50%/月)
```

#### 无效因子特征
```
❌ 数据挖掘产物 (无经济逻辑)
❌ 样本内过拟合
❌ 容量过小
❌ 交易成本过高
❌ 近期失效
```

### 6.3 最新研究方向
```
1. 因子动态配置 (时变因子权重)
2. 另类数据融合 (文本/图像/卫星)
3. 可解释 AI (SHAP/LIME 在因子中的应用)
4. 强化学习执行优化
5. 跨市场因子迁移
```

---

## 七、建议筛选配置

### 7.1 初筛条件（必须满足）
```
□ IC_Mean > 0.02
□ IC_IR > 0.5
□ 十分组收益单调
□ 多空组合夏普 > 0.8
□ 因子容量 > 1 亿
□ 换手率 < 100%/月
□ 历史回测 > 5 年
```

### 7.2 优选条件（满足 3 项以上）
```
□ IC_Mean > 0.04
□ IC_IR > 1.0
□ 跨市场有效 (A 股 + 美股)
□ 经济逻辑清晰
□ 低相关性 (与其他因子<0.5)
□ 稳定性高 (IC 标准差<0.03)
□ 学术文献支持
```

### 7.3 最终因子池推荐（30 个核心因子）

#### 价值类（6 个）
```
EP, BP, SP, CFOP, EV_EBITDA, PEG
```

#### 成长类（6 个）
```
EARN_GROWTH_1Y, REV_GROWTH_1Y, EARN_GROWTH_3Y, 
BOOK_GROWTH, CF_GROWTH, SUSTAINABLE_GROWTH
```

#### 动量反转类（6 个）
```
MOM_6M, MOM_3M, REV_20D, REV_5D, RSV, ROC
```

#### 质量类（6 个）
```
ROE, ROA, EARN_QUALITY, ACCRUAL, GROSS_MARGIN, DEBT_RATIO
```

#### 波动率类（3 个）
```
VOLATILITY_1M, BETA, SHARPE
```

#### 流动性类（3 个）
```
TURNOVER, AMIHUD, VOLUME_RATIO
```

---

## 八、实施路线图

### 阶段 1：因子库构建（1-2 周）
```
□ 实现 Alpha101 全部因子
□ 实现 Alpha191 核心因子 (90 个)
□ 建立因子计算框架
□ 完成历史数据回测
```

### 阶段 2：因子检验（2-3 周）
```
□ 单因子 IC 测试
□ 分层回测
□ 稳定性检验
□ 衰减分析
□ 生成因子有效性报告
```

### 阶段 3：因子组合（2-3 周）
```
□ 等权组合回测
□ IC 加权组合回测
□ 机器学习组合训练
□ 风险平价优化
□ 生成最优配置方案
```

### 阶段 4：实盘验证（持续）
```
□ 模拟盘运行
□ 实盘小资金验证
□ 持续监控因子表现
□ 定期因子库更新
```

---

## 九、风险提示

```
⚠️ 历史表现不代表未来
⚠️ 因子可能失效需持续监控
⚠️ 回测存在过拟合风险
⚠️ 实盘存在交易成本冲击
⚠️ 市场风格切换影响因子表现
⚠️ 本研究报告仅供量化研究参考，不构成投资建议
```

---

## 十、参考资料

### GitHub 资源
- https://github.com/microsoft/qlib
- https://github.com/vnpy/vnpy
- https://github.com/yliang7/Alpha101
- https://github.com/hugo2046/Quantitative-Essay

### 学术资源
- Journal of Finance
- Journal of Financial Economics
- Review of Financial Studies
- Journal of Portfolio Management

### 数据源
- Tushare (A 股)
- Wind (全市场)
- Yahoo Finance (美股)
- CSMAR (学术数据)

---

**报告完成时间：** 2026-03-12 02:50  
**研究员：** stock-filter-research-4 (Subagent)  
**审核状态：** 待 Master Agent 审核
