#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 review manager."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class ReviewManager:
    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.review_file = self.task_dir / "review.json"

    def write(self, reviewed_by: str, decision: str, issues: list[str] | None = None, evidence: list[str] | None = None, **extra) -> dict:
        payload = {
            "task_id": self.task_dir.name,
            "reviewed_by": reviewed_by,
            "decision": decision,
            "issues": issues or [],
            "evidence": evidence or [],
            "reviewed_at": datetime.now().astimezone().isoformat(),
        }
        payload.update(extra)
        self.review_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
