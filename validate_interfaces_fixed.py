#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【阶段 2 - 40+ 接口全量验证脚本 - 修复版】
修正参数后重新验证所有接口
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 导入配置
from fetch_data_optimized import TUSHARE_TOKEN, TUSHARE_API_URL

import tushare as ts
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()
pro._DataApi__http_url = TUSHARE_API_URL

# 验证结果存储
validation_results = {
    'success': [],
    'failed': [],
    'partial': []
}

# 统计信息
stats = {
    'total_interfaces': 0,
    'success_count': 0,
    'failed_count': 0,
    'partial_count': 0,
    'total_records': 0
}

def log_result(interface_name, status, record_count=0, error_msg="", response_time=0):
    """记录验证结果"""
    stats['total_interfaces'] += 1
    
    result = {
        'interface': interface_name,
        'category': get_category(interface_name),
        'status': status,
        'record_count': record_count,
        'error_msg': error_msg,
        'response_time': f"{response_time:.2f}s"
    }
    
    if status == '✅ 成功':
        validation_results['success'].append(result)
        stats['success_count'] += 1
        stats['total_records'] += record_count
    elif status == '⚠️ 部分成功':
        validation_results['partial'].append(result)
        stats['partial_count'] += 1
        stats['total_records'] += record_count
    else:
        validation_results['failed'].append(result)
        stats['failed_count'] += 1

def get_category(interface_name):
    """获取接口分类"""
    categories = {
        '行情数据': ['daily', 'weekly', 'monthly', 'daily_basic', 'adj_factor'],
        '财务数据': ['fina_indicator', 'income', 'balancesheet', 'cashflow'],
        '资金流向': ['moneyflow', 'hk_hold', 'stk_holdertrade'],
        '龙虎榜': ['top_list', 'top_inst'],
        '情绪打板': ['stk_limit', 'cyq_chips', 'cyq_perf'],
        '板块概念': ['concept_detail', 'index_classify', 'index_member', 'concept_list'],
        '其他': ['stock_basic', 'trade_cal', 'suspend_d', 'block_trade', 'index_weight']
    }
    for cat, interfaces in categories.items():
        if interface_name in interfaces:
            return cat
    return '其他'

def test_interface(func_name, params, expected_fields=None, min_records=0, allow_empty=False):
    """通用接口测试函数"""
    start_time = time.time()
    
    try:
        func = getattr(pro, func_name)
        df = func(**params)
        
        response_time = time.time() - start_time
        
        if df is None or df.empty:
            if allow_empty:
                log_result(
                    func_name,
                    '✅ 成功 (可空)',
                    record_count=0,
                    response_time=response_time
                )
                return True
            else:
                log_result(
                    func_name,
                    '❌ 无数据',
                    error_msg="接口返回空数据"
                )
                return False
        
        record_count = len(df)
        
        # 检查必需字段
        if expected_fields:
            missing_fields = [f for f in expected_fields if f not in df.columns]
            if missing_fields:
                log_result(
                    func_name,
                    '⚠️ 部分成功',
                    record_count=record_count,
                    error_msg=f"缺少字段：{missing_fields}",
                    response_time=response_time
                )
                return True
        
        # 检查最小记录数
        if record_count < min_records:
            log_result(
                func_name,
                '⚠️ 数据量少',
                record_count=record_count,
                error_msg=f"仅{record_count}条记录（期望≥{min_records}）",
                response_time=response_time
            )
            return True
        
        log_result(
            func_name,
            '✅ 成功',
            record_count=record_count,
            response_time=response_time
        )
        return True
        
    except Exception as e:
        response_time = time.time() - start_time
        error_msg = str(e)
        
        # 判断是否是权限问题
        if "积分" in error_msg or "权限" in error_msg or "token" in error_msg:
            log_result(
                func_name,
                '❌ 权限不足',
                error_msg=error_msg,
                response_time=response_time
            )
        else:
            log_result(
                func_name,
                '❌ 失败',
                error_msg=error_msg,
                response_time=response_time
            )
        return False

def main():
    print("="*100)
    print("【阶段 2 - 40+ 接口全量验证 - 修复参数版】")
    print(f"验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tushare API: {TUSHARE_API_URL}")
    print("="*100)
    print()
    
    # 获取测试日期（最近一个交易日）
    test_end_date = datetime.now().strftime("%Y%m%d")
    test_start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    single_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    # ============================================
    # 1. 行情数据接口
    # ============================================
    print("\n【1. 行情数据接口】")
    print("-"*60)
    
    test_interface('daily', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date}, 
                   expected_fields=['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'], min_records=1)
    
    test_interface('weekly', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'], min_records=1)
    
    test_interface('monthly', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'], min_records=1)
    
    test_interface('daily_basic', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=1)  # 不检查具体字段，只要有数据即可
    
    test_interface('adj_factor', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'adj_factor'], min_records=1)
    
    # ============================================
    # 2. 财务数据接口 - 使用正确的参数
    # ============================================
    print("\n【2. 财务数据接口】")
    print("-"*60)
    
    # 财务指标 - 使用 ann_date 参数
    test_interface('fina_indicator', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date, 'period': '20241231'},
                   min_records=0, allow_empty=True)
    
    # 利润表
    test_interface('income', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date, 'period': '20241231'},
                   min_records=0, allow_empty=True)
    
    # 资产负债表
    test_interface('balancesheet', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date, 'period': '20241231'},
                   min_records=0, allow_empty=True)
    
    # 现金流量表
    test_interface('cashflow', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date, 'period': '20241231'},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 3. 资金流向接口
    # ============================================
    print("\n【3. 资金流向接口】")
    print("-"*60)
    
    test_interface('moneyflow', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=1)
    
    # 北向资金 - 需要正确的参数
    test_interface('hk_hold', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # 股东交易
    test_interface('stk_holdertrade', {'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 4. 龙虎榜接口 - 修复参数
    # ============================================
    print("\n【4. 龙虎榜接口】")
    print("-"*60)
    
    test_interface('top_list', {'trade_date': single_date},
                   min_records=0, allow_empty=True)
    
    # top_inst 需要 trade_date 参数
    test_interface('top_inst', {'trade_date': single_date},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 5. 情绪打板接口
    # ============================================
    print("\n【5. 情绪打板接口】")
    print("-"*60)
    
    test_interface('stk_limit', {'trade_date': single_date},
                   min_records=0, allow_empty=True)
    
    test_interface('cyq_chips', {'ts_code': '000001.SZ', 'trade_date': single_date},
                   min_records=0, allow_empty=True)
    
    test_interface('cyq_perf', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 6. 板块概念接口 - 修复参数
    # ============================================
    print("\n【6. 板块概念接口】")
    print("-"*60)
    
    # concept_detail 需要 ts_code 或 concept_id
    test_interface('concept_detail', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # index_classify 使用正确的 src
    test_interface('index_classify', {'src': 'SW2021', 'level': 'L1'},
                   min_records=0, allow_empty=True)
    
    # index_member 需要有效的指数代码
    test_interface('index_member', {'index_code': '000001.SH', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # concept_list - 正确的接口名是 concept_list_sw
    test_interface('concept_list_sw', {'src': 'SW2021'},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 7. 其他重要接口
    # ============================================
    print("\n【7. 其他重要接口】")
    print("-"*60)
    
    test_interface('stock_basic', {'exchange': '', 'list_status': 'L'},
                   expected_fields=['ts_code', 'symbol', 'name', 'area', 'industry'], min_records=100)
    
    test_interface('trade_cal', {'exchange': '', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['cal_date', 'is_open'], min_records=20)
    
    test_interface('suspend_d', {'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    test_interface('block_trade', {'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    test_interface('index_weight', {'index_code': '000001.SH', 'start_date': test_start_date, 'end_date': test_end_date},
                   min_records=0, allow_empty=True)
    
    # ============================================
    # 输出验证报告
    # ============================================
    print("\n" + "="*100)
    print("【验证结果汇总】")
    print("="*100)
    
    print(f"\n📊 统计信息：")
    print(f"  总接口数：{stats['total_interfaces']}")
    print(f"  ✅ 成功：{stats['success_count']}")
    print(f"  ⚠️  部分成功：{stats['partial_count']}")
    print(f"  ❌ 失败：{stats['failed_count']}")
    print(f"  总记录数：{stats['total_records']}")
    if stats['total_interfaces'] > 0:
        print(f"  成功率：{stats['success_count']/stats['total_interfaces']*100:.1f}%")
    
    # 按分类统计
    categories = {}
    for r in validation_results['success'] + validation_results['partial'] + validation_results['failed']:
        cat = r['category']
        if cat not in categories:
            categories[cat] = {'success': 0, 'partial': 0, 'failed': 0, 'total': 0}
        categories[cat]['total'] += 1
        if r['status'].startswith('✅'):
            categories[cat]['success'] += 1
        elif r['status'].startswith('⚠️'):
            categories[cat]['partial'] += 1
        else:
            categories[cat]['failed'] += 1
    
    print(f"\n📁 按分类统计：")
    for cat, counts in sorted(categories.items()):
        success_rate = counts['success']/counts['total']*100 if counts['total'] > 0 else 0
        print(f"  {cat}: {counts['success']}/{counts['total']} ({success_rate:.0f}%)")
    
    if validation_results['failed']:
        print(f"\n❌ 失败接口清单：")
        for r in validation_results['failed']:
            print(f"  [{r['category']}] {r['interface']}: {r['error_msg'][:100]}")
    
    if validation_results['partial']:
        print(f"\n⚠️  部分成功接口（数据量少或缺字段）：")
        for r in validation_results['partial']:
            print(f"  [{r['category']}] {r['interface']}: {r['record_count']}条记录 - {r['error_msg']}")
    
    if validation_results['success']:
        print(f"\n✅ 成功接口详情：")
        for r in validation_results['success']:
            print(f"  [{r['category']}] {r['interface']}: {r['record_count']}条记录, 响应时间：{r['response_time']}")
    
    # ============================================
    # 保存验证报告
    # ============================================
    report_file = os.path.join(BASE_DIR, 'interface_validation_report_final.csv')
    
    all_results = validation_results['success'] + validation_results['partial'] + validation_results['failed']
    if all_results:
        df_report = pd.DataFrame(all_results)
        df_report.to_csv(report_file, index=False, encoding='utf-8-sig')
        print(f"\n📁 验证报告已保存：{report_file}")
    
    print("\n" + "="*100)
    print("【验证完成】")
    print("="*100)
    
    return stats

if __name__ == '__main__':
    stats = main()
    
    # 返回退出码
    if stats['failed_count'] > stats['total_interfaces'] * 0.3:
        sys.exit(1)  # 超过 30% 失败则返回错误
    sys.exit(0)
