/* ============================================================
NEBULA Calculator - Frontend logic
============================================================ */

const exprEl = document.getElementById('expr');
const resEl = document.getElementById('result');
const display = document.querySelector('.display');
const modeDeg = document.getElementById('modeDeg');
const modeRad = document.getElementById('modeRad');
const histList = document.getElementById('historyList');
const toastEl = document.getElementById('toast');
const fmtEl = document.getElementById('fmtResult');

let deg = true;
let memory = 0;
let history = JSON.parse(localStorage.getItem('nebula_hist') || '[]');

/* ---------- Helpers ---------- */
function setMode(isDeg) {
  deg = isDeg;
  modeDeg.classList.toggle('active', isDeg);
  modeRad.classList.toggle('active', !isDeg);
}
modeDeg.addEventListener('click', () => setMode(true));
modeRad.addEventListener('click', () => setMode(false));

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.remove('show'), 2200);
}

/* ---------- Expression building ---------- */
function currentExpr() {
  return exprEl.textContent === '0' ? '' : exprEl.textContent;
}

function insert(token) {
  let cur = exprEl.textContent;
  if (cur === '0' && /[0-9.]/.test(token)) cur = '';
  exprEl.textContent = cur + token;
  resEl.textContent = ' ';
  display.classList.remove('error');
}

function clearAll() {
  exprEl.textContent = '0';
  resEl.textContent = ' ';
  display.classList.remove('error');
}

function backspace() {
  if (exprEl.textContent.length <= 1) {
    exprEl.textContent = '0';
  } else {
    exprEl.textContent = exprEl.textContent.slice(0, -1);
  }
}

/* ---------- Memory ---------- */
function memAction(action) {
  switch (action) {
    case 'mc':
      memory = 0;
      showToast('Memory cleared');
      break;
    case 'mr':
      insert(String(memory));
      showToast('Memory recalled');
      break;
    case 'mplus':
      compute(true, v => (memory += v));
      break;
    case 'mminus':
      compute(true, v => (memory -= v));
      break;
  }
}

/* ---------- Compute ---------- */
async function compute(isMemory = false, memCb = null) {
  const expression = currentExpr();
  if (!expression) return;

  try {
    const resp = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expression, deg }),
    });
    const data = await resp.json();

    if (!data.success) {
      if (isMemory) {
        showToast('Memory error: ' + data.error);
        return;
      }
      resEl.textContent = data.error || 'Error';
      display.classList.add('error');
      return;
    }

    if (memCb) {
      memCb(parseFloat(data.result));
      showToast('Memory updated');
      return;
    }

    resEl.textContent = data.result;
    display.classList.remove('error');
    display.classList.remove('flash');
    void display.offsetWidth;
    display.classList.add('flash');
    fmtEl.textContent = ' ';
    document.querySelectorAll('.fmt-key.active').forEach(k => k.classList.remove('active'));
    addHistory(expression, data.result);
  } catch (err) {
    resEl.textContent = 'Network error';
    display.classList.add('error');
  }
}

/* ---------- History ---------- */
function addHistory(expr, result) {
  history.unshift({ expr, result, time: Date.now() });
  history = history.slice(0, 50);
  localStorage.setItem('nebula_hist', JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  if (!history.length) {
    histList.innerHTML = '<li class="history-empty">Your calculations will appear here.</li>';
    return;
  }
  histList.innerHTML = history
    .map(
      (h, i) => `
      <li data-i="${i}">
        <div class="h-expr">${escapeHtml(h.expr)} = <span class="h-edit" title="Edit expression">&#9998;</span></div>
        <div class="h-res">${escapeHtml(h.result)}</div>
      </li>`,
    )
    .join('');
  histList.querySelectorAll('li[data-i]').forEach(li => {
    // click the body recalls the RESULT; the edit link reloads the EXPR
    li.querySelectorAll('.h-expr, .h-res').forEach(seg => {
      seg.addEventListener('click', () => {
        const item = history[+li.dataset.i];
        exprEl.textContent = item.result;
        resEl.textContent = ' ';
      });
    });
    // edit glyph reloads the original expression
    const editG = li.querySelector('.h-edit');
    if (editG) {
      editG.addEventListener('click', ev => {
        ev.stopPropagation();
        const item = history[+li.dataset.i];
        exprEl.textContent = item.expr;
        resEl.textContent = ' ';
        showToast('Expression loaded — edit and press =');
      });
    }
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&',
    '<': '<',
    '>': '>',
    '"': '"',
    "'": '&#39;',
  }[c]));
}

document.getElementById('clearHistory').addEventListener('click', () => {
  history = [];
  localStorage.removeItem('nebula_hist');
  renderHistory();
  showToast('History cleared');
});

/* ---------- History CSV export ---------- */
document.getElementById('exportHistory').addEventListener('click', () => {
  if (!history.length) { showToast('History is empty'); return; }
  const rows = [['Expression', 'Result']];
  for (const h of history) rows.push([h.expr, h.result]);
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'nebula_history.csv';
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  showToast('History exported to CSV');
});

/* ---------- Formatting ---------- */
async function fmtNumber(fmt) {
  const raw = resEl.textContent.trim();
  if (!raw || raw === '' || raw === 'Error' || raw === 'Network error') {
    showToast('Compute a result first');
    return;
  }
  // strip leading "Math error:" style messages just in case
  if (/^[A-Za-z]/.test(raw) && raw !== 'NaN' && raw !== '∞' && raw !== '-∞') {
    showToast('Compute a result first');
    return;
  }
  const number = Number(raw);
  if (!Number.isFinite(number)) {
    fmtEl.textContent = '—';
    return;
  }
  try {
    const resp = await fetch('/api/format', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ number, format: fmt, deg }),
    });
    const data = await resp.json();
    if (!data.success) {
      fmtEl.textContent = data.error || 'Format error';
      return;
    }
    fmtEl.textContent = `= ${data.formatted}`;
    document.querySelectorAll('.fmt-key.active').forEach(k => k.classList.remove('active'));
    document.querySelector(`.fmt-key[data-format="${fmt}"]`)?.classList.add('active');
  } catch (err) {
    fmtEl.textContent = 'Network error';
  }
}

document.querySelectorAll('.fmt-key').forEach(key => {
  key.addEventListener('click', e => {
    const r = key.getBoundingClientRect();
    key.style.setProperty('--rx', `${e.clientX - r.left}px`);
    key.style.setProperty('--ry', `${e.clientY - r.top}px`);
    key.classList.remove('pulse');
    void key.offsetWidth;
    key.classList.add('pulse');
    fmtNumber(key.dataset.format);
  });
});

/* ---------- Keypad wiring ---------- */
document.querySelectorAll('.key').forEach(key => {
  key.addEventListener('click', e => {
    // ripple
    const r = key.getBoundingClientRect();
    key.style.setProperty('--rx', `${e.clientX - r.left}px`);
    key.style.setProperty('--ry', `${e.clientY - r.top}px`);
    key.classList.remove('pulse');
    void key.offsetWidth;
    key.classList.add('pulse');

    const action = key.dataset.action;
    const insertTok = key.dataset.insert;

    if (action === 'equals') return compute();
    if (action === 'clear') return clearAll();
    if (action === 'back') return backspace();
    if (action === 'paren') return insert('(');
    if (action === 'paren2') return insert(')');
    if (action === 'sto') return promptVar('sto');
    if (action === 'recall') return promptVar('recall');
    if (action && action.startsWith('m')) return memAction(action);

    if (insertTok) {
      return insert(insertTok);
    }
  });
});

/* ---------- Variable store / recall (keypad + prompt) ---------- */
function promptVar(kind) {
  const name = window.prompt(kind === 'sto' ? 'Variable name to store current result into:' : 'Variable name to recall:');
  if (!name) return;
  const cleanName = name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '');
  if (!cleanName) { showToast('Invalid variable name'); return; }
  if (kind === 'recall') {
    insert(`recall("${cleanName}")`);
  } else {
    // wrap current expression so result is computed first, then stored
    const expr = currentExpr() || '0';
    exprEl.textContent = `sto("${cleanName}", ${expr})`;
    trackVar(cleanName);
    compute().then(refreshVars);
  }
}

function trackVar(name) {
  const names = JSON.parse(localStorage.getItem('nebula_vars') || '[]');
  if (!names.includes(name)) names.push(name);
  localStorage.setItem('nebula_vars', JSON.stringify(names));
}

async function refreshVars() {
  try {
    const el = document.getElementById('varsList');
    const ul = document.getElementById('varsEntries');
    // We don't have a dedicated endpoint; infer vars by testing recall calls is
    // expensive. Instead, show vars we know about from local attempt: query the
    // engine via a cheap expression that returns 1 if 'a' exists.
    // Simplest: keep a JS-side mirror of stored names in localStorage.
    const names = JSON.parse(localStorage.getItem('nebula_vars') || '[]');
    if (!names.length) { el.hidden = true; return; }
    el.hidden = false;
    ul.innerHTML = '';
    for (const n of names) {
      const r = await fetch('/api/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression: `recall("${n}")`, deg }),
      }).then(x => x.json()).catch(() => null);
      const li = document.createElement('li');
      li.innerHTML = `<span class="v-name">${escapeHtml(n)}</span><span class="v-val">${r && r.success ? escapeHtml(r.result) : '—'}</span>`;
      li.title = `Insert recall("${n}")`;
      li.style.cursor = 'pointer';
      li.addEventListener('click', () => { insert(`recall("${n}")`); });
      ul.appendChild(li);
    }
  } catch (_) { /* ignore */ }
}

/* ---------- Keyboard support ---------- */
document.addEventListener('keydown', e => {
  const k = e.key;
  if (/^[0-9.+\-*/^%()!,]$/.test(k)) {
    insert(k);
    e.preventDefault();
  } else if (k === 'Enter' || k === '=') {
    compute();
    e.preventDefault();
  } else if (k === 'Backspace') {
    backspace();
    e.preventDefault();
  } else if (k === 'Escape') {
    clearAll();
    e.preventDefault();
  } else if (k.toLowerCase() === 'c' && (e.ctrlKey || e.metaKey)) {
    navigator.clipboard?.writeText(exprEl.textContent).catch(() => {});
    showToast('Expression copied');
    e.preventDefault();
  }
});

/* ---------- Responsive resize helper (used by particles) ---------- */
addEventListener('resize', () => {});

/* ---------- Particle background ---------- */
(function particles() {
  const canvas = document.getElementById('particles');
  const ctx = canvas.getContext('2d');
  let w, h, parts;
  function resize() {
    w = canvas.width = innerWidth;
    h = canvas.height = innerHeight;
    parts = Array.from({ length: 60 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: Math.random() * 1.8 + 0.4,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      hue: Math.random() > 0.5 ? '94,234,212' : '167,139,250',
    }));
  }
  function tick() {
    ctx.clearRect(0, 0, w, h);
    for (const p of parts) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.hue},0.6)`;
      ctx.fill();
    }
    for (let i = 0; i < parts.length; i++) {
      for (let j = i + 1; j < parts.length; j++) {
        const dx = parts[i].x - parts[j].x;
        const dy = parts[i].y - parts[j].y;
        const d = Math.hypot(dx, dy);
        if (d < 120) {
          ctx.strokeStyle = `rgba(94,234,212,${0.08 * (1 - d / 120)})`;
          ctx.beginPath();
          ctx.moveTo(parts[i].x, parts[i].y);
          ctx.lineTo(parts[j].x, parts[j].y);
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(tick);
  }
  addEventListener('resize', resize);
  resize();
  tick();
})();

// init
setMode(true);
renderHistory();
applyStoredTheme();
refreshVars();

/* ============================================================
Theme toggle (Dark / Light) — persisted in localStorage
============================================================ */
const themeBtn = document.getElementById('themeBtn');
function applyStoredTheme() {
  const t = localStorage.getItem('nebula_theme') || 'dark';
  document.body.classList.toggle('theme-light', t === 'light');
  themeBtn.textContent = t === 'light' ? '☾' : '☀';
}
themeBtn.addEventListener('click', () => {
  const light = document.body.classList.toggle('theme-light');
  localStorage.setItem('nebula_theme', light ? 'light' : 'dark');
  themeBtn.textContent = light ? '☾' : '☀';
  showToast(light ? 'Light theme' : 'Dark theme');
});

/* ============================================================
Panel toggles: graph + tools drawer
============================================================ */
const graphPanel = document.getElementById('graphPanel');
const graphBtn = document.getElementById('graphBtn');
const toolsDrawer = document.getElementById('toolsDrawer');
const toolsBtn = document.getElementById('toolsBtn');
graphBtn.addEventListener('click', () => {
  graphPanel.hidden = !graphPanel.hidden;
  graphBtn.classList.toggle('active', !graphPanel.hidden);
  if (!graphPanel.hidden) doPlot();
});
toolsBtn.addEventListener('click', () => {
  toolsDrawer.hidden = !toolsDrawer.hidden;
  toolsBtn.classList.toggle('active', !toolsDrawer.hidden);
});
document.getElementById('toolsClose').addEventListener('click', () => {
  toolsDrawer.hidden = true; toolsBtn.classList.remove('active');
});

/* ============================================================
Graph plotter — fetch samples from /api/plot and render on canvas
============================================================ */
const gCanvas = document.getElementById('graph');
const gCtx = gCanvas.getContext('2d');
let gPoints = [];
let gView = null; // {xMin, xMax, yMin, yMax}

function setGraphCanvasSize() {
  const r = gCanvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  gCanvas.width = Math.round(r.width * dpr);
  gCanvas.height = Math.round(320 * dpr);
  gCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

async function doPlot() {
  const expr = document.getElementById('graphExpr').value.trim();
  const xMin = parseFloat(document.getElementById('graphXMin').value);
  const xMax = parseFloat(document.getElementById('graphXMax').value);
  const dstate = document.getElementById('graphDegState').checked;
  if (!expr || isNaN(xMin) || isNaN(xMax) || xMax <= xMin) {
    showToast('Check graph expression and x range');
    return;
  }
  showToast('Plotting…');
  try {
    const resp = await fetch('/api/plot', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expr, xMin, xMax, n: 600, deg: dstate }),
    });
    const data = await resp.json();
    if (!data.success) { showToast(data.error || 'Plot error'); return; }
    gPoints = data.points;
    gView = null; // reset; auto-fit on next draw
    drawGraph();
  } catch (e) { showToast('Plot network error'); }
}

function autoView() {
  if (!gView) {
    let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
    for (const [x, y] of gPoints) {
      if (x < xMin) xMin = x; if (x > xMax) xMax = x;
      if (y !== null && y !== undefined) { if (y < yMin) yMin = y; if (y > yMax) yMax = y; }
    }
    if (!isFinite(yMin) || !isFinite(yMax)) { yMin = -1; yMax = 1; }
    if (yMin === yMax) { yMin -= 1; yMax += 1; }
    const padY = (yMax - yMin) * 0.1;
    gView = { xMin, xMax, yMin: yMin - padY, yMax: yMax + padY };
  }
  return gView;
}

function drawGraph(hx, hy) {
  setGraphCanvasSize();
  const r = gCanvas.getBoundingClientRect();
  const W = r.width, H = 320;
  gCtx.clearRect(0, 0, W, H);
  if (!gPoints.length) return;
  const v = autoView();
  const x2p = x => ((x - v.xMin) / (v.xMax - v.xMin)) * W;
  const y2p = y => H - ((y - v.yMin) / (v.yMax - v.yMin)) * H;

  // grid + axes
  gCtx.strokeStyle = 'rgba(255,255,255,.06)';
  gCtx.lineWidth = 1;
  for (let i = 0; i <= 10; i++) {
    const px = (W / 10) * i;
    gCtx.beginPath(); gCtx.moveTo(px, 0); gCtx.lineTo(px, H); gCtx.stroke();
    const py = (H / 8) * i;
    gCtx.beginPath(); gCtx.moveTo(0, py); gCtx.lineTo(W, py); gCtx.stroke();
  }
  // x = 0 and y = 0 axes
  gCtx.strokeStyle = 'rgba(148,163,184,.35)';
  gCtx.lineWidth = 1.4;
  if (v.yMin < 0 && v.yMax > 0) { const oy = y2p(0); gCtx.beginPath(); gCtx.moveTo(0, oy); gCtx.lineTo(W, oy); gCtx.stroke(); }
  if (v.xMin < 0 && v.xMax > 0) { const ox = x2p(0); gCtx.beginPath(); gCtx.moveTo(ox, 0); gCtx.lineTo(ox, H); gCtx.stroke(); }

  // trace
  gCtx.strokeStyle = '#5eead4';
  gCtx.lineWidth = 2;
  gCtx.shadowColor = 'rgba(94,234,212,.8)'; gCtx.shadowBlur = 8;
  gCtx.beginPath();
  let pen = false;
  for (const [x, y] of gPoints) {
    if (y === null || y === undefined || !isFinite(y)) { pen = false; continue; }
    const px = x2p(x), py = y2p(y);
    if (!pen) { gCtx.moveTo(px, py); pen = true; } else { gCtx.lineTo(px, py); }
  }
  gCtx.stroke();
  gCtx.shadowBlur = 0;

  // hover crosshair + readout
  if (hx !== undefined && hy !== undefined) {
    gCtx.strokeStyle = 'rgba(249,168,212,.7)';
    gCtx.setLineDash([4, 4]);
    gCtx.beginPath(); gCtx.moveTo(hx, 0); gCtx.lineTo(hx, H); gCtx.stroke();
    gCtx.beginPath(); gCtx.moveTo(0, hy); gCtx.lineTo(W, hy); gCtx.stroke();
    gCtx.setLineDash([]);
    const vx = v.xMin + (hx / W) * (v.xMax - v.xMin);
    const vy = v.yMin + ((H - hy) / H) * (v.yMax - v.yMin);
    const label = `(${vx.toFixed(3)}, ${vy.toFixed(3)})`;
    gCtx.font = '12px "JetBrains Mono", monospace';
    const tw = gCtx.measureText(label).width + 12;
    gCtx.fillStyle = 'rgba(10,14,26,.9)';
    gCtx.fillRect(hx + 8, hy - 24, tw, 20);
    gCtx.fillStyle = '#f9a8d4';
    gCtx.fillText(label, hx + 14, hy - 10);
  }
  document.getElementById('graphHint').textContent = 'Scroll to zoom · drag to pan · hover to read (x, y)';
}

// wheel zoom + drag pan
let dragging = false, dragStart = null;
gCanvas.addEventListener('wheel', e => {
  if (!gPoints.length) return;
  e.preventDefault();
  const v = autoView();
  const r = gCanvas.getBoundingClientRect();
  const mx = e.clientX - r.left;
  const fx = v.xMin + (mx / r.width) * (v.xMax - v.xMin);
  const scale = e.deltaY < 0 ? 0.8 : 1.25;
  v.xMin = fx - (fx - v.xMin) * scale;
  v.xMax = fx + (v.xMax - fx) * scale;
  drawGraph();
}, { passive: false });

gCanvas.addEventListener('mousedown', e => { dragging = true; dragStart = { x: e.clientX, v: { ...autoView() } }; });
window.addEventListener('mouseup', () => { dragging = false; });
gCanvas.addEventListener('mousemove', e => {
  const r = gCanvas.getBoundingClientRect();
  const hx = e.clientX - r.left, hy = e.clientY - r.top;
  if (dragging && dragStart) {
    const dx = (e.clientX - dragStart.x) / r.width * (dragStart.v.xMax - dragStart.v.xMin);
    gView = { ...dragStart.v, xMin: dragStart.v.xMin - dx, xMax: dragStart.v.xMax - dx };
    drawGraph();
  } else {
    drawGraph(hx, hy);
  }
});
gCanvas.addEventListener('mouseleave', () => drawGraph());
document.getElementById('graphPlot').addEventListener('click', doPlot);
window.addEventListener('resize', () => { if (!graphPanel.hidden) drawGraph(); });

/* ============================================================
Tools drawer — tabs + per-pane API calls
============================================================ */
document.querySelectorAll('.tools-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tools-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tools-pane').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.querySelector(`.tools-pane[data-pane="${tab.dataset.tab}"]`).classList.add('active');
  });
});

function setResult(id, text, isErr) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.classList.toggle('error', !!isErr);
}

/* --- Convert pane --- */
const convCat = document.getElementById('convCat');
const convFrom = document.getElementById('convFrom');
const convTo = document.getElementById('convTo');
function loadUnits(category) {
  // fetch the units list once
  fetch('/api/units').then(r => r.json()).then(d => {
    const cats = d.categories || {};
    const list = cats[category] || [];
    if (category === 'temperature') {
      // temperature uses fixed names
      unitsFill(['c', 'f', 'k'], convFrom, convTo); return;
    }
    unitsFill(dedupeShort(list), convFrom, convTo);
  });
}
function dedupeShort(list) { const seen = new Set(); const out = []; for (const u of list) { if (!seen.has(u)) { seen.add(u); out.push(u); } } return out; }
function unitsFill(list, ...sels) { for (const sel of sels) { sel.innerHTML = list.map(u => `<option value="${u}">${u}</option>`).join(''); } }
// populate category dropdown
(function () {
  fetch('/api/units').then(r => r.json()).then(d => {
    const cats = Object.keys(d.categories || {});
    convCat.innerHTML = cats.map(c => `<option value="${c}">${c}</option>`).join('');
    if (cats.length) loadUnits(cats[0]);
  });
})();
convCat.addEventListener('change', () => loadUnits(convCat.value));
document.getElementById('convGo').addEventListener('click', async () => {
  try {
    const r = await fetch('/api/convert', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: convCat.value, from: convFrom.value, to: convTo.value, value: parseFloat(document.getElementById('convVal').value) }),
    }).then(x => x.json());
    if (r.success) setResult('convResult', `${r.input} ${r.from} = ${r.result} ${r.to}`);
    else setResult('convResult', r.error || 'Error', true);
  } catch (e) { setResult('convResult', 'Network error', true); }
});

/* --- Currency pane --- */
document.getElementById('curGo').addEventListener('click', async () => {
  try {
    const r = await fetch('/api/currency', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: document.getElementById('curFrom').value, to: document.getElementById('curTo').value, amount: parseFloat(document.getElementById('curAmt').value) }),
    }).then(x => x.json());
    if (r.success) setResult('curResult', `${r.amount} ${r.from} = ${r.result} ${r.to}  (rate ${r.rate})`);
    else setResult('curResult', r.error || 'Error', true);
  } catch (e) { setResult('curResult', 'Network error', true); }
});

/* --- Date/Time pane --- */
document.getElementById('dtGo').addEventListener('click', async () => {
  const op = document.getElementById('dtOp').value;
  const a = document.getElementById('dtA').value;
  const b = document.getElementById('dtB').value;
  // For 'add', second field is days; for others it's a date or on-date
  const body = (op === 'add')
    ? { op, date: a, days: parseInt(b, 10) }
    : (op === 'age')
      ? { op, birth: a, on: b || undefined }
      : { op, a, b };
  try {
    const r = await fetch('/api/datetime', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json());
    if (r.success) setResult('dtResult', JSON.stringify(r.result, null, 2));
    else setResult('dtResult', r.error || 'Error', true);
  } catch (e) { setResult('dtResult', 'Network error', true); }
});

/* --- Stats pane --- */
document.getElementById('statGo').addEventListener('click', async () => {
  const raw = document.getElementById('statData').value.trim();
  const data = raw.split(/[\s,]+/).map(Number).filter(n => !isNaN(n));
  if (!data.length) { setResult('statResult', 'Enter numbers separated by commas'); return; }
  try {
    const r = await fetch('/api/stats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data }) }).then(x => x.json());
    if (r.success) setResult('statResult', Object.entries(r.result).map(([k, v]) => `${k}: ${v}`).join('\n'));
    else setResult('statResult', r.error || 'Error', true);
  } catch (e) { setResult('statResult', 'Network error', true); }
});

/* --- Solve pane --- */
document.getElementById('solveGo').addEventListener('click', async () => {
  const type = document.getElementById('solveType').value;
  if (type === 'poly') {
    const coeffs = document.getElementById('solveCoeffs').value.split(',').map(Number).filter(n => !isNaN(n));
    try {
      const r = await fetch('/api/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'poly', coeffs }) }).then(x => x.json());
      if (r.success) setResult('solveResult', `roots: ${r.roots.join(', ')}${r.complex ? '  (complex)' : ''}${r.discriminant !== null && r.discriminant !== undefined ? `\ndiscriminant: ${r.discriminant}` : ''}`);
      else setResult('solveResult', r.error || 'Error', true);
    } catch (e) { setResult('solveResult', 'Network error', true); }
  } else {
    setResult('solveResult', 'System solver: enter A (rows; e.g. 2,1;1,-1) and b (e.g. 5,0). Use Matrix tab for full systems.', true);
  }
});

/* --- Matrix pane --- */
function parseMatrix(text) { return text.split(';').filter(r => r.trim()).map(r => r.split(',').map(Number)); }
document.getElementById('matGo').addEventListener('click', async () => {
  const op = document.getElementById('matOp').value;
  const a = parseMatrix(document.getElementById('matA').value);
  const body = { op, a };
  if (op === 'mul' || op === 'add') body.b = parseMatrix(document.getElementById('matB').value);
  try {
    const r = await fetch('/api/matrix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json());
    if (r.success) setResult('matResult', (Array.isArray(r.result) && Array.isArray(r.result[0]) ? r.result.map(row => row.join(', ')).join('\n') : `= ${r.result}`) + (r.shape ? `\nshape ${r.shape}` : ''));
    else setResult('matResult', r.error || 'Error', true);
  } catch (e) { setResult('matResult', 'Network error', true); }
});

/* --- Base pane --- */
document.getElementById('baseGo').addEventListener('click', async () => {
  const value = document.getElementById('baseVal').value.trim();
  try {
    const r = await fetch('/api/base', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }) }).then(x => x.json());
    if (r.success) setResult('baseResult', `dec: ${r.dec}\nhex: ${r.hex}\noct: ${r.oct}\nbin: ${r.bin}`);
    else setResult('baseResult', r.error || 'Error', true);
  } catch (e) { setResult('baseResult', 'Network error', true); }
});

/* ============================================================
Voice input — Web Speech API, graceful when unsupported
============================================================ */
const voiceBtn = document.getElementById('voiceBtn');
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRec) {
  voiceBtn.classList.add('unsupported');
  voiceBtn.title = 'Voice input not supported in this browser';
} else {
  const rec = new SpeechRec();
  rec.lang = 'en-US'; rec.interimResults = false; rec.maxAlternatives = 1;
  voiceBtn.addEventListener('click', () => {
    try { rec.start(); voiceBtn.classList.add('active'); showToast('Listening…'); }
    catch (e) { showToast('Already listening'); }
  });
  rec.addEventListener('end', () => voiceBtn.classList.remove('active'));
  rec.addEventListener('result', ev => {
    const said = ev.results[0][0].transcript.toLowerCase();
    const mapped = voiceToMath(said);
    if (mapped) { insert(mapped); showToast('Heard: ' + mapped); }
    else showToast('Could not parse: ' + said);
  });
  rec.addEventListener('error', () => showToast('Voice error or no speech detected'));
}
function voiceToMath(s) {
  // Replace spoken math words with tokens
  s = s.replace(/\bplus\b/g, '+').replace(/\bminus\b/g, '-').replace(/\btimes\b|\bmultiplied by\b/g, '*').replace(/\bdivided by\b|\bover\b/g, '/').replace(/\bpower\b/g, '^').replace(/\bsquared\b/g, '^2').replace(/\bcubed\b/g, '^3');
  s = s.replace(/\bsine of\b|\bsine\b|\bsign of\b/g, 'sin(').replace(/\bcosine of\b|\bcosine\b/g, 'cos(').replace(/\btangent of\b|\btangent\b/g, 'tan(');
  s = s.replace(/\bsquare root of\b/g, 'sqrt(').replace(/\bpi\b/g, 'pi').replace(/\bto the\b/g, '^');
  // normalize digits/decimals
  s = s.replace(/\bpoint\b/g, '.');
  s = s.replace(/\bzero\b|\bzero\b/g, '0').replace(/\bone\b/g, '1').replace(/\btwo\b|\btoo\b|\bto\b/g, '2').replace(/\bthree\b/g, '3').replace(/\bfour\b|\bfor\b/g, '4').replace(/\bfive\b/g, '5').replace(/\bsix\b/g, '6').replace(/\bseven\b/g, '7').replace(/\beight\b/g, '8').replace(/\bnine\b/g, '9');
  // balance by appending ） if needed
  let opens = (s.match(/\(/g) || []).length, closes = (s.match(/\)/g) || []).length;
  s = s + ')'.repeat(Math.max(0, opens - closes));
  return s.trim() || null;
}
