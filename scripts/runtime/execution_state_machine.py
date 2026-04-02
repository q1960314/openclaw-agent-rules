#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行状态机 - 管理 release/rollback 请求的状态流转
Execution State Machine - Manage state transitions for release/rollback requests
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ExecutionStateMachine:
    """执行状态机"""
    
    def __init__(self):
        self.workspace = Path("/home/admin/.openclaw/workspace/master")
        self.states_dir = self.workspace / "traces" / "states"
        self.states_dir.mkdir(parents=True, exist_ok=True)
    
    def transition_state(self, request_id: str, current_state: str, target_state: str, execution_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        状态流转
        - 从 pending -> executing -> completed/failed
        - 记录流转历史
        - 保持状态一致性
        """
        # 验证状态流转是否合法
        valid_transitions = {
            "pending": ["executing", "cancelled"],
            "executing": ["completed", "failed", "timeout", "cancelled"],
            "completed": ["verified", "closed"],
            "failed": ["retry", "closed"],
            "timeout": ["retry", "closed"],
            "retry": ["executing", "cancelled"],
            "cancelled": ["closed"],
            "verified": ["closed"],
            "closed": []
        }
        
        if target_state not in valid_transitions.get(current_state, []):
            return {
                "success": False,
                "error": f"Invalid state transition: {current_state} -> {target_state}",
                "current_state": current_state,
                "attempted_transition": target_state,
                "valid_transitions": valid_transitions[current_state]
            }
        
        # 加载当前状态记录
        state_file = self.states_dir / request_id / "state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_record = json.load(f)
            except Exception:
                state_record = {}
        else:
            state_record = {}
        
        # 更新状态记录
        state_record["request_id"] = request_id
        state_record["current_state"] = target_state
        state_record["previous_state"] = current_state
        state_record["transition_at"] = datetime.now().isoformat()
        state_record["execution_result"] = execution_result or {}
        state_record["state_version"] = state_record.get("state_version", 0) + 1
        
        # 记录流转历史
        transition_history = state_record.get("transition_history", [])
        transition_history.append({
            "from_state": current_state,
            "to_state": target_state,
            "transition_time": datetime.now().isoformat(),
            "transition_reason": "execution_result_received" if execution_result else "manual_transition",
            "execution_summary": {
                "success": execution_result.get("success") if execution_result else None,
                "executor_type": execution_result.get("executor_type") if execution_result else None,
                "artifacts_count": len(execution_result.get("artifacts_generated", [])) if execution_result else 0
            } if execution_result else {}
        })
        state_record["transition_history"] = transition_history
        
        # 更新状态摘要
        transition_at_value = state_record.get("transition_at", datetime.now().isoformat())
        state_record["state_summary"] = {
            "total_transitions": len(transition_history),
            "current_state": target_state,
            "previous_state": current_state,
            "last_transition_at": transition_at_value,
            "execution_success": execution_result.get("success") if execution_result else None,
            "executor_type": execution_result.get("executor_type") if execution_result else None
        }
        
        # 保存状态记录
        state_dir = self.states_dir / request_id
        state_dir.mkdir(parents=True, exist_ok=True)
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_record, f, ensure_ascii=False, indent=2)
        
        # 同时更新任务目录下的状态文件（如果存在）
        job_state_file = self.workspace / "traces" / "jobs" / request_id / "status.json"
        if job_state_file.exists():
            try:
                with open(job_state_file, 'r', encoding='utf-8') as f:
                    job_status = json.load(f)
                job_status["status"] = target_state
                job_status["updated_at"] = datetime.now().isoformat()
                with open(job_state_file, 'w', encoding='utf-8') as f:
                    json.dump(job_status, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 如果无法更新任务状态，继续执行
        
        # 确定是否允许流转
        allowed = target_state in valid_transitions.get(current_state, [])
        
        return {
            "success": True,
            "request_id": request_id,
            "from_state": current_state,
            "to_state": target_state,
            "transitioned_at": state_record.get("transition_at", datetime.now().isoformat()),
            "state_record": state_record,
            "note": f"State transitioned from {current_state} to {target_state} successfully",
            "allowed": allowed,
            "new_state": target_state if allowed else current_state
        }
    
    def get_current_state(self, request_id: str) -> Dict[str, Any]:
        """获取当前状态"""
        state_file = self.states_dir / request_id / "state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_record = json.load(f)
                return {
                    "request_id": request_id,
                    "current_state": state_record.get("current_state", "unknown"),
                    "previous_state": state_record.get("previous_state"),
                    "last_transition_at": state_record.get("transition_at"),
                    "state_version": state_record.get("state_version", 0),
                    "state_exists": True,
                    "state_record": state_record
                }
            except Exception:
                return {
                    "request_id": request_id,
                    "current_state": "unknown",
                    "error": "Failed to read state file",
                    "state_exists": True
                }
        else:
            return {
                "request_id": request_id,
                "current_state": "not_found",
                "error": "State file does not exist",
                "state_exists": False
            }
    
    def initialize_state(self, request_id: str, initial_state: str = "pending", initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """初始化状态"""
        state_file = self.states_dir / request_id / "state.json"
        
        initial_state_record = {
            "request_id": request_id,
            "current_state": initial_state,
            "initial_state": initial_state,
            "previous_state": None,
            "created_at": datetime.now().isoformat(),
            "state_version": 1,
            "transition_history": [],
            "state_summary": {
                "total_transitions": 0,
                "current_state": initial_state,
                "previous_state": None,
                "last_transition_at": None,
                "execution_success": None,
                "executor_type": None
            }
        }
        
        if initial_data:
            initial_state_record.update(initial_data)
        
        # 创建状态目录并保存初始状态
        state_dir = self.states_dir / request_id
        state_dir.mkdir(parents=True, exist_ok=True)
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(initial_state_record, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "request_id": request_id,
            "initial_state": initial_state,
            "current_state": initial_state,
            "new_state": initial_state,
            "allowed": True,  # 初始化总是允许的
            "initialized_at": datetime.now().isoformat(),
            "note": f"Initial state {initial_state} created for request {request_id}"
        }


def transition_execution_state(request_id: str, current_state: str, target_state: str, execution_result: Dict[str, Any] = None) -> Dict[str, Any]:
    """状态流转的便捷函数"""
    sm = ExecutionStateMachine()
    return sm.transition_state(request_id, current_state, target_state, execution_result)


def get_execution_state(request_id: str) -> Dict[str, Any]:
    """获取执行状态的便捷函数"""
    sm = ExecutionStateMachine()
    return sm.get_current_state(request_id)


def initialize_execution_state(request_id: str, initial_state: str = "pending", initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """初始化执行状态的便捷函数"""
    sm = ExecutionStateMachine()
    return sm.initialize_state(request_id, initial_state, initial_data)


if __name__ == "__main__":
    # 示例状态流转
    request_id = "REQ-20260331-1200-INIT-TEST"
    
    # 初始化状态
    init_result = initialize_execution_state(request_id, "pending")
    print("Initialization result:")
    print(json.dumps(init_result, ensure_ascii=False, indent=2))
    
    # 模拟执行结果
    execution_result = {
        "success": True,
        "executor_type": "release",
        "artifacts_generated": ["artifact1.txt", "artifact2.json"],
        "executed_at": datetime.now().isoformat()
    }
    
    # 状态流转：pending -> executing -> completed
    pending_to_executing = transition_execution_state(request_id, "pending", "executing", execution_result)
    print("\\nTransition pending -> executing:")
    print(json.dumps(pending_to_executing, ensure_ascii=False, indent=2))
    
    executing_to_completed = transition_execution_state(request_id, "executing", "completed", execution_result)
    print("\\nTransition executing -> completed:")
    print(json.dumps(executing_to_completed, ensure_ascii=False, indent=2))
    
    # 查询最终状态
    final_state = get_execution_state(request_id)
    print("\\nFinal state:")
    print(json.dumps(final_state, ensure_ascii=False, indent=2))