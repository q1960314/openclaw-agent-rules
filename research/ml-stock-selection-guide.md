# 机器学习选股模型研究

**研究时间：** 2026-03-12  
**研究对象：** ML/DL/RL在选股中的应用

---

## 一、模型类型对比

### 1.1 树模型（Tree-Based Models）

#### XGBoost
```python
优势:
- 训练速度快
- 可解释性强（特征重要性）
- 处理缺失值能力强
- 支持自定义损失函数

劣势:
- 时序建模能力弱
- 容易过拟合（需正则化）

适用场景:
- 截面选股（横截面预测）
- 因子重要性分析
- 中小规模数据（<100 万样本）

推荐参数:
{
    'max_depth': 6,
    'learning_rate': 0.01,
    'n_estimators': 1000,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0
}
```

#### LightGBM
```python
优势:
- 比 XGBoost 更快
- 内存占用更低
- 支持类别特征
- 直方图算法

劣势:
- 参数敏感
- 小数据可能过拟合

适用场景:
- 大规模数据（>100 万样本）
- 实时预测
- 高维特征

推荐参数:
{
    'num_leaves': 31,
    'learning_rate': 0.01,
    'n_estimators': 1000,
    'max_depth': -1,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}
```

#### CatBoost
```python
优势:
- 类别特征处理最优
- 防止预测偏移
- 无需交叉验证

劣势:
- 训练速度较慢
- 内存占用大

适用场景:
- 含大量类别特征
- 对过拟合敏感场景
```

### 1.2 深度学习模型（Deep Learning）

#### LSTM（长短期记忆网络）
```python
优势:
- 捕捉时序依赖
- 适合序列预测
- 记忆长短期模式

劣势:
- 训练慢
- 需要大量数据
- 超参数敏感

架构推荐:
Input(因子序列) → LSTM(128) → Dropout(0.2) → LSTM(64) → Dense(32) → Output(收益)

适用场景:
- 时序预测（次日/周收益）
- 量价序列建模
- 高频数据
```

#### GRU（门控循环单元）
```python
优势:
- 比 LSTM 更简洁
- 训练更快
- 效果相近

劣势:
- 长序列略逊于 LSTM

架构推荐:
Input → GRU(128) → Dropout(0.2) → GRU(64) → Dense(32) → Output

适用场景:
- 中短期时序预测
- 计算资源有限
```

#### Transformer
```python
优势:
- 并行计算
- 长序列依赖
- 注意力机制可解释

劣势:
- 需要极大量数据
- 计算资源需求大
- 训练复杂

架构推荐:
Input → Positional Encoding → Multi-Head Attention(8 heads) → 
Feed Forward → Layer Norm → Output

适用场景:
- 多因子融合
- 长序列建模
- 跨市场学习
```

#### Temporal Fusion Transformer (TFT)
```python
优势:
- 专为时序设计
- 支持静态/动态特征
- 可解释性强

劣势:
- 实现复杂
- 训练时间长

适用场景:
- 多源数据融合
- 需要可解释性
- 中长期预测
```

### 1.3 强化学习模型（Reinforcement Learning）

#### PPO（Proximal Policy Optimization）
```python
优势:
- 训练稳定
- 样本效率较高
- 连续动作空间

劣势:
- 超参数敏感
- 需要大量交互

适用场景:
- 交易执行优化
- 仓位管理
- 动态调仓
```

#### DQN（Deep Q-Network）
```python
优势:
- 离散动作空间优
- 实现相对简单

劣势:
- 连续动作不适用
- 可能不收敛

适用场景:
- 买卖信号生成
- 离散仓位决策
```

### 1.4 图神经网络（GNN）

```python
优势:
- 建模关联关系
- 行业/供应链传播
- 信息聚合

劣势:
- 图构建复杂
- 计算开销大

适用场景:
- 行业轮动
- 供应链选股
- 关联股票分析
```

---

## 二、特征工程最佳实践

### 2.1 特征类型

#### 基础特征（必选）
```
价量特征 (50-100 个):
- OHLCV 衍生指标
- 技术指标 (MA, MACD, RSI, KDJ, etc.)
- 成交量指标
- 波动率指标

基本面特征 (30-50 个):
- 估值指标 (PE, PB, PS, etc.)
- 盈利指标 (ROE, ROA, etc.)
- 成长指标 (收入增长，利润增长)
- 财务健康指标

宏观特征 (10-20 个):
- 利率
- 通胀
- PMI
- 货币供应
```

#### 进阶特征（可选）
```
另类数据:
- 舆情情感分数
- 分析师预期
- 资金流向
- 股东变化
- 机构持仓

衍生特征:
- 因子交互项
- 因子滞后项
- 滚动统计量
- 行业相对值
```

### 2.2 特征预处理

#### 标准化
```python
from sklearn.preprocessing import StandardScaler, RobustScaler

# Z-Score 标准化（推荐）
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 稳健标准化（有异常值时）
scaler = RobustScaler()
X_scaled = scaler.fit_transform(X)
```

#### 中性化
```python
# 行业中性化
def industry_neutralize(X, industry):
    """
    对每个行业内进行标准化
    消除行业暴露
    """
    X_neutral = X.copy()
    for ind in np.unique(industry):
        mask = industry == ind
        X_neutral[mask] = (X[mask] - X[mask].mean()) / (X[mask].std() + 1e-6)
    return X_neutral

# 市值中性化
def market_cap_neutralize(X, market_cap):
    """
    回归取残差
    消除市值暴露
    """
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(np.log(market_cap).reshape(-1, 1), X)
    residual = X - model.predict(np.log(market_cap).reshape(-1, 1))
    return residual
```

#### 去极值
```python
# 3σ原则
def winsorize_3sigma(X, sigma=3):
    mean = X.mean()
    std = X.std()
    lower = mean - sigma * std
    upper = mean + sigma * std
    return np.clip(X, lower, upper)

# 百分位法
def winsorize_percentile(X, lower=1, upper=99):
    lower_bound = np.percentile(X, lower)
    upper_bound = np.percentile(X, upper)
    return np.clip(X, lower_bound, upper_bound)
```

### 2.3 特征选择

#### IC 筛选
```python
def ic_filter(X, y, threshold=0.02):
    """
    基于 IC 值筛选特征
    """
    ic_scores = []
    for col in X.columns:
        ic = np.corrcoef(X[col], y)[0, 1]
        ic_scores.append(abs(ic))
    
    selected = [col for col, ic in zip(X.columns, ic_scores) if ic > threshold]
    return selected
```

#### 相关性筛选
```python
def correlation_filter(X, threshold=0.7):
    """
    剔除高相关特征
    保留代表性特征
    """
    corr_matrix = X.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    return [col for col in X.columns if col not in to_drop]
```

#### 特征重要性
```python
from sklearn.feature_selection import SelectFromModel
from xgboost import XGBRegressor

# 使用 XGBoost 特征重要性
model = XGBRegressor()
model.fit(X, y)
importance = model.feature_importances_

# 选择重要性前 N 的特征
selected_indices = np.argsort(importance)[-50:]
selected_features = X.columns[selected_indices]
```

---

## 三、模型训练要点

### 3.1 防止过拟合

#### 时间序列交叉验证
```python
from sklearn.model_selection import TimeSeriesSplit

# Purged Time Series Split（推荐）
# 避免信息泄露
tscv = TimeSeriesSplit(n_splits=5, gap=20)  # gap 防止泄露

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
```

#### 特征 Dropout
```python
# 训练时随机屏蔽部分特征
# 类似图像中的 Dropout
def feature_dropout(X, dropout_rate=0.1):
    mask = np.random.rand(*X.shape) > dropout_rate
    return X * mask
```

#### 正则化
```python
# L1 正则化（Lasso）- 特征选择
# L2 正则化（Ridge）- 防止过拟合
# ElasticNet - 两者结合

params = {
    'reg_alpha': 0.1,  # L1
    'reg_lambda': 1.0,  # L2
}
```

#### 早停（Early Stopping）
```python
model.fit(
    X_train, y_train,
    eval_set=[(X_valid, y_valid)],
    early_stopping_rounds=50,  # 50 轮不提升则停止
    verbose=False
)
```

### 3.2 样本外验证

#### 滚动回测
```python
def rolling_backtest(X, y, window=252, step=20):
    """
    滚动窗口回测
    window: 训练窗口长度（交易日）
    step: 滚动步长
    """
    scores = []
    for i in range(0, len(X) - window, step):
        X_train = X.iloc[i:i+window]
        y_train = y.iloc[i:i+window]
        X_test = X.iloc[i+window:i+window+step]
        y_test = y.iloc[i+window:i+window+step]
        
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        score = np.corrcoef(pred, y_test)[0, 1]
        scores.append(score)
    
    return scores
```

#### 扩张窗口回测
```python
def expanding_backtest(X, y, initial_window=252, step=20):
    """
    扩张窗口回测
    训练窗口逐渐扩大
    """
    scores = []
    for i in range(initial_window, len(X) - step, step):
        X_train = X.iloc[:i]
        y_train = y.iloc[:i]
        X_test = X.iloc[i:i+step]
        y_test = y.iloc[i:i+step]
        
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        score = np.corrcoef(pred, y_test)[0, 1]
        scores.append(score)
    
    return scores
```

### 3.3 模型集成

#### Bagging
```python
from sklearn.ensemble import BaggingRegressor

bagging = BaggingRegressor(
    base_estimator=XGBRegressor(),
    n_estimators=10,
    max_samples=0.8,
    max_features=0.8,
    random_state=42
)
```

#### Stacking
```python
from sklearn.ensemble import StackingRegressor

estimators = [
    ('xgb', XGBRegressor()),
    ('lgb', LGBMRegressor()),
    ('rf', RandomForestRegressor())
]

stacking = StackingRegressor(
    estimators=estimators,
    final_estimator=LinearRegression()
)
```

---

## 四、模型评估指标

### 4.1 预测准确性

```python
# IC（Information Coefficient）
IC = np.corrcoef(predictions, actual_returns)[0, 1]

# ICIR（Information Coefficient Information Ratio）
ICIR = IC_mean / IC_std

# Rank IC（秩相关）
from scipy.stats import spearmanr
rank_ic = spearmanr(predictions, actual_returns)[0]

# 方向准确率
accuracy = (np.sign(predictions) == np.sign(actual_returns)).mean()
```

### 4.2 组合表现

```python
# 十分组回测
def quantile_backtest(predictions, actual_returns, n_quantiles=10):
    """
    按预测值分组，计算各组收益
    """
    quantiles = pd.qcut(predictions, n_quantiles, labels=False)
    group_returns = actual_returns.groupby(quantiles).mean()
    return group_returns

# 多空组合
long_short_return = group_returns.iloc[-1] - group_returns.iloc[0]

# 夏普比率
sharpe = mean_return / std_return * np.sqrt(252)

# 最大回撤
def max_drawdown(returns):
    cumulative = (1 + returns).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (cumulative - peak) / peak
    return drawdown.min()
```

### 4.3 稳定性检验

```python
# 滚动 IC
rolling_ic = predictions.rolling(60).corr(actual_returns)

# IC 衰减
def ic_decay(predictions, actual_returns, max_lag=20):
    decays = []
    for lag in range(1, max_lag):
        ic = np.corrcoef(predictions.iloc[:-lag], actual_returns.iloc[lag:])[0, 1]
        decays.append(ic)
    return decays

# 半衰期
half_life = np.argmax(np.array(decays) < decays[0] / 2) + 1
```

---

## 五、实战建议

### 5.1 模型选择指南

| 数据规模 | 推荐模型 | 理由 |
|---------|---------|------|
| <10 万样本 | XGBoost/LightGBM | 小数据表现好，训练快 |
| 10-100 万 | LightGBM/CatBoost | 平衡速度与效果 |
| >100 万 | LightGBM/深度学习 | 大数据深度学习优势明显 |
| 时序强相关 | LSTM/GRU/Transformer | 捕捉时序模式 |
| 需要可解释 | XGBoost/LightGBM + SHAP | 特征重要性清晰 |
| 实时预测 | LightGBM | 推理速度快 |

### 5.2 超参数调优

```python
from sklearn.model_selection import RandomizedSearchCV

# XGBoost 参数空间
param_dist = {
    'max_depth': [3, 4, 5, 6, 7, 8],
    'learning_rate': [0.001, 0.01, 0.1],
    'n_estimators': [500, 1000, 2000],
    'subsample': [0.6, 0.7, 0.8, 0.9],
    'colsample_bytree': [0.6, 0.7, 0.8, 0.9],
    'reg_alpha': [0, 0.1, 0.5, 1],
    'reg_lambda': [0.5, 1, 2, 5]
}

search = RandomizedSearchCV(
    XGBRegressor(),
    param_dist,
    n_iter=50,
    cv=TimeSeriesSplit(5),
    scoring='neg_mean_squared_error',
    random_state=42
)
search.fit(X_train, y_train)
best_params = search.best_params_
```

### 5.3 部署建议

```python
# 模型保存
import joblib
joblib.dump(model, 'stock_selector_model.pkl')

# 模型加载
model = joblib.load('stock_selector_model.pkl')

# 批量预测
predictions = model.predict(X_new)

# 实时预测（优化）
# 1. 特征预处理缓存
# 2. 模型量化（减少推理时间）
# 3. 批量预测代替单条预测
```

---

## 六、常见陷阱与规避

### 6.1 数据泄露

```python
❌ 错误：使用未来数据
y = df['close'].shift(-1)  # 使用了未来价格
X = df[['close', 'volume']]

✅ 正确：仅使用历史信息
X = df[['close', 'volume']].shift(1)  # 使用昨日数据
y = df['close'].pct_change()  # 今日收益
```

### 6.2 过拟合

```python
❌ 错误：在测试集上调参
model.fit(X_train, y_train)
score = model.score(X_test, y_test)  # 用测试集调参

✅ 正确：使用验证集
X_train_val, X_test = train_test_split(X, test_size=0.2)
X_train, X_val = train_test_split(X_train_val, test_size=0.2)
model.fit(X_train, y_train)
val_score = model.score(X_val, y_val)  # 验证集调参
test_score = model.score(X_test, y_test)  # 最终测试
```

### 6.3 幸存者偏差

```python
❌ 错误：仅使用当前成分股
stocks = current_index_components()  # 忽略已退市股票

✅ 正确：使用全量历史数据
stocks = all_historical_stocks(include_delisted=True)
```

### 6.4 交易成本忽略

```python
❌ 错误：忽略交易成本
return = portfolio_return

✅ 正确：考虑交易成本
transaction_cost = turnover * 0.001  # 假设 0.1% 成本
net_return = portfolio_return - transaction_cost
```

---

## 七、推荐技术栈

### 7.1 Python 库

```
数据处理:
- pandas, numpy, polars
- akshare, tushare (数据获取)

机器学习:
- scikit-learn
- xgboost, lightgbm, catboost

深度学习:
- pytorch, tensorflow
- transformers (HuggingFace)

回测框架:
- qlib (微软)
- backtrader
- zipline

可视化:
- matplotlib, seaborn
- plotly
```

### 7.2 硬件建议

```
入门配置:
- CPU: 8 核+
- 内存：16GB+
- 存储：SSD 500GB+

进阶配置:
- CPU: 16 核+
- 内存：32GB+
- GPU: RTX 3060+ (深度学习)
- 存储：SSD 1TB+

生产配置:
- 云服务器 (AWS/GCP/Azure)
- 分布式训练
- 实时推理服务
```

---

**文档完成时间：** 2026-03-12 02:55  
**研究员：** stock-filter-research-4 (Subagent)  
**状态：** 完成
