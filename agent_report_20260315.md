# 🦞 OpenClaw Agent 系统报告

**生成时间:** 2026-03-15 21:13 GMT+8  
**系统版本:** OpenClaw v1.0  
**工作区:** `/home/admin/.openclaw/workspace`

---

## 📊 总览

| 指标 | 数值 |
|------|------|
| **总 Agent 数** | 23 个 |
| **活跃会话** | 27 个 |
| **Cron 任务** | 12 个 |
| **总 Token 消耗** | ~2.5M |

---

## 🎯 Agent 列表

### 核心 Agent

| ID | 名称 | 模型 | 工作区 | 状态 |
|----|------|------|--------|------|
| **main** | FK (主助手) | qwen3.5-plus | `/workspace` | ✅ 活跃 |
| **master-quant** | 量化中枢 | glm-5 | `/workspace/agents/master-quant` | ✅ 活跃 |

### 执行层 Agent (5 个)

| ID | 名称 | 模型 | 职责 | 会话数 |
|----|------|------|------|--------|
| **coder** | 代码守护者 | qwen3.5-plus | 代码开发/优化 | 2 |
| **strategy-expert** | 策略专家 | qwen3-max-2026-01-23 | 策略设计 | 2 |
| **test-expert** | 测试专家 | qwen3.5-plus | 测试验证 | 2 |
| **doc-manager** | 文档管理员 | qwen3.5-plus | 文档管理 | 2 |
| **parameter-evolver** | 参数进化 | qwen3.5-plus | 参数优化 | 2 |

### 支撑层 Agent (7 个)

| ID | 名称 | 模型 | 职责 | 会话数 |
|----|------|------|------|--------|
| **factor-miner** | 因子挖掘 | qwen3.5-plus | 因子挖掘 | 2 |
| **backtest-engine** | 回测引擎 | qwen3.5-plus | 回测执行 | 2 |
| **data-collector** | 数据采集员 | qwen3.5-plus | 数据抓取 | 2 |
| **finance-learner** | 金融学习员 | qwen3-max-2026-01-23 | 金融分析 | 2 |
| **sentiment-analyst** | 舆情分析员 | qwen3.5-plus | 舆情分析 | 2 |
| **ops-monitor** | 运维监控员 | qwen3.5-plus | 系统监控 | 2 |
| **knowledge-steward** | 生态沉淀员 | qwen3.5-plus | 知识库管理 | 2 |

### 其他 Agent (9 个)

| ID | 名称 | 模型 | 状态 |
|----|------|------|------|
| **backtester** | 回测专家 | qwen3.5-plus | 闲置 |
| **strategist** | 策略师 | qwen3.5-plus | 闲置 |
| **optimizer** | 优化专家 | qwen3.5-plus | 闲置 |
| **knowledge-curator** | 知识策展 | qwen3.5-plus | 闲置 |
| **doc-admin** | 文档管理 | qwen3.5-plus | 闲置 |
| **tester** | 测试员 | qwen3.5-plus | 闲置 |
| **analyst** | 分析师 | qwen3.5-plus | 闲置 |

---

## ⏰ Cron 定时任务 (12 个)

| Agent | Cron Label | 模型 | 状态 |
|-------|-----------|------|------|
| main | FK AI 自我进化 | qwen3.5-plus | ✅ 运行中 |
| coder | coder-247 | qwen3-coder-plus | ✅ 运行中 |
| strategy-expert | strategy-expert-247 | qwen3-max-2026-01-23 | ✅ 运行中 |
| test-expert | test-expert-247 | qwen3.5-plus | ✅ 运行中 |
| doc-manager | doc-manager-247 | qwen3.5-plus | ✅ 运行中 |
| parameter-evolver | parameter-evolver-247 | qwen3.5-plus | ✅ 运行中 |
| factor-miner | factor-miner-247 | qwen3-max-2026-01-23 | ✅ 运行中 |
| backtest-engine | backtest-engine-247 | qwen3.5-plus | ✅ 运行中 |
| data-collector | data-collector-247 | qwen3.5-plus | ✅ 运行中 |
| finance-learner | finance-learner-247 | qwen3-max-2026-01-23 | ✅ 运行中 |
| sentiment-analyst | sentiment-analyst-247 | qwen3.5-plus | ✅ 运行中 |
| ops-monitor | ops-monitor-247 | qwen3.5-plus | ✅ 运行中 |
| knowledge-steward | knowledge-steward-247 | qwen3.5-plus | ✅ 运行中 |

---

## 📁 Agent 目录结构

```
~/.openclaw/agents/
├── main/                    # 主助手
├── master-quant/            # 量化中枢
├── coder/                   # 代码守护者
├── strategy-expert/         # 策略专家
├── test-expert/             # 测试专家
├── doc-manager/             # 文档管理员
├── parameter-evolver/       # 参数进化
├── factor-miner/            # 因子挖掘
├── backtest-engine/         # 回测引擎
├── data-collector/          # 数据采集员
├── finance-learner/         # 金融学习员
├── sentiment-analyst/       # 舆情分析员
├── ops-monitor/             # 运维监控员
├── knowledge-steward/       # 生态沉淀员
├── backtester/              # 回测专家
├── strategist/              # 策略师
├── optimizer/               # 优化专家
├── knowledge-curator/       # 知识策展
├── doc-admin/               # 文档管理
├── tester/                  # 测试员
└── analyst/                 # 分析师
```

---

## 🔧 配置信息

### 全局配置 (`~/.openclaw/openclaw.json`)

```json
{
  "defaults": {
    "model": {
      "primary": "bailian/qwen3.5-plus"
    },
    "maxConcurrent": 12,
    "subagents": {
      "maxConcurrent": 16
    }
  },
  "agents": [
    {"id": "main"},
    {"id": "coder", "model": "dashscope-coding/qwen3.5-plus"},
    {"id": "strategy-expert", "model": "dashscope-coding/qwen3.5-plus"},
    {"id": "test-expert", "model": "dashscope-coding/qwen3.5-plus"},
    ...
  ]
}
```

### 可用模型

| 别名 | 完整模型 ID | 用途 |
|------|-----------|------|
| `glm-5` | bailian/glm-5 | 通用对话 |
| `qwen3.5-plus` | dashscope/qwen3.5-plus | 主力模型 |
| `qwen3-max-2026-01-23` | dashscope/qwen3-max-2026-01-23 | 高级推理 |
| `qwen3-vl-plus` | dashscope-us/qwen3-vl-plus | 视觉理解 |

---

## 📈 会话统计

### 活跃会话 Top 5

| Agent | 会话 Key | Token 消耗 | 最后活跃 |
|-------|---------|-----------|---------|
| main | agent:main:main | 121,826 | 刚刚 |
| master-quant | agent:master-quant:feishu:... | 36,391 | 5 分钟前 |
| coder | agent:coder:main | 174,529 | 1 小时前 |
| test-expert | agent:test-expert:main | 64,538 | 2 小时前 |
| knowledge-steward | agent:knowledge-steward:main | 31,375 | 2 小时前 |

### 会话模式

| 模式 | 数量 | 说明 |
|------|------|------|
| **webchat** | 10 | Web 控制界面 |
| **feishu** | 2 | 飞书直连 |
| **cron** | 12 | 定时任务 |
| **unknown** | 3 | 其他 |

---

## ⚠️ 注意事项

1. **sessions_send 限制**: 当前环境中 `sessions_send` 工具受限，建议使用 `sessions_spawn` + `subagents` 组合
2. **网关认证**: 部分子智能体调度可能遇到网关认证问题，需检查 `~/.openclaw/openclaw.json`
3. **Cron 任务**: 12 个 Cron 任务独立运行，不依赖对话会话
4. **会话复用**: 使用固定 `label` 可以复用会话，避免重复创建

---

## 🚀 建议

### 短期优化

1. **修复 sessions_send** - 检查网关配置
2. **清理闲置 Agent** - 9 个闲置 Agent 可考虑合并或删除
3. **优化 Cron 频率** - 部分 Cron 任务可降低频率

### 长期规划

1. **引入图结构工作流** - 类似 LangGraph
2. **完善角色定义** - 类似 CrewAI
3. **添加监控面板** - 实时监控 Agent 状态

---

**报告生成完成** ✅
