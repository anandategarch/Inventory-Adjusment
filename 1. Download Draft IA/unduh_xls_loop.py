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
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
NOMOR_RE = re.compile(r"IA\.\d{4}\.\d{2}\.\d+")

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
    print(msg)
    sys.stdout.flush()

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
  var re = /IA\\.\\d{4}\\.\\d{2}\\.\\d+/;
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
  const re = /IA\\.\\d{4}\\.\\d{2}\\.\\d+/;
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
    end = time.time() + timeout
    while time.time() < end:
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
    for _ in range(300):
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
            stall += 1
            if stall >= 3:
                break
        else:
            stall = 0
        stepv = max(vp["ch"] - row_h, row_h)
        driver.execute_script(JS_SET_SCROLL, vp["st"] + stepv)
        time.sleep(0.2)

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
    smart_click(driver, el)
    clear_mark(driver, pr["path"])
    return True

def trigger_print_and_wait(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    settle(0.1)
    _focus_form(driver)
    settle(0.1)

    try:
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('p').key_up(Keys.CONTROL).perform()
        say("    Memicu cetak via Ctrl+P...")
        ux = wait_report_overlay(driver, timeout=12)
        if ux:
            return ux, "Ctrl+P"
    except Exception:
        pass

    if _click_print_button(driver):
        say("    Memicu cetak via tombol Cetak...")
        ux = wait_report_overlay(driver, timeout=15)
        if ux:
            return ux, "tombol Cetak"

    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    settle(0.1)
    _focus_form(driver)
    settle(0.1)
    try:
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('p').key_up(Keys.CONTROL).perform()
        say("    Retry cetak via Ctrl+P...")
        ux = wait_report_overlay(driver, timeout=12)
        if ux:
            return ux, "Ctrl+P (retry)"
    except Exception:
        pass

    return None, None

def close_report(driver):
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
    say(f"\n[{seq}/{limit}] {nomor}")
    try:
        recover_to_list(driver)
        if not find_list_frame(driver, timeout=8):
            raise AppError("E_LIST", "grid tidak ditemukan setelah recovery")

        say("  Klik baris...")
        how = click_row_by_nomor(driver, nomor, seq - 1, row_h)
        if not how:
            raise AppError("E_ROW", f"baris {nomor} tidak ditemukan")

        say("  Membuka detail...")
        driver.switch_to.default_content()
        if not wait_detail_open(driver, nomor, timeout=15):
            raise AppError("E_DETAIL", f"input {nomor} tidak muncul")

        say("  Menentukan Keterangan...")
        suffix = sanitize_suffix((suffix_map or {}).get(nomor, ""))
        if suffix:
            say(f"  Suffix (grid): {suffix}")
        else:
            suffix = read_keterangan_suffix(driver)
            if suffix:
                say(f"  Suffix (detail): {suffix}")
            else:
                say("  Keterangan kosong; nama file tetap asli.")

        say("  Memicu cetak...")
        ux, method = trigger_print_and_wait(driver)
        if not ux:
            raise AppError("E_PRINT", "overlay report tidak muncul")

        say("  Mengunduh XLS...")
        before = snapshot_downloads()
        el = find_marked(driver, ux["path"])
        if not el:
            clear_mark(driver, ux["path"])
            raise AppError("E_UNDUH", "tombol Unduh XLS hilang")
        smart_click(driver, el)
        clear_mark(driver, ux["path"])

        fname = wait_new_download(before, timeout=90)
        if not fname:
            raise AppError("E_DOWNLOAD", "file XLS tidak selesai")

        original_path = os.path.join(DOWNLOAD_DIR, fname)
        final_path = rename_with_suffix(original_path, suffix)
        final_name = os.path.basename(final_path)
        say(f"  File: {final_name}")

        say("  Menutup report & tab detail...")
        close_report(driver)
        close_detail_tab(driver, nomor)
        if not wait_detail_closed(driver, nomor, timeout=15):
            raise AppError("E_CLOSE_TAB", f"tab detail {nomor} masih terbuka")

        dt = time.time() - t0
        say(f"  Selesai ({dt:.1f} detik)")
        return True, final_name

    except AppError as e:
        penjelasan, saran = ERROR_CATALOG.get(e.code, ("-", "-"))
        say(f"  Gagal: {penjelasan}")
        say(f"  Saran: {saran}")
        return False, e.code
    except Exception as e:
        say(f"  Error: {type(e).__name__}: {e}")
        return False, "E_UNEXPECTED"

# ============================================================
# MAIN
# ============================================================
def main():
    say("Memulai loop unduh XLS (FULL SPEED)...")
    say(f"Folder download: {DOWNLOAD_DIR}")
    print()

    if not os.path.isdir(DOWNLOAD_DIR):
        say(f"Folder download tidak ditemukan: {DOWNLOAD_DIR}")
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            say("  Folder dibuat.")
        except Exception as e:
            say(f"  Gagal membuat folder: {e}")

    try:
        driver = connect_chrome()
    except AppError as e:
        penjelasan, saran = ERROR_CATALOG.get(e.code, ("-", "-"))
        say(f"Gagal: {penjelasan}")
        return 1
    except Exception as e:
        say(f"Error: {type(e).__name__}: {e}")
        return 1
    say("Terhubung ke Chrome debugging.")
    print()

    recover_to_list(driver)
    say("Mengumpulkan daftar transaksi + Keterangan dari grid...")
    order, row_h, suffix_map = collect_nomor_list(driver)
    if not order:
        say("  Gagal: tidak ada transaksi terbaca di grid.")
        return 1
    limit = len(order) if MAX_ROWS == 0 else min(MAX_ROWS, len(order))
    say(f"Ditemukan {len(order)} transaksi, akan diproses {limit}.")
    say(f"Suffix terbaca dari grid: {len(suffix_map)} baris.")
    print()

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
                    say(f"\nBerhenti: {consecutive} siklus gagal beruntun.")
                    break
    except KeyboardInterrupt:
        say("\nDihentikan manual.")

    total_dt = time.time() - t_start
    print()
    say("Rekap:")
    say(f"  Durasi: {total_dt:.1f} detik")
    say(f"  Berhasil: {len(hasil)}")
    for nomor, fname in hasil:
        say(f"    {nomor} -> {fname}")
    if gagal:
        say(f"  Gagal: {len(gagal)}")
        for nomor, code in gagal:
            say(f"    {nomor} ({code})")
    print()

    if len(hasil) > 0:
        say(f"Selesai. {len(hasil)} file berhasil diunduh.")
        return 0
    else:
        say("Tidak ada file yang berhasil diunduh.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        say(f"Error tak terduga: {type(e).__name__}: {e}")
        sys.exit(1)