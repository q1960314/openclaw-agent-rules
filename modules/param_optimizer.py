# ==============================================
# 【优化】参数优化模块 - 贝叶斯优化
# ==============================================
# 功能：使用贝叶斯优化/遗传算法自动寻优策略参数
# 优化目标：最大化夏普比率
# ==============================================

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Callable, Optional
from datetime import datetime

logger = logging.getLogger("quant_system")

try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    SKOPT_AVAILABLE = True
except ImportError:
    logger.warning("⚠️  scikit-optimize 未安装，使用简化优化器")
    SKOPT_AVAILABLE = False


class BayesianOptimizer:
    """
    【优化】贝叶斯优化器
    使用高斯过程进行参数优化
    """
    
    def __init__(self, param_space: Dict[str, Any]):
        """
        初始化优化器
        :param param_space: 参数空间定义
        示例：
        {
            'stop_loss_rate': (0.01, 0.10),      # 连续参数
            'stop_profit_rate': (0.05, 0.30),
            'max_hold_days': (1, 5),             # 整数参数
            'min_order_ratio': (0.01, 0.10),
        }
        """
        self.param_space = param_space
        self.best_params = None
        self.best_score = -np.inf
        self.history = []
    
    def optimize(self, objective_func: Callable, n_calls: int = 50, 
                 random_state: int = 42) -> Dict[str, Any]:
        """
        执行优化
        :param objective_func: 目标函数（返回要最大化的分数）
        :param n_calls: 优化迭代次数
        :param random_state: 随机种子
        :return: 最优参数
        """
        if not SKOPT_AVAILABLE:
            logger.warning("⚠️  使用简化网格搜索替代贝叶斯优化")
            return self._grid_search(objective_func, n_calls)
        
        try:
            # 构建参数空间
            space = []
            param_names = []
            
            for param_name, (low, high) in self.param_space.items():
                if isinstance(low, int) and isinstance(high, int):
                    space.append(Integer(low, high, name=param_name))
                else:
                    space.append(Real(low, high, name=param_name))
                param_names.append(param_name)
            
            # 包装目标函数
            @use_named_args(space)
            def wrapped_objective(**params):
                score = objective_func(params)
                
                # 记录历史
                self.history.append({
                    'params': params.copy(),
                    'score': score,
                    'timestamp': datetime.now()
                })
                
                # 更新最优
                if score > self.best_score:
                    self.best_score = score
                    self.best_params = params.copy()
                    logger.info(f"🎯 新最优解：{params}, 分数：{score:.4f}")
                
                # 贝叶斯优化最小化，所以返回负值
                return -score
            
            # 执行优化
            logger.info(f"🚀 开始贝叶斯优化，迭代 {n_calls} 次...")
            result = gp_minimize(
                wrapped_objective,
                space,
                n_calls=n_calls,
                random_state=random_state,
                verbose=True,
                n_initial_points=10,
                acq_func='EI',  # Expected Improvement
            )
            
            logger.info(f"✅ 优化完成，最优参数：{self.best_params}, 最优分数：{self.best_score:.4f}")
            return self.best_params
            
        except Exception as e:
            logger.error(f"❌ 贝叶斯优化失败：{e}", exc_info=True)
            logger.warning("⚠️  降级为网格搜索")
            return self._grid_search(objective_func, n_calls)
    
    def _grid_search(self, objective_func: Callable, n_calls: int) -> Dict[str, Any]:
        """简化网格搜索（当 skopt 不可用时）"""
        try:
            import random
            
            logger.info(f"🚀 开始随机搜索，迭代 {n_calls} 次...")
            
            for i in range(n_calls):
                # 随机采样参数
                params = {}
                for param_name, (low, high) in self.param_space.items():
                    if isinstance(low, int) and isinstance(high, int):
                        params[param_name] = random.randint(low, high)
                    else:
                        params[param_name] = random.uniform(low, high)
                
                # 评估
                score = objective_func(params)
                
                # 记录
                self.history.append({
                    'params': params.copy(),
                    'score': score,
                    'timestamp': datetime.now()
                })
                
                # 更新最优
                if score > self.best_score:
                    self.best_score = score
                    self.best_params = params.copy()
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"📊 迭代 {i+1}/{n_calls}, 当前最优：{params}, 分数：{score:.4f}")
            
            logger.info(f"✅ 优化完成，最优参数：{self.best_params}, 最优分数：{self.best_score:.4f}")
            return self.best_params
            
        except Exception as e:
            logger.error(f"❌ 随机搜索失败：{e}", exc_info=True)
            # 返回默认参数
            default_params = {}
            for param_name, (low, high) in self.param_space.items():
                if isinstance(low, int):
                    default_params[param_name] = (low + high) // 2
                else:
                    default_params[param_name] = (low + high) / 2
            return default_params
    
    def get_optimization_history(self) -> pd.DataFrame:
        """获取优化历史"""
        if not self.history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.history)
        df['params'] = df['params'].apply(lambda x: pd.Series(x))
        return df
    
    def plot_optimization_progress(self):
        """绘制优化进度图（需要 matplotlib）"""
        try:
            import matplotlib.pyplot as plt
            
            if not self.history:
                logger.warning("⚠️  无优化历史数据")
                return
            
            scores = [h['score'] for h in self.history]
            best_scores = [max(scores[:i+1]) for i in range(len(scores))]
            
            plt.figure(figsize=(12, 6))
            plt.plot(scores, label='Score', alpha=0.6)
            plt.plot(best_scores, label='Best Score', linewidth=2)
            plt.xlabel('Iteration')
            plt.ylabel('Score')
            plt.title('Optimization Progress')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig('optimization_progress.png', dpi=150)
            logger.info("📊 优化进度图已保存：optimization_progress.png")
            
        except Exception as e:
            logger.error(f"❌ 绘图失败：{e}")


class StrategyParamOptimizer:
    """
    【优化】策略参数优化器
    为特定策略优化参数
    """
    
    def __init__(self, strategy, backtest_func: Callable):
        """
        初始化
        :param strategy: 策略实例
        :param backtest_func: 回测函数
        """
        self.strategy = strategy
        self.backtest_func = backtest_func
        self.optimizer = None
    
    def optimize_strategy(self, param_space: Dict[str, Any], n_calls: int = 50) -> Dict[str, Any]:
        """
        优化策略参数
        :param param_space: 参数空间
        :param n_calls: 优化迭代次数
        :return: 最优参数
        """
        # 创建优化器
        self.optimizer = BayesianOptimizer(param_space)
        
        # 定义目标函数
        def objective(params):
            try:
                # 设置策略参数
                self.strategy.set_strategy_params(params)
                
                # 运行回测
                result = self.backtest_func(self.strategy)
                
                # 返回夏普比率（要最大化）
                sharpe = result.get('sharpe_ratio', 0)
                
                # 考虑回撤惩罚
                max_drawdown = result.get('max_drawdown', 0)
                penalty = max(0, max_drawdown - 0.20) * 2  # 回撤超过 20% 惩罚
                
                score = sharpe - penalty
                
                return score
                
            except Exception as e:
                logger.error(f"❌ 参数评估失败：{e}")
                return -np.inf  # 返回很差的分数
        
        # 执行优化
        best_params = self.optimizer.optimize(objective, n_calls)
        
        # 应用最优参数
        if best_params:
            self.strategy.set_strategy_params(best_params)
        
        return best_params
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        if not self.optimizer or not self.optimizer.history:
            return {}
        
        history_df = pd.DataFrame([
            {**h['params'], 'score': h['score']}
            for h in self.optimizer.history
        ])
        
        report = {
            'total_iterations': len(self.optimizer.history),
            'best_params': self.optimizer.best_params,
            'best_score': self.optimizer.best_score,
            'score_mean': history_df['score'].mean(),
            'score_std': history_df['score'].std(),
            'score_improvement': self.optimizer.best_score - history_df['score'].iloc[0] if len(history_df) > 1 else 0,
        }
        
        return report


def get_default_param_space(strategy_name: str) -> Dict[str, Tuple[float, float]]:
    """
    获取默认参数空间
    :param strategy_name: 策略名称
    :return: 参数空间定义
    """
    if strategy_name == 'limit_up':
        return {
            'stop_loss_rate': (0.03, 0.10),
            'stop_profit_rate': (0.08, 0.25),
            'max_hold_days': (1, 5),
            'min_order_ratio': (0.01, 0.08),
            'link_board_min': (1, 3),
            'link_board_max': (3, 7),
        }
    
    elif strategy_name == 'shrink_volume':
        return {
            'volume_shrink_ratio': (0.30, 0.70),
            'rsi_oversold': (20, 35),
            'stop_loss_rate': (0.03, 0.08),
            'stop_profit_rate': (0.10, 0.25),
            'max_hold_days': (5, 15),
        }
    
    elif strategy_name == 'sector_rotation':
        return {
            'rotation_period': (2, 7),
            'min_sector_strength': (0.4, 0.8),
            'top_n_sectors': (2, 5),
            'stop_loss_rate': (0.05, 0.12),
            'stop_profit_rate': (0.15, 0.30),
            'max_hold_days': (3, 10),
        }
    
    else:
        # 通用参数空间
        return {
            'stop_loss_rate': (0.03, 0.10),
            'stop_profit_rate': (0.08, 0.25),
            'max_hold_days': (1, 10),
        }
