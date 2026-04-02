#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / 'runtime'
ADAPTER = BASE / 'adapters' / 'opencode'
for p in (RUNTIME, ADAPTER):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from worker_base import WorkerBase  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402
from opencode_adapter import run_opencode  # noqa: E402
from opencode_fallback_policy import decide_fallback  # noqa: E402
from opencode_result_normalizer import OpenCodeResultNormalizer  # noqa: E402
from opencode_task_builder import build_opencode_request  # noqa: E402
from expert_structuring import build_factor_candidate, make_factor_prompt  # noqa: E402


class FactorMinerWorker(WorkerBase):
    def __init__(self):
        super().__init__('factor-miner')

    def execute_task(self, task_dir: Path, task: dict) -> None:
        self.update_status(task_dir, 'running', 40, 'build_opencode_request')
        request = build_opencode_request(task, task_dir)
        request['mode'] = 'plan'
        request['agent'] = 'plan'
        request['prompt'] = make_factor_prompt(request['prompt'])
        self.update_status(task_dir, 'running', 55, 'run_opencode', opencode_mode=request['mode'])
        result = run_opencode(request)
        normalized_request = result.get('effective_request', request)
        OpenCodeResultNormalizer(str(task_dir)).write(normalized_request, result)
        decision = decide_fallback(result)
        if decision['action'] != 'accept':
            self.fail_task(task_dir, decision['reason'])
            return

        artifacts = ArtifactManager(task_dir)
        plan_text = result.get('text', '').strip() or 'No factor mining plan returned.'
        artifacts.write_text('factor_plan.md', plan_text + '\n')
        candidate = build_factor_candidate(task, plan_text, normalized_request, result)
        artifacts.write_json('factor_candidate.json', candidate)
        artifacts.write_json('factor_analysis.json', {
            'factor_hypotheses': candidate.get('factor_hypotheses', []),
            'economic_rationales': candidate.get('economic_rationales', []),
            'candidate_factors': candidate.get('candidate_factors', []),
            'applicability_conditions': candidate.get('applicability_conditions', []),
            'code_touchpoints': candidate.get('code_touchpoints', []),
            'strategy_handoff': candidate.get('strategy_handoff', []),
            'parameter_handoff': candidate.get('parameter_handoff', []),
            'failure_scenarios': candidate.get('failure_scenarios', []),
            'validation_plan': candidate.get('validation_plan', []),
            'validation_priority': candidate.get('validation_priority', []),
            'overlap_risks': candidate.get('overlap_risks', []),
            'recommendation': candidate.get('recommendation', ''),
            'depth_metrics': candidate.get('depth_metrics', {}),
        })
        artifacts.write_json('factor_depth.json', candidate.get('depth_metrics', {}))
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'factor-miner 结构化专家产物已生成，等待验收')


if __name__ == '__main__':
    worker = FactorMinerWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
