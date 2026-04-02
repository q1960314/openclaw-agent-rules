#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from worker_base import WorkerBase  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402
from schema_validator import validate_payload_against_schema  # noqa: E402
from decision_engine import review_outcome  # noqa: E402
from evaluation_runtime import evaluate_quality  # noqa: E402


class TestExpertWorker(WorkerBase):
    def __init__(self):
        super().__init__("test-expert")

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _check_exists(self, task_dir: Path, relative_path: str) -> tuple[bool, str]:
        path = task_dir / relative_path
        if not path.exists():
            return False, f"missing: {relative_path}"
        return True, f"exists: {relative_path}"

    def _check_nonempty_text(self, path: Path, label: str, min_len: int = 20) -> tuple[bool, str]:
        if not path.exists():
            return False, f"missing: {label}"
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if len(text) < min_len:
            return False, f"too short: {label} ({len(text)} chars)"
        return True, f"non-empty: {label} ({len(text)} chars)"

    def _check_diff_quality(self, diff_path: Path, mode: str) -> tuple[bool, str]:
        if not diff_path.exists():
            return False, "missing: diff.patch"
        text = diff_path.read_text(encoding="utf-8", errors="ignore")
        stripped = text.strip()
        if not stripped:
            return False, "empty: diff.patch"
        if mode == "build":
            if "diff --git" not in text:
                return False, "build diff invalid: no git diff markers"
            return True, "build diff contains git patch markers"
        if "placeholder" in stripped.lower():
            return False, "plan diff invalid: placeholder patch"
        return True, f"plan diff present ({len(stripped)} chars)"

    def _check_opencode_result(self, result: dict[str, Any]) -> tuple[bool, str]:
        if not result:
            return False, "missing: opencode_result.json"
        if result.get("returncode") != 0:
            return False, f"opencode returncode != 0 ({result.get('returncode')})"
        if result.get("timed_out"):
            return False, "opencode timed out"
        return True, f"opencode ok: mode={result.get('mode')} model={result.get('model')}"

    def _required_artifacts(self, task: dict[str, Any]) -> list[str]:
        metadata = task.get("metadata", {}) if isinstance(task.get("metadata", {}), dict) else {}
        required = metadata.get("required_artifacts", [])
        if required:
            return [f"artifacts/{item}" for item in required]
        return [
            "artifacts/diff.patch",
            "artifacts/changed_files.json",
            "artifacts/result_summary.md",
            "artifacts/opencode_result.json",
        ]

    def _validate_factor(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "factor_plan.md", "factor_plan.md")
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        candidate = self._read_json(task_dir / "artifacts" / "factor_candidate.json")
        analysis = self._read_json(task_dir / "artifacts" / "factor_analysis.json")
        depth = self._read_json(task_dir / "artifacts" / "factor_depth.json")
        if not candidate:
            issues.append("factor_candidate.json missing or invalid")
            evidence.append("factor_candidate.json missing or invalid")
        else:
            schema_errors = validate_payload_against_schema(candidate, 'factor_miner_result.schema.json')
            if schema_errors:
                issues.extend(schema_errors)
                evidence.extend([f'schema_error: {item}' for item in schema_errors])
            else:
                evidence.append('factor_candidate schema valid')
            summary = str(candidate.get("factor_summary", "")).strip()
            if not summary:
                issues.append("factor_candidate summary empty")
                evidence.append("factor_candidate summary empty")
            else:
                evidence.append("factor_candidate summary present")
            if len(candidate.get('factor_hypotheses', [])) < 2:
                issues.append('factor_hypotheses depth insufficient (<2)')
            else:
                evidence.append(f"factor_hypotheses count={len(candidate.get('factor_hypotheses', []))}")
            if len(candidate.get('economic_rationales', [])) < 2:
                issues.append('economic_rationales depth insufficient (<2)')
            else:
                evidence.append(f"economic_rationales count={len(candidate.get('economic_rationales', []))}")
            if len(candidate.get('candidate_factors', [])) < 2:
                issues.append('candidate_factors depth insufficient (<2)')
            else:
                evidence.append(f"candidate_factors count={len(candidate.get('candidate_factors', []))}")
            if len(candidate.get('applicability_conditions', [])) < 2:
                issues.append('factor applicability_conditions depth insufficient (<2)')
            else:
                evidence.append(f"factor applicability_conditions count={len(candidate.get('applicability_conditions', []))}")
            if len(candidate.get('code_touchpoints', [])) < 2:
                issues.append('factor code_touchpoints depth insufficient (<2)')
            else:
                evidence.append(f"factor code_touchpoints count={len(candidate.get('code_touchpoints', []))}")
            if len(candidate.get('strategy_handoff', [])) < 1:
                issues.append('factor strategy_handoff missing')
            else:
                evidence.append(f"factor strategy_handoff count={len(candidate.get('strategy_handoff', []))}")
            if len(candidate.get('parameter_handoff', [])) < 1:
                issues.append('factor parameter_handoff missing')
            else:
                evidence.append(f"factor parameter_handoff count={len(candidate.get('parameter_handoff', []))}")
            if len(candidate.get('failure_scenarios', [])) < 2:
                issues.append('failure_scenarios depth insufficient (<2)')
            else:
                evidence.append(f"failure_scenarios count={len(candidate.get('failure_scenarios', []))}")
            if len(candidate.get('validation_plan', [])) < 2:
                issues.append('factor validation_plan depth insufficient (<2)')
            else:
                evidence.append(f"factor validation_plan count={len(candidate.get('validation_plan', []))}")
            if len(candidate.get('validation_priority', [])) < 2:
                issues.append('factor validation_priority depth insufficient (<2)')
            else:
                evidence.append(f"factor validation_priority count={len(candidate.get('validation_priority', []))}")
        if not analysis:
            issues.append('factor_analysis.json missing or invalid')
            evidence.append('factor_analysis.json missing or invalid')
        else:
            evidence.append('factor_analysis.json present')
        if not depth:
            issues.append('factor_depth.json missing or invalid')
            evidence.append('factor_depth.json missing or invalid')
        else:
            evidence.append(f"factor depth metrics={depth}")

    def _validate_sentiment(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "sentiment_plan.md", "sentiment_plan.md")
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        candidate = self._read_json(task_dir / "artifacts" / "sentiment_candidate.json")
        if not candidate:
            issues.append("sentiment_candidate.json missing or invalid")
            evidence.append("sentiment_candidate.json missing or invalid")
        else:
            summary = str(candidate.get("sentiment_summary", "")).strip()
            if not summary:
                issues.append("sentiment_candidate summary empty")
                evidence.append("sentiment_candidate summary empty")
            else:
                evidence.append("sentiment_candidate summary present")

    def _validate_finance(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "finance_note.md", "finance_note.md")
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        candidate = self._read_json(task_dir / "artifacts" / "finance_learning.json")
        if not candidate:
            issues.append("finance_learning.json missing or invalid")
            evidence.append("finance_learning.json missing or invalid")
        else:
            summary = str(candidate.get("learning_summary", "")).strip()
            if not summary:
                issues.append("finance_learning summary empty")
                evidence.append("finance_learning summary empty")
            else:
                evidence.append("finance_learning summary present")

    def _validate_strategy(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "strategy_plan.md", "strategy_plan.md")
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        candidate = self._read_json(task_dir / "artifacts" / "strategy_candidate.json")
        analysis = self._read_json(task_dir / "artifacts" / "strategy_analysis.json")
        depth = self._read_json(task_dir / "artifacts" / "strategy_depth.json")
        if not candidate:
            issues.append("strategy_candidate.json missing or invalid")
            evidence.append("strategy_candidate.json missing or invalid")
        else:
            schema_errors = validate_payload_against_schema(candidate, 'strategy_expert_result.schema.json')
            if schema_errors:
                issues.extend(schema_errors)
                evidence.extend([f'schema_error: {item}' for item in schema_errors])
            else:
                evidence.append('strategy_candidate schema valid')
            recommendation = str(candidate.get("recommendation", "")).strip()
            if not recommendation:
                issues.append("strategy_candidate recommendation empty")
                evidence.append("strategy_candidate recommendation empty")
            else:
                evidence.append("strategy_candidate recommendation present")
            if len(candidate.get('hypotheses', [])) < 2:
                issues.append('strategy hypotheses depth insufficient (<2)')
            else:
                evidence.append(f"strategy hypotheses count={len(candidate.get('hypotheses', []))}")
            if len(candidate.get('candidate_solutions', [])) < 2:
                issues.append('strategy candidate_solutions depth insufficient (<2)')
            else:
                evidence.append(f"strategy candidate_solutions count={len(candidate.get('candidate_solutions', []))}")
            if len(candidate.get('solution_comparison', [])) < 2:
                issues.append('strategy solution_comparison depth insufficient (<2)')
            else:
                evidence.append(f"strategy solution_comparison count={len(candidate.get('solution_comparison', []))}")
            if len(candidate.get('recommendation_basis', [])) < 2:
                issues.append('strategy recommendation_basis depth insufficient (<2)')
            else:
                evidence.append(f"strategy recommendation_basis count={len(candidate.get('recommendation_basis', []))}")
            if len(candidate.get('applicability_conditions', [])) < 2:
                issues.append('strategy applicability_conditions depth insufficient (<2)')
            else:
                evidence.append(f"strategy applicability_conditions count={len(candidate.get('applicability_conditions', []))}")
            if len(candidate.get('code_touchpoints', [])) < 2:
                issues.append('strategy code_touchpoints depth insufficient (<2)')
            else:
                evidence.append(f"strategy code_touchpoints count={len(candidate.get('code_touchpoints', []))}")
            if len(candidate.get('change_priority', [])) < 2:
                issues.append('strategy change_priority depth insufficient (<2)')
            else:
                evidence.append(f"strategy change_priority count={len(candidate.get('change_priority', []))}")
            if len(candidate.get('backtest_handoff', [])) < 1:
                issues.append('strategy backtest_handoff missing')
            else:
                evidence.append(f"strategy backtest_handoff count={len(candidate.get('backtest_handoff', []))}")
            if len(candidate.get('parameter_handoff', [])) < 1:
                issues.append('strategy parameter_handoff missing')
            else:
                evidence.append(f"strategy parameter_handoff count={len(candidate.get('parameter_handoff', []))}")
            if len(candidate.get('factor_handoff', [])) < 1:
                issues.append('strategy factor_handoff missing')
            else:
                evidence.append(f"strategy factor_handoff count={len(candidate.get('factor_handoff', []))}")
            if len(candidate.get('failure_scenarios', [])) < 2:
                issues.append('strategy failure_scenarios depth insufficient (<2)')
            else:
                evidence.append(f"strategy failure_scenarios count={len(candidate.get('failure_scenarios', []))}")
            if len(candidate.get('validation_path', [])) < 2:
                issues.append('strategy validation_path depth insufficient (<2)')
            else:
                evidence.append(f"strategy validation_path count={len(candidate.get('validation_path', []))}")
            if len(candidate.get('validation_priority', [])) < 2:
                issues.append('strategy validation_priority depth insufficient (<2)')
            else:
                evidence.append(f"strategy validation_priority count={len(candidate.get('validation_priority', []))}")
            if len(candidate.get('risk_notes', [])) < 2:
                issues.append('strategy risk_notes depth insufficient (<2)')
            else:
                evidence.append(f"strategy risk_notes count={len(candidate.get('risk_notes', []))}")
            if len(str(candidate.get('why_not_others', '')).strip()) < 10:
                issues.append('strategy why_not_others too weak')
            else:
                evidence.append('strategy why_not_others present')
        if not analysis:
            issues.append('strategy_analysis.json missing or invalid')
            evidence.append('strategy_analysis.json missing or invalid')
        else:
            evidence.append('strategy_analysis.json present')
        if not depth:
            issues.append('strategy_depth.json missing or invalid')
            evidence.append('strategy_depth.json missing or invalid')
        else:
            evidence.append(f"strategy depth metrics={depth}")

    def _validate_parameter(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "parameter_plan.md", "parameter_plan.md")
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        candidate = self._read_json(task_dir / "artifacts" / "parameter_candidate.json")
        analysis = self._read_json(task_dir / "artifacts" / "parameter_analysis.json")
        depth = self._read_json(task_dir / "artifacts" / "parameter_depth.json")
        if not candidate:
            issues.append("parameter_candidate.json missing or invalid")
            evidence.append("parameter_candidate.json missing or invalid")
        else:
            schema_errors = validate_payload_against_schema(candidate, 'parameter_evolver_result.schema.json')
            if schema_errors:
                issues.extend(schema_errors)
                evidence.extend([f'schema_error: {item}' for item in schema_errors])
            else:
                evidence.append('parameter_candidate schema valid')
            summary = str(candidate.get("candidate_summary", "")).strip()
            if not summary:
                issues.append("parameter_candidate summary empty")
                evidence.append("parameter_candidate summary empty")
            else:
                evidence.append("parameter_candidate summary present")
            if len(candidate.get('sensitive_parameters', [])) < 2:
                issues.append('sensitive_parameters depth insufficient (<2)')
            else:
                evidence.append(f"sensitive_parameters count={len(candidate.get('sensitive_parameters', []))}")
            if len(candidate.get('sensitivity_rationales', [])) < 2:
                issues.append('sensitivity_rationales depth insufficient (<2)')
            else:
                evidence.append(f"sensitivity_rationales count={len(candidate.get('sensitivity_rationales', []))}")
            if len(candidate.get('robust_ranges', [])) < 1:
                issues.append('robust_ranges missing')
            else:
                evidence.append(f"robust_ranges count={len(candidate.get('robust_ranges', []))}")
            if len(candidate.get('fragile_ranges', [])) < 1:
                issues.append('fragile_ranges missing')
            else:
                evidence.append(f"fragile_ranges count={len(candidate.get('fragile_ranges', []))}")
            if len(candidate.get('range_justification', [])) < 2:
                issues.append('range_justification depth insufficient (<2)')
            else:
                evidence.append(f"range_justification count={len(candidate.get('range_justification', []))}")
            if len(candidate.get('tuning_sequence', [])) < 2:
                issues.append('tuning_sequence depth insufficient (<2)')
            else:
                evidence.append(f"tuning_sequence count={len(candidate.get('tuning_sequence', []))}")
            if len(candidate.get('metric_guardrails', [])) < 2:
                issues.append('metric_guardrails depth insufficient (<2)')
            else:
                evidence.append(f"metric_guardrails count={len(candidate.get('metric_guardrails', []))}")
            if len(candidate.get('code_touchpoints', [])) < 2:
                issues.append('parameter code_touchpoints depth insufficient (<2)')
            else:
                evidence.append(f"parameter code_touchpoints count={len(candidate.get('code_touchpoints', []))}")
            if len(candidate.get('change_priority', [])) < 2:
                issues.append('parameter change_priority depth insufficient (<2)')
            else:
                evidence.append(f"parameter change_priority count={len(candidate.get('change_priority', []))}")
            if len(candidate.get('backtest_handoff', [])) < 1:
                issues.append('parameter backtest_handoff missing')
            else:
                evidence.append(f"parameter backtest_handoff count={len(candidate.get('backtest_handoff', []))}")
            if len(candidate.get('validation_plan', [])) < 2:
                issues.append('parameter validation_plan depth insufficient (<2)')
            else:
                evidence.append(f"parameter validation_plan count={len(candidate.get('validation_plan', []))}")
        if not analysis:
            issues.append('parameter_analysis.json missing or invalid')
            evidence.append('parameter_analysis.json missing or invalid')
        else:
            evidence.append('parameter_analysis.json present')
        if not depth:
            issues.append('parameter_depth.json missing or invalid')
            evidence.append('parameter_depth.json missing or invalid')
        else:
            evidence.append(f"parameter depth metrics={depth}")

    def _validate_data(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        snapshot = self._read_json(task_dir / "artifacts" / "data_snapshot.json")
        check = self._read_json(task_dir / "artifacts" / "data_check.json")
        score = self._read_json(task_dir / "artifacts" / "data_quality_score.json")
        if not snapshot:
            issues.append('data_snapshot.json missing or invalid')
            evidence.append('data_snapshot.json missing or invalid')
        else:
            evidence.append(f"data stock_dir_count={snapshot.get('stock_dir_count')}")
        if not check:
            issues.append('data_check.json missing or invalid')
            evidence.append('data_check.json missing or invalid')
        else:
            evidence.append(f"data status={check.get('summary', {}).get('status')}")
        if not score:
            issues.append('data_quality_score.json missing or invalid')
            evidence.append('data_quality_score.json missing or invalid')
        else:
            evidence.append(f"data quality score={score.get('score')} grade={score.get('grade')}")

    def _validate_ops(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        summary = self._read_json(task_dir / "artifacts" / "ops_summary.json")
        if not summary:
            issues.append('ops_summary.json missing or invalid')
            evidence.append('ops_summary.json missing or invalid')
        else:
            evidence.append(f"ops openclaw_status_returncode={summary.get('openclaw_status_returncode')}")
            evidence.append(f"ops workflow_status_returncode={summary.get('workflow_status_returncode')}")
            evidence.append(f"ops workflow_ok={summary.get('workflow_ok')}")
            evidence.append(f"ops stale_count={summary.get('stale_count')}")
            evidence.append(f"ops recoverability_counts={summary.get('recoverability_counts')}")
            evidence.append(f"ops lifecycle_bucket_counts={summary.get('lifecycle_bucket_counts')}")
        health = self._read_json(task_dir / "artifacts" / "health_dashboard.json")
        if not health:
            issues.append('health_dashboard.json missing or invalid')
            evidence.append('health_dashboard.json missing or invalid')
        else:
            evidence.append(f"health job_count={health.get('job_count')}")
            evidence.append(f"health recoverability_counts={health.get('recoverability_counts')}")
        recovery = self._read_json(task_dir / "artifacts" / "recovery_dashboard.json")
        if not recovery:
            issues.append('recovery_dashboard.json missing or invalid')
            evidence.append('recovery_dashboard.json missing or invalid')
        else:
            evidence.append(f"recovery counts={recovery.get('recoverability_counts')}")
        lifecycle = self._read_json(task_dir / "artifacts" / "lifecycle_dashboard.json")
        if not lifecycle:
            issues.append('lifecycle_dashboard.json missing or invalid')
            evidence.append('lifecycle_dashboard.json missing or invalid')
        else:
            evidence.append(f"lifecycle bucket_counts={lifecycle.get('bucket_counts')}")
        stage_card = self._read_json(task_dir / "artifacts" / "ecosystem_stage_card.json")
        if not stage_card:
            issues.append('ecosystem_stage_card.json missing or invalid')
            evidence.append('ecosystem_stage_card.json missing or invalid')
        else:
            evidence.append(f"stage_card stage_id={stage_card.get('stage_id')} maturity_band={stage_card.get('maturity_band')}")
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "ops_report.md", "ops_report.md", min_len=100)
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "health_dashboard.md", "health_dashboard.md", min_len=100)
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "recovery_dashboard.md", "recovery_dashboard.md", min_len=80)
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "lifecycle_dashboard.md", "lifecycle_dashboard.md", min_len=80)
        evidence.append(msg)
        if not ok:
            issues.append(msg)
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "ecosystem_stage_card.md", "ecosystem_stage_card.md", min_len=80)
        evidence.append(msg)
        if not ok:
            issues.append(msg)

    def _validate_backtest(self, task_dir: Path, issues: list[str], evidence: list[str]) -> None:
        metrics = self._read_json(task_dir / "artifacts" / "backtest_metrics.json")
        if not metrics:
            issues.append("backtest_metrics.json missing or invalid")
            evidence.append("backtest_metrics.json missing or invalid")
        else:
            stats = metrics.get('metrics', {})
            trades = stats.get('total_trades')
            if trades is None:
                issues.append('backtest total_trades missing')
                evidence.append('backtest total_trades missing')
            else:
                evidence.append(f"backtest total_trades={trades}")
            if stats.get('max_drawdown') is None:
                issues.append('backtest max_drawdown missing')
                evidence.append('backtest max_drawdown missing')
            else:
                evidence.append(f"backtest max_drawdown={stats.get('max_drawdown')}")
        ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "backtest_report.md", "backtest_report.md", min_len=80)
        evidence.append(msg)
        if not ok:
            issues.append(msg)

    def _validate_coder(self, task_dir: Path, mode: str, issues: list[str], evidence: list[str]) -> None:
        ok, msg = self._check_diff_quality(task_dir / "artifacts" / "diff.patch", mode)
        evidence.append(msg)
        if not ok:
            issues.append(msg)

        changed_files = self._read_json(task_dir / "artifacts" / "changed_files.json").get("changed_files", [])
        if mode == "build":
            if not changed_files:
                issues.append("build changed_files empty")
                evidence.append("build changed_files empty")
            else:
                evidence.append(f"build changed_files count={len(changed_files)}")
            worktree_path = task_dir / "artifacts" / "worktree_path.txt"
            if not worktree_path.exists():
                issues.append("build missing worktree_path.txt")
                evidence.append("build missing worktree_path.txt")
            else:
                evidence.append("build worktree_path.txt exists")
        else:
            evidence.append(f"mode={mode}; changed_files count={len(changed_files)}")

    def execute_task(self, task_dir: Path, task: dict) -> None:
        artifacts = ArtifactManager(task_dir)
        issues: list[str] = []
        evidence: list[str] = []
        metadata = task.get("metadata", {}) if isinstance(task.get("metadata", {}), dict) else {}

        for rel in self._required_artifacts(task):
            ok, msg = self._check_exists(task_dir, rel)
            evidence.append(msg)
            if not ok:
                issues.append(msg)

        role = task.get("role") or task.get("owner_role") or "unknown"
        if role == 'backtest-engine':
            self._validate_backtest(task_dir, issues, evidence)
            mode = 'native'
        elif role == 'data-collector':
            self._validate_data(task_dir, issues, evidence)
            ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "result_summary.md", "result_summary.md")
            evidence.append(msg)
            if not ok:
                issues.append(msg)
            mode = 'native'
        elif role == 'ops-monitor':
            self._validate_ops(task_dir, issues, evidence)
            ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "result_summary.md", "result_summary.md")
            evidence.append(msg)
            if not ok:
                issues.append(msg)
            mode = 'native'
        else:
            opencode_result = self._read_json(task_dir / "artifacts" / "opencode_result.json")
            mode = opencode_result.get("mode", "unknown")
            ok, msg = self._check_opencode_result(opencode_result)
            evidence.append(msg)
            if not ok:
                issues.append(msg)

            ok, msg = self._check_nonempty_text(task_dir / "artifacts" / "result_summary.md", "result_summary.md")
            evidence.append(msg)
            if not ok:
                issues.append(msg)

            if role == 'factor-miner':
                self._validate_factor(task_dir, issues, evidence)
            elif role == 'finance-learner':
                self._validate_finance(task_dir, issues, evidence)
            elif role == 'sentiment-analyst':
                self._validate_sentiment(task_dir, issues, evidence)
            elif role == 'strategy-expert':
                self._validate_strategy(task_dir, issues, evidence)
            elif role == 'parameter-evolver':
                self._validate_parameter(task_dir, issues, evidence)
            else:
                self._validate_coder(task_dir, mode, issues, evidence)

        if metadata.get('force_reject_once') and not metadata.get('retry_of'):
            issues.append('forced reject once for loop retry validation')
            evidence.append('forced reject once for loop retry validation')

        outcome = review_outcome(
            issues,
            manual_review_required=bool(metadata.get('manual_review_required', False)),
            review_scope='technical_validation',
        )
        decision = outcome['review_decision']
        self.review(task_dir, decision, issues, evidence, terminal_status=outcome['terminal_status'], review_scope=outcome['review_scope'], reason=outcome['reason'])
        quality = evaluate_quality(
            task_id=task_dir.name,
            role=role,
            review_decision=decision,
            issues=issues,
            evidence=evidence,
            manual_review_required=bool(metadata.get('manual_review_required', False)),
        )
        artifacts.write_json('quality_score.json', quality)
        quality_lines = [
            '# Quality Score',
            '',
            quality['summary'],
            '',
            f"- score: {quality['score']}",
            f"- grade: {quality['grade']}",
            f"- artifact_completeness: {quality['dimensions']['artifact_completeness']}",
            f"- structural_quality: {quality['dimensions']['structural_quality']}",
            f"- validation_outcome: {quality['dimensions']['validation_outcome']}",
            f"- release_readiness: {quality['dimensions']['release_readiness']}",
            f"- blocking_flags: {quality['blocking_flags']}",
        ]
        artifacts.write_text('quality_score.md', '\n'.join(quality_lines) + '\n')
        report_lines = [
            f"decision={decision}",
            f"terminal_status={outcome['terminal_status']}",
            f"reason={outcome['reason']}",
            f"role={role}",
            f"mode={mode}",
            f"quality_score={quality['score']}",
            f"quality_grade={quality['grade']}",
            "issues:",
            *[f"- {item}" for item in issues],
            "evidence:",
            *[f"- {item}" for item in evidence],
        ]
        artifacts.write_text("test_report.md", "\n".join(report_lines) + "\n")

        if decision == 'passed':
            self.update_status(task_dir, "under_review", 85, "review_passed")
            self.handoff_task(task_dir, "doc-manager", ["artifacts/test_report.md", "artifacts/quality_score.json", "artifacts/quality_score.md", "review.json"], "验收通过，进入文档整理")
            self.complete_task(task_dir, True, review_decision="passed", terminal_status=outcome['terminal_status'], quality_score=quality['score'], quality_grade=quality['grade'])
        elif decision == 'manual_review_required':
            self.update_status(task_dir, 'manual_review_required', 90, 'manual_review_required', reason=outcome['reason'])
        else:
            self.update_status(task_dir, "rejected", 100, "review_failed", issues=issues, terminal_status=outcome['terminal_status'])


if __name__ == "__main__":
    worker = TestExpertWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or "NO_TASK")
