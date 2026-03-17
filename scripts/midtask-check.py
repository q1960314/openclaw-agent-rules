#!/usr/bin/env python3
"""
子智能体中途检查工具
用途：分派任务 5 分钟后检查进展，发现偏离立即纠正
"""

import sys
import json
from datetime import datetime, timedelta

def check_progress(session_key, agent_id):
    """检查子智能体进展"""
    
    # 这里应该调用 OpenClaw API 检查会话状态
    # 现在是示例代码
    
    print("=" * 60)
    print(f"🔍 中途检查：{agent_id}")
    print("=" * 60)
    print(f"会话：{session_key}")
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查项
    checks = [
        ("是否已开始执行", True),
        ("是否遇到错误", False),
        ("是否在主动修复", True),
        ("是否偏离任务", False)
    ]
    
    print("检查项目：")
    for item, status in checks:
        icon = "✅" if status else "⚠️"
        print(f"  {icon} {item}")
    
    print()
    
    # 如果有问题，生成纠正消息
    deviating = any(not s for _, s in checks[:2])
    if deviating:
        print("⚠️ 发现偏离，生成纠正消息...")
        correction_msg = f"""
发现任务执行偏离，请立即纠正：

1. 检查是否遇到错误
2. 如果遇到错误，请分析原因并尝试修复
3. 不要只汇报问题，要主动解决

请继续执行任务。"""
        print(correction_msg)
    else:
        print("✅ 任务执行正常，继续观察")

def main():
    if len(sys.argv) < 3:
        print("用法：midtask-check.py <session_key> <agent_id>")
        print("\n示例：")
        print("  midtask-check.py agent:master:subagent:xxx test-expert")
        sys.exit(1)
    
    session_key = sys.argv[1]
    agent_id = sys.argv[2]
    
    check_progress(session_key, agent_id)

if __name__ == "__main__":
    main()
