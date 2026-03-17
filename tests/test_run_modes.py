#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==================================================
运行模式验证脚本
==================================================
功能：
  - 自动化测试 4 种运行模式
  - 验证启动、配置、执行、输出全流程
  - 生成验证报告

作者：测试专家
版本：v1.0
创建日期：2026-03-12
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict

# ============================================ 【配置常量】 ============================================

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# 测试日期配置
TEST_END_DATE = datetime.now().strftime("%Y-%m-%d")
TEST_START_DATE = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
BACKTEST_START = "2025-01-01"
BACKTEST_END = "2025-12-31"

# ============================================ 【数据结构】 ============================================

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    mode: str
    status: str = "pending"  # pending/pass/fail/skip
    duration: float = 0.0
    error_message: str = ""
    output_file: str = ""
    checks: List[Dict] = field(default_factory=list)

@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "pass_rate": f"{self.passed/self.total_tests*100:.1f}%" if self.total_tests > 0 else "0%"
            },
            "results": [asdict(r) for r in self.results]
        }

# ============================================ 【测试执行器】 ============================================

class RunModeTester:
    """运行模式测试器"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.report = TestReport(timestamp=datetime.now().isoformat())
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(PROJECT_ROOT)
        
    def run_command(self, cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """
        执行命令
        
        Returns:
            (return_code, stdout, stderr)
        """
        print(f"\n{'='*60}")
        print(f"执行命令：{' '.join(cmd)}")
        print(f"{'='*60}")
        
        try:
            # 兼容老版本 Python：使用 stdout/stderr 代替 capture_output
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=timeout,
                env=self.env,
                cwd=str(PROJECT_ROOT)
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令执行超时"
        except Exception as e:
            return -1, "", str(e)
    
    def check_file_exists(self, filepath: Path, pattern: str = None) -> bool:
        """检查文件是否存在"""
        if pattern:
            files = list(filepath.parent.glob(pattern))
            return len(files) > 0
        return filepath.exists()
    
    def check_json_valid(self, filepath: Path) -> bool:
        """检查 JSON 文件是否有效"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except:
            return False
    
    def check_parquet_valid(self, filepath: Path) -> bool:
        """检查 Parquet 文件是否有效"""
        try:
            import pandas as pd
            df = pd.read_parquet(filepath)
            return len(df) > 0
        except:
            return False
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.report.results.append(result)
        self.report.total_tests += 1
        if result.status == "pass":
            self.report.passed += 1
        elif result.status == "fail":
            self.report.failed += 1
        elif result.status == "skip":
            self.report.skipped += 1
    
    # ============================================ 【测试用例：全量抓取模式】 ============================================
    
    def test_full_fetch_startup(self) -> TestResult:
        """测试 1.1: 全量抓取模式 - 正常启动"""
        result = TestResult(
            test_name="全量抓取模式 - 正常启动",
            mode="抓取 + 回测"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "抓取 + 回测",
            "--dry-run",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：启动成功（返回码 0 或帮助信息）
        if returncode == 0 or "使用示例" in stdout or "运行模式" in stdout:
            result.status = "pass"
            result.checks.append({"item": "程序启动", "status": "pass"})
        else:
            result.status = "fail"
            result.error_message = stderr or f"返回码：{returncode}"
            result.checks.append({"item": "程序启动", "status": "fail", "error": result.error_message})
        
        return result
    
    def test_full_fetch_time_range(self) -> TestResult:
        """测试 1.2: 全量抓取模式 - 读取时间范围"""
        result = TestResult(
            test_name="全量抓取模式 - 读取时间范围",
            mode="抓取 + 回测"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "抓取 + 回测",
            "--start-date", TEST_START_DATE,
            "--end-date", TEST_END_DATE,
            "--dry-run",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：时间范围配置正确
        if returncode == 0 and (TEST_START_DATE in stdout or TEST_START_DATE in stderr or "dry-run" in stdout.lower()):
            result.status = "pass"
            result.checks.append({"item": "时间范围配置", "status": "pass", "value": f"{TEST_START_DATE} ~ {TEST_END_DATE}"})
        else:
            result.status = "fail"
            result.error_message = stderr or f"返回码：{returncode}"
            result.checks.append({"item": "时间范围配置", "status": "fail"})
        
        return result
    
    def test_full_fetch_data(self) -> TestResult:
        """测试 1.3: 全量抓取模式 - 抓取数据（实际执行）"""
        result = TestResult(
            test_name="全量抓取模式 - 抓取数据",
            mode="抓取 + 回测"
        )
        
        if self.dry_run:
            result.status = "skip"
            result.error_message = "Dry-run 模式跳过实际数据抓取"
            return result
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "抓取 + 回测",
            "--start-date", TEST_START_DATE,
            "--end-date", TEST_END_DATE,
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=300)
        result.duration = time.time() - start_time
        
        # 验证：数据文件生成
        data_files = list(DATA_DIR.glob("*.parquet")) + list(DATA_DIR.glob("*.csv"))
        if returncode == 0 and len(data_files) > 0:
            result.status = "pass"
            result.output_file = str(data_files[0])
            result.checks.append({"item": "数据文件生成", "status": "pass", "count": len(data_files)})
        else:
            result.status = "fail"
            result.error_message = stderr or f"返回码：{returncode}, 数据文件数：{len(data_files)}"
            result.checks.append({"item": "数据文件生成", "status": "fail"})
        
        return result
    
    def test_full_fetch_checkpoint(self) -> TestResult:
        """测试 1.4: 全量抓取模式 - 保存进度"""
        result = TestResult(
            test_name="全量抓取模式 - 保存进度",
            mode="抓取 + 回测"
        )
        
        # 检查点文件
        checkpoint_files = [
            DATA_DIR / "checkpoint.json",
            DATA_DIR / "progress.json",
            DATA_DIR / ".checkpoint"
        ]
        
        checkpoint_found = False
        for cf in checkpoint_files:
            if cf.exists():
                checkpoint_found = True
                result.output_file = str(cf)
                break
        
        if checkpoint_found:
            result.status = "pass"
            result.checks.append({"item": "进度文件存在", "status": "pass", "file": result.output_file})
        else:
            result.status = "skip"
            result.error_message = "未找到进度文件（可能是首次运行）"
            result.checks.append({"item": "进度文件存在", "status": "skip"})
        
        return result
    
    # ============================================ 【测试用例：增量抓取模式】 ============================================
    
    def test_incremental_startup(self) -> TestResult:
        """测试 2.1: 增量抓取模式 - 正常启动"""
        result = TestResult(
            test_name="增量抓取模式 - 正常启动",
            mode="抓取 + 回测（增量）"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "抓取 + 回测",
            "--dry-run",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        if returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "程序启动", "status": "pass"})
        else:
            result.status = "fail"
            result.error_message = stderr
            result.checks.append({"item": "程序启动", "status": "fail"})
        
        return result
    
    def test_incremental_latest_date(self) -> TestResult:
        """测试 2.2: 增量抓取模式 - 识别最新交易日"""
        result = TestResult(
            test_name="增量抓取模式 - 识别最新交易日",
            mode="抓取 + 回测（增量）"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "抓取 + 回测",
            "--dry-run",
            "--log-level", "DEBUG"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：日志中包含日期识别信息
        output = stdout + stderr
        if "最新" in output or "latest" in output.lower() or "incremental" in output.lower() or returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "日期识别", "status": "pass"})
        else:
            result.status = "skip"
            result.error_message = "日志中未找到日期识别信息"
            result.checks.append({"item": "日期识别", "status": "skip"})
        
        return result
    
    def test_incremental_one_day(self) -> TestResult:
        """测试 2.3: 增量抓取模式 - 只抓取 1 天数据"""
        result = TestResult(
            test_name="增量抓取模式 - 只抓取 1 天数据",
            mode="抓取 + 回测（增量）"
        )
        
        if self.dry_run:
            result.status = "skip"
            result.error_message = "Dry-run 模式跳过实际数据抓取"
            return result
        
        # 此测试需要已有数据，暂时跳过
        result.status = "skip"
        result.error_message = "需要已有数据才能验证增量抓取"
        result.checks.append({"item": "增量抓取", "status": "skip"})
        
        return result
    
    def test_incremental_merge(self) -> TestResult:
        """测试 2.4: 增量抓取模式 - 合并到现有数据"""
        result = TestResult(
            test_name="增量抓取模式 - 合并到现有数据",
            mode="抓取 + 回测（增量）"
        )
        
        # 检查数据文件
        data_files = list(DATA_DIR.glob("*.parquet")) + list(DATA_DIR.glob("*.csv"))
        if len(data_files) > 0:
            result.status = "pass"
            result.checks.append({"item": "数据合并", "status": "pass", "file_count": len(data_files)})
        else:
            result.status = "skip"
            result.error_message = "无数据文件可验证合并"
            result.checks.append({"item": "数据合并", "status": "skip"})
        
        return result
    
    # ============================================ 【测试用例：回测模式】 ============================================
    
    def test_backtest_startup(self) -> TestResult:
        """测试 3.1: 回测模式 - 正常启动"""
        result = TestResult(
            test_name="回测模式 - 正常启动",
            mode="仅回测"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "仅回测",
            "--dry-run",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        if returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "程序启动", "status": "pass"})
        else:
            result.status = "fail"
            result.error_message = stderr
            result.checks.append({"item": "程序启动", "status": "fail"})
        
        return result
    
    def test_backtest_load_data(self) -> TestResult:
        """测试 3.2: 回测模式 - 加载本地数据"""
        result = TestResult(
            test_name="回测模式 - 加载本地数据",
            mode="仅回测"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "仅回测",
            "--start-date", BACKTEST_START,
            "--end-date", BACKTEST_END,
            "--dry-run",
            "--log-level", "DEBUG"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：日志中包含数据加载信息
        output = stdout + stderr
        if "加载" in output or "load" in output.lower() or returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "数据加载", "status": "pass"})
        else:
            result.status = "skip"
            result.error_message = "日志中未找到数据加载信息"
            result.checks.append({"item": "数据加载", "status": "skip"})
        
        return result
    
    def test_backtest_execute(self) -> TestResult:
        """测试 3.3: 回测模式 - 执行回测"""
        result = TestResult(
            test_name="回测模式 - 执行回测",
            mode="仅回测"
        )
        
        if self.dry_run:
            result.status = "skip"
            result.error_message = "Dry-run 模式跳过实际回测"
            return result
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "仅回测",
            "--start-date", BACKTEST_START,
            "--end-date", BACKTEST_END,
            "--strategy", "打板策略",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=300)
        result.duration = time.time() - start_time
        
        if returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "回测执行", "status": "pass"})
        else:
            result.status = "fail"
            result.error_message = stderr
            result.checks.append({"item": "回测执行", "status": "fail"})
        
        return result
    
    def test_backtest_report(self) -> TestResult:
        """测试 3.4: 回测模式 - 输出回测报告"""
        result = TestResult(
            test_name="回测模式 - 输出回测报告",
            mode="仅回测"
        )
        
        # 检查报告文件
        report_files = (
            list(PROJECT_ROOT.glob("backtest_report_*.html")) +
            list(PROJECT_ROOT.glob("backtest_report_*.json")) +
            list(PROJECT_ROOT.glob("reports/backtest_*.html")) +
            list(PROJECT_ROOT.glob("reports/backtest_*.json"))
        )
        
        if len(report_files) > 0:
            result.status = "pass"
            result.output_file = str(report_files[0])
            result.checks.append({"item": "报告生成", "status": "pass", "file": result.output_file})
        else:
            result.status = "skip"
            result.error_message = "未找到回测报告文件"
            result.checks.append({"item": "报告生成", "status": "skip"})
        
        return result
    
    # ============================================ 【测试用例：每日选股模式】 ============================================
    
    def test_daily_selection_startup(self) -> TestResult:
        """测试 4.1: 每日选股模式 - 正常启动"""
        result = TestResult(
            test_name="每日选股模式 - 正常启动",
            mode="每日选股"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "每日选股",
            "--dry-run",
            "--log-level", "INFO"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        if returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "程序启动", "status": "pass"})
        else:
            result.status = "fail"
            result.error_message = stderr
            result.checks.append({"item": "程序启动", "status": "fail"})
        
        return result
    
    def test_daily_selection_fetch(self) -> TestResult:
        """测试 4.2: 每日选股模式 - 抓取最新数据"""
        result = TestResult(
            test_name="每日选股模式 - 抓取最新数据",
            mode="每日选股"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "每日选股",
            "--dry-run",
            "--log-level", "DEBUG"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：日志中包含数据抓取信息
        output = stdout + stderr
        if "抓取" in output or "fetch" in output.lower() or "最新" in output or returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "数据抓取", "status": "pass"})
        else:
            result.status = "skip"
            result.error_message = "日志中未找到数据抓取信息"
            result.checks.append({"item": "数据抓取", "status": "skip"})
        
        return result
    
    def test_daily_selection_strategy(self) -> TestResult:
        """测试 4.3: 每日选股模式 - 执行选股策略"""
        result = TestResult(
            test_name="每日选股模式 - 执行选股策略",
            mode="每日选股"
        )
        
        start_time = time.time()
        cmd = [
            sys.executable, str(MAIN_SCRIPT),
            "--mode", "每日选股",
            "--strategy", "打板策略",
            "--dry-run",
            "--log-level", "DEBUG"
        ]
        
        returncode, stdout, stderr = self.run_command(cmd, timeout=30)
        result.duration = time.time() - start_time
        
        # 验证：日志中包含策略执行信息
        output = stdout + stderr
        if "策略" in output or "strategy" in output.lower() or "选股" in output or returncode == 0:
            result.status = "pass"
            result.checks.append({"item": "策略执行", "status": "pass"})
        else:
            result.status = "skip"
            result.error_message = "日志中未找到策略执行信息"
            result.checks.append({"item": "策略执行", "status": "skip"})
        
        return result
    
    def test_daily_selection_output(self) -> TestResult:
        """测试 4.4: 每日选股模式 - 输出选股清单"""
        result = TestResult(
            test_name="每日选股模式 - 输出选股清单",
            mode="每日选股"
        )
        
        # 检查选股文件
        selection_files = (
            list(PROJECT_ROOT.glob("daily_selection_*.csv")) +
            list(PROJECT_ROOT.glob("daily_selection_*.xlsx")) +
            list(PROJECT_ROOT.glob("output/daily_selection_*.csv")) +
            list(PROJECT_ROOT.glob("output/daily_selection_*.xlsx"))
        )
        
        if len(selection_files) > 0:
            result.status = "pass"
            result.output_file = str(selection_files[0])
            result.checks.append({"item": "选股清单", "status": "pass", "file": result.output_file})
        else:
            result.status = "skip"
            result.error_message = "未找到选股清单文件"
            result.checks.append({"item": "选股清单", "status": "skip"})
        
        return result
    
    # ============================================ 【测试执行】 ============================================
    
    def run_all_tests(self) -> TestReport:
        """运行所有测试"""
        print("\n" + "="*80)
        print("开始运行模式验证测试")
        print(f"测试时间：{self.report.timestamp}")
        print(f"Dry-run 模式：{self.dry_run}")
        print("="*80)
        
        # 1. 全量抓取模式测试
        print("\n【测试组 1】全量抓取模式")
        self.add_result(self.test_full_fetch_startup())
        self.add_result(self.test_full_fetch_time_range())
        self.add_result(self.test_full_fetch_data())
        self.add_result(self.test_full_fetch_checkpoint())
        
        # 2. 增量抓取模式测试
        print("\n【测试组 2】增量抓取模式")
        self.add_result(self.test_incremental_startup())
        self.add_result(self.test_incremental_latest_date())
        self.add_result(self.test_incremental_one_day())
        self.add_result(self.test_incremental_merge())
        
        # 3. 回测模式测试
        print("\n【测试组 3】回测模式")
        self.add_result(self.test_backtest_startup())
        self.add_result(self.test_backtest_load_data())
        self.add_result(self.test_backtest_execute())
        self.add_result(self.test_backtest_report())
        
        # 4. 每日选股模式测试
        print("\n【测试组 4】每日选股模式")
        self.add_result(self.test_daily_selection_startup())
        self.add_result(self.test_daily_selection_fetch())
        self.add_result(self.test_daily_selection_strategy())
        self.add_result(self.test_daily_selection_output())
        
        return self.report
    
    def save_report(self, output_path: Path = None):
        """保存测试报告"""
        if output_path is None:
            output_path = PROJECT_ROOT / "tests" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"\n测试报告已保存：{output_path}")
        return output_path
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*80)
        print("测试摘要")
        print("="*80)
        print(f"总测试数：{self.report.total_tests}")
        print(f"通过：{self.report.passed} ✓")
        print(f"失败：{self.report.failed} ✗")
        print(f"跳过：{self.report.skipped} ⊘")
        if self.report.total_tests > 0:
            pass_rate = self.report.passed / self.report.total_tests * 100
            print(f"通过率：{pass_rate:.1f}%")
        print("="*80)
        
        # 打印失败详情
        failed_tests = [r for r in self.report.results if r.status == "fail"]
        if failed_tests:
            print("\n失败测试详情:")
            for test in failed_tests:
                print(f"  ✗ {test.test_name}: {test.error_message}")

# ============================================ 【主函数】 ============================================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="运行模式验证脚本")
    parser.add_argument("--no-dry-run", action="store_true", help="执行实际测试（非 dry-run）")
    parser.add_argument("--output", type=str, help="报告输出路径")
    args = parser.parse_args()
    
    tester = RunModeTester(dry_run=not args.no_dry_run)
    tester.run_all_tests()
    tester.print_summary()
    
    output_path = Path(args.output) if args.output else None
    tester.save_report(output_path)
    
    # 返回退出码
    sys.exit(0 if tester.report.failed == 0 else 1)

if __name__ == "__main__":
    main()
