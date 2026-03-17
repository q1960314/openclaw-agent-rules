# 生态共享知识库

## 目录结构

```
knowledge-base/
├── strategies/        # 策略库
│   ├── trend-following/   # 趋势跟踪策略
│   ├── mean-reversion/    # 均值回归策略
│   └── arbitrage/         # 套利策略
├── rules/             # 规则库
│   ├── trading-rules/     # 交易规则
│   ├── risk-rules/        # 风控规则
│   └── compliance-rules/  # 合规规则
├── pitfalls/          # 避坑指南
│   ├── common-mistakes/   # 常见错误
│   └── lessons-learned/   # 教训总结
└── success-cases/     # 成功案例
    ├── strategy-cases/    # 策略案例
    └── optimization-cases/# 优化案例
```

## 使用规则

1. **任务启动前** 必须检索知识库（scripts/kb-search.sh）
2. **复盘迭代后** 必须更新知识库（scripts/kb-update.sh）
3. **所有子智能体** 必须遵循知识库规则

## 检索脚本

```bash
# 关键词搜索
./scripts/kb-search.sh --keyword "止损"

# 分类搜索
./scripts/kb-search.sh --category "risk-rules"

# 标签搜索
./scripts/kb-search.sh --tag "风控"
```

## 更新脚本

```bash
# 新增内容
./scripts/kb-update.sh --add --category "strategies" --file "xxx.md"

# 修改内容
./scripts/kb-update.sh --update --file "xxx.md"

# 归档内容
./scripts/kb-update.sh --archive --file "xxx.md"
```
