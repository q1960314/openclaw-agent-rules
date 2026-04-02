#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略集成模块 - 更新使用已验证的策略和风险接口，优化子策略权重分配
Strategy Ensemble Module - Update to use validated strategy and risk interfaces, optimize sub-strategy weight allocation
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from .strategy_core import StrategyCore, execute_strategy_with_risk_validation, adjust_stop_loss_take_profit_settings
from .risk_engine import RiskEngine, validate_risk_for_strategy


class StrategyEnsemble:
    """策略集成 - 管理多个子策略的组合与权重分配"""
    
    def __init__(self):
        self.strategies = {}
        self.weights = {}
        self.risk_engine = RiskEngine()
        self.ensemble_config = {
            "correlation_threshold": 0.7,  # 策略间相关性阈值
            "diversification_factor": 0.8,  # 分散化因子
            "max_strategy_count": 10,  # 最大策略数量
            "min_performance_threshold": 0.05,  # 最低表现阈值
            "weight_adjustment_frequency": "daily"  # 权重调整频率
        }
        self.performance_records = []
    
    def register_strategy(self, strategy_id: str, strategy_impl: Any, initial_weight: float = 1.0):
        """
        注册策略到集成中
        
        Args:
            strategy_id: 策略ID
            strategy_impl: 策略实现
            initial_weight: 初始权重
        """
        self.strategies[strategy_id] = strategy_impl
        self.weights[strategy_id] = min(initial_weight, 1.0)  # 限制最大权重为1.0
        print(f"✅ 策略 {strategy_id} 已注册到集成，初始权重: {initial_weight}")
    
    def validate_strategy_for_ensemble(self, strategy_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证策略是否适合集成
        
        Args:
            strategy_spec: 策略规范
            
        Returns:
            验证结果
        """
        # 使用已验证的风险接口进行验证
        risk_validation = validate_risk_for_strategy(strategy_spec)
        
        # 额外的集成验证
        ensemble_validation = {
            "strategy_id": strategy_spec.get("strategy_id"),
            "valid_for_ensemble": True,
            "validation_results": {
                "risk_compliant": risk_validation.get("valid", False),
                "performance_acceptable": self._check_performance_threshold(strategy_spec),
                "correlation_acceptable": self._check_correlation_with_existing(stratgy_spec),
                "resource_usage_acceptable": self._check_resource_usage(strategy_spec)
            },
            "violations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查验证结果
        if not risk_validation.get("valid"):
            ensemble_validation["valid_for_ensemble"] = False
            ensemble_validation["violations"].append("Risk validation failed")
        
        if not ensemble_validation["validation_results"]["performance_acceptable"]:
            ensemble_validation["valid_for_ensemble"] = False
            ensemble_validation["violations"].append("Performance below threshold")
        
        if not ensemble_validation["validation_results"]["correlation_acceptable"]:
            ensemble_validation["valid_for_ensemble"] = False
            ensemble_validation["violations"].append("High correlation with existing strategies")
        
        if not ensemble_validation["validation_results"]["resource_usage_acceptable"]:
            ensemble_validation["valid_for_ensemble"] = False
            ensemble_validation["violations"].append("Resource usage exceeds limits")
        
        return ensemble_validation
    
    def _check_performance_threshold(self, strategy_spec: Dict[str, Any]) -> bool:
        """检查策略表现是否达到阈值"""
        expected_sharpe = strategy_spec.get("expected_sharpe_ratio", 0.0)
        expected_return = strategy_spec.get("expected_annual_return", 0.0)
        
        # 基于集成配置检查阈值
        return expected_sharpe >= self.ensemble_config["min_performance_threshold"] or expected_return >= self.ensemble_config["min_performance_threshold"]
    
    def _check_correlation_with_existing(self, strategy_spec: Dict[str, Any]) -> bool:
        """检查策略与现有策略的相关性"""
        # 简化实现：返回True表示通过相关性检查
        # 在实际实现中，这里会计算与现有策略的相关性
        return True
    
    def _check_resource_usage(self, strategy_spec: Dict[str, Any]) -> bool:
        """检查资源使用是否可接受"""
        expected_frequency = strategy_spec.get("execution_frequency", "low")
        resource_estimate = strategy_spec.get("estimated_resource_usage", 0.1)  # 0.0-1.0 scale
        
        # 简化检查：资源使用不超过50%
        return resource_estimate <= 0.5
    
    def optimize_weights(self) -> Dict[str, float]:
        """
        优化子策略权重分配
        
        Returns:
            优化后的权重字典
        """
        optimized_weights = {}
        
        # 简化的权重优化逻辑
        # 在实际实现中，这里会使用更复杂的优化算法
        total_performance = 0.0
        performance_scores = {}
        
        for strategy_id in self.strategies:
            # 模拟获取策略表现分数
            perf_score = self._get_strategy_performance_score(strategy_id)
            performance_scores[strategy_id] = perf_score
            total_performance += perf_score
        
        if total_performance > 0:
            for strategy_id, perf_score in performance_scores.items():
                # 基于表现分配权重
                base_weight = perf_score / total_performance
                # 应用分散化因子
                optimized_weights[strategy_id] = base_weight * self.ensemble_config["diversification_factor"]
        else:
            # 如果没有表现数据，平均分配权重
            equal_weight = 1.0 / len(self.strategies) if self.strategies else 0.0
            for strategy_id in self.strategies:
                optimized_weights[strategy_id] = equal_weight
        
        # 更新当前权重
        self.weights.update(optimized_weights)
        
        return optimized_weights
    
    def _get_strategy_performance_score(self, strategy_id: str) -> float:
        """获取策略表现分数（模拟）"""
        # 在实际实现中，这里会从历史表现数据计算分数
        # 返回一个模拟的分数
        return 0.7 + (hash(strategy_id) % 100) * 0.003  # 0.7-1.0之间的模拟分数
    
    def execute_ensemble(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行策略集成
        
        Args:
            market_data: 市场数据
            
        Returns:
            集成执行结果
        """
        execution_results = {}
        total_weight = sum(self.weights.values())
        
        if total_weight == 0:
            return {
                "success": False,
                "error": "No active strategies in ensemble",
                "timestamp": datetime.now().isoformat(),
                "results": {}
            }
        
        for strategy_id, strategy_impl in self.strategies.items():
            weight = self.weights.get(strategy_id, 0.0)
            if weight <= 0:
                continue
            
            # 为每个策略创建执行规范
            strategy_execution_spec = {
                "strategy_id": strategy_id,
                "market_data": market_data,
                "allocation_weight": weight / total_weight,
                "risk_limits": self._get_strategy_risk_limits(strategy_id)
            }
            
            # 执行单个策略
            try:
                result = execute_strategy_with_risk_validation(strategy_execution_spec)
                execution_results[strategy_id] = result
            except Exception as e:
                execution_results[strategy_id] = {
                    "success": False,
                    "error": str(e),
                    "strategy_id": strategy_id,
                    "executed": False,
                    "timestamp": datetime.now().isoformat()
                }
        
        # 汇总集成结果
        ensemble_result = {
            "ensemble_id": f"ENSEMBLE-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "execution_time": datetime.now().isoformat(),
            "strategy_count": len(execution_results),
            "successful_executions": len([r for r in execution_results.values() if r.get("success")]),
            "failed_executions": len([r for r in execution_results.values() if not r.get("success")]),
            "execution_results": execution_results,
            "total_weight": total_weight,
            "aggregated_signals": self._aggregate_signals(execution_results),
            "ensemble_risk_metrics": self._calculate_ensemble_risk_metrics(execution_results),
            "recommendations": self._generate_recommendations(execution_results)
        }
        
        # 记录执行历史
        self.performance_records.append({
            "execution_time": datetime.now().isoformat(),
            "result_summary": {
                "total_strategies": len(execution_results),
                "successful": len([r for r in execution_results.values() if r.get("success")]),
                "failed": len([r for r in execution_results.values() if not r.get("success")])
            },
            "ensemble_result": ensemble_result
        })
        
        return ensemble_result
    
    def _get_strategy_risk_limits(self, strategy_id: str) -> Dict[str, float]:
        """获取策略风险限制"""
        return {
            "max_position_size": 0.1 * self.weights.get(strategy_id, 0.1),  # 基于权重调整最大头寸
            "max_drawdown": 0.15,
            "max_leverage": 2.0,
            "max_daily_loss": 0.05
        }
    
    def _aggregate_signals(self, execution_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """聚合信号"""
        aggregated_signals = []
        
        for strategy_id, result in execution_results.items():
            if result.get("success") and "signals_generated" in result:
                signals = result.get("signals_generated", [])
                weight = self.weights.get(strategy_id, 0.0)
                
                for signal in signals:
                    signal_with_weight = signal.copy()
                    signal_with_weight["strategy_id"] = strategy_id
                    signal_with_weight["signal_weight"] = weight
                    aggregated_signals.append(signal_with_weight)
        
        return aggregated_signals
    
    def _calculate_ensemble_risk_metrics(self, execution_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """计算集成风险指标"""
        risk_metrics = {
            "total_exposure": 0.0,
            "diversification_score": 0.0,
            "correlation_matrix": {},
            "portfolio_var": 0.0,
            "stress_test_result": "pending"
        }
        
        successful_results = [r for r in execution_results.values() if r.get("success")]
        if successful_results:
            # 计算投资组合风险指标
            risk_metrics["total_exposure"] = sum(
                r.get("risk_metrics", {}).get("exposure", 0.0) 
                for r in successful_results
            )
            risk_metrics["diversification_score"] = min(1.0, len(successful_results) * 0.2)
            risk_metrics["portfolio_var"] = sum(
                r.get("risk_metrics", {}).get("var", 0.0) * self.weights.get(r.get("strategy_id"), 0.1)
                for r in successful_results
            )
        
        return risk_metrics
    
    def _generate_recommendations(self, execution_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
        """生成推荐"""
        recommendations = []
        
        successful_count = len([r for r in execution_results.values() if r.get("success")])
        failed_count = len([r for r in execution_results.values() if not r.get("success")])
        
        if failed_count > 0:
            recommendations.append({
                "type": "weight_adjustment",
                "reason": f"{failed_count} strategies failed execution",
                "action": "Consider reducing weights of underperforming strategies"
            })
        
        if successful_count > 0:
            recommendations.append({
                "type": "performance_monitoring",
                "reason": f"{successful_count} strategies executed successfully", 
                "action": "Monitor performance and adjust weights accordingly"
            })
        
        return recommendations


def register_strategy_to_ensemble(strategy_id: str, strategy_impl: Any, initial_weight: float = 1.0) -> bool:
    """注册策略到集成的便捷函数"""
    ensemble = StrategyEnsemble()
    ensemble.register_strategy(strategy_id, strategy_impl, initial_weight)
    return True


def execute_strategy_ensemble(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行策略集成的便捷函数"""
    ensemble = StrategyEnsemble()
    return ensemble.execute_ensemble(market_data)


def optimize_ensemble_weights() -> Dict[str, float]:
    """优化集成权重的便捷函数"""
    ensemble = StrategyEnsemble()
    return ensemble.optimize_weights()


if __name__ == "__main__":
    # 示例使用
    market_data_example = {
        "timestamp": datetime.now().isoformat(),
        "symbols": ["AAPL.US", "GOOGL.US", "MSFT.US"],
        "prices": {"AAPL.US": 150.0, "GOOGL.US": 2500.0, "MSFT.US": 300.0},
        "volumes": {"AAPL.US": 1000000, "GOOGL.US": 100000, "MSFT.US": 800000},
        "market_conditions": {"volatility": "moderate", "trend": "bullish", "liquidity": "high"}
    }
    
    result = execute_strategy_ensemble(market_data_example)
    print(json.dumps(result, ensure_ascii=False, indent=2))