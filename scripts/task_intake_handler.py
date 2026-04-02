#!/usr/bin/env python3
"""
真实任务监听与处理入口
此脚本提供一个可由 master agent 调用的结构化接口，用于接收和处理任务
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Define Any here to avoid import issues
from typing import Any

# 添加工作目录到路径
WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from task_queue import create_task


class TaskIntakeHandler:
    """任务接收处理器 - 提供结构化任务入口"""
    
    def __init__(self, workspace_root=None):
        self.workspace = workspace_root or WORKSPACE_ROOT
        self.intake_dir = self.workspace / "traces" / "intake"
        self.intake_dir.mkdir(parents=True, exist_ok=True)
    
    def get_next_task_for_master_agent(self) -> Optional[Dict[str, Any]]:
        """
        获取下一个待处理任务 - 供 master agent 调用
        返回任务信息供 master agent 决定如何调度
        """
        from task_queue import JOBS_ROOT
        import json
        
        # 检查队列中的任务
        for task_file in JOBS_ROOT.glob("TASK-*/*/spec.json"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    spec = json.load(f)
                
                task_id = task_file.parent.name
                status_file = task_file.parent / "status.json"
                
                if status_file.exists():
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    
                    # 检查是否是待处理任务
                    if status.get("status") == "queued":
                        return {
                            "task_id": task_id,
                            "task_type": spec.get("task_type"),
                            "owner_role": spec.get("owner_role"),
                            "validator_role": spec.get("validator_role"),
                            "required_artifacts": spec.get("required_artifacts", []),
                            "success_criteria": spec.get("success_criteria", []),
                            "spec": spec,
                            "status": status
                        }
            except Exception:
                continue
        
        # 如果没有待处理任务，返回 None
        return None
    
    def mark_task_as_dispatched_by_master(self, task_id: str, dispatched_by: str = "master-agent") -> bool:
        """
        标记任务已被 master agent 分派 - 供 master agent 调用
        """
        from task_queue import JOBS_ROOT
        import json
        
        status_file = JOBS_ROOT / task_id / "status.json"
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                # 更新状态
                status["status"] = "dispatched_by_master"
                status["dispatched_by"] = dispatched_by
                status["dispatched_at"] = datetime.now().isoformat()
                
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception:
                return False
        
        return False
    
    def intake_task_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收任务请求并将其放入队列
        这是可由 master agent 调用的真实入口
        """
        try:
            # 验证请求数据
            required_fields = ["request", "task_type", "owner_role"]
            missing_fields = [field for field in required_fields if field not in request_data]
            
            if missing_fields:
                return {
                    "success": False,
                    "error": f"缺少必需字段: {missing_fields}",
                    "task_id": None
                }
            
            # 生成任务ID
            task_id = f"INTAKE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{hash(str(request_data)) % 10000:04d}"
            
            # 设置默认值
            owner_role = request_data.get("owner_role", "coder")
            validator_role = request_data.get("validator_role", "test-expert")
            input_refs = request_data.get("input_refs", [])
            success_criteria = request_data.get("success_criteria", ["任务完成"])
            next_roles = request_data.get("next_roles", [])
            
            # 确定所需 artifacts
            required_artifacts = self._get_required_artifacts(
                request_data.get("task_type", "general"), 
                owner_role
            )
            
            # 创建任务
            success = create_task(
                task_id=task_id,
                task_type=request_data["task_type"],
                title=request_data.get("title", request_data["request"][:50]),
                owner_role=owner_role,
                validator_role=validator_role,
                input_refs=input_refs,
                required_artifacts=required_artifacts,
                success_criteria=success_criteria
            )
            
            if success:
                # 记录任务到 intake 日志
                intake_record = {
                    "task_id": task_id,
                    "request": request_data["request"],
                    "task_type": request_data["task_type"],
                    "owner_role": owner_role,
                    "received_at": datetime.now().isoformat(),
                    "next_roles": next_roles,
                    "status": "queued"
                }
                
                intake_file = self.intake_dir / f"{task_id}_intake.json"
                with open(intake_file, 'w', encoding='utf-8') as f:
                    json.dump(intake_record, f, ensure_ascii=False, indent=2)
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 {task_id} 已成功加入队列，分配给 {owner_role}",
                    "next_roles": next_roles
                }
            else:
                return {
                    "success": False,
                    "error": "任务创建失败",
                    "task_id": task_id
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"处理任务请求时出错: {str(e)}",
                "task_id": None
            }
    
    def _get_required_artifacts(self, task_type: str, owner_role: str) -> list:
        """获取特定任务类型和角色所需的 artifacts"""
        artifacts_map = {
            "code_fix": {
                "coder": ["diff.patch", "changed_files.json", "run.log"],
                "test-expert": ["verdict.json", "test_report.md"],
                "doc-manager": ["delivery_pack.md", "doc_path.txt"],
                "knowledge-steward": ["kb_write.json", "kb_index_update.json"]
            },
            "strategy_review": {
                "strategy-expert": ["strategy_review.md", "strategy_candidate.json"],
                "test-expert": ["verdict.json", "test_report.md"],
                "doc-manager": ["delivery_pack.md", "doc_path.txt"],
                "knowledge-steward": ["kb_write.json", "kb_index_update.json"]
            },
            "backtest": {
                "backtest-engine": ["metrics.json", "report.md", "run.log"],
                "test-expert": ["verdict.json", "test_report.md"],
                "doc-manager": ["delivery_pack.md", "doc_path.txt"],
                "knowledge-steward": ["kb_write.json", "kb_index_update.json"]
            },
            "general": {
                "coder": ["diff.patch", "changed_files.json", "run.log"],
                "test-expert": ["verdict.json", "test_report.md"],
                "doc-manager": ["delivery_pack.md", "doc_path.txt"],
                "knowledge-steward": ["kb_write.json", "kb_index_update.json"]
            }
        }
        
        return artifacts_map.get(task_type, {}).get(owner_role, ["result.md"])
    
    def process_intake_from_file(self, file_path: str) -> Dict[str, Any]:
        """从文件处理任务请求"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                request_data = json.load(f)
            
            return self.intake_task_request(request_data)
        except Exception as e:
            return {
                "success": False,
                "error": f"从文件读取任务请求时出错: {str(e)}",
                "task_id": None
            }
    
    def get_pending_intakes(self) -> list:
        """获取待处理的 intake 记录"""
        pending = []
        for intake_file in self.intake_dir.glob("*_intake.json"):
            with open(intake_file, 'r', encoding='utf-8') as f:
                intake_data = json.load(f)
                pending.append(intake_data)
        return pending


def handle_intake_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理任务请求的便捷函数
    可由 master agent 直接调用
    """
    handler = TaskIntakeHandler()
    return handler.intake_task_request(request_data)


def handle_intake_from_file(file_path: str) -> Dict[str, Any]:
    """
    从文件处理任务请求的便捷函数
    """
    handler = TaskIntakeHandler()
    return handler.process_intake_from_file(file_path)


# 如果直接运行此脚本，用于测试
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="任务接收处理器")
    parser.add_argument("--request", type=str, help="任务请求JSON字符串")
    parser.add_argument("--file", type=str, help="任务请求JSON文件路径")
    
    args = parser.parse_args()
    
    if args.request:
        try:
            request_data = json.loads(args.request)
            result = handle_intake_request(request_data)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"JSON解析错误: {str(e)}"
            }, ensure_ascii=False, indent=2))
    
    elif args.file:
        result = handle_intake_from_file(args.file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        # 示例请求
        example_request = {
            "request": "修复 workflow_run_opencode.py 中的命令路径问题",
            "task_type": "code_fix",
            "owner_role": "coder",
            "validator_role": "test-expert",
            "input_refs": [],
            "success_criteria": ["路径问题已修复", "代码可正常运行"],
            "next_roles": ["test-expert", "doc-manager"]
        }
        
        result = handle_intake_request(example_request)
        print(json.dumps(result, ensure_ascii=False, indent=2))