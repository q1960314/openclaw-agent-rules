#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓分析模块

功能：
1. 昨日选股今日表现分析
2. 持仓决策树判断
3. 选股理由记录管理
4. 板块轮动跟踪
5. 每日复盘报告生成

版本：v1.0
创建时间：2026-03-12
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class StockPickRecord:
    """选股记录"""
    stock_code: str
    stock_name: str
    pick_date: str
    strategy: str  # 打板/潜伏/轮动
    core_reason: str
    sector: str
    catalyst: str
    expected_time: str
    score: float
    position: float
    buy_price: float
    stop_profit: float
    stop_loss: float


@dataclass
class StockPerformance:
    """股票表现"""
    stock_code: str
    stock_name: str
    pick_score: float
    today_change: float
    current_status: str  # 涨停/大涨/震荡/小跌/大跌
    trigger_condition: str  # 未破坏/已破坏
    expectation_status: str  # 未兑现/部分兑现/完全兑现/落空
    decision: str  # 继续持有/止盈/止损


@dataclass
class PositionDecision:
    """持仓决策"""
    stock_code: str
    stock_name: str
    decision_type: str  # 继续持有/止盈/止损
    decision_price: float
    decision_reason: str
    next_plan: str


@dataclass
class SectorData:
    """板块数据"""
    sector_name: str
    today_change: float
    five_day_change: float
    fund_flow: float
    limit_up_count: int
    strength: float
    status: str  # 强势/震荡/退潮


class PositionAnalyzer:
    """持仓分析器"""
    
    def __init__(self, trace_dir: str = None):
        if trace_dir is None:
            self.trace_dir = "/home/admin/.openclaw/agents/master/traces"
        else:
            self.trace_dir = trace_dir
        
        os.makedirs(self.trace_dir, exist_ok=True)
    
    def analyze_yesterday_picks(self, yesterday_picks: List[StockPickRecord], 
                                 today_quotes: Dict[str, float]) -> List[StockPerformance]:
        """
        分析昨日选股今日表现
        
        Args:
            yesterday_picks: 昨日选股清单
            today_quotes: 今日行情数据 {股票代码：涨跌幅}
        
        Returns:
            表现分析结果列表
        """
        performances = []
        
        for pick in yesterday_picks:
            today_change = today_quotes.get(pick.stock_code, 0.0)
            
            # 判断当前状态
            if today_change >= 9.5:
                current_status = "涨停"
            elif today_change >= 5:
                current_status = "大涨"
            elif today_change >= -2:
                current_status = "震荡"
            elif today_change >= -5:
                current_status = "小跌"
            else:
                current_status = "大跌"
            
            # 判断触发条件（简化逻辑，实际需要根据策略判断）
            trigger_condition = "未破坏" if today_change > -5 else "已破坏"
            
            # 判断预期状态
            if today_change >= 9.5:
                expectation_status = "完全兑现"
            elif today_change >= 5:
                expectation_status = "部分兑现"
            elif today_change >= -2:
                expectation_status = "未兑现"
            else:
                expectation_status = "落空"
            
            # 生成决策
            decision = self._generate_decision(current_status, trigger_condition, expectation_status)
            
            performance = StockPerformance(
                stock_code=pick.stock_code,
                stock_name=pick.stock_name,
                pick_score=pick.score,
                today_change=today_change,
                current_status=current_status,
                trigger_condition=trigger_condition,
                expectation_status=expectation_status,
                decision=decision
            )
            performances.append(performance)
        
        return performances
    
    def _generate_decision(self, current_status: str, trigger_condition: str, 
                           expectation_status: str) -> str:
        """
        根据决策树生成持仓决策
        
        决策逻辑：
        1. 涨停 + 触发条件未破坏 + 预期未完全兑现 → 继续持有
        2. 涨停 + 预期完全兑现 → 止盈
        3. 大涨 + 未触及止盈线 → 继续持有
        4. 大涨 + 触及止盈线 → 止盈
        5. 震荡 + 触发条件未破坏 → 继续持有
        6. 震荡 + 触发条件已破坏 → 止损
        7. 小跌 + 未触及止损线 → 继续观察
        8. 小跌 + 触及止损线 → 止损
        9. 大跌/跌停 → 止损
        """
        if current_status == "涨停":
            if expectation_status == "完全兑现":
                return "止盈离场"
            else:
                return "继续持有"
        
        elif current_status == "大涨":
            # 简化：大涨默认部分兑现，继续持有
            return "继续持有"
        
        elif current_status == "震荡":
            if trigger_condition == "已破坏":
                return "止损离场"
            else:
                return "继续持有"
        
        elif current_status == "小跌":
            if trigger_condition == "已破坏" or expectation_status == "落空":
                return "止损离场"
            else:
                return "继续观察"
        
        else:  # 大跌
            return "止损离场"
    
    def generate_position_decisions(self, holdings: List[Dict], 
                                     today_quotes: Dict[str, float]) -> List[PositionDecision]:
        """
        生成持仓决策建议
        
        Args:
            holdings: 持仓列表 [{股票代码，股票名称，持仓成本，选股理由，...}]
            today_quotes: 今日行情数据
        
        Returns:
            决策建议列表
        """
        decisions = []
        
        for holding in holdings:
            stock_code = holding['stock_code']
            today_change = today_quotes.get(stock_code, 0.0)
            current_price = holding['cost_price'] * (1 + today_change / 100)
            profit_rate = (current_price - holding['cost_price']) / holding['cost_price']
            
            # 判断决策类型
            decision_type = self._determine_decision_type(holding, profit_rate, today_change)
            
            # 生成决策理由
            decision_reason = self._generate_decision_reason(holding, profit_rate, today_change, decision_type)
            
            # 生成后续计划
            next_plan = self._generate_next_plan(decision_type, holding)
            
            decision = PositionDecision(
                stock_code=stock_code,
                stock_name=holding['stock_name'],
                decision_type=decision_type,
                decision_price=current_price,
                decision_reason=decision_reason,
                next_plan=next_plan
            )
            decisions.append(decision)
        
        return decisions
    
    def _determine_decision_type(self, holding: Dict, profit_rate: float, 
                                  today_change: float) -> str:
        """判断决策类型"""
        strategy = holding.get('strategy', '')
        
        # 止盈条件
        if strategy == '打板策略' and profit_rate >= 0.12:
            return '止盈'
        elif strategy == '潜伏策略' and profit_rate >= 0.15:
            return '止盈'
        elif strategy == '轮动策略' and profit_rate >= 0.10:
            return '止盈'
        
        # 止损条件
        if strategy == '打板策略' and profit_rate <= -0.06:
            return '止损'
        elif strategy == '潜伏策略' and profit_rate <= -0.03:
            return '止损'
        elif strategy == '轮动策略' and profit_rate <= -0.05:
            return '止损'
        
        # 时间止损
        hold_days = holding.get('hold_days', 0)
        if strategy == '打板策略' and hold_days >= 2:
            return '止损'
        elif strategy == '潜伏策略' and hold_days >= 8:
            return '止损'
        elif strategy == '轮动策略' and hold_days >= 3:
            return '止损'
        
        # 默认继续持有
        return '继续持有'
    
    def _generate_decision_reason(self, holding: Dict, profit_rate: float, 
                                   today_change: float, decision_type: str) -> str:
        """生成决策理由"""
        if decision_type == '止盈':
            return f"目标止盈位达成（盈利{profit_rate*100:.1f}%）"
        elif decision_type == '止损':
            if profit_rate <= -0.05:
                return f"价格止损（亏损{abs(profit_rate)*100:.1f}%）"
            else:
                return "时间止损（持股超时）"
        else:
            return "触发条件未破坏，预期未完全兑现"
    
    def _generate_next_plan(self, decision_type: str, holding: Dict) -> str:
        """生成后续计划"""
        if decision_type == '止盈':
            return "已止盈离场，关注回调机会"
        elif decision_type == '止损':
            return "已止损离场，记录避坑指南"
        else:
            return "继续持有，观察能否涨停"
    
    def track_sector_rotation(self, sectors: List[SectorData]) -> Dict:
        """
        跟踪板块轮动
        
        Args:
            sectors: 板块数据列表
        
        Returns:
            轮动分析结果
        """
        # 排序
        sectors_by_strength = sorted(sectors, key=lambda x: x.strength, reverse=True)
        
        # 识别新主线
        new_main_lines = [s for s in sectors_by_strength if s.strength >= 80 and s.status == '强势']
        
        # 识别退潮板块
        declining_sectors = [s for s in sectors_by_strength if s.status == '退潮']
        
        # 识别持续强势
        continuous_strong = [s for s in sectors_by_strength if s.status == '强势']
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'sectors': [asdict(s) for s in sectors],
            'new_main_lines': [asdict(s) for s in new_main_lines],
            'declining_sectors': [asdict(s) for s in declining_sectors],
            'continuous_strong': [asdict(s) for s in continuous_strong],
            'fund_flow_in': sorted(sectors, key=lambda x: x.fund_flow, reverse=True)[:3],
            'fund_flow_out': sorted(sectors, key=lambda x: x.fund_flow)[:3]
        }
    
    def generate_daily_review(self, performances: List[StockPerformance],
                               decisions: List[PositionDecision],
                               sector_rotation: Dict) -> Dict:
        """
        生成每日复盘报告
        
        Args:
            performances: 昨日选股今日表现
            decisions: 持仓决策
            sector_rotation: 板块轮动分析
        
        Returns:
            复盘报告
        """
        # 统计表现
        total_picks = len(performances)
        limit_up = sum(1 for p in performances if p.current_status == '涨停')
        big_rise = sum(1 for p in performances if p.current_status == '大涨')
        oscillation = sum(1 for p in performances if p.current_status == '震荡')
        decline = sum(1 for p in performances if p.current_status in ['小跌', '大跌'])
        
        win_rate = sum(1 for p in performances if p.today_change > 0) / total_picks if total_picks > 0 else 0
        avg_return = sum(p.today_change for p in performances) / total_picks if total_picks > 0 else 0
        
        review = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'stock_pick_performance': {
                'total_picks': total_picks,
                'limit_up': limit_up,
                'big_rise': big_rise,
                'oscillation': oscillation,
                'decline': decline,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'details': [asdict(p) for p in performances]
            },
            'position_decisions': {
                'hold': [asdict(d) for d in decisions if d.decision_type == '继续持有'],
                'stop_profit': [asdict(d) for d in decisions if d.decision_type == '止盈'],
                'stop_loss': [asdict(d) for d in decisions if d.decision_type == '止损']
            },
            'sector_rotation': sector_rotation,
            'summary': {
                'good_points': [],
                'improvements': [],
                'lessons': []
            }
        }
        
        return review
    
    def save_review_to_file(self, review: Dict, filename: str = None):
        """保存复盘报告到文件"""
        if filename is None:
            filename = f"daily-review-{datetime.now().strftime('%Y%m%d')}.md"
        
        filepath = os.path.join(self.trace_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 每日复盘报告\n\n")
            f.write(f"**复盘日期：** {review['date']}\n\n")
            
            # 昨日选股今日表现
            f.write(f"## 一、昨日选股今日表现\n\n")
            perf = review['stock_pick_performance']
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 选股数量 | {perf['total_picks']} 只 |\n")
            f.write(f"| 今日涨停 | {perf['limit_up']} 只 |\n")
            f.write(f"| 今日大涨 | {perf['big_rise']} 只 |\n")
            f.write(f"| 今日震荡 | {perf['oscillation']} 只 |\n")
            f.write(f"| 今日下跌 | {perf['decline']} 只 |\n")
            f.write(f"| 胜率 | {perf['win_rate']*100:.1f}% |\n")
            f.write(f"| 平均收益 | {perf['avg_return']:.2f}% |\n\n")
            
            # 持仓决策
            f.write(f"## 二、持仓决策\n\n")
            f.write(f"### 继续持有：{len(review['position_decisions']['hold'])} 只\n")
            f.write(f"### 止盈离场：{len(review['position_decisions']['stop_profit'])} 只\n")
            f.write(f"### 止损离场：{len(review['position_decisions']['stop_loss'])} 只\n\n")
            
            # 板块轮动
            f.write(f"## 三、板块轮动\n\n")
            f.write(f"### 新主线：{len(review['sector_rotation']['new_main_lines'])} 个\n")
            f.write(f"### 退潮板块：{len(review['sector_rotation']['declining_sectors'])} 个\n\n")
            
            # 合规提示
            f.write(f"## 四、合规提示\n\n")
            f.write(f"本复盘报告仅为量化研究回测使用，不构成任何投资建议。\n\n")
            f.write(f"**投资有风险，入市需谨慎。**\n")
        
        return filepath


def main():
    """测试函数"""
    analyzer = PositionAnalyzer()
    
    # 模拟数据
    picks = [
        StockPickRecord(
            stock_code="000001",
            stock_name="平安银行",
            pick_date="2026-03-11",
            strategy="打板策略",
            core_reason="金融轮动",
            sector="银行",
            catalyst="财报预增",
            expected_time="3 天",
            score=85.0,
            position=0.2,
            buy_price=10.0,
            stop_profit=11.2,
            stop_loss=9.4
        )
    ]
    
    quotes = {"000001": 5.2}
    
    # 分析表现
    performances = analyzer.analyze_yesterday_picks(picks, quotes)
    print(f"表现分析：{performances}")
    
    # 生成决策
    holdings = [{
        'stock_code': '000001',
        'stock_name': '平安银行',
        'cost_price': 10.0,
        'strategy': '打板策略',
        'hold_days': 1
    }]
    decisions = analyzer.generate_position_decisions(holdings, quotes)
    print(f"持仓决策：{decisions}")
    
    # 板块轮动
    sectors = [
        SectorData("银行", 1.2, 5.5, 30.0, 2, 75.0, "震荡"),
        SectorData("科技", 3.2, 12.0, 80.0, 8, 90.0, "强势"),
        SectorData("地产", -1.2, 3.0, -40.0, 0, 30.0, "退潮")
    ]
    rotation = analyzer.track_sector_rotation(sectors)
    print(f"板块轮动：{rotation}")
    
    # 生成复盘
    review = analyzer.generate_daily_review(performances, decisions, rotation)
    filepath = analyzer.save_review_to_file(review)
    print(f"复盘报告已保存：{filepath}")


if __name__ == "__main__":
    main()
