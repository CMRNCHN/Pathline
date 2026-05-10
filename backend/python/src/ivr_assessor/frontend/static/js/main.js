// Requires: common/time.js, common/dom.js, common/api.js, common/state.js

let padBuffer = '';

function detectInputType(text) {
  const trimmed = text.trim();
  if (!trimmed) return '';
  return /^[\s0-9*#]+$/.test(trimmed) ? 'dtmf' : 'speech';
}

function normalizeTarget(value) {
  const trimmed = (value || '').trim();
  if (!trimmed) return '';
  if (trimmed.startsWith('+')) return '+' + trimmed.replace(/[^\d]/g, '');
  const digits = trimmed.replace(/\D/g, '');
  if (!digits) return '';
  return digits.length === 10 ? ('+1' + digits) : ('+' + digits);
}

function updateInputChip() {
  const input = $('smart-input');
  const chip = $('input-chip');
  const type = detectInputType(input.value);
  chip.textContent = type === '' ? 'Auto-detect' : (type === 'dtmf' ? 'DTMF' : 'Speech');
  chip.className = 'smart-input-chip ' + type;
}

function titleize(value) {
  return String(value || '')
    .replace(/[._]/g, ' ')
    .replace(/:/g, ' / ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatClock(tsSeconds) {
  if (typeof tsSeconds !== 'number') return '—';
  return new Date(tsSeconds * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatMaybeSeconds(value) {
  if (value == null || value === '') return '—';
  return String(value);
}

function inferTimelineTone(entry) {
  const marker = String(entry.marker || '').toLowerCase();
  const detail = String(entry.detail || '').toLowerCase();
  if (marker === 'prompt') return 'accent';
  if (marker === 'action') return 'ok';
  if (marker.includes('disconnect') || marker.includes('rejected') || detail.includes('error') || detail.includes('failed')) return 'error';
  if (entry.category === 'cleanup' || marker.includes('cleanup') || marker.includes('reset')) return 'warn';
  if (entry.source === 'websocket') return 'accent';
  return 'neutral';
}

function classifyTimelineEntry(entry) {
  const marker = String(entry.marker || '').toLowerCase();
  const detail = String(entry.detail || '').toLowerCase();
  if (entry.source === 'session_event' && marker === 'prompt') return 'transcript';
  if (entry.source === 'session_event' && marker === 'action') return 'routing';
  if (entry.source === 'websocket') return 'websocket';
  if (entry.category === 'cleanup' || marker.includes('cleanup') || marker.includes('reset')) return 'cleanup';
  if (marker.includes('replay') || marker.includes('record') || marker.includes('artifact') || marker.includes('snapshot') || detail.includes('replay')) return 'replay';
  return 'routing';
}

function formatActionText(rawText) {
  if (!rawText) return 'Operator action';
  if (rawText.startsWith('dtmf:')) return 'Sent DTMF ' + rawText.slice(5);
  if (rawText.startsWith('say:')) return 'Spoke "' + rawText.slice(4) + '"';
  return rawText;
}

function buildTimelineRows() {
  const diagnostics = AppState.runtimeDiagnostics || {};
  const session = (((diagnostics.replay_diagnostics || {}).session) || {});
  const chronology = session.chronology || [];
  const chronologyLookup = {};
  chronology.forEach((item) => {
    chronologyLookup[(item.kind || '') + ':' + item.t_ms] = item;
  });

  const timeline = (diagnostics.timeline || []).map((entry, index) => {
    const matched = chronologyLookup[(entry.marker || '') + ':' + entry.t_ms] || null;
    const type = classifyTimelineEntry(entry);
    const tone = inferTimelineTone(entry);
    const rawText = matched ? matched.text : '';
    let title = titleize(entry.marker || entry.source || 'event');
    let detail = entry.detail || '';
    let badge = titleize(type);

    if (entry.source === 'session_event' && entry.marker === 'prompt') {
      title = 'Transcript';
      detail = rawText || detail;
      badge = 'Transcript';
    } else if (entry.source === 'session_event' && entry.marker === 'action') {
      title = rawText && rawText.startsWith('dtmf:') ? 'DTMF Action' : 'Voice Action';
      detail = formatActionText(rawText || detail);
      badge = 'Routing';
    } else if (entry.source === 'websocket') {
      title = titleize(entry.marker || 'WebSocket');
      detail = entry.detail || 'Lifecycle event';
      badge = 'WebSocket';
    } else if (type === 'cleanup') {
      title = titleize(entry.marker || 'cleanup');
      badge = 'Cleanup';
    } else if (type === 'replay') {
      title = titleize(entry.marker || 'artifact');
      badge = 'Replay';
    } else if (entry.source === 'startup') {
      badge = 'Startup';
    } else {
      badge = entry.source === 'checkpoint' ? 'Runtime' : badge;
    }

    return {
      id: (entry.source || 'event') + ':' + (entry.marker || 'event') + ':' + (entry.t_ms != null ? entry.t_ms : Math.round((entry.ts || 0) * 1000)) + ':' + index,
      type,
      tone,
      title,
      detail: detail || 'No detail surfaced',
      badge,
      meta: entry.t_ms != null ? formatTimer(Math.floor(entry.t_ms / 1000)) : formatClock(entry.ts),
      rawText,
      source: entry.source || 'event',
      sortTs: entry.ts || 0,
      sortIndex: index,
    };
  });

  const legacyRows = (AppState.legacyLogs || []).map((item, index) => ({
    id: 'legacy:' + item.at + ':' + index,
    type: 'routing',
    tone: item.level === 'error' ? 'error' : (item.level === 'accent' ? 'accent' : 'neutral'),
    title: 'Operator Notice',
    detail: item.message,
    badge: 'Notice',
    meta: new Date(item.at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
    rawText: item.message,
    source: 'legacy',
    sortTs: item.at / 1000,
    sortIndex: timeline.length + index,
  }));

  const merged = timeline.concat(legacyRows).sort((left, right) => {
    if (left.sortTs !== right.sortTs) return left.sortTs - right.sortTs;
    return left.sortIndex - right.sortIndex;
  });

  AppState.timelineRows = merged;

  const filter = AppState.selectedTimelineFilter || 'all';
  if (filter === 'all') return merged;
  return merged.filter((row) => row.type === filter);
}

function renderHeaderStatus() {
  const statusEl = $('hdr-status');
  const status = AppState.latestStatus || {};
  statusEl.className = 'status-pill';
  if (status.error) {
    statusEl.classList.add('tone-error');
    statusEl.textContent = 'Error';
  } else if (status.is_running) {
    statusEl.classList.add('tone-ok');
    statusEl.textContent = 'Active';
  } else {
    statusEl.classList.add('tone-warn');
    statusEl.textContent = 'Idle';
  }
  $('btn-end').disabled = !AppState.callRunning;
}

function renderCaption() {
  const status = AppState.latestStatus || {};
  const box = $('caption-box');
  const text = $('caption-text');
  if (status.live_caption) {
    box.classList.remove('is-idle');
    text.textContent = status.live_caption;
  } else {
    box.classList.add('is-idle');
    text.textContent = AppState.callRunning ? 'Waiting for a live caption update…' : 'No active caption. Start a session to see live transcript flow.';
  }
}

function renderTimeline() {
  const timelineEl = $('transcript');
  const rows = buildTimelineRows();
  const selectedId = AppState.selectedTimelineEvent ? AppState.selectedTimelineEvent.id : null;

  if (!rows.length) {
    timelineEl.innerHTML = renderEmptyState('◦', 'No timeline events yet', 'Structured runtime activity will appear here.');
    return;
  }

  if (selectedId && !rows.some((row) => row.id === selectedId)) {
    AppState.selectedTimelineEvent = null;
  }

  timelineEl.innerHTML = renderTimelineRows(rows, AppState.selectedTimelineEvent ? AppState.selectedTimelineEvent.id : null);
}

function summarizeGraphContext() {
  const graph = AppState.latestGraph || {};
  const target = normalizeTarget($('f-target').value);
  const savedMap = (AppState.savedMaps || []).find((item) => item.target === target) || null;
  const branchCount = Object.values(graph).reduce((total, node) => total + Object.keys((node && node.branches) || {}).length, 0);
  const activePrompt = (AppState.selectedTimelineEvent && AppState.selectedTimelineEvent.type === 'transcript' && AppState.selectedTimelineEvent.rawText)
    || ((AppState.latestStatus || {}).active_prompt)
    || '';
  const cards = [
    { label: 'Nodes', value: String(Object.keys(graph).length) },
    { label: 'Branches', value: String(branchCount) },
    { label: 'Target', value: target || 'Unset' },
    { label: 'Saved', value: savedMap ? ((savedMap.session_count || 0) + ' sessions') : ((AppState.savedMaps || []).length + ' maps') },
  ];
  if (activePrompt) {
    cards.push({ label: 'Context', value: activePrompt.slice(0, 30) + (activePrompt.length > 30 ? '…' : '') });
  }
  $('graph-meta').innerHTML = renderGraphMeta(cards);
}

function renderGraph() {
  const graphBox = $('graph-box');
  const graph = AppState.latestGraph || {};
  summarizeGraphContext();

  if (!graph || Object.keys(graph).length === 0) {
    graphBox.innerHTML = renderEmptyState('⋯', 'No graph nodes discovered yet', 'Live graph context appears after prompts and actions accumulate.');
    return;
  }

  const selected = AppState.selectedTimelineEvent;
  const activePrompt = (selected && selected.type === 'transcript' && selected.rawText)
    || ((AppState.latestStatus || {}).active_prompt)
    || '';
  const activeBranch = selected && selected.rawText && selected.rawText.startsWith('dtmf:')
    ? selected.rawText.slice(5)
    : '';

  const entries = Object.entries(graph).sort((left, right) => {
    const leftMatch = activePrompt && (left[0] === activePrompt || left[0].includes(activePrompt));
    const rightMatch = activePrompt && (right[0] === activePrompt || right[0].includes(activePrompt));
    if (leftMatch && !rightMatch) return -1;
    if (!leftMatch && rightMatch) return 1;
    return 0;
  });

  graphBox.innerHTML = entries.slice(0, 10).map(([prompt, node]) => {
    const branches = Object.entries((node && node.branches) || {});
    const confidence = typeof node.confidence === 'number' ? Math.round(node.confidence * 100) + '%' : '—';
    const isActive = !!activePrompt && (prompt === activePrompt || prompt.includes(activePrompt) || activePrompt.includes(prompt));
    return (
      '<article class="graph-node' + (isActive ? ' is-active' : '') + '">' +
        '<div class="graph-node-title">' + escapeHtml(prompt) + '</div>' +
        '<div class="graph-node-meta">' + confidence + ' confidence · ' + branches.length + ' branches</div>' +
        (
          branches.length
            ? branches.slice(0, 6).map(([branch, observation]) => {
              const nextPrompts = (observation.next_prompts || []).slice(0, 2).join(' → ') || 'END';
              const branchActive = isActive && activeBranch && branch === activeBranch;
              return (
                '<div class="graph-branch' + (branchActive ? ' is-active' : '') + '">' +
                  '<span class="graph-branch-key">' + escapeHtml(branch) + '</span>' +
                  '<span class="graph-branch-value">' + escapeHtml(nextPrompts) + '</span>' +
                '</div>'
              );
            }).join('')
            : '<div class="diagnostic-row meta">No branch observations yet.</div>'
        ) +
      '</article>'
    );
  }).join('');
}

function renderHeartbeat() {
  const metrics = AppState.runtimeMetrics || {};
  const diagnostics = AppState.runtimeDiagnostics || {};
  const summary = diagnostics.summary || {};
  const stream = metrics.stream_server || {};
  const streamLast = stream.last_stream_metrics || {};
  const session = metrics.session || {};
  const queue = session.queue || {};
  const runtime = metrics.runtime || {};
  const staleness = metrics.staleness || {};
  const diagnose = AppState.diagnose || {};
  const issues = diagnose.issues || [];

  const speechValue = streamLast.stt_connected === true
    ? 'Connected'
    : (streamLast.stt_connected === false ? 'Unavailable' : 'Unknown');
  const speechTone = streamLast.stt_connected === true
    ? 'ok'
    : (streamLast.stt_connected === false && AppState.callRunning ? 'error' : 'neutral');

  const cards = [
    {
      label: 'Runtime',
      value: summary.session_active ? 'Running' : 'Idle',
      meta: 'Launch #' + (runtime.launch_sequence || 0),
      tone: summary.session_active ? 'ok' : 'neutral',
    },
    {
      label: 'Session',
      value: session.target || (((diagnostics.replay_diagnostics || {}).session || {}).target) || 'No target',
      meta: AppState.callRunning ? ('Events ' + (summary.session_event_count || 0)) : 'Awaiting session',
      tone: AppState.callRunning ? 'accent' : 'neutral',
    },
    {
      label: 'WebSocket',
      value: String(stream.active_streams || 0) + ' stream · ' + String(stream.listen_clients || 0) + ' listen',
      meta: stream.last_stream_disconnect_reason || 'No disconnect signal',
      tone: stream.active_streams ? 'ok' : 'neutral',
    },
    {
      label: 'Speech',
      value: speechValue,
      meta: 'STT ' + (streamLast.stt_backend || 'Not surfaced') + ' · TTS Not surfaced',
      tone: speechTone,
    },
    {
      label: 'Queue',
      value: queue.current_depth != null ? ('Depth ' + queue.current_depth) : 'Inactive',
      meta: queue.max_depth_seen != null ? ('Max ' + queue.max_depth_seen + ' · puts ' + queue.puts_total + ' · gets ' + queue.gets_total) : 'No queue metrics',
      tone: queue.current_depth > 0 ? 'accent' : 'neutral',
    },
    {
      label: 'Checkpoints',
      value: String(runtime.checkpoint_count || 0),
      meta: runtime.last_checkpoint ? String(runtime.last_checkpoint.stage || 'checkpoint') : 'No checkpoint yet',
      tone: runtime.checkpoint_count ? 'accent' : 'neutral',
    },
    {
      label: 'Health',
      value: issues.length ? (issues.length + ' issue' + (issues.length === 1 ? '' : 's')) : (diagnose.ok === true ? 'Ready' : 'Unknown'),
      meta: staleness.is_stale ? ('Idle ' + formatMaybeSeconds(staleness.idle_for_s) + 's') : 'Fresh runtime',
      tone: issues.length ? 'warn' : (diagnose.ok === true ? 'ok' : (staleness.is_stale ? 'warn' : 'neutral')),
    },
  ];

  $('heartbeat-strip').innerHTML = renderHeartbeatCards(cards);
}

function renderControlStatus() {
  const diagnostics = AppState.runtimeDiagnostics || {};
  const metrics = AppState.runtimeMetrics || {};
  const stream = metrics.stream_server || {};
  const streamLast = stream.last_stream_metrics || {};
  const queue = ((diagnostics.queue_visibility || {}).session_queue) || {};
  const statusItems = [
    {
      label: 'Session',
      value: AppState.callRunning ? 'Live' : 'Idle',
      meta: ((diagnostics.summary || {}).session_target) || '—',
    },
    {
      label: 'Stream',
      value: stream.active_streams ? 'Connected' : 'Waiting',
      meta: stream.last_stream_close_code != null ? ('Close ' + stream.last_stream_close_code) : '—',
    },
    {
      label: 'STT',
      value: streamLast.stt_connected === true ? 'Connected' : (streamLast.stt_connected === false ? 'Unavailable' : 'Unknown'),
      meta: streamLast.stt_backend || 'Not surfaced',
    },
    {
      label: 'Queue',
      value: queue.current_depth != null ? String(queue.current_depth) : '—',
      meta: queue.max_depth_seen != null ? ('max ' + queue.max_depth_seen) : '—',
    },
  ];

  $('control-status').innerHTML = statusItems.map((item) =>
    '<div class="status-item">' +
      '<span class="status-item-label">' + escapeHtml(item.label) + '</span>' +
      '<span class="status-item-value">' + escapeHtml(item.value) + '</span>' +
      '<span class="status-item-meta">' + escapeHtml(item.meta) + '</span>' +
    '</div>'
  ).join('');
}

function sectionHtml(title, content) {
  return (
    '<section class="drawer-section">' +
      '<div class="drawer-section-title">' + escapeHtml(title) + '</div>' +
      content +
    '</section>'
  );
}

function renderList(items, cssClass) {
  if (!items.length) return renderEmptyState('◦', 'Nothing surfaced', 'No items available for this view.');
  return '<div class="diagnostic-list">' + items.map((item) =>
    '<div class="diagnostic-row' + (cssClass ? ' ' + cssClass : '') + '">' + escapeHtml(item) + '</div>'
  ).join('') + '</div>';
}

function renderDrawer() {
  const panel = $('drawer-panel');
  const body = $('drawer-body');
  const diagnostics = AppState.runtimeDiagnostics || {};
  const metrics = AppState.runtimeMetrics || {};
  const summary = diagnostics.summary || {};
  const queueVisibility = diagnostics.queue_visibility || {};
  const websocket = diagnostics.websocket_lifecycle || {};
  const replayDiagnostics = diagnostics.replay_diagnostics || {};
  const session = replayDiagnostics.session || {};
  const artifacts = replayDiagnostics.artifact_summary || {};
  const activeTab = AppState.activeDrawerTab || 'runtime';

  panel.classList.toggle('is-open', !!AppState.drawerOpen);
  $('drawer-toggle').textContent = AppState.drawerOpen ? 'Collapse' : 'Expand';

  document.querySelectorAll('[data-drawer-tab]').forEach((tab) => {
    tab.classList.toggle('is-active', tab.dataset.drawerTab === activeTab);
  });

  if (!AppState.drawerOpen) return;

  let html = '';

  if (activeTab === 'runtime') {
    const startupEvents = ((metrics.startup || {}).events || []).slice(-6).map((item) => {
      return formatClock(item.ts) + ' · ' + titleize(item.stage || 'startup') + (item.detail ? ' · ' + item.detail : '');
    });
    const checkpoints = ((metrics.runtime || {}).checkpoints || []).slice(-6).map((item) => {
      return formatClock(item.ts) + ' · ' + titleize(item.stage || 'checkpoint') + (item.detail ? ' · ' + item.detail : '');
    });
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Overview', renderKeyValueTable([
          { key: 'Session active', value: String(!!summary.session_active) },
          { key: 'Session target', value: summary.session_target || '—' },
          { key: 'Runtime checkpoints', value: String(summary.runtime_checkpoint_count || 0) },
          { key: 'Cleanup count', value: String(summary.cleanup_count || 0) },
          { key: 'Stale runtime', value: String(!!summary.stale_runtime) },
        ])) +
        sectionHtml('Operator Notices', renderList((AppState.legacyLogs || []).slice(-8).map((item) => {
          return new Date(item.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' · ' + item.message;
        }), 'meta')) +
        sectionHtml('Startup Events', renderList(startupEvents, 'meta')) +
        sectionHtml('Runtime Checkpoints', renderList(checkpoints, 'meta')) +
      '</div>';
  } else if (activeTab === 'session') {
    const chronology = (session.chronology || []).slice(-10).map((item) => {
      return formatTimer(Math.floor((item.t_ms || 0) / 1000)) + ' · ' + titleize(item.kind || 'event') + ' · ' + item.text_preview;
    });
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Session Summary', renderKeyValueTable([
          { key: 'Target', value: session.target || '—' },
          { key: 'Duration', value: session.duration_ms != null ? formatDuration(session.duration_ms) : '—' },
          { key: 'Graph nodes', value: String(session.graph_node_count || 0) },
          { key: 'Manual mode', value: String(!!session.manual_mode) },
          { key: 'Event count', value: String(session.event_count || 0) },
          { key: 'Error', value: session.error || '—' },
        ])) +
        sectionHtml('Recent Chronology', renderList(chronology, 'meta')) +
      '</div>';
  } else if (activeTab === 'websocket') {
    const counts = websocket.counts || {};
    const countRows = Object.keys(counts).sort().map((key) => ({ key, value: String(counts[key]) }));
    const recent = (websocket.recent || []).slice(-10).map((item) => {
      return formatClock(item.ts) + ' · ' + String(item.endpoint || 'ws') + ' · ' + String(item.phase || 'event');
    });
    const streamLast = ((metrics.stream_server || {}).last_stream_metrics) || {};
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Lifecycle Counts', countRows.length ? renderKeyValueTable(countRows) : renderEmptyState('◦', 'No lifecycle counts', 'WebSocket counters appear after connections.')) +
        sectionHtml('Last Stream Metrics', renderKeyValueTable([
          { key: 'Status', value: streamLast.stream_status || '—' },
          { key: 'STT backend', value: streamLast.stt_backend || '—' },
          { key: 'STT connected', value: String(streamLast.stt_connected) },
          { key: 'Connect ms', value: streamLast.stt_connect_ms != null ? String(streamLast.stt_connect_ms) : '—' },
          { key: 'Last error', value: (metrics.stream_server || {}).last_error || '—' },
        ])) +
        sectionHtml('Recent Lifecycle', renderList(recent, 'meta')) +
      '</div>';
  } else if (activeTab === 'queue') {
    const queue = queueVisibility.session_queue || {};
    const checkpoint = queueVisibility.last_checkpoint || {};
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Queue Metrics', renderKeyValueTable([
          { key: 'Current depth', value: queue.current_depth != null ? String(queue.current_depth) : '—' },
          { key: 'Max depth', value: queue.max_depth_seen != null ? String(queue.max_depth_seen) : '—' },
          { key: 'Puts total', value: queue.puts_total != null ? String(queue.puts_total) : '—' },
          { key: 'Gets total', value: queue.gets_total != null ? String(queue.gets_total) : '—' },
          { key: 'Elapsed ms', value: queue.elapsed_ms != null ? String(queue.elapsed_ms) : '—' },
        ])) +
        sectionHtml('Last Checkpoint', renderKeyValueTable([
          { key: 'Stage', value: checkpoint.stage || '—' },
          { key: 'Category', value: checkpoint.category || '—' },
          { key: 'Detail', value: checkpoint.detail || '—' },
          { key: 't_ms', value: checkpoint.t_ms != null ? String(checkpoint.t_ms) : '—' },
        ])) +
      '</div>';
  } else if (activeTab === 'artifacts') {
    const recordingArtifacts = (artifacts.recording_artifacts || []).map((item) => {
      return String(item.recording_sid || 'artifact') + ' · ' + String(item.status || 'unknown');
    });
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Artifact Summary', renderKeyValueTable([
          { key: 'Reports', value: artifacts.reports ? String(artifacts.reports.file_count) : '—' },
          { key: 'Recordings', value: artifacts.recordings ? String(artifacts.recordings.file_count) : '—' },
          { key: 'Replays', value: artifacts.replays ? String(artifacts.replays.file_count) : '—' },
          { key: 'Snapshots', value: artifacts.snapshots ? String(artifacts.snapshots.file_count) : '—' },
        ])) +
        sectionHtml('Recording Artifacts', renderList(recordingArtifacts, 'meta')) +
      '</div>';
  } else if (activeTab === 'smoke') {
    const diagnose = AppState.diagnose || {};
    const issues = diagnose.issues || [];
    const fixes = (diagnose.fixes || []).map((item) => item.label || item.action || 'Suggested fix');
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Health Signals', renderKeyValueTable([
          { key: 'Twilio auth', value: diagnose.twilio ? String(!!diagnose.twilio.ok) : 'Unknown' },
          { key: 'Deepgram key', value: diagnose.deepgram ? String(!!diagnose.deepgram.ok) : 'Unknown' },
          { key: 'Stream listening', value: diagnose.stream_server ? String(!!diagnose.stream_server.listening) : 'Unknown' },
          { key: 'Tunnel backend', value: diagnose.tunnel ? String(diagnose.tunnel.backend || 'Unknown') : 'Unknown' },
          { key: 'Suggested stream', value: diagnose.suggested_stream_url || '—' },
        ])) +
        sectionHtml('Issues', renderList(issues.map((item) => String(item)), 'meta')) +
        sectionHtml('Suggested Fixes', renderList(fixes, 'meta')) +
      '</div>';
  }

  body.innerHTML = html || renderEmptyState('◦', 'No drawer data', 'Select a diagnostics tab once runtime data is available.');
}

function renderOperatorConsole() {
  renderHeaderStatus();
  renderCaption();
  renderHeartbeat();
  renderTimeline();
  renderGraph();
  renderControlStatus();
  renderDrawer();

  document.querySelectorAll('[data-filter]').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.filter === AppState.selectedTimelineFilter);
  });
}

window.renderOperatorConsole = renderOperatorConsole;

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

async function fetchStatus() {
  try {
    const data = await api.getStatus();
    const previousRunning = AppState.callRunning;
    AppState.latestStatus = data;
    AppState.callRunning = !!data.is_running;
    AppState.latestGraph = data.graph || {};
    if (typeof data.manual_mode === 'boolean' && data.manual_mode !== AppState.manualMode) {
      AppState.manualMode = data.manual_mode;
      applyModeUI();
    }
    if (data.logs) data.logs.forEach(addLog);
    if (!AppState.callRunning && previousRunning) {
      fetchRuntimeMetrics();
      fetchRuntimeDiagnostics();
      fetchMaps();
    }
    renderOperatorConsole();
  } catch (error) {
    console.error('Status fetch error:', error);
  }
}

async function fetchRuntimeMetrics() {
  try {
    const data = await api.getRuntimeMetrics();
    AppState.runtimeMetrics = data;
    const session = data.session || {};
    if (typeof session.elapsed_ms === 'number') {
      AppState.sessionElapsedMs = session.elapsed_ms;
      AppState.lastElapsedSyncAt = Date.now();
    }
    renderOperatorConsole();
  } catch (error) {
    console.error('Runtime metrics fetch error:', error);
  }
}

async function fetchRuntimeDiagnostics() {
  try {
    AppState.runtimeDiagnostics = await api.getRuntimeDiagnostics();
    renderOperatorConsole();
  } catch (error) {
    console.error('Runtime diagnostics fetch error:', error);
  }
}

async function fetchDiagnose(force) {
  const now = Date.now();
  if (!force && AppState.lastDiagnoseAt && now - AppState.lastDiagnoseAt < 30000) return;
  try {
    AppState.diagnose = await api.getDiagnose();
    AppState.lastDiagnoseAt = now;
    renderOperatorConsole();
  } catch (error) {
    console.error('Diagnose fetch error:', error);
  }
}

async function fetchMaps() {
  try {
    const data = await api.getMaps();
    AppState.savedMaps = data.maps || [];
    renderOperatorConsole();
  } catch (error) {
    console.error('Maps fetch error:', error);
  }
}

async function startCall() {
  let target = normalizeTarget($('f-target').value);
  if (!target) {
    addLog('[error] Please enter a target phone number');
    return;
  }

  addLog('[system] Starting call to ' + target + '...');

  const btn = $('btn-start');
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Calling…';

  try {
    const data = await api.startCall({
      target,
      user: '',
      sid: '',
      token: '',
      tnum: '',
      stream_url: null,
      manual_mode: false,
    });
    if (data && data.status === 'started') {
      addLog('[ok] Call initiated via backend API');
      fetchStatus();
      fetchRuntimeMetrics();
      fetchRuntimeDiagnostics();
      fetchMaps();
    } else {
      addLog('[error] Backend returned: ' + JSON.stringify(data));
    }
  } catch (error) {
    addLog('[error] ' + error.message);
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = originalText;
    }, 1800);
  }
}

async function endCall() {
  try {
    await api.endCall();
    addLog('[system] End-session requested');
    fetchStatus();
    fetchRuntimeMetrics();
    fetchRuntimeDiagnostics();
  } catch (error) {
    addLog('[error] Failed to end session: ' + error.message);
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
    fetchRuntimeDiagnostics();
  } catch (error) {
    addLog('[error] Failed to send: ' + error.message);
  }
}

async function toggleMode() {
  const next = !AppState.manualMode;
  try {
    const data = await api.setMode(next);
    AppState.manualMode = !!data.manual_mode;
    applyModeUI();
    fetchStatus();
  } catch (error) {
    addLog('[error] Failed to toggle mode: ' + error.message);
  }
}

function openDrawer(tabName) {
  AppState.drawerOpen = true;
  AppState.activeDrawerTab = tabName;
  if (tabName === 'smoke') fetchDiagnose(false);
  renderOperatorConsole();
}

function syncTimer() {
  const metrics = AppState.runtimeMetrics || {};
  const session = metrics.session || {};
  let elapsedMs = typeof session.elapsed_ms === 'number' ? session.elapsed_ms : AppState.sessionElapsedMs;
  if (AppState.callRunning && AppState.lastElapsedSyncAt) {
    elapsedMs += Date.now() - AppState.lastElapsedSyncAt;
  }
  $('timer').textContent = formatTimer(Math.max(0, Math.floor((elapsedMs || 0) / 1000)));
}

$('btn-start').addEventListener('click', startCall);
$('btn-end').addEventListener('click', endCall);
$('btn-settings').addEventListener('click', () => openDrawer('smoke'));
$('btn-open-runtime').addEventListener('click', () => openDrawer('runtime'));
$('btn-open-artifacts').addEventListener('click', () => openDrawer('artifacts'));
$('btn-open-smoke').addEventListener('click', () => openDrawer('smoke'));
$('btn-refresh-diagnostics').addEventListener('click', () => {
  fetchRuntimeMetrics();
  fetchRuntimeDiagnostics();
  fetchDiagnose(true);
});
$('btn-refresh-maps').addEventListener('click', fetchMaps);
$('drawer-toggle').addEventListener('click', () => {
  AppState.drawerOpen = !AppState.drawerOpen;
  renderOperatorConsole();
});
$('mode-toggle').addEventListener('click', toggleMode);

$('smart-input').addEventListener('input', updateInputChip);
$('smart-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendInput();
  }
});
document.querySelector('.send-btn').addEventListener('click', sendInput);

document.querySelectorAll('.keypad .kbtn').forEach((button) => {
  button.addEventListener('click', () => {
    const digit = button.textContent.split('\n')[0].trim();
    if (!digit) return;
    padBuffer += digit;
    $('pad-display').textContent = padBuffer;
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
    fetchRuntimeDiagnostics();
  } catch (error) {
    addLog('[error] DTMF send failed: ' + error.message);
  }
});

document.querySelectorAll('[data-filter]').forEach((button) => {
  button.addEventListener('click', () => {
    AppState.selectedTimelineFilter = button.dataset.filter;
    renderOperatorConsole();
  });
});

$('transcript').addEventListener('click', (event) => {
  const row = event.target.closest('[data-timeline-id]');
  if (!row || !AppState.timelineRows) return;
  AppState.selectedTimelineEvent = AppState.timelineRows.find((item) => item.id === row.dataset.timelineId) || null;
  renderOperatorConsole();
});

document.querySelectorAll('[data-drawer-tab]').forEach((button) => {
  button.addEventListener('click', () => {
    AppState.activeDrawerTab = button.dataset.drawerTab;
    if (AppState.activeDrawerTab === 'smoke') fetchDiagnose(false);
    renderOperatorConsole();
  });
});

$('f-target').addEventListener('change', fetchMaps);

applyModeUI();
updateInputChip();
renderOperatorConsole();

api.getConfig().then((cfg) => {
  if (cfg && cfg.target) $('f-target').value = cfg.target.replace(/^\+1/, '');
  fetchMaps();
}).catch((error) => console.log('Config load failed:', error));

setInterval(fetchStatus, 500);
setInterval(fetchRuntimeMetrics, 2000);
setInterval(fetchRuntimeDiagnostics, 2500);
setInterval(syncTimer, 1000);

fetchStatus();
fetchRuntimeMetrics();
fetchRuntimeDiagnostics();
fetchDiagnose(true);
