#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 follow-up ticket 入队到统一 queue。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

QUEUE_ROOT = Path("/home/admin/.openclaw/workspace/master/reports/workflow/queue")
PENDING_DIR = QUEUE_ROOT / "pending"
DISPATCHED_DIR = QUEUE_ROOT / "dispatched"
DONE_DIR = QUEUE_ROOT / "done"
FAILED_DIR = QUEUE_ROOT / "failed"
for d in [PENDING_DIR, DISPATCHED_DIR, DONE_DIR, FAILED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def locate(ticket_id: str) -> Path | None:
    safe = ticket_id.replace(":", "__") + ".json"
    for d in [PENDING_DIR, DISPATCHED_DIR, DONE_DIR, FAILED_DIR]:
        p = d / safe
        if p.exists():
            return p
    return None


def find_similar_open_ticket(ticket: Dict) -> Optional[Path]:
    """按 category + dispatch_agent_id + title 做去重，避免连续重复工单刷屏。"""
    for d in [PENDING_DIR, DISPATCHED_DIR]:
        for p in d.glob('*.json'):
            try:
                payload = load_json(p)
                old = payload.get('ticket', {})
                if old.get('category') == ticket.get('category') and \
                   old.get('dispatch_agent_id') == ticket.get('dispatch_agent_id') and \
                   old.get('title') == ticket.get('title'):
                    return p
            except Exception:
                continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="queue_ticket")
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    followup = cycle_dir / "artifacts" / "followup_ticket" / "followup_tickets.json"
    if not followup.exists():
        raise SystemExit(f"未找到 followup_tickets.json: {followup}")

    data = load_json(followup)
    enqueued: List[Dict] = []
    skipped: List[Dict] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for ticket in data.get("tickets", []):
        existing = locate(ticket["ticket_id"])
        if existing:
            skipped.append({"ticket_id": ticket["ticket_id"], "reason": f"already_exists:{existing.parent.name}"})
            continue

        similar = find_similar_open_ticket(ticket)
        if similar:
            payload = load_json(similar)
            payload.setdefault('merged_from', [])
            payload['merged_from'].append({
                'ticket_id': ticket['ticket_id'],
                'cycle_id': data.get('cycle_id'),
                'cycle_type': data.get('cycle_type'),
                'merged_at': now,
                'reason': ticket.get('reason'),
            })
            payload['updated_at'] = now
            write_json(similar, payload)
            skipped.append({"ticket_id": ticket["ticket_id"], "reason": f"merged_into:{similar.name}"})
            continue

        safe = ticket["ticket_id"].replace(":", "__") + ".json"
        payload = {
            "queue_status": "pending",
            "enqueued_at": now,
            "updated_at": now,
            "cycle_id": data.get("cycle_id"),
            "cycle_type": data.get("cycle_type"),
            "source_cycle_dir": str(cycle_dir),
            "followup_file": str(followup),
            "ticket": ticket,
            "merged_from": [],
        }
        out = PENDING_DIR / safe
        write_json(out, payload)
        enqueued.append({"ticket_id": ticket["ticket_id"], "path": str(out)})

    artifact = cycle_dir / "artifacts" / args.stage_id / "queue_result.json"
    result = {
        "stage": args.stage_id,
        "generated_at": now,
        "cycle_id": data.get("cycle_id"),
        "cycle_type": data.get("cycle_type"),
        "enqueued": enqueued,
        "skipped": skipped,
    }
    write_json(artifact, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
