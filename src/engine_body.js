/**
 * Antigravity 简体中文汉化引擎（DOM 动态注入版）
 * 运行于 preload 隔离世界，仅操作 DOM 文本与常见属性，不触碰任何应用逻辑。
 */
(function () {
  "use strict";

  var HOST_OK = /^(127\.0\.0\.1|localhost|\[::1\])$/i.test(location.hostname);
  if (!HOST_OK) return;

  var CJK = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/;
  var LATIN = /[A-Za-z]/;
  var SKIP_TEXT_SELECTOR =
    "pre,code,kbd,samp,textarea,[contenteditable=''],[contenteditable='true']," +
    ".monaco-editor,.view-lines,.view-line,.inputarea,[data-zh-skip],[translate='no']," +
    "script,style,noscript";
  // 遍历时真正跳过的子树（这些容器只含代码/样式，翻译无意义且代价高）
  var HARD_SKIP_SELECTOR =
    "script,style,noscript,pre,code,kbd,samp,.monaco-editor,.view-lines,.view-line,[data-zh-skip],[translate='no']";
  var SKIP_ATTR_SELECTOR = ".monaco-editor,[data-zh-skip]";
  var ATTRS = [
    "placeholder",
    "title",
    "aria-label",
    "aria-description",
    "alt",
    "data-tooltip",
    "data-tip",
    "label"
  ];
  var ATTR_SET = Object.create(null);
  for (var ai = 0; ai < ATTRS.length; ai++) ATTR_SET[ATTRS[ai]] = 1;

  var PHRASE_SELECTOR =
    "button,[role='button'],[role='menuitem'],[role='menuitemcheckbox'],[role='menuitemradio']," +
    "[role='tab'],[role='option'],[role='tooltip'],[role='listbox'],option,label,legend,th," +
    "h1,h2,h3,h4,h5,h6,a,[role='link']";

  var MAX_TEXT = 180;

  /* ---------------------------------------------------------------- lookup */

  var dict = DICT; // 由构建脚本注入
  var RULES = __RULES__; // 由构建脚本注入（动态句式）
  var lower = Object.create(null);
  for (var k in dict) {
    if (!Object.prototype.hasOwnProperty.call(dict, k)) continue;
    var lk = k.toLowerCase();
    if (lower[lk] === undefined) lower[lk] = dict[k];
  }

  // 短语表：仅用于按钮/菜单等界面元素，长词优先
  var phraseKeys = [];
  for (var pk in dict) {
    if (!Object.prototype.hasOwnProperty.call(dict, pk)) continue;
    if (pk.length >= 4 && pk.length <= 40 && /\s/.test(pk) && !/[{}<>]/.test(pk)) {
      phraseKeys.push(pk);
    }
  }
  phraseKeys.sort(function (a, b) {
    return b.length - a.length;
  });
  var PHRASE_RE = phraseKeys.length
    ? new RegExp("(?<![A-Za-z0-9_])(" + phraseKeys.map(escapeRe).join("|") + ")(?![A-Za-z0-9_])", "g")
    : null;

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function normalizeKey(core) {
    // “Loading...” 与 “Loading…” 统一
    return core.replace(/\.\.\.$/, "…");
  }

  function exactTranslate(core) {
    var out = dict[core];
    if (out !== undefined) return out;
    var norm = normalizeKey(core);
    if (norm !== core) {
      out = dict[norm];
      if (out !== undefined) return out;
    }
    out = lower[core.toLowerCase()];
    if (out !== undefined) return out;
    out = lower[norm.toLowerCase()];
    if (out !== undefined) return out;
    // 处理 “Key:” 形式
    if (/:$/.test(core)) {
      var base = core.slice(0, -1);
      out = dict[base] || lower[base.toLowerCase()];
      if (out !== undefined) return out + "：";
    }
    // 动态句式（正则）
    for (var ri = 0; ri < RULES.length; ri++) {
      var re = RULES[ri][0];
      re.lastIndex = 0;
      if (re.test(core)) {
        re.lastIndex = 0;
        var rep = core.replace(re, RULES[ri][1]);
        if (rep !== core) return rep;
      }
    }
    // “Failed to X / Could not X / X is required” 组合式
    var m = /^(Failed to|Could not|Unable to)\s+(.+)$/.exec(core);
    if (m) {
      var rest = dict[m[2]] || lower[m[2].toLowerCase()];
      if (rest !== undefined) return m[1] === "Failed to" ? rest + "失败" : "无法" + rest;
    }
    m = /^(.+)\s+is required$/.exec(core);
    if (m) {
      var sub = dict[m[1]] || lower[m[1].toLowerCase()];
      if (sub !== undefined) return sub + "为必填项";
    }
    return undefined;
  }

  function phraseTranslate(core) {
    if (!PHRASE_RE) return undefined;
    if (!LATIN.test(core)) return undefined;
    if (core.length > 64) return undefined;
    if (/[\n\r]/.test(core)) return undefined;
    if (/[{}]|=|=>|function\s|import\s|const\s/.test(core)) return undefined;
    PHRASE_RE.lastIndex = 0;
    if (!PHRASE_RE.test(core)) return undefined;
    PHRASE_RE.lastIndex = 0;
    return core.replace(PHRASE_RE, function (m) {
      return dict[m] !== undefined ? dict[m] : m;
    });
  }

  /* ------------------------------------------------------------- DOM utils */

  var skipTextCache = new WeakMap();
  var skipAttrCache = new WeakMap();

  function insideSkipped(el, sel, cache) {
    var chain = [];
    var cur = el;
    var hit = false;
    while (cur && cur.nodeType === 1) {
      var cached = cache.get(cur);
      if (cached !== undefined) {
        hit = cached;
        break;
      }
      chain.push(cur);
      if (cur.matches && cur.matches(sel)) {
        hit = true;
        break;
      }
      cur = cur.parentNode;
      if (cur === document.documentElement) {
        if (cur.matches && cur.matches(sel)) hit = true;
        break;
      }
    }
    for (var i = 0; i < chain.length; i++) cache.set(chain[i], hit);
    return hit;
  }

  var ourTextValue = new WeakMap();
  var ourAttrValue = new WeakMap();
  var stats = { text: 0, attr: 0, missing: 0 };
  var missingSamples = Object.create(null);
  var missingCount = 0;

  function recordMissing(core) {
    if (CJK.test(core)) return;
    if (core.length > 90) return;
    if (missingSamples[core]) return;
    missingSamples[core] = 1;
    missingCount++;
  }

  function setText(node, lead, core, tail, out) {
    var next = lead + out + tail;
    var prev = node.nodeValue;
    if (prev === next) return false;
    ourTextValue.set(node, next);
    node.nodeValue = next;
    stats.text++;
    return true;
  }

  function handleText(node, allowPhrase) {
    var v = node.nodeValue;
    if (!v || v.length > MAX_TEXT) return;
    if (!LATIN.test(v)) return;
    var parent = node.parentNode;
    if (!parent) return;
    if (parent.nodeType === 1 && insideSkipped(parent, SKIP_TEXT_SELECTOR, skipTextCache)) return;

    var lead = v.match(/^[\s\u00a0]*/)[0];
    var tail = v.match(/[\s\u00a0]*$/)[0];
    var core = v.slice(lead.length, v.length - tail.length);
    if (!core || core.length < 2) return;

    var out = exactTranslate(core);
    if (out === undefined) {
      // 含中文的文本（例如问候语中带用户名）只允许走词典/正则规则，
      // 不做短语替换，避免二次翻译。
      if (CJK.test(core)) return;
      if (allowPhrase) out = phraseTranslate(core);
    }
    if (out === undefined) {
      recordMissing(core);
      return;
    }
    setText(node, lead, core, tail, out);
  }

  function handleAttrs(el) {
    if (!el.attributes || !el.attributes.length) return;
    if (insideSkipped(el, SKIP_ATTR_SELECTOR, skipAttrCache)) return;
    for (var i = 0; i < el.attributes.length; i++) {
      var at = el.attributes[i];
      if (!ATTR_SET[at.name]) continue;
      var v = at.value;
      if (!v || !LATIN.test(v) || v.length > MAX_TEXT) continue;
      var lead = v.match(/^[\s\u00a0]*/)[0];
      var tail = v.match(/[\s\u00a0]*$/)[0];
      var core = v.slice(lead.length, v.length - tail.length);
      if (!core || CJK.test(core)) continue;
      var out = exactTranslate(core);
      if (out === undefined) out = phraseTranslate(core);
      if (out === undefined) {
        recordMissing(core);
        continue;
      }
      var next = lead + out + tail;
      if (v === next) continue;
      var rec = ourAttrValue.get(el);
      if (!rec) {
        rec = Object.create(null);
        ourAttrValue.set(el, rec);
      }
      rec[at.name] = next;
      try {
        el.setAttribute(at.name, next);
      } catch (e) {
        /* ignore */
      }
      stats.attr++;
    }
  }

  /* --------------------------------------------------------------- batching */

  var pending = new Set();
  var scheduled = false;
  var dbg = { sweep: 0, seen: 0, texts: 0, flush: 0, items: 0, recs: 0, err: "", attached: 0 };

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(flush, 0);
  }

  function flush() {
    scheduled = false;
    dbg.flush++;
    var t0 = performance.now ? performance.now() : Date.now();
    var items;
    try {
      items = Array.from(pending);
    } catch (e) {
      dbg.err = "flush:" + (e && e.message);
      return;
    }
    dbg.items += items.length;
    pending.clear();
    var i = 0;
    for (; i < items.length; i++) {
      var n = items[i];
      try {
        if (n.nodeType === 3) handleText(n, true);
        else if (n.nodeType === 1) {
          handleAttrs(n);
          collectSubtree(n);
        }
      } catch (e) {
        /* ignore single node failures */
      }
      var now = performance.now ? performance.now() : Date.now();
      if (now - t0 > 12) {
        for (var j = i + 1; j < items.length; j++) pending.add(items[j]);
        schedule();
        return;
      }
    }
    if (pending.size) schedule();
  }

  var walkerCache = [];

  function collectSubtree(root) {
    if (!root || !root.isConnected) return;
    dbg.sweep++;
    try {
      var doc = root.ownerDocument || document;
      var tw = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
        acceptNode: function (node) {
          if (node.nodeType === 1 && node.matches && node.matches(HARD_SKIP_SELECTOR)) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var guard = 0;
      var node = tw.nextNode();
      while (node && guard++ < 4000) {
        dbg.seen++;
        if (node.nodeType === 3) {
          dbg.texts++;
          pending.add(node);
        } else {
          handleAttrs(node);
          if (node.shadowRoot) collectSubtree(node.shadowRoot);
        }
        node = tw.nextNode();
      }
    } catch (e) {
      dbg.err = "sweep:" + (e && (e.name + ":" + e.message));
    }
  }

  /* -------------------------------------------------------------- observer */

  var mo = new MutationObserver(function (records) {
    var added = false;
    dbg.recs += records.length;
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if (r.type === "characterData") {
        var t = r.target;
        if (ourTextValue.get(t) === t.nodeValue) continue;
        pending.add(t);
        added = true;
      } else if (r.type === "attributes") {
        var el = r.target;
        var rec = ourAttrValue.get(el);
        if (rec && rec[r.attributeName] !== undefined && el.getAttribute(r.attributeName) === rec[r.attributeName]) {
          continue;
        }
        pending.add(el);
        added = true;
      } else if (r.type === "childList") {
        var nodes = r.addedNodes;
        for (var j = 0; j < nodes.length; j++) {
          var n = nodes[j];
          if (n.nodeType === 3) {
            pending.add(n);
            added = true;
          } else if (n.nodeType === 1) {
            pending.add(n);
            added = true;
          }
        }
      }
    }
    if (added) schedule();
  });

  function observe(root) {
    try {
      mo.observe(root, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ATTRS
      });
    } catch (e) {
      /* ignore */
    }
  }

  /* ---------------------------------------------------------------- frames */

  var attachedFrames = new WeakSet();

  function attachFrames() {
    var frames = document.querySelectorAll("iframe,frame");
    for (var i = 0; i < frames.length; i++) {
      var f = frames[i];
      if (attachedFrames.has(f)) continue;
      try {
        var doc = f.contentDocument;
        if (!doc || !doc.documentElement) continue;
        attachedFrames.add(f);
        observe(doc.documentElement);
        collectSubtree(doc.documentElement);
        schedule();
      } catch (e) {
        /* cross-origin iframe: skip */
      }
    }
  }

  /* ----------------------------------------------------------------- stats */

  var statEl = null;

  function publishStats() {
    try {
      if (!statEl || !statEl.isConnected) {
        statEl = document.createElement("div");
        statEl.id = "__agy_zh_stats";
        statEl.hidden = true;
        (document.body || document.documentElement).appendChild(statEl);
      }
      var top = Object.keys(missingSamples).slice(0, 400);
      statEl.setAttribute(
        "data-zh",
        JSON.stringify({ text: stats.text, attr: stats.attr, missing: missingCount, dbg: dbg, samples: top })
      );
    } catch (e) {
      /* ignore */
    }
  }

  /* ------------------------------------------------------------------ boot */

  var started = false;

  function start() {
    if (started) return;
    var root = document.documentElement;
    if (!root) return;
    started = true;
    try {
      observe(root);
      collectSubtree(root);
      schedule();
      attachFrames();
    } catch (e) {
      dbg.err = "start:" + (e && (e.name + ":" + e.message));
    }
    // 首屏后再补扫几轮，防止框架晚于 preload 初始化
    var ticks = 0;
    var timer = setInterval(function () {
      ticks++;
      try {
        attachFrames();
        if (document.documentElement) collectSubtree(document.documentElement);
        publishStats();
      } catch (e) {
        /* ignore */
      }
      if (ticks > 40) clearInterval(timer);
    }, 500);
  }

  function tryStart() {
    if (document.documentElement) start();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryStart, { once: true });
    // 尽早介入，避免首屏闪烁
    var early = new MutationObserver(function () {
      if (document.documentElement) {
        early.disconnect();
        start();
      }
    });
    early.observe(document, { childList: true, subtree: false });
  } else {
    tryStart();
  }
  window.addEventListener("load", function () {
    start();
    attachFrames();
  });
})();
