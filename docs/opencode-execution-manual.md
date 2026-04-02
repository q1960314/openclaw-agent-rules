# OpenCode 能力放大器 - 完整执行手册

> 创建时间：2026-03-25 01:11
> 目标：给出具体的、可执行的细节

---

## 一、OpenCode 是什么？怎么用？

### 1.1 OpenCode 是 OpenClaw 提供的工具集

**不是**一个新的agent，而是所有agent都可以调用的工具：

| 工具 | 功能 | 调用方式 |
|------|------|----------|
| `read` | 读取文件 | `read(path="/path/to/file")` |
| `write` | 写入文件 | `write(path="/path/to/file", content="...")` |
| `exec` | 执行命令 | `exec(command="python script.py")` |
| `memory_store` | 存储记忆 | `memory_store(text="内容", category="fact")` |
| `memory_recall` | 检索记忆 | `memory_recall(query="关键词")` |

### 1.2 谁可以用？

**所有agent都可以用**，包括：
- master-quant
- coder
- strategy-expert
- backtest-engine
- ... 所有14个子智能体

### 1.3 通过什么方式调用？

**直接在对话中调用**，就像我现在这样：

```python
# 例如，strategy-expert 想查看用户的策略代码：
read(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py")

# 然后，strategy-expert 想写入新的策略：
write(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py", content="新策略代码...")

# 然后，strategy-expert 想运行回测验证：
exec(command="/home/admin/miniconda3/envs/vnpy_env/bin/python /home/admin/.openclaw/workspace/master/vnpy_backtest/orchestrator.py")
```

---

## 二、完整任务流程（以"优化打板策略评分体系"为例）

### 2.1 用户发送需求

```
用户（飞书）: "优化打板策略的评分体系"
```

### 2.2 master-quant 接收并处理

**步骤1：接收需求**
```
master-quant 收到飞书消息
```

**步骤2：检索知识库（使用OpenCode工具）**
```python
memory_recall(query="打板策略 评分体系", limit=5)
```

**步骤3：查看当前代码（使用OpenCode工具）**
```python
read(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py")
```

**步骤4：分析需求，拆解任务**
```
master-quant 分析后拆解为：
- 任务1：strategy-expert 分析当前评分体系
- 任务2：factor-miner 挖掘新因子
- 任务3：backtest-engine 回测验证
```

**步骤5：分派任务给 strategy-expert**
```python
sessions_send(
    sessionKey="agent:strategy-expert:main",
    message="""【任务】分析打板策略评分体系

当前代码位置: /home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py
类名: LimitUpStrategy
方法: score()

要求:
1. 使用 read 工具查看代码
2. 分析 DEFAULT_WEIGHTS 的合理性
3. 找出可以优化的维度
4. 输出分析报告

完成后使用 sessions_send 汇报给我。"""
)
```

**步骤6：master-quant 回到待命状态**
```
master-quant 不等待，立即回到待命状态
可以继续接收用户的消息
```

### 2.3 strategy-expert 执行任务

**步骤1：接收任务**
```
strategy-expert 收到 master-quant 的任务消息
```

**步骤2：查看代码（使用OpenCode工具）**
```python
read(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py")
```

**步骤3：分析代码**
```
strategy-expert 分析 DEFAULT_WEIGHTS:
- order_amount: 15分
- up_down_times: 15分
- inst_buy: 15分
- ...

发现问题:
- 缺少"板块强度"维度
- "炸板次数"权重可能过低
- 建议新增"次日预期"维度
```

**步骤4：汇报给 master-quant**
```python
sessions_send(
    sessionKey="agent:master-quant:main",
    message="""【任务完成】打板策略评分体系分析

分析结果:
1. 当前23维评分体系基本合理
2. 发现可优化点:
   - 缺少"板块强度"维度（建议权重10分）
   - "炸板次数"权重-5分可能过低
   - 建议新增"次日预期"维度

建议:
- 新增板块强度评分
- 调整炸板次数权重为-8分
- 新增次日预期评分

是否继续优化？"""
)
```

### 2.4 master-quant 收到汇报，继续调度

**步骤1：收到 strategy-expert 的汇报**
```
master-quant 收到消息
```

**步骤2：转发给用户确认**
```python
message(
    channel="feishu",
    message="""【策略优化分析】

strategy-expert 完成了打板策略评分体系分析：

1. 当前23维评分体系基本合理
2. 发现可优化点:
   - 缺少"板块强度"维度（建议权重10分）
   - "炸板次数"权重-5分可能过低
3. 建议:
   - 新增板块强度评分
   - 调整炸板次数权重

是否继续优化？请确认。"""
)
```

**步骤3：等待用户确认**
```
用户回复: "继续优化"
```

**步骤4：分派给 factor-miner 挖掘新因子**
```python
sessions_send(
    sessionKey="agent:factor-miner:main",
    message="""【任务】挖掘打板策略新因子

要求:
1. 分析"板块强度"因子如何量化
2. 计算IC值
3. 输出因子定义和权重建议

完成后汇报给我。"""
)
```

**步骤5：同时分派给 backtest-engine 准备回测**
```python
sessions_send(
    sessionKey="agent:backtest-engine:main",
    message="""【任务】准备回测环境

要求:
1. 确认回测框架可用
2. 准备2024年全年数据
3. 等待新评分体系后运行回测

完成后汇报给我。"""
)
```

### 2.5 任务完成后的汇报机制

**方案A：子智能体主动汇报**
```
子智能体完成任务后，使用 sessions_send 发送消息给 master-quant
master-quant 收到后转发给用户
```

**方案B：定时检查状态**
```python
# master-quant 每10分钟检查一次子智能体状态
sessions_history(sessionKey="agent:strategy-expert:main", limit=5)
sessions_history(sessionKey="agent:backtest-engine:main", limit=5)
```

**方案C：回调机制（推荐）**
```
子智能体完成任务后，直接调用：
sessions_send(sessionKey="agent:master-quant:main", message="任务完成报告")

master-quant 收到后立即处理
```

---

## 三、具体配置修改

### 3.1 启用 OpenCode 工具

**当前 TOOLS.md 禁用了 read/write，需要修改：**

```markdown
## 可用工具

### 所有agent可用
| 工具 | 用途 |
|------|------|
| `read` | 读取文件 |
| `exec` | 执行命令 |
| `memory_*` | 记忆管理 |

### 需要确认后使用
| 工具 | 用途 | 确认方式 |
|------|------|----------|
| `write` | 写入文件 | master-quant 确认后执行 |
```

### 3.2 各agent的默认模型配置

**修改每个agent的配置文件：**

**coder 的 models.json:**
```json
{
  "defaultModel": "qwen3-coder-plus",
  "temperature": 0.2,
  "thinking": true
}
```

**strategy-expert 的 models.json:**
```json
{
  "defaultModel": "qwen3-max-2026-01-23",
  "temperature": 0.3,
  "thinking": true
}
```

### 3.3 汇报流程配置

**在 AGENTS.md 中添加：**

```markdown
## 任务汇报流程

### 子智能体完成任务后
1. 使用 sessions_send 发送报告给 master-quant
2. 报告格式：
   【任务完成】任务ID: xxx
   【执行结果】xxx
   【输出文件】xxx
   【需要确认】xxx

### master-quant 收到报告后
1. 检查报告完整性
2. 转发给用户确认
3. 用户确认后，通知知识库沉淀
```

---

## 四、实际代码示例

### 4.1 strategy-expert 写入新策略

```python
# strategy-expert 执行
# 步骤1：读取现有代码
current_code = read(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py")

# 步骤2：分析并设计新评分体系
new_weights = {
    'order_amount': 15,
    'up_down_times': 15,
    'inst_buy': 15,
    'youzi_buy': 10,
    'concept_count': 10,
    'break_limit_times': -8,  # 调整权重
    'float_market_cap': 10,
    'turnover_ratio': 5,
    'no_reduction': 5,
    'no_inquiry': 5,
    'is_main_industry': 5,
    'sector_strength': 10,  # 新增
}

# 步骤3：写入代码
write(path="/home/admin/.openclaw/workspace/master/vnpy_backtest/strategies.py", content=new_code)

# 步骤4：汇报
sessions_send(
    sessionKey="agent:master-quant:main",
    message="【任务完成】已更新评分体系，新增板块强度维度"
)
```

### 4.2 backtest-engine 运行回测

```python
# backtest-engine 执行
# 步骤1：运行回测
result = exec(command="""
/home/admin/miniconda3/envs/vnpy_env/bin/python \
/home/admin/.openclaw/workspace/master/vnpy_backtest/orchestrator.py \
--start 2024-01-01 --end 2024-12-31
""")

# 步骤2：分析结果
# result 包含回测指标

# 步骤3：汇报
sessions_send(
    sessionKey="agent:master-quant:main",
    message=f"""【回测完成】
总收益: {result['total_return']*100:.2f}%
夏普比率: {result['sharpe_ratio']:.2f}
最大回撤: {result['max_drawdown']*100:.2f}%
交易次数: {result['total_trades']}"""
)
```

---

## 五、汇报时间线

| 时间点 | 动作 | 执行者 |
|--------|------|--------|
| T+0 | 用户发送需求 | 用户 |
| T+1min | master-quant 分派任务 | master-quant |
| T+5min | strategy-expert 开始分析 | strategy-expert |
| T+10min | strategy-expert 汇报结果 | strategy-expert |
| T+11min | master-quant 转发给用户 | master-quant |
| T+15min | 用户确认继续 | 用户 |
| T+16min | master-quant 分派给 factor-miner | master-quant |
| T+25min | factor-miner 汇报结果 | factor-miner |
| T+26min | master-quant 转发给用户 | master-quant |
| T+30min | 用户确认应用 | 用户 |
| T+31min | master-quant 通知 coder 写入代码 | master-quant |
| T+35min | coder 完成写入 | coder |
| T+36min | master-quant 通知 backtest-engine 回测 | master-quant |
| T+45min | backtest-engine 汇报回测结果 | backtest-engine |
| T+46min | master-quant 汇报最终结果给用户 | master-quant |

---

## 六、需要你确认的

### 6.1 工具启用

- [ ] 是否同意启用 read/write 工具？
- [ ] write 是否需要用户确认？

### 6.2 模型配置

- [ ] 是否同意按推荐表更新各agent模型？
- [ ] 是否有其他模型偏好？

### 6.3 汇报机制

- [ ] 使用方案A（主动汇报）？
- [ ] 使用方案B（定时检查）？
- [ ] 使用方案C（回调机制）？

### 6.4 立即执行

- [ ] 是否同意立即修改 TOOLS.md？
- [ ] 是否同意立即更新模型配置？

---

**请逐项确认，我立即执行修改。**