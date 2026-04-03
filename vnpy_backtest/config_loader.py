# -*- coding: utf-8 -*-
"""
配置加载器 v1.0
统一加载YAML配置文件
"""

import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load()
    
    def load(self, config_path: str = None) -> Dict:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                'config/backtest_config.yaml'
            )
        
        if not os.path.exists(config_path):
            # 尝试workspace路径
            config_path = '/home/admin/.openclaw/workspace/master/config/backtest_config.yaml'
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        else:
            # 使用默认配置
            self._config = self._get_default_config()
        
        return self._config
    
    def _get_default_config(self) -> Dict:
        """默认配置"""
        return {
            'strategy': {
                'default_type': '打板策略',
                'supported_types': ['打板策略', '缩量潜伏策略', '板块轮动策略']
            },
            'risk': {
                'stop_loss': 0.06,
                'stop_profit': 0.12,
                'max_hold_days': 3,
                'max_positions': 2,
                'position_ratio': 0.2,
                'strategy_params': {
                    '打板策略': {
                        'slippage_rate': 0.015,
                        'high_open_fail_rate': 0.5
                    },
                    '缩量潜伏策略': {
                        'slippage_rate': 0.005,
                        'high_open_fail_rate': 0.1
                    }
                }
            },
            'features': {
                'auto_tune': True,
                'sentiment': True,
                'ml_factor': True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_strategy_params(self, strategy_type: str) -> Dict:
        """获取策略专属参数"""
        strategy_params = self.get('risk.strategy_params', {})
        return strategy_params.get(strategy_type, {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        return self.get(f'features.{feature}', False)


# 全局配置实例
config = ConfigLoader()


if __name__ == "__main__":
    # 测试
    cfg = ConfigLoader()
    print(f"默认策略: {cfg.get('strategy.default_type')}")
    print(f"止损: {cfg.get('risk.stop_loss')}")
    print(f"打板策略参数: {cfg.get_strategy_params('打板策略')}")
    print(f"情绪分析启用: {cfg.is_feature_enabled('sentiment')}")