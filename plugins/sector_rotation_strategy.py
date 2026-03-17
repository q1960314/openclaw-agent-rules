# ==============================================
# 【优化】板块轮动策略插件
# ==============================================
# 功能：监测行业板块资金流向，提前布局轮动板块
# 策略核心：
# 1. 监测行业板块资金流向
# 2. 识别轮动规律（3-5 天周期）
# 3. 提前布局下一轮动板块
# 4. 动态调整板块权重
# ==============================================

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from plugins.plugin_base import PluginInfo
from plugins.strategy_plugin import StrategyPlugin, Signal, SignalType, Position

logger = logging.getLogger("quant_system")


class SectorRotationStrategyPlugin(StrategyPlugin):
    """
    【优化】板块轮动策略插件
    基于板块动量和资金流向的轮动策略
    """
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        """获取插件元信息"""
        return PluginInfo(
            name="sector_rotation_strategy",
            version="1.0.0",
            author="quant-system",
            description="板块轮动策略：监测资金流向，提前布局轮动板块",
            plugin_type="strategy",
            dependencies=[],
            config={
                "rotation_period": 4,             # 轮动周期（天）
                "min_sector_strength": 0.6,       # 最小板块强度
                "top_n_sectors": 3,               # 选择前 N 个板块
                "top_n_stocks_per_sector": 3,     # 每个板块选 N 只股票
                "stop_loss_rate": 0.08,           # 止损 8%
                "stop_profit_rate": 0.20,         # 止盈 20%
                "max_hold_days": 7,               # 最大持仓 7 天
                "min_market_cap": 5e8,            # 最小市值 5 亿
            }
        )
    
    def __init__(self, plugin_info: PluginInfo):
        """初始化策略插件"""
        super().__init__(plugin_info)
        self.strategy_config = plugin_info.config.copy()
        self.sector_momentum = {}
        self.sector_history = []  # 板块历史表现
        self.current_date = None
    
    def on_init_strategy(self) -> bool:
        """策略初始化"""
        try:
            logger.info("🔧 初始化板块轮动策略插件...")
            logger.info("✅ 板块轮动策略插件初始化完成")
            return True
        except Exception as e:
            logger.error(f"❌ 板块轮动策略初始化失败：{e}", exc_info=True)
            return False
    
    def on_start_strategy(self) -> bool:
        """策略启动"""
        try:
            logger.info("🟢 板块轮动策略启动")
            self.watchlist = []
            self.total_signals = 0
            self.buy_signals = 0
            self.sell_signals = 0
            self.sector_momentum = {}
            return True
        except Exception as e:
            logger.error(f"❌ 板块轮动策略启动失败：{e}", exc_info=True)
            return False
    
    def on_stop_strategy(self) -> bool:
        """策略停止"""
        try:
            logger.info("🔴 板块轮动策略停止")
            self.sector_momentum = {}
            self.sector_history = []
            logger.info("✅ 板块轮动策略停止完成")
            return True
        except Exception as e:
            logger.error(f"❌ 板块轮动策略停止失败：{e}", exc_info=True)
            return False
    
    def generate_signals(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_positions: Dict[str, Position]
    ) -> List[Signal]:
        """
        生成交易信号
        :param market_data: 市场数据字典
        :param current_positions: 当前持仓字典
        :return: 信号列表
        """
        signals = []
        
        try:
            daily_data = market_data.get('daily', pd.DataFrame())
            sector_data = market_data.get('sector', pd.DataFrame())
            
            if daily_data.empty:
                logger.warning("⚠️  缺少日线数据，无法生成信号")
                return signals
            
            # 更新当前日期
            if 'trade_date' in daily_data.columns:
                self.current_date = daily_data['trade_date'].max()
            
            # 1. 生成卖出信号（检查持仓）
            for ts_code, position in current_positions.items():
                sell_signal = self._check_sell_condition(ts_code, position, daily_data)
                if sell_signal:
                    signals.append(sell_signal)
            
            # 2. 计算板块动量
            self._calculate_sector_momentum(sector_data)
            
            # 3. 生成买入信号（选择强势板块中的个股）
            buy_candidates = self._screen_sector_leaders(daily_data, sector_data)
            
            for candidate in buy_candidates:
                buy_signal = self._create_buy_signal(candidate)
                if buy_signal:
                    signals.append(buy_signal)
            
            logger.info(f"📊 板块轮动策略生成 {len(signals)} 个信号")
            
        except Exception as e:
            logger.error(f"❌ 板块轮动策略生成信号失败：{e}", exc_info=True)
        
        return signals
    
    def on_bar(self, data: Dict[str, Any]) -> None:
        """K 线回调"""
        try:
            ts_code = data.get('ts_code')
            price = data.get('close')
            if ts_code and price:
                self.update_position_price(ts_code, price)
        except Exception as e:
            logger.error(f"❌ 板块轮动策略 K 线回调失败：{e}", exc_info=True)
    
    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """订单成交回调"""
        try:
            ts_code = order.get('ts_code')
            volume = order.get('volume', 0)
            price = order.get('price', 0)
            direction = order.get('direction', 'buy')
            
            if direction == 'buy':
                position = Position(
                    ts_code=ts_code,
                    volume=volume,
                    avg_cost=price,
                    current_price=price,
                    open_date=datetime.now()
                )
                # 添加板块信息
                if hasattr(position, 'metadata'):
                    position.metadata['sector'] = order.get('sector', '')
                self.add_position(position)
                self.buy_signals += 1
            elif direction == 'sell':
                self.remove_position(ts_code)
                self.sell_signals += 1
            
            self.total_signals += 1
            logger.info(f"✅ 板块轮动策略订单成交：{ts_code} {direction} {volume}@{price}")
        except Exception as e:
            logger.error(f"❌ 板块轮动策略订单回调失败：{e}", exc_info=True)
    
    def risk_check(self, signal: Signal) -> bool:
        """风险检查"""
        try:
            if signal.confidence < 0.5:
                logger.warning(f"⚠️  信号置信度过低：{signal.confidence:.2f}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ 板块轮动策略风控检查失败：{e}", exc_info=True)
            return False
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {
            "rotation_period": self.strategy_config.get("rotation_period", 4),
            "min_sector_strength": self.strategy_config.get("min_sector_strength", 0.6),
            "top_n_sectors": self.strategy_config.get("top_n_sectors", 3),
            "stop_loss_rate": self.strategy_config.get("stop_loss_rate", 0.08),
            "stop_profit_rate": self.strategy_config.get("stop_profit_rate", 0.20),
            "max_hold_days": self.strategy_config.get("max_hold_days", 7),
        }
    
    def set_strategy_params(self, params: Dict[str, Any]) -> bool:
        """设置策略参数"""
        try:
            for key in ['rotation_period', 'min_sector_strength', 'top_n_sectors',
                       'stop_loss_rate', 'stop_profit_rate', 'max_hold_days']:
                if key in params:
                    self.strategy_config[key] = params[key]
            logger.info(f"✅ 板块轮动策略参数已更新")
            return True
        except Exception as e:
            logger.error(f"❌ 板块轮动策略参数设置失败：{e}", exc_info=True)
            return False
    
    # ==================== 策略专属方法 ====================
    
    def _calculate_sector_momentum(self, sector_data: pd.DataFrame):
        """
        计算板块动量
        :param sector_data: 板块数据
        """
        if sector_data.empty or 'sector_name' not in sector_data.columns:
            logger.warning("⚠️  缺少板块数据")
            return
        
        self.sector_momentum = {}
        
        for sector_name in sector_data['sector_name'].unique():
            sector_df = sector_data[sector_data['sector_name'] == sector_name].sort_values('trade_date')
            
            if len(sector_df) < self.strategy_config['rotation_period'] * 2:
                continue
            
            # 计算 N 日收益率
            returns = sector_df['close'].pct_change(self.strategy_config['rotation_period'])
            
            # 计算成交量趋势
            volume_trend = sector_df['vol'].rolling(5).mean().pct_change()
            
            # 计算资金流入（简化：用成交量和价格变化估算）
            price_change = sector_df['close'].pct_change()
            volume_change = sector_df['vol'].pct_change()
            money_flow = (price_change * volume_change).rolling(5).mean()
            
            self.sector_momentum[sector_name] = {
                'return': returns.iloc[-1] if not returns.empty or not pd.isna(returns.iloc[-1]) else 0,
                'volume_trend': volume_trend.iloc[-1] if not volume_trend.empty or not pd.isna(volume_trend.iloc[-1]) else 0,
                'money_flow': money_flow.iloc[-1] if not money_flow.empty or not pd.isna(money_flow.iloc[-1]) else 0,
                'strength': 0,  # 待计算
            }
        
        # 计算综合强度
        if not self.sector_momentum:
            return
        
        # 归一化处理
        returns = [m['return'] for m in self.sector_momentum.values()]
        max_return = max(returns) if returns else 1
        min_return = min(returns) if returns else -1
        return_range = max_return - min_return if max_return != min_return else 1
        
        for sector_name in self.sector_momentum:
            momentum = self.sector_momentum[sector_name]
            
            # 归一化收益率（0-1）
            norm_return = (momentum['return'] - min_return) / return_range
            
            # 综合强度：60% 收益率 + 20% 成交量趋势 + 20% 资金流
            momentum['strength'] = (
                0.6 * norm_return +
                0.2 * max(0, min(1, momentum['volume_trend'] + 0.5)) +
                0.2 * max(0, min(1, momentum['money_flow'] + 0.5))
            )
        
        # 记录历史
        self.sector_history.append({
            'date': self.current_date,
            'momentum': self.sector_momentum.copy()
        })
        
        # 保留最近 30 天历史
        if len(self.sector_history) > 30:
            self.sector_history = self.sector_history[-30:]
        
        logger.info(f"📊 板块动量计算完成，共 {len(self.sector_momentum)} 个板块")
    
    def _screen_sector_leaders(self, daily_data: pd.DataFrame, sector_data: pd.DataFrame) -> List[Dict]:
        """
        筛选板块龙头股
        :param daily_data: 个股日线数据
        :param sector_data: 板块数据
        :return: 候选股票列表
        """
        candidates = []
        
        # 选择前 N 个强势板块
        top_sectors = sorted(
            self.sector_momentum.items(),
            key=lambda x: x[1]['strength'],
            reverse=True
        )[:self.strategy_config['top_n_sectors']]
        
        logger.info(f"🏆 强势板块：{[s[0] for s in top_sectors]}")
        
        for sector_name, momentum in top_sectors:
            if momentum['strength'] < self.strategy_config['min_sector_strength']:
                logger.info(f"⚠️  板块 {sector_name} 强度不足：{momentum['strength']:.2f}")
                continue
            
            # 获取该板块的成分股（简化处理）
            # 实际应用中需要从板块成分表获取
            sector_stocks = self._get_sector_stocks(sector_name, sector_data, daily_data)
            
            if not sector_stocks:
                continue
            
            # 选择板块内最强的股票
            for ts_code, stock_data in sector_stocks.items():
                if len(stock_data) < 20:
                    continue
                
                latest = stock_data.iloc[-1]
                
                # 计算个股动量
                stock_return = stock_data['close'].pct_change(self.strategy_config['rotation_period']).iloc[-1]
                
                # 计算相对强度
                sector_return = momentum['return']
                relative_strength = stock_return - sector_return
                
                # 计算综合评分
                score = self._calculate_stock_score(stock_data, relative_strength)
                
                candidates.append({
                    'ts_code': ts_code,
                    'price': latest['close'],
                    'sector': sector_name,
                    'sector_strength': momentum['strength'],
                    'stock_return': stock_return if not pd.isna(stock_return) else 0,
                    'relative_strength': relative_strength,
                    'score': score,
                })
        
        # 按评分排序，每个板块选前 N 只
        candidates.sort(key=lambda x: (x['sector'], x['score']), reverse=True)
        
        # 每个板块选前 N 只
        final_candidates = []
        sector_count = {}
        for candidate in candidates:
            sector = candidate['sector']
            sector_count[sector] = sector_count.get(sector, 0)
            if sector_count[sector] < self.strategy_config['top_n_stocks_per_sector']:
                final_candidates.append(candidate)
                sector_count[sector] += 1
        
        return final_candidates
    
    def _get_sector_stocks(self, sector_name: str, sector_data: pd.DataFrame, 
                          daily_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        获取板块成分股（简化实现）
        实际应用中需要从板块成分表获取
        """
        # 简化处理：假设 sector_data 包含个股信息
        # 实际应该从专门的板块成分表获取
        stocks = {}
        
        # 这里需要根据实际数据结构调整
        # 示例：从 daily_data 中筛选（实际应该有板块成分映射表）
        for ts_code in daily_data['ts_code'].unique():
            stock_data = daily_data[daily_data['ts_code'] == ts_code].sort_values('trade_date')
            
            # 检查市值
            if 'float_shares' in stock_data.columns:
                market_cap = stock_data['close'].iloc[-1] * stock_data['float_shares'].iloc[-1]
                if market_cap < self.strategy_config['min_market_cap']:
                    continue
            
            stocks[ts_code] = stock_data
        
        return stocks
    
    def _calculate_stock_score(self, stock_data: pd.DataFrame, relative_strength: float) -> float:
        """
        计算个股综合评分
        :param stock_data: 个股数据
        :param relative_strength: 相对强度
        :return: 综合评分（0-1）
        """
        score = 0.5  # 基础分
        
        # 相对强度评分（最多 +0.3）
        if relative_strength > 0.05:
            score += 0.3
        elif relative_strength > 0.02:
            score += 0.2
        elif relative_strength > 0:
            score += 0.1
        
        # 趋势评分（最多 +0.2）
        close = stock_data['close']
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        if current_price > ma5 > ma10 > ma20:
            score += 0.2  # 完美多头排列
        elif current_price > ma5 > ma10:
            score += 0.15
        elif current_price > ma5:
            score += 0.1
        
        # 成交量评分（最多 +0.1）
        avg_volume_5 = stock_data['vol'].rolling(5).mean().iloc[-1]
        avg_volume_20 = stock_data['vol'].rolling(20).mean().iloc[-1]
        
        if avg_volume_5 > avg_volume_20:
            score += 0.1  # 放量
        
        return min(1.0, score)
    
    def _check_sell_condition(self, ts_code: str, position: Position, daily_data: pd.DataFrame) -> Optional[Signal]:
        """
        检查卖出条件
        :return: 卖出信号（不满足返回 None）
        """
        stock_data = daily_data[daily_data['ts_code'] == ts_code]
        
        if stock_data.empty:
            return None
        
        current_price = stock_data.iloc[-1]['close']
        position.update_price(current_price)
        
        profit_rate = position.profit_rate
        hold_days = (datetime.now() - position.open_date).days
        
        # 1. 止损检查
        stop_loss_rate = self.strategy_config.get("stop_loss_rate", 0.08)
        if profit_rate <= -stop_loss_rate:
            logger.info(f"🛑 触发止损：{ts_code} 收益率 {profit_rate:.2%}")
            return Signal(
                ts_code=ts_code,
                signal_type=SignalType.SELL,
                price=current_price,
                timestamp=datetime.now(),
                confidence=1.0,
                reason=f"止损：收益率 {profit_rate:.2%} <= {-stop_loss_rate:.2%}"
            )
        
        # 2. 止盈检查
        stop_profit_rate = self.strategy_config.get("stop_profit_rate", 0.20)
        if profit_rate >= stop_profit_rate:
            logger.info(f"✅ 触发止盈：{ts_code} 收益率 {profit_rate:.2%}")
            return Signal(
                ts_code=ts_code,
                signal_type=SignalType.SELL,
                price=current_price,
                timestamp=datetime.now(),
                confidence=0.9,
                reason=f"止盈：收益率 {profit_rate:.2%} >= {stop_profit_rate:.2%}"
            )
        
        # 3. 超期检查
        max_hold_days = self.strategy_config.get("max_hold_days", 7)
        if hold_days >= max_hold_days:
            logger.info(f"⏰ 超期卖出：{ts_code} 持仓 {hold_days} 天")
            return Signal(
                ts_code=ts_code,
                signal_type=SignalType.SELL,
                price=current_price,
                timestamp=datetime.now(),
                confidence=0.8,
                reason=f"超期：持仓 {hold_days} 天 >= {max_hold_days} 天"
            )
        
        # 4. 板块走弱检查
        sector = getattr(position, 'sector', None)
        if sector and sector in self.sector_momentum:
            sector_strength = self.sector_momentum[sector]['strength']
            if sector_strength < 0.4:
                logger.info(f"⚠️  板块走弱：{ts_code} 所在板块强度 {sector_strength:.2f}")
                return Signal(
                    ts_code=ts_code,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=0.7,
                    reason=f"板块走弱：强度 {sector_strength:.2f}"
                )
        
        # 5. 跌破均线检查
        ma20 = stock_data['close'].rolling(20).mean().iloc[-1]
        if current_price < ma20:
            logger.info(f"⚠️  跌破 20 日线：{ts_code}")
            return Signal(
                ts_code=ts_code,
                signal_type=SignalType.SELL,
                price=current_price,
                timestamp=datetime.now(),
                confidence=0.6,
                reason=f"跌破 20 日线：{current_price:.2f} < {ma20:.2f}"
            )
        
        return None
    
    def _create_buy_signal(self, candidate: Dict) -> Signal:
        """创建买入信号"""
        confidence = 0.5 + 0.3 * candidate['score'] + 0.2 * candidate['sector_strength']
        
        return Signal(
            ts_code=candidate['ts_code'],
            signal_type=SignalType.BUY,
            price=candidate['price'],
            timestamp=datetime.now(),
            confidence=min(1.0, confidence),
            reason=f"板块轮动：{candidate['sector']} 强度{candidate['sector_strength']:.2f}, 评分{candidate['score']:.2f}"
        )
