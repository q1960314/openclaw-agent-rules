#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场环境识别模型
Market Regime Recognition Model

版本：v1.0
日期：2026-03-12
用途：识别牛市/熊市/震荡市，为策略选择提供依据
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum


class MarketRegime(Enum):
    """市场环境枚举"""
    BULL_MARKET = "牛市"
    BEAR_MARKET = "熊市"
    SIDEWAYS_MARKET = "震荡市"


@dataclass
class MarketData:
    """市场数据结构"""
    # 价格数据
    price: float
    ma250: float
    ma250_slope: float  # 250 日均线斜率
    
    # 市场宽度
    new_highs: int  # 创新高股票数
    new_lows: int   # 创新低股票数
    advancing: int  # 上涨家数
    declining: int  # 下跌家数
    
    # 成交量
    volume: float  # 两市成交额（亿）
    
    # 情绪指标
    limit_up_count: int      # 涨停家数
    limit_down_count: int    # 跌停家数
    limit_up_rate: float     # 封板率
    consecutive_limit_height: int  # 连板高度
    yesterday_limit_up_premium: float  # 昨日涨停今日溢价


class MarketRegimeModel:
    """
    市场环境识别模型
    
    使用多维度指标综合评分，识别当前市场环境
    """
    
    def __init__(self):
        # 各维度权重
        self.weights = {
            'ma_system': 0.25,      # 均线系统
            'market_breadth': 0.25, # 市场宽度
            'volume': 0.25,         # 成交量
            'sentiment': 0.25       # 情绪指标
        }
        
        # 阈值配置
        self.thresholds = {
            'bull_score': 70,   # 牛市阈值
            'bear_score': 30,   # 熊市阈值
            'volume_bull': 10000,  # 牛市成交量阈值（亿）
            'volume_bear': 6000,   # 熊市成交量阈值（亿）
        }
    
    def score_ma_system(self, data: MarketData) -> float:
        """
        均线系统评分 (0-25 分)
        
        评分标准：
        - 价格>250 日线且均线向上：25 分
        - 价格>250 日线但均线走平：18 分
        - 价格<250 日线但均线走平：12 分
        - 价格<250 日线且均线向下：0 分
        """
        score = 0
        
        if data.price > data.ma250:
            if data.ma250_slope > 0:
                score = 25
            elif data.ma250_slope > -0.001:
                score = 18
            else:
                score = 12
        else:
            if data.ma250_slope < 0:
                score = 0
            elif data.ma250_slope < 0.001:
                score = 12
            else:
                score = 18
        
        return score
    
    def score_market_breadth(self, data: MarketData) -> float:
        """
        市场宽度评分 (0-25 分)
        
        评分标准：
        - 新高/新低>3: 25 分
        - 新高/新低>2: 20 分
        - 新高/新低>1: 15 分
        - 新高/新低<0.5: 0 分
        - 新高/新低<0.8: 8 分
        """
        width_ratio = data.new_highs / max(1, data.new_lows)
        
        if width_ratio > 3:
            return 25
        elif width_ratio > 2:
            return 20
        elif width_ratio > 1:
            return 15
        elif width_ratio < 0.5:
            return 0
        elif width_ratio < 0.8:
            return 8
        else:
            return 12
    
    def score_volume(self, data: MarketData) -> float:
        """
        成交量评分 (0-25 分)
        
        评分标准：
        - >10000 亿：25 分
        - >8000 亿：20 分
        - >6000 亿：15 分
        - <6000 亿：0-12 分线性
        """
        volume = data.volume
        
        if volume > 10000:
            return 25
        elif volume > 8000:
            return 20
        elif volume > 6000:
            return 15
        else:
            # 6000 亿以下线性评分
            return max(0, 12.5 * (volume / 6000))
    
    def score_sentiment(self, data: MarketData) -> float:
        """
        情绪指标评分 (0-25 分)
        
        评分标准：
        - 封板率>70% 且连板>7: 25 分
        - 封板率>60% 且连板>5: 20 分
        - 封板率>40% 且连板>3: 15 分
        - 封板率<40% 且连板<3: 0 分
        """
        score = 0
        
        # 封板率评分 (0-15 分)
        if data.limit_up_rate > 0.7:
            score += 15
        elif data.limit_up_rate > 0.6:
            score += 12
        elif data.limit_up_rate > 0.4:
            score += 8
        elif data.limit_up_rate < 0.3:
            score += 0
        else:
            score += 4
        
        # 连板高度评分 (0-10 分)
        if data.consecutive_limit_height > 7:
            score += 10
        elif data.consecutive_limit_height > 5:
            score += 8
        elif data.consecutive_limit_height > 3:
            score += 5
        elif data.consecutive_limit_height < 2:
            score += 0
        else:
            score += 3
        
        return min(25, score)
    
    def calculate_score(self, data: MarketData) -> float:
        """
        计算市场环境综合评分 (0-100 分)
        
        Returns:
            float: 综合评分
        """
        score_ma = self.score_ma_system(data)
        score_breadth = self.score_market_breadth(data)
        score_volume = self.score_volume(data)
        score_sentiment = self.score_sentiment(data)
        
        total_score = (
            score_ma * self.weights['ma_system'] +
            score_breadth * self.weights['market_breadth'] +
            score_volume * self.weights['volume'] +
            score_sentiment * self.weights['sentiment']
        )
        
        return total_score
    
    def get_regime(self, score: float) -> MarketRegime:
        """
        根据评分判断市场环境
        
        Args:
            score: 综合评分
            
        Returns:
            MarketRegime: 市场环境
        """
        if score > self.thresholds['bull_score']:
            return MarketRegime.BULL_MARKET
        elif score < self.thresholds['bear_score']:
            return MarketRegime.BEAR_MARKET
        else:
            return MarketRegime.SIDEWAYS_MARKET
    
    def get_recommended_strategies(self, regime: MarketRegime) -> List[str]:
        """
        根据市场环境推荐策略
        
        Args:
            regime: 市场环境
            
        Returns:
            List[str]: 推荐策略列表
        """
        recommendations = {
            MarketRegime.BULL_MARKET: [
                '龙头战法',
                '连板战法',
                '低吸战法'
            ],
            MarketRegime.SIDEWAYS_MARKET: [
                '首板战法',
                '高低切换',
                '低吸战法',
                '轮动战法'
            ],
            MarketRegime.BEAR_MARKET: [
                '埋伏战法',
                '空仓观望'
            ]
        }
        return recommendations.get(regime, [])
    
    def get_position_range(self, regime: MarketRegime) -> Tuple[float, float]:
        """
        获取建议仓位范围
        
        Args:
            regime: 市场环境
            
        Returns:
            Tuple[float, float]: (最小仓位，最大仓位)
        """
        ranges = {
            MarketRegime.BULL_MARKET: (0.6, 1.0),
            MarketRegime.SIDEWAYS_MARKET: (0.4, 0.6),
            MarketRegime.BEAR_MARKET: (0.0, 0.4)
        }
        return ranges.get(regime, (0.0, 0.5))
    
    def analyze(self, data: MarketData) -> Dict:
        """
        完整分析
        
        Args:
            data: 市场数据
            
        Returns:
            Dict: 分析结果
        """
        score = self.calculate_score(data)
        regime = self.get_regime(score)
        strategies = self.get_recommended_strategies(regime)
        position_range = self.get_position_range(regime)
        
        return {
            'score': score,
            'regime': regime.value,
            'recommended_strategies': strategies,
            'position_range': position_range,
            'score_breakdown': {
                'ma_system': self.score_ma_system(data),
                'market_breadth': self.score_market_breadth(data),
                'volume': self.score_volume(data),
                'sentiment': self.score_sentiment(data)
            }
        }


class ExternalFactorMonitor:
    """
    外围因素监控器
    """
    
    def __init__(self):
        self.alerts = []
    
    def check_geopolitical_risk(self, vix: float, gold_change: float, oil_change: float) -> int:
        """
        检查地缘政治风险
        
        Returns:
            int: 风险等级 (-1: 利好，0: 中性，1: 利空)
        """
        risk_score = 0
        
        if vix > 30:
            risk_score += 1
        if abs(gold_change) > 0.03:
            risk_score += 1
        if abs(oil_change) > 0.05:
            risk_score += 1
        
        if risk_score >= 2:
            return 1  # 高风险
        elif risk_score == 0:
            return -1  # 低风险
        else:
            return 0  # 中性
    
    def check_policy_signal(self, policy_type: str, policy_direction: str) -> int:
        """
        检查政策信号
        
        Args:
            policy_type: 政策类型 (monetary/fiscal/industry)
            policy_direction: 政策方向 (loose/tight/neutral)
            
        Returns:
            int: 信号 (-1: 利空，0: 中性，1: 利好)
        """
        if policy_direction == 'loose':
            return 1
        elif policy_direction == 'tight':
            return -1
        else:
            return 0
    
    def check_external_markets(self, nasdaq_change: float, hang_seng_change: float, a50_change: float) -> int:
        """
        检查外围市场
        
        Returns:
            int: 风险等级 (-1: 利好，0: 中性，1: 利空)
        """
        avg_change = (nasdaq_change + hang_seng_change + a50_change) / 3
        
        if avg_change < -0.03:
            return 1  # 利空
        elif avg_change > 0.03:
            return -1  # 利好
        else:
            return 0  # 中性
    
    def adjust_position(self, base_position: float, external_risk: int, policy_signal: int) -> float:
        """
        根据外围因素调整仓位
        
        Args:
            base_position: 基础仓位
            external_risk: 外部风险 (-1, 0, 1)
            policy_signal: 政策信号 (-1, 0, 1)
            
        Returns:
            float: 调整后仓位
        """
        adjusted = base_position
        
        # 外部风险调整
        if external_risk == 1:
            adjusted *= 0.5
        elif external_risk == -1:
            adjusted *= 1.1
        
        # 政策信号调整
        adjusted += policy_signal * 0.1
        
        # 限制在 0-1 之间
        return max(0.0, min(1.0, adjusted))


def demo():
    """演示用法"""
    # 创建模型
    regime_model = MarketRegimeModel()
    external_monitor = ExternalFactorMonitor()
    
    # 示例数据（牛市场景）
    bull_data = MarketData(
        price=3500,
        ma250=3200,
        ma250_slope=0.002,
        new_highs=150,
        new_lows=30,
        advancing=3000,
        declining=1000,
        volume=12000,
        limit_up_count=80,
        limit_down_count=5,
        limit_up_rate=0.75,
        consecutive_limit_height=8,
        yesterday_limit_up_premium=0.04
    )
    
    # 分析
    result = regime_model.analyze(bull_data)
    
    print("=" * 60)
    print("市场环境分析报告")
    print("=" * 60)
    print(f"综合评分：{result['score']:.1f}")
    print(f"市场环境：{result['regime']}")
    print(f"推荐策略：{', '.join(result['recommended_strategies'])}")
    print(f"建议仓位：{result['position_range'][0]:.0%} - {result['position_range'][1]:.0%}")
    print()
    print("评分明细:")
    for key, value in result['score_breakdown'].items():
        print(f"  {key}: {value}")
    print("=" * 60)
    
    # 外围因素调整
    base_position = (result['position_range'][0] + result['position_range'][1]) / 2
    external_risk = external_monitor.check_geopolitical_risk(vix=20, gold_change=0.01, oil_change=0.02)
    policy_signal = external_monitor.check_policy_signal('monetary', 'loose')
    
    final_position = external_monitor.adjust_position(base_position, external_risk, policy_signal)
    print(f"基础仓位：{base_position:.0%}")
    print(f"调整后仓位：{final_position:.0%}")
    print("=" * 60)


if __name__ == '__main__':
    demo()
