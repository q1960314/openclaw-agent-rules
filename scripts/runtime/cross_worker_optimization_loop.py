#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path('/home/admin/.openclaw/workspace/master')
RUNTIME = ROOT / 'scripts' / 'runtime'
WORKERS = ROOT / 'scripts' / 'workers'
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
if str(WORKERS) not in sys.path:
    sys.path.insert(0, str(WORKERS))

from task_queue import TaskQueue  # noqa: E402
from main_worker import create_intake_task  # noqa: E402
from stop_criteria import evaluate_backtest_task  # noqa: E402
from decision_engine import adaptive_next_step, stop_decision  # noqa: E402

ROLE_SCRIPT = {
    'strategy-expert': WORKERS / 'strategy_expert_worker.py',
    'parameter-evolver': WORKERS / 'parameter_evolver_worker.py',
    'factor-miner': WORKERS / 'factor_miner_worker.py',
    'backtest-engine': WORKERS / 'backtest_engine_worker.py',
    'test-expert': WORKERS / 'test_expert_worker.py',
    'doc-manager': WORKERS / 'doc_manager_worker.py',
    'knowledge-steward': WORKERS / 'knowledge_steward_worker.py',
}

ROLE_ARTIFACTS = {
    'strategy-expert': ['strategy_plan.md', 'strategy_candidate.json', 'result_summary.md', 'opencode_result.json'],
    'parameter-evolver': ['parameter_plan.md', 'parameter_candidate.json', 'result_summary.md', 'opencode_result.json'],
    'factor-miner': ['factor_plan.md', 'factor_candidate.json', 'result_summary.md', 'opencode_result.json'],
    'backtest-engine': ['backtest_metrics.json', 'backtest_report.md', 'result_summary.md'],
}

ROLE_TASK_TYPE = {
    'strategy-expert': 'xloop_strategy',
    'parameter-evolver': 'xloop_param',
    'factor-miner': 'xloop_factor',
    'backtest-engine': 'xloop_backtest',
}

ROLE_ENGINE = {
    'strategy-expert': 'opencode',
    'parameter-evolver': 'opencode',
    'factor-miner': 'opencode',
    'backtest-engine': 'native',
}

RECENT_LEARNING_STATE = ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_recent_ecosystem_learning.json'

CANDIDATE_ARTIFACT = {
    'strategy-expert': 'strategy_candidate.json',
    'parameter-evolver': 'parameter_candidate.json',
    'factor-miner': 'factor_candidate.json',
}


class CrossWorkerOptimizationLoop:
    def __init__(self, objective: str, priority: str = 'high', max_adjust_rounds: int = 2, stop_criteria: dict[str, Any] | None = None):
        self.objective = objective
        self.priority = priority
        self.max_adjust_rounds = max_adjust_rounds
        self.stop_criteria = stop_criteria or {'mode': 'backtest_thresholds'}
        self.loops_root = ROOT / 'traces' / 'loops'
        self.loops_root.mkdir(parents=True, exist_ok=True)
        self.loop_id = f"XLOOP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.loop_dir = self.loops_root / self.loop_id
        self.loop_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.loop_dir / 'loop_events.jsonl'
        self.report_path = self.loop_dir / 'loop_report.json'
        self.queue = TaskQueue(ROOT / 'traces' / 'jobs')
        self.stage_results: list[dict[str, Any]] = []
        self.adaptive_trace: list[dict[str, Any]] = []

    def _append_event(self, event_type: str, **payload: Any) -> None:
        item = {
            'ts': datetime.now().astimezone().isoformat(),
            'loop_id': self.loop_id,
            'event_type': event_type,
            **payload,
        }
        with self.events_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + '\n')

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        txt = path.read_text(encoding='utf-8').strip()
        return json.loads(txt) if txt else {}

    def _run_worker(self, role: str, task_id: str) -> int:
        script = ROLE_SCRIPT[role]
        proc = subprocess.run(['python3', str(script), task_id], cwd=str(ROOT), capture_output=True, text=True)
        self._append_event('worker_run', role=role, task_id=task_id, returncode=proc.returncode, stdout=proc.stdout[-1000:], stderr=proc.stderr[-1000:])
        return proc.returncode

    def _task_dir(self, task_id: str) -> Path:
        return self.queue.task_dir(task_id)

    def _review(self, task_id: str) -> dict[str, Any]:
        return self._load_json(self._task_dir(task_id) / 'review.json')

    def _status(self, task_id: str) -> dict[str, Any]:
        return self._load_json(self._task_dir(task_id) / 'status.json')

    def _load_research_hints(self, task_id: str) -> dict[str, Any]:
        task = self.queue.load_task(task_id) or {}
        role = task.get('role')
        candidate_name = CANDIDATE_ARTIFACT.get(role)
        if not candidate_name:
            return {}
        candidate = self._load_json(self._task_dir(task_id) / 'artifacts' / candidate_name)
        if not candidate:
            return {}
        keys_by_role = {
            'strategy-expert': ['code_touchpoints', 'change_priority', 'factor_handoff', 'parameter_handoff', 'backtest_handoff', 'validation_priority'],
            'parameter-evolver': ['code_touchpoints', 'change_priority', 'backtest_handoff', 'metric_guardrails', 'validation_plan'],
            'factor-miner': ['code_touchpoints', 'strategy_handoff', 'parameter_handoff', 'validation_priority', 'applicability_conditions'],
        }
        hints = {'source_role': role, 'task_id': task_id}
        for key in keys_by_role.get(role, []):
            value = candidate.get(key)
            if value:
                hints[key] = value
        return hints

    def _summarize_research_hints(self, research_hints: dict[str, Any]) -> dict[str, Any]:
        if not research_hints:
            return {}
        summary: dict[str, Any] = {
            'source_role': research_hints.get('source_role'),
            'source_task_id': research_hints.get('task_id'),
            'hint_keys': sorted([key for key in research_hints.keys() if key not in {'source_role', 'task_id'}]),
            'hint_preview': {},
        }
        for key, value in research_hints.items():
            if key in {'source_role', 'task_id'}:
                continue
            if isinstance(value, list):
                summary['hint_preview'][key] = value[:2]
            else:
                summary['hint_preview'][key] = value
        return summary

    def _load_recent_learning_hints(self) -> dict[str, Any]:
        payload = self._load_json(RECENT_LEARNING_STATE)
        if not payload:
            return {}
        hints: dict[str, Any] = {
            'source_role': 'recent-ecosystem-learning',
            'task_id': 'latest_recent_ecosystem_learning',
        }
        dominant_expert_role = payload.get('dominant_expert_role')
        adaptive_dominant_next_role = (payload.get('adaptive_loop_bridge', {}) or {}).get('dominant_next_role')
        if dominant_expert_role:
            hints['dominant_expert_role'] = dominant_expert_role
        if adaptive_dominant_next_role:
            hints['adaptive_dominant_next_role'] = adaptive_dominant_next_role
        aggregated: dict[str, list[str]] = {}
        for item in payload.get('recent_examples', []) or []:
            for key, values in (item.get('signal_preview', {}) or {}).items():
                if not isinstance(values, list):
                    continue
                bucket = aggregated.setdefault(key, [])
                for value in values:
                    cleaned = str(value).strip()
                    if cleaned and cleaned not in bucket:
                        bucket.append(cleaned)
        for key, values in aggregated.items():
            if values:
                hints[key] = values[:2]
        return hints

    def _merge_hint_sources(self, research_hints: dict[str, Any], recent_learning_hints: dict[str, Any]) -> dict[str, Any]:
        if not research_hints:
            return dict(recent_learning_hints)
        if not recent_learning_hints:
            return dict(research_hints)
        merged = dict(research_hints)
        merged['secondary_sources'] = [recent_learning_hints.get('source_role')]
        for key, value in recent_learning_hints.items():
            if key in {'source_role', 'task_id'}:
                continue
            if key not in merged or not merged.get(key):
                merged[key] = value
        return merged

    def _explain_adaptive_decision(self, *, next_role: str, decision_basis: str | None, handoff_source_role: str | None, handoff_hints_used: list[str], recent_learning_hint_summary: dict[str, Any]) -> str:
        parts = [f'本轮下一环选择 {next_role}']
        if decision_basis:
            parts.append(f'决策依据={decision_basis}')
        if handoff_source_role:
            parts.append(f'主要提示来源={handoff_source_role}')
        if handoff_hints_used:
            parts.append('本轮实际采用提示=' + '；'.join(handoff_hints_used[:2]))
        hint_preview = (recent_learning_hint_summary or {}).get('hint_preview', {}) or {}
        if hint_preview:
            preview_items = []
            for key, values in hint_preview.items():
                if isinstance(values, list) and values:
                    preview_items.append(f'{key}:{values[0]}')
                elif values:
                    preview_items.append(f'{key}:{values}')
                if len(preview_items) >= 2:
                    break
            if preview_items:
                parts.append('近期经验参考=' + '；'.join(preview_items))
        return ' | '.join(parts)

    def _create_task(self, task_id: str, role: str, objective: str, input_artifacts: list[str], auto_retry_allowed: bool = False, metadata_extra: dict[str, Any] | None = None) -> Path:
        metadata = {
            'task_type': ROLE_TASK_TYPE[role],
            'worker_role': role,
            'source_role': 'cross-worker-optimization-loop',
            'required_artifacts': ROLE_ARTIFACTS[role],
            'auto_retry_allowed': auto_retry_allowed,
        }
        if metadata_extra:
            metadata.update(metadata_extra)
        task = {
            'task_id': task_id,
            'role': role,
            'objective': objective,
            'constraints': ['按 cross-worker optimization loop 执行'],
            'acceptance_criteria': [f'生成 {x}' for x in ROLE_ARTIFACTS[role]],
            'input_artifacts': input_artifacts,
            'upstream': self.loop_id,
            'downstream': 'test-expert',
            'engine': ROLE_ENGINE[role],
            'priority': self.priority,
            'metadata': metadata,
        }
        return self.queue.create_task(task)

    def _run_stage(self, role: str, task_id: str) -> dict[str, Any]:
        self._append_event('stage_started', role=role, task_id=task_id)
        self._run_worker(role, task_id)
        self._run_worker('test-expert', task_id)
        review = self._review(task_id)
        task = self.queue.load_task(task_id) or {}
        metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
        result = {
            'task_id': task_id,
            'role': role,
            'status': self._status(task_id).get('status'),
            'review_decision': review.get('decision'),
            'issues': review.get('issues', []),
            'adaptive_context': {
                'decision_basis': metadata.get('xloop_decision_basis'),
                'handoff_source_role': metadata.get('xloop_handoff_source_role'),
                'handoff_hints_used': metadata.get('xloop_handoff_hints_used', []),
                'research_hint_summary': metadata.get('xloop_research_hint_summary', {}),
            },
        }
        self.stage_results.append(result)
        self._append_event('stage_reviewed', **result)
        return result

    def _maybe_retry_stage(self, role: str, task_id: str) -> dict[str, Any]:
        result = self._run_stage(role, task_id)
        if result.get('review_decision') == 'passed':
            return result
        task = self._load_json(self._task_dir(task_id) / 'task.json')
        if not bool(task.get('metadata', {}).get('auto_retry_allowed', False)):
            return result
        retry_dir = self.queue.create_retry_task(task_id, requested_by='cross-worker-optimization-loop', reason='stage retry after rejection')
        retry_id = retry_dir.name
        self._append_event('stage_retry_created', source_task_id=task_id, retry_task_id=retry_id, role=role)
        retry_result = self._run_stage(role, retry_id)
        retry_result['retry_of'] = task_id
        return retry_result

    def _evaluate_stop(self, backtest_task_id: str, adjust_round: int) -> dict[str, Any]:
        stop_eval = evaluate_backtest_task(self._task_dir(backtest_task_id), self.stop_criteria)
        self._append_event('stop_criteria_evaluated', adjust_round=adjust_round, task_id=backtest_task_id, passed=stop_eval['passed'], checks=stop_eval['checks'])
        self.stage_results.append({
            'task_id': backtest_task_id,
            'role': 'stop-criteria',
            'status': 'evaluated',
            'review_decision': 'passed' if stop_eval['passed'] else 'threshold_not_met',
            'issues': [c['name'] for c in stop_eval['checks'] if not c['passed']],
            'stop_criteria': stop_eval,
        })
        return stop_eval

    def run(self) -> Path:
        intake_dir = create_intake_task(self.objective, priority=self.priority)
        intake_id = intake_dir.name
        self._append_event('loop_started', intake_task_id=intake_id, objective=self.objective, stop_criteria=self.stop_criteria, max_adjust_rounds=self.max_adjust_rounds)

        strategy_dir = self._create_task(
            task_id=f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-XSTRATEGY0",
            role='strategy-expert',
            objective=f"Analyze strategy optimization direction: {self.objective}",
            input_artifacts=[str(intake_dir / 'task.json')],
        )
        sres = self._run_stage('strategy-expert', strategy_dir.name)
        if sres.get('review_decision') == 'manual_review_required':
            final_status = 'manual_review_required'
            final_task_id = sres['task_id']
        elif sres.get('review_decision') != 'passed':
            final_status = 'blocked_on_strategy'
            final_task_id = sres['task_id']
        else:
            baseline_dir = self._create_task(
                task_id=f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-XBACKTEST0",
                role='backtest-engine',
                objective='Run smoke backtest for 打板策略 over 20 days as baseline after strategy review',
                input_artifacts=[str(self._task_dir(sres['task_id']) / 'artifacts' / 'strategy_plan.md')],
                auto_retry_allowed=True,
            )
            bres = self._maybe_retry_stage('backtest-engine', baseline_dir.name)
            if bres.get('review_decision') == 'manual_review_required':
                final_status = 'manual_review_required'
                final_task_id = bres['task_id']
            elif bres.get('review_decision') != 'passed':
                final_status = 'blocked_on_backtest0'
                final_task_id = bres['task_id']
            else:
                final_status = 'threshold_not_met'
                final_task_id = bres['task_id']
                current_backtest_task = bres['task_id']
                last_research_task = sres['task_id']

                for adjust_round in range(1, self.max_adjust_rounds + 1):
                    stop_eval = self._evaluate_stop(current_backtest_task, adjust_round)
                    research_hints = self._load_research_hints(last_research_task)
                    recent_learning_hints = self._load_recent_learning_hints()
                    combined_hints = self._merge_hint_sources(research_hints, recent_learning_hints)
                    decision = stop_decision(stop_eval, adjust_round, self.max_adjust_rounds, research_hints=combined_hints)
                    self._append_event(
                        'stop_decision',
                        adjust_round=adjust_round,
                        decision=decision,
                        research_hints=research_hints,
                        recent_learning_hints=recent_learning_hints,
                        combined_hints=combined_hints,
                    )
                    if decision['action'] == 'stop_passed':
                        self._run_worker('doc-manager', current_backtest_task)
                        self._run_worker('knowledge-steward', current_backtest_task)
                        final_status = 'passed'
                        break
                    if decision['action'] == 'stop_threshold_not_met':
                        final_status = 'threshold_not_met'
                        break

                    next_role = decision['next_role']
                    next_objective = decision['objective']
                    hint_summary = self._summarize_research_hints(combined_hints)
                    recent_learning_hint_summary = self._summarize_research_hints(recent_learning_hints)
                    decision_summary = self._explain_adaptive_decision(
                        next_role=next_role,
                        decision_basis=decision.get('decision_basis'),
                        handoff_source_role=decision.get('handoff_source_role'),
                        handoff_hints_used=decision.get('handoff_hints_used', []),
                        recent_learning_hint_summary=recent_learning_hint_summary,
                    )
                    adaptive_trace_item = {
                        'adjust_round': adjust_round,
                        'next_role': next_role,
                        'next_objective': next_objective,
                        'decision_basis': decision.get('decision_basis'),
                        'failed_checks': [c['name'] for c in stop_eval['checks'] if not c['passed']],
                        'handoff_source_role': decision.get('handoff_source_role'),
                        'handoff_hints_used': decision.get('handoff_hints_used', []),
                        'research_hint_summary': hint_summary,
                        'recent_learning_hint_summary': recent_learning_hint_summary,
                        'decision_summary': decision_summary,
                    }
                    self.adaptive_trace.append(adaptive_trace_item)
                    self.stage_results.append({
                        'task_id': f'{self.loop_id}-ADAPTIVE-{adjust_round}',
                        'role': 'adaptive-decision',
                        'status': 'planned',
                        'review_decision': 'planned',
                        'issues': [],
                        **adaptive_trace_item,
                    })
                    self._append_event('adaptive_decision', **adaptive_trace_item)
                    improve_dir = self._create_task(
                        task_id=f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-X{next_role.upper().replace('-', '')}{adjust_round}",
                        role=next_role,
                        objective=next_objective,
                        input_artifacts=[
                            str(self._task_dir(last_research_task) / 'artifacts'),
                            str(self._task_dir(current_backtest_task) / 'artifacts' / 'backtest_report.md'),
                        ],
                        metadata_extra={
                            'xloop_adjust_round': adjust_round,
                            'xloop_decision_basis': decision.get('decision_basis'),
                            'xloop_handoff_source_role': decision.get('handoff_source_role'),
                            'xloop_handoff_hints_used': decision.get('handoff_hints_used', []),
                            'xloop_research_hint_summary': hint_summary,
                            'xloop_recent_learning_hint_summary': recent_learning_hint_summary,
                            'xloop_decision_summary': decision_summary,
                        },
                    )
                    ires = self._run_stage(next_role, improve_dir.name)
                    if ires.get('review_decision') == 'manual_review_required':
                        final_status = 'manual_review_required'
                        final_task_id = ires['task_id']
                        break
                    if ires.get('review_decision') != 'passed':
                        final_status = f'blocked_on_{next_role}'
                        final_task_id = ires['task_id']
                        break
                    last_research_task = ires['task_id']

                    new_backtest_dir = self._create_task(
                        task_id=f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-XBACKTEST{adjust_round}",
                        role='backtest-engine',
                        objective=f'Run smoke backtest for 打板策略 over 20 days after adaptive optimization round {adjust_round}',
                        input_artifacts=[str(self._task_dir(ires['task_id']) / 'artifacts')],
                        auto_retry_allowed=True,
                    )
                    bres = self._maybe_retry_stage('backtest-engine', new_backtest_dir.name)
                    current_backtest_task = bres['task_id']
                    final_task_id = current_backtest_task
                    if bres.get('review_decision') == 'manual_review_required':
                        final_status = 'manual_review_required'
                        break
                    if bres.get('review_decision') != 'passed':
                        final_status = f'blocked_on_backtest{adjust_round}'
                        break
                else:
                    final_status = 'threshold_not_met'

        report = {
            'loop_id': self.loop_id,
            'objective': self.objective,
            'adaptive': True,
            'max_adjust_rounds': self.max_adjust_rounds,
            'stop_criteria': self.stop_criteria,
            'intake_task_id': intake_id,
            'final_status': final_status,
            'final_task_id': final_task_id,
            'final_task_status': self._status(final_task_id).get('status') if final_task_id else None,
            'final_review': self._review(final_task_id) if final_task_id else {},
            'adaptive_trace': self.adaptive_trace,
            'adaptive_summary_note': self.adaptive_trace[-1].get('decision_summary') if self.adaptive_trace else None,
            'stage_results': self.stage_results,
            'generated_at': datetime.now().astimezone().isoformat(),
        }
        self.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self._append_event('loop_completed', final_status=final_status, final_task_id=final_task_id)
        return self.loop_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--objective', required=True)
    parser.add_argument('--priority', default='high')
    parser.add_argument('--max-adjust-rounds', type=int, default=2)
    parser.add_argument('--min-total-return', type=float)
    parser.add_argument('--min-sharpe-ratio', type=float)
    parser.add_argument('--max-drawdown', type=float)
    parser.add_argument('--min-total-trades', type=int)
    args = parser.parse_args()
    stop_criteria = {'mode': 'backtest_thresholds'}
    for key in ('min_total_return', 'min_sharpe_ratio', 'max_drawdown', 'min_total_trades'):
        value = getattr(args, key)
        if value is not None:
            stop_criteria[key] = value
    loop = CrossWorkerOptimizationLoop(args.objective, priority=args.priority, max_adjust_rounds=args.max_adjust_rounds, stop_criteria=stop_criteria)
    loop_dir = loop.run()
    print(loop_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
