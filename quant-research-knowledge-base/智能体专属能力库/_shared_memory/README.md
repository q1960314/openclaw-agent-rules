# 共享记忆访问指南 - 子智能体专用

## 访问路径

共享记忆系统位于 master-quant 工作空间：

```
/home/admin/.openclaw/workspace/master/memory/
├── core_memory.yaml        # 核心记忆（用户画像、红线规则）
├── working_memory.json     # 工作记忆（错误、决策、待办）
├── memory_manager.py       # 记忆管理器
├── agent_memory.py         # 子智能体接口
├── pressure_monitor.py     # 压力监控
└── staleness_detector.py   # 陈旧检测
```

## 使用方法

### 方法一：通过 Python 脚本访问

```python
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/master/memory')

from agent_memory import AgentMemory

# 初始化（传入你的智能体名称）
memory = AgentMemory("coder")

# 获取用户偏好
user = memory.get_user_preferences()
print(f"用户: {user['name']}, 风险偏好: {user['risk_preference']}")

# 获取红线规则
red_lines = memory.get_red_lines()
for rule in red_lines:
    print(f"红线: {rule['rule']}")

# 检查行为是否违反红线
result = memory.check_red_line("自动买入股票")
if not result['allowed']:
    print(f"拒绝: {result['reason']}")

# 记录错误
memory.log_error("编译失败", "缺少依赖 pandas")

# 记录决策
memory.log_decision("采用均线策略", "回测显示胜率 65%")

# 添加待办
memory.add_todo("修复 bug #123", "high")

# 获取记忆摘要
print(memory.get_memory_summary())
```

### 方法二：命令行访问

```bash
# 查看记忆摘要
python /home/admin/.openclaw/workspace/master/memory/agent_memory.py \
  --agent coder --action summary

# 获取用户信息
python /home/admin/.openclaw/workspace/master/memory/agent_memory.py \
  --agent coder --action user

# 检查红线
python /home/admin/.openclaw/workspace/master/memory/agent_memory.py \
  --agent coder --check "自动交易"

# 记录错误
python /home/admin/.openclaw/workspace/master/memory/agent_memory.py \
  --agent coder --log-error "错误信息"

# 记录决策
python /home/admin/.openclaw/workspace/master/memory/agent_memory.py \
  --agent coder --log-decision "决策内容"
```

## 必须遵守的红线规则

| ID | 规则 | 说明 |
|----|------|------|
| R001 | 绝不自动交易 | 所有交易需用户书面确认 |
| R002 | 绝不修改实盘参数 | 未经用户授权不修改 |
| R003 | 绝不泄露敏感信息 | API Key、密码等严格保密 |
| R004 | 风控第一 | 任何决策优先考虑风险 |

## 任务完成后的记忆更新

```python
# 1. 记录完成的任务
memory.log_decision(f"任务完成: {task_id}", f"结果: {result}")

# 2. 如果有错误，记录到避坑指南
if error:
    memory.log_error(error, context)

# 3. 清理待办
memory.complete_todo(task_keyword)
```

## 注意事项

1. **只读权限**：红线规则只能读取，不能修改
2. **受限写入**：只能写入错误、决策、待办到工作记忆
3. **标签自动添加**：所有写入会自动添加智能体名称标签
4. **知识库沉淀**：重要的经验需要同时沉淀到专属能力库