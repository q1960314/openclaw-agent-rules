# ✅ 已确认的规则配置

**更新时间：** 2026-03-12 14:34  
**配置位置：** `/home/admin/.openclaw/agents/master/.openclaw/config.json`

---

## 📋 完整规则列表

### 1. 错误处理规则 ✅

**配置项：** `enforcement.reportValidation`

**规则内容：**
- ✅ 强制验证汇报格式
- ✅ 必需字段：问题现象、原因分析、修复尝试、验证结果、结论建议
- ✅ 缺少字段 → 打回重新汇报
- ✅ 中途检查：5 分钟后

**实际工具：**
- `validate-report.py` - 验证汇报
- `dispatch-task.py` - 分派任务
- `midtask-check.py` - 中途检查

---

### 2. 固定 Label 规则 ✅

**配置项：** `enforcement.fixedLabels`

**规则内容：**
- ✅ 每个子智能体使用固定 label
- ✅ 禁止使用其他 label
- ✅ 映射表：
  - test-expert → master-test
  - coder → master-coder
  - strategy-expert → master-strategy
  - data-collector → master-data
  - ...（12 个）

**实际工具：**
- `dispatch-task.py` - 自动使用固定 label

---

### 3. 优化建议处理规则 ✅（新增）

**配置项：** `enforcement.optimizationHandling`

**规则内容：**
- ✅ 强制收集所有优化建议
- ✅ 跟踪状态（pending/implemented/rejected）
- ✅ 每周生成报告
- ✅ 5 个类别：性能优化、代码结构、数据源、错误处理、用户体验
- ✅ 3 个优先级：high/medium/low
- ✅ 汇报格式强制要求（6 要素）

**汇报格式（强制）：**
```
## 【优化建议】

**类别：** {性能优化/代码结构/数据源/错误处理/用户体验}
**优先级：** {high/medium/low}
**问题描述：** {描述当前可以优化的地方}
**优化建议：** {具体的优化方案}
**预期收益：** {优化后能带来什么好处}
**实施建议：** {如何实施这个优化}
```

**处理流程：**
- high → 立即实施
- medium → 安排实施
- low → 记录待办

**实际工具：**
- `optimization-handler.py` - 收集、分类、跟踪

---

### 4. Prompt 要求 ✅

**配置项：** `prompt.optimizationRequirement`

**内容：**
- ✅ 发现优化点时必须汇报
- ✅ 汇报格式示例
- ✅ 违反后果说明

---

## 🔍 验证方式

### 验证配置是否正确
```bash
./scripts/verify-config.py
```

### 验证汇报格式
```bash
./scripts/validate-report.py "汇报内容..."
```

### 添加优化建议
```bash
./scripts/optimization-handler.py add test-expert "性能优化" "可以并行执行" high
```

### 生成优化报告
```bash
./scripts/optimization-handler.py report
```

---

## ✅ 规则执行保障

| 规则 | 执行方式 | 违规后果 |
|------|---------|---------|
| 汇报格式 | validate-report.py 验证 | 打回重做 |
| 固定 label | dispatch-task.py 自动使用 | 任务分派失败 |
| 优化建议 | optimization-handler.py 跟踪 | 批评并记录 |
| 中途检查 | midtask-check.py 定时检查 | 发现偏离立即纠正 |

---

## 📊 实际效果

### 之前
- ❌ 只写文档
- ❌ 没有配置
- ❌ 靠自觉
- ❌ 优化被忽略

### 现在
- ✅ 写入 config.json
- ✅ 可执行工具
- ✅ 强制验证
- ✅ 优化有人管

---

**这次是真正写入规则配置文件了！** ✅

**配置备份：** `/home/admin/.openclaw/agents/master/.openclaw/config.json.bak.before_optimization_rule`
