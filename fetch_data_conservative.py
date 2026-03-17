#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据抓取脚本 - 保守配置版（防多进程冲突）
版本：v1.0 (紧急恢复版)
创建时间：2026-03-12

核心改进：
1. 进程锁机制 - 确保只有一个进程运行
2. 保守并发 - 10 线程（原 35 线程）
3. 严格限流 - 2000 次/分钟（原 4000 次）
4. 频繁保存 - 每 20 只股票保存一次
5. 定期验证 - 每 100 只股票验证数据完整性
"""

import os
import sys
import fcntl
import time
import json
import signal
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ============================================== 【进程锁机制 - 防止多进程冲突】 ==============================================
class ProcessLock:
    """进程锁 - 确保只有一个实例运行"""
    
    def __init__(self, lock_file_path='/tmp/fetch_data.lock'):
        self.lock_file_path = lock_file_path
        self.lock_file = None
        self.locked = False
    
    def acquire(self):
        """获取锁"""
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            # LOCK_EX = 排他锁，LOCK_NB = 非阻塞（获取不到立即返回）
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 写入当前进程 PID
            self.lock_file.write(f"{os.getpid()}\n")
            self.lock_file.write(f"{datetime.now().isoformat()}\n")
            self.lock_file.flush()
            self.locked = True
            return True
        except (IOError, OSError) as e:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False
    
    def release(self):
        """释放锁"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                # 删除锁文件
                if os.path.exists(self.lock_file_path):
                    os.remove(self.lock_file_path)
            except Exception as e:
                logging.error(f"释放锁失败：{e}")
            finally:
                self.lock_file = None
                self.locked = False
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("无法获取进程锁 - 可能已有其他实例在运行")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

# ============================================== 【全局配置 - 保守策略】 ==============================================
# 核心运行参数（保守配置）
CONSERVATIVE_CONFIG = {
    'max_workers': 10,              # 并发线程数：10（原 35）
    'max_requests_per_minute': 2000, # 限流：2000 次/分钟（原 4000，留 2000 缓冲）
    'save_frequency': 20,           # 每 20 只股票保存一次
    'verify_frequency': 100,        # 每 100 只股票验证一次
    'retry_times': 3,               # 失败重试次数
    'timeout_per_request': 30,      # 单个请求超时（秒）
}

# 数据抓取优先级
FETCH_PRIORITY = {
    'P0_daily': {'name': '日线行情', 'api': 'daily', 'batch': True, 'priority': 0},
    'P0_daily_basic': {'name': '日线指标', 'api': 'daily_basic', 'batch': True, 'priority': 0},
    'P1_finance': {'name': '财务数据', 'api': 'finance', 'batch': False, 'priority': 1},
    'P2_money_flow': {'name': '资金流向', 'api': 'moneyflow', 'batch': False, 'priority': 2},
    'P3_limit_list': {'name': '龙虎榜/涨跌停', 'api': 'limit_list', 'batch': False, 'priority': 3},
}

# 工作目录
WORK_DIR = Path('/home/admin/.openclaw/agents/master')
DATA_DIR = WORK_DIR / 'data_all_stocks'
LOG_DIR = WORK_DIR / 'logs'
CHECKPOINT_DIR = WORK_DIR / 'checkpoints'

# 确保目录存在
for dir_path in [DATA_DIR, LOG_DIR, CHECKPOINT_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============================================== 【日志配置】 ==============================================
def setup_logging():
    """配置日志"""
    log_file = LOG_DIR / f'fetch_conservative_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================== 【进度跟踪器】 ==============================================
class ProgressTracker:
    """进度跟踪器 - 实时监控抓取进度"""
    
    def __init__(self, total_stocks: int):
        self.total_stocks = total_stocks
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.lock = Lock()
        self.start_time = time.time()
        self.checkpoints = []
    
    def update(self, success: bool = True):
        """更新进度"""
        with self.lock:
            self.processed += 1
            if success:
                self.success += 1
            else:
                self.failed += 1
    
    def get_progress(self):
        """获取进度信息"""
        with self.lock:
            elapsed = time.time() - self.start_time
            rate = self.processed / elapsed if elapsed > 0 else 0
            eta = (self.total_stocks - self.processed) / rate if rate > 0 else 0
            
            return {
                'total': self.total_stocks,
                'processed': self.processed,
                'success': self.success,
                'failed': self.failed,
                'progress_pct': (self.processed / self.total_stocks) * 100,
                'rate_per_min': rate * 60,
                'elapsed_min': elapsed / 60,
                'eta_min': eta / 60,
            }
    
    def save_checkpoint(self, data: dict):
        """保存检查点"""
        with self.lock:
            checkpoint_file = CHECKPOINT_DIR / f'checkpoint_{self.processed}.json'
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'progress': self.get_progress(),
                    'data_summary': data
                }, f, ensure_ascii=False, indent=2)
            self.checkpoints.append(str(checkpoint_file))
            logger.info(f"✅ 检查点已保存：{checkpoint_file}")

# ============================================== 【数据验证器】 ==============================================
class DataValidator:
    """数据完整性验证器"""
    
    @staticmethod
    def validate_daily_data(stock_code: str, data: dict) -> tuple[bool, str]:
        """验证日线数据完整性"""
        if not data:
            return False, "数据为空"
        
        required_fields = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return False, f"缺少字段：{missing}"
        
        # 验证数值合理性
        if data['high'] < data['low']:
            return False, "最高价 < 最低价"
        
        if data['close'] <= 0:
            return False, "收盘价 <= 0"
        
        return True, "验证通过"
    
    @staticmethod
    def validate_data_consistency(stock_code: str, data_dir: Path) -> tuple[bool, str]:
        """验证数据一致性"""
        try:
            # 检查文件是否存在
            data_file = data_dir / f'{stock_code}.json'
            if not data_file.exists():
                return False, f"数据文件不存在：{data_file}"
            
            # 读取并验证
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, "数据格式错误"
            
            if 'daily' not in data:
                return False, "缺少日线数据"
            
            daily_data = data['daily']
            if not isinstance(daily_data, list) or len(daily_data) == 0:
                return False, "日线数据为空"
            
            return True, "验证通过"
        
        except Exception as e:
            return False, f"验证异常：{e}"

# ============================================== 【限流器 - 令牌桶算法】 ==============================================
class RateLimiter:
    """令牌桶限流器"""
    
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self.last_update = time.time()
        self.lock = Lock()
    
    def acquire(self):
        """获取令牌（等待直到有可用令牌）"""
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                # 补充令牌
                self.tokens = min(
                    self.max_requests,
                    self.tokens + elapsed * (self.max_requests / 60.0)
                )
                self.last_update = now
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            
            # 没有令牌，等待
            time.sleep(0.1)

# ============================================== 【数据抓取器】 ==============================================
class ConservativeDataFetcher:
    """保守配置数据抓取器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.rate_limiter = RateLimiter(config['max_requests_per_minute'])
        self.progress = None
        self.validator = DataValidator()
        self.save_lock = Lock()
        
        # 股票列表（示例，实际应从接口获取）
        self.stock_list = self._load_stock_list()
    
    def _load_stock_list(self) -> list:
        """加载股票列表"""
        # 这里简化处理，实际应从 Tushare/Akshare 获取
        logger.info("正在加载股票列表...")
        # 模拟股票列表（实际应替换为真实接口）
        stock_list = []
        for i in range(100):  # 示例：100 只股票
            stock_list.append(f'{600000 + i:06d}.SH' if i < 50 else f'{000000 + i:06d}.SZ')
        logger.info(f"✅ 加载 {len(stock_list)} 只股票")
        return stock_list
    
    def fetch_stock_data(self, stock_code: str) -> dict:
        """抓取单只股票数据（带限流）"""
        try:
            # 限流
            self.rate_limiter.acquire()
            
            # 模拟数据抓取（实际应替换为真实 API 调用）
            data = {
                'stock_code': stock_code,
                'fetch_time': datetime.now().isoformat(),
                'daily': [],  # 日线数据
                'daily_basic': [],  # 日线指标
                'finance': {},  # 财务数据
                'moneyflow': [],  # 资金流向
            }
            
            # 模拟 API 延迟
            time.sleep(0.5)
            
            return {'success': True, 'data': data, 'error': None}
        
        except Exception as e:
            logger.error(f"❌ {stock_code} 抓取失败：{e}")
            return {'success': False, 'data': None, 'error': str(e)}
    
    def save_stock_data(self, stock_code: str, data: dict):
        """保存股票数据"""
        try:
            with self.save_lock:
                data_file = DATA_DIR / f'{stock_code}.json'
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ {stock_code} 保存失败：{e}")
    
    def fetch_all(self):
        """执行全量抓取（保守策略）"""
        total = len(self.stock_list)
        self.progress = ProgressTracker(total)
        
        logger.info("="*80)
        logger.info("🚀 开始保守策略数据抓取")
        logger.info(f"配置：线程数={self.config['max_workers']}, 限流={self.config['max_requests_per_minute']}次/分钟")
        logger.info(f"保存频率：每{self.config['save_frequency']}只股票 | 验证频率：每{self.config['verify_frequency']}只股票")
        logger.info("="*80)
        
        # 使用线程池并发抓取
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = {executor.submit(self.fetch_stock_data, stock): stock 
                      for stock in self.stock_list}
            
            for future in as_completed(futures):
                stock_code = futures[future]
                try:
                    result = future.result()
                    
                    if result['success']:
                        # 保存数据
                        self.save_stock_data(stock_code, result['data'])
                        self.progress.update(success=True)
                    else:
                        self.progress.update(success=False)
                        logger.warning(f"⚠️  {stock_code} 抓取失败：{result['error']}")
                    
                    # 定期保存检查点
                    if self.progress.processed % self.config['save_frequency'] == 0:
                        self.progress.save_checkpoint({'last_stock': stock_code})
                    
                    # 定期验证数据
                    if self.progress.processed % self.config['verify_frequency'] == 0:
                        valid, msg = self.validator.validate_data_consistency(stock_code, DATA_DIR)
                        if valid:
                            logger.info(f"✅ 数据验证通过（已处理 {self.progress.processed}/{total}）")
                        else:
                            logger.error(f"❌ 数据验证失败：{msg}")
                    
                    # 实时进度
                    if self.progress.processed % 10 == 0:
                        prog = self.progress.get_progress()
                        logger.info(
                            f"进度：{prog['progress_pct']:.1f}% | "
                            f"成功={prog['success']} | 失败={prog['failed']} | "
                            f"速率={prog['rate_per_min']:.1f}次/分钟 | "
                            f"预计剩余={prog['eta_min']:.1f}分钟"
                        )
                
                except Exception as e:
                    logger.error(f"❌ {stock_code} 处理异常：{e}")
                    self.progress.update(success=False)
        
        # 最终报告
        final_progress = self.progress.get_progress()
        logger.info("="*80)
        logger.info("🎉 数据抓取完成！")
        logger.info(f"总计：{final_progress['total']} 只股票")
        logger.info(f"成功：{final_progress['success']} | 失败：{final_progress['failed']}")
        logger.info(f"成功率：{final_progress['progress_pct']:.1f}%")
        logger.info(f"总耗时：{final_progress['elapsed_min']:.1f} 分钟")
        logger.info(f"平均速率：{final_progress['rate_per_min']:.1f} 次/分钟")
        logger.info("="*80)
        
        return final_progress

# ============================================== 【主程序入口】 ==============================================
def main():
    """主程序入口"""
    print("="*80)
    print("  📊 数据抓取系统 - 保守配置版（防多进程冲突）")
    print("="*80)
    
    # 1. 获取进程锁
    logger.info("🔒 正在获取进程锁...")
    process_lock = ProcessLock()
    
    try:
        with process_lock:
            logger.info("✅ 进程锁获取成功 - 开始执行抓取")
            
            # 2. 创建抓取器并执行
            fetcher = ConservativeDataFetcher(CONSERVATIVE_CONFIG)
            result = fetcher.fetch_all()
            
            # 3. 发送完成通知
            logger.info("✅ 所有任务完成！")
            
    except RuntimeError as e:
        logger.error(f"❌ {e}")
        logger.error("请检查是否已有其他抓取进程在运行")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("🛑 程序被用户手动终止")
        process_lock.release()
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ 程序异常：{e}", exc_info=True)
        process_lock.release()
        sys.exit(1)

if __name__ == '__main__':
    main()
