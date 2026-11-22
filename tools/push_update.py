# -*- coding: utf-8 -*-
"""把本地改动增量推送到 GitHub（Contents API + 替换 Release 附件）。"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
FULL = "7891vip/antigravity-zh"
REPO = r"D:\UserData\桌面\antigravity-zh"
ZIP = r"D:\UserData\桌面\antigravity-zh-release\Antigravity-zh-CN-v1.0.0.zip"


def call(method, path, payload=None, raw=None, ctype=None, base="https://api.github.com"):
    headers = {"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "agy-updater"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
            return json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %s %s" % (method, path, e.code, e.read().decode("utf-8", "replace")[:300]))


def upsert(rel, message):
    p = os.path.join(REPO, rel.replace("/", os.sep))
    payload = {"message": message, "branch": "main",
               "content": base64.b64encode(open(p, "rb").read()).decode()}
    try:
        cur = call("GET", "/repos/%s/contents/%s?ref=main" % (FULL, urllib.parse.quote(rel)))
        if isinstance(cur, dict) and cur.get("sha"):
            payload["sha"] = cur["sha"]
    except RuntimeError as e:
        if "404" not in str(e):
            raise
    r = call("PUT", "/repos/%s/contents/%s" % (FULL, urllib.parse.quote(rel)), payload)
    print("  ok %-42s %s" % (rel, r["commit"]["sha"][:8]))


me = call("GET", "/user")
print("token 有效，账号:", me["login"])

files = [
    ("src/dict/p8.json", "feat(dict): 补充配额/点数页面词条"),
    ("src/rules.json", "feat(rules): 补充 Resets in / Limit Remaining 句式"),
    ("README.md", "docs: 更新词条规模为 1907 条 / 45 条规则"),
    ("CHANGELOG.md", "docs: 记录同日修订"),
    ("dist/app.zh.asar", "build: 重新打包 app.zh.asar（含配额页面文案）"),
    ("dist/manifest.json", "build: 更新 manifest 校验值"),
    ("screenshots/11-quota.png", "docs: 增加模型与用量页面截图"),
    ("tools/sync_artifacts.py", "chore(tools): 增加产物同步脚本"),
    ("tools/shot_quota.py", "chore(tools): 增加配额页截图脚本"),
]
for rel, msg in files:
    upsert(rel, msg)

# 替换 Release 附件
rel = call("GET", "/repos/%s/releases/tags/v1.0.0" % FULL)
for a in rel["assets"]:
    if a["name"].endswith(".zip"):
        call("DELETE", "/repos/%s/releases/assets/%d" % (FULL, a["id"]))
        print("  removed old asset:", a["name"])
name = os.path.basename(ZIP)
call("POST", "/repos/%s/releases/%d/assets?name=%s" % (FULL, rel["id"], urllib.parse.quote(name)),
     raw=open(ZIP, "rb").read(), ctype="application/zip", base="https://uploads.github.com")
print("  uploaded new asset:", name)
print("\n完成：https://github.com/%s" % FULL)
