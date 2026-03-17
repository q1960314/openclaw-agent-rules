#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【优化】数据完整性校验测试脚本
测试 data_validator.py 中的数据完整性校验功能
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_validator import DataValidator


def create_test_data():
    """创建测试数据"""
    # 生成 30 个交易日的测试数据
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    
    # 创建 5 只股票的测试数据
    stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH', '300001.SZ']
    
    data = []
    for stock in stocks:
        for date in dates:
            data.append({
                'ts_code': stock,
                'trade_date': date.strftime('%Y%m%d'),
                'open': np.random.uniform(10, 100),
                'high': np.random.uniform(10, 100),
                'low': np.random.uniform(10, 100),
                'close': np.random.uniform(10, 100),
                'vol': np.random.uniform(1000, 10000),
                'limit': np.random.choice([0, 1], p=[0.9, 0.1]),
                'up_down_times': np.random.randint(1, 5),
                'order_amount': np.random.uniform(0, 20000),
                'break_limit_times': np.random.randint(0, 3),
                'industry': np.random.choice(['科技', '金融', '消费', '制造']),
                'is_main_industry': np.random.choice([0, 1])
            })
    
    df = pd.DataFrame(data)
    return df


def create_incomplete_data():
    """创建不完整的测试数据"""
    df = create_test_data()
    
    # 删除一些列
    df_incomplete = df.drop(columns=['open', 'high'])
    
    # 添加空值
    df_incomplete.loc[df_incomplete.sample(frac=0.1).index, 'close'] = np.nan
    
    return df_incomplete


def test_field_completeness():
    """测试字段完整性检查"""
    print("=" * 70)
    print("【测试 1】字段完整性检查")
    print("=" * 70)
    
    validator = DataValidator()
    
    # 测试完整数据
    df_complete = create_test_data()
    result_complete = validator.check_field_completeness(df_complete, strategy_type='打板策略')
    
    print("\n✅ 完整数据测试：")
    print(f"  是否完整：{result_complete['is_complete']}")
    print(f"  缺失基础字段：{result_complete['missing_base_fields']}")
    print(f"  缺失策略字段：{result_complete['missing_strategy_fields']}")
    
    # 测试不完整数据
    df_incomplete = create_incomplete_data()
    result_incomplete = validator.check_field_completeness(df_incomplete, strategy_type='打板策略')
    
    print("\n❌ 不完整数据测试：")
    print(f"  是否完整：{result_incomplete['is_complete']}")
    print(f"  缺失基础字段：{result_incomplete['missing_base_fields']}")
    print(f"  关键字段空值：{result_incomplete['critical_null_fields']}")
    
    print("\n")


def test_record_count():
    """测试记录数检查"""
    print("=" * 70)
    print("【测试 2】记录数检查")
    print("=" * 70)
    
    validator = DataValidator()
    
    # 测试正常数据
    df = create_test_data()
    date_range = ('2024-01-01', '2024-01-30')
    result = validator.check_record_count(df, date_range=date_range)
    
    print("\n📊 记录数统计：")
    print(f"  总记录数：{result['total_records']}")
    print(f"  股票数量：{result['total_stocks']}")
    print(f"  预期记录数：{result['expected_records']}")
    print(f"  覆盖率：{result['coverage_ratio']*100:.2f}%")
    print(f"  记录数不足的股票：{len(result['insufficient_stocks'])}只")
    print(f"  记录数异常的股票：{len(result['abnormal_stocks'])}只")
    
    print("\n")


def test_trading_continuity():
    """测试交易日连续性检查"""
    print("=" * 70)
    print("【测试 3】交易日连续性检查")
    print("=" * 70)
    
    validator = DataValidator()
    
    # 创建交易日历
    trade_calendar = pd.date_range(start='2024-01-01', periods=30, freq='D').tolist()
    
    # 测试正常数据
    df = create_test_data()
    result = validator.check_trading_day_continuity(df, trade_calendar=trade_calendar)
    
    print("\n📅 连续性检查：")
    print(f"  实际交易日：{result['total_trading_days']}天")
    print(f"  预期交易日：{result['expected_trading_days']}天")
    print(f"  连续性比例：{result['continuity_ratio']*100:.2f}%")
    print(f"  缺失天数：{len(result['missing_days'])}天")
    print(f"  多余天数：{len(result['extra_days'])}天")
    print(f"  中断期数：{len(result['gap_periods'])}个")
    
    print("\n")


def test_data_integrity():
    """测试数据完整性综合校验"""
    print("=" * 70)
    print("【测试 4】数据完整性综合校验")
    print("=" * 70)
    
    validator = DataValidator()
    
    # 测试完整数据
    df = create_test_data()
    date_range = ('2024-01-01', '2024-01-30')
    trade_calendar = pd.date_range(start='2024-01-01', periods=30, freq='D').tolist()
    
    result = validator.validate_data_integrity(
        df, 
        strategy_type='打板策略',
        trade_calendar=trade_calendar,
        date_range=date_range
    )
    
    print("\n📋 完整性校验结果：")
    print(f"  校验结果：{'✅ 通过' if result['is_valid'] else '❌ 未通过'}")
    print(f"  综合得分：{result['overall_score']}/100")
    print(f"  问题数量：{len(result['issues'])}个")
    print(f"  建议数量：{len(result['recommendations'])}条")
    
    print("\n")


def test_integrity_report():
    """测试完整性报告生成"""
    print("=" * 70)
    print("【测试 5】生成数据完整性报告")
    print("=" * 70)
    
    validator = DataValidator()
    
    # 测试完整数据
    df = create_test_data()
    date_range = ('2024-01-01', '2024-01-30')
    trade_calendar = pd.date_range(start='2024-01-01', periods=30, freq='D').tolist()
    
    report = validator.generate_integrity_report(
        df, 
        strategy_type='打板策略',
        trade_calendar=trade_calendar,
        date_range=date_range
    )
    
    print("\n")
    print(report)
    print("\n")


def main():
    """主测试函数"""
    print("\n")
    print("*" * 70)
    print("*  数据完整性校验功能测试")
    print("*" * 70)
    print("\n")
    
    try:
        test_field_completeness()
        test_record_count()
        test_trading_continuity()
        test_data_integrity()
        test_integrity_report()
        
        print("\n")
        print("=" * 70)
        print("✅ 所有测试完成！")
        print("=" * 70)
        print("\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
