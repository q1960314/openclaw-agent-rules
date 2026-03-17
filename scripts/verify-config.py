#!/usr/bin/env python3
import sys
"""
配置验证工具
用途：验证 master agent 配置是否正确
"""

import json

def verify_config():
    with open('/home/admin/.openclaw/agents/master/.openclaw/config.json', 'r') as f:
        config = json.load(f)
    
    print("=" * 60)
    print("🔍 Master Agent 配置验证")
    print("=" * 60)
    
    checks = []
    
    # 检查 enforcement 配置
    if 'enforcement' in config:
        checks.append(("✅ enforcement 配置", True))
        enf = config['enforcement']
        if 'reportValidation' in enf:
            checks.append(("  ✅ 汇报验证", True))
        if 'midTaskCheck' in enf:
            checks.append(("  ✅ 中途检查", True))
        if 'fixedLabels' in enf:
            checks.append(("  ✅ 固定 label", True))
    else:
        checks.append(("❌ enforcement 配置", False))
    
    # 检查 subagents 配置
    if 'subagents' in config:
        checks.append(("✅ subagents 配置", True))
        agents = config['subagents'].get('allow', [])
        checks.append((f"  ✅ 允许 {len(agents)} 个子智能体", True))
    else:
        checks.append(("❌ subagents 配置", False))
    
    # 输出结果
    print("\n验证结果：")
    for item, status in checks:
        print(item)
    
    print()
    all_passed = all(s for _, s in checks)
    if all_passed:
        print("✅ 所有配置验证通过")
    else:
        print("❌ 部分配置缺失，请检查")
    
    return all_passed

if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)
