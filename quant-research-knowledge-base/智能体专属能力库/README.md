# 智能体专属能力库

## 用途
每个智能体对应 1 个子目录，存储专属能力、经验、迭代记录

## 目录结构
```
智能体专属能力库/
├── strategy-expert/      # 策略专家专属能力
├── coder/                # 代码守护者专属能力
├── test-expert/          # 测试专家专属能力
├── doc-manager/          # 文档管理员专属能力
├── parameter-evolver/    # 参数进化智能体专属能力
├── factor-miner/         # 因子挖掘智能体专属能力
├── backtest-engine/      # 回测引擎智能体专属能力
├── data-collector/       # 数据采集员专属能力
├── finance-learner/      # 金融学习员专属能力
├── sentiment-analyst/    # 舆情分析员专属能力
├── ops-monitor/          # 运维监控员专属能力
└── knowledge-steward/    # 生态沉淀员专属能力
```

## 存储内容
| 内容 | 说明 | 格式 |
|------|------|------|
| 专属能力 | 该智能体的核心能力、专长 | Markdown |
| 经验沉淀 | 执行中积累的经验、技巧 | Markdown |
| 迭代记录 | 能力迭代历史、优化记录 | Markdown |
| 案例库 | 成功案例、失败教训 | Markdown |

## 命名规范
`智能体名/内容类型_名称_日期.md`

## 权限
- 可写：master-quant
- 可读：所有子智能体
