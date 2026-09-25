"""
download_sj_gis.py  (v8.9)
=========================
Download Surat Jalan (SJ) dari modul PEMINDAHAN BARANG Accurate Online (database GiS).

PERBAIKAN v8.9 (dari v8.8):
  - TUJUAN: fix 2 bug dari v8.8 run (3 kodes: 19805 FAIL E_DOWNLOAD_ICON, 20451 OK,
    20447 FAIL E_DOWNLOAD_ICON [no document — expected]).
  - BUG 1 (19805 E_DOWNLOAD_ICON intermittent): dropdown <a> click via ActionChains
    (smart_click) NGGAK reliably trigger Accurate jQuery dropdown <a> handler —
    attachment panel nggak kebuka -> E_DOWNLOAD_ICON. 20451 worked (lucky), 19805
    failed. Same bug class kayak cell click (v8.1) + btnCommentAttachment (v8.3),
    both fixed dgn JS clickSeq.
    FIX: click_first_dropdown_item PRIMARY = JS_CLICK_SEQ_SINGLE (native MouseEvent
    dispatch: pointerdown+mousedown+pointerup+mouseup+click). ActionChains (smart_click)
    sebagai FALLBACK. Konstanta JS_CLICK_SEQ_SINGLE SUDAH ADA (di-add v8.4 buat
    btnCommentAttachment) — dipake lg utk dropdown <a>.
  - BUG 2 (literal 'Tanggal' di filename): user clarify 'Tanggal' di filename format
    {kode}_Tanggal_{cabang}.{ext} should be ACTUAL DATE VALUE dari detail form
    (input[name='transDate'], e.g. '24/09/2026'), BUKAN literal word 'Tanggal'.
    Dari v8.8 dump utk 20451: [14] INPUT:transDate value='24/09/2026'.
    FIX: tambah extract_tanggal_value() baca input[name='transDate'].value. Format:
    replace '/' -> '-' jadi '24-09-2026' (readability), lalu sanitize_for_filename.
    Fallback literal 'Tanggal' kalau nggak terbaca. rename_download_file kini
    signature (kode, tanggal, cabang) -> {kode}_{tanggal}_{cabang}.{ext}.
    Contoh: IT.2026.09.20451_24-09-2026_1023.SKTADI.jpg
  - Download flow steps 1-7 (search -> cell -> detail -> btnCommentAttachment ->
    dropdown -> attachment -> download) TIDAK diubah, kecuali: click method utk
    dropdown <a> (Bug 1, step 4) + rename (Bug 2, step 7.7). Cabang extraction
    (proven working di 20451) TIDAK diubah. close_detail_tab + step 8.5 untouched.

PERBAIKAN v8.8 (dari v8.7):
  - USER CONFIRMED (no more assumptions):
    1. btnToggleList adalah TOGGLE (sekali klik buka list, sekali lg tutup list).
       BUKAN "always show list". v8.7 recover_to_list_view klik btnToggleList di AWAL
       tiap kode iteration, tapi page SUDAH di list view -> klik itu MENUTUP list ->
       search box hidden -> E_SEARCH utk SEMUA kode. Ini WRONG assumption.
    2. Setelah close detail tab (klik X), page OTOMATIS balik ke list view (dgn
       loading delay). Nggak perlu klik apa2.
    3. Saat tool mulai (kode pertama), page SUDAH di list view. Nggak butuh
       recovery action utk kode 1.
  - FIX 1: HAPUS recover_to_list_view ENTIRELY (function definition + step 0/8 call
    di process_one_kode + fr re-find after it). Download flow steps 1-8 unchanged.
  - FIX 2: close_detail_tab REWRITE dgn VERIFY + RETRY. Klik i.icon-cancel-2.smaller
    SEKALI nggak tentu langsung close (user confirm: ada loading setelah close).
    Loop max 3x: klik X -> tunggu 1.5s (loading) -> verify (elemen berisi kode nggak
    ada + JS_DETAIL_OPEN false) -> kalau masih ada, retry. Return True kalau tab
    beneran gone, False kalau 3x retry masih ada.
  - FIX 3: SETELAH close_detail_tab (step 8), ADD step 8.5: wait input[name=keyword]
    visible (max 10s) = list view ready marker. Ensures next kode's search finds box.
  - FIX 4: main() loop jeda 2s -> 1s (search box wait di 8.5 handles the loading).

PERBAIKAN v8.7 (dari v8.6):
  - TUJUAN: fix 3 bug dari v8.6 run (3 kodes: 19805, 20451, 20447).
  - BUG A (19805 FAIL E_DROPDOWN): step 3.5 dump_dropdown_state dipanggil SETELAH
    click_comment_attachment, SEBELUM step 4. Dump itu switch_top(driver) +
    driver.execute_script(...) — focus shift ini bikin Accurate dropdown AUTO-CLOSE
    utk beberapa kode. Saat step 4 cek baseline (JS_COUNT_DROPLEFT), dropdown udah
    hilang (0 visible) → E_DROPDOWN. v8.6 dump step 3.5 nunjukin dropdown visible,
    tapi step 4 baseline 0 = dropdown ke-close antara dump dan step 4.
    FIX: HAPUS step 3.5 dump call dari process_one_kode. Diagnostic purpose udah
    terlayani (kita tau dropdown structure). Step 4.5 dump (after dropdown <a>
    click) DIPERTAHANKAN — harmless krn jalan SETELAH click.
  - BUG B (20451 wrong rename '_Tanggal_Tanggal.pdf'): extract_cabang_value baca
    field SALAH — JS_READ_CABANG label-sibling pakai 'parent children scan' (greedy,
    ambil sibling pertama non-empty = 'Tanggal') + match startsWith('CABANG') (ke-match
    'Cabang:' / 'Cabang Pengirim'). Padahal dump JS_DUMP_INFO_LAINNYA CORRECTLY nemu
    [15] label='Cabang' value='1287.CBIWAR' class='indent-1 required' via
    lbl.nextElementSibling innerText.
    FIX: rewrite JS_READ_CABANG label-sibling PERSIS kayak dump — querySelectorAll
    'label, .control-label, [class*="label"]', EXACT match (lt.toUpperCase()==='CABANG',
    bukan contains/startsWith — hindari 'Cabang:' / 'Cabang Pengirim'), baca
    nextElementSibling innerText/textContent/value (sama kayak dump). Fallback:
    parentElement.nextElementSibling innerText, lalu parent input value. Jadi PRIMARY
    method (sebelum KO observable + input[name=branch] fallback). extract_cabang_value
    udah log method yg match — kelihatan jalan mana yg kepake.
  - BUG C (20447 FAIL E_SEARCH state pollution): setelah 20451, detail tab mungkin nggak
    ke-close dgn benar → list view nggak accessible → search box input[name=keyword]
    nggak ketemu → E_SEARCH.
    FIX: tambah recover_to_list_view(driver) — tutup attachment overlay + tutup SEMUA
    detail tab (cari i.icon-cancel-2.smaller visible + klik satu2, NGGAK butuh kode)
    + klik button[name='btnToggleList'] (PROVEN trigger search-item-transfer.do =
    list refresh, dari recording). Dipanggil di AWAL process_one_kode (step 0/8) utk
    ensure clean state tiap kode. Cegah state pollution dari kode sebelumnya.
  - Download flow steps 1-7 TIDAK diubah (sudah WORKING). Hanya: hapus 3.5 dump,
    rewrite JS_READ_CABANG label-sibling, + tambah recover_to_list_view.

PERBAIKAN v8.6 (dari v8.5 DIAGNOSTIC):
  - TUJUAN: fix RENAME failure. v8.5 run berakhir DOWNLOAD sukses
    (SJ_DRY_MGM20260924.pdf tersimpan) tapi RENAME gagal 3x karena:
      (a) extract_cabang_value baca field SALAH — bukan 'Cabang' (code+name spt
          '1310.GRTSUM'), tapi field STATUS 'Dicetak email\nBelum cetak email'.
          Hasil: value punya newline (\n) -> filename invalid.
      (b) sanitize_for_filename cuma strip \\ / : * ? \" < > | — NEWLINE \n \r\n
          dan control chars (\t, \x00-\x1f) SURVIVE. Value spt
          'Dicetakemail\nBelum cetakemail' lolot sanitization -> filename invalid
          -> os.rename gagal 3x -> file tetap pakai nama asli.
  - FIX 1: sanitize_for_filename kini juga strip control chars
    ([\x00-\x1f\x7f\\/:*?\"<>|]) + collapse whitespace jadi single space + trim.
    Titik DIPERTAHANKAN (format cabang spt '1310.GRTSUM' butuh titik utuh).
  - FIX 2: extract_cabang_value ADD dump_info_lainnya_fields(driver) di awal —
    dump ALL label+value pairs + element berisi 'Cabang'/'branch' di panel
    Info Lainnya. Dari dump ini kelihatan DIMANA field Cabang beneran + value-nya,
    supaya v8.7 bisa tulis selector persis (bukan tebak label sibling).
  - FIX 2b: extract_cabang_value LOG method yg match (KO observable / input branch /
    label sibling) + value-nya — supaya kelihatan jalan mana yg salah baca.
  - Download flow steps 1-7 (search -> cell -> detail -> btnCommentAttachment ->
    dropdown -> attachment -> download) TIDAK diubah (sudah WORKING di v8.5).
    Hanya sanitize + extract_cabang_value + dump yg di-touched.

PERBAIKAN v8.5 DIAGNOSTIC (dari v8.4):
  - TUJUAN: versi DIAGNOSTIC buat lihat REAL DOM state. v8.4 'graceful skip'
    di step 4 MASKS bug sebenarnya — tool SKIP kode yg PUNYA dokumen karena
    dropdown detection unreliable. v8.5 hapus skip, tambah dump di 2 titik
    kritikal (step 3.5 + 4.5) supaya kelihatan state ul.drop-left + attachment
    panel yg sebenarnya. Dari dump, fix v8.6 ditulis berdasar data nyata.
  - ADD: dump_dropdown_state(driver, label) — dump ALL ul.drop-left + items
    (opacity, display, size, parent) + attachment panel existence.
    Dipanggil di:
      * step 3.5 (after click_comment_attachment OK, before step 4) — nunjukin
        apakah btnCommentAttachment click benar2 buka dropdown.
      * step 4.5 (after click_first_dropdown_item OK, before step 5) — nunjukin
        apakah dropdown <a> click benar2 buka attachment panel.
  - REMOVE: 'graceful skip' di step 4. v8.4 return SKIP_NO_DOCUMENT kalau
    dropdown nggak ketemu — itu MASKS bug. v8.5: return False, "E_DROPDOWN"
    (real error) + dump udah di step 3.5 nunjukin state sebenarnya. Tool STOP
    utk kode ini (recover_to_list), nggak dibilang "no document" (kita nggak
    tahu itu sampe bisa detect dropdown dgn reliable).
  - SUMMARY: cuma [OK] / [FAIL] (nggak ada [SKIP]). Counter: "Berhasil: X/total".
  - Download flow steps 1, 2, 3, 5, 6, 7, 7.5, 7.6, 7.7, 8 TIDAK diubah
    (step 4 hanya logic skip yg diganti jadi error + dump dipanggil di sekitar).

PERBAIKAN v8.4 (dari v8.3):
  - FIX ISSUE 1: STEP 3 (klik i#btnCommentAttachment) kini pakai JS clickSeq (native
    MouseEvent dispatch: pointerdown+mousedown+pointerup+mouseup+click) sebagai PRIMARY,
    ActionChains sebagai fallback. v8.3 pakai ActionChains yg TIDAK reliably trigger
    jQuery dropdown handler Accurate (sama kayak cell click issue v8.1): utk kode
    IT.2026.09.20451 (PUNYA dokumen), dropdown nggak muncul -> "Dropdown item tidak
    ditemukan" -> abort. JS clickSeq (native event) trigger jQuery handler dgn benar.
    Pakai SINGLE click (TANPA dblclick) — dblclick bisa toggle/close dropdown.
    Konstanta baru: JS_CLICK_SEQ_SINGLE.
  - FIX ISSUE 2: kode TANPA dokumen (e.g. IT.2026.09.20447) -> dropdown emang nggak
    muncul. v8.3 abort dgn E_DROPDOWN (treated as FAIL). v8.4: treat as SKIP gracefully
    (log [SKIP], tutup detail tab, return SKIP_NO_DOCUMENT, lanjut kode berikutnya).
    Summary kini tampilkan [SKIP] terpisah dari [FAIL]: Berhasil: X/total, Skip: Y/total.
  - Download flow utama (steps 1, 2, 5, 6, 7, 7.5, 7.6, 7.7, 8) TIDAK diubah.

PERBAIKAN v8.3 (dari v8.2):
  - FEATURE: setelah download selesai, file di-rename jadi
    {kode}_Tanggal_{cabang}.{ext} (contoh: IT.2026.09.09561_Tanggal_1310.GRTSUM.pdf).
  - Cabang diekstrak dari tab 'Info Lainnya' di detail form. Flow:
      (a) tutup attachment overlay dulu (supaya detail form accessible),
      (b) klik tab 'Info Lainnya' (JS_CLICK_INFO_TAB, reuse pattern dari unduh_xls_loop.py),
      (c) baca value Cabang via KO observable formData.branch().name (pattern dari
          accurate_bot.py verify_form_observables) + fallback input.value + label scan,
      (d) rename file (sanitized: hilangkan \\ / : * ? \" < > |, titik dipertahankan),
      (e) tutup detail tab.
  - Fallback 'TanpaCabang' kalau Cabang/tab nggak terbaca (tool tetap jalan + rename).
  - Download flow lama (search -> cell -> detail -> dropdown -> attachment -> download)
    TIDAK diubah; rename + cabang extraction cuma ditambah SETELAH download selesai.

PERBAIKAN v8.2 (dari v8.1):
  - CRITICAL FIX: STEP 2 (click cell) kembali pakai JS clickSeq (native MouseEvent dispatch)
    sebagai PRIMARY method. v8/v8.1 regressed ke ActionChains.click() yg TIDAK trigger
    SlickGrid onClick handler → detail nggak pernah kebuka → "btnCommentAttachment
    tidak ditemukan". JS clickSeq PROVEN buka detail di v6 ("Detail kebuka via DETAIL_INPUT").
    ActionChains hanya dipakai sebagai fallback terakhir.

Flow (berdasarkan RECORDER recording user manual — selector PERSIS):
  1. Search kode di input[name=keyword] + click button.btn-search
  2. SINGLE-click cell di row berisi kode (BUKAN double-click) → detail kebuka (AJAX detail-item-transfer.do)
  3. Click i#btnCommentAttachment (icon Komentar/Dokumen di detail toolbar)
  4. Click <a> pertama di dropdown .drop-left → attachment panel kebuka (AJAX attachment.do)
  5. Click i.icon-download-2 di dalam <a> di attachment panel → DOWNLOAD file
  6. Tutup attachment overlay (button.btn-close)
     → klik tab 'Info Lainnya' di detail form → baca Cabang (KO formData.branch().name,
       e.g. '1310.GRTSUM') + baca Tanggal (input[name='transDate'].value, e.g. '24/09/2026'
       -> '24-09-2026') → rename file jadi {kode}_{tanggal}_{cabang}.{ext}
     → tutup detail tab (i.icon-cancel-2.smaller)
  7. Loop ke kode berikutnya (kalau ada)

Cara pakai:
  1. Buka Chrome: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebugProfile" "https://accurate.id"
  2. Login Accurate, buka modul PEMINDAHAN BARANG (halaman LIST/tabel).
  3. python download_sj_gis.py  (atau double-click JALANKAN_SJ_GIS.bat)
  4. Masukkan kode SJ. Bisa 1 kode, atau multi-kode dipisah koma:
       IT.2026.09.19805
       IT.2026.09.19805, IT.2026.09.20451, IT.2026.09.20447

Output: file PDF/XLS tersimpan di folder Downloads (1 file per kode).
       Nama file: {kode}_{tanggal}_{cabang}.{ext}
         (v8.9: tanggal = date value dari input[name='transDate'], e.g. '24-09-2026';
          cabang diekstrak dari tab 'Info Lainnya' detail form; fallback 'Tanggal' /
          'TanpaCabang' kalau nggak terbaca).
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
# JS CLICK SEQUENCES — native MouseEvent dispatch (PROVEN trigger SlickGrid onClick)
# ============================================================
# CRITICAL FIX v8.2: ActionChains.click() does NOT trigger SlickGrid's onClick handler
# (which opens the item-transfer detail via AJAX detail-item-transfer.do). Only native
# JS MouseEvent dispatch does. This was PROVEN in v6 (output: "Detail kebuka via DETAIL_INPUT").
# v8/v8.1 regressed to ActionChains.click() → detail never opens → "btnCommentAttachment
# tidak ditemukan". v8.2 restores the JS clickSeq approach as PRIMARY click method.
#
# Matches the manual recording: user single-clicked the cell (mousedown + click, no dblclick).

# JS clickSeq — 5 single-click events (pointerdown+mousedown+pointerup+mouseup+click).
# Matches recording exactly (user single-clicked cell, no dblclick). Triggers SlickGrid onClick.
JS_CLICK_SEQ = """
var el = arguments[0];
var init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1};
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
  try { el.dispatchEvent(new MouseEvent(t, init)); } catch(e){}
});
return 'OK';
"""

# v6 full clickSeq + dblclick (proven to work in v6). Backup kalau single-click clickSeq
# alone does not trigger SlickGrid onClick for some reason.
JS_CLICK_SEQ_DBL = """
var el = arguments[0];
var init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1};
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
  try { el.dispatchEvent(new MouseEvent(t, init)); } catch(e){}
});
try { el.dispatchEvent(new MouseEvent('dblclick', init)); } catch(e){}
return 'OK';
"""

# v8.4 — JS clickSeq SINGLE-click only (NO dblclick). Dipakai buat i#btnCommentAttachment:
# single click trigger Accurate's jQuery dropdown.open(). dblclick bisa toggle/close dropdown
# jadi nggak muncul. (Sama kayak JS_CLICK_SEQ buat cell, tapi tanpa dblclick backup.)
JS_CLICK_SEQ_SINGLE = """
var el = arguments[0];
var init = {bubbles:true, cancelable:true, view:window, button:0, buttons:1};
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
  try { el.dispatchEvent(new MouseEvent(t, init)); } catch(e){}
});
return 'OK';
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
# CRITICAL FIX v8.2: gunakan JS clickSeq (native MouseEvent dispatch) sebagai PRIMARY method.
# ActionChains.click() does NOT trigger SlickGrid's onClick handler — only native JS
# MouseEvent dispatch does (proven in v6: "Detail kebuka via DETAIL_INPUT"). v8/v8.1
# regressed to ActionChains.click() → detail never opens → "btnCommentAttachment tidak
# ditemukan". v8.2 restores JS clickSeq as PRIMARY, ActionChains only as last-resort fallback.
def click_cell_open_detail(driver, fr, kode):
    """Single-click cell di row berisi kode → detail kebuka (AJAX detail-item-transfer.do).

    Strategi (urutan, tiap strategi dicek pakai JS_DETAIL_OPEN max 4s):
      1. JS clickSeq (pointerdown+mousedown+pointerup+mouseup+click) — PRIMARY, matches recording
      2. JS clickSeq + dblclick (v6 approach, proven)
      3. simple element.click() via JS
      4. ActionChains double-click (fallback)
      5. ActionChains single-click (fallback terakhir — least reliable for SlickGrid)
    Return label strategi yg sukses, atau "JS_CLICK_SEQ_DISPATCHED" kalau semua gagal
    (click tetap di-dispatch — detail-check mungkin flaky; caller ada wait_detail_open 15s).
    """
    def find_cell():
        """Re-mark + cari cell (data-fl-target=2). Fallback ke row (data-fl-target=1)."""
        reframe(driver, fr)
        driver.execute_script(JS_FIND_ROW_WITH_KODE, kode)
        c = find_marked_attr(driver, "2", timeout=2)
        if not c:
            c = find_marked_attr(driver, "1", timeout=2)
        return c

    cell = find_cell()
    if not cell:
        say("    [WARNING] Cell/row tidak ditemukan setelah search.")
        return None

    def try_strategy(label, click_fn):
        """Coba 1 strategi click, cek detail kebuka dalam 4s. Return label kalau sukses, None kalau gagal."""
        c = find_cell()  # re-find (mungkin stale setelah strategi sebelumnya)
        if not c:
            say(f"    [{label}] cell hilang/stale")
            return None
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", c)
        except: pass
        try:
            click_fn(c)
        except Exception as e:
            say(f"    [{label}] exception: {e}")
            return None
        # Tunggu AJAX detail-item-transfer.do (max 4s per strategi)
        end = time.time() + 4
        while time.time() < end:
            try:
                switch_top(driver)
                if driver.execute_script(JS_DETAIL_OPEN, kode):
                    return label
            except: pass
            time.sleep(0.3)
        return None

    # 1. PRIMARY: JS clickSeq (native MouseEvent — pointerdown+mousedown+pointerup+mouseup+click)
    #    Matches recording (user single-clicked cell). PROVEN trigger SlickGrid onClick.
    say("    [1] JS clickSeq (native MouseEvent dispatch)...")
    r = try_strategy("JS_CLICK_SEQ", lambda t: driver.execute_script(JS_CLICK_SEQ, t))
    if r:
        say(f"    [OK] Detail kebuka via {r}")
        return r

    # 2. FALLBACK: v6 full clickSeq + dblclick (proven to work in v6)
    say("    [2] JS clickSeq + dblclick (v6 approach)...")
    r = try_strategy("JS_CLICK_SEQ_DBL", lambda t: driver.execute_script(JS_CLICK_SEQ_DBL, t))
    if r:
        say(f"    [OK] Detail kebuka via {r}")
        return r

    # 3. FALLBACK: simple element.click() via JS
    say("    [3] element.click() via JS...")
    r = try_strategy("JS_CLICK", lambda t: driver.execute_script("arguments[0].click();", t))
    if r:
        say(f"    [OK] Detail kebuka via {r}")
        return r

    # 4. FALLBACK: ActionChains double-click
    say("    [4] ActionChains double-click...")
    r = try_strategy("AC_DBLCLICK", lambda t: ActionChains(driver).move_to_element(t).double_click().perform())
    if r:
        say(f"    [OK] Detail kebuka via {r}")
        return r

    # 5. FALLBACK (terakhir): ActionChains single-click — least reliable for SlickGrid
    say("    [5] ActionChains single-click...")
    r = try_strategy("AC_CLICK", lambda t: ActionChains(driver).move_to_element(t).click().perform())
    if r:
        say(f"    [OK] Detail kebuka via {r}")
        return r

    say("    [WARNING] Semua strategi click gagal buka detail (per JS_DETAIL_OPEN).")
    say("    [INFO] Click dispatched via JS clickSeq. Lanjut — wait_detail_open(15s) di caller.")
    # Kembalikan label primary — process_one_kode akan panggil wait_detail_open(15s) buat
    # pastika detail benar-benar kebuka (mungkin JS_DETAIL_OPEN marker belum sempat render).
    return "JS_CLICK_SEQ_DISPATCHED"

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
    """Klik i#btnCommentAttachment via JS clickSeq (native MouseEvent) — ActionChains nggak reliable
    buat trigger jQuery dropdown handler Accurate (sama kayak cell click issue v8.1).
    v8.4: PRIMARY = JS clickSeq SINGLE (no dblclick — dblclick bisa toggle/close dropdown)."""
    switch_top(driver)
    # Priority 1: by id, click via JS clickSeq (native events) — paling reliable buat jQuery handler
    try:
        btn = driver.find_element(By.ID, "btnCommentAttachment")
        if btn:
            # scroll into view dulu biar event dispatch kena target
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            # dispatch native single-click sequence (pointerdown+mousedown+pointerup+mouseup+click)
            driver.execute_script(JS_CLICK_SEQ_SINGLE, btn)
            return "JS_CLICKSEQ"
    except Exception as e:
        say(f"  [WARNING] JS clickSeq on btnCommentAttachment failed: {e}")
    # Fallback 1: ActionChains (lama) — kalau JS clickSeq somehow gagal
    try:
        btn = driver.find_element(By.ID, "btnCommentAttachment")
        if btn:
            return smart_click(driver, btn)
    except: pass
    # Fallback 2: by class i.icn-navigation-attachment, click via JS clickSeq
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "i.icn-navigation-attachment")
        for btn in btns:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    driver.execute_script(JS_CLICK_SEQ_SINGLE, btn)
                    return "JS_CLICKSEQ_CLASS"
            except: continue
    except: pass
    return None

# ============================================================
# STEP 4: CLICK FIRST <a> IN DROPDOWN (.drop-left)
# ============================================================
# FIX v8.1: HANYA cari ul.drop-left (BUKAN ul generik) + track dropdown BARU
# (yg muncul setelah klik btnCommentAttachment). Ini cegah klik Dashboard link.
JS_COUNT_DROPLEFT = JS_VIS + """
return (function(){
  var uls = document.querySelectorAll('ul.drop-left');
  var visible = 0;
  for (var i=0;i<uls.length;i++){
    if (vis(uls[i])) visible++;
  }
  return {total: uls.length, visible: visible};
})();
"""

JS_FIND_NEW_DROPDOWN_A = JS_VIS + """
return (function(beforeVisible){
  var ATTR='data-fl-target';
  var uls = document.querySelectorAll('ul.drop-left');  // HANYA drop-left, bukan ul generik
  var found = null;
  for (var i=0;i<uls.length;i++){
    var ul = uls[i];
    if (!vis(ul)) continue;
    var r = ul.getBoundingClientRect();
    if (r.width<=0 || r.height<=0) continue;
    // Cari <a> pertama yg visible di dropdown ini
    var links = ul.querySelectorAll('a, li > a');
    for (var j=0;j<links.length;j++){
      var a = links[j];
      if (!vis(a)) continue;
      var t = (a.innerText||'').trim();
      if (!t || t.length > 40) continue;
      // EXCLUDE link Dashboard/main-menu (href #module-accurate__dashboard)
      var href = (a.getAttribute('href')||'');
      if (href.indexOf('dashboard') !== -1) continue;
      a.setAttribute(ATTR,'1');
      return {text:t, href:href.slice(0,80), idx:i};
    }
  }
  return null;
})(arguments[0]);
"""

def click_first_dropdown_item(driver, timeout=8):
    """Setelah btnCommentAttachment, tunggu ul.drop-left BARU muncul, klik <a> pertama.
    FIX v8.1: cuma cari ul.drop-left (bukan ul generik) + exclude Dashboard link.
    FIX v8.9: PRIMARY = JS_CLICK_SEQ_SINGLE (native MouseEvent dispatch). ActionChains
    (smart_click) NGGAK reliably trigger Accurate jQuery dropdown <a> handler — 19805
    failed (attachment panel nggak kebuka -> E_DOWNLOAD_ICON), 20451 lucky (kebuka).
    Same bug class kayak cell click (v8.1 -> v8.2) + btnCommentAttachment (v8.3 -> v8.4),
    both fixed dgn JS clickSeq. ActionChains dipertahankan sebagai FALLBACK."""
    switch_top(driver)
    # Catat jumlah dropdown visible sebelum (baseline)
    try:
        before = driver.execute_script(JS_COUNT_DROPLEFT) or {"visible":0}
    except:
        before = {"visible":0}
    say(f"      [baseline] ul.drop-left visible: {before.get('visible',0)}")
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            ux = driver.execute_script(JS_FIND_NEW_DROPDOWN_A, before.get("visible",0))
            if ux:
                say(f"      [found] dropdown <a>: text='{ux.get('text','')}' href='{ux.get('href','')[:40]}'")
                el = find_marked(driver, [], timeout=2)
                if el:
                    # v8.9: PRIMARY = JS clickSeq (native MouseEvent) — ActionChains intermittent
                    # (19805 failed, 20451 worked). Same bug class as cell click (v8.1->v8.2)
                    # + btnCommentAttachment (v8.3->v8.4), both fixed with JS clickSeq.
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    try:
                        driver.execute_script(JS_CLICK_SEQ_SINGLE, el)
                        clear_mark(driver, [])
                        return "JS_CLICKSEQ"
                    except Exception as e:
                        say(f"      [WARNING] JS clickSeq gagal: {e}, fallback ActionChains")
                        clear_mark(driver, [])
                        how = smart_click(driver, el)
                        clear_mark(driver, [])
                        return how
        except: pass
        time.sleep(0.4)
    return None

# ============================================================
# DIAGNOSTIC DUMP (v8.5) — dump ALL ul.drop-left + items + attachment panels
# ============================================================
# Purpose: lihat REAL DOM state di 2 titik kritikal:
#   - step 3.5 (after click_comment_attachment) — apakah btnCommentAttachment
#     click benar2 buka dropdown? Berapa ul.drop-left visible? Itemnya apa?
#   - step 4.5 (after click_first_dropdown_item) — apakah dropdown <a> click
#     benar2 buka attachment panel? Panel ada + visible?
# Dari dump ini, fix selector v8.6 ditulis berdasar data nyata (bukan tebakan).
JS_DUMP_DROPDOWN_STATE = JS_VIS + """
return (function(){
  var out = {label: arguments[0] || '', url: location.href.slice(0,100), dropLefts: []};
  var uls = document.querySelectorAll('ul.drop-left, ul[class*="drop-left"]');
  for (var i=0;i<uls.length && out.dropLefts.length<10;i++){
    var ul = uls[i];
    var st = window.getComputedStyle(ul);
    var vis = !(st.display==='none'||st.visibility==='hidden'||parseFloat(st.opacity)===0);
    var r = ul.getBoundingClientRect();
    var sizeOk = r.width>0 && r.height>0;
    var parent = ul.parentElement;
    var items = [];
    var links = ul.querySelectorAll('a, li > a, li');
    for (var j=0;j<links.length && items.length<8;j++){
      var a = links[j];
      var ast = window.getComputedStyle(a);
      var avis = !(ast.display==='none'||ast.visibility==='hidden'||parseFloat(ast.opacity)===0);
      var ar = a.getBoundingClientRect();
      var asizeOk = ar.width>0 && ar.height>0;
      items.push({
        tag: a.tagName,
        text: (a.innerText||a.textContent||'').trim().slice(0,40),
        href: (a.getAttribute&&a.getAttribute('href')||'').slice(0,60),
        onclick: (a.getAttribute&&a.getAttribute('onclick')||'').slice(0,60),
        visible: avis && asizeOk,
        opacity: parseFloat(ast.opacity)
      });
    }
    out.dropLefts.push({
      idx: i,
      visible: vis && sizeOk,
      opacity: parseFloat(st.opacity),
      display: st.display,
      parentTag: parent?parent.tagName:'',
      parentClass: parent?(parent.className||'').toString().slice(0,60):'',
      parentId: parent?(parent.id||''):'',
      itemCount: items.length,
      items: items
    });
  }
  // also check attachment panel existence
  out.attachmentPanels = [];
  var aps = document.querySelectorAll("div[id^='accurate__company__attachment']");
  for (var k=0;k<aps.length && out.attachmentPanels.length<5;k++){
    var p = aps[k];
    var pst = window.getComputedStyle(p);
    out.attachmentPanels.push({
      id: p.id,
      visible: !(pst.display==='none'||pst.visibility==='hidden'||parseFloat(pst.opacity)===0),
      hasDownloadIcon: !!p.querySelector('i.icon-download-2, i[class*="icon-download"]')
    });
  }
  return out;
})(arguments[0]);
"""

def dump_dropdown_state(driver, label):
    """Diagnostic dump: ALL ul.drop-left + items + attachment panels. For v8.5 diagnosis."""
    switch_top(driver)
    try:
        st = driver.execute_script(JS_DUMP_DROPDOWN_STATE, label)
    except Exception as e:
        say(f"  [DUMP ERR] {e}"); return
    say(f"\n  ===== DUMP: {label} =====")
    say(f"  URL: {st.get('url','?')[:80]}")
    dls = st.get('dropLefts', [])
    say(f"  ul.drop-left total: {len(dls)}")
    for dl in dls:
        say(f"    [{dl['idx']}] visible={dl['visible']} opacity={dl.get('opacity','?')} display={dl.get('display','?')[:15]}")
        say(f"        parent: <{dl['parentTag']}> id='{dl['parentId']}' class='{dl['parentClass']}'")
        say(f"        items ({dl['itemCount']}):")
        for it in dl.get('items', []):
            say(f"          [{it['tag']}] text='{it['text']}' href='{it['href'][:30]}' visible={it['visible']} opacity={it.get('opacity','?')}")
    aps = st.get('attachmentPanels', [])
    if aps:
        say(f"  Attachment panels: {len(aps)}")
        for ap in aps:
            say(f"    id='{ap['id']}' visible={ap['visible']} hasDownloadIcon={ap['hasDownloadIcon']}")
    else:
        say(f"  Attachment panels: 0 (none)")
    say(f"  ===== END DUMP =====\n")

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

# FIX v8.1: cari i.icon-download-2 HANYA di dalam attachment panel (div[id^='accurate__company__attachment'])
# (sebelumnya cari di seluruh dokumen -> bisa ketemu icon-download-2 di tempat lain)
JS_FIND_DOWNLOAD_ICON = JS_VIS + """
return (function(){
  var ATTR='data-fl-target';
  var panels = document.querySelectorAll("div[id^='accurate__company__attachment']");
  for (var p=0;p<panels.length;p++){
    var panel = panels[p];
    if (!vis(panel)) continue;
    var icons = panel.querySelectorAll('i.icon-download-2, i[class*="icon-download"]');
    for (var i=0;i<icons.length;i++){
      var ic = icons[i];
      if (!vis(ic)) continue;
      var a = ic.closest('a');
      if (a && vis(a)){
        a.setAttribute(ATTR,'1');
        return {text:(a.innerText||'').trim().slice(0,40), href:(a.getAttribute('href')||'').slice(0,100), panel:panel.id};
      }
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
    """Tutup overlay attachment. FIX v8.1: priority div.window-overlay button.btn-close
    (bukan btn-close generik yg bisa kena tombol lain)."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            # Priority 1: btn-close di dalam window-overlay (attachment dialog)
            btns = driver.find_elements(By.CSS_SELECTOR, "div.window-overlay button.btn-close, .window button.btn-close, .metro-window button.btn-close")
            for btn in btns:
                try:
                    if btn.is_displayed():
                        smart_click(driver, btn)
                        return True
                except: continue
            # Priority 2: caption bar btn-close
            btns = driver.find_elements(By.CSS_SELECTOR, "div.caption button.btn-close")
            for btn in btns:
                try:
                    if btn.is_displayed():
                        smart_click(driver, btn)
                        return True
                except: continue
        except: pass
        time.sleep(0.4)
    return False

def verify_still_on_detail(driver, kode):
    """Safety check: pastikan nggak ke-navigation ke Dashboard/halaman lain setelah klik dropdown.
    Return True kalau masih di halaman detail item-transfer."""
    try:
        switch_top(driver)
        url = (driver.current_url or "").lower()
        # Kalau URL jadi dashboard & bukan item-transfer → navigated away
        if "dashboard" in url and "item-transfer" not in url:
            say(f"      [SAFETY] Navigasi ke Dashboard terdeteksi! Abort.")
            return False
        # Cek btnCommentAttachment masih ada (marker detail form)
        btns = driver.find_elements(By.ID, "btnCommentAttachment")
        if btns:
            return True
        # Cek tab detail masih ada (berisi kode)
        tabs = driver.find_elements(By.CSS_SELECTOR, "div.module-tab, div.form-tab-title")
        for t in tabs:
            try:
                if kode in (t.text or ""):
                    return True
            except: continue
        return False
    except:
        return False

def close_detail_tab(driver, kode, timeout=10):
    """Tutup tab detail (klik X i.icon-cancel-2.smaller di tab berisi kode).
    v8.8: VERIFY tab beneran hilang. Retry klik X max 3x. User confirm: ada loading
    setelah close, jadi perlu cek tab beneran gone sebelum return."""
    for attempt in range(3):
        switch_top(driver)
        try:
            cl = driver.execute_script(JS_MARK_CLOSE, kode)
            if not cl:
                # tab udah nggak ada (berisi kode) -> sudah close
                return True
            el = find_marked(driver, cl["path"], timeout=3)
            if el:
                smart_click(driver, el)
                clear_mark(driver, cl["path"])
                say(f"  [close_detail_tab] attempt {attempt+1}: klik X, tunggu loading...")
                time.sleep(1.5)  # user confirm: ada loading setelah close
            else:
                clear_mark(driver, cl["path"])
                # cek lagi apakah tab masih ada
                cl2 = driver.execute_script(JS_MARK_CLOSE, kode)
                if not cl2:
                    return True
        except Exception as e:
            say(f"  [close_detail_tab] attempt {attempt+1} error: {e}")
        # verify: cek tab (elemen berisi kode) masih ada?
        switch_top(driver)
        still_open = driver.execute_script(JS_DETAIL_OPEN, kode)  # JS_DETAIL_OPEN cek input value=kode / #btnCommentAttachment
        # also check: is the kode still in a tab element?
        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, "div.module-tab, div.form-tab-title")
            kode_in_tab = any(kode in (t.text or "") for t in tabs if t.is_displayed())
        except:
            kode_in_tab = False
        if not kode_in_tab and not still_open:
            return True  # tab beneran gone
    return False  # 3x retry masih ada

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
# INFO LAINNYA TAB + CABANG EXTRACTION + RENAME FILE (v8.3)
# ============================================================
# Reuse pattern dari unduh_xls_loop.py (JS_CLICK_INFO_TAB — proven trigger Info lainnya tab).
# Cabang value dibaca via KO observable (vm.formData.branch().name) — pattern dari
# accurate_bot.py verify_form_observables(). Fallback: input.value + label 'Cabang' scan.
# Rename file ke {kode}_Tanggal_{cabang}.{ext} (sanitized: hilangkan \\ / : * ? " < > |,
# titik dipertahankan utk format cabang spt '1310.GRTSUM').

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

JS_DUMP_INFO_LAINNYA = JS_VIS + """
return (function(){
  var out = {fields: []};
  // Cari semua elemen label/value di Info Lainnya panel.
  // Accurate forms: label di <label>/<div>/<span>, value di sibling <span>/<div>/<input>
  // Pattern 1: <div class="input-control..."><label>Cabang</label><input ...> or <div>value</div>
  // Pattern 2: <div><span>Cabang:</span><span>value</span></div>
  // Pattern 3: <label>Cabang</label> diikuti text/value

  // Cari semua <label> dan text-nya, plus sibling value
  var labels = document.querySelectorAll('label, .control-label, [class*="label"]');
  for (var i=0;i<labels.length && out.fields.length<40;i++){
    var lbl = labels[i];
    if (!vis(lbl)) continue;
    var lt = (lbl.innerText||lbl.textContent||'').trim();
    if (!lt || lt.length>40) continue;
    // Cari sibling value: next sibling, atau parent's next child
    var val = '';
    var sib = lbl.nextElementSibling;
    if (sib){
      val = (sib.innerText||sib.textContent||sib.value||'').trim();
    }
    if (!val){
      // cek parent's next sibling
      var psib = lbl.parentElement ? lbl.parentElement.nextElementSibling : null;
      if (psib) val = (psib.innerText||psib.textContent||'').trim();
    }
    if (!val){
      // cek kalau label parent punya input
      var par = lbl.parentElement;
      if (par){
        var inp = par.querySelector('input, select, textarea');
        if (inp) val = (inp.value||inp.innerText||'').trim();
      }
    }
    out.fields.push({label: lt.slice(0,30), value: val.slice(0,60), labelClass:(lbl.className||'').toString().slice(0,40)});
  }
  // Juga cari semua <input> dgn value (field values)
  var inps = document.querySelectorAll('input[type="text"], input:not([type]), input[readonly], select');
  for (var j=0;j<inps.length && out.fields.length<60;j++){
    var inp = inps[j];
    if (!vis(inp)) continue;
    var nm = inp.name||'';
    var val = (inp.value||'').trim();
    if (val && val.length<60){
      out.fields.push({label: 'INPUT:'+nm, value: val.slice(0,60), labelClass: (inp.className||'').toString().slice(0,40)});
    }
  }
  // Cari semua div/span berisi "Cabang" (case insensitive)
  var all = document.querySelectorAll('div, span, li, td');
  for (var k=0;k<all.length && out.fields.length<80;k++){
    var el = all[k];
    if (!vis(el)) continue;
    var t = (el.innerText||'').trim();
    if (!t || t.length>80) continue;
    var low = t.toLowerCase();
    if (low.indexOf('cabang') !== -1 || low.indexOf('branch') !== -1){
      out.fields.push({label: 'CONTAINS_CABANG:', value: t.slice(0,70), labelClass:(el.className||'').toString().slice(0,40)});
    }
  }
  return out;
})();
"""


JS_READ_CABANG = JS_VIS + """
return (function(){
  // v8.7: label-sibling (EXACT "Cabang" + nextElementSibling) jadi PRIMARY method.
  //       PROVEN dari dump JS_DUMP_INFO_LAINNYA yg nemu [15] label='Cabang' value='1287.CBIWAR'.
  //       v8.6 salah baca 'Tanggal' karena label-sibling pakai 'parent children scan' (greedy)
  //       + match pakai startsWith('CABANG') (ke-match 'Cabang:' dll). v8.7: EXACT match +
  //       nextElementSibling (sama persis kayak dump). KO observable + input[name=branch] jadi
  //       fallback. return {value, method} supaya extract_cabang_value bisa log method yg match.
  function getVM(el){
    try { if (window.ko && ko.contextFor) return ko.contextFor(el).$data; } catch(e) {}
    try { if (window.ko && ko.dataFor) return ko.dataFor(el); } catch(e) {}
    return null;
  }
  function read(doc){
    // 1. PRIMARY (v8.7): label-sibling — EXACT "Cabang" label + nextElementSibling value.
    //    PROVEN dari JS_DUMP_INFO_LAINNYA: dump nemu [15] label='Cabang' value='1287.CBIWAR'
    //    class='indent-1 required' via lbl.nextElementSibling innerText. v8.6 salah karena
    //    pakai 'parent children scan' (greedy, ambil sibling pertama yg non-empty = 'Tanggal').
    //    v8.7: EXACT match (case-insensitive, bukan contains/startsWith — hindari 'Cabang:' /
    //    'Cabang Pengirim') + baca nextElementSibling innerText/textContent/value persis kayak
    //    dump. Fallback: parentElement.nextElementSibling innerText, lalu parent input value.
    try {
      let labels = Array.from(doc.querySelectorAll('label, .control-label, [class*="label"]'));
      for (let lbl of labels) {
        if (!vis(lbl)) continue;
        let lt = (lbl.innerText || lbl.textContent || '').trim();
        if (!lt) continue;
        if (lt.toUpperCase() !== 'CABANG') continue;  // EXACT match only (hindari 'Cabang:' / 'Cabang Pengirim')
        let val = '';
        // a. nextElementSibling innerText/textContent/value (SAME as dump)
        let sib = lbl.nextElementSibling;
        if (sib) {
          val = ((sib.innerText || sib.textContent || sib.value || '') + '').trim();
        }
        // b. parentElement.nextElementSibling innerText/textContent (SAME as dump fallback)
        if (!val) {
          let psib = lbl.parentElement ? lbl.parentElement.nextElementSibling : null;
          if (psib) val = ((psib.innerText || psib.textContent || '') + '').trim();
        }
        // c. parent input/select/textarea value (SAME as dump fallback)
        if (!val) {
          let par = lbl.parentElement;
          if (par) {
            let inp = par.querySelector('input, select, textarea');
            if (inp) val = ((inp.value || inp.innerText || '') + '').trim();
          }
        }
        if (val && val.length < 60) return {value: val, method: 'label sibling (exact "Cabang" + nextElementSibling)'};
      }
    } catch(e) {}

    // 2. FALLBACK: KO observable vm.formData.branch().name  (pattern dari accurate_bot.py)
    try {
      let inp = doc.querySelector('input[name="branch"]');
      if (inp && inp.isConnected && vis(inp)) {
        let vm = getVM(inp);
        if (vm && vm.formData) {
          if (typeof vm.formData.branch === 'function') {
            let b = vm.formData.branch();
            if (b && typeof b === 'object') {
              if (b.name) return {value: String(b.name).trim(), method: 'KO observable (formData.branch().name)'};
              if (b.no)  return {value: String(b.no).trim(),  method: 'KO observable (formData.branch().no)'};
            }
            if (typeof b === 'string' && b) return {value: b.trim(), method: 'KO observable (formData.branch() string)'};
          }
          if (typeof vm.formData.branchId === 'function') {
            let bid = vm.formData.branchId();
            if (bid) {
              try {
                if (window.acc && acc.staticData && typeof acc.staticData.branchListOption === 'function') {
                  let opts = acc.staticData.branchListOption() || [];
                  for (let i=0;i<opts.length;i++){
                    let o = opts[i] || {};
                    if (o && (o.id === bid || String(o.id) === String(bid))) {
                      if (o.name) return {value: String(o.name).trim(), method: 'KO observable (branchId+branchListOption.name)'};
                    }
                  }
                }
              } catch(e) {}
              return {value: String(bid).trim(), method: 'KO observable (branchId fallback)'};
            }
          }
        }
        // 2c. plain input.value (Accurate build sometimes set value langsung)
        if (inp.value && inp.value.trim()) return {value: inp.value.trim(), method: 'input branch (input[name=branch].value)'};
      }
    } catch(e) {}

    // 3. recursive iframe scan (detail form bisa ada di iframe)
    const fr = doc.querySelectorAll('iframe, frame');
    for (let i=0;i<fr.length;i++){
      try{ const d=fr[i].contentDocument; if(d){ const r=read(d); if(r && r.value) return r; } }catch(e){}
    }
    return null;
  }
  return read(document);
})()
"""


def click_info_lainnya_tab(driver, timeout=8):
    """Klik tab 'Info lainnya' di detail form.
    Return True kalau ketemu & di-klik (atau sudah aktif), False kalau nggak ketemu.
    Reuse JS_CLICK_INFO_TAB (proven pattern dari unduh_xls_loop.py JS_CLICK_INFO_TAB):
      - a[title="Info lainnya"], a.left-tab[title="Info lainnya"], .icn-transaction-header
      - fallback: elements dengan text persis 'Info lainnya'
      - recursive iframe scan (detail form bisa ada di iframe).
    """
    end = time.time() + timeout
    switch_top(driver)
    while time.time() < end:
        try:
            switch_top(driver)
            res = driver.execute_script(JS_CLICK_INFO_TAB)
            if res:  # 'TITLE' or 'TEXT'
                time.sleep(0.4)  # kasih waktu panel Info Lainnya render field Cabang
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def dump_info_lainnya_fields(driver):
    """Diagnostic: dump ALL label+value pairs + Cabang-containing elements in Info Lainnya panel.
    v8.6: kelihatan DIMANA field Cabang beneran + value-nya supaya v8.7 bisa tulis selector persis
    (bukan tebak label sibling). Dipanggil sekali di awal extract_cabang_value sebelum extraction.
    """
    switch_top(driver)
    try:
        st = driver.execute_script(JS_DUMP_INFO_LAINNYA)
    except Exception as e:
        say(f"    [DUMP ERR] {e}")
        return
    if not st or not isinstance(st, dict):
        tn = type(st).__name__ if st is not None else 'None'
        say(f"    [DUMP] no output (script returned {tn})")
        return
    fields = st.get('fields', []) or []
    say(f"\n    ===== DUMP: Info Lainnya fields ({len(fields)}) =====")
    for i, f in enumerate(fields):
        say(f"      [{i}] label='{f.get('label','')}' value='{f.get('value','')}' class='{f.get('labelClass','')}'")
    # Highlight any field whose label or value contains 'cabang' or 'branch' (case insensitive)
    cabang_candidates = [f for f in fields
                        if 'cabang' in (f.get('label','')+f.get('value','')).lower()
                        or 'branch' in (f.get('label','')+f.get('value','')).lower()]
    if cabang_candidates:
        say(f"      --- CABANG CANDIDATES ({len(cabang_candidates)}) ---")
        for c in cabang_candidates:
            say(f"        label='{c.get('label','')}' value='{c.get('value','')}'")
    else:
        say(f"      (no field with 'cabang'/'branch' in label or value)")
    say(f"    ===== END DUMP =====\n")


def extract_cabang_value(driver, timeout=10):
    """Baca value Cabang dari panel 'Info Lainnya'. v8.6: dump fields first + log method matched.
    Return string cabang (e.g. '1310.GRTSUM') atau None.
    Strategy (urut paling reliable -> fallback, dibungkus JS_READ_CABANG yg return {value, method}):
      1. KO observable vm.formData.branch().name  (pattern accurate_bot.py verify_form_observables)
      2. KO vm.formData.branchId() + lookup acc.staticData.branchListOption() -> .name
      3. input[name='branch'].value (build ada yg set value langsung)
      4. label 'Cabang' + sibling value scan (akomodasi layout non-KO)
      5. recursive iframe scan (detail form bisa ada di iframe)
    v8.6 DIAGNOSTIC: panggil dump_info_lainnya_fields(driver) di awal supaya kelihatan SEMUA field
    di panel Info Lainnya — termasuk field STATUS (bukan Cabang) yg sebelumnya kebaca salah
    akibat label sibling scan greedy. Plus log method yg match + value-nya supaya kelihatan
    jalan mana yg salah baca.
    """
    # DIAGNOSTIC: dump all fields first (one-shot snapshot, no retry biar nggak spam output)
    dump_info_lainnya_fields(driver)

    # Extraction attempt loop (kasih waktu panel render kalau field belum available)
    end = time.time() + timeout
    switch_top(driver)
    while time.time() < end:
        try:
            switch_top(driver)
            res = driver.execute_script(JS_READ_CABANG)
            # v8.6: JS_READ_CABANG return {value, method} (atau null)
            if res and isinstance(res, dict):
                val = (res.get('value') or '').strip()
                if val:
                    say(f"    [method={res.get('method','?')}] cabang='{val}'")
                    return val
            elif res and isinstance(res, str):
                # legacy fallback (kalau JS lama belum di-update, return string) — strip + return
                val = res.strip()
                if val:
                    say(f"    [method=legacy string] cabang='{val}'")
                    return val
        except Exception:
            pass
        time.sleep(0.3)
    say(f"    [method=none] cabang tidak terbaca setelah {timeout}s -> fallback TanpaCabang")
    return None


def extract_tanggal_value(driver, timeout=5):
    """v8.9: baca value input[name='transDate'] dari detail form = tanggal transaksi.
    Dari v8.8 dump utk 20451: [14] INPUT:transDate value='24/09/2026'. Ini DATE VALUE
    sebenarnya (BUKAN literal 'Tanggal' yg dipake v8.3-v8.8 di filename).
    Return string tanggal (e.g. '24/09/2026') atau None kalau nggak ketemu.
    Caller (process_one_kode 7.6) replace '/' -> '-' jadi '24-09-2026' utk readability,
    lalu sanitize_for_filename strip sisa forbidden chars. Fallback literal 'Tanggal'
    kalau None (supaya filename tetap jalan)."""
    end = time.time() + timeout
    while time.time() < end:
        switch_top(driver)
        try:
            val = driver.execute_script("""
                var inp = document.querySelector("input[name='transDate']");
                if (inp && inp.value) return inp.value;
                return null;
            """)
            if val:
                return val
        except: pass
        time.sleep(0.5)
    return None


def sanitize_for_filename(value):
    """Buang karakter Windows-forbidden + control chars (newline, tab, dll) utk filename.
    Titik DIPERTAHANKAN (format cabang spt '1310.GRTSUM' butuh titik utuh).
    v8.6: sebelumnya cuma strip \\ / : * ? " < > | — NEWLINE \\n \\r dan control chars
    (\\t, \\x00-\\x1f) SURVIVE, jadi value spt 'Dicetakemail\\nBelum cetakemail' lolot
    sanitization -> filename invalid -> rename gagal 3x. Sekarang strip control chars
    juga + collapse whitespace jadi single space + trim."""
    if not value:
        return ""
    # Strip control chars (\\x00-\\x1f includes \\n \\r \\t; \\x7f = DEL) + Windows-forbidden chars.
    # KEEP dots, letters, digits, spaces, dashes, parens, dll.
    value = re.sub(r'[\x00-\x1f\x7f\\/:*?"<>|]', '', str(value))
    # Collapse remaining whitespace (multiple spaces) jadi single space, lalu trim.
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def rename_download_file(original_path, kode, tanggal, cabang):
    """Rename file ke {kode}_{tanggal}_{cabang}.{ext}. v8.9: tanggal = date value from form.
    v8.9 (dari v8.8): sebelumnya filename pakai literal 'Tanggal' (BUKAN date value).
    User clarify 'Tanggal' should be ACTUAL DATE dari input[name='transDate'] (e.g.
    '24/09/2026' -> diformat '24-09-2026'). Fallback literal 'Tanggal' kalau None.
    - ext = os.path.splitext(original_path)[1]  (pertahankan .pdf / .xls / .xlsx asli)
    - cabang None/empty/unsanitizable -> fallback 'TanpaCabang'
    - tanggal None/empty/unsanitizable -> fallback 'Tanggal' (v8.3-v8.8 literal behavior)
    - Retry rename 3x (0.5s) utk antisipasi file masih locked Chrome sesaat setelah download
    - Kalau target sudah ada, tambahkan suffix _1, _2, dst biar nggak overwrite
    - Return path baru, atau path asli kalau rename gagal (file tetap ada, cuma nggak ke-rename)
    """
    if not original_path or not os.path.exists(original_path):
        return original_path
    ext = os.path.splitext(original_path)[1]
    safe_cabang = sanitize_for_filename(cabang) if cabang else ""
    if not safe_cabang:
        safe_cabang = "TanpaCabang"
    safe_tanggal = sanitize_for_filename(tanggal) if tanggal else ""
    if not safe_tanggal:
        safe_tanggal = "Tanggal"  # fallback literal (v8.3-v8.8 behavior)
    new_name = f"{kode}_{safe_tanggal}_{safe_cabang}{ext}"
    folder = os.path.dirname(original_path)
    new_path = os.path.join(folder, new_name)
    # Kalau target sudah ada, tambah suffix _1, _2, dst biar nggak overwrite
    if os.path.exists(new_path):
        i = 1
        while os.path.exists(new_path):
            new_path = os.path.join(folder, f"{kode}_{safe_tanggal}_{safe_cabang}_{i}{ext}")
            i += 1
    # Retry rename 3x (file mungkin masih locked oleh Chrome sesaat setelah download selesai)
    for attempt in range(3):
        try:
            os.rename(original_path, new_path)
            return new_path
        except OSError:
            time.sleep(0.5)
    # Kalau rename gagal 3x, kembalikan path asli (file tetap ada, cuma nggak ke-rename)
    say(f"    [WARNING] Rename gagal 3x (file locked?). Pakai nama asli: {os.path.basename(original_path)}")
    return original_path


# ============================================================
# MAIN — proses 1 atau lebih kode (loop)
# ============================================================
def process_one_kode(driver, kode, fr, seq, total):
    """Proses 1 kode: search → klik cell → detail → btnCommentAttachment → dropdown → attachment → download → cleanup."""
    t0 = time.time()
    say(f"\n[{seq}/{total}] Kode: {kode}")
    try:
        # 1. Search
        say(f"  [1/8] Search kode...")
        if not search_kode(driver, kode, fr):
            say(f"  [ERROR] Kode tidak ditemukan di grid setelah search.")
            say(f"  (Mungkin kode bukan transaksi tanggal hari ini — cek filter date)")
            return False, "E_SEARCH"
        say(f"  [OK] Kode ditemukan di grid.")

        # 2. Single-click cell → detail
        say(f"  [2/8] Single-click cell (buka detail)...")
        how = click_cell_open_detail(driver, fr, kode)
        if not how:
            say(f"  [ERROR] Cell tidak bisa di-klik.")
            return False, "E_CLICK_CELL"
        say(f"  [OK] Diklik via {how}. Tunggu detail...")
        if not wait_detail_open(driver, kode, timeout=15):
            say(f"  [WARNING] Detail tidak terdeteksi, tapi lanjut cari btnCommentAttachment.")

        # 3. Click i#btnCommentAttachment
        say(f"  [3/8] Klik i#btnCommentAttachment (Komentar/Dokumen)...")
        how = click_comment_attachment(driver)
        if not how:
            say(f"  [ERROR] i#btnCommentAttachment tidak ditemukan.")
            say(f"  (Detail mungkin belum kebuka. Coba jalankan ulang, atau cek manual.)")
            recover_to_list(driver, kode)
            return False, "E_BTN_COMMENT"
        say(f"  [OK] btnCommentAttachment diklik via {how}. Tunggu dropdown...")

        # 4. Click first <a> di dropdown
        say(f"  [4/8] Klik <a> pertama di dropdown (buka attachment panel)...")
        how = click_first_dropdown_item(driver, timeout=8)
        if not how:
            # v8.5 DIAGNOSTIC: jangan SKIP dibilang "no document" — itu MASKS bug.
            # Kita nggak tahu apakah dokumen ada sampe bisa detect dropdown dgn reliable.
            # Fail dgn E_DROPDOWN. (v8.7: step 3.5 dump dihapus — switch_top+execute_script
            # di dump bikin dropdown auto-close. Jadi nggak ada dump utk lihat lagi.)
            say(f"  [ERROR] Dropdown tidak ditemukan setelah btnCommentAttachment (8s wait).")
            say(f"  Kemungkinan: (a) SJ ini TANPA dokumen (dropdown emang nggak muncul),")
            say(f"  atau (b) btnCommentAttachment click nggak trigger jQuery dropdown handler.")
            recover_to_list(driver, kode)
            return False, "E_DROPDOWN"
        say(f"  [OK] Dropdown item diklik via {how}. Tunggu attachment panel...")

        # 4.5 DIAGNOSTIC DUMP (v8.5) — lihat state attachment panel SETELAH klik dropdown <a>.
        #     Ini nunjukin apakah dropdown <a> click benar2 buka attachment panel (panel ada + visible?).
        dump_dropdown_state(driver, "AFTER click dropdown <a> (step 4.5)")

        # 4.6 SAFETY CHECK: pastikan nggak ke-navigation ke Dashboard
        time.sleep(1)
        if not verify_still_on_detail(driver, kode):
            say(f"  [ERROR] Halaman berubah (ke Dashboard?) setelah klik dropdown.")
            say(f"  Ini berarti dropdown click kena link salah. Abort + recover.")
            recover_to_list(driver, kode)
            return False, "E_NAVIGATED_AWAY"

        # 5. Wait attachment panel
        say(f"  [5/8] Tunggu attachment panel...")
        if not wait_attachment_panel(driver, timeout=15):
            say(f"  [WARNING] Attachment panel tidak terdeteksi. Tetap coba cari download icon.")

        # 6. Click icon-download-2 → download
        say(f"  [6/8] Klik i.icon-download-2 (download file)...")
        before = snapshot_downloads()
        how = click_download_icon(driver, timeout=10)
        if not how:
            say(f"  [ERROR] i.icon-download-2 tidak ditemukan di attachment panel.")
            say(f"  (Mungkin belum ada dokumen yg di-upload utk SJ ini. Cek manual.)")
            recover_to_list(driver, kode)
            return False, "E_DOWNLOAD_ICON"
        say(f"  [OK] Download icon diklik via {how}. Tunggu file (maks 90s)...")

        # 7. Wait file
        say(f"  [7/8] Tunggu file tersimpan (maks 90s)...")
        fname = wait_new_download(before, timeout=90)
        if not fname:
            say(f"  [ERROR] Download tidak selesai 90s. Cek manual: {DOWNLOAD_DIR}")
            recover_to_list(driver, kode)
            return False, "E_DOWNLOAD_TIMEOUT"
        final = os.path.join(DOWNLOAD_DIR, fname)
        say(f"  [OK] File tersimpan: {final}")

        # 7.5 Tutup attachment overlay DULU (supaya detail form accessible utk tab 'Info Lainnya').
        #     Tab 'Info Lainnya' ada di detail form (BUKAN di attachment overlay), jadi overlay
        #     harus ditutup dulu sebelum klik tab. (v8.3 — lihat catatan STEP 6 di docstring.)
        say(f"  [7.5/8] Tutup attachment overlay (buka akses ke detail form)...")
        close_attachment_overlay(driver, timeout=5)

        # 7.6 Klik tab 'Info Lainnya' + extract Cabang (v8.3) + extract Tanggal (v8.9)
        say(f"  [7.6/8] Klik tab 'Info Lainnya' + extract Cabang + Tanggal...")
        if click_info_lainnya_tab(driver, timeout=8):
            cabang = extract_cabang_value(driver, timeout=10)
            if cabang:
                cabang = sanitize_for_filename(cabang)
                say(f"    [OK] Cabang: {cabang}")
            else:
                cabang = "TanpaCabang"
                say(f"    [WARNING] Cabang tidak terbaca, pakai fallback: {cabang}")
            # v8.9: extract Tanggal (date value from input[name='transDate']).
            # Dari v8.8 dump utk 20451: [14] INPUT:transDate value='24/09/2026'.
            # Format: replace '/' -> '-' -> '24-09-2026'. Fallback literal 'Tanggal'.
            tanggal_raw = extract_tanggal_value(driver, timeout=5)
            if tanggal_raw:
                tanggal = tanggal_raw.replace('/', '-')  # "24/09/2026" -> "24-09-2026"
                tanggal = sanitize_for_filename(tanggal)
                say(f"    [OK] Tanggal: {tanggal}")
            else:
                tanggal = "Tanggal"  # fallback literal (v8.3-v8.8 behavior)
                say(f"    [WARNING] Tanggal tidak terbaca, pakai literal: {tanggal}")
        else:
            cabang = "TanpaCabang"
            tanggal = "Tanggal"
            say(f"    [WARNING] Tab 'Info Lainnya' tidak ditemukan, pakai fallback: cabang={cabang}, tanggal={tanggal}")

        # 7.7 Rename file: {kode}_{tanggal}_{cabang}.{ext}  (v8.9: tanggal = date value)
        say(f"  [7.7/8] Rename file: {kode}_{tanggal}_{cabang}{os.path.splitext(final)[1]}...")
        final = rename_download_file(final, kode, tanggal, cabang)
        fname = os.path.basename(final)
        say(f"    [OK] File renamed: {fname}")

        # 8. Tutup tab detail
        say(f"  [8/8] Tutup tab detail...")
        close_detail_tab(driver, kode, timeout=10)
        # v8.8: user confirm ada loading setelah close tab detail -> tunggu search box
        # (input[name=keyword]) visible lagi = list view udah ready buat kode berikutnya.
        say(f"  [8.5] Tunggu list view ready (search box visible)...")
        end = time.time() + 10
        list_ready = False
        while time.time() < end:
            try:
                switch_top(driver)
                inps = driver.find_elements(By.CSS_SELECTOR, "input[name='keyword']")
                for inp in inps:
                    try:
                        if inp.is_displayed():
                            list_ready = True
                            break
                    except: continue
                if list_ready: break
            except: pass
            time.sleep(0.5)
        if list_ready:
            say(f"  [OK] List view ready (search box visible).")
        else:
            say(f"  [WARNING] Search box belum visible setelah 10s. Kode berikutnya mungkin gagal search.")

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
    say("  DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v8.9)")
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
            say(f"\n  Jeda 1 detik sebelum kode berikutnya...")
            time.sleep(1)
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
        if ok:
            success += 1
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
