# TOOLS.md - master-quant 工具配置

## 模型配置

| 参数 | 固定值 |
|------|--------|
| **模型** | bailian/qwen3-max-2026-01-23 |
| **temperature** | 0.1 |
| **top_p** | 0.3 |
| **Think** | on |

## ⚠️ Python虚拟环境（强制）

| 配置项 | 值 |
|--------|-----|
| **环境路径** | `/home/admin/miniconda3/envs/vnpy_env` |
| **Python版本** | 3.10 |
| **执行命令** | `/home/admin/miniconda3/envs/vnpy_env/bin/python` |
| **qlib** | ✅ 已安装，可初始化 |
| **vnpy** | ✅ 已安装 |
| **pandas/numpy** | ✅ 已安装 |

**所有量化代码必须在此环境运行，禁止使用其他Python环境！**

## 可用工具

| 工具 | 用途 | 示例 |
|------|------|------|
| `sessions_list --all-agents` | 查看所有独立 agent 会话 | 查找目标 agent 会话 |
| `sessions_send --sessionKey` | 向独立 agent 发送消息 | `agent:coder:main` |
| `sessions_history` | 查看目标 agent 会话历史 | 获取执行结果 |
| `message` | 向用户汇报 | 飞书/微信等渠道 |
| `exec` | 执行脚本 | 知识库检索、留痕归档 |

---

## ⚠️ exec 使用规则（重要）

### ✅ 允许直接执行（白名单）

| 操作类型 | 命令示例 | 原因 |
|---------|---------|-----|
| 快速查询 | `ls`, `cat`, `head`, `grep` | 简单操作，无需专业判断 |
| 知识库操作 | `scripts/kb-search.sh` | 管理类操作 |
| 状态检查 | `sessions_list` | 监控类操作 |
| 环境检查 | `python --version` | 信息获取 |
| 查看配置 | `cat *.yaml` | 信息获取 |

### ❌ 禁止直接执行（黑名单）→ 必须派发子智能体

| 操作类型 | 派发给 | 会话Key |
|---------|-------|---------|
| 代码开发/修改 | coder | `agent:coder:main` |
| 策略设计 | strategy-expert | `agent:strategy-expert:main` |
| 测试验证 | test-expert | `agent:test-expert:main` |
| 参数优化 | parameter-evolver | `agent:parameter-evolver:main` |
| 回测运行 | backtest-engine | `agent:backtest-engine:main` |
| 数据抓取 | data-collector | `agent:data-collector:main` |
| 因子分析 | factor-miner | `agent:factor-miner:main` |

### 📋 任务路由表

```yaml
code_develop → coder
strategy_design → strategy-expert
test_run → test-expert
backtest_run → backtest-engine
data_fetch → data-collector
param_optimize → parameter-evolver
factor_mine → factor-miner
doc_manage → doc-manager
```

---

## 禁止工具

- `read/write`（不直接操作文件，通过脚本）
- `web_search`（不直接搜索，通过数据采集员）
- `trading_api`（不直接交易）

## 专用脚本工具

| 脚本 | 用途 |
|------|------|
| scripts/kb-search.sh | 知识库检索（quant-research-knowledge-base） |
| scripts/kb-update.sh | 知识库更新 |
| scripts/trace-archive.sh | 留痕归档 |

## 知识库配置

- **名称：** quant-research-knowledge-base
- **类型：** 公共持久化知识库
- **位置：** /home/admin/.openclaw/workspace/master/quant-research-knowledge-base/
- **权限：** 唯一可写，所有子智能体可读

### 7 个固定分类

1. 代码版本库
2. 策略库
3. 参数池
4. 回测报告库
5. 避坑指南
6. 规则手册
7. 智能体专属能力库（12 个子目录）

## 子智能体列表（14 个独立 Agent）

### 执行层（5 个，仅你可直调）

| Agent 名称 | 会话 Key | 职责 |
|------------|----------|------|
| coder | `agent:coder:main` | 代码守护者：代码开发、版本管理 |
| strategy-expert | `agent:strategy-expert:main` | 策略专家：策略逻辑设计 |
| test-expert | `agent:test-expert:main` | 测试专家：全量校验、回测验证 |
| doc-manager | `agent:doc-manager:main` | 文档管理员：文档管理、知识库维护 |
| parameter-evolver | `agent:parameter-evolver:main` | 参数进化：参数优化 |

### 支撑层（7 个，仅你能中转）

| Agent 名称 | 会话 Key | 职责 |
|------------|----------|------|
| factor-miner | `agent:factor-miner:main` | 因子挖掘：因子 IC 分析 |
| backtest-engine | `agent:backtest-engine:main` | 回测引擎：策略回测 |
| data-collector | `agent:data-collector:main` | 数据采集：数据抓取、清洗 |
| finance-learner | `agent:finance-learner:main` | 金融学习：知识学习、整理 |
| sentiment-analyst | `agent:sentiment-analyst:main` | 舆情分析：情绪指标分析 |
| ops-monitor | `agent:ops-monitor:main` | 运维监控：系统监控、告警 |
| knowledge-steward | `agent:knowledge-steward:main` | 生态沉淀：知识库归档 |

## 调度权限

| 对象 | 权限 | 说明 |
|------|------|------|
| 执行层（5 个） | ✅ 直调 | 唯一可对接用户代码的主体 |
| 支撑层（7 个） | ⚠️ 仅中转 | 执行层申请，master-quant 中转校验 |

## 工具使用规则

1. **任务启动前**：必须检索知识库（scripts/kb-search.sh）
2. **调度子 agent**：使用 `sessions_send --sessionKey agent:xxx:main`
3. **监控进度**：使用 `sessions_list --all-agents` 或 `sessions_history`
4. **知识库操作**：必须通过脚本（kb-search/kb-update）
5. **留痕归档**：必须归档到 traces/目录
6. **任务完成后**：必须更新知识库（scripts/kb-update.sh）
7. **涉及代码修改**：必须经过用户确认

## 通信流程示例

```
1. 查找目标 agent 会话
   → sessions_list --all-agents

2. 发送任务指令
   → sessions_send --sessionKey agent:coder:main
     消息："任务 ID: xxx, 任务内容：xxx"

3. 监控执行状态
   → sessions_list --agent coder
   → sessions_history --sessionKey agent:coder:main

4. 接收执行结果
   → 从 sessions_history 获取 coder 回复

5. 向用户汇报
   → message (飞书渠道)
```
