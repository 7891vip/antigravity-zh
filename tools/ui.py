import sys, json, base64, time
sys.path.insert(0, r"D:\UserData\下载\antigravity-zh\_work")
import cdp

PORT = 9333
SHOT_DIR = r"D:\UserData\下载\antigravity-zh\_work\shots"


def page():
    pages = [t for t in cdp.targets(PORT) if t.get("type") == "page" and "127.0.0.1" in (t.get("url") or "")]
    return pages[0] if pages else None


def run(expr, await_promise=False):
    p = page()
    c = cdp.CDP(p["webSocketDebuggerUrl"])
    try:
        r = c.call("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise,
            "userGesture": True,
        }, timeout=120)
        if r.get("exceptionDetails"):
            return {"__exc": r["exceptionDetails"].get("exception", {}).get("description", str(r["exceptionDetails"]))}
        return r["result"].get("value")
    finally:
        c.ws.close()


def shot(name):
    p = page()
    c = cdp.CDP(p["webSocketDebuggerUrl"])
    try:
        res = c.call("Page.captureScreenshot", {"format": "png"}, timeout=60)
        path = "%s\\%s.png" % (SHOT_DIR, name)
        with open(path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        return path
    finally:
        c.ws.close()


def stats():
    raw = run("document.getElementById('__agy_zh_stats') && document.getElementById('__agy_zh_stats').getAttribute('data-zh')")
    if isinstance(raw, str):
        return json.loads(raw)
    return {}


def click_at(text, nth=0):
    """真实鼠标点击：按文本定位元素中心点后 dispatchMouseEvent。"""
    expr = """(function(){
      var t=%s;
      var els=Array.from(document.querySelectorAll('button,[role="button"],[role="tab"],[role="menuitem"],a,div,span,label,li'))
        .filter(function(e){ var s=(e.innerText||'').trim(); return s===t; });
      if(!els.length){
        els=Array.from(document.querySelectorAll('button,[role="button"],[role="tab"],[role="menuitem"],a,div,span,label,li'))
          .filter(function(e){ return (e.innerText||'').trim().indexOf(t)>=0; });
      }
      if(!els.length) return null;
      els.sort(function(a,b){
        var ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect();
        return (ra.width*ra.height) - (rb.width*rb.height);
      });
      var el=els[%d] || els[0];
      var r=el.getBoundingClientRect();
      return [r.left+r.width/2, r.top+r.height/2, el.tagName, els.length];
    })()""" % (json.dumps(text, ensure_ascii=False), nth)
    pos = run(expr)
    if not pos:
        return "not found"
    x, y, tag, n = pos
    p = page()
    c = cdp.CDP(p["webSocketDebuggerUrl"])
    try:
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            c.call("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left",
                                                "clickCount": 1, "buttons": 1 if t != "mouseReleased" else 0})
        return "clicked %s at %s,%s (cands=%s)" % (tag, round(x), round(y), n)
    finally:
        c.ws.close()


def click_text(text, tag="button,[role='button'],[role='menuitem'],[role='tab'],a,div,span"):
    expr = """(function(){
      var t=%s;
      var cands=Array.from(document.querySelectorAll(%s));
      var el=cands.filter(function(e){ return (e.innerText||'').trim()===t; })[0]
          || cands.filter(function(e){ return (e.innerText||'').trim().indexOf(t)>=0; })[0];
      if(!el) return 'not found';
      var target = el.closest('button,a,[role=\"button\"],[role=\"menuitem\"],[role=\"tab\"]') || el;
      target.scrollIntoView({block:'center'});
      target.click();
      return 'clicked:'+(target.tagName||'');
    })()""" % (json.dumps(text, ensure_ascii=False), json.dumps(tag))
    return run(expr)


def key(combo):
    """e.g. 'ctrl+,' or 'Escape'"""
    p = page()
    c = cdp.CDP(p["webSocketDebuggerUrl"])
    try:
        parts = combo.lower().split("+")
        k = parts[-1]
        mods = 0
        for m in parts[:-1]:
            mods |= {"ctrl": 2, "alt": 1, "shift": 8, "meta": 4}[m]
        vk = KEYCODES.get(k, ord(k.upper()) if len(k) == 1 else 0)
        txt = k if len(k) == 1 else ""
        c.call("Input.dispatchKeyEvent", {"type": "keyDown", "modifiers": mods, "key": k,
                                          "code": KEYCODES_NAME.get(k, ""), "windowsVirtualKeyCode": vk,
                                          "nativeVirtualKeyCode": vk, "text": txt})
        c.call("Input.dispatchKeyEvent", {"type": "keyUp", "modifiers": mods, "key": k,
                                          "code": KEYCODES_NAME.get(k, ""), "windowsVirtualKeyCode": vk,
                                          "nativeVirtualKeyCode": vk})
        return "sent:" + combo
    finally:
        c.ws.close()


KEYCODES = {"escape": 27, "enter": 13, "tab": 9, "backspace": 8, ",": 188, ".": 190, "/": 191}
KEYCODES_NAME = {"escape": "Escape", "enter": "Enter", "tab": "Tab", "backspace": "Backspace",
                 ",": "Comma", ".": "Period", "/": "Slash"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        s = stats()
        print(json.dumps(s, ensure_ascii=False, indent=1)[:4000])
    elif cmd == "shot":
        print(shot(sys.argv[2]))
    elif cmd == "click":
        print(click_text(sys.argv[2]))
    elif cmd == "eval":
        print(json.dumps(run(sys.argv[2]), ensure_ascii=False)[:4000])
