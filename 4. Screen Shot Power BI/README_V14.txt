SCREEN SHOT TOOLS V14
======================

V14 adalah pengembangan dari V13 untuk batch multi-page Power BI dengan model:
Page -> seluruh resto -> reset -> Page berikutnya.

Fokus reliability:
- Input page mendukung 19,20,21,22 atau 19-22.
- Setiap page dimulai dari fresh report state.
- Perpindahan Next Page diverifikasi berdasarkan perubahan state; jika DOM Power BI mengekspos nomor page, nomor tersebut juga diverifikasi.
- Final capture hanya dilakukan setelah report stabil + Resto terverifikasi + page terverifikasi (jika identitas page tersedia).
- Error satu resto tidak menghentikan batch; state di-cleanup dan bila perlu hard reset ke page yang sama.
- Error setup satu page tidak menghentikan page berikutnya.
- Output disimpan di output/Page N/<Resto>.png atau .pdf.
- Penulisan output bersifat transactional agar file lama tidak hilang ketika capture/PDF gagal.
- Manifest batch menyimpan hasil per page/resto dan stage error.
- Resto duplikat pada input dilewati.

Catatan:
- V14 mempertahankan metode deteksi slicer bernama Resto dari V13.
- Jika versi/layout Power BI tidak mengekspos numeric page identity ke DOM, V14 menggunakan verifikasi transisi + stability gate dan akan mencatat warning di log.
- Detail debug screenshot tersimpan di output/_debug.
