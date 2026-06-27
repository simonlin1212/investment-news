#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch.py —— 抓 sources.json 里各行业全部源的真实数据,带"最近 N 天"过滤,
时间规整为北京时间"MM-DD HH:MM",每栏按时间倒序,写 ../data.js。纯标准库,零依赖。
"""
import json, os, re, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PER = 5
CUTOFF = None
REDLINE = []
BEIJING = timezone(timedelta(hours=8))

def strip_html(s): return re.sub(r"\s+"," ", re.sub(r"<[^>]+>","", s or "")).strip()
def local(tag): return tag.split("}")[-1]

def parse_dt(s):
    if not s: return None
    try:
        dt = parsedate_to_datetime(s)
    except Exception:
        try: dt = datetime.fromisoformat(s.strip().replace("Z","+00:00"))
        except Exception: return None
    if dt is None: return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt

def fetch(src):
    try:
        req = urllib.request.Request(src["url"], headers={"User-Agent":UA,
              "Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"})
        with urllib.request.urlopen(req, timeout=14) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        out = []
        for n in [e for e in root.iter() if local(e.tag) in ("item","entry")]:
            if len(out) >= PER: break
            d = {"title":"","url":"","time":"","ts":0,"summary":"","source":src["name"]}
            rawtime = ""
            for c in n:
                t = local(c.tag)
                if t=="title" and not d["title"]: d["title"]=(c.text or "").strip()
                elif t=="link" and not d["url"]: d["url"]=c.get("href") or (c.text or "").strip()
                elif t in ("pubDate","published","updated","date") and not rawtime: rawtime=(c.text or "").strip()
                elif t in ("description","summary","content") and not d["summary"]: d["summary"]=strip_html(c.text or "")[:160]
            if not d["title"]: continue
            blob = (d["title"] + " " + d["summary"]).lower()   # 红线过滤(赌博/加密/预测市场)
            if any(k in blob for k in REDLINE): continue
            dt = parse_dt(rawtime)
            if dt is not None:
                if CUTOFF and dt < CUTOFF: continue          # 旧文剔除
                d["time"] = dt.astimezone(BEIJING).strftime("%m-%d %H:%M")
                d["ts"] = int(dt.timestamp())
            else:
                d["time"] = "—"
            out.append(d)
        return out
    except Exception:
        return []

def main():
    global CUTOFF, REDLINE
    cfg = json.load(open(os.path.join(ROOT,"sources.json"), encoding="utf-8"))
    days = cfg.get("fetch",{}).get("recent_days", 120)
    CUTOFF = datetime.now(timezone.utc) - timedelta(days=days)
    REDLINE = [k.lower() for k in cfg.get("redline_keywords", [])]
    inds = cfg["industries"]
    byhint = {}
    for s in cfg["sources"]:
        byhint.setdefault(s["hint"], []).append(s)

    industries, tasks = [], []
    for i, ind in enumerate(inds):
        pool = byhint.get(ind["key"], [])
        industries.append({"key":ind["key"],"name":ind["name"],"accent":ind["accent"],
                           "total":len(pool),"items":[]})
        for s in pool: tasks.append((i, s))

    with ThreadPoolExecutor(max_workers=40) as ex:
        results = list(ex.map(lambda t: (t[0], fetch(t[1])), tasks))
    for idx, items in results:
        industries[idx]["items"].extend(items)
    # 每栏按时间倒序(新→旧)
    for ind in industries:
        ind["items"].sort(key=lambda x: x.get("ts",0), reverse=True)

    data = {"generated_at": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M"),
            "recent_days":days, "industries":industries,
            "stats":{"industries":len(inds),"total_sources":len(cfg["sources"])}}
    with open(os.path.join(ROOT,"data.js"),"w",encoding="utf-8") as f:
        f.write("// data.js —— 各行业源真实数据(最近%d天,北京时间,新→旧)。fetch.py 抓取 → digest.py 补 AI 要点+翻译。\n"%days)
        f.write("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print("最近 %d 天 · 行业 | 源数 | 条数" % days)
    for ind in industries:
        print("  %-16s %3d 源 → %d 条" % (ind["name"], ind["total"], len(ind["items"])))
    print("总源:", len(cfg["sources"]), "· 生成:", data["generated_at"])

if __name__ == "__main__":
    main()
