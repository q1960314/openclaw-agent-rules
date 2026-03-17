#!/usr/bin/env python3
"""
子智能体任务分派工具
用途：分派任务时自动添加验证要求和固定 label
"""

import sys
import json

# 固定 label 映射
FIXED_LABELS = {
    "strategy-expert": "master-strategy",
    "coder": "master-coder",
    "test-expert": "master-test",
    "doc-manager": "master-doc",
    "parameter-evolver": "master-param",
    "factor-miner": "master-factor",
    "backtest-engine": "master-backtest",
    "data-collector": "master-data",
    "finance-learner": "master-finance",
    "sentiment-analyst": "master-sentiment",
    "ops-monitor": "master-ops",
    "knowledge-steward": "master-knowledge"
}

STANDARD_REQUIREMENTS = """
## 核心要求（必须遵守）

1. **发现错误必须分析原因**，禁止只汇报"失败了"
2. **必须主动尝试修复**（换日期、改参数、重试等）
3. **必须验证修复结果**
4. **汇报格式（强制）**：
   - 问题现象
   - 原因分析
   - 修复尝试
   - 验证结果
   - 结论建议

## 验收标准

- 缺少任何要素 → 打回重新汇报
- 不主动修复 → 批评并要求重新执行

## 示例

看到错误时：
- ❌ 禁止：汇报"接口失败"
- ✅ 必须：分析原因 → 尝试修复 → 验证结果 → 汇报

"""

def dispatch_task(agent_id, task_description):
    """生成标准的任务分派内容"""
    
    # 获取固定 label
    label = FIXED_LABELS.get(agent_id, f"master-{agent_id}")
    
    # 构建完整任务描述
    full_task = f"""你是{agent_id}，负责{task_description}。

{STANDARD_REQUIREMENTS}

开始执行。"""
    
    return {
        "agentId": agent_id,
        "label": label,
        "mode": "run",
        "runtime": "subagent",
        "task": full_task
    }

def main():
    if len(sys.argv) < 3:
        print("用法：dispatch-task.py <agentId> <任务描述>")
        print("\n示例：")
        print("  dispatch-task.py test-expert '接口测试'")
        print("  dispatch-task.py coder '代码优化'")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    task_desc = " ".join(sys.argv[2:])
    
    # 生成任务配置
    config = dispatch_task(agent_id, task_desc)
    
    print("=" * 60)
    print("📋 任务分派配置")
    print("=" * 60)
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 输出 sessions_spawn 调用代码
    print("\n" + "=" * 60)
    print("📝 JavaScript 调用代码")
    print("=" * 60)
    print(f"""
sessions_spawn({{
  agentId: "{config['agentId']}",
  label: "{config['label']}",
  mode: "{config['mode']}",
  runtime: "{config['runtime']}",
  task: `{config['task']}`
}})
""")

if __name__ == "__main__":
    main()
