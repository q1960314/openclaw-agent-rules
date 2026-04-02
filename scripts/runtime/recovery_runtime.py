#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recovery runtime for classifying task failures/staleness and proposing next actions.

This layer sits between heartbeat/governance scanning and future scheduler/daemon flows.
It does not execute all actions automatically yet; instead it produces structured recovery
recommendations with explicit recoverability levels.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from decision_engine import governance_action_for_item
from evaluation_runtime import quality_snapshot
from formalization_runtime import load_formalization_snapshot
from release_closure_runtime import load_release_closure_snapshot
from status_manager import StatusManager
from task_queue import TaskQueue


ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'

RECOVERABLE_STATUSES = {'failed', 'rejected'}
NON_RECOVERABLE_STATUSES = {'passed', 'manual_review_required'}


def classify_recovery_level(item: dict[str, Any]) -> dict[str, Any]:
    status = item.get('status')
    reason = str(item.get('reason', '') or '')
    auto_retry_allowed = bool(item.get('auto_retry_allowed', False))

    if status in NON_RECOVERABLE_STATUSES:
        return {
            'recoverability': 'none',
            'recommended_action': 'none',
            'reason': f'status={status} should not be auto-recovered',
        }

    if item.get('stale'):
        gov = governance_action_for_item(item)
        if gov and gov.get('recommended_action') == 'auto_retry':
            return {
                'recoverability': 'auto_retry',
                'recommended_action': 'auto_retry',
                'reason': gov.get('rationale', 'stale task eligible for auto retry'),
            }
        return {
            'recoverability': 'manual_intervention',
            'recommended_action': 'manual_review',
            'reason': gov.get('rationale', 'stale task requires manual review') if gov else 'stale task requires review',
        }

    if status == 'rejected':
        return {
            'recoverability': 'manual_intervention',
            'recommended_action': 'manual_review',
            'reason': 'review rejected; fix issues before retry',
        }

    if status == 'failed':
        if 'stale_task:' in reason and auto_retry_allowed:
            return {
                'recoverability': 'auto_retry',
                'recommended_action': 'auto_retry',
                'reason': 'stale failure with auto-retry enabled',
            }
        if auto_retry_allowed:
            return {
                'recoverability': 'retryable',
                'recommended_action': 'retry_candidate',
                'reason': 'failed task with retry-eligible role',
            }
        return {
            'recoverability': 'manual_intervention',
            'recommended_action': 'manual_review',
            'reason': 'failed task without auto-retry permission',
        }

    return {
        'recoverability': 'unknown',
        'recommended_action': 'manual_review',
        'reason': f'unhandled status={status}',
    }


def task_recovery_snapshot(task_id: str, jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    queue = TaskQueue(jobs_root)
    task = queue.load_task(task_id) or {}
    task_dir = jobs_root / task_id
    status_payload = StatusManager(task_dir).load()
    metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
    item = {
        'task_id': task_id,
        'role': task.get('role'),
        'status': status_payload.get('status'),
        'reason': status_payload.get('blocked_reason') or status_payload.get('review_reason') or '',
        'auto_retry_allowed': bool(metadata.get('auto_retry_allowed', False)),
        'manual_review_required': bool(metadata.get('manual_review_required', False)),
        'retry_of': metadata.get('retry_of'),
        'retry_index': metadata.get('retry_index', 0),
        'updated_at': status_payload.get('updated_at'),
        'stale': False,
    }
    item.update(classify_recovery_level(item))
    item.update(quality_snapshot(task_dir))
    item.update(load_formalization_snapshot(task_dir))
    item.update(load_release_closure_snapshot(task_dir))
    return item


def jobs_recovery_dashboard(jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    queue = TaskQueue(jobs_root)
    items: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for task_dir in sorted(jobs_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith('_'):
            continue
        task = queue.load_task(task_dir.name) or {}
        status_payload = StatusManager(task_dir).load()
        metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
        item = {
            'task_id': task_dir.name,
            'role': task.get('role'),
            'status': status_payload.get('status'),
            'reason': status_payload.get('blocked_reason') or status_payload.get('review_reason') or '',
            'auto_retry_allowed': bool(metadata.get('auto_retry_allowed', False)),
            'manual_review_required': bool(metadata.get('manual_review_required', False)),
            'retry_of': metadata.get('retry_of'),
            'retry_index': metadata.get('retry_index', 0),
            'updated_at': status_payload.get('updated_at'),
            'stale': False,
        }
        item.update(classify_recovery_level(item))
        item.update(quality_snapshot(task_dir))
        item.update(load_formalization_snapshot(task_dir))
        item.update(load_release_closure_snapshot(task_dir))
        counts[item['recoverability']] = counts.get(item['recoverability'], 0) + 1
        items.append(item)

    quality_grade_counts: dict[str, int] = {}
    formalization_state_counts: dict[str, int] = {}
    human_approval_state_counts: dict[str, int] = {}
    approval_recompute_state_counts: dict[str, int] = {}
    release_execution_state_counts: dict[str, int] = {}
    official_release_pipeline_state_counts: dict[str, int] = {}
    closure_counts = {'approval_required': 0, 'approved': 0, 'approval_checklist_ready': 0, 'approval_decision_recorded': 0, 'approval_transition_visible': 0, 'human_approval_input_slot_visible': 0, 'human_approval_input_slot_ready': 0, 'human_approval_input_recorded': 0, 'human_approval_result_recorded': 0, 'human_approval_result_visible': 0, 'approval_recompute_visible': 0, 'release_action_allowed': 0, 'release_preflight_ready': 0, 'pre_release_ready': 0, 'closure_consistency_ready': 0, 'official_release_rehearsal_ready': 0, 'release_execution_blocked': 0, 'post_approval_transition_visible': 0, 'post_approval_execution_unblocked': 0, 'official_release_state_visible': 0, 'official_release_pipeline_visible': 0, 'official_release_pipeline_executable': 0, 'release_artifact_binding_visible': 0, 'release_artifact_binding_ready': 0, 'rollback_supported': 0, 'executor_contract_available': 0, 'dry_run_available': 0, 'execution_receipt_protocol_available': 0, 'handoff_packet_available': 0, 'operator_execution_request_available': 0, 'receipt_correlation_ready': 0, 'release_execution_requested': 0, 'rollback_execution_requested': 0, 'release_execution_receipt_recorded': 0, 'rollback_execution_receipt_recorded': 0, 'closure_visible': 0}
    scored_items = [item.get('quality_score') for item in items if isinstance(item.get('quality_score'), int)]
    for item in items:
        grade = item.get('quality_grade')
        if grade:
            quality_grade_counts[grade] = quality_grade_counts.get(grade, 0) + 1
        fstate = item.get('formalization_state')
        if fstate:
            formalization_state_counts[fstate] = formalization_state_counts.get(fstate, 0) + 1
        human_state = item.get('human_approval_state')
        if human_state:
            human_approval_state_counts[human_state] = human_approval_state_counts.get(human_state, 0) + 1
        recompute_state = item.get('approval_recompute_state')
        if recompute_state:
            approval_recompute_state_counts[recompute_state] = approval_recompute_state_counts.get(recompute_state, 0) + 1
        execution_state = item.get('release_execution_state')
        if execution_state:
            release_execution_state_counts[execution_state] = release_execution_state_counts.get(execution_state, 0) + 1
        pipeline_state = item.get('official_release_pipeline_state')
        if pipeline_state:
            official_release_pipeline_state_counts[pipeline_state] = official_release_pipeline_state_counts.get(pipeline_state, 0) + 1
        for key in closure_counts:
            if item.get(key) is True:
                closure_counts[key] += 1

    return {
        'generated_at': datetime.now().astimezone().isoformat(),
        'job_count': len(items),
        'recoverability_counts': counts,
        'quality_grade_counts': quality_grade_counts,
        'quality_average_score': round(sum(scored_items) / len(scored_items), 2) if scored_items else None,
        'formalization_state_counts': formalization_state_counts,
        'human_approval_state_counts': human_approval_state_counts,
        'approval_recompute_state_counts': approval_recompute_state_counts,
        'release_execution_state_counts': release_execution_state_counts,
        'official_release_pipeline_state_counts': official_release_pipeline_state_counts,
        'closure_counts': closure_counts,
        'items': items,
    }


def export_recovery_dashboard(output_path: str | Path, jobs_root: str | Path = JOBS_ROOT) -> Path:
    payload = jobs_recovery_dashboard(jobs_root)
    output_path = Path(output_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return output_path


def write_recovery_markdown(payload: dict[str, Any], output_path: str | Path) -> Path:
    recoverability_map = {
        'none': '无需恢复', 'manual_intervention': '需人工处理', 'auto_retry': '自动重试',
        'retryable': '可重试', 'unknown': '待判断'
    }
    status_map = {
        'passed': '已通过', 'failed': '失败', 'rejected': '已拒绝', 'queued': '排队中',
        'claimed': '已领取', 'running': '运行中', 'artifact_ready': '产物已就绪', 'under_review': '审核中'
    }
    formalization_map = {
        'release_ready_candidate': '可发布候选结果', 'blocked_candidate': '受阻候选结果', 'manual_review_gate': '人工复核门禁'
    }
    approval_map = {'awaiting': '等待审批', 'approved': '已批准', 'rejected': '已拒绝'}
    recompute_map = {'awaiting_real_human_decision': '等待真实人工结论'}
    execution_map = {'blocked_pending_human_approval': '因等待人工审批而阻塞'}
    pipeline_map = {
        'awaiting_human_approval': '等待人工审批', 'candidate_not_ready': '候选结果尚未就绪',
        'approved_but_blocked': '已审批但仍阻塞', 'ready_but_execution_not_implemented': '已就绪但执行路径未实现',
        'rejected': '已拒绝'
    }
    blocker_map = {
        'human_approval_not_recorded': '人工审批结果未记录', 'official_release_rehearsal_not_ready': '正式发布预演未就绪',
        'pre_release_gate_not_ready': '发布前置门禁未就绪', 'release_artifact_binding_not_ready': '发布产物绑定未就绪',
        'rollback_not_ready': '回滚准备未就绪'
    }

    def translate(key: Any, mapping: dict[str, str]) -> Any:
        return mapping.get(str(key), key)

    def render_list(values: Any, mapping: dict[str, str] | None = None) -> str:
        if not values:
            return '无'
        if isinstance(values, list):
            return '；'.join(str(translate(v, mapping or {})) for v in values)
        return str(values)

    output_path = Path(output_path)
    lines = [
        '# 恢复处理看板',
        '',
        f"- 生成时间: {payload['generated_at']}",
        f"- 任务总数: {payload['job_count']}",
        '',
        '## 可恢复性分布',
    ]
    for key, value in sorted(payload.get('recoverability_counts', {}).items()):
        lines.append(f'- {translate(key, recoverability_map)}: {value}')
    lines.extend(['', '## 质量摘要'])
    lines.append(f"- 平均质量分: {payload.get('quality_average_score')}")
    for key, value in sorted(payload.get('quality_grade_counts', {}).items()):
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## 正式收口状态'])
    for key, value in sorted(payload.get('formalization_state_counts', {}).items()):
        lines.append(f'- {translate(key, formalization_map)}: {value}')
    lines.extend(['', '## 人工审批状态'])
    for key, value in sorted(payload.get('human_approval_state_counts', {}).items()):
        lines.append(f'- {translate(key, approval_map)}: {value}')
    lines.extend(['', '## 审批重算状态'])
    for key, value in sorted(payload.get('approval_recompute_state_counts', {}).items()):
        lines.append(f'- {translate(key, recompute_map)}: {value}')
    lines.extend(['', '## 发布执行状态'])
    for key, value in sorted(payload.get('release_execution_state_counts', {}).items()):
        lines.append(f'- {translate(key, execution_map)}: {value}')
    lines.extend(['', '## 正式发布管线状态'])
    for key, value in sorted(payload.get('official_release_pipeline_state_counts', {}).items()):
        lines.append(f'- {translate(key, pipeline_map)}: {value}')
    lines.extend(['', '## 收口就绪统计'])
    for key, value in sorted(payload.get('closure_counts', {}).items()):
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## 任务明细'])
    for item in payload.get('items', []):
        lines.append(
            f"- 任务={item['task_id']} | 角色={item['role']} | 状态={translate(item['status'], status_map)} | 质量={item.get('quality_score')}/{item.get('quality_grade')} | 正式收口={translate(item.get('formalization_state'), formalization_map)} | 人工审批={translate(item.get('human_approval_state'), approval_map)} | 审批重算={translate(item.get('approval_recompute_state'), recompute_map)} | 发布执行={translate(item.get('release_execution_state'), execution_map)} | 正式发布管线={translate(item.get('official_release_pipeline_state'), pipeline_map)} | 管线阻塞={render_list(item.get('official_release_pipeline_blockers'), blocker_map)} | 发布阻塞={render_list(item.get('release_execution_block_reasons'), blocker_map)} | 需要审批={'是' if item.get('approval_required') else '否'} | 允许发布动作={'是' if item.get('release_action_allowed') else '否'} | 支持回滚={'是' if item.get('rollback_supported') else '否'} | 可恢复性={translate(item['recoverability'], recoverability_map)} | 建议动作={item['recommended_action']} | 原因={item['reason']}"
        )
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output_path
