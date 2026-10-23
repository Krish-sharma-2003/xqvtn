import json, collections, datetime as dt

A = json.load(open("data/actuals.json"))
F = json.load(open("data/forecasts.json"))
p = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

print("actual rows:", len(A), "| unique startTime:", len({r["startTime"] for r in A}))
print("actual range:", A[0]["startTime"], "->", A[-1]["startTime"])
print("forecast rows:", len(F))
pubs = sorted({r["publishTime"] for r in F})
print("unique publishTimes:", len(pubs), "| first:", pubs[0], "| last:", pubs[-1])
per_day = collections.Counter(x[:10] for x in pubs)
print("publishes per day min/max:", min(per_day.values()), max(per_day.values()))
h = [(p(r["startTime"]) - p(r["publishTime"])).total_seconds() / 3600 for r in F]
print("horizon hours min/max:", round(min(h), 1), round(max(h), 1))
print("negative-horizon rows:", sum(x < 0 for x in h))
print("null/negative generation:", sum(r["generation"] is None or r["generation"] < 0 for r in A + F))