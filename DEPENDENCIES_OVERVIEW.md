# 量化回测选股项目依赖清单

> 按你的要求，这里只保留“名称”为主，不展开安装命令。

## 一、Python 运行环境
- Python 3.10
- pip
- conda（如使用现有 vnpy_env）

## 二、当前核心代码直接依赖
基于以下核心代码抽取：
- `data/agents/master/modules/risk_engine.py`
- `data/agents/master/modules/strategy_core.py`
- `data/agents/master/plugins/strategy_ensemble.py`
- `data/agents/master/vnpy_backtest/backtest_engine.py`

### 直接三方库
- numpy
- pandas

## 三、量化/回测场景建议保留的基础组件
这些名称在当前工程规则和文档中反复出现，建议作为环境基座保留：
- vnpy
- qlib

## 四、常见配套能力组件（按工程用途归类）
### 数据处理
- numpy
- pandas

### 回测/量化框架
- vnpy
- qlib

### 配置与序列化
- PyYAML

### 可视化/分析（如后续补充报告）
- matplotlib
- seaborn

### 研究开发常用
- jupyter
- notebook
- ipykernel

## 五、系统/运行侧需要具备的东西（名称）
- Git
- GitHub 访问权限
- 可用的网络出口（用于推送 GitHub）

## 六、当前代码中使用到的标准库（无需额外安装）
- json
- datetime
- time
- pathlib
- typing

## 七、建议的最小可运行名称集
如果你只想先配最小集，可以先准备：
- Python
- pip
- numpy
- pandas
- vnpy
- qlib
- Git
