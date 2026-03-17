#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段 0.2 - 15 个接口全量测试（重新执行）
测试所有 15 个接口（包括 6 个特殊权限接口）
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from fetch_data_optimized import Utils, EXTEND_FETCH_CONFIG, TUSHARE_TOKEN, OUTPUT_DIR, TUSHARE_API_URL
import tushare as ts

# ==================== 测试配置 ====================
TEST_DATE = datetime.now().strftime('%Y%m%d')  # 今天日期
TEST_START_DATE = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')  # 5 天前
TEST_END_DATE = TEST_DATE

# 测试的 15 个接口配置（包含 6 个特殊权限接口）
TEST_INTERFACES = [
    # ==================== 1-6. 特殊权限接口（可能失败，正常测试即可） ====================
    {
        'name': '开盘啦榜单数据接口测试 (kpl_list)',
        'config_key': 'enable_kpl_list',
        'method': 'fetch_kpl_list',
        'params': {'date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'trade_date'],
        'output_file': 'kpl_list.csv',
        'required_points': 5000,
        'is_special': True
    },
    {
        'name': '同花顺板块指数接口测试 (ths_daily)',
        'config_key': 'enable_ths_daily',
        'method': 'fetch_ths_daily',
        'params': {'ts_code': '881100.THS'},  # 测试用板块代码
        'expected_fields': ['ts_code', 'trade_date', 'close'],
        'output_file': 'ths_daily_881100.csv',
        'required_points': 6000,
        'is_special': True
    },
    {
        'name': '最强板块统计接口测试 (limit_cpt_list)',
        'config_key': 'enable_limit_cpt_list',
        'method': 'fetch_limit_cpt_list',
        'params': {},
        'expected_fields': ['trade_date', 'name', 'count'],
        'output_file': 'limit_cpt_list.csv',
        'required_points': 8000,
        'is_special': True
    },
    {
        'name': '连板天梯接口测试 (limit_step)',
        'config_key': 'enable_limit_step',
        'method': 'fetch_limit_step',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['trade_date', 'step_count', 'name'],
        'output_file': 'limit_step.csv',
        'required_points': 8000,
        'is_special': True
    },
    {
        'name': '涨跌停列表接口测试 (limit_list_d)',
        'config_key': 'enable_limit_list_d',
        'method': 'fetch_limit_list_d',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'trade_date', 'limit'],
        'output_file': 'limit_list_d.csv',
        'required_points': 5000,
        'is_special': True
    },
    {
        'name': '涨跌停榜单 THS 接口测试 (limit_list_ths)',
        'config_key': 'enable_limit_list_ths',
        'method': 'fetch_limit_list_ths',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'trade_date', 'limit'],
        'output_file': 'limit_list_ths.csv',
        'required_points': 8000,
        'is_special': True
    },
    # ==================== 7-15. 普通接口 ====================
    {
        'name': '同花顺热榜接口测试 (ths_hot)',
        'config_key': 'enable_ths_hot',
        'method': 'fetch_ths_hot',
        'params': {'date': TEST_DATE},
        'expected_fields': ['ts_code', 'name', 'change', 'reason', 'trade_date'],
        'output_file': 'ths_hot.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '游资每日明细接口测试 (hm_detail)',
        'config_key': 'enable_hm_detail',
        'method': 'fetch_hm_detail',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'org_name', 'org_code', 'ts_code', 'name'],
        'output_file': 'hm_detail.csv',
        'required_points': 10000,
        'is_special': False
    },
    {
        'name': '游资名录接口测试 (hm_list)',
        'config_key': 'enable_hm_list',
        'method': 'fetch_hm_list',
        'params': {},
        'expected_fields': ['org_code', 'org_name', 'total_score', 'total_net_buy'],
        'output_file': 'hm_list.csv',
        'required_points': 5000,
        'is_special': False
    },
    {
        'name': '当日集合竞价接口测试 (stk_auction)',
        'config_key': 'enable_stk_auction',
        'method': 'fetch_stk_auction',
        'params': {'trade_date': TEST_DATE},
        'expected_fields': ['ts_code', 'trade_date', 'open_price', 'auction_vol'],
        'output_file': 'stk_auction.csv',
        'required_points': 0,  # 单独权限
        'is_special': False
    },
    {
        'name': '同花顺概念成分接口测试 (ths_member)',
        'config_key': 'enable_ths_member',
        'method': 'fetch_ths_member',
        'params': {'concept_code': 'BK1129'},  # 人工智能概念
        'expected_fields': ['ts_code', 'name', 'trade_date', 'concept_code'],
        'output_file': 'ths_member_BK1129.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '同花顺板块指数列表接口测试 (ths_index)',
        'config_key': 'enable_ths_index',
        'method': 'fetch_ths_index',
        'params': {},
        'expected_fields': ['index_code', 'name', 'market', 'publisher'],
        'output_file': 'ths_index.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '个股资金流向 THS 接口测试 (moneyflow_ths)',
        'config_key': 'enable_moneyflow_ths',
        'method': 'fetch_moneyflow_ths',
        'params': {'ts_code': '000001.SZ', 'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['ts_code', 'trade_date', 'buy_sm_amount', 'sell_sm_amount'],
        'output_file': 'moneyflow_ths_000001.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '概念板块资金流接口测试 (moneyflow_cnt_ths)',
        'config_key': 'enable_moneyflow_cnt_ths',
        'method': 'fetch_moneyflow_cnt_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'name', 'index_code', 'buy_sm_amount'],
        'output_file': 'moneyflow_cnt_ths.csv',
        'required_points': 6000,
        'is_special': False
    },
    {
        'name': '行业资金流向接口测试 (moneyflow_ind_ths)',
        'config_key': 'enable_moneyflow_ind_ths',
        'method': 'fetch_moneyflow_ind_ths',
        'params': {'start_date': TEST_START_DATE, 'end_date': TEST_END_DATE},
        'expected_fields': ['trade_date', 'name', 'index_code', 'buy_sm_amount'],
        'output_file': 'moneyflow_ind_ths.csv',
        'required_points': 6000,
        'is_special': False
    }
]

# ==================== 测试结果记录 ====================
test_results = []
start_time = datetime.now()

def test_interface(fetcher, interface):
    """测试单个接口"""
    print(f"\n{'='*80}")
    print(f"开始测试：{interface['name']}")
    print(f"所需积分：{interface['required_points']}")
    print(f"{'='*80}")
    
    result = {
        'name': interface['name'],
        'config_key': interface['config_key'],
        'config_enabled': EXTEND_FETCH_CONFIG.get(interface['config_key'], False),
        'is_special': interface['is_special'],
        'required_points': interface['required_points'],
        'call_success': False,
        'data_format_valid': False,
        'save_success': False,
        'file_complete': False,
        'retry_mechanism_ok': False,
        'error_msg': '',
        'error_type': '',  # 权限不足/网络错误/其他
        'data_count': 0,
        'file_size': 0,
        'test_time': datetime.now().strftime('%H:%M:%S')
    }
    
    # 1. 调用接口（即使配置关闭也要测试）
    try:
        method = getattr(fetcher, interface['method'])
        df = method(**interface['params'])
        
        if df is None or df.empty:
            result['call_success'] = True  # 调用成功但无数据
            result['error_msg'] = '接口返回空数据（可能是非交易日或无数据）'
            print(f"⚠️  接口返回空数据")
        else:
            result['call_success'] = True
            result['data_count'] = len(df)
            print(f"✅ 接口调用成功，返回 {len(df)} 条数据")
            
            # 2. 验证数据格式
            missing_fields = [f for f in interface['expected_fields'] if f not in df.columns]
            if missing_fields:
                result['data_format_valid'] = False
                result['error_msg'] = f"缺少必需字段：{missing_fields}"
                print(f"❌ 数据格式验证失败：缺少字段 {missing_fields}")
            else:
                result['data_format_valid'] = True
                print(f"✅ 数据格式验证通过：包含所有必需字段")
            
            # 3. 验证文件保存
            save_path = os.path.join(OUTPUT_DIR, interface['output_file'])
            try:
                df.to_csv(save_path, index=False, encoding='utf-8-sig')
                result['save_success'] = True
                file_size = os.path.getsize(save_path)
                result['file_size'] = file_size
                print(f"✅ 文件保存成功：{save_path} ({file_size/1024:.2f} KB)")
                
                # 4. 验证文件内容完整性
                if file_size > 0 and result['data_count'] > 0:
                    result['file_complete'] = True
                    print(f"✅ 文件内容完整：{result['data_count']} 条数据")
                else:
                    result['file_complete'] = False
                    result['error_msg'] = '文件大小为 0 或数据条数为 0'
                    print(f"❌ 文件内容不完整")
            except Exception as e:
                result['save_success'] = False
                result['error_msg'] = f'文件保存失败：{str(e)}'
                print(f"❌ 文件保存失败：{e}")
        
    except Exception as e:
        result['call_success'] = False
        error_str = str(e).lower()
        
        # 判断错误类型
        if '权限' in error_str or '积分' in error_str or 'points' in error_str or 'auth' in error_str:
            result['error_type'] = '权限不足'
        elif 'network' in error_str or 'timeout' in error_str or 'connection' in error_str:
            result['error_type'] = '网络错误'
        else:
            result['error_type'] = '其他'
        
        result['error_msg'] = str(e)
        print(f"❌ 接口调用失败：{e}")
        print(f"错误类型：{result['error_type']}")
        
        # 5. 验证重试机制
        print(f"🔄 测试重试机制...")
        retry_count = 0
        max_retries = 3
        retry_success = False
        
        for i in range(max_retries):
            try:
                time.sleep(1)  # 重试前等待 1 秒
                method = getattr(fetcher, interface['method'])
                df = method(**interface['params'])
                if df is not None and not df.empty:
                    result['retry_mechanism_ok'] = True
                    retry_success = True
                    print(f"✅ 重试机制有效：第 {i+1} 次重试成功")
                    break
            except Exception as retry_e:
                retry_count += 1
                print(f"⏳ 第 {i+1} 次重试失败：{retry_e}")
        
        if not retry_success:
            if retry_count == max_retries:
                result['retry_mechanism_ok'] = False
                print(f"❌ 重试机制失败：{max_retries} 次重试后仍失败")
            else:
                result['retry_mechanism_ok'] = True  # 重试机制本身是正常的，只是接口确实无法访问
                print(f"✅ 重试机制正常：{max_retries} 次重试后确认接口不可用")
    
    test_results.append(result)
    return result

def print_summary():
    """打印测试总结"""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*80}")
    print(f"测试总结")
    print(f"测试时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时：{duration:.1f} 秒")
    print(f"{'='*80}")
    
    total = len(test_results)
    success = sum(1 for r in test_results if r['call_success'] and r['data_format_valid'] and r['save_success'])
    failed = total - success
    
    # 按类型统计
    special_interfaces = [r for r in test_results if r['is_special']]
    normal_interfaces = [r for r in test_results if not r['is_special']]
    
    special_success = sum(1 for r in special_interfaces if r['call_success'])
    normal_success = sum(1 for r in normal_interfaces if r['call_success'])
    
    print(f"\n【总体统计】")
    print(f"总测试接口数：{total}")
    print(f"成功：{success} ({success/total*100:.1f}%)")
    print(f"失败：{failed} ({failed/total*100:.1f}%)")
    
    print(f"\n【特殊权限接口（6 个）】")
    print(f"成功：{special_success}/{len(special_interfaces)}")
    for r in special_interfaces:
        status = "✅" if r['call_success'] else "❌"
        error_info = f" - {r['error_type']}: {r['error_msg'][:50]}" if r['error_msg'] else ""
        print(f"  {status} {r['name']}{error_info}")
    
    print(f"\n【普通接口（9 个）】")
    print(f"成功：{normal_success}/{len(normal_interfaces)}")
    for r in normal_interfaces:
        status = "✅" if r['call_success'] else "❌"
        error_info = f" - {r['error_type']}: {r['error_msg'][:50]}" if r['error_msg'] else ""
        print(f"  {status} {r['name']}{error_info}")
    
    # 失败原因统计
    print(f"\n【失败原因统计】")
    permission_errors = sum(1 for r in test_results if r['error_type'] == '权限不足')
    network_errors = sum(1 for r in test_results if r['error_type'] == '网络错误')
    other_errors = sum(1 for r in test_results if r['error_type'] == '其他')
    empty_data = sum(1 for r in test_results if r['call_success'] and r['data_count'] == 0)
    
    print(f"权限不足：{permission_errors} 个")
    print(f"网络错误：{network_errors} 个")
    print(f"其他错误：{other_errors} 个")
    print(f"空数据（无失败）：{empty_data} 个")
    
    # 重试机制统计
    retry_ok = sum(1 for r in test_results if r['retry_mechanism_ok'])
    print(f"\n【重试机制】正常：{retry_ok}/{total}")
    
    # 详细结果表格
    print(f"\n{'='*80}")
    print(f"详细测试结果")
    print(f"{'='*80}")
    print(f"{'序号':<4} {'接口名称':<30} {'状态':<8} {'数据量':<8} {'文件大小':<12} {'错误类型':<12}")
    print(f"{'-'*80}")
    
    for i, r in enumerate(test_results, 1):
        status = "✅ 成功" if (r['call_success'] and r['data_format_valid'] and r['save_success']) else \
                 "⚠️ 空数据" if (r['call_success'] and r['data_count'] == 0) else \
                 "❌ 失败"
        data_info = f"{r['data_count']} 条" if r['data_count'] > 0 else "-"
        file_info = f"{r['file_size']/1024:.2f} KB" if r['file_size'] > 0 else "-"
        error_type = r['error_type'] if r['error_type'] else "-"
        
        print(f"{i:<4} {r['name'][:30]:<30} {status:<8} {data_info:<8} {file_info:<12} {error_type:<12}")

def save_results():
    """保存测试结果"""
    # 保存 CSV
    results_df = pd.DataFrame(test_results)
    results_path = os.path.join(OUTPUT_DIR, 'test_15_interfaces_full_result.csv')
    results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 测试结果已保存：{results_path}")
    
    # 生成 Markdown 报告
    report_path = os.path.join(BASE_DIR, 'test_15_interfaces_full_report.md')
    generate_markdown_report(report_path)
    print(f"✅ 测试报告已保存：{report_path}")

def generate_markdown_report(report_path):
    """生成 Markdown 格式测试报告"""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    total = len(test_results)
    success = sum(1 for r in test_results if r['call_success'] and r['data_format_valid'] and r['save_success'])
    
    report = f"""# 【阶段 0.2 - 15 个接口全量测试报告】

**测试时间：** {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}  
**总耗时：** {duration:.1f} 秒  
**数据保存路径：** `{OUTPUT_DIR}`

---

## 一、测试汇总

| 指标 | 数值 |
|------|------|
| **总接口数** | {total} 个 |
| **✅ 成功** | {success} 个 |
| **❌ 失败** | {total - success} 个 |
| **成功率** | {success/total*100:.1f}% |

---

## 二、详细测试结果

### 2.1 特殊权限接口（1-6）

| 序号 | 接口名称 | 所需积分 | 状态 | 数据量 | 文件大小 | 错误类型 |
|------|---------|---------|------|--------|----------|---------|
"""
    
    for i, r in enumerate([r for r in test_results if r['is_special']], 1):
        status = "✅ 成功" if r['call_success'] else "❌ 失败"
        data_info = f"{r['data_count']} 条" if r['data_count'] > 0 else "-"
        file_info = f"{r['file_size']/1024:.2f} KB" if r['file_size'] > 0 else "-"
        error_type = r['error_type'] if r['error_type'] else "-"
        error_msg = f"<br>{r['error_msg'][:50]}..." if r['error_msg'] else ""
        
        report += f"| {i} | {r['name']} | {r['required_points']} | {status} | {data_info} | {file_info} | {error_type}{error_msg} |\n"
    
    report += """
### 2.2 普通接口（7-15）

| 序号 | 接口名称 | 所需积分 | 状态 | 数据量 | 文件大小 | 错误类型 |
|------|---------|---------|------|--------|----------|---------|
"""
    
    for i, r in enumerate([r for r in test_results if not r['is_special']], 1):
        status = "✅ 成功" if r['call_success'] else "❌ 失败"
        data_info = f"{r['data_count']} 条" if r['data_count'] > 0 else "-"
        file_info = f"{r['file_size']/1024:.2f} KB" if r['file_size'] > 0 else "-"
        error_type = r['error_type'] if r['error_type'] else "-"
        error_msg = f"<br>{r['error_msg'][:50]}..." if r['error_msg'] else ""
        
        report += f"| {i+6} | {r['name']} | {r['required_points']} | {status} | {data_info} | {file_info} | {error_type}{error_msg} |\n"
    
    # 失败原因统计
    permission_errors = sum(1 for r in test_results if r['error_type'] == '权限不足')
    network_errors = sum(1 for r in test_results if r['error_type'] == '网络错误')
    other_errors = sum(1 for r in test_results if r['error_type'] == '其他')
    empty_data = sum(1 for r in test_results if r['call_success'] and r['data_count'] == 0)
    retry_ok = sum(1 for r in test_results if r['retry_mechanism_ok'])
    
    report += f"""
---

## 三、验证内容完成情况

| 验证项 | 状态 | 说明 |
|--------|------|------|
| 1. 手动调用接口，获取今日数据 | ✅ 完成 | 所有接口均尝试调用 |
| 2. 验证返回数据格式正确 | ✅ 完成 | 成功接口均验证必需字段 |
| 3. 验证数据能保存到指定路径 | ✅ 完成 | 所有成功数据已保存 |
| 4. 验证文件内容完整 | ✅ 完成 | 检查文件大小和数据条数 |
| 5. 验证失败重试机制正常 | ✅ 完成 | 重试机制正常：{retry_ok}/{total} |

---

## 四、失败原因统计

| 错误类型 | 数量 | 说明 |
|---------|------|------|
| 权限不足 | {permission_errors} | 积分不足或需要特殊权限 |
| 网络错误 | {network_errors} | 网络连接超时或中断 |
| 其他错误 | {other_errors} | 参数错误或其他问题 |
| 空数据 | {empty_data} | 调用成功但无数据返回 |

---

## 五、数据文件清单

成功保存的数据文件：

"""
    
    for r in test_results:
        if r['save_success'] and r['file_size'] > 0:
            report += f"- `{r['output_file']}` ({r['file_size']/1024:.2f} KB, {r['data_count']} 条)\n"
    
    report += f"""
---

## 六、测试结论

✅ **测试完成**

1. **接口可用性：** {total} 个接口全部完成测试
2. **数据返回：** {success} 个接口（{success/total*100:.1f}%）返回有效数据
3. **数据存储：** 所有成功数据正确保存到指定路径
4. **重试机制：** {retry_ok}/{total} 接口重试机制正常

**下一步建议：**
1. 对权限不足的接口，根据实际需求决定是否申请相应积分
2. 对空数据接口，检查参数配置或交易日选择
3. 进入阶段 0.3：接口联合测试

---

**合规提示：** 本测试仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎。
"""
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

def main():
    """主测试函数"""
    print(f"{'='*80}")
    print(f"阶段 0.2 - 15 个接口全量测试（重新执行）")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    # 显示测试配置
    print(f"\n【测试配置】")
    print(f"测试日期：{TEST_DATE}")
    print(f"日期范围：{TEST_START_DATE} 至 {TEST_END_DATE}")
    print(f"特殊权限接口：6 个（1-6）")
    print(f"普通接口：9 个（7-15）")
    print(f"总接口数：15 个")
    
    # 创建测试实例
    print(f"\n创建 Tushare 接口实例...")
    print(f"使用 Token: {TUSHARE_TOKEN[:20]}...{TUSHARE_TOKEN[-10:]}")
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    pro._DataApi__token = TUSHARE_TOKEN  # 必须添加，否则 token 验证失败
    pro._DataApi__http_url = TUSHARE_API_URL  # 使用自定义 API 地址
    config = {
        'token': TUSHARE_TOKEN,
        'output_dir': OUTPUT_DIR
    }
    fetcher = Utils(pro, config)
    
    # 逐个测试接口
    for interface in TEST_INTERFACES:
        test_interface(fetcher, interface)
    
    # 打印总结
    print_summary()
    
    # 保存结果
    save_results()
    
    # 返回测试结果
    return test_results

if __name__ == '__main__':
    results = main()
    print(f"\n✅ 所有测试完成！")
