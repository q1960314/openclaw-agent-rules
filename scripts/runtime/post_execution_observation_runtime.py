#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from artifact_manager import ArtifactManager
from execution_binding_runtime import ensure_execution_batch, get_execution_run_context, validate_run_context
from execution_protocol_runtime import sync_all_execution_protocols
from release_closure_runtime import _load_json

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
DEFAULT_SLA_SECONDS = 3600
DEFAULT_OVERDUE_GRACE_SECONDS = 900
DEFAULT_TIMEOUT_GRACE_SECONDS = 3600

TARGET_CONFIG = {
    'release': {
        'label': 'official_release',
        'registration_artifact': 'official_release_record.json',
        'summary_artifact': 'release_observation_summary.json',
        'audit_artifact': 'release_observation_audit.json',
        'resolution_review_artifact': 'release_followup_resolution_review.json',
        'manual_classification_artifact': 'release_manual_classification_workflow.json',
        'registration_state': 'official_release_registered',
    },
    'rollback': {
        'label': 'rollback',
        'registration_artifact': 'rollback_registration_record.json',
        'summary_artifact': 'rollback_observation_summary.json',
        'audit_artifact': 'rollback_observation_audit.json',
        'resolution_review_artifact': 'rollback_followup_resolution_review.json',
        'manual_classification_artifact': 'rollback_manual_classification_workflow.json',
        'registration_state': 'rollback_registered',
    },
}

FOLLOWUP_ACTION_TO_STATE = {
    'ack': 'acknowledged',
    'assign': '__preserve__',
    'handoff': '__preserve__',
    'accept': 'acknowledged',
    'start': 'in_progress',
    'resolve': 'resolved',
    'close': 'closed',
    'reopen': 'reopened',
}
FOLLOWUP_UNRESOLVED_STATES = {'open', 'acknowledged', 'in_progress', 'reopened'}
FOLLOWUP_TERMINAL_STATES = {'resolved', 'closed'}
RESOLUTION_TAXONOMY = {
    'monitoring_false_positive': 'monitoring',
    'manual_intervention': 'operations',
    'code_fix_required': 'code',
    'config_correction': 'configuration',
    'rollback_recommended': 'release_decision',
    'rollback_effective': 'rollback_validation',
    'accepted_risk': 'risk_acceptance',
    'duplicate_or_noise': 'triage',
}


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _resolve_task_dir(*, task_dir: str | Path | None = None, task_id: str | None = None, jobs_root: str | Path = JOBS_ROOT) -> Path:
    if task_dir:
        resolved = Path(task_dir)
        if not resolved.exists():
            raise FileNotFoundError(f'task_dir not found: {resolved}')
        return resolved
    if task_id:
        resolved = Path(jobs_root) / task_id
        if not resolved.exists():
            raise FileNotFoundError(f'task_id not found under jobs_root: {resolved}')
        return resolved
    raise ValueError('task_dir or task_id is required')


def _normalize_list(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    normalized: list[str] = []
    for item in list(values or []):
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _parse_counts(raw: str) -> dict[str, int]:
    result = {
        'signal_count': 0,
        'drift_count': 0,
        'mismatch_count': 0,
        'anomaly_count': 0,
    }
    if not raw:
        return result
    for chunk in raw.split(','):
        chunk = chunk.strip()
        if not chunk or '=' not in chunk:
            continue
        key, value = chunk.split('=', 1)
        key = key.strip().lower()
        if key not in result:
            continue
        try:
            result[key] = max(0, int(value.strip()))
        except Exception:
            continue
    return result


def _ensure_registered_state(target: str, registration: dict[str, Any]) -> None:
    if registration.get('record_state') != TARGET_CONFIG[target]['registration_state']:
        raise ValueError(f'{target} registration is not in registered state')


def _normalize_followup_state(state: str | None, *, requires_manual_followup: bool) -> str:
    normalized = str(state or '').strip().lower()
    if normalized in FOLLOWUP_UNRESOLVED_STATES | FOLLOWUP_TERMINAL_STATES:
        return normalized
    return 'open' if requires_manual_followup else 'not_required'


def _followup_status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {'open': 0, 'in_progress': 0, 'resolved': 0, 'closed': 0}
    for item in items:
        state = _normalize_followup_state(item.get('followup_item_state'), requires_manual_followup=bool(item.get('requires_manual_followup')))
        if state in {'open', 'acknowledged', 'reopened'}:
            counts['open'] += 1
        elif state == 'in_progress':
            counts['in_progress'] += 1
        elif state == 'resolved':
            counts['resolved'] += 1
        elif state == 'closed':
            counts['closed'] += 1
    return counts


def _normalize_resolution_category(value: str | None) -> str | None:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in RESOLUTION_TAXONOMY else None


def _resolution_taxonomy_payload(category: str | None) -> dict[str, Any]:
    normalized = _normalize_resolution_category(category)
    if not normalized:
        return {'category': None, 'taxonomy': None}
    return {'category': normalized, 'taxonomy': RESOLUTION_TAXONOMY.get(normalized)}


def _category_from_taxonomy(taxonomy: str | None) -> str | None:
    normalized = str(taxonomy or '').strip().lower()
    if not normalized:
        return None
    for category, bucket in RESOLUTION_TAXONOMY.items():
        if bucket == normalized:
            return category
    return None


def _collect_resolution_texts(observation: dict[str, Any], followup: dict[str, Any]) -> list[str]:
    texts = [
        followup.get('followup_resolution_note'),
        followup.get('followup_closure_note'),
        followup.get('followup_resolution_summary'),
        observation.get('completion_note'),
        observation.get('failure_reason'),
        observation.get('note'),
    ]
    closure_audit = followup.get('followup_closure_audit') or {}
    if isinstance(closure_audit, dict):
        texts.extend([
            closure_audit.get('closure_note'),
            closure_audit.get('resolution_summary'),
            closure_audit.get('resolution_category'),
            closure_audit.get('resolution_taxonomy'),
        ])
    for item in list(followup.get('followup_history', []) or []):
        if not isinstance(item, dict):
            continue
        texts.extend([item.get('note'), item.get('resolution_category')])
    return [str(item).strip().lower() for item in texts if str(item or '').strip()]


def _infer_resolution_category(*, target: str, observation: dict[str, Any], followup: dict[str, Any]) -> tuple[str | None, str]:
    closure_audit = followup.get('followup_closure_audit') or {}
    if isinstance(closure_audit, dict):
        direct = _normalize_resolution_category(closure_audit.get('resolution_category'))
        if direct:
            return direct, 'closure_audit.resolution_category'
        from_taxonomy = _category_from_taxonomy(closure_audit.get('resolution_taxonomy'))
        if from_taxonomy:
            return from_taxonomy, 'closure_audit.resolution_taxonomy'

    history = list(followup.get('followup_history', []) or [])
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        inferred = _normalize_resolution_category(item.get('resolution_category'))
        if inferred:
            return inferred, 'followup_history.resolution_category'

    texts = ' '.join(_collect_resolution_texts(observation, followup))
    keyword_rules = [
        ('monitoring_false_positive', ['false positive', '误报', '误触发', 'monitoring false positive']),
        ('duplicate_or_noise', ['duplicate', 'noise', '噪声', '重复']),
        ('config_correction', ['config', 'configuration', '配置']),
        ('code_fix_required', ['code fix', 'bug fix', 'patch', '修复', '代码']),
        ('accepted_risk', ['accepted risk', 'risk accepted', '接受风险', '已接受风险']),
    ]
    if 'rollback' in texts or '回滚' in texts:
        if target == 'rollback':
            return 'rollback_effective', 'keyword:rollback'
        return 'rollback_recommended', 'keyword:rollback'
    for category, keywords in keyword_rules:
        if any(keyword in texts for keyword in keywords):
            return category, f'keyword:{category}'

    if target == 'rollback' and observation.get('observation_state') == 'observation_completed':
        return 'rollback_effective', 'target=rollback+observation_completed'
    if followup.get('followup_item_state') in FOLLOWUP_TERMINAL_STATES and texts:
        return 'manual_intervention', 'terminal_followup_with_text'
    return None, 'manual_classification_required'


def _build_closure_audit_payload(*, followup: dict[str, Any], observation: dict[str, Any], category: str | None, closed_at: str | None, closed_by: str | None) -> dict[str, Any] | None:
    normalized = _normalize_resolution_category(category)
    if not normalized:
        return None
    history = list(followup.get('followup_history', []) or [])
    return {
        'closed_at': closed_at or followup.get('followup_last_action_at') or observation.get('closed_at') or _now(),
        'closed_by': closed_by or followup.get('followup_last_actor') or observation.get('closed_by') or 'system_backfill',
        'closure_note': followup.get('followup_closure_note') or followup.get('followup_resolution_note') or observation.get('failure_reason') or observation.get('completion_note') or '',
        'resolution_category': normalized,
        'resolution_taxonomy': RESOLUTION_TAXONOMY.get(normalized),
        'resolution_summary': followup.get('followup_resolution_summary') or followup.get('followup_resolution_note') or followup.get('followup_closure_note') or observation.get('failure_reason') or observation.get('completion_note') or '',
        'final_assignee': followup.get('followup_assignee'),
        'handoff_count': int(followup.get('followup_handoff_count') or 0),
        'history_count': len(history),
    }


def _build_followup_resolution_review(*, task_dir: Path, target: str, observation: dict[str, Any], followup: dict[str, Any]) -> dict[str, Any]:
    normalized_target = target if target in TARGET_CONFIG else ('release' if observation.get('execution_target') == TARGET_CONFIG['release']['label'] else 'rollback')
    cfg = TARGET_CONFIG[normalized_target]
    backfill = dict(followup.get('followup_backfill') or {})
    closure_audit = followup.get('followup_closure_audit') or {}
    resolution_category = _normalize_resolution_category(followup.get('followup_resolution_category'))
    resolution_taxonomy = (followup.get('followup_resolution_taxonomy') or {}).get('taxonomy') or RESOLUTION_TAXONOMY.get(resolution_category)
    recent_history = list(followup.get('followup_history', []) or [])[-5:]
    manual_workflow = dict(followup.get('manual_classification_workflow') or {})
    manual_state = str(manual_workflow.get('state') or ('closed' if not backfill.get('manual_classification_required') and resolution_category else 'pending')).strip().lower()
    requires_manual_classification = bool(backfill.get('manual_classification_required')) or manual_state in {'pending', 'claimed', 'classified', 'confirmed'} or resolution_category in {None, 'needs_manual_classification', 'unclassified'}
    insights: list[str] = []
    if resolution_category:
        insights.append(f"resolved_as:{resolution_category}")
    if resolution_taxonomy:
        insights.append(f"taxonomy:{resolution_taxonomy}")
    if backfill.get('manual_classification_required'):
        insights.append('needs_manual_classification')
    if manual_state:
        insights.append(f"manual_classification_state:{manual_state}")
    if closure_audit:
        insights.append(f"closure_by:{closure_audit.get('closed_by') or followup.get('followup_last_actor') or 'unknown'}")
    if int(followup.get('followup_handoff_count') or 0) > 0:
        insights.append(f"handoff_count:{int(followup.get('followup_handoff_count') or 0)}")
    return {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'resolution_review_artifact': cfg['resolution_review_artifact'],
        'manual_classification_artifact': cfg['manual_classification_artifact'],
        'batch_id': observation.get('batch_id'),
        'run_id': observation.get('run_id'),
        'observation_state': observation.get('observation_state'),
        'requires_manual_followup': bool(followup.get('requires_manual_followup')),
        'followup_item_state': followup.get('followup_item_state'),
        'followup_terminal': bool(followup.get('followup_terminal')),
        'resolution_category': resolution_category,
        'resolution_taxonomy': resolution_taxonomy,
        'resolution_summary': followup.get('followup_resolution_summary') or (closure_audit.get('resolution_summary') if isinstance(closure_audit, dict) else '') or '',
        'closure_audit': closure_audit if isinstance(closure_audit, dict) else None,
        'closure_note': followup.get('followup_closure_note') or (closure_audit.get('closure_note') if isinstance(closure_audit, dict) else '') or '',
        'owner': followup.get('followup_owner'),
        'assignee': followup.get('followup_assignee'),
        'assignment_status': followup.get('followup_assignment_status'),
        'handoff_count': int(followup.get('followup_handoff_count') or 0),
        'backfill': backfill,
        'manual_classification_workflow': manual_workflow,
        'manual_classification_state': manual_state,
        'manual_classification_required': requires_manual_classification,
        'knowledge_sink_ready': bool(resolution_category or backfill.get('manual_classification_required') or manual_workflow),
        'recent_history': recent_history,
        'closure_insights': insights,
        'generated_at': _now(),
    }


def _history_entry(source: dict[str, Any]) -> dict[str, Any]:
    return {
        'execution_target': source.get('execution_target'),
        'batch_id': source.get('batch_id'),
        'run_id': source.get('run_id'),
        'observation_state': source.get('observation_state'),
        'sla_state': source.get('sla_state'),
        'opened_at': source.get('opened_at'),
        'closed_at': source.get('closed_at'),
        'deadline_at': source.get('deadline_at'),
        'timeout_at': source.get('timeout_at'),
        'observation_completed': source.get('observation_completed'),
        'observation_failed': source.get('observation_failed'),
        'observation_timed_out': source.get('observation_timed_out'),
        'requires_manual_followup': source.get('requires_manual_followup'),
        'manual_followup_reason': source.get('manual_followup_reason'),
        'summary_artifact': source.get('summary_artifact'),
        'audit_artifact': source.get('audit_artifact'),
        'followup_artifact': source.get('followup_artifact'),
        'followup_assignee': source.get('followup_assignee'),
        'followup_assignment_status': source.get('followup_assignment_status'),
        'followup_handoff_count': source.get('followup_handoff_count'),
        'followup_resolution_category': source.get('followup_resolution_category'),
        'followup_closure_audit': source.get('followup_closure_audit'),
        'anomaly_count': source.get('observation_anomaly_count'),
    }


def _compute_sla_fields(observation: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now_dt = now or datetime.now().astimezone()
    opened_at = _parse_ts(observation.get('opened_at'))
    closed_at = _parse_ts(observation.get('closed_at'))
    deadline_at = _parse_ts(observation.get('deadline_at'))
    overdue_at = _parse_ts(observation.get('overdue_at'))
    timeout_at = _parse_ts(observation.get('timeout_at'))
    final_state = observation.get('observation_state')
    active = bool(observation.get('observation_window_active')) and final_state == 'observing'

    if not opened_at:
        return {
            'sla_state': 'not_started',
            'deadline_at': observation.get('deadline_at'),
            'overdue_at': observation.get('overdue_at'),
            'timeout_at': observation.get('timeout_at'),
            'sla_seconds': int(observation.get('sla_seconds') or 0),
            'overdue_grace_seconds': int(observation.get('overdue_grace_seconds') or 0),
            'timeout_grace_seconds': int(observation.get('timeout_grace_seconds') or 0),
            'is_overdue': False,
            'is_timed_out': False,
            'within_observation_window': False,
            'seconds_to_deadline': None,
            'seconds_past_deadline': None,
        }

    if not deadline_at:
        deadline_at = opened_at + timedelta(seconds=max(0, int(observation.get('sla_seconds') or 0)))
    if not overdue_at:
        overdue_at = deadline_at + timedelta(seconds=max(0, int(observation.get('overdue_grace_seconds') or 0)))
    if not timeout_at:
        timeout_at = deadline_at + timedelta(seconds=max(0, int(observation.get('timeout_grace_seconds') or 0)))

    reference_dt = closed_at or now_dt
    seconds_to_deadline = int((deadline_at - reference_dt).total_seconds())
    seconds_past_deadline = max(0, int((reference_dt - deadline_at).total_seconds()))

    if final_state == 'observation_completed':
        sla_state = 'completed_on_time' if closed_at and closed_at <= deadline_at else 'completed_late'
        is_overdue = False
        is_timed_out = False
    elif final_state == 'observation_failed':
        sla_state = 'failed_before_deadline' if closed_at and closed_at <= deadline_at else 'failed_after_deadline'
        is_overdue = False
        is_timed_out = False
    elif final_state == 'observation_timed_out':
        sla_state = 'timed_out'
        is_overdue = True
        is_timed_out = True
    elif not active:
        sla_state = 'inactive'
        is_overdue = False
        is_timed_out = False
    elif now_dt >= timeout_at:
        sla_state = 'timed_out'
        is_overdue = True
        is_timed_out = True
    elif now_dt >= overdue_at:
        sla_state = 'overdue'
        is_overdue = True
        is_timed_out = False
    elif now_dt >= deadline_at:
        sla_state = 'deadline_breached'
        is_overdue = False
        is_timed_out = False
    else:
        sla_state = 'within_sla'
        is_overdue = False
        is_timed_out = False

    return {
        'sla_state': sla_state,
        'deadline_at': _iso(deadline_at),
        'overdue_at': _iso(overdue_at),
        'timeout_at': _iso(timeout_at),
        'sla_seconds': int(observation.get('sla_seconds') or 0),
        'overdue_grace_seconds': int(observation.get('overdue_grace_seconds') or 0),
        'timeout_grace_seconds': int(observation.get('timeout_grace_seconds') or 0),
        'is_overdue': is_overdue,
        'is_timed_out': is_timed_out,
        'within_observation_window': active,
        'seconds_to_deadline': seconds_to_deadline,
        'seconds_past_deadline': seconds_past_deadline if seconds_past_deadline > 0 else 0,
    }


def _build_followup_actions(*, task_dir: Path, target: str, observation: dict[str, Any], final_state: str, note: str, drift_findings: list[str], mismatch_findings: list[str], anomaly_findings: list[str], signal_count: int) -> dict[str, Any]:
    execution_target = TARGET_CONFIG[target]['label']
    reasons = []
    if final_state == 'observation_failed':
        reasons.append('observation_failed')
    if final_state == 'observation_timed_out':
        reasons.append('observation_timed_out')
    if drift_findings:
        reasons.append('drift_detected')
    if mismatch_findings:
        reasons.append('mismatch_detected')
    if anomaly_findings:
        reasons.append('anomaly_detected')
    if observation.get('is_overdue'):
        reasons.append('observation_overdue')
    if signal_count <= 0:
        reasons.append('no_positive_observation_signal')

    requires_manual_followup = bool(reasons)
    if final_state == 'observation_timed_out':
        escalation_level = 'critical'
    elif final_state == 'observation_failed':
        escalation_level = 'high'
    elif anomaly_findings or mismatch_findings or drift_findings:
        escalation_level = 'medium'
    elif requires_manual_followup:
        escalation_level = 'medium'
    else:
        escalation_level = 'none'

    recommended_owner = 'human_operator'
    recommended_routing_target = 'human_operator'
    routing_targets: list[str] = []
    if requires_manual_followup:
        routing_targets.append('human_operator')
    if final_state in {'observation_failed', 'observation_timed_out'}:
        routing_targets.append('ops_monitor')
    if drift_findings or mismatch_findings:
        routing_targets.append('coder')
    if anomaly_findings:
        routing_targets.append('test-expert')
    if target == 'release' and final_state in {'observation_failed', 'observation_timed_out'}:
        routing_targets.append('master-quant')
    if target == 'rollback' and requires_manual_followup:
        routing_targets.append('master-quant')

    seen: set[str] = set()
    ordered_routing_targets: list[str] = []
    for item in routing_targets:
        if item in seen:
            continue
        seen.add(item)
        ordered_routing_targets.append(item)
    if 'ops_monitor' in ordered_routing_targets:
        recommended_owner = 'ops_monitor'
        recommended_routing_target = 'ops_monitor'
    elif 'coder' in ordered_routing_targets:
        recommended_owner = 'coder'
        recommended_routing_target = 'coder'
    elif 'test-expert' in ordered_routing_targets:
        recommended_owner = 'test-expert'
        recommended_routing_target = 'test-expert'

    priority_rank = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'none': 9}
    queue_priority = escalation_level if requires_manual_followup else 'none'
    actions: list[dict[str, Any]] = []
    if requires_manual_followup:
        actions.append({
            'action_id': 'manual_review',
            'action_type': 'manual_review',
            'priority': 'high',
            'required': True,
            'recommended_owner': 'human_operator',
            'routing_target': 'human_operator',
            'title': '人工复核观察结果',
            'reason': '需要人工确认观察失败/超时/异常是否影响发布结果。',
        })
        if final_state in {'observation_failed', 'observation_timed_out'}:
            actions.append({
                'action_id': 'escalate_alert',
                'action_type': 'escalate_alert',
                'priority': 'high',
                'required': True,
                'recommended_owner': 'ops_monitor',
                'routing_target': 'ops_monitor',
                'title': '升级告警',
                'reason': '观察窗口未正常闭合，应升级给运维/值班负责人。',
            })
        if drift_findings or mismatch_findings:
            actions.append({
                'action_id': 'route_for_code_investigation',
                'action_type': 'investigate_code_path',
                'priority': 'medium',
                'required': True,
                'recommended_owner': 'coder',
                'routing_target': 'coder',
                'title': '排查发布/回滚代码与配置漂移',
                'reason': '发现 drift/mismatch，需要代码守护者排查执行路径与产物一致性。',
            })
        if anomaly_findings:
            actions.append({
                'action_id': 'route_for_validation_review',
                'action_type': 'validation_review',
                'priority': 'medium',
                'required': True,
                'recommended_owner': 'test-expert',
                'routing_target': 'test-expert',
                'title': '复核异常信号与验证证据',
                'reason': '发现异常信号，需要测试专家复核监测口径与证据。',
            })
        if target == 'release':
            actions.append({
                'action_id': 'assess_rollback_recommendation',
                'action_type': 'rollback_recommendation',
                'priority': 'high' if final_state in {'observation_failed', 'observation_timed_out'} else 'medium',
                'required': final_state in {'observation_failed', 'observation_timed_out'},
                'recommended_owner': 'human_operator',
                'routing_target': 'master-quant',
                'title': '评估是否建议人工回滚',
                'reason': '仅生成建议，不触发真实自动回滚。',
            })
        else:
            actions.append({
                'action_id': 'verify_rollback_effectiveness',
                'action_type': 'manual_review',
                'priority': 'medium',
                'required': True,
                'recommended_owner': 'human_operator',
                'routing_target': 'master-quant',
                'title': '确认回滚效果是否达到预期',
                'reason': '回滚观察失败/超时后需人工确认风险是否解除。',
            })
    followup_item_state = 'open' if requires_manual_followup else 'not_required'
    return {
        'task_id': task_dir.name,
        'record_type': 'observation_followup_protocol',
        'execution_target': execution_target,
        'batch_id': observation.get('batch_id'),
        'run_id': observation.get('run_id'),
        'observation_state': final_state,
        'sla_state': observation.get('sla_state'),
        'requires_manual_followup': requires_manual_followup,
        'manual_followup_reason': reasons,
        'followup_item_state': followup_item_state,
        'followup_item_open': requires_manual_followup,
        'followup_terminal': not requires_manual_followup,
        'followup_opened_at': _now() if requires_manual_followup else None,
        'followup_acknowledged_at': None,
        'followup_started_at': None,
        'followup_resolved_at': None,
        'followup_closed_at': None,
        'followup_reopened_at': None,
        'followup_last_action': 'created' if requires_manual_followup else 'not_required',
        'followup_last_action_at': _now(),
        'followup_last_actor': None,
        'followup_resolution_note': '',
        'followup_closure_note': '',
        'followup_owner': recommended_owner,
        'followup_assignee': None,
        'followup_assignment_status': 'unassigned' if requires_manual_followup else 'not_required',
        'followup_assigned_at': None,
        'followup_ownership_acknowledged_at': None,
        'followup_ownership_acknowledged_by': None,
        'followup_handoff_count': 0,
        'followup_handoff_history': [],
        'followup_resolution_category': None,
        'followup_resolution_taxonomy': _resolution_taxonomy_payload(None),
        'followup_resolution_summary': '',
        'followup_closure_audit': None,
        'followup_history': ([{
            'action': 'created',
            'to_state': 'open',
            'at': _now(),
            'actor': 'system',
            'note': note or 'Observation follow-up item created from finalized observation.',
        }] if requires_manual_followup else []),
        'escalation_level': escalation_level,
        'queue_priority': queue_priority,
        'queue_priority_rank': priority_rank.get(queue_priority, 9),
        'recommended_owner': recommended_owner,
        'recommended_routing_target': recommended_routing_target,
        'routing_targets': ordered_routing_targets,
        'actions': actions,
        'action_count': len(actions),
        'signal_count': signal_count,
        'drift_findings': drift_findings,
        'mismatch_findings': mismatch_findings,
        'anomaly_findings': anomaly_findings,
        'status_counts': _followup_status_counts([{'followup_item_state': followup_item_state, 'requires_manual_followup': requires_manual_followup}]),
        'summary': note,
        'generated_at': _now(),
        'note': 'Standardized post-observation follow-up protocol only. It recommends manual actions and must not trigger automatic release/rollback execution.',
    }


def _build_history_aggregate(*, task_dir: Path, current: dict[str, Any]) -> dict[str, Any]:
    history = list(current.get('history', []) or [])
    current_entry = _history_entry(current)
    full_history = history + ([current_entry] if current.get('opened_at') else [])
    by_target: dict[str, int] = {}
    by_state: dict[str, int] = {}
    manual_followup_count = 0
    timeout_count = 0
    for item in full_history:
        tgt = item.get('execution_target') or 'unknown'
        state = item.get('observation_state') or 'unknown'
        by_target[tgt] = by_target.get(tgt, 0) + 1
        by_state[state] = by_state.get(state, 0) + 1
        if item.get('requires_manual_followup'):
            manual_followup_count += 1
        if item.get('observation_timed_out') or item.get('sla_state') == 'timed_out':
            timeout_count += 1
    recent = full_history[-5:]
    return {
        'task_id': task_dir.name,
        'record_type': 'observation_history_aggregate',
        'history_count': len(full_history),
        'execution_target_counts': by_target,
        'observation_state_counts': by_state,
        'manual_followup_count': manual_followup_count,
        'timeout_count': timeout_count,
        'latest_execution_target': current.get('execution_target'),
        'latest_observation_state': current.get('observation_state'),
        'latest_sla_state': current.get('sla_state'),
        'latest_requires_manual_followup': current.get('requires_manual_followup'),
        'latest_deadline_at': current.get('deadline_at'),
        'latest_timeout_at': current.get('timeout_at'),
        'latest_run_id': current.get('run_id'),
        'latest_batch_id': current.get('batch_id'),
        'recent_results': recent,
        'generated_at': _now(),
        'note': 'Task-local observation history/trend aggregate across release and rollback observation windows.',
    }


def _build_observation_artifacts(*, task_dir: Path, target: str, observation: dict[str, Any], finalized_by: str, final_state: str, note: str, signal_count: int, drift_findings: list[str], mismatch_findings: list[str], anomaly_findings: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg = TARGET_CONFIG[target]
    drift_count = len(drift_findings)
    mismatch_count = len(mismatch_findings)
    anomaly_count = len(anomaly_findings)
    healthy = final_state == 'observation_completed' and drift_count == 0 and mismatch_count == 0 and anomaly_count == 0
    followup = _build_followup_actions(
        task_dir=task_dir,
        target=target,
        observation=observation,
        final_state=final_state,
        note=note,
        drift_findings=drift_findings,
        mismatch_findings=mismatch_findings,
        anomaly_findings=anomaly_findings,
        signal_count=signal_count,
    )

    summary = {
        'task_id': task_dir.name,
        'record_type': 'observation_summary',
        'execution_target': cfg['label'],
        'batch_id': observation.get('batch_id'),
        'run_id': observation.get('run_id'),
        'observation_state': final_state,
        'sla_state': observation.get('sla_state'),
        'observation_completed': final_state == 'observation_completed',
        'observation_failed': final_state == 'observation_failed',
        'observation_timed_out': final_state == 'observation_timed_out',
        'summary_visible': True,
        'signal_count': signal_count,
        'drift_count': drift_count,
        'mismatch_count': mismatch_count,
        'anomaly_count': anomaly_count,
        'healthy': healthy,
        'opened_at': observation.get('opened_at'),
        'deadline_at': observation.get('deadline_at'),
        'timeout_at': observation.get('timeout_at'),
        'closed_at': observation.get('closed_at'),
        'finalized_by': finalized_by,
        'final_note': note,
        'requires_manual_followup': followup.get('requires_manual_followup'),
        'manual_followup_reason': followup.get('manual_followup_reason'),
        'generated_at': _now(),
        'note': 'Structured summary of the post-execution observation window. Counts may be manual/placeholder until real monitoring sources are connected.',
    }
    audit = {
        'task_id': task_dir.name,
        'record_type': 'observation_audit',
        'execution_target': cfg['label'],
        'batch_id': observation.get('batch_id'),
        'run_id': observation.get('run_id'),
        'observation_state': final_state,
        'sla_state': observation.get('sla_state'),
        'observation_completed': final_state == 'observation_completed',
        'observation_failed': final_state == 'observation_failed',
        'observation_timed_out': final_state == 'observation_timed_out',
        'consistency_checks': {
            'registration_present': bool(observation.get('registration_recorded_at')),
            'registration_state_valid': observation.get('registration_state') == TARGET_CONFIG[target]['registration_state'],
            'batch_id_present': bool(observation.get('batch_id')),
            'run_id_present': bool(observation.get('run_id')),
            'opened_before_closed': bool(observation.get('opened_at')) and bool(observation.get('closed_at')) and observation.get('opened_at') <= observation.get('closed_at'),
            'window_inactive_after_finalize': observation.get('observation_window_active') is False,
            'completed_not_marked_timeout': not (final_state == 'observation_completed' and observation.get('observation_timed_out')),
        },
        'signals': {
            'signal_count': signal_count,
            'drift_findings': drift_findings,
            'mismatch_findings': mismatch_findings,
            'anomaly_findings': anomaly_findings,
            'drift_count': drift_count,
            'mismatch_count': mismatch_count,
            'anomaly_count': anomaly_count,
        },
        'followup': {
            'requires_manual_followup': followup.get('requires_manual_followup'),
            'manual_followup_reason': followup.get('manual_followup_reason'),
            'action_count': followup.get('action_count'),
        },
        'finalized_by': finalized_by,
        'opened_at': observation.get('opened_at'),
        'deadline_at': observation.get('deadline_at'),
        'timeout_at': observation.get('timeout_at'),
        'closed_at': observation.get('closed_at'),
        'generated_at': _now(),
        'note': note,
    }
    history_aggregate = _build_history_aggregate(task_dir=task_dir, current=observation)
    return summary, audit, followup, history_aggregate


def _sync_followup_backfill(*, task_dir: Path, observation: dict[str, Any], followup: dict[str, Any], manager: ArtifactManager | None = None) -> None:
    state = _normalize_followup_state(followup.get('followup_item_state'), requires_manual_followup=bool(followup.get('requires_manual_followup')))
    followup['followup_item_state'] = state
    unresolved = bool(followup.get('requires_manual_followup')) and state in FOLLOWUP_UNRESOLVED_STATES
    followup['followup_item_open'] = unresolved
    followup['followup_terminal'] = state in FOLLOWUP_TERMINAL_STATES or not bool(followup.get('requires_manual_followup'))
    followup['status_counts'] = _followup_status_counts([followup])
    normalized_category = _normalize_resolution_category(followup.get('followup_resolution_category'))
    followup['followup_resolution_category'] = normalized_category
    followup['followup_resolution_taxonomy'] = followup.get('followup_resolution_taxonomy') or _resolution_taxonomy_payload(normalized_category)

    observation['followup_item_state'] = state
    observation['followup_item_open'] = unresolved
    observation['followup_terminal'] = followup['followup_terminal']
    observation['followup_updated_at'] = followup.get('followup_last_action_at') or followup.get('generated_at')
    observation['followup_last_action'] = followup.get('followup_last_action')
    observation['followup_resolution_note'] = followup.get('followup_resolution_note', '')
    observation['followup_closure_note'] = followup.get('followup_closure_note', '')
    observation['followup_owner'] = followup.get('followup_owner')
    observation['followup_assignee'] = followup.get('followup_assignee')
    observation['followup_assignment_status'] = followup.get('followup_assignment_status')
    observation['followup_handoff_count'] = int(followup.get('followup_handoff_count') or 0)
    observation['followup_resolution_category'] = normalized_category
    observation['followup_resolution_taxonomy'] = followup.get('followup_resolution_taxonomy') or _resolution_taxonomy_payload(normalized_category)
    observation['followup_resolution_summary'] = followup.get('followup_resolution_summary', '')
    observation['followup_closure_audit'] = followup.get('followup_closure_audit')
    observation['manual_classification_workflow'] = followup.get('manual_classification_workflow') or {}
    observation['manual_classification_state'] = ((followup.get('manual_classification_workflow') or {}).get('state'))

    cfg_target = 'release' if observation.get('execution_target') == TARGET_CONFIG['release']['label'] else 'rollback'
    review_payload = _build_followup_resolution_review(task_dir=task_dir, target=cfg_target, observation=observation, followup=followup)
    followup['resolution_review_artifact'] = TARGET_CONFIG[cfg_target]['resolution_review_artifact']
    observation['resolution_review_artifact'] = TARGET_CONFIG[cfg_target]['resolution_review_artifact']
    observation['followup_backfill'] = followup.get('followup_backfill') or {}

    summary_path = task_dir / 'artifacts' / TARGET_CONFIG[cfg_target]['summary_artifact']
    summary = _load_json(summary_path)
    if summary:
        summary['followup_item_state'] = state
        summary['followup_item_open'] = unresolved
        summary['followup_terminal'] = followup['followup_terminal']
        summary['followup_status_counts'] = followup['status_counts']
        summary['followup_last_action'] = followup.get('followup_last_action')
        summary['followup_last_action_at'] = followup.get('followup_last_action_at')
        summary['followup_last_actor'] = followup.get('followup_last_actor')
        summary['followup_resolution_note'] = followup.get('followup_resolution_note', '')
        summary['followup_closure_note'] = followup.get('followup_closure_note', '')
        summary['followup_owner'] = followup.get('followup_owner')
        summary['followup_assignee'] = followup.get('followup_assignee')
        summary['followup_assignment_status'] = followup.get('followup_assignment_status')
        summary['followup_handoff_count'] = int(followup.get('followup_handoff_count') or 0)
        summary['followup_resolution_category'] = normalized_category
        summary['followup_resolution_taxonomy'] = followup.get('followup_resolution_taxonomy') or _resolution_taxonomy_payload(normalized_category)
        summary['followup_resolution_summary'] = followup.get('followup_resolution_summary', '')
        summary['followup_closure_audit'] = followup.get('followup_closure_audit')
        summary['followup_backfill'] = followup.get('followup_backfill') or {}
        summary['manual_classification_workflow'] = followup.get('manual_classification_workflow') or {}
        summary['manual_classification_state'] = ((followup.get('manual_classification_workflow') or {}).get('state'))
        summary['resolution_review_artifact'] = TARGET_CONFIG[cfg_target]['resolution_review_artifact']
        summary['generated_at'] = _now()
        if manager:
            manager.write_json(TARGET_CONFIG[cfg_target]['summary_artifact'], summary)
        else:
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if manager:
        manager.write_json(TARGET_CONFIG[cfg_target]['resolution_review_artifact'], review_payload)
    else:
        (task_dir / 'artifacts' / TARGET_CONFIG[cfg_target]['resolution_review_artifact']).write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding='utf-8')


def apply_followup_action(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, action: str, acted_by: str = 'human', note: str = '', assignee: str = '', resolution_category: str = '', resolution_summary: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    observation = _load_json(artifacts_dir / 'post_execution_observation.json')
    if not observation:
        raise FileNotFoundError('missing required artifact: post_execution_observation.json')
    if observation.get('execution_target') != TARGET_CONFIG[target]['label']:
        raise ValueError(f'active observation target mismatch: expected {TARGET_CONFIG[target]["label"]}, got {observation.get("execution_target")}')
    followup_path = artifacts_dir / f'{target}_observation_followup_protocol.json'
    followup = _load_json(followup_path)
    if not followup:
        raise FileNotFoundError(f'missing required artifact: {followup_path.name}')
    if not followup.get('requires_manual_followup'):
        raise ValueError('follow-up item not required for this observation')

    current_state = _normalize_followup_state(followup.get('followup_item_state'), requires_manual_followup=True)
    raw_next_state = FOLLOWUP_ACTION_TO_STATE.get(action)
    if not raw_next_state:
        raise ValueError(f'unsupported follow-up action: {action}')
    next_state = current_state if raw_next_state == '__preserve__' else raw_next_state

    allowed: dict[str, set[str]] = {
        'ack': {'open', 'reopened'},
        'assign': {'open', 'acknowledged', 'in_progress', 'resolved', 'closed', 'reopened'},
        'handoff': {'open', 'acknowledged', 'in_progress', 'resolved', 'closed', 'reopened'},
        'accept': {'open', 'acknowledged', 'in_progress', 'reopened'},
        'start': {'open', 'acknowledged', 'reopened'},
        'resolve': {'open', 'acknowledged', 'in_progress', 'reopened'},
        'close': {'resolved'},
        'reopen': {'resolved', 'closed'},
    }
    if current_state not in allowed[action]:
        raise ValueError(f'follow-up action {action} not allowed from state {current_state}')

    at = _now()
    normalized_assignee = str(assignee or '').strip() or None
    normalized_category = _normalize_resolution_category(resolution_category) or _normalize_resolution_category(followup.get('followup_resolution_category'))
    normalized_summary = str(resolution_summary or '').strip() or str(followup.get('followup_resolution_summary') or '').strip()
    history = list(followup.get('followup_history', []) or [])
    handoff_history = list(followup.get('followup_handoff_history', []) or [])
    previous_assignee = followup.get('followup_assignee')

    if action in {'assign', 'handoff'} and not normalized_assignee:
        raise ValueError(f'follow-up action {action} requires assignee')
    if action == 'resolve' and not normalized_category:
        raise ValueError('resolve action requires resolution_category')
    if action == 'close' and not normalized_category:
        raise ValueError('closed follow-up item must include resolution_category before closure')

    if action == 'assign':
        followup['followup_assignee'] = normalized_assignee
        followup['followup_assignment_status'] = 'assigned'
        followup['followup_assigned_at'] = at
    elif action == 'handoff':
        handoff_record = {
            'from_assignee': previous_assignee,
            'to_assignee': normalized_assignee,
            'at': at,
            'actor': acted_by,
            'note': note,
        }
        handoff_history.append(handoff_record)
        followup['followup_handoff_history'] = handoff_history
        followup['followup_handoff_count'] = len(handoff_history)
        followup['followup_assignee'] = normalized_assignee
        followup['followup_assignment_status'] = 'assigned'
        followup['followup_assigned_at'] = at
    elif action == 'accept':
        if not followup.get('followup_assignee'):
            followup['followup_assignee'] = acted_by
        followup['followup_assignment_status'] = 'acknowledged'
        followup['followup_ownership_acknowledged_at'] = at
        followup['followup_ownership_acknowledged_by'] = acted_by
    elif action == 'resolve':
        followup['followup_resolved_at'] = at
        followup['followup_resolution_note'] = note
        followup['followup_resolution_category'] = normalized_category
        followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
        followup['followup_resolution_summary'] = normalized_summary or note
    elif action == 'close':
        followup['followup_closed_at'] = at
        followup['followup_closure_note'] = note
        followup['followup_resolution_category'] = normalized_category
        followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
        followup['followup_resolution_summary'] = normalized_summary or followup.get('followup_resolution_note') or note
        followup['followup_closure_audit'] = {
            'closed_at': at,
            'closed_by': acted_by,
            'closure_note': note,
            'resolution_category': normalized_category,
            'resolution_taxonomy': RESOLUTION_TAXONOMY.get(normalized_category),
            'resolution_summary': followup.get('followup_resolution_summary') or normalized_summary or note,
            'final_assignee': followup.get('followup_assignee'),
            'handoff_count': int(followup.get('followup_handoff_count') or 0),
            'history_count': len(history) + 1,
        }
    elif action == 'ack':
        followup['followup_acknowledged_at'] = at
    elif action == 'start':
        followup['followup_started_at'] = at
    elif action == 'reopen':
        followup['followup_reopened_at'] = at
        followup['followup_closed_at'] = None
        followup['followup_closure_audit'] = None

    history.append({
        'action': action,
        'from_state': current_state,
        'to_state': next_state,
        'at': at,
        'actor': acted_by,
        'assignee': followup.get('followup_assignee'),
        'resolution_category': followup.get('followup_resolution_category'),
        'note': note,
    })
    followup['followup_item_state'] = next_state
    followup['followup_last_action'] = action
    followup['followup_last_action_at'] = at
    followup['followup_last_actor'] = acted_by
    followup['followup_history'] = history
    if action not in {'resolve', 'close'} and normalized_category and not followup.get('followup_resolution_category'):
        followup['followup_resolution_category'] = normalized_category
        followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
    if action not in {'resolve', 'close'} and normalized_summary and not followup.get('followup_resolution_summary'):
        followup['followup_resolution_summary'] = normalized_summary

    manager = ArtifactManager(resolved_task_dir)
    _sync_followup_backfill(task_dir=resolved_task_dir, observation=observation, followup=followup, manager=manager)
    followup['generated_at'] = at
    manager.write_json('post_execution_observation.json', observation)
    manager.write_json(followup_path.name, followup)
    manager.write_json('observation_history_aggregate.json', _build_history_aggregate(task_dir=resolved_task_dir, current=observation))
    manager.append_log('post_execution_observation_runtime.log', json.dumps({
        'time': at,
        'task_id': resolved_task_dir.name,
        'target': target,
        'run_id': followup.get('run_id'),
        'action': action,
        'from_state': current_state,
        'to_state': next_state,
        'acted_by': acted_by,
        'assignee': followup.get('followup_assignee'),
        'resolution_category': followup.get('followup_resolution_category'),
        'note': note,
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    return followup


def backfill_followup_protocol(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, updated_by: str = 'system_backfill', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    observation = _load_json(artifacts_dir / 'post_execution_observation.json')
    followup_path = artifacts_dir / f'{target}_observation_followup_protocol.json'
    followup = _load_json(followup_path)
    result = {
        'task_id': resolved_task_dir.name,
        'target': target,
        'checked': False,
        'changed': False,
        'skipped': False,
        'reason': '',
        'manual_classification_required': False,
        'repaired_fields': [],
        'resolution_category': None,
        'closure_audit_present': False,
    }
    if not observation or not followup:
        result['skipped'] = True
        result['reason'] = 'missing_observation_or_followup_artifact'
        return result
    if observation.get('execution_target') != TARGET_CONFIG[target]['label']:
        result['skipped'] = True
        result['reason'] = 'target_mismatch'
        return result

    result['checked'] = True
    manager = ArtifactManager(resolved_task_dir)
    state = _normalize_followup_state(followup.get('followup_item_state'), requires_manual_followup=bool(followup.get('requires_manual_followup')))
    normalized_category = _normalize_resolution_category(followup.get('followup_resolution_category'))
    closure_audit = followup.get('followup_closure_audit') if isinstance(followup.get('followup_closure_audit'), dict) else None
    needs_category = bool(followup.get('requires_manual_followup')) and state in FOLLOWUP_TERMINAL_STATES and not normalized_category
    needs_closure_audit = bool(followup.get('requires_manual_followup')) and state == 'closed' and not closure_audit
    inferred_category = None
    inference_basis = 'existing'
    if needs_category:
        inferred_category, inference_basis = _infer_resolution_category(target=target, observation=observation, followup=followup)
        if inferred_category:
            normalized_category = inferred_category
            followup['followup_resolution_category'] = normalized_category
            followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
            if not str(followup.get('followup_resolution_summary') or '').strip():
                followup['followup_resolution_summary'] = followup.get('followup_resolution_note') or followup.get('followup_closure_note') or observation.get('failure_reason') or observation.get('completion_note') or ''
            result['repaired_fields'].append('followup_resolution_category')
            result['changed'] = True
    if needs_closure_audit and normalized_category:
        followup['followup_closure_audit'] = _build_closure_audit_payload(
            followup=followup,
            observation=observation,
            category=normalized_category,
            closed_at=followup.get('followup_closed_at') or observation.get('closed_at'),
            closed_by=followup.get('followup_last_actor') or observation.get('closed_by') or updated_by,
        )
        result['repaired_fields'].append('followup_closure_audit')
        result['changed'] = True
    manual_required = bool(followup.get('requires_manual_followup')) and state in FOLLOWUP_TERMINAL_STATES and not normalized_category
    followup['followup_backfill'] = {
        'checked_at': _now(),
        'checked_by': updated_by,
        'followup_state': state,
        'was_missing_resolution_category': needs_category,
        'was_missing_closure_audit': needs_closure_audit,
        'repaired_fields': result['repaired_fields'],
        'inferred_resolution_category': inferred_category,
        'inference_basis': inference_basis,
        'manual_classification_required': manual_required,
    }
    result['manual_classification_required'] = manual_required
    result['resolution_category'] = normalized_category
    result['closure_audit_present'] = isinstance(followup.get('followup_closure_audit'), dict)
    _sync_followup_backfill(task_dir=resolved_task_dir, observation=observation, followup=followup, manager=manager)
    manager.write_json('post_execution_observation.json', observation)
    manager.write_json(followup_path.name, followup)
    manager.write_json('observation_history_aggregate.json', _build_history_aggregate(task_dir=resolved_task_dir, current=observation))
    if result['changed'] or manual_required:
        manager.append_log('post_execution_observation_runtime.log', json.dumps({
            'time': _now(),
            'task_id': resolved_task_dir.name,
            'target': target,
            'action': 'followup_backfill',
            'updated_by': updated_by,
            'repaired_fields': result['repaired_fields'],
            'manual_classification_required': manual_required,
            'resolution_category': normalized_category,
            'inference_basis': inference_basis,
        }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    return result


def backfill_all_followups(*, jobs_root: str | Path = JOBS_ROOT, updated_by: str = 'system_backfill', limit: int = 0) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    items: list[dict[str, Any]] = []
    changed_count = 0
    manual_required_count = 0
    repaired_category_count = 0
    repaired_closure_audit_count = 0
    checked_count = 0
    for task_dir in sorted([path for path in jobs_root.iterdir() if path.is_dir()]):
        for target in sorted(TARGET_CONFIG.keys()):
            followup_path = task_dir / 'artifacts' / f'{target}_observation_followup_protocol.json'
            if not followup_path.exists():
                continue
            item = backfill_followup_protocol(task_dir=task_dir, target=target, updated_by=updated_by)
            items.append(item)
            if item.get('checked'):
                checked_count += 1
            if item.get('changed'):
                changed_count += 1
            if item.get('manual_classification_required'):
                manual_required_count += 1
            repaired = set(item.get('repaired_fields') or [])
            if 'followup_resolution_category' in repaired:
                repaired_category_count += 1
            if 'followup_closure_audit' in repaired:
                repaired_closure_audit_count += 1
            if limit and checked_count >= limit:
                break
        if limit and checked_count >= limit:
            break
    return {
        'jobs_scanned': len([path for path in jobs_root.iterdir() if path.is_dir()]) if jobs_root.exists() else 0,
        'followups_checked': checked_count,
        'changed_count': changed_count,
        'manual_classification_required_count': manual_required_count,
        'repaired_resolution_category_count': repaired_category_count,
        'repaired_closure_audit_count': repaired_closure_audit_count,
        'items': items,
        'generated_at': _now(),
    }


def open_observation_window(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, observed_by: str = 'system', note: str = '', jobs_root: str | Path = JOBS_ROOT, sla_seconds: int = DEFAULT_SLA_SECONDS, overdue_grace_seconds: int = DEFAULT_OVERDUE_GRACE_SECONDS, timeout_grace_seconds: int = DEFAULT_TIMEOUT_GRACE_SECONDS) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    registration = _load_json(artifacts_dir / TARGET_CONFIG[target]['registration_artifact'])
    if not registration:
        raise FileNotFoundError(f"missing required artifact: {TARGET_CONFIG[target]['registration_artifact']}")
    _ensure_registered_state(target, registration)

    batch = ensure_execution_batch(resolved_task_dir)
    run_context = get_execution_run_context(resolved_task_dir, target)
    validate_run_context(
        expected=run_context,
        candidate={'batch_id': registration.get('batch_id'), 'run_id': registration.get('run_id')},
        label=f'{target} registration',
    )

    existing = _load_json(artifacts_dir / 'post_execution_observation.json')
    history = list(existing.get('history', []) or [])
    if existing.get('opened_at') and existing.get('observation_state'):
        history.append(_history_entry(existing))

    opened_at = datetime.now().astimezone()
    deadline_at = opened_at + timedelta(seconds=max(0, int(sla_seconds or 0)))
    overdue_at = deadline_at + timedelta(seconds=max(0, int(overdue_grace_seconds or 0)))
    timeout_at = deadline_at + timedelta(seconds=max(0, int(timeout_grace_seconds or 0)))

    payload = {
        'task_id': resolved_task_dir.name,
        'record_type': 'post_execution_observation',
        'batch_id': batch['batch_id'],
        'run_id': run_context['run_id'],
        'execution_target': TARGET_CONFIG[target]['label'],
        'observation_state': 'observing',
        'observation_window_active': True,
        'observation_completed': False,
        'observation_failed': False,
        'observation_timed_out': False,
        'opened_at': _iso(opened_at),
        'opened_by': observed_by,
        'closed_at': None,
        'closed_by': None,
        'sla_seconds': int(sla_seconds),
        'overdue_grace_seconds': int(overdue_grace_seconds),
        'timeout_grace_seconds': int(timeout_grace_seconds),
        'deadline_at': _iso(deadline_at),
        'overdue_at': _iso(overdue_at),
        'timeout_at': _iso(timeout_at),
        'sla_state': 'within_sla',
        'is_overdue': False,
        'is_timed_out': False,
        'registration_state': registration.get('record_state'),
        'registration_recorded_at': registration.get('executed_at'),
        'registration_recorded_by': registration.get('executed_by'),
        'summary_artifact': (cfg := TARGET_CONFIG[target])['summary_artifact'],
        'audit_artifact': cfg['audit_artifact'],
        'followup_artifact': f"{target}_observation_followup_protocol.json",
        'history_artifact': 'observation_history_aggregate.json',
        'observation_summary_visible': False,
        'observation_signal_count': 0,
        'observation_drift_count': 0,
        'observation_mismatch_count': 0,
        'observation_anomaly_count': 0,
        'requires_manual_followup': False,
        'manual_followup_reason': [],
        'completion_note': '',
        'failure_reason': '',
        'history': history,
        'note': note or 'Post-execution observation window opened after manual registration. This tracks post-registration observation only and does not perform release/rollback automatically.',
        'generated_at': _now(),
    }
    payload.update(_compute_sla_fields(payload, now=opened_at))
    manager = ArtifactManager(resolved_task_dir)
    manager.write_json('post_execution_observation.json', payload)
    manager.write_json('observation_history_aggregate.json', _build_history_aggregate(task_dir=resolved_task_dir, current=payload))
    manager.append_log('post_execution_observation_runtime.log', json.dumps({
        'time': _now(),
        'task_id': resolved_task_dir.name,
        'target': target,
        'batch_id': payload['batch_id'],
        'run_id': payload['run_id'],
        'observation_state': payload['observation_state'],
        'sla_state': payload['sla_state'],
        'deadline_at': payload['deadline_at'],
        'timeout_at': payload['timeout_at'],
        'opened_by': observed_by,
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    return payload


def _finalize_observation_window(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, finalized_by: str, final_state: str, note: str = '', drift_findings: list[str] | None = None, mismatch_findings: list[str] | None = None, anomaly_findings: list[str] | None = None, signal_count: int = 0, jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    current = _load_json(artifacts_dir / 'post_execution_observation.json')
    if not current:
        raise FileNotFoundError('missing required artifact: post_execution_observation.json')
    if current.get('execution_target') != TARGET_CONFIG[target]['label']:
        raise ValueError(f'active observation target mismatch: expected {TARGET_CONFIG[target]["label"]}, got {current.get("execution_target")}')
    if current.get('observation_state') != 'observing':
        raise ValueError('observation window is not currently active')

    registration = _load_json(artifacts_dir / TARGET_CONFIG[target]['registration_artifact'])
    if not registration:
        raise FileNotFoundError(f"missing required artifact: {TARGET_CONFIG[target]['registration_artifact']}")
    _ensure_registered_state(target, registration)
    validate_run_context(
        expected={'batch_id': current.get('batch_id'), 'run_id': current.get('run_id')},
        candidate={'batch_id': registration.get('batch_id'), 'run_id': registration.get('run_id')},
        label=f'{target} observation finalize registration',
    )

    drift = _normalize_list(drift_findings)
    mismatch = _normalize_list(mismatch_findings)
    anomaly = _normalize_list(anomaly_findings)
    total_signals = max(signal_count, len(drift) + len(mismatch) + len(anomaly))

    current.update({
        'observation_state': final_state,
        'observation_window_active': False,
        'observation_completed': final_state == 'observation_completed',
        'observation_failed': final_state == 'observation_failed',
        'observation_timed_out': final_state == 'observation_timed_out',
        'closed_at': _now(),
        'closed_by': finalized_by,
        'completion_note': note if final_state == 'observation_completed' else '',
        'failure_reason': note if final_state in {'observation_failed', 'observation_timed_out'} else '',
        'observation_summary_visible': True,
        'observation_signal_count': total_signals,
        'observation_drift_count': len(drift),
        'observation_mismatch_count': len(mismatch),
        'observation_anomaly_count': len(anomaly),
        'generated_at': _now(),
    })
    current.update(_compute_sla_fields(current))

    summary, audit, followup, history_aggregate = _build_observation_artifacts(
        task_dir=resolved_task_dir,
        target=target,
        observation=current,
        finalized_by=finalized_by,
        final_state=final_state,
        note=note,
        signal_count=total_signals,
        drift_findings=drift,
        mismatch_findings=mismatch,
        anomaly_findings=anomaly,
    )
    current['requires_manual_followup'] = followup.get('requires_manual_followup', False)
    current['manual_followup_reason'] = followup.get('manual_followup_reason', [])

    manager = ArtifactManager(resolved_task_dir)
    _sync_followup_backfill(task_dir=resolved_task_dir, observation=current, followup=followup, manager=manager)
    manager.write_json('post_execution_observation.json', current)
    manager.write_json(TARGET_CONFIG[target]['summary_artifact'], summary)
    manager.write_json(TARGET_CONFIG[target]['audit_artifact'], audit)
    manager.write_json(current['followup_artifact'], followup)
    manager.write_json('observation_history_aggregate.json', history_aggregate)
    manager.append_log('post_execution_observation_runtime.log', json.dumps({
        'time': _now(),
        'task_id': resolved_task_dir.name,
        'target': target,
        'batch_id': current.get('batch_id'),
        'run_id': current.get('run_id'),
        'observation_state': current.get('observation_state'),
        'sla_state': current.get('sla_state'),
        'finalized_by': finalized_by,
        'requires_manual_followup': current.get('requires_manual_followup'),
        'anomaly_count': current.get('observation_anomaly_count'),
        'mismatch_count': current.get('observation_mismatch_count'),
        'drift_count': current.get('observation_drift_count'),
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    return current


def refresh_observation_window(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str | None = None, refreshed_by: str = 'system', note: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    current = _load_json(artifacts_dir / 'post_execution_observation.json')
    if not current:
        raise FileNotFoundError('missing required artifact: post_execution_observation.json')
    if target and current.get('execution_target') != TARGET_CONFIG[target]['label']:
        raise ValueError('observation target mismatch during refresh')

    current.update(_compute_sla_fields(current))
    observation_target = current.get('execution_target')
    normalized_target = 'release' if observation_target == TARGET_CONFIG['release']['label'] else 'rollback' if observation_target == TARGET_CONFIG['rollback']['label'] else None
    if current.get('observation_state') == 'observing' and current.get('is_timed_out') and normalized_target:
        return _finalize_observation_window(
            task_dir=resolved_task_dir,
            target=normalized_target,
            finalized_by=refreshed_by,
            final_state='observation_timed_out',
            note=note or 'Observation timeout reached before manual completion/failure confirmation.',
            anomaly_findings=['observation_timeout'],
            signal_count=current.get('observation_signal_count') or 0,
        )

    manager = ArtifactManager(resolved_task_dir)
    manager.write_json('post_execution_observation.json', current)
    manager.write_json('observation_history_aggregate.json', _build_history_aggregate(task_dir=resolved_task_dir, current=current))
    manager.append_log('post_execution_observation_runtime.log', json.dumps({
        'time': _now(),
        'task_id': resolved_task_dir.name,
        'execution_target': current.get('execution_target'),
        'run_id': current.get('run_id'),
        'observation_state': current.get('observation_state'),
        'sla_state': current.get('sla_state'),
        'refreshed_by': refreshed_by,
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    return current


def complete_observation_window(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, completed_by: str = 'human', note: str = '', drift_findings: list[str] | None = None, mismatch_findings: list[str] | None = None, anomaly_findings: list[str] | None = None, signal_count: int = 0, jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    return _finalize_observation_window(
        task_dir=task_dir,
        task_id=task_id,
        target=target,
        finalized_by=completed_by,
        final_state='observation_completed',
        note=note,
        drift_findings=drift_findings,
        mismatch_findings=mismatch_findings,
        anomaly_findings=anomaly_findings,
        signal_count=signal_count,
        jobs_root=jobs_root,
    )


def fail_observation_window(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, failed_by: str = 'human', note: str = '', drift_findings: list[str] | None = None, mismatch_findings: list[str] | None = None, anomaly_findings: list[str] | None = None, signal_count: int = 0, jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    return _finalize_observation_window(
        task_dir=task_dir,
        task_id=task_id,
        target=target,
        finalized_by=failed_by,
        final_state='observation_failed',
        note=note,
        drift_findings=drift_findings,
        mismatch_findings=mismatch_findings,
        anomaly_findings=anomaly_findings,
        signal_count=signal_count,
        jobs_root=jobs_root,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    open_p = sub.add_parser('open')
    open_p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
    open_p.add_argument('--task-dir', default='')
    open_p.add_argument('--task-id', default='')
    open_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    open_p.add_argument('--observed-by', default='system')
    open_p.add_argument('--note', default='')
    open_p.add_argument('--sla-seconds', type=int, default=DEFAULT_SLA_SECONDS)
    open_p.add_argument('--overdue-grace-seconds', type=int, default=DEFAULT_OVERDUE_GRACE_SECONDS)
    open_p.add_argument('--timeout-grace-seconds', type=int, default=DEFAULT_TIMEOUT_GRACE_SECONDS)

    refresh_p = sub.add_parser('refresh')
    refresh_p.add_argument('--target', choices=sorted(TARGET_CONFIG.keys()))
    refresh_p.add_argument('--task-dir', default='')
    refresh_p.add_argument('--task-id', default='')
    refresh_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    refresh_p.add_argument('--refreshed-by', default='system')
    refresh_p.add_argument('--note', default='')

    def _add_finalize_args(p: argparse.ArgumentParser, actor_flag: str) -> None:
        p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
        p.add_argument('--task-dir', default='')
        p.add_argument('--task-id', default='')
        p.add_argument('--jobs-root', default=str(JOBS_ROOT))
        p.add_argument(actor_flag, default='human')
        p.add_argument('--note', default='')
        p.add_argument('--signal-count', type=int, default=0)
        p.add_argument('--counts', default='')
        p.add_argument('--drift', action='append', default=[])
        p.add_argument('--mismatch', action='append', default=[])
        p.add_argument('--anomaly', action='append', default=[])

    complete_p = sub.add_parser('complete')
    _add_finalize_args(complete_p, '--completed-by')
    fail_p = sub.add_parser('fail')
    _add_finalize_args(fail_p, '--failed-by')
    followup_p = sub.add_parser('followup-action')
    followup_p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
    followup_p.add_argument('--task-dir', default='')
    followup_p.add_argument('--task-id', default='')
    followup_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    followup_p.add_argument('--action-name', required=True, choices=sorted(FOLLOWUP_ACTION_TO_STATE.keys()))
    followup_p.add_argument('--acted-by', default='human')
    followup_p.add_argument('--assignee', default='')
    followup_p.add_argument('--resolution-category', default='')
    followup_p.add_argument('--resolution-summary', default='')
    followup_p.add_argument('--note', default='')

    backfill_p = sub.add_parser('backfill-followup')
    backfill_p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
    backfill_p.add_argument('--task-dir', default='')
    backfill_p.add_argument('--task-id', default='')
    backfill_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    backfill_p.add_argument('--updated-by', default='system_backfill')

    backfill_all_p = sub.add_parser('backfill-all-followups')
    backfill_all_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    backfill_all_p.add_argument('--updated-by', default='system_backfill')
    backfill_all_p.add_argument('--limit', type=int, default=0)

    args = parser.parse_args()
    if args.action == 'open':
        result = open_observation_window(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, observed_by=args.observed_by, note=args.note, jobs_root=args.jobs_root, sla_seconds=args.sla_seconds, overdue_grace_seconds=args.overdue_grace_seconds, timeout_grace_seconds=args.timeout_grace_seconds)
    elif args.action == 'refresh':
        result = refresh_observation_window(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, refreshed_by=args.refreshed_by, note=args.note, jobs_root=args.jobs_root)
    elif args.action == 'followup-action':
        result = apply_followup_action(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, action=args.action_name, acted_by=args.acted_by, note=args.note, assignee=args.assignee, resolution_category=args.resolution_category, resolution_summary=args.resolution_summary, jobs_root=args.jobs_root)
    elif args.action == 'backfill-followup':
        result = backfill_followup_protocol(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, updated_by=args.updated_by, jobs_root=args.jobs_root)
    elif args.action == 'backfill-all-followups':
        result = backfill_all_followups(jobs_root=args.jobs_root, updated_by=args.updated_by, limit=args.limit)
    else:
        parsed = _parse_counts(args.counts)
        signal_count = max(args.signal_count, parsed['signal_count'])
        drift = list(args.drift or []) + ([f"count={parsed['drift_count']}"] if parsed['drift_count'] and not args.drift else [])
        mismatch = list(args.mismatch or []) + ([f"count={parsed['mismatch_count']}"] if parsed['mismatch_count'] and not args.mismatch else [])
        anomaly = list(args.anomaly or []) + ([f"count={parsed['anomaly_count']}"] if parsed['anomaly_count'] and not args.anomaly else [])
        if args.action == 'complete':
            result = complete_observation_window(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, completed_by=args.completed_by, note=args.note, drift_findings=drift, mismatch_findings=mismatch, anomaly_findings=anomaly, signal_count=signal_count, jobs_root=args.jobs_root)
        else:
            result = fail_observation_window(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, failed_by=args.failed_by, note=args.note, drift_findings=drift, mismatch_findings=mismatch, anomaly_findings=anomaly, signal_count=signal_count, jobs_root=args.jobs_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
