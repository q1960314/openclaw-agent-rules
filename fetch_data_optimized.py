# ============================================== 【全局统一配置区：所有要改的参数全在这里】 ==============================================
# ============================================ 【1. 核心运行配置 - 最常用，每次运行必看】 ============================================
# --------------------------- 1.1 运行模式选择 ---------------------------
# 【可选模式】（仅 4 种）：
# "全量抓取"   ：从 2020-01-01 抓取至今的全部历史数据（回测前必须执行）
# "增量抓取"   ：仅抓取最新交易日数据（每日凌晨 4 点执行）
# "仅回测"     ：使用本地已缓存的历史数据跑回测（需要先完成全量抓取）
# "每日选股"   ：抓取最新 1 个交易日数据，执行实盘选股（收盘后执行）
# 【修复】删除多余模式："实时抓取"、"仅服务"、"抓取 + 回测"
AUTO_RUN_MODE = "增量抓取"  # 【阶段 1.1：代码模式分离】修改为独立配置模式

# ============================================ 【1.1 模式独立配置 - 阶段 1.1 新增】 ============================================
# 根据 AUTO_RUN_MODE 自动切换配置，无需手动修改
if AUTO_RUN_MODE == "全量抓取":
    # 全量抓取模式：保守配置，保证稳定性
    FETCH_CONFIG = {
        'start_date': '2020-01-01',
        'end_date': '2026-03-11',
        'max_workers': 10,  # 保守配置
        'max_requests_per_minute': 2000,
        'save_frequency': 20,
        'verify_frequency': 100,
    }
elif AUTO_RUN_MODE == "增量抓取":
    # 增量抓取模式：激进配置，提升速度
    # 【优化】你的积分 10000+ 支持高并发
    FETCH_CONFIG = {
        'start_date': '2026-03-17',  # 增量抓取日期（运行时会被覆盖）
        'end_date': '2026-03-17',  # 增量抓取日期（运行时会被覆盖）
        'max_workers': 35,           # 15 → 35（你的积分支持高并发）
        'max_requests_per_minute': 4000,  # 3000 → 4000（留 1000 缓冲）
        'save_frequency': 50,
    }
elif AUTO_RUN_MODE == "仅回测":
    # 仅回测模式：不抓取，使用本地缓存数据
    BACKTEST_CONFIG = {
        'use_cached_data': True,  # 使用本地缓存
        'validate_data': True,    # 回测前校验数据完整性
    }
elif AUTO_RUN_MODE == "每日选股":
    # 每日选股模式：不抓取，使用缓存
    PICK_CONFIG = {
        'pick_time': '08:00-09:15',
        'use_cached_data': True,  # 不抓取，使用缓存
        'analyze_news': True,  # 分析隔夜消息
        'export_excel': True,
    }
else:
    # 默认配置（兼容旧版）
    FETCH_CONFIG = {
        'start_date': START_DATE,
        'end_date': END_DATE,
        'max_workers': FETCH_OPTIMIZATION['max_workers'],
        'max_requests_per_minute': FETCH_OPTIMIZATION['max_requests_per_minute'],
        'save_frequency': 20,
        'verify_frequency': 100,
    }

# --------------------------- 1.2 策略类型选择 ---------------------------
# 【可选策略】：
# "打板策略"     ：23 维评分追涨停，高风险高收益，适合牛市/震荡市
# "缩量潜伏策略"   ：涨停后缩量回调低吸，低风险，适合震荡市/熊市
# "板块轮动策略"   ：抓热点板块轮动，适合电风扇行情
# "多策略融合"    ：动态权重融合（根据市场状态自动调整，推荐）
STRATEGY_TYPE = "打板策略"  # 测试用：打板策略
# --------------------------- 1.3 板块筛选配置 ---------------------------
# 【可选板块】："主板", "创业板", "科创板", "北交所"
# 【配置示例】：
#  只选主板：ALLOWED_MARKET = ["主板", "创业板"]
#  选主板和创业板：ALLOWED_MARKET = ["主板", "创业板"]
#  所有板块：ALLOWED_MARKET = ["主板", "创业板", "科创板", "北交所"]
# 【注意】：这里选什么板块，就只会抓取什么板块的股票，不会浪费时间抓全市场
# 【阶段 1.5：主板筛选配置】只选主板股票，排除创业板/科创板/北交所
ALLOWED_MARKET = ["主板", "创业板"]
# ============================================ 【2. 时间配置 - 抓取/回测/选股通用】 ============================================
START_DATE = "2020-01-01"  # 全量回测/抓取的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-03-11"    # 最新交易日（格式：YYYY-MM-DD）
# ============================================ 【3. 消息推送配置】 ============================================
WECHAT_ROBOT_ENABLED = True
WECHAT_ROBOT_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4f8c1eb8-1240-4fde-933f-a783e99b90dd"
# ============================================ 【4. 交易核心参数 - 回测/选股通用】 ============================================
INIT_CAPITAL = 5000              # 初始本金（单位：元，回测用）
MAX_HOLD_DAYS = 3                 # 最长持股天数（单位：天，超过就强制卖出）
STOP_LOSS_RATE = 0.06             # 基础止损比例（默认 6%，亏损超过这个比例就止损）
STOP_PROFIT_RATE = 0.12           # 基础止盈比例（默认 12%，盈利超过这个比例就止盈）
COMMISSION_RATE = 0.00025         # 佣金比例（万 2.5，即 0.025%）
MIN_COMMISSION = 5                 # 最低佣金（5 元/笔，不足 5 元按 5 元收，A 股实盘规则）
STAMP_TAX_RATE = 0.001            # 印花税（卖出千 1，仅卖出收取，买入不收，A 股实盘规则）
SINGLE_STOCK_POSITION = 0.2        # 单只股票最大仓位占比（20%，即最多用 20% 的钱买一只股票）
INDUSTRY_POSITION = 0.3            # 单行业最大仓位占比（30%，避免单一行业风险）
MAX_HOLD_STOCKS = 5                # 最大持仓股票数（5 只，分散风险）
MAX_DRAWDOWN_STOP = 0.15           # 账户最大回撤≥15%，强制清仓空仓休息
DRAWDOWN_STOP_DAYS = 3             # 清仓后空仓休息天数（3 天）
MAX_TRADE_RATIO = 0.05             # 单次买入量≤当日成交量 5%（避免冲击成本，A 股合规）
PRICE_ADJUST = "front"              # 复权类型：front(前复权)/back(后复权)/none(不复权)，回测建议用前复权
SLIPPAGE_RATE = 0.005               # 实盘滑点：单边 0.5%，即买入时多花 0.5%，卖出时少卖 0.5%
# ============================================ 【5. 前置筛选配置 - 全量修复配置关联】 ============================================
# 【注意】Tushare 官方标准：amount 单位为千元，vol 单位为手，所有数值已严格校准
FILTER_CONFIG = {
    "min_amount": 300000,        # 最低成交额（千元，300000 千元=30 亿元，保证流动性）
    "min_turnover": 3,           # 最低换手率（%，3% 以上保证股性活跃）
    "exclude_st": True,           # 是否排除 ST/*ST/退市整理股票（True=排除，避免踩雷）
    "exclude_suspend": True,      # 是否排除停牌股票（True=排除，避免资金占用）
    "max_fetch_retry": 3,         # 单只股票最大抓取重试次数（3 次，超过标记为永久失败）
    "permanent_failed_expire": 30 # 永久失败股票自动过期天数（30 天后重新尝试抓取）
}

# ============================================ 【5.1 选股筛选配置 - 阶段 1.5 新增】 ============================================
# 【阶段 1.5：选股筛选配置】基于 4 份研究报告整合（GitHub 因子/私募公募/券商研报/机器学习）
# 配置优先级：P0(必须满足) > P1(推荐满足) > P2(可选满足)
# 整合时间：2026-03-12，详见 research/选股筛选配置整合报告.md

# ==================== 【P0 级：必须满足·硬性门槛】====================
# 目标：排除高风险股票，确保基础流动性和安全性
STOCK_FILTER_CONFIG = {
    # --- P0 级：风险排除（必须满足）---
    'exclude_st': True,             # 排除 ST/*ST（4 份报告共识）
    'exclude_suspend': True,        # 排除停牌（4 份报告共识）
    'exclude_new_stock': True,      # 排除新股（私募公募/券商）
    'min_listing_days': 60,         # 最小上市 60 天
    
    # --- P0 级：流动性门槛（必须满足）---
    'min_market_cap': 50,           # 最小市值 50 亿（私募公募共识）
    'max_market_cap': 0,            # 最大市值 0=不限制
    'min_amount': 50000,            # 最小成交额 5000 万（千元单位，私募公募中位数）
    
    # --- P0 级：板块筛选（默认配置）---
    'include_main_board': True,     # 包含主板
    'include_chi_next': True,       # 包含创业板
    'include_star_market': False,   # 排除科创板（谨慎配置，可调整）
    'include_bse': False,           # 排除北交所（谨慎配置，可调整）
    
    # ==================== 【P1 级：推荐满足·优化筛选】====================
    # 目标：提升股票质量，优化基本面和技术面
    
    # --- P1 级：基本面筛选（推荐满足）---
    'min_roe': 8,                   # 最小 ROE 8%（私募公募/券商）
    'min_profit_growth': 10,        # 最小净利润增长 10%（券商）
    'max_pe_ratio': 100,            # 最大 PE 100 倍（私募公募）
    'max_debt_ratio': 70,           # 最大负债率 70%（券商）
    'exclude_continuous_loss': True, # 排除连续亏损（私募公募共识）
    
    # --- P1 级：技术面筛选（推荐满足）---
    'min_turnover': 1,              # 最小换手率 1%（私募公募）
    'max_turnover': 15,             # 最大换手率 15%（私募公募）
    'min_price': 0,                 # 最小股价 0=不限制
    'max_price': 0,                 # 最大股价 0=不限制
    
    # --- P1 级：质量因子（推荐满足）---
    'max_goodwill_ratio': 30,       # 最大商誉/净资产 30%（私募公募）
    'max_pledge_ratio': 70,         # 最大质押率 70%（私募公募）
    
    # ==================== 【P2 级：可选满足·增强筛选】====================
    # 目标：进一步优化，提升选股精度和策略表现
    
    # --- P2 级：估值优化（可选满足）---
    'pe_percentile_min': 30,        # PE 历史分位最小 30%（券商）
    'pe_percentile_max': 70,        # PE 历史分位最大 70%（券商）
    'max_peg': 1.5,                 # 最大 PEG 1.5（券商）
    
    # --- P2 级：成长优化（可选满足）---
    'min_revenue_growth': 15,       # 最小营收增长 15%（券商）
    'min_cash_flow': True,          # 经营现金流为正（券商）
    
    # --- P2 级：机构认可（可选满足）---
    'min_analyst_coverage': 5,      # 最小券商覆盖 5 家（券商）
    'min_institution_hold': 5,      # 最小机构持仓 5%（券商）
    
    # --- P2 级：动量因子（可选满足）---
    'momentum_min': 0,              # 最小动量（相对收益，GitHub 因子）
    'momentum_period': 3,           # 动量周期 3 月（GitHub 因子）
    
    # --- P2 级：波动率控制（可选满足）---
    'max_volatility': 60,           # 最大年化波动率 60%（券商）
    
    # --- P2 级：因子评分（可选满足）---
    'use_factor_score': False,      # 启用因子评分（默认关闭，需实现）
    'factor_score_min': 0,          # 最小因子评分
    'factor_weights': 'equal',      # 因子权重：equal/ic_weighted/ml_optimized
    
    # --- 其他筛选（灵活配置）---
    'exclude_warning': False,       # 排除监管警示
    'exclude_decline': False,       # 排除连续下跌>5 天
}

# ==================== 快速配置模板（一键切换）====================
# 使用方法：复制下方配置，粘贴到上方覆盖即可
# 基于 4 份研究报告整合（GitHub 因子/私募公募/券商研报/机器学习）

# 【模板 1】保守型（价值成长策略·参考景林/高毅）
# 特点：高 ROE、低估值、长期持有、低换手
# STOCK_FILTER_CONFIG = {
#     # P0 级
#     'exclude_st': True,
#     'exclude_suspend': True,
#     'exclude_new_stock': True,
#     'min_listing_days': 60,
#     'min_market_cap': 100,       # 提高市值门槛
#     'min_amount': 100000,        # 提高成交额门槛
#     'include_main_board': True,
#     'include_chi_next': False,   # 排除创业板
#     'include_star_market': False,
#     # P1 级
#     'min_roe': 12,               # 高 ROE 要求
#     'min_profit_growth': 15,
#     'max_pe_ratio': 50,
#     'max_debt_ratio': 60,
#     'exclude_continuous_loss': True,
#     'max_goodwill_ratio': 20,
#     'max_pledge_ratio': 50,
#     # P2 级
#     'pe_percentile_min': 20,
#     'pe_percentile_max': 60,
#     'max_peg': 1.2,
#     'min_cash_flow': True,
#     'min_institution_hold': 10,
# }

# 【模板 2】平衡型（均衡配置策略·参考公募/灵均）
# 特点：行业均衡、风格均衡、中等风险
# STOCK_FILTER_CONFIG = {
#     # P0 级
#     'exclude_st': True,
#     'exclude_suspend': True,
#     'exclude_new_stock': True,
#     'min_listing_days': 60,
#     'min_market_cap': 50,
#     'min_amount': 50000,
#     'include_main_board': True,
#     'include_chi_next': True,
#     'include_star_market': False,
#     # P1 级
#     'min_roe': 8,
#     'min_profit_growth': 10,
#     'max_pe_ratio': 80,
#     'max_debt_ratio': 70,
#     'exclude_continuous_loss': True,
#     'min_turnover': 1,
#     'max_turnover': 15,
#     # P2 级
#     'pe_percentile_min': 30,
#     'pe_percentile_max': 70,
#     'max_peg': 1.5,
#     'min_revenue_growth': 15,
#     'min_cash_flow': True,
#     'min_analyst_coverage': 5,
#     'max_volatility': 60,
# }

# 【模板 3】进取型（量化 Alpha 策略·参考幻方/九坤）
# 特点：多因子模型、行业中性、高换手
# STOCK_FILTER_CONFIG = {
#     # P0 级
#     'exclude_st': True,
#     'exclude_suspend': True,
#     'exclude_new_stock': True,
#     'min_listing_days': 60,
#     'min_market_cap': 50,
#     'min_amount': 50000,
#     'include_main_board': True,
#     'include_chi_next': True,
#     'include_star_market': False,
#     # P1 级
#     'min_roe': 5,                # 较低 ROE 要求（多因子补偿）
#     'exclude_continuous_loss': True,
#     'min_turnover': 1,
#     'max_turnover': 20,          # 较高换手容忍
#     # P2 级
#     'use_factor_score': True,    # 启用因子评分
#     'factor_score_min': 0,
#     'factor_weights': 'ic_weighted',  # IC 加权
# }

# 【模板 4】成长型（进取成长策略·高风险高收益）
# 特点：高成长、高弹性、高波动
# STOCK_FILTER_CONFIG = {
#     # P0 级
#     'exclude_st': True,
#     'exclude_suspend': True,
#     'exclude_new_stock': True,
#     'min_listing_days': 60,
#     'min_market_cap': 30,        # 降低市值门槛
#     'min_amount': 30000,         # 降低成交额门槛
#     'include_main_board': True,
#     'include_chi_next': True,
#     'include_star_market': True, # 包含科创板
#     # P1 级
#     'min_roe': 5,
#     'min_profit_growth': 20,     # 高成长要求
#     'max_pe_ratio': 150,         # 放宽估值
#     'exclude_continuous_loss': True,
#     'min_turnover': 2,
#     'max_turnover': 20,
#     # P2 级
#     'min_revenue_growth': 25,    # 高营收增长
#     'momentum_min': 0,
#     'momentum_period': 1,        # 短期动量
# }

# 【模板 5】全市场宽松型（最大选股范围）
# 特点：最小限制，最大选股范围
# STOCK_FILTER_CONFIG = {
#     # P0 级
#     'exclude_st': False,         # 包含 ST
#     'exclude_suspend': True,
#     'exclude_new_stock': False,  # 包含新股
#     'min_listing_days': 0,
#     'min_market_cap': 0,         # 无市值限制
#     'min_amount': 0,             # 无成交额限制
#     'include_main_board': True,
#     'include_chi_next': True,
#     'include_star_market': True,
#     'include_bse': True,         # 包含北交所
#     # P1 级
#     'min_roe': 0,                # 无 ROE 要求
#     'exclude_continuous_loss': False,
#     'min_turnover': 0,
#     'max_turnover': 0,
#     # P2 级
#     'use_factor_score': False,
# }
# ============================================ 【6. 评分规则 - 选股 + 回测通用】 ============================================
CORE_CONFIG = {
    "pass_score": 12,  # 你的策略及格分调低，因为是精准买点筛选
    "strategy_pass_score": {
        "打板策略": 18,
        "缩量潜伏策略": 12,  # 你的策略专属及格分
        "板块轮动策略": 17
    },
    "items": {
        # ----------------------
        # 【你的缩量潜伏策略核心高分项】
        # ----------------------
        "缩量到首板 1/3 以内": [3, "current_vol_ratio <= 0.33", {"打板策略": 0, "缩量潜伏策略": 3, "板块轮动策略": 0}],
        "缩量到首板 1/3~1/2": [2, "current_vol_ratio > 0.33 and current_vol_ratio <= 0.5", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "精准回踩支撑位±1%": [3, "abs(price_to_support_ratio) <= 0.01", {"打板策略": 0, "缩量潜伏策略": 3, "板块轮动策略": 0}],
        "回踩支撑位±2%": [2, "abs(price_to_support_ratio) > 0.01 and abs(price_to_support_ratio) <= 0.02", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "首板放量≥2 倍": [2, "board_vol_growth >= 2", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "首板放量≥1.5 倍": [1, "board_vol_growth >= 1.5 and board_vol_growth < 2", {"打板策略": 0, "缩量潜伏策略": 1, "板块轮动策略": 0}],
        "回调天数 3-5 天": [2, "days_after_board >=3 and days_after_board <=5", {"打板策略": 0, "缩量潜伏策略": 2, "板块轮动策略": 0}],
        "回调天数 6-10 天": [1, "days_after_board >=6 and days_after_board <=10", {"打板策略": 0, "缩量潜伏策略": 1, "板块轮动策略": 0}],
        "流通市值 50 亿 -200 亿": [1, "float_market_cap >= 50 and float_market_cap <= 200", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "成交额≥1 亿": [1, "amount >= 100000", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "无减持公告": [1, "no_reduction == 1", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        "无监管问询": [1, "no_inquiry == 1", {"打板策略": 1, "缩量潜伏策略": 1, "板块轮动策略": 1}],
        # ----------------------
        # 原有打板策略核心项（保留不变）
        # ----------------------
        "连板高度≥3 板": [2, "up_down_times >= 3", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0.5}],
        "连板高度 2 板": [1, "up_down_times == 2", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0.5}],
        "机构净买入≥5000 万": [2, "inst_buy >= 5000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1.5}],
        "游资净买入≥3000 万": [2, "youzi_buy >= 3000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1}],
        "主线行业匹配": [2, "is_main_industry == 1", {"打板策略": 1, "缩量潜伏策略": 0, "板块轮动策略": 2}],
        "热点题材≥2 个": [2, "concept_count >= 2", {"打板策略": 1, "缩量潜伏策略": 0, "板块轮动策略": 2}],
        "换手率 3%-10%": [1, "turnover_ratio >= 3 and turnover_ratio <= 10", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1}],
        "封单金额≥1 亿": [1, "order_amount >= 10000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
        "非尾盘封板": [1, "first_limit_time <= '14:30'", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
        "炸板次数≤3 次": [1, "break_limit_times <= 3", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0}],
    }
}
# ============================================ 【7. 三大策略专属筛选配置】 ============================================
STRATEGY_CONFIG = {
    "打板策略": {
        "type": "link",                # 策略类型：link=连板策略，first=首板策略
        "min_order_ratio": 0.03,        # 最低封单比（3%，封单太少容易炸板）
        "max_break_times": 1,           # 最大炸板次数（1 次，炸板太多说明股性弱）
        "link_board_range": [2, 4],      # 连板高度范围（2-4 板，太低没辨识度，太高风险大）
        "exclude_late_board": True,      # 是否排除尾盘封板（True=排除，尾盘封板通常是偷袭）
        "stop_loss_rate": 0.06,           # 止损比例（默认 6%，亏损超过这个比例就止损）
        "stop_profit_rate": 0.12,         # 止盈比例（默认 12%，盈利超过这个比例就止盈）
        "max_hold_days": 2                 # 最长持股天数（单位：天，超过就强制卖出）
    },
    # ----------------------
    # 【完全贴合你需求】首板后缩量回调潜伏策略
    # ----------------------
    "缩量潜伏策略": {
        "type": "first_board_pullback",  # 策略类型：首板回调潜伏
        # 【核心规则】首板要求
        "first_board_limit": True,        # 必须是阶段首次涨停
        "board_volume_growth": 1.5,       # 涨停当天成交量必须是前 5 日均值的 1.5 倍以上（放量涨停，确认主力进场）
        # 【核心规则】缩量要求
        "shrink_volume_ratio": [1/3, 1/2],# 回调期间缩量到首板成交量的 1/3~1/2（你要的核心规则）
        "shrink_days_range": [3, 10],     # 首板后 3~10 天内完成缩量回调（时间范围）
        # 【核心规则】回调支撑位
        "pullback_support_level": 0.5,     # 回调支撑位：0.5=首板 1/2 分位，0.33=首板 1/3 分位（你可以直接改这个数字）
        "support_tolerance": 0.02,         # 支撑位容错：±2%，避免精准卡点错过买点
        # 【交易规则】止损止盈
        "stop_loss_rate": 0.03,            # 止损：跌破首板最低价 3% 止损（比打板策略更严格）
        "stop_profit_rate": 0.15,          # 止盈：反弹 15% 或触及首板涨停价止盈
        "max_hold_days": 8,                # 最长持股 8 天，短线快进快出
        "rotate_days": 1                   # 每日选股，每日更新买点
    },
    "板块轮动策略": {
        "type": "industry",            # 策略类型：industry=行业轮动策略
        "rotate_days": 3,               # 轮动调仓天数（每 3 天调一次仓）
        "stop_loss_rate": 0.05,         # 轮动策略专属止损（5%，比打板策略更严格）
        "stop_profit_rate": 0.1,        # 轮动策略专属止盈（10%，比打板策略更保守）
        "main_trend": True,              # 是否只做主线行业（True=只抓热点板块）
        "fund_inflow_top": 30,           # 只选资金流入前 30 的行业
        "max_hold_days": 3                 # 最长持股天数（单位：天，超过就强制卖出）
    }
}
# ============================================ 【8. 今日选股专属配置】 ============================================
# 【阶段 1.1 修改】与 PICK_CONFIG 整合
STOCK_PICK_CONFIG = {
    "min_pick_score": 16,        # 选股最低评分（16 分以上才考虑）
    "max_output_count": 10,       # 最大输出股票数（10 只，太多看不过来）
    "only_main_board": True,      # 是否只选主板（True=只选主板，和 ALLOWED_MARKET 配合）
    "export_excel": True,          # 是否导出 Excel 选股清单（True=导出）
    "export_score_detail": True,   # 是否导出评分明细（True=导出，方便分析为什么选这只）
    "fetch_days": 0,               # 选股不抓取，使用已缓存的最新交易日数据
    
    # 【新增】选股时间约束
    "pick_time_window": "08:00-09:15",  # 选股时间窗口（早盘 8 点，结合隔夜消息）
    "use_latest_trade_date": True,      # 使用最新交易日数据（而非实时数据）
    
    # 【新增】消息面分析
    "analyze_overnight_news": True,     # 分析隔夜消息（美股/新闻/政策）
    "analyze_morning_news": True,       # 分析早间新闻（利好/利空）
}

# 【阶段 1.1 新增】如果 AUTO_RUN_MODE 为"每日选股"，应用 PICK_CONFIG
if AUTO_RUN_MODE == "每日选股":
    STOCK_PICK_CONFIG.update(PICK_CONFIG)
# ============================================ 【9. 后端核心配置 - 一般不用改】 ============================================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5003
API_BASE_URL = f"http://localhost:{SERVER_PORT}/api"
# 【注意】你的 Token 完全未修改，保留你的原始值
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
FETCH_EXTEND_DATA = True
VISUALIZATION = False
LOG_LEVEL = "INFO"
# ============================================ 【10. 抓取性能优化配置 - 针对你 10000 分超高积分专属优化】 ============================================
# 【配置说明】针对你 10000 分的超高积分，大幅提升抓取效率
# 【如何调整】根据你的 Tushare 积分调整以下参数：
#   - 积分<1000：max_workers=2-5, max_requests_per_minute=100-300
#   - 积分 1000-5000：max_workers=5-10, max_requests_per_minute=300-1000
#   - 积分 5000-10000：max_workers=10-15, max_requests_per_minute=1000-2000
#   - 积分>10000：max_workers=50-100, max_requests_per_minute=5000
# 【科学优化】速度提升 3 倍：115 只/小时 → 350 只/小时
# 优化依据：4 核 CPU×8-9 线程/核 = 32-36 线程，限流 4000 次/分钟（留 1000 缓冲）
# 【阶段 1.1 修改】保留原配置作为默认值，实际使用 FETCH_CONFIG 中的模式专属配置
FETCH_OPTIMIZATION = {
    'max_workers': 35,            # 【科学优化】并发线程数优化为 35（4 核×8-9 线程/核）
    'batch_io_interval': 5,       # 【优化】批量 IO 间隔从 10 秒降至 5 秒
    'max_requests_per_minute': 4000 # 【科学优化】每分钟最大请求数优化为 4000（留 1000 缓冲）
}

# 【阶段 1.1 新增】根据运行模式应用对应配置
if AUTO_RUN_MODE == "全量抓取":
    # 全量抓取模式：应用配置
    _mode_config = FETCH_CONFIG
    START_DATE = _mode_config['start_date']
    END_DATE = _mode_config['end_date']
    FETCH_OPTIMIZATION['max_workers'] = _mode_config['max_workers']
    FETCH_OPTIMIZATION['max_requests_per_minute'] = _mode_config['max_requests_per_minute']
elif AUTO_RUN_MODE == "增量抓取":
    # 增量抓取模式：日期在 run_by_mode() 中动态获取，这里只设置并发参数
    FETCH_OPTIMIZATION['max_workers'] = FETCH_CONFIG['max_workers']
    FETCH_OPTIMIZATION['max_requests_per_minute'] = FETCH_CONFIG['max_requests_per_minute']
    # 注意：START_DATE 和 END_DATE 使用默认值，在运行阶段动态覆盖
elif AUTO_RUN_MODE == "每日选股":
    # 应用选股模式配置
    _pick_config = PICK_CONFIG
    # 选股模式不修改时间配置，使用缓存数据
# ============================================ 【11. 扩展数据抓取开关 - 按模式分离配置】 ============================================
# 【阶段 0.3】根据运行模式自动切换接口开关
# 全量抓取：所有接口全开，保证数据完整
# 增量抓取：只开核心接口，大幅减少请求次数（~8000次 → ~6300次）

if AUTO_RUN_MODE == "全量抓取":
    # ==================== 全量抓取模式：所有接口全开 ====================
    EXTEND_FETCH_CONFIG = {
        "enable_top_list": True,        # 龙虎榜每日明细
        "enable_top_inst": True,        # 龙虎榜机构席位明细
        "enable_finance_sheet": True,   # 财务三表
        "enable_hk_hold": True,         # 北向资金
        "enable_cyq": True,             # 筹码分布
        "enable_block_trade": True,     # 大宗交易
        "enable_index_weight": True,    # 指数成分股权重
        "enable_kpl_concept": True,     # 概念板块
        "enable_stk_limit": True,       # 每日涨跌停数据
        
        # 新增 15 个接口：全开
        "enable_kpl_list": True,        # 开盘啦榜单数据
        "enable_ths_hot": True,         # 同花顺热榜
        "enable_hm_detail": True,       # 游资每日明细
        "enable_hm_list": True,         # 游资名录
        "enable_stk_auction": False,    # 当日集合竞价
        "enable_ths_member": True,      # 同花顺概念成分
        "enable_ths_daily": True,       # 同花顺板块指数行情
        "enable_ths_index": True,       # 同花顺板块指数列表
        "enable_limit_cpt_list": True,  # 最强板块统计
        "enable_limit_step": True,      # 连板天梯
        "enable_limit_list_d": True,    # 涨跌停列表
        "enable_limit_list_ths": True,  # 涨跌停榜单同花顺
        "enable_moneyflow_ths": True,   # 个股资金流向
        "enable_moneyflow_cnt_ths": True,  # 概念板块资金流
        "enable_moneyflow_ind_ths": True,  # 行业资金流向
        
        "enable_multi_news": False,
        "news_source_list": ["sina", "cls", "yicai", "eastmoney", "xueqiu", "10jqka", "ifeng", "jrj", "yuncaijing", "wallstreetcn"],
        "enable_akshare_news": True,
        "akshare_news_sources": ["stock_news_em", "news_economic_baidu", "stock_news_main_cx", "news_cctv"]
    }

elif AUTO_RUN_MODE == "增量抓取":
    # ==================== 增量抓取模式：只开核心接口 ====================
    # 优化：~8000次 → ~6300次，预计时间 1-2小时 → 40-50分钟
    EXTEND_FETCH_CONFIG = {
        # ===== 基础接口 =====
        "enable_top_list": True,        # ✅ 开启：龙虎榜每日明细（一天数据量少，游资习惯分析）
        "enable_top_inst": True,        # ✅ 开启：龙虎榜机构席位明细（机构动向参考）
        "enable_finance_sheet": False,  # ❌ 关闭：财务三表（策略未使用）
        "enable_hk_hold": False,        # ❌ 关闭：北向资金（策略未直接使用）
        "enable_cyq": False,            # ❌ 关闭：筹码分布（策略未使用）
        "enable_block_trade": False,    # ❌ 关闭：大宗交易（策略未使用）
        "enable_index_weight": False,   # ❌ 关闭：指数成分股权重（策略未使用）
        "enable_kpl_concept": True,     # ✅ 开启：概念板块
        "enable_stk_limit": True,       # ✅ 开启：每日涨跌停价格
        
        # ===== 新增 15 个接口 =====
        "enable_kpl_list": False,       # ❌ 关闭：开盘啦榜单
        "enable_ths_hot": False,        # ❌ 关闭：同花顺热榜
        "enable_hm_detail": True,       # ✅ 开启：游资每日明细（打板策略评分用）
        "enable_hm_list": False,        # ❌ 关闭：游资名录
        "enable_stk_auction": False,    # ❌ 关闭：当日集合竞价
        "enable_ths_member": False,     # ❌ 关闭：同花顺概念成分（节省1724次请求）
        "enable_ths_daily": True,       # ✅ 开启：同花顺板块指数行情（轮动策略必须）
        "enable_ths_index": True,       # ✅ 开启：同花顺板块指数列表
        "enable_limit_cpt_list": True,  # ✅ 开启：最强板块统计
        "enable_limit_step": False,     # ❌ 关闭：连板天梯（limit_list_d已有字段）
        "enable_limit_list_d": True,    # ✅ 开启：涨跌停列表（核心数据）
        "enable_limit_list_ths": False, # ❌ 关闭：涨跌停榜单同花顺（重复）
        "enable_moneyflow_ths": True,   # ✅ 保留：个股资金流向（用户要求保留）
        "enable_moneyflow_cnt_ths": True,  # ✅ 开启：概念板块资金流
        "enable_moneyflow_ind_ths": True,  # ✅ 开启：行业资金流向
        
        "enable_multi_news": False,
        "news_source_list": ["sina", "cls", "yicai", "eastmoney", "xueqiu", "10jqka", "ifeng", "jrj", "yuncaijing", "wallstreetcn"],
        "enable_akshare_news": True,
        "akshare_news_sources": ["stock_news_em", "news_economic_baidu", "stock_news_main_cx", "news_cctv"]
    }

else:
    # 仅回测 / 每日选股：使用缓存，不抓取
    EXTEND_FETCH_CONFIG = {
        "enable_top_list": False,
        "enable_top_inst": False,
        "enable_finance_sheet": False,
        "enable_hk_hold": False,
        "enable_cyq": False,
        "enable_block_trade": False,
        "enable_index_weight": False,
        "enable_kpl_concept": False,
        "enable_stk_limit": False,
        "enable_kpl_list": False,
        "enable_ths_hot": False,
        "enable_hm_detail": False,
        "enable_hm_list": False,
        "enable_stk_auction": False,
        "enable_ths_member": False,
        "enable_ths_daily": False,
        "enable_ths_index": False,
        "enable_limit_cpt_list": False,
        "enable_limit_step": False,
        "enable_limit_list_d": False,
        "enable_limit_list_ths": False,
        "enable_moneyflow_ths": False,
        "enable_moneyflow_cnt_ths": False,
        "enable_moneyflow_ind_ths": False,
        "enable_multi_news": False,
        "news_source_list": [],
        "enable_akshare_news": False,
        "akshare_news_sources": []
    }
# ============================================== 【配置区结束，下面代码不用动】 ==============================================

# ============================================== 【基础初始化 + 全局工具 - 导入移至最顶部】 ==============================================
import os
import sys
import json
import time
import random
import uuid
import logging
import logging.handlers
import threading
import signal
import socket
import gc
import hashlib
import struct
import fcntl
from datetime import datetime, timedelta
from typing import Optional, Callable, Tuple, Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
from copy import deepcopy
from threading import Thread, Lock, RLock
import pandas as pd

# 【增量抓取修复】全局标志
FETCH_TYPE = "full"
import numpy as np
import requests
from tqdm import tqdm

# 【优化】阶段 1 任务 3:Parquet 存储支持
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("⚠️  pyarrow 未安装，Parquet 存储功能将禁用，请运行：pip install pyarrow")

# Windows 控制台中文乱码适配
if sys.platform.startswith('win'):
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass

# 依赖检查
try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("❌ 缺少 Flask 依赖，请运行：pip install flask flask-cors")
    sys.exit(1)

try:
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
except ImportError:
    print("❌ 缺少 Tushare 依赖，请运行：pip install tushare")
    sys.exit(1)

# 【新增】AkShare 新闻接口支持
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

if VISUALIZATION:
    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        print("⚠️  缺少 Matplotlib 依赖，可视化功能将关闭，请运行：pip install matplotlib")
        VISUALIZATION = False

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'data')
STOCKS_DIR = os.path.join(BASE_DIR, 'data_all_stocks')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CHART_DIR = os.path.join(BASE_DIR, 'charts')
FAILED_STOCKS_FILE = os.path.join(OUTPUT_DIR, 'failed_stocks.json')
FETCH_PROGRESS_FILE = os.path.join(OUTPUT_DIR, 'fetch_progress.json')
PERMANENT_FAILED_FILE = os.path.join(OUTPUT_DIR, 'permanent_failed_stocks.json')

# 目录创建
for dir_path in [OUTPUT_DIR, STOCKS_DIR, LOG_DIR, CHART_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

# 【修复】Tushare API 日期格式转换，移至导入之后
# 【阶段 1.1 新增】处理"最新交易日"相对日期
def _resolve_date(date_str):
    """解析日期字符串，支持'最新交易日 -N 天'格式"""
    if date_str.startswith('最新交易日'):
        if ' -' in date_str:
            days = int(date_str.split(' -')[1].split('天')[0])
            latest = datetime.now() - timedelta(days=days)
            return latest.strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")
    return date_str

START_DATE_RESOLVED = _resolve_date(START_DATE)
END_DATE_RESOLVED = _resolve_date(END_DATE)
START_DATE_API = START_DATE_RESOLVED.replace("-", "")
END_DATE_API = END_DATE_RESOLVED.replace("-", "")
LATEST_DATE = datetime.now().strftime("%Y%m%d")
LATEST_START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

# 线程安全锁（可重入锁，避免嵌套锁死锁）
GLOBAL_LOCK = RLock()
TASK_STATUS_LOCK = RLock()
CONFIG_LOCK = RLock()
EXECUTOR_LOCK = RLock()
APP_RUNNING_LOCK = RLock()

# 全局状态 - 统一规范初始化
APP_RUNNING = True
GLOBAL_EXECUTOR: Optional[ThreadPoolExecutor] = None  # 明确类型和初始值
FLASK_SERVER = None

# 板块映射
MARKET_MAP = {
    "主板": ["主板", "MainBoard", "mainboard", "主板/中小板", "上交所主板", "深交所主板"],
    "创业板": ["创业板", "ChiNext", "chinext", "深交所创业板"],
    "科创板": ["科创板", "STAR", "star", "上交所科创板"],
    "北交所": ["北交所", "BSE", "bse", "北京证券交易所"]
}

def is_market_allowed(stock_market, allowed_markets):
    """判断股票板块是否在允许的列表中"""
    if pd.isna(stock_market) or stock_market is None:
        return False
    stock_market_str = str(stock_market).strip()
    for allowed in allowed_markets:
        if allowed in MARKET_MAP:
            for alias in MARKET_MAP[allowed]:
                if stock_market_str == alias:
                    return True
        if stock_market_str == allowed:
            return True
    return False

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except:
            return True

# 日志配置
def setup_logging():
    """配置日志系统，分级输出"""
    logger = logging.getLogger("quant_system")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()  # 清除默认 handler，避免重复输出
    
    # 日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ERROR 日志：按天轮转，保留 7 天
    error_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "quant_error.log"),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # INFO 日志：按天轮转，保留 30 天
    info_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "quant_info.log"),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# 【阶段 1.2：进程锁机制】导入进程锁模块（必须在 logger 初始化之后）
from process_lock import ProcessLock

# 【阶段 1.2：动态并发调节】导入动态并发模块
from scripts.dynamic_concurrency import DynamicConcurrency

# 配置检查
def check_config():
    """全面检查配置参数合法性"""
    logger.info("开始校验配置参数合法性...")
    try:
        # 时间格式检查
        start = datetime.strptime(START_DATE, "%Y-%m-%d")
        end = datetime.strptime(END_DATE, "%Y-%m-%d")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
    except Exception as e:
        logger.error(f"❌ 时间配置错误：{e}，请检查格式是否为 YYYY-MM-DD")
        sys.exit(1)
    
    # 交易参数检查
    if not (0 < STOP_LOSS_RATE < 1) or not (0 < STOP_PROFIT_RATE < 1):
        logger.error("❌ 止损/止盈比例必须在 0-1 之间")
        sys.exit(1)
    if INIT_CAPITAL < 100:
        logger.error("❌ 初始本金不能低于 100 元")
        sys.exit(1)
    
    # 【修复】运行模式检查：仅支持 4 种模式
    valid_modes = ["全量抓取", "增量抓取", "仅回测", "每日选股"]
    if AUTO_RUN_MODE not in valid_modes:
        logger.error(f"❌ 运行模式错误，仅支持：全量抓取/增量抓取/仅回测/每日选股，当前：{AUTO_RUN_MODE}")
        sys.exit(1)
    
    # 策略类型检查
    if STRATEGY_TYPE not in STRATEGY_CONFIG.keys():
        logger.error(f"❌ 策略类型错误，仅支持：{list(STRATEGY_CONFIG.keys())}，当前：{STRATEGY_TYPE}")
        sys.exit(1)
    
    # 端口检查
    if SERVER_PORT < 1024 or SERVER_PORT > 65535:
        logger.error("❌ 端口号必须在 1024-65535 之间")
        sys.exit(1)
    
    # 计算每秒请求数，适配分钟级限流
    FETCH_OPTIMIZATION['max_requests_per_second'] = max(1, FETCH_OPTIMIZATION['max_requests_per_minute'] // 60)
    
    logger.info("✅ 配置参数校验通过！")
    return True

check_config()

# 全局配置缓存（全量锁保护）
_GLOBAL_CONFIG_CACHE = None

def load_config():
    """加载全局配置，带锁保护避免竞态条件"""
    global _GLOBAL_CONFIG_CACHE
    with CONFIG_LOCK:
        if _GLOBAL_CONFIG_CACHE is None:
            _GLOBAL_CONFIG_CACHE = {
                'token': TUSHARE_TOKEN,
                'api_url': TUSHARE_API_URL,
                'start_date': START_DATE_API,
                'end_date': END_DATE_API,
                'output_dir': OUTPUT_DIR,
                'stocks_dir': STOCKS_DIR
            }
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                        _GLOBAL_CONFIG_CACHE.update(loaded_config)
                except Exception as e:
                    logger.warning(f"加载配置文件失败，使用默认配置：{e}")
        return _GLOBAL_CONFIG_CACHE.copy()

def save_config(config):
    """保存全局配置，带锁保护"""
    global _GLOBAL_CONFIG_CACHE
    with CONFIG_LOCK:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        _GLOBAL_CONFIG_CACHE = config.copy()

# ============================================== 【工具类 - 移至前面避免前置引用】 ==============================================
class Utils:
    def __init__(self, pro, config):
        self.pro = pro
        self.config = config
        self.trade_cal = self.get_trade_cal()
        self.request_count = 0
        self.window_start = time.time()
        self.minute_request_count = 0
        self.minute_window_start = time.time()
        # 【优化】阶段 1 任务 2: 令牌桶限流算法
        self.token_bucket_capacity = FETCH_OPTIMIZATION['max_requests_per_minute']
        self.token_bucket_tokens = self.token_bucket_capacity
        self.token_bucket_last_update = time.time()
    
    def get_trade_cal(self):
        """获取交易日历"""
        try:
            cal = self.pro.trade_cal(exchange='', start_date=START_DATE_API, end_date=END_DATE_API)
            # 【调试】打印接口返回
            logger.info(f"[调试] 交易日历接口返回：\n{cal}")
            if cal is not None and not cal.empty:
                # ✅ 修复：根据测试输出，字段名是 cal_date
                if 'cal_date' in cal.columns and 'is_open' in cal.columns:
                    cal['cal_date'] = pd.to_datetime(cal['cal_date'], format="%Y%m%d")
                    # 筛选出开市的日期，并转为列表
                    cal = cal[cal['is_open'] == 1]['cal_date'].tolist()
                    logger.info(f"✅ 加载交易日历完成，共{len(cal)}个交易日")
                    return cal
            logger.warning("⚠️  交易日历数据格式异常，使用空列表")
            return []
        except Exception as e:
            logger.warning(f"⚠️  获取交易日历失败：{e}，使用空列表")
            return []
    
    def get_prev_trade_date(self, date):
        """获取指定日期的前一个交易日"""
        date = pd.to_datetime(date)
        if not self.trade_cal:
            prev_date = date - timedelta(days=1)
            while prev_date.weekday() >= 5:
                prev_date -= timedelta(days=1)
            return prev_date
        if date not in self.trade_cal:
            valid_dates = [d for d in self.trade_cal if d < date]
            if not valid_dates:
                return date - timedelta(days=1)
            date = max(valid_dates)
        prev_dates = [d for d in self.trade_cal if d < date]
        return max(prev_dates) if prev_dates else date - timedelta(days=1)
    
    def is_trade_day(self, check_date=None):
        """判断指定日期是否为交易日"""
        if check_date is None:
            check_date = datetime.now()
        check_date = pd.to_datetime(check_date).normalize()
        if not self.trade_cal:
            return check_date.weekday() < 5
        return check_date in self.trade_cal
    
    def _rate_limit(self):
        """【优化】阶段 1 任务 2: 令牌桶限流算法，替代原有简单计数限流"""
        current_time = time.time()
        
        # 令牌桶算法：每秒补充 tokens
        time_elapsed = current_time - self.minute_window_start
        tokens_to_add = time_elapsed * (FETCH_OPTIMIZATION['max_requests_per_minute'] / 60.0)
        self.token_bucket_tokens = min(self.token_bucket_capacity, self.token_bucket_tokens + tokens_to_add)
        self.minute_window_start = current_time
        
        # 如果令牌不足，等待补充
        if self.token_bucket_tokens < 1:
            sleep_time = (1 - self.token_bucket_tokens) / (FETCH_OPTIMIZATION['max_requests_per_minute'] / 60.0)
            logger.warning(f"⚠️  令牌桶令牌不足，休眠{sleep_time:.2f}秒")
            time.sleep(sleep_time)
            current_time = time.time()
            time_elapsed = current_time - self.minute_window_start
            tokens_to_add = time_elapsed * (FETCH_OPTIMIZATION['max_requests_per_minute'] / 60.0)
            self.token_bucket_tokens = min(self.token_bucket_capacity, self.token_bucket_tokens + tokens_to_add)
            self.minute_window_start = current_time
        
        # 消耗一个令牌
        self.token_bucket_tokens -= 1
        
        # 秒级限流（兜底）
        self.request_count += 1
        elapsed = current_time - self.window_start
        if elapsed >= 1.0:
            self.request_count = 1
            self.window_start = current_time
        if self.request_count > FETCH_OPTIMIZATION['max_requests_per_second']:
            sleep_time = 1.0 - elapsed
            time.sleep(sleep_time)
            self.request_count = 1
            self.window_start = time.time()
    
    def request_retry(self, func, *args, **kwargs):
        """
        接口请求重试，带指数退避 + 限流 + 错误码处理
        :param func: Tushare 接口函数
        :param args: 位置参数
        :param kwargs: 关键字参数，可传入 timeout
        :return: 接口返回数据 DataFrame
        """
        silent = kwargs.pop('silent', False)
        max_retry = kwargs.pop('max_retry', FILTER_CONFIG['max_fetch_retry'])
        timeout = kwargs.pop('timeout', 60)  # 默认超时 60 秒
        last_exception = None
        
        for i in range(max_retry):
            if not get_app_running():
                return pd.DataFrame()
            try:
                self._rate_limit()
                result = func(*args, **kwargs, timeout=timeout)
                if result is not None and not result.empty:
                    return result
                else:
                    time.sleep(0.2 * (i + 1))
                    continue
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                # 致命错误不重试
                if "token" in error_str or "积分" in error_str or "权限" in error_str:
                    logger.error(f"❌ Tushare 致命错误：{e}，停止重试")
                    self.send_wechat_message(f"【Tushare 错误】{str(e)[:200]}")
                    set_app_running(False)
                    return pd.DataFrame()
                if not silent:
                    logger.warning(f"接口请求失败{i+1}次：{e}，指数退避重试中...")
                sleep_time = 0.2 * (2 ** i) + random.uniform(0, 0.5)
                time.sleep(sleep_time)
        
        if not silent:
            logger.error(f"❌ 接口请求{max_retry}次均失败，错误：{last_exception}")
        return pd.DataFrame()
    
    def price_adjust(self, df, ts_code):
        """前复权处理，异常兜底"""
        if PRICE_ADJUST == "none" or not FETCH_EXTEND_DATA:
            return df
        try:
            df_copy = df.copy()
            df_copy['trade_date'] = df_copy['trade_date'].astype(str)
            start_date = df_copy['trade_date'].min()
            end_date = df_copy['trade_date'].max()
            adj = self.request_retry(self.pro.adj_factor, ts_code=ts_code, start_date=start_date, end_date=end_date, silent=True)
            if adj.empty:
                return df
            adj['trade_date'] = adj['trade_date'].astype(str)
            df['trade_date'] = df['trade_date'].astype(str)
            df = pd.merge(df, adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
            df['adj_factor'] = df['adj_factor'].fillna(1)
            for col in ['open', 'close', 'high', 'low']:
                if col in df.columns:
                    df[col] = df[col] * df['adj_factor']
            if 'adj_factor' in df.columns:
                df = df.drop('adj_factor', axis=1)
            return df
        except Exception as e:
            logger.warning(f"{ts_code}复权处理失败：{e}，返回原始数据")
            return df
    
    def filter_black_swan(self, df, stock_basic):
        """黑天鹅事件过滤，完善退市股/减持/问询过滤"""
        if not CORE_CONFIG['items'].get("无减持公告", [0])[0] and not CORE_CONFIG['items'].get("无监管问询", [0])[0]:
            return df
        try:
            if CORE_CONFIG['items'].get("无减持公告", [0])[0] or CORE_CONFIG['items'].get("无监管问询", [0])[0]:
                holder_trade = self.request_retry(self.pro.stk_holdertrade, start_date=LATEST_START_DATE, end_date=LATEST_DATE, silent=True)
                if not holder_trade.empty:
                    reduction_codes = holder_trade[holder_trade['change_type'].str.contains('减持', na=False)]['ts_code'].unique()
                    inquiry_codes = holder_trade[holder_trade['change_type'].str.contains('问询 | 调查 | 立案', na=False)]['ts_code'].unique()
                    df = df[~df['ts_code'].isin(reduction_codes) & ~df['ts_code'].isin(inquiry_codes)]
            if CORE_CONFIG['items'].get("无减持公告", [0])[0]:
                unlock = self.request_retry(self.pro.share_float, start_date=LATEST_START_DATE, end_date=LATEST_DATE, silent=True)
                if not unlock.empty:
                    unlock_codes = unlock['ts_code'].unique()
                    df = df[~df['ts_code'].isin(unlock_codes)]
            return df
        except Exception as e:
            logger.warning(f"黑天鹅过滤失败：{e}，返回原始数据")
            return df
    
    def send_wechat_message(self, content):
        """企业微信消息推送，完善异常兜底 + 超时控制"""
        if not WECHAT_ROBOT_ENABLED:
            return
        try:
            content_bytes = content.encode('utf-8')
            if len(content_bytes) > 2000:
                content = content[:1900] + "\n...【内容过长，已截断，详情查看日志】"
            if "量化系统" not in content:
                content = "【量化系统】\n" + content
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            headers = {'Content-Type': 'application/json'}
            response = requests.post(WECHAT_ROBOT_URL, json=data, headers=headers, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("✅ 企业微信消息发送成功")
                else:
                    logger.warning(f"⚠️  企业微信消息发送失败：{result}")
            else:
                logger.warning(f"⚠️  企业微信消息发送失败，HTTP 状态码：{response.status_code}")
        except Exception as e:
            logger.error(f"❌ 企业微信消息发送异常：{e}，不影响主程序运行")
    
    def save_failed_stocks(self, failed_stocks):
        """保存失败股票清单"""
        try:
            with open(FAILED_STOCKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(failed_stocks, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 失败股票清单已保存，共{len(failed_stocks)}只")
        except Exception as e:
            logger.warning(f"⚠️  保存失败股票清单失败：{e}")
    
    def load_failed_stocks(self):
        """加载失败股票清单"""
        if os.path.exists(FAILED_STOCKS_FILE):
            try:
                with open(FAILED_STOCKS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️  加载失败股票清单失败：{e}")
        return []
    
    def save_fetch_progress(self, completed_stocks, fetch_type, start_date, end_date):
        """【优化】阶段 1 任务 4: 保存抓取进度，支持断点续传"""
        try:
            progress_data = {
                'fetch_type': fetch_type,
                'start_date': start_date,
                'end_date': end_date,
                'completed_stocks': completed_stocks,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_count': len(completed_stocks)
            }
            with open(FETCH_PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 抓取进度已保存，已完成{len(completed_stocks)}只股票")
        except Exception as e:
            logger.warning(f"⚠️  保存抓取进度失败：{e}")
    
    def load_fetch_progress(self, fetch_type, start_date, end_date):
        """【优化】阶段 1 任务 4: 加载抓取进度，支持断点续传"""
        if os.path.exists(FETCH_PROGRESS_FILE):
            try:
                with open(FETCH_PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    if (progress_data.get('fetch_type') == fetch_type 
                        and progress_data.get('start_date') == start_date 
                        and progress_data.get('end_date') == end_date):
                        completed = progress_data.get('completed_stocks', [])
                        logger.info(f"✅ 加载断点续传进度：已完成{len(completed)}只股票")
                        return completed
            except Exception as e:
                logger.warning(f"⚠️  加载抓取进度失败：{e}")
        return []
    
    # 【优化】阶段 1 任务 3:Parquet 存储支持
    def save_to_parquet(self, df, filepath, compression='snappy', merge_key=None):
        """
        保存 DataFrame 为 Parquet 格式，使用 Snappy 压缩
        :param df: pandas DataFrame
        :param filepath: 保存路径
        :param compression: 压缩算法（snappy/gzip/brotli）
        :param merge_key: 日期列名，增量模式下用于合并去重
        """
        global FETCH_TYPE, START_DATE, END_DATE, START_DATE_API, END_DATE_API, EXTEND_FETCH_CONFIG
        
        # 转换为 parquet 路径
        parquet_path = filepath.replace('.csv', '.parquet')
        
        # 【增量抓取修复】如果是增量模式且文件已存在，合并数据
        if FETCH_TYPE == 'latest' and merge_key and os.path.exists(parquet_path) and merge_key in df.columns:
            try:
                df_existing = self.load_from_parquet(filepath)
                if not df_existing.empty and merge_key in df_existing.columns:
                    df = pd.concat([df_existing, df], ignore_index=True)
                    df = df.drop_duplicates(subset=[merge_key], keep='last')
                    df = df.sort_values(merge_key, ascending=False).reset_index(drop=True)
                    logger.debug(f"✅ 数据已合并: {parquet_path}")
            except Exception as e:
                logger.warning(f"合并数据失败: {e}")
        
        if not PARQUET_AVAILABLE:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            return
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            table = pa.Table.from_pandas(df)
            pq.write_table(table, parquet_path, compression=compression)
            logger.debug(f"✅ Parquet 文件已保存：{parquet_path}")
        except Exception as e:
            logger.warning(f"⚠️  Parquet 保存失败，降级为 CSV: {e}")
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    def load_from_parquet(self, filepath):
        """
        从 Parquet 文件加载数据
        :param filepath: 文件路径（支持.csv 或.parquet）
        :return: pandas DataFrame
        """
        if not PARQUET_AVAILABLE:
            return pd.read_csv(filepath, encoding='utf-8-sig', dtype={'trade_date': str})
        
        parquet_path = filepath.replace('.csv', '.parquet')
        if os.path.exists(parquet_path):
            try:
                df = pq.read_table(parquet_path).to_pandas()
                logger.debug(f"✅ Parquet 文件已加载：{parquet_path}")
                return df
            except Exception as e:
                logger.warning(f"⚠️  Parquet 加载失败，降级为 CSV: {e}")
        
        # 降级为 CSV
        return pd.read_csv(filepath, encoding='utf-8-sig', dtype={'trade_date': str})
    
    # 【优化】阶段 1 任务 5: 数据完整性校验
    def validate_data_integrity(self, df, required_columns, ts_code=""):
        """
        校验数据完整性
        :param df: 待校验的 DataFrame
        :param required_columns: 必需列名列表
        :param ts_code: 股票代码（用于日志）
        :return: (是否完整，缺失列列表)
        """
        if df is None or df.empty:
            logger.warning(f"⚠️  {ts_code} 数据完整性校验失败：数据为空")
            return False, []
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.warning(f"⚠️  {ts_code} 数据完整性校验失败：缺失列{missing_cols}")
            return False, missing_cols
        
        # 检查空值比例
        null_ratio = df.isnull().mean()
        high_null_cols = null_ratio[null_ratio > 0.5].index.tolist()
        if high_null_cols:
            logger.warning(f"⚠️  {ts_code} 数据完整性警告：列{high_null_cols}空值比例超过 50%")
        
        return True, []
    
    # 【优化】阶段 1 任务 6: 数据准确性校验
    def validate_data_accuracy(self, df, ts_code=""):
        """
        校验数据准确性（价格逻辑、成交量等）
        :param df: 待校验的 DataFrame
        :param ts_code: 股票代码（用于日志）
        :return: (是否准确，问题列表)
        """
        issues = []
        
        if df is None or df.empty:
            return False, ["数据为空"]
        
        # 检查价格逻辑：high >= low, high >= close/open, low <= close/open
        if all(col in df.columns for col in ['high', 'low', 'close', 'open']):
            invalid_high_low = (df['high'] < df['low']).sum()
            if invalid_high_low > 0:
                issues.append(f"{invalid_high_low}条记录 high < low")
            
            invalid_high_close = (df['high'] < df['close']).sum()
            if invalid_high_close > 0:
                issues.append(f"{invalid_high_close}条记录 high < close")
            
            invalid_low_close = (df['low'] > df['close']).sum()
            if invalid_low_close > 0:
                issues.append(f"{invalid_low_close}条记录 low > close")
        
        # 检查成交量非负
        if 'vol' in df.columns:
            negative_vol = (df['vol'] < 0).sum()
            if negative_vol > 0:
                issues.append(f"{negative_vol}条记录成交量为负")
        
        # 检查成交额非负
        if 'amount' in df.columns:
            negative_amount = (df['amount'] < 0).sum()
            if negative_amount > 0:
                issues.append(f"{negative_amount}条记录成交额为负")
        
        if issues:
            logger.warning(f"⚠️  {ts_code} 数据准确性校验发现问题：{issues}")
            return False, issues
        
        return True, []
    
    def check_api_permission(self):
        """
        预检查核心接口权限，严格区分网络问题和权限问题
        修复了之前把网络超时误判为积分不足的 bug
        """
        logger.info("开始预检查 Tushare 接口权限...")
        permission_ok = True
        
        # 1. 基础接口检查（必过）
        try:
            self.pro.stock_basic(exchange='', list_status='L', fields='ts_code', limit=1, timeout=60)
            logger.info("✅ 基础数据接口权限正常")
        except Exception as e:
            error_str = str(e).lower()
            # 只有明确提到"积分"、"权限"、"token"的才是权限问题
            if "积分" in error_str or "权限" in error_str or "token" in error_str:
                logger.error(f"❌ 基础数据接口权限异常：{e}")
                permission_ok = False
            else:
                logger.warning(f"⚠️  基础数据接口网络波动（非权限问题）：{e}，继续运行")
        
        # 2. 龙虎榜接口检查（仅在开启时检查，只测 1 天小数据量）
        if EXTEND_FETCH_CONFIG.get('enable_top_list', False) or EXTEND_FETCH_CONFIG.get('enable_top_inst', False):
            try:
                # 只取 1 天、1 条数据，纯测试权限，数据量极小，不容易超时
                self.pro.top_list(trade_date='20240101', limit=1, timeout=60)
                logger.info("✅ 龙虎榜接口权限正常（你的积分足够）")
            except Exception as e:
                error_str = str(e).lower()
                if "积分" in error_str or "权限" in error_str or "token" in error_str:
                    # 只有明确的权限错误才关闭
                    logger.warning(f"⚠️  龙虎榜接口权限不足，已自动关闭：{e}")
                    EXTEND_FETCH_CONFIG['enable_top_list'] = False
                    EXTEND_FETCH_CONFIG['enable_top_inst'] = False
                    self.send_wechat_message(f"【权限提醒】龙虎榜接口积分不足，已自动关闭，错误：{str(e)[:100]}")
                else:
                    # 网络超时/波动，**不关闭**，继续运行
                    logger.warning(f"⚠️  龙虎榜接口网络波动（非权限问题）：{e}，继续尝试抓取")
        
        return permission_ok
    
    # ----------------------
    # 【升级】多资讯源批量抓取方法（兼容原有新浪新闻）
    # ----------------------
    def fetch_multi_news(self, start_date, end_date, ts_code="", source_list=None):
        """
        批量抓取多来源财经新闻
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :param ts_code: 股票代码，空字符串则抓取全市场新闻
        :param source_list: 资讯源列表，不传则使用配置里的默认列表
        :return: 合并后的新闻数据 DataFrame
        """
        default_source_list = EXTEND_FETCH_CONFIG.get("news_source_list", ["sina"])
        source_list = source_list if source_list is not None else default_source_list
        
        all_news_df = pd.DataFrame()
        logger.info(f"开始批量抓取{len(source_list)}个资讯源的新闻：{start_date} 至 {end_date}")
        
        for src in source_list:
            if not get_app_running():
                break
            try:
                logger.info(f"  正在抓取：{src}")
                # 复用原有重试/限流逻辑，超时时间 60 秒
                df = self.request_retry(
                    self.pro.news_sina,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    src=src,
                    timeout=60
                )
                if df is not None and not df.empty:
                    df['news_source'] = src  # 新增来源字段，方便后续筛选
                    all_news_df = pd.concat([all_news_df, df], ignore_index=True)
                    logger.info(f"  ✅ {src}抓取完成，共 {len(df)} 条")
                else:
                    logger.warning(f"  ⚠️  {src}无数据返回")
            except Exception as e:
                logger.error(f"  ❌ {src}抓取失败：{e}，跳过该源，继续抓取其他")
                continue
        
        if not all_news_df.empty:
            # 去重：同标题同时间的新闻只保留一条
            if 'title' in all_news_df.columns and 'datetime' in all_news_df.columns:
                all_news_df = all_news_df.drop_duplicates(subset=['title', 'datetime'], keep='first')
            logger.info(f"✅ 多资讯源抓取完成，总计 {len(all_news_df)} 条有效新闻")
        else:
            logger.warning("⚠️  所有资讯源均无数据返回")
        
        return all_news_df
    
    # 保留原有方法，兼容你之前的代码
    def fetch_news_sina(self, start_date, end_date, ts_code="", src="sina"):
        """原有新浪新闻抓取方法，兼容旧代码"""
        return self.fetch_multi_news(start_date, end_date, ts_code, source_list=[src])
    
    # ----------------------
    # 【新增】每日涨跌停数据抓取方法（打板必加）
    # ----------------------
    def fetch_stk_limit(self, trade_date):
        """
        抓取单日涨跌停数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 涨跌停数据 DataFrame
        """
        try:
            df = self.request_retry(
                self.pro.stk_limit,
                trade_date=trade_date,
                timeout=60
            )
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"⚠️  {trade_date} 涨跌停数据抓取失败：{e}")
            return pd.DataFrame()
    
    # ============================================== 【阶段 0.1：15 个新接口集成】 ==============================================
    # 1. 开盘啦榜单数据接口 - 积分 5000，限流 8000 条/次
    def fetch_kpl_list(self, trade_date):
        """
        抓取开盘啦榜单数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 开盘啦榜单数据 DataFrame
        :说明: 积分 5000，限流 8000 条/次
        :保存路径: data/kpl_list.csv
        """
        try:
            df = self.request_retry(
                self.pro.kpl_list,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'kpl_list.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path) and 'trade_date' in df.columns:
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 开盘啦榜单数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 开盘啦榜单数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 2. 同花顺热榜接口 - 积分 6000，限流 2000 条/次
    def fetch_ths_hot(self, date):
        """
        抓取同花顺热榜数据
        :param date: 交易日期，格式 YYYYMMDD
        :return: 同花顺热榜数据 DataFrame
        :说明: 积分 6000，限流 2000 条/次
        :保存路径: data/ths_hot.csv
        """
        try:
            df = self.request_retry(
                self.pro.ths_hot,
                date=date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str) if 'trade_date' in df.columns else date
                save_path = os.path.join(self.config['output_dir'], 'ths_hot.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 同花顺热榜数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {date} 同花顺热榜数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 3. 游资每日明细接口 - 积分 10000，限流 2000 条/次
    def fetch_hm_detail(self, start_date, end_date):
        """
        抓取游资每日明细数据
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :return: 游资每日明细数据 DataFrame
        :说明: 积分 10000，限流 2000 条/次
        :保存路径: data/hm_detail.csv
        """
        try:
            df = self.request_retry(
                self.pro.hm_detail,
                start_date=start_date,
                end_date=end_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'hm_detail.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date', 'name'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 游资每日明细数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 游资每日明细数据抓取失败 ({start_date}-{end_date})：{e}")
            return pd.DataFrame()
    
    # 4. 游资名录接口 - 积分 5000，限流 1000 条/次
    def fetch_hm_list(self):
        """
        抓取游资名录数据
        :return: 游资名录数据 DataFrame
        :说明: 积分 5000，限流 1000 条/次
        :保存路径: data/hm_list.csv
        """
        try:
            df = self.request_retry(
                self.pro.hm_list,
                timeout=60
            )
            if df is not None and not df.empty:
                save_path = os.path.join(self.config['output_dir'], 'hm_list.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 游资名录数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 游资名录数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 5. 当日集合竞价接口 - 单独权限，限流 8000 条/次
    def fetch_stk_auction(self, trade_date):
        """
        抓取当日集合竞价数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 集合竞价数据 DataFrame
        :说明: 单独权限，限流 8000 条/次
        :保存路径: data/stk_auction.csv
        """
        try:
            df = self.request_retry(
                self.pro.stk_auction,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'stk_auction.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 集合竞价数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 集合竞价数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 6. 同花顺概念成分接口 - 积分 6000，限流 5000 条/次
    def fetch_ths_member(self, concept_code):
        """
        抓取同花顺概念成分数据
        :param concept_code: 概念代码
        :return: 概念成分数据 DataFrame
        :说明: 积分 6000，限流 5000 条/次
        :保存路径: data/ths_member_{concept_code}.csv
        """
        try:
            df = self.request_retry(
                self.pro.ths_member,
                code=concept_code,
                timeout=60
            )
            if df is not None and not df.empty:
                save_path = os.path.join(self.config['output_dir'], f'ths_member_{concept_code}.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 同花顺概念成分数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 同花顺概念成分数据抓取失败 (code={concept_code})：{e}")
            return pd.DataFrame()
    
    # 7. 同花顺板块指数接口 - 积分 6000，限流 3000 条/次
    def fetch_ths_daily(self, index_code, start_date, end_date):
        """
        抓取同花顺板块指数行情数据
        :param index_code: 板块指数代码
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :return: 板块指数行情数据 DataFrame
        :说明: 积分 6000，限流 3000 条/次
        :保存路径: data/ths_daily_{index_code}.csv
        """
        try:
            df = self.request_retry(
                self.pro.ths_daily,
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], f'ths_daily_{index_code}.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 同花顺板块指数行情已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 同花顺板块指数行情抓取失败 (code={index_code})：{e}")
            return pd.DataFrame()
    
    # 8. 同花顺板块指数列表接口 - 积分 6000，限流 5000 条/次
    def fetch_ths_index(self):
        """
        抓取同花顺板块指数列表
        :return: 板块指数列表 DataFrame
        :说明: 积分 6000，限流 5000 条/次
        :保存路径: data/ths_index.csv
        """
        try:
            df = self.request_retry(
                self.pro.ths_index,
                timeout=60
            )
            if df is not None and not df.empty:
                save_path = os.path.join(self.config['output_dir'], 'ths_index.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 同花顺板块指数列表已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 同花顺板块指数列表抓取失败：{e}")
            return pd.DataFrame()
    
    # 9. 最强板块统计接口 - 积分 8000，限流 2000 条/次
    def fetch_limit_cpt_list(self, trade_date):
        """
        抓取最强板块统计数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 最强板块统计数据 DataFrame
        :说明: 积分 8000，限流 2000 条/次
        :保存路径: data/limit_cpt_list.csv
        """
        try:
            df = self.request_retry(
                self.pro.limit_cpt_list,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'limit_cpt_list.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['industry', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 最强板块统计数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 最强板块统计数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 10. 连板天梯接口 - 积分 8000，限流 2000 条/次
    def fetch_limit_step(self, trade_date):
        """
        抓取连板天梯数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 连板天梯数据 DataFrame
        :说明: 积分 8000，限流 2000 条/次
        :保存路径: data/limit_step.csv
        """
        try:
            df = self.request_retry(
                self.pro.limit_step,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'limit_step.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 连板天梯数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 连板天梯数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 11. 涨跌停列表接口 - 积分 5000，限流 2500 条/次
    def fetch_limit_list_d(self, trade_date):
        """
        抓取涨跌停列表数据
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 涨跌停列表数据 DataFrame
        :说明: 积分 5000，限流 2500 条/次
        :保存路径: data/limit_list_d.csv
        """
        try:
            df = self.request_retry(
                self.pro.limit_list_d,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'limit_list_d.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 涨跌停列表数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 涨跌停列表数据抓取失败：{e}")
            return pd.DataFrame()
    
    # 12. 涨跌停榜单接口 - 积分 8000，限流 4000 条/次
    def fetch_limit_list_ths(self, trade_date):
        """
        抓取涨跌停榜单数据（同花顺）
        :param trade_date: 交易日期，格式 YYYYMMDD
        :return: 涨跌停榜单数据 DataFrame
        :说明: 积分 8000，限流 4000 条/次
        :保存路径: data/limit_list_ths.csv
        """
        try:
            df = self.request_retry(
                self.pro.limit_list_ths,
                trade_date=trade_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'limit_list_ths.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 涨跌停榜单数据（同花顺）已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {trade_date} 涨跌停榜单数据（同花顺）抓取失败：{e}")
            return pd.DataFrame()
    
    # 13. 个股资金流向 THS 接口 - 积分 6000，限流 6000 条/次
    def fetch_moneyflow_ths(self, ts_code, start_date, end_date):
        """
        抓取个股资金流向数据（同花顺）
        :param ts_code: 股票代码
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :return: 个股资金流向数据 DataFrame
        :说明: 积分 6000，限流 6000 条/次
        :保存路径: data_all_stocks/{ts_code}/moneyflow_ths.csv
        """
        try:
            df = self.request_retry(
                self.pro.moneyflow_ths,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
                stock_dir = os.path.join(self.config['stocks_dir'], ts_code)
                if not os.path.exists(stock_dir):
                    os.makedirs(stock_dir, exist_ok=True)
                save_path = os.path.join(stock_dir, 'moneyflow_ths.csv')
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ {ts_code} 资金流向数据（THS）已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ {ts_code} 资金流向数据（THS）抓取失败：{e}")
            return pd.DataFrame()
    
    # 14. 概念板块资金流接口 - 积分 6000，限流 5000 条/次
    def fetch_moneyflow_cnt_ths(self, start_date, end_date):
        """
        抓取概念板块资金流数据
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :return: 概念板块资金流数据 DataFrame
        :说明: 积分 6000，限流 5000 条/次
        :保存路径: data/moneyflow_cnt_ths.csv
        """
        try:
            df = self.request_retry(
                self.pro.moneyflow_cnt_ths,
                start_date=start_date,
                end_date=end_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str) if 'trade_date' in df.columns else df['end_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'moneyflow_cnt_ths.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['industry', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 概念板块资金流数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 概念板块资金流数据抓取失败 ({start_date}-{end_date})：{e}")
            return pd.DataFrame()
    
    # 15. 行业资金流向接口 - 积分 6000，限流 5000 条/次
    def fetch_moneyflow_ind_ths(self, start_date, end_date):
        """
        抓取行业资金流向数据
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :return: 行业资金流向数据 DataFrame
        :说明: 积分 6000，限流 5000 条/次
        :保存路径: data/moneyflow_ind_ths.csv
        """
        try:
            df = self.request_retry(
                self.pro.moneyflow_ind_ths,
                start_date=start_date,
                end_date=end_date,
                timeout=60
            )
            if df is not None and not df.empty:
                df['trade_date'] = df['trade_date'].astype(str) if 'trade_date' in df.columns else df['end_date'].astype(str)
                save_path = os.path.join(self.config['output_dir'], 'moneyflow_ind_ths.csv')
                # 增量抓取合并旧数据
                if os.path.exists(save_path):
                    try:
                        existing_df = utils.load_from_parquet(save_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['industry', 'trade_date'], keep='last')
                    except:
                        pass
                self.save_to_parquet(df, save_path)
                logger.info(f"✅ 行业资金流向数据已保存：{save_path}，共{len(df)}条")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ 行业资金流向数据抓取失败 ({start_date}-{end_date})：{e}")
            return pd.DataFrame()
    # ============================================== 【阶段 0.1：15 个新接口集成结束】 ==============================================
    
    # ----------------------
    # 【新增】AkShare 多源新闻抓取方法
    # ----------------------
    def fetch_akshare_news(self, start_date, end_date, ts_code="", source_list=None):
        """
        批量抓取 AkShare 多来源财经新闻
        :param start_date: 开始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :param ts_code: 股票代码，空字符串则抓取全市场新闻
        :param source_list: 资讯源列表，不传则使用配置里的默认列表
        :return: 合并后的新闻数据 DataFrame
        """
        if not AKSHARE_AVAILABLE:
            logger.warning("⚠️  AkShare 未安装，跳过新闻抓取")
            return pd.DataFrame()
        
        default_source_list = EXTEND_FETCH_CONFIG.get("akshare_news_sources", [
            "stock_news_em",
            "news_economic_baidu",
            "stock_news_main_cx",
            "news_cctv"
        ])
        source_list = source_list if source_list is not None else default_source_list
        
        all_news_df = pd.DataFrame()
        logger.info(f"开始批量抓取{len(source_list)}个 AkShare 资讯源的新闻：{start_date} 至 {end_date}")
        
        for src in source_list:
            if not get_app_running():
                break
            try:
                logger.info(f"  正在抓取：{src}")
                df = pd.DataFrame()
                
                if src == "stock_news_em":
                    # 东方财富个股新闻
                    if ts_code:
                        df = ak.stock_news_em(symbol=ts_code.split('.')[0])
                    else:
                        logger.warning(f"  ⚠️  {src}需要指定股票代码，跳过全市场抓取")
                        continue
                
                elif src == "news_economic_baidu":
                    # 百度经济日历
                    df = ak.news_economic_baidu(
                        start_date=start_date.replace('-', ''),
                        end_date=end_date.replace('-', '')
                    )
                
                elif src == "stock_news_main_cx":
                    # 财新数据
                    df = ak.stock_news_main_cx()
                
                elif src == "news_cctv":
                    # 新闻联播
                    df = ak.news_cctv()
                
                if df is not None and not df.empty:
                    df['news_source'] = src
                    df['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    all_news_df = pd.concat([all_news_df, df], ignore_index=True)
                    logger.info(f"  ✅ {src}抓取完成，共 {len(df)} 条")
                else:
                    logger.warning(f"  ⚠️  {src}无数据返回")
            except Exception as e:
                logger.error(f"  ❌ {src}抓取失败：{e}，跳过该源，继续抓取其他")
                continue
        
        if not all_news_df.empty:
            # 去重：同标题同时间的新闻只保留一条
            if 'title' in all_news_df.columns and 'datetime' in all_news_df.columns:
                all_news_df = all_news_df.drop_duplicates(subset=['title', 'datetime'], keep='first')
            elif 'title' in all_news_df.columns:
                all_news_df = all_news_df.drop_duplicates(subset=['title'], keep='first')
            logger.info(f"✅ AkShare 多资讯源抓取完成，总计 {len(all_news_df)} 条有效新闻")
        else:
            logger.warning("⚠️  所有 AkShare 资讯源均无数据返回")
        
        return all_news_df

# APP_RUNNING 全局状态读写（锁保护）
def get_app_running():
    """获取 APP 运行状态"""
    with APP_RUNNING_LOCK:
        return APP_RUNNING

def set_app_running(value):
    """设置 APP 运行状态"""
    global APP_RUNNING
    with APP_RUNNING_LOCK:
        APP_RUNNING = value

# 永久失败股票管理（过期自动清除）
def load_permanent_failed():
    """加载永久失败股票清单，自动清除过期的"""
    if not os.path.exists(PERMANENT_FAILED_FILE):
        return {}
    try:
        with open(PERMANENT_FAILED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            expire_days = FILTER_CONFIG['permanent_failed_expire']
            now = datetime.now()
            valid_data = {}
            for ts_code, info in data.items():
                try:
                    fail_time = datetime.strptime(info['fail_time'], '%Y-%m-%d %H:%M:%S')
                    if (now - fail_time).days < expire_days:
                        valid_data[ts_code] = info
                except:
                    continue
            if len(valid_data) != len(data):
                save_permanent_failed(valid_data)
            return valid_data
    except Exception as e:
        logger.warning(f"加载永久失败股票清单失败：{e}")
        return {}

def save_permanent_failed(permanent_failed):
    """保存永久失败股票清单"""
    try:
        with open(PERMANENT_FAILED_FILE, 'w', encoding='utf-8') as f:
            json.dump(permanent_failed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"⚠️  保存永久失败股票清单失败：{e}")

def add_permanent_failed(ts_code, reason=""):
    """添加股票到永久失败清单"""
    permanent_failed = load_permanent_failed()
    permanent_failed[ts_code] = {
        "fail_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "reason": reason
    }
    save_permanent_failed(permanent_failed)
    logger.warning(f"{ts_code}已标记为永久失败，原因：{reason}")

# 优雅退出信号处理
def signal_handler(signum, frame):
    """处理 Ctrl+C 等退出信号，优雅关闭程序"""
    global FLASK_SERVER
    global GLOBAL_EXECUTOR
    logger.info("🛑 收到退出信号，正在优雅关闭程序...")
    set_app_running(False)
    # 关闭线程池
    with EXECUTOR_LOCK:
        if GLOBAL_EXECUTOR is not None:
            try:
                GLOBAL_EXECUTOR.shutdown(wait=False)
                logger.info("✅ 线程池已关闭")
                GLOBAL_EXECUTOR = None
            except Exception as e:
                logger.warning(f"线程池关闭异常：{e}")
    # 关闭 Flask 服务
    if FLASK_SERVER is not None:
        try:
            FLASK_SERVER.shutdown()
            logger.info("✅ Flask 服务已关闭")
        except Exception as e:
            logger.warning(f"Flask 服务关闭异常：{e}")
    # 强制垃圾回收
    gc.collect()
    logger.info("✅ 程序已安全退出")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 【修复】get_pro_api 移至 Utils 类定义之后
def get_pro_api(config):
    """初始化 Tushare API"""
    ts.set_token(config['token'])
    pro = ts.pro_api()
    pro._DataApi__token = config['token']  # 必须添加，否则 token 验证失败
    pro._DataApi__http_url = config['api_url']
    return pro, Utils(pro, config)

# ============================================== 【Flask 后端 - 完全保留，仅做小修复】 ==============================================
flask_app = Flask(__name__)
CORS(flask_app)
TASK_QUEUE = Queue()
TASK_STATUS = {}

@flask_app.route('/')
def index():
    return f"量化系统后端 API 服务已启动！当前模式：{AUTO_RUN_MODE} | 当前策略：{STRATEGY_TYPE} | 扩展数据抓取：{FETCH_EXTEND_DATA}"

@flask_app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mode': AUTO_RUN_MODE,
        'strategy': STRATEGY_TYPE,
        'running': get_app_running()
    })

@flask_app.route('/api/config', methods=['GET'])
def get_config_api():
    config = load_config()
    return jsonify({
        'token': config['token'][:10] + '...' if len(config['token']) > 10 else config['token'],
        'api_url': config['api_url'],
        'start_date': config['start_date'],
        'end_date': config['end_date'],
        'strategy_type': STRATEGY_TYPE
    })

@flask_app.route('/api/config', methods=['POST'])
def update_config_api():
    data = request.json
    config = load_config()
    config.update(data)
    save_config(config)
    return jsonify({'success': True})

@flask_app.route('/api/fetch', methods=['POST'])
def start_fetch_api():
    data = request.json
    task_id = str(uuid.uuid4())
    TASK_QUEUE.put({
        'id': task_id,
        'config': data.get('config', load_config()),
        'fetch_type': data.get('fetch_type', 'full')
    })
    with TASK_STATUS_LOCK:
        TASK_STATUS[task_id] = {'status': 'queued', 'progress': 0, 'message': '任务已排队', 'logs': []}
    return jsonify({'task_id': task_id, 'status': 'queued'})

@flask_app.route('/api/fetch/<task_id>', methods=['GET'])
def get_fetch_status_api(task_id):
    with TASK_STATUS_LOCK:
        status = TASK_STATUS.get(task_id, {'status': 'not_found'})
    return jsonify(status)

@flask_app.route('/api/stock/<ts_code>/moneyflow', methods=['GET'])
def get_stock_moneyflow(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    moneyflow_file = os.path.join(stock_dir, 'moneyflow.csv')
    if not os.path.exists(moneyflow_file):
        return jsonify({'ts_code': ts_code, 'data': []})
    try:
        df = pd.read_csv(moneyflow_file, encoding='utf-8-sig', dtype={'trade_date': str})
        df = df.sort_values('trade_date', ascending=False)
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        logger.warning(f"{ts_code}资金流向读取失败：{e}")
        return jsonify({'ts_code': ts_code, 'data': []})

@flask_app.route('/api/stock/<ts_code>/concept', methods=['GET'])
def get_stock_concept(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    concept_file = os.path.join(stock_dir, 'concept_detail.csv')
    if not os.path.exists(concept_file):
        return jsonify({'ts_code': ts_code, 'data': []})
    try:
        df = pd.read_csv(concept_file, encoding='utf-8-sig')
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        logger.warning(f"{ts_code}题材概念读取失败：{e}")
        return jsonify({'ts_code': ts_code, 'data': []})

@flask_app.route('/api/stock/<ts_code>/top-list', methods=['GET'])
def get_stock_toplist(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    top_file = os.path.join(stock_dir, 'top_list.csv')
    if not os.path.exists(top_file):
        return jsonify({'ts_code': ts_code, 'data': []})
    try:
        df = pd.read_csv(top_file, encoding='utf-8-sig', dtype={'trade_date': str})
        df = df.sort_values('trade_date', ascending=False)
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        logger.warning(f"{ts_code}龙虎榜数据读取失败：{e}")
        return jsonify({'ts_code': ts_code, 'data': []})

@flask_app.route('/api/top-list', methods=['GET'])
def get_top_list():
    config = load_config()
    top_file = os.path.join(config['output_dir'], 'top_list.csv')
    if os.path.exists(top_file):
        try:
            df = pd.read_csv(top_file, encoding='utf-8-sig', dtype={'trade_date': str})
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date:
                df = df[df['trade_date'] >= start_date]
            if end_date:
                df = df[df['trade_date'] <= end_date]
            return jsonify({'data': df.to_dict('records')})
        except Exception as e:
            return jsonify({'data': [], 'error': str(e)})
    try:
        pro, _ = get_pro_api(config)
        start_date = request.args.get('start_date', config['start_date'])
        end_date = request.args.get('end_date', config['end_date'])
        df = pro.top_list(start_date=start_date, end_date=end_date)

        if df is not None and not df.empty:
            df['trade_date'] = df['trade_date'].astype(str)
            df.to_csv(top_file, index=False, encoding='utf-8-sig')
        return jsonify({'data': df.to_dict('records') if df is not None else []})
    except Exception as e:
        return jsonify({'data': [], 'error': str(e)})

@flask_app.route('/api/top-inst', methods=['GET'])
def get_top_inst():
    config = load_config()
    inst_file = os.path.join(config['output_dir'], 'top_inst.csv')
    if os.path.exists(inst_file):
        try:
            df = pd.read_csv(inst_file, encoding='utf-8-sig', dtype={'trade_date': str})
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date:
                df = df[df['trade_date'] >= start_date]
            if end_date:
                df = df[df['trade_date'] <= end_date]
            return jsonify({'data': df.to_dict('records')})
        except Exception as e:
            return jsonify({'data': [], 'error': str(e)})
    try:
        pro, _ = get_pro_api(config)
        start_date = request.args.get('start_date', config['start_date'])
        end_date = request.args.get('end_date', config['end_date'])
        df = pro.top_inst(start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            df['trade_date'] = df['trade_date'].astype(str)
            df.to_csv(inst_file, index=False, encoding='utf-8-sig')
        return jsonify({'data': df.to_dict('records') if df is not None else []})
    except Exception as e:
        return jsonify({'data': [], 'error': str(e)})

@flask_app.route('/api/stocks', methods=['GET'])
def get_stocks():
    config = load_config()
    stocks_dir = config['stocks_dir']
    if not os.path.exists(stocks_dir):
        return jsonify({'stocks': []})
    stocks = []
    for dirname in os.listdir(stocks_dir):
        stock_dir = os.path.join(stocks_dir, dirname)
        if os.path.isdir(stock_dir):
            daily_file = os.path.join(stock_dir, 'daily.csv')
            stocks.append({
                'ts_code': dirname,
                'has_data': os.path.exists(daily_file)
            })
    return jsonify({'stocks': stocks})

@flask_app.route('/api/stock/<ts_code>/data', methods=['GET'])
def get_stock_data(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    daily_file = os.path.join(stock_dir, 'daily.csv')
    if not os.path.exists(daily_file):
        return jsonify({'error': '数据不存在'}), 404
    try:
        df = pd.read_csv(daily_file, encoding='utf-8-sig', dtype={'trade_date': str})
        df = df.sort_values('trade_date', ascending=False)
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@flask_app.route('/api/stock/<ts_code>/daily-basic', methods=['GET'])
def get_stock_daily_basic(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    daily_basic_file = os.path.join(stock_dir, 'daily_basic.csv')
    if not os.path.exists(daily_basic_file):
        return jsonify({'ts_code': ts_code, 'data': []})
    try:
        df = pd.read_csv(daily_basic_file, encoding='utf-8-sig', dtype={'trade_date': str})
        df = df.sort_values('trade_date', ascending=False)
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        logger.warning(f"{ts_code}每日指标读取失败：{e}")
        return jsonify({'ts_code': ts_code, 'data': []})

@flask_app.route('/api/stock/<ts_code>/fina-indicator', methods=['GET'])
def get_stock_fina_indicator(ts_code):
    config = load_config()
    stock_dir = os.path.join(config['stocks_dir'], ts_code)
    fina_file = os.path.join(stock_dir, 'fina_indicator.csv')
    if not os.path.exists(fina_file):
        return jsonify({'ts_code': ts_code, 'data': []})
    try:
        df = pd.read_csv(fina_file, encoding='utf-8-sig', dtype={'trade_date': str, 'end_date': str})
        return jsonify({'ts_code': ts_code, 'data': df.to_dict('records')})
    except Exception as e:
        logger.warning(f"{ts_code}财务指标读取失败：{e}")
        return jsonify({'ts_code': ts_code, 'data': []})

@flask_app.route('/api/stock-basic', methods=['GET'])
def get_stock_basic_api():
    config = load_config()
    stock_basic_file = os.path.join(config['output_dir'], 'stock_basic.csv')
    if os.path.exists(stock_basic_file):
        try:
            df = pd.read_csv(stock_basic_file, encoding='utf-8-sig')
            return jsonify({'data': df.to_dict('records')})
        except Exception as e:
            pass
    try:
        pro, _ = get_pro_api(config)
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date,market')
        if df is not None and not df.empty:
            df.to_csv(stock_basic_file, index=False, encoding='utf-8-sig')
        return jsonify({'data': df.to_dict('records') if df is not None else []})
    except Exception as e:
        pass
    return jsonify({'data': []})

@flask_app.route('/api/trade-cal', methods=['GET'])
def get_trade_cal_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/daily', methods=['GET'])
def get_daily_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/weekly', methods=['GET'])
def get_weekly_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/monthly', methods=['GET'])
def get_monthly_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/daily-basic', methods=['GET'])
def get_daily_basic_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/stk-limit', methods=['GET'])
def get_stk_limit_api():
    config = load_config()
    limit_file = os.path.join(config['output_dir'], 'stk_limit.csv')
    if os.path.exists(limit_file):
        try:
            df = pd.read_csv(limit_file, encoding='utf-8-sig', dtype={'trade_date': str})
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date:
                df = df[df['trade_date'] >= start_date]
            if end_date:
                df = df[df['trade_date'] <= end_date]
            return jsonify({'data': df.to_dict('records')})
        except Exception as e:
            pass
    try:
        pro, _ = get_pro_api(config)
        start_date = request.args.get('start_date', config['start_date'])
        end_date = request.args.get('end_date', config['end_date'])
        df = pro.stk_limit(start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            df['trade_date'] = df['trade_date'].astype(str)
            df.to_csv(limit_file, index=False, encoding='utf-8-sig')
        return jsonify({'data': df.to_dict('records') if df is not None else []})
    except Exception as e:
        pass
    return jsonify({'data': []})

@flask_app.route('/api/suspend-d', methods=['GET'])
def get_suspend_d_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.suspend_d(start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/fina-indicator', methods=['GET'])
def get_fina_indicator_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.fina_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/income', methods=['GET'])
def get_income_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SZ')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

@flask_app.route('/api/index-daily', methods=['GET'])
def get_index_daily_api():
    config = load_config()
    pro, _ = get_pro_api(config)
    ts_code = request.args.get('ts_code', '000001.SH')
    start_date = request.args.get('start_date', config['start_date'])
    end_date = request.args.get('end_date', config['end_date'])
    df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    return jsonify({'data': df.to_dict('records') if df is not None else []})

# ============================================== 【数据抓取线程 - 全量修复 + 多资讯源集成】 ==============================================
# 【阶段 1.2：动态并发调节】全局动态并发调节器实例
_DYNAMIC_CONCURRENCY_INSTANCE: Optional[DynamicConcurrency] = None

def fetch_worker():
    """数据抓取主线程，全量修复 + 多资讯源集成"""
    global GLOBAL_EXECUTOR
    global _DYNAMIC_CONCURRENCY_INSTANCE
    
    # 【阶段 1.2：动态并发调节】初始化动态并发调节器
    _DYNAMIC_CONCURRENCY_INSTANCE = DynamicConcurrency(
        base_workers=FETCH_OPTIMIZATION['max_workers'],
        min_workers=5,
        max_workers=50,
        cpu_high_threshold=80.0,
        cpu_low_threshold=50.0,
        memory_high_threshold=80.0,
        failure_rate_high_threshold=10.0,
        failure_rate_low_threshold=2.0
    )
    
    with EXECUTOR_LOCK:
        if GLOBAL_EXECUTOR is None:
            # 【优化】阶段 1 任务 1: 并发线程优化（从配置区读取，支持用户调整）
            # 【阶段 1.2：动态并发调节】使用动态调节的线程数
            initial_workers = _DYNAMIC_CONCURRENCY_INSTANCE.get_workers()
            GLOBAL_EXECUTOR = ThreadPoolExecutor(max_workers=initial_workers)
            logger.info(
                f"✅ 数据抓取线程池已初始化，初始并发线程数：{initial_workers} "
                f"(动态调节范围：5-50，根据 CPU/内存/失败率自动调整)"
            )
    
    permanent_failed = load_permanent_failed()
    retry_count = {}
    
    while get_app_running():
        try:
            task = TASK_QUEUE.get(timeout=1)
            task_id = task['id']
            config = task['config']
            fetch_type = task['fetch_type']
            
            with TASK_STATUS_LOCK:
                TASK_STATUS[task_id] = {'status': 'running', 'progress': 0, 'message': '初始化...', 'logs': []}
            
            try:
                pro, utils = get_pro_api(config)
                
                if not utils.check_api_permission():
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'message': '接口权限检查失败', 'logs': []}
                    utils.send_wechat_message("【数据抓取失败】接口权限检查失败，请检查 Token 和积分")
                    TASK_QUEUE.task_done()
                    continue
                
                if fetch_type == 'latest':
                    fetch_days = STOCK_PICK_CONFIG['fetch_days']
                    end_date_api = datetime.now().strftime("%Y%m%d")
                    start_date_api = (datetime.now() - timedelta(days=fetch_days)).strftime("%Y%m%d")
                else:
                    start_date_api = config['start_date']
                    end_date_api = config['end_date']
                
                with TASK_STATUS_LOCK:
                    TASK_STATUS[task_id]['progress'] = 5
                    TASK_STATUS[task_id]['message'] = '获取股票列表...'
                logger.info("开始获取全市场股票列表")
                
                stock_list_df = utils.request_retry(pro.stock_basic, exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date,market')
                if stock_list_df is None or stock_list_df.empty:
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'message': '无法获取股票列表', 'logs': []}
                    TASK_QUEUE.task_done()
                    continue
                
                logger.info(f"原始股票列表共{len(stock_list_df)}只，开始根据{ALLOWED_MARKET}过滤板块...")
                stock_list_df['market_allowed'] = stock_list_df['market'].apply(lambda x: is_market_allowed(x, ALLOWED_MARKET))
                stock_list_df = stock_list_df[stock_list_df['market_allowed']].reset_index(drop=True)
                stock_list_df = stock_list_df[~stock_list_df['ts_code'].isin(permanent_failed.keys())]
                logger.info(f"板块过滤 + 永久失败排除完成，剩余{len(stock_list_df)}只股票，仅抓取这些")
                
                stocks = stock_list_df['ts_code'].tolist()
                total = len(stocks)
                if total == 0:
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'message': '没有符合条件的股票可抓取', 'logs': []}
                    TASK_QUEUE.task_done()
                    continue
                
                stock_basic_path = os.path.join(config['output_dir'], 'stock_basic.csv')
                stock_list_df.to_csv(stock_basic_path, index=False, encoding='utf-8-sig')
                
                success_count = 0
                failed_stocks = []
                
                # 【优化】阶段 1 任务 4: 断点续传
                completed_stocks = utils.load_fetch_progress(fetch_type, start_date_api, end_date_api)
                if completed_stocks:
                    logger.info(f"加载到断点续传进度，已完成{len(completed_stocks)}只，优先抓取未完成的")
                    stocks = [s for s in stocks if s not in completed_stocks] + [s for s in stocks if s in completed_stocks]
                
                previous_failed = utils.load_failed_stocks()
                if previous_failed:
                    logger.info(f"加载到上次失败清单，共{len(previous_failed)}只，优先补抓")
                    previous_failed = [s for s in previous_failed if s in stocks and s not in permanent_failed.keys()]
                    stocks = previous_failed + [s for s in stocks if s not in previous_failed]
                
                # 【紧急优化】批量接口：一次性获取全市场日线数据，减少单只股票循环调用
                with TASK_STATUS_LOCK:
                    TASK_STATUS[task_id]['progress'] = 8
                    TASK_STATUS[task_id]['message'] = '批量获取全市场日线数据...'
                logger.info("【批量优化】开始一次性获取全市场日线数据...")
                try:
                    # 批量获取全市场 daily 数据（不传 ts_code 即获取全市场）
                    df_daily_all = utils.request_retry(pro.daily, start_date=start_date_api, end_date=end_date_api)
                    if not df_daily_all.empty:
                        logger.info(f"✅ 批量获取全市场日线数据成功，共{len(df_daily_all)}条记录")
                        # 按股票代码分组保存
                        for ts_code_group, df_group in df_daily_all.groupby('ts_code'):
                            if ts_code_group in stocks:
                                stock_dir = os.path.join(config['stocks_dir'], ts_code_group)
                                if not os.path.exists(stock_dir):
                                    os.makedirs(stock_dir, exist_ok=True)
                                filepath = os.path.join(stock_dir, "daily.csv")
                                df_group['trade_date'] = df_group['trade_date'].astype(str)
                                utils.save_to_parquet(df_group, filepath, merge_key="trade_date")
                        logger.info(f"✅ 全市场日线数据已分组保存至各股票目录")
                    else:
                        logger.warning("⚠️  批量获取全市场日线数据为空")
                except Exception as e:
                    logger.warning(f"⚠️  批量获取日线数据失败：{e}，降级为单只股票抓取")
                
                # 【批量优化】批量获取全市场 daily_basic 数据
                try:
                    df_daily_basic_all = utils.request_retry(pro.daily_basic, start_date=start_date_api, end_date=end_date_api)
                    if not df_daily_basic_all.empty:
                        logger.info(f"✅ 批量获取全市场日线指标数据成功，共{len(df_daily_basic_all)}条记录")
                        for ts_code_group, df_group in df_daily_basic_all.groupby('ts_code'):
                            if ts_code_group in stocks:
                                stock_dir = os.path.join(config['stocks_dir'], ts_code_group)
                                filepath = os.path.join(stock_dir, "daily_basic.csv")
                                df_group['trade_date'] = df_group['trade_date'].astype(str)
                                utils.save_to_parquet(df_group, filepath, merge_key="trade_date")
                        logger.info(f"✅ 全市场日线指标数据已分组保存至各股票目录")
                except Exception as e:
                    logger.warning(f"⚠️  批量获取日线指标数据失败：{e}，降级为单只股票抓取")
                
                # 【批量优化】批量获取全市场财务指标数据（fina_indicator）
                try:
                    df_fina_all = utils.request_retry(pro.fina_indicator, start_date=start_date_api, end_date=end_date_api)
                    if not df_fina_all.empty:
                        logger.info(f"✅ 批量获取全市场财务指标数据成功，共{len(df_fina_all)}条记录")
                        for ts_code_group, df_group in df_fina_all.groupby('ts_code'):
                            if ts_code_group in stocks:
                                stock_dir = os.path.join(config['stocks_dir'], ts_code_group)
                                if not os.path.exists(stock_dir):
                                    os.makedirs(stock_dir, exist_ok=True)
                                filepath = os.path.join(stock_dir, "fina_indicator.csv")
                                if 'end_date' in df_group.columns:
                                    df_group['end_date'] = df_group['end_date'].astype(str)
                                utils.save_to_parquet(df_group, filepath, merge_key="trade_date")
                        logger.info(f"✅ 全市场财务指标数据已分组保存至各股票目录")
                    else:
                        logger.warning("⚠️  批量获取全市场财务指标数据为空")
                except Exception as e:
                    logger.warning(f"⚠️  批量获取财务指标数据失败：{e}，降级为单只股票抓取")
                
                with TASK_STATUS_LOCK:
                    TASK_STATUS[task_id]['progress'] = 10
                    TASK_STATUS[task_id]['message'] = '开始并发抓取个股其他数据...'
                logger.info(f"开始并发抓取个股其他数据（日线 + 财务指标已批量获取），线程数：{FETCH_OPTIMIZATION['max_workers']}")
                
                def fetch_single_stock(ts_code):
                    """单只股票抓取函数（优化版：跳过已批量获取的日线数据）"""
                    nonlocal success_count, completed_stocks, retry_count
                    if ts_code not in retry_count:
                        retry_count[ts_code] = 0
                    if not get_app_running():
                        return ts_code, False
                    try:
                        stock_dir = os.path.join(config['stocks_dir'], ts_code)
                        if not os.path.exists(stock_dir):
                            os.makedirs(stock_dir, exist_ok=True)
                        
                        # 【批量优化】日线数据已批量获取，跳过重复抓取
                        daily_file = os.path.join(stock_dir, 'daily.csv')
                        daily_basic_file = os.path.join(stock_dir, 'daily_basic.csv')
                        fina_file = os.path.join(stock_dir, 'fina_indicator.csv')
                        daily_exists = os.path.exists(daily_file)
                        daily_basic_exists = os.path.exists(daily_basic_file)
                        fina_exists = os.path.exists(fina_file)
                        
                        if daily_exists and daily_basic_exists and fina_exists:
                            logger.debug(f"{ts_code} 日线 + 财务指标数据已存在，跳过重复抓取")
                        else:
                            # 降级抓取：仅当批量接口失败时才单只抓取
                            if not daily_exists:
                                df_daily = utils.request_retry(pro.daily, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api)
                                if df_daily.empty:
                                    retry_count[ts_code] += 1
                                    # 【阶段 1.2：动态并发调节】记录失败
                                    if _DYNAMIC_CONCURRENCY_INSTANCE:
                                        _DYNAMIC_CONCURRENCY_INSTANCE.record_request(success=False)
                                    return ts_code, False
                                df_daily['trade_date'] = df_daily['trade_date'].astype(str)
                                utils.save_to_parquet(df_daily, daily_file, merge_key="trade_date")
                        
                        # 【优化】阶段 1 任务 5&6: 数据完整性&准确性校验（使用已加载的数据）
                        if os.path.exists(daily_file):
                            df_daily_check = utils.load_from_parquet(daily_file)
                            required_cols = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
                            integrity_ok, missing_cols = utils.validate_data_integrity(df_daily_check, required_cols, ts_code)
                            accuracy_ok, accuracy_issues = utils.validate_data_accuracy(df_daily_check, ts_code)
                            
                            if not integrity_ok or not accuracy_ok:
                                logger.warning(f"{ts_code} 数据校验未通过，跳过保存")
                                retry_count[ts_code] += 1
                                # 【阶段 1.2：动态并发调节】记录失败
                                if _DYNAMIC_CONCURRENCY_INSTANCE:
                                    _DYNAMIC_CONCURRENCY_INSTANCE.record_request(success=False)
                                return ts_code, False
                        
                        # 【批量优化】财务指标数据已批量获取，跳过重复抓取
                        if not fina_exists:
                            df_fina = utils.request_retry(pro.fina_indicator, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api)
                            if not df_fina.empty:
                                if 'end_date' in df_fina.columns:
                                    df_fina['end_date'] = df_fina['end_date'].astype(str)
                                filepath = os.path.join(stock_dir, "fina_indicator.csv")
                                utils.save_to_parquet(df_fina, filepath, merge_key="end_date")
                        else:
                            logger.debug(f"{ts_code} 财务指标数据已存在，跳过重复抓取")
                        
                        if FETCH_EXTEND_DATA:
                            df_moneyflow = utils.request_retry(pro.moneyflow, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_moneyflow.empty:
                                df_moneyflow['trade_date'] = df_moneyflow['trade_date'].astype(str)
                                utils.save_to_parquet(df_moneyflow, os.path.join(stock_dir, "moneyflow.csv"), merge_key="trade_date")
                            df_concept = utils.request_retry(pro.concept_detail, ts_code=ts_code, silent=True)
                            if not df_concept.empty:
                                utils.save_to_parquet(df_concept, os.path.join(stock_dir, "concept_detail.csv"))
                        
                        if EXTEND_FETCH_CONFIG.get('enable_top_list', False):
                            df_top = utils.request_retry(pro.top_list, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_top.empty:
                                df_top['trade_date'] = df_top['trade_date'].astype(str)
                                utils.save_to_parquet(df_top, os.path.join(stock_dir, "top_list.csv"), merge_key="trade_date")
                        
                        if EXTEND_FETCH_CONFIG.get('enable_finance_sheet', False):
                            df_balance = utils.request_retry(pro.balancesheet, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_balance.empty:
                                if 'end_date' in df_balance.columns:
                                    df_balance['end_date'] = df_balance['end_date'].astype(str)
                                utils.save_to_parquet(df_balance, os.path.join(stock_dir, "balancesheet.csv"), merge_key="end_date")
                            df_cash = utils.request_retry(pro.cashflow, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_cash.empty:
                                if 'end_date' in df_cash.columns:
                                    df_cash['end_date'] = df_cash['end_date'].astype(str)
                                utils.save_to_parquet(df_cash, os.path.join(stock_dir, "cashflow.csv"), merge_key="end_date")
                            df_income = utils.request_retry(pro.income, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_income.empty:
                                if 'end_date' in df_income.columns:
                                    df_income['end_date'] = df_income['end_date'].astype(str)
                                utils.save_to_parquet(df_income, os.path.join(stock_dir, "income.csv"), merge_key="end_date")
                        
                        if EXTEND_FETCH_CONFIG.get('enable_hk_hold', False):
                            df_hk = utils.request_retry(pro.hk_hold, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_hk.empty:
                                df_hk['trade_date'] = df_hk['trade_date'].astype(str)
                                utils.save_to_parquet(df_hk, os.path.join(stock_dir, "hk_hold.csv"), merge_key="trade_date")
                        
                        if EXTEND_FETCH_CONFIG.get('enable_cyq', False):
                            df_cyq_chips = utils.request_retry(pro.cyq_chips, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_cyq_chips.empty:
                                df_cyq_chips['trade_date'] = df_cyq_chips['trade_date'].astype(str)
                                utils.save_to_parquet(df_cyq_chips, os.path.join(stock_dir, "cyq_chips.csv"), merge_key="trade_date")
                            df_cyq_perf = utils.request_retry(pro.cyq_perf, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_cyq_perf.empty:
                                df_cyq_perf['trade_date'] = df_cyq_perf['trade_date'].astype(str)
                                utils.save_to_parquet(df_cyq_perf, os.path.join(stock_dir, "cyq_perf.csv"), merge_key="trade_date")
                        
                        if EXTEND_FETCH_CONFIG.get('enable_block_trade', False):
                            df_block = utils.request_retry(pro.block_trade, ts_code=ts_code, start_date=start_date_api, end_date=end_date_api, silent=True)
                            if not df_block.empty:
                                df_block['trade_date'] = df_block['trade_date'].astype(str)
                                utils.save_to_parquet(df_block, os.path.join(stock_dir, "block_trade.csv"), merge_key="trade_date")
                        
                        with GLOBAL_LOCK:
                            if ts_code not in completed_stocks:
                                completed_stocks.append(ts_code)
                                if len(completed_stocks) % 50 == 0:  # 【优化】从 100 改为 50，减少中断后重复抓取
                                    utils.save_fetch_progress(completed_stocks, fetch_type, start_date_api, end_date_api)
                        
                        retry_count[ts_code] = 0
                        # 【阶段 1.2：动态并发调节】记录成功
                        if _DYNAMIC_CONCURRENCY_INSTANCE:
                            _DYNAMIC_CONCURRENCY_INSTANCE.record_request(success=True)
                        return ts_code, True
                    except Exception as e:
                        retry_count[ts_code] += 1
                        if retry_count[ts_code] >= FILTER_CONFIG['max_fetch_retry']:
                            add_permanent_failed(ts_code, str(e))
                            with GLOBAL_LOCK:
                                if ts_code in permanent_failed:
                                    del permanent_failed[ts_code]
                        logger.warning(f"{ts_code}抓取失败：{e}")
                        # 【阶段 1.2：动态并发调节】记录失败
                        if _DYNAMIC_CONCURRENCY_INSTANCE:
                            _DYNAMIC_CONCURRENCY_INSTANCE.record_request(success=False)
                        return ts_code, False
                
                future_to_stock = {GLOBAL_EXECUTOR.submit(fetch_single_stock, ts_code): ts_code for ts_code in stocks}
                for idx, future in enumerate(as_completed(future_to_stock)):
                    if not get_app_running():
                        break
                    ts_code, success = future.result()
                    if success:
                        success_count += 1
                        if ts_code in failed_stocks:
                            failed_stocks.remove(ts_code)
                    else:
                        if ts_code not in failed_stocks:
                            failed_stocks.append(ts_code)
                    
                    progress = int(10 + (idx + 1) / len(stocks) * 70)
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = progress
                        TASK_STATUS[task_id]['message'] = f"个股抓取进度：{idx+1}/{len(stocks)}，成功{success_count}只"
                    
                    # 【阶段 1.2：动态并发调节】每 50 只股票调整一次并发数
                    if (idx + 1) % 50 == 0 and _DYNAMIC_CONCURRENCY_INSTANCE:
                        current_workers = _DYNAMIC_CONCURRENCY_INSTANCE.adjust_workers(verbose=True)
                        # 动态调整线程池（需要重新创建）
                        with EXECUTOR_LOCK:
                            if GLOBAL_EXECUTOR is not None:
                                # 不关闭旧线程池，等待当前任务完成
                                logger.info(f"🔄 动态并发调节：当前线程数调整为 {current_workers}（新任务将使用新线程数）")
                    
                    if idx % 100 == 0:
                        # 【阶段 1.2：动态并发调节】输出详细统计
                        if _DYNAMIC_CONCURRENCY_INSTANCE:
                            stats = _DYNAMIC_CONCURRENCY_INSTANCE.get_statistics()
                            logger.info(
                                f"个股抓取进度：{idx+1}/{len(stocks)}，成功{success_count}只，失败{len(failed_stocks)}只 | "
                                f"并发线程数：{stats['current_workers']} | "
                                f"CPU: {stats['cpu_percent']:.1f}% | 内存：{stats['memory_percent']:.1f}% | "
                                f"失败率：{stats['failure_rate']:.1f}%"
                            )
                        else:
                            logger.info(f"个股抓取进度：{idx+1}/{len(stocks)}，成功{success_count}只，失败{len(failed_stocks)}只")
                
                utils.save_fetch_progress(completed_stocks, fetch_type, start_date_api, end_date_api)
                utils.save_failed_stocks(failed_stocks)
                
                if EXTEND_FETCH_CONFIG.get('enable_stk_limit', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 82
                        TASK_STATUS[task_id]['message'] = '抓取全市场涨跌停数据...'
                    logger.info("开始抓取全市场涨跌停数据")
                    try:
                        limit_df = utils.request_retry(pro.stk_limit, start_date=start_date_api, end_date=end_date_api)
                        if not limit_df.empty:
                            limit_df['trade_date'] = limit_df['trade_date'].astype(str)
                            limit_path = os.path.join(config['output_dir'], 'stk_limit.csv')
                            if os.path.exists(limit_path) and fetch_type == 'latest':
                                existing_limit = utils.load_from_parquet(limit_path)
                                limit_df = pd.concat([existing_limit, limit_df], ignore_index=True)
                                limit_df = limit_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                            utils.save_to_parquet(limit_df, limit_path)
                    except Exception as e:
                        logger.warning(f"涨跌停数据抓取失败：{e}")
                
                if EXTEND_FETCH_CONFIG.get('enable_top_list', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 85
                        TASK_STATUS[task_id]['message'] = '抓取龙虎榜每日明细（按单日循环）...'
                    logger.info("开始抓取龙虎榜每日明细（按单日循环，避免超时）...")
                    
                    all_top_list = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        
                        try:
                            df_day = utils.request_retry(pro.top_list, trade_date=current_date_str, timeout=60)
                            if df_day is not None and not df_day.empty:
                                all_top_list.append(df_day)
                                logger.info(f"  已抓取龙虎榜：{current_date_str}，{len(df_day)}条")
                        except Exception as e:
                            logger.warning(f"  {current_date_str} 龙虎榜抓取失败（跳过）：{e}")
                            continue
                    
                    if all_top_list:
                        top_list_df = pd.concat(all_top_list, ignore_index=True)
                        top_list_df['trade_date'] = top_list_df['trade_date'].astype(str)
                        top_list_path = os.path.join(config['output_dir'], 'top_list.csv')
                        if os.path.exists(top_list_path) and fetch_type == 'latest':
                            existing_top = utils.load_from_parquet(top_list_path)
                            top_list_df = pd.concat([existing_top, top_list_df], ignore_index=True)
                            top_list_df = top_list_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                        utils.save_to_parquet(top_list_df, top_list_path)
                        logger.info(f"✅ 龙虎榜每日明细抓取完成，共{len(top_list_df)}条")
                
                if EXTEND_FETCH_CONFIG.get('enable_top_inst', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 88
                        TASK_STATUS[task_id]['message'] = '抓取龙虎榜机构席位明细...'
                    logger.info("开始抓取龙虎榜机构席位明细")
                    try:
                        top_inst_df = utils.request_retry(pro.top_inst, start_date=start_date_api, end_date=end_date_api)
                        if not top_inst_df.empty:
                            top_inst_df['trade_date'] = top_inst_df['trade_date'].astype(str)
                            top_inst_path = os.path.join(config['output_dir'], 'top_inst.csv')
                            if os.path.exists(top_inst_path) and fetch_type == 'latest':
                                existing_inst = utils.load_from_parquet(top_inst_path)
                                top_inst_df = pd.concat([existing_inst, top_inst_df], ignore_index=True)
                                top_inst_df = top_inst_df.drop_duplicates(subset=['ts_code', 'trade_date', 'exalter'], keep='last')
                            utils.save_to_parquet(top_inst_df, top_inst_path)
                    except Exception as e:
                        logger.warning(f"龙虎榜机构席位明细抓取失败：{e}")
                
                if EXTEND_FETCH_CONFIG.get('enable_kpl_concept', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 91
                        TASK_STATUS[task_id]['message'] = '抓取概念板块数据...'
                    logger.info("开始抓取概念板块数据")
                    try:
                        concept_list_df = utils.request_retry(pro.concept_list, fields='id,name,src', silent=True)
                        if not concept_list_df.empty:
                            utils.save_to_parquet(concept_list_df, os.path.join(config['output_dir'], 'concept_list.csv'))
                        concept_detail_df = utils.request_retry(pro.concept_detail, start_date=start_date_api, end_date=end_date_api)
                        if not concept_detail_df.empty:
                            utils.save_to_parquet(concept_detail_df, os.path.join(config['output_dir'], 'concept_detail.csv'))
                    except Exception as e:
                        logger.warning(f"概念板块数据抓取失败：{e}")
                
                if EXTEND_FETCH_CONFIG.get('enable_index_weight', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 94
                        TASK_STATUS[task_id]['message'] = '抓取指数成分股权重数据...'
                    logger.info("开始抓取指数成分股权重数据")
                    try:
                        index_weight_df = utils.request_retry(pro.index_weight, start_date=start_date_api, end_date=end_date_api)
                        if not index_weight_df.empty:
                            index_weight_df['trade_date'] = index_weight_df['trade_date'].astype(str)
                            utils.save_to_parquet(index_weight_df, os.path.join(config['output_dir'], 'index_weight.csv'))
                    except Exception as e:
                        logger.warning(f"指数成分股权重数据抓取失败：{e}")
                
                # ----------------------
                # 【升级】多资讯源抓取集成
                # ----------------------
                if EXTEND_FETCH_CONFIG.get('enable_multi_news', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 95
                        TASK_STATUS[task_id]['message'] = f'批量抓取{len(EXTEND_FETCH_CONFIG["news_source_list"])}个资讯源新闻...'
                    logger.info("开始批量抓取多资讯源新闻...")
                    
                    # 调用升级后的多源抓取方法
                    df_news = utils.fetch_multi_news(
                        start_date=start_date_api,
                        end_date=end_date_api
                    )
                    
                    # 保存到 Parquet
                    if not df_news.empty:
                        news_path = os.path.join(config['output_dir'], 'multi_news_all.csv')
                        # 增量抓取合并旧数据
                        if os.path.exists(news_path) and fetch_type == 'latest':
                            existing_news = utils.load_from_parquet(news_path)
                            df_news = pd.concat([existing_news, df_news], ignore_index=True)
                            if 'title' in df_news.columns and 'datetime' in df_news.columns:
                                df_news = df_news.drop_duplicates(subset=['title', 'datetime'], keep='last')
                        utils.save_to_parquet(df_news, news_path)
                        logger.info(f"✅ 多资讯源新闻已保存到：{news_path}")
                
                # ----------------------
                # 【新增】AkShare 新闻源抓取集成
                # ----------------------
                if EXTEND_FETCH_CONFIG.get('enable_akshare_news', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 96
                        TASK_STATUS[task_id]['message'] = f'批量抓取{len(EXTEND_FETCH_CONFIG["akshare_news_sources"])}个 AkShare 资讯源新闻...'
                    logger.info("开始批量抓取 AkShare 多源新闻...")
                    
                    # 调用 AkShare 多源抓取方法
                    df_akshare_news = utils.fetch_akshare_news(
                        start_date=start_date_api,
                        end_date=end_date_api,
                        ts_code=ts_code if 'ts_code' in locals() else ""
                    )
                    
                    # 保存到 Parquet
                    if not df_akshare_news.empty:
                        akshare_news_path = os.path.join(config['output_dir'], 'akshare_news_all.csv')
                        # 增量抓取合并旧数据
                        if os.path.exists(akshare_news_path) and fetch_type == 'latest':
                            existing_akshare_news = utils.load_from_parquet(akshare_news_path)
                            df_akshare_news = pd.concat([existing_akshare_news, df_akshare_news], ignore_index=True)
                            if 'title' in df_akshare_news.columns:
                                dedup_cols = ['title']
                                if 'datetime' in df_akshare_news.columns:
                                    dedup_cols.append('datetime')
                                df_akshare_news = df_akshare_news.drop_duplicates(subset=dedup_cols, keep='last')
                        utils.save_to_parquet(df_akshare_news, akshare_news_path)
                        logger.info(f"✅ AkShare 新闻已保存到：{akshare_news_path}")
                
                # ----------------------
                # 【新增】集成每日涨跌停数据抓取（按单日循环）
                # ----------------------
                if EXTEND_FETCH_CONFIG.get('enable_stk_limit', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 97
                        TASK_STATUS[task_id]['message'] = '抓取每日涨跌停数据（按单日循环）...'
                    logger.info("开始抓取每日涨跌停数据...")
                    
                    all_stk_limit = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        
                        df_day = utils.fetch_stk_limit(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_stk_limit.append(df_day)
                            logger.info(f"  已抓取涨跌停：{current_date_str}")
                    
                    if all_stk_limit:
                        df_stk_limit = pd.concat(all_stk_limit, ignore_index=True)
                        stk_limit_path = os.path.join(config['output_dir'], 'stk_limit.csv')
                        utils.save_to_parquet(df_stk_limit, stk_limit_path)
                        logger.info(f"✅ 涨跌停数据已保存到：{stk_limit_path}")
                
                # ============================================== 【阶段 0.1：15 个新接口调用集成】 ==============================================
                # 1. 开盘啦榜单数据接口
                if EXTEND_FETCH_CONFIG.get('enable_kpl_list', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取开盘啦榜单数据...'
                    logger.info("开始抓取开盘啦榜单数据...")
                    all_kpl_list = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_kpl_list(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_kpl_list.append(df_day)
                    if all_kpl_list:
                        df_kpl = pd.concat(all_kpl_list, ignore_index=True)
                        kpl_path = os.path.join(config['output_dir'], 'kpl_list.csv')
                        utils.save_to_parquet(df_kpl, kpl_path)
                        logger.info(f"✅ 开盘啦榜单数据已保存到：{kpl_path}")
                else:
                    logger.info("⏭️  跳过开盘啦榜单数据抓取（接口已关闭）")
                
                # 2. 同花顺热榜接口
                if EXTEND_FETCH_CONFIG.get('enable_ths_hot', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取同花顺热榜...'
                    logger.info("开始抓取同花顺热榜...")
                    all_ths_hot = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_ths_hot(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_ths_hot.append(df_day)
                    if all_ths_hot:
                        df_ths_hot = pd.concat(all_ths_hot, ignore_index=True)
                        ths_hot_path = os.path.join(config['output_dir'], 'ths_hot.csv')
                        utils.save_to_parquet(df_ths_hot, ths_hot_path)
                        logger.info(f"✅ 同花顺热榜已保存到：{ths_hot_path}")
                
                # 3. 游资每日明细接口
                if EXTEND_FETCH_CONFIG.get('enable_hm_detail', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取游资每日明细...'
                    logger.info("开始抓取游资每日明细...")
                    utils.fetch_hm_detail(start_date_api, end_date_api)
                
                # 4. 游资名录接口
                if EXTEND_FETCH_CONFIG.get('enable_hm_list', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取游资名录...'
                    logger.info("开始抓取游资名录...")
                    utils.fetch_hm_list()
                
                # 5. 当日集合竞价接口
                if EXTEND_FETCH_CONFIG.get('enable_stk_auction', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取集合竞价数据...'
                    logger.info("开始抓取集合竞价数据...")
                    all_auction = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_stk_auction(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_auction.append(df_day)
                    if all_auction:
                        df_auction = pd.concat(all_auction, ignore_index=True)
                        auction_path = os.path.join(config['output_dir'], 'stk_auction.csv')
                        utils.save_to_parquet(df_auction, auction_path)
                        logger.info(f"✅ 集合竞价数据已保存到：{auction_path}")
                
                # 6. 同花顺概念成分接口（需要先获取概念列表）
                if EXTEND_FETCH_CONFIG.get('enable_ths_member', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取同花顺概念成分...'
                    logger.info("开始抓取同花顺概念成分...")
                    try:
                        concept_list_df = utils.fetch_ths_index()
                        if concept_list_df is not None and not concept_list_df.empty and 'ts_code' in concept_list_df.columns:
                            for idx, row in concept_list_df.iterrows():
                                if not get_app_running():
                                    break
                                concept_code = row['ts_code']
                                utils.fetch_ths_member(concept_code)
                    except Exception as e:
                        logger.error(f"❌ 同花顺概念成分抓取失败：{e}")
                
                # 7. 同花顺板块指数接口（需要先获取概念列表）
                if EXTEND_FETCH_CONFIG.get('enable_ths_daily', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取同花顺板块指数...'
                    logger.info("开始抓取同花顺板块指数...")
                    try:
                        concept_list_df = utils.fetch_ths_index()
                        if concept_list_df is not None and not concept_list_df.empty and 'ts_code' in concept_list_df.columns:
                            for idx, row in concept_list_df.iterrows():
                                if not get_app_running():
                                    break
                                index_code = row['ts_code']
                                utils.fetch_ths_daily(index_code, start_date_api, end_date_api)
                    except Exception as e:
                        logger.error(f"❌ 同花顺板块指数抓取失败：{e}")
                else:
                    logger.info("⏭️  跳过同花顺板块指数抓取（接口已关闭）")
                
                # 8. 同花顺板块指数列表接口
                if EXTEND_FETCH_CONFIG.get('enable_ths_index', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取同花顺板块指数列表...'
                    logger.info("开始抓取同花顺板块指数列表...")
                    utils.fetch_ths_index()
                
                # 9. 最强板块统计接口
                if EXTEND_FETCH_CONFIG.get('enable_limit_cpt_list', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取最强板块统计...'
                    logger.info("开始抓取最强板块统计...")
                    all_cpt = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_limit_cpt_list(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_cpt.append(df_day)
                    if all_cpt:
                        df_cpt = pd.concat(all_cpt, ignore_index=True)
                        cpt_path = os.path.join(config['output_dir'], 'limit_cpt_list.csv')
                        utils.save_to_parquet(df_cpt, cpt_path)
                        logger.info(f"✅ 最强板块统计已保存到：{cpt_path}")
                else:
                    logger.info("⏭️  跳过最强板块统计抓取（接口已关闭）")
                
                # 10. 连板天梯接口
                if EXTEND_FETCH_CONFIG.get('enable_limit_step', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取连板天梯...'
                    logger.info("开始抓取连板天梯...")
                    all_step = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_limit_step(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_step.append(df_day)
                    if all_step:
                        df_step = pd.concat(all_step, ignore_index=True)
                        step_path = os.path.join(config['output_dir'], 'limit_step.csv')
                        utils.save_to_parquet(df_step, step_path)
                        logger.info(f"✅ 连板天梯已保存到：{step_path}")
                else:
                    logger.info("⏭️  跳过连板天梯抓取（接口已关闭）")
                
                # 11. 涨跌停列表接口
                if EXTEND_FETCH_CONFIG.get('enable_limit_list_d', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取涨跌停列表...'
                    logger.info("开始抓取涨跌停列表...")
                    all_limit_d = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_limit_list_d(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_limit_d.append(df_day)
                    if all_limit_d:
                        df_limit_d = pd.concat(all_limit_d, ignore_index=True)
                        limit_d_path = os.path.join(config['output_dir'], 'limit_list_d.csv')
                        utils.save_to_parquet(df_limit_d, limit_d_path)
                        logger.info(f"✅ 涨跌停列表已保存到：{limit_d_path}")
                else:
                    logger.info("⏭️  跳过涨跌停列表抓取（接口已关闭）")
                
                # 12. 涨跌停榜单接口（同花顺）
                if EXTEND_FETCH_CONFIG.get('enable_limit_list_ths', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 98
                        TASK_STATUS[task_id]['message'] = '抓取涨跌停榜单（同花顺）...'
                    logger.info("开始抓取涨跌停榜单（同花顺）...")
                    all_limit_ths = []
                    start_dt = datetime.strptime(start_date_api, "%Y%m%d")
                    end_dt = datetime.strptime(end_date_api, "%Y%m%d")
                    delta = end_dt - start_dt
                    for i in range(delta.days + 1):
                        if not get_app_running():
                            break
                        current_dt = start_dt + timedelta(days=i)
                        current_date_str = current_dt.strftime("%Y%m%d")
                        df_day = utils.fetch_limit_list_ths(current_date_str)
                        if df_day is not None and not df_day.empty:
                            all_limit_ths.append(df_day)
                    if all_limit_ths:
                        df_limit_ths = pd.concat(all_limit_ths, ignore_index=True)
                        limit_ths_path = os.path.join(config['output_dir'], 'limit_list_ths.csv')
                        utils.save_to_parquet(df_limit_ths, limit_ths_path)
                        logger.info(f"✅ 涨跌停榜单（同花顺）已保存到：{limit_ths_path}")
                else:
                    logger.info("⏭️  跳过涨跌停榜单（同花顺）抓取（接口已关闭）")
                
                # 13. 个股资金流向 THS 接口（按股票循环）
                if EXTEND_FETCH_CONFIG.get('enable_moneyflow_ths', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 99
                        TASK_STATUS[task_id]['message'] = '抓取个股资金流向（THS）...'
                    logger.info("开始抓取个股资金流向（THS）...")
                    for ts_code in stocks:
                        if not get_app_running():
                            break
                        try:
                            utils.fetch_moneyflow_ths(ts_code, start_date_api, end_date_api)
                        except Exception as e:
                            logger.error(f"❌ {ts_code} 资金流向（THS）抓取失败：{e}")
                
                # 14. 概念板块资金流接口
                if EXTEND_FETCH_CONFIG.get('enable_moneyflow_cnt_ths', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 99
                        TASK_STATUS[task_id]['message'] = '抓取概念板块资金流...'
                    logger.info("开始抓取概念板块资金流...")
                    utils.fetch_moneyflow_cnt_ths(start_date_api, end_date_api)
                
                # 15. 行业资金流向接口
                if EXTEND_FETCH_CONFIG.get('enable_moneyflow_ind_ths', False):
                    with TASK_STATUS_LOCK:
                        TASK_STATUS[task_id]['progress'] = 99
                        TASK_STATUS[task_id]['message'] = '抓取行业资金流向...'
                    logger.info("开始抓取行业资金流向...")
                    utils.fetch_moneyflow_ind_ths(start_date_api, end_date_api)
                # ============================================== 【阶段 0.1：15 个新接口调用集成结束】 ==============================================
                
                with TASK_STATUS_LOCK:
                    TASK_STATUS[task_id]['progress'] = 100
                    TASK_STATUS[task_id]['status'] = 'completed'
                    TASK_STATUS[task_id]['message'] = f"全量数据抓取完成！成功：{success_count}/{len(stocks)} 只股票，失败{len(failed_stocks)}只已保存清单"
                logger.info(f"✅ 全量数据抓取完成！成功{success_count}/{len(stocks)}只股票，失败{len(failed_stocks)}只已保存清单")
                utils.send_wechat_message(f"【数据抓取完成】成功{success_count}/{len(stocks)}只，失败{len(failed_stocks)}只")
            
            except Exception as e:
                with TASK_STATUS_LOCK:
                    TASK_STATUS[task_id]['status'] = 'failed'
                    TASK_STATUS[task_id]['message'] = str(e)
                logger.error(f"❌ 抓取任务失败：{e}")
            TASK_QUEUE.task_done()
        except Empty:
            continue
        except Exception as e:
            logger.error(f"❌ 抓取线程异常：{e}")

# ============================================== 【策略核心类 - 完全保留，仅做小修复】 ==============================================
class StrategyCore:
    def __init__(self, strategy_type):
        self.strategy_type = strategy_type
        self.filter_config = FILTER_CONFIG
        self.core_config = CORE_CONFIG
        self.strategy_config = STRATEGY_CONFIG.get(strategy_type, {})
        self.pass_score = self.core_config['strategy_pass_score'].get(strategy_type, self.core_config['pass_score'])
        logger.info(f"✅ 初始化{self.strategy_type}，及格分：{self.pass_score}")
    
    def filter(self, df):
        """前置筛选"""
        df_filter = deepcopy(df)
        if df_filter.empty:
            logger.warning("⚠️  策略筛选：输入数据为空，直接返回")
            return df_filter
        try:
            if 'name' in df_filter.columns and self.filter_config['exclude_st']:
                df_filter = df_filter[~df_filter["name"].str.contains("ST|\\*ST|退", na=False, regex=True)]
            if 'amount' in df_filter.columns:
                df_filter = df_filter[df_filter["amount"] >= self.filter_config['min_amount']]
            if 'turnover_ratio' in df_filter.columns:
                df_filter = df_filter[df_filter["turnover_ratio"] >= self.filter_config['min_turnover']]
            
            if self.strategy_type == "打板策略":
                bc = self.strategy_config
                if 'order_amount' in df_filter.columns and 'float_market_cap' in df_filter.columns:
                    df_filter['order_ratio'] = df_filter['order_amount'] / df_filter['float_market_cap']
                    df_filter = df_filter[df_filter['order_ratio'] >= bc.get('min_order_ratio', 0.03)]
                if 'break_limit_times' in df_filter.columns:
                    df_filter = df_filter[df_filter['break_limit_times'] <= bc.get('max_break_times', 1)]
                if 'up_down_times' in df_filter.columns:
                    link_range = bc.get('link_board_range', [2, 4])
                    df_filter = df_filter[(df_filter['up_down_times'] >= link_range[0]) & (df_filter['up_down_times'] <= link_range[1])]
                if bc.get('exclude_late_board', True) and 'first_limit_time' in df_filter.columns:
                    df_filter = df_filter[df_filter['first_limit_time'] <= '14:40']
            
            elif self.strategy_type == "缩量潜伏策略":
                lc = self.strategy_config
                # 1. 基础过滤：排除 ST、退市、无成交量标的
                if 'name' in df_filter.columns and FILTER_CONFIG['exclude_st']:
                    df_filter = df_filter[~df_filter["name"].str.contains("ST|\\*ST|退", na=False, regex=True)]
                if 'vol' in df_filter.columns:
                    df_filter = df_filter[df_filter["vol"] > 0]
                if 'amount' in df_filter.columns:
                    df_filter = df_filter[df_filter["amount"] >= 100000]  # 成交额≥1 亿，保证流动性
                # 2. 【核心 1：标记首板，确认放量涨停】
                # 先按股票代码分组，计算每只票的涨停标记、首板位置
                if 'limit' in df_filter.columns and 'ts_code' in df_filter.columns:
                    # 标记涨停：limit=1 为涨停
                    df_filter['is_limit'] = df_filter['limit'] == 1
                    # 计算每只票的阶段首次涨停（近 20 天内无涨停）
                    df_filter['limit_20d_count'] = df_filter.groupby('ts_code')['is_limit'].rolling(20).sum().shift(1).reset_index(0, drop=True)
                    df_filter['is_first_board'] = (df_filter['is_limit'] == True) & (df_filter['limit_20d_count'] == 0)
                    # 涨停当天成交量必须是前 5 日均值的 1.5 倍以上（放量涨停）
                    df_filter['vol_5d_avg'] = df_filter.groupby('ts_code')['vol'].rolling(5).mean().shift(1).reset_index(0, drop=True)
                    df_filter['board_vol_growth'] = np.where(
                        df_filter['is_first_board'],
                        df_filter['vol'] / df_filter['vol_5d_avg'],
                        np.nan
                    )
                    # 保留符合放量要求的首板
                    df_filter = df_filter[
                        (df_filter['is_first_board'] == False) |
                        ((df_filter['is_first_board'] == True) & (df_filter['board_vol_growth'] >= lc.get('board_volume_growth', 1.5)))
                    ]
                # 3. 【核心 2：首板后缩量回调，缩量到 1/2~1/3】
                if 'is_first_board' in df_filter.columns and 'vol' in df_filter.columns:
                    # 给每只票的首板编号，记录首板当天的成交量、最高价、最低价
                    df_filter['board_id'] = df_filter.groupby('ts_code')['is_first_board'].cumsum()
                    # 提取首板的核心数据，回填到后续 K 线
                    df_filter['board_vol'] = df_filter.groupby(['ts_code', 'board_id'])['vol'].transform(
                        lambda x: x.iloc[0] if x.iloc[0] > 0 else np.nan
                    )
                    df_filter['board_high'] = df_filter.groupby(['ts_code', 'board_id'])['high'].transform(
                        lambda x: x.iloc[0] if x.iloc[0] > 0 else np.nan
                    )
                    df_filter['board_low'] = df_filter.groupby(['ts_code', 'board_id'])['low'].transform(
                        lambda x: x.iloc[0] if x.iloc[0] > 0 else np.nan
                    )
                    df_filter['board_close'] = df_filter.groupby(['ts_code', 'board_id'])['close'].transform(
                        lambda x: x.iloc[0] if x.iloc[0] > 0 else np.nan
                    )
                    # 计算首板后第几天
                    df_filter['days_after_board'] = df_filter.groupby(['ts_code', 'board_id']).cumcount()
                    # 【核心】计算当前成交量相对首板的缩量比例
                    df_filter['current_vol_ratio'] = df_filter['vol'] / df_filter['board_vol']
                    # 筛选缩量比例符合要求（1/3~1/2）、回调天数符合要求（3~10 天）
                    shrink_range = lc.get('shrink_volume_ratio', [1/3, 1/2])
                    days_range = lc.get('shrink_days_range', [3, 10])
                    df_filter = df_filter[
                        (df_filter['days_after_board'] >= days_range[0]) &
                        (df_filter['days_after_board'] <= days_range[1]) &
                        (df_filter['current_vol_ratio'] >= shrink_range[0]) &
                        (df_filter['current_vol_ratio'] <= shrink_range[1])
                    ]
                # 4. 【核心 3：价格回调到首板的 1/2 或 1/3 支撑位】
                if 'board_high' in df_filter.columns and 'board_low' in df_filter.columns and 'close' in df_filter.columns:
                    support_level = lc.get('pullback_support_level', 0.5)
                    support_tolerance = lc.get('support_tolerance', 0.02)
                    # 计算首板 K 线的支撑位：board_low + (board_high - board_low) * support_level
                    # 例：support_level=0.5 → 1/2 分位；support_level=0.33 → 1/3 分位
                    df_filter['board_support_price'] = df_filter['board_low'] + (df_filter['board_high'] - df_filter['board_low']) * support_level
                    # 筛选收盘价在支撑位±2% 范围内，确认回踩支撑
                    df_filter['price_to_support_ratio'] = (df_filter['close'] - df_filter['board_support_price']) / df_filter['board_support_price']
                    df_filter = df_filter[
                        (df_filter['price_to_support_ratio'] >= -support_tolerance) &
                        (df_filter['price_to_support_ratio'] <= support_tolerance)
                    ]
                logger.info(f"✅ {self.strategy_type}筛选完成，剩余标的：{len(df_filter)}只（首板后缩量回调到支撑位）")
            
            elif self.strategy_type == "板块轮动策略":
                rc = self.strategy_config
                if rc.get('main_trend', True) and 'is_main_industry' in df_filter.columns:
                    df_filter = df_filter[df_filter['is_main_industry'] == 1]
                if rc.get('fund_inflow_top') and 'industry_fund_rank' in df_filter.columns:
                    df_filter = df_filter[df_filter['industry_fund_rank'] <= rc['fund_inflow_top']]
            
            logger.info(f"✅ {self.strategy_type}筛选完成，剩余标的：{len(df_filter)}只")
            return df_filter
        except Exception as e:
            logger.error(f"❌ 策略筛选失败：{e}，返回原始数据")
            return df_filter
    
    def score(self, df):
        """评分"""
        df_score = deepcopy(df)
        if df_score.empty:
            logger.warning("⚠️  评分计算：输入数据为空，直接返回")
            return df_score
        df_score['total_score'] = 0
        df_score['score_detail'] = ''
        for item_name, (score, condition, weight_dict) in self.core_config['items'].items():
            weight = weight_dict.get(self.strategy_type, 1)
            if weight == 0:
                continue
            try:
                import re
                condition_fields = re.findall(r'[a-zA-Z_]+', condition)
                for field in condition_fields:
                    if field not in df_score.columns:
                        logger.warning(f"⚠️  评分维度{item_name}缺少字段{field}，跳过")
                        raise ValueError(f"缺少字段{field}")
                df_score.loc[df_score.eval(condition), 'total_score'] += score * weight
                df_score['score_detail'] = df_score.apply(
                    lambda x: x['score_detail'] + f"{item_name}:{score*weight}分;" if x.eval(condition) else x['score_detail'],
                    axis=1
                )
            except Exception as e:
                logger.warning(f"⚠️  评分维度{item_name}计算失败：{e}，跳过")
        df_pass = df_score[df_score['total_score'] >= self.pass_score].sort_values(by='total_score', ascending=False)
        logger.info(f"✅ {self.strategy_type}评分完成，达标标的：{len(df_pass)}只，最高评分：{df_pass['total_score'].max() if not df_pass.empty else 0}")
        return df_pass

# ============================================== 【回测系统 - 完全保留，仅做多资讯源利空过滤升级】 ==============================================
class BacktestSystem:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
        self.end_date = datetime.strptime(END_DATE, "%Y-%m-%d")
        self.pro, self.utils = get_pro_api(load_config())
        self.strategy_display = STRATEGY_TYPE
        self.strategy = StrategyCore(STRATEGY_TYPE)
        self.trade_records = []
        self.daily_capital = []
        self.current_capital = INIT_CAPITAL
        self.position = {}
        self.max_cash = INIT_CAPITAL
        self.news_sina = pd.DataFrame()
        self.stk_limit = pd.DataFrame()

        logger.info("✅ 回测系统初始化完成，完全基于 Tushare 真实数据，贴合 A 股实盘规则")
    
    def load_extra_data(self):
        """【升级】加载多资讯源新闻、涨跌停等额外数据"""
        self.news_sina = pd.DataFrame()
        self.stk_limit = pd.DataFrame()
        
        # 加载多资讯源全量新闻
        news_path = os.path.join(OUTPUT_DIR, 'multi_news_all.csv')
        if os.path.exists(news_path):
            self.news_sina = pd.read_csv(news_path, encoding='utf-8-sig')
            if 'datetime' in self.news_sina.columns:
                self.news_sina['datetime'] = pd.to_datetime(self.news_sina['datetime'])
            logger.info(f"✅ 多资讯源新闻数据加载完成，共{len(self.news_sina)}条")
        
        # 加载涨跌停数据
        stk_limit_path = os.path.join(OUTPUT_DIR, 'stk_limit.csv')
        if os.path.exists(stk_limit_path):
            self.stk_limit = pd.read_csv(stk_limit_path, encoding='utf-8-sig')
            logger.info("✅ 涨跌停数据加载完成")
    
    def get_cached_data(self):
        """加载已缓存的回测数据"""
        logger.info("开始加载已缓存的回测数据...")
        stock_list_result = self._get("stocks")
        stock_list = [item["ts_code"] for item in stock_list_result.get("stocks", []) if item["has_data"]]
        if not stock_list:
            logger.error("❌ 后端未找到已缓存的股票数据，请先执行数据抓取！")
            return pd.DataFrame()
        stock_basic_result = self._get("stock-basic")
        stock_basic_df = pd.DataFrame(stock_basic_result.get("data", []))
        stk_limit_result = self._get("stk-limit")
        stk_limit_df = pd.DataFrame(stk_limit_result.get("data", []))
        if not stk_limit_df.empty:
            stk_limit_df['trade_date'] = stk_limit_df['trade_date'].astype(str)
        all_stock_data = []
        for ts_code in tqdm(stock_list, desc="个股数据加载进度"):
            try:
                daily_result = self._get(f"stock/{ts_code}/data")
                if "error" in daily_result:
                    continue
                daily_df = pd.DataFrame(daily_result.get("data", []))
                if daily_df.empty:
                    continue
                daily_df['trade_date'] = daily_df['trade_date'].astype(str)
                daily_basic_result = self._get(f"stock/{ts_code}/daily-basic")
                daily_basic_df = pd.DataFrame(daily_basic_result.get("data", []))
                if not daily_basic_df.empty:
                    daily_basic_df['trade_date'] = daily_basic_df['trade_date'].astype(str)
                    daily_df = pd.merge(daily_df, daily_basic_df, on=['ts_code', 'trade_date'], how='left')
                fina_result = self._get(f"stock/{ts_code}/fina-indicator")
                fina_df = pd.DataFrame(fina_result.get("data", []))
                if not fina_df.empty and 'end_date' in fina_df.columns:
                    fina_df['end_date'] = fina_df['end_date'].astype(str)
                    daily_df = pd.merge(daily_df, fina_df, on='ts_code', how='left')
                if not stock_basic_df.empty:
                    basic_info = stock_basic_df[stock_basic_df["ts_code"] == ts_code]
                    if not basic_info.empty:
                        daily_df["name"] = basic_info.iloc[0]["name"]
                        daily_df["industry"] = basic_info.iloc[0]["industry"]
                        daily_df["market"] = basic_info.iloc[0]["market"]
                all_stock_data.append(daily_df)
                logger.info(f"{ts_code}数据加载完成，共{len(daily_df)}条行情记录")
            except Exception as e:
                logger.warning(f"{ts_code}数据加载失败，跳过：{e}")
                continue
        if not all_stock_data:
            logger.error("❌ 未加载到任何有效股票数据！")
            return pd.DataFrame()
        total_df = pd.concat(all_stock_data, axis=0, ignore_index=True)
        if not stk_limit_df.empty:
            total_df = pd.merge(total_df, stk_limit_df, on=["ts_code", "trade_date"], how="left")
        logger.info("开始数据预处理，彻底消除未来函数...")
        total_df["trade_date"] = pd.to_datetime(total_df["trade_date"], format="%Y%m%d", errors="coerce")
        total_df = total_df[(total_df["trade_date"] >= self.start_date) & (total_df["trade_date"] <= self.end_date)]
        required_cols = ["ts_code", "trade_date", "open", "close", "high", "low", "vol", "amount"]
        available_cols = [col for col in required_cols if col in total_df.columns]
        if len(available_cols) < 5:
            logger.error(f"❌ 核心数据列缺失，可用列：{available_cols}，回测无法继续")
            return pd.DataFrame()
        total_df = total_df.dropna(subset=available_cols)
        total_df = total_df.sort_values(by=["ts_code", "trade_date"], ascending=True).reset_index(drop=True)
        if 'limit' in total_df.columns:
            total_df["up_down_times"] = total_df.groupby("ts_code")["limit"].cumsum().shift(1).fillna(0).astype(int)
        if 'close' in total_df.columns:
            total_df["pre_close"] = total_df.groupby("ts_code")["close"].shift(1).fillna(0)
            total_df["open_gap"] = np.where(
                total_df["pre_close"] == 0,
                0,
                ((total_df["open"] - total_df["pre_close"]) / total_df["pre_close"] * 100).fillna(0)
            )
        if 'vol' in total_df.columns:
            total_df["pre_day_volume_growth"] = (total_df.groupby("ts_code")["vol"].shift(1) / total_df.groupby("ts_code")["vol"].shift(2) * 100 - 100).fillna(0)
            total_df["volume_ratio"] = total_df["vol"] / total_df.groupby("ts_code")["vol"].rolling(5).mean().shift(1).fillna(1)
        if 'order_amount' in total_df.columns and 'float_market_cap' in total_df.columns:
            total_df["order_ratio"] = (total_df["order_amount"] / total_df["float_market_cap"] * 100).fillna(0)
        if 'inst_buy' in total_df.columns:
            total_df['inst_buy'] = total_df.groupby('ts_code')['inst_buy'].shift(1).fillna(0)
        if 'youzi_buy' in total_df.columns:
            total_df['youzi_buy'] = total_df.groupby('ts_code')['youzi_buy'].shift(1).fillna(0)
        fillna_dict = {
            "concept_count": 0, "industry_rank": 999, "north_hold_ratio": 0,
            "break_limit_times": 0, "open_times": 0, "net_profit_year": np.nan
        }
        existing_fillna = {k: v for k, v in fillna_dict.items() if k in total_df.columns}
        total_df = total_df.fillna(existing_fillna)
        if "amount" in total_df.columns:
            total_df["amount"] = total_df["amount"].astype(float)
        if "turnover_ratio" in total_df.columns:
            total_df["turnover_ratio"] = total_df["turnover_ratio"].astype(float)
        logger.info("="*60)
        logger.info(f"✅ 数据加载&预处理完成！")
        logger.info(f"回测时间范围：{START_DATE} 至 {END_DATE}")
        logger.info(f"有效交易日：{total_df['trade_date'].nunique()}天")
        logger.info(f"总数据量：{len(total_df)}行，覆盖标的：{total_df['ts_code'].nunique()}只")
        logger.info("="*60)
        return total_df
    
    def _get(self, endpoint, params=None):
        """内部 API 调用"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ API 请求失败 [{endpoint}]：{str(e)}")
            return {}
    
    def update_position_market_value(self, df_today):
        """更新持仓股的市值，处理停牌股"""
        for ts_code, pos in list(self.position.items()):
            stock_data = df_today[df_today["ts_code"] == ts_code]
            if not stock_data.empty:
                close_price = stock_data.iloc[0].get("close", pos["buy_price"])
                self.position[ts_code]["close_price"] = close_price
            else:
                logger.warning(f"{ts_code}当日停牌，沿用前收盘价")
    
    def get_total_asset(self):
        """计算账户总资产（现金 + 持仓市值）"""
        total_asset = self.current_capital
        for pos in self.position.values():
            total_asset += pos["volume"] * pos.get("close_price", pos["buy_price"])
        return total_asset
    
    def check_drawdown(self):
        """检查最大回撤，更新账户峰值"""
        total_asset = self.get_total_asset()
        if total_asset > self.max_cash:
            self.max_cash = total_asset
        current_drawdown = (self.max_cash - total_asset) / self.max_cash
        if current_drawdown >= MAX_DRAWDOWN_STOP:
            logger.warning(f"⚠️  账户最大回撤达到{current_drawdown:.2%}，触发强制清仓！")
            self.position = {}
            self.daily_capital.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "capital": self.get_total_asset(),
                "status": "空仓休市"
            })
            return True
        return False
    
    def calculate_position(self, buy_price, ts_code, df_today):
        """计算可买仓位，完全贴合 A 股实盘规则，涨跌停价格限制"""
        single_max_cash = self.current_capital * SINGLE_STOCK_POSITION
        if 'vol' not in df_today.columns:
            return 0, 0
        stock_vol = df_today[df_today["ts_code"] == ts_code]["vol"].iloc[0]
        if pd.isna(stock_vol) or stock_vol <= 0:
            return 0, 0
        max_trade_hand = int(stock_vol * MAX_TRADE_RATIO)
        max_trade_vol = max_trade_hand * 100
        available_hand = int((single_max_cash - MIN_COMMISSION) / buy_price / 100)
        available_vol = available_hand * 100
        buy_vol = min(available_vol, max_trade_vol, 100000)
        if buy_vol < 100:
            return 0, 0
        buy_amount = buy_price * buy_vol
        buy_commission = max(buy_amount * COMMISSION_RATE, MIN_COMMISSION)
        buy_cost = buy_amount + buy_commission
        return buy_vol, buy_cost
    
    def select_stocks(self, current_date, df_today):
        """【升级】多资讯源利空过滤选股逻辑"""
        # 1. 先运行你现有的选股逻辑
        selected = self.strategy.filter(df_today)
        selected = self.strategy.score(selected)
        
        # 2. 【升级】多资讯源利空过滤
        if not self.news_sina.empty and not selected.empty:
            current_dt = pd.to_datetime(current_date)
            # 扩大新闻窗口到前后 5 天，覆盖所有资讯源的公告/快讯
            news_window = self.news_sina[
                (self.news_sina['datetime'] >= current_dt - timedelta(days=5)) &
                (self.news_sina['datetime'] <= current_dt)
            ]
            
            # 扩展利空关键词，覆盖更多风险场景
            bad_keywords = [
                "跌停", "暴跌", "亏损", "立案", "调查", "减持", "质押平仓",
                "问询", "监管", "退市", "暴雷", "造假", "违约", "诉讼",
                "利空", "大跌", "解禁", "业绩变脸", "预亏", "下修"
            ]
            bad_news_stocks = []
            
            for _, news in news_window.iterrows():
                title = str(news.get('title', ''))
                content = str(news.get('content', ''))
                news_text = title + content
                
                # 检查是否有利空关键词
                if any(keyword in news_text for keyword in bad_keywords):
                    # 如果新闻里提到了股票代码，加入剔除列表
                    if 'ts_code' in news and pd.notna(news['ts_code']):
                        bad_news_stocks.append(news['ts_code'])
            
            # 从选中的股票里剔除有利空新闻的
            if bad_news_stocks:
                bad_news_stocks = list(set(bad_news_stocks))  # 去重
                selected = selected[~selected['ts_code'].isin(bad_news_stocks)]
                logger.info(f"  多资讯源利空过滤，剔除股票：{bad_news_stocks}")
        
        return selected
    
    def run(self, df_total):
        """运行回测"""
        if df_total.empty:
            logger.error("❌ 回测执行失败：无有效回测数据！")
            return pd.DataFrame(), pd.DataFrame()
        if self.check_drawdown():
            return pd.DataFrame(), pd.DataFrame()
        
        self.load_extra_data()
        
        logger.info(f"开始执行{self.strategy_display}策略回测，严格贴合 A 股实盘规则，无未来函数...")
        if 'trade_date' not in df_total.columns:
            logger.error("❌ 回测数据缺少 trade_date 列，无法执行！")
            return pd.DataFrame(), pd.DataFrame()
        trade_dates = sorted(df_total["trade_date"].unique())
        drawdown_stop_days = 0
        
        for date in tqdm(trade_dates, desc="回测进度"):
            if not get_app_running():
                break
            try:
                date_str = date.strftime("%Y-%m-%d")
                df_today = df_total[df_total["trade_date"] == date].copy()
                
                if drawdown_stop_days > 0:
                    self.daily_capital.append({"date": date_str, "capital": self.get_total_asset(), "status": "休市"})
                    drawdown_stop_days -= 1
                    continue
                if self.check_drawdown():
                    drawdown_stop_days = DRAWDOWN_STOP_DAYS
                    continue
                
                self.update_position_market_value(df_today)
                
                sell_ts_codes = []
                for ts_code, pos in list(self.position.items()):
                    stock_data = df_today[df_today["ts_code"] == ts_code]
                    if stock_data.empty:
                        continue
                    stock_data = stock_data.iloc[0]
                    hold_days = (date - pos["buy_date"]).days
                    sell_flag = False
                    sell_price = 0
                    sell_reason = ""
                    
                    # 【适配缩量潜伏策略】获取策略专属止损止盈参数
                    strategy_config_key = self.strategy_display
                    sl_rate = STRATEGY_CONFIG[strategy_config_key].get('stop_loss_rate', STOP_LOSS_RATE)
                    sp_rate = STRATEGY_CONFIG[strategy_config_key].get('stop_profit_rate', STOP_PROFIT_RATE)
                    max_hold_days = STRATEGY_CONFIG[strategy_config_key].get('max_hold_days', MAX_HOLD_DAYS)
                    
                    open_price = stock_data.get("open", pos["buy_price"])
                    low_price = stock_data.get("low", pos["buy_price"])
                    high_price = stock_data.get("high", pos["buy_price"])
                    close_price = stock_data.get("close", pos["buy_price"])
                    
                    up_limit_price = pos["buy_price"] * 1.1
                    down_limit_price = pos["buy_price"] * 0.9
                    
                    # 【缩量潜伏策略专属】简化止损逻辑，避免 board_low 字段缺失问题
                    if not sell_flag and open_price <= down_limit_price:
                        continue
                    if not sell_flag and open_price <= pos["buy_price"] * (1 - sl_rate):
                        sell_flag = True
                        sell_price = max(open_price * (1 - SLIPPAGE_RATE), down_limit_price)
                        sell_reason = "开盘破止损"
                    elif not sell_flag and low_price <= pos["buy_price"] * (1 - sl_rate) and open_price > pos["buy_price"] * (1 - sl_rate):
                        sell_flag = True
                        sell_price = max(pos["buy_price"] * (1 - sl_rate), down_limit_price)
                        sell_reason = "盘中破止损"
                    elif open_price >= up_limit_price:
                        continue
                    elif not sell_flag and open_price >= pos["buy_price"] * (1 + sp_rate):
                        sell_flag = True
                        sell_price = min(open_price * (1 - SLIPPAGE_RATE), up_limit_price)
                        sell_reason = "开盘破止盈"
                    elif not sell_flag and high_price >= pos["buy_price"] * (1 + sp_rate) and open_price < pos["buy_price"] * (1 + sp_rate):
                        sell_flag = True
                        sell_price = min(pos["buy_price"] * (1 + sp_rate), up_limit_price)
                        sell_reason = "盘中破止盈"
                    elif not sell_flag and hold_days >= max_hold_days:
                        sell_flag = True
                        sell_price = close_price * (1 - SLIPPAGE_RATE)
                        sell_reason = "持股周期到期"
                    elif not sell_flag and self.strategy_display == '板块轮动策略' and hold_days % STRATEGY_CONFIG[strategy_config_key]['rotate_days'] == 0:
                        sell_flag = True
                        sell_price = close_price * (1 - SLIPPAGE_RATE)
                        sell_reason = "轮动调仓"
                    
                    if sell_flag:
                        sell_amount = sell_price * pos["volume"]
                        sell_commission = max(sell_amount * COMMISSION_RATE, MIN_COMMISSION)
                        stamp_tax = sell_amount * STAMP_TAX_RATE
                        sell_income = sell_amount - sell_commission - stamp_tax
                        profit = sell_income - pos["buy_cost"]
                        profit_rate = (sell_price / pos["buy_price"] - 1) * 100
                        self.current_capital = round(self.current_capital + (sell_income - pos["buy_cost"]), 2)
                        self.trade_records.append({
                            "买入日期": pos["buy_date"].strftime("%Y-%m-%d"),
                            "卖出日期": date_str,
                            "股票代码": ts_code,
                            "股票名称": pos.get("stock_name", "未知"),
                            "买入价格": round(pos["buy_price"], 2),
                            "卖出价格": round(sell_price, 2),
                            "买入数量": pos["volume"],
                            "买入成本": round(pos["buy_cost"], 2),
                            "卖出收入": round(sell_income, 2),
                            "单笔盈亏": round(profit, 2),
                            "盈亏比例": round(profit_rate, 2),
                            "卖出原因": sell_reason,
                            "23 维评分": pos.get("total_score", 0),
                            "所属行业": pos.get("industry", "未知")
                        })
                        sell_ts_codes.append(ts_code)
                
                for ts_code in sell_ts_codes:
                    if ts_code in self.position:
                        del self.position[ts_code]
                
                if len(self.position) < MAX_HOLD_STOCKS and self.current_capital > 1000:
                    df_filter = self.strategy.filter(df_today)
                    if df_filter.empty:
                        self.daily_capital.append({"date": date_str, "capital": self.get_total_asset()})
                        continue
                    df_pass = self.select_stocks(date, df_filter)
                    if df_pass.empty:
                        self.daily_capital.append({"date": date_str, "capital": self.get_total_asset()})
                        continue
                    
                    target_stocks = df_pass.head(MAX_HOLD_STOCKS - len(self.position))
                    for _, target in target_stocks.iterrows():
                        ts_code = target["ts_code"]
                        if ts_code in self.position:
                            continue
                        
                        if 'open' not in target or pd.isna(target['open']):
                            continue
                        target_open = target['open']
                        
                        pre_close = target.get("pre_close", target_open)
                        if pre_close == 0:
                            continue
                        up_limit_price = pre_close * 1.1
                        down_limit_price = pre_close * 0.9
                        if target_open >= up_limit_price or target_open <= down_limit_price:
                            logger.info(f"{ts_code}开盘涨跌停，无法买入，跳过")
                            continue
                        
                        buy_price = min(target_open * (1 + SLIPPAGE_RATE), up_limit_price)
                        buy_vol, buy_cost = self.calculate_position(buy_price, ts_code, df_today)
                        if buy_vol < 100 or buy_cost > self.current_capital:
                            continue
                        
                        self.current_capital = round(self.current_capital - buy_cost, 2)
                        self.position[ts_code] = {
                            "stock_name": target.get("name", "未知"),
                            "buy_date": date,
                            "buy_price": buy_price,
                            "volume": buy_vol,
                            "buy_cost": buy_cost,
                            "close_price": target.get("close", buy_price),
                            "total_score": target.get("total_score", 0),
                            "industry": target.get("industry", "未知")
                        }
                
                self.daily_capital.append({"date": date_str, "capital": self.get_total_asset()})
            except Exception as e:
                logger.error(f"❌ 交易日{date_str}回测异常：{e}，跳过该交易日")
                continue
        
        if self.position:
            logger.info("回测结束，强制卖出剩余持仓")
            last_date = trade_dates[-1].strftime("%Y-%m-%d") if len(trade_dates) > 0 else datetime.now().strftime("%Y-%m-%d")
            for ts_code, pos in list(self.position.items()):
                sell_price = pos.get("close_price", pos["buy_price"]) * (1 - SLIPPAGE_RATE)
                sell_amount = sell_price * pos["volume"]
                sell_commission = max(sell_amount * COMMISSION_RATE, MIN_COMMISSION)
                stamp_tax = sell_amount * STAMP_TAX_RATE
                sell_income = sell_amount - sell_commission - stamp_tax
                profit = sell_income - pos["buy_cost"]
                profit_rate = (sell_price / pos["buy_price"] - 1) * 100
                self.current_capital = round(self.current_capital + (sell_income - pos["buy_cost"]), 2)
                self.trade_records.append({
                    "买入日期": pos["buy_date"].strftime("%Y-%m-%d"),
                    "卖出日期": last_date,
                    "股票代码": ts_code,
                    "股票名称": pos.get("stock_name", "未知"),
                    "买入价格": round(pos["buy_price"], 2),
                    "卖出价格": round(sell_price, 2),
                    "买入数量": pos["volume"],
                    "买入成本": round(pos["buy_cost"], 2),
                    "卖出收入": round(sell_income, 2),
                    "单笔盈亏": round(profit, 2),
                    "盈亏比例": round(profit_rate, 2),
                    "卖出原因": "回测结束强制卖出",
                    "23 维评分": pos.get("total_score", 0),
                    "所属行业": pos.get("industry", "未知")
                })
                del self.position[ts_code]
        
        logger.info("\n✅ 回测完成！正在生成详细回测报告...")
        df_trade = pd.DataFrame(self.trade_records)
        df_capital = pd.DataFrame(self.daily_capital)
        total_trades = len(df_trade)
        win_trades = len(df_trade[df_trade["单笔盈亏"] > 0]) if total_trades > 0 else 0
        loss_trades = len(df_trade[df_trade["单笔盈亏"] < 0]) if total_trades > 0 else 0
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        total_profit = self.current_capital - INIT_CAPITAL
        total_return_rate = (self.current_capital / INIT_CAPITAL - 1) * 100 if INIT_CAPITAL > 0 else 0
        date_diff = (self.end_date - self.start_date).days
        if date_diff < 90:
            annual_return_desc = f"累计收益率{total_return_rate:.2f}%（回测周期不足 3 个月，不计算年化）"
            annual_return = total_return_rate
            use_annual = False
        else:
            annual_return = (total_return_rate / (date_diff / 365))
            annual_return_desc = f"年化收益率{annual_return:.2f}%"
            use_annual = True
        
        max_drawdown = 0
        if not df_capital.empty:
            df_capital["max_cash"] = df_capital["capital"].cummax()
            df_capital["drawdown"] = (df_capital["max_cash"] - df_capital["capital"]) / df_capital["max_cash"] * 100
            max_drawdown = df_capital["drawdown"].max() if not df_capital["drawdown"].empty else 0
        
        avg_profit = df_trade["单笔盈亏"].mean() if total_trades > 0 else 0
        total_commission = 0
        
        logger.info("="*80)
        logger.info(f"📊 【{self.strategy_display}策略】回测核心指标（含滑点{SLIPPAGE_RATE*100}%）")
        logger.info(f"初始本金：{INIT_CAPITAL}元 | 期末资金：{round(self.current_capital, 2)}元 | 总盈利：{round(total_profit, 2)}元")
        logger.info(f"总收益率：{round(total_return_rate, 2)}% | {annual_return_desc}")
        logger.info(f"总交易次数：{total_trades}次 | 盈利：{win_trades}次 | 亏损：{loss_trades}次 | 胜率：{round(win_rate, 2)}%")
        logger.info(f"最大回撤：{round(max_drawdown, 2)}% | 平均单笔盈亏：{round(avg_profit, 2)}元 | 总交易成本：{round(total_commission, 2)}元")
        logger.info("="*80)
        
        try:
            with pd.ExcelWriter("一体化回测结果报告.xlsx", engine='openpyxl') as writer:
                if not df_trade.empty:
                    df_trade.to_excel(writer, sheet_name='逐笔交易全记录', index=False)
                if not df_capital.empty:
                    df_capital.to_excel(writer, sheet_name='每日资金曲线', index=False)
                df_indicator = pd.DataFrame([
                    {"指标名称": "初始本金（元）", "指标值": INIT_CAPITAL},
                    {"指标名称": "期末资金（元）", "指标值": round(self.current_capital, 2)},
                    {"指标名称": "总盈利（元）", "指标值": round(total_profit, 2)},
                    {"指标名称": "总收益率", "指标值": f"{round(total_return_rate, 2)}%"},
                    {"指标名称": "年化收益率", "指标值": f"{round(annual_return, 2)}%"},
                    {"指标名称": "总交易次数", "指标值": total_trades},
                    {"指标名称": "盈利次数", "指标值": win_trades},
                    {"指标名称": "亏损次数", "指标值": loss_trades},
                    {"指标名称": "胜率", "指标值": f"{round(win_rate, 2)}%"},
                    {"指标名称": "最大回撤", "指标值": f"{round(max_drawdown, 2)}%"},
                    {"指标名称": "平均单笔盈亏（元）", "指标值": round(avg_profit, 2)},
                    {"指标名称": "总交易成本（元）", "指标值": round(total_commission, 2)},
                    {"指标名称": "策略类型", "指标值": self.strategy_display},
                    {"指标名称": "回测时间范围", "指标值": f"{START_DATE}至{END_DATE}"},
                    {"指标名称": "有效交易日", "指标值": df_capital["date"].nunique() if not df_capital.empty else 0},
                    {"指标名称": "单边滑点", "指标值": f"{SLIPPAGE_RATE*100}%"}
                ])
                df_indicator.to_excel(writer, sheet_name='核心回测指标', index=False)
                if not df_trade.empty and "所属行业" in df_trade.columns:
                    df_industry = df_trade.groupby("所属行业")["单笔盈亏"].agg(["sum", "mean", "count"]).reset_index()
                    df_industry.columns = ["所属行业", "行业总盈亏", "行业平均盈亏", "行业交易次数"]
                    df_industry.to_excel(writer, sheet_name='行业盈亏统计', index=False)
                
                workbook = writer.book
                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"✅ 回测报告已导出：一体化回测结果报告.xlsx")
        except Exception as e:
            logger.warning(f"⚠️  回测报告导出失败：{e}")
        
        if VISUALIZATION:
            self.run_visualization(df_capital, df_trade)
        
        del df_total
        gc.collect()
        
        return df_trade, df_capital
    
    def run_visualization(self, df_capital, df_trade):
        """运行可视化"""
        if not VISUALIZATION or df_capital.empty:
            return
        logger.info("开始生成回测可视化图表...")
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f"量化策略回测报告 - {self.strategy_display} | {START_DATE}至{END_DATE}", fontsize=16, fontweight='bold')
            
            df_capital["date"] = pd.to_datetime(df_capital["date"])
            df_capital["return_rate"] = (df_capital["capital"] / INIT_CAPITAL - 1) * 100
            ax1.plot(df_capital["date"], df_capital["capital"], color="#2E86AB", linewidth=2, label=f"初始本金：{INIT_CAPITAL}元")
            ax1.set_title("账户资金曲线", fontsize=14, fontweight='bold')
            ax1.set_xlabel("日期")
            ax1.set_ylabel("资金（元）")
            ax1.legend()
            ax1.grid(alpha=0.3)
            
            ax2.plot(df_capital["date"], df_capital["return_rate"], color="#E63946", linewidth=2)
            ax2.set_title("累计收益率曲线", fontsize=14, fontweight='bold')
            ax2.set_xlabel("日期")
            ax2.set_ylabel("累计收益率（%）")
            ax2.grid(alpha=0.3)
            
            df_capital["max_cash"] = df_capital["capital"].cummax()
            df_capital["drawdown"] = (df_capital["max_cash"] - df_capital["capital"]) / df_capital["max_cash"] * 100
            ax3.fill_between(df_capital["date"], 0, df_capital["drawdown"], color="#F77F00", alpha=0.3)
            ax3.plot(df_capital["date"], df_capital["drawdown"], color="#F77F00", linewidth=2)
            ax3.set_title("账户最大回撤曲线", fontsize=14, fontweight='bold')
            ax3.set_xlabel("日期")
            ax3.set_ylabel("回撤（%）")
            ax3.grid(alpha=0.3)
            
            if not df_trade.empty:
                win_num = len(df_trade[df_trade["单笔盈亏"] > 0])
                loss_num = len(df_trade[df_trade["单笔盈亏"] < 0])
                neutral_num = len(df_trade[df_trade["单笔盈亏"] == 0])
                labels = ["盈利", "亏损", "平盘"]
                sizes = [win_num, loss_num, neutral_num]
                colors = ["#06D6A0", "#E63946", "#FFD166"]
                ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax4.set_title(f"交易胜率（总交易{len(df_trade)}次）", fontsize=14, fontweight='bold')
            else:
                ax4.text(0.5, 0.5, "无交易记录", ha='center', va='center', fontsize=16)
                ax4.set_title("交易胜率", fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            chart_path = os.path.join(CHART_DIR, f"回测报告_{datetime.now().strftime('%Y%m%d')}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"✅ 可视化图表已保存：{chart_path}")
        except Exception as e:
            logger.warning(f"⚠️  可视化生成失败：{e}")

# ============================================== 【每日选股模块 - 完全保留，仅做小修复】 ==============================================
class DailyStockPicker:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.config = STOCK_PICK_CONFIG
        self.pro, self.utils = get_pro_api(load_config())
        self.strategy_display = STRATEGY_TYPE
        self.strategy = StrategyCore(STRATEGY_TYPE)
        logger.info(f"✅ 今日选股系统初始化完成 | 策略：{self.strategy_display} | 最大输出{self.config['max_output_count']}只")
    
    def _get(self, endpoint, params=None):
        """内部 API 调用"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ API 请求失败 [{endpoint}]：{str(e)}")
            return {}
    
    def get_latest_data(self):
        """加载最新交易日数据"""
        logger.info("="*60)
        logger.info("开始加载最新交易日数据（仅前一个完整交易日，无未来函数）")
        logger.info("="*60)
        
        stock_list_result = self._get("stocks")
        stock_list = [item["ts_code"] for item in stock_list_result.get("stocks", []) if item["has_data"]]
        if not stock_list:
            logger.error("❌ 未找到有效股票数据，请先完成数据抓取！")
            return pd.DataFrame(), None
        stock_basic_result = self._get("stock-basic")
        stock_basic_df = pd.DataFrame(stock_basic_result.get("data", []))
        logger.info(f"已加载 {len(stock_list)} 只股票基础信息")
        
        latest_trade_date = self.utils.get_prev_trade_date(datetime.now())
        latest_trade_date_api = latest_trade_date.strftime("%Y%m%d")
        logger.info(f"最新有效交易日：{latest_trade_date.strftime('%Y-%m-%d')}")
        
        stk_limit_result = self._get("stk-limit", {'start_date': latest_trade_date_api, 'end_date': latest_trade_date_api})
        stk_limit_df = pd.DataFrame(stk_limit_result.get("data", []))
        if stk_limit_df.empty:
            logger.warning("⚠️  未获取到最新交易日涨跌停数据！")
        else:
            stk_limit_df['trade_date'] = stk_limit_df['trade_date'].astype(str)
            logger.info(f"已加载 {len(stk_limit_df)} 条涨跌停数据")
        
        all_stock_data = []
        for ts_code in tqdm(stock_list, desc="个股最新数据加载进度"):
            try:
                daily_result = self._get(f"stock/{ts_code}/data")
                if "error" in daily_result:
                    continue
                daily_df = pd.DataFrame(daily_result.get("data", []))
                if daily_df.empty:
                    continue
                daily_df["trade_date"] = pd.to_datetime(daily_df["trade_date"], format="%Y%m%d", errors="coerce")
                daily_df = daily_df[daily_df["trade_date"] == latest_trade_date]
                if daily_df.empty:
                    continue
                
                daily_basic_result = self._get(f"stock/{ts_code}/daily-basic")
                daily_basic_df = pd.DataFrame(daily_basic_result.get("data", []))
                if not daily_basic_df.empty:
                    daily_basic_df["trade_date"] = pd.to_datetime(daily_basic_df["trade_date"], format="%Y%m%d", errors="coerce")
                    daily_basic_df = daily_basic_df[daily_basic_df["trade_date"] == latest_trade_date]
                    daily_df = pd.merge(daily_df, daily_basic_df, on=['ts_code', 'trade_date'], how='left')
                
                fina_result = self._get(f"stock/{ts_code}/fina-indicator")
                fina_df = pd.DataFrame(fina_result.get("data", []))
                if not fina_df.empty and 'end_date' in fina_df.columns:
                    fina_df['end_date'] = fina_df['end_date'].astype(str)
                    daily_df = pd.merge(daily_df, fina_df, on='ts_code', how='left')
                
                if not stock_basic_df.empty:
                    basic_info = stock_basic_df[stock_basic_df["ts_code"] == ts_code]
                    if not basic_info.empty:
                        daily_df["name"] = basic_info.iloc[0]["name"]
                        daily_df["industry"] = basic_info.iloc[0]["industry"]
                        daily_df["area"] = basic_info.iloc[0]["area"]
                        daily_df["market"] = basic_info.iloc[0]["market"]
                all_stock_data.append(daily_df)
            except Exception as e:
                logger.warning(f"{ts_code}数据加载失败，跳过：{e}")
                continue
        
        if not all_stock_data:
            logger.error("❌ 未加载到任何有效股票数据！")
            return pd.DataFrame(), None
        total_df = pd.concat(all_stock_data, axis=0, ignore_index=True)
        if not stk_limit_df.empty:
            stk_limit_df["trade_date"] = pd.to_datetime(stk_limit_df["trade_date"], format="%Y%m%d", errors="coerce")
            total_df = pd.merge(total_df, stk_limit_df, on=["ts_code", "trade_date"], how="left")
        
        if 'close' in total_df.columns:
            total_df["pre_close"] = total_df.groupby("ts_code")["close"].shift(1).fillna(0)
            total_df["open_gap"] = np.where(
                total_df["pre_close"] == 0,
                0,
                ((total_df["open"] - total_df["pre_close"]) / total_df["pre_close"] * 100).fillna(0)
            )
        if 'vol' in total_df.columns:
            total_df["volume_ratio"] = total_df["vol"] / total_df.groupby("ts_code")["vol"].rolling(5).mean().shift(1).fillna(1)
        if 'order_amount' in total_df.columns and 'float_market_cap' in total_df.columns:
            total_df["order_ratio"] = (total_df["order_amount"] / total_df["float_market_cap"] * 100).fillna(0)
        
        if 'inst_buy' in total_df.columns:
            total_df['inst_buy'] = total_df.groupby('ts_code')['inst_buy'].shift(1).fillna(0)
        if 'youzi_buy' in total_df.columns:
            total_df['youzi_buy'] = total_df.groupby('ts_code')['youzi_buy'].shift(1).fillna(0)
        
        fillna_dict = {
            "concept_count": 0, "industry_rank": 999, "north_hold_ratio": 0,
            "break_limit_times": 0, "open_times": 0, "net_profit_year": np.nan
        }
        existing_fillna = {k: v for k, v in fillna_dict.items() if k in total_df.columns}
        total_df = total_df.fillna(existing_fillna)
        
        if 'market' in total_df.columns and self.config['only_main_board']:
            total_df = total_df[total_df["market"].apply(lambda x: is_market_allowed(x, ["主板"]))]
            logger.info(f"经过主板过滤后剩余标的：{len(total_df)}只")
        
        logger.info("="*60)
        logger.info(f"✅ 最新数据加载完成！")
        logger.info(f"最新交易日：{latest_trade_date.strftime('%Y-%m-%d')}")
        logger.info(f"有效标的数量：{len(total_df)}只")
        logger.info("="*60)
        return total_df, latest_trade_date
    
    def pick_stocks(self, df_latest, trade_date):
        """执行选股"""
        if df_latest.empty or trade_date is None:
            logger.error("❌ 选股执行失败：无有效最新数据！")
            return pd.DataFrame()
        trade_date_str = trade_date.strftime("%Y-%m-%d")
        logger.info(f"开始执行{self.strategy_display}策略选股 | 日期：{trade_date_str}")
        
        df_filter = self.strategy.filter(df_latest)
        if df_filter.empty:
            logger.warning("❌ 无符合前置筛选条件的标的！")
            return pd.DataFrame()
        df_pass = self.strategy.score(df_filter)
        if df_pass.empty:
            logger.warning(f"❌ 无符合评分要求（≥{self.strategy.pass_score}分）的标的！")
            return pd.DataFrame()
        
        df_result = df_pass.head(self.config['max_output_count']).reset_index(drop=True)
        available_cols = [col for col in [
            "ts_code", "name", "industry", "market", "total_score", "score_detail",
            "open", "close", "high", "low", "amount", "turnover_ratio",
            "up_down_times", "limit", "first_limit_time", "open_gap",
            "order_ratio", "volume_ratio", "inst_buy", "youzi_buy"
        ] if col in df_result.columns]
        result_df = df_result[available_cols].copy()
        
        rename_dict = {
            "ts_code": "股票代码", "name": "股票名称", "industry": "所属行业", "market": "所属板块",
            "total_score": "23 维总评分", "score_detail": "评分明细", "open": "开盘价", "close": "收盘价",
            "high": "最高价", "low": "最低价", "amount": "成交额 (万元)", "turnover_ratio": "换手率 (%)",
            "up_down_times": "连板高度", "limit": "是否涨停 (1=是)", "first_limit_time": "首次封板时间",
            "open_gap": "高开幅度 (%)", "order_ratio": "封单比 (%)", "volume_ratio": "量比",
            "inst_buy": "机构净买入 (万元)", "youzi_buy": "游资净买入 (万元)"
        }
        available_rename = {k: v for k, v in rename_dict.items() if k in result_df.columns}
        result_df.rename(columns=available_rename, inplace=True)
        
        if "成交额 (万元)" in result_df.columns:
            result_df["成交额 (万元)"] = (result_df["成交额 (万元)"] / 10).round(2)
        if "机构净买入 (万元)" in result_df.columns:
            result_df["机构净买入 (万元)"] = result_df["机构净买入 (万元)"].round(2)
        if "游资净买入 (万元)" in result_df.columns:
            result_df["游资净买入 (万元)"] = result_df["游资净买入 (万元)"].round(2)
        for col in ["开盘价", "收盘价", "最高价", "最低价"]:
            if col in result_df.columns:
                result_df[col] = result_df[col].round(2)
        
        logger.info("="*100)
        logger.info(f"📈 【{trade_date_str}】{self.strategy_display}策略选股结果（按评分从高到低）")
        logger.info("="*100)
        print_cols = [col for col in result_df.columns if col != "评分明细"]
        print(result_df.to_string(index=False, columns=print_cols))
        logger.info("="*100)
        
        if self.config['export_excel']:
            file_name = f"{trade_date.strftime('%Y%m%d')}_{self.strategy_display}_选股结果清单.xlsx"
            try:
                with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='选股结果', index=False)
                    score_rule_df = pd.DataFrame([
                        {"评分维度": item_name, "基础分值": score, "策略权重": weight_dict.get(self.strategy_display, weight_dict.get(STRATEGY_TYPE, 1)),
                         "达标条件": condition, "策略实际分值": score * weight_dict.get(self.strategy_display, weight_dict.get(STRATEGY_TYPE, 1))}
                        for item_name, (score, condition, weight_dict) in CORE_CONFIG['items'].items()
                    ])
                    score_rule_df.to_excel(writer, sheet_name='评分规则明细', index=False)
                    strategy_config_key = self.strategy_display if self.strategy_display in STRATEGY_CONFIG else STRATEGY_TYPE
                    strategy_config_df = pd.DataFrame([
                        {"配置项": k, "配置值": v} for k, v in STRATEGY_CONFIG[strategy_config_key].items()
                    ])
                    strategy_config_df.to_excel(writer, sheet_name='策略专属配置', index=False)
                    
                    workbook = writer.book
                    for sheet_name in workbook.sheetnames:
                        worksheet = workbook[sheet_name]
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                
                logger.info(f"✅ 选股结果已导出：{file_name}")
            except Exception as e:
                logger.warning(f"⚠️  选股结果导出失败：{e}")
        
        del df_latest
        gc.collect()
        
        return result_df

# ============================================== 【参数优化建议模块 - 完全保留】 ==============================================
def generate_param_optimize_suggestion(backtest_result):
    """生成参数优化建议"""
    df_trade, df_capital = backtest_result
    if df_trade.empty or df_capital.empty:
        return "回测数据为空，无交易记录，无法生成优化建议"
    
    total_trades = len(df_trade)
    win_trades = len(df_trade[df_trade["单笔盈亏"] > 0]) if total_trades > 0 else 0
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    
    max_drawdown = 0
    if not df_capital.empty:
        df_capital["max_cash"] = df_capital["capital"].cummax()
        df_capital["drawdown"] = (df_capital["max_cash"] - df_capital["capital"]) / df_capital["max_cash"] * 100
        max_drawdown = df_capital["drawdown"].max() if not df_capital["drawdown"].empty else 0
    
    final_capital = df_capital.iloc[-1]["capital"] if not df_capital.empty else INIT_CAPITAL
    total_profit = final_capital - INIT_CAPITAL
    total_return = (total_profit / INIT_CAPITAL) * 100 if INIT_CAPITAL > 0 else 0
    date_diff = (datetime.strptime(END_DATE, "%Y-%m-%d") - datetime.strptime(START_DATE, "%Y-%m-%d")).days
    if date_diff < 90:
        annual_return_desc = f"累计收益率{total_return:.2f}%（回测周期不足 3 个月，不计算年化）"
        annual_return = total_return
        use_annual = False
    else:
        annual_return = (total_return / (date_diff / 365))
        annual_return_desc = f"年化收益率{annual_return:.2f}%"
        use_annual = True
    
    suggestions = []
    strategy_type = STRATEGY_TYPE
    
    if win_rate < 40:
        suggestions.append(f"1. 胜率偏低（{win_rate:.2f}% < 40%）：")
        if strategy_type == "打板策略":
            suggestions.append(f"   ├─ 建议将 CORE_CONFIG['pass_score'] 从 {CORE_CONFIG['pass_score']} 提高到 {CORE_CONFIG['pass_score']+2}-{CORE_CONFIG['pass_score']+4}")
            suggestions.append(f"   └─ 建议将 STRATEGY_CONFIG['打板策略']['link_board_range'] 从 {STRATEGY_CONFIG['打板策略']['link_board_range']} 改为 [{STRATEGY_CONFIG['打板策略']['link_board_range'][0]}, {STRATEGY_CONFIG['打板策略']['link_board_range'][1]-1}]")
        elif strategy_type == "缩量潜伏策略":
            suggestions.append(f"   ├─ 建议将 CORE_CONFIG['pass_score'] 从 {CORE_CONFIG['pass_score']} 提高到 {CORE_CONFIG['pass_score']+1}-{CORE_CONFIG['pass_score']+3}")
            suggestions.append(f"   └─ 建议将 STRATEGY_CONFIG['缩量潜伏策略']['max_pb'] 从 {STRATEGY_CONFIG['缩量潜伏策略']['max_pb']} 降低到 {STRATEGY_CONFIG['缩量潜伏策略']['max_pb']-0.5}")
        elif strategy_type == "板块轮动策略":
            suggestions.append(f"   ├─ 建议将 CORE_CONFIG['pass_score'] 从 {CORE_CONFIG['pass_score']} 提高到 {CORE_CONFIG['pass_score']+1}-{CORE_CONFIG['pass_score']+2}")
            suggestions.append(f"   └─ 建议将 STRATEGY_CONFIG['板块轮动策略']['fund_inflow_top'] 从 {STRATEGY_CONFIG['板块轮动策略']['fund_inflow_top']} 降低到 {STRATEGY_CONFIG['板块轮动策略']['fund_inflow_top']-10}")
    elif win_rate > 60:
        suggestions.append(f"1. 胜率较高（{win_rate:.2f}% > 60%）：")
        suggestions.append(f"   ├─ 建议将 CORE_CONFIG['pass_score'] 从 {CORE_CONFIG['pass_score']} 降低到 {CORE_CONFIG['pass_score']-2}-{CORE_CONFIG['pass_score']-1}")
        suggestions.append(f"   └─ 建议将 MAX_HOLD_STOCKS 从 {MAX_HOLD_STOCKS} 提高到 {MAX_HOLD_STOCKS+1}-{MAX_HOLD_STOCKS+2}")
    else:
        suggestions.append(f"1. 胜率正常（{win_rate:.2f}%），保持当前配置即可")
    
    if max_drawdown > 20:
        suggestions.append(f"\n2. 最大回撤偏大（{max_drawdown:.2f}% > 20%）：")
        suggestions.append(f"   ├─ 建议将 STOP_LOSS_RATE 从 {STOP_LOSS_RATE} 降低到 {STOP_LOSS_RATE-0.02}-{STOP_LOSS_RATE-0.01}")
        suggestions.append(f"   └─ 建议将 SINGLE_STOCK_POSITION 从 {SINGLE_STOCK_POSITION} 降低到 {SINGLE_STOCK_POSITION-0.05}-{SINGLE_STOCK_POSITION-0.1}")
    elif max_drawdown < 10:
        suggestions.append(f"\n2. 最大回撤较小（{max_drawdown:.2f}% < 10%）：")
        suggestions.append(f"   ├─ 建议将 STOP_LOSS_RATE 从 {STOP_LOSS_RATE} 提高到 {STOP_LOSS_RATE+0.01}-{STOP_LOSS_RATE+0.02}")
        suggestions.append(f"   └─ 建议将 SINGLE_STOCK_POSITION 从 {SINGLE_STOCK_POSITION} 提高到 {SINGLE_STOCK_POSITION+0.05}-{SINGLE_STOCK_POSITION+0.1}")
    else:
        suggestions.append(f"\n2. 最大回撤正常（{max_drawdown:.2f}%），保持当前配置即可")
    
    if use_annual:
        if annual_return < 10:
            suggestions.append(f"\n3. {annual_return_desc} < 10%，偏低：")
            if strategy_type == "打板策略":
                suggestions.append(f"   ├─ 建议将 STOP_PROFIT_RATE 从 {STOP_PROFIT_RATE} 提高到 {STOP_PROFIT_RATE+0.03}-{STOP_PROFIT_RATE+0.06}")
                suggestions.append(f"   └─ 建议将 MAX_HOLD_DAYS 从 {MAX_HOLD_DAYS} 提高到 {MAX_HOLD_DAYS+1}-{MAX_HOLD_DAYS+2}")
            elif strategy_type == "缩量潜伏策略":
                suggestions.append(f"   ├─ 建议将 STOP_PROFIT_RATE 从 {STOP_PROFIT_RATE} 提高到 {STOP_PROFIT_RATE+0.05}-{STOP_PROFIT_RATE+0.08}")
                suggestions.append(f"   └─ 建议将 MAX_HOLD_DAYS 从 {MAX_HOLD_DAYS} 提高到 {MAX_HOLD_DAYS+3}-{MAX_HOLD_DAYS+5}")
            elif strategy_type == "板块轮动策略":
                suggestions.append(f"   ├─ 建议将 STRATEGY_CONFIG['板块轮动策略']['rotate_days'] 从 {STRATEGY_CONFIG['板块轮动策略']['rotate_days']} 降低到 {STRATEGY_CONFIG['板块轮动策略']['rotate_days']-1}")
                suggestions.append(f"   └─ 建议将 STOP_PROFIT_RATE 从 {STOP_PROFIT_RATE} 提高到 {STOP_PROFIT_RATE+0.02}-{STOP_PROFIT_RATE+0.04}")
        elif annual_return > 50:
            suggestions.append(f"\n3. {annual_return_desc} > 50%，较高：")
            suggestions.append(f"   ├─ 建议将 STOP_PROFIT_RATE 从 {STOP_PROFIT_RATE} 降低到 {STOP_PROFIT_RATE-0.02}-{STOP_PROFIT_RATE-0.01}")
            suggestions.append(f"   └─ 建议将 SLIPPAGE_RATE 从 {SLIPPAGE_RATE} 提高到 {SLIPPAGE_RATE+0.003}-{SLIPPAGE_RATE+0.005}（增加滑点让回测更保守）")
        else:
            suggestions.append(f"\n3. {annual_return_desc}，保持当前配置即可")
    else:
        suggestions.append(f"\n3. {annual_return_desc}")
        if total_return < 5:
            suggestions.append(f"   累计收益率偏低，建议延长回测周期，或提高选股及格分")
        elif total_return > 20:
            suggestions.append(f"   累计收益率较高，建议增加滑点，让回测更贴近实盘")
        else:
            suggestions.append(f"   累计收益率正常，保持当前配置即可")
    
    return "\n".join(suggestions)

# ============================================== 【微信推送增强模块 - 完全保留】 ==============================================
def send_backtest_result_with_suggestion(backtest_result, optimize_suggestion):
    """推送回测结果 + 优化建议"""
    df_trade, df_capital = backtest_result
    if df_trade.empty or df_capital.empty:
        content = "【回测完成提醒】本次回测无任何交易记录，请检查数据抓取是否完整、选股条件是否过于严格"
        pro, utils = get_pro_api(load_config())
        utils.send_wechat_message(content)
        return
    
    total_trades = len(df_trade)
    win_trades = len(df_trade[df_trade["单笔盈亏"] > 0]) if total_trades > 0 else 0
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    final_capital = df_capital.iloc[-1]["capital"] if not df_capital.empty else INIT_CAPITAL
    total_profit = final_capital - INIT_CAPITAL
    total_return = (total_profit / INIT_CAPITAL) * 100 if INIT_CAPITAL > 0 else 0
    
    max_drawdown = 0
    if not df_capital.empty:
        df_capital["max_cash"] = df_capital["capital"].cummax()
        df_capital["drawdown"] = (df_capital["max_cash"] - df_capital["capital"]) / df_capital["max_cash"] * 100
        max_drawdown = df_capital["drawdown"].max() if not df_capital["drawdown"].empty else 0
    
    content = f"""【量化回测完成 + 参数优化建议】
📊 回测核心结果：
├─ 策略类型：{STRATEGY_TYPE}
├─ 回测时间：{START_DATE} 至 {END_DATE}
├─ 初始本金：{INIT_CAPITAL}元
├─ 期末资金：{final_capital:.2f}元
├─ 总收益率：{total_return:.2f}%
├─ 总交易次数：{total_trades}次
├─ 胜率：{win_rate:.2f}%
└─ 最大回撤：{max_drawdown:.2f}%
💡 参数优化建议（基于当前回测结果）：
{optimize_suggestion}
📁 结果文件已保存：
├─ 回测报告：一体化回测结果报告.xlsx
└─ 运行日志：logs/quant_info.log
"""
    pro, utils = get_pro_api(load_config())
    utils.send_wechat_message(content)

def send_stock_pick_result(stock_pick_result):
    """推送选股结果"""
    if stock_pick_result is None or stock_pick_result.empty:
        content = f"""【每日选股完成】
📅 日期：{datetime.now().strftime('%Y-%m-%d')}
📊 策略：{STRATEGY_TYPE}
❌ 结果：无符合条件的标的，请检查数据抓取是否完整、选股条件是否过于严格
"""
    else:
        top3 = stock_pick_result.head(3)
        top3_text = []
        for _, row in top3.iterrows():
            top3_text.append(f"├─ {row.get('股票代码', 'N/A')} {row.get('股票名称', 'N/A')} 评分：{row.get('23 维总评分', 0)}")
        
        content = f"""【每日选股完成】
📅 日期：{datetime.now().strftime('%Y-%m-%d')}
📊 策略：{STRATEGY_TYPE}
✅ 选股数量：{len(stock_pick_result)}只
🏆 Top 3 标的：
{chr(10).join(top3_text)}
📁 结果文件已保存：
└─ 选股清单：{datetime.now().strftime('%Y%m%d')}_{STRATEGY_TYPE}_选股结果清单.xlsx
"""
    pro, utils = get_pro_api(load_config())
    utils.send_wechat_message(content)

# ============================================== 【本地数据完整性校验 - 完全保留】 ==============================================
def validate_local_data():
    """校验本地数据完整性（支持 CSV 和 Parquet 格式）"""
    logger.info("开始校验本地数据完整性...")
    required_global_files = ['stock_basic.csv']
    for file in required_global_files:
        file_path = os.path.join(OUTPUT_DIR, file)
        if not os.path.exists(file_path):
            logger.error(f"❌ 本地数据校验失败：缺少全局文件 {file}")
            return False
    
    if not os.path.exists(STOCKS_DIR):
        logger.error(f"❌ 本地数据校验失败：缺少个股数据目录 {STOCKS_DIR}")
        return False
    
    stock_dirs = [d for d in os.listdir(STOCKS_DIR) if os.path.isdir(os.path.join(STOCKS_DIR, d))]
    if len(stock_dirs) < 5:
        logger.error(f"❌ 本地数据校验失败：个股数据不足（仅{len(stock_dirs)}只，建议至少 5 只）")
        return False
    
    sample_stocks = stock_dirs[:5]
    for stock_code in sample_stocks:
        # ✅ 支持 CSV 和 Parquet 两种格式
        daily_csv = os.path.join(STOCKS_DIR, stock_code, 'daily.csv')
        daily_parquet = os.path.join(STOCKS_DIR, stock_code, 'daily.parquet')
        
        csv_valid = os.path.exists(daily_csv) and os.path.getsize(daily_csv) >= 1024
        parquet_valid = os.path.exists(daily_parquet) and os.path.getsize(daily_parquet) >= 1024
        
        if not csv_valid and not parquet_valid:
            logger.error(f"❌ 本地数据校验失败：个股 {stock_code} 缺少有效 daily.csv 或 daily.parquet")
            return False
    
    logger.info("✅ 本地数据完整性校验通过")
    return True

# ============================================== 【Flask 服务等待工具 - 完全保留】 ==============================================
def wait_for_api_ready(timeout=15):
    """等待 Flask API 服务启动完成"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not get_app_running():
            return False
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                logger.info("✅ Flask API 服务已就绪")
                return True
        except:
            pass
        time.sleep(0.5)
    logger.error("❌ Flask API 服务启动超时，无法继续执行")
    return False

# ============================================== 【模式执行入口 - 全量修复】 ==============================================
def run_by_mode():
    """根据运行模式执行对应逻辑"""
    global FETCH_TYPE, START_DATE, END_DATE, START_DATE_API, END_DATE_API, EXTEND_FETCH_CONFIG
    logger.info(f"当前运行模式：{AUTO_RUN_MODE}，策略类型：{STRATEGY_TYPE}")
    pro, utils = get_pro_api(load_config())
    
    # 【修复】4 种模式直接执行，无需映射
    effective_mode = AUTO_RUN_MODE
    logger.info(f"运行模式：{effective_mode}")
    
    # ==================== 【模式 1：全量抓取】 ====================
    if effective_mode == "全量抓取":
        logger.info("✅ 启动【全量抓取模式】，从 2020-01-01 抓取至今的全部历史数据")
        utils.send_wechat_message(f"【全量抓取启动】已启动全量抓取模式，策略：{STRATEGY_TYPE}，开始抓取数据")
        if is_port_in_use(SERVER_PORT):
            logger.error(f"❌ 端口{SERVER_PORT}已被占用，请更换端口或关闭占用程序")
            return
        
        server_thread = Thread(target=lambda: flask_app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False), daemon=True)
        server_thread.start()
        
        if not wait_for_api_ready():
            return
        
        FETCH_TYPE = "full"
        logger.info("开始提交全量数据抓取任务...")
        task_id = str(uuid.uuid4())
        TASK_QUEUE.put({
            'id': task_id,
            'config': load_config(),
            'fetch_type': 'full'
        })
        with TASK_STATUS_LOCK:
            TASK_STATUS[task_id] = {'status': 'queued', 'progress': 0, 'message': '任务已排队', 'logs': []}
        
        logger.info(f"数据抓取任务已提交，任务 ID：{task_id}")
        print(f"全量数据抓取中...请稍候（任务 ID：{task_id}），请勿关闭程序！")
        print("="*80)
        
        while True:
            if not get_app_running():
                break
            with TASK_STATUS_LOCK:
                status = TASK_STATUS.get(task_id, {})
            if status.get('status') == 'completed':
                logger.info(f"✅ 数据抓取完成！{status.get('message', '')}")
                break
            elif status.get('status') == 'failed':
                error_msg = f"数据抓取失败：{status.get('message', '未知错误')}"
                logger.error(error_msg)
                utils.send_wechat_message(f"【全量抓取失败】{error_msg}")
                return
            else:
                progress = status.get('progress', 0)
                message = status.get('message', '处理中...')
                print(f"\r抓取进度：{progress}% | 状态：{message}", end='', flush=True)
            time.sleep(2)
        
        print("\n" + "="*80)
        logger.info("🎉 【全量抓取模式】执行完成！所有数据已保存至本地目录")
        print("="*80)
        print("全量抓取完成！结果文件：")
        print(f"1. 抓取/运行日志：logs/quant_info.log")
        print(f"2. 本地数据存储：data/ & data_all_stocks/")
        print(f"3. 失败股票清单：data/failed_stocks.json（可下次自动补抓）")
        print("="*80)
        return
    
    # ==================== 【模式 2：增量抓取】 ====================
    elif effective_mode == "增量抓取":
        logger.info("✅ 启动【增量抓取模式】，仅抓取最新交易日数据")
        utils.send_wechat_message(f"【增量抓取启动】已启动增量抓取模式，策略：{STRATEGY_TYPE}，开始抓取数据")
        if is_port_in_use(SERVER_PORT):
            logger.error(f"❌ 端口{SERVER_PORT}已被占用，请更换端口或关闭占用程序")
            return
        
        server_thread = Thread(target=lambda: flask_app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False), daemon=True)
        server_thread.start()
        
        if not wait_for_api_ready():
            return
        
        FETCH_TYPE = "latest"
        
        # 【增量抓取优化】自动获取上一个有效交易日
        try:
            today_api = datetime.now().strftime("%Y%m%d")
            start_api = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            cal_df = pro.trade_cal(exchange="", start_date=start_api, end_date=today_api)
            if cal_df is not None and not cal_df.empty:
                open_dates = cal_df[cal_df["is_open"] == 1]["cal_date"].tolist()
                today_str = datetime.now().strftime("%Y%m%d")
                prev_dates = [d for d in open_dates if d < today_str]
                if prev_dates:
                    prev_date_api = max(prev_dates)
                    prev_trade_date = datetime.strptime(prev_date_api, "%Y%m%d")
                else:
                    prev_trade_date = datetime.now() - timedelta(days=1)
            else:
                prev_trade_date = datetime.now() - timedelta(days=1)
        except Exception as e:
            logger.warning(f"获取交易日历失败，使用昨天：{e}")
            prev_trade_date = datetime.now() - timedelta(days=1)
        START_DATE = "2026-03-17"  # 临时指定
        END_DATE = "2026-03-18"  # 临时指定
        START_DATE_API = "20260317"  # 临时指定
        END_DATE_API = "20260318"  # 临时指定
        logger.info(f"📅 增量抓取日期范围：{START_DATE} ~ {END_DATE}")
        
        logger.info("开始提交增量数据抓取任务...")
        task_id = str(uuid.uuid4())
        # 【增量抓取优化】关闭季度数据接口（财务三表等）
        EXTEND_FETCH_CONFIG["enable_finance_sheet"] = False  # 财务三表
        EXTEND_FETCH_CONFIG["enable_hk_hold"] = False        # 港股持仓
        logger.info("📅 增量模式：已关闭财务报表等季度数据接口")
        TASK_QUEUE.put({
            'id': task_id,
            'config': load_config(),
            'fetch_type': 'latest'
        })
        with TASK_STATUS_LOCK:
            TASK_STATUS[task_id] = {'status': 'queued', 'progress': 0, 'message': '任务已排队', 'logs': []}
        
        logger.info(f"增量抓取任务已提交，任务 ID：{task_id}")
        print(f"增量数据抓取中...请稍候（任务 ID：{task_id}），请勿关闭程序！")
        print("="*80)
        
        while True:
            if not get_app_running():
                break
            with TASK_STATUS_LOCK:
                status = TASK_STATUS.get(task_id, {})
            if status.get('status') == 'completed':
                logger.info(f"✅ 增量数据抓取完成！{status.get('message', '')}")
                break
            elif status.get('status') == 'failed':
                error_msg = f"增量数据抓取失败：{status.get('message', '未知错误')}"
                logger.error(error_msg)
                utils.send_wechat_message(f"【增量抓取失败】{error_msg}")
                return
            else:
                progress = status.get('progress', 0)
                message = status.get('message', '处理中...')
                print(f"\r抓取进度：{progress}% | 状态：{message}", end='', flush=True)
            time.sleep(1)
        
        print("\n" + "="*80)
        logger.info("🎉 【增量抓取模式】执行完成！所有数据已保存至本地目录")
        print("="*80)
        print("增量抓取完成！结果文件：")
        print(f"1. 抓取/运行日志：logs/quant_info.log")
        print(f"2. 最新数据存储：data/ & data_all_stocks/")
        print("="*80)
        return
    
    # ==================== 【模式 3：仅回测】 ====================
    elif effective_mode == "仅回测":
        logger.info("✅ 启动【仅回测模式】，使用本地已缓存的数据执行回测")
        utils.send_wechat_message(f"【回测启动】已启动仅回测模式，策略：{STRATEGY_TYPE}")
        if not validate_local_data():
            error_msg = "仅回测模式失败：本地数据目录为空或数据不足，请先执行「全量抓取」模式获取数据"
            logger.error(error_msg)
            utils.send_wechat_message(f"【仅回测失败】{error_msg}")
            return
        
        if is_port_in_use(SERVER_PORT):
            logger.error(f"❌ 端口{SERVER_PORT}已被占用，请更换端口或关闭占用程序")
            return
        
        server_thread = Thread(target=lambda: flask_app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False), daemon=True)
        server_thread.start()
        
        if not wait_for_api_ready():
            return
        
        backtest_sys = BacktestSystem(API_BASE_URL)
        df_total = backtest_sys.get_cached_data()
        backtest_result = backtest_sys.run(df_total)
        
        optimize_suggestion = generate_param_optimize_suggestion(backtest_result)
        send_backtest_result_with_suggestion(backtest_result, optimize_suggestion)
        
        logger.info("🎉 【仅回测模式】执行完成！所有报告已导出至本地目录")
        print("="*80)
        print("回测完成！结果文件：")
        print(f"1. 回测报告：一体化回测结果报告.xlsx")
        if VISUALIZATION:
            print(f"2. 可视化图表：charts/回测报告_{datetime.now().strftime('%Y%m%d')}.png")
        print(f"3. 运行日志：logs/quant_info.log")
        print("="*80)
        return
    
    # ==================== 【模式 4：每日选股】 ====================
    elif effective_mode == "每日选股":
        logger.info("✅ 启动【每日选股模式】，抓取最新交易日数据并执行实盘选股")
        utils.send_wechat_message(f"【每日选股启动】已启动每日选股模式，策略：{STRATEGY_TYPE}")
        if not utils.is_trade_day():
            logger.info("今日是非交易日，不执行选股")
            utils.send_wechat_message(f"【每日选股跳过】今日（{datetime.now().strftime('%Y-%m-%d')}）是非交易日，不执行选股")
            return
        
        now = datetime.now()
        if now.hour < 17 or (now.hour == 17 and now.minute < 30):
            logger.warning("当前时间过早，龙虎榜/涨跌停数据可能未更新，建议 17:30 后再试")
            utils.send_wechat_message(f"【每日选股提醒】当前时间（{now.strftime('%H:%M')}）过早，数据可能未更新，建议 17:30 后再试")
        
        if is_port_in_use(SERVER_PORT):
            logger.error(f"❌ 端口{SERVER_PORT}已被占用，请更换端口或关闭占用程序")
            return
        
        server_thread = Thread(target=lambda: flask_app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False), daemon=True)
        server_thread.start()
        
        if not wait_for_api_ready():
            return
        
        FETCH_TYPE = "latest"
        
        # 【每日选股优化】自动获取交易日 + 关闭季度接口
        try:
            today_api = datetime.now().strftime("%Y%m%d")
            start_api = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            cal_df = pro.trade_cal(exchange="", start_date=start_api, end_date=today_api)
            if cal_df is not None and not cal_df.empty:
                open_dates = cal_df[cal_df["is_open"] == 1]["cal_date"].tolist()
                today_str = datetime.now().strftime("%Y%m%d")
                prev_dates = [d for d in open_dates if d <= today_str]
                if prev_dates:
                    prev_date_api = max(prev_dates)
                    prev_trade_date = datetime.strptime(prev_date_api, "%Y%m%d")
                else:
                    prev_trade_date = datetime.now() - timedelta(days=1)
            else:
                prev_trade_date = datetime.now() - timedelta(days=1)
        except Exception as e:
            logger.warning(f"获取交易日历失败：{e}")
            prev_trade_date = datetime.now() - timedelta(days=1)
        START_DATE = "2026-03-17"  # 临时指定
        END_DATE = START_DATE
        START_DATE_API = "20260317"  # 临时指定
        END_DATE_API = "20260318"  # 临时指定
        logger.info(f"📅 每日选股：交易日 {START_DATE}")
        
        # 关闭季度数据接口
        EXTEND_FETCH_CONFIG["enable_finance_sheet"] = False
        EXTEND_FETCH_CONFIG["enable_hk_hold"] = False
        logger.info("📅 每日选股模式：已关闭财务报表等季度数据接口")
        
        logger.info("开始提交增量数据抓取任务...")
        task_id = str(uuid.uuid4())
        TASK_QUEUE.put({
            'id': task_id,
            'config': load_config(),
            'fetch_type': 'latest'
        })
        with TASK_STATUS_LOCK:
            TASK_STATUS[task_id] = {'status': 'queued', 'progress': 0, 'message': '任务已排队', 'logs': []}
        
        logger.info(f"增量抓取任务已提交，任务 ID：{task_id}")
        print(f"增量数据抓取中...请稍候（任务 ID：{task_id}），请勿关闭程序！")
        print("="*80)
        
        while True:
            if not get_app_running():
                break
            with TASK_STATUS_LOCK:
                status = TASK_STATUS.get(task_id, {})
            if status.get('status') == 'completed':
                logger.info(f"✅ 增量数据抓取完成！{status.get('message', '')}")
                break
            elif status.get('status') == 'failed':
                error_msg = f"增量数据抓取失败：{status.get('message', '未知错误')}"
                logger.error(error_msg)
                utils.send_wechat_message(f"【每日选股失败】{error_msg}")
                return
            else:
                progress = status.get('progress', 0)
                message = status.get('message', '处理中...')
                print(f"\r抓取进度：{progress}% | 状态：{message}", end='', flush=True)
            time.sleep(1)
        
        print("\n" + "="*80)
        logger.info("增量抓取完成，开始执行每日选股...")
        
        stock_picker = DailyStockPicker(API_BASE_URL)
        df_latest, trade_date = stock_picker.get_latest_data()
        stock_pick_result = stock_picker.pick_stocks(df_latest, trade_date)
        
        send_stock_pick_result(stock_pick_result)
        
        logger.info("🎉 【每日选股模式】全流程执行完成！选股结果已导出")
        print("="*80)
        print("每日选股完成！结果文件：")
        print(f"1. 选股清单：{trade_date.strftime('%Y%m%d') if trade_date else 'unknown'}_{STRATEGY_TYPE}_选股结果清单.xlsx")
        print(f"2. 运行日志：logs/quant_info.log")
        print(f"3. 最新数据存储：data/ & data_all_stocks/")
        print("="*80)
        return
    
    else:
        logger.error(f"❌ 无效的运行模式：{AUTO_RUN_MODE}，仅支持：全量抓取/增量抓取/仅回测/每日选股")
        utils.send_wechat_message(f"【运行模式错误】配置的 AUTO_RUN_MODE={AUTO_RUN_MODE}，仅支持「全量抓取/增量抓取/仅回测/每日选股」")
        return

# ============================================== 【主程序入口 - 全量修复】 ==============================================
def main():
    """主程序入口函数，统一管理全局变量声明"""
    global GLOBAL_EXECUTOR
    
    # 【阶段 1.2：进程锁机制】确保只有一个抓取进程运行
    process_lock = ProcessLock(lock_file='/tmp/fetch_data.lock')
    if not process_lock.acquire():
        print("="*80)
        print("❌ 无法启动：已有其他抓取进程在运行")
        print("   如果确认没有进程运行，请手动删除锁文件：/tmp/fetch_data.lock")
        print("="*80)
        sys.exit(1)
    
    try:
        print("="*80)
        print("  📊 量化系统 - 全功能数据抓取 + 策略回测 + 实时选股平台")
        print("="*80)
        print(f"当前运行模式：{AUTO_RUN_MODE} | 当前策略：{STRATEGY_TYPE}")
        print(f"服务地址：http://localhost:{SERVER_PORT} | 扩展数据抓取：{FETCH_EXTEND_DATA}")
        print(f"可视化输出：{VISUALIZATION} | 日志级别：{LOG_LEVEL}")
        print(f"并发线程数：{FETCH_OPTIMIZATION['max_workers']}（可调整） | 每分钟最大请求数：{FETCH_OPTIMIZATION['max_requests_per_minute']}")
        print(f"多资讯源抓取：{EXTEND_FETCH_CONFIG.get('enable_multi_news', False)} | 资讯源列表：{EXTEND_FETCH_CONFIG.get('news_source_list', [])}")
        print(f"Parquet 存储：{'✅ 已启用' if PARQUET_AVAILABLE else '⚠️  未启用（pyarrow 未安装）'}")
        print("="*80)
        fetch_thread = Thread(target=fetch_worker, daemon=True)
        fetch_thread.start()
        
        run_by_mode()
        
        logger.info("✅ 主程序执行完成，正在清理资源...")
        set_app_running(False)
        
        # 锁内只做读写和操作，不做 global 声明
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    logger.info("✅ 线程池已关闭")
                    GLOBAL_EXECUTOR = None  # 关闭后置空，避免重复关闭
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        # 【阶段 1.2：进程锁机制】释放进程锁
        process_lock.release()
        
        gc.collect()
        logger.info("✅ 所有资源已清理，程序退出")
    
    except KeyboardInterrupt:
        logger.info("🛑 程序被用户手动终止（Ctrl+C）")
        print("\n" + "="*80)
        print("程序已手动停止，感谢使用！")
        print("="*80)
        set_app_running(False)
        
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    GLOBAL_EXECUTOR = None
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        # 【阶段 1.2：进程锁机制】释放进程锁
        process_lock.release()
        
        gc.collect()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 程序运行异常：{str(e)}", exc_info=True)
        print("="*80)
        print(f"程序运行出错：{str(e)}")
        print(f"请查看日志文件排查问题：logs/quant_error.log")
        print("="*80)
        
        set_app_running(False)
        
        with EXECUTOR_LOCK:
            if GLOBAL_EXECUTOR is not None:
                try:
                    GLOBAL_EXECUTOR.shutdown(wait=False)
                    GLOBAL_EXECUTOR = None
                except Exception as e:
                    logger.warning(f"线程池关闭异常：{e}")
        
        # 【阶段 1.2：进程锁机制】释放进程锁
        process_lock.release()
        
        gc.collect()
        sys.exit(1)

    finally:
        # 【阶段 1.2：进程锁机制】确保锁最终被释放（兜底）
        try:
            process_lock.release()
        except:
            pass

if __name__ == '__main__':
    main()
