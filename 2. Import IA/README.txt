IMPORT IA (v4.5)
================
Isi folder aplikasi (5 file):
- main.py            : titik masuk
- ui_app.py          : tampilan (UI)
- accurate_bot.py    : logika otomasi Selenium + mapping
- MULAI_OTOMASI.bat  : peluncur
- README.txt         : dokumen ini

Cara menjalankan:
1. Double-click MULAI_OTOMASI.bat
2. Login Accurate Online di Chrome yang terbuka, buka Penyesuaian Persediaan
3. Di UI: pilih Database Excel, Folder Induk, atur Tanggal
4. Periksa preview mapping (hijau=siap, abu=dilewati, merah=tidak cocok)
5. Klik salah satu mode: Simpan Approve / Simpan Draft / Hanya Import

Mode:
- Simpan Approve : simpan final via menu Simpan (tanpa CTRL+S, aman dari dialog browser)
- Simpan Draft   : simpan sebagai draf
- Hanya Import   : isi + import saja, transaksi dibiarkan terbuka; batch berhenti 1 file

Pengaman data (v4.5):
- Form dipastikan bersih/baru sebelum tiap file (klik Buat Baru bila perlu)
- Tanggal diverifikasi terbaca sesuai pilihan UI
- Akun diverifikasi SAMA dengan COA target (jika beda, file digagalkan)
- Cabang di-reset lalu diverifikasi SAMA dengan cabang dari nama file
- Pop-up panduan upload diabaikan; hanya pop-up hasil/error/stok yang diproses
- Peringatan stok pasca-simpan diklik LANJUTKAN otomatis (kondisional)

Database: semua sheet yang punya baris COA dipakai; baris = COA (B) + Keterangan (C);
C1 = kode cabang (info). Keterangan final = inti sheet + _<cabang file> + _<periode sheet>.
File dilewati: nama mengandung Raw Material / Deviasi / Adjustment Stock.