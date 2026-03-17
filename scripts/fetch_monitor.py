#!/home/admin/.openclaw/agents/master/venv/bin/python3
# -*- coding: utf-8 -*-
"""
全量抓取监控脚本
职责：
1. 实时监控抓取进度
2. 每 30 分钟发送飞书进度汇报
3. 检测异常（失败率>10% 立即告警）
4. 资源监控（CPU/内存/磁盘）
5. 预计完成时间动态计算
"""

import os
import sys
import json
import time
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
MASTER_DIR = Path('/home/admin/.openclaw/agents/master')
DATA_DIR = MASTER_DIR / 'data'
DATA_ALL_STOCKS_DIR = MASTER_DIR / 'data_all_stocks'
LOGS_DIR = MASTER_DIR / 'logs'
PROGRESS_FILE = DATA_DIR / 'fetch_progress.json'
FAILED_STOCKS_FILE = DATA_DIR / 'failed_stocks.json'
STOCK_BASIC_FILE = DATA_DIR / 'stock_basic.csv'
MONITOR_LOG = LOGS_DIR / 'fetch_monitor.log'

# 数据分类
DATA_TYPES = {
    '日线': ['daily.parquet', 'daily_basic.parquet'],
    '财务': ['balancesheet.parquet', 'income.parquet', 'cashflow.parquet', 'fina_indicator.parquet'],
    '资金流': ['moneyflow.parquet', 'block_trade.parquet'],
    '其他': ['concept_detail.parquet', 'cyq_chips.parquet', 'cyq_perf.parquet', 'hk_hold.parquet']
}

# 飞书 webhook（从环境变量或配置读取）
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK', '')

def log_message(msg, level='INFO'):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"{timestamp} - {level} - {msg}"
    print(log_line)
    try:
        with open(MONITOR_LOG, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except Exception as e:
        print(f"写入日志失败：{e}")

def get_total_stocks():
    """获取总股票数"""
    if STOCK_BASIC_FILE.exists():
        with open(STOCK_BASIC_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return len(lines) - 1  # 减去表头
    return 0

def get_progress():
    """获取当前抓取进度"""
    if not PROGRESS_FILE.exists():
        return {'completed': [], 'total': 0, 'update_time': None}
    
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                'completed': data.get('completed_stocks', []),
                'total': data.get('total_count', 0),
                'update_time': data.get('update_time', ''),
                'fetch_type': data.get('fetch_type', 'unknown'),
                'start_date': data.get('start_date', ''),
                'end_date': data.get('end_date', '')
            }
    except Exception as e:
        log_message(f"读取进度文件失败：{e}", 'ERROR')
        return {'completed': [], 'total': 0, 'update_time': None}

def get_failed_stocks():
    """获取失败股票列表"""
    if not FAILED_STOCKS_FILE.exists():
        return []
    
    try:
        with open(FAILED_STOCKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"读取失败股票文件失败：{e}", 'ERROR')
        return []

def get_data_type_progress():
    """获取各数据类型的进度"""
    progress = {'日线': 0, '财务': 0, '资金流': 0, '其他': 0}
    
    if not DATA_ALL_STOCKS_DIR.exists():
        return progress
    
    completed_stocks = get_progress()['completed']
    
    for stock in completed_stocks[:100]:  # 抽样检查前 100 只
        stock_dir = DATA_ALL_STOCKS_DIR / stock
        if not stock_dir.exists():
            continue
        
        for data_type, files in DATA_TYPES.items():
            has_all = all((stock_dir / f).exists() for f in files)
            if has_all:
                progress[data_type] += 1
    
    return progress

def get_resource_usage():
    """获取系统资源使用情况"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取抓取进程的资源使用
        fetch_process = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'fetch_data_optimized.py' in cmdline:
                    fetch_process = proc
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        fetch_cpu = 0
        fetch_memory = 0
        if fetch_process:
            try:
                fetch_cpu = fetch_process.cpu_percent(interval=0)
                fetch_memory = fetch_process.memory_info().rss / 1024 / 1024  # MB
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'system': {
                'cpu': cpu_percent,
                'memory_used': memory.used / 1024 / 1024 / 1024,  # GB
                'memory_total': memory.total / 1024 / 1024 / 1024,  # GB
                'memory_percent': memory.percent,
                'disk_used': disk.used / 1024 / 1024 / 1024,  # GB
                'disk_total': disk.total / 1024 / 1024 / 1024,  # GB
                'disk_percent': disk.percent
            },
            'fetch_process': {
                'pid': fetch_process.pid if fetch_process else None,
                'cpu': fetch_cpu,
                'memory_mb': fetch_memory
            }
        }
    except Exception as e:
        log_message(f"获取资源使用失败：{e}", 'ERROR')
        return None

def calculate_eta(start_time, completed, total):
    """计算预计完成时间"""
    if completed <= 0 or start_time is None:
        return None
    
    elapsed = (datetime.now() - start_time).total_seconds()
    if elapsed <= 0:
        return None
    
    rate = completed / elapsed  # stocks per second
    remaining = total - completed
    
    if rate <= 0:
        return None
    
    eta_seconds = remaining / rate
    eta_time = datetime.now() + timedelta(seconds=eta_seconds)
    
    return {
        'eta_time': eta_time,
        'eta_hours': eta_seconds / 3600,
        'rate_per_hour': rate * 3600
    }

def check_anomalies(progress, failed_stocks, total):
    """检测异常"""
    anomalies = []
    
    # 检查失败率
    if total > 0:
        failure_rate = len(failed_stocks) / total * 100
        if failure_rate > 10:
            anomalies.append({
                'type': 'HIGH_FAILURE_RATE',
                'level': 'CRITICAL',
                'message': f'失败率过高：{failure_rate:.2f}% (>{len(failed_stocks)}只股票失败)',
                'failed_stocks': failed_stocks[:10]  # 只显示前 10 个
            })
    
    # 检查进度停滞（超过 10 分钟无更新）
    update_time = progress.get('update_time')
    if update_time:
        try:
            last_update = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - last_update).total_seconds() > 600:
                anomalies.append({
                    'type': 'PROGRESS_STALLED',
                    'level': 'WARNING',
                    'message': f'进度停滞超过 10 分钟（最后更新：{update_time}）'
                })
        except Exception:
            pass
    
    return anomalies

def send_feishu_report(title, content, is_alert=False):
    """发送飞书消息"""
    if not FEISHU_WEBHOOK:
        log_message("未配置飞书 webhook，跳过发送")
        print(f"\n=== 飞书消息 ===\n{title}\n{content}\n================\n")
        return False
    
    try:
        import requests
        
        color = 'red' if is_alert else 'blue'
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }
        
        response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        if response.status_code == 200:
            log_message("飞书消息发送成功")
            return True
        else:
            log_message(f"飞书消息发送失败：{response.status_code}", 'ERROR')
            return False
    except Exception as e:
        log_message(f"发送飞书消息异常：{e}", 'ERROR')
        return False

def generate_report(progress, failed_stocks, resources, eta, anomalies, data_type_progress):
    """生成监控报告"""
    total_stocks = get_total_stocks()
    completed = len(progress['completed'])
    progress_percent = (completed / total_stocks * 100) if total_stocks > 0 else 0
    
    report = []
    report.append(f"**📊 抓取进度总览**")
    report.append(f"• 总进度：{completed}/{total_stocks} ({progress_percent:.1f}%)")
    report.append(f"• 抓取类型：{progress.get('fetch_type', 'unknown')}")
    report.append(f"• 日期范围：{progress.get('start_date', '')} ~ {progress.get('end_date', '')}")
    report.append(f"• 最后更新：{progress.get('update_time', 'N/A')}")
    report.append("")
    
    report.append(f"**📁 分类数据进度**（抽样）")
    for data_type, count in data_type_progress.items():
        report.append(f"• {data_type}: ~{count}只股票")
    report.append("")
    
    if failed_stocks:
        report.append(f"**❌ 失败统计**")
        report.append(f"• 失败数量：{len(failed_stocks)}只")
        report.append(f"• 失败率：{len(failed_stocks)/total_stocks*100:.2f}%")
        if failed_stocks:
            report.append(f"• 失败示例：{', '.join(failed_stocks[:5])}")
        report.append("")
    
    if resources:
        report.append(f"**💻 资源使用**")
        sys_res = resources['system']
        report.append(f"• CPU: {sys_res['cpu']:.1f}%")
        report.append(f"• 内存：{sys_res['memory_used']:.2f}GB / {sys_res['memory_total']:.2f}GB ({sys_res['memory_percent']:.1f}%)")
        report.append(f"• 磁盘：{sys_res['disk_used']:.2f}GB / {sys_res['disk_total']:.2f}GB ({sys_res['disk_percent']:.1f}%)")
        
        fetch_proc = resources['fetch_process']
        if fetch_proc['pid']:
            report.append(f"• 抓取进程 (PID {fetch_proc['pid']}): CPU {fetch_proc['cpu']:.1f}%, 内存 {fetch_proc['memory_mb']:.1f}MB")
        report.append("")
    
    if eta:
        report.append(f"**⏰ 预计完成时间**")
        report.append(f"• 预计完成：{eta['eta_time'].strftime('%Y-%m-%d %H:%M')}")
        report.append(f"• 剩余时间：{eta['eta_hours']:.1f}小时")
        report.append(f"• 抓取速度：{eta['rate_per_hour']:.1f}只/小时")
        report.append("")
    
    if anomalies:
        report.append(f"**⚠️ 异常告警**")
        for anomaly in anomalies:
            emoji = "🔴" if anomaly['level'] == 'CRITICAL' else "🟡"
            report.append(f"{emoji} {anomaly['message']}")
        report.append("")
    
    return '\n'.join(report)

def main():
    """主函数"""
    log_message("=" * 50)
    log_message("抓取监控启动")
    
    # 获取抓取进程启动时间（近似）
    start_time = datetime.now() - timedelta(hours=1)  # 假设 1 小时前启动
    
    last_report_time = time.time()
    REPORT_INTERVAL = 30 * 60  # 30 分钟
    
    while True:
        try:
            # 获取最新状态
            progress = get_progress()
            failed_stocks = get_failed_stocks()
            resources = get_resource_usage()
            data_type_progress = get_data_type_progress()
            
            total_stocks = get_total_stocks()
            completed = len(progress['completed'])
            
            # 计算 ETA
            eta = calculate_eta(start_time, completed, total_stocks)
            
            # 检查异常
            anomalies = check_anomalies(progress, failed_stocks, total_stocks)
            
            # 生成报告
            report_content = generate_report(
                progress, failed_stocks, resources, eta, anomalies, data_type_progress
            )
            
            # 记录日志
            log_message(f"进度更新：{completed}/{total_stocks} ({len(anomalies)}个异常)")
            
            # 发送告警（如有严重异常）
            critical_anomalies = [a for a in anomalies if a['level'] == 'CRITICAL']
            if critical_anomalies:
                alert_title = "🚨 抓取异常告警"
                alert_content = "**严重异常 detected:**\n\n" + '\n'.join([
                    f"• {a['message']}" for a in critical_anomalies
                ])
                send_feishu_report(alert_title, alert_content, is_alert=True)
            
            # 定期发送进度汇报（每 30 分钟）
            current_time = time.time()
            if current_time - last_report_time >= REPORT_INTERVAL:
                report_title = "📈 抓取进度汇报"
                send_feishu_report(report_title, report_content, is_alert=False)
                last_report_time = current_time
            
            # 检查是否完成
            if completed >= total_stocks and total_stocks > 0:
                log_message("✅ 抓取任务已完成！")
                final_title = "✅ 抓取任务完成"
                send_feishu_report(final_title, report_content + "\n\n**🎉 所有股票数据抓取完成！**")
                break
            
            # 等待下一次检查
            time.sleep(60)  # 每分钟检查一次
            
        except KeyboardInterrupt:
            log_message("监控被用户中断")
            break
        except Exception as e:
            log_message(f"监控循环异常：{e}", 'ERROR')
            time.sleep(60)

if __name__ == '__main__':
    main()
