"""
download_sj_gis.py  (v1 - TRIAL)
=================================
Download Surat Jalan (SJ) dari modul PEMINDAHAN BARANG Accurate Online (database GiS).
Alur: search kode -> klik baris (buka detail) -> cetak (Ctrl+P) -> unduh dari overlay.

Helper & pola di-REUSE dari tool "Download Draft IA" (unduh_xls_loop.py) yang sudah
terbukti jalan: connect_chrome, find_list_frame, smart_click, JS_FIND_MARK, JS_FIND_PRINT,
trigger_print_and_wait, wait_new_download, close_report, close_detail_tab.

Cara pakai:
  1. Buka Chrome dengan remote debugging:
       chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate, buka modul PEMINDAHAN BARANG (halaman LIST/tabel).
  3. python download_sj_gis.py  (atau double-click JALANKAN_SJ_GIS.bat)
  4. Masukkan kode SJ (mis. IT.2026.09.19805).

Output: file PDF/XLS tersimpan di folder Downloads.
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

# Tombol unduh di overlay: dicari dengan match "contains" (Unduh PDF / Unduh XLS / Unduh / dst)
UNDUH_TEXTS = ["Unduh", "Download", "Cetak PDF", "Simpan"]
# Ekstensi file hasil download yang diakui
DL_EXTS = (".pdf", ".xls", ".xlsx")

def say(msg):
    print(msg); sys.stdout.flush()

# ============================================================
# CHROME CONNECTION (sama kayak tool 1 & 2)
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
    """Cari iframe yg berisi grid SlickGrid / search box keyword."""
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

# ============================================================
# SMART CLICK (proven — Selenium ActionChains = trusted event)
# ============================================================
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
# JS HELPERS (reuse dari tool 1 — terbukti jalan dengan Accurate)
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

# Cari elemen by text (contains) lintas semua frame, tandai dengan data-fl-target
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

# Cari tombol Cetak (text "CETAK" atau icon print)
JS_FIND_PRINT = JS_VIS + """
return (function(){
  const ATTR='data-fl-target';
  function scan(doc, path){
    const cands = doc.querySelectorAll('button, a, span, div');
    for (const el of cands){
      if (!vis(el)) continue;
      const ti = (el.getAttribute('title')||'').toUpperCase();
      const txt = (el.innerText||'').trim().toUpperCase();
      const cls = (el.className||'').toUpperCase();
      const hasPrintIcon = !!el.querySelector('i[class*="print"], [class*="print"], .icon-print');
      const isPrintBtn = ti.includes('CETAK') || txt==='CETAK' || txt.includes('CETAK') ||
                         (hasPrintIcon && (txt==='' || txt.length < 20)) ||
                         cls.includes('PRINT');
      if (isPrintBtn && (el.tagName==='BUTTON' || el.tagName==='A' || el.getAttribute('onclick'))){
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

# Cek apakah detail form sudah kebuka (ada input dengan value = kode)
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

# Cari tombol close (×) pada tab detail
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
# SEARCH BY KODE (proven dari deteksi: input[name=keyword] + btn-search)
# ============================================================
def search_kode(driver, kode, fr):
    """Ketik kode di search box + klik btn-search. Return True kalau row kode muncul."""
    reframe(driver, fr)
    inps = driver.find_elements(By.CSS_SELECTOR, "input[name='keyword']")
    if not inps:
        inps = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
    if not inps:
        say("  [ERROR] Search box tidak ditemukan.")
        return False
    el = inps[0]
    try:
        el.clear()
        el.send_keys(kode)
        time.sleep(0.3)
    except Exception as e:
        say(f"  [ERROR] gagal ketik: {e}")
        return False
    # Klik btn-search (lebih reliable dari Enter sintetik)
    btns = driver.find_elements(By.CSS_SELECTOR, "button.btn-search")
    if btns:
        try: smart_click(driver, btns[0]); say("  [OK] btn-search diklik")
        except: pass
    else:
        try: el.send_keys(Keys.RETURN)
        except: pass
    # Tunggu row kode muncul (polling 10s)
    end = time.time() + 10
    while time.time() < end:
        reframe(driver, fr)
        for r in driver.find_elements(By.CSS_SELECTOR, ".slick-row"):
            try:
                txt = r.get_attribute("innerText") or r.text or ""
                if kode in txt: return True
            except: continue
        time.sleep(0.5)
    return False

def find_row_with_kode(driver, fr, kode):
    reframe(driver, fr)
    for r in driver.find_elements(By.CSS_SELECTOR, ".slick-row"):
        try:
            if not r.is_displayed(): continue
            txt = r.get_attribute("innerText") or r.text or ""
            if kode in txt: return r
        except: continue
    return None

# ============================================================
# DETAIL + PRINT + DOWNLOAD FLOW (proven dari tool 1)
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

def wait_report_overlay(driver, timeout=20):
    """Tunggu overlay report muncul. Cari tombol unduh (match 'Unduh' -> Unduh PDF/XLS/dst)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            switch_top(driver)
            for txt in UNDUH_TEXTS:
                ux = driver.execute_script(JS_FIND_MARK, txt, False)
                if ux: return ux
        except: pass
        time.sleep(0.3)
    return None

def trigger_print_and_wait(driver):
    """Ctrl+P dulu, fallback klik tombol Cetak."""
    try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except: pass
    time.sleep(0.1)
    # Focus form biar Ctrl+P kena halaman detail
    try:
        driver.execute_script("""
            let el = document.querySelector('.slick-viewport, .form-group input, .tab-content, [class*="detail"], .transaction-form');
            if (!el) el = document.body;
            if (el) { el.focus(); el.click(); }
        """)
    except: pass
    time.sleep(0.1)
    # Ctrl+P
    try:
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('p').key_up(Keys.CONTROL).perform()
        say("  [..] Ctrl+P dikirim, tunggu overlay...")
        ux = wait_report_overlay(driver, timeout=15)
        if ux: return ux, "Ctrl+P"
    except: pass
    # Fallback: klik tombol Cetak
    try:
        switch_top(driver)
        pr = driver.execute_script(JS_FIND_PRINT)
        if pr:
            el = find_marked(driver, pr["path"], timeout=5)
            if el:
                smart_click(driver, el); clear_mark(driver, pr["path"])
                say("  [..] Tombol Cetak diklik, tunggu overlay...")
                ux = wait_report_overlay(driver, timeout=15)
                if ux: return ux, "tombol Cetak"
    except: pass
    # Retry Ctrl+P
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform(); time.sleep(0.1)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('p').key_up(Keys.CONTROL).perform()
        say("  [..] Retry Ctrl+P...")
        ux = wait_report_overlay(driver, timeout=12)
        if ux: return ux, "Ctrl+P (retry)"
    except: pass
    return None, None

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

def close_report(driver):
    try:
        switch_top(driver)
        tp = driver.execute_script(JS_FIND_MARK, "Tutup", True)
        if tp:
            el = find_marked(driver, tp["path"], timeout=3)
            if el: smart_click(driver, el)
            clear_mark(driver, tp["path"])
    except: pass

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
    say("  DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v1 TRIAL)")
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

    say("\n[1/6] Connect Chrome port 9222...")
    driver = connect_chrome()
    say(f"  [OK] Terhubung. Tab aktif: {driver.current_url}")

    say("\n[2/6] Cari frame list...")
    fr = find_list_frame(driver, timeout=12)
    if not fr:
        say("  [ERROR] Frame list tidak ditemukan.")
        say("  Pastikan halaman LIST Pemindahan Barang terbuka & login aktif.")
        sys.exit(1)
    say(f"  [OK] Frame: {fr}")

    say(f"\n[3/6] Search kode {kode}...")
    if not search_kode(driver, kode, fr):
        say("  [ERROR] Kode tidak ditemukan di grid setelah search (10s).")
        say("  Kemungkinan: kode bukan transaksi tanggal hari ini, atau filter date perlu diubah.")
        sys.exit(1)
    say("  [OK] Kode ditemukan di grid.")

    say("\n[4/6] Klik baris (buka detail)...")
    row = find_row_with_kode(driver, fr, kode)
    if not row:
        say("  [ERROR] Baris tidak bisa diakses lagi setelah search.")
        sys.exit(1)
    how = smart_click(driver, row)
    say(f"  [OK] Baris diklik via {how}. Tunggu detail terbuka...")
    if wait_detail_open(driver, kode, timeout=15):
        say("  [OK] Detail form terbuka.")
    else:
        say("  [WARNING] Detail form tidak terdeteksi (input kode). Lanjut tetap cetak.")

    say("\n[5/6] Trigger cetak (Ctrl+P / tombol Cetak)...")
    ux, method = trigger_print_and_wait(driver)
    if not ux:
        say("  [ERROR] Overlay report tidak muncul setelah Ctrl+P + Cetak fallback.")
        say("  Saran: coba klik baris manual lalu Ctrl+P manual, lihat apa yg muncul.")
        say("  Kirim screenshot overlay itu ke saya, saya update selector.")
        sys.exit(1)
    say(f"  [OK] Overlay muncul via {method}. Tombol unduh ditemukan: '{ux.get('text','?')}'")

    say("\n[6/6] Klik tombol Unduh + tunggu download (maks 90s)...")
    before = snapshot_downloads()
    el = find_marked(driver, ux["path"])
    if not el:
        clear_mark(driver, ux["path"])
        say("  [ERROR] Tombol Unduh hilang dari overlay sebelum diklik.")
        sys.exit(1)
    smart_click(driver, el); clear_mark(driver, ux["path"])
    fname = wait_new_download(before, timeout=90)
    if not fname:
        say(f"  [ERROR] Download tidak selesai dalam 90 detik. Cek manual: {DOWNLOAD_DIR}")
        sys.exit(1)
    final = os.path.join(DOWNLOAD_DIR, fname)
    say(f"  [OK] File tersimpan: {final}")

    say("\nMenutup overlay + tab detail...")
    close_report(driver)
    close_detail_tab(driver, kode)

    say("\n" + "=" * 60)
    say(f"  SELESAI! File: {fname}")
    say(f"  Lokasi  : {final}")
    say("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        say(f"\n[FATAL] {type(e).__name__}: {e}")
        traceback.print_exc()
        say("\nKirim error ini ke saya, jangan tutup dulu.")
    input("\nTekan Enter untuk keluar...")
