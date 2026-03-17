#!/usr/bin/env python3
"""
子智能体汇报验证工具
用途：验证子智能体汇报是否符合要求（5 要素检查）
"""

import sys
import json

REQUIRED_FIELDS = [
    "问题现象",
    "原因分析", 
    "修复尝试",
    "验证结果",
    "结论建议"
]

def validate_report(report_text):
    """验证汇报是否包含所有必需字段"""
    
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in report_text:
            missing.append(field)
    
    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "message": generate_message(missing)
    }

def generate_message(missing):
    """生成验证结果消息"""
    if not missing:
        return "✅ 汇报格式验证通过"
    
    return f"❌ 汇报缺少：{', '.join(missing)}\n\n请补充后重新汇报，必须包含：\n" + "\n".join(f"- {f}" for f in REQUIRED_FIELDS)

def main():
    if len(sys.argv) < 2:
        print("用法：validate-report.py <汇报文本或文件路径>")
        sys.exit(1)
    
    # 读取汇报内容
    arg = sys.argv[1]
    if arg.startswith('/'):
        # 文件路径
        with open(arg, 'r') as f:
            report = f.read()
    else:
        # 直接传入文本
        report = arg
    
    # 验证
    result = validate_report(report)
    
    print("=" * 60)
    print("📋 汇报验证结果")
    print("=" * 60)
    print(result["message"])
    
    if not result["valid"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
