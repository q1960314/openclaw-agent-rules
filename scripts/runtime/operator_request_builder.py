#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作员请求构建器 - 生成全局唯一 request_id 的操作员请求信封
Operator Request Builder - Generate operator request envelope with globally unique request_id
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class OperatorRequestBuilder:
    """操作员请求构建器"""
    
    def __init__(self):
        self.workspace = Path("/home/admin/.openclaw/workspace/master")
    
    def build_request(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建操作员请求信封
        - 生成全局唯一 request_id
        - 包含所有必需的执行参数
        - 保持幂等性（相同输入产生相同结构输出）
        """
        # 生成全局唯一请求ID
        request_id = f"REQ-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        request_envelope = {
            "request_id": request_id,
            "executor_type": spec.get("executor_type", "unknown"),
            "target": spec.get("target"),
            "parameters": spec.get("parameters", {}),
            "validation_results": spec.get("validation_results", {}),
            "request_context": spec.get("request_context", {}),
            "requestor": spec.get("requestor", "system"),
            "priority": spec.get("priority", "normal"),
            "timeout_seconds": spec.get("timeout_seconds", 3600),
            "retry_policy": spec.get("retry_policy", {"max_attempts": 3, "backoff_multiplier": 2}),
            "credential_binding_ref": spec.get("credential_binding_ref"),
            "environment_constraints": spec.get("environment_constraints", {}),
            "artifact_bindings": spec.get("artifact_bindings", []),
            "rollback_plan_ref": spec.get("rollback_plan_ref"),
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.fromtimestamp(datetime.now().timestamp() + spec.get("timeout_seconds", 3600))).isoformat(),
            "status": "pending",
            "version": "1.0.0",
            "checksum": self._calculate_checksum(spec),
            "trace_path": f"traces/requests/{request_id}"
        }
        
        # 确保请求目录存在
        request_dir = self.workspace / "traces" / "requests" / request_id
        request_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存请求到文件
        request_file = request_dir / "request.json"
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_envelope, f, ensure_ascii=False, indent=2)
        
        return request_envelope
    
    def _calculate_checksum(self, spec: Dict[str, Any]) -> str:
        """计算规范校验和以确保幂等性"""
        import hashlib
        import json
        # 对规范进行标准化序列化以生成一致的校验和
        normalized_spec = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized_spec.encode('utf-8')).hexdigest()[:16]
    
    def build_followup_request(self, original_request_id: str, followup_type: str, additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建后续请求
        - 基于原始请求ID构建关联请求
        - 保持与原始请求的关联性
        """
        followup_request_id = f"FOLLOWUP-{original_request_id}-{followup_type.upper()[:3]}-{str(uuid.uuid4())[:8].upper()}"
        
        followup_request = {
            "request_id": followup_request_id,
            "original_request_id": original_request_id,
            "followup_type": followup_type,
            "additional_context": additional_context,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "trace_path": f"traces/requests/{followup_request_id}"
        }
        
        # 保存后续请求到文件
        followup_dir = self.workspace / "traces" / "requests" / followup_request_id
        followup_dir.mkdir(parents=True, exist_ok=True)
        
        followup_file = followup_dir / "request.json"
        with open(followup_file, 'w', encoding='utf-8') as f:
            json.dump(followup_request, f, ensure_ascii=False, indent=2)
        
        return followup_request


def build_operator_request(spec: Dict[str, Any]) -> Dict[str, Any]:
    """构建操作员请求的便捷函数"""
    builder = OperatorRequestBuilder()
    return builder.build_request(spec)


def build_followup_operator_request(original_request_id: str, followup_type: str, additional_context: Dict[str, Any]) -> Dict[str, Any]:
    """构建后续操作员请求的便捷函数"""
    builder = OperatorRequestBuilder()
    return builder.build_followup_request(original_request_id, followup_type, additional_context)


if __name__ == "__main__":
    # 示例请求构建
    example_spec = {
        "executor_type": "release",
        "target": "example_target_file.py",
        "parameters": {
            "version": "1.0.0",
            "deployment_env": "staging"
        },
        "validation_results": {
            "pre_execution_validation_passed": True,
            "security_scan_passed": True
        },
        "request_context": {
            "source": "automated_test",
            "urgency": "normal"
        },
        "timeout_seconds": 1800
    }
    
    request = build_operator_request(example_spec)
    print(f"Generated request_id: {request['request_id']}")
    print(json.dumps(request, ensure_ascii=False, indent=2))