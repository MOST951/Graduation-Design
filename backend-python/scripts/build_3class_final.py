"""
三分类微博情感数据集构建脚本（最终版）
======================================
合并 weibo_senti_100k (HuggingFace) + nCoV_100k_train 两个真实数据集
构建均衡的三分类情感数据集

步骤：
  1. 探索 weibo_senti_100k 数据
  2. 探索 nCoV 数据
  3. 合并两个数据集
  4. 平衡采样（每类33333条）
  5. 保存
  6. 验证
"""

import pandas as pd
import os
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
NCOV_PATH = os.path.join(DATA_DIR, 'nCoV_100k_train.labled.csv')
OUTPUT_PATH = os.path.join(DATA_DIR, 'weibo_senti_100k.csv')
BACKUP_3CLASS = os.path.join(DATA_DIR, 'weibo_senti_100k_3class.csv')

TARGET_PER_CLASS = 33333

# ==================== 第一步：探索 weibo_senti_100k ====================
print("=" * 70)
print("第一步：探索 weibo_senti_100k (HuggingFace)")
print("=" * 70)

print("\n正在从 HuggingFace 读取 weibo_senti_100k ...")
df_weibo = pd.read_csv("hf://datasets/dirtycomputer/weibo_senti_100k/weibo_senti_100k.csv")

print(f"\n1. df.shape: {df_weibo.shape}")
print(f"\n2. df.columns: {df_weibo.columns.tolist()}")
print(f"\n3. df.head(5):")
print(df_weibo.head(5).to_string())
print(f"\n4. df['label'].value_counts():")
print(df_weibo['label'].value_counts().to_string())
print(f"\n5. df.info():")
df_weibo.info()
print(f"\n6. df.isnull().sum():")
print(df_weibo.isnull().sum().to_string())

# ==================== 第二步：探索 nCoV 数据 ====================
print("\n" + "=" * 70)
print("第二步：探索 nCoV_100k_train.labled.csv")
print("=" * 70)

df_ncov = pd.read_csv(NCOV_PATH, encoding='utf-8')

print(f"\n1. 表头: {df_ncov.columns.tolist()}")
print(f"\n2. 总行数: {len(df_ncov)}")
print(f"\n3. 情感倾向分布:")
print(df_ncov['情感倾向'].value_counts().to_string())
print(f"\n4. 前3行:")
print(df_ncov.head(3)[['微博中文内容', '情感倾向']].to_string())

# ==================== 第三步：合并两个数据集 ====================
print("\n" + "=" * 70)
print("第三步：合并两个数据集")
print("=" * 70)

# 3.1 处理 weibo_senti_100k: label=0→0(负面), label=1→1(正面)
df_w = df_weibo[['label', 'review']].copy()
df_w['label'] = df_w['label'].astype(int)
print(f"\nweibo_senti_100k 取出: {len(df_w)} 条")

# 3.2 处理 nCoV: 情感倾向=-1→0(负面), 0→2(中性), 1→1(正面)
ncov_label_map = {-1: 0, 0: 2, 1: 1}
df_n = df_ncov[['微博中文内容', '情感倾向']].copy()
df_n.columns = ['review', 'label']
# 将标签列转为数值，无法转换的设为 NaN 后丢弃
df_n['label'] = pd.to_numeric(df_n['label'], errors='coerce')
df_n = df_n.dropna(subset=['label'])
# 仅保留合法标签 (-1, 0, 1)
df_n = df_n[df_n['label'].isin([-1, 0, 1])].copy()
df_n['label'] = df_n['label'].map(ncov_label_map).astype(int)
print(f"nCoV 取出: {len(df_n)} 条")

# 3.3 合并
df_merged = pd.concat([df_w[['label', 'review']], df_n[['label', 'review']]], ignore_index=True)
print(f"合并后总数: {len(df_merged)} 条")

# 3.4 删除空值和短文本
df_merged = df_merged.dropna(subset=['review'])
df_merged['review'] = df_merged['review'].astype(str).str.strip()
df_merged = df_merged[df_merged['review'].str.len() >= 4]
print(f"删除空值/短文本后: {len(df_merged)} 条")

# 3.5 去重
before_dedup = len(df_merged)
df_merged = df_merged.drop_duplicates(subset=['review'])
print(f"去重后: {len(df_merged)} 条 (移除 {before_dedup - len(df_merged)} 条重复)")

# 3.6 各类别数量
print(f"\n合并后各类别数量:")
for label in sorted(df_merged['label'].unique()):
    count = (df_merged['label'] == label).sum()
    name = {0: '负面', 1: '正面', 2: '中性'}[label]
    print(f"  {name}(label={label}): {count} 条")
print(f"  总计: {len(df_merged)} 条")

# ==================== 第四步：平衡采样 ====================
print("\n" + "=" * 70)
print(f"第四步：平衡采样（每类 {TARGET_PER_CLASS} 条）")
print("=" * 70)

balanced_parts = []
for label in [0, 1, 2]:
    subset = df_merged[df_merged['label'] == label]
    available = len(subset)
    take = min(available, TARGET_PER_CLASS)
    if available >= TARGET_PER_CLASS:
        sampled = subset.sample(n=TARGET_PER_CLASS, random_state=42)
        status = "✓"
    else:
        sampled = subset
        status = f"不足 (仅 {available})"
    balanced_parts.append(sampled)
    name = {0: '负面', 1: '正面', 2: '中性'}[label]
    print(f"  {name}(label={label}): 可用 {available}, 采样 {take} {status}")

df_final = pd.concat(balanced_parts, ignore_index=True)
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)
print(f"\n采样后总数: {len(df_final)} 条")

# ==================== 第五步：保存 ====================
print("\n" + "=" * 70)
print("第五步：保存")
print("=" * 70)

# 备份原文件
if os.path.exists(OUTPUT_PATH):
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    backup = os.path.join(DATA_DIR, f'weibo_senti_100k_backup_{ts}.csv')
    shutil.copy2(OUTPUT_PATH, backup)
    print(f"  原文件已备份: {os.path.basename(backup)}")

# 确保 label 为整数
df_final['label'] = df_final['label'].astype(int)

# 保存主文件
df_final.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
print(f"  主文件已保存: {OUTPUT_PATH}")

# 保存备份副本
df_final.to_csv(BACKUP_3CLASS, index=False, encoding='utf-8')
print(f"  备份副本已保存: {BACKUP_3CLASS}")

# ==================== 第六步：验证 ====================
print("\n" + "=" * 70)
print("第六步：验证")
print("=" * 70)

# 6.1 各类别数量和占比
total = len(df_final)
print(f"\n1. 各类别数量和占比:")
for label in [0, 1, 2]:
    count = (df_final['label'] == label).sum()
    pct = count / total * 100
    name = {0: '负面', 1: '正面', 2: '中性'}[label]
    print(f"   {name}(label={label}): {count:>6} 条 ({pct:.1f}%)")

# 6.2 总样本数
print(f"\n2. 总样本数: {total}")

# 6.3 各类别5条示例
print(f"\n3. 各类别示例:")
for label in [0, 1, 2]:
    name = {0: '负面', 1: '正面', 2: '中性'}[label]
    print(f"\n   --- {name}(label={label}) ---")
    subset = df_final[df_final['label'] == label]
    if len(subset) == 0:
        print(f"   (无数据)")
        continue
    samples = subset.sample(min(5, len(subset)), random_state=42)
    for _, row in samples.iterrows():
        text = str(row['review'])[:80]
        if len(str(row['review'])) > 80:
            text += '...'
        print(f"   [{label}] {text}")

# 6.4 文件大小
for fpath in [OUTPUT_PATH, BACKUP_3CLASS]:
    size_kb = os.path.getsize(fpath) / 1024
    fname = os.path.basename(fpath)
    print(f"\n4. 文件大小: {fname} = {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")

# 6.5 重新读取验证
print(f"\n5. 重新读取验证:")
df_verify = pd.read_csv(OUTPUT_PATH, encoding='utf-8')
print(f"   行数: {len(df_verify)}")
print(f"   列名: {df_verify.columns.tolist()}")
print(f"   label dtype: {df_verify['label'].dtype}")
print(f"   label 值域: {sorted(df_verify['label'].unique().tolist())}")
print(f"   空值检查: {df_verify.isnull().sum().to_dict()}")

print(f"\n{'=' * 70}")
print("完成！标签说明: 0=负面, 1=正面, 2=中性")
print("=" * 70)
