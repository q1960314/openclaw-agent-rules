#!/usr/bin/env python3
"""
任务结果消费者与决策器
实现 done -> consume -> decide_next 的闭环处理
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Define Any here to avoid import issues
from typing import Any

# 添加工作目录到路径
WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from task_queue import JOBS_ROOT, TaskQueue


class TaskResultConsumer:
    """任务结果消费者 - 处理完成的任务并做决策"""
    
    def __init__(self, workspace_root=None):
        self.workspace = workspace_root or WORKSPACE_ROOT
        self.consumer_dir = self.workspace / "traces" / "consumers"
        self.consumer_dir.mkdir(parents=True, exist_ok=True)
        self.queue = TaskQueue()
    
    def get_completed_tasks_structured(self) -> List[Dict[str, Any]]:
        """
        获取结构化的完成任务 - 供 master agent 消费
        
        返回: 结构化的完成任务列表
        """
        completed_tasks = []
        
        for task_dir in JOBS_ROOT.iterdir():
            if not task_dir.is_dir() or not task_dir.name.startswith('TASK-'):
                continue
                
            status_file = task_dir / "status.json"
            spec_file = task_dir / "spec.json"
            
            if status_file.exists() and spec_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        spec = json.load(f)
                    
                    # 检查是否为已完成任务
                    if status.get("status") in ["completed", "verified"]:
                        # 检查是否有artifacts目录
                        artifacts_dir = task_dir / "artifacts"
                        artifacts = []
                        if artifacts_dir.exists():
                            artifacts = [str(f.name) for f in artifacts_dir.iterdir() if f.is_file()]
                        
                        # 检查是否有verify目录（通常包含验证结果）
                        verify_dir = task_dir / "verify"
                        verification_results = []
                        if verify_dir.exists():
                            for f in verify_dir.iterdir():
                                if f.is_file() and f.name.endswith('.json'):
                                    try:
                                        with open(f, 'r', encoding='utf-8') as vf:
                                            content = json.load(vf)
                                            verification_results.append({
                                                "file": f.name,
                                                "content": content
                                            })
                                    except:
                                        pass
                        
                        task_info = {
                            "task_id": task_dir.name,
                            "task_type": spec.get("task_type"),
                            "owner_role": spec.get("owner_role"),
                            "status": status.get("status"),
                            "completed_at": status.get("updated_at"),
                            "spec": spec,
                            "artifacts": artifacts,
                            "verification_results": verification_results,
                            "next_action_suggestions": self._suggest_next_action(spec, status, verification_results)
                        }
                        completed_tasks.append(task_info)
                        
                except Exception as e:
                    print(f"⚠️ 读取任务状态失败 {task_dir}: {e}")
                    continue
        
        return completed_tasks
    
    def _suggest_next_action(self, spec: Dict[str, Any], status: Dict[str, Any], verification_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        基于任务结果建议下一步操作
        """
        suggestions = []
        
        # 检查验证结果
        for result in verification_results:
            if result["file"] == "verdict.json":
                verdict = result["content"].get("verdict")
                if verdict == "pass":
                    # 任务通过，考虑下一步
                    next_roles = spec.get("next_roles", [])
                    for role in next_roles:
                        suggestions.append({
                            "action": "create_followup_task",
                            "target_role": role,
                            "reason": "Original task passed verification"
                        })
                elif verdict == "fail":
                    suggestions.append({
                        "action": "investigate_failure",
                        "target_role": spec.get("owner_role"),
                        "reason": "Original task failed verification"
                    })
        
        # 如果没有验证结果，基于原始规范建议
        if not suggestions:
            next_roles = spec.get("next_roles", [])
            for role in next_roles:
                suggestions.append({
                    "action": "consider_followup_task",
                    "target_role": role,
                    "reason": "Based on original task specification"
                })
        
        return suggestions
    
    def get_completed_tasks_for_master_agent(self) -> List[Dict[str, Any]]:
        """
        获取已完成的任务 - 供 master agent 调用
        返回已完成的任务列表供 master agent 决策
        """
        completed_tasks = []
        
        for task_dir in JOBS_ROOT.iterdir():
            if not task_dir.is_dir() or task_dir.name.startswith('.'):
                continue
                
            status_file = task_dir / "status.json"
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    
                    # 检查是否为已完成任务
                    if status.get("status") in ["completed", "verified"]:
                        # 加载任务规范
                        spec_file = task_dir / "spec.json"
                        if spec_file.exists():
                            with open(spec_file, 'r', encoding='utf-8') as f:
                                spec = json.load(f)
                            
                            # 检查是否有决策产物
                            decision_file = self.consumer_dir / f"consume_{task_dir.name}_*.json"
                            decision_files = list(self.consumer_dir.glob(f"consume_{task_dir.name}_*.json"))
                            
                            decision_result = None
                            if decision_files:
                                # 获取最新的决策文件
                                latest_decision_file = max(decision_files, key=lambda x: x.stat().st_mtime)
                                with open(latest_decision_file, 'r', encoding='utf-8') as f:
                                    decision_result = json.load(f)
                            
                            task_info = {
                                "task_id": task_dir.name,
                                "status": status,
                                "spec": spec,
                                "task_dir": str(task_dir),
                                "completed_at": status.get("updated_at"),
                                "decision_result": decision_result,  # 包含下一步决策
                                "has_followup_tasks": bool(decision_result and decision_result.get("decision", {}).get("next_actions"))
                            }
                            completed_tasks.append(task_info)
                        
                except Exception as e:
                    print(f"⚠️ 读取任务状态失败 {task_dir}: {e}")
        
        return completed_tasks
    
    def get_next_followup_tasks_for_master_agent(self) -> List[Dict[str, Any]]:
        """
        获取下一个待调度的后续任务 - 供 master agent 调用
        """
        followup_tasks = []
        
        # 查找待处理的后续任务（例如从消费记录中）
        for consume_file in self.consumer_dir.glob("consume_*_decision.json"):
            try:
                with open(consume_file, 'r', encoding='utf-8') as f:
                    consume_record = json.load(f)
                
                decision = consume_record.get("decision", {})
                next_actions = decision.get("next_actions", [])
                
                for action in next_actions:
                    if action.get("action") == "create_task":
                        task_spec = action.get("task_spec", {})
                        if task_spec:
                            followup_tasks.append({
                                "original_task_id": decision.get("task_id"),
                                "next_task_spec": task_spec,
                                "target_role": task_spec.get("owner_role"),
                                "decision_file": str(consume_file)
                            })
            except Exception:
                continue
        
        return followup_tasks
    
    def scan_completed_tasks(self, max_age_minutes: int = 60) -> List[Dict[str, Any]]:
        """扫描已完成的任务"""
        completed_tasks = []
        
        for task_dir in JOBS_ROOT.iterdir():
            if not task_dir.is_dir() or task_dir.name.startswith('.'):
                continue
                
            status_file = task_dir / "status.json"
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    
                    # 检查是否为已完成任务
                    if status.get("status") == "completed":
                        # 检查任务完成时间（如果需要限制时间范围）
                        updated_at = status.get("updated_at", "")
                        # 这里可以添加时间过滤逻辑
                        
                        # 加载任务规范
                        spec_file = task_dir / "spec.json"
                        if spec_file.exists():
                            with open(spec_file, 'r', encoding='utf-8') as f:
                                spec = json.load(f)
                            
                            task_info = {
                                "task_id": task_dir.name,
                                "status": status,
                                "spec": spec,
                                "task_dir": str(task_dir),
                                "completed_at": updated_at
                            }
                            completed_tasks.append(task_info)
                        
                except Exception as e:
                    print(f"⚠️ 读取任务状态失败 {task_dir}: {e}")
        
        return completed_tasks
    
    def consume_task_result(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """消费任务结果并生成决策"""
        task_id = task_info["task_id"]
        spec = task_info["spec"]
        
        print(f" consuming task result: {task_id}")
        
        # 记录消费事件
        consume_record = {
            "task_id": task_id,
            "consumed_at": datetime.now().isoformat(),
            "original_spec": spec,
            "status": task_info["status"],
            "action": "analyzing_next_steps"
        }
        
        # 保存消费记录
        consume_file = self.consumer_dir / f"consume_{task_id}_{datetime.now().strftime('%H%M%S')}.json"
        with open(consume_file, 'w', encoding='utf-8') as f:
            json.dump(consume_record, f, ensure_ascii=False, indent=2)
        
        # 决策逻辑
        decision = self.make_decision(task_info)
        
        # 更新消费记录
        consume_record.update({
            "decision": decision,
            "action": "decision_made"
        })
        
        with open(consume_file, 'w', encoding='utf-8') as f:
            json.dump(consume_record, f, ensure_ascii=False, indent=2)
        
        return decision
    
    def make_decision(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """基于任务结果做决策"""
        task_id = task_info["task_id"]
        spec = task_info["spec"]
        
        # 获取下一个角色（来自原始任务定义或默认）
        next_roles = spec.get("next_roles", [])
        
        decision = {
            "task_id": task_id,
            "original_task_type": spec.get("task_type"),
            "original_owner": spec.get("owner_role"),
            "next_actions": [],
            "decision_timestamp": datetime.now().isoformat()
        }
        
        if next_roles:
            # 创建后续任务
            for i, next_role in enumerate(next_roles):
                next_task_id = f"{task_id}-next-{i+1}-{next_role}"
                
                # 创建后续任务规范
                next_task_spec = {
                    "task_id": next_task_id,
                    "task_type": f"followup_{spec.get('task_type', 'general')}",
                    "title": f"Follow-up for {task_id} - {next_role}",
                    "owner_role": next_role,
                    "validator_role": spec.get("validator_role", "test-expert"),
                    "input_refs": [f"../{task_id}/artifacts"],  # 引用原任务的artifacts
                    "required_artifacts": self._get_followup_artifacts(next_role),
                    "success_criteria": [f"Process artifacts from {task_id}"],
                    "depends_on": task_id,
                    "source_task_type": spec.get("task_type")
                }
                
                decision["next_actions"].append({
                    "action": "create_task",
                    "next_task_id": next_task_id,
                    "next_role": next_role,
                    "task_spec": next_task_spec
                })
        else:
            # 任务完成，无需后续操作
            decision["next_actions"].append({
                "action": "task_complete",
                "message": f"Task {task_id} completed with no further actions required"
            })
        
        return decision
    
    def _get_followup_artifacts(self, role: str) -> List[str]:
        """获取特定角色的后续任务所需 artifacts"""
        artifacts_map = {
            "test-expert": ["verdict.json", "test_report.md"],
            "doc-manager": ["delivery_pack.md", "doc_path.txt"],
            "knowledge-steward": ["kb_write.json", "kb_index_update.json"],
            "strategy-expert": ["analysis.json", "recommendation.md"],
            "backtest-engine": ["metrics.json", "report.md"],
            "coder": ["diff.patch", "changed_files.json"]
        }
        return artifacts_map.get(role, ["result.json", "output.txt"])
    
    def process_completed_tasks(self) -> Dict[str, Any]:
        """处理所有已完成的任务"""
        print("🔍 扫描已完成任务...")
        
        completed_tasks = self.scan_completed_tasks()
        
        results = {
            "scanned_count": len(completed_tasks),
            "processed_tasks": [],
            "decisions": [],
            "errors": []
        }
        
        for task_info in completed_tasks:
            try:
                decision = self.consume_task_result(task_info)
                results["processed_tasks"].append(task_info["task_id"])
                results["decisions"].append(decision)
                
                # 执行决策 - 创建后续任务
                for action in decision.get("next_actions", []):
                    if action["action"] == "create_task":
                        task_spec = action["task_spec"]
                        success = self._create_followup_task(task_spec)
                        action["creation_success"] = success
                        
            except Exception as e:
                error_info = {
                    "task_id": task_info.get("task_id", "unknown"),
                    "error": str(e)
                }
                results["errors"].append(error_info)
                print(f"❌ 处理任务失败 {task_info.get('task_id', 'unknown')}: {e}")
        
        # 保存处理结果
        result_file = self.consumer_dir / f"processing_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return results
    
    def _create_followup_task(self, task_spec: Dict[str, Any]) -> bool:
        """创建后续任务"""
        try:
            from task_queue import create_task
            
            success = create_task(
                task_id=task_spec["task_id"],
                task_type=task_spec["task_type"],
                title=task_spec["title"],
                owner_role=task_spec["owner_role"],
                validator_role=task_spec["validator_role"],
                input_refs=task_spec["input_refs"],
                required_artifacts=task_spec["required_artifacts"],
                success_criteria=task_spec["success_criteria"]
            )
            
            print(f"✅ 后续任务创建: {task_spec['task_id']} -> {task_spec['owner_role']}, 成功: {success}")
            return success
            
        except Exception as e:
            print(f"❌ 创建后续任务失败: {e}")
            return False
    
    def run_consumer_cycle(self) -> Dict[str, Any]:
        """运行一个消费者周期"""
        print("🔄 启动任务结果消费者周期...")
        
        results = self.process_completed_tasks()
        
        summary = {
            "consumer_cycle": datetime.now().isoformat(),
            "summary": {
                "tasks_scanned": results["scanned_count"],
                "tasks_processed": len(results["processed_tasks"]),
                "decisions_made": len(results["decisions"]),
                "errors_encountered": len(results["errors"])
            },
            "details": results
        }
        
        # 保存周期总结
        summary_file = self.consumer_dir / f"consumer_cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"📊 消费者周期完成: {summary['summary']}")
        return summary


def run_consumer_cycle() -> Dict[str, Any]:
    """运行消费者周期的便捷函数"""
    consumer = TaskResultConsumer()
    return consumer.run_consumer_cycle()


def scan_and_consume() -> Dict[str, Any]:
    """扫描并消费的便捷函数"""
    consumer = TaskResultConsumer()
    return consumer.process_completed_tasks()


# 如果直接运行此脚本，执行一个消费者周期
if __name__ == "__main__":
    print("🚀 启动任务结果消费者...")
    
    try:
        result = run_consumer_cycle()
        print(f"✅ 消费者周期完成: {result['summary']}")
    except Exception as e:
        print(f"❌ 消费者周期失败: {e}")
        import traceback
        traceback.print_exc()