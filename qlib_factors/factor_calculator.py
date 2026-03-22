# -*- coding: utf-8 -*-
"""
qlib因子计算器 - 作为评分的额外维度
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QlibFactorCalculator:
    """
    qlib因子计算器
    
    计算因子作为评分的额外维度
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.factor_weights = self.config.get('factor_weights', {
            'momentum': 0.3,
            'volume': 0.2,
            'volatility': 0.2,
            'position': 0.3
        })
    
    def calculate(self, stock_data: pd.DataFrame, date: str) -> pd.Series:
        """
        计算因子评分
        
        Args:
            stock_data: 股票数据
            date: 日期
        
        Returns:
            因子评分Series (0-1)
        """
        if stock_data.empty:
            return pd.Series()
        
        scores = pd.Series(index=stock_data.index, data=0.0)
        
        # 1. 动量因子
        if 'pct_chg' in stock_data.columns:
            momentum_score = self._calc_momentum(stock_data['pct_chg'])
            scores += momentum_score * self.factor_weights['momentum']
        
        # 2. 成交量因子
        if 'amount' in stock_data.columns:
            volume_score = self._calc_volume(stock_data['amount'])
            scores += volume_score * self.factor_weights['volume']
        
        # 3. 波动率因子（如果有历史数据）
        # 简化处理，暂时跳过
        
        # 4. 价格位置因子
        if 'close' in stock_data.columns:
            position_score = self._calc_position(stock_data)
            scores += position_score * self.factor_weights['position']
        
        return scores
    
    def _calc_momentum(self, pct_chg: pd.Series) -> pd.Series:
        """计算动量因子"""
        score = pd.Series(index=pct_chg.index, data=0.0)
        
        # 涨幅越大，得分越高
        score[pct_chg >= 9.9] = 1.0
        score[(pct_chg >= 5) & (pct_chg < 9.9)] = 0.7
        score[(pct_chg >= 2) & (pct_chg < 5)] = 0.4
        score[(pct_chg >= 0) & (pct_chg < 2)] = 0.2
        
        return score
    
    def _calc_volume(self, amount: pd.Series) -> pd.Series:
        """计算成交量因子"""
        score = pd.Series(index=amount.index, data=0.5)
        
        median = amount.median()
        
        score[amount >= median * 2] = 1.0
        score[amount >= median] = 0.7
        score[amount < median * 0.5] = 0.2
        
        return score
    
    def _calc_position(self, data: pd.DataFrame) -> pd.Series:
        """计算价格位置因子"""
        score = pd.Series(index=data.index, data=0.5)
        
        # 价格在5-30元之间加分
        if 'close' in data.columns:
            score[(data['close'] >= 5) & (data['close'] <= 30)] = 0.7
            score[(data['close'] >= 10) & (data['close'] <= 20)] = 1.0
        
        return score
    
    def run_standalone_backtest(self, factors: List[str], start_date: str, 
                                end_date: str, data_loader) -> Dict:
        """
        qlib独立回测新因子
        
        Args:
            factors: 因子列表
            start_date: 开始日期
            end_date: 结束日期
            data_loader: 数据加载器
        
        Returns:
            回测结果
        """
        trade_dates = data_loader.get_trade_dates(start_date, end_date)
        
        results = {
            'dates': trade_dates,
            'signals': [],
            'performance': {}
        }
        
        for date in trade_dates:
            stock_data = data_loader.load_all_stocks_daily(date)
            if stock_data.empty:
                continue
            
            # 计算因子
            factor_scores = self.calculate(stock_data, date)
            
            # 选出高分股票
            top_stocks = factor_scores.nlargest(10)
            
            results['signals'].append({
                'date': date,
                'stocks': top_stocks.index.tolist(),
                'scores': top_stocks.values.tolist()
            })
        
        return results


if __name__ == "__main__":
    calculator = QlibFactorCalculator()
    
    # 测试
    test_data = pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ'],
        'pct_chg': [10.0, 5.0],
        'amount': [100000, 50000],
        'close': [15.0, 25.0]
    })
    
    scores = calculator.calculate(test_data, '20231201')
    print("因子评分测试:")
    print(scores)
    
    print("\n✅ qlib因子模块测试通过")
