"""Test /api/pipeline endpoints"""
import requests, json

BASE = "http://localhost:5000/api/pipeline"

# 1. Health
r = requests.get(f"{BASE}/health", timeout=10)
print(f"Health: {r.status_code} -> {r.json()}")

# 2. Stats
r = requests.get(f"{BASE}/stats", timeout=10)
print(f"\nStats: {r.status_code}")
if r.status_code == 200:
    d = r.json().get("data", {})
    print(json.dumps(d, ensure_ascii=False, indent=2)[:600])

# 3. Status
r = requests.get(f"{BASE}/status", timeout=10)
print(f"\nStatus: {r.status_code}")
if r.status_code == 200:
    print(json.dumps(r.json().get("data", {}), ensure_ascii=False, indent=2)[:400])

# 4. Ranking
r = requests.get(f"{BASE}/ranking?limit=5", timeout=10)
print(f"\nRanking: {r.status_code}")
if r.status_code == 200:
    items = r.json().get("data", {}).get("items", [])
    print(f"  Items: {len(items)}")
    for item in items[:3]:
        print(f"  #{item.get('ranking_position')} score={item.get('composite_score')} content={str(item.get('content',''))[:40]}")

# 5. History
r = requests.get(f"{BASE}/history?limit=5", timeout=10)
print(f"\nHistory: {r.status_code}")
if r.status_code == 200:
    data = r.json().get("data", [])
    print(f"  Records: {len(data)}")
    for h in data[:3]:
        print(f"  batch={h.get('batch_id','')[:30]} status={h.get('status')} weibos={h.get('total_weibos')}")
