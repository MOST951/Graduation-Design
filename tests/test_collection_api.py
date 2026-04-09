"""
数据采集模块 API 测试脚本
测试所有核心功能
"""
import requests
import json
import time
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:8080/api/collection"
HEADERS = {"Content-Type": "application/json"}

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_section(title: str):
    print(f"\n{Colors.BLUE}{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}{Colors.END}\n")

def test_health_check():
    """测试健康检查"""
    print_section("1. 健康检查")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"服务正常运行")
            print_info(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return True
        else:
            print_error(f"健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"连接失败: {e}")
        print_warning("请确保后端服务已启动: python backend/app.py")
        return False

def test_get_statistics():
    """测试获取统计数据"""
    print_section("2. 获取统计数据")
    try:
        response = requests.get(f"{BASE_URL}/statistics")
        if response.status_code == 200:
            data = response.json()['data']
            print_success("统计数据获取成功")
            print_info(f"总任务数: {data['totalTasks']}")
            print_info(f"运行中: {data['runningTasks']}")
            print_info(f"已完成: {data['completedTasks']}")
            print_info(f"总采集: {data['totalCollected']}")
            print_info(f"成功率: {data['successRate']}%")
            return True
        else:
            print_error(f"获取统计失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_create_task():
    """测试创建任务"""
    print_section("3. 创建任务")
    task_data = {
        "name": "API测试任务",
        "keywords": [
            {"word": "测试关键词1", "weight": 1.0},
            {"word": "测试关键词2", "weight": 0.8}
        ],
        "dataSources": ["weibo", "wechat"],
        "maxCount": 100,
        "requestInterval": 2
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=HEADERS,
            json=task_data
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            task_id = data['id']
            print_success(f"任务创建成功")
            print_info(f"任务ID: {task_id}")
            print_info(f"任务名称: {data['name']}")
            print_info(f"状态: {data['status']}")
            return task_id
        else:
            print_error(f"创建任务失败: {response.status_code}")
            print_error(f"响应: {response.text}")
            return None
    except Exception as e:
        print_error(f"请求失败: {e}")
        return None

def test_get_tasks():
    """测试获取任务列表"""
    print_section("4. 获取任务列表")
    try:
        response = requests.get(f"{BASE_URL}/tasks")
        if response.status_code == 200:
            data = response.json()['data']
            print_success(f"获取任务列表成功，共 {len(data)} 个任务")
            for task in data[:3]:  # 只显示前3个
                print_info(f"- {task['name']} ({task['status']}) - 进度: {task['progress']}%")
            return True
        else:
            print_error(f"获取任务列表失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_start_task(task_id: str):
    """测试启动任务"""
    print_section("5. 启动任务")
    try:
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/start")
        if response.status_code == 200:
            print_success(f"任务启动成功")
            return True
        else:
            print_error(f"启动任务失败: {response.status_code}")
            print_error(f"响应: {response.text}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_get_task_status(task_id: str):
    """测试获取任务状态"""
    print_section("6. 监控任务进度")
    print_info("监控10秒，观察任务进度...")
    
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/tasks/{task_id}")
            if response.status_code == 200:
                data = response.json()['data']
                print_info(f"[{i+1}/5] 进度: {data['progress']}% | 已采集: {data['collected']} | 失败: {data['failed']}")
                time.sleep(2)
            else:
                print_error(f"获取任务状态失败: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"请求失败: {e}")
            return False
    
    print_success("任务监控完成")
    return True

def test_get_task_logs(task_id: str):
    """测试获取任务日志"""
    print_section("7. 获取任务日志")
    try:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}/logs")
        if response.status_code == 200:
            logs = response.json()['data']
            print_success(f"获取日志成功，共 {len(logs)} 条")
            for log in logs[-5:]:  # 显示最后5条
                level_color = {
                    'info': Colors.BLUE,
                    'warn': Colors.YELLOW,
                    'error': Colors.RED,
                    'success': Colors.GREEN
                }.get(log['level'], Colors.END)
                print(f"{level_color}[{log['time']}] {log['level'].upper()}: {log['message']}{Colors.END}")
            return True
        else:
            print_error(f"获取日志失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_pause_task(task_id: str):
    """测试暂停任务"""
    print_section("8. 暂停任务")
    try:
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/pause")
        if response.status_code == 200:
            print_success("任务暂停成功")
            return True
        else:
            print_error(f"暂停任务失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_stop_task(task_id: str):
    """测试停止任务"""
    print_section("9. 停止任务")
    try:
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/stop")
        if response.status_code == 200:
            print_success("任务停止成功")
            return True
        else:
            print_error(f"停止任务失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_delete_task(task_id: str):
    """测试删除任务"""
    print_section("10. 删除任务")
    try:
        response = requests.delete(f"{BASE_URL}/tasks/{task_id}")
        if response.status_code == 200:
            print_success("任务删除成功")
            return True
        else:
            print_error(f"删除任务失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def main():
    """主测试流程"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("  数据采集模块 API 测试")
    print(f"{'='*60}{Colors.END}\n")
    
    print_info(f"测试目标: {BASE_URL}")
    print()
    
    # 1. 健康检查
    if not test_health_check():
        print_error("\n❌ 后端服务未启动，测试终止")
        print_warning("请先运行: python backend/app.py")
        return
    
    # 2. 获取统计
    test_get_statistics()
    
    # 3. 获取任务列表
    test_get_tasks()
    
    # 4. 创建任务
    task_id = test_create_task()
    if not task_id:
        print_error("\n❌ 任务创建失败，后续测试跳过")
        return
    
    # 5. 启动任务
    if not test_start_task(task_id):
        print_error("\n❌ 任务启动失败，后续测试跳过")
        return
    
    # 6. 监控任务
    test_get_task_status(task_id)
    
    # 7. 获取日志
    test_get_task_logs(task_id)
    
    # 8. 暂停任务
    test_pause_task(task_id)
    time.sleep(1)
    
    # 9. 停止任务
    test_stop_task(task_id)
    time.sleep(1)
    
    # 10. 删除任务
    test_delete_task(task_id)
    
    # 总结
    print_section("测试完成")
    print_success("所有API测试通过！")
    print_info("数据采集模块运行正常")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}测试被用户中断{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}测试过程中发生错误: {e}{Colors.END}")
