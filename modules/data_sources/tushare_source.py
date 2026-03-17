# ==============================================
# 【优化】Tushare 数据源插件 - tushare_source.py
# ==============================================
# 功能：实现 Tushare 数据源接入，继承 DataSource 基类
# 职责：Tushare API 封装、连接管理、数据抓取
# ==============================================

import os
import time
import logging
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

from .base import DataSource

logger = logging.getLogger("quant_system")


class TushareSource(DataSource):
    """
    【优化】Tushare 数据源实现
    基于原有 DataFetcher 逻辑重构，支持插件化接入
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Tushare 数据源
        :param config: 配置字典（需包含 TUSHARE_TOKEN, TUSHARE_API_URL 等）
        """
        super().__init__(config)
        
        # 【优化】从配置获取 Tushare 参数
        self.token = config.get('TUSHARE_TOKEN', '')
        self.api_url = config.get('TUSHARE_API_URL', 'http://api.tushare.pro')
        
        # 【优化】限流配置
        self.fetch_optimization = config.get('FETCH_OPTIMIZATION', {})
        self.max_rps = self.fetch_optimization.get('max_requests_per_second', 10)
        self.max_rpm = self.fetch_optimization.get('max_requests_per_minute', 100)
        
        # 【优化】令牌桶限流
        self.second_tokens = 0.0
        self.minute_tokens = 0.0
        self.last_second_update = time.time()
        self.last_minute_update = time.time()
        self._lock = Lock()
        
        # 【优化】统计计数器
        self.total_request_count = 0
        self.second_rate_limit_count = 0
        self.minute_rate_limit_count = 0
        self.total_wait_time = 0.0
        self.max_wait_time = 0.0
        self.min_wait_time = float('inf')
        
        # 【优化】Tushare Pro API 实例（延迟初始化）
        self._pro = None
    
    @property
    def pro(self):
        """延迟加载 Tushare Pro API"""
        if self._pro is None:
            self._init_tushare()
        return self._pro
    
    def _init_tushare(self):
        """初始化 Tushare Pro API 连接"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            self._pro = ts.pro()
            logger.info(f"✅ Tushare API 初始化成功")
        except Exception as e:
            logger.error(f"❌ Tushare API 初始化失败：{e}")
            self._pro = None
    
    def connect(self) -> bool:
        """
        【实现】建立 Tushare 连接
        :return: 连接是否成功
        """
        try:
            if self._pro is None:
                self._init_tushare()
            
            if self._pro is not None:
                self._initialized = True
                self._connection = self._pro
                logger.info(f"✅ Tushare 数据源连接成功")
                return True
            else:
                logger.error(f"❌ Tushare 数据源连接失败")
                return False
        except Exception as e:
            logger.error(f"❌ Tushare 连接异常：{e}")
            return False
    
    def disconnect(self) -> None:
        """
        【实现】断开 Tushare 连接
        """
        self._pro = None
        self._connection = None
        self._initialized = False
        logger.info(f"🔌 Tushare 数据源已断开")
    
    def is_connected(self) -> bool:
        """
        【实现】检查 Tushare 连接状态
        :return: 是否已连接
        """
        return self._initialized and self._pro is not None
    
    def validate_config(self) -> bool:
        """
        【实现】校验 Tushare 配置
        :return: 配置是否合法
        """
        if not self.token:
            logger.error("❌ Tushare Token 不能为空")
            return False
        
        if len(self.token) < 32:
            logger.error("❌ Tushare Token 格式错误")
            return False
        
        logger.info("✅ Tushare 配置校验通过")
        return True
    
    def _rate_limit(self):
        """
        【优化】分钟级 + 秒级双重令牌桶限流
        复用原有 DataFetcher 的限流逻辑
        """
        with self._lock:
            current_time = time.time()
            self.total_request_count += 1
            
            # 计算令牌补充速率
            second_refill_rate = self.max_rps
            minute_refill_rate = self.max_rpm / 60.0
            
            # 秒级令牌桶
            elapsed_second = current_time - self.last_second_update
            self.second_tokens = min(self.max_rps, self.second_tokens + elapsed_second * second_refill_rate)
            self.last_second_update = current_time
            
            second_wait_time = 0.0
            if self.second_tokens < 1.0:
                second_wait_time = (1.0 - self.second_tokens) / second_refill_rate
                self.second_rate_limit_count += 1
            
            # 分钟级令牌桶
            elapsed_minute = current_time - self.last_minute_update
            self.minute_tokens = min(self.max_rpm, self.minute_tokens + elapsed_minute * minute_refill_rate)
            self.last_minute_update = current_time
            
            minute_wait_time = 0.0
            if self.minute_tokens < 1.0:
                minute_wait_time = (1.0 - self.minute_tokens) / minute_refill_rate
                self.minute_rate_limit_count += 1
            
            # 综合等待
            total_wait_time = max(second_wait_time, minute_wait_time)
            
            if total_wait_time > 0:
                time.sleep(total_wait_time)
                self.total_wait_time += total_wait_time
                self.max_wait_time = max(self.max_wait_time, total_wait_time)
                self.min_wait_time = min(self.min_wait_time, total_wait_time)
                
                logger.debug(
                    f"⏱️ Tushare 限流 | 等待={total_wait_time:.3f}s | "
                    f"秒级令牌={self.second_tokens:.2f}/{self.max_rps} | "
                    f"分钟级令牌={self.minute_tokens:.2f}/{self.max_rpm}"
                )
                
                self.second_tokens = max(0.0, self.second_tokens - 1.0)
                self.minute_tokens = max(0.0, self.minute_tokens - 1.0)
            else:
                self.second_tokens -= 1.0
                self.minute_tokens -= 1.0
    
    def _request_with_retry(self, func, *args, max_retry: int = 3, timeout: int = 60, **kwargs) -> Optional[pd.DataFrame]:
        """
        【优化】带重试的请求封装
        :param func: Tushare 接口函数
        :param args: 位置参数
        :param max_retry: 最大重试次数
        :param timeout: 超时时间
        :param kwargs: 关键字参数
        :return: DataFrame
        """
        last_exception = None
        
        for i in range(max_retry):
            try:
                self._rate_limit()
                result = func(*args, **kwargs, timeout=timeout)
                
                if result is not None and not result.empty:
                    return result
                else:
                    time.sleep(0.2 * (i + 1))
                    continue
                    
            except Exception as e:
                last_exception = e
                error_msg = str(e)
                
                # 权限错误不重试
                if "权限不够" in error_msg or "积分不足" in error_msg:
                    logger.error(f"❌ Tushare 权限错误：{error_msg}")
                    break
                
                # 网络错误重试
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    logger.warning(f"⚠️ Tushare 网络错误，第{i+1}次重试：{error_msg}")
                    time.sleep(1.0 * (i + 1))
                    continue
                
                # 其他错误
                logger.warning(f"⚠️ Tushare 请求失败，第{i+1}次重试：{error_msg}")
                time.sleep(0.5 * (i + 1))
        
        logger.error(f"❌ Tushare 请求失败，已重试{max_retry}次：{last_exception}")
        return pd.DataFrame()
    
    # ==================== 实现所有抽象方法 ====================
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """【实现】获取股票基本信息"""
        try:
            exchange = kwargs.get('exchange', '')
            fields = kwargs.get('fields', 'ts_code,symbol,name,area,industry,market,list_date')
            
            df = self._request_with_retry(
                self.pro.stock_basic,
                exchange=exchange,
                fields=fields
            )
            
            if not df.empty:
                logger.info(f"✅ Tushare 获取股票列表完成，共{len(df)}只股票")
            
            return df
        except Exception as e:
            logger.error(f"❌ Tushare 获取股票列表失败：{e}")
            return pd.DataFrame()
    
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """【实现】获取交易日历"""
        try:
            exchange = kwargs.get('exchange', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.trade_cal,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )
            
            if not df.empty and 'cal_date' in df.columns and 'is_open' in df.columns:
                df['cal_date'] = pd.to_datetime(df['cal_date'], format="%Y%m%d")
                df = df[df['is_open'] == 1]['cal_date'].tolist()
                logger.info(f"✅ Tushare 获取交易日历完成，共{len(df)}个交易日")
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取交易日历失败：{e}")
            return pd.DataFrame()
    
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """【实现】获取日线数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取{kwargs.get('ts_code', '')}日线数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """【实现】获取每日基本面数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            fields = kwargs.get('fields', 'ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv')
            
            df = self._request_with_retry(
                self.pro.daily_basic,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields=fields
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取每日基本面数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """【实现】获取财务指标数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.fina_indicator,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取财务指标数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """【实现】获取涨跌停数据"""
        try:
            trade_date = kwargs.get('trade_date', '')
            
            df = self._request_with_retry(
                self.pro.stk_limit,
                trade_date=trade_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取涨跌停数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """【实现】获取龙虎榜数据"""
        try:
            trade_date = kwargs.get('trade_date', '')
            
            df = self._request_with_retry(
                self.pro.top_list,
                trade_date=trade_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取龙虎榜数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """【实现】获取机构席位数据"""
        try:
            trade_date = kwargs.get('trade_date', '')
            
            df = self._request_with_retry(
                self.pro.top_inst,
                trade_date=trade_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取机构席位数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """【实现】获取新闻资讯数据"""
        try:
            src = kwargs.get('src', 'sina')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.news,
                src=src,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取新闻数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """【实现】获取概念板块数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            
            df = self._request_with_retry(
                self.pro.concept_detail,
                ts_code=ts_code
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取概念板块数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """【实现】获取资金流向数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.moneyflow,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取资金流向数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """【实现】获取指数日线数据"""
        try:
            index_code = kwargs.get('index_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            exchange = kwargs.get('exchange', 'SSE')
            
            df = self._request_with_retry(
                self.pro.index_daily,
                exchange=exchange,
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取指数数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """【实现】获取停牌数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.suspend_d,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取停牌数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """【实现】获取大宗交易数据"""
        try:
            trade_date = kwargs.get('trade_date', '')
            
            df = self._request_with_retry(
                self.pro.block_trade,
                trade_date=trade_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取大宗交易数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """【实现】获取北向资金持股数据"""
        try:
            ts_code = kwargs.get('ts_code', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            df = self._request_with_retry(
                self.pro.hk_hold,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取北向资金持股数据失败：{e}")
            return pd.DataFrame()
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        【优化】获取限流统计信息
        :return: 限流统计字典
        """
        with self._lock:
            total_triggers = self.second_rate_limit_count + self.minute_rate_limit_count
            avg_wait = self.total_wait_time / max(1, total_triggers)
            rate_limit_ratio = total_triggers / max(1, self.total_request_count) * 100
            
            return {
                'total_requests': self.total_request_count,
                'second_limit_triggers': self.second_rate_limit_count,
                'minute_limit_triggers': self.minute_rate_limit_count,
                'total_triggers': total_triggers,
                'rate_limit_ratio': rate_limit_ratio,
                'total_wait_time': self.total_wait_time,
                'avg_wait_time': avg_wait,
                'max_wait_time': self.max_wait_time,
                'min_wait_time': self.min_wait_time if self.min_wait_time != float('inf') else 0.0,
                'current_second_tokens': self.second_tokens,
                'current_minute_tokens': self.minute_tokens,
            }
    
    def reset_rate_limit_stats(self):
        """【优化】重置限流统计计数器"""
        with self._lock:
            self.second_rate_limit_count = 0
            self.minute_rate_limit_count = 0
            self.total_request_count = 0
            self.total_wait_time = 0.0
            self.max_wait_time = 0.0
            self.min_wait_time = float('inf')
            logger.info("✅ Tushare 限流统计计数器已重置")
