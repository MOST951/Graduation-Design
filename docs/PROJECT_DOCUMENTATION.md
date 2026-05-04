# 基于Spark的微博舆情情感分析系统

## 项目文档

---

### 项目信息

| 项目 | 内容 |
|------|------|
| **论文题目** | 基于Spark的微博舆情情感分析系统设计与实现 |
| **作者** | 罗森 |
| **学号** | 2022407443 |
| **学校** | 四川民族学院 智能科学与技术学院 2248班 |
| **指导教师** | 罗丹 |
| **完成时间** | 2026年4月 |

---

## 目录

1. [项目概述](#一项目概述)
2. [系统架构](#二系统架构)
3. [环境配置](#三环境配置)
4. [模块详解](#四模块详解)
5. [API接口文档](#五api接口文档)
6. [数据库设计](#六数据库设计)
7. [前端页面](#七前端页面)
8. [部署指南](#八部署指南)
9. [使用说明](#九使用说明)
10. [常见问题](#十常见问题)

---

## 一、项目概述

### 1.1 项目背景

随着社交媒体的快速发展，微博已成为中国最重要的舆论场之一。每天产生海量的用户生成内容，其中蕴含着丰富的情感信息和舆情动态。如何高效地采集、处理和分析这些数据，及时发现舆情热点和情感倾向，对于政府部门、企业和研究机构具有重要的实际意义。

### 1.2 项目目标

本项目旨在设计并实现一套完整的微博舆情情感分析系统，主要目标包括：

1. **数据采集**：实现稳定高效的微博数据采集，支持热搜榜、关键词搜索等多种采集方式
2. **数据清洗**：基于Spark分布式框架，实现数据去重、文本清洗、中文分词等预处理
3. **情感分析**：融合词典方法和深度学习模型，实现高准确率的情感分类
4. **三维度排序**：创新性地提出情感-热度三维度排序模型，综合考虑情感强度和传播热度
5. **可视化展示**：提供直观的数据可视化界面，支持多维度的舆情分析展示

### 1.3 核心创新点

**情感-热度三维度排序模型**：

传统舆情分析系统通常只关注单一维度（如时间、热度或情感），本系统创新性地提出三维度排序模型：

```
Score_rank(w) = ω₁·N(S) + ω₂·H_norm(w) + ω₃·γ(t)
```

- **情感强度** N(S)：级联策略（词典优先，置信度≤0.7时调用ChineseBERT），归一化 `(|S|+1)/2` 映射到[0,1]
- **热度得分** H_norm：`log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)`（λ_r=1, λ_c=2, λ_l=1），经最大-最小归一化至[0,1]
- **时效性得分** γ(t)：`2^(-Δt/H)`，半衰期H=12小时，每12小时得分减半
- **默认权重**：ω₁=0.4, ω₂=0.4, ω₃=0.2

### 1.4 技术特点

| 特点 | 说明 |
|------|------|
| 分布式处理 | 基于Spark的并行化数据处理，支持大规模数据 |
| 级联情感分析 | 词典优先+BERT精确分析（级联策略），准确率达86.2%，速度提升2.6倍 |
| 实时流处理 | Spark Streaming支持实时舆情监控 |
| 模块化设计 | 各模块独立，通过REST API通信 |
| 多存储后端 | HDFS+HBase+MySQL分层存储 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        前端展示层 (Vue 3 + TypeScript)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 仪表板   │ │ 情感分析 │ │ 三维度   │ │ 热点话题 │ │ 实时监控 │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP/REST (Axios)
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌───────────────────────┐   ┌─────────────────────────────────────────┐
│ Java后端 (Spring Boot)│   │       Python后端 (Flask :5000)           │
│  :8081                │   │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  ┌─────────┐          │   │  │情感分析  │ │三维度排序│ │数据采集 │ │
│  │认证/用户│          │   │  │ API      │ │ API      │ │ API     │ │
│  │Spark提交│          │   │  └──────────┘ └──────────┘ └─────────┘ │
│  └─────────┘          │   │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│                       │   │  │Pipeline  │ │Dashboard │ │Unified  │ │
│                       │   │  │ Service  │ │ API      │ │ API v2  │ │
│                       │   │  └──────────┘ └──────────┘ └─────────┘ │
└───────────┬───────────┘   └──────────────────┬──────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  大数据处理层 (PySpark / Spark 3.0)                   │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐      │
│  │数据清洗  │ │级联情感分析  │ │三维度排序    │ │Streaming │      │
│  │SimHash   │ │词典+BERT     │ │情感+热度+时效│ │实时流    │      │
│  └──────────┘ └──────────────┘ └──────────────┘ └──────────┘      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────────┐
│                         数据存储层                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │  MySQL   │ │  HDFS    │ │  HBase   │ │  Redis   │              │
│  │核心数据  │ │原始文件  │ │结构化    │ │缓存/会话 │              │
│  │分析结果  │ │          │ │          │ │          │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层次 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **前端** | Vue 3 | 3.4.x | 渐进式JavaScript框架 |
| | TypeScript | 5.x | 类型安全 |
| | Vite | 5.x | 构建工具 |
| | Element Plus | 2.4.x | UI组件库 |
| | ECharts | 5.4.x | 数据可视化 |
| | Axios | 1.x | HTTP客户端 |
| **Java后端** | Spring Boot | 2.7.x | Java Web框架（认证/用户/Spark提交） |
| | Spring Security | 5.x | 认证授权（JWT） |
| | Spring Data JPA | 2.7.x | ORM持久层 |
| | MyBatis-Plus | 3.5.x | 增强SQL映射 |
| | Druid | 1.2.x | 数据库连接池 |
| | Lombok | 1.18.x | 代码简化 |
| **Python后端** | Flask | 2.3.x | NLP/数据分析REST API |
| | Flask-CORS | 4.x | 跨域支持 |
| | DBUtils | 3.x | MySQL连接池 (PooledDB) |
| | PyMySQL | 1.1.x | MySQL驱动 |
| | requests | 2.31.x | HTTP客户端（爬虫） |
| **大数据** | PySpark | 3.5.0 | 分布式计算（Python API） |
| | Hadoop | 3.3.x | 分布式存储 |
| **NLP** | jieba | 0.42.1 | 中文分词 |
| | PyTorch | 2.0+ | 深度学习框架 |
| | Transformers | 4.x | ChineseBERT模型 |
| **存储** | MySQL | 8.0 | 核心数据+分析结果+排序结果 |
| | HDFS | 3.3.x | 分布式文件系统（原始数据） |
| | HBase | 2.4.x | 列式数据库（结构化数据） |
| | Redis | 7.x | 缓存/会话/Token |

### 2.3 目录结构

```
weibo-sentiment-analysis/
├── pom.xml                           # Maven父POM (统一版本管理)
│
├── common/                           # 公共模块 (Java)
│   ├── pom.xml
│   └── src/main/java/com/weibo/
│       ├── collector/                # 数据采集相关类
│       │   ├── api/              # WeiboApiClient, OAuth2
│       │   ├── parser/           # 数据解析器
│       │   ├── spider/           # WeiboSpider, 反爬处理
│       │   ├── storage/          # HDFS写入器
│       │   ├── scheduler/        # 任务调度
│       │   └── task/             # 采集任务配置
│       └── common/               # 通用工具
│           ├── config/           # HdfsConfig, SparkConfig
│           ├── constants/        # 常量定义
│           ├── exception/        # 自定义异常
│           └── model/            # 统一响应体
│
├── web-backend/                      # Spring Boot后端服务
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/weibo/web/
│       │   ├── WebApplication.java  # Spring Boot启动类
│       │   ├── controller/          # REST控制器
│       │   │   ├── AuthController       # 认证接口
│       │   │   ├── AnalysisController   # 情感分析接口
│       │   │   ├── CollectionController # 数据采集接口
│       │   │   ├── DashboardController  # 仪表板接口
│       │   │   └── AdminController      # 管理接口
│       │   ├── service/             # 业务服务层
│       │   │   ├── AuthService          # 认证服务 (JWT)
│       │   │   ├── AnalysisService      # 分析服务
│       │   │   ├── SparkService         # Spark任务提交
│       │   │   └── MonitorService       # 监控服务
│       │   ├── entity/              # JPA实体类
│       │   ├── repository/          # Spring Data仓库
│       │   ├── security/            # Spring Security + JWT
│       │   ├── config/              # 配置类 (Security, Web, Async)
│       │   ├── dto/                 # 数据传输对象
│       │   ├── aspect/              # AOP切面 (日志, 性能, 限流)
│       │   ├── spark/               # Spark任务启动器
│       │   └── utils/               # 工具类
│       └── resources/
│           ├── application.yml      # 主配置文件
│           ├── application-dev.yml  # 开发环境配置
│           └── application-prod.yml # 生产环境配置
│
├── data-collector/                   # 数据采集模块 (Java)
│   ├── pom.xml
│   └── src/main/java/
│
├── sentiment-analysis/               # 情感分析模块 (Java)
│   ├── pom.xml
│   └── src/main/java/
│
├── model-training/                   # 模型训练模块 (Python)
│   ├── pom.xml
│   ├── requirements.txt
│   └── src/
│
├── backend-python/                   # Python后端 (Flask + NLP + Spark)
│   ├── app.py                       # Flask主应用 (蓝图注册/CORS/错误处理)
│   ├── requirements.txt             # Python依赖
│   ├── api/                         # REST API蓝图 (17个模块)
│   │   ├── sentiment.py             # 情感分析API (/api/sentiment/*)
│   │   ├── tri_dimension_api.py    # 三维度排序API (/api/tri-dimension/*)
│   │   ├── pipeline_api.py          # 流水线API (/api/pipeline/*)
│   │   ├── collection.py            # 数据采集API (/api/collection/*)
│   │   ├── crawler.py               # 爬虫API (/api/v2/crawl/*)
│   │   ├── dashboard.py             # 仪表板API (/api/dashboard/*)
│   │   ├── topics.py                # 热点话题API (/api/topics/*)
│   │   ├── monitor.py               # 实时监控API (/api/monitor/*)
│   │   ├── auth.py                  # 认证API (/api/auth/*)
│   │   ├── evaluation.py            # 模型评估API (/api/evaluation/*)
│   │   ├── preprocess.py            # 预处理API (/api/preprocess/*)
│   │   ├── behavior.py              # 用户行为API (/api/behavior/*)
│   │   ├── propagation.py           # 传播分析API (/api/propagation/*)
│   │   ├── weibo_api.py             # 微博综合API (/api/weibo/*)
│   │   └── unified_api.py           # 统一API v2 (/api/v2/*)
│   ├── services/                    # 业务服务层 (25个模块)
│   │   ├── pipeline_service.py      # ★ 数据流水线 (采集→分析→排序)
│   │   ├── database_service.py      # ★ MySQL数据库服务 (连接池+CRUD)
│   │   ├── hybrid_analyzer.py       # 混合情感分析器
│   │   ├── storage_service.py       # 统一存储接口 (HDFS/HBase/MySQL)
│   │   ├── weibo_collector.py       # 微博数据采集服务
│   │   ├── enhanced_crawler.py      # 增强型爬虫
│   │   ├── auth_service.py          # 认证服务
│   │   ├── query_service.py         # 查询服务
│   │   └── ...                      # 其他服务模块
│   ├── spark/                       # Spark处理脚本
│   │   ├── tri_dimension_model_v2.py  # 三维度排序模型 v2
│   │   ├── enhanced_tri_dimension.py  # 增强型三维度
│   │   ├── sentiment_analyzer.py       # 词典情感分析
│   │   ├── chinese_bert_sentiment.py   # ChineseBERT情感分析
│   │   ├── data_cleaner.py             # 数据清洗 (SimHash去重)
│   │   ├── streaming_analyzer.py       # 实时流分析
│   │   └── conf/                       # Spark配置文件
│   ├── core/                        # 核心引擎
│   │   ├── spark_engine.py          # Spark引擎封装
│   │   └── data_pipeline.py         # 数据管道
│   ├── crawler/                     # 爬虫模块
│   │   ├── weibo_crawler.py         # 微博爬虫
│   │   ├── weibo_spider.py          # 微博蜘蛛 (反爬处理)
│   │   └── cookies.json             # Cookie配置
│   ├── models/                      # 模型管理
│   │   └── model_manager.py         # 模型加载/预热
│   ├── routes/                      # 路由
│   │   └── analysis_routes.py       # 分析路由
│   └── resources/                   # 资源文件
│       ├── sentiment_dict/          # 情感词典 (28,000+词条)
│       └── stopwords/               # 停用词表
│
├── web-frontend/                     # 前端代码 (Vue 3)
│   ├── src/
│   │   ├── views/                   # 页面组件
│   │   ├── api/                     # API客户端
│   │   ├── router/                  # 路由配置
│   │   ├── store/                   # 状态管理
│   │   └── components/              # 公共组件
│   ├── package.json
│   └── vite.config.ts
│
├── deployment/                       # 部署配置
│   ├── pom.xml
│   ├── docker/                      # Docker配置
│   └── sql/                         # 数据库脚本
│
├── docs/                             # 文档
├── tests/                            # 测试代码
├── .env                              # 环境变量
├── start-system.bat                  # 启动脚本
└── README.md                         # 项目说明
```

---

## 三、环境配置

### 3.1 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 / Ubuntu 18.04 | Windows 11 / Ubuntu 22.04 |
| CPU | 4核 | 8核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB | 100GB+ SSD |
| Java | 11+ | 11 (Spring Boot + Spark) |
| Maven | 3.6+ | 3.8+ |
| Node.js | 16+ | 18+ |
| Python | 3.8+ | 3.10+ (模型训练/NLP) |

### 3.2 安装依赖

#### Java后端 (Maven)

```bash
# 编译所有模块
mvn clean install -DskipTests

# 仅编译web-backend
mvn clean package -pl web-backend -am -DskipTests
```

**主要依赖** (pom.xml):
```xml
spring-boot-starter-web          2.7.x
spring-boot-starter-security     2.7.x
spring-boot-starter-data-jpa     2.7.x
mybatis-plus-boot-starter        3.5.1
druid-spring-boot-starter        1.2.8
mysql-connector-java             8.0.33
jjwt                             0.11.5
spark-core_2.12                  3.0.0
hbase-client                     2.4.11
```

#### Python后端依赖 (Flask + NLP)

```bash
cd backend-python
pip install -r requirements.txt
```

**主要依赖** (requirements.txt):
```
Flask==2.3.3                 # Web框架
Flask-CORS==4.0.0            # 跨域支持
python-dotenv==1.0.0         # 环境变量加载
requests==2.31.0             # HTTP客户端
numpy>=1.24.0                # 数值计算
pandas>=2.0.0                # 数据处理
jieba==0.42.1                # 中文分词
pyspark==3.5.0               # Spark Python API
# 可选依赖 (按需安装):
# pymysql>=1.1.0             # MySQL驱动
# DBUtils>=3.0.0             # 数据库连接池
# torch>=2.1.0               # PyTorch (BERT需要)
# transformers>=4.35.0       # HuggingFace Transformers
```

> **注意**：`pymysql` 和 `DBUtils` 用于MySQL连接池，Pipeline功能必需。`torch` 和 `transformers` 为可选，不安装时系统仅使用词典方法进行情感分析。

#### Python模型训练依赖 (可选)

```bash
cd model-training
pip install -r requirements.txt
```

#### Node.js依赖 (前端)

```bash
cd web-frontend
npm install
```

### 3.3 环境变量配置

创建 `.env` 文件（参考 `.env.example`）：

```env
# ===== Flask后端配置 =====
FLASK_HOST=0.0.0.0
FLASK_RUN_PORT=5000
FLASK_DEBUG=False
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-in-production
LOG_LEVEL=INFO

# ===== 数据库配置 (MySQL 8.0) =====
DB_HOST=localhost
DB_PORT=3306
DB_NAME=weibo_prod
DB_USERNAME=prod_user
DB_PASSWORD=your_secure_password

# ===== Redis配置 =====
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ===== CORS配置 =====
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ===== HDFS配置 =====
HDFS_DEFAULT_FS=hdfs://localhost:9000

# ===== HBase配置 =====
HBASE_HOST=localhost

# ===== 邮件配置（验证码） =====
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASS=your_auth_code

# ===== Spark配置 =====
SPARK_MASTER=local[*]
SPARK_DRIVER_MEMORY=2g
SPARK_EXECUTOR_MEMORY=2g
```

### 3.4 数据库初始化

执行 `deployment/sql/init.sql` 脚本，该脚本会自动创建数据库、用户和全部12张表：

```bash
mysql -u root -p < deployment/sql/init.sql
```

脚本主要内容：

```sql
-- 创建数据库和用户
CREATE DATABASE IF NOT EXISTS weibo_prod
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'prod_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON weibo_prod.* TO 'prod_user'@'localhost';

USE weibo_prod;
```

**数据库包含12张表**（详见第六章）：

| 分类 | 表名 | 说明 |
|------|------|------|
| **Java后端** | `users` | 用户表 (认证/角色) |
| | `collection_task` | 采集任务表 |
| | `sentiment_result` | 情感结果表 (Java版) |
| | `spark_jobs` | Spark作业表 |
| | `system_log` | 系统日志表 |
| **Python后端** | `weibo_core_data` | ★ 微博核心数据表 |
| | `sentiment_analysis_results` | ★ 情感分析结果表 (级联策略) |
| | `tri_dimension_ranking` | ★ 三维度排序结果表 |
| | `crawl_batch_log` | 爬虫批次日志表 |
| | `crawl_request_log` | 爬虫请求日志表 |
| | `data_quality_log` | 数据质量日志表 |
| | `system_configs` | 系统配置表 |

> **注意**：Python后端的7张核心表通过 `database_service.py` 自动检测并创建（若不存在），无需手动执行DDL。

---

## 四、模块详解

### 4.1 数据采集模块

**文件位置**: `common/src/main/java/com/weibo/collector/spider/WeiboSpider.java`

#### 功能特性

| 功能 | 说明 |
|------|------|
| 热搜榜采集 | 获取微博实时热搜榜单 |
| 关键词搜索 | 按关键词搜索微博内容 |
| 用户微博 | 获取指定用户的微博列表 |
| Cookie池 | 多账号Cookie轮换 |
| UA池 | 随机User-Agent切换 |
| 请求限流 | 2-5秒随机延迟 |

#### 核心类

```python
class WeiboSpider:
    """微博爬虫主类"""
    
    def get_hot_search(self) -> List[Dict]:
        """获取热搜榜"""
        
    def search_weibo(self, keyword: str, page: int = 1) -> List[Dict]:
        """关键词搜索"""
        
    def get_user_weibo(self, user_id: str, page: int = 1) -> List[Dict]:
        """获取用户微博"""
```

#### 采集数据字段

```python
{
    'id': '微博ID',
    'mid': '微博MID',
    'text': '微博正文',
    'source': '发布来源',
    'created_at': '发布时间',
    'user': {
        'id': '用户ID',
        'screen_name': '用户昵称',
        'followers_count': '粉丝数',
        'verified': '是否认证'
    },
    'reposts_count': '转发数',
    'comments_count': '评论数',
    'attitudes_count': '点赞数',
    'pics': ['图片URL列表'],
    'video_url': '视频URL'
}
```

#### 4.1.2 数据清洗

**文件位置**: `backend-python/spark/data_cleaner.py` (Python Spark脚本)

##### 清洗流程

```
原始数据 → 数据去重 → HTML清理 → URL提取 → @提及提取 
        → 表情处理 → 中文分词 → 停用词过滤 → 特征提取 → 清洗后数据
```

##### 核心功能

| 功能 | 方法 | 说明 |
|------|------|------|
| MD5去重 | `deduplicate_by_md5()` | 基于文本MD5哈希去重 |
| SimHash去重 | `deduplicate_by_simhash()` | 相似文本检测 |
| HTML清理 | `clean_html()` | 移除HTML标签 |
| URL提取 | `extract_urls()` | 提取并移除URL |
| 中文分词 | `tokenize()` | jieba分词 |
| TF-IDF | `extract_tfidf()` | 词频-逆文档频率 |
| Word2Vec | `extract_word2vec()` | 词向量 |

##### SimHash算法

```python
class SimHash:
    """SimHash相似度检测"""
    
    def __init__(self, hash_bits: int = 64):
        self.hash_bits = hash_bits
    
    def compute(self, tokens: List[str]) -> int:
        """计算SimHash指纹"""
        
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """计算海明距离"""
        
    def is_similar(self, hash1: int, hash2: int, threshold: int = 3) -> bool:
        """判断是否相似"""
```

### 4.2 算法模型设计

本系统的核心算法包括两个部分：**情感分析混合模型**和**情感‑热度‑时效三维度排序模型**。前者负责准确识别微博文本的情感倾向，后者综合情感强度、互动热度与时效性，对微博话题进行科学排序。

#### 4.2.1 情感分析混合模型

为兼顾情感分析的准确性与计算效率，本文提出一种**级联混合策略**，融合基于词典的快速分类方法与基于ChineseBERT的深度分类模型。处理流程如图4-3所示，其核心思想是：先用轻量级词典方法对大部分简单样本进行快速判断，仅对词典难以确定的高歧义样本调用复杂的深度学习模型，从而在保持高准确率的同时大幅降低平均推理时间。

**（1）词典情感分析**

词典方法依赖情感词典和规则库。本文综合HowNet情感词典、大连理工大学情感词汇本体库以及自建的微博表情词典、否定词词典和程度副词词典，构建了覆盖约28,000个情感词条的领域词典。对于输入文本 \(T\)，经分词后逐词匹配，得分计算规则如下：

- 匹配到基础情感词，累加其情感得分（正面为正，负面为负）；
- 遇到否定词（如"不""没""无"），反转后续情感词的极性；
- 遇到程度副词（如"非常""稍微"），按强度系数（0.5~2.0）调整相邻情感词的权重。

最终累加得分经归一化后映射到区间 \([-1, 1]\)，记为 \(S_{\text{dict}}(T)\)。

**（2）ChineseBERT 深度模型**

对于词典方法难以处理的复杂文本（如含有反语、网络新词、长距离依赖等），本文采用微调后的ChineseBERT模型。ChineseBERT在BERT基础上引入了拼音和笔画特征，更擅长处理中文的语音和字形信息，对微博中的网络用语和表情符号具有更好的适应性。模型以 `hfl/chinese-bert-wwm-ext` 为预训练基座，在公开微博情感数据集（约10万条）上微调，训练参数为：batch size = 32，learning rate = 2e-5，epochs = 3。微调后模型在测试集上的准确率达到89.2%。对于输入文本 \(T\)，模型输出三类情感（正面、负面、中性）的概率，将其映射为情感得分 \(S_{\text{bert}}(T) \in [-1, 1]\)。

**（3）级联决策公式**

本文采用级联策略，而非简单的加权平均。决策公式如下：

\[
S_{\text{final}}(T) = 
\begin{cases} 
S_{\text{dict}}(T), & \text{if } |S_{\text{dict}}(T)| > \theta \\[6pt]
S_{\text{bert}}(T), & \text{otherwise}
\end{cases} \tag{4-2}
\]

其中 \(\theta\) 为置信度阈值。通过验证集搜索（以准确率为优化目标），本文确定 \(\theta = 0.7\)。当词典得分的绝对值大于0.7时，认为词典判断已足够可靠，直接采用词典结果；否则，调用ChineseBERT模型进行二次精确分析。

该策略使得约77.5%的微博文本仅通过词典方法即可完成情感分析，仅22.5%的复杂样本需调用BERT，整体推理速度相比纯BERT提升约2.6倍，同时最终准确率达到86.2%，优于单一词典方法（79.2%）。

#### 4.2.2 情感‑热度‑时效三维度排序模型

传统舆情排序方法往往只关注热度或时间单一维度，容易遗漏情感强烈但尚未大规模传播的潜在热点。为此，本文设计了一个三维度排序模型，综合**情感强度**、**互动热度**和**时效性**，计算每条微博的综合得分，用于话题排序与推荐。模型结构如图4-4所示。

**（1）情感强度归一化**

对于微博 \(w\)，其最终情感得分 \(S_{\text{final}}(w)\) 由公式(4-2)给出。舆情监控中，无论正面还是负面，极端情绪均具有较高的分析价值，因此取绝对值作为情感强度。为与其他维度统一量纲，将其线性映射到 \([0, 1]\) 区间：

\[
\text{Intensity}(w) = \frac{|S_{\text{final}}(w)| + 1}{2} \tag{4-3}
\]

**（2）互动热度计算与归一化**

互动热度仅基于微博的转发、评论、点赞数量，不包含时间衰减。采用对数函数平滑极端值，并赋予评论更高的权重（因为评论通常蕴含更丰富的用户情感）：

\[
H_{\text{raw}}(w) = \log_{10}\!\bigl(1 + \lambda_r R_w + \lambda_c C_w + \lambda_l L_w\bigr) \tag{4-4}
\]

其中 \(R_w, C_w, L_w\) 分别为微博 \(w\) 的转发数、评论数、点赞数；\(\lambda_r = 1\)，\(\lambda_c = 2\)，\(\lambda_l = 1\)。

为使热度得分与情感强度处于同一量级，对训练数据集 \(\mathcal{D}\) 中的所有微博进行最大‑最小归一化：

\[
H_{\text{norm}}(w) = \frac{H_{\text{raw}}(w)}{\max\limits_{w'\in\mathcal{D}} H_{\text{raw}}(w')} \tag{4-5}
\]

归一化后 \(H_{\text{norm}}(w) \in [0, 1]\)。分母可预先计算并存储，避免重复扫描。

**（3）时效性得分（半衰期模型）**

时效性反映微博的新旧程度，新产生的微博应获得更高关注。本文采用半衰期参数化模型，而非传统的指数衰减，使参数更具可解释性：

\[
\gamma(\Delta t) = 2^{-\Delta t / H} \tag{4-6}
\]

其中 \(\Delta t\) 为微博发布时间距当前的小时数；\(H\) 为半衰期，表示热度减半所需的小时数。本文取 \(H = 12\)，即每12小时得分减半。该值可根据不同应用场景（如长期话题追踪）灵活调整。

**（4）综合得分与排序**

最终综合得分由情感强度、互动热度、时效性三项加权求和得到：

\[
\boxed{\text{Score}(w) = \omega_1 \cdot \text{Intensity}(w) + \omega_2 \cdot H_{\text{norm}}(w) + \omega_3 \cdot \gamma(\Delta t)} \tag{4-7}
\]

权重系数满足 \(\omega_1 + \omega_2 + \omega_3 = 1\)。本文通过网格搜索在验证集上优化权重，以排序质量指标 NDCG@10 为准则，确定默认权重为：\(\omega_1 = 0.4\)（情感强度），\(\omega_2 = 0.4\)（互动热度），\(\omega_3 = 0.2\)（时效性）。该配置既保证了情感强烈微博的优先展示，又兼顾了传播热度和时效性。

**（5）模型优势**

- **多维度平衡**：避免单一维度排序的片面性，尤其能提前发现情感强烈但热度尚低的潜在热点。
- **时效敏感**：半衰期参数化使新旧微博的得分衰减直观可控，便于业务理解。
- **可解释性强**：各维度得分均有明确的业务含义，用户可查看每项得分及其贡献。

#### 参数汇总

为便于查阅，将上述所有算法参数汇总于表4-2。

**表4-2 算法模型参数配置**

| 参数名称 | 符号 | 默认值 | 说明 |
|----------|------|--------|------|
| 词典置信度阈值 | \(\theta\) | 0.7 | 级联策略中判断是否直接输出词典结果 |
| 转发权重 | \(\lambda_r\) | 1 | 互动热度中的转发系数 |
| 评论权重 | \(\lambda_c\) | 2 | 互动热度中的评论系数 |
| 点赞权重 | \(\lambda_l\) | 1 | 互动热度中的点赞系数 |
| 半衰期（小时） | \(H\) | 12 | 时效性得分的半衰期 |
| 情感强度权重 | \(\omega_1\) | 0.4 | 综合得分中情感强度占比 |
| 互动热度权重 | \(\omega_2\) | 0.4 | 综合得分中互动热度占比 |
| 时效性权重 | \(\omega_3\) | 0.2 | 综合得分中时效性占比 |

### 4.3 存储服务模块

**文件位置**: 
- Java: `common/src/main/java/com/weibo/collector/storage/HdfsDataWriter.java`
- Python: `backend-python/services/storage_service.py`

#### 存储架构

```
┌─────────────────────────────────────────────────────┐
│                   StorageService                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ HDFSClient  │ │ HBaseClient │ │ MySQLClient │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────┘
         │                │                │
    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
    │  HDFS   │      │  HBase  │      │  MySQL  │
    │ 原始数据 │      │ 结构化  │      │ 元数据  │
    │ Parquet │      │ 列式    │      │ 关系型  │
    └─────────┘      └─────────┘      └─────────┘
```

#### HDFS存储

```python
class HDFSClient:
    """HDFS存储客户端"""
    
    PATHS = {
        'raw_data': '/weibo/raw',
        'cleaned_data': '/weibo/cleaned',
        'features': '/weibo/features',
        'models': '/weibo/models',
    }
    
    def save_parquet(self, df, path: str, partition_by: List[str] = None):
        """保存Parquet格式"""
        
    def read_parquet(self, path: str, spark=None):
        """读取Parquet文件"""
```

#### HBase存储

```python
class HBaseClient:
    """HBase存储客户端"""
    
    TABLES = {
        'weibo_raw': {
            'cf_basic': ['id', 'mid', 'text', 'source', 'created_at'],
            'cf_user': ['user_id', 'user_name', 'user_verified'],
            'cf_stats': ['reposts_count', 'comments_count', 'attitudes_count'],
        },
        'weibo_cleaned': {
            'cf_basic': ['id', 'cleaned_text', 'tokens'],
            'cf_features': ['tfidf', 'word2vec', 'sentiment_score'],
        },
    }
    
    def put(self, table_name: str, rowkey: str, data: Dict):
        """写入数据"""
        
    def get(self, table_name: str, rowkey: str) -> Dict:
        """获取数据"""
        
    def scan(self, table_name: str, row_start: str = None, 
             row_stop: str = None, limit: int = 100) -> List[Dict]:
        """扫描表"""
```

### 4.4 流处理模块

**文件位置**: `backend-python/spark/streaming_analyzer.py` (Python Spark脚本)

#### 功能特性

| 功能 | 说明 |
|------|------|
| Socket流 | 接收Socket数据流 |
| 文件流 | 监控文件目录变化 |
| 微批处理 | 可配置批处理间隔 |
| 滑动窗口 | 时间窗口统计 |
| 实时情感分析 | 集成混合分析模型 |

#### 核心实现

```python
class StreamingSentimentAnalyzer:
    """流式情感分析器"""
    
    def start_socket_stream(self, host: str, port: int):
        """启动Socket流处理"""
        
    def start_file_stream(self, input_path: str):
        """启动文件流处理"""
        
    def process_batch(self, df, batch_id):
        """处理微批数据"""
        # 1. 数据清洗
        # 2. 情感分析
        # 3. 三维度排序
        # 4. 存储结果
```

---

## 五、API接口文档

### 5.1 认证接口

#### 用户注册

```http
POST /api/auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123",
    "code": "123456",
    "username": "用户名"
}

Response:
{
    "code": 200,
    "message": "注册成功",
    "data": {
        "accessToken": "token-xxx",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "username": "用户名"
        }
    }
}
```

#### 邮箱密码登录

```http
POST /api/auth/login-by-email
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}

Response:
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "accessToken": "token-xxx",
        "user": {...},
        "loginType": "email_password"
    }
}
```

#### 发送验证码

```http
POST /api/auth/send-code
Content-Type: application/json

{
    "email": "user@example.com",
    "type": "register"  // register/login/reset
}

Response:
{
    "code": 200,
    "message": "验证码已发送",
    "data": {
        "email": "user@example.com",
        "expire_in": 300
    }
}
```

#### 重置密码

```http
POST /api/auth/reset-password
Content-Type: application/json

{
    "email": "user@example.com",
    "code": "123456",
    "newPassword": "newpassword123"
}

Response:
{
    "code": 200,
    "message": "密码重置成功"
}
```

### 5.2 数据采集接口

#### 获取热搜榜

```http
GET /api/crawl/hot-search

Response:
{
    "code": 200,
    "data": {
        "hot_search": [
            {
                "rank": 1,
                "keyword": "热搜关键词",
                "hot_value": 1234567,
                "category": "社会"
            },
            ...
        ],
        "update_time": "2026-04-04 11:00:00"
    }
}
```

#### 关键词搜索

```http
POST /api/crawl/search
Content-Type: application/json

{
    "keyword": "搜索关键词",
    "page": 1,
    "count": 20
}

Response:
{
    "code": 200,
    "data": {
        "weibos": [...],
        "total": 100,
        "page": 1
    }
}
```

### 5.3 情感分析接口

#### 单条分析

```http
POST /api/sentiment/analyze
Content-Type: application/json

{
    "text": "今天心情很好"
}

Response:
{
    "code": 200,
    "data": {
        "text": "今天心情很好",
        "score": 0.85,
        "label": "positive",
        "confidence": 0.92,
        "dict_score": 0.8,
        "bert_score": 0.87
    }
}
```

#### 批量分析

```http
POST /api/sentiment/batch
Content-Type: application/json

{
    "texts": [
        "今天心情很好",
        "这个产品太差了"
    ]
}

Response:
{
    "code": 200,
    "data": {
        "results": [
            {"text": "...", "score": 0.85, "label": "positive"},
            {"text": "...", "score": -0.72, "label": "negative"}
        ],
        "statistics": {
            "total": 2,
            "positive": 1,
            "neutral": 0,
            "negative": 1
        }
    }
}
```

### 5.4 三维度排序接口

#### 获取排序结果

```http
GET /api/tri-dimension/rank?keyword=热搜关键词&limit=50

Response:
{
    "code": 200,
    "data": {
        "items": [
            {
                "weibo_id": "4912345678",
                "content": "微博内容",
                "sentiment_score": 0.85,
                "sentiment_category": "positive",
                "heat_score": 2.78,
                "heat_normalized": 0.65,
                "time_decay": 0.95,
                "composite_score": 0.82,
                "ranking_position": 1
            }
        ],
        "config": {
            "sentiment_weight": 0.4,
            "heat_weight": 0.4,
            "timeliness_weight": 0.2
        }
    }
}
```

#### 基于MySQL数据排序

```http
POST /api/tri-dimension/run-db

Response:
{
    "code": 200,
    "message": "三维度排序完成",
    "data": {
        "total_ranked": 150,
        "top_items": [...],
        "batch_id": "rank_20260404_abc12345"
    }
}
```

#### 获取MySQL排序结果

```http
GET /api/tri-dimension/ranking-from-db?limit=50

Response:
{
    "code": 200,
    "data": {
        "rankings": [
            {
                "weibo_id": 4912345678,
                "composite_score": 0.8234,
                "ranking_position": 1,
                "sentiment_score": 0.85,
                "popularity_score": 0.72,
                "time_decay": 0.95,
                "popularity_class": "high"
            }
        ],
        "total": 150
    }
}
```

#### 获取算法公式说明

```http
GET /api/tri-dimension/formula

Response:
{
    "code": 200,
    "data": {
        "version": "v2.0 级联策略+半衰期",
        "cascade_strategy": "S_final = S_dict if |S_dict|>θ else S_bert, θ=0.7",
        "sentiment_normalization": "N(S) = (|S|+1)/2",
        "heat_formula": "H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)",
        "time_decay": "γ(t) = 2^(-Δt/H), H=12h",
        "final_score": "Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)",
        "weights": {"ω₁": 0.4, "ω₂": 0.4, "ω₃": 0.2}
    }
}
```

### 5.5 数据流水线接口

#### 运行全流程

```http
POST /api/pipeline/run

Request (可选):
{
    "limit": 100,
    "batch_name": "手动触发"
}

Response:
{
    "code": 200,
    "message": "流水线执行完成",
    "data": {
        "sentiment_stage": {"processed": 100, "method_stats": {"lexicon": 65, "bert": 35}},
        "ranking_stage": {"ranked": 100, "top_score": 0.92},
        "duration_seconds": 12.5
    }
}
```

#### 异步运行

```http
POST /api/pipeline/run-async

Response:
{
    "code": 202,
    "message": "流水线已在后台启动",
    "data": {"task_id": "pipeline_20260404_abc"}
}
```

#### 获取流水线状态

```http
GET /api/pipeline/status

Response:
{
    "code": 200,
    "data": {
        "status": "idle",
        "last_run": "2026-04-04T17:00:00",
        "last_duration_seconds": 12.5,
        "total_runs": 5
    }
}
```

#### 获取数据库统计

```http
GET /api/pipeline/stats

Response:
{
    "code": 200,
    "data": {
        "weibo_core_data": {"total": 5000, "unprocessed": 200, "unranked": 300},
        "sentiment_analysis_results": {"total": 4800},
        "tri_dimension_ranking": {"total": 4700}
    }
}
```

#### 获取最新排名

```http
GET /api/pipeline/ranking?limit=20

Response:
{
    "code": 200,
    "data": {
        "rankings": [...],
        "total": 4700
    }
}
```

### 5.6 情感分析扩展接口

#### 基于MySQL数据分析

```http
POST /api/sentiment/run-db

Response:
{
    "code": 200,
    "message": "情感分析完成",
    "data": {
        "total_analyzed": 200,
        "results_summary": {
            "positive": 80,
            "neutral": 70,
            "negative": 50
        },
        "method_stats": {"lexicon": 130, "bert": 70}
    }
}
```

### 5.7 实时监控接口

#### 获取监控流

```http
GET /api/monitor/stream?keywords=关键词1,关键词2

Response (SSE):
data: {"type": "weibo", "data": {...}}
data: {"type": "stats", "data": {...}}
data: {"type": "alert", "data": {...}}
```

---

## 六、数据库设计

数据库名：`weibo_prod`，字符集：`utf8mb4`，共12张表，分为Java后端表（5张）和Python后端核心表（7张）。

### 6.1 ER图

```
┌─────────────┐       ┌──────────────────┐       ┌───────────────────────────┐
│   users     │       │ collection_task   │       │     spark_jobs            │
├─────────────┤       ├──────────────────┤       ├───────────────────────────┤
│ id (PK)     │──1:N──│ id (PK)          │       │ id (PK)                   │
│ username    │       │ task_name        │       │ job_id (UK)               │
│ password    │       │ keywords         │       │ job_name / status         │
│ email       │       │ status           │       └───────────────────────────┘
│ roles       │       │ user_id (FK)     │
└─────────────┘       └──────────────────┘       ┌───────────────────────────┐
                                                  │     system_log            │
┌──────────────────────────────────────┐          ├───────────────────────────┤
│          weibo_core_data  ★          │          │ id (PK)                   │
├──────────────────────────────────────┤          │ username / operation      │
│ id (PK)                              │          └───────────────────────────┘
│ weibo_id (UK)                        │
│ content / created_at                 │
│ user_id / user_name / verified       │──────────────────────────────┐
│ reposts_count / comments_count       │                              │
│ attitudes_count / followers_count    │                              │
│ keyword / batch_id                   │                              │
│ is_processed / is_ranked             │                              │
│ graduation_batch / student_id        │                              │
└──────────┬───────────────────────────┘                              │
           │ weibo_id                                                 │
           ├──────────────────────────┐                               │
           ▼                          ▼                               │
┌──────────────────────────┐  ┌────────────────────────────┐         │
│sentiment_analysis_results│  │ tri_dimension_ranking  ★  │         │
├──────────────────────────┤  ├────────────────────────────┤         │
│ id (PK)                  │  │ id (PK)                    │         │
│ weibo_id (UK联合)        │  │ weibo_id (UK联合)          │         │
│ dict_score / bert_score  │  │ sentiment_score            │         │
│ hybrid_score             │  │ raw_popularity             │         │
│ sentiment_class          │  │ popularity_score            │         │
│ analysis_method          │  │ time_decay                 │         │
│ model_version            │  │ composite_score ★          │         │
│ graduation_flag          │  │ ranking_position           │         │
└──────────────────────────┘  │ batch_id / algorithm_version│        │
                              └────────────────────────────┘         │
                                                                     │
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────┐ │
│ crawl_batch_log   │  │ crawl_request_log  │  │ data_quality_log │ │
├───────────────────┤  ├────────────────────┤  ├──────────────────┤ │
│ batch_id (UK)     │──│ batch_id (IDX)     │  │ batch_id (IDX)   │ │
│ task_name/type    │  │ request_url        │  │ check_type       │ │
│ keywords (JSON)   │  │ status_code        │  │ quality_score    │ │
│ total_weibos      │  │ response_time_ms   │  │ issues (JSON)    │ │
│ status            │  │ success            │  │ check_time       │ │
└───────────────────┘  └────────────────────┘  └──────────────────┘
                                                                     
┌────────────────────┐                                               
│  system_configs    │                                               
├────────────────────┤                                               
│ config_key (UK)    │                                               
│ config_value       │                                               
│ config_type        │                                               
└────────────────────┘                                               
```

### 6.2 Java后端表结构（Spring Boot）

#### users表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| username | VARCHAR(50) | 用户名，唯一 |
| password | VARCHAR(255) | BCrypt密码哈希 |
| email | VARCHAR(100) | 邮箱，唯一 |
| roles | VARCHAR(255) | 角色：ROLE_ADMIN,ROLE_USER |
| status | VARCHAR(20) | 状态：ACTIVE/DISABLED |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### collection_task表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| task_name | VARCHAR(255) | 任务名称 |
| keywords | TEXT | 采集关键词 |
| status | VARCHAR(20) | 状态 |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| user_id | BIGINT | 外键→users.id |
| created_at | DATETIME | 创建时间 |

#### sentiment_result表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| task_id | BIGINT | 外键→collection_task.id |
| weibo_id | VARCHAR(50) | 微博ID，唯一 |
| content | TEXT | 微博内容 |
| sentiment | VARCHAR(20) | 情感标签 |
| confidence | DOUBLE | 置信度 |
| publish_time | DATETIME | 发布时间 |

#### spark_jobs表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| job_id | VARCHAR(255) | 作业ID，唯一 |
| job_name | VARCHAR(255) | 作业名称 |
| status | VARCHAR(255) | 状态 |
| submit_time | DATETIME | 提交时间 |
| finish_time | DATETIME | 完成时间 |
| arguments | TEXT | 运行参数 |

#### system_log表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| username | VARCHAR(50) | 操作用户 |
| operation | VARCHAR(255) | 操作描述 |
| method | VARCHAR(255) | 请求方法 |
| params | TEXT | 请求参数 |
| execution_time | BIGINT | 执行耗时(ms) |
| ip_address | VARCHAR(50) | 客户端IP |

### 6.3 Python后端核心表（Flask + DatabaseService）

> 以下7张表由 `database_service.py` 在应用启动时自动检测并创建，所有表均包含 `graduation_batch` 和 `student_id` 字段用于毕业设计标记。

#### weibo_core_data表 ★

微博核心数据表，存储爬虫采集的原始微博数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| weibo_id | BIGINT | 微博ID，**唯一** |
| content | TEXT | 微博正文 |
| created_at | DATETIME | 发布时间 |
| crawled_at | DATETIME | 采集时间 |
| user_id | BIGINT | 用户ID |
| user_name | VARCHAR(128) | 用户昵称 |
| verified | TINYINT | 是否认证 (0/1) |
| followers_count | INT | 粉丝数 |
| reposts_count | INT | 转发数 (R) |
| comments_count | INT | 评论数 (C) |
| attitudes_count | INT | 点赞数 (L) |
| has_image | TINYINT | 是否有图片 |
| has_video | TINYINT | 是否有视频 |
| image_urls | JSON | 图片URL列表 |
| location | VARCHAR(128) | 发布位置 |
| topics | JSON | 话题标签 |
| source | VARCHAR(128) | 来源（微博客户端） |
| keyword | VARCHAR(128) | 采集关键词 |
| batch_id | VARCHAR(64) | 采集批次ID |
| **is_processed** | TINYINT | 是否已情感分析 (0/1) |
| **is_ranked** | TINYINT | 是否已三维度排序 (0/1) |
| graduation_batch | TINYINT | 毕业设计批次 |
| student_id | VARCHAR(20) | 学号 (2022407443) |

**索引**: `uk_weibo_id`, `idx_created_at`, `idx_user_id`, `idx_keyword`, `idx_batch_id`, `idx_graduation`

#### sentiment_analysis_results表 ★

情感分析结果表，存储级联策略分析的详细结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| weibo_id | BIGINT | 微博ID |
| dict_score | DECIMAL(5,4) | 词典得分 |
| bert_score | DECIMAL(5,4) | BERT得分 |
| hybrid_score | DECIMAL(5,4) | 混合得分（级联策略最终值） |
| sentiment_class | ENUM | positive/neutral/negative |
| intensity | DECIMAL(3,2) | 情感强度 N(S) |
| confidence | DECIMAL(3,2) | 置信度 |
| dict_positive_count | INT | 词典正面词数 |
| dict_negative_count | INT | 词典负面词数 |
| bert_positive_prob | DECIMAL(5,4) | BERT正面概率 |
| bert_neutral_prob | DECIMAL(5,4) | BERT中性概率 |
| bert_negative_prob | DECIMAL(5,4) | BERT负面概率 |
| **analysis_method** | VARCHAR(32) | cascade-lexicon / cascade-bert |
| **model_version** | VARCHAR(32) | v2.0.0 |
| analysis_time | DATETIME | 分析时间 |
| processing_time_ms | INT | 处理耗时(毫秒) |

**唯一键**: `(weibo_id, analysis_method)`

#### tri_dimension_ranking表 ★

三维度排序结果表，存储综合得分和排名，为本系统的**核心创新点**。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| weibo_id | BIGINT | 微博ID |
| sentiment_score | DECIMAL(5,4) | 情感得分 |
| sentiment_category | VARCHAR(32) | 情感分类 |
| reposts_count | INT | 转发数 |
| comments_count | INT | 评论数 |
| attitudes_count | INT | 点赞数 |
| raw_popularity | DECIMAL(10,4) | 原始热度 H_raw（log平滑后） |
| popularity_score | DECIMAL(10,4) | 归一化热度 H_norm |
| popularity_class | ENUM | high/medium/low |
| time_decay | DECIMAL(5,4) | 时间衰减因子 γ(t) |
| alpha_weight | DECIMAL(3,2) | 情感权重 ω₁ (默认0.40) |
| beta_weight | DECIMAL(3,2) | 热度权重 ω₂ (默认0.40) |
| **composite_score** | DECIMAL(10,4) | **综合排序得分** Score(w) |
| **ranking_position** | INT | 排名位置 |
| batch_id | VARCHAR(64) | 计算批次ID |
| algorithm_version | VARCHAR(32) | v2.0.0 (级联+半衰期) |

**唯一键**: `(weibo_id, batch_id)`，**索引**: `idx_composite_score DESC`, `idx_ranking`

#### crawl_batch_log表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| batch_id | VARCHAR(64) | 批次ID，唯一 |
| task_name | VARCHAR(128) | 任务名称 |
| task_type | VARCHAR(64) | 任务类型 |
| keywords | JSON | 采集关键词列表 |
| status | ENUM | pending/running/completed/failed |
| total_weibos | INT | 采集总数 |
| success_count | INT | 成功数 |
| failure_count | INT | 失败数 |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| error_message | TEXT | 错误信息 |

#### crawl_request_log表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| batch_id | VARCHAR(64) | 批次ID |
| request_url | VARCHAR(512) | 请求URL |
| request_type | VARCHAR(32) | 请求类型 |
| status_code | INT | HTTP状态码 |
| response_time_ms | INT | 响应时间(毫秒) |
| success | TINYINT | 是否成功 |
| error_message | TEXT | 错误信息 |

#### data_quality_log表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| batch_id | VARCHAR(64) | 批次ID |
| check_type | VARCHAR(32) | 检查类型 |
| total_records | INT | 总记录数 |
| valid_records | INT | 有效记录数 |
| invalid_records | INT | 无效记录数 |
| quality_score | DECIMAL(5,2) | 质量得分 |
| issues | JSON | 问题详情 |

#### system_configs表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键，自增 |
| config_key | VARCHAR(64) | 配置键，唯一 |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(32) | 类型：string/number/json |
| description | VARCHAR(256) | 描述 |

---

## 七、前端页面

### 7.1 页面列表

| 页面 | 路由 | 组件 | 功能 |
|------|------|------|------|
| 登录 | /login | Login.vue | 用户登录 |
| 注册 | /register | Register.vue | 用户注册 |
| 找回密码 | /forgot-password | ForgotPassword.vue | 密码重置 |
| 仪表板 | /dashboard | Dashboard.vue | 系统概览 |
| 数据采集 | /collection | DataCollection.vue | 采集任务管理 |
| 数据预处理 | /preprocess | DataPreprocess.vue | 数据清洗 |
| 情感分析 | /sentiment | SentimentAnalysis.vue | 情感分析结果 |
| 三维度分析 | /tri-dimension | TriDimensionAnalysis.vue | 三维度排序 |
| 热点话题 | /topics | HotTopics.vue | 热点追踪 |
| 实时监控 | /realtime | RealTimeMonitor.vue | 实时舆情 |
| 数据可视化 | /visualization | Visualization.vue | 图表展示 |
| 报告生成 | /reports | Reports.vue | 分析报告 |
| 系统管理 | /admin | SystemAdmin.vue | 系统配置 |

### 7.2 可视化图表

| 图表类型 | 使用场景 | 实现库 |
|----------|----------|--------|
| 折线图 | 情感趋势、热度变化 | ECharts |
| 柱状图 | 情感分布对比 | ECharts |
| 饼图 | 情感占比 | ECharts |
| 词云图 | 热点关键词 | ECharts |
| 散点图 | 三维度分布 | ECharts |
| 热力图 | 时间分布 | ECharts |
| 地图 | 地域分布 | ECharts |
| 雷达图 | 多维度对比 | ECharts |
| 网络图 | 传播关系 | ECharts |

### 7.3 响应式设计

- 支持桌面端（1920×1080及以上）
- 支持平板端（768×1024）
- 支持移动端（375×667）

---

## 八、部署指南

### 8.1 开发环境部署

#### 一键启动

```bash
# Windows
双击 start-system.bat

# 或分别启动各服务：

# 1. 编译Java后端
mvn clean package -pl web-backend -am -DskipTests

# 2. 启动Spring Boot后端 (:8081)
java -jar web-backend/target/web-backend-1.0-SNAPSHOT.jar --spring.profiles.active=dev

# 3. 启动Python Flask后端 (:5000)
cd backend-python
pip install -r requirements.txt
python app.py

# 4. 启动前端 (:5173)
cd web-frontend && npm run dev
```

#### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost:5173 | Vue 3开发服务器 |
| Java后端 | http://localhost:8081/api | Spring Boot (认证/用户) |
| Python后端 | http://localhost:5000 | Flask (NLP/分析/排序) |
| Swagger文档 | http://localhost:8081/api/swagger-ui.html | Java API文档 |

### 8.2 Docker部署

配置文件位于 `deployment/docker-compose.yml`，使用环境变量文件管理敏感配置。

#### 准备工作

```bash
# 1. 复制环境变量模板
cp deployment/.env.docker.example deployment/.env.docker

# 2. 修改 .env.docker 中的敏感配置
#    必须设置: SECRET_KEY, DB_ROOT_PASSWORD, DB_PASSWORD
```

#### docker-compose.yml（实际配置）

```yaml
version: '3.8'

services:
  # Flask后端 (:5000)
  web:
    build:
      context: ..
      dockerfile: deployment/docker/Dockerfile
    container_name: weibo_sentiment_web
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "${WEB_PORT:-5000}:5000"
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY}
      - DB_HOST=db
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-weibo_sentiment}
      - DB_USERNAME=${DB_USER:-weibo_user}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
    volumes:
      - ../logs:/app/logs
      - ../backend/model_cache:/app/model_cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MySQL 8.0
  db:
    image: mysql:8.0
    container_name: weibo_sentiment_db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-weibo_sentiment}
      MYSQL_USER: ${DB_USER:-weibo_user}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    ports:
      - "${DB_PORT:-3306}:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 5

  # Redis 7
  redis:
    image: redis:7-alpine
    container_name: weibo_sentiment_redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # 前端 (可选，开发时使用)
  frontend:
    build:
      context: ../web-frontend
      dockerfile: ../deployment/docker/Dockerfile.frontend
    container_name: weibo_sentiment_frontend
    ports:
      - "${FRONTEND_PORT:-5173}:80"
    depends_on:
      - web
    profiles:
      - with-frontend

networks:
  weibo-network:
    driver: bridge

volumes:
  mysql_data:
  redis_data:
```

#### 启动命令

```bash
cd deployment

# 仅启动后端+数据库+Redis
docker-compose --env-file .env.docker up -d

# 包含前端
docker-compose --env-file .env.docker --profile with-frontend up -d

# 查看日志
docker-compose logs -f web
```

### 8.3 生产环境部署

#### Nginx配置（双后端代理）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/weibo-sentiment/dist;
        try_files $uri $uri/ /index.html;
    }

    # Java后端API代理 (认证/用户管理)
    location /api/auth {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Python后端API代理 (情感分析/排序/采集)
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 启动命令

```bash
# Java后端
java -jar web-backend/target/web-backend-1.0-SNAPSHOT.jar \
  --spring.profiles.active=prod \
  --server.port=8081

# Python后端
cd backend-python
FLASK_ENV=production python app.py
```

---

## 九、使用说明

### 9.1 快速开始

1. **初始化数据库**
   ```bash
   mysql -u root -p < deployment/sql/init.sql
   ```

2. **启动后端服务**
   ```bash
   # Java后端 (认证/用户)
   mvn clean package -pl web-backend -am -DskipTests
   java -jar web-backend/target/web-backend-1.0-SNAPSHOT.jar --spring.profiles.active=dev

   # Python后端 (NLP/分析/排序)
   cd backend-python
   pip install -r requirements.txt
   python app.py
   ```

3. **启动前端**
   ```bash
   cd web-frontend && npm install && npm run dev
   ```

4. **访问系统**
   - 前端页面：http://localhost:5173
   - Python API：http://localhost:5000
   - Java API：http://localhost:8081/api

5. **登录系统**
   - 使用管理员账号登录（见9.3）

### 9.2 功能使用

#### 数据采集

1. 进入"数据采集"页面
2. 选择采集类型（热搜/关键词/用户）
3. 配置采集参数
4. 点击"开始采集"
5. 数据自动存入 `weibo_core_data` 表

#### 数据流水线（一键全流程）

1. 调用 `POST /api/pipeline/run` 或 `POST /api/pipeline/run-async`
2. 流水线自动执行三个阶段：
   - **阶段1**：读取 `weibo_core_data` 中 `is_processed=0` 的微博
   - **阶段2**：执行级联情感分析（词典优先，BERT兜底），结果写入 `sentiment_analysis_results`
   - **阶段3**：执行三维度排序（情感+热度+时效），结果写入 `tri_dimension_ranking`
3. 通过 `GET /api/pipeline/stats` 查看各表数据量
4. 通过 `GET /api/pipeline/ranking?limit=20` 查看最新排名

#### 情感分析

1. 进入"情感分析"页面
2. **在线分析**：输入文本，调用 `POST /api/sentiment/analyze`
3. **批量分析**：选择已采集数据，调用 `POST /api/sentiment/run-db`
4. 查看情感分布图表（正面/中性/负面）
5. 查看级联策略命中统计（词典占比 vs BERT占比）

#### 三维度排序

1. 进入"三维度分析"页面
2. 调用 `POST /api/tri-dimension/run-db` 执行排序
3. 调整权重参数（ω₁=情感, ω₂=热度, ω₃=时效）
4. 查看综合排序结果（`GET /api/tri-dimension/ranking-from-db`）
5. 查看算法公式说明（`GET /api/tri-dimension/formula`）

#### 实时监控

1. 进入"实时监控"页面
2. 添加监控关键词
3. 设置预警规则
4. 查看实时数据流（SSE）
5. 接收预警通知

### 9.3 演示账号

| 账号类型 | 用户名 | 密码 | 说明 |
|----------|--------|------|------|
| 管理员 | admin | admin | init.sql预置，BCrypt加密 |
| 普通用户 | 自行注册 | - | 通过前端注册页面 |

> **安全提示**：管理员默认密码为 `admin`，首次登录后请立即修改。

---

## 十、常见问题

### Q1: Java后端启动失败

**问题**: `java.lang.ClassNotFoundException` 或 Maven编译失败

**解决**: 
```bash
# 重新编译
mvn clean install -DskipTests

# 确认Java版本
java -version   # 需要Java 11+
mvn -version    # 需要Maven 3.6+
```

### Q2: Python后端启动失败

**问题**: `ModuleNotFoundError` 或 Flask导入错误

**解决**:
```bash
cd backend-python
pip install -r requirements.txt

# 常见警告（不影响运行）：
# - "BERT model not available" → ChineseBERT未下载，词典方法仍可用
# - "DBUtils not installed" → 安装: pip install DBUtils PyMySQL
```

### Q3: 前端启动失败

**问题**: `npm ERR! code ENOENT`

**解决**:
```bash
cd web-frontend
npm install
npm run dev
```

### Q4: 数据库连接失败

**问题**: `Can't connect to MySQL server` 或 `Access denied`

**解决**:
1. 确认MySQL服务已启动：`systemctl status mysql` 或 `net start mysql`
2. 确认数据库已创建：`mysql -u root -p < deployment/sql/init.sql`
3. 检查 `.env` 中的 `DB_HOST`、`DB_NAME`（应为 `weibo_prod`）、`DB_USERNAME`（应为 `prod_user`）
4. Java后端：检查 `application-dev.yml` 中的数据源配置
5. Python后端：检查环境变量或 `.env` 文件

### Q5: 情感分析速度慢

**问题**: BERT模型推理慢

**解决**:
1. 系统使用**级联策略**，约65%的文本仅通过词典分析（毫秒级），仅35%调用BERT
2. 如仍慢，可调高词典置信度阈值 θ（默认0.7），减少BERT调用比例
3. 使用GPU加速（需要CUDA + PyTorch GPU版）
4. 减小批处理大小：`POST /api/pipeline/run` 中设置 `"limit": 50`

### Q6: 采集数据为空

**问题**: 微博采集返回空数据

**解决**:
1. 检查Cookie是否有效：更新 `backend-python/crawler/cookies.json`
2. 微博Cookie有效期约24-48小时，需定期更新
3. 检查网络连接和代理配置

### Q7: Pipeline流水线执行失败

**问题**: `POST /api/pipeline/run` 返回错误

**解决**:
1. 确认 `weibo_core_data` 表中有数据（`is_processed=0`）
2. 检查数据库连接：`GET /api/pipeline/stats`
3. 查看Flask日志：`tail -f backend-python/logs/app.log`
4. 检查是否有未完成的异步任务：`GET /api/pipeline/status`

### Q8: Spark任务失败

**问题**: `java.lang.OutOfMemoryError`

**解决**:
1. 增加Spark内存：修改 `.env` 中 `SPARK_DRIVER_MEMORY=4g`
2. 减小数据分区大小
3. 使用本地模式测试：`SPARK_MASTER=local[*]`

### Q9: 三维度排序结果异常

**问题**: composite_score值不合理或排名错误

**解决**:
1. 确认权重参数满足 ω₁+ω₂+ω₃=1（默认0.4+0.4+0.2）
2. 检查算法参数：`GET /api/tri-dimension/formula`
3. 确认 λ_r=1, λ_c=2, λ_l=1（热度权重）
4. 检查配置文件：`backend-python/spark/conf/tri_dimension_config.json`

---

## 附录

### A. 参考文献

```
[1] Devlin J, et al. BERT: Pre-training of deep bidirectional 
    transformers for language understanding. arXiv:1810.04805, 2018.

[2] Cui Y, et al. Pre-training with whole word masking for 
    chinese bert. IEEE/ACM TASLP, 2021.

[3] Sun Z, et al. ChineseBERT: Chinese pretraining enhanced by 
    glyph and pinyin information. ACL, 2021.

[4] Zaharia M, et al. Apache spark: a unified engine for big 
    data processing. Communications of the ACM, 2016.

[5] 徐琳宏等. 情感词汇本体的构造. 情报学报, 2008.
```

### B. 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2026-04-01 | 初始版本：Java后端+前端+基础采集 |
| v2.0.0 | 2026-04-04 | **重大更新**：Python Flask后端、pipeline_service全流程串联、级联情感分析(θ=0.7)、三维度排序模型(半衰期H=12h)、MySQL 12表结构、λ_r=1同步、单元测试13/13 |

### C. Flask蓝图注册清单

| 蓝图 | URL前缀 | 文件 |
|------|---------|------|
| collection_bp | /api/collection | api/collection.py |
| sentiment_bp | /api/sentiment | api/sentiment.py |
| tri_bp | /api/tri-dimension | api/tri_dimension_api.py |
| pipeline_bp | /api/pipeline | api/pipeline_api.py |
| topics_bp | /api/topics | api/topics.py |
| monitor_bp | /api/monitor | api/monitor.py |
| auth_bp | /api/auth | api/auth.py |
| dashboard_bp | /api/dashboard | api/dashboard.py |
| weibo_bp | /api/weibo | api/weibo_api.py |
| evaluation_bp | /api/evaluation | api/evaluation.py |
| preprocess_bp | /api/preprocess | api/preprocess.py |
| behavior_bp | /api/behavior | api/behavior.py |
| propagation_bp | /api/propagation | api/propagation.py |
| crawler_bp | /api/v2/crawl | api/crawler.py |
| unified_bp | /api/v2 | api/unified_api.py (可选) |
| analysis_bp | /api/analysis | routes/analysis_routes.py |

### D. 联系方式

- **作者**: 罗森
- **学号**: 2022407443
- **学校**: 四川民族学院 智能科学与技术学院

---

*文档版本: v2.0.0*
*最后更新: 2026年4月4日*
