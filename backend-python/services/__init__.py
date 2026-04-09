# 微博数据采集服务模块
"""
微博数据采集服务
================

模块列表：
- WeiboDataCollector: 主采集器类
- WeiboAPIClient: API客户端
- ProxyPool: 代理IP池
- UserAgentPool: UA池
- CookiePool: Cookie池
- LocalCache: 本地缓存

使用示例:
    from backend.services import WeiboDataCollector
    
    collector = WeiboDataCollector()
    
    # 关键词采集
    weibos = collector.collect_by_keyword('人工智能', limit=100)
    
    # 热搜采集
    hot_search = collector.collect_hot_search()
    
    # 用户时间线采集
    user_weibos = collector.collect_user_timeline('1234567890', limit=50)
"""

from .weibo_collector import (
    WeiboDataCollector,
    CollectionMode,
    DataSource,
    CollectionTask,
    DataValidator,
    quick_collect_keyword,
    quick_collect_hot_search,
    quick_collect_user,
)
from .weibo_api_client import WeiboAPIClient
from .proxy_pool import ProxyPool
from .ua_pool import UserAgentPool
from .cookie_pool import CookiePool
from .local_cache import LocalCache
from .storage_service import (
    StorageService,
    StorageConfig,
    HDFSClient,
    HBaseClient,
    MySQLClient,
    RedisClient,
    get_storage_service,
    cache_decorator,
)
from .rule_based_analyzer import (
    RuleBasedSentimentAnalyzer,
    SentimentMatch,
    AnalysisResult,
    EmojiProcessor,
    get_analyzer,
    analyze_sentiment as rule_analyze_sentiment,
    analyze_batch,
)
from .hybrid_analyzer import (
    HybridSentimentAnalyzer,
    HybridConfig,
    HybridResult,
    AnalysisContext,
    UserHistoryManager,
    TopicSentimentManager,
    OnlineLearningManager,
    get_hybrid_analyzer,
    analyze_sentiment as hybrid_analyze_sentiment,
    analyze_batch as hybrid_analyze_batch,
)
from .topic_analyzer import (
    TopicAnalyzer,
    TopicConfig,
    KeywordExtractor,
    TopicModeler,
    WordCloudGenerator,
    TrendAnalyzer,
    get_topic_analyzer,
    extract_keywords,
    generate_wordcloud,
    topic_modeling,
)
from .report_generator import (
    ReportGenerator,
    ReportConfig,
    Report,
    DataStatistics,
    get_report_generator,
    generate_daily_report,
    generate_weekly_report,
    export_report_html,
    export_data_csv,
)
from .user_analyzer import (
    UserAnalyzer,
    UserAnalyzerConfig,
    UserProfile,
    InfluenceResult,
    ProfileGenerator,
    InfluenceEvaluator,
    PropagationAnalyzer,
    get_user_analyzer,
    generate_user_profile,
    evaluate_user_influence,
)
from .realtime_topic_service import (
    RealtimeTopicService,
    RealtimeConfig,
    HotTopic,
    TopicSnapshot,
    DataBuffer,
    get_realtime_topic_service,
    start_realtime_service,
    stop_realtime_service,
)
from .live_hot_search_service import (
    LiveHotSearchService,
    LiveHotSearchConfig,
    WeiboHotSearchCrawler,
    get_live_hot_search_service,
    start_live_hot_search,
    stop_live_hot_search,
)

# 数据库服务
try:
    from .database_service import (
        DatabaseService,
        get_db_service,
    )
except ImportError:
    DatabaseService = None
    get_db_service = None

__all__ = [
    'WeiboDataCollector',
    'WeiboAPIClient',
    'ProxyPool',
    'UserAgentPool',
    'CookiePool',
    'LocalCache',
    'CollectionMode',
    'DataSource',
    'CollectionTask',
    'DataValidator',
    'quick_collect_keyword',
    'quick_collect_hot_search',
    'quick_collect_user',
    # 存储服务
    'StorageService',
    'StorageConfig',
    'HDFSClient',
    'HBaseClient',
    'MySQLClient',
    'RedisClient',
    'get_storage_service',
    'cache_decorator',
    # 规则分析器
    'RuleBasedSentimentAnalyzer',
    'SentimentMatch',
    'AnalysisResult',
    'EmojiProcessor',
    'get_analyzer',
    'rule_analyze_sentiment',
    'analyze_batch',
    # 混合分析器
    'HybridSentimentAnalyzer',
    'HybridConfig',
    'HybridResult',
    'AnalysisContext',
    'UserHistoryManager',
    'TopicSentimentManager',
    'OnlineLearningManager',
    'get_hybrid_analyzer',
    'hybrid_analyze_sentiment',
    'hybrid_analyze_batch',
    # 话题分析
    'TopicAnalyzer',
    'TopicConfig',
    'KeywordExtractor',
    'TopicModeler',
    'WordCloudGenerator',
    'TrendAnalyzer',
    'get_topic_analyzer',
    'extract_keywords',
    'generate_wordcloud',
    'topic_modeling',
    # 报告生成
    'ReportGenerator',
    'ReportConfig',
    'Report',
    'DataStatistics',
    'get_report_generator',
    'generate_daily_report',
    'generate_weekly_report',
    'export_report_html',
    'export_data_csv',
    # 用户分析
    'UserAnalyzer',
    'UserAnalyzerConfig',
    'UserProfile',
    'InfluenceResult',
    'ProfileGenerator',
    'InfluenceEvaluator',
    'PropagationAnalyzer',
    'get_user_analyzer',
    'generate_user_profile',
    'evaluate_user_influence',
    # 实时话题服务
    'RealtimeTopicService',
    'RealtimeConfig',
    'HotTopic',
    'TopicSnapshot',
    'DataBuffer',
    'get_realtime_topic_service',
    'start_realtime_service',
    'stop_realtime_service',
    # 实时热搜服务
    'LiveHotSearchService',
    'LiveHotSearchConfig',
    'WeiboHotSearchCrawler',
    'get_live_hot_search_service',
    'start_live_hot_search',
    'stop_live_hot_search',
    # 数据库服务
    'DatabaseService',
    'get_db_service',
]
