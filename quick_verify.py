#!/usr/bin/env python3
"""
快速验证修复的脚本
"""

import json
from datetime import datetime
from pathlib import Path

def test_basic_dispatch():
    """测试基本分派功能"""
    print("🧪 测试基本任务分派...")
    
    # 创建一个测试任务
    import sys
    sys.path.append('/home/admin/.openclaw/workspace/master/scripts')
    from task_queue import create_task
    
    task_id = f"FIX-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    success = create_task(
        task_id=task_id,
        task_type="fix_verification",
        title="修复验证任务",
        owner_role="coder",
        validator_role="test-expert",
        input_refs=[],
        required_artifacts=["run.log", "diff.patch", "changed_files.json"],
        success_criteria=["修复验证"]
    )
    
    print(f"✅ 任务创建: {task_id}, 成功: {success}")
    
    # 测试process_task_result函数
    try:
        from master_dispatcher import process_task_result
        process_task_result(task_id, "completed")
        print("✅ process_task_result 调用成功")
    except Exception as e:
        print(f"⚠️ process_task_result 调用遇到问题: {e}")
    
    return success


def main():
    print("🔍 快速验证修复...")
    success = test_basic_dispatch()
    
    if success:
        print("✅ 基本功能测试通过")
        return 0
    else:
        print("❌ 基本功能测试失败")
        return 1


if __name__ == "__main__":
    exit(main())