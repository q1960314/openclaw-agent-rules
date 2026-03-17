# ==============================================
# 【优化】缩量潜伏策略插件
# ==============================================
# 功能：成交量萎缩 + 技术超卖，潜伏等待反弹
# 策略核心：
# 1. 识别成交量萎缩至 20 日均量 50% 以下的股票
# 2. 结合技术指标（MACD 金叉、RSI 超卖）
# 3. 潜伏等待放量上涨
# 4. 止损 5%、止盈 15%
# ==============================================

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from plugins.plugin_base import PluginInfo
from plugins.strategy_plugin import StrategyPlugin, Signal, SignalType, Position

logger = logging.getLogger("quant_system")


class ShrinkVolumeStrategyPlugin(StrategyPlugin):
    """
    【优化】缩量潜伏策略插件
    基于成交量萎缩和技术指标的潜伏策略
    """
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        """获取插件元信息"""
        return PluginInfo(
            name="shrink_volume_strategy",
            version="1.0.0",
            author="quant-system",
            description="缩量潜伏策略：成交量萎缩 + 技术超卖，潜伏等待反弹",
            plugin_type="strategy",
            dependencies=[],
            config={
                "volume_shrink_ratio": 0.50,      # 缩量比例（低于 50%）
                "rsi_oversold": 30,               # RSI 超卖阈值
                "rsi_extreme_oversold": 20,       # RSI 极端超卖（加分项）
                "macd_golden_cross": True,        # 需要 MACD 金叉
                "stop_loss_rate": 0.05,           # 止损 5%
                "stop_profit_rate": 0.15,         # 止盈 15%
                "max_hold_days": 10,              # 最大持仓 10 天
                "min_liquidity": 1e8,             # 最小市值 1 亿
                "min_volume_avg": 1e6,            # 最小日均成交额 100 万
            }
        )
    
    def __init__(self, plugin_info: PluginInfo):
        """初始化策略插件"""
        super().__init__(plugin_info)
        self.strategy_config = plugin_info.config.copy()
        self.current_date = None
    
    def on_init_strategy(self) -> bool:
        """策略初始化"""
        try:
            logger.info("🔧 初始化缩量潜伏策略插件...")
            logger.info("✅ 缩量潜伏策略插件初始化完成")
            return True
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略初始化失败：{e}", exc_info=True)
            return False
    
    def on_start_strategy(self) -> bool:
        """策略启动"""
        try:
            logger.info("🟢 缩量潜伏策略启动")
            self.watchlist = []
            self.total_signals = 0
            self.buy_signals = 0
            self.sell_signals = 0
            return True
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略启动失败：{e}", exc_info=True)
            return False
    
    def on_stop_strategy(self) -> bool:
        """策略停止"""
        try:
            logger.info("🔴 缩量潜伏策略停止")
            self.watchlist = []
            logger.info("✅ 缩量潜伏策略停止完成")
            return True
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略停止失败：{e}", exc_info=True)
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
            
            # 2. 生成买入信号（筛选缩量股）
            buy_candidates = self._screen_shrink_volume_stocks(daily_data)
            
            for candidate in buy_candidates:
                buy_signal = self._create_buy_signal(candidate)
                if buy_signal:
                    signals.append(buy_signal)
            
            logger.info(f"📊 缩量潜伏策略生成 {len(signals)} 个信号")
            
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略生成信号失败：{e}", exc_info=True)
        
        return signals
    
    def on_bar(self, data: Dict[str, Any]) -> None:
        """K 线回调"""
        try:
            ts_code = data.get('ts_code')
            price = data.get('close')
            if ts_code and price:
                self.update_position_price(ts_code, price)
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略 K 线回调失败：{e}", exc_info=True)
    
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
                self.add_position(position)
                self.buy_signals += 1
            elif direction == 'sell':
                self.remove_position(ts_code)
                self.sell_signals += 1
            
            self.total_signals += 1
            logger.info(f"✅ 缩量潜伏策略订单成交：{ts_code} {direction} {volume}@{price}")
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略订单回调失败：{e}", exc_info=True)
    
    def risk_check(self, signal: Signal) -> bool:
        """风险检查"""
        try:
            if signal.confidence < 0.5:
                logger.warning(f"⚠️  信号置信度过低：{signal.confidence:.2f}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略风控检查失败：{e}", exc_info=True)
            return False
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {
            "volume_shrink_ratio": self.strategy_config.get("volume_shrink_ratio", 0.50),
            "rsi_oversold": self.strategy_config.get("rsi_oversold", 30),
            "stop_loss_rate": self.strategy_config.get("stop_loss_rate", 0.05),
            "stop_profit_rate": self.strategy_config.get("stop_profit_rate", 0.15),
            "max_hold_days": self.strategy_config.get("max_hold_days", 10),
        }
    
    def set_strategy_params(self, params: Dict[str, Any]) -> bool:
        """设置策略参数"""
        try:
            for key in ['volume_shrink_ratio', 'rsi_oversold', 'stop_loss_rate', 
                       'stop_profit_rate', 'max_hold_days']:
                if key in params:
                    self.strategy_config[key] = params[key]
            logger.info(f"✅ 缩量潜伏策略参数已更新")
            return True
        except Exception as e:
            logger.error(f"❌ 缩量潜伏策略参数设置失败：{e}", exc_info=True)
            return False
    
    # ==================== 策略专属方法 ====================
    
    def _screen_shrink_volume_stocks(self, daily_data: pd.DataFrame) -> List[Dict]:
        """
        筛选缩量股票
        :param daily_data: 日线数据
        :return: 候选股票列表
        """
        candidates = []
        
        for ts_code in daily_data['ts_code'].unique():
            stock_data = daily_data[daily_data['ts_code'] == ts_code].sort_values('trade_date')
            
            if len(stock_data) < 30:  # 至少 30 天数据
                continue
            
            latest = stock_data.iloc[-1]
            
            # 计算 20 日均量
            avg_volume_20 = stock_data['vol'].rolling(20).mean().iloc[-1]
            current_volume = latest['vol']
            
            if avg_volume_20 == 0:
                continue
            
            # 缩量条件
            volume_ratio = current_volume / avg_volume_20
            if volume_ratio > self.strategy_config['volume_shrink_ratio']:
                continue
            
            # 检查最小成交额
            current_amount = current_volume * latest['close']
            if current_amount < self.strategy_config['min_volume_avg']:
                continue
            
            # RSI 超卖
            rsi = self._calculate_rsi(stock_data['close'], 14)
            if rsi > self.strategy_config['rsi_oversold']:
                continue
            
            # MACD 金叉
            if self.strategy_config['macd_golden_cross']:
                if not self._check_macd_golden_cross(stock_data):
                    continue
            
            # 流动性检查（市值）
            if 'float_shares' in stock_data.columns:
                market_cap = latest['close'] * stock_data['float_shares'].iloc[-1]
                if market_cap < self.strategy_config['min_liquidity']:
                    continue
            
            # 计算综合评分
            score = self._calculate_stock_score(stock_data, volume_ratio, rsi)
            
            candidates.append({
                'ts_code': ts_code,
                'price': latest['close'],
                'volume_ratio': volume_ratio,
                'rsi': rsi,
                'score': score,
            })
        
        # 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:20]  # 返回前 20 只
    
    def _calculate_rsi(self, price: pd.Series, period: int = 14) -> float:
        """计算 RSI 指标"""
        delta = price.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        with pd.option_context('divide_by_zero', 'ignore'):
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _check_macd_golden_cross(self, stock_data: pd.DataFrame) -> bool:
        """检查 MACD 金叉"""
        close = stock_data['close']
        
        if len(close) < 30:
            return False
        
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        # 金叉：MACD 从下向上穿越信号线
        if len(macd) < 2:
            return False
        
        return macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]
    
    def _calculate_stock_score(self, stock_data: pd.DataFrame, volume_ratio: float, rsi: float) -> float:
        """
        计算股票综合评分
        :param stock_data: 股票数据
        :param volume_ratio: 成交量比率
        :param rsi: RSI 值
        :return: 综合评分（0-1）
        """
        score = 0.5  # 基础分
        
        # 缩量程度评分（最多 +0.2）
        if volume_ratio < 0.3:
            score += 0.2
        elif volume_ratio < 0.4:
            score += 0.15
        elif volume_ratio < 0.5:
            score += 0.1
        
        # RSI 超卖程度评分（最多 +0.2）
        if rsi < self.strategy_config['rsi_extreme_oversold']:
            score += 0.2
        elif rsi < self.strategy_config['rsi_oversold']:
            score += 0.1
        
        # 趋势评分（最多 +0.1）
        close = stock_data['close']
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        if current_price > ma5 > ma10:
            score += 0.1  # 多头排列
        
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
        stop_loss_rate = self.strategy_config.get("stop_loss_rate", 0.05)
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
        stop_profit_rate = self.strategy_config.get("stop_profit_rate", 0.15)
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
        max_hold_days = self.strategy_config.get("max_hold_days", 10)
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
        
        # 4. 放量滞涨检查（风险信号）
        avg_volume_5 = stock_data['vol'].rolling(5).mean().iloc[-1]
        current_volume = stock_data['vol'].iloc[-1]
        
        if current_volume > avg_volume_5 * 2 and profit_rate < 0.05:
            logger.info(f"⚠️  放量滞涨：{ts_code} 成交量{current_volume/avg_volume_5:.1f}倍")
            return Signal(
                ts_code=ts_code,
                signal_type=SignalType.SELL,
                price=current_price,
                timestamp=datetime.now(),
                confidence=0.7,
                reason=f"放量滞涨：成交量{current_volume/avg_volume_5:.1f}倍"
            )
        
        return None
    
    def _create_buy_signal(self, candidate: Dict) -> Signal:
        """创建买入信号"""
        confidence = 0.6 + 0.2 * candidate['score']
        
        return Signal(
            ts_code=candidate['ts_code'],
            signal_type=SignalType.BUY,
            price=candidate['price'],
            timestamp=datetime.now(),
            confidence=min(1.0, confidence),
            reason=f"缩量潜伏：成交量{candidate['volume_ratio']:.2%}, RSI={candidate['rsi']:.1f}, 评分{candidate['score']:.2f}"
        )
