#!/usr/bin/env python3
import json
from pathlib import Path

SESSIONS_FILE = Path('/home/admin/.openclaw/agents/master-quant/sessions/sessions.json')

with open(SESSIONS_FILE, 'r') as f:
    data = json.load(f)

session_key = 'agent:master-quant:feishu:direct:ou_61884ea8aa288c6514cc8b4cb3cd16d8'
if session_key in data:
    del data[session_key]
    print(f'Removed session: {session_key}')
else:
    print('Session not found')

with open(SESSIONS_FILE, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Done')
