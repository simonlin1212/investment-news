#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""digest.py —— AI 要点层。读 ../data.js,对每个行业调本机 claude 订阅(零key/$0),
生成「今日要点」+ 每条新闻中文标题翻译,写回 data.js。
机制同 SDesign:spawn `claude -p`,--disallowedTools 禁全工具(只处理文本)。纯标准库。
"""
import json, os, re
from concurrent.futures import ThreadPoolExecutor
import llm   # 统一大模型入口(订阅 claude-cli / API 二选一,见 ../llm.config.json)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOPN = 16            # 每行业取最新 N 条做要点+翻译
WORKERS = 3
ATTEMPTS = 3         # 单栏 LLM 失败重试上限(嵌套跑 claude -p 偶发失败,多试几次)
SYS = ("你是中文行业新闻分析助手。给你某行业最近的新闻列表(每条带序号),请做两件事:\n"
       "1) 提炼 3-5 条「今日要点」:聚合最重要的行业动向,每条不超过 40 字,可合并同类、突出数字/公司/趋势,客观陈述。"
       "每条要点用 refs 标注它主要来自哪几条新闻的序号(用于跳转原文,至少 1 个)。\n"
       "2) 给每条新闻一个简洁准确的中文标题翻译;若原文已是中文则原样返回。\n"
       "只输出 JSON,不要任何解释或代码块标记。格式:\n"
       '{"points":[{"t":"要点1","refs":[0,3]},{"t":"要点2","refs":[5]}],"items":[{"i":0,"zh":"中文标题"}]}')

CFG = {"provider": "claude-cli"}   # main 里按 llm.config.json 覆盖

def _llm(user, label=""):
    try:
        return llm.call(SYS, user, CFG)
    except Exception as e:   # 不再静默吞掉:打出原因(超时/空返回/格式异常),便于定位失败栏
        print("  ⚠️ LLM 调用异常 [%s]: %s" % (label, str(e)[:120]))
        return ""

def extract_json(s):
    if not s: return None
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b < 0: return None
    try: return json.loads(s[a:b+1])
    except Exception: return None

def process(ind):
    if ind.get("points"): return ind          # 已有要点则跳过(支持只补失败的栏目)
    items = ind["items"][:TOPN]
    ind["items"] = items                       # 先统一截到 TOPN,失败栏也与成功栏保持一致条数
    if not items:
        ind["points"] = []; return ind
    lines = ["行业:%s" % ind["name"], "新闻:"]
    for i, it in enumerate(items):
        lines.append("%d. %s (%s)" % (i, it["title"], it.get("source","")))
    user = "\n".join(lines)
    d = None
    for _ in range(ATTEMPTS):                   # 偶发失败重试(总计 ATTEMPTS 次)
        d = extract_json(_llm(user, ind["name"]))
        if d: break
    if not d:
        print("  ⚠️ %s 生成失败(已试 %d 次),本栏暂无要点/翻译,重跑可只补本栏" % (ind["name"], ATTEMPTS))
        ind["points"] = []; return ind
    pts = []
    for p in d.get("points", [])[:5]:
        if isinstance(p, dict):
            t = (p.get("t") or "").strip()
            url = ""
            for r in p.get("refs", []):
                if isinstance(r, int) and 0 <= r < len(items) and items[r].get("url"):
                    url = items[r]["url"]; break
            if t: pts.append({"t": t, "url": url})
        elif isinstance(p, str) and p.strip():
            pts.append({"t": p.strip(), "url": ""})
    ind["points"] = pts
    zh = {x.get("i"): x.get("zh","") for x in d.get("items",[]) if isinstance(x, dict)}
    for i, it in enumerate(items):
        it["zh"] = zh.get(i, "")
    return ind                                  # items 已在函数开头截到 TOPN

def main():
    global CFG
    CFG = llm.load_config(ROOT)
    print("大模型 provider:", CFG.get("provider", "claude-cli"))
    p = os.path.join(ROOT, "data.js")
    txt = open(p, encoding="utf-8").read()
    data = json.loads(txt[txt.index("{"):txt.rindex("}")+1])
    inds = data["industries"]
    print("对 %d 个行业生成 AI 要点+翻译(claude 订阅,%d 并发)…" % (len(inds), WORKERS))
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(process, inds))
    data["has_ai"] = True
    with open(p, "w", encoding="utf-8") as f:
        f.write("// data.js —— 含 AI 要点+中文翻译(claude 订阅生成)。\n")
        f.write("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    failed = []
    for ind in inds:
        n = len(ind.get("points",[])); z = sum(1 for it in ind["items"] if it.get("zh"))
        print("  %-16s 要点 %d 条 · 翻译 %d/%d" % (ind["name"], n, z, len(ind["items"])))
        if ind["items"] and not n:             # 有新闻却没要点 = 该栏失败(空栏不算)
            failed.append(ind["name"])
    if failed:
        print("\n⚠️  %d 个栏目生成失败:%s" % (len(failed), "、".join(failed)))
        print("   重跑即可只补失败栏(已成功栏自动跳过):python3 scripts/digest.py")

if __name__ == "__main__":
    main()
