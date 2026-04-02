#!/usr/bin/env python3
"""
验证 Master Agent 桥接接口
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def test_bridge_creation():
    """测试桥接器创建"""
    print("🧪 测试桥接器创建...")
    
    sys.path.append('/home/admin/.openclaw/workspace/master/scripts')
    
    try:
        from master_agent_bridge import MasterAgentBridge
        bridge = MasterAgentBridge()
        print("✅ MasterAgentBridge 创建成功")
        return True
    except Exception as e:
        print(f"❌ MasterAgentBridge 创建失败: {e}")
        return False


def test_intake_handler_methods():
    """测试 intake handler 方法"""
    print("\n🧪 测试 intake handler 方法...")
    
    try:
        from task_intake_handler import TaskIntakeHandler
        handler = TaskIntakeHandler()
        
        # 测试 get_next_task_for_master_agent 方法
        next_task = handler.get_next_task_for_master_agent()
        print(f"✅ get_next_task_for_master_agent 可用: {type(next_task).__name__}")
        
        # 测试 mark_task_as_dispatched_by_master 方法
        # 先创建一个测试任务
        test_request = {
            "request": "测试任务",
            "task_type": "test",
            "owner_role": "coder"
        }
        result = handler.intake_task_request(test_request)
        if result["success"]:
            task_id = result["task_id"]
            mark_result = handler.mark_task_as_dispatched_by_master(task_id)
            print(f"✅ mark_task_as_dispatched_by_master 可用: {mark_result}")
        
        return True
    except Exception as e:
        print(f"❌ intake handler 方法测试失败: {e}")
        return False


def test_consumer_methods():
    """测试 consumer 方法"""
    print("\n🧪 测试 consumer 方法...")
    
    try:
        from task_result_consumer import TaskResultConsumer
        consumer = TaskResultConsumer()
        
        # 测试 get_completed_tasks_for_master_agent 方法
        completed_tasks = consumer.get_completed_tasks_for_master_agent()
        print(f"✅ get_completed_tasks_for_master_agent 可用: 找到 {len(completed_tasks)} 个任务")
        
        # 测试 get_next_followup_tasks_for_master_agent 方法
        followup_tasks = consumer.get_next_followup_tasks_for_master_agent()
        print(f"✅ get_next_followup_tasks_for_master_agent 可用: 找到 {len(followup_tasks)} 个后续任务")
        
        return True
    except Exception as e:
        print(f"❌ consumer 方法测试失败: {e}")
        return False


def test_dispatcher_methods():
    """测试 dispatcher 方法"""
    print("\n🧪 测试 dispatcher 方法...")
    
    try:
        from master_dispatcher import MasterDispatcher
        dispatcher = MasterDispatcher()
        
        # 测试 get_pending_messages_for_master_agent 方法
        pending_messages = dispatcher.get_pending_messages_for_master_agent()
        print(f"✅ get_pending_messages_for_master_agent 可用: 找到 {len(pending_messages)} 个待处理消息")
        
        return True
    except Exception as e:
        print(f"❌ dispatcher 方法测试失败: {e}")
        return False


def test_bridge_functions():
    """测试桥接函数"""
    print("\n🧪 测试桥接函数...")
    
    try:
        from master_agent_bridge import (
            get_next_task_for_dispatch,
            get_completed_tasks_for_processing,
            get_pending_messages_for_delivery,
            get_next_followup_tasks
        )
        
        # 测试所有函数
        task = get_next_task_for_dispatch()
        completed = get_completed_tasks_for_processing()
        messages = get_pending_messages_for_delivery()
        followups = get_next_followup_tasks()
        
        print(f"✅ get_next_task_for_dispatch: {type(task).__name__}")
        print(f"✅ get_completed_tasks_for_processing: 找到 {len(completed)} 个任务")
        print(f"✅ get_pending_messages_for_delivery: 找到 {len(messages)} 个消息")
        print(f"✅ get_next_followup_tasks: 找到 {len(followups)} 个后续任务")
        
        return True
    except Exception as e:
        print(f"❌ 桥接函数测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔍 验证 Master Agent 桥接接口")
    print("="*60)
    
    results = {}
    
    # 测试桥接器创建
    print("1️⃣ 桥接器创建")
    results['bridge_creation'] = test_bridge_creation()
    
    # 测试 intake handler
    print("\n2️⃣ intake handler 方法")
    results['intake_methods'] = test_intake_handler_methods()
    
    # 测试 consumer
    print("\n3️⃣ consumer 方法")
    results['consumer_methods'] = test_consumer_methods()
    
    # 测试 dispatcher
    print("\n4️⃣ dispatcher 方法")
    results['dispatcher_methods'] = test_dispatcher_methods()
    
    # 测试桥接函数
    print("\n5️⃣ 桥接函数")
    results['bridge_functions'] = test_bridge_functions()
    
    print("\n" + "="*60)
    print("📊 桥接接口验证结果:")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 可用" if passed else "❌ 不可用"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n总体结果: {'✅ 桥接接口全部可用' if all_passed else '❌ 部分接口不可用'}")
    
    print("\n🔧 桥接接口功能:")
    print("  1. 任务接收: 可通过 intake handler 获取待处理任务")
    print("  2. 任务分派: 可通过 dispatcher 标记任务状态")
    print("  3. 结果消费: 可通过 consumer 处理完成任务")
    print("  4. 消息传递: 可通过 dispatcher 处理待发送消息")
    print("  5. 后续任务: 可通过 consumer 获取待创建后续任务")
    
    print("\n🎯 供 master agent 调用的接口:")
    print("  - get_next_task_for_dispatch(): 获取待分派任务")
    print("  - get_completed_tasks_for_processing(): 获取完成任务")
    print("  - get_pending_messages_for_delivery(): 获取待发送消息")
    print("  - get_next_followup_tasks(): 获取待创建后续任务")
    print("  - MasterAgentBridge 类提供完整功能")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())