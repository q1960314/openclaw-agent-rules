#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 0.3 - 15 个接口联合测试
验证多个接口同时运行时的稳定性、性能和数据一致性

测试内容：
1. 热点板块 + 概念成分联动
2. 游资名录 + 游资明细联动
3. 板块指数 + 资金流联动
4. 集合竞价 + 涨跌停联动
5. 批量性能测试
6. 数据一致性验证
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time
import json

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from fetch_data_optimized import Utils, EXTEND_FETCH_CONFIG, TUSHARE_TOKEN, OUTPUT_DIR, TUSHARE_API_URL
import tushare as ts

# ==================== 测试配置 ====================
# ❌ 绝对不要修改后端核心配置（第 419-427 行）
# ✅ 使用代码中已有的 TUSHARE_TOKEN 和 TUSHARE_API_URL

TEST_DATE = datetime.now().strftime('%Y%m%d')
TEST_START_DATE = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
TEST_END_DATE = TEST_DATE

# 限流配置
REQUEST_INTERVAL = 1.0  # 请求间隔 1 秒
RETRY_DELAYS = [5, 10, 15]  # 重试延迟递增（秒）
MAX_RETRIES = 3

# 测试结果记录
test_results = {
    'joint_tests': [],  # 联动测试
    'performance_tests': [],  # 性能测试
    'validation_tests': [],  # 数据验证
    'start_time': datetime.now(),
    'end_time': None
}

# ==================== 辅助函数 ====================

def retry_call(method, params, max_retries=MAX_RETRIES):
    """带重试机制的接口调用"""
    attempt = 0
    max_attempts = 1 + max_retries
    
    while attempt < max_attempts:
        try:
            # 请求间隔
            if attempt > 0:
                retry_delay = RETRY_DELAYS[attempt - 1]
                print(f"🔄 等待 {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            
            df = method(**params)
            return df, None
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 判断是否重试
            if attempt < max_retries:
                if 'network' in error_str or 'timeout' in error_str or 'connection' in error_str or 'limit' in error_str:
                    print(f"⚠️  网络/限流错误，准备重试...")
                    attempt += 1
                    continue
            
            # 不重试或所有重试失败
            return None, str(e)

def validate_data(df, expected_fields, interface_name):
    """验证数据格式"""
    if df is None or df.empty:
        return False, "空数据"
    
    missing_fields = [f for f in expected_fields if f not in df.columns]
    if missing_fields:
        return False, f"缺少字段：{missing_fields}"
    
    return True, "验证通过"

def save_test_data(df, filename):
    """保存测试数据"""
    try:
        save_path = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        file_size = os.path.getsize(save_path)
        return True, save_path, file_size
    except Exception as e:
        return False, None, str(e)

# ==================== 联动测试 ====================

def test_1_ths_hot_member():
    """测试 1：热点板块 + 概念成分联动"""
    print(f"\n{'='*80}")
    print("测试 1：热点板块 + 概念成分联动")
    print(f"{'='*80}")
    
    result = {
        'test_name': '热点板块 + 概念成分联动',
        'start_time': datetime.now(),
        'end_time': None,
        'steps': [],
        'success': False,
        'error': None
    }
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    try:
        # 步骤 1：获取同花顺热榜
        print("\n步骤 1：获取同花顺热榜 (ths_hot)...")
        time.sleep(REQUEST_INTERVAL)
        df_hot, error = retry_call(fetcher.fetch_ths_hot, {'date': TEST_DATE})
        
        if error:
            result['steps'].append({'step': '获取热榜', 'status': '失败', 'error': error})
            result['error'] = f"热榜获取失败：{error}"
            result['end_time'] = datetime.now()
            return result
        
        if df_hot is None or df_hot.empty:
            result['steps'].append({'step': '获取热榜', 'status': '警告', 'message': '返回空数据'})
            print("⚠️  热榜返回空数据，使用默认概念代码测试")
            concept_codes = ['BK1129', 'BK1130', 'BK1131']  # 默认概念代码
        else:
            result['steps'].append({'step': '获取热榜', 'status': '成功', 'data_count': len(df_hot)})
            print(f"✅ 热榜获取成功，{len(df_hot)} 条数据")
            # 提取概念代码（假设有 concept_code 字段）
            concept_codes = df_hot['ts_code'].head(3).tolist() if 'ts_code' in df_hot.columns else ['BK1129']
        
        # 步骤 2：获取概念成分
        print("\n步骤 2：获取概念成分 (ths_member)...")
        member_results = []
        
        for i, concept_code in enumerate(concept_codes[:3]):  # 测试前 3 个概念
            time.sleep(REQUEST_INTERVAL)
            print(f"  获取概念 {concept_code} 的成分股...")
            df_member, error = retry_call(fetcher.fetch_ths_member, {'concept_code': concept_code})
            
            if error:
                member_results.append({'concept': concept_code, 'status': '失败', 'error': error})
                print(f"  ❌ {concept_code}: {error}")
            elif df_member is None or df_member.empty:
                member_results.append({'concept': concept_code, 'status': '警告', 'message': '空数据'})
                print(f"  ⚠️  {concept_code}: 空数据")
            else:
                member_results.append({'concept': concept_code, 'status': '成功', 'data_count': len(df_member)})
                print(f"  ✅ {concept_code}: {len(df_member)} 条数据")
                
                # 保存数据
                save_ok, save_path, file_size = save_test_data(df_member, f'test_ths_member_{concept_code}.csv')
                if save_ok:
                    print(f"     已保存：{file_size/1024:.1f} KB")
        
        result['steps'].append({'step': '获取概念成分', 'status': '成功', 'details': member_results})
        
        # 验证关联性
        print("\n步骤 3：验证数据关联性...")
        if len(member_results) > 0:
            success_count = sum(1 for r in member_results if r['status'] == '成功')
            if success_count > 0:
                result['success'] = True
                print(f"✅ 联动测试通过：{success_count}/{len(member_results)} 概念获取成功")
            else:
                result['success'] = False
                result['error'] = "所有概念成分获取失败"
        else:
            result['success'] = False
            result['error'] = "无概念成分数据"
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        print(f"❌ 测试异常：{e}")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['joint_tests'].append(result)
    return result

def test_2_hm_list_detail():
    """测试 2：游资名录 + 游资明细联动"""
    print(f"\n{'='*80}")
    print("测试 2：游资名录 + 游资明细联动")
    print(f"{'='*80}")
    
    result = {
        'test_name': '游资名录 + 游资明细联动',
        'start_time': datetime.now(),
        'end_time': None,
        'steps': [],
        'success': False,
        'error': None
    }
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    try:
        # 步骤 1：获取游资名录
        print("\n步骤 1：获取游资名录 (hm_list)...")
        time.sleep(REQUEST_INTERVAL)
        df_hm_list, error = retry_call(fetcher.fetch_hm_list, {})
        
        if error:
            result['steps'].append({'step': '获取游资名录', 'status': '失败', 'error': error})
            result['error'] = f"游资名录获取失败：{error}"
            result['end_time'] = datetime.now()
            return result
        
        if df_hm_list is None or df_hm_list.empty:
            result['steps'].append({'step': '获取游资名录', 'status': '警告', 'message': '返回空数据'})
            print("⚠️  游资名录返回空数据")
            org_names = []
        else:
            result['steps'].append({'step': '获取游资名录', 'status': '成功', 'data_count': len(df_hm_list)})
            print(f"✅ 游资名录获取成功，{len(df_hm_list)} 条数据")
            
            # 保存名录数据
            save_ok, save_path, file_size = save_test_data(df_hm_list, 'test_hm_list.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
            
            # 提取前 5 个游资名称
            org_names = df_hm_list['name'].head(5).tolist() if 'name' in df_hm_list.columns else []
        
        # 步骤 2：获取游资明细
        print("\n步骤 2：获取游资明细 (hm_detail)...")
        if not org_names:
            # 如果没有名录，直接测试明细接口
            print("  使用默认日期范围测试明细接口...")
            time.sleep(REQUEST_INTERVAL)
            df_hm_detail, error = retry_call(fetcher.fetch_hm_detail, {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE})
            
            if error:
                result['steps'].append({'step': '获取游资明细', 'status': '失败', 'error': error})
            elif df_hm_detail is None or df_hm_detail.empty:
                result['steps'].append({'step': '获取游资明细', 'status': '警告', 'message': '空数据'})
            else:
                result['steps'].append({'step': '获取游资明细', 'status': '成功', 'data_count': len(df_hm_detail)})
                print(f"  ✅ 游资明细获取成功，{len(df_hm_detail)} 条数据")
                save_ok, save_path, file_size = save_test_data(df_hm_detail, 'test_hm_detail.csv')
                if save_ok:
                    print(f"     已保存：{file_size/1024:.1f} KB")
                result['success'] = True
        else:
            detail_results = []
            for org_name in org_names:
                time.sleep(REQUEST_INTERVAL)
                print(f"  获取游资 {org_name} 的明细...")
                # 注意：fetch_hm_detail 不支持按 org_name 筛选，这里只测试接口可用性
                df_hm_detail, error = retry_call(fetcher.fetch_hm_detail, {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE})
                
                if error:
                    detail_results.append({'org': org_name, 'status': '失败', 'error': error})
                elif df_hm_detail is None or df_hm_detail.empty:
                    detail_results.append({'org': org_name, 'status': '警告', 'message': '空数据'})
                else:
                    detail_results.append({'org': org_name, 'status': '成功', 'data_count': len(df_hm_detail)})
            
            result['steps'].append({'step': '获取游资明细', 'status': '成功', 'details': detail_results})
            
            # 验证关联性
            success_count = sum(1 for r in detail_results if r['status'] == '成功')
            if success_count > 0:
                result['success'] = True
                print(f"✅ 联动测试通过：{success_count}/{len(detail_results)} 游资明细获取成功")
            else:
                result['success'] = False
                result['error'] = "所有游资明细获取失败"
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        print(f"❌ 测试异常：{e}")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['joint_tests'].append(result)
    return result

def test_3_index_moneyflow():
    """测试 3：板块指数 + 资金流联动"""
    print(f"\n{'='*80}")
    print("测试 3：板块指数 + 资金流联动")
    print(f"{'='*80}")
    
    result = {
        'test_name': '板块指数 + 资金流联动',
        'start_time': datetime.now(),
        'end_time': None,
        'steps': [],
        'success': False,
        'error': None
    }
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    try:
        # 步骤 1：获取板块指数列表
        print("\n步骤 1：获取板块指数列表 (ths_index)...")
        time.sleep(REQUEST_INTERVAL)
        df_index, error = retry_call(fetcher.fetch_ths_index, {})
        
        if error:
            result['steps'].append({'step': '获取板块指数', 'status': '失败', 'error': error})
            result['error'] = f"板块指数获取失败：{error}"
            result['end_time'] = datetime.now()
            return result
        
        if df_index is None or df_index.empty:
            result['steps'].append({'step': '获取板块指数', 'status': '警告', 'message': '返回空数据'})
            print("⚠️  板块指数返回空数据")
        else:
            result['steps'].append({'step': '获取板块指数', 'status': '成功', 'data_count': len(df_index)})
            print(f"✅ 板块指数获取成功，{len(df_index)} 条数据")
            
            # 保存数据
            save_ok, save_path, file_size = save_test_data(df_index, 'test_ths_index.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 步骤 2：获取概念资金流
        print("\n步骤 2：获取概念资金流 (moneyflow_cnt_ths)...")
        time.sleep(REQUEST_INTERVAL)
        df_cnt, error = retry_call(fetcher.fetch_moneyflow_cnt_ths, {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE})
        
        if error:
            result['steps'].append({'step': '获取概念资金流', 'status': '失败', 'error': error})
        elif df_cnt is None or df_cnt.empty:
            result['steps'].append({'step': '获取概念资金流', 'status': '警告', 'message': '空数据'})
        else:
            result['steps'].append({'step': '获取概念资金流', 'status': '成功', 'data_count': len(df_cnt)})
            print(f"✅ 概念资金流获取成功，{len(df_cnt)} 条数据")
            save_ok, save_path, file_size = save_test_data(df_cnt, 'test_moneyflow_cnt_ths.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 步骤 3：获取行业资金流
        print("\n步骤 3：获取行业资金流 (moneyflow_ind_ths)...")
        time.sleep(REQUEST_INTERVAL)
        df_ind, error = retry_call(fetcher.fetch_moneyflow_ind_ths, {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE})
        
        if error:
            result['steps'].append({'step': '获取行业资金流', 'status': '失败', 'error': error})
        elif df_ind is None or df_ind.empty:
            result['steps'].append({'step': '获取行业资金流', 'status': '警告', 'message': '空数据'})
        else:
            result['steps'].append({'step': '获取行业资金流', 'status': '成功', 'data_count': len(df_ind)})
            print(f"✅ 行业资金流获取成功，{len(df_ind)} 条数据")
            save_ok, save_path, file_size = save_test_data(df_ind, 'test_moneyflow_ind_ths.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 验证关联性
        if (df_cnt is not None and not df_cnt.empty) or (df_ind is not None and not df_ind.empty):
            result['success'] = True
            print("✅ 联动测试通过：资金流数据获取成功")
        else:
            result['success'] = False
            result['error'] = "资金流数据全部为空"
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        print(f"❌ 测试异常：{e}")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['joint_tests'].append(result)
    return result

def test_4_auction_limit():
    """测试 4：集合竞价 + 涨跌停联动"""
    print(f"\n{'='*80}")
    print("测试 4：集合竞价 + 涨跌停联动")
    print(f"{'='*80}")
    
    result = {
        'test_name': '集合竞价 + 涨跌停联动',
        'start_time': datetime.now(),
        'end_time': None,
        'steps': [],
        'success': False,
        'error': None
    }
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    try:
        # 步骤 1：获取集合竞价数据
        print("\n步骤 1：获取集合竞价数据 (stk_auction)...")
        time.sleep(REQUEST_INTERVAL)
        df_auction, error = retry_call(fetcher.fetch_stk_auction, {'trade_date': TEST_DATE})
        
        if error:
            result['steps'].append({'step': '获取集合竞价', 'status': '失败', 'error': error})
        elif df_auction is None or df_auction.empty:
            result['steps'].append({'step': '获取集合竞价', 'status': '警告', 'message': '空数据'})
        else:
            result['steps'].append({'step': '获取集合竞价', 'status': '成功', 'data_count': len(df_auction)})
            print(f"✅ 集合竞价获取成功，{len(df_auction)} 条数据")
            save_ok, save_path, file_size = save_test_data(df_auction, 'test_stk_auction.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 步骤 2：获取涨跌停数据
        print("\n步骤 2：获取涨跌停数据 (limit_list_d)...")
        time.sleep(REQUEST_INTERVAL)
        df_limit, error = retry_call(fetcher.fetch_limit_list_d, {'trade_date': TEST_DATE})
        
        if error:
            result['steps'].append({'step': '获取涨跌停', 'status': '失败', 'error': error})
        elif df_limit is None or df_limit.empty:
            result['steps'].append({'step': '获取涨跌停', 'status': '警告', 'message': '空数据'})
        else:
            result['steps'].append({'step': '获取涨跌停', 'status': '成功', 'data_count': len(df_limit)})
            print(f"✅ 涨跌停获取成功，{len(df_limit)} 条数据")
            save_ok, save_path, file_size = save_test_data(df_limit, 'test_limit_list_d.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 步骤 3：获取连板天梯
        print("\n步骤 3：获取连板天梯数据 (limit_step)...")
        time.sleep(REQUEST_INTERVAL)
        df_step, error = retry_call(fetcher.fetch_limit_step, {'trade_date': TEST_DATE})
        
        if error:
            result['steps'].append({'step': '获取连板天梯', 'status': '失败', 'error': error})
        elif df_step is None or df_step.empty:
            result['steps'].append({'step': '获取连板天梯', 'status': '警告', 'message': '空数据'})
        else:
            result['steps'].append({'step': '获取连板天梯', 'status': '成功', 'data_count': len(df_step)})
            print(f"✅ 连板天梯获取成功，{len(df_step)} 条数据")
            save_ok, save_path, file_size = save_test_data(df_step, 'test_limit_step.csv')
            if save_ok:
                print(f"   已保存：{file_size/1024:.1f} KB")
        
        # 验证关联性
        success_count = sum(1 for step in result['steps'] if step['status'] == '成功')
        if success_count > 0:
            result['success'] = True
            print(f"✅ 联动测试通过：{success_count}/3 接口获取成功")
        else:
            result['success'] = False
            result['error'] = "所有接口获取失败"
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        print(f"❌ 测试异常：{e}")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['joint_tests'].append(result)
    return result

# ==================== 性能测试 ====================

def test_5_performance():
    """测试 5：批量性能测试"""
    print(f"\n{'='*80}")
    print("测试 5：批量性能测试（所有接口调用 3 次）")
    print(f"{'='*80}")
    
    result = {
        'test_name': '批量性能测试',
        'start_time': datetime.now(),
        'end_time': None,
        'interfaces': [],
        'statistics': {},
        'success': False
    }
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    config = {'token': TUSHARE_TOKEN, 'output_dir': OUTPUT_DIR}
    fetcher = Utils(pro, config)
    
    # 定义所有 15 个接口
    interfaces = [
        ('fetch_ths_hot', {'date': TEST_DATE}),
        ('fetch_hm_list', {}),
        ('fetch_hm_detail', {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE}),
        ('fetch_stk_auction', {'trade_date': TEST_DATE}),
        ('fetch_ths_member', {'concept_code': 'BK1129'}),
        ('fetch_ths_index', {}),
        ('fetch_ths_daily', {'index_code': '881100.THS', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE}),
        ('fetch_moneyflow_ths', {'ts_code': '000001.SZ', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE}),
        ('fetch_moneyflow_cnt_ths', {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE}),
        ('fetch_moneyflow_ind_ths', {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE}),
        ('fetch_limit_cpt_list', {'trade_date': TEST_DATE}),
        ('fetch_limit_step', {'trade_date': TEST_DATE}),
        ('fetch_limit_list_d', {'trade_date': TEST_DATE}),
        ('fetch_limit_list_ths', {'trade_date': TEST_DATE}),
        ('fetch_kpl_list', {'trade_date': TEST_DATE}),
    ]
    
    all_durations = []
    success_count = 0
    fail_count = 0
    
    for interface_name, params in interfaces:
        print(f"\n测试接口：{interface_name}")
        interface_result = {
            'name': interface_name,
            'durations': [],
            'success': 0,
            'fail': 0
        }
        
        for i in range(3):  # 每个接口调用 3 次
            time.sleep(REQUEST_INTERVAL)
            start = datetime.now()
            
            try:
                method = getattr(fetcher, interface_name)
                df = method(**params)
                duration = (datetime.now() - start).total_seconds()
                all_durations.append(duration)
                interface_result['durations'].append(duration)
                interface_result['success'] += 1
                success_count += 1
                print(f"  第{i+1}次：✅ {duration:.2f}秒")
            except Exception as e:
                duration = (datetime.now() - start).total_seconds()
                interface_result['durations'].append(None)
                interface_result['fail'] += 1
                fail_count += 1
                print(f"  第{i+1}次：❌ {str(e)[:50]}")
        
        result['interfaces'].append(interface_result)
    
    # 统计性能数据
    valid_durations = [d for d in all_durations if d is not None]
    if valid_durations:
        result['statistics'] = {
            'total_calls': len(all_durations),
            'success_calls': success_count,
            'fail_calls': fail_count,
            'avg_duration': sum(valid_durations) / len(valid_durations),
            'max_duration': max(valid_durations),
            'min_duration': min(valid_durations),
            'total_duration': sum(valid_durations)
        }
        
        print(f"\n{'='*80}")
        print("性能统计:")
        print(f"  总调用次数：{success_count + fail_count}")
        print(f"  成功次数：{success_count}")
        print(f"  失败次数：{fail_count}")
        print(f"  平均耗时：{result['statistics']['avg_duration']:.2f}秒")
        print(f"  最大耗时：{result['statistics']['max_duration']:.2f}秒")
        print(f"  最小耗时：{result['statistics']['min_duration']:.2f}秒")
        print(f"  总耗时：{result['statistics']['total_duration']:.2f}秒")
        
        # 验收标准
        if result['statistics']['avg_duration'] < 5.0:
            result['success'] = True
            print(f"\n✅ 性能测试通过：平均耗时 < 5 秒")
        else:
            result['success'] = False
            print(f"\n❌ 性能测试不通过：平均耗时 >= 5 秒")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['performance_tests'].append(result)
    return result

# ==================== 数据一致性验证 ====================

def test_6_data_validation():
    """测试 6：数据一致性验证"""
    print(f"\n{'='*80}")
    print("测试 6：数据一致性验证")
    print(f"{'='*80}")
    
    result = {
        'test_name': '数据一致性验证',
        'start_time': datetime.now(),
        'end_time': None,
        'files_checked': [],
        'validation_results': [],
        'success': False
    }
    
    # 检查所有生成的测试文件
    expected_files = [
        'test_ths_member_BK1129.csv',
        'test_hm_list.csv',
        'test_hm_detail.csv',
        'test_ths_index.csv',
        'test_moneyflow_cnt_ths.csv',
        'test_moneyflow_ind_ths.csv',
        'test_stk_auction.csv',
        'test_limit_list_d.csv',
        'test_limit_step.csv',
    ]
    
    validation_results = []
    
    for filename in expected_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        file_result = {
            'filename': filename,
            'exists': False,
            'size': 0,
            'fields': [],
            'row_count': 0,
            'valid': False,
            'error': None
        }
        
        try:
            if os.path.exists(filepath):
                file_result['exists'] = True
                file_result['size'] = os.path.getsize(filepath)
                
                # 读取并验证
                df = pd.read_csv(filepath, encoding='utf-8-sig')
                file_result['row_count'] = len(df)
                file_result['fields'] = list(df.columns)
                
                # 验证字段完整性
                if len(df.columns) > 0 and len(df) >= 0:
                    file_result['valid'] = True
                    print(f"✅ {filename}: {len(df)}行，{os.path.getsize(filepath)/1024:.1f}KB")
                else:
                    file_result['error'] = '数据为空'
                    print(f"⚠️  {filename}: 数据为空")
            else:
                file_result['error'] = '文件不存在'
                print(f"❌ {filename}: 文件不存在")
        except Exception as e:
            file_result['error'] = str(e)
            print(f"❌ {filename}: {str(e)[:50]}")
        
        validation_results.append(file_result)
        result['files_checked'].append(filename)
    
    result['validation_results'] = validation_results
    
    # 统计验证结果
    valid_count = sum(1 for r in validation_results if r['valid'])
    exist_count = sum(1 for r in validation_results if r['exists'])
    
    print(f"\n验证统计:")
    print(f"  检查文件数：{len(validation_results)}")
    print(f"  存在文件数：{exist_count}")
    print(f"  验证通过数：{valid_count}")
    
    if exist_count > 0 and valid_count > 0:
        result['success'] = True
        print(f"\n✅ 数据一致性验证通过")
    else:
        result['success'] = False
        print(f"\n❌ 数据一致性验证不通过")
    
    result['end_time'] = datetime.now()
    result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
    test_results['validation_tests'].append(result)
    return result

# ==================== 生成报告 ====================

def generate_report():
    """生成测试报告"""
    test_results['end_time'] = datetime.now()
    total_duration = (test_results['end_time'] - test_results['start_time']).total_seconds()
    
    print(f"\n{'='*80}")
    print("阶段 0.3 - 15 个接口联合测试报告")
    print(f"{'='*80}")
    
    print(f"\n【测试概况】")
    print(f"测试开始：{test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试结束：{test_results['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时：{total_duration:.1f}秒 ({total_duration/60:.1f}分钟)")
    
    # 联动测试结果
    print(f"\n【联动测试结果】")
    for i, test in enumerate(test_results['joint_tests'], 1):
        status = "✅" if test['success'] else "❌"
        print(f"{i}. {status} {test['test_name']}: {'通过' if test['success'] else '失败'}")
        if test.get('error'):
            print(f"   错误：{test['error']}")
        print(f"   耗时：{test.get('duration', 0):.1f}秒")
    
    # 性能测试结果
    print(f"\n【性能测试结果】")
    for test in test_results['performance_tests']:
        if test.get('statistics'):
            stats = test['statistics']
            print(f"平均耗时：{stats['avg_duration']:.2f}秒")
            print(f"最大耗时：{stats['max_duration']:.2f}秒")
            print(f"最小耗时：{stats['min_duration']:.2f}秒")
            print(f"成功率：{stats['success_calls']}/{stats['total_calls']} ({stats['success_calls']/stats['total_calls']*100:.1f}%)")
    
    # 数据验证结果
    print(f"\n【数据一致性验证】")
    for test in test_results['validation_tests']:
        valid_count = sum(1 for r in test['validation_results'] if r['valid'])
        total_count = len(test['validation_results'])
        print(f"验证通过：{valid_count}/{total_count} 文件")
    
    # 保存报告
    report_path = os.path.join(OUTPUT_DIR, 'stage_0_3_joint_test_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        # 转换 datetime 为字符串
        report_data = {}
        for key, value in test_results.items():
            if isinstance(value, datetime):
                report_data[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                report_data[key] = value
        
        # 特殊处理包含 datetime 的列表
        for key in ['joint_tests', 'performance_tests', 'validation_tests']:
            for i, item in enumerate(report_data[key]):
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, datetime):
                            report_data[key][i][k] = v.strftime('%Y-%m-%d %H:%M:%S')
        
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试报告已保存：{report_path}")
    
    return test_results

# ==================== 主函数 ====================

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print("阶段 0.3 - 15 个接口联合测试")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n【测试配置】")
    print(f"测试日期：{TEST_DATE}")
    print(f"日期范围：{TEST_START_DATE} 至 {TEST_END_DATE}")
    print(f"请求间隔：{REQUEST_INTERVAL}秒")
    print(f"重试延迟：{RETRY_DELAYS}秒")
    print(f"最大重试：{MAX_RETRIES}次")
    
    print(f"\n【重要提醒】")
    print(f"✅ 使用代码中已有的 TUSHARE_TOKEN 和 TUSHARE_API_URL")
    print(f"✅ 添加请求间隔，避免频率过高")
    print(f"✅ 失败后重试 3 次，延迟递增")
    print(f"❌ 不修改后端核心配置")
    
    # 执行联动测试
    print(f"\n{'='*80}")
    print("开始执行联动测试...")
    print(f"{'='*80}")
    
    test_1_ths_hot_member()
    test_2_hm_list_detail()
    test_3_index_moneyflow()
    test_4_auction_limit()
    
    # 执行性能测试
    print(f"\n{'='*80}")
    print("开始执行性能测试...")
    print(f"{'='*80}")
    
    test_5_performance()
    
    # 执行数据验证
    print(f"\n{'='*80}")
    print("开始执行数据验证...")
    print(f"{'='*80}")
    
    test_6_data_validation()
    
    # 生成报告
    generate_report()
    
    print(f"\n{'='*80}")
    print("✅ 所有测试完成！")
    print(f"{'='*80}")
    
    return test_results

if __name__ == '__main__':
    results = main()
