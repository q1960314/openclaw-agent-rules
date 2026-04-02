# 生态循环运行内核实施表（最小可落地版）

更新时间：2026-03-27 18:27:47 +0800

## 目标

把当前“消息委托 + 文本完成”的多 agent 协作，升级为“任务对象 + 状态机 + 产物驱动 + 独立验收 + 沉淀回流”的生态运行内核。

---

## 完成态定义

整个生态系统可循环运行，必须同时满足：

1. 任务不是一段消息，而是一个任务对象（task object）
2. 执行不靠 agent 自述完成，而靠 artifacts 产物落地
3. 执行者不能自己宣布完成，必须经独立 verifier 验收
4. 状态机明确：queued/claimed/running/verifying/awaiting_approval/completed/failed/blocked/stale/archived
5. OpenCode 被纳入执行层标准节点，不再挂在普通子 agent 主观执行链后
6. 顶层入口任务由调度层触发，中间链条由事件/状态驱动推进
7. 所有 completed 任务自动进入文档/知识沉淀层，反哺下一轮

---

## 分层架构

### L1 Agent 协议层（已完成第一轮）
- 目标：让 agent 至少具备真实执行/真实验收/真实写入的能力
- 状态：第一轮已完成
- 说明：仍需在真实任务内核里继续验证

### L2 任务运行内核层（当前开始落地）
- 目标：建立 task spec / status / claim / artifacts / verify / final
- 状态：本次开始创建骨架

### L3 工作流执行层（下一阶段）
- 目标：把 daily/weekly/diagnosis/execution/validation 串到任务内核上
- 状态：未开始

### L4 调度循环层（后续阶段）
- 目标：支持“几点几分做什么”，顶层时间驱动，链内状态驱动
- 状态：未开始

---

## 执行角色分层

### 决策型 Agent
- strategy-expert
- parameter-evolver
- factor-miner
- finance-learner
- sentiment-analyst

职责：输出分析、方案、候选项。不能直接算执行完成。

### 执行型 Worker
- master 直接工具执行
- OpenCode（执行层工具型 worker）
- 后续可接 ACP / 硬执行器

职责：真改文件、真跑命令、真产生产物。

### 验收型 Agent
- test-expert
- backtest-engine
- ops-monitor

职责：字符串层 / 语义层 / 运行层验收。

### 沉淀型 Agent
- doc-manager
- knowledge-steward

职责：文档整理、知识归档、经验沉淀。

---

## 任务对象标准

每个任务目录结构：

```text
traces/jobs/
└── TASK-YYYYMMDD-XXXX/
    ├── spec.json
    ├── status.json
    ├── claim.json
    ├── artifacts/
    ├── verify/
    │   └── verdict.json
    ├── approval/
    │   └── approval.json
    └── final.json
```

### spec.json 最小字段
- task_id
- task_type
- title
- owner_role
- validator_role
- source_cycle
- input_refs
- required_artifacts
- approval_policy
- next_on_success
- next_on_failure
- retry_policy

### status.json 最小字段
- task_id
- status
- retry_count
- blocked_reason
- next_retry_at
- updated_at

### claim.json 最小字段
- task_id
- claimed_by
- claimed_at
- lease_until
- attempt
- status

### verify/verdict.json 最小字段
- task_id
- validator
- artifact_check
- string_check
- semantic_check
- runtime_check
- final_verdict
- reason

### final.json 最小字段
- task_id
- final_status
- owner_role
- validator_role
- approval_status
- archived
- closed_at

---

## OpenCode 的正确位置

OpenCode 是执行层工具型 worker，不是 agent，不是调度器，不是验收器。

正确链路：
1. task spec 明确需要 OpenCode
2. 外部执行器显式调用 OpenCode
3. 产物写入 artifacts/opencode/
4. test-expert / backtest-engine 做验收
5. verdict 决定 pass/fail

禁止：
- 让普通子 agent 主观决定“要不要调用 OpenCode”
- 用文本说明代替 OpenCode 产物

---

## 时间调度原则

### 时间属于调度器，不属于 agent

以后“几点几分做什么”应该只改 schedule registry，不改 agent prompt，不靠 agent 记忆。

### 顶层入口任务（时间驱动）
- daily_data_cycle
- daily_research_cycle
- weekly_health_cycle
- knowledge_cycle

### 中间推进任务（状态/事件驱动）
- diagnosis_cycle
- execution_cycle
- validation_cycle
- archive_followup
- retry/recovery

---

## 实施顺序

### Phase 1：建立任务运行内核骨架
1. 创建 traces/jobs 目录与模板
2. 固化 task schema
3. 固化状态机文档
4. 选择第一批角色接入：coder / test-expert / doc-manager / knowledge-steward

### Phase 2：把当前 Step 1 修复任务接入内核
任务：修复 workflow_run_opencode.py / workflow_run_execution_opencode.py / ecosystem.crontab.example

执行链：
- coder 认领
- coder 产生产物
- test-expert 验收
- doc-manager 整理
- knowledge-steward 归档

### Phase 3：扩展到工作流主链
- daily_research
- diagnosis
- execution
- validation
- archive

### Phase 4：接入调度层
- schedule registry
- missed_run_policy
- concurrency
- retry/backoff/cooldown

---

## 当前第一批真实落地任务

### 任务 ID
`TASK-20260327-STEP1-ENV-FIX`

### 任务内容
修复：
1. scripts/workflow_run_opencode.py
2. scripts/workflow_run_execution_opencode.py
3. config/ecosystem.crontab.example

### 角色链
- owner_role: coder
- validator_role: test-expert
- doc_role: doc-manager
- archive_role: knowledge-steward

### 判定标准
- workflow_run_opencode.py：命令路径正确 + 语义正确
- workflow_run_execution_opencode.py：无裸 opencode + 语义正确
- ecosystem.crontab.example：PATH 已补齐
- test-expert verdict = pass

---

## 成功标准

第一阶段不是整个生态完成，而是满足：

1. 至少 1 个真实任务不再靠 sessions_send 文本完成，而是靠任务目录推进
2. coder 真实修改产物落地
3. test-expert 真实写出 verifier verdict
4. doc-manager 真实整理文档
5. knowledge-steward 真实沉淀到知识库

这一步一旦跑通，才算“生态运行内核”开始真正落地。
