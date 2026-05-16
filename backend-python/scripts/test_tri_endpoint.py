"""Quick test for /api/weibo/rank/tri-dimension endpoint"""
import requests
import json

url = "http://localhost:5000/api/weibo/rank/tri-dimension"
payload = {
    "data": [
        {
            "id": "t1",
            "text": "测试热搜话题正面",
            "interactions": {"reposts": 500, "comments": 300, "likes": 1000},
            "created_at": "2026-05-15T00:00:00"
        },
        {
            "id": "t2",
            "text": "这个话题太差了很糟糕",
            "interactions": {"reposts": 100, "comments": 50, "likes": 200},
            "created_at": "2026-05-14T12:00:00"
        }
    ],
    "sentiment_weight": 0.4,
    "heat_weight": 0.4,
    "timeliness_weight": 0.2
}

r = requests.post(url, json=payload, timeout=15)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:1000])
