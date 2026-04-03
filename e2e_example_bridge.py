#!/usr/bin/env python3
"""
Master Agent 桥接接口 E2E 示例
演示从 intake 到派单再到回流消费的完整流程
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加工作目录到路径
WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

def mock_sessions_send(sessionKey: str, message: str):
    """
    模拟 sessions_send 函数
    在真实环境中，这将是 OpenClaw 的 sessions_send 工具
    """
    print(f"📞 模拟发送消息到 {sessionKey}: {message[:100]}...")
    return {"status": "sent", "sessionKey": sessionKey, "timestamp": datetime.now().isoformat()}


def e2e_example():
    """端到端示例"""
    print("🚀 Master Agent 桥接接口 E2E 示例")
    print("="*60)
    
    # 1. 导入桥接器
    from master_agent_bridge import MasterAgentBridge, get_next_task_for_dispatch, get_completed_tasks_for_processing
    
    print("1️⃣ 初始化桥接器...")
    bridge = MasterAgentBridge()
    print("✅ 桥接器初始化完成\n")
    
    # 2. 获取待分派的任务
    print("2️⃣ 获取待分派任务...")
    next_task = get_next_task_for_dispatch()
    
    if next_task:
        print(f"📋 找到待分派任务: {next_task['task_id']} -> {next_task['owner_role']}")
        
        # 3. 通过 sessions_send 分派任务（模拟）
        print(f"\n3️⃣ 通过 sessions_send 分派任务到 {next_task['owner_role']}...")
        dispatch_result = bridge.dispatch_task_via_sessions_send(next_task, mock_sessions_send)
        print(f"✅ 分派结果: {dispatch_result['success']}")
    else:
        print("📋 没有待分派的任务，创建一个示例任务...")
        
        # 创建一个示例任务用于演示
        from task_intake_handler import TaskIntakeHandler
        handler = TaskIntakeHandler()
        sample_request = {
            "request": "修复 workflow_run_opencode.py 中的命令路径问题",
            "task_type": "code_fix",
            "owner_role": "coder",
            "validator_role": "test-expert",
            "input_refs": [],
            "success_criteria": ["路径问题已修复", "代码可正常运行"],
            "next_roles": ["test-expert", "doc-manager"]
        }
        intake_result = handler.intake_task_request(sample_request)
        print(f"✅ 示例任务创建: {intake_result['success']}, ID: {intake_result.get('task_id', 'N/A')}")
        
        # 再次尝试获取任务
        next_task = get_next_task_for_dispatch()
        if next_task:
            print(f"📋 找到新创建的待分派任务: {next_task['task_id']} -> {next_task['owner_role']}")
            dispatch_result = bridge.dispatch_task_via_sessions_send(next_task, mock_sessions_send)
            print(f"✅ 分派结果: {dispatch_result['success']}")
    
    # 4. 获取已完成的任务
    print(f"\n4️⃣ 获取已完成的任务...")
    completed_tasks = get_completed_tasks_for_processing()
    print(f"📊 找到 {len(completed_tasks)} 个已完成任务")
    
    for i, task in enumerate(completed_tasks[:2]):  # 只处理前2个以简化输出
        print(f"\n  处理完成任务 {i+1}: {task['task_id']}")
        
        # 5. 处理已完成任务
        processed_result = bridge.process_completed_task(task)
        print(f"  💡 生成 {len(processed_result['next_recommendations'])} 条下一步建议")
        
        for j, rec in enumerate(processed_result['next_recommendations']):
            print(f"    建议 {j+1}: {rec['type']} -> {rec.get('target_role', 'N/A')}")
    
    # 6. 获取待发送的消息
    print(f"\n6️⃣ 获取待发送的消息...")
    from master_agent_bridge import get_pending_messages_for_delivery
    pending_messages = get_pending_messages_for_delivery()
    print(f"📨 找到 {len(pending_messages)} 个待发送消息")
    
    for i, msg in enumerate(pending_messages):
        print(f"  消息 {i+1}: {msg['session_key']}")
        delivery_result = bridge.deliver_message_via_sessions_send(msg, mock_sessions_send)
        print(f"  ✅ 发送结果: {delivery_result['success']}")
    
    # 7. 获取待创建的后续任务
    print(f"\n7️⃣ 获取待创建的后续任务...")
    from master_agent_bridge import get_next_followup_tasks
    followup_tasks = get_next_followup_tasks()
    print(f"🔄 找到 {len(followup_tasks)} 个待创建后续任务")
    
    for i, task in enumerate(followup_tasks):
        print(f"  后续任务 {i+1}: {task.get('target_role', 'N/A')}")
        creation_result = bridge.create_followup_task_via_intake(task)
        print(f"  ✅ 创建结果: {creation_result['success']}")
    
    print(f"\n8️⃣ 示例流程完成")
    print("="*60)
    print("📋 E2E 示例总结:")
    print("  - 任务 intake: 通过 TaskIntakeHandler 接收结构化任务")
    print("  - 任务 dispatch: 通过 sessions_send 发送到 worker agent")
    print("  - 结果 consume: 处理完成任务并生成下一步建议")
    print("  - 消息 delivery: 发送状态更新和通知")
    print("  - 后续任务: 创建 follow-up 任务并加入队列")
    print("\n🎯 这套接口允许 master agent 实现完整的闭环调度")


def minimal_example():
    """最小化示例"""
    print("\n🎯 最小化示例 - Master Agent 调用模式")
    print("-" * 40)
    
    # 这是 master agent 会在其循环中执行的操作
    from master_agent_bridge import (
        get_next_task_for_dispatch,
        get_completed_tasks_for_processing,
        get_pending_messages_for_delivery,
        get_next_followup_tasks
    )
    
    print("1. 检查待分派任务...")
    next_task = get_next_task_for_dispatch()
    if next_task:
        print(f"   → 发现任务: {next_task['task_id']} -> {next_task['owner_role']}")
    
    print("2. 检查已完成任务...")
    completed_tasks = get_completed_tasks_for_processing()
    print(f"   → {len(completed_tasks)} 个已完成任务待处理")
    
    print("3. 检查待发送消息...")
    pending_messages = get_pending_messages_for_delivery()
    print(f"   → {len(pending_messages)} 个消息待发送")
    
    print("4. 检查后续任务...")
    followup_tasks = get_next_followup_tasks()
    print(f"   → {len(followup_tasks)} 个后续任务待创建")
    
    print("✅ Master Agent 可以基于这些信息做调度决策")


if __name__ == "__main__":
    e2e_example()
    minimal_example()