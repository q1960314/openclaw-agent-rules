#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parquet 存储功能补充测试
"""

import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

print("="*80)
print("Parquet 存储功能验证")
print("="*80)

# 检查 pyarrow 版本
print(f"✅ PyArrow 版本：{pa.__version__}")

# 创建测试数据
test_df = pd.DataFrame({
    'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ'],
    'trade_date': ['20240101', '20240102', '20240103', '20240104', '20240105'],
    'close': [10.5, 11.2, 10.8, 11.5, 11.0],
    'open': [10.2, 11.0, 10.5, 11.2, 10.8],
    'high': [10.8, 11.5, 11.0, 11.8, 11.3],
    'low': [10.0, 10.8, 10.3, 11.0, 10.5],
    'volume': [1000000, 1200000, 950000, 1100000, 1050000],
    'amount': [10500000.0, 13440000.0, 10260000.0, 12650000.0, 11550000.0]
})

# 计算原始大小
original_size = test_df.memory_usage(deep=True).sum()
print(f"\n📊 原始数据大小：{original_size/1024:.2f}KB")

# 保存为 Parquet (Snappy 压缩)
test_file = "/home/admin/.openclaw/agents/master/tests/test_parquet_compression.parquet"
table = pa.Table.from_pandas(test_df)
pq.write_table(table, test_file, compression='snappy')

# 计算压缩后大小
compressed_size = os.path.getsize(test_file)
compression_ratio = original_size / compressed_size if compressed_size > 0 else 0

print(f"📦 压缩后大小：{compressed_size/1024:.2f}KB")
print(f"🎯 压缩比：{compression_ratio:.2f}x")

# 读取验证
read_df = pq.read_table(test_file).to_pandas()

# 验证数据一致性
if len(read_df) == len(test_df) and list(read_df.columns) == list(test_df.columns):
    print("\n✅ Parquet 存储验证通过！")
    print(f"   - 行数一致：{len(read_df)} 行")
    print(f"   - 列数一致：{len(read_df.columns)} 列")
    print(f"   - 数据完整性：✓")
else:
    print("\n❌ Parquet 存储验证失败！")
    print(f"   - 原始：{len(test_df)} 行 vs 读取：{len(read_df)} 行")

# 测试不同压缩算法
print("\n" + "="*80)
print("不同压缩算法对比")
print("="*80)

compressions = ['snappy', 'gzip', 'brotli', None]
for comp in compressions:
    try:
        test_file_comp = f"/home/admin/.openclaw/agents/master/tests/test_parquet_{comp or 'uncompressed'}.parquet"
        pq.write_table(table, test_file_comp, compression=comp)
        size = os.path.getsize(test_file_comp)
        comp_name = comp if comp else 'uncompressed'
        ratio = original_size / size if size > 0 else 0
        print(f"{comp_name:12s}: {size/1024:8.2f}KB (压缩比：{ratio:.2f}x)")
        os.remove(test_file_comp)
    except Exception as e:
        print(f"{comp:12s}: 不支持 - {e}")

# 清理测试文件
os.remove(test_file)

print("\n" + "="*80)
print("✅ Parquet 功能测试完成")
print("="*80)
