# Task Object Schema（最小版）

## 目录结构

```text
traces/jobs/
└── TASK-YYYYMMDD-XXXX/
    ├── spec.json
    ├── status.json
    ├── claim.json
    ├── artifacts/
    ├── verify/
    │   └── verdict.json
    ├── approval/
    │   └── approval.json
    └── final.json
```

## 状态机
- queued
- claimed
- running
- artifact_ready
- verifying
- awaiting_approval
- completed
- failed
- blocked
- stale
- archived

## spec.json
```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "task_type": "code_fix",
  "title": "修复 Step 1 环境入口问题",
  "owner_role": "coder",
  "validator_role": "test-expert",
  "source_cycle": "manual",
  "input_refs": [
    "scripts/workflow_run_opencode.py",
    "scripts/workflow_run_execution_opencode.py",
    "config/ecosystem.crontab.example"
  ],
  "required_artifacts": [
    "diff.patch",
    "changed_files.json",
    "verify/verdict.json"
  ],
  "approval_policy": "manual_if_merge",
  "next_on_success": "DOC-AND-ARCHIVE",
  "next_on_failure": "REPAIR-OR-RETRY",
  "retry_policy": {
    "max_attempts": 2,
    "backoff_sec": 300
  }
}
```

## status.json
```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "status": "queued",
  "retry_count": 0,
  "blocked_reason": null,
  "next_retry_at": null,
  "updated_at": "2026-03-27 18:27:47 +0800"
}
```

## claim.json
```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "claimed_by": null,
  "claimed_at": null,
  "lease_until": null,
  "attempt": 0,
  "status": "unclaimed"
}
```

## verify/verdict.json
```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "validator": "test-expert",
  "artifact_check": "pending",
  "string_check": "pending",
  "semantic_check": "pending",
  "runtime_check": "pending",
  "final_verdict": "pending",
  "reason": null
}
```

## final.json
```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "final_status": "open",
  "owner_role": "coder",
  "validator_role": "test-expert",
  "approval_status": "not_required_yet",
  "archived": false,
  "closed_at": null
}
```
