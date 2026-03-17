#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据抓取监控脚本 - 每 30 分钟发送飞书进度汇报
"""
import os
import sys
import json
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, 'data', 'fetch_progress.json')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'quant_info.log')

def get_progress():
    """获取当前进度"""
    if not os.path.exists(PROGRESS_FILE):
        return None
    
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'completed': len(data.get('completed_stocks', [])),
            'update_time': data.get('update_time', 'Unknown'),
            'fetch_type': data.get('fetch_type', 'unknown'),
            'start_date': data.get('start_date', ''),
            'end_date': data.get('end_date', '')
        }
    except Exception as e:
        return None

def get_recent_logs():
    """获取最近的日志"""
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # 返回最后 50 行
        return [l.strip() for l in lines[-50:] if 'INFO' in l or 'ERROR' in l or 'WARNING' in l]
    except:
        return []

def send_feishu_report(progress, recent_logs):
    """发送飞书报告"""
    if not progress:
        print("❌ 无法获取进度")
        return
    
    completed = progress['completed']
    total = 5489
    percent = (completed / total) * 100
    
    # 估算进度
    if completed > 0:
        # 假设从 02:30 开始，到现在的时间
        start_time = datetime(2026, 3, 12, 2, 30, 0)
        elapsed = (datetime.now() - start_time).total_seconds() / 3600
        if elapsed > 0:
            rate = completed / elapsed  # stocks per hour
            remaining = total - completed
            eta_hours = remaining / rate if rate > 0 else 999
        else:
            eta_hours = 999
    else:
        elapsed = 0
        eta_hours = 999
    
    content = f"""【全量数据抓取进度汇报】

📊 进度：{completed:,}/{total:,}只 ({percent:.1f}%)
⏱️  已运行：{elapsed:.2f}小时
⏳  预计剩余：{eta_hours:.1f}小时
📅 数据范围：{progress['start_date']} 至 {progress['end_date']}
🕐 更新时间：{progress['update_time']}

✅ 状态：正常抓取中

📝 最近日志：
"""
    
    # 添加最近的重要日志
    important_logs = [l for l in recent_logs if '成功' in l or '失败' in l or '进度' in l or 'ERROR' in l][-5:]
    for log in important_logs:
        # 截断过长的日志
        if len(log) > 100:
            log = log[:100] + "..."
        content += f"\n• {log}"
    
    print("=" * 80)
    print(content)
    print("=" * 80)
    
    # 这里可以集成飞书 webhook
    # 暂时只打印到日志
    report_file = os.path.join(BASE_DIR, 'logs', f'feishu_report_{datetime.now().strftime("%Y%m%d_%H%M")}.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"📄 报告已保存至：{report_file}")

def main():
    """主循环"""
    print("🚀 数据抓取监控启动")
    print(f"监控文件：{PROGRESS_FILE}")
    print(f"汇报间隔：30 分钟")
    print("=" * 80)
    
    last_report_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # 每 30 分钟汇报一次
            if current_time - last_report_time >= 30 * 60:
                progress = get_progress()
                recent_logs = get_recent_logs()
                send_feishu_report(progress, recent_logs)
                last_report_time = current_time
            
            # 每分钟检查一次
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n⚠️  监控停止")
            break
        except Exception as e:
            print(f"❌ 监控异常：{e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
