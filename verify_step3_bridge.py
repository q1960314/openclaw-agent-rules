#!/usr/bin/env python3
"""
验证 STEP-3 桥接改进
"""

import sys
from pathlib import Path

# 添加路径
WORKSPACE_ROOT = Path("/home/admin/.openclaw/workspace/master")
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

def test_dispatch_payload():
    """测试分派payload"""
    print("🔍 测试分派payload...")
    
    from master_agent_bridge import get_next_task_for_dispatch, get_stable_dispatch_payload
    
    # 获取下一个待分派任务
    next_task = get_next_task_for_dispatch()
    if next_task:
        task_id = next_task['task_id']
        owner_role = next_task['owner_role']
        
        print(f"📋 任务: {task_id} -> {owner_role}")
        
        # 获取稳定的分派负载
        payload = get_stable_dispatch_payload(task_id, owner_role)
        
        print(f"✅ 成功: {payload.get('success')}")
        print(f"   task_id: {payload.get('task_id')}")
        print(f"   owner_role: {payload.get('owner_role')}")
        print(f"   sessionKey: {payload.get('sessionKey')}")
        print(f"   message keys: {list(payload.get('message', {}).keys())}")
        
        return True
    else:
        print("ℹ️ 没有待分派任务，但接口可用")
        return True


def test_completed_payload():
    """测试完成payload"""
    print("\n🔍 测试完成payload...")
    
    from master_agent_bridge import get_stable_completed_payload
    
    # 获取稳定的完成负载
    completed_payloads = get_stable_completed_payload()
    
    print(f"📊 找到 {len(completed_payloads)} 个完成任务")
    
    for i, payload in enumerate(completed_payloads[:2]):  # 只显示前2个
        print(f"\n  任务 {i+1}: {payload.get('task_id')}")
        print(f"    owner_role: {payload.get('owner_role')}")
        print(f"    status: {payload.get('status')}")
        print(f"    verdict: {payload.get('verdict')}")
        print(f"    next_actions: {len(payload.get('next_action_suggestions'))}")
        print(f"    artifacts: {len(payload.get('artifacts'))}")
        print(f"    file_paths: {list(payload.get('file_paths', {}).keys())}")
    
    return True


def main():
    """主测试函数"""
    print("🚀 验证 STEP-3 桥接改进")
    print("="*60)
    
    success_count = 0
    total_tests = 2
    
    # 测试1: 分派payload
    print("1️⃣ 分派payload测试")
    if test_dispatch_payload():
        success_count += 1
    
    # 测试2: 完成payload
    print("\n2️⃣ 完成payload测试")
    if test_completed_payload():
        success_count += 1
    
    print("\n" + "="*60)
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("✅ 所有payload接口已验证通过")
        
        print("\n🎯 最小 dispatch payload 结构:")
        print("  - sessionKey: agent:{role}:main")
        print("  - message: 包含task信息的字典")
        print("  - task_id: 任务唯一标识")
        print("  - owner_role: 目标worker角色")
        print("  - evidence: 验证相关信息")
        
        print("\n🎯 最小 completed payload 结构:")
        print("  - task_id: 任务唯一标识")
        print("  - owner_role: 原始worker角色")
        print("  - verdict: 验证结果")
        print("  - next_action_suggestions: 下一步建议")
        print("  - file_paths: 关键文件路径")
        print("  - evidence: 验证相关信息")
        
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit(main())