#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==============================================
# 【阶段 1.5：主板筛选配置】集成验证脚本
# ==============================================
# 功能：验证 STOCK_FILTER_CONFIG 已正确集成到 fetch_data_optimized.py
# 验收标准：从实际代码文件读取配置并验证
# ==============================================

import re
import sys
import os

def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ 读取文件失败：{e}")
        return None

def extract_config(content, config_name):
    """从代码中提取配置字典"""
    # 使用正则表达式提取配置
    pattern = rf'{config_name}\s*=\s*\{{([^}}]+)\}}'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(0)
    return None

def verify_allowed_market(content):
    """验证 ALLOWED_MARKET 配置"""
    print("="*80)
    print("【验证 1】ALLOWED_MARKET 配置")
    print("="*80)
    
    # 查找 ALLOWED_MARKET 配置
    pattern = r'ALLOWED_MARKET\s*=\s*\[([^\]]+)\]'
    match = re.search(pattern, content)
    
    if match:
        allowed_market_str = match.group(0)
        print(f"找到配置：{allowed_market_str}")
        
        # 检查是否只包含主板
        if '"主板"' in allowed_market_str or "'主板'" in allowed_market_str:
            print("✅ 包含主板")
            
            # 检查是否排除了其他板块
            has_chi_next = '"创业板"' in allowed_market_str or "'创业板'" in allowed_market_str
            has_star = '"科创板"' in allowed_market_str or "'科创板'" in allowed_market_str
            has_bse = '"北交所"' in allowed_market_str or "'北交所'" in allowed_market_str
            
            if not has_chi_next:
                print("✅ 已排除创业板")
            else:
                print("❌ 未排除创业板")
                return False
            
            if not has_star:
                print("✅ 已排除科创板")
            else:
                print("❌ 未排除科创板")
                return False
            
            if not has_bse:
                print("✅ 已排除北交所")
            else:
                print("❌ 未排除北交所")
                return False
            
            print("✅ ALLOWED_MARKET 配置正确")
            return True
        else:
            print("❌ 未找到主板配置")
            return False
    else:
        print("❌ 未找到 ALLOWED_MARKET 配置")
        return False

def verify_stock_filter_config(content):
    """验证 STOCK_FILTER_CONFIG 配置"""
    print("="*80)
    print("【验证 2】STOCK_FILTER_CONFIG 配置")
    print("="*80)
    
    config = extract_config(content, 'STOCK_FILTER_CONFIG')
    
    if config:
        print("找到 STOCK_FILTER_CONFIG 配置：")
        print("-"*60)
        # 打印配置内容（简化版）
        lines = config.split('\n')
        for line in lines[:15]:  # 只显示前 15 行
            print(line)
        print("-"*60)
        
        # 验证关键字段
        checks = [
            ("'include_main_board': True", "包含主板"),
            ("'include_chi_next': False", "排除创业板"),
            ("'include_star_market': False", "排除科创板"),
            ("'include_bse': False", "排除北交所"),
            ("'exclude_st': True", "排除 ST"),
            ("'exclude_suspend': True", "排除停牌"),
            ("'min_market_cap': 50", "最小市值 50 亿"),
            ("'min_amount': 100000", "最小成交额"),
            ("'min_turnover': 2", "最小换手率"),
        ]
        
        all_passed = True
        for check_str, description in checks:
            if check_str in config:
                print(f"✅ {description}: {check_str}")
            else:
                print(f"❌ {description}: {check_str} (未找到)")
                all_passed = False
        
        if all_passed:
            print("✅ STOCK_FILTER_CONFIG 配置正确")
        else:
            print("⚠️  STOCK_FILTER_CONFIG 配置部分缺失")
        
        return all_passed
    else:
        print("❌ 未找到 STOCK_FILTER_CONFIG 配置")
        return False

def verify_filter_config(content):
    """验证 FILTER_CONFIG 配置"""
    print("="*80)
    print("【验证 3】FILTER_CONFIG 配置")
    print("="*80)
    
    config = extract_config(content, 'FILTER_CONFIG')
    
    if config:
        print("找到 FILTER_CONFIG 配置")
        
        # 验证关键字段（支持单引号和双引号）
        checks = [
            ('"min_amount"', "最小成交额"),
            ('"min_turnover"', "最小换手率"),
            ('"exclude_st": True', "排除 ST"),
            ('"exclude_suspend": True', "排除停牌"),
        ]
        
        all_passed = True
        for check_str, description in checks:
            if check_str in config:
                print(f"✅ {description}: 存在")
            else:
                print(f"❌ {description}: {check_str} (未找到)")
                all_passed = False
        
        if all_passed:
            print("✅ FILTER_CONFIG 配置正确")
        else:
            print("⚠️  FILTER_CONFIG 配置部分缺失")
        
        return all_passed
    else:
        print("❌ 未找到 FILTER_CONFIG 配置")
        return False

def verify_market_map(content):
    """验证 MARKET_MAP 配置"""
    print("="*80)
    print("【验证 4】MARKET_MAP 板块映射")
    print("="*80)
    
    config = extract_config(content, 'MARKET_MAP')
    
    if config:
        print("找到 MARKET_MAP 配置")
        
        # 验证关键板块
        checks = [
            ('"主板"', "主板"),
            ('"创业板"', "创业板"),
            ('"科创板"', "科创板"),
            ('"北交所"', "北交所"),
        ]
        
        all_passed = True
        for check_str, description in checks:
            if check_str in config:
                print(f"✅ {description}映射：存在")
            else:
                print(f"❌ {description}映射：{check_str} (未找到)")
                all_passed = False
        
        if all_passed:
            print("✅ MARKET_MAP 配置正确")
        else:
            print("⚠️  MARKET_MAP 配置部分缺失")
        
        return all_passed
    else:
        print("❌ 未找到 MARKET_MAP 配置")
        return False

def main():
    """主验证函数"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "【阶段 1.5：主板筛选配置集成验证】" + " "*18 + "║")
    print("╚" + "="*78 + "╝")
    print("\n")
    
    # 读取代码文件
    filepath = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'fetch_data_optimized.py'
    )
    
    print(f"验证文件：{filepath}")
    content = read_file_content(filepath)
    
    if not content:
        print("❌ 无法读取文件，验证失败")
        return 1
    
    # 执行验证
    v1 = verify_allowed_market(content)
    v2 = verify_stock_filter_config(content)
    v3 = verify_filter_config(content)
    v4 = verify_market_map(content)
    
    # 总结
    print("\n")
    print("="*80)
    print("【验证总结】")
    print("="*80)
    print(f"ALLOWED_MARKET 配置：{'✅ 通过' if v1 else '❌ 失败'}")
    print(f"STOCK_FILTER_CONFIG 配置：{'✅ 通过' if v2 else '❌ 失败'}")
    print(f"FILTER_CONFIG 配置：{'✅ 通过' if v3 else '❌ 失败'}")
    print(f"MARKET_MAP 配置：{'✅ 通过' if v4 else '❌ 失败'}")
    print()
    
    all_passed = v1 and v2 and v3 and v4
    
    print("验收标准检查：")
    print(f"  1. 配置集成到代码：{'✅ 通过' if all_passed else '❌ 失败'}")
    print(f"  2. 测试结果只有主板股票：需运行功能测试验证")
    print("="*80)
    print()
    
    if all_passed:
        print("🎉 所有配置验证通过！主板筛选配置已正确集成到代码中。")
        return 0
    else:
        print("❌ 部分配置验证失败，请检查代码。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
