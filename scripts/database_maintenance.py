#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库监控和维护脚本
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
学校: 四川民族学院 智能科学与技术学院 2248班
指导教师: 罗丹

功能:
1. 数据库性能监控
2. 自动索引优化
3. 数据备份和恢复
4. 空间管理和清理
5. 毕业设计数据保护
"""

import pymysql
from pymysql.cursors import DictCursor
import logging
import json
import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import time

# 尝试导入schedule库
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_maintenance.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMaintenance:
    """数据库维护服务"""
    
    def __init__(self, db_config: Dict = None):
        """
        初始化数据库维护服务
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'weibo_sentiment_graduation',
            'charset': 'utf8mb4'
        }
        
        # 备份目录
        self.backup_dir = os.path.join(os.path.dirname(__file__), 'database_backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 毕业设计保护设置 - 这些表的数据不会被清理
        self.graduation_tables = [
            'weibo_core_data',
            'sentiment_analysis_results',
            'dual_dimension_ranking',
            'graduation_statistics',
            'system_configs'
        ]
        
        # 维护统计
        self.maintenance_stats = {
            'last_backup': None,
            'last_cleanup': None,
            'last_optimize': None,
            'total_backups': 0,
            'total_cleanups': 0,
            'total_optimizations': 0,
            'errors': []
        }
        
        # 毕业设计信息
        self.graduation_info = {
            'student': '罗森',
            'student_id': '2022407443',
            'school': '四川民族学院',
            'advisor': '罗丹'
        }
    
    def get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        return pymysql.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            charset=self.db_config['charset'],
            cursorclass=DictCursor
        )
    
    # ==================== 性能监控 ====================
    
    def monitor_performance(self) -> Dict:
        """
        监控数据库性能
        
        Returns:
            性能监控报告
        """
        logger.info("开始数据库性能监控...")
        
        report = {
            'monitor_time': datetime.now().isoformat(),
            'table_statistics': [],
            'slow_queries': 0,
            'connections': 0,
            'buffer_pool': {},
            'query_cache': {},
            'warnings': []
        }
        
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # 1. 表统计信息
                cursor.execute("""
                SELECT 
                    TABLE_NAME as table_name,
                    TABLE_ROWS as row_count,
                    ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_size_mb,
                    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_size_mb,
                    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as total_size_mb,
                    ROUND(DATA_FREE / 1024 / 1024, 2) as free_space_mb
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s
                ORDER BY DATA_LENGTH + INDEX_LENGTH DESC
                """, (self.db_config['database'],))
                
                report['table_statistics'] = cursor.fetchall()
                
                # 计算总大小
                total_size = sum(t['total_size_mb'] or 0 for t in report['table_statistics'])
                report['total_database_size_mb'] = round(total_size, 2)
                
                # 2. 慢查询统计
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries'")
                result = cursor.fetchone()
                if result:
                    report['slow_queries'] = int(result.get('Value', 0))
                
                # 3. 连接数
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                result = cursor.fetchone()
                if result:
                    report['connections'] = int(result.get('Value', 0))
                
                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                result = cursor.fetchone()
                if result:
                    report['max_connections'] = int(result.get('Value', 0))
                
                # 4. InnoDB缓冲池
                cursor.execute("SHOW STATUS LIKE 'Innodb_buffer_pool%'")
                buffer_stats = cursor.fetchall()
                for stat in buffer_stats:
                    key = stat.get('Variable_name', '').replace('Innodb_buffer_pool_', '')
                    report['buffer_pool'][key] = stat.get('Value')
                
                # 5. 查询缓存（如果启用）
                cursor.execute("SHOW STATUS LIKE 'Qcache%'")
                cache_stats = cursor.fetchall()
                for stat in cache_stats:
                    key = stat.get('Variable_name', '').replace('Qcache_', '')
                    report['query_cache'][key] = stat.get('Value')
                
                # 6. 检查潜在问题
                # 检查碎片化
                for table in report['table_statistics']:
                    if table['free_space_mb'] and table['free_space_mb'] > 100:
                        report['warnings'].append(
                            f"表 {table['table_name']} 有 {table['free_space_mb']}MB 碎片空间，建议优化"
                        )
                
                # 检查连接数
                if report['connections'] > report.get('max_connections', 100) * 0.8:
                    report['warnings'].append(
                        f"连接数 ({report['connections']}) 接近最大值，建议检查连接池配置"
                    )
            
            conn.close()
            
        except pymysql.Error as e:
            logger.error(f"性能监控失败: {e}")
            report['error'] = str(e)
            self.maintenance_stats['errors'].append(f"监控失败: {e}")
        
        logger.info(f"性能监控完成: 数据库大小 {report.get('total_database_size_mb', 0)}MB, "
                   f"连接数 {report['connections']}, 警告 {len(report['warnings'])} 个")
        
        return report
    
    def get_table_sizes(self) -> List[Dict]:
        """获取表大小信息"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                SELECT 
                    TABLE_NAME as table_name,
                    TABLE_ROWS as rows,
                    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s
                ORDER BY DATA_LENGTH + INDEX_LENGTH DESC
                """, (self.db_config['database'],))
                return cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"获取表大小失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    # ==================== 索引优化 ====================
    
    def optimize_indexes(self) -> Dict:
        """
        优化索引和表
        
        Returns:
            优化结果
        """
        logger.info("开始索引优化...")
        
        result = {
            'optimize_time': datetime.now().isoformat(),
            'tables_optimized': [],
            'tables_analyzed': [],
            'errors': []
        }
        
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # 1. 查找需要优化的表（碎片空间大于1MB）
                cursor.execute("""
                SELECT 
                    TABLE_NAME as table_name,
                    ROUND(DATA_FREE / 1024 / 1024, 2) as free_space_mb
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND DATA_FREE > 1024 * 1024
                AND ENGINE = 'InnoDB'
                """, (self.db_config['database'],))
                
                tables_to_optimize = cursor.fetchall()
                
                # 2. 优化表
                for table in tables_to_optimize:
                    table_name = table['table_name']
                    try:
                        logger.info(f"优化表: {table_name} (碎片: {table['free_space_mb']}MB)")
                        cursor.execute(f"OPTIMIZE TABLE `{table_name}`")
                        result['tables_optimized'].append(table_name)
                    except pymysql.Error as e:
                        logger.warning(f"优化表 {table_name} 失败: {e}")
                        result['errors'].append(f"优化 {table_name} 失败: {e}")
                
                # 3. 分析所有表（更新统计信息）
                cursor.execute("""
                SELECT TABLE_NAME as table_name
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s
                AND ENGINE = 'InnoDB'
                """, (self.db_config['database'],))
                
                all_tables = cursor.fetchall()
                
                for table in all_tables:
                    table_name = table['table_name']
                    try:
                        cursor.execute(f"ANALYZE TABLE `{table_name}`")
                        result['tables_analyzed'].append(table_name)
                    except pymysql.Error as e:
                        logger.warning(f"分析表 {table_name} 失败: {e}")
                
                conn.commit()
            
            conn.close()
            
            self.maintenance_stats['last_optimize'] = datetime.now()
            self.maintenance_stats['total_optimizations'] += 1
            
        except pymysql.Error as e:
            logger.error(f"索引优化失败: {e}")
            result['error'] = str(e)
            self.maintenance_stats['errors'].append(f"优化失败: {e}")
        
        logger.info(f"索引优化完成: 优化 {len(result['tables_optimized'])} 个表, "
                   f"分析 {len(result['tables_analyzed'])} 个表")
        
        return result
    
    def check_missing_indexes(self) -> List[Dict]:
        """
        检查缺失的索引
        
        Returns:
            建议添加的索引列表
        """
        suggestions = []
        
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # 检查常用查询字段是否有索引
                check_fields = [
                    ('weibo_core_data', 'created_at'),
                    ('weibo_core_data', 'user_id'),
                    ('weibo_core_data', 'keyword'),
                    ('sentiment_analysis_results', 'sentiment_class'),
                    ('dual_dimension_ranking', 'composite_score'),
                ]
                
                for table, column in check_fields:
                    cursor.execute("""
                    SELECT COUNT(*) as idx_count
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = %s
                    AND COLUMN_NAME = %s
                    """, (self.db_config['database'], table, column))
                    
                    result = cursor.fetchone()
                    if result['idx_count'] == 0:
                        suggestions.append({
                            'table': table,
                            'column': column,
                            'suggestion': f"CREATE INDEX idx_{column} ON {table}({column})"
                        })
            
            conn.close()
            
        except pymysql.Error as e:
            logger.error(f"检查索引失败: {e}")
        
        return suggestions
    
    # ==================== 数据备份 ====================
    
    def backup_graduation_data(self, compress: bool = True) -> Optional[Dict]:
        """
        备份毕业设计数据
        
        Args:
            compress: 是否压缩
            
        Returns:
            备份结果
        """
        logger.info("开始备份毕业设计数据...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f'graduation_backup_{timestamp}.sql')
        
        result = {
            'backup_time': datetime.now().isoformat(),
            'backup_file': None,
            'tables_backed_up': self.graduation_tables,
            'file_size_mb': 0,
            'compressed': compress,
            'student_info': f"{self.graduation_info['student']}/{self.graduation_info['student_id']}"
        }
        
        try:
            # 方法1: 使用mysqldump（如果可用）
            mysqldump_path = self._find_mysqldump()
            
            if mysqldump_path:
                cmd = [
                    mysqldump_path,
                    f'--host={self.db_config["host"]}',
                    f'--port={self.db_config["port"]}',
                    f'--user={self.db_config["user"]}',
                    f'--password={self.db_config["password"]}',
                    '--single-transaction',
                    '--routines',
                    '--triggers',
                    self.db_config['database']
                ] + self.graduation_tables
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
                
                logger.info(f"mysqldump备份完成: {backup_file}")
            else:
                # 方法2: 使用Python导出
                self._backup_with_python(backup_file)
            
            # 压缩备份文件
            if compress and os.path.exists(backup_file):
                compressed_file = backup_file + '.gz'
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                os.remove(backup_file)
                backup_file = compressed_file
                logger.info(f"备份文件已压缩: {compressed_file}")
            
            # 获取文件大小
            if os.path.exists(backup_file):
                result['file_size_mb'] = round(os.path.getsize(backup_file) / 1024 / 1024, 2)
                result['backup_file'] = backup_file
            
            self.maintenance_stats['last_backup'] = datetime.now()
            self.maintenance_stats['total_backups'] += 1
            
            logger.info(f"毕业设计数据备份完成: {backup_file} ({result['file_size_mb']}MB)")
            
        except Exception as e:
            logger.error(f"备份失败: {e}")
            result['error'] = str(e)
            self.maintenance_stats['errors'].append(f"备份失败: {e}")
            return None
        
        return result
    
    def _find_mysqldump(self) -> Optional[str]:
        """查找mysqldump路径"""
        possible_paths = [
            'mysqldump',
            '/usr/bin/mysqldump',
            '/usr/local/bin/mysqldump',
            'C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqldump.exe',
            'C:\\xampp\\mysql\\bin\\mysqldump.exe',
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    return path
            except:
                continue
        
        return None
    
    def _backup_with_python(self, backup_file: str):
        """使用Python导出数据"""
        conn = self.get_connection()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f"-- 毕业设计数据备份\n")
            f.write(f"-- 学生: {self.graduation_info['student']}\n")
            f.write(f"-- 学号: {self.graduation_info['student_id']}\n")
            f.write(f"-- 备份时间: {datetime.now().isoformat()}\n\n")
            f.write(f"USE {self.db_config['database']};\n\n")
            
            with conn.cursor() as cursor:
                for table in self.graduation_tables:
                    try:
                        # 获取表结构
                        cursor.execute(f"SHOW CREATE TABLE `{table}`")
                        create_sql = cursor.fetchone()
                        if create_sql:
                            f.write(f"-- 表结构: {table}\n")
                            f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                            f.write(create_sql.get('Create Table', '') + ";\n\n")
                        
                        # 导出数据
                        cursor.execute(f"SELECT * FROM `{table}` WHERE graduation_batch = 1 OR graduation_flag = 1")
                        rows = cursor.fetchall()
                        
                        if rows:
                            f.write(f"-- 数据: {table} ({len(rows)} 条)\n")
                            columns = list(rows[0].keys())
                            
                            for row in rows:
                                values = []
                                for col in columns:
                                    val = row[col]
                                    if val is None:
                                        values.append('NULL')
                                    elif isinstance(val, (int, float)):
                                        values.append(str(val))
                                    elif isinstance(val, datetime):
                                        values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                                    else:
                                        val_str = str(val).replace("'", "''")
                                        values.append(f"'{val_str}'")
                                
                                f.write(f"INSERT INTO `{table}` ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                            
                            f.write("\n")
                    except pymysql.Error as e:
                        logger.warning(f"导出表 {table} 失败: {e}")
        
        conn.close()
    
    def restore_backup(self, backup_file: str) -> bool:
        """
        恢复备份
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            是否恢复成功
        """
        logger.info(f"开始恢复备份: {backup_file}")
        
        if not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return False
        
        try:
            # 如果是压缩文件，先解压
            if backup_file.endswith('.gz'):
                uncompressed_file = backup_file[:-3]
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(uncompressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file = uncompressed_file
            
            # 执行SQL文件
            conn = self.get_connection()
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句
            statements = sql_content.split(';')
            
            with conn.cursor() as cursor:
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                        except pymysql.Error as e:
                            logger.warning(f"执行SQL失败: {e}")
                
                conn.commit()
            
            conn.close()
            
            logger.info("备份恢复完成")
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            self.maintenance_stats['errors'].append(f"恢复失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份文件"""
        backups = []
        
        if os.path.exists(self.backup_dir):
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('graduation_backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    backups.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size_mb': round(os.path.getsize(filepath) / 1024 / 1024, 2),
                        'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })
        
        # 按时间倒序排列
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    # ==================== 数据清理 ====================
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """
        清理旧数据（保留毕业设计数据）
        
        Args:
            days_to_keep: 保留天数
            
        Returns:
            清理结果
        """
        logger.info(f"开始清理旧数据（保留 {days_to_keep} 天）...")
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        result = {
            'cleanup_time': datetime.now().isoformat(),
            'cutoff_date': cutoff_date.isoformat(),
            'deleted_records': {},
            'protected_tables': self.graduation_tables,
            'note': '毕业设计数据受到保护，不会被清理'
        }
        
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # 清理非毕业设计的请求日志
                cursor.execute("""
                DELETE FROM crawl_request_log 
                WHERE request_time < %s
                AND batch_id NOT IN (
                    SELECT batch_id FROM crawl_batch_log WHERE graduation_batch = 1
                )
                LIMIT 10000
                """, (cutoff_date,))
                result['deleted_records']['crawl_request_log'] = cursor.rowcount
                
                # 清理非毕业设计的数据质量日志
                cursor.execute("""
                DELETE FROM data_quality_log 
                WHERE check_time < %s
                AND graduation_check = 0
                LIMIT 10000
                """, (cutoff_date,))
                result['deleted_records']['data_quality_log'] = cursor.rowcount
                
                conn.commit()
            
            conn.close()
            
            self.maintenance_stats['last_cleanup'] = datetime.now()
            self.maintenance_stats['total_cleanups'] += 1
            
            total_deleted = sum(result['deleted_records'].values())
            logger.info(f"数据清理完成: 共删除 {total_deleted} 条记录")
            
        except pymysql.Error as e:
            logger.error(f"数据清理失败: {e}")
            result['error'] = str(e)
            self.maintenance_stats['errors'].append(f"清理失败: {e}")
        
        return result
    
    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        清理旧备份文件
        
        Args:
            keep_count: 保留的备份数量
            
        Returns:
            删除的文件数量
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        deleted = 0
        for backup in backups[keep_count:]:
            try:
                os.remove(backup['filepath'])
                deleted += 1
                logger.info(f"删除旧备份: {backup['filename']}")
            except Exception as e:
                logger.warning(f"删除备份失败: {e}")
        
        return deleted
    
    # ==================== 定时任务 ====================
    
    def run_scheduled_maintenance(self):
        """运行定时维护任务"""
        if not SCHEDULE_AVAILABLE:
            logger.warning("schedule库未安装，无法运行定时任务")
            return
        
        logger.info("启动定时维护任务...")
        
        # 每天凌晨2点优化索引
        schedule.every().day.at("02:00").do(self.optimize_indexes)
        
        # 每周日凌晨3点备份数据
        schedule.every().sunday.at("03:00").do(self.backup_graduation_data)
        
        # 每天凌晨4点清理旧数据
        schedule.every().day.at("04:00").do(self.cleanup_old_data)
        
        # 每天清理旧备份（保留5个）
        schedule.every().day.at("05:00").do(lambda: self.cleanup_old_backups(5))
        
        logger.info("定时任务已配置:")
        logger.info("  - 每天 02:00 优化索引")
        logger.info("  - 每周日 03:00 备份数据")
        logger.info("  - 每天 04:00 清理旧数据")
        logger.info("  - 每天 05:00 清理旧备份")
        
        while True:
            schedule.run_pending()
            
            # 每小时监控一次
            if datetime.now().minute == 0:
                report = self.monitor_performance()
                if report.get('warnings'):
                    for warning in report['warnings']:
                        logger.warning(warning)
            
            time.sleep(60)
    
    def run_maintenance_once(self) -> Dict:
        """
        运行一次完整维护
        
        Returns:
            维护报告
        """
        logger.info("=" * 60)
        logger.info("开始数据库维护")
        logger.info(f"学生: {self.graduation_info['student']}")
        logger.info(f"学号: {self.graduation_info['student_id']}")
        logger.info("=" * 60)
        
        report = {
            'start_time': datetime.now().isoformat(),
            'graduation_info': self.graduation_info
        }
        
        # 1. 性能监控
        report['performance'] = self.monitor_performance()
        
        # 2. 索引优化
        report['optimization'] = self.optimize_indexes()
        
        # 3. 数据备份
        report['backup'] = self.backup_graduation_data()
        
        # 4. 数据清理
        report['cleanup'] = self.cleanup_old_data()
        
        # 5. 清理旧备份
        report['backup_cleanup'] = self.cleanup_old_backups(5)
        
        report['end_time'] = datetime.now().isoformat()
        report['maintenance_stats'] = self.maintenance_stats.copy()
        
        logger.info("=" * 60)
        logger.info("数据库维护完成")
        logger.info("=" * 60)
        
        return report
    
    def get_maintenance_stats(self) -> Dict:
        """获取维护统计"""
        stats = self.maintenance_stats.copy()
        stats['backup_count'] = len(self.list_backups())
        stats['graduation_info'] = self.graduation_info
        return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='微博情感分析系统数据库维护')
    parser.add_argument('--action', choices=['monitor', 'optimize', 'backup', 'cleanup', 'full', 'scheduled'],
                       default='monitor', help='维护操作')
    parser.add_argument('--host', default='localhost', help='数据库主机')
    parser.add_argument('--user', default='root', help='数据库用户')
    parser.add_argument('--password', default='123456', help='数据库密码')
    parser.add_argument('--database', default='weibo_sentiment_graduation', help='数据库名')
    
    args = parser.parse_args()
    
    db_config = {
        'host': args.host,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }
    
    maintenance = DatabaseMaintenance(db_config)
    
    if args.action == 'monitor':
        report = maintenance.monitor_performance()
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    
    elif args.action == 'optimize':
        result = maintenance.optimize_indexes()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == 'backup':
        result = maintenance.backup_graduation_data()
        if result:
            print(f"✓ 备份成功: {result['backup_file']}")
        else:
            print("✗ 备份失败")
    
    elif args.action == 'cleanup':
        result = maintenance.cleanup_old_data()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == 'full':
        report = maintenance.run_maintenance_once()
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    
    elif args.action == 'scheduled':
        maintenance.run_scheduled_maintenance()


if __name__ == '__main__':
    main()
