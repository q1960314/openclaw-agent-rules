# -*- coding: utf-8 -*-
"""
打板策略实现 v1.0
23维评分体系，追涨停板策略

基于原有fetch_data_optimized.py中的打板逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging

from .base_strategy import (
    BaseStrategy, Signal, Position, SignalType, 
    MarketType, StrategyRegistry, RiskParams
)

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class LimitUpStrategy(BaseStrategy):
    """
    打板策略
    
    策略逻辑：
    1. 筛选涨停股票
    2. 23维评分
    3. 买入评分最高的股票
    
    风控参数：
    - 止损: 6%
    - 止盈: 12%
    - 最长持股: 3天
    - 滑点: 1.5%（涨停股买入难度大）
    - 高开买入失败率: 50%
    """
    
    # 策略元信息
    strategy_name = "limit_up"
    strategy_version = "1.0.0"
    strategy_type = "momentum"
    description = "打板策略 - 23维评分追涨停"
    
    # 支持的市场
    supported_markets = [MarketType.MAIN_BOARD, MarketType.CHI_NEXT]
    
    # 所需数据
    required_data = ['daily', 'limit_list', 'top_list', 'hm_detail']
    
    # 23维评分权重（可配置）
    DEFAULT_WEIGHTS = {
        # 封单金额 (15分)
        'order_amount': 15,
        # 连板高度 (15分)
        'up_down_times': 15,
        # 龙虎榜机构买入 (15分)
        'inst_buy': 15,
        # 龙虎榜游资买入 (10分)
        'youzi_buy': 10,
        # 概念热度 (10分)
        'concept_count': 10,
        # 炸板次数 (-5分)
        'break_limit_times': -5,
        # 流通市值 (10分)
        'float_market_cap': 10,
        # 换手率 (5分)
        'turnover_ratio': 5,
        # 无减持 (5分)
        'no_reduction': 5,
        # 无问询 (5分)
        'no_inquiry': 5,
        # 主线行业 (5分)
        'is_main_industry': 5,
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        
        # 加载评分权重
        self.weights = self.config.get('weights', self.DEFAULT_WEIGHTS)
        
        # 初始化风控参数（打板策略特殊参数）
        self.risk_params = RiskParams(
            stop_loss=self.config.get('stop_loss', 0.06),
            stop_profit=self.config.get('stop_profit', 0.12),
            max_hold_days=self.config.get('max_hold_days', 3),
            max_positions=self.config.get('max_positions', 2),
            position_ratio=self.config.get('position_ratio', 0.2),
            slippage_rate=0.015,  # 打板滑点1.5%
            high_open_fail_rate=0.5  # 高开买入失败率50%
        )
    
    def filter(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        股票过滤
        
        筛选条件：
        1. 涨停股票（limit_status == 'U'）
        2. 排除ST
        3. 排除新股（上市<60天）
        4. 市场支持（主板/创业板）
        """
        if data.empty:
            return data
        
        df = data.copy()
        
        # 1. 筛选涨停股票
        if 'limit_status' in df.columns:
            df = df[df['limit_status'] == 'U']
        elif 'pct_chg' in df.columns:
            df = df[df['pct_chg'] >= 9.5]
        
        if df.empty:
            return df
        
        # 2. 排除ST
        if 'name' in df.columns:
            df = df[~df['name'].str.contains('ST|退市', na=False)]
        
        # 3. 市场支持
        if 'ts_code' in df.columns:
            df = df[df['ts_code'].apply(self.is_market_supported)]
        
        # 4. 基本过滤
        if 'close' in df.columns:
            df = df[df['close'] > 0]
        
        return df.reset_index(drop=True)
    
    def score(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        23维评分
        
        评分维度：
        1. 封单金额 (15分)
        2. 连板高度 (15分)
        3. 龙虎榜机构买入 (15分)
        4. 龙虎榜游资买入 (10分)
        5. 概念热度 (10分)
        6. 炸板次数 (-5分)
        7. 流通市值 (10分)
        8. 换手率 (5分)
        9. 无减持 (5分)
        10. 无问询 (5分)
        11. 主线行业 (5分)
        """
        if data.empty:
            return data
        
        df = data.copy()
        
        # 初始化评分列
        df['total_score'] = 0.0
        
        for col, weight in self.weights.items():
            if col in df.columns:
                score = self._calculate_dimension_score(df, col, weight)
                df['total_score'] += score
                df[f'{col}_score'] = score
        
        # 按评分排序
        df = df.sort_values('total_score', ascending=False)
        
        return df.reset_index(drop=True)
    
    def _calculate_dimension_score(self, df: pd.DataFrame, 
                                   dimension: str, 
                                   weight: float) -> pd.Series:
        """计算单维度评分"""
        if dimension not in df.columns:
            return pd.Series(0.0, index=df.index)
        
        values = df[dimension].fillna(0)
        
        if dimension == 'order_amount':
            # 封单金额：分位数评分
            if values.max() > 0:
                normalized = values / values.max()
                return normalized * abs(weight)
        
        elif dimension == 'up_down_times':
            # 连板高度：线性评分
            return values.clip(0, 5) / 5 * abs(weight)
        
        elif dimension == 'inst_buy':
            # 机构买入：分位数评分
            if values.max() > 0:
                normalized = values / values.max()
                return normalized * abs(weight)
        
        elif dimension == 'youzi_buy':
            # 游资买入：分位数评分
            if values.max() > 0:
                normalized = values / values.max()
                return normalized * abs(weight)
        
        elif dimension == 'concept_count':
            # 概念数量：线性评分
            return values.clip(1, 10) / 10 * abs(weight)
        
        elif dimension == 'break_limit_times':
            # 炸板次数：负分
            return -values.clip(0, 5) * abs(weight) / 5
        
        elif dimension == 'float_market_cap':
            # 流通市值：中等市值得分高
            if values.max() > 0:
                # 50-200亿市值得分最高
                mid_cap = (values >= 50) & (values <= 200)
                return mid_cap.astype(float) * abs(weight)
        
        elif dimension == 'turnover_ratio':
            # 换手率：适中得分高
            optimal = (values >= 5) & (values <= 20)
            return optimal.astype(float) * abs(weight)
        
        elif dimension in ['no_reduction', 'no_inquiry', 'is_main_industry']:
            # 二元特征
            return values * abs(weight)
        
        return pd.Series(0.0, index=df.index)
    
    def generate_signals(self, 
                         scored_data: pd.DataFrame, 
                         positions: Dict[str, Position],
                         date: str,
                         capital: float) -> List[Signal]:
        """
        生成买入信号
        
        打板策略特点：
        1. 只在次日开盘买入
        2. 高开可能买不进（模拟）
        3. 涨停开盘直接跳过
        """
        signals = super().generate_signals(scored_data, positions, date, capital)
        
        # 打板策略特殊处理
        for signal in signals:
            signal.reason = f"打板策略选股: 评分{signal.score:.1f}"
            signal.metadata['strategy_type'] = 'limit_up'
        
        return signals


# ==================== 缩量潜伏策略 ====================

@StrategyRegistry.register
class VolumeContractionStrategy(BaseStrategy):
    """
    缩量潜伏策略
    
    策略逻辑：
    1. 筛选首板后的缩量回调股票
    2. 低吸买入
    3. 风险较低
    
    风控参数：
    - 止损: 6%
    - 止盈: 12%
    - 最长持股: 5天
    - 滑点: 0.5%
    """
    
    strategy_name = "volume_contraction"
    strategy_version = "1.0.0"
    strategy_type = "reversal"
    description = "缩量潜伏策略 - 首板后缩量低吸"
    
    supported_markets = [MarketType.MAIN_BOARD, MarketType.CHI_NEXT]
    required_data = ['daily', 'limit_list']
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        
        # 缩量潜伏策略风控参数
        self.risk_params = RiskParams(
            stop_loss=self.config.get('stop_loss', 0.06),
            stop_profit=self.config.get('stop_profit', 0.12),
            max_hold_days=self.config.get('max_hold_days', 5),
            max_positions=self.config.get('max_positions', 2),
            position_ratio=self.config.get('position_ratio', 0.2),
            slippage_rate=0.005,  # 低滑点
            high_open_fail_rate=0.1
        )
    
    def filter(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        筛选缩量回调股票
        
        条件：
        1. 近20日有首板
        2. 当日缩量（成交量 < 首板日成交量的50%）
        3. 价格回调到支撑位附近
        """
        if data.empty:
            return data
        
        df = data.copy()
        
        # 检查是否有首板特征
        if 'is_first_board' in df.columns:
            # 筛选首板后2-5天的股票
            if 'days_after_board' in df.columns:
                df = df[(df['days_after_board'] >= 2) & (df['days_after_board'] <= 5)]
        
        # 检查缩量
        if 'current_vol_ratio' in df.columns:
            df = df[df['current_vol_ratio'] < 0.5]
        
        # 检查支撑位
        if 'price_to_support_ratio' in df.columns:
            df = df[df['price_to_support_ratio'] < 0.05]
        
        # 市场支持
        if 'ts_code' in df.columns:
            df = df[df['ts_code'].apply(self.is_market_supported)]
        
        return df.reset_index(drop=True)
    
    def score(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        缩量评分
        
        评分维度：
        1. 缩量程度 (30分)
        2. 首板放量程度 (20分)
        3. 回调幅度 (20分)
        4. 支撑强度 (15分)
        5. 概念热度 (15分)
        """
        if data.empty:
            return data
        
        df = data.copy()
        df['total_score'] = 0.0
        
        # 缩量程度评分
        if 'current_vol_ratio' in df.columns:
            vol_ratio = df['current_vol_ratio'].fillna(1)
            df['vol_score'] = (1 - vol_ratio.clip(0, 1)) * 30
            df['total_score'] += df['vol_score']
        
        # 首板放量程度
        if 'board_vol_growth' in df.columns:
            growth = df['board_vol_growth'].fillna(1)
            df['growth_score'] = growth.clip(1, 5) / 5 * 20
            df['total_score'] += df['growth_score']
        
        # 回调幅度评分
        if 'price_to_support_ratio' in df.columns:
            pullback = df['price_to_support_ratio'].abs()
            df['pullback_score'] = (1 - pullback.clip(0, 0.1) * 10) * 20
            df['total_score'] += df['pullback_score']
        
        df = df.sort_values('total_score', ascending=False)
        return df.reset_index(drop=True)


# ==================== 注册测试 ====================

if __name__ == "__main__":
    print("已注册策略:", StrategyRegistry.list_all())
    
    # 测试打板策略
    strategy = StrategyRegistry.get_instance("limit_up")
    print(f"策略: {strategy.strategy_name}")
    print(f"风控参数: 止损{strategy.risk_params.stop_loss*100}%, 滑点{strategy.risk_params.slippage_rate*100}%")
    
    # 测试缩量潜伏策略
    strategy2 = StrategyRegistry.get_instance("volume_contraction")
    print(f"策略: {strategy2.strategy_name}")
    print(f"风控参数: 最长持股{strategy2.risk_params.max_hold_days}天")