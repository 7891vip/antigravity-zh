import sys, json, re
sys.path.insert(0, r"D:\UserData\下载\antigravity-zh\_work")
import ui

SCAN = r"""(function(){
  var CJK=/[\u4e00-\u9fff]/;
  var out={};
  var w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  var n=w.nextNode();
  while(n){
    var v=n.nodeValue;
    if(v && /[A-Za-z]{2}/.test(v) && !CJK.test(v)){
      var t=v.trim().replace(/\s+/g,' ');
      if(t && t.length>=2 && t.length<=110){
        var el=n.parentNode;
        var chain=[]; var c=el;
        while(c && c.nodeType===1 && chain.length<3){ chain.push(c.tagName+(c.className?'.'+String(c.className).split(' ')[0].slice(0,20):'')); c=c.parentNode; }
        var key=t;
        if(!out[key]) out[key]={n:0, where:chain.join('<')};
        out[key].n++;
      }
    }
    n=w.nextNode();
  }
  // attributes
  ['placeholder','title','aria-label','aria-description','alt'].forEach(function(a){
    Array.from(document.querySelectorAll('['+a+']')).forEach(function(el){
      var v=el.getAttribute(a);
      if(v && /[A-Za-z]{2}/.test(v) && !CJK.test(v)){
        var t=v.trim().replace(/\s+/g,' ');
        if(t && t.length>=2 && t.length<=110){
          var key=t;
          if(!out[key]) out[key]={n:0, where:'@'+a+':'+el.tagName};
          out[key].n++;
        }
      }
    });
  });
  return out;
})()"""


def scan(label=""):
    data = ui.run(SCAN) or {}
    print("== %s: %d untranslated ==" % (label, len(data)))
    for k in sorted(data, key=lambda x: -data[x]["n"]):
        print("%3d | %-60s | %s" % (data[k]["n"], k, data[k]["where"]))
    return data


if __name__ == "__main__":
    scan(sys.argv[1] if len(sys.argv) > 1 else "")
