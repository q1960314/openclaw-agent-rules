# 自动流转执行指南

## 📋 规则已写入配置

**配置位置：** `/home/admin/.openclaw/agents/master/.openclaw/config.json`

**配置项：** `enforcement.autoWorkflow`

---

## ⚡ 响应时间要求

| 动作 | 最大时间 | 实际工具 |
|------|---------|---------|
| 收到报告 → 分析 | < 30 秒 | 自动 |
| 分析 → 分派下一步 | < 60 秒 | auto-workflow.py |
| 子智能体超时检查 | 每 5 分钟 | midtask-check.py |
| 任务超时 | 1 小时 | 自动重试 |

---

## 🔧 使用方式

### 1. 收到报告后自动分派

```bash
# 收到 coder 的接口集成报告后
./scripts/auto-workflow.py next stage_0_1 "接口集成完成，15 个接口已实现"

# 输出：自动分派 stage_0_2 → test-expert
```

### 2. 查看进度

```bash
./scripts/auto-workflow.py status
```

### 3. 检查超时

```bash
./scripts/auto-workflow.py check-timeout
```

---

## 📊 工作流阶段

```
stage_0_1 (接口集成) → coder
  ↓ 自动
stage_0_2 (接口测试) → test-expert
  ↓ 自动
stage_0_3 (联合测试) → test-expert
  ↓ 自动
stage_1 (全量抓取) → data-collector
  ↓ 完成
汇总 → 用户
```

---

## ✅ 这次是真正自动的！

- ✅ 配置已写入 config.json
- ✅ 工具已创建（auto-workflow.py）
- ✅ 规则已添加到 AGENTS.md
- ✅ 不等待用户确认
- ✅ 60 秒内自动分派

---

**最后更新：** 2026-03-12 14:41
