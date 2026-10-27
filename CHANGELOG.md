# Changelog

## 1.0.4

说明文档更正 —— 程序没有改动，README 和 SKILL.md 的说法改得更准确。

- **写清楚数据去向**：抓取和看板都在本机运行；生成「今日要点」时，程序会把新闻
  标题（附来源和赛道名）发给你选的模型——默认 Claude Code，或你配置的 API
  服务商。新闻库、报告和配置都存在本机。原来写的「数据全程留存本机」不准确，
  README 和 SKILL.md 描述都已改正。
  *docs: state plainly that headlines (with source and sector) are sent to your
  chosen model when generating key points; the news store, reports and config
  stay on your machine.*
- **源数量更正为 106**，和 `sources.json` 实际一致（原来写 108）。
  *docs: source count corrected to 106, matching sources.json.*
- README 首屏写明「默认直接用你的 Claude Code」；provider 表格改成不换行，标签列
  不再被挤成竖排；删去赞赏段落。
  *docs: first screen notes Claude Code is used by default; provider table no
  longer wraps; donation section removed.*

---

## 1.0.3

去重基准时间修复 —— 同名栏目窗口外复现后，更旧的窗内转载不再逃过去重。
（下游 [Vibe-Research](https://github.com/simonlin1212/Vibe-Research) 分叉里 codex
审查发现的两个去重 bug，回馈上游：一个在本仓库真实存在、已修；另一个本仓库
实现本就正确，补测试锁行为防回归。）

- **fix：保留条目时刷新标题去重的基准时间**。此前 `dedup()` 用 `setdefault`
  登记标题时间基准，基准永远停在最新那期——同名栏目在 48h 窗口外合法复现
  （合法保留）后，比它更旧的窗内转载与最新期时间差超窗，就逃过了去重。
  现在保留条目时用赋值刷新基准（跟着「最近保留的那条」走），丢弃分支保持
  `setdefault`（被丢弃的转载不能反过来把窗口越拖越长，链式转载会把窗口外的
  合法复现也吞掉）。
  *fetch: refresh the title-dedup baseline on kept items, so a within-window
  reprint after a legitimate out-of-window recurrence no longer escapes dedup.*
- **test：锁死「转义 query 分隔符不折叠」的行为**。`?id=a%26b%3Dc` 与
  `?id=a&b=c` 必须归一化成不同的 key——`parse_qsl` 会把转义分隔符解码回
  `&`/`=`，重组必须用 `urlencode` 重新转义；手工 `"&".join` 拼接会把两篇不同
  文章误合并（下游分叉真实踩过此坑，本仓库实现本就用 `urlencode`，补测试防
  日后改坏）。
  *test: lock that percent-encoded query separators never collapse two
  distinct URLs into one dedup key.*
- `scripts/test_fetch.py` 21 → 23 例，新增的基准刷新用例已验证在 1.0.2 代码上
  失败、修复后通过。

---

## 1.0.2

条目层去重 —— 不同源转载同一条新闻不再重复显示。

- **fetch.py 新增条目层去重**（#1）：同栏内同一 URL 只留一条；标题相同且发布时间
  相近（48h 内）的转载也只留最新的一条。此前只在配置层清过跨栏重复源，运行时
  完全没有去重逻辑，姊妹站共用内容仍会重复显示。实测仓库现有数据 192 → 188 条，
  剔除的 4 条全部是 The Robot Report 与 Robotics Business Review 指向同一链接。
  *fetch: dedup items by URL and by syndicated title within each sector.*
  - **只剥跟踪参数（utm_* / fbclid / spm 等），不整段砍 query**：不少源把文章 id
    放在 query 里（`?p=123`），砍掉整段会把不同文章折叠成一条——那是静默丢内容。
  - **标题去重限定 48h 窗口**：不加窗口会把「每周综述」这类跨周复用的固定栏目名
    整片清掉，同样是丢内容。
  - 运行末尾打印剔除条数，去重结果可见而非静默发生。
- **codex 审计后收紧三处**（审计前的实现有真缺陷）：
  - **畸形链接不再中断整次刷新**：`normalize_url` 在 `dedup()` 里调用，那已在
    `fetch()` 的单源异常处理之外——`https://[broken` 会让 `urlsplit` 抛 ValueError
    并终止 `main()`，一条新闻都写不出来。解析失败改为退回"原串小写"当 key。
  - **不再剥 `source` / `from` / `ref` / `share` 这类通用参数**：它们在某些站点上是
    文章标识（`?source=alpha` 与 `?source=beta` 是两篇），无条件剥掉会把不同文章
    归一化成同一个 key 再删掉一篇。只保留 utm_* / fbclid / gclid / spm 等无歧义的。
  - **时间缺失时不做标题去重**：两条都没有发布时间时，无从判断是转载还是同名栏目的
    不同期。判错的代价不对等——多显示一条只是冗余，判错删掉是永久丢一篇。交给 URL
    去重兜底。（此前的实现和测试把这条写反了。）
- **新增 `scripts/test_fetch.py`**（19 例，纯标准库）：除了"重复要去掉"，重点锁死
  两条反向边界——带文章 id 的不同 URL 必须都留、跨周同名栏目必须都留。
  *Add dedup tests, including the two over-dedup regressions.*

感谢 [@iyangjialin](https://github.com/iyangjialin) 在 PR
[#2](https://github.com/simonlin1212/investment-news/pull/2) 里提出的去重思路。

---

## 1.0.1

健壮性修复 / Robustness fixes —— 自动化刷新场景下「某栏静默失败、没人发现」的问题。

- **digest.py 不再静默吞 LLM 异常**:`_llm` 失败时打出原因(超时/空返回/格式异常)+ 所属栏目,便于定位。
  *digest: surface LLM call errors instead of swallowing them.*
- **digest.py 偶发失败重试 1 → 3 次**(`ATTEMPTS=3`),嵌套调 `claude -p` 时偶发空返回的概率显著下降。
  *digest: retry transient LLM failures up to 3 times.*
- **digest.py 运行末尾汇总失败栏目** + 提示「重跑可只补失败栏(成功栏自动跳过)」,不再只能靠人肉盯「0 条」。
  *digest: print a summary of failed sectors at the end of a run.*
- **digest.py 失败栏也截断到 `TOPN`**:失败与成功栏目条数一致,不再出现某栏多带几条没翻译的旧数据。
  *digest: truncate items to TOPN even when a sector fails, for consistency.*
- **fetch.py 单源失败不再静默**:抓取出错的源会打出源名+原因,并在末尾汇总「X/N 个源抓取失败」;`None`(出错)与 `[]`(成功但近 N 天无新内容)区分开。
  *fetch: report failed sources by name; distinguish errored sources from empty-but-OK ones.*

### 安全 / Security

- **看板 XSS 与本地服务暴露**：`index.html` 的 RSS 外链未转义直入 `href`，新增 `safeUrl()` 仅放行 http(s) 并转义，堵住属性逃逸 XSS 与 `javascript:` / `data:` 伪协议（两处）；`server.py` 由绑 `0.0.0.0` 改为**仅绑 `127.0.0.1`**（看板会跑本机子进程，绝不能对局域网开放），移除通配 CORS，`/api/refresh` 只保留 POST（GET 可被 `<img>` / 跳转做 CSRF 触发子进程）。
  *Escape RSS link URLs; bind to loopback only; drop wildcard CORS; POST-only refresh.*

### 兼容性 / Compatibility

- **中文 Windows 下点刷新按钮必崩**：`child_env()` 给子进程设了 `PYTHONUTF8=1` 强制其输出 UTF-8，父进程的 `subprocess.run(text=True)` 却按系统 locale 解码——中文 Windows 上即 GBK，必然 `UnicodeDecodeError`。两处显式加 `encoding="utf-8", errors="replace"`。（#4）
  *Fix UnicodeDecodeError on Chinese Windows when clicking refresh.*

### 网络 / Networking

- **单源超时可配，默认 14s → 30s**：新增 `FETCH_TIMEOUT` 环境变量。14s 在链路差时会把大量本来能成功的源判成失败。README 新增「网络环境」小节，说明 urllib 原生读 `HTTPS_PROXY` / `HTTP_PROXY`（无需改代码），以及代理需在启动 `server.py` 前 export。（#3）
  *Make per-source timeout configurable; default raised to 30s; document proxy usage.*
  > 未采纳「默认关闭证书校验」的建议——实测 Python 3.9 / 3.12 下 monkeypatch `ssl._create_default_https_context` 对 `urllib.request.urlopen` 均生效，报告人推测的机制并不成立；默认关闭 TLS 校验是对所有用户的安全降级。README 改为指出证书链的正确修法。

### 数据 / Data

- **清掉跨栏重复源**：Engadget 与 少数派 原本同时挂在 `tech` 和 `consumer` 两栏，同一条新闻在看板出现两次。两家均为消费电子/数码媒体，从 `tech` 移除（106 源）。`build_sources.py` 同步去重并新增跨栏重复断言——再混进重复源会直接报错，而不是跑一次生成器就把去重结果覆盖回去。（#1）
  *Remove cross-column duplicate sources; add a guard in the generator.*
  > 条目级去重（不同源转载同一条新闻）见 PR #2，尚未合并。

## 1.0.0

首个版本 / Initial release.

- 12 大赛道映射 A股板块,100+ 权威源,纯标准库零依赖。
- `fetch.py` 抓取 → `digest.py` AI 要点+中文翻译(claude 订阅 / API 二选一),本地静态看板。
