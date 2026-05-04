"""
第7章 系统测试 - 自动化测试脚本
==========================================
按照论文章节结构依次执行功能测试和性能测试，
输出格式化的测试报告。
"""
import sys, os, json, time, requests, statistics
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:5000"
JAVA_BASE = "http://127.0.0.1:8081"
FRONTEND = "http://127.0.0.1:3001"
DIVIDER = "=" * 70
DELAY = 0.3          # 请求间隔 (秒)
RETRY_MAX = 3

# 带重试的 requests session
session = requests.Session()
_retry = Retry(total=RETRY_MAX, backoff_factor=1,
               status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=_retry))

def section(title):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)

def check(name, ok, detail=""):
    tag = "通过 ✓" if ok else "未通过 ✗"
    print(f"  [{tag}] {name}")
    if detail:
        print(f"         {detail}")
    return ok

def timed_request(method, url, **kwargs):
    """发送请求并返回 (response, elapsed_ms), 自动重试"""
    kwargs.setdefault('timeout', 30)
    for attempt in range(RETRY_MAX):
        try:
            start = time.perf_counter()
            r = method(url, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            return r, elapsed
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < RETRY_MAX - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise

def pause():
    time.sleep(DELAY)

# ============================================================
#  7.2.1 数据采集功能测试
# ============================================================
def test_7_2_1():
    section("7.2.1 数据采集功能测试")
    results = []

    # 测试1: 创建采集任务
    try:
        r, ms = timed_request(session.post, f"{BASE}/api/weibo/crawl/start", json={
            "keyword": "人工智能",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "max_count": 100
        })
        ok = r.status_code == 200 and r.json().get("code") == 200
        results.append(check("创建采集任务（关键词‘人工智能’）", ok,
                             f"状态码={r.status_code}, 响应={r.json().get('message','')}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("创建采集任务", False, str(e)))
    pause()

    # 测试2: 查看采集任务列表
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/weibo/crawl/tasks")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        raw = data.get("data", {})
        task_count = len(raw.get("tasks", [])) if isinstance(raw, dict) else len(raw) if isinstance(raw, list) else 0
        results.append(check("查看采集任务列表", ok,
                             f"任务数={task_count}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("查看采集任务列表", False, str(e)))
    pause()

    # 测试3: 微博搜索功能
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/weibo/search",
                              params={"keyword": "人工智能", "count": 10})
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        raw = data.get("data", {})
        count = len(raw.get("weibos", [])) if isinstance(raw, dict) else len(raw) if isinstance(raw, list) else 0
        results.append(check("微博搜索功能", ok,
                             f"返回{count}条微博, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("微博搜索功能", False, str(e)))
    pause()

    # 测试4: 热搜榜获取
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/weibo/hotsearch")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        raw = data.get("data", [])
        count = len(raw) if isinstance(raw, list) else len(raw.get("items", [])) if isinstance(raw, dict) else 0
        results.append(check("热搜榜数据获取", ok,
                             f"热搜条数={count}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("热搜榜数据获取", False, str(e)))
    pause()

    passed = sum(1 for r in results if r)
    print(f"\n  数据采集功能测试: {passed}/{len(results)} 通过")
    return results

# ============================================================
#  7.2.2 情感分析功能测试
# ============================================================
def test_7_2_2():
    section("7.2.2 情感分析功能测试")
    results = []

    # 测试样本：覆盖正面、负面、中性
    test_samples = [
        ("今天天气真好，心情特别愉快！", "positive"),
        ("这个产品质量非常棒，强烈推荐！", "positive"),
        ("科技创新为我们的生活带来了便利", "positive"),
        ("这部电影太精彩了，演员演技炸裂", "positive"),
        ("春暖花开，万物复苏，美好的一天", "positive"),
        ("服务态度太差了，再也不来了", "negative"),
        ("交通堵塞严重，迟到了整整一小时", "negative"),
        ("食品安全问题令人担忧", "negative"),
        ("这次考试又没考好，好沮丧", "negative"),
        ("环境污染越来越严重了", "negative"),
        ("今天是星期三", "neutral"),
        ("会议定在下午两点召开", "neutral"),
        ("北京今日气温15度", "neutral"),
        ("新闻发布会已经结束", "neutral"),
        ("学校明天放假一天", "neutral"),
    ]

    # 测试1: 单文本情感分析API
    try:
        r, ms = timed_request(session.post, f"{BASE}/api/v2/sentiment/analyze",
                              json={"text": "今天天气真好，心情特别愉快！"})
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        sentiment = data.get("data", {}).get("sentiment", "")
        confidence = data.get("data", {}).get("confidence", 0)
        method = data.get("data", {}).get("fusion_method", "N/A")
        results.append(check("单文本情感分析API可用", ok,
                             f"情感={sentiment}, 置信度={confidence:.3f}, 方法={method}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("单文本情感分析API可用", False, str(e)))
    pause()

    # 测试2: 批量情感分析准确率
    correct = 0
    total = len(test_samples)
    errors_detail = []
    latencies = []
    method_stats = {}

    for text, expected in test_samples:
        try:
            r, ms = timed_request(session.post, f"{BASE}/api/v2/sentiment/analyze",
                                  json={"text": text})
            latencies.append(ms)
            data = r.json()
            if data.get("code") == 200:
                result_data = data.get("data", {})
                predicted = result_data.get("sentiment", "")
                confidence = result_data.get("confidence", 0)
                method = result_data.get("fusion_method", "unknown")
                score = result_data.get("score", 0)
                label = result_data.get("label", "")
                method_stats[method] = method_stats.get(method, 0) + 1
                if predicted == expected:
                    correct += 1
                else:
                    errors_detail.append(
                        f"    文本: {text[:20]}...  预期={expected}  实际={predicted}  "
                        f"置信度={confidence:.2f}  得分={score:.4f}  标签={label}  方法={method}")
            pause()
        except Exception as e:
            errors_detail.append(f"    文本: {text[:20]}... 错误={e}")
            time.sleep(3)

    accuracy = correct / total * 100 if total > 0 else 0
    avg_latency = statistics.mean(latencies) if latencies else 0

    results.append(check(f"批量情感分析准确率 ({correct}/{total})", accuracy >= 60,
                         f"准确率={accuracy:.1f}%, 平均耗时={avg_latency:.0f}ms"))

    if errors_detail:
        print(f"  误判详情:")
        for e in errors_detail:
            print(e)

    # 方法统计
    print(f"  分析方法统计: {json.dumps(method_stats, ensure_ascii=False)}")

    passed = sum(1 for r in results if r)
    print(f"\n  情感分析功能测试: {passed}/{len(results)} 通过")
    return results

# ============================================================
#  7.2.3 数据展示功能测试
# ============================================================
def test_7_2_3():
    section("7.2.3 数据展示功能测试")
    results = []

    # 测试1: 前端页面可访问
    try:
        r, ms = timed_request(session.get, FRONTEND)
        ok = r.status_code == 200
        results.append(check("前端首页可访问", ok, f"状态码={r.status_code}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("前端首页可访问", False, str(e)))
    pause()

    # 测试2: 情感分布数据API
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/v2/sentiment/distribution")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        dist = data.get("data", {}).get("distribution", {})
        pct = data.get("data", {}).get("percentage", {})
        results.append(check("情感分布数据接口", ok,
                             f"正面={pct.get('positive',0):.1f}% 负面={pct.get('negative',0):.1f}% 中性={pct.get('neutral',0):.1f}% 总数={dist.get('total',0)}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("情感分布数据接口", False, str(e)))
    pause()

    # 测试3: 统计概览API
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/v2/stats/overview")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        overview = data.get("data", {})
        results.append(check("统计概览数据接口", ok,
                             f"微博总数={overview.get('total_weibo',0)}, 用户数={overview.get('total_users',0)}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("统计概览数据接口", False, str(e)))
    pause()

    # 测试4: 趋势数据API
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/v2/stats/trend")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        trend = data.get("data", [])
        days = len(trend) if isinstance(trend, list) else 0
        results.append(check("情感趋势数据接口", ok,
                             f"返回{days}天数据, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("情感趋势数据接口", False, str(e)))
    pause()

    # 测试5: 三维度排序API
    try:
        r, ms = timed_request(session.post, f"{BASE}/api/v2/ranking/tri-dimension",
                              json={"texts": ["人工智能发展迅速", "今天心情不好"]})
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        results.append(check("三维度排序接口", ok,
                             f"耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("三维度排序接口", False, str(e)))
    pause()

    # 测试6: 健康检查
    try:
        r, ms = timed_request(session.get, f"{BASE}/api/v2/health")
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        results.append(check("系统健康检查接口", ok,
                             f"version={data.get('version','')}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("系统健康检查接口", False, str(e)))

    passed = sum(1 for r in results if r)
    print(f"\n  数据展示功能测试: {passed}/{len(results)} 通过")
    return results

# ============================================================
#  7.3.1 数据处理效率测试
# ============================================================
def test_7_3_1():
    section("7.3.1 数据处理效率测试")
    results = []

    batch_texts = [
        "人工智能正在改变世界，未来可期",
        "今天股市大跌，投资者损失惨重",
        "新能源汽车销量创新高",
        "食品安全问题引发社会关注",
        "科技公司发布新一代芯片",
        "环保政策推动绿色发展",
        "教育改革深入推进",
        "医疗技术取得重大突破",
        "网络安全形势日益严峻",
        "文化产业蓬勃发展",
    ]

    # 测试1: 10条文本逐条分析耗时
    latencies = []
    for text in batch_texts:
        try:
            _, ms = timed_request(session.post, f"{BASE}/api/v2/sentiment/analyze",
                                  json={"text": text})
            latencies.append(ms)
            pause()
        except:
            pass

    if latencies:
        avg = statistics.mean(latencies)
        p50 = sorted(latencies)[len(latencies)//2]
        p95 = sorted(latencies)[int(len(latencies)*0.95)]
        total_sec = sum(latencies) / 1000
        results.append(check(f"情感分析 {len(latencies)} 条微博", True,
                             f"总耗时={total_sec:.1f}s, 平均={avg:.0f}ms, P50={p50:.0f}ms, P95={p95:.0f}ms"))
    else:
        results.append(check("情感分析", False, "无有效结果"))

    # 测试2: 轻量级 API 响应时间基准
    endpoints = [
        ("GET", f"{BASE}/api/v2/health", "健康检查"),
        ("GET", f"{BASE}/api/v2/stats/overview", "统计概览"),
        ("GET", f"{BASE}/api/v2/sentiment/distribution", "情感分布"),
    ]

    for method, url, name in endpoints:
        times = []
        for _ in range(3):
            try:
                _, ms = timed_request(session.get, url)
                times.append(ms)
                pause()
            except:
                pass
        if times:
            avg = statistics.mean(times)
            results.append(check(f"{name} 响应时间", avg < 3000,
                                 f"平均={avg:.0f}ms (3次请求)"))

    passed = sum(1 for r in results if r)
    print(f"\n  数据处理效率测试: {passed}/{len(results)} 通过")
    return results

# ============================================================
#  7.3.2 系统稳定性测试
# ============================================================
def test_7_3_2():
    section("7.3.2 系统稳定性测试")
    results = []

    # 测试1: 服务存活性
    services = [
        ("Flask API", f"{BASE}/"),
        ("Frontend", FRONTEND),
    ]
    for name, url in services:
        try:
            r, ms = timed_request(session.get, url)
            results.append(check(f"{name} 服务存活", r.status_code == 200,
                                 f"状态码={r.status_code}, 耗时={ms:.0f}ms"))
        except Exception as e:
            results.append(check(f"{name} 服务存活", False, str(e)))
        pause()

    # 测试2: Java后端
    try:
        r, ms = timed_request(session.get, f"{JAVA_BASE}/api/actuator/health")
        ok = r.status_code == 200
        results.append(check("Java API 服务存活", ok, f"状态码={r.status_code}, 耗时={ms:.0f}ms"))
    except Exception as e:
        results.append(check("Java API 服务存活", False, str(e)))
    pause()

    # 测试3: 模型加载状态
    try:
        r = session.get(f"{BASE}/api/models/status", timeout=15)
        data = r.json()
        ok = r.status_code == 200 and data.get("code") == 200
        model_data = data.get("data", {})
        loaded = [k for k, v in model_data.items() if isinstance(v, dict) and v.get("status") == "loaded"]
        results.append(check("模型加载状态", ok,
                             f"已加载: {', '.join(loaded) if loaded else '无'}, 全部模型: {list(model_data.keys())}"))
    except Exception as e:
        results.append(check("模型加载状态", False, str(e)))
    pause()

    # 测试4: 连续100次混合接口请求稳定性（间隔0.2s）
    mixed_urls = [
        f"{BASE}/api/v2/health",
        f"{BASE}/",
        f"{BASE}/api/v2/stats/overview",
        f"{BASE}/api/v2/stats/trend",
        f"{BASE}/api/v2/sentiment/distribution",
    ]
    total_req = 100
    success = 0
    err_count = 0
    resp_times = []
    for i in range(total_req):
        url = mixed_urls[i % len(mixed_urls)]
        try:
            t0 = time.perf_counter()
            r = session.get(url, timeout=10)
            elapsed = (time.perf_counter() - t0) * 1000
            resp_times.append(elapsed)
            if r.status_code == 200:
                success += 1
            else:
                err_count += 1
        except:
            err_count += 1
        time.sleep(0.2)

    rate = success / total_req * 100
    avg_rt = statistics.mean(resp_times) if resp_times else 0
    max_rt = max(resp_times) if resp_times else 0
    results.append(check(f"连续{total_req}次混合请求成功率", rate >= 95,
                         f"成功率={rate:.1f}% ({success}/{total_req}), 失败={err_count}次, 平均={avg_rt:.0f}ms, 最大={max_rt:.0f}ms"))

    passed = sum(1 for r in results if r)
    print(f"\n  系统稳定性测试: {passed}/{len(results)} 通过")
    return results


# ============================================================
#  主函数
# ============================================================
if __name__ == "__main__":
    print(DIVIDER)
    print("  第7章 系统测试 - 自动化测试报告")
    print(f"  测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试环境: Flask={BASE}, Java={JAVA_BASE}, Frontend={FRONTEND}")
    print(DIVIDER)

    # 环境版本检测
    section("测试环境信息")
    import platform
    print(f"  操作系统: {platform.system()} {platform.version()}")
    print(f"  Python: {platform.python_version()}")
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        print(f"  CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA版本: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("  PyTorch: 未安装")
    try:
        import transformers
        print(f"  Transformers: {transformers.__version__}")
    except ImportError:
        print("  Transformers: 未安装")
    try:
        import flask
        print(f"  Flask: {flask.__version__}")
    except ImportError:
        pass
    try:
        import pyspark
        print(f"  PySpark: {pyspark.__version__}")
    except ImportError:
        pass

    all_results = []

    # 7.2 功能测试
    all_results.extend(test_7_2_1())
    all_results.extend(test_7_2_2())
    all_results.extend(test_7_2_3())

    # 7.3 性能测试
    all_results.extend(test_7_3_1())
    all_results.extend(test_7_3_2())

    # 汇总
    total = len(all_results)
    passed = sum(1 for r in all_results if r)
    failed = total - passed

    section("测试汇总")
    print(f"  总测试项: {total}")
    print(f"  通过:     {passed}")
    print(f"  未通过:   {failed}")
    print(f"  通过率:   {passed/total*100:.1f}%")
    print(DIVIDER)
