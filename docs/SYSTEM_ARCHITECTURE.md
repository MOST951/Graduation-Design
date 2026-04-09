# 微博舆情情感分析系统 - 系统架构文档

## 项目信息
- **作者**: 罗森
- **学号**: 2022407443
- **学校**: 四川民族学院 智能科学与技术学院
- **指导教师**: 罗丹

## 一、系统概述

本系统是一套完整的微博舆情情感分析平台，采用分布式架构设计，实现从数据采集、清洗、情感分析到可视化展示的全流程处理。

### 核心创新点
**情感-热度双维度排序模型**：
```
composite_score = α × sentiment_score + β × popularity_score + γ × timeliness_score
```
- `sentiment_score`: 情感得分 (词典+BERT混合方法)
- `popularity_score`: 热度得分 = log(1 + reposts×3 + comments×2 + likes)
- `timeliness_score`: 时效性得分 = exp(-λ × hours_since_publish)
- 默认权重: α=0.4, β=0.4, γ=0.2

## 二、技术栈

### 后端技术
| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Web框架 | Flask | Python轻量级Web框架 |
| 大数据处理 | PySpark 3.0 | 分布式计算引擎 |
| NLP | ChineseBERT + jieba | 深度学习+传统分词 |
| 情感分析 | 词典+BERT混合 | 准确率87.2% |

### 前端技术
| 组件 | 技术选型 | 说明 |
|------|----------|------|
| 框架 | Vue 3 + TypeScript | 现代前端框架 |
| 构建工具 | Vite | 快速开发构建 |
| UI组件 | Element Plus | 企业级UI库 |
| 可视化 | ECharts | 丰富的图表库 |

### 存储技术
| 组件 | 技术选型 | 说明 |
|------|----------|------|
| 分布式存储 | HDFS | 原始数据存储 |
| 结构化存储 | HBase | 清洗后数据 |
| 元数据管理 | MySQL | 用户、配置、日志 |

## 三、系统模块

### 1. 数据采集模块 (`backend/crawler/`)
```
├── weibo_spider.py      # 微博爬虫主类
├── cookies.json         # Cookie池配置
└── __init__.py
```

**功能特性**：
- 微博API调用 (OAuth2.0认证)
- Cookie池轮换策略
- 动态UA切换
- 请求限流与重试
- 代理IP池支持

**采集内容**：
- 热搜榜数据
- 关键词搜索微博
- 用户信息与互动数据

### 2. 数据清洗模块 (`backend/spark/data_cleaner.py`)

**清洗流程**：
1. **数据去重**: MD5去重、SimHash相似文本检测
2. **文本清洗**: HTML标签、URL、@提及、表情符号处理
3. **中文分词**: jieba分词、自定义词典、停用词过滤
4. **特征提取**: TF-IDF、Word2Vec、文本统计特征
5. **数据标准化**: 时间格式、数值归一化

### 3. 情感分析模块 (`backend/spark/`)
```
├── sentiment_analyzer.py       # 词典情感分析
├── chinese_bert_sentiment.py   # ChineseBERT深度学习
├── dual_dimension_model.py     # 双维度排序模型
└── streaming_analyzer.py       # 实时流处理
```

**混合分析方法**：
- **词典方法**: 基础情感词、否定词、程度副词、表情符号
- **深度学习**: ChineseBERT微调模型
- **融合策略**: 加权平均，词典权重0.3，BERT权重0.7

### 4. 数据存储模块 (`backend/services/`)
```
├── database_service.py    # MySQL数据库服务
├── storage_service.py     # HDFS/HBase存储服务
└── query_service.py       # 数据查询服务
```

**存储方案**：
- **HDFS**: 原始微博数据、中间处理结果
- **HBase**: 清洗后结构化数据、情感分析结果
- **MySQL**: 用户信息、系统配置、任务日志

### 5. 可视化模块 (`web-frontend/`)
```
├── src/views/
│   ├── Dashboard.vue              # 仪表板
│   ├── SentimentAnalysis.vue      # 情感分析
│   ├── DualDimensionAnalysis.vue  # 双维度分析
│   ├── HotTopics.vue              # 热点话题
│   ├── RealTimeMonitor.vue        # 实时监控
│   └── ...
```

**可视化内容**：
- 情感分布饼图/柱状图
- 情感趋势折线图
- 热点话题词云
- 地域分布地图
- 用户影响力网络图

## 四、API接口

### 认证接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login-by-email` | POST | 邮箱密码登录 |
| `/api/auth/login-by-code` | POST | 验证码登录 |
| `/api/auth/reset-password` | POST | 重置密码 |

### 数据采集接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/crawl/start` | POST | 启动采集任务 |
| `/api/crawl/status/<task_id>` | GET | 查询任务状态 |
| `/api/crawl/hot-search` | GET | 获取热搜榜 |

### 情感分析接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sentiment/analyze` | POST | 单条文本分析 |
| `/api/sentiment/batch` | POST | 批量分析 |
| `/api/sentiment/statistics` | GET | 情感统计 |

### 双维度排序接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/dual-dimension/rank` | GET | 获取排序结果 |
| `/api/dual-dimension/config` | POST | 配置权重参数 |

## 五、部署架构

### Spark伪集群配置
```
┌─────────────────────────────────────────────┐
│                 Master Node                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ Spark   │ │ HDFS    │ │ HBase       │   │
│  │ Master  │ │ NameNode│ │ Master      │   │
│  └─────────┘ └─────────┘ └─────────────┘   │
└─────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ Worker1 │    │ Worker2 │    │ Worker3 │
    │ Executor│    │ Executor│    │ Executor│
    │ DataNode│    │ DataNode│    │ DataNode│
    └─────────┘    └─────────┘    └─────────┘
```

### Docker Compose服务
```yaml
services:
  mysql:      # 元数据存储
  hbase:      # 结构化数据
  flask:      # 后端API
  frontend:   # Vue前端
```

## 六、性能指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 情感分析准确率 | >85% | 87.2% |
| 单条分析延迟 | <100ms | ~50ms |
| 批量处理吞吐 | >1000条/秒 | 待测试 |
| 实时流延迟 | <5秒 | 待测试 |

## 七、文件结构

```
weibo-sentiment-analysis/
├── backend/                    # Flask后端
│   ├── crawler/               # 数据采集
│   ├── spark/                 # Spark处理
│   ├── services/              # 业务服务
│   ├── api/                   # API路由
│   └── run_server.py          # 启动入口
├── web-frontend/              # Vue前端
│   ├── src/views/             # 页面组件
│   ├── src/api/               # API客户端
│   └── src/router/            # 路由配置
├── deployment/                # 部署配置
│   ├── docker/                # Docker配置
│   └── sql/                   # 数据库脚本
├── docs/                      # 文档
└── tests/                     # 测试用例
```

## 八、开发进度

### 已完成 ✅
- [x] Spark伪集群环境搭建
- [x] 微博数据采集模块
- [x] 数据清洗与预处理
- [x] 词典情感分析
- [x] ChineseBERT集成
- [x] 双维度排序模型
- [x] Flask后端API
- [x] Vue前端界面
- [x] 用户认证系统

### 进行中 🔄
- [ ] HDFS/HBase存储集成
- [ ] Spark Streaming实时处理
- [ ] 性能测试与优化

### 待完成 📋
- [ ] 系统集成测试
- [ ] 论文撰写
