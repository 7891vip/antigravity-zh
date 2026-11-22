"""构建 Antigravity 简体中文汉化包（app.asar 重打包）。

用法:
  python build.py                 # 生成 app.zh.asar 与校验报告
  python build.py --install       # 同时备份并安装到 Antigravity
  python build.py --restore       # 还原官方英文
"""
import argparse, hashlib, json, os, shutil, struct, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORK = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "antigravity")
ASAR = os.path.join(APP_DIR, "resources", "app.asar")
BACKUP = os.path.join(APP_DIR, "resources", "app.asar.zh-backup")
STAGE = os.path.join(WORK, "app.zh.asar")
STAMP = os.path.join(WORK, "build-report.json")


def read_asar(path):
    with open(path, "rb") as f:
        raw = f.read()
    size_a, header_size = struct.unpack("<II", raw[0:8])
    json_len = struct.unpack("<I", raw[12:16])[0]
    header = json.loads(raw[16:16 + json_len].decode("utf-8"))
    base = 8 + header_size
    files = []

    def walk(node, prefix=""):
        for name, value in node.get("files", {}).items():
            p = prefix + "/" + name
            if "files" in value:
                walk(value, p)
            else:
                files.append((p, value, base + int(value.get("offset", 0))))

    walk(header)
    return raw, header, base, files


def data_of(raw, entry):
    path, meta, off = entry
    size = int(meta.get("size", 0))
    return raw[off:off + size]


def build_dict():
    merged = {}
    total = 0
    ddir = os.path.join(WORK, "dict")
    for name in sorted(os.listdir(ddir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(ddir, name), "r", encoding="utf-8") as f:
            part = json.load(f)
        total += len(part)
        merged.update(part)
    return merged, total


def build_engine(dict_map):
    with open(os.path.join(WORK, "engine_body.js"), "r", encoding="utf-8") as f:
        body = f.read()
    with open(os.path.join(WORK, "rules.json"), "r", encoding="utf-8") as f:
        rules = json.load(f)
    dict_json = json.dumps(dict_map, ensure_ascii=False, separators=(",", ":"))
    rules_pairs = "[" + ",".join(
        "[%s,%s]" % (json.dumps(p, ensure_ascii=False), json.dumps(r, ensure_ascii=False))
        for p, r in rules
    ) + "]"
    rules_js = "(%s).map(function(x){return [new RegExp(x[0]), x[1]];})" % rules_pairs
    body = body.replace("var dict = DICT; // 由构建脚本注入", "var dict = %s;" % dict_json)
    body = body.replace("var RULES = __RULES__; // 由构建脚本注入（动态句式）", "var RULES = %s;" % rules_js)
    return "/* ---- Antigravity 简体中文汉化包 v1.0 · 自动生成，请勿手工修改 ---- */\n" + body


def make_header(entries):
    root = {"files": {}}

    def ensure(node, parts):
        cur = node
        for p in parts:
            cur = cur["files"].setdefault(p, {"files": {}})
        return cur

    for path, meta in entries:
        parts = [x for x in path.strip("/").split("/") if x]
        parent = ensure(root, parts[:-1])
        parent["files"][parts[-1]] = meta
    return root


def pack(path, entries):
    """entries: list of (path, meta, bytes or None)  None => unpacked"""
    offset = 0
    header_entries = []
    blobs = []
    for p, base_meta, blob in entries:
        meta = {k: v for k, v in base_meta.items() if k not in ("offset", "size", "integrity")}
        if blob is None:
            meta["size"] = int(base_meta.get("size", 0))
            meta["unpacked"] = True
        else:
            meta["size"] = len(blob)
            meta["offset"] = str(offset)
            offset += len(blob)
            blobs.append(blob)
        header_entries.append((p, meta))
    header = make_header(header_entries)
    json_bytes = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    pad = (-len(json_bytes)) % 4
    L = 4 + len(json_bytes) + pad
    H = 4 + L
    prefix = struct.pack("<IIII", 4, H, L, len(json_bytes)) + json_bytes + b"\x00" * pad
    with open(path, "wb") as f:
        f.write(prefix)
        for b in blobs:
            f.write(b)
    return len(prefix) + offset


def verify(new_path, entries):
    """重新解析新 asar，逐文件比对 SHA256。"""
    raw, header, base, files = read_asar(new_path)
    got = {}
    for p, meta, off in files:
        if meta.get("unpacked"):
            continue
        got[p] = hashlib.sha256(raw[off:off + int(meta["size"])]).hexdigest()
    bad = []
    for p, meta, blob in entries:
        if blob is None:
            continue
        want = hashlib.sha256(blob).hexdigest()
        have = got.get(p)
        if have != want:
            bad.append(p)
            print("MISMATCH %s want=%s have=%s len=%d got=%s" % (p, want[:12], (have or "none")[:12], len(blob), "yes" if have else "no"))
    return len(got), bad


def install(new_path):
    if not os.path.exists(BACKUP):
        shutil.copy2(ASAR, BACKUP)
        print("已备份原版: %s" % BACKUP)
    shutil.copy2(new_path, ASAR)
    print("已写入: %s" % ASAR)


def restore():
    if not os.path.exists(BACKUP):
        print("没有找到备份，无法还原")
        return 1
    shutil.copy2(BACKUP, ASAR)
    print("已还原官方原版")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        return restore()

    dict_map, total = build_dict()
    duplicates = total - len(dict_map)
    engine = build_engine(dict_map)

    src = BACKUP if os.path.exists(BACKUP) else ASAR
    raw, header, base, files = read_asar(src)
    entries = []
    replaced = False
    for p, meta, off in files:
        if p == "/dist/zh-build.json":
            continue  # 旧版本残留，重建时丢弃
        if meta.get("unpacked"):
            entries.append((p, meta, None))
        else:
            blob = raw[off:off + int(meta["size"])]
            if p == "/dist/preload.js":
                blob = blob + b"\n" + engine.encode("utf-8")
                replaced = True
            entries.append((p, meta, blob))
    if not replaced:
        print("错误: 未找到 /dist/preload.js", file=sys.stderr)
        return 2

    stamp = {
        "pack": "antigravity-zh",
        "version": "1.0.0",
        "dictEntries": len(dict_map),
        "duplicates": duplicates,
        "engineBytes": len(engine),
        "builtAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sourceAsarSize": len(raw),
    }
    stamp_bytes = json.dumps(stamp, ensure_ascii=False, indent=2).encode("utf-8")
    entries.append(("/dist/zh-build.json", {"size": 0}, stamp_bytes))

    size = pack(STAGE, entries)
    n, bad = verify(STAGE, entries)
    print("词典条目: %d（合并去重 %d）" % (len(dict_map), duplicates))
    print("引擎大小: %.1f KB" % (len(engine) / 1024.0))
    print("新 asar: %.2f MB, 校验文件 %d 个, 不一致 %d 个" % (size / 1048576.0, n, len(bad)))
    if bad:
        print("不一致:", bad[:5], file=sys.stderr)
        return 3
    with open(STAMP, "w", encoding="utf-8") as f:
        json.dump(stamp, f, ensure_ascii=False, indent=2)

    if args.install:
        install(STAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
