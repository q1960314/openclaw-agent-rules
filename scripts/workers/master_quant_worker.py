#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from task_queue import TaskQueue  # noqa: E402
from worker_base import WorkerBase  # noqa: E402
from decision_engine import analyze_request, auto_retry_allowed  # noqa: E402

DEFAULT_CODE_ROOT = '/data/agents/master'


class MasterQuantWorker(WorkerBase):
    def __init__(self):
        super().__init__('master-quant')

    def _extract_target_files(self, objective: str) -> list[str]:
        pattern = re.compile(r"(?<!\w)([A-Za-z0-9_./-]+\.[A-Za-z0-9_+-]+)")
        seen: list[str] = []
        for item in pattern.findall(objective):
            cleaned = item.strip().strip('"\'')
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen[:10]

    def _merge_unique(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                cleaned = str(item).strip()
                if cleaned and cleaned not in merged:
                    merged.append(cleaned)
        return merged

    def _analysis_artifact_refs(self, parent_task_dir: Path) -> list[str]:
        return [
            str(parent_task_dir / 'task.json'),
            str(parent_task_dir / 'artifacts' / 'intake_analysis.json'),
            str(parent_task_dir / 'artifacts' / 'dependency_plan.json'),
        ]

    def _build_execution_brief(self, parent_task_dir: Path, task: dict[str, Any], analysis: dict[str, Any], child_task: dict[str, Any]) -> dict[str, Any]:
        dependency_plan = analysis.get('dependency_plan', {})
        return {
            'parent_task_id': parent_task_dir.name,
            'child_task_id': child_task.get('task_id'),
            'child_role': child_task.get('role'),
            'objective_summary': analysis.get('objective_summary'),
            'main_objective': analysis.get('main_objective'),
            'objective_hierarchy': analysis.get('objective_hierarchy', []),
            'risk_assessment': analysis.get('risk_assessment', []),
            'clarification_priority': analysis.get('clarification_priority'),
            'clarification_questions': analysis.get('clarification_questions', []),
            'manual_review_required': analysis.get('manual_review_required', False),
            'validation_focus': analysis.get('acceptance_contract', {}).get('validation_focus'),
            'required_outcomes': analysis.get('acceptance_contract', {}).get('required_outcomes', []),
            'stop_when': analysis.get('stop_policy', {}).get('stop_when', []),
            'continue_when': analysis.get('stop_policy', {}).get('continue_when', []),
            'escalate_when': analysis.get('stop_policy', {}).get('escalate_when', []),
            'execution_sequence': analysis.get('execution_sequence', []),
            'recent_learning_context': analysis.get('recent_learning_context', {}),
            'recent_learning_guidance': analysis.get('recent_learning_guidance', []),
            'support_roles': dependency_plan.get('support_roles', []),
            'review_checkpoints': dependency_plan.get('review_checkpoints', []),
            'target_files': child_task.get('metadata', {}).get('target_files', []),
            'source_objective': task.get('objective'),
        }

    def _build_execution_brief_markdown(self, brief: dict[str, Any]) -> str:
        lines = [
            '# Master Execution Brief',
            '',
            f"- parent_task_id: {brief.get('parent_task_id')}",
            f"- child_task_id: {brief.get('child_task_id')}",
            f"- child_role: {brief.get('child_role')}",
            f"- objective_summary: {brief.get('objective_summary')}",
            f"- clarification_priority: {brief.get('clarification_priority')}",
            f"- manual_review_required: {brief.get('manual_review_required')}",
            f"- validation_focus: {brief.get('validation_focus')}",
            '',
            '## Objective Hierarchy',
        ]
        for item in brief.get('objective_hierarchy', []):
            lines.append(f"- level={item.get('level')} | objective={item.get('objective')} | success_signal={item.get('success_signal')}")
        lines.extend(['', '## Risk Assessment'])
        for item in brief.get('risk_assessment', []):
            lines.append(f"- {item.get('tag')} | priority={item.get('priority')} | rationale={item.get('rationale')}")
        lines.extend(['', '## Clarification Questions'])
        for item in brief.get('clarification_questions', []):
            lines.append(f'- {item}')
        lines.extend(['', '## Execution Sequence'])
        for item in brief.get('execution_sequence', []):
            lines.append(f'- {item}')
        lines.extend(['', '## Recent Learning Context'])
        recent_learning = brief.get('recent_learning_context', {}) or {}
        lines.append(f"- available: {recent_learning.get('available')}")
        lines.append(f"- recent_task_count: {recent_learning.get('recent_task_count')}")
        lines.append(f"- dominant_expert_role: {recent_learning.get('dominant_expert_role')}")
        lines.append(f"- adaptive_dominant_next_role: {recent_learning.get('adaptive_dominant_next_role')}")
        lines.append(f"- focus_signals: {recent_learning.get('focus_signals')}")
        lines.extend(['', '## Recent Learning Guidance'])
        for item in brief.get('recent_learning_guidance', []):
            lines.append(f'- {item}')
        lines.extend(['', '## Required Outcomes'])
        for item in brief.get('required_outcomes', []):
            lines.append(f'- {item}')
        lines.extend(['', '## Stop / Continue / Escalate'])
        lines.append('### stop_when')
        for item in brief.get('stop_when', []):
            lines.append(f'- {item}')
        lines.append('### continue_when')
        for item in brief.get('continue_when', []):
            lines.append(f'- {item}')
        lines.append('### escalate_when')
        for item in brief.get('escalate_when', []):
            lines.append(f'- {item}')
        return '\n'.join(lines) + '\n'

    def _build_child_task(self, parent_task_dir: Path, task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        objective = task.get('objective', 'execute specialist task')
        analysis = analyze_request(objective)
        role = analysis['suggested_role']
        mode = analysis['execution_mode']
        target_files = self._extract_target_files(objective)
        parent_constraints = list(task.get('constraints', []))
        derived_constraints = list(analysis.get('constraints', []))
        risk_tags = analysis.get('risk_tags', [])
        acceptance_hints = analysis.get('acceptance_hints', [])
        derived_acceptance = list(analysis.get('acceptance_criteria', []))
        input_artifacts = self._analysis_artifact_refs(parent_task_dir)

        if role == 'data-collector':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '必须执行数据快照、数据校验、质量评分',
                    '必须输出 data_snapshot.json',
                    '必须输出 data_check.json',
                    '必须输出 data_quality_score.json',
                    '必须输出 result_summary.md',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                [
                    '原生数据检查命令执行成功',
                    '生成 data_snapshot.json',
                    '生成 data_check.json',
                    '生成 data_quality_score.json',
                    '生成 result_summary.md',
                ],
                acceptance_hints,
            )
            required_artifacts = ['data_snapshot.json', 'data_check.json', 'data_quality_score.json', 'result_summary.md']
            child_suffix = 'DATA'
            task_type = 'p1_data'
            engine = 'native'
        elif role == 'ops-monitor':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '必须执行 openclaw status 与工作流状态检查',
                    '必须输出 ops_report.md',
                    '必须输出 ops_summary.json',
                    '必须输出 result_summary.md',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                [
                    '原生诊断命令执行成功',
                    '生成 ops_report.md',
                    '生成 ops_summary.json',
                    '生成 result_summary.md',
                ],
                acceptance_hints,
            )
            required_artifacts = ['ops_report.md', 'ops_summary.json', 'health_dashboard.json', 'health_dashboard.md', 'recovery_dashboard.json', 'recovery_dashboard.md', 'lifecycle_dashboard.json', 'lifecycle_dashboard.md', 'ecosystem_stage_card.json', 'ecosystem_stage_card.md', 'result_summary.md']
            child_suffix = 'OPS'
            task_type = 'p1_ops'
            engine = 'native'
        elif role == 'backtest-engine':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '必须在 vnpy_env 中执行回测',
                    '必须输出 backtest_metrics.json',
                    '必须输出 backtest_report.md',
                    '必须输出 result_summary.md',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                [
                    '原生回测命令执行成功',
                    '生成 backtest_metrics.json',
                    '生成 backtest_report.md',
                    '生成 result_summary.md',
                ],
                acceptance_hints,
            )
            required_artifacts = ['backtest_metrics.json', 'backtest_report.md', 'result_summary.md']
            child_suffix = 'BACKTEST'
            task_type = 'p1_backtest'
            engine = 'native'
        elif role == 'factor-miner':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '默认只输出因子研究方案，不做高风险代码改动',
                    '必须给出候选因子、研究方向、验证建议',
                    '如果建议改代码，必须指出目标文件和最小改动路径',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                ['OpenCode 调用成功', '生成 factor_plan.md', '生成 factor_candidate.json', '生成 result_summary.md'],
                acceptance_hints,
            )
            required_artifacts = ['factor_plan.md', 'factor_candidate.json', 'factor_analysis.json', 'factor_depth.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'FACTOR'
            task_type = 'p1_factor'
            engine = 'opencode'
        elif role == 'finance-learner':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '默认只输出金融研究/学习结论，不做高风险代码改动',
                    '必须给出核心结论、可落地启发和后续验证建议',
                    '如果建议改代码，必须指出目标文件和最小改动路径',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                ['OpenCode 调用成功', '生成 finance_note.md', '生成 finance_learning.json', '生成 result_summary.md'],
                acceptance_hints,
            )
            required_artifacts = ['finance_note.md', 'finance_learning.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'FINANCE'
            task_type = 'p1_finance'
            engine = 'opencode'
        elif role == 'sentiment-analyst':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '默认只输出舆情/情绪分析方案，不做高风险代码改动',
                    '必须给出情绪结论、主要驱动、风险提示和验证建议',
                    '如果建议改代码，必须指出目标文件和最小改动路径',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                ['OpenCode 调用成功', '生成 sentiment_plan.md', '生成 sentiment_candidate.json', '生成 result_summary.md'],
                acceptance_hints,
            )
            required_artifacts = ['sentiment_plan.md', 'sentiment_candidate.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'SENTIMENT'
            task_type = 'p1_sentiment'
            engine = 'opencode'
        elif role == 'strategy-expert':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '默认只输出策略方案，不做高风险代码改动',
                    '必须明确诊断、方案、验证路径',
                    '如果建议改代码，必须指出目标文件和最小改动路径',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                ['OpenCode 调用成功', '生成 strategy_plan.md', '生成 strategy_candidate.json', '生成 result_summary.md'],
                acceptance_hints,
            )
            required_artifacts = ['strategy_plan.md', 'strategy_candidate.json', 'strategy_analysis.json', 'strategy_depth.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'STRATEGY'
            task_type = 'p1_strategy'
            engine = 'opencode'
        elif role == 'parameter-evolver':
            constraints = self._merge_unique(
                parent_constraints,
                derived_constraints,
                [
                    '默认只输出参数优化方案，不做高风险代码改动',
                    '必须给出参数候选、边界、优先级和验证建议',
                    '如果建议改代码，必须指出目标文件和最小改动路径',
                ],
            )
            acceptance = self._merge_unique(
                derived_acceptance,
                ['OpenCode 调用成功', '生成 parameter_plan.md', '生成 parameter_candidate.json', '生成 result_summary.md'],
                acceptance_hints,
            )
            required_artifacts = ['parameter_plan.md', 'parameter_candidate.json', 'parameter_analysis.json', 'parameter_depth.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'PARAM'
            task_type = 'p1_parameter'
            engine = 'opencode'
        else:
            constraints = self._merge_unique(parent_constraints, derived_constraints)
            acceptance = self._merge_unique(derived_acceptance, acceptance_hints)
            constraints.extend(['必须输出 diff.patch', '必须输出 changed_files.json', '必须输出 result_summary.md'])
            if mode == 'build':
                constraints.extend(['必须在隔离 worktree 中执行', '禁止直接污染主代码仓', '只做最小必要改动'])
                acceptance.extend(['OpenCode 调用成功', '生成真实 git diff patch', 'changed_files.json 非空', 'worktree_path.txt 存在'])
                required_artifacts = ['diff.patch', 'changed_files.json', 'result_summary.md', 'opencode_result.json', 'worktree_path.txt']
            else:
                constraints.extend(['默认只输出计划，不做高风险改动', '如果需要真实修改，必须在摘要中明确指出'])
                acceptance.extend(['OpenCode 调用成功', '生成 opencode_result.md', '生成 result_summary.md'])
                required_artifacts = ['diff.patch', 'changed_files.json', 'result_summary.md', 'opencode_result.json']
            child_suffix = 'CODER'
            task_type = 'p1_coder'
            engine = 'opencode'

        child_task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{child_suffix}"
        child_task = {
            'task_id': child_task_id,
            'role': role,
            'objective': objective,
            'constraints': self._merge_unique(constraints),
            'acceptance_criteria': self._merge_unique(acceptance),
            'input_artifacts': input_artifacts,
            'upstream': parent_task_dir.name,
            'downstream': 'test-expert',
            'engine': engine,
            'priority': task.get('priority', 'high'),
            'metadata': {
                'task_type': task_type,
                'worker_role': role,
                'parent_task_id': parent_task_dir.name,
                'source_role': 'master-quant',
                'opencode_mode': mode,
                'code_root': DEFAULT_CODE_ROOT,
                'target_files': target_files,
                'required_artifacts': required_artifacts,
                'auto_retry_allowed': auto_retry_allowed(role),
                'risk_tags': risk_tags,
                'analysis_version': analysis.get('analysis_version', 2),
                'intake_type': analysis.get('intake_type'),
                'manual_review_required': analysis.get('manual_review_required', False),
                'needs_clarification': analysis.get('needs_clarification', False),
                'clarification_questions': analysis.get('clarification_questions', []),
                'clarification_priority': analysis.get('clarification_priority', 'none'),
                'sub_objectives': analysis.get('sub_objectives', []),
                'objective_hierarchy': analysis.get('objective_hierarchy', []),
                'risk_assessment': analysis.get('risk_assessment', []),
                'acceptance_contract': analysis.get('acceptance_contract', {}),
                'stop_criteria_hints': analysis.get('stop_criteria_hints', []),
                'stop_policy': analysis.get('stop_policy', {}),
                'dependency_plan': analysis.get('dependency_plan', {}),
                'execution_sequence': analysis.get('execution_sequence', []),
                'recent_learning_context': analysis.get('recent_learning_context', {}),
                'recent_learning_guidance': analysis.get('recent_learning_guidance', []),
            },
        }
        return child_task, analysis

    def execute_task(self, task_dir: Path, task: dict[str, Any]) -> None:
        queue = TaskQueue()
        child_task, analysis = self._build_child_task(task_dir, task)
        queue.create_task(child_task)

        dependency_plan = analysis.get('dependency_plan', {})
        execution_brief = self._build_execution_brief(task_dir, task, analysis, child_task)
        plan_lines = [
            f"parent_task={task_dir.name}",
            f"child_task={child_task['task_id']}",
            f"child_role={child_task['role']}",
            f"objective={child_task['objective']}",
            f"objective_summary={analysis.get('objective_summary')}",
            f"mode={child_task['metadata']['opencode_mode']}",
            f"engine={child_task['engine']}",
            f"intake_type={analysis.get('intake_type')}",
            f"manual_review_required={analysis.get('manual_review_required')}",
            f"needs_clarification={analysis.get('needs_clarification')}",
            f"clarification_priority={analysis.get('clarification_priority')}",
            'sub_objectives=',
            *[f"- {item}" for item in analysis.get('sub_objectives', [])],
            'objective_hierarchy=',
            *[f"- level={item.get('level')} | objective={item.get('objective')} | success_signal={item.get('success_signal')}" for item in analysis.get('objective_hierarchy', [])],
            'risk_tags=',
            *[f"- {item}" for item in child_task['metadata'].get('risk_tags', [])],
            'risk_assessment=',
            *[f"- {item.get('tag')} | priority={item.get('priority')} | rationale={item.get('rationale')}" for item in analysis.get('risk_assessment', [])],
            'target_files=',
            *[f"- {item}" for item in child_task['metadata'].get('target_files', [])],
            'constraints=',
            *[f"- {item}" for item in child_task['constraints']],
            'acceptance_criteria=',
            *[f"- {item}" for item in child_task['acceptance_criteria']],
            'acceptance_contract.required_outcomes=',
            *[f"- {item}" for item in analysis.get('acceptance_contract', {}).get('required_outcomes', [])],
            f"acceptance_contract.validation_focus={analysis.get('acceptance_contract', {}).get('validation_focus')}",
            'stop_criteria_hints=',
            *[f"- {item}" for item in analysis.get('stop_criteria_hints', [])],
            'stop_policy.stop_when=',
            *[f"- {item}" for item in analysis.get('stop_policy', {}).get('stop_when', [])],
            'stop_policy.continue_when=',
            *[f"- {item}" for item in analysis.get('stop_policy', {}).get('continue_when', [])],
            'stop_policy.escalate_when=',
            *[f"- {item}" for item in analysis.get('stop_policy', {}).get('escalate_when', [])],
            'clarification_questions=',
            *[f"- {item}" for item in analysis.get('clarification_questions', [])],
            'dependency_plan.serial=',
            *[f"- {item}" for item in dependency_plan.get('serial', [])],
            'execution_sequence=',
            *[f"- {item}" for item in analysis.get('execution_sequence', [])],
            'dependency_plan.parallel_groups=',
            *[f"- {group}" for group in dependency_plan.get('parallel_groups', [])],
            'dependency_plan.review_checkpoints=',
            *[f"- {item}" for item in dependency_plan.get('review_checkpoints', [])],
        ]
        plan_path = self.write_artifact(task_dir, 'master_plan.md', '\n'.join(plan_lines) + '\n')
        analysis_path = self.write_artifact(task_dir, 'demand_analysis.json', analysis, as_json=True)
        intake_analysis_path = self.write_artifact(task_dir, 'intake_analysis.json', analysis, as_json=True)
        dependency_path = self.write_artifact(task_dir, 'dependency_plan.json', dependency_plan, as_json=True)
        execution_brief_path = self.write_artifact(task_dir, 'execution_brief.json', execution_brief, as_json=True)
        execution_brief_md_path = self.write_artifact(task_dir, 'execution_brief.md', self._build_execution_brief_markdown(execution_brief))
        child_path = self.write_artifact(task_dir, 'generated_child_task.json', child_task, as_json=True)
        artifacts = [
            str(plan_path.relative_to(task_dir)),
            str(analysis_path.relative_to(task_dir)),
            str(intake_analysis_path.relative_to(task_dir)),
            str(dependency_path.relative_to(task_dir)),
            str(execution_brief_path.relative_to(task_dir)),
            str(execution_brief_md_path.relative_to(task_dir)),
            str(child_path.relative_to(task_dir)),
        ]
        self.handoff_task(task_dir, child_task['role'], artifacts, f"已生成 {child_task['role']} 子任务 {child_task['task_id']}")
        self.complete_task(
            task_dir,
            True,
            generated_task=child_task['task_id'],
            generated_role=child_task['role'],
            generated_mode=child_task['metadata']['opencode_mode'],
            manual_review_required=analysis.get('manual_review_required', False),
            needs_clarification=analysis.get('needs_clarification', False),
        )


if __name__ == '__main__':
    worker = MasterQuantWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
