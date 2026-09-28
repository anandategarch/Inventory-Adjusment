# Inventory Adjusment Tools

Kumpulan tool otomatisasi untuk **Accurate Online** + **Power BI**. Dijalankan dari satu UI terpadu.

## Cara Pakai

### 1. Setup (sekali saja)
Jalankan `SETUP.bat` di root folder. Ini install semua dependencies:
- selenium, openpyxl, xlrd (Accurate automation + Excel)
- playwright + Chromium browser (Power BI screenshot)
- Pillow (image processing)

### 2. Jalankan (setiap kali)
Jalankan `MULAI.bat` di root folder. UI kebuka dengan 5 tab:

| Tab | Tool | Fungsi |
|-----|------|--------|
| Otomasi | Import IA | Import Inventory Adjustment ke Accurate (UI Tkinter + Selenium) |
| Database COA & Keterangan | View DB Excel | Lihat/muat database COA + Keterangan |
| Download Draft IA | unduh_xls_loop.py | Download draf IA per transaksi (filter + unduh XLS) |
| Download SJ GIS | download_sj_gis.py | Download Surat Jalan dari Pemindahan Barang (search kode → klik → download + rename) |
| Screen Shot Power BI | app.py V16 | Screenshot dashboard Power BI per page × per resto |

## Struktur Folder

```
Inventory-Adjusment/
├── MULAI.bat              ← ENTRY POINT (buka UI 5 tab)
├── SETUP.bat              ← One-time install dependencies
├── README.md
├── 1. Download Draft IA/  ← Tool 1: filter + unduh XLS draf IA
│   ├── unduh_xls_loop.py
│   └── filter_pembuat_data.py
├── 2. Import IA/           ← Tool 2: UI utama + Import IA bot
│   ├── ui_app.py           (UI 5 tab — v4.15, entry point langsung)
│   ├── accurate_bot.py     (Import IA logic)
│   └── ui_settings.json    (saved settings)
├── 3. Download SJ GIS/     ← Tool 3: download SJ dari Pemindahan Barang
│   ├── download_sj_gis.py  (v8.13 — env var support)
│   ├── DETEKSI_HALAMAN.py  (diagnostic)
│   ├── DETEKSI_HALAMAN.js  (diagnostic — paste to console)
│   └── JALANKAN_DETEKSI.bat (diagnostic launcher)
└── 4. Screen Shot Power BI/ ← Tool 4: screenshot Power BI dashboard
    ├── app.py              (V16 — + --cli mode for UI subprocess)
    ├── config.json         (Power BI URL, pages, restos, options)
    ├── requirements.txt    (playwright, Pillow)
    ├── README_V16.txt
    └── build_exe.bat       (packaging to .exe — niche)
```

## Tool Details

### 1. Download Draft IA
Download file Excel draf Penyesuaian Persediaan per transaksi dari Accurate Online, dengan filter "Pembuat Data". Pakai Selenium + Chrome Remote Debugging.
- **Via UI:** Tab "Download Draft IA" → setup cabang → Mulai
- **Standalone (optional):** `python unduh_xls_loop.py` (perlu Chrome debugging port 9222)

### 2. Import IA
Import Inventory Adjustment ke Accurate Online. UI Tkinter + Selenium, dengan mapping COA & Keterangan dari database Excel.
- **Via UI:** Tab "Otomasi" → pilih database + folder + tanggal → pilih mode (Simpan Approve / Draft / Hanya Import)

### 3. Download SJ GIS
Download Surat Jalan dari modul Pemindahan Barang Accurate Online. Search kode SJ → klik baris → buka detail → download dokumen + rename ke `{kode}_{tanggal}_{cabang}.ext`.
- **Via UI:** Tab "Download SJ GIS" → paste kodes → Mulai
- **Standalone (optional):** `python download_sj_gis.py` (prompts for kodes via stdin)

### 4. Screen Shot Power BI
Screenshot dashboard Power BI per page × per resto. Pakai Playwright (headless Chromium). Output PNG/PDF di folder output.
- **Via UI:** Tab "Screen Shot Power BI" → isi Power BI URL + pages + restos → Mulai
- **Standalone (optional):** `python app.py` (original Tk UI standalone)
- **Setup Playwright:** `SETUP.bat` handles install. Atau manual: `pip install playwright && playwright install chromium`

## Persyaratan Umum

- **Python 3.10+**
- **Google Chrome** terpasang (untuk tool 1, 2, 3)
- **Chromium** (auto-install via Playwright untuk tool 4)
- Jalankan `SETUP.bat` sekali untuk install semua dependencies

## Chrome Remote Debugging (Tool 1, 3)

Tool 1 (Download Draft IA) dan Tool 3 (Download SJ GIS) butuh Chrome dengan remote debugging:
```
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile" "https://accurate.id"
```
Login Accurate sekali di Chrome tersebut (session persist di `C:\ChromeDebugProfile`). Setelah itu, tool auto-attach ke Chrome yang sudah login.

**Tip:** Tab "Download SJ GIS" di UI punya tombol "🌐 Buka Chrome 9222" yang launch Chrome otomatis.

## Cara Download & Update

1. Download ZIP repo: https://github.com/anandategarch/Inventory-Adjusment/archive/refs/heads/main.zip
2. Ekstrak
3. Jalankan `SETUP.bat` (sekali)
4. Jalankan `MULAI.bat` (setiap kali)

## Changelog

- **v4.14** (ui_app.py): 5 tab unified UI (Otomasi + Database + Download Draft IA + Download SJ GIS + Screen Shot Power BI)
- **v8.13** (download_sj_gis.py): env var support + Kode Gagal retry feature
- **V16** (app.py): reliability fix + --cli mode for UI subprocess
