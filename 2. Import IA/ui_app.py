"""
ui_app.py — tampilan aplikasi Import IA (v5.2, pasangan accurate_bot.py v4.7).
Tab: Otomasi | Database COA & Keterangan | Download Draft IA | Download SJ GIS | Screen Shot Power BI.
v5.2: Professional log formatting across all 3 tool scripts (unduh_xls_loop.py,
  filter_pembuat_data.py, download_sj_gis.py, app.py) + UI cleanup. Removed
  "Cek Chrome" button from SJ GIS tab (auto-check 3s after launch + auto-check
  on Mulai Download is sufficient). Removed "Deteksi Ulang" button from SJ GIS
  tab (auto-detect on startup sufficient). Updated SJ GIS worker log parser to
  detect new ✅ Selesai success marker (in addition to legacy [DONE]).

v5.1: Chrome anti-throttle flags di _sj_launch_chrome
  (--disable-background-timer-throttling,
   --disable-backgrounding-occluded-windows,
   --disable-renderer-backgrounding) — user boleh switch ke app lain selama
  tool berjalan tanpa Chrome mem-throttle JS timers / rendering. README di-
  update dengan guidance "stay on Chrome" + anti-throttle flags.

v5.0: MAJOR REFACTOR — ganti inline log Text widgets (dl_text/sj_text/ss_text)
yang 0px/invisible (lines di-insert via _drain_queue tapi widget tinggi 0px,
tak kelihatan — root cause: grid layout gives 0px to log row on sebagian
DPI/resolution combo) dengan popup log windows berbasis SimpleLogPopup
class (tk.Toplevel — pola proven-VISIBLE dari Otomasi tab's ProcessLogWindow).

Changes:
  1. SimpleLogPopup class — popup dgn Text + scrollbar + Bersihkan btn, hidden
     by default, shown via _show_*_logwin atau auto-open di _start_*.
  2. 3 popup instances (dl_logwin, sj_logwin, ss_logwin) via _ensure pattern.
  3. Card 3 (inline log) DIHAPUS dari DL, SJ, SS tabs (was 0px invisible).
  4. 'Log Proses' button di-Card 2 tiap tab (open popup).
  5. _drain_queue route dl_log/sj_log/ss_log -> popup.append() (bukan inline
     Text insert); dl_done/sj_done/ss_done -> popup.append('Selesai').
  6. Auto-open popup + clear saat klik 'Mulai' (_start_download/_start_sj_download/_start_ss).
  7. _dl_clear/_sj_clear/_ss_clear -> popup.clear(); _ss_test_log -> popup.append.
  8. _dl_text_wheel/_sj_log_wheel/_ss_text_wheel DIHAPUS (no inline Text utk
     scroll). _sj_text_wheel DIPERTAHANKAN (scroll sj_kodes_text input box,
     BUKAN log — penamaan misleading tapi bindingnya ke input box).
  9. Card 4 'Kode Gagal' (SJ tab, sj_failed_text) TIDAK diubah — terpisah
     dari log, hanya display kode yg gagal.
 10. Fix folder detection: _detect_dl_folder sekarang cari folder dgn SUBSTRING
     match 'Download Draft IA' (akomodasi prefix '1. ' dll) — sebelumnya
     exact-name match terhadap DL_FOLDER_NAME='Download Draft IA' GAGAL karena
     folder sebenarnya bernama '1. Download Draft IA'.
 11. _on_close destroy popup windows (dl_logwin, sj_logwin, ss_logwin).
 12. Buka Folder Unduhan (SJ) + Buka Output (SS) dipindah ke Card 2 button row
     (sebelumnya di Card 3 log button row yg dihapus).

Root cause of inline Text 0px: grid layout gives 0px to log row on some
DPI/resolution combos. v4.17-v4.19 tried pack, pack_propagate, grid minsize
— none worked reliably. Popup window (tk.Toplevel) is ALWAYS visible
(independent of tab grid layout) — same pattern as the proven-working
ProcessLogWindow (Otomasi tab, sejak v3.x).
v4.19: FIX log Text widgets (sj_text, ss_text, dl_text) yang 0px/invisible.
Root cause: grid rowconfigure(N, weight=1) TANPA minsize memungkinkan row
di-shrink ke 0px bila parent layout tidak mengalokasikan ruang cukup. Lines
tetap di-insert via _drain_queue tapi Text widget tinggi 0px -> invisible.
Fix: tambah minsize=300 ke log CARD rowconfigure(1) + minsize=280 ke log WRAP
rowconfigure(0) untuk ketiga tab (SJ GIS + SS + DL). Tambahan minsize=300 ke
parent view rowconfigure(1) (sjview/ssview/dlview) sebagai defensive layer.
minsize = HARD floor — grid tidak bisa shrink row di bawah 300px. Text widget
sticky=nsew akan mengisi 300px -> visible + scrollable. Tidak mengubah Text
widget creation atau _drain_queue.
v4.18: REVERT SS tab Card 3 (Log Screenshot) ke grid layout. v4.17 pakai
pack_propagate(False) + pack() + height=15 untuk ss_text, tapi ini bikin
ss_log_wrap Frame stuck di 0px (pack_propagate mencegah child men-size parent,
grid luar tidak mengalokasikan ruang cukup). Text widget menerima lines via
_drain_queue tapi invisible. Fix: revert ke grid layout EXACTLY match pattern
WORKING SJ GIS tab sj_text — columnconfigure(0, weight=1) +
rowconfigure(0, weight=1) + sticky=nsew, NO pack_propagate, NO explicit
height. Keep: Test Log button, wheel scroll (MouseWheel + Button-4/5),
ss_log_card.rowconfigure(1, weight=1). Sj_text TIDAK diubah (working).
v4.17: redesign Card 3 (Log Screenshot) di tab Screen Shot — Text widget
sebelumnya pakai grid tanpa explicit height, jadi pada sebagian DPI / theme
combo ukurannya jadi mendekati 0px (lines tetap diinsert via _drain_queue,
tapi tak terlihat). Sekarang: pack-based layout + pack_propagate(False) +
height=15 explicit + scrollbar pack fill-y. Tambahan tombol "Test Log" di
baris tombol Card 3 (sebelah Bersihkan + Buka Output) — push 8 dummy lines
via jalur yang sama (_ss_log_line -> ui_queue -> _drain_queue) buat
verifikasi widget. Kalau Test Log keliatan = widget OK, masalah ada di
_ss_worker/subprocess; kalau Test Log kosong = widget/drain_queue bermasalah.
"Buka Output" dipindah dari ss_ctl_card ke baris tombol Card 3 (sebelah
Test Log + Bersihkan). Sj_text (tab Download SJ GIS) TIDAK diubah — layout
mirip tapi sudah ada wheel scroll dan user tidak report issue, jangan
break working code. .bat encoding fix: em dash (U+2014) di MULAI.bat +
SETUP.bat diganti hyphen-minus biasa (CMD gak parse Unicode em dash ->
"'—' is not recognized" errors). UI Python tetap Unicode (Tkinter handle
em dash + emoji OK).
v4.14: tab kelima "Screen Shot Power BI" — menjalankan app.py (folder
'4. Screen Shot Power BI') sebagai subprocess `app.py --cli`. 3 cards:
(1) Konfigurasi: Power BI URL + Pages + Output folder + Format (PNG/PDF);
(2) Resto & Opsi: Text multi-utk daftar resto + 5 V16 checkboxes (sequential
nav / reuse screenshot / merge stability / light recovery /
force-click Next Page) + tombol Mulai / Hentikan / Buka Output + progressbar
+ status label; (3) Log terminal-style + scrollbar + Bersihkan. UI baca +
tulis config.json di folder 4 (sumber kebenaran). _ss_worker menjalankan
subprocess, parse stdout line-by-line; marker 'PROGRESS: cur/total label'
-> progress bar, 'DONE: success=N failed=N' -> status, sisanya -> log
widget. Auto-detect path app.py via _ss_detect_script (relatif ke file ini).
Playwright + Chromium wajib terpasang (dipasang otomatis oleh launch.bat di
folder 4, atau oleh ensure_playwright() di app.py saat runtime).
v4.13: Card 4 "Kode Gagal" di tab Download SJ GIS (row 2, di bawah Log card,
compact fixed-height). Pasangan download_sj_gis.py v8.13. Worker parse
marker 'SJ_RESULT_FAIL: <kodes>' dari stdout subprocess, push ke ui_queue
tag 'sj_failed'. _drain_queue handle 'sj_failed' -> _sj_set_failed_kodes
populate Text widget (red if ada gagal, gray placeholder 'Tidak ada kode
gagal' jika 0). Title label update count: '4. Kode Gagal (N)'. 3 tombol:
Copy (clipboard), Pindahkan ke Input (replace input box utk retry), Bersihkan.
_start_sj_download clear failed list on new run.
v4.12: tombol "Buka Chrome 9222" di Card 2 (Kontrol) tab Download SJ GIS —
meluncurkan chrome.exe dengan --remote-debugging-port=9222 +
--user-data-dir=C:\\ChromeDebugProfile lalu buka https://accurate.id.
Auto-finds chrome.exe (Program Files / x86 / LOCALAPPDATA / PATH). Setelah
launch: tunggu 3s + auto re-check port 9222 via _sj_check_chrome(). Non-blocking
(subprocess.Popen). Tidak simpan password — user login manual sekali, sesi
persist di C:\\ChromeDebugProfile.
v4.11: tab keempat "Download SJ GIS" — menjalankan download_sj_gis.py (v8.12,
folder 3. Download SJ GIS) sebagai subprocess. Kode SJ dikirim via env var
SJ_GIS_KODES (string dipisah koma). Stdout direplay ke widget log terminal
style + progress bar (parse [X/Y] pattern dari output say()).
v4.10: pipeline Download = [FILTER] lalu [UNDUH]; nama cabang tersimpan di ui_settings.json.
"""
import os
import re
import sys
import json
import queue
import threading
import time
import subprocess
from datetime import datetime, date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# v4.15: merged main.py — ui_app.py sekarang entry point langsung.
# import accurate_bot + version check di-wrap try/except (preserve nice error dialog
# dari main.py lama). Kalau import/version gagal -> messagebox dialog (bukan traceback).
try:
    import accurate_bot as bot
    REQUIRED_BOT_VERSION = "4.8"
    if getattr(bot, "BOT_VERSION", None) != REQUIRED_BOT_VERSION:
        raise RuntimeError(
            "Versi file TIDAK SEPASANG.\n\n"
            f"ui_app.py ini butuh accurate_bot.py versi {REQUIRED_BOT_VERSION},\n"
            f"tapi terdeteksi versi: {getattr(bot, 'BOT_VERSION', 'LAMA')}.\n\n"
            "Salin ulang kedua file dari paket yang sama, lalu hapus copy lama."
        )
except Exception as e:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("Import IA — Error Startup", str(e))
    raise SystemExit(1)

APP_TITLE = "Import IA"
DL_FOLDER_NAME = "Download Draft IA"
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
DEFAULT_BRANCHES = "RESTO.PWKTAM, RESTO.KWGGAL"
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_settings.json")

_FONT = "Segoe UI"
_MONO = "Consolas"
F_APP_TITLE = (_FONT, 16, "bold")
F_CARD      = (_FONT, 11, "bold")
F_BODY      = (_FONT, 10)
F_HINT      = (_FONT, 9)
F_LOG       = (_MONO, 10)
F_POP_FILE  = (_FONT, 11, "bold")

C_BG      = "#eef2f7"
C_CARD    = "#ffffff"
C_HEADER  = "#172033"
C_FOOTER  = "#e2e8f0"
C_INFO_BG = "#f8fafc"
C_TERM_BG = "#0b1220"


# ============================================================
# PENGATURAN TERSIMPAN
# ============================================================
def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _wheel_steps(e):
    if getattr(e, "delta", 0):
        return -1 * int(e.delta / 120)
    if getattr(e, "num", 0) == 4:
        return -1
    if getattr(e, "num", 0) == 5:
        return 1
    return 0


class ScrollableBody(ttk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="TFrame")
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._inner_conf)
        self.canvas.bind("<Configure>", self._canvas_conf)
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", self._on_wheel)
        self.bind_all("<Button-5>", self._on_wheel)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _inner_conf(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _canvas_conf(self, e):
        self.canvas.itemconfig(self._win, width=e.width)

    def _ok_target(self, w):
        cur = w
        while cur is not None:
            if not hasattr(cur, "winfo_class"):
                return False
            cls = cur.winfo_class()
            if cls in ("Text", "Listbox", "Treeview", "Entry", "Combobox", "TEntry", "TCombobox"):
                return False
            if cur is self.inner or cur is self.canvas or cur is self:
                return True
            cur = getattr(cur, "master", None)
        return False

    def _on_wheel(self, e):
        w = getattr(e, "widget", None)
        if w is None or not hasattr(w, "winfo_class"):
            return
        if not self._ok_target(w):
            return
        steps = _wheel_steps(e)
        if not steps:
            return
        if self.canvas.yview() == (0.0, 1.0):
            return
        self.canvas.yview_scroll(steps, "units")

    def _on_destroy(self, e):
        if e.widget is self:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    self.unbind_all(seq)
                except Exception:
                    pass


class ProcessLogWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(f"Log Proses — {APP_TITLE}")
        self.geometry("820x500")
        self.minsize(560, 320)
        self.configure(bg=C_TERM_BG)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        head = tk.Frame(self, bg=C_TERM_BG)
        head.pack(fill="x", padx=14, pady=(12, 6))
        self.file_lbl = tk.Label(head, text="Menunggu proses...", bg=C_TERM_BG,
                                 fg="#38bdf8", font=F_POP_FILE, anchor="w")
        self.file_lbl.pack(fill="x")
        self.step_lbl = tk.Label(head, text="", bg=C_TERM_BG, fg="#e2e8f0",
                                 font=F_BODY, anchor="w", justify="left", wraplength=780)
        self.step_lbl.pack(fill="x", pady=(2, 6))

        prog_wrap = tk.Frame(self, bg=C_TERM_BG)
        prog_wrap.pack(fill="x", padx=14, pady=(0, 8))
        self.progress = ttk.Progressbar(prog_wrap, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.counter_lbl = tk.Label(prog_wrap, text="0 / 0", bg=C_TERM_BG, fg="#94a3b8", font=F_BODY)
        self.counter_lbl.pack(side="left", padx=(10, 0))

        body = tk.Frame(self, bg=C_TERM_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.text = tk.Text(body, bg=C_TERM_BG, fg="#dbeafe", insertbackground="white",
                            relief="flat", font=F_LOG, wrap="word", state="disabled")
        self.text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scroll.set)
        self.text.bind("<MouseWheel>", self._text_wheel)
        self.text.bind("<Button-4>", self._text_wheel)
        self.text.bind("<Button-5>", self._text_wheel)
        for tag, color in (("SUCCESS", "#4ade80"), ("ERROR", "#f87171"),
                           ("WARN", "#fbbf24"), ("FILE", "#38bdf8"), ("INFO", "#dbeafe")):
            self.text.tag_config(tag, foreground=color)

        foot = tk.Frame(self, bg=C_TERM_BG)
        foot.pack(fill="x", padx=14, pady=(0, 12))
        self.topmost_var = tk.BooleanVar(value=True)
        tk.Checkbutton(foot, text="Selalu di atas", variable=self.topmost_var,
                       bg=C_TERM_BG, fg="#94a3b8", selectcolor="#1e293b",
                       activebackground=C_TERM_BG, activeforeground="#e2e8f0",
                       font=F_BODY, command=self._apply_topmost).pack(side="left")
        ttk.Button(foot, text="Bersihkan", command=self.clear).pack(side="right", padx=(8, 0))
        ttk.Button(foot, text="Tutup", command=self.hide).pack(side="right")
        self._apply_topmost()

    def _text_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.text.yview_scroll(steps, "units")

    def _apply_topmost(self):
        try:
            self.attributes("-topmost", bool(self.topmost_var.get()))
        except Exception:
            pass

    def show(self):
        self.deiconify()
        self.lift()
        self._apply_topmost()

    def hide(self):
        self.withdraw()

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def set_file(self, text):
        self.file_lbl.configure(text=text)

    def set_step(self, text, color="#e2e8f0"):
        self.step_lbl.configure(text=text, fg=color)

    def set_progress(self, done, total):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = done
        self.counter_lbl.configure(text=f"{done} / {total}")

    def append(self, line, kind="INFO"):
        self.text.configure(state="normal")
        self.text.insert("end", line, kind)
        self.text.see("end")
        self.text.configure(state="disabled")

    def finish(self, success, fail, skipped):
        self.set_step(f"SELESAI — berhasil {success}, gagal {fail}, dilewati {skipped}",
                      "#4ade80" if fail == 0 else "#fbbf24")
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass
        self.lift()


class SimpleLogPopup(tk.Toplevel):
    """Popup log window (proven visible — unlike inline Text which gets 0px).
    One instance per tab (DL, SJ, SS). Hidden by default, shown via button or
    auto-open. Reusable (withdraw on close, deiconify on show — NOT destroyed).

    v5.0: replaces the broken inline log Text widgets (dl_text/sj_text/ss_text)
    which had 0px height on some DPI/resolution combos. Pattern is identical to
    the proven-working ProcessLogWindow (Otomasi tab) — tk.Toplevel is ALWAYS
    visible, independent of the parent tab's grid layout.
    """
    def __init__(self, master, title="Log"):
        super().__init__(master)
        self.title(title)
        self.geometry("900x550")
        self.minsize(600, 300)
        # Text + scrollbar
        wrap = tk.Frame(self, bg=C_TERM_BG)
        wrap.pack(fill="both", expand=True, padx=6, pady=6)
        self.text = tk.Text(wrap, bg=C_TERM_BG, fg="#dbeafe", insertbackground="white",
                            relief="flat", font=F_LOG, wrap="word", state="disabled")
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)
        # Wheel scroll (Linux Button-4/5 = up/down; Windows/Mac = MouseWheel)
        self.text.bind("<MouseWheel>", lambda e: self.text.yview_scroll(_wheel_steps(e), "units"))
        self.text.bind("<Button-4>", lambda e: self.text.yview_scroll(_wheel_steps(e), "units"))
        self.text.bind("<Button-5>", lambda e: self.text.yview_scroll(_wheel_steps(e), "units"))
        # Clear button
        btn_frame = tk.Frame(self, bg=C_FOOTER)
        btn_frame.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btn_frame, text="Bersihkan", command=self.clear).pack(side="right")
        # Hidden by default (call .show() to deiconify)
        self.withdraw()
        self.protocol("WM_DELETE_WINDOW", self.hide)

    def append(self, line):
        """Thread-safe: called from _drain_queue (main thread) or directly from
        main-thread methods. Append line + auto-scroll to end."""
        try:
            self.text.configure(state="normal")
            self.text.insert("end", str(line) + "\n")
            self.text.see("end")
            self.text.configure(state="disabled")
        except Exception:
            pass

    def clear(self):
        try:
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.configure(state="disabled")
        except Exception:
            pass

    def show(self):
        """Show + raise popup (topmost briefly to lift above main window)."""
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def hide(self):
        """Withdraw (hide) — don't destroy (reusable via .show())."""
        try:
            self.withdraw()
        except Exception:
            pass


class AutoImportApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1320x860")
        self.minsize(1000, 660)
        self.configure(bg=C_BG)

        self.db_folder = ""
        self.db_map = {}
        self.db_meta = {}
        self.root_folder = ""
        self.folders, self.files, self.plan = [], [], []
        self.stop_requested = threading.Event()
        self.ui_queue = queue.Queue()
        self.running, self.worker_thread = False, None
        self.run_date = ""
        self.run_mode = bot.MODE_DRAFT
        self.logwin = None
        self.log_buffer = []

        self.dl_folder = ""
        self.unduh_path = ""
        self.filter_path = ""
        self.dl_running = False
        self.dl_stop = threading.Event()
        self.dl_proc = None
        self.dl_branches = ""

        # ---- Download SJ GIS (tab keempat, v4.11) ----
        self.sj_running = False
        self.sj_stop = threading.Event()
        self.sj_proc = None
        self.sj_kodes = []
        self.sj_script_path = None
        # v4.13: list kode yg GAGAL di run terakhir (diparse dari marker
        # 'SJ_RESULT_FAIL:' line by _sj_worker). Di-populate ke Card 4
        # 'Kode Gagal' via _sj_set_failed_kodes. Reset tiap _start_sj_download.
        self.sj_failed_kodes = []

        # ---- Screen Shot Power BI (tab kelima, v4.14) ----
        # app.py di folder '4. Screen Shot Power BI' (berdampingan dgn folder
        # '2. Import IA' ini). Dijalankan sebagai subprocess `app.py --cli`.
        # Lihat _ss_worker + _ss_detect_script + _ss_load_config + _ss_save_config.
        self.ss_running = False
        self.ss_stop = threading.Event()
        self.ss_proc = None
        self.ss_script_path = None

        # v5.0: popup log windows — one per tab (DL, SJ, SS). Lazy-init via
        # _ensure_*_logwin (mirrors _ensure_logwin utk Otomasi tab). Hidden by
        # default, shown via 'Log Proses' button or auto-opened when 'Mulai'
        # clicked (clear+show in _start_download/_start_sj_download/_start_ss).
        # Replaces broken inline dl_text/sj_text/ss_text (0px invisible).
        self.dl_logwin = None
        self.sj_logwin = None
        self.ss_logwin = None

        self._setup_style()
        self._build_ui()
        self._apply_settings()
        self._load_db(silent=True)
        self._detect_dl_folder()
        self.after(100, self._drain_queue)
        self.after(500, self._refresh_summary_loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================= STYLE =================
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=C_BG)
        style.configure("Card.TFrame", background=C_CARD)
        style.configure("TLabel", background=C_CARD, foreground="#1f2937", font=F_BODY)
        style.configure("TButton", font=(_FONT, 10, "bold"), padding=(14, 9))
        style.configure("Success.TButton", background="#16a34a", foreground="#ffffff")
        style.map("Success.TButton", background=[("active", "#15803d"), ("disabled", "#86efac")])
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93c5fd")])
        style.configure("Warn.TButton", background="#d97706", foreground="#ffffff")
        style.map("Warn.TButton", background=[("active", "#b45309"), ("disabled", "#fcd34d")])
        style.configure("Danger.TButton", background="#dc2626", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b91c1c"), ("disabled", "#fca5a5")])
        style.configure("Treeview", font=(_FONT, 9), rowheight=26)
        style.configure("Treeview.Heading", font=(_FONT, 9, "bold"))
        style.configure("TCombobox", font=F_BODY, padding=(6, 6))
        style.configure("TEntry", font=F_BODY)
        style.configure("TNotebook.Tab", font=(_FONT, 10, "bold"), padding=(14, 6))

    # ================= BUILD UI =================
    def _build_ui(self):
        header = tk.Frame(self, bg=C_HEADER)
        header.pack(fill="x")
        tk.Label(header, text=APP_TITLE, bg=C_HEADER, fg="white",
                 font=F_APP_TITLE).pack(anchor="w", padx=24, pady=(16, 14))

        footer = tk.Frame(self, bg=C_FOOTER)
        footer.pack(fill="x", side="bottom")
        self.stop_btn = ttk.Button(footer, text="■  HENTIKAN", style="Danger.TButton",
                                   command=self.stop_automation, state="disabled")
        self.stop_btn.pack(side="left", padx=(20, 8), pady=14)
        ttk.Button(footer, text="Log Proses", command=self._show_logwin).pack(side="left", padx=8, pady=14)
        ttk.Button(footer, text="Refresh File", command=self.refresh_files).pack(side="right", padx=(8, 20), pady=14)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        tab_auto = ttk.Frame(self.notebook)
        tab_db = ttk.Frame(self.notebook)
        tab_dl = ttk.Frame(self.notebook)
        tab_sj = ttk.Frame(self.notebook)
        tab_ss = ttk.Frame(self.notebook)
        self.notebook.add(tab_auto, text="  Otomasi  ")
        self.notebook.add(tab_db, text="  Database COA & Keterangan  ")
        self.notebook.add(tab_dl, text="  Download Draft IA  ")
        self.notebook.add(tab_sj, text="  Download SJ GIS  ")
        self.notebook.add(tab_ss, text="  Screen Shot Power BI  ")

        # ================= TAB OTOMASI =================
        self.scroller = ScrollableBody(tab_auto)
        self.scroller.pack(fill="both", expand=True)
        body = self.scroller.inner
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        db_card = self._card(body, "1. Database COA & Keterangan")
        db_card.grid(row=0, column=0, sticky="nsew", padx=(18, 6), pady=(16, 8))
        db_card.columnconfigure(0, weight=1)
        self.db_info = tk.Label(db_card, text="Memuat database...", justify="left", anchor="w",
                                bg=C_INFO_BG, fg="#475569", padx=12, pady=8, font=F_BODY)
        self.db_info.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 6))
        ttk.Button(db_card, text="Muat Ulang", command=self._reload_db).grid(row=1, column=1, padx=(6, 14), pady=(4, 6))

        folder_card = self._card(body, "2. Folder Induk")
        folder_card.grid(row=0, column=1, sticky="nsew", padx=(6, 18), pady=(16, 8))
        folder_card.columnconfigure(1, weight=1)
        self.folder_var = tk.StringVar()
        self._path_row(folder_card, 1, "Folder", self.folder_var, self.pick_folder)
        self.folder_summary = tk.Label(folder_card, text="Belum ada folder dipilih.", justify="left", anchor="w",
                                       bg=C_INFO_BG, fg="#475569", padx=12, pady=8, font=F_BODY)
        self.folder_summary.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(4, 12))

        date_card = self._card(body, "3. Tanggal Transaksi")
        date_card.grid(row=1, column=0, sticky="nsew", padx=(18, 6), pady=(0, 8))
        date_row = tk.Frame(date_card, bg=C_CARD)
        date_row.grid(row=1, column=0, sticky="w", padx=14, pady=8)
        today = date.today()
        tk.Label(date_row, text="Tanggal", bg=C_CARD, fg="#64748b", font=F_BODY).pack(side="left", padx=(0, 6))
        self.date_day = ttk.Combobox(date_row, values=[f"{i:02d}" for i in range(1, 32)], width=4, state="readonly")
        self.date_day.pack(side="left", padx=(0, 12))
        self.date_day.set(f"{today.day:02d}")
        tk.Label(date_row, text="Bulan", bg=C_CARD, fg="#64748b", font=F_BODY).pack(side="left", padx=(0, 6))
        self.date_month = ttk.Combobox(date_row, values=[f"{i:02d}" for i in range(1, 13)], width=4, state="readonly")
        self.date_month.pack(side="left", padx=(0, 12))
        self.date_month.set(f"{today.month:02d}")
        tk.Label(date_row, text="Tahun", bg=C_CARD, fg="#64748b", font=F_BODY).pack(side="left", padx=(0, 6))
        self.date_year = ttk.Combobox(date_row, values=[str(y) for y in range(today.year - 5, today.year + 6)], width=6, state="readonly")
        self.date_year.pack(side="left", padx=(0, 14))
        self.date_year.set(str(today.year))
        ttk.Button(date_row, text="Hari Ini", command=self.set_today).pack(side="left")

        sum_card = self._card(body, "4. Ringkasan")
        sum_card.grid(row=1, column=1, sticky="nsew", padx=(6, 18), pady=(0, 8))
        sum_card.columnconfigure(0, weight=1)
        self.chrome_lbl = tk.Label(sum_card, text="● Memeriksa Chrome...", bg=C_CARD, fg="#f59e0b",
                                   font=(_FONT, 10, "bold"), anchor="w")
        self.chrome_lbl.grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 4))
        self.summary_lbl = tk.Label(sum_card, text="Memuat ringkasan...", justify="left", anchor="w",
                                    bg=C_INFO_BG, fg="#334155", padx=12, pady=8, font=F_BODY)
        self.summary_lbl.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

        mode_card = self._card(body, "5. Mode Penyimpanan")
        mode_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 8))
        mode_card.columnconfigure(0, weight=1)

        # Skip keywords field (user-editable exclusion list)
        skip_row = tk.Frame(mode_card, bg=C_CARD)
        skip_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        tk.Label(skip_row, text="Kata Pengecualian:", bg=C_CARD, fg="#64748b", font=F_BODY).pack(side="left", padx=(0, 6))
        self.skip_keywords_var = tk.StringVar(value="Raw Material, Deviasi")
        skip_entry = ttk.Entry(skip_row, textvariable=self.skip_keywords_var, width=45)
        skip_entry.pack(side="left", padx=(0, 6))
        skip_entry.bind("<Return>", lambda e: self._rebuild_plan())
        skip_entry.bind("<FocusOut>", lambda e: self._rebuild_plan())
        tk.Label(skip_row, text="(file yang mengandung kata ini akan dilewati — pisahkan koma)", bg=C_CARD, fg="#94a3b8", font=(_FONT, 8)).pack(side="left")

        btn_row = tk.Frame(mode_card, bg=C_CARD)
        btn_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 10))
        self.start_approve_btn = ttk.Button(btn_row, text="▶  Simpan Approve", style="Success.TButton",
                                            command=lambda: self.start_automation(bot.MODE_APPROVE))
        self.start_approve_btn.pack(side="left", padx=(0, 8))
        self.start_draft_btn = ttk.Button(btn_row, text="▶  Simpan Draft", style="Primary.TButton",
                                          command=lambda: self.start_automation(bot.MODE_DRAFT))
        self.start_draft_btn.pack(side="left", padx=(0, 8))
        self.start_import_btn = ttk.Button(btn_row, text="▶  Hanya Import", style="Warn.TButton",
                                           command=lambda: self.start_automation(bot.MODE_IMPORT))
        self.start_import_btn.pack(side="left")
        self.start_buttons = [self.start_approve_btn, self.start_draft_btn, self.start_import_btn]

        files_card = self._card(body, "6. Preview Mapping")
        files_card.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 18))
        files_card.columnconfigure(0, weight=1)
        files_card.rowconfigure(2, weight=1)
        self.match_lbl = tk.Label(files_card, text="Belum ada data.",
                                  bg=C_INFO_BG, fg="#475569", padx=12, pady=6,
                                  font=(_FONT, 10, "bold"), anchor="w", justify="left")
        self.match_lbl.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 6))
        tree_wrap = ttk.Frame(files_card)
        tree_wrap.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_wrap, columns=("no", "folder", "file", "cabang", "coa", "ket", "status"),
                                 show="headings", height=8)
        self.tree.heading("no", text="#")
        self.tree.heading("folder", text="Folder")
        self.tree.heading("file", text="File Excel")
        self.tree.heading("cabang", text="Cabang")
        self.tree.heading("coa", text="COA")
        self.tree.heading("ket", text="Keterangan / Alasan")
        self.tree.heading("status", text="Status")
        self.tree.column("no", width=40, anchor="center", stretch=False)
        self.tree.column("folder", width=130)
        self.tree.column("file", width=250)
        self.tree.column("cabang", width=70, anchor="center")
        self.tree.column("coa", width=90, anchor="center")
        self.tree.column("ket", width=420)
        self.tree.column("status", width=90, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<MouseWheel>", self._tree_wheel)
        self.tree.bind("<Button-4>", self._tree_wheel)
        self.tree.bind("<Button-5>", self._tree_wheel)
        self.tree.tag_configure("OK", foreground="#15803d")
        self.tree.tag_configure("DILEWATI", foreground="#9ca3af")
        self.tree.tag_configure("TIDAK COCOK", foreground="#dc2626")
        self.tree.tag_configure("MENUNGGU DB", foreground="#b45309")

        # ================= TAB DATABASE =================
        dbview = ttk.Frame(tab_db, style="TFrame")
        dbview.pack(fill="both", expand=True, padx=18, pady=16)
        dbview.columnconfigure(0, weight=1)
        dbview.rowconfigure(1, weight=1)

        top = tk.Frame(dbview, bg=C_BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)
        self.db_summary_lbl = tk.Label(top, text="Memuat...", bg=C_INFO_BG, fg="#334155",
                                       padx=12, pady=8, font=(_FONT, 10, "bold"), anchor="w", justify="left")
        self.db_summary_lbl.pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Muat Ulang", command=self._reload_db).pack(side="right", padx=(8, 0))

        db_tree_wrap = ttk.Frame(dbview, style="TFrame")
        db_tree_wrap.grid(row=1, column=0, sticky="nsew")
        db_tree_wrap.columnconfigure(0, weight=1)
        db_tree_wrap.rowconfigure(0, weight=1)
        self.db_tree = ttk.Treeview(db_tree_wrap, columns=("sumber", "cabang", "coa", "ket"),
                                    show="headings", height=18)
        self.db_tree.heading("sumber", text="Sumber (File | Sheet)")
        self.db_tree.heading("cabang", text="Cabang")
        self.db_tree.heading("coa", text="COA")
        self.db_tree.heading("ket", text="Keterangan")
        self.db_tree.column("sumber", width=260)
        self.db_tree.column("cabang", width=90, anchor="center")
        self.db_tree.column("coa", width=110, anchor="center")
        self.db_tree.column("ket", width=620)
        self.db_tree.grid(row=0, column=0, sticky="nsew")
        db_sb = ttk.Scrollbar(db_tree_wrap, orient="vertical", command=self.db_tree.yview)
        db_sb.grid(row=0, column=1, sticky="ns")
        self.db_tree.configure(yscrollcommand=db_sb.set)
        self.db_tree.bind("<MouseWheel>", self._db_tree_wheel)
        self.db_tree.bind("<Button-4>", self._db_tree_wheel)
        self.db_tree.bind("<Button-5>", self._db_tree_wheel)

        # ================= TAB DOWNLOAD DRAFT IA =================
        dlview = ttk.Frame(tab_dl, style="TFrame")
        dlview.pack(fill="both", expand=True, padx=18, pady=16)
        dlview.columnconfigure(0, weight=1)
        dlview.columnconfigure(1, weight=1)
        # v5.0: row 1 (Card 3 log) removed — popup log window replaces inline
        # Text. No rowconfigure(1, weight=1, minsize=300) needed anymore.

        src_card = self._card(dlview, "1. Sumber & Lokasi")
        src_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        src_card.columnconfigure(0, weight=1)
        self.dl_folder_lbl = tk.Label(src_card, text="Folder : -", justify="left", anchor="w",
                                      bg=C_INFO_BG, fg="#475569", padx=12, pady=8, font=F_BODY)
        self.dl_folder_lbl.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 6))
        src_btns = tk.Frame(src_card, bg=C_CARD)
        src_btns.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        ttk.Button(src_btns, text="Deteksi Ulang", command=self._detect_dl_folder).pack(side="left", padx=(0, 8))
        ttk.Button(src_btns, text="Buka Folder Unduhan", command=self._open_download_dir).pack(side="left")

        ctl_card = self._card(dlview, "2. Kontrol & Filter")
        ctl_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        ctl_card.columnconfigure(0, weight=1)

        br_row = tk.Frame(ctl_card, bg=C_CARD)
        br_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 4))
        br_row.columnconfigure(1, weight=1)
        tk.Label(br_row, text="Nama Cabang / Pembuat Data", bg=C_CARD, fg="#64748b",
                 font=F_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.dl_branches_var = tk.StringVar(value=DEFAULT_BRANCHES)
        ttk.Entry(br_row, textvariable=self.dl_branches_var).grid(row=0, column=1, sticky="ew")
        tk.Label(ctl_card, text="Pisahkan dengan koma. Nilai tersimpan otomatis saat Mulai / tutup aplikasi.",
                 bg=C_CARD, fg="#94a3b8", font=F_HINT, anchor="w").grid(row=2, column=0, sticky="w", padx=14)

        self.dl_skip_filter_var = tk.BooleanVar(value=False)
        self.dl_skip_cb = ttk.Checkbutton(ctl_card, text="Lewati tahap filter (list sudah difilter manual)",
                                          variable=self.dl_skip_filter_var)
        self.dl_skip_cb.grid(row=3, column=0, sticky="w", padx=14, pady=(4, 4))

        dl_btns = tk.Frame(ctl_card, bg=C_CARD)
        dl_btns.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.dl_start_btn = ttk.Button(dl_btns, text="▶  Mulai Unduh XLS", style="Success.TButton",
                                       command=self._start_download)
        self.dl_start_btn.pack(side="left", padx=(0, 8))
        self.dl_stop_btn = ttk.Button(dl_btns, text="■  Hentikan", style="Danger.TButton",
                                      command=self._stop_download, state="disabled")
        self.dl_stop_btn.pack(side="left", padx=(0, 8))
        # v5.0: 'Log Proses' button — opens popup log window (replaces inline
        # dl_text which was 0px invisible on some DPI/resolution combos).
        ttk.Button(dl_btns, text="📋  Log Proses",
                   command=self._show_dl_logwin).pack(side="left")

        dl_prog = tk.Frame(ctl_card, bg=C_CARD)
        dl_prog.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 4))
        dl_prog.columnconfigure(0, weight=1)
        self.dl_progress = ttk.Progressbar(dl_prog, mode="determinate")
        self.dl_progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.dl_counter_lbl = tk.Label(dl_prog, text="0 / 0", bg=C_CARD, fg="#475569", font=F_BODY)
        self.dl_counter_lbl.grid(row=0, column=1)

        self.dl_status_lbl = tk.Label(ctl_card, text="Siap.", justify="left", anchor="w",
                                      bg=C_INFO_BG, fg="#334155", padx=12, pady=8, font=F_BODY)
        self.dl_status_lbl.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 10))

        # v5.0: Card 3 (Log Download) DIHAPUS — diganti popup log window
        # (SimpleLogPopup, buka via 'Log Proses' button di Card 2 atas, atau
        # auto-open saat klik 'Mulai Unduh XLS'). Inline dl_text Text widget
        # 0px invisible pada sebagian DPI/resolution combo — root cause gagal
        # diperbaiki oleh v4.17/v4.18/v4.19 (pack/grid/minsize — none worked
        # reliably). Popup window (tk.Toplevel) selalu visible independent of
        # tab grid layout. Lihat _ensure_dl_logwin + _show_dl_logwin +
        # _drain_queue dl_log handler.

        # ================= TAB DOWNLOAD SJ GIS (v4.11) =================
        sjview = ttk.Frame(tab_sj, style="TFrame")
        sjview.pack(fill="both", expand=True, padx=18, pady=16)
        sjview.columnconfigure(0, weight=1)
        sjview.columnconfigure(1, weight=1)
        # v5.0: row 1 (Card 3 log) removed — popup log window replaces sj_text.
        # Card 4 (Kode Gagal) sekarang di row 1 (sebelumnya row 2).

        # ---- Card 1: Input Kode SJ ----
        sj_in_card = self._card(sjview, "1. Input Kode SJ")
        sj_in_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        sj_in_card.columnconfigure(0, weight=1)
        tk.Label(sj_in_card, text="Masukkan kode SJ (pisahkan dgn koma atau baris baru):",
                 bg=C_CARD, fg="#475569", font=F_BODY, anchor="w"
                 ).grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 2))
        sj_txt_wrap = tk.Frame(sj_in_card, bg=C_TERM_BG)
        sj_txt_wrap.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 6))
        sj_txt_wrap.columnconfigure(0, weight=1)
        sj_txt_wrap.rowconfigure(0, weight=1)
        self.sj_kodes_text = tk.Text(sj_txt_wrap, bg=C_TERM_BG, fg="#dbeafe", insertbackground="white",
                                     relief="flat", font=F_LOG, wrap="word", height=6,
                                     undo=True)
        self.sj_kodes_text.grid(row=0, column=0, sticky="nsew")
        sj_txt_sb = ttk.Scrollbar(sj_txt_wrap, orient="vertical", command=self.sj_kodes_text.yview)
        sj_txt_sb.grid(row=0, column=1, sticky="ns")
        self.sj_kodes_text.configure(yscrollcommand=sj_txt_sb.set)
        self.sj_kodes_text.bind("<KeyRelease>", self._sj_count_kodes)
        self.sj_kodes_text.bind("<MouseWheel>", self._sj_text_wheel)
        self.sj_kodes_text.bind("<Button-4>", self._sj_text_wheel)
        self.sj_kodes_text.bind("<Button-5>", self._sj_text_wheel)
        self.sj_count_lbl = tk.Label(sj_in_card, text="0 kode terdeteksi",
                                     bg=C_INFO_BG, fg="#475569", padx=12, pady=6,
                                     font=(_FONT, 10, "bold"), anchor="w")
        self.sj_count_lbl.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))

        # ---- Card 2: Kontrol ----
        sj_ctl_card = self._card(sjview, "2. Kontrol")
        sj_ctl_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        sj_ctl_card.columnconfigure(0, weight=1)

        self.sj_script_lbl = tk.Label(sj_ctl_card, text="Script: download_sj_gis.py — memeriksa...",
                                      justify="left", anchor="w", bg=C_INFO_BG, fg="#475569",
                                      padx=12, pady=8, font=F_BODY)
        self.sj_script_lbl.grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 4))
        self.sj_chrome_lbl = tk.Label(sj_ctl_card, text="Chrome 9222: memeriksa...",
                                     justify="left", anchor="w", bg=C_INFO_BG, fg="#475569",
                                     padx=12, pady=8, font=F_BODY)
        self.sj_chrome_lbl.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))

        sj_ctl_btns = tk.Frame(sj_ctl_card, bg=C_CARD)
        sj_ctl_btns.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 6))
        # "Buka Chrome 9222" tombol paling menonjol (paling sering dipakai utk mulai kerja).
        ttk.Button(sj_ctl_btns, text="🌐  Buka Chrome 9222",
                   style="Success.TButton",
                   command=self._sj_launch_chrome).pack(side="left", padx=(0, 8))
        # v5.2: "Deteksi Ulang" + "Cek Chrome" buttons removed — auto-detect
        # on startup + auto-check 3s after "Buka Chrome 9222" + auto-check on
        # "Mulai Download" is sufficient (less clutter, same functionality).

        sj_run_btns = tk.Frame(sj_ctl_card, bg=C_CARD)
        sj_run_btns.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.sj_start_btn = ttk.Button(sj_run_btns, text="▶  Mulai Download",
                                       style="Success.TButton",
                                       command=self._start_sj_download)
        self.sj_start_btn.pack(side="left", padx=(0, 8))
        self.sj_stop_btn = ttk.Button(sj_run_btns, text="■  Hentikan",
                                      style="Danger.TButton", state="disabled",
                                      command=self._stop_sj_download)
        self.sj_stop_btn.pack(side="left", padx=(0, 8))
        # v5.0: 'Log Proses' + 'Buka Folder Unduhan' (dipindah dari Card 3 log
        # button row yang dihapus). Popup log window replaces inline sj_text.
        ttk.Button(sj_run_btns, text="📋  Log Proses",
                   command=self._show_sj_logwin).pack(side="left", padx=(0, 8))
        ttk.Button(sj_run_btns, text="📂  Buka Folder Unduhan",
                   command=self._sj_open_folder).pack(side="left")

        sj_prog = tk.Frame(sj_ctl_card, bg=C_CARD)
        sj_prog.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 4))
        sj_prog.columnconfigure(0, weight=1)
        self.sj_progress = ttk.Progressbar(sj_prog, mode="determinate")
        self.sj_progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.sj_counter_lbl = tk.Label(sj_prog, text="0 / 0", bg=C_CARD, fg="#475569", font=F_BODY)
        self.sj_counter_lbl.grid(row=0, column=1)

        self.sj_status_lbl = tk.Label(sj_ctl_card, text="Siap.", justify="left", anchor="w",
                                      bg=C_INFO_BG, fg="#334155", padx=12, pady=8, font=F_BODY)
        self.sj_status_lbl.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 10))

        # v5.0: Card 3 (Log Download SJ) DIHAPUS — diganti popup log window
        # (SimpleLogPopup, buka via 'Log Proses' button di Card 2 atas, atau
        # auto-open saat klik 'Mulai Download'). Inline sj_text Text widget
        # 0px invisible — popup window selalu visible. Lihat _ensure_sj_logwin
        # + _show_sj_logwin + _drain_queue sj_log handler. 'Buka Folder
        # Unduhan' button dipindah ke Card 2 sj_run_btns.

        # ---- Card 4: Kode Gagal (v4.13, v5.0: moved to row 1, col 0+1, compact fixed height) ----
        # Built manually (NOT via _card() helper) so we can keep a reference to
        # the title Label and update its text with the failed-count later
        # (e.g. '4. Kode Gagal (2)').
        sj_fail_card = ttk.Frame(sjview, style="Card.TFrame", padding=0)
        sj_fail_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(8, 0))
        sj_fail_card.columnconfigure(0, weight=1)
        self.sj_fail_title_lbl = tk.Label(sj_fail_card, text="4. Kode Gagal (0)",
                                         bg=C_CARD, fg="#111827",
                                         font=F_CARD, anchor="w")
        self.sj_fail_title_lbl.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        # Text widget (read-only, height 3) — shows failed kodes comma-separated.
        # Red text on light bg when failures, gray placeholder when none.
        sj_fail_wrap = tk.Frame(sj_fail_card, bg=C_INFO_BG)
        sj_fail_wrap.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 4))
        sj_fail_wrap.columnconfigure(0, weight=1)
        self.sj_failed_text = tk.Text(sj_fail_wrap, height=3, bg=C_INFO_BG, fg="#94a3b8",
                                     font=F_LOG, wrap="word", relief="flat",
                                     state="disabled", padx=8, pady=6)
        self.sj_failed_text.grid(row=0, column=0, sticky="ew")
        # No scrollbar (compact). The text is usually short.
        # Buttons row.
        sj_fail_btns = tk.Frame(sj_fail_card, bg=C_CARD)
        sj_fail_btns.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        ttk.Button(sj_fail_btns, text="\U0001f4cb Copy",
                   command=self._sj_copy_failed).pack(side="left", padx=(0, 8))
        ttk.Button(sj_fail_btns, text="\u21a9 Pindahkan ke Input",
                   command=self._sj_move_failed_to_input).pack(side="left", padx=(0, 8))
        ttk.Button(sj_fail_btns, text="Bersihkan",
                   command=self._sj_clear_failed).pack(side="left")
        # Initial populate (shows placeholder 'Tidak ada kode gagal').
        self._sj_set_failed_kodes([])

        # ---- Inisialisasi indikator SJ (auto-detect script + cek chrome + load kodes) ----
        self._sj_detect_script()
        self._sj_check_chrome()
        self._load_sj_settings()

        # ================= TAB SCREEN SHOT POWER BI (v4.14) =================
        # Menjalankan app.py (folder '4. Screen Shot Power BI') sebagai
        # subprocess `app.py --cli`. Stdout diparse di _ss_worker:
        #   PROGRESS: <cur>/<total> <label>   -> progressbar
        #   DONE: success=<N> failed=<N>      -> status label
        #   sisanya                           -> log widget
        ssview = ttk.Frame(tab_ss, style="TFrame")
        ssview.pack(fill="both", expand=True, padx=18, pady=16)
        ssview.columnconfigure(0, weight=1)
        ssview.columnconfigure(1, weight=1)
        # v5.0: row 1 (Card 3 log) removed — popup log window replaces ss_text.

        # ---- Card 1: Konfigurasi ----
        ss_cfg_card = self._card(ssview, "1. Konfigurasi")
        ss_cfg_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        ss_cfg_card.columnconfigure(1, weight=1)

        # Power BI URL
        tk.Label(ss_cfg_card, text="Power BI URL", bg=C_CARD, fg="#64748b",
                 font=F_BODY).grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(6, 4))
        self.ss_url_var = tk.StringVar()
        ttk.Entry(ss_cfg_card, textvariable=self.ss_url_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=(6, 4))

        # Pages
        tk.Label(ss_cfg_card, text="Pages", bg=C_CARD, fg="#64748b",
                 font=F_BODY).grid(row=2, column=0, sticky="w", padx=(14, 8), pady=(0, 4))
        self.ss_pages_var = tk.StringVar()
        ttk.Entry(ss_cfg_card, textvariable=self.ss_pages_var, width=22).grid(
            row=2, column=1, sticky="w", padx=(0, 8), pady=(0, 4))
        tk.Label(ss_cfg_card, text="Contoh: 19,20,21,22 atau 19-22",
                 bg=C_CARD, fg="#94a3b8", font=F_HINT, anchor="w").grid(
            row=3, column=1, sticky="w", padx=(0, 8), pady=(0, 4))

        # Output Folder
        tk.Label(ss_cfg_card, text="Output Folder", bg=C_CARD, fg="#64748b",
                 font=F_BODY).grid(row=4, column=0, sticky="w", padx=(14, 8), pady=(0, 4))
        self.ss_output_var = tk.StringVar()
        ttk.Entry(ss_cfg_card, textvariable=self.ss_output_var).grid(
            row=4, column=1, sticky="ew", padx=(0, 4), pady=(0, 4))
        ttk.Button(ss_cfg_card, text="Ubah...",
                   command=self._ss_change_output).grid(
            row=4, column=2, padx=(0, 14), pady=(0, 4))

        # Format
        tk.Label(ss_cfg_card, text="Format", bg=C_CARD, fg="#64748b",
                 font=F_BODY).grid(row=5, column=0, sticky="w", padx=(14, 8), pady=(0, 12))
        self.ss_format_var = tk.StringVar(value="PNG")
        self.ss_format_combo = ttk.Combobox(
            ss_cfg_card, textvariable=self.ss_format_var,
            values=("PNG", "PDF"), state="readonly", width=8)
        self.ss_format_combo.grid(row=5, column=1, sticky="w", padx=(0, 8), pady=(0, 12))

        # ---- Card 2: Resto & Opsi ----
        ss_ctl_card = self._card(ssview, "2. Resto & Opsi")
        ss_ctl_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        ss_ctl_card.columnconfigure(0, weight=1)

        tk.Label(ss_ctl_card, text="Daftar Resto (satu per baris):",
                 bg=C_CARD, fg="#475569", font=F_BODY, anchor="w"
                 ).grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 2))
        ss_txt_wrap = tk.Frame(ss_ctl_card, bg=C_TERM_BG)
        ss_txt_wrap.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 6))
        ss_txt_wrap.columnconfigure(0, weight=1)
        ss_txt_wrap.rowconfigure(0, weight=1)
        ss_ctl_card.rowconfigure(2, weight=1)
        self.ss_restos_text = tk.Text(ss_txt_wrap, bg=C_TERM_BG, fg="#dbeafe",
                                      insertbackground="white", relief="flat",
                                      font=F_LOG, wrap="word", height=8, undo=True)
        self.ss_restos_text.grid(row=0, column=0, sticky="nsew")
        ss_txt_sb = ttk.Scrollbar(ss_txt_wrap, orient="vertical",
                                  command=self.ss_restos_text.yview)
        ss_txt_sb.grid(row=0, column=1, sticky="ns")
        self.ss_restos_text.configure(yscrollcommand=ss_txt_sb.set)
        self.ss_restos_text.bind("<MouseWheel>", self._ss_restos_wheel)
        self.ss_restos_text.bind("<Button-4>", self._ss_restos_wheel)
        self.ss_restos_text.bind("<Button-5>", self._ss_restos_wheel)

        # V16 Optimizations frame
        ss_opt = ttk.LabelFrame(ss_ctl_card, text="V16 Optimizations", padding=8)
        ss_opt.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.ss_opt_sequential = tk.BooleanVar(value=True)
        self.ss_opt_reuse = tk.BooleanVar(value=True)
        self.ss_opt_merge = tk.BooleanVar(value=True)
        self.ss_opt_light = tk.BooleanVar(value=True)
        self.ss_opt_force = tk.BooleanVar(value=True)
        ss_row1 = tk.Frame(ss_opt, bg=C_CARD); ss_row1.pack(fill="x", pady=(0, 4))
        ttk.Checkbutton(ss_row1, text="Sequential page nav",
                       variable=self.ss_opt_sequential).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(ss_row1, text="Reuse stable screenshot",
                       variable=self.ss_opt_reuse).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(ss_row1, text="Merge final stability check",
                       variable=self.ss_opt_merge).pack(side="left")
        ss_row2 = tk.Frame(ss_opt, bg=C_CARD); ss_row2.pack(fill="x")
        ttk.Checkbutton(ss_row2, text="Light recovery (clear, no reload)",
                       variable=self.ss_opt_light).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(ss_row2, text="Force-click Next Page fallback",
                       variable=self.ss_opt_force).pack(side="left")

        # Run/Stop buttons (v5.0: 'Buka Output' moved back here from Card 3 log
        # button row (Card 3 dihapus); 'Log Proses' button added utk open popup
        # log window. Mulai + Hentikan + Log Proses + Buka Output in one row.)
        ss_run_btns = tk.Frame(ss_ctl_card, bg=C_CARD)
        ss_run_btns.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.ss_start_btn = ttk.Button(ss_run_btns, text="\u25b6  Mulai Screenshot",
                                       style="Success.TButton",
                                       command=self._start_ss)
        self.ss_start_btn.pack(side="left", padx=(0, 8))
        self.ss_stop_btn = ttk.Button(ss_run_btns, text="\u25a0  Hentikan",
                                     style="Danger.TButton", state="disabled",
                                     command=self._stop_ss)
        self.ss_stop_btn.pack(side="left", padx=(0, 8))
        ttk.Button(ss_run_btns, text="📋  Log Proses",
                   command=self._show_ss_logwin).pack(side="left", padx=(0, 8))
        ttk.Button(ss_run_btns, text="📂  Buka Output",
                   command=self._ss_open_output).pack(side="left")

        # Progress bar + counter
        ss_prog = tk.Frame(ss_ctl_card, bg=C_CARD)
        ss_prog.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 4))
        ss_prog.columnconfigure(0, weight=1)
        self.ss_progress = ttk.Progressbar(ss_prog, mode="determinate")
        self.ss_progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.ss_counter_lbl = tk.Label(ss_prog, text="0 / 0", bg=C_CARD,
                                       fg="#475569", font=F_BODY)
        self.ss_counter_lbl.grid(row=0, column=1)

        # Status label
        self.ss_status_lbl = tk.Label(ss_ctl_card, text="Siap. (Playwright + Chromium wajib terpasang)",
                                      justify="left", anchor="w", bg=C_INFO_BG,
                                      fg="#334155", padx=12, pady=8, font=F_BODY)
        self.ss_status_lbl.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 10))

        # v5.0: Card 3 (Log Screenshot) DIHAPUS — diganti popup log window
        # (SimpleLogPopup, buka via 'Log Proses' button di Card 2 atas, atau
        # auto-open saat klik 'Mulai Screenshot'). Inline ss_text Text widget
        # 0px invisible pada sebagian DPI/resolution combo — root cause gagal
        # diperbaiki oleh v4.17/v4.18/v4.19 (pack/grid/minsize — none worked
        # reliably). Popup window (tk.Toplevel) selalu visible independent of
        # tab grid layout. Lihat _ensure_ss_logwin + _show_ss_logwin +
        # _drain_queue ss_log handler. 'Buka Output' button dipindah ke Card 2
        # ss_run_btns (sebelumnya di Card 3 log button row).
        #
        # v4.17 'Test Log' button juga dihapus (sebelumnya di Card 3 log button
        # row). Test functionality tersisa di method _ss_test_log (utk
        # diagnostic jika dipanggil manual), tapi tidak ada UI button lagi —
        # user verify popup via 'Log Proses' button +Mulai Screenshot run.

        # ---- Inisialisasi indikator SS (auto-detect app.py + load config.json) ----
        self._ss_detect_script()
        self._ss_load_config()

    # ================= HELPERS =================
    def _db_tree_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.db_tree.yview_scroll(steps, "units")

    def _tree_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.tree.yview_scroll(steps, "units")

    def _sj_text_wheel(self, e):
        # v5.0: NOTE — this method name is misleading. It scrolls sj_kodes_text
        # (the INPUT box in Card 1, NOT the log). The log Text widget (sj_text)
        # was removed in v5.0 — its wheel handler was _sj_log_wheel (also removed).
        # KEPT here because sj_kodes_text input box still binds to it (lines in
        # Card 1 sj_in_card block). Removing this would break input box scroll.
        steps = _wheel_steps(e)
        if steps:
            try:
                self.sj_kodes_text.yview_scroll(steps, "units")
            except Exception:
                pass

    def _card(self, parent, title):
        outer = ttk.Frame(parent, style="Card.TFrame", padding=0)
        tk.Label(outer, text=title, bg=C_CARD, fg="#111827", font=F_CARD, anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        return outer

    def _path_row(self, parent, row, label, variable, command):
        tk.Label(parent, text=label, bg=C_CARD, fg="#64748b", font=F_BODY).grid(row=row, column=0, padx=(14, 8), pady=6, sticky="w")
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(parent, text="Pilih", command=command).grid(row=row, column=2, padx=(6, 14), pady=6)

    # ================= SETTINGS =================
    def _apply_settings(self):
        st = load_settings()
        saved = (st.get("dl_branches") or "").strip()
        if saved:
            self.dl_branches_var.set(saved)

    def _save_settings(self):
        ok = save_settings({"dl_branches": self.dl_branches_var.get().strip()})
        if not ok:
            self.log("Gagal menyimpan pengaturan ke ui_settings.json.", "WARN")
        return ok

    # ================= DATABASE =================
    def _load_db(self, silent=False):
        self.db_folder = bot.get_db_folder()
        db_map, meta = bot.load_database_folder(self.db_folder)
        self.db_map = db_map
        self.db_meta = meta
        if meta.get("created"):
            self.db_info.configure(text=f"Folder : {self.db_folder}\nFolder database baru dibuat otomatis.\nLetakkan file .xlsx/.xls di dalamnya, lalu klik Muat Ulang.")
        elif meta["files"]:
            self.db_info.configure(text=f"Folder : {self.db_folder}\nFile terbaca : {', '.join(meta['files'])}\nTotal baris COA : {meta['total_rows']}")
        else:
            self.db_info.configure(text=f"Folder : {self.db_folder}\nBelum ada file Excel database.\nLetakkan file .xlsx/.xls di folder tersebut, lalu klik Muat Ulang.")
        self._rebuild_db_tree()
        self._rebuild_plan()
        if not silent:
            if meta["files"]:
                self.log(f"Database dimuat: {meta['total_rows']} baris dari {len(meta['files'])} file.", "SUCCESS")
            else:
                self.log("Folder database kosong; belum ada mapping dimuat.", "WARN")

    def _reload_db(self):
        self._load_db(silent=False)

    def _rebuild_db_tree(self):
        for i in self.db_tree.get_children():
            self.db_tree.delete(i)
        n = 0
        for key, d in self.db_map.items():
            for r in d["rows"]:
                n += 1
                self.db_tree.insert("", "end", values=(key, d.get("cabang_db") or "-", r["coa"], r["memo"]))
        self.db_summary_lbl.configure(
            text=f"Total baris mapping : {n}   |   Sumber : {len(self.db_meta.get('files', []))} file   |   Folder : {self.db_folder}")

    # ================= DETEKSI FOLDER DOWNLOAD =================
    def _detect_dl_folder(self):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.dirname(app_dir)
        # v5.0: substring match — folder mungkin bernama '1. Download Draft IA'
        # (prefixed dgn angka urutan) atau varian lain. Sebelumnya (v4.x)
        # pakai exact-name match terhadap DL_FOLDER_NAME='Download Draft IA' ->
        # GAGAL karena folder sebenarnya bernama '1. Download Draft IA'.
        # Sekarang scan parent ATAU app_dir utk folder yg namanya mengandung
        # substring 'Download Draft IA' (case-sensitive — match exactly as in
        # DL_FOLDER_NAME). Exact-name match tetap dicoba dulu (utk kompatibilitas
        # backward bila folder tanpa prefix).
        cands = []
        for base in (parent, app_dir):
            cands.append(os.path.join(base, DL_FOLDER_NAME))  # exact-name fallback
            try:
                for name in os.listdir(base):
                    if (DL_FOLDER_NAME in name
                            and os.path.isdir(os.path.join(base, name))):
                        cands.append(os.path.join(base, name))
            except Exception:
                pass
        self.dl_folder = next((c for c in cands if os.path.isdir(c)), "")
        self.unduh_path = os.path.join(self.dl_folder, "unduh_xls_loop.py") if self.dl_folder else ""
        self.filter_path = os.path.join(self.dl_folder, "filter_pembuat_data.py") if self.dl_folder else ""

        if not self.dl_folder:
            self.dl_folder_lbl.configure(text=f"Folder '{DL_FOLDER_NAME}' tidak ditemukan di sebelah folder aplikasi.\nLetakkan folder tersebut berdampingan dengan folder Import IA, lalu klik Deteksi Ulang.")
            self.dl_start_btn.configure(state="disabled")
            self.dl_status_lbl.configure(text="Sumber belum tersedia.")
            return

        ok_unduh = os.path.isfile(self.unduh_path)
        ok_filter = os.path.isfile(self.filter_path)
        lines = [f"Folder : {self.dl_folder}",
                 f"unduh_xls_loop.py : {'ADA' if ok_unduh else 'TIDAK ADA'}",
                 f"filter_pembuat_data.py : {'ADA' if ok_filter else 'TIDAK ADA (tahap filter akan gagal)'}",
                 f"Output unduhan : {DOWNLOAD_DIR}"]
        self.dl_folder_lbl.configure(text="\n".join(lines))
        self.dl_start_btn.configure(state="normal" if ok_unduh else "disabled")
        self.dl_status_lbl.configure(text="Siap." if ok_unduh else "Script unduh tidak ditemukan.")

    def _open_download_dir(self):
        try:
            os.startfile(DOWNLOAD_DIR)
        except Exception as e:
            messagebox.showwarning(APP_TITLE, f"Tidak bisa membuka folder unduhan:\n{e}", parent=self)

    # ================= LOG DOWNLOAD =================
    # v5.0: _dl_log_line append directly ke popup (main-thread only — called
    # from _start_download + _drain_queue dl_done/dl_error handlers, semuanya
    # main thread). Worker thread (_dl_worker) pakai ui_queue.put(('dl_log',
    # line)) -> _drain_queue routes ke popup.append (handler dl_log).
    def _dl_log_line(self, line):
        """Append line to DL log popup (main-thread only — direct append)."""
        self._ensure_dl_logwin().append(line)

    def _dl_clear(self):
        self._ensure_dl_logwin().clear()

    # ================= DOWNLOAD SJ GIS (v4.11) =================
    def _sj_detect_script(self):
        """Auto-detect download_sj_gis.py path: ../3. Download SJ GIS/ relative to this file."""
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, "..", "3. Download SJ GIS", "download_sj_gis.py"),
            os.path.join(base, "3. Download SJ GIS", "download_sj_gis.py"),
            os.path.join(base, "download_sj_gis.py"),
        ]
        for c in candidates:
            c = os.path.normpath(c)
            if os.path.isfile(c):
                self.sj_script_path = c
                self.sj_script_lbl.configure(
                    text=f"Script: {os.path.basename(c)} — ✓ terdeteksi", fg="#16a34a")
                return True
        self.sj_script_path = None
        self.sj_script_lbl.configure(
            text="Script: download_sj_gis.py — ✗ tidak ditemukan", fg="#dc2626")
        return False

    def _sj_check_chrome(self):
        """Check if Chrome debugging port 9222 is active."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", 9222)) == 0:
                    self.sj_chrome_lbl.configure(text="Chrome 9222: ✓ terhubung", fg="#16a34a")
                    return True
        except Exception:
            pass
        self.sj_chrome_lbl.configure(text="Chrome 9222: ✗ belum aktif", fg="#dc2626")
        return False

    def _sj_launch_chrome(self):
        """Launch Chrome with debugging port 9222, open accurate.id. Auto re-check after."""
        # Cari chrome.exe di lokasi umum (Program Files / x86 / LOCALAPPDATA / PATH).
        chrome_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"),
                         "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
                         "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""),
                         "Google", "Chrome", "Application", "chrome.exe"),
        ]
        chrome_path = None
        for p in chrome_paths:
            if p and os.path.isfile(p):
                chrome_path = p
                break
        if not chrome_path:
            # Fallback: cari di PATH sistem.
            try:
                import shutil
                chrome_path = shutil.which("chrome") or shutil.which("chrome.exe")
            except Exception:
                chrome_path = None
        if not chrome_path:
            messagebox.showwarning(
                APP_TITLE,
                "chrome.exe tidak ditemukan.\n"
                "Cari manual di:\n"
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                parent=self)
            return
        try:
            subprocess.Popen([
                chrome_path,
                "--remote-debugging-port=9222",
                "--user-data-dir=C:\\ChromeDebugProfile",
                "--disable-background-timer-throttling",        # JS timers full speed when backgrounded
                "--disable-backgrounding-occluded-windows",      # don't deprioritize occluded windows
                "--disable-renderer-backgrounding",              # keep rendering priority high
                "https://accurate.id",
            ])
            self._sj_log_line("[INFO] Chrome diluncurkan dengan port 9222. Tunggu 3 detik, cek koneksi...")
            self.sj_status_lbl.configure(text="Chrome diluncurkan, tunggu 3s...")
            # Re-check setelah 3 detik (beri waktu Chrome start + listen port 9222).
            def _recheck():
                time.sleep(3)
                ok = self._sj_check_chrome()
                if ok:
                    self._sj_log_line("[OK] Chrome 9222 terhubung. Siap download.")
                    self.sj_status_lbl.configure(text="Chrome 9222 siap. Klik Mulai Download.")
                else:
                    self._sj_log_line("[WARNING] Chrome blm terdeteksi di port 9222. "
                                      "Tunggu Chrome selesai load, lalu klik 'Buka Chrome 9222' lagi.")
                    self.sj_status_lbl.configure(
                        text="Chrome launching... tunggu atau klik 'Buka Chrome 9222' lagi.")
            threading.Thread(target=_recheck, daemon=True).start()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Gagal meluncurkan Chrome: {e}", parent=self)

    def _sj_open_folder(self):
        """Open ~/Downloads folder."""
        try:
            if sys.platform == "win32":
                try:
                    os.startfile(DOWNLOAD_DIR)
                except Exception:
                    subprocess.Popen(["explorer", DOWNLOAD_DIR])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", DOWNLOAD_DIR])
            else:
                subprocess.Popen(["xdg-open", DOWNLOAD_DIR])
        except Exception as e:
            messagebox.showwarning(APP_TITLE, f"Tidak bisa membuka folder unduhan:\n{e}", parent=self)

    def _sj_clear(self):
        # v5.0: clear popup log window (replaces sj_text inline Text deletion).
        self._ensure_sj_logwin().clear()

    def _sj_log_line(self, line):
        """Append a line to the SJ log popup (thread-safe via ui_queue ->
        _drain_queue sj_log handler -> popup.append)."""
        self.ui_queue.put(("sj_log", line))

    def _sj_count_kodes(self, event=None):
        """Parse the Text widget, count valid kode patterns."""
        text = self.sj_kodes_text.get("1.0", "end").strip()
        parts = re.split(r"[,\n]+", text)
        kodes = [p.strip() for p in parts if p.strip()]
        valid = [k for k in kodes if re.match(r"IT\.\d{4}\.\d{2}\.\d+", k)]
        self.sj_count_lbl.configure(text=f"{len(valid)} kode terdeteksi")
        self.sj_kodes = valid

    # ================= KODE GAGAL CARD (v4.13) =================
    def _sj_set_failed_kodes(self, kodes_list):
        """Populate the 'Kode Gagal' card with failed kodes.

        Called from _drain_queue (tag 'sj_failed') after _sj_worker parses the
        'SJ_RESULT_FAIL: <kodes>' marker line emitted by download_sj_gis.py
        v8.13. Also called directly from _start_sj_download (with []) to clear
        the card before a new run, and from _sj_clear_failed.
        """
        self.sj_failed_kodes = list(kodes_list)
        # Update title with count.
        self.sj_fail_title_lbl.configure(text=f"4. Kode Gagal ({len(self.sj_failed_kodes)})")
        # Update text widget.
        self.sj_failed_text.configure(state="normal")
        self.sj_failed_text.delete("1.0", "end")
        if self.sj_failed_kodes:
            self.sj_failed_text.insert("1.0", ", ".join(self.sj_failed_kodes))
            self.sj_failed_text.configure(fg="#dc2626")  # red
        else:
            # Gray placeholder — indicate no failures.
            self.sj_failed_text.insert("1.0", "Tidak ada kode gagal \u2713")
            self.sj_failed_text.configure(fg="#94a3b8")  # slate-400
        self.sj_failed_text.configure(state="disabled")

    def _sj_copy_failed(self):
        """Copy failed kodes (comma-separated) to system clipboard."""
        if not self.sj_failed_kodes:
            messagebox.showinfo(APP_TITLE, "Tidak ada kode gagal untuk di-copy.",
                                parent=self)
            return
        text = ", ".join(self.sj_failed_kodes)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # ensure clipboard is set on X11
        self._sj_log_line(
            f"[INFO] {len(self.sj_failed_kodes)} kode gagal disalin ke clipboard.")
        messagebox.showinfo(
            APP_TITLE,
            f"{len(self.sj_failed_kodes)} kode gagal disalin ke clipboard:\n"
            f"{text[:200]}",
            parent=self)

    def _sj_move_failed_to_input(self):
        """Move failed kodes into the Input Kode SJ text box (replace content).

        Enables quick retry: user clicks 'Pindahkan ke Input' then 'Mulai
        Download' again. Only the failed subset is re-run.
        """
        if not self.sj_failed_kodes:
            messagebox.showinfo(APP_TITLE, "Tidak ada kode gagal untuk di-retry.",
                                parent=self)
            return
        text = ", ".join(self.sj_failed_kodes)
        self.sj_kodes_text.delete("1.0", "end")
        self.sj_kodes_text.insert("1.0", text)
        self._sj_count_kodes()  # update count + re-parse self.sj_kodes
        self._sj_log_line(
            f"[INFO] {len(self.sj_failed_kodes)} kode gagal dipindahkan ke input. "
            "Klik 'Mulai Download' untuk retry.")
        messagebox.showinfo(
            APP_TITLE,
            f"{len(self.sj_failed_kodes)} kode gagal dipindahkan ke input.\n"
            "Klik 'Mulai Download' untuk retry.",
            parent=self)

    def _sj_clear_failed(self):
        """Clear the failed-kodes list + reset the card to placeholder."""
        self._sj_set_failed_kodes([])
        self._sj_log_line("[INFO] List kode gagal dibersihkan.")

    def _start_sj_download(self):
        if self.sj_running:
            return
        if not self._sj_detect_script():
            messagebox.showwarning(
                APP_TITLE,
                "download_sj_gis.py tidak ditemukan.\n"
                "Pastikan file ada di folder '3. Download SJ GIS' "
                "berdampingan dengan folder '2. Import IA'.",
                parent=self)
            return
        self._sj_count_kodes()  # parse latest
        if not self.sj_kodes:
            messagebox.showwarning(
                APP_TITLE,
                "Masukkan minimal 1 kode SJ (format: IT.2026.09.19805).\n"
                "Pisahkan multi-kode dengan koma atau baris baru.",
                parent=self)
            return
        if not self._sj_check_chrome():
            messagebox.showwarning(
                APP_TITLE,
                "Chrome debugging (port 9222) belum aktif.\n"
                "Klik tombol 'Buka Chrome 9222' (otomatis pakai anti-throttle flags),\n"
                "atau jalankan manual:\n"
                "  chrome.exe --remote-debugging-port=9222 "
                "--user-data-dir=\"C:\\ChromeDebugProfile\" "
                "--disable-background-timer-throttling "
                "--disable-backgrounding-occluded-windows "
                "--disable-renderer-backgrounding",
                parent=self)
            return
        # save kodes to settings
        self._save_sj_settings()
        self.sj_running = True
        self.sj_stop.clear()
        self.sj_start_btn.configure(state="disabled")
        self.sj_stop_btn.configure(state="normal")
        self.sj_progress["value"] = 0
        self.sj_progress["maximum"] = max(len(self.sj_kodes), 1)
        self.sj_counter_lbl.configure(text=f"0 / {len(self.sj_kodes)}")
        self.sj_status_lbl.configure(text=f"Berjalan — {len(self.sj_kodes)} kode")
        # v4.13: clear previous failed list (a new run replaces last run's
        # failures; populated again when worker parses SJ_RESULT_FAIL marker).
        self._sj_set_failed_kodes([])
        # v5.0: auto-open popup log window + clear (replace inline sj_text).
        self._ensure_sj_logwin().clear()
        self._ensure_sj_logwin().show()
        self._sj_log_line(f"===== Mulai Download SJ GIS: {len(self.sj_kodes)} kode =====")
        for k in self.sj_kodes:
            self._sj_log_line(f"  - {k}")
        threading.Thread(target=self._sj_worker, daemon=True).start()

    def _stop_sj_download(self):
        if not self.sj_running:
            return
        self.sj_stop.set()
        self.sj_stop_btn.configure(state="disabled")
        self.sj_status_lbl.configure(text="Menghentikan...")
        proc = self.sj_proc

        def _graceful():
            try:
                if proc is not None and proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        threading.Thread(target=_graceful, daemon=True).start()

    def _sj_worker(self):
        """Run download_sj_gis.py as subprocess, read stdout, push to ui_queue."""
        kodes_str = ", ".join(self.sj_kodes)
        env = {**os.environ,
               "SJ_GIS_KODES": kodes_str,
               "IA_UI_MODE": "1",
               "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.Popen(
                [sys.executable, self.sj_script_path],
                cwd=os.path.dirname(self.sj_script_path),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=env,
            )
        except Exception as e:
            self.ui_queue.put(("sj_log", f"[ERROR] Gagal menjalankan: {e}"))
            self.ui_queue.put(("sj_done", (0, len(self.sj_kodes))))
            return
        self.sj_proc = proc
        total = len(self.sj_kodes)
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            if not line:
                continue
            self.ui_queue.put(("sj_log", line))
            # parse progress: [X/Y] pattern (dari output "  [i/total] kode")
            m = re.search(r"\[(\d+)/(\d+)\]", line)
            if m:
                cur = int(m.group(1))
                tot = int(m.group(2))
                self.ui_queue.put(("sj_progress", (cur, tot)))
            # v4.13: parse machine-readable marker lines emitted by
            # download_sj_gis.py v8.13 at the end of main():
            #   'SJ_RESULT_OK: IT.2026.09.19805'
            #   'SJ_RESULT_FAIL: IT.2026.09.20451, IT.2026.09.20447'
            # Empty payload after the colon = none (e.g. 'SJ_RESULT_FAIL: ').
            # Only SJ_RESULT_FAIL is consumed by the UI (to populate Card 4).
            if line.startswith("SJ_RESULT_FAIL:"):
                fail_str = line[len("SJ_RESULT_FAIL:"):].strip()
                if fail_str:
                    failed = [k.strip() for k in fail_str.split(",") if k.strip()]
                else:
                    failed = []
                self.ui_queue.put(("sj_failed", failed))
            # parse [DONE] / [OK] / [FAIL] / [ERROR]
            # v5.2: detect new professional format (✅ Selesai / ❌) in addition
            # to legacy markers ([DONE] / [OK] / [FAIL] / [ERROR]).
            if "[DONE]" in line or "✅ Selesai" in line or " [OK] " in line or line.strip().endswith("[OK]"):
                self.ui_queue.put(("sj_ok", line))
            elif "[FAIL]" in line or "[ERROR]" in line or "❌" in line:
                self.ui_queue.put(("sj_fail", line))
        proc.wait()
        self.ui_queue.put(("sj_done", (None, total)))

    def _save_sj_settings(self):
        """Save last kodes to ui_settings.json (merge with existing keys)."""
        data = load_settings()
        data["sj_kodes"] = ", ".join(self.sj_kodes)
        if not save_settings(data):
            self.log("Gagal menyimpan sj_kodes ke ui_settings.json.", "WARN")

    def _load_sj_settings(self):
        """Load last kodes from ui_settings.json, populate Text widget."""
        data = load_settings()
        kodes = (data.get("sj_kodes") or "").strip()
        if kodes:
            self.sj_kodes_text.delete("1.0", "end")
            self.sj_kodes_text.insert("1.0", kodes)
            self._sj_count_kodes()

    # ================= SCREEN SHOT POWER BI (v4.14) =================
    def _ss_detect_script(self):
        """Auto-detect app.py path: ../4. Screen Shot Power BI/ relative to this file.

        Returns True if app.py is found, False otherwise. Sets self.ss_script_path.
        """
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, "..", "4. Screen Shot Power BI", "app.py"),
            os.path.join(base, "4. Screen Shot Power BI", "app.py"),
            os.path.join(base, "app.py"),
        ]
        for c in candidates:
            c = os.path.normpath(c)
            if os.path.isfile(c):
                self.ss_script_path = c
                return True
        self.ss_script_path = None
        return False

    def _ss_load_config(self):
        """Load config.json from app.py folder, populate form fields.

        Called at end of _build_ui() after _ss_detect_script(). If script not
        detected, leaves form fields at their defaults (empty / 'PNG').
        """
        if not self.ss_script_path:
            # leave defaults; user can fill manually
            self.ss_format_var.set("PNG")
            self.ss_output_var.set("")
            return
        cfg_path = os.path.join(os.path.dirname(self.ss_script_path), "config.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            self._ss_log_line(f"[WARNING] Gagal load config.json: {e}")
            return
        self.ss_url_var.set(cfg.get("powerbi_url", ""))
        self.ss_pages_var.set(cfg.get("page", "19,20,21,22"))
        # output_dir default = folder 'output' di sebelah app.py
        default_out = os.path.join(os.path.dirname(self.ss_script_path), "output")
        self.ss_output_var.set(cfg.get("output_dir", default_out) or default_out)
        self.ss_format_var.set(str(cfg.get("output_format", "PNG")).upper())
        self.ss_restos_text.delete("1.0", "end")
        self.ss_restos_text.insert("1.0", cfg.get("restos", "4217\nDPKLIM\nMTR\nBSD"))
        self.ss_opt_sequential.set(bool(cfg.get("opt_sequential_page_nav", True)))
        self.ss_opt_reuse.set(bool(cfg.get("opt_reuse_stable_screenshot", True)))
        self.ss_opt_merge.set(bool(cfg.get("opt_merge_final_stability", True)))
        self.ss_opt_light.set(bool(cfg.get("opt_light_recovery", True)))
        self.ss_opt_force.set(bool(cfg.get("opt_force_click_next_page", True)))

    def _ss_save_config(self):
        """Save form values to config.json (in app.py folder) before running.

        Merges with existing keys (preserves viewport / timing / etc).
        """
        if not self.ss_script_path:
            return
        cfg_path = os.path.join(os.path.dirname(self.ss_script_path), "config.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg["powerbi_url"] = self.ss_url_var.get().strip()
        cfg["page"] = self.ss_pages_var.get().strip()
        cfg["output_dir"] = self.ss_output_var.get().strip()
        cfg["output_format"] = self.ss_format_var.get().strip().upper()
        cfg["restos"] = self.ss_restos_text.get("1.0", "end").strip()
        cfg["opt_sequential_page_nav"] = bool(self.ss_opt_sequential.get())
        cfg["opt_reuse_stable_screenshot"] = bool(self.ss_opt_reuse.get())
        cfg["opt_merge_final_stability"] = bool(self.ss_opt_merge.get())
        cfg["opt_light_recovery"] = bool(self.ss_opt_light.get())
        cfg["opt_force_click_next_page"] = bool(self.ss_opt_force.get())
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._ss_log_line(f"[WARNING] Gagal simpan config.json: {e}")

    def _ss_change_output(self):
        """Browse for output folder."""
        initial = self.ss_output_var.get().strip()
        if not initial or not os.path.isdir(initial):
            initial = (os.path.dirname(self.ss_script_path)
                       if self.ss_script_path else os.getcwd())
        folder = filedialog.askdirectory(
            title="Pilih folder output", initialdir=initial)
        if folder:
            self.ss_output_var.set(folder)

    def _ss_open_output(self):
        """Open output folder in OS file explorer."""
        folder = self.ss_output_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                APP_TITLE,
                "Folder output tidak ada.\nMulai screenshot dulu, folder dibuat otomatis.",
                parent=self)
            return
        try:
            if sys.platform == "win32":
                try:
                    os.startfile(folder)
                except Exception:
                    subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _ss_clear(self):
        # v5.0: clear popup log window (replaces ss_text inline Text deletion).
        self._ensure_ss_logwin().clear()

    def _ss_log_line(self, line):
        """Append a line to the SS log popup (thread-safe via ui_queue ->
        _drain_queue ss_log handler -> popup.append)."""
        self.ui_queue.put(("ss_log", line))

    def _ss_test_log(self):
        """Test: push 8 dummy lines to verify the SS log popup works.

        v5.0: 'Test Log' button dihapus dari UI (sebelumnya di Card 3 log
        button row). Method ini dipertahankan utk diagnostic manual (call via
        console/script). Routes directly ke popup (bukan via ui_queue) utk
        immediate feedback. show()+clear() utk mulai fresh.
        """
        win = self._ensure_ss_logwin()
        win.show()
        win.clear()
        win.append("===== TEST LOG: verifikasi widget log =====")
        for i in range(1, 6):
            win.append(
                f"[TEST {i}/5] Log widget test line - jika ini keliatan, log jalan.")
        win.append(
            "[TEST] Jika 6 baris di atas keliatan, masalahnya di subprocess (app.py --cli).")
        win.append(
            "[TEST] Kalau nggak keliatan, masalahnya di ss_logwin popup atau _drain_queue.")

    def _ss_restos_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            try:
                self.ss_restos_text.yview_scroll(steps, "units")
            except Exception:
                pass

    # v5.0: _ss_text_wheel DIHAPUS — scrolled ss_text inline log widget yang
    # sudah dihapus (Card 3 removed). Wheel scroll utk popup Text widget
    # sudah ditangani oleh lambda binding di SimpleLogPopup.__init__.

    def _start_ss(self):
        """Validate form + save config + launch `app.py --cli` subprocess."""
        if self.ss_running:
            return
        if not self._ss_detect_script():
            messagebox.showwarning(
                APP_TITLE,
                "app.py tidak ditemukan di folder '4. Screen Shot Power BI'.\n"
                "Pastikan folder berdampingan dengan '2. Import IA'.",
                parent=self)
            return
        if not self.ss_url_var.get().strip():
            messagebox.showwarning(APP_TITLE, "Power BI URL belum diisi.", parent=self)
            return
        if not self.ss_pages_var.get().strip():
            messagebox.showwarning(
                APP_TITLE, "Pages belum diisi (mis. 19,20,21,22).", parent=self)
            return
        restos = [r.strip() for r in self.ss_restos_text.get("1.0", "end").splitlines()
                  if r.strip()]
        if not restos:
            messagebox.showwarning(APP_TITLE, "Daftar resto masih kosong.", parent=self)
            return
        # save config.json before launching (so subprocess reads latest values)
        self._ss_save_config()
        self.ss_running = True
        self.ss_stop.clear()
        self.ss_start_btn.configure(state="disabled")
        self.ss_stop_btn.configure(state="normal")
        self.ss_progress["value"] = 0
        self.ss_progress["maximum"] = 1
        self.ss_counter_lbl.configure(text="0 / 0")
        self.ss_status_lbl.configure(
            text=f"Berjalan — {len(restos)} resto × pages {self.ss_pages_var.get()}")
        # v5.0: auto-open popup log window + clear (replace inline ss_text).
        self._ensure_ss_logwin().clear()
        self._ensure_ss_logwin().show()
        self._ss_log_line(
            f"===== Mulai Screen Shot Power BI: pages={self.ss_pages_var.get()} "
            f"| resto={len(restos)} =====")
        threading.Thread(target=self._ss_worker, daemon=True).start()

    def _stop_ss(self):
        """Request stop: set threading.Event + terminate subprocess gracefully."""
        if not self.ss_running:
            return
        self.ss_stop.set()
        self.ss_stop_btn.configure(state="disabled")
        self.ss_status_lbl.configure(text="Menghentikan...")
        proc = self.ss_proc

        def _graceful():
            try:
                if proc is not None and proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        threading.Thread(target=_graceful, daemon=True).start()

    def _ss_worker(self):
        """Run app.py --cli as subprocess, read stdout, push to ui_queue.

        Parses machine-readable markers emitted by run_cli() in app.py:
          'PROGRESS: <cur>/<total> <label>' -> ('ss_progress', (cur, tot, label))
          'DONE: success=<N> failed=<N>'    -> ('ss_done', (success, failed))
          any other line                    -> ('ss_log', line)
        """
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        # Track whether app.py emitted a DONE marker so we can detect crashes.
        self._ss_done_seen = False
        try:
            proc = subprocess.Popen(
                [sys.executable, self.ss_script_path, "--cli"],
                cwd=os.path.dirname(self.ss_script_path),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=env,
            )
        except Exception as e:
            self.ui_queue.put(("ss_log", f"[ERROR] Gagal menjalankan app.py: {e}"))
            self.ui_queue.put(("ss_done", (0, 0)))
            return
        self.ss_proc = proc
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            self.ui_queue.put(("ss_log", line))
            if line.startswith("PROGRESS:"):
                m = re.search(r"PROGRESS:\s*(\d+)/(\d+)\s*(.*)", line)
                if m:
                    cur = int(m.group(1))
                    tot = int(m.group(2))
                    label = m.group(3)
                    self.ui_queue.put(("ss_progress", (cur, tot, label)))
            elif line.startswith("DONE:"):
                m = re.search(r"DONE:\s*success=(\d+)\s*failed=(\d+)", line)
                if m:
                    success = int(m.group(1))
                    failed = int(m.group(2))
                    self._ss_done_seen = True
                    self.ui_queue.put(("ss_done", (success, failed)))
            # Check stop between lines (best-effort; subprocess terminate
            # is the real stop mechanism in _stop_ss).
            if self.ss_stop.is_set():
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
        proc.wait()
        exit_code = proc.returncode
        # If process crashed (non-zero exit) and no DONE marker was seen,
        # surface the failure in the log so the user sees the traceback.
        if exit_code != 0 and not self._ss_done_seen:
            self.ui_queue.put(("ss_log", f"[ERROR] app.py exited with code {exit_code}. Lihat log di atas untuk traceback."))
        # Always emit a final ss_done (None, None) if no DONE marker was seen,
        # so the UI re-enables the Start button.
        self.ui_queue.put(("ss_done", (None, None)))

    def _parse_branches(self):
        raw = self.dl_branches_var.get()
        return [x.strip() for x in re.split(r"[,;]", raw) if x.strip()]

    # ================= MULAI / STOP DOWNLOAD =================
    def _start_download(self):
        if self.dl_running:
            return
        if not self.unduh_path or not os.path.isfile(self.unduh_path):
            messagebox.showwarning(APP_TITLE, "Script unduh_xls_loop.py tidak ditemukan.\nKlik Deteksi Ulang setelah folder disiapkan.", parent=self)
            return
        branches = self._parse_branches()
        if not branches:
            messagebox.showwarning(APP_TITLE, "Isi dahulu Nama Cabang / Pembuat Data\n(pisahkan dengan koma bila lebih dari satu).", parent=self)
            return
        self.dl_branches = ", ".join(branches)
        self._save_settings()

        stages = []
        if not self.dl_skip_filter_var.get():
            if not self.filter_path or not os.path.isfile(self.filter_path):
                messagebox.showerror(
                    APP_TITLE,
                    "filter_pembuat_data.py tidak ditemukan di:\n" + (self.dl_folder or "-") +
                    "\n\nSimpan file filter tersebut ke folder Download Draft IA,\n"
                    "atau centang 'Lewati tahap filter' bila list sudah difilter manual.",
                    parent=self)
                return
            stages.append((self.filter_path, "[FILTER]"))
        stages.append((self.unduh_path, "[UNDUH]"))

        self.dl_running = True
        self.dl_stop.clear()
        self.dl_start_btn.configure(state="disabled")
        self.dl_skip_cb.configure(state="disabled")
        self.dl_stop_btn.configure(state="normal")
        self.dl_progress["value"] = 0
        self.dl_counter_lbl.configure(text="0 / 0")
        urutan = " -> ".join(s[1] for s in stages)
        self.dl_status_lbl.configure(text=f"Berjalan ({urutan}) — cabang: {self.dl_branches}")
        # v5.0: auto-open popup log window + clear (replace inline dl_text).
        self._ensure_dl_logwin().clear()
        self._ensure_dl_logwin().show()
        self._dl_log_line(f"===== Pipeline: {urutan} | Cabang: {self.dl_branches} =====")
        threading.Thread(target=self._dl_worker, args=(stages,), daemon=True).start()

    def _stop_download(self):
        if not self.dl_running:
            return
        self.dl_stop.set()
        self.dl_stop_btn.configure(state="disabled")
        self.dl_status_lbl.configure(text="Menghentikan...")
        proc = self.dl_proc

        def _graceful():
            try:
                if proc is not None and proc.poll() is None:
                    try:
                        proc.stdin.write("\n")
                        proc.stdin.flush()
                    except Exception:
                        pass
                    try:
                        proc.wait(timeout=4)
                    except Exception:
                        if proc.poll() is None:
                            proc.terminate()
            except Exception:
                pass
        threading.Thread(target=_graceful, daemon=True).start()

    def _dl_worker(self, stages):
        final_success = final_fail = None
        overall_ok = True
        env = {**os.environ, "IA_UI_MODE": "1", "IA_FILTER_BRANCHES": self.dl_branches, "PYTHONIOENCODING": "utf-8"}
        for path, prefix in stages:
            self.ui_queue.put(("dl_log", f"{prefix} Menjalankan: {os.path.basename(path)}"))
            try:
                proc = subprocess.Popen(
                    [sys.executable, path],
                    cwd=os.path.dirname(path),
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                    env=env,
                )
            except Exception as e:
                self.ui_queue.put(("dl_error", f"Gagal menjalankan {os.path.basename(path)}: {e}"))
                return
            self.dl_proc = proc
            succ = fail = 0
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                self.ui_queue.put(("dl_log", f"{prefix} {line}"))
                m = re.search(r"SIKLUS (\d+)/(\d+)", line)
                if m:
                    self.ui_queue.put(("dl_progress", int(m.group(1)), int(m.group(2))))
                if "SIKLUS SELESAI" in line:
                    succ += 1
                    self.ui_queue.put(("dl_count", succ, fail))
                if re.search(r"\[ERROR\]\s+(E_[A-Z_]+|FATAL-LOOP)\s*:", line):
                    fail += 1
                    self.ui_queue.put(("dl_count", succ, fail))
                ms = re.search(r"Berhasil diunduh\s*:\s*(\d+)", line)
                if ms:
                    final_success = int(ms.group(1))
                mf = re.search(r"^\s*Gagal\s*:\s*(\d+)", line)
                if mf:
                    final_fail = int(mf.group(1))
                if "Tekan Enter untuk keluar" in line:
                    try:
                        proc.stdin.write("\n")
                        proc.stdin.flush()
                    except Exception:
                        pass
            code = proc.wait()
            self.dl_proc = None
            if prefix == "[FILTER]" and code != 0:
                self.ui_queue.put(("dl_error", f"Tahap filter berhenti dengan kode {code}. Pipeline dihentikan."))
                return
            if self.dl_stop.is_set():
                self.ui_queue.put(("dl_log", f"{prefix} Dihentikan oleh pengguna."))
                overall_ok = False
                break
        if final_success is not None:
            succ = final_success
        if final_fail is not None:
            fail = final_fail
        self.ui_queue.put(("dl_done", 0 if overall_ok else 1, succ, fail))

    # ================= LAIN-LAIN =================
    def set_today(self):
        t = date.today()
        self.date_day.set(f"{t.day:02d}")
        self.date_month.set(f"{t.month:02d}")
        self.date_year.set(str(t.year))

    def get_date_str(self):
        try:
            d, m, y = int(self.date_day.get()), int(self.date_month.get()), int(self.date_year.get())
            return date(y, m, d).strftime("%d/%m/%Y")
        except (ValueError, tk.TclError):
            raise ValueError("Tanggal tidak valid.")

    def _ensure_logwin(self):
        if self.logwin is None or not self.logwin.winfo_exists():
            self.logwin = ProcessLogWindow(self)
            for line, kind in self.log_buffer:
                self.logwin.append(line, kind)
        return self.logwin

    def _show_logwin(self):
        self._ensure_logwin().show()

    # v5.0: popup log windows untuk DL, SJ, SS tabs. Lazy-init pattern sama
    # seperti _ensure_logwin (Otomasi tab, ProcessLogWindow). Hidden by default
    # (withdraw in __init__), shown via _show_*_logwin (button click) atau
    # auto-open di _start_download/_start_sj_download/_start_ss. Reusable
    # (withdraw on close, deiconify on show — NOT destroyed).
    def _ensure_dl_logwin(self):
        if self.dl_logwin is None or not self.dl_logwin.winfo_exists():
            self.dl_logwin = SimpleLogPopup(self, "Log Download Draft IA")
        return self.dl_logwin

    def _ensure_sj_logwin(self):
        if self.sj_logwin is None or not self.sj_logwin.winfo_exists():
            self.sj_logwin = SimpleLogPopup(self, "Log Download SJ GIS")
        return self.sj_logwin

    def _ensure_ss_logwin(self):
        if self.ss_logwin is None or not self.ss_logwin.winfo_exists():
            self.ss_logwin = SimpleLogPopup(self, "Log Screen Shot Power BI")
        return self.ss_logwin

    def _show_dl_logwin(self):
        self._ensure_dl_logwin().show()

    def _show_sj_logwin(self):
        self._ensure_sj_logwin().show()

    def _show_ss_logwin(self):
        self._ensure_ss_logwin().show()

    def log(self, message, kind="INFO"):
        stamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"SUCCESS": "[OK]", "ERROR": "[GAGAL]", "WARN": "[PERHATIAN]", "FILE": "[FILE]"}.get(kind, "[INFO]")
        line = f"{stamp} {prefix} {message}\n"
        self.log_buffer.append((line, kind))
        if len(self.log_buffer) > 3000:
            del self.log_buffer[:1000]
        if self.logwin is not None and self.logwin.winfo_exists():
            self.logwin.append(line, kind)
            if kind == "FILE":
                self.logwin.set_file(message.strip("─ ").strip())
                self.logwin.set_step("Memproses file...")
            else:
                color = {"SUCCESS": "#4ade80", "ERROR": "#f87171", "WARN": "#fbbf24"}.get(kind, "#e2e8f0")
                self.logwin.set_step(message, color)

    def _queue_log(self, message, kind="INFO"):
        self.ui_queue.put(("log", message, kind))

    def pick_folder(self):
        path = filedialog.askdirectory(title="Pilih Folder Induk")
        if not path:
            return
        self.root_folder = path
        self.folder_var.set(path)
        self.refresh_files()

    def refresh_files(self):
        if not self.root_folder:
            self.folder_summary.configure(text="Belum ada folder dipilih.")
            self._rebuild_plan()
            return
        folders, total_files = bot.collect_excel_files(self.root_folder)
        self.folders = folders
        self.files = [p for f in folders for p in f["files"]]
        self.log(f"Scan folder: {len(folders)} folder, {total_files} file.")
        self._rebuild_plan()

    def _rebuild_plan(self):
        # Parse user's skip keywords (comma-separated, uppercased)
        raw_kw = self.skip_keywords_var.get().strip()
        skip_kw = tuple(s.strip().upper() for s in raw_kw.split(",") if s.strip()) if raw_kw else ()
        self.plan = bot.build_file_plan(self.db_map, self.files, skip_keywords=skip_kw)
        for item in self.tree.get_children():
            self.tree.delete(item)
        counts = {}
        no = 1
        for p in self.plan:
            counts[p["status"]] = counts.get(p["status"], 0) + 1
            ket_display = (p["memo"] or "-")[:70] if p["status"] == "OK" else p["reason"]
            self.tree.insert("", "end", tags=(p["status"],), values=(
                no, p["folder"], p["filename"], p["branch"] or "-",
                p["coa"] or "-", ket_display, p["status"]))
            no += 1
        ok = counts.get("OK", 0)
        skip = counts.get("DILEWATI", 0)
        bad = counts.get("TIDAK COCOK", 0)
        wait = counts.get("MENUNGGU DB", 0)

        if not self.plan:
            self.match_lbl.configure(text="Belum ada data.", fg="#475569")
        else:
            txt = f"Cocok: {ok}   |   Dilewati: {skip}   |   Tidak Cocok: {bad}"
            if wait:
                txt += f"   |   Menunggu DB: {wait}"
            self.match_lbl.configure(text=txt,
                                     fg="#15803d" if (ok and not bad) else ("#dc2626" if bad else "#b45309"))

        self.folder_summary.configure(
            text=f"Folder : {len(self.folders)}\n"
                 f"File      : {len(self.files)}\n"
                 f"Siap     : {ok}\n"
                 f"Dilewati : {skip}\n"
                 f"Tidak cocok : {bad}")

    def _refresh_summary_loop(self):
        try:
            if bot.is_port_open(bot.DEBUG_PORT):
                self.chrome_lbl.configure(text="● Chrome : TERHUBUNG", fg="#16a34a")
            else:
                self.chrome_lbl.configure(text="● Chrome : BELUM TERHUBUNG", fg="#dc2626")
            lines = []
            lines.append(f"Database : {self.db_meta.get('total_rows', 0)} baris COA" if self.db_map else "Database : belum dimuat")
            try:
                lines.append(f"Tanggal  : {self.get_date_str()}")
            except Exception:
                lines.append("Tanggal  : -")
            ok = sum(1 for p in self.plan if p["status"] == "OK")
            lines.append(f"Siap        : {ok} file")
            self.summary_lbl.configure(text="\n".join(lines))
        except Exception:
            pass
        self.after(2000, self._refresh_summary_loop)

    def _drain_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()
                a = item[0]
                if a == "log":
                    self.log(item[1], item[2])
                elif a == "progress":
                    if self.logwin is not None and self.logwin.winfo_exists():
                        self.logwin.set_progress(item[1], item[2])
                elif a == "done":
                    success, fail, skipped = item[1], item[2], item[3]
                    self.running = False
                    for b in self.start_buttons:
                        b.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if self.logwin is not None and self.logwin.winfo_exists():
                        self.logwin.finish(success, fail, skipped)
                    messagebox.showinfo(APP_TITLE, f"Otomasi selesai.\n\nBerhasil : {success}\nGagal    : {fail}\nDilewati : {skipped}", parent=self)
                elif a == "error":
                    self.running = False
                    for b in self.start_buttons:
                        b.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if self.logwin is not None and self.logwin.winfo_exists():
                        self.logwin.set_step("TERJADI ERROR — lihat detail di log", "#f87171")
                    messagebox.showerror(APP_TITLE, item[1], parent=self)
                elif a == "dl_log":
                    # v5.0: route ke popup log window (replaces inline dl_text
                    # which was 0px invisible).
                    self._ensure_dl_logwin().append(item[1])
                elif a == "dl_progress":
                    self.dl_progress["maximum"] = max(item[2], 1)
                    self.dl_progress["value"] = item[1]
                    self.dl_counter_lbl.configure(text=f"{item[1]} / {item[2]}")
                elif a == "dl_count":
                    self.dl_counter_lbl.configure(text=f"{item[1]} / ?  (OK {item[1]}, GAGAL {item[2]})")
                elif a == "dl_done":
                    code, succ, fail = item[1], item[2], item[3]
                    self.dl_running = False
                    self.dl_start_btn.configure(state="normal")
                    self.dl_stop_btn.configure(state="disabled")
                    self.dl_skip_cb.configure(state="normal")
                    self._detect_dl_folder_state_only()
                    self.dl_status_lbl.configure(text=f"Selesai (kode {code}) — OK {succ}, GAGAL {fail}. Lihat log popup utk detail.")
                    # v5.0: append 'Selesai' ke popup (replaces inline dl_text).
                    self._ensure_dl_logwin().append(f"===== SELESAI (kode {code}) — OK {succ}, GAGAL {fail} =====")
                elif a == "dl_error":
                    self.dl_running = False
                    self.dl_start_btn.configure(state="normal")
                    self.dl_stop_btn.configure(state="disabled")
                    self.dl_skip_cb.configure(state="normal")
                    self._detect_dl_folder_state_only()
                    self.dl_status_lbl.configure(text="Gagal. Lihat log popup.")
                    # v5.0: append error ke popup (replaces inline dl_text).
                    self._ensure_dl_logwin().append(f"!!!!! {item[1]}")
                # ---- Download SJ GIS (v4.11) ----
                elif a == "sj_log":
                    # v5.0: route ke popup log window (replaces inline sj_text).
                    self._ensure_sj_logwin().append(item[1])
                elif a == "sj_progress":
                    cur, tot = item[1]
                    self.sj_progress["maximum"] = max(tot, 1)
                    self.sj_progress["value"] = cur
                    self.sj_counter_lbl.configure(text=f"{cur} / {tot}")
                elif a == "sj_ok":
                    # optional: bisa color-code baris log hijau; dikosongkan utk sekarang
                    pass
                elif a == "sj_fail":
                    # optional: bisa color-code baris log merah; dikosongkan utk sekarang
                    pass
                elif a == "sj_failed":
                    # v4.13: payload = list of failed kode strings (diparse dari
                    # marker 'SJ_RESULT_FAIL:' line oleh _sj_worker). Populate
                    # Card 4 'Kode Gagal'. Empty list -> placeholder text.
                    failed_list = item[1]
                    self._sj_set_failed_kodes(failed_list)
                elif a == "sj_done":
                    _, total = item[1]
                    self.sj_running = False
                    self.sj_start_btn.configure(state="normal")
                    self.sj_stop_btn.configure(state="disabled")
                    self.sj_progress["value"] = total if total else 0
                    self.sj_status_lbl.configure(text="Selesai — lihat log popup untuk detail")
                    # v5.0: append 'Selesai' ke popup (replaces inline sj_text).
                    self._ensure_sj_logwin().append("===== Selesai =====")
                # ---- Screen Shot Power BI (v4.14) ----
                elif a == "ss_log":
                    # v5.0: route ke popup log window (replaces inline ss_text).
                    self._ensure_ss_logwin().append(item[1])
                elif a == "ss_progress":
                    cur, tot, label = item[1]
                    self.ss_progress["maximum"] = max(tot, 1)
                    self.ss_progress["value"] = cur
                    self.ss_counter_lbl.configure(text=f"{cur} / {tot}")
                    self.ss_status_lbl.configure(text=f"{cur}/{tot} — {label}")
                elif a == "ss_done":
                    success, failed = item[1]
                    self.ss_running = False
                    self.ss_start_btn.configure(state="normal")
                    self.ss_stop_btn.configure(state="disabled")
                    if success is not None:
                        self.ss_status_lbl.configure(
                            text=f"Selesai — {success} berhasil, {failed} gagal. Lihat log popup.")
                        # v5.0: append 'Selesai' ke popup (replaces inline ss_text).
                        self._ensure_ss_logwin().append(
                            f"===== Selesai: {success} berhasil, {failed} gagal =====")
                    else:
                        # No DONE marker seen (subprocess terminated early or
                        # crashed without emitting DONE). Show 'Dihentikan'.
                        self.ss_status_lbl.configure(text="Dihentikan")
                        # v5.0: surface di popup juga (supaya user tau kenapa
                        # ga ada 'Selesai' line).
                        self._ensure_ss_logwin().append("===== Dihentikan =====")
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _detect_dl_folder_state_only(self):
        ok_unduh = bool(self.unduh_path) and os.path.isfile(self.unduh_path)
        self.dl_start_btn.configure(state="normal" if ok_unduh else "disabled")

    def _on_close(self):
        try:
            self._save_settings()
        except Exception:
            pass
        try:
            self._save_sj_settings()
        except Exception:
            pass
        self.stop_requested.set()
        self.dl_stop.set()
        self.sj_stop.set()
        self.ss_stop.set()
        try:
            if self.dl_proc is not None and self.dl_proc.poll() is None:
                self.dl_proc.terminate()
        except Exception:
            pass
        try:
            if self.sj_proc is not None and self.sj_proc.poll() is None:
                self.sj_proc.terminate()
        except Exception:
            pass
        try:
            if self.ss_proc is not None and self.ss_proc.poll() is None:
                self.ss_proc.terminate()
        except Exception:
            pass
        # v5.0: destroy popup log windows (DL, SJ, SS). Reusable popups withdraw
        # on hide() — but on app close, destroy them so tidak ada dangling
        # Toplevel references after main Tk window destroyed.
        for win in (self.dl_logwin, self.sj_logwin, self.ss_logwin):
            try:
                if win is not None and win.winfo_exists():
                    win.destroy()
            except Exception:
                pass
        self.destroy()

    # ================= OTOMASI IMPORT =================
    def start_automation(self, mode):
        if self.running:
            return
        if not self.db_map:
            messagebox.showwarning(APP_TITLE, "Database belum dimuat.\nLetakkan file Excel di folder 'Database COA&Keterangan' lalu klik Muat Ulang.", parent=self)
            return
        if not self.root_folder or not self.files:
            messagebox.showwarning(APP_TITLE, "Pilih Folder Induk terlebih dahulu.", parent=self)
            return
        ok_items = [p for p in self.plan if p["status"] == "OK"]
        if not ok_items:
            messagebox.showwarning(APP_TITLE, "Tidak ada file berstatus Cocok di preview.", parent=self)
            return
        try:
            self.run_date = self.get_date_str()
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e), parent=self)
            return

        # Confirmation dialog before starting automation
        mode_label = {"DRAFT": "Simpan Draf", "APPROVE": "Approve (Simpan Final)", "IMPORT": "Import Saja"}.get(mode, mode)
        if not messagebox.askokcancel(APP_TITLE,
                f"Import pada tanggal {self.run_date}?\n\n"
                f"Mode  : {mode_label}\n"
                f"File  : {len(ok_items)} siap diproses\n\n"
                f"Klik OK untuk mulai, atau Batal untuk batal.",
                parent=self):
            self.log("Dibatalkan oleh pengguna (tidak jalan).", "WARN")
            return

        self.run_mode = mode
        self.running = True
        self.stop_requested.clear()
        for b in self.start_buttons:
            b.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        win = self._ensure_logwin()
        win.clear()
        self.log_buffer.clear()
        win.set_file("Bersiap...")
        win.set_step(f"Mode: {mode} — menghubungkan ke Chrome...", "#fbbf24")
        win.set_progress(0, len(ok_items))
        win.show()

        self.log(f"Memulai otomasi. Mode: {mode}. Tanggal: {self.run_date}. File siap: {len(ok_items)}.")
        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.worker_thread.start()

    def stop_automation(self):
        if self.running:
            self.stop_requested.set()
            self.stop_btn.configure(state="disabled")
            self.log("Permintaan berhenti dikirim.", "WARN")

    def _run_worker(self):
        driver = None
        success_count, fail_count, skipped_count, global_idx = 0, 0, 0, 0
        fail_list = []
        mode_break = False
        try:
            if not bot.is_port_open(bot.DEBUG_PORT):
                self._queue_log("Chrome belum aktif, membuka Chrome...", "WARN")
                bot.launch_chrome_silent()
                for _ in range(15):
                    time.sleep(1)
                    if bot.is_port_open(bot.DEBUG_PORT):
                        break
                if not bot.is_port_open(bot.DEBUG_PORT):
                    raise RuntimeError("Gagal membuka Chrome debugging.\nJalankan MULAI.bat (di root folder) lalu login ke Accurate, atau klik tombol 'Buka Chrome 9222' di tab Download SJ GIS.")

            opt = Options()
            opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{bot.DEBUG_PORT}")
            try:
                driver = webdriver.Chrome(options=opt)
            except Exception as e:
                raise RuntimeError("Chrome Debugging belum aktif.\nJalankan MULAI.bat (di root folder), login ke Accurate, buka Penyesuaian Persediaan.\nAtau klik 'Buka Chrome 9222' di tab Download SJ GIS.\nDetail: " + str(e))

            self._queue_log("Terhubung ke Chrome.", "SUCCESS")
            self._queue_log("Mencari tab Penyesuaian Persediaan...")
            detect = bot.smart_detect_accurate_tab(driver, total_timeout=25)
            if not detect["found"]:
                raise RuntimeError(detect["message"])
            tab = detect["tab"]
            self._queue_log(f"Tab ditemukan: {tab['title'][:50]}", "SUCCESS")
            try:
                driver.switch_to.window(tab["handle"])
                driver.switch_to.default_content()
            except Exception:
                pass

            total_files = sum(1 for p in self.plan if p["status"] == "OK")
            for p in self.plan:
                if self.stop_requested.is_set():
                    self._queue_log("Proses dihentikan pengguna.", "WARN")
                    break
                if p["status"] != "OK":
                    skipped_count += 1
                    self._queue_log(f"Dilewati ({p['status']} — {p['reason']}): {p['filename']}", "WARN")
                    continue
                global_idx += 1
                item = {"account": p["coa"], "memo": p["memo"], "branch": p["branch"]}
                ok = bot.process_single_file(driver, p["path"], global_idx, total_files, item, self.run_date, self.run_mode, self._queue_log)
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
                    fail_list.append(p["filename"])
                    # Recovery: close the dirty tab + open a new blank form →
                    # prevents cascade failure + data numpuk (stacking). Without
                    # this, the next file fills the SAME dirty form (failed file's
                    # imported data still there) → potential data mixing or rejection.
                    if global_idx < total_files and not self.stop_requested.is_set():
                        bot.recover_after_failure(driver, self._queue_log)
                self.ui_queue.put(("progress", global_idx, total_files))

                if self.run_mode == bot.MODE_IMPORT:
                    remaining = total_files - global_idx
                    if remaining > 0:
                        skipped_count += remaining
                        self._queue_log(f"Mode Hanya Import: {remaining} file sisanya dilewati.", "WARN")
                    mode_break = True
                    break

            if not mode_break and not self.stop_requested.is_set():
                self._queue_log(f"Selesai. Berhasil: {success_count} | Gagal: {fail_count} | Dilewati: {skipped_count}",
                                "SUCCESS" if fail_count == 0 else "WARN")
            if fail_list:
                self._queue_log("File gagal: " + ", ".join(fail_list), "ERROR")
            self.ui_queue.put(("done", success_count, fail_count, skipped_count))
        except Exception as e:
            self._queue_log(str(e), "ERROR")
            self.ui_queue.put(("error", str(e)))
        finally:
            if driver is not None:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass


if __name__ == "__main__":
    print(f"=== {APP_TITLE} — ui_app.py v5.2 (pasangan accurate_bot.py v4.7) ===")
    app = AutoImportApp()
    app.mainloop()