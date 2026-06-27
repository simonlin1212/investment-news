---
name: investment-news
description: 本地「投资资讯看板」。从 100+ 源抓 12 大赛道新闻,用用户自己的大模型(Claude 订阅或 API)提炼中文「今日要点」+翻译,浏览器看板呈现。当用户想搭建/启动/更新投资资讯看板、或想看某赛道近期动向时使用。纯 Python 标准库,零 key,数据不出本机。
---

# Investment News —— 本地投资资讯看板

一个自包含工具:`fetch.py` 抓源 → `digest.py` 用**用户自己的大模型**出「今日要点」+翻译 → `index.html` 看板呈现,`server.py` 提供刷新接口。

## 给 Agent 的操作指南

> **🔑 核心:这个工具的产物是一个【浏览器看板】(http://localhost:8793),不是终端输出、也不是 `data.js` 文件。**
> 用户想"看资讯 / 看某赛道 / 更新看板"时,你的**最终动作必须是 `open http://localhost:8793` 把网页打开,并明确告诉用户"看板在浏览器里,去看"**。
> ❌ 不要在终端里罗列/粘贴新闻内容(那不是这个工具的用法);❌ 不要跑完 fetch/digest 生成完 `data.js` 就当任务结束。**没把用户导向那个网页 = 没完成。** 看板里的「AI 今日要点 + 中文翻译 + 分赛道 + 跳转原文」才是价值所在,终端给不了。

### 1. 第一次用(setup)——必须先问用户用哪种大模型
打开 `llm.config.json`,两种 provider 二选一,**主动问使用者**:
- **`claude-cli`(默认,推荐)**：用本机 Claude Code 订阅,**$0、零 key**。前提:本机装了 Claude Code 且 `claude login` 过。仅本机可用。
- **`api`**：用 OpenAI 兼容 API key(DeepSeek/OpenAI/硅基/OpenRouter…),任意机器可用,按量付费。需在 `llm.config.json` 的 `api.api_key` 填 key。

确认后写进 `llm.config.json`。

### 2. 启动看板,并把网页打开(关键,别漏)
```bash
python3 server.py            # 默认端口 8793,保持运行
open http://localhost:8793   # 必做:把看板在浏览器打开(Win 用 start、Linux 用 xdg-open)
```
启动后**一定要把 `http://localhost:8793` 在浏览器打开**,并对用户说一句:
「投资资讯看板已在浏览器打开(http://localhost:8793)——左边 12 个赛道随便点,每栏顶部是 AI 今日要点,点 ↗ 跳原文,左上角 ⟳ 可刷新。」

### 3. 更新数据(两种方式等价)
- **看板里点左上角 ⟳ 刷新**(后端会跑 fetch+digest,转圈等它)
- **或命令行**：`python3 scripts/fetch.py && python3 scripts/digest.py`
  - `fetch.py`：抓 `sources.json` 全部源 → `data.js`(带红线过滤 + 最近 N 天)
  - `digest.py`：用 `llm.config.json` 配的模型,给每个赛道出 3–5 条中文要点 + 翻译每条标题 → 写回 `data.js`

### 4. 加源 / 调参
- 加源:`sources.json` 的 `sources` 里加一行 `{ "name","hint"(赛道key),"type":"rss","url" }`。
- 只看最近几天:改 `sources.json` 的 `fetch.recent_days`(默认 7)。
- 红线词:`sources.json` 的 `redline_keywords`(默认滤赌博/预测市场/加密/色情;时政/财经照收)。

## 注意
- **纯 Python 标准库,不用 pip 装任何东西。**
- `claude-cli` 模式下 `digest` 会 spawn 本机 `claude -p`(订阅鉴权,`--disallowedTools` 全禁,只让它处理文本),**只能在用户本机跑**。
- 个别批次若被订阅模型安全策略拒答(如某些医疗内容),该赛道会优雅降级(只显示新闻列表,无要点);换 `api` 模式可避免。
- **本工具仅为资讯聚合,不构成投资建议。**
