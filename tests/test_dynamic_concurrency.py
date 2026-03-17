#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态并发模块测试脚本
测试场景：
1. CPU 高负载 → 验证线程数下降
2. CPU 低负载 → 验证线程数上升
3. 失败率高 → 验证线程数下降
4. 调节日志输出
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dynamic_concurrency import DynamicConcurrency


def test_basic_functionality():
    """测试 1：基本功能测试"""
    print("="*80)
    print("测试 1：基本功能测试")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50
    )
    
    # 初始状态
    assert dc.get_workers() == 10, "初始线程数应为 10"
    print(f"✅ 初始线程数：{dc.get_workers()}")
    
    # 获取系统负载
    cpu, mem = dc.get_system_load()
    print(f"✅ 当前系统负载：CPU={cpu:.1f}%, 内存={mem:.1f}%")
    
    # 获取失败率（空窗口）
    failure_rate = dc.get_failure_rate()
    assert failure_rate == 0.0, "空窗口失败率应为 0"
    print(f"✅ 当前失败率：{failure_rate:.1f}%")
    
    print("✅ 测试 1 通过：基本功能正常\n")


def test_failure_rate_recording():
    """测试 2：失败率记录测试"""
    print("="*80)
    print("测试 2：失败率记录测试")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        adjustment_window=100
    )
    
    # 模拟 100 次请求，50 次失败
    print("模拟 100 次请求，50 次成功，50 次失败...")
    for i in range(50):
        dc.record_request(success=True)
        dc.record_request(success=False)
    
    failure_rate = dc.get_failure_rate()
    print(f"✅ 失败率：{failure_rate:.1f}%")
    assert 49.0 <= failure_rate <= 51.0, f"失败率应接近 50%，实际：{failure_rate}"
    
    # 模拟高失败率场景（90% 失败）
    dc.reset_statistics()
    print("\n模拟 100 次请求，90 次失败...")
    for i in range(90):
        dc.record_request(success=False)
    for i in range(10):
        dc.record_request(success=True)
    
    failure_rate = dc.get_failure_rate()
    print(f"✅ 失败率：{failure_rate:.1f}%")
    assert failure_rate > 85.0, f"失败率应大于 85%，实际：{failure_rate}"
    
    print("✅ 测试 2 通过：失败率记录正常\n")


def test_cpu_high_adjustment():
    """测试 3：模拟 CPU 高负载调节"""
    print("="*80)
    print("测试 3：模拟 CPU 高负载调节")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        cpu_high_threshold=80.0
    )
    
    # 模拟 CPU 高负载（通过 monkey patch）
    original_get_system_load = dc.get_system_load
    
    def mock_get_system_load_high_cpu():
        return 85.0, 50.0  # CPU 85%, 内存 50%
    
    dc.get_system_load = mock_get_system_load_high_cpu
    
    # 调整前
    original_workers = dc.get_workers()
    print(f"调整前线程数：{original_workers}")
    
    # 执行调整
    new_workers = dc.adjust_workers(verbose=True)
    print(f"调整后线程数：{new_workers}")
    
    # 验证线程数下降
    assert new_workers < original_workers, f"CPU 高负载时线程数应下降：{original_workers} → {new_workers}"
    assert new_workers >= dc.min_workers, f"线程数不应低于最小值：{new_workers} >= {dc.min_workers}"
    
    print("✅ 测试 3 通过：CPU 高负载时线程数下降\n")


def test_cpu_low_adjustment():
    """测试 4：模拟 CPU 低负载调节"""
    print("="*80)
    print("测试 4：模拟 CPU 低负载调节")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        cpu_low_threshold=50.0
    )
    
    # 先记录一些成功请求（保持低失败率）
    for i in range(20):
        dc.record_request(success=True)
    
    # 模拟 CPU 低负载
    def mock_get_system_load_low_cpu():
        return 40.0, 50.0  # CPU 40%, 内存 50%
    
    dc.get_system_load = mock_get_system_load_low_cpu
    
    # 调整前
    original_workers = dc.get_workers()
    print(f"调整前线程数：{original_workers}")
    
    # 执行调整
    new_workers = dc.adjust_workers(verbose=True)
    print(f"调整后线程数：{new_workers}")
    
    # 验证线程数上升
    assert new_workers > original_workers, f"CPU 低负载时线程数应上升：{original_workers} → {new_workers}"
    assert new_workers <= dc.max_workers, f"线程数不应超过最大值：{new_workers} <= {dc.max_workers}"
    
    print("✅ 测试 4 通过：CPU 低负载时线程数上升\n")


def test_failure_rate_adjustment():
    """测试 5：模拟高失败率调节"""
    print("="*80)
    print("测试 5：模拟高失败率调节")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        failure_rate_high_threshold=10.0
    )
    
    # 模拟高失败率（90% 失败）
    for i in range(90):
        dc.record_request(success=False)
    for i in range(10):
        dc.record_request(success=True)
    
    # 模拟正常 CPU 和内存
    def mock_get_system_load_normal():
        return 60.0, 60.0  # CPU 60%, 内存 60%
    
    dc.get_system_load = mock_get_system_load_normal
    
    # 调整前
    original_workers = dc.get_workers()
    print(f"调整前线程数：{original_workers}")
    print(f"当前失败率：{dc.get_failure_rate():.1f}%")
    
    # 执行调整
    new_workers = dc.adjust_workers(verbose=True)
    print(f"调整后线程数：{new_workers}")
    
    # 验证线程数下降
    assert new_workers < original_workers, f"高失败率时线程数应下降：{original_workers} → {new_workers}"
    assert new_workers >= dc.min_workers, f"线程数不应低于最小值：{new_workers} >= {dc.min_workers}"
    
    print("✅ 测试 5 通过：高失败率时线程数下降\n")


def test_memory_high_adjustment():
    """测试 6：模拟内存高负载调节"""
    print("="*80)
    print("测试 6：模拟内存高负载调节")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50,
        memory_high_threshold=80.0
    )
    
    # 模拟内存高负载
    def mock_get_system_load_high_memory():
        return 60.0, 85.0  # CPU 60%, 内存 85%
    
    dc.get_system_load = mock_get_system_load_high_memory
    
    # 调整前
    original_workers = dc.get_workers()
    print(f"调整前线程数：{original_workers}")
    print(f"当前内存使用率：85.0%")
    
    # 执行调整
    new_workers = dc.adjust_workers(verbose=True)
    print(f"调整后线程数：{new_workers}")
    
    # 验证线程数下降（内存优先级最高）
    assert new_workers < original_workers, f"内存高负载时线程数应下降：{original_workers} → {new_workers}"
    assert new_workers >= dc.min_workers, f"线程数不应低于最小值：{new_workers} >= {dc.min_workers}"
    
    print("✅ 测试 6 通过：内存高负载时线程数下降（优先级最高）\n")


def test_statistics():
    """测试 7：统计信息测试"""
    print("="*80)
    print("测试 7：统计信息测试")
    print("="*80)
    
    dc = DynamicConcurrency(
        base_workers=10,
        min_workers=5,
        max_workers=50
    )
    
    # 记录一些请求
    for i in range(50):
        dc.record_request(success=True)
    for i in range(10):
        dc.record_request(success=False)
    
    # 获取统计信息
    stats = dc.get_statistics()
    
    print(f"统计信息：")
    print(f"  当前线程数：{stats['current_workers']}")
    print(f"  基础线程数：{stats['base_workers']}")
    print(f"  最小/最大线程数：{stats['min_workers']}/{stats['max_workers']}")
    print(f"  CPU 使用率：{stats['cpu_percent']:.1f}%")
    print(f"  内存使用率：{stats['memory_percent']:.1f}%")
    print(f"  失败率：{stats['failure_rate']:.1f}%")
    print(f"  调节次数：{stats['adjustment_count']}")
    print(f"  窗口大小：{stats['window_size']}")
    
    assert stats['current_workers'] == 10, "当前线程数应为 10"
    assert stats['window_size'] == 60, "窗口大小应为 60"
    assert 16.0 <= stats['failure_rate'] <= 17.0, f"失败率应接近 16.67%，实际：{stats['failure_rate']}"
    
    print("✅ 测试 7 通过：统计信息正常\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("动态并发模块 - 全量测试")
    print("="*80 + "\n")
    
    try:
        test_basic_functionality()
        test_failure_rate_recording()
        test_cpu_high_adjustment()
        test_cpu_low_adjustment()
        test_failure_rate_adjustment()
        test_memory_high_adjustment()
        test_statistics()
        
        print("="*80)
        print("✅ 所有测试通过！")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
