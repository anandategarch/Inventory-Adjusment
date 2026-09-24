/* RECORDER.js — "Record macro" kayak Excel macro recorder.
 * Paste ke Console browser (F12) di halaman LIST Pemindahan Barang.
 * Lalu kerjakan MANUAL: search kode -> klik baris -> klik tab Dokumen -> klik Unduh PDF.
 * Recorder ngerecord SEMUA: elemen diklik (selector + id + name + class + onclick),
 * input value, AJAX request, iframe baru, window.open, console message.
 *
 * Selesai kerja manual, KETIK di Console:  __recorderExport()
 * Output ke-clipboard. Paste ke chat ke saya. Dari situ saya tulis tool final.
 *
 * Cara stop record:  __recorderStop()
 * Cara lihat count:  __recorderCount()
 */
(function () {
  if (window.__recorder) {
    console.log('[REC] Sudah jalan. Total events:', window.__recorder.log.length);
    console.log('[REC] Export: __recorderExport() | Stop: __recorderStop()');
    return;
  }
  var log = [];
  var t0 = Date.now();
  function record(type, data) {
    var entry = { ms: Date.now() - t0, type: type };
    for (var k in data) entry[k] = data[k];
    log.push(entry);
    try { console.log('[REC ' + (entry.ms) + 'ms] ' + type + ': ' + JSON.stringify(data).slice(0, 250)); } catch (e) {}
  }

  // Generate unique CSS selector path for an element
  function selector(el) {
    if (!el || el.nodeType !== 1) return '';
    var parts = [];
    var cur = el;
    var depth = 0;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement && depth < 8) {
      var part = cur.tagName.toLowerCase();
      if (cur.id) { part += '#' + cur.id; parts.unshift(part); break; }
      var cls = (cur.className || '').toString().trim().split(/\s+/).filter(Boolean);
      if (cls.length) part += '.' + cls.slice(0, 2).join('.');
      try {
        var parent = cur.parentNode;
        if (parent && parent.children) {
          var sibs = Array.prototype.filter.call(parent.children, function (s) { return s.tagName === cur.tagName; });
          if (sibs.length > 1) part += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
        }
      } catch (e) {}
      parts.unshift(part);
      cur = cur.parentNode;
      depth++;
    }
    return parts.join(' > ');
  }

  function elemInfo(el) {
    if (!el || el.nodeType !== 1) return null;
    var info = {
      tag: el.tagName,
      selector: selector(el),
      id: el.id || '',
      name: el.name || '',
      text: (el.innerText || el.textContent || '').trim().slice(0, 60),
      class: (el.className || '').toString().slice(0, 80),
      onclick: (el.getAttribute && el.getAttribute('onclick') || '').slice(0, 120),
      href: (el.getAttribute && el.getAttribute('href') || '').slice(0, 100),
      title: (el.getAttribute && el.getAttribute('title') || '').slice(0, 40),
      type: (el.getAttribute && el.getAttribute('type') || '').slice(0, 20)
    };
    // value utk input
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      info.value = (el.value || '').slice(0, 80);
    }
    // parent utk context
    try {
      if (el.parentNode) info.parentClass = (el.parentNode.className || '').toString().slice(0, 60);
    } catch (e) {}
    return info;
  }

  // Hook clicks (capture phase — catch semua, bahkan yg diblokir)
  ['click', 'dblclick', 'mousedown', 'contextmenu'].forEach(function (evType) {
    document.addEventListener(evType, function (e) {
      record(evType.toUpperCase(), {
        target: elemInfo(e.target),
        currentTarget: elemInfo(e.currentTarget),
        trusted: e.isTrusted,
        x: e.clientX, y: e.clientY
      });
    }, true);
  });

  // Hook input/keydown (utk lihat apa yg diketik di mana)
  document.addEventListener('keydown', function (e) {
    var target = e.target;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
      record('KEYDOWN', {
        target: { tag: target.tagName, name: target.name || '', id: target.id || '', selector: selector(target) },
        key: e.key, code: e.code, ctrl: e.ctrlKey, value: (target.value || '').slice(0, 60)
      });
    }
  }, true);

  // Hook change utk input
  document.addEventListener('change', function (e) {
    var t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA')) {
      record('CHANGE', { tag: t.tagName, name: t.name || '', id: t.id || '', value: (t.value || '').slice(0, 80) });
    }
  }, true);

  // Hook window.open
  var origOpen = window.open;
  window.open = function (url) {
    record('WINDOW_OPEN', { url: (url || '').slice(0, 200) });
    return origOpen.apply(window, arguments);
  };

  // Hook location changes (hash)
  var lastHref = location.href;
  setInterval(function () {
    if (location.href !== lastHref) {
      record('LOCATION_CHANGE', { from: lastHref.slice(0, 120), to: location.href.slice(0, 120) });
      lastHref = location.href;
    }
  }, 500);

  // Hook jQuery AJAX (Accurate pakai jQuery 1.11)
  function hookAjax() {
    if (window.jQuery && !window.__ajaxHooked) {
      window.__ajaxHooked = true;
      try {
        window.jQuery(document).on('ajaxSend', function (e, xhr, settings) {
          record('AJAX', { url: ((settings && settings.url) || '').slice(0, 200), method: (settings && (settings.type || settings.method)) || '' });
        });
        console.log('[REC] jQuery AJAX hooked');
      } catch (err) { console.log('[REC] jQuery ajax hook err:', err); }
    }
  }
  hookAjax();
  setTimeout(hookAjax, 1500);
  setTimeout(hookAjax, 4000);

  // Hook fetch
  if (window.fetch) {
    var origFetch = window.fetch;
    window.fetch = function () {
      var url = (arguments[0] || '').toString();
      record('FETCH', { url: url.slice(0, 200) });
      return origFetch.apply(window, arguments);
    };
  }

  // Hook XHR open
  if (window.XMLHttpRequest) {
    var origXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url) {
      record('XHR', { method: method || '', url: (url || '').slice(0, 200) });
      return origXhrOpen.apply(this, arguments);
    };
  }

  // Observe DOM mutations — iframe baru, form baru, modal baru
  var obs = new MutationObserver(function (muts) {
    for (var i = 0; i < muts.length; i++) {
      var m = muts[i];
      for (var j = 0; j < (m.addedNodes || []).length; j++) {
        var n = m.addedNodes[j];
        if (n.nodeType !== 1) continue;
        if (n.tagName === 'IFRAME') {
          record('IFRAME_ADDED', { src: (n.src || '').slice(0, 150), id: n.id || '', name: n.name || '' });
        } else if (n.tagName === 'FORM') {
          record('FORM_ADDED', { id: n.id || '', action: (n.action || '').slice(0, 100), class: (n.className || '').toString().slice(0, 60) });
        } else if (n.id && /modal|dialog|overlay|popup|report/i.test(n.id)) {
          record('MODAL_ADDED', { id: n.id, tag: n.tagName, class: (n.className || '').toString().slice(0, 60) });
        }
      }
    }
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });

  // Hook console messages (Accurate framework logs)
  ['log', 'error', 'warn', 'info'].forEach(function (type) {
    var orig = console[type];
    console[type] = function () {
      var args = Array.prototype.slice.call(arguments);
      var msg = args.map(function (a) {
        try { return typeof a === 'object' ? JSON.stringify(a).slice(0, 100) : String(a); } catch (e) { return String(a); }
      }).join(' ');
      if (msg.indexOf('[REC') !== 0) {
        record('CONSOLE_' + type.toUpperCase(), { msg: msg.slice(0, 200) });
      }
      orig.apply(console, arguments);
    };
  });

  window.__recorder = {
    log: log,
    count: function () { return log.length; }
  };
  window.__recorderStop = function () {
    obs.disconnect();
    console.log('[REC] Stopped. Total events:', log.length);
    console.log('[REC] Export: __recorderExport()');
  };
  window.__recorderCount = function () {
    console.log('[REC] Total events:', log.length);
    var byType = {};
    log.forEach(function (e) { byType[e.type] = (byType[e.type] || 0) + 1; });
    console.log('[REC] By type:', JSON.stringify(byType));
  };
  window.__recorderExport = function () {
    var lines = log.map(function (e) {
      var t = e.ms;
      var type = e.type;
      var rest = {};
      for (var k in e) { if (k !== 'ms' && k !== 'type') rest[k] = e[k]; }
      return '[' + t + 'ms] ' + type + ': ' + JSON.stringify(rest);
    });
    var txt = '=== RECORDER OUTPUT ===\nTotal events: ' + log.length + '\n\n' + lines.join('\n');
    console.log(txt);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(function () {
        console.log('[REC] ✓ Output DISALIN ke clipboard. Ctrl+V di chat.');
      }).catch(function () {
        console.log('[REC] Clipboard gagal. Copy manual output di atas.');
      });
    }
    return txt;
  };

  console.log('[REC] ========================================');
  console.log('[REC] RECORDER STARTED. Kerjakan manual sekarang:');
  console.log('[REC]   1. Ketik kode di search box + Enter');
  console.log('[REC]   2. Double-click baris hasil');
  console.log('[REC]   3. Klik tab "Dokumen"');
  console.log('[REC]   4. Klik "Unduh PDF" / download');
  console.log('[REC] Selesai: ketik  __recorderExport()');
  console.log('[REC] ========================================');
})();
