# A股量化生态循环蓝图 v3.2-runtime

> 原则：**以当前最新代码为主，旧任务列表（v3.1 / 阶段3-9）为参考融合**。
> 适用对象：**中国A股量化回测 / 选股系统**，后续可能涉及实盘，但当前仅限研究/回测/验证闭环。

## 1. 总体思路

整个生态分为三层：

### 1.1 Framework 层（全局框架）
- 数据抓取与校验
- 回测引擎与健康检查
- 工单 / 队列 / 派发 / 回执
- 通知 / 汇总 / 清理 / 修复
- OpenCode 优化支线

### 1.2 Strategy 层（可插拔策略层）
- 23维评分策略
- 打板策略
- 缩量潜伏策略
- 板块轮动策略
- 多策略融合
- 未来新增策略

### 1.3 Optimization 层（循环进化层）
- 参数优化
- 回测验证
- OpenCode plan/build
- 测试 / 回测 / 审批门

> 关键修正：**23维评分只是策略层的一种，不是整个系统的全局硬框架。**

---

## 2. 当前代码主干（以最新代码为准）

### 2.1 当前核心代码
- `/data/agents/master/fetch_data_optimized.py`
- `/data/agents/master/vnpy_backtest/`
- `/data/agents/master/qlib_integration/`

### 2.2 当前已经成型的能力
- 运行模式分离（全量/增量/仅回测/每日选股）
- 向量化回测引擎
- 健康检查
- 自动调参
- 因子缓存
- OpenClaw 工作流 / 工单 / 队列 / 通知
- OpenCode plan 支线

---

## 3. 生态循环（runtime版）

## 3.1 daily_data_cycle
目标：把“数据抓取 / 数据验证 / 数据快照”独立成循环，而不是混在策略循环里。

阶段：
1. preflight
2. data_validate
3. summarize
4. notify_user

后续增强：
- 数据版本快照
- 数据质量评分
- 备份

---

## 3.2 daily_research
目标：对当前缓存数据做快速研究验证，判断是否有策略异常。

阶段：
1. preflight
2. data_validate
3. smoke_backtest（后续可改名：快速验证回测）
4. followup_ticket
5. queue_ticket
6. dispatch_ticket
7. collect_reply
8. summarize
9. notify_user

---

## 3.3 weekly_health
目标：周级健康检查，确认策略是否失效、是否需要优化。

阶段：
1. preflight
2. data_validate
3. health_check
4. followup_ticket
5. queue_ticket
6. dispatch_ticket
7. collect_reply
8. summarize
9. notify_user

---

## 3.4 optimization_cycle
目标：把“发现问题”转成“优化计划 / 低风险验证 / 后续 build 候选”。

阶段：
1. preflight
2. select_target
3. prepare_task
4. opencode_plan
5. summarize
6. notify_user

当前状态：
- 已接入 OpenCode plan
- 低风险支线（parameter-evolver / backtest-engine）已打通
- 下一步才是 build 候选

---

## 3.5 knowledge_cycle
目标：把 daily / weekly / optimization 的结果自动沉淀成知识闭环。

阶段：
1. collect_cycle_reports
2. summarize
3. notify_user

沉淀对象：
- 报告索引
- 工单索引
- 回测结果摘要
- 需要知识归档的候选项

---

## 4. Agent职责（runtime版）

### 4.1 主循环内高频 agent
- master-quant：总控 / 汇总 / 路由 / 门禁
- validation-center（逻辑角色）：数据验证 / 回测验证 / 健康检查
- knowledge-steward：知识沉淀 / 报告归档
- strategy-expert：策略复核 / 优化建议
- parameter-evolver：低风险参数支线
- backtest-engine：回测验证支线

### 4.2 OpenCode 的位置
OpenCode 不进主循环日常常驻链，而是：

`strategy_review / weekly_optimization / data_fix`
→ `coder`
→ `OpenCode(plan/build)`
→ `test-expert`
→ `backtest-engine`
→ `summary`
→ `notify`
→ `manual approval`

---

## 5. 旧任务列表如何融合

### 5.1 以当前代码为主
- 旧任务列表中已经被当前代码覆盖的，不再重复实现
- 旧任务列表中仍有价值的，转成 cycle 或支线

### 5.2 当前优先吸收的内容
- 3.3.x 数据验证 → daily_data_cycle
- 7.x 循环回测 / 健康检查 → weekly_health / optimization_cycle
- 9.x 知识沉淀 → knowledge_cycle
- 4.x/5.x 战法/因子研究 → strategy_research / factor_research（后续支线）

---

## 6. 当前运行原则
1. 先把生态循环做顺
2. 再让专项 agent 接具体优化任务
3. OpenCode 默认只做 plan / build 支线，不直接进入主循环
4. 实盘相关始终设审批门

---

## 7. 当前下一步
1. 先完善 `daily_data_cycle`
2. 先完善 `knowledge_cycle`
3. 然后再把 optimization_cycle 升级到：
   - plan
   - low-risk validation
   - build candidate
4. 最后接 OpenCode build + test/backtest 审批门
