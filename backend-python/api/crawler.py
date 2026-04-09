"""
多平台爬虫API
支持微博、抖音、快手数据采集
"""
from flask import Blueprint, request, jsonify
import os
import sys
import logging
from datetime import datetime

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from crawler.douyin_crawler import DouyinCrawler, get_douyin_crawler
from crawler.kuaishou_crawler import KuaishouCrawler, get_kuaishou_crawler

logger = logging.getLogger(__name__)

crawler_bp = Blueprint('crawler', __name__, url_prefix='/api/crawler')


# ==================== 抖音爬虫API ====================

@crawler_bp.route('/douyin/hot', methods=['GET'])
def get_douyin_hot():
    """获取抖音热门"""
    try:
        count = request.args.get('count', 20, type=int)
        crawler = get_douyin_crawler()
        videos = crawler.get_hot_videos(count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': videos,
            'source': 'douyin',
            'count': len(videos)
        })
    except Exception as e:
        logger.error(f'获取抖音热门失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@crawler_bp.route('/douyin/search', methods=['GET'])
def search_douyin():
    """搜索抖音视频"""
    try:
        keyword = request.args.get('keyword', '')
        count = request.args.get('count', 20, type=int)
        
        if not keyword:
            return jsonify({
                'code': 400,
                'message': '请提供搜索关键词'
            }), 400
        
        crawler = get_douyin_crawler()
        videos = crawler.search_videos(keyword=keyword, count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': videos,
            'source': 'douyin',
            'keyword': keyword,
            'count': len(videos)
        })
    except Exception as e:
        logger.error(f'搜索抖音视频失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@crawler_bp.route('/douyin/comments', methods=['GET'])
def get_douyin_comments():
    """获取抖音视频评论"""
    try:
        video_id = request.args.get('video_id', '')
        count = request.args.get('count', 50, type=int)
        
        if not video_id:
            return jsonify({
                'code': 400,
                'message': '请提供视频ID'
            }), 400
        
        crawler = get_douyin_crawler()
        comments = crawler.get_video_comments(video_id=video_id, count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': comments,
            'source': 'douyin',
            'video_id': video_id,
            'count': len(comments)
        })
    except Exception as e:
        logger.error(f'获取抖音评论失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 快手爬虫API ====================

@crawler_bp.route('/kuaishou/hot', methods=['GET'])
def get_kuaishou_hot():
    """获取快手热门"""
    try:
        count = request.args.get('count', 20, type=int)
        crawler = get_kuaishou_crawler()
        videos = crawler.get_hot_videos(count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': videos,
            'source': 'kuaishou',
            'count': len(videos)
        })
    except Exception as e:
        logger.error(f'获取快手热门失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@crawler_bp.route('/kuaishou/search', methods=['GET'])
def search_kuaishou():
    """搜索快手视频"""
    try:
        keyword = request.args.get('keyword', '')
        count = request.args.get('count', 20, type=int)
        
        if not keyword:
            return jsonify({
                'code': 400,
                'message': '请提供搜索关键词'
            }), 400
        
        crawler = get_kuaishou_crawler()
        videos = crawler.search_videos(keyword=keyword, count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': videos,
            'source': 'kuaishou',
            'keyword': keyword,
            'count': len(videos)
        })
    except Exception as e:
        logger.error(f'搜索快手视频失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@crawler_bp.route('/kuaishou/comments', methods=['GET'])
def get_kuaishou_comments():
    """获取快手视频评论"""
    try:
        video_id = request.args.get('video_id', '')
        count = request.args.get('count', 50, type=int)
        
        if not video_id:
            return jsonify({
                'code': 400,
                'message': '请提供视频ID'
            }), 400
        
        crawler = get_kuaishou_crawler()
        comments = crawler.get_video_comments(video_id=video_id, count=count)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': comments,
            'source': 'kuaishou',
            'video_id': video_id,
            'count': len(comments)
        })
    except Exception as e:
        logger.error(f'获取快手评论失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 统一采集API ====================

@crawler_bp.route('/collect', methods=['POST'])
def collect_data():
    """
    统一数据采集接口
    支持多平台同时采集
    """
    try:
        data = request.get_json() or {}
        
        sources = data.get('sources', ['weibo'])
        keywords = data.get('keywords', [])
        count = data.get('count', 20)
        
        results = {
            'weibo': [],
            'douyin': [],
            'kuaishou': [],
        }
        
        # 抖音采集
        if 'douyin' in sources:
            douyin_crawler = get_douyin_crawler()
            if keywords:
                for kw in keywords:
                    videos = douyin_crawler.search_videos(kw, count=count)
                    results['douyin'].extend(videos)
            else:
                results['douyin'] = douyin_crawler.get_hot_videos(count=count)
        
        # 快手采集
        if 'kuaishou' in sources:
            kuaishou_crawler = get_kuaishou_crawler()
            if keywords:
                for kw in keywords:
                    videos = kuaishou_crawler.search_videos(kw, count=count)
                    results['kuaishou'].extend(videos)
            else:
                results['kuaishou'] = kuaishou_crawler.get_hot_videos(count=count)
        
        # 统计
        total = sum(len(v) for v in results.values())
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': results,
            'total': total,
            'sources': sources,
            'keywords': keywords
        })
        
    except Exception as e:
        logger.error(f'数据采集失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@crawler_bp.route('/status', methods=['GET'])
def get_crawler_status():
    """获取爬虫状态"""
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'weibo': {
                'status': 'available',
                'description': '微博爬虫（需要Cookie）'
            },
            'douyin': {
                'status': 'available',
                'description': '抖音爬虫（需要Cookie，部分功能使用模拟数据）'
            },
            'kuaishou': {
                'status': 'available',
                'description': '快手爬虫（需要Cookie，部分功能使用模拟数据）'
            }
        }
    })


@crawler_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Crawler service is running',
        'supported_platforms': ['weibo', 'douyin', 'kuaishou']
    })
