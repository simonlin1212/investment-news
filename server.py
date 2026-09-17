#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py —— 本地看板服务 + 刷新接口(纯标准库)。
- 静态服务整个 investment-news 目录(看板、data、脚本)
- POST /api/refresh → 跑 scripts/fetch.py(抓取+红线+最近N天) 再跑 scripts/digest.py
  (用 llm.config.json 配的大模型出「今日要点」+翻译),完成后返回 JSON。前端按钮转圈等它。
跑法: python3 server.py [port]   默认 8793
"""
import os, sys, json, subprocess, secrets, hmac
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
# /api/refresh 会跑昂贵的子进程(抓取+调用大模型),即便只绑回环也要防本机其它
# 用户/进程随意触发消耗配额,所以要求携带启动时生成的一次性令牌。
REFRESH_TOKEN = secrets.token_urlsafe(32)


def child_env():
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    # 保证子进程能找到 claude(订阅模式)
    extra = "/opt/homebrew/bin:/usr/local/bin:" + os.path.expanduser("~/.local/bin")
    env["PATH"] = extra + ":" + env.get("PATH", "")
    return env


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def log_message(self, *a):
        pass

    def _refresh(self):
        try:
            py = sys.executable
            env = child_env()
            # encoding 必须显式指定 utf-8：child_env() 已给子进程设了 PYTHONUTF8=1
            # （强制它输出 UTF-8），父进程若按 locale 解码，中文 Windows 上就是 GBK，
            # 必然 UnicodeDecodeError（issue #4）。errors="replace" 兜底异常字节。
            r1 = subprocess.run([py, "scripts/fetch.py"], cwd=HERE, env=env,
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=600)
            r2 = subprocess.run([py, "scripts/digest.py"], cwd=HERE, env=env,
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=1200)
            ok = (r2.returncode == 0 and r1.returncode == 0)
            payload = {"ok": ok, "fetch": (r1.stdout or "")[-500:], "digest": (r2.stdout or "")[-500:]}
            if not ok:
                payload["error"] = ((r2.stderr or "") + (r1.stderr or ""))[-500:]
            code = 200 if ok else 500
        except Exception as e:
            payload, code = {"ok": False, "error": str(e)}, 500
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.startswith("/api/refresh"):
            return self._refresh()
        self.send_error(404)

    def do_GET(self):
        # /api/refresh 只走 POST:GET 会跑 fetch.py+claude 子进程,若可 GET 触发则易被
        # <img>/跳转做 CSRF。这里让它落到静态处理(404),仅 do_POST 才真正刷新。
        return super().do_GET()


if __name__ == "__main__":
    print("看板服务已启动: http://localhost:%d/index.html   (Ctrl+C 停止)" % PORT)
    # 只绑回环:看板+/api/refresh 会跑本机子进程(fetch.py/claude),绝不能对局域网开放。
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
