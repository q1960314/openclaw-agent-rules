#!/usr/bin/env python3
"""
Master Agent Bridge 最小可执行件
可被 master 真实调用的接口
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 工作空间路径
WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
JOBS_ROOT = WORKSPACE_ROOT / "traces" / "jobs"


class MasterBridge:
    """
    Master Agent Bridge - 最小可执行件
    专为 master agent 调用设计
    """
    
    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.bridge_dir = self.workspace / "traces" / "bridge"
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据指定 task_id 获取任务信息
        
        Master 需要传入: task_id (任务ID)
        返回: 任务信息字典或 None
        """
        task_dir = JOBS_ROOT / task_id
        spec_file = task_dir / "spec.json"
        status_file = task_dir / "status.json"
        
        if not task_dir.exists():
            print(f"❌ 任务目录不存在: {task_id}")
            return None
        
        if not spec_file.exists():
            print(f"❌ 任务规范文件不存在: {spec_file}")
            return None
        
        if not status_file.exists():
            print(f"❌ 任务状态文件不存在: {status_file}")
            return None
        
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            
            # 检查任务状态是否允许分派
            if status.get("status") not in ["queued", "pending_dispatch"]:
                print(f"⚠️ 任务 {task_id} 状态不允许分派: {status.get('status')}")
                return None
            
            # 返回任务信息
            return {
                "task_id": task_id,
                "task_type": spec.get("task_type"),
                "owner_role": spec.get("owner_role"),
                "validator_role": spec.get("validator_role"),
                "title": spec.get("title", ""),
                "input_refs": spec.get("input_refs", []),
                "required_artifacts": spec.get("required_artifacts", []),
                "success_criteria": spec.get("success_criteria", []),
                "status": status.get("status"),
                "created_at": spec.get("created_at", status.get("created_at"))
            }
        except Exception as e:
            print(f"❌ 读取任务信息失败 {task_id}: {e}")
            return None

    def get_next_task_for_dispatch(self) -> Optional[Dict[str, Any]]:
        """
        获取下一个待分派的任务
        
        Master 需要传入: 无
        返回: 任务信息字典或 None
        """
        # 搜索队列中的任务
        for task_dir in JOBS_ROOT.iterdir():
            if not task_dir.is_dir() or not task_dir.name.startswith('TASK-'):
                continue
            
            spec_file = task_dir / "spec.json"
            status_file = task_dir / "status.json"
            
            if spec_file.exists() and status_file.exists():
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        spec = json.load(f)
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    
                    # 如果任务状态是 queued，返回任务信息
                    if status.get("status") == "queued":
                        return {
                            "task_id": task_dir.name,
                            "task_type": spec.get("task_type"),
                            "owner_role": spec.get("owner_role"),
                            "validator_role": spec.get("validator_role"),
                            "title": spec.get("title", ""),
                            "input_refs": spec.get("input_refs", []),
                            "required_artifacts": spec.get("required_artifacts", []),
                            "success_criteria": spec.get("success_criteria", [])
                        }
                except Exception:
                    continue
        
        return None
    
    def prepare_task_dispatch_data(self, task_id: str, target_role: str) -> Dict[str, Any]:
        """
        准备任务分派数据 - 供 master agent 调用
        
        Master 需要传入: task_id, target_role
        返回: 分派所需的数据结构
        """
        from scripts.master_dispatcher import MasterDispatcher
        dispatcher = MasterDispatcher()
        return dispatcher.prepare_task_for_dispatch(task_id, target_role)
    
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """
        获取已完成的任务
        
        Master 需要传入: 无
        返回: 完成任务列表
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
                    
                    # 如果任务状态是 completed，添加到结果
                    if status.get("status") == "completed":
                        completed_tasks.append({
                            "task_id": task_dir.name,
                            "task_type": spec.get("task_type"),
                            "owner_role": spec.get("owner_role"),
                            "status": status.get("status"),
                            "completed_at": status.get("updated_at"),
                            "spec": spec
                        })
                except Exception:
                    continue
        
        return completed_tasks
    
    def get_pending_messages(self) -> List[Dict[str, Any]]:
        """
        获取待发送的消息
        
        Master 需要传入: 无
        返回: 待发送消息列表
        """
        # 在当前实现中，我们不创建待发送消息，但提供接口以备将来使用
        return []
    
    def mark_task_as_dispatched(self, task_id: str) -> bool:
        """
        标记任务为已分派
        
        Master 需要传入: task_id (任务ID)
        返回: 是否成功标记
        """
        status_file = JOBS_ROOT / task_id / "status.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                # 更新状态为已分派
                status["status"] = "dispatched_by_master"
                status["dispatched_at"] = datetime.now().isoformat()
                
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception:
                return False
        
        return False
    
    def create_followup_task(self, original_task_id: str, next_role: str, description: str = "") -> Optional[str]:
        """
        创建后续任务
        
        Master 需要传入: original_task_id, next_role, description
        返回: 新任务ID或None
        """
        from scripts.task_queue import create_task
        
        new_task_id = f"FOLLOWUP-{original_task_id}-{next_role[:3]}-{datetime.now().strftime('%H%M%S')}"
        
        success = create_task(
            task_id=new_task_id,
            task_type="followup",
            title=f"Follow-up for {original_task_id} - {next_role}",
            owner_role=next_role,
            validator_role="test-expert",
            input_refs=[f"../{original_task_id}/artifacts"],
            required_artifacts=["result.md"],
            success_criteria=[f"Process follow-up for {original_task_id}"]
        )
        
        return new_task_id if success else None


# 便捷函数 - 供 master agent 直接调用
def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """根据指定 task_id 获取任务信息"""
    bridge = MasterBridge()
    return bridge.get_task_by_id(task_id)


def get_next_task_for_dispatch() -> Optional[Dict[str, Any]]:
    """获取下一个待分派的任务"""
    bridge = MasterBridge()
    return bridge.get_next_task_for_dispatch()


def get_completed_tasks_for_processing() -> List[Dict[str, Any]]:
    """获取待处理的完成任务 - 供 master agent 调用"""
    import sys
    from pathlib import Path
    
    # 确保当前目录在路径中
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from task_result_consumer import TaskResultConsumer
    consumer = TaskResultConsumer()
    return consumer.get_completed_tasks_structured()


def get_pending_messages_for_delivery() -> List[Dict[str, Any]]:
    """获取待发送的消息"""
    bridge = MasterBridge()
    return bridge.get_pending_messages()


def mark_task_dispatched(task_id: str) -> bool:
    """标记任务为已分派"""
    bridge = MasterBridge()
    return bridge.mark_task_as_dispatched(task_id)


def create_followup_task(original_task_id: str, next_role: str, description: str = "") -> Optional[str]:
    """创建后续任务"""
    bridge = MasterBridge()
    return bridge.create_followup_task(original_task_id, next_role, description)


def prepare_task_dispatch_data(task_id: str, target_role: str) -> Dict[str, Any]:
    """准备任务分派数据 - 供 master agent 调用"""
    import sys
    from pathlib import Path
    
    # 确保当前目录在路径中
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from master_dispatcher import MasterDispatcher
    dispatcher = MasterDispatcher()
    return dispatcher.prepare_task_for_dispatch(task_id, target_role)


def get_stable_dispatch_payload(task_id: str, target_role: str) -> Dict[str, Any]:
    """
    获取稳定的分派负载 - 供 master agent 直接使用
    
    返回包含 sessionKey、message、task_id、owner_role 的稳定结构
    """
    # 准备分派数据
    dispatch_data = prepare_task_dispatch_data(task_id, target_role)
    
    if not dispatch_data.get("success"):
        return {
            "success": False,
            "error": dispatch_data.get("error", "Unknown error"),
            "task_id": task_id,
            "owner_role": target_role
        }
    
    # 构建稳定的分派负载
    payload = {
        "success": True,
        "task_id": task_id,
        "owner_role": target_role,
        "sessionKey": dispatch_data.get("session_key", f"agent:{target_role}:main"),
        "message": dispatch_data.get("dispatch_message", {}),
        "prepared_at": dispatch_data.get("prepared_at"),
        "evidence": {
            "source": "master_agent_bridge",
            "dispatch_method": "sessions_send_required",
            "verification_needed": True
        }
    }
    
    return payload


def get_stable_completed_payload(task_id: str = None) -> List[Dict[str, Any]]:
    """
    获取稳定的完成任务负载 - 供 master agent 直接使用
    
    返回包含 task_id、owner_role、verdict、next_action_suggestions 的稳定结构
    """
    completed_tasks = get_completed_tasks_for_processing()
    
    stable_payloads = []
    
    for task in completed_tasks:
        if task_id and task.get("task_id") != task_id:
            continue
            
        # 构建稳定的完成负载
        payload = {
            "task_id": task.get("task_id"),
            "owner_role": task.get("owner_role"),
            "status": task.get("status"),
            "completed_at": task.get("completed_at"),
            "verdict": _extract_verdict_from_verification(task.get("verification_results", [])),
            "next_action_suggestions": task.get("next_action_suggestions", []),
            "artifacts": task.get("artifacts", []),
            "file_paths": {
                "spec_path": f"traces/jobs/{task.get('task_id', '')}/spec.json",
                "status_path": f"traces/jobs/{task.get('task_id', '')}/status.json",
                "artifacts_dir": f"traces/jobs/{task.get('task_id', '')}/artifacts/",
                "verify_dir": f"traces/jobs/{task.get('task_id', '')}/verify/"
            },
            "evidence": {
                "source": "task_result_consumer",
                "verification_results_count": len(task.get("verification_results", [])),
                "next_action_count": len(task.get("next_action_suggestions", []))
            }
        }
        stable_payloads.append(payload)
    
    return stable_payloads


def _extract_verdict_from_verification(verification_results: List[Dict[str, Any]]) -> str:
    """从验证结果中提取verdict"""
    for result in verification_results:
        if result.get("file") == "verdict.json":
            content = result.get("content", {})
            return content.get("verdict", "unknown")
    return "not_available"


def example_usage():
    """使用示例"""
    print("🔍 检查待分派任务...")
    next_task = get_next_task_for_dispatch()
    if next_task:
        print(f"📋 任务: {next_task['task_id']} -> {next_task['owner_role']}")
        print(f"   类型: {next_task['task_type']}")
        print(f"   标题: {next_task['title']}")
        
        # 标记为已分派
        success = mark_task_dispatched(next_task['task_id'])
        print(f"✅ 标记分派状态: {success}")
    
    print("\n🔍 检查已完成任务...")
    completed = get_completed_tasks_for_processing()
    for task in completed[:3]:  # 只显示前3个
        print(f"📊 完成任务: {task['task_id']} -> {task['owner_role']}")
        print(f"   类型: {task['task_type']}")
        print(f"   完成时间: {task['completed_at']}")
    
    if completed:
        # 创建一个后续任务作为示例
        sample_task = completed[0]
        followup_id = create_followup_task(sample_task['task_id'], "test-expert", "验证任务结果")
        if followup_id:
            print(f"\n🔄 创建后续任务: {followup_id}")


if __name__ == "__main__":
    example_usage()