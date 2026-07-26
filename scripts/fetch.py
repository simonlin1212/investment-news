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

def normalize_url(url):
    """Normalize URL for deduplication: strip trailing slash, query string, and fragment."""
    if not url: return ""
    url = url.split("?")[0].split("#")[0].rstrip("/")
    return url.lower()

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
            blob = (d["title"] + " " + d["summary"]).lower()
            if any(k in blob for k in REDLINE): continue
            dt = parse_dt(rawtime)
            if dt is not None:
                if CUTOFF and dt < CUTOFF: continue
                d["time"] = dt.astimezone(BEIJING).strftime("%m-%d %H:%M")
                d["ts"] = int(dt.timestamp())
            else:
                d["time"] = "—"
            out.append(d)
        return out
    except Exception as e:   # 不再静默吞掉:打出失败源名+原因(超时/非法XML/编码)
        print("  ⚠️ 源抓取失败 %s: %s" % (src.get("name","?"), str(e)[:80]))
        return None          # None=出错(区别于 []=成功但近 N 天无新内容)

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
        results = list(ex.map(lambda t: (t[0], t[1].get("name",""), fetch(t[1])), tasks))
    failed_sources = []
    for idx, name, items in results:
        if items is None:          # 该源抓取出错
            failed_sources.append(name); continue
        industries[idx]["items"].extend(items)

    # 每栏按时间倒序(新→旧)，同 URL 只保留第一条(按时间优先)
    for ind in industries:
        seen, unique = set(), []
        for item in sorted(ind["items"], key=lambda x: x.get("ts", 0), reverse=True):
            key = normalize_url(item.get("url", ""))
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        ind["items"] = unique

    data = {"generated_at": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M"),
            "recent_days":days, "industries":industries,
            "stats":{"industries":len(inds),"total_sources":len(cfg["sources"])}}
    with open(os.path.join(ROOT,"data.js"),"w",encoding="utf-8") as f:
        f.write("// data.js —— 含 AI 要点+中文翻译(claude 订阅生成)。\n")
        f.write("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print("最近 %d 天 · 行业 | 源数 | 条数" % days)
    for ind in industries:
        print("  %-16s %3d 源 → %d 条" % (ind["name"], ind["total"], len(ind["items"])))
    print("总源:", len(cfg["sources"]), "· 生成:", data["generated_at"])
    if failed_sources:
        print("⚠️  %d/%d 个源抓取失败:%s%s" % (len(failed_sources), len(cfg["sources"]),
              "、".join(failed_sources[:15]), " …" if len(failed_sources) > 15 else ""))

if __name__ == "__main__":
    main()
