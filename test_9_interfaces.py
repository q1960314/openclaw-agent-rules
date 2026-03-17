#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 0.2 - 9 个接口测试脚本
测试剩余 9 个接口（已关闭 6 个特殊权限接口）
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from fetch_data_optimized import Utils, EXTEND_FETCH_CONFIG, TUSHARE_TOKEN, OUTPUT_DIR, TUSHARE_API_URL
import tushare as ts

# ==================== 测试配置 ====================
TEST_DATE = datetime.now().strftime('%Y%m%d')  # 今天日期
TEST_START_DATE = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')  # 5 天前
TEST_END_DATE = TEST_DATE

# 测试的 9 个接口配置
TEST_INTERFACES = [
    {
        'name': '同花顺热榜接口测试 (ths_hot)',
        'config_key': 'enable_ths_hot',
        'method': 'fetch_ths_hot',
        'params': {'date': TEST_DATE},
        'expected_fields': ['ts_code', 'ts_name', 'pct_change', 'trade_date'],  # 实际字段
        'output_file': 'ths_hot.csv'
    },
    {
        'name': '游资每日明细接口测试 (hm_detail)',
        'config_key': 'enable_hm_detail',
        'method': 'fetch_hm_detail',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'ts_code', 'ts_name'],  # 实际字段
        'output_file': 'hm_detail.csv'
    },
    {
        'name': '游资名录接口测试 (hm_list)',
        'config_key': 'enable_hm_list',
        'method': 'fetch_hm_list',
        'params': {},
        'expected_fields': ['name'],  # 实际字段
        'output_file': 'hm_list.csv'
    },
    {
        'name': '当日集合竞价接口测试 (stk_auction)',
        'config_key': 'enable_stk_auction',
        'method': 'fetch_stk_auction',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'trade_date'],  # 实际字段
        'output_file': 'stk_auction.csv'
    },
    {
        'name': '同花顺概念成分接口测试 (ths_member)',
        'config_key': 'enable_ths_member',
        'method': 'fetch_ths_member',
        'params': {'concept_code': 'BK1129'},  # 人工智能概念
        'expected_fields': ['ts_code', 'con_name'],  # 实际字段
        'output_file': 'ths_member_BK1129.csv'
    },
    {
        'name': '同花顺板块指数列表接口测试 (ths_index)',
        'config_key': 'enable_ths_index',
        'method': 'fetch_ths_index',
        'params': {},
        'expected_fields': ['ts_code', 'name'],  # 实际字段
        'output_file': 'ths_index.csv'
    },
    {
        'name': '个股资金流向 THS 接口测试 (moneyflow_ths)',
        'config_key': 'enable_moneyflow_ths',
        'method': 'fetch_moneyflow_ths',
        'params': {'ts_code': '000001.SZ', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['ts_code', 'trade_date'],  # 实际字段
        'output_file': 'moneyflow_ths_000001.csv'
    },
    {
        'name': '概念板块资金流接口测试 (moneyflow_cnt_ths)',
        'config_key': 'enable_moneyflow_cnt_ths',
        'method': 'fetch_moneyflow_cnt_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'name'],  # 实际字段
        'output_file': 'moneyflow_cnt_ths.csv'
    },
    {
        'name': '行业资金流向接口测试 (moneyflow_ind_ths)',
        'config_key': 'enable_moneyflow_ind_ths',
        'method': 'fetch_moneyflow_ind_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'industry'],  # 实际字段
        'output_file': 'moneyflow_ind_ths.csv'
    }
]

# ==================== 测试结果记录 ====================
test_results = []

def test_interface(fetcher, interface):
    """测试单个接口"""
    print(f"\n{'='*80}")
    print(f"开始测试：{interface['name']}")
    print(f"{'='*80}")
    
    result = {
        'name': interface['name'],
        'config_key': interface['config_key'],
        'config_enabled': EXTEND_FETCH_CONFIG.get(interface['config_key'], False),
        'call_success': False,
        'data_format_valid': False,
        'save_success': False,
        'file_complete': False,
        'retry_mechanism_ok': False,
        'error_msg': '',
        'data_count': 0,
        'file_size': 0
    }
    
    # 1. 检查配置开关
    if not result['config_enabled']:
        result['error_msg'] = f"配置开关 {interface['config_key']} 为 False，跳过测试"
        print(f"⚠️  配置开关关闭：{interface['config_key']}")
        test_results.append(result)
        return result
    
    print(f"✅ 配置开关已开启：{interface['config_key']}")
    
    # 2. 调用接口
    try:
        method = getattr(fetcher, interface['method'])
        df = method(**interface['params'])
        
        if df is None or df.empty:
            result['call_success'] = True  # 调用成功但无数据
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
            else:
                result['data_format_valid'] = True
                print(f"✅ 数据格式验证通过：包含所有必需字段")
            
            # 4. 验证文件保存
            save_path = os.path.join(OUTPUT_DIR, interface['output_file'])
            if os.path.exists(save_path):
                result['save_success'] = True
                file_size = os.path.getsize(save_path)
                result['file_size'] = file_size
                print(f"✅ 文件保存成功：{save_path} ({file_size/1024:.2f} KB)")
                
                # 5. 验证文件内容完整性
                if file_size > 0 and result['data_count'] > 0:
                    result['file_complete'] = True
                    print(f"✅ 文件内容完整：{result['data_count']} 条数据")
                else:
                    result['file_complete'] = False
                    result['error_msg'] = '文件大小为 0 或数据条数为 0'
                    print(f"❌ 文件内容不完整")
            else:
                result['save_success'] = False
                result['error_msg'] = f'文件未保存：{save_path}'
                print(f"❌ 文件保存失败：{save_path}")
        
    except Exception as e:
        result['call_success'] = False
        result['error_msg'] = str(e)
        print(f"❌ 接口调用失败：{e}")
        
        # 6. 验证重试机制
        print(f"🔄 测试重试机制...")
        retry_count = 0
        max_retries = 3
        for i in range(max_retries):
            try:
                method = getattr(fetcher, interface['method'])
                df = method(**interface['params'])
                if df is not None and not df.empty:
                    result['retry_mechanism_ok'] = True
                    print(f"✅ 重试机制有效：第 {i+1} 次重试成功")
                    break
            except:
                retry_count += 1
                print(f"⏳ 第 {i+1} 次重试失败")
        
        if retry_count == max_retries:
            result['retry_mechanism_ok'] = False
            print(f"❌ 重试机制失败：{max_retries} 次重试后仍失败")
    
    test_results.append(result)
    return result

def print_summary():
    """打印测试总结"""
    print(f"\n{'='*80}")
    print(f"测试总结")
    print(f"{'='*80}")
    
    total = len(test_results)
    success = sum(1 for r in test_results if r['call_success'] and r['data_format_valid'] and r['save_success'])
    
    print(f"\n总测试接口数：{total}")
    print(f"成功：{success}")
    print(f"失败：{total - success}")
    print(f"成功率：{success/total*100:.1f}%")
    
    print(f"\n详细结果：")
    print(f"{'-'*80}")
    for r in test_results:
        status = "✅" if (r['call_success'] and r['data_format_valid'] and r['save_success']) else "❌"
        print(f"{status} {r['name']}")
        print(f"   配置开关：{'开启' if r['config_enabled'] else '关闭'}")
        print(f"   调用成功：{'是' if r['call_success'] else '否'}")
        print(f"   数据格式：{'正确' if r['data_format_valid'] else '错误'}")
        print(f"   保存成功：{'是' if r['save_success'] else '否'}")
        print(f"   文件完整：{'是' if r['file_complete'] else '否'}")
        print(f"   数据条数：{r['data_count']}")
        print(f"   文件大小：{r['file_size']/1024:.2f} KB" if r['file_size'] > 0 else "   文件大小：N/A")
        if r['error_msg']:
            print(f"   错误信息：{r['error_msg']}")
        print()
    
    # 检查 6 个特殊权限接口是否已关闭
    print(f"\n{'='*80}")
    print(f"6 个特殊权限接口状态检查")
    print(f"{'='*80}")
    
    closed_interfaces = [
        'enable_kpl_list',
        'enable_ths_daily',
        'enable_limit_cpt_list',
        'enable_limit_step',
        'enable_limit_list_d',
        'enable_limit_list_ths'
    ]
    
    all_closed = True
    for key in closed_interfaces:
        status = EXTEND_FETCH_CONFIG.get(key, True)
        status_str = "❌ 已关闭" if not status else "⚠️  未关闭"
        if status:
            all_closed = False
        print(f"{status_str} {key}")
    
    print(f"\n{'='*80}")
    if all_closed:
        print(f"✅ 所有特殊权限接口已正确关闭")
    else:
        print(f"❌ 部分特殊权限接口未关闭，请检查配置")
    print(f"{'='*80}")

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print(f"阶段 0.2 - 9 个接口测试")
    print(f"测试日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    # 检查 6 个特殊权限接口是否已关闭
    print(f"\n检查配置...")
    closed_count = sum(1 for key in ['enable_kpl_list', 'enable_ths_daily', 'enable_limit_cpt_list', 
                                      'enable_limit_step', 'enable_limit_list_d', 'enable_limit_list_ths']
                       if not EXTEND_FETCH_CONFIG.get(key, True))
    print(f"✅ 已关闭的特殊权限接口数：{closed_count}/6")
    
    # 创建测试实例
    print(f"\n创建 Tushare 接口实例...")
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN  # 必须添加，否则 token 验证失败
    pro._DataApi__http_url = TUSHARE_API_URL  # 使用自定义 API 地址
    config = {
        'token': TUSHARE_TOKEN,
        'output_dir': OUTPUT_DIR,
        'stocks_dir': os.path.join(OUTPUT_DIR, 'all_stocks')  # 添加 stocks_dir 配置
    }
    fetcher = Utils(pro, config)
    
    # 逐个测试接口
    for interface in TEST_INTERFACES:
        test_interface(fetcher, interface)
    
    # 打印总结
    print_summary()
    
    # 返回测试结果
    return test_results

if __name__ == '__main__':
    results = main()
    
    # 保存测试结果
    results_df = pd.DataFrame(results)
    results_path = os.path.join(OUTPUT_DIR, 'test_9_interfaces_result.csv')
    results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 测试结果已保存：{results_path}")
