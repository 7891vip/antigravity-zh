# -*- coding: utf-8 -*-
"""把当前目录发布的 GitHub 仓库（纯标准库，无需 git）。

鉴权：优先读环境变量 GITHUB_TOKEN；其次读 --token-file 指定的文件。

用法：
    python tools/publish_github.py --repo antigravity-zh --release-zip ..\\Antigravity-zh-CN-v1.0.0.zip

流程：创建仓库 → 用 Git Data API 一次性提交全部文件（单 commit）
      → 设置描述与 topics → 打 Release 并上传 zip。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_FILE_EXT = {".zip", ".pyc"}


def token():
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if t:
        return t
    for i, a in enumerate(sys.argv):
        if a == "--token-file" and i + 1 < len(sys.argv):
            with open(sys.argv[i + 1], "r", encoding="utf-8-sig") as f:
                return f.read().strip()
    sys.exit("缺少 token：请设置 GITHUB_TOKEN 环境变量或使用 --token-file")


TOKEN = token()


def call(method, url, payload=None, raw=None, ctype=None, base=API):
    data = None
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "antigravity-zh-publisher",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    req = urllib.request.Request(base + url, data=data, headers=headers, method=method)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (500, 502, 503, 504) or (e.code == 403 and "rate limit" in body.lower()):
                time.sleep(2 + attempt * 3)
                continue
            raise RuntimeError("%s %s -> %s %s" % (method, url, e.code, body[:500]))
    raise RuntimeError("重试耗尽: %s %s" % (method, url))


def collect_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.join(rel_dir, name).replace("\\", "/")
            ext = os.path.splitext(name)[1].lower()
            if ext in SKIP_FILE_EXT:
                continue
            out.append((rel, path))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="antigravity-zh")
    ap.add_argument("--release-zip", default="")
    ap.add_argument("--token-file", default="")
    ap.add_argument("--private", action="store_true")
    args = ap.parse_args()

    me = call("GET", "/user")
    login = me["login"]
    print("账号: %s" % login)

    desc = ("Google Antigravity 桌面客户端简体中文汉化包：1887 条词条 + 43 条句式规则，"
            "运行时 DOM 翻译引擎，一键安装 / 一键还原，不修改官方二进制。")
    try:
        repo = call("POST", "/user/repos", {
            "name": args.repo,
            "description": desc[:340],
            "private": bool(args.private),
            "has_issues": True,
            "has_wiki": False,
            "has_projects": False,
            "auto_init": False,
        })
    except RuntimeError as e:
        if "422" not in str(e):
            raise
        print("仓库已存在，复用:", login + "/" + args.repo)
        repo = call("GET", "/repos/%s/%s" % (login, args.repo))
    full = repo["full_name"]
    print("仓库: %s  (private=%s)" % (full, repo.get("private")))

    # Git Data API 在空仓库上会返回 409 "Git Repository is empty"，
    # 先用 Contents API 建一个初始提交把 main 分支开出来。
    try:
        call("GET", "/repos/%s/git/ref/heads/main" % full)
        print("分支 main 已存在")
    except RuntimeError:
        call("PUT", "/repos/%s/contents/README.md" % full, {
            "message": "chore: init repository",
            "content": base64.b64encode(
                "Antigravity 简体中文汉化包\n".encode("utf-8")).decode("ascii"),
        })
        print("已创建初始提交以开启 main 分支")

    files = collect_files()
    print("待上传文件: %d 个" % len(files))

    tree = []
    for i, (rel, path) in enumerate(files, 1):
        with open(path, "rb") as f:
            blob = f.read()
        if rel == "README.md":
            blob = blob.replace(b"<your-name>", login.encode("utf-8"))
        b = call("POST", "/repos/%s/git/blobs" % full, {
            "content": base64.b64encode(blob).decode("ascii"),
            "encoding": "base64",
        })
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": b["sha"]})
        if i % 10 == 0 or i == len(files):
            print("  blob %d/%d" % (i, len(files)))

    t = call("POST", "/repos/%s/git/trees" % full, {"tree": tree})
    commit_msg = ("feat: Antigravity 简体中文汉化包 v1.0.0\n\n"
                  "- 词条 1887 条 + 句式规则 43 条\n"
                  "- 运行时 DOM 翻译引擎（preload 注入）\n"
                  "- 一键安装 / 还原脚本与 asar 构建工具\n")
    try:
        commit = call("POST", "/repos/%s/git/commits" % full, {"message": commit_msg, "tree": t["sha"]})
    except RuntimeError as e:
        if "workflow" not in str(e).lower():
            raise
        print("token 缺少 workflow 权限，跳过 .github/workflows 后重试")
        tree2 = [x for x in tree if not x["path"].startswith(".github/workflows")]
        t2 = call("POST", "/repos/%s/git/trees" % full, {"tree": tree2})
        commit = call("POST", "/repos/%s/git/commits" % full, {"message": commit_msg, "tree": t2["sha"]})
    try:
        call("POST", "/repos/%s/git/refs" % full, {"ref": "refs/heads/main", "sha": commit["sha"]})
        print("已提交 main:", commit["sha"][:10])
    except RuntimeError as e:
        print("创建引用失败，改为强制更新:", str(e)[:120])
        call("PATCH", "/repos/%s/git/refs/heads/main" % full, {"sha": commit["sha"], "force": True})
        print("已强制更新 main:", commit["sha"][:10])

    call("PATCH", "/repos/%s" % full, {"description": desc[:340], "has_issues": True, "has_wiki": False})
    try:
        call("PUT", "/repos/%s/topics" % full, {
            "names": ["antigravity", "localization", "chinese", "i18n", "electron", "asar", "windows", "zh-cn"]
        })
    except RuntimeError as e:
        print("topics 设置失败（可忽略）:", str(e)[:120])

    if args.release_zip and os.path.exists(args.release_zip):
        rel = call("POST", "/repos/%s/releases" % full, {
            "tag_name": "v1.0.0",
            "name": "v1.0.0 — 首个公开版本",
            "body": "## Antigravity 简体中文汉化包 v1.0.0\n\n"
                    "- 词典 1887 条、句式规则 43 条\n"
                    "- 覆盖主界面 / 设置全部页签 / 智能体权限 / 插件市场\n"
                    "- 代码、终端、编辑器区域不翻译，避免污染\n\n"
                    "### 使用\n\n"
                    "1. 下载 `Antigravity-zh-CN-v1.0.0.zip` 并完整解压\n"
                    "2. 双击 `安装汉化.cmd`\n"
                    "3. 想还原英文时双击 `还原英文.cmd`\n\n"
                    "> 客户端自动更新后界面会变回英文，重新运行一次 `安装汉化.cmd` 即可。\n",
            "draft": False,
            "prerelease": False,
        })
        name = os.path.basename(args.release_zip)
        with open(args.release_zip, "rb") as f:
            data = f.read()
        call("POST",
             "/repos/%s/releases/%d/assets?name=%s" % (full, rel["id"], urllib.parse.quote(name)),
             raw=data, ctype="application/zip", base=UPLOAD)
        print("Release 已发布，附件:", name)

    print("\n完成：https://github.com/%s" % full)
    print("       https://github.com/%s/releases" % full)


if __name__ == "__main__":
    main()
