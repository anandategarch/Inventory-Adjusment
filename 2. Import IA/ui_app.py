"""
ui_app.py — tampilan aplikasi Import IA (v4.10, pasangan accurate_bot.py v4.7).
Tab: Otomasi | Database COA & Keterangan | Download Draft IA.
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

import accurate_bot as bot

REQUIRED_BOT_VERSION = "4.7"
if getattr(bot, "BOT_VERSION", None) != REQUIRED_BOT_VERSION:
    raise RuntimeError(
        "Versi file TIDAK SEPASANG.\n\n"
        f"ui_app.py ini butuh accurate_bot.py versi {REQUIRED_BOT_VERSION},\n"
        f"tapi terdeteksi versi: {getattr(bot, 'BOT_VERSION', 'LAMA')}.\n\n"
        "Salin ulang kedua file dari paket yang sama, lalu hapus copy lama."
    )

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
        self.notebook.add(tab_auto, text="  Otomasi  ")
        self.notebook.add(tab_db, text="  Database COA & Keterangan  ")
        self.notebook.add(tab_dl, text="  Download Draft IA  ")

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
        dlview.rowconfigure(1, weight=1)

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
        self.dl_stop_btn.pack(side="left")

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

        log_card = self._card(dlview, "3. Log Download")
        log_card.grid(row=1, column=0, columnspan=2, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        dl_log_wrap = tk.Frame(log_card, bg=C_TERM_BG)
        dl_log_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(4, 12))
        dl_log_wrap.columnconfigure(0, weight=1)
        dl_log_wrap.rowconfigure(0, weight=1)
        self.dl_text = tk.Text(dl_log_wrap, bg=C_TERM_BG, fg="#dbeafe", insertbackground="white",
                               relief="flat", font=F_LOG, wrap="word", state="disabled")
        self.dl_text.grid(row=0, column=0, sticky="nsew")
        dl_sb = ttk.Scrollbar(dl_log_wrap, orient="vertical", command=self.dl_text.yview)
        dl_sb.grid(row=0, column=1, sticky="ns")
        self.dl_text.configure(yscrollcommand=dl_sb.set)
        self.dl_text.bind("<MouseWheel>", self._dl_text_wheel)
        self.dl_text.bind("<Button-4>", self._dl_text_wheel)
        self.dl_text.bind("<Button-5>", self._dl_text_wheel)
        ttk.Button(log_card, text="Bersihkan", command=self._dl_clear).grid(row=2, column=0, sticky="e", padx=14, pady=(0, 10))

    # ================= HELPERS =================
    def _db_tree_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.db_tree.yview_scroll(steps, "units")

    def _tree_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.tree.yview_scroll(steps, "units")

    def _dl_text_wheel(self, e):
        steps = _wheel_steps(e)
        if steps:
            self.dl_text.yview_scroll(steps, "units")

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
        cands = [os.path.join(parent, DL_FOLDER_NAME), os.path.join(app_dir, DL_FOLDER_NAME)]
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
    def _dl_log_line(self, line):
        self.dl_text.configure(state="normal")
        self.dl_text.insert("end", line + "\n")
        self.dl_text.see("end")
        self.dl_text.configure(state="disabled")

    def _dl_clear(self):
        self.dl_text.configure(state="normal")
        self.dl_text.delete("1.0", "end")
        self.dl_text.configure(state="disabled")

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
        self.plan = bot.build_file_plan(self.db_map, self.files)
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
                    self._dl_log_line(item[1])
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
                    self.dl_status_lbl.configure(text=f"Selesai (kode {code}) — OK {succ}, GAGAL {fail}.")
                    self._dl_log_line(f"===== SELESAI (kode {code}) — OK {succ}, GAGAL {fail} =====")
                elif a == "dl_error":
                    self.dl_running = False
                    self.dl_start_btn.configure(state="normal")
                    self.dl_stop_btn.configure(state="disabled")
                    self.dl_skip_cb.configure(state="normal")
                    self._detect_dl_folder_state_only()
                    self.dl_status_lbl.configure(text="Gagal. Lihat log.")
                    self._dl_log_line(f"!!!!! {item[1]}")
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
        self.stop_requested.set()
        self.dl_stop.set()
        try:
            if self.dl_proc is not None and self.dl_proc.poll() is None:
                self.dl_proc.terminate()
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
                    raise RuntimeError("Gagal membuka Chrome debugging.\nJalankan MULAI_OTOMASI.bat lalu login ke Accurate.")

            opt = Options()
            opt.add_experimental_option("debuggerAddress", f"127.0.0.1:{bot.DEBUG_PORT}")
            try:
                driver = webdriver.Chrome(options=opt)
            except Exception as e:
                raise RuntimeError("Chrome Debugging belum aktif.\nJalankan MULAI_OTOMASI.bat, login, buka Penyesuaian Persediaan.\nDetail: " + str(e))

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
    app = AutoImportApp()
    app.mainloop()