# ==============================================
# 【优化】因子库 - 23 维综合评分
# ==============================================
# 功能：提供技术面、资金面、情绪面因子
# 因子类型：
# 1. 技术面因子（10 个）
# 2. 资金面因子（8 个）
# 3. 情绪面因子（5 个）
# ==============================================

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("quant_system")


class FactorLibrary:
    """
    【优化】因子库
    提供 23 维综合评分所需的所有因子
    """
    
    def __init__(self):
        """初始化因子库"""
        self.factor_cache = {}
        self.factor_weights = self._get_default_weights()
    
    def _get_default_weights(self) -> Dict[str, float]:
        """获取默认因子权重"""
        return {
            # 技术面因子（总权重 0.45）
            'momentum_5d': 0.08,
            'momentum_20d': 0.08,
            'volatility': 0.05,
            'volume_ratio': 0.06,
            'ma_trend': 0.06,
            'rsi': 0.04,
            'macd': 0.04,
            'bollinger': 0.02,
            'atr': 0.01,
            'obv': 0.01,
            
            # 资金面因子（总权重 0.35）
            'northbound_flow': 0.08,
            'institutional_flow': 0.08,
            'main_force_flow': 0.10,
            'large_order_flow': 0.05,
            '资金流入加速度': 0.02,
            '主力持仓变化': 0.01,
            '机构调研': 0.005,
            '大宗交易': 0.005,
            
            # 情绪面因子（总权重 0.20）
            'limit_up_count': 0.04,
            'sentiment_index': 0.06,
            'turnover_rate': 0.04,
            'market_width': 0.03,
            'news_sentiment': 0.03,
        }
    
    # ==================== 技术面因子 ====================
    
    def momentum_factor(self, price: pd.Series, period: int = 20) -> pd.Series:
        """
        动量因子：N 日收益率
        :param price: 价格序列
        :param period: 周期
        :return: 动量因子
        """
        return price.pct_change(period)
    
    def momentum_5d_factor(self, price: pd.Series) -> pd.Series:
        """5 日动量因子"""
        return self.momentum_factor(price, 5)
    
    def volatility_factor(self, price: pd.Series, period: int = 20) -> pd.Series:
        """
        波动率因子：N 日波动率
        :param price: 价格序列
        :param period: 周期
        :return: 波动率因子
        """
        returns = price.pct_change()
        return returns.rolling(period).std()
    
    def volume_ratio_factor(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """
        成交量因子：当日成交量/N 日均量
        :param volume: 成交量序列
        :param period: 周期
        :return: 成交量比率
        """
        avg_volume = volume.rolling(period).mean()
        return volume / avg_volume
    
    def ma_trend_factor(self, price: pd.Series) -> pd.Series:
        """
        均线趋势因子：均线多头排列程度
        :param price: 价格序列
        :return: 趋势因子（0-1）
        """
        ma5 = price.rolling(5).mean()
        ma10 = price.rolling(10).mean()
        ma20 = price.rolling(20).mean()
        ma60 = price.rolling(60).mean()
        
        # 计算多头排列得分
        score = pd.Series(0, index=price.index)
        score += (ma5 > ma10).astype(float) * 0.25
        score += (ma10 > ma20).astype(float) * 0.25
        score += (ma20 > ma60).astype(float) * 0.25
        score += (price > ma5).astype(float) * 0.25
        
        return score
    
    def rsi_factor(self, price: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI 因子：相对强弱指标
        :param price: 价格序列
        :param period: 周期
        :return: RSI（归一化到 0-1）
        """
        delta = price.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        with np.errstate(divide='ignore', invalid='ignore'):
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
        
        # 归一化到 0-1
        return rsi / 100
    
    def macd_factor(self, price: pd.Series) -> pd.Series:
        """
        MACD 因子：MACD 指标强度
        :param price: 价格序列
        :return: MACD 因子（归一化）
        """
        exp1 = price.ewm(span=12, adjust=False).mean()
        exp2 = price.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        # MACD 与信号线的差值（归一化）
        diff = macd - signal
        # 使用历史百分位归一化
        return diff.rank(pct=True)
    
    def bollinger_factor(self, price: pd.Series, period: int = 20) -> pd.Series:
        """
        布林带因子：价格在布林带中的位置
        :param price: 价格序列
        :param period: 周期
        :return: 位置因子（0-1，0=下轨，1=上轨）
        """
        middle = price.rolling(period).mean()
        std = price.rolling(period).std()
        upper = middle + 2 * std
        lower = middle - 2 * std
        
        # 位置 = (价格 - 下轨) / (上轨 - 下轨)
        position = (price - lower) / (upper - lower)
        return position.clip(0, 1)
    
    def atr_factor(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                   period: int = 14) -> pd.Series:
        """
        ATR 因子：平均真实波幅（归一化）
        :param high: 最高价
        :param low: 最低价
        :param close: 收盘价
        :param period: 周期
        :return: ATR（归一化）
        """
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # 归一化：ATR/价格
        return atr / close
    
    def obv_factor(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        OBV 因子：能量潮
        :param close: 收盘价
        :param volume: 成交量
        :return: OBV（归一化）
        """
        direction = np.sign(close.diff())
        obv = (volume * direction).cumsum()
        
        # 归一化：使用历史百分位
        return obv.rank(pct=True)
    
    # ==================== 资金面因子 ====================
    
    def northbound_flow_factor(self, northbound_data: pd.DataFrame) -> pd.Series:
        """
        北向资金因子：北向资金净流入
        :param northbound_data: 北向资金数据
        :return: 资金流因子
        """
        if northbound_data is None or northbound_data.empty:
            return pd.Series(0)
        
        net_inflow = northbound_data['net_inflow']
        # 5 日累计
        return net_inflow.rolling(5).sum()
    
    def institutional_flow_factor(self, institutional_data: pd.DataFrame) -> pd.Series:
        """
        机构资金因子：机构净买入
        :param institutional_data: 机构交易数据
        :return: 资金流因子
        """
        if institutional_data is None or institutional_data.empty:
            return pd.Series(0)
        
        return institutional_data['net_buy']
    
    def main_force_flow_factor(self, top_list_data: pd.DataFrame) -> pd.Series:
        """
        主力资金因子：龙虎榜主力净买入
        :param top_list_data: 龙虎榜数据
        :return: 资金流因子
        """
        if top_list_data is None or top_list_data.empty:
            return pd.Series(0)
        
        return top_list_data['main_net_buy']
    
    def large_order_flow_factor(self, order_data: pd.DataFrame) -> pd.Series:
        """
        大单资金因子：大单净流入
        :param order_data: 订单数据
        :return: 资金流因子
        """
        if order_data is None or order_data.empty:
            return pd.Series(0)
        
        large_buy = order_data['large_buy_volume']
        large_sell = order_data['large_sell_volume']
        
        return (large_buy - large_sell) / (large_buy + large_sell + 1e-8)
    
    def capital_flow_acceleration_factor(self, flow_data: pd.Series) -> pd.Series:
        """
        资金流入加速度因子
        :param flow_data: 资金流数据
        :return: 加速度因子
        """
        # 一阶差分（速度）
        velocity = flow_data.diff()
        # 二阶差分（加速度）
        acceleration = velocity.diff()
        
        return acceleration
    
    def institutional_holding_change_factor(self, holding_data: pd.DataFrame) -> pd.Series:
        """
        机构持仓变化因子
        :param holding_data: 持仓数据
        :return: 持仓变化因子
        """
        if holding_data is None or holding_data.empty:
            return pd.Series(0)
        
        return holding_data['holding_ratio'].pct_change()
    
    def institutional_research_factor(self, research_data: pd.DataFrame) -> pd.Series:
        """
        机构调研因子
        :param research_data: 调研数据
        :return: 调研因子
        """
        if research_data is None or research_data.empty:
            return pd.Series(0)
        
        # 近 30 天调研次数
        return research_data['research_count'].rolling(30).sum()
    
    def block_trade_factor(self, block_trade_data: pd.DataFrame) -> pd.Series:
        """
        大宗交易因子
        :param block_trade_data: 大宗交易数据
        :return: 大宗交易因子
        """
        if block_trade_data is None or block_trade_data.empty:
            return pd.Series(0)
        
        # 大宗交易净买入
        net_buy = block_trade_data['buy_volume'] - block_trade_data['sell_volume']
        return net_buy
    
    # ==================== 情绪面因子 ====================
    
    def limit_up_count_factor(self, market_data: pd.DataFrame) -> pd.Series:
        """
        涨停数量因子：市场涨停家数
        :param market_data: 市场数据
        :return: 涨停数量因子
        """
        if market_data is None or market_data.empty:
            return pd.Series(0)
        
        return market_data['limit_up_count']
    
    def sentiment_index_factor(self, sentiment_data: pd.DataFrame) -> pd.Series:
        """
        情绪指数因子：基于新闻情感分析
        :param sentiment_data: 情感数据
        :return: 情绪指数
        """
        if sentiment_data is None or sentiment_data.empty:
            return pd.Series(0.5)  # 中性
        
        return sentiment_data['sentiment_score']
    
    def turnover_rate_factor(self, turnover_data: pd.Series) -> pd.Series:
        """
        换手率因子：高换手代表高情绪
        :param turnover_data: 换手率数据
        :return: 换手率因子（归一化）
        """
        # 使用历史百分位归一化
        return turnover_data.rank(pct=True)
    
    def market_width_factor(self, market_data: pd.DataFrame) -> pd.Series:
        """
        市场宽度因子：上涨家数/下跌家数
        :param market_data: 市场数据
        :return: 市场宽度因子
        """
        if market_data is None or market_data.empty:
            return pd.Series(0.5)
        
        up_count = market_data['up_count']
        down_count = market_data['down_count']
        
        return up_count / (up_count + down_count + 1e-8)
    
    def news_sentiment_factor(self, news_data: pd.DataFrame) -> pd.Series:
        """
        新闻情感因子
        :param news_data: 新闻数据
        :return: 新闻情感因子
        """
        if news_data is None or news_data.empty:
            return pd.Series(0.5)
        
        # 近 7 天新闻情感平均
        return news_data['sentiment'].rolling(7).mean()
    
    # ==================== 综合评分 ====================
    
    def calculate_composite_score(self, stock_data: Dict[str, pd.Series], 
                                  market_data: Optional[pd.DataFrame] = None,
                                  weights: Optional[Dict[str, float]] = None) -> pd.Series:
        """
        计算综合评分（23 维）
        :param stock_data: 股票数据字典（包含 price, volume, high, low 等）
        :param market_data: 市场数据
        :param weights: 因子权重（可选）
        :return: 综合评分（0-1）
        """
        if weights is None:
            weights = self.factor_weights
        
        score = pd.Series(0, index=stock_data['close'].index)
        
        try:
            # ===== 技术面因子 =====
            # 1. 5 日动量
            momentum_5d = self.momentum_5d_factor(stock_data['close'])
            score += weights['momentum_5d'] * momentum_5d.rank(pct=True)
            
            # 2. 20 日动量
            momentum_20d = self.momentum_20d_factor(stock_data['close'])
            score += weights['momentum_20d'] * momentum_20d.rank(pct=True)
            
            # 3. 波动率（反向：低波动更好）
            volatility = self.volatility_factor(stock_data['close'])
            score += weights['volatility'] * (1 - volatility.rank(pct=True))
            
            # 4. 成交量比率
            volume_ratio = self.volume_ratio_factor(stock_data['volume'])
            score += weights['volume_ratio'] * volume_ratio.rank(pct=True)
            
            # 5. 均线趋势
            ma_trend = self.ma_trend_factor(stock_data['close'])
            score += weights['ma_trend'] * ma_trend
            
            # 6. RSI（适中最好）
            rsi = self.rsi_factor(stock_data['close'])
            # RSI 在 0.4-0.6 之间得分最高
            rsi_score = 1 - ((rsi - 0.5) * 2).abs()
            score += weights['rsi'] * rsi_score
            
            # 7. MACD
            macd = self.macd_factor(stock_data['close'])
            score += weights['macd'] * macd
            
            # 8. 布林带位置
            bollinger = self.bollinger_factor(stock_data['close'])
            score += weights['bollinger'] * bollinger
            
            # 9. ATR（反向：低 ATR 更好）
            atr = self.atr_factor(stock_data['high'], stock_data['low'], stock_data['close'])
            score += weights['atr'] * (1 - atr.rank(pct=True))
            
            # 10. OBV
            obv = self.obv_factor(stock_data['close'], stock_data['volume'])
            score += weights['obv'] * obv
            
            # ===== 资金面因子 =====
            # 11-18. 各种资金流因子（简化处理，实际需要从对应数据源获取）
            if 'northbound' in stock_data:
                northbound = self.northbound_flow_factor(stock_data['northbound'])
                score += weights['northbound_flow'] * northbound.rank(pct=True)
            
            if 'institutional' in stock_data:
                institutional = self.institutional_flow_factor(stock_data['institutional'])
                score += weights['institutional_flow'] * institutional.rank(pct=True)
            
            if 'top_list' in stock_data:
                main_force = self.main_force_flow_factor(stock_data['top_list'])
                score += weights['main_force_flow'] * main_force.rank(pct=True)
            
            if 'order_data' in stock_data:
                large_order = self.large_order_flow_factor(stock_data['order_data'])
                score += weights['large_order_flow'] * large_order
            
            # ===== 情绪面因子 =====
            # 19-23. 情绪因子
            if market_data is not None:
                limit_up_count = self.limit_up_count_factor(market_data)
                score += weights['limit_up_count'] * limit_up_count.rank(pct=True)
                
                market_width = self.market_width_factor(market_data)
                score += weights['market_width'] * market_width
            
            if 'turnover' in stock_data:
                turnover = self.turnover_rate_factor(stock_data['turnover'])
                score += weights['turnover_rate'] * turnover
            
            if 'sentiment' in stock_data:
                sentiment = self.sentiment_index_factor(stock_data['sentiment'])
                score += weights['sentiment_index'] * sentiment
            
            if 'news' in stock_data:
                news_sentiment = self.news_sentiment_factor(stock_data['news'])
                score += weights['news_sentiment'] * news_sentiment
            
        except Exception as e:
            logger.error(f"❌ 综合评分计算失败：{e}", exc_info=True)
        
        # 确保分数在 0-1 之间
        return score.clip(0, 1)
    
    def get_top_factors(self, stock_data: Dict[str, pd.Series], top_n: int = 10) -> pd.DataFrame:
        """
        获取最重要的因子
        :param stock_data: 股票数据
        :param top_n: 返回前 N 个因子
        :return: 因子重要性 DataFrame
        """
        # 计算各因子当前值
        factor_values = {}
        
        factor_values['momentum_5d'] = self.momentum_5d_factor(stock_data['close']).iloc[-1]
        factor_values['momentum_20d'] = self.momentum_20d_factor(stock_data['close']).iloc[-1]
        factor_values['volatility'] = self.volatility_factor(stock_data['close']).iloc[-1]
        factor_values['volume_ratio'] = self.volume_ratio_factor(stock_data['volume']).iloc[-1]
        factor_values['ma_trend'] = self.ma_trend_factor(stock_data['close']).iloc[-1]
        factor_values['rsi'] = self.rsi_factor(stock_data['close']).iloc[-1]
        factor_values['macd'] = self.macd_factor(stock_data['close']).iloc[-1]
        
        # 创建 DataFrame
        df = pd.DataFrame([
            {'factor': name, 'value': value, 'weight': self.factor_weights.get(name, 0)}
            for name, value in factor_values.items()
        ])
        
        # 计算贡献度
        df['contribution'] = df['value'] * df['weight']
        
        # 按贡献度排序
        df = df.sort_values('contribution', ascending=False).head(top_n)
        
        return df
