#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后续闭包处理器 - 处理超时和未完成项目，形成闭环或重试机制
Follow-up Closer - Process timeout and incomplete items, form closure or retry mechanism
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class FollowUpCloser:
    """后续闭包处理器"""
    
    def __init__(self):
        self.workspace = Path("/home/admin/.openclaw/workspace/master")
        self.closures_dir = self.workspace / "traces" / "closures"
        self.closures_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_closure_record(self, request_id: str, execution_result: Dict[str, Any], closure_type: str = "minimal") -> Dict[str, Any]:
        """
        生成闭包记录
        - 至少产出最小 closure/result record
        - 记录执行结果和状态
        - 为后续处理提供依据
        """
        closure_record = {
            "closure_id": f"CLOSURE-{request_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "request_id": request_id,
            "executor_type": execution_result.get("executor_type", "unknown"),
            "closure_type": closure_type,
            "result_summary": execution_result.get("result_summary", "Execution completed without detailed summary"),
            "status": "completed" if execution_result.get("success", False) else "failed",
            "execution_success": execution_result.get("success", False),
            "generated_at": datetime.now().isoformat(),
            "artifacts_referenced": execution_result.get("artifacts_generated", []),
            "execution_log_summary": self._extract_log_summary(execution_result.get("execution_log", [])),
            "execution_result_binding": execution_result,  # 显式绑定原始执行结果
            "next_action": self._determine_next_action(execution_result),
            "followup_required": self._requires_followup(execution_result),
            "closure_reason": self._determine_closure_reason(execution_result),
            "version": "1.0.0",
            "checksum": self._calculate_checksum(execution_result),
            "metadata": {
                "source": "followup_closer",
                "generator": "FollowUpCloser.generate_closure_record",
                "trace_path": f"traces/closures/{request_id}/closure_record.json"
            }
        }
        
        # 保存闭包记录
        closure_dir = self.closures_dir / request_id
        closure_dir.mkdir(parents=True, exist_ok=True)
        
        closure_file = closure_dir / "closure_record.json"
        with open(closure_file, 'w', encoding='utf-8') as f:
            json.dump(closure_record, f, ensure_ascii=False, indent=2)
        
        # 创建闭包摘要
        summary_file = closure_dir / "closure_summary.json"
        summary = {
            "request_id": request_id,
            "closure_id": closure_record["closure_id"],
            "status": closure_record["status"],
            "execution_success": closure_record["execution_success"],
            "artifacts_count": len(closure_record["artifacts_referenced"]),
            "next_action": closure_record["next_action"],
            "followup_required": closure_record["followup_required"],
            "generated_at": closure_record["generated_at"],
            "summary_version": "1.0.0"
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return closure_record
    
    def _extract_log_summary(self, execution_log: List[str]) -> str:
        """提取执行日志摘要"""
        if not execution_log:
            return "No execution log available"
        
        # 提取前几条和后几条日志作为摘要
        if len(execution_log) <= 6:
            return "\\n".join(execution_log)
        else:
            prefix = "\\n".join(execution_log[:3])
            suffix = "\\n".join(execution_log[-3:])
            return f"{prefix}\\n... ({len(execution_log)-6} more entries) ...\\n{suffix}"
    
    def _determine_next_action(self, execution_result: Dict[str, Any]) -> str:
        """确定下一步动作"""
        if execution_result.get("success", False):
            return "notify_completion"
        else:
            error_report = execution_result.get("error_report", {})
            if error_report and "retryable" in str(error_report).lower():
                return "schedule_retry"
            else:
                return "manual_intervention_required"
    
    def _requires_followup(self, execution_result: Dict[str, Any]) -> bool:
        """判断是否需要后续处理"""
        if not execution_result.get("success", False):
            error_report = execution_result.get("error_report", {})
            return bool(error_report)  # 有错误报告通常需要后续处理
        return False
    
    def _determine_closure_reason(self, execution_result: Dict[str, Any]) -> str:
        """确定闭包原因"""
        if execution_result.get("success", False):
            return "execution_completed_successfully"
        else:
            error_report = execution_result.get("error_report", {})
            if error_report:
                return f"execution_failed: {str(error_report.get('error', 'unknown_error'))}"
            else:
                return "execution_failed_no_detailed_error"
    
    def _calculate_checksum(self, execution_result: Dict[str, Any]) -> str:
        """计算校验和"""
        import hashlib
        import json
        normalized_data = json.dumps(execution_result, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized_data.encode('utf-8')).hexdigest()[:16]
    
    def process_timeout_item(self, request_id: str, timeout_reason: str = "execution_timeout") -> Dict[str, Any]:
        """处理超时项目"""
        timeout_closure = {
            "closure_id": f"TIMEOUT-{request_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "request_id": request_id,
            "closure_type": "timeout_closure",
            "result_summary": f"Request timed out: {timeout_reason}",
            "status": "timeout",
            "execution_success": False,
            "timeout_reason": timeout_reason,
            "generated_at": datetime.now().isoformat(),
            "artifacts_referenced": [],
            "execution_log_summary": f"Request {request_id} timed out after exceeding maximum allowed duration",
            "next_action": "investigate_timeout_cause_and_schedule_retry",
            "followup_required": True,
            "closure_reason": f"timeout: {timeout_reason}",
            "version": "1.0.0",
            "metadata": {
                "source": "followup_closer_timeout_handler",
                "generator": "FollowUpCloser.process_timeout_item",
                "trace_path": f"traces/closures/{request_id}/timeout_closure.json"
            }
        }
        
        # 保存超时闭包记录
        closure_dir = self.closures_dir / request_id
        closure_dir.mkdir(parents=True, exist_ok=True)
        
        timeout_file = closure_dir / "timeout_closure.json"
        with open(timeout_file, 'w', encoding='utf-8') as f:
            json.dump(timeout_closure, f, ensure_ascii=False, indent=2)
        
        return timeout_closure
    
    def process_failed_item(self, request_id: str, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """处理失败项目"""
        failure_closure = {
            "closure_id": f"FAILED-{request_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "request_id": request_id,
            "closure_type": "failure_closure",
            "result_summary": f"Request failed: {failure_details.get('error', 'unknown_error')}",
            "status": "failed",
            "execution_success": False,
            "failure_details": failure_details,
            "generated_at": datetime.now().isoformat(),
            "artifacts_referenced": [],
            "execution_log_summary": f"Request {request_id} failed with error: {failure_details.get('error', 'unknown_error')}",
            "next_action": "analyze_failure_and_decide_retry_or_manual_intervention",
            "followup_required": True,
            "closure_reason": f"failure: {failure_details.get('error', 'unknown_error')}",
            "version": "1.0.0",
            "metadata": {
                "source": "followup_closer_failure_handler",
                "generator": "FollowUpCloser.process_failed_item",
                "trace_path": f"traces/closures/{request_id}/failure_closure.json"
            }
        }
        
        # 保存失败闭包记录
        closure_dir = self.closures_dir / request_id
        closure_dir.mkdir(parents=True, exist_ok=True)
        
        failure_file = closure_dir / "failure_closure.json"
        with open(failure_file, 'w', encoding='utf-8') as f:
            json.dump(failure_closure, f, ensure_ascii=False, indent=2)
        
        return failure_closure


def generate_followup_closure(request_id: str, execution_result: Dict[str, Any], closure_type: str = "minimal") -> Dict[str, Any]:
    """生成后续闭包的便捷函数"""
    closer = FollowUpCloser()
    return closer.generate_closure_record(request_id, execution_result, closure_type)


def process_timeout_followup(request_id: str, timeout_reason: str = "execution_timeout") -> Dict[str, Any]:
    """处理超时后续的便捷函数"""
    closer = FollowUpCloser()
    return closer.process_timeout_item(request_id, timeout_reason)


def process_failed_followup(request_id: str, failure_details: Dict[str, Any]) -> Dict[str, Any]:
    """处理失败后续的便捷函数"""
    closer = FollowUpCloser()
    return closer.process_failed_item(request_id, failure_details)


if __name__ == "__main__":
    # 示例闭包生成
    request_id = "REQ-20260331-1205-CLOSURE-TEST"
    
    # 模拟执行结果
    execution_result = {
        "success": True,
        "executor_type": "release",
        "result_summary": "Mock execution completed successfully",
        "artifacts_generated": ["artifact1.txt", "artifact2.json"],
        "execution_log": [
            f"[{datetime.now().isoformat()}] Started mock execution",
            f"[{datetime.now().isoformat()}] Validated parameters",
            f"[{datetime.now().isoformat()}] Completed mock execution (no real changes made)"
        ]
    }
    
    closure = generate_followup_closure(request_id, execution_result)
    print("Closure record generated:")
    print(json.dumps(closure, ensure_ascii=False, indent=2))
    
    # 示例超时处理
    timeout_closure = process_timeout_followup(request_id, "execution_timeout")
    print("\\nTimeout closure generated:")
    print(json.dumps(timeout_closure, ensure_ascii=False, indent=2))