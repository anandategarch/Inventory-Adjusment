import hashlib, json, os, queue, re, subprocess, sys, threading, time, uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_VERSION = 'V16 - Optimized + Reliability Fix'
APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_FILE = APP_DIR / 'config.json'

# ---------------------------------------------------------------------------
# V16 config defaults.
#
# V16 fixes three critical issues found in V15 production runs:
#   1. Smart resto transition had an unreliable search-input clear
#      (Control+A failed on Power BI's Angular custom input, causing the
#      new value to be APPENDED to the old value -> wrong row matched
#      -> selection cleared instead of replaced -> every resto failed).
#      V16 fixes this with a native JS value setter that bypasses Angular's
#      change detection, AND requires exact text match on the found row.
#      As an extra safety, smart_resto_transition defaults to OFF in V16.
#   2. Next Page click timed out at 5000ms even when the button was
#      visible/enabled/stable (Power BI overlay intercepts the click).
#      V16 adds a force=True retry and dispatch_event('click') fallback.
#   3. Recovery after a resto error did a FULL _hard_reset_page (URL reload
#      + 20+ Next-clicks, ~30s each). V16 adds _light_recovery that only
#      clears the Resto selection (~3s) and falls back to hard reset only
#      if the clear itself fails.
#
# Timing values are the same as V15 (already proven fast when working).
# Every optimization can be turned off via a flag.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    'powerbi_url': 'https://app.powerbi.com/view?r=eyJrIjoiNTRmNTI1ZDQtMjg5Ny00MDNiLTg3ZjYtZTM4Njc5OWYwNjIwIiwidCI6IjczZThkZTM5LTVhM2EtNGE3My1iMTc0LTRmY2I0Yjg5MGUwMSJ9',
    'page': '19,20,21,22',
    'restos': '4217\nDPKLIM\nMTR\nBSD',
    'viewport_width': 1920,
    'viewport_height': 1080,
    'headless': True,
    'navigation_timeout_ms': 60000,
    'default_timeout_ms': 30000,
    'page_load_wait_ms': 3000,
    'after_filter_wait_ms': 3000,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'output_dir': str(APP_DIR / 'output'),
    'output_format': 'PNG',
    'stability_min_wait_ms': 500,
    'stability_poll_ms': 400,
    'stability_required_cycles': 2,
    'stability_timeout_ms': 30000,
    'recovery_timeout_ms': 20000,
    'page_stability_timeout_ms': 30000,
    # --- V16 optimization flags ---
    # Smart transition is OFF by default in V16. It works on simple Power BI
    # slicers but the V15 production run proved it unreliable on this report
    # (Angular custom input + search retained between opens). Enable manually
    # to test on your environment; V16 includes a JS-based clear fix that
    # makes it safer than V15, but the V14 clear-then-select path is the
    # proven reliable default.
    'opt_sequential_page_nav': True,
    'opt_smart_resto_transition': False,
    'opt_reuse_stable_screenshot': True,
    'opt_merge_final_stability': True,
    'opt_skip_page_load_fixed_wait': True,
    'opt_light_recovery': True,         # V16: clear selection instead of full reload on resto error
    'opt_force_click_next_page': True,  # V16: force=True retry + dispatch_event fallback for Next Page
    'page_navigation_step_timeout_ms': 12000,
    # --- V16 tightened interaction waits (ms) ---
    'wait_dropdown_open_ms': 500,
    'wait_after_search_ms': 900,
    'wait_after_select_ms': 400,
    'wait_after_uncheck_ms': 600,
    'wait_clear_search_ms': 200,
    'wait_escape_ms': 350,
    'next_page_click_timeout_ms': 5000,   # V16: initial click timeout before force retry
    'next_page_force_click_timeout_ms': 3000, # V16: force click timeout
}
if not CONFIG_FILE.exists():
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding='utf-8')
try:
    CONFIG = {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text(encoding='utf-8'))}
except Exception:
    CONFIG = DEFAULT_CONFIG.copy()

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


def ensure_playwright():
    global sync_playwright
    if sync_playwright is not None:
        return
    py = sys.executable
    subprocess.check_call([py, '-m', 'pip', 'install', '--quiet', '--upgrade', 'playwright'])
    subprocess.check_call([py, '-m', 'playwright', 'install', 'chromium'])
    from playwright.sync_api import sync_playwright as sp
    sync_playwright = sp


def js_own_text_script(filter_expr):
    return f'''() => {{
        const out=[]; const all=document.querySelectorAll('*');
        for(const el of all){{
          const own=Array.from(el.childNodes).filter(n=>n.nodeType===3).map(n=>(n.textContent||'').trim()).join('');
          const r=el.getBoundingClientRect();
          if({filter_expr}){{ out.push({{x:r.x+r.width/2,y:r.y+r.height/2,left:r.x,w:r.width,h:r.height,text:own}}); }}
        }}
        out.sort((a,b)=>a.left-b.left); return out;
    }}'''


class Engine:
    def __init__(self, log, progress, done):
        self.log_cb, self.progress_cb, self.done_cb = log, progress, done
        self.stop_requested = False
        # V15: cache of the last stable screenshot bytes, reused for capture.
        self._last_stable_png = None
        self._cached_page_number = None

    def log(self, msg):
        """Pass msg to callback. The callback (CLI log_cb or GUI add_log)
        is responsible for adding the HH:MM:SS timestamp prefix."""
        self.log_cb(msg)

    def stop(self):
        self.stop_requested = True

    def set_output_dir(self, folder):
        global OUTPUT_DIR
        OUTPUT_DIR = Path(folder).expanduser().resolve()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG['output_dir'] = str(OUTPUT_DIR)
        try:
            CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass

    def debug(self, page, label):
        try:
            debug_dir = OUTPUT_DIR / '_debug'
            debug_dir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', label)
            path = debug_dir / f'debug_{safe}_{int(time.time())}.png'
            page.screenshot(path=str(path), type='png')
            self.log(f'   Debug: Debug screenshot: _debug/{path.name}')
            return path
        except Exception as e:
            self.log(f'   WARN: Gagal membuat debug screenshot: {e}')
            return None

    def _page_output_dir(self, page_number):
        try:
            page_num = int(page_number)
        except Exception as e:
            raise ValueError(f'Nomor page tidak valid: {page_number!r}') from e
        if page_num < 1:
            raise ValueError(f'Nomor page harus >= 1, bukan {page_num}.')
        page_dir = OUTPUT_DIR / f'Page {page_num}'
        page_dir.mkdir(parents=True, exist_ok=True)
        return page_dir

    @staticmethod
    def _safe_filename(value):
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(value).strip())
        return safe or 'RESTO'

    def save_capture(self, page, page_number, resto, output_format, png_bytes=None):
        """Transactional output writer.

        V15: accepts optional `png_bytes` from the last stability check.
        When provided, the screenshot is NOT taken again — the bytes already
        represent the verified stable state. This saves one full-page
        screenshot per resto (~200-400ms) without any loss of accuracy,
        because `wait_for_powerbi_stable` only returns after 2+ identical
        snapshots, proving the screenshot is the final rendered state.
        """
        safe_resto = self._safe_filename(resto)
        output_format = str(output_format).upper().strip()
        if output_format not in ('PNG', 'PDF'):
            raise ValueError(f'Format output tidak didukung: {output_format}')

        page_dir = self._page_output_dir(page_number)
        base = safe_resto
        png_path = page_dir / f'{base}.png'
        pdf_path = page_dir / f'{base}.pdf'
        token = uuid.uuid4().hex[:10]
        temp_png = page_dir / f'.{base}.{token}.tmp.png'
        temp_pdf = page_dir / f'.{base}.{token}.tmp.pdf'

        try:
            if png_bytes:
                # V15: reuse the stability-check screenshot bytes directly.
                temp_png.write_bytes(png_bytes)
            else:
                page.screenshot(path=str(temp_png), type='png', full_page=False,
                                animations='disabled', caret='hide')
            if not temp_png.exists() or temp_png.stat().st_size == 0:
                raise RuntimeError('Screenshot sementara tidak terbentuk atau berukuran 0 byte.')

            if output_format == 'PNG':
                os.replace(temp_png, png_path)
                try:
                    if pdf_path.exists():
                        pdf_path.unlink()
                except Exception as e:
                    self.log(f'   WARN: PNG baru sudah tersimpan, tetapi PDF lama tidak terhapus: {e}')
                self.log(f'   Output: Page {page_number}/{png_path.name}')
                return png_path

            try:
                from PIL import Image
            except Exception as e:
                raise RuntimeError(f'Library Pillow tidak tersedia untuk membuat PDF: {e}') from e

            with Image.open(temp_png) as img:
                rgb = img.convert('RGB')
                rgb.save(temp_pdf, 'PDF', resolution=150.0)

            if not temp_pdf.exists() or temp_pdf.stat().st_size == 0:
                raise RuntimeError('PDF sementara tidak terbentuk atau berukuran 0 byte.')

            os.replace(temp_pdf, pdf_path)
            try:
                if png_path.exists():
                    png_path.unlink()
            except Exception as e:
                self.log(f'   WARN: PDF baru sudah tersimpan, tetapi PNG lama tidak terhapus: {e}')
            self.log(f'   Output: Page {page_number}/{pdf_path.name}')
            return pdf_path
        except Exception as e:
            raise RuntimeError(
                f'Gagal menyimpan output {output_format} untuk {resto} di {page_dir}: {e}'
            ) from e
        finally:
            for tmp in (temp_png, temp_pdf):
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass

    def find_dropdowns(self, page):
        return page.evaluate(js_own_text_script("own==='All' && r.width>50 && r.height>10 && r.top>40 && r.top<100 && r.left>0"))

    def find_label_rect(self, page, label):
        return page.evaluate("""
        (label) => {
          const out=[];
          for (const el of document.querySelectorAll('*')) {
            const own = Array.from(el.childNodes)
              .filter(n => n.nodeType === 3)
              .map(n => (n.textContent || '').trim())
              .join('');
            if (own.toLowerCase() !== label.toLowerCase()) continue;
            const r = el.getBoundingClientRect();
            if (r.width > 10 && r.height > 8 && r.top >= 0 && r.top < (window.innerHeight || 1080) && r.left >= 0) {
              out.push({left:r.left, top:r.top, right:r.right, bottom:r.bottom,
                        centerX:r.left+r.width/2, centerY:r.top+r.height/2,
                        text:own});
            }
          }
          out.sort((a,b)=>a.top-b.top || a.left-b.left);
          return out.length ? out[0] : null;
        }
        """, label)

    def find_resto_dropdown(self, page):
        label = self.find_label_rect(page, 'Resto')
        if not label:
            return None, self.find_dropdowns(page), 'label Resto tidak ditemukan'

        dds = page.evaluate("""
        (label) => {
          const all = Array.from(document.querySelectorAll("*"));
          const candidates = [];

          for (const el of all) {
            const r = el.getBoundingClientRect();

            if (r.width < 100 || r.width > 400) continue;
            if (r.height < 20 || r.height > 80) continue;

            if (r.top < label.bottom - 8 || r.top > label.bottom + 90) continue;

            const center = r.left + r.width / 2;
            if (center < label.left - 80 || center > label.right + 280) continue;

            const text = (el.textContent || "").trim();
            const hasSvg = !!el.querySelector("svg");
            const hasButton = !!el.querySelector("button");
            if (!text && !hasSvg && !hasButton) continue;

            const score =
              Math.abs(center - (label.left + label.width / 2)) +
              Math.abs(r.top - label.bottom) * 4;

            candidates.push({
              x: center,
              y: r.top + r.height / 2,
              left: r.left,
              top: r.top,
              width: r.width,
              height: r.height,
              text,
              score
            });
          }

          candidates.sort((a,b) => a.score - b.score);
          return candidates.length ? candidates[0] : null;
        }
        """, label)

        if dds:
            return dds, self.find_dropdowns(page), 'label Resto + geometry'

        return None, self.find_dropdowns(page), 'label Resto ditemukan tetapi kontrol tidak teridentifikasi'

    def try_dropdown(self, page, dd, value):
        """Open the Resto slicer, search for value, and return its actual row."""
        page.mouse.click(dd['x'], dd['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_dropdown_open_ms', 500)))

        inp = self._find_resto_search_input(page, dd['x'])
        if inp:
            page.mouse.click(inp['x'], inp['y'])
            page.keyboard.press('Control+A')
            page.keyboard.press('Backspace')
            page.wait_for_timeout(int(CONFIG.get('wait_clear_search_ms', 200)))
            page.keyboard.type(value, delay=60)        # V14: 80 -> V15: 60
        else:
            self.log("   Input pencarian Resto tidak ditemukan; mencoba keyboard langsung")
            page.keyboard.type(value, delay=60)

        page.wait_for_timeout(int(CONFIG.get('wait_after_search_ms', 900)))
        row = self._find_resto_row(page, value, dd['x'], dd['y'])
        if not row:
            return {'match': False}
        return {'match': True, **row}

    def _find_resto_search_input(self, page, target_x):
        return page.evaluate("""
        (targetX) => {
          const c=[];
          for (const i of document.querySelectorAll('input')) {
            const r=i.getBoundingClientRect();
            if (r.width>50 && r.height>5 && r.top>40 && r.top<760 && r.width<1000) {
              c.push({
                x:r.x+r.width/2,
                y:r.y+r.height/2,
                left:r.x, top:r.y, right:r.right, bottom:r.bottom,
                dist:Math.abs((r.x+r.width/2)-targetX),
                w:r.width, h:r.height
              });
            }
          }
          c.sort((a,b)=>a.dist-b.dist);
          return c.length ? c[0] : null;
        }
        """, target_x)

    def _open_resto_slicer(self, page):
        dd, _, method = self.find_resto_dropdown(page)
        if not dd:
            return None, None, 'Dropdown Resto tidak ditemukan.'
        page.mouse.click(dd['x'], dd['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_dropdown_open_ms', 500)))
        inp = self._find_resto_search_input(page, dd['x'])
        return dd, inp, method

    def _clear_resto_search(self, page, inp):
        """V16: clear the Resto search input reliably.

        V14/V15 used Control+A + Backspace, which fails on Power BI's
        Angular custom input (Control+A selects the whole page, not the
        input content; the new typed value gets APPENDED to the old one).

        V16 uses a native JS value setter that triggers Angular's change
        detection via a synthetic 'input' event. This is the same technique
        React/Angular testing libraries use to set controlled input values.
        As a belt-and-suspenders fallback, we also try triple-click + Delete.
        """
        if not inp:
            return
        try:
            # Tier 1: native JS value setter (Angular/React compatible).
            cleared = page.evaluate("""
            (payload) => {
              const el = document.elementFromPoint(payload.x, payload.y);
              if (!el) return false;
              // Find the actual input (could be the element itself or a child).
              const input = el.tagName === 'INPUT' ? el : el.querySelector('input');
              if (!input) return false;
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              setter.call(input, '');
              input.dispatchEvent(new Event('input', {bubbles: true}));
              input.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }
            """, {'x': inp['x'], 'y': inp['y']})
            if cleared:
                page.wait_for_timeout(int(CONFIG.get('wait_clear_search_ms', 200)))
                return
        except Exception:
            pass
        # Tier 2: triple-click to select all text in the input, then Delete.
        try:
            page.mouse.click(inp['x'], inp['y'])
            page.mouse.click(inp['x'], inp['y'])
            page.mouse.click(inp['x'], inp['y'])
            page.wait_for_timeout(100)
            page.keyboard.press('Delete')
            page.keyboard.press('Backspace')
            page.wait_for_timeout(int(CONFIG.get('wait_clear_search_ms', 200)))
        except Exception:
            pass

    def _get_resto_display(self, page):
        dd, _, method = self.find_resto_dropdown(page)
        if not dd:
            return None, None, method
        text = (dd.get('text') or '').strip()
        text = re.sub(r'\s+', ' ', text)
        return text, dd, method

    @staticmethod
    def _normalize_resto_display(text):
        return re.sub(r'\s+', ' ', str(text or '')).strip().lower()

    def _is_no_resto_selection(self, text):
        t = self._normalize_resto_display(text)
        return t in ('', 'all', 'select all')

    def _is_multiple_resto_selection(self, text):
        t = self._normalize_resto_display(text)
        return 'multiple selections' in t or 'multiple selection' in t

    def _is_stop(self):
        return bool(self.stop_requested)

    def _get_report_signature(self, page, capture_bytes=False):
        """Return DOM + loading + viewport-image signature for the visible report.

        V15: when `capture_bytes=True`, also returns the raw PNG bytes of the
        screenshot so it can be reused by `save_capture` without a second
        capture. This is safe because the signature is only considered stable
        after `required_cycles` identical snapshots, meaning the bytes ARE the
        final rendered state.
        """
        try:
            dom_payload = page.evaluate(r"""
            () => {
              const norm = s => (s || '').replace(/\s+/g, ' ').trim();
              const visible = el => {
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
              };
              const loadingSelectors = [
                '[role="progressbar"]','[aria-busy="true"]','.spinner','.loading',
                '[class*="spinner"]','[class*="loading"]','[class*="progress"]'
              ];
              let loadingCount=0;
              for (const sel of loadingSelectors) {
                for (const el of document.querySelectorAll(sel)) if (visible(el)) loadingCount++;
              }
              const nodes=[];
              for (const el of document.querySelectorAll('body *')) {
                if (!visible(el)) continue;
                const r=el.getBoundingClientRect();
                if (r.bottom<0 || r.top>window.innerHeight || r.right<0 || r.left>window.innerWidth) continue;
                if (r.width<20 || r.height<10) continue;
                const own=Array.from(el.childNodes)
                  .filter(n=>n.nodeType===3)
                  .map(n=>norm(n.textContent))
                  .filter(Boolean).join(' ');
                if (!own) continue;
                nodes.push({t:own.slice(0,180),x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)});
              }
              nodes.sort((a,b)=>a.y-b.y || a.x-b.x || a.t.localeCompare(b.t));
              return {loadingCount,nodes:nodes.slice(0,300)};
            }
            """)
            shot = page.screenshot(
                type='png', full_page=False,
                animations='disabled', caret='hide'
            )
            shot_hash = hashlib.sha256(shot).hexdigest()
            dom_key = json.dumps(dom_payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            result = {
                'loading_count': int(dom_payload.get('loadingCount', 0)),
                'dom_key': dom_key,
                'shot_hash': shot_hash
            }
            if capture_bytes:
                result['png_bytes'] = shot
            return result
        except Exception:
            return None

    def wait_for_powerbi_stable(self, page, reason='', timeout_ms=None, required_cycles=None, capture_bytes=False):
        """Finite, stop-aware wait; requires no loading and repeated identical visual state.

        V15: returns the last stable signature (including PNG bytes when
        `capture_bytes=True`) so the caller can reuse the screenshot for
        capture instead of taking another one.
        """
        timeout_ms = int(timeout_ms or CONFIG.get('stability_timeout_ms', 30000))
        required_cycles = int(required_cycles or CONFIG.get('stability_required_cycles', 2))
        poll_ms = int(CONFIG.get('stability_poll_ms', 400))
        min_wait_ms = int(CONFIG.get('stability_min_wait_ms', 500))
        started = time.monotonic()
        last_sig = None
        stable_cycles = 0
        if reason:
            self.log(f'   Menunggu Power BI stabil ({reason})...')
        while True:
            if self._is_stop():
                self.log('   Stability wait dihentikan oleh pengguna.')
                return None
            elapsed_ms = int((time.monotonic()-started)*1000)
            if elapsed_ms >= timeout_ms:
                self.log(f'   WARN: Timeout stability setelah {elapsed_ms/1000:.1f}s.')
                return None
            time.sleep(poll_ms/1000)
            if self._is_stop():
                return None
            elapsed_ms = int((time.monotonic()-started)*1000)
            sig = self._get_report_signature(page, capture_bytes=capture_bytes)
            stable_now = bool(
                sig and sig.get('loading_count', 1) == 0 and
                sig.get('shot_hash') and sig.get('dom_key')
            )
            same_as_last = bool(sig and last_sig and
                                sig.get('loading_count') == last_sig.get('loading_count') and
                                sig.get('shot_hash') == last_sig.get('shot_hash') and
                                sig.get('dom_key') == last_sig.get('dom_key'))
            if stable_now and same_as_last and elapsed_ms >= min_wait_ms:
                stable_cycles += 1
            else:
                stable_cycles = 0
            last_sig = sig
            if stable_now and elapsed_ms >= min_wait_ms and stable_cycles >= required_cycles:
                self.log(f'   Report stabil ({stable_cycles} siklus berturut-turut, {elapsed_ms/1000:.1f}s).')
                return sig
        # Unreachable

    def _wait_after_filter(self, page, value):
        return self.wait_for_powerbi_stable(
            page, f'setelah filter Resto {value}',
            capture_bytes=bool(CONFIG.get('opt_reuse_stable_screenshot', True))
        )

    def _wait_after_page_navigation(self, page, page_number):
        return self.wait_for_powerbi_stable(
            page,
            f'Page {page_number}',
            timeout_ms=int(CONFIG.get('page_stability_timeout_ms', 30000))
        )

    def _find_next_page_locator(self, page):
        selectors = [
            'button[aria-label="Next Page"]',
            'button[aria-label="next page"]',
            'button[aria-label="Next page"]',
            '[role="button"][aria-label="Next Page"]',
            '[role="button"][aria-label="next page"]'
        ]
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if loc.is_visible(timeout=1500):
                    return loc
            except Exception:
                continue
        return None

    def _find_page_identity_candidates(self, page):
        try:
            return page.evaluate(r"""
            () => {
              const out=[];
              const seen=new Set();
              const els=document.querySelectorAll(
                'button,a,[role="tab"],[role="button"],[aria-current],[aria-selected]'
              );
              for(const el of els){
                const r=el.getBoundingClientRect();
                const cs=getComputedStyle(el);
                if(r.width<4||r.height<4||cs.display==='none'||cs.visibility==='hidden') continue;
                if(r.bottom<0||r.top>window.innerHeight||r.right<0||r.left>window.innerWidth) continue;
                const attrs=[
                  el.getAttribute('aria-label')||'',
                  el.getAttribute('title')||'',
                  el.getAttribute('data-page-name')||'',
                  el.getAttribute('data-automation-id')||'',
                  el.innerText||'',
                  el.textContent||''
                ].map(x=>(x||'').replace(/\\s+/g,' ').trim());
                const raw=attrs.join(' | ');
                const navish=/\\b(page|halaman)\\b/i.test(raw) ||
                             el.getAttribute('role')==='tab' ||
                             el.getAttribute('aria-current')==='page' ||
                             el.getAttribute('aria-selected')==='true';
                if(!navish) continue;
                const m=raw.match(/\\b(?:page|halaman)\\s*[:#-]?\\s*(\\d+)\\b/i) ||
                        raw.match(/(?:^|\\s)(\\d{1,3})(?:\\s*$|\\s*\\|)/);
                if(!m) continue;
                const n=parseInt(m[1],10);
                if(!Number.isFinite(n)||n<1||n>9999) continue;
                const selected = el.getAttribute('aria-selected')==='true' ||
                                 el.getAttribute('aria-current')==='page' ||
                                 el.getAttribute('data-selected')==='true';
                const key=n+'|'+Math.round(r.x)+'|'+Math.round(r.y)+'|'+selected;
                if(seen.has(key)) continue;
                seen.add(key);
                out.push({page:n,selected,text:raw.slice(0,220),x:r.x,y:r.y,w:r.width,h:r.height});
              }
              return out;
            }
            """) or []
        except Exception:
            return []

    def _get_current_page_number(self, page, use_cache=False):
        # V15: optional cache to avoid repeated expensive DOM scans within a
        # single page iteration. The cache is invalidated whenever we navigate.
        if use_cache and self._cached_page_number is not None:
            return self._cached_page_number
        candidates = self._find_page_identity_candidates(page)
        selected = [x['page'] for x in candidates if x.get('selected')]
        if len(set(selected)) == 1:
            result = selected[0]
        else:
            nums = [x['page'] for x in candidates]
            unique = sorted(set(nums))
            if len(unique) == 1:
                result = unique[0]
            else:
                result = None
        if use_cache:
            self._cached_page_number = result
        return result

    def _invalidate_page_cache(self):
        self._cached_page_number = None

    def _page_signature_without_screenshot(self, page):
        try:
            return self._get_report_signature(page)
        except Exception:
            return None

    def _click_next_button(self, next_btn):
        """V16: click Next Page with three-tier fallback.

        Tier 1: normal click (respects actionability checks).
        Tier 2: force=True (skip actionability, dispatch at coordinates).
        Tier 3: dispatch_event('click') (synthetic event, no mouse movement).

        Power BI sometimes has an overlay/iframe that intercepts the mouse
        click even when the button is visibly enabled. The force+dispatch
        fallbacks ensure we never block the entire batch on a single click.
        """
        click_timeout = int(CONFIG.get('next_page_click_timeout_ms', 5000))
        force_timeout = int(CONFIG.get('next_page_force_click_timeout_ms', 3000))
        use_force_fallback = bool(CONFIG.get('opt_force_click_next_page', True))

        # Tier 1: normal click.
        try:
            next_btn.click(timeout=click_timeout)
            return 'normal'
        except Exception as e:
            if not use_force_fallback:
                raise
            self.log(f'   WARN: Normal click Next Page timeout ({click_timeout}ms); mencoba force click...')

        # Tier 2: force click (skip actionability checks).
        try:
            next_btn.click(timeout=force_timeout, force=True)
            return 'force'
        except Exception as e:
            self.log(f'   WARN: Force click juga gagal ({e}); mencoba dispatch_event...')

        # Tier 3: synthetic click event via JS.
        try:
            next_btn.dispatch_event('click')
            return 'dispatch'
        except Exception as e:
            raise RuntimeError(f'Semua metode click Next Page gagal: {e}')

    def _click_next_and_verify_transition(self, page, expected_page=None):
        next_btn = self._find_next_page_locator(page)
        if next_btn is None:
            raise RuntimeError('Tombol Next Page tidak ditemukan.')
        before_identity = self._get_current_page_number(page)
        before_sig = self._page_signature_without_screenshot(page)
        try:
            if next_btn.is_disabled(timeout=1000):
                raise RuntimeError('Tombol Next Page disabled; kemungkinan sudah mencapai halaman terakhir.')
        except RuntimeError:
            raise
        except Exception:
            pass
        method = self._click_next_button(next_btn)
        if method != 'normal':
            self.log(f'   Next Page diklik via metode: {method}')

        timeout_ms = int(CONFIG.get('page_navigation_step_timeout_ms', 12000))
        started = time.monotonic()
        changed = False
        after_identity = None
        after_sig = None
        while int((time.monotonic()-started)*1000) < timeout_ms:
            if self._is_stop():
                return False
            page.wait_for_timeout(300)   # V14: 450 -> V15: 300
            after_identity = self._get_current_page_number(page)
            after_sig = self._page_signature_without_screenshot(page)
            if before_identity is not None and after_identity is not None:
                changed = after_identity != before_identity
            elif before_sig and after_sig:
                changed = (
                    after_sig.get('shot_hash') != before_sig.get('shot_hash') or
                    after_sig.get('dom_key') != before_sig.get('dom_key')
                )
            if changed:
                break

        if not changed:
            raise RuntimeError('Klik Next Page tidak menghasilkan perubahan page yang terverifikasi.')
        if expected_page is not None and after_identity is not None and after_identity != expected_page:
            raise RuntimeError(
                f'Identitas page salah setelah navigasi: terbaca Page {after_identity}, target Page {expected_page}.'
            )
        return True

    def _navigate_to_page(self, page, page_number):
        """Fresh-load the report, then walk sequentially to target page."""
        target = int(page_number)
        if target < 1:
            raise ValueError('Nomor page harus >= 1.')
        self.log(f'   Reset report -> navigasi ke Page {target}...')
        self._invalidate_page_cache()
        page.goto(CONFIG['powerbi_url'], wait_until='domcontentloaded',
                  timeout=int(CONFIG['navigation_timeout_ms']))
        if CONFIG.get('opt_skip_page_load_fixed_wait', True):
            # V15: rely on the stability gate instead of a fixed 8s wait.
            page.wait_for_timeout(1500)
        else:
            page.wait_for_timeout(int(CONFIG['page_load_wait_ms']))
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            self.log('   WARN: Network idle tidak tercapai; menggunakan stability gate.')
        if not self._wait_after_page_navigation(page, 1):
            raise RuntimeError('Report awal belum stabil setelah reset.')

        detected = self._get_current_page_number(page, use_cache=True)
        if detected not in (None, 1):
            self.log(f'   WARN: Report awal terbaca Page {detected}; tetap gunakan fresh navigation.')
            detected = None
            self._cached_page_number = None
        if target == 1:
            if detected == 1:
                self.log('   Page 1 terverifikasi.')
            else:
                self.log('   WARN: Identitas Page 1 tidak terekspos oleh DOM; state awal stabil akan digunakan.')
            return True

        for next_page in range(2, target + 1):
            if self._is_stop():
                return False
            self._click_next_and_verify_transition(page, expected_page=next_page if detected is not None else None)
            detected = self._get_current_page_number(page, use_cache=True) or detected
            if next_page % 5 == 0 or next_page == target:
                self.log(f'      • Navigasi mencapai Page {next_page}')

        if not self._wait_after_page_navigation(page, target):
            raise RuntimeError(f'Page {target} belum stabil setelah navigasi.')
        final_identity = self._get_current_page_number(page, use_cache=True)
        if final_identity is not None and final_identity != target:
            raise RuntimeError(f'Verifikasi final gagal: terbaca Page {final_identity}, target Page {target}.')
        if final_identity is None:
            self.log(f'   WARN: Page {target} stabil tetapi nomor page tidak terekspos oleh DOM; transisi telah diverifikasi.')
        else:
            self.log(f'   Page {target} terverifikasi.')
        return True

    def _advance_to_next_page(self, page, from_page, to_page):
        """V15: advance from one page to the next via Next-clicks, no full reload.

        This is the core optimization for multi-page batches: instead of
        reloading the URL and walking from page 1 every time, we click
        Next (to_page - from_page) times. Each click is verified exactly
        like in `_navigate_to_page`, so accuracy is preserved.
        """
        diff = int(to_page) - int(from_page)
        if diff <= 0:
            # Should not happen (caller ensures ascending order); fall back.
            return self._navigate_to_page(page, to_page)

        self.log(f'   Advance Page {from_page} -> {to_page} ({diff}x Next)...')
        self._invalidate_page_cache()
        detected = self._get_current_page_number(page, use_cache=True)
        for step in range(1, diff + 1):
            if self._is_stop():
                return False
            expected = from_page + step
            self._click_next_and_verify_transition(page, expected_page=expected if detected is not None else None)
            detected = self._get_current_page_number(page, use_cache=True) or detected
            if step == diff:
                self.log(f'      • Navigasi mencapai Page {expected}')

        if not self._wait_after_page_navigation(page, to_page):
            raise RuntimeError(f'Page {to_page} belum stabil setelah advance.')
        final_identity = self._get_current_page_number(page, use_cache=True)
        if final_identity is not None and final_identity != to_page:
            raise RuntimeError(f'Verifikasi final gagal: terbaca Page {final_identity}, target Page {to_page}.')
        if final_identity is None:
            self.log(f'   WARN: Page {to_page} stabil tetapi nomor page tidak terekspos oleh DOM; transisi telah diverifikasi.')
        else:
            self.log(f'   Page {to_page} terverifikasi (advance).')
        return True

    def _hard_reset_page(self, page, page_number):
        try:
            return self._navigate_to_page(page, int(page_number))
        except Exception as e:
            self.log(f'   FAIL: Hard reset ke Page {page_number} gagal: {e}')
            self.debug(page, f'hard_reset_failed_page_{page_number}')
            raise

    def _clear_exact_resto_value(self, page, value):
        """Uncheck one known selected Resto value inside the open slicer."""
        dd, inp, _ = self._open_resto_slicer(page)
        if not dd:
            return False, 'Dropdown Resto tidak ditemukan.'
        self._clear_resto_search(page, inp)
        inp = self._find_resto_search_input(page, dd['x'])
        if inp:
            page.mouse.click(inp['x'], inp['y'])
            page.keyboard.press('Control+A')
            page.keyboard.press('Backspace')
            page.keyboard.type(value, delay=50)
            page.wait_for_timeout(600)   # V14: 1000 -> V15: 600
        row = self._find_resto_row(page, value, dd['x'], dd['y'])
        if not row:
            page.keyboard.press('Escape')
            return False, f'Nilai aktif "{value}" tidak ditemukan di popup Resto.'
        self.log(f'      • Uncheck Resto: {row["text"]}')
        page.mouse.click(row['x'], row['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_after_uncheck_ms', 600)))
        page.keyboard.press('Escape')
        page.wait_for_timeout(int(CONFIG.get('wait_escape_ms', 350)))
        display, _, _ = self._get_resto_display(page)
        if self._is_no_resto_selection(display):
            return True, 'All'
        return False, display or '(kosong)'

    def clear_all_resto_selections(self, page, context_label='', page_number=None):
        display, dd, _ = self._get_resto_display(page)
        if not dd:
            return False, 'Dropdown Resto tidak ditemukan.'
        self.log(f'   Membersihkan selection aktif di slicer Resto{(" ("+context_label+")") if context_label else ""}...')
        self.log(f'      • State Resto saat ini: "{display or ""}"')
        if self._is_no_resto_selection(display):
            self.log('   Slicer Resto sekarang tidak memiliki selection aktif.')
            return True, []
        if self._is_multiple_resto_selection(display):
            self.log('   WARN: Slicer Resto menunjukkan Multiple selections; DOM tidak aman untuk menebak item mana saja yang aktif.')
            if page_number is not None:
                self._hard_reset_page(page, page_number)
                display2, _, _ = self._get_resto_display(page)
                if self._is_no_resto_selection(display2):
                    self.log('   Hard reset berhasil: Resto kembali ke All.')
                    return True, ['<hard reset>']
            return False, display or 'Multiple selections'
        ok, detail = self._clear_exact_resto_value(page, display)
        if ok:
            self.log('   Slicer Resto sekarang tidak memiliki selection aktif.')
            return True, [display]
        self.log(f'   WARN: Uncheck "{display}" belum terverifikasi; detail={detail}')
        if page_number is not None:
            self._hard_reset_page(page, page_number)
            display2, _, _ = self._get_resto_display(page)
            if self._is_no_resto_selection(display2):
                self.log('   Hard reset berhasil: Resto kembali ke All.')
                return True, ['<hard reset>']
        return False, detail

    def _find_resto_row(self, page, value, target_x, target_y, exact=False):
        """V16: find the Resto row matching `value`.

        `exact=True` requires the row text to EQUAL the value (not just
        contain it). This prevents matching a container that happens to
        include both the new search value AND the old selected value
        (e.g. text="1049.DPKMAR1042.KWGGAL" when searching for
        "1049.DPKMAR"). Used by smart_resto_transition to avoid the
        V15 bug where a parent element was clicked instead of the row.
        """
        return page.evaluate("""
        (payload) => {
          const value=(payload.value||'').toLowerCase().trim();
          const exact=payload.exact;
          const targetX=payload.targetX, targetY=payload.targetY;
          const candidates=[];
          function own(el){
            return Array.from(el.childNodes).filter(n=>n.nodeType===3)
              .map(n=>(n.textContent||'').trim()).join(' ').replace(/\\s+/g,' ').trim();
          }
          function txt(el){ return own(el) || (el.textContent||'').replace(/\\s+/g,' ').trim(); }
          function norm(t){ return (t||'').replace(/\\s+/g,' ').trim().toLowerCase(); }
          for(const el of document.querySelectorAll('*')){
            const t=txt(el); if(!t || t.length>120) continue;
            const low=norm(t);
            if(exact){
              if(low !== value) continue;
            } else {
              if(!low.includes(value)) continue;
            }
            if(/^(select all|all|search)$/i.test(t)) continue;
            const r=el.getBoundingClientRect();
            if(r.width<40||r.height<10||r.height>90) continue;
            if(r.top<=targetY+5||r.top>760) continue;
            if(Math.abs((r.left+r.width/2)-targetX)>420) continue;
            let row=el;
            for(let i=0;i<8&&row;i++,row=row.parentElement){
              const rr=row.getBoundingClientRect();
              const rt=txt(row);
              const role=(row.getAttribute('role')||'').toLowerCase();
              if(!rt || rt.length>160) continue;
              if(rr.width>=80 && rr.height>=16 && rr.height<=100 &&
                 rr.top>targetY+5 && rr.top<760 &&
                 Math.abs((rr.left+rr.width/2)-targetX)<=420 &&
                 (role==='option'||role==='listitem'||row.querySelector('[aria-checked],[aria-selected],[aria-pressed]'))){
                break;
              }
            }
            const rr=row.getBoundingClientRect();
            if(rr.width<40||rr.height<10) continue;
            let selected=false;
            let n=row;
            for(let i=0;i<8&&n;i++,n=n.parentElement){
              for(const a of ['aria-checked','aria-selected','aria-pressed']){
                if((n.getAttribute(a)||'').toLowerCase()==='true') selected=true;
              }
            }
            candidates.push({x:rr.left+rr.width/2,y:rr.top+rr.height/2,text:txt(row),
                             selected,w:rr.width,h:rr.height,
                             score: Math.abs((rr.left+rr.width/2)-targetX)+Math.abs((rr.top+rr.height/2)-(targetY+120))});
          }
          candidates.sort((a,b)=>a.score-b.score || b.w*b.h-a.w*a.h);
          return candidates.length ? candidates[0] : null;
        }
        """, {'value':value,'targetX':target_x,'targetY':target_y,'exact':exact})

    def verify_single_resto(self, page, expected_value):
        """Verify the CLOSED Resto slicer display equals the target exactly."""
        display, dd, _ = self._get_resto_display(page)
        if not dd:
            return False, 'Dropdown Resto tidak ditemukan saat verifikasi.'
        actual = self._normalize_resto_display(display)
        expected = self._normalize_resto_display(expected_value)
        if actual == expected:
            return True, display
        # V17 fix: Power BI displays resto with code prefix (e.g. "1345.DPKLIM")
        # but user enters "DPKLIM" (without prefix). Check if expected is contained
        # in actual (suffix/substring match). This handles the prefix case.
        if expected and expected in actual:
            return True, display
        if self._is_no_resto_selection(display):
            return False, f'Tidak ada selection pada slicer Resto; target={expected_value}'
        if self._is_multiple_resto_selection(display):
            return False, f'Multiple selections pada slicer Resto; target={expected_value}'
        return False, f'Seleksi Resto tidak sesuai target: "{display}"; target={expected_value}'

    def _select_resto_direct(self, page, value, dd):
        """V16: open slicer, clear search via JS, search value, click EXACT row.

        Fixes the V15 bug where Control+A failed to clear the Angular input,
        causing the new value to be appended and a wrong (container) row to
        be clicked. V16 uses the JS-native value setter in _clear_resto_search
        and requires an EXACT text match on the found row.
        """
        page.mouse.click(dd['x'], dd['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_dropdown_open_ms', 500)))
        inp = self._find_resto_search_input(page, dd['x'])
        if inp:
            # V16: use the reliable JS-based clear (Control+A was broken).
            self._clear_resto_search(page, inp)
            page.mouse.click(inp['x'], inp['y'])
            page.keyboard.type(value, delay=60)
        else:
            page.keyboard.type(value, delay=60)
        page.wait_for_timeout(int(CONFIG.get('wait_after_search_ms', 900)))
        # V16: exact=True — reject containers that contain both old+new values.
        row = self._find_resto_row(page, value, dd['x'], dd['y'], exact=True)
        if not row:
            # Fallback: try substring match (V14 behavior) if exact fails.
            # This is safe because the JS clear now works; the only reason
            # exact fails is if the row text has extra whitespace or a prefix.
            row = self._find_resto_row(page, value, dd['x'], dd['y'], exact=False)
            if row and value.upper() not in (row.get('text','') or '').upper():
                row = None
        if not row:
            try: page.keyboard.press('Escape')
            except Exception: pass
            return False
        self.log(f'   Ditemukan pilihan "{row["text"]}" di dropdown Resto')
        page.mouse.click(row['x'], row['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_after_select_ms', 400)))
        try: page.keyboard.press('Escape')
        except Exception: pass
        return True

    def set_filter(self, page, value, page_number=None):
        """Apply exactly one Resto selection.

        V15: uses smart resto transition by default. When the current slicer
        state is a single value (not All, not Multiple), it skips the clear
        step and directly searches + clicks the new value — Power BI
        single-select slicers replace the selection automatically.

        Falls back to the V14 clear-then-select path when:
          - the slicer shows Multiple selections, OR
          - the direct select fails verification (slicer turned out to be
            multi-select and added the value instead of replacing it).

        Returns True only after the slicer display is verified to equal
        `value` AND the report is stable. Also caches the last stable
        screenshot bytes (via _wait_after_filter) for reuse by save_capture.
        """
        if self._is_stop():
            return False

        smart = bool(CONFIG.get('opt_smart_resto_transition', True))
        self._last_stable_png = None

        if smart:
            # Try the fast path first.
            display, dd, method = self._get_resto_display(page)
            if dd and not self._is_multiple_resto_selection(display) and not self._is_no_resto_selection(display):
                # Single value currently selected — try direct replace.
                current = self._normalize_resto_display(display)
                target = self._normalize_resto_display(value)
                if current == target:
                    self.log(f'   Resto sudah terpilih: "{display}" (skip)')
                    sig = self._wait_after_filter(page, value)
                    if sig and sig.get('png_bytes'):
                        self._last_stable_png = sig['png_bytes']
                    verified, detail = self.verify_single_resto(page, value)
                    if verified:
                        self.log(f'   Verifikasi single selection Resto: {detail}')
                        return True
                    self.log(f'   FAIL: Verifikasi Resto gagal: {detail}')
                    return False

                self.log(f'   Smart transition: "{display}" -> "{value}" (skip clear)')
                res = self._select_resto_direct(page, value, dd)
                if not res:
                    self.log(f'   WARN: Smart transition gagal; fallback ke clear-then-select.')
                else:
                    sig = self._wait_after_filter(page, value)
                    if sig and sig.get('png_bytes'):
                        self._last_stable_png = sig['png_bytes']
                    verified, detail = self.verify_single_resto(page, value)
                    if verified:
                        self.log(f'   Verifikasi single selection Resto: {detail}')
                        return True
                    if self._is_multiple_resto_selection(detail):
                        self.log(f'   WARN: Slicer ternyata multi-select; fallback ke clear-then-select.')
                    else:
                        self.log(f'   FAIL: Verifikasi Resto gagal: {detail}')
                        self.debug(page, f'verify_Resto_failed_smart_{value}')
                        return False
            elif dd and self._is_no_resto_selection(display):
                # Already All — direct select without clear.
                self.log(f'   Slicer All; langsung pilih "{value}"')
                res = self._select_resto_direct(page, value, dd)
                if not res:
                    self.log(f'   WARN: Direct select gagal; fallback ke clear-then-select.')
                else:
                    sig = self._wait_after_filter(page, value)
                    if sig and sig.get('png_bytes'):
                        self._last_stable_png = sig['png_bytes']
                    verified, detail = self.verify_single_resto(page, value)
                    if verified:
                        self.log(f'   Verifikasi single selection Resto: {detail}')
                        return True
                    self.log(f'   FAIL: Verifikasi Resto gagal: {detail}')
                    self.debug(page, f'verify_Resto_failed_direct_{value}')
                    return False

        # Fallback / non-smart path: clear then select (V14 behavior).
        self.log(f'   Menyiapkan slicer Resto untuk "{value}"...')
        reset_ok, _ = self.clear_all_resto_selections(page, f'target {value}', page_number=page_number)
        if not reset_ok:
            self.debug(page, f'clear_Resto_failed_before_{value}')
            return False
        if self._is_stop():
            return False

        self.log(f'   Mencari dropdown Resto untuk "{value}"...')
        dd, all_dds, method = self.find_resto_dropdown(page)
        if not dd:
            self.log('   FAIL: Dropdown Resto tidak ditemukan')
            self.debug(page, f'dropdown_notfound_{value}')
            return False
        self.log(f'   {len(all_dds)} dropdown ditemukan: [{", ".join(str(round(x["left"])) for x in all_dds)}]')
        self.log(f'   Target Resto: x={round(dd["x"])} y={round(dd["y"])} ({method})')

        res = self.try_dropdown(page, dd, value)
        if not res.get('match'):
            self.log(f'   FAIL: "{value}" tidak ditemukan di dropdown Resto')
            self.debug(page, f'dropdown_Resto_notfound_{value}')
            try: page.keyboard.press('Escape')
            except Exception: pass
            return False

        self.log(f'   Ditemukan pilihan "{res["text"]}" di dropdown Resto')
        if self._is_stop():
            return False
        page.mouse.click(res['x'], res['y'])
        page.wait_for_timeout(int(CONFIG.get('wait_after_select_ms', 400)))
        try: page.keyboard.press('Escape')
        except Exception: pass

        sig = self._wait_after_filter(page, value)
        if not sig:
            self.debug(page, f'filter_not_stable_{value}')
            return False
        if sig.get('png_bytes'):
            self._last_stable_png = sig['png_bytes']

        display, _, _ = self._get_resto_display(page)
        self.log(f'   State Resto setelah render: "{display or ""}"')
        verified, detail = self.verify_single_resto(page, value)
        if not verified:
            self.log(f'   FAIL: Verifikasi Resto gagal: {detail}')
            self.debug(page, f'verify_Resto_failed_{value}')
            return False
        self.log(f'   Verifikasi single selection Resto: {detail}')
        return True

    @staticmethod
    def parse_pages(raw):
        if isinstance(raw, (list, tuple, set)):
            tokens = list(raw)
        else:
            text = str(raw or '').strip()
            tokens = re.split(r'[,;\n]+', text)
        pages=[]
        for token in tokens:
            token=str(token).strip()
            if not token:
                continue
            m=re.fullmatch(r'(\d+)\s*-\s*(\d+)', token)
            if m:
                a,b=int(m.group(1)),int(m.group(2))
                step=1 if b>=a else -1
                pages.extend(range(a,b+step,step))
                continue
            if re.fullmatch(r'\d+', token):
                pages.append(int(token)); continue
            raise ValueError(f'Format page tidak valid: {token!r}. Contoh: 19,20,21 atau 19-22.')
        pages=sorted(dict.fromkeys(pages))
        if not pages:
            raise ValueError('Daftar page kosong.')
        if any(p<1 for p in pages):
            raise ValueError('Nomor page harus >= 1.')
        return pages

    @staticmethod
    def parse_restos(restos):
        seen=set(); clean=[]; duplicates=[]
        for raw in restos:
            value=re.sub(r'\s+', ' ', str(raw or '')).strip().upper()
            if not value:
                continue
            key=value.casefold()
            if key in seen:
                duplicates.append(value)
                continue
            seen.add(key); clean.append(value)
        if duplicates:
            duplicates_text=', '.join(duplicates[:10])
        else:
            duplicates_text=''
        return clean, duplicates_text

    def _result_key(self, page_number, resto):
        return f'Page {int(page_number)} / {resto}'

    def _write_batch_manifest(self, pages, restos, output_format, page_results, started_at, ended_at):
        token=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        manifest=OUTPUT_DIR / f'batch_{token}.json'
        payload={
            'app_version': APP_VERSION,
            'pages': pages,
            'restos': restos,
            'output_format': output_format,
            'started_at': started_at,
            'ended_at': ended_at,
            'page_results': page_results,
            'summary': {
                'total_jobs': len(pages)*len(restos),
                'success': sum(1 for v in page_results.values() if v.get('success')),
                'failed': sum(1 for v in page_results.values() if not v.get('success')),
                'pages_total': len(pages),
                'pages_with_error': sorted({int(v['page']) for v in page_results.values() if v.get('page_error')})
            }
        }
        manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return manifest

    def _recover_after_resto_error(self, page, page_number, resto):
        """V16: light recovery — clear Resto selection first, only full-reload if needed.

        V15 always called _hard_reset_page on resto error (URL reload + 20+
        Next-clicks, ~30s each). V16 first tries clear_all_resto_selections
        (~3-5s) which is sufficient for most errors. Only if the clear itself
        fails do we fall back to a full hard reset.
        """
        self.log(f'   Membersihkan state setelah error Resto {resto}...')
        if CONFIG.get('opt_light_recovery', True):
            try:
                ok, detail = self.clear_all_resto_selections(
                    page, context_label=f'light recovery {resto}', page_number=None
                )
                if ok:
                    self.log(f'   Light recovery berhasil: {detail}')
                    return True
            except Exception as e:
                self.log(f'   WARN: Light recovery gagal: {e}')
            self.log(f'   WARN: Light recovery tidak cukup; fallback ke hard reset...')
        else:
            # Legacy V15 behavior: always hard reset.
            try:
                ok, detail = self.clear_all_resto_selections(
                    page, context_label=f'cleanup error {resto}', page_number=None
                )
                if ok:
                    self.log(f'   Cleanup state setelah error berhasil: {detail}')
                    return True
            except Exception as e:
                self.log(f'   WARN: Cleanup langsung gagal: {e}')
        try:
            self._hard_reset_page(page, page_number)
            self.log(f'   Hard reset berhasil setelah error Resto {resto}.')
            return True
        except Exception as e:
            self.log(f'   FAIL: Hard reset setelah error Resto {resto} juga gagal: {e}')
            return False

    def run(self, pages, restos, output_format):
        page_results = {}
        browser = None
        context = None
        page = None
        started_at = datetime.now().isoformat(timespec='seconds')
        total_jobs = len(pages) * len(restos)
        completed_jobs = 0

        # V15: sequential page navigation. Pages are already sorted ascending
        # by parse_pages(). We navigate to the first page via full reset, then
        # advance to subsequent pages via Next-clicks only. This avoids
        # reloading the URL and re-walking from page 1 for every page.
        sequential = bool(CONFIG.get('opt_sequential_page_nav', True)) and len(pages) > 1
        if sequential:
            self.log(f'V15 sequential page navigation aktif: {pages[0]} -> {pages[-1]} via Next-clicks.')

        try:
            self.set_output_dir(CONFIG.get('output_dir') or str(APP_DIR / 'output'))
            output_format = str(output_format).upper().strip()
            if output_format not in ('PNG', 'PDF'):
                raise ValueError('Format output harus PNG atau PDF.')
            ensure_playwright()
            self.progress_cb(0, total_jobs, 'Menyiapkan browser...')
            self.log(f'V15 Optimized mulai | Pages={pages} | Resto={len(restos)} | Jobs={total_jobs} | Output={output_format}')

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=bool(CONFIG['headless']),
                    args=['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu','--disable-extensions','--disable-software-rasterizer','--disable-features=site-per-process']
                )
                context = browser.new_context(
                    viewport={'width': int(CONFIG['viewport_width']), 'height': int(CONFIG['viewport_height'])},
                    user_agent=CONFIG['user_agent']
                )
                page = context.new_page()
                page.set_default_timeout(int(CONFIG['default_timeout_ms']))

                current_page_number = None  # V15: track which page the browser is on.

                for page_index, page_number in enumerate(pages, start=1):
                    if self._is_stop():
                        break
                    self.log(f'── PAGE {page_number} ({page_index}/{len(pages)}) ──')
                    page_error = False
                    page_setup_message = None

                    try:
                        if sequential and current_page_number is not None and page_number > current_page_number:
                            # V15: advance via Next-clicks (fast path).
                            self._advance_to_next_page(page, current_page_number, page_number)
                        else:
                            # First page, or non-sequential: full reset.
                            self._hard_reset_page(page, page_number)
                        current_page_number = page_number
                    except Exception as e:
                        # If the fast advance fails, try one full reset before
                        # declaring the page failed. This keeps accuracy intact.
                        if sequential and current_page_number is not None:
                            self.log(f'   WARN: Advance gagal; mencoba full reset ke Page {page_number}...')
                            try:
                                self._hard_reset_page(page, page_number)
                                current_page_number = page_number
                            except Exception as e2:
                                page_error = True
                                page_setup_message = str(e2)
                                self.log(f'   FAIL: PAGE SETUP GAGAL: Page {page_number} — {e2}')
                                self.debug(page, f'page_setup_failed_{page_number}')
                                current_page_number = None
                        else:
                            page_error = True
                            page_setup_message = str(e)
                            self.log(f'   FAIL: PAGE SETUP GAGAL: Page {page_number} — {e}')
                            self.debug(page, f'page_setup_failed_{page_number}')
                            current_page_number = None

                    for resto_index, resto in enumerate(restos, start=1):
                        if self._is_stop():
                            break
                        completed_jobs += 1
                        self.progress_cb(completed_jobs-1, total_jobs, f'Page {page_number} / {resto}')
                        key=self._result_key(page_number, resto)
                        self.log(f'── Page {page_number} | Resto {resto_index}/{len(restos)}: {resto} ──')

                        if page_error:
                            page_results[key]={
                                'page': page_number, 'resto': resto,
                                'success': False, 'page_error': True,
                                'stage': 'PAGE_SETUP', 'message': page_setup_message
                            }
                            self.log(f'   ⏭️ Dilewati karena setup Page {page_number} gagal.')
                            self.progress_cb(completed_jobs, total_jobs, f'Gagal Page {page_number} / {resto}')
                            continue

                        try:
                            filter_ok=self.set_filter(page, resto, page_number=page_number)
                            if not filter_ok and not self.stop_requested:
                                self.log(f'   Retry: Recovery satu kali untuk Resto {resto}...')
                                try:
                                    # V16: light recovery first (clear Resto, no full reload).
                                    # Only hard-reset if the clear fails. This avoids the
                                    # ~30s URL-reload+Next-click cost on every resto error.
                                    recovered = self._recover_after_resto_error(page, page_number, resto)
                                    if recovered:
                                        current_page_number = page_number
                                        filter_ok=self.set_filter(page, resto, page_number=page_number)
                                    else:
                                        filter_ok=False
                                except Exception as recovery_error:
                                    self.log(f'   WARN: Recovery awal gagal: {recovery_error}')
                                    filter_ok=False
                            if not filter_ok:
                                if self.stop_requested:
                                    raise RuntimeError('Proses dihentikan oleh pengguna.')
                                raise RuntimeError(f'Resto "{resto}" tidak ditemukan atau gagal dipilih/render stabil.')

                            # V15: set_filter already verified (a) report stable and
                            # (b) slicer display == resto. The V14 "final check"
                            # duplicated both. We skip it unless explicitly disabled.
                            if not CONFIG.get('opt_merge_final_stability', True):
                                if not self.wait_for_powerbi_stable(page, f'final check sebelum capture {resto}'):
                                    raise RuntimeError(f'Report belum stabil untuk capture Resto "{resto}".')
                                verified, detail=self.verify_single_resto(page, resto)
                                if not verified:
                                    raise RuntimeError(f'Final verification gagal: {detail}')

                            # Page identity verification is unique to run() — always keep it.
                            final_page=self._get_current_page_number(page, use_cache=True)
                            if final_page is not None and final_page != page_number:
                                raise RuntimeError(f'Final page verification gagal: terbaca Page {final_page}, target Page {page_number}.')

                            # V15: reuse the stable screenshot bytes from set_filter
                            # when available; otherwise save_capture will take a fresh one.
                            reuse_png = self._last_stable_png if CONFIG.get('opt_reuse_stable_screenshot', True) else None
                            capture_path=self.save_capture(page, page_number, resto, output_format, png_bytes=reuse_png)
                            page_results[key]={
                                'page': page_number, 'resto': resto,
                                'success': True, 'page_error': False,
                                'stage': 'CAPTURE', 'message': 'OK',
                                'output': str(capture_path)
                            }
                            self.log(f'   Selesai: {resto} -> {capture_path.name}')
                        except Exception as e:
                            msg=str(e)
                            page_results[key]={
                                'page': page_number, 'resto': resto,
                                'success': False, 'page_error': False,
                                'stage': 'RESTO', 'message': msg
                            }
                            self.log(f'   FAIL: Gagal: Page {page_number} / {resto} — {msg}')
                            self.debug(page, f'error_page{page_number}_{resto}')
                            if not self.stop_requested:
                                # V16: light recovery — clear Resto selection (~3s)
                                # instead of full hard reset (~30s). Falls back to
                                # hard reset internally if the clear fails.
                                try:
                                    self._recover_after_resto_error(page, page_number, resto)
                                    current_page_number = page_number
                                except Exception:
                                    current_page_number = None
                            else:
                                break
                        finally:
                            self.progress_cb(completed_jobs, total_jobs, f'Page {page_number} / {resto}: ' + ('OK' if page_results.get(key,{}).get('success') else 'GAGAL'))

                    if not self.stop_requested and page_index < len(pages):
                        if sequential and current_page_number is not None:
                            self.log(f'   Page {page_number} selesai. Page {pages[page_index]} via Next-click (tanpa reload).')
                        else:
                            self.log(f'   Page {page_number} selesai. Page {pages[page_index]} akan dimulai dari fresh reset.')

                ended_at=datetime.now().isoformat(timespec='seconds')
                manifest=self._write_batch_manifest(pages, restos, output_format, page_results, started_at, ended_at)
                success=sum(1 for v in page_results.values() if v.get('success'))
                failed=total_jobs-success
                self.done_cb({
                    'success': success,
                    'failed': failed,
                    'manifest': str(manifest),
                    'results': page_results,
                    'output_format': output_format,
                    'pages': pages,
                    'restos': restos
                })
                self.log(f'\nBATCH SELESAI: {success} berhasil, {failed} gagal dari {total_jobs} job.')
                self.log(f'Manifest: {manifest.name}')
        except Exception as e:
            self.log(f'FAIL: Fatal error: {e}')
            ended_at=datetime.now().isoformat(timespec='seconds')
            try:
                manifest=self._write_batch_manifest(pages, restos, output_format if 'output_format' in locals() else 'UNKNOWN', page_results, started_at, ended_at)
                manifest_path=str(manifest)
            except Exception:
                manifest_path=None
            missing=[]
            for pg in pages:
                for resto in restos:
                    key=self._result_key(pg, resto)
                    if key not in page_results:
                        page_results[key]={
                            'page': pg, 'resto': resto,
                            'success': False, 'page_error': True,
                            'stage': 'FATAL', 'message': str(e)
                        }
                        missing.append(key)
            self.done_cb({
                'success': sum(1 for v in page_results.values() if v.get('success')),
                'failed': len(page_results)-sum(1 for v in page_results.values() if v.get('success')),
                'manifest': manifest_path,
                'results': page_results,
                'output_format': output_format if 'output_format' in locals() else None,
                'pages': pages,
                'restos': restos
            })
        finally:
            try:
                if context:
                    context.close()
            except Exception as e:
                self.log(f'   WARN: Gagal menutup context: {e}')
            try:
                if browser:
                    browser.close()
            except Exception as e:
                self.log(f'   WARN: Gagal menutup browser: {e}')


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Power BI Screenshot Tool - {APP_VERSION}')
        self.geometry('1180x880')
        self.minsize(980,700)
        self.q=queue.Queue(); self.engine=None; self.thread=None
        self.build(); self.after(100,self.poll)

    def build(self):
        f=ttk.Frame(self,padding=14); f.pack(fill='both',expand=True)
        row=ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row,text='Pages:').grid(row=0,column=0,sticky='w',padx=(0,8))
        self.page=tk.StringVar(value=str(CONFIG.get('page','19,20,21,22')))
        ttk.Entry(row,textvariable=self.page,width=22).grid(row=0,column=1,sticky='w')
        ttk.Label(row,text='Contoh: 19,20,21,22 atau 19-22',foreground='#555').grid(row=1,column=1,sticky='w',pady=(2,0))

        ttk.Label(row,text='Alamat Output:').grid(row=0,column=2,sticky='w',padx=(30,8))
        self.output_var=tk.StringVar(value=str(OUTPUT_DIR))
        ttk.Entry(row,textvariable=self.output_var,width=46).grid(row=0,column=3,sticky='ew')
        ttk.Button(row,text='Ubah...',command=self.change_output).grid(row=0,column=4,sticky='w',padx=(8,0))
        ttk.Label(row,text='Format:').grid(row=0,column=5,sticky='w',padx=(18,8))
        self.format_var=tk.StringVar(value=str(CONFIG.get('output_format','PNG')).upper())
        self.format_combo=ttk.Combobox(row,textvariable=self.format_var,values=('PNG','PDF'),state='readonly',width=8)
        self.format_combo.grid(row=0,column=6,sticky='w')
        row.columnconfigure(3,weight=1)

        ttk.Label(f,text='Daftar Resto (satu per baris):').pack(anchor='w',pady=(14,5))
        self.restos=tk.Text(f,height=10,font=('Consolas',11)); self.restos.pack(fill='x')
        self.restos.insert('1.0',CONFIG.get('restos','4217\nDPKLIM\nMTR\nBSD'))

        # V16: optimization flags panel.
        opt=ttk.LabelFrame(f,text='V16 Optimizations',padding=8)
        opt.pack(fill='x',pady=(8,4))
        self.opt_sequential=tk.BooleanVar(value=bool(CONFIG.get('opt_sequential_page_nav',True)))
        self.opt_smart=tk.BooleanVar(value=bool(CONFIG.get('opt_smart_resto_transition',False)))
        self.opt_reuse=tk.BooleanVar(value=bool(CONFIG.get('opt_reuse_stable_screenshot',True)))
        self.opt_merge=tk.BooleanVar(value=bool(CONFIG.get('opt_merge_final_stability',True)))
        self.opt_light=tk.BooleanVar(value=bool(CONFIG.get('opt_light_recovery',True)))
        self.opt_force=tk.BooleanVar(value=bool(CONFIG.get('opt_force_click_next_page',True)))
        row1=ttk.Frame(opt); row1.pack(fill='x',pady=(0,4))
        ttk.Checkbutton(row1,text='Sequential page nav',variable=self.opt_sequential).pack(side='left',padx=(0,12))
        ttk.Checkbutton(row1,text='Reuse stable screenshot',variable=self.opt_reuse).pack(side='left',padx=(0,12))
        ttk.Checkbutton(row1,text='Merge final stability check',variable=self.opt_merge).pack(side='left')
        row2=ttk.Frame(opt); row2.pack(fill='x')
        ttk.Checkbutton(row2,text='Light recovery (clear, no reload)',variable=self.opt_light).pack(side='left',padx=(0,12))
        ttk.Checkbutton(row2,text='Force-click Next Page fallback',variable=self.opt_force).pack(side='left',padx=(0,12))
        ttk.Checkbutton(row2,text='Smart resto transition (experimental)',variable=self.opt_smart).pack(side='left')

        b=ttk.Frame(f); b.pack(fill='x',pady=10)
        self.start=ttk.Button(b,text='▶ START MULTI-PAGE (V16)',command=self.start_run); self.start.pack(side='left')
        self.stopb=ttk.Button(b,text='■ STOP',command=self.stop_run,state='disabled'); self.stopb.pack(side='left',padx=8)
        ttk.Button(b,text='BUKA OUTPUT',command=lambda: os.startfile(OUTPUT_DIR)).pack(side='left')

        self.prog=tk.DoubleVar(); ttk.Progressbar(f,variable=self.prog,maximum=100).pack(fill='x')
        self.plabel=ttk.Label(f,text='Siap.'); self.plabel.pack(anchor='w',pady=(3,8))
        ttk.Label(f,text='Log:').pack(anchor='w')
        lf=ttk.Frame(f); lf.pack(fill='both',expand=True)
        self.logbox=tk.Text(lf,wrap='word',font=('Consolas',9),state='disabled'); self.logbox.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(lf,command=self.logbox.yview); sb.pack(side='right',fill='y'); self.logbox.configure(yscrollcommand=sb.set)

    def add_log(self,msg): self.q.put(('log',f'{datetime.now().strftime("%H:%M:%S")} {msg}'))
    def progress(self,c,t,label): self.q.put(('progress',c,t,label))
    def done(self,r): self.q.put(('done',r))

    def change_output(self):
        global OUTPUT_DIR
        current=self.output_var.get().strip() or str(OUTPUT_DIR)
        folder=filedialog.askdirectory(title='Pilih folder output', initialdir=current if os.path.isdir(current) else str(APP_DIR))
        if folder:
            self.output_var.set(folder); OUTPUT_DIR=Path(folder).expanduser().resolve(); OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
            CONFIG['output_dir']=str(OUTPUT_DIR)
            try: CONFIG_FILE.write_text(json.dumps(CONFIG,indent=2,ensure_ascii=False),encoding='utf-8')
            except Exception as e: messagebox.showwarning('Output',f'Folder berubah, tetapi config.json gagal disimpan:\n{e}')

    def start_run(self):
        global OUTPUT_DIR
        try: pages=Engine.parse_pages(self.page.get())
        except Exception as e: return messagebox.showerror('Input Page',str(e))
        raw_restos=[x.strip() for x in self.restos.get('1.0','end').splitlines()]
        restos, duplicates=Engine.parse_restos(raw_restos)
        if not restos: return messagebox.showerror('Input','Daftar resto masih kosong.')
        if duplicates:
            messagebox.showwarning('Duplikat Resto',f'Duplikat akan dilewati: {duplicates}')
        out=self.output_var.get().strip() or str(APP_DIR/'output')
        output_format=self.format_var.get().strip().upper()
        if output_format not in ('PNG','PDF'): return messagebox.showerror('Format','Pilih format output PNG atau PDF.')
        # V15: persist optimization flags.
        CONFIG['opt_sequential_page_nav']=bool(self.opt_sequential.get())
        CONFIG['opt_smart_resto_transition']=bool(self.opt_smart.get())
        CONFIG['opt_reuse_stable_screenshot']=bool(self.opt_reuse.get())
        CONFIG['opt_merge_final_stability']=bool(self.opt_merge.get())
        CONFIG['opt_light_recovery']=bool(self.opt_light.get())
        CONFIG['opt_force_click_next_page']=bool(self.opt_force.get())
        try:
            OUTPUT_DIR=Path(out).expanduser().resolve(); OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
            if not OUTPUT_DIR.is_dir(): raise NotADirectoryError(str(OUTPUT_DIR))
            CONFIG['output_dir']=str(OUTPUT_DIR); CONFIG['output_format']=output_format; CONFIG['page']=','.join(map(str,pages)); CONFIG['restos']='\n'.join(restos)
            CONFIG_FILE.write_text(json.dumps(CONFIG,indent=2,ensure_ascii=False),encoding='utf-8')
        except Exception as e:
            return messagebox.showerror('Output',f'Alamat output tidak valid atau config gagal disimpan:\n{e}')
        self.logbox.configure(state='normal'); self.logbox.delete('1.0','end'); self.logbox.configure(state='disabled'); self.prog.set(0)
        self.start.configure(state='disabled'); self.stopb.configure(state='normal')
        self.engine=Engine(self.add_log,self.progress,self.done)
        self.thread=threading.Thread(target=self.engine.run,args=(pages,restos,output_format),daemon=True); self.thread.start()

    def stop_run(self):
        if self.engine: self.engine.stop(); self.add_log('Permintaan stop dikirim...')

    def poll(self):
        try:
            while True:
                typ,*data=self.q.get_nowait()
                if typ=='log':
                    self.logbox.configure(state='normal'); self.logbox.insert('end',data[0]+'\n'); self.logbox.see('end'); self.logbox.configure(state='disabled')
                elif typ=='progress':
                    c,t,label=data; self.prog.set(100*c/t if t else 0); self.plabel.configure(text=f'{c}/{t} — {label}')
                else:
                    r=data[0]; self.start.configure(state='normal'); self.stopb.configure(state='disabled')
                    fmt=r.get('output_format') or self.format_var.get().upper()
                    pages=r.get('pages') or []
                    success=r.get('success',0); failed=r.get('failed',0)
                    manifest=r.get('manifest') or '-'
                    self.plabel.configure(text=f'Selesai: {success} berhasil, {failed} gagal.')
                    messagebox.showinfo('Selesai',f'Page: {", ".join(map(str,pages))}\nBerhasil: {success}\nGagal: {failed}\nFormat: {fmt}\nManifest: {manifest}\nFolder: {self.output_var.get()}')
        except queue.Empty:
            pass
        self.after(100,self.poll)

def run_cli():
    """Headless mode: read config.json, run Engine, log to stdout.

    Invoked by `python app.py --cli`. Designed to be driven as a subprocess
    by the parent UI (ui_app.py tab "Screen Shot Power BI"). Reads all
    parameters from config.json (same file the Tk GUI reads/writes), runs
    the Engine end-to-end, and prints machine-readable markers to stdout:

      * every line passed to the log callback is printed as-is (UTF-8)
      * 'PROGRESS: <cur>/<total> <label>'  — per-job progress
      * 'DONE: success=<N> failed=<N>'     — end of batch
      * 'ERROR: <message>'                 — fatal exception (instead of
                                              crashing the subprocess)

    The parent UI parses these markers (see _ss_worker in ui_app.py) to
    update the progress bar, status label, and log widget.
    """
    pages = Engine.parse_pages(CONFIG.get('page', ''))
    restos_raw = (CONFIG.get('restos', '') or '').splitlines()
    restos, _dups = Engine.parse_restos(restos_raw)
    output_format = str(CONFIG.get('output_format', 'PNG')).upper().strip()

    def log_cb(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{ts} {msg}", flush=True)

    def progress_cb(cur, total, label):
        print(f"PROGRESS: {cur}/{total} {label}", flush=True)

    def done_cb(result):
        success = result.get('success', 0)
        failed = result.get('failed', 0)
        print(f"DONE: success={success} failed={failed}", flush=True)

    engine = Engine(log_cb, progress_cb, done_cb)
    try:
        engine.run(pages, restos, output_format)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)


if __name__ == '__main__':
    if '--cli' in sys.argv:
        run_cli()
    else:
        App().mainloop()
