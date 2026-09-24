# Inventory Adjusment Tools

Kumpulan tool otomatisasi untuk **Accurate Online** (modul Penyesuaian Persediaan / Inventory Adjustment).
Dibangun dengan Python + Selenium. Dijalankan dari laptop via Chrome dengan **Remote Debugging**.

---

## Struktur Folder

```
Inventory-Adjusment/
├── 1. Download Draft IA/      # Tool untuk mengunduh draf IA per transaksi
├── 2. Import IA/              # Tool untuk mengimpor IA ke Accurate (UI Tkinter)
└── 3. Download SJ GIS/       # (kosong — akan diisi nanti)
```

> **Catatan:** Folder `3. Download SJ GIS` sengaja dikosongkan dulu.
> Tooling-nya akan ditambahkan kemudian.

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

## Cara Download & Update

1. Buka halaman repo ini di GitHub.
2. Klik tombol **Code → Download ZIP** (atau `git clone` bila pakai Git).
3. Ekstrak zip, jalankan langsung file `.bat` yang sesuai.
4. Untuk mendapatkan update terbaru, ulangi unduhan zip dari GitHub.
