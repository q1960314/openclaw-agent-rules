#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 0.2 - 15 个接口全量测试（限流保护版）
添加请求间隔和递增延迟重试机制
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

# ==================== 测试配置 ====================
TEST_DATE = datetime.now().strftime('%Y%m%d')
TEST_START_DATE = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
TEST_END_DATE = TEST_DATE

# 限流配置
REQUEST_INTERVAL = 1.0  # 请求间隔 1 秒
RETRY_DELAYS = [5, 10, 15]  # 重试延迟递增（秒）
MAX_RETRIES = 3

# 测试的 15 个接口配置（使用正确的方法签名）
TEST_INTERFACES = [
    # ==================== 1-6. 特殊权限接口 ====================
    {
        'name': '开盘啦榜单数据接口测试 (kpl_list)',
        'config_key': 'enable_kpl_list',
        'method': 'fetch_kpl_list',
        'params': {'trade_date': TEST_DATE},  # ✅ 修正：trade_date
        'expected_fields': ['ts_code', 'name', 'trade_date'],
        'output_file': 'kpl_list.csv',
        'required_points': 5000,
        'is_special': True
    },
    {
        'name': '同花顺板块指数接口测试 (ths_daily)',
        'config_key': 'enable_ths_daily',
        'method': 'fetch_ths_daily',
        'params': {'index_code': '881100.THS', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},  # ✅ 修正参数
        'expected_fields': ['ts_code', 'trade_date', 'close'],
        'output_file': 'ths_daily_881100.csv',
        'required_points': 6000,
        'is_special': True
    },
    {
        'name': '最强板块统计接口测试 (limit_cpt_list)',
        'config_key': 'enable_limit_cpt_list',
        'method': 'fetch_limit_cpt_list',
        'params': {'trade_date': TEST_DATE},  # ✅ 修正：trade_date
        'expected_fields': ['trade_date', 'name', 'count'],
        'output_file': 'limit_cpt_list.csv',
        'required_points': 8000,
        'is_special': True
    },
    {
        'name': '连板天梯接口测试 (limit_step)',
        'config_key': 'enable_limit_step',
        'method': 'fetch_limit_step',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['trade_date', 'step_count', 'name'],
        'output_file': 'limit_step.csv',
        'required_points': 8000,
        'is_special': True
    },
    {
        'name': '涨跌停列表接口测试 (limit_list_d)',
        'config_key': 'enable_limit_list_d',
        'method': 'fetch_limit_list_d',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'trade_date', 'limit'],
        'output_file': 'limit_list_d.csv',
        'required_points': 5000,
        'is_special': True
    },
    {
        'name': '涨跌停榜单 THS 接口测试 (limit_list_ths)',
        'config_key': 'enable_limit_list_ths',
        'method': 'fetch_limit_list_ths',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'trade_date', 'limit'],
        'output_file': 'limit_list_ths.csv',
        'required_points': 8000,
        'is_special': True
    },
    # ==================== 7-15. 普通接口 ====================
    {
        'name': '同花顺热榜接口测试 (ths_hot)',
        'config_key': 'enable_ths_hot',
        'method': 'fetch_ths_hot',
        'params': {'date': TEST_DATE},
        'expected_fields': ['trade_date', 'ts_code', 'ts_name'],
        'output_file': 'ths_hot.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '游资每日明细接口测试 (hm_detail)',
        'config_key': 'enable_hm_detail',
        'method': 'fetch_hm_detail',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'org_name', 'ts_code'],
        'output_file': 'hm_detail.csv',
        'required_points': 10000,
        'is_special': False
    },
    {
        'name': '游资名录接口测试 (hm_list)',
        'config_key': 'enable_hm_list',
        'method': 'fetch_hm_list',
        'params': {},
        'expected_fields': ['name', 'desc', 'orgs'],
        'output_file': 'hm_list.csv',
        'required_points': 5000,
        'is_special': False
    },
    {
        'name': '当日集合竞价接口测试 (stk_auction)',
        'config_key': 'enable_stk_auction',
        'method': 'fetch_stk_auction',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'trade_date', 'open_price'],
        'output_file': 'stk_auction.csv',
        'required_points': 0,
        'is_special': False
    },
    {
        'name': '同花顺概念成分接口测试 (ths_member)',
        'config_key': 'enable_ths_member',
        'method': 'fetch_ths_member',
        'params': {'concept_code': 'BK1129'},
        'expected_fields': ['ts_code', 'name', 'concept_code'],
        'output_file': 'ths_member_BK1129.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '同花顺板块指数列表接口测试 (ths_index)',
        'config_key': 'enable_ths_index',
        'method': 'fetch_ths_index',
        'params': {},
        'expected_fields': ['ts_code', 'name', 'exchange'],
        'output_file': 'ths_index.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '个股资金流向 THS 接口测试 (moneyflow_ths)',
        'config_key': 'enable_moneyflow_ths',
        'method': 'fetch_moneyflow_ths',
        'params': {'ts_code': '000001.SZ', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['ts_code', 'trade_date', 'buy_sm_amount'],
        'output_file': 'moneyflow_ths_000001.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '概念板块资金流接口测试 (moneyflow_cnt_ths)',
        'config_key': 'enable_moneyflow_cnt_ths',
        'method': 'fetch_moneyflow_cnt_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'ts_code', 'name'],
        'output_file': 'moneyflow_cnt_ths.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '行业资金流向接口测试 (moneyflow_ind_ths)',
        'config_key': 'enable_moneyflow_ind_ths',
        'method': 'fetch_moneyflow_ind_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'ts_code', 'name'],
        'output_file': 'moneyflow_ind_ths.csv',
        'required_points': 6000,
        'is_special': False
    }
]

# ==================== 测试结果记录 ====================
test_results = []
start_time = datetime.now()

def test_interface(fetcher, interface):
    """测试单个接口（带限流保护）"""
    print(f"\n{'='*80}")
    print(f"开始测试：{interface['name']}")
    print(f"所需积分：{interface['required_points']}")
    print(f"{'='*80}")
    
    result = {
        'name': interface['name'],
        'config_key': interface['config_key'],
        'config_enabled': EXTEND_FETCH_CONFIG.get(interface['config_key'], False),
        'is_special': interface['is_special'],
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
    
    # 1. 请求间延迟（避免限流）
    time.sleep(REQUEST_INTERVAL)
    
    # 2. 调用接口（带重试机制）
    attempt = 0
    max_attempts = 1 + MAX_RETRIES  # 1 次初始 + 3 次重试
    
    while attempt < max_attempts:
        try:
            method = getattr(fetcher, interface['method'])
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
    
    # 按类型统计
    special_interfaces = [r for r in test_results if r['is_special']]
    normal_interfaces = [r for r in test_results if not r['is_special']]
    
    print(f"\n【特殊权限接口（6 个）】")
    print(f"调用成功：{sum(1 for r in special_interfaces if r['call_success'])}/{len(special_interfaces)}")
    
    print(f"\n【普通接口（9 个）】")
    print(f"调用成功：{sum(1 for r in normal_interfaces if r['call_success'])}/{len(normal_interfaces)}")
    
    # 错误类型统计
    print(f"\n【错误类型统计】")
    permission_errors = sum(1 for r in test_results if r['error_type'] == '权限不足')
    ratelimit_errors = sum(1 for r in test_results if r['error_type'] == '限流/网络')
    other_errors = sum(1 for r in test_results if r['error_type'] == '其他')
    empty_data = sum(1 for r in test_results if r['call_success'] and r['data_count'] == 0)
    
    print(f"权限不足：{permission_errors}")
    print(f"限流/网络：{ratelimit_errors}")
    print(f"其他错误：{other_errors}")
    print(f"空数据：{empty_data}")
    
    # 重试统计
    total_retries = sum(r['retry_count'] for r in test_results)
    print(f"\n【重试统计】")
    print(f"总重试次数：{total_retries}")
    print(f"平均重试：{total_retries/total:.2f} 次/接口")
    
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
        
        print(f"{i:2}. {status} {r['name'][:40]:<40} {data_info:>8} {file_info:>10} {retry_info}")

def save_results():
    """保存测试结果"""
    results_df = pd.DataFrame(test_results)
    results_path = os.path.join(OUTPUT_DIR, 'test_15_interfaces_ratelimit_result.csv')
    results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 测试结果已保存：{results_path}")

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print(f"阶段 0.2 - 15 个接口全量测试（限流保护版）")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n【限流配置】")
    print(f"请求间隔：{REQUEST_INTERVAL} 秒")
    print(f"重试延迟：{RETRY_DELAYS} 秒（递增）")
    print(f"最大重试：{MAX_RETRIES} 次")
    
    print(f"\n【测试配置】")
    print(f"测试日期：{TEST_DATE}")
    print(f"日期范围：{TEST_START_DATE} 至 {TEST_END_DATE}")
    print(f"特殊权限接口：6 个")
    print(f"普通接口：9 个")
    
    # 创建测试实例
    print(f"\n创建 Tushare 接口实例...")
    print(f"Token: {TUSHARE_TOKEN[:20]}...{TUSHARE_TOKEN[-10:]}")
    print(f"API URL: {TUSHARE_API_URL}")
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    print(f"✅ Tushare 接口实例创建成功")
    
    # 逐个测试接口
    for interface in TEST_INTERFACES:
        test_interface(fetcher, interface)
    
    # 打印总结
    print_summary()
    
    # 保存结果
    save_results()
    
    return test_results

if __name__ == '__main__':
    results = main()
    print(f"\n✅ 所有测试完成！")
