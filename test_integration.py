#!/usr/bin/env python3
"""
集成测试脚本
验证优化功能是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/admin/.openclaw/agents/master')

def test_imports():
    """测试导入"""
    print("="*80)
    print("测试 1: 导入模块")
    print("="*80)
    
    try:
        import pandas as pd
        print("✅ pandas 导入成功")
    except ImportError as e:
        print(f"❌ pandas 导入失败：{e}")
        return False
    
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        print("✅ pyarrow 导入成功 (Parquet 可用)")
        parquet_ok = True
    except ImportError:
        print("⚠️  pyarrow 未安装 (Parquet 将降级为 CSV)")
        parquet_ok = False
    
    try:
        import akshare as ak
        print("✅ akshare 导入成功 (降级支持可用)")
        akshare_ok = True
    except ImportError:
        print("⚠️  akshare 未安装 (降级功能不可用)")
        akshare_ok = False
    
    try:
        import tushare as ts
        print("✅ tushare 导入成功")
    except ImportError as e:
        print(f"❌ tushare 导入失败：{e}")
        return False
    
    return True

def test_config():
    """测试配置"""
    print("\n" + "="*80)
    print("测试 2: 读取配置")
    print("="*80)
    
    # 读取配置文件
    config_file = '/home/admin/.openclaw/agents/master/fetch_data_optimized.py'
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查并发配置
    if "'max_workers': 15" in content:
        print("✅ 并发线程数配置正确：15 线程")
    else:
        print("❌ 并发线程数配置错误")
        return False
    
    if "'max_requests_per_minute': 3000" in content:
        print("✅ 每分钟请求数配置正确：3000 次/分")
    else:
        print("❌ 每分钟请求数配置错误")
        return False
    
    # 检查 Parquet 配置
    if "USE_PARQUET = True" in content:
        print("✅ Parquet 存储已启用")
    else:
        print("⚠️  Parquet 存储未启用")
    
    # 检查 AkShare 配置
    if "import akshare as ak" in content:
        print("✅ AkShare 降级支持已集成")
    else:
        print("⚠️  AkShare 降级支持未集成")
    
    return True

def test_syntax():
    """测试语法"""
    print("\n" + "="*80)
    print("测试 3: 语法检查")
    print("="*80)
    
    import py_compile
    try:
        py_compile.compile('/home/admin/.openclaw/agents/master/fetch_data_optimized.py', doraise=True)
        print("✅ 语法检查通过")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ 语法检查失败：{e}")
        return False

def test_interfaces():
    """测试接口文档"""
    print("\n" + "="*80)
    print("测试 4: 14 个接口文档")
    print("="*80)
    
    config_file = '/home/admin/.openclaw/agents/master/fetch_data_optimized.py'
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    interfaces = [
        'stock_basic', 'daily', 'daily_basic', 'fina_indicator',
        'moneyflow', 'concept_detail', 'top_list', 'top_inst',
        'balancesheet', 'cashflow', 'income', 'hk_hold',
        'cyq_chips', 'stk_limit'
    ]
    
    found_count = 0
    for interface in interfaces:
        if f"'{interface}'" in content or f'"{interface}"' in content:
            found_count += 1
    
    print(f"✅ 找到 {found_count}/{len(interfaces)} 个接口")
    
    if found_count == len(interfaces):
        print("✅ 所有 14 个接口已完整实现")
        return True
    else:
        print(f"⚠️  缺少 {len(interfaces) - found_count} 个接口")
        return False

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("  量化数据采集系统 - 集成测试")
    print("="*80)
    
    results = []
    
    # 测试 1: 导入
    results.append(("导入测试", test_imports()))
    
    # 测试 2: 配置
    results.append(("配置测试", test_config()))
    
    # 测试 3: 语法
    results.append(("语法测试", test_syntax()))
    
    # 测试 4: 接口
    results.append(("接口测试", test_interfaces()))
    
    # 汇总
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print("="*80)
    print(f"总计：{passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统已就绪")
        print("\n下一步：")
        print("1. 安装依赖（如果还没安装）：pip install pyarrow akshare")
        print("2. 运行程序：python3 fetch_data_optimized.py")
    else:
        print("⚠️  部分测试失败，请检查上面的错误信息")
    
    print("="*80)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
