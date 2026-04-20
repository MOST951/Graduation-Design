# 第5章 数据集准备 - 数据处理流程图

## 5.1 数据集处理流程图

```mermaid
flowchart TD
    A[数据采集<br/>Data Collection] --> B[数据清洗<br/>Data Cleaning]
    B --> C[中文分词<br/>Chinese Segmentation]
    C --> D[特征提取<br/>Feature Extraction]
    D --> E[数据标注<br/>Data Labeling]
    E --> F[数据划分<br/>Data Splitting]
    F --> G[数据存储<br/>Data Storage]
    
    subgraph "数据采集详细流程"
        A1[关键词配置<br/>Keyword Configuration]
        A2[微博API调用<br/>Weibo API Calls]
        A3[增量去重<br/>Deduplication]
        A4[实时流处理<br/>Real-time Stream]
        A5[数据验证<br/>Data Validation]
    end
    
    subgraph "数据清洗详细流程"
        B1[HTML标签去除<br/>HTML Tag Removal]
        B2[特殊字符处理<br/>Special Character Processing]
        B3[繁简转换<br/>Traditional-Simplified Conversion]
        B4[表情符号处理<br/>Emoji Processing]
        B5[URL链接处理<br/>URL Link Processing]
        B6[重复内容检测<br/>Duplicate Content Detection]
    end
    
    subgraph "中文分词详细流程"
        C1[自定义词典加载<br/>Custom Dictionary Loading]
        C2[Jieba分词<br/>Jieba Segmentation]
        C3[停用词过滤<br/>Stopword Filtering]
        C4[词性标注<br/>Part-of-Speech Tagging]
        C5[分词结果验证<br/>Segmentation Validation]
    end
    
    subgraph "特征提取详细流程"
        D1[词向量提取<br/>Word Vector Extraction]
        D2[统计特征计算<br/>Statistical Feature Calculation]
        D3[情感特征构建<br/>Sentiment Feature Construction]
        D4[热度特征计算<br/>Popularity Feature Calculation]
        D5[时间特征编码<br/>Time Feature Encoding]
    end
    
    subgraph "数据标注详细流程"
        E1[人工标注<br/>Manual Labeling]
        E2[词典标注<br/>Dictionary Labeling]
        E3[半自动标注<br/>Semi-automatic Labeling]
        E4[标注一致性检查<br/>Label Consistency Check]
        E5[标注质量评估<br/>Label Quality Assessment]
    end
    
    subgraph "数据划分详细流程"
        F1[训练集<br/>Training Set<br/>70%]
        F2[验证集<br/>Validation Set<br/>15%]
        F3[测试集<br/>Test Set<br/>15%]
        F4[分层抽样<br/>Stratified Sampling]
        F5[时间序列划分<br/>Time Series Splitting]
    end
    
    A --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    
    B --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> B5
    B5 --> B6
    
    C --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    
    D --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    
    E --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> E5
    
    F --> F1
    F --> F2
    F --> F3
    F1 --> F4
    F2 --> F4
    F3 --> F4
    F4 --> F5
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#f1f8e9
    style G fill:#e1f5fe
```

## 5.2 数据采集详细流程

### 5.2.1 微博数据采集架构

```mermaid
graph TD
    subgraph "数据源 Data Sources"
        S1[微博搜索API<br/>Search API]
        S2[微博用户时间线<br/>User Timeline]
        S3[微博热门话题<br/>Hot Topics]
        S4[实时流接口<br/>Streaming API]
    end
    
    subgraph "采集层 Collection Layer"
        C1[关键词采集器<br/>Keyword Collector]
        C2[用户采集器<br/>User Collector]
        C3[热门采集器<br/>Hot Topics Collector]
        C4[流式采集器<br/>Stream Collector]
    end
    
    subgraph "处理层 Processing Layer"
        P1[数据验证器<br/>Data Validator]
        P2[去重处理器<br/>Deduplication Processor]
        P3[格式转换器<br/>Format Converter]
        P4[质量检查器<br/>Quality Checker]
    end
    
    subgraph "存储层 Storage Layer"
        ST1[原始数据存储<br/>Raw Data Storage]
        ST2[元数据存储<br/>Metadata Storage]
        ST3[索引存储<br/>Index Storage]
    end
    
    S1 --> C1
    S2 --> C2
    S3 --> C3
    S4 --> C4
    
    C1 --> P1
    C2 --> P1
    C3 --> P1
    C4 --> P1
    
    P1 --> P2
    P2 --> P3
    P3 --> P4
    
    P4 --> ST1
    P4 --> ST2
    P4 --> ST3
    
    style S1 fill:#e3f2fd
    style S2 fill:#e3f2fd
    style S3 fill:#e3f2fd
    style S4 fill:#e3f2fd
    style C1 fill:#f3e5f5
    style C2 fill:#f3e5f5
    style C3 fill:#f3e5f5
    style C4 fill:#f3e5f5
    style P1 fill:#e8f5e8
    style P2 fill:#e8f5e8
    style P3 fill:#e8f5e8
    style P4 fill:#e8f5e8
    style ST1 fill:#fff3e0
    style ST2 fill:#fff3e0
    style ST3 fill:#fff3e0
```

### 5.2.2 数据采集算法实现

```python
class WeiboDataCollector:
    """微博数据采集器"""
    
    def __init__(self, config):
        self.keywords = config.get('keywords', [])
        self.user_ids = config.get('user_ids', [])
        self.collection_rate = config.get('rate', 1)  # 每秒采集次数
        self.deduplication_cache = set()
        self.session = requests.Session()
        
    def collect_by_keywords(self):
        """基于关键词的数据采集"""
        for keyword in self.keywords:
            try:
                # 1. 调用微博搜索API
                response = self.session.get(
                    f'https://m.weibo.cn/api/container/getIndex',
                    params={
                        'containerid': 100103type,
                        'q': keyword,
                        'count': 50
                    }
                )
                
                # 2. 数据验证
                if response.status_code == 200:
                    data = response.json()
                    posts = self.extract_posts(data)
                    
                    # 3. 去重处理
                    unique_posts = []
                    for post in posts:
                        post_id = post.get('id')
                        if post_id and post_id not in self.deduplication_cache:
                            self.deduplication_cache.add(post_id)
                            unique_posts.append(post)
                    
                    # 4. 存储数据
                    self.save_posts(unique_posts, keyword)
                    
            except Exception as e:
                self.log_error(f'关键词采集失败: {keyword}, 错误: {e}')
            
            # 5. 采集频率控制
            time.sleep(self.collection_rate)
    
    def collect_realtime_stream(self):
        """实时流数据采集"""
        while True:
            try:
                # 建立WebSocket连接
                ws = websocket.create_connection(
                    'wss://stream.weibo.com/2/status/sample'
                )
                
                for message in ws:
                    data = json.loads(message)
                    post = self.parse_stream_message(data)
                    
                    if post and self.is_relevant_post(post):
                        self.save_post(post)
                        
            except Exception as e:
                self.log_error(f'流采集异常: {e}')
                time.sleep(5)  # 重连间隔
```

## 5.3 数据清洗详细流程

### 5.3.1 文本预处理算法

```python
class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        self.stopwords = self.load_stopwords()
        self.custom_dict = self.load_custom_dictionary()
        self.emoji_pattern = re.compile(
            r'[\U00010000-\U0010ffff\U00002600-\U000027bf\U000024c2-\U0001f251]'
        )
        
    def clean_text(self, text):
        """综合文本清洗"""
        if not text:
            return ""
            
        # 1. HTML标签去除
        text = re.sub(r'<[^>]+>', '', text)
        
        # 2. URL链接处理
        text = re.sub(r'http[s]?://\S+', '[URL]', text)
        
        # 3. @用户提及处理
        text = re.sub(r'@\w+', '[USER]', text)
        
        # 4. #话题标签处理
        text = re.sub(r'#\w+#', '[TOPIC]', text)
        
        # 5. 表情符号处理
        text = self.emoji_pattern.sub('[EMOJI]', text)
        
        # 6. 繁简转换
        text = self.traditional_to_simplified(text)
        
        # 7. 特殊字符处理
        text = re.sub(r'[^\u4e00-\u9fff\w\s]', '', text)
        
        # 8. 多余空格处理
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def segment_text(self, text):
        """中文分词处理"""
        # 1. 加载自定义词典
        jieba.load_userdict(self.custom_dict)
        
        # 2. 精确模式分词
        words = jieba.lcut(text, cut_all=False)
        
        # 3. 停用词过滤
        filtered_words = []
        for word in words:
            if (len(word) > 1 and 
                word not in self.stopwords and 
                not word.isdigit()):
                filtered_words.append(word)
        
        return filtered_words
```

### 5.3.2 数据质量评估

```python
class DataQualityAssessor:
    """数据质量评估器"""
    
    def assess_data_quality(self, dataset):
        """评估数据集质量"""
        metrics = {}
        
        # 1. 完整性评估
        metrics['completeness'] = {
            'total_records': len(dataset),
            'missing_values': self.count_missing_values(dataset),
            'completeness_rate': self.calculate_completeness(dataset)
        }
        
        # 2. 准确性评估
        metrics['accuracy'] = {
            'duplicate_rate': self.calculate_duplicate_rate(dataset),
            'format_consistency': self.check_format_consistency(dataset),
            'language_detection': self.detect_language_consistency(dataset)
        }
        
        # 3. 一致性评估
        metrics['consistency'] = {
            'timestamp_consistency': self.check_timestamp_consistency(dataset),
            'field_consistency': self.check_field_consistency(dataset),
            'value_range_consistency': self.check_value_ranges(dataset)
        }
        
        # 4. 及时性评估
        metrics['timeliness'] = {
            'data_freshness': self.calculate_freshness(dataset),
            'collection_delay': self.calculate_collection_delay(dataset),
            'update_frequency': self.calculate_update_frequency(dataset)
        }
        
        return metrics
    
    def generate_quality_report(self, metrics):
        """生成质量评估报告"""
        report = {
            'overall_score': self.calculate_overall_quality_score(metrics),
            'detailed_metrics': metrics,
            'recommendations': self.generate_improvement_recommendations(metrics)
        }
        
        return report
```

## 5.4 特征工程详细流程

### 5.4.1 情感特征构建

```python
class SentimentFeatureExtractor:
    """情感特征提取器"""
    
    def __init__(self):
        self.sentiment_dict = self.load_sentiment_dictionary()
        self.bert_tokenizer = AutoTokenizer.from_pretrained('bert-base-chinese')
        self.bert_model = AutoModel.from_pretrained('bert-base-chinese')
        
    def extract_sentiment_features(self, text):
        """提取情感特征"""
        features = {}
        
        # 1. 词典特征
        dict_features = self.extract_dictionary_features(text)
        features.update(dict_features)
        
        # 2. 统计特征
        stat_features = self.extract_statistical_features(text)
        features.update(stat_features)
        
        # 3. 语义特征
        semantic_features = self.extract_semantic_features(text)
        features.update(semantic_features)
        
        # 4. 上下文特征
        context_features = self.extract_context_features(text)
        features.update(context_features)
        
        return features
    
    def extract_dictionary_features(self, text):
        """词典特征提取"""
        words = jieba.lcut(text)
        
        # 正面情感词统计
        positive_words = [w for w in words if w in self.sentiment_dict and self.sentiment_dict[w] > 0]
        negative_words = [w for w in words if w in self.sentiment_dict and self.sentiment_dict[w] < 0]
        
        features = {
            'positive_word_count': len(positive_words),
            'negative_word_count': len(negative_words),
            'positive_word_ratio': len(positive_words) / len(words) if words else 0,
            'negative_word_ratio': len(negative_words) / len(words) if words else 0,
            'sentiment_word_ratio': (len(positive_words) + len(negative_words)) / len(words) if words else 0,
            'max_positive_score': max([self.sentiment_dict[w] for w in positive_words], default=0),
            'min_negative_score': min([self.sentiment_dict[w] for w in negative_words], default=0),
            'sentiment_intensity': sum([abs(self.sentiment_dict[w]) for w in words if w in self.sentiment_dict])
        }
        
        return features
```

### 5.4.2 BERT语义特征提取

```python
def extract_bert_features(self, text):
    """BERT语义特征提取"""
    # 1. 文本编码
    inputs = self.bert_tokenizer(
        text, 
        return_tensors='pt', 
        truncation=True, 
        padding=True, 
        max_length=512
    )
    
    # 2. BERT推理
    with torch.no_grad():
        outputs = self.bert_model(**inputs)
        last_hidden_states = outputs.last_hidden_state
        attention_weights = outputs.attentions
    
    # 3. 特征提取
    features = {
        # CLS向量特征
        'cls_embedding': last_hidden_states[:, 0, :].squeeze().numpy(),
        
        # 平均池化特征
        'mean_pooling': last_hidden_states.mean(dim=1).squeeze().numpy(),
        
        # 最大池化特征
        'max_pooling': last_hidden_states.max(dim=1).squeeze().numpy(),
        
        # 注意力特征
        'attention_entropy': self.calculate_attention_entropy(attention_weights),
        'attention_variance': self.calculate_attention_variance(attention_weights),
        
        # 序列长度特征
        'sequence_length': (inputs['attention_mask'].sum(dim=1)).item(),
        'padding_ratio': (inputs['attention_mask'] == 0).float().mean().item()
    }
    
    return features
```

## 5.5 数据存储策略

### 5.5.1 分层存储架构

```mermaid
graph LR
    subgraph "热数据 Hot Data"
        H1[Redis缓存<br/>实时分析结果]
        H2[内存数据库<br/>用户会话]
        H3[应用缓存<br/>配置参数]
    end
    
    subgraph "温数据 Warm Data"
        W1[MySQL关系库<br/>用户/任务数据]
        W2[索引存储<br/>快速查询]
        W3[中间结果<br/>处理缓存]
    end
    
    subgraph "冷数据 Cold Data"
        C1[HBase列式库<br/>历史微博数据]
        C2[HDFS分布式<br/>原始数据文件]
        C3[对象存储<br/>模型文件]
    end
    
    subgraph "数据流转 Data Flow"
        DF1[实时写入<br/>Redis]
        DF2[定期同步<br/>MySQL]
        DF3[批量归档<br/>HBase]
        DF4[冷备策略<br/>HDFS]
    end
    
    H1 --> DF1
    H2 --> DF1
    H3 --> DF1
    DF1 --> DF2
    DF2 --> W1
    DF2 --> W2
    DF2 --> W3
    W1 --> DF3
    W2 --> DF3
    W3 --> DF3
    DF3 --> C1
    DF3 --> C2
    C1 --> DF4
    C2 --> DF4
    DF4 --> C3
    
    style H1 fill:#ff6b6b
    style H2 fill:#ff6b6b
    style H3 fill:#ff6b6b
    style W1 fill:#4ecdc4
    style W2 fill:#4ecdc4
    style W3 fill:#4ecdc4
    style C1 fill:#45b7d1
    style C2 fill:#45b7d1
    style C3 fill:#45b7d1
    style DF1 fill:#96ceb4
    style DF2 fill:#96ceb4
    style DF3 fill:#96ceb4
    style DF4 fill:#96ceb4
```

### 5.5.2 数据分区策略

```python
class DataPartitioner:
    """数据分区器"""
    
    def partition_by_time(self, data, partition_unit='day'):
        """按时间分区"""
        if partition_unit == 'hour':
            return data.groupby(data['publish_time'].dt.floor('H'))
        elif partition_unit == 'day':
            return data.groupby(data['publish_time'].dt.date)
        elif partition_unit == 'week':
            return data.groupby(data['publish_time'].dt.to_period('W'))
        elif partition_unit == 'month':
            return data.groupby(data['publish_time'].dt.to_period('M'))
    
    def partition_by_sentiment(self, data):
        """按情感分区"""
        sentiment_bins = [-1, -0.5, 0, 0.5, 1]
        sentiment_labels = ['strong_negative', 'negative', 'neutral', 'positive', 'strong_positive']
        
        data['sentiment_category'] = pd.cut(
            data['sentiment_score'], 
            bins=sentiment_bins, 
            labels=sentiment_labels
        )
        
        return dict(list(data.groupby('sentiment_category')))
    
    def partition_by_popularity(self, data):
        """按热度分区"""
        popularity_percentiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        popularity_labels = ['very_low', 'low', 'medium', 'high', 'very_high']
        
        data['popularity_category'] = pd.qcut(
            data['popularity_score'], 
            q=popularity_percentiles, 
            labels=popularity_labels
        )
        
        return dict(list(data.groupby('popularity_category')))
```

## 5.6 数据质量监控

### 5.6.1 质量指标体系

| 质量维度 | 具体指标 | 计算方法 | 目标值 |
|---------|---------|----------|--------|
| **完整性** | 数据完整率 | (有效记录数 / 总记录数) × 100% | ≥ 95% |
| **完整性** | 字段缺失率 | (缺失字段数 / 总字段数) × 100% | ≤ 5% |
| **准确性** | 重复数据率 | (重复记录数 / 总记录数) × 100% | ≤ 2% |
| **准确性** | 格式一致性 | 符合格式的记录数 / 总记录数 | ≥ 98% |
| **一致性** | 时间戳一致性 | 有效时间戳记录数 / 总记录数 | ≥ 99% |
| **一致性** | 数值范围一致性 | 在合理范围内的记录数 / 总记录数 | ≥ 95% |
| **及时性** | 数据新鲜度 | (当前时间 - 最新数据时间) | ≤ 1小时 |
| **及时性** | 采集延迟 | 平均采集响应时间 | ≤ 2秒 |

### 5.6.2 质量监控实现

```python
class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self):
        self.quality_metrics = {}
        self.alert_thresholds = {
            'completeness_rate': 0.95,
            'duplicate_rate': 0.02,
            'format_consistency': 0.98,
            'freshness_hours': 1.0
        }
    
    def monitor_data_quality(self, dataset):
        """实时监控数据质量"""
        current_metrics = self.assess_data_quality(dataset)
        
        # 检查是否触发预警
        alerts = []
        for metric, threshold in self.alert_thresholds.items():
            if current_metrics.get(metric, 0) < threshold:
                alerts.append({
                    'metric': metric,
                    'current_value': current_metrics[metric],
                    'threshold': threshold,
                    'severity': 'high' if current_metrics[metric] < threshold * 0.8 else 'medium'
                })
        
        # 发送预警通知
        if alerts:
            self.send_quality_alerts(alerts)
        
        # 更新监控指标
        self.quality_metrics = current_metrics
        
        return current_metrics, alerts
    
    def generate_quality_dashboard(self):
        """生成质量监控仪表盘数据"""
        dashboard_data = {
            'overall_score': self.calculate_overall_quality_score(),
            'trend_data': self.get_quality_trends(),
            'alert_count': len(self.get_active_alerts()),
            'last_update': datetime.now().isoformat(),
            'metrics_breakdown': self.quality_metrics
        }
        
        return dashboard_data
```
