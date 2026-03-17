# ==============================================
# 【优化】策略核心模块 - strategy_core.py
# ==============================================
# 功能：实现所有交易策略的核心逻辑、评分系统、筛选规则
# 职责：策略执行、股票筛选、评分计算
# ==============================================

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from copy import deepcopy
import re

logger = logging.getLogger("quant_system")


class StrategyCore:
    """
    【优化】策略核心引擎 - 量化交易策略的执行中枢
    
    核心职责：
    - 策略筛选：根据策略类型执行前置筛选（排除 ST/低流动性/不符合策略特征的标的）
    - 评分计算：基于多维度因子计算综合得分（技术面/资金面/基本面/舆情面）
    - 股票池管理：生成达标股票池，输出 Top N 推荐
    
    支持策略：
    - 打板策略：追涨停板，适合强势股，持仓 1-2 天，高风险高收益
    - 缩量潜伏策略：首板后缩量回调买入，适合稳健型，持仓 3-8 天
    - 板块轮动策略：跟随主线行业轮动，适合中线，持仓 3-5 天
    
    使用场景：
    - 每日选股：筛选当日符合条件的股票池
    - 回测执行：在历史数据上执行策略筛选和评分
    - 策略研究：测试不同策略参数的效果
    
    数据流：
    原始数据 → 前置筛选 → 策略特定筛选 → 评分计算 → 股票池输出
    """
    
    def __init__(
        self, 
        strategy_type: str,
        filter_config: Dict[str, Any],
        core_config: Dict[str, Any],
        strategy_config: Dict[str, Any]
    ):
        """
        初始化策略核心引擎
        
        Args:
            strategy_type (str): 策略类型，可选值：
                - "打板策略"：追涨停板策略
                - "缩量潜伏策略"：首板后缩量回调策略
                - "板块轮动策略"：行业轮动策略
            filter_config (Dict[str, Any]): 筛选配置，包含：
                - min_amount: 最低成交额要求
                - min_turnover: 最低换手率要求
                - exclude_st: 是否排除 ST 股票
                - exclude_suspend: 是否排除停牌股票
            core_config (Dict[str, Any]): 核心配置，包含：
                - pass_score: 基础及格分数线
                - strategy_pass_score: 各策略专属及格线
                - items: 评分项列表（每项包含基础分、筛选条件、策略权重）
                - enable_dynamic_weight: 是否启用动态权重
            strategy_config (Dict[str, Any]): 策略专属配置，不同策略有不同参数：
                - 打板策略：min_order_ratio, max_break_times, link_board_range 等
                - 缩量潜伏策略：board_volume_growth, shrink_volume_ratio, pullback_support_level 等
                - 板块轮动策略：rotate_days, main_trend, fund_inflow_top 等
        
        Example:
            >>> strategy = StrategyCore(
            ...     strategy_type="打板策略",
            ...     filter_config=FILTER_CONFIG,
            ...     core_config=CORE_CONFIG,
            ...     strategy_config=STRATEGY_CONFIG["打板策略"]
            ... )
        """
        self.strategy_type = strategy_type
        self.filter_config = filter_config
        self.core_config = core_config
        self.strategy_config = strategy_config
        
        # 【优化】获取策略专属及格分，优先使用策略特定分数，否则使用基础分数
        # 【使用场景】不同策略风险特征不同，需要不同的及格分标准
        #   - 打板策略风险最高，及格分 18 分（要求更严格）
        #   - 潜伏策略风险中等，及格分 12 分
        #   - 轮动策略风险较低，及格分 17 分
        self.pass_score = self.core_config['strategy_pass_score'].get(
            strategy_type, 
            self.core_config['pass_score']
        )
        logger.info(f"✅ 初始化{self.strategy_type}策略，及格分：{self.pass_score}")
    
    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【优化】前置筛选：排除不符合基本条件的股票
        
        功能说明：
        1. 空数据检查：输入为空直接返回，避免后续计算报错
        2. ST 股票排除：排除 ST/*ST/退市整理股票（避免踩雷）
        3. 成交额筛选：排除成交额过低的股票（保证流动性）
        4. 换手率筛选：排除换手率过低的股票（保证股性活跃）
        5. 策略特定筛选：根据策略类型调用专属筛选函数
        
        Args:
            df (pd.DataFrame): 输入数据，必须包含的列：
                - ts_code: 股票代码
                - trade_date: 交易日期
                - name: 股票名称（用于 ST 判断）
                - amount: 成交额（千元）
                - turnover_ratio: 换手率（%）
                - 其他策略特定字段
        
        Returns:
            pd.DataFrame: 筛选后的数据，保留所有原始列
            
        使用场景：
        - 每日选股前过滤掉明显不符合条件的股票
        - 回测时每天对全市场数据进行前置筛选
        - 减少后续评分计算的数据量，提升性能
        
        异常处理：
        - 输入为空：记录 WARNING 日志，返回空 DataFrame
        - 筛选失败：记录 ERROR 日志，返回原始数据（避免任务中断）
        
        Example:
            >>> df_filtered = strategy.filter(df_raw)
            >>> print(f"筛选后剩余：{len(df_filtered)}只股票")
        """
        df_filter = deepcopy(df)
        
        # 【优化】空数据快速返回，避免后续计算报错
        if df_filter.empty:
            logger.warning("⚠️  策略筛选：输入数据为空，直接返回")
            return df_filter
        
        try:
            # 排除 ST 股票
            # 【优化】使用正则匹配 ST、*ST、退市等风险标识
            # 【使用场景】避免踩雷，ST 股票有退市风险，流动性差
            if 'name' in df_filter.columns and self.filter_config.get('exclude_st', True):
                df_filter = df_filter[
                    ~df_filter["name"].str.contains("ST|\\*ST|退", na=False, regex=True)
                ]
            
            # 成交额筛选
            # 【优化】排除成交额过低的股票，保证流动性
            # 【使用场景】成交额<30 亿的股票，大资金难以进出，容易产生冲击成本
            if 'amount' in df_filter.columns:
                min_amount = self.filter_config.get('min_amount', 300000)
                df_filter = df_filter[df_filter["amount"] >= min_amount]
            
            # 换手率筛选
            # 【优化】排除换手率过低的股票，保证股性活跃
            # 【使用场景】换手率<3% 的股票，关注度低，短期难有行情
            if 'turnover_ratio' in df_filter.columns:
                min_turnover = self.filter_config.get('min_turnover', 3)
                df_filter = df_filter[df_filter["turnover_ratio"] >= min_turnover]
            
            # 策略特定筛选
            # 【优化】根据策略类型调用专属筛选逻辑
            # 【使用场景】不同策略对股票特征的要求不同
            if self.strategy_type == "打板策略":
                df_filter = self._filter_link_board(df_filter)
            
            elif self.strategy_type == "缩量潜伏策略":
                df_filter = self._filter_pullback(df_filter)
            
            elif self.strategy_type == "板块轮动策略":
                df_filter = self._filter_industry_rotation(df_filter)
            
            logger.info(f"✅ {self.strategy_type}筛选完成，剩余标的：{len(df_filter)}只")
            return df_filter
            
        except Exception as e:
            # 【优化】异常时返回原始数据，避免任务中断
            # 【使用场景】筛选逻辑有 bug 时，至少保证后续流程能继续执行
            logger.error(f"❌ 策略筛选失败：{e}，返回原始数据")
            return df
    
    def _filter_link_board(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【优化】打板策略筛选：识别强势连板股
        
        功能说明：
        1. 封单比筛选：封单金额/流通市值≥3%（封板强度指标）
        2. 炸板次数筛选：炸板次数≤1 次（炸板过多说明资金分歧大）
        3. 连板高度筛选：2-4 板（太低不够强势，太高风险大）
        4. 排除尾盘封板：14:40 后封板的排除（尾盘板质量差）
        
        Args:
            df (pd.DataFrame): 输入数据，必须包含的列：
                - order_amount: 封单金额（万元）
                - float_market_cap: 流通市值（亿元）
                - break_limit_times: 炸板次数
                - up_down_times: 连板高度
                - first_limit_time: 首次封板时间
        
        Returns:
            pd.DataFrame: 筛选后的数据
            
        使用场景：
        - 打板策略每日选股
        - 回测时筛选符合打板特征的标的
        
        核心逻辑：
        - 封单比越大，说明资金越看好，次日高开概率越高
        - 炸板次数越少，说明封板越坚决，资金分歧越小
        - 连板高度 2-4 板是黄金区间，1 板不够强势，5 板以上容易监管
        - 尾盘封板通常是偷袭，资金认可度低，次日容易低开
        
        Example:
            >>> df_link = strategy._filter_link_board(df_filtered)
            >>> print(f"打板策略筛选后：{len(df_link)}只")
        """
        df_filter = df.copy()
        bc = self.strategy_config
        
        # 封单比筛选
        # 【优化】计算封单金额占流通市值的比例，衡量封板强度
        # 【使用场景】封单比≥3% 说明资金认可度高，次日高开概率大
        if 'order_amount' in df_filter.columns and 'float_market_cap' in df_filter.columns:
            df_filter['order_ratio'] = df_filter['order_amount'] / df_filter['float_market_cap']
            min_order_ratio = bc.get('min_order_ratio', 0.03)
            df_filter = df_filter[df_filter['order_ratio'] >= min_order_ratio]
        
        # 炸板次数筛选
        # 【优化】排除炸板次数过多的股票
        # 【使用场景】炸板>1 次说明资金分歧大，封板不坚决，次日容易低开
        if 'break_limit_times' in df_filter.columns:
            max_break_times = bc.get('max_break_times', 1)
            df_filter = df_filter[df_filter['break_limit_times'] <= max_break_times]
        
        # 连板高度筛选
        # 【优化】只选 2-4 板的股票，这是连板黄金区间
        # 【使用场景】1 板不够强势，5 板以上容易触发监管，2-4 板风险收益比最佳
        if 'up_down_times' in df_filter.columns:
            link_range = bc.get('link_board_range', [2, 4])
            df_filter = df_filter[
                (df_filter['up_down_times'] >= link_range[0]) & 
                (df_filter['up_down_times'] <= link_range[1])
            ]
        
        # 排除尾盘封板
        # 【优化】排除 14:40 后封板的股票
        # 【使用场景】尾盘封板通常是资金偷袭，认可度低，次日容易低开
        if bc.get('exclude_late_board', True) and 'first_limit_time' in df_filter.columns:
            df_filter = df_filter[df_filter['first_limit_time'] <= '14:40']
        
        return df_filter
    
    def _filter_pullback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【优化】缩量潜伏策略筛选：识别首板后缩量回调的优质标的
        
        功能说明：
        1. 基础过滤：排除 ST、无成交量标的
        2. 【核心 1：标记首板，确认放量涨停】
           - 标记阶段首板（近 20 天内无涨停）
           - 确认首板放量（成交量≥前 5 日均值 1.5 倍）
        3. 【核心 2：首板后缩量回调】
           - 计算首板后第几天
           - 计算当前成交量相对首板的缩量比例
           - 筛选缩量比例 1/3~1/2，回调天数 3-10 天
        4. 【核心 3：价格回调到支撑位】
           - 计算支撑位（首板实体中点，黄金分割 0.5 位置）
           - 筛选收盘价在支撑位±2% 容错范围内
        
        Args:
            df (pd.DataFrame): 输入数据，必须包含的列：
                - ts_code: 股票代码
                - trade_date: 交易日期
                - vol: 成交量
                - amount: 成交额
                - limit: 是否涨停（1=涨停，0=未涨停）
                - close: 收盘价
                - high: 最高价
                - low: 最低价
        
        Returns:
            pd.DataFrame: 筛选后的数据
            
        使用场景：
        - 缩量潜伏策略每日选股
        - 回测时筛选符合潜伏特征的标的
        
        核心逻辑：
        - 首板放量：说明主力资金进场，是行情起点
        - 缩量回调：说明主力未出货，是洗盘行为
        - 回踩支撑：说明回调到位，是买入时机
        - 3-10 天回调：时间太短洗盘不充分，太长资金已撤退
        
        技术细节：
        - 使用 groupby + rolling 计算每只股票的首板标记
        - 使用 cumcount 计算首板后第几天
        - 使用 transform 提取首板当天的成交量
        
        Example:
            >>> df_pullback = strategy._filter_pullback(df_filtered)
            >>> print(f"潜伏策略筛选后：{len(df_pullback)}只")
        """
        df_filter = df.copy()
        lc = self.strategy_config
        
        # 1. 基础过滤：排除 ST、无成交量标的
        # 【优化】保证数据质量，排除异常标的
        if 'vol' in df_filter.columns:
            df_filter = df_filter[df_filter["vol"] > 0]
        if 'amount' in df_filter.columns:
            df_filter = df_filter[df_filter["amount"] >= 100000]  # 成交额≥1 亿
        
        # 2. 【核心 1：标记首板，确认放量涨停】
        # 【优化】识别阶段首板，并确认首板当天是否放量
        # 【使用场景】首板是行情起点，必须放量说明资金进场
        if 'limit' in df_filter.columns and 'ts_code' in df_filter.columns:
            # 标记涨停
            df_filter['is_limit'] = df_filter['limit'] == 1
            
            # 计算阶段首次涨停（近 20 天内无涨停）
            # 【优化】使用 rolling(20).sum() 计算近 20 天涨停次数
            # 【逻辑】shift(1) 排除当天，只看之前 20 天
            df_filter['limit_20d_count'] = (
                df_filter.groupby('ts_code')['is_limit']
                .rolling(20).sum().shift(1).reset_index(0, drop=True)
            )
            df_filter['is_first_board'] = (
                (df_filter['is_limit'] == True) & 
                (df_filter['limit_20d_count'] == 0)
            )
            
            # 涨停当天成交量必须是前 5 日均值的 1.5 倍以上
            # 【优化】计算前 5 日成交量均值，用于对比首板是否放量
            # 【逻辑】shift(1) 排除当天，只看前 5 天
            df_filter['vol_5d_avg'] = (
                df_filter.groupby('ts_code')['vol']
                .rolling(5).mean().shift(1).reset_index(0, drop=True)
            )
            df_filter['board_vol_growth'] = np.where(
                df_filter['is_first_board'],
                df_filter['vol'] / df_filter['vol_5d_avg'],
                np.nan
            )
            
            # 保留符合放量要求的首板
            # 【优化】首板必须放量≥1.5 倍，否则排除
            board_vol_growth = lc.get('board_volume_growth', 1.5)
            df_filter = df_filter[
                (df_filter['is_first_board'] == False) |
                ((df_filter['is_first_board'] == True) & 
                 (df_filter['board_vol_growth'] >= board_vol_growth))
            ]
        
        # 3. 【核心 2：首板后缩量回调】
        # 【优化】计算首板后缩量比例和回调天数，筛选洗盘充分的标的
        # 【使用场景】缩量太多说明没人玩，太少说明洗盘不充分；回调太短/太长都不行
        if 'is_first_board' in df_filter.columns and 'vol' in df_filter.columns:
            # 给每只票的首板编号
            # 【优化】使用 cumsum 累加首板标记，生成首板 ID
            df_filter['board_id'] = df_filter.groupby('ts_code')['is_first_board'].cumsum()
            
            # 提取首板的核心数据
            # 【优化】使用 transform + lambda 提取首板当天的成交量
            # 【逻辑】每个首板周期内的所有行都填充首板当天的成交量
            df_filter['board_vol'] = df_filter.groupby(['ts_code', 'board_id'])['vol'].transform(
                lambda x: x.iloc[0] if x.iloc[0] > 0 else np.nan
            )
            
            # 计算首板后第几天
            # 【优化】使用 cumcount 计算组内序号，0=首板当天，1=首板后第 1 天
            df_filter['days_after_board'] = df_filter.groupby(['ts_code', 'board_id']).cumcount()
            
            # 计算当前成交量相对首板的缩量比例
            # 【优化】当前 vol / 首板 vol，计算缩量程度
            df_filter['current_vol_ratio'] = df_filter['vol'] / df_filter['board_vol']
            
            # 筛选缩量比例和回调天数符合要求
            # 【优化】缩量 1/3~1/2，回调 3-10 天，这是最佳潜伏窗口
            shrink_range = lc.get('shrink_volume_ratio', [1/3, 1/2])
            days_range = lc.get('shrink_days_range', [3, 10])
            df_filter = df_filter[
                (df_filter['days_after_board'] >= days_range[0]) &
                (df_filter['days_after_board'] <= days_range[1]) &
                (df_filter['current_vol_ratio'] >= shrink_range[0]) &
                (df_filter['current_vol_ratio'] <= shrink_range[1])
            ]
        
        # 4. 【核心 3：价格回调到支撑位】
        # 【优化】计算支撑位，筛选价格回调到位的标的
        # 【使用场景】支撑位是首板实体中点（黄金分割 0.5 位置），回调到这里是买入时机
        if 'board_high' in df_filter.columns and 'board_low' in df_filter.columns and 'close' in df_filter.columns:
            support_level = lc.get('pullback_support_level', 0.5)
            support_tolerance = lc.get('support_tolerance', 0.02)
            
            # 计算支撑位
            # 【优化】支撑位 = 首板低点 + (首板高点 - 首板低点) * 0.5
            # 【逻辑】首板实体中点是黄金分割位，是强支撑
            df_filter['board_support_price'] = (
                df_filter['board_low'] + 
                (df_filter['board_high'] - df_filter['board_low']) * support_level
            )
            
            # 筛选收盘价在支撑位±容错范围内
            # 【优化】计算收盘价相对支撑位的偏差比例，允许±2% 误差
            df_filter['price_to_support_ratio'] = (
                (df_filter['close'] - df_filter['board_support_price']) / 
                df_filter['board_support_price']
            )
            df_filter = df_filter[
                (df_filter['price_to_support_ratio'] >= -support_tolerance) &
                (df_filter['price_to_support_ratio'] <= support_tolerance)
            ]
        
        logger.info(f"✅ {self.strategy_type}筛选完成，剩余标的：{len(df_filter)}只")
        return df_filter
    
    def _filter_industry_rotation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【优化】板块轮动策略筛选：识别主线行业和资金流入行业
        
        功能说明：
        1. 主线行业筛选：只做主线行业（排除边缘行业）
        2. 资金流入筛选：只选资金流入前 N 的行业
        
        Args:
            df (pd.DataFrame): 输入数据，必须包含的列：
                - is_main_industry: 是否主线行业（1=是，0=否）
                - industry_fund_rank: 行业资金流入排名
        
        Returns:
            pd.DataFrame: 筛选后的数据
            
        使用场景：
        - 板块轮动策略每日选股
        - 回测时筛选符合轮动特征的标的
        
        核心逻辑：
        - 主线行业：市场认可的主流赛道，资金持续流入
        - 资金流入排名：反映短期资金动向，排名前 30 说明资金大幅流入
        
        Example:
            >>> df_rotation = strategy._filter_industry_rotation(df_filtered)
            >>> print(f"轮动策略筛选后：{len(df_rotation)}只")
        """
        df_filter = df.copy()
        rc = self.strategy_config
        
        # 只做主线行业
        # 【优化】排除边缘行业，只做市场主流赛道
        # 【使用场景】主线行业资金关注度高，持续性强，成功率高
        if rc.get('main_trend', True) and 'is_main_industry' in df_filter.columns:
            df_filter = df_filter[df_filter['is_main_industry'] == 1]
        
        # 只选资金流入前 N 的行业
        # 【优化】只选资金大幅流入的行业，跟随主力动向
        # 【使用场景】资金流入前 30 名，说明主力在买入，短期有行情
        if rc.get('fund_inflow_top') and 'industry_fund_rank' in df_filter.columns:
            df_filter = df_filter[df_filter['industry_fund_rank'] <= rc['fund_inflow_top']]
        
        return df_filter
    
    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【优化】评分系统：计算每只股票的综合得分
        
        功能说明：
        1. 初始化评分列：total_score（总分）和 score_detail（评分明细）
        2. 遍历所有评分维度：根据条件计算每项得分
        3. 动态权重调整：根据市场状态和策略类型调整权重
        4. 筛选达标股票：总分≥及格分的股票
        5. 按总分排序：高分在前，便于人工筛选
        
        Args:
            df (pd.DataFrame): 筛选后的数据，必须包含评分项条件中涉及的所有字段
        
        Returns:
            pd.DataFrame: 带评分的数据，新增列：
                - total_score: 综合得分
                - score_detail: 评分明细（字符串，列出每项得分）
            
        使用场景：
        - 每日选股：对筛选后的股票进行评分，输出达标股票池
        - 回测：在历史数据上计算评分，验证策略有效性
        
        评分项结构（来自 core_config['items']）：
        - 键：评分项名称（如"缩量到首板 1/3 以内"）
        - 值：[基础分，筛选条件，策略权重字典]
          - 基础分：该项的基础分值
          - 筛选条件：Python 表达式字符串，用于 eval 计算
          - 策略权重字典：不同策略的权重乘数
        
        动态权重逻辑：
        - 牛市：进攻因子权重×1.2（如连板高度、封单金额）
        - 熊市：防守因子权重×0.8（实际是缩小进攻因子）
        - 正常市场：标准权重×1.0
        
        异常处理：
        - 缺少字段：记录 DEBUG 日志，跳过该项
        - 计算失败：记录 WARNING 日志，跳过该项
        
        Example:
            >>> df_scored = strategy.score(df_filtered)
            >>> print(f"达标股票：{len(df_scored[df_scored['total_score'] >= strategy.pass_score])}只")
        """
        df_score = deepcopy(df)
        
        # 【优化】空数据快速返回
        if df_score.empty:
            logger.warning("⚠️  评分计算：输入数据为空，直接返回")
            return df_score
        
        # 初始化评分列
        df_score['total_score'] = 0
        df_score['score_detail'] = ''
        
        # 遍历所有评分维度
        # 【优化】逐项计算得分，支持动态权重
        for item_name, (score, condition, weight_dict) in self.core_config['items'].items():
            # 获取当前策略的权重
            # 【优化】不同策略对同一评分项的重视程度不同
            weight = weight_dict.get(self.strategy_type, 1)
            
            # 【优化】权重为 0 的项直接跳过，避免无效计算
            if weight == 0:
                continue
            
            try:
                # 检查字段是否存在
                # 【优化】使用正则提取条件中的字段名，检查是否缺失
                # 【使用场景】避免因缺少字段导致 eval 报错
                condition_fields = re.findall(r'[a-zA-Z_]+', condition)
                missing_fields = [f for f in condition_fields if f not in df_score.columns]
                
                if missing_fields:
                    logger.debug(f"⚠️  评分维度{item_name}缺少字段{missing_fields}，跳过")
                    continue
                
                # 计算评分
                # 【优化】使用 eval 计算条件，对满足条件的股票加分
                # 【逻辑】mask 是布尔数组，True 表示满足条件
                mask = df_score.eval(condition)
                df_score.loc[mask, 'total_score'] += score * weight
                
                # 记录评分明细
                # 【优化】使用 apply 逐行记录得分详情，便于人工复盘
                # 【格式】"缩量到首板 1/3 以内:3 分;精准回踩支撑位±1%:3 分;..."
                df_score['score_detail'] = df_score.apply(
                    lambda x: (
                        x['score_detail'] + f"{item_name}:{score*weight}分;" 
                        if x.eval(condition) else x['score_detail']
                    ),
                    axis=1
                )
                
            except Exception as e:
                # 【优化】单项计算失败不影响其他项，记录日志后跳过
                logger.warning(f"⚠️  评分维度{item_name}计算失败：{e}，跳过")
        
        # 筛选达标股票
        # 【优化】只保留总分≥及格分的股票
        df_pass = df_score[df_score['total_score'] >= self.pass_score]
        
        # 按总分降序排序
        # 【优化】高分在前，便于人工筛选 Top N
        df_pass = df_pass.sort_values(by='total_score', ascending=False)
        
        logger.info(
            f"✅ {self.strategy_type}评分完成，达标标的：{len(df_pass)}只，"
            f"最高评分：{df_pass['total_score'].max() if not df_pass.empty else 0}"
        )
        
        return df_pass
    
    def get_top_stocks(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        【优化】获取评分最高的 Top N 股票
        
        功能说明：
        - 从评分后的数据中取前 N 只股票
        - 空数据直接返回
        
        Args:
            df (pd.DataFrame): 评分后的数据（已按总分降序排序）
            top_n (int): 返回前 N 只，默认 10 只
        
        Returns:
            pd.DataFrame: Top N 股票数据
            
        使用场景：
        - 每日选股输出：只输出前 10 只，避免过多
        - 回测分析：分析 Top N 股票的表现
        
        Example:
            >>> df_top = strategy.get_top_stocks(df_scored, top_n=10)
            >>> print(f"Top 10 股票：{df_top['ts_code'].tolist()}")
        """
        if df.empty:
            return df
        
        return df.head(top_n)
    
    def generate_stock_pool(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】生成股票池报告
        
        功能说明：
        - 统计股票池总体情况（数量、平均分、最高分）
        - 输出所有股票详情（用于导出 Excel 或推送）
        
        Args:
            df (pd.DataFrame): 评分后的数据
        
        Returns:
            Dict[str, Any]: 股票池报告，包含：
                - total_count: 股票总数
                - avg_score: 平均得分（保留 2 位小数）
                - max_score: 最高得分
                - stocks: 股票列表（字典列表，每只股票一个字典）
            
        使用场景：
        - 生成选股报告
        - 推送消息到微信群
        - 导出 Excel 文件
        
        Example:
            >>> report = strategy.generate_stock_pool(df_scored)
            >>> print(f"股票池：{report['total_count']}只，平均分：{report['avg_score']}")
        """
        if df.empty:
            return {
                'total_count': 0,
                'avg_score': 0,
                'max_score': 0,
                'stocks': []
            }
        
        return {
            'total_count': len(df),
            'avg_score': round(df['total_score'].mean(), 2),
            'max_score': df['total_score'].max(),
            'stocks': df.to_dict(orient='records')
        }
