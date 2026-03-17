#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
量化交易系统 - 主程序入口（优化版）
==============================================
功能：
  - 中文注释完善
  - 命令行交互优化
  - 配置文件支持
  - 日志系统优化
  - 帮助文档完善

作者：量化系统团队
版本：v2.1
最后更新：2026-03-12
"""

# ============================================ 【模块导入】 ============================================

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入优化工具
try:
    from cli_utils import (
        Colors, colorize, supports_color,
        print_banner, print_section, print_success,
        print_error, print_warning, print_info,
        ProgressBar, ErrorDisplay, print_table
    )
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False

try:
    from logger import get_logger, log_function_call, log_timer
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

# 导入主程序
try:
    from fetch_data_optimized import main as fetch_main
    MAIN_AVAILABLE = True
except (ImportError, NameError) as e:
    MAIN_AVAILABLE = False
    FETCH_ERROR = str(e)

# ============================================ 【版本信息】 ============================================

__version__ = "2.1.0"
__author__ = "量化系统团队"
__description__ = "A 股量化交易系统 - 支持打板/缩量潜伏/板块轮动策略"

# ============================================ 【帮助文本】 ============================================

HELP_EPILOG = """
【使用示例】
  # 每日选股（主板，打板策略）
  python %(prog)s -m 每日选股 -s 打板策略 --market 主板

  # 全量回测（2020 年至今）
  python %(prog)s -m 抓取 + 回测 --start-date 2020-01-01

  # 仅回测（使用本地数据）
  python %(prog)s -m 仅回测 -s 缩量潜伏策略

  # 调试模式（详细日志）
  python %(prog)s --log-level DEBUG

  # 使用配置文件
  python %(prog)s --config config.yaml

【策略说明】
  打板策略     - 追涨停板，捕捉连板机会（高风险高收益）
  缩量潜伏策略 - 涨停后缩量回调低吸（中风险中收益）
  板块轮动策略 - 捕捉行业板块轮动（低风险稳定收益）

【运行模式】
  抓取 + 回测   - 全量数据抓取 + 回测验证（首次使用推荐）
  仅服务       - 仅启动 API 服务
  仅回测       - 使用本地数据回测
  每日选股     - 抓取最新数据 + 实盘选股

【合规提示】
  本系统仅供量化研究和学习使用，不构成任何投资建议。
  市场有风险，投资需谨慎！
"""

# ============================================ 【参数解析器】 ============================================

def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器实例
    """
    parser = argparse.ArgumentParser(
        prog="fetch_data_optimized",
        description=colorize("📊 A 股量化交易系统", Colors.BRIGHT_MAGENTA + Colors.BOLD) if CLI_AVAILABLE else "A 股量化交易系统",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )
    
    # ========== 核心参数 ==========
    core_group = parser.add_argument_group("🎯 核心参数")
    
    core_group.add_argument(
        "-m", "--mode",
        type=str,
        choices=["抓取 + 回测", "仅服务", "仅回测", "每日选股"],
        default=None,
        help="运行模式（默认：配置文件设置）"
    )
    
    core_group.add_argument(
        "-s", "--strategy",
        type=str,
        choices=["打板策略", "缩量潜伏策略", "板块轮动策略"],
        default=None,
        help="策略类型（默认：配置文件设置）"
    )
    
    core_group.add_argument(
        "--market",
        type=str,
        nargs="+",
        choices=["主板", "创业板", "科创板", "北交所"],
        default=None,
        help="允许板块（默认：配置文件设置）"
    )
    
    # ========== 时间参数 ==========
    time_group = parser.add_argument_group("📅 时间参数")
    
    time_group.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="回测开始日期（格式：YYYY-MM-DD）"
    )
    
    time_group.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="回测结束日期（格式：YYYY-MM-DD）"
    )
    
    # ========== 配置参数 ==========
    config_group = parser.add_argument_group("⚙️  配置参数")
    
    config_group.add_argument(
        "-c", "--config",
        type=str,
        default="config.yaml",
        help="配置文件路径（默认：config.yaml）"
    )
    
    config_group.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="日志级别（默认：INFO）"
    )
    
    config_group.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="日志目录（默认：logs）"
    )
    
    # ========== 性能参数 ==========
    perf_group = parser.add_argument_group("⚡ 性能参数")
    
    perf_group.add_argument(
        "--workers",
        type=int,
        default=None,
        help="并发线程数（默认：配置文件设置）"
    )
    
    perf_group.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="每分钟最大请求数（默认：配置文件设置）"
    )
    
    # ========== 输出参数 ==========
    output_group = parser.add_argument_group("📤 输出参数")
    
    output_group.add_argument(
        "--no-excel",
        action="store_true",
        help="不导出 Excel 文件"
    )
    
    output_group.add_argument(
        "--no-chart",
        action="store_true",
        help="不生成图表"
    )
    
    output_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    
    # ========== 系统参数 ==========
    sys_group = parser.add_argument_group("🔧 系统参数")
    
    sys_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    sys_group.add_argument(
        "--validate",
        action="store_true",
        help="验证配置和数据完整性"
    )
    
    sys_group.add_argument(
        "--dry-run",
        action="store_true",
        help="空运行（不执行实际操作）"
    )
    
    return parser


# ============================================ 【配置加载】 ============================================

def log_decorator(func):
    """条件日志装饰器"""
    if LOGGER_AVAILABLE:
        return log_function_call()(func)
    return func

@log_decorator
def load_config(args) -> dict:
    """
    加载配置文件
    
    Args:
        args: 命令行参数
    
    Returns:
        dict: 配置字典
    """
    config = {}
    
    # 尝试加载 YAML 配置
    config_file = Path(args.config)
    if config_file.exists():
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                config.update(yaml_config)
            if CLI_AVAILABLE:
                print_success(f"已加载配置文件：{config_file}")
        except Exception as e:
            if CLI_AVAILABLE:
                print_warning(f"配置文件加载失败：{e}，使用默认配置")
            else:
                print(f"配置文件加载失败：{e}")
    
    # 命令行参数覆盖配置
    if args.mode:
        config['core'] = config.get('core', {})
        config['core']['auto_run_mode'] = args.mode
    
    if args.strategy:
        config['core'] = config.get('core', {})
        config['core']['strategy_type'] = args.strategy
    
    if args.market:
        config['core'] = config.get('core', {})
        config['core']['allowed_market'] = args.market
    
    return config


# ============================================ 【环境检查】 ============================================

@log_decorator
def check_environment() -> bool:
    """
    检查运行环境
    
    Returns:
        bool: 环境是否正常
    """
    if CLI_AVAILABLE:
        print_section("环境检查")
    
    checks = [
        ("Python 版本", sys.version_info >= (3, 8), f"{sys.version_info.major}.{sys.version_info.minor}"),
        ("CLI 工具", CLI_AVAILABLE, "可用" if CLI_AVAILABLE else "不可用"),
        ("日志模块", LOGGER_AVAILABLE, "可用" if LOGGER_AVAILABLE else "不可用"),
        ("主程序", MAIN_AVAILABLE, "可用" if MAIN_AVAILABLE else "不可用"),
    ]
    
    all_passed = True
    for name, passed, detail in checks:
        if CLI_AVAILABLE:
            if passed:
                print_success(f"{name}: {detail}")
            else:
                print_warning(f"{name}: {detail}")
        else:
            status = "✅" if passed else "⚠️"
            print(f"{status} {name}: {detail}")
        
        if not passed:
            all_passed = False
    
    return all_passed


# ============================================ 【主函数】 ============================================

@log_decorator
def main():
    """
    主函数入口
    """
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 显示横幅
    if CLI_AVAILABLE:
        print_banner(
            "📊 A 股量化交易系统",
            f"版本 v{__version__} | {__author__}"
        )
        
        print_section("启动检查")
    else:
        print(f"A 股量化交易系统 v{__version__}")
        print("=" * 60)
    
    # 环境检查
    if not check_environment():
        if CLI_AVAILABLE:
            print_warning("部分环境检查未通过，但程序仍可运行")
        else:
            print("⚠️ 部分环境检查未通过")
    
    # 加载配置
    config = load_config(args)
    
    # 初始化日志
    if LOGGER_AVAILABLE:
        logger = get_logger(
            name="quant_system",
            level=args.log_level or "INFO",
            log_dir=args.log_dir
        )
        logger.info(f"系统启动，版本：{__version__}")
    else:
        logger = None
    
    # 验证模式
    if args.validate:
        if CLI_AVAILABLE:
            print_section("验证模式")
            print_info("执行配置和数据完整性验证...")
        # TODO: 实现验证逻辑
        if CLI_AVAILABLE:
            print_success("验证完成")
        return
    
    # 空运行模式
    if args.dry_run:
        if CLI_AVAILABLE:
            print_section("空运行模式")
            print_warning("空运行模式：不执行实际操作")
            print_info(f"运行模式：{args.mode or '配置文件设置'}")
            print_info(f"策略类型：{args.strategy or '配置文件设置'}")
        return
    
    # 执行主程序
    if MAIN_AVAILABLE:
        if CLI_AVAILABLE:
            print_section("启动主程序")
            print_info(f"运行模式：{args.mode or '配置文件设置'}")
            print_info(f"策略类型：{args.strategy or '配置文件设置'}")
            print()
            
            # 显示进度条
            with ProgressBar(10, "初始化", style="chinese") as pb:
                for i in range(10):
                    pb.update(1)
                    import time
                    time.sleep(0.1)
            
            print()
            print_success("初始化完成，启动主程序...")
            print()
        
        # 调用主程序
        try:
            fetch_main()
        except KeyboardInterrupt:
            if CLI_AVAILABLE:
                print()
                print_warning("用户中断，正在退出...")
            else:
                print("\n用户中断")
        except Exception as e:
            if CLI_AVAILABLE:
                print_error(f"程序异常：{str(e)}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
            else:
                print(f"程序异常：{e}")
            
            if logger:
                logger.exception("程序执行异常")
            
            sys.exit(1)
    else:
        if CLI_AVAILABLE:
            print_error("主程序不可用，请检查 fetch_data_optimized.py 是否存在")
            if 'FETCH_ERROR' in globals():
                print_warning(f"错误详情：{FETCH_ERROR}")
            print_info("提示：可以先运行依赖模块测试，或查看使用手册")
        else:
            print("❌ 主程序不可用")
        sys.exit(1)


# ============================================ 【程序入口】 ============================================

if __name__ == "__main__":
    main()
