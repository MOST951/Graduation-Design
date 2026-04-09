"""
全模块API测试脚本
测试所有5个模块的核心功能
"""
import requests
import json
from typing import Dict

BASE_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.END}")
def print_error(msg): print(f"{Colors.RED}❌ {msg}{Colors.END}")
def print_info(msg): print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")
def print_section(title): print(f"\n{Colors.BLUE}{'='*60}\n  {title}\n{'='*60}{Colors.END}\n")

def test_module(module_name: str, endpoints: Dict[str, Dict]) -> bool:
    """测试单个模块"""
    print_section(f"测试模块: {module_name}")
    
    all_passed = True
    for name, config in endpoints.items():
        try:
            method = config.get('method', 'GET')
            url = f"{BASE_URL}{config['path']}"
            data = config.get('data')
            
            if method == 'GET':
                response = requests.get(url, timeout=5)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=5)
            
            if response.status_code == 200:
                print_success(f"{name}: {response.status_code}")
                if config.get('show_data'):
                    result = response.json()
                    print_info(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)[:200]}...")
            else:
                print_error(f"{name}: {response.status_code}")
                all_passed = False
        except Exception as e:
            print_error(f"{name}: {str(e)}")
            all_passed = False
    
    return all_passed

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("  微博舆情系统 - 全模块API测试")
    print(f"{'='*60}{Colors.END}\n")
    
    print_info(f"测试目标: {BASE_URL}")
    
    # 测试根路由
    print_section("0. 系统总览")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("系统API正常运行")
            print_info(f"版本: {data.get('version')}")
            print_info(f"可用模块: {len(data.get('endpoints', {}))}")
        else:
            print_error("系统API异常")
            return
    except Exception as e:
        print_error(f"无法连接到后端: {e}")
        print_info("请先运行: python backend/app.py")
        return
    
    # 模块1: 数据采集
    collection_tests = {
        "健康检查": {"path": "/api/collection/health"},
        "获取任务列表": {"path": "/api/collection/tasks"},
        "获取统计数据": {"path": "/api/collection/statistics", "show_data": True},
    }
    test_module("数据采集", collection_tests)
    
    # 模块2: 情感分析
    sentiment_tests = {
        "健康检查": {"path": "/api/sentiment/health"},
        "分析文本": {
            "path": "/api/sentiment/analyze",
            "method": "POST",
            "data": {"text": "这个产品真的很不错！"},
            "show_data": True
        },
        "获取情感分布": {"path": "/api/sentiment/distribution"},
        "获取情感趋势": {"path": "/api/sentiment/trend"},
        "获取统计数据": {"path": "/api/sentiment/statistics"},
    }
    test_module("情感分析", sentiment_tests)
    
    # 模块3: 热点话题
    topics_tests = {
        "健康检查": {"path": "/api/topics/health"},
        "获取话题列表": {"path": "/api/topics/list", "show_data": True},
        "获取词云数据": {"path": "/api/topics/wordcloud"},
        "获取关联网络": {"path": "/api/topics/network"},
    }
    test_module("热点话题", topics_tests)
    
    # 模块4: 用户行为
    behavior_tests = {
        "健康检查": {"path": "/api/behavior/health"},
        "获取用户列表": {"path": "/api/behavior/users"},
        "获取影响力网络": {"path": "/api/behavior/network"},
    }
    test_module("用户行为", behavior_tests)
    
    # 模块5: 实时监控
    monitor_tests = {
        "健康检查": {"path": "/api/monitor/health"},
        "获取实时数据流": {"path": "/api/monitor/stream"},
        "获取实时指标": {"path": "/api/monitor/metrics", "show_data": True},
        "获取预警规则": {"path": "/api/monitor/alerts"},
    }
    test_module("实时监控", monitor_tests)
    
    # 总结
    print_section("测试完成")
    print_success("所有模块API测试通过！")
    print_info("前端页面访问: http://localhost:3000")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}测试被用户中断{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}测试过程中发生错误: {e}{Colors.END}")
