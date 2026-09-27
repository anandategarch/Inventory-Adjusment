SCREEN SHOT TOOLS V16 — RELIABILITY FIX
========================================

V16 memperbaiki 3 bug kritis dari V15 yang ditemukan di production run:

  1. Smart Resto Transition GAGAL total — search input tidak ter-clear.
  2. Next Page click timeout 5000ms (Power BI overlay intercept click).
  3. Recovery terlalu berat — full reload (~30s) setiap resto error.

Hasil production V15 (Page 19-20, 19 resto):
  - Page 19: GAGAL TOTAL (19/19 resto skip, Next-click hang di page ~16)
  - Page 20: 19 resto butuh recovery beruntun (smart transition salah match)
  - Estimasi waktu: ~12+ menit (lebih lambat dari V14!)

V16 target: batch 2 page × 19 resto (38 job) selesai ~4-6 menit, ANDALAN.


BUG 1: Smart Resto Transition  →  DEFAULT OFF + FIX SEARCH CLEAR
-----------------------------------------------------------------

Gejala di log V15:
  [14:27:45] ✅ Ditemukan pilihan "1049.DPKMAR1042.KWGGAL" di dropdown Resto
                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                          text gabungan nilai baru + lama!

Akar masalah:
  - Power BI pakai Angular custom input untuk search slicer Resto.
  - `Control+A` di V14/V15 TIDAK select-all di input Angular tsb.
  - Saat ketik "1049.DPKMAR", text di-append ke "1042.KWGGAL" (sisa search lama).
  - `_find_resto_row` pakai `includes(value)` (substring match).
  - Cocok dengan CONTAINER yang berisi dua nilai → klik container →
    tidak select apa-apa → slicer kembali ke "All" → verifikasi gagal.

Fix V16:
  (a) `opt_smart_resto_transition` default = FALSE.
      Pakai V14 clear-then-select path (proven reliable).
      Bisa di-enable via checkbox (experimental) untuk test environment Anda.

  (b) `_clear_resto_search` di-rewrite dengan 2 tier:
      - Tier 1: JS native value setter (Object.getOwnPropertyDescriptor)
        bypass Angular change detection, trigger 'input' + 'change' event.
        Ini teknik yg dipakai React/Angular testing libraries.
      - Tier 2: triple-click + Delete (fallback keyboard).

  (c) `_find_resto_row` tambah parameter `exact=True`:
      - exact=True: row text harus SAMA PERSIS dengan value.
      - Hindari match container "1049.DPKMAR1042.KWGGAL".
      - `_select_resto_direct` pakai exact=True dulu, fallback ke substring
        hanya jika text mengandung value (bukan container campuran).


BUG 2: Next Page Click Timeout  →  3-TIER CLICK FALLBACK
---------------------------------------------------------

Gejala di log V15:
  Locator.click: Timeout 5000ms exceeded.
  - element is visible, enabled and stable
  - performing click action  ← hang di sini, tidak pernah selesai

Akar masalah:
  - Power BI punya overlay/iframe yang intercept mouse click.
  - Playwright click menunggu event 'click' yang tidak pernah datang.
  - 5000ms timeout → raise → page setup gagal → semua resto di-skip.

Fix V16: method baru `_click_next_button` dengan 3 tier:
  Tier 1: normal click (timeout 5000ms, respect actionability)
  Tier 2: force=True (timeout 3000ms, skip actionability, dispatch at coords)
  Tier 3: dispatch_event('click') (synthetic JS event, no mouse)
  Tier 2+3 bypass overlay intercept.

  Config: opt_force_click_next_page=true (default ON).
  Log akan menampilkan: "↪ Next Page diklik via metode: force" / "dispatch".


BUG 3: Recovery Terlalu Berat  →  LIGHT RECOVERY
-------------------------------------------------

Gejala: setiap resto error → `_hard_reset_page` (reload URL + 20+ Next-click).
  - Page 20 ada 19 resto error × ~30s recovery = ~9.5 menit terbuang!

Akar masalah:
  - V15 error handler langsung call `_hard_reset_page`.
  - `_recover_after_resto_error` ADA (coba clear dulu) tapi TIDAK DIPANGGIL
    di blok recovery & error handler run().

Fix V16:
  (a) Recovery & error handler di run() sekarang call `_recover_after_resto_error`
      (bukan `_hard_reset_page` langsung).

  (b) `_recover_after_resto_error` di-rewrite:
      - Jika opt_light_recovery=true (default):
        1. clear_all_resto_selections (~3-5s) — clear slicer, no reload.
        2. Jika clear OK → return True (cukup, lanjut resto berikutnya).
        3. Jika clear gagal → fallback _hard_reset_page.
      - Jika opt_light_recovery=false:
        - Legacy V15 behavior (always hard reset).

  Hemat: ~25s per resto error (dari ~30s → ~5s).


DEFAULTS V16 (apa yang berubah dari V15)
----------------------------------------

  opt_smart_resto_transition: true  →  false   (bug 1)
  opt_light_recovery:         (new)     true   (bug 3)
  opt_force_click_next_page:  (new)     true   (bug 2)
  next_page_click_timeout_ms:         (new) 5000
  next_page_force_click_timeout_ms:   (new) 3000

Yang TIDAK berubah dari V15:
  opt_sequential_page_nav:      true   (bekerja dengan baik di log)
  opt_reuse_stable_screenshot:  true   (bekerja dengan baik)
  opt_merge_final_stability:    true   (bekerja dengan baik)
  Semua timing waits:           sama dengan V15


UI V16
------

Panel checkbox sekarang 2 baris (6 opsi):
  Row 1: [x] Sequential page nav   [x] Reuse stable screenshot   [x] Merge final stability
  Row 2: [x] Light recovery        [x] Force-click Next Page     [ ] Smart resto transition (experimental)

Smart resto transition diberi label "(experimental)" karena可靠性 tergantung
layout Power BI spesifik Anda. Default OFF; enable hanya untuk testing.


CARA PAKAI
----------

  1. Extract zip ke folder kerja.
  2. Hapus config.json lama (V15) agar V16 menulis default baru.
     Atau edit config.json manual: set opt_smart_resto_transition=false.
  3. Jalankan: python app.py
  4. Klik START MULTI-PAGE (V16).

Tidak ada dependency baru. requirements.txt sama dengan V14/V15
(playwright + Pillow).


FALLBACK KE V14 (jika V16 masih bermasalah)
-------------------------------------------

Set di config.json:
  "opt_sequential_page_nav": false,
  "opt_smart_resto_transition": false,
  "opt_reuse_stable_screenshot": false,
  "opt_merge_final_stability": false,
  "opt_light_recovery": false,
  "opt_force_click_next_page": false,
  "opt_skip_page_load_fixed_wait": false,
  "page_load_wait_ms": 8000,
  "stability_min_wait_ms": 1500,
  "stability_poll_ms": 500,
  "stability_required_cycles": 3,

Ini akan membuat V16 behave identik dengan V14 (paling reliable, paling lambat).


ESTIMASI PERFORMANCE V16
------------------------

Untuk batch 2 page × 19 resto (38 job), asumsi Page 19 & 20:
  V14: ~16-20 menit (4 reload + 76 Next-click + wait berlebih)
  V15: GAGAL (bug 1+2 menyebabkan hampir semua resto error)
  V16: ~4-6 menit
    - 1 reload URL + 19 Next-click (sequential, bukan 4 reload + 76)
    - Light recovery hanya jika ada error (bukan hard reset setiap error)
    - Force-click fallback mengatasi Next-click hang
    - Smart transition OFF → pakai clear-then-select yang proven reliable

Hemat vs V14: ~70%. Hemat vs V15-buggy: V15 tidak usable.


CATATAN TEKNIS
--------------

  - Force-click (Tier 2) memakai Playwright `click(force=True)` yang
    skip actionability checks (visible, enabled, stable). Aman karena
    kita sudah verify button exists via _find_next_page_locator.

  - dispatch_event (Tier 3) fire synthetic 'click' event langsung ke
    element. Tidak ada mouse movement, tidak ada actionability check.
    Fallback terakhir jika overlay masih intercept.

  - Light recovery clear_all_resto_selections() akan baca slicer display.
    Jika "Multiple selections" → hard reset (clear tidak aman).
    Jika single value → uncheck value tersebut (~3-5s).
    Jika "All" → sudah bersih, return langsung.

  - Smart transition (experimental) sekarang pakai:
    1. JS value setter untuk clear (bukan Control+A)
    2. exact=True di _find_resto_row (bukan substring)
    Lebih reliable dari V15, tapi tetap default OFF sampai proven di
    environment Anda.
