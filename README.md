# Inventory Adjusment Tools

Kumpulan tool otomatisasi untuk **Accurate Online** (modul Penyesuaian Persediaan / Inventory Adjustment).
Dibangun dengan Python + Selenium. Dijalankan dari laptop via Chrome dengan **Remote Debugging**.

---

## Struktur Folder

```
Inventory-Adjusment/
├── 1. Download Draft IA/      # Tool untuk mengunduh draf IA per transaksi
├── 2. Import IA/              # Tool untuk mengimpor IA ke Accurate (UI Tkinter)
├── 3. Download SJ GIS/       # Tool download Surat Jalan dari modul Pemindahan Barang
└── 4. Screen Shot Power BI/  # Tool screenshot otomatis dashboard Power BI (Playwright)
```

> **Catatan:** Folder `3. Download SJ GIS` dan `4. Screen Shot Power BI`
> bisa dijalankan langsung dari tab di UI `2. Import IA/ui_app.py` (v4.14+).

---

## Persyaratan Umum (semua tool)

1. **Python 3.10+** terpasang dan `python` dapat dipanggil dari Command Prompt.
2. **Google Chrome** terpasang.
3. Jalankan tool via **`.bat`** yang sudah disediakan — dependency Python
   (`selenium`, `openpyxl`, `xlrd`) akan dipasang otomatis pada jalankan pertama.
4. Chrome dibuka dengan mode **Remote Debugging** (sudah diatur di dalam `.bat`):
   ```
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile" "https://accurate.id"
   ```
   Profil `C:\ChromeDebugProfile` akan menyimpan sesi login, jadi cukup login
   sekali dan tool berikutnya langsung terhubung.

---

## 1. Download Draft IA

Mengunduh file Excel draf Penyesuaian Persediaan per transaksi, dengan filter
"Pembuat Data".

| File | Fungsi |
|------|--------|
| `filter_pembuat_data.py` | Memfilter daftar transaksi berdasarkan Pembuat Data (mis. `RESTO.PWKTAM`, `RESTO.KWGGAL`) |
| `unduh_xls_loop.py` | Mengunduh XLS tiap baris transaksi yang sudah terfilter |
| `debug_filter.py` | Versi debug untuk filter (diagnostik) |
| `JALANKAN_FILTER.bat` | Filter daftar transaksi |
| `JALANKAN_UNDUH.bat` | Unduh XLS per transaksi (daftar sudah terfilter) |
| `JALANKAN_FULL.bat` | Pipeline lengkap: filter → unduh |
| `JALANKAN_DEBUG.bat` | Jalankan `debug_filter.py` |

**Cara pakai singkat:**
1. Jalankan `JALANKAN_FULL.bat` (atau `JALANKAN_FILTER.bat` lalu `JALANKAN_UNDUH.bat`).
2. Login Accurate Online di Chrome yang terbuka, buka halaman **LIST Penyesuaian Persediaan**.
3. Tekan tombol di Command Prompt untuk mulai.

---

## 2. Import IA

Aplikasi (UI Tkinter) untuk mengimpor draf IA ke Accurate Online secara otomatis,
dengan mapping COA & Keterangan dari database Excel.

| File | Fungsi |
|------|--------|
| `main.py` | Titik masuk aplikasi |
| `ui_app.py` | Tampilan UI (Tkinter) |
| `accurate_bot.py` | Logika otomasi Selenium + mapping COA |
| `MULAI_OTOMASI.bat` | Peluncur aplikasi (pasang dependency + buka Chrome) |
| `README.txt` | Dokumentasi internal tool |
| `ui_settings.json` | Pengaturan (mis. daftar cabang unduh) |
| `Database Import.xlsx` | Template database import |
| `Database COA&Keterangan/` | **Folder** database COA (dibaca otomatis oleh aplikasi). Letakkan semua file Excel COA di sini. |
| `Database COA&Keterangan.xlsx` | Salinan database COA (cadangan) |

**Cara pakai singkat:**
1. Jalankan `MULAI_OTOMASI.bat`.
2. Login Accurate Online di Chrome yang terbuka, buka **Penyesuaian Persediaan**.
3. Di UI: pilih Database Excel, Folder Induk, atur Tanggal.
4. Periksa preview mapping (hijau = siap, abu = dilewati, merah = tidak cocok).
5. Pilih mode: **Simpan Approve** / **Simpan Draft** / **Hanya Import**.

Detail lengkap mode & pengaman data ada di `2. Import IA/README.txt`.

---

## 3. Download SJ GIS

> **Status: TRIAL — tool final v1.**
> Download Surat Jalan dari modul Pemindahan Barang (database GiS) Accurate Online.

### Tool Final

| File | Fungsi |
|------|--------|
| `download_sj_gis.py` | Tool utama: search kode → klik baris → cetak (Ctrl+P) → unduh dari overlay. Reuse helper proven dari `unduh_xls_loop.py` (smart_click, JS_FIND_MARK, JS_FIND_PRINT, wait overlay, wait download) |
| `JALANKAN_SJ_GIS.bat` | Peluncur (pasang selenium + jalankan tool) |

**Cara pakai:**
1. Buka Chrome dengan remote debugging port 9222, login Accurate, buka **LIST Pemindahan Barang**.
2. Jalankan `JALANKAN_SJ_GIS.bat`.
3. Masukkan kode SJ (mis. `IT.2026.09.19805`), Enter.
4. Tunggu sampai `SELESAI! File: ...`. File tersimpan di folder `Downloads`.

**Alur tool:**
1. Connect Chrome port 9222 (attach ke session yg sudah login)
2. Cari frame list (iframe berisi `.slick-row` / `input[name=keyword]`)
3. Ketik kode di search box + klik `button.btn-search`
4. Tunggu baris berisi kode muncul di grid
5. Klik baris via `ActionChains` (trusted click, bukan synthetic JS)
6. Tunggu detail form terbuka
7. Trigger cetak: `Ctrl+P` dulu, fallback klik tombol Cetak
8. Tunggu overlay report + cari tombol Unduh (match "Unduh" — catch Unduh PDF/XLS/dst)
9. Klik Unduh + tunggu file baru di `~/Downloads` (`.pdf` / `.xls` / `.xlsx`)
10. Tutup overlay + tab detail

### File Deteksi (arsip — untuk debug struktur halaman)

| File | Fungsi |
|------|--------|
| `DETEKSI_HALAMAN.py` | Script diagnostik versi Python (backup) |
| `DETEKSI_HALAMAN.js` | Script diagnostik versi paste-to-Console (lebih cepat, skip Chrome port connect) |
| `JALANKAN_DETEKSI.bat` | Peluncur versi Python deteksi |

Dipakai saat pengembangan untuk membaca struktur DOM halaman. Tidak dipakai di alur final.

---

## 4. Screen Shot Power BI

> **Status: V16 — Optimized + Reliability Fix.**
> Screenshot otomatis dashboard Power BI (per page × per resto) memakai Playwright + Chromium.

### Cara pakai (via UI Import IA)

1. Jalankan `2. Import IA/MULAI_OTOMASI.bat` lalu buka tab **"Screen Shot Power BI"**.
2. Card **1. Konfigurasi** — isi:
   - **Power BI URL** (URL lengkap `app.powerbi.com/view?r=...`)
   - **Pages** — nomor halaman, mis. `19,20,21,22` atau range `19-22`
   - **Output Folder** — lokasi simpan screenshot
   - **Format** — `PNG` atau `PDF`
3. Card **2. Resto & Opsi** — ketik daftar resto (satu per baris) + centang opsi V16
   (Sequential page nav, Reuse stable screenshot, Merge final stability,
   Light recovery, Force-click Next Page, Smart resto transition — experimental).
4. Klik **▶ Mulai Screenshot**. Log muncul di Card **3. Log Screenshot**.
   Pakai **■ Hentikan** untuk stop, **📁 Buka Output** untuk buka folder hasil.

### Cara pakai (standalone, tanpa UI Import IA)

1. Jalankan `4. Screen Shot Power BI/START_HERE.vbs` (memanggil `launch.bat`).
   Script otomatis: bikin `.venv` lokal → pasang Playwright + Chromium → jalankan `app.py`.
2. Atau manual: `python app.py` (Tk UI standalone, sama seperti yang dipakai UI).

### Headless mode (`--cli`)

`app.py` mendukung `python app.py --cli` — mode headless yang baca `config.json`
lalu log progress ke **stdout** (untuk dipanggil sebagai subprocess oleh UI lain).
Marker yang dipancarkan:

- `PROGRESS: <cur>/<total> <label>` — per-job progress
- `DONE: success=<N> failed=<N>` — akhir batch
- `ERROR: <msg>` — fatal exception

Tab **Screen Shot Power BI** di `2. Import IA/ui_app.py` memakai mode `--cli`
ini: form di UI → simpan `config.json` → subprocess `app.py --cli` → parse
stdout → progressbar + log widget.

### File

| File | Fungsi |
|------|--------|
| `app.py` | Tool utama: Playwright Engine + Tk UI + `--cli` headless mode |
| `config.json` | Konfigurasi (URL, pages, restos, opsi V16, timing, output) — sumber kebenaran, dibaca + ditulis UI dan `app.py` |
| `requirements.txt` | `playwright`, `Pillow` |
| `launch.bat` | Setup `.venv` + Playwright + Chromium, lalu jalankan `app.py` |
| `RUN.bat` | Peluncur cepat (langsung `app.py` via `.venv`) |
| `START_HERE.vbs` | Peluncur Windows (klik double, panggil `launch.bat` tanpa jendela CMD) |
| `build_exe.bat` | (Opsional) Build standalone `.exe` via PyInstaller |
| `README_V14.txt` / `README_V15.txt` / `README_V16.txt` | Catatan rilis tiap versi |

### Dependensi

- **Python 3.10+** (recommend 3.13 x64)
- **Playwright** + **Chromium** — dipasang otomatis oleh `launch.bat` (atau
  oleh `ensure_playwright()` di `app.py` saat runtime bila belum ada)
- Tidak butuh Chrome Remote Debugging (tool ini pakai Chromium bawaan Playwright)

---

## Cara Download & Update

1. Buka halaman repo ini di GitHub.
2. Klik tombol **Code → Download ZIP** (atau `git clone` bila pakai Git).
3. Ekstrak zip, jalankan langsung file `.bat` yang sesuai.
4. Untuk mendapatkan update terbaru, ulangi unduhan zip dari GitHub.
