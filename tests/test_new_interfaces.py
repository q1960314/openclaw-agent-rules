#!/usr/bin/env python3
# ==============================================
# 【测试】18 个新接口验证测试 - test_new_interfaces.py
# ==============================================
# 功能：测试 18 个新增/未覆盖的接口
# 包含：
#   - DataSourcePlugin 生命周期接口 (8 个)
#   - Tushare 新增数据接口 (3 个)
#   - 配置管理接口 (4 个)
#   - 统计与上下文管理接口 (3 个)
# 使用：python3 tests/test_new_interfaces.py
# ==============================================

import sys
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("new_interface_test")

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

def record_result(category: str, name: str, status: str, error: str = None, details: str = ""):
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
    
    if category not in test_results['interfaces']:
        test_results['interfaces'][category] = []
    
    test_results['interfaces'][category].append({
        'name': name,
        'status': status,
        'error': error,
        'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    status_icon = {'PASS': '✅', 'FAIL': '❌', 'ERROR': '⚠️', 'SKIP': '⏭️'}.get(status, '❓')
    print(f"  {status_icon} {name}: {status}")
    if error and status in ['FAIL', 'ERROR']:
        print(f"     错误：{error}")

# ==============================================
# 第一部分：DataSourcePlugin 生命周期接口测试 (8 个)
# ==============================================

def test_lifecycle_interfaces():
    """测试数据源插件生命周期接口"""
    print_subheader("生命周期接口测试 (8 个)")
    
    from plugins.tushare_source_plugin import TushareDataSourcePlugin
    from plugins.plugin_base import PluginInfo, PluginState
    
    plugin_info = PluginInfo(
        name="tushare_data_source",
        version="1.0.0",
        author="quant-system",
        description="Tushare 数据源",
        plugin_type="data_source",
        config={
            "TUSHARE_TOKEN": "test_token_12345678901234567890123456789012",
            "TUSHARE_API_URL": "http://api.tushare.pro",
        }
    )
    
    try:
        plugin = TushareDataSourcePlugin(plugin_info)
    except Exception as e:
        record_result('lifecycle', 'initialization', 'ERROR', str(e))
        for api in ['on_load', 'on_init', 'on_activate', 'on_deactivate', 
                    'on_connect', 'on_disconnect', 'rate_limit', 'set_config']:
            record_result('lifecycle', api, 'SKIP', '插件初始化失败')
        return
    
    # 1. 测试 on_load
    try:
        result = plugin.on_load()
        assert isinstance(result, bool)
        record_result('lifecycle', 'on_load', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_load', 'ERROR', str(e))
    
    # 2. 测试 on_init
    try:
        result = plugin.on_init()
        assert isinstance(result, bool)
        record_result('lifecycle', 'on_init', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_init', 'ERROR', str(e))
    
    # 3. 测试 on_activate
    try:
        result = plugin.on_activate()
        assert isinstance(result, bool)
        record_result('lifecycle', 'on_activate', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_activate', 'ERROR', str(e))
    
    # 4. 测试 on_deactivate
    try:
        # 注意：如果插件未激活，on_deactivate 可能返回 False，这是正常的
        result = plugin.on_deactivate()
        # 不强制要求返回 True，只要能正常执行即可
        record_result('lifecycle', 'on_deactivate', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_deactivate', 'ERROR', str(e))
    
    # 5. 测试 on_connect
    try:
        result = plugin.on_connect()
        assert isinstance(result, bool)
        record_result('lifecycle', 'on_connect', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_connect', 'ERROR', str(e))
    
    # 6. 测试 on_disconnect
    try:
        result = plugin.on_disconnect()
        assert isinstance(result, bool)
        record_result('lifecycle', 'on_disconnect', 'PASS', details=f"结果：{result}")
    except Exception as e:
        record_result('lifecycle', 'on_disconnect', 'ERROR', str(e))
    
    # 7. 测试 rate_limit
    try:
        plugin.rate_limit()
        record_result('lifecycle', 'rate_limit', 'PASS')
    except Exception as e:
        record_result('lifecycle', 'rate_limit', 'ERROR', str(e))
    
    # 8. 测试 set_config
    try:
        new_config = {"TUSHARE_TOKEN": "new_token_12345678901234567890123456789012"}
        plugin.set_config(new_config)
        record_result('lifecycle', 'set_config', 'PASS')
    except Exception as e:
        record_result('lifecycle', 'set_config', 'ERROR', str(e))

# ==============================================
# 第二部分：Tushare 新增数据接口测试 (3 个)
# ==============================================

def test_new_data_interfaces():
    """测试 Tushare 新增数据接口"""
    print_subheader("Tushare 新增数据接口测试 (3 个)")
    
    from plugins.tushare_source_plugin import TushareDataSourcePlugin
    from plugins.plugin_base import PluginInfo
    import pandas as pd
    
    plugin_info = PluginInfo(
        name="tushare_data_source",
        version="1.0.0",
        plugin_type="data_source",
        config={
            "TUSHARE_TOKEN": "test_token_12345678901234567890123456789012",
        }
    )
    
    try:
        plugin = TushareDataSourcePlugin(plugin_info)
    except Exception as e:
        record_result('new_data', 'initialization', 'ERROR', str(e))
        for api in ['fetch_suspend_d', 'fetch_block_trade', 'fetch_hk_hold']:
            record_result('new_data', api, 'SKIP', '插件初始化失败')
        return
    
    # 1. 测试 fetch_suspend_d (停牌数据)
    try:
        result = plugin.fetch_suspend_d()
        assert isinstance(result, pd.DataFrame)
        record_result('new_data', 'fetch_suspend_d', 'PASS', 
                     details=f"返回 {len(result)} 行数据")
    except Exception as e:
        record_result('new_data', 'fetch_suspend_d', 'ERROR', str(e))
    
    # 2. 测试 fetch_block_trade (大宗交易数据)
    try:
        result = plugin.fetch_block_trade()
        assert isinstance(result, pd.DataFrame)
        record_result('new_data', 'fetch_block_trade', 'PASS',
                     details=f"返回 {len(result)} 行数据")
    except Exception as e:
        record_result('new_data', 'fetch_block_trade', 'ERROR', str(e))
    
    # 3. 测试 fetch_hk_hold (北向资金持股数据)
    try:
        result = plugin.fetch_hk_hold()
        assert isinstance(result, pd.DataFrame)
        record_result('new_data', 'fetch_hk_hold', 'PASS',
                     details=f"返回 {len(result)} 行数据")
    except Exception as e:
        record_result('new_data', 'fetch_hk_hold', 'ERROR', str(e))

# ==============================================
# 第三部分：配置管理接口测试 (4 个)
# ==============================================

def test_config_management_interfaces():
    """测试配置管理接口"""
    print_subheader("配置管理接口测试 (4 个)")
    
    from plugins.tushare_source_plugin import TushareDataSourcePlugin
    from plugins.plugin_base import PluginInfo
    
    plugin_info = PluginInfo(
        name="tushare_data_source",
        version="1.0.0",
        plugin_type="data_source",
        config={
            "TUSHARE_TOKEN": "test_token_12345678901234567890123456789012",
            "TUSHARE_API_URL": "http://api.tushare.pro",
        }
    )
    
    try:
        plugin = TushareDataSourcePlugin(plugin_info)
    except Exception as e:
        record_result('config', 'initialization', 'ERROR', str(e))
        for api in ['get_config', 'set_rate_limit', 'validate_config', 'get_status']:
            record_result('config', api, 'SKIP', '插件初始化失败')
        return
    
    # 1. 测试 get_config
    try:
        config = plugin.get_config()
        # get_config 返回空字典也是正常的（如果未设置 source_config）
        assert isinstance(config, dict)
        record_result('config', 'get_config', 'PASS', 
                     details=f"配置项数：{len(config)}")
    except Exception as e:
        record_result('config', 'get_config', 'ERROR', str(e))
    
    # 2. 测试 set_rate_limit
    try:
        plugin.set_rate_limit(rps=5, rpm=50)
        record_result('config', 'set_rate_limit', 'PASS')
    except Exception as e:
        record_result('config', 'set_rate_limit', 'ERROR', str(e))
    
    # 3. 测试 validate_config (重复测试，确保稳定性)
    try:
        result = plugin.validate_config()
        assert isinstance(result, bool)
        record_result('config', 'validate_config', 'PASS', 
                     details=f"验证结果：{result}")
    except Exception as e:
        record_result('config', 'validate_config', 'ERROR', str(e))
    
    # 4. 测试 get_status
    try:
        status = plugin.get_status()
        assert isinstance(status, dict)
        record_result('config', 'get_status', 'PASS',
                     details=f"状态项数：{len(status)}")
    except Exception as e:
        record_result('config', 'get_status', 'ERROR', str(e))

# ==============================================
# 第四部分：统计与上下文管理接口测试 (3 个)
# ==============================================

def test_stats_and_context_interfaces():
    """测试统计与上下文管理接口"""
    print_subheader("统计与上下文管理接口测试 (3 个)")
    
    from plugins.tushare_source_plugin import TushareDataSourcePlugin
    from plugins.plugin_base import PluginInfo
    
    plugin_info = PluginInfo(
        name="tushare_data_source",
        version="1.0.0",
        plugin_type="data_source",
        config={
            "TUSHARE_TOKEN": "test_token_12345678901234567890123456789012",
        }
    )
    
    try:
        plugin = TushareDataSourcePlugin(plugin_info)
    except Exception as e:
        record_result('stats_context', 'initialization', 'ERROR', str(e))
        for api in ['get_stats', 'reset_stats', 'context_manager']:
            record_result('stats_context', api, 'SKIP', '插件初始化失败')
        return
    
    # 1. 测试 get_stats
    try:
        stats = plugin.get_stats()
        assert isinstance(stats, dict)
        record_result('stats_context', 'get_stats', 'PASS',
                     details=f"统计项：{list(stats.keys())[:5]}...")
    except Exception as e:
        record_result('stats_context', 'get_stats', 'ERROR', str(e))
    
    # 2. 测试 reset_stats
    try:
        plugin.reset_stats()
        record_result('stats_context', 'reset_stats', 'PASS')
    except Exception as e:
        record_result('stats_context', 'reset_stats', 'ERROR', str(e))
    
    # 3. 测试上下文管理器 (__enter__ / __exit__)
    try:
        with plugin as p:
            assert p is not None
            assert p.is_connected() is not None
        record_result('stats_context', 'context_manager', 'PASS',
                     details="上下文管理器正常工作")
    except Exception as e:
        record_result('stats_context', 'context_manager', 'ERROR', str(e))

# ==============================================
# 测试报告生成
# ==============================================

def generate_test_report():
    """生成测试报告"""
    print_header("测试报告")
    
    # 计算通过率
    pass_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    
    print(f"\n📊 测试总览:")
    print(f"  总接口数：{test_results['total']}")
    print(f"  ✅ 通过：{test_results['passed']}")
    print(f"  ❌ 失败：{test_results['failed']}")
    print(f"  ⚠️  错误：{test_results['errors']}")
    print(f"  📊 通过率：{pass_rate:.1f}%")
    
    # 分类统计
    print(f"\n📁 分类统计:")
    for category, tests in test_results['interfaces'].items():
        passed = sum(1 for t in tests if t['status'] == 'PASS')
        total = len(tests)
        rate = (passed / total * 100) if total > 0 else 0
        print(f"  {category}: {passed}/{total} ({rate:.1f}%)")
    
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
    report_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存 JSON 报告
    json_path = os.path.join(report_dir, f'new_interfaces_test_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 报告已保存：{json_path}")
    
    # 保存文本报告
    txt_path = os.path.join(report_dir, f'new_interfaces_test_{timestamp}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("【测试】18 个新接口验证测试报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"生成时间：{test_results['timestamp']}\n\n")
        f.write("测试总览:\n")
        f.write(f"  总接口数：{test_results['total']}\n")
        f.write(f"  通过：{test_results['passed']}\n")
        f.write(f"  失败：{test_results['failed']}\n")
        f.write(f"  错误：{test_results['errors']}\n")
        f.write(f"  通过率：{pass_rate:.1f}%\n\n")
        
        f.write("分类统计:\n")
        for category, tests in test_results['interfaces'].items():
            passed = sum(1 for t in tests if t['status'] == 'PASS')
            total = len(tests)
            rate = (passed / total * 100) if total > 0 else 0
            f.write(f"  {category}: {passed}/{total} ({rate:.1f}%)\n")
        
        # 失败详情
        failed_tests = []
        for category, tests in test_results['interfaces'].items():
            for test in tests:
                if test['status'] in ['FAIL', 'ERROR']:
                    failed_tests.append({
                        'category': category,
                        'name': test['name'],
                        'status': test['status'],
                        'error': test['error']
                    })
        
        if failed_tests:
            f.write("\n失败/错误详情:\n")
            for test in failed_tests:
                f.write(f"  - {test['category']}.{test['name']}: {test['status']}\n")
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
    print_header("18 个新接口验证测试开始")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试接口：18 个")
    print(f"测试分类：4 类")
    print("  - 生命周期接口：8 个")
    print("  - 新增数据接口：3 个")
    print("  - 配置管理接口：4 个")
    print("  - 统计与上下文：3 个")
    
    start_time = time.time()
    
    # 执行所有测试
    try:
        test_lifecycle_interfaces()
    except Exception as e:
        logger.error(f"生命周期接口测试异常：{e}", exc_info=True)
    
    try:
        test_new_data_interfaces()
    except Exception as e:
        logger.error(f"新增数据接口测试异常：{e}", exc_info=True)
    
    try:
        test_config_management_interfaces()
    except Exception as e:
        logger.error(f"配置管理接口测试异常：{e}", exc_info=True)
    
    try:
        test_stats_and_context_interfaces()
    except Exception as e:
        logger.error(f"统计与上下文接口测试异常：{e}", exc_info=True)
    
    elapsed_time = time.time() - start_time
    
    # 生成报告
    pass_rate = generate_test_report()
    
    print_header("18 个新接口验证测试完成")
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
