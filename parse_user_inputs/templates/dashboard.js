/* ═══════════════════════════════════════════════════════════════════════════
   parse_user_inputs — Dashboard JavaScript (Canvas Charts + Interaction)
   ═══════════════════════════════════════════════════════════════════════════
   Data-Arrays are injected by the Jinja2 template:
     USER_INPUTS, CAT_COUNTS, TIMELINE, PASTE_IMAGES,
     MEM_STATS, REASONING, TOOL_DATA
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Platform Stats (Multi-Plattform Modus) ──────────────────────────────────
(function renderPlatformStats() {
  const el = document.getElementById('platformStats');
  if (!el || typeof PLATFORM_COUNTS === 'undefined') return;

  const platformColors = {
    hermes: '#d2a8ff', claude_code: '#f0883e', codex: '#3fb950',
    cursor: '#58a6ff', copilot: '#79c0ff', cline: '#f85149',
    roo_code: '#ffa657', kilo_code: '#ff7b72', windsurf: '#56d364',
    gemini_cli: '#a5d6ff', aider: '#bc8cff', freebuff: '#d2a8ff',
    continue: '#7ee787',
  };
  const platformNames = {
    hermes: 'Hermes', claude_code: 'Claude Code', codex: 'Codex CLI',
    cursor: 'Cursor', copilot: 'Copilot', cline: 'Cline',
    roo_code: 'Roo Code', kilo_code: 'Kilo Code', windsurf: 'Windsurf',
    gemini_cli: 'Gemini CLI', aider: 'Aider', freebuff: 'Freebuff',
    continue: 'Continue.dev',
  };

  Object.entries(PLATFORM_COUNTS).sort((a, b) => b[1] - a[1]).forEach(([pid, count]) => {
    const color = platformColors[pid] || '#8b949e';
    const name = platformNames[pid] || pid;
    el.innerHTML += '<div class="stat-card"><div class="label">' + name + '</div><div class="value" style="color:' + color + '">' + count + '</div><div class="sub">User-Inputs</div></div>';
  });
})();

// ── Stats Cards ─────────────────────────────────────────────────────────────
(function renderStats() {
  const el = document.getElementById('stats');
  if (!el) return;

  const memMB = (MEM_STATS.total_bytes / 1024 / 1024).toFixed(1);
  const userMB = ((MEM_STATS.by_role.user || 0) / 1024 / 1024).toFixed(1);
  const asstMB = ((MEM_STATS.by_role.assistant || 0) / 1024 / 1024).toFixed(1);
  const toolMB = ((MEM_STATS.by_role.tool || 0) / 1024 / 1024).toFixed(1);
  const coveragePct = MEM_STATS.total_bytes > 0
    ? ((USER_INPUTS.length * 221 / MEM_STATS.total_bytes) * 100).toFixed(1)
    : 0;

  const data = [
    { label: 'User-Inputs', value: USER_INPUTS.length, cls: 'blue', sub: coveragePct + '% der Memory' },
    { label: 'Assistant-Snippets', value: REASONING.length, cls: 'purple', sub: 'Reasoning extrahiert' },
    { label: 'Git-Commits', value: TIMELINE.reduce((a, d) => a + d.count, 0), cls: 'green', sub: 'Agent-Arbeit' },
    { label: 'Paste-PNGs', value: PASTE_IMAGES.length, cls: 'orange', sub: 'Visuelle Inputs' },
    { label: 'Memory Gesamt', value: memMB + ' MB', cls: 'red', sub: 'User ' + userMB + ' / Asst ' + asstMB + ' / Tool ' + toolMB },
  ];

  data.forEach(s => {
    el.innerHTML += '<div class="stat-card"><div class="label">' + s.label + '</div><div class="value ' + s.cls + '">' + s.value + '</div><div class="sub">' + s.sub + '</div></div>';
  });
})();

// ── Memory Volume ───────────────────────────────────────────────────────────
(function renderMemoryVolume() {
  const bar = document.getElementById('memBar');
  const legend = document.getElementById('memLegend');
  const detail = document.getElementById('memDetail');
  if (!bar) return;

  const total = MEM_STATS.total_bytes || 1;
  const roles = [
    { key: 'user', label: 'User', cls: 'user' },
    { key: 'assistant', label: 'Assistant', cls: 'asst' },
    { key: 'tool', label: 'Tool', cls: 'tool' },
  ];

  let barHtml = '', legendHtml = '';
  let detailHtml = '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
  detailHtml += '<tr style="color:var(--text2)"><th style="text-align:left;padding:4px 8px">Session</th><th style="text-align:right;padding:4px 8px">User</th><th style="text-align:right;padding:4px 8px">Assistant</th><th style="text-align:right;padding:4px 8px">Tool</th><th style="text-align:right;padding:4px 8px">Total</th></tr>';

  roles.forEach(r => {
    const bytes = MEM_STATS.by_role[r.key] || 0;
    const pct = (bytes / total * 100).toFixed(1);
    const mb = (bytes / 1024 / 1024).toFixed(1);
    barHtml += '<div class="' + r.cls + '" style="width:' + pct + '%">' + (pct > 8 ? r.label : '') + '</div>';
    const colorVar = r.key === 'user' ? 'accent' : r.key === 'assistant' ? 'accent3' : 'warn';
    legendHtml += '<span style="color:var(--text2);font-size:12px"><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:var(--' + colorVar + ');vertical-align:middle;margin-right:4px"></span>' + r.label + ': ' + mb + ' MB (' + pct + '%)</span>';
  });

  bar.innerHTML = barHtml;
  legend.innerHTML = legendHtml;

  // Session detail table
  const sessions = Object.entries(MEM_STATS.by_session || {}).sort((a, b) => b[1].total - a[1].total);
  sessions.forEach(([sid, s]) => {
    detailHtml += '<tr style="border-top:1px solid var(--border);color:var(--text2)"><td style="padding:4px 8px;font-family:monospace;font-size:11px">' + sid + '.. ' + (s.title ? '- ' + s.title : '') + '</td><td style="text-align:right;padding:4px 8px">' + (s.user / 1024).toFixed(0) + ' KB</td><td style="text-align:right;padding:4px 8px">' + (s.assistant / 1024).toFixed(0) + ' KB</td><td style="text-align:right;padding:4px 8px">' + (s.tool / 1024).toFixed(0) + ' KB</td><td style="text-align:right;padding:4px 8px;font-weight:600">' + (s.total / 1024).toFixed(0) + ' KB</td></tr>';
  });
  detailHtml += '</table>';
  detail.innerHTML = detailHtml;

  // Donut chart
  const canvas = document.getElementById('memChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 40;
  const h = 200;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);

  const cx = w / 2, cy = h / 2, r = 70;
  let startAngle = -Math.PI / 2;
  const colors = { user: '#58a6ff', assistant: '#d2a8ff', tool: '#f0883e' };

  roles.forEach(role => {
    const bytes = MEM_STATS.by_role[role.key] || 0;
    const slice = (bytes / total) * Math.PI * 2;
    ctx.beginPath(); ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, startAngle, startAngle + slice);
    ctx.fillStyle = colors[role.key]; ctx.fill();
    startAngle += slice;
  });

  ctx.beginPath(); ctx.arc(cx, cy, 40, 0, Math.PI * 2);
  ctx.fillStyle = '#161b22'; ctx.fill();
  ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 18px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText((MEM_STATS.total_bytes / 1024 / 1024).toFixed(1) + ' MB', cx, cy + 6);
})();

// ── Category Chart ──────────────────────────────────────────────────────────
(function renderCategoryChart() {
  const canvas = document.getElementById('catChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  const cats = Object.entries(CAT_COUNTS).sort((a, b) => b[1] - a[1]);
  if (!cats.length) return;

  const maxVal = Math.max(...cats.map(c => c[1]));
  const barH = 28, gap = 6, pad = 12, labelW = 140;
  const w = canvas.parentElement.clientWidth - 40;
  const h = cats.length * (barH + gap) + pad * 2;

  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);

  const colors = ['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#f85149', '#79c0ff', '#56d364', '#bc8cff', '#ffa657', '#ff7b72', '#a5d6ff', '#7ee787', '#d2a8ff'];

  cats.forEach(([cat, count], i) => {
    const y = pad + i * (barH + gap);
    const barW = (count / maxVal) * (w - labelW - pad - 60);

    ctx.fillStyle = '#8b949e'; ctx.font = '12px -apple-system, sans-serif';
    ctx.textAlign = 'right'; ctx.fillText(cat, labelW - 8, y + barH / 2 + 4);

    const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
    const c = colors[i % colors.length];
    grad.addColorStop(0, c); grad.addColorStop(1, c + '66');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 4); ctx.fill();

    ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 12px -apple-system, sans-serif';
    ctx.textAlign = 'left'; ctx.fillText(count, labelW + barW + 8, y + barH / 2 + 4);
  });
})();

// ── Activity Chart ──────────────────────────────────────────────────────────
(function renderActivityChart() {
  const canvas = document.getElementById('activityChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const data = TIMELINE;
  if (!data.length) return;

  const maxVal = Math.max(...data.map(d => d.count));
  const w = canvas.parentElement.clientWidth - 40;
  const h = 300;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);

  const pad = { top: 20, right: 20, bottom: 60, left: 50 };
  const cw = w - pad.left - pad.right;
  const ch = h - pad.top - pad.bottom;

  // Grid lines
  ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = pad.top + (ch / 5) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#8b949e'; ctx.font = '11px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxVal - (maxVal / 5) * i), pad.left - 8, y + 4);
  }

  const barW = Math.min(40, (cw / data.length) - 4);
  data.forEach((d, i) => {
    const x = pad.left + (cw / data.length) * i + (cw / data.length - barW) / 2;
    const barH = (d.count / maxVal) * ch;
    const y = pad.top + ch - barH;

    const grad = ctx.createLinearGradient(0, y, 0, pad.top + ch);
    grad.addColorStop(0, '#58a6ff'); grad.addColorStop(1, '#58a6ff22');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(x, y, barW, barH, 4); ctx.fill();

    ctx.save(); ctx.translate(x + barW / 2, pad.top + ch + 12);
    ctx.rotate(-Math.PI / 4); ctx.fillStyle = '#8b949e';
    ctx.font = '11px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(d.date, 0, 0); ctx.restore();

    ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center'; ctx.fillText(d.count, x + barW / 2, y - 6);
  });
})();

// ── Tool Charts ─────────────────────────────────────────────────────────────
(function renderToolCharts() {
  const counter = TOOL_DATA.counter || {};
  const sizes = TOOL_DATA.sizes || {};

  // Tool calls
  const entries = Object.entries(counter).sort((a, b) => b[1] - a[1]).slice(0, 15);
  if (entries.length) {
    const canvas = document.getElementById('toolChart');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      const dpr = window.devicePixelRatio || 1;
      const maxVal = Math.max(...entries.map(e => e[1]));
      const w = canvas.parentElement.clientWidth - 40;
      const h = 300;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);

      const barH = 18, gap = 4, pad = 10, labelW = 140;
      entries.forEach(([name, count], i) => {
        const y = pad + i * (barH + gap);
        const barW = (count / maxVal) * (w - labelW - pad - 40);

        ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
        ctx.textAlign = 'right'; ctx.fillText(name, labelW - 8, y + barH / 2 + 4);

        const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
        grad.addColorStop(0, '#f0883e'); grad.addColorStop(1, '#f0883e44');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 3); ctx.fill();

        ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'left'; ctx.fillText(count, labelW + barW + 6, y + barH / 2 + 4);
      });
    }
  }

  // Tool sizes
  const sizeEntries = Object.entries(sizes).sort((a, b) => b[1] - a[1]).slice(0, 15);
  if (sizeEntries.length) {
    const canvas = document.getElementById('toolSizeChart');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      const dpr = window.devicePixelRatio || 1;
      const maxVal = Math.max(...sizeEntries.map(e => e[1]));
      const w = canvas.parentElement.clientWidth - 40;
      const h = 300;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);

      const barH = 18, gap = 4, pad = 10, labelW = 140;
      sizeEntries.forEach(([name, bytes], i) => {
        const y = pad + i * (barH + gap);
        const barW = (bytes / maxVal) * (w - labelW - pad - 60);

        ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
        ctx.textAlign = 'right'; ctx.fillText(name, labelW - 8, y + barH / 2 + 4);

        const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
        grad.addColorStop(0, '#3fb950'); grad.addColorStop(1, '#3fb95044');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 3); ctx.fill();

        const kb = (bytes / 1024).toFixed(0);
        ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'left'; ctx.fillText(kb + ' KB', labelW + barW + 6, y + barH / 2 + 4);
      });
    }
  }
})();

// ── Timeline ────────────────────────────────────────────────────────────────
(function renderTimeline() {
  const el = document.getElementById('timeline');
  if (!el) return;

  TIMELINE.forEach(d => {
    const commits = d.subjects.map(s => '<li>' + s + '</li>').join('');
    el.innerHTML += '<div class="timeline-day">' +
      '<div class="timeline-date">' + d.date + ' <span class="badge">' + d.count + ' commits</span></div>' +
      '<ul class="timeline-commits">' + commits + '</ul></div>';
  });
})();

// ── Reasoning Snippets ──────────────────────────────────────────────────────
(function renderReasoning() {
  const el = document.getElementById('reasoningList');
  if (!el) return;

  REASONING.slice(0, 50).forEach((r, i) => {
    const card = document.createElement('div');
    card.className = 'reasoning-card';
    card.innerHTML =
      '<div class="meta"><span>' + r.date + '</span><span class="model">' + r.model + '</span><span>' + r.session + '..</span><span>' + (r.content_len / 1024).toFixed(0) + ' KB msg</span></div>' +
      '<div class="snippet" id="rsn-' + i + '">' + r.reasoning + '</div>' +
      '<div class="expand-btn" onclick="toggleReasoning(' + i + ')">&#9656; Mehr</div>';
    el.appendChild(card);
  });
})();

function toggleReasoning(idx) {
  const el = document.getElementById('rsn-' + idx);
  if (!el) return;
  const btn = el.nextElementSibling;
  el.classList.toggle('expanded');
  btn.textContent = el.classList.contains('expanded') ? '\u25BE Weniger' : '\u25B6 Mehr';
}

// ── Paste Grid ──────────────────────────────────────────────────────────────
(function renderPasteGrid() {
  const grid = document.getElementById('pasteGrid');
  const modal = document.getElementById('modal');
  const modalImg = document.getElementById('modalImg');
  if (!grid) return;

  PASTE_IMAGES.forEach(p => {
    const card = document.createElement('div');
    card.className = 'paste-card';
    card.innerHTML =
      '<img src="' + (p.data_uri || '') + '" alt="' + p.file + '" loading="lazy">' +
      '<div class="info"><strong>' + p.date + '</strong><br>' + p.dims + ' &middot; ' + p.size_kb + 'KB</div>';
    card.onclick = () => {
      if (p.data_uri) { modalImg.src = p.data_uri; modal.classList.add('active'); }
    };
    grid.appendChild(card);
  });

  if (modal) modal.onclick = () => modal.classList.remove('active');
})();

// ── Filter Chips + User Inputs ──────────────────────────────────────────────
(function renderUserInputs() {
  const allCats = [...new Set(USER_INPUTS.flatMap(i => i.categories))].sort();
  const chipsEl = document.getElementById('filterChips');
  const listEl = document.getElementById('inputsList');
  const searchEl = document.getElementById('searchInput');
  if (!chipsEl || !listEl || !searchEl) return;

  let activeFilter = null;

  allCats.forEach(cat => {
    const chip = document.createElement('span');
    chip.className = 'chip'; chip.textContent = cat;
    chip.onclick = () => {
      activeFilter = activeFilter === cat ? null : cat;
      document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      if (activeFilter) chip.classList.add('active');
      render();
    };
    chipsEl.appendChild(chip);
  });

  function render() {
    const q = searchEl.value.toLowerCase();
    const filtered = USER_INPUTS.filter(i => {
      if (activeFilter && !i.categories.includes(activeFilter)) return false;
      if (q && !i.content.toLowerCase().includes(q) && !i.categories.join(' ').toLowerCase().includes(q)) return false;
      return true;
    });

    listEl.innerHTML = '';
    filtered.forEach(i => {
      const tags = i.categories.map(c => '<span class="tag">' + c + '</span>').join('');
      const card = document.createElement('div');
      card.className = 'input-card';
      card.innerHTML =
        '<div class="head"><span><span class="idx">#' + i.idx + '</span> &middot; <span class="date">' + i.date + '</span> &middot; ' + i.source + ' &middot; ' + i.session + '..</span><div class="tags">' + tags + '</div></div>' +
        '<div class="body" id="body-' + i.idx + '">' + i.content + '</div>' +
        '<div class="expand-btn" onclick="toggleBody(' + i.idx + ')">\u25B6 Mehr anzeigen</div>';
      listEl.appendChild(card);
    });

    if (!filtered.length) {
      listEl.innerHTML = '<div style="color:var(--text2);padding:24px;text-align:center">Keine Treffer.</div>';
    }
  }

  searchEl.oninput = render;
  render();
})();

function toggleBody(idx) {
  const el = document.getElementById('body-' + idx);
  if (!el) return;
  const btn = el.nextElementSibling;
  el.classList.toggle('expanded');
  btn.textContent = el.classList.contains('expanded') ? '\u25BE Weniger' : '\u25B6 Mehr anzeigen';
}
