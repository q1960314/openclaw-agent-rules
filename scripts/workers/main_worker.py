#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from task_queue import TaskQueue  # noqa: E402
from decision_engine import analyze_request  # noqa: E402


def create_intake_task(objective: str, priority: str = 'high') -> Path:
    queue = TaskQueue()
    now = datetime.now().astimezone()
    analysis = analyze_request(objective)
    task_id = f"TASK-{now.strftime('%Y%m%d-%H%M%S')}-INTAKE"
    task_dir = queue.create_task({
        'task_id': task_id,
        'role': 'master-quant',
        'objective': objective,
        'constraints': ['按 P1 最小闭环执行', '禁止伪完成', '必须生成结构化下游任务'],
        'acceptance_criteria': ['生成下游专项子任务', '状态流转可追踪', '事件审计完整'],
        'input_artifacts': [],
        'upstream': 'main',
        'downstream': 'master-quant',
        'engine': 'native',
        'priority': priority,
        'metadata': {
            'task_type': 'intake',
            'intake_schema_version': analysis.get('analysis_version', 2),
            'source_role': 'main',
            'requested_at': now.isoformat(),
            'raw_user_objective': objective,
            'intake_type': analysis.get('intake_type'),
            'suggested_role': analysis.get('suggested_role'),
            'execution_mode': analysis.get('execution_mode'),
            'manual_review_required': analysis.get('manual_review_required', False),
            'needs_clarification': analysis.get('needs_clarification', False),
            'clarification_priority': analysis.get('clarification_priority', 'none'),
            'risk_tags': analysis.get('risk_tags', []),
            'risk_assessment': analysis.get('risk_assessment', []),
            'execution_sequence': analysis.get('execution_sequence', []),
            'objective_hierarchy': analysis.get('objective_hierarchy', []),
            'acceptance_contract': analysis.get('acceptance_contract', {}),
            'stop_policy': analysis.get('stop_policy', {}),
            'recent_learning_context': analysis.get('recent_learning_context', {}),
            'recent_learning_guidance': analysis.get('recent_learning_guidance', []),
        },
    })
    manifest = {
        'task_id': task_id,
        'source_role': 'main',
        'priority': priority,
        'objective': objective,
        'created_at': now.isoformat(),
        'intake_schema_version': analysis.get('analysis_version', 2),
        'analysis': analysis,
    }
    (task_dir / 'artifacts').mkdir(exist_ok=True)
    (task_dir / 'artifacts' / 'intake_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (task_dir / 'artifacts' / 'intake_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    (task_dir / 'artifacts' / 'dependency_plan.json').write_text(json.dumps(analysis.get('dependency_plan', {}), ensure_ascii=False, indent=2), encoding='utf-8')
    brief_lines = [
        '# Intake Brief',
        '',
        f"- task_id: {task_id}",
        f"- objective: {objective}",
        f"- suggested_role: {analysis.get('suggested_role')}",
        f"- execution_mode: {analysis.get('execution_mode')}",
        f"- clarification_priority: {analysis.get('clarification_priority')}",
        f"- manual_review_required: {analysis.get('manual_review_required')}",
        '',
        '## Objective Hierarchy',
    ]
    for item in analysis.get('objective_hierarchy', []):
        brief_lines.append(f"- level={item.get('level')} | objective={item.get('objective')} | success_signal={item.get('success_signal')}")
    brief_lines.extend(['', '## Recent Learning Guidance'])
    for item in analysis.get('recent_learning_guidance', []):
        brief_lines.append(f'- {item}')
    (task_dir / 'artifacts' / 'intake_brief.md').write_text('\n'.join(brief_lines) + '\n', encoding='utf-8')
    return task_dir


if __name__ == '__main__':
    objective = ' '.join(sys.argv[1:]).strip() or 'P1 intake task'
    task_dir = create_intake_task(objective)
    print(task_dir)
