#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==============================================
# 【测试】实时数据源集成测试
# ==============================================
# 功能：测试 AkShare、新浪、东财实时数据源
# 测试项：
#   1. AkShare 实时行情
#   2. AkShare 板块实时
#   3. AkShare 热榜
#   4. 新浪实时行情
#   5. 新浪分钟线
#   6. 东财资金流向
#   7. 东财板块排名
#   8. 数据源切换机制
# ==============================================

import sys
import os
import logging
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_sources import (
    AkShareRealtimeSource,
    SinaCrawlerSource,
    EastmoneyCrawlerSource,
    RealtimeDataManager,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """测试结果记录"""
    def __init__(self):
        self.results = []
    
    def add(self, test_name: str, success: bool, message: str, data=None):
        self.results.append({
            'test_name': test_name,
            'success': success,
            'message': message,
            'data': data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed
        
        summary = "\n" + "=" * 70 + "\n"
        summary += f"【实时数据源测试报告】\n"
        summary += "=" * 70 + "\n"
        summary += f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"总计：{total} 项 | 通过：{passed} 项 | 失败：{failed} 项 | 通过率：{passed/total*100:.1f}%\n"
        summary += "=" * 70 + "\n\n"
        
        for r in self.results:
            status = "✅" if r['success'] else "❌"
            summary += f"{status} {r['test_name']}: {r['message']}\n"
        
        return summary


def test_akshare_realtime_spot(result: TestResult):
    """测试 AkShare 实时行情"""
    test_name = "AkShare 实时行情"
    try:
        source = AkShareRealtimeSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_realtime_spot()
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}只股票", df.head())
            logger.info(f"✅ {test_name}: {len(df)}只股票")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_akshare_industry_board(result: TestResult):
    """测试 AkShare 行业板块"""
    test_name = "AkShare 行业板块实时"
    try:
        source = AkShareRealtimeSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_industry_board_realtime()
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}个板块", df.head())
            logger.info(f"✅ {test_name}: {len(df)}个板块")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_akshare_hot_rank(result: TestResult):
    """测试 AkShare 热榜"""
    test_name = "AkShare 股票热榜"
    try:
        source = AkShareRealtimeSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_hot_rank()
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}只股票", df.head())
            logger.info(f"✅ {test_name}: {len(df)}只股票")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_sina_realtime(result: TestResult):
    """测试新浪实时行情"""
    test_name = "新浪实时行情"
    test_codes = ["000001.SZ", "600519.SH", "300750.SZ"]
    
    try:
        source = SinaCrawlerSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        success_count = 0
        results = []
        
        for code in test_codes:
            data = source.get_realtime_by_code(code)
            if data:
                success_count += 1
                results.append(f"{code}: {data.get('name', 'N/A')} ¥{data.get('price', 0):.2f}")
        
        if success_count > 0:
            result.add(test_name, True, f"成功{success_count}/{len(test_codes)}", "; ".join(results))
            logger.info(f"✅ {test_name}: {success_count}/{len(test_codes)}")
        else:
            result.add(test_name, False, "全部失败")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_sina_minute_data(result: TestResult):
    """测试新浪分钟线"""
    test_name = "新浪分钟线数据"
    try:
        source = SinaCrawlerSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_minute_data("000001.SZ", period='5', count=10)
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}条", df.head())
            logger.info(f"✅ {test_name}: {len(df)}条")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_eastmoney_moneyflow(result: TestResult):
    """测试东财资金流向"""
    test_name = "东财资金流向"
    try:
        source = EastmoneyCrawlerSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        data = source.get_stock_moneyflow("000001")
        
        if data:
            msg = f"主力净流入:{data['main_net_inflow']:.2f}万元"
            result.add(test_name, True, msg, data)
            logger.info(f"✅ {test_name}: {msg}")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_eastmoney_board_rank(result: TestResult):
    """测试东财板块排名"""
    test_name = "东财行业板块排名"
    try:
        source = EastmoneyCrawlerSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_industry_board_rank(top_n=10)
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}个板块", df.head())
            logger.info(f"✅ {test_name}: {len(df)}个板块")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_eastmoney_main_money(result: TestResult):
    """测试东财主力资金排名"""
    test_name = "东财主力资金排名"
    try:
        source = EastmoneyCrawlerSource({})
        if not source.connect():
            result.add(test_name, False, "连接失败")
            return
        
        df = source.get_main_money_rank(top_n=10)
        
        if df is not None and not df.empty:
            result.add(test_name, True, f"成功获取{len(df)}只股票", df.head())
            logger.info(f"✅ {test_name}: {len(df)}只股票")
        else:
            result.add(test_name, False, "返回数据为空")
        
        source.disconnect()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def test_realtime_manager(result: TestResult):
    """测试实时数据管理器（优先级切换）"""
    test_name = "数据源优先级切换"
    test_codes = ["000001", "600519", "300750"]
    
    try:
        config = {
            'TUSHARE_TOKEN': '',  # 如有 Tushare Token 可填入
            'REALTIME_CACHE_TIMEOUT': 30,
        }
        
        manager = RealtimeDataManager(config)
        
        success_count = 0
        source_stats = {}
        
        for code in test_codes:
            data = manager.get_realtime_data(code)
            if data:
                success_count += 1
                source = data.get('source', 'unknown')
                source_stats[source] = source_stats.get(source, 0) + 1
        
        if success_count > 0:
            msg = f"成功{success_count}/{len(test_codes)} | 数据源分布：{source_stats}"
            result.add(test_name, True, msg, source_stats)
            logger.info(f"✅ {test_name}: {msg}")
        else:
            result.add(test_name, False, "全部失败")
        
        manager.disconnect_all()
    except Exception as e:
        result.add(test_name, False, f"异常：{str(e)}")
        logger.error(f"❌ {test_name}: {e}")


def main():
    """主测试函数"""
    print("=" * 70)
    print("【实时数据源集成测试】")
    print("=" * 70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    result = TestResult()
    
    # AkShare 测试
    print("📊 测试 AkShare 数据源...")
    test_akshare_realtime_spot(result)
    test_akshare_industry_board(result)
    test_akshare_hot_rank(result)
    
    # 新浪测试
    print("\n📊 测试新浪数据源...")
    test_sina_realtime(result)
    test_sina_minute_data(result)
    
    # 东财测试
    print("\n📊 测试东财数据源...")
    test_eastmoney_moneyflow(result)
    test_eastmoney_board_rank(result)
    test_eastmoney_main_money(result)
    
    # 管理器测试
    print("\n📊 测试数据源管理器...")
    test_realtime_manager(result)
    
    # 输出报告
    print(result.summary())
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'realtime_source_test_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 实时数据源测试报告\n\n")
        f.write(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(result.summary())
        f.write("\n\n## 详细数据\n\n")
        for r in result.results:
            f.write(f"### {r['test_name']}\n")
            f.write(f"- 状态：{'通过' if r['success'] else '失败'}\n")
            f.write(f"- 说明：{r['message']}\n")
            if r['data'] is not None:
                if isinstance(r['data'], pd.DataFrame):
                    try:
                        f.write(f"- 数据预览:\n{r['data'].to_markdown()}\n")
                    except:
                        f.write(f"- 数据预览:\n{r['data'].head().to_string()}\n")
                else:
                    f.write(f"- 数据：{r['data']}\n")
            f.write("\n")
    
    print(f"📄 测试报告已保存至：{report_path}")
    
    # 返回测试结果
    passed = sum(1 for r in result.results if r['success'])
    total = len(result.results)
    
    if passed == total:
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
