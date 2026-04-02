# 深度思考：OpenCode + 量化生态整合的核心问题

> 创建时间：2026-03-25 00:15
> 背景：用户指出"丢三落四"，需要深度思考

---

## 一、根本问题：记忆系统的两难

### 1.1 矛盾点

```
启用记忆加载 → memory_manager.py 循环调用 → 超时中止
禁用记忆加载 → 上下文丢失 → 丢三落四
```

### 1.2 工作记忆中已有的关键信息

```json
{
  "错误": "模块测试时预加载数据导致卡住，需优化数据加载器懒加载逻辑",
  "决策": "回测框架优化启动：vnpy v6.0 + qlib因子增强已就绪，准备集成到源代码",
  "待办": "优化回测框架：1.完善vnpy+qlib集成 2.解决打板策略买入时机问题 3.生成可视化图表 4.完善企业微信通知"
}
```

### 1.3 OpenCode 的 memory_* 工具

| 工具 | 能力 | 与现有系统的关系 |
|------|------|------------------|
| `memory_store` | 存储记忆 | 可替代 memory_manager.py 的 add_* |
| `memory_recall` | 检索记忆 | 可替代 kb-search.sh |
| `memory_update` | 更新记忆 | 新能力 |
| `memory_forget` | 删除记忆 | 新能力 |

**关键问题**：OpenCode 的 memory_* 是独立的记忆系统，还是可以与现有的 working_memory.json 整合？

---

## 二、用户需求的结构化理解

### 2.1 四种运行模式

| 模式 | 触发时机 | 核心任务 | 涉及文件 |
|------|----------|----------|----------|
| **1. 全量抓取** | 手动触发 | 抓取所有历史数据 | akshare_source.py, data/ |
| **2. 增量抓取** | 定时（每日） | 更新最新数据 | akshare_source.py |
| **3. 回测** | 手动触发 | 运行策略回测 | orchestrator.py, vector_engine.py |
| **4. 每日选股** | 定时（盘前） | 生成当日选股结果 | strategies.py |

### 2.2 三种策略

| 策略 | 文件位置 | 核心逻辑 |
|------|----------|----------|
| **打板策略** | strategies.py (LimitUpStrategy) | 23维评分追涨停 |
| **缩量潜伏** | strategies.py (VolumeContractionStrategy) | 首板后缩量低吸 |
| **板块轮动** | （待实现） | 板块轮动切换 |

### 2.3 技术环境

```
Python 环境: /home/admin/miniconda3/envs/vnpy_env (3.10)
回测框架: VNPY + 向量化引擎
因子系统: QLIB（需要与 VNPY 联动）
```

---

## 三、OpenCode 整合的三个层面

### 3.1 记忆层：解决"丢三落四"

**方案**：用 OpenCode 的 `memory_*` 工具替代有 bug 的 `memory_manager.py`

```python
# 原来（有 bug）
python memory/memory_manager.py --action add_decision --content "决策内容"

# 现在（用 OpenCode 工具）
memory_store(
    text="决策内容",
    category="decision",
    scope="master-quant"
)
```

**好处**：
- 不再依赖 memory_manager.py 脚本
- 避免循环调用超时
- OpenCode 原生支持，更稳定

### 3.2 调度层：解决子智能体中断

**问题**：子智能体大量 abortedLastRun: true

**方案**：
1. 用 `subagents(action="list")` 检查运行状态
2. 用 `sessions_send` 发送恢复指令
3. 建立心跳机制，定期检查

### 3.3 执行层：解决工具限制

**问题**：TOOLS.md 禁用了 read/write

**方案**：
- 启用 `read`：master 可以直接查看代码
- `write` 需用户确认：保持安全
- 启用 `exec`：直接运行回测脚本

---

## 四、整合后的工作流

### 4.1 每日选股流程（示例）

```
定时触发（盘前 8:00）
    ↓
master-quant:
    1. memory_recall(query="昨日选股结果")  # 检索记忆
    2. exec("python fetch_incremental.py")  # 增量数据
    3. exec("python run_selection.py")      # 运行选股
    4. memory_store(text="今日选股结果")     # 存储记忆
    5. message(to="飞书用户", message="今日选股结果")  # 通知用户
```

### 4.2 回测流程（示例）

```
用户指令: "回测打板策略，用 QLIB 因子增强"
    ↓
master-quant:
    1. read("strategies.py")  # 直接查看策略代码
    2. memory_recall(query="QLIB 因子")  # 检索相关知识
    3. sessions_send(
         sessionKey="agent:backtest-engine:main",
         message="运行回测：打板策略 + QLIB 因子增强"
       )
    4. 等待结果 → 汇报用户
```

---

## 五、需要做出的决策

| 决策点 | 选项 | 建议 |
|--------|------|------|
| 1. 记忆系统 | A) 迁移到 OpenCode memory_* B) 修复 memory_manager.py | **A** |
| 2. read/write | A) 启用 B) 需确认后启用 C) 保持禁用 | **B** |
| 3. 子智能体中断 | A) 逐个恢复 B) 批量重置 | **A** |
| 4. 整合优先级 | A) 先解决记忆 B) 先解决调度 | **A** |

---

## 六、立即行动计划

### 步骤 1：迁移记忆系统

```python
# 用 memory_store 替代 memory_manager.py
# 在每次会话结束时，使用 memory_store 保存关键信息
```

### 步骤 2：恢复子智能体

```python
# 向中断的子智能体发送恢复指令
sessions_send(sessionKey="agent:strategy-expert:main", message="【系统恢复】请恢复待命状态")
sessions_send(sessionKey="agent:backtest-engine:main", message="【系统恢复】请恢复待命状态")
```

### 步骤 3：更新 TOOLS.md

```markdown
## 可用工具（更新后）

### 记忆管理
- `memory_store`: 存储记忆
- `memory_recall`: 检索记忆
- `memory_update`: 更新记忆
- `memory_forget`: 删除记忆

### 文件操作
- `read`: 直接读取文件 ✅
- `write`: 需用户确认 ⚠️

### 执行
- `exec`: 运行脚本/命令 ✅
```

### 步骤 4：测试联动

```bash
# 测试 master-quant 直接运行回测
exec(command="cd /home/admin/.openclaw/workspace/master && /home/admin/miniconda3/envs/vnpy_env/bin/python vnpy_backtest/orchestrator.py")
```

---

## 七、预期效果

整合完成后：

1. **不再丢三落四**：用 OpenCode memory_* 替代有 bug 的脚本
2. **调度更高效**：master 可以直接 read/exec，不用事事调度子智能体
3. **子智能体恢复**：中断的任务可以恢复
4. **4 种模式正常运行**：全量抓取、增量抓取、回测、每日选股

---

**需要你确认：**

1. 是否同意用 OpenCode memory_* 替代 memory_manager.py？
2. 是否立即执行"恢复子智能体"？
3. 是否有其他优先级更高的问题？