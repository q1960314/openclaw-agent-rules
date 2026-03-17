#!/usr/bin/env python3
"""
协作流程优化脚本
基于日志分析结果，优化 Agent 之间的协作流程
"""

import json
import os
from datetime import datetime

REPORT_DIR = "/home/admin/.openclaw/agents/master/reports"

class CollaborationOptimizer:
    def __init__(self):
        self.optimization_history = []
    
    def analyze_collaboration(self, report_file):
        """
        分析协作流程
        """
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        optimizations = []
        
        # 分析 Agent 之间的依赖关系
        bottlenecks = self.identify_bottlenecks(report)
        if bottlenecks:
            optimizations.extend(bottlenecks)
        
        # 分析响应时间
        slow_agents = self.identify_slow_agents(report)
        if slow_agents:
            optimizations.extend(slow_agents)
        
        # 分析失败传递
        failure_chain = self.analyze_failure_chain(report)
        if failure_chain:
            optimizations.extend(failure_chain)
        
        # 生成优化方案
        optimization_plan = {
            'date': report['date'],
            'analyzed_at': datetime.now().isoformat(),
            'optimizations': optimizations,
            'expected_improvement': self.calculate_expected_improvement(optimizations)
        }
        
        return optimization_plan
    
    def identify_bottlenecks(self, report):
        """
        识别瓶颈 Agent
        """
        bottlenecks = []
        
        for agent, metrics in report['agents'].items():
            # 任务数多且响应时间长 = 瓶颈
            if metrics['task_count'] > 10 and metrics['avg_response_time'] > 30:
                bottlenecks.append({
                    'type': 'bottleneck',
                    'agent': agent,
                    'issue': f"任务数多 ({metrics['task_count']}) 且响应时间长 ({metrics['avg_response_time']:.2f}秒)",
                    'suggestions': [
                        '考虑任务分流',
                        '优化 Prompt 减少响应时间',
                        '升级到更快的模型',
                        '增加并行处理'
                    ],
                    'priority': 'high'
                })
        
        return bottlenecks
    
    def identify_slow_agents(self, report):
        """
        识别慢 Agent
        """
        slow_agents = []
        
        for agent, metrics in report['agents'].items():
            if metrics['avg_response_time'] > 30:
                slow_agents.append({
                    'type': 'slow_response',
                    'agent': agent,
                    'issue': f"平均响应时间过长 ({metrics['avg_response_time']:.2f}秒)",
                    'suggestions': [
                        '简化 Prompt',
                        '减少不必要的验证',
                        '使用流式响应',
                        '缓存常用结果'
                    ],
                    'priority': 'medium'
                })
        
        return slow_agents
    
    def analyze_failure_chain(self, report):
        """
        分析失败传递链
        """
        failure_chains = []
        
        # 分析失败级别分布
        total_p0 = sum(m.get('failure_levels', {}).get('P0', 0) for m in report['agents'].values())
        total_p1 = sum(m.get('failure_levels', {}).get('P1', 0) for m in report['agents'].values())
        total_p2 = sum(m.get('failure_levels', {}).get('P2', 0) for m in report['agents'].values())
        
        if total_p0 > 0:
            failure_chains.append({
                'type': 'p0_failure',
                'issue': f"发生 {total_p0} 次 P0 失败（致命错误）",
                'suggestions': [
                    '立即根因分析',
                    '加强预防措施',
                    '建立冗余机制'
                ],
                'priority': 'critical'
            })
        
        if total_p1 > 5:
            failure_chains.append({
                'type': 'high_p1_failure',
                'issue': f"P1 失败过多 ({total_p1}次)",
                'suggestions': [
                    '分析常见失败原因',
                    '加强 Agent 培训',
                    '优化验证标准'
                ],
                'priority': 'high'
            })
        
        return failure_chains
    
    def calculate_expected_improvement(self, optimizations):
        """
        计算预期改进效果
        """
        improvement = {
            'response_time_reduction': 0,
            'failure_rate_reduction': 0,
            'token_usage_reduction': 0
        }
        
        for opt in optimizations:
            if opt['type'] == 'slow_response':
                improvement['response_time_reduction'] += 20  # 预期减少 20%
            elif opt['type'] == 'bottleneck':
                improvement['response_time_reduction'] += 30
                improvement['failure_rate_reduction'] += 10
            elif opt['type'] in ['p0_failure', 'high_p1_failure']:
                improvement['failure_rate_reduction'] += 20
        
        return improvement
    
    def save_optimization_plan(self, plan):
        """
        保存优化方案
        """
        os.makedirs(REPORT_DIR, exist_ok=True)
        plan_file = f"{REPORT_DIR}/collaboration_optimization_{plan['date']}.json"
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 优化方案已保存：{plan_file}")
        
        # 生成 Markdown 版本
        md_file = f"{REPORT_DIR}/collaboration_optimization_{plan['date']}.md"
        self.save_markdown_plan(plan, md_file)
        print(f"✅ Markdown 方案已保存：{md_file}")
    
    def save_markdown_plan(self, plan, md_file):
        """
        保存 Markdown 格式优化方案
        """
        md_content = f"""# 协作流程优化方案

**分析日期：** {plan['date']}  
**生成时间：** {plan['analyzed_at']}

---

## 优化建议

"""
        for i, opt in enumerate(plan['optimizations'], 1):
            md_content += f"""### {i}. {opt['type']} (优先级：{opt['priority']})
- **Agent:** {opt.get('agent', 'N/A')}
- **问题:** {opt['issue']}
- **建议:**
"""
            for j, suggestion in enumerate(opt['suggestions'], 1):
                md_content += f"  {j}. {suggestion}\n"
            md_content += "\n"
        
        md_content += f"""
---

## 预期改进效果

| 指标 | 预期改进 |
|------|---------|
| 响应时间减少 | {plan['expected_improvement']['response_time_reduction']}% |
| 失败率减少 | {plan['expected_improvement']['failure_rate_reduction']}% |
| Token 消耗减少 | {plan['expected_improvement']['token_usage_reduction']}% |

---

## 实施计划

1. **立即实施**（高优先级）
   - 实施瓶颈优化
   - 处理 P0 失败

2. **本周实施**（中优先级）
   - 优化慢 Agent
   - 减少 P1 失败

3. **持续优化**
   - 每日监控效果
   - 根据数据调整
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

if __name__ == '__main__':
    # 查找最新的日志分析报告
    import glob
    report_files = glob.glob(f"{REPORT_DIR}/daily_analysis_*.json")
    
    if report_files:
        latest_report = max(report_files)
        print(f"📊 分析最新报告：{latest_report}")
        
        optimizer = CollaborationOptimizer()
        plan = optimizer.analyze_collaboration(latest_report)
        optimizer.save_optimization_plan(plan)
        
        print(f"\n🎯 优化方案已生成！")
        print(f"✅ 优化建议：{len(plan['optimizations'])}条")
        print(f"✅ 预期响应时间减少：{plan['expected_improvement']['response_time_reduction']}%")
        print(f"✅ 预期失败率减少：{plan['expected_improvement']['failure_rate_reduction']}%")
    else:
        print("❌ 未找到日志分析报告，请先运行 daily_log_analyzer.py")
