#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 1 - 运行模式配置验证测试
验证 4 种运行模式的配置和逻辑是否正确
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ==================== 测试配置 ====================
TEST_MODES = [
    "全量抓取",
    "增量抓取",
    "仅回测",
    "每日选股"
]

# ==================== 测试结果记录 ====================
test_results = []

def test_mode_config(mode):
    """测试单个模式的配置"""
    print(f"\n{'='*80}")
    print(f"测试模式：{mode}")
    print(f"{'='*80}")
    
    result = {
        'mode': mode,
        'config_valid': False,
        'run_by_mode_valid': False,
        'issues': [],
        'suggestions': []
    }
    
    # 1. 检查 fetch_data_optimized.py 中的配置
    config_path = os.path.join(BASE_DIR, 'fetch_data_optimized.py')
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查 AUTO_RUN_MODE 配置
    if f'AUTO_RUN_MODE = "{mode}"' in content:
        print(f"✅ AUTO_RUN_MODE 配置正确：{mode}")
    else:
        print(f"⚠️  AUTO_RUN_MODE 当前不是 {mode}（这是正常的，测试时不需要修改）")
    
    # 检查模式专属配置
    if mode == "全量抓取":
        if 'FETCH_CONFIG' in content and "'max_workers': 10" in content:
            print(f"✅ 全量抓取模式配置存在（max_workers=10，保守配置）")
            result['config_valid'] = True
        else:
            print(f"❌ 全量抓取模式配置缺失或不完整")
            result['issues'].append("全量抓取配置缺失")
    
    elif mode == "增量抓取":
        if "'max_workers': 15" in content and "'最新交易日'" in content:
            print(f"✅ 增量抓取模式配置存在（max_workers=15，激进配置）")
            result['config_valid'] = True
        else:
            print(f"❌ 增量抓取模式配置缺失或不完整")
            result['issues'].append("增量抓取配置缺失")
    
    elif mode == "仅回测":
        if 'validate_local_data()' in content:
            print(f"✅ 仅回测模式逻辑存在（会验证本地数据）")
            result['config_valid'] = True
        else:
            print(f"❌ 仅回测模式逻辑缺失")
            result['issues'].append("仅回测逻辑缺失")
    
    elif mode == "每日选股":
        if 'DailyStockPicker' in content and 'pick_stocks' in content:
            print(f"✅ 每日选股模式逻辑存在（使用 DailyStockPicker）")
            result['config_valid'] = True
        else:
            print(f"❌ 每日选股模式逻辑缺失")
            result['issues'].append("每日选股逻辑缺失")
    
    # 2. 检查 run_by_mode() 函数
    if f'effective_mode == "{mode}"' in content:
        print(f"✅ run_by_mode() 函数包含 {mode} 处理逻辑")
        result['run_by_mode_valid'] = True
    else:
        print(f"❌ run_by_mode() 函数缺少 {mode} 处理逻辑")
        result['issues'].append(f"run_by_mode() 缺少 {mode} 逻辑")
    
    # 3. 检查本地数据（仅回测模式需要）
    if mode == "仅回测":
        data_dir = os.path.join(BASE_DIR, 'data')
        all_stocks_dir = os.path.join(BASE_DIR, 'data', 'all_stocks')
        
        if os.path.exists(data_dir):
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
            print(f"✅ 本地数据目录存在：{len(csv_files)} 个 CSV 文件")
            result['suggestions'].append(f"本地已有 {len(csv_files)} 个 CSV 文件，可以执行回测")
        else:
            print(f"⚠️  本地数据目录不存在，需要先执行全量抓取")
            result['issues'].append("本地数据目录不存在")
        
        if os.path.exists(all_stocks_dir):
            stock_dirs = [d for d in os.listdir(all_stocks_dir) if os.path.isdir(os.path.join(all_stocks_dir, d))]
            print(f"✅ 个股数据目录存在：{len(stock_dirs)} 只股票")
            result['suggestions'].append(f"本地已有 {len(stock_dirs)} 只股票数据")
        else:
            print(f"⚠️  个股数据目录不存在")
    
    # 4. 检查后端服务配置（所有模式都需要）
    if 'SERVER_HOST' in content and 'SERVER_PORT' in content:
        print(f"✅ 后端服务配置存在")
    else:
        print(f"❌ 后端服务配置缺失")
        result['issues'].append("后端服务配置缺失")
    
    test_results.append(result)
    return result

def print_summary():
    """打印测试总结"""
    print(f"\n{'='*80}")
    print(f"阶段 1 - 运行模式配置验证总结")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    total = len(test_results)
    config_valid = sum(1 for r in test_results if r['config_valid'])
    run_valid = sum(1 for r in test_results if r['run_by_mode_valid'])
    total_issues = sum(len(r['issues']) for r in test_results)
    
    print(f"\n【总体统计】")
    print(f"总测试模式数：{total}")
    print(f"配置有效：{config_valid}/{total}")
    print(f"run_by_mode() 逻辑有效：{run_valid}/{total}")
    print(f"发现问题：{total_issues} 个")
    
    print(f"\n【按模式统计】")
    for result in test_results:
        status = "✅" if (result['config_valid'] and result['run_by_mode_valid']) else "❌"
        issues = f" ({len(result['issues'])} 个问题)" if result['issues'] else ""
        print(f"{status} {result['mode']}{issues}")
    
    # 详细问题
    if total_issues > 0:
        print(f"\n【问题清单】")
        for result in test_results:
            if result['issues']:
                print(f"\n{result['mode']}:")
                for issue in result['issues']:
                    print(f"  - {issue}")
    
    # 建议
    print(f"\n【优化建议】")
    for result in test_results:
        if result['suggestions']:
            print(f"\n{result['mode']}:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")

def save_results():
    """保存测试结果"""
    results_path = os.path.join(BASE_DIR, 'data', 'test_stage_1_run_modes_result.json')
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试结果已保存：{results_path}")

def check_local_data():
    """检查本地数据情况"""
    print(f"\n{'='*80}")
    print(f"本地数据检查")
    print(f"{'='*80}")
    
    data_dir = os.path.join(BASE_DIR, 'data')
    all_stocks_dir = os.path.join(BASE_DIR, 'data', 'all_stocks')
    
    # 检查 data 目录
    if os.path.exists(data_dir):
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        print(f"\n【data 目录】")
        print(f"CSV 文件数：{len(csv_files)}")
        
        # 显示主要文件
        key_files = [
            'stock_basic.csv',
            'stk_limit.csv',
            'kpl_list.csv',
            'limit_list_d.csv',
            'ths_index.csv'
        ]
        for key_file in key_files:
            file_path = os.path.join(data_dir, key_file)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {key_file}: {size/1024:.1f} KB")
            else:
                print(f"  ❌ {key_file}: 不存在")
    else:
        print(f"❌ data 目录不存在")
    
    # 检查 all_stocks 目录
    if os.path.exists(all_stocks_dir):
        stock_dirs = [d for d in os.listdir(all_stocks_dir) if os.path.isdir(os.path.join(all_stocks_dir, d))]
        print(f"\n【all_stocks 目录】")
        print(f"股票数：{len(stock_dirs)}")
        
        # 检查示例股票
        if stock_dirs:
            sample_stock = stock_dirs[0]
            stock_path = os.path.join(all_stocks_dir, sample_stock)
            stock_files = os.listdir(stock_path)
            print(f"示例股票 {sample_stock}:")
            for f in stock_files[:5]:
                file_path = os.path.join(stock_path, f)
                size = os.path.getsize(file_path)
                print(f"  - {f}: {size/1024:.1f} KB")
    else:
        print(f"❌ all_stocks 目录不存在")

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print(f"阶段 1 - 运行模式配置验证测试")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n【测试模式】")
    for mode in TEST_MODES:
        print(f"  - {mode}")
    
    # 逐个测试模式
    for mode in TEST_MODES:
        test_mode_config(mode)
    
    # 检查本地数据
    check_local_data()
    
    # 打印总结
    print_summary()
    
    # 保存结果
    save_results()
    
    return test_results

if __name__ == '__main__':
    results = main()
    print(f"\n✅ 所有测试完成！")
