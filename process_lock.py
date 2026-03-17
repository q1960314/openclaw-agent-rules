#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程锁模块 - 独立文件版本
确保同一时间只有一个抓取进程运行
使用文件锁机制，进程退出后锁自动释放
"""

import os
import fcntl
from datetime import datetime

class ProcessLock:
    """
    进程锁类，确保同一时间只有一个抓取进程运行
    使用文件锁机制，进程退出后锁自动释放
    """
    def __init__(self, lock_file='/tmp/fetch_data.lock', logger=None):
        self.lock_file = lock_file
        self.lock_fd = None
        self.logger = logger
    
    def _log(self, level, message):
        """统一的日志方法"""
        if self.logger:
            getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def acquire(self):
        """
        获取排他锁（非阻塞）
        :return: True 表示获取成功，False 表示已有其他进程在运行
        """
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 写入 PID 和时间戳
            self.lock_fd.write(f"{os.getpid()}\n{datetime.now()}\n")
            self.lock_fd.flush()
            self._log('info', f"✅ 进程锁已获取 (PID: {os.getpid()})")
            return True
        except BlockingIOError:
            pid = self._read_lock_pid()
            self._log('error', f"❌ 无法获取进程锁，已有其他进程在运行 (PID: {pid})")
            return False
        except Exception as e:
            self._log('error', f"❌ 获取进程锁失败：{e}")
            return False
    
    def release(self):
        """释放锁"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                # 可选：删除锁文件
                if os.path.exists(self.lock_file):
                    try:
                        os.remove(self.lock_file)
                    except:
                        pass
                self._log('info', f"✅ 进程锁已释放 (PID: {os.getpid()})")
            except Exception as e:
                self._log('warning', f"⚠️  释放进程锁异常：{e}")
    
    def _read_lock_pid(self):
        """读取锁文件中的 PID（用于日志）"""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        return lines[0].strip()
        except:
            pass
        return "未知"


# 测试代码
if __name__ == '__main__':
    import time
    
    print("测试进程锁模块...")
    lock = ProcessLock(lock_file='/tmp/test_lock.lock')
    
    if lock.acquire():
        print("成功获取锁，持有 5 秒...")
        time.sleep(5)
        lock.release()
        print("锁已释放")
    else:
        print("无法获取锁，已有其他进程在运行")
