#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助数据源抓取模块
用于补充 Tushare 权限不够的接口（爬虫实现）

数据源：
- 同花顺（THS）
- 东方财富（DC）
- 通达信（TDX）
- 开盘啦（KPL）
"""

import os
import sys
import time
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# 日志配置
logger = logging.getLogger("auxiliary_data")
logger.setLevel(logging.INFO)

# 存储路径
AUX_DATA_DIR = "/mnt/data/quant_data_project/data/auxiliary"
os.makedirs(AUX_DATA_DIR, exist_ok=True)


class AuxiliaryDataFetcher:
    """辅助数据源抓取器（爬虫实现）"""
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        logger.info("✅ 辅助数据源抓取器初始化完成")
    
    # ============================================ 【资金流向类】 ============================================
    def fetch_ths_moneyflow(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        同花顺资金流向（板块/行业）
        
        数据源：同花顺财经
        接口：http://data.10jqka.com.cn/ajax/zhangting/
        
        参数：
            date: 日期（YYYYMMDD），默认今天
        
        返回：
            DataFrame 包含：板块名、涨跌幅、主力净流入、超大单流入等
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        try:
            # 同花顺资金流向 API（示例）
            url = f"http://data.10jqka.com.cn/ajax/moneyflow/{date}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data and 'data' in data:
                df = pd.DataFrame(data['data'])
                
                # 保存
                output_path = os.path.join(AUX_DATA_DIR, f"ths_moneyflow_{date}.csv")
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 同花顺资金流向已保存：{output_path}")
                
                return df
            else:
                logger.warning(f"⚠️ 同花顺资金流向数据为空：{date}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 同花顺资金流向抓取失败：{e}")
            return None
    
    def fetch_dc_moneyflow(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        东方财富资金流向（大盘/个股）
        
        数据源：东方财富网
        接口：http://push2.eastmoney.com/api/qt/clist/get
        
        参数：
            date: 日期（YYYYMMDD），默认今天
        
        返回：
            DataFrame 包含：代码、名称、主力净流入、超大单、大单等
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        try:
            # 东方财富资金流向 API
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '500',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f62',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                'fields': 'f12,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f206',
                '_': str(int(time.time() * 1000))
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data and 'data' in data and 'diff' in data['data']:
                df = pd.DataFrame(data['data']['diff'])
                
                # 重命名列
                df.rename(columns={
                    'f12': 'ts_code',
                    'f14': 'name',
                    'f62': 'main_net_inflow',
                    'f184': 'main_net_inflow_rate',
                }, inplace=True)
                
                # 保存
                output_path = os.path.join(AUX_DATA_DIR, f"dc_moneyflow_{date}.csv")
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 东方财富资金流向已保存：{output_path}")
                
                return df
            else:
                logger.warning(f"⚠️ 东方财富资金流向数据为空：{date}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 东方财富资金流向抓取失败：{e}")
            return None
    
    # ============================================ 【板块概念类】 ============================================
    def fetch_ths_concept(self) -> Optional[pd.DataFrame]:
        """
        同花顺概念板块
        
        数据源：同花顺财经
        接口：http://q.10jqka.com.cn/gn/
        
        返回：
            DataFrame 包含：概念代码、名称、涨跌幅、成分股数等
        """
        try:
            # 同花顺概念列表
            url = "http://q.10jqka.com.cn/gn/index/field/addtime/order/desc/page/{page}/ajax/1/"
            
            all_dfs = []
            for page in range(1, 11):  # 假设最多 10 页
                try:
                    response = self.session.get(url.format(page=page), timeout=30)
                    response.raise_for_status()
                    
                    # 解析 HTML（简化处理）
                    # 实际需要用 BeautifulSoup 解析
                    logger.info(f"📊 抓取同花顺概念第{page}页")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 同花顺概念第{page}页抓取失败：{e}")
                    break
            
            if all_dfs:
                df = pd.concat(all_dfs, ignore_index=True)
                output_path = os.path.join(AUX_DATA_DIR, "ths_concept.csv")
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 同花顺概念板块已保存：{output_path}")
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ 同花顺概念板块抓取失败：{e}")
            return None
    
    def fetch_dc_concept(self) -> Optional[pd.DataFrame]:
        """
        东方财富概念板块
        
        数据源：东方财富网
        接口：http://nufm.dfcfw.com/EM_Fund2099/QF_StockJs/
        
        返回：
            DataFrame 包含：概念代码、名称、涨跌幅等
        """
        try:
            # 东方财富概念列表（简化实现）
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '500',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'b:BK0900',
                'fields': 'f12,f14,f3,f4,f62',
                '_': str(int(time.time() * 1000))
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data and 'data' in data and 'diff' in data['data']:
                df = pd.DataFrame(data['data']['diff'])
                
                df.rename(columns={
                    'f12': 'concept_code',
                    'f14': 'concept_name',
                    'f3': 'change_pct',
                }, inplace=True)
                
                output_path = os.path.join(AUX_DATA_DIR, "dc_concept.csv")
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 东方财富概念板块已保存：{output_path}")
                
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ 东方财富概念板块抓取失败：{e}")
            return None
    
    # ============================================ 【情绪打板类】 ============================================
    def fetch_limit_break(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        炸板数据
        
        数据源：同花顺/爬虫
        参数：
            date: 日期（YYYYMMDD）
        
        返回：
            DataFrame 包含：代码、名称、涨停价、炸板次数等
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        try:
            # 炸板数据（通过涨跌停数据计算）
            # 实际实现需要解析涨停池和炸板池
            logger.info(f"📊 抓取炸板数据：{date}")
            
            # 简化实现：返回空 DataFrame
            df = pd.DataFrame(columns=[
                'ts_code', 'name', 'limit_price', 'break_times', 'last_limit_time'
            ])
            
            output_path = os.path.join(AUX_DATA_DIR, f"limit_break_{date}.csv")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"⚠️ 炸板数据待实现：{output_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 炸板数据抓取失败：{e}")
            return None
    
    def fetch_link_board(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        连板天梯
        
        数据源：同花顺/爬虫
        参数：
            date: 日期（YYYYMMDD）
        
        返回：
            DataFrame 包含：连板数、代码、名称、所属概念等
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        try:
            logger.info(f"📊 抓取连板天梯：{date}")
            
            # 简化实现
            df = pd.DataFrame(columns=[
                'link_count', 'ts_code', 'name', 'concept', 'first_limit_time'
            ])
            
            output_path = os.path.join(AUX_DATA_DIR, f"link_board_{date}.csv")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"⚠️ 连板天梯待实现：{output_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 连板天梯抓取失败：{e}")
            return None
    
    # ============================================ 【热榜类】 ============================================
    def fetch_ths_hot(self) -> Optional[pd.DataFrame]:
        """
        同花顺热榜
        
        数据源：同花顺 App
        接口：http://search.10jqka.com.cn/gateway/urp/v7/landing/getDataList
        
        返回：
            DataFrame 包含：排名、代码、名称、热度等
        """
        try:
            url = "http://search.10jqka.com.cn/gateway/urp/v7/landing/getDataList"
            params = {
                'query': '热榜',
                'condition': '[{"type":"hot_list"}]',
                'perpage': '50',
                'page': '1',
                'source': 'ths_pc',
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data and 'data' in data:
                df = pd.DataFrame(data['data'])
                
                output_path = os.path.join(AUX_DATA_DIR, "ths_hot.csv")
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 同花顺热榜已保存：{output_path}")
                
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ 同花顺热榜抓取失败：{e}")
            return None
    
    def fetch_dc_hot(self) -> Optional[pd.DataFrame]:
        """
        东方财富热榜
        
        数据源：东方财富 App
        
        返回：
            DataFrame 包含：排名、代码、名称、热度等
        """
        try:
            # 东方财富热榜（简化实现）
            logger.info("📊 抓取东方财富热榜...")
            
            df = pd.DataFrame(columns=['rank', 'ts_code', 'name', 'hot_value'])
            
            output_path = os.path.join(AUX_DATA_DIR, "dc_hot.csv")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"⚠️ 东方财富热榜待实现：{output_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 东方财富热榜抓取失败：{e}")
            return None
    
    # ============================================ 【Tushare 补充接口】 ============================================
    def fetch_tushare_supplement(self, pro, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Tushare 补充接口（业绩预告、快报、分红）
        
        参数：
            pro: Tushare pro API 实例
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        返回：
            Dict 包含各个接口的 DataFrame
        """
        results = {}
        
        # 1. 业绩预告
        try:
            logger.info("📊 抓取业绩预告...")
            df_forecast = pro.forecast(start_date=start_date, end_date=end_date)
            if not df_forecast.empty:
                results['forecast'] = df_forecast
                logger.info(f"✅ 业绩预告：{len(df_forecast)}条")
        except Exception as e:
            logger.warning(f"⚠️ 业绩预告抓取失败：{e}")
        
        # 2. 业绩快报
        try:
            logger.info("📊 抓取业绩快报...")
            df_express = pro.express(start_date=start_date, end_date=end_date)
            if not df_express.empty:
                results['express'] = df_express
                logger.info(f"✅ 业绩快报：{len(df_express)}条")
        except Exception as e:
            logger.warning(f"⚠️ 业绩快报抓取失败：{e}")
        
        # 3. 分红送股
        try:
            logger.info("📊 抓取分红送股...")
            df_dividend = pro.dividend(start_date=start_date, end_date=end_date)
            if not df_dividend.empty:
                results['dividend'] = df_dividend
                logger.info(f"✅ 分红送股：{len(df_dividend)}条")
        except Exception as e:
            logger.warning(f"⚠️ 分红送股抓取失败：{e}")
        
        return results


# ============================================ 【主函数】 ============================================
def fetch_all_auxiliary(pro, start_date: str, end_date: str):
    """
    抓取全部辅助数据
    
    参数：
        pro: Tushare pro API 实例
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
    """
    logger.info("=" * 80)
    logger.info("🚀 开始抓取辅助数据")
    logger.info(f"⏰ 时间范围：{start_date} - {end_date}")
    logger.info("=" * 80)
    
    fetcher = AuxiliaryDataFetcher()
    
    # 1. 资金流向类
    logger.info("\n📊 【资金流向类】")
    fetcher.fetch_ths_moneyflow()
    fetcher.fetch_dc_moneyflow()
    
    # 2. 板块概念类
    logger.info("\n📊 【板块概念类】")
    fetcher.fetch_ths_concept()
    fetcher.fetch_dc_concept()
    
    # 3. 情绪打板类
    logger.info("\n📊 【情绪打板类】")
    fetcher.fetch_limit_break()
    fetcher.fetch_link_board()
    
    # 4. 热榜类
    logger.info("\n📊 【热榜类】")
    fetcher.fetch_ths_hot()
    fetcher.fetch_dc_hot()
    
    # 5. Tushare 补充接口
    logger.info("\n📊 【Tushare 补充接口】")
    supplement_results = fetcher.fetch_tushare_supplement(pro, start_date, end_date)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 辅助数据抓取完成")
    logger.info("=" * 80)
    
    return True


# ============================================ 【入口】 ============================================
if __name__ == "__main__":
    # 测试
    fetch_all_auxiliary(None, "20260301", "20260311")
