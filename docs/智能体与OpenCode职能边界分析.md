# 智能体与 OpenCode 职能边界分析

## 一、当前架构问题分析

### 问题1：工具与角色混淆

```
当前状态：
┌─────────────────────────────────────────┐
│           master-quant                   │
│  ┌─────────────────────────────────┐    │
│  │ 工具: exec, sessions_send, message │    │
│  └─────────────────────────────────┘    │
│              ↓ 直接执行                  │
│         Python脚本                       │
│              ↓ 越过                      │
│         子智能体                         │
└─────────────────────────────────────────┘

问题：master-quant 可以直接用 exec 执行任何代码，越过子智能体
```

### 问题2：职责边界模糊

| 任务 | 谁应该执行？ | 当前实际情况 |
|-----|-------------|-------------|
| 运行回测 | backtest-engine | master-quant 用 exec 直接运行 |
| 抓取数据 | data-collector | master-quant 用 exec 直接运行 |
| 测试代码 | test-expert | master-quant 用 exec 直接运行 |
| 开发代码 | coder | master-quant 用 exec 直接修改 |

### 问题3：资源浪费

```
当前：14个子智能体存在，但很多时候 master-quant 直接用 exec 执行任务
结果：子智能体变成摆设，没有发挥价值
```

---

## 二、根本原因

### 原因1：工具权限过大

master-quant 拥有 `exec` 工具，可以执行任何代码，导致：
- 直接运行回测 → 越过 backtest-engine
- 直接抓取数据 → 越过 data-collector
- 直接测试代码 → 越过 test-expert

### 原因2：没有明确边界

当前 TOOLS.md 中：
```markdown
| 工具 | 用途 | 示例 |
|------|------|------|
| `exec` | 执行脚本 | 知识库检索、留痕归档 |
```

问题：`exec` 的用途定义太宽泛，"执行脚本" 可以是任何操作

### 原因3：子智能体缺乏执行能力

子智能体只能接收消息、返回结果，但：
- 没有自己的执行环境
- 无法直接操作代码
- 只能"建议"而非"执行"

---

## 三、解决方案

### 方案1：重新定义 exec 使用边界

```markdown
## master-quant 的 exec 使用规则

### ✅ 允许直接执行（不需要派发子智能体）
| 操作类型 | 示例 | 原因 |
|---------|------|-----|
| 快速查询 | 查看文件状态、检查配置 | 简单操作，无需专业判断 |
| 知识库操作 | kb-search.sh, kb-update.sh | 管理类操作 |
| 状态检查 | 查看后台任务状态 | 监控类操作 |
| 文件读取 | cat, ls, head | 信息获取 |

### ❌ 禁止直接执行（必须派发子智能体）
| 操作类型 | 派发给 | 原因 |
|---------|-------|-----|
| 代码开发/修改 | coder | 专业职责 |
| 策略设计 | strategy-expert | 专业职责 |
| 测试验证 | test-expert | 专业职责 |
| 参数优化 | parameter-evolver | 专业职责 |
| 回测运行 | backtest-engine | 专业职责 |
| 数据抓取 | data-collector | 专业职责 |
| 因子分析 | factor-miner | 专业职责 |
```

### 方案2：子智能体增强执行能力

```python
# 子智能体执行模型
class AgentExecutor:
    """子智能体执行器"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.venv = "/home/admin/miniconda3/envs/vnpy_env/bin/python"
    
    def run_code(self, script_path: str, background: bool = False):
        """运行代码（子智能体专用）"""
        command = f"{self.venv} {script_path}"
        # 子智能体可以调用 exec 执行代码
        return exec(command, background=background)
    
    def modify_code(self, file_path: str, changes: dict):
        """修改代码（coder 专用）"""
        # 只允许 coder 使用此方法
        if self.agent_name != "coder":
            raise PermissionError("只有 coder 可以修改代码")
        # 执行修改...
```

### 方案3：建立任务派发优先级

```
用户请求
    ↓
master-quant 判断任务类型
    ↓
┌─────────────────────────────────────────┐
│ 任务类型判断                             │
├─────────────────────────────────────────┤
│ 1. 简单查询 → master-quant 直接执行      │
│ 2. 专业任务 → 派发对应子智能体           │
│ 3. 复合任务 → 拆解后派发多个子智能体     │
└─────────────────────────────────────────┘
    ↓
子智能体执行（可能调用 exec）
    ↓
返回结果给 master-quant
    ↓
master-quant 汇总后汇报用户
```

---

## 四、优化后的架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户 (90)                               │
│                         ↓                                   │
│              master-quant (唯一对话窗口)                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 允许直接执行:                                         │    │
│  │  - 快速查询 (ls, cat, grep)                          │    │
│  │  - 知识库操作 (kb-search.sh)                         │    │
│  │  - 状态检查 (sessions_list)                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 必须派发子智能体:                                     │    │
│  │  - 代码开发 → coder                                  │    │
│  │  - 策略设计 → strategy-expert                        │    │
│  │  - 测试验证 → test-expert                            │    │
│  │  - 参数优化 → parameter-evolver                      │    │
│  │  - 回测运行 → backtest-engine                        │    │
│  │  - 数据抓取 → data-collector                         │    │
│  │  - 因子分析 → factor-miner                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│         ┌──────────────────────────────────────┐            │
│         │           子智能体池                   │            │
│         │                                      │            │
│         │  每个子智能体可以:                     │            │
│         │  - 接收任务                           │            │
│         │  - 调用 exec 执行代码                  │            │
│         │  - 返回结果给 master-quant             │            │
│         └──────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、具体实施建议

### 建议1：更新 TOOLS.md

```markdown
## exec 使用规则

### ✅ 允许的操作（白名单）
1. 快速查询：ls, cat, head, tail, grep, find
2. 知识库操作：scripts/kb-search.sh, scripts/kb-update.sh
3. 状态检查：sessions_list, sessions_history
4. 环境检查：python --version, pip list

### ❌ 禁止的操作（黑名单）
1. 代码开发：修改 .py 文件 → 派发 coder
2. 运行回测：python run_backtest.py → 派发 backtest-engine
3. 数据抓取：python fetch_data.py → 派发 data-collector
4. 参数优化：python optimize.py → 派发 parameter-evolver
5. 测试运行：python test.py → 派发 test-expert
```

### 建议2：创建子智能体执行脚本

```bash
# /home/admin/.openclaw/workspace/master/scripts/agent_exec.sh
#!/bin/bash
# 子智能体执行脚本

AGENT_NAME=$1
TASK_TYPE=$2
TASK_CMD=$3

echo "【子智能体执行】"
echo "智能体: $AGENT_NAME"
echo "任务类型: $TASK_TYPE"
echo "执行命令: $TASK_CMD"

# 检查权限
case $TASK_TYPE in
    "code_modify")
        if [ "$AGENT_NAME" != "coder" ]; then
            echo "错误: 只有 coder 可以修改代码"
            exit 1
        fi
        ;;
    "backtest")
        if [ "$AGENT_NAME" != "backtest-engine" ] && [ "$AGENT_NAME" != "test-expert" ]; then
            echo "错误: 只有 backtest-engine 或 test-expert 可以运行回测"
            exit 1
        fi
        ;;
    "data_fetch")
        if [ "$AGENT_NAME" != "data-collector" ]; then
            echo "错误: 只有 data-collector 可以抓取数据"
            exit 1
        fi
        ;;
esac

# 执行命令
eval $TASK_CMD
```

### 建议3：建立任务路由表

```python
# /home/admin/.openclaw/workspace/master/config/task_routing.yaml

task_routing:
  # 代码相关
  code_develop:
    agent: coder
    description: 代码开发、修改、重构
  code_review:
    agent: coder
    description: 代码审查
  code_fix:
    agent: coder
    description: Bug修复
  
  # 策略相关
  strategy_design:
    agent: strategy-expert
    description: 策略逻辑设计
  strategy_optimize:
    agent: strategy-expert
    description: 策略优化
  
  # 测试相关
  test_run:
    agent: test-expert
    description: 运行测试
  test_verify:
    agent: test-expert
    description: 验证结果
  
  # 回测相关
  backtest_run:
    agent: backtest-engine
    description: 运行回测
  backtest_analyze:
    agent: backtest-engine
    description: 回测分析
  
  # 数据相关
  data_fetch:
    agent: data-collector
    description: 数据抓取
  data_clean:
    agent: data-collector
    description: 数据清洗
  
  # 参数相关
  param_optimize:
    agent: parameter-evolver
    description: 参数优化
  
  # 因子相关
  factor_mine:
    agent: factor-miner
    description: 因子挖掘
  factor_analyze:
    agent: factor-miner
    description: 因子分析
  
  # 文档相关
  doc_manage:
    agent: doc-manager
    description: 文档管理
  
  # 知识库相关
  knowledge_archive:
    agent: knowledge-steward
    description: 知识库归档
```

---

## 六、预期效果

### 优化前
```
用户: 运行回测
master-quant: [直接用 exec 运行 python run_backtest.py]
问题: 越过 backtest-engine，子智能体没用上
```

### 优化后
```
用户: 运行回测
master-quant: [判断任务类型 → 回测]
master-quant: [派发给 backtest-engine]
backtest-engine: [调用 exec 运行 python run_backtest.py]
backtest-engine: [返回结果给 master-quant]
master-quant: [汇总后汇报用户]
效果: 子智能体发挥作用，职责清晰
```

---

## 七、更新记录

| 日期 | 更新内容 |
|-----|---------|
| 2026-03-25 | 创建文档，分析职能边界问题 |