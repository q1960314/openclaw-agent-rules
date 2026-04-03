# -*- coding: utf-8 -*-
"""
向量化回测引擎 v7.6 - 完整字段修复版
修复内容：
1. 正确映射limit_list_d字段（fd_amount→order_amount等）
2. 合并top_list机构买入数据（l_buy→inst_buy）
3. 合并hm_detail游资买入数据（buy_amount→youzi_buy）
4. 从概念数据统计concept_count
5. 设置默认值（no_reduction=1, no_inquiry=1, is_main_industry=0）
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import logging
import sys
import random
import os

sys.path.insert(0, '/data/agents/master')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

try:
    from fetch_data_optimized import (
        INIT_CAPITAL, MAX_HOLD_DAYS, STOP_LOSS_RATE, STOP_PROFIT_RATE,
        COMMISSION_RATE, MIN_COMMISSION, STAMP_TAX_RATE,
        SINGLE_STOCK_POSITION, MAX_HOLD_STOCKS
    )
except ImportError:
    INIT_CAPITAL = 10000
    MAX_HOLD_DAYS = 3
    STOP_LOSS_RATE = 0.06
    STOP_PROFIT_RATE = 0.12
    COMMISSION_RATE = 0.00025
    MIN_COMMISSION = 5
    STAMP_TAX_RATE = 0.001
    SINGLE_STOCK_POSITION = 0.2
    MAX_HOLD_STOCKS = 2


class VectorBacktestEngine:
    """向量化回测引擎 v7.6 - 完整字段修复版"""
    
    def __init__(self, strategy, initial_capital=None, strategy_type="打板策略", benchmark_return=0.08):
        self.strategy = strategy
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital or INIT_CAPITAL
        self.benchmark_return = benchmark_return
        
        self.stop_loss = STOP_LOSS_RATE
        self.stop_profit = STOP_PROFIT_RATE
        self.max_hold_days = MAX_HOLD_DAYS
        self.max_positions = MAX_HOLD_STOCKS
        self.position_ratio = SINGLE_STOCK_POSITION
        
        self.slippage_rate = 0.015 if strategy_type == "打板策略" else 0.005
        self.high_open_fail = 0.5 if strategy_type == "打板策略" else 0.1
        self.commission_rate = COMMISSION_RATE
        self.min_commission = MIN_COMMISSION
        self.stamp_duty = STAMP_TAX_RATE
        
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_capital = []
        self.daily_returns = []
        
        # 数据缓存
        self._limit_df = None
        self._daily_cache = {}
        self._concept_cache = {}
        self._top_list_df = None
        self._hm_detail_df = None
        self._dates = []
        
        logger.info(f"📊 向量化引擎 v7.6 | 策略:{strategy_type} | 资金:{self.initial_capital:,.0f}")
    
    def preload_data(self, data_dir="/data/agents/master/data_all_stocks", 
                     limit_file="/data/agents/master/data/limit_list_d.parquet",
                     data_path="/data/agents/master/data",
                     start_date=None, end_date=None):
        """预加载数据（完整字段修复）"""
        logger.info("预加载数据...")
        t0 = datetime.now()
        
        # ========== 1. 加载涨跌停数据 ==========
        logger.info("加载涨跌停数据...")
        raw_limit = pd.read_parquet(limit_file)
        raw_limit['trade_date'] = raw_limit['trade_date'].astype(str)
        
        # 【关键】字段映射
        self._limit_df = raw_limit.rename(columns={
            'fd_amount': 'order_amount',       # 封单金额
            'float_mv': 'float_market_cap',    # 流通市值
            'open_times': 'break_limit_times', # 炸板次数
            'first_time': 'first_limit_time',  # 首次涨停时间
        })
        
        # 解析连板高度
        def parse_up_stat(x):
            if pd.isna(x): return 0
            s = str(x)
            if '/' in s: return int(s.split('/')[0])
            try: return int(float(s))
            except: return 0
        self._limit_df['up_down_times'] = raw_limit['up_stat'].apply(parse_up_stat)
        
        # 涨停标记
        self._limit_df['is_limit'] = (raw_limit['limit'] == 'U').astype(int)
        self._limit_df['name'] = raw_limit['name'].fillna(raw_limit['ts_code'])
        
        logger.info(f"  涨跌停数据: {len(self._limit_df)}条")
        
        # ========== 2. 加载龙虎榜数据 ==========
        logger.info("加载龙虎榜数据...")
        
        # top_list（机构买卖）
        top_file = os.path.join(data_path, 'top_list.parquet')
        if os.path.exists(top_file):
            self._top_list_df = pd.read_parquet(top_file)
            self._top_list_df['trade_date'] = self._top_list_df['trade_date'].astype(str)
            logger.info(f"  top_list: {len(self._top_list_df)}条")
        else:
            self._top_list_df = pd.DataFrame()
        
        # hm_detail（游资买卖）
        hm_file = os.path.join(data_path, 'hm_detail.parquet')
        if os.path.exists(hm_file):
            self._hm_detail_df = pd.read_parquet(hm_file)
            self._hm_detail_df['trade_date'] = self._hm_detail_df['trade_date'].astype(str)
            logger.info(f"  hm_detail: {len(self._hm_detail_df)}条")
        else:
            self._hm_detail_df = pd.DataFrame()
        
        # ========== 3. 合并龙虎榜数据 ==========
        self._merge_longhu_data()
        
        # ========== 4. 设置默认字段 ==========
        default_fields = {
            'no_reduction': 1,      # 默认无减持
            'no_inquiry': 1,        # 默认无问询
            'is_main_industry': 0,  # 非主线行业
            'concept_count': 1,     # 默认1个概念
        }
        for field, default in default_fields.items():
            if field not in self._limit_df.columns:
                self._limit_df[field] = default
        
        # 日期过滤
        if start_date:
            self._limit_df = self._limit_df[self._limit_df['trade_date'] >= start_date.replace('-', '')]
        if end_date:
            self._limit_df = self._limit_df[self._limit_df['trade_date'] <= end_date.replace('-', '')]
        
        # ========== 5. 加载日线数据 ==========
        logger.info("加载日线数据...")
        for stock_dir in os.listdir(data_dir):
            stock_path = os.path.join(data_dir, stock_dir)
            if os.path.isdir(stock_path):
                daily_path = os.path.join(stock_path, 'daily.parquet')
                if os.path.exists(daily_path):
                    try:
                        df = pd.read_parquet(daily_path)
                        df['trade_date'] = df['trade_date'].astype(str)
                        self._daily_cache[stock_dir] = df
                    except:
                        pass
                
                # 加载概念数据
                concept_path = os.path.join(stock_path, 'concept_detail.parquet')
                if os.path.exists(concept_path):
                    try:
                        concept_df = pd.read_parquet(concept_path)
                        self._concept_cache[stock_dir] = len(concept_df)
                    except:
                        self._concept_cache[stock_dir] = 1
        
        # 更新概念数量
        if self._concept_cache:
            self._limit_df['concept_count'] = self._limit_df['ts_code'].map(
                lambda x: self._concept_cache.get(x, 1)
            )
        
        self._dates = sorted(self._limit_df['trade_date'].unique())
        
        elapsed = (datetime.now() - t0).total_seconds()
        logger.info(f"加载完成: 涨跌停{len(self._limit_df)}条, 日线{len(self._daily_cache)}只, {elapsed:.1f}秒")
        
        # 验证字段
        self._validate_fields()
    
    def _merge_longhu_data(self):
        """合并龙虎榜数据（机构+游资）"""
        # 合并机构数据
        if not self._top_list_df.empty:
            # 按股票+日期汇总机构买卖
            top_agg = self._top_list_df.groupby(['trade_date', 'ts_code']).agg({
                'l_buy': 'sum',      # 机构买入（万元）
                'l_sell': 'sum',     # 机构卖出（万元）
                'net_amount': 'sum'  # 净买入（万元）
            }).reset_index()
            top_agg = top_agg.rename(columns={
                'l_buy': 'inst_buy',
                'l_sell': 'inst_sell',
                'net_amount': 'inst_net'
            })
            
            # 合并到limit_df
            self._limit_df = self._limit_df.merge(
                top_agg, on=['trade_date', 'ts_code'], how='left'
            )
            self._limit_df['inst_buy'] = self._limit_df['inst_buy'].fillna(0)
            self._limit_df['inst_sell'] = self._limit_df['inst_sell'].fillna(0)
            inst_count = (self._limit_df['inst_buy'] > 0).sum()
            logger.info(f"  机构数据已合并，inst_buy>0: {inst_count}条")
        else:
            self._limit_df['inst_buy'] = 0
            self._limit_df['inst_sell'] = 0
        
        # 合并游资数据
        if not self._hm_detail_df.empty:
            hm_agg = self._hm_detail_df.groupby(['trade_date', 'ts_code']).agg({
                'buy_amount': 'sum',
                'sell_amount': 'sum',
                'net_amount': 'sum'
            }).reset_index()
            # 转换为万元
            hm_agg['youzi_buy'] = hm_agg['buy_amount'] / 10000
            hm_agg['youzi_sell'] = hm_agg['sell_amount'] / 10000
            hm_agg['youzi_net'] = hm_agg['net_amount'] / 10000
            
            # 合并到limit_df
            self._limit_df = self._limit_df.merge(
                hm_agg[['trade_date', 'ts_code', 'youzi_buy', 'youzi_sell', 'youzi_net']],
                on=['trade_date', 'ts_code'], how='left'
            )
            self._limit_df['youzi_buy'] = self._limit_df['youzi_buy'].fillna(0)
            self._limit_df['youzi_sell'] = self._limit_df['youzi_sell'].fillna(0)
            youzi_count = (self._limit_df['youzi_buy'] > 0).sum()
            logger.info(f"  游资数据已合并，youzi_buy>0: {youzi_count}条")
        else:
            self._limit_df['youzi_buy'] = 0
            self._limit_df['youzi_sell'] = 0
    
    def _validate_fields(self):
        """验证必要字段"""
        required_fields = [
            'ts_code', 'trade_date', 'name', 'close', 'pct_chg',
            'order_amount', 'float_market_cap', 'turnover_ratio',
            'up_down_times', 'break_limit_times', 'first_limit_time',
            'inst_buy', 'youzi_buy', 'concept_count',
            'no_reduction', 'no_inquiry', 'is_main_industry', 'is_limit'
        ]
        
        missing = [f for f in required_fields if f not in self._limit_df.columns]
        if missing:
            logger.warning(f"⚠️  缺失字段: {missing}")
        else:
            logger.info(f"✅ 所有必要字段已就绪 ({len(required_fields)}个)")
        
        # 统计数据完整性
        sample = self._limit_df[self._limit_df['is_limit'] == 1].head(10)
        if not sample.empty:
            logger.info(f"字段验证（涨停样本）:")
            for col in ['order_amount', 'float_market_cap', 'inst_buy', 'youzi_buy', 'concept_count']:
                if col in sample.columns:
                    val = sample[col].iloc[0]
                    logger.info(f"  {col}: {val}")
    
    def get_trade_dates(self, start_date, end_date):
        s, e = start_date.replace('-', ''), end_date.replace('-', '')
        return [d for d in self._dates if s <= d <= e]
    
    def run(self, trade_dates, data_loader=None):
        """运行回测"""
        random.seed(42)
        logger.info(f"回测开始: {len(trade_dates)}天")
        t0 = datetime.now()
        
        self.cash, self.positions, self.trades = self.initial_capital, {}, []
        self.daily_capital, self.daily_returns = [], []
        stats = {'signals': 0, 'buys': 0, 'fail_limit': 0, 'fail_high': 0}
        
        for i, date in enumerate(trade_dates):
            if (i+1) % 50 == 0:
                logger.info(f"进度: {(i+1)/len(trade_dates)*100:.0f}%")
            
            day_limit = self._limit_df[self._limit_df['trade_date'] == date].copy()
            
            # 卖出检查
            sells = []
            for code, pos in list(self.positions.items()):
                hold_days = i - pos['idx']
                if hold_days >= self.max_hold_days:
                    sells.append((code, '超时'))
                elif code in self._daily_cache:
                    row = self._daily_cache[code][self._daily_cache[code]['trade_date'] == date]
                    if not row.empty:
                        close = row.iloc[0]['close']
                        pnl = (close - pos['cost']) / pos['cost']
                        if pnl <= -self.stop_loss:
                            sells.append((code, '止损'))
                        elif pnl >= self.stop_profit:
                            sells.append((code, '止盈'))
            
            for code, reason in sells:
                if code in self.positions and code in self._daily_cache:
                    row = self._daily_cache[code][self._daily_cache[code]['trade_date'] == date]
                    if not row.empty:
                        self._sell(code, row.iloc[0]['open'], date, reason)
            
            # 选股
            if len(self.positions) < self.max_positions and not day_limit.empty:
                try:
                    filtered = self.strategy.filter(day_limit)
                    if not filtered.empty:
                        scored = self.strategy.score(filtered)
                        stats['signals'] += len(scored)
                        
                        if not scored.empty and i+1 < len(trade_dates):
                            next_date = trade_dates[i+1]
                            for _, sig in scored.head(self.max_positions - len(self.positions)).iterrows():
                                code = sig['ts_code']
                                if code in self.positions or code not in self._daily_cache:
                                    continue
                                
                                next_row = self._daily_cache[code][self._daily_cache[code]['trade_date'] == next_date]
                                if next_row.empty:
                                    continue
                                
                                open_p = next_row.iloc[0]['open']
                                pre_close = next_row.iloc[0].get('pre_close', open_p)
                                pct = (open_p - pre_close) / pre_close if pre_close > 0 else 0
                                
                                stats['buys'] += 1
                                if pct >= 0.095:
                                    stats['fail_limit'] += 1
                                    continue
                                if pct >= 0.05 and random.random() < self.high_open_fail:
                                    stats['fail_high'] += 1
                                    continue
                                
                                buy_price = open_p * (1 + self.slippage_rate)
                                shares = int(min(self.cash*0.95, self.cash*self.position_ratio) / buy_price / 100) * 100
                                if shares < 100:
                                    continue
                                
                                cost = shares * buy_price + max(shares*buy_price*self.commission_rate, self.min_commission)
                                if cost > self.cash:
                                    continue
                                
                                self.cash -= cost
                                self.positions[code] = {'shares': shares, 'cost': buy_price, 'idx': i}
                                self.trades.append({
                                    'date': next_date, 'ts_code': code, 'action': 'buy',
                                    'price': buy_price, 'shares': shares, 
                                    'score': sig.get('total_score', 0),
                                    'inst_buy': sig.get('inst_buy', 0),
                                    'youzi_buy': sig.get('youzi_buy', 0)
                                })
                except Exception as e:
                    logger.debug(f"选股异常: {e}")
            
            # 记录资金
            total = self.cash
            for code, pos in self.positions.items():
                if code in self._daily_cache:
                    row = self._daily_cache[code][self._daily_cache[code]['trade_date'] == date]
                    if not row.empty:
                        total += pos['shares'] * row.iloc[0]['close']
            self.daily_capital.append({'date': date, 'total': total})
            
            if len(self.daily_capital) >= 2:
                prev = self.daily_capital[-2]['total']
                if prev > 0:
                    self.daily_returns.append((total - prev) / prev)
        
        # 清算
        if self.positions and trade_dates:
            last = trade_dates[-1]
            for code in list(self.positions.keys()):
                if code in self._daily_cache:
                    row = self._daily_cache[code][self._daily_cache[code]['trade_date'] == last]
                    if not row.empty:
                        self._sell(code, row.iloc[0]['close'], last, '清算')
        
        elapsed = (datetime.now() - t0).total_seconds()
        
        perf = self._perf()
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.daily_capital[-1]['total'] if self.daily_capital else self.initial_capital,
            'total_return': perf['ret'],
            'annual_return': perf['ann'],
            'max_drawdown': perf['dd'],
            'sharpe_ratio': perf['sharpe'],
            'win_rate': perf['win'],
            'total_trades': len([t for t in self.trades if t['action']=='buy']),
            'trades': self.trades,
            'stats': stats,
            'elapsed': elapsed,
            'speed': elapsed/len(trade_dates) if trade_dates else 0
        }
    
    def _sell(self, code, price, date, reason):
        if code not in self.positions:
            return
        pos = self.positions.pop(code)
        revenue = pos['shares']*price - max(pos['shares']*price*self.commission_rate, self.min_commission) - pos['shares']*price*self.stamp_duty
        self.cash += revenue
        pnl = (price - pos['cost']) * pos['shares']
        self.trades.append({
            'date': date, 'ts_code': code, 'action': 'sell',
            'price': price, 'shares': pos['shares'], 'pnl': pnl, 'reason': reason
        })
    
    def _perf(self):
        if not self.daily_capital:
            return {'ret': 0, 'ann': 0, 'dd': 0, 'sharpe': 0, 'win': 0}
        vals = [d['total'] for d in self.daily_capital]
        ret = (vals[-1] - self.initial_capital) / self.initial_capital
        ann = (1+ret)**(252/len(vals)) - 1 if len(vals) > 0 else 0
        peak, dd = vals[0], 0
        for v in vals:
            if v > peak: peak = v
            d = (peak-v)/peak
            if d > dd: dd = d
        r = pd.Series(self.daily_returns)
        sharpe = r.mean()/r.std()*np.sqrt(252) if len(r) > 0 and r.std() > 0 else 0
        sells = [t for t in self.trades if t['action']=='sell']
        wins = [t for t in sells if t.get('pnl',0) > 0]
        win = len(wins)/len(sells) if sells else 0
        return {'ret': ret, 'ann': ann, 'dd': dd, 'sharpe': sharpe, 'win': win}


if __name__ == "__main__":
    print("✅ VectorBacktestEngine v7.6 OK")