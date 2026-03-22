# -*- coding: utf-8 -*-
"""
vnpy数据加载器 v2.2 - 正确映射字段名
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VnpyDataLoader:
    """
    vnpy数据加载器 v2.2
    
    读取本地parquet数据，正确映射字段名
    """
    
    def __init__(self, data_dir: str = "/data/agents/master/data_all_stocks",
                 public_dir: str = "/data/agents/master/data"):
        self.data_dir = Path(data_dir)
        self.public_dir = Path(public_dir)
        
        # 缓存
        self._limit_cache = None
    
    def get_main_board_stocks(self) -> List[str]:
        """获取主板股票列表（00/60开头）"""
        stocks = [d.name for d in self.data_dir.iterdir() 
                 if d.is_dir() and d.name.startswith(('00', '60'))]
        return sorted(stocks)
    
    def load_stock_daily(self, ts_code: str, start_date: str = None, 
                         end_date: str = None) -> pd.DataFrame:
        """加载单只股票日线数据"""
        stock_dir = self.data_dir / ts_code
        daily_path = stock_dir / "daily.parquet"
        
        if not daily_path.exists():
            return pd.DataFrame()
        
        df = pd.read_parquet(daily_path)
        
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
        
        正确映射涨跌停数据字段：
        - fd_amount -> order_amount (封单金额)
        - float_mv -> float_market_cap (流通市值)
        - open_times -> break_limit_times (炸板次数)
        - up_stat -> up_down_times (连板高度，提取数字)
        - first_time -> first_limit_time (封板时间)
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
        
        result = pd.concat(all_data, ignore_index=True)
        
        # 合并涨跌停数据
        limit = self.load_limit_data(date, date)
        if not limit.empty:
            # 创建映射后的列
            limit_mapping = {
                'fd_amount': 'order_amount',
                'float_mv': 'float_market_cap',
                'open_times': 'break_limit_times',
                'first_time': 'first_limit_time',
                'limit_times': 'limit_times',
                'limit': 'limit_status'
            }
            
            # 选择存在的列
            limit_cols = ['ts_code']
            for src_col, dst_col in limit_mapping.items():
                if src_col in limit.columns:
                    limit_cols.append(src_col)
            
            limit_subset = limit[limit_cols].copy()
            
            # 重命名列
            for src_col, dst_col in limit_mapping.items():
                if src_col in limit_subset.columns:
                    limit_subset = limit_subset.rename(columns={src_col: dst_col})
            
            # 处理连板高度（从"5/5"提取数字）
            if 'up_stat' in limit.columns:
                limit_subset['up_down_times'] = limit['up_stat'].apply(
                    lambda x: int(str(x).split('/')[0]) if pd.notna(x) and '/' in str(x) else 0
                )
            
            result = result.merge(limit_subset, on='ts_code', how='left')
            
            # 填充默认值
            default_values = {
                'order_amount': 0,
                'float_market_cap': 0,
                'break_limit_times': 0,
                'up_down_times': 0,
                'first_limit_time': '09:30',
                'limit_times': 0
            }
            for col, default in default_values.items():
                if col in result.columns:
                    result[col] = result[col].fillna(default)
        
        # 添加其他默认字段
        if 'turnover_ratio' in result.columns:
            result['turnover_ratio'] = result['turnover_ratio'].fillna(0)
        
        return result
    
    def load_limit_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """加载涨跌停数据"""
        if self._limit_cache is None:
            limit_path = self.public_dir / "limit_list_d.parquet"
            if limit_path.exists():
                self._limit_cache = pd.read_parquet(limit_path)
            else:
                self._limit_cache = pd.DataFrame()
        
        df = self._limit_cache
        if df.empty:
            return df
        
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
            all_dates = set()
            for ts_code in self.get_main_board_stocks()[:50]:
                df = self.load_stock_daily(ts_code, start_date, end_date)
                if not df.empty:
                    all_dates.update(df['trade_date'].tolist())
            return sorted(list(all_dates))
        return sorted(limit_data['trade_date'].unique().tolist())


if __name__ == "__main__":
    loader = VnpyDataLoader()
    
    daily = loader.load_all_stocks_daily("20231201")
    print(f"20231201数据: {len(daily)}条")
    if not daily.empty:
        # 检查打板策略需要的字段
        required_fields = ['ts_code', 'close', 'pct_chg', 'order_amount', 'float_market_cap', 
                          'break_limit_times', 'up_down_times', 'first_limit_time']
        print(f"打板策略需要的字段:")
        for f in required_fields:
            exists = f in daily.columns
            print(f"  {f}: {'✅' if exists else '❌'}")
