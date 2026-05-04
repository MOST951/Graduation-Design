# 数据目录

## 说明

本项目用到的训练 / 测试数据集体积较大或包含爬取产物，**未上传到 GitHub**。
按下述方式获取或重新生成。

## 训练数据集

| 文件 | 大小 | 说明 | 获取方式 |
|------|------|------|----------|
| `weibo_senti_100k.csv` | ~20 MB | 微博 10万条情感数据 (二分类) | [weibo_senti_100k 数据集](https://github.com/SophonPlus/ChineseNlpCorpus/tree/master/datasets/weibo_senti_100k) |
| `weibo_senti_100k_3class.csv` | ~20 MB | 转换为三分类版本 (negative/positive/neutral) | 由二分类版本通过 `scripts/build_3class_final.py` 生成 |
| `nCoV_100k_train.labled.csv` | ~44 MB | 疫情微博数据 | [nCoV_100k 数据集](https://github.com/SophonPlus/ChineseNlpCorpus) |
| `test_set_200.csv` | ~2 MB | 离线评估测试集 (200 条) | 项目自建 |

## 运行时缓存 (会自动生成, 无需下载)

以下文件会在运行系统时自动产生，已加入 `.gitignore`：

```
data/
├── crawl_result_*.json      # 爬虫采集结果
├── processed_*.json         # 预处理输出
├── hotsearch_cache.json     # 热搜缓存
├── metadata_*.json          # 任务元数据
├── spark_jobs.json          # Spark 作业记录
├── weibo_raw/               # 原始爬取数据
├── output/                  # 分析输出
└── processed/               # Spark 处理输出
```

## 快速准备

```bash
# 1. 创建数据目录结构
mkdir -p data/weibo_raw data/output data/processed data/preprocess

# 2. 下载并放入 weibo_senti_100k.csv
# 从上面给出的链接下载, 放到 data/ 目录下

# 3. (可选) 生成三分类版本
python scripts/build_3class_final.py
```
