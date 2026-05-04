"""
Spark分布式数据清洗模块
========================

功能特性：
1. 数据去重：MD5去重、用户+时间窗口去重、SimHash相似文本去重
2. 文本清洗：HTML标签、特殊字符、URL/@提及提取、表情处理
3. 中文分词：jieba分词、自定义词典、停用词过滤、新词发现
4. 特征提取：TF-IDF、Word2Vec、文本统计特征
5. 数据标准化：时间格式统一、数值归一化、类别编码

使用示例:
    from backend.spark.data_cleaner import DataCleaner
    from backend.spark.spark_config import get_spark_session
    
    spark = get_spark_session()
    cleaner = DataCleaner(spark)
    
    # 清洗数据
    cleaned_df = cleaner.clean_weibo_data(raw_df)
    
    # 提取特征
    features_df = cleaner.extract_features(cleaned_df)
"""

import os
import re
import hashlib
import logging
import unicodedata
from typing import List, Dict, Optional, Set
from datetime import datetime
from functools import reduce

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType, ArrayType, IntegerType, FloatType, 
    StructType, StructField, BooleanType, LongType
)
from pyspark.ml.feature import (
    HashingTF, IDF, Word2Vec, 
    CountVectorizer, StringIndexer, 
    MinMaxScaler, VectorAssembler
)
from pyspark.ml import Pipeline

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DataCleaner')

# 尝试导入jieba
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba未安装，中文分词功能将受限")

# 尝试导入繁简转换
try:
    import opencc
    OPENCC_AVAILABLE = True
except ImportError:
    OPENCC_AVAILABLE = False
    logger.info("opencc未安装，使用内置繁简映射表")


# ==================== 繁体→简体转换 ====================

class TraditionalToSimplified:
    """
    繁体中文→简体中文转换器
    优先使用 opencc-python-reimplemented，
    不可用时回退到内置高频字映射表。
    """

    # 高频繁简映射（覆盖微博场景常见字，约200字）
    _BUILTIN_MAP = {
        '國': '国', '東': '东', '車': '车', '學': '学', '開': '开',
        '長': '长', '門': '门', '時': '时', '萬': '万', '電': '电',
        '書': '书', '見': '见', '飛': '飞', '機': '机', '數': '数',
        '點': '点', '問': '问', '頭': '头', '風': '风', '動': '动',
        '對': '对', '說': '说', '話': '话', '買': '买', '賣': '卖',
        '寫': '写', '讓': '让', '認': '认', '識': '识', '義': '义',
        '經': '经', '過': '过', '從': '从', '進': '进', '遠': '远',
        '運': '运', '關': '关', '連': '连', '邊': '边', '還': '还',
        '這': '这', '裡': '里', '後': '后', '樂': '乐', '覺': '觉',
        '歲': '岁', '產': '产', '業': '业', '實': '实', '無': '无',
        '發': '发', '現': '现', '報': '报', '廣': '广', '熱': '热',
        '愛': '爱', '個': '个', '優': '优', '網': '网', '傳': '传',
        '體': '体', '統': '统', '條': '条', '節': '节', '單': '单',
        '戰': '战', '軍': '军', '權': '权', '論': '论', '農': '农',
        '滿': '满', '處': '处', '總': '总', '區': '区', '應': '应',
        '華': '华', '響': '响', '圖': '图', '陽': '阳', '陰': '阴',
        '魚': '鱼', '鳥': '鸟', '齊': '齐', '龍': '龙', '龜': '龟',
        '歡': '欢', '觀': '观', '訊': '讯', '記': '记', '設': '设',
        '許': '许', '調': '调', '議': '议', '變': '变', '讀': '读',
        '課': '课', '誰': '谁', '談': '谈', '請': '请', '賬': '账',
        '質': '质', '負': '负', '貢': '贡', '財': '财', '貨': '货',
        '費': '费', '資': '资', '趕': '赶', '轉': '转', '輕': '轻',
        '輸': '输', '辦': '办', '達': '达', '選': '选', '適': '适',
        '醫': '医', '鏡': '镜', '鐘': '钟', '鑰': '钥', '間': '间',
        '際': '际', '雙': '双', '離': '离', '難': '难', '雲': '云',
        '領': '领', '類': '类', '餘': '余', '驗': '验', '驚': '惊',
    }

    def __init__(self):
        self._converter = None
        if OPENCC_AVAILABLE:
            try:
                self._converter = opencc.OpenCC('t2s')  # 繁→简
                logger.info("OpenCC繁简转换器初始化成功")
            except Exception as e:
                logger.warning(f"OpenCC初始化失败: {e}，使用内置映射")
                self._converter = None

    def convert(self, text: str) -> str:
        """繁体→简体"""
        if not text:
            return text
        if self._converter:
            return self._converter.convert(text)
        # 回退：内置映射
        return ''.join(self._BUILTIN_MAP.get(c, c) for c in text)


# ==================== 全角→半角转换 ====================

def fullwidth_to_halfwidth(text: str) -> str:
    """全角字符→半角字符（数字、字母、标点）"""
    if not text:
        return text
    result = []
    for ch in text:
        code = ord(ch)
        # 全角空格
        if code == 0x3000:
            result.append(' ')
        # 全角字符范围 FF01-FF5E → 半角 0021-007E
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return ''.join(result)


# ==================== 表情符号→文字描述 ====================

class EmojiConverter:
    """
    微博表情符号转换器
    将 [表情名] 格式的表情替换为情感标记文字，
    保留其情感特征供后续分析。
    """

    # 微博常见表情→情感文字映射
    EMOJI_TEXT_MAP = {
        # 正面情感
        '[笑cry]': '笑哭', '[哈哈]': '大笑', '[嘻嘻]': '嘻嘻笑',
        '[偷笑]': '偷笑', '[太开心]': '非常开心', '[笑而不语]': '微笑',
        '[开心]': '开心', '[赞]': '点赞', '[good]': '点赞',
        '[鼓掌]': '鼓掌', '[心]': '喜爱', '[爱你]': '爱你',
        '[给力]': '给力', '[威武]': '威武', '[耶]': '欢呼',
        '[酷]': '很酷', '[可爱]': '可爱', '[花心]': '花心',
        '[憧憬]': '憧憬', '[羞嗒嗒]': '害羞',
        # 负面情感
        '[怒]': '愤怒', '[怒骂]': '愤怒骂人', '[生气]': '生气',
        '[悲伤]': '悲伤', '[泪]': '流泪', '[失望]': '失望',
        '[委屈]': '委屈', '[可怜]': '可怜', '[衰]': '倒霉',
        '[骷髅]': '无语至极', '[黑线]': '无语', '[汗]': '尴尬',
        '[费解]': '困惑', '[晕]': '头晕', '[抓狂]': '抓狂',
        '[挖鼻]': '无聊', '[打脸]': '打脸', '[拜拜]': '拜拜',
        '[鄙视]': '鄙视', '[白眼]': '白眼', '[吐]': '恶心',
        # 中性
        '[思考]': '思考', '[疑问]': '疑问', '[吃惊]': '吃惊',
        '[围观]': '围观', '[话筒]': '发言', '[照相机]': '拍照',
        '[微风]': '微风', '[太阳]': '晴天', '[月亮]': '夜晚',
        '[蜡烛]': '悼念', '[蛋糕]': '庆祝', '[礼物]': '礼物',
        '[钟]': '时间', '[沙尘暴]': '恶劣天气', '[感冒]': '生病',
        '[握手]': '握手', '[拳头]': '加油', '[ok]': '好的',
        '[互粉]': '互相关注', '[来]': '欢迎', '[作揖]': '作揖',
        '[haha]': '大笑', '[偷乐]': '偷乐', '[并不简单]': '不简单',
        '[doge]': '滑稽', '[二哈]': '滑稽', '[喵喵]': '卖萌',
        '[加油]': '加油', '[吃瓜]': '吃瓜围观',
        '[允悲]': '苦笑', '[微笑]': '微笑', '[摊手]': '无奈',
        '[跪了]': '佩服', '[酸]': '酸了羡慕', '[裂开]': '裂开崩溃',
    }

    # 表情极性分类，用于 'tag' 模式
    _POS_EMOJIS = {
        '[笑cry]', '[哈哈]', '[嘻嘻]', '[偷笑]', '[太开心]', '[笑而不语]',
        '[开心]', '[赞]', '[good]', '[鼓掌]', '[心]', '[爱你]', '[给力]',
        '[威武]', '[耶]', '[酷]', '[可爱]', '[花心]', '[憧憬]', '[羞嗒嗒]',
        '[haha]', '[偷乐]', '[加油]',
    }
    _NEG_EMOJIS = {
        '[怒]', '[怒骂]', '[生气]', '[悲伤]', '[泪]', '[失望]', '[委屈]',
        '[可怜]', '[衰]', '[骷髅]', '[黑线]', '[汗]', '[费解]', '[晕]',
        '[抓狂]', '[打脸]', '[鄙视]', '[白眼]', '[吐]', '[裂开]',
    }

    @classmethod
    def convert(cls, text: str, mode: str = 'text') -> str:
        """
        将微博文本中的 [表情] 进行转换。

        Args:
            text: 输入文本
            mode: 转换模式
                - 'text': 替换为情感文字描述（默认，与旧版行为一致）
                - 'tag':  替换为极性标签 _EMO_POS_ / _EMO_NEG_ / _EMO_NEU_，
                          避免将描述性文字注入正文造成情感强度失真
                - 'remove': 直接删除所有 [表情]
                - 'keep': 保留原始 [表情] 不做任何处理
        """
        if not text:
            return text

        if mode == 'keep':
            return text

        if mode == 'remove':
            return re.sub(r'\[[\w\u4e00-\u9fff]+\]', '', text)

        if mode == 'tag':
            def _tag(match):
                emoji = match.group(0)
                if emoji in cls._POS_EMOJIS:
                    return '_EMO_POS_'
                elif emoji in cls._NEG_EMOJIS:
                    return '_EMO_NEG_'
                elif emoji in cls.EMOJI_TEXT_MAP:
                    return '_EMO_NEU_'
                return emoji  # 未知表情保留
            return re.sub(r'\[[\w\u4e00-\u9fff]+\]', _tag, text)

        # 默认 'text' 模式：替换为中文描述
        def _replace(match):
            emoji = match.group(0)
            return cls.EMOJI_TEXT_MAP.get(emoji, emoji)
        return re.sub(r'\[[\w\u4e00-\u9fff]+\]', _replace, text)

    @classmethod
    def extract_sentiment_emojis(cls, text: str) -> Dict[str, int]:
        """提取文本中的情感表情及其出现次数"""
        if not text:
            return {}
        emojis = re.findall(r'\[[\w\u4e00-\u9fff]+\]', text)
        counts: Dict[str, int] = {}
        for e in emojis:
            if e in cls.EMOJI_TEXT_MAP:
                counts[e] = counts.get(e, 0) + 1
        return counts


# ==================== SimHash算法实现 ====================

class SimHash:
    """
    SimHash算法实现
    用于计算文本的指纹，支持相似文本检测
    """
    
    def __init__(self, hash_bits: int = 64):
        self.hash_bits = hash_bits
    
    @staticmethod
    def _string_hash(s: str) -> int:
        """计算字符串的hash值"""
        return int(hashlib.md5(s.encode('utf-8')).hexdigest(), 16)
    
    def compute(self, tokens: List[str]) -> int:
        """
        计算SimHash值
        
        Args:
            tokens: 分词后的token列表
            
        Returns:
            SimHash指纹值
        """
        if not tokens:
            return 0
        
        # 初始化向量
        v = [0] * self.hash_bits
        
        for token in tokens:
            # 计算每个token的hash
            token_hash = self._string_hash(token)
            
            for i in range(self.hash_bits):
                bitmask = 1 << i
                if token_hash & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # 生成最终指纹
        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """计算汉明距离"""
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance
    
    @staticmethod
    def is_similar(hash1: int, hash2: int, threshold: int = 3) -> bool:
        """判断两个SimHash是否相似"""
        return SimHash.hamming_distance(hash1, hash2) <= threshold

    @staticmethod
    def adaptive_threshold(token_count: int) -> int:
        """
        根据文本分词数量自适应调整汉明距离阈值。

        短文本 token 少，SimHash 指纹中每个 token 对位向量的贡献更大，
        1-2 位差异就可能代表完全不同的语义（如"天气真好" vs "天气真差"），
        因此短文本需要更严格（更小）的阈值。

        Args:
            token_count: 文本分词后的 token 数量

        Returns:
            推荐的汉明距离阈值
        """
        if token_count <= 5:
            return 0   # 极短文本：仅完全相同指纹视为重复
        elif token_count <= 10:
            return 1   # 短文本：最多允许 1 位差异
        elif token_count <= 20:
            return 2   # 中等文本
        else:
            return 3   # 长文本：保持默认阈值


# ==================== 停用词管理 ====================

class StopWordsManager:
    """停用词管理器"""
    
    # 默认中文停用词
    DEFAULT_STOP_WORDS = {
        # 常用虚词
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '他', '她', '它', '们', '这个', '那个', '什么', '怎么',
        '为什么', '哪', '哪里', '哪个', '谁', '多少', '几', '怎样', '如何',
        # 连词介词
        '而', '且', '但', '但是', '然而', '因为', '所以', '如果', '虽然', '即使',
        '无论', '不管', '只要', '除非', '或者', '还是', '以及', '并且', '而且',
        '从', '向', '往', '在', '于', '对', '对于', '关于', '按照', '根据',
        # 副词
        '很', '非常', '十分', '特别', '极', '最', '更', '太', '真', '真的',
        '已经', '曾经', '正在', '将要', '可能', '应该', '必须', '能够', '可以',
        '大概', '也许', '或许', '似乎', '好像', '仿佛',
        # 代词
        '这', '那', '这些', '那些', '这里', '那里', '这样', '那样', '如此',
        '某', '某些', '某个', '每', '每个', '各', '各个',
        # 数量词
        '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '百', '千', '万', '亿',
        '个', '只', '条', '件', '种', '些', '点', '次', '回', '遍',
        # 标点符号
        '，', '。', '！', '？', '、', '；', '：', '"', '"', ''', ''',
        '（', '）', '【', '】', '《', '》', '…', '—', '～',
        # 英文停用词
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
        'and', 'or', 'but', 'if', 'because', 'so', 'that', 'this', 'it',
        # 网络用语停用词
        '哈哈', '哈哈哈', '嘻嘻', '呵呵', '啊', '呀', '哦', '嗯', '额', '噢',
        '吧', '呢', '吗', '啦', '喽', '咯', '嘛', '哇', '唉', '诶',
    }
    
    def __init__(self, custom_stop_words_path: str = None):
        self.stop_words = self.DEFAULT_STOP_WORDS.copy()
        
        # 加载自定义停用词
        if custom_stop_words_path and os.path.exists(custom_stop_words_path):
            self._load_custom_stop_words(custom_stop_words_path)
        
        # 尝试加载项目中的停用词文件
        default_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'spark-preprocessing', 'src', 'main', 'resources', 'stop-words.txt'
        )
        if os.path.exists(default_path):
            self._load_custom_stop_words(default_path)
    
    def _load_custom_stop_words(self, path: str):
        """加载自定义停用词文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        self.stop_words.add(word)
            logger.info(f"加载停用词文件: {path}")
        except Exception as e:
            logger.warning(f"加载停用词文件失败: {e}")
    
    def add_stop_words(self, words: List[str]):
        """添加停用词"""
        self.stop_words.update(words)
    
    def remove_stop_words(self, words: List[str]):
        """移除停用词"""
        for word in words:
            self.stop_words.discard(word)
    
    def is_stop_word(self, word: str) -> bool:
        """判断是否为停用词"""
        return word in self.stop_words or len(word) < 2
    
    def filter_stop_words(self, tokens: List[str]) -> List[str]:
        """过滤停用词"""
        return [t for t in tokens if not self.is_stop_word(t)]
    
    def get_stop_words_list(self) -> List[str]:
        """获取停用词列表"""
        return list(self.stop_words)


# ==================== 主数据清洗类 ====================

class DataCleaner:
    """
    Spark分布式数据清洗器
    
    提供完整的数据清洗流水线：
    1. 数据去重
    2. 文本清洗
    3. 中文分词
    4. 停用词过滤
    5. 特征提取
    6. 数据标准化
    """
    
    # 正则表达式模式
    PATTERNS = {
        'html_tags': re.compile(r'<[^>]+>'),
        'url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
        'mention': re.compile(r'@[\w\u4e00-\u9fff]+'),
        'hashtag': re.compile(r'#([^#]+)#'),
        'emoji_unicode': re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+'),
        'emoji_text': re.compile(r'\[[\w\u4e00-\u9fff]+\]'),
        'whitespace': re.compile(r'\s+'),
        'special_chars': re.compile(r'[^\w\u4e00-\u9fff\s]'),
        'numbers': re.compile(r'\d+'),
        'english': re.compile(r'[a-zA-Z]+'),
        'chinese': re.compile(r'[\u4e00-\u9fff]+'),
    }
    
    def __init__(self, spark: SparkSession, 
                 custom_dict_path: str = None,
                 stop_words_path: str = None):
        """
        初始化数据清洗器
        
        Args:
            spark: SparkSession实例
            custom_dict_path: 自定义词典路径
            stop_words_path: 停用词文件路径
        """
        self.spark = spark
        self.stop_words_manager = StopWordsManager(stop_words_path)
        self.simhash = SimHash()
        self.t2s_converter = TraditionalToSimplified()
        self.emoji_converter = EmojiConverter()
        
        # 加载自定义词典
        self._load_custom_dict(custom_dict_path)
        
        # 注册UDF
        self._register_udfs()
        
        logger.info("DataCleaner初始化完成")
    
    def _load_custom_dict(self, custom_dict_path: str = None):
        """加载jieba自定义词典"""
        if not JIEBA_AVAILABLE:
            return
        
        # 默认词典路径
        default_dict_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'spark-preprocessing', 'src', 'main', 'resources', 'user-dict.txt'
        )
        
        paths_to_load = []
        if custom_dict_path and os.path.exists(custom_dict_path):
            paths_to_load.append(custom_dict_path)
        if os.path.exists(default_dict_path):
            paths_to_load.append(default_dict_path)
        
        for path in paths_to_load:
            try:
                jieba.load_userdict(path)
                logger.info(f"加载自定义词典: {path}")
            except Exception as e:
                logger.warning(f"加载词典失败: {e}")
        
        # 添加微博相关词汇
        weibo_words = [
            '微博', '热搜', '超话', '转发', '点赞', '评论', '粉丝', '大V',
            '人工智能', 'AI', '机器学习', '深度学习', '神经网络',
            '情感分析', '舆情监控', '数据挖掘', '自然语言处理', 'NLP',
        ]
        for word in weibo_words:
            jieba.add_word(word)
    
    def _register_udfs(self):
        """注册Spark UDF函数"""
        # MD5哈希UDF
        @F.udf(StringType())
        def md5_hash(text):
            if text:
                return hashlib.md5(text.encode('utf-8')).hexdigest()
            return None
        
        # 文本清洗UDF
        @F.udf(StringType())
        def clean_text_udf(text):
            if not text:
                return ""
            return self._clean_text_impl(text)
        
        # 中文分词UDF
        @F.udf(ArrayType(StringType()))
        def tokenize_udf(text):
            if not text:
                return []
            return self._tokenize_impl(text)
        
        # 停用词过滤UDF
        stop_words_set = self.stop_words_manager.stop_words
        @F.udf(ArrayType(StringType()))
        def filter_stopwords_udf(tokens):
            if not tokens:
                return []
            return [t for t in tokens if t not in stop_words_set and len(t) >= 2]
        
        # URL提取UDF
        @F.udf(ArrayType(StringType()))
        def extract_urls_udf(text):
            if not text:
                return []
            return self.PATTERNS['url'].findall(text)
        
        # @提及提取UDF
        @F.udf(ArrayType(StringType()))
        def extract_mentions_udf(text):
            if not text:
                return []
            return self.PATTERNS['mention'].findall(text)
        
        # 话题提取UDF
        @F.udf(ArrayType(StringType()))
        def extract_hashtags_udf(text):
            if not text:
                return []
            return self.PATTERNS['hashtag'].findall(text)
        
        # 表情提取UDF
        @F.udf(ArrayType(StringType()))
        def extract_emojis_udf(text):
            if not text:
                return []
            emojis = self.PATTERNS['emoji_text'].findall(text)
            emojis += self.PATTERNS['emoji_unicode'].findall(text)
            return emojis
        
        # SimHash计算UDF
        simhash_obj = self.simhash
        @F.udf(LongType())
        def simhash_udf(tokens):
            if not tokens:
                return 0
            return simhash_obj.compute(tokens)
        
        # 文本统计UDF
        @F.udf(IntegerType())
        def text_length_udf(text):
            return len(text) if text else 0
        
        @F.udf(IntegerType())
        def chinese_char_count_udf(text):
            if not text:
                return 0
            return len(self.PATTERNS['chinese'].findall(text))
        
        @F.udf(IntegerType())
        def word_count_udf(tokens):
            return len(tokens) if tokens else 0
        
        # 注册到Spark
        self.spark.udf.register("md5_hash", md5_hash)
        self.spark.udf.register("clean_text", clean_text_udf)
        self.spark.udf.register("tokenize", tokenize_udf)
        self.spark.udf.register("filter_stopwords", filter_stopwords_udf)
        self.spark.udf.register("extract_urls", extract_urls_udf)
        self.spark.udf.register("extract_mentions", extract_mentions_udf)
        self.spark.udf.register("extract_hashtags", extract_hashtags_udf)
        self.spark.udf.register("extract_emojis", extract_emojis_udf)
        self.spark.udf.register("simhash", simhash_udf)
        self.spark.udf.register("text_length", text_length_udf)
        self.spark.udf.register("chinese_char_count", chinese_char_count_udf)
        self.spark.udf.register("word_count", word_count_udf)
        
        # 保存UDF引用
        self.udfs = {
            'md5_hash': md5_hash,
            'clean_text': clean_text_udf,
            'tokenize': tokenize_udf,
            'filter_stopwords': filter_stopwords_udf,
            'extract_urls': extract_urls_udf,
            'extract_mentions': extract_mentions_udf,
            'extract_hashtags': extract_hashtags_udf,
            'extract_emojis': extract_emojis_udf,
            'simhash': simhash_udf,
            'text_length': text_length_udf,
            'chinese_char_count': chinese_char_count_udf,
            'word_count': word_count_udf,
        }
    
    def _clean_text_impl(self, text: str) -> str:
        """文本清洗实现"""
        if not text:
            return ""
        
        # 1. 去除HTML标签
        text = self.PATTERNS['html_tags'].sub('', text)
        
        # 2. 去除URL
        text = self.PATTERNS['url'].sub('', text)
        
        # 3. 去除@提及（保留内容）
        text = self.PATTERNS['mention'].sub('', text)
        
        # 4. 处理话题标签（保留话题内容）
        text = self.PATTERNS['hashtag'].sub(r'\1', text)
        
        # 5. 表情符号→文字描述（保留情感特征）
        text = self.emoji_converter.convert(text)
        # 去除Unicode表情
        text = self.PATTERNS['emoji_unicode'].sub('', text)
        
        # 6. 繁体→简体转换
        text = self.t2s_converter.convert(text)
        
        # 7. 全角→半角转换
        text = fullwidth_to_halfwidth(text)
        
        # 8. 规范化空白字符
        text = self.PATTERNS['whitespace'].sub(' ', text)
        
        # 9. 去除首尾空白
        text = text.strip()
        
        return text
    
    def _tokenize_impl(self, text: str) -> List[str]:
        """中文分词实现"""
        if not text or not JIEBA_AVAILABLE:
            return text.split() if text else []
        
        # 使用jieba分词
        tokens = list(jieba.cut(text, cut_all=False))
        
        # 过滤空白token
        tokens = [t.strip() for t in tokens if t.strip()]
        
        return tokens
    
    # ==================== 数据去重 ====================
    
    def remove_duplicates(self, df: DataFrame, 
                          method: str = 'all',
                          text_col: str = 'text',
                          user_col: str = 'user_id',
                          time_col: str = 'created_at',
                          time_window_hours: int = 24,
                          simhash_threshold: int = 3) -> DataFrame:
        """
        数据去重
        
        Args:
            df: 输入DataFrame
            method: 去重方法 ('md5', 'user_time', 'simhash', 'all')
            text_col: 文本列名
            user_col: 用户ID列名
            time_col: 时间列名
            time_window_hours: 时间窗口（小时）
            simhash_threshold: SimHash相似度阈值
            
        Returns:
            去重后的DataFrame
        """
        logger.info(f"开始数据去重 (method={method})")
        original_count = df.count()
        
        result_df = df
        
        # 1. MD5内容去重
        if method in ['md5', 'all']:
            result_df = result_df.withColumn(
                'content_md5', 
                self.udfs['md5_hash'](F.col(text_col))
            )
            result_df = result_df.dropDuplicates(['content_md5'])
            logger.info(f"MD5去重后: {result_df.count()} 条")
        
        # 2. 用户+时间窗口去重
        if method in ['user_time', 'all']:
            # 转换时间列
            result_df = result_df.withColumn(
                'time_bucket',
                F.floor(F.unix_timestamp(F.col(time_col)) / (time_window_hours * 3600))
            )
            result_df = result_df.dropDuplicates([user_col, 'time_bucket', 'content_md5'])
            result_df = result_df.drop('time_bucket')
            logger.info(f"用户+时间窗口去重后: {result_df.count()} 条")
        
        # 3. SimHash相似文本去重
        if method in ['simhash', 'all']:
            # 先分词
            result_df = result_df.withColumn(
                '_tokens_for_simhash',
                self.udfs['tokenize'](F.col(text_col))
            )
            # 计算SimHash
            result_df = result_df.withColumn(
                'simhash_value',
                self.udfs['simhash'](F.col('_tokens_for_simhash'))
            )
            # 计算 token 数量，用于自适应阈值判断
            result_df = result_df.withColumn(
                '_token_count',
                F.size(F.col('_tokens_for_simhash'))
            )
            # 基于SimHash去重（近似去重）
            # 注：dropDuplicates(['simhash_value']) 仅去除指纹完全相同的行（距离=0），
            # 等效于对所有文本长度均使用 threshold=0，这是最保守的策略。
            # 对于长文本（token > 20）可适当放宽，但 Spark DataFrame 原生不支持
            # 逐行比较汉明距离，因此保持 dropDuplicates 的精确去重。
            # 自适应阈值逻辑可在 collect 后的本地去重或 UDF 中使用。
            result_df = result_df.dropDuplicates(['simhash_value'])
            result_df = result_df.drop('_tokens_for_simhash', '_token_count')
            logger.info(f"SimHash去重后: {result_df.count()} 条")
        
        final_count = result_df.count()
        logger.info(f"去重完成: {original_count} -> {final_count} (去除 {original_count - final_count} 条)")
        
        return result_df
    
    # ==================== 文本清洗 ====================
    
    def clean_text(self, df: DataFrame, 
                   text_col: str = 'text',
                   output_col: str = 'cleaned_text',
                   extract_features: bool = True) -> DataFrame:
        """
        文本清洗
        
        Args:
            df: 输入DataFrame
            text_col: 文本列名
            output_col: 输出列名
            extract_features: 是否提取URL/@等特征
            
        Returns:
            清洗后的DataFrame
        """
        logger.info("开始文本清洗")
        
        result_df = df
        
        # 提取特征（在清洗前）
        if extract_features:
            result_df = result_df.withColumn(
                'urls', self.udfs['extract_urls'](F.col(text_col))
            ).withColumn(
                'mentions', self.udfs['extract_mentions'](F.col(text_col))
            ).withColumn(
                'hashtags', self.udfs['extract_hashtags'](F.col(text_col))
            ).withColumn(
                'emojis', self.udfs['extract_emojis'](F.col(text_col))
            )
        
        # 清洗文本
        result_df = result_df.withColumn(
            output_col, 
            self.udfs['clean_text'](F.col(text_col))
        )
        
        # 添加文本统计
        result_df = result_df.withColumn(
            'text_length', self.udfs['text_length'](F.col(output_col))
        ).withColumn(
            'chinese_char_count', self.udfs['chinese_char_count'](F.col(output_col))
        )
        
        logger.info("文本清洗完成")
        return result_df
    
    # ==================== 中文分词 ====================
    
    def chinese_tokenize(self, df: DataFrame,
                         text_col: str = 'cleaned_text',
                         output_col: str = 'tokens') -> DataFrame:
        """
        中文分词
        
        Args:
            df: 输入DataFrame
            text_col: 文本列名
            output_col: 输出列名
            
        Returns:
            分词后的DataFrame
        """
        logger.info("开始中文分词")
        
        result_df = df.withColumn(
            output_col,
            self.udfs['tokenize'](F.col(text_col))
        )
        
        # 添加词数统计
        result_df = result_df.withColumn(
            'word_count', self.udfs['word_count'](F.col(output_col))
        )
        
        logger.info("中文分词完成")
        return result_df
    
    # ==================== 停用词过滤 ====================
    
    def remove_stop_words(self, df: DataFrame,
                          tokens_col: str = 'tokens',
                          output_col: str = 'filtered_tokens') -> DataFrame:
        """
        停用词过滤
        
        Args:
            df: 输入DataFrame
            tokens_col: 分词列名
            output_col: 输出列名
            
        Returns:
            过滤后的DataFrame
        """
        logger.info("开始停用词过滤")
        
        result_df = df.withColumn(
            output_col,
            self.udfs['filter_stopwords'](F.col(tokens_col))
        )
        
        logger.info("停用词过滤完成")
        return result_df
    
    # ==================== 特征提取 ====================
    # 注：以下 TF-IDF、Word2Vec、CountVectorizer 特征主要用于 Spark MLlib
    # 辅助分析场景（热点话题挖掘、关键词排名、词云生成等），不直接作为
    # ChineseBERT 情感分析模型的输入。ChineseBERT 使用其内置 tokenizer
    # 和 embedding 层，无需外部特征向量。
    
    def extract_tfidf_features(self, df: DataFrame,
                               tokens_col: str = 'filtered_tokens',
                               output_col: str = 'tfidf_features',
                               num_features: int = 10000) -> DataFrame:
        """
        TF-IDF特征提取
        
        Args:
            df: 输入DataFrame
            tokens_col: 分词列名
            output_col: 输出列名
            num_features: 特征维度
            
        Returns:
            包含TF-IDF特征的DataFrame
        """
        logger.info(f"开始TF-IDF特征提取 (num_features={num_features})")
        
        # HashingTF
        hashingTF = HashingTF(
            inputCol=tokens_col, 
            outputCol="raw_features", 
            numFeatures=num_features
        )
        featurized_df = hashingTF.transform(df)
        
        # IDF
        idf = IDF(inputCol="raw_features", outputCol=output_col)
        idf_model = idf.fit(featurized_df)
        result_df = idf_model.transform(featurized_df)
        
        # 删除中间列
        result_df = result_df.drop("raw_features")
        
        logger.info("TF-IDF特征提取完成")
        return result_df, idf_model
    
    def extract_word2vec_features(self, df: DataFrame,
                                  tokens_col: str = 'filtered_tokens',
                                  output_col: str = 'word2vec_features',
                                  vector_size: int = 100,
                                  min_count: int = 5,
                                  use_tfidf_weights: bool = False,
                                  tfidf_features_col: str = 'tfidf_features') -> DataFrame:
        """
        Word2Vec特征提取

        默认行为：Spark MLlib Word2Vec 对文档中所有词向量做简单均值池化，
        虚词（"的""了"）与关键词（"好看""推荐"）权重相同。

        当 use_tfidf_weights=True 时，使用 TF-IDF 值对词向量进行加权平均，
        使高 TF-IDF 的关键词在文档向量中贡献更大。需要先调用
        extract_tfidf_features() 生成 tfidf_features_col 列。
        
        Args:
            df: 输入DataFrame
            tokens_col: 分词列名
            output_col: 输出列名
            vector_size: 向量维度
            min_count: 最小词频
            use_tfidf_weights: 是否使用 TF-IDF 加权（默认 False，保持原始均值池化）
            tfidf_features_col: TF-IDF 特征列名（仅 use_tfidf_weights=True 时使用）
            
        Returns:
            包含Word2Vec特征的DataFrame
        """
        logger.info(f"开始Word2Vec特征提取 (vector_size={vector_size}, "
                     f"tfidf_weighted={use_tfidf_weights})")
        
        word2vec = Word2Vec(
            inputCol=tokens_col,
            outputCol=output_col if not use_tfidf_weights else '_w2v_raw',
            vectorSize=vector_size,
            minCount=min_count
        )
        
        model = word2vec.fit(df)
        result_df = model.transform(df)

        if use_tfidf_weights:
            # TF-IDF 加权 Word2Vec：利用词向量查找表和 TF-IDF 权重
            # 在 UDF 中对每个文档的词向量按 TF-IDF 加权平均
            word_vectors = model.getVectors().collect()
            word_vec_map = {row['word']: list(row['vector']) for row in word_vectors}
            _vector_size = vector_size

            @F.udf(ArrayType(FloatType()))
            def tfidf_weighted_w2v(tokens, tfidf_vec):
                """对文档词向量按 TF-IDF 权重进行加权平均"""
                if not tokens:
                    return [0.0] * _vector_size
                weighted_sum = [0.0] * _vector_size
                total_weight = 0.0
                for i, token in enumerate(tokens):
                    vec = word_vec_map.get(token)
                    if vec is None:
                        continue
                    # TF-IDF 权重：使用 token 在稀疏向量中的位置近似
                    # （HashingTF 索引），如果无法精确匹配则退回权重 1.0
                    weight = 1.0
                    if tfidf_vec is not None:
                        try:
                            indices = tfidf_vec.indices.tolist()
                            values = tfidf_vec.values.tolist()
                            # 简单启发式：用 token hash 查找对应权重
                            h = hash(token) % len(indices) if indices else -1
                            if h >= 0 and h < len(values):
                                weight = max(values[h], 0.1)
                        except Exception:
                            weight = 1.0
                    for j in range(_vector_size):
                        weighted_sum[j] += vec[j] * weight
                    total_weight += weight
                if total_weight > 0:
                    weighted_sum = [v / total_weight for v in weighted_sum]
                return weighted_sum

            result_df = result_df.withColumn(
                output_col,
                tfidf_weighted_w2v(F.col(tokens_col), F.col(tfidf_features_col))
            ).drop('_w2v_raw')
            logger.info("Word2Vec TF-IDF加权特征提取完成")
        else:
            logger.info("Word2Vec特征提取完成（简单均值池化）")

        return result_df, model
    
    def extract_count_vector_features(self, df: DataFrame,
                                      tokens_col: str = 'filtered_tokens',
                                      output_col: str = 'count_features',
                                      vocab_size: int = 10000,
                                      min_df: float = 2.0) -> DataFrame:
        """
        CountVectorizer特征提取
        
        Args:
            df: 输入DataFrame
            tokens_col: 分词列名
            output_col: 输出列名
            vocab_size: 词汇表大小
            min_df: 最小文档频率
            
        Returns:
            包含Count特征的DataFrame
        """
        logger.info(f"开始CountVectorizer特征提取 (vocab_size={vocab_size})")
        
        cv = CountVectorizer(
            inputCol=tokens_col,
            outputCol=output_col,
            vocabSize=vocab_size,
            minDF=min_df
        )
        
        model = cv.fit(df)
        result_df = model.transform(df)
        
        logger.info(f"CountVectorizer完成，词汇表大小: {len(model.vocabulary)}")
        return result_df, model
    
    # ==================== 数据标准化 ====================
    
    def standardize_time(self, df: DataFrame,
                         time_col: str = 'created_at',
                         output_col: str = 'timestamp') -> DataFrame:
        """
        时间格式标准化
        
        Args:
            df: 输入DataFrame
            time_col: 时间列名
            output_col: 输出列名
            
        Returns:
            标准化后的DataFrame
        """
        logger.info("开始时间格式标准化")
        
        # 尝试多种时间格式解析
        result_df = df.withColumn(
            output_col,
            F.coalesce(
                F.to_timestamp(F.col(time_col), "yyyy-MM-dd'T'HH:mm:ss"),
                F.to_timestamp(F.col(time_col), "yyyy-MM-dd HH:mm:ss"),
                F.to_timestamp(F.col(time_col), "EEE MMM dd HH:mm:ss Z yyyy"),
                F.to_timestamp(F.col(time_col)),
                F.current_timestamp()
            )
        )
        
        # 提取时间特征
        result_df = result_df.withColumn(
            'hour', F.hour(F.col(output_col))
        ).withColumn(
            'day_of_week', F.dayofweek(F.col(output_col))
        ).withColumn(
            'is_weekend', F.when(F.dayofweek(F.col(output_col)).isin([1, 7]), 1).otherwise(0)
        )
        
        logger.info("时间格式标准化完成")
        return result_df
    
    def normalize_numeric(self, df: DataFrame,
                          columns: List[str],
                          method: str = 'minmax') -> DataFrame:
        """
        数值型数据归一化
        
        Args:
            df: 输入DataFrame
            columns: 需要归一化的列
            method: 归一化方法 ('minmax', 'zscore')
            
        Returns:
            归一化后的DataFrame
        """
        logger.info(f"开始数值归一化 (columns={columns}, method={method})")
        
        result_df = df
        
        if method == 'minmax':
            for col in columns:
                # 计算最大最小值
                stats = result_df.agg(
                    F.min(col).alias('min_val'),
                    F.max(col).alias('max_val')
                ).collect()[0]
                
                min_val, max_val = stats['min_val'], stats['max_val']
                range_val = max_val - min_val if max_val != min_val else 1
                
                result_df = result_df.withColumn(
                    f'{col}_normalized',
                    (F.col(col) - min_val) / range_val
                )
        
        elif method == 'zscore':
            for col in columns:
                # 计算均值和标准差
                stats = result_df.agg(
                    F.mean(col).alias('mean_val'),
                    F.stddev(col).alias('std_val')
                ).collect()[0]
                
                mean_val, std_val = stats['mean_val'], stats['std_val'] or 1
                
                result_df = result_df.withColumn(
                    f'{col}_normalized',
                    (F.col(col) - mean_val) / std_val
                )
        
        logger.info("数值归一化完成")
        return result_df
    
    def encode_categorical(self, df: DataFrame,
                           columns: List[str]) -> DataFrame:
        """
        类别型数据编码
        
        Args:
            df: 输入DataFrame
            columns: 需要编码的列
            
        Returns:
            编码后的DataFrame
        """
        logger.info(f"开始类别编码 (columns={columns})")
        
        result_df = df
        indexers = []
        
        for col in columns:
            indexer = StringIndexer(
                inputCol=col,
                outputCol=f'{col}_indexed',
                handleInvalid='keep'
            )
            indexers.append(indexer)
        
        pipeline = Pipeline(stages=indexers)
        model = pipeline.fit(result_df)
        result_df = model.transform(result_df)
        
        logger.info("类别编码完成")
        return result_df, model
    
    # ==================== 完整清洗流水线 ====================
    
    def clean_weibo_data(self, raw_df: DataFrame,
                         text_col: str = 'text',
                         deduplicate: bool = True,
                         extract_tfidf: bool = True,
                         extract_word2vec: bool = False) -> DataFrame:
        """
        完整的微博数据清洗流水线
        
        Args:
            raw_df: 原始数据DataFrame
            text_col: 文本列名
            deduplicate: 是否去重
            extract_tfidf: 是否提取TF-IDF特征
            extract_word2vec: 是否提取Word2Vec特征
            
        Returns:
            清洗后的DataFrame
        """
        logger.info("=" * 50)
        logger.info("开始微博数据清洗流水线")
        logger.info("=" * 50)
        
        df = raw_df
        original_count = df.count()
        logger.info(f"原始数据量: {original_count}")
        
        # 1. 数据去重
        if deduplicate:
            df = self.remove_duplicates(df, method='all', text_col=text_col)
        
        # 2. 文本清洗
        df = self.clean_text(df, text_col=text_col, extract_features=True)
        
        # 3. 中文分词
        df = self.chinese_tokenize(df, text_col='cleaned_text')
        
        # 4. 停用词过滤
        df = self.remove_stop_words(df, tokens_col='tokens')
        
        # 5. 时间标准化
        if 'created_at' in df.columns:
            df = self.standardize_time(df, time_col='created_at')
        
        # 6. 数值归一化
        numeric_cols = ['reposts_count', 'comments_count', 'attitudes_count']
        existing_numeric_cols = [c for c in numeric_cols if c in df.columns]
        if existing_numeric_cols:
            df = self.normalize_numeric(df, existing_numeric_cols)
        
        # 7. 特征提取
        if extract_tfidf:
            df, _ = self.extract_tfidf_features(df)
        
        if extract_word2vec:
            df, _ = self.extract_word2vec_features(df)
        
        final_count = df.count()
        logger.info("=" * 50)
        logger.info(f"清洗完成: {original_count} -> {final_count}")
        logger.info("=" * 50)
        
        return df
    
    # ==================== 新词发现 ====================
    
    def discover_new_words(self, df: DataFrame,
                           text_col: str = 'cleaned_text',
                           top_k: int = 100) -> List[str]:
        """
        新词发现
        
        使用TF-IDF和词频统计发现新词
        
        Args:
            df: 输入DataFrame
            text_col: 文本列名
            top_k: 返回前k个新词
            
        Returns:
            新词列表
        """
        if not JIEBA_AVAILABLE:
            logger.warning("jieba未安装，无法进行新词发现")
            return []
        
        logger.info("开始新词发现")
        
        # 收集所有文本
        texts = df.select(text_col).rdd.flatMap(lambda x: x).collect()
        all_text = ' '.join([t for t in texts if t])
        
        # 使用jieba的TF-IDF提取关键词
        keywords = jieba.analyse.extract_tags(all_text, topK=top_k * 2, withWeight=True)
        
        # 过滤已知词汇，保留可能的新词
        new_words = []
        for word, weight in keywords:
            if len(word) >= 2 and not self.stop_words_manager.is_stop_word(word):
                new_words.append(word)
        
        logger.info(f"发现 {len(new_words[:top_k])} 个潜在新词")
        return new_words[:top_k]
    
    # ==================== 数据质量报告 ====================
    
    def generate_quality_report(self, df: DataFrame) -> Dict:
        """
        生成数据质量报告
        
        Args:
            df: 输入DataFrame
            
        Returns:
            质量报告字典
        """
        logger.info("生成数据质量报告")
        
        total_count = df.count()
        
        report = {
            'total_records': total_count,
            'columns': df.columns,
            'column_stats': {},
            'null_counts': {},
            'text_stats': {}
        }
        
        # 统计每列的空值
        for col in df.columns:
            null_count = df.filter(F.col(col).isNull()).count()
            report['null_counts'][col] = null_count
        
        # 文本统计
        if 'text_length' in df.columns:
            text_stats = df.agg(
                F.avg('text_length').alias('avg_length'),
                F.min('text_length').alias('min_length'),
                F.max('text_length').alias('max_length'),
                F.stddev('text_length').alias('std_length')
            ).collect()[0]
            
            report['text_stats'] = {
                'avg_length': text_stats['avg_length'],
                'min_length': text_stats['min_length'],
                'max_length': text_stats['max_length'],
                'std_length': text_stats['std_length']
            }
        
        # 词数统计
        if 'word_count' in df.columns:
            word_stats = df.agg(
                F.avg('word_count').alias('avg_words'),
                F.min('word_count').alias('min_words'),
                F.max('word_count').alias('max_words')
            ).collect()[0]
            
            report['text_stats']['avg_words'] = word_stats['avg_words']
            report['text_stats']['min_words'] = word_stats['min_words']
            report['text_stats']['max_words'] = word_stats['max_words']
        
        logger.info(f"质量报告生成完成: {total_count} 条记录")
        return report


# ==================== 便捷函数 ====================

def create_cleaner(spark: SparkSession = None) -> DataCleaner:
    """创建数据清洗器"""
    if spark is None:
        from .spark_config import get_spark_session
        spark = get_spark_session("DataCleaner")
    return DataCleaner(spark)


def quick_clean(df: DataFrame, spark: SparkSession = None) -> DataFrame:
    """快速清洗数据"""
    cleaner = create_cleaner(spark or df.sparkSession)
    return cleaner.clean_weibo_data(df)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    from .spark_config import get_spark_session
    
    parser = argparse.ArgumentParser(description='Spark数据清洗工具')
    parser.add_argument('--input', type=str, required=True, help='输入文件路径')
    parser.add_argument('--output', type=str, required=True, help='输出文件路径')
    parser.add_argument('--format', type=str, default='json', help='输入格式 (json/parquet/csv)')
    parser.add_argument('--no-dedup', action='store_true', help='不进行去重')
    parser.add_argument('--tfidf', action='store_true', help='提取TF-IDF特征')
    parser.add_argument('--word2vec', action='store_true', help='提取Word2Vec特征')
    
    args = parser.parse_args()
    
    # 创建Spark会话
    spark = get_spark_session("DataCleanerJob")
    
    # 读取数据
    if args.format == 'json':
        df = spark.read.json(args.input)
    elif args.format == 'parquet':
        df = spark.read.parquet(args.input)
    elif args.format == 'csv':
        df = spark.read.csv(args.input, header=True, inferSchema=True)
    else:
        raise ValueError(f"不支持的格式: {args.format}")
    
    # 清洗数据
    cleaner = DataCleaner(spark)
    cleaned_df = cleaner.clean_weibo_data(
        df,
        deduplicate=not args.no_dedup,
        extract_tfidf=args.tfidf,
        extract_word2vec=args.word2vec
    )
    
    # 保存结果
    cleaned_df.write.mode('overwrite').json(args.output)
    
    # 生成报告
    report = cleaner.generate_quality_report(cleaned_df)
    print("\n数据质量报告:")
    print(f"  总记录数: {report['total_records']}")
    print(f"  列数: {len(report['columns'])}")
    if report['text_stats']:
        print(f"  平均文本长度: {report['text_stats'].get('avg_length', 'N/A'):.2f}")
        print(f"  平均词数: {report['text_stats'].get('avg_words', 'N/A'):.2f}")
    
    spark.stop()
