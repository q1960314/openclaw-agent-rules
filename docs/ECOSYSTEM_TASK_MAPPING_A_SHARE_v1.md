# 中国A股量化生态循环任务映射（v1）

> 基于：
> - `/home/admin/.openclaw/workspace/master/memory/量化系统完整任务列表_v3.1_深度融合版_20260320.md`
> - `/data/agents/master/量化系统任务列表_阶段3-9_详细版_20260319.md`
> - 最新代码主干（2026-03-24 最近修改）

## 一、目标

把历史任务体系从“阶段式项目计划”映射成“可循环运行的生态系统”。

核心原则：
1. 保留任务列表中的业务目标
2. 结合最新代码判断哪些已经落地
3. 将未完成部分接入现有 cycle
4. OpenCode 只进入优化支线，不进入 daily 主循环

---

## 二、最新代码主干判断

### 已形成主干的部分

1. `fetch_data_optimized.py`
   - 已形成统一配置区
   - 已有运行模式分离（全量抓取/增量抓取/仅回测/每日选股）
   - 已接入 qlib 增强、多策略融合、自动调参、风控、情绪分析等总开关

2. `vnpy_backtest/`
   - 已形成核心回测研究框架
   - 关键模块包含：
     - `backtest_engine.py`
     - `vector_engine.py`
     - `orchestrator.py`
     - `health_check.py`
     - `auto_tune.py`
     - `portfolio_optimizer.py`
     - `risk_engine.py`
     - `attribution.py`

3. `qlib_integration/`
   - 已形成因子增强与缓存能力
   - `factor_cache.py` 表明因子预计算 / 增量更新 / 缓存机制已经开始工程化

### 当前代码结构结论

系统当前已经不再是“纯抓取脚本”，而是：

> **A股数据抓取 + 回测引擎 + 因子增强 + 健康检查 + 自动调参 + 多策略框架**

因此历史任务列表里大量内容，不应再按“从零实现”，而应按：
- 已落地能力
- 需要补齐能力
- 需要接入循环的能力
来重新划分。

---

## 三、任务列表映射结果

## 阶段 0-3：接口 / 数据 / 验证

### 已覆盖 / 部分覆盖
- 运行模式分离（已在 `fetch_data_optimized.py`）
- 数据质量验证（现有 `workflow_data_check.py` + data validation reports）
- 增量/全量抓取模式（代码已存在）
- qlib 因子缓存（已实现）
- 数据清洗/标准化/去重/评分（已有部分报告与脚本痕迹）

### 未完全循环化的
- 3.3.3 自动补充脚本
- 3.3.8 数据版本快照
- 3.3.9 数据备份执行
- 3.3.10 数据质量评分的正式 cycle 接入

### 建议接入
- **daily_data_cycle**
  - 增量抓取
  - 数据校验
  - 数据质量评分
  - 快照/备份
  - 通知

---

## 阶段 4：战法库深度分析

### 已覆盖 / 部分覆盖
- 策略类型已存在：打板 / 缩量潜伏 / 板块轮动 / 多策略融合
- 回测框架已具备战法验证底座
- OpenCode 已可接入 strategy_review / optimization_cycle

### 未完成 / 应放到研究支线
- 4.1.x 大规模战法收集与时效性筛选
- 4.3.x 160 战法验证与综合评分
- 极端行情测试、策略衰减监控、策略归因等需要系统化整理

### 建议接入
- **strategy_research_cycle（周级/按需）**
  - strategy-expert 主导
  - factor-miner / sentiment-analyst 支撑
  - 产出战法候选与筛选结论

---

## 阶段 5：因子库深度分析

### 已覆盖 / 部分覆盖
- qlib integration 已存在
- factor_cache 已存在
- vnpy 回测框架里已开始融合 ML/因子增强思路

### 未完成 / 应放到研究支线
- 5.2.x 因子 IC / ICIR / 容量 / 稳定性标准化产出
- 5.1.12 / 5.1.13 RD-Agent 部署与自动挖掘（当前未接）
- 多因子组合对比与因子衰减监控的正式循环化

### 建议接入
- **factor_research_cycle（周级/按需）**
  - factor-miner 主导
  - qlib 因子缓存支撑
  - 输出因子评分、衰减监控、组合建议

---

## 阶段 6：多维度联动分析框架

### 已覆盖 / 部分覆盖
- `fetch_data_optimized.py` 已有较强配置与评分基础
- `vector_engine.py` / `portfolio_strategy.py` 已具备策略无关化与组合逻辑
- 现有 daily/weekly cycle 已有“问题发现 → 工单 → 派发 → 回执”链路

### 未完成 / 最关键
- 板块资金分析模块正式化
- 板块热度确认模块正式化
- 23维评分系统的统一落盘与接口化
- 选股-风控联动的日级输出

### 建议接入
- **daily_research_cycle 的升级版**
  - 从“快速验证回测”升级为：
    - 市场环境评分
    - 板块/个股联动
    - 选股理由
    - 风控联动

---

## 阶段 7：循环回测框架

### 已覆盖 / 部分覆盖
- `orchestrator.py`
- `health_check.py`
- `auto_tune.py`
- `vector_engine.py`

### 已经很接近的任务
- 7.1.2 参数优化框架
- 7.1.4 样本外验证
- 7.1.5 滚动回测
- 7.1.6 参数衰减监控（已有健康检查思路）

### 建议接入
- **weekly_health_cycle**
  - 继续承担健康检查
  - 后续补：
    - 滚动窗口结果
    - 样本外验证摘要
    - 参数衰减预警

- **optimization_cycle**
  - 现在已建成
  - 当前为 plan 模式
  - 后续接 low-risk validation → build candidate

---

## 阶段 8：每日选股流程

### 当前判断
这是未来最重要的一层，但**现在还不应该直接做成全自动实盘链**。

### 已有基础
- 每日选股模式已在 `fetch_data_optimized.py`
- daily cycle 已有自动调度 / 通知能力
- 策略、回测、风控、评分基础已经存在

### 未完成
- 盘前 / 竞价 / 开盘 / 盘中 / 盘后流程的正式事件化
- 舆情抓取正式接入 daily cycle
- 选股理由/打分/风控输出的稳定模板

### 建议接入
- **daily_pick_cycle（后续）**
  - 先做“研究版每日选股”
  - 不直接连实盘执行
  - 输出候选池 + 理由 + 风险提示 + 建议仓位

---

## 阶段 9：知识沉淀

### 已覆盖 / 部分覆盖
- knowledge-steward 已接入 weekly 工单
- workflow_summary / notify / reports 已有基础
- 每日/每周报告已能自动落盘

### 未完成
- 正式 knowledge_cycle
- 策略优化记录自动归档
- 避坑指南自动沉淀
- 工单、报告、回测结果统一入知识库

### 建议接入
- **knowledge_cycle（每日/每周）**
  - 汇总当前 cycles 的摘要
  - 自动归档到知识库目录
  - 更新避坑指南 / 版本记录

---

## 四、现有 cycle 体系 vs 任务列表映射

### 已存在 cycle
1. `daily_research`
2. `weekly_health`
3. `optimization_cycle`
4. `workflow_cleanup`

### 建议新增 cycle
1. `daily_data_cycle`
2. `strategy_research_cycle`
3. `factor_research_cycle`
4. `daily_pick_cycle`
5. `knowledge_cycle`

---

## 五、OpenCode 在生态里的正确位置

### 不建议
- 把 OpenCode 放进 daily 主循环每次都跑
- 把 OpenCode 作为总控
- 让 OpenCode 直接决定策略或实盘动作

### 建议
- 把 OpenCode 放在 **optimization_cycle / coder 支线**

推荐链路：

`strategy_review / weekly_optimization / data_fix`
→ `coder`
→ `OpenCode(plan/build)`
→ `test-expert`
→ `backtest-engine`
→ `summary`
→ `notify`
→ `manual approval`

---

## 六、最终建议

### 先做（短期）
1. 报告模板升级（已开始）
2. optimization_cycle 稳定化（已开始）
3. weekly/daily 的详细回执汇总（已开始）
4. 数据快照 / 备份 / 评分接入 daily_data_cycle

### 中期做
1. strategy_research_cycle
2. factor_research_cycle
3. knowledge_cycle
4. OpenCode build 支线（在低风险验证后启用）

### 后期做
1. daily_pick_cycle
2. 舆情抓取正式接入
3. 实盘前的审批门 / 仓位门 / 风控门

---

## 七、核心结论

当前系统不是从零搭建阶段，而是：

> **主干代码已具备“数据 + 回测 + 因子 + 健康检查 + 优化支线”的雏形。**

历史详细任务列表现在最好的用法，不是照单执行，而是：

> **把它重构为一套“主循环 + 研究支线 + 优化支线 + 知识支线”的生态任务图谱。**
