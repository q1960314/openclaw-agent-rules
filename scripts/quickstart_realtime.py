#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==============================================
# 【快速开始】实时数据源使用示例
# ==============================================
# 功能：演示如何使用实时数据源模块
# ==============================================

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_sources import (
    get_realtime_data,
    get_realtime_batch,
    get_industry_board_realtime,
    get_hot_rank,
    get_moneyflow,
    RealtimeDataManager,
)


def demo_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("【基础使用示例】")
    print("=" * 60)
    
    # 获取单只股票实时行情
    print("\n1️⃣ 获取平安银行实时行情...")
    data = get_realtime_data("000001")
    if data:
        print(f"   代码：{data['ts_code']}")
        print(f"   名称：{data.get('name', 'N/A')}")
        print(f"   价格：¥{data.get('price', 0):.2f}")
        print(f"   涨跌幅：{data.get('pct_change', 0):.2f}%")
        print(f"   数据源：{data.get('source', 'unknown')}")
    else:
        print("   ❌ 获取失败")
    
    # 获取多只股票
    print("\n2️⃣ 批量获取股票行情...")
    batch = get_realtime_batch(["000001", "600519", "300750"])
    for code, data in batch.items():
        print(f"   {code}: ¥{data.get('price', 0):.2f} ({data.get('pct_change', 0):.2f}%)")


def demo_industry_board():
    """行业板块示例"""
    print("\n" + "=" * 60)
    print("【行业板块示例】")
    print("=" * 60)
    
    print("\n📊 获取行业板块实时行情...")
    df = get_industry_board_realtime()
    
    if df is not None and not df.empty:
        print(f"   共 {len(df)} 个板块")
        print("\n   TOP 5 涨幅榜:")
        top5 = df.nlargest(5, 'pct_change')
        for _, row in top5.iterrows():
            board_name = row.get('board_name', row.get('name', 'N/A'))
            pct = row.get('pct_change', 0)
            print(f"   - {board_name}: {pct:.2f}%")
    else:
        print("   ❌ 获取失败")


def demo_hot_rank():
    """热榜示例"""
    print("\n" + "=" * 60)
    print("【股票热榜示例】")
    print("=" * 60)
    
    print("\n🔥 获取股票人气热榜...")
    df = get_hot_rank()
    
    if df is not None and not df.empty:
        print(f"   共 {len(df)} 只股票")
        print("\n   TOP 10:")
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            name = row.get('name', 'N/A')
            code = row.get('ts_code', 'N/A')
            print(f"   {i}. {code} {name}")
    else:
        print("   ❌ 获取失败")


def demo_moneyflow():
    """资金流向示例"""
    print("\n" + "=" * 60)
    print("【资金流向示例】")
    print("=" * 60)
    
    print("\n💰 获取平安银行资金流向...")
    flow = get_moneyflow("000001")
    
    if flow:
        print(f"   主力净流入：{flow.get('main_net_inflow', 0):.2f}万元")
        print(f"   超大单：{flow.get('super_large_net_inflow', 0):.2f}万元")
        print(f"   大单：{flow.get('large_net_inflow', 0):.2f}万元")
        print(f"   中单：{flow.get('medium_net_inflow', 0):.2f}万元")
        print(f"   小单：{flow.get('small_net_inflow', 0):.2f}万元")
    else:
        print("   ❌ 获取失败")


def demo_manager():
    """管理器高级用法"""
    print("\n" + "=" * 60)
    print("【管理器高级用法】")
    print("=" * 60)
    
    # 自定义配置
    config = {
        'REALTIME_PRIORITY': ['akshare', 'sina', 'eastmoney'],  # 自定义优先级
        'REALTIME_CACHE_TIMEOUT': 60,  # 缓存 60 秒
    }
    
    print("\n⚙️  使用自定义配置...")
    manager = RealtimeDataManager(config)
    
    # 获取数据
    data = manager.get_realtime_data("000001")
    if data:
        print(f"   ✅ {data['ts_code']}: ¥{data.get('price', 0):.2f}")
        print(f"   数据源：{data.get('source', 'unknown')}")
    
    # 查看统计
    stats = manager.get_stats()
    print(f"\n📈 统计信息:")
    print(f"   总请求数：{stats['total_requests']}")
    print(f"   成功分布：{stats['success_by_source']}")
    print(f"   降级次数：{stats['fallback_count']}")
    
    # 断开连接
    manager.disconnect_all()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("【实时数据源快速开始】")
    print("=" * 60)
    print("优先级：Tushare → AkShare → 新浪 → 东财")
    print("=" * 60)
    
    try:
        # 基础用法
        demo_basic_usage()
        
        # 行业板块
        demo_industry_board()
        
        # 热榜
        demo_hot_rank()
        
        # 资金流向
        demo_moneyflow()
        
        # 管理器高级用法
        demo_manager()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
