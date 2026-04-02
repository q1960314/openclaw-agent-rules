#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恢复过重/aborted 的 agent 主会话。

动作：
1. 备份 sessions.json
2. 备份/归档 main session transcript（若存在）
3. 从 sessions.json 中移除 agent:xxx:main 项，促使下次调用创建新会话
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

BASE = Path('/home/admin/.openclaw/agents')
WORKFLOW_REPORT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/recovery')
WORKFLOW_REPORT.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent-id', required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    agent_dir = BASE / args.agent_id / 'sessions'
    store = agent_dir / 'sessions.json'
    key = f'agent:{args.agent_id}:main'
    now = datetime.now().strftime('%Y%m%d_%H%M%S')

    if not store.exists():
        raise SystemExit(f'未找到 session store: {store}')

    data = load_json(store)
    entry = data.get(key)
    if not entry:
        result = {'agent_id': args.agent_id, 'status': 'no_main_session', 'store': str(store)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    health = {
        'abortedLastRun': bool(entry.get('abortedLastRun')),
        'contextTokens': entry.get('contextTokens') or 0,
        'totalTokens': entry.get('totalTokens') or 0,
        'sessionId': entry.get('sessionId'),
    }
    overloaded = bool(health['contextTokens'] and health['totalTokens'] and health['totalTokens'] / health['contextTokens'] >= 0.80)
    if not args.force and not health['abortedLastRun'] and not overloaded:
        result = {'agent_id': args.agent_id, 'status': 'skip_healthy', 'health': health}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    backup_store = agent_dir / f'sessions.backup_{now}.json'
    shutil.copy2(store, backup_store)

    archived_transcript = None
    session_id = entry.get('sessionId')
    if session_id:
        transcript = agent_dir / f'{session_id}.jsonl'
        if transcript.exists():
            archive_dir = agent_dir / 'archive'
            archive_dir.mkdir(parents=True, exist_ok=True)
            archived_transcript = archive_dir / f'{session_id}_{now}.jsonl'
            shutil.move(str(transcript), str(archived_transcript))

    del data[key]
    write_json(store, data)

    result = {
        'agent_id': args.agent_id,
        'status': 'recovered',
        'health_before': health,
        'overloaded': overloaded,
        'backup_store': str(backup_store),
        'archived_transcript': str(archived_transcript) if archived_transcript else None,
        'store': str(store),
    }
    out = WORKFLOW_REPORT / f'{args.agent_id}_{now}.json'
    write_json(out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
