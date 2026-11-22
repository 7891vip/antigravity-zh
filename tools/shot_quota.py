# -*- coding: utf-8 -*-
import base64, json, os, sys, time

TOOLS = r"D:\UserData\桌面\antigravity-zh\tools"
sys.path.insert(0, TOOLS)
import cdp

PORT = 9333
OUT = r"D:\UserData\桌面\agy-quota.png"

page = [t for t in cdp.targets(PORT) if t.get("type") == "page" and "127.0.0.1" in (t.get("url") or "")][0]
c = cdp.CDP(page["webSocketDebuggerUrl"])


def ev(expr):
    r = c.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True, "userGesture": True})
    if r.get("exceptionDetails"):
        return {"__exc": r["exceptionDetails"].get("exception", {}).get("description", "")}
    return r["result"].get("value")


def key_ctrl_comma():
    for t in ("keyDown", "keyUp"):
        c.call("Input.dispatchKeyEvent", {
            "type": t, "modifiers": 2, "key": ",", "code": "Comma",
            "windowsVirtualKeyCode": 188, "nativeVirtualKeyCode": 188,
        })


def click_by_text(text, nth=0):
    pos = ev("""(function(){
      var t=%s;
      var els=Array.from(document.querySelectorAll('button,[role="button"],[role="tab"],[role="menuitem"],a,div,span,label,li'))
        .filter(function(e){ var s=(e.innerText||'').trim(); return s===t; });
      if(!els.length) return null;
      els.sort(function(a,b){var ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect(); return ra.width*ra.height - rb.width*rb.height;});
      var el=els[%d]; if(!el) return null;
      var r=el.getBoundingClientRect();
      return [r.left+r.width/2, r.top+r.height/2, el.tagName, els.length];
    })()""" % (json.dumps(text, ensure_ascii=False), nth))
    if not pos:
        return "not found: " + text
    x, y, tag, n = pos
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        c.call("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left",
                                            "clickCount": 1, "buttons": 1 if t != "mouseReleased" else 0})
    return "clicked %s at %s,%s (cands=%s)" % (tag, round(x), round(y), n)


time.sleep(1)
print("settings:", click_by_text("设置"))
time.sleep(2.5)
print(ev("(document.body.innerText||'').slice(0,120).replace(/\\n/g,' | ')"))
print("models tab:", click_by_text("模型"))
time.sleep(2.5)
txt = ev("(function(){var m=document.querySelector('[role=\"dialog\"], .agy-settings, main'); return (m||document.body).innerText;})()")
print("---- panel text ----")
print(txt[:1200] if isinstance(txt, str) else txt)
res = c.call("Page.captureScreenshot", {"format": "png"}, timeout=60)
open(OUT, "wb").write(base64.b64decode(res["data"]))
print("shot ->", OUT, os.path.getsize(OUT))
c.ws.close()
