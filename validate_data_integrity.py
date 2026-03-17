#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据完整性验证脚本
版本：v1.0
创建时间：2026-03-12

功能：
1. 验证数据文件完整性
2. 检查数据一致性
3. 生成验证报告
4. 标记异常数据
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# ============================================== 【配置区】 ==============================================
WORK_DIR = Path('/home/admin/.openclaw/agents/master')
DATA_DIR = WORK_DIR / 'data_all_stocks'
LOG_DIR = WORK_DIR / 'logs'
REPORT_DIR = WORK_DIR / 'validation_reports'

# 确保目录存在
for dir_path in [LOG_DIR, REPORT_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 验证配置
VALIDATION_CONFIG = {
    'max_workers': 20,              # 并发验证线程数
    'check_fields': True,           # 检查必填字段
    'check_consistency': True,      # 检查数据一致性
    'check_duplicates': True,       # 检查重复数据
    'generate_report': True,        # 生成验证报告
}

# 必填字段定义
REQUIRED_FIELDS = {
    'daily': ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount'],
    'daily_basic': ['trade_date', 'turnover_rate', 'volume_ratio', 'pe', 'pb'],
    'finance': ['report_date', 'revenue', 'net_profit', 'total_assets', 'total_liabilities'],
}

# ============================================== 【日志配置】 ==============================================
def setup_logging():
    """配置日志"""
    log_file = LOG_DIR / f'validate_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================== 【数据验证器】 ==============================================
class DataIntegrityValidator:
    """数据完整性验证器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
    
    def validate_file(self, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """验证单个文件"""
        errors = []
        warnings = []
        
        try:
            # 1. 检查文件是否存在
            if not file_path.exists():
                errors.append(f"文件不存在：{file_path}")
                return False, errors, warnings
            
            # 2. 检查文件大小
            file_size = file_path.stat().st_size
            if file_size == 0:
                errors.append(f"文件为空：{file_path}")
                return False, errors, warnings
            
            if file_size < 100:  # 小于 100 字节可能数据不完整
                warnings.append(f"文件过小（{file_size}字节）：{file_path}")
            
            # 3. 读取并解析 JSON
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"JSON 解析失败：{file_path} - {e}")
                return False, errors, warnings
            
            # 4. 检查数据结构
            if not isinstance(data, dict):
                errors.append(f"数据结构错误（应为 dict）：{file_path}")
                return False, errors, warnings
            
            # 5. 检查必填字段
            if self.config.get('check_fields', True):
                for data_type, fields in REQUIRED_FIELDS.items():
                    if data_type in data:
                        type_data = data[data_type]
                        if isinstance(type_data, list) and len(type_data) > 0:
                            # 检查第一条记录
                            first_record = type_data[0] if isinstance(type_data[0], dict) else {}
                            missing = [f for f in fields if f not in first_record]
                            if missing:
                                warnings.append(f"{file_path.stem} 缺少{data_type}字段：{missing}")
            
            # 6. 检查数据一致性
            if self.config.get('check_consistency', True):
                if 'daily' in data and isinstance(data['daily'], list):
                    daily_data = data['daily']
                    if len(daily_data) > 0:
                        # 检查日期顺序
                        dates = [d.get('trade_date', '') for d in daily_data if isinstance(d, dict)]
                        dates = [d for d in dates if d]
                        if dates != sorted(dates, reverse=True):
                            warnings.append(f"{file_path.stem} 日期顺序异常")
                        
                        # 检查价格合理性
                        for record in daily_data:
                            if isinstance(record, dict):
                                if record.get('high', 0) < record.get('low', 0):
                                    errors.append(f"{file_path.stem} 价格异常：high < low")
                                    break
                                if record.get('close', 0) <= 0:
                                    errors.append(f"{file_path.stem} 价格异常：close <= 0")
                                    break
            
            # 7. 检查重复数据
            if self.config.get('check_duplicates', True):
                if 'daily' in data and isinstance(data['daily'], list):
                    dates = [d.get('trade_date') for d in data['daily'] if isinstance(d, dict)]
                    duplicates = len(dates) - len(set(dates))
                    if duplicates > 0:
                        warnings.append(f"{file_path.stem} 存在{duplicates}条重复日期记录")
            
            # 验证通过
            return True, errors, warnings
        
        except Exception as e:
            errors.append(f"{file_path} 验证异常：{e}")
            return False, errors, warnings
    
    def validate_all(self, data_dir: Path) -> dict:
        """验证所有数据文件"""
        logger.info("="*80)
        logger.info("🔍 开始数据完整性验证")
        logger.info("="*80)
        
        # 获取所有数据文件
        data_files = list(data_dir.glob('*.json'))
        total = len(data_files)
        
        if total == 0:
            logger.warning("⚠️  未找到任何数据文件")
            return self.results
        
        logger.info(f"找到 {total} 个数据文件")
        logger.info(f"验证配置：并发线程={self.config['max_workers']}")
        logger.info("-"*80)
        
        self.results['total_files'] = total
        
        # 并发验证
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = {executor.submit(self.validate_file, f): f for f in data_files}
            
            for i, future in enumerate(as_completed(futures), 1):
                file_path = futures[future]
                try:
                    valid, errors, warnings = future.result()
                    
                    if valid:
                        self.results['valid_files'] += 1
                    else:
                        self.results['invalid_files'] += 1
                    
                    self.results['errors'].extend(errors)
                    self.results['warnings'].extend(warnings)
                    
                    # 进度显示
                    if i % 100 == 0 or i == total:
                        logger.info(f"验证进度：{i}/{total} ({i/total*100:.1f}%)")
                
                except Exception as e:
                    logger.error(f"❌ {file_path} 验证异常：{e}")
                    self.results['invalid_files'] += 1
                    self.results['errors'].append(f"{file_path} 验证异常：{e}")
        
        # 生成统计信息
        self.results['statistics'] = {
            'total': total,
            'valid': self.results['valid_files'],
            'invalid': self.results['invalid_files'],
            'valid_rate': self.results['valid_files'] / total * 100 if total > 0 else 0,
            'error_count': len(self.results['errors']),
            'warning_count': len(self.results['warnings']),
        }
        
        return self.results
    
    def generate_report(self, output_path: Path = None):
        """生成验证报告"""
        if not self.config.get('generate_report', True):
            return None
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = REPORT_DIR / f'validation_report_{timestamp}.json'
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'results': self.results,
            'summary': {
                'total_files': self.results['total_files'],
                'valid_files': self.results['valid_files'],
                'invalid_files': self.results['invalid_files'],
                'valid_rate': f"{self.results['statistics'].get('valid_rate', 0):.2f}%",
                'errors': len(self.results['errors']),
                'warnings': len(self.results['warnings']),
            }
        }
        
        # 保存 JSON 报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成文本摘要
        summary_path = output_path.with_suffix('.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("数据完整性验证报告\n")
            f.write("="*80 + "\n\n")
            f.write(f"验证时间：{report['timestamp']}\n\n")
            f.write("统计摘要:\n")
            f.write(f"  - 总文件数：{report['summary']['total_files']}\n")
            f.write(f"  - 有效文件：{report['summary']['valid_files']}\n")
            f.write(f"  - 无效文件：{report['summary']['invalid_files']}\n")
            f.write(f"  - 有效率：{report['summary']['valid_rate']}\n")
            f.write(f"  - 错误数：{report['summary']['errors']}\n")
            f.write(f"  - 警告数：{report['summary']['warnings']}\n\n")
            
            if self.results['errors']:
                f.write("错误列表:\n")
                for i, error in enumerate(self.results['errors'][:50], 1):
                    f.write(f"  {i}. {error}\n")
                if len(self.results['errors']) > 50:
                    f.write(f"  ... 还有 {len(self.results['errors']) - 50} 个错误\n")
                f.write("\n")
            
            if self.results['warnings']:
                f.write("警告列表:\n")
                for i, warning in enumerate(self.results['warnings'][:50], 1):
                    f.write(f"  {i}. {warning}\n")
                if len(self.results['warnings']) > 50:
                    f.write(f"  ... 还有 {len(self.results['warnings']) - 50} 个警告\n")
        
        logger.info(f"✅ 验证报告已保存：{output_path}")
        logger.info(f"✅ 验证摘要已保存：{summary_path}")
        
        return report

# ============================================== 【主程序入口】 ==============================================
def main():
    """主程序入口"""
    print("="*80)
    print("  🔍 数据完整性验证工具")
    print("="*80)
    
    # 检查数据目录
    if not DATA_DIR.exists():
        logger.error(f"❌ 数据目录不存在：{DATA_DIR}")
        sys.exit(1)
    
    # 创建验证器
    validator = DataIntegrityValidator(VALIDATION_CONFIG)
    
    # 执行验证
    results = validator.validate_all(DATA_DIR)
    
    # 生成报告
    report = validator.generate_report()
    
    # 输出摘要
    print("\n" + "="*80)
    print("验证完成！")
    print("="*80)
    print(f"总文件数：{results['total_files']}")
    print(f"有效文件：{results['valid_files']}")
    print(f"无效文件：{results['invalid_files']}")
    print(f"有效率：{results['statistics'].get('valid_rate', 0):.2f}%")
    print(f"错误数：{len(results['errors'])}")
    print(f"警告数：{len(results['warnings'])}")
    print("="*80)
    
    # 返回退出码
    if results['invalid_files'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
