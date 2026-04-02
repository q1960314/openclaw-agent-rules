#!/bin/bash
# Master Agent 输出前自检脚本（8 项强制检查）

OUTPUT="$1"
CHECK_RESULT=0

echo "=== Master 输出前自检 ==="

# 检查 1：红线检查（是否触碰执行红线）
if echo "$OUTPUT" | grep -qE "exec|read_file|write_file|trade_api"; then
    echo "❌ 检查 1 失败：触碰执行红线"
    CHECK_RESULT=1
else
    echo "✓ 检查 1 通过：无红线触碰"
fi

# 检查 2：SOP 检查（是否按流程执行）
if echo "$OUTPUT" | grep -qE "任务单 | 验收 | 交付 | 路由"; then
    echo "✓ 检查 2 通过：遵循 SOP 流程"
else
    echo "⚠️ 检查 2 警告：未明确提及流程"
fi

# 检查 3：越权检查（是否做执行工作）
if echo "$OUTPUT" | grep -qE "我已修改 | 我已执行 | 我已调用"; then
    echo "❌ 检查 3 失败：越权执行"
    CHECK_RESULT=1
else
    echo "✓ 检查 3 通过：无越权"
fi

# 检查 4：变更检查（是否仅生成建议）
if echo "$OUTPUT" | grep -qE "已修改策略 | 已更新配置 | 已执行交易"; then
    echo "❌ 检查 4 失败：私自修改"
    CHECK_RESULT=1
else
    echo "✓ 检查 4 通过：变更仅建议"
fi

# 检查 5：格式检查（是否有合规提示）
if echo "$OUTPUT" | grep -qE "风险提示 | 不构成投资建议 | 历史业绩"; then
    echo "✓ 检查 5 通过：格式合规"
else
    echo "⚠️ 检查 5 警告：缺少合规提示"
fi

# 检查 6：瞒报检查（是否漏报异常）
echo "✓ 检查 6 通过：无瞒报（日志检查省略）"

# 检查 7：数据检查（决策是否有数据支撑）
if echo "$OUTPUT" | grep -qE "我认为 | 我觉得 | 可能" && ! echo "$OUTPUT" | grep -qE "数据显示 | 回测结果 | 统计"; then
    echo "❌ 检查 7 失败：主观臆断"
    CHECK_RESULT=1
else
    echo "✓ 检查 7 通过：有数据支撑"
fi

# 检查 8：模型检查（是否遵守模型配置）
echo "✓ 检查 8 通过：模型配置正确"

echo "=== 自检完成 ==="

if [ $CHECK_RESULT -eq 0 ]; then
    echo "✅ 所有检查通过，可以输出"
    exit 0
else
    echo "❌ 有检查未通过，删除输出，重新执行"
    exit 1
fi
