#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any


SECTION_RE = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)


def _clean_text(text: str) -> str:
    return re.sub(r'\n{3,}', '\n\n', (text or '').strip())


def first_nonempty_line(text: str, default: str = '') -> str:
    for line in (text or '').splitlines():
        cleaned = line.strip().strip('-*0123456789. ')
        if cleaned:
            return cleaned
    return default


def bullet_items(text: str, limit: int = 5) -> list[str]:
    items: list[str] = []
    for line in (text or '').splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r'^[-*•]\s*', '', cleaned)
        cleaned = re.sub(r'^\d+[.)]\s*', '', cleaned)
        if len(cleaned) < 2:
            continue
        if cleaned not in items:
            items.append(cleaned)
        if len(items) >= limit:
            break
    return items


def _find_section_spans(text: str) -> list[tuple[str, int, int]]:
    matches = list(SECTION_RE.finditer(text or ''))
    spans: list[tuple[str, int, int]] = []
    for idx, match in enumerate(matches):
        heading = match.group(2).strip().lower()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        spans.append((heading, start, end))
    return spans


def section_text(text: str, aliases: list[str], default: str = '') -> str:
    normalized_aliases = [a.strip().lower() for a in aliases]
    for heading, start, end in _find_section_spans(text):
        if any(alias in heading for alias in normalized_aliases):
            return _clean_text(text[start:end])
    return default


def section_bullets(text: str, aliases: list[str], limit: int = 5, fallback: list[str] | None = None) -> list[str]:
    section = section_text(text, aliases, '')
    items = bullet_items(section, limit=limit)
    if items:
        return items
    return fallback[:] if fallback else []


def _depth_metrics(**counts: int) -> dict[str, Any]:
    return {
        'counts': counts,
        'depth_ready': all(int(v) > 0 for v in counts.values()),
    }


def make_strategy_prompt(base_prompt: str) -> str:
    return base_prompt + """

Structured output requirements for strategy-expert:
- Return a markdown report with these exact headings:
  # Problem Statement
  # Hypotheses
  # Candidate Solutions
  # Solution Comparison
  # Recommended Solution
  # Recommendation Basis
  # Why Not Others
  # Applicability Conditions
  # Code Touchpoints
  # Change Priority
  # Backtest Handoff
  # Parameter Handoff
  # Factor Handoff
  # Failure Scenarios
  # Validation Path
  # Validation Priority
  # Risk Notes
- Under Candidate Solutions, compare at least 2 candidate directions.
- Provide at least 2 hypotheses, at least 2 candidate solutions, at least 2 solution comparison items, at least 2 recommendation basis items, at least 2 applicability conditions, at least 2 code touchpoints, at least 2 change priority items, at least 1 backtest handoff item, at least 1 parameter handoff item, at least 1 factor handoff item, at least 2 failure scenarios, at least 2 validation steps, at least 2 validation priority items, and at least 2 risk notes.
- Solution Comparison must explain the concrete trade-offs between candidate directions.
- Recommendation Basis must explain why the selected path is better for the current objective/code context.
- Code Touchpoints must tie the recommendation back to concrete files/modules/functions when possible.
- Change Priority must explain what to inspect or modify first vs later.
- Backtest/Parameter/Factor Handoff must tell the downstream expert what to validate or optimize next.
- Why Not Others must explicitly explain why the non-selected path is weaker.
- Validation Priority must explain which validation checks should run first and why.
- Keep the output concrete and implementation-oriented; avoid generic summary language.
"""


def make_parameter_prompt(base_prompt: str) -> str:
    return base_prompt + """

Structured output requirements for parameter-evolver:
- Return a markdown report with these exact headings:
  # Parameter Objective
  # Sensitive Parameters
  # Sensitivity Rationales
  # Robust Ranges
  # Fragile Ranges
  # Range Justification
  # Tuning Sequence
  # Boundary Design
  # Metric Guardrails
  # Code Touchpoints
  # Change Priority
  # Backtest Handoff
  # Validation Plan
  # Risk Notes
- Distinguish robust ranges from fragile / overfit-prone ranges.
- Provide at least 2 sensitive parameters (when possible), at least 2 sensitivity rationales, at least 1 robust range, at least 1 fragile range, at least 2 range justification items, at least 2 tuning steps, at least 2 metric guardrails, at least 2 code touchpoints, at least 2 change priority items, at least 1 backtest handoff item, and at least 2 validation steps.
- Sensitivity Rationales must explain why a parameter is fragile or influential.
- Range Justification must explain why a range is considered robust or fragile.
- Metric Guardrails must define which metrics must not be sacrificed while tuning.
- Code Touchpoints must tie the parameters back to concrete files/modules/functions when possible.
- Change Priority must explain what to inspect or adjust first vs later.
- Backtest Handoff must tell backtest-engine what ranges/guardrails to validate next.
- Make the output directly usable for later backtest validation.
"""


def make_factor_prompt(base_prompt: str) -> str:
    return base_prompt + """

Structured output requirements for factor-miner:
- Return a markdown report with these exact headings:
  # Factor Hypotheses
  # Economic Rationales
  # Candidate Factors
  # Applicability Conditions
  # Code Touchpoints
  # Strategy Handoff
  # Parameter Handoff
  # Failure Scenarios
  # Validation Plan
  # Validation Priority
  # Overlap Risks
  # Recommendation
- Explain why the factor may work, when it may fail, where it is more applicable, how it maps back to the code, and how downstream strategy/parameter work should continue.
- Provide at least 2 hypotheses, at least 2 rationales, at least 2 candidate factors, at least 2 applicability conditions, at least 2 code touchpoints, at least 1 strategy handoff item, at least 1 parameter handoff item, at least 2 failure scenarios, at least 2 validation steps, and at least 2 validation priority items.
- Validation Priority must explain which checks should run first and why.
- Code Touchpoints must tie the factor idea back to concrete files/modules/features when possible.
- Strategy/Parameter Handoff must explain what downstream experts should do next if the factor looks promising.
- Avoid empty finance jargon; keep the output specific and testable.
"""


def build_strategy_candidate(task: dict[str, Any], plan_text: str, normalized_request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    recommendation = section_text(plan_text, ['recommended solution'], '')
    hypotheses = section_bullets(plan_text, ['hypotheses'], limit=8)
    candidate_solutions = section_bullets(plan_text, ['candidate solutions'], limit=8)
    solution_comparison = section_bullets(plan_text, ['solution comparison'], limit=8)
    recommendation_basis = section_bullets(plan_text, ['recommendation basis'], limit=8)
    applicability_conditions = section_bullets(plan_text, ['applicability conditions'], limit=8)
    code_touchpoints = section_bullets(plan_text, ['code touchpoints'], limit=8)
    change_priority = section_bullets(plan_text, ['change priority'], limit=8)
    backtest_handoff = section_bullets(plan_text, ['backtest handoff'], limit=8)
    parameter_handoff = section_bullets(plan_text, ['parameter handoff'], limit=8)
    factor_handoff = section_bullets(plan_text, ['factor handoff'], limit=8)
    failure_scenarios = section_bullets(plan_text, ['failure scenarios'], limit=8)
    validation_path = section_bullets(plan_text, ['validation path'], limit=8)
    validation_priority = section_bullets(plan_text, ['validation priority'], limit=8)
    risk_notes = section_bullets(plan_text, ['risk notes'], limit=8)
    return {
        'task_id': task.get('task_id'),
        'objective': task.get('objective', ''),
        'mode': result.get('mode'),
        'model': result.get('model'),
        'recommendation': first_nonempty_line(recommendation or plan_text, ''),
        'problem_statement': section_text(plan_text, ['problem statement'], first_nonempty_line(plan_text, '')),
        'hypotheses': hypotheses,
        'candidate_solutions': candidate_solutions,
        'solution_comparison': solution_comparison,
        'recommended_solution': recommendation or first_nonempty_line(plan_text, ''),
        'recommendation_basis': recommendation_basis,
        'why_not_others': section_text(plan_text, ['why not others'], ''),
        'applicability_conditions': applicability_conditions,
        'code_touchpoints': code_touchpoints,
        'change_priority': change_priority,
        'backtest_handoff': backtest_handoff,
        'parameter_handoff': parameter_handoff,
        'factor_handoff': factor_handoff,
        'failure_scenarios': failure_scenarios,
        'validation_path': validation_path,
        'validation_priority': validation_priority,
        'risk_notes': risk_notes,
        'target_files': normalized_request.get('target_files', []),
        'depth_metrics': _depth_metrics(
            hypotheses=len(hypotheses),
            candidate_solutions=len(candidate_solutions),
            solution_comparison=len(solution_comparison),
            recommendation_basis=len(recommendation_basis),
            applicability_conditions=len(applicability_conditions),
            code_touchpoints=len(code_touchpoints),
            change_priority=len(change_priority),
            backtest_handoff=len(backtest_handoff),
            parameter_handoff=len(parameter_handoff),
            factor_handoff=len(factor_handoff),
            failure_scenarios=len(failure_scenarios),
            validation_path=len(validation_path),
            validation_priority=len(validation_priority),
            risk_notes=len(risk_notes),
        ),
    }


def build_parameter_candidate(task: dict[str, Any], plan_text: str, normalized_request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    sensitive_parameters = section_bullets(plan_text, ['sensitive parameters'], limit=8)
    sensitivity_rationales = section_bullets(plan_text, ['sensitivity rationales'], limit=8)
    robust_ranges = section_bullets(plan_text, ['robust ranges'], limit=8)
    fragile_ranges = section_bullets(plan_text, ['fragile ranges'], limit=8)
    range_justification = section_bullets(plan_text, ['range justification'], limit=8)
    tuning_sequence = section_bullets(plan_text, ['tuning sequence'], limit=8)
    boundary_design = section_bullets(plan_text, ['boundary design'], limit=8)
    metric_guardrails = section_bullets(plan_text, ['metric guardrails'], limit=8)
    code_touchpoints = section_bullets(plan_text, ['code touchpoints'], limit=8)
    change_priority = section_bullets(plan_text, ['change priority'], limit=8)
    backtest_handoff = section_bullets(plan_text, ['backtest handoff'], limit=8)
    validation_plan = section_bullets(plan_text, ['validation plan'], limit=8)
    risk_notes = section_bullets(plan_text, ['risk notes'], limit=8)
    return {
        'task_id': task.get('task_id'),
        'objective': task.get('objective', ''),
        'mode': result.get('mode'),
        'model': result.get('model'),
        'candidate_summary': first_nonempty_line(section_text(plan_text, ['parameter objective'], '') or plan_text, ''),
        'parameter_objective': section_text(plan_text, ['parameter objective'], first_nonempty_line(plan_text, '')),
        'sensitive_parameters': sensitive_parameters,
        'sensitivity_rationales': sensitivity_rationales,
        'robust_ranges': robust_ranges,
        'fragile_ranges': fragile_ranges,
        'range_justification': range_justification,
        'tuning_sequence': tuning_sequence,
        'boundary_design': boundary_design,
        'metric_guardrails': metric_guardrails,
        'code_touchpoints': code_touchpoints,
        'change_priority': change_priority,
        'backtest_handoff': backtest_handoff,
        'validation_plan': validation_plan,
        'risk_notes': risk_notes,
        'target_files': normalized_request.get('target_files', []),
        'depth_metrics': _depth_metrics(
            sensitive_parameters=len(sensitive_parameters),
            sensitivity_rationales=len(sensitivity_rationales),
            robust_ranges=len(robust_ranges),
            fragile_ranges=len(fragile_ranges),
            range_justification=len(range_justification),
            tuning_sequence=len(tuning_sequence),
            metric_guardrails=len(metric_guardrails),
            code_touchpoints=len(code_touchpoints),
            change_priority=len(change_priority),
            backtest_handoff=len(backtest_handoff),
            validation_plan=len(validation_plan),
        ),
    }


def build_factor_candidate(task: dict[str, Any], plan_text: str, normalized_request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    recommendation = section_text(plan_text, ['recommendation'], '')
    factor_hypotheses = section_bullets(plan_text, ['factor hypotheses'], limit=8)
    economic_rationales = section_bullets(plan_text, ['economic rationales'], limit=8)
    candidate_factors = section_bullets(plan_text, ['candidate factors'], limit=8)
    applicability_conditions = section_bullets(plan_text, ['applicability conditions'], limit=8)
    code_touchpoints = section_bullets(plan_text, ['code touchpoints'], limit=8)
    strategy_handoff = section_bullets(plan_text, ['strategy handoff'], limit=8)
    parameter_handoff = section_bullets(plan_text, ['parameter handoff'], limit=8)
    failure_scenarios = section_bullets(plan_text, ['failure scenarios'], limit=8)
    validation_plan = section_bullets(plan_text, ['validation plan'], limit=8)
    validation_priority = section_bullets(plan_text, ['validation priority'], limit=8)
    overlap_risks = section_bullets(plan_text, ['overlap risks'], limit=8)
    return {
        'task_id': task.get('task_id'),
        'objective': task.get('objective', ''),
        'mode': result.get('mode'),
        'model': result.get('model'),
        'factor_summary': first_nonempty_line(recommendation or plan_text, ''),
        'factor_hypotheses': factor_hypotheses,
        'economic_rationales': economic_rationales,
        'candidate_factors': candidate_factors,
        'applicability_conditions': applicability_conditions,
        'code_touchpoints': code_touchpoints,
        'strategy_handoff': strategy_handoff,
        'parameter_handoff': parameter_handoff,
        'failure_scenarios': failure_scenarios,
        'validation_plan': validation_plan,
        'validation_priority': validation_priority,
        'overlap_risks': overlap_risks,
        'recommendation': recommendation or first_nonempty_line(plan_text, ''),
        'target_files': normalized_request.get('target_files', []),
        'depth_metrics': _depth_metrics(
            factor_hypotheses=len(factor_hypotheses),
            economic_rationales=len(economic_rationales),
            candidate_factors=len(candidate_factors),
            applicability_conditions=len(applicability_conditions),
            code_touchpoints=len(code_touchpoints),
            strategy_handoff=len(strategy_handoff),
            parameter_handoff=len(parameter_handoff),
            failure_scenarios=len(failure_scenarios),
            validation_plan=len(validation_plan),
            validation_priority=len(validation_priority),
        ),
    }
