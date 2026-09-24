"""
download_sj_gis.py  (v2 - TRIAL)
==================================
Download Surat Jalan (SJ) dari modul PEMINDAHAN BARANG Accurate Online (database GiS).

PERBAIKAN v2 (dari feedback user):
  1. Search pakai JS setVal (native setter + dispatch input/change/keyup) — BUKAN Selenium
     send_keys yang nggak dikenalin framework Accurate. (Fix "kode tidak keluar".)
  2. Flow download BUKAN Ctrl+P. Tombolnya = "Komentar dan Dokumen" di halaman detail.
     Alur: search -> klik baris -> buka detail -> klik tombol Dokumen/Komentar ->
     panel dokumen muncul -> cari link download SJ -> klik -> file tersimpan.

Cara pakai:
  1. Buka Chrome: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate, buka modul PEMINDAHAN BARANG (halaman LIST/tabel).
  3. python download_sj_gis.py  (atau double-click JALANKAN_SJ_GIS.bat)
  4. Masukkan kode SJ (mis. IT.2026.09.19805).

Output: file PDF/XLS tersimpan di folder Downloads.
Kalau auto-download gagal, tool cetak DUMP panel dokumen — kirim ke saya buat fix selector.
"""
import os
import sys
import time
import socket
import re
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException, StaleElementReferenceException, ElementClickInterceptedException,
)

# ============================================================
# CONFIG
# ============================================================
DEBUG_PORT = 9222
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
KODE_RE = re.compile(r"IT\.\d{4}\.\d{2}\.\d+")

# Tombol Dokumen/Komentar di detail view (dicari contains match)
DOKUMEN_TEXTS = ["Dokumen", "Komentar", "Lampiran", "Attachment", "Dokumen & Komentar", "Komentar & Dokumen"]
# Tombol/link unduh di panel dokumen
UNDUH_TEXTS = ["Unduh", "Download", "Cetak", "Simpan", "PDF", "XLS"]
DL_EXTS = (".pdf", ".xls", ".xlsx", ".doc", ".docx", ".png", ".jpg", ".jpeg")

def say(msg):
    print(msg); sys.stdout.flush()

# ============================================================
# CHROME CONNECTION
# ============================================================
def connect_chrome():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", DEBUG_PORT)) != 0:
            say(f"[ERROR] Port debugging {DEBUG_PORT} tidak aktif.")
            say(f"  Buka Chrome: chrome.exe --remote-debugging-port={DEBUG_PORT} --user-data-dir=\"C:\\ChromeDebugProfile\"")
            sys.exit(1)
    opt = Options()
    opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    return webdriver.Chrome(options=opt)

def switch_top(driver):
    try: driver.switch_to.default_content()
    except: pass

def find_list_frame(driver, timeout=12):
    end = time.time() + timeout
    SEL = ".slick-viewport, .slick-row, input[name='keyword']"
    while time.time() < end:
        switch_top(driver)
        if driver.find_elements(By.CSS_SELECTOR, SEL): return "top"
        for i, fr in enumerate(driver.find_elements(By.CSS_SELECTOR, "iframe, frame")):
            try:
                switch_top(driver); driver.switch_to.frame(fr)
                if driver.find_elements(By.CSS_SELECTOR, SEL): return f"iframe[{i}]"
            except: continue
        switch_top(driver); time.sleep(0.25)
    return None

def reframe(driver, fr):
    if fr and fr != "top":
        try:
            switch_top(driver)
            ifs = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            idx = int(fr.split("[")[1].split("]")[0]) if "[" in fr else -1
            if 0 <= idx < len(ifs): driver.switch_to.frame(ifs[idx])
        except: pass

def switch_path(driver, path):
    switch_top(driver)
    for i in (path or []):
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        if 0 <= i < len(frames): driver.switch_to.frame(frames[i])
        else: return False
    return True

def smart_click(driver, el, retries=3):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            ActionChains(driver).move_to_element(el).click().perform()
            return "ACTIONCHAINS"
        except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
            time.sleep(0.3)
    try: el.click(); return "ELCLICK"
    except: pass
    try:
        driver.execute_script("arguments[0].click();", el); return "JSCLICK"
    except: return "GAGAL"

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

JS_FIND_MARK = JS_VIS + """
return (function(txt, exact){
  const ATTR='data-fl-target';
  const up = txt.toUpperCase();
  function scan(doc, path){
    const els = doc.querySelectorAll('button, a, span, div, li, label, input[type="button"], i, svg');
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

JS_DETAIL_OPEN = JS_VIS + """
return (function(nomor){
  function scan(doc){
    const inps = doc.querySelectorAll('input');
    for (const i of inps){
      if (i.name === 'keyword') continue;
      if (i.name === 'searchDetailItem') continue;
      if (i.name === 'warehouse') continue;
      if (i.name === 'referenceWarehouse') continue;
      if (i.name === 'transDate') continue;
      if ((i.value||'').trim()===nomor && vis(i)) return true;
    }
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){ try{ const d=fr[i].contentDocument; if(d && scan(d)) return true; }catch(e){} }
    return false;
  }
  return scan(document);
})(arguments[0])
"""

JS_MARK_CLOSE = JS_VIS + """
return (function(nomor){
  const ATTR='data-fl-target';
  function scan(doc, path){
    const els = doc.querySelectorAll('li, a, div, span');
    for (const el of els){
      if (!vis(el)) continue;
      const t = (el.innerText||'').trim();
      if (!t || t.length>60) continue;
      if (!t.includes(nomor)) continue;
      let close = el.querySelector('i[class*="cancel"], i[class*="close"], i[class*="remove"], span[class*="close"], button[class*="close"], .icon-cancel, .icon-close');
      if (!close){
        const kids = el.querySelectorAll('i, span, b, button');
        for (const k of kids){
          const kt = (k.textContent||'').trim();
          if (kt==='x' || kt==='\u00d7'){ close = k; break; }
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

def find_marked(driver, path, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if switch_path(driver, path):
            for el in driver.find_elements(By.CSS_SELECTOR, '[data-fl-target="1"]'):
                try:
                    if el.is_displayed(): return el
                except: continue
        time.sleep(0.2)
    return None

def clear_mark(driver, path):
    try:
        if switch_path(driver, path):
            driver.execute_script(
              "document.querySelectorAll('[data-fl-target=\"1\"]')"
              ".forEach(e=>e.removeAttribute('data-fl-target'));")
    except: pass

# ============================================================
# SEARCH BY KODE — FIX: pakai JS setVal (proven dari deteksi)
# ============================================================
JS_SET_KEYWORD = """
return (function(kode){
  var el = document.querySelector("input[name='keyword']") || document.querySelector("input[type='text']");
  if (!el) return {ok:false, msg:'NO_INPUT'};
  el.focus(); el.click();
  try {
    var proto = Object.getPrototypeOf(el);
    var desc = Object.getOwnPropertyDescriptor(proto, 'value') || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
    if (desc && desc.set) desc.set.call(el, kode); else el.value = kode;
  } catch(e) { el.value = kode; }
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
  el.dispatchEvent(new Event('keyup', {bubbles:true}));
  return {ok:true, value: el.value};
})(arguments[0]);
"""

JS_CLICK_BTN_SEARCH = """
return (function(){
  var b = document.querySelector("button.btn-search");
  if (!b) return 'NO_BTN';
  b.click();
  return 'OK';
})();
"""

JS_FIND_ROW_WITH_KODE = """
return (function(kode){
  var rows = document.querySelectorAll(".slick-row");
  for (var i=0;i<rows.length;i++){
    var t = rows[i].innerText || '';
    if (t.indexOf(kode) !== -1){
      rows[i].setAttribute('data-fl-target','1');
      var cells = rows[i].querySelectorAll('.slick-cell');
      var cellMarked = false;
      for (var j=0;j<cells.length;j++){
        var ct = (cells[j].innerText||'').trim();
        if (ct.indexOf(kode) !== -1){
          cells[j].setAttribute('data-fl-target','2');
          cellMarked = true;
          break;
        }
      }
      return {found:true, text:t.slice(0,80), path:[], cellMarked:cellMarked, cellCount:cells.length};
    }
  }
  return {found:false, count:rows.length};
})(arguments[0]);
"""

JS_CLICK_SEQ = """
var el = arguments[0];
var init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1};
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
  try { el.dispatchEvent(new MouseEvent(t, init)); } catch(e){}
});
try { el.dispatchEvent(new MouseEvent('dblclick', init)); } catch(e){}
"""

def find_marked_attr(driver, attr_val, timeout=3):
    """Cari element dengan data-fl-target = attr_val (1=row, 2=cell)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, f'[data-fl-target="{attr_val}"]')
            for el in els:
                try:
                    if el.is_displayed(): return el
                except: continue
        except: pass
        time.sleep(0.2)
    return None

def search_kode(driver, kode, fr):
    """Ketik kode via JS setVal + klik btn-search via JS. Return True kalau row muncul."""
    reframe(driver, fr)
    res = driver.execute_script(JS_SET_KEYWORD, kode)
    if not res or not res.get("ok"):
        say(f"  [ERROR] Search box tidak ditemukan: {res}")
        return False
    say(f"  [OK] Keyword diset via JS: value={res.get('value','')}")
    time.sleep(0.3)
    click_res = driver.execute_script(JS_CLICK_BTN_SEARCH)
    say(f"  [OK] btn-search diklik via JS: {click_res}")
    if click_res == "NO_BTN":
        say("  [WARNING] btn-search tidak ada, coba Enter key fallback...")
        try:
            inps = driver.find_elements(By.CSS_SELECTOR, "input[name='keyword']")
            if inps: inps[0].send_keys(Keys.RETURN)
        except: pass
    # Polling row kode muncul (12s)
    end = time.time() + 12
    while time.time() < end:
        reframe(driver, fr)
        r = driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
        if r and r.get("found"):
            say(f"  [OK] Kode ditemukan di grid: {r.get('text','')[:60]}")
            return True
        time.sleep(0.5)
    say(f"  [FAIL] Kode tidak muncul dalam 12s. Grid rows terakhir: {r.get('count',0) if r else '?'}")
    return False

def detail_opened(driver, kode, before_tab_count):
    """Quick check apakah detail kebuka. Return string label or None."""
    try:
        switch_top(driver)
        if driver.execute_script(JS_DETAIL_OPEN, kode): return "DETAIL_INPUT"
        tab_count = driver.execute_script(
            "return document.querySelectorAll('[class*=\"aol-main-tab\"]').length;") or 0
        if tab_count > before_tab_count: return "NEW_INTERNAL_TAB"
    except: pass
    return None

def click_row_with_kode(driver, fr, kode):
    """Buka detail — coba 6 strategi, cek kebuka tiap strategi (jangan percaya 'no exception')."""
    switch_top(driver)
    before_tabs = driver.execute_script(
        "return document.querySelectorAll('[class*=\"aol-main-tab\"]').length;") or 0
    before_handles = len(driver.window_handles)

    # Re-mark + dump cell info buat verifikasi
    reframe(driver, fr)
    driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
    cell_info = driver.execute_script("""
        var cell = document.querySelector('[data-fl-target="2"]');
        var row = document.querySelector('[data-fl-target="1"]');
        return {
            cellText: cell ? (cell.innerText||'').trim().slice(0,60) : '(no cell)',
            cellHTML: cell ? (cell.innerHTML||'').slice(0,250) : '(no cell)',
            rowText: row ? (row.innerText||'').trim().slice(0,80) : '(no row)'
        };
    """)
    say(f"  Cell text     : {cell_info.get('cellText','?')}")
    say(f"  Cell innerHTML: {cell_info.get('cellHTML','?')[:200]}")
    say(f"  Row text      : {cell_info.get('rowText','?')[:70]}")
    say(f"  Baseline: internal_tabs={before_tabs}, browser_tabs={before_handles}")

    def try_strategy(label, desc, get_target, click_fn):
        say(f"  [{label}] {desc}...")
        try:
            reframe(driver, fr)
            driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
            target = get_target()
            if not target:
                say(f"      [skip] target hilang/stale"); return None
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            click_fn(target)
            say(f"      [terkirim tanpa error]")
        except Exception as e:
            say(f"      [gagal exception: {e}]"); return None
        time.sleep(3)
        switch_top(driver)
        # Cek new browser tab
        if len(driver.window_handles) > before_handles:
            driver.switch_to.window(driver.window_handles[-1])
            say(f"      [OK] Tab browser baru terbuka!")
            return f"{label}_NEW_BROWSER_TAB"
        opened = detail_opened(driver, kode, before_tabs)
        if opened:
            say(f"      [OK] Detail kebuka via {opened}")
            return f"{label}_{opened}"
        say(f"      [~] belum kebuka, coba strategi berikutnya")
        return None

    # a: double-click cell (ActionChains)
    r = try_strategy("a", "DOUBLE-CLICK cell Nomor (ActionChains)",
        lambda: find_marked_attr(driver, "2", timeout=2),
        lambda t: ActionChains(driver).move_to_element(t).double_click().perform())
    if r: return r
    # b: JS clickSeq pada cell (full pointer events)
    r = try_strategy("b", "JS clickSeq (pointerdown+mousedown+mouseup+click+dblclick) cell",
        lambda: find_marked_attr(driver, "2", timeout=2),
        lambda t: driver.execute_script(JS_CLICK_SEQ, t))
    if r: return r
    # c: element.click() pada cell (single JS click — bisa trigger Accurate's onClick)
    r = try_strategy("c", "element.click() single pada cell (JS)",
        lambda: find_marked_attr(driver, "2", timeout=2),
        lambda t: driver.execute_script("arguments[0].click();", t))
    if r: return r
    # d: double-click row (ActionChains)
    r = try_strategy("d", "DOUBLE-CLICK row (ActionChains)",
        lambda: find_marked_attr(driver, "1", timeout=2),
        lambda t: ActionChains(driver).move_to_element(t).double_click().perform())
    if r: return r
    # e: single click row (ActionChains)
    r = try_strategy("e", "single click row (ActionChains)",
        lambda: find_marked_attr(driver, "1", timeout=2),
        lambda t: ActionChains(driver).move_to_element(t).click().perform())
    if r: return r
    # f: click inner <a>/<span onclick> link di dalam cell (nomor mungkin hyperlink)
    def get_inner_link():
        driver.execute_script("""
            var c=document.querySelector('[data-fl-target="2"]');
            if(!c) return;
            var a=c.querySelector('a,span[onclick],[onclick],.slick-cell-text');
            if(a){a.setAttribute('data-fl-target','3');}
        """)
        return find_marked_attr(driver, "3", timeout=2)
    r = try_strategy("f", "click <a>/<span onclick> di dalam cell Nomor",
        get_inner_link,
        lambda t: ActionChains(driver).move_to_element(t).click().perform())
    if r: return r
    say("  [FAIL] Semua 6 strategi gagal buka detail.")
    return None

# ============================================================
# DETAIL + DOKUMEN PANEL FLOW
# ============================================================
def wait_detail_open(driver, kode, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            switch_top(driver)
            if driver.execute_script(JS_DETAIL_OPEN, kode): return True
        except: pass
        time.sleep(0.3)
    return False

def check_new_tab_and_switch(driver, before_handles):
    """Cek apakah klik baris membuka tab browser baru. Switch ke tab terbaru kalau ada."""
    after = driver.window_handles
    if len(after) > len(before_handles):
        driver.switch_to.window(after[-1])
        say(f"  [OK] Tab baru terbuka. Switch ke tab {len(after)}/{len(after)}: {driver.current_url[:60]}")
        return True
    return False

JS_DUMP_DETAIL_STATE = JS_VIS + """
return (function(kode){
  var out = {url: location.href, title: document.title, tabs: window.length,
             internalTabs: [], allButtons: [], dokumenEls: [], kodeEls: []};
  // Internal Accurate tabs (aol-main-tab-*) — apakah ada tab detail baru?
  var tabEls = document.querySelectorAll('[class*="aol-main-tab"], .left-tab');
  for (var i=0;i<tabEls.length;i++){
    var t = (tabEls[i].innerText||'').trim().slice(0,40);
    if (!t) continue;
    out.internalTabs.push({text:t, class:(tabEls[i].className||'').toString().slice(0,50)});
  }
  // SEMUA buttons (visible + hidden) — catch detail buttons di tab hidden
  var btns = document.querySelectorAll('button, [role="button"], a.btn, .button, input[type="button"]');
  for (var i=0;i<btns.length && out.allButtons.length<50;i++){
    var b = btns[i];
    var st = window.getComputedStyle(b);
    var vis = !(st.display==='none'||st.visibility==='hidden'||parseFloat(st.opacity)===0);
    var r = b.getBoundingClientRect();
    var sizeOk = r.width>0 && r.height>0;
    var t = (b.innerText||b.textContent||'').trim().slice(0,40);
    var ti = (b.getAttribute && b.getAttribute('title')||'').slice(0,40);
    var nm = b.name||''; var cls = (b.className||'').toString().slice(0,40);
    var ic = b.querySelector('i,span[class*="icon"],[class*="mif-"]');
    var icon = ic ? (ic.className||'').toString().slice(0,40) : '';
    out.allButtons.push({t:t||ti||'(no text)', name:nm, class:cls, icon:icon,
                         visible: vis && sizeOk});
  }
  var all = document.querySelectorAll('*');
  var RE_DOC = /DOKUMEN|KOMENTAR|LAMPIRAN|ATTACH|COMMENT|DOCUMENT/i;
  for (var i=0;i<all.length && out.dokumenEls.length<25;i++){
    var el = all[i];
    var t = (el.innerText||'').trim();
    if (!t || t.length>50) continue;
    if (RE_DOC.test(t)){
      var st2 = window.getComputedStyle(el);
      out.dokumenEls.push({tag:el.tagName, text:t.slice(0,50),
                           class:(el.className||'').toString().slice(0,40),
                           visible: !(st2.display==='none'||st2.visibility==='hidden')});
    }
  }
  // Elemen berisi kode (di mana kode muncul setelah klik?)
  for (var i=0;i<all.length && out.kodeEls.length<15;i++){
    var el = all[i];
    var t = (el.innerText||'').trim();
    if (!t || t.length>80) continue;
    if (t.indexOf(kode) !== -1 && t.length < 80){
      out.kodeEls.push({tag:el.tagName, text:t.slice(0,70),
                        class:(el.className||'').toString().slice(0,40)});
    }
  }
  return out;
})(arguments[0]);
"""

def dump_detail_state(driver, kode):
    """Dump komprehensif — internal tabs + ALL buttons (visible+hidden) + elemen Dokumen + elemen kode."""
    switch_top(driver)
    try:
        st = driver.execute_script(JS_DUMP_DETAIL_STATE, kode)
    except Exception as e:
        say(f"  [ERR] dump gagal: {e}"); return
    say(f"  URL: {st.get('url','?')[:80]}")
    say(f"  Title: {st.get('title','?')}")
    say(f"  Iframe count: {st.get('tabs',0)}")
    # Internal tabs
    tabs = st.get('internalTabs', [])
    say(f"\n  --- INTERNAL TABS Accurate ({len(tabs)}) ---")
    for i, t in enumerate(tabs):
        say(f'    [{i}] text="{t["text"]}" class="{t["class"]}"')
    # ALL buttons (visible + hidden)
    btns = st.get('allButtons', [])
    visBtns = [b for b in btns if b.get('visible')]
    hidBtns = [b for b in btns if not b.get('visible')]
    say(f"\n  --- ALL BUTTONS ({len(btns)}: {len(visBtns)} visible, {len(hidBtns)} hidden) ---")
    for i, b in enumerate(btns):
        v = "VIS" if b.get('visible') else "HID"
        say(f'    [{i}] [{v}] text="{b["t"]}" name="{b["name"]}" class="{b["class"]}" icon="{b["icon"]}"')
    # Dokumen elements
    docEls = st.get('dokumenEls', [])
    say(f"\n  --- ELEMEN DOKUMEN/KOMENTAR ({len(docEls)}) ---")
    if not docEls:
        say("    (tidak ada elemen dengan teks Dokumen/Komentar/Lampiran/Attachment)")
    for i, d in enumerate(docEls):
        v = "VIS" if d.get('visible') else "HID"
        say(f'    [{i}] [{v}] <{d["tag"]}> text="{d["text"]}" class="{d["class"]}"')
    # Elements containing kode
    kodeEls = st.get('kodeEls', [])
    say(f"\n  --- ELEMEN BERISI KODE ({len(kodeEls)}) ---")
    for i, k in enumerate(kodeEls):
        say(f'    [{i}] <{k["tag"]}> text="{k["text"]}" class="{k["class"]}"')

JS_FIND_DOKUMEN_TAB = JS_VIS + """
return (function(){
  var ATTR='data-fl-target';
  var links = document.querySelectorAll('a, li');
  for (var i=0;i<links.length;i++){
    var el = links[i];
    if (!vis(el)) continue;
    var t = (el.innerText||'').trim();
    if (!t || t.length > 30) continue;
    var up = t.toUpperCase();
    // Cari "Dokumen" tapi EXCLUDE "Memiliki dokumen" (checkbox label)
    if (up.indexOf('DOKUMEN') !== -1 && up.indexOf('MEMILIKI') === -1){
      el.setAttribute(ATTR,'1');
      return {path:[], text:t.slice(0,30), html:(el.outerHTML||'').slice(0,300)};
    }
  }
  return null;
})();
"""

def find_dokumen_tab(driver):
    """Cari tab 'Dokumen' (bukan 'Memiliki dokumen'). Return (ux, label)."""
    switch_top(driver)
    try:
        ux = driver.execute_script(JS_FIND_DOKUMEN_TAB)
        if ux: return ux, "dokumen-tab"
    except Exception as e:
        say(f"  [ERR] find_dokumen_tab: {e}")
    return None, None

def find_download_button_by_name(driver, names):
    """Cari button by name attribute (paling reliable). Return (element, name).
    Prefer visible; kalau semua hidden, ambil yg pertama (JS click bisa trigger hidden)."""
    switch_top(driver)
    for name in names:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, f'button[name="{name}"]')
            if not btns: continue
            # Prefer visible
            for btn in btns:
                try:
                    if btn.is_displayed(): return btn, name
                except: continue
            # Fallback: ambil pertama (akan di-JS click)
            return btns[0], name
        except: continue
    return None, None

def click_dokumen_tab_and_find_download(driver):
    """Klik tab Dokumen, tunggu, cari tombol download by name. Return (btn, name) or (None, None)."""
    say('\n  Mencari tab "Dokumen"...')
    ux, via = find_dokumen_tab(driver)
    if not ux:
        say('  [WARNING] Tab "Dokumen" tidak ditemukan (exclude "Memiliki").')
        say('  Coba langsung cari tombol download by name (mungkin sudah visible)...')
    else:
        say(f'  [OK] Tab Dokumen ditemukan: "{ux.get("text","?")}"')
        el = find_marked(driver, ux["path"], timeout=5)
        if el:
            how = smart_click(driver, el)
            say(f"  [OK] Tab Dokumen diklik via {how}. Tunggu panel...")
            clear_mark(driver, ux["path"])
            time.sleep(3)
        else:
            clear_mark(driver, ux["path"])
            say("  [WARNING] Tab Dokumen tidak bisa di-klik. Lanjut cari download by name.")
    # Cari tombol download by name (urutan preferensi)
    say('  Mencari tombol download by name (btnExportPdf > btnExportXls > btnPrint)...')
    btn, name = find_download_button_by_name(driver, ["btnExportPdf", "btnExportXls", "btnPrint"])
    return btn, name

def dump_dokumen_panel(driver):
    """Dump semua link/button relevan di panel dokumen (download/pdf/xls/unduh + nama file)."""
    switch_top(driver)
    JS_DUMP = """
return (function(){
  var out = [];
  var els = document.querySelectorAll('a, button, [role="button"], span[onclick], div[onclick]');
  var RE = /UNDUH|DOWNLOAD|PDF|XLS|XLSX|SJ|SURAT|\\.pdf|\\.xls/i;
  for (var i=0;i<els.length;i++){
    var el = els[i];
    var t = (el.innerText||el.textContent||'').trim();
    var href = el.getAttribute && (el.getAttribute('href')||'') || '';
    var oncl = el.getAttribute && (el.getAttribute('onclick')||'') || '';
    var cls = (el.className||'').toString();
    var tag = el.tagName;
    if (RE.test(t) || RE.test(href) || RE.test(oncl)){
      var r = el.getBoundingClientRect();
      if (r.width>0 && r.height>0){
        out.push({i:i, tag:tag, text:t.slice(0,60), href:href.slice(0,100), onclick:oncl.slice(0,80), class:cls.slice(0,50)});
      }
    }
  }
  return out.slice(0, 40);
})();
"""
    try:
        return driver.execute_script(JS_DUMP) or []
    except Exception as e:
        say(f"  [ERR] dump gagal: {e}")
        return []

def try_click_download_in_panel(driver, panel_dump):
    """Coba klik link/button download pertama yg relevan."""
    for item in panel_dump[:10]:
        txt = (item.get("text") or "").upper()
        href = (item.get("href") or "")
        oncl = (item.get("onclick") or "")
        # Skip kalau cuma "PDF" label doang (bukan link)
        if txt in ("PDF", "XLS", "XLSX") and not href and not oncl:
            continue
        if any(k in txt for k in ("UNDUH", "DOWNLOAD", "CETAK", "SIMPAN")) or href.endswith(".pdf") or href.endswith(".xls"):
            switch_top(driver)
            ux = driver.execute_script(JS_FIND_MARK, item["text"], False)
            if ux:
                el = find_marked(driver, ux["path"], timeout=3)
                if el:
                    how = smart_click(driver, el)
                    clear_mark(driver, ux["path"])
                    say(f"  [OK] Diklik: '{item['text'][:40]}' via {how}")
                    return True
    return False

def snapshot_downloads():
    try: return set(os.listdir(DOWNLOAD_DIR))
    except: return set()

def wait_new_download(before, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try: cur = set(os.listdir(DOWNLOAD_DIR))
        except: time.sleep(0.25); continue
        pending = [f for f in cur if f.endswith(('.crdownload', '.part', '.tmp'))]
        new = [f for f in (cur - before)
               if not f.endswith(('.crdownload', '.part', '.tmp'))
               and f.lower().endswith(DL_EXTS)]
        if new and not pending:
            cand = sorted(new, key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_DIR, f)))[-1]
            p = os.path.join(DOWNLOAD_DIR, cand)
            try:
                s1 = os.path.getsize(p); time.sleep(0.4); s2 = os.path.getsize(p)
                if s1 == s2 and s1 > 0: return cand
            except: pass
        time.sleep(0.25)
    return None

def close_detail_tab(driver, kode):
    try:
        switch_top(driver)
        cl = driver.execute_script(JS_MARK_CLOSE, kode)
        if cl:
            el = find_marked(driver, cl["path"], timeout=3)
            if el: smart_click(driver, el)
            clear_mark(driver, cl["path"])
    except: pass

# ============================================================
# MAIN
# ============================================================
def main():
    say("=" * 60)
    say("  DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v7 TRIAL)")
    say("=" * 60)
    say(f"Folder download: {DOWNLOAD_DIR}")
    if not os.path.isdir(DOWNLOAD_DIR):
        say(f"[ERROR] Folder Downloads tidak ditemukan: {DOWNLOAD_DIR}")
        sys.exit(1)

    kode = input("\nMasukkan kode SJ (default: IT.2026.09.19805, atau ketik kode lain): ").strip()
    if not kode:
        kode = "IT.2026.09.19805"
        say("  [INFO] Kode kosong -> pakai default: IT.2026.09.19805")
    if not KODE_RE.match(kode):
        say(f"[WARNING] Format kode tidak biasa: {kode} (tetap lanjut)")
    say(f"\nKode: {kode}")

    say("\n[1/8] Connect Chrome port 9222...")
    driver = connect_chrome()
    say(f"  [OK] Terhubung. Tab aktif: {driver.current_url}")

    say("\n[2/8] Cari frame list...")
    fr = find_list_frame(driver, timeout=12)
    if not fr:
        say("  [ERROR] Frame list tidak ditemukan.")
        say("  Pastikan halaman LIST Pemindahan Barang terbuka & login aktif.")
        sys.exit(1)
    say(f"  [OK] Frame: {fr}")

    say(f"\n[3/8] Search kode {kode} (via JS setVal)...")
    if not search_kode(driver, kode, fr):
        say("  [ERROR] Kode tidak ditemukan di grid setelah search.")
        say("  Kemungkinan: kode bukan transaksi tanggal hari ini (cek filter date),")
        say("  atau halaman list belum terbuka di tab aktif.")
        sys.exit(1)

    say("\n[4/8] Klik baris (buka detail)...")
    before_handles = driver.window_handles
    how = click_row_with_kode(driver, fr, kode)
    if not how:
        say("  [ERROR] Baris tidak bisa di-klik.")
        sys.exit(1)
    say(f"  [OK] Baris diklik via {how}.")
    time.sleep(2)
    # Cek apakah tab browser baru terbuka
    check_new_tab_and_switch(driver, before_handles)
    # Tunggu detail form (input kode, exclude search box)
    if wait_detail_open(driver, kode, timeout=15):
        say("  [OK] Detail form terbuka (input kode ditemukan, exclude search box).")
    else:
        say("  [WARNING] Detail form TIDAK terdeteksi. Mungkin detail belum kebuka,")
        say("  atau detail kebuka tapi input nomor-nya bukan <input> (label/text doang).")
        say("  Lanjut tetap dump state + cari tombol Dokumen.")

    say("\n[5/8] DUMP STATE HALAMAN (cari dimana tombol Dokumen)...")
    dump_detail_state(driver, kode)

    say("\n[6/8] Klik tab Dokumen + cari tombol download by name...")
    btn, dl_name = click_dokumen_tab_and_find_download(driver)
    if not btn:
        say('  [ERROR] Tombol download (btnExportPdf/btnExportXls/btnPrint) tidak ditemukan.')
        say('  Kirim output [5/8] DUMP ke saya — dari list ALL BUTTONS saya lihat name tombol yg benar.')
        close_detail_tab(driver, kode)
        sys.exit(1)
    say(f'  [OK] Tombol download ditemukan: name="{dl_name}" text="{btn.text.strip()[:40]}"')

    say(f"\n[7/8] Klik tombol {dl_name} + tunggu download (maks 90s)...")
    before = snapshot_downloads()
    # Coba ActionChains dulu, fallback JS click (bisa trigger hidden button)
    how = None
    try:
        how = smart_click(driver, btn)
        say(f"  [OK] Diklik via {how}")
    except Exception as e:
        say(f"  [WARNING] smart_click gagal: {e}, coba JS click...")
    if not how or how == "GAGAL":
        try:
            driver.execute_script("arguments[0].click();", btn)
            say("  [OK] JS click terkirim")
        except Exception as e:
            say(f"  [ERROR] JS click juga gagal: {e}")
            close_detail_tab(driver, kode)
            sys.exit(1)
    say("  [..] Tunggu file tersimpan...")
    fname = wait_new_download(before, timeout=90)
    if not fname:
        say(f"  [ERROR] Download tidak selesai 90s. Cek manual: {DOWNLOAD_DIR}")
        say("  Mungkin tombol butuh panel dokumen aktif dulu, atau ada popup konfirmasi.")
        close_detail_tab(driver, kode)
        sys.exit(1)
    final = os.path.join(DOWNLOAD_DIR, fname)
    say(f"\n  [OK] File tersimpan: {final}")

    say("\n[8/8] Tutup tab detail...")
    close_detail_tab(driver, kode)
    say("\n" + "=" * 60)
    say(f"  SELESAI! File: {fname}")
    say(f"  Lokasi  : {final}")
    say(f"  Kode    : {kode}")
    say("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        say(f"\n[FATAL] {type(e).__name__}: {e}")
        traceback.print_exc()
        say("\nKirim error ini ke saya, jangan tutup dulu.")
    input("\nTekan Enter untuk keluar...")
