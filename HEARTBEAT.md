# HEARTBEAT.md - master-quant 心跳（轻量化版）

## ⚠️ 强制规则：轻量化启动

### 🚫 启动时禁止：
- ❌ 不要执行大量 Python 导入
- ❌ 不要读取旧日志文件（3月18-24号等）
- ❌ 不要全量检索知识库
- ❌ 不要预加载历史记忆

### ✅ 启动时自动可用：
- **relevant-memories**：系统自动注入最近30-50条对话（无需操作）
- **working_memory.json**：最近2条错误/决策，3条待办

### ✅ 运行时按需加载：
```
用户提到关键词 → memory_recall(query="关键词", limit=3)
```

---

## 记忆加载策略（避免卡住）

### 启动时：
- **不预加载任何记忆**
- **等待用户消息**

### 运行时：
- **relevant-memories**（系统注入）：最近 30-50 条对话记录
- **向量检索**：用户提到关键词时，用 `memory_recall` 按需搜索，limit=3

### 示例：
```python
# 用户提到"打板策略"时，按需检索
memory_recall(query="打板策略", limit=3)
```

---

## 触发条件（严格执行）

**唯一触发源：**
- 用户的手动指令
- 用户定时任务下发的触发信号

**无自动触发：**
- 无任何自动触发动作
- 无触发信号绝不执行任何自动操作

---

## 每日定时任务（保留）

| 时间 | 任务 | 执行方式 |
|------|------|----------|
| 23:00 | 发送沉淀命令给 doc-manager | sessions_send |
| 23:30 | 日终总结发送给用户 | message |

### 每日沉淀命令格式
```
sessions_send(
  sessionKey="agent:doc-manager:main",
  message="【每日沉淀】日期：YYYY-MM-DD\n任务：整理今日所有沉淀文档，归档到知识库"
)
```

---

---

## 后台运行机制（避免阻塞会话）

### 长时间任务必须后台运行

| 任务类型 | 预计耗时 | 执行方式 |
|---------|---------|---------|
| 全量数据抓取 | 2-4小时 | `exec(background=True)` |
| 回测(484天) | 5-15分钟 | `exec(background=True)` |
| 参数优化 | 10-30分钟 | `exec(background=True)` |
| 代码开发 | 10-30分钟 | `exec(background=True)` |

### 后台运行示例

```python
# 启动后台任务
exec(
    command="python /data/agents/master/run_backtest.py",
    background=True,
    yieldMs=30000  # 30秒后返回控制权
)

# 继续与用户沟通...

# 任务完成后通知用户
message(
    action="send",
    channel="feishu",
    message="【后台任务完成】回测已完成，年化收益15.2%"
)
```

---

## 多智能体协作机制

### 任务派发

```python
# 派发任务给子智能体
sessions_send(
    sessionKey="agent:coder:main",
    message="【任务派发】任务ID: xxx, 内容: xxx"
)
```

### 任务流转规则

1. **执行层（直调）**: coder, strategy-expert, test-expert, doc-manager, parameter-evolver
2. **支撑层（中转）**: factor-miner, backtest-engine, data-collector, finance-learner, sentiment-analyst, ops-monitor, knowledge-steward
3. **完成后通知**: 子智能体完成任务后，通过 message 通知用户

---

## 自检要求（每次输出前）
1. 红线检查（10 项全局红线）
2. 用户确认检查（代码修改必须经过用户确认）
3. 后台运行检查（长时间任务是否后台运行）

## 违规处理
- 发现违规 → 立即停止 → 记录 → 告警用户
