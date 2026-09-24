"""
download_sj_gis.py  (v8 - FINAL)
=================================
Download Surat Jalan (SJ) dari modul PEMINDAHAN BARANG Accurate Online (database GiS).

Flow (berdasarkan RECORDER recording user manual — selector PERSIS):
  1. Search kode di input[name=keyword] + click button.btn-search
  2. SINGLE-click cell di row berisi kode (BUKAN double-click) → detail kebuka (AJAX detail-item-transfer.do)
  3. Click i#btnCommentAttachment (icon Komentar/Dokumen di detail toolbar)
  4. Click <a> pertama di dropdown .drop-left → attachment panel kebuka (AJAX attachment.do)
  5. Click i.icon-download-2 di dalam <a> di attachment panel → DOWNLOAD file
  6. Close attachment overlay (button.btn-close) + close detail tab (i.icon-cancel-2.smaller)
  7. Loop ke kode berikutnya (kalau ada)

Cara pakai:
  1. Buka Chrome: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate, buka modul PEMINDAHAN BARANG (halaman LIST/tabel).
  3. python download_sj_gis.py  (atau double-click JALANKAN_SJ_GIS.bat)
  4. Masukkan kode SJ. Bisa 1 kode, atau multi-kode dipisah koma:
       IT.2026.09.19805
       IT.2026.09.19805, IT.2026.09.20451, IT.2026.09.20447

Output: file PDF/XLS tersimpan di folder Downloads (1 file per kode).
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
    TimeoutException,
)

# ============================================================
# CONFIG
# ============================================================
DEBUG_PORT = 9222
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
KODE_RE = re.compile(r"IT\.\d{4}\.\d{2}\.\d+")
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

def find_marked_attr(driver, attr_val, timeout=3):
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
    # Fallback: ambil pertama walau hidden
    try:
        els = driver.find_elements(By.CSS_SELECTOR, f'[data-fl-target="{attr_val}"]')
        if els: return els[0]
    except: pass
    return None

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
      return {found:true, text:t.slice(0,80), cellMarked:cellMarked, cellCount:cells.length};
    }
  }
  return {found:false, count:rows.length};
})(arguments[0]);
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
    // cek i#btnCommentAttachment (marker detail form terbuka)
    var btn = doc.querySelector('#btnCommentAttachment');
    if (btn && vis(btn)) return true;
    // cek input value=kode (exclude search boxes)
    const inps = doc.querySelectorAll('input');
    for (const i of inps){
      if (i.name === 'keyword' || i.name === 'searchDetailItem' || i.name === 'warehouse'
          || i.name === 'referenceWarehouse' || i.name === 'transDate') continue;
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
    const els = doc.querySelectorAll('li, a, div, span, button');
    for (const el of els){
      if (!vis(el)) continue;
      const t = (el.innerText||'').trim();
      if (!t || t.length>60) continue;
      if (!t.includes(nomor)) continue;
      let close = el.querySelector('i[class*="cancel"], i[class*="close"], i[class*="remove"], i.icon-cancel-2, .icon-cancel-2');
      if (close){
        close.setAttribute(ATTR,'1');
        return {path:path, text:t.slice(0,60)};
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

# ============================================================
# STEP 1: SEARCH (proven)
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

def search_kode(driver, kode, fr):
    """Ketik kode + klik btn-search via JS. Return True kalau row kode muncul."""
    reframe(driver, fr)
    res = driver.execute_script(JS_SET_KEYWORD, kode)
    if not res or not res.get("ok"):
        say(f"    [ERROR] Search box tidak ditemukan.")
        return False
    time.sleep(0.3)
    driver.execute_script("""
        var b = document.querySelector("button.btn-search");
        if (b) b.click();
    """)
    end = time.time() + 12
    while time.time() < end:
        reframe(driver, fr)
        r = driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
        if r and r.get("found"):
            return True
        time.sleep(0.5)
    return False

# ============================================================
# STEP 2: SINGLE-CLICK CELL → OPEN DETAIL (BUKAN double-click!)
# ============================================================
def click_cell_open_detail(driver, fr, kode):
    """Single-click cell di row berisi kode → detail kebuka (AJAX detail-item-transfer.do)."""
    reframe(driver, fr)
    driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
    cell = find_marked_attr(driver, "2", timeout=3)
    if not cell:
        say("    [WARNING] Cell Nomor tidak ditemukan, coba row...")
        cell = find_marked_attr(driver, "1", timeout=2)
    if not cell:
        return None
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cell)
        ActionChains(driver).move_to_element(cell).click().perform()
        return "SINGLE_CLICK_CELL"
    except Exception as e:
        try:
            driver.execute_script("arguments[0].click();", cell)
            return "JS_CLICK_CELL"
        except:
            return None

def wait_detail_open(driver, kode, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            switch_top(driver)
            if driver.execute_script(JS_DETAIL_OPEN, kode): return True
        except: pass
        time.sleep(0.3)
    return False

# ============================================================
# STEP 3: CLICK i#btnCommentAttachment (tombol Komentar/Dokumen)
# ============================================================
def click_comment_attachment(driver):
    """Klik i#btnCommentAttachment (id unik dari recording)."""
    switch_top(driver)
    # Priority 1: by id (paling reliable)
    try:
        btn = driver.find_element(By.ID, "btnCommentAttachment")
        if btn:
            return smart_click(driver, btn)
    except: pass
    # Priority 2: by class
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "i.icn-navigation-attachment, [id*='ommentAttachment'], [class*='navigation-attachment']")
        for btn in btns:
            try:
                if btn.is_displayed():
                    return smart_click(driver, btn)
            except: continue
    except: pass
    return None

# ============================================================
# STEP 4: CLICK FIRST <a> IN DROPDOWN (.drop-left)
# ============================================================
JS_FIND_FIRST_DROPDOWN_A = JS_VIS + """
return (function(){
  var ATTR='data-fl-target';
  var uls = document.querySelectorAll('ul.drop-left, ul[class*="drop"], ul.dropdown-menu, ul.d-menu, ul');
  for (var i=0;i<uls.length;i++){
    var ul = uls[i];
    if (!vis(ul)) continue;
    var links = ul.querySelectorAll('a, li > a');
    for (var j=0;j<links.length;j++){
      var a = links[j];
      if (!vis(a)) continue;
      var t = (a.innerText||'').trim();
      if (!t || t.length > 40) continue;
      a.setAttribute(ATTR,'1');
      return {text:t, href:(a.getAttribute('href')||'').slice(0,80)};
    }
  }
  return null;
})();
"""

def click_first_dropdown_item(driver, timeout=5):
    """Setelah btnCommentAttachment, tunggu dropdown, klik <a> pertama."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            ux = driver.execute_script(JS_FIND_FIRST_DROPDOWN_A)
            if ux:
                el = find_marked(driver, [], timeout=2)
                if el:
                    how = smart_click(driver, el)
                    clear_mark(driver, [])
                    return how
        except: pass
        time.sleep(0.4)
    return None

# ============================================================
# STEP 5: WAIT ATTACHMENT PANEL + CLICK icon-download-2
# ============================================================
def wait_attachment_panel(driver, timeout=15):
    """Tunggu div[id^='accurate__company__attachment'] visible."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            switch_top(driver)
            panels = driver.find_elements(By.CSS_SELECTOR, "div[id^='accurate__company__attachment']")
            for p in panels:
                try:
                    if p.is_displayed(): return True
                except: continue
        except: pass
        time.sleep(0.5)
    return False

JS_FIND_DOWNLOAD_ICON = JS_VIS + """
return (function(){
  var ATTR='data-fl-target';
  var icons = document.querySelectorAll('i.icon-download-2, i[class*="icon-download"], [class*="icon-download-2"]');
  for (var i=0;i<icons.length;i++){
    var ic = icons[i];
    if (!vis(ic)) continue;
    var a = ic.closest('a');
    if (a && vis(a)){
      a.setAttribute(ATTR,'1');
      return {text:(a.innerText||'').trim().slice(0,40), href:(a.getAttribute('href')||'').slice(0,100)};
    }
    // fallback: click icon sendiri
    if (vis(ic)){
      ic.setAttribute(ATTR,'1');
      return {text:'(icon)', href:''};
    }
  }
  return null;
})();
"""

def click_download_icon(driver, timeout=10):
    """Cari i.icon-download-2 di dalam <a>, klik <a>-nya → download."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            ux = driver.execute_script(JS_FIND_DOWNLOAD_ICON)
            if ux:
                el = find_marked(driver, [], timeout=2)
                if el:
                    how = smart_click(driver, el)
                    clear_mark(driver, [])
                    return how
        except: pass
        time.sleep(0.4)
    return None

# ============================================================
# CLEANUP: CLOSE ATTACHMENT OVERLAY + DETAIL TAB
# ============================================================
def close_attachment_overlay(driver, timeout=5):
    """Tutup overlay attachment (button.btn-close di .window-overlay)."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "button.btn-close")
            for btn in btns:
                try:
                    if btn.is_displayed():
                        smart_click(driver, btn)
                        return True
                except: continue
        except: pass
        time.sleep(0.4)
    return False

def close_detail_tab(driver, kode, timeout=5):
    """Tutup tab detail (klik i.icon-cancel-2.smaller di tab berisi kode)."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            cl = driver.execute_script(JS_MARK_CLOSE, kode)
            if cl:
                el = find_marked(driver, cl["path"], timeout=2)
                if el:
                    smart_click(driver, el)
                    clear_mark(driver, cl["path"])
                    return True
        except: pass
        # Fallback: cari i.icon-cancel-2.smaller visible
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "i.icon-cancel-2.smaller")
            for btn in btns:
                try:
                    if btn.is_displayed():
                        smart_click(driver, btn)
                        return True
                except: continue
        except: pass
        time.sleep(0.4)
    return False

def recover_to_list(driver, kode):
    """Cleanup buat recovery ke list view: tutup overlay + tab detail."""
    close_attachment_overlay(driver, timeout=3)
    close_detail_tab(driver, kode, timeout=3)
    # Klik btnToggleList buat pastikan di list view
    try:
        switch_top(driver)
        btn = driver.find_element(By.CSS_SELECTOR, "button[name='btnToggleList']")
        if btn:
            smart_click(driver, btn)
            time.sleep(1)
    except: pass

# ============================================================
# DOWNLOAD WAIT
# ============================================================
def snapshot_downloads():
    try: return set(os.listdir(DOWNLOAD_DIR))
    except: return set()

def wait_new_download(before, timeout=90):
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

# ============================================================
# MAIN — proses 1 atau lebih kode (loop)
# ============================================================
def process_one_kode(driver, kode, fr, seq, total):
    """Proses 1 kode: search → klik cell → detail → btnCommentAttachment → dropdown → attachment → download → cleanup."""
    t0 = time.time()
    say(f"\n[{seq}/{total}] Kode: {kode}")
    try:
        # 1. Search
        say(f"  [1/7] Search kode...")
        if not search_kode(driver, kode, fr):
            say(f"  [ERROR] Kode tidak ditemukan di grid setelah search.")
            say(f"  (Mungkin kode bukan transaksi tanggal hari ini — cek filter date)")
            return False, "E_SEARCH"
        say(f"  [OK] Kode ditemukan di grid.")

        # 2. Single-click cell → detail
        say(f"  [2/7] Single-click cell (buka detail)...")
        how = click_cell_open_detail(driver, fr, kode)
        if not how:
            say(f"  [ERROR] Cell tidak bisa di-klik.")
            return False, "E_CLICK_CELL"
        say(f"  [OK] Diklik via {how}. Tunggu detail...")
        if not wait_detail_open(driver, kode, timeout=15):
            say(f"  [WARNING] Detail tidak terdeteksi, tapi lanjut cari btnCommentAttachment.")

        # 3. Click i#btnCommentAttachment
        say(f"  [3/7] Klik i#btnCommentAttachment (Komentar/Dokumen)...")
        how = click_comment_attachment(driver)
        if not how:
            say(f"  [ERROR] i#btnCommentAttachment tidak ditemukan.")
            say(f"  (Detail mungkin belum kebuka. Coba jalankan ulang, atau cek manual.)")
            recover_to_list(driver, kode)
            return False, "E_BTN_COMMENT"
        say(f"  [OK] btnCommentAttachment diklik via {how}. Tunggu dropdown...")

        # 4. Click first <a> di dropdown
        say(f"  [4/7] Klik <a> pertama di dropdown (buka attachment panel)...")
        how = click_first_dropdown_item(driver, timeout=8)
        if not how:
            say(f"  [ERROR] Dropdown item tidak ditemukan.")
            recover_to_list(driver, kode)
            return False, "E_DROPDOWN"
        say(f"  [OK] Dropdown item diklik via {how}. Tunggu attachment panel...")

        # 5. Wait attachment panel
        say(f"  [5/7] Tunggu attachment panel...")
        if not wait_attachment_panel(driver, timeout=15):
            say(f"  [WARNING] Attachment panel tidak terdeteksi. Tetap coba cari download icon.")

        # 6. Click icon-download-2 → download
        say(f"  [6/7] Klik i.icon-download-2 (download file)...")
        before = snapshot_downloads()
        how = click_download_icon(driver, timeout=10)
        if not how:
            say(f"  [ERROR] i.icon-download-2 tidak ditemukan di attachment panel.")
            say(f"  (Mungkin belum ada dokumen yg di-upload utk SJ ini. Cek manual.)")
            recover_to_list(driver, kode)
            return False, "E_DOWNLOAD_ICON"
        say(f"  [OK] Download icon diklik via {how}. Tunggu file (maks 90s)...")

        # 7. Wait file
        fname = wait_new_download(before, timeout=90)
        if not fname:
            say(f"  [ERROR] Download tidak selesai 90s. Cek manual: {DOWNLOAD_DIR}")
            recover_to_list(driver, kode)
            return False, "E_DOWNLOAD_TIMEOUT"
        final = os.path.join(DOWNLOAD_DIR, fname)
        say(f"  [OK] File tersimpan: {final}")

        # Cleanup
        say(f"  [7/7] Tutup overlay + tab detail...")
        close_attachment_overlay(driver, timeout=5)
        close_detail_tab(driver, kode, timeout=5)
        time.sleep(1)

        dt = time.time() - t0
        say(f"  [DONE] {kode} -> {fname} ({dt:.1f}s)")
        return True, fname

    except Exception as e:
        say(f"  [ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        recover_to_list(driver, kode)
        return False, "E_UNEXPECTED"

def main():
    say("=" * 60)
    say("  DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v8 FINAL)")
    say("=" * 60)
    say(f"Folder download: {DOWNLOAD_DIR}")
    if not os.path.isdir(DOWNLOAD_DIR):
        say(f"[ERROR] Folder Downloads tidak ditemukan: {DOWNLOAD_DIR}")
        sys.exit(1)

    raw = input("\nMasukkan kode SJ (1 kode, atau multi dipisah koma):\n  misal: IT.2026.09.19805\n  atau : IT.2026.09.19805, IT.2026.09.20451, IT.2026.09.20447\n\nKode: ").strip()
    if not raw:
        raw = "IT.2026.09.19805"
        say(f"  [INFO] Kosong -> pakai default: {raw}")
    # Parse multi-kode
    kodes = [k.strip() for k in raw.split(",") if k.strip()]
    kodes = [k for k in kodes if KODE_RE.match(k) or True]  # accept all non-empty
    say(f"\nTotal kode diproses: {len(kodes)}")
    for i, k in enumerate(kodes, 1):
        say(f"  [{i}/{len(kodes)}] {k}")

    say(f"\n[0] Connect Chrome port 9222...")
    driver = connect_chrome()
    say(f"  [OK] Terhubung. Tab aktif: {driver.current_url[:60]}...")

    say(f"\n[0] Cari frame list...")
    fr = find_list_frame(driver, timeout=12)
    if not fr:
        say("  [ERROR] Frame list tidak ditemukan.")
        say("  Pastikan halaman LIST Pemindahan Barang terbuka & login aktif.")
        sys.exit(1)
    say(f"  [OK] Frame: {fr}")

    # Loop proses tiap kode
    results = []
    for i, kode in enumerate(kodes, 1):
        ok, result = process_one_kode(driver, kode, fr, i, len(kodes))
        results.append((kode, ok, result))
        if i < len(kodes):
            say(f"\n  Jeda 2 detik sebelum kode berikutnya...")
            time.sleep(2)
            # re-find frame (mungkin berubah)
            fr2 = find_list_frame(driver, timeout=8)
            if fr2: fr = fr2

    # Summary
    say("\n" + "=" * 60)
    say("  RINGKASAN HASIL")
    say("=" * 60)
    success = 0
    for kode, ok, result in results:
        status = "OK" if ok else "FAIL"
        say(f"  [{status}] {kode} -> {result}")
        if ok: success += 1
    say(f"\n  Berhasil: {success}/{len(kodes)}")
    say(f"  Folder   : {DOWNLOAD_DIR}")
    say("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        say(f"\n[FATAL] {type(e).__name__}: {e}")
        traceback.print_exc()
        say("\nKirim error ini ke saya, jangan tutup dulu.")
    input("\nTekan Enter untuk keluar...")
