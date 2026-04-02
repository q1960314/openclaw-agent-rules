#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流状态面板（CLI 版）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

WORKFLOW_STATE_ROOT = Path("/home/admin/.openclaw/workspace/master/reports/workflow/state")
WORKFLOW_LATEST_STATUS = WORKFLOW_STATE_ROOT / "latest_status.json"
WORKFLOW_LATEST_CYCLES = WORKFLOW_STATE_ROOT / "latest_cycles.json"
WORKFLOW_EVENTS = WORKFLOW_STATE_ROOT / "events.jsonl"

WORKER_RUNTIME_STATE_ROOT = Path("/home/admin/.openclaw/workspace/master/reports/worker-runtime/state")
WORKER_RUNTIME_LATEST = WORKER_RUNTIME_STATE_ROOT / "latest_cycle.json"
WORKER_RUNTIME_HEALTH = WORKER_RUNTIME_STATE_ROOT / "latest_health_dashboard.json"
WORKER_RUNTIME_RECOVERY = WORKER_RUNTIME_STATE_ROOT / "latest_recovery_dashboard.json"
WORKER_RUNTIME_LIFECYCLE = WORKER_RUNTIME_STATE_ROOT / "latest_lifecycle_dashboard.json"
WORKER_RUNTIME_STAGE_CARD = WORKER_RUNTIME_STATE_ROOT / "latest_stage_card.json"
WORKER_RUNTIME_EVENTS = WORKER_RUNTIME_STATE_ROOT / "events.jsonl"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events(path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    data = [json.loads(line) for line in lines if line.strip()]
    return data[-limit:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--events", type=int, default=8)
    args = parser.parse_args()

    payload = {
        "workflow": {
            "latest_status": load_json(WORKFLOW_LATEST_STATUS),
            "latest_cycles": load_json(WORKFLOW_LATEST_CYCLES) or {},
            "recent_events": load_events(WORKFLOW_EVENTS, args.events),
        },
        "worker_runtime": {
            "latest_cycle": load_json(WORKER_RUNTIME_LATEST),
            "latest_health": load_json(WORKER_RUNTIME_HEALTH),
            "latest_recovery": load_json(WORKER_RUNTIME_RECOVERY),
            "latest_lifecycle": load_json(WORKER_RUNTIME_LIFECYCLE),
            "latest_stage_card": load_json(WORKER_RUNTIME_STAGE_CARD),
            "recent_events": load_events(WORKER_RUNTIME_EVENTS, args.events),
        },
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=== Workflow Dashboard ===")
    latest = payload["workflow"]["latest_status"] or {}
    if latest:
        print(f"当前活动循环: {latest.get('cycle_id')}")
        print(f"类型: {latest.get('cycle_type')}")
        print(f"状态: {latest.get('status')} / {latest.get('stage_status')}")
        print(f"当前阶段: {latest.get('current_stage')}")
        print(f"更新时间: {latest.get('updated_at')}")
        if latest.get("elapsed_seconds") is not None:
            print(f"阶段已运行: {latest.get('elapsed_seconds')}s")
        print("")
    else:
        print("暂无 latest_status")
        print("")

    print("--- Latest Workflow Cycles ---")
    for cycle_type, item in (payload["workflow"]["latest_cycles"] or {}).items():
        print(f"[{cycle_type}] {item.get('cycle_id')} | status={item.get('status')} | stage={item.get('current_stage')} | updated={item.get('updated_at')}")
    print("")

    print("--- Workflow Recent Events ---")
    for ev in payload["workflow"]["recent_events"]:
        print(f"{ev.get('time')} | {ev.get('event_type')} | {ev.get('cycle_id')} | stage={ev.get('stage', ev.get('current_stage'))} | status={ev.get('status')}")
    print("")

    print("=== Worker Runtime Scheduler ===")
    runtime_latest = payload["worker_runtime"]["latest_cycle"] or {}
    if runtime_latest:
        print(f"最新巡检周期: {runtime_latest.get('cycle_id')}")
        print(f"更新时间: {runtime_latest.get('generated_at')}")
        print(f"job_count={runtime_latest.get('job_count')} stale_count={runtime_latest.get('stale_count')} healed_count={runtime_latest.get('healed_count')}")
        print(f"governance_action_count={runtime_latest.get('governance_action_count')} retry_created_count={runtime_latest.get('retry_created_count')}")
        print(f"recoverability_counts={runtime_latest.get('recoverability_counts')}")
        print(f"quality_grade_counts={runtime_latest.get('quality_grade_counts')} average_quality_score={runtime_latest.get('quality_average_score')}")
        print(f"formalization_state_counts={runtime_latest.get('formalization_state_counts')}")
        print(f"closure_counts={runtime_latest.get('closure_counts')}")
        print(f"backfill_jobs_scanned={runtime_latest.get('backfill_jobs_scanned')} backfill_quality_count={runtime_latest.get('backfill_quality_count')} backfill_formalization_count={runtime_latest.get('backfill_formalization_count')} backfill_closure_count={runtime_latest.get('backfill_closure_count')}")
        print(f"lifecycle_bucket_counts={runtime_latest.get('lifecycle_bucket_counts')}")
        print("")
    else:
        print("暂无 worker runtime latest_cycle")
        print("")

    health = payload["worker_runtime"].get("latest_health") or {}
    recovery = payload["worker_runtime"].get("latest_recovery") or {}
    lifecycle = payload["worker_runtime"].get("latest_lifecycle") or {}
    stage_card = payload["worker_runtime"].get("latest_stage_card") or {}
    if health:
        print("--- Worker Runtime Health ---")
        print(f"job_count={health.get('job_count')} stale_count={health.get('stale_count')} recoverability_counts={health.get('recoverability_counts')} quality_grade_counts={health.get('quality_grade_counts')} average_quality_score={health.get('quality_average_score')} formalization_state_counts={health.get('formalization_state_counts')} closure_counts={health.get('closure_counts')}")
    if recovery:
        print("--- Worker Runtime Recovery ---")
        print(f"recoverability_counts={recovery.get('recoverability_counts')} quality_grade_counts={recovery.get('quality_grade_counts')} average_quality_score={recovery.get('quality_average_score')} formalization_state_counts={recovery.get('formalization_state_counts')} closure_counts={recovery.get('closure_counts')}")
    if lifecycle:
        print("--- Worker Runtime Lifecycle ---")
        print(f"bucket_counts={lifecycle.get('bucket_counts')} status_counts={lifecycle.get('status_counts')} quality_grade_counts={lifecycle.get('quality_grade_counts')} average_quality_score={lifecycle.get('quality_average_score')} formalization_state_counts={lifecycle.get('formalization_state_counts')} closure_counts={lifecycle.get('closure_counts')}")
    if stage_card:
        print("--- Ecosystem Stage Card ---")
        print(f"stage_id={stage_card.get('stage_id')} maturity_band={stage_card.get('maturity_band')} stage_label={stage_card.get('stage_label')}")
        print(f"phase_completion_state={stage_card.get('phase_completion_state')} closure_readiness_state={stage_card.get('closure_readiness_state')}")
        next_card = stage_card.get('next_action_card') or {}
        print(f"next_action={next_card.get('title')} | priority={next_card.get('priority')}")
    if health or recovery or lifecycle or stage_card:
        print("")

    print("--- Worker Runtime Recent Events ---")
    for ev in payload["worker_runtime"]["recent_events"]:
        print(f"{ev.get('time')} | {ev.get('event_type')} | cycle_id={ev.get('cycle_id')} | healed_count={ev.get('healed_count')} | stale_count={ev.get('stale_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
