#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================
# 【优化】并发压力测试脚本 - stress_test.py（简化版）
# ==============================================
# 功能：测试不同并发线程数下的数据抓取性能
# 测试指标：成功率、响应时间、限流触发次数
# 测试线程数：2/4/8/12/16/20
# 【优化】无需外部依赖，使用标准库实现
# ==============================================

import os
import sys
import time
import logging
import threading
import statistics
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 【优化】配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(log_dir, 'stress_test.log'),
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("stress_test")


# ==============================================
# 【配置区】- 参数值不变，保持原有架构
# ==============================================
TEST_CONFIG = {
    'thread_counts': [2, 4, 8, 12, 16, 20],  # 【优化】测试的线程数列表
    'requests_per_thread': 50,                # 【优化】每个线程的请求次数
    'test_stock_codes': [                    # 【优化】测试用的股票代码列表（分散请求）
        '000001.SZ', '000002.SZ', '000063.SZ', '000100.SZ', '000157.SZ',
        '000333.SZ', '000538.SZ', '000568.SZ', '000596.SZ', '000625.SZ',
        '000651.SZ', '000661.SZ', '000725.SZ', '000858.SZ', '000895.SZ',
        '002001.SZ', '002007.SZ', '002027.SZ', '002049.SZ', '002050.SZ',
        '600000.SH', '600004.SH', '600007.SH', '600008.SH', '600009.SH',
        '600010.SH', '600011.SH', '600015.SH', '600016.SH', '600018.SH',
        '600019.SH', '600020.SH', '600021.SH', '600022.SH', '600023.SH',
        '600025.SH', '600026.SH', '600027.SH', '600028.SH', '600029.SH',
        '600030.SH', '600031.SH', '600033.SH', '600036.SH', '600038.SH',
        '600039.SH', '600048.SH', '600050.SH', '600053.SH', '600054.SH',
    ],
    'tushare_api_url': 'http://42.194.163.97:5000',  # 【优化】Tushare API 地址
    'tushare_token': 'ca7f3527c06099b904673bcabf3ed7e396376365a90f0cfa4393ad6b2edb',  # 【优化】Tushare Token
    'timeout': 30,  # 【优化】请求超时时间（秒）
    'max_retry': 2,  # 【优化】重试次数
    'max_requests_per_second': 41,  # 【优化】秒级限流（2500/60）
    'max_requests_per_minute': 2500,  # 【优化】分钟级限流
}


class RateLimiter:
    """
    【优化】令牌桶限流器
    职责：实现分钟级 + 秒级双重令牌桶限流
    """
    
    def __init__(self, max_rps: int, max_rpm: int):
        """
        初始化限流器
        :param max_rps: 每秒最大请求数
        :param max_rpm: 每分钟最大请求数
        """
        self.max_rps = max_rps
        self.max_rpm = max_rpm
        
        # 【优化】令牌桶状态
        self.second_tokens = float(max_rps)
        self.minute_tokens = float(max_rpm)
        self.last_second_update = time.time()
        self.last_minute_update = time.time()
        
        # 【优化】统计计数器
        self.second_limit_count = 0
        self.minute_limit_count = 0
        self.total_request_count = 0
        self.total_wait_time = 0.0
        self.max_wait_time = 0.0
        self._lock = Lock()
    
    def acquire(self) -> float:
        """
        【优化】获取令牌，可能需要等待
        :return: 等待时间（秒）
        """
        with self._lock:
            current_time = time.time()
            self.total_request_count += 1
            
            # 【优化】计算时间流逝
            elapsed_second = current_time - self.last_second_update
            elapsed_minute = current_time - self.last_minute_update
            
            # 【优化】补充令牌
            self.second_tokens = min(self.max_rps, self.second_tokens + elapsed_second * self.max_rps)
            self.minute_tokens = min(self.max_rpm, self.minute_tokens + elapsed_minute * (self.max_rpm / 60.0))
            
            self.last_second_update = current_time
            self.last_minute_update = current_time
            
            # 【优化】计算等待时间
            wait_time = 0.0
            
            if self.second_tokens < 1.0:
                second_wait = (1.0 - self.second_tokens) / self.max_rps
                wait_time = max(wait_time, second_wait)
                if second_wait > 0:
                    self.second_limit_count += 1
            
            if self.minute_tokens < 1.0:
                minute_wait = (1.0 - self.minute_tokens) / (self.max_rpm / 60.0)
                wait_time = max(wait_time, minute_wait)
                if minute_wait > 0:
                    self.minute_limit_count += 1
            
            # 【优化】执行等待
            if wait_time > 0:
                time.sleep(wait_time)
                self.total_wait_time += wait_time
                self.max_wait_time = max(self.max_wait_time, wait_time)
                
                # 【优化】等待后补充令牌
                current_time = time.time()
                elapsed = current_time - self.last_second_update
                self.second_tokens = min(self.max_rps, self.second_tokens + elapsed * self.max_rps)
                self.last_second_update = current_time
                
                elapsed = current_time - self.last_minute_update
                self.minute_tokens = min(self.max_rpm, self.minute_tokens + elapsed * (self.max_rpm / 60.0))
                self.last_minute_update = current_time
            
            # 【优化】消耗令牌
            self.second_tokens = max(0.0, self.second_tokens - 1.0)
            self.minute_tokens = max(0.0, self.minute_tokens - 1.0)
            
            return wait_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        【优化】获取统计信息
        :return: 统计字典
        """
        with self._lock:
            total_triggers = self.second_limit_count + self.minute_limit_count
            avg_wait = self.total_wait_time / max(1, total_triggers)
            rate_limit_ratio = total_triggers / max(1, self.total_request_count) * 100
            
            return {
                'total_requests': self.total_request_count,
                'second_limit_triggers': self.second_limit_count,
                'minute_limit_triggers': self.minute_limit_count,
                'total_triggers': total_triggers,
                'rate_limit_ratio': rate_limit_ratio,
                'total_wait_time': self.total_wait_time,
                'avg_wait_time': avg_wait,
                'max_wait_time': self.max_wait_time,
            }
    
    def reset(self):
        """
        【优化】重置统计
        """
        with self._lock:
            self.second_tokens = float(self.max_rps)
            self.minute_tokens = float(self.max_rpm)
            self.last_second_update = time.time()
            self.last_minute_update = time.time()
            self.second_limit_count = 0
            self.minute_limit_count = 0
            self.total_request_count = 0
            self.total_wait_time = 0.0
            self.max_wait_time = 0.0


class StressTester:
    """
    【优化】并发压力测试器
    职责：执行并发测试、收集统计信息、生成报告
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化压力测试器
        :param config: 测试配置
        """
        self.config = config
        self.rate_limiter = RateLimiter(
            config['max_requests_per_second'],
            config['max_requests_per_minute']
        )
    
    def _make_request(self, stock_code: str, request_id: int) -> Dict[str, Any]:
        """
        【优化】发送 HTTP 请求到 Tushare API
        :param stock_code: 股票代码
        :param request_id: 请求 ID
        :return: 请求结果字典
        """
        start_time = time.time()
        success = False
        error_msg = ""
        
        try:
            # 【优化】限流控制
            wait_time = self.rate_limiter.acquire()
            
            # 【优化】构建 Tushare API 请求
            api_params = {
                "api_name": "daily",
                "token": self.config['tushare_token'],
                "params": {
                    "ts_code": stock_code,
                    "start_date": "20250101",
                    "end_date": "20250131"
                }
            }
            
            req_data = json.dumps(api_params).encode('utf-8')
            req = urllib.request.Request(
                self.config['tushare_api_url'],
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # 【优化】发送请求
            with urllib.request.urlopen(req, timeout=self.config['timeout']) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if result.get('code') == 0 and result.get('data'):
                    success = True
                    data_rows = len(result['data'].get('items', []))
                    logger.debug(f"✅ 请求 {request_id} | {stock_code} | 耗时={response_time:.3f}s | 等待={wait_time:.3f}s | 数据行数={data_rows}")
                else:
                    error_msg = result.get('msg', '未知错误')
                    logger.warning(f"⚠️  请求 {request_id} | {stock_code} | 耗时={response_time:.3f}s | 等待={wait_time:.3f}s | {error_msg}")
                
                return {
                    'request_id': request_id,
                    'stock_code': stock_code,
                    'success': success,
                    'response_time': response_time,
                    'wait_time': wait_time,
                    'error_msg': error_msg,
                    'timestamp': datetime.now().isoformat()
                }
        
        except urllib.error.HTTPError as e:
            end_time = time.time()
            response_time = end_time - start_time
            error_msg = f"HTTP 错误：{e.code} {e.reason}"
            logger.error(f"❌ 请求 {request_id} | {stock_code} | 耗时={response_time:.3f}s | {error_msg}")
            
            return {
                'request_id': request_id,
                'stock_code': stock_code,
                'success': False,
                'response_time': response_time,
                'wait_time': 0.0,
                'error_msg': error_msg,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            error_msg = str(e)
            logger.error(f"❌ 请求 {request_id} | {stock_code} | 耗时={response_time:.3f}s | {error_msg}")
            
            return {
                'request_id': request_id,
                'stock_code': stock_code,
                'success': False,
                'response_time': response_time,
                'wait_time': 0.0,
                'error_msg': error_msg,
                'timestamp': datetime.now().isoformat()
            }
    
    def _worker(self, thread_id: int, requests_per_thread: int) -> List[Dict[str, Any]]:
        """
        【优化】工作线程函数
        :param thread_id: 线程 ID
        :param requests_per_thread: 每个线程的请求次数
        :return: 该线程的所有请求结果
        """
        thread_results = []
        stock_codes = self.config['test_stock_codes']
        
        for i in range(requests_per_thread):
            # 【优化】轮询选择股票代码，分散请求
            stock_code = stock_codes[i % len(stock_codes)]
            request_id = thread_id * requests_per_thread + i
            
            result = self._make_request(stock_code, request_id)
            result['thread_id'] = thread_id
            thread_results.append(result)
        
        return thread_results
    
    def run_test(self, thread_count: int) -> Dict[str, Any]:
        """
        【优化】执行单轮测试
        :param thread_count: 线程数
        :return: 测试结果统计
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 开始测试 | 线程数={thread_count} | 总请求数={thread_count * self.config['requests_per_thread']}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        # 【优化】重置限流统计
        self.rate_limiter.reset()
        
        # 【优化】创建线程池
        results = []
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # 【优化】提交任务
            futures = [
                executor.submit(self._worker, thread_id, self.config['requests_per_thread'])
                for thread_id in range(thread_count)
            ]
            
            # 【优化】收集结果
            for future in as_completed(futures):
                try:
                    thread_results = future.result()
                    results.extend(thread_results)
                except Exception as e:
                    logger.error(f"❌ 线程执行失败：{e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 【优化】统计分析
        total_requests = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_requests - success_count
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        response_times = [r['response_time'] for r in results if r['success']]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = statistics.median(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        std_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # 【优化】获取限流统计
        rate_limit_stats = self.rate_limiter.get_stats()
        
        # 【优化】计算吞吐量
        throughput = total_requests / total_time if total_time > 0 else 0
        
        test_result = {
            'thread_count': thread_count,
            'total_requests': total_requests,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_rate,
            'total_time': total_time,
            'throughput': throughput,
            'avg_response_time': avg_response_time,
            'median_response_time': median_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'std_response_time': std_response_time,
            'second_limit_triggers': rate_limit_stats['second_limit_triggers'],
            'minute_limit_triggers': rate_limit_stats['minute_limit_triggers'],
            'total_limit_triggers': rate_limit_stats['total_triggers'],
            'rate_limit_ratio': rate_limit_stats['rate_limit_ratio'],
            'total_wait_time': rate_limit_stats['total_wait_time'],
            'avg_wait_time': rate_limit_stats['avg_wait_time'],
            'max_wait_time': rate_limit_stats['max_wait_time'],
            'timestamp': datetime.now().isoformat()
        }
        
        # 【优化】输出本轮测试结果
        logger.info(f"\n📊 测试结果 | 线程数={thread_count}")
        logger.info(f"  总请求数：{total_requests}")
        logger.info(f"  成功/失败：{success_count}/{failed_count} (成功率={success_rate:.2f}%)")
        logger.info(f"  总耗时：{total_time:.2f}s | 吞吐量={throughput:.2f} req/s")
        logger.info(f"  响应时间：avg={avg_response_time:.3f}s | median={median_response_time:.3f}s | min={min_response_time:.3f}s | max={max_response_time:.3f}s")
        logger.info(f"  限流触发：{rate_limit_stats['total_triggers']} 次 (秒级={rate_limit_stats['second_limit_triggers']} | 分钟级={rate_limit_stats['minute_limit_triggers']})")
        logger.info(f"  限流比例：{rate_limit_stats['rate_limit_ratio']:.2f}%")
        logger.info(f"  等待时间：total={rate_limit_stats['total_wait_time']:.2f}s | avg={rate_limit_stats['avg_wait_time']:.3f}s | max={rate_limit_stats['max_wait_time']:.3f}s")
        
        return test_result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """
        【优化】执行所有测试
        :return: 所有测试结果列表
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 并发压力测试开始")
        logger.info(f"  测试配置：{self.config['thread_counts']} 线程")
        logger.info(f"  每线程请求数：{self.config['requests_per_thread']}")
        logger.info(f"  测试股票代码数：{len(self.config['test_stock_codes'])}")
        logger.info(f"{'='*60}\n")
        
        all_results = []
        
        for thread_count in self.config['thread_counts']:
            try:
                result = self.run_test(thread_count)
                all_results.append(result)
                
                # 【优化】每轮测试之间间隔，避免限流影响
                logger.info(f"\n⏱️  等待 30 秒，准备下一轮测试...")
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ 线程数={thread_count} 测试失败：{e}")
                continue
        
        return all_results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """
        【优化】生成测试报告
        :param results: 测试结果列表
        :return: 测试报告字符串
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("📈 并发压力测试报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"测试配置：")
        report_lines.append(f"  - 测试线程数：{self.config['thread_counts']}")
        report_lines.append(f"  - 每线程请求数：{self.config['requests_per_thread']}")
        report_lines.append(f"  - 测试股票代码数：{len(self.config['test_stock_codes'])}")
        report_lines.append(f"  - 限流配置：{self.config['max_requests_per_second']} req/s, {self.config['max_requests_per_minute']} req/min")
        report_lines.append("")
        
        # 【优化】汇总表格
        report_lines.append("-" * 80)
        report_lines.append("📊 测试结果汇总")
        report_lines.append("-" * 80)
        report_lines.append(
            f"{'线程数':<8} | {'总请求':<8} | {'成功率':<8} | {'吞吐量':<10} | "
            f"{'平均响应':<10} | {'中位响应':<10} | {'限流触发':<10} | {'限流比例':<10}"
        )
        report_lines.append("-" * 80)
        
        for r in results:
            report_lines.append(
                f"{r['thread_count']:<8} | {r['total_requests']:<8} | {r['success_rate']:<8.2f}% | "
                f"{r['throughput']:<10.2f} | {r['avg_response_time']:<10.3f}s | "
                f"{r['median_response_time']:<10.3f}s | {r['total_limit_triggers']:<10} | "
                f"{r['rate_limit_ratio']:<10.2f}%"
            )
        
        report_lines.append("-" * 80)
        report_lines.append("")
        
        # 【优化】详细分析
        report_lines.append("-" * 80)
        report_lines.append("🔍 详细分析")
        report_lines.append("-" * 80)
        
        for r in results:
            report_lines.append(f"\n【线程数={r['thread_count']}】")
            report_lines.append(f"  性能指标：")
            report_lines.append(f"    - 总请求数：{r['total_requests']}")
            report_lines.append(f"    - 成功/失败：{r['success_count']}/{r['failed_count']} (成功率={r['success_rate']:.2f}%)")
            report_lines.append(f"    - 总耗时：{r['total_time']:.2f}s")
            report_lines.append(f"    - 吞吐量：{r['throughput']:.2f} req/s")
            report_lines.append(f"  响应时间：")
            report_lines.append(f"    - 平均：{r['avg_response_time']:.3f}s")
            report_lines.append(f"    - 中位数：{r['median_response_time']:.3f}s")
            report_lines.append(f"    - 最小值：{r['min_response_time']:.3f}s")
            report_lines.append(f"    - 最大值：{r['max_response_time']:.3f}s")
            report_lines.append(f"    - 标准差：{r['std_response_time']:.3f}s")
            report_lines.append(f"  限流统计：")
            report_lines.append(f"    - 秒级限流触发：{r['second_limit_triggers']} 次")
            report_lines.append(f"    - 分钟级限流触发：{r['minute_limit_triggers']} 次")
            report_lines.append(f"    - 总限流触发：{r['total_limit_triggers']} 次")
            report_lines.append(f"    - 限流比例：{r['rate_limit_ratio']:.2f}%")
            report_lines.append(f"  等待时间：")
            report_lines.append(f"    - 累计等待：{r['total_wait_time']:.2f}s")
            report_lines.append(f"    - 平均等待：{r['avg_wait_time']:.3f}s")
            report_lines.append(f"    - 最大等待：{r['max_wait_time']:.3f}s")
        
        report_lines.append("")
        
        # 【优化】结论与建议
        report_lines.append("-" * 80)
        report_lines.append("💡 结论与建议")
        report_lines.append("-" * 80)
        
        if results:
            # 【优化】找到最佳线程数
            best_throughput_result = max(results, key=lambda x: x['throughput'])
            best_success_rate_result = max(results, key=lambda x: x['success_rate'])
            
            report_lines.append(f"\n1. 最佳吞吐量：{best_throughput_result['thread_count']} 线程")
            report_lines.append(f"   - 吞吐量：{best_throughput_result['throughput']:.2f} req/s")
            report_lines.append(f"   - 成功率：{best_throughput_result['success_rate']:.2f}%")
            
            report_lines.append(f"\n2. 最佳成功率：{best_success_rate_result['thread_count']} 线程")
            report_lines.append(f"   - 成功率：{best_success_rate_result['success_rate']:.2f}%")
            report_lines.append(f"   - 吞吐量：{best_success_rate_result['throughput']:.2f} req/s")
            
            # 【优化】分析限流情况
            high_rate_limit_results = [r for r in results if r['rate_limit_ratio'] > 50]
            if high_rate_limit_results:
                report_lines.append(f"\n3. 限流警告：")
                report_lines.append(f"   - 以下线程数限流比例超过 50%：{[r['thread_count'] for r in high_rate_limit_results]}")
                report_lines.append(f"   - 建议降低并发线程数或调整限流参数")
            
            # 【优化】推荐配置
            report_lines.append(f"\n4. 推荐配置：")
            report_lines.append(f"   - 推荐线程数：{best_throughput_result['thread_count']} (基于吞吐量)")
            report_lines.append(f"   - 当前配置：{TEST_CONFIG['max_requests_per_minute']} 次/分钟限流")
            
            report_lines.append(f"\n5. 优化建议：")
            report_lines.append(f"   - 如果限流比例过高 (>50%)，建议降低线程数或增加限流配额")
            report_lines.append(f"   - 如果响应时间标准差过大，检查网络稳定性或 API 服务状态")
            report_lines.append(f"   - 建议在生产环境使用最佳吞吐量线程数，并留 20% 余量")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("测试完成")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    """
    【优化】主函数
    """
    logger.info("🚀 并发压力测试脚本启动")
    
    try:
        # 【优化】创建测试器
        tester = StressTester(TEST_CONFIG)
        
        # 【优化】执行所有测试
        results = tester.run_all_tests()
        
        # 【优化】生成报告
        report = tester.generate_report(results)
        
        # 【优化】输出报告
        print("\n" + report)
        
        # 【优化】保存报告到文件
        report_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✅ 测试报告已保存：{report_file}")
        
        # 【优化】保存结果到 JSON（便于后续分析）
        json_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 测试结果已保存：{json_file}")
        
        logger.info("🎉 并发压力测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
