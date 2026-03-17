# ==============================================
# 【优化】数据校验模块 - data_validator.py
# ==============================================
# 功能：负责数据质量校验、一致性检查、异常检测、数据完整性校验
# 职责：数据验证、质量检查、异常报告、完整性报告
# ==============================================

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("quant_system")


class DataValidator:
    """
    【优化】数据校验器
    职责：数据质量检查、一致性验证、异常检测
    """
    
    def __init__(self):
        """初始化数据校验器"""
        self.validation_results = []
        self.error_count = 0
        self.warning_count = 0
        # 【优化】数据完整性校验配置
        self.required_fields = {
            'base': ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol'],
            '打板策略': ['ts_code', 'trade_date', 'close', 'vol', 'limit', 'up_down_times', 'order_amount', 'break_limit_times'],
            '缩量潜伏策略': ['ts_code', 'trade_date', 'close', 'vol', 'high', 'low', 'limit'],
            '板块轮动策略': ['ts_code', 'trade_date', 'close', 'vol', 'industry', 'is_main_industry']
        }
        self.min_records_per_stock = 60  # 【优化】每只股票最小记录数（约 3 个月交易日）
        self.max_gap_days = 5  # 【优化】允许的最大交易日中断天数
        # 【优化】数据准确性校验配置
        self.price_min = 0  # 【优化】价格最小值
        self.price_max = 10000  # 【优化】价格最大值
        self.price_change_warning = 0.20  # 【优化】涨跌幅预警阈值（20%）
        self.vol_change_warning = 10  # 【优化】成交量变化预警倍数（10 倍）
        self.sigma_threshold = 3  # 【优化】3σ原则阈值
    
    def validate_data_consistency(
        self, 
        df: pd.DataFrame, 
        required_columns: List[str],
        min_rows: int = 0
    ) -> Tuple[bool, List[str]]:
        """
        【优化】验证数据一致性
        :param df: 待验证的 DataFrame
        :param required_columns: 必需的列名列表
        :param min_rows: 最小行数要求
        :return: (是否通过验证，错误信息列表)
        """
        errors = []
        
        # 空数据检查
        if df is None or df.empty:
            if min_rows > 0:
                errors.append("数据为空，不满足最小行数要求")
                return False, errors
            return True, errors
        
        # 行数检查
        if len(df) < min_rows:
            errors.append(f"数据行数{len(df)}小于最小要求{min_rows}")
        
        # 列存在性检查
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"缺少必需列：{missing_columns}")
        
        # 核心列空值检查
        critical_columns = ['ts_code', 'trade_date', 'close']
        for col in critical_columns:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    errors.append(f"核心列'{col}'存在{null_count}个空值")
        
        # 价格合理性检查
        if 'close' in df.columns:
            negative_prices = (df['close'] <= 0).sum()
            if negative_prices > 0:
                errors.append(f"存在{negative_prices}条价格≤0 的异常数据")
            
            # 检查价格突变（单日涨跌幅超过 50%）
            if len(df) > 1:
                df_sorted = df.sort_values('trade_date')
                price_change = df_sorted['close'].pct_change().abs()
                abnormal_changes = (price_change > 0.5).sum()
                if abnormal_changes > 0:
                    errors.append(f"存在{abnormal_changes}条价格突变异常（单日涨跌幅>50%）")
        
        # 成交量合理性检查
        if 'vol' in df.columns:
            negative_vol = (df['vol'] <= 0).sum()
            if negative_vol > len(df) * 0.1:  # 超过 10% 的数据成交量异常
                errors.append(f"存在{negative_vol}条成交量≤0 的异常数据")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def check_field_completeness(
        self, 
        df: pd.DataFrame, 
        strategy_type: str = None
    ) -> Dict[str, Any]:
        """
        【优化】字段完整性检查 - 检查必填字段是否存在
        :param df: 待检查的 DataFrame
        :param strategy_type: 策略类型（可选，用于策略特定字段检查）
        :return: 检查报告字典
        """
        report = {
            'is_complete': True,
            'missing_base_fields': [],
            'missing_strategy_fields': [],
            'null_ratio_by_field': {},
            'critical_null_fields': []
        }
        
        if df is None or df.empty:
            report['is_complete'] = False
            report['missing_base_fields'] = self.required_fields['base'].copy()
            return report
        
        # 检查基础必填字段
        missing_base = [col for col in self.required_fields['base'] if col not in df.columns]
        if missing_base:
            report['missing_base_fields'] = missing_base
            report['is_complete'] = False
        
        # 检查策略特定字段（如果指定了策略类型）
        if strategy_type and strategy_type in self.required_fields:
            missing_strategy = [col for col in self.required_fields[strategy_type] if col not in df.columns]
            report['missing_strategy_fields'] = missing_strategy
            if missing_strategy:
                report['is_complete'] = False
        
        # 计算每个字段的空值比例
        for col in df.columns:
            null_count = df[col].isna().sum()
            null_ratio = null_count / len(df) if len(df) > 0 else 0
            if null_ratio > 0:
                report['null_ratio_by_field'][col] = round(null_ratio, 4)
        
        # 标记关键字段的空值问题（空值比例超过 5%）
        critical_fields = ['ts_code', 'trade_date', 'close', 'vol']
        for field in critical_fields:
            if field in report['null_ratio_by_field']:
                if report['null_ratio_by_field'][field] > 0.05:
                    report['critical_null_fields'].append({
                        'field': field,
                        'null_ratio': report['null_ratio_by_field'][field]
                    })
        
        if report['critical_null_fields']:
            report['is_complete'] = False
        
        return report
    
    def check_record_count(
        self, 
        df: pd.DataFrame,
        date_range: tuple = None
    ) -> Dict[str, Any]:
        """
        【优化】记录数检查 - 检查数据量是否合理
        :param df: 待检查的 DataFrame
        :param date_range: 日期范围元组 (start_date, end_date)，用于计算预期记录数
        :return: 检查报告字典
        """
        report = {
            'is_reasonable': True,
            'total_records': 0,
            'total_stocks': 0,
            'records_per_stock': {},
            'expected_records': 0,
            'coverage_ratio': 0,
            'insufficient_stocks': [],
            'abnormal_stocks': []
        }
        
        if df is None or df.empty:
            report['is_reasonable'] = False
            return report
        
        report['total_records'] = len(df)
        
        if 'ts_code' not in df.columns:
            report['is_reasonable'] = False
            return report
        
        report['total_stocks'] = df['ts_code'].nunique()
        
        # 统计每只股票的记录数
        stock_counts = df.groupby('ts_code').size()
        report['records_per_stock'] = stock_counts.to_dict()
        
        # 计算预期记录数（如果有日期范围）
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            try:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                # 估算交易日数量（一年约 242 个交易日）
                total_days = (end - start).days
                estimated_trading_days = int(total_days * 242 / 365)
                report['expected_records'] = estimated_trading_days * report['total_stocks']
                
                # 计算覆盖率
                if report['expected_records'] > 0:
                    report['coverage_ratio'] = round(report['total_records'] / report['expected_records'], 4)
            except Exception as e:
                logger.warning(f"⚠️  计算预期记录数失败：{e}")
        
        # 检查每只股票的记录数是否达到最小要求
        for stock, count in report['records_per_stock'].items():
            if count < self.min_records_per_stock:
                report['insufficient_stocks'].append({
                    'ts_code': stock,
                    'count': count,
                    'min_required': self.min_records_per_stock
                })
        
        # 检查异常多的记录数（可能重复）
        if 'trade_date' in df.columns:
            max_expected = len(df['trade_date'].unique()) * 1.5  # 允许 50% 冗余
            for stock, count in report['records_per_stock'].items():
                if count > max_expected:
                    report['abnormal_stocks'].append({
                        'ts_code': stock,
                        'count': count,
                        'expected_max': int(max_expected)
                    })
        
        # 综合判断
        if report['insufficient_stocks'] or report['abnormal_stocks']:
            if len(report['insufficient_stocks']) > report['total_stocks'] * 0.1:
                report['is_reasonable'] = False
        
        return report
    
    def check_trading_day_continuity(
        self, 
        df: pd.DataFrame,
        trade_calendar: List = None
    ) -> Dict[str, Any]:
        """
        【优化】交易日连续性检查 - 对比交易日历检查数据连续性
        :param df: 待检查的 DataFrame
        :param trade_calendar: 交易日历列表（datetime 对象列表）
        :return: 检查报告字典
        """
        report = {
            'is_continuous': True,
            'total_trading_days': 0,
            'expected_trading_days': 0,
            'missing_days': [],
            'extra_days': [],
            'gap_periods': [],
            'continuity_ratio': 0
        }
        
        if df is None or df.empty or 'trade_date' not in df.columns:
            report['is_continuous'] = False
            return report
        
        # 获取数据中的日期范围
        df_dates = pd.to_datetime(df['trade_date']).dropna().unique()
        if len(df_dates) == 0:
            report['is_continuous'] = False
            return report
        
        df_dates_sorted = sorted(df_dates)
        report['total_trading_days'] = len(df_dates_sorted)
        
        # 如果有交易日历，进行对比
        if trade_calendar and len(trade_calendar) > 0:
            trade_cal_set = set(pd.to_datetime(trade_calendar))
            df_dates_set = set(df_dates_sorted)
            
            # 找出缺失的交易日
            missing = trade_cal_set - df_dates_set
            report['missing_days'] = sorted([d.strftime('%Y-%m-%d') for d in missing])
            
            # 找出多余的日期（数据中有但日历中没有）
            extra = df_dates_set - trade_cal_set
            report['extra_days'] = sorted([d.strftime('%Y-%m-%d') for d in extra])
            
            # 计算连续性比例
            if len(trade_cal_set) > 0:
                report['continuity_ratio'] = round(
                    (len(trade_cal_set) - len(missing)) / len(trade_cal_set), 
                    4
                )
            
            report['expected_trading_days'] = len(trade_cal_set)
        else:
            # 无交易日历时，检查日期间隔
            gap_periods = []
            for i in range(1, len(df_dates_sorted)):
                prev_date = df_dates_sorted[i-1]
                curr_date = df_dates_sorted[i]
                gap_days = (curr_date - prev_date).days
                
                # 如果间隔超过最大允许天数（考虑节假日）
                if gap_days > self.max_gap_days:
                    gap_periods.append({
                        'start': prev_date.strftime('%Y-%m-%d'),
                        'end': curr_date.strftime('%Y-%m-%d'),
                        'gap_days': gap_days
                    })
            
            report['gap_periods'] = gap_periods
            report['continuity_ratio'] = 1.0 if not gap_periods else 0.9
        
        # 综合判断
        if len(report['missing_days']) > report['expected_trading_days'] * 0.05:
            report['is_continuous'] = False
        
        if report['gap_periods']:
            report['is_continuous'] = False
        
        return report
    
    # ==============================================
    # 【优化】任务 7：数据准确性校验 - 新增方法
    # ==============================================
    
    def _get_stock_market_type(self, ts_code: str) -> str:
        """
        【优化】判断股票市场类型
        :param ts_code: 股票代码（格式：000001.SZ）
        :return: 市场类型（main/chinext/star）
        """
        if not ts_code or '.' not in ts_code:
            return 'unknown'
        
        code_part = ts_code.split('.')[0]
        if code_part.startswith('688'):
            return 'star'  # 科创板
        elif code_part.startswith('300') or code_part.startswith('301'):
            return 'chinext'  # 创业板
        else:
            return 'main'  # 主板
    
    def check_price_logic(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】价格逻辑检查 - 验证开高低收关系
        :param df: 待检查的 DataFrame
        :return: 检查报告字典
        """
        report = {
            'is_valid': True,
            'total_records': 0,
            'invalid_records': 0,
            'invalid_rate': 0,
            'error_types': {
                'high_not_max': 0,  # high 不是最大值
                'low_not_min': 0,   # low 不是最小值
                'open_out_of_range': 0,  # open 超出 high-low 范围
                'close_out_of_range': 0,  # close 超出 high-low 范围
            },
            'error_details': []
        }
        
        if df is None or df.empty:
            return report
        
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            report['is_valid'] = False
            report['error_details'].append("缺少必需的价格列（open/high/low/close）")
            return report
        
        report['total_records'] = len(df)
        error_mask = pd.Series([False] * len(df))
        
        # 检查 high 是否为最大值
        high_not_max = df['high'] < df[['open', 'high', 'low', 'close']].max(axis=1)
        report['error_types']['high_not_max'] = high_not_max.sum()
        error_mask |= high_not_max
        
        # 检查 low 是否为最小值
        low_not_min = df['low'] > df[['open', 'high', 'low', 'close']].min(axis=1)
        report['error_types']['low_not_min'] = low_not_min.sum()
        error_mask |= low_not_min
        
        # 检查 open 是否在 [low, high] 范围内
        open_out_of_range = (df['open'] < df['low']) | (df['open'] > df['high'])
        report['error_types']['open_out_of_range'] = open_out_of_range.sum()
        error_mask |= open_out_of_range
        
        # 检查 close 是否在 [low, high] 范围内
        close_out_of_range = (df['close'] < df['low']) | (df['close'] > df['high'])
        report['error_types']['close_out_of_range'] = close_out_of_range.sum()
        error_mask |= close_out_of_range
        
        report['invalid_records'] = error_mask.sum()
        report['invalid_rate'] = round(report['invalid_records'] / report['total_records'] * 100, 2) if report['total_records'] > 0 else 0
        
        # 记录部分错误详情（最多 10 条）
        if report['invalid_records'] > 0:
            error_indices = error_mask[error_mask].index[:10]
            for idx in error_indices:
                report['error_details'].append({
                    'index': idx,
                    'ts_code': df.loc[idx, 'ts_code'] if 'ts_code' in df.columns else 'N/A',
                    'trade_date': df.loc[idx, 'trade_date'] if 'trade_date' in df.columns else 'N/A',
                    'open': df.loc[idx, 'open'],
                    'high': df.loc[idx, 'high'],
                    'low': df.loc[idx, 'low'],
                    'close': df.loc[idx, 'close']
                })
        
        # 错误率超过 1% 视为无效
        if report['invalid_rate'] > 1:
            report['is_valid'] = False
        
        return report
    
    def check_price_range(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】数值范围检查 - 价格>0 且<10000
        :param df: 待检查的 DataFrame
        :return: 检查报告字典
        """
        report = {
            'is_valid': True,
            'total_records': 0,
            'price_columns': [],
            'out_of_range_records': {},
            'total_out_of_range': 0,
            'out_of_range_rate': 0,
            'error_details': []
        }
        
        if df is None or df.empty:
            return report
        
        price_columns = ['open', 'high', 'low', 'close']
        available_price_cols = [col for col in price_columns if col in df.columns]
        report['price_columns'] = available_price_cols
        report['total_records'] = len(df)
        
        if not available_price_cols:
            report['error_details'].append("无价格列可检查")
            return report
        
        total_out_of_range = 0
        for col in available_price_cols:
            # 检查价格 <= 0
            below_min = df[col] <= self.price_min
            # 检查价格 >= 10000
            above_max = df[col] >= self.price_max
            # 合并错误
            out_of_range = below_min | above_max
            count = out_of_range.sum()
            
            report['out_of_range_records'][col] = {
                'below_min': int(below_min.sum()),
                'above_max': int(above_max.sum()),
                'total': int(count)
            }
            total_out_of_range += count
        
        report['total_out_of_range'] = total_out_of_range
        report['out_of_range_rate'] = round(total_out_of_range / (report['total_records'] * len(available_price_cols)) * 100, 2) if report['total_records'] > 0 else 0
        
        # 记录部分错误详情（最多 10 条）
        if total_out_of_range > 0:
            for col in available_price_cols:
                out_of_range = (df[col] <= self.price_min) | (df[col] >= self.price_max)
                error_indices = out_of_range[out_of_range].index[:5]
                for idx in error_indices:
                    report['error_details'].append({
                        'index': idx,
                        'ts_code': df.loc[idx, 'ts_code'] if 'ts_code' in df.columns else 'N/A',
                        'trade_date': df.loc[idx, 'trade_date'] if 'trade_date' in df.columns else 'N/A',
                        'column': col,
                        'value': df.loc[idx, col]
                    })
        
        # 有任何超出范围的数据视为无效
        if total_out_of_range > 0:
            report['is_valid'] = False
        
        return report
    
    def check_price_change_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】异常值检测 - 3σ原则 + 涨跌幅>20% 标记
        :param df: 待检查的 DataFrame
        :return: 检查报告字典
        """
        report = {
            'is_valid': True,
            'total_records': 0,
            'total_stocks': 0,
            'outliers_3sigma': 0,
            'outliers_change_20pct': 0,
            'outliers_by_market': {
                'main': {'count': 0, 'limit': 0.10},  # 主板 10%
                'chinext': {'count': 0, 'limit': 0.20},  # 创业板 20%
                'star': {'count': 0, 'limit': 0.20},  # 科创板 20%
            },
            'outlier_details': []
        }
        
        if df is None or df.empty:
            return report
        
        if 'close' not in df.columns or 'ts_code' not in df.columns:
            report['error_details'].append("缺少 close 或 ts_code 列")
            return report
        
        report['total_records'] = len(df)
        report['total_stocks'] = df['ts_code'].nunique()
        
        # 按股票分组计算涨跌幅
        df_sorted = df.sort_values(['ts_code', 'trade_date']).copy()
        df_sorted['price_change'] = df_sorted.groupby('ts_code')['close'].pct_change()
        
        # 3σ原则检测异常值
        mean_change = df_sorted['price_change'].mean()
        std_change = df_sorted['price_change'].std()
        if pd.notna(mean_change) and pd.notna(std_change) and std_change > 0:
            lower_bound = mean_change - self.sigma_threshold * std_change
            upper_bound = mean_change + self.sigma_threshold * std_change
            outliers_3sigma = df_sorted['price_change'].apply(
                lambda x: pd.notna(x) and (x < lower_bound or x > upper_bound)
            )
            report['outliers_3sigma'] = outliers_3sigma.sum()
        
        # 涨跌幅>20% 检测
        outliers_20pct = df_sorted['price_change'].apply(
            lambda x: pd.notna(x) and abs(x) > self.price_change_warning
        )
        report['outliers_change_20pct'] = outliers_20pct.sum()
        
        # 区分市场类型检测涨跌幅限制
        df_sorted['market_type'] = df_sorted['ts_code'].apply(self._get_stock_market_type)
        
        for market_type in ['main', 'chinext', 'star']:
            market_mask = df_sorted['market_type'] == market_type
            market_limit = self.outliers_by_market[market_type]['limit']
            market_outliers = df_sorted[market_mask]['price_change'].apply(
                lambda x: pd.notna(x) and abs(x) > market_limit
            )
            report['outliers_by_market'][market_type]['count'] = market_outliers.sum()
        
        # 记录部分异常详情（最多 20 条）
        outlier_mask = outliers_20pct | outliers_3sigma
        if outlier_mask.any():
            outlier_indices = outlier_mask[outlier_mask].index[:20]
            for idx in outlier_indices:
                report['outlier_details'].append({
                    'index': idx,
                    'ts_code': df_sorted.loc[idx, 'ts_code'],
                    'trade_date': df_sorted.loc[idx, 'trade_date'],
                    'close': df_sorted.loc[idx, 'close'],
                    'price_change': round(df_sorted.loc[idx, 'price_change'] * 100, 2) if pd.notna(df_sorted.loc[idx, 'price_change']) else None,
                    'market_type': df_sorted.loc[idx, 'market_type']
                })
        
        # 异常值比例超过 1% 视为需要关注
        if report['outliers_change_20pct'] > report['total_records'] * 0.01:
            report['is_valid'] = False
        
        return report
    
    def check_volume_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】成交量异常检测 - 变化>10 倍标记
        :param df: 待检查的 DataFrame
        :return: 检查报告字典
        """
        report = {
            'is_valid': True,
            'total_records': 0,
            'total_stocks': 0,
            'volume_outliers': 0,
            'outlier_rate': 0,
            'outlier_details': []
        }
        
        if df is None or df.empty:
            return report
        
        if 'vol' not in df.columns or 'ts_code' not in df.columns:
            report['error_details'].append("缺少 vol 或 ts_code 列")
            return report
        
        report['total_records'] = len(df)
        report['total_stocks'] = df['ts_code'].nunique()
        
        # 按股票分组计算成交量变化
        df_sorted = df.sort_values(['ts_code', 'trade_date']).copy()
        df_sorted['vol_change_ratio'] = df_sorted.groupby('ts_code')['vol'].pct_change().abs()
        
        # 检测成交量变化>10 倍
        vol_outliers = df_sorted['vol_change_ratio'] > self.vol_change_warning
        report['volume_outliers'] = vol_outliers.sum()
        report['outlier_rate'] = round(report['volume_outliers'] / report['total_records'] * 100, 2) if report['total_records'] > 0 else 0
        
        # 记录部分异常详情（最多 10 条）
        if report['volume_outliers'] > 0:
            outlier_indices = vol_outliers[vol_outliers].index[:10]
            for idx in outlier_indices:
                report['outlier_details'].append({
                    'index': idx,
                    'ts_code': df_sorted.loc[idx, 'ts_code'],
                    'trade_date': df_sorted.loc[idx, 'trade_date'],
                    'vol': df_sorted.loc[idx, 'vol'],
                    'vol_change_ratio': round(df_sorted.loc[idx, 'vol_change_ratio'], 2) if pd.notna(df_sorted.loc[idx, 'vol_change_ratio']) else None
                })
        
        # 异常率超过 5% 视为需要关注
        if report['outlier_rate'] > 5:
            report['is_valid'] = False
        
        return report
    
    def validate_data_accuracy(
        self, 
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        【优化】数据准确性综合校验 - 整合所有准确性检查
        :param df: 待验证的 DataFrame
        :return: 准确性校验报告
        """
        report = {
            'is_valid': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price_logic': None,
            'price_range': None,
            'price_change_outliers': None,
            'volume_outliers': None,
            'overall_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        # 1. 价格逻辑检查
        report['price_logic'] = self.check_price_logic(df)
        if not report['price_logic']['is_valid']:
            report['is_valid'] = False
            report['issues'].append({
                'type': '价格逻辑错误',
                'severity': '高',
                'details': f"{report['price_logic']['invalid_records']}条记录价格逻辑异常（开高低收关系错误），错误率{report['price_logic']['invalid_rate']}%"
            })
            report['recommendations'].append("检查数据源，修复开高低收关系错误的数据")
        
        # 2. 数值范围检查
        report['price_range'] = self.check_price_range(df)
        if not report['price_range']['is_valid']:
            report['is_valid'] = False
            report['issues'].append({
                'type': '价格超出范围',
                'severity': '高',
                'details': f"{report['price_range']['total_out_of_range']}条记录价格超出有效范围（0-10000）"
            })
            report['recommendations'].append("检查数据源，剔除或修复价格异常的数据")
        
        # 3. 价格异常值检测
        report['price_change_outliers'] = self.check_price_change_outliers(df)
        if not report['price_change_outliers']['is_valid']:
            report['issues'].append({
                'type': '价格异常波动',
                'severity': '中',
                'details': f"{report['price_change_outliers']['outliers_change_20pct']}条记录涨跌幅超过 20%，{report['price_change_outliers']['outliers_3sigma']}条记录违反 3σ原则"
            })
            report['recommendations'].append("核实异常波动股票的公告信息，确认是否为真实市场行为")
        
        # 4. 成交量异常检测
        report['volume_outliers'] = self.check_volume_outliers(df)
        if not report['volume_outliers']['is_valid']:
            report['issues'].append({
                'type': '成交量异常',
                'severity': '中',
                'details': f"{report['volume_outliers']['volume_outliers']}条记录成交量变化超过 10 倍，异常率{report['volume_outliers']['outlier_rate']}%"
            })
            report['recommendations'].append("核实成交量异常股票的公告信息，确认是否为真实市场行为")
        
        # 计算综合得分（0-100）
        score = 100
        if report['price_logic'] and not report['price_logic']['is_valid']:
            score -= 40
        if report['price_range'] and not report['price_range']['is_valid']:
            score -= 40
        if report['price_change_outliers'] and not report['price_change_outliers']['is_valid']:
            score -= 10
        if report['volume_outliers'] and not report['volume_outliers']['is_valid']:
            score -= 10
        
        report['overall_score'] = max(0, score)
        
        return report
    
    # ==============================================
    # 【优化】任务 7 结束
    # ==============================================
    
    def validate_local_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        【优化】全面验证本地数据质量
        :param df: 待验证的 DataFrame
        :return: 验证报告字典
        """
        report = {
            'is_valid': True,
            'total_rows': 0,
            'total_stocks': 0,
            'date_range': None,
            'missing_data_ratio': 0,
            'abnormal_data_count': 0,
            'errors': [],
            'warnings': []
        }
        
        if df is None or df.empty:
            report['is_valid'] = False
            report['errors'].append("数据为空")
            return report
        
        report['total_rows'] = len(df)
        report['total_stocks'] = df['ts_code'].nunique() if 'ts_code' in df.columns else 0
        
        # 日期范围
        if 'trade_date' in df.columns:
            df_sorted = df.sort_values('trade_date')
            report['date_range'] = {
                'start': df_sorted['trade_date'].min(),
                'end': df_sorted['trade_date'].max()
            }
        
        # 缺失数据检查
        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
        available_columns = [col for col in required_columns if col in df.columns]
        
        if len(available_columns) < len(required_columns):
            missing = set(required_columns) - set(available_columns)
            report['warnings'].append(f"缺少列：{missing}")
        
        # 计算缺失率
        if available_columns:
            missing_count = df[available_columns].isna().sum().sum()
            total_cells = len(df) * len(available_columns)
            report['missing_data_ratio'] = round(missing_count / total_cells * 100, 2) if total_cells > 0 else 0
        
        # 异常数据检测
        abnormal_count = 0
        
        # 价格异常
        if 'close' in df.columns:
            abnormal_count += (df['close'] <= 0).sum()
            abnormal_count += (df['close'] > 1000).sum()  # 股价超过 1000 元视为异常
        
        # 成交量异常
        if 'vol' in df.columns:
            abnormal_count += (df['vol'] <= 0).sum()
        
        # 涨跌幅异常
        if len(df) > 1 and 'close' in df.columns:
            df_sorted = df.sort_values(['ts_code', 'trade_date'])
            price_change = df_sorted.groupby('ts_code')['close'].pct_change().abs()
            abnormal_count += (price_change > 0.5).sum()
        
        report['abnormal_data_count'] = int(abnormal_count)
        
        # 综合判断
        if report['errors'] or report['missing_data_ratio'] > 10 or abnormal_count > len(df) * 0.01:
            report['is_valid'] = False
        
        return report
    
    def validate_data_integrity(
        self, 
        df: pd.DataFrame, 
        strategy_type: str = None,
        trade_calendar: List = None,
        date_range: tuple = None
    ) -> Dict[str, Any]:
        """
        【优化】数据完整性综合校验 - 整合所有完整性检查
        :param df: 待验证的 DataFrame
        :param strategy_type: 策略类型
        :param trade_calendar: 交易日历列表
        :param date_range: 日期范围元组 (start_date, end_date)
        :return: 完整性校验报告
        """
        report = {
            'is_valid': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'field_completeness': None,
            'record_count': None,
            'trading_continuity': None,
            'overall_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        # 1. 字段完整性检查
        report['field_completeness'] = self.check_field_completeness(df, strategy_type)
        if not report['field_completeness']['is_complete']:
            report['is_valid'] = False
            if report['field_completeness']['missing_base_fields']:
                report['issues'].append({
                    'type': '字段缺失',
                    'severity': '高',
                    'details': f"缺少基础字段：{report['field_completeness']['missing_base_fields']}"
                })
                report['recommendations'].append("补充缺失的基础字段数据")
            
            if report['field_completeness']['critical_null_fields']:
                for item in report['field_completeness']['critical_null_fields']:
                    report['issues'].append({
                        'type': '关键字段空值',
                        'severity': '高',
                        'details': f"字段 '{item['field']}' 空值比例过高：{item['null_ratio']*100:.2f}%"
                    })
                report['recommendations'].append("检查数据源，修复关键字段的空值问题")
        
        # 2. 记录数检查
        report['record_count'] = self.check_record_count(df, date_range)
        if not report['record_count']['is_reasonable']:
            report['is_valid'] = False
            if report['record_count']['insufficient_stocks']:
                report['issues'].append({
                    'type': '记录数不足',
                    'severity': '中',
                    'details': f"{len(report['record_count']['insufficient_stocks'])} 只股票记录数不足"
                })
                report['recommendations'].append("补充历史数据，确保每只股票有足够的交易记录")
            
            if report['record_count']['abnormal_stocks']:
                report['issues'].append({
                    'type': '记录数异常',
                    'severity': '中',
                    'details': f"{len(report['record_count']['abnormal_stocks'])} 只股票记录数异常（可能重复）"
                })
                report['recommendations'].append("检查数据是否有重复，进行去重处理")
        
        # 3. 交易日连续性检查
        report['trading_continuity'] = self.check_trading_day_continuity(df, trade_calendar)
        if not report['trading_continuity']['is_continuous']:
            report['is_valid'] = False
            if report['trading_continuity']['missing_days']:
                report['issues'].append({
                    'type': '交易日缺失',
                    'severity': '中',
                    'details': f"缺失 {len(report['trading_continuity']['missing_days'])} 个交易日"
                })
                report['recommendations'].append("补充缺失的交易日数据")
            
            if report['trading_continuity']['gap_periods']:
                for gap in report['trading_continuity']['gap_periods']:
                    report['issues'].append({
                        'type': '日期中断',
                        'severity': '低',
                        'details': f"{gap['start']} 至 {gap['end']} 中断 {gap['gap_days']} 天"
                    })
        
        # 计算综合得分（0-100）
        score = 100
        if report['field_completeness'] and not report['field_completeness']['is_complete']:
            score -= 40
        if report['record_count'] and not report['record_count']['is_reasonable']:
            score -= 30
        if report['trading_continuity'] and not report['trading_continuity']['is_continuous']:
            score -= 30
        
        report['overall_score'] = max(0, score)
        
        return report
    
    def check_future_function(
        self, 
        df: pd.DataFrame, 
        check_columns: List[str] = None
    ) -> Dict[str, Any]:
        """
        【优化】检查未来函数（使用未来数据的 bug）
        :param df: 待检查的 DataFrame
        :param check_columns: 需要检查的列
        :return: 检查报告
        """
        report = {
            'has_future_function': False,
            'suspicious_columns': [],
            'details': []
        }
        
        if df is None or df.empty:
            return report
        
        if check_columns is None:
            check_columns = ['limit', 'order_amount', 'inst_buy', 'youzi_buy']
        
        # 检查是否有列使用了未来数据（典型特征：当天数据在当天无法获取）
        for col in check_columns:
            if col not in df.columns:
                continue
            
            # 检查该列是否有 shift 操作
            # 如果列名包含特定后缀，可能是已处理的
            if col.endswith('_shifted') or col.endswith('_prev'):
                continue
            
            # 典型未来函数场景：
            # 1. limit（涨停标记）：当天收盘后才能知道
            # 2. order_amount（封单金额）：当天收盘后才能知道
            # 3. inst_buy（机构买入）：龙虎榜收盘后才公布
            if col in ['limit', 'order_amount', 'inst_buy', 'youzi_buy', 'break_limit_times']:
                report['has_future_function'] = True
                report['suspicious_columns'].append(col)
                report['details'].append(
                    f"列'{col}'可能包含未来函数，需确保使用 shift(1) 或 shift(2) 处理"
                )
        
        return report
    
    def validate_strategy_input(
        self, 
        df: pd.DataFrame, 
        strategy_type: str
    ) -> Tuple[bool, List[str]]:
        """
        【优化】验证策略输入数据
        :param df: 输入数据
        :param strategy_type: 策略类型
        :return: (是否通过，错误列表)
        """
        errors = []
        
        # 通用检查
        if df is None or df.empty:
            errors.append("输入数据为空")
            return False, errors
        
        # 必需列检查
        required_columns = ['ts_code', 'trade_date', 'close', 'vol']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            errors.append(f"缺少必需列：{missing}")
        
        # 策略特定检查
        if strategy_type == "打板策略":
            strategy_columns = ['limit', 'order_amount', 'up_down_times', 'break_limit_times']
            missing_strategy = [col for col in strategy_columns if col not in df.columns]
            if missing_strategy:
                errors.append(f"打板策略缺少列：{missing_strategy}")
        
        elif strategy_type == "缩量潜伏策略":
            strategy_columns = ['limit', 'vol', 'high', 'low']
            missing_strategy = [col for col in strategy_columns if col not in df.columns]
            if missing_strategy:
                errors.append(f"缩量潜伏策略缺少列：{missing_strategy}")
        
        elif strategy_type == "板块轮动策略":
            strategy_columns = ['industry', 'is_main_industry']
            missing_strategy = [col for col in strategy_columns if col not in df.columns]
            if missing_strategy:
                errors.append(f"板块轮动策略缺少列：{missing_strategy}")
        
        return len(errors) == 0, errors
    
    def generate_validation_report(self, df: pd.DataFrame) -> str:
        """
        【优化】生成数据验证报告
        :param df: 数据 DataFrame
        :return: 报告文本
        """
        consistency_result, consistency_errors = self.validate_data_consistency(
            df, 
            ['ts_code', 'trade_date', 'close', 'vol']
        )
        
        local_result = self.validate_local_data(df)
        future_result = self.check_future_function(df)
        
        report_lines = [
            "=" * 60,
            "【数据质量验证报告】",
            "=" * 60,
            f"数据总量：{local_result['total_rows']}行",
            f"股票数量：{local_result['total_stocks']}只",
            f"日期范围：{local_result['date_range']}",
            f"数据缺失率：{local_result['missing_data_ratio']}%",
            f"异常数据量：{local_result['abnormal_data_count']}条",
            "",
            "【一致性检查】",
            f"状态：{'✅ 通过' if consistency_result else '❌ 未通过'}",
        ]
        
        if consistency_errors:
            for error in consistency_errors:
                report_lines.append(f"  - {error}")
        
        report_lines.append("")
        report_lines.append("【未来函数检查】")
        report_lines.append(f"状态：{'⚠️  发现风险' if future_result['has_future_function'] else '✅ 无风险'}")
        
        if future_result['suspicious_columns']:
            for col in future_result['suspicious_columns']:
                report_lines.append(f"  - 可疑列：{col}")
        
        report_lines.append("")
        report_lines.append("【综合评估】")
        overall_valid = consistency_result and local_result['is_valid']
        report_lines.append(f"数据质量：{'✅ 合格' if overall_valid else '❌ 不合格'}")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def generate_integrity_report(
        self, 
        df: pd.DataFrame,
        strategy_type: str = None,
        trade_calendar: List = None,
        date_range: tuple = None
    ) -> str:
        """
        【优化】生成数据完整性报告 - 包含字段、记录数、连续性检查
        :param df: 数据 DataFrame
        :param strategy_type: 策略类型
        :param trade_calendar: 交易日历列表
        :param date_range: 日期范围元组
        :return: 完整性报告文本
        """
        integrity_result = self.validate_data_integrity(
            df, 
            strategy_type=strategy_type,
            trade_calendar=trade_calendar,
            date_range=date_range
        )
        
        report_lines = [
            "=" * 70,
            "【数据完整性校验报告】",
            "=" * 70,
            f"生成时间：{integrity_result['timestamp']}",
            f"综合得分：{integrity_result['overall_score']}/100",
            f"校验结果：{'✅ 通过' if integrity_result['is_valid'] else '❌ 未通过'}",
            "",
            "-" * 70,
            "【1. 字段完整性检查】",
            "-" * 70,
        ]
        
        field_report = integrity_result['field_completeness']
        if field_report:
            status = '✅ 完整' if field_report['is_complete'] else '❌ 不完整'
            report_lines.append(f"状态：{status}")
            
            if field_report['missing_base_fields']:
                report_lines.append(f"❌ 缺失基础字段：{field_report['missing_base_fields']}")
            
            if field_report['missing_strategy_fields']:
                report_lines.append(f"⚠️  缺失策略字段：{field_report['missing_strategy_fields']}")
            
            if field_report['critical_null_fields']:
                report_lines.append("⚠️  关键字段空值问题：")
                for item in field_report['critical_null_fields']:
                    report_lines.append(f"   - {item['field']}: 空值率 {item['null_ratio']*100:.2f}%")
            
            if field_report['null_ratio_by_field']:
                report_lines.append("📊 字段空值统计：")
                for field, ratio in sorted(field_report['null_ratio_by_field'].items(), 
                                          key=lambda x: x[1], reverse=True)[:10]:
                    report_lines.append(f"   - {field}: {ratio*100:.2f}%")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【2. 记录数检查】")
        report_lines.append("-" * 70)
        
        record_report = integrity_result['record_count']
        if record_report:
            status = '✅ 合理' if record_report['is_reasonable'] else '❌ 不合理'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"总记录数：{record_report['total_records']}行")
            report_lines.append(f"股票数量：{record_report['total_stocks']}只")
            
            if record_report['expected_records'] > 0:
                report_lines.append(f"预期记录数：{record_report['expected_records']}行")
                report_lines.append(f"覆盖率：{record_report['coverage_ratio']*100:.2f}%")
            
            if record_report['insufficient_stocks']:
                report_lines.append(f"⚠️  记录数不足的股票 ({len(record_report['insufficient_stocks'])}只)：")
                for item in record_report['insufficient_stocks'][:5]:  # 只显示前 5 个
                    report_lines.append(f"   - {item['ts_code']}: {item['count']}行 (要求≥{item['min_required']}行)")
                if len(record_report['insufficient_stocks']) > 5:
                    report_lines.append(f"   ... 还有 {len(record_report['insufficient_stocks'])-5} 只")
            
            if record_report['abnormal_stocks']:
                report_lines.append(f"⚠️  记录数异常的股票 ({len(record_report['abnormal_stocks'])}只，可能重复)：")
                for item in record_report['abnormal_stocks'][:5]:
                    report_lines.append(f"   - {item['ts_code']}: {item['count']}行 (预期≤{item['expected_max']}行)")
                if len(record_report['abnormal_stocks']) > 5:
                    report_lines.append(f"   ... 还有 {len(record_report['abnormal_stocks'])-5} 只")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【3. 交易日连续性检查】")
        report_lines.append("-" * 70)
        
        continuity_report = integrity_result['trading_continuity']
        if continuity_report:
            status = '✅ 连续' if continuity_report['is_continuous'] else '❌ 不连续'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"实际交易日：{continuity_report['total_trading_days']}天")
            
            if continuity_report['expected_trading_days'] > 0:
                report_lines.append(f"预期交易日：{continuity_report['expected_trading_days']}天")
                report_lines.append(f"连续性比例：{continuity_report['continuity_ratio']*100:.2f}%")
            
            if continuity_report['missing_days']:
                report_lines.append(f"❌ 缺失交易日 ({len(continuity_report['missing_days'])}天)：")
                # 显示前 10 个缺失日期
                missing_sample = continuity_report['missing_days'][:10]
                report_lines.append(f"   {', '.join(missing_sample)}")
                if len(continuity_report['missing_days']) > 10:
                    report_lines.append(f"   ... 还有 {len(continuity_report['missing_days'])-10} 天")
            
            if continuity_report['extra_days']:
                report_lines.append(f"⚠️  多余日期 ({len(continuity_report['extra_days'])}天，不在交易日历中)：")
                extra_sample = continuity_report['extra_days'][:10]
                report_lines.append(f"   {', '.join(extra_sample)}")
            
            if continuity_report['gap_periods']:
                report_lines.append(f"⚠️  日期中断期 ({len(continuity_report['gap_periods'])}个)：")
                for gap in continuity_report['gap_periods'][:5]:
                    report_lines.append(f"   - {gap['start']} 至 {gap['end']} (中断{gap['gap_days']}天)")
                if len(continuity_report['gap_periods']) > 5:
                    report_lines.append(f"   ... 还有 {len(continuity_report['gap_periods'])-5} 个中断期")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【4. 问题汇总与建议】")
        report_lines.append("-" * 70)
        
        if integrity_result['issues']:
            report_lines.append("📋 发现的问题：")
            for i, issue in enumerate(integrity_result['issues'], 1):
                report_lines.append(f"   {i}. [{issue['severity']}] {issue['type']}: {issue['details']}")
        else:
            report_lines.append("✅ 未发现明显问题")
        
        if integrity_result['recommendations']:
            report_lines.append("")
            report_lines.append("💡 改进建议：")
            for i, rec in enumerate(integrity_result['recommendations'], 1):
                report_lines.append(f"   {i}. {rec}")
        
        report_lines.append("")
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
    
    def generate_accuracy_report(
        self, 
        df: pd.DataFrame
    ) -> str:
        """
        【优化】生成数据准确性报告 - 包含价格逻辑、范围、异常值检查
        :param df: 数据 DataFrame
        :return: 准确性报告文本
        """
        accuracy_result = self.validate_data_accuracy(df)
        
        report_lines = [
            "=" * 70,
            "【数据准确性校验报告】",
            "=" * 70,
            f"生成时间：{accuracy_result['timestamp']}",
            f"综合得分：{accuracy_result['overall_score']}/100",
            f"校验结果：{'✅ 通过' if accuracy_result['is_valid'] else '❌ 未通过'}",
            "",
            "-" * 70,
            "【1. 价格逻辑检查】",
            "-" * 70,
        ]
        
        price_logic = accuracy_result['price_logic']
        if price_logic:
            status = '✅ 通过' if price_logic['is_valid'] else '❌ 未通过'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"总记录数：{price_logic['total_records']}行")
            report_lines.append(f"无效记录数：{price_logic['invalid_records']}行")
            report_lines.append(f"错误率：{price_logic['invalid_rate']}%")
            
            if price_logic['error_types']:
                report_lines.append("错误类型统计：")
                for error_type, count in price_logic['error_types'].items():
                    if count > 0:
                        report_lines.append(f"   - {error_type}: {count}条")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【2. 数值范围检查】")
        report_lines.append("-" * 70)
        
        price_range = accuracy_result['price_range']
        if price_range:
            status = '✅ 通过' if price_range['is_valid'] else '❌ 未通过'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"检查的价格列：{', '.join(price_range['price_columns'])}")
            report_lines.append(f"有效范围：({self.price_min}, {self.price_max})")
            report_lines.append(f"超出范围记录数：{price_range['total_out_of_range']}条")
            report_lines.append(f"异常率：{price_range['out_of_range_rate']}%")
            
            if price_range['out_of_range_records']:
                report_lines.append("分列统计：")
                for col, stats in price_range['out_of_range_records'].items():
                    if stats['total'] > 0:
                        report_lines.append(f"   - {col}: {stats['below_min']}条≤{self.price_min}, {stats['above_max']}条≥{self.price_max}")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【3. 价格异常值检测】")
        report_lines.append("-" * 70)
        
        price_outliers = accuracy_result['price_change_outliers']
        if price_outliers:
            status = '✅ 正常' if price_outliers['is_valid'] else '⚠️  异常'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"总记录数：{price_outliers['total_records']}行")
            report_lines.append(f"股票数量：{price_outliers['total_stocks']}只")
            report_lines.append(f"3σ原则异常值：{price_outliers['outliers_3sigma']}条")
            report_lines.append(f"涨跌幅>20% 异常值：{price_outliers['outliers_change_20pct']}条")
            
            if price_outliers['outliers_by_market']:
                report_lines.append("分市场统计：")
                for market, stats in price_outliers['outliers_by_market'].items():
                    market_name = {'main': '主板', 'chinext': '创业板', 'star': '科创板'}.get(market, market)
                    report_lines.append(f"   - {market_name}（限制{stats['limit']*100}%）: {stats['count']}条异常")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【4. 成交量异常检测】")
        report_lines.append("-" * 70)
        
        vol_outliers = accuracy_result['volume_outliers']
        if vol_outliers:
            status = '✅ 正常' if vol_outliers['is_valid'] else '⚠️  异常'
            report_lines.append(f"状态：{status}")
            report_lines.append(f"总记录数：{vol_outliers['total_records']}行")
            report_lines.append(f"股票数量：{vol_outliers['total_stocks']}只")
            report_lines.append(f"成交量变化>10 倍异常值：{vol_outliers['volume_outliers']}条")
            report_lines.append(f"异常率：{vol_outliers['outlier_rate']}%")
        
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("【5. 问题汇总与建议】")
        report_lines.append("-" * 70)
        
        if accuracy_result['issues']:
            report_lines.append("📋 发现的问题：")
            for i, issue in enumerate(accuracy_result['issues'], 1):
                report_lines.append(f"   {i}. [{issue['severity']}] {issue['type']}: {issue['details']}")
        else:
            report_lines.append("✅ 未发现明显问题")
        
        if accuracy_result['recommendations']:
            report_lines.append("")
            report_lines.append("💡 改进建议：")
            for i, rec in enumerate(accuracy_result['recommendations'], 1):
                report_lines.append(f"   {i}. {rec}")
        
        report_lines.append("")
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
