"""DETEKSI_HALAMAN.py - Trial diagnostic untuk Download SJ GIS (Pemindahan Barang, Accurate).
Cara pakai:
  1. Buka Chrome: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate, buka halaman LIST Pemindahan Barang.
  3. python DETEKSI_HALAMAN.py  (atau double-click JALANKAN_DETEKSI.bat)
  4. Masukkan kode (default IT.2026.09.19805), Enter, tunggu selesai.
Aman: cuma BACA + KETIK + KLIK 1 baris. Tidak download/simpan/hapus.
Kirim ke saya: (1) isi Command Prompt, (2) file deteksi_page*.html"""
import sys, time, socket, traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

PORT = 9222
KODE_DEF = "IT.2026.09.19805"

def conn():
    s = socket.socket(); s.settimeout(0.5)
    if s.connect_ex(("127.0.0.1", PORT)) != 0:
        sys.exit(f"Port {PORT} mati. Buka Chrome: chrome.exe --remote-debugging-port={PORT} --user-data-dir=\"C:\\ChromeDebugProfile\"")
    s.close()
    o = Options(); o.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORT}")
    return webdriver.Chrome(options=o)

def top(d):
    try: d.switch_to.default_content()
    except: pass

def find_frame(d, t=12):
    end = time.time() + t
    SEL = ".slick-viewport,.slick-row,input[type='text'],input[type='search'],[class*='search']"
    while time.time() < end:
        top(d)
        if d.find_elements(By.CSS_SELECTOR, SEL): return "top"
        for i, f in enumerate(d.find_elements(By.CSS_SELECTOR, "iframe,frame")):
            try:
                top(d); d.switch_to.frame(f)
                if d.find_elements(By.CSS_SELECTOR, SEL): return f"iframe[{i}]"
            except: pass
        top(d); time.sleep(0.3)
    return None

def g(el, a): return el.get_attribute(a) or ""

def desc(el, i):
    t = (el.text or "").strip().replace("\n", " ")[:50]
    return (f"[{i}] <{el.tag_name}> id={g(el,'id')} class={g(el,'class')[:35]} "
            f"name={g(el,'name')} placeholder={g(el,'placeholder')[:25]} "
            f"aria={g(el,'aria-label')[:25]} type={g(el,'type')} text={t}")

def dump(d, label):
    print("\n" + "="*70); print(label); print("="*70)
    try: print("URL:", d.current_url)
    except Exception as e: print("URL err:", e)
    try: print("Title:", d.title)
    except: pass
    try: print("Tabs:", len(d.window_handles))
    except: pass
    for name, sel, lim in [
        ("INPUT", "input[type='text'],input[type='search'],input:not([type]),textarea", 25),
        ("BUTTON", "button,[role='button'],input[type='button'],input[type='submit']", 20),
        ("LINK", "a[href]", 20),
        ("GRID-HEADER", ".slick-header-column,.slick-column-name,th", 15),
        ("GRID-ROW", ".slick-row,tr,[role='row']", 20),
    ]:
        els = d.find_elements(By.CSS_SELECTOR, sel)
        print(f"\n--- {name} ({len(els)}) ---")
        for i, e in enumerate(els[:lim]):
            try: print("  " + desc(e, i))
            except Exception as ex: print(f"  [{i}] err {ex}")
    try:
        r = d.execute_script("""var o=[];var n=document.querySelectorAll('a,span,div,li,label,td,button,p');
        var k=arguments[0].toUpperCase();
        for(var i=0;i<n.length;i++){var t=(n[i].innerText||'').trim();if(!t)continue;var u=t.toUpperCase();
        if(u.indexOf(k)!=-1||u.indexOf('UNDUH')!=-1||u.indexOf('DOWNLOAD')!=-1||u.indexOf('CETAK')!=-1
        ||u.indexOf('PRINT')!=-1||u.indexOf('PDF')!=-1||u.indexOf('XLS')!=-1||u.indexOf('EKSPOR')!=-1){
        var r=n[i].getBoundingClientRect();if(r.width>0&&r.height>0)
        o.push({tag:n[i].tagName,id:n[i].id||'',cls:(n[i].className||'').toString().slice(0,40),text:t.slice(0,70)});}
        if(o.length>60)break;}return o;""", KODE_DEF)
        print(f"\n--- TEKS RELEVAN (kode/UNDUH/CETAK/DOWNLOAD/PDF/XLS) ({len(r)}) ---")
        for i, x in enumerate(r): print(f"  [{i}] <{x['tag']}> id={x['id']} class={x['cls']} text={x['text']}")
    except Exception as e: print("  teks relevan err:", e)

def save_html(d, p):
    try:
        open(p, "w", encoding="utf-8").write(d.page_source)
        print("[OK] simpan", p)
    except Exception as e: print("[ERR] simpan html:", e)

def reframe(d, fr):
    if fr and fr != "top":
        try:
            top(d); ifs = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
            idx = int(fr.split("[")[1].split("]")[0]) if "[" in fr else -1
            if 0 <= idx < len(ifs): d.switch_to.frame(ifs[idx])
        except: pass

def main():
    kode = input(f"Kode SJ (default {KODE_DEF}): ").strip() or KODE_DEF
    print("Kode:", kode)
    print("\n[1/5] connect Chrome 9222...")
    d = conn(); print("OK", d.current_url)
    try:
        d.execute_script("window.__e=[];['error'].forEach(function(t){var o=console[t];"
                         "console[t]=function(){try{window.__e.push(Array.from(arguments).map(String).join(' '));}"
                         "catch(x){}o.apply(console,arguments);};});")
    except: pass
    print("\n[2/5] cari frame..."); fr = find_frame(d, 12); print("frame:", fr)
    print("\n[3/5] snapshot SEBELUM search..."); dump(d, "SEBELUM SEARCH"); save_html(d, "deteksi_page.html")
    print("\n[4/5] cari search box + ketik kode...")
    chosen = None
    cands = d.find_elements(By.CSS_SELECTOR, "input[type='search'],input[type='text'],input:not([type]),textarea")
    for i, e in enumerate(cands):
        try:
            if not e.is_displayed(): continue
            s = (g(e,'placeholder')+g(e,'aria-label')+g(e,'name')+g(e,'id')+g(e,'class')).lower()
            if any(k in s for k in ('search','cari','filter','nomor','no','pencarian')):
                print("  pilih:", desc(e, i)); chosen = e; break
        except: pass
    if chosen is None:
        for e in cands:
            try:
                if e.is_displayed(): chosen = e; print("  pilih (visible pertama):", desc(e, 0)); break
            except: pass
    if chosen:
        try:
            chosen.click(); time.sleep(0.2); chosen.clear(); time.sleep(0.1)
            chosen.send_keys(kode); time.sleep(0.2); chosen.send_keys(Keys.RETURN)
            print("  OK diketik + enter")
        except Exception as e: print("  ERR ketik:", e)
    else:
        print("  Tidak ada input terlihat. Kirim output ini ke saya.")
    print("\n  tunggu 5s..."); time.sleep(5); reframe(d, fr)
    print("\n[5/5] snapshot SETELAH search + cari baris berisi kode...")
    dump(d, "SETELAH SEARCH")
    clicked = None
    rows = d.find_elements(By.CSS_SELECTOR, ".slick-row,tr,[role='row']")
    print(f"\n  cari baris berisi kode di {len(rows)} baris...")
    for i, r in enumerate(rows[:50]):
        try:
            if kode in (r.text or ''):
                print(f"  >> klik baris [{i}]: {(r.text or '')[:70]}"); r.click(); clicked = r; break
        except: pass
    if not clicked:
        try:
            for el in d.find_elements(By.XPATH, f"//*[contains(text(),'{kode}')]")[:10]:
                if el.is_displayed():
                    print(f"  >> klik elemen: <{el.tag_name}> {(el.text or '')[:50]}"); el.click(); clicked = el; break
        except: pass
    if clicked:
        print("\n  tunggu 5s..."); time.sleep(5); reframe(d, fr)
        dump(d, "SETELAH KLIK BARIS"); save_html(d, "deteksi_page_after_click.html")
    else:
        print("  Tidak ada baris/elemen berisi kode. Kirim output + screenshot manual.")
    try:
        e = d.execute_script("return window.__e||[]")
        print("\n--- CONSOLE ERRORS (selama script jalan) ---")
        for x in (e or [])[:30]: print("  -", x)
    except: pass
    print("\n" + "="*70); print("DETEKSI SELESAI"); print("="*70)
    print("Kirim ke saya: (1) isi Command Prompt ini, (2) file deteksi_page*.html")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"\nFATAL {type(e).__name__}: {e}"); traceback.print_exc()
    input("\nEnter untuk keluar...")
