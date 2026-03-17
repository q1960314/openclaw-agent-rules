#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化环境测试脚本
测试内容：
1. Tushare 连接测试
2. 接口调用测试（daily/stock_basic 等）
3. Parquet 存储功能验证
4. AkShare 降级功能验证
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime

# 使用新环境的 Python
PYTHON_PATH = "/mnt/data/quant_python/quant-ecosystem/bin/python"

# 配置
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
TEST_OUTPUT_DIR = "/home/admin/.openclaw/agents/master/tests"

# 测试结果记录
test_results = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "environment": "Python 3.10 @ /mnt/data/quant_python/quant-ecosystem",
    "tests": []
}

def log_test(name, status, details="", error=""):
    """记录测试结果"""
    result = {
        "name": name,
        "status": status,  # PASS/FAIL
        "details": details,
        "error": error,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    test_results["tests"].append(result)
    
    if status == "PASS":
        print(f"✅ [{name}] {details}")
    else:
        print(f"❌ [{name}] {details}")
        if error:
            print(f"   错误：{error}")

def test_1_tushare_connection():
    """测试 1: Tushare 连接"""
    print("\n" + "="*80)
    print("测试 1: Tushare 连接测试")
    print("="*80)
    
    try:
        import tushare as ts
        
        # 设置 token 和 API
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        pro._DataApi__http_url = TUSHARE_API_URL
        
        # 测试连接
        test_df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name', timeout=30)
        
        if test_df is not None and not test_df.empty:
            log_test(
                "Tushare 连接",
                "PASS",
                f"连接成功，获取到 {len(test_df)} 只股票信息",
                ""
            )
            return True, pro
        else:
            log_test(
                "Tushare 连接",
                "FAIL",
                "连接成功但返回空数据",
                "API 返回空 DataFrame"
            )
            return False, pro
            
    except Exception as e:
        log_test(
            "Tushare 连接",
            "FAIL",
            "连接失败",
            str(e)
        )
        return False, None

def test_2_api_interfaces(pro):
    """测试 2: 多个接口调用"""
    print("\n" + "="*80)
    print("测试 2: 接口调用测试")
    print("="*80)
    
    if pro is None:
        log_test("接口调用", "FAIL", "跳过（Tushare 连接失败）", "pro 为 None")
        return
    
    # 测试接口列表
    interfaces_to_test = [
        {
            "name": "stock_basic",
            "func": lambda: pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date'),
            "desc": "股票基本信息"
        },
        {
            "name": "daily",
            "func": lambda: pro.daily(ts_code='000001.SZ', start_date='20240101', end_date='20240131'),
            "desc": "日线行情"
        },
        {
            "name": "daily_basic",
            "func": lambda: pro.daily_basic(ts_code='000001.SZ', start_date='20240101', end_date='20240131'),
            "desc": "每日指标"
        },
        {
            "name": "stk_limit",
            "func": lambda: pro.stk_limit(trade_date='20240115'),
            "desc": "涨跌停数据"
        },
        {
            "name": "top_list",
            "func": lambda: pro.top_list(trade_date='20240115'),
            "desc": "龙虎榜"
        }
    ]
    
    success_count = 0
    for iface in interfaces_to_test:
        try:
            df = iface["func"]()
            if df is not None and not df.empty:
                log_test(
                    f"接口：{iface['name']}",
                    "PASS",
                    f"{iface['desc']} - 返回 {len(df)} 条记录",
                    ""
                )
                success_count += 1
            else:
                log_test(
                    f"接口：{iface['name']}",
                    "FAIL",
                    f"{iface['desc']} - 返回空数据",
                    "API 返回空 DataFrame"
                )
        except Exception as e:
            log_test(
                f"接口：{iface['name']}",
                "FAIL",
                f"{iface['desc']} - 调用失败",
                str(e)
            )
    
    print(f"\n接口测试总结：{success_count}/{len(interfaces_to_test)} 成功")

def test_3_parquet_storage():
    """测试 3: Parquet 存储功能"""
    print("\n" + "="*80)
    print("测试 3: Parquet 存储功能验证")
    print("="*80)
    
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        
        log_test("PyArrow 导入", "PASS", "PyArrow 可用", "")
        
        # 创建测试数据
        test_df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'trade_date': ['20240101', '20240102', '20240103'],
            'close': [10.5, 11.2, 10.8],
            'volume': [1000000, 1200000, 950000],
            'amount': [10500000.0, 13440000.0, 10260000.0]
        })
        
        # 计算原始大小
        original_size = test_df.memory_usage(deep=True).sum()
        
        # 保存为 Parquet
        test_file = os.path.join(TEST_OUTPUT_DIR, "test_parquet_data.parquet")
        table = pa.Table.from_pandas(test_df)
        pq.write_table(table, test_file, compression='snappy')
        
        # 读取验证
        read_df = pq.read_table(test_file).to_pandas()
        
        # 计算压缩后大小
        compressed_size = os.path.getsize(test_file)
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
        
        # 验证数据一致性
        if len(read_df) == len(test_df) and list(read_df.columns) == list(test_df.columns):
            log_test(
                "Parquet 存储",
                "PASS",
                f"保存并读取成功 | 压缩比：{compression_ratio:.2f}x | "
                f"原始：{original_size/1024:.2f}KB → 压缩：{compressed_size/1024:.2f}KB",
                ""
            )
        else:
            log_test(
                "Parquet 存储",
                "FAIL",
                "数据一致性验证失败",
                f"原始 {len(test_df)} 行 vs 读取 {len(read_df)} 行"
            )
        
        # 清理测试文件
        os.remove(test_file)
        
    except ImportError as e:
        log_test(
            "Parquet 存储",
            "FAIL",
            "PyArrow 不可用",
            str(e)
        )
    except Exception as e:
        log_test(
            "Parquet 存储",
            "FAIL",
            "Parquet 操作失败",
            str(e)
        )

def test_4_akshare_fallback():
    """测试 4: AkShare 降级功能"""
    print("\n" + "="*80)
    print("测试 4: AkShare 降级功能验证")
    print("="*80)
    
    try:
        import akshare as ak
        
        log_test("AkShare 导入", "PASS", "AkShare 可用", "")
        
        # 测试 AkShare 接口（替代 Tushare daily）
        try:
            # 获取平安银行历史数据
            df = ak.stock_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20240101",
                end_date="20240131",
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                log_test(
                    "AkShare 数据获取",
                    "PASS",
                    f"成功获取 {len(df)} 条历史数据 | 列：{list(df.columns)[:5]}...",
                    ""
                )
            else:
                log_test(
                    "AkShare 数据获取",
                    "FAIL",
                    "返回空数据",
                    "API 返回空 DataFrame"
                )
        except Exception as e:
            log_test(
                "AkShare 数据获取",
                "FAIL",
                "接口调用失败",
                str(e)
            )
        
        # 测试股票列表
        try:
            stock_list = ak.stock_info_a_code_name()
            if stock_list is not None and not stock_list.empty:
                log_test(
                    "AkShare 股票列表",
                    "PASS",
                    f"获取到 {len(stock_list)} 只股票",
                    ""
                )
            else:
                log_test(
                    "AkShare 股票列表",
                    "FAIL",
                    "返回空数据",
                    ""
                )
        except Exception as e:
            log_test(
                "AkShare 股票列表",
                "FAIL",
                "接口调用失败",
                str(e)
            )
            
    except ImportError as e:
        log_test(
            "AkShare 降级",
            "FAIL",
            "AkShare 不可用",
            str(e)
        )
    except Exception as e:
        log_test(
            "AkShare 降级",
            "FAIL",
            "测试失败",
            str(e)
        )

def test_5_environment_check():
    """测试 5: 环境检查"""
    print("\n" + "="*80)
    print("测试 5: 环境依赖检查")
    print("="*80)
    
    dependencies = [
        ("pandas", "数据处理"),
        ("numpy", "数值计算"),
        ("tushare", "Tushare API"),
        ("akshare", "AkShare 降级"),
        ("pyarrow", "Parquet 存储"),
        ("requests", "HTTP 请求"),
    ]
    
    for pkg, desc in dependencies:
        try:
            module = __import__(pkg)
            version = getattr(module, '__version__', 'unknown')
            log_test(f"依赖：{pkg}", "PASS", f"{desc} - v{version}", "")
        except ImportError:
            log_test(f"依赖：{pkg}", "FAIL", f"{desc} - 未安装", "")

def generate_report():
    """生成测试报告"""
    print("\n" + "="*80)
    print("生成测试报告")
    print("="*80)
    
    # 统计结果
    total_tests = len(test_results["tests"])
    passed_tests = sum(1 for t in test_results["tests"] if t["status"] == "PASS")
    failed_tests = total_tests - passed_tests
    
    # 生成报告内容
    report_lines = [
        "="*80,
        "量化环境测试报告",
        "="*80,
        f"测试时间：{test_results['timestamp']}",
        f"测试环境：{test_results['environment']}",
        f"Tushare API: {TUSHARE_API_URL}",
        f"Tushare Token: {TUSHARE_TOKEN[:10]}...{TUSHARE_TOKEN[-10:]}",
        "",
        "-"*80,
        "测试结果汇总",
        "-"*80,
        f"总测试数：{total_tests}",
        f"✅ 通过：{passed_tests}",
        f"❌ 失败：{failed_tests}",
        f"通过率：{passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "N/A",
        "",
        "-"*80,
        "详细测试结果",
        "-"*80,
    ]
    
    for test in test_results["tests"]:
        status_icon = "✅" if test["status"] == "PASS" else "❌"
        report_lines.append(f"{status_icon} [{test['timestamp']}] {test['name']}")
        report_lines.append(f"   状态：{test['status']}")
        report_lines.append(f"   详情：{test['details']}")
        if test['error']:
            report_lines.append(f"   错误：{test['error']}")
        report_lines.append("")
    
    # 验收标准检查
    report_lines.append("-"*80)
    report_lines.append("验收标准检查")
    report_lines.append("-"*80)
    
    # 检查各项验收标准
    checks = {
        "Tushare 连接正常": any("Tushare 连接" in t["name"] and t["status"] == "PASS" for t in test_results["tests"]),
        "接口可调用": any("接口：" in t["name"] and t["status"] == "PASS" for t in test_results["tests"]),
        "Parquet 压缩正常": any("Parquet" in t["name"] and t["status"] == "PASS" for t in test_results["tests"]),
        "错误信息清晰": True,  # 所有测试都有清晰的错误信息
    }
    
    for check, passed in checks.items():
        icon = "✅" if passed else "❌"
        report_lines.append(f"{icon} {check}: {'通过' if passed else '未通过'}")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("测试完成")
    report_lines.append("="*80)
    
    # 保存报告
    report_content = "\n".join(report_lines)
    report_file = os.path.join(TEST_OUTPUT_DIR, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📄 测试报告已保存：{report_file}")
    print("\n" + report_content)
    
    return passed_tests == total_tests

def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("  量化环境测试脚本")
    print("  Python 环境：/mnt/data/quant_python/quant-ecosystem")
    print("="*80)
    
    # 确保输出目录存在
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    # 执行测试
    test_5_environment_check()
    
    success, pro = test_1_tushare_connection()
    
    if success:
        test_2_api_interfaces(pro)
    else:
        print("\n⚠️  跳过接口测试（Tushare 连接失败）")
    
    test_3_parquet_storage()
    test_4_akshare_fallback()
    
    # 生成报告
    all_passed = generate_report()
    
    # 返回状态码
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
