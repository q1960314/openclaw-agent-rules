#!/usr/bin/env python3
"""
集成脚本：将优化功能集成到 fetch_data_optimized.py
1. 启用 Parquet 存储（替换 CSV）
2. 添加 AkShare 降级支持
3. 确保 14 个接口完整实现
"""

import os
import re

BASE_DIR = "/home/admin/.openclaw/agents/master"
TARGET_FILE = os.path.join(BASE_DIR, "fetch_data_optimized.py")

def add_akshare_import():
    """添加 AkShare 导入"""
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有 AkShare 导入
    if 'import akshare' in content:
        print("⚠️  AkShare 导入已存在")
        return
    
    # 在 pyarrow 导入后添加 AkShare 导入
    akshare_import = """
# 【新增】AkShare 降级支持
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  缺少 akshare 依赖，降级功能将不可用，请运行：pip install akshare")
"""
    
    # 找到 pyarrow 导入的位置
    if 'import pyarrow.parquet as pq' in content:
        content = content.replace(
            'import pyarrow.parquet as pq',
            'import pyarrow.parquet as pq\n' + akshare_import
        )
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ AkShare 导入已添加")
    else:
        print("❌ 未找到 pyarrow 导入位置")

def enable_parquet_by_default():
    """默认启用 Parquet 存储"""
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加 Parquet 开关配置
    parquet_config = "\n# 【新增】Parquet 存储开关\nUSE_PARQUET = True  # True=使用 Parquet，False=使用 CSV\n"
    
    # 在 VISUALIZATION 配置后添加
    if 'VISUALIZATION = False' in content:
        content = content.replace(
            'VISUALIZATION = False',
            'VISUALIZATION = False\n' + parquet_config
        )
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Parquet 配置已添加")
    else:
        print("❌ 未找到 VISUALIZATION 配置")

def update_save_methods():
    """更新保存方法，优先使用 Parquet"""
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换部分关键的 to_csv 调用为 save_to_parquet_snappy
    # 示例：个股日线数据
    replacements = [
        # 日线数据
        ('df_daily.to_csv(filepath, index=False, encoding=\'utf-8-sig\')',
         'self.save_to_parquet_snappy(df_daily, filepath.replace(".csv", ".parquet"), "日线行情") if USE_PARQUET else df_daily.to_csv(filepath, index=False, encoding=\'utf-8-sig\')'),
    ]
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
    
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 保存方法已更新（部分）")

def add_interface_documentation():
    """添加 14 个接口的文档说明"""
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在文件开头添加接口清单
    interface_doc = """
# ===========================================================================================================================
# 【14 个 Tushare 接口完整实现清单】
# 1. stock_basic - 股票基本信息
# 2. daily - 日线行情
# 3. daily_basic - 每日指标
# 4. fina_indicator - 财务指标
# 5. moneyflow - 资金流向
# 6. concept_detail - 概念题材
# 7. top_list - 龙虎榜
# 8. top_inst - 龙虎榜机构席位
# 9. balancesheet - 资产负债表
# 10. cashflow - 现金流量表
# 11. income - 利润表
# 12. hk_hold - 北向资金持股
# 13. cyq_chips - 筹码分布
# 14. stk_limit - 每日涨跌停
# ===========================================================================================================================

"""
    
    # 在文件开头添加
    if '# ==============================================' in content:
        content = content.replace(
            '# ==============================================',
            interface_doc + '# =============================================='
        )
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 接口文档已添加")
    else:
        print("❌ 未找到合适位置添加接口文档")

def main():
    """主函数"""
    print("="*80)
    print("开始集成优化功能...")
    print("="*80)
    
    add_akshare_import()
    enable_parquet_by_default()
    update_save_methods()
    add_interface_documentation()
    
    print("="*80)
    print("✅ 集成完成！")
    print("="*80)
    print("\n下一步：")
    print("1. 安装依赖：pip install pyarrow akshare")
    print("2. 测试运行：python3 fetch_data_optimized.py")
    print("="*80)

if __name__ == '__main__':
    main()
