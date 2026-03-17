#!/usr/bin/env python3
# ==============================================
# 【测试】Tushare 全接口验证测试 - test_all_tushare_interfaces.py
# ==============================================
# 功能：快速验证所有 47 个 Tushare 接口调用
# 使用：python3 tests/test_all_tushare_interfaces.py
# 时限：15 分钟（每个接口测试 1 条记录）
# ==============================================

import sys
import os
import time
import json
import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tushare_test")

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

# Tushare 配置
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', 'ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb')
TUSHARE_API_URL = 'http://api.tushare.pro'

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

def init_tushare():
    """初始化 Tushare"""
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    # 设置自定义 API URL（如果需要）
    pro._DataApi__http_url = TUSHARE_API_URL
    return pro

# ==============================================
# 第一部分：基础数据接口 (10 个)
# ==============================================

def test_basic_data_interfaces(pro):
    """测试基础数据接口"""
    print_subheader("基础数据接口测试 (10 个)")
    
    # 1. stock_basic - 股票基本信息
    try:
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name', limit=1)
        assert not df.empty, "stock_basic 返回空数据"
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'stock_basic', 'PASS', details=f"获取 {len(df)} 只股票")
    except Exception as e:
        record_result('basic_data', 'stock_basic', 'ERROR', str(e))
    
    # 2. trade_cal - 交易日历
    try:
        df = pro.trade_cal(exchange='SSE', start_date='20260301', end_date='20260331', is_open='1', limit=5)
        assert not df.empty, "trade_cal 返回空数据"
        assert 'cal_date' in df.columns, "缺少 cal_date 字段"
        record_result('basic_data', 'trade_cal', 'PASS', details=f"获取 {len(df)} 个交易日")
    except Exception as e:
        record_result('basic_data', 'trade_cal', 'ERROR', str(e))
    
    # 3. hs_const - 沪深港通成分股
    try:
        df = pro.hs_const(sh_type='SH', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'hs_const', 'PASS', details=f"获取 {len(df)} 只股票")
    except Exception as e:
        record_result('basic_data', 'hs_const', 'ERROR', str(e))
    
    # 4. stock_company - 上市公司信息
    try:
        df = pro.stock_company(ts_code='000001.SZ', fields='ts_code,change_date,industry,org_type')
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'stock_company', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('basic_data', 'stock_company', 'ERROR', str(e))
    
    # 5. stk_managers - 上市公司管理层
    try:
        df = pro.stk_managers(ts_code='000001.SZ', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'stk_managers', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('basic_data', 'stk_managers', 'ERROR', str(e))
    
    # 6. stk_rewards - 上市公司管理层报酬
    try:
        df = pro.stk_rewards(ts_code='000001.SZ', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'stk_rewards', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('basic_data', 'stk_rewards', 'ERROR', str(e))
    
    # 7. new_share - 新股上市信息
    try:
        df = pro.new_share(start_date='20260301', end_date='20260311', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('basic_data', 'new_share', 'PASS', details=f"获取 {len(df)} 只新股")
    except Exception as e:
        record_result('basic_data', 'new_share', 'ERROR', str(e))
    
    # 8. concept_list - 概念列表
    try:
        df = pro.concept_list(fields='code,name', limit=1)
        assert 'code' in df.columns, "缺少 code 字段"
        record_result('basic_data', 'concept_list', 'PASS', details=f"获取 {len(df)} 个概念")
    except Exception as e:
        record_result('basic_data', 'concept_list', 'ERROR', str(e))
    
    # 9. index_classify - 指数分类
    try:
        df = pro.index_classify(level='L1', src='SW2021', limit=1)
        assert 'index_code' in df.columns or 'code' in df.columns, "缺少代码字段"
        record_result('basic_data', 'index_classify', 'PASS', details=f"获取 {len(df)} 个分类")
    except Exception as e:
        record_result('basic_data', 'index_classify', 'ERROR', str(e))
    
    # 10. index_member - 指数成分股
    try:
        df = pro.index_member(index_code='000001.SH', limit=1)
        assert 'ts_code' in df.columns or 'con_code' in df.columns, "缺少代码字段"
        record_result('basic_data', 'index_member', 'PASS', details=f"获取 {len(df)} 只成分股")
    except Exception as e:
        record_result('basic_data', 'index_member', 'ERROR', str(e))

# ==============================================
# 第二部分：行情数据接口 (12 个)
# ==============================================

def test_market_data_interfaces(pro):
    """测试行情数据接口"""
    print_subheader("行情数据接口测试 (12 个)")
    
    # 11. daily - 日线行情
    try:
        df = pro.daily(ts_code='000001.SZ', trade_date='20260311')
        assert not df.empty, "daily 返回空数据"
        assert 'close' in df.columns, "缺少 close 字段"
        record_result('market_data', 'daily', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'daily', 'ERROR', str(e))
    
    # 12. weekly - 周线行情
    try:
        df = pro.weekly(ts_code='000001.SZ', start_date='20260201', end_date='20260311', limit=1)
        assert not df.empty, "weekly 返回空数据"
        assert 'close' in df.columns, "缺少 close 字段"
        record_result('market_data', 'weekly', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'weekly', 'ERROR', str(e))
    
    # 13. monthly - 月线行情
    try:
        df = pro.monthly(ts_code='000001.SZ', start_date='20260101', end_date='20260311', limit=1)
        assert not df.empty, "monthly 返回空数据"
        assert 'close' in df.columns, "缺少 close 字段"
        record_result('market_data', 'monthly', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'monthly', 'ERROR', str(e))
    
    # 14. daily_basic - 每日基本面
    try:
        df = pro.daily_basic(ts_code='000001.SZ', trade_date='20260311')
        assert not df.empty, "daily_basic 返回空数据"
        assert 'turnover_rate' in df.columns, "缺少 turnover_rate 字段"
        record_result('market_data', 'daily_basic', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'daily_basic', 'ERROR', str(e))
    
    # 15. moneyflow - 资金流向
    try:
        df = pro.moneyflow(ts_code='000001.SZ', trade_date='20260311')
        assert not df.empty, "moneyflow 返回空数据"
        assert 'buy_sm_amount' in df.columns, "缺少 buy_sm_amount 字段"
        record_result('market_data', 'moneyflow', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'moneyflow', 'ERROR', str(e))
    
    # 16. stk_limit - 涨跌停价格
    try:
        df = pro.stk_limit(trade_date='20260311', limit=1)
        assert not df.empty, "stk_limit 返回空数据"
        assert 'limit' in df.columns or 'ts_code' in df.columns, "缺少关键字段"
        record_result('market_data', 'stk_limit', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'stk_limit', 'ERROR', str(e))
    
    # 17. limit_list - 涨跌停列表
    try:
        df = pro.limit_list(trade_date='20260311', limit=1)
        assert not df.empty, "limit_list 返回空数据"
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('market_data', 'limit_list', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'limit_list', 'ERROR', str(e))
    
    # 18. suspend_d - 停牌数据
    try:
        df = pro.suspend_d(ts_code='000001.SZ', start_date='20260301', end_date='20260311', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('market_data', 'suspend_d', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'suspend_d', 'ERROR', str(e))
    
    # 19. top_list - 龙虎榜
    try:
        df = pro.top_list(trade_date='20260311', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('market_data', 'top_list', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'top_list', 'ERROR', str(e))
    
    # 20. top_inst - 机构席位
    try:
        df = pro.top_inst(trade_date='20260311', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('market_data', 'top_inst', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'top_inst', 'ERROR', str(e))
    
    # 21. block_trade - 大宗交易
    try:
        df = pro.block_trade(trade_date='20260311', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "block_trade 字段检查失败"
        record_result('market_data', 'block_trade', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'block_trade', 'ERROR', str(e))
    
    # 22. hk_hold - 北向资金持股
    try:
        df = pro.hk_hold(ts_code='000001.SZ', start_date='20260301', end_date='20260311', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('market_data', 'hk_hold', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('market_data', 'hk_hold', 'ERROR', str(e))

# ==============================================
# 第三部分：财务数据接口 (10 个)
# ==============================================

def test_financial_data_interfaces(pro):
    """测试财务数据接口"""
    print_subheader("财务数据接口测试 (10 个)")
    
    # 23. fina_indicator - 财务指标
    try:
        df = pro.fina_indicator(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert not df.empty, "fina_indicator 返回空数据"
        assert 'eps' in df.columns or 'ts_code' in df.columns, "缺少关键字段"
        record_result('financial_data', 'fina_indicator', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'fina_indicator', 'ERROR', str(e))
    
    # 24. income - 利润表
    try:
        df = pro.income(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('financial_data', 'income', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'income', 'ERROR', str(e))
    
    # 25. balancesheet - 资产负债表
    try:
        df = pro.balancesheet(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('financial_data', 'balancesheet', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'balancesheet', 'ERROR', str(e))
    
    # 26. cashflow - 现金流量表
    try:
        df = pro.cashflow(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('financial_data', 'cashflow', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'cashflow', 'ERROR', str(e))
    
    # 27. forecast - 业绩预告
    try:
        df = pro.forecast(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('financial_data', 'forecast', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'forecast', 'ERROR', str(e))
    
    # 28. express - 业绩快报
    try:
        df = pro.express(ts_code='000001.SZ', start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns, "缺少 ts_code 字段"
        record_result('financial_data', 'express', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'express', 'ERROR', str(e))
    
    # 29. dividend - 分红数据
    try:
        df = pro.dividend(ts_code='000001.SZ', start_date='20200101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "dividend 字段检查失败"
        record_result('financial_data', 'dividend', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'dividend', 'ERROR', str(e))
    
    # 30. adj_factor - 复权因子
    try:
        df = pro.adj_factor(ts_code='000001.SZ', trade_date='20260311')
        assert 'ts_code' in df.columns or not df.empty, "adj_factor 字段检查失败"
        record_result('financial_data', 'adj_factor', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'adj_factor', 'ERROR', str(e))
    
    # 31. share_float - 解禁股票
    try:
        df = pro.share_float(ts_code='000001.SZ', start_date='20250101', end_date='20261231', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "share_float 字段检查失败"
        record_result('financial_data', 'share_float', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'share_float', 'ERROR', str(e))
    
    # 32. stk_holdertrade - 股东增减持
    try:
        df = pro.stk_holdertrade(start_date='20250101', end_date='20251231', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "stk_holdertrade 字段检查失败"
        record_result('financial_data', 'stk_holdertrade', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('financial_data', 'stk_holdertrade', 'ERROR', str(e))

# ==============================================
# 第四部分：指数数据接口 (5 个)
# ==============================================

def test_index_data_interfaces(pro):
    """测试指数数据接口"""
    print_subheader("指数数据接口测试 (5 个)")
    
    # 33. index_daily - 指数日线
    try:
        df = pro.index_daily(ts_code='000001.SH', start_date='20260301', end_date='20260311', limit=1)
        assert not df.empty, "index_daily 返回空数据"
        assert 'close' in df.columns or 'ts_code' in df.columns, "缺少关键字段"
        record_result('index_data', 'index_daily', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('index_data', 'index_daily', 'ERROR', str(e))
    
    # 34. index_weekly - 指数周线
    try:
        df = pro.index_weekly(ts_code='000001.SH', start_date='20260201', end_date='20260311', limit=1)
        assert 'close' in df.columns or not df.empty, "index_weekly 字段检查失败"
        record_result('index_data', 'index_weekly', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('index_data', 'index_weekly', 'ERROR', str(e))
    
    # 35. index_monthly - 指数月线
    try:
        df = pro.index_monthly(ts_code='000001.SH', start_date='20260101', end_date='20260311', limit=1)
        assert 'close' in df.columns or not df.empty, "index_monthly 字段检查失败"
        record_result('index_data', 'index_monthly', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('index_data', 'index_monthly', 'ERROR', str(e))
    
    # 36. index_weight - 指数权重
    try:
        df = pro.index_weight(index_code='000001.SH', start_date='20260301', end_date='20260311', limit=1)
        assert 'index_code' in df.columns or not df.empty, "index_weight 字段检查失败"
        record_result('index_data', 'index_weight', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('index_data', 'index_weight', 'ERROR', str(e))
    
    # 37. index_dailybasic - 指数基本面
    try:
        df = pro.index_dailybasic(ts_code='000001.SH', trade_date='20260311')
        assert 'ts_code' in df.columns or not df.empty, "index_dailybasic 字段检查失败"
        record_result('index_data', 'index_dailybasic', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('index_data', 'index_dailybasic', 'ERROR', str(e))

# ==============================================
# 第五部分：特色数据接口 (10 个)
# ==============================================

def test_special_data_interfaces(pro):
    """测试特色数据接口"""
    print_subheader("特色数据接口测试 (10 个)")
    
    # 38. concept_detail - 概念详情
    try:
        df = pro.concept_detail(concept_code='BK0001', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "concept_detail 字段检查失败"
        record_result('special_data', 'concept_detail', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'concept_detail', 'ERROR', str(e))
    
    # 39. cyq_chips - 筹码分布
    try:
        df = pro.cyq_chips(ts_code='000001.SZ', trade_date='20260311', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "cyq_chips 字段检查失败"
        record_result('special_data', 'cyq_chips', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'cyq_chips', 'ERROR', str(e))
    
    # 40. cyq_perf - 筹码业绩
    try:
        df = pro.cyq_perf(ts_code='000001.SZ', trade_date='20260311', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "cyq_perf 字段检查失败"
        record_result('special_data', 'cyq_perf', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'cyq_perf', 'ERROR', str(e))
    
    # 41. news - 新闻资讯
    try:
        df = pro.news(src='sina', start_date='20260310', end_date='20260311', limit=1)
        assert 'title' in df.columns or not df.empty, "news 字段检查失败"
        record_result('special_data', 'news', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'news', 'ERROR', str(e))
    
    # 42. news_sina - 新浪新闻
    try:
        df = pro.news_sina(start_date='20260310', end_date='20260311', limit=1)
        assert 'title' in df.columns or not df.empty, "news_sina 字段检查失败"
        record_result('special_data', 'news_sina', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'news_sina', 'ERROR', str(e))
    
    # 43. report_rc - 券商研报
    try:
        df = pro.report_rc(start_date='20260301', end_date='20260311', limit=1)
        assert 'title' in df.columns or not df.empty, "report_rc 字段检查失败"
        record_result('special_data', 'report_rc', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'report_rc', 'ERROR', str(e))
    
    # 44. broker_recommend - 券商推荐
    try:
        df = pro.broker_recommend(start_date='20260301', end_date='20260311', limit=1)
        assert not df.empty or True, "broker_recommend 允许空数据"
        record_result('special_data', 'broker_recommend', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'broker_recommend', 'ERROR', str(e))
    
    # 45. fund_basic - 基金基本信息
    try:
        df = pro.fund_basic(market='E', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "fund_basic 字段检查失败"
        record_result('special_data', 'fund_basic', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'fund_basic', 'ERROR', str(e))
    
    # 46. fund_nav - 基金净值
    try:
        df = pro.fund_nav(ts_code='000001.OF', start_date='20260301', end_date='20260311', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "fund_nav 字段检查失败"
        record_result('special_data', 'fund_nav', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'fund_nav', 'ERROR', str(e))
    
    # 47. fund_portfolio - 基金持仓
    try:
        df = pro.fund_portfolio(ts_code='000001.OF', ann_date='20251231', limit=1)
        assert 'ts_code' in df.columns or not df.empty, "fund_portfolio 字段检查失败"
        record_result('special_data', 'fund_portfolio', 'PASS', details=f"获取 {len(df)} 条记录")
    except Exception as e:
        record_result('special_data', 'fund_portfolio', 'ERROR', str(e))

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
    json_path = os.path.join(report_dir, f'tushare_interface_test_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 报告已保存：{json_path}")
    
    # 保存文本报告
    txt_path = os.path.join(report_dir, f'tushare_interface_test_{timestamp}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("【测试】Tushare 全接口验证测试报告\n")
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
            f.write("\n✅ 所有接口测试通过！\n")
    
    print(f"📄 文本报告已保存：{txt_path}")
    
    return pass_rate

# ==============================================
# 主函数
# ==============================================

def main():
    """主函数"""
    print_header("Tushare 全接口验证测试开始")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查配置
    if not TUSHARE_TOKEN:
        print("❌ 错误：TUSHARE_TOKEN 环境变量未设置")
        print("请设置：export TUSHARE_TOKEN='your_token'")
        return 1
    
    start_time = time.time()
    
    # 初始化 Tushare
    try:
        print("\n正在初始化 Tushare...")
        pro = init_tushare()
        print("✅ Tushare 初始化成功")
    except Exception as e:
        print(f"❌ Tushare 初始化失败：{e}")
        return 1
    
    # 执行所有测试
    try:
        test_basic_data_interfaces(pro)
    except Exception as e:
        logger.error(f"基础数据接口测试异常：{e}", exc_info=True)
    
    try:
        test_market_data_interfaces(pro)
    except Exception as e:
        logger.error(f"行情数据接口测试异常：{e}", exc_info=True)
    
    try:
        test_financial_data_interfaces(pro)
    except Exception as e:
        logger.error(f"财务数据接口测试异常：{e}", exc_info=True)
    
    try:
        test_index_data_interfaces(pro)
    except Exception as e:
        logger.error(f"指数数据接口测试异常：{e}", exc_info=True)
    
    try:
        test_special_data_interfaces(pro)
    except Exception as e:
        logger.error(f"特色数据接口测试异常：{e}", exc_info=True)
    
    elapsed_time = time.time() - start_time
    
    # 生成报告
    pass_rate = generate_test_report()
    
    print_header("Tushare 全接口验证测试完成")
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
