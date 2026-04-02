# Worker 架构 - 完整实施文档

> 创建时间：2026-03-27 23:00  
> 状态：**已落地实施**

---

## 一、架构概述

### 核心设计

```
用户需求
   ↓
Master 调度器 (master_dispatcher.py)
   ↓
任务队列 (task_queue.py)
   ↓
Worker 进程 (worker_base.py)
   ↓
独立验收 (verdict.json)
   ↓
Master 决定下一步
```

### 关键特性

1. **强制 claim** - 没有 claim 不能执行
2. **强制 artifacts** - 没有产物不能完成
3. **独立验收** - verifier 独立于 executor
4. **任务队列** - 异步解耦，支持并发

---

## 二、文件结构

```
/home/admin/.openclaw/workspace/master/scripts/
├── task_queue.py          # 任务队列系统
├── worker_base.py         # Worker 基类 + 所有 Worker 实现
├── master_dispatcher.py   # Master 调度器
└── run_worker.sh          # Worker 启动脚本
```

---

## 三、使用方法

### 3.1 启动 Master 调度器

```bash
cd /home/admin/.openclaw/workspace/master/scripts
python3 master_dispatcher.py "修复 workflow_run_opencode.py 中的命令路径问题"
```

### 3.2 手动启动 Worker

```bash
# Coder Worker
python3 worker_base.py coder

# Test-Expert Worker
python3 worker_base.py test-expert

# Doc-Manager Worker
python3 worker_base.py doc-manager

# Knowledge-Steward Worker
python3 worker_base.py knowledge-steward
```

### 3.3 创建任务

```python
from task_queue import create_task

create_task(
    task_id='TASK-20260327-001',
    task_type='code_fix',
    title='修复命令路径问题',
    owner_role='coder',
    validator_role='test-expert',
    input_refs=['scripts/workflow_run_opencode.py'],
    required_artifacts=['diff.patch', 'changed_files.json', 'run.log'],
    success_criteria=['命令路径正确']
)
```

### 3.4 领取任务

```python
from worker_base import CoderWorker

worker = CoderWorker()
if worker.claim_task():
    worker.execute()
```

---

## 四、任务状态流转

```
queued → claimed → running → completed → verified → finalized
              ↓            ↓
          timeout      failed
              ↓            ↓
          retry        retry
```

---

## 五、Worker 职责

### Coder Worker

- **职责**: 代码修复与功能实现
- **输入**: spec.json, input_refs
- **输出**: diff.patch, changed_files.json, run.log
- **验收**: test-expert

### Test-Expert Worker

- **职责**: 独立验收
- **输入**: artifacts/
- **输出**: verdict.json, test_report.md
- **验收**: 无（最终验收）

### Doc-Manager Worker

- **职责**: 文档整理交付
- **输入**: delivery_pack.md
- **输出**: doc_path.txt, delivery_pack.md
- **验收**: knowledge-steward

### Knowledge-Steward Worker

- **职责**: 知识沉淀归档
- **输入**: 所有 artifacts
- **输出**: kb_write.json, kb_index_update.json
- **验收**: 无（最终归档）

---

## 六、OpenCode 集成

### 在 Coder Worker 中调用 OpenCode

```python
def _run_opencode(self):
    import subprocess
    
    prompt = f"""修复以下文件：
{', '.join(self.current_task.input_refs)}

成功标准：
{chr(10).join(self.current_task.success_criteria)}
"""
    
    cmd = [
        "/home/admin/.npm-global/bin/opencode", "run",
        "--format", "json",
        "--agent", "plan",
        "--model", "bailian/qwen3-coder-plus",
        "--dir", "/data/agents/master",
        prompt
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    
    # 写入 artifacts
    ...
```

---

## 七、Master 调度流程

### 完整流程

```python
dispatcher = MasterDispatcher()

# 1. 接收需求
request = "修复 workflow_run_opencode.py 中的命令路径问题"

# 2. 分析并分派任务
results = dispatcher.run(request)

# 3. 监控进度
# 自动监控，等待任务完成

# 4. 决定下一步
# 根据完成情况决定重试或继续
```

### 异步并发

```python
# Master 可以同时分派多个任务
tasks = [
    {"owner_role": "coder", ...},
    {"owner_role": "strategy-expert", ...},
    {"owner_role": "backtest-engine", ...}
]

for task in tasks:
    dispatcher.dispatch_task(task)
    dispatcher.wake_worker(task["owner_role"])

# 所有 Worker 并发执行
results = dispatcher.monitor_tasks()
```

---

## 八、与 sessions_send 的区别

| 维度 | sessions_send | Worker 架构 |
|------|--------------|------------|
| **通信方式** | 发消息 | 任务队列 |
| **约束** | 软约束 | 硬约束 |
| **claim** | 可选 | 强制 |
| **artifacts** | 可选 | 强制 |
| **验收** | 自检 | 独立验收 |
| **状态** | 无状态 | 强制更新 |
| **执行** | 可选择 | 必须执行 |

---

## 九、测试验证

### 测试任务创建

```bash
cd /home/admin/.openclaw/workspace/master/scripts
python3 -c "
from task_queue import create_task
success = create_task(
    task_id='TASK-TEST-001',
    task_type='code_fix',
    title='测试',
    owner_role='coder',
    validator_role='test-expert',
    input_refs=[],
    required_artifacts=['diff.patch'],
    success_criteria=['测试']
)
print('任务创建:', '成功' if success else '失败')
"
```

### 测试 Worker 执行

```bash
python3 -c "
from worker_base import CoderWorker
worker = CoderWorker()
if worker.claim_task():
    print('任务领取：成功')
    print('任务 ID:', worker.current_task.task_id)
    success = worker.execute()
    print('任务执行:', '成功' if success else '失败')
"
```

---

## 十、生产部署

### 后台运行 Worker

```bash
# 使用 systemd 运行 Worker
cat > /etc/systemd/user/coder-worker.service <<EOF
[Unit]
Description=Coder Worker

[Service]
ExecStart=/usr/bin/python3 /home/admin/.openclaw/workspace/master/scripts/worker_base.py coder
Restart=always
WorkingDirectory=/home/admin/.openclaw/workspace/master/scripts

[Install]
WantedBy=default.target
EOF

systemctl --user enable coder-worker
systemctl --user start coder-worker
```

### 监控 Worker 状态

```bash
# 查看 Worker 日志
journalctl --user -u coder-worker -f

# 查看任务队列
python3 -c "from task_queue import TaskQueue; q=TaskQueue(); print(q.list_pending())"
```

---

## 十一、下一步扩展

### 添加更多 Worker

```python
class StrategyExpertWorker(Worker):
    def __init__(self):
        super().__init__("strategy-expert")
    
    def execute_core(self) -> Dict[str, Path]:
        # 实现策略分析逻辑
        ...
```

### 集成更多执行引擎

- OpenCode（代码生成）
- 回测引擎（backtest-engine）
- 数据采集（data-collector）

### 添加任务依赖

```python
# 任务 B 依赖任务 A 完成
task_b = {
    "task_id": "TASK-B",
    "depends_on": ["TASK-A"],
    ...
}
```

---

## 十二、总结

### 已实现

- ✅ 任务队列系统
- ✅ Worker 基类
- ✅ Coder/Test/Doc/Knowledge Worker
- ✅ Master 调度器
- ✅ 强制 claim/artifacts/验收
- ✅ OpenCode 集成

### 待扩展

- ⏳ 更多 Worker（strategy-expert, backtest-engine 等）
- ⏳ 任务依赖管理
- ⏳ 生产部署（systemd）
- ⏳ 监控仪表盘

---

**架构已落地，可以开始使用。**
