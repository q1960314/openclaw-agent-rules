#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from rule_proposal_runtime import apply_rule_proposal_action, update_rule_sink_status
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
STATE_ROOT = ROOT / 'reports' / 'worker-runtime' / 'state'
JOBS_ROOT = ROOT / 'traces' / 'jobs'


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))



def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)



def _find_proposal(payload: dict, *, state: str | None = None, target: str | None = None, exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    for item in list(payload.get('proposals', []) or []):
        if item.get('proposal_id') in exclude:
            continue
        if state and item.get('proposal_state') != state:
            continue
        if target and int((item.get('source_targets') or {}).get(target, 0) or 0) <= 0:
            continue
        return item
    raise AssertionError(f'proposal not found: state={state}, target={target}')



def main() -> int:
    (STATE_ROOT / 'rule_proposal_review_registry.json').write_text(json.dumps({'proposals': {}, 'reset_for_validation': True}, ensure_ascii=False, indent=2), encoding='utf-8')

    bootstrap_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-rule-proposal-bootstrap', backfill_missing=True)
    bootstrap_review = _load_json(STATE_ROOT / 'latest_rule_proposal_review.json')

    _assert(bootstrap_review.get('proposal_count', 0) >= 3, 'bootstrap should produce multiple rule proposals')
    _assert(any(int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 for item in (bootstrap_review.get('proposals') or [])), 'release evidence should enter proposal governance')
    _assert(any(int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 for item in (bootstrap_review.get('proposals') or [])), 'rollback evidence should enter proposal governance')

    used: set[str] = set()
    draft_item = _find_proposal(bootstrap_review, state='draft')
    used.add(draft_item['proposal_id'])
    accepted_item = _find_proposal(bootstrap_review, state='proposed', target='rollback', exclude=used)
    used.add(accepted_item['proposal_id'])
    rejected_item = _find_proposal(bootstrap_review, state='proposed', target='official_release', exclude=used)
    used.add(rejected_item['proposal_id'])

    apply_rule_proposal_action(
        proposal_id=draft_item['proposal_id'],
        action='propose',
        reviewer='validator-rule-proposal',
        note='promote draft proposal into review queue',
        sink_target='knowledge_candidate',
        state_root=STATE_ROOT,
    )
    apply_rule_proposal_action(
        proposal_id=accepted_item['proposal_id'],
        action='accept',
        reviewer='validator-rule-proposal',
        note='accepted after cross-target rollback evidence review',
        sink_target='rulebook_candidate',
        state_root=STATE_ROOT,
    )
    apply_rule_proposal_action(
        proposal_id=rejected_item['proposal_id'],
        action='reject',
        reviewer='validator-rule-proposal',
        note='rejected pending more release-side evidence',
        sink_target='knowledge_candidate',
        state_root=STATE_ROOT,
    )

    cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-rule-proposal-final', backfill_missing=True)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage = _load_json(STATE_ROOT / 'latest_stage_card.json')
    latest_review = _load_json(STATE_ROOT / 'latest_rule_proposal_review.json')
    governed_rules = _load_json(STATE_ROOT / 'latest_governed_rule_candidates.json')
    accepted_registry = _load_json(STATE_ROOT / 'accepted_rule_registry.json')

    signals = latest_stage.get('signals') or {}
    proposals = {item.get('proposal_id'): item for item in (latest_review.get('proposals') or [])}
    accepted = proposals.get(accepted_item['proposal_id']) or {}
    rejected = proposals.get(rejected_item['proposal_id']) or {}
    promoted = proposals.get(draft_item['proposal_id']) or {}

    _assert(promoted.get('proposal_state') == 'proposed', 'draft proposal should be promotable into proposed state')
    _assert(accepted.get('proposal_state') == 'accepted', 'proposal should reach accepted state')
    _assert(rejected.get('proposal_state') == 'rejected', 'proposal should reach rejected state')
    _assert(latest_cycle.get('rule_proposal_count', 0) >= bootstrap_review.get('proposal_count', 0), 'latest_cycle should expose proposal count')
    _assert(latest_cycle.get('rule_proposal_pending_review_count', 0) >= 1, 'latest_cycle should expose pending review count')
    _assert(latest_cycle.get('rule_proposal_accepted_count', 0) >= 1, 'latest_cycle should expose accepted count')
    _assert(latest_cycle.get('rule_proposal_rejected_count', 0) >= 1, 'latest_cycle should expose rejected count')
    _assert(signals.get('rule_proposal_count', 0) >= 1, 'stage card should expose proposal count')
    _assert(signals.get('rule_proposal_pending_review_count', 0) >= 1, 'stage card should expose pending review count')
    _assert(signals.get('rule_proposal_accepted_count', 0) >= 1, 'stage card should expose accepted count')
    _assert(signals.get('rule_proposal_rejected_count', 0) >= 1, 'stage card should expose rejected count')
    _assert(bool(latest_review.get('digest_available')), 'rule proposal review digest should be generated')
    _assert((STATE_ROOT / 'latest_rule_proposal_review.md').exists(), 'rule proposal review markdown digest should exist')
    _assert(any(item.get('proposal_id') == accepted_item['proposal_id'] for item in (latest_review.get('accepted_sink_items') or [])), 'accepted proposal should enter sink-ready artifact')
    _assert(governed_rules.get('written_count', 0) >= 1, 'accepted proposal should be materialized into governed rule artifact')
    written_item = next((item for item in (governed_rules.get('items') or []) if item.get('proposal_id') == accepted_item['proposal_id']), None)
    _assert(bool(written_item), 'written governed rule item should exist for accepted proposal')
    artifact_path = STATE_ROOT / str((written_item or {}).get('artifact_path') or '')
    _assert(artifact_path.exists(), 'governed rule artifact file should exist')
    artifact = _load_json(artifact_path)
    _assert(artifact.get('proposal_id') == accepted_item['proposal_id'], 'artifact should preserve proposal_id traceability')
    _assert(((artifact.get('governance') or {}).get('reviewer')) == accepted.get('reviewer'), 'artifact should preserve reviewer traceability')
    _assert(len(artifact.get('evidence') or []) >= 1, 'artifact should preserve evidence traceability')
    _assert(signals.get('rule_sink_ready_count', 0) >= 1, 'stage card should expose sink-ready count')
    _assert(signals.get('written_rule_candidate_count', 0) >= 1, 'stage card should expose written rule count')
    _assert(latest_cycle.get('rule_sink_ready_count', 0) >= 1, 'latest_cycle should expose sink-ready count')
    _assert(latest_cycle.get('written_rule_candidate_count', 0) >= 1, 'latest_cycle should expose written rule count')
    _assert(any(int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 for item in proposals.values()), 'proposal set should include release-side evidence')
    _assert(any(int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 for item in proposals.values()), 'proposal set should include rollback-side evidence')

    update_rule_sink_status(proposal_id=accepted_item['proposal_id'], action='export', export_target='local-rulebook', state_root=STATE_ROOT)
    exported_registry = _load_json(STATE_ROOT / 'accepted_rule_registry.json')
    result = {
        'bootstrap_cycle_id': bootstrap_cycle.get('cycle_id'),
        'final_cycle_id': cycle.get('cycle_id'),
        'bootstrap_proposal_count': bootstrap_review.get('proposal_count'),
        'final_proposal_state_counts': latest_review.get('proposal_state_counts'),
        'latest_cycle_metrics': {
            'rule_proposal_count': latest_cycle.get('rule_proposal_count'),
            'rule_proposal_pending_review_count': latest_cycle.get('rule_proposal_pending_review_count'),
            'rule_proposal_accepted_count': latest_cycle.get('rule_proposal_accepted_count'),
            'rule_proposal_rejected_count': latest_cycle.get('rule_proposal_rejected_count'),
            'top_proposed_rules': latest_cycle.get('top_proposed_rules'),
        },
        'stage_card_metrics': {
            'rule_proposal_count': signals.get('rule_proposal_count'),
            'rule_proposal_pending_review_count': signals.get('rule_proposal_pending_review_count'),
            'rule_proposal_accepted_count': signals.get('rule_proposal_accepted_count'),
            'rule_proposal_rejected_count': signals.get('rule_proposal_rejected_count'),
            'top_proposed_rules': signals.get('top_proposed_rules'),
        },
        'accepted_proposal': accepted,
        'rejected_proposal': rejected,
        'promoted_proposal': promoted,
        'accepted_sink_items': latest_review.get('accepted_sink_items'),
        'governed_rules': governed_rules,
        'accepted_rule_registry': accepted_registry,
        'exported_entry': ((exported_registry.get('items') or {}).get(accepted_item['proposal_id'])),
        'digest_markdown_preview': latest_review.get('digest_markdown'),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
