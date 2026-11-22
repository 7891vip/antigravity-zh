# -*- coding: utf-8 -*-
"""词典与规则的静态校验（CI 使用）。

检查项：
1. src/dict/*.json 均为合法 JSON 对象；
2. 条目值非空；
3. 跨文件重复键仅作提示（合并时后加载覆盖前者，属预期行为）；
4. 键/译文首尾空白仅作提示（个别条目刻意保留空格，用于拼接前缀）；
5. src/rules.json 每条为 [正则, 替换] 二元组，且正则可编译。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(ROOT, "src", "dict")
RULES = os.path.join(ROOT, "src", "rules.json")


def main():
    errors = []
    warns = []
    seen = {}
    total = 0

    if not os.path.isdir(DICT_DIR):
        print("缺少目录: %s" % DICT_DIR)
        return 1

    for name in sorted(os.listdir(DICT_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(DICT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001
            errors.append("%s: JSON 解析失败 (%s)" % (name, exc))
            continue
        if not isinstance(data, dict):
            errors.append("%s: 顶层必须是对象" % name)
            continue
        for k, v in data.items():
            total += 1
            if not isinstance(k, str) or not k.strip():
                errors.append("%s: 空键" % name)
                continue
            if not isinstance(v, str) or not v.strip():
                errors.append("%s: %r 的译文为空" % (name, k))
                continue
            if k != k.strip() or v != v.strip():
                warns.append("%s: 保留首尾空白 %r" % (name, k))
            seen.setdefault(k, []).append(name)

    dup = {k: v for k, v in seen.items() if len(v) > 1}

    rule_count = 0
    if os.path.exists(RULES):
        with open(RULES, "r", encoding="utf-8") as f:
            rules = json.load(f)
        if not isinstance(rules, list):
            errors.append("rules.json: 顶层必须是数组")
        else:
            for i, item in enumerate(rules):
                if not (isinstance(item, list) and len(item) == 2):
                    errors.append("rules.json[%d]: 必须是 [正则, 替换]" % i)
                    continue
                pattern, repl = item
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append("rules.json[%d]: 正则无法编译 (%s)" % (i, exc))
                if not isinstance(repl, str) or not repl:
                    errors.append("rules.json[%d]: 替换串为空" % i)
                rule_count += 1
    else:
        errors.append("缺少 rules.json")

    print("词典条目: %d（去重后 %d）" % (total, len(seen)))
    print("句式规则: %d" % rule_count)
    print("跨文件重复键: %d %s" % (len(dup), sorted(dup)[:5] if dup else ""))
    print("首尾空白提示: %d" % len(warns))
    for w in warns[:5]:
        print("  ~", w)

    if errors:
        print("\n发现 %d 个错误：" % len(errors))
        for e in errors:
            print("  -", e)
        return 1

    print("\n校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
