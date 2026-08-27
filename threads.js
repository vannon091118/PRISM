/* ═══════════════════════════════════════════════════════════════════════════
   parse_user_inputs — Threads Dashboard JS
   ═══════════════════════════════════════════════════════════════════════════ */

/* global THREADS, CAT_COUNTS, PROJECT_COUNTS, PLATFORM_COUNTS, NUM_MESSAGES, NUM_PLATFORMS */

// ── Stats ────────────────────────────────────────────────────────────────
function renderStats() {
  const el = document.getElementById('stats');
  if (!el) return;
  const withAgent = THREADS.filter(t => t.has_agent_response).length;
  const data = [
    { label: 'Threads', value: THREADS.length, cls: 'blue', sub: withAgent + ' mit Agent-Antwort' },
    { label: 'Messages', value: NUM_MESSAGES, cls: 'purple', sub: 'User + Agent + Tool' },
    { label: 'Plattformen', value: NUM_PLATFORMS, cls: 'green', sub: 'Aktive Quellen' },
    { label: 'Kategorien', value: Object.keys(CAT_COUNTS).length, cls: 'orange', sub: 'Topics' },
  ];
  data.forEach(function(s) {
    el.innerHTML += '<div class="stat-card"><div class="label">' + s.label +
      '</div><div class="value ' + s.cls + '">' + s.value +
      '</div><div class="sub">' + s.sub + '</div></div>';
  });
}

// ── Platform Stats ───────────────────────────────────────────────────────
function renderPlatformStats() {
  var el = document.getElementById('platformStats');
  if (!el) return;
  var colors = { freebuff: '#d2a8ff', hermes: '#58a6ff', claude_code: '#f0883e', codex: '#3fb950', cursor: '#8b949e', gemini_cli: '#4285f4' };
  var names = { freebuff: 'Freebuff', hermes: 'Hermes', claude_code: 'Claude Code', codex: 'Codex', cursor: 'Cursor', gemini_cli: 'Gemini CLI' };
  Object.entries(PLATFORM_COUNTS).sort(function(a, b) { return b[1] - a[1]; }).forEach(function(entry) {
    var pid = entry[0], count = entry[1];
    el.innerHTML += '<div class="stat-card"><div class="label">' + (names[pid] || pid) +
      '</div><div class="value" style="color:' + (colors[pid] || '#8b949e') + '">' + count +
      '</div><div class="sub">Threads</div></div>';
  });
}

// ── View State ───────────────────────────────────────────────────────────
var currentView = 'category';
var activeFilter = null;

function setView(view) {
  currentView = view;
  document.querySelectorAll('.view-btn').forEach(function(b) { b.classList.remove('active'); });
  event.target.classList.add('active');
  render();
}

// ── Filter Chips ─────────────────────────────────────────────────────────
function renderChips() {
  var el = document.getElementById('filterChips');
  if (!el) return;
  var allCats = [];
  THREADS.forEach(function(t) {
    t.categories.forEach(function(c) {
      if (allCats.indexOf(c) === -1) allCats.push(c);
    });
  });
  allCats.sort();
  allCats.forEach(function(cat) {
    var chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = cat;
    chip.onclick = function() {
      activeFilter = activeFilter === cat ? null : cat;
      document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
      if (activeFilter) chip.classList.add('active');
      render();
    };
    el.appendChild(chip);
  });
}

// ── Thread Rendering ─────────────────────────────────────────────────────
function renderThreadCard(t) {
  var tags = t.categories.map(function(c) { return '<span class="tag">' + c + '</span>'; }).join('');
  var hasInterrupt = t.has_interrupts ? '<span class="msg-badge interrupt">INTERRUPT</span>' : '';
  var hasFollowup = t.has_followups ? '<span class="msg-badge followup">FOLLOW-UP</span>' : '';

  var msgs = t.messages.slice(0, 10).map(function(m, i) {
    var mt = m.message_type || 'normal';
    var role, label, extraClass = '';
    if (mt === 'interrupt') {
      role = 'interrupt'; label = 'INTERRUPT'; extraClass = ' interrupt-msg';
    } else if (mt === 'followup') {
      role = 'followup'; label = 'FOLLOW-UP'; extraClass = ' followup-msg';
    } else if (mt === 'system') {
      role = 'system'; label = 'SYSTEM'; extraClass = ' system-msg';
    } else if (mt === 'model_switch') {
      role = 'system'; label = 'MODEL SWITCH'; extraClass = ' system-msg';
    } else if (m.role === 'user') {
      role = 'user'; label = 'USER';
    } else if (m.role === 'assistant') {
      role = 'assistant'; label = 'AGENT';
    } else {
      role = 'tool'; label = 'TOOL';
    }
    return '<div class="thread-message ' + role + '-msg' + extraClass + '">' +
      '<div class="role-label ' + role + '">' + label + '</div>' +
      '<div class="content" id="msg-' + t.id + '-' + i + '">' + m.content.substring(0, 1500) + '</div>' +
      (m.content.length > 200 ? '<div class="expand-btn" onclick="toggleMsg(\'' + t.id + '-' + i + '\')">Mehr</div>' : '') +
      '</div>';
  }).join('');

  return '<div class="thread-card" data-categories="' + t.categories.join(',') +
    '" data-project="' + t.project + '" data-platform="' + t.platform + '">' +
    '<div class="thread-header">' +
      '<span class="title">' + t.title.substring(0, 80) + '</span>' +
      '<div class="meta">' + hasInterrupt + hasFollowup +
        '<span class="platform-badge ' + t.platform + '">' + t.platform + '</span>' +
        '<span class="date">' + t.date + '</span>' +
        '<span class="msg-count">' + t.message_count + ' msgs</span>' +
      '</div>' +
    '</div>' +
    '<div class="thread-tags">' + tags + '</div>' +
    '<div class="thread-body">' + msgs + '</div>' +
    '<div class="thread-footer">' +
      '<span class="project">' + t.project + '</span>' +
      '<span class="thread-id">' + t.id + '</span>' +
    '</div>' +
  '</div>';
}

// ── Main Render ──────────────────────────────────────────────────────────
function render() {
  var q = document.getElementById('searchInput').value.toLowerCase();
  var listEl = document.getElementById('threadList');
  if (!listEl) return;

  var filtered = THREADS.filter(function(t) {
    if (activeFilter && t.categories.indexOf(activeFilter) === -1) return false;
    if (q && t.title.toLowerCase().indexOf(q) === -1 &&
        t.user_input.toLowerCase().indexOf(q) === -1 &&
        t.project.toLowerCase().indexOf(q) === -1) return false;
    return true;
  });

  if (currentView === 'category') {
    var groups = {};
    filtered.forEach(function(t) {
      var cat = t.categories[0] || 'UNCATEGORIZED';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    });
    var html = '';
    Object.entries(groups).sort(function(a, b) { return b[1].length - a[1].length; }).forEach(function(entry) {
      var cat = entry[0], threads = entry[1];
      html += '<div class="category-group">';
      html += '<div class="category-group-header">' + cat + ' <span class="count">' + threads.length + '</span></div>';
      threads.forEach(function(t) { html += renderThreadCard(t); });
      html += '</div>';
    });
    listEl.innerHTML = html;
  } else if (currentView === 'project') {
    var groups = {};
    filtered.forEach(function(t) {
      var proj = t.project || 'unknown';
      if (!groups[proj]) groups[proj] = [];
      groups[proj].push(t);
    });
    var html = '';
    Object.entries(groups).sort(function(a, b) { return b[1].length - a[1].length; }).forEach(function(entry) {
      var proj = entry[0], threads = entry[1];
      html += '<div class="project-group">';
      html += '<div class="project-group-header">' + proj + ' <span class="count">' + threads.length + ' threads</span></div>';
      threads.forEach(function(t) { html += renderThreadCard(t); });
      html += '</div>';
    });
    listEl.innerHTML = html;
  } else {
    var html = '';
    filtered.forEach(function(t) { html += renderThreadCard(t); });
    listEl.innerHTML = html;
  }

  if (!filtered.length) {
    listEl.innerHTML = '<div style="color:var(--text2);padding:24px;text-align:center">Keine Treffer.</div>';
  }
}

// ── Message Toggle ───────────────────────────────────────────────────────
function toggleMsg(id) {
  var el = document.getElementById('msg-' + id);
  if (!el) return;
  var btn = el.nextElementSibling;
  el.classList.toggle('expanded');
  if (btn) btn.textContent = el.classList.contains('expanded') ? 'Weniger' : 'Mehr';
}

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  renderStats();
  renderPlatformStats();
  renderChips();
  document.getElementById('searchInput').oninput = render;
  render();
});
