#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 18 个新 Tushare 接口的数据抓取功能 - 修复版
测试日期范围：2026-03-01 至 2026-03-11
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time

# 添加项目路径
sys.path.insert(0, '/home/admin/.openclaw/agents/master')

# 导入 Tushare
import tushare as ts

# 配置
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
START_DATE = "2026-03-01"
END_DATE = "2026-03-11"
START_DATE_API = "20260301"
END_DATE_API = "20260311"

# 测试的 18 个新接口列表（修复参数）
TEST_INTERFACES = [
    # 基础接口（已验证）
    ("stock_basic", "股票基本信息", {"exchange": "", "list_status": "L", "fields": "ts_code,symbol,name,area,industry,list_date,market"}),
    ("daily", "日线行情", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("daily_basic", "每日指标", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("fina_indicator", "财务指标", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("moneyflow", "资金流向", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    
    # 新增接口（需要验证）
    ("concept_detail", "概念题材", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("top_list", "龙虎榜", {"trade_date": END_DATE_API}),  # 修复：使用 trade_date
    ("top_inst", "龙虎榜机构席位", {"trade_date": END_DATE_API}),  # 修复：使用 trade_date
    ("balancesheet", "资产负债表", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("cashflow", "现金流量表", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("income", "利润表", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("hk_hold", "北向资金持股", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("cyq_chips", "筹码分布", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("stk_limit", "每日涨跌停", {"start_date": START_DATE_API, "end_date": END_DATE_API}),
    
    # 同花顺系列接口
    ("ths_daily", "同花顺日线", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("ths_index", "同花顺指数", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
    ("limit_list_ths", "同花顺涨跌停列表", {"trade_date": END_DATE_API}),
    ("hm_detail", "聪明钱明细", {"ts_code": "000001.SZ", "start_date": START_DATE_API, "end_date": END_DATE_API}),
]

def request_retry(api_func, max_retry=3, timeout=60, **kwargs):
    """带重试的请求"""
    for i in range(max_retry):
        try:
            df = api_func(timeout=timeout, **kwargs)
            return df
        except Exception as e:
            if i < max_retry - 1:
                print(f"  重试 {i+1}/{max_retry}: {str(e)}")
                time.sleep(2)
            else:
                raise

def test_interface(pro, interface_name, description, params):
    """测试单个接口"""
    print(f"\n{'='*80}")
    print(f"测试接口：{interface_name} - {description}")
    print(f"参数：{params}")
    print(f"{'='*80}")
    
    try:
        # 获取对应的 API 方法
        if hasattr(pro, interface_name):
            api_func = getattr(pro, interface_name)
            
            # 调用 API
            df = request_retry(api_func, timeout=60, **params)
            
            if df is not None and not df.empty:
                print(f"✅ 成功！返回 {len(df)} 条记录")
                print(f"列名：{list(df.columns)[:10]}{'...' if len(df.columns) > 10 else ''}")
                print(f"示例数据:\n{df.head(2)}")
                return True, len(df)
            else:
                print(f"⚠️  返回空数据（日期范围内无数据或接口正常）")
                return True, 0
        else:
            print(f"❌ 接口不存在：{interface_name}")
            return False, 0
            
    except Exception as e:
        print(f"❌ 失败：{str(e)}")
        return False, 0

def main():
    print("="*80)
    print("开始测试 18 个 Tushare 新接口（修复版）")
    print(f"测试日期范围：{START_DATE} 至 {END_DATE}")
    print(f"API 日期格式：{START_DATE_API} 至 {END_DATE_API}")
    print("="*80)
    
    # 初始化 Tushare API
    print("\n初始化 Tushare API...")
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__http_url = TUSHARE_API_URL
    pro._DataApi__token = TUSHARE_TOKEN
    print("✅ Tushare API 初始化完成")
    
    # 测试结果统计
    results = []
    success_count = 0
    total_records = 0
    failed_interfaces = []
    
    # 逐个测试接口
    for interface_name, description, params in TEST_INTERFACES:
        success, records = test_interface(pro, interface_name, description, params)
        results.append({
            'interface': interface_name,
            'description': description,
            'success': success,
            'records': records
        })
        
        if success:
            success_count += 1
            total_records += records
        else:
            failed_interfaces.append(interface_name)
        
        # 间隔避免请求过快
        time.sleep(1)
    
    # 输出汇总报告
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    print(f"总接口数：{len(TEST_INTERFACES)}")
    print(f"成功数：{success_count}")
    print(f"失败数：{len(TEST_INTERFACES) - success_count}")
    print(f"成功率：{success_count/len(TEST_INTERFACES)*100:.1f}%")
    print(f"总记录数：{total_records}")
    print("\n详细结果：")
    print(f"{'接口名':<20} {'描述':<20} {'状态':<8} {'记录数':>10}")
    print("-"*80)
    
    for r in results:
        status = "✅ 成功" if r['success'] else "❌ 失败"
        print(f"{r['interface']:<20} {r['description']:<20} {status:<8} {r['records']:>10}")
    
    print("="*80)
    
    # 保存测试结果
    results_df = pd.DataFrame(results)
    results_file = '/home/admin/.openclaw/agents/master/test_18_interfaces_result.csv'
    results_df.to_csv(results_file, index=False, encoding='utf-8-sig')
    print(f"\n测试结果已保存到：{results_file}")
    
    # 保存详细日志
    log_file = '/home/admin/.openclaw/agents/master/test_18_interfaces_log.txt'
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("测试结果详细日志\n")
        f.write("="*80 + "\n")
        f.write(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试日期范围：{START_DATE} 至 {END_DATE}\n")
        f.write(f"总接口数：{len(TEST_INTERFACES)}\n")
        f.write(f"成功数：{success_count}\n")
        f.write(f"失败数：{len(TEST_INTERFACES) - success_count}\n")
        f.write(f"成功率：{success_count/len(TEST_INTERFACES)*100:.1f}%\n")
        f.write(f"总记录数：{total_records}\n\n")
        
        if failed_interfaces:
            f.write("失败接口列表：\n")
            for iface in failed_interfaces:
                f.write(f"  - {iface}\n")
    
    print(f"测试日志已保存到：{log_file}")
    
    return success_count, len(TEST_INTERFACES), failed_interfaces

if __name__ == "__main__":
    try:
        success, total, failed = main()
        print(f"\n✅ 测试完成：{success}/{total} 接口成功")
        if failed:
            print(f"⚠️  失败接口：{', '.join(failed)}")
        sys.exit(0 if success == total else 1)
    except Exception as e:
        print(f"\n❌ 测试异常：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
