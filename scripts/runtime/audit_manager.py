#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 audit/event manager."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditManager:
    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.task_dir / 'events.jsonl'

    def append(self, event_type: str, actor: str, **payload: Any) -> dict[str, Any]:
        item = {
            'ts': datetime.now().astimezone().isoformat(),
            'task_id': self.task_dir.name,
            'event_type': event_type,
            'actor': actor,
            'payload': payload,
        }
        with self.events_file.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + '\n')
        return item
