import sys, json, os, time
sys.path.insert(0, r"D:\UserData\下载\antigravity-zh\_work")
import ui, scan

OUT = r"D:\UserData\下载\antigravity-zh\_work\missing"
os.makedirs(OUT, exist_ok=True)

PANELS = [
    ("应用程序", "app"),
    ("外观", "appearance"),
    ("快捷键", "shortcuts"),
    ("通知", "notifications"),
    ("浏览器", "browser"),
    ("对话", "chat"),
    ("Models", "models"),
]


def dump(name, data):
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    # 先记录当前面板
    dump("general", ui.run(scan.SCAN))
    for label, key in PANELS:
        r = ui.click_at(label)
        print(label, "->", r)
        time.sleep(2.0)
        data = ui.run(scan.SCAN) or {}
        dump(key, data)
        print("   untranslated:", len(data))


if __name__ == "__main__":
    main()
