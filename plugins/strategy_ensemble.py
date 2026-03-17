# ==============================================
# 【优化】多策略融合引擎
# ==============================================
# 功能：融合多个策略信号，动态调整权重
# 策略核心：
# 1. 各策略独立生成信号
# 2. 根据市场状态动态调整权重
# 3. 加权融合信号
# 4. 输出最终交易信号
# ==============================================

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from plugins.strategy_plugin import StrategyPlugin, Signal, SignalType, Position

logger = logging.getLogger("quant_system")


class StrategyEnsemble:
    """
    【优化】多策略融合引擎
    实现多策略的加权融合和动态权重调整
    """
    
    def __init__(self):
        """初始化融合引擎"""
        self.strategies = {}  # name -> StrategyPlugin
        self.weights = {}  # name -> weight
        self.market_regime = 'normal'  # bull/bear/oscillation
        self.regime_history = []
    
    def register_strategy(self, name: str, strategy: StrategyPlugin, weight: float):
        """
        注册策略
        :param name: 策略名称
        :param strategy: 策略实例
        :param weight: 初始权重
        """
        self.strategies[name] = strategy
        self.weights[name] = weight
        logger.info(f"✅ 注册策略：{name}, 权重：{weight:.2f}")
    
    def set_market_regime(self, regime: str):
        """
        设置市场状态
        :param regime: 市场状态（bull/bear/oscillation）
        """
        if regime not in ['bull', 'bear', 'oscillation']:
            logger.warning(f"⚠️  未知市场状态：{regime}, 使用默认值 normal")
            regime = 'normal'
        
        old_regime = self.market_regime
        self.market_regime = regime
        
        if old_regime != regime:
            logger.info(f"📊 市场状态变更：{old_regime} -> {regime}")
            self._adjust_weights()
        
        # 记录历史
        self.regime_history.append({
            'date': datetime.now(),
            'regime': regime
        })
        
        # 保留最近 100 条记录
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
    
    def _adjust_weights(self):
        """根据市场状态动态调整权重"""
        if self.market_regime == 'bull':
            # 牛市：提高打板策略权重（进攻型）
            self.weights = {
                'limit_up': 0.6,
                'shrink_volume': 0.2,
                'sector_rotation': 0.2
            }
            logger.info("🐂 牛市模式：提高打板策略权重")
            
        elif self.market_regime == 'bear':
            # 熊市：提高防御型策略权重
            self.weights = {
                'limit_up': 0.1,
                'shrink_volume': 0.5,
                'sector_rotation': 0.4
            }
            logger.info("🐻 熊市模式：提高防御策略权重")
            
        elif self.market_regime == 'oscillation':
            # 震荡市：均衡配置
            self.weights = {
                'limit_up': 0.3,
                'shrink_volume': 0.4,
                'sector_rotation': 0.3
            }
            logger.info("📊 震荡市模式：均衡配置")
        
        # 归一化权重
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for name in self.weights:
                self.weights[name] /= total_weight
        
        logger.info(f"📊 权重调整完成：{self.weights}")
    
    def detect_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> str:
        """
        检测市场状态
        :param market_data: 市场数据
        :return: 市场状态（bull/bear/oscillation）
        """
        try:
            daily_data = market_data.get('daily', pd.DataFrame())
            
            if daily_data.empty:
                return 'normal'
            
            # 计算市场宽度（上涨家数/下跌家数）
            if 'pct_change' in daily_data.columns:
                latest_date = daily_data['trade_date'].max()
                latest_data = daily_data[daily_data['trade_date'] == latest_date]
                
                up_count = (latest_data['pct_change'] > 0).sum()
                down_count = (latest_data['pct_change'] < 0).sum()
                
                if up_count + down_count > 0:
                    width_ratio = up_count / (up_count + down_count)
                    
                    # 判断市场状态
                    if width_ratio > 0.7:
                        return 'bull'
                    elif width_ratio < 0.3:
                        return 'bear'
                    else:
                        return 'oscillation'
            
            # 使用指数均线判断
            if 'close' in daily_data.columns:
                # 简化：用平均价格代表市场
                avg_price = daily_data.groupby('trade_date')['close'].mean().sort_index()
                
                if len(avg_price) < 60:
                    return 'normal'
                
                ma20 = avg_price.rolling(20).mean().iloc[-1]
                ma60 = avg_price.rolling(60).mean().iloc[-1]
                current_price = avg_price.iloc[-1]
                
                if current_price > ma20 > ma60:
                    return 'bull'
                elif current_price < ma20 < ma60:
                    return 'bear'
                else:
                    return 'oscillation'
            
            return 'normal'
            
        except Exception as e:
            logger.error(f"❌ 市场状态检测失败：{e}", exc_info=True)
            return 'normal'
    
    def generate_signals(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_positions: Dict[str, Position]
    ) -> List[Signal]:
        """
        融合多策略信号
        :param market_data: 市场数据
        :param current_positions: 当前持仓
        :return: 融合后的信号列表
        """
        try:
            # 自动检测市场状态
            detected_regime = self.detect_market_regime(market_data)
            self.set_market_regime(detected_regime)
            
            all_signals = {}  # ts_code -> {strategy_name: signal}
            
            # 1. 各策略独立生成信号
            for name, strategy in self.strategies.items():
                try:
                    weight = self.weights.get(name, 0.1)
                    logger.info(f"📊 策略 {name} 生成信号 (权重：{weight:.2f})...")
                    
                    signals = strategy.generate_signals(market_data, current_positions)
                    
                    for signal in signals:
                        if signal.ts_code not in all_signals:
                            all_signals[signal.ts_code] = {}
                        all_signals[signal.ts_code][name] = signal
                    
                    logger.info(f"✅ 策略 {name} 生成 {len(signals)} 个信号")
                    
                except Exception as e:
                    logger.error(f"❌ 策略 {name} 生成信号失败：{e}", exc_info=True)
            
            # 2. 融合信号
            final_signals = []
            
            for ts_code, strategy_signals in all_signals.items():
                weighted_score = 0
                total_weight = 0
                primary_signal = None
                max_confidence = 0
                
                for strategy_name, signal in strategy_signals.items():
                    weight = self.weights.get(strategy_name, 0.1)
                    weighted_score += signal.confidence * weight
                    total_weight += weight
                    
                    # 选择置信度最高的信号作为主信号
                    if signal.confidence > max_confidence:
                        max_confidence = signal.confidence
                        primary_signal = signal
                
                # 归一化
                if total_weight > 0:
                    weighted_score /= total_weight
                
                # 阈值过滤（卖出信号阈值更低）
                threshold = 0.5 if primary_signal.signal_type == SignalType.SELL else 0.6
                
                if weighted_score > threshold and primary_signal:
                    # 创建融合信号
                    fused_signal = Signal(
                        ts_code=ts_code,
                        signal_type=primary_signal.signal_type,
                        price=primary_signal.price,
                        timestamp=datetime.now(),
                        confidence=weighted_score,
                        reason=f"多策略融合：{', '.join(strategy_signals.keys())}",
                        metadata={
                            'individual_signals': {
                                k: {'confidence': v.confidence, 'reason': v.reason}
                                for k, v in strategy_signals.items()
                            },
                            'weights': {k: self.weights.get(k, 0) for k in strategy_signals.keys()},
                            'market_regime': self.market_regime,
                        }
                    )
                    final_signals.append(fused_signal)
            
            logger.info(f"📊 多策略融合完成，生成 {len(final_signals)} 个最终信号")
            return final_signals
            
        except Exception as e:
            logger.error(f"❌ 多策略融合失败：{e}", exc_info=True)
            return []
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """获取各策略表现"""
        performance = {}
        
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'total_signals'):
                performance[name] = {
                    'weight': self.weights.get(name, 0),
                    'total_signals': strategy.total_signals,
                    'buy_signals': getattr(strategy, 'buy_signals', 0),
                    'sell_signals': getattr(strategy, 'sell_signals', 0),
                }
        
        return performance
    
    def optimize_weights(self, historical_returns: Dict[str, float]):
        """
        根据历史收益优化权重（简化实现）
        :param historical_returns: 各策略历史收益率
        """
        try:
            # 计算总收益
            total_return = sum(historical_returns.values())
            
            if total_return <= 0:
                logger.warning("⚠️  所有策略历史收益为负，使用均衡权重")
                return
            
            # 根据收益比例分配权重
            new_weights = {}
            for name, ret in historical_returns.items():
                if ret > 0:
                    new_weights[name] = ret / total_return
                else:
                    new_weights[name] = 0.05  # 最小权重
            
            # 归一化
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                for name in new_weights:
                    new_weights[name] /= total_weight
            
            self.weights = new_weights
            logger.info(f"✅ 权重优化完成：{self.weights}")
            
        except Exception as e:
            logger.error(f"❌ 权重优化失败：{e}", exc_info=True)


class DynamicRiskManager:
    """
    【优化】动态风控管理器
    实现动态止损/止盈/仓位管理
    """
    
    def __init__(self):
        """初始化风控管理器"""
        self.base_stop_loss = 0.06
        self.base_stop_profit = 0.12
        self.base_position = 0.2  # 基础仓位 20%
        self.account_drawdown = 0.0
        self.market_volatility = 0.02
    
    def set_account_drawdown(self, drawdown: float):
        """设置账户回撤"""
        self.account_drawdown = drawdown
        logger.info(f"📊 账户回撤：{drawdown:.2%}")
    
    def set_market_volatility(self, volatility: float):
        """设置市场波动率"""
        self.market_volatility = volatility
        logger.info(f"📊 市场波动率：{volatility:.2%}")
    
    def calculate_dynamic_stop_loss(self, stock_volatility: float) -> float:
        """
        动态止损：根据波动率调整
        :param stock_volatility: 个股波动率
        :return: 动态止损率
        """
        # 波动率大时放宽止损，避免被洗盘
        vol_ratio = stock_volatility / self.market_volatility if self.market_volatility > 0 else 1
        
        dynamic_stop = self.base_stop_loss * (1 + 0.5 * (vol_ratio - 1))
        
        # 限制在 3%-15%
        dynamic_stop = max(0.03, min(0.15, dynamic_stop))
        
        logger.debug(f"📊 动态止损：基础{self.base_stop_loss:.2%}, 波动率比{vol_ratio:.2f}, 结果{dynamic_stop:.2%}")
        return dynamic_stop
    
    def calculate_dynamic_stop_profit(self, profit_rate: float, trend_strength: float) -> float:
        """
        动态止盈：根据盈利和趋势强度调整
        :param profit_rate: 当前收益率
        :param trend_strength: 趋势强度（0-1）
        :return: 动态止盈率
        """
        if profit_rate > 0.20 and trend_strength > 0.8:
            # 盈利高且趋势强，让利润奔跑
            return 0.99  # 几乎不止盈
        elif profit_rate > 0.10:
            return self.base_stop_profit * 1.5  # 提高止盈点
        else:
            return self.base_stop_profit
    
    def calculate_dynamic_position(self, signal_confidence: float, market_regime: str) -> float:
        """
        动态仓位：根据信号置信度、市场状态、回撤调整
        :param signal_confidence: 信号置信度
        :param market_regime: 市场状态
        :return: 动态仓位比例
        """
        base = self.base_position
        
        # 信号置信度调整
        confidence_factor = signal_confidence * 1.5  # 高置信度提高仓位
        
        # 市场状态调整
        regime_factor = {
            'bull': 1.2,
            'bear': 0.5,
            'oscillation': 0.8,
            'normal': 1.0
        }.get(market_regime, 1.0)
        
        # 回撤调整（回撤大时降低仓位）
        drawdown_factor = max(0.5, 1 - self.account_drawdown * 2)
        
        dynamic_position = base * confidence_factor * regime_factor * drawdown_factor
        
        # 限制在 5%-50%
        dynamic_position = max(0.05, min(0.50, dynamic_position))
        
        logger.debug(f"📊 动态仓位：基础{base:.2%}, 置信度{confidence_factor:.2f}, "
                    f"市场{regime_factor:.2f}, 回撤{drawdown_factor:.2f}, 结果{dynamic_position:.2%}")
        return dynamic_position
    
    def risk_check(self, signal: Signal, position: Optional[Position] = None) -> bool:
        """
        综合风控检查
        :param signal: 交易信号
        :param position: 持仓信息（可选）
        :return: 是否通过风控
        """
        try:
            # 1. 置信度检查
            if signal.confidence < 0.5:
                logger.warning(f"⚠️  信号置信度过低：{signal.confidence:.2f}")
                return False
            
            # 2. 账户回撤检查
            if self.account_drawdown > 0.20:
                logger.warning(f"⚠️  账户回撤过大：{self.account_drawdown:.2%}, 停止交易")
                return False
            
            # 3. 持仓集中度检查（如果有持仓信息）
            if position:
                # 单一股票仓位不超过 30%
                # 这里需要根据实际持仓计算
                pass
            
            # 4. 市场极端情况检查
            if self.market_volatility > 0.05:
                logger.warning(f"⚠️  市场波动率过高：{self.market_volatility:.2%}, 谨慎交易")
                # 可以降低仓位，但不完全禁止
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 风控检查失败：{e}", exc_info=True)
            return False
