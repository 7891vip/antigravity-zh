# -*- coding: utf-8 -*-
"""更新 README / CHANGELOG / 说明.txt，补充单文件 exe 版本。"""
import io
import os

REPO = r"D:\UserData\桌面\antigravity-zh"
PACK = r"D:\UserData\桌面\Antigravity-中文汉化包"

README = os.path.join(REPO, "README.md")
readme = io.open(README, encoding="utf-8").read()

OLD_START = "## 快速开始\n\n### 方式一：下载发布包（推荐）"
NEW_START = """## 快速开始

### 方式一：单文件 exe（推荐，零依赖）

1. 到 [Releases](../../releases) 下载 `Antigravity-ZH-Installer.exe`（约 6.3 MB，汉化文件已内嵌，不需要 PowerShell / Python）。
2. 双击运行，程序会自动定位 Antigravity 并显示当前状态（已汉化 / 官方原版 / 已备份）。
3. 点「安装 / 更新汉化」，剩下的关闭客户端、备份、写入、重启全自动完成。

![汉化工具](screenshots/12-installer.png)

也支持命令行静默执行（便于脚本或批量部署）：

| 参数 | 作用 |
| --- | --- |
| `--install` | 静默安装 / 更新汉化 |
| `--restore` | 静默还原官方英文 |
| `--status` | 只检测状态 |
| `--help` | 显示帮助 |

日志写入 `%TEMP%\\antigravity-zh.log`。

### 方式二：脚本版（zip）"""

if OLD_START in readme and "单文件 exe" not in readme:
    readme = readme.replace(OLD_START, NEW_START, 1)
    readme = readme.replace("### 方式二：直接用本仓库", "### 方式三：直接用本仓库", 1)

readme = readme.replace(
    "| 零依赖 | 装机端只需 PowerShell 5.1（系统自带），不需要 Python / Node |",
    "| 零依赖 | 单文件 exe 版不依赖 PowerShell / Python；脚本版只需系统自带 PowerShell 5.1 |")

readme = readme.replace(
    "├─ dist/                 已构建产物\n",
    "├─ src/exe/              单文件安装器（C# 源码、图标、build.ps1）\n├─ dist/                 已构建产物\n", 1)

io.open(README, "w", encoding="utf-8").write(readme)
print("README updated:", "单文件 exe" in readme, "| exe 目录:", "src/exe/" in readme)

# CHANGELOG
CH = os.path.join(REPO, "CHANGELOG.md")
ch = io.open(CH, encoding="utf-8").read()
if "单文件 exe" not in ch:
    block = """## v1.0.0 新增 — 单文件安装器

新增 `Antigravity-ZH-Installer.exe`（6.3 MB，C# / .NET Framework 4.x 编译）：

- 汉化文件内嵌，双击即用，不需要 PowerShell 或 Python
- 图形界面显示安装目录、当前状态（已汉化 / 官方原版 / 未知版本）、备份状态
- 一键「安装 / 更新汉化」「还原英文」「打开安装目录」
- 写入后自动做 SHA256 校验，失败会明确报错
- 支持 `--install` / `--restore` / `--status` 静默参数
- 启动客户端时剔除 `ELECTRON_RUN_AS_NODE`，避免从 Electron 系终端启动时客户端秒退

"""
    ch = ch.replace("# 更新日志\n\n", "# 更新日志\n\n" + block, 1)
    io.open(CH, "w", encoding="utf-8").write(ch)
    print("CHANGELOG updated")

# 说明.txt（仓库 docs 与发布包各一份）
for path in (os.path.join(REPO, "docs", "说明.txt"), os.path.join(PACK, "说明.txt")):
    raw = open(path, "rb").read()
    bom = b""
    if raw.startswith(b"\xef\xbb\xbf"):
        bom, raw = raw[:3], raw[3:]
    text = raw.decode("utf-8")
    if "Antigravity-ZH-Installer.exe" in text:
        print("说明.txt 已含 exe 说明:", path)
        continue
    anchor = "一、已经装好了吗？"
    ins = """一、最简单的用法：双击 Antigravity-ZH-Installer.exe
------------------------------------------------
单文件程序，汉化文件已内嵌，不需要安装任何运行环境。
双击后点「安装 / 更新汉化」，它会自动关闭客户端、备份官方文件、
写入汉化、再重新启动客户端。想还原英文就点「还原英文」。

二、已经装好了吗？"""
    if anchor in text:
        text = text.replace(anchor, ins, 1)
        # 后面的编号往后顺延（保留原文其他小节标题不动，仅提示）
        open(path, "wb").write(bom + text.encode("utf-8"))
        print("说明.txt updated:", path)
    else:
        print("说明.txt 未找到插入锚点:", path)
