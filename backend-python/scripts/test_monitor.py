"""Test /api/monitor/statistics endpoint"""
import requests, json

r = requests.get("http://localhost:5000/api/monitor/statistics", timeout=15)
d = r.json()
data = d["data"]

print(f"Status: {r.status_code}")
print(f"Alert: {data['alert']['level']} - {data['alert']['message']}")

sd = data["sentiment_distribution"]
print(f"Distribution: positive={sd['positive']} neutral={sd['neutral']} negative={sd['negative']} total={sd['total']}")

kw = data["keyword_ranking"]
print(f"Keywords: {len(kw)} items")
for k in kw[:5]:
    print(f"  {k['keyword']}: {k['count']}")

print(f"Alert history: {len(data['alert_history'])} records")
for a in data["alert_history"][:3]:
    print(f"  [{a.get('level','')}] {a.get('message','')[:60]}")

ss = data["system_status"]
print(f"Spark jobs: {ss['spark_jobs']}")
print(f"Crawler tasks: {ss['crawler_tasks']}")
