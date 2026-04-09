"""
分析功能API路由
===============

提供情感分析、话题分析、用户分析、报告生成等API接口
"""

from flask import Blueprint, request, jsonify, send_file
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 创建蓝图
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')


# ==================== 情感分析接口 ====================

@analysis_bp.route('/sentiment', methods=['POST'])
def analyze_sentiment():
    """
    情感分析接口
    
    Request Body:
        {
            "text": "要分析的文本",
            "method": "hybrid"  // hybrid, rule, bert
        }
    
    Response:
        {
            "success": true,
            "data": {
                "text": "...",
                "sentiment": "positive",
                "score": 0.85,
                "confidence": 0.92
            }
        }
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        method = data.get('method', 'hybrid')
        
        if not text:
            return jsonify({'success': False, 'error': '文本不能为空'}), 400
        
        # 根据方法选择分析器
        if method == 'rule':
            from backend.services import rule_analyze_sentiment
            result = rule_analyze_sentiment(text)
        elif method == 'bert':
            from backend.models import ChineseBertSentimentModel, BERT_AVAILABLE
            if not BERT_AVAILABLE:
                return jsonify({'success': False, 'error': 'BERT模型不可用'}), 500
            model = ChineseBertSentimentModel()
            results = model.predict([text])
            result = results[0] if results else {}
        else:
            from backend.services import hybrid_analyze_sentiment
            result = hybrid_analyze_sentiment(text)
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/sentiment/batch', methods=['POST'])
def analyze_sentiment_batch():
    """
    批量情感分析接口
    
    Request Body:
        {
            "texts": ["文本1", "文本2", ...],
            "method": "hybrid"
        }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        method = data.get('method', 'hybrid')
        
        if not texts:
            return jsonify({'success': False, 'error': '文本列表不能为空'}), 400
        
        from backend.services import hybrid_analyze_batch
        results = hybrid_analyze_batch(texts)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"批量情感分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 话题分析接口 ====================

@analysis_bp.route('/topic/keywords', methods=['POST'])
def extract_keywords():
    """
    关键词提取接口
    
    Request Body:
        {
            "texts": ["文本1", "文本2", ...],
            "method": "tfidf",  // tfidf, textrank, both
            "top_k": 20
        }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        method = data.get('method', 'tfidf')
        top_k = data.get('top_k', 20)
        
        if not texts:
            return jsonify({'success': False, 'error': '文本列表不能为空'}), 400
        
        from backend.services import get_topic_analyzer
        analyzer = get_topic_analyzer()
        keywords = analyzer.extract_keywords(texts, method=method, top_k=top_k)
        
        return jsonify({
            'success': True,
            'data': keywords,
            'count': len(keywords)
        })
        
    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/topic/wordcloud', methods=['POST'])
def generate_wordcloud():
    """
    生成词云数据接口
    
    Request Body:
        {
            "texts": ["文本1", "文本2", ...],
            "max_words": 100
        }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        max_words = data.get('max_words', 100)
        
        if not texts:
            return jsonify({'success': False, 'error': '文本列表不能为空'}), 400
        
        from backend.services import get_topic_analyzer
        analyzer = get_topic_analyzer()
        wordcloud_data = analyzer.generate_wordcloud(texts, max_words=max_words)
        echarts_option = analyzer.get_wordcloud_option(texts, max_words=max_words)
        
        return jsonify({
            'success': True,
            'data': wordcloud_data,
            'echarts_option': echarts_option
        })
        
    except Exception as e:
        logger.error(f"词云生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/topic/modeling', methods=['POST'])
def topic_modeling():
    """
    主题建模接口
    
    Request Body:
        {
            "texts": ["文本1", "文本2", ...],
            "method": "lda",  // lda, nmf
            "n_topics": 5
        }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        method = data.get('method', 'lda')
        n_topics = data.get('n_topics', 5)
        
        if not texts:
            return jsonify({'success': False, 'error': '文本列表不能为空'}), 400
        
        from backend.services import get_topic_analyzer
        analyzer = get_topic_analyzer()
        topics = analyzer.topic_modeling(texts, method=method, n_topics=n_topics)
        
        return jsonify({
            'success': True,
            'data': topics,
            'count': len(topics)
        })
        
    except Exception as e:
        logger.error(f"主题建模失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/topic/trend', methods=['POST'])
def analyze_trend():
    """
    热度趋势分析接口
    
    Request Body:
        {
            "data": [{"text": "...", "created_at": "...", ...}, ...],
            "interval": "hour"  // hour, day
        }
    """
    try:
        data = request.get_json()
        items = data.get('data', [])
        interval = data.get('interval', 'hour')
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services import get_topic_analyzer
        analyzer = get_topic_analyzer()
        trend = analyzer.analyze_trend(items, interval=interval)
        hotspots = analyzer.detect_hotspots(items, interval=interval)
        
        return jsonify({
            'success': True,
            'data': {
                'trend': trend,
                'hotspots': hotspots
            }
        })
        
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 用户分析接口 ====================

@analysis_bp.route('/user/profile', methods=['POST'])
def generate_user_profile():
    """
    生成用户画像接口
    
    Request Body:
        {
            "user_id": "123456",
            "posts": [...],
            "user_info": {...}
        }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id', '')
        posts = data.get('posts', [])
        user_info = data.get('user_info', {})
        
        if not user_id:
            return jsonify({'success': False, 'error': '用户ID不能为空'}), 400
        
        from backend.services import get_user_analyzer
        analyzer = get_user_analyzer()
        profile = analyzer.generate_profile(user_id, posts, user_info)
        
        return jsonify({'success': True, 'data': profile})
        
    except Exception as e:
        logger.error(f"用户画像生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/user/influence', methods=['POST'])
def evaluate_user_influence():
    """
    评估用户影响力接口
    
    Request Body:
        {
            "user_id": "123456",
            "posts": [...],
            "user_info": {...}
        }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id', '')
        posts = data.get('posts', [])
        user_info = data.get('user_info', {})
        
        if not user_id:
            return jsonify({'success': False, 'error': '用户ID不能为空'}), 400
        
        from backend.services import get_user_analyzer
        analyzer = get_user_analyzer()
        influence = analyzer.evaluate_influence(user_id, posts, user_info)
        
        return jsonify({'success': True, 'data': influence})
        
    except Exception as e:
        logger.error(f"影响力评估失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/user/ranking', methods=['POST'])
def get_user_ranking():
    """
    用户影响力排名接口
    
    Request Body:
        {
            "users_data": [
                {"user_id": "...", "posts": [...], "user_info": {...}},
                ...
            ]
        }
    """
    try:
        data = request.get_json()
        users_data = data.get('users_data', [])
        
        if not users_data:
            return jsonify({'success': False, 'error': '用户数据不能为空'}), 400
        
        from backend.services import get_user_analyzer
        analyzer = get_user_analyzer()
        rankings = analyzer.rank_users(users_data)
        kols = analyzer.get_kol_list(users_data)
        
        return jsonify({
            'success': True,
            'data': {
                'rankings': rankings,
                'kols': kols,
                'total': len(rankings)
            }
        })
        
    except Exception as e:
        logger.error(f"用户排名失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 报告生成接口 ====================

@analysis_bp.route('/report/daily', methods=['POST'])
def generate_daily_report():
    """
    生成日报接口
    
    Request Body:
        {
            "data": [...],
            "date": "2025-12-10"  // 可选
        }
    """
    try:
        data = request.get_json()
        items = data.get('data', [])
        date_str = data.get('date')
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services import get_report_generator
        generator = get_report_generator()
        
        date = datetime.fromisoformat(date_str) if date_str else None
        report = generator.generate_daily_report(items, date)
        summary = generator.get_report_summary(report)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"日报生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/report/weekly', methods=['POST'])
def generate_weekly_report():
    """生成周报接口"""
    try:
        data = request.get_json()
        items = data.get('data', [])
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services import get_report_generator
        generator = get_report_generator()
        report = generator.generate_weekly_report(items)
        summary = generator.get_report_summary(report)
        
        return jsonify({'success': True, 'data': summary})
        
    except Exception as e:
        logger.error(f"周报生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/report/export/html', methods=['POST'])
def export_report_html():
    """
    导出HTML报告接口
    
    Request Body:
        {
            "data": [...],
            "report_type": "daily"  // daily, weekly, monthly
        }
    """
    try:
        data = request.get_json()
        items = data.get('data', [])
        report_type = data.get('report_type', 'daily')
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services import get_report_generator
        generator = get_report_generator()
        
        if report_type == 'weekly':
            report = generator.generate_weekly_report(items)
        elif report_type == 'monthly':
            report = generator.generate_monthly_report(items)
        else:
            report = generator.generate_daily_report(items)
        
        # 导出HTML
        output_path = generator.export_html(report)
        
        return jsonify({
            'success': True,
            'data': {
                'path': output_path,
                'filename': os.path.basename(output_path)
            }
        })
        
    except Exception as e:
        logger.error(f"HTML导出失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/report/export/csv', methods=['POST'])
def export_data_csv():
    """导出CSV数据接口"""
    try:
        data = request.get_json()
        items = data.get('data', [])
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services import get_report_generator
        generator = get_report_generator()
        output_path = generator.export_csv(items)
        
        return jsonify({
            'success': True,
            'data': {
                'path': output_path,
                'filename': os.path.basename(output_path)
            }
        })
        
    except Exception as e:
        logger.error(f"CSV导出失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/report/download/<filename>', methods=['GET'])
def download_report(filename):
    """下载报告文件"""
    try:
        reports_dir = './reports'
        file_path = os.path.join(reports_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 实时流处理接口 ====================

@analysis_bp.route('/streaming/start', methods=['POST'])
def start_streaming():
    """
    启动实时流处理接口
    
    Request Body:
        {
            "source": "rate",  // rate, socket, kafka
            "config": {...}
        }
    """
    try:
        data = request.get_json()
        source = data.get('source', 'rate')
        config = data.get('config', {})
        
        from backend.spark import start_realtime_analysis
        query_id = start_realtime_analysis(source, **config)
        
        return jsonify({
            'success': True,
            'data': {
                'query_id': query_id,
                'status': 'started'
            }
        })
        
    except Exception as e:
        logger.error(f"流处理启动失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/streaming/status', methods=['GET'])
def get_streaming_status():
    """获取流处理状态"""
    try:
        from backend.spark import get_streaming_analyzer
        analyzer = get_streaming_analyzer()
        
        status = analyzer.get_query_status()
        stats = analyzer.get_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'queries': status,
                'stats': stats
            }
        })
        
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/streaming/stop', methods=['POST'])
def stop_streaming():
    """停止流处理"""
    try:
        data = request.get_json()
        query_id = data.get('query_id')
        
        from backend.spark import get_streaming_analyzer
        analyzer = get_streaming_analyzer()
        
        if query_id:
            analyzer.stop_query(query_id)
        else:
            analyzer.stop_all()
        
        return jsonify({
            'success': True,
            'message': '流处理已停止'
        })
        
    except Exception as e:
        logger.error(f"停止流处理失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 统计接口 ====================

# ==================== 微博实时热搜接口 ====================

@analysis_bp.route('/hot-search/live', methods=['GET'])
def get_live_hot_search():
    """
    获取微博实时热搜（直接从微博爬取）
    
    Response:
        {
            "success": true,
            "data": {
                "hot_list": [...],
                "summary": {...},
                "last_refresh": "..."
            }
        }
    """
    try:
        from services.live_hot_search_service import get_live_hot_search_service
        service = get_live_hot_search_service()
        
        data = service.get_hot_search_with_sentiment()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"获取实时热搜失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/hot-search/refresh', methods=['POST'])
def refresh_hot_search():
    """强制刷新热搜"""
    try:
        from services.live_hot_search_service import get_live_hot_search_service
        service = get_live_hot_search_service()
        
        hot_list = service.force_refresh()
        
        return jsonify({
            'success': True,
            'message': '刷新完成',
            'data': {
                'hot_list': hot_list,
                'count': len(hot_list),
                'refresh_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"刷新热搜失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/hot-search/start', methods=['POST'])
def start_hot_search_service():
    """启动热搜自动刷新服务"""
    try:
        data = request.get_json() or {}
        refresh_interval = data.get('refresh_interval', 60)
        
        from services.live_hot_search_service import (
            get_live_hot_search_service, LiveHotSearchConfig
        )
        
        service = get_live_hot_search_service()
        service.config.refresh_interval = refresh_interval
        service.start()
        
        return jsonify({
            'success': True,
            'message': '热搜服务已启动',
            'config': {
                'refresh_interval': refresh_interval
            }
        })
        
    except Exception as e:
        logger.error(f"启动热搜服务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/hot-search/stop', methods=['POST'])
def stop_hot_search_service():
    """停止热搜服务"""
    try:
        from services.live_hot_search_service import stop_live_hot_search
        stop_live_hot_search()
        
        return jsonify({
            'success': True,
            'message': '热搜服务已停止'
        })
        
    except Exception as e:
        logger.error(f"停止热搜服务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/hot-search/history', methods=['GET'])
def get_hot_search_history():
    """获取热搜历史"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        from services.live_hot_search_service import get_live_hot_search_service
        service = get_live_hot_search_service()
        
        history = service.get_history(limit)
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        logger.error(f"获取热搜历史失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/hot-search/stats', methods=['GET'])
def get_hot_search_stats():
    """获取热搜服务统计"""
    try:
        from services.live_hot_search_service import get_live_hot_search_service
        service = get_live_hot_search_service()
        
        return jsonify({
            'success': True,
            'data': service.get_stats()
        })
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 实时热点接口 ====================

@analysis_bp.route('/realtime/hotspots', methods=['GET'])
def get_realtime_hotspots():
    """
    获取实时热点话题
    
    Response:
        {
            "success": true,
            "data": {
                "hotspots": [...],
                "updated_at": "..."
            }
        }
    """
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        hotspots = service.get_current_hotspots()
        stats = service.get_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'hotspots': hotspots,
                'total_count': len(hotspots),
                'last_refresh': stats.get('last_refresh'),
                'window_size': service.config.window_size
            }
        })
        
    except Exception as e:
        logger.error(f"获取实时热点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/snapshot', methods=['GET'])
def get_realtime_snapshot():
    """获取实时快照"""
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        snapshot = service.get_current_snapshot()
        
        return jsonify({
            'success': True,
            'data': snapshot
        })
        
    except Exception as e:
        logger.error(f"获取快照失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/wordcloud', methods=['GET'])
def get_realtime_wordcloud():
    """获取实时词云数据"""
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        wordcloud_data = service.get_wordcloud_data()
        
        return jsonify({
            'success': True,
            'data': wordcloud_data
        })
        
    except Exception as e:
        logger.error(f"获取词云失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/trend/<keyword>', methods=['GET'])
def get_keyword_trend(keyword):
    """获取关键词趋势"""
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        trend = service.get_keyword_trend(keyword)
        
        return jsonify({
            'success': True,
            'data': trend
        })
        
    except Exception as e:
        logger.error(f"获取趋势失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/history', methods=['GET'])
def get_snapshot_history():
    """获取快照历史"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        history = service.get_snapshot_history(limit)
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/start', methods=['POST'])
def start_realtime_service():
    """启动实时服务"""
    try:
        data = request.get_json() or {}
        
        from services.realtime_topic_service import (
            get_realtime_topic_service, RealtimeConfig
        )
        
        config = RealtimeConfig(
            refresh_interval=data.get('refresh_interval', 60),
            window_size=data.get('window_size', 3600),
            data_dir=data.get('data_dir', './data/collected')
        )
        
        service = get_realtime_topic_service()
        service.config = config
        service.start()
        
        return jsonify({
            'success': True,
            'message': '实时服务已启动',
            'config': {
                'refresh_interval': config.refresh_interval,
                'window_size': config.window_size
            }
        })
        
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/stop', methods=['POST'])
def stop_realtime_service():
    """停止实时服务"""
    try:
        from services.realtime_topic_service import stop_realtime_service
        stop_realtime_service()
        
        return jsonify({
            'success': True,
            'message': '实时服务已停止'
        })
        
    except Exception as e:
        logger.error(f"停止服务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/refresh', methods=['POST'])
def force_refresh_hotspots():
    """强制刷新热点"""
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        service.force_refresh()
        
        return jsonify({
            'success': True,
            'message': '刷新完成',
            'data': service.get_current_hotspots()
        })
        
    except Exception as e:
        logger.error(f"刷新失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/add_data', methods=['POST'])
def add_realtime_data():
    """添加实时数据"""
    try:
        data = request.get_json()
        items = data.get('data', [])
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        service.add_data(items)
        
        return jsonify({
            'success': True,
            'message': f'已添加 {len(items)} 条数据',
            'stats': service.get_stats()
        })
        
    except Exception as e:
        logger.error(f"添加数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/realtime/stats', methods=['GET'])
def get_realtime_stats():
    """获取实时服务统计"""
    try:
        from services.realtime_topic_service import get_realtime_topic_service
        service = get_realtime_topic_service()
        
        return jsonify({
            'success': True,
            'data': service.get_stats()
        })
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/stats/overview', methods=['POST'])
def get_stats_overview():
    """
    获取数据统计概览
    
    Request Body:
        {
            "data": [...]
        }
    """
    try:
        data = request.get_json()
        items = data.get('data', [])
        
        if not items:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        from backend.services.report_generator import DataStatistics
        
        sentiment_stats = DataStatistics.calculate_sentiment_stats(items)
        time_distribution = DataStatistics.calculate_time_distribution(items)
        keywords = DataStatistics.extract_top_keywords(items)
        
        return jsonify({
            'success': True,
            'data': {
                'sentiment': sentiment_stats,
                'time_distribution': time_distribution,
                'keywords': keywords[:20]
            }
        })
        
    except Exception as e:
        logger.error(f"统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
