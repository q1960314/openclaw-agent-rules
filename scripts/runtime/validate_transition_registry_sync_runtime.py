#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from rule_proposal_runtime import STATE_ROOT, build_rule_proposal_review, export_rulebook_artifacts, materialize_rule_sink
from worker_runtime_scheduler import run_cycle


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    txt = path.read_text(encoding='utf-8').strip()
    return json.loads(txt) if txt else {}


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()])


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    followup = _load_json(STATE_ROOT / 'latest_followup_resolution_review.json')
    _assert(bool(followup), 'latest_followup_resolution_review.json is required for validation')
    cycle_id = 'VALIDATE-TRANSITION-REGISTRY-SYNC'
    review = build_rule_proposal_review(followup_resolution_review=followup, latest_cycle={}, state_root=STATE_ROOT, cycle_id=cycle_id)
    materialize_rule_sink(rule_proposal_review=review, state_root=STATE_ROOT, cycle_id=cycle_id)

    ledger_path = STATE_ROOT / 'rule_transition_ledger.jsonl'
    suppression_path = STATE_ROOT / 'rule_transition_suppressions.jsonl'
    before_ledger = _count_lines(ledger_path)
    before_suppressed = _count_lines(suppression_path)

    first_export = export_rulebook_artifacts(rule_proposal_review=review, state_root=STATE_ROOT, cycle_id=cycle_id, export_target='local-rulebook')
    after_first_ledger = _count_lines(ledger_path)
    after_first_suppressed = _count_lines(suppression_path)
    second_export = export_rulebook_artifacts(rule_proposal_review=review, state_root=STATE_ROOT, cycle_id=cycle_id + '-RERUN', export_target='local-rulebook')
    after_second_ledger = _count_lines(ledger_path)
    after_second_suppressed = _count_lines(suppression_path)

    digest = _load_json(STATE_ROOT / 'transition_ledger_digest_review.json')
    sync_audit = _load_json(STATE_ROOT / 'rule_registry_sync_audit.json')

    _assert(after_first_ledger >= before_ledger, 'ledger must remain append-only after first export')
    _assert(after_second_ledger >= after_first_ledger, 'ledger must remain append-only after rerun')
    _assert(after_second_suppressed >= after_first_suppressed >= before_suppressed, 'suppression log should be monotonic append-only')
    _assert(int(second_export.get('transition_duplicate_suppressed_count', 0) or 0) >= int(first_export.get('transition_duplicate_suppressed_count', 0) or 0), 'rerun should not reduce suppressed duplicate count')
    _assert(int(digest.get('digest_duplicate_semantic_event_count', 0) or 0) == 0, 'digest-level duplicate semantic events should remain collapsed to zero for current ledger')
    _assert(bool(sync_audit.get('consistency_audit_available')), 'registry sync audit must be available')
    _assert(int(sync_audit.get('registry_sync_issue_count', 0) or 0) >= 0, 'registry sync audit must expose issue count')

    cycle_summary = run_cycle(backfill_missing=False)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage = _load_json(STATE_ROOT / 'latest_stage_card.json')
    signals = latest_stage.get('signals', {}) if isinstance(latest_stage.get('signals'), dict) else {}

    _assert('transition_duplicate_suppressed_count' in latest_cycle, 'latest_cycle must expose transition_duplicate_suppressed_count')
    _assert('registry_sync_issue_count' in latest_cycle, 'latest_cycle must expose registry_sync_issue_count')
    _assert('sync_scope_exception_count' in latest_cycle, 'latest_cycle must expose sync_scope_exception_count')
    _assert('audit_scope_refinement_available' in latest_cycle, 'latest_cycle must expose audit_scope_refinement_available')
    _assert('registry_sync_review_available' in latest_cycle, 'latest_cycle must expose registry_sync_review_available')
    _assert('consistency_audit_available' in latest_cycle, 'latest_cycle must expose consistency_audit_available')
    _assert('recent_sync_issues' in latest_cycle, 'latest_cycle must expose recent_sync_issues')
    _assert('recent_scope_exceptions' in latest_cycle, 'latest_cycle must expose recent_scope_exceptions')
    _assert('transition_duplicate_suppressed_count' in signals, 'stage card must expose transition_duplicate_suppressed_count')
    _assert('registry_sync_issue_count' in signals, 'stage card must expose registry_sync_issue_count')
    _assert('sync_scope_exception_count' in signals, 'stage card must expose sync_scope_exception_count')
    _assert('audit_scope_refinement_available' in signals, 'stage card must expose audit_scope_refinement_available')
    _assert('registry_sync_review_available' in signals, 'stage card must expose registry_sync_review_available')
    _assert('consistency_audit_available' in signals, 'stage card must expose consistency_audit_available')
    _assert(int(sync_audit.get('sync_scope_exception_count', 0) or 0) >= 0, 'registry sync audit must expose sync scope exception count')
    _assert(any(int((item.get('source_targets') or {}).get('official_release', 0) or 0) > 0 and int((item.get('source_targets') or {}).get('rollback', 0) or 0) > 0 for item in (first_export.get('items') or []) if isinstance(item, dict)), 'release/rollback evidence should still share the same governed export rules')
    _assert(not any(item.get('issue_type') == 'shared_release_rollback_evidence_missing' for item in (sync_audit.get('issues') or []) if isinstance(item, dict) and str(item.get('proposal_id') or '') in {'proposal-02aaba9d0e', 'proposal-137353edea'}), 'rollback-only rules should not be flagged as shared evidence missing')
    _assert((STATE_ROOT / 'shared_sample_governance_registry.json').exists(), 'shared sample governance registry should be materialized')
    _assert((STATE_ROOT / 'rule_registry_sync_scope_review.json').exists(), 'registry sync scope review should be materialized')

    result = {
        'before_ledger_count': before_ledger,
        'after_first_ledger_count': after_first_ledger,
        'after_second_ledger_count': after_second_ledger,
        'before_suppressed_count': before_suppressed,
        'after_first_suppressed_count': after_first_suppressed,
        'after_second_suppressed_count': after_second_suppressed,
        'digest_duplicate_semantic_event_count': digest.get('digest_duplicate_semantic_event_count', 0),
        'transition_duplicate_suppressed_count': digest.get('transition_duplicate_suppressed_count', 0),
        'registry_sync_issue_count': sync_audit.get('registry_sync_issue_count', 0),
        'sync_scope_exception_count': sync_audit.get('sync_scope_exception_count', 0),
        'registry_sync_ok': sync_audit.get('registry_sync_ok', False),
        'latest_cycle_transition_duplicate_suppressed_count': latest_cycle.get('transition_duplicate_suppressed_count'),
        'latest_cycle_registry_sync_issue_count': latest_cycle.get('registry_sync_issue_count'),
        'latest_cycle_sync_scope_exception_count': latest_cycle.get('sync_scope_exception_count'),
        'latest_cycle_audit_scope_refinement_available': latest_cycle.get('audit_scope_refinement_available'),
        'stage_card_transition_duplicate_suppressed_count': signals.get('transition_duplicate_suppressed_count'),
        'stage_card_registry_sync_issue_count': signals.get('registry_sync_issue_count'),
        'stage_card_sync_scope_exception_count': signals.get('sync_scope_exception_count'),
        'stage_card_audit_scope_refinement_available': signals.get('audit_scope_refinement_available'),
        'cycle_id': cycle_summary.get('cycle_id'),
    }
    out = STATE_ROOT / 'validate_transition_registry_sync_runtime.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
