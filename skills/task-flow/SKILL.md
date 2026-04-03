name: task-flow
description: 任务流转技能。收到子智能体报告时自动触发，强制转发给用户，并根据下个任务的需求，还有子智能体的相应职责派发下一任务给相应子智能体。并发送派发任务信息给用户。

# 任务流转技能

## 触发条件

收到任何子智能体（coder、test-expert、strategy-expert 等）通过 sessions_send 发送的任务报告。

## 强制执行流程

**收到子智能体报告时，必须按以下步骤执行（不可跳过任何步骤）：**

### 步骤 1: 转发报告给用户

使用 message 工具发送到飞书：

```
message(
  channel="feishu",
  message="【子智能体报告】\n任务ID: xxx\n执行者: xxx\n状态: xxx\n结果: xxx"
)
```

### 步骤 2: 判断是否有下一个任务

根据任务流转规则判断：

| 当前完成阶段 | 下一个任务 | 执行智能体 |
|--------------|------------|------------|
| 代码修改完成 | 代码验证 | test-expert |
| 策略优化完成 | 策略回测 | backtest-engine |
| 数据采集完成 | 数据验证 | test-expert |
| 测试验证完成 | 知识沉淀 | knowledge-steward |

如果没有明确的下一个任务，跳到步骤 4。

### 步骤 3: 派发下一任务

使用 sessions_send 派发：

```
sessions_send(
  sessionKey="agent:xxx:main",
  message="【任务ID】xxx\n【任务内容】xxx"
)
```

### 步骤 4: 汇报派发信息给用户

使用 message 工具发送到飞书：

```
message(
  channel="feishu",
  message="【已派发】任务 xxx 给 xxx 智能体"
)
```

如果没有下一任务：

```
message(
  channel="feishishu",
  message="【任务完成】xxx 任务已全部完成，无待处理任务"
)
```

## 禁止行为

- ❌ 只回复"收到"、"等待"等确认语
- ❌ 不转发报告给用户
- ❌ 不派发下一个任务
- ❌ 不汇报派发信息
- ❌ 等待用户询问才行动

## 验证自检

每次收到子智能体报告后，自检是否执行了所有步骤：

1. ✅ 是否用 message 转发了报告？
2. ✅ 是否判断了下一个任务？
3. ✅ 如有任务，是否派发了？
4. ✅ 是否用 message 汇报了派发信息？

如有遗漏，立即补救。

## 示例

**收到 coder 报告：**

```
【任务ID】TASK-001
【执行状态】已完成
【代码修改内容】删除了集合竞价接口
```

**执行动作：**

1. message → 飞书：转发报告
2. 判断：代码修改完成 → 需要验证
3. sessions_send → test-expert：派发验证任务
4. message → 飞书：汇报派发信息

---

*此技能由用户授权创建，强制执行。*