#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行结果接收处理器 - 基于 request_id 关联执行结果，具有幂等语义
Execution Receipt Processor - Correlate execution results based on request_id with idempotent semantics
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ReceiptProcessor:
    """执行结果接收处理器"""
    
    def __init__(self):
        self.workspace = Path("/home/admin/.openclaw/workspace/master")
        self.receipts_dir = self.workspace / "traces" / "receipts"
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
    
    def ingest_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收执行结果
        - 基于 request_id 进行关联
        - 具有幂等语义（重复接收不会产生副作用）
        - 返回处理结果
        """
        request_id = receipt_data.get("request_id")
        if not request_id:
            return {
                "success": False,
                "error": "Missing request_id in receipt data",
                "processed_at": datetime.now().isoformat()
            }
        
        # 验证receipt数据结构
        required_fields = ["executor_type", "execution_result", "executed_at"]
        missing_fields = [field for field in required_fields if field not in receipt_data]
        if missing_fields:
            return {
                "success": False,
                "error": f"Missing required fields in receipt: {missing_fields}",
                "processed_at": datetime.now().isoformat()
            }
        
        # 检查是否已处理过此receipt（幂等性保证）
        receipt_file = self.receipts_dir / request_id / "receipt.json"
        if receipt_file.exists():
            existing_receipt = self._load_receipt(request_id)
            if existing_receipt:
                return {
                    "success": True,
                    "status": "already_processed",
                    "request_id": request_id,
                    "processed_at": datetime.now().isoformat(),
                    "note": "Receipt already processed, maintaining idempotent behavior",
                    "existing_receipt_id": existing_receipt.get("receipt_id"),
                    "idempotent_response": True,
                    "ingested": False  # 重复处理，所以未真正新摄入
                }
        
        # 创建receipt目录
        receipt_dir = self.receipts_dir / request_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建完整receipt记录
        receipt_record = {
            "receipt_id": f"RCPT-{request_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "request_id": request_id,
            "executor_type": receipt_data.get("executor_type"),
            "execution_result": receipt_data.get("execution_result"),
            "executed_at": receipt_data.get("executed_at", datetime.now().isoformat()),
            "receipt_processed_at": datetime.now().isoformat(),
            "correlation_key": request_id,
            "checksum": self._calculate_checksum(receipt_data),
            "artifacts_generated": receipt_data.get("artifacts_generated", []),
            "execution_log": receipt_data.get("execution_log", []),
            "status": "processed",
            "version": "1.0.0"
        }
        
        # 保存receipt到文件
        with open(receipt_file, 'w', encoding='utf-8') as f:
            json.dump(receipt_record, f, ensure_ascii=False, indent=2)
        
        # 创建receipt摘要
        summary_file = receipt_dir / "receipt_summary.json"
        summary = {
            "request_id": request_id,
            "receipt_id": receipt_record["receipt_id"],
            "executor_type": receipt_record["executor_type"],
            "execution_status": "success" if receipt_data.get("execution_result", {}).get("success", False) else "failed",
            "executed_at": receipt_record["executed_at"],
            "receipt_processed_at": receipt_record["receipt_processed_at"],
            "artifacts_count": len(receipt_record["artifacts_generated"]),
            "log_entries_count": len(receipt_record["execution_log"]),
            "summary_generated_at": datetime.now().isoformat()
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "status": "newly_processed",
            "request_id": request_id,
            "receipt_id": receipt_record["receipt_id"],
            "processed_at": datetime.now().isoformat(),
            "note": "Receipt successfully ingested and correlated to request",
            "artifacts_saved": len(receipt_record["artifacts_generated"]),
            "idempotent_response": False,  # 首次处理，不是幂等响应
            "ingested": True  # 首次处理，所以已摄入
        }
    
    def _load_receipt(self, request_id: str) -> Optional[Dict[str, Any]]:
        """加载已有的receipt"""
        receipt_file = self.receipts_dir / request_id / "receipt.json"
        if receipt_file.exists():
            try:
                with open(receipt_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _calculate_checksum(self, receipt_data: Dict[str, Any]) -> str:
        """计算校验和以确保幂等性"""
        import hashlib
        import json
        # 对receipt数据进行标准化序列化以生成一致的校验和
        normalized_data = json.dumps(receipt_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized_data.encode('utf-8')).hexdigest()[:16]
    
    def get_receipt_by_request_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """根据request_id获取receipt"""
        receipt_file = self.receipts_dir / request_id / "receipt.json"
        if receipt_file.exists():
            try:
                with open(receipt_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def verify_correlation(self, request_id: str, expected_executor_type: str = None) -> Dict[str, Any]:
        """验证关联性"""
        receipt = self.get_receipt_by_request_id(request_id)
        if not receipt:
            return {
                "request_id": request_id,
                "correlated": False,
                "reason": "No receipt found for request_id",
                "verified_at": datetime.now().isoformat()
            }
        
        correlation_valid = receipt.get("request_id") == request_id
        type_match = not expected_executor_type or receipt.get("executor_type") == expected_executor_type
        
        return {
            "request_id": request_id,
            "correlated": correlation_valid and type_match,
            "receipt_found": True,
            "receipt_id": receipt.get("receipt_id"),
            "executor_type_match": type_match,
            "correlation_key_match": correlation_valid,
            "verified_at": datetime.now().isoformat(),
            "receipt_data": {
                "executor_type": receipt.get("executor_type"),
                "execution_status": "success" if receipt.get("execution_result", {}).get("success") else "failed",
                "executed_at": receipt.get("executed_at")
            }
        }


def process_execution_receipt(receipt_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理执行结果的便捷函数"""
    processor = ReceiptProcessor()
    return processor.ingest_receipt(receipt_data)


def verify_receipt_correlation(request_id: str, expected_executor_type: str = None) -> Dict[str, Any]:
    """验证receipt关联性的便捷函数"""
    processor = ReceiptProcessor()
    return processor.verify_correlation(request_id, expected_executor_type)


if __name__ == "__main__":
    # 示例receipt处理
    example_receipt = {
        "request_id": "REQ-20260331-1155-1234ABCD",
        "executor_type": "release",
        "execution_result": {
            "success": True,
            "simulated_action": "Mock release execution completed",
            "artifacts_generated": ["mock_artifact1.txt", "mock_artifact2.json"]
        },
        "executed_at": datetime.now().isoformat(),
        "artifacts_generated": ["mock_artifact1.txt", "mock_artifact2.json"],
        "execution_log": [
            f"[{datetime.now().isoformat()}] Started mock execution",
            f"[{datetime.now().isoformat()}] Completed mock execution (no real changes)"
        ]
    }
    
    result = process_execution_receipt(example_receipt)
    print(json.dumps(result, ensure_ascii=False, indent=2))