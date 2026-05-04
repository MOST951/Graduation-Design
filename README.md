# 微博舆情情感分析系统

> **项目类型**: 本科毕业设计  
> **作者**: 罗森 | 学号: 2022407443  
> **技术栈**: Flask + Spring Boot + Vue 3 + Spark + ChineseBERT + ECharts  
> **核心创新**: 情感-热度三维度排序模型  
> **部署环境**: Ubuntu 20.04 + Docker Compose v2 + 1Panel

---

## 🚀 一键部署 (Ubuntu Docker)

> 详细步骤请参阅 [Ubuntu 部署指南](deployment/UBUNTU_DEPLOY_GUIDE.md)

### 环境要求

- **Ubuntu** 20.04 LTS (4GB RAM / 2 核 CPU / 20GB 磁盘)
- **Docker** 20.10+
- **Docker Compose** v2.x (`docker compose` 子命令)

### 快速部署

```bash
# 1. 上传项目到 Ubuntu VM
scp -r ./weibo-sentiment-analysis root@<VM_IP>:/root/weibo-analysis

# 2. 修复脚本权限和换行符
cd /root/weibo-analysis
chmod +x docker-cluster.sh deployment/scripts/*.sh
apt-get install -y dos2unix && find . -name "*.sh" -exec dos2unix {} \;

# 3. 配置环境变量
cd deployment && cp .env.docker.example .env.docker
nano .env.docker   # 开发测试默认密码为 123456；生产必须改密
cd ..

# 4. 一键启动
./docker-cluster.sh

# 等价 Compose 全量启动命令（显式 --env-file + 全 profile）
docker compose -f deployment/docker-compose.yml \
  --env-file deployment/.env.docker \
  --profile with-frontend \
  --profile with-java-backend \
  --profile with-spark \
  --profile with-bigdata up -d

# 5. 验证
./docker-cluster.sh health
bash deployment/scripts/health-check.sh
```

> 安全提醒：`123456` 仅适用于开发测试环境，生产环境请务必修改 `DB_PASSWORD`、`DB_ROOT_PASSWORD`、`REDIS_PASSWORD`、`SECRET_KEY`、`JWT_SECRET`。

### 访问地址

假设虚拟机 IP 为 `192.168.1.100`：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://192.168.1.100:3001 | Vue 3 + Element Plus |
| Flask API | http://192.168.1.100:5000/api/health | 核心业务 API |
| Java API | http://192.168.1.100:8081/api/actuator/health | 用户认证/Spark 调度 |
| Spark UI | http://192.168.1.100:8080 | Spark Web 管理界面 |

### 日常管理

```bash
./docker-cluster.sh stop      # 停止（保留数据）
./docker-cluster.sh restart   # 重启
./docker-cluster.sh status    # 查看状态
./docker-cluster.sh logs      # 实时日志
./docker-cluster.sh health    # 健康自检
./docker-cluster.sh down      # 销毁容器（数据卷保留）
```

---

## 🎯 系统架构（双后端 + Docker）

本系统采用**双后端架构**，通过 Docker Compose 编排：

| 后端 | 技术 | 端口 | 职责 |
|------|------|------|------|
| **backend-python** | Flask + Gunicorn | :5000 | 核心业务：爬虫、NLP 情感分析、三维度排序、数据可视化 |
| **web-backend** | Spring Boot | :8081 | 企业级功能：JWT 认证、Spark 调度、WebSocket 通信 |

```
┌─────────────────────────────────────────────────────┐
│                  Ubuntu 20.04 VM                     │
│                                                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │ Frontend  │  │ Flask API │  │ Java Backend  │   │
│  │ (Nginx)   │→ │ (Gunicorn)│  │ (Spring Boot) │   │
│  │ :3001     │  │ :5000     │  │ :8081         │   │
│  └───────────┘  └─────┬─────┘  └───────┬───────┘   │
│                       │                 │            │
│         ┌─────────────┼─────────────────┤            │
│         ▼             ▼                 ▼            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │  Redis    │  │  MySQL    │  │ Spark Cluster │   │
│  │  :6379    │  │  :3306    │  │ Master :8080  │   │
│  └───────────┘  └───────────┘  │ Worker :7077  │   │
│                                 └───────────────┘   │
│  Network: weibo-net (bridge)                        │
└─────────────────────────────────────────────────────┘
```

---

## 🔥 核心创新点：情感-热度三维度排序模型

| 公式编号 | 公式 | 说明 |
|---------|------|------|
| 4-2 | `S_final = S_dict if \|S_dict\| > θ else S_bert` | 级联策略，θ = 0.7 |
| 4-3 | `N(S) = (\|S\| + 1) / 2` | 情感强度归一化 |
| 4-4 | `H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)` | 热度原始得分 |
| 4-5 | `H_norm = H_raw / max(H_raw)` | 热度归一化 |
| 4-6 | `γ(t) = 2^(-Δt / H)` | 时间衰减因子，半衰期 H=12h |
| 4-7 | `Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)` | 综合评分，ω₁=0.4, ω₂=0.4, ω₃=0.2 |

- **级联情感分析准确率**: 86.2%

---

## 📦 功能模块（8 个）

| # | 模块 | 路由 | 前端组件 | 关键功能 |
|---|------|------|----------|----------|
| 1 | 数据采集 | `/collection` | `DataCollection.vue` | 爬虫配置、采集速率图表、增量去重 |
| 2 | 数据预处理 | `/preprocess` | `DataPreprocessEnhanced.vue` | 清洗规则、繁简转换、分词可视化 |
| 3 | 情感分析 | `/sentiment` | `SentimentAnalysis.vue` | 词典+BERT 级联策略、批量分析 |
| 4 | 三维度排序 | `/tri-dimension` | `TriDimensionAnalysis.vue` | 三维权重联动、散点/热力图 |
| 5 | 实时监控 | `/realtime` | `RealTimeMonitor.vue` | 关键词订阅、舆情预警 |
| 6 | 流水线管理 | `/pipeline` | `PipelineManager.vue` | 全链路编排、任务调度 |
| 7 | 可视化展示 | `/visualization` | `VisualizationDashboard.vue` | 6 大仪表盘、图表导出 |
| 8 | 系统管理 | `/admin` | `SystemAdmin.vue` | 用户管理、系统日志、Spark 配置 |

---

## 📁 项目结构

```
weibo-sentiment-analysis/
├── backend-python/                # Python 后端 (Flask :5000)
│   ├── api/                       #   API 接口层 (15+ 蓝图)
│   ├── services/                  #   业务服务层
│   ├── spark/                     #   Spark 处理模块 + 三维度模型
│   ├── crawler/                   #   微博爬虫
│   ├── models/                    #   数据模型
│   ├── resources/                 #   情感词典资源
│   ├── config.py                  #   统一配置管理
│   ├── requirements.txt           #   Python 依赖
│   └── app.py                     #   Flask 应用入口
├── web-backend/                   # Java 后端 (Spring Boot :8081)
│   ├── src/main/java/             #   Controller/Service/Config
│   ├── src/main/resources/        #   application.yml
│   └── pom.xml                    #   Maven 依赖
├── web-frontend/                  # Vue 3 前端 (:3001)
│   ├── src/                       #   Vue 源码
│   ├── package.json               #   npm 依赖
│   └── vite.config.ts             #   Vite 配置
├── common/                        # Java 公共模块
├── data-collector/                # Java 数据采集模块
├── sentiment-analysis/            # Java 情感分析模块
├── model-training/                # 模型训练模块
├── deployment/                    # Docker 部署配置
│   ├── docker-compose.yml         #   Compose 编排文件
│   ├── .env.docker.example        #   环境变量模板
│   ├── UBUNTU_DEPLOY_GUIDE.md     #   Ubuntu 部署指南
│   ├── docker/                    #   Dockerfiles + Nginx 配置
│   ├── config/                    #   application-prod.yml + spark-prod.conf
│   ├── sql/                       #   数据库初始化脚本
│   └── scripts/                   #   运维脚本 (健康检查/备份/监控)
├── docs/                          # 项目文档
│   ├── SYSTEM_ARCHITECTURE.md     #   系统架构文档
│   └── PROJECT_DOCUMENTATION.md   #   项目完整文档
├── docker-cluster.sh              # Docker 集群启停脚本 (Ubuntu)
├── .env.example                   #   环境变量模板
├── pom.xml                        #   Maven 父 POM
└── README.md                      #   本文件
```

---

## ⚡ 技术栈详情

### 前端技术栈
- **Vue 3.2.37** - 渐进式 JavaScript 框架
- **TypeScript 4.6.4** - 类型安全的 JavaScript
- **Vite 3.1.0** - 现代化前端构建工具
- **Element Plus 2.2.17** - Vue 3 UI 组件库
- **ECharts 5.3.3** - 数据可视化图表库
- **Pinia 2.0.22** - Vue 状态管理
- **Axios 0.27.2** - HTTP 客户端
- **SCSS** - CSS 预处理器

### 后端技术栈
- **Flask 2.3.3** - Python Web 框架
- **Spring Boot 3.x** - Java 企业级框架
- **Apache Spark 3.5.0** - 大数据处理引擎
- **MySQL 8.0** - 关系型数据库
- **Redis 7.0** - 内存数据库/缓存
- **HBase** - 列式存储数据库（大数据）
- **Gunicorn** - Python WSGI 服务器
- **Nginx** - 反向代理/静态文件服务

### AI/NLP 技术栈
- **Jieba 0.42.1** - 中文分词
- **ChineseBERT** - 中文预训练模型
- **情感词典** - 知网 Hownet + 清华大学
- **级联分析策略** - 词典 + BERT 融合

---

## 🎨 前端特色功能

### 1. 优雅的错误处理
- **无红弹窗设计**: 全局拦截 404/500/网络错误，静默处理
- **柔和提示**: 所有错误提示改为 `warning` 类型，避免视觉冲击
- **平滑动画**: 消息/通知采用滑入动画，提升用户体验

### 2. 响应式设计
- **移动端适配**: 完整响应式布局，支持手机/平板访问
- **暗色主题**: 支持明暗主题切换（开发中）
- **无障碍支持**: 符合 WCAG 2.1 AA 标准

### 3. 数据可视化
- **6 大仪表盘**: 实时监控、情感分布、热点话题、传播网络
- **交互式图表**: ECharts 实现的动态图表，支持钻取和导出
- **词云图**: 基于 echarts-wordcloud 的动态词云

---

## ⚡ Spark 性能优化

| 优化项 | 技术手段 | 提升幅度 |
|--------|----------|----------|
| 内存管理 | 动态 `memory.fraction`、堆外内存 | — |
| 序列化 | Kryo 序列化替代 Java 默认序列化 | ~10x |
| 分区策略 | AQE 自适应执行、自动合并小分区 | — |

| 测试指标 | 优化前 | 优化后 | 提升 |
|----------|--------|--------|------|
| 数据清洗 | 5.2s | 1.8s | **65%** |
| 特征提取 | 8.5s | 3.2s | **62%** |
| 情感分析 | 12.3s | 4.5s | **63%** |
| 内存占用 | 2.1GB | 1.4GB | **33%** |

---

## 🔧 开发环境搭建

### 前端开发
```bash
cd web-frontend
npm install
npm run dev    # 开发服务器 :3000
npm run build  # 生产构建
```

### Python 后端开发
```bash
cd backend-python
pip install -r requirements.txt
python app.py  # 开发服务器 :5000
```

### Java 后端开发
```bash
cd web-backend
mvn clean install
mvn spring-boot:run  # 开发服务器 :8081
```

---

## 📖 相关文档

- [Ubuntu 部署指南](deployment/UBUNTU_DEPLOY_GUIDE.md)
- [系统架构](docs/SYSTEM_ARCHITECTURE.md)
- [项目文档](docs/PROJECT_DOCUMENTATION.md)
- [技术架构说明](docs/技术架构说明.md)

---

## 🐛 爬虫合规说明

本系统的微博数据采集模块仅用于**学术研究和毕业设计演示**，遵循以下原则：

1. **尊重 robots.txt** — 采集前检查并遵守目标网站的爬虫协议
2. **控制访问频率** — 默认间隔 1 秒，避免对目标服务器造成压力
3. **数据脱敏** — 不采集、不存储用户密码、手机号等个人敏感信息
4. **仅限学术用途** — 采集数据仅用于情感分析研究，不会用于商业目的

---

## 📝 License

MIT License
