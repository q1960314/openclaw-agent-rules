# Evaluation Runtime

Updated: 2026-03-28 15:58 Asia/Shanghai

## 1. 目的

evaluation runtime 用于把当前系统从“通过 / 拒绝”推进到“有最小质量分层判断”。

它当前不是完整 benchmark / regression / leaderboard 系统；
它只是最小评分骨架。

---

## 2. Runtime Module

- `scripts/runtime/evaluation_runtime.py`
- `protocols/quality_score.schema.json`

---

## 3. 当前已实现能力

### 3.1 质量分输出
`test-expert` 现在会额外产出：
- `quality_score.json`
- `quality_score.md`

### 3.2 当前评分维度
- `artifact_completeness`
- `structural_quality`
- `validation_outcome`
- `release_readiness`

### 3.3 当前输出字段
- `score`
- `grade`
- `blocking_flags`
- `summary`

### 3.4 当前观察面接入
质量分现在已接入：
- `health_dashboard`
- `recovery_dashboard`
- `lifecycle_dashboard`
- `worker_runtime_scheduler latest_cycle`
- `workflow_dashboard.py`

当前可看到：
- `quality_grade_counts`
- `quality_average_score`
- 单任务 `quality_score / quality_grade`

---

## 4. 当前最准确的说法

现在可以说：
- 系统已经有最小质量评分骨架
- test-expert 已不再只有二元通过/拒绝
- 质量分已进入运维观察面

但不能说：
- 已完成完整评测体系
- 已完成回归题集
- 已完成 agent leaderboard
- 已完成长期质量基准系统
