# 微博舆情情感分析系统 - 项目总结

> 本文档为 AI 编程助手（如 Windsurf/Cascade）提供项目概况说明
> 
> **最后更新**: 2026-01-18

---

## 0. 项目背景与约束 ⚠️

> **重要**: 本项目为**本科毕业设计**，运行于 **Spark 伪集群环境**（单机模拟分布式），**非企业级微服务架构**。
> 
> 后续所有开发建议和技术方案必须贴合以下约束：
> - **规模定位**: 学术演示项目，非生产环境
> - **运行环境**: 单机 Spark Local/Standalone 模式
> - **设计原则**: 避免过度设计，优先可演示性和学习目的
> - **资源限制**: 单机运行，无真实分布式集群
> 
> ### ❌ 严禁使用的技术
> Java, Spring Boot, MyBatis, JWT, Redis, Kafka, Druid, RBAC, Kubernetes

---

## 1. 项目名称与简介

**项目名称**: Weibo Sentiment Analysis System（微博舆情情感分析系统）

**项目类型**: 本科毕业设计

**项目目标**: 
构建一个基于 Spark 伪集群的微博舆情情感分析演示平台，实现从数据采集、预处理、情感分析到可视化展示的全流程处理，展示大数据技术在舆情分析领域的应用。

**核心创新点**: 
- **情感-热度双维度排序模型** ✅ 已完成
- 混合情感分析（规则 + BERT，准确率 87.2%）

---

## 2. 技术栈概览（真实技术栈）

### 后端技术
| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **语言** | Python | 3.9+ | 主要后端语言 |
| **框架** | Flask | 2.x | 轻量级 Web 框架 |
| **大数据** | Apache Spark | 3.0.0 | 伪集群模式 |
| **大数据** | Scala | 2.12.15 | Spark 作业开发 |
| **存储** | HBase | 2.x | 微博数据存储 |
| **存储** | HDFS | 3.3 | 原始数据存储 |
| **数据库** | MySQL | 8.0 | 仅系统元数据 |

### 前端技术
| 类别 | 技术 | 版本 |
|------|------|------|
| **框架** | Vue.js | 3.x |
| **构建工具** | Vite | 3.x |
| **语言** | TypeScript | 4.x |
| **UI组件库** | Element Plus | 2.x |
| **图表库** | ECharts | 5.x |
| **词云** | echarts-wordcloud | - |

### NLP 与模型
| 类别 | 技术 |
|------|------|
| **深度学习** | PyTorch |
| **预训练模型** | ChineseBERT |
| **中文分词** | jieba |
| **情感词典** | 自定义情感词典 |

### 部署技术
| 类别 | 技术 |
|------|------|
| **容器化** | Docker Compose |
| **容器服务** | MySQL + HBase |

---

## 3. 目录结构说明

```
weibo-sentiment-analysis/
├── backend/                   # Flask 后端服务 (Python)
│   ├── app.py                 # Flask 主入口
│   ├── api/                   # API 蓝图（topics.py, sentiment.py 等）
│   ├── services/              # 业务逻辑层
│   ├── spark/                 # Spark 相关 Python 模块
│   │   ├── dual_dimension_model.py  # 双维度排序模型
│   │   ├── chinese_bert_sentiment.py # BERT 情感分析
│   │   └── sentiment_analyzer.py     # 混合情感分析器
│   └── data/                  # 数据文件
├── spark-preprocessing/       # Spark 预处理模块 (Scala)
│   └── src/main/scala/com/weibo/preprocessing/
│       ├── ranking/           # 双维度排序作业
│       │   └── TopicRanker.scala  # ✅ 核心排序作业
│       ├── cleaner/           # 数据清洗
│       └── tokenizer/         # 分词处理
├── web-frontend/              # Vue 3 前端应用
│   ├── src/
│   │   ├── api/               # API 接口封装
│   │   ├── views/             # 页面视图
│   │   ├── components/        # 可复用组件
│   │   │   └── topics/        # 话题相关组件
│   │   │       └── DualDimensionRanking.vue  # ✅ 双维度排序组件
│   │   └── store/             # Pinia 状态管理
│   └── package.json
├── model-training/            # 模型训练模块 (Python)
├── data-collector/            # 数据采集模块
├── deployment/                # 部署配置 (Docker Compose)
├── tests/                     # 测试脚本
├── config/                    # 全局配置
└── README.md
```

### 3.1 Flask 后端结构 (`backend/`)

```
backend/
├── app.py                     # Flask 主入口，注册蓝图
├── api/                       # API 蓝图
│   ├── topics.py              # 热点话题 API（含双维度排序）
│   ├── sentiment.py           # 情感分析 API
│   └── weibo.py               # 微博数据 API
├── services/                  # 业务服务
│   ├── rule_based_analyzer.py # 规则情感分析
│   └── hybrid_analyzer.py     # 混合分析器
├── spark/                     # Spark 相关模块
│   ├── dual_dimension_model.py    # Python 版双维度模型
│   ├── chinese_bert_sentiment.py  # ChineseBERT 情感分析
│   └── sentiment_analyzer.py      # 情感词典分析
└── routes/                    # 路由模块
    └── analysis_routes.py     # 分析路由
```

### 3.2 前端结构 (`web-frontend/`)

```
web-frontend/src/
├── main.ts                    # 应用入口
├── App.vue                    # 根组件
├── api/                       # API接口封装（17个模块）
│   ├── admin.ts               # 系统管理API
│   ├── collection.ts          # 数据采集API
│   ├── sentiment.ts           # 情感分析API
│   ├── visualization.ts       # 可视化API
│   ├── realtime.ts            # 实时监控API
│   ├── topics.ts              # 热点话题API
│   ├── reports.ts             # 报告生成API
│   └── ...
├── views/                     # 页面视图（18个页面）
│   ├── Dashboard.vue          # 仪表盘
│   ├── Login.vue              # 登录页
│   ├── DataCollection.vue     # 数据采集
│   ├── SentimentAnalysis.vue  # 情感分析
│   ├── Visualization.vue      # 数据可视化
│   ├── RealTimeMonitor.vue    # 实时监控
│   ├── HotTopics.vue          # 热点话题
│   ├── SystemAdmin.vue        # 系统管理
│   └── ...
├── components/                # 可复用组件（49+组件）
│   ├── charts/                # 图表组件
│   ├── collection/            # 采集相关组件
│   ├── reports/               # 报告组件
│   └── ...
├── store/                     # Pinia状态管理（10个store）
│   ├── auth.ts                # 认证状态
│   ├── collection.ts          # 采集任务状态
│   ├── visualization.ts       # 可视化状态
│   └── ...
├── router/                    # 路由配置
├── composables/               # 组合式函数
├── layouts/                   # 布局组件
├── styles/                    # 全局样式
└── utils/                     # 工具函数
```

---

## 4. 核心功能实现

### 4.1 情感-热度双维度排序 ✅ **核心创新点**

- **技术实现**: Spark (Scala) + SHC + HBase
- **功能**: 融合情感强度和传播热度的综合排序
- **核心公式**:
  ```
  rawPopularity = log(1 + reposts + 2*comments + likes)
  timeDecay = 1.0 / (1 + 0.1 * hoursAgo)
  popularityScore = rawPopularity * timeDecay
  compositeScore = 0.6 * |sentiment_score| + 0.4 * popularityScore
  ```
- **相关文件**: 
  - `spark-preprocessing/src/main/scala/.../ranking/TopicRanker.scala`
  - `backend/api/topics.py` (`/api/topics/ranked`)
  - `web-frontend/src/components/topics/DualDimensionRanking.vue`

### 4.2 混合情感分析 ✅

- **技术实现**: 规则引擎 + ChineseBERT（准确率 87.2%）
- **功能**: 
  - 基于情感词典的规则分析
  - 基于 ChineseBERT 的深度学习分析
  - 混合策略自动选择
- **相关文件**: 
  - `backend/spark/chinese_bert_sentiment.py`
  - `backend/spark/sentiment_analyzer.py`
  - `backend/api/sentiment.py`

### 4.3 数据采集模块 ✅

- **技术实现**: Python 爬虫 + 微博 API
- **功能**: 关键词采集、热搜实时爬取、采集任务管理
- **相关文件**: `data-collector/`, `backend/api/weibo.py`

### 4.4 数据预处理 ✅

- **技术实现**: Apache Spark (Scala)
- **功能**: 文本清洗、jieba 分词、特征提取
- **相关文件**: `spark-preprocessing/`

### 4.5 数据可视化 ✅

- **技术实现**: ECharts + echarts-wordcloud
- **功能**: 
  - 情感分布图表
  - 词云图
  - 双维度散点图（情感 vs 热度）
  - 综合得分柱状图
- **相关文件**: `web-frontend/src/views/HotTopics.vue`, `web-frontend/src/components/`

### 4.6 热点话题分析 ✅

- **技术实现**: 双维度排序 + 实时热搜爬取
- **功能**: 
  - 热点话题发现与排序
  - 实时热搜榜展示
  - 话题情感分析
- **相关文件**: `web-frontend/src/views/HotTopics.vue`, `backend/api/topics.py`

---

## 5. 第三方依赖与工具

### Flask 后端依赖 (Python)
- **flask**: Web 框架
- **flask-cors**: 跨域支持
- **pyspark**: Spark Python API
- **happybase**: HBase Python 客户端
- **jieba**: 中文分词
- **torch**: PyTorch 深度学习
- **transformers**: ChineseBERT 模型

### Spark 作业依赖 (Scala)
- **spark-core**: Spark 核心
- **spark-sql**: Spark SQL
- **shc-core**: Spark HBase Connector
- **hbase-client**: HBase 客户端

### 前端核心依赖
- **vue**: 前端框架 (3.x)
- **vue-router**: 路由管理
- **pinia**: 状态管理
- **element-plus**: UI 组件库
- **echarts**: 图表库
- **echarts-wordcloud**: 词云插件
- **axios**: HTTP 请求
- **typescript**: 类型支持

---

## 6. 部署与运行说明

### 6.1 环境要求
- Python 3.9+
- Node.js 16+
- JDK 11+ (Spark 作业)
- Apache Spark 3.0 (伪集群模式)
- HBase 2.x
- Docker & Docker Compose

### 6.2 本地开发运行

**Flask 后端启动**:
```bash
cd backend
pip install -r requirements.txt
python app.py
# 默认运行在 http://localhost:5000
```

**前端启动**:
```bash
cd web-frontend
npm install
npm run dev
# 默认运行在 http://localhost:5173
```

**Spark 作业提交**:
```bash
spark-submit --class com.weibo.preprocessing.ranking.TopicRanker \
  --master local[2] \
  spark-preprocessing/target/spark-jobs-1.0.jar
```

### 6.3 Docker 部署
```bash
cd deployment
docker-compose up -d
```

**服务端口**:
- Flask API: `http://localhost:5000/api`
- 前端: `http://localhost:5173`
- MySQL: `3306`
- HBase: `16010` (Web UI), `2181` (ZooKeeper)

### 6.4 HBase 表初始化
```bash
# 创建微博数据表
hbase shell
> create 'weibo_posts', 'cf'
> create 'hot_topics', 'cf'
```

**MySQL 初始化**:
```bash
mysql -u root -p < deployment/sql/init.sql
```

---

## 7. 数据存储设计

### 7.1 HBase 表结构

**输入表: `weibo_posts`**
| 列族 | 列限定符 | 类型 | 说明 |
|------|----------|------|------|
| cf | text | String | 微博文本 |
| cf | reposts | Int | 转发数 |
| cf | comments | Int | 评论数 |
| cf | likes | Int | 点赞数 |
| cf | timestamp | Long | 发布时间戳（毫秒） |
| cf | sentiment_score | Double | 情感分（-1.0 ～ 1.0） |

**输出表: `hot_topics`**
| 列族 | 列限定符 | 类型 | 说明 |
|------|----------|------|------|
| cf | keywords | String | 话题关键词（逗号分隔） |
| cf | composite_score | Double | 综合得分 |
| cf | sentiment_avg | Double | 平均情感分 |
| cf | post_count | Int | 包含微博数量 |

### 7.2 MySQL 表（仅元数据）

| 表名 | 说明 |
|------|------|
| `users` | 用户表 |
| `collection_task` | 采集任务表 |
| `spark_jobs` | Spark 作业状态表 |
| `system_log` | 系统日志表 |

---

## 8. API 接口概览

Flask 后端提供 RESTful API，基础路径: `/api`

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 话题 | `/topics` | 热点话题接口 |
| **双维度排序** | `/topics/ranked` | ✅ 获取排序后的热点话题 |
| **排序配置** | `/topics/dual-dimension/config` | ✅ 获取/更新排序配置 |
| 情感分析 | `/sentiment` | 情感分析接口 |
| 微博数据 | `/weibo` | 微博数据接口 |
| 热搜 | `/weibo/hot-search` | 实时热搜爬取 |

### 8.1 双维度排序 API 示例

**GET `/api/topics/ranked`**
```json
[
  {
    "topic_id": 1,
    "name": "人工智能",
    "keywords": ["AI", "大模型", "GPT"],
    "composite_score": 0.7234,
    "sentiment_avg": 0.8,
    "popularity_score": 0.5891,
    "rank": 1,
    "trend": "up"
  }
]
```

---

## 9. 项目进度

### ✅ 已完成功能
- [x] Spark 伪集群环境搭建
- [x] 微博数据采集模块
- [x] 数据清洗与预处理
- [x] 混合情感分析（规则 + BERT，准确率 87.2%）
- [x] **情感-热度双维度排序** ⭐ 核心创新点
- [x] Flask 后端 API
- [x] Vue 前端可视化
- [x] **完整数据流连通** ⭐ 解决中期检查问题

### 🔄 待完善功能
- [ ] 全链路集成测试
- [ ] 性能优化
- [ ] 论文撰写

---

## 11. 完整数据流连通 ⭐

解决中期检查表中"爬虫数据未与各个模块连通"问题。

### 数据流架构

```
微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 双维度排序 → 前端展示
```

### 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **Spark服务** | `backend/services/spark_service.py` | 触发和监控Spark作业 |
| **数据流API** | `backend/api/weibo_api.py` | 完整流水线触发接口 |
| **前端监控** | `web-frontend/src/views/DataCollection.vue` | 实时状态可视化 |

### API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/weibo/collect` | POST | 启动完整数据流处理 |
| `/api/weibo/collect/status/<task_id>` | GET | 获取任务状态（含各阶段进度） |
| `/api/weibo/collect/result/<task_id>` | GET | 获取处理结果（raw/analyzed/ranked） |
| `/api/weibo/spark/jobs` | GET | 获取Spark作业列表 |
| `/api/weibo/dataflow/overview` | GET | 获取数据流概览统计 |

### 技术特点

1. **异步任务**: 使用线程池执行长时间任务
2. **状态追踪**: 各阶段进度实时更新
3. **错误重试**: 最多3次重试，30秒间隔
4. **完整日志**: 详细记录每个阶段执行情况
5. **前端可视化**: 流水线进度实时展示

---

## 10. 项目特点

1. **核心创新**: 情感-热度双维度排序模型，融合情感强度与传播热度
2. **大数据支持**: Spark 伪集群 + HBase 存储
3. **深度学习**: ChineseBERT 中文情感分析（87.2% 准确率）
4. **前后端分离**: Vue 3 + Flask 轻量级架构
5. **适合毕设**: 避免过度设计，聚焦核心功能演示

---

*文档更新时间: 2026-01-18*
*适用于: Windsurf/Cascade 等 AI 编程助手*
