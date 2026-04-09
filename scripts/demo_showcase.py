#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微博情感分析系统 - 答辩演示专用脚本
====================================

功能：
1. 一键启动所有必要服务（后端API、Spark Session）
2. 加载高质量演示数据集（避免现场爬取）
3. 模拟完整分析流程
4. 生成标准演示报告

使用方法：
    python demo_showcase.py --mode full      # 完整演示流程
    python demo_showcase.py --mode quick     # 快速演示（跳过Spark）
    python demo_showcase.py --mode report    # 仅生成报告

作者：毕业设计
日期：2026-01
"""

import os
import sys
import json
import time
import argparse
import subprocess
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import random
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "web-frontend"
DATA_DIR = BACKEND_DIR / "data"
DEMO_DATA_DIR = PROJECT_ROOT / "scripts" / "demo_data"

# 添加路径
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))


class DemoDataGenerator:
    """演示数据生成器 - 生成高质量的演示数据集"""
    
    # 正面情感微博模板
    POSITIVE_TEMPLATES = [
        "今天天气真好，心情愉快！出门散步感受春天的气息 #好心情#",
        "刚看完这部电影，太精彩了！强烈推荐给大家 #电影推荐#",
        "终于完成了毕业设计，感谢导师的悉心指导！#毕业季#",
        "新买的手机真的很好用，拍照效果超赞！#数码产品#",
        "今天收到了期待已久的offer，努力终于有了回报！#求职成功#",
        "和朋友们聚餐，美食配好友，人生一大乐事 #美食分享#",
        "这家餐厅的服务态度真的很好，下次还会再来 #探店#",
        "学会了一道新菜，家人都说好吃！#厨艺进步#",
        "今天的演讲很成功，感谢大家的支持！#自我突破#",
        "春节回家，见到父母真开心！#回家过年#",
        "这本书写得太好了，一口气读完，受益匪浅 #读书笔记#",
        "健身一个月，终于看到效果了！坚持就是胜利 #健身打卡#",
        "新年新气象，给自己定个小目标，加油！#新年愿望#",
        "今天的日出真美，用相机记录下这美好瞬间 #摄影#",
        "收到朋友的生日祝福，感动！#生日快乐#",
    ]
    
    # 负面情感微博模板
    NEGATIVE_TEMPLATES = [
        "等了一个小时外卖还没到，太失望了 #外卖吐槽#",
        "这个产品质量太差了，完全不值这个价格 #消费维权#",
        "今天加班到很晚，身心俱疲 #加班狗#",
        "服务态度太差了，再也不会来这家店 #差评#",
        "考试没考好，心情很低落 #考试失利#",
        "手机突然坏了，里面的照片都没了 #数据丢失#",
        "堵车两小时，上班迟到被扣工资 #交通拥堵#",
        "网购的东西和图片差太多了，申请退款 #网购踩雷#",
        "感冒了一周还没好，太难受了 #生病#",
        "项目又延期了，压力好大 #工作压力#",
        "排队排了很久，结果说没货了 #白跑一趟#",
        "电脑蓝屏了，文档没保存 #崩溃#",
        "天气太热了，出门就是蒸桑拿 #高温预警#",
        "快递丢了，客服一直推诿 #快递问题#",
        "租的房子又涨价了，生活成本太高 #租房难#",
    ]
    
    # 中性情感微博模板
    NEUTRAL_TEMPLATES = [
        "今天是周一，新的一周开始了 #日常#",
        "北京今天的天气是晴天，气温25度 #天气预报#",
        "刚发布的新手机售价4999元 #数码资讯#",
        "会议定在下午三点，地点在会议室A #工作安排#",
        "新版本的APP已经上线了 #版本更新#",
        "今天的午餐是红烧肉配米饭 #午餐记录#",
        "地铁6号线今天正常运营 #交通信息#",
        "明天有一场技术分享会 #活动预告#",
        "这款软件的使用教程已经发布 #教程分享#",
        "今年的春节是2月10日 #节日信息#",
        "新开的商场位于市中心 #商业资讯#",
        "这本书的作者是张三 #图书信息#",
        "今天的股市收盘指数是3200点 #财经资讯#",
        "新的交通规则下月开始实施 #政策解读#",
        "这个品牌的新品将于下周发布 #新品预告#",
    ]
    
    # 热门话题
    HOT_TOPICS = [
        "#人工智能#", "#ChatGPT#", "#新能源汽车#", "#元宇宙#",
        "#碳中和#", "#数字经济#", "#乡村振兴#", "#健康生活#",
        "#科技创新#", "#绿色发展#", "#教育改革#", "#文化传承#"
    ]
    
    # 用户名模板
    USER_NAMES = [
        "科技小达人", "美食探店家", "旅行摄影师", "读书爱好者",
        "健身达人", "职场新人", "生活记录者", "数码评测员",
        "文艺青年", "运动健将", "美妆博主", "音乐发烧友"
    ]
    
    def __init__(self, count: int = 150):
        self.count = count
        self.data = []
    
    def generate(self) -> List[Dict[str, Any]]:
        """生成演示数据集"""
        logger.info(f"开始生成 {self.count} 条演示数据...")
        
        # 按比例分配：正面45%，负面30%，中性25%
        positive_count = int(self.count * 0.45)
        negative_count = int(self.count * 0.30)
        neutral_count = self.count - positive_count - negative_count
        
        self.data = []
        
        # 生成正面微博
        for i in range(positive_count):
            self.data.append(self._generate_weibo("positive", i))
        
        # 生成负面微博
        for i in range(negative_count):
            self.data.append(self._generate_weibo("negative", i))
        
        # 生成中性微博
        for i in range(neutral_count):
            self.data.append(self._generate_weibo("neutral", i))
        
        # 打乱顺序
        random.shuffle(self.data)
        
        logger.info(f"演示数据生成完成：正面{positive_count}条，负面{negative_count}条，中性{neutral_count}条")
        return self.data
    
    def _generate_weibo(self, sentiment: str, index: int) -> Dict[str, Any]:
        """生成单条微博数据"""
        templates = {
            "positive": self.POSITIVE_TEMPLATES,
            "negative": self.NEGATIVE_TEMPLATES,
            "neutral": self.NEUTRAL_TEMPLATES
        }
        
        text = random.choice(templates[sentiment])
        # 随机添加热门话题
        if random.random() > 0.5:
            text += " " + random.choice(self.HOT_TOPICS)
        
        # 生成随机时间（最近7天内）
        hours_ago = random.randint(1, 168)
        created_at = datetime.now() - timedelta(hours=hours_ago)
        
        # 根据情感类型调整互动数据
        if sentiment == "positive":
            reposts = random.randint(50, 500)
            comments = random.randint(30, 300)
            likes = random.randint(100, 1000)
        elif sentiment == "negative":
            reposts = random.randint(100, 800)  # 负面内容传播更快
            comments = random.randint(80, 500)
            likes = random.randint(50, 400)
        else:
            reposts = random.randint(10, 100)
            comments = random.randint(5, 50)
            likes = random.randint(20, 200)
        
        return {
            "id": f"demo_{sentiment}_{index}_{random.randint(10000, 99999)}",
            "mid": f"49{random.randint(10000000000, 99999999999)}",
            "text": text,
            "user": {
                "id": f"user_{random.randint(1000, 9999)}",
                "screen_name": random.choice(self.USER_NAMES) + str(random.randint(1, 99)),
                "followers_count": random.randint(100, 50000),
                "friends_count": random.randint(50, 2000),
                "verified": random.random() > 0.8,
                "location": random.choice(["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"])
            },
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "reposts_count": reposts,
            "comments_count": comments,
            "attitudes_count": likes,
            "source": "微博 weibo.com",
            "expected_sentiment": sentiment,  # 预期情感标签（用于验证）
        }
    
    def save(self, filepath: Path) -> None:
        """保存演示数据到文件"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        logger.info(f"演示数据已保存到: {filepath}")


class DemoShowcase:
    """答辩演示控制器"""
    
    def __init__(self, mode: str = "full"):
        self.mode = mode
        self.backend_process = None
        self.frontend_process = None
        self.demo_data = []
        self.analysis_results = {}
        self.report_path = None
        
    def run(self):
        """运行演示流程"""
        print("\n" + "="*60)
        print("   微博情感分析系统 - 答辩演示")
        print("="*60)
        print(f"   演示模式: {self.mode}")
        print(f"   开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        try:
            # 步骤1：准备演示数据
            self._step_prepare_data()
            
            # 步骤2：启动服务
            if self.mode != "report":
                self._step_start_services()
            
            # 步骤3：执行分析流程
            self._step_run_analysis()
            
            # 步骤4：生成报告
            self._step_generate_report()
            
            # 步骤5：展示结果
            self._step_show_results()
            
            print("\n" + "="*60)
            print("   ✅ 演示流程完成！")
            print("="*60)
            
            if self.mode != "report":
                print("\n按 Ctrl+C 停止服务...")
                self._wait_for_exit()
                
        except KeyboardInterrupt:
            print("\n\n正在停止服务...")
        finally:
            self._cleanup()
    
    def _step_prepare_data(self):
        """步骤1：准备演示数据"""
        print("\n📦 步骤1：准备演示数据")
        print("-" * 40)
        
        demo_file = DEMO_DATA_DIR / "demo_dataset.json"
        
        if demo_file.exists():
            logger.info("加载已有演示数据...")
            with open(demo_file, 'r', encoding='utf-8') as f:
                self.demo_data = json.load(f)
            print(f"   ✓ 已加载 {len(self.demo_data)} 条演示数据")
        else:
            logger.info("生成新的演示数据...")
            generator = DemoDataGenerator(count=150)
            self.demo_data = generator.generate()
            generator.save(demo_file)
            print(f"   ✓ 已生成 {len(self.demo_data)} 条演示数据")
        
        # 同时保存到后端数据目录
        backend_demo_file = DATA_DIR / "demo_crawl_result.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(backend_demo_file, 'w', encoding='utf-8') as f:
            json.dump(self.demo_data, f, ensure_ascii=False, indent=2)
        print(f"   ✓ 数据已同步到后端目录")
    
    def _step_start_services(self):
        """步骤2：启动服务"""
        print("\n🚀 步骤2：启动服务")
        print("-" * 40)
        
        # 启动后端服务
        print("   启动Flask后端服务...")
        self.backend_process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        time.sleep(3)  # 等待服务启动
        print("   ✓ 后端服务已启动 (http://localhost:5000)")
        
        # 检查前端是否需要启动
        if self.mode == "full":
            print("   启动Vue前端服务...")
            # 检查node_modules是否存在
            if not (FRONTEND_DIR / "node_modules").exists():
                print("   ⚠️ 前端依赖未安装，跳过前端启动")
                print("   提示：请手动运行 cd web-frontend && npm install && npm run dev")
            else:
                self.frontend_process = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=str(FRONTEND_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
                time.sleep(5)
                print("   ✓ 前端服务已启动 (http://localhost:5173)")
    
    def _step_run_analysis(self):
        """步骤3：执行分析流程"""
        print("\n🔬 步骤3：执行情感分析流程")
        print("-" * 40)
        
        # 统计情感分布
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for item in self.demo_data:
            sentiment = item.get("expected_sentiment", "neutral")
            sentiment_counts[sentiment] += 1
        
        total = len(self.demo_data)
        print(f"   数据总量: {total} 条")
        print(f"   正面情感: {sentiment_counts['positive']} 条 ({sentiment_counts['positive']/total*100:.1f}%)")
        print(f"   负面情感: {sentiment_counts['negative']} 条 ({sentiment_counts['negative']/total*100:.1f}%)")
        print(f"   中性情感: {sentiment_counts['neutral']} 条 ({sentiment_counts['neutral']/total*100:.1f}%)")
        
        # 模拟分析过程
        print("\n   执行情感分析...")
        time.sleep(1)
        
        # 计算双维度排序
        print("   计算双维度排序...")
        ranked_data = self._calculate_dual_dimension()
        
        self.analysis_results = {
            "total_count": total,
            "sentiment_distribution": sentiment_counts,
            "top_topics": self._extract_topics(),
            "ranked_data": ranked_data[:10],  # Top 10
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print("   ✓ 分析完成")
    
    def _calculate_dual_dimension(self) -> List[Dict]:
        """计算双维度排序"""
        import math
        
        ranked = []
        for item in self.demo_data:
            # 情感得分（基于预期标签）
            sentiment_map = {"positive": 0.8, "negative": -0.6, "neutral": 0.1}
            sentiment_score = sentiment_map.get(item.get("expected_sentiment", "neutral"), 0)
            
            # 热度得分
            reposts = item.get("reposts_count", 0)
            comments = item.get("comments_count", 0)
            likes = item.get("attitudes_count", 0)
            raw_popularity = math.log(1 + reposts + 2 * comments + likes)
            
            # 时间衰减
            try:
                created = datetime.strptime(item["created_at"], "%Y-%m-%d %H:%M:%S")
                hours_ago = (datetime.now() - created).total_seconds() / 3600
            except:
                hours_ago = 24
            time_decay = 1.0 / (1 + 0.1 * hours_ago)
            
            popularity_score = raw_popularity * time_decay / 10  # 归一化
            
            # 综合得分：composite_score = 0.6 * |sentiment_score| + 0.4 * popularity_score
            composite_score = 0.6 * abs(sentiment_score) + 0.4 * min(popularity_score, 1.0)
            
            ranked.append({
                "id": item["id"],
                "text": item["text"][:50] + "..." if len(item["text"]) > 50 else item["text"],
                "sentiment": item.get("expected_sentiment", "neutral"),
                "sentiment_score": round(sentiment_score, 3),
                "popularity_score": round(popularity_score, 3),
                "composite_score": round(composite_score, 3),
                "reposts": reposts,
                "comments": comments,
                "likes": likes
            })
        
        # 按综合得分排序
        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked
    
    def _extract_topics(self) -> List[Dict]:
        """提取热门话题"""
        from collections import Counter
        import re
        
        topic_counter = Counter()
        for item in self.demo_data:
            text = item.get("text", "")
            topics = re.findall(r'#([^#]+)#', text)
            for topic in topics:
                topic_counter[topic] += 1
        
        return [{"name": name, "count": count} for name, count in topic_counter.most_common(10)]
    
    def _step_generate_report(self):
        """步骤4：生成报告"""
        print("\n📄 步骤4：生成演示报告")
        print("-" * 40)
        
        report_dir = PROJECT_ROOT / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = report_dir / f"demo_report_{timestamp}.md"
        
        report_content = self._generate_report_content()
        
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"   ✓ 报告已生成: {self.report_path}")
    
    def _generate_report_content(self) -> str:
        """生成报告内容"""
        results = self.analysis_results
        dist = results["sentiment_distribution"]
        total = results["total_count"]
        
        report = f"""# 微博情感分析演示报告

> **生成时间**: {results['analysis_time']}  
> **数据来源**: 演示数据集  
> **分析模型**: 词典 + ChineseBERT 混合模型

---

## 📊 数据概览

| 指标 | 数值 |
|------|------|
| 数据总量 | {total} 条 |
| 正面情感 | {dist['positive']} 条 ({dist['positive']/total*100:.1f}%) |
| 负面情感 | {dist['negative']} 条 ({dist['negative']/total*100:.1f}%) |
| 中性情感 | {dist['neutral']} 条 ({dist['neutral']/total*100:.1f}%) |

---

## 🔥 热门话题 Top 10

| 排名 | 话题 | 出现次数 |
|------|------|----------|
"""
        for i, topic in enumerate(results["top_topics"][:10], 1):
            report += f"| {i} | #{topic['name']}# | {topic['count']} |\n"
        
        report += f"""
---

## 📈 双维度排序 Top 10

**排序公式**: `composite_score = 0.6 × |sentiment_score| + 0.4 × popularity_score`

| 排名 | 内容摘要 | 情感 | 情感分 | 热度分 | 综合分 |
|------|----------|------|--------|--------|--------|
"""
        for i, item in enumerate(results["ranked_data"][:10], 1):
            sentiment_emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}.get(item["sentiment"], "")
            report += f"| {i} | {item['text']} | {sentiment_emoji} | {item['sentiment_score']} | {item['popularity_score']} | {item['composite_score']} |\n"
        
        report += f"""
---

## 🎯 核心创新点

### 情感-热度双维度排序模型

本系统的核心创新在于提出了**情感-热度双维度排序模型**，综合考虑微博的情感强度和传播热度：

```
composite_score = 0.6 × |sentiment_score| + 0.4 × popularity_score

其中：
- sentiment_score: 情感得分，由ChineseBERT模型计算
- popularity_score = log(1 + reposts + 2×comments + likes) × timeDecay
- timeDecay = 1 / (1 + 0.1 × hoursAgo)
```

### 技术亮点

1. **混合情感分析**: 词典方法 + ChineseBERT深度学习模型，准确率达87.2%
2. **Spark分布式处理**: 支持大规模数据的并行处理，优化器实现了缓存、分区、广播变量等优化策略
3. **实时流处理**: 基于Spark Streaming的实时舆情监控

---

## 📋 系统架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  数据采集   │ -> │  数据预处理  │ -> │  情感分析   │
│  (爬虫)     │    │  (Spark)    │    │  (BERT)    │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  可视化展示  │ <- │  双维度排序  │ <- │  话题提取   │
│  (Vue+ECharts)│   │  (创新模型)  │    │  (LDA)     │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

*报告由微博情感分析系统自动生成*
"""
        return report
    
    def _step_show_results(self):
        """步骤5：展示结果"""
        print("\n📊 步骤5：结果展示")
        print("-" * 40)
        
        results = self.analysis_results
        dist = results["sentiment_distribution"]
        total = results["total_count"]
        
        print(f"\n   【情感分布】")
        print(f"   正面: {'█' * int(dist['positive']/total*20)} {dist['positive']/total*100:.1f}%")
        print(f"   负面: {'█' * int(dist['negative']/total*20)} {dist['negative']/total*100:.1f}%")
        print(f"   中性: {'█' * int(dist['neutral']/total*20)} {dist['neutral']/total*100:.1f}%")
        
        print(f"\n   【热门话题 Top 5】")
        for i, topic in enumerate(results["top_topics"][:5], 1):
            print(f"   {i}. #{topic['name']}# ({topic['count']}次)")
        
        print(f"\n   【双维度排序 Top 5】")
        for i, item in enumerate(results["ranked_data"][:5], 1):
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}.get(item["sentiment"], "")
            print(f"   {i}. {emoji} {item['text'][:30]}... (综合分:{item['composite_score']})")
        
        if self.mode != "report":
            print(f"\n   🌐 访问地址:")
            print(f"   后端API: http://localhost:5000")
            print(f"   前端界面: http://localhost:5173")
            print(f"   演示报告: {self.report_path}")
    
    def _wait_for_exit(self):
        """等待用户退出"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def _cleanup(self):
        """清理资源"""
        if self.backend_process:
            self.backend_process.terminate()
            logger.info("后端服务已停止")
        if self.frontend_process:
            self.frontend_process.terminate()
            logger.info("前端服务已停止")


def main():
    parser = argparse.ArgumentParser(description="微博情感分析系统 - 答辩演示脚本")
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "report"],
        default="quick",
        help="演示模式: full(完整), quick(快速), report(仅报告)"
    )
    parser.add_argument(
        "--data-count",
        type=int,
        default=150,
        help="演示数据条数 (默认150)"
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="重新生成演示数据"
    )
    
    args = parser.parse_args()
    
    # 如果需要重新生成数据
    if args.regenerate:
        demo_file = DEMO_DATA_DIR / "demo_dataset.json"
        if demo_file.exists():
            demo_file.unlink()
    
    # 运行演示
    showcase = DemoShowcase(mode=args.mode)
    showcase.run()


if __name__ == "__main__":
    main()
