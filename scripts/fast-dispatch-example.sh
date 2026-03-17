#!/bin/bash
# 快速任务分派示例脚本
# 用途：演示如何快速分派任务给多个子智能体

echo "=========================================="
echo "🚀 快速任务分派示例"
echo "=========================================="

echo ""
echo "场景：收到用户指令后，Master 快速分派任务"
echo ""

echo "1. 分派给 strategy-expert (策略分析)"
echo "   Label: master-strategy"
echo "   任务：分析当前代码优化方向"

echo ""
echo "2. 分派给 coder (代码实现)"
echo "   Label: master-coder"
echo "   任务：实现优化方案"

echo ""
echo "3. 分派给 test-expert (测试验证)"
echo "   Label: master-test"
echo "   任务：验证代码正确性"

echo ""
echo "4. 分派给 data-collector (数据采集)"
echo "   Label: master-data"
echo "   任务：补充缺失数据接口"

echo ""
echo "=========================================="
echo "⚡ 并行执行：4 个子智能体同时工作"
echo "=========================================="
echo ""
echo "预计完成时间：5-10 分钟（并行）"
echo "串行执行时间：20-40 分钟（串行）"
echo "速度提升：4 倍"
echo ""

# 实际调用示例（伪代码）
cat << 'JSEOF'

// Master agent 中的调用代码示例
const tasks = [
  { agent: "strategy-expert", label: "master-strategy", task: "分析优化方向" },
  { agent: "coder", label: "master-coder", task: "实现优化方案" },
  { agent: "test-expert", label: "master-test", task: "验证代码" },
  { agent: "data-collector", label: "master-data", task: "采集数据" }
];

// 并行执行所有任务
await Promise.all(tasks.map(t => 
  sessions_spawn({
    runtime: "subagent",
    agentId: t.agent,
    mode: "run",
    label: t.label,  // 固定 label
    task: t.task
  })
));

// 等待所有子智能体完成并汇总结果
JSEOF

echo ""
echo "=========================================="
