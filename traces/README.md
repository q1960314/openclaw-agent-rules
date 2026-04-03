# 全链路留痕目录

## 目录结构

```
traces/
├── tasks/           # 任务留痕
│   ├── TASK-20260310-001/
│   │   ├── step1.json
│   │   ├── step2.json
│   │   └── ...
├── reviews/         # 复盘留痕
│   ├── REVIEW-20260310-001.json
├── iterations/      # 迭代留痕
│   ├── ITER-20260310-001.json
└── archives/        # 归档留痕
    └── 2026-03/
```

## 留痕格式（JSON）

```json
{
  "timestamp": "2026-03-10T00:00:00+08:00",
  "task_id": "TASK-20260310-001",
  "step": 1,
  "agent": "master-quant",
  "action": "需求接收",
  "input": {"user_request": "xxx"},
  "output": {"plan": "xxx"},
  "status": "success",
  "duration_ms": 1000
}
```

## 留痕规则

1. **每个步骤** 必须留痕
2. **所有决策** 必须留痕
3. **异常情况** 必须留痕
4. **无留痕** 的执行结果直接打回

## 归档脚本

```bash
# 归档任务留痕
./scripts/trace-archive.sh --task TASK-20260310-001

# 归档复盘留痕
./scripts/trace-archive.sh --review REVIEW-20260310-001

# 清理过期留痕（>90 天）
./scripts/trace-archive.sh --cleanup --older-than 90d
```
