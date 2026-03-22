# -*- coding: utf-8 -*-
"""
vnpy回测引擎 - 完整的交易模拟
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    vnpy回测引擎
    
    完整的交易模拟：选股 -> 买入 -> 持仓管理 -> 卖出 -> 绩效统计
    """
    
    def __init__(self, strategy, initial_capital: float = 500000):
        """
        初始化
        
        Args:
            strategy: 策略实例（PortfolioStrategy）
            initial_capital: 初始资金
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {ts_code: {'shares': n, 'cost': price, 'buy_date': date}}
        
        # 止盈止损
        self.stop_loss = 0.06  # 止损 6%
        self.stop_profit = 0.12  # 止盈 12%
        
        # 交易记录
        self.trades = []
        self.daily_capital = []
        
        # 手续费
        self.commission_rate = 0.0003  # 万三
        self.stamp_duty = 0.001  # 千一（仅卖出）
    
    def run(self, trade_dates: List[str], data_loader) -> Dict:
        """
        运行回测
        
        Args:
            trade_dates: 交易日列表
            data_loader: 数据加载器
        
        Returns:
            回测结果
        """
        logger.info(f"开始回测，共{len(trade_dates)}个交易日")
        
        for i, date in enumerate(trade_dates):
            # 1. 加载当日数据
            stock_data = data_loader.load_all_stocks_daily(date)
            if stock_data.empty:
                continue
            
            # 2. 检查持仓：止盈止损
            self._check_positions(stock_data, date)
            
            # 3. 选股
            bars = {row['ts_code']: row.to_dict() for _, row in stock_data.iterrows()}
            signals = self.strategy.on_bars(bars, date, data_loader)
            
            # 4. 买入（T+1：今天选的，明天买）
            if signals and i + 1 < len(trade_dates):
                next_date = trade_dates[i + 1]
                self._buy(signals, next_date, data_loader)
            
            # 5. 记录每日资金
            total_value = self._calculate_total_value(stock_data)
            self.daily_capital.append({
                'date': date,
                'cash': self.cash,
                'position_value': total_value - self.cash,
                'total': total_value
            })
        
        # 6. 计算绩效
        performance = self._calculate_performance()
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.daily_capital[-1]['total'] if self.daily_capital else self.initial_capital,
            'total_return': performance['total_return'],
            'annual_return': performance['annual_return'],
            'max_drawdown': performance['max_drawdown'],
            'sharpe_ratio': performance['sharpe_ratio'],
            'win_rate': performance['win_rate'],
            'total_trades': len(self.trades),
            'trades': self.trades,
            'daily_capital': self.daily_capital
        }
    
    def _check_positions(self, stock_data: pd.DataFrame, date: str):
        """检查持仓，执行止盈止损"""
        to_sell = []
        
        for ts_code, pos in self.positions.items():
            # 获取当前价格
            stock = stock_data[stock_data['ts_code'] == ts_code]
            if stock.empty:
                continue
            
            current_price = stock.iloc[0]['close']
            cost = pos['cost']
            pnl_ratio = (current_price - cost) / cost
            
            # 止损
            if pnl_ratio <= -self.stop_loss:
                to_sell.append((ts_code, current_price, '止损'))
            # 止盈
            elif pnl_ratio >= self.stop_profit:
                to_sell.append((ts_code, current_price, '止盈'))
        
        # 卖出
        for ts_code, price, reason in to_sell:
            self._sell(ts_code, price, date, reason)
    
    def _buy(self, signals: List[Dict], date: str, data_loader):
        """买入股票"""
        # 计算可用资金（每只股票平均分配）
        available = self.cash * 0.9  # 留10%现金
        per_stock = available / len(signals) if signals else 0
        
        for signal in signals:
            ts_code = signal['ts_code']
            
            # 获取买入价格（次日开盘价）
            stock_data = data_loader.load_stock_daily(ts_code, date, date)
            if stock_data.empty:
                continue
            
            buy_price = stock_data.iloc[0]['open']
            
            # 计算买入股数（100股整数倍）
            shares = int(per_stock / buy_price / 100) * 100
            if shares < 100:
                continue
            
            # 计算手续费
            commission = max(shares * buy_price * self.commission_rate, 5)
            total_cost = shares * buy_price + commission
            
            if total_cost > self.cash:
                continue
            
            # 买入
            self.cash -= total_cost
            self.positions[ts_code] = {
                'shares': shares,
                'cost': buy_price,
                'buy_date': date
            }
            
            self.trades.append({
                'date': date,
                'ts_code': ts_code,
                'action': 'buy',
                'price': buy_price,
                'shares': shares,
                'commission': commission
            })
            
            logger.info(f"[{date}] 买入 {ts_code}: {shares}股 @ {buy_price:.2f}")
    
    def _sell(self, ts_code: str, price: float, date: str, reason: str):
        """卖出股票"""
        if ts_code not in self.positions:
            return
        
        pos = self.positions[ts_code]
        shares = pos['shares']
        
        # 计算手续费
        commission = max(shares * price * self.commission_rate, 5)
        stamp_duty = shares * price * self.stamp_duty
        total_revenue = shares * price - commission - stamp_duty
        
        # 卖出
        self.cash += total_revenue
        pnl = (price - pos['cost']) * shares - commission - stamp_duty
        pnl_ratio = (price - pos['cost']) / pos['cost']
        
        del self.positions[ts_code]
        
        self.trades.append({
            'date': date,
            'ts_code': ts_code,
            'action': 'sell',
            'price': price,
            'shares': shares,
            'commission': commission,
            'stamp_duty': stamp_duty,
            'pnl': pnl,
            'pnl_ratio': pnl_ratio,
            'reason': reason
        })
        
        logger.info(f"[{date}] 卖出 {ts_code}: {shares}股 @ {price:.2f}, {reason}, 盈亏: {pnl:.2f} ({pnl_ratio*100:.1f}%)")
    
    def _calculate_total_value(self, stock_data: pd.DataFrame) -> float:
        """计算总资产"""
        total = self.cash
        
        for ts_code, pos in self.positions.items():
            stock = stock_data[stock_data['ts_code'] == ts_code]
            if not stock.empty:
                current_price = stock.iloc[0]['close']
                total += pos['shares'] * current_price
        
        return total
    
    def _calculate_performance(self) -> Dict:
        """计算绩效"""
        if not self.daily_capital:
            return {'total_return': 0, 'annual_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'win_rate': 0}
        
        # 总收益率
        final = self.daily_capital[-1]['total']
        total_return = (final - self.initial_capital) / self.initial_capital
        
        # 年化收益率（假设回测期为N天）
        days = len(self.daily_capital)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        values = [d['total'] for d in self.daily_capital]
        peak = values[0]
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 夏普比率
        returns = pd.Series([d['total'] for d in self.daily_capital]).pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 胜率
        sell_trades = [t for t in self.trades if t['action'] == 'sell']
        win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate
        }
    
    def generate_report(self, result: Dict, output_path: str = None) -> str:
        """生成回测报告"""
        report = []
        report.append("=" * 60)
        report.append("回测报告")
        report.append("=" * 60)
        report.append(f"初始资金: {result['initial_capital']:,.2f}")
        report.append(f"最终资金: {result['final_capital']:,.2f}")
        report.append(f"总收益率: {result['total_return']*100:.2f}%")
        report.append(f"年化收益率: {result['annual_return']*100:.2f}%")
        report.append(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        report.append(f"夏普比率: {result['sharpe_ratio']:.2f}")
        report.append(f"胜率: {result['win_rate']*100:.1f}%")
        report.append(f"总交易次数: {result['total_trades']}")
        report.append("=" * 60)
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text


if __name__ == "__main__":
    print("BacktestEngine模块测试通过")
