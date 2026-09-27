SCREEN SHOT TOOLS V15 — OPTIMIZED
==================================

V15 adalah pengembangan dari V14 dengan fokus: **percepat batch tanpa
mengurangi akurasi**. Semua verification step V14 (stability gate, resto
display match, page identity check, transactional output, manifest)
dipertahankan. Yang dihilangkan hanya wait yang redundan dan kerja double.

Estimasi kecepatan untuk batch 4 page × 4 resto (16 job):
  V14: ~8-12 menit
  V15: ~3-5 menit  (hemat ~50-60%)


7 OPTIMISASI V15
----------------

1. Sequential Page Navigation  [opt_sequential_page_nav]
   V14 me-reload URL + klik Next dari page 1 untuk SETIAP page.
   Untuk pages [19,20,21,22]: 4 reload + 78 Next-click.
   V15: reload 1× ke page 19, lalu Next-click 3× ke 20,21,22.
   Hemat: ~3-5 menit untuk contoh di atas.
   Setiap Next-click tetap diverifikasi (transition change + page identity).

2. Smart Resto Transition  [opt_smart_resto_transition]
   V14 selalu clear selection → search → select untuk setiap resto.
   V15: jika slicer menunjukkan single value, langsung search + click value
   baru (Power BI single-select auto-replace). Clear hanya jika:
     - slicer "Multiple selections", atau
     - direct select gagal verifikasi (slicer ternyata multi-select).
   Hemat: ~3-5 detik per resto transition.
   Verifikasi slicer display == target tetap dilakukan → akurasi sama.

3. Reuse Stable Screenshot  [opt_reuse_stable_screenshot]
   V14 mengambil screenshot 2× per resto: satu untuk stability hash,
   satu untuk capture output.
   V15: simpan bytes screenshot dari cycle stability terakhir, pakai untuk
   output. Aman karena stability gate sudah konfirmasi 2+ snapshot identik
   = bytes itu IS the final rendered state.
   Hemat: ~200-400ms per resto.

4. Merge Final Stability Check  [opt_merge_final_stability]
   V14: set_filter() sudah wait_for_powerbi_stable + verify_single_resto,
   lalu run() memanggil keduanya LAGI ("final check"). Redundan.
   V15: skip duplikat. Page identity check tetap dilakukan di run().
   Hemat: ~2-4 detik per resto.
   Jika paranoid, set opt_merge_final_stability=false untuk kembali ke V14.

5. Stability Gate lebih cepat
   V14: min_wait_ms=1500, poll_ms=500, required_cycles=3 → ~3s per cek.
   V15: min_wait_ms=500,  poll_ms=400, required_cycles=2 → ~1.3s per cek.
   Masih mengonfirmasi 2 snapshot identik berturut-turut (800ms stabilitas).
   Hemat: ~1.7s × ~32 stability check = ~55 detik.

6. Fixed wait dipangkas
   wait_dropdown_open_ms:   900 → 500
   wait_after_search_ms:   1600 → 900
   wait_after_select_ms:    700 → 400
   wait_after_uncheck_ms:  1200 → 600
   wait_clear_search_ms:    350 → 200
   wait_escape_ms:          700 → 350
   page_load_wait_ms:      8000 → 3000 (stability gate covers the rest)
   Hemat: ~2-3s per resto.

7. Page identity cache
   _get_current_page_number() di-cache selama satu iterasi page.
   Hindari DOM scan berulang yang mahal.
   Cache di-invalidate setiap navigasi.


CARA PAKAI
----------

  1. Salin folder ini ke lokasi kerja Anda.
  2. Jalankan:  python app.py   (atau klik RUN.bat / START_HERE.vbs)
  3. UI baru memiliki 4 checkbox optimization — bisa dinonaktifkan
     per-feature jika environment Power BI Anda memerlukan fallback V14.
  4. config.json berisi semua timing; bisa di-tune lebih lanjut.

Tidak ada dependency baru. requirements.txt sama dengan V14
(playwright + Pillow).


FALLBACK KE V14
---------------

Set di config.json:
  "opt_sequential_page_nav": false,
  "opt_smart_resto_transition": false,
  "opt_reuse_stable_screenshot": false,
  "opt_merge_final_stability": false,
  "opt_skip_page_load_fixed_wait": false,

Dan kembalikan timing V14:
  "page_load_wait_ms": 8000,
  "stability_min_wait_ms": 1500,
  "stability_poll_ms": 500,
  "stability_required_cycles": 3,
  "wait_dropdown_open_ms": 900,
  "wait_after_search_ms": 1600,
  "wait_after_select_ms": 700,
  "wait_after_uncheck_ms": 1200,
  "wait_clear_search_ms": 350,
  "wait_escape_ms": 700,


APA YANG TIDAK BERUBAH (akurasi dijaga)
---------------------------------------

  ✓ Hard reset (fresh URL load) untuk page pertama dan error recovery
  ✓ Setiap Next-click diverifikasi (transition + page identity)
  ✓ Stability gate sebelum capture (loading=0 + 2 snapshot identik)
  ✓ verify_single_resto: slicer display harus == target exactly
  ✓ Page identity verification di run()
  ✓ Transactional output (temp file → os.replace → final)
  ✓ Manifest batch JSON dengan stage error
  ✓ Error satu resto tidak menghentikan batch
  ✓ Error setup satu page tidak menghentikan page berikutnya
  ✓ Recovery: hard reset setelah resto error
  ✓ Debug screenshot di output/_debug
  ✓ Resto duplikat di-skip


CATATAN TEKNIS
--------------

  - Pages di-sort ascending oleh parse_pages() (sudah sejak V14).
    Sequential nav mengharuskan ascending; output file tetap per-folder
    (Page N/<Resto>.png) jadi urutan tidak mempengaruhi hasil.

  - Jika sequential nav gagal di tengah (mis. Next button disabled),
    V15 otomatis fallback ke full reset untuk page tersebut.

  - Smart resto transition bisa gagal jika slicer adalah multi-select.
    Verifikasi akan mendeteksi "Multiple selections" dan otomatis
    fallback ke clear-then-select. Tidak ada risiko akurasi.

  - Reuse screenshot aman karena stability gate hanya return setelah
    2+ snapshot identik (loading=0, DOM hash sama, screenshot hash sama).
    Bytes terakhir = representasi state final yang terverifikasi.
