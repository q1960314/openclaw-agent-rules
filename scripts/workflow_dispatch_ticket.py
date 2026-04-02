#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 queue/pending 中自动派发 ticket 到对应 OpenClaw agent。

增强版：
1. 派发前做 agent 健康检查，过载/aborted 不再硬派发
2. 直接解析 `openclaw agent --json` 的返回 JSON，优先使用 payload.text 作为真实回执
3. 有真实文本回执 -> done；无回执 -> dispatched；预检失败/命令失败 -> failed/block
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
RECOVER_SCRIPT = WORKSPACE_ROOT / "scripts" / "workflow_agent_recover.py"

QUEUE_ROOT = Path("/home/admin/.openclaw/workspace/master/reports/workflow/queue")
PENDING_DIR = QUEUE_ROOT / "pending"
DISPATCHED_DIR = QUEUE_ROOT / "dispatched"
DONE_DIR = QUEUE_ROOT / "done"
FAILED_DIR = QUEUE_ROOT / "failed"
CATEGORY_AGENT_MAP = {
    "strategy_review": "strategy-expert",
    "weekly_optimization": "strategy-expert",
    "data_quality": "data-collector",
    "monitoring": "knowledge-steward",
}
for d in [PENDING_DIR, DISPATCHED_DIR, DONE_DIR, FAILED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def normalize_agent_id(agent_id: str) -> str:
    if agent_id == "strategy-research":
        return "strategy-expert"
    if agent_id == "doc-knowledge-manager":
        return "knowledge-steward"
    return agent_id


def build_message(payload: Dict) -> str:
    ticket = payload["ticket"]
    lines = [
        f"【自动工单】{ticket['ticket_id']}",
        f"优先级：{ticket['priority']}",
        f"标题：{ticket['title']}",
        f"原因：{ticket['reason']}",
        f"建议下一步：{ticket['suggested_next_step']}",
        f"来源循环：{payload['cycle_id']} ({payload['cycle_type']})",
        f"循环目录：{payload['source_cycle_dir']}",
        "",
        "请基于上述工单和 cycle 产物，给出简洁结构化回复：",
        "1. 你对当前结果的判断",
        "2. 是否需要下一步动作",
        "3. 如需要，给出最小可执行建议",
        "4. 标注风险与验收要点",
        "",
        "注意：不要修改实盘参数，不要做交易动作。",
    ]
    return "\n".join(lines)


def agent_session_store(agent_id: str) -> Path:
    return Path(f"/home/admin/.openclaw/agents/{agent_id}/sessions/sessions.json")


def get_agent_health(agent_id: str) -> Dict:
    p = agent_session_store(agent_id)
    if not p.exists():
        return {}
    obj = load_json(p)
    key = f"agent:{agent_id}:main"
    return obj.get(key, {})


def health_gate(agent_id: str) -> Optional[Dict]:
    health = get_agent_health(agent_id)
    if not health:
        return None
    ctx = health.get("contextTokens") or 0
    total = health.get("totalTokens") or 0
    aborted = bool(health.get("abortedLastRun"))
    overloaded = bool(ctx and total and total / ctx >= 0.80)
    if aborted or overloaded:
        return {
            "reason": "agent_aborted_or_overloaded",
            "abortedLastRun": aborted,
            "contextTokens": ctx,
            "totalTokens": total,
            "sessionId": health.get("sessionId"),
        }
    return None


def recover_agent(agent_id: str) -> Dict:
    cmd = [
        "/home/admin/miniconda3/envs/vnpy_env/bin/python",
        str(RECOVER_SCRIPT),
        "--agent-id", agent_id,
        "--force",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    parsed = extract_json_object(proc.stdout) if proc.stdout else None
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-1000:],
        "parsed": parsed,
    }


def extract_json_object(text: str) -> Optional[Dict]:
    text = text.strip()
    if not text:
        return None
    for start in range(len(text)):
        if text[start] != "{":
            continue
        for end in range(len(text), start, -1):
            if text[end - 1] != "}":
                continue
            try:
                return json.loads(text[start:end])
            except Exception:
                continue
    return None


def extract_reply(parsed: Optional[Dict]) -> Optional[str]:
    if not parsed:
        return None
    result = parsed.get("result", {})
    payloads = result.get("payloads", []) or []
    texts = []
    for item in payloads:
        if isinstance(item, dict) and item.get("text"):
            texts.append(item.get("text"))
    joined = "\n".join([t for t in texts if t]).strip()
    return joined or None


def dispatch_one(path: Path, timeout: int = 240) -> Dict:
    payload = load_json(path)
    ticket = payload["ticket"]
    agent_id = normalize_agent_id(ticket.get("dispatch_agent_id") or CATEGORY_AGENT_MAP.get(ticket.get("category")) or ticket.get("owner"))
    if not agent_id:
        raise RuntimeError("ticket 缺少 dispatch_agent_id/owner")
    if ticket.get("approval_required"):
        return {
            "ticket_id": ticket["ticket_id"],
            "status": "blocked",
            "reason": "approval_required",
            "agent_id": agent_id,
        }

    recovery = None
    gate = health_gate(agent_id)
    if gate:
        recovery = recover_agent(agent_id)
        gate_after = health_gate(agent_id)
        if gate_after:
            return {
                "ticket_id": ticket["ticket_id"],
                "status": "failed",
                "reason": gate_after["reason"],
                "agent_id": agent_id,
                "health": gate_after,
                "recovery": recovery,
            }

    message = build_message(payload)
    cmd = [
        "/home/admin/.local/share/pnpm/openclaw", "agent",
        "--agent", agent_id,
        "--message", message,
        "--timeout", str(timeout),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)

    parsed = extract_json_object(proc.stdout)
    reply_text = extract_reply(parsed)
    if proc.returncode != 0:
        status = "failed"
    elif reply_text:
        status = "done"
    else:
        status = "dispatched"

    return {
        "ticket_id": ticket["ticket_id"],
        "status": status,
        "agent_id": agent_id,
        "returncode": proc.returncode,
        "assistant_text": reply_text,
        "parsed_json": bool(parsed),
        "summary": parsed.get("summary") if isinstance(parsed, dict) else None,
        "recovery": recovery,
        "stderr": proc.stderr[-2000:],
        "stdout_tail": proc.stdout[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-dir", required=False)
    parser.add_argument("--stage-id", default="dispatch_ticket")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    pending = sorted(PENDING_DIR.glob("*.json"))[: max(1, args.limit)]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dispatched: List[Dict] = []
    blocked: List[Dict] = []
    done: List[Dict] = []
    failed: List[Dict] = []

    for p in pending:
        payload = load_json(p)
        try:
            result = dispatch_one(p, timeout=args.timeout)
            payload["updated_at"] = now
            payload["dispatch_result"] = result
            if result["status"] == "blocked":
                payload["queue_status"] = "blocked"
                out = FAILED_DIR / p.name
                write_json(out, payload)
                p.unlink()
                blocked.append(result)
            elif result["status"] == "done":
                payload["queue_status"] = "done"
                out = DONE_DIR / p.name
                write_json(out, payload)
                p.unlink()
                done.append(result)
            elif result["status"] == "dispatched":
                payload["queue_status"] = "dispatched"
                out = DISPATCHED_DIR / p.name
                write_json(out, payload)
                p.unlink()
                dispatched.append(result)
            else:
                payload["queue_status"] = "failed"
                out = FAILED_DIR / p.name
                write_json(out, payload)
                p.unlink()
                failed.append(result)
        except Exception as e:
            failed.append({"ticket_id": load_json(p)["ticket"]["ticket_id"], "status": "failed", "error": str(e)})

    result = {
        "stage": args.stage_id,
        "generated_at": now,
        "pending_scanned": len(pending),
        "done": done,
        "dispatched": dispatched,
        "blocked": blocked,
        "failed": failed,
    }

    if args.cycle_dir:
        cycle_dir = Path(args.cycle_dir)
        artifact = cycle_dir / "artifacts" / args.stage_id / "dispatch_result.json"
        write_json(artifact, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
