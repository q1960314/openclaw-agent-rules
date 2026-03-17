#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【任务：47 个 Tushare 接口全量测试】
测试全部 47 个 Tushare 接口，验证：
1. 能否正常调用
2. 返回数据是否有效
3. 数据是否正确保存
4. Parquet 压缩是否正常
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

# 添加路径
sys.path.insert(0, '/home/admin/.openclaw/agents/master')

# 导入 Tushare
try:
    import tushare as ts
    from tushare.pro import data_pro
    print("✅ Tushare 导入成功")
except ImportError as e:
    print(f"❌ Tushare 导入失败：{e}")
    sys.exit(1)

# 检查 Parquet
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
    print("✅ Parquet 支持已启用")
except ImportError:
    PARQUET_AVAILABLE = False
    print("⚠️  Parquet 不支持，将使用 CSV")

# ============================================================================
# 【配置区】
# ============================================================================
TUSHARE_TOKEN = "ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb"
TUSHARE_API_URL = "http://42.194.163.97:5000"
DATA_DIR = "/home/admin/.openclaw/agents/master/quant_data_project/data/test_results/"
LOG_DIR = "/home/admin/.openclaw/agents/master/quant_data_project/logs/"

# 创建目录
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 初始化 Tushare
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()
# 自定义 API URL（如果需要）
if TUSHARE_API_URL:
    pro._DataApi__http_url = TUSHARE_API_URL

# 测试日期范围
END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
LATEST_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

# ============================================================================
# 【47 个接口分类定义】
# ============================================================================
INTERFACE_CATEGORIES = {
    "基础数据": [
        {"name": "stock_basic", "desc": "股票基本信息", "params": {"exchange": "", "list_status": "L", "fields": "ts_code,symbol,name,area,industry,market,list_date"}},
        {"name": "trade_cal", "desc": "交易日历", "params": {"exchange": "", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "namechange", "desc": "股票名称变更", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "hs_const", "desc": "沪深股通成分股", "params": {"hs_type": "SH", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "stock_company", "desc": "上市公司信息", "params": {"fields": "ts_code,change_date,industry,chairman,manager,cfo,reg_capital,employee_num"}},
        {"name": "stk_managers", "desc": "上市公司管理层", "params": {"fields": "ts_code,ann_date,name,position"}},
    ],
    "行情数据": [
        {"name": "daily", "desc": "日线行情", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "weekly", "desc": "周线行情", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "monthly", "desc": "月线行情", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "daily_basic", "desc": "每日指标", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "adj_factor", "desc": "复权因子", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "suspend_d", "desc": "停牌天数", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "stk_limit", "desc": "每日涨跌停", "params": {"start_date": LATEST_DATE, "end_date": LATEST_DATE}},
    ],
    "财务数据": [
        {"name": "fina_indicator", "desc": "财务指标", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "income", "desc": "利润表", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "balancesheet", "desc": "资产负债表", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "cashflow", "desc": "现金流量表", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "fina_audit", "desc": "财务审计意见", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "fina_mainbz", "desc": "主营业务构成", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "dividend", "desc": "分红信息", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "report_rc", "desc": "研报盈利预测", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "forecast", "desc": "业绩预告", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
    ],
    "资金流向": [
        {"name": "moneyflow", "desc": "资金流向", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "hk_hold", "desc": "北向资金持股", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "stk_holdertrade", "desc": "股东增减持", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "share_float", "desc": "解禁统计", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "top10_holders", "desc": "十大股东", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
    ],
    "板块概念": [
        {"name": "concept_list", "desc": "概念列表", "params": {"src": "ts"}},
        {"name": "concept_detail", "desc": "概念详情", "params": {"id": "BK0621"}},
        {"name": "index_classify", "desc": "指数行业分类", "params": {"src": "SW2021"}},
        {"name": "index_member", "desc": "指数成分股", "params": {"index_code": "801010.SI"}},
    ],
    "情绪打板": [
        {"name": "limit_list", "desc": "涨跌停列表", "params": {"trade_date": LATEST_DATE}},
        {"name": "limit_list_d", "desc": "涨跌停详情", "params": {"start_date": LATEST_DATE, "end_date": LATEST_DATE}},
        {"name": "cyq_chips", "desc": "筹码分布", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "cyq_perf", "desc": "筹码性能", "params": {"ts_code": "000001.SZ", "start_date": START_DATE, "end_date": END_DATE}},
    ],
    "龙虎榜": [
        {"name": "top_list", "desc": "龙虎榜", "params": {"trade_date": LATEST_DATE}},
        {"name": "top_inst", "desc": "龙虎榜机构席位", "params": {"trade_date": LATEST_DATE}},
    ],
    "新闻数据": [
        {"name": "news", "desc": "新闻快讯", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "sina"}},
        {"name": "news", "desc": "新闻快讯 (财联社)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "cls"}},
        {"name": "news", "desc": "新闻快讯 (第一财经)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "yicai"}},
        {"name": "news", "desc": "新闻快讯 (东方财富)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "eastmoney"}},
        {"name": "news", "desc": "新闻快讯 (雪球)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "xueqiu"}},
        {"name": "news", "desc": "新闻快讯 (同花顺)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "10jqka"}},
        {"name": "news", "desc": "新闻快讯 (凤凰财经)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "ifeng"}},
        {"name": "news", "desc": "新闻快讯 (金融界)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "jrj"}},
        {"name": "news", "desc": "新闻快讯 (云财经)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "yuncaijing"}},
        {"name": "news", "desc": "新闻快讯 (华尔街见闻)", "params": {"start_date": START_DATE, "end_date": END_DATE, "src": "wallstreetcn"}},
    ],
    "其他补充": [
        {"name": "index_daily", "desc": "大盘指数行情", "params": {"ts_code": "000001.SH", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "index_dailybasic", "desc": "大盘指数指标", "params": {"ts_code": "000001.SH", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "fund_basic", "desc": "基金基本信息", "params": {"market": "E"}},
        {"name": "fund_daily", "desc": "基金日线", "params": {"ts_code": "159915.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "fund_nav", "desc": "基金净值", "params": {"ts_code": "159915.SZ", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "fut_basic", "desc": "期货基本信息", "params": {"exchange": "CFFEX"}},
        {"name": "fut_daily", "desc": "期货日线", "params": {"ts_code": "IF2401.CFX", "start_date": START_DATE, "end_date": END_DATE}},
        {"name": "broker_recommend", "desc": "券商金股", "params": {"start_date": START_DATE, "end_date": END_DATE}},
        {"name": "broker_recommend_detail", "desc": "券商金股详情", "params": {"start_date": START_DATE, "end_date": END_DATE}},
    ],
}

# ============================================================================
# 【测试工具函数】
# ============================================================================

def save_data(df: pd.DataFrame, filename: str, category: str, interface_name: str) -> Dict[str, Any]:
    """保存数据并返回统计信息"""
    result = {
        "filename": filename,
        "format": "parquet" if PARQUET_AVAILABLE else "csv",
        "rows": len(df),
        "columns": len(df.columns),
        "size_bytes": 0,
        "save_success": False,
        "error": None
    }
    
    if len(df) == 0:
        result["error"] = "数据为空"
        return result
    
    try:
        filepath = os.path.join(DATA_DIR, category, f"{filename}")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if PARQUET_AVAILABLE:
            # Parquet 压缩
            df.to_parquet(filepath + ".parquet", compression='snappy', index=False)
            result["size_bytes"] = os.path.getsize(filepath + ".parquet")
        else:
            # CSV
            df.to_csv(filepath + ".csv", index=False, encoding='utf-8-sig')
            result["size_bytes"] = os.path.getsize(filepath + ".csv")
        
        result["save_success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        result["save_success"] = False
    
    return result


def test_interface(category: str, interface_info: Dict) -> Dict[str, Any]:
    """测试单个接口"""
    name = interface_info["name"]
    desc = interface_info["desc"]
    params = interface_info["params"].copy()
    
    result = {
        "category": category,
        "name": name,
        "desc": desc,
        "call_success": False,
        "data_valid": False,
        "save_success": False,
        "row_count": 0,
        "column_count": 0,
        "data_size_kb": 0,
        "time_cost_ms": 0,
        "error": None,
        "error_type": None
    }
    
    start_time = time.time()
    
    try:
        # 检查接口是否存在
        if not hasattr(pro, name):
            result["error"] = f"接口不存在：{name}"
            result["error_type"] = "interface_not_found"
            return result
        
        # 调用接口
        func = getattr(pro, name)
        
        # 处理参数中的日期格式
        for key, value in params.items():
            if isinstance(value, str) and '-' in value:
                params[key] = value.replace('-', '')
        
        # 调用接口
        df = func(**params)
        
        result["call_success"] = True
        result["time_cost_ms"] = int((time.time() - start_time) * 1000)
        
        # 验证数据
        if df is None:
            result["error"] = "接口返回 None"
            result["error_type"] = "empty_response"
            return result
        
        if not isinstance(df, pd.DataFrame):
            result["error"] = f"返回类型错误：{type(df)}"
            result["error_type"] = "invalid_type"
            return result
        
        result["data_valid"] = True
        result["row_count"] = len(df)
        result["column_count"] = len(df.columns)
        
        # 保存数据
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_result = save_data(df, filename, category, name)
        result["save_success"] = save_result["save_success"]
        result["data_size_kb"] = round(save_result["size_bytes"] / 1024, 2)
        result["save_error"] = save_result.get("error")
        
        if not save_result["save_success"]:
            result["error"] = f"保存失败：{save_result.get('error')}"
            result["error_type"] = "save_failed"
        
    except Exception as e:
        result["call_success"] = False
        result["time_cost_ms"] = int((time.time() - start_time) * 1000)
        result["error"] = str(e)
        
        # 错误分类
        error_str = str(e).lower()
        if "权限" in error_str or "permission" in error_str or "积分" in error_str:
            result["error_type"] = "permission_denied"
        elif "timeout" in error_str or "连接" in error_str or "network" in error_str:
            result["error_type"] = "network_error"
        elif "参数" in error_str or "param" in error_str:
            result["error_type"] = "invalid_params"
        else:
            result["error_type"] = "unknown_error"
    
    return result


def run_all_tests() -> Dict[str, Any]:
    """运行全部测试"""
    print("\n" + "="*80)
    print("【47 个 Tushare 接口全量测试】")
    print("="*80)
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Parquet 支持：{'✅ 已启用' if PARQUET_AVAILABLE else '❌ 未启用'}")
    print(f"数据保存目录：{DATA_DIR}")
    print("="*80 + "\n")
    
    total_start = time.time()
    all_results = {
        "test_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "categories": {},
        "summary": {
            "total": 0,
            "success": 0,
            "failed": 0,
            "permission_denied": 0,
            "network_error": 0,
            "empty_response": 0,
            "other_error": 0
        }
    }
    
    # 按分类测试
    for category, interfaces in INTERFACE_CATEGORIES.items():
        print(f"\n{'='*80}")
        print(f"【测试分类】{category}（{len(interfaces)} 个接口）")
        print(f"{'='*80}")
        
        category_results = {
            "category": category,
            "total": len(interfaces),
            "success": 0,
            "failed": 0,
            "interfaces": []
        }
        
        for i, interface in enumerate(interfaces, 1):
            print(f"\n[{i}/{len(interfaces)}] 测试 {interface['name']} - {interface['desc']}...", end=" ")
            
            result = test_interface(category, interface)
            category_results["interfaces"].append(result)
            
            # 统计
            if result["call_success"] and result["data_valid"]:
                print(f"✅ 成功 (数据：{result['row_count']}行/{result['column_count']}列, 耗时：{result['time_cost_ms']}ms, 大小：{result['data_size_kb']}KB)")
                category_results["success"] += 1
                all_results["summary"]["success"] += 1
            else:
                error_type_map = {
                    "permission_denied": "❌ 权限不足",
                    "network_error": "⚠️  网络错误",
                    "empty_response": "⚠️  空数据",
                    "interface_not_found": "❌ 接口不存在",
                    "invalid_params": "❌ 参数错误",
                    "save_failed": "⚠️  保存失败",
                    "invalid_type": "❌ 类型错误",
                    "unknown_error": f"❌ 错误：{result['error'][:50]}"
                }
                error_msg = error_type_map.get(result["error_type"], f"❌ {result['error'][:50]}")
                print(f"{error_msg}")
                
                category_results["failed"] += 1
                all_results["summary"]["failed"] += 1
                
                if result["error_type"] == "permission_denied":
                    all_results["summary"]["permission_denied"] += 1
                elif result["error_type"] == "network_error":
                    all_results["summary"]["network_error"] += 1
                elif result["error_type"] == "empty_response":
                    all_results["summary"]["empty_response"] += 1
                else:
                    all_results["summary"]["other_error"] += 1
            
            all_results["summary"]["total"] += 1
        
        all_results["categories"][category] = category_results
    
    total_time = int((time.time() - total_start) / 60)
    all_results["summary"]["total_time_minutes"] = total_time
    
    return all_results


def generate_report(results: Dict[str, Any]):
    """生成测试报告"""
    print("\n" + "="*80)
    print("【测试报告汇总】")
    print("="*80)
    
    summary = results["summary"]
    print(f"\n总测试接口数：{summary['total']}")
    print(f"成功：{summary['success']} ({summary['success']/summary['total']*100:.1f}%)")
    print(f"失败：{summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)")
    print(f"  - 权限不足：{summary['permission_denied']}")
    print(f"  - 网络错误：{summary['network_error']}")
    print(f"  - 空数据：{summary['empty_response']}")
    print(f"  - 其他错误：{summary['other_error']}")
    print(f"总耗时：{summary['total_time_minutes']} 分钟")
    
    # 按分类统计
    print("\n【分类统计】")
    for category, data in results["categories"].items():
        success_rate = data["success"]/data["total"]*100 if data["total"] > 0 else 0
        print(f"  {category}: {data['success']}/{data['total']} ({success_rate:.1f}%)")
    
    # 保存报告
    report_path = os.path.join(LOG_DIR, f"interface_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存：{report_path}")
    
    # 生成 Markdown 报告
    md_report = generate_markdown_report(results)
    md_path = os.path.join(LOG_DIR, f"interface_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    print(f"Markdown 报告已保存：{md_path}")
    
    return report_path


def generate_markdown_report(results: Dict[str, Any]) -> str:
    """生成 Markdown 格式报告"""
    md = []
    md.append("# Tushare 接口全量测试报告")
    md.append(f"\n**测试时间：** {results['test_time']}")
    md.append(f"\n**Parquet 支持：** {'✅ 已启用' if PARQUET_AVAILABLE else '❌ 未启用'}")
    
    summary = results["summary"]
    md.append("\n## 汇总统计\n")
    md.append(f"| 指标 | 数值 |")
    md.append(f"|------|------|")
    md.append(f"| 总接口数 | {summary['total']} |")
    md.append(f"| 成功 | {summary['success']} ({summary['success']/summary['total']*100:.1f}%) |")
    md.append(f"| 失败 | {summary['failed']} |")
    md.append(f"| 权限不足 | {summary['permission_denied']} |")
    md.append(f"| 网络错误 | {summary['network_error']} |")
    md.append(f"| 空数据 | {summary['empty_response']} |")
    md.append(f"| 总耗时 | {summary['total_time_minutes']} 分钟 |")
    
    md.append("\n## 分类详情\n")
    for category, data in results["categories"].items():
        md.append(f"### {category}\n")
        md.append(f"**成功率：** {data['success']}/{data['total']} ({data['success']/data['total']*100:.1f}%)\n")
        md.append("\n| 接口名 | 描述 | 状态 | 数据量 | 耗时 | 大小 | 错误 |")
        md.append("|--------|------|------|--------|------|------|------|")
        
        for iface in data["interfaces"]:
            status = "✅" if iface["call_success"] and iface["data_valid"] else "❌"
            data_info = f"{iface['row_count']}行/{iface['column_count']}列" if iface["data_valid"] else "-"
            time_info = f"{iface['time_cost_ms']}ms" if iface["time_cost_ms"] > 0 else "-"
            size_info = f"{iface['data_size_kb']}KB" if iface["data_size_kb"] > 0 else "-"
            error_info = iface.get("error", "")[:50] if iface.get("error") else "-"
            
            md.append(f"| {iface['name']} | {iface['desc']} | {status} | {data_info} | {time_info} | {size_info} | {error_info} |")
        
        md.append("")
    
    md.append("\n---\n*本报告由自动化测试脚本生成*")
    
    return "\n".join(md)


# ============================================================================
# 【主函数】
# ============================================================================

if __name__ == "__main__":
    try:
        # 运行测试
        results = run_all_tests()
        
        # 生成报告
        generate_report(results)
        
        print("\n" + "="*80)
        print("✅ 全部测试完成！")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程出错：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
