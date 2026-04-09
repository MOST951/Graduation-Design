#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询优化服务 - 高性能数据查询
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
学校: 四川民族学院 智能科学与技术学院 2248班
指导教师: 罗丹

功能:
1. 查询缓存机制
2. 分页查询优化
3. 复杂查询的索引优化
4. 实时统计查询
5. 毕业设计专用查询接口
"""

import hashlib
import json
import logging
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)


class LRUCache:
    """线程安全的LRU缓存"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存数量
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
        
        # 统计
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            # 检查过期
            if datetime.now() - self.timestamps[key] > timedelta(seconds=self.ttl):
                del self.cache[key]
                del self.timestamps[key]
                self.misses += 1
                return None
            
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # 删除最旧的
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = datetime.now()
    
    def invalidate(self, key: str = None):
        """使缓存失效"""
        with self.lock:
            if key:
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
            else:
                self.cache.clear()
                self.timestamps.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.hits + self.misses
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total if total > 0 else 0
        }


class QueryService:
    """查询服务 - 优化数据库查询性能"""
    
    def __init__(self, db_service):
        """
        初始化查询服务
        
        Args:
            db_service: 数据库服务实例
        """
        self.db_service = db_service
        
        # 查询缓存
        self.cache = LRUCache(max_size=1000, ttl=300)
        
        # 查询统计
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'slow_queries': 0,
            'start_time': datetime.now()
        }
        
        # 毕业设计信息
        self.graduation_info = {
            'student': '罗森',
            'student_id': '2022407443'
        }
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_weibo_by_id(self, weibo_id: int, use_cache: bool = True) -> Optional[Dict]:
        """
        根据ID查询微博（缓存优化）
        
        Args:
            weibo_id: 微博ID
            use_cache: 是否使用缓存
            
        Returns:
            微博数据
        """
        self.query_stats['total_queries'] += 1
        
        cache_key = f"weibo_{weibo_id}"
        
        # 检查缓存
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.query_stats['cache_hits'] += 1
                return cached
        
        sql = """
        SELECT w.*, 
               s.sentiment_class, s.hybrid_score, s.confidence,
               d.composite_score, d.ranking_position, d.popularity_class
        FROM weibo_core_data w
        LEFT JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
        LEFT JOIN dual_dimension_ranking d ON w.weibo_id = d.weibo_id
        WHERE w.weibo_id = %s
        """
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (weibo_id,))
                result = cursor.fetchone()
                
                if result and use_cache:
                    self.cache.set(cache_key, result)
                
                return result
    
    def search_weibos(self, keyword: str = None, sentiment: str = None,
                     start_date: str = None, end_date: str = None,
                     popularity_class: str = None,
                     page: int = 1, page_size: int = 20,
                     order_by: str = 'created_at', order_dir: str = 'DESC') -> Dict:
        """
        搜索微博（分页优化）
        
        Args:
            keyword: 搜索关键词
            sentiment: 情感分类 (positive/neutral/negative)
            start_date: 开始日期
            end_date: 结束日期
            popularity_class: 热度分类 (high/medium/low)
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_dir: 排序方向
            
        Returns:
            搜索结果
        """
        self.query_stats['total_queries'] += 1
        
        # 构建查询条件
        conditions = ["w.graduation_batch = 1"]
        params = []
        
        if keyword:
            conditions.append("(w.content LIKE %s OR w.keyword = %s)")
            params.extend([f"%{keyword}%", keyword])
        
        if sentiment:
            conditions.append("s.sentiment_class = %s")
            params.append(sentiment)
        
        if start_date:
            conditions.append("w.created_at >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("w.created_at <= %s")
            params.append(end_date)
        
        if popularity_class:
            conditions.append("d.popularity_class = %s")
            params.append(popularity_class)
        
        where_clause = " AND ".join(conditions)
        
        # 验证排序字段
        valid_order_fields = ['created_at', 'crawled_at', 'reposts_count', 
                             'comments_count', 'attitudes_count', 'composite_score']
        if order_by not in valid_order_fields:
            order_by = 'created_at'
        
        order_dir = 'DESC' if order_dir.upper() == 'DESC' else 'ASC'
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                # 计算总数
                count_sql = f"""
                SELECT COUNT(*) as total
                FROM weibo_core_data w
                LEFT JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
                LEFT JOIN dual_dimension_ranking d ON w.weibo_id = d.weibo_id
                WHERE {where_clause}
                """
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']
                
                # 计算分页
                offset = (page - 1) * page_size
                total_pages = (total + page_size - 1) // page_size
                
                # 主查询
                query_sql = f"""
                SELECT w.weibo_id, w.content, w.created_at, w.user_name, w.user_id,
                       w.reposts_count, w.comments_count, w.attitudes_count,
                       w.keyword, w.location, w.source,
                       s.sentiment_class, s.hybrid_score, s.confidence,
                       d.composite_score, d.ranking_position, d.popularity_class
                FROM weibo_core_data w
                LEFT JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
                LEFT JOIN dual_dimension_ranking d ON w.weibo_id = d.weibo_id
                WHERE {where_clause}
                ORDER BY {order_by} {order_dir}
                LIMIT %s OFFSET %s
                """
                
                cursor.execute(query_sql, params + [page_size, offset])
                results = cursor.fetchall()
                
                return {
                    'data': results,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': total,
                        'total_pages': total_pages,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    },
                    'query_info': {
                        'keyword': keyword,
                        'sentiment': sentiment,
                        'date_range': f"{start_date or 'N/A'} to {end_date or 'N/A'}",
                        'order_by': f"{order_by} {order_dir}"
                    }
                }
    
    def get_top_weibos(self, limit: int = 100, batch_id: str = None) -> List[Dict]:
        """
        获取TOP热门微博
        
        Args:
            limit: 返回数量
            batch_id: 批次ID（可选）
            
        Returns:
            热门微博列表
        """
        self.query_stats['total_queries'] += 1
        
        cache_key = f"top_weibos_{limit}_{batch_id or 'all'}"
        cached = self.cache.get(cache_key)
        if cached:
            self.query_stats['cache_hits'] += 1
            return cached
        
        sql = """
        SELECT d.ranking_position, d.weibo_id, w.content, w.user_name,
               d.sentiment_score, d.sentiment_category,
               d.popularity_score, d.popularity_class,
               d.composite_score, d.time_decay,
               w.reposts_count, w.comments_count, w.attitudes_count,
               w.created_at
        FROM dual_dimension_ranking d
        JOIN weibo_core_data w ON d.weibo_id = w.weibo_id
        WHERE d.graduation_flag = 1
        """
        
        params = []
        if batch_id:
            sql += " AND d.batch_id = %s"
            params.append(batch_id)
        
        sql += " ORDER BY d.composite_score DESC LIMIT %s"
        params.append(limit)
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                self.cache.set(cache_key, results)
                return results
    
    def get_sentiment_distribution(self, start_date: str = None, 
                                   end_date: str = None) -> Dict:
        """
        获取情感分布统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            情感分布数据
        """
        self.query_stats['total_queries'] += 1
        
        conditions = ["graduation_flag = 1"]
        params = []
        
        if start_date:
            conditions.append("analysis_time >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("analysis_time <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
        SELECT 
            sentiment_class,
            COUNT(*) as count,
            ROUND(AVG(hybrid_score), 4) as avg_score,
            ROUND(AVG(confidence), 4) as avg_confidence,
            ROUND(AVG(intensity), 4) as avg_intensity
        FROM sentiment_analysis_results
        WHERE {where_clause}
        GROUP BY sentiment_class
        ORDER BY count DESC
        """
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                distribution = cursor.fetchall()
                
                # 计算总数和百分比
                total = sum(d['count'] for d in distribution)
                for d in distribution:
                    d['percentage'] = round(d['count'] * 100 / total, 2) if total > 0 else 0
                
                return {
                    'distribution': distribution,
                    'total': total,
                    'date_range': {
                        'start': start_date,
                        'end': end_date
                    }
                }
    
    def get_timeline_statistics(self, days: int = 7, granularity: str = 'day') -> List[Dict]:
        """
        获取时间线统计
        
        Args:
            days: 天数
            granularity: 粒度 (hour/day/week)
            
        Returns:
            时间线数据
        """
        self.query_stats['total_queries'] += 1
        
        if granularity == 'hour':
            date_format = '%Y-%m-%d %H:00'
            group_by = "DATE_FORMAT(created_at, '%Y-%m-%d %H:00')"
        elif granularity == 'week':
            date_format = '%Y-%W'
            group_by = "YEARWEEK(created_at)"
        else:
            date_format = '%Y-%m-%d'
            group_by = "DATE(created_at)"
        
        sql = f"""
        SELECT 
            {group_by} as time_bucket,
            COUNT(*) as weibo_count,
            SUM(CASE WHEN s.sentiment_class = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN s.sentiment_class = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
            SUM(CASE WHEN s.sentiment_class = 'negative' THEN 1 ELSE 0 END) as negative_count,
            ROUND(AVG(s.hybrid_score), 4) as avg_sentiment
        FROM weibo_core_data w
        LEFT JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
        WHERE w.graduation_batch = 1
        AND w.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY {group_by}
        ORDER BY time_bucket DESC
        """
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (days,))
                return cursor.fetchall()
    
    def get_keyword_statistics(self, limit: int = 20) -> List[Dict]:
        """
        获取关键词统计
        
        Args:
            limit: 返回数量
            
        Returns:
            关键词统计数据
        """
        self.query_stats['total_queries'] += 1
        
        sql = """
        SELECT 
            keyword,
            COUNT(*) as weibo_count,
            SUM(reposts_count) as total_reposts,
            SUM(comments_count) as total_comments,
            SUM(attitudes_count) as total_attitudes,
            ROUND(AVG(s.hybrid_score), 4) as avg_sentiment
        FROM weibo_core_data w
        LEFT JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
        WHERE w.graduation_batch = 1 AND w.keyword IS NOT NULL AND w.keyword != ''
        GROUP BY keyword
        ORDER BY weibo_count DESC
        LIMIT %s
        """
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                return cursor.fetchall()
    
    def get_user_statistics(self, limit: int = 20) -> List[Dict]:
        """
        获取用户统计
        
        Args:
            limit: 返回数量
            
        Returns:
            用户统计数据
        """
        self.query_stats['total_queries'] += 1
        
        sql = """
        SELECT 
            user_id,
            user_name,
            COUNT(*) as weibo_count,
            SUM(reposts_count) as total_reposts,
            SUM(comments_count) as total_comments,
            SUM(attitudes_count) as total_attitudes,
            MAX(followers_count) as followers_count,
            MAX(verified) as verified
        FROM weibo_core_data
        WHERE graduation_batch = 1
        GROUP BY user_id, user_name
        ORDER BY weibo_count DESC
        LIMIT %s
        """
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                return cursor.fetchall()
    
    def get_graduation_statistics(self) -> Dict:
        """
        获取毕业设计统计（实时计算）
        
        Returns:
            毕业设计统计数据
        """
        self.query_stats['total_queries'] += 1
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                stats = {}
                
                # 1. 数据总量统计
                cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM weibo_core_data WHERE graduation_batch=1) as total_weibos,
                    (SELECT COUNT(DISTINCT user_id) FROM weibo_core_data WHERE graduation_batch=1) as total_users,
                    (SELECT COUNT(DISTINCT keyword) FROM weibo_core_data WHERE graduation_batch=1 AND keyword IS NOT NULL) as total_keywords,
                    (SELECT COUNT(*) FROM sentiment_analysis_results WHERE graduation_flag=1) as analyzed_weibos,
                    (SELECT COUNT(*) FROM dual_dimension_ranking WHERE graduation_flag=1) as ranked_weibos,
                    (SELECT COUNT(*) FROM crawl_batch_log WHERE graduation_batch=1) as total_batches
                """)
                stats['basic'] = cursor.fetchone()
                
                # 2. 情感分布
                cursor.execute("""
                SELECT 
                    sentiment_class,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM sentiment_analysis_results WHERE graduation_flag=1), 2) as percentage
                FROM sentiment_analysis_results
                WHERE graduation_flag = 1
                GROUP BY sentiment_class
                ORDER BY count DESC
                """)
                stats['sentiment_distribution'] = cursor.fetchall()
                
                # 3. 热度分布
                cursor.execute("""
                SELECT 
                    popularity_class,
                    COUNT(*) as count
                FROM dual_dimension_ranking
                WHERE graduation_flag = 1
                GROUP BY popularity_class
                ORDER BY count DESC
                """)
                stats['popularity_distribution'] = cursor.fetchall()
                
                # 4. 最近7天趋势
                cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM weibo_core_data 
                WHERE graduation_batch=1
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """)
                stats['timeline'] = cursor.fetchall()
                
                # 5. TOP5关键词
                cursor.execute("""
                SELECT keyword, COUNT(*) as count
                FROM weibo_core_data
                WHERE graduation_batch=1 AND keyword IS NOT NULL AND keyword != ''
                GROUP BY keyword
                ORDER BY count DESC
                LIMIT 5
                """)
                stats['top_keywords'] = cursor.fetchall()
                
                # 添加元信息
                stats['graduation_info'] = self.graduation_info
                stats['generated_at'] = datetime.now().isoformat()
                stats['cache_stats'] = self.cache.get_stats()
                stats['query_stats'] = self.query_stats.copy()
                stats['query_stats']['uptime'] = str(datetime.now() - self.query_stats['start_time'])
                
                return stats
    
    def get_dual_dimension_analysis(self, batch_id: str = None) -> Dict:
        """
        获取双维度分析结果
        
        Args:
            batch_id: 批次ID
            
        Returns:
            双维度分析数据
        """
        self.query_stats['total_queries'] += 1
        
        conditions = ["graduation_flag = 1"]
        params = []
        
        if batch_id:
            conditions.append("batch_id = %s")
            params.append(batch_id)
        
        where_clause = " AND ".join(conditions)
        
        with self.db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                # 情感-热度交叉分析
                cursor.execute(f"""
                SELECT 
                    sentiment_category,
                    popularity_class,
                    COUNT(*) as count,
                    ROUND(AVG(composite_score), 4) as avg_composite_score
                FROM dual_dimension_ranking
                WHERE {where_clause}
                GROUP BY sentiment_category, popularity_class
                ORDER BY sentiment_category, popularity_class
                """, params)
                cross_analysis = cursor.fetchall()
                
                # 综合评分分布
                cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN composite_score >= 0.8 THEN '0.8-1.0'
                        WHEN composite_score >= 0.6 THEN '0.6-0.8'
                        WHEN composite_score >= 0.4 THEN '0.4-0.6'
                        WHEN composite_score >= 0.2 THEN '0.2-0.4'
                        ELSE '0.0-0.2'
                    END as score_range,
                    COUNT(*) as count
                FROM dual_dimension_ranking
                WHERE {where_clause}
                GROUP BY score_range
                ORDER BY score_range DESC
                """, params)
                score_distribution = cursor.fetchall()
                
                # 算法参数统计
                cursor.execute(f"""
                SELECT 
                    ROUND(AVG(alpha_weight), 2) as avg_alpha,
                    ROUND(AVG(beta_weight), 2) as avg_beta,
                    ROUND(AVG(time_decay), 4) as avg_time_decay,
                    COUNT(*) as total_records
                FROM dual_dimension_ranking
                WHERE {where_clause}
                """, params)
                algorithm_stats = cursor.fetchone()
                
                return {
                    'cross_analysis': cross_analysis,
                    'score_distribution': score_distribution,
                    'algorithm_stats': algorithm_stats,
                    'formula': 'C_score = α × |sentiment_score| + β × popularity_score × time_decay',
                    'default_weights': {'alpha': 0.6, 'beta': 0.4}
                }
    
    def invalidate_cache(self, pattern: str = None):
        """
        使缓存失效
        
        Args:
            pattern: 缓存键模式（None表示清空所有）
        """
        if pattern:
            # 简单实现：清空所有缓存
            self.cache.invalidate()
        else:
            self.cache.invalidate()
        
        logger.info("缓存已清空")
    
    def get_query_stats(self) -> Dict:
        """获取查询统计"""
        stats = self.query_stats.copy()
        stats['cache_stats'] = self.cache.get_stats()
        stats['uptime'] = str(datetime.now() - self.query_stats['start_time'])
        return stats


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 需要先导入数据库服务
    try:
        from database_service import DatabaseService
        
        db = DatabaseService()
        query = QueryService(db)
        
        # 测试查询
        stats = query.get_graduation_statistics()
        print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
        
    except Exception as e:
        print(f"测试失败: {e}")
