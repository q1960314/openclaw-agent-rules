#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal periodic runtime scheduler for worker ecosystem health/recovery views.

Current scope:
- run one cycle on demand
- optional continuous loop with sleep interval
- export health / recovery / lifecycle dashboards
- optionally heal stale jobs and create retry tasks when policy allows
- persist latest cycle summary for ops visibility

This is intentionally a lightweight scheduler skeleton, not a full daemon/supervisor.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from backfill_runtime import backfill_jobs
from ecosystem_stage_card import GAP_ID_ZH, OFFICIAL_RELEASE_FOCUS_LABEL_ZH, OFFICIAL_RELEASE_STATE_ZH, build_stage_card, write_stage_card_markdown
from heartbeat_monitor import dashboard, heal_jobs, write_dashboard_markdown
from recovery_runtime import jobs_recovery_dashboard, write_recovery_markdown
from task_lifecycle import lifecycle_dashboard, write_lifecycle_markdown
from post_execution_observation_runtime import backfill_all_followups, refresh_observation_window
from rule_proposal_runtime import build_rule_proposal_review, export_rulebook_artifacts, materialize_rule_sink, write_rule_proposal_review_markdown


ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
LOOPS_ROOT = ROOT / 'traces' / 'loops'
REPORT_ROOT = ROOT / 'reports' / 'worker-runtime'
STATE_ROOT = REPORT_ROOT / 'state'
CYCLES_ROOT = REPORT_ROOT / 'cycles'

RECENT_EXPERT_CANDIDATES = {
    'strategy-expert': 'strategy_candidate.json',
    'parameter-evolver': 'parameter_candidate.json',
    'factor-miner': 'factor_candidate.json',
}


def _now() -> datetime:
    return datetime.now().astimezone()


def _append_event(event_type: str, **payload: Any) -> dict[str, Any]:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    item = {
        'time': _now().isoformat(),
        'event_type': event_type,
        **payload,
    }
    events_path = STATE_ROOT / 'events.jsonl'
    with events_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + '\n')
    return item


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def _render_report_value(value: Any) -> Any:
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, list):
        if not value:
            return '无'
        return '；'.join(str(item) for item in value)
    if isinstance(value, dict):
        if not value:
            return '无'
        return '；'.join(f"{k}={v}" for k, v in value.items())
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _top_counts(counter: dict[str, int] | Counter[str], *, limit: int = 5) -> dict[str, int]:
    normalized = {str(key): int(value or 0) for key, value in dict(counter or {}).items() if int(value or 0) > 0}
    ordered_keys = sorted(normalized, key=lambda key: (-normalized[key], key))[:limit]
    return {key: normalized[key] for key in ordered_keys}


def _extract_theme_tokens(*, execution_target: str | None, resolution_category: str | None, resolution_taxonomy: str | None, closure_insights: list[str] | None, resolution_summary: str, closure_note: str, handoff_count: int, manual_classification_required: bool) -> list[str]:
    tokens: list[str] = []
    target_key = 'rollback' if execution_target == 'rollback' else 'release'
    if resolution_category:
        tokens.append(f'category:{resolution_category}')
    if resolution_taxonomy:
        tokens.append(f'taxonomy:{resolution_taxonomy}')
    tokens.append(f'target:{target_key}')
    if resolution_taxonomy:
        tokens.append(f'target:{target_key}|taxonomy:{resolution_taxonomy}')
    if resolution_category:
        tokens.append(f'target:{target_key}|category:{resolution_category}')
    if handoff_count > 0:
        tokens.append('pattern:handoff_involved')
    if manual_classification_required:
        tokens.append('pattern:manual_classification_required')

    merged_text = ' '.join([
        str(resolution_summary or '').lower(),
        str(closure_note or '').lower(),
        ' '.join(str(item).lower() for item in list(closure_insights or [])),
    ])
    keyword_map = {
        'theme:false_positive_noise': ['false positive', '误报', 'duplicate', 'noise', '噪声', '重复'],
        'theme:config_alignment': ['config', 'configuration', '配置'],
        'theme:code_fix': ['code fix', 'bug fix', 'patch', '修复', '代码'],
        'theme:rollback_validation': ['rollback', '回滚'],
        'theme:risk_acceptance': ['accepted risk', 'risk accepted', '接受风险'],
        'theme:manual_ops': ['manual intervention', '人工', 'manual_review', 'manual review'],
        'theme:monitoring_signal': ['monitoring', '监控', 'signal', '告警', 'anomaly', '异常', 'drift', '漂移', 'mismatch'],
    }
    for token, keywords in keyword_map.items():
        if any(keyword in merged_text for keyword in keywords):
            tokens.append(token)

    for insight in list(closure_insights or []):
        insight_text = str(insight or '').strip().lower()
        if not insight_text:
            continue
        if insight_text.startswith('resolved_as:'):
            tokens.append(f"theme:{insight_text.replace('resolved_as:', 'resolved_as|', 1)}")
        elif insight_text.startswith('taxonomy:'):
            tokens.append(f"theme:{insight_text.replace('taxonomy:', 'taxonomy|', 1)}")
        elif insight_text.startswith('manual_classification_state:'):
            tokens.append(f"pattern:{insight_text}")
        elif insight_text.startswith('handoff_count:'):
            tokens.append('pattern:handoff_count_observed')
        elif insight_text.startswith('closure_by:'):
            tokens.append(f"pattern:{insight_text}")
        elif insight_text == 'needs_manual_classification':
            tokens.append('pattern:manual_classification_required')
    return sorted({token for token in tokens if token})


def _build_pattern_key(item: dict[str, Any]) -> str:
    target = item.get('execution_target') or 'unknown'
    taxonomy = item.get('resolution_taxonomy') or 'unclassified'
    category = item.get('resolution_category') or 'unclassified'
    handoff = 'handoff' if int(item.get('handoff_count') or 0) > 0 else 'direct'
    manual = 'manual' if item.get('manual_classification_required') else 'classified'
    return f'{target}|{taxonomy}|{category}|{handoff}|{manual}'


def _candidate_label(prefix: str, name: str) -> str:
    return f'{prefix}:{name}'


def build_followup_resolution_review(observation_runtime: dict[str, Any]) -> dict[str, Any]:
    queue = (observation_runtime or {}).get('followup_queue') or {}
    all_items = list(queue.get('all_items', []) or [])
    manual_classification_required_count = int(queue.get('manual_classification_required_count', 0) or 0)
    backfilled_item_count = int(queue.get('backfilled_item_count', 0) or 0)
    target_resolution_counts = (queue.get('target_resolution_category_counts') or {})
    taxonomy_theme_counts: Counter[str] = Counter()
    knowledge_candidate_counts = {'task_local': 0, 'cycle_level': 0}
    closure_theme_counts: Counter[str] = Counter()
    top_closure_theme_counts: Counter[str] = Counter()
    pattern_digest_counts: Counter[str] = Counter()
    rule_candidate_counts: Counter[str] = Counter()
    pattern_candidate_counts: Counter[str] = Counter()
    release_theme_counts: Counter[str] = Counter()
    rollback_theme_counts: Counter[str] = Counter()
    manual_classification_items: list[dict[str, Any]] = []
    knowledge_candidate_items: list[dict[str, Any]] = []

    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        resolution_category = item.get('followup_resolution_category') or ('needs_manual_classification' if item.get('manual_classification_required') else 'unclassified')
        resolution_taxonomy = ((item.get('followup_resolution_taxonomy') or {}).get('taxonomy') if isinstance(item.get('followup_resolution_taxonomy'), dict) else None)
        closure_note = (item.get('followup_closure_audit') or {}).get('closure_note') if isinstance(item.get('followup_closure_audit'), dict) else ''
        closure_insight_list = list(item.get('closure_insights') or [])
        handoff_count = int(item.get('followup_handoff_count') or 0)
        knowledge_sink_candidate = bool(item.get('followup_resolution_category') or item.get('manual_classification_required') or resolution_category in {'needs_manual_classification', 'unclassified'})
        theme_tokens = _extract_theme_tokens(
            execution_target=item.get('execution_target'),
            resolution_category=resolution_category,
            resolution_taxonomy=resolution_taxonomy,
            closure_insights=closure_insight_list,
            resolution_summary=item.get('followup_resolution_summary') or '',
            closure_note=closure_note or '',
            handoff_count=handoff_count,
            manual_classification_required=bool(item.get('manual_classification_required')),
        )
        pattern_key = _build_pattern_key({
            'execution_target': item.get('execution_target'),
            'resolution_taxonomy': resolution_taxonomy,
            'resolution_category': resolution_category,
            'handoff_count': handoff_count,
            'manual_classification_required': bool(item.get('manual_classification_required')),
        })
        normalized = {
            'task_id': item.get('task_id'),
            'execution_target': item.get('execution_target'),
            'resolution_category': resolution_category,
            'resolution_taxonomy': resolution_taxonomy,
            'resolution_summary': item.get('followup_resolution_summary') or '',
            'closure_note': closure_note or '',
            'closure_insights': closure_insight_list,
            'extracted_themes': theme_tokens,
            'pattern_key': pattern_key,
            'handoff_count': handoff_count,
            'followup_item_state': item.get('followup_item_state'),
            'manual_classification_required': bool(item.get('manual_classification_required')),
            'manual_classification_state': item.get('manual_classification_state'),
            'manual_classification_workflow': item.get('manual_classification_workflow') or {},
            'knowledge_linkage': {
                'task_local_candidate': knowledge_sink_candidate,
                'cycle_level_candidate': knowledge_sink_candidate,
                'entered_review_digest': True,
                'source_artifact': item.get('resolution_review_artifact'),
            },
        }
        if resolution_taxonomy:
            taxonomy_theme_counts[resolution_taxonomy] += 1
        for theme in theme_tokens:
            closure_theme_counts[theme] += 1
            if theme.startswith('category:') or theme.startswith('taxonomy:') or theme.startswith('theme:'):
                top_closure_theme_counts[theme] += 1
            if theme.startswith('taxonomy:') or theme.startswith('theme:'):
                rule_candidate_counts[_candidate_label('rule', theme)] += 1
            if theme.startswith('pattern:'):
                pattern_candidate_counts[_candidate_label('pattern', theme.split(':', 1)[1])] += 1
            if item.get('execution_target') == 'rollback':
                rollback_theme_counts[theme] += 1
            else:
                release_theme_counts[theme] += 1
        pattern_digest_counts[pattern_key] += 1
        if knowledge_sink_candidate:
            knowledge_candidate_counts['task_local'] += 1
            knowledge_candidate_counts['cycle_level'] += 1
            knowledge_candidate_items.append(normalized)
        return normalized

    normalized_all_items = [_normalize_item(item) for item in all_items]
    normalized_closed_items = [item for item in normalized_all_items if item.get('followup_item_state') == 'closed']

    closure_insights = normalized_closed_items[:5]
    manual_classification_state_counts: dict[str, int] = {}
    manual_classification_state_items: list[dict[str, Any]] = []
    for item in normalized_all_items:
        manual_state = str(item.get('manual_classification_state') or '').strip().lower()
        tracked = bool(manual_state) or item.get('manual_classification_required') or item.get('resolution_category') in {'needs_manual_classification', 'unclassified'}
        if tracked:
            if not manual_state:
                manual_state = 'pending'
                item['manual_classification_state'] = manual_state
            manual_classification_state_counts[manual_state] = manual_classification_state_counts.get(manual_state, 0) + 1
            manual_classification_state_items.append(item)
        if item.get('manual_classification_required') or manual_state in {'pending', 'claimed', 'classified', 'confirmed'} or item.get('resolution_category') in {'needs_manual_classification', 'unclassified'}:
            manual_classification_items.append(item)

    contrasted_theme_counts: dict[str, dict[str, int]] = {}
    for theme in sorted(set(release_theme_counts) | set(rollback_theme_counts)):
        rel = int(release_theme_counts.get(theme, 0) or 0)
        rb = int(rollback_theme_counts.get(theme, 0) or 0)
        if rel <= 0 and rb <= 0:
            continue
        contrasted_theme_counts[theme] = {'release': rel, 'rollback': rb, 'delta': rel - rb}
    theme_contrast = {
        'top_release_themes': _top_counts(release_theme_counts),
        'top_rollback_themes': _top_counts(rollback_theme_counts),
        'largest_deltas': {
            key: contrasted_theme_counts[key]
            for key in sorted(
                contrasted_theme_counts,
                key=lambda key: (-abs(int(contrasted_theme_counts[key]['delta'])), key),
            )[:5]
        },
    }

    manual_classification_backlog = {
        'count': len(manual_classification_items),
        'unresolved_count': len([item for item in manual_classification_items if item.get('manual_classification_state') in {'pending', 'claimed', 'classified', 'confirmed'} or item.get('followup_item_state') in {'open', 'acknowledged', 'reopened', 'in_progress'}]),
        'closed_without_classification_count': len([item for item in manual_classification_items if item.get('followup_item_state') == 'closed' and not item.get('resolution_category')]),
        'state_counts': manual_classification_state_counts,
        'items': manual_classification_items[:10],
        'unresolved_items': [item for item in manual_classification_items if item.get('manual_classification_state') in {'pending', 'claimed', 'classified', 'confirmed'} or item.get('followup_item_state') in {'open', 'acknowledged', 'reopened', 'in_progress'}][:10],
        'recently_completed_items': [item for item in manual_classification_state_items if item.get('manual_classification_state') == 'closed'][:10],
    }

    top_rule_candidates = _top_counts(rule_candidate_counts)
    top_pattern_candidates = _top_counts(pattern_candidate_counts)
    top_closure_themes = _top_counts(top_closure_theme_counts)
    pattern_digest_top = _top_counts(pattern_digest_counts)

    digest_markdown_lines = [
        '# Closure Theme Pattern Digest',
        '',
        f"- top_closure_themes: {_render_report_value(top_closure_themes)}",
        f"- pattern_digest_top: {_render_report_value(pattern_digest_top)}",
        f"- top_rule_candidates: {_render_report_value(top_rule_candidates)}",
        f"- top_pattern_candidates: {_render_report_value(top_pattern_candidates)}",
        f"- top_release_themes: {_render_report_value(theme_contrast['top_release_themes'])}",
        f"- top_rollback_themes: {_render_report_value(theme_contrast['top_rollback_themes'])}",
        '',
    ]

    return {
        'generated_at': _now().isoformat(),
        'resolution_category_counts': observation_runtime.get('followup_resolution_category_counts', {}),
        'target_resolution_category_counts': target_resolution_counts,
        'manual_classification_required_count': max(manual_classification_required_count, len(manual_classification_items)),
        'manual_classification_backlog': manual_classification_backlog,
        'backfilled_item_count': backfilled_item_count,
        'queue_count': queue.get('queue_count', 0),
        'closed_count': observation_runtime.get('followup_closed_count', 0),
        'resolved_count': observation_runtime.get('followup_resolved_count', 0),
        'recent_closure_insights': closure_insights,
        'recent_closure_knowledge_themes': dict(_top_counts(closure_theme_counts, limit=12)),
        'top_closure_themes': top_closure_themes,
        'resolution_taxonomy_theme_counts': dict(_top_counts(taxonomy_theme_counts, limit=12)),
        'pattern_digest_counts': dict(_top_counts(pattern_digest_counts, limit=12)),
        'pattern_digest_top': pattern_digest_top,
        'pattern_digest_available': bool(pattern_digest_top),
        'theme_contrast': theme_contrast,
        'rule_candidate_counts': dict(_top_counts(rule_candidate_counts, limit=12)),
        'pattern_candidate_counts': dict(_top_counts(pattern_candidate_counts, limit=12)),
        'top_rule_candidates': top_rule_candidates,
        'top_pattern_candidates': top_pattern_candidates,
        'knowledge_candidate_counts': knowledge_candidate_counts,
        'knowledge_candidate_items': knowledge_candidate_items[:10],
        'digest_markdown': '\n'.join(digest_markdown_lines),
        'digest_available': bool(closure_insights or manual_classification_items or taxonomy_theme_counts or pattern_digest_top),
        'knowledge_sink_ready': bool(closure_insights or observation_runtime.get('followup_resolution_category_counts') or manual_classification_required_count or backfilled_item_count),
    }


def write_followup_resolution_review_markdown(payload: dict[str, Any], path: Path) -> Path:
    lines = [
        '# Follow-up Resolution Review',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- resolution_category_counts: {_render_report_value(payload.get('resolution_category_counts'))}",
        f"- target_resolution_category_counts: {_render_report_value(payload.get('target_resolution_category_counts'))}",
        f"- backfilled_item_count: {payload.get('backfilled_item_count')}",
        f"- manual_classification_required_count: {payload.get('manual_classification_required_count')}",
        f"- manual_classification_backlog: {_render_report_value(payload.get('manual_classification_backlog'))}",
        f"- resolution_taxonomy_theme_counts: {_render_report_value(payload.get('resolution_taxonomy_theme_counts'))}",
        f"- recent_closure_knowledge_themes: {_render_report_value(payload.get('recent_closure_knowledge_themes'))}",
        f"- top_closure_themes: {_render_report_value(payload.get('top_closure_themes'))}",
        f"- pattern_digest_available: {_render_report_value(payload.get('pattern_digest_available'))}",
        f"- pattern_digest_top: {_render_report_value(payload.get('pattern_digest_top'))}",
        f"- theme_contrast: {_render_report_value(payload.get('theme_contrast'))}",
        f"- top_rule_candidates: {_render_report_value(payload.get('top_rule_candidates'))}",
        f"- top_pattern_candidates: {_render_report_value(payload.get('top_pattern_candidates'))}",
        f"- digest_available: {_render_report_value(payload.get('digest_available'))}",
        f"- knowledge_candidate_counts: {_render_report_value(payload.get('knowledge_candidate_counts'))}",
        f"- knowledge_sink_ready: {_render_report_value(payload.get('knowledge_sink_ready'))}",
        '',
        '## recent_closure_insights',
    ]
    insights = list(payload.get('recent_closure_insights', []) or [])
    if not insights:
        lines.append('- none')
    else:
        for item in insights:
            lines.append(
                f"- {item.get('task_id')} | {item.get('execution_target')} | {item.get('resolution_category')} | taxonomy={item.get('resolution_taxonomy') or 'n/a'} | pattern={item.get('pattern_key') or 'n/a'} | themes={_render_report_value(item.get('extracted_themes'))} | summary={item.get('resolution_summary') or 'n/a'} | note={item.get('closure_note') or 'n/a'}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


OFFICIAL_RELEASE_FOCUS_LABEL_ZH = {
    'prereq_not_ready': '前置条件未满足',
    'awaiting_human_approval': '等待人工审批',
    'approved_but_blocked': '已审批但仍有阻塞',
    'execution_path_not_implemented': '执行路径未实现',
    'rejected_candidates_present': '已出现拒绝样本',
    'pipeline_state_unclear': '当前卡点仍不清晰',
}

OFFICIAL_RELEASE_STATE_ZH = {
    'candidate_not_ready': '候选结果尚未就绪',
    'awaiting_human_approval': '等待人工审批',
    'approved_but_blocked': '已审批但仍阻塞',
    'ready_but_execution_not_implemented': '已就绪但执行路径未实现',
    'rejected': '已拒绝',
}

OFFICIAL_RELEASE_BLOCKER_ZH = {
    'human_approval_not_recorded': '人工审批结果未记录',
    'official_release_rehearsal_not_ready': '正式发布预演未就绪',
    'pre_release_gate_not_ready': '发布前置门禁未就绪',
    'release_artifact_binding_not_ready': '发布产物绑定未就绪',
    'rollback_not_ready': '回滚准备未就绪',
    'human_approval_rejected': '人工审批已拒绝',
    'human_approval_invalid_state': '人工审批状态异常',
}


def _translate_count_keys(counts: dict[str, Any], mapping: dict[str, str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, value in (counts or {}).items():
        normalized = int(value or 0)
        if normalized <= 0:
            continue
        result[mapping.get(str(key), str(key))] = normalized
    return result


def _enrich_open_gap_summary_with_stage_focus(open_gap_summary: dict[str, Any], stage_card: dict[str, Any]) -> dict[str, Any]:
    if not open_gap_summary:
        return {}
    enriched = json.loads(json.dumps(open_gap_summary, ensure_ascii=False))
    next_action = (stage_card or {}).get('next_action_card', {}) or {}
    focus_gap_id = ((stage_card or {}).get('signals', {}) or {}).get('recommended_focus_gap_id')
    if focus_gap_id != 'official_release_pipeline':
        return enriched

    focus_label = next_action.get('focus_label')
    dominant_state = next_action.get('dominant_state')
    blocker_counts = next_action.get('blocker_counts', {}) or {}
    state_counts = next_action.get('state_counts', {}) or {}
    focus_title = next_action.get('title')
    focus_summary = (
        f"当前聚焦：{focus_title or '未命名焦点'}；"
        f"卡点类型：{OFFICIAL_RELEASE_FOCUS_LABEL_ZH.get(focus_label, focus_label or '未知')}；"
        f"主导状态：{OFFICIAL_RELEASE_STATE_ZH.get(dominant_state, dominant_state or '未知')}。"
    )

    for item in enriched.get('items', []) or []:
        if item.get('gap_id') != 'official_release_pipeline':
            continue
        item['current_focus_title'] = focus_title
        item['current_focus_label'] = focus_label
        item['current_focus_label_zh'] = OFFICIAL_RELEASE_FOCUS_LABEL_ZH.get(focus_label, focus_label)
        item['dominant_state'] = dominant_state
        item['dominant_state_zh'] = OFFICIAL_RELEASE_STATE_ZH.get(dominant_state, dominant_state)
        item['blocker_counts'] = blocker_counts
        item['blocker_counts_zh'] = _translate_count_keys(blocker_counts, OFFICIAL_RELEASE_BLOCKER_ZH)
        item['state_counts'] = state_counts
        item['state_counts_zh'] = _translate_count_keys(state_counts, OFFICIAL_RELEASE_STATE_ZH)
        item['current_focus_summary'] = focus_summary
        item['rationale'] = (item.get('rationale') or '') + ' ' + focus_summary
        if next_action.get('why_now'):
            item['why_now_detailed'] = next_action.get('why_now')
        if next_action.get('recommended_actions'):
            item['recommended_actions_detailed'] = list(next_action.get('recommended_actions') or [])
        break
    return enriched


def summarize_adaptive_loops(loops_root: str | Path = LOOPS_ROOT) -> dict[str, Any]:
    loops_root = Path(loops_root)
    role_counts: dict[str, int] = {}
    source_role_counts: dict[str, int] = {}
    decision_basis_counts: dict[str, int] = {}
    total_loops = 0
    loops_with_adaptive_trace = 0
    total_adaptive_decisions = 0
    latest_loop_id = None
    latest_final_status = None
    latest_generated_at = None

    if not loops_root.exists():
        return {
            'loop_count': 0,
            'loops_with_adaptive_trace': 0,
            'total_adaptive_decisions': 0,
            'next_role_counts': {},
            'handoff_source_role_counts': {},
            'decision_basis_counts': {},
            'dominant_next_role': None,
            'dominant_handoff_source_role': None,
            'dominant_decision_basis': None,
            'latest_loop_id': None,
            'latest_final_status': None,
            'latest_generated_at': None,
        }

    for report_path in sorted(loops_root.glob('*/loop_report.json')):
        payload = _load_json(report_path)
        if not payload:
            continue
        total_loops += 1
        adaptive_trace = payload.get('adaptive_trace', []) or []
        if adaptive_trace:
            loops_with_adaptive_trace += 1
        total_adaptive_decisions += len(adaptive_trace)
        latest_loop_id = payload.get('loop_id', latest_loop_id)
        latest_final_status = payload.get('final_status', latest_final_status)
        latest_generated_at = payload.get('generated_at', latest_generated_at)
        for item in adaptive_trace:
            next_role = item.get('next_role')
            if next_role:
                role_counts[next_role] = role_counts.get(next_role, 0) + 1
            source_role = item.get('handoff_source_role')
            if source_role:
                source_role_counts[source_role] = source_role_counts.get(source_role, 0) + 1
            basis = item.get('decision_basis')
            if basis:
                decision_basis_counts[basis] = decision_basis_counts.get(basis, 0) + 1

    dominant_next_role = max(role_counts, key=role_counts.get) if role_counts else None
    dominant_handoff_source_role = max(source_role_counts, key=source_role_counts.get) if source_role_counts else None
    dominant_decision_basis = max(decision_basis_counts, key=decision_basis_counts.get) if decision_basis_counts else None
    return {
        'loop_count': total_loops,
        'loops_with_adaptive_trace': loops_with_adaptive_trace,
        'total_adaptive_decisions': total_adaptive_decisions,
        'next_role_counts': role_counts,
        'handoff_source_role_counts': source_role_counts,
        'decision_basis_counts': decision_basis_counts,
        'dominant_next_role': dominant_next_role,
        'dominant_handoff_source_role': dominant_handoff_source_role,
        'dominant_decision_basis': dominant_decision_basis,
        'latest_loop_id': latest_loop_id,
        'latest_final_status': latest_final_status,
        'latest_generated_at': latest_generated_at,
    }


def summarize_recent_ecosystem_learning(jobs_root: str | Path = JOBS_ROOT, adaptive_loop_summary: dict[str, Any] | None = None, limit: int = 12) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    role_counts: dict[str, int] = {}
    reusable_signal_counts: dict[str, int] = {}
    latest_examples: list[dict[str, Any]] = []

    if not jobs_root.exists():
        return {
            'recent_task_count': 0,
            'expert_role_counts': {},
            'reusable_signal_counts': {},
            'dominant_expert_role': None,
            'recent_examples': [],
            'adaptive_loop_bridge': adaptive_loop_summary or {},
        }

    candidates: list[tuple[float, Path]] = []
    for task_dir in jobs_root.iterdir():
        if not task_dir.is_dir() or task_dir.name.startswith('_'):
            continue
        task = _load_json(task_dir / 'task.json')
        role = task.get('role')
        candidate_name = RECENT_EXPERT_CANDIDATES.get(role)
        if not candidate_name:
            continue
        review = _load_json(task_dir / 'review.json')
        if review.get('decision') != 'passed':
            continue
        candidate_path = task_dir / 'artifacts' / candidate_name
        if not candidate_path.exists():
            continue
        candidates.append((candidate_path.stat().st_mtime, task_dir))

    for _, task_dir in sorted(candidates, key=lambda item: item[0], reverse=True)[:limit]:
        task = _load_json(task_dir / 'task.json')
        role = task.get('role')
        candidate_name = RECENT_EXPERT_CANDIDATES.get(role)
        candidate = _load_json(task_dir / 'artifacts' / str(candidate_name))
        if not role or not candidate:
            continue
        role_counts[role] = role_counts.get(role, 0) + 1
        signal_keys_by_role = {
            'strategy-expert': ['code_touchpoints', 'change_priority', 'factor_handoff', 'parameter_handoff', 'backtest_handoff', 'validation_priority'],
            'parameter-evolver': ['sensitivity_rationales', 'range_justification', 'metric_guardrails', 'code_touchpoints', 'change_priority', 'backtest_handoff'],
            'factor-miner': ['applicability_conditions', 'code_touchpoints', 'strategy_handoff', 'parameter_handoff', 'validation_priority'],
        }
        signal_preview: dict[str, list[str]] = {}
        for key in signal_keys_by_role.get(role, []):
            values = candidate.get(key, [])
            if isinstance(values, list) and values:
                reusable_signal_counts[key] = reusable_signal_counts.get(key, 0) + 1
                signal_preview[key] = values[:2]
        latest_examples.append({
            'task_id': task_dir.name,
            'role': role,
            'objective': task.get('objective'),
            'target_files': candidate.get('target_files', []),
            'signal_preview': signal_preview,
        })

    dominant_expert_role = max(role_counts, key=role_counts.get) if role_counts else None
    return {
        'recent_task_count': len(latest_examples),
        'expert_role_counts': role_counts,
        'reusable_signal_counts': reusable_signal_counts,
        'dominant_expert_role': dominant_expert_role,
        'recent_examples': latest_examples,
        'adaptive_loop_bridge': adaptive_loop_summary or {},
    }


def refresh_active_observation_windows(jobs_root: str | Path = JOBS_ROOT, refreshed_by: str = 'worker-runtime-scheduler') -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    items: list[dict[str, Any]] = []
    refreshed_count = 0
    finalized_timeout_count = 0
    overdue_count = 0
    active_count = 0

    if not jobs_root.exists():
        return {
            'jobs_scanned': 0,
            'refreshed_count': 0,
            'active_count': 0,
            'overdue_count': 0,
            'finalized_timeout_count': 0,
            'items': [],
        }

    for task_dir in sorted(jobs_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith('_'):
            continue
        observation = _load_json(task_dir / 'artifacts' / 'post_execution_observation.json')
        if not observation:
            continue
        if observation.get('observation_state') != 'observing':
            continue
        target = 'release' if observation.get('execution_target') == 'official_release' else 'rollback' if observation.get('execution_target') == 'rollback' else None
        if not target:
            continue
        active_count += 1
        refreshed = refresh_observation_window(task_dir=task_dir, target=target, refreshed_by=refreshed_by, note='scheduler cycle refresh')
        refreshed_count += 1
        if refreshed.get('sla_state') == 'overdue':
            overdue_count += 1
        if refreshed.get('observation_state') == 'observation_timed_out':
            finalized_timeout_count += 1
        items.append({
            'task_id': task_dir.name,
            'execution_target': refreshed.get('execution_target'),
            'run_id': refreshed.get('run_id'),
            'observation_state': refreshed.get('observation_state'),
            'sla_state': refreshed.get('sla_state'),
            'is_overdue': refreshed.get('is_overdue'),
            'is_timed_out': refreshed.get('is_timed_out'),
            'requires_manual_followup': refreshed.get('requires_manual_followup'),
            'deadline_at': refreshed.get('deadline_at'),
            'timeout_at': refreshed.get('timeout_at'),
        })

    return {
        'jobs_scanned': len([p for p in jobs_root.iterdir() if p.is_dir() and not p.name.startswith('_')]) if jobs_root.exists() else 0,
        'refreshed_count': refreshed_count,
        'active_count': active_count,
        'overdue_count': overdue_count,
        'finalized_timeout_count': finalized_timeout_count,
        'items': items,
    }


def summarize_observation_runtime(lifecycle_payload: dict[str, Any]) -> dict[str, Any]:
    items = list((lifecycle_payload or {}).get('items', []) or [])
    active_items = [item for item in items if item.get('post_execution_observation_state') == 'observing' and item.get('post_execution_observation_active')]
    pending_followups = [item for item in items if item.get('post_execution_observation_requires_manual_followup')]
    timed_out_items = [item for item in items if item.get('post_execution_observation_timed_out') or item.get('post_execution_observation_state') == 'observation_timed_out']
    overdue_items = [item for item in items if item.get('post_execution_observation_is_overdue') and item.get('post_execution_observation_state') == 'observing']
    failed_items = [item for item in items if item.get('post_execution_observation_state') == 'observation_failed']

    def _normalize_followup_state(item: dict[str, Any]) -> str:
        state = str(item.get('post_execution_observation_followup_item_state') or '').strip().lower()
        if state in {'open', 'acknowledged', 'in_progress', 'resolved', 'closed', 'reopened'}:
            return state
        return 'open' if item.get('post_execution_observation_requires_manual_followup') else 'not_required'

    def _sort_key(item: dict[str, Any]) -> tuple[int, str, str, str]:
        return (
            int(item.get('post_execution_observation_queue_priority_rank') if item.get('post_execution_observation_queue_priority_rank') is not None else 9),
            str(item.get('post_execution_observation_timeout_at') or ''),
            str(item.get('post_execution_observation_deadline_at') or ''),
            str(item.get('task_id') or ''),
        )

    latest_attention_items = sorted(overdue_items + timed_out_items, key=_sort_key)[:5]
    pending_examples = sorted(pending_followups, key=_sort_key)[:5]
    escalation_counts: dict[str, int] = {}
    routing_target_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    assignment_counts = {'assigned': 0, 'unassigned': 0, 'acknowledged': 0}
    resolution_category_counts: dict[str, int] = {}
    target_resolution_category_counts: dict[str, dict[str, int]] = {'release': {}, 'rollback': {}}
    handoff_count = 0
    backfilled_item_count = 0
    manual_classification_required_count = 0
    status_counts = {'open': 0, 'in_progress': 0, 'resolved': 0, 'closed': 0}
    queue_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    recently_closed_items: list[dict[str, Any]] = []

    def _compact(item: dict[str, Any]) -> dict[str, Any]:
        followup_state = _normalize_followup_state(item)
        compact = {
            'task_id': item.get('task_id'),
            'role': item.get('role'),
            'execution_target': item.get('post_execution_observation_target'),
            'run_id': item.get('post_execution_observation_run_id'),
            'batch_id': item.get('post_execution_observation_batch_id'),
            'observation_state': item.get('post_execution_observation_state'),
            'sla_state': item.get('post_execution_observation_sla_state'),
            'is_overdue': item.get('post_execution_observation_is_overdue'),
            'is_timed_out': item.get('post_execution_observation_is_timed_out'),
            'requires_manual_followup': item.get('post_execution_observation_requires_manual_followup'),
            'manual_followup_reason': item.get('post_execution_observation_manual_followup_reason'),
            'escalation_level': item.get('post_execution_observation_escalation_level'),
            'queue_priority': item.get('post_execution_observation_queue_priority'),
            'queue_priority_rank': item.get('post_execution_observation_queue_priority_rank'),
            'recommended_owner': item.get('post_execution_observation_recommended_owner'),
            'recommended_routing_target': item.get('post_execution_observation_recommended_routing_target'),
            'routing_targets': item.get('post_execution_observation_routing_targets'),
            'followup_action_count': item.get('post_execution_observation_followup_action_count'),
            'followup_owner': item.get('post_execution_observation_followup_owner'),
            'followup_assignee': item.get('post_execution_observation_followup_assignee'),
            'followup_assignment_status': item.get('post_execution_observation_followup_assignment_status'),
            'followup_handoff_count': int(item.get('post_execution_observation_followup_handoff_count') or 0),
            'followup_resolution_category': item.get('post_execution_observation_followup_resolution_category'),
            'followup_resolution_taxonomy': item.get('post_execution_observation_followup_resolution_taxonomy'),
            'followup_resolution_summary': item.get('post_execution_observation_followup_resolution_summary'),
            'followup_closure_audit': item.get('post_execution_observation_followup_closure_audit'),
            'followup_backfill': item.get('post_execution_observation_followup_backfill'),
            'manual_classification_required': bool(item.get('post_execution_observation_followup_manual_classification_required')),
            'manual_classification_state': item.get('post_execution_observation_manual_classification_state'),
            'manual_classification_workflow': item.get('post_execution_observation_manual_classification_workflow') or {},
            'resolution_review_artifact': item.get('post_execution_observation_followup_resolution_review_artifact'),
            'followup_item_state': followup_state,
            'followup_item_open': item.get('post_execution_observation_followup_item_open'),
            'followup_terminal': item.get('post_execution_observation_followup_terminal'),
            'followup_last_action': item.get('post_execution_observation_followup_last_action'),
            'followup_last_action_at': item.get('post_execution_observation_followup_last_action_at'),
            'followup_last_actor': item.get('post_execution_observation_followup_last_actor'),
            'deadline_at': item.get('post_execution_observation_deadline_at'),
            'timeout_at': item.get('post_execution_observation_timeout_at'),
            'closed_at': item.get('post_execution_observation_closed_at'),
        }
        return compact

    for item in pending_followups:
        compact = _compact(item)
        queue_items.append(compact)
        escalation = compact.get('escalation_level') or 'none'
        escalation_counts[escalation] = escalation_counts.get(escalation, 0) + 1
        owner = compact.get('recommended_owner') or 'unassigned'
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        assignment_status = str(compact.get('followup_assignment_status') or '').strip().lower()
        if compact.get('followup_assignee'):
            assignment_counts['assigned'] += 1
        else:
            assignment_counts['unassigned'] += 1
        if assignment_status == 'acknowledged':
            assignment_counts['acknowledged'] += 1
        handoff_count += int(compact.get('followup_handoff_count') or 0)
        backfill_payload = compact.get('followup_backfill') or {}
        if isinstance(backfill_payload, dict) and list(backfill_payload.get('repaired_fields') or []):
            backfilled_item_count += 1
        target_key = 'rollback' if compact.get('execution_target') == 'rollback' else 'release'
        resolution_category = compact.get('followup_resolution_category')
        if not resolution_category:
            manual_classification_required_count += 1
            resolution_bucket = 'needs_manual_classification'
        else:
            resolution_bucket = resolution_category
        resolution_category_counts[resolution_bucket] = resolution_category_counts.get(resolution_bucket, 0) + 1
        target_resolution_category_counts.setdefault(target_key, {})
        target_resolution_category_counts[target_key][resolution_bucket] = target_resolution_category_counts[target_key].get(resolution_bucket, 0) + 1
        for target in list(compact.get('routing_targets') or []):
            routing_target_counts[target] = routing_target_counts.get(target, 0) + 1
        state = compact.get('followup_item_state')
        if state in {'open', 'acknowledged', 'reopened'}:
            status_counts['open'] += 1
            unresolved_items.append(compact)
        elif state == 'in_progress':
            status_counts['in_progress'] += 1
            unresolved_items.append(compact)
        elif state == 'resolved':
            status_counts['resolved'] += 1
        elif state == 'closed':
            status_counts['closed'] += 1
            recently_closed_items.append(compact)

    queue_summary = {
        'queue_count': len(unresolved_items),
        'total_item_count': len(queue_items),
        'all_items': queue_items,
        'status_counts': status_counts,
        'escalation_counts': escalation_counts,
        'routing_target_counts': routing_target_counts,
        'recommended_owner_counts': owner_counts,
        'assignment_counts': assignment_counts,
        'assigned_count': assignment_counts['assigned'],
        'unassigned_count': assignment_counts['unassigned'],
        'ownership_acknowledged_count': assignment_counts['acknowledged'],
        'handoff_count': handoff_count,
        'backfilled_item_count': backfilled_item_count,
        'manual_classification_required_count': manual_classification_required_count,
        'resolution_category_counts': resolution_category_counts,
        'target_resolution_category_counts': target_resolution_category_counts,
        'top_items': sorted(unresolved_items, key=lambda item: _sort_key({
            'post_execution_observation_queue_priority_rank': item.get('queue_priority_rank'),
            'post_execution_observation_timeout_at': item.get('timeout_at'),
            'post_execution_observation_deadline_at': item.get('deadline_at'),
            'task_id': item.get('task_id'),
        }))[:5],
        'top_unresolved_items': sorted(unresolved_items, key=lambda item: _sort_key({
            'post_execution_observation_queue_priority_rank': item.get('queue_priority_rank'),
            'post_execution_observation_timeout_at': item.get('timeout_at'),
            'post_execution_observation_deadline_at': item.get('deadline_at'),
            'task_id': item.get('task_id'),
        }))[:5],
        'recently_closed_items': sorted(recently_closed_items, key=lambda item: (str(item.get('closed_at') or ''), str(item.get('task_id') or '')), reverse=True)[:5],
        'manual_classification_items': [item for item in queue_items if item.get('manual_classification_required')][:10],
        'unresolved_manual_classification_items': [item for item in unresolved_items if item.get('manual_classification_required')][:10],
    }

    return {
        'visible_count': len([item for item in items if item.get('post_execution_observation_visible')]),
        'active_count': len(active_items),
        'pending_followup_count': len(unresolved_items),
        'timed_out_count': len(timed_out_items),
        'overdue_count': len(overdue_items),
        'failed_count': len(failed_items),
        'followup_open_count': status_counts['open'],
        'followup_in_progress_count': status_counts['in_progress'],
        'followup_resolved_count': status_counts['resolved'],
        'followup_closed_count': status_counts['closed'],
        'latest_attention_items': [_compact(item) for item in latest_attention_items],
        'pending_followup_examples': [_compact(item) for item in pending_examples],
        'followup_queue': queue_summary,
        'followup_assigned_count': assignment_counts['assigned'],
        'followup_unassigned_count': assignment_counts['unassigned'],
        'followup_handoff_count': handoff_count,
        'followup_backfilled_item_count': backfilled_item_count,
        'followup_manual_classification_required_count': manual_classification_required_count,
        'followup_resolution_category_counts': resolution_category_counts,
        'followup_target_resolution_category_counts': target_resolution_category_counts,
        'recently_closed_followup_items': queue_summary['recently_closed_items'],
        'target_counts': {
            'release': len([item for item in items if item.get('post_execution_observation_target') == 'official_release']),
            'rollback': len([item for item in items if item.get('post_execution_observation_target') == 'rollback']),
        },
        'state_counts': {
            'observing': len([item for item in items if item.get('post_execution_observation_state') == 'observing']),
            'observation_completed': len([item for item in items if item.get('post_execution_observation_state') == 'observation_completed']),
            'observation_failed': len(failed_items),
            'observation_timed_out': len(timed_out_items),
        },
    }


def summarize_open_gaps(*, health_payload: dict[str, Any], adaptive_loop_summary: dict[str, Any], recent_learning_summary: dict[str, Any]) -> dict[str, Any]:
    closure_counts = (health_payload or {}).get('closure_counts', {}) or {}
    approval_states = (health_payload or {}).get('human_approval_state_counts', {}) or {}
    quality_observable = (health_payload or {}).get('quality_average_score') is not None or bool((health_payload or {}).get('quality_grade_counts'))
    adaptive_decision_count = int((adaptive_loop_summary or {}).get('total_adaptive_decisions', 0) or 0)
    recent_task_count = int((recent_learning_summary or {}).get('recent_task_count', 0) or 0)

    items: list[dict[str, Any]] = [
        {
            'gap_id': 'official_release_pipeline',
            'title': 'official release / rollback 仍是骨架，不是完整闭环',
            'priority': 'high',
            'status': 'open',
            'rationale': '当前 release closure 观察面已建立，但真实发布执行与正式回滚仍未落成可执行闭环。',
            'next_step': '继续推进 official release action、rollback registry 与正式执行前检查的真实收口。',
        },
        {
            'gap_id': 'supervisor_runtime',
            'title': 'systemd/supervisor 常驻托管仍未完成',
            'priority': 'medium',
            'status': 'open',
            'rationale': '当前 runtime scheduler 可跑，但仍属于轻量 skeleton，不是完整常驻托管。',
            'next_step': '继续补 supervisor/systemd 级托管与故障恢复策略。',
        },
        {
            'gap_id': 'benchmark_regression',
            'title': '更深 benchmark / regression 体系仍未完成',
            'priority': 'medium',
            'status': 'open',
            'rationale': '当前 quality 与专家深化已可观察，但尚未形成更完整 benchmark / regression 面。',
            'next_step': '继续补强 benchmark、regression 与稳定性评测基线。',
        },
    ]

    if int(closure_counts.get('approval_required', 0) or 0) > 0 or int(approval_states.get('awaiting', 0) or 0) > 0:
        items.append({
            'gap_id': 'real_human_approval',
            'title': '真实人工审批记录与正式发布动作仍未接入可执行路径',
            'priority': 'high',
            'status': 'open',
            'rationale': '当前审批三态已可观察，但仍主要是 awaiting / placeholder，不是可执行的真实审批通道。',
            'next_step': '继续补真实 approve/reject 输入与 official release 执行入口。',
        })
    if adaptive_decision_count < 3:
        items.append({
            'gap_id': 'adaptive_loop_depth',
            'title': 'adaptive loop 真实样本深度仍偏浅',
            'priority': 'medium',
            'status': 'open',
            'rationale': f'当前仅记录 {adaptive_decision_count} 次 adaptive 选路，真实流转样本仍偏少。',
            'next_step': '继续跑通更多 cross-worker adaptive loop 样本，验证选路稳定性。',
        })
    if recent_task_count < 6:
        items.append({
            'gap_id': 'recent_learning_density',
            'title': '近期经验沉淀样本密度仍不足',
            'priority': 'medium',
            'status': 'open',
            'rationale': f'当前仅沉淀 {recent_task_count} 个可复用专家样本，反哺面还不够厚。',
            'next_step': '继续补真实通过验收的 strategy / parameter / factor 样本。',
        })
    if not quality_observable:
        items.append({
            'gap_id': 'quality_observability',
            'title': 'quality / evaluation 观察面仍不足',
            'priority': 'medium',
            'status': 'open',
            'rationale': '若缺少质量评分/质量样本，后续阶段判断会继续偏骨架口径。',
            'next_step': '继续补质量评分样本与评测链。',
        })

    priority_rank = {'high': 0, 'medium': 1, 'low': 2}
    ordered = sorted(items, key=lambda item: (priority_rank.get(item.get('priority', 'low'), 9), item.get('gap_id', '')))
    return {
        'open_gap_count': len(ordered),
        'high_priority_gap_count': len([item for item in ordered if item.get('priority') == 'high']),
        'top_gap_ids': [item.get('gap_id') for item in ordered[:3]],
        'items': ordered,
    }


def build_governance_closeout_cutline(*, cycle_id: str, task_id: str = 'validation_controlled_execution_runtime', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    artifact_root = jobs_root / task_id / 'artifacts'
    unresolved = _load_json(artifact_root / 'unresolved_blocker_tracker.json')
    owner_matrix = _load_json(artifact_root / 'blocker_owner_resolution_matrix.json')
    dependency_map = _load_json(artifact_root / 'signoff_dependency_map.json')
    evidence_packet = _load_json(artifact_root / 'cutover_signoff_evidence_packet.json')
    binding_checklist = _load_json(artifact_root / 'credential_binding_evidence_checklist.json')
    progress_digest = _load_json(artifact_root / 'human_action_progress_digest.json')
    pending_board = _load_json(artifact_root / 'pending_human_action_board.json')

    matrix_items = list(owner_matrix.get('items', []) or [])
    unresolved_items = list(unresolved.get('items', []) or [])
    structural_items = [item for item in matrix_items if item.get('closure_class') == 'structurally_blocked']
    governance_ready_items = [item for item in matrix_items if item.get('closure_class') == 'already_prepared']
    human_driven_items = [item for item in matrix_items if item.get('closure_class') == 'human_driven']
    closable_items = [item for item in matrix_items if bool(item.get('closable_now_without_real_execution'))]
    residual_governance_items = [item for item in matrix_items if item.get('closure_class') in {'human_driven'}]

    shared_rule_family = owner_matrix.get('shared_rule_family') or unresolved.get('shared_rule_family') or 'release_rollback_controlled_executor_policy'
    unresolved_index = {item.get('blocker_id'): item for item in unresolved_items}
    pending_count = int((pending_board.get('pending_count') or pending_board.get('item_count') or len((pending_board.get('items') or [])) or 0))

    governance_closeout_review = {
        'cycle_id': cycle_id,
        'task_id': task_id,
        'record_type': 'governance_closeout_review',
        'generated_at': _now().isoformat(),
        'shared_rule_family': shared_rule_family,
        'governance_closeout_available': True,
        'zero_real_execution_required': True,
        'governance_closable_item_count': len(closable_items),
        'residual_governance_gap_count': len(residual_governance_items),
        'residual_structural_blocker_count': len(structural_items),
        'governance_items_ready_count': len(governance_ready_items),
        'human_driven_items_pending_count': len(human_driven_items),
        'pending_human_action_count': pending_count,
        'closeout_status': 'governance_surface_exhausted' if not residual_governance_items else 'governance_ready_waiting_human_closeout',
        'decision_boundary': 'stop_when_only_structural_or_human-controlled blockers remain',
        'items': [
            {
                'blocker_id': item.get('blocker_id'),
                'execution_target': item.get('execution_target'),
                'closure_class': item.get('closure_class'),
                'closable_now_without_real_execution': bool(item.get('closable_now_without_real_execution')),
                'owner': item.get('owner'),
                'depends_on': item.get('depends_on', []),
                'evidence_refs': item.get('evidence_refs', []),
                'source_refs': item.get('source_refs', {}),
                'tracker_ref': 'artifacts/unresolved_blocker_tracker.json',
                'tracker_status': (unresolved_index.get(item.get('blocker_id')) or {}).get('status'),
                'governance_disposition': 'closeable_within_governance' if item.get('closure_class') in {'already_prepared', 'human_driven'} else 'outside_governance_scope',
            }
            for item in matrix_items
        ],
        'refs': {
            'unresolved_blocker_tracker': 'artifacts/unresolved_blocker_tracker.json',
            'blocker_owner_resolution_matrix': 'artifacts/blocker_owner_resolution_matrix.json',
            'signoff_dependency_map': 'artifacts/signoff_dependency_map.json',
            'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
            'cutover_signoff_evidence_packet': 'artifacts/cutover_signoff_evidence_packet.json',
            'human_action_progress_digest': 'artifacts/human_action_progress_digest.json',
            'pending_human_action_board': 'artifacts/pending_human_action_board.json',
        },
    }

    residual_structural_blocker_register = {
        'cycle_id': cycle_id,
        'task_id': task_id,
        'record_type': 'residual_structural_blocker_register',
        'generated_at': _now().isoformat(),
        'shared_rule_family': shared_rule_family,
        'residual_structural_blocker_register_available': True,
        'zero_real_execution_required': True,
        'residual_structural_blocker_count': len(structural_items),
        'top_residual_structural_blockers': [item.get('blocker_id') for item in structural_items[:3]],
        'items': [
            {
                'blocker_id': item.get('blocker_id'),
                'execution_target': item.get('execution_target'),
                'category': item.get('category'),
                'severity': item.get('severity'),
                'owner': item.get('owner'),
                'dependency_refs': item.get('depends_on', []),
                'evidence_refs': item.get('evidence_refs', []),
                'tracker_ref': 'artifacts/unresolved_blocker_tracker.json',
                'closeout_ref': 'artifacts/governance_closeout_review.json',
                'structural_reason': item.get('blocking_type') or 'real_executor_body_missing',
                'phase_shift_signal': 'requires_next_phase_real_implementation',
                'within_governance_closeout_scope': False,
            }
            for item in structural_items
        ],
        'refs': governance_closeout_review['refs'],
    }

    governance_cutline_decision = {
        'cycle_id': cycle_id,
        'task_id': task_id,
        'record_type': 'governance_cutline_decision',
        'generated_at': _now().isoformat(),
        'shared_rule_family': shared_rule_family,
        'governance_cutline_available': True,
        'zero_real_execution_required': True,
        'decision': 'stop_governance_shell_expansion_and_handoff' if len(structural_items) > 0 else 'continue_governance_closeout',
        'decision_summary': '治理壳子已完成收口；剩余问题已转为结构性实现缺口与人工受控动作，不应继续横向加治理层。',
        'residual_governance_gap_count': len(residual_governance_items),
        'residual_structural_blocker_count': len(structural_items),
        'stop_conditions_met': [
            'shared closeout/cutline rules exist for release and rollback',
            'owner/dependency/evidence/blocker reference chain complete',
            'remaining implementation blockers are outside governance-only scope',
        ],
        'do_not_continue_when': [
            'new governance artifacts would not reduce structural blocker count',
            'remaining items require real executor implementation',
            'remaining items require human credential binding or cutover signoff',
        ],
        'continue_only_if': [
            'owner missing',
            'dependency map broken',
            'evidence chain incomplete',
        ],
        'refs': {
            **governance_closeout_review['refs'],
            'governance_closeout_review': 'artifacts/governance_closeout_review.json',
            'residual_structural_blocker_register': 'artifacts/residual_structural_blocker_register.json',
        },
    }

    next_phase_handoff_gate = {
        'cycle_id': cycle_id,
        'task_id': task_id,
        'record_type': 'next_phase_handoff_gate',
        'generated_at': _now().isoformat(),
        'shared_rule_family': shared_rule_family,
        'next_phase_handoff_gate_available': True,
        'zero_real_execution_required': True,
        'next_phase_name': 'real executor implementation + controlled binding/signoff completion',
        'gate_state': 'blocked_pending_structural_and_human_inputs',
        'entry_prerequisites': [
            'governance cutline decision recorded',
            'residual structural blocker register recorded',
            'implementation blueprint frozen as handoff baseline',
            'manual credential/target binding evidence ready for operator completion',
            'cutover signoff dependency map visible to owner',
        ],
        'unmet_prerequisites': [
            'real release executor body not implemented',
            'real rollback executor body not implemented',
            'manual credential/target binding not completed',
            'cutover signoff not completed',
        ],
        'handoff_inputs': {
            'implementation_blueprint_ref': 'artifacts/future_executor_implementation_blueprint.json',
            'dependency_map_ref': 'artifacts/signoff_dependency_map.json',
            'binding_checklist_ref': 'artifacts/credential_binding_evidence_checklist.json',
            'signoff_evidence_ref': 'artifacts/cutover_signoff_evidence_packet.json',
            'human_action_progress_ref': 'artifacts/human_action_progress_digest.json',
        },
        'release_rollback_rule_shared': True,
        'blocker_tracker_ref': 'artifacts/unresolved_blocker_tracker.json',
        'closeout_decision_ref': 'artifacts/governance_cutline_decision.json',
    }

    def _md_lines(payload: dict[str, Any], title: str) -> str:
        lines = [f'# {title}', '']
        for key, value in payload.items():
            if key == 'items' and isinstance(value, list):
                lines.append(f'- {key}:')
                for item in value:
                    lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
            elif key == 'refs' and isinstance(value, dict):
                lines.append(f'- {key}: ' + _render_report_value(value))
            else:
                lines.append(f'- {key}: ' + str(_render_report_value(value)))
        return '\n'.join(lines) + '\n'

    _write_json(artifact_root / 'governance_closeout_review.json', governance_closeout_review)
    (artifact_root / 'governance_closeout_review.md').write_text(_md_lines(governance_closeout_review, 'Governance Closeout Review'), encoding='utf-8')
    _write_json(artifact_root / 'residual_structural_blocker_register.json', residual_structural_blocker_register)
    (artifact_root / 'residual_structural_blocker_register.md').write_text(_md_lines(residual_structural_blocker_register, 'Residual Structural Blocker Register'), encoding='utf-8')
    _write_json(artifact_root / 'governance_cutline_decision.json', governance_cutline_decision)
    (artifact_root / 'governance_cutline_decision.md').write_text(_md_lines(governance_cutline_decision, 'Governance Cutline Decision'), encoding='utf-8')
    _write_json(artifact_root / 'next_phase_handoff_gate.json', next_phase_handoff_gate)
    (artifact_root / 'next_phase_handoff_gate.md').write_text(_md_lines(next_phase_handoff_gate, 'Next Phase Handoff Gate'), encoding='utf-8')

    return {
        'governance_closeout_review': governance_closeout_review,
        'residual_structural_blocker_register': residual_structural_blocker_register,
        'governance_cutline_decision': governance_cutline_decision,
        'next_phase_handoff_gate': next_phase_handoff_gate,
        'source_artifacts': {
            'dependency_map': dependency_map,
            'evidence_packet': evidence_packet,
            'binding_checklist': binding_checklist,
            'progress_digest': progress_digest,
            'pending_human_action_board': pending_board,
        },
    }


def run_cycle(*, jobs_root: str | Path = JOBS_ROOT, max_age_minutes: int = 30, auto_retry: bool = False, retry_requested_by: str = 'worker-runtime-scheduler', backfill_missing: bool = True) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    cycle_id = f"WRS-{_now().strftime('%Y%m%d-%H%M%S')}"
    cycle_dir = CYCLES_ROOT / cycle_id
    cycle_dir.mkdir(parents=True, exist_ok=True)

    _append_event('cycle_started', cycle_id=cycle_id, jobs_root=str(jobs_root), max_age_minutes=max_age_minutes, auto_retry=auto_retry, backfill_missing=backfill_missing)

    backfill = backfill_jobs(jobs_root) if backfill_missing else {'jobs_scanned': 0, 'quality_backfilled_count': 0, 'formalization_backfilled_count': 0, 'closure_backfilled_count': 0, 'items': []}
    followup_backfill = backfill_all_followups(jobs_root=jobs_root, updated_by='worker-runtime-scheduler') if backfill_missing else {'jobs_scanned': 0, 'followups_checked': 0, 'changed_count': 0, 'manual_classification_required_count': 0, 'repaired_resolution_category_count': 0, 'repaired_closure_audit_count': 0, 'items': []}
    healed = heal_jobs(jobs_root, max_age_minutes=max_age_minutes, auto_retry=auto_retry, retry_requested_by=retry_requested_by)
    observation_refresh = refresh_active_observation_windows(jobs_root, refreshed_by='worker-runtime-scheduler')
    health_payload = dashboard(jobs_root, max_age_minutes=max_age_minutes)
    recovery_payload = jobs_recovery_dashboard(jobs_root)
    lifecycle_payload = lifecycle_dashboard(jobs_root)
    observation_runtime = summarize_observation_runtime(lifecycle_payload)
    observation_resolution_review = build_followup_resolution_review(observation_runtime)
    rule_proposal_review = build_rule_proposal_review(
        followup_resolution_review=observation_resolution_review,
        latest_cycle={},
        state_root=STATE_ROOT,
        cycle_id=cycle_id,
    )
    governed_rule_sink = materialize_rule_sink(rule_proposal_review=rule_proposal_review, state_root=STATE_ROOT, cycle_id=cycle_id)
    local_rulebook_export = export_rulebook_artifacts(rule_proposal_review=rule_proposal_review, state_root=STATE_ROOT, cycle_id=cycle_id, export_target='local-rulebook')
    local_rulebook_governance_review = _load_json(STATE_ROOT / 'local_rulebook_governance_review.json')
    adaptive_loop_summary = summarize_adaptive_loops()
    recent_learning_summary = summarize_recent_ecosystem_learning(jobs_root, adaptive_loop_summary=adaptive_loop_summary)
    governance_closeout_bundle = build_governance_closeout_cutline(cycle_id=cycle_id, jobs_root=jobs_root)
    open_gap_summary = summarize_open_gaps(
        health_payload=health_payload,
        adaptive_loop_summary=adaptive_loop_summary,
        recent_learning_summary=recent_learning_summary,
    )

    _write_json(cycle_dir / 'health_dashboard.json', health_payload)
    _write_json(cycle_dir / 'recovery_dashboard.json', recovery_payload)
    _write_json(cycle_dir / 'lifecycle_dashboard.json', lifecycle_payload)
    _write_json(cycle_dir / 'adaptive_loop_summary.json', adaptive_loop_summary)
    _write_json(cycle_dir / 'recent_ecosystem_learning.json', recent_learning_summary)
    _write_json(cycle_dir / 'backfill_summary.json', backfill)
    _write_json(cycle_dir / 'followup_backfill_summary.json', followup_backfill)
    _write_json(cycle_dir / 'healed_jobs.json', {'cycle_id': cycle_id, 'items': healed})
    _write_json(cycle_dir / 'observation_refresh.json', observation_refresh)
    _write_json(cycle_dir / 'observation_runtime_summary.json', observation_runtime)
    _write_json(cycle_dir / 'followup_resolution_review.json', observation_resolution_review)
    write_followup_resolution_review_markdown(observation_resolution_review, cycle_dir / 'followup_resolution_review.md')
    _write_json(cycle_dir / 'pending_followup_queue.json', (observation_runtime.get('followup_queue') or {}))
    _write_json(cycle_dir / 'governance_closeout_review.json', governance_closeout_bundle['governance_closeout_review'])
    _write_json(cycle_dir / 'residual_structural_blocker_register.json', governance_closeout_bundle['residual_structural_blocker_register'])
    _write_json(cycle_dir / 'governance_cutline_decision.json', governance_closeout_bundle['governance_cutline_decision'])
    _write_json(cycle_dir / 'next_phase_handoff_gate.json', governance_closeout_bundle['next_phase_handoff_gate'])
    write_dashboard_markdown(health_payload, cycle_dir / 'health_dashboard.md')
    write_recovery_markdown(recovery_payload, cycle_dir / 'recovery_dashboard.md')
    write_lifecycle_markdown(lifecycle_payload, cycle_dir / 'lifecycle_dashboard.md')

    top_gap_items = (open_gap_summary.get('items', []) or [])[:3]
    health_items = (health_payload.get('items') or [])
    readiness_gate_counts = [int(item.get('executor_readiness_gate_count') or 0) for item in health_items if item.get('executor_readiness_gate_count') is not None]
    readiness_unmet_counts = [int(item.get('executor_unmet_gate_count') or 0) for item in health_items if item.get('executor_unmet_gate_count') is not None]
    rollout_gate_counts = [int(item.get('rollout_gate_count') or 0) for item in health_items if item.get('rollout_gate_count') is not None]
    rollout_unmet_counts = [int(item.get('rollout_unmet_count') or 0) for item in health_items if item.get('rollout_unmet_count') is not None]
    waiver_exception_counts = [int(item.get('waiver_exception_count') or 0) for item in health_items if item.get('waiver_exception_count') is not None]
    admission_state_counter: Counter[str] = Counter()
    top_blocking_gate_counter: Counter[str] = Counter()
    readiness_unmet_gate_counter: Counter[str] = Counter()
    request_state_counter: Counter[str] = Counter()
    request_actions: list[dict[str, Any]] = []
    request_requested_count = 0
    request_acknowledged_count = 0
    request_accepted_count = 0
    request_declined_count = 0
    request_expired_count = 0
    request_open_count = 0
    request_inflight_count = 0
    request_reassigned_count = 0
    request_escalated_count = 0
    request_retry_ready_count = 0
    request_escalations: list[dict[str, Any]] = []
    request_transitions: list[dict[str, Any]] = []
    top_pending_requests: list[dict[str, Any]] = []
    request_owner_counter: Counter[str] = Counter()
    for item in health_items:
        for gate_id in list(item.get('top_unmet_executor_gates') or []):
            readiness_unmet_gate_counter[str(gate_id)] += 1
        for gate_id in list(item.get('top_blocking_gates') or []):
            top_blocking_gate_counter[str(gate_id)] += 1
        if item.get('overall_admission_state'):
            admission_state_counter[str(item.get('overall_admission_state'))] += 1
        request_requested_count += int(item.get('execution_request_requested_count') or 0)
        request_acknowledged_count += int(item.get('execution_request_acknowledged_count') or 0)
        request_accepted_count += int(item.get('execution_request_accepted_count') or 0)
        request_declined_count += int(item.get('execution_request_declined_count') or 0)
        request_expired_count += int(item.get('execution_request_expired_count') or 0)
        request_open_count += int(item.get('request_open_count') or 0)
        request_inflight_count += int(item.get('request_inflight_count') or 0)
        request_reassigned_count += int(item.get('execution_request_reassigned_count') or 0)
        request_escalated_count += int(item.get('execution_request_escalated_count') or 0)
        request_retry_ready_count += int(item.get('execution_request_retry_ready_count') or 0)
        for owner in list(item.get('top_request_owners') or []):
            request_owner_counter[str(owner.get('owner') or '')] += int(owner.get('request_count') or 0)
        for escalation in list(item.get('recent_request_escalations') or []):
            request_escalations.append(escalation)
        for transition in list(item.get('recent_request_transitions') or []):
            request_transitions.append(transition)
        for pending in list(item.get('top_pending_requests') or []):
            top_pending_requests.append(pending)
        for state in list(item.get('top_request_states') or []):
            request_state_counter[str(state)] += 1
        for action in list(item.get('recent_request_actions') or []):
            request_actions.append(action)
    top_unmet_executor_gates = [gate_id for gate_id, _count in sorted(readiness_unmet_gate_counter.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]
    top_blocking_gates = [gate_id for gate_id, _count in sorted(top_blocking_gate_counter.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]
    request_actions.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    request_escalations.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    request_transitions.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    top_pending_requests.sort(key=lambda item: (0 if item.get('retry_ready') else 1, {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'none': 4}.get(str(item.get('escalation_level') or 'none'), 5), str(item.get('expires_at') or item.get('requested_at') or '')))
    summary = {
        'cycle_id': cycle_id,
        'generated_at': _now().isoformat(),
        'jobs_root': str(jobs_root),
        'max_age_minutes': max_age_minutes,
        'auto_retry': auto_retry,
        'job_count': health_payload.get('job_count'),
        'stale_count': health_payload.get('stale_count'),
        'healed_count': len(healed),
        'retry_created_count': len([item for item in healed if item.get('retry_task_id')]),
        'governance_action_count': health_payload.get('governance', {}).get('action_count', 0),
        'recoverability_counts': recovery_payload.get('recoverability_counts', {}),
        'quality_grade_counts': health_payload.get('quality_grade_counts', {}),
        'quality_average_score': health_payload.get('quality_average_score'),
        'formalization_state_counts': health_payload.get('formalization_state_counts', {}),
        'closure_counts': health_payload.get('closure_counts', {}),
        'executor_contract_available_count': health_payload.get('closure_counts', {}).get('executor_contract_available', 0),
        'dry_run_available_count': health_payload.get('closure_counts', {}).get('dry_run_available', 0),
        'execution_receipt_protocol_available_count': health_payload.get('closure_counts', {}).get('execution_receipt_protocol_available', 0),
        'handoff_packet_available_count': health_payload.get('closure_counts', {}).get('handoff_packet_available', 0),
        'operator_execution_request_available_count': health_payload.get('closure_counts', {}).get('operator_execution_request_available', 0),
        'receipt_correlation_ready_count': health_payload.get('closure_counts', {}).get('receipt_correlation_ready', 0),
        'executor_readiness_review_available_count': health_payload.get('closure_counts', {}).get('executor_readiness_review_visible', 0),
        'executor_adapter_available_count': sum(int(item.get('executor_adapter_available_count') or 0) for item in health_items),
        'executor_capability_registry_available': any(bool(item.get('executor_capability_registry_available')) for item in health_items),
        'invocation_policy_available': any(bool(item.get('invocation_policy_available')) for item in health_items),
        'future_executor_scaffold_available': any(bool(item.get('future_executor_scaffold_available')) for item in health_items),
        'executor_plugin_interface_available': any(bool(item.get('executor_plugin_interface_available')) for item in health_items),
        'transcript_contract_available': any(bool(item.get('transcript_contract_available')) for item in health_items),
        'no_op_executor_available': any(bool(item.get('no_op_executor_available')) for item in health_items),
        'executor_conformance_available': any(bool(item.get('executor_conformance_available')) for item in health_items),
        'executor_error_contract_available': any(bool(item.get('executor_error_contract_available')) for item in health_items),
        'release_rollback_parity_available': any(bool(item.get('release_rollback_parity_available')) for item in health_items),
        'implementation_blueprint_available': any(bool(item.get('implementation_blueprint_available')) for item in health_items),
        'executor_delivery_pack_available': any(bool(item.get('executor_delivery_pack_available')) for item in health_items),
        'executor_acceptance_pack_available': any(bool(item.get('executor_acceptance_pack_available')) for item in health_items),
        'ownership_split_available': any(bool(item.get('ownership_split_available')) for item in health_items),
        'executor_blocker_matrix_available': any(bool(item.get('executor_blocker_matrix_available')) for item in health_items),
        'executor_delivery_item_count': max([int(item.get('executor_delivery_item_count') or 0) for item in health_items] or [0]),
        'executor_acceptance_case_count': max([int(item.get('executor_acceptance_case_count') or 0) for item in health_items] or [0]),
        'executor_blocker_count': max([int(item.get('executor_blocker_count') or 0) for item in health_items] or [0]),
        'cutover_pack_available': any(bool(item.get('cutover_pack_available')) for item in health_items),
        'integration_checklist_available': any(bool(item.get('integration_checklist_available')) for item in health_items),
        'risk_register_available': any(bool(item.get('risk_register_available')) for item in health_items),
        'handoff_summary_available': any(bool(item.get('handoff_summary_available')) for item in health_items),
        'credential_binding_policy_available': any(bool(item.get('credential_binding_policy_available')) for item in health_items),
        'target_binding_registry_available': any(bool(item.get('target_binding_registry_available')) for item in health_items),
        'cutover_signoff_available': any(bool(item.get('cutover_signoff_available')) for item in health_items),
        'blocker_drilldown_available': any(bool(item.get('blocker_drilldown_available')) for item in health_items),
        'human_action_pack_available': any(bool(item.get('human_action_pack_available')) for item in health_items),
        'credential_binding_evidence_checklist_available': any(bool(item.get('credential_binding_evidence_checklist_available')) for item in health_items),
        'signoff_evidence_packet_available': any(bool(item.get('signoff_evidence_packet_available')) for item in health_items),
        'unresolved_blocker_tracker_available': any(bool(item.get('unresolved_blocker_tracker_available')) for item in health_items),
        'pending_human_action_board_available': any(bool(item.get('pending_human_action_board_available')) for item in health_items),
        'credential_binding_runbook_available': any(bool(item.get('credential_binding_runbook_available')) for item in health_items),
        'signoff_runbook_available': any(bool(item.get('signoff_runbook_available')) for item in health_items),
        'blocker_resolution_playbook_available': any(bool(item.get('blocker_resolution_playbook_available')) for item in health_items),
        'unresolved_credential_binding_count': max([int(item.get('unresolved_credential_binding_count') or 0) for item in health_items] or [0]),
        'unresolved_signoff_count': max([int(item.get('unresolved_signoff_count') or 0) for item in health_items] or [0]),
        'unresolved_blocker_owner_count': max([int(item.get('unresolved_blocker_owner_count') or 0) for item in health_items] or [0]),
        'pending_signoff_role_count': max([int(item.get('pending_signoff_role_count') or 0) for item in health_items] or [0]),
        'binding_evidence_gap_count': max([int(item.get('binding_evidence_gap_count') or 0) for item in health_items] or [0]),
        'top_blocker_categories': [category for category, _count in sorted(Counter([str(category) for item in health_items for category in list(item.get('top_blocker_categories') or []) if category]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'top_human_actions': [action for action, _count in sorted(Counter([str(action) for item in health_items for action in list(item.get('top_human_actions') or []) if action]).items(), key=lambda pair: (-pair[1], pair[0]))[:8]],
        'top_pending_human_actions': [action for action, _count in sorted(Counter([str(action) for item in health_items for action in list(item.get('top_pending_human_actions') or []) if action]).items(), key=lambda pair: (-pair[1], pair[0]))[:8]],
        'top_unresolved_human_blockers': [blocker for blocker, _count in sorted(Counter([str(blocker) for item in health_items for blocker in list(item.get('top_unresolved_human_blockers') or []) if blocker]).items(), key=lambda pair: (-pair[1], pair[0]))[:8]],
        'top_missing_executor_contracts': [gap for gap, _count in sorted(Counter([str(gap) for item in health_items for gap in list(item.get('top_missing_executor_contracts') or []) if gap]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'parity_gaps': [gap for gap, _count in sorted(Counter([str(gap) for item in health_items for gap in list(item.get('parity_gaps') or []) if gap]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'top_executor_risks': [risk for risk, _count in sorted(Counter([str(risk) for item in health_items for risk in list(item.get('top_executor_risks') or []) if risk]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'top_executor_blockers': [blocker for blocker, _count in sorted(Counter([str(blocker) for item in health_items for blocker in list(item.get('top_executor_blockers') or []) if blocker]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'top_remaining_blockers': [blocker for blocker, _count in sorted(Counter([str(blocker) for item in health_items for blocker in list(item.get('top_remaining_blockers') or []) if blocker]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'environment_guard_ok_count': sum(int(item.get('environment_guard_ok_count') or 0) for item in health_items),
        'environment_guard_unmet_count': sum(int(item.get('environment_guard_unmet_count') or 0) for item in health_items),
        'top_executor_adapter_types': sorted({str(t) for item in health_items for t in (item.get('top_executor_adapter_types') or []) if t}),
        'top_executor_plugin_targets': list(dict.fromkeys([target for item in health_items for target in list(item.get('top_executor_plugin_targets') or [])]))[:5],
        'handoff_boundary_ready_count': health_payload.get('closure_counts', {}).get('handoff_boundary_ready', 0),
        'release_execution_requested_count': health_payload.get('closure_counts', {}).get('release_execution_requested', 0),
        'rollback_execution_requested_count': health_payload.get('closure_counts', {}).get('rollback_execution_requested', 0),
        'release_execution_receipt_recorded_count': health_payload.get('closure_counts', {}).get('release_execution_receipt_recorded', 0),
        'rollback_execution_receipt_recorded_count': health_payload.get('closure_counts', {}).get('rollback_execution_receipt_recorded', 0),
        'executor_readiness_gate_count': max(readiness_gate_counts) if readiness_gate_counts else 0,
        'executor_unmet_gate_count': min(readiness_unmet_counts) if readiness_unmet_counts else 0,
        'top_unmet_executor_gates': top_unmet_executor_gates,
        'executor_admission_available': any(bool(item.get('executor_admission_available')) for item in health_items),
        'go_no_go_available': any(bool(item.get('go_no_go_available')) for item in health_items),
        'rollout_gate_count': max(rollout_gate_counts) if rollout_gate_counts else 0,
        'rollout_unmet_count': min(rollout_unmet_counts) if rollout_unmet_counts else 0,
        'waiver_exception_count': sum(waiver_exception_counts),
        'overall_admission_state': admission_state_counter.most_common(1)[0][0] if admission_state_counter else None,
        'top_blocking_gates': top_blocking_gates,
        'executor_simulation_available_count': sum(int(item.get('executor_simulation_available_count') or 0) for item in health_items),
        'executor_simulation_pass_count': sum(int(item.get('executor_simulation_pass_count') or 0) for item in health_items),
        'executor_simulation_fail_count': sum(int(item.get('executor_simulation_fail_count') or 0) for item in health_items),
        'contract_compliance_available': any(bool(item.get('contract_compliance_available')) for item in health_items),
        'integration_rehearsal_available': any(bool(item.get('integration_rehearsal_available')) for item in health_items),
        'top_executor_contract_gaps': [gap for gap, _count in sorted(Counter([str(gap) for item in health_items for gap in list(item.get('top_executor_contract_gaps') or []) if gap]).items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
        'top_execution_handoff_targets': list(dict.fromkeys([target for item in health_items for target in list(item.get('top_execution_handoff_targets') or [])]))[:5],
        'top_command_plan_steps': list(dict.fromkeys([step for item in health_items for step in list(item.get('top_command_plan_steps') or [])]))[:5],
        'execution_request_requested_count': request_requested_count,
        'execution_request_acknowledged_count': request_acknowledged_count,
        'execution_request_accepted_count': request_accepted_count,
        'execution_request_declined_count': request_declined_count,
        'execution_request_expired_count': request_expired_count,
        'request_open_count': request_open_count,
        'request_inflight_count': request_inflight_count,
        'execution_request_reassigned_count': request_reassigned_count,
        'execution_request_escalated_count': request_escalated_count,
        'execution_request_retry_ready_count': request_retry_ready_count,
        'top_request_states': [state for state, _count in request_state_counter.most_common(5)],
        'top_pending_requests': top_pending_requests[:5],
        'recent_request_actions': request_actions[:8],
        'recent_request_transitions': request_transitions[:8],
        'recent_request_escalations': request_escalations[:8],
        'top_request_owners': [{'owner': owner, 'request_count': count} for owner, count in request_owner_counter.most_common(5) if owner],
        'executor_readiness_state': (
            'handoff_boundary_ready'
            if health_payload.get('closure_counts', {}).get('handoff_boundary_ready', 0)
            else 'dry_run_validated'
            if health_payload.get('closure_counts', {}).get('dry_run_available', 0)
            and health_payload.get('closure_counts', {}).get('release_execution_receipt_recorded', 0)
            and health_payload.get('closure_counts', {}).get('rollback_execution_receipt_recorded', 0)
            else 'contracts_ready_for_dry_run'
            if health_payload.get('closure_counts', {}).get('executor_contract_available', 0)
            else 'not_ready'
        ),
        'observation_refresh': observation_refresh,
        'observation_runtime': observation_runtime,
        'observation_pending_followup_count': observation_runtime.get('pending_followup_count', 0),
        'observation_timed_out_count': observation_runtime.get('timed_out_count', 0),
        'observation_active_count': observation_runtime.get('active_count', 0),
        'observation_overdue_count': observation_runtime.get('overdue_count', 0),
        'followup_queue_count': ((observation_runtime.get('followup_queue') or {}).get('queue_count', 0)),
        'followup_open_count': observation_runtime.get('followup_open_count', 0),
        'followup_in_progress_count': observation_runtime.get('followup_in_progress_count', 0),
        'followup_resolved_count': observation_runtime.get('followup_resolved_count', 0),
        'followup_closed_count': observation_runtime.get('followup_closed_count', 0),
        'followup_queue_status_counts': ((observation_runtime.get('followup_queue') or {}).get('status_counts', {})),
        'followup_queue_escalation_counts': ((observation_runtime.get('followup_queue') or {}).get('escalation_counts', {})),
        'followup_queue_routing_target_counts': ((observation_runtime.get('followup_queue') or {}).get('routing_target_counts', {})),
        'followup_queue_recommended_owner_counts': ((observation_runtime.get('followup_queue') or {}).get('recommended_owner_counts', {})),
        'followup_assigned_count': observation_runtime.get('followup_assigned_count', 0),
        'followup_unassigned_count': observation_runtime.get('followup_unassigned_count', 0),
        'followup_handoff_count': observation_runtime.get('followup_handoff_count', 0),
        'followup_backfilled_item_count': observation_runtime.get('followup_backfilled_item_count', 0),
        'followup_manual_classification_required_count': observation_runtime.get('followup_manual_classification_required_count', 0),
        'followup_resolution_category_counts': observation_runtime.get('followup_resolution_category_counts', {}),
        'followup_target_resolution_category_counts': observation_runtime.get('followup_target_resolution_category_counts', {}),
        'manual_classification_backlog_count': ((observation_resolution_review.get('manual_classification_backlog') or {}).get('count', 0)),
        'manual_classification_unresolved_count': ((observation_resolution_review.get('manual_classification_backlog') or {}).get('unresolved_count', 0)),
        'manual_classification_backlog_items': ((observation_resolution_review.get('manual_classification_backlog') or {}).get('items', [])),
        'manual_classification_unresolved_items': ((observation_resolution_review.get('manual_classification_backlog') or {}).get('unresolved_items', [])),
        'manual_classification_state_counts': ((observation_resolution_review.get('manual_classification_backlog') or {}).get('state_counts', {})),
        'followup_resolution_digest_available': observation_resolution_review.get('digest_available', False),
        'closure_theme_counts': observation_resolution_review.get('recent_closure_knowledge_themes', {}),
        'top_closure_themes': observation_resolution_review.get('top_closure_themes', {}),
        'followup_resolution_taxonomy_theme_counts': observation_resolution_review.get('resolution_taxonomy_theme_counts', {}),
        'recent_closure_knowledge_themes': observation_resolution_review.get('recent_closure_knowledge_themes', {}),
        'pattern_digest_available': observation_resolution_review.get('pattern_digest_available', False),
        'pattern_digest_counts': observation_resolution_review.get('pattern_digest_counts', {}),
        'pattern_digest_top': observation_resolution_review.get('pattern_digest_top', {}),
        'theme_contrast': observation_resolution_review.get('theme_contrast', {}),
        'rule_candidate_counts': observation_resolution_review.get('rule_candidate_counts', {}),
        'pattern_candidate_counts': observation_resolution_review.get('pattern_candidate_counts', {}),
        'top_rule_candidates': observation_resolution_review.get('top_rule_candidates', {}),
        'top_pattern_candidates': observation_resolution_review.get('top_pattern_candidates', {}),
        'knowledge_candidate_counts': observation_resolution_review.get('knowledge_candidate_counts', {}),
        'knowledge_candidate_items': observation_resolution_review.get('knowledge_candidate_items', []),
        'followup_resolution_review': observation_resolution_review,
        'rule_proposal_review': rule_proposal_review,
        'rule_proposal_count': rule_proposal_review.get('proposal_count', 0),
        'rule_proposal_pending_review_count': rule_proposal_review.get('pending_review_count', 0),
        'rule_proposal_accepted_count': rule_proposal_review.get('accepted_count', 0),
        'rule_proposal_rejected_count': rule_proposal_review.get('rejected_count', 0),
        'rule_proposal_state_counts': rule_proposal_review.get('proposal_state_counts', {}),
        'top_proposed_rules': rule_proposal_review.get('top_proposed_rules', []),
        'rule_proposal_digest_available': rule_proposal_review.get('digest_available', False),
        'rule_merge_candidate_count': rule_proposal_review.get('merge_candidate_count', 0),
        'rule_conflict_candidate_count': rule_proposal_review.get('conflict_candidate_count', 0),
        'rule_duplicate_candidate_count': rule_proposal_review.get('duplicate_candidate_count', 0),
        'top_rule_merge_items': rule_proposal_review.get('top_merge_items', []),
        'top_rule_conflict_items': rule_proposal_review.get('top_conflict_items', []),
        'top_rule_duplicate_items': rule_proposal_review.get('top_duplicate_items', []),
        'rule_conflict_review': rule_proposal_review.get('rule_conflict_review', {}),
        'accepted_rule_sink_items': rule_proposal_review.get('accepted_sink_items', []),
        'governed_rule_sink': governed_rule_sink,
        'rule_sink_ready_count': governed_rule_sink.get('sink_ready_count', 0),
        'written_rule_candidate_count': governed_rule_sink.get('written_count', 0),
        'exported_rule_candidate_count': governed_rule_sink.get('exported_count', 0),
        'rejected_rule_candidate_count': governed_rule_sink.get('rejected_count', 0),
        'governed_rule_state_counts': governed_rule_sink.get('state_counts', {}),
        'governed_rule_sink_target_counts': governed_rule_sink.get('sink_target_counts', {}),
        'top_written_rules': governed_rule_sink.get('top_written_rules', []),
        'local_rulebook_export': local_rulebook_export,
        'local_rulebook_exported_count': local_rulebook_export.get('exported_count', 0),
        'local_rulebook_already_exported_count': local_rulebook_export.get('already_exported_count', 0),
        'local_rulebook_blocked_count': local_rulebook_export.get('blocked_count', 0),
        'local_rulebook_item_count': local_rulebook_export.get('local_rulebook_item_count', 0),
        'local_rulebook_export_audit_available': local_rulebook_export.get('export_audit_available', False),
        'local_rulebook_export_status_counts': local_rulebook_export.get('export_status_counts', {}),
        'local_rulebook_duplicate_blocked_count': local_rulebook_export.get('duplicate_blocked_count', 0),
        'local_rulebook_active_rule_count': local_rulebook_export.get('active_rule_count', 0),
        'local_rulebook_inactive_rule_count': local_rulebook_export.get('inactive_rule_count', 0),
        'local_rulebook_archived_rule_count': local_rulebook_export.get('archived_rule_count', 0),
        'local_rulebook_merged_rule_count': local_rulebook_export.get('merged_rule_count', 0),
        'local_rulebook_superseded_rule_count': local_rulebook_export.get('superseded_rule_count', 0),
        'local_rulebook_consequence_state_counts': local_rulebook_export.get('consequence_state_counts', {}),
        'local_rulebook_merge_candidate_count': local_rulebook_export.get('merge_candidate_count', 0),
        'local_rulebook_conflict_candidate_count': local_rulebook_export.get('conflict_candidate_count', 0),
        'local_rulebook_conflict_state_counts': local_rulebook_export.get('conflict_state_counts', {}),
        'local_rulebook_conflict_open_count': local_rulebook_export.get('conflict_open_count', 0),
        'local_rulebook_conflict_reviewing_count': local_rulebook_export.get('conflict_reviewing_count', 0),
        'local_rulebook_conflict_resolved_count': local_rulebook_export.get('conflict_resolved_count', 0),
        'local_rulebook_recent_adjudications': local_rulebook_export.get('recent_adjudications', []),
        'local_rulebook_duplicate_candidate_count': local_rulebook_export.get('duplicate_candidate_count', 0),
        'merge_queue_count': local_rulebook_export.get('merge_queue_count', 0),
        'merge_queue_state_counts': local_rulebook_export.get('merge_queue_state_counts', {}),
        'merge_queue_open_count': local_rulebook_export.get('merge_queue_open_count', 0),
        'merge_queue_reviewing_count': local_rulebook_export.get('merge_queue_reviewing_count', 0),
        'merge_queue_accepted_count': local_rulebook_export.get('merge_queue_accepted_count', 0),
        'merge_queue_rejected_count': local_rulebook_export.get('merge_queue_rejected_count', 0),
        'top_exported_rules': local_rulebook_export.get('top_exported_rules', []),
        'top_merge_targets': local_rulebook_export.get('top_merge_targets', []),
        'top_supersede_suggestions': local_rulebook_export.get('top_supersede_suggestions', []),
        'top_supersede_candidates': local_rulebook_export.get('top_supersede_candidates', []),
        'top_merge_items': local_rulebook_export.get('top_merge_items', []),
        'top_conflict_items': local_rulebook_export.get('top_conflict_items', []),
        'recent_adjudications': local_rulebook_export.get('recent_adjudications', []),
        'conflict_resolution_type_counts': local_rulebook_export.get('conflict_resolution_type_counts', {}),
        'recent_consequence_updates': local_rulebook_export.get('recent_consequence_updates', []),
        'consequence_history_available': local_rulebook_export.get('consequence_history_available', False),
        'consequence_history_event_count': local_rulebook_export.get('consequence_history_event_count', 0),
        'recent_consequence_transitions': local_rulebook_export.get('recent_consequence_transitions', []),
        'transition_ledger_available': local_rulebook_export.get('transition_ledger_available', False),
        'transition_event_count': local_rulebook_export.get('transition_event_count', 0),
        'unique_semantic_event_count': local_rulebook_export.get('unique_semantic_event_count', 0),
        'digest_duplicate_semantic_event_count': local_rulebook_export.get('digest_duplicate_semantic_event_count', 0),
        'transition_duplicate_suppressed_count': local_rulebook_export.get('transition_duplicate_suppressed_count', 0),
        'transition_digest_review_available': local_rulebook_export.get('transition_digest_review_available', False),
        'recent_transition_events': local_rulebook_export.get('recent_transition_events', []),
        'recent_suppressed_events': local_rulebook_export.get('recent_suppressed_events', []),
        'top_transition_triggers': local_rulebook_export.get('top_transition_triggers', {}),
        'consistency_audit_available': local_rulebook_export.get('consistency_audit_available', False),
        'audit_scope_refinement_available': local_rulebook_export.get('audit_scope_refinement_available', False),
        'registry_sync_review_available': local_rulebook_export.get('registry_sync_review_available', False),
        'registry_sync_issue_count': local_rulebook_export.get('registry_sync_issue_count', 0),
        'sync_scope_exception_count': local_rulebook_export.get('sync_scope_exception_count', 0),
        'scope_exception_counts': local_rulebook_export.get('scope_exception_counts', {}),
        'recent_sync_issues': local_rulebook_export.get('recent_sync_issues', []),
        'recent_scope_exceptions': local_rulebook_export.get('recent_scope_exceptions', []),
        'archived_transition_count': local_rulebook_export.get('archived_transition_count', 0),
        'recent_archived_items': local_rulebook_export.get('recent_archived_items', []),
        'archive_policy_counts': local_rulebook_export.get('archive_policy_counts', {}),
        'archived_restorable_count': local_rulebook_export.get('archived_restorable_count', 0),
        'archived_reopened_count': local_rulebook_export.get('archived_reopened_count', 0),
        'restore_count': local_rulebook_export.get('restore_count', 0),
        'reopen_count': local_rulebook_export.get('reopen_count', 0),
        'revive_count': local_rulebook_export.get('revive_count', 0),
        'restore_state_counts': local_rulebook_export.get('restore_state_counts', {}),
        'shared_source_archived_count': local_rulebook_export.get('shared_source_archived_count', 0),
        'recent_restore_actions': local_rulebook_export.get('recent_restore_actions', []),
        'recent_restore_timeline': local_rulebook_export.get('recent_restore_timeline', []),
        'recent_archive_actions': local_rulebook_export.get('recent_archive_actions', []),
        'precedence_decision_count': local_rulebook_export.get('precedence_decision_count', 0),
        'precedence_override_counts': local_rulebook_export.get('precedence_override_counts', {}),
        'recent_precedence_decisions': local_rulebook_export.get('recent_precedence_decisions', []),
        'top_duplicate_items': local_rulebook_export.get('top_duplicate_items', []),
        'post_decision_linkage_count': local_rulebook_export.get('post_decision_linkage_count', 0),
        'merge_linked_count': local_rulebook_export.get('merge_linked_count', 0),
        'supersede_linked_count': local_rulebook_export.get('supersede_linked_count', 0),
        'conflict_adjudicated_linked_count': local_rulebook_export.get('conflict_adjudicated_linked_count', 0),
        'recent_decision_linkages': local_rulebook_export.get('recent_decision_linkages', []),
        'local_rulebook_governance_review': local_rulebook_governance_review,
        'recently_closed_followup_items': observation_runtime.get('recently_closed_followup_items', []),
        'top_pending_followup_items': ((observation_runtime.get('followup_queue') or {}).get('top_items', [])),
        'top_unresolved_followup_items': ((observation_runtime.get('followup_queue') or {}).get('top_unresolved_items', [])),
        'latest_attention_observations': observation_runtime.get('latest_attention_items', []),
        'pending_followup_examples': observation_runtime.get('pending_followup_examples', []),
        'adaptive_loop_summary': adaptive_loop_summary,
        'recent_ecosystem_learning': recent_learning_summary,
        'open_gap_summary': open_gap_summary,
        'recommended_focus_gap_id': open_gap_summary.get('top_gap_ids', [None])[0] if open_gap_summary.get('top_gap_ids') else None,
        'top_gap_titles': [item.get('title') for item in top_gap_items],
        'backfill_jobs_scanned': backfill.get('jobs_scanned', 0),
        'backfill_quality_count': backfill.get('quality_backfilled_count', 0),
        'backfill_formalization_count': backfill.get('formalization_backfilled_count', 0),
        'backfill_closure_count': backfill.get('closure_backfilled_count', 0),
        'followup_backfill_checked_count': followup_backfill.get('followups_checked', 0),
        'followup_backfill_changed_count': followup_backfill.get('changed_count', 0),
        'followup_backfill_manual_required_count': followup_backfill.get('manual_classification_required_count', 0),
        'followup_backfill_repaired_resolution_category_count': followup_backfill.get('repaired_resolution_category_count', 0),
        'followup_backfill_repaired_closure_audit_count': followup_backfill.get('repaired_closure_audit_count', 0),
        'lifecycle_bucket_counts': lifecycle_payload.get('bucket_counts', {}),
        'cycle_dir': str(cycle_dir),
        # Governance closeout bundle fields - adding to top level summary
        'governance_closeout_available': True,
        'governance_cutline_available': True,
        'residual_structural_blocker_count': len(governance_closeout_bundle.get('residual_structural_blocker_register', {}).get('items', [])),
        'residual_governance_gap_count': governance_closeout_bundle.get('governance_cutline_decision', {}).get('residual_governance_gap_count', 0),
        'next_phase_handoff_gate_available': governance_closeout_bundle.get('next_phase_handoff_gate', {}).get('next_phase_handoff_gate_available', False),
        'governance_closeout_review': governance_closeout_bundle.get('governance_closeout_review', {}),
        'residual_structural_blocker_register': governance_closeout_bundle.get('residual_structural_blocker_register', {}),
        'governance_cutline_decision': governance_closeout_bundle.get('governance_cutline_decision', {}),
        'next_phase_handoff_gate': governance_closeout_bundle.get('next_phase_handoff_gate', {}),
    }
    stage_card = build_stage_card(latest_cycle=summary, health=health_payload, recovery=recovery_payload, lifecycle=lifecycle_payload)
    stage_focus = stage_card.get('next_action_card', {}) or {}
    summary.update({
        'recommended_focus_title': stage_focus.get('title'),
        'recommended_focus_label': stage_focus.get('focus_label'),
        'recommended_focus_dominant_state': stage_focus.get('dominant_state'),
        'recommended_focus_blocker_counts': stage_focus.get('blocker_counts', {}),
        'recommended_focus_state_counts': stage_focus.get('state_counts', {}),
    })
    open_gap_summary = _enrich_open_gap_summary_with_stage_focus(open_gap_summary, stage_card)
    summary['open_gap_summary'] = open_gap_summary
    top_gap_items = (open_gap_summary.get('items', []) or [])[:3]
    summary['top_gap_titles'] = [item.get('title') for item in top_gap_items]

    priority_value_map = {'high': '高', 'medium': '中', 'low': '低'}
    lines = [
        '# 运行时调度汇总报告',
        '',
        f"- 周期编号: {summary['cycle_id']}",
        f"- 生成时间: {summary['generated_at']}",
        f"- 任务总数: {summary['job_count']}",
        f"- 陈旧任务数: {summary['stale_count']}",
        f"- 已修复数: {summary['healed_count']}",
        f"- 已创建重试数: {summary['retry_created_count']}",
        f"- 治理动作数: {summary['governance_action_count']}",
        f"- 平均质量分: {summary['quality_average_score']}",
        f"- 活跃 observation 数: {summary['observation_active_count']}",
        f"- observation 待人工跟进数: {summary['observation_pending_followup_count']}",
        f"- observation 超时数: {summary['observation_timed_out_count']}",
        f"- observation 逾期数: {summary['observation_overdue_count']}",
        f"- follow-up queue 数: {summary['followup_queue_count']}",
        f"- follow-up escalation 分布: {_render_report_value(summary['followup_queue_escalation_counts'])}",
        f"- follow-up routing 分布: {_render_report_value(summary['followup_queue_routing_target_counts'])}",
        f"- follow-up 回填修复数: {summary['followup_backfill_changed_count']}",
        f"- follow-up 待人工补分类数: {summary['followup_manual_classification_required_count']}",
        f"- manual classification backlog 数: {summary['manual_classification_backlog_count']}",
        f"- manual classification backlog 未解决数: {summary['manual_classification_unresolved_count']}",
        f"- resolution insight digest 可用: {_render_report_value(summary['followup_resolution_digest_available'])}",
        f"- closure theme counts: {_render_report_value(summary['closure_theme_counts'])}",
        f"- top closure themes: {_render_report_value(summary['top_closure_themes'])}",
        f"- recent closure knowledge themes: {_render_report_value(summary['recent_closure_knowledge_themes'])}",
        f"- resolution taxonomy themes: {_render_report_value(summary['followup_resolution_taxonomy_theme_counts'])}",
        f"- pattern digest 可用: {_render_report_value(summary['pattern_digest_available'])}",
        f"- top pattern digest: {_render_report_value(summary['pattern_digest_top'])}",
        f"- top rule candidates: {_render_report_value(summary['top_rule_candidates'])}",
        f"- top pattern candidates: {_render_report_value(summary['top_pattern_candidates'])}",
        f"- rule proposal digest 可用: {_render_report_value(summary['rule_proposal_digest_available'])}",
        f"- rule proposal count: {summary['rule_proposal_count']}",
        f"- rule proposal pending review: {summary['rule_proposal_pending_review_count']}",
        f"- rule proposal accepted / rejected: {summary['rule_proposal_accepted_count']} / {summary['rule_proposal_rejected_count']}",
        f"- rule proposal state counts: {_render_report_value(summary['rule_proposal_state_counts'])}",
        f"- rule merge/conflict/duplicate candidates: {summary['rule_merge_candidate_count']} / {summary['rule_conflict_candidate_count']} / {summary['rule_duplicate_candidate_count']}",
        f"- rule sink-ready count: {summary['rule_sink_ready_count']}",
        f"- written rule candidate count: {summary['written_rule_candidate_count']}",
        f"- governed rule state counts: {_render_report_value(summary['governed_rule_state_counts'])}",
        f"- local rulebook exported count: {summary['local_rulebook_exported_count']}",
        f"- local rulebook item count: {summary['local_rulebook_item_count']}",
        f"- local rulebook export audit available: {_render_report_value(summary['local_rulebook_export_audit_available'])}",
        f"- local rulebook export status counts: {_render_report_value(summary['local_rulebook_export_status_counts'])}",
        f"- local rulebook active/inactive/archived: {summary['local_rulebook_active_rule_count']} / {summary['local_rulebook_inactive_rule_count']} / {summary['local_rulebook_archived_rule_count']}",
        f"- archive policy counts: {summary['archive_policy_counts']}",
        f"- archived restorable/reopened: {summary['archived_restorable_count']} / {summary['archived_reopened_count']}",
        f"- local rulebook merged/superseded/duplicate_blocked: {summary['local_rulebook_merged_rule_count']} / {summary['local_rulebook_superseded_rule_count']} / {summary['local_rulebook_duplicate_blocked_count']}",
        f"- local rulebook consequence states: {_render_report_value(summary['local_rulebook_consequence_state_counts'])}",
        f"- local rulebook merge/conflict/duplicate-like candidates: {summary['local_rulebook_merge_candidate_count']} / {summary['local_rulebook_conflict_candidate_count']} / {summary['local_rulebook_duplicate_candidate_count']}",
        f"- local rulebook conflict lifecycle: {_render_report_value(summary['local_rulebook_conflict_state_counts'])}",
        f"- transition ledger semantic unique/duplicate/suppressed: {summary['unique_semantic_event_count']} / {summary['digest_duplicate_semantic_event_count']} / {summary['transition_duplicate_suppressed_count']}",
        f"- registry sync issue count: {summary['registry_sync_issue_count']} | sync scope exceptions={_render_report_value(summary['sync_scope_exception_count'])} | audit available={_render_report_value(summary['consistency_audit_available'])} | scope refinement={_render_report_value(summary['audit_scope_refinement_available'])} | review available={_render_report_value(summary['registry_sync_review_available'])}",
        f"- recent sync issues: {_render_report_value(summary['recent_sync_issues'])}",
        f"- recent scope exceptions: {_render_report_value(summary['recent_scope_exceptions'])}",
        f"- post-decision linkage count: {summary['post_decision_linkage_count']} (merge={summary['merge_linked_count']} / supersede={summary['supersede_linked_count']} / conflict={summary['conflict_adjudicated_linked_count']})",
        f"- conflict resolution types: {_render_report_value(summary['conflict_resolution_type_counts'])}",
        f"- recent consequence updates: {_render_report_value(summary['recent_consequence_updates'])}",
        f"- top proposed rules: {_render_report_value(summary['top_proposed_rules'])}",
        f"- top written rules: {_render_report_value(summary['top_written_rules'])}",
        f"- top exported rules: {_render_report_value(summary['top_exported_rules'])}",
        f"- top supersede candidates: {_render_report_value(summary['top_supersede_candidates'])}",
        f"- top merge items: {_render_report_value(summary['top_merge_items'])}",
        f"- top conflict items: {_render_report_value(summary['top_conflict_items'])}",
        f"- recent adjudications: {_render_report_value(summary['recent_adjudications'])}",
        f"- top duplicate-like items: {_render_report_value(summary['top_duplicate_items'])}",
        f"- release / rollback theme contrast: {_render_report_value(summary['theme_contrast'])}",
        f"- 当前推荐聚焦缺口: {GAP_ID_ZH.get(summary['recommended_focus_gap_id'], summary['recommended_focus_gap_id'])}",
        f"- 当前聚焦标题: {summary.get('recommended_focus_title')}",
        f"- 当前卡点类型: {OFFICIAL_RELEASE_FOCUS_LABEL_ZH.get(summary.get('recommended_focus_label'), summary.get('recommended_focus_label'))}",
        f"- 当前主导状态: {OFFICIAL_RELEASE_STATE_ZH.get(summary.get('recommended_focus_dominant_state'), summary.get('recommended_focus_dominant_state'))}",
        f"- 当前顶部缺口标题: {_render_report_value([GAP_ID_ZH.get(item.get('gap_id'), item.get('title')) for item in top_gap_items])}",
        '',
        '## 当前推荐聚焦',
    ]
    if top_gap_items:
        top_item = top_gap_items[0]
        lines.extend([
            f"- 缺口编号: {top_item.get('gap_id')}",
            f"- 优先级: {priority_value_map.get(top_item.get('priority'), top_item.get('priority'))}",
            f"- 缺口标题: {GAP_ID_ZH.get(top_item.get('gap_id'), top_item.get('title'))}",
            f"- 当前原因: {top_item.get('why_now_detailed') or top_item.get('current_focus_summary') or top_item.get('rationale')}",
            f"- 下一步动作: {_render_report_value(top_item.get('recommended_actions_detailed') or top_item.get('next_step'))}",
            f"- 阶段卡聚焦标题: {stage_focus.get('title')}",
            f"- 阶段卡卡点类型: {stage_focus.get('focus_label_zh') or OFFICIAL_RELEASE_FOCUS_LABEL_ZH.get(stage_focus.get('focus_label'), stage_focus.get('focus_label'))}",
            f"- 阶段卡主导状态: {stage_focus.get('dominant_state_zh') or OFFICIAL_RELEASE_STATE_ZH.get(stage_focus.get('dominant_state'), stage_focus.get('dominant_state'))}",
            f"- 阶段卡阻塞分布: {_render_report_value(stage_focus.get('blocker_counts_zh') or stage_focus.get('blocker_counts'))}",
            f"- 阶段卡状态分布: {_render_report_value(stage_focus.get('state_counts_zh') or stage_focus.get('state_counts'))}",
            '',
            '## 运行时信号',
        ])
    else:
        lines.extend([
            '- 当前没有登记中的聚焦缺口',
            '',
            '## 运行时信号',
        ])
    lines.extend([
        f"- 可恢复性分布: {_render_report_value(summary['recoverability_counts'])}",
        f"- 质量等级分布: {_render_report_value(summary['quality_grade_counts'])}",
        f"- 正式收口状态分布: {_render_report_value(summary['formalization_state_counts'])}",
        f"- 收口统计: {_render_report_value(summary['closure_counts'])}",
        f"- observation 刷新摘要: {_render_report_value(summary['observation_refresh'])}",
        f"- observation 运行汇总: {_render_report_value(summary['observation_runtime'])}",
        f"- follow-up queue 顶部条目: {_render_report_value(summary['top_pending_followup_items'])}",
        f"- 自适应流转摘要: {_render_report_value(summary['adaptive_loop_summary'])}",
        f"- 近期生态经验摘要: {_render_report_value(summary['recent_ecosystem_learning'])}",
        f"- 缺口汇总: {_render_report_value(summary['open_gap_summary'])}",
        f"- 回填扫描任务数: {summary['backfill_jobs_scanned']}",
        f"- 回填质量产物数: {summary['backfill_quality_count']}",
        f"- 回填正式收口产物数: {summary['backfill_formalization_count']}",
        f"- 回填收口链产物数: {summary['backfill_closure_count']}",
        f"- 生命周期分桶分布: {summary['lifecycle_bucket_counts']}",
        '',
        '## 顶部缺口列表',
    ])
    if top_gap_items:
        for item in top_gap_items:
            focus_summary = item.get('current_focus_summary')
            if focus_summary:
                lines.append(
                    f"- 缺口={GAP_ID_ZH.get(item.get('gap_id'), item.get('gap_id'))} | 优先级={priority_value_map.get(item.get('priority'), item.get('priority'))} | 标题={GAP_ID_ZH.get(item.get('gap_id'), item.get('title'))} | 下一步={_render_report_value(item.get('recommended_actions_detailed') or item.get('next_step'))} | 当前说明={focus_summary} | 阻塞分布={_render_report_value(item.get('blocker_counts_zh') or item.get('blocker_counts'))}"
                )
            else:
                lines.append(
                    f"- 缺口={GAP_ID_ZH.get(item.get('gap_id'), item.get('gap_id'))} | 优先级={priority_value_map.get(item.get('priority'), item.get('priority'))} | 标题={GAP_ID_ZH.get(item.get('gap_id'), item.get('title'))} | 下一步={_render_report_value(item.get('recommended_actions_detailed') or item.get('next_step'))}"
                )
    else:
        lines.append('- 当前周期没有正式登记的顶部缺口')
    lines.extend(['', '## 已处理的陈旧任务'])
    if healed:
        for item in healed:
            lines.append(
                f"- 任务={item['task_id']} | 可恢复性={item.get('recoverability')} | 动作={item.get('recommended_action')} | 重试任务={item.get('retry_task_id')} | 原因={item.get('reason')}"
            )
    else:
        lines.append('- 当前周期没有需要处理的陈旧任务')
    (cycle_dir / 'cycle_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    _write_json(cycle_dir / 'cycle_summary.json', summary)
    _write_json(cycle_dir / 'open_gap_summary.json', open_gap_summary)
    _write_json(cycle_dir / 'ecosystem_stage_card.json', stage_card)
    _write_json(cycle_dir / 'rule_candidate_review.json', rule_proposal_review)
    _write_json(cycle_dir / 'rule_conflict_review.json', summary.get('rule_conflict_review', {}))
    (cycle_dir / 'rule_conflict_review.md').write_text((rule_proposal_review.get('digest_markdown') or '') + '\n', encoding='utf-8')
    _write_json(cycle_dir / 'governed_rule_candidates.json', governed_rule_sink)
    _write_json(cycle_dir / 'local_rulebook_export.json', local_rulebook_export)
    _write_json(cycle_dir / 'local_rulebook_governance_review.json', local_rulebook_governance_review)
    _write_json(cycle_dir / 'rule_decision_linkage_review.json', _load_json(STATE_ROOT / 'rule_decision_linkage_review.json'))
    write_rule_proposal_review_markdown(rule_proposal_review, cycle_dir / 'rule_candidate_review.md')
    (cycle_dir / 'ecosystem_stage_card.md').write_text(write_stage_card_markdown(stage_card), encoding='utf-8')

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(STATE_ROOT / 'latest_cycle.json', summary)
    _write_json(STATE_ROOT / 'latest_health_dashboard.json', health_payload)
    _write_json(STATE_ROOT / 'latest_recovery_dashboard.json', recovery_payload)
    _write_json(STATE_ROOT / 'latest_lifecycle_dashboard.json', lifecycle_payload)
    _write_json(STATE_ROOT / 'latest_adaptive_loop_summary.json', adaptive_loop_summary)
    _write_json(STATE_ROOT / 'latest_recent_ecosystem_learning.json', recent_learning_summary)
    _write_json(STATE_ROOT / 'latest_open_gap_summary.json', open_gap_summary)
    _write_json(STATE_ROOT / 'latest_observation_refresh.json', observation_refresh)
    _write_json(STATE_ROOT / 'latest_observation_runtime_summary.json', observation_runtime)
    _write_json(STATE_ROOT / 'latest_followup_backfill_summary.json', followup_backfill)
    _write_json(STATE_ROOT / 'latest_followup_resolution_review.json', observation_resolution_review)
    write_followup_resolution_review_markdown(observation_resolution_review, STATE_ROOT / 'latest_followup_resolution_review.md')
    _write_json(STATE_ROOT / 'latest_rule_proposal_review.json', rule_proposal_review)
    _write_json(STATE_ROOT / 'latest_rule_conflict_review.json', summary.get('rule_conflict_review', {}))
    (STATE_ROOT / 'latest_rule_conflict_review.md').write_text((rule_proposal_review.get('digest_markdown') or '') + '\n', encoding='utf-8')
    _write_json(STATE_ROOT / 'latest_governed_rule_candidates.json', governed_rule_sink)
    _write_json(STATE_ROOT / 'latest_local_rulebook_export.json', local_rulebook_export)
    _write_json(STATE_ROOT / 'latest_local_rulebook_governance_review.json', local_rulebook_governance_review)
    _write_json(STATE_ROOT / 'latest_rule_decision_linkage_review.json', _load_json(STATE_ROOT / 'rule_decision_linkage_review.json'))
    write_rule_proposal_review_markdown(rule_proposal_review, STATE_ROOT / 'latest_rule_proposal_review.md')
    _write_json(STATE_ROOT / 'latest_pending_followup_queue.json', (observation_runtime.get('followup_queue') or {}))
    _write_json(STATE_ROOT / 'latest_stage_card.json', stage_card)
    (STATE_ROOT / 'latest_cycle.md').write_text((cycle_dir / 'cycle_summary.md').read_text(encoding='utf-8'), encoding='utf-8')
    (STATE_ROOT / 'latest_stage_card.md').write_text(write_stage_card_markdown(stage_card), encoding='utf-8')

    _append_event(
        'cycle_completed',
        cycle_id=cycle_id,
        job_count=summary['job_count'],
        stale_count=summary['stale_count'],
        healed_count=summary['healed_count'],
        retry_created_count=summary['retry_created_count'],
        governance_action_count=summary['governance_action_count'],
    )
    return summary


def run_loop(*, interval_seconds: int, jobs_root: str | Path = JOBS_ROOT, max_age_minutes: int = 30, auto_retry: bool = False, retry_requested_by: str = 'worker-runtime-scheduler', max_cycles: int = 0, backfill_missing: bool = True) -> dict[str, Any]:
    executed = 0
    last_summary: dict[str, Any] | None = None
    _append_event('loop_started', interval_seconds=interval_seconds, max_cycles=max_cycles, auto_retry=auto_retry, backfill_missing=backfill_missing)
    while True:
        last_summary = run_cycle(
            jobs_root=jobs_root,
            max_age_minutes=max_age_minutes,
            auto_retry=auto_retry,
            retry_requested_by=retry_requested_by,
            backfill_missing=backfill_missing,
        )
        executed += 1
        if max_cycles and executed >= max_cycles:
            break
        time.sleep(max(1, int(interval_seconds)))
    _append_event('loop_completed', executed_cycles=executed, last_cycle_id=(last_summary or {}).get('cycle_id'))
    return last_summary or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    run_once_p = sub.add_parser('run-once')
    run_once_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    run_once_p.add_argument('--max-age-minutes', type=int, default=30)
    run_once_p.add_argument('--auto-retry', action='store_true')
    run_once_p.add_argument('--retry-requested-by', default='worker-runtime-scheduler')
    run_once_p.add_argument('--no-backfill-missing', action='store_true')

    loop_p = sub.add_parser('loop')
    loop_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    loop_p.add_argument('--max-age-minutes', type=int, default=30)
    loop_p.add_argument('--auto-retry', action='store_true')
    loop_p.add_argument('--retry-requested-by', default='worker-runtime-scheduler')
    loop_p.add_argument('--interval-seconds', type=int, default=300)
    loop_p.add_argument('--max-cycles', type=int, default=0)
    loop_p.add_argument('--no-backfill-missing', action='store_true')

    status_p = sub.add_parser('status')
    status_p.add_argument('--state-root', default=str(STATE_ROOT))

    args = parser.parse_args()
    if args.action == 'run-once':
        summary = run_cycle(
            jobs_root=args.jobs_root,
            max_age_minutes=args.max_age_minutes,
            auto_retry=args.auto_retry,
            retry_requested_by=args.retry_requested_by,
            backfill_missing=not args.no_backfill_missing,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.action == 'loop':
        summary = run_loop(
            interval_seconds=args.interval_seconds,
            jobs_root=args.jobs_root,
            max_age_minutes=args.max_age_minutes,
            auto_retry=args.auto_retry,
            retry_requested_by=args.retry_requested_by,
            max_cycles=args.max_cycles,
            backfill_missing=not args.no_backfill_missing,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    state_root = Path(args.state_root)
    latest = state_root / 'latest_cycle.json'
    if latest.exists():
        print(latest.read_text(encoding='utf-8'))
    else:
        print(json.dumps({'status': 'no_scheduler_state'}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
