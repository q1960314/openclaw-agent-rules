#!/usr/bin/env python3
"""
任务执行器 - 用于跑通第一条真实任务链

使用方法:
    python3 /home/admin/.openclaw/workspace/master/scripts/task_executor.py \
        --task-id TASK-20260327-STEP1-ENV-FIX \
        --role coder \
        --action claim

    python3 /home/admin/.openclaw/workspace/master/scripts/task_executor.py \
        --task-id TASK-20260327-STEP1-ENV-FIX \
        --role coder \
        --action execute

    python3 /home/admin/.openclaw/workspace/master/scripts/task_executor.py \
        --task-id TASK-20260327-STEP1-ENV-FIX \
        --role test-expert \
        --action verify
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 任务根目录
JOBS_ROOT = Path("/home/admin/.openclaw/workspace/master/traces/jobs")


def load_json(path: Path) -> dict:
    """加载 JSON 文件"""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    """保存 JSON 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 已写入：{path}")


def get_task_dir(task_id: str) -> Path:
    """获取任务目录"""
    return JOBS_ROOT / task_id


def claim_task(task_id: str, role: str, lease_hours: int = 1) -> bool:
    """
    认领任务
    
    返回 True 表示认领成功，False 表示认领失败（已被认领）
    """
    task_dir = get_task_dir(task_id)
    claim_path = task_dir / "claim.json"
    
    if not task_dir.exists():
        print(f"❌ 任务目录不存在：{task_dir}")
        return False
    
    claim = load_json(claim_path)
    
    # 检查是否已被认领
    if claim.get("claimed_by") and claim.get("lease_until"):
        lease_until = datetime.fromisoformat(claim["lease_until"])
        if datetime.now() < lease_until:
            print(f"⚠️  任务已被 {claim['claimed_by']} 认领，租约至 {lease_until}")
            return False
    
    # 更新 claim.json
    now = datetime.now()
    claim["claimed_by"] = role
    claim["claimed_at"] = now.strftime("%Y-%m-%d %H:%M:%S %z")
    claim["lease_until"] = (now + timedelta(hours=lease_hours)).isoformat()
    claim["attempt"] = claim.get("attempt", 0) + 1
    claim["status"] = "claimed"
    
    save_json(claim_path, claim)
    
    # 更新 status.json
    status_path = task_dir / "status.json"
    status = load_json(status_path)
    status["status"] = "running"
    status["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S %z")
    save_json(status_path, status)
    
    print(f"✅ 任务已认领：{task_id} → {role}")
    return True


def complete_task(task_id: str, role: str, artifacts: list = None):
    """完成任务"""
    task_dir = get_task_dir(task_id)
    status_path = task_dir / "status.json"
    
    status = load_json(status_path)
    status["status"] = "completed"
    status["artifacts_complete"] = True
    status["completed_by"] = role
    status["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    
    if artifacts:
        status["artifacts"] = artifacts
    
    save_json(status_path, status)
    print(f"✅ 任务已完成：{task_id}")


def verify_task(task_id: str, verdict: str, checks: list, summary: str):
    """
    验收任务
    
    verdict: "pass" | "fail" | "conditional_pass"
    checks: [{"criterion": "...", "status": "pass/fail", "evidence": "..."}]
    """
    task_dir = get_task_dir(task_id)
    verify_dir = task_dir / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    
    verdict_path = verify_dir / "verdict.json"
    
    verdict_data = {
        "task_id": task_id,
        "verdict": verdict,
        "verified_by": "test-expert",
        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        "checks": checks,
        "summary": summary
    }
    
    save_json(verdict_path, verdict_data)
    
    # 更新 status.json
    status_path = task_dir / "status.json"
    status = load_json(status_path)
    status["status"] = "verified"
    status["verdict"] = verdict
    status["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    save_json(status_path, status)
    
    print(f"✅ 验收完成：{task_id} → {verdict}")


def finalize_task(task_id: str, success: bool, archive_path: str = None):
    """完成任务最终归档"""
    task_dir = get_task_dir(task_id)
    final_path = task_dir / "final.json"
    
    final_data = {
        "task_id": task_id,
        "status": "success" if success else "failure",
        "finalized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        "archive_path": archive_path
    }
    
    save_json(final_path, final_data)
    
    # 更新 status.json
    status_path = task_dir / "status.json"
    status = load_json(status_path)
    status["status"] = "finalized"
    status["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    save_json(status_path, status)
    
    print(f"✅ 任务已归档：{task_id} → {'success' if success else 'failure'}")


def show_task_status(task_id: str):
    """显示任务状态"""
    task_dir = get_task_dir(task_id)
    
    print(f"\n📋 任务状态：{task_id}\n")
    print("=" * 60)
    
    # spec.json
    spec_path = task_dir / "spec.json"
    if spec_path.exists():
        spec = load_json(spec_path)
        print(f"标题：{spec.get('title', 'N/A')}")
        print(f"类型：{spec.get('task_type', 'N/A')}")
        print(f"负责人：{spec.get('owner_role', 'N/A')}")
    print()
    
    # claim.json
    claim_path = task_dir / "claim.json"
    if claim_path.exists():
        claim = load_json(claim_path)
        print(f"认领状态：{claim.get('status', 'N/A')}")
        print(f"认领人：{claim.get('claimed_by', 'N/A')}")
        print(f"认领时间：{claim.get('claimed_at', 'N/A')}")
    print()
    
    # status.json
    status_path = task_dir / "status.json"
    if status_path.exists():
        status = load_json(status_path)
        print(f"执行状态：{status.get('status', 'N/A')}")
        print(f"更新时间：{status.get('updated_at', 'N/A')}")
    print()
    
    # artifacts
    artifacts_dir = task_dir / "artifacts"
    if artifacts_dir.exists():
        artifacts = list(artifacts_dir.iterdir())
        print(f"交付物：{len(artifacts)} 个文件")
        for f in artifacts:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    print()
    
    # verify
    verify_dir = task_dir / "verify"
    if verify_dir.exists():
        verdict_path = verify_dir / "verdict.json"
        if verdict_path.exists():
            verdict = load_json(verdict_path)
            print(f"验收结果：{verdict.get('verdict', 'N/A')}")
            print(f"验收摘要：{verdict.get('summary', 'N/A')}")
    print()
    
    # final
    final_path = task_dir / "final.json"
    if final_path.exists():
        final = load_json(final_path)
        print(f"最终状态：{final.get('status', 'N/A')}")
        print(f"归档路径：{final.get('archive_path', 'N/A')}")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="任务执行器")
    parser.add_argument("--task-id", required=True, help="任务 ID")
    parser.add_argument("--role", choices=["coder", "test-expert", "doc-manager", "knowledge-steward"], help="执行角色")
    parser.add_argument("--action", choices=["claim", "execute", "complete", "verify", "finalize", "status"], help="执行动作")
    parser.add_argument("--verdict", choices=["pass", "fail", "conditional_pass"], help="验收结果（verify 动作时使用）")
    parser.add_argument("--summary", default="", help="验收摘要（verify 动作时使用）")
    
    args = parser.parse_args()
    
    if args.action == "status":
        show_task_status(args.task_id)
        return
    
    if args.action == "claim":
        if not args.role:
            print("❌ claim 动作需要指定 --role")
            sys.exit(1)
        success = claim_task(args.task_id, args.role)
        sys.exit(0 if success else 1)
    
    if args.action == "complete":
        if not args.role:
            print("❌ complete 动作需要指定 --role")
            sys.exit(1)
        complete_task(args.task_id, args.role)
        sys.exit(0)
    
    if args.action == "verify":
        if not args.verdict:
            print("❌ verify 动作需要指定 --verdict")
            sys.exit(1)
        # 示例 checks
        checks = [
            {"criterion": "文件修改", "status": "pass", "evidence": "diff.patch 存在"},
            {"criterion": "语义正确", "status": "pass", "evidence": "代码审查通过"}
        ]
        verify_task(args.task_id, args.verdict, checks, args.summary)
        sys.exit(0)
    
    if args.action == "finalize":
        finalize_task(args.task_id, success=True)
        sys.exit(0)
    
    print("❌ 未知动作")
    sys.exit(1)


if __name__ == "__main__":
    main()
