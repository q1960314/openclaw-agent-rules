#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from rule_proposal_runtime import apply_archive_restore_action, apply_rule_conflict_action, apply_rule_proposal_action, update_rule_sink_status
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
STATE_ROOT = ROOT / 'reports' / 'worker-runtime' / 'state'
JOBS_ROOT = ROOT / 'traces' / 'jobs'

RESET_FILES = [
    'rule_proposal_review_registry.json',
    'accepted_rule_registry.json',
    'governed_rule_candidates.json',
    'local_rulebook_registry.json',
    'local_rulebook_export.json',
    'local_rulebook_export.md',
    'local_rulebook_export_audit.json',
    'rule_conflict_registry.json',
    'merge_queue_registry.json',
    'rule_consequence_review.json',
    'rule_consequence_review.md',
    'rule_consequence_history.json',
    'rule_consequence_history.md',
    'rule_transition_ledger.jsonl',
    'rule_transition_digest.json',
    'rule_transition_digest.md',
    'archive_audit_registry.json',
    'archive_policy_review.json',
    'archive_policy_review.md',
    'archive_restore_registry.json',
    'archive_restore_review.json',
    'archive_restore_review.md',
    'archive_restore_timeline.json',
    'archive_restore_timeline.md',
    'rule_precedence_review.json',
    'rule_precedence_review.md',
    'latest_rule_proposal_review.json',
    'latest_rule_proposal_review.md',
    'latest_governed_rule_candidates.json',
    'latest_governed_rule_candidates.md',
    'latest_cycle.json',
    'latest_stage_card.json',
    'latest_stage_card.md',
]
RESET_DIRS = ['governed-rule-artifacts', 'governed-rulebook']


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _reset() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    for name in RESET_FILES:
        path = STATE_ROOT / name
        if path.exists():
            path.unlink()
    for name in RESET_DIRS:
        path = STATE_ROOT / name
        if path.exists():
            for child in sorted(path.rglob('*'), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            path.rmdir()
    (STATE_ROOT / 'rule_proposal_review_registry.json').write_text(json.dumps({'proposals': {}, 'reset_for_validation': True}, ensure_ascii=False, indent=2), encoding='utf-8')


def _set_archived_snapshot(proposal_id: str, snapshot: dict) -> None:
    local_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    local_registry.setdefault('items', {})[proposal_id] = deepcopy(snapshot)
    _write(STATE_ROOT / 'local_rulebook_registry.json', local_registry)
    for rel in ['governed-rulebook', 'governed-rule-artifacts']:
        path = STATE_ROOT / rel / f'{proposal_id}.json'
        if path.exists():
            payload = _load(path)
            payload.update({
                'status': snapshot.get('status'),
                'archive_metadata': snapshot.get('archive_metadata'),
                'archive_reason': snapshot.get('archive_reason'),
                'archived_at': snapshot.get('archived_at'),
                'archived_from_state': snapshot.get('archived_from_state'),
                'archive_reopen_pending': snapshot.get('archive_reopen_pending'),
                'restore_audit': snapshot.get('restore_audit'),
                'reopen_history': snapshot.get('reopen_history'),
                'consequence': snapshot.get('consequence'),
                'source_targets': snapshot.get('source_targets'),
            })
            _write(path, payload)




def _clone_local_rulebook_item(base_snapshot: dict, proposal_id: str, *, candidate_key: str, status: str, cycle_id: str, note: str, resolution_type: str | None = None, target_proposal_id: str | None = None) -> dict:
    clone = deepcopy(base_snapshot)
    clone['proposal_id'] = proposal_id
    clone['candidate_key'] = candidate_key
    clone['status'] = status
    clone['reviewer'] = 'validator-archive-restore'
    clone['decision_note'] = note
    clone['export_status'] = 'already_exported'
    clone['rulebook_artifact_path'] = f'governed-rulebook/{proposal_id}.json'
    consequence = dict(clone.get('consequence') or {})
    consequence.update({
        'state': status,
        'decision_type': {
            'duplicate_blocked': 'duplicate_blocked',
            'inactive_conflict_rejected': 'conflict_rejected',
            'inactive_superseded': 'superseded_by_new_rule',
        }.get(status, consequence.get('decision_type') or status),
        'source_proposal_id': proposal_id,
        'target_proposal_id': target_proposal_id,
        'target_rulebook_state': 'active' if target_proposal_id else consequence.get('target_rulebook_state'),
        'resolution_type': resolution_type,
        'note': note,
        'updated_at': cycle_id,
        'cycle_id': cycle_id,
    })
    clone['consequence'] = consequence
    for rel in ['governed-rulebook', 'governed-rule-artifacts']:
        path = STATE_ROOT / rel / f'{proposal_id}.json'
        payload = deepcopy(clone)
        payload['artifact_path'] = str(path.relative_to(STATE_ROOT))
        _write(path, payload)
    local_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    local_registry.setdefault('items', {})[proposal_id] = deepcopy(clone)
    _write(STATE_ROOT / 'local_rulebook_registry.json', local_registry)
    return clone

def _archive_shared_item(shared_id: str, cycle_id: str) -> dict:
    local_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    entry = deepcopy((local_registry.get('items') or {}).get(shared_id))
    _assert(isinstance(entry, dict), 'shared release/rollback item must exist before archive test')
    entry['status'] = 'duplicate_blocked'
    entry['duplicate_reason'] = 'validator shared release+rollback archive sample'
    entry['archive_reopen_pending'] = False
    entry['consequence'] = {
        'state': 'duplicate_blocked',
        'decision_type': 'duplicate_blocked',
        'source_proposal_id': shared_id,
        'target_proposal_id': None,
        'target_rulebook_state': None,
        'merge_candidate_id': None,
        'conflict_id': None,
        'resolution_type': None,
        'note': 'validator shared release+rollback archive sample',
        'updated_at': bootstrap.get('generated_at') if False else None,
        'cycle_id': cycle_id,
    }
    entry['consequence']['updated_at'] = entry.get('exported_at') or cycle_id
    _set_archived_snapshot(shared_id, entry)
    archive_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-shared-archive', backfill_missing=True)
    archived_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    archived_entry = deepcopy((archived_registry.get('items') or {}).get(shared_id))
    _assert(archived_entry.get('status') == 'archived', 'shared release/rollback item should archive through shared governance path')
    _assert(((archived_entry.get('archive_metadata') or {}).get('evidence_scope')) == 'shared_release_rollback', 'shared archived item should keep shared evidence scope')
    _assert(((archived_entry.get('archive_metadata') or {}).get('shared_governance_rule')) is True, 'shared archived item should stay on common governance rule path')
    return archived_entry


def main() -> int:
    _reset()
    bootstrap = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-bootstrap', backfill_missing=True)
    review = _load(STATE_ROOT / 'latest_rule_proposal_review.json')

    _assert(review.get('proposal_count', 0) >= 3, 'bootstrap should produce proposals')
    proposals = list(review.get('proposals') or [])
    _assert(any(int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 for item in proposals), 'release evidence must enter shared governance')
    _assert(any(int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 for item in proposals), 'rollback evidence must enter shared governance')

    rollback_pair = [item for item in proposals if int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 and item.get('proposal_id') != 'proposal-f091d0fca0'][:2]
    _assert(len(rollback_pair) >= 2, 'need two rollback proposals for conflict validation')
    shared_item = next((item for item in proposals if int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 and int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0), None)
    _assert(shared_item is not None, 'need shared release/rollback evidence proposal')

    for item in rollback_pair + [shared_item]:
        apply_rule_proposal_action(
            proposal_id=item['proposal_id'],
            action='accept',
            reviewer='validator-archive-restore',
            note='accept proposal for archive/restore validation',
            sink_target='rulebook_candidate',
            state_root=STATE_ROOT,
        )

    run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-export', backfill_missing=True)
    accepted_registry = _load(STATE_ROOT / 'accepted_rule_registry.json')
    for item in rollback_pair + [shared_item]:
        sink_entry = (accepted_registry.get('items') or {}).get(item['proposal_id']) or {}
        _assert(bool(sink_entry), f'missing sink entry for {item["proposal_id"]}')
        if sink_entry.get('sink_state') != 'exported':
            update_rule_sink_status(proposal_id=item['proposal_id'], action='export', export_target='local-rulebook', state_root=STATE_ROOT)
    run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-export-final', backfill_missing=True)

    source_id = rollback_pair[0]['proposal_id']
    target_id = rollback_pair[1]['proposal_id']
    conflict_id = f'conflict-{source_id[:8]}-{target_id[:8]}'
    source_item = next(item for item in proposals if item['proposal_id'] == source_id)
    target_item = next(item for item in proposals if item['proposal_id'] == target_id)
    conflict_registry = _load(STATE_ROOT / 'rule_conflict_registry.json') if (STATE_ROOT / 'rule_conflict_registry.json').exists() else {'items': {}}
    items = conflict_registry.get('items') or {}
    items[conflict_id] = {
        'conflict_id': conflict_id,
        'semantic_group_key': 'rule:validation',
        'conflict_state': 'open',
        'resolution_type': None,
        'adjudication_note': None,
        'adjudicator': None,
        'adjudicated_at': None,
        'reason': 'validator real sample: reject_old between rollback validation rules',
        'similarity': 1.0,
        'source_proposal_id': source_id,
        'target_proposal_id': target_id,
        'conflicting_rule_ids': [source_id, target_id],
        'conflicting_proposals': [
            {'proposal_id': source_id, 'candidate_key': source_item.get('candidate_key')},
            {'proposal_id': target_id, 'candidate_key': target_item.get('candidate_key')},
        ],
        'latest_shared_source_targets': {
            'left': source_item.get('source_targets', {}),
            'right': target_item.get('source_targets', {}),
        },
        'governance_history': [],
    }
    conflict_registry.update({'generated_at': bootstrap.get('generated_at'), 'items': items})
    _write(STATE_ROOT / 'rule_conflict_registry.json', conflict_registry)

    apply_rule_conflict_action(
        conflict_id=conflict_id,
        action='resolve',
        adjudicator='validator-archive-restore',
        note='validate reject_old with real exported rollback sample',
        resolution_type='reject_old',
        state_root=STATE_ROOT,
    )
    reject_old_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-reject-old', backfill_missing=True)

    local_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    loser = deepcopy((local_registry.get('items') or {}).get(target_id))
    winner = deepcopy((local_registry.get('items') or {}).get(source_id))
    archive_policy = _load(STATE_ROOT / 'archive_policy_review.json')
    _assert(isinstance(loser, dict), 'reject_old loser entry should exist in local rulebook')
    _assert(isinstance(winner, dict), 'reject_old winner entry should exist in local rulebook')
    _assert(loser.get('status') == 'archived', 'reject_old loser should be archived after cycle')
    _assert(((loser.get('archive_metadata') or {}).get('archived_policy')) == 'conflict_reject_old_archive', 'archived loser should carry explicit reject_old policy')
    _assert(((archive_policy.get('archive_policy_counts') or {}).get('conflict_reject_old_archive', 0)) >= 1, 'archive policy review should aggregate reject_old policy')

    archived_loser_snapshot = deepcopy(loser)
    shared_archived_snapshot = _archive_shared_item(shared_item['proposal_id'], reject_old_cycle.get('cycle_id'))
    shared_variant_base = deepcopy(shared_archived_snapshot)
    shared_duplicate_snapshot = _clone_local_rulebook_item(shared_variant_base, 'proposal-shared-dup-001', candidate_key='pattern:handoff_involved:shared-duplicate', status='duplicate_blocked', cycle_id=reject_old_cycle.get('cycle_id'), note='extra shared release+rollback duplicate archived sample')
    shared_conflict_snapshot = _clone_local_rulebook_item(shared_variant_base, 'proposal-shared-conflict-001', candidate_key='pattern:handoff_involved:shared-conflict', status='inactive_conflict_rejected', cycle_id=reject_old_cycle.get('cycle_id'), note='extra shared release+rollback conflict archived sample', resolution_type='reject_new', target_proposal_id=shared_item['proposal_id'])
    shared_supersede_snapshot = _clone_local_rulebook_item(shared_variant_base, 'proposal-shared-supersede-001', candidate_key='pattern:handoff_involved:shared-supersede', status='inactive_superseded', cycle_id=reject_old_cycle.get('cycle_id'), note='extra shared release+rollback supersede archived sample', target_proposal_id=shared_item['proposal_id'])
    thickened_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-shared-thickening', backfill_missing=True)
    thickened_registry = _load(STATE_ROOT / 'local_rulebook_registry.json')
    for thickened_id in ['proposal-shared-dup-001', 'proposal-shared-conflict-001', 'proposal-shared-supersede-001']:
        thickened_entry = deepcopy((thickened_registry.get('items') or {}).get(thickened_id))
        _assert(thickened_entry.get('status') == 'archived', f'{thickened_id} should archive as thickened shared sample')
        _assert(((thickened_entry.get('archive_metadata') or {}).get('shared_governance_rule')) is True, f'{thickened_id} should preserve shared governance rule')

    restore_entry = apply_archive_restore_action(
        proposal_id=target_id,
        action='restore',
        actor='validator-archive-restore',
        note='restore archived reject_old sample to prior consequence state',
        state_root=STATE_ROOT,
    )
    restore_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-restore', backfill_missing=True)
    _assert(restore_entry.get('status') == 'inactive_conflict_rejected', 'restore should route archived item back to prior consequence state')
    _assert((restore_entry.get('consequence') or {}).get('state') == 'inactive_conflict_rejected', 'restore consequence should preserve prior inactive conflict rejected state')

    _set_archived_snapshot(target_id, archived_loser_snapshot)
    reopen_entry = apply_archive_restore_action(
        proposal_id=target_id,
        action='reopen',
        actor='validator-archive-restore',
        note='reopen archived reject_old sample back into governance review',
        state_root=STATE_ROOT,
    )
    reopen_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-reopen', backfill_missing=True)
    _assert(reopen_entry.get('status') == 'reviewing', 'reopen should route archived item into governance reviewing state')
    _assert((reopen_entry.get('consequence') or {}).get('state') == 'reviewing', 'reopen consequence should become reviewing')
    _assert(reopen_entry.get('archive_reopen_pending') is True, 'reopen should mark governance review pending')

    _set_archived_snapshot(shared_item['proposal_id'], shared_archived_snapshot)
    revive_entry = apply_archive_restore_action(
        proposal_id=shared_item['proposal_id'],
        action='revive',
        actor='validator-archive-restore',
        note='revive shared release+rollback archived sample back to active effect',
        state_root=STATE_ROOT,
    )
    revive_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-archive-restore-revive', backfill_missing=True)
    _assert(revive_entry.get('status') == 'active', 'revive should route archived item back to active state')
    _assert((revive_entry.get('consequence') or {}).get('state') == 'active', 'revive consequence should become active')
    _assert(((revive_entry.get('archive_metadata') or {}).get('shared_governance_rule')) is True, 'shared release/rollback revive should keep shared governance flag')

    latest_cycle = _load(STATE_ROOT / 'latest_cycle.json')
    stage = _load(STATE_ROOT / 'latest_stage_card.json')
    signals = stage.get('signals') or {}
    restore_registry = _load(STATE_ROOT / 'archive_restore_registry.json')
    archive_restore_review = _load(STATE_ROOT / 'archive_restore_review.json')
    consequence_review = _load(STATE_ROOT / 'rule_consequence_review.json')
    archive_policy = _load(STATE_ROOT / 'archive_policy_review.json')

    _assert((restore_registry.get('restored_count', 0)) >= 1, 'restore registry should count restore actions')
    _assert((restore_registry.get('reopened_count', 0)) >= 1, 'restore registry should count reopen actions')
    _assert((restore_registry.get('revived_count', 0)) >= 1, 'restore registry should count revive actions')
    state_counts = restore_registry.get('restore_state_counts') or {}
    _assert(state_counts.get('inactive_conflict_rejected', 0) >= 1, 'restore_state_counts should include restore route back to prior consequence state')
    _assert(state_counts.get('reviewing', 0) >= 1, 'restore_state_counts should include reopen reviewing route')
    _assert(state_counts.get('active', 0) >= 1, 'restore_state_counts should include revive active route')

    _assert(latest_cycle.get('restore_state_counts', {}).get('reviewing', 0) >= 1, 'latest_cycle should expose restore_state_counts.reviewing')
    _assert(latest_cycle.get('reopen_count', 0) >= 1, 'latest_cycle should expose reopen_count')
    _assert(latest_cycle.get('revive_count', 0) >= 1, 'latest_cycle should expose revive_count')
    _assert(latest_cycle.get('consequence_history_available') is True, 'latest_cycle should expose consequence_history_available')
    _assert(latest_cycle.get('consequence_history_event_count', 0) >= 6, 'latest_cycle should expose consequence_history_event_count')
    _assert(bool(latest_cycle.get('recent_consequence_transitions')), 'latest_cycle should expose recent_consequence_transitions')
    _assert(latest_cycle.get('transition_ledger_available') is True, 'latest_cycle should expose transition_ledger_available')
    _assert(latest_cycle.get('transition_event_count', 0) >= 6, 'latest_cycle should expose transition_event_count')
    _assert(bool(latest_cycle.get('recent_transition_events')), 'latest_cycle should expose recent_transition_events')
    _assert(bool(latest_cycle.get('top_transition_triggers')), 'latest_cycle should expose top_transition_triggers')
    _assert(latest_cycle.get('shared_source_archived_count', 0) >= 4, 'latest_cycle should expose thickened shared_source_archived_count')
    _assert(bool(latest_cycle.get('recent_restore_actions')), 'latest_cycle should expose recent_restore_actions')

    _assert(signals.get('restore_state_counts', {}).get('reviewing', 0) >= 1, 'stage card should expose restore_state_counts.reviewing')
    _assert(signals.get('reopen_count', 0) >= 1, 'stage card should expose reopen_count')
    _assert(signals.get('revive_count', 0) >= 1, 'stage card should expose revive_count')
    _assert(signals.get('consequence_history_available') is True, 'stage card should expose consequence_history_available')
    _assert(signals.get('consequence_history_event_count', 0) >= 6, 'stage card should expose consequence_history_event_count')
    _assert(bool(signals.get('recent_consequence_transitions')), 'stage card should expose recent_consequence_transitions')
    _assert(signals.get('transition_ledger_available') is True, 'stage card should expose transition_ledger_available')
    _assert(signals.get('transition_event_count', 0) >= 6, 'stage card should expose transition_event_count')
    _assert(bool(signals.get('recent_transition_events')), 'stage card should expose recent_transition_events')
    _assert(bool(signals.get('top_transition_triggers')), 'stage card should expose top_transition_triggers')
    _assert(bool(signals.get('recent_restore_timeline')), 'stage card should expose recent_restore_timeline')
    _assert(signals.get('shared_source_archived_count', 0) >= 4, 'stage card should expose thickened shared_source_archived_count')
    _assert(bool(signals.get('recent_restore_actions')), 'stage card should expose recent_restore_actions')

    _assert((archive_policy.get('archive_evidence_scope_counts') or {}).get('shared_release_rollback', 0) >= 4, 'archive policy review should count thickened shared release/rollback archived evidence')
    history_review = _load(STATE_ROOT / 'rule_consequence_history.json')
    restore_timeline = _load(STATE_ROOT / 'archive_restore_timeline.json')
    transition_digest = _load(STATE_ROOT / 'rule_transition_digest.json')
    transition_ledger_lines = (STATE_ROOT / 'rule_transition_ledger.jsonl').read_text(encoding='utf-8').splitlines()
    _assert(history_review.get('history_available') is True, 'consequence history should be available')
    _assert(history_review.get('history_event_count', 0) >= 6, 'consequence history should capture multi-step transitions')
    _assert(any(item.get('transition_type') == 'archive_reopen' for item in (history_review.get('recent_transitions') or [])), 'consequence history should track reopen transitions')
    _assert(len(transition_ledger_lines) >= 6, 'transition ledger should append multiple state changes')
    _assert(transition_digest.get('transition_ledger_available') is True, 'transition digest should expose ledger availability')
    _assert(transition_digest.get('transition_event_count', 0) >= 6, 'transition digest should count ledger events')
    _assert(bool(transition_digest.get('recent_transition_events')), 'transition digest should expose recent transition events')
    _assert(bool(transition_digest.get('top_transition_triggers')), 'transition digest should aggregate top transition triggers')
    _assert(archive_restore_review.get('shared_source_archived_count', 0) >= 4, 'archive restore review should count thickened shared source archived samples')
    _assert(bool(restore_timeline.get('recent_restore_timeline')), 'archive restore timeline should contain recent restore actions')
    _assert((archive_restore_review.get('restore_state_counts') or {}).get('reviewing', 0) >= 1, 'archive restore review should preserve reopen reviewing route')
    _assert(any(item.get('shared_governance_rule') for item in (restore_registry.get('items') or {}).values()), 'restore registry should preserve shared governance flag on restore actions')
    _assert(any(int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 for item in proposals), 'release evidence still present in common governance set')
    _assert(any(int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 for item in proposals), 'rollback evidence still present in common governance set')

    result = {
        'bootstrap_cycle_id': bootstrap.get('cycle_id'),
        'reject_old_cycle_id': reject_old_cycle.get('cycle_id'),
        'restore_cycle_id': restore_cycle.get('cycle_id'),
        'reopen_cycle_id': reopen_cycle.get('cycle_id'),
        'thickened_cycle_id': thickened_cycle.get('cycle_id'),
        'revive_cycle_id': revive_cycle.get('cycle_id'),
        'conflict_id': conflict_id,
        'restore_state_routes': {
            'restore': restore_entry.get('status'),
            'reopen': reopen_entry.get('status'),
            'revive': revive_entry.get('status'),
        },
        'shared_archived_sample': {
            'proposal_id': shared_item['proposal_id'],
            'archive_policy': (shared_archived_snapshot.get('archive_metadata') or {}).get('archived_policy'),
            'evidence_scope': (shared_archived_snapshot.get('archive_metadata') or {}).get('evidence_scope'),
            'shared_governance_rule': (shared_archived_snapshot.get('archive_metadata') or {}).get('shared_governance_rule'),
        },
        'archive_restore_registry': {
            'restored_count': restore_registry.get('restored_count'),
            'reopened_count': restore_registry.get('reopened_count'),
            'revived_count': restore_registry.get('revived_count'),
            'restore_state_counts': restore_registry.get('restore_state_counts'),
            'recent_archive_actions': restore_registry.get('recent_archive_actions'),
        },
        'archive_restore_review': archive_restore_review,
        'consequence_history_review': history_review,
        'archive_restore_timeline': restore_timeline,
        'latest_cycle_metrics': {
            'restore_state_counts': latest_cycle.get('restore_state_counts'),
            'reopen_count': latest_cycle.get('reopen_count'),
            'revive_count': latest_cycle.get('revive_count'),
            'consequence_history_available': latest_cycle.get('consequence_history_available'),
            'consequence_history_event_count': latest_cycle.get('consequence_history_event_count'),
            'recent_consequence_transitions': latest_cycle.get('recent_consequence_transitions'),
            'shared_source_archived_count': latest_cycle.get('shared_source_archived_count'),
            'recent_restore_actions': latest_cycle.get('recent_restore_actions'),
        },
        'stage_card_metrics': {
            'restore_state_counts': signals.get('restore_state_counts'),
            'reopen_count': signals.get('reopen_count'),
            'revive_count': signals.get('revive_count'),
            'consequence_history_available': signals.get('consequence_history_available'),
            'consequence_history_event_count': signals.get('consequence_history_event_count'),
            'recent_consequence_transitions': signals.get('recent_consequence_transitions'),
            'recent_restore_timeline': signals.get('recent_restore_timeline'),
            'shared_source_archived_count': signals.get('shared_source_archived_count'),
            'recent_restore_actions': signals.get('recent_restore_actions'),
        },
        'consequence_review': consequence_review,
        'archive_policy_review': archive_policy,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
