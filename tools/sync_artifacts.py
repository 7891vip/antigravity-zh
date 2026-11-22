# -*- coding: utf-8 -*-
"""把重新构建的产物同步到「桌面发布包」与「GitHub 仓库目录」。"""
import hashlib
import json
import os
import shutil

PACK = r"D:\UserData\桌面\Antigravity-中文汉化包"
REPO = r"D:\UserData\桌面\antigravity-zh"
SRC_ASAR = os.path.join(REPO, "src", "app.zh.asar")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merged_count():
    total = {}
    for name in sorted(os.listdir(os.path.join(REPO, "src", "dict"))):
        if name.endswith(".json"):
            total.update(json.load(open(os.path.join(REPO, "src", "dict", name), encoding="utf-8")))
    rules = json.load(open(os.path.join(REPO, "src", "rules.json"), encoding="utf-8"))
    return len(total), len(rules)


entries, rules = merged_count()
print("词典去重后: %d 条, 规则 %d 条" % (entries, rules))

for asar_path in (os.path.join(PACK, "app.zh.asar"), os.path.join(REPO, "dist", "app.zh.asar")):
    shutil.copy2(SRC_ASAR, asar_path)
    print("copied ->", asar_path)

pack_hash = sha256(os.path.join(REPO, "dist", "app.zh.asar"))
pack_size = os.path.getsize(os.path.join(REPO, "dist", "app.zh.asar"))

for mpath in (os.path.join(PACK, "manifest.json"), os.path.join(REPO, "dist", "manifest.json")):
    with open(mpath, encoding="utf-8-sig") as f:
        m = json.load(f)
    m["packAsarSha256"] = pack_hash
    m["packAsarSize"] = pack_size
    m["dictEntries"] = entries
    m["ruleCount"] = rules
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=4)
    print("manifest updated ->", mpath, pack_hash[:12])

# 截图
shot_src = r"D:\UserData\桌面\agy-quota.png"
shutil.copy2(shot_src, os.path.join(PACK, "截图", "11-模型与用量-配额.png"))
shutil.copy2(shot_src, os.path.join(REPO, "screenshots", "11-quota.png"))
print("screenshots copied")

# README 数字
for rp in (os.path.join(REPO, "README.md"),):
    txt = open(rp, encoding="utf-8").read()
    before = txt
    txt = txt.replace("**1887 条**", "**%d 条**" % entries)
    txt = txt.replace("**43 条**", "**%d 条**" % rules)
    txt = txt.replace("1,887 hand-curated", "%s hand-curated" % format(entries, ","))
    txt = txt.replace("1887 条", "%d 条" % entries)
    txt = txt.replace("43 条句式规则", "%d 条句式规则" % rules)
    if txt != before:
        open(rp, "w", encoding="utf-8").write(txt)
        print("README 更新数字")
    else:
        print("README 无需改动")

print("完成")
