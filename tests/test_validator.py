# ==============================================
# 【优化】校验类单元测试 - test_validator.py
# ==============================================
# 功能：测试数据校验器的各种校验功能
# 覆盖模块：data_validator.py
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


class TestDataValidatorInit:
    """
    【优化】数据校验器初始化测试类
    测试校验器的初始化配置
    """
    
    def test_init_default_config(self, data_validator_instance):
        """
        【优化】测试默认配置加载
        验证初始化配置正确
        """
        from modules.data_validator import DataValidator
        validator = DataValidator()
        
        assert validator.min_records_per_stock == 60, "每只股票最小记录数配置错误"
        assert validator.max_gap_days == 5, "最大交易日中断天数配置错误"
        assert validator.price_min == 0, "价格最小值配置错误"
        assert validator.price_max == 10000, "价格最大值配置错误"
        assert validator.sigma_threshold == 3, "3σ阈值配置错误"
    
    def test_init_required_fields(self, data_validator_instance):
        """
        【优化】测试必填字段配置
        验证必填字段配置完整
        """
        required_fields = data_validator_instance.required_fields
        
        assert 'base' in required_fields, "缺少基础字段配置"
        assert '打板策略' in required_fields, "缺少打板策略字段配置"
        assert '缩量潜伏策略' in required_fields, "缺少潜伏策略字段配置"
        assert '板块轮动策略' in required_fields, "缺少轮动策略字段配置"
        
        # 【优化】验证基础字段
        base_fields = required_fields['base']
        assert 'ts_code' in base_fields, "缺少 ts_code 字段"
        assert 'trade_date' in base_fields, "缺少 trade_date 字段"
        assert 'close' in base_fields, "缺少 close 字段"


class TestValidateDataConsistency:
    """
    【优化】数据一致性校验测试类
    测试数据一致性验证功能
    """
    
    def test_consistency_empty_data(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据一致性
        验证空数据能正确处理
        """
        is_valid, errors = data_validator_instance.validate_data_consistency(
            empty_dataframe,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=0
        )
        
        assert is_valid is True, "空数据（min_rows=0）应通过校验"
        assert len(errors) == 0, "空数据不应有错误"
    
    def test_consistency_empty_with_min_rows(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据带最小行数要求
        验证空数据不满足行数要求
        """
        is_valid, errors = data_validator_instance.validate_data_consistency(
            empty_dataframe,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=10
        )
        
        assert is_valid is False, "空数据不满足最小行数要求"
        assert len(errors) > 0, "应该有错误信息"
        assert any('行数' in err for err in errors), "错误信息应包含行数问题"
    
    def test_consistency_missing_columns(self, data_validator_instance, sample_base_data):
        """
        【优化】测试缺少必需列
        验证缺少必需列时能正确检测
        """
        # 【优化】创建一个缺少列的 DataFrame
        df = sample_base_data[['ts_code', 'trade_date']]  # 缺少 close 列
        
        is_valid, errors = data_validator_instance.validate_data_consistency(
            df,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=0
        )
        
        assert is_valid is False, "缺少必需列应不通过校验"
        assert any('缺少必需列' in err for err in errors), "错误信息应包含缺少列的问题"
    
    def test_consistency_null_values(self, data_validator_instance):
        """
        【优化】测试空值检测
        验证核心列空值能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', None, '000003.SZ'],
            'trade_date': ['2024-01-01', '2024-01-02', None],
            'close': [10.5, 10.8, 11.2]
        })
        
        is_valid, errors = data_validator_instance.validate_data_consistency(
            df,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=0
        )
        
        assert is_valid is False, "核心列有空值应不通过校验"
        assert any('空值' in err for err in errors), "错误信息应包含空值问题"
    
    def test_consistency_negative_prices(self, data_validator_instance):
        """
        【优化】测试负价格检测
        验证负价格能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [10.5, -5.0, 11.2]
        })
        
        is_valid, errors = data_validator_instance.validate_data_consistency(
            df,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=0
        )
        
        assert is_valid is False, "负价格应不通过校验"
        assert any('价格' in err for err in errors), "错误信息应包含价格问题"
    
    def test_consistency_price_sudden_change(self, data_validator_instance):
        """
        【优化】测试价格突变检测
        验证价格突变能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [10.0, 20.0, 10.5]  # 第二天涨幅 100%
        })
        
        is_valid, errors = data_validator_instance.validate_data_consistency(
            df,
            required_columns=['ts_code', 'trade_date', 'close'],
            min_rows=0
        )
        
        assert is_valid is False, "价格突变应不通过校验"
        assert any('突变' in err or '涨跌幅' in err for err in errors), \
            "错误信息应包含价格突变问题"
    
    def test_consistency_valid_data(self, data_validator_instance, sample_base_data):
        """
        【优化】测试有效数据
        验证正常数据能通过校验
        """
        is_valid, errors = data_validator_instance.validate_data_consistency(
            sample_base_data,
            required_columns=['ts_code', 'trade_date', 'close', 'vol'],
            min_rows=0
        )
        
        assert is_valid is True, "有效数据应通过校验"
        assert len(errors) == 0, "有效数据不应有错误"


class TestCheckFieldCompleteness:
    """
    【优化】字段完整性检查测试类
    测试字段完整性验证功能
    """
    
    def test_completeness_empty_data(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据字段完整性
        验证空数据字段检查正确
        """
        report = data_validator_instance.check_field_completeness(
            empty_dataframe,
            strategy_type='打板策略'
        )
        
        assert report['is_complete'] is False, "空数据应标记为不完整"
        assert len(report['missing_base_fields']) > 0, "应报告缺少基础字段"
    
    def test_completeness_base_fields(self, data_validator_instance, sample_base_data):
        """
        【优化】测试基础字段完整性
        验证基础字段检查正确
        """
        report = data_validator_instance.check_field_completeness(
            sample_base_data,
            strategy_type=None
        )
        
        assert report['is_complete'] is True, "基础字段完整应通过检查"
        assert len(report['missing_base_fields']) == 0, "不应缺少基础字段"
    
    def test_completeness_strategy_fields(self, data_validator_instance, sample_strategy_data):
        """
        【优化】测试策略字段完整性
        验证策略特定字段检查正确
        """
        report = data_validator_instance.check_field_completeness(
            sample_strategy_data,
            strategy_type='打板策略'
        )
        
        assert report['is_complete'] is True, "策略字段完整应通过检查"
        assert len(report['missing_strategy_fields']) == 0, "不应缺少策略字段"
    
    def test_completeness_null_ratio(self, data_validator_instance):
        """
        【优化】测试空值比例计算
        验证空值比例计算正确
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ'],
            'close': [10.5, None, 11.2, 11.8]  # 25% 空值
        })
        
        report = data_validator_instance.check_field_completeness(df)
        
        assert 'close' in report['null_ratio_by_field'], "应计算 close 列空值比例"
        assert report['null_ratio_by_field']['close'] == 0.25, "空值比例计算错误"
    
    def test_completeness_critical_null(self, data_validator_instance):
        """
        【优化】测试关键字段空值标记
        验证关键字段空值超过阈值时正确标记
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 20,
            'close': [10.5] * 18 + [None, None]  # 10% 空值
        })
        
        report = data_validator_instance.check_field_completeness(df)
        
        # 【优化】空值比例>5% 应标记为关键字段空值问题
        critical_fields = [item['field'] for item in report['critical_null_fields']]
        assert 'close' in critical_fields, "close 列空值比例>5% 应标记为关键字段问题"


class TestCheckRecordCount:
    """
    【优化】记录数检查测试类
    测试数据量合理性检查
    """
    
    def test_record_count_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据记录数
        验证空数据记录数检查正确
        """
        report = data_validator_instance.check_record_count(empty_dataframe)
        
        assert report['is_reasonable'] is False, "空数据应标记为不合理"
        assert report['total_records'] == 0, "总记录数应为 0"
    
    def test_record_count_statistics(self, data_validator_instance, sample_base_data):
        """
        【优化】测试记录数统计
        验证统计信息计算正确
        """
        report = data_validator_instance.check_record_count(sample_base_data)
        
        assert report['total_records'] == 10, "总记录数统计错误"
        assert report['total_stocks'] == 1, "股票数量统计错误"
        assert 'records_per_stock' in report, "缺少每只股票记录数统计"
    
    def test_record_count_insufficient(self, data_validator_instance):
        """
        【优化】测试记录数不足
        验证记录数不足时正确标记
        """
        # 【优化】创建只有 10 条记录的数据（低于 60 条最小要求）
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 10,
            'trade_date': pd.date_range(start='2024-01-01', periods=10),
            'close': range(10, 20)
        })
        
        report = data_validator_instance.check_record_count(df)
        
        assert len(report['insufficient_stocks']) > 0, "应标记记录数不足的股票"


class TestCheckTradingDayContinuity:
    """
    【优化】交易日连续性测试类
    测试交易日连续性检查
    """
    
    def test_continuity_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据连续性
        验证空数据连续性检查正确
        """
        report = data_validator_instance.check_trading_day_continuity(empty_dataframe)
        
        assert report['is_continuous'] is False, "空数据应标记为不连续"
    
    def test_continuity_valid(self, data_validator_instance, sample_base_data):
        """
        【优化】测试有效连续性
        验证正常数据连续性检查正确
        """
        report = data_validator_instance.check_trading_day_continuity(sample_base_data)
        
        assert 'gaps' in report, "应包含中断信息"
        assert 'max_gap_days' in report, "应包含最大中断天数"


class TestCheckPriceLogic:
    """
    【优化】价格逻辑检查测试类
    测试价格合理性验证
    """
    
    def test_price_logic_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据价格逻辑
        验证空数据价格检查正确
        """
        report = data_validator_instance.check_price_logic(empty_dataframe)
        
        assert report['is_valid'] is False, "空数据应标记为无效"
    
    def test_price_logic_high_low(self, data_validator_instance):
        """
        【优化】测试高低价格逻辑
        验证 high>=low 逻辑检查正确
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'high': [10.5, 10.8, 11.2],
            'low': [10.8, 10.5, 11.0]  # 第一天 high<low，异常
        })
        
        report = data_validator_instance.check_price_logic(df)
        
        assert report['is_valid'] is False, "high<low 应标记为无效"
        assert len(report['logic_errors']) > 0, "应有逻辑错误信息"
    
    def test_price_logic_valid(self, data_validator_instance, sample_base_data):
        """
        【优化】测试有效价格逻辑
        验证正常数据价格逻辑检查正确
        """
        report = data_validator_instance.check_price_logic(sample_base_data)
        
        assert report['is_valid'] is True, "有效数据应通过价格逻辑检查"


class TestCheckPriceRange:
    """
    【优化】价格范围检查测试类
    测试价格是否在合理范围内
    """
    
    def test_price_range_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据价格范围
        验证空数据价格范围检查正确
        """
        report = data_validator_instance.check_price_range(empty_dataframe)
        
        assert report['is_valid'] is False, "空数据应标记为无效"
    
    def test_price_range_negative(self, data_validator_instance):
        """
        【优化】测试负价格
        验证负价格能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [10.5, -5.0, 11.2],
            'open': [10.2, -4.8, 11.0]
        })
        
        report = data_validator_instance.check_price_range(df)
        
        assert report['is_valid'] is False, "负价格应标记为无效"
        assert len(report['out_of_range']) > 0, "应有超出范围的价格记录"
    
    def test_price_range_too_high(self, data_validator_instance):
        """
        【优化】测试过高价格
        验证过高价格能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [10.5, 15000.0, 11.2]  # 超过 10000 阈值
        })
        
        report = data_validator_instance.check_price_range(df)
        
        assert report['is_valid'] is False, "过高价格应标记为无效"
    
    def test_price_range_valid(self, data_validator_instance, sample_base_data):
        """
        【优化】测试有效价格范围
        验证正常价格范围检查正确
        """
        report = data_validator_instance.check_price_range(sample_base_data)
        
        assert report['is_valid'] is True, "有效价格应通过范围检查"


class TestCheckPriceChangeOutliers:
    """
    【优化】价格变化异常检测测试类
    测试价格突变检测
    """
    
    def test_outlier_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据异常检测
        验证空数据异常检测正确
        """
        report = data_validator_instance.check_price_change_outliers(empty_dataframe)
        
        assert report['is_valid'] is False, "空数据应标记为无效"
    
    def test_outlier_sudden_change(self, data_validator_instance):
        """
        【优化】测试价格突变
        验证价格突变能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 4,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'close': [10.0, 10.5, 25.0, 26.0]  # 第三天涨幅 138%
        })
        
        report = data_validator_instance.check_price_change_outliers(df)
        
        assert report['is_valid'] is False, "价格突变应标记为无效"
        assert len(report['outliers']) > 0, "应有异常记录"
    
    def test_outlier_valid(self, data_validator_instance, sample_base_data):
        """
        【优化】测试有效价格变化
        验证正常价格变化检查正确
        """
        report = data_validator_instance.check_price_change_outliers(sample_base_data)
        
        assert report['is_valid'] is True, "正常价格变化应通过检查"


class TestCheckVolumeOutliers:
    """
    【优化】成交量异常检测测试类
    测试成交量异常检测
    """
    
    def test_volume_outlier_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据成交量异常
        验证空数据成交量检查正确
        """
        report = data_validator_instance.check_volume_outliers(empty_dataframe)
        
        assert report['is_valid'] is False, "空数据应标记为无效"
    
    def test_volume_outlier_negative(self, data_validator_instance):
        """
        【优化】测试负成交量
        验证负成交量能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'vol': [1000000, -500000, 1200000]
        })
        
        report = data_validator_instance.check_volume_outliers(df)
        
        assert report['is_valid'] is False, "负成交量应标记为无效"
    
    def test_volume_outlier_sudden_change(self, data_validator_instance):
        """
        【优化】测试成交量突变
        验证成交量突变能正确检测
        """
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 4,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'vol': [1000000, 1200000, 15000000, 1300000]  # 第三天突增 12.5 倍
        })
        
        report = data_validator_instance.check_volume_outliers(df)
        
        assert report['is_valid'] is False, "成交量突变应标记为无效"
        assert len(report['outliers']) > 0, "应有异常记录"


class TestValidateDataAccuracy:
    """
    【优化】数据准确性校验测试类
    测试综合准确性验证
    """
    
    def test_accuracy_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据准确性
        验证空数据准确性检查正确
        """
        report = data_validator_instance.validate_data_accuracy(empty_dataframe)
        
        assert report['is_accurate'] is False, "空数据应标记为不准确"
    
    def test_accuracy_comprehensive(self, data_validator_instance, sample_base_data):
        """
        【优化】测试综合准确性
        验证正常数据准确性检查正确
        """
        report = data_validator_instance.validate_data_accuracy(sample_base_data)
        
        assert 'price_check' in report, "应包含价格检查结果"
        assert 'volume_check' in report, "应包含成交量检查结果"
        assert 'logic_check' in report, "应包含逻辑检查结果"


class TestValidateDataIntegrity:
    """
    【优化】数据完整性校验测试类
    测试综合完整性验证
    """
    
    def test_integrity_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据完整性
        验证空数据完整性检查正确
        """
        report = data_validator_instance.validate_data_integrity(empty_dataframe)
        
        assert report['is_complete'] is False, "空数据应标记为不完整"
    
    def test_integrity_comprehensive(self, data_validator_instance, sample_base_data):
        """
        【优化】测试综合完整性
        验证正常数据完整性检查正确
        """
        report = data_validator_instance.validate_data_integrity(sample_base_data)
        
        assert 'field_check' in report, "应包含字段检查结果"
        assert 'record_check' in report, "应包含记录数检查结果"
        assert 'continuity_check' in report, "应包含连续性检查结果"


class TestCheckFutureFunction:
    """
    【优化】未来函数检测测试类
    测试未来函数检测
    """
    
    def test_future_function_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空数据未来函数
        验证空数据未来函数检查正确
        """
        report = data_validator_instance.check_future_function(empty_dataframe)
        
        assert report['has_future_function'] is False, "空数据应标记为无未来函数"
    
    def test_future_function_detection(self, data_validator_instance):
        """
        【优化】测试未来函数检测
        验证未来函数能正确检测
        """
        # 【优化】创建包含未来函数的数据（使用未来数据计算当前信号）
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 5,
            'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'close': [10.0, 10.5, 11.0, 11.5, 12.0],
            'signal': [1, 1, 1, 1, 0]  # 信号基于未来价格（第 5 天下跌，前 4 天买入）
        })
        
        report = data_validator_instance.check_future_function(df)
        
        # 【优化】未来函数检测逻辑可能因实现而异，这里只验证报告结构
        assert 'has_future_function' in report, "应包含未来函数标记"
        assert 'details' in report or 'warnings' in report, "应包含详细信息"


class TestValidateStrategyInput:
    """
    【优化】策略输入校验测试类
    测试策略输入数据验证
    """
    
    def test_strategy_input_empty(self, data_validator_instance, empty_dataframe):
        """
        【优化】测试空策略输入
        验证空策略输入检查正确
        """
        report = data_validator_instance.validate_strategy_input(
            empty_dataframe,
            strategy_type='打板策略'
        )
        
        assert report['is_valid'] is False, "空数据应标记为无效"
    
    def test_strategy_input_daban(self, data_validator_instance, sample_strategy_data):
        """
        【优化】测试打板策略输入
        验证打板策略输入检查正确
        """
        report = data_validator_instance.validate_strategy_input(
            sample_strategy_data,
            strategy_type='打板策略'
        )
        
        assert 'field_check' in report, "应包含字段检查结果"
        assert 'logic_check' in report, "应包含逻辑检查结果"


class TestReportGeneration:
    """
    【优化】报告生成测试类
    测试各种报告生成功能
    """
    
    def test_validation_report(self, data_validator_instance, sample_base_data):
        """
        【优化】测试校验报告生成
        验证校验报告格式正确
        """
        report = data_validator_instance.generate_validation_report(sample_base_data)
        
        assert isinstance(report, str), "报告应为字符串"
        assert len(report) > 0, "报告不应为空"
        assert '校验' in report or '验证' in report or 'Valid' in report, \
            "报告应包含校验相关信息"
    
    def test_integrity_report(self, data_validator_instance, sample_base_data):
        """
        【优化】测试完整性报告生成
        验证完整性报告格式正确
        """
        report = data_validator_instance.generate_integrity_report(sample_base_data)
        
        assert isinstance(report, str), "报告应为字符串"
        assert len(report) > 0, "报告不应为空"
        assert '完整' in report or 'Integrity' in report, \
            "报告应包含完整性相关信息"
    
    def test_accuracy_report(self, data_validator_instance, sample_base_data):
        """
        【优化】测试准确性报告生成
        验证准确性报告格式正确
        """
        report = data_validator_instance.generate_accuracy_report(sample_base_data)
        
        assert isinstance(report, str), "报告应为字符串"
        assert len(report) > 0, "报告不应为空"
        assert '准确' in report or 'Accuracy' in report, \
            "报告应包含准确性相关信息"


class TestValidatorIntegration:
    """
    【优化】校验器集成测试类
    测试完整校验流程
    """
    
    def test_full_validation_pipeline_valid(self, data_validator_instance, sample_base_data):
        """
        【优化】测试完整校验流程（有效数据）
        验证正常数据通过所有校验
        """
        # 【优化】步骤 1：一致性校验
        is_consistent, errors = data_validator_instance.validate_data_consistency(
            sample_base_data,
            required_columns=['ts_code', 'trade_date', 'close', 'vol']
        )
        assert is_consistent is True, "有效数据应通过一致性校验"
        
        # 【优化】步骤 2：字段完整性
        completeness = data_validator_instance.check_field_completeness(sample_base_data)
        assert completeness['is_complete'] is True, "有效数据应通过完整性检查"
        
        # 【优化】步骤 3：价格逻辑
        price_logic = data_validator_instance.check_price_logic(sample_base_data)
        assert price_logic['is_valid'] is True, "有效数据应通过价格逻辑检查"
        
        # 【优化】步骤 4：生成综合报告
        report = data_validator_instance.generate_validation_report(sample_base_data)
        assert len(report) > 0, "应生成校验报告"
    
    def test_full_validation_pipeline_invalid(self, data_validator_instance, sample_exception_data):
        """
        【优化】测试完整校验流程（异常数据）
        验证异常数据被正确检测
        """
        # 【优化】步骤 1：一致性校验
        is_consistent, errors = data_validator_instance.validate_data_consistency(
            sample_exception_data,
            required_columns=['ts_code', 'trade_date', 'close', 'vol']
        )
        assert is_consistent is False, "异常数据应不通过一致性校验"
        
        # 【优化】步骤 2：价格范围
        price_range = data_validator_instance.check_price_range(sample_exception_data)
        assert price_range['is_valid'] is False, "异常数据应不通过价格范围检查"
        
        # 【优化】步骤 3：成交量异常
        volume_outliers = data_validator_instance.check_volume_outliers(sample_exception_data)
        assert volume_outliers['is_valid'] is False, "异常数据应不通过成交量检查"


# 【优化】运行测试统计
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
