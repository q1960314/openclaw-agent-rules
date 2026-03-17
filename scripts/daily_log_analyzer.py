#!/usr/bin/env python3
"""
每日日志分析脚本
每天固定时间（20:00）分析所有 Agent 日志，生成分析报告
"""

import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

LOG_DIR = "/home/admin/.openclaw/agents/master/logs"
REPORT_DIR = "/home/admin/.openclaw/agents/master/reports"

class DailyLogAnalyzer:
    def __init__(self):
        self.agents = [
            'master', 'strategy-expert', 'coder', 'test-expert',
            'data-collector', 'backtest-engine', 'knowledge-steward',
            'parameter-evolver', 'doc-manager', 'factor-miner',
            'finance-learner', 'sentiment-analyst', 'ops-monitor'
        ]
        self.metrics = defaultdict(lambda: {
            'task_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'response_times': [],
            'token_usage': 0,
            'validation_levels': defaultdict(int),
            'failure_levels': defaultdict(int)
        })
    
    def analyze_logs(self, date=None):
        """
        分析指定日期的日志
        """
        if date is None:
            date = datetime.now().date()
        
        print(f"📊 分析日期：{date}")
        
        for agent in self.agents:
            log_file = f"{LOG_DIR}/{agent}_execution.jsonl"
            if os.path.exists(log_file):
                self.analyze_agent_log(agent, log_file, date)
        
        return self.generate_report(date)
    
    def analyze_agent_log(self, agent, log_file, date):
        """
        分析单个 Agent 的日志
        """
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_date = datetime.fromisoformat(entry['timestamp']).date()
                    
                    if entry_date == date:
                        self.metrics[agent]['task_count'] += 1
                        
                        if entry['action'] == 'complete':
                            self.metrics[agent]['success_count'] += 1
                        elif entry['action'] == 'failed':
                            self.metrics[agent]['failure_count'] += 1
                        
                        if 'response_time' in entry:
                            self.metrics[agent]['response_times'].append(entry['response_time'])
                        
                        if 'token_usage' in entry:
                            self.metrics[agent]['token_usage'] += entry['token_usage']
                        
                        if 'validation_level' in entry:
                            self.metrics[agent]['validation_levels'][entry['validation_level']] += 1
                        
                        if 'failure_level' in entry:
                            self.metrics[agent]['failure_levels'][entry['failure_level']] += 1
                except:
                    continue
    
    def generate_report(self, date):
        """
        生成分析报告
        """
        report = {
            'date': str(date),
            'generated_at': datetime.now().isoformat(),
            'agents': {},
            'summary': {
                'total_tasks': 0,
                'total_success': 0,
                'total_failure': 0,
                'success_rate': 0,
                'avg_response_time': 0,
                'total_token_usage': 0
            },
            'collaboration_analysis': {
                'bottlenecks': [],
                'slow_agents': [],
                'high_failure_agents': []
            },
            'recommendations': []
        }
        
        total_tasks = 0
        total_success = 0
        total_failure = 0
        all_response_times = []
        total_token_usage = 0
        
        for agent, metrics in self.metrics.items():
            if metrics['task_count'] == 0:
                continue
            
            # 计算成功率
            success_rate = (metrics['success_count'] / metrics['task_count'] * 100) if metrics['task_count'] > 0 else 0
            
            # 计算平均响应时间
            avg_response_time = (sum(metrics['response_times']) / len(metrics['response_times'])) if metrics['response_times'] else 0
            
            # 识别瓶颈
            if avg_response_time > 30:  # 超过 30 秒
                report['collaboration_analysis']['slow_agents'].append({
                    'agent': agent,
                    'avg_response_time': avg_response_time
                })
            
            # 识别高失败率
            failure_rate = (metrics['failure_count'] / metrics['task_count'] * 100) if metrics['task_count'] > 0 else 0
            if failure_rate > 20:  # 失败率超过 20%
                report['collaboration_analysis']['high_failure_agents'].append({
                    'agent': agent,
                    'failure_rate': failure_rate
                })
            
            report['agents'][agent] = {
                'task_count': metrics['task_count'],
                'success_count': metrics['success_count'],
                'failure_count': metrics['failure_count'],
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'token_usage': metrics['token_usage'],
                'validation_levels': dict(metrics['validation_levels']),
                'failure_levels': dict(metrics['failure_levels'])
            }
            
            total_tasks += metrics['task_count']
            total_success += metrics['success_count']
            total_failure += metrics['failure_count']
            all_response_times.extend(metrics['response_times'])
            total_token_usage += metrics['token_usage']
        
        # 总体统计
        report['summary']['total_tasks'] = total_tasks
        report['summary']['total_success'] = total_success
        report['summary']['total_failure'] = total_failure
        report['summary']['success_rate'] = (total_success / total_tasks * 100) if total_tasks > 0 else 0
        report['summary']['avg_response_time'] = (sum(all_response_times) / len(all_response_times)) if all_response_times else 0
        report['summary']['total_token_usage'] = total_token_usage
        
        # 生成优化建议
        report['recommendations'] = self.generate_recommendations(report)
        
        # 保存报告
        self.save_report(report, date)
        
        return report
    
    def generate_recommendations(self, report):
        """
        生成优化建议
        """
        recommendations = []
        
        # 慢 Agent 优化建议
        for agent_info in report['collaboration_analysis']['slow_agents']:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'agent': agent_info['agent'],
                'issue': f"平均响应时间过长 ({agent_info['avg_response_time']:.2f}秒)",
                'suggestion': '考虑优化 Prompt 或升级到更快的模型'
            })
        
        # 高失败率 Agent 优化建议
        for agent_info in report['collaboration_analysis']['high_failure_agents']:
            recommendations.append({
                'type': 'reliability',
                'priority': 'high',
                'agent': agent_info['agent'],
                'issue': f"失败率过高 ({agent_info['failure_rate']:.2f}%)",
                'suggestion': '分析失败原因，加强培训或更换 Agent'
            })
        
        # 分级验证效果分析
        total_complete = sum(m['validation_levels'].get('complete', 0) for m in self.metrics.values())
        total_simplified = sum(m['validation_levels'].get('simplified', 0) for m in self.metrics.values())
        total_quick = sum(m['validation_levels'].get('quick', 0) for m in self.metrics.values())
        
        if total_simplified + total_quick > 0:
            saved_tokens = (total_simplified + total_quick) * 600  # 估算节省
            recommendations.append({
                'type': 'cost_optimization',
                'priority': 'medium',
                'issue': '分级验证效果良好',
                'suggestion': f'估算节省 Token: {saved_tokens}次/天',
                'metric': f'简化验证：{total_simplified}次，快速验证：{total_quick}次'
            })
        
        # 失败处理效果分析
        total_p0 = sum(m['failure_levels'].get('P0', 0) for m in self.metrics.values())
        total_p1 = sum(m['failure_levels'].get('P1', 0) for m in self.metrics.values())
        total_p2 = sum(m['failure_levels'].get('P2', 0) for m in self.metrics.values())
        
        if total_p0 + total_p1 + total_p2 > 0:
            recommendations.append({
                'type': 'failure_handling',
                'priority': 'medium',
                'issue': '失败处理机制运行中',
                'suggestion': f'P0: {total_p0}次，P1: {total_p1}次，P2: {total_p2}次',
                'metric': '失败处理流程正常运作'
            })
        
        return recommendations
    
    def save_report(self, report, date):
        """
        保存报告
        """
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_file = f"{REPORT_DIR}/daily_analysis_{date}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 同时生成 Markdown 版本
        md_file = f"{REPORT_DIR}/daily_analysis_{date}.md"
        self.save_markdown_report(report, md_file)
        
        print(f"✅ 报告已保存：{report_file}")
        print(f"✅ Markdown 报告已保存：{md_file}")
    
    def save_markdown_report(self, report, md_file):
        """
        保存 Markdown 格式报告
        """
        md_content = f"""# 每日日志分析报告

**分析日期：** {report['date']}  
**生成时间：** {report['generated_at']}

---

## 总体统计

| 指标 | 数值 |
|------|------|
| 总任务数 | {report['summary']['total_tasks']} |
| 成功数 | {report['summary']['total_success']} |
| 失败数 | {report['summary']['total_failure']} |
| 成功率 | {report['summary']['success_rate']:.2f}% |
| 平均响应时间 | {report['summary']['avg_response_time']:.2f}秒 |
| 总 Token 消耗 | {report['summary']['total_token_usage']}次 |

---

## Agent 表现

| Agent | 任务数 | 成功率 | 平均响应时间 | Token 消耗 |
|-------|--------|--------|-------------|-----------|
"""
        
        for agent, metrics in report['agents'].items():
            md_content += f"| {agent} | {metrics['task_count']} | {metrics['success_rate']:.2f}% | {metrics['avg_response_time']:.2f}秒 | {metrics['token_usage']} |\n"
        
        md_content += f"""
---

## 协作分析

### 慢 Agent
"""
        if report['collaboration_analysis']['slow_agents']:
            for agent_info in report['collaboration_analysis']['slow_agents']:
                md_content += f"- **{agent_info['agent']}**: 平均响应时间 {agent_info['avg_response_time']:.2f}秒\n"
        else:
            md_content += "- 无\n"
        
        md_content += f"""
### 高失败率 Agent
"""
        if report['collaboration_analysis']['high_failure_agents']:
            for agent_info in report['collaboration_analysis']['high_failure_agents']:
                md_content += f"- **{agent_info['agent']}**: 失败率 {agent_info['failure_rate']:.2f}%\n"
        else:
            md_content += "- 无\n"
        
        md_content += f"""
---

## 优化建议

"""
        for i, rec in enumerate(report['recommendations'], 1):
            md_content += f"""### {i}. {rec['type']} (优先级：{rec['priority']})
- **Agent:** {rec.get('agent', 'N/A')}
- **问题:** {rec['issue']}
- **建议:** {rec['suggestion']}
- **指标:** {rec.get('metric', 'N/A')}

"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

if __name__ == '__main__':
    analyzer = DailyLogAnalyzer()
    report = analyzer.analyze_logs()
    print(f"\n📊 分析完成！")
    print(f"✅ 总任务数：{report['summary']['total_tasks']}")
    print(f"✅ 成功率：{report['summary']['success_rate']:.2f}%")
    print(f"✅ 平均响应时间：{report['summary']['avg_response_time']:.2f}秒")
    print(f"✅ 优化建议：{len(report['recommendations'])}条")
