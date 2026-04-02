# -*- coding: utf-8 -*-
"""
龙虎榜数据单独抓取脚本
用途：补充历史龙虎榜数据（top_list, top_inst, hm_detail）
执行：python scripts/fetch_longhubao.py

【重要】使用源代码中的第三方Tushare代理接口
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import pandas as pd
import time

# ============================================================
# 配置区（与源代码一致）
# ============================================================

# Tushare Token（与源代码一致）
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"

# 第三方代理API地址（与源代码一致）
TUSHARE_API_URL = "http://42.194.163.97:5000"

# 数据输出目录
OUTPUT_DIR = '/data/agents/master/data'

# 请求间隔（秒），避免触发限流
REQUEST_INTERVAL = 0.1

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# ============================================================
# 初始化Tushare API（使用源代码中的方式）
# ============================================================

def init_tushare_api():
    """
    初始化Tushare API
    【重要】使用源代码中的第三方代理接口配置
    """
    try:
        import tushare as ts
    except ImportError:
        print("❌ tushare 未安装，请先安装: pip install tushare")
        return None
    
    # 设置token
    ts.set_token(TUSHARE_TOKEN)
    
    # 创建pro对象
    pro = ts.pro_api()
    
    # 【关键】设置token和API地址（与源代码一致）
    pro._DataApi__token = TUSHARE_TOKEN
    pro._DataApi__http_url = TUSHARE_API_URL
    
    print(f"✅ Tushare API 初始化完成")
    print(f"   API地址: {TUSHARE_API_URL}")
    print(f"   Token: {TUSHARE_TOKEN[:10]}...{TUSHARE_TOKEN[-10:]}")
    
    return pro


def get_trade_dates(pro, start_date, end_date):
    """获取交易日列表"""
    try:
        df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()
            return sorted(trade_dates)
    except Exception as e:
        print(f"❌ 获取交易日失败: {e}")
    return []


def request_with_retry(pro, api_func, **kwargs):
    """带重试的请求"""
    for attempt in range(MAX_RETRIES):
        try:
            df = api_func(**kwargs)
            return df
        except Exception as e:
            error_msg = str(e)
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠️  请求失败({attempt+1}/{MAX_RETRIES}): {error_msg[:80]}")
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"  ❌ 请求最终失败: {error_msg[:80]}")
                return None
    return None


def fetch_top_list(pro, trade_dates, output_path):
    """
    抓取龙虎榜每日明细
    API: pro.top_list(trade_date='YYYYMMDD')
    """
    print(f"\n{'='*60}")
    print(f"开始抓取龙虎榜每日明细 (top_list)")
    print(f"日期范围: {trade_dates[0]} ~ {trade_dates[-1]} ({len(trade_dates)}个交易日)")
    print(f"{'='*60}")
    
    all_data = []
    success_count = 0
    fail_count = 0
    
    # 加载已有数据（追加模式）
    if os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        existing_df['trade_date'] = existing_df['trade_date'].astype(str)
        existing_dates = set(existing_df['trade_date'].unique())
        print(f"已有数据: {len(existing_df)}条, {len(existing_dates)}个交易日")
    else:
        existing_df = pd.DataFrame()
        existing_dates = set()
    
    for i, date in enumerate(trade_dates):
        # 跳过已有日期
        if date in existing_dates:
            continue
        
        # 进度显示
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(trade_dates)} ({(i+1)/len(trade_dates)*100:.0f}%)")
        
        # 请求（按日查询）
        df = request_with_retry(pro, pro.top_list, trade_date=date)
        
        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
        else:
            fail_count += 1
        
        # 间隔
        time.sleep(REQUEST_INTERVAL)
    
    # 合并数据
    if all_data:
        new_df = pd.concat(all_data, ignore_index=True)
        new_df['trade_date'] = new_df['trade_date'].astype(str)
        
        # 与已有数据合并
        if not existing_df.empty:
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        else:
            final_df = new_df
        
        # 保存
        final_df.to_parquet(output_path, index=False)
        print(f"\n✅ top_list 抓取完成:")
        print(f"   新增: {success_count}个交易日")
        print(f"   失败: {fail_count}个交易日")
        print(f"   总计: {len(final_df)}条")
    else:
        print(f"\n⚠️  无新增数据")


def fetch_top_inst(pro, trade_dates, output_path):
    """
    抓取龙虎榜机构席位明细
    API: pro.top_inst(trade_date='YYYYMMDD')
    """
    print(f"\n{'='*60}")
    print(f"开始抓取龙虎榜机构席位明细 (top_inst)")
    print(f"日期范围: {trade_dates[0]} ~ {trade_dates[-1]} ({len(trade_dates)}个交易日)")
    print(f"{'='*60}")
    
    all_data = []
    success_count = 0
    fail_count = 0
    
    # 加载已有数据
    if os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        existing_df['trade_date'] = existing_df['trade_date'].astype(str)
        existing_dates = set(existing_df['trade_date'].unique())
        print(f"已有数据: {len(existing_df)}条, {len(existing_dates)}个交易日")
    else:
        existing_df = pd.DataFrame()
        existing_dates = set()
    
    for i, date in enumerate(trade_dates):
        if date in existing_dates:
            continue
        
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(trade_dates)} ({(i+1)/len(trade_dates)*100:.0f}%)")
        
        # 请求（按日查询）
        df = request_with_retry(pro, pro.top_inst, trade_date=date)
        
        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
        else:
            fail_count += 1
        
        time.sleep(REQUEST_INTERVAL)
    
    if all_data:
        new_df = pd.concat(all_data, ignore_index=True)
        new_df['trade_date'] = new_df['trade_date'].astype(str)
        
        if not existing_df.empty:
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['ts_code', 'trade_date', 'exalter'], keep='last')
        else:
            final_df = new_df
        
        final_df.to_parquet(output_path, index=False)
        print(f"\n✅ top_inst 抓取完成:")
        print(f"   新增: {success_count}个交易日")
        print(f"   失败: {fail_count}个交易日")
        print(f"   总计: {len(final_df)}条")
    else:
        print(f"\n⚠️  无新增数据")


def fetch_hm_detail(pro, trade_dates, output_path):
    """
    抓取游资每日明细
    API: pro.hm_detail(trade_date='YYYYMMDD')
    """
    print(f"\n{'='*60}")
    print(f"开始抓取游资每日明细 (hm_detail)")
    print(f"日期范围: {trade_dates[0]} ~ {trade_dates[-1]} ({len(trade_dates)}个交易日)")
    print(f"{'='*60}")
    
    all_data = []
    success_count = 0
    fail_count = 0
    
    # 加载已有数据
    if os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        existing_df['trade_date'] = existing_df['trade_date'].astype(str)
        existing_dates = set(existing_df['trade_date'].unique())
        print(f"已有数据: {len(existing_df)}条, {len(existing_dates)}个交易日")
    else:
        existing_df = pd.DataFrame()
        existing_dates = set()
    
    for i, date in enumerate(trade_dates):
        if date in existing_dates:
            continue
        
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(trade_dates)} ({(i+1)/len(trade_dates)*100:.0f}%)")
        
        # 请求（按日查询）
        df = request_with_retry(pro, pro.hm_detail, trade_date=date)
        
        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
        else:
            fail_count += 1
        
        time.sleep(REQUEST_INTERVAL)
    
    if all_data:
        new_df = pd.concat(all_data, ignore_index=True)
        new_df['trade_date'] = new_df['trade_date'].astype(str)
        
        if not existing_df.empty:
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        else:
            final_df = new_df
        
        final_df.to_parquet(output_path, index=False)
        print(f"\n✅ hm_detail 抓取完成:")
        print(f"   新增: {success_count}个交易日")
        print(f"   失败: {fail_count}个交易日")
        print(f"   总计: {len(final_df)}条")
    else:
        print(f"\n⚠️  无新增数据")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='龙虎榜数据单独抓取脚本')
    parser.add_argument('--start', type=str, default='20200101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, default='20260320', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--top-list', action='store_true', help='只抓取龙虎榜每日明细')
    parser.add_argument('--top-inst', action='store_true', help='只抓取机构席位明细')
    parser.add_argument('--hm-detail', action='store_true', help='只抓取游资明细')
    
    args = parser.parse_args()
    
    print("="*60)
    print("龙虎榜数据抓取脚本")
    print("="*60)
    print(f"日期范围: {args.start} ~ {args.end}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("="*60)
    
    # 初始化API（使用源代码中的方式）
    pro = init_tushare_api()
    if pro is None:
        print("❌ 初始化失败")
        sys.exit(1)
    
    # 测试连接
    print("\n测试API连接...")
    try:
        test_df = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240110')
        if test_df is not None and not test_df.empty:
            print(f"✅ API连接正常，返回{len(test_df)}条测试数据")
        else:
            print("⚠️  API返回空")
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        sys.exit(1)
    
    # 获取交易日
    print(f"\n获取交易日列表...")
    trade_dates = get_trade_dates(pro, args.start, args.end)
    if not trade_dates:
        print("❌ 获取交易日失败")
        sys.exit(1)
    print(f"✅ 交易日数量: {len(trade_dates)}")
    
    # 确定抓取内容
    fetch_all = not (args.top_list or args.top_inst or args.hm_detail)
    
    # 执行抓取
    start_time = datetime.now()
    
    if fetch_all or args.top_list:
        fetch_top_list(pro, trade_dates, os.path.join(OUTPUT_DIR, 'top_list.parquet'))
    
    if fetch_all or args.top_inst:
        fetch_top_inst(pro, trade_dates, os.path.join(OUTPUT_DIR, 'top_inst.parquet'))
    
    if fetch_all or args.hm_detail:
        fetch_hm_detail(pro, trade_dates, os.path.join(OUTPUT_DIR, 'hm_detail.parquet'))
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"✅ 全部抓取完成，耗时: {elapsed:.1f}秒")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()