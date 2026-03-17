#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程锁测试脚本
验证进程锁机制是否正常工作

测试场景：
1. 启动第一个进程，获取锁
2. 启动第二个进程，应该无法获取锁
3. 第一个进程退出后，锁自动释放
4. 第三个进程可以正常获取锁
"""

import os
import sys
import time
import subprocess
import tempfile

# 导入进程锁模块
from process_lock import ProcessLock

def test_process_lock():
    """测试进程锁功能"""
    lock_file = '/tmp/test_fetch_data.lock'
    
    # 清理旧的锁文件
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    print("="*80)
    print("进程锁功能测试")
    print("="*80)
    
    # 测试 1：第一个进程获取锁
    print("\n【测试 1】第一个进程尝试获取锁...")
    lock1 = ProcessLock(lock_file=lock_file)
    result1 = lock1.acquire()
    if result1:
        print("✅ 第一个进程成功获取锁")
    else:
        print("❌ 第一个进程获取锁失败（异常）")
        return False
    
    # 测试 2：第二个进程尝试获取锁（应该失败）
    print("\n【测试 2】第二个进程尝试获取锁（应该失败）...")
    lock2 = ProcessLock(lock_file=lock_file)
    result2 = lock2.acquire()
    if not result2:
        print("✅ 第二个进程正确被阻止（无法获取锁）")
    else:
        print("❌ 第二个进程也获取了锁（进程锁失效！）")
        lock2.release()
        lock1.release()
        return False
    
    # 测试 3：第一个进程释放锁
    print("\n【测试 3】第一个进程释放锁...")
    lock1.release()
    print("✅ 第一个进程已释放锁")
    
    # 测试 4：第三个进程现在可以获取锁
    print("\n【测试 4】第三个进程尝试获取锁（应该成功）...")
    lock3 = ProcessLock(lock_file=lock_file)
    result3 = lock3.acquire()
    if result3:
        print("✅ 第三个进程成功获取锁")
        lock3.release()
    else:
        print("❌ 第三个进程获取锁失败（异常）")
        return False
    
    # 清理
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    print("\n" + "="*80)
    print("✅ 所有测试通过！进程锁机制工作正常")
    print("="*80)
    return True

def test_concurrent_processes():
    """测试并发进程场景"""
    lock_file = '/tmp/test_concurrent.lock'
    
    # 清理旧的锁文件
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    print("\n" + "="*80)
    print("并发进程测试")
    print("="*80)
    
    # 创建测试脚本
    test_script = f'''
import sys
import time
sys.path.insert(0, '/home/admin/.openclaw/agents/master')
from process_lock import ProcessLock

lock = ProcessLock(lock_file='{lock_file}')
if lock.acquire():
    print("PROCESS_OK")
    time.sleep(5)  # 持有锁 5 秒
    lock.release()
else:
    print("PROCESS_BLOCKED")
'''
    
    script_path = '/tmp/test_lock_script.py'
    with open(script_path, 'w') as f:
        f.write(test_script)
    
    # 启动第一个进程
    print("\n【并发测试】启动第一个进程...")
    proc1 = subprocess.Popen(
        ['python3', script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 等待第一个进程获取锁
    time.sleep(1)
    
    # 启动第二个进程
    print("【并发测试】启动第二个进程...")
    proc2 = subprocess.Popen(
        ['python3', script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 等待两个进程完成
    out1, _ = proc1.communicate()
    out2, _ = proc2.communicate()
    
    print(f"\n第一个进程输出：{out1.strip()}")
    print(f"第二个进程输出：{out2.strip()}")
    
    # 清理
    if os.path.exists(script_path):
        os.remove(script_path)
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    # 验证结果
    if "PROCESS_OK" in out1 and "PROCESS_BLOCKED" in out2:
        print("\n✅ 并发测试通过！第二个进程被正确阻止")
        return True
    else:
        print("\n❌ 并发测试失败")
        return False

if __name__ == '__main__':
    success = True
    
    # 运行基本测试
    if not test_process_lock():
        success = False
    
    # 运行并发测试
    if not test_concurrent_processes():
        success = False
    
    if success:
        print("\n" + "="*80)
        print("🎉 所有测试通过！进程锁机制已就绪")
        print("="*80)
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ 部分测试失败")
        print("="*80)
        sys.exit(1)
