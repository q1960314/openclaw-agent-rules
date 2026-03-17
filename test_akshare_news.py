#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AkShare 新闻接口测试脚本
测试 4 个新闻源：
1. ak.stock_news_em() - 东方财富个股新闻
2. ak.news_economic_baidu() - 百度经济日历
3. ak.stock_news_main_cx() - 财新数据
4. ak.news_cctv() - 新闻联播
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import akshare as ak
    import pandas as pd
    from datetime import datetime
    AKSHARE_AVAILABLE = True
    print("✅ AkShare 库已加载")
except ImportError as e:
    print(f"❌ AkShare 未安装：{e}")
    print("请运行：pip install akshare")
    sys.exit(1)

def test_stock_news_em():
    """测试东方财富个股新闻"""
    print("\n" + "="*80)
    print("【测试 1】东方财富个股新闻 - ak.stock_news_em()")
    print("="*80)
    try:
        # 测试平安银行
        df = ak.stock_news_em(symbol="000001")
        if df is not None and not df.empty:
            print(f"✅ 抓取成功，共 {len(df)} 条新闻")
            print(f"列名：{list(df.columns)}")
            print(f"\n前 3 条新闻：")
            print(df.head(3).to_string())
            return True
        else:
            print("⚠️  无数据返回")
            return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def test_news_economic_baidu():
    """测试百度经济日历"""
    print("\n" + "="*80)
    print("【测试 2】百度经济日历 - ak.news_economic_baidu()")
    print("="*80)
    try:
        # 测试最近 7 天
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now()).strftime("%Y%m%d")
        df = ak.news_economic_baidu(start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            print(f"✅ 抓取成功，共 {len(df)} 条新闻")
            print(f"列名：{list(df.columns)}")
            print(f"\n前 3 条新闻：")
            print(df.head(3).to_string())
            return True
        else:
            print("⚠️  无数据返回")
            return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def test_stock_news_main_cx():
    """测试财新数据"""
    print("\n" + "="*80)
    print("【测试 3】财新数据 - ak.stock_news_main_cx()")
    print("="*80)
    try:
        df = ak.stock_news_main_cx()
        if df is not None and not df.empty:
            print(f"✅ 抓取成功，共 {len(df)} 条新闻")
            print(f"列名：{list(df.columns)}")
            print(f"\n前 3 条新闻：")
            print(df.head(3).to_string())
            return True
        else:
            print("⚠️  无数据返回")
            return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def test_news_cctv():
    """测试新闻联播"""
    print("\n" + "="*80)
    print("【测试 4】新闻联播 - ak.news_cctv()")
    print("="*80)
    try:
        df = ak.news_cctv()
        if df is not None and not df.empty:
            print(f"✅ 抓取成功，共 {len(df)} 条新闻")
            print(f"列名：{list(df.columns)}")
            print(f"\n前 3 条新闻：")
            print(df.head(3).to_string())
            return True
        else:
            print("⚠️  无数据返回")
            return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def main():
    print("="*80)
    print("AkShare 新闻接口测试脚本")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = {
        "东方财富个股新闻": test_stock_news_em(),
        "百度经济日历": test_news_economic_baidu(),
        "财新数据": test_stock_news_main_cx(),
        "新闻联播": test_news_cctv()
    }
    
    print("\n" + "="*80)
    print("【测试结果汇总】")
    print("="*80)
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\n总计：{passed}/{total} 通过")
    print("="*80)
    
    if passed >= 3:
        print("✅ 测试通过，AkShare 新闻接口可正常使用")
        return 0
    else:
        print("⚠️  部分测试失败，请检查网络连接或 AkShare 版本")
        return 1

if __name__ == "__main__":
    sys.exit(main())
