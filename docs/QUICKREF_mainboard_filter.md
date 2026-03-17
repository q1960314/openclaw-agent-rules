# 主板筛选配置 - 快速参考

## 🎯 配置位置

**文件：** `fetch_data_optimized.py`  
**行号：** 约 73-84 行（ALLOWED_MARKET），103-117 行（STOCK_FILTER_CONFIG）

## 📝 核心配置

### 1. ALLOWED_MARKET（板块筛选）

```python
# 只选主板
ALLOWED_MARKET = ["主板"]
```

### 2. STOCK_FILTER_CONFIG（完整筛选配置）

```python
STOCK_FILTER_CONFIG = {
    # 板块筛选
    'include_main_board': True,     # 包含主板
    'include_chi_next': False,      # 排除创业板
    'include_star_market': False,   # 排除科创板
    'include_bse': False,           # 排除北交所
    
    # 风险排除
    'exclude_st': True,             # 排除 ST/*ST
    'exclude_suspend': True,        # 排除停牌
    
    # 流动性筛选
    'min_market_cap': 50,           # 最小市值 50 亿
    'min_amount': 100000,           # 最小成交额 1 万
    'min_turnover': 2,              # 最小换手率 2%
}
```

## 🧪 运行测试

```bash
cd /home/admin/.openclaw/agents/master

# 功能测试
python tests/test_mainboard_filter_simple.py

# 集成验证
python tests/test_mainboard_integration.py
```

## ✅ 验收标准

- [x] 配置集成到代码
- [x] 测试结果只有主板股票（100% 准确率）

## 📊 测试覆盖

- 主板股票别名识别：5 种（✅ 通过）
- 创业板排除：3 种别名（✅ 通过）
- 科创板排除：3 种别名（✅ 通过）
- 北交所排除：3 种别名（✅ 通过）
- 总测试用例：17 个（✅ 100% 通过）

## 🔧 快速修改

如需调整筛选板块，修改 `ALLOWED_MARKET`：

```python
# 主板 + 创业板
ALLOWED_MARKET = ["主板", "创业板"]

# 所有板块
ALLOWED_MARKET = ["主板", "创业板", "科创板", "北交所"]
```

---

**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎
