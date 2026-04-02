#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from rule_proposal_runtime import apply_merge_queue_action, apply_rule_conflict_action, apply_rule_proposal_action, build_governed_rule_artifact, export_rulebook_artifacts
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
STATE_ROOT = ROOT / 'reports' / 'worker-runtime' / 'state'
JOBS_ROOT = ROOT / 'traces' / 'jobs'


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _find_proposal(payload: dict, *, state: str | None = None, target: str | None = None, candidate_key: str | None = None, exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    for item in list(payload.get('proposals', []) or []):
        if item.get('proposal_id') in exclude:
            continue
        if state and item.get('proposal_state') != state:
            continue
        if target and int((item.get('source_targets') or {}).get(target, 0) or 0) <= 0:
            continue
        if candidate_key and item.get('candidate_key') != candidate_key:
            continue
        return item
    raise AssertionError(f'proposal not found: state={state}, target={target}, candidate_key={candidate_key}')


def _synthetic_semantic_proposal(base: dict, *, proposal_id: str, candidate_key: str, note: str, semantic_group_key: str, merge_with: list[dict] | None = None, conflict_with: list[dict] | None = None, duplicate_with: list[dict] | None = None) -> dict:
    merge_with = merge_with or []
    conflict_with = conflict_with or []
    duplicate_with = duplicate_with or []
    return {
        **base,
        'proposal_id': proposal_id,
        'candidate_key': candidate_key,
        'proposal_state': 'accepted',
        'reviewer': 'validator-local-rulebook',
        'decision_note': note,
        'sink_target': 'rulebook_candidate',
        'semantic_group_key': semantic_group_key,
        'semantic_tokens': candidate_key.replace(':', ' ').replace('_', ' ').split(),
        'merge_candidates': merge_with,
        'conflict_candidates': conflict_with,
        'duplicate_candidates': duplicate_with,
        'merge_candidate_count': len(merge_with),
        'conflict_candidate_count': len(conflict_with),
        'duplicate_candidate_count': len(duplicate_with),
        'merge_reason': merge_with[0]['reason'] if merge_with else '',
        'conflict_reason': conflict_with[0]['reason'] if conflict_with else '',
        'duplicate_reason': duplicate_with[0]['reason'] if duplicate_with else '',
    }


def main() -> int:
    for name, payload in {
        'rule_proposal_review_registry.json': {'proposals': {}, 'reset_for_validation': True},
        'accepted_rule_registry.json': {'items': {}, 'reset_for_validation': True},
        'local_rulebook_registry.json': {'items': {}, 'reset_for_validation': True},
        'local_rulebook_export.json': {'items': [], 'reset_for_validation': True},
        'local_rulebook_export_audit.json': {'items': [], 'reset_for_validation': True},
        'local_rulebook_governance_review.json': {'items': [], 'reset_for_validation': True},
        'merge_queue_registry.json': {'items': {}, 'reset_for_validation': True},
        'latest_merge_target_review.json': {'items': {}, 'reset_for_validation': True},
        'rule_conflict_registry.json': {'items': {}, 'reset_for_validation': True},
        'rule_decision_linkage_review.json': {'items': [], 'reset_for_validation': True},
        'rule_consequence_review.json': {'items': [], 'reset_for_validation': True},
        'linkage_audit_registry.json': {'items': {}, 'reset_for_validation': True},
        'archive_audit_registry.json': {'items': {}, 'reset_for_validation': True},
        'rule_precedence_review.json': {'items': [], 'reset_for_validation': True},
    }.items():
        _write_json(STATE_ROOT / name, payload)
    for folder in ('governed-rule-artifacts', 'governed-rulebook'):
        target = STATE_ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        for child in target.glob('*.json'):
            child.unlink()

    bootstrap_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-local-rulebook-bootstrap', backfill_missing=True)
    bootstrap_review = _load_json(STATE_ROOT / 'latest_rule_proposal_review.json')
    _assert(bootstrap_review.get('proposal_count', 0) >= 5, 'bootstrap should produce multiple rule proposals')

    rollback_taxonomy = _find_proposal(bootstrap_review, state='proposed', candidate_key='rule:taxonomy:rollback_validation')
    rollback_theme = _find_proposal(bootstrap_review, state='proposed', candidate_key='rule:theme:rollback_validation')
    release_pattern = _find_proposal(bootstrap_review, state='accepted', candidate_key='pattern:handoff_involved') if any(item.get('candidate_key') == 'pattern:handoff_involved' and item.get('proposal_state') == 'accepted' for item in bootstrap_review.get('proposals', [])) else _find_proposal(bootstrap_review, state='proposed', candidate_key='pattern:handoff_involved')
    blocked_item = _find_proposal(bootstrap_review, state='proposed', candidate_key='rule:taxonomy:operations')

    for proposal, note in [
        (release_pattern, 'accept cross-target release/rollback shared pattern into local rulebook export'),
        (rollback_taxonomy, 'accept rollback taxonomy candidate as initial active revision'),
        (rollback_theme, 'accept rollback theme candidate as superseding revision'),
    ]:
        apply_rule_proposal_action(
            proposal_id=proposal['proposal_id'],
            action='accept',
            reviewer='validator-local-rulebook',
            note=note,
            sink_target='rulebook_candidate',
            state_root=STATE_ROOT,
        )

    final_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-local-rulebook-final', backfill_missing=True)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage = _load_json(STATE_ROOT / 'latest_stage_card.json')
    latest_rulebook_export = _load_json(STATE_ROOT / 'latest_local_rulebook_export.json')
    local_registry = _load_json(STATE_ROOT / 'local_rulebook_registry.json')
    governance_review = _load_json(STATE_ROOT / 'local_rulebook_governance_review.json')
    export_audit = _load_json(STATE_ROOT / 'local_rulebook_export_audit.json')
    accepted_registry = _load_json(STATE_ROOT / 'accepted_rule_registry.json')

    signals = latest_stage.get('signals') or {}
    local_items = local_registry.get('items') or {}
    pattern_rule = local_items.get(release_pattern['proposal_id']) or {}
    taxonomy_rule = local_items.get(rollback_taxonomy['proposal_id']) or {}
    theme_rule = local_items.get(rollback_theme['proposal_id']) or {}
    _assert(pattern_rule.get('version') == 'r1', 'newly exported shared rule should receive revision r1')
    _assert(theme_rule.get('revision') == 2, 'superseding rule should advance revision to 2')
    _assert(theme_rule.get('status') == 'active', 'superseding rule should become active')
    _assert(taxonomy_rule.get('status') == 'inactive_superseded', 'previous rollback rule should become inactive_superseded')
    _assert(theme_rule.get('supersedes') == [rollback_taxonomy['proposal_id']], 'superseding rule should reference prior active proposal')
    _assert(taxonomy_rule.get('superseded_by') == rollback_theme['proposal_id'], 'superseded rule should point to replacement')

    pattern_artifact = _load_json(STATE_ROOT / str(pattern_rule.get('rulebook_artifact_path')))
    theme_artifact = _load_json(STATE_ROOT / str(theme_rule.get('rulebook_artifact_path')))
    _assert(pattern_artifact.get('version') == 'r1', 'artifact should preserve version metadata')
    _assert(theme_artifact.get('version') == 'r2', 'artifact should preserve superseding revision metadata')

    duplicate_proposal_id = 'proposal-duplicate-content-check'
    governed_dup_path = STATE_ROOT / 'governed-rule-artifacts' / f'{duplicate_proposal_id}.json'
    duplicate_artifact = build_governed_rule_artifact(
        proposal={
            **release_pattern,
            'proposal_id': duplicate_proposal_id,
            'proposal_state': 'accepted',
            'reviewer': 'validator-local-rulebook',
            'reviewed_at': latest_cycle.get('generated_at'),
            'decision_note': 'synthetic duplicate content coverage',
            'sink_target': 'rulebook_candidate',
        },
        cycle_id=f"{latest_cycle.get('cycle_id')}-dup-content",
        state_root=STATE_ROOT,
    )
    _write_json(governed_dup_path, duplicate_artifact)
    accepted_items = accepted_registry.get('items') or {}
    accepted_items[duplicate_proposal_id] = {
        'proposal_id': duplicate_proposal_id,
        'candidate_key': release_pattern.get('candidate_key'),
        'candidate_kind': release_pattern.get('candidate_kind'),
        'sink_target': 'rulebook_candidate',
        'sink_state': 'written',
        'reviewer': 'validator-local-rulebook',
        'reviewed_at': latest_cycle.get('generated_at'),
        'decision_note': 'synthetic duplicate content coverage',
        'evidence_count': release_pattern.get('evidence_count', 0),
        'source_targets': release_pattern.get('source_targets', {}),
        'artifact_path': f'governed-rule-artifacts/{duplicate_proposal_id}.json',
        'written_at': latest_cycle.get('generated_at'),
        'exported_at': None,
        'export_target': None,
        'last_cycle_id': latest_cycle.get('cycle_id'),
        'artifact_version': duplicate_artifact.get('artifact_version'),
    }
    accepted_registry['items'] = accepted_items
    _write_json(STATE_ROOT / 'accepted_rule_registry.json', accepted_registry)

    duplicate_attempt = export_rulebook_artifacts(
        rule_proposal_review={
            'cycle_id': f"{latest_cycle.get('cycle_id')}-dup-content",
            'proposals': [{
                **release_pattern,
                'proposal_id': duplicate_proposal_id,
                'proposal_state': 'accepted',
                'reviewer': 'validator-local-rulebook',
                'reviewed_at': latest_cycle.get('generated_at'),
                'decision_note': 'synthetic duplicate content coverage',
                'sink_target': 'rulebook_candidate',
            }],
        },
        state_root=STATE_ROOT,
        cycle_id=f"{latest_cycle.get('cycle_id')}-dup-content",
        export_target='local-rulebook',
    )
    _assert(duplicate_attempt.get('duplicate_blocked_count', 0) >= 1, 'duplicate content should be blocked by stronger duplicate guard')

    blocked_export = export_rulebook_artifacts(
        rule_proposal_review={
            'cycle_id': f"{latest_cycle.get('cycle_id')}-blocked-check",
            'proposals': [{
                **blocked_item,
                'proposal_state': 'accepted',
                'reviewer': 'validator-local-rulebook',
                'decision_note': 'force sink-not-written guard coverage',
                'sink_target': 'rulebook_candidate',
            }],
        },
        state_root=STATE_ROOT,
        cycle_id=f"{latest_cycle.get('cycle_id')}-blocked-check",
        export_target='local-rulebook',
    )
    _assert(blocked_export.get('blocked_count', 0) >= 1, 'export should block accepted-but-not-written proposals')

    synthetic_cycle_id = f"{latest_cycle.get('cycle_id')}-semantic-governance"
    synthetic_specs = [
        ('proposal-merge-semantic-a', 'rule:theme:manual_review_prefer', 'rule:manual-review', 'merge_semantic_group_review'),
        ('proposal-merge-semantic-b', 'rule:taxonomy:manual_review_enable', 'rule:manual-review', 'merge_semantic_group_review'),
        ('proposal-conflict-semantic-a', 'rule:theme:manual_review_avoid', 'rule:manual-review', 'conflict_semantic_group_review'),
        ('proposal-conflict-semantic-b', 'rule:taxonomy:manual_review_require', 'rule:manual-review', 'conflict_semantic_group_review'),
        ('proposal-duplicate-semantic-a', 'rule:theme:config_alignment_review', 'rule:config-alignment-review', 'duplicate_like_semantic_review'),
        ('proposal-duplicate-semantic-b', 'rule:taxonomy:config_alignment_review', 'rule:config-alignment-review', 'duplicate_like_semantic_review'),
    ]
    synthetic_items = []
    accepted_items = accepted_registry.get('items') or {}
    for proposal_id, candidate_key, semantic_group_key, note in synthetic_specs:
        related = []
        for other_id, other_key, other_group, other_note in synthetic_specs:
            if other_id == proposal_id or other_group != semantic_group_key:
                continue
            related.append({'proposal_id': other_id, 'candidate_key': other_key, 'reason': note, 'similarity': 0.8})
        synthetic_proposal = _synthetic_semantic_proposal(
            release_pattern,
            proposal_id=proposal_id,
            candidate_key=candidate_key,
            note=note,
            semantic_group_key=semantic_group_key,
            merge_with=related if 'merge' in note else [],
            conflict_with=related if 'conflict' in note else [],
            duplicate_with=related if 'duplicate' in note else [],
        )
        synthetic_items.append(synthetic_proposal)
        artifact = build_governed_rule_artifact(proposal=synthetic_proposal, cycle_id=synthetic_cycle_id, state_root=STATE_ROOT)
        governed_path = STATE_ROOT / 'governed-rule-artifacts' / f'{proposal_id}.json'
        _write_json(governed_path, artifact)
        accepted_items[proposal_id] = {
            'proposal_id': proposal_id,
            'candidate_key': candidate_key,
            'candidate_kind': synthetic_proposal.get('candidate_kind'),
            'sink_target': 'rulebook_candidate',
            'sink_state': 'written',
            'reviewer': 'validator-local-rulebook',
            'reviewed_at': latest_cycle.get('generated_at'),
            'decision_note': note,
            'evidence_count': synthetic_proposal.get('evidence_count', 0),
            'source_targets': synthetic_proposal.get('source_targets', {}),
            'artifact_path': f'governed-rule-artifacts/{proposal_id}.json',
            'written_at': latest_cycle.get('generated_at'),
            'exported_at': None,
            'export_target': None,
            'last_cycle_id': synthetic_cycle_id,
            'artifact_version': artifact.get('artifact_version'),
        }
    accepted_registry['items'] = accepted_items
    _write_json(STATE_ROOT / 'accepted_rule_registry.json', accepted_registry)
    semantic_export = export_rulebook_artifacts(
        rule_proposal_review={'cycle_id': synthetic_cycle_id, 'proposals': synthetic_items},
        state_root=STATE_ROOT,
        cycle_id=synthetic_cycle_id,
        export_target='local-rulebook',
    )
    _assert(semantic_export.get('exported_count', 0) >= 5, 'semantic governance validation should export synthetic merge/conflict/duplicate-like items')

    refresh_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-local-rulebook-refresh', backfill_missing=True)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage = _load_json(STATE_ROOT / 'latest_stage_card.json')
    signals = latest_stage.get('signals') or {}
    local_registry = _load_json(STATE_ROOT / 'local_rulebook_registry.json')
    governance_review = _load_json(STATE_ROOT / 'local_rulebook_governance_review.json')
    latest_rulebook_export = _load_json(STATE_ROOT / 'latest_local_rulebook_export.json')

    _assert(latest_cycle.get('local_rulebook_active_rule_count', 0) >= 2, 'latest_cycle should expose active rule count')
    _assert(latest_cycle.get('local_rulebook_superseded_rule_count', 0) >= 1, 'latest_cycle should expose superseded rule count')
    _assert(latest_cycle.get('local_rulebook_merge_candidate_count', 0) >= 2, 'latest_cycle should expose merge candidate count')
    _assert(latest_cycle.get('local_rulebook_conflict_candidate_count', 0) >= 1, 'latest_cycle should expose conflict candidate count')
    _assert(latest_cycle.get('local_rulebook_duplicate_candidate_count', 0) >= 2, 'latest_cycle should expose duplicate-like candidate count')
    _assert(signals.get('local_rulebook_active_rule_count', 0) >= 2, 'stage card should expose active rule count')
    _assert(signals.get('local_rulebook_superseded_rule_count', 0) >= 1, 'stage card should expose superseded rule count')
    _assert(signals.get('local_rulebook_merge_candidate_count', 0) >= 2, 'stage card should expose merge candidate count')
    _assert(signals.get('local_rulebook_conflict_candidate_count', 0) >= 1, 'stage card should expose conflict candidate count')
    _assert(signals.get('local_rulebook_duplicate_candidate_count', 0) >= 2, 'stage card should expose duplicate-like candidate count')
    _assert(latest_cycle.get('merge_queue_count', 0) >= 1, 'latest_cycle should expose merge queue count')
    _assert(latest_cycle.get('merge_queue_open_count', 0) >= 1, 'latest_cycle should expose merge queue open count')
    _assert(bool(latest_cycle.get('top_merge_targets')), 'latest_cycle should expose top merge targets')
    _assert(bool(latest_cycle.get('top_supersede_suggestions')), 'latest_cycle should expose top supersede suggestions')
    _assert(signals.get('merge_queue_count', 0) >= 1, 'stage card should expose merge queue count')
    _assert(bool(signals.get('top_merge_targets')), 'stage card should expose top merge targets')
    _assert(bool(signals.get('top_supersede_suggestions')), 'stage card should expose top supersede suggestions')
    _assert(bool(signals.get('top_supersede_candidates')), 'stage card should expose top supersede candidates')
    _assert(bool(signals.get('top_merge_items')), 'stage card should expose top merge items')
    _assert(bool(signals.get('top_conflict_items')), 'stage card should expose top conflict items')
    _assert(bool(governance_review.get('top_merge_targets')), 'governance review should expose top merge targets')
    _assert(bool(governance_review.get('top_supersede_suggestions')), 'governance review should expose top supersede suggestions')
    _assert(bool(governance_review.get('top_merge_items')), 'governance review should expose top merge items')
    _assert(bool(governance_review.get('top_conflict_items')), 'governance review should expose top conflict items')
    _assert(bool(governance_review.get('top_duplicate_items')), 'governance review should expose top duplicate items')
    _assert((STATE_ROOT / 'latest_rule_conflict_review.json').exists(), 'conflict review artifact should be generated')

    merge_queue_review = _load_json(STATE_ROOT / 'merge_queue_registry.json')
    _assert(merge_queue_review.get('queue_count', 0) >= 1, 'merge/supersede candidate should enter merge queue registry')
    merge_candidate = next((item for item in (merge_queue_review.get('items') or {}).values() if item.get('relation_type') == 'merge'), None)
    _assert(bool(merge_candidate), 'merge queue should include merge candidate entries')
    _assert(bool(merge_candidate.get('suggested_target')), 'merge queue item should have suggested target')
    _assert(bool(merge_candidate.get('reason')), 'merge queue item should retain traceable reason')
    _assert(bool(merge_candidate.get('priority')), 'merge queue item should retain priority bucket')
    apply_merge_queue_action(
        candidate_id=merge_candidate['candidate_id'],
        action='review',
        reviewer='validator-merge-queue',
        note='enter reviewing state for merge queue lifecycle coverage',
        state_root=STATE_ROOT,
    )
    apply_merge_queue_action(
        candidate_id=merge_candidate['candidate_id'],
        action='accept',
        reviewer='validator-merge-queue',
        note='accept merge queue suggestion for lifecycle coverage',
        state_root=STATE_ROOT,
    )

    conflict_review = _load_json(STATE_ROOT / 'rule_conflict_registry.json')
    _assert(conflict_review.get('conflict_count', 0) >= 2, 'conflict candidate should enter conflict registry with multiple adjudication paths')
    conflict_items = list((conflict_review.get('items') or {}).values())
    conflict_item = conflict_items[0]
    conflict_id = conflict_item.get('conflict_id')
    rejected_conflict_item = conflict_items[1]
    rejected_conflict_id = rejected_conflict_item.get('conflict_id')
    apply_rule_conflict_action(
        conflict_id=conflict_id,
        action='review',
        adjudicator='validator-conflict-registry',
        note='enter reviewing state for lifecycle coverage',
        state_root=STATE_ROOT,
    )
    apply_rule_conflict_action(
        conflict_id=conflict_id,
        action='resolve',
        adjudicator='validator-conflict-registry',
        note='resolve semantic conflict by keeping both with explicit governance note',
        resolution_type='keep_both',
        state_root=STATE_ROOT,
    )
    apply_rule_conflict_action(
        conflict_id=rejected_conflict_id,
        action='review',
        adjudicator='validator-conflict-registry',
        note='enter reviewing state before reject coverage',
        state_root=STATE_ROOT,
    )
    apply_rule_conflict_action(
        conflict_id=rejected_conflict_id,
        action='reject',
        adjudicator='validator-conflict-registry',
        note='reject conflict escalation and keep prior rule consequence unchanged',
        resolution_type='reject_new',
        state_root=STATE_ROOT,
    )

    post_adjudication_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-local-rulebook-merge-conflict-adjudication', backfill_missing=True)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage = _load_json(STATE_ROOT / 'latest_stage_card.json')
    signals = latest_stage.get('signals') or {}
    merge_queue_review = _load_json(STATE_ROOT / 'merge_queue_registry.json')
    _assert(merge_queue_review.get('queue_count', 0) >= 1, 'merge/supersede candidate should enter merge queue registry')
    merge_candidate = next((item for item in (merge_queue_review.get('items') or {}).values() if item.get('relation_type') == 'merge'), None)
    _assert(bool(merge_candidate), 'merge queue should include merge candidate entries')
    _assert(bool(merge_candidate.get('suggested_target')), 'merge queue item should have suggested target')
    _assert(bool(merge_candidate.get('reason')), 'merge queue item should retain traceable reason')
    _assert(bool(merge_candidate.get('priority')), 'merge queue item should retain priority bucket')
    apply_merge_queue_action(
        candidate_id=merge_candidate['candidate_id'],
        action='review',
        reviewer='validator-merge-queue',
        note='enter reviewing state for merge queue lifecycle coverage',
        state_root=STATE_ROOT,
    )
    apply_merge_queue_action(
        candidate_id=merge_candidate['candidate_id'],
        action='accept',
        reviewer='validator-merge-queue',
        note='accept merge queue suggestion for lifecycle coverage',
        state_root=STATE_ROOT,
    )

    merge_queue_review = _load_json(STATE_ROOT / 'merge_queue_registry.json')
    conflict_review = _load_json(STATE_ROOT / 'rule_conflict_registry.json')
    governance_review = _load_json(STATE_ROOT / 'local_rulebook_governance_review.json')
    decision_linkage_review = _load_json(STATE_ROOT / 'rule_decision_linkage_review.json')
    consequence_review = _load_json(STATE_ROOT / 'rule_consequence_review.json')
    proposal_registry = _load_json(STATE_ROOT / 'rule_proposal_review_registry.json')
    accepted_registry = _load_json(STATE_ROOT / 'accepted_rule_registry.json')
    local_registry = _load_json(STATE_ROOT / 'local_rulebook_registry.json')
    _assert((merge_queue_review.get('items') or {}).get(merge_candidate['candidate_id'], {}).get('review_state') == 'accepted', 'merge queue item should move through minimal review lifecycle')
    _assert(latest_cycle.get('merge_queue_accepted_count', 0) >= 1, 'latest_cycle should expose merge queue accepted count')
    _assert(signals.get('merge_queue_accepted_count', 0) >= 1, 'stage card should expose merge queue accepted count')
    _assert((conflict_review.get('items') or {}).get(conflict_id, {}).get('conflict_state') == 'resolved', 'conflict item should move to resolved state')
    _assert((conflict_review.get('items') or {}).get(conflict_id, {}).get('resolution_type') == 'keep_both', 'conflict resolution should persist adjudication result')
    _assert((conflict_review.get('items') or {}).get(rejected_conflict_id, {}).get('conflict_state') == 'rejected', 'second conflict item should move to rejected state')
    _assert((conflict_review.get('items') or {}).get(rejected_conflict_id, {}).get('resolution_type') == 'reject_new', 'rejected conflict should persist reject_new resolution type')
    _assert(latest_cycle.get('local_rulebook_conflict_resolved_count', 0) >= 1, 'latest_cycle should expose resolved conflict count')
    _assert(signals.get('conflict_resolved_count', 0) >= 1, 'stage card should expose conflict resolved count')
    _assert(bool(signals.get('recent_adjudications')), 'stage card should expose recent adjudications')
    _assert(bool(governance_review.get('recent_adjudications')), 'governance review should expose recent adjudications')
    _assert(decision_linkage_review.get('post_decision_linkage_count', 0) >= 3, 'decision linkage review should capture merge/supersede/conflict closure')
    _assert(decision_linkage_review.get('merge_linked_count', 0) >= 1, 'decision linkage review should capture accepted merge linkage')
    _assert(decision_linkage_review.get('supersede_linked_count', 0) >= 1, 'decision linkage review should capture supersede linkage')
    _assert(decision_linkage_review.get('conflict_adjudicated_linked_count', 0) >= 1, 'decision linkage review should capture conflict adjudication linkage')
    _assert(latest_cycle.get('post_decision_linkage_count', 0) >= 3, 'latest_cycle should expose post-decision linkage count')
    _assert(latest_cycle.get('merge_linked_count', 0) >= 1, 'latest_cycle should expose merge-linked count')
    _assert(latest_cycle.get('supersede_linked_count', 0) >= 1, 'latest_cycle should expose supersede-linked count')
    _assert(latest_cycle.get('conflict_adjudicated_linked_count', 0) >= 1, 'latest_cycle should expose conflict-adjudicated-linked count')
    _assert(signals.get('post_decision_linkage_count', 0) >= 3, 'stage card should expose post-decision linkage count')
    _assert(signals.get('merge_linked_count', 0) >= 1, 'stage card should expose merge-linked count')
    _assert(signals.get('supersede_linked_count', 0) >= 1, 'stage card should expose supersede-linked count')
    _assert(signals.get('conflict_adjudicated_linked_count', 0) >= 1, 'stage card should expose conflict-adjudicated-linked count')
    _assert(bool(signals.get('recent_decision_linkages')), 'stage card should expose recent decision linkages')
    _assert(bool(governance_review.get('recent_decision_linkages')), 'governance review should expose recent decision linkages')
    linked_merge_item = next((item for item in (decision_linkage_review.get('items') or []) if item.get('linkage_type') == 'merge_accepted' and ((proposal_registry.get('proposals') or {}).get(item.get('source_proposal_id'), {}).get('status') == 'inactive_merged')), None)
    if not linked_merge_item:
        linked_merge_item = next((item for item in (decision_linkage_review.get('items') or []) if item.get('linkage_type') == 'merge_accepted'), None)
    _assert(bool(linked_merge_item), 'at least one accepted merge linkage should exist')
    _assert((proposal_registry.get('proposals') or {}).get(linked_merge_item['source_proposal_id'], {}).get('merged_into_proposal_id') == linked_merge_item['target_proposal_id'], 'proposal registry should reflect merge target linkage')
    _assert((accepted_registry.get('items') or {}).get(linked_merge_item['source_proposal_id'], {}).get('merged_into_proposal_id') == linked_merge_item['target_proposal_id'], 'governed rule registry should reflect merge target linkage')
    _assert((local_registry.get('items') or {}).get(rollback_taxonomy['proposal_id'], {}).get('superseded_by') == rollback_theme['proposal_id'], 'local rulebook registry should reflect supersede linkage')
    _assert((proposal_registry.get('proposals') or {}).get(rollback_taxonomy['proposal_id'], {}).get('superseded_by') == rollback_theme['proposal_id'], 'proposal registry should reflect superseded old rule')
    _assert((accepted_registry.get('items') or {}).get(rollback_theme['proposal_id'], {}).get('supersedes') == [rollback_taxonomy['proposal_id']], 'governed rule registry should reflect new-over-old supersede linkage')
    _assert(bool((proposal_registry.get('proposals') or {}).get(linked_merge_item['source_proposal_id'], {}).get('merged_into_proposal_id')), 'merge-accepted source proposal should retain merged-into linkage even if overridden later')
    _assert(bool((accepted_registry.get('items') or {}).get(linked_merge_item['source_proposal_id'], {}).get('merged_into_proposal_id')), 'merge-accepted source governed rule should retain merged-into linkage even if overridden later')
    _assert(bool((local_registry.get('items') or {}).get(linked_merge_item['source_proposal_id'], {}).get('merged_into_proposal_id')), 'merge-accepted source local rule should retain merged-into linkage even if overridden later')
    _assert(bool((local_registry.get('items') or {}).get(linked_merge_item['target_proposal_id'], {})), 'merge target local rule should remain traceable in registry')
    _assert((local_registry.get('items') or {}).get(rollback_taxonomy['proposal_id'], {}).get('status') == 'inactive_superseded', 'superseded old rule should become inactive_superseded')
    _assert((local_registry.get('items') or {}).get(rollback_theme['proposal_id'], {}).get('status') == 'active', 'new superseding rule should remain active')
    _assert(latest_cycle.get('local_rulebook_inactive_rule_count', 0) >= 1, 'latest_cycle should expose inactive rule count')
    _assert(latest_cycle.get('merge_linked_count', 0) >= 1, 'latest_cycle should expose merge-linked count even when precedence overrides final merged state')
    _assert(latest_cycle.get('conflict_resolution_type_counts', {}).get('keep_both', 0) >= 1, 'latest_cycle should expose keep_both conflict resolution count')
    _assert(bool(latest_cycle.get('recent_consequence_updates')), 'latest_cycle should expose recent consequence updates')
    _assert(signals.get('local_rulebook_inactive_rule_count', 0) >= 1, 'stage card should expose inactive rule count')
    _assert(signals.get('merge_linked_count', 0) >= 1, 'stage card should expose merge-linked count even when precedence overrides final merged state')
    _assert(signals.get('conflict_resolution_type_counts', {}).get('keep_both', 0) >= 1, 'stage card should expose keep_both conflict resolution count')
    _assert(bool(signals.get('recent_consequence_updates')), 'stage card should expose recent consequence updates')
    _assert(decision_linkage_review.get('merge_linked_count', 0) >= 1, 'decision linkage review should capture merge linkage even when final precedence suppresses inactive_merged state')
    _assert(consequence_review.get('local_rulebook_state_counts', {}).get('inactive_superseded', 0) >= 1, 'consequence review should capture inactive_superseded state count')
    _assert((conflict_review.get('items') or {}).get(conflict_id, {}).get('linkage_state') == 'linked', 'resolved conflict should be marked as linked')
    resolved_conflict_entry = (conflict_review.get('items') or {}).get(conflict_id, {})
    rejected_conflict_entry = (conflict_review.get('items') or {}).get(rejected_conflict_id, {})
    _assert((proposal_registry.get('proposals') or {}).get((resolved_conflict_entry.get('conflicting_rule_ids') or [None, None])[1], {}).get('latest_conflict_id') == conflict_id, 'proposal registry should receive resolved conflict adjudication backwrite')
    _assert((proposal_registry.get('proposals') or {}).get((rejected_conflict_entry.get('conflicting_rule_ids') or [None])[0], {}).get('latest_conflict_id') == rejected_conflict_id, 'proposal registry should receive rejected conflict adjudication backwrite')
    archive_audit = _load_json(STATE_ROOT / 'archive_audit_registry.json')
    precedence_review = _load_json(STATE_ROOT / 'rule_precedence_review.json')
    archived_item = next((item for item in (local_registry.get('items') or {}).values() if item.get('status') == 'archived'), None)
    _assert(bool(archived_item), 'archived workflow should produce at least one archived local rule item')
    _assert(archive_audit.get('archived_transition_count', 0) >= 1, 'archive audit should capture archived transition count')
    _assert(bool(archive_audit.get('recent_archived_items')), 'archive audit should expose recent archived items')
    _assert(latest_cycle.get('local_rulebook_archived_rule_count', 0) >= 1, 'latest_cycle should expose archived rule count')
    _assert(latest_cycle.get('archived_transition_count', 0) >= 1, 'latest_cycle should expose archived transition count')
    _assert(bool(latest_cycle.get('recent_archived_items')), 'latest_cycle should expose recent archived items')
    _assert(signals.get('local_rulebook_archived_rule_count', 0) >= 1, 'stage card should expose archived rule count')
    _assert(signals.get('archived_transition_count', 0) >= 1, 'stage card should expose archived transition count')
    _assert(bool(signals.get('recent_archived_items')), 'stage card should expose recent archived items')
    _assert(consequence_review.get('local_rulebook_state_counts', {}).get('archived', 0) >= 1, 'consequence review should capture archived state count')
    _assert(consequence_review.get('conflict_resolution_type_counts', {}).get('reject_new', 0) >= 1, 'consequence review should capture reject_new conflict consequence count')
    _assert(latest_cycle.get('conflict_resolution_type_counts', {}).get('reject_new', 0) >= 1, 'latest_cycle should expose reject_new conflict consequence count')
    _assert(signals.get('conflict_resolution_type_counts', {}).get('reject_new', 0) >= 1, 'stage card should expose reject_new conflict consequence count')
    _assert(precedence_review.get('decision_count', 0) >= 1, 'precedence review should capture overlapping governance decisions')
    _assert(bool(precedence_review.get('override_counts')), 'precedence review should expose override counts')
    _assert(latest_cycle.get('precedence_decision_count', 0) >= 1, 'latest_cycle should expose precedence decision count')
    _assert(bool(latest_cycle.get('precedence_override_counts')), 'latest_cycle should expose precedence override summary')
    _assert(bool(latest_cycle.get('recent_precedence_decisions')), 'latest_cycle should expose recent precedence decisions')
    _assert(signals.get('precedence_decision_count', 0) >= 1, 'stage card should expose precedence decision count')
    _assert(bool(signals.get('precedence_override_counts')), 'stage card should expose precedence override summary')
    _assert(bool(signals.get('recent_precedence_decisions')), 'stage card should expose recent precedence decisions')

    shared_targets = pattern_rule.get('source_targets') or {}
    _assert(shared_targets.get('official_release', 0) > 0 and shared_targets.get('rollback', 0) > 0, 'shared rulebook governance should retain both release and rollback evidence sources')

    result = {
        'bootstrap_cycle_id': bootstrap_cycle.get('cycle_id'),
        'final_cycle_id': final_cycle.get('cycle_id'),
        'refresh_cycle_id': refresh_cycle.get('cycle_id'),
        'latest_cycle_metrics': {
            'local_rulebook_exported_count': latest_cycle.get('local_rulebook_exported_count'),
            'local_rulebook_item_count': latest_cycle.get('local_rulebook_item_count'),
            'local_rulebook_active_rule_count': latest_cycle.get('local_rulebook_active_rule_count'),
            'local_rulebook_inactive_rule_count': latest_cycle.get('local_rulebook_inactive_rule_count'),
            'local_rulebook_archived_rule_count': latest_cycle.get('local_rulebook_archived_rule_count'),
            'local_rulebook_merged_rule_count': latest_cycle.get('local_rulebook_merged_rule_count'),
            'local_rulebook_superseded_rule_count': latest_cycle.get('local_rulebook_superseded_rule_count'),
            'local_rulebook_consequence_state_counts': latest_cycle.get('local_rulebook_consequence_state_counts'),
            'local_rulebook_duplicate_blocked_count': latest_cycle.get('local_rulebook_duplicate_blocked_count'),
            'local_rulebook_merge_candidate_count': latest_cycle.get('local_rulebook_merge_candidate_count'),
            'local_rulebook_conflict_candidate_count': latest_cycle.get('local_rulebook_conflict_candidate_count'),
            'local_rulebook_conflict_state_counts': latest_cycle.get('local_rulebook_conflict_state_counts'),
            'local_rulebook_conflict_open_count': latest_cycle.get('local_rulebook_conflict_open_count'),
            'local_rulebook_conflict_reviewing_count': latest_cycle.get('local_rulebook_conflict_reviewing_count'),
            'local_rulebook_conflict_resolved_count': latest_cycle.get('local_rulebook_conflict_resolved_count'),
            'local_rulebook_duplicate_candidate_count': latest_cycle.get('local_rulebook_duplicate_candidate_count'),
            'merge_queue_count': latest_cycle.get('merge_queue_count'),
            'merge_queue_state_counts': latest_cycle.get('merge_queue_state_counts'),
            'merge_queue_open_count': latest_cycle.get('merge_queue_open_count'),
            'merge_queue_reviewing_count': latest_cycle.get('merge_queue_reviewing_count'),
            'merge_queue_accepted_count': latest_cycle.get('merge_queue_accepted_count'),
            'merge_queue_rejected_count': latest_cycle.get('merge_queue_rejected_count'),
            'top_merge_targets': latest_cycle.get('top_merge_targets'),
            'top_supersede_suggestions': latest_cycle.get('top_supersede_suggestions'),
            'top_supersede_candidates': latest_cycle.get('top_supersede_candidates'),
            'top_merge_items': latest_cycle.get('top_merge_items'),
            'top_conflict_items': latest_cycle.get('top_conflict_items'),
            'recent_adjudications': latest_cycle.get('recent_adjudications'),
            'conflict_resolution_type_counts': latest_cycle.get('conflict_resolution_type_counts'),
            'recent_consequence_updates': latest_cycle.get('recent_consequence_updates'),
            'archived_transition_count': latest_cycle.get('archived_transition_count'),
            'recent_archived_items': latest_cycle.get('recent_archived_items'),
            'precedence_decision_count': latest_cycle.get('precedence_decision_count'),
            'precedence_override_counts': latest_cycle.get('precedence_override_counts'),
            'recent_precedence_decisions': latest_cycle.get('recent_precedence_decisions'),
            'top_duplicate_items': latest_cycle.get('top_duplicate_items'),
            'post_decision_linkage_count': latest_cycle.get('post_decision_linkage_count'),
            'merge_linked_count': latest_cycle.get('merge_linked_count'),
            'supersede_linked_count': latest_cycle.get('supersede_linked_count'),
            'conflict_adjudicated_linked_count': latest_cycle.get('conflict_adjudicated_linked_count'),
            'recent_decision_linkages': latest_cycle.get('recent_decision_linkages'),
        },
        'stage_card_metrics': {
            'local_rulebook_active_rule_count': signals.get('local_rulebook_active_rule_count'),
            'local_rulebook_inactive_rule_count': signals.get('local_rulebook_inactive_rule_count'),
            'local_rulebook_archived_rule_count': signals.get('local_rulebook_archived_rule_count'),
            'local_rulebook_merged_rule_count': signals.get('local_rulebook_merged_rule_count'),
            'local_rulebook_superseded_rule_count': signals.get('local_rulebook_superseded_rule_count'),
            'local_rulebook_consequence_state_counts': signals.get('local_rulebook_consequence_state_counts'),
            'local_rulebook_duplicate_blocked_count': signals.get('local_rulebook_duplicate_blocked_count'),
            'local_rulebook_merge_candidate_count': signals.get('local_rulebook_merge_candidate_count'),
            'local_rulebook_conflict_candidate_count': signals.get('local_rulebook_conflict_candidate_count'),
            'conflict_state_counts': signals.get('conflict_state_counts'),
            'conflict_open_count': signals.get('conflict_open_count'),
            'conflict_reviewing_count': signals.get('conflict_reviewing_count'),
            'conflict_resolved_count': signals.get('conflict_resolved_count'),
            'local_rulebook_duplicate_candidate_count': signals.get('local_rulebook_duplicate_candidate_count'),
            'merge_queue_count': signals.get('merge_queue_count'),
            'merge_queue_state_counts': signals.get('merge_queue_state_counts'),
            'merge_queue_open_count': signals.get('merge_queue_open_count'),
            'merge_queue_reviewing_count': signals.get('merge_queue_reviewing_count'),
            'merge_queue_accepted_count': signals.get('merge_queue_accepted_count'),
            'merge_queue_rejected_count': signals.get('merge_queue_rejected_count'),
            'top_merge_targets': signals.get('top_merge_targets'),
            'top_supersede_suggestions': signals.get('top_supersede_suggestions'),
            'top_supersede_candidates': signals.get('top_supersede_candidates'),
            'top_merge_items': signals.get('top_merge_items'),
            'top_conflict_items': signals.get('top_conflict_items'),
            'recent_adjudications': signals.get('recent_adjudications'),
            'conflict_resolution_type_counts': signals.get('conflict_resolution_type_counts'),
            'recent_consequence_updates': signals.get('recent_consequence_updates'),
            'archived_transition_count': signals.get('archived_transition_count'),
            'recent_archived_items': signals.get('recent_archived_items'),
            'precedence_decision_count': signals.get('precedence_decision_count'),
            'precedence_override_counts': signals.get('precedence_override_counts'),
            'recent_precedence_decisions': signals.get('recent_precedence_decisions'),
            'top_duplicate_items': signals.get('top_duplicate_items'),
            'post_decision_linkage_count': signals.get('post_decision_linkage_count'),
            'merge_linked_count': signals.get('merge_linked_count'),
            'supersede_linked_count': signals.get('supersede_linked_count'),
            'conflict_adjudicated_linked_count': signals.get('conflict_adjudicated_linked_count'),
            'recent_decision_linkages': signals.get('recent_decision_linkages'),
        },
        'latest_local_rulebook_export': latest_rulebook_export,
        'local_rulebook_registry': local_registry,
        'local_rulebook_governance_review': governance_review,
        'duplicate_attempt': duplicate_attempt,
        'blocked_attempt': blocked_export,
        'semantic_export': semantic_export,
        'merge_queue_review': _load_json(STATE_ROOT / 'latest_merge_target_review.json'),
        'rule_conflict_review': _load_json(STATE_ROOT / 'latest_rule_conflict_review.json'),
        'resolved_conflict_id': conflict_id,
        'rejected_conflict_id': rejected_conflict_id,
        'rule_decision_linkage_review': decision_linkage_review,
        'rule_consequence_review': consequence_review,
        'archive_audit': archive_audit,
        'rule_precedence_review': precedence_review,
        'proposal_registry': proposal_registry,
        'accepted_rule_registry': accepted_registry,
        'release_pattern_rule': pattern_rule,
        'rollback_taxonomy_rule': taxonomy_rule,
        'rollback_theme_rule': theme_rule,
        'pattern_artifact': pattern_artifact,
        'theme_artifact': theme_artifact,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
