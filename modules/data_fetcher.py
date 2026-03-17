# ==============================================
# 【优化】数据抓取模块 - data_fetcher.py
# ==============================================
# 功能：负责所有 Tushare API 数据抓取、限流控制、重试机制
# 职责：数据请求、限流管理、错误处理、数据缓存
# ==============================================

import os
import time
import logging
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

logger = logging.getLogger("quant_system")


class DataFetcher:
    """
    【优化】数据抓取器
    职责：Tushare API 调用、限流控制、重试机制
    """
    
    def __init__(self, pro, config: Dict[str, Any]):
        """
        初始化数据抓取器
        :param pro: Tushare Pro API 实例
        :param config: 配置字典
        """
        self.pro = pro
        self.config = config
        self.request_count = 0
        self.window_start = time.time()
        self.minute_request_count = 0
        self.minute_window_start = time.time()
        self._lock = Lock()
        
        # 【优化】令牌桶限流优化：更平滑的令牌补充机制
        self.second_tokens = 0.0  # 秒级令牌桶当前令牌数
        self.minute_tokens = 0.0  # 分钟级令牌桶当前令牌数
        self.last_second_update = time.time()  # 上次秒级令牌更新时间
        self.last_minute_update = time.time()  # 上次分钟级令牌更新时间
        
        # 【优化】限流触发计数器（用于监控和调试）
        self.second_rate_limit_count = 0  # 秒级限流触发次数
        self.minute_rate_limit_count = 0  # 分钟级限流触发次数
        self.total_request_count = 0  # 总请求次数
        
        # 【优化】高级统计计数器
        self.total_wait_time = 0.0  # 累计等待时间（秒）
        self.last_request_time = time.time()  # 上次请求时间（用于计算请求间隔）
        self.max_wait_time = 0.0  # 最大单次等待时间
        self.min_wait_time = float('inf')  # 最小单次等待时间
    
    def _rate_limit(self):
        """
        【优化】分钟级 + 秒级双重令牌桶限流，更平滑的令牌补充机制
        令牌桶算法优势：
        1. 允许突发流量（桶内有令牌时可立即处理）
        2. 平滑限流（令牌按固定速率补充，避免硬重置）
        3. 更公平（不会在时间窗口边界产生请求尖峰）
        
        【优化点】：
        - 连续时间模型：令牌补充基于时间流逝，而非离散更新
        - 平滑等待：避免硬重置，保持令牌桶状态连续性
        - 详细日志：DEBUG 级别记录令牌桶状态、等待时间、请求间隔
        - 完善统计：累计等待时间、最大/最小等待时间、限流触发率
        """
        with self._lock:
            current_time = time.time()
            self.total_request_count += 1
            
            # 【优化】计算请求间隔（用于监控请求频率）
            request_interval = current_time - self.last_request_time
            self.last_request_time = current_time
            
            # 获取限流配置
            max_rps = self.config.get('FETCH_OPTIMIZATION', {}).get('max_requests_per_second', 10)
            max_rpm = self.config.get('FETCH_OPTIMIZATION', {}).get('max_requests_per_minute', 100)
            
            # 计算令牌补充速率
            second_refill_rate = max_rps  # 每秒补充 max_rps 个令牌
            minute_refill_rate = max_rpm / 60.0  # 每秒补充 max_rpm/60 个令牌
            
            # ==========================================
            # 【优化】秒级令牌桶：连续时间模型，更平滑的令牌补充
            # ==========================================
            elapsed_second = current_time - self.last_second_update
            # 【优化】按时间流逝连续补充令牌，避免离散更新导致的令牌突变
            self.second_tokens = min(max_rps, self.second_tokens + elapsed_second * second_refill_rate)
            self.last_second_update = current_time
            
            # 【优化】秒级限流判断与等待
            second_wait_time = 0.0
            if self.second_tokens < 1.0:
                # 【优化】计算需要等待的时间，使令牌刚好补充到 1 个
                second_wait_time = (1.0 - self.second_tokens) / second_refill_rate
                self.second_rate_limit_count += 1
            
            # ==========================================
            # 【优化】分钟级令牌桶：连续时间模型，更平滑的令牌补充
            # ==========================================
            elapsed_minute = current_time - self.last_minute_update
            # 【优化】按时间流逝连续补充令牌，避免离散更新导致的令牌突变
            self.minute_tokens = min(max_rpm, self.minute_tokens + elapsed_minute * minute_refill_rate)
            self.last_minute_update = current_time
            
            # 【优化】分钟级限流判断与等待
            minute_wait_time = 0.0
            if self.minute_tokens < 1.0:
                # 【优化】计算需要等待的时间，使令牌刚好补充到 1 个
                minute_wait_time = (1.0 - self.minute_tokens) / minute_refill_rate
                self.minute_rate_limit_count += 1
            
            # ==========================================
            # 【优化】综合等待策略：取最大等待时间，确保同时满足秒级和分钟级限流
            # ==========================================
            total_wait_time = max(second_wait_time, minute_wait_time)
            
            # 【优化】执行等待并更新统计
            if total_wait_time > 0:
                time.sleep(total_wait_time)
                
                # 【优化】更新等待时间统计
                self.total_wait_time += total_wait_time
                self.max_wait_time = max(self.max_wait_time, total_wait_time)
                self.min_wait_time = min(self.min_wait_time, total_wait_time)
                
                # 【优化】DEBUG 级别日志：详细记录限流状态
                logger.debug(
                    f"⏱️ 限流触发 | 总等待={total_wait_time:.3f}s | "
                    f"秒级令牌={self.second_tokens:.2f}/{max_rps} (等待{second_wait_time:.3f}s) | "
                    f"分钟级令牌={self.minute_tokens:.2f}/{max_rpm} (等待{minute_wait_time:.3f}s) | "
                    f"请求间隔={request_interval:.3f}s | "
                    f"秒级触发={self.second_rate_limit_count} | 分钟级触发={self.minute_rate_limit_count}"
                )
                
                # 【优化】消耗令牌（等待后令牌已补充到 1 个）
                self.second_tokens = max(0.0, self.second_tokens - 1.0)
                self.minute_tokens = max(0.0, self.minute_tokens - 1.0)
            else:
                # 【优化】无等待，直接消耗令牌
                self.second_tokens -= 1.0
                self.minute_tokens -= 1.0
                
                # 【优化】DEBUG 级别日志：记录正常请求
                logger.debug(
                    f"✅ 请求通过 | 令牌充足 | "
                    f"秒级令牌={self.second_tokens:.2f}/{max_rps} | "
                    f"分钟级令牌={self.minute_tokens:.2f}/{max_rpm} | "
                    f"请求间隔={request_interval:.3f}s"
                )
            
            # 【优化】定期输出限流统计（每 500 次请求，更频繁的监控）
            if self.total_request_count % 500 == 0:
                avg_wait = self.total_wait_time / max(1, self.second_rate_limit_count + self.minute_rate_limit_count)
                rate_limit_ratio = (self.second_rate_limit_count + self.minute_rate_limit_count) / self.total_request_count * 100
                logger.info(
                    f"📊 限流统计 | 总请求={self.total_request_count} | "
                    f"秒级触发={self.second_rate_limit_count} | 分钟级触发={self.minute_rate_limit_count} | "
                    f"限流比例={rate_limit_ratio:.2f}% | "
                    f"累计等待={self.total_wait_time:.2f}s | 平均等待={avg_wait:.3f}s | "
                    f"最大等待={self.max_wait_time:.3f}s | 最小等待={self.min_wait_time:.3f}s | "
                    f"平均请求间隔={request_interval:.3f}s"
                )
    
    def request_with_retry(
        self, 
        func, 
        *args, 
        max_retry: int = 3, 
        timeout: int = 60,
        silent: bool = False,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        【优化】接口请求重试，带指数退避 + 限流 + 错误码处理
        :param func: Tushare 接口函数
        :param args: 位置参数
        :param max_retry: 最大重试次数
        :param timeout: 超时时间（秒）
        :param silent: 是否静默模式
        :param kwargs: 关键字参数
        :return: 接口返回数据 DataFrame
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
                    logger.error(f"❌ 权限错误，停止重试：{error_msg}")
                    break
                
                # 网络错误重试
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    logger.warning(f"⚠️  网络错误，第{i+1}次重试：{error_msg}")
                    time.sleep(1.0 * (i + 1))
                    continue
                
                # 其他错误记录日志
                if not silent:
                    logger.warning(f"⚠️  接口请求失败，第{i+1}次重试：{error_msg}")
                time.sleep(0.5 * (i + 1))
        
        # 所有重试失败
        if not silent:
            logger.error(f"❌ 接口请求失败，已重试{max_retry}次：{last_exception}")
        return pd.DataFrame()
    
    def fetch_stock_basic(self, exchange: str = '') -> pd.DataFrame:
        """
        【优化】获取股票列表
        :param exchange: 交易所（''=全部）
        :return: 股票列表 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.stock_basic,
                exchange=exchange,
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            if not df.empty:
                logger.info(f"✅ 获取股票列表完成，共{len(df)}只股票")
            return df
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败：{e}")
            return pd.DataFrame()
    
    def fetch_trade_cal(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取交易日历
        :param start_date: 开始日期（YYYYMMDD）
        :param end_date: 结束日期（YYYYMMDD）
        :return: 交易日历 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.trade_cal,
                exchange='',
                start_date=start_date,
                end_date=end_date
            )
            if not df.empty and 'cal_date' in df.columns and 'is_open' in df.columns:
                df['cal_date'] = pd.to_datetime(df['cal_date'], format="%Y%m%d")
                df = df[df['is_open'] == 1]['cal_date'].tolist()
                logger.info(f"✅ 获取交易日历完成，共{len(df)}个交易日")
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取交易日历失败：{e}")
            return pd.DataFrame()
    
    def fetch_daily_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取个股日线数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 日线数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}日线数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取个股每日基本面数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 每日基本面数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.daily_basic,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}每日基本面数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_fina_indicator(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取个股财务指标数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 财务指标数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.fina_indicator,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}财务指标数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_stk_limit(self, trade_date: str) -> pd.DataFrame:
        """
        【优化】获取每日涨跌停数据
        :param trade_date: 交易日期
        :return: 涨跌停数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.stk_limit,
                trade_date=trade_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{trade_date}涨跌停数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_top_list(self, trade_date: str) -> pd.DataFrame:
        """
        【优化】获取龙虎榜每日明细
        :param trade_date: 交易日期
        :return: 龙虎榜数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.top_list,
                trade_date=trade_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{trade_date}龙虎榜数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_top_inst(self, trade_date: str) -> pd.DataFrame:
        """
        【优化】获取龙虎榜机构席位明细
        :param trade_date: 交易日期
        :return: 机构席位数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.top_inst,
                trade_date=trade_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{trade_date}机构席位数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_news(self, src: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取新闻资讯数据
        :param src: 资讯源（sina/cls/yicai 等）
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 新闻数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.news,
                src=src,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{src}新闻数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_concept(self, ts_code: str) -> pd.DataFrame:
        """
        【优化】获取股票概念板块数据
        :param ts_code: 股票代码
        :return: 概念板块数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.concept_detail,
                ts_code=ts_code
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}概念板块数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_moneyflow(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取个股资金流向数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 资金流向数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.moneyflow,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}资金流向数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_index_daily(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取指数日线数据
        :param index_code: 指数代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 指数日线数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.index_daily,
                exchange='SSE',
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{index_code}指数数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_suspend_d(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取股票停牌数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 停牌数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.suspend_d,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}停牌数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_block_trade(self, trade_date: str) -> pd.DataFrame:
        """
        【优化】获取大宗交易数据
        :param trade_date: 交易日期
        :return: 大宗交易数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.block_trade,
                trade_date=trade_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{trade_date}大宗交易数据失败：{e}")
            return pd.DataFrame()
    
    def fetch_hk_hold(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        【优化】获取北向资金持股数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 北向资金持股数据 DataFrame
        """
        try:
            df = self.request_with_retry(
                self.pro.hk_hold,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.warning(f"⚠️  获取{ts_code}北向资金持股数据失败：{e}")
            return pd.DataFrame()
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        【优化】获取限流统计信息（用于监控和调试）
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
        """
        【优化】重置限流统计计数器（用于新一轮统计）
        """
        with self._lock:
            self.second_rate_limit_count = 0
            self.minute_rate_limit_count = 0
            self.total_request_count = 0
            self.total_wait_time = 0.0
            self.max_wait_time = 0.0
            self.min_wait_time = float('inf')
            logger.info("✅ 限流统计计数器已重置")
