# Agent 执行契约规范

> 创建时间：2026-03-27  
> 目标：让每个 agent 都成为独立可落地的执行单元

---

## 一、核心原则

### 1.1 不是横向拆分，而是纵向闭环

❌ **错误做法**：把 agent 分成"思考型/执行型/验收型"  
✅ **正确做法**：每个 agent 在自己职责内具备完整闭环能力

### 1.2 每个 agent 都必须具备 6 个能力

1. **能接任务** - 通过任务对象（task spec）接收任务
2. **能认领任务** - 更新 claim.json 声明所有权
3. **能真实执行** - 在职责范围内真正落地
4. **能产出 artifacts** - 产生本职责的交付物
5. **能做自检** - 完成本职责内的自我验证
6. **能交接下一步** - 通过 handoff 把结果交给下一个节点

---

## 二、统一任务内核

### 2.1 任务目录结构

```
traces/jobs/{TASK-ID}/
├── spec.json           # 任务规格（输入/输出/成功标准）
├── claim.json          # 认领状态（claimed_by/attempt/lease）
├── status.json         # 执行状态（queued/running/blocked/done/failed）
├── artifacts/          # 交付产物（每个 agent 产出不同内容）
├── verify/             # 验收结果（verdict.json）
├── approval/           # 审批记录（如需人工审批）
└── final.json          # 最终状态（success/failure + 归档路径）
```

### 2.2 状态流转

```
queued → claimed → running → completed → verified → finalized
              ↓            ↓
          timeout      blocked
              ↓            ↓
          retry        failed
```

### 2.3 关键规则

| 规则 | 说明 |
|------|------|
| 没有 claim 不能执行 | claim.json 的 claimed_by 必须非空 |
| 没有 artifacts 不能完成 | artifacts 目录必须有本职责的交付物 |
| 没有 verify 不能归档 | verdict.json 必须存在且 pass |
| 超时自动释放 | lease_until 过期后其他 agent 可重新认领 |

---

## 三、Agent 专属执行契约

每个 agent 都有自己的专属契约，定义：

1. **职责边界** - 它负责什么
2. **输入格式** - 它接收什么任务
3. **输出格式** - 它必须产出什么 artifacts
4. **完成定义** - 什么算完成
5. **交接规范** - 如何把结果交给下一个节点

### 3.1 执行型 Agent 列表

| Agent | 职责 | 关键 artifacts |
|-------|------|---------------|
| `coder` | 代码修复/功能实现 | diff.patch, changed_files.json, run.log |
| `test-expert` | 独立验收 | verdict.json, test_report.md |
| `doc-manager` | 文档整理交付 | doc_path.txt, delivery_pack.md |
| `knowledge-steward` | 知识沉淀归档 | kb_write.json, kb_index_update.json |
| `strategy-expert` | 策略分析与调整 | strategy_review.md, strategy_candidate.json |
| `parameter-evolver` | 参数优化建议 | candidate_params.json, sensitivity_report.md |
| `backtest-engine` | 回测执行 | metrics.json, report.md, run.log |
| `data-collector` | 数据采集 | data_snapshot.json, quality_report.md |

---

## 四、执行流程示例

### 4.1 代码修复任务链

```
1. TASK 创建
   └─ spec.json 定义任务目标

2. coder 认领
   ├─ 更新 claim.json（claimed_by=coder）
   ├─ 更新 status.json（status=running）
   ├─ 执行代码修复
   └─ 产出 artifacts/diff.patch, artifacts/changed_files.json

3. test-expert 验收
   ├─ 读取 artifacts
   ├─ 独立验证
   └─ 产出 verify/verdict.json（pass/fail）

4. doc-manager 整理
   ├─ 读取 verdict.json
   ├─ 生成交付文档
   └─ 产出 artifacts/delivery_pack.md

5. knowledge-steward 沉淀
   ├─ 读取交付包
   ├─ 写入知识库
   └─ 产出 artifacts/kb_index_update.json

6. TASK 完成
   └─ 更新 final.json（status=success）
```

---

## 五、OpenCode 定位

OpenCode 不是 agent，而是：

> **每个 agent 在自己职责内可调用的执行引擎**

### 使用规范

| Agent | 是否使用 OpenCode | 使用场景 |
|-------|------------------|----------|
| `coder` | ✅ | 代码生成/修复 |
| `test-expert` | ❌ | 独立验收，不依赖代码生成 |
| `doc-manager` | ❌ | 文档整理 |
| `knowledge-steward` | ❌ | 知识归档 |
| `backtest-engine` | ❌ | 真跑回测 |

---

## 六、失败处理

### 6.1 认领失败

- claim.json 的 claimed_by 为空
- 任务保持 unclaimed 状态
- 调度器可重新派发

### 6.2 执行超时

- lease_until 过期
- status.json 更新为 blocked
- 其他 agent 可重新认领

### 6.3 验收失败

- verdict.json 的 verdict=fail
- status.json 更新为 failed
- 触发 retry_policy 或人工审批

---

## 七、与 sessions_send 的区别

| 维度 | sessions_send | 任务内核执行 |
|------|--------------|-------------|
| 约束 | 软约束 | 硬约束 |
| 产物 | 文本回复 | artifacts |
| 状态 | 无状态 | claim/status |
| 验收 | 自检 | 独立验收 |
| 适用 | 分析/建议 | 关键执行 |

---

## 八、下一步

1. ✅ 本文件作为总规范
2. ⏳ 为每个执行型 agent 创建专属契约
3. ⏳ 用 TASK-20260327-STEP1-ENV-FIX 跑通第一条链
4. ⏳ 接入调度层
