# -*- coding: utf-8 -*-
"""
vnpy数据加载器 - 读取parquet数据转换成vnpy格式
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VnpyDataLoader:
    """
    vnpy数据加载器
    
    读取本地parquet数据，转换成vnpy需要的格式
    """
    
    def __init__(self, data_dir: str = "/data/agents/master/data_all_stocks",
                 public_dir: str = "/data/agents/master/data"):
        self.data_dir = Path(data_dir)
        self.public_dir = Path(public_dir)
    
    def get_main_board_stocks(self) -> List[str]:
        """获取主板股票列表（00/60开头）"""
        stocks = [d.name for d in self.data_dir.iterdir() 
                 if d.is_dir() and d.name.startswith(('00', '60'))]
        return sorted(stocks)
    
    def load_stock_daily(self, ts_code: str, start_date: str = None, 
                         end_date: str = None) -> pd.DataFrame:
        """
        加载单只股票日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end_date: 结束日期
        """
        stock_dir = self.data_dir / ts_code
        daily_path = stock_dir / "daily.parquet"
        
        if not daily_path.exists():
            return pd.DataFrame()
        
        df = pd.read_parquet(daily_path)
        
        # 日期格式处理
        if start_date:
            start_date = start_date.replace('-', '')
            df = df[df['trade_date'] >= start_date]
        if end_date:
            end_date = end_date.replace('-', '')
            df = df[df['trade_date'] <= end_date]
        
        return df.reset_index(drop=True)
    
    def load_all_stocks_daily(self, date: str) -> pd.DataFrame:
        """
        加载当日所有股票数据
        
        Args:
            date: 日期 (YYYYMMDD 或 YYYY-MM-DD)
        """
        date = date.replace('-', '')
        all_data = []
        stock_list = self.get_main_board_stocks()
        
        for ts_code in stock_list:
            stock_dir = self.data_dir / ts_code
            daily_path = stock_dir / "daily.parquet"
            
            if daily_path.exists():
                try:
                    df = pd.read_parquet(daily_path)
                    df = df[df['trade_date'] == date]
                    if not df.empty:
                        df['ts_code'] = ts_code
                        all_data.append(df)
                except:
                    continue
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    def load_limit_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """加载涨跌停数据"""
        limit_path = self.public_dir / "stk_limit.parquet"
        if not limit_path.exists():
            return pd.DataFrame()
        
        df = pd.read_parquet(limit_path)
        
        if start_date:
            start_date = start_date.replace('-', '')
            df = df[df['trade_date'] >= start_date]
        if end_date:
            end_date = end_date.replace('-', '')
            df = df[df['trade_date'] <= end_date]
        
        return df
    
    def load_lhb_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """加载龙虎榜数据"""
        lhb_path = self.public_dir / "limit_list_d.parquet"
        if not lhb_path.exists():
            return pd.DataFrame()
        
        df = pd.read_parquet(lhb_path)
        
        if start_date:
            start_date = start_date.replace('-', '')
            df = df[df['trade_date'] >= start_date]
        if end_date:
            end_date = end_date.replace('-', '')
            df = df[df['trade_date'] <= end_date]
        
        return df
    
    def get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表"""
        limit_data = self.load_limit_data(start_date, end_date)
        if limit_data.empty:
            return []
        return sorted(limit_data['trade_date'].unique().tolist())


if __name__ == "__main__":
    loader = VnpyDataLoader()
    stocks = loader.get_main_board_stocks()
    print(f"主板股票数量: {len(stocks)}")
