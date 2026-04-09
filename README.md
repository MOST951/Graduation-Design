# 微博舆情情感分析系统

> **项目类型**: 本科毕业设计  
> **作者**: 罗森 | 学号: 2022407443  
> **技术栈**: Flask + Vue 3 + Spark + ChineseBERT + ECharts  
> **核心创新**: 情感-热度双维度排序模型

---

## 🚀 快速开始

### 环境要求

- **Python** 3.8+
- **Node.js** 16+
- Spark 3.0（可选，用于大规模数据处理）

### 一键启动（推荐）

双击项目根目录下的 `start-system.bat`，在菜单中选择 `[1] Start All Services` 即可同时启动前后端。

### 手动启动

```bash
# 1. 安装后端依赖
cd backend-python
pip install -r requirements.txt

# 2. 安装前端依赖
cd web-frontend
npm install

# 3. 启动后端（终端 1）
cd backend-python
python run_server.py

# 4. 启动前端（终端 2）
cd web-frontend
npm run dev
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3001 |
| 后端 API | http://localhost:5000 |

### 停止服务

双击 `stop-all.bat`，或在 `start-system.bat` 菜单中选择 `[4] Stop All Services`。

---

## 🎯 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  用户界面层 (Vue 3 + Element Plus + ECharts)      │
│  数据采集 │ 预处理 │ 情感分析 │ 双维度排序 │ 监控 │ 可视化 │ 管理 │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP / REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API 网关层 (Flask + CORS)                      │
│  /api/collection │ /api/sentiment │ /api/dual-dimension │ ...   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        业务服务层                                │
│  微博采集 (爬虫+API) │ 混合情感分析 (词典+BERT) │ 双维度排序     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  大数据处理层 (Spark 伪集群)                      │
│  数据清洗 (去噪/分词) │ 特征提取 (TF-IDF) │ 分布式计算          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据存储层                                │
│       MySQL (元数据)  │  HDFS (原始数据)  │  HBase (分析结果)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔥 核心创新点：情感-热度双维度排序模型

本系统提出基于情感强度与热度双维度的综合排序模型，涉及以下论文公式：

| 公式编号 | 公式 | 说明 |
|---------|------|------|
| 4-2 | `S_final = S_dict if \|S_dict\| > θ else S_bert` | 级联策略，θ = 0.7 |
| 4-3 | `N(S) = (\|S\| + 1) / 2` | 情感强度归一化 |
| 4-4 | `H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)` | 热度原始得分，λ_r=1, λ_c=2, λ_l=1 |
| 4-5 | `H_norm = H_raw / max(H_raw)` | 热度归一化 |
| 4-6 | `γ(t) = 2^(-Δt / H)` | 时间衰减因子，半衰期 H=12h |
| 4-7 | `Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)` | 综合评分，ω₁=0.4, ω₂=0.4, ω₃=0.2 |

- **级联情感分析准确率**: 88.6%
- **优势**: 融合情感强度、社交热度与时效性三个维度，能更早发现情感强烈但尚未大规模传播的潜在热点。

---

## � 功能模块（8 个）

| # | 模块 | 路由 | 前端组件 | 关键功能 |
|---|------|------|----------|----------|
| 1 | 数据采集 | `/collection` | `DataCollection.vue` | 爬虫配置、采集速率图表、增量去重、采集日志 |
| 2 | 数据预处理 | `/preprocess` | `DataPreprocessEnhanced.vue` | 清洗规则、繁简/全半角转换、表情处理、停用词统计、分词可视化 |
| 3 | 情感分析 | `/sentiment` | `SentimentAnalysis.vue` | 词典+BERT 级联策略、批量分析进度、分析方式统计饼图 |
| 4 | 双维度排序 | `/dual-dimension` | `DualDimensionAnalysis.vue` | 三维权重联动 (ω₁+ω₂+ω₃=1)、时间衰减预览、散点/热力图 |
| 5 | 实时监控 | `/realtime` | `RealTimeMonitor.vue` | 关键词订阅、舆情预警阈值、预警记录列表、实时数据流 |
| 6 | 流水线管理 | `/pipeline` | `PipelineManager.vue` | 采集→预处理→分析→排序全链路编排、任务调度与监控 |
| 7 | 可视化展示 | `/visualization` | `VisualizationDashboard.vue` | 6 大仪表盘、传播路径力导向图、图表导出 PNG/PDF |
| 8 | 系统管理 | `/admin` | `SystemAdmin.vue` | 用户管理、系统日志(按级别筛选)、Spark 参数配置 |

---

## 📁 项目结构

```
weibo-sentiment-analysis/
├── backend-python/                # Python 后端 (Flask)
│   ├── api/                       #   API 接口层
│   ├── services/                  #   业务服务层
│   ├── spark/                     #   Spark 处理模块
│   ├── crawler/                   #   微博爬虫
│   ├── models/                    #   数据模型
│   ├── requirements.txt           #   Python 依赖
│   └── run_server.py              #   应用入口
├── web-frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── views/                 #   页面组件 (8 个功能模块)
│   │   ├── components/            #   通用 UI 组件
│   │   ├── store/                 #   Pinia 状态管理
│   │   ├── router/                #   路由配置
│   │   └── api/                   #   API 调用封装
│   ├── package.json
│   └── vite.config.ts             #   Vite 配置 (port: 3001)
├── common/                        # 公共工具类、实体
├── deployment/                    # Docker / Docker Compose 部署
│   └── sql/                       #   数据库初始化脚本
├── scripts/                       # 工具脚本
├── docs/                          # 项目文档 & 答辩材料
├── tests/                         # 测试用例
├── start-system.bat               # 一键启动器 (菜单式)
└── stop-all.bat                   # 一键停止
```

---

## ⚡ Spark 性能优化

系统集成 Spark 性能优化模块 (`backend-python/spark/spark_optimizer.py`)，针对伪集群环境调优：

| 优化项 | 技术手段 | 提升幅度 |
|--------|----------|----------|
| 内存管理 | 动态 `memory.fraction`、堆外内存 | — |
| 序列化 | Kryo 序列化替代 Java 默认序列化 | ~10x |
| 分区策略 | AQE 自适应执行、自动合并小分区 | — |
| 广播与缓存 | 小表广播 Join、智能缓存中间结果 | — |

| 测试指标 | 优化前 | 优化后 | 提升 |
|----------|--------|--------|------|
| 数据清洗 | 5.2s | 1.8s | **65%** |
| 特征提取 | 8.5s | 3.2s | **62%** |
| 情感分析 | 12.3s | 4.5s | **63%** |
| 内存占用 | 2.1GB | 1.4GB | **33%** |

---

## �️ 启动脚本说明

`start-system.bat` 提供交互式菜单：

```
[1]  Start All Services   (Backend + Frontend)
[2]  Start Backend Only   (Flask :5000)
[3]  Start Frontend Only  (Vite  :3001)
[4]  Stop All Services
[5]  Service Status
[6]  Install / Update Deps
[0]  Exit
```

功能特性：
- **环境检查** — 自动检测 Python / Node.js 版本及项目文件完整性
- **端口冲突检测** — 启动前发现占用端口，可选择自动释放
- **后端就绪轮询** — 等待 Flask 端口监听后再启动前端
- **依赖自动安装** — 首次运行自动 `npm install`
- **`.env` 自动生成** — 从 `.env.example` 复制

---

## 📖 相关文档

- [项目概览](PROJECT_OVERVIEW.md)
- [系统架构](docs/SYSTEM_ARCHITECTURE.md)
- [论文数据](docs/THESIS_DATA.md)
- [项目文档](docs/PROJECT_DOCUMENTATION.md)
- [答辩演示指南](docs/DEFENSE_GUIDE.md)
- [答辩 PPT 大纲](docs/答辩PPT大纲.md)
- [创新点说明与答辩讲稿](docs/创新点说明与答辩讲稿.md)

---

## 📝 License

MIT License

