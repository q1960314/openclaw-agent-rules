# TOOLS.md - master-quant 工具配置

## 模型配置

| 参数 | 固定值 |
|------|--------|
| **模型** | dashscope/qwen3-max-2026-01-23 |
| **temperature** | 0.1 |
| **top_p** | 0.3 |
| **Think** | on |

## 可用工具
- sessions_spawn（路由给子智能体）
- sessions_send（发送消息）
- sessions_list（查看状态）
- message（汇报用户）
- exec（执行脚本：知识库检索、留痕归档等）

## sessions_spawn 调用规范（⚠️ 必须遵守）

### 核心原则：使用持久会话，实现实时通信

**错误示例**（每次创建新会话，无法通知）：
```javascript
sessions_spawn({
  agentId: "coder",
  task: "执行任务",
  mode: "run"  // ❌ 单次运行，完成后会话销毁，无法通知
})
```

**正确示例**（持久会话，完成后立即回复）：
```javascript
sessions_spawn({
  agentId: "coder",
  task: "执行任务 X",
  mode: "session",           // ✅ 持久会话，保持活跃
  label: "coder-task",       // ✅ 固定标签，复用会话
  thread: true,              // ✅ 绑定线程，实时通信
  cleanup: "keep"            // ✅ 会话保持，不销毁
})
```

### 任务下发后等待回复

**Master 下发任务后：**
1. ✅ 在同一个会话中等待子智能体回复
2. ✅ 子智能体完成后立即回复"完成"
3. ✅ Master 收到回复后立即继续下一步
4. ✅ 实现秒级响应，无需轮询

### 子智能体会话标签映射表

| 子智能体 | label (固定) | 说明 |
|---------|-------------|------|
| `master` | `master` | 全局中枢 |
| `strategy-expert` | `strategy-expert` | 策略优化 |
| `coder` | `coder` | 代码编写 |
| `test-expert` | `test-expert` | 测试验证 |
| `doc-manager` | `doc-manager` | 文档管理 |
| `parameter-evolver` | `parameter-evolver` | 参数进化 |
| `factor-miner` | `factor-miner` | 因子挖掘 |
| `backtest-engine` | `backtest-engine` | 回测引擎 |
| `data-collector` | `data-collector` | 数据采集 |
| `finance-learner` | `finance-learner` | 金融学习 |
| `sentiment-analyst` | `sentiment-analyst` | 舆情分析 |
| `ops-monitor` | `ops-monitor` | 运维监控 |
| `knowledge-steward` | `knowledge-steward` | 知识沉淀 |

### 会话复用流程

1. **首次调用**：`sessions_spawn` 创建会话（自动使用 label 标识）
2. **后续调用**：使用 `sessions_send` + 相同 `label` 发送消息
3. **查看状态**：`sessions_list()` 检查会话是否活跃
4. **清理会话**：仅在必要时使用 `subagents(action="kill", target="label")`

### 实时通信保障

- ✅ 使用 `mode: "session"` 保持会话活跃
- ✅ 使用固定 `label` 确保消息路由到正确会话
- ✅ 使用 `thread: true` 绑定到同一对话线程
- ❌ 避免 `mode: "run"`（单次运行，无法接收回复）
- ❌ 避免不指定 `label`（每次创建新会话）

## 禁止工具
- read/write（不直接操作文件，通过脚本）
- web_search（不直接搜索，通过数据采集员）
- trading_api（不直接交易）

## 专用脚本工具
| 脚本 | 用途 |
|------|------|
| scripts/kb-search.sh | 知识库检索（quant-research-knowledge-base） |
| scripts/kb-update.sh | 知识库更新 |
| scripts/trace-archive.sh | 留痕归档 |

## 知识库配置
- **名称：** quant-research-knowledge-base
- **类型：** 公共持久化知识库
- **位置：** /home/admin/.openclaw/agents/master/quant-research-knowledge-base/
- **权限：** 唯一可写，所有子智能体可读

### 7 个固定分类
1. 代码版本库
2. 策略库
3. 参数池
4. 回测报告库
5. 避坑指南
6. 规则手册
7. 智能体专属能力库（12 个子目录）

## 调度权限
| 对象 | 权限 | 说明 |
|------|------|------|
| 执行层（5 个） | ✅ 直调 | 唯一可对接用户代码的主体 |
| 支撑层（7 个） | ⚠️ 仅中转 | 执行层申请，master-quant 中转校验 |

## 工具使用规则
1. 知识库操作必须通过脚本（kb-search/kb-update）
2. 留痕必须归档到 traces/目录
3. 所有脚本执行必须记录日志
4. 调度必须严格按层级权限
5. 任务启动前必须检索知识库
6. 任务完成后必须更新知识库
7. 涉及代码修改必须经过用户确认
8. **调用子智能体必须使用持久会话模式（mode: "session" + 固定 label）**
