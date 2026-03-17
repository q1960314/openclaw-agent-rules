#!/usr/bin/env python3
"""
自动流转执行工具
用途：收到子智能体报告后，自动分派下一步任务（不等待用户确认）
"""

import json
import sys
from datetime import datetime

# 工作流阶段定义
WORKFLOW_STAGES = {
    "stage_0_1": {
        "name": "接口集成",
        "agent": "coder",
        "label": "master-coder",
        "next": "stage_0_2",
        "auto": True
    },
    "stage_0_2": {
        "name": "接口测试",
        "agent": "test-expert",
        "label": "master-test",
        "next": "stage_0_3",
        "auto": True
    },
    "stage_0_3": {
        "name": "接口联合测试",
        "agent": "test-expert",
        "label": "master-test",
        "next": "stage_1",
        "auto": True
    },
    "stage_1": {
        "name": "全量数据抓取",
        "agent": "data-collector",
        "label": "master-data",
        "next": None,
        "auto": False,  # 完成后等待用户确认
        "notify": True
    }
}

def load_current_stage():
    """加载当前阶段"""
    stage_file = "/home/admin/.openclaw/agents/master/workflow-stage.json"
    try:
        with open(stage_file, 'r') as f:
            return json.load(f)
    except:
        return {"current": "stage_0_1", "history": []}

def save_current_stage(data):
    """保存当前阶段"""
    stage_file = "/home/admin/.openclaw/agents/master/workflow-stage.json"
    with open(stage_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def dispatch_next_stage(current_stage_id, report_summary=""):
    """分派下一阶段任务"""
    
    stage = WORKFLOW_STAGES.get(current_stage_id)
    if not stage:
        print(f"❌ 未知阶段：{current_stage_id}")
        return None
    
    next_stage_id = stage.get('next')
    if not next_stage_id:
        print(f"✅ 工作流完成！当前阶段：{stage['name']}")
        return "completed"
    
    next_stage = WORKFLOW_STAGES.get(next_stage_id)
    if not next_stage:
        print(f"❌ 下一阶段不存在：{next_stage_id}")
        return None
    
    # 生成任务描述
    task_template = {
        "stage_0_1": "负责代码集成和接口实现",
        "stage_0_2": "负责接口测试和数据验证",
        "stage_0_3": "负责接口联合测试和兼容性验证",
        "stage_1": "负责全量数据抓取和存储"
    }
    
    task_desc = task_template.get(next_stage_id, "负责任务执行")
    
    # 输出分派命令
    print("=" * 70)
    print(f"🚀 自动分派下一阶段：{next_stage['name']}")
    print("=" * 70)
    print(f"执行 Agent: {next_stage['agent']}")
    print(f"固定 Label: {next_stage['label']}")
    print(f"任务描述：{task_desc}")
    print()
    
    # 生成 sessions_spawn 调用
    print("JavaScript 调用代码：")
    print("-" * 70)
    print(f"""
sessions_spawn({{
  agentId: "{next_stage['agent']}",
  label: "{next_stage['label']}",
  mode: "run",
  runtime: "subagent",
  task: `你是{next_stage['agent']}，负责{task_desc}。

## 核心要求（必须遵守）

1. **发现错误必须分析原因**，禁止只汇报"失败了"
2. **必须主动尝试修复**（换日期、改参数、重试等）
3. **必须验证修复结果**
4. **汇报格式（强制）**：问题现象 + 原因分析 + 修复尝试 + 验证结果 + 结论建议
5. **发现优化点必须汇报**（类别 + 优先级 + 描述 + 收益 + 建议）

## 验收标准

- 缺少任何要素 → 打回重新汇报
- 不主动修复 → 批评并要求重新执行

开始执行。`
}})
""")
    
    # 保存进度
    workflow_data = load_current_stage()
    workflow_data["history"].append({
        "from": current_stage_id,
        "to": next_stage_id,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "report": report_summary[:200]
    })
    workflow_data["current"] = next_stage_id
    save_current_stage(workflow_data)
    
    print("=" * 70)
    print(f"✅ 已更新工作流进度：{current_stage_id} → {next_stage_id}")
    print(f"📁 进度文件：/home/admin/.openclaw/agents/master/workflow-stage.json")
    
    return next_stage_id

def check_timeout():
    """检查子智能体任务是否超时"""
    # 这里应该检查活跃的子智能体会话
    print("🔍 检查子智能体任务超时状态...")
    # TODO: 实现超时检查和重试逻辑
    return []

def main():
    if len(sys.argv) < 2:
        print("用法：auto-workflow.py <command> [args]")
        print("\n命令：")
        print("  next [stage_id] [report]  - 分派下一阶段")
        print("  status                    - 查看当前进度")
        print("  check-timeout             - 检查超时")
        print("  reset                     - 重置工作流")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "next":
        current = load_current_stage()["current"]
        stage_id = sys.argv[2] if len(sys.argv) > 2 else current
        report = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        dispatch_next_stage(stage_id, report)
    
    elif command == "status":
        data = load_current_stage()
        stage = WORKFLOW_STAGES.get(data["current"], {})
        print("=" * 70)
        print("📊 工作流进度")
        print("=" * 70)
        print(f"当前阶段：{stage.get('name', '未知')} ({data['current']})")
        print(f"执行 Agent: {stage.get('agent', '未知')}")
        print(f"自动流转：{'是' if stage.get('auto') else '否'}")
        print()
        print("历史进度：")
        for i, hist in enumerate(data.get("history", [])[-5:], 1):
            print(f"  {i}. [{hist['time']}] {hist['from']} → {hist['to']}")
    
    elif command == "check-timeout":
        check_timeout()
    
    elif command == "reset":
        save_current_stage({"current": "stage_0_1", "history": []})
        print("✅ 工作流已重置")
    
    else:
        print(f"未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
