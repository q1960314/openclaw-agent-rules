#!/usr/bin/env python3
"""
分级验证判断脚本
根据任务类型自动判断验证级别
"""

import sys
import json

# 验证级别定义
VALIDATION_LEVELS = {
    'complete': {
        'name': '完整验证（6 重）',
        'levels': ['L1', 'L2', 'L3', 'L4', 'L5', 'L6'],
        'cost': '600-800 次调用',
        'applicable': [
            '策略修改', '参数优化', '代码核心逻辑',
            '新因子添加', '回测引擎修改', '数据抓取逻辑修改'
        ]
    },
    'simplified': {
        'name': '简化验证（L1-L3）',
        'levels': ['L1', 'L2', 'L3'],
        'cost': '0 次调用（Python 脚本）',
        'applicable': [
            '文档更新', '注释完善', '依赖更新',
            '配置文件修改（非策略参数）', 'README 更新'
        ]
    },
    'quick': {
        'name': '快速验证（L1-L2）',
        'levels': ['L1', 'L2'],
        'cost': '0 次调用（Python 脚本）',
        'applicable': [
            '小 Bug 修复（不影响逻辑）', '格式调整',
            '拼写错误修复', '日志优化'
        ]
    }
}

def determine_validation_level(task_type, task_description):
    """
    根据任务类型和描述判断验证级别
    """
    task_keywords = {
        'complete': ['策略', '参数', '核心逻辑', '因子', '回测', '数据抓取'],
        'simplified': ['文档', '注释', '依赖', '配置', 'README'],
        'quick': ['Bug 修复', '格式', '拼写', '日志']
    }
    
    # 检查任务类型
    for level, keywords in task_keywords.items():
        if any(keyword in task_type or keyword in task_description for keyword in keywords):
            return level
    
    # 默认使用完整验证（保守策略）
    return 'complete'

def main():
    if len(sys.argv) < 3:
        print("用法：python validate_level.py <任务类型> <任务描述>")
        sys.exit(1)
    
    task_type = sys.argv[1]
    task_description = sys.argv[2]
    
    level = determine_validation_level(task_type, task_description)
    result = VALIDATION_LEVELS[level]
    
    output = {
        'task_type': task_type,
        'task_description': task_description,
        'validation_level': level,
        'level_name': result['name'],
        'levels': result['levels'],
        'cost': result['cost'],
        'applicable': result['applicable']
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
