#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path('/home/admin/.openclaw/workspace/master')
STATE_ROOT = ROOT / 'reports' / 'worker-runtime' / 'state'

ALLOWED_STATES = {'draft', 'proposed', 'reviewed', 'accepted', 'rejected'}
SINK_ALLOWED_STATES = {'pending', 'written', 'exported', 'rejected'}
EXPORT_ALLOWED_STATUSES = {'exported', 'already_exported', 'blocked', 'duplicate_blocked'}
CONFLICT_ALLOWED_STATES = {'open', 'reviewing', 'resolved', 'rejected', 'superseded'}
CONFLICT_ALLOWED_RESOLUTIONS = {'merge', 'supersede', 'keep_both', 'reject_new', 'reject_old', 'defer'}
MERGE_QUEUE_ALLOWED_STATES = {'open', 'reviewing', 'accepted', 'rejected', 'superseded'}
PRECEDENCE_PRIORITY = {
    'duplicate': 400,
    'conflict': 300,
    'supersede': 200,
    'merge': 100,
}
RULE_CONSEQUENCE_STATES = {
    'active',
    'reviewing',
    'inactive_merged',
    'inactive_superseded',
    'inactive_conflict_rejected',
    'archived',
    'duplicate_blocked',
}
ACTION_STATE = {
    'propose': 'proposed',
    'review': 'reviewed',
    'accept': 'accepted',
    'reject': 'rejected',
    'reopen': 'proposed',
}


def _now() -> str:
    return datetime.now().astimezone().isoformat()



def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}



def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path



def _render(value: Any) -> str:
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, dict):
        if not value:
            return '无'
        return '；'.join(f'{k}={v}' for k, v in value.items())
    if isinstance(value, list):
        if not value:
            return '无'
        return '；'.join(_render(item) if isinstance(item, (dict, list, bool)) else str(item) for item in value)
    return '无' if value in (None, '', []) else str(value)



def _registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_proposal_review_registry.json'



def _normalize_sink_target(candidate_key: str, sink_target: str = '') -> str:
    sink = str(sink_target or '').strip()
    if sink:
        return sink
    if candidate_key.startswith('pattern:'):
        return 'knowledge_candidate'
    return 'rulebook_candidate'



def _proposal_id(candidate_key: str) -> str:
    digest = hashlib.sha1(candidate_key.encode('utf-8')).hexdigest()[:10]
    return f'proposal-{digest}'


def _sink_registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'accepted_rule_registry.json'


def _conflict_registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_conflict_registry.json'


def _governed_candidates_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'governed_rule_candidates.json'


def _governed_artifact_dir(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'governed-rule-artifacts'


def _local_rulebook_registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'local_rulebook_registry.json'


def _local_rulebook_export_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'local_rulebook_export.json'


def _local_rulebook_export_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'local_rulebook_export.md'


def _local_rulebook_export_audit_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'local_rulebook_export_audit.json'


def _merge_queue_registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'merge_queue_registry.json'


def _merge_target_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'latest_merge_target_review.json'


def _merge_target_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'latest_merge_target_review.md'


def _local_rulebook_artifact_dir(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'governed-rulebook'


def _rule_consequence_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_consequence_review.json'


def _rule_consequence_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_consequence_review.md'


def _archive_audit_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_audit_registry.json'


def _archive_policy_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_policy_review.json'


def _archive_policy_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_policy_review.md'


def _archive_restore_registry_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_restore_registry.json'


def _archive_restore_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_restore_review.json'


def _archive_restore_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_restore_review.md'


def _rule_precedence_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_precedence_review.json'


def _rule_precedence_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_precedence_review.md'


def _normalize_sink_state(value: str = '') -> str:
    state = str(value or '').strip().lower()
    return state if state in SINK_ALLOWED_STATES else 'pending'




def _candidate_topic_key(candidate_key: str) -> str:
    parts = [part for part in str(candidate_key or '').split(':') if part]
    if len(parts) >= 3:
        return parts[-1]
    if len(parts) >= 2:
        return parts[1]
    return str(candidate_key or 'unknown')


def _relation_key(candidate_kind: str, candidate_key: str) -> str:
    topic = _candidate_topic_key(candidate_key)
    kind = str(candidate_kind or 'rule')
    return f'{kind}:{topic}'


def _semantic_text(candidate_key: str) -> str:
    parts = [part for part in str(candidate_key or '').split(':') if part]
    if len(parts) >= 2:
        parts = parts[1:]
    text = ' '.join(parts).replace('_', ' ').replace('|', ' ').replace('-', ' ')
    return re.sub(r'\s+', ' ', text).strip().lower()


_STOPWORDS = {'theme', 'taxonomy', 'pattern', 'rule', 'target', 'category'}
_NEGATIVE_TOKENS = {'avoid', 'block', 'reject', 'disable', 'deny', 'prevent', 'skip', 'stop', 'without', 'fail', 'failed', 'rollback'}
_POSITIVE_TOKENS = {'prefer', 'allow', 'accept', 'enable', 'require', 'promote', 'use', 'with', 'pass', 'success', 'release'}


def _semantic_tokens(candidate_key: str) -> list[str]:
    raw = re.findall(r'[a-z0-9]+', _semantic_text(candidate_key))
    return [token for token in raw if token and token not in _STOPWORDS]


def _semantic_group_key(candidate_kind: str, candidate_key: str) -> str:
    tokens = _semantic_tokens(candidate_key)
    core = [token for token in tokens if token not in _NEGATIVE_TOKENS and token not in _POSITIVE_TOKENS]
    if not core:
        core = tokens or [_candidate_topic_key(candidate_key)]
    return f"{str(candidate_kind or 'rule')}:{'-'.join(core[:4])}"


def _token_similarity(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / max(len(left_set | right_set), 1)


def _semantic_reason(left: dict[str, Any], right: dict[str, Any], *, relation: str, similarity: float) -> str:
    base = f"semantic_group={left.get('semantic_group_key')} similarity={similarity:.2f}"
    if relation == 'conflict':
        return base + ' polarity_opposes'
    if relation == 'duplicate_like':
        return base + ' wording_is_highly_similar'
    return base + ' same_topic_candidate_can_merge_or_supersede'


def _detect_pair_relation(left: dict[str, Any], right: dict[str, Any]) -> tuple[str | None, str | None, float]:
    left_group = left.get('semantic_group_key')
    right_group = right.get('semantic_group_key')
    left_tokens = list(left.get('semantic_tokens') or [])
    right_tokens = list(right.get('semantic_tokens') or [])
    similarity = _token_similarity(left_tokens, right_tokens)
    if not left_group or left_group != right_group:
        return None, None, similarity
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    left_negative = bool(left_set & _NEGATIVE_TOKENS)
    right_negative = bool(right_set & _NEGATIVE_TOKENS)
    left_positive = bool(left_set & _POSITIVE_TOKENS)
    right_positive = bool(right_set & _POSITIVE_TOKENS)
    if (left_negative and right_positive) or (right_negative and left_positive):
        return 'conflict_candidate', _semantic_reason(left, right, relation='conflict', similarity=similarity), similarity
    if left.get('candidate_key') == right.get('candidate_key') or similarity >= 0.74:
        return 'duplicate_candidate', _semantic_reason(left, right, relation='duplicate_like', similarity=similarity), similarity
    return 'merge_candidate', _semantic_reason(left, right, relation='merge', similarity=similarity), similarity


def _content_fingerprint(*, candidate_kind: str, candidate_key: str, source_targets: dict[str, Any], source_themes: dict[str, Any], source_patterns: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    canonical = {
        'candidate_kind': candidate_kind,
        'candidate_key': str(candidate_key or ''),
        'topic_key': _candidate_topic_key(candidate_key),
        'source_targets': source_targets or {},
        'source_themes': source_themes or {},
        'source_patterns': source_patterns or {},
        'evidence_pairs': [
            {
                'task_id': item.get('task_id'),
                'execution_target': item.get('execution_target'),
                'resolution_category': item.get('resolution_category'),
                'resolution_taxonomy': item.get('resolution_taxonomy'),
                'pattern_key': item.get('pattern_key'),
            }
            for item in list(evidence or [])
        ],
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def _version_string(revision: int) -> str:
    return f'r{max(1, int(revision or 1))}'

def _artifact_relpath(path: Path, *, state_root: Path) -> str:
    try:
        return str(path.relative_to(state_root))
    except ValueError:
        return str(path)


def _conflict_id(left_proposal_id: str, right_proposal_id: str, semantic_group_key: str = '') -> str:
    ordered = sorted([str(left_proposal_id or ''), str(right_proposal_id or '')])
    seed = '|'.join(ordered + [str(semantic_group_key or '')])
    return f"conflict-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:10]}"


def _merge_candidate_id(source_rule_id: str, target_rule_id: str, relation_type: str, semantic_group_key: str = '') -> str:
    seed = '|'.join([str(source_rule_id or ''), str(target_rule_id or ''), str(relation_type or ''), str(semantic_group_key or '')])
    return f"merge-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:10]}"


def _priority_bucket(score: float) -> str:
    if score >= 85:
        return 'critical'
    if score >= 70:
        return 'high'
    if score >= 50:
        return 'medium'
    return 'low'


def _merge_queue_state_rank(state: str) -> int:
    return {'open': 0, 'reviewing': 1, 'accepted': 2, 'rejected': 3, 'superseded': 4}.get(str(state or '').strip().lower(), 9)


def _build_merge_queue_registry(*, local_items: dict[str, Any], cycle_id: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    registry = _load_json(_merge_queue_registry_path(state_root))
    existing_items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    tracked_items = {
        str(k): v for k, v in (local_items or {}).items()
        if isinstance(v, dict) and v.get('proposal_id') and str(v.get('status') or '') in {'active', 'inactive_superseded', 'duplicate_blocked'}
    }

    def _priority_score(*, source: dict[str, Any], target: dict[str, Any], similarity: float, relation_type: str) -> tuple[int, list[str]]:
        score = round(float(similarity or 0) * 100)
        reasons: list[str] = []
        shared_sources = sorted(set((source.get('source_targets') or {}).keys()) & set((target.get('source_targets') or {}).keys()))
        if shared_sources:
            score += min(12, len(shared_sources) * 4)
            reasons.append(f"shared_sources={','.join(shared_sources)}")
        if (source.get('relation_key') or '') == (target.get('relation_key') or ''):
            score += 18
            reasons.append('same_relation_key')
        if relation_type == 'supersede':
            score += 20
            reasons.append('explicit_supersede_chain')
        elif relation_type == 'merge':
            score += 8
            reasons.append('semantic_merge_candidate')
        score += min(10, int(source.get('evidence_count', 0) or 0))
        if str(target.get('status') or '') == 'active':
            score += 6
            reasons.append('target_active')
        if str(source.get('status') or '') in {'superseded', 'inactive_superseded'}:
            score -= 12
            reasons.append('source_already_superseded')
        return max(score, 0), reasons

    staged_items: dict[str, Any] = {}
    for source_id, source in tracked_items.items():
        for target_id in list(source.get('supersedes', []) or []):
            target = tracked_items.get(str(target_id), {}) if isinstance(tracked_items.get(str(target_id)), dict) else {}
            if not target:
                continue
            similarity = 1.0 if (source.get('relation_key') or '') == (target.get('relation_key') or '') else _token_similarity(list(source.get('semantic_tokens') or []), list(target.get('semantic_tokens') or []))
            priority_score, extra_reasons = _priority_score(source=source, target=target, similarity=similarity, relation_type='supersede')
            candidate_id = _merge_candidate_id(source_id, target_id, 'supersede', str(source.get('semantic_group_key') or ''))
            existing = existing_items.get(candidate_id, {}) if isinstance(existing_items.get(candidate_id), dict) else {}
            review_state = str(existing.get('review_state') or 'accepted').strip().lower()
            if review_state not in MERGE_QUEUE_ALLOWED_STATES:
                review_state = 'accepted'
            combined_reasons = [f"similarity={similarity:.2f}", source.get('decision_note') or 'supersede_from_local_rulebook_revision'] + extra_reasons
            staged_items[candidate_id] = {
                'candidate_id': candidate_id,
                'merge_id': candidate_id,
                'relation_type': 'supersede',
                'source_rule': source_id,
                'target_rule': target_id,
                'suggested_target': target_id,
                'suggested_target_rule': target_id,
                'source_candidate_key': source.get('candidate_key'),
                'target_candidate_key': target.get('candidate_key'),
                'similarity': round(similarity, 4),
                'reason': '; '.join(filter(None, combined_reasons)),
                'priority_score': priority_score,
                'priority': _priority_bucket(priority_score),
                'review_state': review_state,
                'first_seen_cycle_id': existing.get('first_seen_cycle_id') or cycle_id,
                'last_seen_cycle_id': cycle_id,
                'reviewer': existing.get('reviewer'),
                'reviewed_at': existing.get('reviewed_at'),
                'decision_note': existing.get('decision_note') or 'auto-linked from supersede chain',
                'governance_history': list(existing.get('governance_history', []) or []),
                'source_targets': source.get('source_targets', {}),
                'target_source_targets': target.get('source_targets', {}),
                'source_status': source.get('status'),
                'target_status': target.get('status'),
                'semantic_group_key': source.get('semantic_group_key') or target.get('semantic_group_key'),
            }

        for peer in list(source.get('merge_candidates', []) or []):
            target_id = str(peer.get('proposal_id') or '')
            target = tracked_items.get(target_id, {}) if isinstance(tracked_items.get(target_id), dict) else {}
            if not target or source_id == target_id:
                continue
            similarity = float(peer.get('similarity', 0) or 0)
            priority_score, extra_reasons = _priority_score(source=source, target=target, similarity=similarity, relation_type='merge')
            candidate_id = _merge_candidate_id(source_id, target_id, 'merge', str(source.get('semantic_group_key') or ''))
            existing = existing_items.get(candidate_id, {}) if isinstance(existing_items.get(candidate_id), dict) else {}
            review_state = str(existing.get('review_state') or 'open').strip().lower()
            if review_state not in MERGE_QUEUE_ALLOWED_STATES:
                review_state = 'open'
            combined_reasons = [peer.get('reason') or source.get('merge_reason') or 'semantic_merge_candidate', f"similarity={similarity:.2f}"] + extra_reasons
            staged_items[candidate_id] = {
                'candidate_id': candidate_id,
                'merge_id': candidate_id,
                'relation_type': 'merge',
                'source_rule': source_id,
                'target_rule': target_id,
                'suggested_target': target_id,
                'suggested_target_rule': target_id,
                'source_candidate_key': source.get('candidate_key'),
                'target_candidate_key': target.get('candidate_key'),
                'similarity': round(similarity, 4),
                'reason': '; '.join(filter(None, combined_reasons)),
                'priority_score': priority_score,
                'priority': _priority_bucket(priority_score),
                'review_state': review_state,
                'first_seen_cycle_id': existing.get('first_seen_cycle_id') or cycle_id,
                'last_seen_cycle_id': cycle_id,
                'reviewer': existing.get('reviewer'),
                'reviewed_at': existing.get('reviewed_at'),
                'decision_note': existing.get('decision_note'),
                'governance_history': list(existing.get('governance_history', []) or []),
                'source_targets': source.get('source_targets', {}),
                'target_source_targets': target.get('source_targets', {}),
                'source_status': source.get('status'),
                'target_status': target.get('status'),
                'semantic_group_key': source.get('semantic_group_key') or target.get('semantic_group_key'),
            }

    for candidate_id, existing in existing_items.items():
        if candidate_id in staged_items:
            continue
        if str(existing.get('review_state') or '') in {'accepted', 'rejected', 'superseded'}:
            carried = dict(existing)
            carried['last_seen_cycle_id'] = cycle_id or carried.get('last_seen_cycle_id')
            staged_items[candidate_id] = carried

    best_by_source: dict[str, dict[str, Any]] = {}
    for item in staged_items.values():
        source_rule = str(item.get('source_rule') or '')
        current = best_by_source.get(source_rule)
        if current is None or (int(item.get('priority_score', 0) or 0), -_merge_queue_state_rank(item.get('review_state')), str(item.get('target_candidate_key') or '')) > (int(current.get('priority_score', 0) or 0), -_merge_queue_state_rank(current.get('review_state')), str(current.get('target_candidate_key') or '')):
            best_by_source[source_rule] = item
    for item in staged_items.values():
        item['suggested_target'] = (best_by_source.get(str(item.get('source_rule') or '')) or item).get('target_rule')
        item['suggested_target_rule'] = item.get('suggested_target')
        item['is_top_suggestion_for_source'] = item.get('candidate_id') == (best_by_source.get(str(item.get('source_rule') or '')) or {}).get('candidate_id')

    state_counts: dict[str, int] = {}
    relation_counts: dict[str, int] = {}
    top_merge_targets_map: dict[str, dict[str, Any]] = {}
    top_supersede_suggestions: list[dict[str, Any]] = []
    ranked_items: list[dict[str, Any]] = []
    for item in staged_items.values():
        state = str(item.get('review_state') or 'open')
        state_counts[state] = state_counts.get(state, 0) + 1
        relation = str(item.get('relation_type') or 'merge')
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
        ranked_items.append(item)
        if relation == 'supersede':
            top_supersede_suggestions.append({
                'candidate_id': item.get('candidate_id'),
                'source_rule': item.get('source_rule'),
                'target_rule': item.get('target_rule'),
                'source_candidate_key': item.get('source_candidate_key'),
                'target_candidate_key': item.get('target_candidate_key'),
                'suggested_target': item.get('suggested_target'),
                'reason': item.get('reason'),
                'priority': item.get('priority'),
                'priority_score': item.get('priority_score'),
                'review_state': item.get('review_state'),
                'source_targets': item.get('source_targets', {}),
            })
        target_rule = str(item.get('target_rule') or '')
        if target_rule:
            target_entry = top_merge_targets_map.setdefault(target_rule, {
                'target_rule': target_rule,
                'target_candidate_key': item.get('target_candidate_key'),
                'suggestion_count': 0,
                'merge_count': 0,
                'supersede_count': 0,
                'open_count': 0,
                'reviewing_count': 0,
                'accepted_count': 0,
                'rejected_count': 0,
                'superseded_count': 0,
                'priority_score_total': 0,
                'source_targets': item.get('target_source_targets', {}),
            })
            target_entry['suggestion_count'] += 1
            target_entry['priority_score_total'] += int(item.get('priority_score', 0) or 0)
            target_entry[f"{relation}_count"] = target_entry.get(f"{relation}_count", 0) + 1
            target_entry[f"{state}_count"] = target_entry.get(f"{state}_count", 0) + 1

    ranked_items = sorted(ranked_items, key=lambda item: (_merge_queue_state_rank(item.get('review_state')), -int(item.get('priority_score', 0) or 0), str(item.get('source_candidate_key') or '')) )
    top_merge_targets = sorted(top_merge_targets_map.values(), key=lambda item: (-int(item.get('priority_score_total', 0) or 0), -int(item.get('suggestion_count', 0) or 0), str(item.get('target_candidate_key') or '')))[:5]
    top_supersede_suggestions = sorted(top_supersede_suggestions, key=lambda item: (_merge_queue_state_rank(item.get('review_state')), -int(item.get('priority_score', 0) or 0), str(item.get('source_candidate_key') or '')))[:5]

    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'queue_count': len(staged_items),
        'merge_count': relation_counts.get('merge', 0),
        'supersede_count': relation_counts.get('supersede', 0),
        'state_counts': state_counts,
        'open_count': state_counts.get('open', 0),
        'reviewing_count': state_counts.get('reviewing', 0),
        'accepted_count': state_counts.get('accepted', 0),
        'rejected_count': state_counts.get('rejected', 0),
        'superseded_count': state_counts.get('superseded', 0) + state_counts.get('inactive_superseded', 0),
        'top_merge_targets': top_merge_targets,
        'top_supersede_suggestions': top_supersede_suggestions,
        'items': {item.get('candidate_id'): item for item in ranked_items if item.get('candidate_id')},
    }
    _write_json(_merge_queue_registry_path(state_root), payload)
    _write_json(_merge_target_review_json_path(state_root), payload)
    lines = [
        '# Merge Target Review',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- queue_count: {payload.get('queue_count')}",
        f"- merge_count: {payload.get('merge_count')}",
        f"- supersede_count: {payload.get('supersede_count')}",
        f"- state_counts: {_render(payload.get('state_counts'))}",
        '',
        '## top_merge_targets',
    ]
    if payload['top_merge_targets']:
        for item in payload['top_merge_targets']:
            lines.append(f"- {item.get('target_rule')} | {item.get('target_candidate_key')} | suggestions={item.get('suggestion_count')} | priority_total={item.get('priority_score_total')} | merge={item.get('merge_count')} | supersede={item.get('supersede_count')}")
    else:
        lines.append('- none')
    lines.extend(['', '## top_supersede_suggestions'])
    if payload['top_supersede_suggestions']:
        for item in payload['top_supersede_suggestions']:
            lines.append(f"- {item.get('candidate_id')} | {item.get('source_candidate_key')} -> {item.get('target_candidate_key')} | priority={item.get('priority')}({item.get('priority_score')}) | state={item.get('review_state')} | reason={item.get('reason')}")
    else:
        lines.append('- none')
    lines.extend(['', '## queue_items'])
    queue_items = list(payload.get('items', {}).values())[:10]
    if queue_items:
        for item in queue_items:
            lines.append(f"- {item.get('candidate_id')} | {item.get('relation_type')} | {item.get('source_candidate_key')} -> {item.get('target_candidate_key')} | suggested_target={item.get('suggested_target')} | priority={item.get('priority')}({item.get('priority_score')}) | state={item.get('review_state')}")
    else:
        lines.append('- none')
    _merge_target_review_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def _build_semantic_candidate_review(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    merge_items: list[dict[str, Any]] = []
    conflict_items: list[dict[str, Any]] = []
    duplicate_items: list[dict[str, Any]] = []
    by_id = {str(item.get('proposal_id')): item for item in proposals if item.get('proposal_id')}
    for item in proposals:
        item.setdefault('merge_candidates', [])
        item.setdefault('conflict_candidates', [])
        item.setdefault('duplicate_candidates', [])
    for index, left in enumerate(proposals):
        for right in proposals[index + 1:]:
            relation, reason, similarity = _detect_pair_relation(left, right)
            if not relation:
                continue
            pair = {
                'conflict_id': _conflict_id(left.get('proposal_id'), right.get('proposal_id'), left.get('semantic_group_key')),
                'semantic_group_key': left.get('semantic_group_key'),
                'left_proposal_id': left.get('proposal_id'),
                'left_candidate_key': left.get('candidate_key'),
                'right_proposal_id': right.get('proposal_id'),
                'right_candidate_key': right.get('candidate_key'),
                'reason': reason,
                'similarity': round(similarity, 4),
            }
            compact = {
                'proposal_id': right.get('proposal_id'),
                'candidate_key': right.get('candidate_key'),
                'reason': reason,
                'similarity': round(similarity, 4),
            }
            reverse = {
                'proposal_id': left.get('proposal_id'),
                'candidate_key': left.get('candidate_key'),
                'reason': reason,
                'similarity': round(similarity, 4),
            }
            if relation == 'merge_candidate':
                merge_items.append(pair)
                left['merge_candidates'].append(compact)
                right['merge_candidates'].append(reverse)
            elif relation == 'conflict_candidate':
                conflict_items.append(pair)
                left['conflict_candidates'].append(compact)
                right['conflict_candidates'].append(reverse)
            elif relation == 'duplicate_candidate':
                duplicate_items.append(pair)
                left['duplicate_candidates'].append(compact)
                right['duplicate_candidates'].append(reverse)
    for proposal_id, item in by_id.items():
        item['merge_candidate_count'] = len(item.get('merge_candidates', []))
        item['conflict_candidate_count'] = len(item.get('conflict_candidates', []))
        item['duplicate_candidate_count'] = len(item.get('duplicate_candidates', []))
        item['merge_reason'] = (item.get('merge_candidates') or [{}])[0].get('reason') if item.get('merge_candidates') else ''
        item['conflict_reason'] = (item.get('conflict_candidates') or [{}])[0].get('reason') if item.get('conflict_candidates') else ''
        item['duplicate_reason'] = (item.get('duplicate_candidates') or [{}])[0].get('reason') if item.get('duplicate_candidates') else ''
    return {
        'merge_candidate_count': len(merge_items),
        'conflict_candidate_count': len(conflict_items),
        'duplicate_candidate_count': len(duplicate_items),
        'top_merge_items': merge_items[:5],
        'top_conflict_items': conflict_items[:5],
        'top_duplicate_items': duplicate_items[:5],
        'items': {
            'merge_candidates': merge_items,
            'conflict_candidates': conflict_items,
            'duplicate_candidates': duplicate_items,
        },
    }


def _build_rule_conflict_registry(*, proposals: list[dict[str, Any]], semantic_review: dict[str, Any], cycle_id: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    registry = _load_json(_conflict_registry_path(state_root))
    existing_items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    proposal_index = {str(item.get('proposal_id')): item for item in proposals if item.get('proposal_id')}
    next_items: dict[str, Any] = {}
    recent_adjudications: list[dict[str, Any]] = []

    for pair in list((semantic_review.get('items') or {}).get('conflict_candidates', []) or []):
        conflict_id = str(pair.get('conflict_id') or _conflict_id(pair.get('left_proposal_id'), pair.get('right_proposal_id'), pair.get('semantic_group_key')))
        existing = existing_items.get(conflict_id, {}) if isinstance(existing_items.get(conflict_id), dict) else {}
        left_id = pair.get('left_proposal_id')
        right_id = pair.get('right_proposal_id')
        left = proposal_index.get(str(left_id), {})
        right = proposal_index.get(str(right_id), {})
        state = str(existing.get('conflict_state') or 'open').strip().lower()
        if state not in CONFLICT_ALLOWED_STATES:
            state = 'open'
        resolution_type = str(existing.get('resolution_type') or '').strip().lower() or None
        if resolution_type and resolution_type not in CONFLICT_ALLOWED_RESOLUTIONS:
            resolution_type = None
        item = {
            'conflict_id': conflict_id,
            'semantic_group_key': pair.get('semantic_group_key'),
            'conflict_state': state,
            'reason': pair.get('reason'),
            'similarity': pair.get('similarity'),
            'conflicting_rule_ids': [proposal_id for proposal_id in [left_id, right_id] if proposal_id],
            'conflicting_proposals': [
                {
                    'proposal_id': proposal.get('proposal_id'),
                    'candidate_key': proposal.get('candidate_key'),
                    'proposal_state': proposal.get('proposal_state'),
                    'source_targets': proposal.get('source_targets', {}),
                }
                for proposal in [left, right] if proposal
            ],
            'adjudication_note': existing.get('adjudication_note'),
            'adjudicator': existing.get('adjudicator'),
            'adjudicated_at': existing.get('adjudicated_at'),
            'resolution_type': resolution_type,
            'governance_history': list(existing.get('governance_history', []) or []),
            'first_seen_cycle_id': existing.get('first_seen_cycle_id') or cycle_id,
            'last_seen_cycle_id': cycle_id,
            'latest_shared_source_targets': {
                'left': left.get('source_targets', {}),
                'right': right.get('source_targets', {}),
            },
        }
        next_items[conflict_id] = item
        if item.get('adjudicated_at'):
            recent_adjudications.append({
                'conflict_id': conflict_id,
                'conflict_state': item.get('conflict_state'),
                'resolution_type': item.get('resolution_type'),
                'adjudicator': item.get('adjudicator'),
                'adjudicated_at': item.get('adjudicated_at'),
                'adjudication_note': item.get('adjudication_note'),
                'conflicting_rule_ids': item.get('conflicting_rule_ids', []),
                'conflicting_proposals': item.get('conflicting_proposals', []),
            })

    for conflict_id, existing in existing_items.items():
        if conflict_id in next_items:
            continue
        if str(existing.get('conflict_state') or '') in {'resolved', 'rejected', 'superseded'}:
            carried = dict(existing)
            carried['last_seen_cycle_id'] = cycle_id or carried.get('last_seen_cycle_id')
            next_items[conflict_id] = carried
            if carried.get('adjudicated_at'):
                recent_adjudications.append({
                    'conflict_id': conflict_id,
                    'conflict_state': carried.get('conflict_state'),
                    'resolution_type': carried.get('resolution_type'),
                    'adjudicator': carried.get('adjudicator'),
                    'adjudicated_at': carried.get('adjudicated_at'),
                    'adjudication_note': carried.get('adjudication_note'),
                    'conflicting_rule_ids': carried.get('conflicting_rule_ids', []),
                    'conflicting_proposals': carried.get('conflicting_proposals', []),
                })

    state_counts: dict[str, int] = {}
    top_conflict_items: list[dict[str, Any]] = []
    for item in next_items.values():
        state = str(item.get('conflict_state') or 'open')
        state_counts[state] = state_counts.get(state, 0) + 1
        top_conflict_items.append({
            'conflict_id': item.get('conflict_id'),
            'semantic_group_key': item.get('semantic_group_key'),
            'conflict_state': item.get('conflict_state'),
            'resolution_type': item.get('resolution_type'),
            'adjudicator': item.get('adjudicator'),
            'adjudicated_at': item.get('adjudicated_at'),
            'conflicting_rule_ids': item.get('conflicting_rule_ids', []),
            'conflicting_proposals': item.get('conflicting_proposals', []),
            'reason': item.get('reason'),
            'similarity': item.get('similarity'),
        })
    top_conflict_items = sorted(
        top_conflict_items,
        key=lambda item: ({'open': 0, 'reviewing': 1, 'resolved': 2, 'rejected': 3, 'superseded': 4}.get(str(item.get('conflict_state')), 9), -(float(item.get('similarity') or 0))),
    )[:5]
    recent_adjudications = sorted(recent_adjudications, key=lambda item: str(item.get('adjudicated_at') or ''), reverse=True)[:5]
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'conflict_count': len(next_items),
        'state_counts': state_counts,
        'open_count': state_counts.get('open', 0),
        'reviewing_count': state_counts.get('reviewing', 0),
        'resolved_count': state_counts.get('resolved', 0),
        'rejected_count': state_counts.get('rejected', 0),
        'superseded_count': state_counts.get('superseded', 0) + state_counts.get('inactive_superseded', 0),
        'top_conflict_items': top_conflict_items,
        'recent_adjudications': recent_adjudications,
        'items': next_items,
    }
    _write_json(_conflict_registry_path(state_root), payload)
    return payload



def _normalize_consequence_state(value: str = '', *, fallback: str = 'active') -> str:
    state = str(value or '').strip().lower()
    return state if state in RULE_CONSEQUENCE_STATES else fallback


def _default_consequence_payload(*, consequence_state: str = 'active', decision_type: str = 'accepted', source_proposal_id: str = '', target_proposal_id: str = '', target_rulebook_state: str = '', note: str = '', updated_at: str | None = None, cycle_id: str = '', merge_candidate_id: str = '', conflict_id: str = '', resolution_type: str = '') -> dict[str, Any]:
    return {
        'state': _normalize_consequence_state(consequence_state),
        'decision_type': decision_type,
        'source_proposal_id': source_proposal_id or None,
        'target_proposal_id': target_proposal_id or None,
        'target_rulebook_state': target_rulebook_state or None,
        'merge_candidate_id': merge_candidate_id or None,
        'conflict_id': conflict_id or None,
        'resolution_type': resolution_type or None,
        'note': note or None,
        'updated_at': updated_at or _now(),
        'cycle_id': cycle_id or None,
    }


def _conflict_resolution_outcome(*, resolution: str, decision_state: str, role: str) -> tuple[str, str, str]:
    resolution = str(resolution or '').strip().lower()
    decision_state = str(decision_state or '').strip().lower()
    if decision_state == 'rejected':
        if resolution == 'reject_new':
            return ('archived', 'conflict_rejected_archived', 'active') if role == 'source' else ('active', 'conflict_rejected_retained', 'active')
        if resolution == 'reject_old':
            return ('active', 'conflict_rejected_retained', 'active') if role == 'source' else ('archived', 'conflict_rejected_archived', 'active')
        return ('active', 'conflict_rejected_no_change', 'active')
    if resolution in {'keep_both', 'defer'}:
        return 'active', f'conflict_resolved_{resolution}', 'active'
    if resolution == 'merge':
        return ('inactive_merged', 'conflict_resolved_merge_source', 'active') if role == 'source' else ('active', 'conflict_resolved_merge_target', 'active')
    if resolution == 'supersede':
        return ('active', 'conflict_resolved_supersede_winner', 'inactive_superseded') if role == 'source' else ('inactive_superseded', 'conflict_resolved_supersede_loser', 'active')
    if resolution == 'reject_new':
        return ('inactive_conflict_rejected', 'conflict_resolved_reject_new', 'active') if role == 'source' else ('active', 'conflict_resolved_keep_existing', 'active')
    if resolution == 'reject_old':
        return ('active', 'conflict_resolved_keep_new', 'active') if role == 'source' else ('inactive_conflict_rejected', 'conflict_resolved_reject_old', 'active')
    return 'active', 'conflict_resolved_unspecified', 'active'


def _apply_consequence_to_artifact(path: Path, consequence: dict[str, Any]) -> None:
    if not path.exists():
        return
    def updater(payload: dict[str, Any]) -> None:
        existing = dict(payload.get('consequence') or {})
        merged = {**existing, **consequence}
        merged['state'] = _normalize_consequence_state(merged.get('state'), fallback=payload.get('status', 'active'))
        payload['consequence'] = merged
        payload['status'] = merged.get('state')
        if merged.get('target_proposal_id'):
            payload['target_proposal_id'] = merged.get('target_proposal_id')
        if merged.get('target_rulebook_state'):
            payload['target_rulebook_state'] = merged.get('target_rulebook_state')
    _update_json_artifact(path, updater)


def _collect_consequence_state_counts(items: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items.values():
        if not isinstance(item, dict) or not item.get('proposal_id'):
            continue
        state = _normalize_consequence_state((item.get('consequence') or {}).get('state') or item.get('status') or 'active')
        counts[state] = counts.get(state, 0) + 1
    return counts


def _collect_recent_consequence_updates(items: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    rows = []
    for item in items.values():
        if not isinstance(item, dict) or not item.get('proposal_id'):
            continue
        consequence = item.get('consequence') or {}
        if not isinstance(consequence, dict) or not consequence.get('updated_at'):
            continue
        rows.append({
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'state': consequence.get('state') or item.get('status'),
            'decision_type': consequence.get('decision_type'),
            'target_proposal_id': consequence.get('target_proposal_id'),
            'resolution_type': consequence.get('resolution_type'),
            'updated_at': consequence.get('updated_at'),
        })
    rows.sort(key=lambda row: str(row.get('updated_at') or ''), reverse=True)
    return rows[:limit]


def _rule_consequence_history_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_consequence_history.json'


def _rule_consequence_history_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_consequence_history.md'


def _archive_restore_timeline_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_restore_timeline.json'


def _archive_restore_timeline_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'archive_restore_timeline.md'


def _rule_transition_ledger_jsonl_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_transition_ledger.jsonl'


def _rule_transition_digest_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_transition_digest.json'


def _rule_transition_digest_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_transition_digest.md'


def _transition_ledger_digest_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'transition_ledger_digest_review.json'


def _transition_ledger_digest_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'transition_ledger_digest_review.md'


def _rule_registry_sync_audit_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_registry_sync_audit.json'


def _rule_registry_sync_audit_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_registry_sync_audit.md'


def _rule_registry_sync_scope_review_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_registry_sync_scope_review.json'


def _rule_registry_sync_scope_review_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_registry_sync_scope_review.md'


def _shared_sample_governance_registry_json_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'shared_sample_governance_registry.json'


def _shared_sample_governance_registry_md_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'shared_sample_governance_registry.md'


def _transition_ledger_suppression_jsonl_path(state_root: Path = STATE_ROOT) -> Path:
    return state_root / 'rule_transition_suppressions.jsonl'


def _semantic_event_fingerprint(*, proposal_id: str, candidate_key: str = '', from_state: str | None = None, to_state: str | None = None, trigger: str = '', related_registry: str = '', target_proposal_id: str = '', merge_candidate_id: str = '', conflict_id: str = '', archive_policy: str = '', archived_reason_family: str = '', resolution_type: str = '', source_targets: dict[str, Any] | None = None, event_scope: str = 'rule_governance', transition_type: str = '') -> str:
    canonical = {
        'proposal_id': str(proposal_id or ''),
        'candidate_key': str(candidate_key or ''),
        'from_state': from_state or None,
        'to_state': to_state or None,
        'trigger': str(trigger or ''),
        'related_registry': str(related_registry or ''),
        'target_proposal_id': str(target_proposal_id or ''),
        'merge_candidate_id': str(merge_candidate_id or ''),
        'conflict_id': str(conflict_id or ''),
        'archive_policy': str(archive_policy or ''),
        'archived_reason_family': str(archived_reason_family or ''),
        'resolution_type': str(resolution_type or ''),
        'source_targets': {str(k): int(v or 0) for k, v in sorted((source_targets or {}).items())},
        'event_scope': str(event_scope or ''),
        'transition_type': str(transition_type or ''),
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def _append_transition_event(*, state_root: Path, proposal_id: str, candidate_key: str = '', from_state: str | None = None, to_state: str | None = None, trigger: str = '', actor: str = '', reason: str = '', related_registry: str = '', cycle_id: str = '', event_at: str | None = None, event_scope: str = 'rule_governance', transition_type: str = '', target_proposal_id: str = '', merge_candidate_id: str = '', conflict_id: str = '', archive_policy: str = '', archived_reason_family: str = '', resolution_type: str = '', source_targets: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    ts = event_at or _now()
    semantic_fingerprint = _semantic_event_fingerprint(
        proposal_id=proposal_id,
        candidate_key=candidate_key,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger or transition_type or 'state_transition',
        related_registry=related_registry,
        target_proposal_id=target_proposal_id,
        merge_candidate_id=merge_candidate_id,
        conflict_id=conflict_id,
        archive_policy=archive_policy,
        archived_reason_family=archived_reason_family,
        resolution_type=resolution_type,
        source_targets=source_targets,
        event_scope=event_scope,
        transition_type=transition_type or trigger or 'state_transition',
    )
    existing = next((item for item in reversed(_load_transition_events(state_root)) if item.get('semantic_fingerprint') == semantic_fingerprint), None)
    if existing:
        suppressed = {
            'suppressed': True,
            'suppressed_at': ts,
            'cycle_id': cycle_id,
            'proposal_id': proposal_id,
            'candidate_key': candidate_key,
            'semantic_fingerprint': semantic_fingerprint,
            'existing_event_id': existing.get('event_id'),
            'existing_event_at': existing.get('event_at'),
            'trigger': trigger or transition_type or 'state_transition',
            'related_registry': related_registry or '',
            'target_proposal_id': target_proposal_id or None,
            'merge_candidate_id': merge_candidate_id or None,
            'conflict_id': conflict_id or None,
        }
        if extra:
            suppressed.update({k: v for k, v in extra.items() if k not in suppressed})
        suppression_path = _transition_ledger_suppression_jsonl_path(state_root)
        suppression_path.parent.mkdir(parents=True, exist_ok=True)
        with suppression_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(suppressed, ensure_ascii=False) + '\n')
        return suppressed
    payload = {
        'event_id': f"transition-{hashlib.sha1('|'.join([str(ts), str(proposal_id), str(trigger), str(from_state), str(to_state), str(related_registry), str(target_proposal_id), str(merge_candidate_id), str(conflict_id)]).encode('utf-8')).hexdigest()[:12]}",
        'event_at': ts,
        'cycle_id': cycle_id,
        'event_scope': event_scope,
        'proposal_id': proposal_id,
        'candidate_key': candidate_key,
        'from_state': from_state,
        'to_state': to_state,
        'transition_type': transition_type or trigger or 'state_transition',
        'trigger': trigger or transition_type or 'state_transition',
        'actor': actor or 'system',
        'reason': reason or '',
        'related_registry': related_registry or '',
        'target_proposal_id': target_proposal_id or None,
        'merge_candidate_id': merge_candidate_id or None,
        'conflict_id': conflict_id or None,
        'archive_policy': archive_policy or None,
        'archived_reason_family': archived_reason_family or None,
        'resolution_type': resolution_type or None,
        'source_targets': source_targets or {},
        'semantic_fingerprint': semantic_fingerprint,
    }
    if extra:
        payload.update({k: v for k, v in extra.items() if k not in payload})
    path = _rule_transition_ledger_jsonl_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + '\n')
    return payload


def _load_transition_events(state_root: Path) -> list[dict[str, Any]]:
    path = _rule_transition_ledger_jsonl_path(state_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    rows.sort(key=lambda item: (str(item.get('event_at') or ''), str(item.get('event_id') or '')))
    return rows


def _build_rule_transition_digest(*, state_root: Path, cycle_id: str = '') -> dict[str, Any]:
    events = _load_transition_events(state_root)
    trigger_counts: dict[str, int] = {}
    registry_counts: dict[str, int] = {}
    state_pair_counts: dict[str, int] = {}
    proposal_counts: dict[str, int] = {}
    semantic_counts: dict[str, int] = {}
    for item in events:
        trigger = str(item.get('trigger') or 'unknown')
        trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        registry = str(item.get('related_registry') or 'unknown')
        registry_counts[registry] = registry_counts.get(registry, 0) + 1
        pair = f"{item.get('from_state') or 'n/a'}->{item.get('to_state') or 'n/a'}"
        state_pair_counts[pair] = state_pair_counts.get(pair, 0) + 1
        pid = str(item.get('proposal_id') or 'unknown')
        proposal_counts[pid] = proposal_counts.get(pid, 0) + 1
        semantic = str(item.get('semantic_fingerprint') or '')
        if semantic:
            semantic_counts[semantic] = semantic_counts.get(semantic, 0) + 1
    recent_events = sorted(events, key=lambda item: str(item.get('event_at') or ''), reverse=True)[:8]
    recent_summary = [
        {
            'event_at': item.get('event_at'),
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'from_state': item.get('from_state'),
            'to_state': item.get('to_state'),
            'trigger': item.get('trigger'),
            'actor': item.get('actor'),
            'related_registry': item.get('related_registry'),
            'semantic_fingerprint': item.get('semantic_fingerprint'),
        }
        for item in recent_events
    ]
    replay_preview = {}
    for item in events:
        pid = str(item.get('proposal_id') or '')
        if not pid or pid in replay_preview:
            continue
        replay_preview[pid] = {'proposal_id': pid, 'candidate_key': item.get('candidate_key'), 'trajectory': []}
    for item in events:
        pid = str(item.get('proposal_id') or '')
        if pid in replay_preview and len(replay_preview[pid]['trajectory']) < 6:
            replay_preview[pid]['trajectory'].append({
                'event_at': item.get('event_at'),
                'from_state': item.get('from_state'),
                'to_state': item.get('to_state'),
                'trigger': item.get('trigger'),
            })
    duplicate_fingerprints = {k: v for k, v in semantic_counts.items() if int(v or 0) > 1}
    suppression_rows: list[dict[str, Any]] = []
    suppression_path = _transition_ledger_suppression_jsonl_path(state_root)
    if suppression_path.exists():
        for line in suppression_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                suppression_rows.append(payload)
    duplicate_groups: list[dict[str, Any]] = []
    for fingerprint, count in sorted(duplicate_fingerprints.items(), key=lambda kv: (-kv[1], kv[0]))[:8]:
        matched = [item for item in events if item.get('semantic_fingerprint') == fingerprint]
        exemplar = matched[0] if matched else {}
        duplicate_groups.append({
            'semantic_fingerprint': fingerprint,
            'event_count': count,
            'proposal_id': exemplar.get('proposal_id'),
            'candidate_key': exemplar.get('candidate_key'),
            'trigger': exemplar.get('trigger'),
            'related_registry': exemplar.get('related_registry'),
        })
    unique_semantic_event_count = len([k for k in semantic_counts if k])
    append_only_ok = bool(events) or _rule_transition_ledger_jsonl_path(state_root).exists()
    review_payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'append_only_ledger': True,
        'append_only_ledger_ok': append_only_ok,
        'transition_event_count': len(events),
        'unique_semantic_event_count': unique_semantic_event_count,
        'digest_duplicate_semantic_event_count': sum(max(int(v or 0) - 1, 0) for v in semantic_counts.values()),
        'semantic_duplicate_group_count': len(duplicate_fingerprints),
        'transition_duplicate_suppressed_count': len(suppression_rows),
        'recent_suppressed_events': sorted(suppression_rows, key=lambda item: str(item.get('suppressed_at') or ''), reverse=True)[:8],
        'top_duplicate_semantic_groups': duplicate_groups,
    }
    _write_json(_transition_ledger_digest_review_json_path(state_root), review_payload)
    review_lines = [
        '# Transition Ledger Digest Review',
        '',
        f"- generated_at: {review_payload.get('generated_at')}",
        f"- cycle_id: {review_payload.get('cycle_id')}",
        f"- append_only_ledger: {review_payload.get('append_only_ledger')}",
        f"- append_only_ledger_ok: {review_payload.get('append_only_ledger_ok')}",
        f"- transition_event_count: {review_payload.get('transition_event_count')}",
        f"- unique_semantic_event_count: {review_payload.get('unique_semantic_event_count')}",
        f"- digest_duplicate_semantic_event_count: {review_payload.get('digest_duplicate_semantic_event_count')}",
        f"- semantic_duplicate_group_count: {review_payload.get('semantic_duplicate_group_count')}",
        f"- transition_duplicate_suppressed_count: {review_payload.get('transition_duplicate_suppressed_count')}",
        '',
        '## top_duplicate_semantic_groups',
    ]
    if duplicate_groups:
        for item in duplicate_groups:
            review_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | trigger={item.get('trigger')} | registry={item.get('related_registry')} | duplicate_events={item.get('event_count')}")
    else:
        review_lines.append('- none')
    _transition_ledger_digest_review_md_path(state_root).write_text('\n'.join(review_lines) + '\n', encoding='utf-8')
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'transition_ledger_available': bool(events),
        'transition_event_count': len(events),
        'unique_semantic_event_count': unique_semantic_event_count,
        'digest_duplicate_semantic_event_count': review_payload.get('digest_duplicate_semantic_event_count', 0),
        'semantic_duplicate_group_count': review_payload.get('semantic_duplicate_group_count', 0),
        'transition_duplicate_suppressed_count': review_payload.get('transition_duplicate_suppressed_count', 0),
        'recent_suppressed_events': review_payload.get('recent_suppressed_events', []),
        'transition_digest_review_available': True,
        'top_transition_triggers': dict(sorted(trigger_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        'related_registry_counts': dict(sorted(registry_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        'state_pair_counts': dict(sorted(state_pair_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        'proposal_event_counts': dict(sorted(proposal_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        'recent_transition_events': recent_summary,
        'replay_preview': list(replay_preview.values())[:6],
        'digest_review': review_payload,
    }
    _write_json(_rule_transition_digest_json_path(state_root), payload)
    lines = ['# Rule Transition Digest', '', f"- generated_at: {payload.get('generated_at')}", f"- cycle_id: {payload.get('cycle_id')}", f"- transition_ledger_available: {payload.get('transition_ledger_available')}", f"- transition_event_count: {payload.get('transition_event_count')}", f"- unique_semantic_event_count: {payload.get('unique_semantic_event_count')}", f"- digest_duplicate_semantic_event_count: {payload.get('digest_duplicate_semantic_event_count')}", f"- transition_digest_review_available: {payload.get('transition_digest_review_available')}", f"- top_transition_triggers: {_render(payload.get('top_transition_triggers'))}", f"- related_registry_counts: {_render(payload.get('related_registry_counts'))}", '', '## recent_transition_events']
    if recent_summary:
        for item in recent_summary:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | {item.get('from_state') or 'n/a'} -> {item.get('to_state') or 'n/a'} | trigger={item.get('trigger')} | actor={item.get('actor')} | registry={item.get('related_registry')} | at={item.get('event_at')}")
    else:
        lines.append('- none')
    lines.extend(['', '## replay_preview'])
    if payload['replay_preview']:
        for item in payload['replay_preview']:
            traj = ' ; '.join(f"{step.get('from_state') or 'n/a'}->{step.get('to_state') or 'n/a'}({step.get('trigger')})" for step in item.get('trajectory') or [])
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | {traj or 'n/a'}")
    else:
        lines.append('- none')
    _rule_transition_digest_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def _build_consequence_history(*, state_root: Path, cycle_id: str, local_items: dict[str, Any], restore_registry: dict[str, Any]) -> dict[str, Any]:
    history_items: dict[str, dict[str, Any]] = {}
    recent_transitions: list[dict[str, Any]] = []
    transition_type_counts: dict[str, int] = {}
    shared_source_archived_count = 0
    for proposal_id, item in local_items.items():
        if not isinstance(item, dict) or not proposal_id:
            continue
        candidate_key = item.get('candidate_key')
        events: list[dict[str, Any]] = []
        exported_at = item.get('exported_at') or ((item.get('consequence') or {}).get('updated_at'))
        if exported_at:
            events.append({
                'event_at': exported_at,
                'transition_type': 'exported_active',
                'from_state': None,
                'to_state': 'active',
                'decision_type': 'exported_active',
            })
        archived_from_state = str(item.get('archived_from_state') or '')
        archive_meta = item.get('archive_metadata') or {}
        archived_at = item.get('archived_at') or ((item.get('consequence') or {}).get('updated_at'))
        if archived_from_state and archived_from_state != 'active' and archived_at:
            events.append({
                'event_at': archived_at,
                'transition_type': 'pre_archive_consequence',
                'from_state': 'active',
                'to_state': archived_from_state,
                'decision_type': (item.get('consequence') or {}).get('decision_type'),
                'resolution_type': (item.get('consequence') or {}).get('resolution_type'),
                'archive_policy': archive_meta.get('archived_policy'),
                'archive_reason_family': archive_meta.get('archived_reason_family'),
            })
        if archived_from_state and archived_at:
            events.append({
                'event_at': archived_at,
                'transition_type': 'archive',
                'from_state': archived_from_state or 'active',
                'to_state': 'archived',
                'decision_type': 'archived',
                'archive_policy': archive_meta.get('archived_policy'),
                'archive_reason_family': archive_meta.get('archived_reason_family'),
                'shared_governance_rule': archive_meta.get('shared_governance_rule', False),
            })
        for restore_item in (restore_registry.get('items') or {}).values():
            if not isinstance(restore_item, dict) or restore_item.get('proposal_id') != proposal_id:
                continue
            events.append({
                'event_at': restore_item.get('action_at'),
                'transition_type': f"archive_{restore_item.get('action')}",
                'from_state': restore_item.get('from_state'),
                'to_state': restore_item.get('to_state'),
                'decision_type': f"archive_{restore_item.get('action')}",
                'archive_policy': restore_item.get('archive_policy'),
                'archive_reason_family': restore_item.get('archived_reason_family'),
                'shared_governance_rule': restore_item.get('shared_governance_rule', False),
                'action': restore_item.get('action'),
            })
        if not events:
            consequence = item.get('consequence') or {}
            updated_at = consequence.get('updated_at')
            state = _normalize_consequence_state(consequence.get('state') or item.get('status') or 'active')
            if updated_at:
                events.append({
                    'event_at': updated_at,
                    'transition_type': 'current_consequence',
                    'from_state': None,
                    'to_state': state,
                    'decision_type': consequence.get('decision_type'),
                    'resolution_type': consequence.get('resolution_type'),
                })
        events = [event for event in events if event.get('event_at')]
        events.sort(key=lambda event: (str(event.get('event_at') or ''), str(event.get('transition_type') or '')))
        if (archive_meta.get('shared_governance_rule')):
            shared_source_archived_count += 1
        trajectory = [event.get('to_state') for event in events if event.get('to_state')]
        for event in events:
            transition_type = str(event.get('transition_type') or 'unknown')
            transition_type_counts[transition_type] = transition_type_counts.get(transition_type, 0) + 1
            recent_transitions.append({
                'proposal_id': proposal_id,
                'candidate_key': candidate_key,
                **event,
            })
        history_items[proposal_id] = {
            'proposal_id': proposal_id,
            'candidate_key': candidate_key,
            'current_state': item.get('status'),
            'current_consequence_state': ((item.get('consequence') or {}).get('state') or item.get('status')),
            'source_targets': item.get('source_targets', {}),
            'archive_metadata': archive_meta,
            'event_count': len(events),
            'trajectory': trajectory,
            'events': events,
        }
    recent_transitions = sorted(recent_transitions, key=lambda event: str(event.get('event_at') or ''), reverse=True)[:8]
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'history_available': bool(history_items),
        'history_item_count': len(history_items),
        'history_event_count': sum(int(item.get('event_count', 0) or 0) for item in history_items.values()),
        'shared_source_archived_count': shared_source_archived_count,
        'transition_type_counts': transition_type_counts,
        'recent_transitions': recent_transitions,
        'items': history_items,
    }
    _write_json(_rule_consequence_history_json_path(state_root), payload)
    lines = [
        '# Rule Consequence History',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- history_available: {payload.get('history_available')}",
        f"- history_item_count: {payload.get('history_item_count')}",
        f"- history_event_count: {payload.get('history_event_count')}",
        f"- shared_source_archived_count: {payload.get('shared_source_archived_count')}",
        f"- transition_type_counts: {_render(payload.get('transition_type_counts'))}",
        '',
        '## recent_transitions',
    ]
    if recent_transitions:
        for event in recent_transitions:
            lines.append(f"- {event.get('proposal_id')} | {event.get('candidate_key')} | {event.get('from_state') or 'n/a'} -> {event.get('to_state') or 'n/a'} | type={event.get('transition_type')} | at={event.get('event_at')}")
    else:
        lines.append('- none')
    lines.extend(['', '## trajectories'])
    if history_items:
        for item in list(history_items.values())[:12]:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | trajectory={' -> '.join(item.get('trajectory') or []) or 'n/a'} | events={item.get('event_count')}")
    else:
        lines.append('- none')
    _rule_consequence_history_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def _write_rule_consequence_review(*, state_root: Path, cycle_id: str, proposal_entries: dict[str, Any], sink_items: dict[str, Any], local_items: dict[str, Any], restore_registry: dict[str, Any]) -> dict[str, Any]:
    proposal_state_counts = _collect_consequence_state_counts(proposal_entries)
    governed_state_counts = _collect_consequence_state_counts(sink_items)
    local_state_counts = _collect_consequence_state_counts(local_items)
    recent_updates = _collect_recent_consequence_updates(local_items)
    consequence_history = _build_consequence_history(state_root=state_root, cycle_id=cycle_id, local_items=local_items, restore_registry=restore_registry)
    transition_digest = _build_rule_transition_digest(state_root=state_root, cycle_id=cycle_id)
    conflict_resolution_type_counts: dict[str, int] = {}
    for item in local_items.values():
        if not isinstance(item, dict):
            continue
        resolution = str(((item.get('consequence') or {}).get('resolution_type')) or '').strip()
        if resolution:
            conflict_resolution_type_counts[resolution] = conflict_resolution_type_counts.get(resolution, 0) + 1
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'proposal_registry_state_counts': proposal_state_counts,
        'governed_rule_state_counts': governed_state_counts,
        'local_rulebook_state_counts': local_state_counts,
        'active_rule_count': local_state_counts.get('active', 0),
        'inactive_rule_count': sum(local_state_counts.get(k, 0) for k in ['reviewing', 'inactive_merged', 'inactive_superseded', 'inactive_conflict_rejected', 'archived', 'duplicate_blocked']),
        'archived_rule_count': local_state_counts.get('archived', 0),
        'merged_rule_count': local_state_counts.get('inactive_merged', 0),
        'superseded_rule_count': local_state_counts.get('inactive_superseded', 0),
        'conflict_resolution_type_counts': conflict_resolution_type_counts,
        'recent_consequence_updates': recent_updates,
        'consequence_history_available': consequence_history.get('history_available', False),
        'consequence_history_event_count': consequence_history.get('history_event_count', 0),
        'recent_consequence_transitions': consequence_history.get('recent_transitions', []),
        'transition_ledger_available': transition_digest.get('transition_ledger_available', False),
        'transition_event_count': transition_digest.get('transition_event_count', 0),
        'recent_transition_events': transition_digest.get('recent_transition_events', []),
        'top_transition_triggers': transition_digest.get('top_transition_triggers', {}),
        'transition_digest': transition_digest,
        'consequence_history': consequence_history,
    }
    _write_json(_rule_consequence_review_json_path(state_root), payload)
    lines = [
        '# Rule Consequence Review',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- proposal_registry_state_counts: {_render(payload.get('proposal_registry_state_counts'))}",
        f"- governed_rule_state_counts: {_render(payload.get('governed_rule_state_counts'))}",
        f"- local_rulebook_state_counts: {_render(payload.get('local_rulebook_state_counts'))}",
        f"- active/inactive/archived: {payload.get('active_rule_count')} / {payload.get('inactive_rule_count')} / {payload.get('archived_rule_count')}",
        f"- merged/superseded: {payload.get('merged_rule_count')} / {payload.get('superseded_rule_count')}",
        f"- conflict_resolution_type_counts: {_render(payload.get('conflict_resolution_type_counts'))}",
        f"- consequence_history_available: {payload.get('consequence_history_available')}",
        f"- consequence_history_event_count: {payload.get('consequence_history_event_count')}",
        '',
        '## recent_consequence_updates',
    ]
    if recent_updates:
        for item in recent_updates:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | state={item.get('state')} | decision={item.get('decision_type')} | target={item.get('target_proposal_id') or 'n/a'} | resolution={item.get('resolution_type') or 'n/a'} | at={item.get('updated_at')}")
    else:
        lines.append('- none')
    lines.extend(['', '## recent_consequence_transitions'])
    if payload.get('recent_consequence_transitions'):
        for item in payload.get('recent_consequence_transitions') or []:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | {item.get('from_state') or 'n/a'} -> {item.get('to_state') or 'n/a'} | type={item.get('transition_type')} | at={item.get('event_at')}")
    else:
        lines.append('- none')
    _rule_consequence_review_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload



def _build_archive_metadata(*, item: dict[str, Any], archive_reason: str, source_state: str) -> dict[str, Any]:
    consequence = item.get('consequence') or {}
    resolution_type = str(consequence.get('resolution_type') or '')
    source_targets = item.get('source_targets', {}) or {}
    retained_as = 'historical_rule'
    policy = 'manual_review_archive'
    reason_family = 'manual'
    restorable = True
    restore_to_state = source_state or 'active'
    if archive_reason.startswith('duplicate_'):
        reason_family = 'duplicate_guard'
        policy = 'duplicate_terminal_archive'
        retained_as = 'duplicate_evidence'
        restore_to_state = source_state or 'duplicate_blocked'
    elif archive_reason.startswith('conflict_rejected') or resolution_type in {'reject_new', 'reject_old'}:
        reason_family = 'conflict_rejected'
        policy = f'conflict_{resolution_type or "rejected"}_archive'
        retained_as = 'conflict_evidence'
        restore_to_state = source_state or 'inactive_conflict_rejected'
    elif archive_reason.startswith('superseded') or source_state == 'inactive_superseded':
        reason_family = 'superseded'
        policy = 'superseded_archive'
        retained_as = 'superseded_history'
        restore_to_state = source_state or 'inactive_superseded'
        restorable = False
    elif source_state == 'inactive_merged':
        reason_family = 'merged'
        policy = 'merged_history_archive'
        retained_as = 'merge_history'
        restore_to_state = source_state or 'inactive_merged'
        restorable = False
    evidence_scope = 'shared_release_rollback' if int(source_targets.get('official_release', 0) or 0) > 0 and int(source_targets.get('rollback', 0) or 0) > 0 else ('release' if int(source_targets.get('official_release', 0) or 0) > 0 else ('rollback' if int(source_targets.get('rollback', 0) or 0) > 0 else 'generic'))
    return {
        'archived_reason_family': reason_family,
        'archived_policy': policy,
        'retained_as': retained_as,
        'restorable': bool(restorable),
        'restore_to_state': restore_to_state,
        'reopen_to_state': 'reviewing' if restorable else None,
        'revive_to_state': 'active' if restorable else None,
        'evidence_scope': evidence_scope,
        'shared_governance_rule': evidence_scope == 'shared_release_rollback',
        'archive_reason': archive_reason,
        'archived_from_state': source_state or item.get('status') or 'active',
        'source_targets': source_targets,
    }


def _write_archive_policy_review(*, state_root: Path, cycle_id: str, local_items: dict[str, Any], archive_audit: dict[str, Any]) -> dict[str, Any]:
    archived_items = [item for item in local_items.values() if isinstance(item, dict) and str(item.get('status') or '') == 'archived']
    historical_items = [item for item in (archive_audit.get('items') or {}).values() if isinstance(item, dict)]
    policy_counts: dict[str, int] = {}
    reason_family_counts: dict[str, int] = {}
    retained_as_counts: dict[str, int] = {}
    evidence_scope_counts: dict[str, int] = {}
    restorable_count = 0
    shared_count = 0
    for item in historical_items:
        meta = item.get('archive_metadata') or {}
        policy = str(meta.get('archived_policy') or 'unspecified')
        reason_family = str(meta.get('archived_reason_family') or 'unspecified')
        retained_as = str(meta.get('retained_as') or 'unspecified')
        evidence_scope = str(meta.get('evidence_scope') or 'generic')
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
        reason_family_counts[reason_family] = reason_family_counts.get(reason_family, 0) + 1
        retained_as_counts[retained_as] = retained_as_counts.get(retained_as, 0) + 1
        evidence_scope_counts[evidence_scope] = evidence_scope_counts.get(evidence_scope, 0) + 1
        if meta.get('restorable'):
            restorable_count += 1
        if meta.get('shared_governance_rule'):
            shared_count += 1
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'archived_item_count': len(archived_items),
        'historical_archived_item_count': len(historical_items),
        'archived_restorable_count': restorable_count,
        'archive_policy_counts': policy_counts,
        'archive_reason_family_counts': reason_family_counts,
        'archive_retained_as_counts': retained_as_counts,
        'archive_evidence_scope_counts': evidence_scope_counts,
        'shared_release_rollback_governance_count': shared_count,
        'recent_archive_actions': archive_audit.get('recent_archived_items', []),
    }
    _write_json(_archive_policy_review_json_path(state_root), payload)
    lines = ['# Archive Policy Review', '', f"- generated_at: {payload.get('generated_at')}", f"- cycle_id: {payload.get('cycle_id')}", f"- archived_item_count: {payload.get('archived_item_count')}", f"- historical_archived_item_count: {payload.get('historical_archived_item_count')}", f"- archived_restorable_count: {payload.get('archived_restorable_count')}", f"- archive_policy_counts: {_render(payload.get('archive_policy_counts'))}", f"- archive_reason_family_counts: {_render(payload.get('archive_reason_family_counts'))}", f"- archive_retained_as_counts: {_render(payload.get('archive_retained_as_counts'))}", f"- archive_evidence_scope_counts: {_render(payload.get('archive_evidence_scope_counts'))}", f"- shared_release_rollback_governance_count: {payload.get('shared_release_rollback_governance_count')}", '', '## recent_archive_actions']
    recent = list(payload.get('recent_archive_actions') or [])
    if recent:
        for item in recent:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | policy={(item.get('archive_metadata') or {}).get('archived_policy') or item.get('archived_policy') or 'n/a'} | restorable={(item.get('archive_metadata') or {}).get('restorable')} | at={item.get('archived_at') or item.get('action_at')}")
    else:
        lines.append('- none')
    _archive_policy_review_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def _load_archive_restore_registry(state_root: Path) -> dict[str, Any]:
    payload = _load_json(_archive_restore_registry_path(state_root))
    if not isinstance(payload.get('items'), dict):
        payload['items'] = {}
    return payload


def apply_archive_restore_action(*, proposal_id: str, action: str, actor: str = 'human', note: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    action = str(action or '').strip().lower()
    if action not in {'restore', 'reopen', 'revive'}:
        raise ValueError(f'unsupported archive action: {action}')
    registry = _load_json(_local_rulebook_registry_path(state_root))
    items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    entry = items.get(proposal_id) if isinstance(items.get(proposal_id), dict) else None
    if not entry:
        raise ValueError(f'unknown proposal_id: {proposal_id}')
    if str(entry.get('status') or '') != 'archived':
        raise ValueError(f'proposal is not archived: {proposal_id}')
    archive_meta = dict(entry.get('archive_metadata') or {})
    if not archive_meta.get('restorable'):
        raise ValueError(f'proposal is not restorable: {proposal_id}')
    restore_routes = {
        'restore': str(archive_meta.get('restore_to_state') or entry.get('archived_from_state') or 'active'),
        'reopen': str(archive_meta.get('reopen_to_state') or 'reviewing'),
        'revive': str(archive_meta.get('revive_to_state') or 'active'),
    }
    restored_state = restore_routes[action]
    event_at = _now()
    history = list(entry.get('reopen_history') or [])
    history.append({
        'action': action,
        'actor': actor,
        'note': note,
        'action_at': event_at,
        'from_state': 'archived',
        'to_state': restored_state,
        'restore_route': restore_routes,
    })
    entry['status'] = restored_state
    entry['archive_reopen_pending'] = action == 'reopen'
    entry['restored_at'] = event_at
    entry['restored_by'] = actor
    entry['restore_note'] = note
    entry['restored_from_archive'] = True
    entry['reopen_history'] = history[-12:]
    entry['restore_audit'] = {
        'last_action': action,
        'actor': actor,
        'note': note,
        'restored_at': event_at,
        'restored_to_state': restored_state,
        'restore_routes': restore_routes,
    }
    entry['archive_metadata'] = {
        **archive_meta,
        'last_restore_action': action,
        'last_restore_at': event_at,
        'last_restored_to_state': restored_state,
        'restore_routes': restore_routes,
    }
    consequence = dict(entry.get('consequence') or {})
    entry['consequence'] = _default_consequence_payload(
        consequence_state=restored_state,
        decision_type=f'archive_{action}',
        source_proposal_id=proposal_id,
        target_proposal_id=consequence.get('target_proposal_id'),
        target_rulebook_state='reviewing' if action == 'reopen' else (consequence.get('target_rulebook_state') or 'active'),
        note=note or f'archive {action}',
        updated_at=event_at,
        cycle_id=consequence.get('cycle_id') or None,
        merge_candidate_id=consequence.get('merge_candidate_id') or '',
        conflict_id=consequence.get('conflict_id') or '',
        resolution_type=consequence.get('resolution_type') or '',
    )
    items[proposal_id] = entry
    registry['items'] = items
    registry['generated_at'] = event_at
    _write_json(_local_rulebook_registry_path(state_root), registry)
    conflict_id = consequence.get('conflict_id')
    if action == 'reopen' and conflict_id:
        conflict_registry = _load_json(_conflict_registry_path(state_root))
        conflict_items = conflict_registry.get('items', {}) if isinstance(conflict_registry.get('items'), dict) else {}
        conflict_entry = conflict_items.get(conflict_id) if isinstance(conflict_items.get(conflict_id), dict) else None
        if conflict_entry:
            conflict_entry['conflict_state'] = 'open'
            conflict_entry['resolution_type'] = None
            conflict_entry['adjudicator'] = actor
            conflict_entry['adjudicated_at'] = event_at
            conflict_entry['adjudication_note'] = note or 'reopened from archive restore workflow'
            history2 = list(conflict_entry.get('governance_history') or [])
            history2.append({
                'action': 'reopen_from_archive',
                'previous_state': 'resolved',
                'next_state': 'open',
                'adjudicator': actor,
                'adjudicated_at': event_at,
                'adjudication_note': note,
                'resolution_type': None,
            })
            conflict_entry['governance_history'] = history2[-12:]
            conflict_items[conflict_id] = conflict_entry
            conflict_registry['items'] = conflict_items
            conflict_registry['generated_at'] = event_at
            _write_json(_conflict_registry_path(state_root), conflict_registry)
    for path in (_local_rulebook_artifact_dir(state_root) / f'{proposal_id}.json', _governed_artifact_dir(state_root) / f'{proposal_id}.json'):
        _update_json_artifact(path, lambda payload: payload.update({
            'status': restored_state,
            'archive_reopen_pending': entry.get('archive_reopen_pending'),
            'archive_metadata': entry.get('archive_metadata'),
            'reopen_history': entry.get('reopen_history'),
            'restore_audit': entry.get('restore_audit'),
            'consequence': entry.get('consequence'),
        }))
    restore_registry = _load_archive_restore_registry(state_root)
    restore_items = restore_registry.get('items', {})
    restore_id = f'{action}:{proposal_id}:{event_at}'
    restore_items[restore_id] = {
        'restore_id': restore_id,
        'proposal_id': proposal_id,
        'candidate_key': entry.get('candidate_key'),
        'action': action,
        'actor': actor,
        'note': note,
        'action_at': event_at,
        'from_state': 'archived',
        'to_state': restored_state,
        'archive_policy': archive_meta.get('archived_policy'),
        'archived_reason_family': archive_meta.get('archived_reason_family'),
        'shared_governance_rule': archive_meta.get('shared_governance_rule', False),
    }
    restore_registry.update({
        'generated_at': event_at,
        'cycle_id': registry.get('cycle_id'),
        'items': restore_items,
        'restored_count': sum(1 for item in restore_items.values() if isinstance(item, dict) and item.get('action') == 'restore'),
        'reopened_count': sum(1 for item in restore_items.values() if isinstance(item, dict) and item.get('action') == 'reopen'),
        'revived_count': sum(1 for item in restore_items.values() if isinstance(item, dict) and item.get('action') == 'revive'),
        'restore_state_counts': {state: sum(1 for item in restore_items.values() if isinstance(item, dict) and item.get('to_state') == state) for state in sorted({str((item.get('to_state') or '')) for item in restore_items.values() if isinstance(item, dict) and item.get('to_state')})},
        'recent_archive_actions': sorted([item for item in restore_items.values() if isinstance(item, dict)], key=lambda x: str(x.get('action_at') or ''), reverse=True)[:8],
    })
    _write_json(_archive_restore_registry_path(state_root), restore_registry)
    _append_transition_event(
        state_root=state_root, proposal_id=proposal_id, candidate_key=entry.get('candidate_key') or '', from_state='archived', to_state=restored_state,
        trigger=f'archive_{action}', actor=actor, reason=note, related_registry='archive_restore_registry', cycle_id=str(registry.get('cycle_id') or ''),
        transition_type=f'archive_{action}', archive_policy=archive_meta.get('archived_policy') or '', archived_reason_family=archive_meta.get('archived_reason_family') or '',
        source_targets=entry.get('source_targets') or {}, extra={'shared_governance_rule': archive_meta.get('shared_governance_rule', False)}
    )
    return entry


def _write_archive_restore_review(*, state_root: Path, cycle_id: str, restore_registry: dict[str, Any], archive_policy_review: dict[str, Any], consequence_review: dict[str, Any], consequence_history: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in (restore_registry.get('items') or {}).values() if isinstance(item, dict)]
    recent_actions = sorted(items, key=lambda x: str(x.get('action_at') or ''), reverse=True)[:8]
    outcome_counts: dict[str, int] = {}
    shared_action_count = 0
    for item in items:
        outcome = str(item.get('action') or 'unknown')
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if item.get('shared_governance_rule'):
            shared_action_count += 1
    shared_source_archived_count = max(shared_action_count, int(archive_policy_review.get('shared_release_rollback_governance_count', 0) or 0), int(consequence_history.get('shared_source_archived_count', 0) or 0))
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'restore_state_counts': dict(restore_registry.get('restore_state_counts') or {}),
        'reopen_count': int(restore_registry.get('reopened_count', 0) or 0),
        'revive_count': int(restore_registry.get('revived_count', 0) or 0),
        'restore_count': int(restore_registry.get('restored_count', 0) or 0),
        'shared_source_archived_count': shared_source_archived_count,
        'restore_outcome_counts': outcome_counts,
        'recent_restore_actions': recent_actions,
        'recent_restore_timeline': recent_actions,
        'archive_policy_counts': archive_policy_review.get('archive_policy_counts', {}),
        'archive_evidence_scope_counts': archive_policy_review.get('archive_evidence_scope_counts', {}),
        'consequence_state_counts': consequence_review.get('local_rulebook_state_counts', {}),
        'reviewing_rule_count': consequence_review.get('local_rulebook_state_counts', {}).get('reviewing', 0),
        'consequence_history_event_count': consequence_history.get('history_event_count', 0),
        'recent_consequence_transitions': consequence_history.get('recent_transitions', []),
    }
    _write_json(_archive_restore_review_json_path(state_root), payload)
    lines = [
        '# Archive Restore Review',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- restore_state_counts: {_render(payload.get('restore_state_counts'))}",
        f"- restore/reopen/revive: {payload.get('restore_count')} / {payload.get('reopen_count')} / {payload.get('revive_count')}",
        f"- shared_source_archived_count: {payload.get('shared_source_archived_count')}",
        f"- reviewing_rule_count: {payload.get('reviewing_rule_count')}",
        '',
        '## recent_restore_actions',
    ]
    if recent_actions:
        for item in recent_actions:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | action={item.get('action')} | state={item.get('to_state')} | shared={item.get('shared_governance_rule')} | at={item.get('action_at')}")
    else:
        lines.append('- none')
    lines.extend(['', '## recent_consequence_transitions'])
    if payload.get('recent_consequence_transitions'):
        for item in payload.get('recent_consequence_transitions') or []:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | {item.get('from_state') or 'n/a'} -> {item.get('to_state') or 'n/a'} | type={item.get('transition_type')} | at={item.get('event_at')}")
    else:
        lines.append('- none')
    _archive_restore_timeline_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    _write_json(_archive_restore_timeline_json_path(state_root), payload)
    _archive_restore_review_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def _archive_terminal_rulebook_entries(*, state_root: Path, cycle_id: str, local_items: dict[str, Any]) -> dict[str, Any]:
    audit_items = _load_json(_archive_audit_path(state_root)).get('items', {}) if isinstance(_load_json(_archive_audit_path(state_root)).get('items'), dict) else {}
    transitions = []
    for proposal_id, item in list(local_items.items()):
        if not isinstance(item, dict) or not proposal_id:
            continue
        status = str(item.get('status') or '')
        consequence = item.get('consequence') or {}
        decision_type = str(consequence.get('decision_type') or '')
        resolution_type = str(consequence.get('resolution_type') or '')
        archive_reason = ''
        source_state = status
        if status == 'duplicate_blocked':
            archive_reason = 'duplicate_blocked_terminal'
        elif status == 'inactive_conflict_rejected' and resolution_type in {'reject_new', 'reject_old'}:
            archive_reason = 'conflict_rejected_terminal'
        elif status == 'inactive_superseded':
            archive_reason = 'superseded_terminal'
        elif status == 'inactive_merged':
            archive_reason = 'merged_terminal'
        elif status == 'archived':
            archive_reason = str(item.get('archive_reason') or consequence.get('note') or 'archived')
        if item.get('archive_reopen_pending') and status == 'active':
            continue
        if not archive_reason:
            continue
        archive_metadata = _build_archive_metadata(item=item, archive_reason=archive_reason, source_state=source_state)
        if status != 'archived':
            item['status'] = 'archived'
            item['archived_at'] = _now()
            item['archived_from_state'] = source_state
            item['archive_reason'] = archive_reason
            item['archive_target_proposal_id'] = consequence.get('target_proposal_id')
            item['archive_metadata'] = archive_metadata
            item['consequence'] = _default_consequence_payload(
                consequence_state='archived',
                decision_type='archived',
                source_proposal_id=proposal_id,
                target_proposal_id=consequence.get('target_proposal_id'),
                target_rulebook_state=consequence.get('target_rulebook_state') or 'active',
                note=archive_reason,
                updated_at=item.get('archived_at'),
                cycle_id=cycle_id,
                merge_candidate_id=consequence.get('merge_candidate_id') or '',
                conflict_id=consequence.get('conflict_id') or '',
                resolution_type=resolution_type,
            )
            local_items[proposal_id] = item
            _apply_consequence_to_artifact(_local_rulebook_artifact_dir(state_root) / f'{proposal_id}.json', item['consequence'])
            _apply_consequence_to_artifact(_governed_artifact_dir(state_root) / f'{proposal_id}.json', item['consequence'])
        if status == 'archived' and 'archive_metadata' not in item:
            item['archive_metadata'] = archive_metadata
        audit_key = f"archive:{proposal_id}:{item.get('archived_at') or consequence.get('updated_at') or cycle_id}"
        if audit_key not in audit_items:
            audit_items[audit_key] = {
                'audit_id': audit_key,
                'proposal_id': proposal_id,
                'candidate_key': item.get('candidate_key'),
                'archived_at': item.get('archived_at') or consequence.get('updated_at') or _now(),
                'cycle_id': cycle_id,
                'from_state': source_state,
                'to_state': 'archived',
                'archive_reason': archive_reason,
                'target_proposal_id': item.get('archive_target_proposal_id') or consequence.get('target_proposal_id'),
                'resolution_type': resolution_type or None,
                'decision_type': decision_type or 'archived',
                'archive_metadata': item.get('archive_metadata') or archive_metadata,
                'archived_policy': (item.get('archive_metadata') or archive_metadata).get('archived_policy'),
                'restorable': (item.get('archive_metadata') or archive_metadata).get('restorable'),
            }
        _append_transition_event(
            state_root=state_root, proposal_id=proposal_id, candidate_key=item.get('candidate_key') or '', from_state=source_state, to_state='archived',
            trigger='archive_terminal', actor='system', reason=archive_reason, related_registry='archive_audit_registry', cycle_id=cycle_id,
            transition_type='archive', target_proposal_id=item.get('archive_target_proposal_id') or consequence.get('target_proposal_id') or '',
            archive_policy=(item.get('archive_metadata') or archive_metadata).get('archived_policy') or '', archived_reason_family=(item.get('archive_metadata') or archive_metadata).get('archived_reason_family') or '',
            resolution_type=resolution_type or '', source_targets=item.get('source_targets') or {}, extra={'shared_governance_rule': (item.get('archive_metadata') or archive_metadata).get('shared_governance_rule', False)}
        )
        transitions.append(audit_items[audit_key])
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'archived_transition_count': len(transitions),
        'items': audit_items,
        'recent_archived_items': sorted(transitions, key=lambda x: str(x.get('archived_at') or ''), reverse=True)[:8],
    }
    _write_json(_archive_audit_path(state_root), payload)
    return payload


def _build_rule_precedence_review(*, state_root: Path, cycle_id: str, local_items: dict[str, Any], merge_queue_review: dict[str, Any], conflict_registry: dict[str, Any]) -> dict[str, Any]:
    decisions = []
    override_counts = {}
    for item in local_items.values():
        if not isinstance(item, dict) or not item.get('proposal_id'):
            continue
        drivers = []
        if item.get('duplicate_candidates') or str(item.get('archive_reason') or '').startswith('duplicate_'):
            drivers.append(('duplicate', PRECEDENCE_PRIORITY['duplicate']))
        if item.get('conflict_candidates') or str(item.get('latest_conflict_id') or ''):
            drivers.append(('conflict', PRECEDENCE_PRIORITY['conflict']))
        if item.get('supersedes') or item.get('superseded_by'):
            drivers.append(('supersede', PRECEDENCE_PRIORITY['supersede']))
        if item.get('merge_candidates') or item.get('merged_into_proposal_id') or item.get('merged_from_proposal_ids'):
            drivers.append(('merge', PRECEDENCE_PRIORITY['merge']))
        if len(drivers) < 2:
            continue
        drivers = sorted(drivers, key=lambda x: (-x[1], x[0]))
        winner = drivers[0][0]
        suppressed = [name for name,_ in drivers[1:]]
        for name in suppressed:
            key=f'{winner}>{name}'
            override_counts[key]=override_counts.get(key,0)+1
        decisions.append({
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'final_state': item.get('status'),
            'winner': winner,
            'suppressed': suppressed,
            'drivers': [name for name,_ in drivers],
            'latest_conflict_id': item.get('latest_conflict_id'),
            'merged_into_proposal_id': item.get('merged_into_proposal_id'),
            'superseded_by': item.get('superseded_by'),
            'archive_reason': item.get('archive_reason'),
            'updated_at': ((item.get('consequence') or {}).get('updated_at')),
        })
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'precedence_matrix': {
            'duplicate': ['conflict', 'supersede', 'merge'],
            'conflict': ['supersede', 'merge'],
            'supersede': ['merge'],
            'merge': [],
        },
        'decision_count': len(decisions),
        'override_counts': override_counts,
        'recent_precedence_decisions': sorted(decisions, key=lambda x: str(x.get('updated_at') or ''), reverse=True)[:8],
        'items': decisions,
    }
    _write_json(_rule_precedence_review_json_path(state_root), payload)
    lines=['# Rule Precedence Review','',f"- generated_at: {payload.get('generated_at')}",f"- cycle_id: {payload.get('cycle_id')}",f"- decision_count: {payload.get('decision_count')}",f"- override_counts: {_render(payload.get('override_counts'))}",'', '## recent_precedence_decisions']
    if payload['recent_precedence_decisions']:
        for item in payload['recent_precedence_decisions']:
            lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | winner={item.get('winner')} | suppressed={_render(item.get('suppressed'))} | state={item.get('final_state')} | archive_reason={item.get('archive_reason') or 'n/a'}")
    else:
        lines.append('- none')
    _rule_precedence_review_md_path(state_root).write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
    return payload


def build_governed_rule_artifact(*, proposal: dict[str, Any], cycle_id: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    return {
        'artifact_version': 'governed-rule-candidate/v1',
        'proposal_id': proposal.get('proposal_id'),
        'candidate_key': proposal.get('candidate_key'),
        'candidate_kind': proposal.get('candidate_kind'),
        'sink_target': proposal.get('sink_target'),
        'proposal_state': proposal.get('proposal_state'),
        'governance': {
            'reviewer': proposal.get('reviewer'),
            'reviewed_at': proposal.get('reviewed_at'),
            'decision_note': proposal.get('decision_note'),
            'history': list(proposal.get('governance_history', []) or []),
        },
        'traceability': {
            'cycle_id': cycle_id or proposal.get('last_seen_cycle_id') or proposal.get('first_seen_cycle_id'),
            'first_seen_cycle_id': proposal.get('first_seen_cycle_id'),
            'last_seen_cycle_id': proposal.get('last_seen_cycle_id'),
            'source_targets': proposal.get('source_targets', {}),
            'source_themes': proposal.get('source_themes', {}),
            'source_patterns': proposal.get('source_patterns', {}),
            'evidence_count': proposal.get('evidence_count', 0),
        },
        'semantic_governance': {
            'semantic_group_key': proposal.get('semantic_group_key'),
            'semantic_tokens': list(proposal.get('semantic_tokens', []) or []),
            'merge_candidate_count': proposal.get('merge_candidate_count', 0),
            'conflict_candidate_count': proposal.get('conflict_candidate_count', 0),
            'duplicate_candidate_count': proposal.get('duplicate_candidate_count', 0),
            'merge_candidates': list(proposal.get('merge_candidates', []) or []),
            'conflict_candidates': list(proposal.get('conflict_candidates', []) or []),
            'duplicate_candidates': list(proposal.get('duplicate_candidates', []) or []),
            'merge_reason': proposal.get('merge_reason'),
            'conflict_reason': proposal.get('conflict_reason'),
            'duplicate_reason': proposal.get('duplicate_reason'),
        },
        'consequence': _default_consequence_payload(
            consequence_state='active',
            decision_type='accepted',
            source_proposal_id=proposal.get('proposal_id'),
            note=proposal.get('decision_note') or 'accepted_governed_rule',
            cycle_id=cycle_id or proposal.get('last_seen_cycle_id') or proposal.get('first_seen_cycle_id') or '',
        ),
        'evidence': list(proposal.get('evidence', []) or []),
        'generated_at': _now(),
    }


def build_local_rulebook_artifact(*, governed_artifact: dict[str, Any], registry_entry: dict[str, Any], cycle_id: str = '', export_target: str = 'local-rulebook') -> dict[str, Any]:
    proposal_id = governed_artifact.get('proposal_id')
    revision = int(registry_entry.get('revision', 1) or 1)
    return {
        'artifact_version': 'local-rulebook-item/v2',
        'rulebook_item_id': f'rulebook-{proposal_id}',
        'proposal_id': proposal_id,
        'candidate_key': governed_artifact.get('candidate_key'),
        'candidate_kind': governed_artifact.get('candidate_kind'),
        'candidate_topic_key': _candidate_topic_key(governed_artifact.get('candidate_key')),
        'relation_key': registry_entry.get('relation_key'),
        'content_fingerprint': registry_entry.get('content_fingerprint'),
        'status': registry_entry.get('status', 'active'),
        'revision': revision,
        'version': registry_entry.get('version', _version_string(revision)),
        'supersedes': list(registry_entry.get('supersedes', []) or []),
        'superseded_by': registry_entry.get('superseded_by'),
        'sink_target': governed_artifact.get('sink_target'),
        'export_target': export_target,
        'exported_at': _now(),
        'governance': {
            'reviewer': ((governed_artifact.get('governance') or {}).get('reviewer')),
            'reviewed_at': ((governed_artifact.get('governance') or {}).get('reviewed_at')),
            'decision_note': ((governed_artifact.get('governance') or {}).get('decision_note')),
        },
        'semantic_governance': dict((governed_artifact.get('semantic_governance') or {})),
        'traceability': {
            'cycle_id': cycle_id or ((governed_artifact.get('traceability') or {}).get('cycle_id')),
            'governed_artifact_path': registry_entry.get('artifact_path'),
            'source_targets': ((governed_artifact.get('traceability') or {}).get('source_targets', {})),
            'source_themes': ((governed_artifact.get('traceability') or {}).get('source_themes', {})),
            'source_patterns': ((governed_artifact.get('traceability') or {}).get('source_patterns', {})),
            'evidence_count': ((governed_artifact.get('traceability') or {}).get('evidence_count', 0)),
        },
        'consequence': dict(registry_entry.get('consequence') or _default_consequence_payload(
            consequence_state=registry_entry.get('status', 'active'),
            decision_type='exported',
            source_proposal_id=proposal_id,
            cycle_id=cycle_id or ((governed_artifact.get('traceability') or {}).get('cycle_id')) or '',
        )),
        'evidence': list(governed_artifact.get('evidence', []) or []),
    }


def _append_compact_linkage(existing: list[dict[str, Any]] | None, linkage: dict[str, Any], *, key_fields: tuple[str, ...] = ('linkage_key',)) -> list[dict[str, Any]]:
    items = [dict(item) for item in list(existing or []) if isinstance(item, dict)]
    key = tuple(str(linkage.get(field) or '') for field in key_fields)
    if key and any(tuple(str(item.get(field) or '') for field in key_fields) == key for item in items):
        return items
    items.append(dict(linkage))
    items.sort(key=lambda item: str(item.get('linked_at') or ''), reverse=True)
    return items[:12]


def _update_json_artifact(path: Path, updater) -> None:
    if not path.exists():
        return
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return
    updater(payload)
    _write_json(path, payload)


def _build_rule_decision_linkage_review(*, state_root: Path, cycle_id: str, local_items: dict[str, Any], merge_queue_review: dict[str, Any], conflict_registry: dict[str, Any]) -> dict[str, Any]:
    proposal_registry = _load_json(_registry_path(state_root))
    proposal_entries = proposal_registry.get('proposals', {}) if isinstance(proposal_registry.get('proposals'), dict) else {}
    sink_registry = _load_json(_sink_registry_path(state_root))
    sink_items = sink_registry.get('items', {}) if isinstance(sink_registry.get('items'), dict) else {}
    linkage_items: list[dict[str, Any]] = []
    linkage_audit: dict[str, Any] = {}

    def ensure_entry(container: dict[str, Any], key: str) -> dict[str, Any]:
        current = container.get(key)
        if not isinstance(current, dict):
            current = {'proposal_id': key}
            container[key] = current
        return current

    def apply_to_registry(entry: dict[str, Any], linkage: dict[str, Any], *, role: str) -> None:
        entry['decision_linkage_state'] = 'linked'
        entry['decision_linkage_updated_at'] = linkage.get('linked_at')
        entry['decision_linkage_types'] = sorted({*(entry.get('decision_linkage_types') or []), linkage.get('linkage_type')})
        compact = {
            'linkage_key': linkage.get('linkage_key'),
            'linkage_type': linkage.get('linkage_type'),
            'role': role,
            'counterparty_proposal_id': linkage.get('target_proposal_id') if role == 'source' else linkage.get('source_proposal_id'),
            'conflict_id': linkage.get('conflict_id'),
            'merge_candidate_id': linkage.get('merge_candidate_id'),
            'resolution_type': linkage.get('resolution_type'),
            'linked_at': linkage.get('linked_at'),
            'cycle_id': linkage.get('cycle_id'),
        }
        entry['decision_linkages'] = _append_compact_linkage(entry.get('decision_linkages'), compact)
        if linkage.get('linkage_type') == 'merge_accepted':
            if role == 'source':
                entry['merged_into_proposal_id'] = linkage.get('target_proposal_id')
                entry['status'] = 'inactive_merged'
                entry['target_rulebook_state'] = 'active'
                entry['consequence'] = _default_consequence_payload(
                    consequence_state='inactive_merged',
                    decision_type='merge_accepted',
                    source_proposal_id=entry.get('proposal_id'),
                    target_proposal_id=linkage.get('target_proposal_id'),
                    target_rulebook_state='active',
                    note=linkage.get('reason') or 'merge accepted',
                    updated_at=linkage.get('linked_at'),
                    cycle_id=linkage.get('cycle_id'),
                    merge_candidate_id=linkage.get('merge_candidate_id'),
                )
                _append_transition_event(state_root=state_root, proposal_id=str(entry.get('proposal_id') or ''), candidate_key=entry.get('candidate_key') or '', from_state='active', to_state='inactive_merged', trigger='decision_linkage_merge_accepted', actor='system', reason=linkage.get('reason') or '', related_registry='rule_decision_linkage_review', cycle_id=str(linkage.get('cycle_id') or ''), transition_type='merge_accepted', target_proposal_id=linkage.get('target_proposal_id') or '', merge_candidate_id=linkage.get('merge_candidate_id') or '', source_targets=entry.get('source_targets') or {})
                _append_transition_event(state_root=state_root, proposal_id=str(entry.get('proposal_id') or ''), candidate_key=entry.get('candidate_key') or '', from_state='active', to_state='active', trigger='decision_linkage_supersede_source_active', actor='system', reason=linkage.get('reason') or '', related_registry='rule_decision_linkage_review', cycle_id=str(linkage.get('cycle_id') or ''), transition_type='supersede_source_active', target_proposal_id=linkage.get('target_proposal_id') or '', source_targets=entry.get('source_targets') or {})
            elif role == 'target':
                merged_from = list(entry.get('merged_from_proposal_ids') or [])
                if linkage.get('source_proposal_id') and linkage.get('source_proposal_id') not in merged_from:
                    merged_from.append(linkage.get('source_proposal_id'))
                entry['merged_from_proposal_ids'] = sorted(merged_from)
                entry['status'] = 'active'
                entry['consequence'] = _default_consequence_payload(
                    consequence_state='active',
                    decision_type='merge_target_retained',
                    source_proposal_id=entry.get('proposal_id'),
                    target_proposal_id=linkage.get('source_proposal_id'),
                    target_rulebook_state='active',
                    note=linkage.get('reason') or 'merge target retained',
                    updated_at=linkage.get('linked_at'),
                    cycle_id=linkage.get('cycle_id'),
                    merge_candidate_id=linkage.get('merge_candidate_id'),
                )
                _append_transition_event(state_root=state_root, proposal_id=str(entry.get('proposal_id') or ''), candidate_key=entry.get('candidate_key') or '', from_state='active', to_state='active', trigger='decision_linkage_merge_target_retained', actor='system', reason=linkage.get('reason') or '', related_registry='rule_decision_linkage_review', cycle_id=str(linkage.get('cycle_id') or ''), transition_type='merge_target_retained', target_proposal_id=linkage.get('source_proposal_id') or '', merge_candidate_id=linkage.get('merge_candidate_id') or '', source_targets=entry.get('source_targets') or {})
        elif linkage.get('linkage_type') == 'supersede_linked':
            if role == 'source':
                entry['supersedes'] = sorted({*(entry.get('supersedes') or []), linkage.get('target_proposal_id')})
                entry['status'] = 'active'
                entry['consequence'] = _default_consequence_payload(
                    consequence_state='active',
                    decision_type='supersede_new_active',
                    source_proposal_id=entry.get('proposal_id'),
                    target_proposal_id=linkage.get('target_proposal_id'),
                    target_rulebook_state='inactive_superseded',
                    note=linkage.get('reason') or 'superseding rule active',
                    updated_at=linkage.get('linked_at'),
                    cycle_id=linkage.get('cycle_id'),
                )
            elif role == 'target':
                entry['superseded_by'] = linkage.get('source_proposal_id')
                entry['status'] = 'inactive_superseded'
                entry['target_rulebook_state'] = 'active'
                entry['consequence'] = _default_consequence_payload(
                    consequence_state='inactive_superseded',
                    decision_type='superseded_by_new_rule',
                    source_proposal_id=entry.get('proposal_id'),
                    target_proposal_id=linkage.get('source_proposal_id'),
                    target_rulebook_state='active',
                    note=linkage.get('reason') or 'superseded by newer active rule',
                    updated_at=linkage.get('linked_at'),
                    cycle_id=linkage.get('cycle_id'),
                )
                _append_transition_event(state_root=state_root, proposal_id=str(entry.get('proposal_id') or ''), candidate_key=entry.get('candidate_key') or '', from_state='active', to_state='inactive_superseded', trigger='decision_linkage_supersede_target_inactive', actor='system', reason=linkage.get('reason') or '', related_registry='rule_decision_linkage_review', cycle_id=str(linkage.get('cycle_id') or ''), transition_type='supersede_target_inactive', target_proposal_id=linkage.get('source_proposal_id') or '', source_targets=entry.get('source_targets') or {})
        elif linkage.get('linkage_type') in {'conflict_resolved', 'conflict_rejected'}:
            entry['latest_conflict_id'] = linkage.get('conflict_id')
            entry['latest_conflict_state'] = linkage.get('decision_state')
            entry['latest_conflict_resolution_type'] = linkage.get('resolution_type')
            resolution = str(linkage.get('resolution_type') or '')
            consequence_state, decision_type, target_state = _conflict_resolution_outcome(
                resolution=resolution,
                decision_state=str(linkage.get('decision_state') or ''),
                role=role,
            )
            entry['status'] = consequence_state
            entry['consequence'] = _default_consequence_payload(
                consequence_state=consequence_state,
                decision_type=decision_type,
                source_proposal_id=entry.get('proposal_id'),
                target_proposal_id=(linkage.get('target_proposal_id') if role == 'source' else linkage.get('source_proposal_id')),
                target_rulebook_state=target_state,
                note=linkage.get('reason') or 'conflict adjudicated',
                updated_at=linkage.get('linked_at'),
                cycle_id=linkage.get('cycle_id'),
                conflict_id=linkage.get('conflict_id'),
                resolution_type=resolution,
            )
            _append_transition_event(state_root=state_root, proposal_id=str(entry.get('proposal_id') or ''), candidate_key=entry.get('candidate_key') or '', from_state=None, to_state=consequence_state, trigger=f'conflict_{resolution or action}', actor='system', reason=linkage.get('reason') or 'conflict adjudicated', related_registry='rule_decision_linkage_review', cycle_id=str(linkage.get('cycle_id') or ''), transition_type=decision_type, target_proposal_id=(linkage.get('target_proposal_id') if role == 'source' else linkage.get('source_proposal_id')) or '', conflict_id=linkage.get('conflict_id') or '', resolution_type=resolution or '', source_targets=entry.get('source_targets') or {}, extra={'decision_state': linkage.get('decision_state'), 'role': role})

    def apply_artifact_linkage(proposal_id: str, linkage: dict[str, Any], *, role: str) -> None:
        governed_path = _governed_artifact_dir(state_root) / f'{proposal_id}.json'
        local_path = _local_rulebook_artifact_dir(state_root) / f'{proposal_id}.json'
        compact = {
            'linkage_key': linkage.get('linkage_key'),
            'linkage_type': linkage.get('linkage_type'),
            'role': role,
            'counterparty_proposal_id': linkage.get('target_proposal_id') if role == 'source' else linkage.get('source_proposal_id'),
            'merge_candidate_id': linkage.get('merge_candidate_id'),
            'conflict_id': linkage.get('conflict_id'),
            'resolution_type': linkage.get('resolution_type'),
            'linked_at': linkage.get('linked_at'),
            'cycle_id': linkage.get('cycle_id'),
        }
        for path in (governed_path, local_path):
            _update_json_artifact(path, lambda payload: payload.update({
                'decision_linkage': {
                    **(payload.get('decision_linkage') or {}),
                    'state': 'linked',
                    'updated_at': linkage.get('linked_at'),
                    'items': _append_compact_linkage(((payload.get('decision_linkage') or {}).get('items') or []), compact),
                }
            }))
        proposal_entry = proposal_entries.get(proposal_id, {}) if isinstance(proposal_entries.get(proposal_id), dict) else {}
        sink_entry = sink_items.get(proposal_id, {}) if isinstance(sink_items.get(proposal_id), dict) else {}
        local_entry = local_items.get(proposal_id, {}) if isinstance(local_items.get(proposal_id), dict) else {}
        consequence = dict((local_entry.get('consequence') or sink_entry.get('consequence') or proposal_entry.get('consequence') or {}))
        if consequence:
            _apply_consequence_to_artifact(governed_path, consequence)
            _apply_consequence_to_artifact(local_path, consequence)

    def record_linkage(linkage: dict[str, Any]) -> None:
        linkage_items.append(linkage)
        linkage_audit[linkage['linkage_key']] = linkage
        for proposal_id, role in ((linkage.get('source_proposal_id'), 'source'), (linkage.get('target_proposal_id'), 'target')):
            if not proposal_id:
                continue
            apply_to_registry(ensure_entry(proposal_entries, proposal_id), linkage, role=role)
            apply_to_registry(ensure_entry(sink_items, proposal_id), linkage, role=role)
            local_entry = local_items.get(proposal_id)
            if isinstance(local_entry, dict):
                apply_to_registry(local_entry, linkage, role=role)
            apply_artifact_linkage(proposal_id, linkage, role=role)

    for item in list((merge_queue_review.get('items') or {}).values()):
        if str(item.get('review_state') or '') != 'accepted':
            continue
        source_id = str(item.get('source_rule') or '')
        target_id = str(item.get('target_rule') or '')
        if not source_id or not target_id:
            continue
        linkage_key = f"merge:{item.get('candidate_id')}:{source_id}:{target_id}"
        record_linkage({
            'linkage_key': linkage_key,
            'linkage_type': 'merge_accepted',
            'cycle_id': cycle_id,
            'linked_at': item.get('reviewed_at') or _now(),
            'decision_state': item.get('review_state'),
            'merge_candidate_id': item.get('candidate_id'),
            'source_proposal_id': source_id,
            'target_proposal_id': target_id,
            'source_candidate_key': item.get('source_candidate_key'),
            'target_candidate_key': item.get('target_candidate_key'),
            'source_targets': item.get('source_targets', {}),
            'target_source_targets': item.get('target_source_targets', {}),
            'reason': item.get('reason'),
        })
        item['linkage_state'] = 'linked'
        item['linked_at'] = item.get('reviewed_at') or _now()
        item['linked_proposal_ids'] = [source_id, target_id]

    for entry in list(local_items.values()):
        if not isinstance(entry, dict):
            continue
        source_id = str(entry.get('proposal_id') or '')
        for target_id in list(entry.get('supersedes') or []):
            if not source_id or not target_id:
                continue
            record_linkage({
                'linkage_key': f'supersede:{source_id}:{target_id}',
                'linkage_type': 'supersede_linked',
                'cycle_id': cycle_id,
                'linked_at': entry.get('exported_at') or _now(),
                'decision_state': entry.get('status'),
                'source_proposal_id': source_id,
                'target_proposal_id': target_id,
                'source_candidate_key': entry.get('candidate_key'),
                'target_candidate_key': (local_items.get(target_id) or {}).get('candidate_key'),
                'source_targets': entry.get('source_targets', {}),
                'target_source_targets': (local_items.get(target_id) or {}).get('source_targets', {}),
                'reason': 'local_rulebook_supersede_chain',
            })

    for item in list((conflict_registry.get('items') or {}).values()):
        state = str(item.get('conflict_state') or '')
        if state not in {'resolved', 'rejected'}:
            continue
        linked_ids = list(item.get('conflicting_rule_ids') or [])[:2]
        if len(linked_ids) < 2:
            continue
        source_id, target_id = linked_ids[0], linked_ids[1]
        record_linkage({
            'linkage_key': f'conflict:{item.get("conflict_id")}:{state}',
            'linkage_type': f'conflict_{state}',
            'cycle_id': cycle_id,
            'linked_at': item.get('adjudicated_at') or _now(),
            'decision_state': state,
            'conflict_id': item.get('conflict_id'),
            'resolution_type': item.get('resolution_type'),
            'source_proposal_id': source_id,
            'target_proposal_id': target_id,
            'source_candidate_key': ((item.get('conflicting_proposals') or [{}])[0]).get('candidate_key'),
            'target_candidate_key': ((item.get('conflicting_proposals') or [{}, {}])[1]).get('candidate_key'),
            'source_targets': ((item.get('latest_shared_source_targets') or {}).get('left') or {}),
            'target_source_targets': ((item.get('latest_shared_source_targets') or {}).get('right') or {}),
            'reason': item.get('adjudication_note') or item.get('reason'),
        })
        item['linkage_state'] = 'linked'
        item['linked_at'] = item.get('adjudicated_at') or _now()

    proposal_registry['proposals'] = proposal_entries
    proposal_registry['generated_at'] = _now()
    sink_registry['items'] = sink_items
    sink_registry['generated_at'] = _now()
    _write_json(_registry_path(state_root), proposal_registry)
    _write_json(_sink_registry_path(state_root), sink_registry)
    _write_json(_merge_queue_registry_path(state_root), merge_queue_review)
    _write_json(_conflict_registry_path(state_root), conflict_registry)

    recent = sorted(linkage_items, key=lambda item: str(item.get('linked_at') or ''), reverse=True)[:8]
    review = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'post_decision_linkage_count': len(linkage_items),
        'merge_linked_count': sum(1 for item in linkage_items if item.get('linkage_type') == 'merge_accepted'),
        'supersede_linked_count': sum(1 for item in linkage_items if item.get('linkage_type') == 'supersede_linked'),
        'conflict_adjudicated_linked_count': sum(1 for item in linkage_items if str(item.get('linkage_type') or '').startswith('conflict_')),
        'recent_decision_linkages': recent,
        'items': linkage_items,
    }
    _write_json(state_root / 'rule_decision_linkage_review.json', review)
    _write_json(state_root / 'linkage_audit_registry.json', {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'item_count': len(linkage_audit),
        'items': linkage_audit,
    })
    lines = [
        '# Rule Decision Linkage Review',
        '',
        f"- generated_at: {review.get('generated_at')}",
        f"- cycle_id: {review.get('cycle_id')}",
        f"- post_decision_linkage_count: {review.get('post_decision_linkage_count')}",
        f"- merge_linked_count: {review.get('merge_linked_count')}",
        f"- supersede_linked_count: {review.get('supersede_linked_count')}",
        f"- conflict_adjudicated_linked_count: {review.get('conflict_adjudicated_linked_count')}",
        '',
        '## recent_decision_linkages',
    ]
    if recent:
        for item in recent:
            lines.append(f"- {item.get('linkage_type')} | {item.get('source_proposal_id')} -> {item.get('target_proposal_id')} | state={item.get('decision_state')} | resolution={item.get('resolution_type') or 'n/a'} | at={item.get('linked_at')}")
    else:
        lines.append('- none')
    (state_root / 'rule_decision_linkage_review.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return review


def _write_rulebook_markdown(*, payload: dict[str, Any], path: Path) -> Path:
    lines = [
        '# Local Rulebook Export',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- exported_count: {payload.get('exported_count')}",
        f"- already_exported_count: {payload.get('already_exported_count')}",
        f"- blocked_count: {payload.get('blocked_count')}",
        f"- local_rulebook_item_count: {payload.get('local_rulebook_item_count')}",
        f"- export_audit_available: {'yes' if payload.get('export_audit_available') else 'no'}",
        '',
        '## top_exported_rules',
    ]
    top = list(payload.get('top_exported_rules', []) or [])
    if not top:
        lines.append('- none')
    else:
        for item in top:
            lines.append(
                f"- {item.get('proposal_id')} | {item.get('candidate_key')} | export_status={item.get('export_status')} | evidence_count={item.get('evidence_count')} | reviewer={item.get('reviewer') or 'n/a'} | export_target={item.get('export_target') or 'n/a'}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _build_rule_registry_sync_audit(*, state_root: Path, cycle_id: str, proposal_entries: dict[str, Any], sink_items: dict[str, Any], local_items: dict[str, Any], conflict_registry: dict[str, Any], merge_queue_review: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    scope_exceptions: list[dict[str, Any]] = []
    proposal_ids = {str(k) for k, v in (proposal_entries or {}).items() if isinstance(v, dict)}
    sink_ids = {str(k) for k, v in (sink_items or {}).items() if isinstance(v, dict)}
    local_ids = {str(k) for k, v in (local_items or {}).items() if isinstance(v, dict)}
    shared_sample_registry_items: dict[str, Any] = {}

    def _record_scope_exception(item: dict[str, Any], *, registry_expectation: str, missing_in: list[str]) -> dict[str, Any]:
        archive_meta = item.get('archive_metadata') or {}
        entry = {
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'status': item.get('status'),
            'governance_disposition': registry_expectation,
            'missing_in': missing_in,
            'archive_policy': archive_meta.get('archived_policy'),
            'retained_as': archive_meta.get('retained_as'),
            'evidence_scope': archive_meta.get('evidence_scope'),
            'shared_governance_rule': archive_meta.get('shared_governance_rule', False),
            'source_targets': item.get('source_targets') or archive_meta.get('source_targets') or {},
            'traceability': {
                'archive_reason': archive_meta.get('archive_reason'),
                'target_proposal_id': ((item.get('consequence') or {}).get('target_proposal_id')),
                'rulebook_artifact_path': item.get('rulebook_artifact_path'),
            },
        }
        scope_exceptions.append(entry)
        shared_sample_registry_items[str(item.get('proposal_id') or '')] = entry
        return entry

    for proposal_id in sorted(local_ids):
        item = local_items.get(proposal_id) or {}
        archive_meta = item.get('archive_metadata') or {}
        shared_governance_rule = bool(item.get('shared_governance_rule', archive_meta.get('shared_governance_rule', False)))
        evidence_scope = str(item.get('evidence_scope') or archive_meta.get('evidence_scope') or '')
        is_archived = str(item.get('status') or '') == 'archived'
        retained_as = str(archive_meta.get('retained_as') or '')
        registry_expectation = 'registry_managed'
        if is_archived and shared_governance_rule and retained_as in {'duplicate_evidence', 'conflict_evidence', 'superseded_history', 'merge_history', 'historical_rule'}:
            registry_expectation = 'archived_legacy_sample'
        item_missing: list[str] = []
        if proposal_id not in proposal_ids:
            item_missing.append('proposal_registry')
        if proposal_id not in sink_ids:
            item_missing.append('governed_registry')
        if item_missing:
            if registry_expectation == 'archived_legacy_sample':
                _record_scope_exception(item, registry_expectation=registry_expectation, missing_in=item_missing)
            else:
                if 'proposal_registry' in item_missing:
                    issues.append({'severity': 'error', 'issue_type': 'local_rule_missing_proposal_registry', 'proposal_id': proposal_id, 'candidate_key': item.get('candidate_key')})
                if 'governed_registry' in item_missing:
                    issues.append({'severity': 'error', 'issue_type': 'local_rule_missing_governed_registry', 'proposal_id': proposal_id, 'candidate_key': item.get('candidate_key')})
        if str(item.get('status') or '') == 'active' and not (item.get('rulebook_artifact_path') and (state_root / str(item.get('rulebook_artifact_path'))).exists()):
            issues.append({'severity': 'error', 'issue_type': 'active_local_rule_artifact_missing', 'proposal_id': proposal_id, 'candidate_key': item.get('candidate_key')})
        shared_targets = item.get('source_targets') or archive_meta.get('source_targets') or {}
        if shared_governance_rule or evidence_scope == 'shared_release_rollback':
            if not (int(shared_targets.get('official_release', 0) or 0) > 0 and int(shared_targets.get('rollback', 0) or 0) > 0):
                issues.append({'severity': 'warn', 'issue_type': 'shared_release_rollback_evidence_missing', 'proposal_id': proposal_id, 'candidate_key': item.get('candidate_key'), 'source_targets': shared_targets, 'evidence_scope': evidence_scope or 'shared_release_rollback'})
        for target_id in list(item.get('supersedes') or []):
            target = local_items.get(str(target_id)) or {}
            if not isinstance(target, dict) or not target:
                issues.append({'severity': 'error', 'issue_type': 'supersede_target_missing', 'proposal_id': proposal_id, 'target_proposal_id': target_id})
                continue
            if target.get('superseded_by') != proposal_id:
                issues.append({'severity': 'error', 'issue_type': 'supersede_backlink_mismatch', 'proposal_id': proposal_id, 'target_proposal_id': target_id, 'target_superseded_by': target.get('superseded_by')})
    for proposal_id in sorted(sink_ids):
        entry = sink_items.get(proposal_id) or {}
        if str(entry.get('sink_state') or '') == 'exported' and proposal_id not in local_ids:
            issues.append({'severity': 'error', 'issue_type': 'exported_sink_missing_local_rulebook', 'proposal_id': proposal_id, 'candidate_key': entry.get('candidate_key')})
    for conflict in (conflict_registry.get('items') or {}).values():
        if not isinstance(conflict, dict):
            continue
        for ref in list(conflict.get('conflicting_rule_ids') or []):
            if str(ref) not in local_ids:
                issues.append({'severity': 'error', 'issue_type': 'conflict_reference_missing_local_rule', 'proposal_id': ref, 'conflict_id': conflict.get('conflict_id')})
    for merge in (merge_queue_review.get('items') or {}).values():
        if not isinstance(merge, dict):
            continue
        if str(merge.get('source_rule') or '') not in local_ids:
            issues.append({'severity': 'error', 'issue_type': 'merge_source_missing_local_rule', 'proposal_id': merge.get('source_rule'), 'merge_candidate_id': merge.get('candidate_id')})
        if str(merge.get('target_rule') or '') not in local_ids:
            issues.append({'severity': 'error', 'issue_type': 'merge_target_missing_local_rule', 'proposal_id': merge.get('target_rule'), 'merge_candidate_id': merge.get('candidate_id')})
    severity_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for issue in issues:
        sev = str(issue.get('severity') or 'warn')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        kind = str(issue.get('issue_type') or 'unknown')
        type_counts[kind] = type_counts.get(kind, 0) + 1
    scope_exception_counts: dict[str, int] = {}
    for item in scope_exceptions:
        kind = str(item.get('governance_disposition') or 'unspecified')
        scope_exception_counts[kind] = scope_exception_counts.get(kind, 0) + 1
    shared_sample_registry = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'item_count': len(shared_sample_registry_items),
        'governance_disposition_counts': scope_exception_counts,
        'items': shared_sample_registry_items,
    }
    _write_json(_shared_sample_governance_registry_json_path(state_root), shared_sample_registry)
    shared_lines = [
        '# Shared Sample Governance Registry',
        '',
        f"- generated_at: {shared_sample_registry.get('generated_at')}",
        f"- cycle_id: {shared_sample_registry.get('cycle_id')}",
        f"- item_count: {shared_sample_registry.get('item_count')}",
        f"- governance_disposition_counts: {_render(shared_sample_registry.get('governance_disposition_counts'))}",
        '',
        '## items',
    ]
    if shared_sample_registry_items:
        for item in shared_sample_registry_items.values():
            shared_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | disposition={item.get('governance_disposition')} | missing_in={_render(item.get('missing_in'))} | retained_as={item.get('retained_as') or 'n/a'} | evidence_scope={item.get('evidence_scope') or 'n/a'}")
    else:
        shared_lines.append('- none')
    _shared_sample_governance_registry_md_path(state_root).write_text('\n'.join(shared_lines) + '\n', encoding='utf-8')

    scope_review = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'audit_scope_refinement_available': True,
        'review_status': 'available',
        'sync_scope_exception_count': len(scope_exceptions),
        'scope_exception_counts': scope_exception_counts,
        'recent_scope_exceptions': scope_exceptions[:8],
        'shared_sample_governance_registry_available': True,
        'shared_sample_governance_registry_path': _shared_sample_governance_registry_json_path(state_root).name,
    }
    _write_json(_rule_registry_sync_scope_review_json_path(state_root), scope_review)
    scope_lines = [
        '# Rule Registry Sync Scope Review',
        '',
        f"- generated_at: {scope_review.get('generated_at')}",
        f"- cycle_id: {scope_review.get('cycle_id')}",
        f"- audit_scope_refinement_available: {scope_review.get('audit_scope_refinement_available')}",
        f"- review_status: {scope_review.get('review_status')}",
        f"- sync_scope_exception_count: {scope_review.get('sync_scope_exception_count')}",
        f"- scope_exception_counts: {_render(scope_review.get('scope_exception_counts'))}",
        f"- shared_sample_governance_registry_available: {scope_review.get('shared_sample_governance_registry_available')}",
        f"- shared_sample_governance_registry_path: {scope_review.get('shared_sample_governance_registry_path')}",
        '',
        '## recent_scope_exceptions',
    ]
    if scope_review['recent_scope_exceptions']:
        for item in scope_review['recent_scope_exceptions']:
            scope_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | disposition={item.get('governance_disposition')} | missing_in={_render(item.get('missing_in'))} | retained_as={item.get('retained_as') or 'n/a'}")
    else:
        scope_lines.append('- none')
    _rule_registry_sync_scope_review_md_path(state_root).write_text('\n'.join(scope_lines) + '\n', encoding='utf-8')

    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id,
        'consistency_audit_available': True,
        'audit_scope_refinement_available': True,
        'registry_sync_review_available': True,
        'registry_sync_ok': not any(item.get('severity') == 'error' for item in issues),
        'registry_sync_issue_count': len(issues),
        'sync_scope_exception_count': len(scope_exceptions),
        'scope_exception_counts': scope_exception_counts,
        'severity_counts': severity_counts,
        'issue_type_counts': type_counts,
        'recent_sync_issues': issues[:8],
        'recent_scope_exceptions': scope_exceptions[:8],
        'registry_counts': {
            'proposal_registry_count': len(proposal_ids),
            'governed_registry_count': len(sink_ids),
            'local_rulebook_count': len(local_ids),
            'shared_sample_governance_count': len(shared_sample_registry_items),
            'conflict_registry_count': int(conflict_registry.get('conflict_count', 0) or 0),
            'merge_queue_count': int(merge_queue_review.get('queue_count', 0) or 0),
        },
        'sync_scope_review': scope_review,
        'shared_sample_governance_registry': {
            'item_count': len(shared_sample_registry_items),
            'path': _shared_sample_governance_registry_json_path(state_root).name,
        },
        'issues': issues,
        'scope_exceptions': scope_exceptions,
    }
    _write_json(_rule_registry_sync_audit_json_path(state_root), payload)
    lines = [
        '# Rule Registry Sync Audit',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- consistency_audit_available: {payload.get('consistency_audit_available')}",
        f"- audit_scope_refinement_available: {payload.get('audit_scope_refinement_available')}",
        f"- registry_sync_review_available: {payload.get('registry_sync_review_available')}",
        f"- registry_sync_ok: {payload.get('registry_sync_ok')}",
        f"- registry_sync_issue_count: {payload.get('registry_sync_issue_count')}",
        f"- sync_scope_exception_count: {payload.get('sync_scope_exception_count')}",
        f"- severity_counts: {_render(payload.get('severity_counts'))}",
        f"- issue_type_counts: {_render(payload.get('issue_type_counts'))}",
        f"- scope_exception_counts: {_render(payload.get('scope_exception_counts'))}",
        f"- registry_counts: {_render(payload.get('registry_counts'))}",
        '',
        '## recent_sync_issues',
    ]
    if payload['recent_sync_issues']:
        for item in payload['recent_sync_issues']:
            lines.append(f"- severity={item.get('severity')} | type={item.get('issue_type')} | proposal_id={item.get('proposal_id') or 'n/a'} | target={item.get('target_proposal_id') or item.get('merge_candidate_id') or item.get('conflict_id') or 'n/a'} | candidate_key={item.get('candidate_key') or 'n/a'}")
    else:
        lines.append('- none')
    lines.extend(['', '## recent_scope_exceptions'])
    if payload['recent_scope_exceptions']:
        for item in payload['recent_scope_exceptions']:
            lines.append(f"- proposal_id={item.get('proposal_id') or 'n/a'} | candidate_key={item.get('candidate_key') or 'n/a'} | disposition={item.get('governance_disposition') or 'n/a'} | missing_in={_render(item.get('missing_in'))} | retained_as={item.get('retained_as') or 'n/a'}")
    else:
        lines.append('- none')
    _rule_registry_sync_audit_md_path(state_root).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return payload


def export_rulebook_artifacts(*, rule_proposal_review: dict[str, Any], state_root: Path = STATE_ROOT, cycle_id: str = '', export_target: str = 'local-rulebook') -> dict[str, Any]:
    registry = _load_json(_sink_registry_path(state_root))
    registry_items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    proposal_registry = _load_json(_registry_path(state_root))
    proposal_entries = proposal_registry.get('proposals', {}) if isinstance(proposal_registry.get('proposals'), dict) else {}
    local_registry = _load_json(_local_rulebook_registry_path(state_root))
    local_items = local_registry.get('items', {}) if isinstance(local_registry.get('items'), dict) else {}
    audit_payload = _load_json(_local_rulebook_export_audit_path(state_root))
    audit_items = list(audit_payload.get('items', []) or []) if isinstance(audit_payload.get('items'), list) else []
    export_results: list[dict[str, Any]] = []
    export_status_counts: dict[str, int] = {}

    accepted_proposals = {
        str(item.get('proposal_id')): item
        for item in list(rule_proposal_review.get('proposals', []) or [])
        if item.get('proposal_state') == 'accepted' and item.get('proposal_id')
    }

    for proposal_id, proposal in accepted_proposals.items():
        registry_entry = registry_items.get(proposal_id, {}) if isinstance(registry_items.get(proposal_id), dict) else {}
        governed_rel = str(registry_entry.get('artifact_path') or '')
        governed_path = state_root / governed_rel if governed_rel else _governed_artifact_dir(state_root) / f'{proposal_id}.json'
        local_path = _local_rulebook_artifact_dir(state_root) / f'{proposal_id}.json'
        relation_key = _relation_key(str(proposal.get('candidate_kind') or ''), str(proposal.get('candidate_key') or ''))
        content_fingerprint = _content_fingerprint(
            candidate_kind=str(proposal.get('candidate_kind') or ''),
            candidate_key=str(proposal.get('candidate_key') or ''),
            source_targets=proposal.get('source_targets', {}) or {},
            source_themes=proposal.get('source_themes', {}) or {},
            source_patterns=proposal.get('source_patterns', {}) or {},
            evidence=list(proposal.get('evidence', []) or []),
        )
        audit_entry = {
            'proposal_id': proposal_id,
            'candidate_key': proposal.get('candidate_key'),
            'relation_key': relation_key,
            'content_fingerprint': content_fingerprint,
            'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
            'export_target': export_target,
            'checked_at': _now(),
        }

        active_related = [
            item for item in local_items.values()
            if isinstance(item, dict) and item.get('status') == 'active' and item.get('relation_key') == relation_key and item.get('proposal_id') != proposal_id
        ]
        duplicate_match = next((
            item for item in local_items.values()
            if isinstance(item, dict) and item.get('content_fingerprint') == content_fingerprint and item.get('proposal_id') != proposal_id
        ), None)

        if proposal.get('proposal_state') != 'accepted':
            audit_entry['export_status'] = 'blocked'
            audit_entry['guard_reason'] = 'proposal_not_accepted'
        elif registry_entry.get('sink_state') not in {'written', 'exported'}:
            audit_entry['export_status'] = 'blocked'
            audit_entry['guard_reason'] = 'sink_not_written'
        elif not governed_path.exists():
            audit_entry['export_status'] = 'blocked'
            audit_entry['guard_reason'] = 'governed_artifact_missing'
        elif local_path.exists() or isinstance(local_items.get(proposal_id), dict):
            audit_entry['export_status'] = 'already_exported'
            audit_entry['guard_reason'] = 'duplicate_export_guard'
            audit_entry['rulebook_artifact_path'] = _artifact_relpath(local_path, state_root=state_root)
        elif duplicate_match:
            audit_entry['export_status'] = 'duplicate_blocked'
            audit_entry['guard_reason'] = 'duplicate_content_guard'
            audit_entry['duplicate_of'] = duplicate_match.get('proposal_id')
            audit_entry['rulebook_artifact_path'] = duplicate_match.get('rulebook_artifact_path')
            duplicate_entry = {
                'proposal_id': proposal_id,
                'candidate_key': proposal.get('candidate_key'),
                'candidate_kind': proposal.get('candidate_kind'),
                'candidate_topic_key': _candidate_topic_key(proposal.get('candidate_key')),
                'relation_key': relation_key,
                'semantic_group_key': proposal.get('semantic_group_key'),
                'semantic_tokens': list(proposal.get('semantic_tokens', []) or []),
                'content_fingerprint': content_fingerprint,
                'status': 'duplicate_blocked',
                'duplicate_of': duplicate_match.get('proposal_id'),
                'duplicate_reason': proposal.get('duplicate_reason') or 'duplicate_content_guard',
                'merge_candidates': list(proposal.get('merge_candidates', []) or []),
                'conflict_candidates': list(proposal.get('conflict_candidates', []) or []),
                'duplicate_candidates': list(proposal.get('duplicate_candidates', []) or []),
                'reviewer': proposal.get('reviewer'),
                'reviewed_at': proposal.get('reviewed_at'),
                'decision_note': proposal.get('decision_note'),
                'evidence_count': proposal.get('evidence_count', 0),
                'source_targets': proposal.get('source_targets', {}),
                'governed_artifact_path': registry_entry.get('artifact_path'),
                'rulebook_artifact_path': duplicate_match.get('rulebook_artifact_path'),
                'export_target': export_target,
                'exported_at': None,
                'revision': duplicate_match.get('revision'),
                'version': duplicate_match.get('version'),
                'supersedes': [],
                'superseded_by': None,
                'duplicate_blocked_at': audit_entry['checked_at'],
                'consequence': _default_consequence_payload(consequence_state='duplicate_blocked', decision_type='duplicate_blocked', source_proposal_id=proposal_id, target_proposal_id=duplicate_match.get('proposal_id'), target_rulebook_state=duplicate_match.get('status'), note='duplicate_content_guard', updated_at=audit_entry['checked_at'], cycle_id=cycle_id or rule_proposal_review.get('cycle_id')),
            }
            local_items[proposal_id] = duplicate_entry
            _append_transition_event(state_root=state_root, proposal_id=proposal_id, candidate_key=proposal.get('candidate_key') or '', from_state=None, to_state='duplicate_blocked', trigger='duplicate_content_guard', actor='system', reason='duplicate_content_guard', related_registry='local_rulebook_registry', cycle_id=cycle_id or rule_proposal_review.get('cycle_id') or '', transition_type='duplicate_blocked', target_proposal_id=duplicate_match.get('proposal_id') or '', source_targets=proposal.get('source_targets') or {})
            registry_entry['sink_state'] = 'written'
            registry_entry['rulebook_artifact_path'] = duplicate_match.get('rulebook_artifact_path')
        else:
            governed_artifact = _load_json(governed_path)
            prior_chain = [
                item for item in local_items.values()
                if isinstance(item, dict) and item.get('relation_key') == relation_key
            ]
            revision = max([int(item.get('revision', 0) or 0) for item in prior_chain] + [0]) + 1
            supersedes = [item.get('proposal_id') for item in active_related if item.get('proposal_id')]
            registry_entry['relation_key'] = relation_key
            registry_entry['content_fingerprint'] = content_fingerprint
            registry_entry['revision'] = revision
            registry_entry['version'] = _version_string(revision)
            registry_entry['status'] = 'active'
            registry_entry['supersedes'] = supersedes
            registry_entry['superseded_by'] = None
            registry_entry['candidate_topic_key'] = _candidate_topic_key(proposal.get('candidate_key'))
            registry_entry['consequence'] = _default_consequence_payload(consequence_state='active', decision_type='exported_active', source_proposal_id=proposal_id, note='exported into local rulebook', updated_at=_now(), cycle_id=cycle_id or rule_proposal_review.get('cycle_id'))
            local_artifact = build_local_rulebook_artifact(
                governed_artifact=governed_artifact,
                registry_entry=registry_entry,
                cycle_id=cycle_id,
                export_target=export_target,
            )
            _write_json(local_path, local_artifact)
            registry_entry['sink_state'] = 'exported'
            registry_entry['exported_at'] = local_artifact.get('exported_at')
            registry_entry['export_target'] = export_target
            registry_entry['rulebook_artifact_path'] = _artifact_relpath(local_path, state_root=state_root)
            local_items[proposal_id] = {
                'proposal_id': proposal_id,
                'candidate_key': proposal.get('candidate_key'),
                'candidate_kind': proposal.get('candidate_kind'),
                'candidate_topic_key': _candidate_topic_key(proposal.get('candidate_key')),
                'relation_key': relation_key,
                'semantic_group_key': proposal.get('semantic_group_key'),
                'semantic_tokens': list(proposal.get('semantic_tokens', []) or []),
                'content_fingerprint': content_fingerprint,
                'sink_target': proposal.get('sink_target'),
                'status': 'active',
                'reviewer': proposal.get('reviewer'),
                'reviewed_at': proposal.get('reviewed_at'),
                'decision_note': proposal.get('decision_note'),
                'evidence_count': proposal.get('evidence_count', 0),
                'source_targets': proposal.get('source_targets', {}),
                'merge_candidate_count': proposal.get('merge_candidate_count', 0),
                'conflict_candidate_count': proposal.get('conflict_candidate_count', 0),
                'duplicate_candidate_count': proposal.get('duplicate_candidate_count', 0),
                'merge_candidates': list(proposal.get('merge_candidates', []) or []),
                'conflict_candidates': list(proposal.get('conflict_candidates', []) or []),
                'duplicate_candidates': list(proposal.get('duplicate_candidates', []) or []),
                'merge_reason': proposal.get('merge_reason'),
                'conflict_reason': proposal.get('conflict_reason'),
                'duplicate_reason': proposal.get('duplicate_reason'),
                'governed_artifact_path': registry_entry.get('artifact_path'),
                'rulebook_artifact_path': registry_entry.get('rulebook_artifact_path'),
                'export_target': export_target,
                'exported_at': registry_entry.get('exported_at'),
                'revision': revision,
                'version': _version_string(revision),
                'supersedes': supersedes,
                'superseded_by': None,
                'consequence': dict(registry_entry.get('consequence') or {}),
            }
            if supersedes:
                for prior_id in supersedes:
                    prior_item = local_items.get(prior_id, {}) if isinstance(local_items.get(prior_id), dict) else {}
                    prior_item['status'] = 'inactive_superseded'
                    prior_item['superseded_by'] = proposal_id
                    prior_item['consequence'] = _default_consequence_payload(consequence_state='inactive_superseded', decision_type='superseded_by_new_rule', source_proposal_id=prior_id, target_proposal_id=proposal_id, target_rulebook_state='active', note='superseded during local rulebook export', updated_at=registry_entry.get('exported_at'), cycle_id=cycle_id or rule_proposal_review.get('cycle_id'))
                    local_items[prior_id] = prior_item
                    _append_transition_event(state_root=state_root, proposal_id=prior_id, candidate_key=prior_item.get('candidate_key') or '', from_state='active', to_state='inactive_superseded', trigger='local_rulebook_supersede_export', actor='system', reason='superseded during local rulebook export', related_registry='local_rulebook_registry', cycle_id=cycle_id or rule_proposal_review.get('cycle_id') or '', transition_type='superseded_by_new_rule', target_proposal_id=proposal_id, source_targets=prior_item.get('source_targets') or {})
                    _apply_consequence_to_artifact(_local_rulebook_artifact_dir(state_root) / f'{prior_id}.json', prior_item['consequence'])
                    _apply_consequence_to_artifact(_governed_artifact_dir(state_root) / f'{prior_id}.json', prior_item['consequence'])
            audit_entry['export_status'] = 'exported'
            audit_entry['rulebook_artifact_path'] = registry_entry.get('rulebook_artifact_path')
            audit_entry['governed_artifact_path'] = registry_entry.get('artifact_path')
            audit_entry['revision'] = revision
            audit_entry['version'] = _version_string(revision)
            audit_entry['supersedes'] = supersedes
            audit_entry['supersede_candidate'] = bool(supersedes)

        export_results.append({
            'proposal_id': proposal_id,
            'candidate_key': proposal.get('candidate_key'),
            'reviewer': proposal.get('reviewer'),
            'decision_note': proposal.get('decision_note'),
            'evidence_count': proposal.get('evidence_count', 0),
            'source_targets': proposal.get('source_targets', {}),
            'relation_key': relation_key,
            'content_fingerprint': content_fingerprint,
            'revision': audit_entry.get('revision') or (local_items.get(proposal_id, {}) or {}).get('revision'),
            'version': audit_entry.get('version') or (local_items.get(proposal_id, {}) or {}).get('version'),
            'export_target': export_target,
            'export_status': audit_entry.get('export_status'),
            'guard_reason': audit_entry.get('guard_reason'),
            'duplicate_of': audit_entry.get('duplicate_of'),
            'supersedes': audit_entry.get('supersedes') or ((local_items.get(proposal_id, {}) or {}).get('supersedes')),
            'rulebook_artifact_path': audit_entry.get('rulebook_artifact_path') or registry_entry.get('rulebook_artifact_path'),
        })
        export_status = audit_entry.get('export_status', 'blocked')
        export_status_counts[export_status] = export_status_counts.get(export_status, 0) + 1
        audit_items.append(audit_entry)
        registry_items[proposal_id] = registry_entry

    registry['items'] = registry_items
    registry['generated_at'] = _now()
    _write_json(_sink_registry_path(state_root), registry)

    status_counts: dict[str, int] = {}
    supersede_candidates = []
    top_merge_items: list[dict[str, Any]] = []
    top_conflict_items: list[dict[str, Any]] = []
    top_duplicate_items: list[dict[str, Any]] = []
    for item in local_items.values():
        if not isinstance(item, dict) or not item.get('proposal_id'):
            continue
        status = str(item.get('status') or 'active')
        status_counts[status] = status_counts.get(status, 0) + 1
        if item.get('supersedes'):
            supersede_candidates.append({
                'proposal_id': item.get('proposal_id'),
                'candidate_key': item.get('candidate_key'),
                'semantic_group_key': item.get('semantic_group_key'),
                'version': item.get('version'),
                'revision': item.get('revision'),
                'supersedes': item.get('supersedes'),
                'source_targets': item.get('source_targets', {}),
            })
        if item.get('merge_candidate_count', 0) > 0:
            top_merge_items.append({
                'proposal_id': item.get('proposal_id'),
                'candidate_key': item.get('candidate_key'),
                'semantic_group_key': item.get('semantic_group_key'),
                'merge_candidate_count': item.get('merge_candidate_count', 0),
                'merge_reason': item.get('merge_reason'),
            })
        if item.get('conflict_candidate_count', 0) > 0:
            top_conflict_items.append({
                'proposal_id': item.get('proposal_id'),
                'candidate_key': item.get('candidate_key'),
                'semantic_group_key': item.get('semantic_group_key'),
                'conflict_candidate_count': item.get('conflict_candidate_count', 0),
                'conflict_reason': item.get('conflict_reason'),
            })
        if item.get('duplicate_candidate_count', 0) > 0 or status == 'duplicate_blocked':
            top_duplicate_items.append({
                'proposal_id': item.get('proposal_id'),
                'candidate_key': item.get('candidate_key'),
                'semantic_group_key': item.get('semantic_group_key'),
                'duplicate_candidate_count': item.get('duplicate_candidate_count', 0),
                'duplicate_reason': item.get('duplicate_reason'),
                'status': status,
            })

    conflict_registry = _load_json(_conflict_registry_path(state_root))
    conflict_items = conflict_registry.get('items', {}) if isinstance(conflict_registry.get('items'), dict) else {}
    if not conflict_items:
        seeded: dict[str, Any] = {}
        for item in local_items.values():
            if not isinstance(item, dict) or not item.get('proposal_id'):
                continue
            for peer in list(item.get('conflict_candidates', []) or []):
                peer_id = peer.get('proposal_id')
                if not peer_id:
                    continue
                semantic_group_key = item.get('semantic_group_key') or ''
                conflict_id = _conflict_id(item.get('proposal_id'), peer_id, semantic_group_key)
                if conflict_id in seeded:
                    continue
                peer_item = local_items.get(peer_id, {}) if isinstance(local_items.get(peer_id), dict) else {}
                seeded[conflict_id] = {
                    'conflict_id': conflict_id,
                    'semantic_group_key': semantic_group_key,
                    'conflict_state': 'open',
                    'reason': peer.get('reason') or item.get('conflict_reason'),
                    'similarity': peer.get('similarity'),
                    'conflicting_rule_ids': [item.get('proposal_id'), peer_id],
                    'conflicting_proposals': [
                        {'proposal_id': item.get('proposal_id'), 'candidate_key': item.get('candidate_key'), 'proposal_state': 'accepted', 'source_targets': item.get('source_targets', {})},
                        {'proposal_id': peer_id, 'candidate_key': peer_item.get('candidate_key'), 'proposal_state': 'accepted', 'source_targets': peer_item.get('source_targets', {})},
                    ],
                    'adjudication_note': None,
                    'adjudicator': None,
                    'adjudicated_at': None,
                    'resolution_type': None,
                    'governance_history': [],
                    'first_seen_cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
                    'last_seen_cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
                }
        if seeded:
            conflict_registry = {
                'generated_at': _now(),
                'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
                'conflict_count': len(seeded),
                'state_counts': {'open': len(seeded)},
                'open_count': len(seeded),
                'reviewing_count': 0,
                'resolved_count': 0,
                'rejected_count': 0,
                'superseded_count': 0,
                'top_conflict_items': [
                    {
                        'conflict_id': item['conflict_id'],
                        'semantic_group_key': item.get('semantic_group_key'),
                        'conflict_state': item.get('conflict_state'),
                        'resolution_type': item.get('resolution_type'),
                        'adjudicator': item.get('adjudicator'),
                        'adjudicated_at': item.get('adjudicated_at'),
                        'conflicting_rule_ids': item.get('conflicting_rule_ids', []),
                        'conflicting_proposals': item.get('conflicting_proposals', []),
                        'reason': item.get('reason'),
                        'similarity': item.get('similarity'),
                    }
                    for item in list(seeded.values())[:5]
                ],
                'recent_adjudications': [],
                'items': seeded,
            }
            _write_json(_conflict_registry_path(state_root), conflict_registry)
    merge_queue_review = _build_merge_queue_registry(local_items=local_items, cycle_id=cycle_id or rule_proposal_review.get('cycle_id'), state_root=state_root)
    registry_sync_audit = _build_rule_registry_sync_audit(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        proposal_entries=proposal_entries,
        sink_items=registry_items,
        local_items=local_items,
        conflict_registry=conflict_registry,
        merge_queue_review=merge_queue_review,
    )
    decision_linkage_review = _build_rule_decision_linkage_review(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        local_items=local_items,
        merge_queue_review=merge_queue_review,
        conflict_registry=conflict_registry,
    )
    archive_audit = _archive_terminal_rulebook_entries(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        local_items=local_items,
    )
    archive_policy_review = _write_archive_policy_review(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        local_items=local_items,
        archive_audit=archive_audit,
    )
    archive_restore_registry = _load_archive_restore_registry(state_root)
    precedence_review = _build_rule_precedence_review(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        local_items=local_items,
        merge_queue_review=merge_queue_review,
        conflict_registry=conflict_registry,
    )
    local_rulebook_item_count = len([item for item in local_items.values() if isinstance(item, dict) and _normalize_consequence_state((item.get('consequence') or {}).get('state') or item.get('status') or 'active') in {'active', 'reviewing', 'inactive_merged', 'inactive_superseded', 'inactive_conflict_rejected', 'archived'}])
    consequence_review = _write_rule_consequence_review(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        proposal_entries=proposal_entries,
        sink_items=registry_items,
        local_items=local_items,
        restore_registry=archive_restore_registry,
    )
    archive_restore_review = _write_archive_restore_review(
        state_root=state_root,
        cycle_id=cycle_id or rule_proposal_review.get('cycle_id'),
        restore_registry=archive_restore_registry,
        archive_policy_review=archive_policy_review,
        consequence_review=consequence_review,
        consequence_history=consequence_review.get('consequence_history', {}),
    )
    governance_review = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'registry_status_counts': status_counts,
        'consequence_state_counts': consequence_review.get('local_rulebook_state_counts', {}),
        'proposal_consequence_state_counts': consequence_review.get('proposal_registry_state_counts', {}),
        'governed_consequence_state_counts': consequence_review.get('governed_rule_state_counts', {}),
        'active_rule_count': consequence_review.get('active_rule_count', 0),
        'inactive_rule_count': consequence_review.get('inactive_rule_count', 0),
        'archived_rule_count': consequence_review.get('archived_rule_count', 0),
        'merged_rule_count': consequence_review.get('merged_rule_count', 0),
        'superseded_rule_count': consequence_review.get('superseded_rule_count', 0),
        'duplicate_blocked_count': status_counts.get('duplicate_blocked', 0),
        'conflict_resolution_type_counts': consequence_review.get('conflict_resolution_type_counts', {}),
        'recent_consequence_updates': consequence_review.get('recent_consequence_updates', []),
        'consequence_history_available': consequence_review.get('consequence_history_available', False),
        'consequence_history_event_count': consequence_review.get('consequence_history_event_count', 0),
        'recent_consequence_transitions': consequence_review.get('recent_consequence_transitions', []),
        'transition_ledger_available': consequence_review.get('transition_ledger_available', False),
        'transition_event_count': consequence_review.get('transition_event_count', 0),
        'recent_transition_events': consequence_review.get('recent_transition_events', []),
        'top_transition_triggers': consequence_review.get('top_transition_triggers', {}),
        'archived_transition_count': archive_audit.get('archived_transition_count', 0),
        'recent_archived_items': archive_audit.get('recent_archived_items', []),
        'archive_policy_counts': archive_policy_review.get('archive_policy_counts', {}),
        'archived_restorable_count': archive_policy_review.get('archived_restorable_count', 0),
        'archived_reopened_count': archive_restore_registry.get('reopened_count', 0),
        'restore_count': archive_restore_registry.get('restored_count', 0),
        'reopen_count': archive_restore_registry.get('reopened_count', 0),
        'revive_count': archive_restore_registry.get('revived_count', 0),
        'restore_state_counts': archive_restore_registry.get('restore_state_counts', {}),
        'shared_source_archived_count': archive_restore_review.get('shared_source_archived_count', 0),
        'recent_restore_actions': archive_restore_review.get('recent_restore_actions', []),
        'recent_restore_timeline': archive_restore_review.get('recent_restore_timeline', []),
        'recent_archive_actions': sorted(list((archive_restore_registry.get('recent_archive_actions') or [])) + list(archive_audit.get('recent_archived_items', [])), key=lambda x: str(x.get('action_at') or x.get('archived_at') or ''), reverse=True)[:8],
        'archive_policy_review': archive_policy_review,
        'archive_restore_registry': archive_restore_registry,
        'archive_restore_review': archive_restore_review,
        'precedence_review_available': True,
        'precedence_decision_count': precedence_review.get('decision_count', 0),
        'precedence_override_counts': precedence_review.get('override_counts', {}),
        'recent_precedence_decisions': precedence_review.get('recent_precedence_decisions', []),
        'merge_candidate_count': sum(int(item.get('merge_candidate_count', 0) or 0) for item in local_items.values() if isinstance(item, dict)),
        'conflict_candidate_count': int(conflict_registry.get('conflict_count', 0) or 0),
        'conflict_state_counts': conflict_registry.get('state_counts', {}),
        'conflict_open_count': conflict_registry.get('open_count', 0),
        'conflict_reviewing_count': conflict_registry.get('reviewing_count', 0),
        'conflict_resolved_count': conflict_registry.get('resolved_count', 0),
        'duplicate_candidate_count': sum(int(item.get('duplicate_candidate_count', 0) or 0) for item in local_items.values() if isinstance(item, dict)),
        'merge_queue_count': merge_queue_review.get('queue_count', 0),
        'merge_queue_state_counts': merge_queue_review.get('state_counts', {}),
        'merge_queue_open_count': merge_queue_review.get('open_count', 0),
        'merge_queue_reviewing_count': merge_queue_review.get('reviewing_count', 0),
        'merge_queue_accepted_count': merge_queue_review.get('accepted_count', 0),
        'merge_queue_rejected_count': merge_queue_review.get('rejected_count', 0),
        'top_merge_targets': merge_queue_review.get('top_merge_targets', []),
        'top_supersede_suggestions': merge_queue_review.get('top_supersede_suggestions', []),
        'top_supersede_candidates': supersede_candidates[:5],
        'top_merge_items': sorted(top_merge_items, key=lambda x: (-int(x.get('merge_candidate_count', 0) or 0), str(x.get('candidate_key') or '')))[:5],
        'top_conflict_items': conflict_registry.get('top_conflict_items', []),
        'recent_adjudications': conflict_registry.get('recent_adjudications', []),
        'top_duplicate_items': sorted(top_duplicate_items, key=lambda x: (-int(x.get('duplicate_candidate_count', 0) or 0), str(x.get('candidate_key') or '')))[:5],
        'post_decision_linkage_count': decision_linkage_review.get('post_decision_linkage_count', 0),
        'merge_linked_count': decision_linkage_review.get('merge_linked_count', 0),
        'supersede_linked_count': decision_linkage_review.get('supersede_linked_count', 0),
        'conflict_adjudicated_linked_count': decision_linkage_review.get('conflict_adjudicated_linked_count', 0),
        'recent_decision_linkages': decision_linkage_review.get('recent_decision_linkages', []),
        'registry_sync_issue_count': registry_sync_audit.get('registry_sync_issue_count', 0),
        'recent_sync_issues': registry_sync_audit.get('recent_sync_issues', []),
        'consistency_audit_available': registry_sync_audit.get('consistency_audit_available', False),
        'audit_scope_refinement_available': registry_sync_audit.get('audit_scope_refinement_available', False),
        'registry_sync_review_available': registry_sync_audit.get('registry_sync_review_available', False),
        'sync_scope_exception_count': registry_sync_audit.get('sync_scope_exception_count', 0),
        'scope_exception_counts': registry_sync_audit.get('scope_exception_counts', {}),
        'recent_scope_exceptions': registry_sync_audit.get('recent_scope_exceptions', []),
        'shared_sample_governance_registry': registry_sync_audit.get('shared_sample_governance_registry', {}),
        'registry_sync_ok': registry_sync_audit.get('registry_sync_ok', False),
        'decision_linkage_review': decision_linkage_review,
        'registry_sync_audit': registry_sync_audit,
        'archive_audit': archive_audit,
        'precedence_review': precedence_review,
        'items': supersede_candidates,
    }
    _write_json(state_root / 'local_rulebook_governance_review.json', governance_review)
    md_lines = [
        '# Local Rulebook Governance Review',
        '',
        f"- generated_at: {governance_review.get('generated_at')}",
        f"- cycle_id: {governance_review.get('cycle_id')}",
        f"- registry_status_counts: {_render(governance_review.get('registry_status_counts'))}",
        f"- active_rule_count: {governance_review.get('active_rule_count')}",
        f"- inactive_rule_count: {governance_review.get('inactive_rule_count')}",
        f"- archived_rule_count: {governance_review.get('archived_rule_count')}",
        f"- merged_rule_count: {governance_review.get('merged_rule_count')}",
        f"- superseded_rule_count: {governance_review.get('superseded_rule_count')}",
        f"- duplicate_blocked_count: {governance_review.get('duplicate_blocked_count')}",
        f"- consequence_state_counts: {_render(governance_review.get('consequence_state_counts'))}",
        f"- conflict_resolution_type_counts: {_render(governance_review.get('conflict_resolution_type_counts'))}",
        f"- consequence_history_available: {governance_review.get('consequence_history_available')}",
        f"- consequence_history_event_count: {governance_review.get('consequence_history_event_count')}",
        f"- merge_candidate_count: {governance_review.get('merge_candidate_count')}",
        f"- conflict_candidate_count: {governance_review.get('conflict_candidate_count')}",
        f"- conflict_state_counts: {_render(governance_review.get('conflict_state_counts'))}",
        f"- conflict_open/reviewing/resolved: {governance_review.get('conflict_open_count')} / {governance_review.get('conflict_reviewing_count')} / {governance_review.get('conflict_resolved_count')}",
        f"- duplicate_candidate_count: {governance_review.get('duplicate_candidate_count')}",
        f"- merge_queue_count: {governance_review.get('merge_queue_count')}",
        f"- merge_queue_state_counts: {_render(governance_review.get('merge_queue_state_counts'))}",
        f"- consistency_audit_available: {governance_review.get('consistency_audit_available')}",
        f"- audit_scope_refinement_available: {governance_review.get('audit_scope_refinement_available')}",
        f"- registry_sync_review_available: {governance_review.get('registry_sync_review_available')}",
        f"- registry_sync_issue_count: {governance_review.get('registry_sync_issue_count')}",
        f"- sync_scope_exception_count: {governance_review.get('sync_scope_exception_count')}",
        f"- registry_sync_ok: {governance_review.get('registry_sync_ok')}",
        f"- post_decision_linkage_count: {governance_review.get('post_decision_linkage_count')}",
        f"- merge/supersede/conflict_linked: {governance_review.get('merge_linked_count')} / {governance_review.get('supersede_linked_count')} / {governance_review.get('conflict_adjudicated_linked_count')}",
        '',
        '## top_merge_targets',
    ]
    if governance_review['top_merge_targets']:
        for item in governance_review['top_merge_targets']:
            md_lines.append(f"- {item.get('target_rule')} | {item.get('target_candidate_key')} | suggestions={item.get('suggestion_count')} | priority_total={item.get('priority_score_total')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## top_supersede_candidates'])
    if governance_review['top_supersede_candidates']:
        for item in governance_review['top_supersede_candidates']:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | version={item.get('version')} | supersedes={_render(item.get('supersedes'))}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## top_supersede_suggestions'])
    if governance_review['top_supersede_suggestions']:
        for item in governance_review['top_supersede_suggestions']:
            md_lines.append(f"- {item.get('candidate_id')} | {item.get('source_candidate_key')} -> {item.get('target_candidate_key')} | priority={item.get('priority')}({item.get('priority_score')}) | state={item.get('review_state')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## top_merge_items'])
    if governance_review['top_merge_items']:
        for item in governance_review['top_merge_items']:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | semantic_group={item.get('semantic_group_key')} | merge_count={item.get('merge_candidate_count')} | reason={item.get('merge_reason')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## top_conflict_items'])
    if governance_review['top_conflict_items']:
        for item in governance_review['top_conflict_items']:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | semantic_group={item.get('semantic_group_key')} | conflict_count={item.get('conflict_candidate_count')} | reason={item.get('conflict_reason')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## top_duplicate_items'])
    if governance_review['top_duplicate_items']:
        for item in governance_review['top_duplicate_items']:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | semantic_group={item.get('semantic_group_key')} | duplicate_count={item.get('duplicate_candidate_count')} | status={item.get('status') or 'candidate'} | reason={item.get('duplicate_reason')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## recent_consequence_updates'])
    if governance_review['recent_consequence_updates']:
        for item in governance_review['recent_consequence_updates']:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | state={item.get('state')} | decision={item.get('decision_type')} | target={item.get('target_proposal_id') or 'n/a'} | resolution={item.get('resolution_type') or 'n/a'} | at={item.get('updated_at')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## recent_restore_timeline'])
    if governance_review.get('recent_restore_timeline'):
        for item in governance_review.get('recent_restore_timeline') or []:
            md_lines.append(f"- {item.get('proposal_id')} | {item.get('candidate_key')} | action={item.get('action')} | state={item.get('to_state')} | shared={item.get('shared_governance_rule')} | at={item.get('action_at')}")
    else:
        md_lines.append('- none')
    md_lines.extend(['', '## recent_decision_linkages'])
    if governance_review['recent_decision_linkages']:
        for item in governance_review['recent_decision_linkages']:
            md_lines.append(f"- {item.get('linkage_type')} | {item.get('source_proposal_id')} -> {item.get('target_proposal_id')} | state={item.get('decision_state')} | resolution={item.get('resolution_type') or 'n/a'} | at={item.get('linked_at')}")
    else:
        md_lines.append('- none')
    (state_root / 'local_rulebook_governance_review.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    local_registry_payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'item_count': local_rulebook_item_count,
        'registry_status_counts': status_counts,
        'active_rule_count': consequence_review.get('active_rule_count', 0),
        'inactive_rule_count': consequence_review.get('inactive_rule_count', 0),
        'archived_rule_count': consequence_review.get('archived_rule_count', 0),
        'merged_rule_count': consequence_review.get('merged_rule_count', 0),
        'superseded_rule_count': consequence_review.get('superseded_rule_count', 0),
        'duplicate_blocked_count': status_counts.get('duplicate_blocked', 0),
        'consequence_state_counts': consequence_review.get('local_rulebook_state_counts', {}),
        'proposal_consequence_state_counts': consequence_review.get('proposal_registry_state_counts', {}),
        'governed_consequence_state_counts': consequence_review.get('governed_rule_state_counts', {}),
        'conflict_resolution_type_counts': consequence_review.get('conflict_resolution_type_counts', {}),
        'recent_consequence_updates': consequence_review.get('recent_consequence_updates', []),
        'consequence_history_available': consequence_review.get('consequence_history_available', False),
        'consequence_history_event_count': consequence_review.get('consequence_history_event_count', 0),
        'recent_consequence_transitions': consequence_review.get('recent_consequence_transitions', []),
        'transition_ledger_available': governance_review.get('transition_ledger_available', False),
        'transition_event_count': governance_review.get('transition_event_count', 0),
        'unique_semantic_event_count': consequence_review.get('transition_digest', {}).get('unique_semantic_event_count', 0),
        'digest_duplicate_semantic_event_count': consequence_review.get('transition_digest', {}).get('digest_duplicate_semantic_event_count', 0),
        'transition_duplicate_suppressed_count': consequence_review.get('transition_digest', {}).get('transition_duplicate_suppressed_count', 0),
        'transition_digest_review_available': consequence_review.get('transition_digest', {}).get('transition_digest_review_available', False),
        'recent_transition_events': governance_review.get('recent_transition_events', []),
        'recent_suppressed_events': consequence_review.get('transition_digest', {}).get('recent_suppressed_events', []),
        'top_transition_triggers': governance_review.get('top_transition_triggers', {}),
        'archived_transition_count': governance_review.get('archived_transition_count', 0),
        'recent_archived_items': governance_review.get('recent_archived_items', []),
        'archive_policy_counts': governance_review.get('archive_policy_counts', {}),
        'archived_restorable_count': governance_review.get('archived_restorable_count', 0),
        'archived_reopened_count': governance_review.get('archived_reopened_count', 0),
        'restore_count': governance_review.get('restore_count', 0),
        'reopen_count': governance_review.get('reopen_count', 0),
        'revive_count': governance_review.get('revive_count', 0),
        'restore_state_counts': governance_review.get('restore_state_counts', {}),
        'shared_source_archived_count': governance_review.get('shared_source_archived_count', 0),
        'recent_restore_actions': governance_review.get('recent_restore_actions', []),
        'recent_restore_timeline': governance_review.get('recent_restore_timeline', []),
        'recent_archive_actions': governance_review.get('recent_archive_actions', []),
        'precedence_decision_count': governance_review.get('precedence_decision_count', 0),
        'precedence_override_counts': governance_review.get('precedence_override_counts', {}),
        'recent_precedence_decisions': governance_review.get('recent_precedence_decisions', []),
        'merge_candidate_count': governance_review.get('merge_candidate_count', 0),
        'conflict_candidate_count': governance_review.get('conflict_candidate_count', 0),
        'duplicate_candidate_count': governance_review.get('duplicate_candidate_count', 0),
        'merge_queue_count': governance_review.get('merge_queue_count', 0),
        'merge_queue_state_counts': governance_review.get('merge_queue_state_counts', {}),
        'merge_queue_open_count': governance_review.get('merge_queue_open_count', 0),
        'merge_queue_reviewing_count': governance_review.get('merge_queue_reviewing_count', 0),
        'merge_queue_accepted_count': governance_review.get('merge_queue_accepted_count', 0),
        'merge_queue_rejected_count': governance_review.get('merge_queue_rejected_count', 0),
        'top_merge_targets': governance_review.get('top_merge_targets', []),
        'top_supersede_suggestions': governance_review.get('top_supersede_suggestions', []),
        'top_merge_targets': governance_review.get('top_merge_targets', []),
        'top_supersede_suggestions': governance_review.get('top_supersede_suggestions', []),
        'top_supersede_candidates': supersede_candidates[:5],
        'top_merge_items': governance_review.get('top_merge_items', []),
        'top_conflict_items': governance_review.get('top_conflict_items', []),
        'top_duplicate_items': governance_review.get('top_duplicate_items', []),
        'post_decision_linkage_count': governance_review.get('post_decision_linkage_count', 0),
        'merge_linked_count': governance_review.get('merge_linked_count', 0),
        'supersede_linked_count': governance_review.get('supersede_linked_count', 0),
        'conflict_adjudicated_linked_count': governance_review.get('conflict_adjudicated_linked_count', 0),
        'recent_decision_linkages': governance_review.get('recent_decision_linkages', []),
        'consistency_audit_available': governance_review.get('consistency_audit_available', False),
        'audit_scope_refinement_available': governance_review.get('audit_scope_refinement_available', False),
        'registry_sync_review_available': governance_review.get('registry_sync_review_available', False),
        'registry_sync_issue_count': governance_review.get('registry_sync_issue_count', 0),
        'sync_scope_exception_count': governance_review.get('sync_scope_exception_count', 0),
        'scope_exception_counts': governance_review.get('scope_exception_counts', {}),
        'recent_sync_issues': governance_review.get('recent_sync_issues', []),
        'recent_scope_exceptions': governance_review.get('recent_scope_exceptions', []),
        'shared_sample_governance_registry': governance_review.get('shared_sample_governance_registry', {}),
        'registry_sync_ok': governance_review.get('registry_sync_ok', False),
        'items': local_items,
    }
    _write_json(_local_rulebook_registry_path(state_root), local_registry_payload)

    audit_summary = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'item_count': len(audit_items),
        'status_counts': export_status_counts,
        'items': audit_items,
    }
    _write_json(_local_rulebook_export_audit_path(state_root), audit_summary)

    top_exported_rules = [
        item for item in sorted(export_results, key=lambda x: (-int(x.get('evidence_count', 0) or 0), str(x.get('candidate_key') or '')))[:5]
    ]
    payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'export_target': export_target,
        'exported_count': export_status_counts.get('exported', 0),
        'already_exported_count': export_status_counts.get('already_exported', 0),
        'blocked_count': export_status_counts.get('blocked', 0),
        'duplicate_blocked_count': status_counts.get('duplicate_blocked', 0),
        'active_rule_count': consequence_review.get('active_rule_count', 0),
        'inactive_rule_count': consequence_review.get('inactive_rule_count', 0),
        'archived_rule_count': consequence_review.get('archived_rule_count', 0),
        'merged_rule_count': consequence_review.get('merged_rule_count', 0),
        'superseded_rule_count': consequence_review.get('superseded_rule_count', 0),
        'consequence_state_counts': consequence_review.get('local_rulebook_state_counts', {}),
        'proposal_consequence_state_counts': consequence_review.get('proposal_registry_state_counts', {}),
        'governed_consequence_state_counts': consequence_review.get('governed_rule_state_counts', {}),
        'conflict_resolution_type_counts': consequence_review.get('conflict_resolution_type_counts', {}),
        'recent_consequence_updates': consequence_review.get('recent_consequence_updates', []),
        'consequence_history_available': consequence_review.get('consequence_history_available', False),
        'consequence_history_event_count': consequence_review.get('consequence_history_event_count', 0),
        'recent_consequence_transitions': consequence_review.get('recent_consequence_transitions', []),
        'transition_ledger_available': governance_review.get('transition_ledger_available', False),
        'transition_event_count': governance_review.get('transition_event_count', 0),
        'unique_semantic_event_count': consequence_review.get('transition_digest', {}).get('unique_semantic_event_count', 0),
        'digest_duplicate_semantic_event_count': consequence_review.get('transition_digest', {}).get('digest_duplicate_semantic_event_count', 0),
        'transition_duplicate_suppressed_count': consequence_review.get('transition_digest', {}).get('transition_duplicate_suppressed_count', 0),
        'transition_digest_review_available': consequence_review.get('transition_digest', {}).get('transition_digest_review_available', False),
        'recent_transition_events': governance_review.get('recent_transition_events', []),
        'recent_suppressed_events': consequence_review.get('transition_digest', {}).get('recent_suppressed_events', []),
        'top_transition_triggers': governance_review.get('top_transition_triggers', {}),
        'archived_transition_count': governance_review.get('archived_transition_count', 0),
        'recent_archived_items': governance_review.get('recent_archived_items', []),
        'archive_policy_counts': governance_review.get('archive_policy_counts', {}),
        'archived_restorable_count': governance_review.get('archived_restorable_count', 0),
        'archived_reopened_count': governance_review.get('archived_reopened_count', 0),
        'restore_count': governance_review.get('restore_count', 0),
        'reopen_count': governance_review.get('reopen_count', 0),
        'revive_count': governance_review.get('revive_count', 0),
        'restore_state_counts': governance_review.get('restore_state_counts', {}),
        'shared_source_archived_count': governance_review.get('shared_source_archived_count', 0),
        'recent_restore_actions': governance_review.get('recent_restore_actions', []),
        'recent_restore_timeline': governance_review.get('recent_restore_timeline', []),
        'recent_archive_actions': governance_review.get('recent_archive_actions', []),
        'precedence_decision_count': governance_review.get('precedence_decision_count', 0),
        'precedence_override_counts': governance_review.get('precedence_override_counts', {}),
        'recent_precedence_decisions': governance_review.get('recent_precedence_decisions', []),
        'merge_candidate_count': governance_review.get('merge_candidate_count', 0),
        'conflict_candidate_count': governance_review.get('conflict_candidate_count', 0),
        'conflict_state_counts': governance_review.get('conflict_state_counts', {}),
        'conflict_open_count': governance_review.get('conflict_open_count', 0),
        'conflict_reviewing_count': governance_review.get('conflict_reviewing_count', 0),
        'conflict_resolved_count': governance_review.get('conflict_resolved_count', 0),
        'recent_adjudications': governance_review.get('recent_adjudications', []),
        'duplicate_candidate_count': governance_review.get('duplicate_candidate_count', 0),
        'merge_queue_count': governance_review.get('merge_queue_count', 0),
        'merge_queue_state_counts': governance_review.get('merge_queue_state_counts', {}),
        'merge_queue_open_count': governance_review.get('merge_queue_open_count', 0),
        'merge_queue_reviewing_count': governance_review.get('merge_queue_reviewing_count', 0),
        'merge_queue_accepted_count': governance_review.get('merge_queue_accepted_count', 0),
        'merge_queue_rejected_count': governance_review.get('merge_queue_rejected_count', 0),
        'export_status_counts': export_status_counts,
        'local_rulebook_item_count': local_rulebook_item_count,
        'export_audit_available': bool(audit_items),
        'governance_review_available': True,
        'top_exported_rules': top_exported_rules,
        'top_merge_targets': governance_review.get('top_merge_targets', []),
        'top_supersede_suggestions': governance_review.get('top_supersede_suggestions', []),
        'top_supersede_candidates': supersede_candidates[:5],
        'top_merge_items': governance_review.get('top_merge_items', []),
        'top_conflict_items': governance_review.get('top_conflict_items', []),
        'top_duplicate_items': governance_review.get('top_duplicate_items', []),
        'post_decision_linkage_count': governance_review.get('post_decision_linkage_count', 0),
        'merge_linked_count': governance_review.get('merge_linked_count', 0),
        'supersede_linked_count': governance_review.get('supersede_linked_count', 0),
        'conflict_adjudicated_linked_count': governance_review.get('conflict_adjudicated_linked_count', 0),
        'recent_decision_linkages': governance_review.get('recent_decision_linkages', []),
        'consistency_audit_available': governance_review.get('consistency_audit_available', False),
        'audit_scope_refinement_available': governance_review.get('audit_scope_refinement_available', False),
        'registry_sync_review_available': governance_review.get('registry_sync_review_available', False),
        'registry_sync_issue_count': governance_review.get('registry_sync_issue_count', 0),
        'sync_scope_exception_count': governance_review.get('sync_scope_exception_count', 0),
        'scope_exception_counts': governance_review.get('scope_exception_counts', {}),
        'recent_sync_issues': governance_review.get('recent_sync_issues', []),
        'recent_scope_exceptions': governance_review.get('recent_scope_exceptions', []),
        'shared_sample_governance_registry': governance_review.get('shared_sample_governance_registry', {}),
        'registry_sync_ok': governance_review.get('registry_sync_ok', False),
        'items': export_results,
    }
    _write_json(_local_rulebook_export_json_path(state_root), payload)
    _write_rulebook_markdown(payload=payload, path=_local_rulebook_export_md_path(state_root))
    return payload


def materialize_rule_sink(*, rule_proposal_review: dict[str, Any], state_root: Path = STATE_ROOT, cycle_id: str = '') -> dict[str, Any]:
    registry = _load_json(_sink_registry_path(state_root))
    registry_items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    accepted_rule_registry: dict[str, Any] = {}
    governed_rule_candidates: list[dict[str, Any]] = []
    sink_state_counts: dict[str, int] = {}
    sink_target_counts: dict[str, int] = {}

    accepted_proposals = [
        item for item in list(rule_proposal_review.get('proposals', []) or [])
        if item.get('proposal_state') == 'accepted'
    ]

    for proposal in accepted_proposals:
        proposal_id = str(proposal.get('proposal_id') or '').strip()
        if not proposal_id:
            continue
        existing = registry_items.get(proposal_id, {}) if isinstance(registry_items.get(proposal_id), dict) else {}
        sink_state = _normalize_sink_state(existing.get('sink_state') or '')
        artifact_path = _governed_artifact_dir(state_root) / f'{proposal_id}.json'
        if sink_state == 'pending':
            artifact = build_governed_rule_artifact(proposal=proposal, cycle_id=cycle_id, state_root=state_root)
            _write_json(artifact_path, artifact)
            sink_state = 'written'
            written_at = _now()
        else:
            written_at = existing.get('written_at')
            if artifact_path.exists():
                artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
            else:
                artifact = build_governed_rule_artifact(proposal=proposal, cycle_id=cycle_id, state_root=state_root)
                _write_json(artifact_path, artifact)
                if sink_state != 'exported':
                    sink_state = 'written'
                written_at = written_at or _now()
        entry = {
            'proposal_id': proposal_id,
            'candidate_key': proposal.get('candidate_key'),
            'candidate_kind': proposal.get('candidate_kind'),
            'sink_target': proposal.get('sink_target'),
            'sink_state': sink_state,
            'reviewer': proposal.get('reviewer'),
            'reviewed_at': proposal.get('reviewed_at'),
            'decision_note': proposal.get('decision_note'),
            'evidence_count': proposal.get('evidence_count', 0),
            'source_targets': proposal.get('source_targets', {}),
            'artifact_path': _artifact_relpath(artifact_path, state_root=state_root),
            'written_at': written_at,
            'exported_at': existing.get('exported_at'),
            'export_target': existing.get('export_target'),
            'last_cycle_id': cycle_id or proposal.get('last_seen_cycle_id'),
            'artifact_version': artifact.get('artifact_version'),
        }
        accepted_rule_registry[proposal_id] = entry
        governed_rule_candidates.append(entry)
        sink_state_counts[sink_state] = sink_state_counts.get(sink_state, 0) + 1
        sink = str(proposal.get('sink_target') or 'rulebook_candidate')
        sink_target_counts[sink] = sink_target_counts.get(sink, 0) + 1

    registry_payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'items': accepted_rule_registry,
        'state_counts': sink_state_counts,
        'sink_target_counts': sink_target_counts,
    }
    _write_json(_sink_registry_path(state_root), registry_payload)

    top_written_rules = [
        {
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'sink_state': item.get('sink_state'),
            'sink_target': item.get('sink_target'),
            'evidence_count': item.get('evidence_count'),
            'source_targets': item.get('source_targets'),
            'artifact_path': item.get('artifact_path'),
        }
        for item in sorted(governed_rule_candidates, key=lambda x: (-int(x.get('evidence_count', 0) or 0), str(x.get('candidate_key') or '')))[:5]
    ]
    governed_payload = {
        'generated_at': _now(),
        'cycle_id': cycle_id or rule_proposal_review.get('cycle_id'),
        'sink_ready_count': len(accepted_proposals),
        'written_count': sink_state_counts.get('written', 0),
        'exported_count': sink_state_counts.get('exported', 0),
        'rejected_count': sink_state_counts.get('rejected', 0),
        'state_counts': sink_state_counts,
        'sink_target_counts': sink_target_counts,
        'top_written_rules': top_written_rules,
        'items': governed_rule_candidates,
    }
    _write_json(_governed_candidates_path(state_root), governed_payload)
    return governed_payload


def update_rule_sink_status(*, proposal_id: str, action: str, export_target: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    registry_path = _sink_registry_path(state_root)
    registry = _load_json(registry_path)
    items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    entry = items.get(proposal_id) if isinstance(items.get(proposal_id), dict) else None
    if not entry:
        raise ValueError(f'unknown sink proposal: {proposal_id}')
    if action == 'write':
        entry['sink_state'] = 'written'
        entry['written_at'] = entry.get('written_at') or _now()
    elif action == 'export':
        entry['sink_state'] = 'exported'
        entry['exported_at'] = _now()
        if export_target:
            entry['export_target'] = export_target
    elif action == 'reject':
        entry['sink_state'] = 'rejected'
    else:
        raise ValueError(f'unsupported sink action: {action}')
    items[proposal_id] = entry
    registry['items'] = items
    registry['generated_at'] = _now()
    _write_json(registry_path, registry)
    _append_transition_event(
        state_root=state_root, proposal_id=proposal_id, candidate_key=entry.get('candidate_key') or '',
        from_state=None, to_state=entry.get('sink_state'), trigger=f'sink_{action}', actor='system',
        reason=entry.get('decision_note') or action, related_registry='accepted_rule_registry', cycle_id=str(registry.get('cycle_id') or ''),
        transition_type=f'sink_{action}', source_targets=entry.get('source_targets') or {}, extra={'sink_target': entry.get('sink_target'), 'sink_state': entry.get('sink_state')}
    )
    return entry



def _all_review_items(review: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ('knowledge_candidate_items', 'recent_closure_insights'):
        for item in list(review.get(key, []) or []):
            if isinstance(item, dict):
                items.append(item)
    backlog = (review.get('manual_classification_backlog') or {})
    for key in ('items', 'recently_completed_items', 'unresolved_items'):
        for item in list(backlog.get(key, []) or []):
            if isinstance(item, dict):
                items.append(item)
    dedup: dict[str, dict[str, Any]] = {}
    for item in items:
        task_id = item.get('task_id') or 'unknown'
        target = item.get('execution_target') or 'unknown'
        pattern = item.get('pattern_key') or 'n/a'
        dedup[f'{task_id}|{target}|{pattern}'] = item
    return list(dedup.values())



def _match_item(candidate_key: str, item: dict[str, Any]) -> bool:
    themes = set(item.get('extracted_themes') or [])
    if candidate_key.startswith('rule:'):
        theme = candidate_key.split('rule:', 1)[1]
        return theme in themes
    if candidate_key.startswith('pattern:'):
        theme = candidate_key
        return theme in themes
    return False



def build_rule_proposal_review(*, followup_resolution_review: dict[str, Any], latest_cycle: dict[str, Any] | None = None, state_root: Path = STATE_ROOT, cycle_id: str = '') -> dict[str, Any]:
    latest_cycle = latest_cycle or {}
    registry = _load_json(_registry_path(state_root))
    registry_entries = registry.get('proposals', {}) if isinstance(registry.get('proposals'), dict) else {}
    all_items = _all_review_items(followup_resolution_review)

    candidate_counts: dict[str, int] = {}
    candidate_counts.update({str(k): int(v or 0) for k, v in (followup_resolution_review.get('rule_candidate_counts') or {}).items()})
    candidate_counts.update({str(k): int(v or 0) for k, v in (followup_resolution_review.get('pattern_candidate_counts') or {}).items()})

    proposals: list[dict[str, Any]] = []
    for candidate_key, count in sorted(candidate_counts.items(), key=lambda kv: (-int(kv[1]), kv[0])):
        matched = [item for item in all_items if _match_item(candidate_key, item)]
        targets: dict[str, int] = {}
        source_patterns: dict[str, int] = {}
        source_themes: dict[str, int] = {}
        evidence: list[dict[str, Any]] = []
        for item in matched:
            target = str(item.get('execution_target') or 'unknown')
            targets[target] = targets.get(target, 0) + 1
            for theme in list(item.get('extracted_themes') or []):
                source_themes[theme] = source_themes.get(theme, 0) + 1
            pattern_key = str(item.get('pattern_key') or 'n/a')
            source_patterns[pattern_key] = source_patterns.get(pattern_key, 0) + 1
            evidence.append({
                'task_id': item.get('task_id'),
                'execution_target': item.get('execution_target'),
                'resolution_category': item.get('resolution_category'),
                'resolution_taxonomy': item.get('resolution_taxonomy'),
                'pattern_key': item.get('pattern_key'),
                'matched_tokens': [candidate_key.split('rule:', 1)[1]] if candidate_key.startswith('rule:') else [candidate_key],
                'resolution_summary': item.get('resolution_summary') or '',
                'source_artifact': ((item.get('knowledge_linkage') or {}).get('source_artifact')),
            })
        proposal_id = _proposal_id(candidate_key)
        registry_entry = registry_entries.get(proposal_id, {}) if isinstance(registry_entries.get(proposal_id), dict) else {}
        default_state = 'proposed' if count >= 2 else 'draft'
        proposal_state = str(registry_entry.get('proposal_state') or default_state).strip().lower()
        if proposal_state not in ALLOWED_STATES:
            proposal_state = default_state
        sink_target = _normalize_sink_target(candidate_key, str(registry_entry.get('sink_target') or ''))
        candidate_kind = 'pattern' if candidate_key.startswith('pattern:') else 'rule'
        semantic_tokens = _semantic_tokens(candidate_key)
        proposal = {
            'proposal_id': proposal_id,
            'candidate_key': candidate_key,
            'candidate_kind': candidate_kind,
            'candidate_count': count,
            'semantic_tokens': semantic_tokens,
            'semantic_group_key': _semantic_group_key(candidate_kind, candidate_key),
            'proposal_state': proposal_state,
            'default_state': default_state,
            'source_targets': targets,
            'source_themes': dict(sorted(source_themes.items(), key=lambda kv: (-int(kv[1]), kv[0]))[:8]),
            'source_patterns': dict(sorted(source_patterns.items(), key=lambda kv: (-int(kv[1]), kv[0]))[:6]),
            'evidence_count': len(evidence),
            'evidence': evidence[:8],
            'reviewer': registry_entry.get('reviewer'),
            'reviewed_at': registry_entry.get('reviewed_at'),
            'decision_note': registry_entry.get('decision_note') or '',
            'sink_target': sink_target,
            'sink_status': 'ready_for_sink' if proposal_state == 'accepted' else ('rejected' if proposal_state == 'rejected' else 'pending_review'),
            'governance_history': list(registry_entry.get('history', []) or []),
            'first_seen_cycle_id': registry_entry.get('first_seen_cycle_id') or cycle_id or latest_cycle.get('cycle_id'),
            'last_seen_cycle_id': cycle_id or latest_cycle.get('cycle_id'),
        }
        proposals.append(proposal)

    semantic_review = _build_semantic_candidate_review(proposals)
    conflict_registry = _build_rule_conflict_registry(proposals=proposals, semantic_review=semantic_review, cycle_id=cycle_id or latest_cycle.get('cycle_id'), state_root=state_root)

    state_counts: dict[str, int] = {}
    pending_review_count = 0
    accepted_sink_targets: dict[str, int] = {}
    for proposal in proposals:
        state = proposal.get('proposal_state') or 'draft'
        state_counts[state] = state_counts.get(state, 0) + 1
        if state in {'draft', 'proposed'}:
            pending_review_count += 1
        if state == 'accepted':
            sink = str(proposal.get('sink_target') or 'rulebook_candidate')
            accepted_sink_targets[sink] = accepted_sink_targets.get(sink, 0) + 1

    top_proposed_rules = [
        {
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'proposal_state': item.get('proposal_state'),
            'candidate_count': item.get('candidate_count'),
            'source_targets': item.get('source_targets'),
            'sink_target': item.get('sink_target'),
        }
        for item in proposals[:5]
    ]

    accepted_sink_items = [
        {
            'proposal_id': item.get('proposal_id'),
            'candidate_key': item.get('candidate_key'),
            'sink_target': item.get('sink_target'),
            'sink_status': item.get('sink_status'),
            'reviewer': item.get('reviewer'),
            'reviewed_at': item.get('reviewed_at'),
            'decision_note': item.get('decision_note'),
            'evidence_count': item.get('evidence_count'),
            'source_targets': item.get('source_targets'),
        }
        for item in proposals if item.get('proposal_state') == 'accepted'
    ]

    top_rule_digest = [
        f"{item.get('candidate_key')}|{item.get('proposal_state')}|count={item.get('candidate_count')}"
        for item in top_proposed_rules
    ]
    digest_lines = [
        '# Rule Proposal Governance Review',
        '',
        f"- proposal_count: {len(proposals)}",
        f"- pending_review_count: {pending_review_count}",
        f"- state_counts: {_render(state_counts)}",
        f"- accepted_sink_targets: {_render(accepted_sink_targets)}",
        f"- merge_candidate_count: {semantic_review.get('merge_candidate_count', 0)}",
        f"- conflict_candidate_count: {semantic_review.get('conflict_candidate_count', 0)}",
        f"- duplicate_candidate_count: {semantic_review.get('duplicate_candidate_count', 0)}",
        f"- top_proposed_rules: {_render(top_rule_digest)}",
        '',
    ]

    return {
        'generated_at': _now(),
        'cycle_id': cycle_id or latest_cycle.get('cycle_id'),
        'proposal_count': len(proposals),
        'pending_review_count': pending_review_count,
        'accepted_count': state_counts.get('accepted', 0),
        'rejected_count': state_counts.get('rejected', 0),
        'reviewed_count': state_counts.get('reviewed', 0),
        'proposed_count': state_counts.get('proposed', 0),
        'draft_count': state_counts.get('draft', 0),
        'proposal_state_counts': state_counts,
        'accepted_sink_targets': accepted_sink_targets,
        'merge_candidate_count': semantic_review.get('merge_candidate_count', 0),
        'conflict_candidate_count': semantic_review.get('conflict_candidate_count', 0),
        'duplicate_candidate_count': semantic_review.get('duplicate_candidate_count', 0),
        'top_merge_items': semantic_review.get('top_merge_items', []),
        'top_conflict_items': conflict_registry.get('top_conflict_items', []),
        'top_duplicate_items': semantic_review.get('top_duplicate_items', []),
        'rule_conflict_review': conflict_registry,
        'top_proposed_rules': top_proposed_rules,
        'proposals': proposals,
        'accepted_sink_items': accepted_sink_items,
        'digest_available': bool(proposals),
        'digest_markdown': '\n'.join(digest_lines),
    }



def write_rule_proposal_review_markdown(payload: dict[str, Any], path: Path) -> Path:
    lines = [
        '# Rule Proposal Review',
        '',
        f"- generated_at: {payload.get('generated_at')}",
        f"- cycle_id: {payload.get('cycle_id')}",
        f"- proposal_count: {payload.get('proposal_count')}",
        f"- pending_review_count: {payload.get('pending_review_count')}",
        f"- proposal_state_counts: {_render(payload.get('proposal_state_counts'))}",
        f"- accepted_sink_targets: {_render(payload.get('accepted_sink_targets'))}",
        f"- merge_candidate_count: {payload.get('merge_candidate_count')}",
        f"- conflict_candidate_count: {payload.get('conflict_candidate_count')}",
        f"- duplicate_candidate_count: {payload.get('duplicate_candidate_count')}",
        '',
        '## top_proposed_rules',
    ]
    top_items = list(payload.get('top_proposed_rules', []) or [])
    if not top_items:
        lines.append('- none')
    else:
        for item in top_items:
            lines.append(
                f"- {item.get('proposal_id')} | {item.get('candidate_key')} | state={item.get('proposal_state')} | count={item.get('candidate_count')} | targets={_render(item.get('source_targets'))} | sink={item.get('sink_target')}"
            )
    lines.extend(['', '## top_merge_items'])
    merge_items = list(payload.get('top_merge_items', []) or [])
    if not merge_items:
        lines.append('- none')
    else:
        for item in merge_items:
            lines.append(f"- {item.get('left_candidate_key')} <-> {item.get('right_candidate_key')} | semantic_group={item.get('semantic_group_key')} | similarity={item.get('similarity')} | reason={item.get('reason')}")
    lines.extend(['', '## top_conflict_items'])
    conflict_items = list(payload.get('top_conflict_items', []) or [])
    if not conflict_items:
        lines.append('- none')
    else:
        for item in conflict_items:
            lines.append(f"- {item.get('left_candidate_key')} <-> {item.get('right_candidate_key')} | semantic_group={item.get('semantic_group_key')} | similarity={item.get('similarity')} | reason={item.get('reason')}")
    lines.extend(['', '## top_duplicate_items'])
    duplicate_items = list(payload.get('top_duplicate_items', []) or [])
    if not duplicate_items:
        lines.append('- none')
    else:
        for item in duplicate_items:
            lines.append(f"- {item.get('left_candidate_key')} <-> {item.get('right_candidate_key')} | semantic_group={item.get('semantic_group_key')} | similarity={item.get('similarity')} | reason={item.get('reason')}")
    lines.extend(['', '## accepted_sink_items'])
    accepted = list(payload.get('accepted_sink_items', []) or [])
    if not accepted:
        lines.append('- none')
    else:
        for item in accepted:
            lines.append(
                f"- {item.get('proposal_id')} | {item.get('candidate_key')} | sink={item.get('sink_target')} | reviewer={item.get('reviewer') or 'n/a'} | reviewed_at={item.get('reviewed_at') or 'n/a'} | note={item.get('decision_note') or 'n/a'}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path



def apply_merge_queue_action(*, candidate_id: str, action: str, reviewer: str = 'human', note: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    action_map = {
        'review': 'reviewing',
        'accept': 'accepted',
        'reject': 'rejected',
        'supersede': 'superseded',
        'reopen': 'open',
    }
    if action not in action_map:
        raise ValueError(f'unsupported merge queue action: {action}')
    registry_path = _merge_queue_registry_path(state_root)
    registry = _load_json(registry_path)
    items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    entry = items.get(candidate_id) if isinstance(items.get(candidate_id), dict) else None
    if not entry:
        raise ValueError(f'unknown merge queue candidate_id: {candidate_id}')
    next_state = action_map[action]
    history = list(entry.get('governance_history', []) or [])
    history.append({
        'action': action,
        'previous_state': entry.get('review_state'),
        'next_state': next_state,
        'reviewer': reviewer,
        'reviewed_at': _now(),
        'decision_note': note,
    })
    entry.update({
        'review_state': next_state,
        'reviewer': reviewer,
        'reviewed_at': history[-1]['reviewed_at'],
        'decision_note': note,
        'governance_history': history,
    })
    items[candidate_id] = entry
    registry['items'] = items
    registry['generated_at'] = _now()
    _write_json(registry_path, registry)
    _append_transition_event(
        state_root=state_root, proposal_id=str(entry.get('source_rule') or candidate_id), candidate_key=entry.get('source_candidate_key') or '',
        from_state=history[-1].get('previous_state'), to_state=next_state, trigger=f'merge_queue_{action}', actor=reviewer, reason=note,
        related_registry='merge_queue_registry', cycle_id=str(registry.get('cycle_id') or ''), transition_type=f'merge_queue_{action}',
        target_proposal_id=entry.get('target_rule') or '', merge_candidate_id=candidate_id, source_targets=entry.get('source_targets') or {}, extra={'merge_role': 'source'}
    )
    return entry


def apply_rule_conflict_action(*, conflict_id: str, action: str, adjudicator: str = 'human', note: str = '', resolution_type: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    action_map = {
        'review': 'reviewing',
        'resolve': 'resolved',
        'reject': 'rejected',
        'supersede': 'superseded',
        'reopen': 'open',
    }
    if action not in action_map:
        raise ValueError(f'unsupported rule conflict action: {action}')
    registry_path = _conflict_registry_path(state_root)
    registry = _load_json(registry_path)
    items = registry.get('items', {}) if isinstance(registry.get('items'), dict) else {}
    entry = items.get(conflict_id) if isinstance(items.get(conflict_id), dict) else None
    if not entry:
        raise ValueError(f'unknown conflict_id: {conflict_id}')
    next_state = action_map[action]
    resolution = str(resolution_type or entry.get('resolution_type') or '').strip().lower() or None
    if resolution and resolution not in CONFLICT_ALLOWED_RESOLUTIONS:
        raise ValueError(f'unsupported resolution_type: {resolution_type}')
    history = list(entry.get('governance_history', []) or [])
    history.append({
        'action': action,
        'previous_state': entry.get('conflict_state'),
        'next_state': next_state,
        'adjudicator': adjudicator,
        'adjudicated_at': _now(),
        'adjudication_note': note,
        'resolution_type': resolution,
    })
    entry.update({
        'conflict_state': next_state,
        'adjudicator': adjudicator,
        'adjudicated_at': history[-1]['adjudicated_at'],
        'adjudication_note': note,
        'resolution_type': resolution,
        'governance_history': history,
    })
    items[conflict_id] = entry
    registry['items'] = items
    registry['generated_at'] = _now()
    _write_json(registry_path, registry)
    _append_transition_event(
        state_root=state_root, proposal_id=str(entry.get('source_proposal_id') or conflict_id), candidate_key=((entry.get('conflicting_proposals') or [{}])[0].get('candidate_key') if isinstance((entry.get('conflicting_proposals') or [{}])[0], dict) else ''),
        from_state=history[-1].get('previous_state'), to_state=next_state, trigger=f'conflict_{action}', actor=adjudicator, reason=note,
        related_registry='rule_conflict_registry', cycle_id=str(registry.get('cycle_id') or ''), transition_type=f'conflict_{action}',
        target_proposal_id=entry.get('target_proposal_id') or '', conflict_id=conflict_id, source_targets=((entry.get('latest_shared_source_targets') or {}).get('left') or {}), extra={'resolution_type': resolution}
    )
    return entry


def apply_rule_proposal_action(*, proposal_id: str, action: str, reviewer: str = 'human', note: str = '', sink_target: str = '', state_root: Path = STATE_ROOT) -> dict[str, Any]:
    if action not in ACTION_STATE:
        raise ValueError(f'unsupported rule proposal action: {action}')
    registry_path = _registry_path(state_root)
    registry = _load_json(registry_path)
    proposals = registry.setdefault('proposals', {})
    entry = proposals.get(proposal_id, {}) if isinstance(proposals.get(proposal_id), dict) else {}
    previous_state = str(entry.get('proposal_state') or 'draft').strip().lower() or 'draft'
    next_state = ACTION_STATE[action]
    entry.update({
        'proposal_id': proposal_id,
        'proposal_state': next_state,
        'reviewer': reviewer,
        'reviewed_at': _now(),
        'decision_note': note,
    })
    if sink_target:
        entry['sink_target'] = sink_target
    history = list(entry.get('history', []) or [])
    history.append({
        'action': action,
        'previous_state': previous_state,
        'next_state': next_state,
        'reviewer': reviewer,
        'reviewed_at': entry['reviewed_at'],
        'decision_note': note,
        'sink_target': entry.get('sink_target'),
    })
    entry['history'] = history
    proposals[proposal_id] = entry
    registry['updated_at'] = _now()
    _write_json(registry_path, registry)
    _append_transition_event(
        state_root=state_root, proposal_id=proposal_id, candidate_key=entry.get('candidate_key') or '', from_state=previous_state, to_state=next_state,
        trigger=f'proposal_{action}', actor=reviewer, reason=note, related_registry='rule_proposal_review_registry', cycle_id=str(registry.get('cycle_id') or ''),
        transition_type=f'proposal_{action}', extra={'sink_target': entry.get('sink_target')}
    )
    return entry



def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--proposal-id', required=True)
    p_apply.add_argument('--action', required=True, choices=sorted(ACTION_STATE.keys()))
    p_apply.add_argument('--reviewer', default='human')
    p_apply.add_argument('--note', default='')
    p_apply.add_argument('--sink-target', default='')
    p_apply.add_argument('--state-root', default=str(STATE_ROOT))

    p_sink = sub.add_parser('sink')
    p_sink.add_argument('--proposal-id', required=True)
    p_sink.add_argument('--action', required=True, choices=['write', 'export', 'reject'])
    p_sink.add_argument('--export-target', default='')
    p_sink.add_argument('--state-root', default=str(STATE_ROOT))

    p_merge = sub.add_parser('merge-queue')
    p_merge.add_argument('--candidate-id', required=True)
    p_merge.add_argument('--action', required=True, choices=['review', 'accept', 'reject', 'supersede', 'reopen'])
    p_merge.add_argument('--reviewer', default='human')
    p_merge.add_argument('--note', default='')
    p_merge.add_argument('--state-root', default=str(STATE_ROOT))

    p_conflict = sub.add_parser('conflict')
    p_conflict.add_argument('--conflict-id', required=True)
    p_conflict.add_argument('--action', required=True, choices=['review', 'resolve', 'reject', 'supersede', 'reopen'])
    p_conflict.add_argument('--adjudicator', default='human')
    p_conflict.add_argument('--note', default='')
    p_conflict.add_argument('--resolution-type', default='')
    p_conflict.add_argument('--state-root', default=str(STATE_ROOT))

    p_archive = sub.add_parser('archive-action')
    p_archive.add_argument('--proposal-id', required=True)
    p_archive.add_argument('--action', required=True, choices=['restore', 'reopen', 'revive'])
    p_archive.add_argument('--actor', default='human')
    p_archive.add_argument('--note', default='')
    p_archive.add_argument('--state-root', default=str(STATE_ROOT))

    args = parser.parse_args()
    if args.cmd == 'apply':
        result = apply_rule_proposal_action(
            proposal_id=args.proposal_id,
            action=args.action,
            reviewer=args.reviewer,
            note=args.note,
            sink_target=args.sink_target,
            state_root=Path(args.state_root),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'sink':
        result = update_rule_sink_status(
            proposal_id=args.proposal_id,
            action=args.action,
            export_target=args.export_target,
            state_root=Path(args.state_root),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'merge-queue':
        result = apply_merge_queue_action(
            candidate_id=args.candidate_id,
            action=args.action,
            reviewer=args.reviewer,
            note=args.note,
            state_root=Path(args.state_root),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'conflict':
        result = apply_rule_conflict_action(
            conflict_id=args.conflict_id,
            action=args.action,
            adjudicator=args.adjudicator,
            note=args.note,
            resolution_type=args.resolution_type,
            state_root=Path(args.state_root),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'archive-action':
        result = apply_archive_restore_action(
            proposal_id=args.proposal_id,
            action=args.action,
            actor=args.actor,
            note=args.note,
            state_root=Path(args.state_root),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
