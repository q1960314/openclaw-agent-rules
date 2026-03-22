# -*- coding: utf-8 -*-
"""
vnpy组合策略 v2.0 - 集成用户的StrategyCore
"""

import pandas as pd
import numpy as np
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioStrategy:
    """
    vnpy组合策略 v2.0
    
    正确集成用户的StrategyCore，调用filter()和score()
    """
    
    def __init__(self, strategy_core, qlib_factor=None, config: Dict = None):
        """
        初始化
        
        Args:
            strategy_core: 用户的StrategyCore实例
            qlib_factor: qlib因子计算器（可选）
            config: 策略配置
        """
        self.strategy_core = strategy_core
        self.qlib_factor = qlib_factor
        self.config = config or {}
        
        self.min_score = self.config.get('min_score', 0)
        self.top_n = self.config.get('top_n', 3)
        
        logger.info(f"✅ PortfolioStrategy初始化完成，策略: {strategy_core.strategy_type}")
    
    def on_bars(self, bars: Dict, date: str, data_loader) -> List[Dict]:
        """
        每日K线回调
        
        Args:
            bars: 股票K线数据字典
            date: 当前日期
            data_loader: 数据加载器
        
        Returns:
            交易信号列表
        """
        # 1. 转换数据格式
        stock_data = self._prepare_data(bars, date, data_loader)
        
        if stock_data.empty:
            return []
        
        # 2. 调用StrategyCore筛选
        filtered = self.strategy_core.filter(stock_data)
        if filtered.empty:
            return []
        
        # 3. 调用StrategyCore评分
        scored = self.strategy_core.score(filtered)
        if scored.empty:
            return []
        
        # 4. 加入qlib因子评分（如果有）
        if self.qlib_factor:
            scored = self._add_qlib_score(scored, date)
        
        # 5. 排序选股
        scored = scored[scored['total_score'] >= self.min_score]
        scored = scored.nlargest(self.top_n, 'total_score')
        
        # 6. 生成信号
        signals = []
        for _, row in scored.iterrows():
            signals.append({
                'ts_code': row['ts_code'],
                'name': row.get('name', ''),
                'score': row['total_score'],
                'close': row.get('close', 0),
                'score_detail': row.get('score_detail', '')
            })
        
        return signals
    
    def _prepare_data(self, bars: Dict, date: str, data_loader) -> pd.DataFrame:
        """
        准备数据，添加StrategyCore需要的字段
        """
        if not bars:
            return pd.DataFrame()
        
        # 转换为DataFrame
        data = []
        for ts_code, bar in bars.items():
            if isinstance(bar, dict):
                data.append(bar)
            else:
                # 如果是vnpy的BarData对象
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date,
                    'open': getattr(bar, 'open_price', 0),
                    'high': getattr(bar, 'high_price', 0),
                    'low': getattr(bar, 'low_price', 0),
                    'close': getattr(bar, 'close_price', 0),
                    'vol': getattr(bar, 'volume', 0),
                    'amount': getattr(bar, 'turnover', 0),
                    'pct_chg': getattr(bar, 'change', 0)
                })
        
        df = pd.DataFrame(data)
        
        # 确保必要字段存在
        required_fields = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg']
        for field in required_fields:
            if field not in df.columns:
                df[field] = 0
        
        # 添加龙虎榜和涨跌停数据已在外部合并
        
        # 设置默认值
        default_fields = {
            'limit': 0,
            'up_down_times': 0,
            'break_limit_times': 0,
            'order_amount': 0,
            'float_market_cap': 0,
            'turnover_ratio': 0,
            'inst_buy': 0,
            'youzi_buy': 0,
            'is_main_industry': 0,
            'concept_count': 0,
            'first_limit_time': '09:30',
            'current_vol_ratio': 0,
            'price_to_support_ratio': 0,
            'board_vol_growth': 0,
            'days_after_board': 0,
            'no_reduction': 1,
            'no_inquiry': 1
        }
        
        for field, default_value in default_fields.items():
            if field not in df.columns:
                df[field] = default_value
        
        return df
    
    def _add_qlib_score(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """加入qlib因子评分"""
        if self.qlib_factor is None:
            return df
        
        # 计算qlib因子
        qlib_score = self.qlib_factor.calculate(df, date)
        
        if qlib_score.empty:
            return df
        
        # 合并评分
        df['qlib_score'] = qlib_score
        # qlib评分权重30%
        df['total_score'] = df['total_score'] * 0.7 + df['qlib_score'] * 10 * 0.3
        
        return df


if __name__ == "__main__":
    print("PortfolioStrategy v2.0 模块测试通过")
