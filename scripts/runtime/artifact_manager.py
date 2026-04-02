#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 artifact manager with automatic artifact manifest maintenance."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ArtifactManager:
    MANIFEST_NAME = 'artifact_manifest.json'

    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.artifacts_dir = self.task_dir / 'artifacts'
        self.logs_dir = self.task_dir / 'logs'
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.artifacts_dir / self.MANIFEST_NAME

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def _kind(self, path: Path, default: str) -> str:
        if path.suffix == '.json':
            return 'json'
        if path.suffix in {'.md', '.txt', '.patch'}:
            return 'text'
        return default

    def _update_manifest(self) -> None:
        artifacts = []
        for p in sorted(self.artifacts_dir.rglob('*')):
            if not p.is_file() or p.name == self.MANIFEST_NAME:
                continue
            stat = p.stat()
            artifacts.append({
                'path': str(p.relative_to(self.task_dir)),
                'kind': self._kind(p, 'other'),
                'size_bytes': stat.st_size,
                'updated_at': datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
            })
        payload = {
            'task_id': self.task_dir.name,
            'generated_at': self._now(),
            'artifacts': artifacts,
        }
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def write_text(self, relative_name: str, content: str) -> Path:
        path = self.artifacts_dir / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        if path.name != self.MANIFEST_NAME:
            self._update_manifest()
        return path

    def write_json(self, relative_name: str, payload: Any) -> Path:
        path = self.artifacts_dir / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        if path.name != self.MANIFEST_NAME:
            self._update_manifest()
        return path

    def append_log(self, filename: str, line: str) -> Path:
        path = self.logs_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as fh:
            fh.write(line.rstrip('\n') + '\n')
        return path

    def list_artifacts(self) -> list[str]:
        files = [str(p.relative_to(self.task_dir)) for p in self.artifacts_dir.rglob('*') if p.is_file()]
        return sorted(files)
