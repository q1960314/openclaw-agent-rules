#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充数据抓取脚本 - 专门抓取剩余缺失的数据
- concept_detail: 5263 只股票
- stk_limit: 1495 天（2020-01-01 至 2026-03-09）
- top_list/top_inst: 1497 天
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import tushare as ts

# 配置
DATA_DIR = "/home/admin/.openclaw/agents/master/data_all_stocks"
MARKET_DATA_DIR = "/home/admin/.openclaw/agents/master/data"
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
START_DATE = "20200101"
END_DATE = "20260311"

# 初始化 Tushare（使用私有 API 服务器）
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()
pro._DataApi__token = TUSHARE_TOKEN
pro._DataApi__http_url = TUSHARE_API_URL

def get_stock_list():
    """获取所有股票代码"""
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
    return df['ts_code'].tolist()

def fetch_concept_detail(ts_code):
    """抓取单只股票的概念板块数据"""
    try:
        df = pro.concept_detail(ts_code=ts_code)
        if df is not None and not df.empty:
            filepath = os.path.join(DATA_DIR, ts_code, 'concept_detail.parquet')
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df.to_parquet(filepath, index=False)
            return ts_code, len(df), True
        return ts_code, 0, True
    except Exception as e:
        print(f"Error fetching concept for {ts_code}: {e}")
        return ts_code, 0, False

def fetch_stk_limit_batch():
    """批量抓取涨跌停数据"""
    print("开始抓取涨跌停数据...")
    all_data = []
    
    # 按日期循环抓取
    start = datetime.strptime(START_DATE, "%Y%m%d")
    end = datetime.strptime(END_DATE, "%Y%m%d")
    current = start
    
    total_days = (end - start).days + 1
    fetched_days = 0
    
    while current <= end:
        trade_date = current.strftime("%Y%m%d")
        try:
            df = pro.stk_limit(trade_date=trade_date)
            if df is not None and not df.empty:
                df['trade_date'] = trade_date
                all_data.append(df)
                fetched_days += 1
                if fetched_days % 100 == 0:
                    print(f"  已抓取 {fetched_days}/{total_days} 天")
        except Exception as e:
            print(f"Error fetching stk_limit for {trade_date}: {e}")
        
        current += timedelta(days=1)
        time.sleep(0.1)  # 限流
    
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        filepath = os.path.join(MARKET_DATA_DIR, 'stk_limit_full.parquet')
        df_all.to_parquet(filepath, index=False)
        print(f"✅ 涨跌停数据抓取完成：{len(df_all)} 条记录，保存至 {filepath}")
    else:
        print("⚠️  涨跌停数据为空")

def fetch_top_list_batch():
    """批量抓取龙虎榜数据"""
    print("开始抓取龙虎榜数据...")
    all_data = []
    all_inst_data = []
    
    start = datetime.strptime(START_DATE, "%Y%m%d")
    end = datetime.strptime(END_DATE, "%Y%m%d")
    current = start
    
    total_days = (end - start).days + 1
    fetched_days = 0
    
    while current <= end:
        trade_date = current.strftime("%Y%m%d")
        try:
            # 龙虎榜每日明细
            df = pro.top_list(trade_date=trade_date)
            if df is not None and not df.empty:
                df['trade_date'] = trade_date
                all_data.append(df)
            
            # 龙虎榜机构席位
            df_inst = pro.top_inst(trade_date=trade_date)
            if df_inst is not None and not df_inst.empty:
                df_inst['trade_date'] = trade_date
                all_inst_data.append(df_inst)
            
            fetched_days += 1
            if fetched_days % 100 == 0:
                print(f"  已抓取 {fetched_days}/{total_days} 天")
        except Exception as e:
            print(f"Error fetching top_list for {trade_date}: {e}")
        
        current += timedelta(days=1)
        time.sleep(0.15)  # 限流
    
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        filepath = os.path.join(MARKET_DATA_DIR, 'top_list_full.parquet')
        df_all.to_parquet(filepath, index=False)
        print(f"✅ 龙虎榜数据抓取完成：{len(df_all)} 条记录")
    
    if all_inst_data:
        df_inst_all = pd.concat(all_inst_data, ignore_index=True)
        filepath = os.path.join(MARKET_DATA_DIR, 'top_inst_full.parquet')
        df_inst_all.to_parquet(filepath, index=False)
        print(f"✅ 龙虎榜机构席位数据抓取完成：{len(df_inst_all)} 条记录")

def main():
    print("="*80)
    print("  补充数据抓取脚本")
    print("="*80)
    
    # 1. 抓取 concept_detail
    print("\n【1/3】抓取概念板块数据...")
    stocks = get_stock_list()
    existing = [d for d in os.listdir(DATA_DIR) if os.path.exists(os.path.join(DATA_DIR, d, 'concept_detail.parquet'))]
    missing = [s for s in stocks if s not in existing]
    
    print(f"  总股票数：{len(stocks)}")
    print(f"  已有概念数据：{len(existing)}")
    print(f"  需补充：{len(missing)}")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_concept_detail, ts_code): ts_code for ts_code in missing}
        for i, future in enumerate(as_completed(futures)):
            ts_code, count, success = future.result()
            if success:
                success_count += 1
            if (i + 1) % 500 == 0:
                print(f"  进度：{i+1}/{len(missing)}，成功：{success_count}")
            time.sleep(0.05)  # 限流
    
    print(f"✅ 概念板块数据抓取完成：{success_count}/{len(missing)}")
    
    # 2. 抓取 stk_limit
    print("\n【2/3】抓取涨跌停数据...")
    fetch_stk_limit_batch()
    
    # 3. 抓取 top_list/top_inst
    print("\n【3/3】抓取龙虎榜数据...")
    fetch_top_list_batch()
    
    print("\n" + "="*80)
    print("✅ 所有补充数据抓取完成！")
    print("="*80)

if __name__ == '__main__':
    main()
