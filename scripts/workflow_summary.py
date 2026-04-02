#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总一个循环目录下的任务结果。"""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="summarize")
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    meta_path = cycle_dir / "meta.json"
    meta = load_json(meta_path)

    task_files = sorted((cycle_dir / "tasks").glob("*.json"))
    tasks = [load_json(p) for p in task_files]
    completed = [t for t in tasks if t.get("status") == "completed"]
    failed = [t for t in tasks if t.get("status") == "failed"]
    summarize_task = next((t for t in tasks if t.get("stage") == args.stage_id), None)
    completed_count = len(completed)
    if summarize_task and summarize_task.get("status") != "failed":
        completed_count = max(completed_count, len(tasks))

    data_check = cycle_dir / "artifacts" / "data_validate" / "data_check.json"
    smoke = cycle_dir / "artifacts" / "smoke_backtest" / "smoke_backtest.json"
    weekly = cycle_dir / "artifacts" / "health_check" / "weekly_health.json"
    followup = cycle_dir / "artifacts" / "followup_ticket" / "followup_tickets.json"
    queue_result = cycle_dir / "artifacts" / "queue_ticket" / "queue_result.json"
    dispatch_result = cycle_dir / "artifacts" / "dispatch_ticket" / "dispatch_result.json"
    collect_result = cycle_dir / "artifacts" / "collect_reply" / "collect_result.json"
    select_target = cycle_dir / 'artifacts' / 'select_target' / 'selected_target.json'
    opencode_result = cycle_dir / 'artifacts' / 'opencode_plan' / 'opencode_result.json'
    data_snapshot = cycle_dir / 'artifacts' / 'data_snapshot' / 'data_snapshot.json'
    data_quality_score = cycle_dir / 'artifacts' / 'data_quality_score' / 'data_quality_score.json'

    summary = {
        "cycle_id": meta.get("cycle_id"),
        "cycle_type": meta.get("cycle_type"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed" if not failed else "failed",
        "task_total": len(tasks),
        "task_completed": completed_count,
        "task_failed": len(failed),
        "artifacts": {
            "data_check": str(data_check) if data_check.exists() else None,
            "smoke_backtest": str(smoke) if smoke.exists() else None,
            "weekly_health": str(weekly) if weekly.exists() else None,
            "followup_ticket": str(followup) if followup.exists() else None,
            "queue_result": str(queue_result) if queue_result.exists() else None,
            "dispatch_result": str(dispatch_result) if dispatch_result.exists() else None,
            "collect_result": str(collect_result) if collect_result.exists() else None,
            "select_target": str(select_target) if select_target.exists() else None,
            "opencode_result": str(opencode_result) if opencode_result.exists() else None,
            "data_snapshot": str(data_snapshot) if data_snapshot.exists() else None,
            "data_quality_score": str(data_quality_score) if data_quality_score.exists() else None,
        },
    }

    if data_check.exists():
        data_payload = load_json(data_check)
        summary["data_check"] = data_payload.get("summary", {})
    if smoke.exists():
        smoke_payload = load_json(smoke)
        summary["smoke_backtest"] = smoke_payload.get("metrics", {})
        summary["smoke_strategy"] = smoke_payload.get("strategy_type")
        summary["smoke_range"] = [smoke_payload.get("start_date"), smoke_payload.get("end_date")]
    if weekly.exists():
        weekly_payload = load_json(weekly)
        summary["weekly_health"] = weekly_payload.get("health_report", {})
        summary["weekly_strategy"] = weekly_payload.get("strategy_type")
    if followup.exists():
        followup_payload = load_json(followup)
        summary["followup_ticket_count"] = followup_payload.get("ticket_count", 0)
        summary["followup_tickets"] = followup_payload.get("tickets", [])
    if data_snapshot.exists():
        ds_payload = load_json(data_snapshot)
        summary['data_snapshot'] = {
            'stock_dir_count': ds_payload.get('stock_dir_count'),
            'sample_size': ds_payload.get('sample_size'),
        }
    if data_quality_score.exists():
        dqs_payload = load_json(data_quality_score)
        summary['data_quality_score'] = dqs_payload
    if select_target.exists():
        select_payload = load_json(select_target)
        summary['optimization_selected'] = select_payload.get('selected')
        summary['optimization_ticket'] = select_payload.get('selected_ticket')
    if queue_result.exists():
        queue_payload = load_json(queue_result)
        summary["queue_enqueued_count"] = len(queue_payload.get("enqueued", []))
        summary["queue_skipped_count"] = len(queue_payload.get("skipped", []))
    dispatch_payload = {}
    if dispatch_result.exists():
        dispatch_payload = load_json(dispatch_result)
        summary["dispatch_done_count"] = len(dispatch_payload.get("done", []))
        summary["dispatch_dispatched_count"] = len(dispatch_payload.get("dispatched", []))
        summary["dispatch_blocked_count"] = len(dispatch_payload.get("blocked", []))
        summary["dispatch_failed_count"] = len(dispatch_payload.get("failed", []))
        summary["dispatch_done_items"] = dispatch_payload.get("done", [])
        summary["dispatch_failed_items"] = dispatch_payload.get("failed", [])
        summary["dispatch_blocked_items"] = dispatch_payload.get("blocked", [])
    if collect_result.exists():
        collect_payload = load_json(collect_result)
        summary["collect_done_count"] = len(collect_payload.get("done", []))
        summary["collect_failed_count"] = len(collect_payload.get("failed", []))
        summary["collect_pending_followup_count"] = len(collect_payload.get("pending_followup", []))
    if opencode_result.exists():
        op_payload = load_json(opencode_result)
        summary['opencode_mode'] = op_payload.get('mode')
        summary['opencode_model'] = op_payload.get('model')
        summary['opencode_text'] = op_payload.get('text')
        summary['opencode_returncode'] = op_payload.get('returncode')

    recommended_actions = []
    for ticket in summary.get("followup_tickets", []):
        category = ticket.get("category")
        if ticket.get("approval_required"):
            recommended_actions.append({
                "type": "approval_required",
                "ticket_id": ticket.get("ticket_id"),
                "owner": ticket.get("owner"),
                "action": ticket.get("title"),
            })
        elif category == "strategy_review":
            recommended_actions.append({
                "type": "strategy_review",
                "ticket_id": ticket.get("ticket_id"),
                "owner": ticket.get("owner"),
                "action": "根据策略复核结果，决定是否启动周度优化流程",
            })
        elif category == "monitoring":
            recommended_actions.append({
                "type": "archive",
                "ticket_id": ticket.get("ticket_id"),
                "owner": ticket.get("owner"),
                "action": "保持归档与监控，无需立即优化",
            })
        elif category == "data_quality":
            recommended_actions.append({
                "type": "data_fix",
                "ticket_id": ticket.get("ticket_id"),
                "owner": ticket.get("owner"),
                "action": "优先修复数据质量问题，再继续后续流程",
            })
    summary["recommended_actions"] = recommended_actions

    meta["summary"] = summary
    write_json(meta_path, meta)

    report_lines: List[str] = []
    report_lines.append(f"# 循环汇总报告\n")
    report_lines.append(f"- 循环 ID: {summary['cycle_id']}")
    report_lines.append(f"- 循环类型: {summary['cycle_type']}")
    report_lines.append(f"- 生成时间: {summary['generated_at']}")
    report_lines.append(f"- 状态: {summary['status']}")
    report_lines.append(f"- 任务完成: {summary['task_completed']}/{summary['task_total']}")
    report_lines.append("")

    if summary.get("data_check"):
        dc = summary["data_check"]
        report_lines.append("## 数据校验")
        report_lines.append(f"- 最新样本交易日: {dc.get('latest_sample_trade_date')}")
        report_lines.append(f"- limit_list 最新日: {dc.get('limit_list_latest_trade_date')}")
        report_lines.append(f"- 错误数: {dc.get('errors')}")
        report_lines.append(f"- 警告数: {dc.get('warnings')}")
        report_lines.append("")
    if summary.get('data_snapshot'):
        ds = summary['data_snapshot']
        report_lines.append('## 数据快照')
        report_lines.append(f"- 股票目录数: {ds.get('stock_dir_count')}")
        report_lines.append(f"- 抽样数: {ds.get('sample_size')}")
        report_lines.append('')
    if summary.get('data_quality_score'):
        dqs = summary['data_quality_score']
        report_lines.append('## 数据质量评分')
        report_lines.append(f"- score: {dqs.get('score')}")
        report_lines.append(f"- grade: {dqs.get('grade')}")
        report_lines.append(f"- status: {dqs.get('status')}")
        report_lines.append('')

    if summary.get("smoke_backtest"):
        sm = summary["smoke_backtest"]
        report_lines.append("## 冒烟回测")
        report_lines.append(f"- 策略: {summary.get('smoke_strategy')}")
        report_lines.append(f"- 区间: {summary.get('smoke_range')}")
        report_lines.append(f"- 总收益: {sm.get('total_return')}")
        report_lines.append(f"- 年化收益: {sm.get('annual_return')}")
        report_lines.append(f"- 最大回撤: {sm.get('max_drawdown')}")
        report_lines.append(f"- 夏普比率: {sm.get('sharpe_ratio')}")
        report_lines.append(f"- 胜率: {sm.get('win_rate')}")
        report_lines.append(f"- 交易次数: {sm.get('total_trades')}")
        report_lines.append("")

    if summary.get("weekly_health"):
        wh = summary["weekly_health"]
        report_lines.append("## 周度健康检查")
        report_lines.append(f"- 策略: {summary.get('weekly_strategy')}")
        report_lines.append(f"- 总体状态: {wh.get('overall_status')}")
        report_lines.append(f"- 问题数: {len(wh.get('issues', []))}")
        for issue in wh.get("issues", []):
            report_lines.append(f"  - {issue}")
        report_lines.append("")
    if summary.get('optimization_selected'):
        report_lines.append('## 优化支线目标')
        ticket = summary.get('optimization_ticket') or {}
        report_lines.append(f"- ticket_id: {ticket.get('ticket_id')}")
        report_lines.append(f"- category: {ticket.get('category')}")
        report_lines.append(f"- owner: {ticket.get('owner')}")
        report_lines.append(f"- title: {ticket.get('title')}")
        report_lines.append(f"- reason: {ticket.get('reason')}")
        report_lines.append('')
    if summary.get('opencode_text'):
        report_lines.append('## OpenCode 计划结果')
        report_lines.append(f"- mode: {summary.get('opencode_mode')}")
        report_lines.append(f"- model: {summary.get('opencode_model')}")
        report_lines.append(summary.get('opencode_text'))
        report_lines.append('')

    if summary.get("followup_tickets"):
        report_lines.append("## 后续工单")
        for ticket in summary.get("followup_tickets", []):
            report_lines.append(
                f"- [{ticket.get('priority')}] {ticket.get('owner')} | {ticket.get('title')} | approval_required={ticket.get('approval_required')}"
            )
        report_lines.append("")

    if summary.get("queue_enqueued_count") is not None or summary.get("dispatch_dispatched_count") is not None:
        report_lines.append("## 队列与派发")
        report_lines.append(f"- 入队: {summary.get('queue_enqueued_count', 0)} | 跳过: {summary.get('queue_skipped_count', 0)}")
        report_lines.append(f"- 直接完成: {summary.get('dispatch_done_count', 0)} | 已派发待收: {summary.get('dispatch_dispatched_count', 0)} | 阻塞: {summary.get('dispatch_blocked_count', 0)} | 派发失败: {summary.get('dispatch_failed_count', 0)}")
        if summary.get('collect_done_count') is not None:
            report_lines.append(f"- 回执采集: done={summary.get('collect_done_count', 0)} failed={summary.get('collect_failed_count', 0)} pending={summary.get('collect_pending_followup_count', 0)}")
        report_lines.append("")

    if summary.get('dispatch_done_items'):
        report_lines.append("## 子智能体详细回执")
        for item in summary.get('dispatch_done_items', []):
            report_lines.append(f"### {item.get('ticket_id')} | {item.get('agent_id')}")
            reply = (item.get('assistant_text') or '').strip()
            if reply:
                report_lines.append(reply)
            else:
                report_lines.append("- 无正文回执")
            report_lines.append("")

    if summary.get('dispatch_failed_items') or summary.get('dispatch_blocked_items'):
        report_lines.append("## 派发异常")
        for item in summary.get('dispatch_failed_items', []):
            report_lines.append(f"- FAILED | {item.get('ticket_id')} | {item.get('agent_id')} | {item.get('reason', item.get('error', 'unknown'))}")
        for item in summary.get('dispatch_blocked_items', []):
            report_lines.append(f"- BLOCKED | {item.get('ticket_id')} | {item.get('agent_id')} | {item.get('reason', 'blocked')}")
        report_lines.append("")

    if summary.get('recommended_actions'):
        report_lines.append("## 建议的下一步动作")
        for item in summary.get('recommended_actions', []):
            report_lines.append(f"- [{item.get('type')}] {item.get('owner')} | {item.get('action')}")
        report_lines.append("")

    if failed:
        report_lines.append("## 失败任务")
        for task in failed:
            report_lines.append(f"- {task.get('stage')} | exit_code={task.get('exit_code')} | log={task.get('log_file')}")
        report_lines.append("")

    report_path = cycle_dir / "reports" / "cycle_summary.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    write_json(cycle_dir / "reports" / "cycle_summary.json", summary)

    user_brief_lines = [
        f"循环 {summary['cycle_id']} 已完成",
        f"类型: {summary['cycle_type']}",
        f"状态: {summary['status']}",
    ]
    if summary.get("data_check"):
        dc = summary["data_check"]
        user_brief_lines.append(
            f"数据校验: latest={dc.get('latest_sample_trade_date')} errors={dc.get('errors')} warnings={dc.get('warnings')}"
        )
    if summary.get('data_quality_score'):
        dqs = summary['data_quality_score']
        user_brief_lines.append(
            f"数据质量评分: score={dqs.get('score')} grade={dqs.get('grade')} status={dqs.get('status')}"
        )
    if summary.get("smoke_backtest"):
        sm = summary["smoke_backtest"]
        user_brief_lines.append(
            f"冒烟回测: return={sm.get('total_return'):.4f} sharpe={sm.get('sharpe_ratio'):.4f} drawdown={sm.get('max_drawdown'):.4f} trades={sm.get('total_trades')}"
        )
    if summary.get("weekly_health"):
        wh = summary["weekly_health"]
        user_brief_lines.append(f"周度健康检查: {wh.get('overall_status')}")
    if summary.get("followup_ticket_count") is not None:
        user_brief_lines.append(f"后续工单数: {summary.get('followup_ticket_count', 0)}")
    if summary.get("dispatch_dispatched_count") is not None or summary.get('dispatch_done_count') is not None:
        user_brief_lines.append(
            f"自动派发: done={summary.get('dispatch_done_count', 0)} dispatched={summary.get('dispatch_dispatched_count', 0)} blocked={summary.get('dispatch_blocked_count', 0)} failed={summary.get('dispatch_failed_count', 0)}"
        )
    if summary.get('collect_done_count') is not None:
        user_brief_lines.append(
            f"回执采集: done={summary.get('collect_done_count', 0)} failed={summary.get('collect_failed_count', 0)} pending={summary.get('collect_pending_followup_count', 0)}"
        )
    if summary.get('recommended_actions'):
        user_brief_lines.append(
            f"下一步动作: {len(summary.get('recommended_actions', []))}项"
        )

    (cycle_dir / "reports" / "user_brief.md").write_text("\n".join(user_brief_lines), encoding="utf-8")
    write_json(cycle_dir / "reports" / "notification_payload.json", {
        "cycle_id": summary["cycle_id"],
        "cycle_type": summary["cycle_type"],
        "status": summary["status"],
        "message": " | ".join(user_brief_lines)
    })

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
