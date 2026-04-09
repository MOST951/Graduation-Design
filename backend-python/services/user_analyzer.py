"""
用户行为分析模块
================

功能特性：
1. 用户画像 - 活跃度、情感倾向、兴趣标签
2. 影响力评估 - KOL识别、影响力评分
3. 传播路径 - 信息扩散分析
4. 用户聚类 - 相似用户分组

使用示例:
    from backend.services.user_analyzer import UserAnalyzer
    
    analyzer = UserAnalyzer()
    
    # 生成用户画像
    profile = analyzer.generate_profile(user_data)
    
    # 计算影响力
    influence = analyzer.calculate_influence(user_data)
"""

import os
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UserAnalyzer')


# ==================== 配置类 ====================

@dataclass
class UserAnalyzerConfig:
    """用户分析配置"""
    # 影响力权重
    followers_weight: float = 0.3
    engagement_weight: float = 0.4
    activity_weight: float = 0.2
    quality_weight: float = 0.1
    
    # KOL阈值
    kol_influence_threshold: float = 0.7
    kol_followers_threshold: int = 10000
    
    # 活跃度配置
    active_days_threshold: int = 7
    high_activity_posts_per_day: float = 3.0
    
    # 聚类配置
    n_clusters: int = 5


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    user_name: str
    
    # 基本信息
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    
    # 活跃度
    activity_level: str = "low"  # low, medium, high
    activity_score: float = 0.0
    avg_posts_per_day: float = 0.0
    active_hours: List[int] = field(default_factory=list)
    
    # 情感倾向
    sentiment_tendency: str = "neutral"  # positive, negative, neutral
    avg_sentiment_score: float = 0.0
    positive_ratio: float = 0.0
    negative_ratio: float = 0.0
    
    # 影响力
    influence_score: float = 0.0
    influence_level: str = "low"  # low, medium, high, kol
    avg_engagement: float = 0.0
    
    # 兴趣标签
    interest_tags: List[str] = field(default_factory=list)
    top_keywords: List[str] = field(default_factory=list)
    
    # 互动特征
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_reposts: float = 0.0


@dataclass
class InfluenceResult:
    """影响力评估结果"""
    user_id: str
    influence_score: float
    influence_level: str
    is_kol: bool
    
    # 分项得分
    reach_score: float = 0.0      # 覆盖度
    engagement_score: float = 0.0  # 互动度
    activity_score: float = 0.0    # 活跃度
    quality_score: float = 0.0     # 内容质量
    
    # 排名
    rank: int = 0
    percentile: float = 0.0


@dataclass
class PropagationNode:
    """传播节点"""
    user_id: str
    user_name: str
    level: int  # 传播层级
    timestamp: str
    engagement: int
    children: List['PropagationNode'] = field(default_factory=list)


# ==================== 用户画像生成器 ====================

class ProfileGenerator:
    """用户画像生成器"""
    
    def __init__(self, config: UserAnalyzerConfig = None):
        self.config = config or UserAnalyzerConfig()
    
    def generate(self, user_id: str, posts: List[Dict], 
                user_info: Dict = None) -> UserProfile:
        """
        生成用户画像
        
        Args:
            user_id: 用户ID
            posts: 用户发布的微博列表
            user_info: 用户基本信息
            
        Returns:
            UserProfile对象
        """
        user_info = user_info or {}
        
        profile = UserProfile(
            user_id=user_id,
            user_name=user_info.get('user_name', user_info.get('screen_name', f'用户{user_id}')),
            followers_count=user_info.get('followers_count', 0),
            following_count=user_info.get('following_count', 0),
            posts_count=len(posts)
        )
        
        if not posts:
            return profile
        
        # 1. 计算活跃度
        self._calculate_activity(profile, posts)
        
        # 2. 计算情感倾向
        self._calculate_sentiment(profile, posts)
        
        # 3. 计算影响力
        self._calculate_influence(profile, posts)
        
        # 4. 提取兴趣标签
        self._extract_interests(profile, posts)
        
        # 5. 计算互动特征
        self._calculate_engagement(profile, posts)
        
        return profile
    
    def _calculate_activity(self, profile: UserProfile, posts: List[Dict]):
        """计算活跃度"""
        if not posts:
            return
        
        # 统计发帖时间
        post_times = []
        hour_counter = Counter()
        
        for post in posts:
            created_at = post.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    post_times.append(dt)
                    hour_counter[dt.hour] += 1
                except:
                    pass
        
        if not post_times:
            return
        
        # 计算日均发帖量
        date_range = (max(post_times) - min(post_times)).days + 1
        profile.avg_posts_per_day = round(len(posts) / max(1, date_range), 2)
        
        # 活跃时段（取前3个）
        profile.active_hours = [h for h, _ in hour_counter.most_common(3)]
        
        # 活跃度评分
        if profile.avg_posts_per_day >= self.config.high_activity_posts_per_day:
            profile.activity_level = 'high'
            profile.activity_score = min(1.0, profile.avg_posts_per_day / 5)
        elif profile.avg_posts_per_day >= 1.0:
            profile.activity_level = 'medium'
            profile.activity_score = 0.5 + profile.avg_posts_per_day / 6
        else:
            profile.activity_level = 'low'
            profile.activity_score = profile.avg_posts_per_day / 2
        
        profile.activity_score = round(profile.activity_score, 4)
    
    def _calculate_sentiment(self, profile: UserProfile, posts: List[Dict]):
        """计算情感倾向"""
        sentiments = [p.get('sentiment', 'neutral') for p in posts]
        scores = [p.get('sentiment_score', 0) for p in posts if p.get('sentiment_score') is not None]
        
        total = len(sentiments)
        if total == 0:
            return
        
        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        
        profile.positive_ratio = round(positive / total, 4)
        profile.negative_ratio = round(negative / total, 4)
        profile.avg_sentiment_score = round(sum(scores) / len(scores), 4) if scores else 0
        
        # 判断情感倾向
        if profile.positive_ratio > 0.5:
            profile.sentiment_tendency = 'positive'
        elif profile.negative_ratio > 0.3:
            profile.sentiment_tendency = 'negative'
        else:
            profile.sentiment_tendency = 'neutral'
    
    def _calculate_influence(self, profile: UserProfile, posts: List[Dict]):
        """计算影响力"""
        # 粉丝数得分（对数归一化）
        followers = profile.followers_count
        reach_score = math.log10(followers + 1) / 7 if followers > 0 else 0  # 假设1000万为满分
        reach_score = min(1.0, reach_score)
        
        # 互动得分
        total_engagement = sum(
            p.get('likes_count', 0) + p.get('comments_count', 0) + p.get('reposts_count', 0)
            for p in posts
        )
        avg_engagement = total_engagement / max(1, len(posts))
        engagement_score = math.log10(avg_engagement + 1) / 4  # 假设10000为满分
        engagement_score = min(1.0, engagement_score)
        
        profile.avg_engagement = round(avg_engagement, 2)
        
        # 综合影响力
        influence = (
            self.config.followers_weight * reach_score +
            self.config.engagement_weight * engagement_score +
            self.config.activity_weight * profile.activity_score
        )
        
        profile.influence_score = round(influence, 4)
        
        # 影响力等级
        if profile.influence_score >= self.config.kol_influence_threshold:
            profile.influence_level = 'kol'
        elif profile.influence_score >= 0.5:
            profile.influence_level = 'high'
        elif profile.influence_score >= 0.3:
            profile.influence_level = 'medium'
        else:
            profile.influence_level = 'low'
    
    def _extract_interests(self, profile: UserProfile, posts: List[Dict]):
        """提取兴趣标签"""
        try:
            import jieba
            
            word_counter = Counter()
            stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一',
                        '这', '那', '他', '她', '它', '们', '什么', '怎么', '可以', '没'}
            
            for post in posts:
                text = post.get('text', '')
                if text:
                    words = jieba.cut(text)
                    for word in words:
                        if len(word) >= 2 and word not in stopwords:
                            word_counter[word] += 1
            
            # 取前10个高频词作为兴趣标签
            profile.top_keywords = [w for w, _ in word_counter.most_common(10)]
            
            # 简单的兴趣分类
            interest_mapping = {
                '旅游': ['旅游', '景点', '酒店', '机票', '出行', '度假'],
                '美食': ['美食', '好吃', '餐厅', '美味', '吃货'],
                '科技': ['科技', '手机', '电脑', '互联网', '人工智能', 'AI'],
                '娱乐': ['电影', '电视剧', '综艺', '明星', '演唱会'],
                '体育': ['足球', '篮球', '运动', '健身', '比赛'],
                '财经': ['股票', '基金', '投资', '理财', '经济'],
            }
            
            interest_scores = defaultdict(int)
            for word in profile.top_keywords:
                for interest, keywords in interest_mapping.items():
                    if any(kw in word for kw in keywords):
                        interest_scores[interest] += 1
            
            profile.interest_tags = [i for i, _ in sorted(interest_scores.items(), 
                                                          key=lambda x: x[1], reverse=True)[:5]]
            
        except ImportError:
            profile.top_keywords = []
            profile.interest_tags = []
    
    def _calculate_engagement(self, profile: UserProfile, posts: List[Dict]):
        """计算互动特征"""
        if not posts:
            return
        
        likes = [p.get('likes_count', 0) for p in posts]
        comments = [p.get('comments_count', 0) for p in posts]
        reposts = [p.get('reposts_count', 0) for p in posts]
        
        profile.avg_likes = round(sum(likes) / len(likes), 2)
        profile.avg_comments = round(sum(comments) / len(comments), 2)
        profile.avg_reposts = round(sum(reposts) / len(reposts), 2)


# ==================== 影响力评估器 ====================

class InfluenceEvaluator:
    """影响力评估器"""
    
    def __init__(self, config: UserAnalyzerConfig = None):
        self.config = config or UserAnalyzerConfig()
    
    def evaluate(self, user_id: str, posts: List[Dict],
                user_info: Dict = None) -> InfluenceResult:
        """评估用户影响力"""
        user_info = user_info or {}
        
        # 1. 覆盖度得分（粉丝数）
        followers = user_info.get('followers_count', 0)
        reach_score = self._calculate_reach_score(followers)
        
        # 2. 互动度得分
        engagement_score = self._calculate_engagement_score(posts)
        
        # 3. 活跃度得分
        activity_score = self._calculate_activity_score(posts)
        
        # 4. 内容质量得分
        quality_score = self._calculate_quality_score(posts)
        
        # 综合得分
        influence_score = (
            self.config.followers_weight * reach_score +
            self.config.engagement_weight * engagement_score +
            self.config.activity_weight * activity_score +
            self.config.quality_weight * quality_score
        )
        
        # 判断是否为KOL
        is_kol = (influence_score >= self.config.kol_influence_threshold or
                  followers >= self.config.kol_followers_threshold)
        
        # 影响力等级
        if is_kol:
            level = 'kol'
        elif influence_score >= 0.5:
            level = 'high'
        elif influence_score >= 0.3:
            level = 'medium'
        else:
            level = 'low'
        
        return InfluenceResult(
            user_id=user_id,
            influence_score=round(influence_score, 4),
            influence_level=level,
            is_kol=is_kol,
            reach_score=round(reach_score, 4),
            engagement_score=round(engagement_score, 4),
            activity_score=round(activity_score, 4),
            quality_score=round(quality_score, 4)
        )
    
    def _calculate_reach_score(self, followers: int) -> float:
        """计算覆盖度得分"""
        if followers <= 0:
            return 0.0
        # 对数归一化，假设1000万粉丝为满分
        score = math.log10(followers + 1) / 7
        return min(1.0, score)
    
    def _calculate_engagement_score(self, posts: List[Dict]) -> float:
        """计算互动度得分"""
        if not posts:
            return 0.0
        
        total_engagement = sum(
            p.get('likes_count', 0) + 
            p.get('comments_count', 0) * 2 +  # 评论权重更高
            p.get('reposts_count', 0) * 3     # 转发权重最高
            for p in posts
        )
        
        avg_engagement = total_engagement / len(posts)
        # 对数归一化，假设平均10000互动为满分
        score = math.log10(avg_engagement + 1) / 4
        return min(1.0, score)
    
    def _calculate_activity_score(self, posts: List[Dict]) -> float:
        """计算活跃度得分"""
        if not posts:
            return 0.0
        
        # 统计发帖时间跨度
        times = []
        for post in posts:
            created_at = post.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    times.append(dt)
                except:
                    pass
        
        if len(times) < 2:
            return 0.3
        
        date_range = (max(times) - min(times)).days + 1
        posts_per_day = len(posts) / max(1, date_range)
        
        # 归一化，假设每天5条为满分
        score = min(1.0, posts_per_day / 5)
        return score
    
    def _calculate_quality_score(self, posts: List[Dict]) -> float:
        """计算内容质量得分"""
        if not posts:
            return 0.0
        
        quality_scores = []
        for post in posts:
            text = post.get('text', '')
            
            # 文本长度得分
            length_score = min(1.0, len(text) / 140)
            
            # 互动率得分
            engagement = (post.get('likes_count', 0) + 
                         post.get('comments_count', 0) + 
                         post.get('reposts_count', 0))
            engagement_score = min(1.0, math.log10(engagement + 1) / 3)
            
            # 情感明确度
            sentiment_score = abs(post.get('sentiment_score', 0))
            
            quality = (length_score * 0.3 + engagement_score * 0.5 + sentiment_score * 0.2)
            quality_scores.append(quality)
        
        return sum(quality_scores) / len(quality_scores)
    
    def rank_users(self, users_data: List[Dict]) -> List[InfluenceResult]:
        """批量评估并排名"""
        results = []
        
        for user_data in users_data:
            user_id = user_data.get('user_id', '')
            posts = user_data.get('posts', [])
            user_info = user_data.get('user_info', {})
            
            result = self.evaluate(user_id, posts, user_info)
            results.append(result)
        
        # 排序
        results.sort(key=lambda x: x.influence_score, reverse=True)
        
        # 添加排名信息
        for i, result in enumerate(results):
            result.rank = i + 1
            result.percentile = round((len(results) - i) / len(results) * 100, 2)
        
        return results


# ==================== 传播路径分析器 ====================

class PropagationAnalyzer:
    """传播路径分析器"""
    
    def __init__(self):
        pass
    
    def analyze_propagation(self, original_post: Dict,
                           reposts: List[Dict]) -> PropagationNode:
        """
        分析传播路径
        
        Args:
            original_post: 原始微博
            reposts: 转发列表
            
        Returns:
            传播树根节点
        """
        # 创建根节点
        root = PropagationNode(
            user_id=original_post.get('user_id', ''),
            user_name=original_post.get('user_name', ''),
            level=0,
            timestamp=original_post.get('created_at', ''),
            engagement=self._get_engagement(original_post)
        )
        
        # 构建转发树
        # 简化处理：按时间排序，假设都是一级转发
        sorted_reposts = sorted(reposts, key=lambda x: x.get('created_at', ''))
        
        for repost in sorted_reposts:
            child = PropagationNode(
                user_id=repost.get('user_id', ''),
                user_name=repost.get('user_name', ''),
                level=1,
                timestamp=repost.get('created_at', ''),
                engagement=self._get_engagement(repost)
            )
            root.children.append(child)
        
        return root
    
    def _get_engagement(self, post: Dict) -> int:
        """获取互动量"""
        return (post.get('likes_count', 0) + 
                post.get('comments_count', 0) + 
                post.get('reposts_count', 0))
    
    def get_propagation_stats(self, root: PropagationNode) -> Dict:
        """获取传播统计"""
        total_nodes = 1
        total_engagement = root.engagement
        max_level = 0
        
        def traverse(node):
            nonlocal total_nodes, total_engagement, max_level
            for child in node.children:
                total_nodes += 1
                total_engagement += child.engagement
                max_level = max(max_level, child.level)
                traverse(child)
        
        traverse(root)
        
        return {
            'total_nodes': total_nodes,
            'total_engagement': total_engagement,
            'max_level': max_level,
            'direct_reposts': len(root.children),
            'avg_engagement': round(total_engagement / total_nodes, 2)
        }
    
    def to_echarts_tree(self, root: PropagationNode) -> Dict:
        """转换为ECharts树图数据"""
        def node_to_dict(node):
            return {
                'name': node.user_name or node.user_id,
                'value': node.engagement,
                'children': [node_to_dict(child) for child in node.children]
            }
        
        return {
            'tooltip': {'trigger': 'item'},
            'series': [{
                'type': 'tree',
                'data': [node_to_dict(root)],
                'top': '5%',
                'left': '10%',
                'bottom': '5%',
                'right': '10%',
                'symbolSize': 10,
                'label': {
                    'position': 'left',
                    'verticalAlign': 'middle',
                    'align': 'right'
                },
                'leaves': {
                    'label': {
                        'position': 'right',
                        'verticalAlign': 'middle',
                        'align': 'left'
                    }
                },
                'expandAndCollapse': True,
                'animationDuration': 550,
                'animationDurationUpdate': 750
            }]
        }


# ==================== 主分析器 ====================

class UserAnalyzer:
    """
    用户行为分析器
    
    整合用户画像、影响力评估、传播分析
    """
    
    def __init__(self, config: UserAnalyzerConfig = None):
        self.config = config or UserAnalyzerConfig()
        self.profile_generator = ProfileGenerator(config)
        self.influence_evaluator = InfluenceEvaluator(config)
        self.propagation_analyzer = PropagationAnalyzer()
    
    def generate_profile(self, user_id: str, posts: List[Dict],
                        user_info: Dict = None) -> Dict:
        """生成用户画像"""
        profile = self.profile_generator.generate(user_id, posts, user_info)
        return asdict(profile)
    
    def evaluate_influence(self, user_id: str, posts: List[Dict],
                          user_info: Dict = None) -> Dict:
        """评估用户影响力"""
        result = self.influence_evaluator.evaluate(user_id, posts, user_info)
        return asdict(result)
    
    def rank_users(self, users_data: List[Dict]) -> List[Dict]:
        """用户影响力排名"""
        results = self.influence_evaluator.rank_users(users_data)
        return [asdict(r) for r in results]
    
    def analyze_propagation(self, original_post: Dict,
                           reposts: List[Dict]) -> Dict:
        """分析传播路径"""
        root = self.propagation_analyzer.analyze_propagation(original_post, reposts)
        stats = self.propagation_analyzer.get_propagation_stats(root)
        tree_data = self.propagation_analyzer.to_echarts_tree(root)
        
        return {
            'stats': stats,
            'tree_data': tree_data
        }
    
    def get_kol_list(self, users_data: List[Dict]) -> List[Dict]:
        """获取KOL列表"""
        results = self.influence_evaluator.rank_users(users_data)
        kols = [asdict(r) for r in results if r.is_kol]
        return kols
    
    def get_activity_ranking(self, users_data: List[Dict], top_k: int = 20) -> List[Dict]:
        """获取活跃度排名"""
        rankings = []
        
        for user_data in users_data:
            user_id = user_data.get('user_id', '')
            posts = user_data.get('posts', [])
            user_info = user_data.get('user_info', {})
            
            profile = self.profile_generator.generate(user_id, posts, user_info)
            rankings.append({
                'user_id': profile.user_id,
                'user_name': profile.user_name,
                'activity_score': profile.activity_score,
                'activity_level': profile.activity_level,
                'posts_count': profile.posts_count,
                'avg_posts_per_day': profile.avg_posts_per_day
            })
        
        rankings.sort(key=lambda x: x['activity_score'], reverse=True)
        return rankings[:top_k]


# ==================== 便捷函数 ====================

_analyzer_instance = None

def get_user_analyzer() -> UserAnalyzer:
    """获取用户分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = UserAnalyzer()
    return _analyzer_instance


def generate_user_profile(user_id: str, posts: List[Dict], 
                         user_info: Dict = None) -> Dict:
    """生成用户画像"""
    return get_user_analyzer().generate_profile(user_id, posts, user_info)


def evaluate_user_influence(user_id: str, posts: List[Dict],
                           user_info: Dict = None) -> Dict:
    """评估用户影响力"""
    return get_user_analyzer().evaluate_influence(user_id, posts, user_info)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 测试数据
    test_posts = [
        {'text': '今天天气真好！', 'sentiment': 'positive', 'sentiment_score': 0.8,
         'created_at': '2025-12-10T10:00:00', 'likes_count': 100, 'comments_count': 20, 'reposts_count': 5},
        {'text': '这个产品太棒了', 'sentiment': 'positive', 'sentiment_score': 0.9,
         'created_at': '2025-12-10T14:00:00', 'likes_count': 200, 'comments_count': 50, 'reposts_count': 30},
        {'text': '有点失望', 'sentiment': 'negative', 'sentiment_score': -0.5,
         'created_at': '2025-12-11T09:00:00', 'likes_count': 50, 'comments_count': 10, 'reposts_count': 2},
    ] * 10
    
    test_user_info = {
        'user_name': '测试用户',
        'followers_count': 50000,
        'following_count': 500
    }
    
    print("=" * 60)
    print("用户行为分析测试")
    print("=" * 60)
    
    analyzer = UserAnalyzer()
    
    # 1. 生成用户画像
    print("\n【用户画像】")
    profile = analyzer.generate_profile('user_001', test_posts, test_user_info)
    print(f"  用户名: {profile['user_name']}")
    print(f"  粉丝数: {profile['followers_count']}")
    print(f"  活跃度: {profile['activity_level']} ({profile['activity_score']:.2f})")
    print(f"  情感倾向: {profile['sentiment_tendency']}")
    print(f"  影响力: {profile['influence_level']} ({profile['influence_score']:.2f})")
    print(f"  兴趣标签: {', '.join(profile['interest_tags'][:5])}")
    
    # 2. 影响力评估
    print("\n【影响力评估】")
    influence = analyzer.evaluate_influence('user_001', test_posts, test_user_info)
    print(f"  综合得分: {influence['influence_score']:.4f}")
    print(f"  覆盖度: {influence['reach_score']:.4f}")
    print(f"  互动度: {influence['engagement_score']:.4f}")
    print(f"  活跃度: {influence['activity_score']:.4f}")
    print(f"  是否KOL: {'是' if influence['is_kol'] else '否'}")
    
    # 3. 用户排名
    print("\n【用户排名】")
    users_data = [
        {'user_id': 'user_001', 'posts': test_posts, 'user_info': {'followers_count': 50000}},
        {'user_id': 'user_002', 'posts': test_posts[:5], 'user_info': {'followers_count': 10000}},
        {'user_id': 'user_003', 'posts': test_posts[:2], 'user_info': {'followers_count': 1000}},
    ]
    rankings = analyzer.rank_users(users_data)
    for r in rankings:
        print(f"  #{r['rank']} {r['user_id']}: {r['influence_score']:.4f} ({r['influence_level']})")
    
    print("\n✅ 用户分析完成!")
