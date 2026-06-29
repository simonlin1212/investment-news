# Changelog

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

## 1.0.0

首个版本 / Initial release.

- 12 大赛道映射 A股板块,100+ 权威源,纯标准库零依赖。
- `fetch.py` 抓取 → `digest.py` AI 要点+中文翻译(claude 订阅 / API 二选一),本地静态看板。
