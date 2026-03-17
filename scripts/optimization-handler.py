#!/usr/bin/env python3
"""
优化建议处理工具
用途：收集、分类、跟踪子智能体发现的优化建议
"""

import json
import os
from datetime import datetime

OPTIMIZATION_FILE = "/home/admin/.openclaw/agents/master/optimizations.json"

def load_optimizations():
    """加载优化建议列表"""
    if os.path.exists(OPTIMIZATION_FILE):
        with open(OPTIMIZATION_FILE, 'r') as f:
            return json.load(f)
    return {"optimizations": [], "stats": {"total": 0, "implemented": 0, "pending": 0}}

def save_optimizations(data):
    """保存优化建议列表"""
    with open(OPTIMIZATION_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_optimization(agent_id, category, description, priority="medium", suggested_action=""):
    """添加优化建议"""
    
    data = load_optimizations()
    
    optimization = {
        "id": f"opt-{data['stats']['total'] + 1:03d}",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "agent": agent_id,
        "category": category,
        "description": description,
        "priority": priority,  # high, medium, low
        "suggested_action": suggested_action,
        "status": "pending",  # pending, reviewing, implemented, rejected
        "implemented_at": None,
        "notes": ""
    }
    
    data["optimizations"].append(optimization)
    data["stats"]["total"] += 1
    data["stats"]["pending"] += 1
    
    save_optimizations(data)
    
    return optimization

def list_optimizations(status="all", priority="all"):
    """列出优化建议"""
    data = load_optimizations()
    
    optimizations = data["optimizations"]
    
    # 过滤
    if status != "all":
        optimizations = [o for o in optimizations if o["status"] == status]
    if priority != "all":
        optimizations = [o for o in optimizations if o["priority"] == priority]
    
    # 排序（按优先级）
    priority_order = {"high": 0, "medium": 1, "low": 2}
    optimizations.sort(key=lambda x: priority_order.get(x["priority"], 1))
    
    return optimizations

def update_optimization(opt_id, status, notes=""):
    """更新优化建议状态"""
    data = load_optimizations()
    
    for opt in data["optimizations"]:
        if opt["id"] == opt_id:
            opt["status"] = status
            opt["notes"] = notes
            if status == "implemented":
                opt["implemented_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data["stats"]["implemented"] += 1
                data["stats"]["pending"] -= 1
            break
    
    save_optimizations(data)
    return True

def generate_report():
    """生成优化建议报告"""
    data = load_optimizations()
    
    print("=" * 70)
    print("📊 优化建议统计报告")
    print("=" * 70)
    print(f"总建议数：{data['stats']['total']}")
    print(f"已实施：{data['stats']['implemented']}")
    print(f"待处理：{data['stats']['pending']}")
    print()
    
    # 按优先级分类
    by_priority = {}
    for opt in data["optimizations"]:
        p = opt["priority"]
        if p not in by_priority:
            by_priority[p] = []
        by_priority[p].append(opt)
    
    for priority in ["high", "medium", "low"]:
        opts = by_priority.get(priority, [])
        if opts:
            print(f"\n{'🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'} {priority.upper()} 优先级 ({len(opts)}):")
            for opt in opts[:5]:  # 只显示前 5 个
                status_icon = {"pending": "⏳", "implemented": "✅", "rejected": "❌"}.get(opt["status"], "?")
                print(f"  {status_icon} [{opt['id']}] {opt['description'][:50]}...")
    
    print()

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法：optimization-handler.py <command> [args]")
        print("\n命令：")
        print("  add <agent> <category> <description> [priority]  - 添加优化建议")
        print("  list [status] [priority]                        - 列出优化建议")
        print("  update <id> <status> [notes]                    - 更新状态")
        print("  report                                          - 生成报告")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 5:
            print("用法：add <agent> <category> <description> [priority]")
            sys.exit(1)
        opt = add_optimization(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5] if len(sys.argv) > 5 else "medium"
        )
        print(f"✅ 已添加优化建议：{opt['id']}")
    
    elif command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else "all"
        priority = sys.argv[3] if len(sys.argv) > 3 else "all"
        opts = list_optimizations(status, priority)
        print(f"找到 {len(opts)} 条优化建议")
        for opt in opts[:10]:
            print(f"  [{opt['id']}] {opt['agent']} - {opt['description'][:50]}")
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("用法：update <id> <status> [notes]")
            sys.exit(1)
        update_optimization(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        print(f"✅ 已更新优化建议：{sys.argv[2]}")
    
    elif command == "report":
        generate_report()
    
    else:
        print(f"未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
