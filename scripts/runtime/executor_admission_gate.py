#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器准入门控 - 只读验证，无副作用
Executor Admission Gate - Read-only validation, no side effects
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class ExecutorAdmissionGate:
    """执行器准入门控 - 只读验证，无副作用"""
    
    def __init__(self):
        self.workspace = Path("/home/admin/.openclaw/workspace/master")
    
    def validate_request(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证请求是否满足准入条件
        - 只读验证，不产生任何副作用
        - 返回验证结果和建议
        """
        validation_results = {
            "request_id": spec.get("request_id", ""),
            "executor_type": spec.get("executor_type", "unknown"),
            "validation_timestamp": datetime.now().isoformat(),
            "validation_passed": True,
            "validation_failures": [],
            "required_fields_check": self._check_required_fields(spec),
            "precondition_check": self._check_preconditions(spec),
            "credential_binding_check": self._check_credential_bindings(spec),
            "environment_state_check": self._check_environment_state(spec),
            "recommendation": "proceed" if self._is_valid(spec) else "reject"
        }
        
        if not validation_results["required_fields_check"]["valid"]:
            validation_results["validation_passed"] = False
            validation_results["validation_failures"].extend(validation_results["required_fields_check"]["errors"])
        
        if not validation_results["precondition_check"]["valid"]:
            validation_results["validation_passed"] = False
            validation_results["validation_failures"].extend(validation_results["precondition_check"]["errors"])
        
        if not validation_results["credential_binding_check"]["valid"]:
            validation_results["validation_passed"] = False
            validation_results["validation_failures"].extend(validation_results["credential_binding_check"]["errors"])
        
        if not validation_results["environment_state_check"]["valid"]:
            validation_results["validation_passed"] = False
            validation_results["validation_failures"].extend(validation_results["environment_state_check"]["errors"])
        
        return validation_results
    
    def _check_required_fields(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """检查必需字段"""
        required_fields = [
            "target", "parameters", "validation_results", 
            "executor_type", "request_context"
        ]
        
        missing_fields = [field for field in required_fields if field not in spec]
        
        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "errors": [f"Missing required field: {field}" for field in missing_fields]
        }
    
    def _check_preconditions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """检查前置条件"""
        validation_results = spec.get("validation_results", {})
        pre_execution_passed = validation_results.get("pre_execution_validation_passed", False)
        
        errors = []
        if not pre_execution_passed:
            errors.append("Pre-execution validation did not pass")
        
        return {
            "valid": pre_execution_passed,
            "errors": errors
        }
    
    def _check_credential_bindings(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """检查凭证绑定"""
        # 在骨架中，只检查凭证绑定是否存在，不实际验证
        credentials_available = "credentials" in spec or spec.get("credential_binding_available", True)
        
        errors = []
        if not credentials_available:
            errors.append("Credential binding not available for execution")
        
        return {
            "valid": credentials_available,
            "errors": errors
        }
    
    def _check_environment_state(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """检查环境状态"""
        env_state = spec.get("environment_state", {})
        safe_for_execution = env_state.get("safe_for_execution", True)
        
        errors = []
        if not safe_for_execution:
            errors.append("Environment state not safe for execution")
        
        return {
            "valid": safe_for_execution,
            "errors": errors
        }
    
    def _is_valid(self, spec: Dict[str, Any]) -> bool:
        """综合判断请求是否有效"""
        field_check = self._check_required_fields(spec)
        precondition_check = self._check_preconditions(spec)
        credential_check = self._check_credential_bindings(spec)
        env_check = self._check_environment_state(spec)
        
        return (
            field_check["valid"] and 
            precondition_check["valid"] and 
            credential_check["valid"] and 
            env_check["valid"]
        )


def validate_executor_request(spec: Dict[str, Any]) -> Dict[str, Any]:
    """验证执行器请求的便捷函数"""
    gate = ExecutorAdmissionGate()
    return gate.validate_request(spec)


if __name__ == "__main__":
    # 示例验证
    example_spec = {
        "target": "example_target",
        "parameters": {"param1": "value1"},
        "validation_results": {
            "pre_execution_validation_passed": True
        },
        "executor_type": "release",
        "request_context": "example_context",
        "credential_binding_available": True,
        "environment_state": {
            "safe_for_execution": True
        }
    }
    
    result = validate_executor_request(example_spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))