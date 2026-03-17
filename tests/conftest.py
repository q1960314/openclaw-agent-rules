# ==============================================
# 【优化】pytest 配置文件 - conftest.py
# ==============================================
# 功能：提供全局 fixtures、测试配置、共享数据
# 职责：测试环境初始化、共享测试数据、测试工具函数
# ==============================================

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 【优化】添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_base_data():
    """
    【优化】基础测试数据 fixture
    提供包含基础字段的 DataFrame，用于通用测试
    """
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
    data = {
        'ts_code': ['000001.SZ'] * 10,
        'trade_date': dates,
        'open': [10.0, 10.2, 10.5, 10.3, 10.8, 11.0, 11.2, 11.5, 11.3, 11.8],
        'high': [10.3, 10.6, 10.8, 10.7, 11.2, 11.4, 11.6, 11.8, 11.7, 12.0],
        'low': [9.8, 10.0, 10.3, 10.1, 10.6, 10.8, 11.0, 11.3, 11.1, 11.6],
        'close': [10.2, 10.5, 10.3, 10.8, 11.0, 11.2, 11.5, 11.3, 11.8, 12.0],
        'vol': [1000000, 1200000, 900000, 1500000, 1800000, 2000000, 2200000, 1900000, 2500000, 2800000]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_strategy_data():
    """
    【优化】策略测试数据 fixture
    提供包含策略特定字段的 DataFrame，用于策略筛选和评分测试
    """
    dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
    data = {
        'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ'],
        'trade_date': dates,
        'name': ['平安银行', '万科 A', 'ST 康美', '格力电器', '比亚迪'],
        'close': [10.5, 20.3, 5.2, 45.8, 180.5],
        'vol': [1500000, 2000000, 800000, 3000000, 5000000],
        'amount': [500000, 600000, 200000, 800000, 900000],  # 千元
        'turnover_ratio': [5.2, 6.8, 2.1, 8.5, 12.3],
        'limit': [1, 0, 0, 1, 1],  # 是否涨停
        'up_down_times': [2, 0, 0, 3, 4],  # 连板高度
        'order_amount': [15000, 0, 0, 25000, 30000],  # 封单金额（万元）
        'break_limit_times': [0, 0, 0, 1, 2],  # 炸板次数
        'first_limit_time': ['10:30', '', '', '09:45', '14:50'],  # 首次封板时间
        'float_market_cap': [150.5, 200.3, 50.2, 300.8, 500.5],  # 流通市值（亿元）
        'current_vol_ratio': [0.25, 0.6, 0.8, 0.3, 0.4],  # 当前成交量/首板成交量
        'days_after_board': [5, 0, 0, 3, 2],  # 首板后天数
        'board_vol_growth': [2.5, 1.0, 1.2, 1.8, 2.2],  # 首板放量倍数
        'is_main_industry': [1, 0, 0, 1, 1],  # 是否主线行业
        'concept_count': [2, 1, 0, 3, 4],  # 题材数量
        'inst_buy': [6000, 2000, 0, 8000, 10000],  # 机构净买入（万元）
        'youzi_buy': [4000, 1000, 0, 5000, 6000],  # 游资净买入（万元）
        'no_reduction': [1, 1, 0, 1, 1],  # 无减持公告
        'no_inquiry': [1, 0, 0, 1, 1],  # 无监管问询
    }
    return pd.DataFrame(data)


@pytest.fixture
def filter_config():
    """
    【优化】筛选配置 fixture
    """
    return {
        "min_amount": 300000,  # 千元
        "min_turnover": 3,  # %
        "exclude_st": True,
        "exclude_suspend": True,
        "max_fetch_retry": 3,
        "permanent_failed_expire": 30,
        "smart_retry_enabled": True,
        "smart_retry_days": 7,
        "fundamental_check": True
    }


@pytest.fixture
def core_config():
    """
    【优化】核心评分配置 fixture
    """
    return {
        "pass_score": 12,
        "enable_dynamic_weight": True,
        "strategy_pass_score": {
            "打板策略": 18,
            "缩量潜伏策略": 12,
            "板块轮动策略": 17
        },
        "items": {
            "缩量到首板 1/3 以内": [3, "current_vol_ratio <= 0.33", {"打板策略": 0, "缩量潜伏策略": 3, "板块轮动策略": 0}],
            "连板高度≥3 板": [2, "up_down_times >= 3", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 0.5}],
            "机构净买入≥5000 万": [2, "inst_buy >= 5000", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1.5}],
            "主线行业匹配": [2, "is_main_industry == 1", {"打板策略": 1, "缩量潜伏策略": 0, "板块轮动策略": 2}],
            "换手率 3%-10%": [1, "turnover_ratio >= 3 and turnover_ratio <= 10", {"打板策略": 2, "缩量潜伏策略": 0, "板块轮动策略": 1}],
        }
    }


@pytest.fixture
def strategy_config():
    """
    【优化】策略专属配置 fixture
    """
    return {
        "打板策略": {
            "type": "link",
            "min_order_ratio": 0.03,
            "max_break_times": 1,
            "link_board_range": [2, 4],
            "exclude_late_board": True,
            "stop_loss_rate": 0.06,
            "stop_profit_rate": 0.12,
            "max_hold_days": 2
        },
        "缩量潜伏策略": {
            "type": "first_board_pullback",
            "first_board_limit": True,
            "board_volume_growth": 1.5,
            "shrink_volume_ratio": [1/3, 1/2],
            "shrink_days_range": [3, 10],
            "pullback_support_level": 0.5,
            "support_tolerance": 0.02,
            "stop_loss_rate": 0.03,
            "stop_profit_rate": 0.15,
            "max_hold_days": 8,
            "rotate_days": 1
        },
        "板块轮动策略": {
            "type": "industry",
            "rotate_days": 3,
            "stop_loss_rate": 0.05,
            "stop_profit_rate": 0.1,
            "main_trend": True,
            "fund_inflow_top": 30,
            "max_hold_days": 3
        }
    }


@pytest.fixture
def empty_dataframe():
    """
    【优化】空 DataFrame fixture
    用于测试边界情况
    """
    return pd.DataFrame()


@pytest.fixture
def large_test_data():
    """
    【优化】大规模测试数据 fixture
    用于性能测试和压力测试
    """
    np.random.seed(42)
    n_stocks = 100
    n_days = 60
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
    
    data = {
        'ts_code': [],
        'trade_date': [],
        'close': [],
        'vol': [],
        'amount': [],
        'turnover_ratio': []
    }
    
    for i in range(n_stocks):
        ts_code = f"00000{i:02d}.SZ" if i < 100 else f"0000{i:02d}.SZ"
        for date in dates:
            data['ts_code'].append(ts_code)
            data['trade_date'].append(date)
            data['close'].append(np.random.uniform(10, 100))
            data['vol'].append(np.random.randint(100000, 5000000))
            data['amount'].append(np.random.randint(100000, 1000000))
            data['turnover_ratio'].append(np.random.uniform(1, 15))
    
    return pd.DataFrame(data)


@pytest.fixture
def config_manager_instance():
    """
    【优化】配置管理器实例 fixture
    """
    from modules.config_manager import ConfigManager
    return ConfigManager()


@pytest.fixture
def strategy_core_instance(filter_config, core_config, strategy_config):
    """
    【优化】策略核心引擎实例 fixture（打板策略）
    """
    from modules.strategy_core import StrategyCore
    return StrategyCore(
        strategy_type="打板策略",
        filter_config=filter_config,
        core_config=core_config,
        strategy_config=strategy_config["打板策略"]
    )


@pytest.fixture
def data_validator_instance():
    """
    【优化】数据校验器实例 fixture
    """
    from modules.data_validator import DataValidator
    return DataValidator()


@pytest.fixture
def sample_exception_data():
    """
    【优化】异常数据 fixture
    包含各种数据质量问题，用于测试校验器
    """
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
    data = {
        'ts_code': ['000001.SZ'] * 10,
        'trade_date': dates,
        'open': [10.0, 10.2, -5.0, 10.3, 10.8, 11.0, 11.2, 11.5, 11.3, 11.8],  # 负值异常
        'high': [10.3, 10.6, 10.8, 10.7, 11.2, 11.4, 11.6, 11.8, 11.7, 12.0],
        'low': [9.8, 10.0, 10.3, 10.1, 10.6, 10.8, 11.0, 11.3, 11.1, 11.6],
        'close': [10.2, 10.5, 0, 10.8, 11.0, 11.2, 25.0, 11.3, 11.8, 12.0],  # 0 值和突变异常
        'vol': [1000000, 1200000, -100, 1500000, 1800000, 2000000, 2200000, 1900000, 2500000, 2800000],  # 负值异常
    }
    return pd.DataFrame(data)
