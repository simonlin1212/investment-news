#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm.py —— 统一大模型调用入口。两种 provider 二选一:

  1) claude-cli (默认, 订阅, $0)：spawn 本机已登录的 `claude` CLI。零 key,鉴权靠 claude 自己
     (事先 `claude login` 过一次)。只在【本机】可用。机制同 SDesign。
  2) api (OpenAI 兼容)：用 API key 调 /chat/completions。任意机器可用,按量付费。
     支持 DeepSeek / OpenAI / 硅基流动 / OpenRouter 等一切 OpenAI 兼容端点。

provider 由 ../llm.config.json 决定(没有就默认 claude-cli)。
**客户的 Agent**:看到 llm.config.json 就知道有这两个选项,应当问使用者要用「订阅」还是「API」。
纯标准库(api 模式用 urllib;cli 模式用 subprocess)。
"""
import os, json, shutil, subprocess, tempfile, urllib.request

# claude 禁用全部工具:只让它处理我们给的文本,不读文件/不联网/不起子任务
_DISALLOW = ["Read","Write","Edit","Bash","Glob","Grep","WebFetch","WebSearch","TodoWrite","Task","NotebookEdit"]
_CLAUDE_DIRS = ["/opt/homebrew/bin","/usr/local/bin",
                os.path.expanduser("~/.local/bin"), os.path.expanduser("~/.claude/local")]


def find_claude():
    p = shutil.which("claude")
    if p:
        return p
    for d in _CLAUDE_DIRS:
        c = os.path.join(d, "claude")
        if os.path.exists(c):
            return c
    return None


def load_config(root):
    p = os.path.join(root, "llm.config.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"provider": "claude-cli"}


def _call_cli(system, user, timeout):
    binp = find_claude()
    if not binp:
        raise RuntimeError("未检测到 claude CLI。订阅模式需本机装好 Claude Code 并 `claude login`,"
                           "或在 llm.config.json 改用 api 模式。")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(system); sysf = f.name
    try:
        p = subprocess.run([binp, "-p", "--output-format", "text",
                            "--system-prompt-file", sysf, "--disallowedTools", *_DISALLOW],
                           input=user, capture_output=True, text=True, timeout=timeout)
        return p.stdout or ""
    finally:
        try: os.unlink(sysf)
        except Exception: pass


def _call_api(system, user, cfg, timeout):
    api = cfg.get("api", cfg)
    base = (api.get("base_url") or "https://api.deepseek.com").rstrip("/")
    key = api.get("api_key") or os.environ.get(api.get("api_key_env", "LLM_API_KEY"), "")
    if not key:
        raise RuntimeError("API 模式需在 llm.config.json 的 api.api_key 填 key,或设对应环境变量。")
    model = api.get("model", "deepseek-chat")
    body = json.dumps({"model": model, "temperature": 0.3, "stream": False,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def call(system, user, cfg=None, timeout=240):
    cfg = cfg or {"provider": "claude-cli"}
    if cfg.get("provider") == "api":
        return _call_api(system, user, cfg, timeout)
    return _call_cli(system, user, timeout)
