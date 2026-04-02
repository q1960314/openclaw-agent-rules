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
from artifact_manager import ArtifactManager  # noqa: E402
from official_release_registry import build_official_release_stub  # noqa: E402
from release_closure_runtime import build_rollback_registry_entry  # noqa: E402


class KnowledgeStewardWorker(WorkerBase):
    def __init__(self):
        super().__init__("knowledge-steward")

    def _load_review(self, task_dir: Path) -> dict:
        review_file = task_dir / "review.json"
        if not review_file.exists():
            return {}
        return json.loads(review_file.read_text(encoding="utf-8"))

    def execute_task(self, task_dir: Path, task: dict) -> None:
        review = self._load_review(task_dir)
        if review.get("decision") != "passed":
            self.fail_task(task_dir, "knowledge-steward blocked: review decision is not passed")
            return

        required = [
            "delivery_note.md",
            "delivery_boundary.json",
            "formalization_gate.json",
            "release_readiness.json",
            "rollback_stub.json",
            "approval_record.json",
            "approval_checklist.json",
            "approval_outcome_stub.json",
            "approval_decision_placeholder.json",
            "approval_transition_stub.json",
            "human_approval_result_stub.json",
            "human_approval_input_slot.json",
            "release_action_stub.json",
            "release_preflight_stub.json",
            "pre_release_gate.json",
            "release_closure_consistency.json",
            "official_release_rehearsal.json",
            "release_execution_guardrail.json",
            "post_approval_guardrail_transition.json",
            "official_release_state_placeholder.json",
            "approval_recompute_snapshot.json",
            "release_artifact_binding.json",
        ]
        for name in required:
            if not (task_dir / "artifacts" / name).exists():
                self.fail_task(task_dir, f"knowledge-steward blocked: {name} missing")
                return

        boundary = self._result_boundary(task_dir)
        gate_payload = json.loads((task_dir / 'artifacts' / 'formalization_gate.json').read_text(encoding='utf-8'))
        rollback_payload = json.loads((task_dir / 'artifacts' / 'rollback_stub.json').read_text(encoding='utf-8'))
        pre_release_gate = json.loads((task_dir / 'artifacts' / 'pre_release_gate.json').read_text(encoding='utf-8'))
        release_rehearsal = json.loads((task_dir / 'artifacts' / 'official_release_rehearsal.json').read_text(encoding='utf-8'))
        human_approval_result = json.loads((task_dir / 'artifacts' / 'human_approval_result_stub.json').read_text(encoding='utf-8'))
        human_approval_input = json.loads((task_dir / 'artifacts' / 'human_approval_input_slot.json').read_text(encoding='utf-8'))
        execution_guardrail = json.loads((task_dir / 'artifacts' / 'release_execution_guardrail.json').read_text(encoding='utf-8'))
        post_approval_transition = json.loads((task_dir / 'artifacts' / 'post_approval_guardrail_transition.json').read_text(encoding='utf-8'))
        official_release_state = json.loads((task_dir / 'artifacts' / 'official_release_state_placeholder.json').read_text(encoding='utf-8'))
        approval_recompute = json.loads((task_dir / 'artifacts' / 'approval_recompute_snapshot.json').read_text(encoding='utf-8'))
        release_artifact_binding = json.loads((task_dir / 'artifacts' / 'release_artifact_binding.json').read_text(encoding='utf-8'))
        artifacts = ArtifactManager(task_dir)
        official_release_stub = build_official_release_stub(task_dir, boundary=boundary, review=review)
        knowledge_entry = "\n".join([
            "# Knowledge Entry",
            "",
            f"Task: {task_dir.name}",
            "Summary: archived as candidate-level ecosystem knowledge.",
            "",
            "## Boundary",
            f"- result_tier: {boundary.get('result_tier')}",
            f"- approval_state: {boundary.get('approval_state')}",
            f"- official_release: {official_release_stub.get('official_release')}",
            f"- formalization_state: {gate_payload.get('formalization_state')}",
            f"- pre_release_gate: {pre_release_gate.get('gate_state')}",
            f"- official_release_rehearsal: {release_rehearsal.get('rehearsal_state')}",
            f"- human_approval_result: {human_approval_result.get('ingestion_state')}",
            f"- human_approval_input_slot: {human_approval_input.get('current_state')}",
            f"- release_execution_guardrail: {execution_guardrail.get('execution_state')}",
            f"- post_approval_guardrail_transition: {post_approval_transition.get('transition_state')}",
            f"- official_release_state: {official_release_state.get('official_release_state')}",
            f"- approval_recompute: {approval_recompute.get('recompute_state')}",
            f"- release_artifact_binding: {release_artifact_binding.get('binding_ready')}",
            "- 本次沉淀是候选知识沉淀，不代表正式规则/正式版本发布。",
        ]) + "\n"
        artifacts.write_text("knowledge_entry.md", knowledge_entry)
        artifacts.write_json(
            "knowledge_boundary.json",
            {
                "task_id": task_dir.name,
                "result_tier": boundary.get("result_tier"),
                "approval_state": boundary.get("approval_state"),
                "formalization_required": boundary.get("formalization_required"),
                "manual_review_required": boundary.get("manual_review_required"),
                "knowledge_tier": "candidate_archive",
                "official_release": False,
            },
        )
        artifacts.write_json("official_release_stub.json", official_release_stub)
        artifacts.write_json("rollback_registry_entry.json", build_rollback_registry_entry(task_dir.name, rollback_stub=rollback_payload, formalization_gate=gate_payload, official_release=False))
        self.complete_task(task_dir, True, archived=True, result_tier="candidate", official_release=False)


if __name__ == "__main__":
    worker = KnowledgeStewardWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or "NO_TASK")
