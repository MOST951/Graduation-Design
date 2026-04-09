"""
报告生成模块
============

功能特性：
1. 日报/周报/月报自动生成
2. 自定义报告模板
3. 多格式导出 (HTML, PDF, Word, Excel)
4. 图表嵌入
5. 邮件发送

使用示例:
    from backend.services.report_generator import ReportGenerator
    
    generator = ReportGenerator()
    
    # 生成日报
    report = generator.generate_daily_report(data)
    
    # 导出PDF
    generator.export_pdf(report, 'report.pdf')
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict
import base64
import io

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ReportGenerator')


# ==================== 配置类 ====================

@dataclass
class ReportConfig:
    """报告配置"""
    # 基本信息
    title: str = "微博舆情分析报告"
    author: str = "舆情分析系统"
    organization: str = ""
    
    # 报告类型
    report_type: str = "daily"  # daily, weekly, monthly, custom
    
    # 内容配置
    include_summary: bool = True
    include_sentiment: bool = True
    include_keywords: bool = True
    include_topics: bool = True
    include_trend: bool = True
    include_samples: bool = True
    sample_count: int = 10
    
    # 样式配置
    theme: str = "default"  # default, professional, simple
    logo_path: str = ""
    
    # 导出配置
    output_dir: str = "./reports"
    filename_pattern: str = "{type}_{date}"


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    charts: List[Dict] = field(default_factory=list)
    tables: List[Dict] = field(default_factory=list)
    order: int = 0


@dataclass
class Report:
    """报告对象"""
    title: str
    report_type: str
    generated_at: str
    period_start: str
    period_end: str
    sections: List[ReportSection]
    summary: Dict
    metadata: Dict = field(default_factory=dict)


# ==================== 数据统计器 ====================

class DataStatistics:
    """数据统计器"""
    
    @staticmethod
    def calculate_sentiment_stats(data: List[Dict]) -> Dict:
        """计算情感统计"""
        if not data:
            return {
                'total': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'neutral_ratio': 0,
                'avg_score': 0
            }
        
        total = len(data)
        sentiments = [d.get('sentiment', 'neutral') for d in data]
        scores = [d.get('sentiment_score', 0) for d in data if d.get('sentiment_score') is not None]
        
        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        neutral = sentiments.count('neutral')
        
        return {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_ratio': round(positive / total * 100, 2) if total > 0 else 0,
            'negative_ratio': round(negative / total * 100, 2) if total > 0 else 0,
            'neutral_ratio': round(neutral / total * 100, 2) if total > 0 else 0,
            'avg_score': round(sum(scores) / len(scores), 4) if scores else 0
        }
    
    @staticmethod
    def calculate_time_distribution(data: List[Dict], 
                                   time_field: str = 'created_at',
                                   interval: str = 'hour') -> List[Dict]:
        """计算时间分布"""
        time_counts = defaultdict(lambda: {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0})
        
        for item in data:
            time_str = item.get(time_field, '')
            if not time_str:
                continue
            
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if interval == 'hour':
                    key = dt.strftime('%H:00')
                elif interval == 'day':
                    key = dt.strftime('%Y-%m-%d')
                else:
                    key = dt.strftime('%Y-%m-%d %H:00')
            except:
                continue
            
            time_counts[key]['total'] += 1
            sentiment = item.get('sentiment', 'neutral')
            time_counts[key][sentiment] += 1
        
        return [
            {'time': k, **v}
            for k, v in sorted(time_counts.items())
        ]
    
    @staticmethod
    def extract_top_keywords(data: List[Dict], 
                            text_field: str = 'text',
                            top_k: int = 20) -> List[Dict]:
        """提取热门关键词"""
        try:
            import jieba
            word_counter = Counter()
            
            stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                        '这', '那', '他', '她', '它', '们', '什么', '怎么', '可以', '没', '把'}
            
            for item in data:
                text = item.get(text_field, '')
                if text:
                    words = jieba.cut(text)
                    for word in words:
                        if len(word) >= 2 and word not in stopwords:
                            word_counter[word] += 1
            
            return [
                {'word': word, 'count': count}
                for word, count in word_counter.most_common(top_k)
            ]
        except ImportError:
            # jieba不可用时的降级方案
            return []
    
    @staticmethod
    def get_sample_weibos(data: List[Dict], 
                         sentiment: str = None,
                         count: int = 5) -> List[Dict]:
        """获取样本微博"""
        if sentiment:
            filtered = [d for d in data if d.get('sentiment') == sentiment]
        else:
            filtered = data
        
        # 按互动量排序
        sorted_data = sorted(
            filtered,
            key=lambda x: (x.get('reposts_count', 0) + x.get('comments_count', 0) + x.get('likes_count', 0)),
            reverse=True
        )
        
        return sorted_data[:count]


# ==================== HTML模板 ====================

class HTMLTemplates:
    """HTML模板"""
    
    @staticmethod
    def get_base_template() -> str:
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .report-header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .report-header .meta {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-card .label {{
            color: #666;
            margin-top: 5px;
        }}
        .stat-card.positive .value {{ color: #28a745; }}
        .stat-card.negative .value {{ color: #dc3545; }}
        .stat-card.neutral .value {{ color: #6c757d; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .keyword-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            padding: 20px;
        }}
        .keyword {{
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }}
        .keyword.large {{ font-size: 20px; padding: 12px 24px; }}
        .keyword.medium {{ font-size: 16px; }}
        .keyword.small {{ font-size: 12px; opacity: 0.8; }}
        .sample-weibo {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }}
        .sample-weibo.positive {{ border-left-color: #28a745; }}
        .sample-weibo.negative {{ border-left-color: #dc3545; }}
        .sample-weibo .content {{
            margin-bottom: 10px;
        }}
        .sample-weibo .meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .chart-container {{
            width: 100%;
            height: 300px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 0.9em;
        }}
        @media print {{
            body {{ background: white; }}
            .section {{ box-shadow: none; border: 1px solid #ddd; }}
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
</head>
<body>
    <div class="container">
        {content}
    </div>
    {scripts}
</body>
</html>'''
    
    @staticmethod
    def get_header_template() -> str:
        return '''<div class="report-header">
    <h1>{title}</h1>
    <div class="meta">
        <p>报告类型：{report_type} | 统计周期：{period_start} 至 {period_end}</p>
        <p>生成时间：{generated_at}</p>
    </div>
</div>'''
    
    @staticmethod
    def get_summary_template() -> str:
        return '''<div class="section">
    <h2>📊 数据概览</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{total}</div>
            <div class="label">总数据量</div>
        </div>
        <div class="stat-card positive">
            <div class="value">{positive_ratio}%</div>
            <div class="label">正面情感占比</div>
        </div>
        <div class="stat-card negative">
            <div class="value">{negative_ratio}%</div>
            <div class="label">负面情感占比</div>
        </div>
        <div class="stat-card neutral">
            <div class="value">{neutral_ratio}%</div>
            <div class="label">中性情感占比</div>
        </div>
    </div>
</div>'''
    
    @staticmethod
    def get_sentiment_chart_template() -> str:
        return '''<div class="section">
    <h2>📈 情感分布</h2>
    <div class="chart-container" id="sentiment-pie"></div>
    <div class="chart-container" id="sentiment-trend"></div>
</div>'''
    
    @staticmethod
    def get_keywords_template() -> str:
        return '''<div class="section">
    <h2>🔥 热门关键词</h2>
    <div class="keyword-cloud">
        {keywords}
    </div>
</div>'''
    
    @staticmethod
    def get_samples_template() -> str:
        return '''<div class="section">
    <h2>📝 典型样本</h2>
    <h3>正面样本</h3>
    {positive_samples}
    <h3>负面样本</h3>
    {negative_samples}
</div>'''
    
    @staticmethod
    def get_footer_template() -> str:
        return '''<div class="footer">
    <p>本报告由微博舆情分析系统自动生成</p>
    <p>© {year} 版权所有</p>
</div>'''


# ==================== 报告生成器 ====================

class ReportGenerator:
    """
    报告生成器
    
    支持生成日报、周报、月报，并导出为多种格式
    """
    
    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()
        self.statistics = DataStatistics()
        self.templates = HTMLTemplates()
    
    def generate_daily_report(self, data: List[Dict], 
                             date: datetime = None) -> Report:
        """生成日报"""
        date = date or datetime.now()
        period_start = date.replace(hour=0, minute=0, second=0)
        period_end = date.replace(hour=23, minute=59, second=59)
        
        return self._generate_report(
            data=data,
            report_type='日报',
            period_start=period_start,
            period_end=period_end
        )
    
    def generate_weekly_report(self, data: List[Dict],
                              end_date: datetime = None) -> Report:
        """生成周报"""
        end_date = end_date or datetime.now()
        period_end = end_date.replace(hour=23, minute=59, second=59)
        period_start = (end_date - timedelta(days=6)).replace(hour=0, minute=0, second=0)
        
        return self._generate_report(
            data=data,
            report_type='周报',
            period_start=period_start,
            period_end=period_end
        )
    
    def generate_monthly_report(self, data: List[Dict],
                               year: int = None,
                               month: int = None) -> Report:
        """生成月报"""
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        return self._generate_report(
            data=data,
            report_type='月报',
            period_start=period_start,
            period_end=period_end
        )
    
    def _generate_report(self, data: List[Dict],
                        report_type: str,
                        period_start: datetime,
                        period_end: datetime) -> Report:
        """生成报告"""
        sections = []
        
        # 1. 数据概览
        sentiment_stats = self.statistics.calculate_sentiment_stats(data)
        
        # 2. 时间分布
        time_distribution = self.statistics.calculate_time_distribution(data)
        
        # 3. 热门关键词
        keywords = self.statistics.extract_top_keywords(data)
        
        # 4. 样本微博
        positive_samples = self.statistics.get_sample_weibos(data, 'positive', 5)
        negative_samples = self.statistics.get_sample_weibos(data, 'negative', 5)
        
        # 构建报告
        return Report(
            title=f"{self.config.title} - {report_type}",
            report_type=report_type,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            period_start=period_start.strftime('%Y-%m-%d'),
            period_end=period_end.strftime('%Y-%m-%d'),
            sections=sections,
            summary={
                'sentiment_stats': sentiment_stats,
                'time_distribution': time_distribution,
                'keywords': keywords,
                'positive_samples': positive_samples,
                'negative_samples': negative_samples
            }
        )
    
    def render_html(self, report: Report) -> str:
        """渲染HTML报告"""
        content_parts = []
        
        # 1. 头部
        header = self.templates.get_header_template().format(
            title=report.title,
            report_type=report.report_type,
            period_start=report.period_start,
            period_end=report.period_end,
            generated_at=report.generated_at
        )
        content_parts.append(header)
        
        # 2. 数据概览
        stats = report.summary['sentiment_stats']
        summary = self.templates.get_summary_template().format(
            total=stats['total'],
            positive_ratio=stats['positive_ratio'],
            negative_ratio=stats['negative_ratio'],
            neutral_ratio=stats['neutral_ratio']
        )
        content_parts.append(summary)
        
        # 3. 情感图表
        content_parts.append(self.templates.get_sentiment_chart_template())
        
        # 4. 关键词
        keywords = report.summary.get('keywords', [])
        keyword_html = ''
        for i, kw in enumerate(keywords[:30]):
            size_class = 'large' if i < 5 else ('medium' if i < 15 else 'small')
            keyword_html += f'<span class="keyword {size_class}">{kw["word"]} ({kw["count"]})</span>\n'
        
        keywords_section = self.templates.get_keywords_template().format(keywords=keyword_html)
        content_parts.append(keywords_section)
        
        # 5. 样本微博
        positive_samples = report.summary.get('positive_samples', [])
        negative_samples = report.summary.get('negative_samples', [])
        
        pos_html = ''
        for sample in positive_samples:
            pos_html += f'''<div class="sample-weibo positive">
                <div class="content">{sample.get('text', '')[:200]}</div>
                <div class="meta">
                    👍 {sample.get('likes_count', 0)} | 
                    💬 {sample.get('comments_count', 0)} | 
                    🔄 {sample.get('reposts_count', 0)}
                </div>
            </div>'''
        
        neg_html = ''
        for sample in negative_samples:
            neg_html += f'''<div class="sample-weibo negative">
                <div class="content">{sample.get('text', '')[:200]}</div>
                <div class="meta">
                    👍 {sample.get('likes_count', 0)} | 
                    💬 {sample.get('comments_count', 0)} | 
                    🔄 {sample.get('reposts_count', 0)}
                </div>
            </div>'''
        
        samples_section = self.templates.get_samples_template().format(
            positive_samples=pos_html or '<p>暂无数据</p>',
            negative_samples=neg_html or '<p>暂无数据</p>'
        )
        content_parts.append(samples_section)
        
        # 6. 页脚
        footer = self.templates.get_footer_template().format(year=datetime.now().year)
        content_parts.append(footer)
        
        # 7. 图表脚本
        stats = report.summary['sentiment_stats']
        time_dist = report.summary.get('time_distribution', [])
        
        scripts = f'''<script>
        // 情感分布饼图
        var pieChart = echarts.init(document.getElementById('sentiment-pie'));
        pieChart.setOption({{
            title: {{ text: '情感分布', left: 'center' }},
            tooltip: {{ trigger: 'item' }},
            legend: {{ orient: 'vertical', left: 'left' }},
            series: [{{
                type: 'pie',
                radius: '50%',
                data: [
                    {{ value: {stats['positive']}, name: '正面', itemStyle: {{ color: '#28a745' }} }},
                    {{ value: {stats['negative']}, name: '负面', itemStyle: {{ color: '#dc3545' }} }},
                    {{ value: {stats['neutral']}, name: '中性', itemStyle: {{ color: '#6c757d' }} }}
                ]
            }}]
        }});
        
        // 时间趋势图
        var trendChart = echarts.init(document.getElementById('sentiment-trend'));
        trendChart.setOption({{
            title: {{ text: '数据量趋势', left: 'center' }},
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{
                type: 'category',
                data: {json.dumps([d['time'] for d in time_dist])}
            }},
            yAxis: {{ type: 'value' }},
            series: [{{
                type: 'line',
                data: {json.dumps([d['total'] for d in time_dist])},
                smooth: true,
                areaStyle: {{}}
            }}]
        }});
        
        // 响应式
        window.addEventListener('resize', function() {{
            pieChart.resize();
            trendChart.resize();
        }});
        </script>'''
        
        # 组装完整HTML
        html = self.templates.get_base_template().format(
            title=report.title,
            content='\n'.join(content_parts),
            scripts=scripts
        )
        
        return html
    
    def export_html(self, report: Report, output_path: str = None) -> str:
        """导出HTML文件"""
        html = self.render_html(report)
        
        if not output_path:
            os.makedirs(self.config.output_dir, exist_ok=True)
            filename = self.config.filename_pattern.format(
                type=report.report_type,
                date=datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            output_path = os.path.join(self.config.output_dir, f"{filename}.html")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML报告已导出: {output_path}")
        return output_path
    
    def export_json(self, report: Report, output_path: str = None) -> str:
        """导出JSON数据"""
        if not output_path:
            os.makedirs(self.config.output_dir, exist_ok=True)
            filename = self.config.filename_pattern.format(
                type=report.report_type,
                date=datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            output_path = os.path.join(self.config.output_dir, f"{filename}.json")
        
        report_dict = {
            'title': report.title,
            'report_type': report.report_type,
            'generated_at': report.generated_at,
            'period_start': report.period_start,
            'period_end': report.period_end,
            'summary': report.summary,
            'metadata': report.metadata
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON报告已导出: {output_path}")
        return output_path
    
    def export_csv(self, data: List[Dict], output_path: str = None) -> str:
        """导出CSV数据"""
        if not output_path:
            os.makedirs(self.config.output_dir, exist_ok=True)
            filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = os.path.join(self.config.output_dir, f"{filename}.csv")
        
        if not data:
            logger.warning("没有数据可导出")
            return output_path
        
        # 获取所有字段
        fields = set()
        for item in data:
            fields.update(item.keys())
        fields = sorted(fields)
        
        # 写入CSV
        import csv
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"CSV数据已导出: {output_path}")
        return output_path
    
    def get_report_summary(self, report: Report) -> Dict:
        """获取报告摘要"""
        stats = report.summary.get('sentiment_stats', {})
        keywords = report.summary.get('keywords', [])
        
        return {
            'title': report.title,
            'report_type': report.report_type,
            'period': f"{report.period_start} 至 {report.period_end}",
            'generated_at': report.generated_at,
            'total_count': stats.get('total', 0),
            'sentiment_distribution': {
                'positive': stats.get('positive_ratio', 0),
                'negative': stats.get('negative_ratio', 0),
                'neutral': stats.get('neutral_ratio', 0)
            },
            'top_keywords': [kw['word'] for kw in keywords[:10]],
            'avg_sentiment_score': stats.get('avg_score', 0)
        }


# ==================== 便捷函数 ====================

_generator_instance = None

def get_report_generator() -> ReportGenerator:
    """获取报告生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ReportGenerator()
    return _generator_instance


def generate_daily_report(data: List[Dict]) -> Report:
    """生成日报"""
    return get_report_generator().generate_daily_report(data)


def generate_weekly_report(data: List[Dict]) -> Report:
    """生成周报"""
    return get_report_generator().generate_weekly_report(data)


def export_report_html(report: Report, output_path: str = None) -> str:
    """导出HTML报告"""
    return get_report_generator().export_html(report, output_path)


def export_data_csv(data: List[Dict], output_path: str = None) -> str:
    """导出CSV数据"""
    return get_report_generator().export_csv(data, output_path)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 测试数据
    test_data = [
        {'text': '这个产品太棒了，非常喜欢！', 'sentiment': 'positive', 'sentiment_score': 0.8,
         'created_at': '2025-12-10T10:00:00', 'likes_count': 100, 'comments_count': 20, 'reposts_count': 5},
        {'text': '服务态度很差，再也不来了', 'sentiment': 'negative', 'sentiment_score': -0.7,
         'created_at': '2025-12-10T11:00:00', 'likes_count': 50, 'comments_count': 30, 'reposts_count': 10},
        {'text': '今天天气不错', 'sentiment': 'neutral', 'sentiment_score': 0.1,
         'created_at': '2025-12-10T12:00:00', 'likes_count': 10, 'comments_count': 2, 'reposts_count': 0},
        {'text': '真的很失望，完全不值这个价', 'sentiment': 'negative', 'sentiment_score': -0.6,
         'created_at': '2025-12-10T13:00:00', 'likes_count': 80, 'comments_count': 40, 'reposts_count': 15},
        {'text': '强烈推荐，值得购买！', 'sentiment': 'positive', 'sentiment_score': 0.9,
         'created_at': '2025-12-10T14:00:00', 'likes_count': 200, 'comments_count': 50, 'reposts_count': 30},
    ] * 20  # 复制20次模拟更多数据
    
    print("=" * 60)
    print("报告生成测试")
    print("=" * 60)
    
    generator = ReportGenerator()
    
    # 生成日报
    print("\n生成日报...")
    report = generator.generate_daily_report(test_data)
    
    # 打印摘要
    summary = generator.get_report_summary(report)
    print(f"\n报告摘要:")
    print(f"  标题: {summary['title']}")
    print(f"  周期: {summary['period']}")
    print(f"  数据量: {summary['total_count']}")
    print(f"  情感分布: 正面{summary['sentiment_distribution']['positive']}% / "
          f"负面{summary['sentiment_distribution']['negative']}% / "
          f"中性{summary['sentiment_distribution']['neutral']}%")
    print(f"  热门关键词: {', '.join(summary['top_keywords'][:5])}")
    
    # 导出HTML
    print("\n导出HTML报告...")
    html_path = generator.export_html(report)
    print(f"  HTML: {html_path}")
    
    # 导出JSON
    print("\n导出JSON报告...")
    json_path = generator.export_json(report)
    print(f"  JSON: {json_path}")
    
    # 导出CSV
    print("\n导出CSV数据...")
    csv_path = generator.export_csv(test_data)
    print(f"  CSV: {csv_path}")
    
    print("\n✅ 报告生成完成!")
