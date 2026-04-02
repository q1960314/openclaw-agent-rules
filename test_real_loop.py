#!/usr/bin/env python3
"""
测试真实调度闭环的脚本
"""

import json
import subprocess
import time
from pathlib import Path

def test_basic_dispatch():
    """测试基本的任务分派和执行流程"""
    print("🧪 开始测试真实调度闭环...")
    
    # 创建一个测试任务
    test_request = "修复一个简单的代码问题"
    
    print(f"📤 发送测试请求: {test_request}")
    
    # 使用master dispatcher处理请求
    cmd = [
        "python3",
        "scripts/master_dispatcher.py"
    ] + test_request.split()
    
    # 执行命令并捕获输出
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd="/home/admin/.openclaw/workspace/master"
    )
    
    print(f"💻 执行完成，返回码: {result.returncode}")
    print(f"📄 标准输出:\n{result.stdout}")
    if result.stderr:
        print(f"⚠️ 标准错误:\n{result.stderr}")
    
    return result.returncode == 0


def test_task_creation():
    """测试任务创建和队列功能"""
    print("\n🧪 测试任务创建功能...")
    
    import sys
    sys.path.append('/home/admin/.openclaw/workspace/master/scripts')
    from task_queue import create_task
    from datetime import datetime
    
    task_id = f"TEST-TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    success = create_task(
        task_id=task_id,
        task_type="test",
        title="测试任务",
        owner_role="coder",
        validator_role="test-expert",
        input_refs=[],
        required_artifacts=["result.md"],
        success_criteria=["任务成功完成"]
    )
    
    print(f"📋 任务创建 {'成功' if success else '失败'}: {task_id}")
    
    return success


def test_worker_claim():
    """测试worker认领任务功能"""
    print("\n🧪 测试Worker认领任务...")
    
    import sys
    sys.path.append('/home/admin/.openclaw/workspace/master/scripts')
    from task_queue import claim_task
    from worker_base import CoderWorker
    from task_queue import JOBS_ROOT
    
    # 尝试认领一个任务
    task = claim_task("coder")
    
    if task:
        print(f"✅ 成功认领任务: {task.task_id}")
        
        # 创建一个简单的worker实例来执行任务
        worker = CoderWorker()
        worker.current_task = task
        # 设置任务目录
        worker.task_dir = JOBS_ROOT / task.task_id
        
        # 执行任务
        result = worker.execute()
        print(f"🔧 任务执行 {'成功' if result else '失败'}")
        
        return result
    else:
        print("ℹ️ 没有待处理的coder任务（这可能是正常的）")
        return True  # 没有任务也算正常


def main():
    """主测试函数"""
    print("🎯 开始真实调度闭环测试")
    print("="*60)
    
    results = []
    
    # 测试任务创建
    results.append(("任务创建", test_task_creation()))
    
    # 测试worker认领
    results.append(("Worker认领", test_worker_claim()))
    
    # 测试基本调度
    results.append(("基本调度", test_basic_dispatch()))
    
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())