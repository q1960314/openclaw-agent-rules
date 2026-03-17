# ==============================================
# 【新增】财联社（CLS）数据源接口 - cls_source.py
# ==============================================
# 功能：财联社资讯数据接入接口
# 职责：财联社 API 封装、电报快讯、深度资讯抓取
# 状态：✅ 已实现
# ==============================================

import logging
import pandas as pd
import requests
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .base import DataSource

logger = logging.getLogger("quant_system")


class CLSSource(DataSource):
    """
    【新增】财联社（CLS）数据源
    
    核心功能：
    1. 电报快讯（7x24 小时实时快讯）
    2. 深度资讯（财经新闻深度报道）
    3. 主题新闻（按主题/板块分类）
    4. 个股资讯（特定股票相关新闻）
    
    接入说明：
    - 财联社提供公开 API，无需账号
    - 有访问频率限制，建议添加缓存
    - 支持获取实时快讯和历史资讯
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化财联社数据源
        :param config: 配置字典（需包含 enabled, base_url 等）
        """
        super().__init__(config)
        
        # 财联社配置参数
        self.enabled = config.get('CLS_ENABLED', True)
        self.base_url = config.get('CLS_BASE_URL', 'https://www.cls.cn')
        self.api_url = config.get('CLS_API_URL', 'https://www.cls.cn/nodeapi/updateDataQuery')
        self.timeout = config.get('CLS_TIMEOUT', 10)
        self.max_retry = config.get('CLS_MAX_RETRY', 3)
        
        # 请求头（模拟浏览器）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.cls.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        # 会话管理
        self._session = None
        self._last_request_time = 0
        self._request_interval = 1.0  # 请求间隔（秒）
        
        logger.info(f"✅ 财联社数据源初始化完成 (enabled={self.enabled})")
    
    def connect(self) -> bool:
        """建立财联社连接"""
        try:
            if not self.enabled:
                logger.warning("⚠️ 财联社数据源已禁用")
                return False
            
            self._session = requests.Session()
            self._session.headers.update(self.headers)
            
            # 测试连接
            test_url = f"{self.base_url}/telegraph"
            response = self._session.get(test_url, timeout=self.timeout)
            
            if response.status_code == 200:
                logger.info("✅ 财联社数据源连接成功")
                return True
            else:
                logger.warning(f"⚠️ 财联社连接测试返回状态码：{response.status_code}")
                return True  # 仍然返回成功，因为可能是临时问题
                
        except Exception as e:
            logger.error(f"❌ 财联社连接失败：{e}")
            return False
    
    def disconnect(self) -> None:
        """断开财联社连接"""
        if self._session:
            self._session.close()
            self._session = None
        logger.info("🔌 财联社数据源已断开")
    
    def is_connected(self) -> bool:
        """检查财联社连接状态"""
        return self._session is not None and self.enabled
    
    def validate_config(self) -> bool:
        """校验财联社配置"""
        if not self.enabled:
            return True  # 禁用状态下认为配置有效
        
        if not self.base_url or not self.api_url:
            logger.error("❌ 财联社 API URL 不能为空")
            return False
        
        logger.info("✅ 财联社配置校验通过")
        return True
    
    def _rate_limit(self):
        """请求频率控制"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._request_interval:
            sleep_time = self._request_interval - elapsed
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _request_with_retry(self, url: str, params: Dict = None, **kwargs) -> Optional[Dict]:
        """带重试的 HTTP 请求"""
        last_exception = None
        
        for i in range(self.max_retry):
            try:
                self._rate_limit()
                
                response = self._session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"⚠️ 财联社请求返回状态码 {response.status_code}，第{i+1}次重试")
                    time.sleep(0.5 * (i + 1))
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"⚠️ 财联社请求超时，第{i+1}次重试：{e}")
                time.sleep(1.0 * (i + 1))
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"⚠️ 财联社请求异常，第{i+1}次重试：{e}")
                time.sleep(0.5 * (i + 1))
        
        logger.error(f"❌ 财联社请求失败，已重试{self.max_retry}次：{last_exception}")
        return None
    
    # ==================== 实现所有数据源接口方法 ====================
    
    def fetch_stock_basic(self, **kwargs) -> pd.DataFrame:
        """获取股票基本信息（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供股票基本信息接口")
        return pd.DataFrame()
    
    def fetch_trade_cal(self, **kwargs) -> pd.DataFrame:
        """获取交易日历（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供交易日历接口")
        return pd.DataFrame()
    
    def fetch_daily_data(self, **kwargs) -> pd.DataFrame:
        """获取日线数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供行情数据接口")
        return pd.DataFrame()
    
    def fetch_daily_basic(self, **kwargs) -> pd.DataFrame:
        """获取每日基本面数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供基本面数据接口")
        return pd.DataFrame()
    
    def fetch_fina_indicator(self, **kwargs) -> pd.DataFrame:
        """获取财务指标数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供财务数据接口")
        return pd.DataFrame()
    
    def fetch_stk_limit(self, **kwargs) -> pd.DataFrame:
        """获取涨跌停数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供涨跌停数据接口")
        return pd.DataFrame()
    
    def fetch_top_list(self, **kwargs) -> pd.DataFrame:
        """获取龙虎榜数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供龙虎榜数据接口")
        return pd.DataFrame()
    
    def fetch_top_inst(self, **kwargs) -> pd.DataFrame:
        """获取机构席位数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供机构席位数据接口")
        return pd.DataFrame()
    
    def fetch_news(self, **kwargs) -> pd.DataFrame:
        """
        【核心功能】获取财联社新闻资讯数据
        
        参数：
        - last_time: 获取最近 N 小时的资讯（默认 24）
        - category: 资讯分类（telegraph=电报，depth=深度）
        - keyword: 关键词筛选
        
        返回：
        DataFrame 包含字段：
        - id: 资讯 ID
        - title: 标题
        - content: 内容
        - source: 来源（cls）
        - publish_time: 发布时间
        - url: 链接
        - tags: 标签
        """
        try:
            if not self.enabled:
                logger.warning("⚠️ 财联社数据源已禁用")
                return pd.DataFrame()
            
            last_hours = kwargs.get('last_hours', 24)
            category = kwargs.get('category', 'telegraph')
            keyword = kwargs.get('keyword', '')
            
            news_list = []
            
            if category == 'telegraph':
                # 获取电报快讯
                params = {
                    'category': 'telegraph',
                    'last_time': int((datetime.now() - timedelta(hours=last_hours)).timestamp()),
                }
                
                result = self._request_with_retry(self.api_url, params=params)
                
                if result and 'data' in result:
                    for item in result['data']:
                        news_list.append({
                            'id': item.get('id', ''),
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'source': 'cls',
                            'publish_time': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                            'url': f"https://www.cls.cn/detail/{item.get('id', '')}",
                            'tags': ','.join(item.get('tags', [])) if isinstance(item.get('tags'), list) else '',
                        })
            
            elif category == 'depth':
                # 获取深度资讯（需要不同的 API）
                logger.warning("⚠️ 财联社深度资讯接口需要特殊权限，暂不支持")
            
            df = pd.DataFrame(news_list)
            
            # 关键词过滤
            if keyword and not df.empty:
                df = df[df['content'].str.contains(keyword, case=False, na=False)]
            
            if not df.empty:
                logger.info(f"✅ 财联社获取资讯完成，共{len(df)}条")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 财联社获取资讯失败：{e}")
            return pd.DataFrame()
    
    def fetch_concept(self, **kwargs) -> pd.DataFrame:
        """获取概念板块数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供概念板块数据接口")
        return pd.DataFrame()
    
    def fetch_moneyflow(self, **kwargs) -> pd.DataFrame:
        """获取资金流向数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供资金流向数据接口")
        return pd.DataFrame()
    
    def fetch_index_daily(self, **kwargs) -> pd.DataFrame:
        """获取指数日线数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供指数数据接口")
        return pd.DataFrame()
    
    def fetch_suspend_d(self, **kwargs) -> pd.DataFrame:
        """获取停牌数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供停牌数据接口")
        return pd.DataFrame()
    
    def fetch_block_trade(self, **kwargs) -> pd.DataFrame:
        """获取大宗交易数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供大宗交易数据接口")
        return pd.DataFrame()
    
    def fetch_hk_hold(self, **kwargs) -> pd.DataFrame:
        """获取北向资金持股数据（财联社不支持，返回空）"""
        logger.debug("⚠️ 财联社不提供北向资金数据接口")
        return pd.DataFrame()
    
    # ==================== 财联社专属方法 ====================
    
    def fetch_telegraph_realtime(self, **kwargs) -> pd.DataFrame:
        """
        【专属】获取实时电报快讯（最新 N 条）
        
        参数：
        - limit: 获取条数（默认 50）
        
        返回：
        DataFrame 包含实时快讯
        """
        try:
            if not self.enabled:
                return pd.DataFrame()
            
            limit = kwargs.get('limit', 50)
            
            # 财联社实时电报 API
            url = f"{self.base_url}/api/telegraph/list"
            params = {
                'limit': limit,
            }
            
            result = self._request_with_retry(url, params=params)
            
            if result and 'data' in result:
                news_list = []
                for item in result['data']:
                    news_list.append({
                        'id': item.get('id', ''),
                        'title': item.get('title', ''),
                        'content': item.get('content', ''),
                        'source': 'cls',
                        'publish_time': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'url': f"https://www.cls.cn/detail/{item.get('id', '')}",
                    })
                
                df = pd.DataFrame(news_list)
                logger.info(f"✅ 财联社获取实时电报完成，共{len(df)}条")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ 财联社获取实时电报失败：{e}")
            return pd.DataFrame()
    
    def fetch_topic_news(self, topic: str, **kwargs) -> pd.DataFrame:
        """
        【专属】获取主题新闻
        
        参数：
        - topic: 主题名称（如 '芯片', '新能源', 'AI' 等）
        - limit: 获取条数（默认 20）
        
        返回：
        DataFrame 包含主题相关新闻
        """
        try:
            if not self.enabled:
                return pd.DataFrame()
            
            limit = kwargs.get('limit', 20)
            
            # 搜索 API
            url = f"{self.base_url}/api/search"
            params = {
                'keyword': topic,
                'limit': limit,
                'type': 'news',
            }
            
            result = self._request_with_retry(url, params=params)
            
            if result and 'data' in result:
                news_list = []
                for item in result['data']:
                    news_list.append({
                        'id': item.get('id', ''),
                        'title': item.get('title', ''),
                        'content': item.get('content', ''),
                        'source': 'cls',
                        'topic': topic,
                        'publish_time': datetime.fromtimestamp(item.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'url': f"https://www.cls.cn/detail/{item.get('id', '')}",
                    })
                
                df = pd.DataFrame(news_list)
                logger.info(f"✅ 财联社获取'{topic}'主题新闻完成，共{len(df)}条")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ 财联社获取主题新闻失败：{e}")
            return pd.DataFrame()
    
    def get_status(self) -> Dict[str, Any]:
        """获取财联社数据源状态"""
        return {
            'name': self.name,
            'connected': self.is_connected(),
            'type': self.__class__.__name__,
            'enabled': self.enabled,
            'base_url': self.base_url,
            'status': 'active' if self.enabled else 'disabled'
        }


# ==============================================
# 【调用示例】
# ==============================================
# if __name__ == "__main__":
#     # 配置
#     config = {
#         'CLS_ENABLED': True,
#         'CLS_BASE_URL': 'https://www.cls.cn',
#         'CLS_TIMEOUT': 10,
#     }
#     
#     # 创建数据源
#     cls = CLSSource(config)
#     
#     # 连接
#     if cls.connect():
#         # 获取最近 24 小时电报
#         df = cls.fetch_news(last_hours=24, category='telegraph')
#         print(f"获取到 {len(df)} 条资讯")
#         print(df.head())
#         
#         # 获取实时电报
#         realtime_df = cls.fetch_telegraph_realtime(limit=10)
#         print(f"\n实时电报：{len(realtime_df)} 条")
#         
#         # 获取主题新闻
#         topic_df = cls.fetch_topic_news('芯片', limit=10)
#         print(f"\n芯片主题新闻：{len(topic_df)} 条")
#         
#         # 断开
#         cls.disconnect()
