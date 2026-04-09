# 项目冗余文件清理报告

> **生成时间**: 2026-01-28 15:20  
> **扫描范围**: weibo-sentiment-analysis 全项目

---

## 🔍 扫描结果汇总

### 1. 重复实现文件

| 文件路径 | 类型 | 建议操作 |
|----------|------|----------|
| `backend/spark/dual_dimension_model.py` | 双维度模型v1 | 保留 |
| `backend/spark/dual_dimension_model_v2.py` | 双维度模型v2 | ⚠️ 合并到v1或删除 |
| `backend/spark/enhanced_dual_dimension.py` | 增强版双维度 | ⚠️ 合并 |
| `backend/spark/bert_sentiment.py` | BERT情感分析 | ⚠️ 与chinese_bert合并 |
| `backend/spark/chinese_bert_sentiment.py` | ChineseBERT | 保留（主版本） |

### 2. 冗余配置目录（Kubernetes不适用于本项目）

| 目录 | 说明 | 建议操作 |
|------|------|----------|
| `deployment/k8s/` | Kubernetes配置 | 🗑️ 删除（本科设计不需要） |
| `deployment/kubernetes/` | Kubernetes配置（重复） | 🗑️ 删除 |
| `deployment/docker/Dockerfile.web-backend` | Spring Boot Dockerfile | 🗑️ 删除（已弃用） |
| `deployment/docker/Dockerfile.model` | 模型服务Dockerfile | 评估是否需要 |

### 3. 遗留Java/Spring Boot代码

| 目录/文件 | 说明 | 建议操作 |
|-----------|------|----------|
| `web-backend/` | Spring Boot后端（已弃用） | 🗑️ 移至archive或删除 |
| `pom.xml` (根目录) | Maven配置 | 🗑️ 删除（Flask项目不需要） |
| `sentiment-analysis/pom.xml` | Java情感分析模块 | 🗑️ 移至archive |
| `data-collector/` | Java数据采集模块 | 🗑️ 移至archive |
| `model-training/` | Java模型训练模块 | 🗑️ 移至archive |
| `common/` | Java公共模块 | 🗑️ 移至archive |
| `spark-streaming/` | Scala流处理模块 | 评估是否需要 |

### 4. 日志文件

| 文件 | 大小 | 建议操作 |
|------|------|----------|
| `backend/logs/collector.log` | - | 🗑️ 清理 |
| `logs/error.log` | - | 🗑️ 清理 |
| `logs/weibo-sentiment-analysis.log` | - | 🗑️ 清理 |
| `web-backend/logs/error.log` | - | 🗑️ 清理 |
| `web-backend/logs/weibo-sentiment-analysis.log` | - | 🗑️ 清理 |

### 5. 空目录

| 目录 | 建议操作 |
|------|----------|
| `scripts/backup/` | 🗑️ 删除 |
| `scripts/deploy/` | 🗑️ 删除 |
| `scripts/monitor/` | 🗑️ 删除 |
| `web-backend/target/` | 🗑️ 删除 |
| `web-backend/logs/` | 🗑️ 删除 |
| `data/` | 保留（数据目录） |

### 6. IDE配置文件

| 文件/目录 | 建议操作 |
|-----------|----------|
| `.idea/` | 已在.gitignore |
| `.vscode/` | 已在.gitignore |
| `.cursor/` | 已在.gitignore |
| `*.iml` 文件 | 🗑️ 删除 |

---

## 📊 清理统计预估

| 类别 | 文件数 | 预估大小 |
|------|--------|----------|
| Java/Spring Boot遗留代码 | ~200+ | ~5MB |
| Kubernetes配置 | ~25 | ~50KB |
| 日志文件 | 5 | 可变 |
| 空目录 | 5 | 0 |
| IDE配置 | ~10 | ~100KB |
| **总计** | **~245** | **~5.2MB** |

---

## ✅ 建议清理操作

### 高优先级（立即执行）

1. **删除Kubernetes配置**（本科设计不需要）
   ```
   deployment/k8s/
   deployment/kubernetes/
   ```

2. **移动Java遗留代码到archive**
   ```
   web-backend/ → archive/web-backend/
   sentiment-analysis/ → archive/sentiment-analysis/
   data-collector/ → archive/data-collector/
   model-training/ → archive/model-training/
   common/ → archive/common/
   ```

3. **删除根目录pom.xml**

4. **清理日志文件**

### 中优先级（合并重复模块）

1. 合并 `dual_dimension_model.py` 和 `dual_dimension_model_v2.py`
2. 合并 `bert_sentiment.py` 和 `chinese_bert_sentiment.py`

### 低优先级

1. 清理空目录
2. 删除IDE配置文件

---

## ⚠️ 注意事项

1. **备份重要数据**：执行删除前确保已备份
2. **检查引用**：删除前确认文件未被其他模块引用
3. **Git提交**：建议在删除前先提交当前状态

---

**是否确认执行清理操作？请回复确认。**
