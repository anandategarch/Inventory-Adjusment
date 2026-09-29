"""
unduh_xls_loop.py  (v7 - FULL SPEED)
- TANPA delay tiruan-manusia; hanya wait fungsional (event-driven) + margin render tipis.
- Suffix Keterangan dari kolom grid saat scroll (fallback textarea detail).
- Cetak: Ctrl+P dulu, tombol Cetak fallback, retry Escape+Ctrl+P.
- Circuit breaker + katalog error + rekap akhir.
"""
import os
import re
import sys
import time
import socket
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException, StaleElementReferenceException, ElementClickInterceptedException,
)

DEBUG_PORT = 9222
MAX_ROWS = 0
MAX_CONSECUTIVE_FAIL = 3
DELAY_BETWEEN_TRANSACTIONS = 1.5  # seconds — prevent Accurate rate-limit after 4+ rapid prints
                                   # (was 2.5; trimmed to 1.5 — still safe, JS clickSeq + faster
                                   # detail detection recover headroom)
HARD_RESET_EVERY_N = 4  # more frequent — E_ROW can happen at #5, #7 (before #8)
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
NOMOR_RE = re.compile(r"(?:IA\.\d{4}\.\d{2}\.\d+|DFT\.\d+)")

ERROR_CATALOG = {
    "E_LIST": ("Grid list tidak ditemukan.", "Pastikan tab Penyesuaian Persediaan terbuka & login aktif."),
    "E_ROW": ("Baris transaksi tidak ditemukan / tidak bisa diklik.", "Grid mungkin belum selesai render. Coba jalankan ulang."),
    "E_DETAIL": ("Tab detail transaksi tidak terbuka.", "Klik manual baris sekali untuk memastikan halaman responsif."),
    "E_PRINT": ("Overlay report tidak muncul.", "Pastikan fokus di halaman detail; coba ulang siklus."),
    "E_UNDUH": ("Tombol Unduh XLS hilang.", "Overlay mungkin tertutup sendiri. Coba jalankan ulang."),
    "E_DOWNLOAD": ("File XLS tidak selesai diunduh.", f"Cek folder {DOWNLOAD_DIR} dan setting download Chrome."),
    "E_CLOSE_TAB": ("Tab detail masih terbuka.", "Tutup manual sekali; program recovery di siklus berikutnya."),
    "E_UNEXPECTED": ("Kesalahan tak terduga.", "Program recovery otomatis; bila berulang, laporkan."),
    "FATAL-LOOP": ("Kegagalan beruntun terdeteksi.", "Periksa Chrome & login Accurate, lalu jalankan ulang."),
}

class AppError(Exception):
    def __init__(self, code, msg=""):
        self.code = code
        self.msg = msg
        super().__init__(f"{code}: {msg}")

# Margin render tipis (BUKAN mimicry) — jaga klik tidak mendahului DOM
def settle(s=0.1):
    time.sleep(s)

def say(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {msg}")
    sys.stdout.flush()

def say_section(title):
    """Print a major section header (clean style, no === separators)."""
    say(f"── {title} ──")

def say_trans_header(seq, total, kode):
    """Print a per-transaction header."""
    say(f"\u2500\u2500 [{seq}/{total}] {kode} " + "\u2500" * max(0, 40 - len(f"[{seq}/{total}] {kode}")))

def say_step(label, status="OK"):
    """Print a step with aligned label + status."""
    dots = max(2, 35 - len(label))
    say(f"  {label}{'.' * dots} {status}")

def say_summary_box(lines):
    """Print a summary (clean style, no === box)."""
    say("── RINGKASAN ──")
    for line in lines:
        say(f" {line}")

# ============================================================
# JS HELPERS
# ============================================================
JS_VIS = """
function vis(el){
  if (!el || !(el instanceof Element)) return false;
  if (el.disabled) return false;
  const st = window.getComputedStyle(el);
  if (!st) return false;
  if (st.display==='none'||st.visibility==='hidden') return false;
  if (parseFloat(st.opacity)===0) return false;
  const r = el.getBoundingClientRect();
  return r.width>0 && r.height>0;
}
"""

JS_RENDERED_ROWS = """
return (function(){
  var re = /(?:IA\\.\\d{4}\\.\\d{2}\\.\\d+|DFT\\.\\d+)/;
  var headers = document.querySelectorAll('.slick-header-column');
  var ketIdx = -1, nomIdx = -1;
  for (var i=0;i<headers.length;i++){
    var ht = (headers[i].innerText||'').trim().toUpperCase();
    if (ketIdx === -1 && ht.includes('KETERANGAN')) ketIdx = i;
    if (nomIdx === -1 && ht.includes('NOMOR')) nomIdx = i;
  }
  var out = [];
  document.querySelectorAll('.slick-row').forEach(function(r){
    var cells = r.querySelectorAll('.slick-cell');
    var nomor = null, ket = null;
    if (nomIdx >= 0 && cells[nomIdx]) nomor = (cells[nomIdx].innerText||'').trim();
    if (!nomor || !re.test(nomor)) {
      var m = (r.innerText||'').match(re);
      nomor = m ? m[0] : null;
    }
    if (ketIdx >= 0 && cells[ketIdx]) ket = (cells[ketIdx].innerText||'').trim();
    if (nomor) out.push({nomor: nomor, ket: ket || ''});
  });
  return out;
})()
"""

JS_GET_VP = """
return (function(){
  var vp = document.querySelector('.slick-viewport');
  if (!vp) return null;
  var rows = document.querySelectorAll('.slick-row');
  var h = rows.length ? rows[0].getBoundingClientRect().height : 44;
  return {st: vp.scrollTop, sh: vp.scrollHeight, ch: vp.clientHeight, h: h};
})()
"""

JS_SET_SCROLL = """
return (function(val){
  var vp = document.querySelector('.slick-viewport');
  if (!vp) return false;
  vp.scrollTop = val;
  return true;
})(arguments[0])
"""

JS_FIND_MARK = JS_VIS + """
return (function(txt, exact){
  const ATTR='data-fl-target';
  const up = txt.toUpperCase();
  function scan(doc, path){
    const els = doc.querySelectorAll('button, a, span, div, li, label, input[type="button"]');
    for (const el of els){
      if (!vis(el)) continue;
      const t = (el.innerText||el.textContent||'').trim();
      const ti = (el.getAttribute && (el.getAttribute('title')||'')) || '';
      const ok = exact ? (t.toUpperCase()===up)
                       : ((t && t.toUpperCase().includes(up) && t.length<60) || (ti && ti.toUpperCase().includes(up)));
      if (ok){
        el.setAttribute(ATTR,'1');
        return {path:path, text:t.slice(0,60), html:(el.outerHTML||'').slice(0,400)};
      }
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(!d) continue; const r=scan(d, path.concat([i])); if(r) return r; }catch(e){}
    }
    return null;
  }
  return scan(document, []);
})(arguments[0], arguments[1])
"""

JS_FIND_PRINT = JS_VIS + """
return (function(){
  const ATTR='data-fl-target';
  function scan(doc, path){
    // PRIMARY: find the print ICON directly and mark IT (not a container).
    // The OLD logic matched the first div/span/button that CONTAINED a print
    // icon as a descendant — which was the OUTER container (e.g. .form-toolbar,
    // a 65x370 div). Clicking the container dispatches click on the container;
    // events bubble UP (to parents), NOT DOWN (to children), so the handler
    // bound on the actual button (.tile.dropdown-toggle, a CHILD of the
    // container) never fired → overlay never opened (root cause of the DFT
    // print failure — NOT an isTrusted issue as I previously concluded).
    // Diagnostic confirmed: Accurate's print button is
    //   <i id="btnPrint" class="icn-navigation-printer"> inside
    //   .tile.dropdown-toggle. Marking the ICON and clicking it makes the
    //   click bubble UP through .tile-content.icon → .tile.dropdown-toggle
    //   → handler fires → report overlay opens. Same dispatch path as a
    //   manual click; synthetic (isTrusted=false) works (proven by the
    //   __dg.dl console macro clicking "Unduh XLS" successfully).
    const iconSel = '#btnPrint, i[class*="print"], i.icon-print, i[class*="icon-print"], [class*="icon-print"]';
    const icons = doc.querySelectorAll(iconSel);
    for (let i = 0; i < icons.length; i++){
      const icon = icons[i];
      if (!vis(icon)) continue;
      icon.setAttribute(ATTR,'1');
      return {path:path, text:(icon.getAttribute('title')||'print-icon').slice(0,60), html:(icon.outerHTML||'').slice(0,400)};
    }
    // FALLBACK: text "CETAK" / class "PRINT" (for pages without a print icon).
    // Removed the old 'hasPrintIcon && text<20' check — that was the bug (it
    // matched outer containers). Now only matches elements whose OWN text/title
    // says CETAK or whose OWN class says PRINT.
    const cands = doc.querySelectorAll('button, a, span, div');
    for (let i = 0; i < cands.length; i++){
      const el = cands[i];
      if (!vis(el)) continue;
      const ti = (el.getAttribute('title')||'').toUpperCase();
      const txt = (el.innerText||'').trim().toUpperCase();
      const cls = (el.className||'').toString().toUpperCase();
      const isPrintBtn = ti.includes('CETAK') || txt==='CETAK' || txt.includes('CETAK') || cls.includes('PRINT');
      if (isPrintBtn){
        el.setAttribute(ATTR,'1');
        return {path:path, text:(el.innerText||el.getAttribute('title')||'').slice(0,60), html:(el.outerHTML||'').slice(0,400)};
      }
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(!d) continue; const r=scan(d, path.concat([i])); if(r) return r; }catch(e){}
    }
    return null;
  }
  return scan(document, []);
})()
"""

JS_MARK_CLOSE = JS_VIS + """
return (function(nomor){
  const ATTR='data-fl-target';
  const re = /(?:IA\\.\\d{4}\\.\\d{2}\\.\\d+|DFT\\.\\d+)/;
  function scan(doc, path){
    const els = doc.querySelectorAll('li, a, div, span');
    for (const el of els){
      if (!vis(el)) continue;
      const t = (el.innerText||'').trim();
      if (!t || t.length>60) continue;
      if (nomor ? !t.includes(nomor) : !re.test(t)) continue;
      let close = el.querySelector('i[class*="cancel"], i[class*="close"], i[class*="remove"], span[class*="close"], button[class*="close"], .icon-cancel, .icon-close');
      if (!close){
        const kids = el.querySelectorAll('i, span, b, button');
        for (const k of kids){
          const kt = (k.textContent||'').trim();
          if (kt==='×' || kt==='x'){ close = k; break; }
        }
      }
      if (close){
        close.setAttribute(ATTR,'1');
        return {path:path, text:t.slice(0,60), html:(close.outerHTML||'').slice(0,300)};
      }
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(!d) continue; const r=scan(d, path.concat([i])); if(r) return r; }catch(e){}
    }
    return null;
  }
  return scan(document, []);
})(arguments[0])
"""

# Native clickSeq (pointer+mouse events) — proven reliable for Accurate's jQuery
# SPA navigation handlers (vs ActionChains which silently fails to trigger them).
# Used for the row click that opens the transaction detail tab.
JS_CLICK_ROW_SEQ = JS_VIS + """
return (function(nomor){
  function clickSeq(el){
    if (!el) return false;
    try { el.scrollIntoView({block:'center', inline:'center'}); } catch(e){ try{el.scrollIntoView();}catch(_){} }
    const init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1, composed:true};
    const types = ['pointerover','pointerenter','pointerdown','mousedown','pointerup','mouseup','click'];
    for (const t of types){
      try {
        if (t.startsWith('pointer') && typeof PointerEvent !== 'undefined') {
          el.dispatchEvent(new PointerEvent(t, Object.assign({}, init, {pointerId:1, pointerType:'mouse', isPrimary:true})));
        } else if (!t.startsWith('pointer')) {
          el.dispatchEvent(new MouseEvent(t, init));
        }
      } catch(e){}
    }
    return true;
  }
  function scan(doc){
    const rows = doc.querySelectorAll('.slick-row');
    for (const r of rows){
      if (!vis(r)) continue;
      const t = (r.innerText || r.textContent || '').trim();
      if (t.indexOf(nomor) === -1) continue;
      const cell = r.querySelector('.slick-cell') || r;
      if (clickSeq(cell)) return 'CLICKED';
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){ try{ const d=fr[i].contentDocument; if(d){ const r=scan(d); if(r) return r; } }catch(e){} }
    return null;
  }
  return scan(document);
})(arguments[0])
"""

# Detail-open detector. For approved IA, the nomor shows in an <input> (header
# number field). For DFT *drafts*, the nomor appears in a <div>/<span> (status
# text like "Draft - DFT.4519226"), NOT in an input — so we also scan visible
# text nodes. Fallback: a transaction detail form is loaded (list grid absent
# in this document) which means SPA navigated to the detail page.
JS_DETAIL_OPEN = JS_VIS + """
return (function(nomor){
  function scan(doc){
    // 1) nomor in an input value (approved IA detail page)
    const inps = doc.querySelectorAll('input');
    for (const i of inps){ if ((i.value||'').trim()===nomor && vis(i)) return true; }
    // 2) nomor in any visible short text node (DFT draft detail uses div/span)
    const els = doc.querySelectorAll('div, span, li, a, label, p, h1, h2, h3, h4');
    for (const el of els){
      if (!vis(el)) continue;
      const t = (el.innerText || el.textContent || '').trim();
      if (!t || t.length > 80) continue;
      if (t.indexOf(nomor) !== -1) return true;
    }
    // 3) detail form loaded + list grid absent in this doc (SPA navigated away)
    const hasForm = !!doc.querySelector('.transaction-form, .form-horizontal, [class*="detail-form"], .tab-content');
    const hasGrid = !!doc.querySelector('.slick-grid');
    if (hasForm && !hasGrid) return true;
    // recurse into iframes
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){ try{ const d=fr[i].contentDocument; if(d && scan(d)) return true; }catch(e){} }
    return false;
  }
  return scan(document);
})(arguments[0])
"""

JS_CLICK_INFO_TAB = JS_VIS + """
return (function(){
  function clickSeq(el){
    if (!el) return;
    const init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1};
    ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>{
      try{ el.dispatchEvent(new MouseEvent(t, init)); }catch(e){}
    });
  }
  function scan(doc){
    let el = doc.querySelector('a[title="Info lainnya"], a.left-tab[title="Info lainnya"], .icn-transaction-header');
    if (el && vis(el)) { clickSeq(el.closest('a') || el); return 'TITLE'; }
    const nodes = Array.from(doc.querySelectorAll('a, span, div, li, label')).filter(x=>{
      const t = (x.innerText || x.textContent || '').trim();
      return t === 'Info lainnya' && vis(x);
    });
    if (nodes.length){
      nodes.sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length);
      clickSeq(nodes[0]);
      return 'TEXT';
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(d){ const r=scan(d); if(r) return r; } }catch(e){}
    }
    return null;
  }
  return scan(document);
})()
"""

JS_READ_KETERANGAN = JS_VIS + """
return (function(){
  function scan(doc){
    const tas = Array.from(doc.querySelectorAll('textarea'));
    for (const ta of tas){ if (vis(ta) && (ta.value||'').trim()) return (ta.value||'').trim(); }
    for (const ta of tas){ if (vis(ta)) return (ta.value||'').trim(); }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(d){ const r=scan(d); if(r) return r; } }catch(e){}
    }
    return null;
  }
  return scan(document);
})()
"""

# Native clickSeq on a specific WebElement (passed as arguments[0]).
# Same dispatch sequence as JS_CLICK_ROW_SEQ — proven reliable for Accurate's
# jQuery click handlers (vs ActionChains which silently fails to fire them).
# Used by _click_print_button to click the "Cetak" button reliably.
JS_CLICK_SEQ_EL = """
return (function(el){
  if (!el) return false;
  try { el.scrollIntoView({block:'center', inline:'center'}); } catch(e){ try{el.scrollIntoView();}catch(_){} }
  const init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1, composed:true};
  const types = ['pointerover','pointerenter','pointerdown','mousedown','pointerup','mouseup','click'];
  for (const t of types){
    try {
      if (t.startsWith('pointer') && typeof PointerEvent !== 'undefined') {
        el.dispatchEvent(new PointerEvent(t, Object.assign({}, init, {pointerId:1, pointerType:'mouse', isPrimary:true})));
      } else if (!t.startsWith('pointer')) {
        el.dispatchEvent(new MouseEvent(t, init));
      }
    } catch(e){}
  }
  return true;
})(arguments[0])
"""

# Dispatch Ctrl+P as a real JS KeyboardEvent to the top document AND every
# same-origin iframe document. Accurate's Ctrl+P handler (the one that opens
# the report overlay instead of the native print dialog) is bound on `keydown`
# in the DETAIL FORM'S IFRAME — not the top document. ActionChains(Ctrl+P)
# sends the key to whatever has focus (usually top body after _focus_form
# falls back), so the iframe handler never receives it. Dispatching the event
# directly to all documents guarantees the handler fires wherever it's bound.
# Diagnostic confirmed: manual Ctrl+P opens `metro window-overlay` with
# "UNDUH XLS" button — this JS dispatch replicates that path.
JS_DISPATCH_CTRL_P = """
return (function(){
  function dispatch(doc){
    let down, up;
    try {
      down = new KeyboardEvent('keydown', {key:'p', code:'KeyP', keyCode:80, which:80, ctrlKey:true, bubbles:true, cancelable:true, composed:true});
      up   = new KeyboardEvent('keyup',   {key:'p', code:'KeyP', keyCode:80, which:80, ctrlKey:true, bubbles:true, cancelable:true, composed:true});
    } catch(e) {
      down = new Event('keydown', {bubbles:true, cancelable:true});
      up   = new Event('keyup',   {bubbles:true, cancelable:true});
    }
    // Force keyCode/which/ctrlKey readable (some jQuery code reads these)
    try { Object.defineProperties(down, {keyCode:{get:()=>80}, which:{get:()=>80}, ctrlKey:{get:()=>true}, key:{get:()=>'p'}}); } catch(e){}
    try { Object.defineProperties(up,   {keyCode:{get:()=>80}, which:{get:()=>80}, ctrlKey:{get:()=>true}, key:{get:()=>'p'}}); } catch(e){}
    try { doc.dispatchEvent(down); } catch(e){}
    try { doc.dispatchEvent(up); } catch(e){}
  }
  dispatch(document);
  const fr = document.querySelectorAll('iframe, frame');
  for (let i=0;i<fr.length;i++){
    try { if (fr[i].contentDocument) dispatch(fr[i].contentDocument); } catch(e){}
  }
  return true;
})()
"""

# Find the "#Penyesuaian Persediaan" menu item in the dropdown that appears
# after clicking #btnPrint. The dropdown is a <ul class="dropdown-menu"> with
# <li><a data-bind="click: click"> items. CRITICAL: search <A> FIRST (the <A>
# has the KO click handler) — not <LI> (the <A>'s parent). Clicking <LI>
# dispatches events on the <LI>, which bubble UP to <UL>, NOT DOWN to <A> →
# handler never fires → overlay never opens (this was the v5 console bug).
# If only <LI> matches, walk DOWN to find the <A> inside it.
# Recorder confirmed: <a data-bind="click: click"><span>#Penyesuaian Persediaan</span></a>
JS_FIND_DROPDOWN_ITEM = JS_VIS + """
return (function(keyword){
  const ATTR='data-fl-target';
  const want = String(keyword||'').toUpperCase();
  function scan(doc, path){
    // 1. <A> inside .dropdown-menu (has KO click handler)
    const menus = doc.querySelectorAll('.dropdown-menu, ul[class*="dropdown-menu"]');
    for (let mi=0; mi<menus.length; mi++){
      const menu = menus[mi];
      if (!vis(menu)) continue;
      const links = menu.querySelectorAll('a');
      for (const el of links){
        if (!vis(el)) continue;
        const t = (el.innerText||'').trim().toUpperCase();
        if (!t || t.length > 60) continue;
        if (t.indexOf(want) !== -1){
          el.setAttribute(ATTR,'1');
          return {path:path, text:(el.innerText||'').trim().slice(0,60), html:(el.outerHTML||'').slice(0,400)};
        }
      }
      // 2. <LI> fallback → walk down to <A>
      const items = menu.querySelectorAll('li');
      for (const el of items){
        if (!vis(el)) continue;
        const t = (el.innerText||'').trim().toUpperCase();
        if (!t || t.length > 60) continue;
        if (t.indexOf(want) !== -1){
          const a = el.querySelector('a');
          if (a && vis(a)){
            a.setAttribute(ATTR,'1');
            return {path:path, text:(a.innerText||'').trim().slice(0,60), html:(a.outerHTML||'').slice(0,400)};
          }
        }
      }
    }
    // 3. Fallback: any visible <A> with text (not in grid/module-title/tab-control)
    const all = doc.querySelectorAll('a');
    for (const el of all){
      if (!vis(el)) continue;
      if (el.closest && el.closest('.slick-grid, .slick-viewport, .slick-row, .module-switcher-container, .navigation-bar, .tab-control')) continue;
      const t = (el.innerText||'').trim().toUpperCase();
      if (!t || t.length > 60) continue;
      if (t.indexOf(want) !== -1){
        el.setAttribute(ATTR,'1');
        return {path:path, text:(el.innerText||'').trim().slice(0,60), html:(el.outerHTML||'').slice(0,400)};
      }
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(!d) continue; const r=scan(d, path.concat([i])); if(r) return r; }catch(e){}
    }
    return null;
  }
  return scan(document, []);
})(arguments[0])
"""

# Click an element by its stable ID via native clickSeq. Recorder confirmed
# stable IDs: #print-preview-excel (Unduh XLS button), #print-preview-close
# (Tutup button). These IDs are stable across transactions — more reliable
# than text search (JS_FIND_MARK). Used for the download + close steps.
JS_CLICK_BY_ID = """
return (function(id){
  const el = document.getElementById(id);
  if (!el) return false;
  try { el.scrollIntoView({block:'center', inline:'center'}); } catch(e){ try{el.scrollIntoView();}catch(_){} }
  const init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1, composed:true};
  const types = ['pointerover','pointerenter','pointerdown','mousedown','pointerup','mouseup','click'];
  for (const t of types){
    try {
      if (t.startsWith('pointer') && typeof PointerEvent !== 'undefined'){
        el.dispatchEvent(new PointerEvent(t, Object.assign({}, init, {pointerId:1, pointerType:'mouse', isPrimary:true})));
      } else if (!t.startsWith('pointer')){
        el.dispatchEvent(new MouseEvent(t, init));
      }
    } catch(e){}
  }
  return true;
})(arguments[0])
"""

# ============================================================
# UTILITAS
# ============================================================
def sanitize_suffix(s):
    if not s:
        return ""
    invalid = '\\/:*?"<>|'
    out = []
    for ch in s:
        out.append("_" if ch in invalid else ch)
    clean = "".join(out).strip().rstrip(".")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def rename_with_suffix(path, suffix):
    if not suffix:
        return path
    folder = os.path.dirname(path)
    base = os.path.basename(path)
    root, ext = os.path.splitext(base)
    newname = f"{root}_{suffix}{ext}"
    target = os.path.join(folder, newname)
    if os.path.exists(target):
        i = 1
        while os.path.exists(target):
            target = os.path.join(folder, f"{root}_{suffix}_{i}{ext}")
            i += 1
    try:
        os.rename(path, target)
        return target
    except Exception:
        return path

def connect_chrome():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", DEBUG_PORT)) != 0:
            raise AppError("E_LIST", f"port debugging {DEBUG_PORT} tidak aktif")
    opt = Options()
    opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    return webdriver.Chrome(options=opt)

def switch_path(driver, path):
    driver.switch_to.default_content()
    for i in (path or []):
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        if 0 <= i < len(frames):
            driver.switch_to.frame(frames[i])
        else:
            return False
    return True

def find_list_frame(driver, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        driver.switch_to.default_content()
        if len(driver.find_elements(By.CSS_SELECTOR, ".slick-viewport")) > 0:
            return True
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                if len(driver.find_elements(By.CSS_SELECTOR, ".slick-viewport")) > 0:
                    return True
            except Exception:
                continue
        driver.switch_to.default_content()
        time.sleep(0.25)
    return False

def smart_click(driver, el, retries=3):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
            ActionChains(driver).move_to_element(el).click().perform()
            return "ACTIONCHAINS"
        except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
            time.sleep(0.3)
    try:
        el.click()
        return "ELCLICK"
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
            return "JSCLICK"
        except Exception:
            return "GAGAL"

def find_marked(driver, path, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if switch_path(driver, path):
            for el in driver.find_elements(By.CSS_SELECTOR, '[data-fl-target="1"]'):
                try:
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
        time.sleep(0.2)
    return None

def clear_mark(driver, path):
    try:
        if switch_path(driver, path):
            driver.execute_script("document.querySelectorAll('[data-fl-target]').forEach(e=>e.removeAttribute('data-fl-target'));")
    except Exception:
        pass

def wait_detail_open(driver, nomor, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            driver.switch_to.default_content()
            if driver.execute_script(JS_DETAIL_OPEN, nomor):
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def wait_detail_closed(driver, nomor, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            driver.switch_to.default_content()
            if find_list_frame(driver, timeout=1):
                return True
            if not driver.execute_script(JS_DETAIL_OPEN, nomor):
                return True
        except Exception:
            return True
        time.sleep(0.25)
    return False

def wait_report_overlay(driver, timeout=20):
    # Check #print-preview-excel FIRST (stable id from recorder — more reliable
    # than text search). Fall back to JS_FIND_MARK("Unduh XLS") text search.
    # v6 console found #print-preview-excel in ~0.8s after menu item click.
    # Returns a mark dict {path, text, html} compatible with find_marked + smart_click.
    end = time.time() + timeout
    while time.time() < end:
        try:
            driver.switch_to.default_content()
            # 1. Check #print-preview-excel (stable id) via a quick JS that marks it
            #    using the same ATTR as JS_FIND_MARK so find_marked works.
            found = driver.execute_script("""
                const el = document.getElementById('print-preview-excel');
                if (el){
                    const st = window.getComputedStyle(el);
                    if (st.display !== 'none' && st.visibility !== 'hidden' && parseFloat(st.opacity) !== 0){
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0){
                            el.setAttribute('data-fl-target','1');
                            return {path:[], text:(el.innerText||'').slice(0,60), html:(el.outerHTML||'').slice(0,400)};
                        }
                    }
                }
                return null;
            """)
            if found:
                return found
        except Exception:
            pass
        # 2. Fallback: text search "Unduh XLS"
        try:
            driver.switch_to.default_content()
            ux = driver.execute_script(JS_FIND_MARK, "Unduh XLS", False)
            if ux:
                return ux
        except Exception:
            pass
        time.sleep(0.25)
    return None

def snapshot_downloads():
    try:
        return set(os.listdir(DOWNLOAD_DIR))
    except Exception:
        return set()

def wait_new_download(before, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            cur = set(os.listdir(DOWNLOAD_DIR))
        except Exception:
            time.sleep(0.25)
            continue
        pending = [f for f in cur if f.endswith(('.crdownload', '.part', '.tmp'))]
        new = [f for f in (cur - before)
               if not f.endswith(('.crdownload', '.part', '.tmp'))
               and f.lower().endswith(('.xls', '.xlsx'))]
        if new and not pending:
            cand = sorted(new, key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_DIR, f)))[-1]
            p = os.path.join(DOWNLOAD_DIR, cand)
            try:
                s1 = os.path.getsize(p)
                time.sleep(0.4)
                s2 = os.path.getsize(p)
                if s1 == s2 and s1 > 0:
                    return cand
            except Exception:
                pass
        time.sleep(0.25)
    return None

# ============================================================
# RECOVERY & NAVIGASI
# ============================================================
def recover_to_list(driver):
    for _ in range(2):
        try:
            driver.switch_to.default_content()
            tp = driver.execute_script(JS_FIND_MARK, "Tutup", True)
        except Exception:
            tp = None
        if not tp:
            break
        el = find_marked(driver, tp["path"], timeout=3)
        if el:
            smart_click(driver, el)
        clear_mark(driver, tp["path"])
        time.sleep(0.3)
    try:
        driver.switch_to.default_content()
        cl = driver.execute_script(JS_MARK_CLOSE, "")
    except Exception:
        cl = None
    if cl:
        el = find_marked(driver, cl["path"], timeout=3)
        if el:
            smart_click(driver, el)
            settle(0.15)
        clear_mark(driver, cl["path"])
    return find_list_frame(driver, timeout=8)

def hard_reset_list(driver, seq=None, kind="scheduled"):
    """Hard reset: click btnRefresh to reload the list page.

    Resets SlickGrid stylesheet (fixes 'Cannot find stylesheet' error after
    many SPA navigations) + clears 173+ residual overlay elements from DOM.

    Called every HARD_RESET_EVERY_N transactions to prevent grid 'mepet' issue,
    and on failure as a recovery reset before the next transaction.
    """
    if kind == "recovery":
        say("  \U0001f504 Recovery reset (gagal \u2192 reset grid)")
    elif seq is not None:
        say(f"  \U0001f504 Refresh list (reset #{seq})")
    else:
        say("  \U0001f504 Refresh list")
    try:
        switch_path(driver, [])
        # Try btnRefresh first
        btn = driver.find_element(By.CSS_SELECTOR, "button[name='btnRefresh']")
        if btn:
            smart_click(driver, btn)
            say_step("Refresh", "OK")
            time.sleep(3)  # wait for list to re-render + SlickGrid to re-init
            # Re-find the list frame (may have changed after refresh)
            if find_list_frame(driver, timeout=12):
                say_step("List siap", "OK")
            else:
                say_step("List siap", "FAIL")
            return True
    except Exception as e:
        say_step("Refresh", f"FAIL ({e})")
    # Fallback: try btnToggleList (toggle list view on/off)
    try:
        switch_path(driver, [])
        btn = driver.find_element(By.CSS_SELECTOR, "button[name='btnToggleList']")
        if btn:
            smart_click(driver, btn)
            time.sleep(2)
            smart_click(driver, btn)  # toggle back on
            time.sleep(3)
            find_list_frame(driver, timeout=12)
            say_step("Refresh (toggle)", "OK")
            return True
    except Exception as e:
        say_step("Refresh (toggle)", f"FAIL ({e})")
    return False

def collect_nomor_list(driver):
    if not find_list_frame(driver):
        return [], 44, {}
    driver.execute_script(JS_SET_SCROLL, 0)
    time.sleep(0.3)
    vp = driver.execute_script(JS_GET_VP)
    row_h = vp["h"] if vp else 44

    order, seen = [], set()
    suffix_map = {}
    stall, steps = 0, 0
    # SlickGrid uses VIRTUAL scrolling — only renders rows in the viewport (~10).
    # collect_nomor_list scrolls through + reads rendered rows at each position.
    # FIX for "40 rows but only 20 found" (grid 40+ rows):
    #   1. Smaller scroll step (half viewport, not ch-row_h) → 50% overlap between
    #      reads → no rows skipped even if one read is stale
    #   2. Longer wait after scroll (0.4s, was 0.2s) → SlickGrid has time to render
    #      the new virtual rows before JS_RENDERED_ROWS reads them
    #   3. Higher stall threshold (8, was 3) → more tolerance for slow rendering
    #   4. Re-read on stall → if first read gets 0 new rows, wait + re-read once
    #      more before counting as stall (handles temporary render delay)
    for _ in range(400):
        steps += 1
        rows = driver.execute_script(JS_RENDERED_ROWS) or []
        added = 0
        for r in rows:
            n = (r.get("nomor") or "").strip()
            if not n:
                continue
            k = (r.get("ket") or "").strip()
            if k:
                suffix_map[n] = k
            if n not in seen:
                seen.add(n)
                order.append(n)
                added += 1
        vp = driver.execute_script(JS_GET_VP)
        if not vp:
            break
        if vp["st"] + vp["ch"] >= vp["sh"] - 2:
            break
        if added == 0:
            # Re-read after a short wait — SlickGrid might still be rendering
            time.sleep(0.35)
            rows2 = driver.execute_script(JS_RENDERED_ROWS) or []
            for r in rows2:
                n = (r.get("nomor") or "").strip()
                if not n:
                    continue
                k = (r.get("ket") or "").strip()
                if k:
                    suffix_map[n] = k
                if n not in seen:
                    seen.add(n)
                    order.append(n)
                    added += 1
        if added == 0:
            stall += 1
            if stall >= 8:
                break
        else:
            stall = 0
        # Smaller step: half viewport (50% overlap) — ensures no rows skipped
        stepv = max(vp["ch"] // 2, row_h)
        driver.execute_script(JS_SET_SCROLL, vp["st"] + stepv)
        time.sleep(0.4)  # was 0.2 — give SlickGrid time to render virtual rows

    driver.execute_script(JS_SET_SCROLL, 0)
    time.sleep(0.3)
    return order, row_h, suffix_map

def find_rendered_row(driver, nomor):
    for _ in range(3):
        for r in driver.find_elements(By.CSS_SELECTOR, ".slick-row"):
            try:
                if not r.is_displayed():
                    continue
            except Exception:
                continue
            text = r.get_attribute("innerText") or r.get_attribute("textContent") or r.text or ""
            if nomor in text:
                return r
        time.sleep(0.2)
    return None

def click_row_by_nomor(driver, nomor, idx, row_h):
    # Try JS clickSeq FIRST — proven reliable for Accurate's jQuery SPA
    # navigation (ActionChains silently fails to trigger the row-click handler
    # that opens the detail tab, especially for DFT draft rows).
    try:
        res = driver.execute_script(JS_CLICK_ROW_SEQ, nomor)
        if res == "CLICKED":
            return "JSSEQ"
    except Exception:
        pass
    row = find_rendered_row(driver, nomor)
    if row:
        return smart_click(driver, row)
    driver.execute_script(JS_SET_SCROLL, idx * row_h)
    time.sleep(0.3)
    row = find_rendered_row(driver, nomor)
    if row:
        return smart_click(driver, row)
    vp = driver.execute_script(JS_GET_VP) or {"st": 0, "ch": 400}
    base = vp["st"]
    for k in range(1, 7):
        target = base + (k * vp["ch"] // 2) * (1 if k % 2 == 1 else -1)
        driver.execute_script(JS_SET_SCROLL, max(target, 0))
        time.sleep(0.3)
        row = find_rendered_row(driver, nomor)
        if row:
            return smart_click(driver, row)
    return None

# ============================================================
# BACA KETERANGAN (fallback detail)
# ============================================================
def read_keterangan_suffix(driver, timeout=8):
    try:
        driver.switch_to.default_content()
        end = time.time() + timeout
        clicks = 0
        while time.time() < end:
            raw = driver.execute_script(JS_READ_KETERANGAN)
            if raw and raw.strip():
                return sanitize_suffix(raw)
            if raw is None and clicks < 2:
                if driver.execute_script(JS_CLICK_INFO_TAB):
                    clicks += 1
                time.sleep(0.3)
                continue
            time.sleep(0.3)
        return ""
    except Exception:
        return ""

# ============================================================
# MICU CETAK (Ctrl+P dulu, tombol Cetak fallback, retry)
# ============================================================
def _focus_form(driver):
    try:
        driver.execute_script("""
            let el = document.querySelector('.form-group input, .transaction-form, .tab-content, [class*="detail"], .slick-viewport');
            if (!el) el = document.body;
            if (el) { el.focus(); el.click(); }
        """)
    except Exception:
        pass

def _click_print_button(driver):
    # 2-STEP FLOW (replicates v6 console — proven working):
    #   Step 1: click #btnPrint (icon) → opens dropdown menu
    #   Step 2: click "#Penyesuaian Persediaan" menu item (<A data-bind="click: click">)
    #           → opens report overlay
    # After this returns True, wait_report_overlay will find #print-preview-excel.
    #
    # CRITICAL: poll for #btnPrint (stable id, DETAIL toolbar print) to be VISIBLE
    # before clicking. The detail toolbar renders AFTER the nomor appears (which
    # wait_detail_open detects). Without this poll, _click_print_button might run
    # before #btnPrint is in the DOM → JS_FIND_PRINT's fallback selector
    # i[class*="print"] matches the MODULE/LIST print icon (icn-transaction-printer
    # in <nav class="horizontal-menu">) → clicks the WRONG button → list print
    # dialog → fail. This race was masked by the old 8s Ctrl+P timeout (which gave
    # the toolbar time to render). With skip_ctrl_p=True for DFT, the race is
    # exposed — so we poll #btnPrint explicitly (up to 5s).
    pr = None
    end = time.time() + 5
    while time.time() < end:
        try:
            driver.switch_to.default_content()
            # Check #btnPrint (stable id, detail toolbar) — NOT the broader
            # JS_FIND_PRINT (which falls back to module/list print icon).
            found = driver.execute_script("""
                const el = document.getElementById('btnPrint');
                if (el){
                    const st = window.getComputedStyle(el);
                    if (st.display !== 'none' && st.visibility !== 'hidden' && parseFloat(st.opacity) !== 0){
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0){
                            el.setAttribute('data-fl-target','1');
                            return {path:[], text:'btnPrint', html:(el.outerHTML||'').slice(0,400)};
                        }
                    }
                }
                return null;
            """)
            if found:
                pr = found
                break
        except Exception:
            pass
        time.sleep(0.3)
    # Fallback: old JS_FIND_PRINT (broader — only if #btnPrint not found in 5s)
    if not pr:
        try:
            driver.switch_to.default_content()
            pr = driver.execute_script(JS_FIND_PRINT)
        except Exception:
            pr = None
    if not pr:
        return False
    el = find_marked(driver, pr["path"])
    if not el:
        clear_mark(driver, pr["path"])
        return False

    # STEP 1: click #btnPrint via JS clickSeq (proven — v6 console Step 1)
    try:
        clicked = driver.execute_script(JS_CLICK_SEQ_EL, el)
        if not clicked:
            smart_click(driver, el)
    except Exception:
        smart_click(driver, el)
    clear_mark(driver, pr["path"])

    # STEP 2: poll for "#Penyesuaian Persediaan" dropdown menu item, click it.
    # The dropdown appears ~0-1s after #btnPrint click. The <A> menu item has
    # data-bind="click: click" (KO handler) — clicking it opens the overlay.
    # v6 console found it in 0-3s; timeout 8s for safety.
    end = time.time() + 8
    menu_mark = None
    while time.time() < end:
        try:
            driver.switch_to.default_content()
            menu_mark = driver.execute_script(JS_FIND_DROPDOWN_ITEM, "Penyesuaian Persediaan")
        except Exception:
            menu_mark = None
        if menu_mark:
            break
        time.sleep(0.2)
    if not menu_mark:
        return True  # btnPrint clicked but menu didn't appear — let wait_report_overlay decide

    menu_el = find_marked(driver, menu_mark["path"])
    if menu_el:
        try:
            if not driver.execute_script(JS_CLICK_SEQ_EL, menu_el):
                smart_click(driver, menu_el)
        except Exception:
            smart_click(driver, menu_el)
        clear_mark(driver, menu_mark["path"])

    return True  # overlay should now be opening — wait_report_overlay finds #print-preview-excel

def trigger_print_and_wait(driver, skip_ctrl_p=False):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    settle(0.1)
    _focus_form(driver)
    settle(0.1)

    # JS-dispatched Ctrl+P — sends a real KeyboardEvent(keydown, ctrlKey:true,
    # key:'p') to the top document AND every iframe document. Accurate's Ctrl+P
    # handler (which opens the report overlay, not native print) is bound on the
    # detail form's IFRAME — ActionChains(Ctrl+P) only reached the top document
    # body (form not found → body fallback), so the iframe handler never fired.
    # Timeout 8s (was 12s) — diagnostic shows overlay appears in ~4-5s; 8s is
    # a safe margin, saves 4s on the failed-Ctrl+P path (DFT doesn't respond to
    # Ctrl+P, falls through to the Cetak button below).
    #
    # skip_ctrl_p=True for DFT drafts: Ctrl+P doesn't trigger DFT print (proven
    # by tests — 8s wasted timeout every transaction). Skip it → go straight to
    # the Cetak button 2-step flow (#btnPrint → menu item). Saves ~8s per DFT.
    if not skip_ctrl_p:
        try:
            driver.switch_to.default_content()
            driver.execute_script(JS_DISPATCH_CTRL_P)
            ux = wait_report_overlay(driver, timeout=8)
            if ux:
                return ux, "Ctrl+P"
        except Exception:
            pass

    # Cetak button via JS clickSeq (2-step: #btnPrint → "#Penyesuaian Persediaan"
    # menu item → overlay). This is the reliable path for DFT drafts (and the
    # fallback for IA if Ctrl+P fails). Timeout 10s — overlay ~5s + margin.
    if _click_print_button(driver):
        say_step("Cetak (tombol Cetak)", "FALLBACK")
        ux = wait_report_overlay(driver, timeout=10)
        if ux:
            return ux, "tombol Cetak"

    # NOTE: removed retry Ctrl+P (user request). If Ctrl+P + Cetak button both
    # fail, retrying Ctrl+P won't help. Worst-case failure now 18s (was 26s).

    return None, None

def close_report(driver):
    # Click #print-preview-close (stable id from recorder) via JS clickSeq.
    # v6 console Step 4: closes the report overlay after download.
    # Fallback: find "Tutup" by text (JS_FIND_MARK) + smart_click.
    try:
        driver.switch_to.default_content()
        clicked = driver.execute_script(JS_CLICK_BY_ID, "print-preview-close")
        if clicked:
            settle(0.3)
            return
    except Exception:
        pass
    # Fallback: find "Tutup" by text
    try:
        driver.switch_to.default_content()
        tp = driver.execute_script(JS_FIND_MARK, "Tutup", True)
    except Exception:
        tp = None
    if not tp:
        return
    el = find_marked(driver, tp["path"], timeout=3)
    if el:
        smart_click(driver, el)
    clear_mark(driver, tp["path"])
    settle(0.15)

def close_detail_tab(driver, nomor):
    try:
        driver.switch_to.default_content()
        cl = driver.execute_script(JS_MARK_CLOSE, nomor)
    except Exception:
        cl = None
    if not cl:
        return
    el = find_marked(driver, cl["path"], timeout=3)
    if el:
        smart_click(driver, el)
    clear_mark(driver, cl["path"])

# ============================================================
# SIKLUS PER NOMOR
# ============================================================
def process_nomor(driver, nomor, seq, limit, row_h, suffix_map):
    t0 = time.time()
    say_trans_header(seq, limit, nomor)
    try:
        recover_to_list(driver)
        if not find_list_frame(driver, timeout=8):
            raise AppError("E_LIST", "grid tidak ditemukan setelah recovery")

        how = click_row_by_nomor(driver, nomor, seq - 1, row_h)
        if not how:
            raise AppError("E_ROW", f"baris {nomor} tidak ditemukan")
        say_step("Klik baris", how)

        driver.switch_to.default_content()
        if not wait_detail_open(driver, nomor, timeout=15):
            raise AppError("E_DETAIL", f"input {nomor} tidak muncul")
        say_step("Buka detail")

        say_step("Baca Keterangan")
        suffix = sanitize_suffix((suffix_map or {}).get(nomor, ""))
        if suffix:
            say(f"    {suffix}")
        else:
            suffix = read_keterangan_suffix(driver)
            if suffix:
                say(f"    {suffix} (dari detail)")
            else:
                say("    (tanpa suffix)")

        # ─── PRINT + DOWNLOAD ────────────────────────────────────────────
        # With the fixed JS_FIND_PRINT (targets the print ICON #btnPrint, not
        # the outer container), the Cetak button click now bubbles UP through
        # .tile-content.icon → .tile.dropdown-toggle → handler fires → overlay
        # opens. This works for BOTH approved IA AND DFT drafts — the previous
        # failure was a SELECTOR bug (clicking the container, not the icon),
        # NOT an isTrusted issue.
        #
        # DFT strategy: try auto-print FIRST (trigger_print_and_wait). If it
        # fails (rare — only if the icon fix is wrong), fall back to manual
        # Cetak (user clicks, Python polls for overlay 120s). Minimal risk:
        # if auto works → fully automatic (no manual step); if not → manual
        # fallback keeps the pipeline running.
        is_draft = nomor.startswith("DFT.")

        if is_draft:
            # DFT: skip Ctrl+P (doesn't trigger DFT print — 8s wasted timeout,
            # proven by tests). Go straight to the Cetak button 2-step flow
            # (#btnPrint → "#Penyesuaian Persediaan" menu item → overlay).
            # This is the proven working path (v6 console + 8/8 test success).
            ux, method = trigger_print_and_wait(driver, skip_ctrl_p=True)
            if ux:
                say_step(f"Cetak ({method})", "AUTO")
            else:
                # Auto failed → manual fallback. User clicks Cetak, Python polls.
                say("  → [DFT] Auto-cetak gagal. Klik Cetak manual di Accurate, Python tunggu overlay...")
                ux = wait_report_overlay(driver, timeout=120)
                if not ux:
                    raise AppError("E_PRINT", "overlay tidak muncul — auto & manual both failed")
                say_step("Cetak (manual)", "OK")
        else:
            # Approved IA: fully auto-print.
            ux, method = trigger_print_and_wait(driver)
            if not ux:
                raise AppError("E_PRINT", "overlay report tidak muncul")
            say_step(f"Cetak ({method})")

        # Common: click "Unduh XLS" in the overlay → wait for download
        # Use JS_CLICK_BY_ID("print-preview-excel") FIRST — stable id from
        # recorder + native clickSeq (proven in v6 console Step 3). Falls back
        # to find_marked + smart_click if the id-based click fails.
        say_step("Unduh XLS")
        before = snapshot_downloads()
        try:
            driver.switch_to.default_content()
            clicked = driver.execute_script(JS_CLICK_BY_ID, "print-preview-excel")
        except Exception:
            clicked = False
        if not clicked:
            # Fallback: find_marked + smart_click (the mark was set by wait_report_overlay)
            el = find_marked(driver, ux["path"])
            if not el:
                clear_mark(driver, ux["path"])
                raise AppError("E_UNDUH", "tombol Unduh XLS hilang")
            smart_click(driver, el)
        clear_mark(driver, ux["path"])

        fname = wait_new_download(before, timeout=90)
        if not fname:
            raise AppError("E_DOWNLOAD", "file XLS tidak selesai")

        # Common: rename with suffix + close detail + report
        original_path = os.path.join(DOWNLOAD_DIR, fname)
        final_path = rename_with_suffix(original_path, suffix)
        final_name = os.path.basename(final_path)
        say(f"  File: {final_name}")

        say_step("Tutup detail + report")
        close_report(driver)
        close_detail_tab(driver, nomor)
        if not wait_detail_closed(driver, nomor, timeout=15):
            raise AppError("E_CLOSE_TAB", f"tab detail {nomor} masih terbuka")

        dt = time.time() - t0
        say(f"  \u2705 Selesai \u2014 {dt:.1f}s")
        return True, final_name

    except AppError as e:
        penjelasan, saran = ERROR_CATALOG.get(e.code, ("-", "-"))
        say(f"  \u274c Gagal: {penjelasan}")
        say(f"     \u2192 {saran}")
        return False, e.code
    except Exception as e:
        say(f"  \u274c Error: {type(e).__name__}: {e}")
        return False, "E_UNEXPECTED"

# ============================================================
# MAIN
# ============================================================
def main():
    say_section("DOWNLOAD DRAFT IA \u2014 Pipeline Start")
    say(f"  Folder   : {DOWNLOAD_DIR}")
    if not os.path.isdir(DOWNLOAD_DIR):
        say(f"  \u274c Folder tidak ditemukan")
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            say_step("Buat folder", "OK")
        except Exception as e:
            say_step("Buat folder", f"FAIL ({e})")

    try:
        driver = connect_chrome()
    except AppError as e:
        penjelasan, saran = ERROR_CATALOG.get(e.code, ("-", "-"))
        say(f"  \u274c Gagal: {penjelasan}")
        return 1
    except Exception as e:
        say(f"  \u274c Error: {type(e).__name__}: {e}")
        return 1
    say("  Chrome   : terhubung (port 9222)")

    recover_to_list(driver)

    # Kumpul transaksi langsung (tanpa refresh dulu — hemat ~3s).
    # User request: "habis filter nama pembuat data gak perlu ada refresh lagi".
    # Filter scope fix (c3a1bbf) bikin grid lebih stabil, jadi refresh by default
    # tidak diperlukan. TAPI kalau 0 rows (grid masih rusak dari filter SPA nav),
    # fallback: hard_reset + re-scan (safety net — tidak re-introduce bug 0 transaksi).
    say_step("Kumpul transaksi + Keterangan")
    order, row_h, suffix_map = collect_nomor_list(driver)
    if not order:
        # Fallback: grid mungkin rusak dari filter SPA navigation. Refresh + re-scan.
        say("  ⚠ 0 transaksi terbaca — refresh list (reset grid dari filter)...")
        hard_reset_list(driver)
        order, row_h, suffix_map = collect_nomor_list(driver)
        if not order:
            say("  \u274c Gagal: tidak ada transaksi terbaca di grid (bahkan setelah refresh).")
            return 1
    limit = len(order) if MAX_ROWS == 0 else min(MAX_ROWS, len(order))
    say(f"  Transaksi: {len(order)} ditemukan")
    say(f"  Suffix   : {len(suffix_map)} baris terbaca")
    say("")

    hasil, gagal, processed = [], [], set()
    consecutive = 0
    t_start = time.time()

    try:
        for i in range(limit):
            nomor = order[i]
            if nomor in processed:
                continue
            ok, info = process_nomor(driver, nomor, i + 1, limit, row_h, suffix_map)
            processed.add(nomor)
            if ok:
                hasil.append((nomor, info))
                consecutive = 0
            else:
                gagal.append((nomor, info))
                consecutive += 1
                if consecutive >= MAX_CONSECUTIVE_FAIL:
                    say(f"  \u26d4 Berhenti: {consecutive} gagal beruntun")
                    break

            # Delay between transactions to avoid Accurate rate-limiting
            # (confirmed: 4+ rapid prints cause print overlay to stop appearing)
            seq = i + 1
            if seq < limit:  # don't delay after last transaction
                say(f"  (cooldown {DELAY_BETWEEN_TRANSACTIONS}s)")
                time.sleep(DELAY_BETWEEN_TRANSACTIONS)

            # Hard reset every N transactions to prevent SlickGrid stylesheet breakage
            # + DOM pollution from 173+ residual overlay elements
            if seq < limit and seq % HARD_RESET_EVERY_N == 0:
                hard_reset_list(driver, seq=seq, kind="scheduled")
                # Re-collect suffix_map after refresh (grid re-rendered, rows may have changed)
                # Actually, the existing code collects suffix_map BEFORE the loop. After refresh,
                # the grid re-renders with the same data (filter still applied). So suffix_map
                # should still be valid. But row heights might change — re-read row_h.
                # The process_nomor function uses find_rendered_row which searches the grid
                # dynamically, so it should adapt to the refreshed grid.

            # Failure recovery: if this transaction FAILED, hard reset before next
            # (grid might be in bad state from the failed transaction — E_ROW, E_PRINT, etc.)
            # This works WITH the scheduled reset above: scheduled runs every 4, this runs
            # only on failure, so worst case = reset after EVERY failure + every 4 on success.
            if not ok and seq < limit:
                hard_reset_list(driver, seq=seq, kind="recovery")
    except KeyboardInterrupt:
        say("  ⛔ Dihentikan manual")

    total_dt = time.time() - t_start
    say("")
    pct = 100 * len(hasil) // limit if limit else 0
    summary = [f"Durasi  : {total_dt:.1f}s ({int(total_dt)//60}m {total_dt%60:.0f}s)",
               f"Hasil   : {len(hasil)}/{limit} berhasil ({pct}%)"]
    if hasil:
        summary.append("File diunduh:")
        for i, (nomor, fname) in enumerate(hasil, 1):
            summary.append(f"  {i}. {nomor} → {fname}")
    if gagal:
        summary.append(f"Gagal   : {len(gagal)}")
        for nomor, code in gagal:
            summary.append(f"  • {nomor} ({code})")
    say_summary_box(summary)
    say("")

    if len(hasil) > 0:
        say(f"  ✅ Selesai — {len(hasil)} file diunduh")
        return 0
    else:
        say("  ❌ Tidak ada file yang diunduh")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        say(f"  ❌ Error tak terduga: {type(e).__name__}: {e}")
        sys.exit(1)