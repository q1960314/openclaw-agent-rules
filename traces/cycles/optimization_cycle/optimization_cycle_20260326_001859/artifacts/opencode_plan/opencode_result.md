# OpenCode Optimization Plan

## 1. Diagnosis
# OpenCode Optimization Plan

## 1. Diagnosis

根据分析，smoke_backtest出现负面收益(-0.1715)、负夏普(-4.4467)和较大回撤(0.1693)的根本原因是：

**策略参数未经优化** - 当前系统虽具备贝叶斯优化能力，但参数仍使用默认配置，未能适应回测期间的市场环境。主要问题包括：
- 固定风险参数(止损-6%，止盈+12%)不适用于特定市场周期
- 策略权重分配不当，单一策略失效影响整体表现
- 缺乏动态风控和市场状态感知

## 2. Minimal Change Path

1. **立即参数优化** - 使用现有贝叶斯优化器对关键参数进行寻优
2. **策略权重调整** - 在多策略融合引擎中动态调整权重配比
3. **风控参数微调** - 基于回测结果调整止损、止盈阈值
4. **市场状态检测** - 启用动态风险管理模式

## 3. Files To Touch

- `/data/agents/master/modules/param_optimizer.py` - 参数优化器配置
- `/data/agents/master/fetch_data_optimized.py` - 策略核心参数
- `/data/agents/master/run_backtest_v4.py` - 回测配置调整
- `/data/agents/master/modules/backtest_engine.py` - 风控参数优化
- `/data/agents/master/modules/strategy_core.py` - 策略评分参数

## 4. Validation Plan

1. **分阶段回测验证** - 运行30天滚动窗口回测检验稳定性
2. **参数敏感性测试** - 验证优化参数的鲁棒性
3. **样本外测试** - 在未参与训练的数据上验证表现
4. **对比基准测试** - 与基准策略比较关键指标

## 5. Approval Gates

- **策略参数变更** - 需人工审批参数优化结果
- **风控阈值调整** - 需确认新的止损止盈设置
- **实盘应用** - 所有改动仅限回测使用，不得直接应用实盘
- **参数空间定义** - 需审批贝叶斯优化的参数边界