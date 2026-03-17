#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态并发调节模块
根据 CPU/内存使用率和失败率动态调整并发线程数

【验收标准】
- CPU>80% → 线程数下降
- CPU<50% → 线程数上升
- 失败率>10% → 线程数下降
- 调节日志输出
"""

import time
import logging
from typing import Tuple, Optional
from collections import deque

# 尝试导入 psutil，如果失败则使用 fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Fallback: 使用/proc 文件系统（Linux only）
    import os
    
# 配置日志
logger = logging.getLogger(__name__)


class DynamicConcurrency:
    """动态并发调节器"""
    
    def __init__(self, 
                 base_workers: int = 10,      # 基础线程数
                 min_workers: int = 5,        # 最小线程数
                 max_workers: int = 50,       # 最大线程数
                 cpu_high_threshold: float = 80.0,  # CPU 高负载阈值
                 cpu_low_threshold: float = 50.0,   # CPU 低负载阈值
                 memory_high_threshold: float = 80.0,  # 内存高负载阈值
                 failure_rate_high_threshold: float = 10.0,  # 失败率高阈值
                 failure_rate_low_threshold: float = 2.0,    # 失败率低阈值
                 adjustment_window: int = 100):  # 失败率统计窗口大小
        """
        初始化动态并发调节器
        
        Args:
            base_workers: 基础线程数
            min_workers: 最小线程数
            max_workers: 最大线程数
            cpu_high_threshold: CPU 高负载阈值（%）
            cpu_low_threshold: CPU 低负载阈值（%）
            memory_high_threshold: 内存高负载阈值（%）
            failure_rate_high_threshold: 失败率高阈值（%）
            failure_rate_low_threshold: 失败率低阈值（%）
            adjustment_window: 失败率统计窗口大小（最近 N 次请求）
        """
        self.base_workers = base_workers
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.current_workers = base_workers
        self.cpu_high_threshold = cpu_high_threshold
        self.cpu_low_threshold = cpu_low_threshold
        self.memory_high_threshold = memory_high_threshold
        self.failure_rate_high_threshold = failure_rate_high_threshold
        self.failure_rate_low_threshold = failure_rate_low_threshold
        
        # 失败率统计（使用 deque 维护固定大小的窗口）
        self.adjustment_window = adjustment_window
        self.request_results = deque(maxlen=adjustment_window)  # True=成功，False=失败
        
        # 调节日志
        self.adjustment_count = 0
        self.last_adjustment_time = time.time()
    
    def get_system_load(self) -> Tuple[float, float]:
        """
        获取系统负载
        
        Returns:
            (cpu_percent, memory_percent): CPU 和内存使用率
        """
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.1)  # 非阻塞模式
            memory_percent = psutil.virtual_memory().percent
        else:
            # Fallback: 使用/proc 文件系统（Linux only，粗略估计）
            try:
                # 读取/proc/loadavg 获取系统负载
                with open('/proc/loadavg', 'r') as f:
                    load_avg = f.read().split()
                    # 简化处理：假设 1 分钟负载平均 / CPU 核心数 * 100
                    import os
                    cpu_count = os.cpu_count() or 1
                    load_1min = float(load_avg[0])
                    cpu_percent = min(100.0, (load_1min / cpu_count) * 100)
                
                # 读取/proc/meminfo 获取内存使用率
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = int(parts[1].strip().split()[0])
                            meminfo[key] = value
                    
                    total = meminfo.get('MemTotal', 1)
                    available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                    memory_percent = ((total - available) / total) * 100
            except Exception as e:
                logger.warning(f"无法读取系统负载，使用默认值：{e}")
                cpu_percent = 50.0
                memory_percent = 50.0
        
        return cpu_percent, memory_percent
    
    def get_failure_rate(self) -> float:
        """
        计算失败率
        
        Returns:
            failure_rate: 失败率（%），如果窗口为空则返回 0
        """
        if not self.request_results:
            return 0.0
        
        failed_count = sum(1 for result in self.request_results if not result)
        failure_rate = (failed_count / len(self.request_results)) * 100
        return failure_rate
    
    def record_request(self, success: bool):
        """
        记录请求结果（用于计算失败率）
        
        Args:
            success: 请求是否成功
        """
        self.request_results.append(success)
    
    def adjust_workers(self, verbose: bool = True) -> int:
        """
        动态调整线程数
        
        Args:
            verbose: 是否输出详细日志
        
        Returns:
            new_workers: 调整后的线程数
        """
        cpu_percent, memory_percent = self.get_system_load()
        failure_rate = self.get_failure_rate()
        
        original_workers = self.current_workers
        adjustment_reason = None
        
        # 优先级 1：内存过高，立即降低并发（最危险）
        if memory_percent > self.memory_high_threshold:
            new_workers = max(self.min_workers, self.current_workers - 10)
            adjustment_reason = f"内存过高 ({memory_percent:.1f}%)"
            self.current_workers = new_workers
        
        # 优先级 2：CPU 过高，降低并发
        elif cpu_percent > self.cpu_high_threshold:
            new_workers = max(self.min_workers, self.current_workers - 10)
            adjustment_reason = f"CPU 过高 ({cpu_percent:.1f}%)"
            self.current_workers = new_workers
        
        # 优先级 3：失败率过高，降低并发
        elif failure_rate > self.failure_rate_high_threshold:
            new_workers = max(self.min_workers, self.current_workers - 5)
            adjustment_reason = f"失败率过高 ({failure_rate:.1f}%)"
            self.current_workers = new_workers
        
        # 优先级 4：CPU 过低且失败率低，提高并发
        elif cpu_percent < self.cpu_low_threshold and failure_rate < self.failure_rate_low_threshold:
            new_workers = min(self.max_workers, self.current_workers + 10)
            adjustment_reason = f"CPU 充足 ({cpu_percent:.1f}%) 且失败率低 ({failure_rate:.1f}%)"
            self.current_workers = new_workers
        
        # 记录调节日志
        if self.current_workers != original_workers:
            self.adjustment_count += 1
            self.last_adjustment_time = time.time()
            
            if verbose:
                direction = "↑" if self.current_workers > original_workers else "↓"
                logger.info(
                    f"🔄 动态并发调节 #{self.adjustment_count}: "
                    f"{adjustment_reason} → 线程数 {direction} {original_workers} → {self.current_workers}"
                )
        else:
            if verbose:
                logger.debug(
                    f"✔️  并发保持稳定：CPU={cpu_percent:.1f}% | "
                    f"内存={memory_percent:.1f}% | 失败率={failure_rate:.1f}% | "
                    f"线程数={self.current_workers}"
                )
        
        return self.current_workers
    
    def get_workers(self) -> int:
        """
        获取当前推荐线程数
        
        Returns:
            current_workers: 当前线程数
        """
        return self.current_workers
    
    def reset_statistics(self):
        """重置统计信息"""
        self.request_results.clear()
        self.adjustment_count = 0
        self.last_adjustment_time = time.time()
        logger.info("✅ 动态并发统计已重置")
    
    def get_statistics(self) -> dict:
        """
        获取统计信息
        
        Returns:
            stats: 统计信息字典
        """
        cpu_percent, memory_percent = self.get_system_load()
        return {
            'current_workers': self.current_workers,
            'base_workers': self.base_workers,
            'min_workers': self.min_workers,
            'max_workers': self.max_workers,
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'failure_rate': self.get_failure_rate(),
            'adjustment_count': self.adjustment_count,
            'window_size': len(self.request_results),
            'last_adjustment_time': self.last_adjustment_time
        }
    
    def monitor_loop(self, interval: int = 60, verbose: bool = True):
        """
        监控循环（定期调整并发）
        
        Args:
            interval: 调整间隔（秒）
            verbose: 是否输出详细日志
        """
        logger.info(f"🔍 开始动态并发监控，初始并发：{self.current_workers} 线程")
        logger.info(
            f"📊 阈值配置：CPU 高={self.cpu_high_threshold}% / 低={self.cpu_low_threshold}% / "
            f"内存高={self.memory_high_threshold}% / 失败率高={self.failure_rate_high_threshold}%"
        )
        
        try:
            while True:
                self.adjust_workers(verbose=verbose)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("🛑 动态并发监控已停止")


# 使用示例和测试
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建动态并发调节器
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        cpu_high_threshold=80.0,
        cpu_low_threshold=50.0,
        memory_high_threshold=80.0,
        failure_rate_high_threshold=10.0,
        failure_rate_low_threshold=2.0
    )
    
    print("="*80)
    print("动态并发调节器 - 测试模式")
    print("="*80)
    
    # 模拟测试：展示调节逻辑
    print("\n【测试 1】正常状态")
    stats = dc.get_statistics()
    print(f"  当前线程数：{stats['current_workers']}")
    print(f"  CPU: {stats['cpu_percent']:.1f}%")
    print(f"  内存：{stats['memory_percent']:.1f}%")
    print(f"  失败率：{stats['failure_rate']:.1f}%")
    
    print("\n【测试 2】模拟高失败率场景")
    for i in range(50):
        dc.record_request(success=False)  # 模拟连续失败
    dc.adjust_workers()
    print(f"  调整后线程数：{dc.get_workers()}")
    
    print("\n【测试 3】重置统计")
    dc.reset_statistics()
    print(f"  重置后线程数：{dc.get_workers()}")
    
    print("\n【测试 4】启动监控循环（按 Ctrl+C 停止）")
    print("="*80)
    
    # 启动监控循环
    dc.monitor_loop(interval=5, verbose=True)
