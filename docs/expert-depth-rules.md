# Expert Depth Rules

Updated: 2026-03-28 17:22 Asia/Shanghai

## 1. 目的

expert depth rules 用于把关键研究型 worker 从“有结构化模板”继续推进到“满足最小专家深度门槛”。

当前不是完整专家评测体系；
而是最小深度门槛。

---

## 2. 当前覆盖 worker
- `strategy-expert`
- `parameter-evolver`
- `factor-miner`

---

## 3. 当前最小深度门槛

### strategy-expert
至少要求：
- hypotheses >= 2
- candidate_solutions >= 2
- validation_path >= 2
- risk_notes >= 2
- why_not_others 非空且不能过弱

### parameter-evolver
至少要求：
- sensitive_parameters >= 2
- robust_ranges >= 1
- fragile_ranges >= 1
- tuning_sequence >= 2
- validation_plan >= 2

### factor-miner
至少要求：
- factor_hypotheses >= 2
- economic_rationales >= 2
- candidate_factors >= 2
- failure_scenarios >= 2
- validation_plan >= 2

---

## 4. 当前最准确的说法

现在可以说：
- 三个关键研究型 worker 已进入“结构化 + 深度门槛”阶段
- test-expert 已开始检查最小专家深度

但不能说：
- 已完成成熟专家能力体系
- 已完成完整深度 benchmark
- 已完成真实长期专家能力评分系统
