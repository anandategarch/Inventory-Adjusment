/* DETEKSI_HALAMAN.js — paste ke Console browser (F12) di halaman LIST Pemindahan Barang.
 * Cara pakai:
 *   1. Buka Accurate Online, login, buka halaman LIST Pemindahan Barang.
 *   2. Tekan F12 → tab Console.
 *   3. (Kalau halaman pakai iframe) pilih frame yg benar di dropdown "top" pojok kiri atas Console.
 *   4. Paste semua kode ini ke Console → Enter.
 *   5. Masukkan kode (default IT.2026.09.19805) → tunggu ~12 detik sampai "DETEKSI SELESAI".
 * Aman: cuma BACA + KETIK + KLIK 1 baris. Tidak download/simpan/hapus.
 * Output: otomatis disalin ke clipboard. Tinggal Ctrl+V ke chat.
 */
(async () => {
  const KODE = prompt('Kode SJ (default IT.2026.09.19805):', 'IT.2026.09.19805') || 'IT.2026.09.19805';
  const out = [];
  const log = (...a) => { out.push(a.join(' ')); console.log(...a); };
  const sep = (s) => log('\n' + '='.repeat(70) + '\n' + s + '\n' + '='.repeat(70));
  const delay = (ms) => new Promise(r => setTimeout(r, ms));
  const errs = [];
  window.addEventListener('error', e => errs.push((e.message||'') + ' @ ' + (e.filename||'') + ':' + (e.lineno||'')));

  const isVisible = (el) => {
    if (!el || el.disabled) return false;
    const st = getComputedStyle(el);
    if (st.display==='none' || st.visibility==='hidden' || parseFloat(st.opacity)===0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const setVal = (el, val) => {
    try {
      const proto = Object.getPrototypeOf(el);
      const desc = Object.getOwnPropertyDescriptor(proto, 'value') || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
      if (desc && desc.set) desc.set.call(el, val); else el.value = val;
    } catch(e) { el.value = val; }
    el.dispatchEvent(new Event('input', {bubbles:true}));
    el.dispatchEvent(new Event('change', {bubbles:true}));
  };

  const sendEnter = (el) => {
    const o = {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, cancelable:true};
    el.dispatchEvent(new KeyboardEvent('keydown', o));
    el.dispatchEvent(new KeyboardEvent('keypress', o));
    el.dispatchEvent(new KeyboardEvent('keyup', o));
  };

  const descEl = (el, i) => {
    const t = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 50);
    return `[${i}] <${el.tagName.toLowerCase()}> id="${el.id||''}" class="${(el.className||'').toString().slice(0,35)}" name="${el.name||''}" placeholder="${el.placeholder||''}" aria="${el.getAttribute('aria-label')||''}" type="${el.type||''}" text="${t}"`;
  };

  const dump = (label) => {
    sep(label);
    log('URL:', location.href);
    log('Title:', document.title);
    const sections = [
      ['INPUT', "input[type='text'],input[type='search'],input:not([type]),textarea", 25],
      ['BUTTON', "button,[role='button'],input[type='button'],input[type='submit']", 20],
      ['LINK', "a[href]", 20],
      ['GRID-HEADER', ".slick-header-column,.slick-column-name,th", 15],
      ['GRID-ROW', ".slick-row,tr,[role='row']", 20],
    ];
    for (const [name, sel, lim] of sections) {
      const els = [...document.querySelectorAll(sel)].filter(isVisible);
      log(`\n--- ${name} (${els.length} visible) ---`);
      els.slice(0, lim).forEach((e, i) => log('  ' + descEl(e, i)));
    }
    const all = [...document.querySelectorAll('a,span,div,li,label,td,button,p')];
    const k = KODE.toUpperCase();
    const rel = [];
    for (const el of all) {
      const t = (el.innerText || '').trim();
      if (!t) continue;
      const u = t.toUpperCase();
      if (u.includes(k) || u.includes('UNDUH') || u.includes('DOWNLOAD') || u.includes('CETAK') || u.includes('PRINT') || u.includes('PDF') || u.includes('XLS') || u.includes('EKSPOR')) {
        if (isVisible(el)) {
          rel.push({tag: el.tagName, id: el.id, cls: (el.className||'').toString().slice(0,40), text: t.slice(0,70)});
          if (rel.length >= 60) break;
        }
      }
    }
    log(`\n--- TEKS RELEVAN (kode/UNDUH/CETAK/DOWNLOAD/PDF/XLS) (${rel.length}) ---`);
    rel.forEach((x, i) => log(`  [${i}] <${x.tag}> id="${x.id}" class="${x.cls}" text="${x.text}"`));
  };

  log('Kode:', KODE);
  sep('STEP 1: SNAPSHOT SEBELUM SEARCH');
  dump('SEBELUM SEARCH');

  const inputs = [...document.querySelectorAll("input[type='search'],input[type='text'],input:not([type]),textarea")];
  let chosen = null;
  for (const el of inputs) {
    if (!isVisible(el)) continue;
    const s = ((el.placeholder||'') + ' ' + (el.getAttribute('aria-label')||'') + ' ' + (el.name||'') + ' ' + (el.id||'') + ' ' + (el.className||'')).toLowerCase();
    if (['search','cari','filter','nomor','pencarian'].some(k => s.includes(k))) { chosen = el; break; }
  }
  if (!chosen) chosen = inputs.find(isVisible);

  if (chosen) {
    sep('STEP 2: KETIK KODE + ENTER');
    log('Search box:', descEl(chosen, 0));
    chosen.focus(); chosen.click();
    setVal(chosen, KODE);
    await delay(200);
    sendEnter(chosen);
    log('OK diketik + enter');
  } else {
    log('TIDAK ADA INPUT VISIBLE. Coba ganti frame di dropdown "top" pojok kiri atas Console, lalu paste ulang.');
  }

  log('\nTunggu 5 detik...');
  await delay(5000);
  sep('STEP 3: SNAPSHOT SETELAH SEARCH');
  dump('SETELAH SEARCH');

  sep('STEP 4: CARI + KLIK BARIS BERISI KODE');
  const rows = [...document.querySelectorAll(".slick-row,tr,[role='row']")];
  log(`Cari baris berisi kode di ${rows.length} baris...`);
  let clicked = false;
  for (const r of rows.slice(0, 50)) {
    const t = (r.innerText || '').trim();
    if (t.includes(KODE)) { log(`>> klik baris: ${t.slice(0,70)}`); r.click(); clicked = true; break; }
  }
  if (!clicked) {
    const els = [...document.querySelectorAll('*')];
    for (const el of els.slice(0, 2000)) {
      if (isVisible(el) && (el.innerText || '').includes(KODE)) {
        log(`>> klik elemen: <${el.tagName.toLowerCase()}> ${(el.innerText||'').slice(0,50)}`);
        el.click(); clicked = true; break;
      }
    }
  }
  if (!clicked) log('Tidak ada baris/elemen berisi kode. Kirim screenshot manual halaman setelah search.');

  log('\nTunggu 5 detik...');
  await delay(5000);
  sep('STEP 5: SNAPSHOT SETELAH KLIK BARIS');
  dump('SETELAH KLIK BARIS');

  sep('CONSOLE ERRORS (selama script jalan)');
  if (errs.length === 0) log('(tidak ada)');
  else errs.slice(0, 30).forEach(e => log('  -', e));

  sep('DETEKSI SELESAI');
  log('Output:', out.length, 'baris');
  try {
    await navigator.clipboard.writeText(out.join('\n'));
    log('✓ Output SUDAH DISALIN ke clipboard. Tinggal Ctrl+V di chat ke saya.');
  } catch(e) {
    log('Clipboard gagal:', e.message, '| Copy manual: select all di Console + Ctrl+C.');
  }
})();
