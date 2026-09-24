"""
filter_pembuat_data.py  (v9.1 - FAST EDITION)
Verifikasi via chip nilai individual di panel (anti chip-terpotong).
Delay dipercepat tapi tetap acak; wait popup saran (1.2s) TIDAK dipangkas.
"""
import time
import socket
import subprocess
import os
import sys
import re
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

DEBUG_PORT = 9222
DEFAULT_BRANCHES = "RESTO.PWKTAM, RESTO.KWGGAL"

LIST_DETECTOR = 'input[placeholder*="Ketik dan"], .slick-grid, [class*="slick-grid"]'
SEL_FUNNEL = 'button.add-criteria, i.icn-transaction-filter'
SEL_PANEL = 'ul.dynamic-filter-panel'
SEL_CHIP = 'div.filter-item[key="createdByFilter"]'
SEL_CHIP_LABEL = 'div.filter-item[key="createdByFilter"] label.dropdown-toggle'
XP_LABEL_PEMBUAT = '//ul[contains(@class,"dynamic-filter-panel")]//label[normalize-space(.)="Pembuat Data"]'
XP_CHIP_LI_INPUT = '//div[@key="createdByFilter"]/parent::li//input'

# FAST, tetap acak
def human(min_s=0.15, max_s=0.45):
    time.sleep(random.uniform(min_s, max_s))

def human_click(min_s=0.25, max_s=0.70):
    time.sleep(random.uniform(min_s, max_s))

def say(msg):
    print(msg)
    sys.stdout.flush()

def is_ui_mode():
    return os.environ.get("IA_UI_MODE") == "1"

def pause_if_standalone():
    if not is_ui_mode():
        input("\nTekan Enter untuk keluar...")

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

JS_LOADING_VISIBLE = """
return (function(){
    const sels = ['.loader-image','[class*="loader"]','[class*="loading"]',
        '[class*="spinner"]','.nprogress','[class*="overlay"]','img[src*="loader"]'];
    const els = document.querySelectorAll(sels.join(','));
    for (const el of els) {
        try {
            const st = window.getComputedStyle(el);
            if (!st) continue;
            if (st.display === 'none' || st.visibility === 'hidden') continue;
            if (parseFloat(st.opacity) === 0) continue;
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return true;
        } catch (e) {}
    }
    return false;
})()
"""

JS_PANEL_OPEN = JS_VIS + """
return (function(){
  const inps = document.querySelectorAll('input');
  for (const i of inps){
    const ph = (i.getAttribute('placeholder')||'').toUpperCase();
    if (ph.includes('CARI') && vis(i)) return true;
  }
  return false;
})()
"""

JS_READ_SELECTED = JS_VIS + """
return (function(){
  const out = [];
  const els = document.querySelectorAll('span, div, li, button, a');
  for (const el of els){
    if (!vis(el)) continue;
    if (el.closest('.slick-grid, .slick-viewport, table')) continue;
    let t = (el.innerText || '').trim();
    t = t.replace(/\\s*[×x]\\s*$/,'').trim();
    if (!/^RESTO\\.[A-Z0-9]+$/i.test(t)) continue;
    let kidSame = false;
    for (const k of el.children){
      const kt = (k.innerText||'').trim().replace(/\\s*[×x]\\s*$/,'').trim().toUpperCase();
      if (kt === t.toUpperCase()) { kidSame = true; break; }
    }
    if (kidSame) continue;
    out.push(t.toUpperCase());
  }
  return Array.from(new Set(out));
})()
"""

JS_MARK_SUGGESTION = """
return (function(code){
    function vis2(el){
        if (!el || !(el instanceof Element)) return false;
        if (el.disabled) return false;
        const st = window.getComputedStyle(el);
        if (!st) return false;
        if (st.display === 'none' || st.visibility === 'hidden') return false;
        if (parseFloat(st.opacity) === 0) return false;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return false;
        return true;
    }
    function scanDoc(doc, tag){
        const up = String(code).toUpperCase();
        const cands = [];
        const all = doc.querySelectorAll('*');
        for (let i = 0; i < all.length; i++) {
            const el = all[i];
            if (!vis2(el)) continue;
            const tg = el.tagName;
            if (tg === 'SCRIPT' || tg === 'STYLE' || tg === 'INPUT' || tg === 'TEXTAREA') continue;
            const t = (el.textContent || '').toUpperCase();
            if (t.indexOf(up) === -1) continue;
            if (t.length > 160) continue;
            let kid = false;
            for (let k = 0; k < el.children.length; k++) {
                if ((el.children[k].textContent || '').toUpperCase().indexOf(up) !== -1) { kid = true; break; }
            }
            if (kid) continue;
            if (el.closest && el.closest('.slick-grid, table, .filter-container, .filter-item')) continue;
            cands.push(el);
        }
        if (!cands.length) return null;
        const pref = cands.filter(function(el){
            return el.closest && el.closest('[class*="dropdown"], [class*="suggestion"], [class*="autocomplete"], [class*="popup"], [class*="popover"], ul');
        });
        const pool = pref.length ? pref : cands;
        pool.sort(function(a, b){ return (a.textContent || '').length - (b.textContent || '').length; });
        const best = pool[0];
        best.setAttribute('data-fl-sug', '1');
        let row = best;
        if (best.closest) {
            row = best.closest('li, a, [class*="item"], [class*="option"], [class*="suggestion"]') || best.parentElement || best;
        }
        row.setAttribute('data-fl-sug-row', '1');
        return {where: tag, text: (best.textContent || '').trim().slice(0, 80)};
    }
    let r = scanDoc(document, 'self');
    if (r) return {found: true, where: r.where, text: r.text};
    try {
        if (window.top && window.top.document !== document) {
            r = scanDoc(window.top.document, 'top');
            if (r) return {found: true, where: r.where, text: r.text};
            const fr = window.top.document.querySelectorAll('iframe, frame');
            for (let f = 0; f < fr.length; f++) {
                try {
                    const d = fr[f].contentDocument;
                    if (!d || d === document) continue;
                    r = scanDoc(d, f);
                    if (r) return {found: true, where: r.where, text: r.text};
                } catch (e) {}
            }
        }
    } catch (e) {}
    return {found: false};
})(arguments[0])
"""

JS_CLEAR_MARKS = """
return (function(){
    document.querySelectorAll('[data-fl-sug]').forEach(e => e.removeAttribute('data-fl-sug'));
    document.querySelectorAll('[data-fl-sug-row]').forEach(e => e.removeAttribute('data-fl-sug-row'));
    return true;
})()
"""

# ============================================================
# UTILITAS CHROME
# ============================================================
def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def launch_chrome_silent():
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome = next((p for p in candidates if os.path.exists(p)), None)
    if not chrome:
        return False
    user_data = os.path.expandvars(r"%TEMP%\ChromeDebug_Accurate")
    try:
        subprocess.Popen(
            [chrome, f"--remote-debugging-port={DEBUG_PORT}",
             f"--user-data-dir={user_data}", "https://accurate.id"],
            creationflags=0x08000000
        )
        return True
    except Exception:
        return False

def connect_chrome():
    if not is_port_open(DEBUG_PORT):
        launch_chrome_silent()
        for _ in range(15):
            time.sleep(1)
            if is_port_open(DEBUG_PORT):
                break
        if not is_port_open(DEBUG_PORT):
            raise RuntimeError("Chrome debugging tidak aktif.")
    opt = Options()
    opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    return webdriver.Chrome(options=opt)

def find_and_switch_iframe(driver, selector, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        driver.switch_to.default_content()
        if len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0:
            return True
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                if len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0:
                    return True
            except Exception:
                continue
        driver.switch_to.default_content()
        time.sleep(0.35)
    driver.switch_to.default_content()
    return False

def find_list_tab(driver):
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            url = (driver.current_url or "").lower()
            title = (driver.title or "").lower()
            if "accurate" not in url and "accurate" not in title:
                continue
            if find_and_switch_iframe(driver, LIST_DETECTOR, timeout=6):
                return True
        except Exception:
            continue
    return False

def switch_back_to_list_frame(driver):
    if find_and_switch_iframe(driver, SEL_CHIP, timeout=6):
        return True
    return find_and_switch_iframe(driver, LIST_DETECTOR, timeout=6)

def wait_loading_done(driver, timeout=20, settle=0.5, grace=0.6):
    end_appear = time.time() + grace
    appeared = False
    while time.time() < end_appear:
        try:
            appeared = bool(driver.execute_script(JS_LOADING_VISIBLE))
        except Exception:
            appeared = False
        if appeared:
            break
        time.sleep(0.2)
    if not appeared:
        return True
    end = time.time() + timeout
    while time.time() < end:
        try:
            loading = bool(driver.execute_script(JS_LOADING_VISIBLE))
        except Exception:
            loading = False
        if not loading:
            time.sleep(settle)
            return True
        time.sleep(0.3)
    return False

def wait_grid_stable(driver, timeout=15, checks=2, interval=0.8):
    last = count_rows(driver)
    stable = 0
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(interval)
        cur = count_rows(driver)
        if cur == last:
            stable += 1
            if stable >= checks:
                return cur
        else:
            stable = 0
            last = cur
    return last

def wait_for(driver, by, value, timeout=10, must_visible=True):
    end = time.time() + timeout
    while time.time() < end:
        try:
            els = driver.find_elements(by, value)
        except Exception:
            els = []
        for el in els:
            try:
                if not must_visible or el.is_displayed():
                    return el
            except Exception:
                continue
        time.sleep(0.25)
    return None

def smart_click(driver, el, retries=3):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
            ActionChains(driver).move_to_element(el).click().perform()
            return "ACTIONCHAINS"
        except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
            time.sleep(0.4)
            continue
    try:
        el.click()
        return "ELCLICK"
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
            return "JSCLICK"
        except Exception:
            return "GAGAL"

def count_rows(driver):
    return driver.execute_script("""
        return (function(){
            let n = 0;
            try {
                n = Array.from(document.querySelectorAll('.slick-row')).filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }).length;
            } catch (e) {}
            return n;
        })()
    """)

def read_selected_codes(driver, timeout=4):
    end = time.time() + timeout
    while time.time() < end:
        opened = False
        try:
            opened = bool(driver.execute_script(JS_PANEL_OPEN))
        except Exception:
            opened = False
        if opened:
            try:
                codes = driver.execute_script(JS_READ_SELECTED) or []
                return [c.upper() for c in codes]
            except Exception:
                return []
        cl = wait_for(driver, By.CSS_SELECTOR, SEL_CHIP_LABEL, timeout=2)
        if cl:
            smart_click(driver, cl)
            time.sleep(0.4)
        else:
            time.sleep(0.3)
    return []

def is_code_selected(driver, code):
    codes = read_selected_codes(driver)
    up = code.upper()
    for c in codes:
        if c == ("RESTO." + up) or c.endswith(up):
            return True, codes
    return False, codes

def ensure_input_empty(driver, inp):
    try:
        inp.click()
    except Exception:
        pass
    try:
        inp.send_keys(Keys.CONTROL, 'a')
        inp.send_keys(Keys.DELETE)
    except Exception:
        pass
    try:
        val = inp.get_attribute('value') or ''
        if val.strip():
            driver.execute_script("""
                const el = arguments[0];
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
                if (setter && setter.set) setter.set.call(el,'');
                el.dispatchEvent(new Event('input',{bubbles:true}));
            """, inp)
    except Exception:
        pass

def find_panel_input(driver, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        for el in driver.find_elements(By.XPATH, XP_CHIP_LI_INPUT):
            try:
                if not el.is_displayed() or not el.is_enabled():
                    continue
                t = (el.get_attribute("type") or "text").lower()
                if t in ("text", "search", ""):
                    return el
            except Exception:
                continue
        time.sleep(0.25)
    return None

def open_panel_via_ko(driver):
    return driver.execute_script("""
        return (function(){
            try {
                const chip = document.querySelector('div.filter-item[key="createdByFilter"]');
                if (!chip || typeof ko === 'undefined') return 'NO_CHIP_OR_KO';
                const ctx = ko.contextFor(chip);
                const root = ctx && ctx.$root;
                const data = ctx && ctx.$data;
                if (!root || !data) return 'NO_CTX';
                if (root.filterPanel && typeof root.filterPanel.selectedFilter === 'function') {
                    root.filterPanel.selectedFilter(data);
                    return 'KO_SET_SELECTED';
                }
                if (typeof root.modifyFilter === 'function') {
                    root.modifyFilter(data, {stopPropagation:function(){}, preventDefault:function(){}, target: chip, currentTarget: chip});
                    return 'KO_MODIFY';
                }
                return 'NO_METHOD';
            } catch (e) { return 'ERR:' + e.message; }
        })()
    """)

def ensure_panel_input(driver):
    inp = find_panel_input(driver, timeout=3)
    if inp:
        return inp
    cl = wait_for(driver, By.CSS_SELECTOR, SEL_CHIP_LABEL, timeout=5)
    if cl:
        smart_click(driver, cl)
        time.sleep(0.4)
        inp = find_panel_input(driver, timeout=5)
    if not inp:
        open_panel_via_ko(driver)
        inp = find_panel_input(driver, timeout=4)
    return inp

def switch_to_where(driver, where):
    if where == "self":
        return True
    driver.switch_to.default_content()
    if where == "top":
        return True
    if isinstance(where, int):
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        if 0 <= where < len(frames):
            driver.switch_to.frame(frames[where])
            return True
    return False

# ============================================================
# STRATEGI SARAN
# ============================================================
def try_select_via_dom(driver, code, timeout=1.5):
    mark = None
    end = time.time() + timeout
    while time.time() < end:
        try:
            mark = driver.execute_script(JS_MARK_SUGGESTION, code)
        except Exception:
            mark = None
        if mark and mark.get("found"):
            break
        time.sleep(0.2)
    if not mark or not mark.get("found"):
        return None
    where = mark.get("where")
    switch_to_where(driver, where)
    row = None
    for sel in ('[data-fl-sug-row="1"]', '[data-fl-sug="1"]'):
        row = wait_for(driver, By.CSS_SELECTOR, sel, timeout=2, must_visible=False)
        if row:
            break
    if not row:
        try:
            driver.execute_script(JS_CLEAR_MARKS)
        except Exception:
            pass
        switch_back_to_list_frame(driver)
        return None
    how = smart_click(driver, row)
    try:
        driver.execute_script(JS_CLEAR_MARKS)
    except Exception:
        pass
    switch_back_to_list_frame(driver)
    return how if how != "GAGAL" else None

def try_select_via_keyboard(driver, inp):
    try:
        inp.click()
        time.sleep(0.15)
        inp.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.3)
        inp.send_keys(Keys.ENTER)
        return True
    except (StaleElementReferenceException, WebDriverException):
        return False

def try_select_via_coordinates(driver, inp, dy_list=(24, 32, 18, 40)):
    try:
        r = inp.rect
        half = int(r.get("height", 30) / 2)
    except (StaleElementReferenceException, WebDriverException):
        return False
    for dy in dy_list:
        try:
            human_click()
            ActionChains(driver).move_to_element(inp).move_by_offset(0, half + dy).click().perform()
            human()
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
            time.sleep(0.3)
            continue
    return False

def read_branches():
    raw = os.environ.get("IA_FILTER_BRANCHES", DEFAULT_BRANCHES)
    items = [x.strip() for x in re.split(r"[,;]", raw) if x.strip()]
    if not items:
        items = [x.strip() for x in DEFAULT_BRANCHES.split(",") if x.strip()]
    return items

# ============================================================
# MAIN
# ============================================================
def main():
    TARGET_CODES = read_branches()
    say("Memulai filter Pembuat Data...")
    say(f"Target: {', '.join(TARGET_CODES)}")
    print()

    try:
        driver = connect_chrome()
    except Exception as e:
        say(f"Gagal: {e}")
        pause_if_standalone()
        return 1

    say("Terhubung ke Chrome.")
    human()

    say("Mencari tab list Penyesuaian Persediaan...")
    if not find_list_tab(driver):
        say("Gagal: Halaman list tidak ditemukan.")
        pause_if_standalone()
        return 1

    say("Tab list ditemukan.")
    wait_loading_done(driver)
    rows_before = wait_grid_stable(driver, timeout=8, checks=1)
    human()

    chip = wait_for(driver, By.CSS_SELECTOR, SEL_CHIP, timeout=2)
    if chip:
        say("Chip 'Pembuat Data' sudah ada, lewati corong & checkbox.")
    else:
        say("Membuka panel filter...")
        funnel = wait_for(driver, By.CSS_SELECTOR, SEL_FUNNEL, timeout=8)
        if not funnel:
            say("Gagal: Tombol corong tidak ditemukan.")
            pause_if_standalone()
            return 1
        human_click()
        smart_click(driver, funnel)
        human()

        panel = wait_for(driver, By.CSS_SELECTOR, SEL_PANEL, timeout=6)
        if not panel:
            say("Gagal: Panel dropdown filter tidak terbuka.")
            pause_if_standalone()
            return 1
        label = wait_for(driver, By.XPATH, XP_LABEL_PEMBUAT, timeout=5)
        if not label:
            say("Gagal: Label 'Pembuat Data' tidak ditemukan.")
            pause_if_standalone()
            return 1
        human_click()
        smart_click(driver, label)
        wait_loading_done(driver)

        chip = wait_for(driver, By.CSS_SELECTOR, SEL_CHIP, timeout=10)
        if not chip:
            say("Gagal: Chip tidak muncul setelah dicentang.")
            pause_if_standalone()
            return 1

    selected = 0
    say("Memilih kode target...")
    for code in TARGET_CODES:
        switch_back_to_list_frame(driver)

        already, _ = is_code_selected(driver, code)
        if already:
            say(f"  {code}: sudah ada, dilewati.")
            selected += 1
            continue

        say(f"  {code}: mengetik dan memilih saran...")
        ok_code = False
        for attempt in range(2):
            already, _ = is_code_selected(driver, code)
            if already:
                ok_code = True
                break

            wait_loading_done(driver)
            switch_back_to_list_frame(driver)
            inp = ensure_panel_input(driver)
            if not inp:
                continue
            ensure_input_empty(driver, inp)
            human()
            try:
                inp.send_keys(code)
            except StaleElementReferenceException:
                continue

            time.sleep(1.2)  # KRITIS: tunggu popup saran (jangan dipangkas)

            how = try_select_via_dom(driver, code, timeout=1.5)
            if how:
                wait_loading_done(driver)
                switch_back_to_list_frame(driver)
                ok, _ = is_code_selected(driver, code)
                if ok:
                    ok_code = True
                    break

            switch_back_to_list_frame(driver)
            inp2 = ensure_panel_input(driver) or inp
            if try_select_via_keyboard(driver, inp2):
                wait_loading_done(driver)
                time.sleep(0.2)
                switch_back_to_list_frame(driver)
                ok, _ = is_code_selected(driver, code)
                if ok:
                    ok_code = True
                    break

            switch_back_to_list_frame(driver)
            inp3 = ensure_panel_input(driver) or inp
            ensure_input_empty(driver, inp3)
            try:
                inp3.send_keys(code)
                time.sleep(1.2)
            except StaleElementReferenceException:
                continue
            if try_select_via_coordinates(driver, inp3):
                wait_loading_done(driver)
                time.sleep(0.2)
                switch_back_to_list_frame(driver)
                ok, _ = is_code_selected(driver, code)
                if ok:
                    ok_code = True
                    break

        if ok_code:
            selected += 1
            say(f"  {code}: berhasil diterapkan.")
        else:
            say(f"  {code}: GAGAL dipilih.")
        human()

    say("Verifikasi akhir...")
    wait_loading_done(driver)
    switch_back_to_list_frame(driver)
    rows_after = wait_grid_stable(driver)
    codes_final = read_selected_codes(driver, timeout=5)

    say(f"Baris sebelum: {rows_before} | Baris setelah: {rows_after}")
    say(f"Kode terpilih di panel: {', '.join(codes_final) if codes_final else '(tidak terbaca)'}")
    say(f"Kode target tercapai: {selected}/{len(TARGET_CODES)}")
    print()

    if selected > 0:
        say(f"Filter selesai. {selected} cabang berhasil diterapkan.")
        pause_if_standalone()
        return 0
    else:
        say("Filter gagal: tidak ada cabang yang berhasil ditambahkan.")
        pause_if_standalone()
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        say(f"Error tak terduga: {type(e).__name__}: {e}")
        pause_if_standalone()
        sys.exit(1)