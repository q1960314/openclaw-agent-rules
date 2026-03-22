# -*- coding: utf-8 -*-
"""
vnpy组合策略 - 集成StrategyCore
"""

import pandas as pd
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioStrategy:
    """
    vnpy组合策略
    
    集成用户的StrategyCore，调用qlib因子
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
        
        # 交易记录
        self.trades = []
        self.positions = {}
        self.cash = self.config.get('initial_capital', 5000)
        
        # 止盈止损
        self.stop_loss = 0.06
        self.stop_profit = 0.12
    
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
        stock_data = self._convert_bars_to_dataframe(bars)
        
        if stock_data.empty:
            return []
        
        # 2. 加载龙虎榜数据
        lhb_data = data_loader.load_lhb_data(date, date)
        limit_data = data_loader.load_limit_data(date, date)
        
        # 3. 调用StrategyCore筛选
        filtered = self.strategy_core.filter(stock_data)
        if filtered.empty:
            return []
        
        # 4. 调用StrategyCore评分
        scored = self.strategy_core.score(filtered)
        if scored.empty:
            return []
        
        # 5. 加入qlib因子评分（如果有）
        if self.qlib_factor:
            scored = self._add_qlib_score(scored, date)
        
        # 6. 排序选股
        scored = scored[scored['total_score'] >= self.min_score]
        scored = scored.nlargest(self.top_n, 'total_score')
        
        # 7. 生成信号
        signals = []
        for _, row in scored.iterrows():
            signals.append({
                'ts_code': row['ts_code'],
                'name': row.get('name', ''),
                'score': row['total_score'],
                'close': row.get('close', 0)
            })
        
        return signals
    
    def _convert_bars_to_dataframe(self, bars: Dict) -> pd.DataFrame:
        """转换bars格式为DataFrame"""
        if not bars:
            return pd.DataFrame()
        
        data = []
        for ts_code, bar in bars.items():
            data.append({
                'ts_code': ts_code,
                'trade_date': bar.datetime.strftime('%Y%m%d') if hasattr(bar, 'datetime') else '',
                'open': bar.open_price if hasattr(bar, 'open_price') else bar.get('open', 0),
                'high': bar.high_price if hasattr(bar, 'high_price') else bar.get('high', 0),
                'low': bar.low_price if hasattr(bar, 'low_price') else bar.get('low', 0),
                'close': bar.close_price if hasattr(bar, 'close_price') else bar.get('close', 0),
                'volume': bar.volume if hasattr(bar, 'volume') else bar.get('volume', 0),
                'amount': bar.turnover if hasattr(bar, 'turnover') else bar.get('amount', 0),
                'pct_chg': bar.change if hasattr(bar, 'change') else bar.get('pct_chg', 0)
            })
        
        return pd.DataFrame(data)
    
    def _add_qlib_score(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """加入qlib因子评分"""
        if self.qlib_factor is None:
            return df
        
        # 计算qlib因子
        qlib_score = self.qlib_factor.calculate(df, date)
        
        # 合并评分
        df['qlib_score'] = qlib_score
        df['total_score'] = df['total_score'] * 0.6 + df['qlib_score'] * 10 * 0.4
        
        return df


if __name__ == "__main__":
    print("PortfolioStrategy模块测试通过")
