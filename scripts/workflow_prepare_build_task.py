#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='prepare_build_task')
    args = parser.parse_args()
    cycle_dir = Path(args.cycle_dir)
    selected = load_json(cycle_dir / 'artifacts' / 'select_build_candidate' / 'selected_build_candidate.json')
    wt = load_json(cycle_dir / 'artifacts' / 'create_worktree' / 'worktree.json')
    worktree = wt['worktree']
    plan = selected['execution_plan']
    task = selected['execution_task']
    files = [f for f in task.get('files', []) if Path(f).exists()]
    prompt = f'''你现在在一个隔离 worktree 中执行中国A股量化回测/选股系统的 build 候选任务。

工作目录：{worktree}
原始代码仓：/data/agents/master
这是 research/backtest 范围，不是实盘，不允许修改实盘参数。

你必须优先只修改这些文件（如果文件不存在则跳过，不要扩展到无关目录）：
{chr(10).join(['- ' + f for f in files])}

专项 agent 已经完成诊断，execution plan 如下：
{plan.get('text','')[:6000]}

【强约束】
1. 本次不是写计划，必须进行真实代码修改
2. 至少要修改 1 个目标文件，并产生 git diff
3. 不扫描 backup/历史文件
4. 不修改无关目录
5. 不做实盘相关修改
6. 如果你判断当前不应该改代码，也要明确说明“为什么不能改”，但默认目标是做最小可验证改动

【执行要求】
请优先完成一个最小但真实的实现，例如：
- 调整 strategy_core 中和诊断直接相关的阈值/参数接入
- 或调整 backtest_engine / risk_engine 中直接相关的风险参数逻辑
- 或修正 strategy_ensemble 中与市场状态/权重有关的最小逻辑

结束后必须输出：
- 修改了哪些文件
- 做了什么改动
- 需要怎么验证
- 是否建议继续更大范围修改

如果没有实际改动，任务视为不合格。
'''
    payload = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'worktree': worktree,
        'files': files,
        'prompt': prompt,
        'source_execution_cycle': selected.get('source_execution_cycle'),
    }
    out = cycle_dir / 'artifacts' / args.stage_id / 'build_task.json'
    write_json(out, payload)
    (cycle_dir / 'artifacts' / args.stage_id / 'build_task.md').write_text(prompt, encoding='utf-8')
    print(json.dumps({'worktree': worktree, 'file_count': len(files)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
