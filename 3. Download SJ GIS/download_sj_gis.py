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
    for (const i of inps){ if ((i.value||'').trim()===nomor && vis(i)) return true; }
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
      return {found:true, text:t.slice(0,80), path:[]};
    }
  }
  return {found:false, count:rows.length};
})(arguments[0]);
"""

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

def click_row_with_kode(driver, fr, kode):
    reframe(driver, fr)
    el = find_marked(driver, [], timeout=2)
    if el:
        return smart_click(driver, el)
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

def find_dokumen_button(driver):
    """Cari tombol Dokumen/Komentar/Lampiran di detail view."""
    switch_top(driver)
    for txt in DOKUMEN_TEXTS:
        ux = driver.execute_script(JS_FIND_MARK, txt, False)
        if ux:
            return ux
    return None

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
    say("  DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v2 TRIAL)")
    say("=" * 60)
    say(f"Folder download: {DOWNLOAD_DIR}")
    if not os.path.isdir(DOWNLOAD_DIR):
        say(f"[ERROR] Folder Downloads tidak ditemukan: {DOWNLOAD_DIR}")
        sys.exit(1)

    kode = input("\nMasukkan kode SJ (mis. IT.2026.09.19805): ").strip()
    if not kode:
        say("Kode kosong. Keluar."); sys.exit(1)
    if not KODE_RE.match(kode):
        say(f"[WARNING] Format kode tidak biasa: {kode} (tetap lanjut)")
    say(f"\nKode: {kode}")

    say("\n[1/7] Connect Chrome port 9222...")
    driver = connect_chrome()
    say(f"  [OK] Terhubung. Tab aktif: {driver.current_url}")

    say("\n[2/7] Cari frame list...")
    fr = find_list_frame(driver, timeout=12)
    if not fr:
        say("  [ERROR] Frame list tidak ditemukan.")
        say("  Pastikan halaman LIST Pemindahan Barang terbuka & login aktif.")
        sys.exit(1)
    say(f"  [OK] Frame: {fr}")

    say(f"\n[3/7] Search kode {kode} (via JS setVal)...")
    if not search_kode(driver, kode, fr):
        say("  [ERROR] Kode tidak ditemukan di grid setelah search.")
        say("  Kemungkinan: kode bukan transaksi tanggal hari ini (cek filter date),")
        say("  atau halaman list belum terbuka di tab aktif.")
        sys.exit(1)

    say("\n[4/7] Klik baris (buka detail)...")
    how = click_row_with_kode(driver, fr, kode)
    if not how:
        say("  [ERROR] Baris tidak bisa di-klik.")
        sys.exit(1)
    say(f"  [OK] Baris diklik via {how}. Tunggu detail terbuka...")
    if wait_detail_open(driver, kode, timeout=15):
        say("  [OK] Detail form terbuka.")
    else:
        say("  [WARNING] Detail form tidak terdeteksi (input kode). Lanjut tetap cari tombol Dokumen.")

    say('\n[5/7] Cari tombol "Dokumen/Komentar" di detail...')
    ux = find_dokumen_button(driver)
    if not ux:
        say('  [ERROR] Tombol Dokumen/Komentar tidak ditemukan di detail.')
        say('  Kirim screenshot halaman detail ke saya, saya cari selector yg benar.')
        sys.exit(1)
    say(f'  [OK] Ditemukan: "{ux.get("text","?")}"')
    el = find_marked(driver, ux["path"], timeout=5)
    if not el:
        clear_mark(driver, ux["path"])
        say("  [ERROR] Tombol Dokumen hilang sebelum diklik.")
        sys.exit(1)
    smart_click(driver, el); clear_mark(driver, ux["path"])
    say("  [OK] Diklik. Tunggu panel dokumen muncul...")
    time.sleep(3)

    say("\n[6/7] Dump panel dokumen + cari link download...")
    panel = dump_dokumen_panel(driver)
    if not panel:
        say("  [WARNING] Panel dokumen kosong / tidak ada link download yg terdeteksi.")
        say("  Mungkin panel belum kebuka, atau butuh klik tab 'Dokumen' spesifik.")
        say("  Saya tetap coba auto-download dari elemen apa pun yg ada.")
    else:
        say(f"  Ditemukan {len(panel)} elemen relevan:")
        for item in panel:
            say(f'    [{item["i"]}] <{item["tag"]}> text="{item["text"]}" href="{item["href"][:50]}" onclick="{item["onclick"][:40]}"')

    say("\n[7/7] Coba auto-download...")
    before = snapshot_downloads()
    if try_click_download_in_panel(driver, panel):
        say("  [..] Link download diklik, tunggu file (maks 60s)...")
        fname = wait_new_download(before, timeout=60)
        if fname:
            final = os.path.join(DOWNLOAD_DIR, fname)
            say(f"\n  [OK] File tersimpan: {final}")
            close_detail_tab(driver, kode)
            say("\n" + "=" * 60)
            say(f"  SELESAI! File: {fname}")
            say(f"  Lokasi  : {final}")
            say("=" * 60)
            return
        else:
            say(f"  [ERROR] Download tidak selesai 60s. Cek manual: {DOWNLOAD_DIR}")
    else:
        say("  [FAIL] Tidak ada link download otomatis yg bisa diklik.")
        say("")
        say("  === PENTING ===")
        say("  Kirim output ini (terutama bagian [6/7] dump) ke saya.")
        say("  Dari situ saya bisa lihat selector link download SJ yg benar,")
        say("  lalu update tool v3 buat auto-download.")
    # tutup tab detail biar bersih
    close_detail_tab(driver, kode)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        say(f"\n[FATAL] {type(e).__name__}: {e}")
        traceback.print_exc()
        say("\nKirim error ini ke saya, jangan tutup dulu.")
    input("\nTekan Enter untuk keluar...")
