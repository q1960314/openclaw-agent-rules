# 子智能体固定会话配置

## 📌 会话管理策略

**原则：** 每个子智能体使用固定 label，复用会话，不重复创建。

## 🎯 固定 Label 映射表

| 子智能体 | 固定 Label | 会话用途 |
|---------|-----------|---------|
| strategy-expert | `master-strategy` | 策略分析与优化 |
| coder | `master-coder` | 代码开发与集成 |
| test-expert | `master-test` | 测试与验证 |
| doc-manager | `master-doc` | 文档管理 |
| parameter-evolver | `master-param` | 参数优化 |
| factor-miner | `master-factor` | 因子挖掘 |
| backtest-engine | `master-backtest` | 回测执行 |
| data-collector | `master-data` | 数据采集 |
| finance-learner | `master-finance` | 金融分析 |
| sentiment-analyst | `master-sentiment` | 舆情分析 |
| ops-monitor | `master-ops` | 运维监控 |
| knowledge-steward | `master-knowledge` | 知识库管理 |

## 📝 使用示例

```javascript
// ✅ 正确：使用固定 label
sessions_spawn({
  runtime: "subagent",
  agentId: "coder",
  mode: "run",
  label: "master-coder",  // ← 固定 label
  task: "检查代码状态"
})

// ❌ 错误：不使用 label 或使用随机 label
sessions_spawn({
  runtime: "subagent",
  agentId: "coder",
  mode: "run",
  // 没有 label，每次创建新会话
  task: "检查代码状态"
})
```

## 🔄 会话复用逻辑

1. **第一次调用**：创建新会话
2. **后续调用**：复用相同 label 的会话
3. **会话文件**：保存在 `/mnt/data/agents/master/sessions/`
4. **上下文保持**：同一 label 的对话历史累积

## ⚡ 快速分派任务流程

```
收到用户指令
  ↓
Master 分析任务
  ↓
并行分派给多个子智能体（固定 label）
  ↓
子智能体执行并汇报
  ↓
Master 汇总结果
  ↓
交付给用户
```

## 📊 会话监控

```bash
# 查看当前会话
ls -lh /mnt/data/agents/master/sessions/*.jsonl

# 查看会话映射
cat /mnt/data/agents/master/sessions/sessions.json | python3 -m json.tool
```

---

**最后更新：** 2026-03-12
