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
from decision_engine import retry_policy  # noqa: E402

ROLE_SCRIPT = {
    'master-quant': WORKERS / 'master_quant_worker.py',
    'coder': WORKERS / 'coder_worker.py',
    'strategy-expert': WORKERS / 'strategy_expert_worker.py',
    'parameter-evolver': WORKERS / 'parameter_evolver_worker.py',
    'backtest-engine': WORKERS / 'backtest_engine_worker.py',
    'data-collector': WORKERS / 'data_collector_worker.py',
    'factor-miner': WORKERS / 'factor_miner_worker.py',
    'sentiment-analyst': WORKERS / 'sentiment_analyst_worker.py',
    'finance-learner': WORKERS / 'finance_learner_worker.py',
    'ops-monitor': WORKERS / 'ops_monitor_worker.py',
    'test-expert': WORKERS / 'test_expert_worker.py',
    'doc-manager': WORKERS / 'doc_manager_worker.py',
    'knowledge-steward': WORKERS / 'knowledge_steward_worker.py',
}


class ContinuousOptimizationLoop:
    def __init__(self, objective: str, max_rounds: int = 3, priority: str = 'high', force_reject_once: bool = False):
        self.objective = objective
        self.max_rounds = max_rounds
        self.priority = priority
        self.force_reject_once = force_reject_once
        self.loops_root = ROOT / 'traces' / 'loops'
        self.loops_root.mkdir(parents=True, exist_ok=True)
        self.loop_id = f"LOOP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.loop_dir = self.loops_root / self.loop_id
        self.loop_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.loop_dir / 'loop_events.jsonl'
        self.report_path = self.loop_dir / 'loop_report.json'
        self.queue = TaskQueue(ROOT / 'traces' / 'jobs')
        self.rounds: list[dict[str, Any]] = []

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

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def _run_worker(self, role: str, task_id: str) -> int:
        script = ROLE_SCRIPT[role]
        proc = subprocess.run(['python3', str(script), task_id], cwd=str(ROOT), capture_output=True, text=True)
        self._append_event('worker_run', role=role, task_id=task_id, returncode=proc.returncode, stdout=proc.stdout[-1000:], stderr=proc.stderr[-1000:])
        return proc.returncode

    def _child_task_id_from_parent(self, parent_task_id: str) -> str:
        child_json = ROOT / 'traces' / 'jobs' / parent_task_id / 'artifacts' / 'generated_child_task.json'
        data = self._load_json(child_json)
        return data['task_id']

    def _task_dir(self, task_id: str) -> Path:
        return ROOT / 'traces' / 'jobs' / task_id

    def _task_json(self, task_id: str) -> dict[str, Any]:
        return self._load_json(self._task_dir(task_id) / 'task.json')

    def _review(self, task_id: str) -> dict[str, Any]:
        return self._load_json(self._task_dir(task_id) / 'review.json')

    def _status(self, task_id: str) -> dict[str, Any]:
        return self._load_json(self._task_dir(task_id) / 'status.json')

    def _mark_force_reject_once(self, task_id: str) -> None:
        task_path = self._task_dir(task_id) / 'task.json'
        payload = self._load_json(task_path)
        metadata = payload.get('metadata', {}) if isinstance(payload.get('metadata', {}), dict) else {}
        metadata['force_reject_once'] = True
        payload['metadata'] = metadata
        self._write_json(task_path, payload)
        self._append_event('force_reject_enabled', task_id=task_id)

    def _maybe_retry(self, task_id: str, role: str, review: dict[str, Any], round_no: int) -> str | None:
        task = self._task_json(task_id)
        metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
        decision = retry_policy(role, metadata, review, round_no)
        self._append_event('retry_policy_evaluated', task_id=task_id, role=role, decision=decision)
        if not decision.get('allow_retry'):
            return None
        retry_dir = self.queue.create_retry_task(task_id, requested_by='continuous-optimization-loop', reason=decision['requested_reason'])
        self._append_event('retry_created', source_task_id=task_id, retry_task_id=retry_dir.name, reason=decision['requested_reason'])
        return retry_dir.name

    def run(self) -> Path:
        intake_dir = create_intake_task(self.objective, priority=self.priority)
        intake_id = intake_dir.name
        self._append_event('loop_started', intake_task_id=intake_id, objective=self.objective, max_rounds=self.max_rounds, force_reject_once=self.force_reject_once)

        current_task_id: str | None = None
        current_role: str | None = None
        final_status = 'max_rounds_reached'

        for round_no in range(1, self.max_rounds + 1):
            self._append_event('round_started', round=round_no, current_task_id=current_task_id, current_role=current_role)
            round_info: dict[str, Any] = {'round': round_no}

            if round_no == 1:
                self._run_worker('master-quant', intake_id)
                current_task_id = self._child_task_id_from_parent(intake_id)
                current_role = self._task_json(current_task_id)['role']
                self._append_event('child_generated', round=round_no, task_id=current_task_id, role=current_role)
                if self.force_reject_once:
                    self._mark_force_reject_once(current_task_id)

            assert current_task_id and current_role
            round_info['task_id'] = current_task_id
            round_info['role'] = current_role

            self._run_worker(current_role, current_task_id)
            self._run_worker('test-expert', current_task_id)
            review = self._review(current_task_id)
            decision = review.get('decision')
            round_info['review_decision'] = decision
            round_info['issues'] = review.get('issues', [])
            self._append_event('review_decision', round=round_no, task_id=current_task_id, role=current_role, decision=decision, issues=review.get('issues', []))

            if decision == 'passed':
                self._run_worker('doc-manager', current_task_id)
                self._run_worker('knowledge-steward', current_task_id)
                final_status = 'passed'
                round_info['outcome'] = 'passed'
                self.rounds.append(round_info)
                break

            if decision == 'manual_review_required':
                final_status = 'manual_review_required'
                round_info['outcome'] = 'manual_review_required'
                self.rounds.append(round_info)
                break

            retry_task_id = self._maybe_retry(current_task_id, current_role, review, round_no)
            if retry_task_id:
                round_info['outcome'] = 'retry_created'
                round_info['retry_task_id'] = retry_task_id
                self.rounds.append(round_info)
                current_task_id = retry_task_id
                current_role = self._task_json(current_task_id)['role']
                if round_no == self.max_rounds:
                    final_status = 'retry_exhausted'
                continue

            round_info['outcome'] = 'blocked'
            self.rounds.append(round_info)
            final_status = 'blocked'
            break
        else:
            if final_status == 'max_rounds_reached' and self.rounds:
                last = self.rounds[-1]
                if last.get('outcome') == 'retry_created':
                    final_status = 'retry_exhausted'

        report = {
            'loop_id': self.loop_id,
            'objective': self.objective,
            'max_rounds': self.max_rounds,
            'force_reject_once': self.force_reject_once,
            'final_status': final_status,
            'intake_task_id': intake_id,
            'final_task_id': current_task_id,
            'final_task_status': self._status(current_task_id).get('status') if current_task_id else None,
            'final_review': self._review(current_task_id) if current_task_id else {},
            'rounds': self.rounds,
            'generated_at': datetime.now().astimezone().isoformat(),
        }
        self.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self._append_event('loop_completed', final_status=final_status, final_task_id=current_task_id)
        return self.loop_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--objective', required=True)
    parser.add_argument('--max-rounds', type=int, default=3)
    parser.add_argument('--priority', default='high')
    parser.add_argument('--force-reject-once', action='store_true')
    args = parser.parse_args()
    loop = ContinuousOptimizationLoop(args.objective, max_rounds=args.max_rounds, priority=args.priority, force_reject_once=args.force_reject_once)
    loop_dir = loop.run()
    print(loop_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
