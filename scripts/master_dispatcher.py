#!/usr/bin/env python3
"""
Master 调度器 - 接收用户需求，分派任务给 Worker，监控执行进度

流程：
1. 接收用户需求
2. 分析并拆解任务
3. 创建任务并推送到队列
4. 唤醒对应 Worker
5. 监控任务状态
6. 根据完成情况决定下一步
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Define Any here to avoid import issues
from typing import Any

import sys
from pathlib import Path

# 确保当前目录在路径中
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from task_queue import TaskQueue, Task, JOBS_ROOT, create_task, claim_task


class MasterDispatcher:
    """Master 调度器"""
    
    def __init__(self, workspace_root=None):
        self.queue = TaskQueue()
        self.workspace = workspace_root or Path("/home/admin/.openclaw/workspace/master")
        self.active_tasks = {}  # 跟踪活跃任务
    
    def get_pending_messages_for_master_agent(self) -> List[Dict[str, Any]]:
        """
        获取待处理的消息 - 供 master agent 调用
        这些消息需要由 master agent 通过 sessions_send 真实发送
        """
        import json
        from pathlib import Path
        
        msg_dir = Path(self.workspace) / "traces" / "messages"
        pending_messages = []
        
        # 查找所有待处理的消息
        for msg_file in msg_dir.glob("pending_message_*.json"):
            try:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    message_data = json.load(f)
                
                if message_data.get("status") == "pending_master_agent_delivery":
                    pending_messages.append({
                        "message_id": msg_file.name,
                        "session_key": message_data["session_key"],
                        "message": message_data["message"],
                        "timestamp": message_data["timestamp"],
                        "file_path": str(msg_file)
                    })
            except Exception:
                continue
        
        return pending_messages
    
    def mark_message_as_delivered_by_master(self, message_id: str, delivery_result: str = "success") -> bool:
        """
        标记消息已由 master agent 发送 - 供 master agent 调用
        """
        import json
        from pathlib import Path
        
        msg_dir = Path(self.workspace) / "traces" / "messages"
        msg_file = msg_dir / message_id
        
        if msg_file.exists():
            try:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    message_data = json.load(f)
                
                # 更新状态
                message_data["status"] = f"delivered_by_master_{delivery_result}"
                message_data["delivered_at"] = datetime.now().isoformat()
                
                # 重命名文件以表示已处理
                delivered_file = msg_dir / f"delivered_{message_id}"
                msg_file.rename(delivered_file)
                
                with open(delivered_file, 'w', encoding='utf-8') as f:
                    json.dump(message_data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception:
                return False
        
        return False
    
    def receive_request(self, request: str) -> dict:
        """
        接收用户需求，分析并返回任务列表
        """
        print(f"📥 接收用户需求：{request[:100]}...")
        
        # 分析需求并拆解任务
        tasks = self._analyze_request(request)
        
        return {"tasks": tasks}
    
    def _analyze_request(self, request: str) -> List[dict]:
        """分析需求并拆解为任务"""
        # 简化实现：根据关键词匹配任务类型
        tasks = []
        
        if "修复" in request or "bug" in request.lower() or "fix" in request.lower():
            # 创建修复任务，需要 coder -> test-expert -> doc-manager 流程
            tasks.append({
                "task_type": "code_fix",
                "owner_role": "coder",
                "validator_role": "test-expert",
                "next_roles": ["test-expert", "doc-manager", "knowledge-steward"]
            })
        
        if "优化" in request or "策略" in request or "strategy" in request.lower():
            tasks.append({
                "task_type": "strategy_review",
                "owner_role": "strategy-expert",
                "validator_role": "test-expert",
                "next_roles": ["test-expert", "doc-manager", "knowledge-steward"]
            })
        
        if "回测" in request or "backtest" in request.lower():
            tasks.append({
                "task_type": "backtest",
                "owner_role": "backtest-engine",
                "validator_role": "test-expert",
                "next_roles": ["doc-manager", "knowledge-steward"]
            })
        
        # 如果没有匹配，创建通用任务
        if not tasks:
            tasks.append({
                "task_type": "general",
                "owner_role": "coder",
                "validator_role": "test-expert",
                "next_roles": ["test-expert", "doc-manager", "knowledge-steward"]
            })
        
        return tasks
    
    def dispatch_task(self, task_def: dict, task_id: str, title: str, input_refs: List[str], success_criteria: List[str]) -> bool:
        """分派任务到队列"""
        required_artifacts = self._get_required_artifacts(task_def["task_type"], task_def["owner_role"])
        
        success = create_task(
            task_id=task_id,
            task_type=task_def["task_type"],
            title=title,
            owner_role=task_def["owner_role"],
            validator_role=task_def["validator_role"],
            input_refs=input_refs,
            required_artifacts=required_artifacts,
            success_criteria=success_criteria
        )
        
        if success:
            # 记录任务到活跃任务列表
            self.active_tasks[task_id] = {
                "task_def": task_def,
                "status": "dispatched",
                "start_time": datetime.now().isoformat(),
                "dependent_tasks": []
            }
        
        return success
    
    def _get_required_artifacts(self, task_type: str, owner_role: str) -> List[str]:
        """获取必需的 artifacts 列表"""
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
    
    def prepare_task_for_dispatch(self, task_id: str, target_role: str) -> Dict[str, Any]:
        """
        准备任务分派数据 - 供 master agent 调用
        不执行实际分派，只准备分派所需的数据
        
        Master 需要传入: task_id, target_role
        返回: 分派所需的数据结构
        """
        from pathlib import Path
        import json
        
        # 加载任务规范
        task_dir = Path(self.workspace) / "traces" / "jobs" / task_id
        spec_file = task_dir / "spec.json"
        status_file = task_dir / "status.json"
        
        # 检查任务是否存在
        if not task_dir.exists():
            return {
                "success": False,
                "error": f"Task directory does not exist: {task_dir}",
                "task_id": task_id
            }
        
        if not spec_file.exists():
            return {
                "success": False,
                "error": f"Task spec not found: {spec_file}",
                "task_id": task_id
            }
        
        # 检查任务状态是否允许分派
        status_data = {}
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read status file: {e}",
                    "task_id": task_id
                }
        
        current_status = status_data.get("status", "unknown")
        if current_status not in ["queued", "pending_dispatch"]:
            return {
                "success": False,
                "error": f"Task {task_id} has invalid status for dispatch: {current_status}",
                "task_id": task_id,
                "current_status": current_status
            }
        
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            
            # 检查任务所有者角色是否匹配
            expected_role = spec.get("owner_role")
            if expected_role != target_role:
                return {
                    "success": False,
                    "error": f"Task {task_id} expected role {expected_role}, but requested {target_role}",
                    "task_id": task_id,
                    "expected_role": expected_role,
                    "requested_role": target_role
                }
            
            # 构造分派消息
            dispatch_message = {
                "type": "task_assignment",
                "task_id": task_id,
                "task_type": spec.get("task_type"),
                "title": spec.get("title"),
                "owner_role": target_role,
                "validator_role": spec.get("validator_role"),
                "input_refs": spec.get("input_refs", []),
                "required_artifacts": spec.get("required_artifacts", []),
                "success_criteria": spec.get("success_criteria", []),
                "assigned_at": datetime.now().isoformat(),
                "source": "master_dispatcher"
            }
            
            # 更新任务状态为待分派
            status_data["status"] = "pending_dispatch"
            status_data["dispatch_prepared_at"] = datetime.now().isoformat()
            status_data["dispatch_prepared_by"] = "master_dispatcher"
            
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "task_id": task_id,
                "target_role": target_role,
                "session_key": f"agent:{target_role}:main",
                "dispatch_message": dispatch_message,
                "prepared_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
    
    def send_message_to_agent(self, session_key: str, message: str):
        """向 agent 发送消息的桥接接口 - 标记为待由 master agent 调用的真实桥接入口"""
        # 这是一个占位符，实际的消息发送需要由 master agent 层完成
        # 通过 OpenClaw 的 sessions_send 工具实现真实跨 agent 通信
        print(f"🚧 消息桥接接口: 待由 master agent 调用的真实通信 - {session_key}: {message[:50]}...")
        # 实际的通信由 master agent 层通过 sessions_send 实现
        # 这里只记录消息，不尝试直接发送
        self._record_agent_message(session_key, message)
    
    def _record_agent_message(self, session_key: str, message: str):
        """记录待发送的消息，等待 master agent 层处理"""
        # 记录消息到待处理队列
        message_record = {
            "timestamp": datetime.now().isoformat(),
            "session_key": session_key,
            "message": message,
            "status": "pending_master_agent_delivery"
        }
        
        # 将消息记录保存到文件，等待 master agent 处理
        from pathlib import Path
        import json
        msg_dir = Path(self.workspace) / "traces" / "messages"
        msg_dir.mkdir(parents=True, exist_ok=True)
        
        msg_file = msg_dir / f"pending_message_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.json"
        with open(msg_file, 'w', encoding='utf-8') as f:
            json.dump(message_record, f, ensure_ascii=False, indent=2)
    
    def monitor_tasks(self, timeout_seconds: int = 300) -> dict:
        """监控任务执行进度"""
        print(f"⏱️ 开始监控任务（超时：{timeout_seconds}秒）...")
        
        start_time = time.time()
        results = {}
        
        while time.time() - start_time < timeout_seconds:
            # 检查队列中的任务
            pending = self.queue.list_pending()
            
            # 检查进行中的任务
            running = []
            completed_tasks = []
            failed_tasks = []
            
            for task_file in JOBS_ROOT.glob("TASK-*/status.json"):
                try:
                    status_data = json.load(open(task_file, 'r', encoding='utf-8'))
                    task_id = status_data.get("task_id")
                    
                    if status_data.get("status") in ["running", "completed", "verified"]:
                        running.append({
                            "task_id": task_id,
                            "status": status_data.get("status"),
                            "updated_at": status_data.get("updated_at")
                        })
                        
                        # 检查任务是否完成
                        if status_data.get("status") == "completed":
                            completed_tasks.append(task_id)
                        elif status_data.get("status") == "failed":
                            failed_tasks.append(task_id)
                            
                    # 更新活跃任务状态
                    if task_id in self.active_tasks:
                        self.active_tasks[task_id]["status"] = status_data.get("status")
                    
                    # 当任务完成时，通知相关agent
                    if status_data.get("status") == "completed":
                        try:
                            owner_role = self.active_tasks[task_id]["task_def"]["owner_role"]
                            self.send_message_to_agent(
                                session_key=f"agent:{owner_role}:main",
                                message=f"任务 {task_id} 已完成，等待后续处理"
                            )
                        except KeyError:
                            print(f"⚠️ 任务 {task_id} 不在活跃任务列表中，跳过通知")
                    elif status_data.get("status") == "failed":
                        try:
                            owner_role = self.active_tasks[task_id]["task_def"]["owner_role"]
                            self.send_message_to_agent(
                                session_key=f"agent:{owner_role}:main",
                                message=f"任务 {task_id} 失败，需要重试或修复"
                            )
                        except KeyError:
                            print(f"⚠️ 任务 {task_id} 不在活跃任务列表中，跳过通知")
                        
                except Exception as e:
                    print(f"⚠️ 读取任务状态失败 {task_file}: {e}")
                    continue
            
            print(f"📊 任务状态：待处理={len(pending)}, 进行中={len(running)}, 完成={len(completed_tasks)}, 失败={len(failed_tasks)}")
            
            # 更新结果字典
            for task_id in completed_tasks:
                if task_id not in results:
                    results[task_id] = "completed"
                    print(f"✅ 任务完成：{task_id}")
                    
                    # 当任务完成时，通知相关agent
                    self.send_message_to_agent(
                        session_key=f"agent:{self.active_tasks[task_id]['task_def']['owner_role']}:main",
                        message=f"任务 {task_id} 已完成，等待后续处理"
                    )
            
            for task_id in failed_tasks:
                if task_id not in results:
                    results[task_id] = "failed"
                    print(f"❌ 任务失败：{task_id}")
                    
                    # 当任务失败时，通知相关agent
                    self.send_message_to_agent(
                        session_key=f"agent:{self.active_tasks[task_id]['task_def']['owner_role']}:main",
                        message=f"任务 {task_id} 失败，需要重试或修复"
                    )
            
            # 如果所有活跃任务都完成，退出
            all_done = True
            for task_id in self.active_tasks:
                if task_id not in results:
                    all_done = False
                    break
                    
            if all_done and results:
                break
            
            time.sleep(2)  # 减少轮询间隔以提高响应速度
        
        return results
    
    def decide_next(self, task_results: dict) -> List[dict]:
        """根据任务完成情况决定下一步"""
        next_tasks = []
        
        for task_id, result in task_results.items():
            if result == "completed":
                # 任务成功，根据原任务定义创建后续任务
                original_task = None
                for task_info in self.active_tasks.values():
                    if task_info.get("task_def", {}).get("task_id") == task_id:
                        original_task = task_info
                        break
                        
                if original_task:
                    next_roles = original_task["task_def"].get("next_roles", [])
                    if next_roles:
                        # 创建后续任务
                        for next_role in next_roles:
                            next_task_id = f"{task_id}-followup-{next_role}"
                            next_tasks.append({
                                "action": "create_followup",
                                "task_id": task_id,
                                "next_task_id": next_task_id,
                                "next_role": next_role,
                                "next_step": "create_task"
                            })
                    else:
                        next_tasks.append({
                            "action": "complete",
                            "task_id": task_id,
                            "next_step": "notify_user"
                        })
            elif result == "failed":
                # 任务失败，需要重试或修复
                next_tasks.append({
                    "action": "retry",
                    "task_id": task_id,
                    "next_step": "repair"
                })
        
        return next_tasks
    
    def create_followup_task(self, original_task_id: str, next_role: str) -> bool:
        """创建后续任务"""
        print(f"🔄 为任务 {original_task_id} 创建后续任务给 {next_role}")
        
        # 获取原始任务信息
        original_task_info = self.active_tasks.get(original_task_id)
        if not original_task_info:
            print(f"❌ 找不到原始任务信息：{original_task_id}")
            return False
        
        original_task_def = original_task_info["task_def"]
        
        # 创建后续任务ID
        next_task_id = f"{original_task_id}-followup-{next_role}"
        title = f"Follow-up task for {original_task_id} - {next_role}"
        
        # 根据角色确定任务类型
        task_type = f"{next_role.replace('-', '_')}_followup"
        
        # 创建后续任务
        success = create_task(
            task_id=next_task_id,
            task_type=task_type,
            title=title,
            owner_role=next_role,
            validator_role="test-expert",  # 默认测试验证
            input_refs=[f"../{original_task_id}/artifacts"],  # 引用原始任务的artifacts
            required_artifacts=self._get_required_artifacts(task_type, next_role),
            success_criteria=[f"Process artifacts from {original_task_id}"]
        )
        
        if success:
            # 添加到活跃任务
            self.active_tasks[next_task_id] = {
                "task_def": {
                    "task_type": task_type,
                    "owner_role": next_role,
                    "validator_role": "test-expert",
                    "input_refs": [f"../{original_task_id}/artifacts"]
                },
                "status": "created",
                "start_time": datetime.now().isoformat(),
                "depends_on": original_task_id
            }
            
            # 唤醒对应的worker
            self.wake_worker(next_role)
            
            print(f"✅ 后续任务已创建：{next_task_id} → {next_role}")
        else:
            print(f"❌ 后续任务创建失败：{next_task_id}")
        
        return success
    
    def run(self, request: str):
        """
        完整执行流程
        
        1. 接收需求
        2. 分派任务
        3. 唤醒 Worker
        4. 监控进度
        5. 决定下一步
        """
        print(f"\n{'='*60}")
        print(f"🚀 Master 调度器启动")
        print(f"{'='*60}\n")
        
        # 1. 接收需求并分析
        analysis = self.receive_request(request)
        tasks = analysis["tasks"]
        
        print(f"📋 分析完成，需要创建 {len(tasks)} 个任务\n")
        
        # 2. 分派任务
        for i, task_def in enumerate(tasks):
            task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(i+1).zfill(3)}"
            title = f"自动任务 {i+1} - {task_def['task_type']}"
            
            success = self.dispatch_task(
                task_def=task_def,
                task_id=task_id,
                title=title,
                input_refs=[],
                success_criteria=["任务完成"]
            )
            
            if success:
                print(f"✅ 任务已分派：{task_id} → {task_def['owner_role']}")
                
                # 3. 唤醒对应 Worker
                self.wake_worker(task_def["owner_role"])
            else:
                print(f"❌ 任务分派失败：{task_id}")
        
        print(f"\n⏳ 等待任务执行完成...\n")
        
        # 4. 监控进度
        results = self.monitor_tasks(timeout_seconds=600)  # 增加超时时间
        
        # 5. 决定下一步
        next_actions = self.decide_next(results)
        
        print(f"\n{'='*60}")
        print(f"📊 执行结果汇总")
        print(f"{'='*60}")
        for task_id, result in results.items():
            status = "✅" if result == "completed" else "❌"
            print(f"{status} {task_id}: {result}")
        
        print(f"\n📋 下一步动作:")
        for action in next_actions:
            if action['action'] == 'create_followup':
                print(f"  - 创建后续任务: {action['next_task_id']} → {action['next_role']}")
                # 实际创建后续任务
                self.create_followup_task(action['task_id'], action['next_role'])
            else:
                print(f"  - {action['action']}: {action['task_id']} → {action['next_step']}")
        
        return {"results": results, "next_actions": next_actions}
    
    def process_task_result(self, task_id: str, result: str):
        """
        处理任务结果，触发下一轮任务
        这是解决"回流后不触发下一轮"问题的关键方法
        """
        print(f"🔄 处理任务结果: {task_id} -> {result}")
        
        # 根据结果决定下一步
        if result == "completed":
            # 检查是否有后续任务
            original_task_info = self.active_tasks.get(task_id)
            if original_task_info:
                next_roles = original_task_info["task_def"].get("next_roles", [])
                if next_roles:
                    print(f"🎯 为任务 {task_id} 创建后续任务...")
                    for next_role in next_roles:
                        self.create_followup_task(task_id, next_role)
                else:
                    print(f"✅ 任务 {task_id} 完成，无后续任务")
            else:
                print(f"⚠️ 无法找到任务 {task_id} 的原始定义")
        elif result == "failed":
            print(f"⚠️ 任务 {task_id} 失败，需要重试或修复")
            # 在这里可以实现重试逻辑
        else:
            print(f"❓ 未知任务结果: {result}")


def dispatch_request(request: str):
    """分派用户需求"""
    dispatcher = MasterDispatcher()
    return dispatcher.run(request)


def process_task_result(task_id: str, result: str):
    """处理任务结果（用于解决回流问题）"""
    dispatcher = MasterDispatcher()
    # 由于无法从内存中获取任务定义，我们尝试从文件系统加载任务信息
    import json
    from pathlib import Path
    from task_queue import JOBS_ROOT
    
    task_dir = JOBS_ROOT / task_id
    spec_file = task_dir / "spec.json"
    
    if spec_file.exists():
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        # 将任务信息临时添加到调度器的活跃任务中
        dispatcher.active_tasks[task_id] = {
            "task_def": {
                "task_type": spec.get("task_type", "unknown"),
                "owner_role": spec.get("owner_role", "unknown"),
                "validator_role": spec.get("validator_role", "unknown"),
                "next_roles": spec.get("next_roles", [])
            },
            "status": result,
            "start_time": spec.get("created_at", ""),
            "dependent_tasks": []
        }
    
    dispatcher.process_task_result(task_id, result)


def run_from_local_input(input_file: str):
    """从本地输入文件运行调度器"""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        return
    
    # 读取结构化请求
    with open(input_path, 'r', encoding='utf-8') as f:
        request_data = json.load(f)
    
    request = request_data.get("request", "")
    print(f"📥 从本地文件加载请求: {request}")
    
    dispatcher = MasterDispatcher()
    return dispatcher.run(request)


def run_from_structured_request(request_data: dict):
    """从结构化请求运行调度器"""
    request = request_data.get("request", "")
    print(f"📥 从结构化请求运行: {request}")
    
    dispatcher = MasterDispatcher()
    return dispatcher.run(request)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file":
            # 从文件运行
            if len(sys.argv) > 2:
                run_from_local_input(sys.argv[2])
            else:
                print("用法: python master_dispatcher.py --file <input_file>")
        else:
            # 直接从命令行参数运行
            request = " ".join(sys.argv[1:])
            dispatch_request(request)
    else:
        request = "修复 workflow_run_opencode.py 中的命令路径问题"
        dispatch_request(request)