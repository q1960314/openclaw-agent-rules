# Ecosystem Stage Card

Updated: 2026-03-28 18:48 Asia/Shanghai

## 1. 目的

ecosystem stage card 用于把系统当前阶段压缩成一张“诚实阶段卡”，避免只堆很多散乱指标。

它当前不是完整成熟度模型；
它是最小阶段表达骨架。

---

## 2. 当前来源

stage card 当前综合：
- `latest_cycle`
- `health_dashboard`
- `recovery_dashboard`
- `lifecycle_dashboard`
- formalization / evaluation / runtime / closure readiness 现状信号

特别是现在已纳入：
- `quality_grade_counts`
- `quality_average_score`
- `formalization_state_counts`
- `closure_counts`
- `release_ready_candidates`
- `manual_review_gates`
- `approval_required_count`
- `pre_release_ready_count`
- `closure_consistency_ready_count`
- `rollback_ready_count`
- `closure_readiness_state`

---

## 3. 当前输出
- `ecosystem_stage_card.json`
- `ecosystem_stage_card.md`
- `latest_stage_card.json`
- `latest_stage_card.md`

并且当前已新增：
- `phase_completion_state`
- `closure_readiness_state`
- `completion_definition`
- `next_action_card`
- `remaining_gaps`

---

## 4. 当前作用

stage card 现在回答：
- 系统处于哪个阶段
- 哪些说法是可以成立的
- 哪些说法还不能成立
- skeleton / agent_depth / runtime / formalization / evaluation 这些轴大致走到哪了
- 当前这一阶段什么时候算完成
- 当前 closure readiness 到哪一步
- 下一步最优先推进什么

---

## 5. 当前最准确的说法

现在可以说：
- 系统已有最小阶段卡
- 系统能更集中地表达“自己已经到哪一步”
- 阶段卡已开始吸收质量、formalization、closure readiness、consistency-check 联动信号
- 阶段卡已开始给出阶段完成定义与下一步建议

但不能说：
- 已完成严格成熟度评估体系
- 已完成长期阶段评分模型
- 已完成自动长期路线规划系统
