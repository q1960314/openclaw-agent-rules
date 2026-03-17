#!/usr/bin/env python3
"""修复语法错误"""

import re

TARGET_FILE = "/home/admin/.openclaw/agents/master/fetch_data_optimized.py"

with open(TARGET_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 broken 的 try-except 块
old_pattern = """try:
    import pyarrow as pa
    import pyarrow.parquet as pq

# 【新增】AkShare 降级支持
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  缺少 akshare 依赖，降级功能将不可用，请运行：pip install akshare")

    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False"""

new_pattern = """# 【优化 3】数据压缩相关导入
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("⚠️  缺少 pyarrow 依赖，Parquet 压缩功能将不可用，请运行：pip install pyarrow")

# 【新增】AkShare 降级支持
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  缺少 akshare 依赖，降级功能将不可用，请运行：pip install akshare")"""

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 语法错误已修复")
else:
    print("❌ 未找到需要修复的模式")
    # 尝试查找问题位置
    if 'PARQUET_AVAILABLE = True' in content and 'except ImportError:' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines[235:255], start=235):
            print(f"{i}: {line}")
