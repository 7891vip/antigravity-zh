import sys, json, re
sys.path.insert(0, r"D:\UserData\下载\antigravity-zh\_work")
import ui

MIXED = r"""(function(){
  var out={};
  var w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  var n=w.nextNode();
  while(n){
    var v=(n.nodeValue||'').trim().replace(/\s+/g,' ');
    if(v && /[\u4e00-\u9fff]/.test(v) && /[A-Za-z]{3,}/.test(v) && v.length<120){
      out[v]=(out[v]||0)+1;
    }
    n=w.nextNode();
  }
  return out;
})()"""

if __name__ == "__main__":
    data = ui.run(MIXED) or {}
    print("== mixed %d ==" % len(data))
    for k in sorted(data, key=lambda x: -data[x]):
        print("%3d | %s" % (data[k], k))
