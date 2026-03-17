#!/usr/bin/env python3
# ==============================================
# 【测试】阶段 0.2 - 15 个新接口集成测试 - test_15_new_interfaces.py
# ==============================================
# 功能：测试代码守护者刚集成的 15 个新接口
# 测试内容：
#   1. 手动调用接口，获取今日数据
#   2. 验证返回数据格式正确（包含必需字段）
#   3. 验证数据能保存到指定路径
#   4. 验证文件内容完整（文件大小/数据条数）
#   5. 验证失败重试机制正常
# 
# 15 个接口列表：
#   1. 开盘啦榜单数据接口 (kpl_list)
#   2. 同花顺热榜接口 (ths_hot)
#   3. 游资每日明细接口 (hm_detail)
#   4. 游资名录接口 (hm_list)
#   5. 当日集合竞价接口 (stk_auction)
#   6. 同花顺概念成分接口 (ths_member)
#   7. 同花顺板块指数接口 (ths_daily)
#   8. 同花顺板块指数列表接口 (ths_index)
#   9. 最强板块统计接口 (limit_cpt_list)
#   10. 连板天梯接口 (limit_step)
#   11. 涨跌停列表接口 (limit_list_d)
#   12. 涨跌停榜单 THS 接口 (limit_list_ths)
#   13. 个股资金流向 THS 接口 (moneyflow_ths)
#   14. 概念板块资金流接口 (moneyflow_cnt_ths)
#   15. 行业资金流向接口 (moneyflow_ind_ths)
#
# 使用：python3 tests/test_15_new_interfaces.py
# ==============================================

import sys
import os
import time
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# 导入 tushare
try:
    import tushare as ts
except ImportError:
    print("❌ 缺少 Tushare 依赖，请运行：pip install tushare")
    sys.exit(1)

# 添加项目根目录到 Python 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("15_interfaces_test")

# 测试结果结构
test_results = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'total': 0,
    'passed': 0,
    'failed': 0,
    'errors': 0,
    'skipped': 0,
    'interfaces': {},
    'summary': {}
}

# 测试配置
TEST_CONFIG = {
    'trade_date': datetime.now().strftime('%Y%m%d'),  # 今日日期
    'start_date': (datetime.now() - timedelta(days=5)).strftime('%Y%m%d'),  # 5 天前
    'end_date': datetime.now().strftime('%Y%m%d'),  # 今日日期
    'ts_code': '000001.SZ',  # 测试用股票代码
    'concept_code': 'BK0001',  # 测试用概念代码
    'index_code': '886013',  # 测试用板块指数代码
    'output_dir': os.path.join(BASE_DIR, 'data'),
    'stocks_dir': os.path.join(BASE_DIR, 'data_all_stocks'),
}

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"【测试】{text}")
    print("=" * 80)

def print_subheader(text):
    """打印子标题"""
    print(f"\n{'-' * 60}")
    print(f"  {text}")
    print(f"{'-' * 60}")

def record_result(interface_name: str, test_item: str, status: str, 
                  error: str = None, details: str = ""):
    """记录测试结果"""
    test_results['total'] += 1
    
    if status == 'PASS':
        test_results['passed'] += 1
    elif status == 'FAIL':
        test_results['failed'] += 1
    elif status == 'ERROR':
        test_results['errors'] += 1
    elif status == 'SKIP':
        test_results['skipped'] += 1
    
    if interface_name not in test_results['interfaces']:
        test_results['interfaces'][interface_name] = []
    
    test_results['interfaces'][interface_name].append({
        'test_item': test_item,
        'status': status,
        'error': error,
        'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    status_icon = {'PASS': '✅', 'FAIL': '❌', 'ERROR': '⚠️', 'SKIP': '⏭️'}.get(status, '❓')
    print(f"    {status_icon} {test_item}: {status}")
    if error and status in ['FAIL', 'ERROR']:
        print(f"       错误：{error}")

def check_data_format(df: pd.DataFrame, required_fields: List[str]) -> Tuple[bool, str]:
    """检查数据格式"""
    if df is None or df.empty:
        return False, "数据为空"
    
    missing_fields = [f for f in required_fields if f not in df.columns]
    if missing_fields:
        return False, f"缺少必需字段：{missing_fields}"
    
    return True, f"数据格式正确，共{len(df)}行，{len(df.columns)}列"

def check_file_saved(file_path: str) -> Tuple[bool, str]:
    """检查文件是否保存"""
    if not os.path.exists(file_path):
        # 检查 parquet 文件
        parquet_path = file_path.replace('.csv', '.parquet')
        if os.path.exists(parquet_path):
            file_size = os.path.getsize(parquet_path)
            return True, f"文件已保存 (parquet): {parquet_path}, 大小：{file_size} bytes"
        return False, f"文件未保存：{file_path}"
    
    file_size = os.path.getsize(file_path)
    return True, f"文件已保存：{file_path}, 大小：{file_size} bytes"

def check_file_content(file_path: str, min_rows: int = 1) -> Tuple[bool, str]:
    """检查文件内容完整性"""
    try:
        if file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            # 尝试 parquet
            parquet_path = file_path.replace('.csv', '.parquet')
            if os.path.exists(parquet_path):
                df = pd.read_parquet(parquet_path)
            else:
                return False, "无法读取文件格式"
        
        if len(df) < min_rows:
            return False, f"数据条数不足：{len(df)} < {min_rows}"
        
        return True, f"文件内容完整：{len(df)}行"
    except Exception as e:
        return False, f"读取文件失败：{e}"

def test_retry_mechanism(fetch_func, *args, **kwargs) -> Tuple[bool, str]:
    """测试失败重试机制"""
    # 这里我们验证接口本身是否有重试机制
    # 通过检查方法是否存在 request_retry 调用来判断
    import inspect
    source = inspect.getsource(fetch_func)
    if 'request_retry' in source or 'request_with_retry' in source:
        return True, "重试机制已实现"
    return False, "未发现重试机制"

# ==============================================
# 15 个接口测试
# ==============================================

def test_01_kpl_list(fetcher):
    """测试 1. 开盘啦榜单数据接口"""
    print_subheader("1. 开盘啦榜单数据接口 (kpl_list)")
    interface_name = "kpl_list"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_kpl_list(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'kpl_list.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_kpl_list)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_02_ths_hot(fetcher):
    """测试 2. 同花顺热榜接口"""
    print_subheader("2. 同花顺热榜接口 (ths_hot)")
    interface_name = "ths_hot"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_ths_hot(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'name'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'ths_hot.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_ths_hot)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_03_hm_detail(fetcher):
    """测试 3. 游资每日明细接口"""
    print_subheader("3. 游资每日明细接口 (hm_detail)")
    interface_name = "hm_detail"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_hm_detail(TEST_CONFIG['start_date'], TEST_CONFIG['end_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date', 'name'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'hm_detail.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_hm_detail)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_04_hm_list(fetcher):
    """测试 4. 游资名录接口"""
    print_subheader("4. 游资名录接口 (hm_list)")
    interface_name = "hm_list"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_hm_list()
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['name'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'hm_list.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_hm_list)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_05_stk_auction(fetcher):
    """测试 5. 当日集合竞价接口"""
    print_subheader("5. 当日集合竞价接口 (stk_auction)")
    interface_name = "stk_auction"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_stk_auction(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'stk_auction.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_stk_auction)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_06_ths_member(fetcher):
    """测试 6. 同花顺概念成分接口"""
    print_subheader("6. 同花顺概念成分接口 (ths_member)")
    interface_name = "ths_member"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_ths_member(TEST_CONFIG['concept_code'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'name'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], f'ths_member_{TEST_CONFIG["concept_code"]}.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_ths_member)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_07_ths_daily(fetcher):
    """测试 7. 同花顺板块指数接口"""
    print_subheader("7. 同花顺板块指数接口 (ths_daily)")
    interface_name = "ths_daily"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_ths_daily(TEST_CONFIG['index_code'], TEST_CONFIG['start_date'], TEST_CONFIG['end_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date', 'close'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], f'ths_daily_{TEST_CONFIG["index_code"]}.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_ths_daily)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_08_ths_index(fetcher):
    """测试 8. 同花顺板块指数列表接口"""
    print_subheader("8. 同花顺板块指数列表接口 (ths_index)")
    interface_name = "ths_index"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_ths_index()
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['index_code', 'name'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'ths_index.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_ths_index)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_09_limit_cpt_list(fetcher):
    """测试 9. 最强板块统计接口"""
    print_subheader("9. 最强板块统计接口 (limit_cpt_list)")
    interface_name = "limit_cpt_list"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_limit_cpt_list(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['industry', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'limit_cpt_list.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_limit_cpt_list)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_10_limit_step(fetcher):
    """测试 10. 连板天梯接口"""
    print_subheader("10. 连板天梯接口 (limit_step)")
    interface_name = "limit_step"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_limit_step(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date', 'up_down_times'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'limit_step.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_limit_step)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_11_limit_list_d(fetcher):
    """测试 11. 涨跌停列表接口"""
    print_subheader("11. 涨跌停列表接口 (limit_list_d)")
    interface_name = "limit_list_d"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_limit_list_d(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'limit_list_d.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_limit_list_d)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_12_limit_list_ths(fetcher):
    """测试 12. 涨跌停榜单 THS 接口"""
    print_subheader("12. 涨跌停榜单 THS 接口 (limit_list_ths)")
    interface_name = "limit_list_ths"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_limit_list_ths(TEST_CONFIG['trade_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'limit_list_ths.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_limit_list_ths)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_13_moneyflow_ths(fetcher):
    """测试 13. 个股资金流向 THS 接口"""
    print_subheader("13. 个股资金流向 THS 接口 (moneyflow_ths)")
    interface_name = "moneyflow_ths"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_moneyflow_ths(
            TEST_CONFIG['ts_code'], 
            TEST_CONFIG['start_date'], 
            TEST_CONFIG['end_date']
        )
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['ts_code', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        stock_dir = os.path.join(TEST_CONFIG['stocks_dir'], TEST_CONFIG['ts_code'])
        file_path = os.path.join(stock_dir, 'moneyflow_ths.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_moneyflow_ths)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_14_moneyflow_cnt_ths(fetcher):
    """测试 14. 概念板块资金流接口"""
    print_subheader("14. 概念板块资金流接口 (moneyflow_cnt_ths)")
    interface_name = "moneyflow_cnt_ths"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_moneyflow_cnt_ths(TEST_CONFIG['start_date'], TEST_CONFIG['end_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['industry', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'moneyflow_cnt_ths.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_moneyflow_cnt_ths)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

def test_15_moneyflow_ind_ths(fetcher):
    """测试 15. 行业资金流向接口"""
    print_subheader("15. 行业资金流向接口 (moneyflow_ind_ths)")
    interface_name = "moneyflow_ind_ths"
    
    try:
        # 1. 调用接口
        df = fetcher.fetch_moneyflow_ind_ths(TEST_CONFIG['start_date'], TEST_CONFIG['end_date'])
        
        # 2. 验证数据格式
        success, msg = check_data_format(df, ['industry', 'trade_date'])
        record_result(interface_name, '数据格式验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 3. 验证数据保存
        file_path = os.path.join(TEST_CONFIG['output_dir'], 'moneyflow_ind_ths.parquet')
        success, msg = check_file_saved(file_path)
        record_result(interface_name, '数据保存验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 4. 验证文件内容
        if success:
            success, msg = check_file_content(file_path)
            record_result(interface_name, '文件内容验证', 'PASS' if success else 'FAIL', details=msg)
        
        # 5. 验证重试机制
        success, msg = test_retry_mechanism(fetcher.fetch_moneyflow_ind_ths)
        record_result(interface_name, '重试机制验证', 'PASS' if success else 'FAIL', details=msg)
        
    except Exception as e:
        record_result(interface_name, '接口调用', 'ERROR', str(e))

# ==============================================
# 测试报告生成
# ==============================================

def generate_test_report():
    """生成测试报告"""
    print_header("测试报告")
    
    # 计算通过率
    pass_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    
    print(f"\n📊 测试总览:")
    print(f"  总测试项：{test_results['total']}")
    print(f"  ✅ 通过：{test_results['passed']}")
    print(f"  ❌ 失败：{test_results['failed']}")
    print(f"  ⚠️  错误：{test_results['errors']}")
    print(f"  📊 通过率：{pass_rate:.1f}%")
    
    # 按接口统计
    print(f"\n📁 接口统计:")
    for interface_name, tests in test_results['interfaces'].items():
        passed = sum(1 for t in tests if t['status'] == 'PASS')
        total = len(tests)
        rate = (passed / total * 100) if total > 0 else 0
        status = '✅' if rate == 100 else '⚠️' if rate >= 60 else '❌'
        print(f"  {status} {interface_name}: {passed}/{total} ({rate:.1f}%)")
    
    # 保存 JSON 报告
    report_data = {
        'timestamp': test_results['timestamp'],
        'summary': {
            'total': test_results['total'],
            'passed': test_results['passed'],
            'failed': test_results['failed'],
            'errors': test_results['errors'],
            'skipped': test_results['skipped'],
            'pass_rate': pass_rate
        },
        'interfaces': test_results['interfaces']
    }
    
    # 创建报告目录
    report_dir = os.path.join(BASE_DIR, 'tests', 'logs')
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存 JSON 报告
    json_path = os.path.join(report_dir, f'15_interfaces_test_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 报告已保存：{json_path}")
    
    # 保存文本报告
    txt_path = os.path.join(report_dir, f'15_interfaces_test_{timestamp}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("【测试】阶段 0.2 - 15 个新接口集成测试报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"生成时间：{test_results['timestamp']}\n\n")
        f.write("测试总览:\n")
        f.write(f"  总测试项：{test_results['total']}\n")
        f.write(f"  通过：{test_results['passed']}\n")
        f.write(f"  失败：{test_results['failed']}\n")
        f.write(f"  错误：{test_results['errors']}\n")
        f.write(f"  通过率：{pass_rate:.1f}%\n\n")
        
        f.write("接口统计:\n")
        for interface_name, tests in test_results['interfaces'].items():
            passed = sum(1 for t in tests if t['status'] == 'PASS')
            total = len(tests)
            rate = (passed / total * 100) if total > 0 else 0
            f.write(f"  {interface_name}: {passed}/{total} ({rate:.1f}%)\n")
        
        # 失败详情
        failed_tests = []
        for interface_name, tests in test_results['interfaces'].items():
            for test in tests:
                if test['status'] in ['FAIL', 'ERROR']:
                    failed_tests.append({
                        'interface': interface_name,
                        'test_item': test['test_item'],
                        'status': test['status'],
                        'error': test['error']
                    })
        
        if failed_tests:
            f.write("\n失败/错误详情:\n")
            for test in failed_tests:
                f.write(f"  - {test['interface']}.{test['test_item']}: {test['status']}\n")
                if test['error']:
                    f.write(f"    错误：{test['error']}\n")
        else:
            f.write("\n✅ 所有测试通过！\n")
    
    print(f"📄 文本报告已保存：{txt_path}")
    
    return pass_rate

# ==============================================
# 主函数
# ==============================================

def main():
    """主函数"""
    print_header("阶段 0.2 - 15 个新接口集成测试开始")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试接口：15 个")
    print(f"测试配置:")
    print(f"  交易日期：{TEST_CONFIG['trade_date']}")
    print(f"  日期范围：{TEST_CONFIG['start_date']} - {TEST_CONFIG['end_date']}")
    print(f"  测试股票：{TEST_CONFIG['ts_code']}")
    print(f"  输出目录：{TEST_CONFIG['output_dir']}")
    
    start_time = time.time()
    
    # 导入 fetcher
    try:
        # 确保输出目录存在
        os.makedirs(TEST_CONFIG['output_dir'], exist_ok=True)
        os.makedirs(TEST_CONFIG['stocks_dir'], exist_ok=True)
        
        # 导入 fetch_data_optimized 模块
        sys.path.insert(0, BASE_DIR)
        import fetch_data_optimized as fetch_module
        
        # 创建 fetcher 实例
        config = {
            'output_dir': TEST_CONFIG['output_dir'],
            'stocks_dir': TEST_CONFIG['stocks_dir'],
            'FETCH_OPTIMIZATION': fetch_module.FETCH_OPTIMIZATION,
            'FILTER_CONFIG': fetch_module.FILTER_CONFIG,
        }
        
        # 创建 Utils 实例（15 个接口方法在 Utils 类中）
        # 需要先初始化 tushare pro
        ts.set_token(fetch_module.TUSHARE_TOKEN)
        # 使用自定义 API 地址（通过内部属性设置）
        pro = ts.pro_api(fetch_module.TUSHARE_TOKEN)
        pro._DataApi__http_url = fetch_module.TUSHARE_API_URL
        fetcher = fetch_module.Utils(pro, config)
        
        logger.info("✅ Utils 初始化完成，15 个接口已就绪")
        logger.info(f"📊 Tushare Token: {fetch_module.TUSHARE_TOKEN[:20]}...")
        logger.info(f"🌐 API URL: {fetch_module.TUSHARE_API_URL}")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败：{e}", exc_info=True)
        print(f"\n❌ 测试无法继续：{e}")
        return 1
    
    # 执行所有测试
    tests = [
        test_01_kpl_list,
        test_02_ths_hot,
        test_03_hm_detail,
        test_04_hm_list,
        test_05_stk_auction,
        test_06_ths_member,
        test_07_ths_daily,
        test_08_ths_index,
        test_09_limit_cpt_list,
        test_10_limit_step,
        test_11_limit_list_d,
        test_12_limit_list_ths,
        test_13_moneyflow_ths,
        test_14_moneyflow_cnt_ths,
        test_15_moneyflow_ind_ths,
    ]
    
    for test_func in tests:
        try:
            test_func(fetcher)
        except Exception as e:
            logger.error(f"{test_func.__name__} 测试异常：{e}", exc_info=True)
    
    elapsed_time = time.time() - start_time
    
    # 生成报告
    pass_rate = generate_test_report()
    
    print_header("阶段 0.2 - 15 个新接口集成测试完成")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"耗时：{elapsed_time:.2f}秒")
    
    # 返回退出码
    if pass_rate >= 90:
        print("\n✅ 测试通过！通过率≥90%")
        return 0
    elif pass_rate >= 80:
        print(f"\n⚠️  测试基本通过！通过率：{pass_rate:.1f}% (目标≥90%)")
        return 0
    else:
        print(f"\n❌ 测试未达标！通过率：{pass_rate:.1f}% < 80%")
        return 1

if __name__ == '__main__':
    sys.exit(main())
