#!/usr/bin/env python3
# ==============================================
# 【优化】一键切换运行模式工具 - switch_mode.py
# ==============================================
# 功能：命令行工具，一键切换 AUTO_RUN_MODE 配置并重启程序
# 支持模式：全量/增量/每日选股
# 用法：python scripts/switch_mode.py --mode 全量
# ==============================================

import argparse
import sys
import os
import re
import subprocess
from pathlib import Path

# ============================================== 【配置区 - 【优化】标记】 ==============================================
# 【优化】配置参数（保持原值不变）
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_ROOT / "modules" / "config_manager.py"
MAIN_FILE = PROJECT_ROOT / "main_modular.py"

# 【优化】模式映射表
MODE_MAP = {
    "全量": "抓取 + 回测",
    "增量": "抓取 + 回测",  # 增量模式也使用抓取 + 回测，但会通过其他配置控制
    "每日选股": "每日选股",
    "仅服务": "仅服务",
    "仅回测": "仅回测"
}

# 【优化】有效模式列表
VALID_MODES = list(MODE_MAP.keys())

# ============================================== 【工具函数 - 【优化】标记】 ==============================================

def print_banner():
    """【优化】打印横幅"""
    print("=" * 60)
    print("【优化】量化系统 - 一键切换运行模式工具")
    print("=" * 60)

def get_current_mode():
    """【优化】获取当前运行模式"""
    if not CONFIG_FILE.exists():
        print(f"❌ 配置文件不存在：{CONFIG_FILE}")
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 【优化】查找 AUTO_RUN_MODE 配置行
        match = re.search(r'AUTO_RUN_MODE\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
        else:
            print("❌ 未在配置文件中找到 AUTO_RUN_MODE")
            return None
    except Exception as e:
        print(f"❌ 读取配置文件失败：{e}")
        return None

def update_mode(new_mode):
    """【优化】更新运行模式配置"""
    if not CONFIG_FILE.exists():
        print(f"❌ 配置文件不存在：{CONFIG_FILE}")
        return False
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 【优化】替换 AUTO_RUN_MODE 配置行（保持原有格式）
        old_pattern = r'(AUTO_RUN_MODE\s*=\s*)"[^"]+"'
        new_line = r'\1"' + new_mode + '"'
        
        new_content = re.sub(old_pattern, new_line, content)
        
        if new_content == content:
            print("❌ 配置文件无需更新（模式已相同）")
            return False
        
        # 【优化】写回配置文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 配置文件已更新：{CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"❌ 更新配置文件失败：{e}")
        return False

def restart_program():
    """【优化】重启主程序"""
    if not MAIN_FILE.exists():
        print(f"❌ 主程序文件不存在：{MAIN_FILE}")
        return False
    
    try:
        print("🔄 正在重启主程序...")
        # 【优化】使用 subprocess 启动主程序
        process = subprocess.Popen(
            [sys.executable, str(MAIN_FILE)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✅ 主程序已启动（PID: {process.pid}）")
        return True
    except Exception as e:
        print(f"❌ 重启主程序失败：{e}")
        return False

# ============================================== 【主函数 - 【优化】标记】 ==============================================

def main():
    """【优化】主函数"""
    print_banner()
    
    # 【优化】解析命令行参数
    parser = argparse.ArgumentParser(
        description="【优化】一键切换量化系统运行模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
【优化】可用模式：
  全量      - 抓取 + 回测模式（全量数据）
  增量      - 抓取 + 回测模式（增量数据）
  每日选股  - 每日选股模式
  仅服务    - 仅启动 API 服务
  仅回测    - 仅执行回测

【优化】使用示例：
  python scripts/switch_mode.py --mode 全量
  python scripts/switch_mode.py --mode 每日选股
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=VALID_MODES,
        help='【优化】目标运行模式（全量/增量/每日选股/仅服务/仅回测）'
    )
    
    parser.add_argument(
        '--no-restart',
        action='store_true',
        help='【优化】仅修改配置，不重启程序'
    )
    
    args = parser.parse_args()
    
    # 【优化】获取当前模式
    current_mode = get_current_mode()
    if current_mode is None:
        sys.exit(1)
    
    print(f"📊 当前运行模式：{current_mode}")
    print(f"🎯 目标运行模式：{args.mode}")
    
    # 【优化】检查是否需要切换
    if current_mode == args.mode:
        print("⚠️  当前模式与目标模式相同，无需切换")
        if not args.no_restart:
            restart = input("是否仍要重启主程序？(y/n): ")
            if restart.lower() == 'y':
                restart_program()
        sys.exit(0)
    
    # 【优化】映射模式名称
    mapped_mode = MODE_MAP[args.mode]
    print(f"📝 配置值将更新为：{mapped_mode}")
    
    # 【优化】确认操作
    confirm = input("\n⚠️  确认切换运行模式？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 操作已取消")
        sys.exit(0)
    
    # 【优化】更新配置
    if not update_mode(mapped_mode):
        sys.exit(1)
    
    # 【优化】重启程序
    if not args.no_restart:
        print("\n" + "=" * 60)
        if not restart_program():
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ 模式切换完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
