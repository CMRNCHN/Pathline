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
  if (entry.source === 'session_event' && marker === 'action') return 'response';
  if (entry.source === 'websocket') return 'websocket';
  if (entry.category === 'cleanup' || marker.includes('cleanup') || marker.includes('reset')) return 'notice';
  if (marker.includes('replay') || marker.includes('record') || marker.includes('artifact') || marker.includes('snapshot') || detail.includes('replay')) return 'review';
  return 'traversal';
}

function timelineGroupLabel(type) {
  if (type === 'transcript') return 'Prompt Matches';
  if (type === 'response') return 'Response Anchors';
  if (type === 'traversal') return 'Traversal Logic';
  if (type === 'notice') return 'Run Notices';
  if (type === 'review') return 'Review / Replay Evidence';
  if (type === 'websocket') return 'Technical Diagnostics';
  return 'Live Operations Events';
}

function formatActionText(rawText) {
  if (!rawText) return 'Human operator response';
  if (rawText.startsWith('dtmf:')) return 'Response anchor: DTMF ' + rawText.slice(5);
  if (rawText.startsWith('say:')) return 'Response anchor: speech "' + rawText.slice(4) + '"';
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
      title = 'Prompt Match';
      detail = rawText || detail;
      badge = 'Prompt Match';
    } else if (entry.source === 'session_event' && entry.marker === 'action') {
      title = rawText && rawText.startsWith('dtmf:') ? 'DTMF Response Anchor' : 'Speech Response Anchor';
      detail = formatActionText(rawText || detail);
      badge = 'Response Anchor';
    } else if (entry.source === 'websocket') {
      title = titleize(entry.marker || 'Technical Diagnostics');
      detail = entry.detail || 'Technical diagnostics event';
      badge = 'Diagnostics';
    } else if (type === 'cleanup') {
      title = titleize(entry.marker || 'cleanup');
      badge = 'Notice';
    } else if (type === 'review') {
      title = titleize(entry.marker || 'artifact');
      badge = 'Review';
    } else if (entry.source === 'startup') {
      badge = 'Startup';
    } else {
      badge = entry.source === 'checkpoint' ? 'Traversal Logic' : badge;
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
    type: 'notice',
    tone: item.level === 'error' ? 'error' : (item.level === 'accent' ? 'accent' : 'neutral'),
    title: 'Run Notice',
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
    statusEl.textContent = 'Exception';
  } else if (status.is_running) {
    statusEl.classList.add('tone-ok');
    statusEl.textContent = 'Active Run';
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
    text.textContent = AppState.callRunning ? 'Waiting for the next heard prompt…' : 'No current prompt yet. Start a bounded run to watch prompt flow.';
  }
}

function renderTimeline() {
  const timelineEl = $('transcript');
  const rows = buildTimelineRows();
  const selectedId = AppState.selectedTimelineEvent ? AppState.selectedTimelineEvent.id : null;

  if (!rows.length) {
    timelineEl.innerHTML = renderEmptyState('◦', 'No live operations events yet', 'Start a bounded run to monitor prompt matching, response anchoring, traversal logic, and run notices.');
    return;
  }

  if (selectedId && !rows.some((row) => row.id === selectedId)) {
    AppState.selectedTimelineEvent = null;
  }

  const selectedFilter = AppState.selectedTimelineFilter || 'all';
  if (selectedFilter !== 'all') {
    timelineEl.innerHTML =
      '<div class="timeline-group-label">' + escapeHtml(timelineGroupLabel(selectedFilter)) + '</div>' +
      renderTimelineRows(rows, selectedId);
    return;
  }

  const groups = [
    {
      label: 'Live Operations / Active Run',
      rows: rows.filter((row) => ['transcript', 'response', 'traversal', 'notice'].includes(row.type)),
    },
    {
      label: 'Review / Replay Evidence',
      rows: rows.filter((row) => row.type === 'review'),
    },
    {
      label: 'Technical Diagnostics',
      rows: rows.filter((row) => row.type === 'websocket'),
    },
  ];

  timelineEl.innerHTML = groups
    .filter((group) => group.rows.length)
    .map((group) =>
      '<div class="timeline-group-label">' + escapeHtml(group.label) + '</div>' +
      renderTimelineRows(group.rows, selectedId)
    )
    .join('');
}

function summarizeGraphContext() {
  const graph = AppState.latestGraph || {};
  const target = normalizeTarget($('f-target').value);
  const savedMap = (AppState.savedMaps || []).find((item) => item.target === target) || null;
  const branchCount = Object.values(graph).reduce((total, node) => total + Object.keys((node && node.branches) || {}).length, 0);
  const openBranchCount = Object.values(graph).reduce((total, node) => {
    return total + Object.values((node && node.branches) || {}).filter((observation) => {
      const nextPrompts = (observation && observation.next_prompts) || [];
      return !nextPrompts.length;
    }).length;
  }, 0);
  const activePrompt = (AppState.selectedTimelineEvent && AppState.selectedTimelineEvent.type === 'transcript' && AppState.selectedTimelineEvent.rawText)
    || ((AppState.latestStatus || {}).active_prompt)
    || '';
  const cards = activePrompt ? [
    { label: 'Current State', value: activePrompt.slice(0, 30) + (activePrompt.length > 30 ? '…' : '') },
    { label: 'Prompt Nodes', value: String(Object.keys(graph).length) },
    { label: 'Response Branches', value: String(branchCount) },
    { label: 'Unresolved Branches', value: String(openBranchCount) },
  ] : [
    { label: 'Prompt Nodes', value: String(Object.keys(graph).length) },
    { label: 'Response Branches', value: String(branchCount) },
    { label: 'Unresolved Branches', value: String(openBranchCount) },
    { label: 'Target IVR', value: target || 'Unset' },
  ];
  cards.push({ label: 'Saved Context', value: savedMap ? ((savedMap.session_count || 0) + ' prior runs') : ((AppState.savedMaps || []).length + ' saved maps') });
  $('graph-meta').innerHTML = renderGraphMeta(cards);
}

function renderGraph() {
  const graphBox = $('graph-box');
  const graph = AppState.latestGraph || {};
  summarizeGraphContext();

  if (!graph || Object.keys(graph).length === 0) {
    graphBox.innerHTML = renderEmptyState('⋯', 'No IVR state mapping yet', 'Current state, prompt nodes, and response branches appear after prompt matches and response anchors accumulate.');
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
        '<div class="graph-node-title">' + (isActive ? '<span class="state-pill tone-accent">Current IVR State</span> ' : '') + escapeHtml(prompt) + '</div>' +
        '<div class="graph-node-meta">' + confidence + ' prompt matching confidence · ' + branches.length + ' response branches observed</div>' +
        (
          branches.length
            ? branches.slice(0, 6).map(([branch, observation]) => {
              const nextPrompts = (observation.next_prompts || []).slice(0, 2).join(' → ') || 'End of observed path';
              const branchActive = isActive && activeBranch && branch === activeBranch;
              return (
                '<div class="graph-branch' + (branchActive ? ' is-active' : '') + '">' +
                  '<span class="graph-branch-key">Response ' + escapeHtml(branch) + '</span>' +
                  '<span class="graph-branch-value">' + escapeHtml(nextPrompts) + '</span>' +
                '</div>'
              );
            }).join('')
            : '<div class="diagnostic-row meta">No response branches observed from this IVR state yet.</div>'
        ) +
      '</article>'
    );
  }).join('') + (entries.length > 10
    ? '<div class="diagnostic-row meta">Showing the first 10 IVR state nodes. Refresh maps or inspect replay/review evidence for the full mapping.</div>'
    : '');
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

  const cards = [];
  const status = AppState.latestStatus || {};
  const target = session.target || (((diagnostics.replay_diagnostics || {}).session || {}).target) || normalizeTarget($('f-target').value);

  if (status.error) {
    cards.push({
      label: 'P1 Exception',
      value: 'Run error surfaced',
      meta: status.error,
      tone: 'error',
      priority: 1,
    });
  }

  issues.slice(0, 3).forEach((issue, index) => {
    cards.push({
      label: index === 0 ? 'P3 Readiness' : 'P3 Readiness',
      value: 'Pre-run issue',
      meta: String(issue),
      tone: 'warn',
      priority: 4,
    });
  });

  if (AppState.callRunning && streamLast.stt_connected === false) {
    cards.push({
      label: 'P1 Prompt Capture',
      value: 'Unavailable',
      meta: streamLast.stt_backend || 'Speech backend not connected',
      tone: 'error',
      priority: 2,
    });
  }

  if (AppState.callRunning && stream.active_streams === 0) {
    cards.push({
      label: 'P2 Media Stream',
      value: 'No active stream',
      meta: stream.last_stream_disconnect_reason || 'Waiting for Twilio media stream',
      tone: 'warn',
      priority: 2,
    });
  }

  if (stream.last_error) {
    cards.push({
      label: 'P1 Stream Exception',
      value: 'Stream error',
      meta: stream.last_error,
      tone: 'error',
      priority: 1,
    });
  }

  if (staleness.is_stale) {
    cards.push({
      label: 'P2 Runtime Health',
      value: 'Runtime stale',
      meta: 'Idle ' + formatMaybeSeconds(staleness.idle_for_s) + 's',
      tone: 'warn',
      priority: 3,
    });
  }

  if (queue.current_depth > 0) {
    cards.push({
      label: 'P2 Operator Response',
      value: 'Checkpoint pending',
      meta: queue.max_depth_seen != null ? ('Depth ' + queue.current_depth + ' · max ' + queue.max_depth_seen) : 'Queue awaiting deterministic traversal response',
      tone: 'accent',
      priority: 2,
    });
  }

  if (!cards.length) {
    cards.push({
      label: 'Run Health',
      value: 'Nominal',
      meta: (AppState.callRunning ? 'Active bounded run' : 'Idle') + ' · target ' + (target || 'unset'),
      tone: diagnose.ok === true || AppState.callRunning ? 'ok' : 'neutral',
      priority: 5,
    });
    cards.push({
      label: 'IVR State Context',
      value: summary.session_active ? 'Running' : 'Ready',
      meta: 'Launch #' + (runtime.launch_sequence || 0) + ' · checkpoints ' + (runtime.checkpoint_count || 0),
      tone: summary.session_active ? 'accent' : 'neutral',
      priority: 5,
    });
  }

  $('heartbeat-strip').innerHTML = renderHeartbeatCards(cards
    .sort((left, right) => (left.priority || 9) - (right.priority || 9))
    .slice(0, 3));
}

function renderControlStatus() {
  const diagnostics = AppState.runtimeDiagnostics || {};
  const metrics = AppState.runtimeMetrics || {};
  const stream = metrics.stream_server || {};
  const streamLast = stream.last_stream_metrics || {};
  const queue = ((diagnostics.queue_visibility || {}).session_queue) || {};
  const statusItems = [
    {
      label: 'Active Run',
      value: AppState.callRunning ? 'Live operations' : 'Idle',
      meta: ((diagnostics.summary || {}).session_target) || '—',
    },
    {
      label: 'Media Stream',
      value: stream.active_streams ? 'Connected' : (AppState.callRunning ? 'No active stream' : 'Waiting'),
      meta: stream.last_stream_close_code != null ? ('Close ' + stream.last_stream_close_code) : '—',
    },
    {
      label: 'Prompt Capture',
      value: streamLast.stt_connected === true ? 'Connected' : (streamLast.stt_connected === false ? 'Unavailable' : 'Unknown'),
      meta: streamLast.stt_backend || 'Not surfaced',
    },
    {
      label: 'Alert Priority',
      value: queue.current_depth > 0 ? 'P2 response needed' : 'No active exception',
      meta: queue.max_depth_seen != null ? ('queue max ' + queue.max_depth_seen) : '—',
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

function buildRouteRefinementItems(session, queueVisibility, artifacts) {
  const chronology = session.chronology || [];
  const prompts = chronology.filter((item) => item.kind === 'prompt');
  const actions = chronology.filter((item) => item.kind === 'action');
  const items = [];

  if (session.error) {
    items.push('Review the last run error before reusing this route: ' + session.error);
  }
  if (prompts.length > actions.length + 1) {
    items.push('Some prompt matches do not have response anchors yet; review missing route responses after the active run.');
  }

  const repeatedPrompt = prompts.find((item, index) => {
    if (index === 0) return false;
    return item.text_preview && item.text_preview === prompts[index - 1].text_preview;
  });
  if (repeatedPrompt) {
    items.push('Repeated prompts suggest a loop or retry branch; confirm the expected route check and starting DTMF path.');
  }

  const queue = queueVisibility.session_queue || {};
  if ((queue.current_depth || 0) > 0) {
    items.push('Checkpoint queue items remained pending at the last snapshot; verify traversal logic and human operator response timing.');
  }

  if ((session.graph_node_count || 0) === 0 && prompts.length > 0) {
    items.push('Prompt activity was captured without persisted map growth; re-run to confirm IVR state mapping coverage.');
  }

  const reports = ((artifacts.reports || {}).file_count) || 0;
  const recordings = ((artifacts.recordings || {}).file_count) || 0;
  if (!reports && !recordings) {
    items.push('No replay/review artifacts were captured for this run; collect evidence before extracting a reusable suite.');
  }

  if (!items.length) {
    items.push('Prompt matching, response anchoring, and evidence capture look ready for the next bounded run.');
  }
  return items;
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
  panel.classList.toggle('is-secondary-active-run', !!AppState.callRunning);
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
    const routeRefinement = buildRouteRefinementItems(session, queueVisibility, artifacts);
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Bounded Run Health', renderKeyValueTable([
          { key: 'Run active', value: String(!!summary.session_active) },
          { key: 'Target IVR', value: summary.session_target || '—' },
          { key: 'Runtime checkpoints', value: String(summary.runtime_checkpoint_count || 0) },
          { key: 'Cleanup count', value: String(summary.cleanup_count || 0) },
          { key: 'Stale runtime', value: String(!!summary.stale_runtime) },
        ])) +
        sectionHtml('Route Refinement Cues', renderList(routeRefinement, 'meta')) +
        sectionHtml('Exception-First Run Alerts', renderList((AppState.legacyLogs || []).slice(-8).map((item) => {
          return new Date(item.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' · ' + item.message;
        }), 'meta')) +
        sectionHtml('Secondary Startup Diagnostics', renderList(startupEvents, 'meta')) +
        sectionHtml('Runtime Checkpoint Chronology', renderList(checkpoints, 'meta')) +
      '</div>';
  } else if (activeTab === 'session') {
    const chronology = (session.chronology || []).slice(-10).map((item) => {
      return formatTimer(Math.floor((item.t_ms || 0) / 1000)) + ' · ' + titleize(item.kind || 'event') + ' · ' + item.text_preview;
    });
    const promptCount = (session.chronology || []).filter((item) => item.kind === 'prompt').length;
    const actionCount = (session.chronology || []).filter((item) => item.kind === 'action').length;
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Call-Path Replay', renderKeyValueTable([
          { key: 'Target', value: session.target || '—' },
          { key: 'Duration', value: session.duration_ms != null ? formatDuration(session.duration_ms) : '—' },
          { key: 'Graph nodes', value: String(session.graph_node_count || 0) },
          { key: 'Manual response mode', value: String(!!session.manual_mode) },
          { key: 'Prompt matches', value: String(promptCount) },
          { key: 'Anchored responses', value: String(actionCount) },
          { key: 'Event count', value: String(session.event_count || 0) },
          { key: 'Error', value: session.error || '—' },
        ])) +
        sectionHtml('Prompt & Action Chronology', renderList(chronology, 'meta')) +
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
        sectionHtml('Technical Diagnostics Counts', countRows.length ? renderKeyValueTable(countRows) : renderEmptyState('◦', 'No diagnostics counts', 'Technical diagnostics counters appear after connections.')) +
        sectionHtml('Technical Diagnostics Snapshot', renderKeyValueTable([
          { key: 'Status', value: streamLast.stream_status || '—' },
          { key: 'STT backend', value: streamLast.stt_backend || '—' },
          { key: 'STT connected', value: String(streamLast.stt_connected) },
          { key: 'Connect ms', value: streamLast.stt_connect_ms != null ? String(streamLast.stt_connect_ms) : '—' },
          { key: 'Last error', value: (metrics.stream_server || {}).last_error || '—' },
        ])) +
        sectionHtml('Recent Technical Diagnostics', renderList(recent, 'meta')) +
      '</div>';
  } else if (activeTab === 'queue') {
    const queue = queueVisibility.session_queue || {};
    const checkpoint = queueVisibility.last_checkpoint || {};
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Checkpoint Verification Summary', renderKeyValueTable([
          { key: 'Current depth', value: queue.current_depth != null ? String(queue.current_depth) : '—' },
          { key: 'Max depth', value: queue.max_depth_seen != null ? String(queue.max_depth_seen) : '—' },
          { key: 'Puts total', value: queue.puts_total != null ? String(queue.puts_total) : '—' },
          { key: 'Gets total', value: queue.gets_total != null ? String(queue.gets_total) : '—' },
          { key: 'Elapsed ms', value: queue.elapsed_ms != null ? String(queue.elapsed_ms) : '—' },
        ])) +
        sectionHtml('Latest Checkpoint Verification', renderKeyValueTable([
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
        sectionHtml('Evidence & Artifacts Summary', renderKeyValueTable([
          { key: 'Reports', value: artifacts.reports ? String(artifacts.reports.file_count) : '—' },
          { key: 'Recordings', value: artifacts.recordings ? String(artifacts.recordings.file_count) : '—' },
          { key: 'Replays', value: artifacts.replays ? String(artifacts.replays.file_count) : '—' },
          { key: 'Snapshots', value: artifacts.snapshots ? String(artifacts.snapshots.file_count) : '—' },
        ])) +
        sectionHtml('Captured Evidence', renderList(recordingArtifacts, 'meta')) +
      '</div>';
  } else if (activeTab === 'smoke') {
    const diagnose = AppState.diagnose || {};
    const issues = diagnose.issues || [];
    const fixes = (diagnose.fixes || []).map((item) => item.label || item.action || 'Suggested fix');
    html =
      '<div class="drawer-grid">' +
        sectionHtml('Run Readiness', renderKeyValueTable([
          { key: 'Twilio auth', value: diagnose.twilio ? String(!!diagnose.twilio.ok) : 'Unknown' },
          { key: 'Deepgram key', value: diagnose.deepgram ? String(!!diagnose.deepgram.ok) : 'Unknown' },
          { key: 'Stream listening', value: diagnose.stream_server ? String(!!diagnose.stream_server.listening) : 'Unknown' },
          { key: 'Tunnel backend', value: diagnose.tunnel ? String(diagnose.tunnel.backend || 'Unknown') : 'Unknown' },
          { key: 'Suggested stream', value: diagnose.suggested_stream_url || '—' },
        ])) +
        sectionHtml('Readiness Issues', renderList(issues.map((item) => String(item)), 'meta')) +
        sectionHtml('Suggested Fixes', renderList(fixes, 'meta')) +
      '</div>';
  }

  body.innerHTML = html || renderEmptyState('◦', 'No review data', 'Select a review tab once run data is available.');
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
    state.textContent = 'MANUAL';
    text.textContent = 'Manual Response';
  } else {
    wrap.classList.remove('is-manual');
    state.textContent = 'AUTO';
    text.textContent = 'Deterministic Traversal';
  }
}

async function fetchStatus() {
  try {
    const data = await api.getStatus();
    const previousRunning = AppState.callRunning;
    AppState.latestStatus = data;
    AppState.callRunning = !!data.is_running;
    if (AppState.callRunning && !previousRunning) {
      AppState.drawerOpen = false;
      AppState.activeDrawerTab = 'runtime';
    }
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
$('btn-settings').addEventListener('click', () => openDrawer('runtime'));
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
