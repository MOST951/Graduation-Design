"""
系统架构图生成器
================

自动生成论文中的系统架构图

功能：
1. 系统总体架构图
2. 双维度排序算法流程图
3. 混合情感分析流程图
4. 伪集群部署图

技术：使用Graphviz和Mermaid生成图表
"""

import os
import subprocess
from typing import Optional

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'architecture_diagrams')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_graphviz() -> bool:
    """检查Graphviz是否安装"""
    try:
        result = subprocess.run(['dot', '-V'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def generate_dot_file(content: str, filename: str) -> str:
    """生成DOT文件"""
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.dot")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath


def render_graphviz(dot_file: str, output_format: str = 'png') -> Optional[str]:
    """渲染Graphviz图"""
    if not check_graphviz():
        print("警告: Graphviz未安装，跳过渲染")
        return None
    
    output_file = dot_file.replace('.dot', f'.{output_format}')
    
    try:
        subprocess.run(
            ['dot', f'-T{output_format}', dot_file, '-o', output_file],
            check=True,
            capture_output=True
        )
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"渲染失败: {e}")
        return None


def generate_mermaid_file(content: str, filename: str) -> str:
    """生成Mermaid文件"""
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.mmd")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath


# ==================== 系统总体架构图 ====================

def generate_system_architecture():
    """生成系统总体架构图"""
    
    dot_content = '''
digraph SystemArchitecture {
    rankdir=TB;
    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei"];
    
    // 颜色定义
    node [fillcolor="#E3F2FD"];
    
    // 数据采集层
    subgraph cluster_collection {
        label="数据采集层";
        style=filled;
        fillcolor="#E8F5E9";
        
        weibo_crawler [label="微博爬虫\\nWeibo Crawler", fillcolor="#C8E6C9"];
        hot_search [label="热搜监控\\nHot Search Monitor", fillcolor="#C8E6C9"];
    }
    
    // 数据存储层
    subgraph cluster_storage {
        label="数据存储层 (三层架构)";
        style=filled;
        fillcolor="#FFF3E0";
        
        hdfs [label="HDFS\\n原始数据存储\\n(Parquet格式)", fillcolor="#FFE0B2"];
        hbase [label="HBase\\n结构化数据存储\\n(热点话题表)", fillcolor="#FFE0B2"];
        mysql [label="MySQL\\n元数据存储\\n(任务/用户)", fillcolor="#FFE0B2"];
    }
    
    // 数据处理层
    subgraph cluster_processing {
        label="数据处理层";
        style=filled;
        fillcolor="#E1F5FE";
        
        spark_clean [label="Spark 数据清洗\\n去重/格式化/分词", fillcolor="#B3E5FC"];
        sentiment [label="混合情感分析\\n词典+BERT\\n(准确率87.2%)", fillcolor="#B3E5FC"];
        dual_rank [label="双维度排序\\nS = 0.6|E| + 0.4P", fillcolor="#BBDEFB", style="rounded,filled,bold"];
    }
    
    // 应用服务层
    subgraph cluster_service {
        label="应用服务层";
        style=filled;
        fillcolor="#F3E5F5";
        
        flask_api [label="Flask REST API\\n后端服务", fillcolor="#E1BEE7"];
        cache [label="缓存服务\\nLRU + SQLite", fillcolor="#E1BEE7"];
    }
    
    // 展示层
    subgraph cluster_presentation {
        label="展示层";
        style=filled;
        fillcolor="#FCE4EC";
        
        vue_frontend [label="Vue 3 前端\\n可视化仪表板", fillcolor="#F8BBD9"];
        echarts [label="ECharts\\n图表可视化", fillcolor="#F8BBD9"];
    }
    
    // 连接关系
    weibo_crawler -> hdfs [label="原始数据"];
    hot_search -> hdfs;
    
    hdfs -> spark_clean [label="批处理"];
    spark_clean -> hbase [label="清洗后数据"];
    spark_clean -> sentiment;
    
    sentiment -> dual_rank [label="情感得分"];
    hbase -> dual_rank [label="热度数据"];
    dual_rank -> hbase [label="排序结果"];
    
    hbase -> flask_api [label="查询"];
    mysql -> flask_api [label="元数据"];
    flask_api -> cache [label="缓存"];
    
    flask_api -> vue_frontend [label="REST API"];
    vue_frontend -> echarts;
}
'''
    
    dot_file = generate_dot_file(dot_content, 'system_architecture')
    render_graphviz(dot_file, 'png')
    render_graphviz(dot_file, 'svg')
    
    print(f"已生成: 系统总体架构图")
    return dot_file


# ==================== 双维度排序算法流程图 ====================

def generate_dual_dimension_flowchart():
    """生成双维度排序算法流程图"""
    
    dot_content = '''
digraph DualDimensionRanking {
    rankdir=TB;
    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei"];
    
    // 开始
    start [label="开始", shape=ellipse, fillcolor="#E8F5E9"];
    
    // 输入
    input [label="输入微博数据\\n(文本, 转发, 评论, 点赞, 时间)", fillcolor="#E3F2FD"];
    
    // 情感计算
    subgraph cluster_sentiment {
        label="情感得分计算";
        style=filled;
        fillcolor="#FFF8E1";
        
        sentiment_analysis [label="混合情感分析\\n(词典+BERT)", fillcolor="#FFECB3"];
        sentiment_score [label="情感强度 |E|\\n范围: [0, 1]", fillcolor="#FFE082"];
    }
    
    // 热度计算
    subgraph cluster_heat {
        label="热度得分计算";
        style=filled;
        fillcolor="#E8EAF6";
        
        heat_formula [label="P = log(1 + w₁×转发 + w₂×评论 + w₃×点赞)\\n默认: w₁=1, w₂=2, w₃=1", fillcolor="#C5CAE9"];
        time_decay [label="时间衰减\\nP' = P × e^(-γ×Δt)\\nγ=0.1", fillcolor="#9FA8DA"];
    }
    
    // 综合计算
    dual_score [label="综合得分计算\\nS = α×|E| + β×P'\\nα=0.6, β=0.4", fillcolor="#FFCDD2", style="rounded,filled,bold"];
    
    // 排序
    sort [label="按综合得分S降序排序", fillcolor="#B2DFDB"];
    
    // 输出
    output [label="输出排序结果\\n(话题列表, 得分, 排名)", fillcolor="#C8E6C9"];
    
    // 结束
    end [label="结束", shape=ellipse, fillcolor="#FFCDD2"];
    
    // 连接
    start -> input;
    input -> sentiment_analysis;
    input -> heat_formula;
    
    sentiment_analysis -> sentiment_score;
    heat_formula -> time_decay;
    
    sentiment_score -> dual_score;
    time_decay -> dual_score;
    
    dual_score -> sort;
    sort -> output;
    output -> end;
}
'''
    
    dot_file = generate_dot_file(dot_content, 'dual_dimension_flowchart')
    render_graphviz(dot_file, 'png')
    render_graphviz(dot_file, 'svg')
    
    print(f"已生成: 双维度排序算法流程图")
    return dot_file


# ==================== 混合情感分析流程图 ====================

def generate_sentiment_analysis_flowchart():
    """生成混合情感分析流程图"""
    
    dot_content = '''
digraph SentimentAnalysis {
    rankdir=TB;
    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei"];
    
    // 输入
    input [label="输入文本", shape=ellipse, fillcolor="#E8F5E9"];
    
    // 预处理
    preprocess [label="文本预处理\\n分词/去停用词/标准化", fillcolor="#E3F2FD"];
    
    // 并行分析
    subgraph cluster_parallel {
        label="并行情感分析";
        style=filled;
        fillcolor="#F5F5F5";
        
        // 词典方法
        subgraph cluster_dict {
            label="词典方法";
            style=filled;
            fillcolor="#FFF3E0";
            
            dict_match [label="情感词典匹配\\n(正面词/负面词)", fillcolor="#FFE0B2"];
            dict_score [label="词典得分\\n准确率: 72.3%", fillcolor="#FFCC80"];
        }
        
        // BERT方法
        subgraph cluster_bert {
            label="BERT方法";
            style=filled;
            fillcolor="#E8F5E9";
            
            bert_encode [label="ChineseBERT\\n文本编码", fillcolor="#C8E6C9"];
            bert_classify [label="分类层\\n准确率: 85.6%", fillcolor="#A5D6A7"];
        }
    }
    
    // 混合策略
    subgraph cluster_fusion {
        label="混合策略";
        style=filled;
        fillcolor="#FCE4EC";
        
        confidence [label="置信度评估", fillcolor="#F8BBD9"];
        fusion [label="加权融合\\n最终得分 = w₁×词典 + w₂×BERT", fillcolor="#F48FB1"];
    }
    
    // 输出
    output [label="输出结果\\n情感标签 + 置信度\\n准确率: 87.2%", fillcolor="#BBDEFB", style="rounded,filled,bold"];
    
    // 连接
    input -> preprocess;
    preprocess -> dict_match;
    preprocess -> bert_encode;
    
    dict_match -> dict_score;
    bert_encode -> bert_classify;
    
    dict_score -> confidence;
    bert_classify -> confidence;
    
    confidence -> fusion;
    fusion -> output;
}
'''
    
    dot_file = generate_dot_file(dot_content, 'sentiment_analysis_flowchart')
    render_graphviz(dot_file, 'png')
    render_graphviz(dot_file, 'svg')
    
    print(f"已生成: 混合情感分析流程图")
    return dot_file


# ==================== 伪集群部署图 ====================

def generate_deployment_diagram():
    """生成伪集群部署图"""
    
    dot_content = '''
digraph Deployment {
    rankdir=TB;
    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei"];
    
    // 单机服务器
    subgraph cluster_server {
        label="单机伪集群部署 (开发/演示环境)";
        style=filled;
        fillcolor="#ECEFF1";
        
        // Hadoop生态
        subgraph cluster_hadoop {
            label="Hadoop 生态系统";
            style=filled;
            fillcolor="#E3F2FD";
            
            hdfs_nn [label="HDFS NameNode\\nPort: 9870", fillcolor="#BBDEFB"];
            hdfs_dn [label="HDFS DataNode\\nPort: 9864", fillcolor="#BBDEFB"];
            
            spark_master [label="Spark Master\\nPort: 8080", fillcolor="#B3E5FC"];
            spark_worker [label="Spark Worker\\nPort: 8081", fillcolor="#B3E5FC"];
            
            hbase_master [label="HBase Master\\nPort: 16010", fillcolor="#B2EBF2"];
            hbase_rs [label="HBase RegionServer\\nPort: 16030", fillcolor="#B2EBF2"];
            
            zk [label="ZooKeeper\\nPort: 2181", fillcolor="#C8E6C9"];
        }
        
        // 应用服务
        subgraph cluster_app {
            label="应用服务";
            style=filled;
            fillcolor="#FFF3E0";
            
            flask [label="Flask Backend\\nPort: 5000", fillcolor="#FFE0B2"];
            vue [label="Vue Frontend\\nPort: 3000", fillcolor="#FFCC80"];
        }
        
        // 数据库
        subgraph cluster_db {
            label="数据库";
            style=filled;
            fillcolor="#F3E5F5";
            
            mysql [label="MySQL\\nPort: 3306", fillcolor="#E1BEE7"];
        }
    }
    
    // 外部访问
    browser [label="浏览器\\n用户访问", shape=ellipse, fillcolor="#DCEDC8"];
    
    // 连接关系
    browser -> vue [label="HTTP :3000"];
    vue -> flask [label="REST API :5000"];
    
    flask -> mysql [label="JDBC :3306"];
    flask -> hbase_master [label="Thrift :9090"];
    
    spark_master -> hdfs_nn [label="HDFS"];
    spark_worker -> spark_master;
    spark_worker -> hdfs_dn;
    
    hbase_master -> hdfs_nn;
    hbase_rs -> hbase_master;
    hbase_rs -> zk;
    
    hdfs_dn -> hdfs_nn;
}
'''
    
    dot_file = generate_dot_file(dot_content, 'deployment_diagram')
    render_graphviz(dot_file, 'png')
    render_graphviz(dot_file, 'svg')
    
    print(f"已生成: 伪集群部署图")
    return dot_file


# ==================== 数据流图 ====================

def generate_dataflow_diagram():
    """生成数据流图"""
    
    dot_content = '''
digraph DataFlow {
    rankdir=LR;
    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei", fontsize=10];
    
    // 数据源
    weibo [label="微博平台", shape=cylinder, fillcolor="#E8F5E9"];
    
    // 处理节点
    crawler [label="爬虫采集", fillcolor="#C8E6C9"];
    hdfs [label="HDFS\\n原始存储", shape=cylinder, fillcolor="#BBDEFB"];
    spark [label="Spark\\n数据清洗", fillcolor="#B3E5FC"];
    sentiment [label="情感分析", fillcolor="#FFE082"];
    ranking [label="双维度排序", fillcolor="#FFCDD2"];
    hbase [label="HBase\\n结果存储", shape=cylinder, fillcolor="#B2EBF2"];
    api [label="REST API", fillcolor="#E1BEE7"];
    frontend [label="前端展示", fillcolor="#F8BBD9"];
    
    // 数据流
    weibo -> crawler [label="HTTP请求"];
    crawler -> hdfs [label="JSON/Parquet"];
    hdfs -> spark [label="批处理"];
    spark -> sentiment [label="清洗后数据"];
    sentiment -> ranking [label="情感得分"];
    ranking -> hbase [label="排序结果"];
    hbase -> api [label="查询"];
    api -> frontend [label="JSON"];
    
    // 反馈
    frontend -> api [label="用户请求", style=dashed];
}
'''
    
    dot_file = generate_dot_file(dot_content, 'dataflow_diagram')
    render_graphviz(dot_file, 'png')
    render_graphviz(dot_file, 'svg')
    
    print(f"已生成: 数据流图")
    return dot_file


# ==================== Mermaid格式 ====================

def generate_mermaid_diagrams():
    """生成Mermaid格式的图表（用于Markdown）"""
    
    # 系统架构
    system_arch_mermaid = '''
graph TB
    subgraph 数据采集层
        A[微博爬虫] --> B[热搜监控]
    end
    
    subgraph 数据存储层
        C[(HDFS<br>原始数据)]
        D[(HBase<br>结构化数据)]
        E[(MySQL<br>元数据)]
    end
    
    subgraph 数据处理层
        F[Spark数据清洗]
        G[混合情感分析<br>准确率87.2%]
        H[双维度排序<br>S=0.6|E|+0.4P]
    end
    
    subgraph 应用服务层
        I[Flask REST API]
        J[缓存服务]
    end
    
    subgraph 展示层
        K[Vue 3 前端]
        L[ECharts可视化]
    end
    
    A --> C
    B --> C
    C --> F
    F --> D
    F --> G
    G --> H
    H --> D
    D --> I
    E --> I
    I --> J
    I --> K
    K --> L
'''
    
    generate_mermaid_file(system_arch_mermaid, 'system_architecture')
    
    # 双维度排序流程
    dual_rank_mermaid = '''
flowchart TD
    A[输入微博数据] --> B[文本预处理]
    B --> C{并行处理}
    C --> D[情感分析]
    C --> E[热度计算]
    D --> F[情感强度 |E|]
    E --> G[热度得分 P]
    G --> H[时间衰减 P']
    F --> I[综合得分<br>S = 0.6×|E| + 0.4×P']
    H --> I
    I --> J[降序排序]
    J --> K[输出排序结果]
    
    style I fill:#ffcdd2
    style F fill:#fff3e0
    style H fill:#e8eaf6
'''
    
    generate_mermaid_file(dual_rank_mermaid, 'dual_dimension_flowchart')
    
    # 情感分析流程
    sentiment_mermaid = '''
flowchart TD
    A[输入文本] --> B[文本预处理<br>分词/去停用词]
    B --> C{并行分析}
    C --> D[词典方法<br>准确率72.3%]
    C --> E[BERT方法<br>准确率85.6%]
    D --> F[词典得分]
    E --> G[BERT得分]
    F --> H[置信度评估]
    G --> H
    H --> I[加权融合]
    I --> J[输出结果<br>准确率87.2%]
    
    style J fill:#bbdefb
    style D fill:#fff3e0
    style E fill:#e8f5e9
'''
    
    generate_mermaid_file(sentiment_mermaid, 'sentiment_analysis_flowchart')
    
    print("已生成: Mermaid格式图表")


# ==================== 主函数 ====================

def main():
    """生成所有架构图"""
    
    print("=" * 50)
    print("系统架构图生成器")
    print("=" * 50)
    
    graphviz_available = check_graphviz()
    if not graphviz_available:
        print("\n警告: Graphviz未安装，将只生成DOT和Mermaid源文件")
        print("安装Graphviz后可渲染为PNG/SVG图片")
        print("下载地址: https://graphviz.org/download/")
    
    print("\n[1/5] 生成系统总体架构图...")
    generate_system_architecture()
    
    print("\n[2/5] 生成双维度排序算法流程图...")
    generate_dual_dimension_flowchart()
    
    print("\n[3/5] 生成混合情感分析流程图...")
    generate_sentiment_analysis_flowchart()
    
    print("\n[4/5] 生成伪集群部署图...")
    generate_deployment_diagram()
    
    print("\n[5/5] 生成数据流图...")
    generate_dataflow_diagram()
    
    print("\n生成Mermaid格式图表...")
    generate_mermaid_diagrams()
    
    print("\n" + "=" * 50)
    print("完成!")
    print(f"所有文件已保存到: {OUTPUT_DIR}")
    print("\n生成的文件:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        print(f"  - {f}")
    
    if not graphviz_available:
        print("\n提示: 安装Graphviz后重新运行可生成PNG/SVG图片")


if __name__ == '__main__':
    main()
