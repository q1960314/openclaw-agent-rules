#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')
OPENCODE_BIN = '/home/admin/.npm-global/bin/opencode'

def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def extract_texts(lines: List[str]) -> str:
    texts=[]
    for raw in lines:
        try:
            item=json.loads(raw)
        except Exception:
            continue
        if item.get('type')=='text':
            part=item.get('part',{})
            if part.get('text'):
                texts.append(part['text'])
    return '\n'.join(texts).strip()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='opencode_build')
    args = parser.parse_args()
    cfg = load_json(CONFIG)
    model = cfg.get('opencode',{}).get('build_model','bailian/qwen3-coder-plus')
    cycle_dir = Path(args.cycle_dir)
    task = load_json(cycle_dir / 'artifacts' / 'prepare_build_task' / 'build_task.json')
    worktree = task['worktree']
    prompt = task['prompt']
    cmd = [OPENCODE_BIN,'run','--format','json','--agent','build','--model',model,'--dir',worktree,prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    lines=[x for x in proc.stdout.splitlines() if x.strip()]
    text=extract_texts(lines)
    result={'stage':args.stage_id,'generated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'model':model,'worktree':worktree,'returncode':proc.returncode,'text':text,'raw_lines':len(lines),'stderr':proc.stderr[-2000:]}
    out=cycle_dir / 'artifacts' / args.stage_id / 'opencode_build.json'
    write_json(out,result)
    (cycle_dir / 'artifacts' / args.stage_id / 'opencode_build.md').write_text(text or '', encoding='utf-8')
    print(json.dumps({'returncode':proc.returncode,'text_chars':len(text),'worktree':worktree}, ensure_ascii=False, indent=2))
    return 0 if proc.returncode==0 else 1

if __name__=='__main__':
    raise SystemExit(main())
