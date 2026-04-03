# -*- coding: utf-8 -*-
"""
策略抽象基类 v1.0
所有策略必须继承此类，实现filter()和score()方法

设计原则：
1. 策略无关 - 框架不绑定任何特定策略
2. 可插拔 - 新策略只需继承BaseStrategy
3. 配置驱动 - 参数从配置文件加载
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class MarketType(Enum):
    """市场类型"""
    MAIN_BOARD = "主板"      # 60xxxx, 00xxxx
    CHI_NEXT = "创业板"      # 30xxxx
    STAR_MARKET = "科创板"   # 68xxxx
    BSE = "北交所"           # 8xxxxx, 4xxxxx


@dataclass
class Signal:
    """交易信号"""
    ts_code: str                    # 股票代码
    signal_type: SignalType         # 信号类型
    price: float                    # 建议价格
    shares: int = 0                 # 建议数量
    confidence: float = 0.0         # 信号置信度 (0-1)
    reason: str = ""                # 信号原因
    timestamp: str = ""             # 信号时间
    score: float = 0.0              # 评分
    metadata: Dict = field(default_factory=dict)  # 扩展信息
    
    def to_dict(self) -> Dict:
        return {
            'ts_code': self.ts_code,
            'signal_type': self.signal_type.value,
            'price': self.price,
            'shares': self.shares,
            'confidence': self.confidence,
            'reason': self.reason,
            'timestamp': self.timestamp,
            'score': self.score,
            'metadata': self.metadata
        }


@dataclass
class Position:
    """持仓信息"""
    ts_code: str                    # 股票代码
    shares: int                     # 持股数量
    cost_price: float               # 成本价
    current_price: float = 0.0      # 当前价
    market_value: float = 0.0       # 市值
    profit_loss: float = 0.0        # 盈亏
    profit_loss_pct: float = 0.0    # 盈亏比例
    hold_days: int = 0              # 持股天数
    buy_date: str = ""              # 买入日期
    buy_idx: int = 0                # 买入时的日期索引
    
    def update(self, current_price: float):
        """更新持仓信息"""
        self.current_price = current_price
        self.market_value = self.shares * current_price
        self.profit_loss = (current_price - self.cost_price) * self.shares
        if self.cost_price > 0:
            self.profit_loss_pct = (current_price - self.cost_price) / self.cost_price


@dataclass
class RiskParams:
    """风控参数"""
    stop_loss: float = 0.06         # 止损比例
    stop_profit: float = 0.12       # 止盈比例
    max_hold_days: int = 3          # 最长持股天数
    max_positions: int = 2          # 最大持仓数量
    position_ratio: float = 0.2     # 单只股票仓位比例
    slippage_rate: float = 0.01     # 滑点率
    high_open_fail_rate: float = 0.3  # 高开买入失败率


class BaseStrategy(ABC):
    """
    策略抽象基类 v1.0
    
    所有策略必须继承此类，并实现以下方法：
    - filter(): 股票过滤
    - score(): 股票评分
    
    可选重写：
    - generate_signals(): 生成交易信号
    - get_risk_params(): 获取风控参数
    - on_bar(): K线事件回调
    """
    
    # 策略元信息（子类必须重写）
    strategy_name: str = "base_strategy"
    strategy_version: str = "1.0.0"
    strategy_type: str = "generic"
    description: str = "策略基类"
    
    # 支持的市场类型
    supported_markets: List[MarketType] = [
        MarketType.MAIN_BOARD, 
        MarketType.CHI_NEXT,
        MarketType.STAR_MARKET  # 添加科创板支持
    ]
    
    # 所需数据类型
    required_data: List[str] = ['daily', 'limit_list']
    
    def __init__(self, config: Dict = None):
        """
        初始化策略
        
        Args:
            config: 策略配置参数
        """
        self.config = config or {}
        self._validate_config()
        self._init_risk_params()
        logger.info(f"📊 策略初始化: {self.strategy_name} v{self.strategy_version}")
    
    def _validate_config(self):
        """验证配置参数"""
        pass
    
    def _init_risk_params(self):
        """初始化风控参数"""
        risk_config = self.config.get('risk', {})
        self.risk_params = RiskParams(
            stop_loss=risk_config.get('stop_loss', 0.06),
            stop_profit=risk_config.get('stop_profit', 0.12),
            max_hold_days=risk_config.get('max_hold_days', 3),
            max_positions=risk_config.get('max_positions', 2),
            position_ratio=risk_config.get('position_ratio', 0.2),
            slippage_rate=risk_config.get('slippage_rate', 0.01),
            high_open_fail_rate=risk_config.get('high_open_fail_rate', 0.3)
        )
    
    @abstractmethod
    def filter(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        股票过滤（必须实现）
        
        Args:
            data: 当日股票数据 DataFrame
            date: 交易日期 (YYYY-MM-DD 或 YYYYMMDD)
            
        Returns:
            过滤后的股票 DataFrame
        """
        pass
    
    @abstractmethod
    def score(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        股票评分（必须实现）
        
        Args:
            data: 过滤后的股票数据 DataFrame
            date: 交易日期
            
        Returns:
            带评分的股票 DataFrame，必须包含 'total_score' 列
        """
        pass
    
    def generate_signals(self, 
                         scored_data: pd.DataFrame, 
                         positions: Dict[str, Position],
                         date: str,
                         capital: float) -> List[Signal]:
        """
        生成交易信号（可重写）
        
        Args:
            scored_data: 评分后的股票数据
            positions: 当前持仓 {ts_code: Position}
            date: 交易日期
            capital: 当前可用资金
            
        Returns:
            交易信号列表
        """
        signals = []
        
        # 买入信号
        if len(positions) < self.risk_params.max_positions:
            available_slots = self.risk_params.max_positions - len(positions)
            
            for _, row in scored_data.head(available_slots).iterrows():
                ts_code = row.get('ts_code', '')
                if ts_code and ts_code not in positions:
                    score = row.get('total_score', 0)
                    price = row.get('close', 0)
                    
                    # 计算买入数量
                    position_value = capital * self.risk_params.position_ratio
                    shares = int(position_value / price / 100) * 100 if price > 0 else 0
                    
                    if shares >= 100:
                        signals.append(Signal(
                            ts_code=ts_code,
                            signal_type=SignalType.BUY,
                            price=price,
                            shares=shares,
                            confidence=min(score / 100, 1.0),
                            reason=f"策略选股: {self.strategy_name}",
                            timestamp=date,
                            score=score,
                            metadata={'row_data': row.to_dict()}
                        ))
        
        return signals
    
    def check_sell(self, 
                   positions: Dict[str, Position],
                   date: str,
                   date_idx: int) -> List[Signal]:
        """
        检查卖出信号（止损/止盈/超时）
        
        Args:
            positions: 当前持仓
            date: 交易日期
            date_idx: 日期索引
            
        Returns:
            卖出信号列表
        """
        signals = []
        
        for ts_code, pos in positions.items():
            reason = None
            
            # 止损检查
            if pos.profit_loss_pct <= -self.risk_params.stop_loss:
                reason = 'stop_loss'
            # 止盈检查
            elif pos.profit_loss_pct >= self.risk_params.stop_profit:
                reason = 'stop_profit'
            # 超时检查
            elif (date_idx - pos.buy_idx) >= self.risk_params.max_hold_days:
                reason = 'time_exit'
            
            if reason:
                signals.append(Signal(
                    ts_code=ts_code,
                    signal_type=SignalType.SELL,
                    price=pos.current_price,
                    shares=pos.shares,
                    reason=reason,
                    timestamp=date
                ))
        
        return signals
    
    def get_risk_params(self) -> RiskParams:
        """获取风控参数"""
        return self.risk_params
    
    def get_required_data(self) -> List[str]:
        """获取策略所需数据类型"""
        return self.required_data
    
    def is_market_supported(self, ts_code: str) -> bool:
        """
        检查股票是否属于支持的市场
        
        Args:
            ts_code: 股票代码
            
        Returns:
            是否支持
        """
        if not ts_code:
            return False
        
        code = ts_code.split('.')[0] if '.' in ts_code else ts_code
        
        # 主板: 60xxxx, 00xxxx
        if MarketType.MAIN_BOARD in self.supported_markets:
            if code.startswith(('60', '00')):
                return True
        
        # 创业板: 30xxxx
        if MarketType.CHI_NEXT in self.supported_markets:
            if code.startswith('30'):
                return True
        
        # 科创板: 68xxxx
        if MarketType.STAR_MARKET in self.supported_markets:
            if code.startswith('68'):
                return True
        
        # 北交所: 8xxxxx, 4xxxxx
        if MarketType.BSE in self.supported_markets:
            if code.startswith(('8', '4')):
                return True
        
        return False
    
    def on_bar(self, bar: Dict, positions: Dict[str, Position]) -> List[Signal]:
        """
        K线事件回调（事件驱动引擎使用）
        
        Args:
            bar: K线数据
            positions: 当前持仓
            
        Returns:
            交易信号列表
        """
        return []
    
    def on_tick(self, tick: Dict, positions: Dict[str, Position]) -> List[Signal]:
        """
        Tick事件回调（高频策略使用）
        
        Args:
            tick: Tick数据
            positions: 当前持仓
            
        Returns:
            交易信号列表
        """
        return []


# ==================== 策略注册器 ====================

class StrategyRegistry:
    """
    策略注册器 - 支持动态加载策略
    
    使用方法：
    1. 装饰器注册: @StrategyRegistry.register
    2. 手动注册: StrategyRegistry.register_class(MyStrategy)
    3. 获取策略: StrategyRegistry.get('limit_up')
    4. 列出所有: StrategyRegistry.list_all()
    """
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, strategy_class: type) -> type:
        """装饰器方式注册策略"""
        instance = strategy_class()
        cls._strategies[instance.strategy_name] = strategy_class
        logger.info(f"✅ 策略已注册: {instance.strategy_name}")
        return strategy_class
    
    @classmethod
    def register_class(cls, strategy_class: type):
        """手动注册策略类"""
        instance = strategy_class()
        cls._strategies[instance.strategy_name] = strategy_class
        logger.info(f"✅ 策略已注册: {instance.strategy_name}")
    
    @classmethod
    def get(cls, name: str) -> type:
        """获取策略类"""
        if name not in cls._strategies:
            raise ValueError(f"策略 '{name}' 未注册，可用策略: {list(cls._strategies.keys())}")
        return cls._strategies[name]
    
    @classmethod
    def get_instance(cls, name: str, config: Dict = None) -> BaseStrategy:
        """获取策略实例"""
        strategy_class = cls.get(name)
        return strategy_class(config)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有已注册策略"""
        return list(cls._strategies.keys())
    
    @classmethod
    def from_config(cls, config_path: str) -> BaseStrategy:
        """从配置文件加载策略"""
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        strategy_name = config.get('strategy_name')
        return cls.get_instance(strategy_name, config)


# ==================== 工具函数 ====================

def create_signal(ts_code: str, 
                  signal_type: SignalType,
                  price: float,
                  shares: int = 0,
                  confidence: float = 0.0,
                  reason: str = "",
                  **kwargs) -> Signal:
    """
    创建交易信号的便捷函数
    
    Args:
        ts_code: 股票代码
        signal_type: 信号类型
        price: 价格
        shares: 数量
        confidence: 置信度
        reason: 原因
        **kwargs: 其他参数
        
    Returns:
        Signal对象
    """
    return Signal(
        ts_code=ts_code,
        signal_type=signal_type,
        price=price,
        shares=shares,
        confidence=confidence,
        reason=reason,
        **kwargs
    )


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试策略注册
    @StrategyRegistry.register
    class TestStrategy(BaseStrategy):
        strategy_name = "test_strategy"
        strategy_type = "test"
        description = "测试策略"
        
        def filter(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
            return data
        
        def score(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
            data['total_score'] = 50
            return data
    
    print("已注册策略:", StrategyRegistry.list_all())
    
    # 测试获取策略
    strategy = StrategyRegistry.get_instance("test_strategy")
    print("策略实例:", strategy.strategy_name)
    
    # 测试市场支持
    print("主板支持:", strategy.is_market_supported("600000.SH"))
    print("创业板支持:", strategy.is_market_supported("300001.SZ"))
    print("科创板支持:", strategy.is_market_supported("688001.SH"))