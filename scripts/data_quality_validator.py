#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【数据验证与质检系统】- 完整版
功能：数据完整性检查、准确性验证、异常检测、质量报告生成
作者：master-quant 生态
版本：v1.0
创建时间：2026-03-12
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_validator import DataValidator

# ==============================================
# 配置常量
# ==============================================

class DataQualityConfig:
    """数据质量检查配置"""
    
    # 数据目录
    DATA_DIR = Path("/home/admin/.openclaw/agents/master/data_all_stocks")
    STOCK_BASIC_FILE = Path("/home/admin/.openclaw/agents/master/data/stock_basic.csv")
    OUTPUT_DIR = Path("/home/admin/.openclaw/agents/master/data/quality_reports")
    
    # 必填字段
    REQUIRED_FIELDS = {
        'base': ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'],
        '打板策略': ['ts_code', 'trade_date', 'close', 'vol', 'limit', 'up_down_times', 'order_amount'],
        '缩量潜伏策略': ['ts_code', 'trade_date', 'close', 'vol', 'high', 'low'],
        '板块轮动策略': ['ts_code', 'trade_date', 'close', 'vol', 'industry']
    }
    
    # 价格有效性范围
    PRICE_MIN = 0.01
    PRICE_MAX = 10000.0
    
    # 涨跌幅阈值
    PRICE_CHANGE_WARNING = 0.20  # 20%
    
    # 成交量异常阈值
    VOL_CHANGE_WARNING = 10.0  # 10 倍
    
    # 最小记录数要求
    MIN_RECORDS_PER_STOCK = 60  # 约 3 个月交易日
    
    # 输出配置
    REPORT_FORMAT = 'markdown'
    MAX_ERROR_DETAILS = 100


# ==============================================
# 数据质量检查器
# ==============================================

class DataQualityChecker:
    """数据质量综合检查器"""
    
    def __init__(self, config: DataQualityConfig = None):
        self.config = config or DataQualityConfig()
        self.validator = DataValidator()
        self.results = {}
        
        # 创建输出目录
        self.config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_stock_list(self) -> pd.DataFrame:
        """加载股票列表"""
        if not self.config.STOCK_BASIC_FILE.exists():
            raise FileNotFoundError(f"股票列表文件不存在：{self.config.STOCK_BASIC_FILE}")
        
        df = pd.read_csv(self.config.STOCK_BASIC_FILE)
        return df
    
    def load_stock_data(self, ts_code: str, data_type: str = 'daily') -> Optional[pd.DataFrame]:
        """加载单只股票数据"""
        stock_dir = self.config.DATA_DIR / ts_code
        data_file = stock_dir / f"{data_type}.parquet"
        
        if not data_file.exists():
            return None
        
        try:
            df = pd.read_parquet(data_file)
            return df
        except Exception as e:
            print(f"⚠️  加载 {ts_code} 数据失败：{e}")
            return None
    
    def check_stock_list_completeness(self, official_count: int = None) -> Dict[str, Any]:
        """
        1.1 股票列表完整性检查（对比 Tushare 官方）
        """
        result = {
            'check_name': '股票列表完整性',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_complete': True,
            'local_count': 0,
            'official_count': official_count,
            'missing_stocks': [],
            'extra_stocks': [],
            'details': []
        }
        
        try:
            # 获取本地股票列表
            local_stocks = set()
            if self.config.DATA_DIR.exists():
                for item in self.config.DATA_DIR.iterdir():
                    if item.is_dir() and '.' in item.name:
                        local_stocks.add(item.name)
            
            result['local_count'] = len(local_stocks)
            
            # 加载股票基本信息
            stock_basic = self.load_stock_list()
            official_stocks = set(stock_basic['ts_code'].tolist())
            result['official_count'] = len(official_stocks)
            
            # 对比差异
            missing = official_stocks - local_stocks
            extra = local_stocks - official_stocks
            
            result['missing_stocks'] = sorted(list(missing))[:100]  # 最多显示 100 个
            result['extra_stocks'] = sorted(list(extra))[:100]
            
            if missing:
                result['is_complete'] = False
                result['details'].append(f"❌ 缺失 {len(missing)} 只股票（显示前{min(len(missing), 100)}个）")
            
            if extra:
                result['details'].append(f"⚠️  多余 {len(extra)} 只股票（可能已退市）")
            
            result['completeness_rate'] = round(
                (len(official_stocks) - len(missing)) / len(official_stocks) * 100, 2
            ) if official_stocks else 0
            
        except Exception as e:
            result['is_complete'] = False
            result['error'] = str(e)
        
        return result
    
    def check_date_continuity(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        1.2 日期连续性检查（无缺失交易日）
        """
        result = {
            'check_name': '日期连续性',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_continuous': True,
            'total_days': 0,
            'expected_days': 0,
            'missing_days': [],
            'gap_periods': [],
            'continuity_rate': 0
        }
        
        if df is None or df.empty or 'trade_date' not in df.columns:
            result['is_continuous'] = False
            result['error'] = "数据为空或缺少 trade_date 列"
            return result
        
        try:
            # 转换日期
            df_dates = pd.to_datetime(df['trade_date'].astype(str)).dropna().unique()
            df_dates_sorted = sorted(df_dates)
            result['total_days'] = len(df_dates_sorted)
            
            if len(df_dates_sorted) < 2:
                result['error'] = "数据天数不足 2 天"
                return result
            
            # 计算预期交易日（去除周末）
            start_date = df_dates_sorted[0]
            end_date = df_dates_sorted[-1]
            all_days = pd.date_range(start=start_date, end=end_date, freq='D')
            trading_days = all_days[all_days.dayofweek < 5]  # 排除周末
            result['expected_days'] = len(trading_days)
            
            # 找出缺失的交易日
            df_dates_set = set(df_dates_sorted)
            trading_days_set = set(trading_days)
            missing = trading_days_set - df_dates_set
            result['missing_days'] = sorted([d.strftime('%Y-%m-%d') for d in missing])[:50]
            
            # 找出中断期（连续缺失>5 天）
            gap_periods = []
            if missing:
                missing_sorted = sorted(list(missing))
                gap_start = missing_sorted[0]
                gap_end = missing_sorted[0]
                
                for i in range(1, len(missing_sorted)):
                    if (missing_sorted[i] - missing_sorted[i-1]).days == 1:
                        gap_end = missing_sorted[i]
                    else:
                        if (gap_end - gap_start).days >= 5:
                            gap_periods.append({
                                'start': gap_start.strftime('%Y-%m-%d'),
                                'end': gap_end.strftime('%Y-%m-%d'),
                                'days': (gap_end - gap_start).days + 1
                            })
                        gap_start = missing_sorted[i]
                        gap_end = missing_sorted[i]
                
                # 处理最后一个间隙
                if (gap_end - gap_start).days >= 5:
                    gap_periods.append({
                        'start': gap_start.strftime('%Y-%m-%d'),
                        'end': gap_end.strftime('%Y-%m-%d'),
                        'days': (gap_end - gap_start).days + 1
                    })
            
            result['gap_periods'] = gap_periods
            
            # 计算连续性比例
            if result['expected_days'] > 0:
                result['continuity_rate'] = round(
                    (result['expected_days'] - len(missing)) / result['expected_days'] * 100, 2
                )
            
            # 判断是否连续
            if len(missing) > result['expected_days'] * 0.05:  # 缺失超过 5%
                result['is_continuous'] = False
            
            if gap_periods:
                result['is_continuous'] = False
            
        except Exception as e:
            result['is_continuous'] = False
            result['error'] = str(e)
        
        return result
    
    def check_field_completeness(self, df: pd.DataFrame, ts_code: str = None, 
                                  strategy_type: str = None) -> Dict[str, Any]:
        """
        1.3 字段完整性检查（无缺失列）
        """
        result = {
            'check_name': '字段完整性',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_complete': True,
            'missing_base_fields': [],
            'missing_strategy_fields': [],
            'null_ratio_by_field': {},
            'critical_null_fields': []
        }
        
        if df is None or df.empty:
            result['is_complete'] = False
            result['error'] = "数据为空"
            return result
        
        # 检查基础字段
        missing_base = [col for col in self.config.REQUIRED_FIELDS['base'] 
                       if col not in df.columns]
        result['missing_base_fields'] = missing_base
        
        # 检查策略字段
        if strategy_type and strategy_type in self.config.REQUIRED_FIELDS:
            missing_strategy = [col for col in self.config.REQUIRED_FIELDS[strategy_type]
                               if col not in df.columns]
            result['missing_strategy_fields'] = missing_strategy
        
        # 计算空值比例
        for col in df.columns:
            null_count = df[col].isna().sum()
            null_ratio = null_count / len(df) if len(df) > 0 else 0
            if null_ratio > 0:
                result['null_ratio_by_field'][col] = round(null_ratio, 4)
        
        # 标记关键字段空值问题
        critical_fields = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
        for field in critical_fields:
            if field in result['null_ratio_by_field']:
                if result['null_ratio_by_field'][field] > 0.05:
                    result['critical_null_fields'].append({
                        'field': field,
                        'null_ratio': result['null_ratio_by_field'][field]
                    })
        
        # 综合判断
        if missing_base or result['critical_null_fields']:
            result['is_complete'] = False
        
        return result
    
    def check_price_validity(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        2.1 价格合理性检查（无异常值）
        """
        result = {
            'check_name': '价格合理性',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_valid': True,
            'total_records': 0,
            'price_columns': [],
            'out_of_range': {},
            'invalid_logic': 0,
            'details': []
        }
        
        if df is None or df.empty:
            result['is_valid'] = False
            return result
        
        price_cols = ['open', 'high', 'low', 'close']
        available_cols = [col for col in price_cols if col in df.columns]
        result['price_columns'] = available_cols
        result['total_records'] = len(df)
        
        if not available_cols:
            result['error'] = "无价格列"
            return result
        
        # 检查价格范围
        for col in available_cols:
            below_min = (df[col] < self.config.PRICE_MIN).sum()
            above_max = (df[col] > self.config.PRICE_MAX).sum()
            result['out_of_range'][col] = {
                'below_min': int(below_min),
                'above_max': int(above_max)
            }
            
            if below_min > 0 or above_max > 0:
                result['is_valid'] = False
        
        # 检查价格逻辑（high >= low, high >= open/close, low <= open/close）
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_logic = (
                (df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])
            ).sum()
            result['invalid_logic'] = int(invalid_logic)
            
            if invalid_logic > 0:
                result['is_valid'] = False
                result['details'].append(f"❌ {invalid_logic}条记录价格逻辑错误（high<low 或 high<open/close）")
        
        return result
    
    def check_volume_amount_match(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        2.2 成交量/额匹配检查
        """
        result = {
            'check_name': '成交量额匹配',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_matched': True,
            'total_records': 0,
            'mismatch_count': 0,
            'mismatch_rate': 0,
            'details': []
        }
        
        if df is None or df.empty:
            return result
        
        # 检查是否有成交量和成交额
        if 'vol' not in df.columns or 'amount' not in df.columns:
            result['note'] = "缺少 vol 或 amount 列，跳过检查"
            return result
        
        result['total_records'] = len(df)
        
        # 成交量和成交额应该同向变化（简化检查）
        df_sorted = df.sort_values('trade_date').copy()
        vol_change = df_sorted['vol'].pct_change()
        amount_change = df_sorted['amount'].pct_change()
        
        # 检查成交量和成交额变化方向是否一致
        if len(df_sorted) > 1:
            same_direction = ((vol_change > 0) == (amount_change > 0)).sum()
            total_valid = vol_change.notna().sum()
            match_rate = same_direction / total_valid if total_valid > 0 else 0
            
            result['match_rate'] = round(match_rate * 100, 2)
            
            if match_rate < 0.8:  # 匹配率低于 80% 视为异常
                result['is_matched'] = False
                result['mismatch_rate'] = round((1 - match_rate) * 100, 2)
        
        return result
    
    def check_price_change_accuracy(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        2.3 涨跌幅计算正确性检查
        """
        result = {
            'check_name': '涨跌幅准确性',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_accurate': True,
            'total_records': 0,
            'calculated_changes': 0,
            'abnormal_changes': 0,
            'details': []
        }
        
        if df is None or df.empty or 'close' not in df.columns:
            return result
        
        result['total_records'] = len(df)
        
        # 计算涨跌幅
        df_sorted = df.sort_values(['ts_code', 'trade_date']).copy()
        df_sorted['calc_change'] = df_sorted.groupby('ts_code')['close'].pct_change()
        
        # 检查异常涨跌幅
        abnormal = df_sorted['calc_change'].apply(
            lambda x: pd.notna(x) and abs(x) > self.config.PRICE_CHANGE_WARNING
        )
        result['calculated_changes'] = df_sorted['calc_change'].notna().sum()
        result['abnormal_changes'] = abnormal.sum()
        
        if result['abnormal_changes'] > 0:
            result['details'].append(
                f"⚠️  发现 {result['abnormal_changes']} 条异常涨跌幅记录（>{self.config.PRICE_CHANGE_WARNING*100}%）"
            )
        
        return result
    
    def check_limit_price(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        3.1 涨停/跌停价验证
        """
        result = {
            'check_name': '涨跌停价验证',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_valid': True,
            'total_records': 0,
            'limit_up_count': 0,
            'limit_down_count': 0,
            'invalid_limit': [],
            'details': []
        }
        
        if df is None or df.empty:
            return result
        
        required_cols = ['close', 'pre_close']
        if not all(col in df.columns for col in required_cols):
            result['note'] = "缺少 close 或 pre_close 列，跳过检查"
            return result
        
        result['total_records'] = len(df)
        
        # 判断市场类型（确定涨跌停幅度）
        if ts_code:
            code_part = ts_code.split('.')[0]
            if code_part.startswith('688') or code_part.startswith('300') or code_part.startswith('301'):
                limit_ratio = 0.20  # 科创板/创业板 20%
            elif code_part.startswith('8') or code_part.startswith('4') or code_part.startswith('920'):
                limit_ratio = 0.30  # 北交所 30%
            else:
                limit_ratio = 0.10  # 主板 10%
        else:
            limit_ratio = 0.10
        
        # 计算理论涨跌停价
        df_calc = df.copy()
        df_calc['theoretical_limit_up'] = df_calc['pre_close'] * (1 + limit_ratio)
        df_calc['theoretical_limit_down'] = df_calc['pre_close'] * (1 - limit_ratio)
        
        # 检查实际涨停价
        limit_up_mask = df_calc['close'] >= df_calc['theoretical_limit_up'] * 0.999
        result['limit_up_count'] = limit_up_mask.sum()
        
        # 检查实际跌停价
        limit_down_mask = df_calc['close'] <= df_calc['theoretical_limit_down'] * 1.001
        result['limit_down_count'] = limit_down_mask.sum()
        
        # 检查超出涨跌停价的情况
        invalid_up = df_calc['close'] > df_calc['theoretical_limit_up'] * 1.001
        invalid_down = df_calc['close'] < df_calc['theoretical_limit_down'] * 0.999
        
        invalid_count = (invalid_up | invalid_down).sum()
        if invalid_count > 0:
            result['is_valid'] = False
            result['details'].append(f"❌ {invalid_count}条记录价格超出涨跌停限制")
        
        return result
    
    def check_suspension(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        3.2 停牌数据标记
        """
        result = {
            'check_name': '停牌数据标记',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_days': 0,
            'suspension_days': 0,
            'suspension_rate': 0,
            'suspension_periods': [],
            'details': []
        }
        
        if df is None or df.empty:
            return result
        
        # 检查是否有停牌标记
        if 'trade_status' in df.columns:
            suspension_mask = df['trade_status'].isin(['S', 'suspend', '停牌'])
            result['suspension_days'] = suspension_mask.sum()
        elif 'vol' in df.columns:
            # 成交量为 0 视为停牌
            suspension_mask = df['vol'] == 0
            result['suspension_days'] = suspension_mask.sum()
        else:
            result['note'] = "无法识别停牌标记"
            return result
        
        result['total_days'] = len(df)
        result['suspension_rate'] = round(
            result['suspension_days'] / result['total_days'] * 100, 2
        ) if result['total_days'] > 0 else 0
        
        # 标记停牌期间
        if result['suspension_days'] > 0:
            df_sorted = df.sort_values('trade_date').copy()
            df_sorted['is_suspended'] = suspension_mask
            
            # 找出连续停牌期
            suspension_periods = []
            in_suspension = False
            start_date = None
            
            for idx, row in df_sorted.iterrows():
                if row['is_suspended'] and not in_suspension:
                    in_suspension = True
                    start_date = row['trade_date']
                elif not row['is_suspended'] and in_suspension:
                    in_suspension = False
                    suspension_periods.append({
                        'start': start_date,
                        'end': df_sorted.loc[idx, 'trade_date'],
                        'days': len(df_sorted.loc[start_date:df_sorted.loc[idx, 'trade_date']])
                    })
            
            result['suspension_periods'] = suspension_periods[:10]  # 最多显示 10 个
            result['details'].append(f"⚠️  发现 {result['suspension_days']} 天停牌，停牌率 {result['suspension_rate']}%")
        
        return result
    
    def check_dividend_adjustment(self, df: pd.DataFrame, ts_code: str = None) -> Dict[str, Any]:
        """
        3.3 除权除息处理检查
        """
        result = {
            'check_name': '除权除息处理',
            'ts_code': ts_code,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_records': 0,
            'price_drop_events': 0,
            'potential_dividend_dates': [],
            'details': []
        }
        
        if df is None or df.empty or 'close' not in df.columns:
            return result
        
        result['total_records'] = len(df)
        
        # 检测价格大幅下跌（可能是除权除息）
        df_sorted = df.sort_values('trade_date').copy()
        df_sorted['price_change'] = df_sorted.groupby('ts_code')['close'].pct_change()
        
        # 查找跌幅>15% 但不是跌停的情况（可能是除权）
        large_drop = df_sorted['price_change'].apply(
            lambda x: pd.notna(x) and x < -0.15 and x > -0.30
        )
        
        result['price_drop_events'] = large_drop.sum()
        
        if result['price_drop_events'] > 0:
            potential_dates = df_sorted[large_drop]['trade_date'].tolist()[:10]
            result['potential_dividend_dates'] = [str(d) for d in potential_dates]
            result['details'].append(
                f"⚠️  发现 {result['price_drop_events']} 次疑似除权除息事件"
            )
        
        return result
    
    def generate_quality_score(self, check_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        4.1 生成质量评分（完整性 + 准确性）
        """
        score_report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completeness_score': 100,
            'accuracy_score': 100,
            'overall_score': 100,
            'grade': 'A',
            'details': []
        }
        
        # 完整性评分（权重 50%）
        completeness_deductions = 0
        
        if 'stock_list' in check_results:
            if not check_results['stock_list']['is_complete']:
                missing_rate = 100 - check_results['stock_list'].get('completeness_rate', 0)
                completeness_deductions += missing_rate * 0.5
        
        if 'date_continuity' in check_results:
            if not check_results['date_continuity']['is_continuous']:
                continuity_rate = check_results['date_continuity'].get('continuity_rate', 0)
                completeness_deductions += (100 - continuity_rate) * 0.3
        
        if 'field_completeness' in check_results:
            if not check_results['field_completeness']['is_complete']:
                completeness_deductions += 20
        
        score_report['completeness_score'] = max(0, 100 - completeness_deductions)
        
        # 准确性评分（权重 50%）
        accuracy_deductions = 0
        
        if 'price_validity' in check_results:
            if not check_results['price_validity']['is_valid']:
                accuracy_deductions += 20
        
        if 'price_change_accuracy' in check_results:
            abnormal_rate = (check_results['price_change_accuracy'].get('abnormal_changes', 0) /
                           max(check_results['price_change_accuracy'].get('total_records', 1), 1))
            accuracy_deductions += abnormal_rate * 100 * 0.3
        
        if 'limit_price' in check_results:
            if not check_results['limit_price']['is_valid']:
                accuracy_deductions += 15
        
        score_report['accuracy_score'] = max(0, 100 - accuracy_deductions)
        
        # 综合评分
        score_report['overall_score'] = round(
            score_report['completeness_score'] * 0.5 + 
            score_report['accuracy_score'] * 0.5, 2
        )
        
        # 评级
        if score_report['overall_score'] >= 90:
            score_report['grade'] = 'A'
        elif score_report['overall_score'] >= 80:
            score_report['grade'] = 'B'
        elif score_report['overall_score'] >= 70:
            score_report['grade'] = 'C'
        elif score_report['overall_score'] >= 60:
            score_report['grade'] = 'D'
        else:
            score_report['grade'] = 'F'
        
        return score_report
    
    def run_full_check(self, ts_codes: List[str] = None, 
                       sample_size: int = 10) -> Dict[str, Any]:
        """
        运行完整的数据质量检查
        """
        print("=" * 70)
        print("【数据质量检查系统】启动")
        print("=" * 70)
        
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {},
            'stock_list_check': None,
            'sample_checks': [],
            'quality_score': None,
            'issues': [],
            'recommendations': []
        }
        
        # 1. 股票列表完整性检查
        print("\n【1】检查股票列表完整性...")
        stock_list_result = self.check_stock_list_completeness()
        results['stock_list_check'] = stock_list_result
        print(f"  本地股票数：{stock_list_result['local_count']}")
        print(f"  官方股票数：{stock_list_result['official_count']}")
        print(f"  完整性：{stock_list_result.get('completeness_rate', 0)}%")
        
        if not stock_list_result['is_complete']:
            results['issues'].append({
                'type': '股票列表不完整',
                'severity': '高',
                'details': f"缺失 {len(stock_list_result['missing_stocks'])} 只股票"
            })
            results['recommendations'].append("补充缺失股票的历史数据")
        
        # 2. 抽样检查单只股票
        print(f"\n【2】抽样检查 {sample_size} 只股票...")
        
        if ts_codes is None:
            # 随机选择样本
            stock_basic = self.load_stock_list()
            ts_codes = stock_basic['ts_code'].sample(
                min(sample_size, len(stock_basic))
            ).tolist()
        
        sample_results = []
        for i, ts_code in enumerate(ts_codes, 1):
            print(f"  [{i}/{len(ts_codes)}] 检查 {ts_code}...")
            
            df = self.load_stock_data(ts_code, 'daily')
            if df is None or df.empty:
                sample_results.append({
                    'ts_code': ts_code,
                    'error': '数据加载失败'
                })
                continue
            
            stock_check = {
                'ts_code': ts_code,
                'record_count': len(df),
                'date_range': {
                    'start': df['trade_date'].min() if 'trade_date' in df.columns else None,
                    'end': df['trade_date'].max() if 'trade_date' in df.columns else None
                },
                'checks': {}
            }
            
            # 执行各项检查
            stock_check['checks']['date_continuity'] = self.check_date_continuity(df, ts_code)
            stock_check['checks']['field_completeness'] = self.check_field_completeness(df, ts_code)
            stock_check['checks']['price_validity'] = self.check_price_validity(df, ts_code)
            stock_check['checks']['price_change_accuracy'] = self.check_price_change_accuracy(df, ts_code)
            stock_check['checks']['limit_price'] = self.check_limit_price(df, ts_code)
            stock_check['checks']['suspension'] = self.check_suspension(df, ts_code)
            stock_check['checks']['dividend_adjustment'] = self.check_dividend_adjustment(df, ts_code)
            
            sample_results.append(stock_check)
            
            # 收集问题
            for check_name, check_result in stock_check['checks'].items():
                if not check_result.get('is_valid', True) and not check_result.get('is_complete', True):
                    results['issues'].append({
                        'type': check_name,
                        'ts_code': ts_code,
                        'severity': '中',
                        'details': check_result.get('details', [])
                    })
        
        results['sample_checks'] = sample_results
        
        # 3. 生成质量评分
        print("\n【3】生成质量评分...")
        quality_score = self.generate_quality_score(results)
        results['quality_score'] = quality_score
        print(f"  完整性得分：{quality_score['completeness_score']}")
        print(f"  准确性得分：{quality_score['accuracy_score']}")
        print(f"  综合得分：{quality_score['overall_score']} ({quality_score['grade']}级)")
        
        # 4. 生成建议
        if quality_score['overall_score'] < 90:
            results['recommendations'].append("建议进行全面数据修复")
        
        if quality_score['overall_score'] < 80:
            results['recommendations'].append("建议重新抓取问题股票的数据")
        
        results['summary'] = {
            'total_stocks_checked': len(ts_codes),
            'issues_found': len(results['issues']),
            'recommendations_count': len(results['recommendations']),
            'quality_grade': quality_score['grade']
        }
        
        print("\n" + "=" * 70)
        print("【数据质量检查】完成")
        print("=" * 70)
        
        return results
    
    def generate_report(self, results: Dict[str, Any], 
                        output_file: str = None) -> str:
        """
        生成质检报告（Markdown 格式）
        """
        report = []
        report.append("# 📊 数据质量检查报告")
        report.append("")
        report.append(f"**生成时间：** {results['timestamp']}")
        report.append("")
        
        # 摘要
        report.append("## 📋 检查摘要")
        report.append("")
        summary = results.get('summary', {})
        report.append(f"- **检查股票数：** {summary.get('total_stocks_checked', 0)}")
        report.append(f"- **发现问题数：** {summary.get('issues_found', 0)}")
        report.append(f"- **质量评级：** {summary.get('quality_grade', 'N/A')}")
        report.append("")
        
        # 质量评分
        score = results.get('quality_score', {})
        report.append("## 🎯 质量评分")
        report.append("")
        report.append(f"| 评分项 | 得分 |")
        report.append(f"|--------|------|")
        report.append(f"| 完整性 | {score.get('completeness_score', 0)} |")
        report.append(f"| 准确性 | {score.get('accuracy_score', 0)} |")
        report.append(f"| **综合** | **{score.get('overall_score', 0)}** ({score.get('grade', 'N/A')}) |")
        report.append("")
        
        # 股票列表检查
        stock_check = results.get('stock_list_check', {})
        report.append("## 📈 股票列表完整性")
        report.append("")
        report.append(f"- 本地股票数：{stock_check.get('local_count', 0)}")
        report.append(f"- 官方股票数：{stock_check.get('official_count', 0)}")
        report.append(f"- 完整性：{stock_check.get('completeness_rate', 0)}%")
        report.append("")
        
        if stock_check.get('missing_stocks'):
            report.append("### ❌ 缺失股票（前 20 个）")
            report.append("")
            for stock in stock_check['missing_stocks'][:20]:
                report.append(f"- {stock}")
            report.append("")
        
        # 抽样检查详情
        report.append("## 🔍 抽样检查详情")
        report.append("")
        
        for stock_result in results.get('sample_checks', []):
            ts_code = stock_result.get('ts_code', 'Unknown')
            report.append(f"### {ts_code}")
            report.append("")
            report.append(f"- 记录数：{stock_result.get('record_count', 0)}")
            
            date_range = stock_result.get('date_range', {})
            if date_range.get('start'):
                report.append(f"- 日期范围：{date_range['start']} ~ {date_range['end']}")
            report.append("")
            
            checks = stock_result.get('checks', {})
            for check_name, check_result in checks.items():
                status = "✅" if check_result.get('is_valid', True) or check_result.get('is_complete', True) else "❌"
                report.append(f"- {status} {check_name}")
            report.append("")
        
        # 问题清单
        if results.get('issues'):
            report.append("## ⚠️  问题清单")
            report.append("")
            for i, issue in enumerate(results['issues'], 1):
                report.append(f"{i}. **{issue['type']}** [{issue.get('severity', '中')}]")
                if 'ts_code' in issue:
                    report.append(f"   - 股票：{issue['ts_code']}")
                if isinstance(issue.get('details'), list):
                    for detail in issue['details'][:3]:
                        report.append(f"   - {detail}")
                else:
                    report.append(f"   - {issue.get('details', '')}")
                report.append("")
        
        # 修复建议
        if results.get('recommendations'):
            report.append("## 💡 修复建议")
            report.append("")
            for i, rec in enumerate(results['recommendations'], 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        # 免责声明
        report.append("---")
        report.append("")
        report.append("**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎")
        report.append("")
        
        report_text = "\n".join(report)
        
        # 保存报告
        if output_file:
            output_path = self.config.OUTPUT_DIR / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"📄 报告已保存：{output_path}")
        
        return report_text


# ==============================================
# 主函数
# ==============================================

def main():
    """主函数"""
    print("\n")
    print("*" * 70)
    print("*  数据验证与质检系统 v1.0")
    print("*" * 70)
    print("\n")
    
    try:
        # 创建检查器
        checker = DataQualityChecker()
        
        # 运行完整检查
        results = checker.run_full_check(sample_size=10)
        
        # 生成报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"quality_report_{timestamp}.md"
        report = checker.generate_report(results, report_file)
        
        # 打印报告
        print("\n")
        print(report)
        
        # 保存 JSON 结果
        json_file = checker.config.OUTPUT_DIR / f"quality_result_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            # 处理 pandas 对象序列化
            def convert(obj):
                if isinstance(obj, (np.integer, np.floating)):
                    return obj.item()
                elif isinstance(obj, pd.Timestamp):
                    return str(obj)
                elif isinstance(obj, dict):
                    return {k: convert(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert(i) for i in obj]
                return obj
            
            json.dump(convert(results), f, ensure_ascii=False, indent=2)
        print(f"📄 JSON 结果已保存：{json_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 检查失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
