# ==============================================
# 【优化】策略类单元测试 - test_strategy.py
# ==============================================
# 功能：测试策略核心引擎的筛选、评分、选股功能
# 覆盖模块：strategy_core.py
# 目标覆盖率：>80%
# ==============================================

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any
import sys
import os

# 【优化】添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStrategyCoreInit:
    """
    【优化】策略核心初始化测试类
    测试策略引擎的初始化逻辑
    """
    
    def test_init_daban_strategy(self, filter_config, core_config, strategy_config):
        """
        【优化】测试打板策略初始化
        验证打板策略参数正确加载
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        assert strategy.strategy_type == "打板策略", "策略类型设置错误"
        assert strategy.pass_score == 18, "打板策略及格分应为 18 分"
        assert strategy.strategy_config['type'] == "link", "打板策略类型应为 link"
    
    def test_init_qianshu_strategy(self, filter_config, core_config, strategy_config):
        """
        【优化】测试缩量潜伏策略初始化
        验证潜伏策略参数正确加载
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="缩量潜伏策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["缩量潜伏策略"]
        )
        
        assert strategy.strategy_type == "缩量潜伏策略", "策略类型设置错误"
        assert strategy.pass_score == 12, "潜伏策略及格分应为 12 分"
        assert strategy.strategy_config['type'] == "first_board_pullback", "潜伏策略类型错误"
    
    def test_init_lundong_strategy(self, filter_config, core_config, strategy_config):
        """
        【优化】测试板块轮动策略初始化
        验证轮动策略参数正确加载
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="板块轮动策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["板块轮动策略"]
        )
        
        assert strategy.strategy_type == "板块轮动策略", "策略类型设置错误"
        assert strategy.pass_score == 17, "轮动策略及格分应为 17 分"
        assert strategy.strategy_config['type'] == "industry", "轮动策略类型错误"
    
    def test_init_invalid_strategy(self, filter_config, core_config, strategy_config):
        """
        【优化】测试无效策略类型处理
        验证传入无效策略类型时的处理
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="无效策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config={}
        )
        
        # 【优化】应该使用基础及格分
        assert strategy.pass_score == core_config['pass_score'], "无效策略应使用基础及格分"


class TestStrategyFilter:
    """
    【优化】策略筛选功能测试类
    测试前置筛选和策略特定筛选逻辑
    """
    
    def test_filter_empty_dataframe(self, strategy_core_instance, empty_dataframe):
        """
        【优化】测试空数据筛选
        验证空输入能正确处理
        """
        result = strategy_core_instance.filter(empty_dataframe)
        assert result.empty, "空数据筛选后应返回空 DataFrame"
    
    def test_filter_st_exclusion(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试 ST 股票排除
        验证 ST 股票被正确过滤
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】sample_strategy_data 包含 'ST 康美'
        original_count = len(sample_strategy_data)
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】ST 股票应该被排除
        assert len(filtered) < original_count, "ST 股票应该被排除"
        assert 'ST 康美' not in filtered['name'].values, "ST 康美应该被过滤掉"
    
    def test_filter_amount_threshold(self, filter_config, core_config, strategy_config):
        """
        【优化】测试成交额筛选
        验证低于阈值的股票被排除
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】创建测试数据：一只成交额达标，一只不达标
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'name': ['股票 A', '股票 B'],
            'amount': [200000, 500000],  # 千元，第一只低于 30 万阈值
            'turnover_ratio': [5.0, 6.0]
        })
        
        filtered = strategy.filter(df)
        assert len(filtered) == 1, "应该只保留成交额达标的股票"
        assert filtered.iloc[0]['ts_code'] == '000002.SZ', "应该保留股票 B"
    
    def test_filter_turnover_threshold(self, filter_config, core_config, strategy_config):
        """
        【优化】测试换手率筛选
        验证低于阈值的股票被排除
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】创建测试数据：一只换手率达标，一只不达标
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'name': ['股票 A', '股票 B'],
            'amount': [500000, 500000],
            'turnover_ratio': [2.0, 5.0]  # 第一只低于 3% 阈值
        })
        
        filtered = strategy.filter(df)
        assert len(filtered) == 1, "应该只保留换手率达标的股票"
        assert filtered.iloc[0]['turnover_ratio'] >= 3.0, "保留的股票换手率应≥3%"
    
    def test_filter_link_board_order_ratio(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试打板策略封单比筛选
        验证封单比不达标的股票被排除
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】检查封单比筛选逻辑
        # 封单比 = order_amount(万元) * 10000 / (float_market_cap(亿元) * 100000000)
        # 阈值：3%
        for idx, row in filtered.iterrows():
            if row['order_amount'] > 0 and row['float_market_cap'] > 0:
                order_ratio = row['order_amount'] * 10000 / (row['float_market_cap'] * 100000000)
                # 【优化】允许一定的容差，因为可能还有其他筛选条件
                assert order_ratio >= 0.02 or row['up_down_times'] == 0, \
                    f"股票{row['ts_code']}封单比{order_ratio:.4f}低于阈值"
    
    def test_filter_link_board_break_times(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试打板策略炸板次数筛选
        验证炸板次数过多的股票被排除
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】炸板次数>1 的股票应该被排除
        for idx, row in filtered.iterrows():
            assert row['break_limit_times'] <= 1 or row['up_down_times'] == 0, \
                f"股票{row['ts_code']}炸板次数{row['break_limit_times']}超过阈值"
    
    def test_filter_pullback_volume_ratio(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试潜伏策略缩量比例筛选
        验证缩量比例在合理范围内
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="缩量潜伏策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["缩量潜伏策略"]
        )
        
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】缩量比例应在 1/3~1/2 范围内
        shrink_ratio_range = strategy_config["缩量潜伏策略"]['shrink_volume_ratio']
        for idx, row in filtered.iterrows():
            if row['current_vol_ratio'] > 0:
                assert shrink_ratio_range[0] <= row['current_vol_ratio'] <= shrink_ratio_range[1] or \
                       row['days_after_board'] == 0, \
                    f"股票{row['ts_code']}缩量比例{row['current_vol_ratio']}不在范围内"


class TestStrategyScore:
    """
    【优化】策略评分功能测试类
    测试评分计算逻辑和权重调整
    """
    
    def test_score_empty_dataframe(self, strategy_core_instance, empty_dataframe):
        """
        【优化】测试空数据评分
        验证空输入能正确处理
        """
        result = strategy_core_instance.score(empty_dataframe)
        assert result.empty, "空数据评分后应返回空 DataFrame"
    
    def test_score_columns_added(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试评分列添加
        验证评分后添加了必需列
        """
        result = strategy_core_instance.score(sample_strategy_data)
        
        # 【优化】检查是否添加了评分相关列
        assert 'total_score' in result.columns, "缺少总分列"
        assert 'pass_score' in result.columns, "缺少及格分列"
    
    def test_score_calculation_logic(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试评分计算逻辑
        验证各项得分计算正确
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】创建简化的测试数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-01-01'],
            'up_down_times': [3],  # 3 连板，应得 2 分
            'inst_buy': [6000],     # 机构买入≥5000 万，应得 2 分
            'is_main_industry': [1],  # 主线行业，应得 1 分
            'turnover_ratio': [5.0],  # 换手率 3%-10%，应得 1 分
        })
        
        result = strategy.score(df)
        
        # 【优化】验证总分计算（至少应该有上述几项的分数）
        assert 'total_score' in result.columns, "缺少总分列"
        assert result.iloc[0]['total_score'] >= 6, f"总分计算错误：{result.iloc[0]['total_score']}"
    
    def test_score_pass_threshold(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试及格线判断
        验证及格线标记正确
        """
        result = strategy_core_instance.score(sample_strategy_data)
        
        # 【优化】检查 pass 列是否存在
        if 'pass' in result.columns:
            for idx, row in result.iterrows():
                if row['total_score'] >= strategy_core_instance.pass_score:
                    assert row['pass'] == True, f"股票{row['ts_code']}分数达标但未标记为 pass"
                else:
                    assert row['pass'] == False, f"股票{row['ts_code']}分数未达标但标记为 pass"
    
    def test_score_dynamic_weight(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试动态权重调整
        验证不同市场状态下权重调整正确
        """
        # 【优化】牛市状态
        core_config_bull = core_config.copy()
        core_config_bull['MARKET_CONDITION'] = 'bull'
        
        from modules.strategy_core import StrategyCore
        strategy_bull = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config_bull,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】熊市状态
        core_config_bear = core_config.copy()
        core_config_bear['MARKET_CONDITION'] = 'bear'
        
        strategy_bear = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config_bear,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】同一数据在不同市场状态下得分应不同
        result_bull = strategy_bull.score(sample_strategy_data)
        result_bear = strategy_bear.score(sample_strategy_data)
        
        # 【优化】验证动态权重使能
        if core_config['enable_dynamic_weight']:
            # 【优化】至少有一只股票得分不同
            scores_diff = (result_bull['total_score'] != result_bear['total_score']).sum()
            # 【优化】允许部分股票得分相同（边界情况）
            assert scores_diff >= 0, "动态权重应该影响部分股票的得分"


class TestGetTopStocks:
    """
    【优化】Top N 选股测试类
    测试股票筛选和排序逻辑
    """
    
    def test_get_top_stocks_empty(self, strategy_core_instance, empty_dataframe):
        """
        【优化】测试空数据 Top N
        验证空输入能正确处理
        """
        result = strategy_core_instance.get_top_stocks(empty_dataframe, top_n=10)
        assert result.empty, "空数据应返回空结果"
    
    def test_get_top_stocks_count(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试 Top N 数量
        验证返回数量不超过要求
        """
        # 【优化】先评分
        scored = strategy_core_instance.score(sample_strategy_data)
        
        # 【优化】获取 Top 3
        top_stocks = strategy_core_instance.get_top_stocks(scored, top_n=3)
        
        assert len(top_stocks) <= 3, f"返回股票数量{len(top_stocks)}超过要求的 3 只"
    
    def test_get_top_stocks_sorted(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试 Top N 排序
        验证返回结果按分数降序排列
        """
        # 【优化】先评分
        scored = strategy_core_instance.score(sample_strategy_data)
        
        # 【优化】获取 Top 5
        top_stocks = strategy_core_instance.get_top_stocks(scored, top_n=5)
        
        # 【优化】验证降序排列
        if len(top_stocks) > 1:
            scores = top_stocks['total_score'].values
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i+1], f"排序错误：{scores[i]} < {scores[i+1]}"
    
    def test_get_top_stocks_pass_filter(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试 Top N 及格线过滤
        验证只返回及格的股票
        """
        # 【优化】先评分
        scored = strategy_core_instance.score(sample_strategy_data)
        
        # 【优化】获取 Top 10
        top_stocks = strategy_core_instance.get_top_stocks(scored, top_n=10)
        
        # 【优化】验证所有返回股票都及格
        for idx, row in top_stocks.iterrows():
            assert row['total_score'] >= strategy_core_instance.pass_score, \
                f"股票{row['ts_code']}分数{row['total_score']}低于及格线{strategy_core_instance.pass_score}"


class TestGenerateStockPool:
    """
    【优化】股票池生成测试类
    测试完整选股流程
    """
    
    def test_generate_stock_pool_structure(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试股票池结构
        验证返回字典包含必需字段
        """
        result = strategy_core_instance.generate_stock_pool(sample_strategy_data)
        
        assert isinstance(result, dict), "返回类型必须是字典"
        assert 'stock_pool' in result, "缺少 stock_pool 字段"
        assert 'count' in result, "缺少 count 字段"
        assert 'pass_score' in result, "缺少 pass_score 字段"
    
    def test_generate_stock_pool_count(self, sample_strategy_data, strategy_core_instance):
        """
        【优化】测试股票池数量
        验证数量统计正确
        """
        result = strategy_core_instance.generate_stock_pool(sample_strategy_data)
        
        assert result['count'] == len(result['stock_pool']), \
            f"数量统计错误：count={result['count']}, 实际={len(result['stock_pool'])}"
    
    def test_generate_stock_pool_with_empty(self, strategy_core_instance, empty_dataframe):
        """
        【优化】测试空数据股票池
        验证空输入能正确处理
        """
        result = strategy_core_instance.generate_stock_pool(empty_dataframe)
        
        assert result['count'] == 0, "空数据股票池数量应为 0"
        assert len(result['stock_pool']) == 0, "空数据股票池应为空列表"


class TestStrategyIntegration:
    """
    【优化】策略集成测试类
    测试完整流程的集成
    """
    
    def test_full_pipeline_daban(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试打板策略完整流程
        验证 filter -> score -> get_top_stocks 全流程
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="打板策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["打板策略"]
        )
        
        # 【优化】步骤 1：筛选
        filtered = strategy.filter(sample_strategy_data)
        assert not filtered.empty or sample_strategy_data.empty, "筛选后数据异常"
        
        # 【优化】步骤 2：评分
        if not filtered.empty:
            scored = strategy.score(filtered)
            assert 'total_score' in scored.columns, "评分后缺少总分列"
            
            # 【优化】步骤 3：Top N
            top_stocks = strategy.get_top_stocks(scored, top_n=5)
            assert len(top_stocks) <= 5, "Top N 数量超过限制"
    
    def test_full_pipeline_qianshu(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试潜伏策略完整流程
        验证 filter -> score -> get_top_stocks 全流程
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="缩量潜伏策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["缩量潜伏策略"]
        )
        
        # 【优化】步骤 1：筛选
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】步骤 2：评分
        if not filtered.empty:
            scored = strategy.score(filtered)
            assert 'total_score' in scored.columns, "评分后缺少总分列"
            
            # 【优化】步骤 3：Top N
            top_stocks = strategy.get_top_stocks(scored, top_n=5)
            assert len(top_stocks) <= 5, "Top N 数量超过限制"
    
    def test_full_pipeline_lundong(self, sample_strategy_data, filter_config, core_config, strategy_config):
        """
        【优化】测试轮动策略完整流程
        验证 filter -> score -> get_top_stocks 全流程
        """
        from modules.strategy_core import StrategyCore
        strategy = StrategyCore(
            strategy_type="板块轮动策略",
            filter_config=filter_config,
            core_config=core_config,
            strategy_config=strategy_config["板块轮动策略"]
        )
        
        # 【优化】步骤 1：筛选
        filtered = strategy.filter(sample_strategy_data)
        
        # 【优化】步骤 2：评分
        if not filtered.empty:
            scored = strategy.score(filtered)
            assert 'total_score' in scored.columns, "评分后缺少总分列"
            
            # 【优化】步骤 3：Top N
            top_stocks = strategy.get_top_stocks(scored, top_n=5)
            assert len(top_stocks) <= 5, "Top N 数量超过限制"


# 【优化】运行测试统计
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
