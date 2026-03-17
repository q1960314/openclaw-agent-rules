#!/usr/bin/env python3
"""
失败处理流程脚本
处理 P0/P1/P2 失败
"""

import sys
import json
from datetime import datetime

# 失败级别定义
FAILURE_LEVELS = {
    'P0': {
        'name': '致命错误',
        'examples': ['系统崩溃', '数据丢失', '安全漏洞'],
        'action': '立即停止，Master 介入，用户通知',
        'priority': '最高'
    },
    'P1': {
        'name': '严重错误',
        'examples': ['验证不通过', 'Bug', '性能问题'],
        'action': '打回重做，记录原因，3 次失败更换 Agent',
        'priority': '高'
    },
    'P2': {
        'name': '轻微错误',
        'examples': ['文档不全', '注释少', '格式问题'],
        'action': '记录问题，限期修复',
        'priority': '中'
    }
}

def handle_failure(failure_id, agent_name, failure_level, failure_description):
    """
    处理失败
    """
    if failure_level not in FAILURE_LEVELS:
        return {'error': 'Invalid failure level'}
    
    level_info = FAILURE_LEVELS[failure_level]
    
    # 生成失败记录
    failure_record = {
        'failure_id': failure_id,
        'agent_name': agent_name,
        'failure_level': failure_level,
        'level_name': level_info['name'],
        'examples': level_info['examples'],
        'action': level_info['action'],
        'priority': level_info['priority'],
        'failure_description': failure_description,
        'timestamp': datetime.now().isoformat(),
        'status': 'open'
    }
    
    # 根据级别执行不同处理
    if failure_level == 'P0':
        # P0 失败：立即停止所有任务
        failure_record['actions'] = [
            '立即停止所有任务',
            'Master 介入',
            '根因分析',
            '用户通知',
            '修复验证',
            '知识库归档'
        ]
    elif failure_level == 'P1':
        # P1 失败：打回重做
        failure_record['actions'] = [
            '打回重做',
            '记录原因',
            '跟踪失败次数（3 次更换 Agent）',
            '根因分析',
            '修复验证',
            '知识库归档'
        ]
    elif failure_level == 'P2':
        # P2 失败：记录问题
        failure_record['actions'] = [
            '记录问题',
            '限期修复（24 小时内）',
            '验证关闭',
            '知识库归档'
        ]
    
    return failure_record

def main():
    if len(sys.argv) < 4:
        print("用法：python failure_handler.py <失败 ID> <Agent 名称> <失败级别> [失败描述]")
        sys.exit(1)
    
    failure_id = sys.argv[1]
    agent_name = sys.argv[2]
    failure_level = sys.argv[3]
    failure_description = sys.argv[4] if len(sys.argv) > 4 else ''
    
    result = handle_failure(failure_id, agent_name, failure_level, failure_description)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
