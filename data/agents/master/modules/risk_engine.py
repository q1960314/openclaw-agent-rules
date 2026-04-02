#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险引擎模块 - 添加风险验证钩子和熔断逻辑
Risk Engine Module - Add risk validation hooks and circuit breaker logic
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class RiskEngine:
    """风险引擎 - 实现风险验证和熔断控制"""
    
    def __init__(self):
        self.risk_thresholds = {
            "max_drawdown": 0.15,  # 最大回撤 15%
            "max_position_size": 0.1,  # 最大头寸 10%
            "max_leverage": 2.0,  # 最大杠杆 2倍
            "max_daily_loss": 0.05,  # 最大日亏损 5%
        }
        self.circuit_breakers = {
            "drawdown_triggered": False,
            "position_size_triggered": False,
            "leverage_triggered": False,
            "daily_loss_triggered": False,
        }
        self.validation_hooks = []
    
    def add_risk_validation_hook(self, hook_func):
        """添加风险验证钩子"""
        self.validation_hooks.append(hook_func)
    
    def validate_strategy_execution(self, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证策略执行参数是否符合风险要求
        
        Args:
            strategy_params: 策略执行参数
            
        Returns:
            验证结果字典
        """
        validation_results = {
            "strategy_id": strategy_params.get("strategy_id", "unknown"),
            "valid": True,
            "violations": [],
            "risk_score": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查回撤限制
        drawdown = strategy_params.get("expected_drawdown", 0.0)
        if drawdown > self.risk_thresholds["max_drawdown"]:
            validation_results["valid"] = False
            validation_results["violations"].append({
                "type": "drawdown_exceeded",
                "expected": drawdown,
                "threshold": self.risk_thresholds["max_drawdown"],
                "severity": "critical"
            })
        
        # 检查头寸大小
        position_size = strategy_params.get("position_size", 0.0)
        if position_size > self.risk_thresholds["max_position_size"]:
            validation_results["valid"] = False
            validation_results["violations"].append({
                "type": "position_size_exceeded", 
                "expected": position_size,
                "threshold": self.risk_thresholds["max_position_size"],
                "severity": "high"
            })
        
        # 检查杠杆
        leverage = strategy_params.get("leverage", 1.0)
        if leverage > self.risk_thresholds["max_leverage"]:
            validation_results["valid"] = False
            validation_results["violations"].append({
                "type": "leverage_exceeded",
                "expected": leverage,
                "threshold": self.risk_thresholds["max_leverage"],
                "severity": "high"
            })
        
        # 检查日亏损
        daily_loss = strategy_params.get("expected_daily_loss", 0.0)
        if daily_loss > self.risk_thresholds["max_daily_loss"]:
            validation_results["valid"] = False
            validation_results["violations"].append({
                "type": "daily_loss_exceeded",
                "expected": daily_loss,
                "threshold": self.risk_thresholds["max_daily_loss"],
                "severity": "medium"
            })
        
        # 计算风险分数 (0-10)
        violation_count = len(validation_results["violations"])
        validation_results["risk_score"] = min(10.0, violation_count * 2.5)
        
        return validation_results
    
    def check_circuit_breaker(self, strategy_id: str) -> Dict[str, Any]:
        """
        检查熔断状态
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            熔断检查结果
        """
        active_breakers = [k for k, v in self.circuit_breakers.items() if v]
        
        return {
            "strategy_id": strategy_id,
            "circuit_breaker_active": len(active_breakers) > 0,
            "active_breakers": active_breakers,
            "can_execute": len(active_breakers) == 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def trigger_circuit_breaker(self, breaker_type: str, reason: str = ""):
        """触发熔断器"""
        if breaker_type in self.circuit_breakers:
            self.circuit_breakers[breaker_type] = True
            print(f"🚨 熔断器触发: {breaker_type}, 原因: {reason}")
    
    def reset_circuit_breaker(self, breaker_type: str):
        """重置熔断器"""
        if breaker_type in self.circuit_breakers:
            self.circuit_breakers[breaker_type] = False
            print(f"✅ 熔断器重置: {breaker_type}")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        return {
            "risk_thresholds": self.risk_thresholds,
            "circuit_breakers": self.circuit_breakers,
            "validation_hook_count": len(self.validation_hooks),
            "timestamp": datetime.now().isoformat()
        }


# 便捷函数
def validate_risk_for_strategy(strategy_params: Dict[str, Any]) -> Dict[str, Any]:
    """验证策略风险的便捷函数"""
    engine = RiskEngine()
    return engine.validate_strategy_execution(strategy_params)


def check_circuit_breaker_status(strategy_id: str) -> Dict[str, Any]:
    """检查熔断状态的便捷函数"""
    engine = RiskEngine()
    return engine.check_circuit_breaker(strategy_id)


if __name__ == "__main__":
    # 示例使用
    example_strategy = {
        "strategy_id": "test_strategy_001",
        "expected_drawdown": 0.12,
        "position_size": 0.08,
        "leverage": 1.5,
        "expected_daily_loss": 0.03
    }
    
    result = validate_risk_for_strategy(example_strategy)
    print(json.dumps(result, ensure_ascii=False, indent=2))