/**
 * SpecAgent Dashboard — Main Application
 *
 * Connects to the WebSocket, renders agent cards, pipeline phases,
 * handles HITM gates, and bridges data to the pixel-art engine.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────
const WS_URL = `ws://${location.host}/ws`;
const PHASES = ['intake', 'spec', 'architecture', 'coding', 'testing', 'review', 'delivery'];
const PHASE_LABELS = {
  intake: 'Intake',
  spec: 'Spec',
  architecture: 'Architecture',
  coding: 'Coding',
  testing: 'Testing',
  review: 'Review',
  delivery: 'Delivery',
};
const PHASE_COLORS = {
  intake: '#8b92b5',
  spec: '#9b59b6',
  architecture: '#e67e22',
  coding: '#27ae60',
  testing: '#2980b9',
  review: '#c0392b',
  delivery: '#f1c40f',
};
const AGENT_ORDER = ['spec', 'architect', 'coder', 'tester', 'reviewer'];
const STATUS_LABELS = {
  idle: 'Idle',
  thinking: 'Thinking…',
  working: 'Working',
  awaiting_hitm: 'Awaiting Review',
  celebrating: 'Done!',
  error: 'Error',
};

// ─────────────────────────────────────────────────────────────────────────────
// DOM refs
// ─────────────────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const connStatus   = $('connStatus');
const taskEmpty    = $('taskEmpty');
const taskInfo     = $('taskInfo');
const taskTitleEl  = $('taskTitle');
const taskIdEl     = $('taskId');
const taskHitmEl   = $('taskHitm');
const progressBar  = $('progressBar');
const progressLabel= $('progressLabel');
const phaseList    = $('phaseList');
const agentsGrid   = $('agentsGrid');
const logStream    = $('logStream');
const hitmGate     = $('hitmGate');
const hitmMessage  = $('hitmMessage');
const hitmContent  = $('hitmContent');
const hitmNotes    = $('hitmNotes');
const specPanel    = $('specPanel');
const specContent  = $('specContent');
const specVersion  = $('specVersion');
const dashView     = $('dashView');
const pixelView    = $('pixelView');
const officeCanvas = $('officeCanvas');
const pixelLegend  = $('pixelLegend');
const modalOverlay = $('modalOverlay');

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let ws = null;
let vizMode = false;         // false = dashboard, true = pixel art
let currentCheckpointId = null;
let lastKnownLogs = [];
let logCount = 0;

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket
// ─────────────────────────────────────────────────────────────────────────────
function connect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    connStatus.textContent = '● CONNECTED';
    connStatus.className = 'conn-indicator connected';
  };

  ws.onclose = () => {
    connStatus.textContent = '● DISCONNECTED';
    connStatus.className = 'conn-indicator error';
    setTimeout(connect, 3000);
  };

  ws.onerror = () => {
    connStatus.textContent = '● ERROR';
    connStatus.className = 'conn-indicator error';
  };

  ws.onmessage = evt => {
    let data;
    try { data = JSON.parse(evt.data); } catch { return; }
    if (data.type === 'ping') return;
    render(data);
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Render full state snapshot
// ─────────────────────────────────────────────────────────────────────────────
function render(state) {
  renderTask(state.task);
  renderAgents(state.agents);
  renderSpec(state.spec);
  renderHitm(state.pending_checkpoint);
  appendNewLogs(state.task);

  // Sync to pixel art engine
  if (state.agents) {
    const agentMap = {};
    for (const [key, val] of Object.entries(state.agents)) {
      agentMap[key] = val;
    }
    window.PixelArt.setAgentStates(agentMap);
  }
}

// ── Task / pipeline ──
function renderTask(task) {
  if (!task) {
    taskEmpty.classList.remove('hidden');
    taskInfo.classList.add('hidden');
    phaseList.innerHTML = '';
    return;
  }
  taskEmpty.classList.add('hidden');
  taskInfo.classList.remove('hidden');

  taskTitleEl.textContent = task.title;
  taskIdEl.textContent = `#${task.id}`;
  taskHitmEl.classList.toggle('hidden', !task.hitm_enabled);

  progressBar.style.width = `${task.progress_pct}%`;
  progressLabel.textContent = `${task.progress_pct}%`;

  // Phase list
  phaseList.innerHTML = '';
  for (const phase of PHASES) {
    const pData = (task.phases || {})[phase] || {};
    const isCurrent = task.current_phase === phase;
    const status = pData.status || 'pending';

    const item = document.createElement('div');
    item.className = `phase-item${isCurrent ? ' active' : ''} ${status === 'completed' ? 'completed' : ''}`;

    const dotClass = isCurrent ? 'active'
                   : status === 'completed' ? 'completed'
                   : status === 'failed' ? 'error' : '';

    item.innerHTML = `
      <span class="phase-dot ${dotClass}" style="${isCurrent ? `--accent:${PHASE_COLORS[phase]}` : ''}"></span>
      <span class="phase-name" style="color:${isCurrent ? PHASE_COLORS[phase] : ''}">${PHASE_LABELS[phase] || phase}</span>
      <span class="phase-status">${formatPhaseStatus(status, isCurrent)}</span>
    `;
    phaseList.appendChild(item);
  }
}

function formatPhaseStatus(status, isCurrent) {
  if (isCurrent && status === 'in_progress') return '⚡';
  if (status === 'completed') return '✓';
  if (status === 'failed') return '✗';
  if (status === 'awaiting_review') return '⏸';
  return '';
}

// ── Agents ──
function renderAgents(agents) {
  if (!agents) return;
  agentsGrid.innerHTML = '';
  for (const key of AGENT_ORDER) {
    const a = agents[key];
    if (!a) continue;
    const meta = a.meta || {};
    const status = a.status || 'idle';
    const card = document.createElement('div');
    card.className = `agent-card ${status} fade-in`;
    card.style.setProperty('--agent-color', meta.color || '#4a6cf7');
    card.dataset.agent = key;
    card.innerHTML = `
      <span class="agent-emoji">${meta.emoji || '🤖'}</span>
      <div class="agent-name">${meta.name || key}</div>
      <div class="agent-role">${meta.role || ''}</div>
      <div class="agent-status-pill status-${status}">
        <span class="status-dot"></span>
        ${STATUS_LABELS[status] || status}
      </div>
      <div class="agent-activity">${a.current_activity || ''}</div>
      <div class="agent-output">${escapeHtml(a.output_preview || '')}</div>
    `;
    agentsGrid.appendChild(card);
  }
}

// ── Spec ──
function renderSpec(spec) {
  if (!spec) {
    specPanel.classList.add('hidden');
    return;
  }
  specPanel.classList.remove('hidden');
  specVersion.textContent = `v${spec.version || 1}`;
  specContent.textContent = spec.summary
    ? `${spec.title}\n\n${spec.summary}\n\n${spec.user_stories?.length || 0} user stories · ${
        (spec.user_stories || []).reduce((s, us) => s + (us.acceptance_criteria?.length || 0), 0)
      } acceptance criteria`
    : 'Spec loading…';
}

// ── HITM ──
function renderHitm(pending) {
  if (!pending || !pending.ids || pending.ids.length === 0) {
    hitmGate.classList.add('hidden');
    currentCheckpointId = null;
    return;
  }
  currentCheckpointId = pending.ids[0];
  hitmGate.classList.remove('hidden');

  // Scroll checkpoint gate into view
  hitmGate.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Logs ──
function appendNewLogs(task) {
  if (!task || !task.logs) return;
  const logs = task.logs;
  if (logs.length === logCount) return;
  const newLogs = logs.slice(logCount);
  logCount = logs.length;

  for (const entry of newLogs) {
    const el = document.createElement('div');
    el.className = `log-entry log-${entry.level || 'info'} fade-in`;
    const ts = entry.ts ? entry.ts.slice(11, 19) : '';
    el.innerHTML = `
      <span class="log-ts">${ts}</span>
      <span class="log-agent">${entry.agent || 'system'}</span>
      <span>${escapeHtml(entry.message || '')}</span>
    `;
    logStream.appendChild(el);
  }
  // Auto-scroll to bottom
  logStream.scrollTop = logStream.scrollHeight;
}

// ─────────────────────────────────────────────────────────────────────────────
// HITM actions
// ─────────────────────────────────────────────────────────────────────────────
$('btnApprove').addEventListener('click', () => {
  if (!currentCheckpointId) return;
  sendHitmResolution(currentCheckpointId, true, hitmNotes.value.trim());
  hitmNotes.value = '';
  hitmGate.classList.add('hidden');
});

$('btnReject').addEventListener('click', () => {
  if (!currentCheckpointId) return;
  sendHitmResolution(currentCheckpointId, false, hitmNotes.value.trim());
  hitmNotes.value = '';
  hitmGate.classList.add('hidden');
});

function sendHitmResolution(checkpointId, approved, notes) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'hitm.resolve',
      checkpoint_id: checkpointId,
      approved,
      notes,
    }));
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// New task modal
// ─────────────────────────────────────────────────────────────────────────────
$('btnNewTask').addEventListener('click', () => {
  modalOverlay.classList.remove('hidden');
  $('inputTitle').focus();
});

$('btnModalCancel').addEventListener('click', () => {
  modalOverlay.classList.add('hidden');
});

$('btnModalRun').addEventListener('click', async () => {
  const title = $('inputTitle').value.trim();
  const desc  = $('inputDesc').value.trim();
  const hitm  = $('checkHitm').checked;

  if (!title || !desc) {
    alert('Please provide both a title and a description.');
    return;
  }

  modalOverlay.classList.add('hidden');
  logCount = 0;
  logStream.innerHTML = '';

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, hitm }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${err.detail || 'Failed to start pipeline'}`);
    }
  } catch (e) {
    alert('Could not reach the server. Is it running?');
  }
});

// Close modal on overlay click
modalOverlay.addEventListener('click', e => {
  if (e.target === modalOverlay) modalOverlay.classList.add('hidden');
});

// ─────────────────────────────────────────────────────────────────────────────
// Visualization mode toggle
// ─────────────────────────────────────────────────────────────────────────────
$('btnVizMode').addEventListener('click', () => {
  vizMode = !vizMode;
  dashView.classList.toggle('hidden', vizMode);
  pixelView.classList.toggle('hidden', !vizMode);
  $('btnVizMode').textContent = vizMode ? '📊 Dashboard' : '🕹 Pixel Mode';

  if (vizMode) {
    buildPixelLegend();
    window.PixelArt.start(officeCanvas);
  } else {
    window.PixelArt.stop();
  }
});

function buildPixelLegend() {
  pixelLegend.innerHTML = '';
  const agents = [
    { name: 'Speck', color: '#4a6cf7', role: 'Spec Writer' },
    { name: 'Arch',  color: '#e67e22', role: 'Architect' },
    { name: 'Cody',  color: '#2ecc71', role: 'Developer' },
    { name: 'Tess',  color: '#9b59b6', role: 'QA Engineer' },
    { name: 'Rex',   color: '#e74c3c', role: 'Reviewer' },
  ];
  for (const a of agents) {
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML = `<span class="legend-dot" style="background:${a.color}"></span>${a.name} — ${a.role}`;
    pixelLegend.appendChild(item);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Log clear
// ─────────────────────────────────────────────────────────────────────────────
$('btnClearLog').addEventListener('click', () => {
  logStream.innerHTML = '';
});

// ─────────────────────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
(async () => {
  // Fetch initial state over HTTP (fast path before WS connects)
  try {
    const res = await fetch('/api/state');
    if (res.ok) render(await res.json());
  } catch {}

  connect();

  // Build phase list skeleton immediately
  phaseList.innerHTML = PHASES.map(p => `
    <div class="phase-item">
      <span class="phase-dot"></span>
      <span class="phase-name">${PHASE_LABELS[p]}</span>
      <span class="phase-status"></span>
    </div>
  `).join('');
})();
