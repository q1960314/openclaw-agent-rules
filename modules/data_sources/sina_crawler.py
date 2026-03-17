# ==============================================
# 【实时数据源】新浪财经爬虫集成
# ==============================================
# 功能：提供 A 股实时行情、分钟线数据
# 接口：
#   - 实时行情 API：http://hq.sinajs.cn/list={market}{code}
#   - 分钟线 API：http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/...
# ==============================================

import time
import logging
import pandas as pd
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import requests
from threading import Lock

from .base import DataSource

logger = logging.getLogger("quant_system")


class SinaCrawlerSource(DataSource):
    """
    【实时数据源】新浪财经爬虫
    基于新浪 HTTP API，提供实时行情和分钟线数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化新浪爬虫数据源
        :param config: 配置字典
        """
        super().__init__(config)
        
        # API 配置
        self.realtime_url = "http://hq.sinajs.cn/list={}"
        self.minute_url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        
        # 请求配置
        self.timeout = config.get('SINA_TIMEOUT', 10)
        self.max_retry = config.get('SINA_MAX_RETRY', 3)
        self.request_delay = config.get('SINA_REQUEST_DELAY', 0.1)  # 请求间隔（秒）
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'http://finance.sina.com.cn/',
        }
        
        # 缓存配置
        self.cache = {}
        self.cache_timeout = config.get('REALTIME_CACHE_TIMEOUT', 30)
        
        # 限流
        self._lock = Lock()
        self.last_request_time = 0
    
    def connect(self) -> bool:
        """建立连接（测试）"""
        try:
            # 测试获取平安银行行情
            test_data = self._fetch_realtime_single("sz000001")
            if test_data:
                self._initialized = True
                logger.info("✅ 新浪财经爬虫连接成功")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 新浪财经爬虫连接失败：{e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.cache.clear()
        self._initialized = False
        logger.info("🔌 新浪财经爬虫已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._initialized
    
    def _rate_limit(self):
        """请求限流"""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
            self.last_request_time = time.time()
    
    def _fetch_realtime_single(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【内部方法】获取单只股票实时行情
        :param stock_code: 股票代码（如 "sz000001" 或 "sh600000"）
        :return: 行情字典
        """
        try:
            self._rate_limit()
            
            url = self.realtime_url.format(stock_code)
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析返回数据
            # 格式：var hq_str_sz000001="平安银行，10.50,10.45,10.55,10.60,10.40,..."
            content = response.text.strip()
            match = re.search(r'="([^"]+)"', content)
            
            if not match:
                return None
            
            data_str = match.group(1)
            fields = data_str.split(',')
            
            if len(fields) < 32:
                return None
            
            # 解析字段
            result = {
                'name': fields[0],
                'open': float(fields[1]) if fields[1] else 0,
                'pre_close': float(fields[2]) if fields[2] else 0,
                'price': float(fields[3]) if fields[3] else 0,
                'high': float(fields[4]) if fields[4] else 0,
                'low': float(fields[5]) if fields[5] else 0,
                'bid': float(fields[6]) if fields[6] else 0,
                'ask': float(fields[7]) if fields[7] else 0,
                'volume': int(fields[8]) if fields[8] else 0,
                'amount': float(fields[9]) if fields[9] else 0,
                'b1_v': int(fields[10]) if fields[10] else 0,
                'b1_p': float(fields[11]) if fields[11] else 0,
                'b2_v': int(fields[12]) if fields[12] else 0,
                'b2_p': float(fields[13]) if fields[13] else 0,
                'b3_v': int(fields[14]) if fields[14] else 0,
                'b3_p': float(fields[15]) if fields[15] else 0,
                'b4_v': int(fields[16]) if fields[16] else 0,
                'b4_p': float(fields[17]) if fields[17] else 0,
                'b5_v': int(fields[18]) if fields[18] else 0,
                'b5_p': float(fields[19]) if fields[19] else 0,
                'a1_v': int(fields[20]) if fields[20] else 0,
                'a1_p': float(fields[21]) if fields[21] else 0,
                'a2_v': int(fields[22]) if fields[22] else 0,
                'a2_p': float(fields[23]) if fields[23] else 0,
                'a3_v': int(fields[24]) if fields[24] else 0,
                'a3_p': float(fields[25]) if fields[25] else 0,
                'a4_v': int(fields[26]) if fields[26] else 0,
                'a4_p': float(fields[27]) if fields[27] else 0,
                'a5_v': int(fields[28]) if fields[28] else 0,
                'a5_p': float(fields[29]) if fields[29] else 0,
                'date': fields[30] if len(fields) > 30 else '',
                'time': fields[31] if len(fields) > 31 else '',
            }
            
            # 计算涨跌幅
            if result['pre_close'] > 0:
                result['pct_change'] = (result['price'] - result['pre_close']) / result['pre_close'] * 100
                result['change'] = result['price'] - result['pre_close']
            else:
                result['pct_change'] = 0
                result['change'] = 0
            
            return result
        except Exception as e:
            logger.warning(f"⚠️ 新浪获取 {stock_code} 行情失败：{e}")
            return None
    
    def _format_stock_code(self, stock_code: str) -> str:
        """
        格式化股票代码为新浪格式
        :param stock_code: 原始代码（如 "000001" 或 "000001.SZ"）
        :return: 新浪格式（如 "sz000001"）
        """
        code = stock_code.replace(".", "").replace("_", "").strip()
        
        # 判断市场
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3'):
            return f"sz{code}"
        elif code.startswith('4') or code.startswith('8'):
            return f"bj{code}"
        else:
            # 默认按深市处理
            return f"sz{code}"
    
    # ==================== 核心接口 ====================
    
    def get_realtime_by_code(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        【核心接口】获取单只股票实时行情
        :param stock_code: 股票代码
        :return: 行情字典
        """
        try:
            sina_code = self._format_stock_code(stock_code)
            
            # 检查缓存
            cache_key = f"sina_{sina_code}"
            if cache_key in self.cache:
                data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    return data
            
            # 获取数据
            data = self._fetch_realtime_single(sina_code)
            
            if data:
                data['ts_code'] = stock_code
                self.cache[cache_key] = (data, time.time())
                return data
            else:
                return None
        except Exception as e:
            logger.error(f"❌ 新浪获取 {stock_code} 行情失败：{e}")
            return None
    
    def get_realtime_batch(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        【核心接口】批量获取股票实时行情
        :param stock_codes: 股票代码列表
        :return: 行情字典 {code: data}
        """
        results = {}
        
        for code in stock_codes:
            data = self.get_realtime_by_code(code)
            if data:
                results[code] = data
            time.sleep(self.request_delay)  # 避免请求过快
        
        return results
    
    def get_minute_data(self, stock_code: str, period: str = '5', count: int = 100) -> pd.DataFrame:
        """
        【核心接口】获取分钟线数据
        :param stock_code: 股票代码
        :param period: 周期（1/5/15/30/60 分钟）
        :param count: 获取条数
        :return: DataFrame(date, open, high, low, close, volume)
        """
        try:
            sina_code = self._format_stock_code(stock_code)
            
            params = {
                'symbol': sina_code,
                'scale': period,
                'datalen': str(count)
            }
            
            self._rate_limit()
            response = requests.get(self.minute_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data_list = response.json()
            
            if not data_list:
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame(data_list)
            df = df.rename(columns={
                'day': 'trade_time',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
            })
            
            df['ts_code'] = stock_code
            df['period'] = period
            
            logger.info(f"✅ 新浪获取 {stock_code} {period}分钟线成功，共{len(df)}条")
            return df
        except Exception as e:
            logger.error(f"❌ 新浪获取 {stock_code} 分钟线失败：{e}")
            return pd.DataFrame()
    
    def get_realtime_spot(self) -> pd.DataFrame:
        """
        【核心接口】获取市场实时行情（需配合股票列表）
        注意：新浪不提供全市场实时行情接口，需要已知股票列表
        :return: DataFrame
        """
        logger.warning("⚠️ 新浪爬虫不支持全市场实时行情，请使用 get_realtime_by_code 获取单只股票")
        return pd.DataFrame()
    
    # ==================== 实现基类抽象方法 ====================
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """获取股票基本信息（不支持）"""
        return pd.DataFrame()
    
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """交易日历（不支持）"""
        return pd.DataFrame()
    
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """日线数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """每日基本面（不支持）"""
        return pd.DataFrame()
    
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """财务指标（不支持）"""
        return pd.DataFrame()
    
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """涨跌停数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """龙虎榜（不支持）"""
        return pd.DataFrame()
    
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """机构席位（不支持）"""
        return pd.DataFrame()
    
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """新闻数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """概念板块（不支持）"""
        return pd.DataFrame()
    
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """资金流向（不支持）"""
        return pd.DataFrame()
    
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """指数日线（不支持）"""
        return pd.DataFrame()
    
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """停牌数据（不支持）"""
        return pd.DataFrame()
    
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """大宗交易（不支持）"""
        return pd.DataFrame()
    
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """北向资金持股（不支持）"""
        return pd.DataFrame()
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        return {
            'name': 'SinaCrawlerSource',
            'connected': self.is_connected(),
            'type': 'realtime',
            'cache_size': len(self.cache),
            'timeout': self.timeout,
        }


# ==================== 便捷函数 ====================

def sina_realtime_by_code(stock_code: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取单只股票实时行情"""
    source = SinaCrawlerSource({})
    if source.connect():
        return source.get_realtime_by_code(stock_code)
    return None


def sina_minute_data(stock_code: str, period: str = '5', count: int = 100) -> pd.DataFrame:
    """便捷函数：获取分钟线数据"""
    source = SinaCrawlerSource({})
    if source.connect():
        return source.get_minute_data(stock_code, period, count)
    return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("【新浪财经爬虫测试】")
    print("=" * 60)
    
    source = SinaCrawlerSource({})
    if source.connect():
        print("\n1️⃣ 测试平安银行实时行情...")
        data = source.get_realtime_by_code("000001.SZ")
        if data:
            print(f"✅ 平安银行：{data['name']} 价格={data['price']} 涨跌幅={data['pct_change']:.2f}%")
        
        print("\n2️⃣ 测试贵州茅台实时行情...")
        data = source.get_realtime_by_code("600519.SH")
        if data:
            print(f"✅ 贵州茅台：{data['name']} 价格={data['price']} 涨跌幅={data['pct_change']:.2f}%")
        
        print("\n3️⃣ 测试 5 分钟线数据...")
        df = source.get_minute_data("000001.SZ", period='5', count=10)
        if not df.empty:
            print(f"✅ 5 分钟线：{len(df)}条")
            print(df[['trade_time', 'open', 'high', 'low', 'close']].head())
        
        source.disconnect()
    else:
        print("❌ 连接失败")
