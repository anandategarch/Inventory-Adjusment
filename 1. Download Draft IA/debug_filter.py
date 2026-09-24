"""
debug_filter.py
Dump otomatis struktur UI filter ke debug_filter_output.txt.
Mencoba 5 varian klik chip untuk menemukan cara yang membuka popover search.
"""
import time
import socket
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

DEBUG_PORT = 9222
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_filter_output.txt")
L = []


def w(s=""):
    L.append(str(s))
    print(str(s))


JS_HELP = """
function isVisible(el) {
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
function clickSeq(el) {
    if (!el) return;
    const init = {bubbles: true, cancelable: true, view: window, button: 0, buttons: 1};
    ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t => {
        try { el.dispatchEvent(new MouseEvent(t, init)); } catch (e) {}
    });
}
function dump(el, lim) {
    if (!el) return '(null)';
    lim = lim || 1200;
    const s = el.outerHTML || '';
    return s.length > lim ? s.slice(0, lim) + ' ...[CUT]' : s;
}
function chipNode() {
    const nodes = Array.from(document.querySelectorAll('button, a, span, div, li')).filter(el => {
        const t = (el.innerText || el.textContent || '').trim().toUpperCase();
        return t.startsWith('PEMBUAT DATA:') && isVisible(el);
    });
    if (!nodes.length) return null;
    nodes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
    return nodes[0];
}
"""

JS_CHIP_EXISTS = JS_HELP + "return !!chipNode();"

JS_MARK = JS_HELP + """
return (function(){
    document.querySelectorAll('input, textarea').forEach(el => el.setAttribute('data-dbg-old', '1'));
    return document.querySelectorAll('[data-dbg-old]').length;
})()
"""

JS_NEAR_CHIP = JS_HELP + """
return (function(){
    const c = chipNode();
    if (!c) return {chip: null, inputs: []};
    const cr = c.getBoundingClientRect();
    const out = [];
    document.querySelectorAll('input, textarea').forEach(el => {
        if (!isVisible(el)) return;
        const r = el.getBoundingClientRect();
        if (r.top < cr.top - 60 || r.top > cr.bottom + 420) return;
        if (r.left < cr.left - 520 || r.left > cr.right + 520) return;
        out.push({
            old: el.hasAttribute('data-dbg-old'),
            type: el.getAttribute('type') || '',
            ph: el.getAttribute('placeholder') || '',
            rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
            html: dump(el, 400),
            parentHtml: dump(el.parentElement, 1500)
        });
    });
    return {
        chip: {text: (c.innerText || '').trim(), html: dump(c, 600), parentHtml: dump(c.parentElement, 2000)},
        inputs: out
    };
})()
"""

JS_NEW_INPUTS = JS_HELP + """
return (function(){
    const out = [];
    document.querySelectorAll('input, textarea').forEach(el => {
        if (el.hasAttribute('data-dbg-old')) return;
        const r = el.getBoundingClientRect();
        out.push({
            vis: isVisible(el),
            type: el.getAttribute('type') || '',
            ph: el.getAttribute('placeholder') || '',
            rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
            html: dump(el, 400),
            parentHtml: dump(el.parentElement, 1200)
        });
    });
    return out;
})()
"""

JS_ACTIVE = JS_HELP + """
return (function(){
    const a = document.activeElement;
    if (!a) return null;
    return {
        tag: a.tagName,
        type: (a.getAttribute && a.getAttribute('type')) || '',
        ph: (a.getAttribute && a.getAttribute('placeholder')) || '',
        old: !!(a.hasAttribute && a.hasAttribute('data-dbg-old'))
    };
})()
"""

JS_CLICK_CHIP = JS_HELP + """
return (function(v){
    const c = chipNode();
    if (!c) return 'NO_CHIP';
    if (v === 'dispatch_self')  { clickSeq(c); return 'ok'; }
    if (v === 'native_self')    { try { c.click(); } catch (e) {} return 'ok'; }
    if (v === 'dispatch_parent'){ clickSeq(c.parentElement || c); return 'ok'; }
    if (v === 'native_parent')  { try { (c.parentElement || c).click(); } catch (e) {} return 'ok'; }
    if (v === 'dispatch_caret') {
        const i = c.querySelector('i, svg, [class*="caret"], [class*="arrow"], [class*="icon"]');
        if (!i) return 'NO_CARET';
        clickSeq(i);
        return 'ok';
    }
    return 'UNKNOWN';
})(arguments[0])
"""

JS_TYPE = JS_HELP + """
return (function(text){
    function okText(el) {
        if (!el || el.tagName !== 'INPUT') return false;
        const t = (el.getAttribute('type') || 'text').toLowerCase();
        return t === 'text' || t === 'search' || t === '';
    }
    let cands = Array.from(document.querySelectorAll('input, textarea')).filter(el => !el.hasAttribute('data-dbg-old') && isVisible(el) && okText(el));
    let target = cands.length ? cands[cands.length - 1] : null;
    if (!target) {
        const c = chipNode();
        if (c) {
            const cr = c.getBoundingClientRect();
            const near = Array.from(document.querySelectorAll('input, textarea')).filter(el => {
                if (!isVisible(el) || !okText(el)) return false;
                const ph = (el.getAttribute('placeholder') || '').toUpperCase();
                if (ph.includes('KETIK')) return false;
                if (el.closest('.slick-grid')) return false;
                const r = el.getBoundingClientRect();
                return r.top >= cr.top - 60 && r.top <= cr.bottom + 420 &&
                       r.left >= cr.left - 520 && r.left <= cr.right + 520;
            });
            if (near.length) target = near[near.length - 1];
        }
    }
    if (!target) return {typed: false};
    target.focus();
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
    if (setter && setter.set) setter.set.call(target, text); else target.value = text;
    ['input', 'change', 'keyup'].forEach(ev => target.dispatchEvent(new Event(ev, {bubbles: true})));
    return {typed: true, ph: target.getAttribute('placeholder') || '', type: target.getAttribute('type') || '', old: target.hasAttribute('data-dbg-old')};
})(arguments[0])
"""

JS_SUGGESTIONS = JS_HELP + """
return (function(t){
    const up = t.toUpperCase();
    const hits = Array.from(document.querySelectorAll('body *')).filter(el => {
        if (!isVisible(el)) return false;
        if (el.children.length > 0) return false;
        const s = (el.textContent || '').trim().toUpperCase();
        return s.includes(up);
    }).slice(0, 8);
    return hits.map(el => ({
        tag: el.tagName,
        cls: String(el.className || '').slice(0, 100),
        text: (el.textContent || '').trim().slice(0, 120),
        html: dump(el, 500),
        parentHtml: dump(el.parentElement, 1200),
        grandHtml: dump(el.parentElement ? el.parentElement.parentElement : null, 1500)
    }));
})(arguments[0])
"""

JS_CLICK_FUNNEL = JS_HELP + """
return (function(){
    const sels = ['button[class*="filter"]','a[class*="filter"]','[class*="filter-toggle"]','button:has(i[class*="filter"])','i[class*="filter"]','[data-bind*="filter"]','[title*="ilter"]'];
    for (const s of sels) {
        const hit = Array.from(document.querySelectorAll(s)).find(isVisible);
        if (hit) { clickSeq(hit.tagName === 'I' ? hit.parentElement : hit); return 'CLICKED:' + s; }
    }
    return 'NOT_FOUND';
})()
"""

JS_CLICK_PEMBUAT = JS_HELP + """
return (function(){
    const nodes = Array.from(document.querySelectorAll('label, li, div, span, a')).filter(el => (el.innerText || el.textContent || '').trim() === 'Pembuat Data' && isVisible(el));
    if (!nodes.length) return 'NOT_FOUND';
    nodes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
    const t = nodes[0];
    clickSeq(t);
    let cb = t.querySelector('input[type="checkbox"]');
    if (!cb && t.closest('label')) cb = t.closest('label').querySelector('input[type="checkbox"]');
    if (cb) { clickSeq(cb); if (!cb.checked) { try { cb.click(); } catch (e) {} } }
    return 'CLICKED';
})()
"""


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_list_tab(driver):
    detector = 'input[placeholder*="Ketik dan"], .slick-grid, [class*="slick-grid"]'
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            url = (driver.current_url or "").lower()
            title = (driver.title or "").lower()
            if "accurate" not in url and "accurate" not in title:
                continue
            start = time.time()
            while time.time() - start < 8:
                driver.switch_to.default_content()
                if len(driver.find_elements(By.CSS_SELECTOR, detector)) > 0:
                    return True
                for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(iframe)
                        if len(driver.find_elements(By.CSS_SELECTOR, detector)) > 0:
                            return True
                    except Exception:
                        continue
                driver.switch_to.default_content()
                time.sleep(0.5)
        except Exception:
            continue
    return False


def keys_of(near):
    return {(i.get("ph"), tuple(i.get("rect") or [])) for i in near.get("inputs", [])}


def main():
    w("=" * 70)
    w("DEBUG FILTER PEMBUAT DATA")
    w("=" * 70)

    if not is_port_open(DEBUG_PORT):
        w("[ERR] Chrome debugging belum aktif. Jalankan BAT dulu.")
    else:
        opt = Options()
        opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        driver = webdriver.Chrome(options=opt)

        if not find_list_tab(driver):
            w("[ERR] Tab list Penyesuaian Persediaan tidak ditemukan.")
        else:
            w("[OK] Tab list ditemukan.")

            chip_exists = driver.execute_script(JS_CHIP_EXISTS)
            if chip_exists:
                w("[INFO] Chip 'Pembuat Data:' sudah ada - lewati corong & checkbox.")
            else:
                w("\n--- PERSIAPAN: KLIK CORONG ---")
                w(driver.execute_script(JS_CLICK_FUNNEL))
                time.sleep(1.0)
                w("--- PERSIAPAN: CENTANG PEMBUAT DATA ---")
                w(driver.execute_script(JS_CLICK_PEMBUAT))
                time.sleep(1.0)

            w("\n--- A. TANDAI INPUT LAMA & DUMP AREA CHIP ---")
            w(f"input ditandai: {driver.execute_script(JS_MARK)}")
            before = driver.execute_script(JS_NEAR_CHIP)
            w(before)
            base_keys = keys_of(before)

            worked = None
            for variant in ["dispatch_self", "native_self", "dispatch_caret", "dispatch_parent", "native_parent"]:
                w(f"\n--- B. COBA KLIK CHIP: {variant} ---")
                res = driver.execute_script(JS_CLICK_CHIP, variant)
                w(f"hasil klik: {res}")
                if res not in ("ok",):
                    continue
                time.sleep(0.9)
                new_inputs = driver.execute_script(JS_NEW_INPUTS)
                near = driver.execute_script(JS_NEAR_CHIP)
                active = driver.execute_script(JS_ACTIVE)
                w(f"input BARU: {new_inputs}")
                w(f"input dekat chip sekarang: {near.get('inputs')}")
                w(f"activeElement: {active}")
                grew = keys_of(near) - base_keys
                new_vis = [x for x in new_inputs if x.get("vis")]
                active_new = bool(active and active.get("tag") == "INPUT" and not active.get("old"))
                if grew or new_vis or active_new:
                    worked = variant
                    w(f">>> POPOVER TERBUKA via: {variant}")
                    break
                else:
                    w(">>> popover belum terbuka via varian ini.")

            if worked is None:
                w("\n[WARN] Tidak ada varian klik yang membuka popover.")

            w("\n--- C. KETIK 'pwktam' & DUMP SARAN ---")
            typed = driver.execute_script(JS_TYPE, "pwktam")
            w(f"ketik: {typed}")
            time.sleep(1.5)
            sugg = driver.execute_script(JS_SUGGESTIONS, "pwktam")
            w(f"jumlah elemen saran berisi 'PWKTAM': {len(sugg)}")
            for s in sugg:
                w(s)
            w("\n--- D. AREA CHIP SETELAH KETIK ---")
            w(driver.execute_script(JS_NEAR_CHIP))

    w("\n" + "=" * 70)
    w("SELESAI. File tersimpan di:")
    w(OUT)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    input("\nTekan Enter untuk keluar...")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
        input("Enter...")