# ==============================================
# 【优化】配置管理模块 - config_manager.py
# ==============================================
# 功能：统一管理所有配置参数、配置加载/保存、配置校验
# 职责：配置集中化、配置校验、配置缓存
# ==============================================

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from threading import RLock

logger = logging.getLogger("quant_system")

# ============================================ 【1. 核心运行配置 - 最常用，每次运行必看】 ============================================
# --------------------------- 1.1 运行模式选择 ---------------------------
# 【使用场景】
#   - "每日选股"：仅执行当日选股，输出股票池（实盘/模拟盘用）
#   - "抓取 + 回测"：全量历史数据抓取 + 完整回测（策略研发阶段用）
#   - "仅服务"：仅启动 API 服务，不执行任何任务（部署到服务器用）
#   - "仅回测"：使用已抓取的历史数据进行回测（验证策略用）
AUTO_RUN_MODE = "每日选股"  # 【可选模式】："抓取 + 回测" / "仅服务" / "仅回测" / "每日选股"

# --------------------------- 1.2 策略类型选择 ---------------------------
# 【使用场景】
#   - "打板策略"：追涨停板，适合强势股，持仓 1-2 天，高风险高收益
#   - "缩量潜伏策略"：首板后缩量回调买入，适合稳健型，持仓 3-8 天
#   - "板块轮动策略"：跟随主线行业轮动，适合中线，持仓 3-5 天
STRATEGY_TYPE = "打板策略"  # 【可选策略】："打板策略" / "缩量潜伏策略" / "板块轮动策略"

# --------------------------- 1.3 板块筛选配置 ---------------------------
# 【使用场景】
#   - "主板"：沪深主板，稳定性高，适合大资金
#   - "创业板"：高波动，适合激进策略
#   - "科创板"：高科技企业，门槛高（50 万），波动大
#   - "北交所"：中小企业，流动性较差
ALLOWED_MARKET = ["主板"]  # 【可选板块】："主板", "创业板", "科创板", "北交所"

# ============================================ 【2. 时间配置 - 抓取/回测/选股通用】 ============================================
# 【使用场景】
#   - START_DATE：历史数据抓取的起始日期，回测周期起点
#   - END_DATE：历史数据抓取的结束日期，回测周期终点
#   - 格式必须为 YYYY-MM-DD，API 调用时会自动转换为 YYYYMMDD
START_DATE = "2018-03-01"  # 全量回测/抓取的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-02-28"    # 全量回测/抓取的结束日期（格式：YYYY-MM-DD）

# ============================================ 【3. 消息推送配置】 ============================================
# 【使用场景】
#   - WECHAT_ROBOT_ENABLED：是否启用企业微信机器人推送（True=启用，False=禁用）
#   - WECHAT_ROBOT_URL：企业微信机器人 Webhook URL，用于发送选股结果、回测报告
#   - 适用场景：每日选股完成后自动推送结果到微信群，回测完成后推送报告
WECHAT_ROBOT_ENABLED = True
WECHAT_ROBOT_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4f8c1eb8-1240-4fde-933f-a783e99b90dd"

# ============================================ 【4. 交易核心参数 - 回测/选股通用】 ============================================
# 【使用场景说明】以下参数直接影响回测结果和实盘表现，修改需谨慎，必须经过回测验证

INIT_CAPITAL = 5000              # 【初始本金】单位：元，回测起始资金（实盘参考：建议≥5 万）
MAX_HOLD_DAYS = 3                 # 【最长持股天数】单位：天，超过强制卖出（打板策略 1-2 天，潜伏策略 5-8 天）
STOP_LOSS_RATE = 0.06             # 【基础止损比例】默认 6%，亏损超过此比例止损（打板 6%，潜伏 3%，轮动 5%）
STOP_PROFIT_RATE = 0.12           # 【基础止盈比例】默认 12%，盈利超过此比例止盈（打板 12%，潜伏 15%，轮动 10%）
COMMISSION_RATE = 0.00025         # 【佣金比例】万 2.5（0.025%），券商收取，买卖双向收取（可和券商协商降低）
MIN_COMMISSION = 5                 # 【最低佣金】5 元/笔，不足 5 元按 5 元收（A 股实盘规则，小资金需注意）
STAMP_TAX_RATE = 0.001            # 【印花税】卖出千 1（0.1%），仅卖出收取，买入不收（国家政策，2023 年 8 月减半）
SINGLE_STOCK_POSITION = 0.2        # 【单只股票最大仓位】20%，即最多用 20% 的钱买一只股票（分散风险，避免单只暴雷）
INDUSTRY_POSITION = 0.3            # 【单行业最大仓位】30%，避免单一行业风险（防止行业政策突变导致大幅回撤）
MAX_HOLD_STOCKS = 5                # 【最大持仓股票数】5 只，分散风险（资金量小可减少，资金量大可增加）
MAX_DRAWDOWN_STOP = 0.15           # 【账户最大回撤止损】≥15% 强制清仓空仓休息（保护本金，避免连续亏损）
DRAWDOWN_STOP_DAYS = 3             # 【清仓后空仓休息天数】3 天，冷静期（避免情绪化交易，等待市场企稳）
MAX_TRADE_RATIO = 0.05             # 【单次买入占成交量比例】≤5%，避免冲击成本（A 股合规要求，防止操纵股价）
PRICE_ADJUST = "front"              # 【复权类型】front(前复权)/back(后复权)/none(不复权)，回测建议用前复权（保持价格连续性）
SLIPPAGE_RATE = 0.005               # 【实盘滑点】单边 0.5%，买入多花 0.5%，卖出少卖 0.5%（模拟实盘交易摩擦）

# ============================================ 【5. 前置筛选配置 - 全量修复配置关联】 ============================================
# 【使用场景】用于数据抓取前的初步筛选，排除不符合基本条件的股票，提高数据质量
FILTER_CONFIG = {
    "min_amount": 300000,        # 【最低成交额】千元，300000 千元=30 亿元，保证流动性（避免小成交额股票无法买入/卖出）
    "min_turnover": 3,           # 【最低换手率】%，3% 以上保证股性活跃（换手率过低说明关注度低，难以获利）
    "exclude_st": True,           # 【排除 ST 股票】True=排除 ST/*ST/退市整理股票（避免踩雷，ST 股票有退市风险）
    "exclude_suspend": True,      # 【排除停牌股票】True=排除停牌股票（避免资金占用，停牌期间无法交易）
    "max_fetch_retry": 3,         # 【单只股票最大抓取重试次数】3 次，超过标记为永久失败（网络波动时自动重试）
    "permanent_failed_expire": 30,  # 【永久失败过期天数】30 天后自动清除，允许重新抓取（定期清理失败记录）
    "smart_retry_enabled": True,        # 【优化 D2】【智能重试开关】True=开启智能重试（优质标的失败后自动重试）
    "smart_retry_days": 7,              # 【优质标的重试间隔】7 天，避免频繁重试（给市场时间消化利空）
    "fundamental_check": True           # 【重试前基本面检查】True=重试前检查基本面是否恶化（避免垃圾股反复重试）
}

# ============================================ 【6. 评分规则 - 选股 + 回测通用】 ============================================
# 【使用场景】根据市场状态动态调整因子权重，牛市放大进攻因子，熊市放大防守因子
MARKET_CONDITION = "normal"  # 【市场状态】bull(牛市)/bear(熊市)/normal(震荡市)，用于动态权重调整

# 【动态权重乘数配置】
# 【使用场景】
#   - bull：牛市环境，放大进攻因子权重（如连板高度、封单金额）
#   - bear：熊市环境，放大防守因子权重（如无减持、无问询、市值适中）
#   - normal：正常市场，使用标准权重
DYNAMIC_WEIGHT_MULTIPLIER = {
    "bull": 1.2,    # 【牛市乘数】放大进攻因子权重 20%
    "bear": 0.8,    # 【熊市乘数】放大防守因子权重（实际是缩小进攻因子）
    "normal": 1.0   # 【正常市场】标准权重
}

# 【核心评分配置】
# 【使用场景】
#   - pass_score：及格分数线，低于此分数的股票直接淘汰
#   - enable_dynamic_weight：是否启用动态权重（根据市场状态调整）
#   - strategy_pass_score：各策略专属及格线（打板要求最高，潜伏次之，轮动再次）
#   - items：评分项列表，每项包含 [基础分，筛选条件，各策略权重]
CORE_CONFIG = {
    "pass_score": 12,  # 【基础及格分】低于此分直接淘汰
    "enable_dynamic_weight": True,  # 【优化 S2】【动态权重使能】True=根据市场状态调整权重
    "strategy_pass_score": {
        "打板策略": 18,      # 【打板策略及格分】18 分（要求最高，因为风险最大）
        "缩量潜伏策略": 12,  # 【潜伏策略及格分】12 分（中等要求）
        "板块轮动策略": 17   # 【轮动策略及格分】17 分（较高要求，需要精准判断主线）
    },
    "items": {
        # 【缩量潜伏策略核心高分项】
        # 【使用场景】识别首板后缩量回调的优质标的，是潜伏策略的核心评分项
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
        # 原有打板策略核心项（保留不变）
        # 【使用场景】识别强势连板股，是打板策略的核心评分项
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
# 【使用场景】各策略的特定筛选参数，与策略逻辑强相关，修改需理解策略原理

STRATEGY_CONFIG = {
    # 【打板策略配置】
    # 【使用场景】追涨停板策略，核心是识别强势连板股
    "打板策略": {
        "type": "link",  # 【策略类型】连板策略
        "min_order_ratio": 0.03,  # 【最小封单比】封单金额/流通市值≥3%（封板强度指标）
        "max_break_times": 1,  # 【最大炸板次数】≤1 次（炸板过多说明资金分歧大）
        "link_board_range": [2, 4],  # 【连板高度范围】2-4 板（太低不够强势，太高风险大）
        "exclude_late_board": True,  # 【排除尾盘封板】True=排除 14:40 后封板的（尾盘板质量差）
        "stop_loss_rate": 0.06,  # 【策略专属止损】6%（打板失败立即止损）
        "stop_profit_rate": 0.12,  # 【策略专属止盈】12%（快速获利了结）
        "max_hold_days": 2  # 【最大持股天数】2 天（打板策略快进快出）
    },
    # 【缩量潜伏策略配置】
    # 【使用场景】首板后缩量回调策略，核心是识别洗盘结束的信号
    "缩量潜伏策略": {
        "type": "first_board_pullback",  # 【策略类型】首板回调
        "first_board_limit": True,  # 【必须首板】True=必须是阶段首板（排除连续涨停）
        "board_volume_growth": 1.5,  # 【首板放量要求】≥1.5 倍（首板必须放量，说明资金进场）
        "shrink_volume_ratio": [1/3, 1/2],  # 【缩量比例范围】1/3~1/2（缩量太多说明没人玩，太少说明洗盘不充分）
        "shrink_days_range": [3, 10],  # 【回调天数范围】3-10 天（太短洗盘不充分，太长资金已撤退）
        "pullback_support_level": 0.5,  # 【支撑位比例】0.5=首板实体中点（黄金分割位）
        "support_tolerance": 0.02,  # 【支撑位容错】±2%（允许小幅跌破支撑位）
        "stop_loss_rate": 0.03,  # 【策略专属止损】3%（潜伏失败小亏离场）
        "stop_profit_rate": 0.15,  # 【策略专属止盈】15%（潜伏成功大赚）
        "max_hold_days": 8,  # 【最大持股天数】8 天（给足时间等待拉升）
        "rotate_days": 1  # 【轮动周期】1 天（每天都可以调仓）
    },
    # 【板块轮动策略配置】
    # 【使用场景】跟随主线行业轮动，核心是识别资金流向
    "板块轮动策略": {
        "type": "industry",  # 【策略类型】行业轮动
        "rotate_days": 3,  # 【轮动周期】3 天（每 3 天调仓一次，跟随行业轮动）
        "stop_loss_rate": 0.05,  # 【策略专属止损】5%（中等止损）
        "stop_profit_rate": 0.1,  # 【策略专属止盈】10%（中等止盈）
        "main_trend": True,  # 【只做主线】True=只做主线行业（排除边缘行业）
        "fund_inflow_top": 30,  # 【资金流入排名】前 30 名（只选资金大幅流入的行业）
        "max_hold_days": 3  # 【最大持股天数】3 天（短线轮动）
    }
}

# ============================================ 【8. 今日选股专属配置】 ============================================
# 【使用场景】每日选股任务的输出控制参数
STOCK_PICK_CONFIG = {
    "min_pick_score": 16,  # 【最低选股分数】≥16 分才输出（保证质量）
    "max_output_count": 10,  # 【最多输出数量】10 只（避免过多，便于人工筛选）
    "only_main_board": True,  # 【仅主板】True=只输出主板股票（排除创业板/科创板）
    "export_excel": True,  # 【导出 Excel】True=导出选股结果到 Excel 文件
    "export_score_detail": True,  # 【导出评分明细】True=Excel 中包含每项得分详情
    "fetch_days": 1  # 【抓取天数】1 天（仅抓取当日数据）
}

# ============================================ 【9. 后端核心配置 - 一般不用改】 ============================================
# 【使用场景】系统后端服务配置，除非部署环境变化，否则不需要修改
SERVER_HOST = "0.0.0.0"  # 【服务监听地址】0.0.0.0=允许外部访问（本地用 127.0.0.1）
SERVER_PORT = 5001  # 【服务端口】5001（避免和常见端口冲突）
API_BASE_URL = f"http://localhost:{SERVER_PORT}/api"  # 【API 基础 URL】内部调用用
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"  # 【Tushare Token】API 认证凭证（注意保密）
TUSHARE_API_URL = "http://42.194.163.97:5000"  # 【Tushare API 地址】私有部署地址
FETCH_EXTEND_DATA = True  # 【抓取扩展数据】True=抓取龙虎榜/财务/舆情等扩展数据
VISUALIZATION = False  # 【可视化开关】True=生成 K 线图等可视化图表（调试用）
LOG_LEVEL = "INFO"  # 【日志级别】INFO/WARNING/ERROR/DEBUG（调试用 DEBUG）

# ============================================ 【10. 抓取性能优化配置】 ============================================
# 【优化】如何根据 Tushare 积分调整线程数和限流参数：
#   - 积分 < 1000：max_workers=2-5, max_requests_per_minute=100-300（低频接口权限）
#   - 积分 1000-5000：max_workers=5-10, max_requests_per_minute=300-1000（中频接口权限）
#   - 积分 5000-10000：max_workers=10-15, max_requests_per_minute=1000-2000（高频接口权限）
#   - 积分 > 10000：max_workers=15-20, max_requests_per_minute=2000-5000（超高权限，可拉满）
# 【注意】max_requests_per_minute 上限受限于 Tushare 积分等级，超出会导致接口调用失败
FETCH_OPTIMIZATION = {
    'max_workers': 20,                          # 【优化】【并发线程数】根据你的积分调整（10000 分建议 15-20）
    'batch_io_interval': 10,                    # 【优化】【批量 IO 间隔】秒，避免磁盘 IO 瓶颈（写入太频繁会拖慢系统）
    'max_requests_per_minute': 2500             # 【优化】【每分钟最大请求数】用户要求 2500 次/分钟（10000 分高积分）
}

# ============================================ 【11. 扩展数据抓取开关】 ============================================
# 【使用场景】控制是否抓取扩展数据，扩展数据用于增强评分和策略判断
EXTEND_FETCH_CONFIG = {
    "enable_top_list": True,  # 【龙虎榜数据】True=抓取龙虎榜（机构/游资动向）
    "enable_top_inst": True,  # 【机构席位数据】True=抓取机构买卖明细
    "enable_finance_sheet": True,  # 【财务数据】True=抓取财务报表（基本面分析用）
    "enable_hk_hold": True,  # 【港资持股】True=抓取港资持仓变化（北向资金动向）
    "enable_cyq": True,  # 【筹码分布】True=抓取筹码分布数据（成本分析用）
    "enable_block_trade": True,  # 【大宗交易】True=抓取大宗交易数据（主力动向）
    "enable_index_weight": True,  # 【指数权重】True=抓取指数成分股权重
    "enable_kpl_concept": True,  # 【板块概念】True=抓取板块概念数据
    "enable_stk_limit": True,  # 【涨跌停统计】True=抓取涨跌停家数统计
    "enable_multi_news": True,  # 【舆情数据】True=抓取多源新闻舆情
    "news_source_list": [  # 【新闻源列表】按优先级排序
        "sina", "cls", "yicai", "eastmoney", "xueqiu",
        "10jqka", "ifeng", "jrj", "yuncaijing", "wallstreetcn"
    ]
}

# ============================================ 【配置管理核心类】 ============================================

class ConfigManager:
    """
    【优化】配置管理器 - 单例模式
    
    核心职责：
    - 配置加载：从配置文件或默认值加载配置
    - 配置保存：将修改后的配置保存到文件
    - 配置校验：检查配置参数的合法性
    - 配置缓存：使用缓存避免重复加载
    
    使用场景：
    - 系统启动时自动加载配置
    - 修改配置后保存
    - 运行前校验配置是否合法
    - 获取配置用于其他模块
    
    线程安全：
    - 使用 RLock 保证多线程安全
    - 单例模式保证全局唯一实例
    """
    
    _instance = None
    _lock = RLock()
    
    def __new__(cls):
        """
        【优化】单例模式实现，保证全局唯一实例
        
        使用双重检查锁定（Double-Checked Locking）：
        1. 第一次检查：无锁状态下检查实例是否存在（避免不必要的锁竞争）
        2. 加锁：如果实例不存在，获取锁
        3. 第二次检查：锁内再次检查实例是否存在（避免重复创建）
        4. 创建实例：如果仍不存在，创建新实例
        
        Returns:
            ConfigManager: 全局唯一的配置管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        【优化】初始化配置管理器
        
        初始化内容：
        - 配置缓存：用于存储已加载的配置
        - 配置锁：保护缓存的线程安全
        - 基础目录：计算配置文件的存储路径
        - 配置文件路径：config.json 的完整路径
        
        注意：
        - 使用 _initialized 标志避免重复初始化
        - 单例模式下 __init__ 可能被多次调用
        """
        if self._initialized:
            return
        self._initialized = True
        self._config_cache: Optional[Dict[str, Any]] = None
        self._config_lock = RLock()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(self.base_dir, 'config.json')
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        【优化】获取所有配置（只读副本）
        
        功能说明：
        - 返回所有配置项的字典副本
        - 包含所有模块配置（运行/交易/筛选/评分/后端等）
        - 返回副本避免外部修改影响全局配置
        
        Returns:
            Dict[str, Any]: 包含所有配置项的字典
            
        使用场景：
        - 其他模块需要读取多个配置项时
        - 导出配置用于备份或分享
        - 测试时获取完整配置
        """
        return {
            'AUTO_RUN_MODE': AUTO_RUN_MODE,
            'STRATEGY_TYPE': STRATEGY_TYPE,
            'ALLOWED_MARKET': ALLOWED_MARKET,
            'START_DATE': START_DATE,
            'END_DATE': END_DATE,
            'WECHAT_ROBOT_ENABLED': WECHAT_ROBOT_ENABLED,
            'WECHAT_ROBOT_URL': WECHAT_ROBOT_URL,
            'INIT_CAPITAL': INIT_CAPITAL,
            'MAX_HOLD_DAYS': MAX_HOLD_DAYS,
            'STOP_LOSS_RATE': STOP_LOSS_RATE,
            'STOP_PROFIT_RATE': STOP_PROFIT_RATE,
            'COMMISSION_RATE': COMMISSION_RATE,
            'MIN_COMMISSION': MIN_COMMISSION,
            'STAMP_TAX_RATE': STAMP_TAX_RATE,
            'SINGLE_STOCK_POSITION': SINGLE_STOCK_POSITION,
            'INDUSTRY_POSITION': INDUSTRY_POSITION,
            'MAX_HOLD_STOCKS': MAX_HOLD_STOCKS,
            'MAX_DRAWDOWN_STOP': MAX_DRAWDOWN_STOP,
            'DRAWDOWN_STOP_DAYS': DRAWDOWN_STOP_DAYS,
            'MAX_TRADE_RATIO': MAX_TRADE_RATIO,
            'PRICE_ADJUST': PRICE_ADJUST,
            'SLIPPAGE_RATE': SLIPPAGE_RATE,
            'FILTER_CONFIG': FILTER_CONFIG,
            'MARKET_CONDITION': MARKET_CONDITION,
            'DYNAMIC_WEIGHT_MULTIPLIER': DYNAMIC_WEIGHT_MULTIPLIER,
            'CORE_CONFIG': CORE_CONFIG,
            'STRATEGY_CONFIG': STRATEGY_CONFIG,
            'STOCK_PICK_CONFIG': STOCK_PICK_CONFIG,
            'SERVER_HOST': SERVER_HOST,
            'SERVER_PORT': SERVER_PORT,
            'API_BASE_URL': API_BASE_URL,
            'TUSHARE_TOKEN': TUSHARE_TOKEN,
            'TUSHARE_API_URL': TUSHARE_API_URL,
            'FETCH_EXTEND_DATA': FETCH_EXTEND_DATA,
            'VISUALIZATION': VISUALIZATION,
            'LOG_LEVEL': LOG_LEVEL,
            'FETCH_OPTIMIZATION': FETCH_OPTIMIZATION,
            'EXTEND_FETCH_CONFIG': EXTEND_FETCH_CONFIG,
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        【优化】加载全局配置，带锁保护避免竞态条件
        
        功能说明：
        - 优先从配置文件（config.json）加载
        - 如果配置文件不存在，返回默认配置
        - 使用缓存避免重复读取文件
        - 带锁保护保证多线程安全
        
        Returns:
            Dict[str, Any]: 配置字典（包含 token/api_url/start_date/end_date/output_dir/stocks_dir）
            
        使用场景：
        - 系统启动时加载配置
        - 其他模块需要访问 Tushare API 凭证时
        - 获取数据输出目录路径
        
        异常处理：
        - 配置文件不存在：使用默认配置，记录 INFO 日志
        - 配置文件格式错误：记录 WARNING 日志，使用默认配置
        """
        with self._config_lock:
            if self._config_cache is None:
                self._config_cache = {
                    'token': TUSHARE_TOKEN,
                    'api_url': TUSHARE_API_URL,
                    'start_date': START_DATE.replace("-", ""),
                    'end_date': END_DATE.replace("-", ""),
                    'output_dir': os.path.join(self.base_dir, 'data'),
                    'stocks_dir': os.path.join(self.base_dir, 'data_all_stocks')
                }
                if os.path.exists(self.config_file):
                    try:
                        with open(self.config_file, 'r', encoding='utf-8') as f:
                            loaded_config = json.load(f)
                            self._config_cache.update(loaded_config)
                            logger.info(f"✅ 加载配置文件成功：{self.config_file}")
                    except Exception as e:
                        logger.warning(f"⚠️  加载配置文件失败，使用默认配置：{e}")
                else:
                    logger.info("✅ 配置文件不存在，使用默认配置")
            return self._config_cache.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        【优化】保存全局配置，带锁保护
        
        功能说明：
        - 将配置字典保存到 config.json 文件
        - 更新缓存保证后续读取一致
        - 带锁保护避免多线程写入冲突
        
        Args:
            config (Dict[str, Any]): 配置字典
            
        Returns:
            bool: 是否保存成功（True=成功，False=失败）
            
        使用场景：
        - 用户修改配置后保存
        - 系统自动更新配置（如记录抓取进度）
        
        异常处理：
        - 文件写入失败：记录 ERROR 日志，返回 False
        - JSON 序列化失败：记录 ERROR 日志，返回 False
        """
        with self._config_lock:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self._config_cache = config.copy()
                logger.info(f"✅ 保存配置文件成功：{self.config_file}")
                return True
            except Exception as e:
                logger.error(f"❌ 保存配置文件失败：{e}")
                return False
    
    def check_config(self) -> bool:
        """
        【优化】全面检查配置参数合法性
        
        功能说明：
        - 时间格式检查：必须是 YYYY-MM-DD 格式，开始日期不能晚于结束日期
        - 交易参数检查：止损/止盈比例必须在 0-1 之间，初始本金不能低于 100 元
        - 运行模式检查：必须是预定义的 4 种模式之一
        - 策略类型检查：必须是 STRATEGY_CONFIG 中定义的策略
        - 端口检查：必须在 1024-65535 之间
        - 计算限流参数：根据分钟级限流计算秒级限流
        
        Returns:
            bool: 配置是否合法（True=合法，False=非法）
            
        使用场景：
        - 系统启动前校验配置
        - 用户修改配置后校验
        - 回测/选股任务执行前校验
        
        日志输出：
        - 校验通过：记录 INFO 日志 "✅ 配置参数校验通过！"
        - 校验失败：记录 ERROR 日志，说明具体错误原因
        """
        logger.info("开始校验配置参数合法性...")
        try:
            # 时间格式检查
            start = datetime.strptime(START_DATE, "%Y-%m-%d")
            end = datetime.strptime(END_DATE, "%Y-%m-%d")
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
        except Exception as e:
            logger.error(f"❌ 时间配置错误：{e}，请检查格式是否为 YYYY-MM-DD")
            return False
        
        # 交易参数检查
        if not (0 < STOP_LOSS_RATE < 1) or not (0 < STOP_PROFIT_RATE < 1):
            logger.error("❌ 止损/止盈比例必须在 0-1 之间")
            return False
        if INIT_CAPITAL < 100:
            logger.error("❌ 初始本金不能低于 100 元")
            return False
        
        # 运行模式检查
        valid_modes = ["抓取 + 回测", "仅服务", "仅回测", "每日选股"]
        if AUTO_RUN_MODE not in valid_modes:
            logger.error(f"❌ 运行模式错误，仅支持：{valid_modes}，当前：{AUTO_RUN_MODE}")
            return False
        
        # 策略类型检查
        if STRATEGY_TYPE not in STRATEGY_CONFIG.keys():
            logger.error(f"❌ 策略类型错误，仅支持：{list(STRATEGY_CONFIG.keys())}，当前：{STRATEGY_TYPE}")
            return False
        
        # 端口检查
        if SERVER_PORT < 1024 or SERVER_PORT > 65535:
            logger.error("❌ 端口号必须在 1024-65535 之间")
            return False
        
        # 计算每秒请求数，适配分钟级限流
        # 【优化】根据分钟级限流自动计算秒级限流，避免手动配置
        FETCH_OPTIMIZATION['max_requests_per_second'] = max(
            1, 
            FETCH_OPTIMIZATION['max_requests_per_minute'] // 60
        )
        
        logger.info("✅ 配置参数校验通过！")
        return True
    
    def get_api_dates(self) -> tuple:
        """
        【优化】获取 API 用的日期格式
        
        功能说明：
        - 将 START_DATE/END_DATE 转换为 API 格式（YYYYMMDD）
        - 获取当前日期作为最新日期
        - 获取 30 天前的日期作为近期起点
        
        Returns:
            tuple: (START_DATE_API, END_DATE_API, LATEST_DATE, LATEST_START_DATE)
                - START_DATE_API: 开始日期（YYYYMMDD 格式）
                - END_DATE_API: 结束日期（YYYYMMDD 格式）
                - LATEST_DATE: 当前日期（YYYYMMDD 格式）
                - LATEST_START_DATE: 30 天前的日期（YYYYMMDD 格式）
            
        使用场景：
        - 调用 Tushare API 时传递日期参数
        - 抓取近期数据时使用 LATEST_START_DATE
        """
        start_date_api = START_DATE.replace("-", "")
        end_date_api = END_DATE.replace("-", "")
        latest_date = datetime.now().strftime("%Y%m%d")
        latest_start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        return start_date_api, end_date_api, latest_date, latest_start_date


# 导入依赖（延迟导入避免循环引用）
from datetime import timedelta

# 单例实例
config_manager = ConfigManager()
