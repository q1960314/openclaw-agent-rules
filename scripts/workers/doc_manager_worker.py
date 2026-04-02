#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from worker_base import WorkerBase  # noqa: E402
from artifact_binding_runtime import build_release_artifact_binding  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402
from approval_recompute_runtime import build_approval_recompute_snapshot  # noqa: E402
from human_approval_input_runtime import build_human_approval_input_slot  # noqa: E402
from formalization_runtime import build_formalization_gate  # noqa: E402
from official_release_registry import build_release_readiness, build_rollback_stub  # noqa: E402
from official_release_rehearsal_runtime import build_official_release_rehearsal  # noqa: E402
from closure_consistency_runtime import build_release_closure_consistency  # noqa: E402
from release_closure_runtime import build_approval_checklist, build_approval_decision_placeholder, build_approval_outcome_stub, build_approval_record, build_approval_transition_stub, build_human_approval_result_stub, build_official_release_pipeline_summary, build_official_release_state_placeholder, build_post_approval_guardrail_transition, build_pre_release_gate, build_release_action_stub, build_release_execution_guardrail, build_release_preflight_stub, build_rollback_registry_entry  # noqa: E402


class DocManagerWorker(WorkerBase):
    def __init__(self):
        super().__init__("doc-manager")

    def _load_review(self, task_dir: Path) -> dict:
        review_file = task_dir / "review.json"
        if not review_file.exists():
            return {}
        return json.loads(review_file.read_text(encoding="utf-8"))

    def execute_task(self, task_dir: Path, task: dict) -> None:
        review = self._load_review(task_dir)
        if review.get("decision") != "passed":
            self.fail_task(task_dir, "doc-manager blocked: review decision is not passed")
            return

        artifacts = ArtifactManager(task_dir)
        boundary = self._result_boundary(task_dir)
        formalization_gate = build_formalization_gate(task_dir, boundary=boundary, review=review)
        release_readiness = build_release_readiness(task_dir, boundary=boundary, review=review)
        rollback_stub = build_rollback_stub(task_dir)
        approval_record = build_approval_record(task_dir.name, review=review, boundary=boundary, formalization_gate=formalization_gate)
        approval_checklist = build_approval_checklist(task_dir.name, formalization_gate=formalization_gate, release_readiness=release_readiness, rollback_stub=rollback_stub)
        approval_outcome_stub = build_approval_outcome_stub(task_dir.name, approval_checklist=approval_checklist)
        approval_decision_placeholder = build_approval_decision_placeholder(task_dir.name, approval_outcome=approval_outcome_stub)
        approval_transition_stub = build_approval_transition_stub(task_dir.name, approval_decision=approval_decision_placeholder)
        human_approval_result_stub = build_human_approval_result_stub(task_dir.name, approval_transition=approval_transition_stub)
        release_action_stub = build_release_action_stub(task_dir.name, formalization_gate=formalization_gate)
        rollback_registry_entry = build_rollback_registry_entry(task_dir.name, rollback_stub=rollback_stub, formalization_gate=formalization_gate, official_release=False)
        artifacts.write_json(
            "delivery_boundary.json",
            {
                "task_id": task_dir.name,
                "result_tier": boundary.get("result_tier"),
                "approval_state": boundary.get("approval_state"),
                "formalization_required": boundary.get("formalization_required"),
                "manual_review_required": boundary.get("manual_review_required"),
                "official_release": False,
                "note": "delivery artifacts remain candidate-level until explicit human approval.",
            },
        )
        artifacts.write_json("formalization_gate.json", formalization_gate)
        artifacts.write_json("release_readiness.json", release_readiness)
        artifacts.write_json("rollback_stub.json", rollback_stub)
        artifacts.write_json("approval_record.json", approval_record)
        artifacts.write_json("approval_checklist.json", approval_checklist)
        artifacts.write_json("approval_outcome_stub.json", approval_outcome_stub)
        artifacts.write_json("approval_decision_placeholder.json", approval_decision_placeholder)
        artifacts.write_json("approval_transition_stub.json", approval_transition_stub)
        artifacts.write_json("human_approval_result_stub.json", human_approval_result_stub)
        artifacts.write_json("release_action_stub.json", release_action_stub)
        artifacts.write_json("rollback_registry_entry.json", rollback_registry_entry)
        release_preflight_stub = build_release_preflight_stub(task_dir.name, task_dir)
        artifacts.write_json("release_preflight_stub.json", release_preflight_stub)
        pre_release_gate = build_pre_release_gate(task_dir.name, formalization_gate=formalization_gate, approval_outcome=approval_outcome_stub, release_preflight=release_preflight_stub, rollback_registry=rollback_registry_entry)
        artifacts.write_json("pre_release_gate.json", pre_release_gate)
        human_approval_input_slot = build_human_approval_input_slot(task_dir.name, pre_release_gate=pre_release_gate, human_approval_result=human_approval_result_stub)
        artifacts.write_json("human_approval_input_slot.json", human_approval_input_slot)
        closure_consistency = build_release_closure_consistency(task_dir.name, approval_record=approval_record, approval_checklist=approval_checklist, approval_outcome=approval_outcome_stub, release_action=release_action_stub, release_preflight=release_preflight_stub, pre_release_gate=pre_release_gate, rollback_registry=rollback_registry_entry)
        artifacts.write_json("release_closure_consistency.json", closure_consistency)
        official_release_rehearsal = build_official_release_rehearsal(task_dir.name, pre_release_gate=pre_release_gate, closure_consistency=closure_consistency, approval_outcome=approval_outcome_stub, release_action=release_action_stub)
        artifacts.write_json("official_release_rehearsal.json", official_release_rehearsal)
        release_execution_guardrail = build_release_execution_guardrail(task_dir.name, approval_decision=approval_decision_placeholder, pre_release_gate=pre_release_gate, human_approval_result=human_approval_result_stub)
        artifacts.write_json("release_execution_guardrail.json", release_execution_guardrail)
        post_approval_guardrail_transition = build_post_approval_guardrail_transition(task_dir.name, human_approval_result=human_approval_result_stub, release_execution_guardrail=release_execution_guardrail)
        artifacts.write_json("post_approval_guardrail_transition.json", post_approval_guardrail_transition)
        official_release_state_placeholder = build_official_release_state_placeholder(task_dir.name, approval_transition=approval_transition_stub, release_execution_guardrail=release_execution_guardrail, human_approval_result=human_approval_result_stub)
        artifacts.write_json("official_release_state_placeholder.json", official_release_state_placeholder)
        approval_recompute_snapshot = build_approval_recompute_snapshot(task_dir.name, human_approval_result=human_approval_result_stub, pre_release_gate=pre_release_gate, official_release_rehearsal=official_release_rehearsal, release_execution_guardrail=release_execution_guardrail, official_release_state=official_release_state_placeholder)
        artifacts.write_json("approval_recompute_snapshot.json", approval_recompute_snapshot)
        release_artifact_binding = build_release_artifact_binding(task_dir.name, task_dir, rollback_stub=rollback_stub)
        artifacts.write_json("release_artifact_binding.json", release_artifact_binding)
        official_release_pipeline_summary = build_official_release_pipeline_summary(
            task_dir.name,
            pre_release_gate=pre_release_gate,
            official_release_rehearsal=official_release_rehearsal,
            release_execution_guardrail=release_execution_guardrail,
            official_release_state=official_release_state_placeholder,
            release_artifact_binding=release_artifact_binding,
            rollback_registry=rollback_registry_entry,
            human_approval_result=human_approval_result_stub,
            approval_recompute_snapshot=approval_recompute_snapshot,
        )
        artifacts.write_json("official_release_pipeline_summary.json", official_release_pipeline_summary)
        delivery_note = "\n".join([
            "# Delivery note",
            "",
            f"Task: {task_dir.name}",
            f"Objective: {task.get('objective', '')}",
            f"Review decision: {review.get('decision')}",
            f"Result tier: {boundary.get('result_tier')}",
            f"Approval state: {boundary.get('approval_state')}",
            f"Formalization required: {boundary.get('formalization_required')}",
            f"Release ready: {release_readiness.get('release_ready')}",
            f"Formalization state: {formalization_gate.get('formalization_state')}",
            f"Approval required: {approval_record.get('approval_required')}",
            f"Approval checklist ready: {approval_checklist.get('checklist_ready')}",
            f"Approval status: {approval_outcome_stub.get('approval_status')}",
            f"Approval decision placeholder: {approval_decision_placeholder.get('decision_state')}",
            f"Approval transition stub: {approval_transition_stub.get('transition_state')}",
            f"Human approval result stub: {human_approval_result_stub.get('ingestion_state')}",
            f"Human approval input slot: {human_approval_input_slot.get('current_state')}",
            f"Release action allowed: {release_action_stub.get('action_allowed')}",
            f"Release preflight ready: {release_preflight_stub.get('preflight_ready')}",
            f"Pre-release gate: {pre_release_gate.get('gate_state')}",
            f"Closure consistency ready: {closure_consistency.get('consistency_ready')}",
            f"Official release rehearsal: {official_release_rehearsal.get('rehearsal_state')}",
            f"Release execution guardrail: {release_execution_guardrail.get('execution_state')}",
            f"Post-approval guardrail transition: {post_approval_guardrail_transition.get('transition_state')}",
            f"Official release state placeholder: {official_release_state_placeholder.get('official_release_state')}",
            f"Approval recompute snapshot: {approval_recompute_snapshot.get('recompute_state')}",
            f"Release artifact binding: {release_artifact_binding.get('binding_ready')}",
            f"Official release pipeline summary: {official_release_pipeline_summary.get('pipeline_state')}",
            "",
            "## Boundary",
            "- 当前交付物属于候选结果（candidate），不是正式发布结果。",
            "- 如需进入正式版本/正式知识沉淀，仍需后续人工审批与正式收口动作。",
            f"- rollback_supported: {rollback_stub.get('rollback_supported')}",
        ]) + "\n"
        artifacts.write_text("delivery_note.md", delivery_note)
        names = artifacts.list_artifacts()
        self.handoff_task(task_dir, "knowledge-steward", names, "文档交付已生成（候选结果边界、pre-release gate、审批预演与 rollback 已标记），进入知识沉淀")
        self.complete_task(task_dir, True, delivery_note=True, result_tier="candidate", official_release=False)


if __name__ == "__main__":
    worker = DocManagerWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or "NO_TASK")
