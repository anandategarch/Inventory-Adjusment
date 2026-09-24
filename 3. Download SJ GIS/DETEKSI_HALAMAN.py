"""
DETEKSI_HALAMAN.py  (TRIAL - DIAGNOSTIC TOOL)
=============================================
Tool DETEKSI struktur halaman untuk modul Pemindahan Barang (SJ GIS) Accurate Online.

Tujuan: jalankan SEKALI di laptop Anda, lalu kirim output-nya ke saya (Z.ai)
biar saya bisa tulis tool "Download SJ GIS" yang pasti jalan tanpa nebak-nebak.

Cara pakai:
  1. Buka Chrome dengan remote debugging (kalau belum):
       chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate Online, lalu buka modul PEMINDAHAN BARANG (halaman LIST/tabel).
  3. Double-click JALANKAN_DETEKSI.bat  (atau:  python DETEKSI_HALAMAN.py)
  4. Saat diminta, masukkan kode (default: IT.2026.09.19805) lalu Enter.
  5. Tunggu sampai selesai (cetak semua struktur halaman + klik baris + cetak lagi).
  6. Kirim 2 hal ini ke saya:
       - isi Command Prompt (copy semua, klik kanan > Select All > Enter)
       - file  deteksi_page.html  +  deteksi_page_after_click.html  (di folder yang sama)

Aman: script ini TIDAK melakukan download / simpan / hapus. Cuma baca + ketik + klik 1 baris.
"""
import os
import sys
import time
import socket
import json
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException, NoSuchElementException, StaleElementReferenceException,
)

# ============================================================
# CONFIG
# ============================================================
DEBUG_PORT = 9222
DEFAULT_KODE = "IT.2026.09.19805"
OUT_TXT = "deteksi_output.txt"
OUT_HTML = "deteksi_page.html"
OUT_HTML_AFTER = "deteksi_page_after_click.html"

# ============================================================
# OUTPUT TEE: cetak ke console + simpan ke file
# ============================================================
class Tee:
    def __init__(self, path):
        self.file = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout
    def write(self, s):
        self.stdout.write(s)
        self.file.write(s)
        self.stdout.flush()
    def flush(self):
        self.stdout.flush()
        self.file.flush()

def banner(s):
    line = "=" * 78
    print("\n" + line); print(s); print(line); sys.stdout.flush()

def say(s):
    print(s); sys.stdout.flush()

# ============================================================
# CONNECT KE CHROME (sama pola kayak tool 1 & 2)
# ============================================================
def connect_chrome():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", DEBUG_PORT)) != 0:
            say(f"[ERROR] Port debugging {DEBUG_PORT} tidak aktif.")
            say(f"        Buka Chrome dulu dengan: chrome.exe --remote-debugging-port={DEBUG_PORT} --user-data-dir=\"C:\\ChromeDebugProfile\"")
            sys.exit(1)
    opt = Options()
    opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    return webdriver.Chrome(options=opt)

# ============================================================
# CARI FRAME yang berisi grid/ konten utama
# (Accurate Online biasanya bungkus semuanya di iframe)
# ============================================================
def switch_top(driver):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

def find_content_frame(driver, timeout=12):
    """Cari iframe yang di dalamnya ada grid SlickGrid / search box / konten utama.
    Return (path_frame_yang_aktif) atau None. Frame sudah di-switch."""
    start = time.time()
    last_seen = None
    while time.time() - start < timeout:
        switch_top(driver)
        # Marker Accurate: .slick-viewport (grid), atau input search, atau .page-title
        markers = driver.find_elements(By.CSS_SELECTOR,
            ".slick-viewport, .slick-row, input[type='text'], input[type='search'], .page-title, [class*='search']")
        if markers:
            last_seen = "top"
            return "top"
        # telusur iframe
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for idx, ifr in enumerate(iframes):
            try:
                switch_top(driver)
                driver.switch_to.frame(ifr)
                markers = driver.find_elements(By.CSS_SELECTOR,
                    ".slick-viewport, .slick-row, input[type='text'], input[type='search'], .page-title, [class*='search']")
                if markers:
                    last_seen = f"iframe[{idx}]"
                    return last_seen
            except Exception:
                continue
        switch_top(driver)
        time.sleep(0.3)
    return last_seen  # mungkin None

# ============================================================
# DUMP struktur halaman (cetak rapi)
# ============================================================
def safe_attr(el, attr):
    try:
        v = el.get_attribute(attr)
        return v if v else ""
    except Exception:
        return ""

def describe(el, idx):
    """Bikin 1 baris deskripsi elemen: tag | id | class | name | placeholder | text."""
    try:
        tag = el.tag_name or "?"
    except Exception:
        tag = "?"
    idv = safe_attr(el, "id")
    cls = safe_attr(el, "class")
    name = safe_attr(el, "name")
    placeholder = safe_attr(el, "placeholder")
    aria = safe_attr(el, "aria-label")
    role = safe_attr(el, "role")
    typev = safe_attr(el, "type")
    onclick = safe_attr(el, "onclick")
    href = safe_attr(el, "href")
    try:
        text = (el.text or "").strip().replace("\n", " ")
        if len(text) > 60:
            text = text[:60] + "..."
    except Exception:
        text = ""
    parts = [f"[{idx}]", f"<{tag}>"]
    if idv: parts.append(f"id={idv}")
    if cls: parts.append(f"class={cls[:40]}")
    if name: parts.append(f"name={name}")
    if typev: parts.append(f"type={typev}")
    if placeholder: parts.append(f"placeholder={placeholder[:30]}")
    if aria: parts.append(f"aria={aria[:30]}")
    if role: parts.append(f"role={role}")
    if onclick: parts.append(f"onclick={onclick[:30]}")
    if href: parts.append(f"href={href[:40]}")
    if text: parts.append(f"text={text}")
    return " ".join(parts)

def dump_section(title, elements, max_items=40):
    print(f"\n--- {title} (total {len(elements)}) ---")
    if not elements:
        print("  (kosong)")
        return
    for i, el in enumerate(elements[:max_items]):
        try:
            print("  " + describe(el, i))
        except Exception as e:
            print(f"  [{i}] <error membaca: {e}>")
    if len(elements) > max_items:
        print(f"  ... dan {len(elements)-max_items} lainnya")

def dump_all(driver, label):
    """Cetak semua struktur penting dari frame aktif saat ini."""
    banner(f"SNAPSHOT: {label}")
    try:
        say(f"URL saat ini    : {driver.current_url}")
    except Exception as e:
        say(f"URL saat ini    : <{e}>")
    try:
        say(f"Title           : {driver.title}")
    except Exception as e:
        say(f"Title           : <{e}>")
    try:
        wins = driver.window_handles
        say(f"Window/tab      : {len(wins)} handle(s)")
        for i, h in enumerate(wins):
            try:
                driver.switch_to.window(h)
                say(f"  [{i}] handle={h[:12]}... url={driver.current_url}")
            except Exception as e:
                say(f"  [{i}] <{e}>")
        # kembali ke tab terakhir biar stabil
        driver.switch_to.window(wins[-1])
    except Exception:
        pass

    # 1) Semua input / search box / textarea
    inputs = driver.find_elements(By.CSS_SELECTOR,
        "input[type='text'], input[type='search'], input[type='tel'], input:not([type]), textarea")
    dump_section("INPUT / SEARCH BOX", inputs)

    # 2) Semua button / tombol
    buttons = driver.find_elements(By.CSS_SELECTOR, "button, [role='button'], input[type='button'], input[type='submit']")
    dump_section("BUTTON / TOMBOL", buttons)

    # 3) Semua link
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    dump_section("LINK", links)

    # 4) Grid SlickGrid (Accurate pakai ini) - rows + header
    headers = driver.find_elements(By.CSS_SELECTOR, ".slick-header-column, .slick-column-name, th")
    dump_section("GRID HEADER", headers)
    rows = driver.find_elements(By.CSS_SELECTOR, ".slick-row, .slick-cell")
    dump_section("GRID ROW/CELL (.slick-*)", rows)

    # 5) Elemen yg text-nya mengandung kode atau kata kunci download
    try:
        all_text = driver.execute_script("""
        var out=[];
        var nodes = document.querySelectorAll('a, span, div, li, label, td, button, p');
        var kode = arguments[0].toUpperCase();
        for (var i=0;i<nodes.length;i++){
          var t = (nodes[i].innerText||nodes[i].textContent||'').trim();
          if (!t) continue;
          var up = t.toUpperCase();
          if (up.indexOf(kode) !== -1 || up.indexOf('UNDUH') !== -1 || up.indexOf('DOWNLOAD') !== -1
              || up.indexOf('CETAK') !== -1 || up.indexOf('PRINT') !== -1 || up.indexOf('PDF') !== -1
              || up.indexOf('XLS') !== -1 || up.indexOf('EXPORT') !== -1 || up.indexOf('EKSPOR') !== -1) {
            var rect = nodes[i].getBoundingClientRect();
            if (rect.width>0 && rect.height>0){
              out.push({tag: nodes[i].tagName, id: nodes[i].id||'',
                        cls: (nodes[i].className||'').toString().slice(0,50),
                        text: t.slice(0,80)});
            }
          }
          if (out.length>80) break;
        }
        return out;
        """, DEFAULT_KODE)
        print(f"\n--- ELEMEN TEKS RELEVAN (kode/UNDUH/CETAK/DOWNLOAD/PDF/XLS) ---")
        if not all_text:
            print("  (tidak ditemukan elemen dengan teks tersebut)")
        for i, x in enumerate(all_text):
            print(f"  [{i}] <{x.get('tag')}> id={x.get('id')} class={x.get('cls')} text={x.get('text')}")
    except Exception as e:
        print(f"  <error dump teks: {e}>")

    # 6) Console errors via JS hook (kalau ada window.__consoleErr)
    try:
        errs = driver.execute_script(
            "return (window.__consoleErr || []).slice(0, 50);") or []
        print(f"\n--- CONSOLE ERRORS (yang tercatat setelah script ini jalan) ---")
        if not errs:
            print("  (kosong / belum ada)")
        for e in errs:
            print(f"  - {e}")
    except Exception as e:
        print(f"  <error baca console: {e}>")

def save_html(driver, path):
    try:
        html = driver.page_source
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        say(f"[OK] HTML snapshot disimpan: {os.path.abspath(path)}")
    except Exception as e:
        say(f"[ERROR] gagal simpan HTML: {e}")

# ============================================================
# MAIN
# ============================================================
def main():
    print(__doc__)
    # Tee output ke file
    sys.stdout = Tee(OUT_TXT)
    banner("MULAI DETEKSI HALAMAN - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    say(f"Python: {sys.version.split()[0]} | Selenium: {webdriver.__version__ if hasattr(webdriver,'__version__') else '?'}")

    kode = input(f"\nMasukkan kode SJ (default: {DEFAULT_KODE}): ").strip()
    if not kode:
        kode = DEFAULT_KODE
    say(f"Kode dipakai: {kode}")

    say("\n[1/6] Menghubungkan Chrome (port 9222)...")
    driver = connect_chrome()
    say(f"[OK] Terhubung. Tab aktif: {driver.current_url}")

    # Pasang hook console error biar ke catch errors yg muncul saat search
    try:
        driver.execute_script("""
        window.__consoleErr = [];
        ['error'].forEach(function(t){
          var orig = console[t];
          console[t] = function(){
            try { window.__consoleErr.push(Array.from(arguments).map(function(a){
              try { return typeof a==='object'? JSON.stringify(a) : String(a); } catch(e){ return String(a); }
            }).join(' ')); } catch(e){}
            orig.apply(console, arguments);
          };
        });
        window.addEventListener('error', function(e){
          try { window.__consoleErr.push('PAGE_ERROR: ' + (e.message||'') + ' @ ' + (e.filename||'')+':'+(e.lineno||'')); } catch(x){}
        });
        """)
        say("[OK] Console error hook terpasang.")
    except Exception as e:
        say(f"[note] console hook gagal dipasang: {e} (lanjut aja)")

    say("\n[2/6] Mencari frame / konten utama...")
    frame = find_content_frame(driver, timeout=12)
    if frame:
        say(f"[OK] Konten ditemukan di: {frame}")
    else:
        say("[!] Konten tidak ditemukan otomatis. Lanjut di top frame.")

    say("\n[3/6] Snapshot SEBELUM search (struktur halaman awal)...")
    dump_all(driver, "SEBELUM SEARCH")

    say("\n[4/6] Mencari search box & mengetik kode...")
    # Pilih search box: prioritas input[type=search], lalu placeholder mengandung cari/search/filter/no/nomor
    # kalau nggak ada, ambil input[type=text] pertama yang visible.
    chosen = None
    candidates = driver.find_elements(By.CSS_SELECTOR,
        "input[type='search'], input[type='text'], input:not([type]), textarea")
    say(f"  Kandidat input: {len(candidates)}")
    for i, el in enumerate(candidates):
        try:
            if not el.is_displayed():
                continue
            ph = (safe_attr(el, "placeholder") or "").lower()
            aria = (safe_attr(el, "aria-label") or "").lower()
            name = (safe_attr(el, "name") or "").lower()
            idv = (safe_attr(el, "id") or "").lower()
            cls = (safe_attr(el, "class") or "").lower()
            score = 0
            for kw in ("search", "cari", "filter", "no", "nomor", "cari:", "pencarian"):
                if kw in ph or kw in aria or kw in name or kw in idv or kw in cls:
                    score += 1
            if score > 0:
                say(f"  >> kandidat kuat [{i}]: {describe(el, i)} (skor={score})")
                if chosen is None:
                    chosen = el
        except Exception:
            continue
    if chosen is None:
        # ambil visible pertama
        for el in candidates:
            try:
                if el.is_displayed():
                    chosen = el
                    say(f"  >> pakai input visible pertama: {describe(el, 0)}")
                    break
            except Exception:
                continue
    if chosen is None:
        say("[ERROR] Tidak ada search box / input yang bisa dipakai.")
        say("        Kirim output ini ke saya, nanti saya cari selector manual.")
    else:
        try:
            chosen.click()
            time.sleep(0.3)
            chosen.clear()
            time.sleep(0.2)
            chosen.send_keys(kode)
            time.sleep(0.3)
            chosen.send_keys(Keys.RETURN)
            say(f"[OK] Diketik & Enter: {kode}")
        except Exception as e:
            say(f"[ERROR] gagal ketik/enter: {e}")

    say("\n[5/6] Tunggu loading 5 detik, lalu snapshot SETELAH search...")
    time.sleep(5)
    # refresh frame (kalau DOM berubah)
    if frame and frame != "top":
        try:
            switch_top(driver)
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            idx = int(frame.split("[")[1].split("]")[0]) if "[" in frame else -1
            if 0 <= idx < len(iframes):
                driver.switch_to.frame(iframes[idx])
        except Exception:
            pass
    dump_all(driver, "SETELAH SEARCH")
    save_html(driver, OUT_HTML)

    # Coba klik baris pertama yang text-nya mengandung kode
    say("\n[6/6] Mencoba KLIK baris hasil (row label)...")
    clicked_el = None
    # Cari baris slick-row yang mengandung kode
    rows = driver.find_elements(By.CSS_SELECTOR, ".slick-row, tr, [role='row']")
    say(f"  Kandidat baris: {len(rows)}")
    for i, r in enumerate(rows[:50]):
        try:
            txt = (r.text or "").strip()
            if kode in txt or kode.replace("IT.", "IT.") in txt:
                say(f"  >> ketemu baris [{i}] berisi kode: {txt[:80]}")
                r.click()
                clicked_el = r
                break
        except Exception:
            continue
    if clicked_el is None:
        # fallback: cari elemen apa saja yg text = kode
        try:
            els = driver.find_elements(By.XPATH, f"//*[contains(text(),'{kode}')]")
            say(f"  Fallback XPath contains: {len(els)} elemen")
            for el in els[:10]:
                try:
                    if el.is_displayed():
                        say(f"  >> klik elemen: tag={el.tag_name} text={(el.text or '')[:60]}")
                        el.click()
                        clicked_el = el
                        break
                except Exception:
                    continue
        except Exception as e:
            say(f"  fallback xpath gagal: {e}")
    if clicked_el is None:
        say("[!] Tidak ada baris/elemen berisi kode yg bisa diklik otomatis.")
        say("    Kirim output ini + screenshot manual halaman setelah search supaya saya tulis selector yg benar.")

    if clicked_el is not None:
        say("\nMenunggu 5 detik setelah klik baris...")
        time.sleep(5)
        # refresh frame
        if frame and frame != "top":
            try:
                switch_top(driver)
                iframes = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                idx = int(frame.split("[")[1].split("]")[0]) if "[" in frame else -1
                if 0 <= idx < len(iframes):
                    driver.switch_to.frame(iframes[idx])
            except Exception:
                pass
        dump_all(driver, "SETELAH KLIK BARIS")
        save_html(driver, OUT_HTML_AFTER)

    banner("DETEKSI SELESAI")
    say("Kirim ke saya (Z.ai):")
    say(f"  1. Isi Command Prompt ini (select all -> enter) ATAU file {OUT_TXT}")
    say(f"  2. File {OUT_HTML}" + (f" dan {OUT_HTML_AFTER}" if clicked_el else ""))
    say("Dari situ saya tulis tool 'Download SJ GIS' yang benar-benar jalan. ✅")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("\nKirim error ini + output di atas ke saya. Jangan tutup dulu.")
    input("\nTekan Enter untuk keluar...")
