# ==============================================
# 【优化】存储管理模块 - storage_manager.py
# ==============================================
# 功能：负责所有数据持久化、文件读写、数据缓存管理
# 职责：数据存储、文件管理、缓存清理、数据加载
# 【优化】任务 4：添加 Parquet+Snappy 压缩存储、SQLite 备选存储、自动降级兼容
# ==============================================

import os
import json
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import RLock

# 【优化】Parquet 存储支持（自动降级兼容）
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    PARQUET_AVAILABLE = None  # 标记为 None 表示未安装

# 【优化】SQLite 存储支持
try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

logger = logging.getLogger("quant_system")


class StorageManager:
    """
    【优化】存储管理器
    职责：数据持久化、文件管理、缓存管理
    【优化】支持 Parquet+Snappy 压缩、SQLite 备选存储、自动降级兼容
    """
    
    def __init__(self, base_dir: str, storage_format: str = 'parquet'):
        """
        初始化存储管理器
        :param base_dir: 基础目录路径
        :param storage_format: 默认存储格式（parquet/sqlite/csv）
        """
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, 'data')
        self.stocks_dir = os.path.join(base_dir, 'data_all_stocks')
        self.log_dir = os.path.join(base_dir, 'logs')
        self.chart_dir = os.path.join(base_dir, 'charts')
        self.config_file = os.path.join(base_dir, 'config.json')
        self.failed_stocks_file = os.path.join(self.output_dir, 'failed_stocks.json')
        self.fetch_progress_file = os.path.join(self.output_dir, 'fetch_progress.json')
        self.permanent_failed_file = os.path.join(self.output_dir, 'permanent_failed_stocks.json')
        self.sqlite_db_path = os.path.join(self.output_dir, 'quant_data.db')
        self._lock = RLock()
        
        # 【优化】存储格式配置（自动降级）
        if storage_format == 'parquet' and not PARQUET_AVAILABLE:
            logger.warning("⚠️  pyarrow 未安装，Parquet 存储不可用，自动降级为 CSV 格式")
            self.storage_format = 'csv'
        elif storage_format == 'sqlite' and not SQLITE_AVAILABLE:
            logger.warning("⚠️  sqlite3 不可用，自动降级为 CSV 格式")
            self.storage_format = 'csv'
        else:
            self.storage_format = storage_format
        
        logger.info(f"✅ 存储管理器初始化完成，使用格式：{self.storage_format}")
        
        # 创建必要的目录
        self._create_directories()
        
        # 【优化】初始化 SQLite 数据库（如果使用 SQLite 格式）
        if self.storage_format == 'sqlite':
            self._init_sqlite_db()
    
    def _create_directories(self):
        """【优化】创建必要的目录"""
        for dir_path in [self.output_dir, self.stocks_dir, self.log_dir, self.chart_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"✅ 创建目录：{dir_path}")
    
    def _init_sqlite_db(self):
        """【优化】初始化 SQLite 数据库"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.sqlite_db_path)
                cursor = conn.cursor()
                
                # 创建通用数据表（按需扩展）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts_code TEXT NOT NULL,
                        data_type TEXT NOT NULL,
                        trade_date TEXT,
                        data_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(ts_code, data_type, trade_date)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_info (
                        ts_code TEXT PRIMARY KEY,
                        name TEXT,
                        market TEXT,
                        industry TEXT,
                        list_date TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引加速查询
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ts_code ON stock_data(ts_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_data(trade_date)')
                
                conn.commit()
                conn.close()
                logger.info("✅ SQLite 数据库初始化完成")
        except Exception as e:
            logger.error(f"❌ SQLite 数据库初始化失败：{e}")
            # 降级为 CSV
            self.storage_format = 'csv'
            logger.warning("⚠️  已自动降级为 CSV 格式")
    
    # ==============================================
    # 【优化】统一存储方法 - 所有数据保存都使用这些方法
    # ==============================================
    
    def save_dataframe(self, df: pd.DataFrame, filename: str, subdir: str = '', 
                      table_name: str = None, use_parquet: bool = True) -> bool:
        """
        【优化】统一 DataFrame 保存方法（支持 Parquet/SQLite/CSV 自动降级）
        :param df: DataFrame 数据
        :param filename: 文件名（不含后缀）
        :param subdir: 子目录
        :param table_name: SQLite 表名（仅 SQLite 模式使用）
        :param use_parquet: 是否优先使用 Parquet（仅当 storage_format='parquet' 时有效）
        :return: 是否保存成功
        """
        if df is None or df.empty:
            logger.warning(f"⚠️  尝试保存空 DataFrame：{filename}")
            return False
        
        try:
            if self.storage_format == 'sqlite' and table_name:
                return self._save_to_sqlite(df, table_name)
            elif self.storage_format == 'parquet' and use_parquet and PARQUET_AVAILABLE:
                return self._save_to_parquet(df, filename, subdir)
            else:
                # 自动降级为 CSV
                return self.save_csv(df, filename + '.csv', subdir)
        except Exception as e:
            logger.error(f"❌ 保存 DataFrame 失败：{e}")
            # 尝试降级为 CSV
            try:
                return self.save_csv(df, filename + '.csv', subdir)
            except Exception as e2:
                logger.error(f"❌ 降级 CSV 保存也失败：{e2}")
                return False
    
    def load_dataframe(self, filename: str, subdir: str = '', 
                      table_name: str = None, query: str = None) -> Optional[pd.DataFrame]:
        """
        【优化】统一 DataFrame 加载方法（支持 Parquet/SQLite/CSV 自动降级）
        :param filename: 文件名（不含后缀）
        :param subdir: 子目录
        :param table_name: SQLite 表名（仅 SQLite 模式使用）
        :param query: SQLite 查询条件（可选）
        :return: DataFrame 数据
        """
        try:
            if self.storage_format == 'sqlite' and table_name:
                return self._load_from_sqlite(table_name, query)
            elif self.storage_format == 'parquet' and PARQUET_AVAILABLE:
                return self._load_from_parquet(filename, subdir)
            else:
                # 自动降级为 CSV
                return self.load_csv(filename + '.csv', subdir)
        except Exception as e:
            logger.error(f"❌ 加载 DataFrame 失败：{e}")
            return None
    
    # ==============================================
    # 【优化】Parquet 存储方法（Snappy 压缩）
    # ==============================================
    
    def _save_to_parquet(self, df: pd.DataFrame, filename: str, subdir: str = '', 
                        compression: str = 'snappy') -> bool:
        """
        【优化】保存 Parquet 文件（使用 Snappy 压缩）
        :param df: DataFrame 数据
        :param filename: 文件名（不含后缀）
        :param subdir: 子目录
        :param compression: 压缩算法（snappy/gzip/brotli）
        :return: 是否保存成功
        """
        if not PARQUET_AVAILABLE:
            logger.warning("⚠️  pyarrow 未安装，无法保存 Parquet，降级为 CSV")
            return self.save_csv(df, filename + '.csv', subdir)
        
        try:
            if subdir:
                dir_path = os.path.join(self.output_dir, subdir)
                os.makedirs(dir_path, exist_ok=True)
                file_path = os.path.join(dir_path, filename + '.parquet')
            else:
                file_path = os.path.join(self.output_dir, filename + '.parquet')
            
            # 使用 PyArrow 保存，Snappy 压缩
            table = pa.Table.from_pandas(df, preserve_index=False)
            pq.write_table(table, file_path, compression=compression)
            
            logger.info(f"✅ 保存 Parquet 文件成功：{file_path}，共{len(df)}行，压缩算法：{compression}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Parquet 保存失败，降级为 CSV: {e}")
            return self.save_csv(df, filename + '.csv', subdir)
    
    def _load_from_parquet(self, filename: str, subdir: str = '') -> Optional[pd.DataFrame]:
        """
        【优化】加载 Parquet 文件
        :param filename: 文件名（不含后缀）
        :param subdir: 子目录
        :return: DataFrame 数据
        """
        if not PARQUET_AVAILABLE:
            logger.debug("⚠️  pyarrow 未安装，无法加载 Parquet，降级为 CSV")
            return self.load_csv(filename + '.csv', subdir)
        
        try:
            if subdir:
                file_path = os.path.join(self.output_dir, subdir, filename + '.parquet')
            else:
                file_path = os.path.join(self.output_dir, filename + '.parquet')
            
            if not os.path.exists(file_path):
                logger.debug(f"⚠️  Parquet 文件不存在，尝试 CSV: {file_path}")
                return self.load_csv(filename + '.csv', subdir)
            
            df = pq.read_table(file_path).to_pandas()
            logger.debug(f"✅ 加载 Parquet 文件成功：{file_path}，共{len(df)}行")
            return df
        except Exception as e:
            logger.warning(f"⚠️  Parquet 加载失败，降级为 CSV: {e}")
            return self.load_csv(filename + '.csv', subdir)
    
    # ==============================================
    # 【优化】SQLite 存储方法
    # ==============================================
    
    def _save_to_sqlite(self, df: pd.DataFrame, table_name: str, 
                       if_exists: str = 'append') -> bool:
        """
        【优化】保存 DataFrame 到 SQLite 数据库
        :param df: DataFrame 数据
        :param table_name: 表名
        :param if_exists: 已存在时的处理方式（fail/replace/append）
        :return: 是否保存成功
        """
        if not SQLITE_AVAILABLE:
            logger.warning("⚠️  sqlite3 不可用，无法保存 SQLite，降级为 CSV")
            return self.save_csv(df, table_name + '.csv', '')
        
        try:
            with self._lock:
                conn = sqlite3.connect(self.sqlite_db_path)
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                conn.commit()
                conn.close()
            
            logger.info(f"✅ 保存 SQLite 表成功：{table_name}，共{len(df)}行")
            return True
        except Exception as e:
            logger.warning(f"⚠️  SQLite 保存失败，降级为 CSV: {e}")
            return self.save_csv(df, table_name + '.csv', '')
    
    def _load_from_sqlite(self, table_name: str, query: str = None) -> Optional[pd.DataFrame]:
        """
        【优化】从 SQLite 数据库加载 DataFrame
        :param table_name: 表名
        :param query: 自定义查询 SQL（可选，如未提供则 SELECT * FROM table_name）
        :return: DataFrame 数据
        """
        if not SQLITE_AVAILABLE:
            logger.debug("⚠️  sqlite3 不可用，无法加载 SQLite，降级为 CSV")
            return self.load_csv(table_name + '.csv', '')
        
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            
            if query:
                df = pd.read_sql_query(query, conn)
            else:
                df = pd.read_sql_table(table_name, conn)
            
            conn.close()
            logger.debug(f"✅ 加载 SQLite 表成功：{table_name}，共{len(df)}行")
            return df
        except Exception as e:
            logger.warning(f"⚠️  SQLite 加载失败，降级为 CSV: {e}")
            return self.load_csv(table_name + '.csv', '')
    
    def execute_sql(self, sql: str, params: tuple = None) -> Optional[pd.DataFrame]:
        """
        【优化】执行自定义 SQL 查询
        :param sql: SQL 查询语句
        :param params: 参数元组
        :return: 查询结果 DataFrame
        """
        if not SQLITE_AVAILABLE:
            logger.error("❌ sqlite3 不可用，无法执行 SQL")
            return None
        
        try:
            with self._lock:
                conn = sqlite3.connect(self.sqlite_db_path)
                if params:
                    df = pd.read_sql_query(sql, conn, params=params)
                else:
                    df = pd.read_sql_query(sql, conn)
                conn.close()
            return df
        except Exception as e:
            logger.error(f"❌ 执行 SQL 失败：{e}")
            return None
    
    # ==============================================
    # 【优化】原有 JSON 存储方法（保留兼容）
    # ==============================================
    
    def save_stock_data(self, ts_code: str, data: Dict[str, pd.DataFrame]) -> bool:
        """
        【优化】保存个股数据（JSON 格式，保留兼容）
        :param ts_code: 股票代码
        :param data: 数据字典（包含 daily/daily_basic/fina_indicator 等）
        :return: 是否保存成功
        """
        try:
            stock_file = os.path.join(self.stocks_dir, f"{ts_code}.json")
            
            # 转换 DataFrame 为 JSON 格式
            json_data = {}
            for key, df in data.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    json_data[key] = df.to_dict(orient='records')
                else:
                    json_data[key] = []
            
            with self._lock:
                with open(stock_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ 保存{ts_code}数据成功：{stock_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存{ts_code}数据失败：{e}")
            return False
    
    def load_stock_data(self, ts_code: str) -> Dict[str, pd.DataFrame]:
        """
        【优化】加载个股数据（JSON 格式，保留兼容）
        :param ts_code: 股票代码
        :return: 数据字典
        """
        try:
            stock_file = os.path.join(self.stocks_dir, f"{ts_code}.json")
            
            if not os.path.exists(stock_file):
                logger.debug(f"⚠️  股票数据文件不存在：{stock_file}")
                return {}
            
            with self._lock:
                with open(stock_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            
            # 转换 JSON 为 DataFrame
            data = {}
            for key, records in json_data.items():
                if records:
                    data[key] = pd.DataFrame(records)
                else:
                    data[key] = pd.DataFrame()
            
            return data
            
        except Exception as e:
            logger.error(f"❌ 加载{ts_code}数据失败：{e}")
            return {}
    
    # ==============================================
    # 【优化】失败股票列表管理（JSON 格式，保留兼容）
    # ==============================================
    
    def save_failed_stocks(self, failed_list: List[Dict[str, Any]]) -> bool:
        """
        【优化】保存失败股票列表
        :param failed_list: 失败股票列表
        :return: 是否保存成功
        """
        try:
            with self._lock:
                with open(self.failed_stocks_file, 'w', encoding='utf-8') as f:
                    json.dump(failed_list, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 保存失败股票列表成功，共{len(failed_list)}只")
            return True
        except Exception as e:
            logger.error(f"❌ 保存失败股票列表失败：{e}")
            return False
    
    def load_failed_stocks(self) -> List[Dict[str, Any]]:
        """
        【优化】加载失败股票列表
        :return: 失败股票列表
        """
        try:
            if not os.path.exists(self.failed_stocks_file):
                return []
            
            with self._lock:
                with open(self.failed_stocks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️  加载失败股票列表失败：{e}")
            return []
    
    def save_permanent_failed(self, permanent_failed: Dict[str, Dict[str, Any]]) -> bool:
        """
        【优化】保存永久失败股票列表
        :param permanent_failed: 永久失败股票字典 {ts_code: {reason, timestamp}}
        :return: 是否保存成功
        """
        try:
            with self._lock:
                with open(self.permanent_failed_file, 'w', encoding='utf-8') as f:
                    json.dump(permanent_failed, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 保存永久失败股票列表成功，共{len(permanent_failed)}只")
            return True
        except Exception as e:
            logger.error(f"❌ 保存永久失败股票列表失败：{e}")
            return False
    
    def load_permanent_failed(self) -> Dict[str, Dict[str, Any]]:
        """
        【优化】加载永久失败股票列表
        :return: 永久失败股票字典
        """
        try:
            if not os.path.exists(self.permanent_failed_file):
                return {}
            
            with self._lock:
                with open(self.permanent_failed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️  加载永久失败股票列表失败：{e}")
            return {}
    
    def add_permanent_failed(self, ts_code: str, reason: str = "") -> bool:
        """
        【优化】添加永久失败股票
        :param ts_code: 股票代码
        :param reason: 失败原因
        :return: 是否添加成功
        """
        try:
            permanent_failed = self.load_permanent_failed()
            permanent_failed[ts_code] = {
                "reason": reason,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return self.save_permanent_failed(permanent_failed)
        except Exception as e:
            logger.error(f"❌ 添加永久失败股票失败：{e}")
            return False
    
    def save_fetch_progress(self, progress: Dict[str, Any]) -> bool:
        """
        【优化】保存抓取进度
        :param progress: 进度字典
        :return: 是否保存成功
        """
        try:
            with self._lock:
                with open(self.fetch_progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
            logger.debug(f"✅ 保存抓取进度成功：{progress.get('progress', 0)}%")
            return True
        except Exception as e:
            logger.error(f"❌ 保存抓取进度失败：{e}")
            return False
    
    def load_fetch_progress(self) -> Dict[str, Any]:
        """
        【优化】加载抓取进度
        :return: 进度字典
        """
        try:
            if not os.path.exists(self.fetch_progress_file):
                return {}
            
            with self._lock:
                with open(self.fetch_progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️  加载抓取进度失败：{e}")
            return {}
    
    # ==============================================
    # 【优化】CSV 存储方法（保留兼容，作为降级备选）
    # ==============================================
    
    def save_csv(self, data: pd.DataFrame, filename: str, subdir: str = '') -> bool:
        """
        【优化】保存 CSV 文件（降级备选）
        :param data: DataFrame 数据
        :param filename: 文件名
        :param subdir: 子目录
        :return: 是否保存成功
        """
        try:
            if subdir:
                dir_path = os.path.join(self.output_dir, subdir)
                os.makedirs(dir_path, exist_ok=True)
                file_path = os.path.join(dir_path, filename)
            else:
                file_path = os.path.join(self.output_dir, filename)
            
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 保存 CSV 文件成功：{file_path}，共{len(data)}行")
            return True
        except Exception as e:
            logger.error(f"❌ 保存 CSV 文件失败：{e}")
            return False
    
    def load_csv(self, filename: str, subdir: str = '') -> Optional[pd.DataFrame]:
        """
        【优化】加载 CSV 文件（降级备选）
        :param filename: 文件名
        :param subdir: 子目录
        :return: DataFrame 数据
        """
        try:
            if subdir:
                file_path = os.path.join(self.output_dir, subdir, filename)
            else:
                file_path = os.path.join(self.output_dir, filename)
            
            if not os.path.exists(file_path):
                logger.debug(f"⚠️  CSV 文件不存在：{file_path}")
                return None
            
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            logger.debug(f"✅ 加载 CSV 文件成功：{file_path}，共{len(df)}行")
            return df
        except Exception as e:
            logger.error(f"❌ 加载 CSV 文件失败：{e}")
            return None
    
    def save_excel(self, data: pd.DataFrame, filename: str, subdir: str = '') -> bool:
        """
        【优化】保存 Excel 文件
        :param data: DataFrame 数据
        :param filename: 文件名
        :param subdir: 子目录
        :return: 是否保存成功
        """
        try:
            if subdir:
                dir_path = os.path.join(self.output_dir, subdir)
                os.makedirs(dir_path, exist_ok=True)
                file_path = os.path.join(dir_path, filename)
            else:
                file_path = os.path.join(self.output_dir, filename)
            
            data.to_excel(file_path, index=False, engine='openpyxl')
            logger.info(f"✅ 保存 Excel 文件成功：{file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存 Excel 文件失败：{e}")
            return False
    
    # ==============================================
    # 【优化】缓存管理
    # ==============================================
    
    def clear_cache(self, cache_type: str = 'all') -> bool:
        """
        【优化】清理缓存
        :param cache_type: 缓存类型（all/stocks/failed/progress）
        :return: 是否清理成功
        """
        try:
            if cache_type in ['all', 'stocks']:
                # 清理股票数据缓存
                for file in os.listdir(self.stocks_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.stocks_dir, file))
                logger.info("✅ 清理股票数据缓存完成")
            
            if cache_type in ['all', 'failed']:
                # 清理失败列表
                if os.path.exists(self.failed_stocks_file):
                    os.remove(self.failed_stocks_file)
                if os.path.exists(self.permanent_failed_file):
                    os.remove(self.permanent_failed_file)
                logger.info("✅ 清理失败列表完成")
            
            if cache_type in ['all', 'progress']:
                # 清理进度文件
                if os.path.exists(self.fetch_progress_file):
                    os.remove(self.fetch_progress_file)
                logger.info("✅ 清理进度文件完成")
            
            return True
        except Exception as e:
            logger.error(f"❌ 清理缓存失败：{e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        【优化】获取存储统计信息
        :return: 统计信息字典
        """
        try:
            stats = {
                'stocks_count': 0,
                'stocks_size_mb': 0,
                'failed_stocks_count': 0,
                'permanent_failed_count': 0,
                'storage_format': self.storage_format,
                'parquet_available': PARQUET_AVAILABLE,
                'sqlite_available': SQLITE_AVAILABLE
            }
            
            # 统计股票数据
            if os.path.exists(self.stocks_dir):
                stock_files = [f for f in os.listdir(self.stocks_dir) if f.endswith('.json')]
                stats['stocks_count'] = len(stock_files)
                stats['stocks_size_mb'] = round(
                    sum(os.path.getsize(os.path.join(self.stocks_dir, f)) for f in stock_files) / 1024 / 1024,
                    2
                )
            
            # 统计失败股票
            failed_list = self.load_failed_stocks()
            stats['failed_stocks_count'] = len(failed_list)
            
            permanent_failed = self.load_permanent_failed()
            stats['permanent_failed_count'] = len(permanent_failed)
            
            # 【优化】统计 Parquet 文件
            if os.path.exists(self.output_dir):
                parquet_files = [f for f in os.listdir(self.output_dir) if f.endswith('.parquet')]
                stats['parquet_count'] = len(parquet_files)
                stats['parquet_size_mb'] = round(
                    sum(os.path.getsize(os.path.join(self.output_dir, f)) for f in parquet_files) / 1024 / 1024,
                    2
                )
            
            # 【优化】统计 SQLite 数据库
            if os.path.exists(self.sqlite_db_path):
                stats['sqlite_db_size_mb'] = round(
                    os.path.getsize(self.sqlite_db_path) / 1024 / 1024, 2
                )
            
            return stats
        except Exception as e:
            logger.error(f"❌ 获取存储统计失败：{e}")
            return {}
