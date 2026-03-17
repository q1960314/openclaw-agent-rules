# ==============================================
# 【优化】示例策略插件 - 打板策略
# ==============================================
# 功能：实现打板策略插件，演示策略插件的完整实现
# 职责：识别强势连板股，生成买卖信号
# ==============================================

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Any, List

from plugins.plugin_base import PluginInfo
from plugins.strategy_plugin import StrategyPlugin, Signal, SignalType, Position

logger = logging.getLogger("quant_system")


class LimitUpStrategyPlugin(StrategyPlugin):
    """
    【优化】打板策略插件实现
    基于原有打板策略逻辑，改造为插件化架构
    
    策略核心：
    1. 识别连板股票（2-4 板）
    2. 检查封板强度（封单金额、封板时间）
    3. 检查资金动向（机构/游资净买入）
    4. 检查行业板块（是否主线）
    5. 生成买入/卖出信号
    """
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        """获取插件元信息"""
        return PluginInfo(
            name="limit_up_strategy",
            version="1.0.0",
            author="quant-system",
            description="打板策略：追涨停板，适合强势股，持仓 1-2 天",
            plugin_type="strategy",
            dependencies=[],  # 无依赖
            config={
                "min_order_ratio": 0.03,  # 最小封单比
                "max_break_times": 1,  # 最大炸板次数
                "link_board_range": [2, 4],  # 连板高度范围
                "exclude_late_board": True,  # 排除尾盘封板
                "stop_loss_rate": 0.06,  # 止损比例
                "stop_profit_rate": 0.12,  # 止盈比例
                "max_hold_days": 2,  # 最大持股天数
            }
        )
    
    def __init__(self, plugin_info: PluginInfo):
        """初始化策略插件"""
        super().__init__(plugin_info)
        
        # 策略专属配置
        self.strategy_config = plugin_info.config.copy()
        
        # 策略状态
        self.current_date = None
        self.market_trend = "normal"
    
    def on_init_strategy(self) -> bool:
        """
        【实现】策略初始化
        加载策略专属配置
        """
        try:
            logger.info("🔧 初始化打板策略插件...")
            
            # 从配置管理器加载配置（如果有的话）
            # 这里使用默认配置
            
            logger.info("✅ 打板策略插件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 打板策略初始化失败：{e}", exc_info=True)
            return False
    
    def on_start_strategy(self) -> bool:
        """
        【实现】策略启动
        启动策略专属逻辑
        """
        try:
            logger.info("🟢 打板策略启动")
            
            # 清空观察列表
            self.watchlist = []
            
            # 重置统计
            self.total_signals = 0
            self.buy_signals = 0
            self.sell_signals = 0
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 打板策略启动失败：{e}", exc_info=True)
            return False
    
    def on_stop_strategy(self) -> bool:
        """
        【实现】策略停止
        清理策略专属资源
        """
        try:
            logger.info("🔴 打板策略停止")
            
            # 清空观察列表
            self.watchlist = []
            
            logger.info("✅ 打板策略停止完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 打板策略停止失败：{e}", exc_info=True)
            return False
    
    def generate_signals(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_positions: Dict[str, Position]
    ) -> List[Signal]:
        """
        【实现】生成交易信号
        策略核心逻辑
        
        :param market_data: 市场数据字典
        :param current_positions: 当前持仓字典
        :return: 信号列表
        """
        signals = []
        
        try:
            # 获取必要的数据
            daily_data = market_data.get('daily', pd.DataFrame())
            top_list = market_data.get('top_list', pd.DataFrame())
            stock_basic = market_data.get('stock_basic', pd.DataFrame())
            
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
            
            # 2. 生成买入信号（筛选新股）
            buy_candidates = self._screen_buy_candidates(daily_data, top_list, stock_basic)
            
            for candidate in buy_candidates:
                buy_signal = self._create_buy_signal(candidate, daily_data)
                if buy_signal:
                    signals.append(buy_signal)
            
            logger.info(f"📊 打板策略生成 {len(signals)} 个信号")
            
        except Exception as e:
            logger.error(f"❌ 打板策略生成信号失败：{e}", exc_info=True)
        
        return signals
    
    def on_bar(self, data: Dict[str, Any]) -> None:
        """
        【实现】K 线回调
        实时更新策略状态
        """
        try:
            # 更新持仓价格
            ts_code = data.get('ts_code')
            price = data.get('close')
            
            if ts_code and price:
                self.update_position_price(ts_code, price)
            
        except Exception as e:
            logger.error(f"❌ 打板策略 K 线回调失败：{e}", exc_info=True)
    
    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """
        【实现】订单成交回调
        更新持仓状态
        """
        try:
            ts_code = order.get('ts_code')
            volume = order.get('volume', 0)
            price = order.get('price', 0)
            direction = order.get('direction', 'buy')
            
            if direction == 'buy':
                # 买入成交，添加持仓
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
                # 卖出成交，移除持仓
                self.remove_position(ts_code)
                self.sell_signals += 1
            
            self.total_signals += 1
            
            logger.info(f"✅ 打板策略订单成交：{ts_code} {direction} {volume}@{price}")
            
        except Exception as e:
            logger.error(f"❌ 打板策略订单回调失败：{e}", exc_info=True)
    
    def risk_check(self, signal: Signal) -> bool:
        """
        【实现】风险检查
        添加打板策略专属风控
        """
        try:
            # 1. 检查是否停牌
            # 2. 检查是否 ST
            # 3. 检查涨跌幅限制
            # 4. 检查流动性
            
            # 示例：检查置信度
            if signal.confidence < 0.6:
                logger.warning(f"⚠️  信号置信度过低：{signal.confidence:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 打板策略风控检查失败：{e}", exc_info=True)
            return False
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """
        【实现】获取策略参数
        返回可调参数用于优化
        """
        return {
            "min_order_ratio": self.strategy_config.get("min_order_ratio", 0.03),
            "max_break_times": self.strategy_config.get("max_break_times", 1),
            "link_board_min": self.strategy_config.get("link_board_range", [2, 4])[0],
            "link_board_max": self.strategy_config.get("link_board_range", [2, 4])[1],
            "stop_loss_rate": self.strategy_config.get("stop_loss_rate", 0.06),
            "stop_profit_rate": self.strategy_config.get("stop_profit_rate", 0.12),
            "max_hold_days": self.strategy_config.get("max_hold_days", 2),
        }
    
    def set_strategy_params(self, params: Dict[str, Any]) -> bool:
        """
        【实现】设置策略参数
        """
        try:
            # 更新配置
            if "min_order_ratio" in params:
                self.strategy_config["min_order_ratio"] = params["min_order_ratio"]
            if "max_break_times" in params:
                self.strategy_config["max_break_times"] = params["max_break_times"]
            if "stop_loss_rate" in params:
                self.strategy_config["stop_loss_rate"] = params["stop_loss_rate"]
            if "stop_profit_rate" in params:
                self.strategy_config["stop_profit_rate"] = params["stop_profit_rate"]
            if "max_hold_days" in params:
                self.strategy_config["max_hold_days"] = params["max_hold_days"]
            
            logger.info(f"✅ 打板策略参数已更新")
            return True
            
        except Exception as e:
            logger.error(f"❌ 打板策略参数设置失败：{e}", exc_info=True)
            return False
    
    # ==================== 策略专属方法 ====================
    
    def _check_sell_condition(
        self,
        ts_code: str,
        position: Position,
        daily_data: pd.DataFrame
    ) -> Signal:
        """
        检查卖出条件
        :return: 卖出信号（不满足返回 None）
        """
        try:
            # 获取该股票的日线数据
            stock_data = daily_data[daily_data['ts_code'] == ts_code]
            
            if stock_data.empty:
                return None
            
            # 获取最新价格
            latest = stock_data.iloc[-1]
            current_price = latest.get('close', position.current_price)
            
            # 更新持仓价格
            position.update_price(current_price)
            
            # 计算收益率
            profit_rate = position.profit_rate
            
            # 1. 止损检查
            stop_loss_rate = self.strategy_config.get("stop_loss_rate", 0.06)
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
            stop_profit_rate = self.strategy_config.get("stop_profit_rate", 0.12)
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
            max_hold_days = self.strategy_config.get("max_hold_days", 2)
            hold_days = (datetime.now() - position.open_date).days
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
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 检查卖出条件失败：{e}", exc_info=True)
            return None
    
    def _screen_buy_candidates(
        self,
        daily_data: pd.DataFrame,
        top_list: pd.DataFrame,
        stock_basic: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        筛选买入候选股票
        :return: 候选股票列表
        """
        candidates = []
        
        try:
            # 示例筛选逻辑（简化版）
            # 实际应使用完整的打板策略逻辑
            
            # 1. 筛选涨停股票
            limit_up_stocks = daily_data[daily_data.get('pct_chg', 0) >= 9.5]
            
            # 2. 筛选连板股票（2-4 板）
            link_board_range = self.strategy_config.get("link_board_range", [2, 4])
            # 这里需要计算连板高度，简化处理
            
            # 3. 加入候选列表
            for _, row in limit_up_stocks.iterrows():
                candidates.append({
                    'ts_code': row.get('ts_code'),
                    'close': row.get('close'),
                    'pct_chg': row.get('pct_chg'),
                })
            
            logger.debug(f"🔍 筛选出 {len(candidates)} 只候选股票")
            
        except Exception as e:
            logger.error(f"❌ 筛选候选股票失败：{e}", exc_info=True)
        
        return candidates
    
    def _create_buy_signal(
        self,
        candidate: Dict[str, Any],
        daily_data: pd.DataFrame
    ) -> Signal:
        """
        创建买入信号
        :return: 买入信号（不满足返回 None）
        """
        try:
            ts_code = candidate.get('ts_code')
            price = candidate.get('close')
            
            # 风险检查
            signal = Signal(
                ts_code=ts_code,
                signal_type=SignalType.BUY,
                price=price,
                timestamp=datetime.now(),
                confidence=0.8,
                reason="打板策略买入信号",
                metadata=candidate
            )
            
            if not self.risk_check(signal):
                return None
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ 创建买入信号失败：{e}", exc_info=True)
            return None
