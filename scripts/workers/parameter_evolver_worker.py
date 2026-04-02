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
from expert_structuring import build_parameter_candidate, make_parameter_prompt  # noqa: E402


class ParameterEvolverWorker(WorkerBase):
    def __init__(self):
        super().__init__('parameter-evolver')

    def execute_task(self, task_dir: Path, task: dict) -> None:
        self.update_status(task_dir, 'running', 40, 'build_opencode_request')
        request = build_opencode_request(task, task_dir)
        request['mode'] = 'plan'
        request['agent'] = 'plan'
        request['prompt'] = make_parameter_prompt(request['prompt'])
        self.update_status(task_dir, 'running', 55, 'run_opencode', opencode_mode=request['mode'])
        result = run_opencode(request)
        normalized_request = result.get('effective_request', request)
        OpenCodeResultNormalizer(str(task_dir)).write(normalized_request, result)
        decision = decide_fallback(result)
        if decision['action'] != 'accept':
            self.fail_task(task_dir, decision['reason'])
            return

        artifacts = ArtifactManager(task_dir)
        plan_text = result.get('text', '').strip() or 'No parameter evolution plan returned.'
        artifacts.write_text('parameter_plan.md', plan_text + '\n')
        candidate = build_parameter_candidate(task, plan_text, normalized_request, result)
        artifacts.write_json('parameter_candidate.json', candidate)
        artifacts.write_json('parameter_analysis.json', {
            'parameter_objective': candidate.get('parameter_objective', ''),
            'sensitive_parameters': candidate.get('sensitive_parameters', []),
            'sensitivity_rationales': candidate.get('sensitivity_rationales', []),
            'robust_ranges': candidate.get('robust_ranges', []),
            'fragile_ranges': candidate.get('fragile_ranges', []),
            'range_justification': candidate.get('range_justification', []),
            'tuning_sequence': candidate.get('tuning_sequence', []),
            'boundary_design': candidate.get('boundary_design', []),
            'metric_guardrails': candidate.get('metric_guardrails', []),
            'code_touchpoints': candidate.get('code_touchpoints', []),
            'change_priority': candidate.get('change_priority', []),
            'backtest_handoff': candidate.get('backtest_handoff', []),
            'validation_plan': candidate.get('validation_plan', []),
            'risk_notes': candidate.get('risk_notes', []),
            'depth_metrics': candidate.get('depth_metrics', {}),
        })
        artifacts.write_json('parameter_depth.json', candidate.get('depth_metrics', {}))
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'parameter-evolver 结构化专家产物已生成，等待验收')


if __name__ == '__main__':
    worker = ParameterEvolverWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
