# ==============================================
# 【优化】回测引擎模块 - backtest_engine.py
# ==============================================
# 功能：实现完整的回测系统、交易模拟、绩效分析
# 职责：回测执行、交易记录、绩效计算、报告生成
# ==============================================

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from copy import deepcopy

logger = logging.getLogger("quant_system")


class BacktestEngine:
    """
    【优化】回测引擎
    职责：模拟交易、仓位管理、绩效分析
    """
    
    def __init__(
        self,
        init_capital: float,
        max_hold_days: int,
        stop_loss_rate: float,
        stop_profit_rate: float,
        commission_rate: float,
        min_commission: float,
        stamp_tax_rate: float,
        single_stock_position: float,
        max_hold_stocks: int,
        max_drawdown_stop: float,
        max_trade_ratio: float,
        slippage_rate: float,
        strategy_core
    ):
        """
        初始化回测引擎
        :param init_capital: 初始资金
        :param max_hold_days: 最大持股天数
        :param stop_loss_rate: 止损比例
        :param stop_profit_rate: 止盈比例
        :param commission_rate: 佣金比例
        :param min_commission: 最低佣金
        :param stamp_tax_rate: 印花税比例
        :param single_stock_position: 单只股票最大仓位
        :param max_hold_stocks: 最大持仓股票数
        :param max_drawdown_stop: 最大回撤止损
        :param max_trade_ratio: 单次买入占成交量比例
        :param slippage_rate: 滑点比例
        :param strategy_core: 策略核心实例
        """
        self.init_capital = init_capital
        self.max_hold_days = max_hold_days
        self.stop_loss_rate = stop_loss_rate
        self.stop_profit_rate = stop_profit_rate
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.single_stock_position = single_stock_position
        self.max_hold_stocks = max_hold_stocks
        self.max_drawdown_stop = max_drawdown_stop
        self.max_trade_ratio = max_trade_ratio
        self.slippage_rate = slippage_rate
        self.strategy_core = strategy_core
        
        # 回测状态
        self.current_capital = init_capital
        self.max_cash = init_capital
        self.position: Dict[str, Dict[str, Any]] = {}
        self.trade_records: List[Dict[str, Any]] = []
        self.daily_capital: List[Dict[str, Any]] = []
    
    def reset(self):
        """【优化】重置回测状态"""
        self.current_capital = self.init_capital
        self.max_cash = self.init_capital
        self.position = {}
        self.trade_records = []
        self.daily_capital = []
        logger.info("✅ 回测状态已重置")
    
    def calculate_position(
        self, 
        buy_price: float, 
        ts_code: str, 
        df_today: pd.DataFrame
    ) -> Tuple[int, float]:
        """
        【优化】计算可买仓位（贴合 A 股实盘规则）
        :param buy_price: 买入价格
        :param ts_code: 股票代码
        :param df_today: 当日数据
        :return: (可买股数，买入成本)
        """
        # 单只股票最大可用资金
        single_max_cash = self.current_capital * self.single_stock_position
        
        # 成交量限制
        if 'vol' not in df_today.columns:
            return 0, 0
        
        stock_vol = df_today[df_today["ts_code"] == ts_code]["vol"].iloc[0]
        if pd.isna(stock_vol) or stock_vol <= 0:
            return 0, 0
        
        # 最大可买手数（不超过成交量 5%）
        max_trade_hand = int(stock_vol * self.max_trade_ratio)
        max_trade_vol = max_trade_hand * 100
        
        # 资金限制
        available_hand = int((single_max_cash - self.min_commission) / buy_price / 100)
        available_vol = available_hand * 100
        
        # 取最小值
        buy_vol = min(available_vol, max_trade_vol, 100000)
        
        if buy_vol < 100:  # 不足 1 手
            return 0, 0
        
        # 计算买入成本（含佣金和滑点）
        buy_amount = buy_price * buy_vol
        buy_commission = max(buy_amount * self.commission_rate, self.min_commission)
        buy_slippage = buy_amount * self.slippage_rate
        buy_cost = buy_amount + buy_commission + buy_slippage
        
        if buy_cost > self.current_capital:
            return 0, 0
        
        return buy_vol, buy_cost
    
    def execute_buy(
        self, 
        ts_code: str, 
        buy_price: float, 
        buy_vol: int, 
        buy_cost: float,
        trade_date: str
    ) -> bool:
        """
        【优化】执行买入操作
        :param ts_code: 股票代码
        :param buy_price: 买入价格
        :param buy_vol: 买入股数
        :param buy_cost: 买入成本
        :param trade_date: 交易日期
        :return: 是否成功
        """
        try:
            # 更新资金
            self.current_capital -= buy_cost
            
            # 记录持仓
            self.position[ts_code] = {
                "ts_code": ts_code,
                "buy_price": buy_price,
                "volume": buy_vol,
                "buy_date": trade_date,
                "buy_cost": buy_cost,
                "close_price": buy_price
            }
            
            # 记录交易
            self.trade_records.append({
                "trade_date": trade_date,
                "ts_code": ts_code,
                "action": "买入",
                "price": buy_price,
                "volume": buy_vol,
                "cost": buy_cost,
                "capital_after": self.current_capital
            })
            
            logger.debug(f"✅ 买入{ts_code}：{buy_vol}股 @ {buy_price}元")
            return True
            
        except Exception as e:
            logger.error(f"❌ 买入失败：{e}")
            return False
    
    def execute_sell(
        self, 
        ts_code: str, 
        sell_price: float, 
        trade_date: str,
        reason: str = ""
    ) -> bool:
        """
        【优化】执行卖出操作
        :param ts_code: 股票代码
        :param sell_price: 卖出价格
        :param trade_date: 交易日期
        :param reason: 卖出原因
        :return: 是否成功
        """
        try:
            if ts_code not in self.position:
                logger.warning(f"⚠️  卖出失败：{ts_code}不在持仓中")
                return False
            
            pos = self.position[ts_code]
            sell_vol = pos["volume"]
            
            # 计算卖出收入
            sell_amount = sell_price * sell_vol
            sell_commission = max(sell_amount * self.commission_rate, self.min_commission)
            sell_stamp_tax = sell_amount * self.stamp_tax_rate
            sell_slippage = sell_amount * self.slippage_rate
            sell_income = sell_amount - sell_commission - sell_stamp_tax - sell_slippage
            
            # 计算盈亏
            profit = sell_income - pos["buy_cost"]
            profit_rate = profit / pos["buy_cost"] if pos["buy_cost"] > 0 else 0
            
            # 更新资金
            self.current_capital += sell_income
            
            # 记录交易
            self.trade_records.append({
                "trade_date": trade_date,
                "ts_code": ts_code,
                "action": "卖出",
                "price": sell_price,
                "volume": sell_vol,
                "income": sell_income,
                "profit": profit,
                "profit_rate": profit_rate,
                "reason": reason,
                "capital_after": self.current_capital
            })
            
            # 删除持仓
            del self.position[ts_code]
            
            logger.debug(
                f"✅ 卖出{ts_code}：{sell_vol}股 @ {sell_price}元 | "
                f"盈亏：{profit:.2f}元 ({profit_rate:.2%}) | 原因：{reason}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ 卖出失败：{e}")
            return False
    
    def check_stop_loss_stop_profit(
        self, 
        ts_code: str, 
        current_price: float,
        trade_date: str
    ) -> Optional[str]:
        """
        【优化】检查止损止盈
        :param ts_code: 股票代码
        :param current_price: 当前价格
        :param trade_date: 交易日期
        :return: 卖出原因（如果需要卖出）
        """
        if ts_code not in self.position:
            return None
        
        pos = self.position[ts_code]
        buy_price = pos["buy_price"]
        
        # 计算当前盈亏
        profit_rate = (current_price - buy_price) / buy_price
        
        # 止损检查
        if profit_rate <= -self.stop_loss_rate:
            return f"止损（亏损{profit_rate:.2%}）"
        
        # 止盈检查
        if profit_rate >= self.stop_profit_rate:
            return f"止盈（盈利{profit_rate:.2%}）"
        
        # 持股天数检查
        buy_date = datetime.strptime(pos["buy_date"], "%Y-%m-%d")
        trade_date_dt = datetime.strptime(trade_date, "%Y-%m-%d")
        hold_days = (trade_date_dt - buy_date).days
        
        if hold_days >= self.max_hold_days:
            return f"到期卖出（持股{hold_days}天）"
        
        return None
    
    def check_drawdown(self, trade_date: str) -> bool:
        """
        【优化】检查账户最大回撤
        :param trade_date: 交易日期
        :return: 是否触发清仓
        """
        total_asset = self.get_total_asset()
        
        # 更新峰值
        if total_asset > self.max_cash:
            self.max_cash = total_asset
        
        # 计算回撤
        current_drawdown = (self.max_cash - total_asset) / self.max_cash
        
        if current_drawdown >= self.max_drawdown_stop:
            logger.warning(
                f"⚠️  账户最大回撤达到{current_drawdown:.2%}，触发强制清仓！"
            )
            
            # 清仓所有持仓
            for ts_code in list(self.position.keys()):
                # 使用当前价格卖出（这里简化处理）
                self.execute_sell(ts_code, self.position[ts_code]["close_price"], trade_date, "风控清仓")
            
            # 记录空仓状态
            self.daily_capital.append({
                "date": trade_date,
                "capital": total_asset,
                "status": "空仓休市"
            })
            
            return True
        
        return False
    
    def get_total_asset(self) -> float:
        """
        【优化】计算账户总资产
        :return: 总资产
        """
        total_asset = self.current_capital
        
        for pos in self.position.values():
            total_asset += pos["volume"] * pos.get("close_price", pos["buy_price"])
        
        return total_asset
    
    def update_position_market_value(self, df_today: pd.DataFrame):
        """
        【优化】更新持仓股市值
        :param df_today: 当日数据
        """
        for ts_code, pos in list(self.position.items()):
            stock_data = df_today[df_today["ts_code"] == ts_code]
            
            if not stock_data.empty:
                close_price = stock_data.iloc[0].get("close", pos["buy_price"])
                self.position[ts_code]["close_price"] = close_price
            else:
                logger.debug(f"{ts_code}当日停牌，沿用前收盘价")
    
    def record_daily_capital(self, trade_date: str):
        """
        【优化】记录每日资金曲线
        :param trade_date: 交易日期
        """
        total_asset = self.get_total_asset()
        
        self.daily_capital.append({
            "date": trade_date,
            "capital": total_asset,
            "position_count": len(self.position),
            "cash": self.current_capital
        })
    
    def calculate_performance(self) -> Dict[str, Any]:
        """
        【优化】计算回测绩效指标
        :return: 绩效指标字典
        """
        if not self.daily_capital:
            return {}
        
        capital_df = pd.DataFrame(self.daily_capital)
        capital_series = capital_df['capital']
        
        # 总收益率
        total_return = (capital_series.iloc[-1] - self.init_capital) / self.init_capital
        
        # 年化收益率
        days = len(capital_series)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        max_drawdown = 0
        peak = capital_series.iloc[0]
        for value in capital_series:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 波动率
        daily_returns = capital_series.pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
        
        # 夏普比率
        risk_free_rate = 0.03  # 无风险利率假设 3%
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 胜率
        sell_trades = [t for t in self.trade_records if t['action'] == '卖出']
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        # 盈亏比
        total_profit = sum(t.get('profit', 0) for t in profitable_trades)
        total_loss = abs(sum(t.get('profit', 0) for t in sell_trades if t.get('profit', 0) < 0))
        profit_loss_ratio = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'init_capital': self.init_capital,
            'final_capital': capital_series.iloc[-1],
            'total_return': round(total_return, 4),
            'annual_return': round(annual_return, 4),
            'max_drawdown': round(max_drawdown, 4),
            'volatility': round(volatility, 4),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'win_rate': round(win_rate, 4),
            'profit_loss_ratio': round(profit_loss_ratio, 2),
            'total_trades': len(self.trade_records),
            'total_stocks': len(set(t['ts_code'] for t in self.trade_records)),
            'trade_days': days
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        【优化】生成回测报告
        :return: 回测报告字典
        """
        performance = self.calculate_performance()
        
        report = {
            'performance': performance,
            'trade_records': self.trade_records,
            'capital_curve': self.daily_capital,
            'final_position': self.position,
            'summary': self._generate_summary(performance)
        }
        
        return report
    
    def _generate_summary(self, performance: Dict[str, Any]) -> str:
        """
        【优化】生成回测总结
        :param performance: 绩效指标
        :return: 总结文本
        """
        lines = [
            "=" * 60,
            "【回测绩效报告】",
            "=" * 60,
            f"初始资金：{performance.get('init_capital', 0):,.2f}元",
            f"最终资金：{performance.get('final_capital', 0):,.2f}元",
            f"总收益率：{performance.get('total_return', 0):.2%}",
            f"年化收益率：{performance.get('annual_return', 0):.2%}",
            f"最大回撤：{performance.get('max_drawdown', 0):.2%}",
            f"夏普比率：{performance.get('sharpe_ratio', 0):.2f}",
            f"胜率：{performance.get('win_rate', 0):.2%}",
            f"盈亏比：{performance.get('profit_loss_ratio', 0):.2f}",
            f"总交易次数：{performance.get('total_trades', 0)}",
            f"交易股票数：{performance.get('total_stocks', 0)}",
            f"回测天数：{performance.get('trade_days', 0)}",
            "=" * 60
        ]
        
        return "\n".join(lines)
