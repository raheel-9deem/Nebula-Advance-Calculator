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
        <div class="h-expr">${escapeHtml(h.expr)} =</div>
        <div class="h-res">${escapeHtml(h.result)}</div>
      </li>`,
    )
    .join('');
  histList.querySelectorAll('li[data-i]').forEach(li => {
    li.addEventListener('click', () => {
      const item = history[+li.dataset.i];
      exprEl.textContent = item.result;
      resEl.textContent = ' ';
    });
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
    if (action && action.startsWith('m')) return memAction(action);

    if (insertTok) {
      // special-case keyboard symbols like '!', '10^', '^' that map 1:1
      if (['10^', '!', '^'].includes(insertTok)) return insert(insertTok);
      return insert(insertTok);
    }
  });
});

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
