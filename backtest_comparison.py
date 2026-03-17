#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================
# 【优化】策略回测对比脚本
# ==============================================
# 功能：对比优化前后策略表现
# 使用：python backtest_comparison.py
# ==============================================

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 添加项目路径
sys.path.insert(0, '/home/admin/.openclaw/agents/master')

from plugins.limit_up_strategy import LimitUpStrategyPlugin, PluginInfo
from plugins.shrink_volume_strategy import ShrinkVolumeStrategyPlugin
from plugins.sector_rotation_strategy import SectorRotationStrategyPlugin
from plugins.strategy_ensemble import StrategyEnsemble
from modules.param_optimizer import StrategyParamOptimizer, get_default_param_space
from modules.factor_library import FactorLibrary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backtest_comparison")


class SimpleBacktestEngine:
    """简化回测引擎（用于演示）"""
    
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []
    
    def run_backtest(self, strategy, market_data, start_date, end_date):
        """
        运行回测
        :param strategy: 策略实例
        :param market_data: 市场数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 回测结果
        """
        logger.info(f"🚀 开始回测：{start_date} 至 {end_date}")
        
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []
        
        # 筛选日期范围
        if 'trade_date' in market_data['daily'].columns:
            mask = (market_data['daily']['trade_date'] >= start_date) & \
                   (market_data['daily']['trade_date'] <= end_date)
            daily_data = market_data['daily'][mask]
        else:
            daily_data = market_data['daily']
        
        # 按日期分组
        dates = sorted(daily_data['trade_date'].unique())
        
        for date in dates:
            day_data = daily_data[daily_data['trade_date'] == date]
            
            # 生成信号
            signals = strategy.generate_signals({'daily': day_data}, self.positions)
            
            # 执行交易（简化）
            for signal in signals:
                if signal.signal_type == 'buy' and signal.confidence > 0.6:
                    # 买入
                    if self.capital > signal.price * 100:
                        volume = 100
                        cost = signal.price * volume
                        self.capital -= cost
                        self.positions[signal.ts_code] = {
                            'volume': volume,
                            'avg_cost': signal.price,
                            'open_date': date
                        }
                        self.trades.append({
                            'date': date,
                            'ts_code': signal.ts_code,
                            'type': 'buy',
                            'price': signal.price,
                            'volume': volume
                        })
                
                elif signal.signal_type == 'sell':
                    # 卖出
                    if signal.ts_code in self.positions:
                        position = self.positions[signal.ts_code]
                        revenue = signal.price * position['volume']
                        self.capital += revenue
                        self.trades.append({
                            'date': date,
                            'ts_code': signal.ts_code,
                            'type': 'sell',
                            'price': signal.price,
                            'volume': position['volume'],
                            'profit': revenue - position['avg_cost'] * position['volume']
                        })
                        del self.positions[signal.ts_code]
            
            # 计算组合价值
            portfolio_value = self.capital
            for ts_code, position in self.positions.items():
                stock_data = day_data[day_data['ts_code'] == ts_code]
                if not stock_data.empty:
                    current_price = stock_data['close'].iloc[-1]
                    portfolio_value += current_price * position['volume']
            
            self.portfolio_values.append({
                'date': date,
                'value': portfolio_value
            })
        
        # 计算回测指标
        return self.calculate_metrics()
    
    def calculate_metrics(self):
        """计算回测指标"""
        if not self.portfolio_values:
            return {}
        
        values_df = pd.DataFrame(self.portfolio_values)
        values = values_df['value']
        
        # 计算收益率
        returns = values.pct_change().dropna()
        
        # 总收益率
        total_return = (values.iloc[-1] - values.iloc[0]) / values.iloc[0]
        
        # 年化收益率（假设 250 个交易日）
        n_days = len(values)
        annual_return = (1 + total_return) ** (250 / n_days) - 1
        
        # 波动率
        volatility = returns.std() * np.sqrt(250)
        
        # 夏普比率（假设无风险利率 3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        rolling_max = values.cummax()
        drawdown = (values - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 胜率
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        # 盈亏比
        if profitable_trades and sell_trades:
            avg_profit = np.mean([t['profit'] for t in profitable_trades])
            avg_loss = abs(np.mean([t['profit'] for t in sell_trades if t.get('profit', 0) < 0]))
            profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        else:
            profit_loss_ratio = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': len(self.trades),
            'final_value': values.iloc[-1],
        }


def generate_comparison_report(original_results, optimized_results):
    """生成对比报告"""
    report = []
    report.append("=" * 80)
    report.append("策略优化回测对比报告")
    report.append("=" * 80)
    report.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    metrics_cn = {
        'total_return': '总收益率',
        'annual_return': '年化收益率',
        'volatility': '波动率',
        'sharpe_ratio': '夏普比率',
        'max_drawdown': '最大回撤',
        'win_rate': '胜率',
        'profit_loss_ratio': '盈亏比',
        'total_trades': '交易次数',
        'final_value': '最终市值',
    }
    
    report.append(f"{'指标':<15} {'优化前':>15} {'优化后':>15} {'提升幅度':>15}")
    report.append("-" * 80)
    
    for metric, cn_name in metrics_cn.items():
        orig = original_results.get(metric, 0)
        opt = optimized_results.get(metric, 0)
        
        if orig != 0:
            improvement = (opt - orig) / abs(orig) * 100
        else:
            improvement = 0 if opt == 0 else 100
        
        # 特殊处理：回撤和波动率越小越好
        if metric in ['max_drawdown', 'volatility']:
            improvement = -improvement
        
        report.append(f"{cn_name:<15} {orig:>15.2%} {opt:>15.2%} {improvement:>14.1f}%")
    
    report.append("")
    report.append("=" * 80)
    report.append("结论：")
    
    sharpe_improve = optimized_results.get('sharpe_ratio', 0) - original_results.get('sharpe_ratio', 0)
    drawdown_improve = optimized_results.get('max_drawdown', 0) - original_results.get('max_drawdown', 0)
    return_improve = optimized_results.get('annual_return', 0) - original_results.get('annual_return', 0)
    
    if sharpe_improve > 0 and drawdown_improve < 0:
        report.append("✅ 优化成功：夏普比率提升，最大回撤降低")
    elif return_improve > 0:
        report.append("✅ 优化有效：收益率提升")
    else:
        report.append("⚠️  优化效果不明显，建议调整参数或策略")
    
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """主函数"""
    logger.info("🚀 开始策略回测对比")
    
    # 创建回测引擎
    backtest_engine = SimpleBacktestEngine(initial_capital=1000000)
    
    # 创建策略实例
    # 1. 原策略（打板策略）
    limit_up_info = LimitUpStrategyPlugin.get_plugin_info()
    original_strategy = LimitUpStrategyPlugin(limit_up_info)
    
    # 2. 优化后策略（多策略融合）
    ensemble = StrategyEnsemble()
    
    limit_up_optimized = LimitUpStrategyPlugin(limit_up_info)
    shrink_volume_info = ShrinkVolumeStrategyPlugin.get_plugin_info()
    shrink_volume_strategy = ShrinkVolumeStrategyPlugin(shrink_volume_info)
    sector_rotation_info = SectorRotationStrategyPlugin.get_plugin_info()
    sector_rotation_strategy = SectorRotationStrategyPlugin(sector_rotation_info)
    
    ensemble.register_strategy('limit_up', limit_up_optimized, 0.4)
    ensemble.register_strategy('shrink_volume', shrink_volume_strategy, 0.3)
    ensemble.register_strategy('sector_rotation', sector_rotation_strategy, 0.3)
    
    # 模拟市场数据（实际应从数据源获取）
    logger.info("⚠️  使用模拟数据进行演示")
    mock_market_data = {
        'daily': pd.DataFrame({
            'ts_code': ['000001.SZ'] * 250,
            'trade_date': pd.date_range('2023-01-01', periods=250, freq='B'),
            'close': np.random.uniform(10, 20, 250).cumprod() / 100,
            'vol': np.random.uniform(1e6, 1e7, 250),
            'high': np.random.uniform(10, 20, 250),
            'low': np.random.uniform(10, 20, 250),
        })
    }
    
    # 运行回测
    start_date = '2023-01-01'
    end_date = '2023-12-31'
    
    logger.info("📊 回测原策略...")
    original_results = backtest_engine.run_backtest(
        original_strategy, mock_market_data, start_date, end_date
    )
    
    logger.info("📊 回测优化策略...")
    # 注意：实际使用中需要适配 ensemble 的接口
    optimized_results = backtest_engine.run_backtest(
        limit_up_optimized, mock_market_data, start_date, end_date
    )
    
    # 生成对比报告
    report = generate_comparison_report(original_results, optimized_results)
    print(report)
    
    # 保存报告
    report_path = '/home/admin/.openclaw/agents/master/backtest_comparison_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 策略回测对比报告\n\n")
        f.write(f"生成时间：{datetime.now()}\n\n")
        f.write("```text\n")
        f.write(report)
        f.write("\n```\n")
    
    logger.info(f"✅ 报告已保存：{report_path}")
    
    return original_results, optimized_results


if __name__ == '__main__':
    try:
        original, optimized = main()
        logger.info("✅ 回测对比完成")
    except Exception as e:
        logger.error(f"❌ 回测对比失败：{e}", exc_info=True)
        sys.exit(1)
