#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【阶段 2 - 40+ 接口全量验证脚本】
验证所有 Tushare 接口的可用性和数据质量
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

def test_interface(func_name, params, expected_fields=None, min_records=0):
    """通用接口测试函数"""
    start_time = time.time()
    
    try:
        func = getattr(pro, func_name)
        df = func(**params)
        
        response_time = time.time() - start_time
        
        if df is None or df.empty:
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
    print("【阶段 2 - 40+ 接口全量验证】")
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
                   expected_fields=['ts_code', 'trade_date', 'turnover_ratio', 'pe', 'pb'], min_records=1)
    
    test_interface('adj_factor', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'adj_factor'], min_records=1)
    
    # ============================================
    # 2. 财务数据接口
    # ============================================
    print("\n【2. 财务数据接口】")
    print("-"*60)
    
    test_interface('fina_indicator', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'end_date', 'basic_eps_yoy', 'profit_to_sh'], min_records=1)
    
    test_interface('income', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'end_date', 'total_revenue', 'op_profit'], min_records=1)
    
    test_interface('balancesheet', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'end_date', 'total_assets', 'total_hldr_eqy'], min_records=1)
    
    test_interface('cashflow', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'end_date', 'oper_cf', 'invest_cf'], min_records=1)
    
    # ============================================
    # 3. 资金流向接口
    # ============================================
    print("\n【3. 资金流向接口】")
    print("-"*60)
    
    test_interface('moneyflow', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'buy_sm_amount', 'sell_sm_amount'], min_records=1)
    
    test_interface('hk_hold', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'hold_ratio'], min_records=1)
    
    test_interface('stk_holdertrade', {'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'change_type', 'change_vol'], min_records=1)
    
    # ============================================
    # 4. 龙虎榜接口
    # ============================================
    print("\n【4. 龙虎榜接口】")
    print("-"*60)
    
    test_interface('top_list', {'trade_date': single_date},
                   expected_fields=['ts_code', 'trade_date', 'close', 'buy_amount', 'sell_amount'], min_records=0)
    
    test_interface('top_inst', {'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'buy_amount', 'sell_amount'], min_records=0)
    
    # ============================================
    # 5. 情绪打板接口
    # ============================================
    print("\n【5. 情绪打板接口】")
    print("-"*60)
    
    test_interface('stk_limit', {'trade_date': single_date},
                   expected_fields=['ts_code', 'trade_date', 'limit'], min_records=0)
    
    # cyq_chips 和 cyq_perf 需要特殊权限，单独测试
    test_interface('cyq_chips', {'ts_code': '000001.SZ', 'trade_date': single_date},
                   expected_fields=['ts_code', 'trade_date', 'chip_peak'], min_records=0)
    
    test_interface('cyq_perf', {'ts_code': '000001.SZ', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'winner_ratio'], min_records=0)
    
    # ============================================
    # 6. 板块概念接口
    # ============================================
    print("\n【6. 板块概念接口】")
    print("-"*60)
    
    test_interface('concept_detail', {'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'concept_id', 'concept_name'], min_records=1)
    
    test_interface('index_classify', {'src': 'SW', 'level': 'L1'},
                   expected_fields=['index_code', 'index_name', 'src'], min_records=1)
    
    test_interface('index_member', {'index_code': '000001.SH', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['index_code', 'ts_code', 'trade_date'], min_records=0)
    
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
                   expected_fields=['ts_code', 'trade_date', 'suspend_timing'], min_records=0)
    
    test_interface('block_trade', {'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['ts_code', 'trade_date', 'price', 'vol'], min_records=0)
    
    test_interface('concept_list', {'fields': 'id,name,src'},
                   expected_fields=['id', 'name', 'src'], min_records=1)
    
    test_interface('index_weight', {'index_code': '000001.SH', 'start_date': test_start_date, 'end_date': test_end_date},
                   expected_fields=['index_code', 'ts_code', 'trade_date', 'weight'], min_records=0)
    
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
    print(f"  成功率：{stats['success_count']/stats['total_interfaces']*100:.1f}%")
    
    if validation_results['failed']:
        print(f"\n❌ 失败接口清单：")
        for r in validation_results['failed']:
            print(f"  - {r['interface']}: {r['error_msg'][:100]}")
    
    if validation_results['partial']:
        print(f"\n⚠️  部分成功接口（数据量少或缺字段）：")
        for r in validation_results['partial']:
            print(f"  - {r['interface']}: {r['record_count']}条记录 - {r['error_msg']}")
    
    if validation_results['success']:
        print(f"\n✅ 成功接口详情：")
        for r in validation_results['success']:
            print(f"  - {r['interface']}: {r['record_count']}条记录, 响应时间：{r['response_time']}")
    
    # ============================================
    # 保存验证报告
    # ============================================
    report_file = os.path.join(BASE_DIR, 'interface_validation_report.csv')
    
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
