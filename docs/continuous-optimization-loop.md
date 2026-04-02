# Continuous Optimization Loop

This document describes the current multi-round optimization loop skeleton.

## Scope
- Creates a structured intake task via `main_worker`
- Routes the first round via `master_quant_worker`
- Executes the routed worker
- Runs `test_expert_worker` for review
- On pass: hands off to `doc_manager_worker` and `knowledge_steward_worker`
- On reject/fail: creates a retry task when policy allows (`auto_retry_allowed=true` or coder role)

## Entry Script
- `scripts/runtime/continuous_optimization_loop.py`

## Current Limits
- First-class retry currently works best for single-worker iterative loops
- More advanced DAG-style multi-branch orchestration is not implemented yet
- Final formal code promotion still requires human approval
