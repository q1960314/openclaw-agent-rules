#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker heartbeat + stale task monitor + dashboard."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from audit_manager import AuditManager
from decision_engine import governance_action_for_item, governance_recommendations
from evaluation_runtime import quality_snapshot
from formalization_runtime import load_formalization_snapshot
from recovery_runtime import classify_recovery_level
from release_closure_runtime import load_release_closure_snapshot
from status_manager import StatusManager
from task_queue import TaskQueue

ACTIVE_STATUSES = {'claimed', 'running', 'artifact_ready', 'under_review'}


class HeartbeatMonitor:
    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.heartbeat_file = self.task_dir / 'heartbeat.json'
        self.claim_file = self.task_dir / 'claim.json'

    def _now(self) -> datetime:
        return datetime.now().astimezone()

    def touch(self, actor: str, stage: str, status: str | None = None) -> dict[str, Any]:
        payload = {
            'task_id': self.task_dir.name,
            'actor': actor,
            'stage': stage,
            'status': status,
            'ts': self._now().isoformat(),
        }
        self.heartbeat_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return payload

    def load(self) -> dict[str, Any]:
        if not self.heartbeat_file.exists():
            return {}
        return json.loads(self.heartbeat_file.read_text(encoding='utf-8'))

    def load_claim(self) -> dict[str, Any]:
        if not self.claim_file.exists():
            return {}
        return json.loads(self.claim_file.read_text(encoding='utf-8'))

    def is_stale(self, max_age_minutes: int = 30) -> tuple[bool, str]:
        status = StatusManager(self.task_dir).load().get('status')
        if status not in ACTIVE_STATUSES:
            return False, f'status={status}'

        claim = self.load_claim()
        lease_until = claim.get('lease_until')
        if lease_until:
            try:
                lease_dt = datetime.fromisoformat(lease_until)
                if self._now() > lease_dt:
                    return True, f'lease expired at {lease_until}'
            except Exception:
                pass

        hb = self.load()
        ts = hb.get('ts')
        if not ts:
            return True, 'missing heartbeat timestamp'
        try:
            hb_dt = datetime.fromisoformat(ts)
        except Exception:
            return True, f'invalid heartbeat ts: {ts}'
        if self._now() - hb_dt > timedelta(minutes=max_age_minutes):
            return True, f'heartbeat stale since {ts}'
        return False, 'healthy'

    def mark_stale(self, reason: str, actor: str = 'heartbeat-monitor') -> dict[str, Any]:
        queue = TaskQueue(self.task_dir.parent)
        try:
            queue.release_claim(self.task_dir, actor=actor, reason=f'stale_task: {reason}')
        except Exception:
            pass
        payload = StatusManager(self.task_dir).set_failed(f'stale_task: {reason}', failed_by=actor)
        AuditManager(self.task_dir).append('stale_marked', actor, reason=reason)
        self.touch(actor, 'stale_marked', status='failed')
        return payload


def scan_jobs(jobs_root: str | Path, max_age_minutes: int = 30) -> list[dict[str, Any]]:
    jobs_root = Path(jobs_root)
    results: list[dict[str, Any]] = []
    queue = TaskQueue(jobs_root)
    for task_dir in sorted(jobs_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith('_'):
            continue
        mon = HeartbeatMonitor(task_dir)
        stale, heartbeat_reason = mon.is_stale(max_age_minutes=max_age_minutes)
        task = queue.load_task(task_dir.name) or {}
        metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
        status_payload = StatusManager(task_dir).load()
        status_reason = status_payload.get('blocked_reason') or status_payload.get('review_reason') or ''
        item = {
            'task_id': task_dir.name,
            'role': task.get('role'),
            'status': status_payload.get('status'),
            'stale': stale,
            'reason': heartbeat_reason if stale else (status_reason or heartbeat_reason),
            'heartbeat_reason': heartbeat_reason,
            'status_reason': status_reason,
            'auto_retry_allowed': bool(metadata.get('auto_retry_allowed', False)),
            'manual_review_required': bool(metadata.get('manual_review_required', False)),
        }
        item.update(classify_recovery_level(item))
        item.update(quality_snapshot(task_dir))
        item.update(load_formalization_snapshot(task_dir))
        item.update(load_release_closure_snapshot(task_dir))
        results.append(item)
    return results


def heal_jobs(jobs_root: str | Path, max_age_minutes: int = 30, auto_retry: bool = False, retry_requested_by: str = 'heartbeat-monitor') -> list[dict[str, Any]]:
    jobs_root = Path(jobs_root)
    results = []
    queue = TaskQueue(jobs_root)
    for item in scan_jobs(jobs_root, max_age_minutes=max_age_minutes):
        if item['stale']:
            mon = HeartbeatMonitor(jobs_root / item['task_id'])
            mon.mark_stale(item['reason'])
            result = {
                'task_id': item['task_id'],
                'healed': True,
                'reason': item['reason'],
                'auto_retry_allowed': item.get('auto_retry_allowed', False),
            }
            recommendation = governance_action_for_item(item)
            if recommendation:
                result['recommended_action'] = recommendation['recommended_action']
                result['rationale'] = recommendation['rationale']
            result['recoverability'] = item.get('recoverability')
            if auto_retry and recommendation and recommendation.get('recommended_action') == 'auto_retry':
                retry_dir = queue.create_retry_task(item['task_id'], requested_by=retry_requested_by, reason=f'auto_retry_after_stale: {item["reason"]}')
                result['retry_task_id'] = retry_dir.name
            results.append(result)
    return results


def dashboard(jobs_root: str | Path, max_age_minutes: int = 30) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    counts: dict[str, int] = {}
    recoverability_counts: dict[str, int] = {}
    quality_grade_counts: dict[str, int] = {}
    formalization_state_counts: dict[str, int] = {}
    human_approval_state_counts: dict[str, int] = {}
    approval_recompute_state_counts: dict[str, int] = {}
    release_execution_state_counts: dict[str, int] = {}
    official_release_pipeline_state_counts: dict[str, int] = {}
    closure_counts = {'approval_required': 0, 'approved': 0, 'approval_checklist_ready': 0, 'approval_decision_recorded': 0, 'approval_transition_visible': 0, 'human_approval_input_slot_visible': 0, 'human_approval_input_slot_ready': 0, 'human_approval_input_recorded': 0, 'human_approval_result_recorded': 0, 'human_approval_result_visible': 0, 'approval_recompute_visible': 0, 'release_action_allowed': 0, 'release_preflight_ready': 0, 'pre_release_ready': 0, 'closure_consistency_ready': 0, 'official_release_rehearsal_ready': 0, 'release_execution_blocked': 0, 'post_approval_transition_visible': 0, 'post_approval_execution_unblocked': 0, 'official_release_state_visible': 0, 'official_release_pipeline_visible': 0, 'official_release_pipeline_executable': 0, 'release_artifact_binding_visible': 0, 'release_artifact_binding_ready': 0, 'rollback_supported': 0, 'executor_contract_available': 0, 'dry_run_available': 0, 'execution_receipt_protocol_available': 0, 'handoff_packet_available': 0, 'operator_execution_request_available': 0, 'receipt_correlation_ready': 0, 'executor_readiness_review_visible': 0, 'executor_adapter_available_count': 0, 'executor_capability_registry_available': 0, 'invocation_policy_available': 0, 'environment_guard_ok_count': 0, 'environment_guard_unmet_count': 0, 'handoff_boundary_ready': 0, 'release_execution_requested': 0, 'rollback_execution_requested': 0, 'release_execution_receipt_recorded': 0, 'rollback_execution_receipt_recorded': 0, 'closure_visible': 0}
    scored_items = 0
    score_total = 0
    stale_count = 0
    items = []
    for item in scan_jobs(jobs_root, max_age_minutes=max_age_minutes):
        counts[item['status']] = counts.get(item['status'], 0) + 1
        recoverability = item.get('recoverability', 'unknown')
        recoverability_counts[recoverability] = recoverability_counts.get(recoverability, 0) + 1
        grade = item.get('quality_grade')
        score = item.get('quality_score')
        if grade:
            quality_grade_counts[grade] = quality_grade_counts.get(grade, 0) + 1
        if isinstance(score, int):
            scored_items += 1
            score_total += score
        formalization_state = item.get('formalization_state')
        if formalization_state:
            formalization_state_counts[formalization_state] = formalization_state_counts.get(formalization_state, 0) + 1
        human_state = item.get('human_approval_state')
        if human_state:
            human_approval_state_counts[human_state] = human_approval_state_counts.get(human_state, 0) + 1
        recompute_state = item.get('approval_recompute_state')
        if recompute_state:
            approval_recompute_state_counts[recompute_state] = approval_recompute_state_counts.get(recompute_state, 0) + 1
        execution_state = item.get('release_execution_state')
        if execution_state:
            release_execution_state_counts[execution_state] = release_execution_state_counts.get(execution_state, 0) + 1
        pipeline_state = item.get('official_release_pipeline_state')
        if pipeline_state:
            official_release_pipeline_state_counts[pipeline_state] = official_release_pipeline_state_counts.get(pipeline_state, 0) + 1
        for key in closure_counts:
            if item.get(key) is True:
                closure_counts[key] += 1
        if item['stale']:
            stale_count += 1
        items.append(item)
    gov = governance_recommendations(items)
    return {
        'generated_at': datetime.now().astimezone().isoformat(),
        'job_count': len(items),
        'stale_count': stale_count,
        'status_counts': counts,
        'recoverability_counts': recoverability_counts,
        'quality_grade_counts': quality_grade_counts,
        'quality_average_score': round(score_total / scored_items, 2) if scored_items else None,
        'formalization_state_counts': formalization_state_counts,
        'human_approval_state_counts': human_approval_state_counts,
        'approval_recompute_state_counts': approval_recompute_state_counts,
        'release_execution_state_counts': release_execution_state_counts,
        'official_release_pipeline_state_counts': official_release_pipeline_state_counts,
        'closure_counts': closure_counts,
        'items': items,
        'governance': {
            'generated_at': datetime.now().astimezone().isoformat(),
            **gov,
        },
    }


def write_dashboard_markdown(payload: dict[str, Any], output_path: str | Path) -> Path:
    status_map = {
        'passed': '已通过', 'failed': '失败', 'rejected': '已拒绝', 'queued': '排队中',
        'claimed': '已领取', 'running': '运行中', 'artifact_ready': '产物已就绪',
        'under_review': '审核中', 'manual_review_required': '需人工复核', 'completed': '已完成'
    }
    recoverability_map = {
        'none': '无需恢复', 'manual_intervention': '需人工处理', 'auto_retry': '自动重试',
        'retryable': '可重试', 'unknown': '待判断'
    }
    formalization_map = {
        'release_ready_candidate': '可发布候选结果', 'blocked_candidate': '受阻候选结果', 'manual_review_gate': '人工复核门禁'
    }
    approval_map = {'awaiting': '等待审批', 'approved': '已批准', 'rejected': '已拒绝'}
    recompute_map = {'awaiting_real_human_decision': '等待真实人工结论'}
    execution_map = {'blocked_pending_human_approval': '因等待人工审批而阻塞'}
    pipeline_map = {
        'awaiting_human_approval': '等待人工审批', 'candidate_not_ready': '候选结果尚未就绪',
        'approved_but_blocked': '已审批但仍阻塞', 'ready_but_execution_not_implemented': '已就绪但执行路径未实现',
        'rejected': '已拒绝'
    }
    blocker_map = {
        'human_approval_not_recorded': '人工审批结果未记录', 'official_release_rehearsal_not_ready': '正式发布预演未就绪',
        'pre_release_gate_not_ready': '发布前置门禁未就绪', 'release_artifact_binding_not_ready': '发布产物绑定未就绪',
        'rollback_not_ready': '回滚准备未就绪'
    }

    def translate(key: Any, mapping: dict[str, str]) -> Any:
        return mapping.get(str(key), key)

    def render_map(data: dict[str, Any], mapping: dict[str, str] | None = None) -> str:
        if not data:
            return '无'
        return '；'.join(f"{translate(k, mapping or {})}={v}" for k, v in data.items())

    def render_list(values: Any, mapping: dict[str, str] | None = None) -> str:
        if not values:
            return '无'
        if isinstance(values, list):
            return '；'.join(str(translate(v, mapping or {})) for v in values)
        return str(values)

    output_path = Path(output_path)
    lines = [
        '# 健康监控看板',
        '',
        f"- 生成时间: {payload['generated_at']}",
        f"- 任务总数: {payload['job_count']}",
        f"- 陈旧任务数: {payload['stale_count']}",
        '',
        '## 状态分布',
    ]
    for key, value in sorted(payload['status_counts'].items()):
        lines.append(f"- {translate(key, status_map)}: {value}")
    lines.extend(['', '## 可恢复性分布'])
    for key, value in sorted(payload.get('recoverability_counts', {}).items()):
        lines.append(f'- {translate(key, recoverability_map)}: {value}')
    lines.extend(['', '## 质量摘要'])
    lines.append(f"- 平均质量分: {payload.get('quality_average_score')}")
    for key, value in sorted(payload.get('quality_grade_counts', {}).items()):
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## 正式收口状态'])
    for key, value in sorted(payload.get('formalization_state_counts', {}).items()):
        lines.append(f'- {translate(key, formalization_map)}: {value}')
    lines.extend(['', '## 人工审批状态'])
    for key, value in sorted(payload.get('human_approval_state_counts', {}).items()):
        lines.append(f'- {translate(key, approval_map)}: {value}')
    lines.extend(['', '## 审批重算状态'])
    for key, value in sorted(payload.get('approval_recompute_state_counts', {}).items()):
        lines.append(f'- {translate(key, recompute_map)}: {value}')
    lines.extend(['', '## 发布执行状态'])
    for key, value in sorted(payload.get('release_execution_state_counts', {}).items()):
        lines.append(f'- {translate(key, execution_map)}: {value}')
    lines.extend(['', '## 正式发布管线状态'])
    for key, value in sorted(payload.get('official_release_pipeline_state_counts', {}).items()):
        lines.append(f'- {translate(key, pipeline_map)}: {value}')
    lines.extend(['', '## 收口就绪统计'])
    for key, value in sorted(payload.get('closure_counts', {}).items()):
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## 任务明细'])
    for item in payload['items']:
        lines.append(
            f"- 任务={item['task_id']} | 角色={item['role']} | 状态={translate(item['status'], status_map)} | 陈旧={'是' if item['stale'] else '否'} | 质量={item.get('quality_score')}/{item.get('quality_grade')} | 正式收口={translate(item.get('formalization_state'), formalization_map)} | 人工审批={translate(item.get('human_approval_state'), approval_map)} | 审批重算={translate(item.get('approval_recompute_state'), recompute_map)} | 发布执行={translate(item.get('release_execution_state'), execution_map)} | 正式发布管线={translate(item.get('official_release_pipeline_state'), pipeline_map)} | 管线阻塞={render_list(item.get('official_release_pipeline_blockers'), blocker_map)} | 发布阻塞={render_list(item.get('release_execution_block_reasons'), blocker_map)} | 需要审批={'是' if item.get('approval_required') else '否'} | 允许发布动作={'是' if item.get('release_action_allowed') else '否'} | 支持回滚={'是' if item.get('rollback_supported') else '否'} | 可恢复性={translate(item.get('recoverability'), recoverability_map)} | 建议动作={item.get('recommended_action')} | 允许自动重试={'是' if item['auto_retry_allowed'] else '否'} | 原因={item['reason']}"
        )
    lines.extend(['', '## 治理建议'])
    gov = payload.get('governance', {})
    for action in gov.get('actions', []):
        lines.append(f"- 任务={action['task_id']} | 动作={action['recommended_action']} | 理由={action['rationale']} | 原因={action['reason']}")
    if not gov.get('actions'):
        lines.append('- 当前无需治理动作')
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['scan', 'heal', 'dashboard'])
    parser.add_argument('--jobs-root', default=str(Path(__file__).resolve().parents[2] / 'traces' / 'jobs'))
    parser.add_argument('--max-age-minutes', type=int, default=30)
    parser.add_argument('--auto-retry', action='store_true')
    parser.add_argument('--retry-requested-by', default='heartbeat-monitor')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    if args.action == 'scan':
        print(json.dumps(scan_jobs(args.jobs_root, args.max_age_minutes), ensure_ascii=False, indent=2))
    elif args.action == 'heal':
        print(json.dumps(heal_jobs(args.jobs_root, args.max_age_minutes, auto_retry=args.auto_retry, retry_requested_by=args.retry_requested_by), ensure_ascii=False, indent=2))
    else:
        payload = dashboard(args.jobs_root, args.max_age_minutes)
        if args.output:
            write_dashboard_markdown(payload, args.output)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
