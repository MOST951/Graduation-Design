#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三维度排序模型权重网格搜索实验
===================================

目标：基于专家规则构建的"伪金标准"排序，搜索三维度权重 (α, β, γ) 的最优组合。

实验设计：
1. 数据来源：从 MySQL `weibo_core_data` JOIN `sentiment_analysis_results`
   抽取 N 条已分析微博（默认 N=1000）。若无 MySQL，回退到合成数据。
2. 伪金标准 (Pseudo Gold)：
   每条微博的相关性分数 R ∈ {0, 1, 2, 3}：
     +1 if |sentiment_score| >= 0.7  (情感强烈)
     +1 if heat_rank within top 25%  (热度高)
     +1 if age_hours <= 24            (24小时内)
   规则呈非线性，避免与任何单一权重组合直接同构。
3. 网格搜索：(α, β, γ), α+β+γ=1, 步长 0.1, 共 36 组。
4. 评估指标：NDCG@10, NDCG@20, MAP@20。
5. 维度消融：单维度 / 双维度 / 三维度对比。

输出: scripts/grid_search_tri_dim_results.json + 终端 Markdown 表格

用法:
  cd backend-python
  python scripts/grid_search_tri_dim.py [--n 1000] [--use-mysql] [--seed 42]
"""

import os
import sys
import time
import json
import math
import argparse
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('GridSearchTriDim')

OUTPUT_PATH = SCRIPT_DIR / 'grid_search_tri_dim_results.json'

# ==================== 1. 数据加载 ====================

def load_from_mysql(n: int) -> List[Dict]:
    """从 MySQL 加载已分析微博"""
    try:
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            port=int(os.environ.get('MYSQL_PORT', 3306)),
            user=os.environ.get('MYSQL_USER', 'root'),
            password=os.environ.get('MYSQL_PASSWORD', ''),
            database=os.environ.get('MYSQL_DATABASE', 'weibo_sentiment'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        sql = f"""
            SELECT w.weibo_id, w.created_at,
                   w.reposts_count, w.comments_count, w.attitudes_count,
                   COALESCE(s.hybrid_score, s.bert_score, s.dict_score) AS sentiment_score
            FROM weibo_core_data w
            INNER JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
            WHERE COALESCE(s.hybrid_score, s.bert_score, s.dict_score) IS NOT NULL
            ORDER BY w.created_at DESC
            LIMIT {n}
        """
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        conn.close()
        logger.info(f'从 MySQL 加载 {len(rows)} 条')
        return list(rows)
    except Exception as e:
        logger.warning(f'MySQL 加载失败: {e}')
        return []


def generate_synthetic(n: int, seed: int = 42) -> List[Dict]:
    """合成数据（带真实分布特征）"""
    rng = np.random.default_rng(seed)
    now = datetime.now()
    items = []
    for i in range(n):
        # 情感得分: 双峰 + 中性集中分布
        if rng.random() < 0.3:
            s = rng.uniform(-1, -0.5)
        elif rng.random() < 0.5:
            s = rng.uniform(0.5, 1)
        else:
            s = rng.uniform(-0.3, 0.3)
        # 热度: 长尾分布 (Pareto)
        reposts = int(rng.pareto(1.5) * 50)
        comments = int(rng.pareto(1.5) * 30)
        likes = int(rng.pareto(1.3) * 200)
        # 时间: 0~72 小时内
        hours_ago = rng.uniform(0, 72)
        created = now - timedelta(hours=hours_ago)
        items.append({
            'weibo_id': f'syn_{i}',
            'sentiment_score': float(s),
            'reposts_count': reposts,
            'comments_count': comments,
            'attitudes_count': likes,
            'created_at': created,
        })
    logger.info(f'生成合成数据 {n} 条')
    return items


# ==================== 2. 特征计算 ====================

def compute_features(items: List[Dict], reference_time: datetime,
                     half_life_h: float = 12.0) -> List[Dict]:
    """为每条微博计算 (sentiment_intensity, heat_norm, timeliness) 三维特征"""
    # 1. 原始热度 (log 平滑)
    raw_heats = []
    for it in items:
        r = float(it.get('reposts_count', 0) or 0)
        c = float(it.get('comments_count', 0) or 0)
        l = float(it.get('attitudes_count', 0) or 0)
        raw_heat = math.log10(1 + r * 1.0 + c * 2.0 + l * 1.0)
        raw_heats.append(raw_heat)
    max_heat = max(raw_heats) if raw_heats else 1.0
    if max_heat <= 0:
        max_heat = 1.0

    enriched = []
    for it, raw_heat in zip(items, raw_heats):
        s = float(it.get('sentiment_score', 0.0) or 0.0)
        # 情感强度: |s|, 已在 [0, 1]
        intensity = abs(s)
        # 热度归一化
        heat_norm = raw_heat / max_heat
        # 时效性: 半衰期衰减
        created = it.get('created_at')
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created is None:
            age_h = 0.0
        else:
            age_h = max(0.0, (reference_time - created).total_seconds() / 3600)
        timeliness = 0.5 ** (age_h / half_life_h)
        enriched.append({
            **it,
            'intensity': intensity,
            'heat_norm': heat_norm,
            'timeliness': timeliness,
            'age_hours': age_h,
            'raw_heat': raw_heat,
        })
    return enriched


# ==================== 3. 伪金标准 ====================

def build_pseudo_gold(items: List[Dict]) -> List[int]:
    """
    专家规则伪金标准: relevance ∈ {0, 1, 2, 3}
      +1 if |sentiment| >= 0.7  (强情感)
      +1 if heat_norm in top 25% (高热度)
      +1 if age_hours <= 24      (24h 内)
    """
    heats = sorted([it['heat_norm'] for it in items], reverse=True)
    if heats:
        top25_threshold = heats[int(len(heats) * 0.25)]
    else:
        top25_threshold = 1.0

    gold = []
    for it in items:
        rel = 0
        if it['intensity'] >= 0.7:
            rel += 1
        if it['heat_norm'] >= top25_threshold:
            rel += 1
        if it['age_hours'] <= 24:
            rel += 1
        gold.append(rel)
    return gold


# ==================== 4. 评估指标 ====================

def dcg(rels: List[int], k: int) -> float:
    rels = rels[:k]
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def ndcg_at_k(predicted_order: List[int], gold_relevance: List[int], k: int) -> float:
    """predicted_order: 模型排序后的下标列表; gold_relevance: 各下标对应的金标准 relevance"""
    pred_rels = [gold_relevance[i] for i in predicted_order[:k]]
    ideal_rels = sorted(gold_relevance, reverse=True)[:k]
    idcg = dcg(ideal_rels, k)
    return dcg(pred_rels, k) / idcg if idcg > 0 else 0


def map_at_k(predicted_order: List[int], gold_relevance: List[int], k: int) -> float:
    """MAP@K: 视 relevance>=2 为正例"""
    relevant = set(i for i, r in enumerate(gold_relevance) if r >= 2)
    if not relevant:
        return 0
    hits = 0
    sum_prec = 0
    for rank, idx in enumerate(predicted_order[:k], start=1):
        if idx in relevant:
            hits += 1
            sum_prec += hits / rank
    return sum_prec / min(len(relevant), k)


# ==================== 5. 排序 ====================

def rank_by_weights(items: List[Dict], alpha: float, beta: float, gamma: float) -> List[int]:
    """给定权重，返回降序排序后的下标列表"""
    scores = []
    for i, it in enumerate(items):
        score = alpha * it['intensity'] + beta * it['heat_norm'] + gamma * it['timeliness']
        scores.append((score, i))
    scores.sort(key=lambda x: -x[0])
    return [i for _, i in scores]


# ==================== 6. 网格搜索 ====================

def grid_search(items: List[Dict], gold: List[int],
                step: float = 0.1) -> List[Dict]:
    results = []
    n_steps = int(round(1.0 / step)) + 1
    for a_i in range(n_steps):
        alpha = round(a_i * step, 2)
        for b_i in range(n_steps - a_i):
            beta = round(b_i * step, 2)
            gamma = round(1.0 - alpha - beta, 2)
            if gamma < -1e-6:
                continue
            order = rank_by_weights(items, alpha, beta, gamma)
            row = {
                'alpha': alpha,
                'beta': beta,
                'gamma': gamma,
                'ndcg10': ndcg_at_k(order, gold, 10),
                'ndcg20': ndcg_at_k(order, gold, 20),
                'map20': map_at_k(order, gold, 20),
            }
            results.append(row)
    return results


def ablation_study(items: List[Dict], gold: List[int]) -> List[Dict]:
    """维度消融：单维度 / 双维度 / 三维度"""
    configs = [
        ('仅情感 (单维)', 1.0, 0.0, 0.0),
        ('仅热度 (单维 — 传统方法)', 0.0, 1.0, 0.0),
        ('仅时效 (单维)', 0.0, 0.0, 1.0),
        ('情感+热度 (双维)', 0.5, 0.5, 0.0),
        ('情感+时效 (双维)', 0.5, 0.0, 0.5),
        ('热度+时效 (双维)', 0.0, 0.5, 0.5),
        ('等权三维 (1/3,1/3,1/3)', 1/3, 1/3, 1/3),
        ('本文三维 (0.4,0.4,0.2)', 0.4, 0.4, 0.2),
    ]
    rows = []
    for name, a, b, g in configs:
        order = rank_by_weights(items, a, b, g)
        rows.append({
            'config': name,
            'alpha': round(a, 4), 'beta': round(b, 4), 'gamma': round(g, 4),
            'ndcg10': ndcg_at_k(order, gold, 10),
            'ndcg20': ndcg_at_k(order, gold, 20),
            'map20': map_at_k(order, gold, 20),
        })
    return rows


# ==================== 7. 主流程 ====================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=1000)
    parser.add_argument('--use-mysql', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--half-life', type=float, default=12.0)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # 加载数据
    items = []
    if args.use_mysql:
        items = load_from_mysql(args.n)
    if not items:
        items = generate_synthetic(args.n, args.seed)
        data_source = 'synthetic'
    else:
        data_source = 'mysql'

    # 计算特征
    ref_time = datetime.now()
    items = compute_features(items, ref_time, half_life_h=args.half_life)

    # 伪金标准
    gold = build_pseudo_gold(items)
    gold_dist = {r: gold.count(r) for r in [0, 1, 2, 3]}
    logger.info(f'伪金标准分布: {gold_dist}')

    # 网格搜索
    logger.info('Step 1/2: 网格搜索 (36 组权重) ...')
    t0 = time.perf_counter()
    grid = grid_search(items, gold, step=0.1)
    grid_sorted = sorted(grid, key=lambda r: -r['ndcg10'])
    logger.info(f'  完成，耗时 {time.perf_counter()-t0:.2f}s。最优 NDCG@10={grid_sorted[0]["ndcg10"]:.4f} '
                f'@ (α,β,γ)=({grid_sorted[0]["alpha"]},{grid_sorted[0]["beta"]},{grid_sorted[0]["gamma"]})')

    # 维度消融
    logger.info('Step 2/2: 维度消融 ...')
    ablation = ablation_study(items, gold)

    # 保存
    result = {
        'data_source': data_source,
        'n_items': len(items),
        'half_life_h': args.half_life,
        'pseudo_gold_distribution': gold_dist,
        'grid_search_top10': grid_sorted[:10],
        'grid_search_full': grid_sorted,
        'ablation': ablation,
        'best_weights': {
            'alpha': grid_sorted[0]['alpha'],
            'beta': grid_sorted[0]['beta'],
            'gamma': grid_sorted[0]['gamma'],
            'ndcg10': grid_sorted[0]['ndcg10'],
        },
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f'结果已保存: {OUTPUT_PATH}')

    # ==================== Markdown 表格 ====================
    print()
    print('=' * 88)
    print(f'  实验数据来源: {data_source} | 样本数: {len(items)} | '
          f'伪金标准分布: {gold_dist}')
    print('=' * 88)

    # 表 A: 网格搜索代表性结果
    print()
    print('表 A — 三维度权重网格搜索 (按 NDCG@10 降序，节选 10 组)')
    print()
    print('| α(情感) | β(热度) | γ(时效) | NDCG@10 | NDCG@20 | MAP@20 |')
    print('|---------|---------|---------|---------|---------|--------|')
    for row in grid_sorted[:10]:
        print(f'| {row["alpha"]:.2f}    | {row["beta"]:.2f}    | {row["gamma"]:.2f}    '
              f'| {row["ndcg10"]:.4f}  | {row["ndcg20"]:.4f}  | {row["map20"]:.4f} |')

    # 表 A2: 包含本文 (0.4, 0.4, 0.2) 在排名中的位置
    paper_rank = next((i+1 for i, r in enumerate(grid_sorted)
                       if abs(r['alpha']-0.4)<1e-6 and abs(r['beta']-0.4)<1e-6
                       and abs(r['gamma']-0.2)<1e-6), None)
    if paper_rank:
        paper_row = grid_sorted[paper_rank-1]
        print(f'\n本文配置 (0.4, 0.4, 0.2) 在 36 组中排名第 {paper_rank}，'
              f'NDCG@10 = {paper_row["ndcg10"]:.4f}')

    # 表 B: 维度消融
    print()
    print('表 B — 维度消融实验')
    print()
    print('| 模型变体                   | α     | β     | γ     | NDCG@10 | NDCG@20 | MAP@20 |')
    print('|----------------------------|-------|-------|-------|---------|---------|--------|')
    for row in ablation:
        print(f'| {row["config"]:<26} | {row["alpha"]:.3f} | {row["beta"]:.3f} | {row["gamma"]:.3f} '
              f'| {row["ndcg10"]:.4f}  | {row["ndcg20"]:.4f}  | {row["map20"]:.4f} |')

    print()
    print('=' * 88)


if __name__ == '__main__':
    main()
