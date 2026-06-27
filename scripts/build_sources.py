#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_sources.py —— 策展每行业 tier-1 大媒体清单（高信号），liveness 实测后写 ../sources.json。
纯标准库。
"""
import json, os, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

INDUSTRIES = [
 {"key":"ai","name":"AI / 大模型","accent":"#ff5a1f"},
 {"key":"semi","name":"半导体 / 芯片","accent":"#22d3ee"},
 {"key":"robot","name":"机器人 / 自动化","accent":"#14b8a6"},
 {"key":"auto","name":"汽车 / 新能源车","accent":"#fb7185"},
 {"key":"energy","name":"能源 / 新能源","accent":"#84cc16"},
 {"key":"bio","name":"生物医药 / 健康","accent":"#ec4899"},
 {"key":"space","name":"航天 / 太空","accent":"#8b5cf6"},
 {"key":"security","name":"网络安全","accent":"#ef4444"},
 {"key":"tech","name":"科技 / 互联网","accent":"#3b82f6"},
 {"key":"consumer","name":"消费电子 / 数码","accent":"#a855f7"},
 {"key":"macro","name":"财经 / 宏观","accent":"#eab308"},
 {"key":"science","name":"科学 / 前沿","accent":"#38bdf8"},
]

TIER1 = {
 "ai":[
  ("OpenAI","https://openai.com/news/rss.xml"),("Google Research","https://research.google/blog/rss/"),
  ("Hugging Face","https://huggingface.co/blog/feed.xml"),("量子位","https://www.qbitai.com/feed"),
  ("MIT Tech Review AI","https://www.technologyreview.com/topic/artificial-intelligence/feed"),
  ("The Verge AI","https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
  ("VentureBeat AI","https://venturebeat.com/category/ai/feed/"),
  ("TechCrunch AI","https://techcrunch.com/category/artificial-intelligence/feed/"),
  ("arXiv cs.AI","https://export.arxiv.org/rss/cs.AI"),("KDnuggets","https://www.kdnuggets.com/feed"),
  ("MarkTechPost","https://www.marktechpost.com/feed/"),("BAIR Blog","https://bair.berkeley.edu/blog/feed.xml"),
  ("Import AI","https://importai.substack.com/feed"),("DeepMind","https://deepmind.google/blog/rss.xml"),
  ("智东西","https://zhidx.com/rss"),
  ("机器之心","https://wechat2rss.xlab.app/feed/51e92aad2728acdd1fda7314be32b16639353001.xml"),
  ("新智元","https://wechat2rss.xlab.app/feed/ede30346413ea70dbef5d485ea5cbb95cca446e7.xml"),
 ],
 "semi":[
  ("DIGITIMES","https://www.digitimes.com/rss/daily.xml"),("SemiAnalysis","https://semianalysis.substack.com/feed"),
  ("Semiconductor Engineering","https://semiengineering.com/feed/"),("EE Times","https://www.eetimes.com/feed/"),
  ("IEEE Spectrum 半导体","https://spectrum.ieee.org/feeds/topic/semiconductors.rss"),
  ("SemiWiki","https://semiwiki.com/feed/"),
  ("Semiconductor Today","https://www.semiconductor-today.com/rss/news.xml"),
  ("Electronics Weekly","https://www.electronicsweekly.com/feed/"),
  ("All About Circuits","https://www.allaboutcircuits.com/rss/news/"),
 ],
 "robot":[
  ("The Robot Report","https://www.therobotreport.com/feed/"),
  ("IEEE Spectrum 机器人","https://spectrum.ieee.org/feeds/topic/robotics.rss"),
  ("Robohub","https://robohub.org/feed/"),("Robotics & Automation","https://roboticsandautomationnews.com/feed/"),
  ("Robotics Business Review","https://www.roboticsbusinessreview.com/feed/"),
  ("Automation World","https://www.automationworld.com/rss.xml"),
  ("Unite.AI","https://www.unite.ai/feed/"),
 ],
 "auto":[
  ("Electrek","https://electrek.co/feed/"),("InsideEVs","https://insideevs.com/rss/articles/all/"),
  ("Green Car Reports","https://www.greencarreports.com/rss.xml"),
  ("The Verge Transport","https://www.theverge.com/rss/transportation/index.xml"),
  ("TechCrunch Transport","https://techcrunch.com/category/transportation/feed/"),
  ("Automotive News","https://www.autonews.com/rss"),("CnEVPost","https://cnevpost.com/feed/"),
  ("Autoblog","https://www.autoblog.com/rss.xml"),
 ],
 "energy":[
  ("CleanTechnica","https://cleantechnica.com/feed/"),("Utility Dive","https://www.utilitydive.com/feeds/news/"),
  ("pv magazine","https://www.pv-magazine.com/feed/"),("Energy Storage News","https://www.energy-storage.news/feed/"),
  ("OilPrice","https://oilprice.com/rss/main"),("Canary Media","https://www.canarymedia.com/articles.rss"),
  ("PV Tech","https://www.pv-tech.org/feed/"),("EIA","https://www.eia.gov/rss/press_room.xml"),
  ("Renewable Energy World","https://www.renewableenergyworld.com/feed/"),
  ("国际能源网","https://www.in-en.com/feed/rss.php?mid=21"),
 ],
 "bio":[
  ("STAT News","https://www.statnews.com/feed/"),("Endpoints News","https://endpts.com/feed/"),
  ("FierceBiotech","https://www.fiercebiotech.com/rss/xml"),("FiercePharma","https://www.fiercepharma.com/rss/xml"),
  ("BioPharma Dive","https://www.biopharmadive.com/feeds/news/"),("MedCity News","https://medcitynews.com/feed/"),
  ("GEN","https://www.genengnews.com/feed/"),("Nature Biotech","https://www.nature.com/nbt.rss"),
  ("Pharma Technology","https://www.pharmaceutical-technology.com/feed/"),
 ],
 "space":[
  ("SpaceNews","https://spacenews.com/feed/"),("Space.com","https://www.space.com/feeds/all"),
  ("Ars Technica Space","https://feeds.arstechnica.com/arstechnica/space"),
  ("Spaceflight Now","https://spaceflightnow.com/feed/"),("Payload","https://payloadspace.com/feed/"),
  ("NASA","https://www.nasa.gov/news-release/feed/"),("NASASpaceflight","https://www.nasaspaceflight.com/feed/"),
 ],
 "security":[
  ("Krebs on Security","https://krebsonsecurity.com/feed/"),("The Hacker News","https://feeds.feedburner.com/TheHackersNews"),
  ("BleepingComputer","https://www.bleepingcomputer.com/feed/"),("Dark Reading","https://www.darkreading.com/rss.xml"),
  ("SecurityWeek","https://www.securityweek.com/feed/"),("The Record","https://therecord.media/feed/"),
  ("Ars Technica Security","https://feeds.arstechnica.com/arstechnica/security"),
 ],
 "tech":[
  ("TechCrunch","https://techcrunch.com/feed/"),("The Verge","https://www.theverge.com/rss/index.xml"),
  ("Ars Technica","https://feeds.arstechnica.com/arstechnica/index"),("Hacker News","https://hnrss.org/frontpage"),
  ("WIRED","https://www.wired.com/feed/rss"),("Engadget","https://www.engadget.com/rss.xml"),
  ("Techmeme","https://www.techmeme.com/feed.xml"),("36氪","https://36kr.com/feed"),
  ("钛媒体","https://www.tmtpost.com/rss.xml"),("少数派","https://sspai.com/feed"),
  ("IT之家","https://www.ithome.com/rss/"),("GitHub Blog","https://github.blog/feed/"),
  ("Stratechery","https://stratechery.com/feed/"),
  ("虎嗅","https://rss.huxiu.com/"),("动点科技","https://cn.technode.com/feed/"),
  ("月光博客","https://www.williamlong.info/rss.xml"),("Solidot","https://www.solidot.org/index.rss"),
  ("白鲸出海","https://www.baijingapp.com/feed"),
 ],
 "consumer":[
  ("Engadget","https://www.engadget.com/rss.xml"),
  ("9to5Mac","https://9to5mac.com/feed/"),("9to5Google","https://9to5google.com/feed/"),
  ("GSMArena","https://www.gsmarena.com/rss-news-reviews.php3"),("Android Authority","https://www.androidauthority.com/feed/"),
  ("DPReview","https://www.dpreview.com/feeds/news.xml"),("少数派","https://sspai.com/feed"),
 ],
 "macro":[
  ("CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html"),("Financial Times","https://www.ft.com/rss/home"),
  ("WSJ Markets","https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),("MarketWatch","https://feeds.marketwatch.com/marketwatch/topstories/"),
  ("Yahoo Finance","https://finance.yahoo.com/news/rssindex"),("华尔街见闻","https://dedicated.wallstreetcn.com/rss.xml"),
  ("Finextra","https://www.finextra.com/rss/headlines.aspx"),("SEC","https://www.sec.gov/news/pressreleases.rss"),
  ("Federal Reserve","https://www.federalreserve.gov/feeds/press_all.xml"),("Seeking Alpha","https://seekingalpha.com/market_currents.xml"),
  ("东方财富股票","http://rss.eastmoney.com/rss_stock.xml"),("东方财富资讯","http://rss.eastmoney.com/rss_partener.xml"),
  ("经济观察网","http://www.eeo.com.cn/rss.xml"),
 ],
 "science":[
  ("Nature News","https://www.nature.com/nature.rss"),("ScienceDaily","https://www.sciencedaily.com/rss/all.xml"),
  ("Quanta Magazine","https://api.quantamagazine.org/feed/"),("New Scientist","https://www.newscientist.com/feed/home/"),
  ("Scientific American","https://www.scientificamerican.com/feed/"),
  ("Live Science","https://www.livescience.com/feeds/all"),("MIT News","https://news.mit.edu/rss/research"),
  ("Science News","https://www.sciencenews.org/feed"),
  ("Ars Technica Science","https://feeds.arstechnica.com/arstechnica/science"),
 ],
}

def local(tag): return tag.split("}")[-1]
def liveness(item):
    key,name,url = item
    for attempt in range(3):                 # 重试，避免好源因瞬时超时被误删
        try:
            req = urllib.request.Request(url, headers={"User-Agent":UA,
                  "Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"})
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()               # 读完整，避免大 feed 被截断导致 XML 解析失败
            root = ET.fromstring(raw)
            n = sum(1 for e in root.iter() if local(e.tag) in ("item","entry"))
            return (key,name,url, n>=1)
        except Exception:
            if attempt < 2: time.sleep(1.5); continue
            return (key,name,url, False)

def main():
    tasks=[]
    for key, lst in TIER1.items():
        for name,url in lst: tasks.append((key,name,url))
    with ThreadPoolExecutor(max_workers=30) as ex:
        res = list(ex.map(liveness, tasks))
    sources, dead = [], []
    for key,name,url,ok in res:
        (sources if ok else dead).append({"key":key,"name":name,"url":url})
    out_sources = [{"name":s["name"],"hint":s["key"],"type":"rss","url":s["url"]} for s in sources]
    # 红线只滤"真正不能碰的"(赌博/预测市场/加密/色情)。时政/地缘/关税照收(本工具=新闻源,非抖音口播)
    RED=["赌博","博彩","赌场","彩票","下注","押注","预测市场","polymarket","kalshi","prediction market",
         "加密货币","虚拟货币","比特币","以太坊","稳定币","crypto","bitcoin","ethereum","stablecoin",
         "gambling","betting","casino","lottery","sportsbook","色情","porn"]
    out={"_comment":"tier-1 策展源(每行业公认大媒体,高信号,纯RSS)。",
         "fetch":{"per_source":6,"timeout":15,"recent_days":7},"industries":INDUSTRIES,
         "sources":out_sources,"redline_keywords":RED}
    json.dump(out, open(os.path.join(ROOT,"sources.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    by=Counter(s["hint"] for s in out_sources)
    print("✅ tier-1 活源 %d / 候选 %d" % (len(out_sources), len(tasks)))
    for ind in INDUSTRIES:
        print("  %-16s %d" % (ind["name"], by.get(ind["key"],0)))
    if dead:
        print("\n失效(剔除):", ", ".join(d["name"] for d in dead))

if __name__=="__main__":
    main()
