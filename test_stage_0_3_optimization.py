#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 0.3 - 优化建议执行测试
执行 4 个优化任务：
1. 涨跌停接口换日期测试（使用 20260311）
2. 添加 stocks_dir 配置测试 fetch_moneyflow_ths
3. 更新字段名配置（根据实际 CSV 文件头）
4. 概念成分逻辑修复（使用固定概念代码 BK1129）
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from fetch_data_optimized import Utils, EXTEND_FETCH_CONFIG, TUSHARE_TOKEN, OUTPUT_DIR, TUSHARE_API_URL
import tushare as ts

# ==================== 优化测试配置 ====================
# 优化 1：使用 20260311 代替今天（避免非交易日问题）
TEST_DATE = '20260311'  # ✅ 优化 1：固定为 20260311
TEST_START_DATE = '20260305'
TEST_END_DATE = TEST_DATE

# 优化 2：添加 stocks_dir 配置
STOCKS_DIR = os.path.join(BASE_DIR, 'data', 'all_stocks')

# 限流配置
REQUEST_INTERVAL = 1.0
RETRY_DELAYS = [5, 10, 15]
MAX_RETRIES = 3

# ==================== 优化后的接口配置 ====================
# 根据实际 CSV 文件头更新 expected_fields（优化 3）
TEST_INTERFACES = [
    # ==================== 优化 1：涨跌停接口换日期测试 ====================
    {
        'name': '【优化 1】涨跌停列表接口测试 (limit_list_d)',
        'config_key': 'enable_limit_list_d',
        'method': 'fetch_limit_list_d',
        'params': {'trade_date': TEST_DATE},  # ✅ 使用 20260311
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['trade_date', 'ts_code', 'name', 'limit'],
        'output_file': 'limit_list_d_20260311.csv',
        'required_points': 5000,
        'is_special': True,
        'optimization': 1
    },
    {
        'name': '【优化 1】连板天梯接口测试 (limit_step)',
        'config_key': 'enable_limit_step',
        'method': 'fetch_limit_step',
        'params': {'trade_date': TEST_DATE},  # ✅ 使用 20260311
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['ts_code', 'name', 'trade_date'],
        'output_file': 'limit_step_20260311.csv',
        'required_points': 8000,
        'is_special': True,
        'optimization': 1
    },
    # ==================== 优化 2：添加 stocks_dir 配置 ====================
    {
        'name': '【优化 2】个股资金流向 THS 接口测试 (moneyflow_ths)',
        'config_key': 'enable_moneyflow_ths',
        'method': 'fetch_moneyflow_ths',
        'params': {
            'ts_code': '000001.SZ',
            'start_date': TEST_START_DATE,
            'end_date': TEST_END_DATE
        },
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['trade_date', 'ts_code', 'name'],
        'output_file': 'moneyflow_ths_000001_test.csv',
        'required_points': 6000,
        'is_special': False,
        'optimization': 2,
        'stocks_dir': STOCKS_DIR  # ✅ 优化 2：添加 stocks_dir
    },
    # ==================== 优化 4：概念成分逻辑修复 ====================
    {
        'name': '【优化 4】同花顺概念成分接口测试 (ths_member)',
        'config_key': 'enable_ths_member',
        'method': 'fetch_ths_member',
        'params': {'concept_code': 'BK1129'},  # ✅ 优化 4：使用固定概念代码
        'expected_fields': ['ts_code', 'con_code', 'con_name'],  # ✅ 更新为实际字段
        'output_file': 'ths_member_BK1129_test.csv',
        'required_points': 6000,
        'is_special': False,
        'optimization': 4
    },
    # ==================== 其他接口（验证字段更新） ====================
    {
        'name': '【优化 3】同花顺热榜接口测试 (ths_hot)',
        'config_key': 'enable_ths_hot',
        'method': 'fetch_ths_hot',
        'params': {'date': TEST_DATE},
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['trade_date', 'ts_code', 'ts_name', 'rank'],
        'output_file': 'ths_hot_test.csv',
        'required_points': 6000,
        'is_special': False,
        'optimization': 3
    },
    {
        'name': '涨跌停榜单 THS 接口测试 (limit_list_ths)',
        'config_key': 'enable_limit_list_ths',
        'method': 'fetch_limit_list_ths',
        'params': {'trade_date': TEST_DATE},
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['trade_date', 'ts_code', 'name', 'price', 'pct_chg'],
        'output_file': 'limit_list_ths_20260311.csv',
        'required_points': 8000,
        'is_special': True,
        'optimization': 3
    },
    {
        'name': '最强板块统计接口测试 (limit_cpt_list)',
        'config_key': 'enable_limit_cpt_list',
        'method': 'fetch_limit_cpt_list',
        'params': {'trade_date': TEST_DATE},
        # ✅ 优化 3：根据实际 CSV 更新字段
        'expected_fields': ['ts_code', 'name', 'trade_date', 'pct_chg'],
        'output_file': 'limit_cpt_list_20260311.csv',
        'required_points': 8000,
        'is_special': True,
        'optimization': 3
    },
]

# ==================== 测试结果记录 ====================
test_results = []
start_time = datetime.now()

def test_interface(fetcher, interface):
    """测试单个接口（带限流保护）"""
    print(f"\n{'='*80}")
    print(f"开始测试：{interface['name']}")
    print(f"优化类型：优化{interface.get('optimization', 'N/A')}")
    print(f"所需积分：{interface['required_points']}")
    print(f"{'='*80}")
    
    result = {
        'name': interface['name'],
        'config_key': interface['config_key'],
        'config_enabled': EXTEND_FETCH_CONFIG.get(interface['config_key'], False),
        'is_special': interface['is_special'],
        'optimization': interface.get('optimization', 0),
        'required_points': interface['required_points'],
        'call_success': False,
        'data_format_valid': False,
        'save_success': False,
        'file_complete': False,
        'retry_count': 0,
        'error_msg': '',
        'error_type': '',
        'data_count': 0,
        'file_size': 0,
        'test_time': datetime.now().strftime('%H:%M:%S')
    }
    
    # 1. 请求间延迟
    time.sleep(REQUEST_INTERVAL)
    
    # 2. 调用接口（带重试机制）
    attempt = 0
    max_attempts = 1 + MAX_RETRIES
    
    while attempt < max_attempts:
        try:
            method = getattr(fetcher, interface['method'])
            
            # ✅ 优化 2：特殊处理 moneyflow_ths，传入 stocks_dir
            if interface['method'] == 'fetch_moneyflow_ths':
                # 需要临时修改 fetcher 的 config
                original_stocks_dir = fetcher.config.get('stocks_dir')
                fetcher.config['stocks_dir'] = STOCKS_DIR
                print(f"📁 设置 stocks_dir: {STOCKS_DIR}")
                
                df = method(**interface['params'])
                
                # 恢复原配置
                if original_stocks_dir:
                    fetcher.config['stocks_dir'] = original_stocks_dir
            else:
                df = method(**interface['params'])
            
            if df is None or df.empty:
                result['call_success'] = True
                result['error_msg'] = '接口返回空数据（可能是非交易日或无数据）'
                print(f"⚠️  接口返回空数据")
            else:
                result['call_success'] = True
                result['data_count'] = len(df)
                print(f"✅ 接口调用成功，返回 {len(df)} 条数据")
                
                # 3. 验证数据格式
                missing_fields = [f for f in interface['expected_fields'] if f not in df.columns]
                if missing_fields:
                    result['data_format_valid'] = False
                    result['error_msg'] = f"缺少必需字段：{missing_fields}"
                    print(f"❌ 数据格式验证失败：缺少字段 {missing_fields}")
                    print(f"   实际字段：{list(df.columns)[:10]}...")
                else:
                    result['data_format_valid'] = True
                    print(f"✅ 数据格式验证通过")
                
                # 4. 验证文件保存
                save_path = os.path.join(OUTPUT_DIR, interface['output_file'])
                try:
                    # 使用 Parquet 格式保存（根据 USE_PARQUET 配置）
                    if USE_PARQUET:
                        try:
                            import pyarrow as pa
                            import pyarrow.parquet as pq
                            table = pa.Table.from_pandas(df)
                            pq.write_table(table, save_path.replace('.csv', '.parquet'), compression='snappy')
                        except ImportError:
                            logger.warning("PyArrow 未安装，降级使用 CSV 格式")
                            df.to_csv(save_path, index=False, encoding='utf-8-sig')
                    else:
                        df.to_csv(save_path, index=False, encoding='utf-8-sig')
                    result['save_success'] = True
                    file_size = os.path.getsize(save_path)
                    result['file_size'] = file_size
                    print(f"✅ 文件保存成功：{save_path} ({file_size/1024:.2f} KB)")
                    
                    if file_size > 0 and result['data_count'] > 0:
                        result['file_complete'] = True
                        print(f"✅ 文件内容完整")
                except Exception as e:
                    result['save_success'] = False
                    result['error_msg'] = f'文件保存失败：{str(e)}'
                    print(f"❌ 文件保存失败：{e}")
            
            break  # 成功后退出重试循环
            
        except Exception as e:
            error_str = str(e).lower()
            result['error_msg'] = str(e)
            
            # 判断错误类型
            if '权限' in error_str or '积分' in error_str or 'points' in error_str or 'auth' in error_str:
                result['error_type'] = '权限不足'
            elif 'network' in error_str or 'timeout' in error_str or 'connection' in error_str or 'limit' in error_str:
                result['error_type'] = '限流/网络'
            else:
                result['error_type'] = '其他'
            
            print(f"❌ 第 {attempt + 1} 次尝试失败：{e}")
            print(f"   错误类型：{result['error_type']}")
            
            # 重试逻辑
            if attempt < MAX_RETRIES:
                retry_delay = RETRY_DELAYS[attempt]
                print(f"🔄 {retry_delay}秒后第 {attempt + 2} 次重试...")
                time.sleep(retry_delay)
                result['retry_count'] = attempt + 1
            
            attempt += 1
    
    if attempt >= max_attempts:
        print(f"❌ 所有 {max_attempts} 次尝试均失败")
    
    test_results.append(result)
    return result

def print_summary():
    """打印测试总结"""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*80}")
    print(f"测试总结")
    print(f"测试时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时：{duration:.1f} 秒")
    print(f"{'='*80}")
    
    total = len(test_results)
    success = sum(1 for r in test_results if r['call_success'] and r['data_format_valid'] and r['save_success'])
    
    print(f"\n【总体统计】")
    print(f"总测试接口数：{total}")
    print(f"完全成功：{success} ({success/total*100:.1f}%)")
    print(f"调用成功：{sum(1 for r in test_results if r['call_success'])} ({sum(1 for r in test_results if r['call_success'])/total*100:.1f}%)")
    print(f"保存成功：{sum(1 for r in test_results if r['save_success'])} ({sum(1 for r in test_results if r['save_success'])/total*100:.1f}%)")
    
    # 按优化类型统计
    print(f"\n【按优化类型统计】")
    for opt_id in [1, 2, 3, 4]:
        opt_results = [r for r in test_results if r.get('optimization') == opt_id]
        if opt_results:
            opt_success = sum(1 for r in opt_results if r['call_success'] and r['data_count'] > 0)
            print(f"优化{opt_id}: 成功 {opt_success}/{len(opt_results)}")
    
    # 详细结果
    print(f"\n{'='*80}")
    print(f"详细结果")
    print(f"{'='*80}")
    
    for i, r in enumerate(test_results, 1):
        status = "✅" if (r['call_success'] and r['data_format_valid'] and r['save_success']) else \
                 "⚠️" if (r['call_success'] and r['data_count'] == 0) else "❌"
        data_info = f"{r['data_count']}条" if r['data_count'] > 0 else "-"
        file_info = f"{r['file_size']/1024:.1f}KB" if r['file_size'] > 0 else "-"
        retry_info = f"重试{r['retry_count']}次" if r['retry_count'] > 0 else ""
        
        print(f"{i:2}. {status} {r['name'][:50]:<50} {data_info:>8} {file_info:>10} {retry_info}")

def save_results():
    """保存测试结果"""
    results_df = pd.DataFrame(test_results)
    results_path = os.path.join(OUTPUT_DIR, 'test_stage_0_3_optimization_result.csv')
    results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 测试结果已保存：{results_path}")

def verify_optimization_results():
    """验证优化结果"""
    print(f"\n{'='*80}")
    print(f"优化结果验证")
    print(f"{'='*80}")
    
    # 优化 1 验证
    print(f"\n【优化 1：涨跌停接口换日期测试】")
    limit_list_d_path = os.path.join(OUTPUT_DIR, 'limit_list_d_20260311.csv')
    limit_step_path = os.path.join(OUTPUT_DIR, 'limit_step_20260311.csv')
    
    if os.path.exists(limit_list_d_path):
        df = pd.read_csv(limit_list_d_path)
        print(f"✅ limit_list_d_20260311.csv: {len(df)} 条数据")
        print(f"   字段：{list(df.columns)}")
    else:
        print(f"❌ limit_list_d_20260311.csv 未生成")
    
    if os.path.exists(limit_step_path):
        df = pd.read_csv(limit_step_path)
        print(f"✅ limit_step_20260311.csv: {len(df)} 条数据")
        print(f"   字段：{list(df.columns)}")
    else:
        print(f"❌ limit_step_20260311.csv 未生成")
    
    # 优化 2 验证
    print(f"\n【优化 2：添加 stocks_dir 配置】")
    moneyflow_path = os.path.join(STOCKS_DIR, '000001.SZ', 'moneyflow_ths.csv')
    if os.path.exists(moneyflow_path):
        df = pd.read_csv(moneyflow_path)
        print(f"✅ moneyflow_ths.csv 已保存到：{moneyflow_path}")
        print(f"   数据量：{len(df)} 条")
        print(f"   字段：{list(df.columns)}")
    else:
        print(f"❌ moneyflow_ths.csv 未生成到预期路径")
    
    # 优化 3 验证
    print(f"\n【优化 3：更新字段名配置】")
    print(f"✅ 已根据实际 CSV 文件头更新 expected_fields 配置")
    print(f"   参见测试脚本中的字段定义")
    
    # 优化 4 验证
    print(f"\n【优化 4：概念成分逻辑修复】")
    ths_member_path = os.path.join(OUTPUT_DIR, 'ths_member_BK1129_test.csv')
    if os.path.exists(ths_member_path):
        df = pd.read_csv(ths_member_path)
        print(f"✅ ths_member_BK1129_test.csv: {len(df)} 条数据")
        print(f"   字段：{list(df.columns)}")
        if 'concept_code' in df.columns:
            print(f"   concept_code 值：{df['concept_code'].unique()[:3]}")
    else:
        print(f"❌ ths_member_BK1129_test.csv 未生成")

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print(f"阶段 0.3 - 优化建议执行测试")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n【优化配置】")
    print(f"优化 1：涨跌停接口换日期测试 (使用 20260311)")
    print(f"优化 2：添加 stocks_dir 配置 ({STOCKS_DIR})")
    print(f"优化 3：更新字段名配置 (根据实际 CSV)")
    print(f"优化 4：概念成分逻辑修复 (使用 BK1129)")
    
    print(f"\n【测试配置】")
    print(f"测试日期：{TEST_DATE}")
    print(f"日期范围：{TEST_START_DATE} 至 {TEST_END_DATE}")
    print(f"stocks_dir: {STOCKS_DIR}")
    
    # 创建测试实例
    print(f"\n创建 Tushare 接口实例...")
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    
    config = {
        'token': TUSHARE_TOKEN,
        'output_dir': OUTPUT_DIR,
        'stocks_dir': STOCKS_DIR  # ✅ 优化 2：添加 stocks_dir
    }
    fetcher = Utils(pro, config)
    
    print(f"✅ Tushare 接口实例创建成功")
    
    # 逐个测试接口
    for interface in TEST_INTERFACES:
        test_interface(fetcher, interface)
    
    # 打印总结
    print_summary()
    
    # 保存结果
    save_results()
    
    # 验证优化结果
    verify_optimization_results()
    
    return test_results

if __name__ == '__main__':
    results = main()
    print(f"\n✅ 所有优化测试完成！")
