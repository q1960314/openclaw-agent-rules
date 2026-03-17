# ==============================================
# 【优化】策略插件接口 - strategy_plugin.py
# ==============================================
# 功能：定义策略插件的抽象接口，规范策略实现
# 职责：策略信号生成、持仓管理、风险控制、回测支持
# ==============================================

from abc import abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import logging
import time
from datetime import datetime

from .plugin_base import PluginBase, PluginInfo, PluginState

logger = logging.getLogger("quant_system")


class SignalType:
    """
    【优化】信号类型枚举
    定义交易信号的类型
    """
    BUY = "buy"              # 买入信号
    SELL = "sell"            # 卖出信号
    HOLD = "hold"            # 持有信号
    WATCH = "watch"          # 观察信号（关注但不动作）


class Signal:
    """
    【优化】交易信号类
    封装策略生成的交易信号
    """
    
    def __init__(
        self,
        ts_code: str,
        signal_type: str,
        price: float,
        timestamp: datetime,
        confidence: float = 1.0,
        reason: str = "",
        metadata: Dict[str, Any] = None
    ):
        """
        初始化交易信号
        :param ts_code: 股票代码
        :param signal_type: 信号类型（buy/sell/hold/watch）
        :param price: 信号价格
        :param timestamp: 信号时间
        :param confidence: 置信度（0-1）
        :param reason: 信号原因
        :param metadata: 附加元数据
        """
        self.ts_code = ts_code
        self.signal_type = signal_type
        self.price = price
        self.timestamp = timestamp
        self.confidence = confidence
        self.reason = reason
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ts_code': self.ts_code,
            'signal_type': self.signal_type,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'reason': self.reason,
            'metadata': self.metadata,
        }
    
    def __repr__(self) -> str:
        return f"Signal({self.ts_code}, {self.signal_type}, {self.price}, {self.confidence:.2f})"


class Position:
    """
    【优化】持仓信息类
    封装当前持仓状态
    """
    
    def __init__(
        self,
        ts_code: str,
        volume: int,
        avg_cost: float,
        current_price: float,
        open_date: datetime
    ):
        """
        初始化持仓信息
        :param ts_code: 股票代码
        :param volume: 持仓数量
        :param avg_cost: 平均成本
        :param current_price: 当前价格
        :param open_date: 开仓日期
        """
        self.ts_code = ts_code
        self.volume = volume
        self.avg_cost = avg_cost
        self.current_price = current_price
        self.open_date = open_date
        self.profit_rate = (current_price - avg_cost) / avg_cost if avg_cost > 0 else 0
    
    def update_price(self, price: float) -> None:
        """更新当前价格"""
        self.current_price = price
        self.profit_rate = (price - self.avg_cost) / self.avg_cost if self.avg_cost > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ts_code': self.ts_code,
            'volume': self.volume,
            'avg_cost': self.avg_cost,
            'current_price': self.current_price,
            'open_date': self.open_date.isoformat(),
            'profit_rate': self.profit_rate,
        }


class StrategyPlugin(PluginBase):
    """
    【优化】策略插件基类
    所有策略插件必须继承此类并实现核心方法
    
    设计原则：
    1. 接口统一：所有策略提供一致的方法签名
    2. 插件化：支持动态加载/卸载策略
    3. 可扩展：新增策略只需继承实现，不影响现有代码
    4. 回测友好：支持回测模式和实盘模式切换
    
    策略生命周期：
    加载 → 初始化 → 激活 → [生成信号] → 停用 → 卸载
    """
    
    def __init__(self, plugin_info: PluginInfo):
        """
        初始化策略插件
        :param plugin_info: 插件元信息
        """
        super().__init__(plugin_info)
        
        # 策略配置
        self.strategy_config: Dict[str, Any] = {}
        
        # 当前持仓
        self.positions: Dict[str, Position] = {}
        
        # 待买入股票池
        self.watchlist: List[str] = []
        
        # 回测模式标志
        self.backtest_mode = False
        
        # 策略统计
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
    
    # ==================== 抽象方法（必须实现） ====================
    
    @abstractmethod
    def generate_signals(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_positions: Dict[str, Position]
    ) -> List[Signal]:
        """
        【抽象方法】生成交易信号
        策略核心逻辑，根据市场数据生成买卖信号
        
        :param market_data: 市场数据字典
            - 'daily': 日线数据 DataFrame
            - 'daily_basic': 每日基本面数据 DataFrame
            - 'top_list': 龙虎榜数据 DataFrame
            - 等其他数据...
        :param current_positions: 当前持仓字典
        :return: 信号列表
        """
        pass
    
    @abstractmethod
    def on_bar(self, data: Dict[str, Any]) -> None:
        """
        【抽象方法】K 线回调
        每根 K 线触发一次，用于实时更新策略状态
        
        :param data: K 线数据字典
        """
        pass
    
    @abstractmethod
    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """
        【抽象方法】订单成交回调
        订单成交时调用，用于更新持仓状态
        
        :param order: 成交订单字典
        """
        pass
    
    # ==================== 虚方法（可选重写） ====================
    
    def on_init_strategy(self) -> bool:
        """
        【虚方法】策略初始化回调
        在策略初始化时调用，用于加载策略专属配置
        默认实现返回 True，子类可重写
        
        :return: 是否初始化成功
        """
        logger.debug(f"🔧 策略 {self.info.name} 初始化")
        return True
    
    def on_start_strategy(self) -> bool:
        """
        【虚方法】策略启动回调
        在策略激活时调用，用于启动策略专属逻辑
        默认实现返回 True，子类可重写
        
        :return: 是否启动成功
        """
        logger.debug(f"🟢 策略 {self.info.name} 启动")
        return True
    
    def on_stop_strategy(self) -> bool:
        """
        【虚方法】策略停止回调
        在策略停用时调用，用于清理策略专属资源
        默认实现返回 True，子类可重写
        
        :return: 是否停止成功
        """
        logger.debug(f"🔴 策略 {self.info.name} 停止")
        return True
    
    def risk_check(self, signal: Signal) -> bool:
        """
        【虚方法】风险检查
        在信号生成后进行风险控制检查
        默认实现返回 True（允许交易），子类可重写添加风控逻辑
        
        :param signal: 待检查的信号
        :return: 是否通过风控检查
        """
        return True
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """
        【虚方法】获取策略参数
        返回策略的可调参数，用于参数优化
        默认实现返回空字典，子类可重写
        
        :return: 策略参数字典
        """
        return {}
    
    def set_strategy_params(self, params: Dict[str, Any]) -> bool:
        """
        【虚方法】设置策略参数
        更新策略参数
        默认实现更新配置字典，子类可重写添加自定义逻辑
        
        :param params: 参数字典
        :return: 是否设置成功
        """
        self.strategy_config.update(params)
        logger.info(f"⚙️  策略 {self.info.name} 参数已更新")
        return True
    
    # ==================== 生命周期方法重写 ====================
    
    def on_init(self) -> bool:
        """
        【优化】策略初始化流程
        调用策略专属初始化
        """
        try:
            # 调用策略专属初始化
            success = self.on_init_strategy()
            
            if success:
                self.set_state(PluginState.INACTIVE)
                logger.info(f"✅ 策略 {self.info.name} 初始化完成")
                return True
            else:
                self._error_message = "on_init_strategy() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 策略 {self.info.name} 初始化失败")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 策略 {self.info.name} 初始化异常：{e}", exc_info=True)
            return False
    
    def on_activate(self) -> bool:
        """
        【优化】策略激活流程
        调用策略专属启动
        """
        try:
            # 调用策略专属启动
            success = self.on_start_strategy()
            
            if success:
                self.set_state(PluginState.ACTIVE)
                self._last_active_time = time.time()
                logger.info(f"🟢 策略 {self.info.name} 已激活")
                return True
            else:
                self._error_message = "on_start_strategy() 返回 False"
                self.set_state(PluginState.ERROR)
                logger.error(f"❌ 策略 {self.info.name} 启动失败")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            self.set_state(PluginState.ERROR)
            logger.error(f"❌ 策略 {self.info.name} 激活异常：{e}", exc_info=True)
            return False
    
    def on_deactivate(self) -> bool:
        """
        【优化】策略停用流程
        调用策略专属停止
        """
        try:
            # 调用策略专属停止
            success = self.on_stop_strategy()
            
            if success:
                self.set_state(PluginState.INACTIVE)
                logger.info(f"🔴 策略 {self.info.name} 已停用")
                return True
            else:
                self._error_message = "on_stop_strategy() 返回 False"
                logger.error(f"❌ 策略 {self.info.name} 停止失败")
                return False
                
        except Exception as e:
            self._error_message = str(e)
            logger.error(f"❌ 策略 {self.info.name} 停用异常：{e}", exc_info=True)
            return False
    
    # ==================== 工具方法 ====================
    
    def add_position(self, position: Position) -> None:
        """
        添加持仓
        :param position: 持仓信息
        """
        self.positions[position.ts_code] = position
        logger.debug(f"📈 添加持仓：{position.ts_code} x {position.volume}")
    
    def remove_position(self, ts_code: str) -> Optional[Position]:
        """
        移除持仓
        :param ts_code: 股票代码
        :return: 被移除的持仓（不存在返回 None）
        """
        position = self.positions.pop(ts_code, None)
        if position:
            logger.debug(f"📉 移除持仓：{ts_code}")
        return position
    
    def update_position_price(self, ts_code: str, price: float) -> None:
        """
        更新持仓价格
        :param ts_code: 股票代码
        :param price: 最新价格
        """
        if ts_code in self.positions:
            self.positions[ts_code].update_price(price)
    
    def get_position(self, ts_code: str) -> Optional[Position]:
        """获取指定股票的持仓"""
        return self.positions.get(ts_code)
    
    def get_total_position_value(self) -> float:
        """获取总持仓市值"""
        return sum(p.volume * p.current_price for p in self.positions.values())
    
    def get_total_profit(self) -> float:
        """获取总盈亏"""
        return sum(
            p.volume * (p.current_price - p.avg_cost)
            for p in self.positions.values()
        )
    
    def set_backtest_mode(self, mode: bool) -> None:
        """设置回测模式"""
        self.backtest_mode = mode
        logger.info(f"🔄 策略回测模式：{'开启' if mode else '关闭'}")
    
    def is_backtest_mode(self) -> bool:
        """检查是否为回测模式"""
        return self.backtest_mode
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取策略统计信息
        :return: 统计信息字典
        """
        base_stats = super().get_stats()
        
        base_stats.update({
            'total_signals': self.total_signals,
            'buy_signals': self.buy_signals,
            'sell_signals': self.sell_signals,
            'position_count': len(self.positions),
            'watchlist_count': len(self.watchlist),
            'backtest_mode': self.backtest_mode,
            'total_position_value': self.get_total_position_value(),
            'total_profit': self.get_total_profit(),
        })
        
        return base_stats
    
    def __repr__(self) -> str:
        return f"StrategyPlugin(name={self.info.name}, state={self.get_state().value})"
