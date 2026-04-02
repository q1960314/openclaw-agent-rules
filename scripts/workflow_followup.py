#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据循环结果自动生成后续工单。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_daily_followup(cycle_id: str, smoke: Dict, data_check: Dict) -> List[Dict]:
    tickets: List[Dict] = []
    dc = data_check.get("summary", {}) if data_check else {}
    metrics = smoke.get("metrics", {}) if smoke else {}

    if dc.get("errors", 0) > 0:
        tickets.append({
            "ticket_id": f"{cycle_id}::data_repair",
            "category": "data_quality",
            "priority": "P1",
            "owner": "data-collector",
            "dispatch_agent_id": "data-collector",
            "title": "修复每日研究闭环中的数据完整性问题",
            "reason": f"data_check errors={dc.get('errors')} warnings={dc.get('warnings')}",
            "suggested_next_step": "排查缺失 parquet / 日期不一致 / 数据源中断",
            "approval_required": False,
        })

    total_return = metrics.get("total_return")
    sharpe = metrics.get("sharpe_ratio")
    drawdown = metrics.get("max_drawdown")
    if total_return is not None and sharpe is not None and drawdown is not None:
        if total_return < -0.10 or sharpe < -2 or drawdown > 0.15:
            tickets.append({
                "ticket_id": f"{cycle_id}::strategy_review",
                "category": "strategy_review",
                "priority": "P1",
                "owner": "strategy-expert",
                "dispatch_agent_id": "strategy-expert",
                "title": "每日闭环触发策略复核",
                "reason": f"smoke_backtest total_return={total_return:.4f}, sharpe={sharpe:.4f}, max_drawdown={drawdown:.4f}",
                "suggested_next_step": "复核近 60 交易日策略表现，确认是否需要进入周度优化/参数审查",
                "approval_required": False,
            })

    return tickets


def build_weekly_followup(cycle_id: str, weekly: Dict) -> List[Dict]:
    tickets: List[Dict] = []
    health = weekly.get("health_report", {}) if weekly else {}
    status = health.get("overall_status")
    issues = health.get("issues", [])

    if status in {"警告", "危险"}:
        tickets.append({
            "ticket_id": f"{cycle_id}::weekly_optimization",
            "category": "weekly_optimization",
            "priority": "P1" if status == "警告" else "P0",
            "owner": "strategy-expert",
            "dispatch_agent_id": "strategy-expert",
            "title": "周度健康检查触发优化工单",
            "reason": f"health_status={status}; issues={issues}",
            "suggested_next_step": "生成策略优化假设，并进入 coder/OpenCode 隔离改造链",
            "approval_required": True,
        })
    elif status == "健康":
        tickets.append({
            "ticket_id": f"{cycle_id}::weekly_stable",
            "category": "monitoring",
            "priority": "P3",
            "owner": "knowledge-steward",
            "dispatch_agent_id": "knowledge-steward",
            "title": "周度健康检查通过，无需优化，仅做归档",
            "reason": "health_status=健康",
            "suggested_next_step": "沉淀本周稳定性结果，等待下一个周期",
            "approval_required": False,
        })

    return tickets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="followup_ticket")
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    meta = load_json(cycle_dir / "meta.json")
    cycle_type = meta.get("cycle_type")
    cycle_id = meta.get("cycle_id")

    smoke_path = cycle_dir / "artifacts" / "smoke_backtest" / "smoke_backtest.json"
    data_path = cycle_dir / "artifacts" / "data_validate" / "data_check.json"
    weekly_path = cycle_dir / "artifacts" / "health_check" / "weekly_health.json"

    smoke = load_json(smoke_path) if smoke_path.exists() else {}
    data_check = load_json(data_path) if data_path.exists() else {}
    weekly = load_json(weekly_path) if weekly_path.exists() else {}

    if cycle_type == "daily_research":
        tickets = build_daily_followup(cycle_id, smoke, data_check)
    elif cycle_type == "weekly_health":
        tickets = build_weekly_followup(cycle_id, weekly)
    else:
        tickets = []

    payload = {
        "stage": args.stage_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cycle_id": cycle_id,
        "cycle_type": cycle_type,
        "ticket_count": len(tickets),
        "tickets": tickets,
    }

    artifact_dir = cycle_dir / "artifacts" / args.stage_id
    write_json(artifact_dir / "followup_tickets.json", payload)

    md_lines = [f"# Follow-up Tickets", "", f"- cycle_id: {cycle_id}", f"- cycle_type: {cycle_type}", f"- generated_at: {payload['generated_at']}", f"- ticket_count: {len(tickets)}", ""]
    for t in tickets:
        md_lines.extend([
            f"## {t['ticket_id']}",
            f"- owner: {t['owner']}",
            f"- priority: {t['priority']}",
            f"- title: {t['title']}",
            f"- reason: {t['reason']}",
            f"- suggested_next_step: {t['suggested_next_step']}",
            f"- approval_required: {t['approval_required']}",
            "",
        ])
    (artifact_dir / "followup_tickets.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
