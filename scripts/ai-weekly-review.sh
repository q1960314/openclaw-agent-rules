#!/bin/bash
# ==============================================
# AI 自我进化定时任务 - 周度能力评估
# ==============================================
# 任务说明：master-quant 周度能力变化和成长评估
# 执行时间：每周日 21:30（避开量化业务任务）
# 输出：周度能力报告存储到 memory/ 目录

AGENT_DIR="/home/admin/.openclaw/agents/master"
MEMORY_DIR="$AGENT_DIR/memory"
LOG_FILE="$AGENT_DIR/logs/ai-self-improvement.log"
REPORT_FILE="$MEMORY_DIR/weekly-review-$(date +%Y-%W).md"

# 确保目录存在
mkdir -p "$MEMORY_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 AI 周度能力评估..." >> "$LOG_FILE"

# 创建自我评估提示文件
cat > /tmp/ai_weekly_review_$$.txt << 'EOF'
【AI 自我进化任务 - 周度能力评估】

请回顾本周的所有任务执行和成长，完成以下深度评估：

## 1. 本周任务全景统计
- 总任务数量
- 任务类型分布（策略开发/代码优化/回测/数据分析/运维）
- 任务成功率
- 平均完成时间
- 用户满意度趋势

## 2. 能力维度评估（1-10 分）
### 知识维度
- 知识广度：本周扩展了哪些新领域？
- 知识深度：在哪些核心领域更深入了？
- 知识更新：学习了什么新的量化方法/工具？

### 能力维度
- 响应质量：回答的准确性、完整性、专业性
- 问题解决能力：处理复杂问题的能力变化
- 调度协调能力：多智能体协作效率
- 风险控制能力：识别和规避风险的能力

### 进化维度
- 学习能力：从错误中学习的速度
- 适应能力：应对新场景的灵活性
- 创新能力：提出优化建议的质量

## 3. 本周亮点与不足
### 亮点（做得好的）
1. 
2. 
3. 

### 不足（需要改进的）
1. 
2. 
3. 

## 4. 根本原因分析
对每个不足进行深度分析：
- 表面原因
- 根本原因
- 改进方案

## 5. 下周提升计划
### 重点改进目标（1-3 个）
1. 
2. 
3. 

### 具体行动计划
- 学习什么新知识？
- 优化什么流程？
- 改进什么能力？

## 6. 知识库沉淀建议
- 本周什么经验值得存入共享知识库？
- 什么最佳实践值得所有子智能体学习？
- 什么教训值得记录避免再犯？

请生成完整的《周度能力评估报告》，保存到 memory/ 目录，并同步到共享知识库。
EOF

# 通过 OpenClaw 发送自我评估消息
cd "$AGENT_DIR"
openclaw sessions send \
  --sessionKey "agent:master:feishu:direct:ou_27cbc3bb73b465799a20195d83cf92e1" \
  --message "$(cat /tmp/ai_weekly_review_$$.txt)" \
  >> "$LOG_FILE" 2>&1

# 清理临时文件
rm -f /tmp/ai_weekly_review_$$.txt

echo "[$(date '+%Y-%m-%d %H:%M:%S')] AI 周度能力评估完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
