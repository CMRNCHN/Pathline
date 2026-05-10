// Requires: common/time.js, common/dom.js, common/api.js, common/state.js

let padBuffer = '';
let startTime = null;

function detectInputType(text) {
  const trimmed = text.trim();
  if (!trimmed) return '';
  return /^[\s0-9*#]+$/.test(trimmed) ? 'dtmf' : 'speech';
}

function updateInputChip() {
  const input = $('smart-input');
  const chip = $('input-chip');
  const type = detectInputType(input.value);
  chip.textContent = type === '' ? 'Auto-detect' : (type === 'dtmf' ? '⚡ DTMF' : '🗣 Speech');
  chip.className = 'smart-input-chip ' + type;
}

function renderGraph(graph) {
  const graphBox = $('graph-box');
  if (!graph || Object.keys(graph).length === 0) {
    graphBox.innerHTML = '<div style="color:var(--text-3);text-align:center;padding:20px;">No nodes discovered yet</div>';
    return;
  }
  let html = '';
  Object.entries(graph).slice(0, 10).forEach(([prompt, node], idx) => {
    const conf = (node.confidence * 100).toFixed(0);
    const branchCount = Object.keys(node.branches || {}).length;
    html += '<div class="graph-node prompt">[Node ' + (idx + 1) + '] ' + prompt.slice(0, 60) + (prompt.length > 60 ? '...' : '') + '</div>';
    if (node.branches) {
      Object.entries(node.branches).slice(0, 5).forEach(([branch, obs]) => {
        const nextPrompts = obs.next_prompts ? obs.next_prompts.slice(0, 2).join(' → ') : 'END';
        html += '<div class="graph-branch">→ ' + branch + ': ' + nextPrompts.slice(0, 40) + '</div>';
      });
    }
    html += '<div style="color:var(--text-4);font-size:10px;padding:2px 0;">' + conf + '% • ' + branchCount + ' branches</div>';
  });
  graphBox.innerHTML = html || '<div style="color:var(--text-3);">Graph data loading...</div>';
}

async function fetchStatus() {
  try {
    const data = await api.getStatus();
    const statusEl = $('hdr-status');
    if (data.error) {
      statusEl.textContent = '❌ ' + data.error.split('\n')[0].slice(0, 20);
      statusEl.style.background = 'var(--danger-soft)';
      statusEl.style.color = 'var(--danger)';
    } else if (data.is_running) {
      statusEl.textContent = '🔴 Active';
      statusEl.style.background = 'rgba(248,113,113,.16)';
      statusEl.style.color = 'var(--danger)';
    } else {
      statusEl.textContent = '⚠ Idle';
      statusEl.style.background = 'var(--warn-soft)';
      statusEl.style.color = 'var(--warn)';
    }

    if (typeof data.manual_mode === 'boolean' && data.manual_mode !== AppState.manualMode) {
      AppState.manualMode = data.manual_mode;
      applyModeUI();
    }

    if (data.logs) data.logs.forEach(addLog);

    if (data.live_caption) {
      $('caption-box').style.display = 'flex';
      $('caption-text').textContent = data.live_caption;
    } else {
      $('caption-box').style.display = 'none';
    }

    if (data.graph && Object.keys(data.graph).length > 0) renderGraph(data.graph);

    AppState.callRunning = data.is_running;
  } catch(e) {
    console.error('Status fetch error:', e);
  }
}

async function startCall() {
  let target = $('f-target').value.trim();
  if (!target) { addLog('[error] Please enter a target phone number'); return; }
  if (!target.startsWith('+')) target = '+1' + target.replace(/\D/g, '');

  addLog('[system] Starting call to ' + target + '...');

  const btn = $('btn-start');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ Calling...';
  btn.style.opacity = '0.7';

  try {
    const data = await api.startCall({
      target, user: '', sid: '', token: '', tnum: '', stream_url: null, manual_mode: false,
    });
    if (data && data.status === 'started') {
      addLog('[ok] Call initiated via backend API');
      startTime = Date.now();
    } else {
      addLog('[error] Backend returned: ' + JSON.stringify(data));
    }
  } catch(e) {
    addLog('[error] ' + e.message);
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.innerHTML = originalText;
      btn.style.opacity = '1';
    }, 2000);
  }
}

async function sendInput() {
  const input = $('smart-input');
  const text = input.value.trim();
  if (!text) return;
  const type = detectInputType(text);
  try {
    if (type === 'dtmf') {
      await api.injectDtmf(text);
    } else {
      await api.injectVoice(text);
    }
    addLog('[' + type.toUpperCase() + '] You: ' + text);
    input.value = '';
    updateInputChip();
  } catch(e) {
    addLog('[error] Failed to send: ' + e.message);
  }
}

$('btn-start').addEventListener('click', startCall);
$('smart-input').addEventListener('input', updateInputChip);
$('smart-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendInput(); }
});
document.querySelector('.send-btn').addEventListener('click', sendInput);

function applyModeUI() {
  const wrap = $('mode-toggle');
  const state = $('mode-toggle-state');
  const text = $('mode-toggle-text');
  if (AppState.manualMode) {
    wrap.classList.add('is-manual');
    state.textContent = 'OFF';
    text.textContent = 'Manual';
  } else {
    wrap.classList.remove('is-manual');
    state.textContent = 'ON';
    text.textContent = 'Auto-pilot';
  }
}

async function toggleMode() {
  const next = !AppState.manualMode;
  try {
    const data = await api.setMode(next);
    AppState.manualMode = !!data.manual_mode;
    applyModeUI();
  } catch(e) {
    addLog('[error] Failed to toggle mode: ' + e.message);
  }
}

$('mode-toggle').addEventListener('click', toggleMode);
applyModeUI();

document.querySelectorAll('.keypad .kbtn').forEach(btn => {
  btn.addEventListener('click', () => {
    const digit = btn.textContent.split('\n')[0].trim();
    if (digit) {
      padBuffer += digit;
      $('pad-display').textContent = padBuffer;
    }
  });
});

document.querySelector('.pad-del').addEventListener('click', () => {
  padBuffer = padBuffer.slice(0, -1);
  $('pad-display').textContent = padBuffer || '—';
});

document.querySelector('.pad-send').addEventListener('click', async () => {
  if (!padBuffer) return;
  try {
    await api.injectDtmf(padBuffer);
    addLog('[DTMF] You: ' + padBuffer);
    padBuffer = '';
    $('pad-display').textContent = '—';
  } catch(e) {
    addLog('[error] DTMF send failed: ' + e.message);
  }
});

// Timer
let _timerSeconds = 0;
setInterval(() => {
  if (AppState.callRunning) {
    _timerSeconds++;
    $('timer').textContent = formatTimer(_timerSeconds);
  }
}, 1000);

// Load saved target
api.getConfig().then(cfg => {
  if (cfg && cfg.target) $('f-target').value = cfg.target.replace(/^\+1/, '');
}).catch(e => console.log('Config load failed:', e));

// Poll
setInterval(fetchStatus, 500);
fetchStatus();
