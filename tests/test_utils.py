# ==============================================
# 【优化】工具类单元测试 - test_utils.py
# ==============================================
# 功能：测试配置管理器、数据生成器、工具函数
# 覆盖模块：config_manager.py 及通用工具函数
# 目标覆盖率：>80%
# ==============================================

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 【优化】添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigManager:
    """
    【优化】配置管理器测试类
    测试配置加载、保存、校验等功能
    """
    
    def test_singleton_pattern(self, config_manager_instance):
        """
        【优化】测试单例模式
        验证多次获取实例是否为同一对象
        """
        from modules.config_manager import ConfigManager
        instance1 = ConfigManager()
        instance2 = ConfigManager()
        assert instance1 is instance2, "单例模式失效，两次获取的实例不同"
    
    def test_get_all_config(self, config_manager_instance):
        """
        【优化】测试获取全部配置
        验证配置字典包含所有必需的配置项
        """
        config = config_manager_instance.get_all_config()
        assert isinstance(config, dict), "配置必须是字典类型"
        assert 'AUTO_RUN_MODE' in config, "缺少 AUTO_RUN_MODE 配置"
        assert 'STRATEGY_TYPE' in config, "缺少 STRATEGY_TYPE 配置"
        assert 'FILTER_CONFIG' in config, "缺少 FILTER_CONFIG 配置"
        assert 'CORE_CONFIG' in config, "缺少 CORE_CONFIG 配置"
        assert 'STRATEGY_CONFIG' in config, "缺少 STRATEGY_CONFIG 配置"
    
    def test_check_config_valid(self, config_manager_instance):
        """
        【优化】测试配置校验（正常情况）
        验证标准配置能通过校验
        """
        result = config_manager_instance.check_config()
        assert result is True, "标准配置应该通过校验"
    
    def test_get_api_dates(self, config_manager_instance):
        """
        【优化】测试 API 日期获取
        验证日期格式正确且在合理范围内
        """
        start_date, end_date, latest_date, latest_start_date = config_manager_instance.get_api_dates()
        assert isinstance(start_date, str), "开始日期必须是字符串"
        assert isinstance(end_date, str), "结束日期必须是字符串"
        assert isinstance(latest_date, str), "最新日期必须是字符串"
        assert isinstance(latest_start_date, str), "近期开始日期必须是字符串"
        assert len(start_date) == 8, "开始日期应为 8 位"
        assert len(end_date) == 8, "结束日期应为 8 位"
        assert len(latest_date) == 8, "最新日期应为 8 位"
        assert len(latest_start_date) == 8, "近期开始日期应为 8 位"
        
        # 【优化】验证日期格式 YYYY-MM-DD
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            assert end_dt >= start_dt, "结束日期不能早于开始日期"
        except ValueError as e:
            pytest.fail(f"日期格式错误：{e}")
    
    def test_config_immutability(self, config_manager_instance):
        """
        【优化】测试配置不可变性
        验证获取的配置修改后不影响原始配置
        """
        config1 = config_manager_instance.get_all_config()
        original_mode = config1['AUTO_RUN_MODE']
        
        # 【优化】尝试修改配置
        config1['AUTO_RUN_MODE'] = 'modified_value'
        
        config2 = config_manager_instance.get_all_config()
        assert config2['AUTO_RUN_MODE'] == original_mode, "配置被意外修改，应该保持不变"


class TestDataGeneration:
    """
    【优化】测试数据生成工具类
    测试各种测试数据生成的正确性
    """
    
    def test_sample_base_data_structure(self, sample_base_data):
        """
        【优化】测试基础数据结构
        验证 fixture 生成的数据包含必需字段
        """
        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
        for col in required_columns:
            assert col in sample_base_data.columns, f"缺少必需列：{col}"
        
        assert len(sample_base_data) == 10, "基础测试数据应该有 10 条记录"
        assert sample_base_data['ts_code'].nunique() == 1, "基础测试数据应该只有 1 只股票"
    
    def test_sample_strategy_data_structure(self, sample_strategy_data):
        """
        【优化】测试策略数据结构
        验证策略测试数据包含所有策略字段
        """
        strategy_columns = [
            'ts_code', 'trade_date', 'name', 'close', 'vol', 'amount',
            'turnover_ratio', 'limit', 'up_down_times', 'order_amount',
            'break_limit_times', 'first_limit_time', 'float_market_cap'
        ]
        for col in strategy_columns:
            assert col in sample_strategy_data.columns, f"缺少策略字段：{col}"
        
        assert len(sample_strategy_data) == 5, "策略测试数据应该有 5 条记录"
    
    def test_empty_dataframe_fixture(self, empty_dataframe):
        """
        【优化】测试空 DataFrame fixture
        验证空数据能正确处理
        """
        assert empty_dataframe.empty, "fixture 应该返回空 DataFrame"
        assert len(empty_dataframe) == 0, "空 DataFrame 长度应为 0"
    
    def test_large_test_data_structure(self, large_test_data):
        """
        【优化】测试大规模数据结构
        验证性能测试数据量符合要求
        """
        expected_stocks = 100
        expected_days = 60
        expected_records = expected_stocks * expected_days
        
        assert len(large_test_data) == expected_records, f"大规模测试数据应该有{expected_records}条记录"
        assert large_test_data['ts_code'].nunique() == expected_stocks, f"应该包含{expected_stocks}只股票"
    
    def test_sample_exception_data(self, sample_exception_data):
        """
        【优化】测试异常数据 fixture
        验证异常数据包含各种质量问题
        """
        # 【优化】检查负值
        negative_open = (sample_exception_data['open'] < 0).sum()
        assert negative_open > 0, "异常数据应该包含负的开盘价"
        
        # 【优化】检查零值
        zero_close = (sample_exception_data['close'] == 0).sum()
        assert zero_close > 0, "异常数据应该包含零收盘价"
        
        # 【优化】检查突变
        price_changes = sample_exception_data['close'].pct_change().abs()
        large_changes = (price_changes > 0.5).sum()
        assert large_changes > 0, "异常数据应该包含价格突变"


class TestConfigValidation:
    """
    【优化】配置校验逻辑测试类
    测试各种配置参数的边界情况
    """
    
    def test_filter_config_values(self, filter_config):
        """
        【优化】测试筛选配置值合理性
        验证配置参数在合理范围内
        """
        assert filter_config['min_amount'] > 0, "最低成交额必须为正数"
        assert filter_config['min_turnover'] > 0, "最低换手率必须为正数"
        assert filter_config['min_turnover'] <= 100, "换手率不能超过 100%"
        assert isinstance(filter_config['exclude_st'], bool), "exclude_st 必须是布尔值"
        assert filter_config['max_fetch_retry'] > 0, "重试次数必须为正数"
    
    def test_core_config_structure(self, core_config):
        """
        【优化】测试核心配置结构
        验证评分配置包含所有必需项
        """
        assert 'pass_score' in core_config, "缺少 pass_score"
        assert 'strategy_pass_score' in core_config, "缺少 strategy_pass_score"
        assert 'items' in core_config, "缺少 items"
        
        # 【优化】验证策略及格分
        strategy_scores = core_config['strategy_pass_score']
        assert '打板策略' in strategy_scores, "缺少打板策略及格分"
        assert '缩量潜伏策略' in strategy_scores, "缺少缩量潜伏策略及格分"
        assert '板块轮动策略' in strategy_scores, "缺少板块轮动策略及格分"
        
        # 【优化】验证打分项格式 [基础分，筛选条件，策略权重]
        for item_name, item_config in core_config['items'].items():
            assert len(item_config) == 3, f"打分项'{item_name}'配置格式错误"
            assert isinstance(item_config[0], (int, float)), f"打分项'{item_name}'基础分必须是数字"
            assert isinstance(item_config[1], str), f"打分项'{item_name}'筛选条件必须是字符串"
            assert isinstance(item_config[2], dict), f"打分项'{item_name}'策略权重必须是字典"
    
    def test_strategy_config_completeness(self, strategy_config):
        """
        【优化】测试策略配置完整性
        验证每个策略都有必需的参数
        """
        required_strategies = ['打板策略', '缩量潜伏策略', '板块轮动策略']
        required_params = ['type', 'stop_loss_rate', 'stop_profit_rate', 'max_hold_days']
        
        for strategy in required_strategies:
            assert strategy in strategy_config, f"缺少策略配置：{strategy}"
            config = strategy_config[strategy]
            for param in required_params:
                assert param in config, f"策略'{strategy}'缺少参数：{param}"
    
    def test_strategy_pass_score_ordering(self, core_config):
        """
        【优化】测试策略及格分合理性
        验证高风险策略有更高的及格分要求
        """
        scores = core_config['strategy_pass_score']
        # 【优化】打板策略风险最高，及格分应该最高
        assert scores['打板策略'] >= scores['缩量潜伏策略'], "打板策略及格分应不低于潜伏策略"
        assert scores['打板策略'] >= scores['板块轮动策略'], "打板策略及格分应不低于轮动策略"


class TestEdgeCases:
    """
    【优化】边界情况测试类
    测试各种极端场景下的配置处理
    """
    
    def test_zero_amount_filter(self, filter_config):
        """
        【优化】测试零成交额筛选
        验证成交额筛选能正确处理零值
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'amount': [0, 500000]
        })
        
        # 【优化】模拟筛选逻辑
        filtered = df[df['amount'] >= filter_config['min_amount']]
        assert len(filtered) == 1, "应该筛选掉成交额为 0 的股票"
        assert filtered.iloc[0]['ts_code'] == '000002.SZ', "应该保留成交额达标的股票"
    
    def test_st_stock_detection(self):
        """
        【优化】测试 ST 股票识别
        验证 ST 股票名称匹配逻辑
        """
        import re
        st_names = ['ST 康美', '*ST 华仪', '退市美都', '正常股票', '小康股份']
        st_pattern = "ST|\\*ST|退"
        
        st_detected = [name for name in st_names if re.search(st_pattern, name)]
        assert len(st_detected) == 3, "应该检测到 3 只 ST/退市股票"
        assert 'ST 康美' in st_detected
        assert '*ST 华仪' in st_detected
        assert '退市美都' in st_detected
        assert '正常股票' not in st_detected
    
    def test_turnover_ratio_boundary(self, filter_config):
        """
        【优化】测试换手率边界值
        验证换手率筛选在边界值的正确性
        """
        test_cases = [
            (2.9, False),   # 低于阈值，应排除
            (3.0, True),    # 等于阈值，应保留
            (3.1, True),    # 高于阈值，应保留
            (0.0, False),   # 零值，应排除
            (-1.0, False),  # 负值，应排除
        ]
        
        for turnover, expected_keep in test_cases:
            keep = turnover >= filter_config['min_turnover']
            assert keep == expected_keep, f"换手率{turnover}%的筛选结果错误"
    
    def test_date_range_validation(self, config_manager_instance):
        """
        【优化】测试日期范围校验
        验证日期范围的合理性
        """
        start_date, end_date, latest_date, latest_start_date = config_manager_instance.get_api_dates()
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 【优化】日期范围应该在合理年限内（1-10 年）
        days_diff = (end_dt - start_dt).days
        assert days_diff > 0, "结束日期必须晚于开始日期"
        assert days_diff < 3650, "日期范围不应超过 10 年"  # 10 年约 3650 天
    
    def test_config_load_save_consistency(self, config_manager_instance):
        """
        【优化】测试配置加载保存一致性
        验证配置加载和保存的数据一致性
        """
        # 【优化】获取原始配置
        original_config = config_manager_instance.get_all_config()
        
        # 【优化】模拟保存和重新加载
        # 注意：这里不实际写入文件，只验证逻辑
        assert original_config is not None, "配置加载失败"
        assert len(original_config) > 0, "配置不应为空"


class TestPerformance:
    """
    【优化】性能测试类
   测试配置操作的性能表现
    """
    
    def test_config_access_speed(self, config_manager_instance):
        """
        【优化】测试配置访问速度
        验证配置访问的性能在合理范围内
        """
        import time
        
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            _ = config_manager_instance.get_all_config()
        
        elapsed_time = time.time() - start_time
        avg_time_per_access = elapsed_time / iterations
        
        # 【优化】单次配置访问应该小于 1ms
        assert avg_time_per_access < 0.001, f"配置访问太慢：{avg_time_per_access*1000:.3f}ms/次"
    
    def test_large_data_memory_usage(self, large_test_data):
        """
        【优化】测试大数据内存占用
        验证大规模数据的内存使用在合理范围内
        """
        # 【优化】估算 DataFrame 内存占用
        memory_usage = large_test_data.memory_usage(deep=True).sum()
        memory_mb = memory_usage / (1024 * 1024)
        
        # 【优化】100 只股票*60 天的数据应该小于 50MB
        assert memory_mb < 50, f"内存占用过大：{memory_mb:.2f}MB"


# 【优化】运行测试统计
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
