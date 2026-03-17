#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
量化交易系统 - 命令行交互优化模块
==============================================
功能：
  - 彩色终端输出
  - 美化进度条
  - 友好的错误提示
  - 中文日志支持

作者：量化系统团队
版本：v1.0
"""

import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# ============================================ 【彩色输出配置】 ============================================

class Colors:
    """
    终端颜色代码类
    用于在支持 ANSI 的终端中显示彩色文本
    """
    # 基础颜色
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    
    # 前景色（文字颜色）
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # 高亮前景色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # 背景色
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # RGB 颜色（需要终端支持）
    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """返回 RGB 颜色代码"""
        return f"\033[38;2;{r};{g};{b}m"
    
    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        """返回 RGB 背景色代码"""
        return f"\033[48;2;{r};{g};{b}m"


def supports_color() -> bool:
    """
    检测当前终端是否支持彩色输出
    
    Returns:
        bool: 是否支持彩色
    """
    # 检查环境变量
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    
    # 检查是否为 TTY
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    
    # 检查平台
    if sys.platform == "win32":
        # Windows 10+ 支持 ANSI
        try:
            from ctypes import windll
            kernel32 = windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    
    return True


# 全局颜色支持标志
COLOR_ENABLED = supports_color()


def colorize(text: str, color: str) -> str:
    """
    为文本添加颜色
    
    Args:
        text: 要着色的文本
        color: 颜色代码（来自 Colors 类）
    
    Returns:
        str: 着色后的文本
    """
    if not COLOR_ENABLED:
        return text
    return f"{color}{text}{Colors.RESET}"


# ============================================ 【便捷输出函数】 ============================================

def print_success(text: str, bold: bool = False) -> None:
    """打印成功消息（绿色）"""
    prefix = "✅ " if COLOR_ENABLED else ""
    style = Colors.BOLD if bold else ""
    print(colorize(f"{prefix}{text}", Colors.GREEN + style))


def print_error(text: str, bold: bool = True) -> None:
    """打印错误消息（红色）"""
    prefix = "❌ " if COLOR_ENABLED else ""
    style = Colors.BOLD if bold else ""
    print(colorize(f"{prefix}{text}", Colors.RED + style), file=sys.stderr)


def print_warning(text: str, bold: bool = False) -> None:
    """打印警告消息（黄色）"""
    prefix = "⚠️  " if COLOR_ENABLED else ""
    style = Colors.BOLD if bold else ""
    print(colorize(f"{prefix}{text}", Colors.YELLOW + style))


def print_info(text: str, bold: bool = False) -> None:
    """打印信息消息（蓝色）"""
    prefix = "ℹ️  " if COLOR_ENABLED else ""
    style = Colors.BOLD if bold else ""
    print(colorize(f"{prefix}{text}", Colors.BLUE + style))


def print_debug(text: str) -> None:
    """打印调试消息（青色）"""
    prefix = "🔍 " if COLOR_ENABLED else ""
    print(colorize(f"{prefix}{text}", Colors.CYAN))


def print_step(step_num: int, total_steps: int, text: str) -> None:
    """
    打印步骤信息（带序号）
    
    Args:
        step_num: 当前步骤号
        total_steps: 总步骤数
        text: 步骤描述
    """
    step_str = colorize(f"[{step_num}/{total_steps}]", Colors.BRIGHT_CYAN)
    print(f"{step_str} {text}")


def print_section(title: str, char: str = "=") -> None:
    """
    打印分节标题
    
    Args:
        title: 标题文本
        char: 分隔符字符
    """
    width = 60
    border = char * width
    padding = (width - len(title) - 4) // 2
    
    print()
    print(colorize(border, Colors.BRIGHT_CYAN))
    print(colorize(f"{char * padding} {title} {char * padding}", Colors.BRIGHT_CYAN))
    print(colorize(border, Colors.BRIGHT_CYAN))
    print()


def print_banner(title: str, subtitle: Optional[str] = None) -> None:
    """
    打印程序横幅
    
    Args:
        title: 主标题
        subtitle: 副标题（可选）
    """
    width = 70
    border = "═" * width
    
    print()
    print(colorize(f"╔{border}╗", Colors.BRIGHT_MAGENTA))
    print(colorize(f"║{title.center(width)}║", Colors.BRIGHT_MAGENTA + Colors.BOLD))
    if subtitle:
        print(colorize(f"║{subtitle.center(width)}║", Colors.MAGENTA))
    print(colorize(f"╚{border}╝", Colors.BRIGHT_MAGENTA))
    print()


# ============================================ 【进度条美化】 ============================================

class ProgressBar:
    """
    美化进度条类
    支持多种样式和自定义配置
    """
    
    # 进度条样式模板
    STYLES = {
        "default": {
            "complete": "█",
            "incomplete": "░",
            "arrow": "▶",
        },
        "thin": {
            "complete": "━",
            "incomplete": "─",
            "arrow": "►",
        },
        "blocks": {
            "complete": "▓",
            "incomplete": "░",
            "arrow": "→",
        },
        "dots": {
            "complete": "●",
            "incomplete": "○",
            "arrow": "●",
        },
        "chinese": {
            "complete": "■",
            "incomplete": "□",
            "arrow": "►",
        }
    }
    
    def __init__(
        self,
        total: int,
        description: str = "进度",
        width: int = 40,
        style: str = "default",
        show_percentage: bool = True,
        show_eta: bool = True,
        color: str = Colors.GREEN
    ):
        """
        初始化进度条
        
        Args:
            total: 总任务数
            description: 进度描述
            width: 进度条宽度（字符数）
            style: 进度条样式（default/thin/blocks/dots/chinese）
            show_percentage: 是否显示百分比
            show_eta: 是否显示预计剩余时间
            color: 进度条颜色
        """
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.style = self.STYLES.get(style, self.STYLES["default"])
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.color = color
        self.start_time = datetime.now()
        self._last_print_len = 0
    
    def update(self, n: int = 1) -> None:
        """
        更新进度
        
        Args:
            n: 完成的数量增量
        """
        self.current += n
        self._render()
    
    def set(self, value: int) -> None:
        """
        设置当前进度值
        
        Args:
            value: 当前进度值
        """
        self.current = min(value, self.total)
        self._render()
    
    def finish(self) -> None:
        """完成进度条"""
        self.current = self.total
        self._render()
        print()  # 换行
    
    def _calculate_eta(self) -> str:
        """计算预计剩余时间"""
        if self.current == 0:
            return "--:--"
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0
        
        if rate > 0:
            remaining = (self.total - self.current) / rate
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return "--:--"
    
    def _render(self) -> None:
        """渲染进度条"""
        # 计算进度
        percentage = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percentage)
        remaining = self.width - filled
        
        # 构建进度条
        bar = (
            self.style["complete"] * filled +
            self.style["arrow"] +
            self.style["incomplete"] * (remaining - 1)
        ) if remaining > 0 else self.style["complete"] * self.width
        
        # 添加颜色
        if COLOR_ENABLED:
            bar = f"{self.color}{bar}{Colors.RESET}"
        
        # 构建输出文本
        parts = [f"\r{self.description}: "]
        parts.append(f"[{bar}]")
        
        if self.show_percentage:
            pct_str = f"{percentage * 100:5.1f}%"
            if COLOR_ENABLED:
                pct_str = colorize(pct_str, Colors.BRIGHT_YELLOW)
            parts.append(f" {pct_str}")
        
        if self.show_eta:
            eta_str = f"ETA: {self._calculate_eta()}"
            if COLOR_ENABLED:
                eta_str = colorize(eta_str, Colors.CYAN)
            parts.append(f" | {eta_str}")
        
        # 显示当前/总数
        count_str = f"({self.current}/{self.total})"
        if COLOR_ENABLED:
            count_str = colorize(count_str, Colors.WHITE)
        parts.append(f" {count_str}")
        
        # 输出并清除旧内容
        output = "".join(parts)
        padding = " " * max(0, self._last_print_len - len(output))
        print(output + padding, end="", flush=True)
        self._last_print_len = len(output)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.current < self.total:
            self.finish()


# ============================================ 【错误提示优化】 ============================================

class ErrorDisplay:
    """
    友好的错误提示显示类
    """
    
    ERROR_TEMPLATES = {
        "network": {
            "icon": "🌐",
            "title": "网络连接错误",
            "suggestion": "请检查网络连接或 API 服务状态",
        },
        "permission": {
            "icon": "🔒",
            "title": "权限错误",
            "suggestion": "请检查文件权限或管理员权限",
        },
        "config": {
            "icon": "⚙️",
            "title": "配置错误",
            "suggestion": "请检查配置文件格式和参数",
        },
        "data": {
            "icon": "📊",
            "title": "数据错误",
            "suggestion": "请检查数据源或数据格式",
        },
        "system": {
            "icon": "💻",
            "title": "系统错误",
            "suggestion": "请查看日志文件或联系技术支持",
        }
    }
    
    @classmethod
    def show(
        cls,
        message: str,
        error_type: str = "system",
        details: Optional[str] = None,
        exit_code: int = 1
    ) -> None:
        """
        显示友好的错误提示
        
        Args:
            message: 错误消息
            error_type: 错误类型（network/permission/config/data/system）
            details: 详细错误信息（可选）
            exit_code: 退出码
        """
        template = cls.ERROR_TEMPLATES.get(error_type, cls.ERROR_TEMPLATES["system"])
        
        print()
        print_section("错误提示", "─")
        
        # 显示错误图标和标题
        icon = template["icon"] if COLOR_ENABLED else "[ERROR]"
        title = colorize(f"{icon} {template['title']}", Colors.BRIGHT_RED + Colors.BOLD)
        print(title)
        print()
        
        # 显示错误消息
        print(colorize(f"问题描述：{message}", Colors.RED))
        
        # 显示详细信息
        if details:
            print()
            print(colorize("详细信息：", Colors.YELLOW))
            print(colorize(f"  {details}", Colors.DIM))
        
        # 显示建议
        print()
        suggestion = colorize(f"💡 建议：{template['suggestion']}", Colors.BRIGHT_YELLOW)
        print(suggestion)
        
        print()
        print_section("", "─")
        print()
        
        if exit_code > 0:
            sys.exit(exit_code)
    
    @classmethod
    def show_exception(
        cls,
        exception: Exception,
        error_type: str = "system",
        show_traceback: bool = False
    ) -> None:
        """
        显示异常错误
        
        Args:
            exception: 异常对象
            error_type: 错误类型
            show_traceback: 是否显示堆栈跟踪
        """
        import traceback
        
        message = str(exception)
        details = None
        
        if show_traceback:
            details = traceback.format_exc()
        
        cls.show(message, error_type, details)


# ============================================ 【表格输出】 ============================================

def print_table(
    headers: List[str],
    rows: List[List[Any]],
    col_widths: Optional[List[int]] = None,
    alignment: str = "left"
) -> None:
    """
    打印格式化表格
    
    Args:
        headers: 表头列表
        rows: 数据行列表
        col_widths: 列宽列表（可选，自动计算）
        alignment: 对齐方式（left/center/right）
    """
    if not rows:
        print_info("无数据")
        return
    
    # 计算列宽
    if col_widths is None:
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(str(header))
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width + 2)
    
    # 对齐函数
    def align_text(text: str, width: int, align: str) -> str:
        text = str(text)
        if align == "left":
            return text.ljust(width)
        elif align == "center":
            return text.center(width)
        elif align == "right":
            return text.rjust(width)
        return text.ljust(width)
    
    # 打印表格
    separator = "+" + "+".join("-" * w for w in col_widths) + "+"
    
    if COLOR_ENABLED:
        separator = colorize(separator, Colors.CYAN)
    
    print(separator)
    
    # 表头
    header_row = "|" + "|".join(
        align_text(h, w, alignment) for h, w in zip(headers, col_widths)
    ) + "|"
    if COLOR_ENABLED:
        header_row = colorize(header_row, Colors.BRIGHT_CYAN + Colors.BOLD)
    print(header_row)
    
    print(separator)
    
    # 数据行
    for i, row in enumerate(rows):
        row_str = "|" + "|".join(
            align_text(row[j] if j < len(row) else "", w, alignment)
            for j, w in enumerate(col_widths)
        ) + "|"
        
        # 偶数行添加背景色（如果支持）
        if COLOR_ENABLED and i % 2 == 0:
            print(row_str)
        else:
            print(row_str)
    
    print(separator)


# ============================================ 【测试入口】 ============================================

if __name__ == "__main__":
    # 测试彩色输出
    print_banner("量化交易系统", "命令行交互优化模块 v1.0")
    
    print_section("功能测试")
    
    print_success("这是一个成功消息")
    print_error("这是一个错误消息")
    print_warning("这是一个警告消息")
    print_info("这是一个信息消息")
    print_debug("这是一个调试消息")
    
    print()
    print_step(1, 3, "第一步：初始化系统")
    print_step(2, 3, "第二步：加载配置")
    print_step(3, 3, "第三步：启动服务")
    
    print()
    print_section("进度条测试")
    
    with ProgressBar(100, "测试进度", style="chinese") as pb:
        for i in range(100):
            pb.update(1)
            import time
            time.sleep(0.02)
    
    print()
    print_section("表格输出测试")
    
    headers = ["股票代码", "股票名称", "评分", "状态"]
    rows = [
        ["000001", "平安银行", 18.5, "✅ 通过"],
        ["000002", "万科 A", 16.2, "✅ 通过"],
        ["600000", "浦发银行", 14.8, "⚠️  观察"],
        ["600036", "招商银行", 19.1, "✅ 通过"],
    ]
    
    print_table(headers, rows)
    
    print()
    print_success("所有测试完成！")
    print()
