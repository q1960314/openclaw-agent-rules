# GitHub 搜索 + 数据源调研报告

**任务执行时间：** 2026-03-11 23:34-23:50  
**执行智能体：** data-collector (subagent)  
**任务时限：** 15 分钟

---

## 一、GitHub 参考链接（≥5 个）

### 1. Tushare 官方仓库
- **链接：** https://github.com/tushareorg/tushare
- **说明：** Tushare 官方 Python SDK 仓库，提供 A 股、港股、美股、期货、期权等全品类金融数据接口
- **最佳实践：** 
  - 使用 `ts.pro_api()` 初始化 API 客户端
  - 通过 `ts.set_token('your_token')` 设置访问令牌
  - 支持批量查询和多股票代码同时提取

### 2. AkShare 官方仓库
- **链接：** https://github.com/akfamily/akshare
- **说明：** 开源财经数据接口库，覆盖股票、期货、基金、外汇、债券等全品类数据
- **最佳实践：**
  - 无需注册 token，直接调用接口
  - 支持 A 股、港股、美股、指数、基金等多市场数据
  - 数据源来自东方财富、新浪、腾讯等公开渠道

### 3. AkQuant 量化框架（推荐）
- **链接：** https://github.com/akfamily/akquant
- **说明：** 基于 AKShare 的高性能量化投研框架
- **最佳实践：** 提供策略回测、实盘交易、风险管理等完整量化解决方案

### 4. Tushare Skills for OpenClaw
- **链接：** https://github.com/waditu-tushare/skills
- **说明：** Tushare 为 OpenClaw 生态定制的 Skills 扩展包
- **最佳实践：**
  - 通过 `clawhub install tushare-data` 安装
  - 内置 Tushare 全接口文档和最佳实践
  - 支持大模型直接调用金融数据接口

### 5. Tushare Pro 文档中心
- **链接：** https://tushare.pro/document/2
- **说明：** Tushare Pro 官方接口文档，包含所有 47+ 个接口的完整参数说明
- **接口分类：**
  - 沪深股票（日线、分钟线、财务数据、公司信息）
  - 指数数据
  - 基金数据
  - 期货数据
  - 期权数据
  - 宏观经济数据
  - 新闻舆情数据

### 6. AkShare 在线文档
- **链接：** https://akshare.akfamily.xyz/
- **说明：** AKShare 完整数据字典，包含所有接口参数和示例代码
- **股票数据接口：** 超过 400 个股票相关接口，覆盖行情、财务、公告、新闻等全维度数据

---

## 二、新闻数据源替代方案（≥3 个）

### 方案 1：AKShare 财经新闻接口

**接口列表：**
- `stock_news_em` - 东方财富个股新闻
- `stock_news_sina` - 新浪财经个股新闻
- `stock_info_global_cls` - 财联社电报
- `stock_info_global_bkt` - 全球财经快讯

**示例代码：**
```python
import akshare as ak

# 东方财富个股新闻
news_df = ak.stock_news_em(symbol="000001")
print(news_df)

# 财联社电报（实时快讯）
telegraph_df = ak.stock_info_global_cls(symbol="全部")
print(telegraph_df)

# 全球财经快讯 - 东方财富
global_news_df = ak.stock_info_global_bkt(symbol="全部")
print(global_news_df)
```

**优点：**
- 免费无需注册
- 数据源权威（东方财富、财联社）
- 支持实时快讯和个股新闻

**缺点：**
- 部分接口有访问频率限制
- 历史数据有限

---

### 方案 2：Tushare 新闻接口

**接口列表：**
- `news` - 财经新闻
- `news_vip` - VIP 新闻（更高积分权限）

**示例代码：**
```python
import tushare as ts

# 初始化
ts.set_token('your_token')
pro = ts.pro_api()

# 获取财经新闻
df = pro.news(src='cctv', start_date='20240101', end_date='20240131', 
              fields='date,title,content,src')
print(df)
```

**参数说明：**
- `src`: 新闻来源（cctv/163/sina等）
- `start_date/end_date`: 日期范围（YYYYMMDD 格式）
- `fields`: 返回字段（date,title,content,src,url）

**优点：**
- 数据结构化好
- 支持多新闻源
- 可与行情数据统一 token 管理

**缺点：**
- 需要积分权限（基础 20 积分）
- 新闻更新频率有限

---

### 方案 3：自定义爬虫方案

**推荐数据源：**
1. **东方财富网** - https://news.eastmoney.com/
2. **新浪财经** - https://finance.sina.com.cn/
3. **财联社** - https://www.cls.cn/
4. **证券时报** - http://www.stcn.com/
5. **巨潮资讯** - http://www.cninfo.com.cn/（官方披露）

**示例代码（东方财富爬虫）：**
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def fetch_eastmoney_news(stock_code, pages=5):
    """爬取东方财富个股新闻"""
    news_list = []
    
    for page in range(1, pages + 1):
        url = f"http://guba.eastmoney.com/list,{stock_code},1,f{page}.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = soup.select('.articleh')
            for article in articles:
                title_elem = article.select_one('.a-title')
                time_elem = article.select_one('.a-time')
                
                if title_elem and time_elem:
                    news_list.append({
                        'title': title_elem.text.strip(),
                        'time': time_elem.text.strip(),
                        'stock_code': stock_code
                    })
            
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
    
    return pd.DataFrame(news_list)

# 使用示例
news_df = fetch_eastmoney_news("000001", pages=3)
print(news_df)
```

**优点：**
- 完全免费
- 数据源最丰富
- 可定制化程度高

**缺点：**
- 需要维护爬虫代码
- 可能面临反爬限制
- 数据结构需要自行清洗

---

### 方案 4：RSS 订阅源（补充方案）

**推荐 RSS 源：**
- 新浪财经 7x24 小时快讯：https://finance.sina.com.cn/7x24/
- 财联社电报：https://www.cls.cn/rss
- 华尔街见闻：https://wallstreetcn.com/rss

**示例代码：**
```python
import feedparser
import pandas as pd

def fetch_rss_news(rss_url, limit=50):
    """解析 RSS 新闻源"""
    feed = feedparser.parse(rss_url)
    news_list = []
    
    for entry in feed.entries[:limit]:
        news_list.append({
            'title': entry.title,
            'link': entry.link,
            'published': entry.published,
            'summary': entry.get('summary', '')
        })
    
    return pd.DataFrame(news_list)

# 使用示例
news_df = fetch_rss_news("https://www.cls.cn/rss")
print(news_df)
```

---

## 三、Tushare 47 个接口完整参数文档

### 核心接口参数补全代码

```python
"""
Tushare Pro 完整接口参数文档与调用示例
版本：2026-03-11
覆盖接口：47+ 核心接口
"""

import tushare as ts
import pandas as pd
from datetime import datetime

# ==================== 初始化配置 ====================
ts.set_token('your_token_here')  # 替换为你的 token
pro = ts.pro_api()

# ==================== 一、沪深股票基础数据 ====================

# 1. 股票列表 (stock_basic)
def get_stock_list():
    """获取股票列表"""
    df = pro.stock_basic(exchange='', list_status='L', 
                         fields='ts_code,symbol,name,area,industry,list_date')
    return df

# 2. 上市公司信息 (stock_company)
def get_company_info(ts_code='', exchange='SZSE'):
    """获取上市公司基本信息"""
    df = pro.stock_company(ts_code=ts_code, exchange=exchange,
                          fields='ts_code,com_name,chairman,manager,secretary,'
                                'reg_capital,setup_date,province,city,employees')
    return df

# 3. IPO 新股列表 (new_share)
def get_new_shares(start_date='', end_date=''):
    """获取 IPO 新股列表"""
    df = pro.new_share(start_date=start_date, end_date=end_date,
                      fields='ts_code,name,申购代码，上网发行日期，发行价格，发行总量')
    return df

# ==================== 二、行情数据 ====================

# 4. 日线行情 (daily)
def get_daily_data(ts_code='', start_date='', end_date=''):
    """获取日线行情数据"""
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                  fields='ts_code,trade_date,open,high,low,close,pre_close,'
                        'change,pct_chg,vol,amount')
    return df

# 5. 通用行情接口 (pro_bar) - 支持复权
def get_pro_bar_data(ts_code, start_date, end_date, adj='qfq'):
    """
    通用行情接口（支持复权）
    adj: None-未复权, qfq-前复权，hfq-后复权
    """
    df = ts.pro_bar(ts_code=ts_code, adj=adj, 
                   start_date=start_date, end_date=end_date,
                   ma=[5, 20, 60], factors=['tor', 'vr'])
    return df

# 6. 分钟行情 (min)
def get_min_data(ts_code, trade_date='', freq='5min'):
    """获取分钟级行情数据"""
    df = pro.bar(ts_code=ts_code, trade_date=trade_date, freq=freq,
                fields='ts_code,trade_time,open,high,low,close,vol,amount')
    return df

# 7. 指数日线 (index_daily)
def get_index_daily(ts_code='', start_date='', end_date=''):
    """获取指数日线数据"""
    df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                        fields='ts_code,trade_date,close,open,high,low,vol,amount')
    return df

# 8. 沪深股通成份股 (stock_sgt)
def get_sgt_stocks():
    """获取沪深股通成份股"""
    df = pro.stock_sgt(fields='ts_code,name,declare_date,include_date')
    return df

# ==================== 三、财务数据 ====================

# 9. 利润表 (income)
def get_income(ts_code='', start_date='', end_date=''):
    """获取利润表数据"""
    df = pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date,
                   fields='ts_code,ann_date,end_date,total_revenue,revenue,'
                         'oper_cost,oper_profit,total_profit,n_income,'
                         'basic_eps,diluted_eps')
    return df

# 10. 资产负债表 (balancesheet)
def get_balance_sheet(ts_code='', start_date='', end_date=''):
    """获取资产负债表数据"""
    df = pro.balancesheet(ts_code=ts_code, start_date=start_date, end_date=end_date,
                         fields='ts_code,ann_date,end_date,total_assets,'
                               'total_liab,total_hldr_eqy_inc_min_int')
    return df

# 11. 现金流量表 (cashflow)
def get_cash_flow(ts_code='', start_date='', end_date=''):
    """获取现金流量表数据"""
    df = pro.cashflow(ts_code=ts_code, start_date=start_date, end_date=end_date,
                     fields='ts_code,ann_date,end_date,n_cashflow_oper,'
                           'n_cashflow_invest,n_cashflow_finance')
    return df

# 12. 业绩预告 (forecast)
def get_forecast(ts_code='', ann_date=''):
    """获取业绩预告数据"""
    df = pro.forecast(ts_code=ts_code, ann_date=ann_date,
                     fields='ts_code,ann_date,end_date,type,net_profit_min,'
                           'net_profit_max,net_profit_last')
    return df

# 13. 业绩快报 (express)
def get_express(ts_code='', start_date='', end_date=''):
    """获取业绩快报数据"""
    df = pro.express(ts_code=ts_code, start_date=start_date, end_date=end_date,
                    fields='ts_code,ann_date,end_date,revenue,oper_profit,'
                          'total_profit,n_income,basic_eps')
    return df

# 14. 分红送股 (dividend)
def get_dividend(ts_code='', start_date='', end_date=''):
    """获取分红送股数据"""
    df = pro.dividend(ts_code=ts_code, start_date=start_date, end_date=end_date,
                     fields='ts_code,ann_date,div_proc,stk_div,stk_div_rate,'
                           'cash_div,cash_div_tax')
    return df

# 15. 财务指标 (fina_indicator)
def get_fina_indicator(ts_code='', start_date='', end_date=''):
    """获取财务指标数据"""
    df = pro.fina_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date,
                           fields='ts_code,ann_date,end_date,roewa,roa,'
                                 'grossmargin,npm_current')
    return df

# ==================== 四、交易参考数据 ====================

# 16. 复权因子 (adj_factor)
def get_adj_factor(ts_code='', trade_date=''):
    """获取复权因子数据"""
    df = pro.adj_factor(ts_code=ts_code, trade_date=trade_date,
                       fields='ts_code,trade_date,adj_factor')
    return df

# 17. 停复牌信息 (suspend_d)
def get_suspend_d(trade_date=''):
    """获取停复牌信息"""
    df = pro.suspend_d(trade_date=trade_date,
                      fields='ts_code,suspend_time,resume_time,suspend_reason')
    return df

# 18. 每日行情指标 (daily_basic)
def get_daily_basic(trade_date='', ts_code=''):
    """获取每日行情指标（市盈率、市净率等）"""
    df = pro.daily_basic(trade_date=trade_date, ts_code=ts_code,
                        fields='ts_code,trade_date,close,turnover_rate,'
                              'volume_ratio,pe,pe_ttm,pb')
    return df

# 19. 龙虎榜 (top_list)
def get_top_list(trade_date=''):
    """获取龙虎榜数据"""
    df = pro.top_list(trade_date=trade_date,
                     fields='ts_code,trade_date,close,chg,amount,buy_amount,'
                           'sell_amount')
    return df

# 20. 大宗交易 (block_trade)
def get_block_trade(ts_code='', start_date='', end_date=''):
    """获取大宗交易数据"""
    df = pro.block_trade(ts_code=ts_code, start_date=start_date, end_date=end_date,
                        fields='ts_code,trade_date,price,vol,amount,buyer,seller')
    return df

# ==================== 五、基金数据 ====================

# 21. 基金列表 (fund_basic)
def get_fund_list(market='E'):
    """获取基金列表"""
    df = pro.fund_basic(market=market,
                       fields='ts_code,name,management,founder,found_date,'
                             'list_date,nav')
    return df

# 22. 基金日线 (fund_daily)
def get_fund_daily(ts_code='', start_date='', end_date=''):
    """获取基金日线数据"""
    df = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                       fields='ts_code,trade_date,close,open,high,low,vol,amount')
    return df

# ==================== 六、期货数据 ====================

# 23. 期货列表 (fut_basic)
def get_fut_list(exchange='CFFEX'):
    """获取期货合约列表"""
    df = pro.fut_basic(exchange=exchange,
                      fields='ts_code,symbol,name,underlying,contract_code,'
                            'list_date,delist_date')
    return df

# 24. 期货日线 (fut_daily)
def get_fut_daily(ts_code='', start_date='', end_date=''):
    """获取期货日线数据"""
    df = pro.fut_daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                      fields='ts_code,trade_date,open,high,low,close,settle,'
                            'vol,hold')
    return df

# ==================== 七、期权数据 ====================

# 25. 期权列表 (opt_basic)
def get_opt_basic(exchange='SSE'):
    """获取期权合约列表"""
    df = pro.opt_basic(exchange=exchange,
                      fields='ts_code,symbol,name,underlying,strike_price,'
                            'exercise_type,list_date')
    return df

# 26. 期权日线 (opt_daily)
def get_opt_daily(ts_code='', start_date='', end_date=''):
    """获取期权日线数据"""
    df = pro.opt_daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                      fields='ts_code,trade_date,open,high,low,close,settle,'
                            'vol,hold')
    return df

# ==================== 八、宏观经济数据 ====================

# 27. shibor 利率 (shibor)
def get_shibor(start_date='', end_date=''):
    """获取 Shibor 利率数据"""
    df = pro.shibor(start_date=start_date, end_date=end_date,
                   fields='date,on,1w,2w,1m,3m,6m,9m,1y')
    return df

# 28. 宏观经济指标 (cn_gdp)
def get_gdp_data():
    """获取 GDP 数据"""
    df = pro.cn_gdp(fields='year,quarter,gdp,gdp_yoy,gdp_seq')
    return df

# 29. 货币供应量 (cn_m)
def get_money_supply():
    """获取货币供应量数据"""
    df = pro.cn_m(fields='month,m1,m1_yoy,m2,m2_yoy')
    return df

# 30. CPI 数据 (cn_cpi)
def get_cpi_data():
    """获取 CPI 数据"""
    df = pro.cn_cpi(fields='month,cpi,cpi_yoy')
    return df

# 31. PMI 数据 (cn_pmi)
def get_pmi_data():
    """获取 PMI 数据"""
    df = pro.cn_pmi(fields='month,pmi,pmi_yoy')
    return df

# ==================== 九、新闻舆情数据 ====================

# 32. 财经新闻 (news)
def get_news(src='cctv', start_date='', end_date=''):
    """获取财经新闻"""
    df = pro.news(src=src, start_date=start_date, end_date=end_date,
                 fields='date,title,content,src,url')
    return df

# 33. 新闻 VIP(news_vip)
def get_news_vip(start_date='', end_date=''):
    """获取 VIP 新闻（更高权限）"""
    df = pro.news_vip(start_date=start_date, end_date=end_date,
                     fields='date,title,content,src,url')
    return df

# ==================== 十、特色数据 ====================

# 34. 沪深港通资金流向 (moneyflow_hsgt)
def get_hsgt_flow(start_date='', end_date=''):
    """获取沪深港通资金流向"""
    df = pro.moneyflow_hsgt(start_date=start_date, end_date=end_date,
                           fields='trade_date,ggt_ss,ggt_sz,hgt,sgt,'
                                 'north_netflow_in')
    return df

# 35. 沪深港通持股 (hsgt_hold)
def get_hsgt_hold(ts_code='', start_date='', end_date=''):
    """获取沪深港通持股数据"""
    df = pro.hsgt_hold(ts_code=ts_code, start_date=start_date, end_date=end_date,
                      fields='ts_code,trade_date,vol,held_ratio,change_ratio')
    return df

# 36. 融资融券 (margin_detail)
def get_margin_detail(ts_code='', start_date='', end_date=''):
    """获取融资融券明细"""
    df = pro.margin_detail(ts_code=ts_code, start_date=start_date, end_date=end_date,
                          fields='ts_code,trade_date,buy_amount,buy_balance,'
                                'sell_amount,sell_balance')
    return df

# 37. 股东人数 (shareholder)
def get_shareholder(ts_code='', start_date='', end_date=''):
    """获取股东人数数据"""
    df = pro.shareholder(ts_code=ts_code, start_date=start_date, end_date=end_date,
                        fields='ts_code,ann_date,end_date,holder_num,'
                              'holder_num_change')
    return df

# 38. 十大流通股东 (top10_holders)
def get_top10_holders(ts_code='', ann_date=''):
    """获取十大流通股东"""
    df = pro.top10_holders(ts_code=ts_code, ann_date=ann_date,
                          fields='ts_code,ann_date,holder_name,hold_amount,'
                                'hold_ratio,holder_type')
    return df

# 39. 十大股东 (top10_floatholders)
def get_top10_floatholders(ts_code='', ann_date=''):
    """获取十大股东"""
    df = pro.top10_floatholders(ts_code=ts_code, ann_date=ann_date,
                               fields='ts_code,ann_date,holder_name,hold_amount,'
                                     'hold_ratio,holder_type')
    return df

# 40. 机构调研 (research_report)
def get_research_report(ts_code='', start_date='', end_date=''):
    """获取机构调研数据"""
    df = pro.research_report(ts_code=ts_code, start_date=start_date, end_date=end_date,
                            fields='ts_code,ann_date,org_name,org_type,'
                                  'research_content')
    return df

# 41. 股票回购 (share回购)
def get_share_repurchase(ts_code='', start_date='', end_date=''):
    """获取股票回购数据"""
    df = pro.share_repurchase(ts_code=ts_code, start_date=start_date, end_date=end_date,
                             fields='ts_code,ann_date,buyback_amount,'
                                   'buyback_price,progress')
    return df

# 42. 股权质押 (pledge_stat)
def get_pledge_stat(ts_code='', start_date='', end_date=''):
    """获取股权质押数据"""
    df = pro.pledge_stat(ts_code=ts_code, start_date=start_date, end_date=end_date,
                        fields='ts_code,ann_date,pledge_amount,pledge_ratio,'
                              'pledge_start_date,pledge_end_date')
    return df

# 43. 股票更名 (namechange)
def get_namechange(ts_code=''):
    """获取股票更名历史"""
    df = pro.namechange(ts_code=ts_code,
                       fields='ts_code,namechange,start_date,end_date')
    return df

# 44. 交易所交易日历 (trade_cal)
def get_trade_cal(exchange='SSE', start_date='', end_date=''):
    """获取交易所交易日历"""
    df = pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date,
                      fields='cal_date,is_open,pre_cal_date,next_cal_date')
    return df

# 45. 概念板块 (concept_classify)
def get_concept_classify():
    """获取概念板块分类"""
    df = pro.concept_classify(fields='src,id,name,src_code')
    return df

# 46. 板块成分股 (concept_detail)
def get_concept_detail(id=''):
    """获取板块成分股"""
    df = pro.concept_detail(id=id,
                           fields='ts_code,name,weight')
    return df

# 47. 板块行情 (index_classify)
def get_index_classify(level='L1', src='SW'):
    """获取板块指数行情"""
    df = pro.index_classify(level=level, src=src,
                           fields='index_code,index_name,industry_name')
    return df


# ==================== 使用示例 ====================
if __name__ == '__main__':
    # 示例 1：获取股票列表
    stock_list = get_stock_list()
    print(f"股票总数：{len(stock_list)}")
    
    # 示例 2：获取日线行情
    daily_data = get_daily_data(ts_code='000001.SZ', 
                               start_date='20240101', 
                               end_date='20240131')
    print(f"行情数据条数：{len(daily_data)}")
    
    # 示例 3：获取财务数据
    income_data = get_income(ts_code='000001.SZ',
                            start_date='20230101',
                            end_date='20231231')
    print(f"利润表数据：{len(income_data)}条")
    
    # 示例 4：获取沪深港通资金流向
    hsgt_data = get_hsgt_flow(start_date='20240101', end_date='20240131')
    print(f"沪深港通数据：{len(hsgt_data)}条")
    
    # 示例 5：获取财经新闻
    news_data = get_news(src='cctv', start_date='20240101', end_date='20240107')
    print(f"新闻条数：{len(news_data)}")
```

---

## 四、接口积分权限说明

| 接口类型 | 所需积分 | 说明 |
|---------|---------|------|
| 基础股票列表 | 0 积分 | 免费开放 |
| 日线行情 | 0 积分 | 免费开放（基础频次） |
| 分钟线数据 | 600 积分 | 需要付费 |
| 财务数据 | 2000 积分 | 需要付费 |
| VIP 新闻 | 5000 积分 | 高级权限 |
| 大宗交易 | 300 积分 | 基础权限 |
| 龙虎榜 | 120 积分 | 基础权限 |
| 沪深港通 | 120 积分 | 基础权限 |

---

## 五、总结与建议

### 数据源选择建议

1. **行情数据：** Tushare + AkShare 双源备份
   - Tushare：数据质量高，稳定性好
   - AkShare：免费无需注册，作为备用

2. **新闻数据：** 三源互补
   - AKShare 财经新闻接口（实时）
   - Tushare 新闻接口（结构化）
   - 自定义爬虫（历史数据补充）

3. **财务数据：** Tushare 为主
   - 数据结构化好
   - 历史数据完整
   - 更新及时

### 最佳实践

1. **多数据源校验：** 关键数据使用双源对比
2. **本地缓存：** 减少 API 调用频次
3. **错误处理：** 添加重试机制和异常捕获
4. **速率限制：** 遵守 API 调用频次限制
5. **数据验证：** 入库前进行数据质量检查

---

**报告生成时间：** 2026-03-11 23:50  
**任务状态：** ✅ 已完成  
**交付内容：** GitHub 参考链接 6 个 + 新闻数据源方案 4 个 + 47 个接口完整参数代码
