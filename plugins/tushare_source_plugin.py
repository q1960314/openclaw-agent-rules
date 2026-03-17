# ==============================================
# 【优化】示例数据源插件 - Tushare 数据源
# ==============================================
# 功能：实现 Tushare 数据源插件，演示数据源插件的完整实现
# 职责：Tushare API 封装、连接管理、数据抓取、限流控制
# ==============================================

import os
import time
import logging
import pandas as pd
from typing import Optional, Dict, Any, List
from threading import Lock
from datetime import datetime

from plugins.plugin_base import PluginInfo
from plugins.data_source_plugin import DataSourcePlugin

logger = logging.getLogger("quant_system")


class TushareDataSourcePlugin(DataSourcePlugin):
    """
    【优化】Tushare 数据源插件实现
    基于原有 TushareSource 改造，支持插件化架构
    
    核心功能：
    1. Tushare API 连接管理
    2. 令牌桶限流（秒级 + 分钟级）
    3. 自动重试机制
    4. 请求统计和监控
    """
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        """获取插件元信息"""
        return PluginInfo(
            name="tushare_data_source",
            version="1.0.0",
            author="quant-system",
            description="Tushare 数据源：A 股数据接入，支持日线/基本面/龙虎榜等数据",
            plugin_type="data_source",
            dependencies=[],  # 无依赖
            config={
                "TUSHARE_TOKEN": "",
                "TUSHARE_API_URL": "http://api.tushare.pro",
                "max_requests_per_second": 10,
                "max_requests_per_minute": 100,
            }
        )
    
    def __init__(self, plugin_info: PluginInfo):
        """初始化 Tushare 数据源插件"""
        super().__init__(plugin_info)
        
        # 从配置获取 Tushare 参数
        self.token = plugin_info.config.get('TUSHARE_TOKEN', '')
        self.api_url = plugin_info.config.get('TUSHARE_API_URL', 'http://api.tushare.pro')
        
        # 限流配置
        self.max_requests_per_second = plugin_info.config.get('max_requests_per_second', 10)
        self.max_requests_per_minute = plugin_info.config.get('max_requests_per_minute', 100)
        
        # 令牌桶限流
        self.second_tokens = 0.0
        self.minute_tokens = 0.0
        self.last_second_update = time.time()
        self.last_minute_update = time.time()
        self._lock = Lock()
        
        # Tushare Pro API 实例（延迟初始化）
        self._pro = None
    
    def validate_config(self) -> bool:
        """
        【实现】校验 Tushare 配置
        """
        if not self.token:
            logger.error("❌ Tushare Token 不能为空")
            return False
        
        if len(self.token) < 32:
            logger.error("❌ Tushare Token 格式错误")
            return False
        
        logger.info("✅ Tushare 配置校验通过")
        return True
    
    def connect(self) -> bool:
        """
        【实现】建立 Tushare 连接
        """
        try:
            if self._pro is None:
                self._init_tushare()
            
            if self._pro is not None:
                self._connected = True
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
        self._connected = False
        logger.info(f"🔌 Tushare 数据源已断开")
    
    def is_connected(self) -> bool:
        """
        【实现】检查 Tushare 连接状态
        """
        return self._connected and self._pro is not None
    
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
    
    @property
    def pro(self):
        """延迟加载 Tushare Pro API"""
        if self._pro is None:
            self._init_tushare()
        return self._pro
    
    def rate_limit(self) -> None:
        """
        【实现】分钟级 + 秒级双重令牌桶限流
        """
        with self._lock:
            current_time = time.time()
            
            # 计算令牌补充速率
            second_refill_rate = self.max_requests_per_second
            minute_refill_rate = self.max_requests_per_minute / 60.0
            
            # 秒级令牌桶
            elapsed_second = current_time - self.last_second_update
            self.second_tokens = min(
                self.max_requests_per_second,
                self.second_tokens + elapsed_second * second_refill_rate
            )
            self.last_second_update = current_time
            
            second_wait_time = 0.0
            if self.second_tokens < 1.0:
                second_wait_time = (1.0 - self.second_tokens) / second_refill_rate
            
            # 分钟级令牌桶
            elapsed_minute = current_time - self.last_minute_update
            self.minute_tokens = min(
                self.max_requests_per_minute,
                self.minute_tokens + elapsed_minute * minute_refill_rate
            )
            self.last_minute_update = current_time
            
            minute_wait_time = 0.0
            if self.minute_tokens < 1.0:
                minute_wait_time = (1.0 - self.minute_tokens) / minute_refill_rate
            
            # 综合等待
            total_wait_time = max(second_wait_time, minute_wait_time)
            
            if total_wait_time > 0:
                time.sleep(total_wait_time)
                self.second_tokens = max(0.0, self.second_tokens - 1.0)
                self.minute_tokens = max(0.0, self.minute_tokens - 1.0)
                
                logger.debug(
                    f"⏱️ Tushare 限流 | 等待={total_wait_time:.3f}s | "
                    f"秒级令牌={self.second_tokens:.2f}/{self.max_requests_per_second} | "
                    f"分钟级令牌={self.minute_tokens:.2f}/{self.max_requests_per_minute}"
                )
            else:
                self.second_tokens -= 1.0
                self.minute_tokens -= 1.0
    
    def _request_with_retry(
        self,
        func,
        *args,
        max_retry: int = 3,
        timeout: int = 60,
        api_name: str = "",
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        【优化】带重试的请求封装
        """
        last_exception = None
        
        for i in range(max_retry):
            try:
                # 限流控制
                self.rate_limit()
                
                # 请求前回调
                self.on_request(api_name, kwargs)
                
                # 发送请求
                result = func(*args, **kwargs, timeout=timeout)
                
                if result is not None and not result.empty:
                    # 响应后回调（成功）
                    self.on_response(api_name, result, True)
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
        
        # 响应后回调（失败）
        self.on_response(api_name, pd.DataFrame(), False)
        
        logger.error(f"❌ Tushare 请求失败，已重试{max_retry}次：{last_exception}")
        return pd.DataFrame()
    
    # ==================== 实现所有数据源接口方法 ====================
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """【实现】获取股票基本信息"""
        try:
            exchange = kwargs.get('exchange', '')
            fields = kwargs.get('fields', 'ts_code,symbol,name,area,industry,market,list_date')
            
            df = self._request_with_retry(
                self.pro.stock_basic,
                exchange=exchange,
                fields=fields,
                api_name='stock_basic'
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
                end_date=end_date,
                api_name='trade_cal'
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
                end_date=end_date,
                api_name='daily'
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
            fields = kwargs.get(
                'fields',
                'ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            )
            
            df = self._request_with_retry(
                self.pro.daily_basic,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields=fields,
                api_name='daily_basic'
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
                end_date=end_date,
                api_name='fina_indicator'
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
                trade_date=trade_date,
                api_name='stk_limit'
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
                trade_date=trade_date,
                api_name='top_list'
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
                trade_date=trade_date,
                api_name='top_inst'
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
                end_date=end_date,
                api_name='news'
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
                ts_code=ts_code,
                api_name='concept_detail'
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
                end_date=end_date,
                api_name='moneyflow'
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
                end_date=end_date,
                api_name='index_daily'
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
                end_date=end_date,
                api_name='suspend_d'
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
                trade_date=trade_date,
                api_name='block_trade'
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
                end_date=end_date,
                api_name='hk_hold'
            )
            
            return df
        except Exception as e:
            logger.warning(f"⚠️ Tushare 获取北向资金持股数据失败：{e}")
            return pd.DataFrame()
