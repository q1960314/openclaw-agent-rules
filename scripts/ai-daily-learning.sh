#!/bin/bash
# ==============================================
# AI 自我进化定时任务 - 每日学习总结
# ==============================================
# 任务说明：master-quant 每日自我反思和学习总结
# 执行时间：每天 22:00（避开量化业务任务）
# 输出：每日学习报告存储到 memory/ 目录

AGENT_DIR="/home/admin/.openclaw/agents/master"
MEMORY_DIR="$AGENT_DIR/memory"
LOG_FILE="$AGENT_DIR/logs/ai-self-improvement.log"
REPORT_FILE="$MEMORY_DIR/daily-learning-$(date +%Y-%m-%d).md"

# 确保目录存在
mkdir -p "$MEMORY_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 AI 每日学习总结..." >> "$LOG_FILE"

# 创建自我反思提示文件
cat > /tmp/ai_daily_reflection_$$.txt << 'PROMPT'
【AI 自我进化任务 - 每日学习总结】

请回顾今天的所有对话和任务执行，完成以下自我反思：

## 1. 今日任务统计
- 执行了多少个用户任务？
- 任务类型分布（策略开发/代码优化/回测/数据分析/其他）
- 平均任务完成质量（1-10 分）

## 2. 今日最大收获
- 学到了什么新的量化知识？
- 发现了什么可优化的流程？
- 积累了什么可复用的经验？

## 3. 今日最大失误
- 哪个任务完成得不够好？
- 哪里可以做得更好？
- 根本原因是什么？

## 4. 能力变化评估
- 知识广度：今天扩展了哪些领域？（1-10 分）
- 知识深度：在哪些领域更深入了？（1-10 分）
- 响应质量：相比昨天是否有提升？（1-10 分）
- 问题解决能力：处理复杂问题的能力变化？（1-10 分）

## 5. 明日改进计划
- 重点改进哪 1-2 个方面？
- 需要学习什么新知识？
- 需要优化什么流程？

## 6. 知识库更新建议
- 今天学到的什么内容值得存入共享知识库？
- 什么经验值得所有子智能体学习？

请生成完整的《每日学习报告》，保存到 memory/ 目录。
PROMPT

# 通过 Master 智能体执行自我反思
cd "$AGENT_DIR"
/home/admin/.local/share/pnpm/openclaw agent --agent master --message "$(cat /tmp/ai_daily_reflection_$$.txt)" >> "$LOG_FILE" 2>&1

# 清理临时文件
rm -f /tmp/ai_daily_reflection_$$.txt

echo "[$(date '+%Y-%m-%d %H:%M:%S')] AI 每日学习总结完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
