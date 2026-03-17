#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据抓取进度监控面板
版本：v1.0
创建时间：2026-03-12

功能：
1. 实时监控抓取进度
2. 显示速率和 ETA
3. 监控进程状态
4. 生成可视化报告
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# ============================================== 【配置区】 ==============================================
WORK_DIR = Path('/home/admin/.openclaw/agents/master')
DATA_DIR = WORK_DIR / 'data_all_stocks'
LOG_DIR = WORK_DIR / 'logs'
CHECKPOINT_DIR = WORK_DIR / 'checkpoints'
DASHBOARD_DIR = WORK_DIR / 'dashboards'

# 确保目录存在
for dir_path in [LOG_DIR, CHECKPOINT_DIR, DASHBOARD_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 监控配置
MONITOR_CONFIG = {
    'refresh_interval': 5,        # 刷新间隔（秒）
    'show_history': True,         # 显示历史记录
    'export_html': True,          # 导出 HTML 报告
    'total_stocks': 5000,         # 总股票数（估算）
}

# ============================================== 【日志配置】 ==============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================== 【进度监控器】 ==============================================
class ProgressMonitor:
    """进度监控器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.history = []
    
    def get_lock_status(self) -> Dict:
        """获取进程锁状态"""
        lock_file = Path('/tmp/fetch_data.lock')
        
        if lock_file.exists():
            try:
                with open(lock_file, 'r') as f:
                    lines = f.readlines()
                    pid = lines[0].strip() if len(lines) > 0 else 'unknown'
                    timestamp = lines[1].strip() if len(lines) > 1 else 'unknown'
                
                # 检查进程是否还在运行
                import subprocess
                try:
                    result = subprocess.run(['ps', '-p', pid], capture_output=True, text=True)
                    running = result.returncode == 0
                except:
                    running = False
                
                return {
                    'locked': True,
                    'pid': pid,
                    'start_time': timestamp,
                    'running': running,
                }
            except Exception as e:
                return {'locked': False, 'error': str(e)}
        else:
            return {'locked': False}
    
    def get_data_statistics(self) -> Dict:
        """获取数据统计"""
        if not DATA_DIR.exists():
            return {'total_files': 0, 'total_size_mb': 0}
        
        data_files = list(DATA_DIR.glob('*.json'))
        total_size = sum(f.stat().st_size for f in data_files)
        
        return {
            'total_files': len(data_files),
            'total_size_mb': total_size / (1024 * 1024),
            'latest_file': max(data_files, key=lambda f: f.stat().st_mtime).name if data_files else None,
        }
    
    def get_checkpoint_info(self) -> Dict:
        """获取检查点信息"""
        if not CHECKPOINT_DIR.exists():
            return {'checkpoints': [], 'latest': None}
        
        checkpoints = sorted(CHECKPOINT_DIR.glob('checkpoint_*.json'), 
                            key=lambda f: f.stat().st_mtime, reverse=True)
        
        latest = None
        if checkpoints:
            try:
                with open(checkpoints[0], 'r', encoding='utf-8') as f:
                    latest = json.load(f)
            except:
                pass
        
        return {
            'checkpoints': [str(c) for c in checkpoints[:5]],
            'latest': latest,
        }
    
    def get_recent_logs(self, lines: int = 20) -> List[str]:
        """获取最近日志"""
        if not LOG_DIR.exists():
            return []
        
        log_files = sorted(LOG_DIR.glob('fetch_*.log'), 
                          key=lambda f: f.stat().st_mtime, reverse=True)
        
        if not log_files:
            return []
        
        try:
            with open(log_files[0], 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except:
            return []
    
    def calculate_progress(self) -> Dict:
        """计算进度"""
        stats = self.get_data_statistics()
        checkpoint = self.get_checkpoint_info()
        
        total = self.config['total_stocks']
        processed = stats['total_files']
        progress_pct = (processed / total) * 100 if total > 0 else 0
        
        # 估算剩余时间（基于检查点）
        eta_minutes = None
        rate_per_min = None
        
        if checkpoint['latest'] and 'progress' in checkpoint['latest']:
            prog = checkpoint['latest']['progress']
            if prog.get('rate_per_min', 0) > 0:
                rate_per_min = prog['rate_per_min']
                remaining = total - processed
                eta_minutes = remaining / rate_per_min if rate_per_min > 0 else None
        
        return {
            'total': total,
            'processed': processed,
            'progress_pct': progress_pct,
            'remaining': total - processed,
            'rate_per_min': rate_per_min,
            'eta_minutes': eta_minutes,
            'data_size_mb': stats['total_size_mb'],
        }
    
    def generate_dashboard(self) -> str:
        """生成文本仪表板"""
        lock_status = self.get_lock_status()
        progress = self.calculate_progress()
        logs = self.get_recent_logs(10)
        
        dashboard = []
        dashboard.append("="*80)
        dashboard.append("  📊 数据抓取进度监控面板")
        dashboard.append("="*80)
        dashboard.append(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        dashboard.append("")
        
        # 进程锁状态
        dashboard.append("🔒 进程锁状态:")
        if lock_status.get('locked'):
            dashboard.append(f"   状态：🔒 已锁定")
            dashboard.append(f"   进程 PID: {lock_status.get('pid', 'N/A')}")
            dashboard.append(f"   运行中：{'✅ 是' if lock_status.get('running') else '❌ 否'}")
            dashboard.append(f"   启动时间：{lock_status.get('start_time', 'N/A')}")
        else:
            dashboard.append(f"   状态：🔓 未锁定")
        dashboard.append("")
        
        # 抓取进度
        dashboard.append("📈 抓取进度:")
        dashboard.append(f"   总股票数：{progress['total']}")
        dashboard.append(f"   已处理：{progress['processed']} ({progress['progress_pct']:.1f}%)")
        dashboard.append(f"   剩余：{progress['remaining']}")
        if progress['rate_per_min']:
            dashboard.append(f"   速率：{progress['rate_per_min']:.1f} 次/分钟")
        if progress['eta_minutes']:
            dashboard.append(f"   预计剩余：{progress['eta_minutes']:.1f} 分钟")
        dashboard.append(f"   数据大小：{progress['data_size_mb']:.2f} MB")
        dashboard.append("")
        
        # 最近日志
        if logs:
            dashboard.append("📝 最近日志:")
            for log in logs:
                dashboard.append(f"   {log}")
        dashboard.append("")
        
        dashboard.append("="*80)
        
        return "\n".join(dashboard)
    
    def export_html_report(self, output_path: Path = None):
        """导出 HTML 报告"""
        if not self.config.get('export_html', True):
            return None
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = DASHBOARD_DIR / f'dashboard_{timestamp}.html'
        
        progress = self.calculate_progress()
        lock_status = self.get_lock_status()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>数据抓取进度监控</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .status {{ display: inline-block; padding: 5px 15px; border-radius: 4px; margin: 5px 0; }}
        .status-locked {{ background: #ffeb3b; color: #333; }}
        .status-unlocked {{ background: #e8f5e9; color: #2e7d32; }}
        .progress-bar {{ width: 100%; height: 30px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); transition: width 0.3s; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .logs {{ background: #263238; color: #aed581; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 300px; overflow-y: auto; }}
        .timestamp {{ color: #90a4ae; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 数据抓取进度监控</h1>
        <p>更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>🔒 进程锁状态</h2>
        <div class="status {'status-locked' if lock_status.get('locked') else 'status-unlocked'}">
            {'🔒 已锁定' if lock_status.get('locked') else '🔓 未锁定'}
        </div>
        {f"<p>进程 PID: {lock_status.get('pid', 'N/A')}</p>" if lock_status.get('locked') else ''}
        {f"<p>运行中：{'✅ 是' if lock_status.get('running') else '❌ 否'}</p>" if lock_status.get('locked') else ''}
        
        <h2>📈 抓取进度</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress['progress_pct']:.1f}%"></div>
        </div>
        <p>进度：{progress['progress_pct']:.1f}% ({progress['processed']}/{progress['total']})</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{progress['processed']}</div>
                <div class="stat-label">已处理股票</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{progress['remaining']}</div>
                <div class="stat-label">剩余股票</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{progress['data_size_mb']:.1f} MB</div>
                <div class="stat-label">数据大小</div>
            </div>
            {f'<div class="stat-card"><div class="stat-value">{progress["rate_per_min"]:.1f}</div><div class="stat-label">速率 (次/分钟)</div></div>' if progress.get('rate_per_min') else ''}
            {f'<div class="stat-card"><div class="stat-value">{progress["eta_minutes"]:.1f}</div><div class="stat-label">预计剩余 (分钟)</div></div>' if progress.get('eta_minutes') else ''}
        </div>
        
        <h2>📝 使用说明</h2>
        <ul>
            <li>刷新页面查看最新进度</li>
            <li>日志文件：logs/fetch_*.log</li>
            <li>检查点：checkpoints/checkpoint_*.json</li>
            <li>数据目录：data_all_stocks/</li>
        </ul>
    </div>
    
    <script>
        // 自动刷新（每 30 秒）
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"✅ HTML 仪表板已导出：{output_path}")
        return output_path
    
    def run_monitor(self, duration_minutes: int = None):
        """运行监控（持续模式）"""
        logger.info("🚀 启动进度监控...")
        logger.info("按 Ctrl+C 停止监控")
        
        start_time = time.time()
        
        try:
            while True:
                # 检查是否超时
                if duration_minutes:
                    elapsed = (time.time() - start_time) / 60
                    if elapsed >= duration_minutes:
                        logger.info(f"⏰ 监控时长已达{duration_minutes}分钟，停止监控")
                        break
                
                # 显示仪表板
                dashboard = self.generate_dashboard()
                print("\033[2J\033[H", end='')  # 清屏
                print(dashboard)
                
                # 导出 HTML
                self.export_html_report()
                
                # 记录历史
                self.history.append({
                    'timestamp': datetime.now().isoformat(),
                    'progress': self.calculate_progress(),
                })
                
                # 等待刷新
                time.sleep(self.config['refresh_interval'])
        
        except KeyboardInterrupt:
            logger.info("🛑 监控已手动停止")
        
        # 保存历史记录
        if self.config.get('show_history') and self.history:
            history_file = DASHBOARD_DIR / f'monitor_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 历史记录已保存：{history_file}")

# ============================================== 【主程序入口】 ==============================================
def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据抓取进度监控面板')
    parser.add_argument('--duration', type=int, help='监控时长（分钟）')
    parser.add_argument('--once', action='store_true', help='只显示一次，不持续监控')
    parser.add_argument('--html', action='store_true', help='只导出 HTML 报告')
    
    args = parser.parse_args()
    
    print("="*80)
    print("  📊 数据抓取进度监控面板")
    print("="*80)
    
    monitor = ProgressMonitor(MONITOR_CONFIG)
    
    if args.html:
        # 只导出 HTML
        html_path = monitor.export_html_report()
        print(f"✅ HTML 报告已导出：{html_path}")
    
    elif args.once:
        # 只显示一次
        dashboard = monitor.generate_dashboard()
        print(dashboard)
        monitor.export_html_report()
    
    else:
        # 持续监控
        monitor.run_monitor(duration_minutes=args.duration)

if __name__ == '__main__':
    main()
