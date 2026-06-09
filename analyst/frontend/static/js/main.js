let activeTestId = null;
let testPollInterval = null;

async function runValidationTest() {
  const target = normalizeTarget($('f-target').value);
  if (!target) {
    alert('Please enter a target phone number in the header');
    return;
  }

  const payload = {
    target_number_ref: target,
    max_duration_seconds: $('test-max-duration').value,
    max_depth: $('test-max-depth').value,
    max_dtmf_actions: $('test-max-dtmf').value,
    stop_on_transfer: $('test-stop-on-transfer').checked,
    stop_on_low_confidence: $('test-stop-on-low-confidence').checked
  };

  try {
    const data = await api.runTelecomTest(payload);
    if (data.status === 'started') {
      activeTestId = data.test_id;
      showTestRunning(true);
      startTestPolling();
      addLog('[test] Validation test started: ' + activeTestId);
    }
  } catch (error) {
    alert('Failed to start test: ' + error.message);
  }
}

async function abortValidationTest() {
  if (!activeTestId) return;
  try {
    await api.abortTelecomTest(activeTestId);
    addLog('[test] Abort requested');
  } catch (error) {
    addLog('[error] Failed to abort: ' + error.message);
  }
}

function showTestRunning(isRunning) {
  $('btn-run-validation-test').classList.toggle('is-hidden', isRunning);
  $('btn-abort-validation-test').classList.toggle('is-hidden', !isRunning);
  $('test-result-summary').classList.remove('is-hidden');
  if (isRunning) {
    $('test-outcome-badge').textContent = 'RUNNING';
    $('test-outcome-badge').className = 'status-pill tone-accent';
    } else {
      $('btn-run-validation-test').classList.remove('is-hidden');
      $('btn-abort-validation-test').classList.add('is-hidden');
    }
}

function startTestPolling() {
  if (testPollInterval) clearInterval(testPollInterval);
  testPollInterval = setInterval(async () => {
    if (!activeTestId) return;
    try {
      const data = await api.getTelecomTestStatus(activeTestId);
      if (data.status === 'completed') {
        clearInterval(testPollInterval);
        testPollInterval = null;
        showTestRunning(false);
        applyTestResult(data.result);
      }
    } catch (error) {
      console.error('Test poll error:', error);
    }
  }, 2000);
}

function applyTestResult(result) {
  if (!result) return;
  const badge = $('test-outcome-badge');
  badge.textContent = result.outcome;
  
  if (result.outcome === 'PASSED') badge.className = 'status-pill tone-ok';
  else if (result.outcome === 'ABORTED' || result.outcome === 'TIMED_OUT') badge.className = 'status-pill tone-warn';
  else if (result.outcome === 'RUNNING') badge.className = 'status-pill tone-accent';
  else badge.className = 'status-pill tone-error';

  $('test-result-details').textContent = `
    Duration: ${Math.round(result.ended_at - result.started_at)}s |
    States: ${result.states_discovered} |
    Events: ${result.events_count} |
    Reason: ${result.safety_stop_reason || 'N/A'}
  `;
  
  $('test-evidence-link').classList.remove('is-hidden');
  
  // Show export button after test completion
  const exportBtn = $('btn-export-bundle');
  if (exportBtn) {
    exportBtn.classList.remove('is-hidden');
    exportBtn.onclick = () => exportBundle(result.session_id, activeTestId);
  }
}

async function exportBundle(sessionId, testId) {
  const btn = $('btn-export-bundle');
  const originalText = btn ? btn.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Exporting...';
  }
  
  try {
    addLog('[test] Exporting evidence bundle for ' + sessionId + '...');
    const data = await api.exportEvidenceBundle({
      session_id: sessionId,
      test_id: testId,
      copy_recording: false
    });
    if (data.status === 'success') {
      addLog('[test] Bundle exported: ' + data.bundle_id);
      showBundleReport(data.bundle_id);
    }
  } catch (error) {
    addLog('[error] Export failed: ' + error.message);
    alert('Export failed: ' + error.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

async function showBundleReport(bundleId) {
  try {
    const report = await api.getBundleReport(bundleId);
    const manifest = await api.getBundleManifest(bundleId);
    
    // Create a simple modal or overlay for the report
    const reportOverlay = document.createElement('div');
    reportOverlay.id = 'report-overlay';
    reportOverlay.className = 'report-overlay';
    reportOverlay.innerHTML = `
      <div class="report-content">
        <div class="report-header">
          <h3>Validation Report: ${bundleId}</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove()">Close</button>
        </div>
        <div class="report-body">
          <div class="report-score">
            <div class="score-circle">${report.qa_score.session_score}</div>
            <div>QA Score</div>
          </div>
          <div class="report-summary">
            <p><strong>Result:</strong> ${report.failure_classification.primary_category}</p>
            <p><strong>Explanation:</strong> ${report.failure_classification.explanation}</p>
          </div>
          <h4>Recommendations</h4>
          <ul>
            ${report.recommendations.map(r => `<li>${r}</li>`).join('')}
          </ul>
          <h4>Benchmarks</h4>
          <ul>
            ${Object.entries(report.benchmarks).map(([k, v]) => `<li>${k}: ${v}</li>`).join('')}
          </ul>
          <h4>Integrity</h4>
          <p>SHA-256: <code>${report.integrity.manifest_sha256}</code></p>
        </div>
      </div>
    `;
    document.body.appendChild(reportOverlay);
  } catch (error) {
    addLog('[error] Failed to load report: ' + error.message);
  }
}

// ... existing code ...

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
  
  // Operational resilience events
  if (marker.includes('stalled') || marker.includes('disconnected')) return 'error';
  if (marker.includes('recovering') || marker.includes('recovery')) return 'accent';
  if (marker.includes('recovered')) return 'ok';
  if (marker.includes('cleaned')) return 'warn';

  if (marker.includes('disconnect') || marker.includes('rejected') || detail.includes('error') || detail.includes('failed')) return 'error';
  if (entry.category === 'cleanup' || marker.includes('cleanup') || marker.includes('reset')) return 'warn';
  if (entry.source === 'websocket') return 'accent';
  return 'neutral';
}

function classifyTimelineEntry(entry) {
  const marker = String(entry.marker || '').toLowerCase();
  const detail = String(entry.detail || '').toLowerCase();
  
  // Operational resilience events
  if (marker.includes('stalled') || 
      marker.includes('recovery') || 
      marker.includes('recovered') || 
      marker.includes('cleaned') ||
      marker.includes('disconnected')) return 'notice';

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
  const status = AppState.latestStatus || {};

  const rel = $('hdr-runtime-state');
  if (rel) {
    if (status.is_running && status.runtime_health) {
      const health = status.runtime_health;
      let state = 'ACTIVE';
      if (health.runtime_state_counts) {
        const counts = health.runtime_state_counts;
        if (counts.STALLING > 0) state = 'STALLING';
        else if (counts.RECOVERING > 0) state = 'RECOVERING';
        else if (counts.DISCONNECTED > 0) state = 'DISCONNECTED';
        else if (counts.FAILED > 0) state = 'FAILED';
      }
      rel.textContent = state;
      rel.classList.remove('is-hidden');
      
      let tone = 'tone-info';
      if (state === 'STALLING') tone = 'tone-warn';
      else if (state === 'DISCONNECTED' || state === 'FAILED') tone = 'tone-error';
      else if (state === 'RECOVERING') tone = 'tone-accent';
      rel.className = 'status-pill ' + tone;
    } else {
      rel.classList.add('is-hidden');
    }
  }

  const liveBtn = $('btn-live-call');
  const hangupBtn = $('btn-hangup-call');
  const interactiveBtn = $('btn-interactive-call');
  if (interactiveBtn) {
    interactiveBtn.classList.toggle('is-active', AppState.currentWorkspace === 'live');
  }
  if (liveBtn) {
    liveBtn.classList.toggle('is-busy', !!status.is_running);
    liveBtn.textContent = status.is_running ? 'Live Now' : 'Live';
  }
  if (hangupBtn) {
    hangupBtn.disabled = !status.is_running;
    hangupBtn.classList.toggle('is-disabled', !status.is_running);
  }
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
  if ($('graph-meta')) $('graph-meta').innerHTML = renderGraphMeta(cards);
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

function renderStatusCard() {
  const diagnostics = AppState.runtimeDiagnostics || {};
  const metrics = AppState.runtimeMetrics || {};
  const stream = metrics.stream_server || {};
  const streamLast = stream.last_stream_metrics || {};
  const session = metrics.session || {};
  const status = AppState.latestStatus || {};
  const runtime = metrics.runtime || {};
  const sink = runtime.prompt_queue || {};
  const health = status.runtime_health || {};

  const target = session.target || normalizeTarget($('f-target').value) || 'Unset';
  const duration = AppState.sessionElapsedMs ? formatDuration(AppState.sessionElapsedMs) : '00:00';

  const items = [
    { label: 'Target', value: target },
    { label: 'Timer', value: duration },
    { label: 'Status', value: AppState.callRunning ? 'Active Run' : 'Idle', tone: AppState.callRunning ? 'ok' : 'warn' },
    { label: 'Health', value: health.active_session_count !== undefined ? `${health.active_session_count} Act / ${health.failed_session_count || 0} Fail` : 'Healthy', tone: (health.failed_session_count > 0 || health.stalled_session_count > 0) ? 'warn' : 'ok' },
    { label: 'Coverage', value: (runtime.checkpoint_count || 0) + ' nodes' },
    { label: 'Confidence', value: status.active_confidence != null ? Math.round(status.active_confidence * 100) + '%' : '—' },
    { label: 'Stream', value: stream.active_streams ? 'Connected' : 'Offline', tone: stream.active_streams ? 'ok' : 'error' },
    { label: 'Persistence', value: sink.persisted_event_count ? sink.persisted_event_count + ' events' : (sink.persisted_event_count === 0 ? 'Active' : 'Offline'), tone: sink.persisted_event_count !== undefined ? 'ok' : 'warn' },
    { label: 'AI Status', value: streamLast.stt_connected ? 'Ready' : 'Wait', tone: streamLast.stt_connected ? 'ok' : 'warn' },
    { label: 'Mode', value: AppState.manualMode ? 'Manual' : 'Auto' },
  ];

  const bar = $('live-status-bar');
  if (!bar) return;

  if (!AppState.callRunning) {
    bar.innerHTML = '';
    bar.classList.remove('is-active');
    return;
  }

  bar.classList.add('is-active');
  const html = '<div class="status-card-compact">' + items.map(item => `
    <div class="status-card-item">
      <div class="status-card-label">${escapeHtml(item.label)}</div>
      <div class="status-card-value ${item.tone ? 'tone-' + item.tone : ''}">${escapeHtml(String(item.value))}</div>
    </div>
  `).join('') + '</div>';

  bar.innerHTML = html;
}

function renderInjectionBar() {
  const root = $('injection-bar-root');
  root.innerHTML = `
    <div class="injection-field-group">
      <input type="text" id="smart-input" class="injection-input" placeholder="Type digits or words…">
      <button class="btn-ptt" id="btn-ptt" type="button">PTT</button>
      <button class="btn-primary" id="btn-send-injection" style="min-height: 38px;">Send</button>
    </div>
  `;

  const input = $('smart-input');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendInput();
  });
  $('btn-send-injection').addEventListener('click', sendInput);

  // PTT Placeholder logic
  const ptt = $('btn-ptt');
  ptt.addEventListener('mousedown', () => ptt.classList.add('active'));
  ptt.addEventListener('mouseup', () => ptt.classList.remove('active'));
  ptt.addEventListener('mouseleave', () => ptt.classList.remove('active'));
}

function renderReadyResponses() {
  const root = $('ready-responses-root');
  const responses = [
    'Representative', 'Billing', 'Support', 'Repeat That',
    'Main Menu', 'Yes', 'No', 'Press 0'
  ];

  root.innerHTML = responses.map(r => `
    <button class="ready-chip" onclick="populateInjection('${escapeHtml(r)}')">${escapeHtml(r)}</button>
  `).join('');
}

window.populateInjection = (text) => {
  const input = $('smart-input');
  if (input) {
    input.value = text;
    input.focus();
  }
};

function renderPromptMarkers() {
  const root = $('prompt-markers-root');
  const markers = [
    'Mark Prompt', 'Mark Response Needed', 'Mark Unknown State',
    'Mark Verification', 'Mark Transfer'
  ];

  root.innerHTML = markers.map(m => `
    <button class="marker-chip" onclick="addLog('[marker] ${escapeHtml(m)}')">${escapeHtml(m)}</button>
  `).join('');
}

function renderRecentEvents() {
  const root = $('recent-events');
  if (!root) return;
  const rows = AppState.timelineRows || [];
  const recent = rows.slice(-20).reverse();

  if (!recent.length) {
    root.innerHTML = '<div class="empty-state">No recent events</div>';
    return;
  }

  root.innerHTML = recent.map(row => `
    <div class="event-row">
      <span class="event-ts">${escapeHtml(row.meta)}</span>
      <span class="event-msg">${escapeHtml(row.title)}: ${escapeHtml(row.detail.slice(0, 60))}</span>
    </div>
  `).join('');
}

function renderUnresolvedStates() {
  const root = $('unresolved-states');
  if (!root) return;
  const graph = AppState.latestGraph || {};
  const unresolved = Object.entries(graph).filter(([p, node]) => {
    const branches = Object.values(node.branches || {});
    return branches.some(b => !(b.next_prompts || []).length);
  });

  if (!unresolved.length) {
    root.innerHTML = '<div class="empty-state">No unresolved states detected</div>';
    return;
  }

  root.innerHTML = unresolved.map(([prompt, node]) => `
    <div class="event-row" style="cursor: pointer;" onclick="inspectState('${escapeHtml(prompt)}')">
      <span class="event-msg">Unresolved: ${escapeHtml(prompt.slice(0, 50))}</span>
      <span class="state-pill tone-warn">Fix</span>
    </div>
  `).join('');
}

window.inspectState = (prompt) => {
  const inspector = $('state-inspector');
  const graph = AppState.latestGraph || {};
  const node = graph[prompt];
  if (!node) return;

  inspector.classList.remove('is-hidden');
  inspector.innerHTML = `
    <div class="panel-header panel-header-spread">
      <h3 class="panel-title">State Inspector</h3>
      <button class="btn-compact btn-tertiary" onclick="$('state-inspector').classList.add('is-hidden')">✕</button>
    </div>
    <div class="drawer-body">
      <div class="section-title">Prompt Text</div>
      <div class="diagnostic-row" style="margin-bottom: 12px;">${escapeHtml(prompt)}</div>
      <div class="section-title">Observed Branches</div>
      ${Object.entries(node.branches || {}).map(([b, obs]) => `
        <div class="graph-branch">
          <span class="graph-branch-key">${escapeHtml(b)}</span>
          <span class="graph-branch-value">${(obs.next_prompts || []).length ? obs.next_prompts.join(', ') : 'Unresolved'}</span>
        </div>
      `).join('')}
    </div>
  `;
};

function renderPrepWorkspace() {
  renderPrepReadinessStrip();
  renderPrepConfig();
  renderPrepChecklist();
  renderPrepTriggers();
  renderPrepReadyResponses();
}

function renderDrawer() {
  const panel = $('drawer-panel');
  if (!panel) return;
  panel.classList.toggle('is-open', AppState.drawerOpen);

  const tabs = document.querySelectorAll('[data-drawer-tab]');
  tabs.forEach(tab => {
    tab.classList.toggle('is-active', tab.dataset.drawerTab === AppState.activeDrawerTab);
  });

  const body = $('drawer-body');
  if (!body) return;

  if (AppState.activeDrawerTab === 'runtime') {
    if (typeof renderRuntimeTab === 'function') renderRuntimeTab(body);
  } else if (AppState.activeDrawerTab === 'queue') {
    if (typeof renderQueueTab === 'function') renderQueueTab(body);
  } else if (AppState.activeDrawerTab === 'artifacts') {
    if (typeof renderArtifactsTab === 'function') renderArtifactsTab(body);
  } else if (AppState.activeDrawerTab === 'session') {
    if (typeof renderSessionTab === 'function') renderSessionTab(body);
  } else if (AppState.activeDrawerTab === 'websocket') {
    if (typeof renderWebsocketTab === 'function') renderWebsocketTab(body);
  } else if (AppState.activeDrawerTab === 'telemetry') {
    body.innerHTML = '<div class="telemetry-monitor" id="telemetry-monitor"></div>';
    renderTelemetryMonitor();
  } else if (AppState.activeDrawerTab === 'smoke') {
    if (typeof renderSmokeTab === 'function') renderSmokeTab(body);
  }
}

function renderPrepReadinessStrip() {
  const root = $('prep-readiness-strip');
  if (!root) return;

  const readiness = getPrepReadiness();
  const metrics = AppState.runtimeMetrics || {};
  const stream = metrics.stream_server || {};
  const diagnostics = AppState.diagnose || {};

  const items = [
    { key: 'backend', label: 'Backend', status: readiness.backend },
    { key: 'tunnel', label: readiness.tunnelLabel, status: readiness.tunnel },
    { key: 'twilio', label: 'Twilio', status: readiness.twilio },
    { key: 'mediaStream', label: 'Media Stream', status: readiness.mediaStream },
    { key: 'wsStream', label: 'WS Stream', status: stream.active_streams ? 'ok' : 'warn' },
    { key: 'stt', label: 'STT Engine', status: readiness.stt },
    { key: 'tts', label: 'TTS Engine', status: readiness.tts },
    { key: 'ai', label: 'AI Model', status: readiness.ai },
    { key: 'recording', label: 'Recording', status: 'ok' },
    { key: 'transcript', label: 'Transcript', status: readiness.stt },
    { key: 'conference', label: 'Conf Bridge', status: readiness.twilio },
    { key: 'artifacts', label: 'Artifacts', status: 'ok' },
    { key: 'suiteEngine', label: 'Suite Engine', status: 'ok' },
    { key: 'templates', label: 'Templates', status: AppState.savedMaps.length ? 'ok' : 'gray' }
  ];

  const legend = [
    { tone: 'ok', label: 'Ready' },
    { tone: 'warn', label: 'Needs attention' },
    { tone: 'error', label: 'Broken' },
    { tone: 'gray', label: 'Not configured' }
  ];

  root.innerHTML = `<div class="status-strip-shell"><div class="status-card-compact">` + items.map((item) => {
    const detail = buildReadinessDetail(item, diagnostics, metrics);
    return `
    <div class="status-card-item status-card-hover" tabindex="0" aria-label="${escapeHtml(item.label)} status details">
      <div class="status-card-label">${escapeHtml(item.label)}</div>
      <div class="status-pill tone-${escapeHtml(item.status)} btn-compact" style="min-height: 22px; font-size: 9px; padding: 0 8px;">
        ${escapeHtml(statusLabel(item.status))}
      </div>
      ${renderReadinessBubble(item, detail)}
    </div>
  `;
  }).join('') + `</div>
    <div class="status-legend" aria-label="Status legend">
      ${legend.map((item) => `
        <div class="status-legend-item">
          <span class="status-legend-dot tone-${escapeHtml(item.tone)}"></span>
          <span>${escapeHtml(item.label)}</span>
        </div>
      `).join('')}
    </div>
  </div>`;
}

function statusLabel(status) {
  if (status === 'ok') return 'Ready';
  if (status === 'error') return 'Broken';
  if (status === 'warn') return 'Warning';
  return 'N/A';
}

function renderReadinessBubble(item, detail) {
  const steps = detail.steps || [];
  return `
    <div class="status-detail-bubble tone-${escapeHtml(item.status)}" role="tooltip">
      <div class="status-detail-title">
        <span>${escapeHtml(item.label)}</span>
        <span class="status-detail-state">${escapeHtml(statusLabel(item.status))}</span>
      </div>
      <div class="status-detail-body">${escapeHtml(detail.message)}</div>
      ${detail.meta ? `<div class="status-detail-meta">${escapeHtml(detail.meta)}</div>` : ''}
      ${steps.length ? `
        <div class="status-detail-steps-title">${item.status === 'error' ? 'Fix' : 'Next steps'}</div>
        <ol class="status-detail-steps">
          ${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('')}
        </ol>
      ` : ''}
    </div>
  `;
}

function buildReadinessDetail(item, diagnostics, metrics) {
  const stream = metrics.stream_server || {};
  const twilio = diagnostics.twilio || {};
  const stt = diagnostics.stt || {};
  const tts = diagnostics.tts || {};
  const tunnel = diagnostics.tunnel || {};
  const issues = diagnostics.issues || [];
  const issueText = issues.length ? issues.join(' ') : '';

  if (item.key === 'backend') {
    if (item.status === 'ok') {
      return { message: 'The local GUI and runtime diagnostics endpoint are responding.', meta: 'GUI: 8080, stream server: 8081' };
    }
    return {
      message: 'The GUI server is not reporting a healthy runtime.',
      steps: ['Restart the GUI with ./run_ivr_assessor.sh live-map-gui.', 'Check the terminal for startup errors.', 'Verify ports 8080 and 8081 are free.'],
    };
  }

  if (item.key === 'tunnel') {
    if (item.status === 'ok') {
      return {
        message: tunnel.configured_url ? 'A public stream URL is configured for Twilio media streaming.' : 'A tunnel is reachable for Twilio media streaming.',
        meta: diagnostics.suggested_stream_url || tunnel.configured_url || '',
      };
    }
    if (item.status === 'gray') {
      return { message: 'Tunnel checks are disabled for local-only mode.', meta: 'Use this only for local demos without Twilio callbacks.' };
    }
    return {
      message: issueText || 'No reachable public tunnel is detected for the stream server.',
      steps: ['Run ngrok http 8081, or launch with TUNNEL_BACKEND=cloudflare.', 'Set IVR_STREAM_URL to wss://<public-host>/stream.', 'Refresh readiness after the tunnel is live.'],
    };
  }

  if (item.key === 'twilio') {
    if (item.status === 'ok') {
      return { message: 'Twilio credentials authenticated successfully.', meta: twilio.account ? `Account: ${twilio.account}` : 'Account fetch succeeded.' };
    }
    return {
      message: twilio.error || 'Twilio credentials are missing or failed authentication.',
      steps: ['Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env.', 'Set TWILIO_PHONE_NUMBER to an owned Twilio number.', 'Rotate and update credentials if Twilio rejects the token.'],
    };
  }

  if (item.key === 'mediaStream') {
    if (item.status === 'ok') {
      return { message: 'The local media stream server is listening and ready for Twilio WebSocket audio.', meta: 'Expected port: 8081' };
    }
    return {
      message: 'The stream server is not reachable locally.',
      steps: ['Restart the GUI so it starts the stream server.', 'Confirm nothing else is using port 8081.', 'Check /api/diagnose after restart.'],
    };
  }

  if (item.key === 'wsStream') {
    if (item.status === 'ok') {
      return { message: 'A WebSocket media stream is currently connected.', meta: `Active streams: ${stream.active_streams || 0}` };
    }
    return {
      message: 'No active Twilio WebSocket stream is connected right now. This is expected before a live call starts.',
      steps: ['Start a live run to create a stream.', 'Confirm Twilio uses the suggested wss:// stream URL with the token.', 'If a call is active, verify the tunnel points to local port 8081.'],
    };
  }

  if (item.key === 'stt' || item.key === 'transcript') {
    if (item.status === 'ok') {
      return { message: 'Speech-to-text is ready for transcript generation.', meta: `Backend: ${stt.backend || 'faster-whisper'}` };
    }
    return {
      message: stt.error || 'Speech-to-text is not ready.',
      steps: ['Install backend dependencies in backend/python/.venv.', 'Use STT_BACKEND=simulated for local demos, or STT_BACKEND=deepgram with DEEPGRAM_API_KEY.', 'For local STT, keep webrtcvad-wheels and faster-whisper installed.'],
    };
  }

  if (item.key === 'tts' || item.key === 'ai') {
    if (item.status === 'ok') {
      return { message: 'Response audio generation is configured.', meta: `Backend: ${tts.backend || 'openai/piper'}` };
    }
    return {
      message: tts.error || 'Text-to-speech is not ready.',
      steps: ['For OpenAI TTS, set OPENAI_API_KEY and TTS_BACKEND=openai.', 'For Piper, set TTS_BACKEND=piper plus PIPER_BINARY and PIPER_VOICE.', 'Refresh readiness after updating .env.'],
    };
  }

  if (item.key === 'recording') {
    return { message: 'Call recording support is ready when Twilio can reach the recording callback.', meta: 'Callback: TWILIO_RECORDING_STATUS_CALLBACK' };
  }

  if (item.key === 'conference') {
    if (item.status === 'ok') {
      return { message: 'Conference bridge controls are available through the authenticated Twilio client.' };
    }
    return {
      message: 'Conference bridge controls depend on valid Twilio credentials.',
      steps: ['Fix Twilio credential readiness first.', 'Confirm USER_PHONE_NUMBER is set for bridged operator calls.'],
    };
  }

  if (item.key === 'templates') {
    if (item.status === 'ok') {
      return { message: 'Saved IVR maps/templates are available for planning and review.', meta: `${AppState.savedMaps.length} saved map${AppState.savedMaps.length === 1 ? '' : 's'}` };
    }
    return {
      message: 'No saved maps/templates are loaded yet.',
      steps: ['Run a route discovery session.', 'Save or import a route suite.', 'Refresh maps from the prep workspace.'],
    };
  }

  if (item.key === 'artifacts') {
    return { message: 'Local artifact storage is available for reports, recordings, events, and replay evidence.' };
  }

  if (item.key === 'suiteEngine') {
    return { message: 'The suite runner UI and local suite storage are ready.' };
  }

  return { message: 'Status detail is available from the current readiness snapshot.' };
}

function getPrepReadiness() {
  const diagnostics = AppState.diagnose || {};
  const streamReady = !!((diagnostics.stream_server || {}).listening || diagnostics.media_stream_ready);
  const tunnel = diagnostics.tunnel || {};
  const tunnelBackend = tunnel.backend || 'ngrok';
  const localOnly = !!tunnel.local_only || tunnelBackend === 'none';
  const tunnelActive = localOnly || !!diagnostics.tunnel_active || !!(diagnostics.ngrok || {}).running || !!diagnostics.suggested_stream_url;
  const sttBackend = (diagnostics.stt || {}).backend || '';
  return {
    backend: diagnostics.server_active === false ? 'error' : 'ok',
    tunnelLabel: localOnly ? 'Local Only' : (tunnelBackend === 'cloudflare' ? 'Cloudflare' : 'Ngrok'),
    tunnel: tunnelActive ? (localOnly ? 'gray' : 'ok') : 'warn',
    twilio: diagnostics.twilio_ready || (diagnostics.twilio || {}).ok ? 'ok' : 'warn',
    mediaStream: streamReady ? 'ok' : 'warn',
    stt: diagnostics.stt_ready || (diagnostics.stt || {}).ok ? 'ok' : 'warn',
    tts: diagnostics.tts_ready || (diagnostics.tts || {}).ok ? 'ok' : 'warn',
    ai: diagnostics.ai_ready || sttBackend === 'simulated' ? 'ok' : 'warn',
  };
}

function renderPrepConfig() {
  const p = AppState.prep;
  $('prep-target').value = p.target;
  $('prep-caller-id').value = p.callerId;
  $('prep-profile').value = p.profile;
  $('prep-record').checked = p.record;
  $('prep-transcript').checked = p.transcript;
  $('prep-injection-mode').value = p.injectionMode;
  $('prep-silence-timeout').value = p.silenceTimeout;
  $('prep-retry-limit').value = p.retryLimit;
}

function updatePrepState() {
  AppState.prep.target = $('prep-target').value;
  AppState.prep.callerId = $('prep-caller-id').value;
  AppState.prep.profile = $('prep-profile').value;
  AppState.prep.record = $('prep-record').checked;
  AppState.prep.transcript = $('prep-transcript').checked;
  AppState.prep.injectionMode = $('prep-injection-mode').value;
  AppState.prep.silenceTimeout = parseInt($('prep-silence-timeout').value);
  AppState.prep.retryLimit = parseInt($('prep-retry-limit').value);
  
  // Sync header target if changed
  if (AppState.prep.target) {
    $('f-target').value = AppState.prep.target;
  } else {
    AppState.prep.target = normalizeTarget($('f-target').value);
  }
}

function renderPrepChecklist() {
  const root = $('prep-checklist');
  if (!root) return;

  const readiness = getPrepReadiness();
  const items = [
    { label: 'Twilio Connected', status: readiness.twilio },
    { label: 'Media Stream Active', status: readiness.mediaStream },
    { label: 'Recording Webhook', status: 'ok' },
    { label: 'STT Ready', status: readiness.stt },
    { label: 'TTS Ready', status: readiness.tts },
    { label: 'DTMF Injection', status: 'ok' },
    { label: 'AI Model Loaded', status: readiness.ai },
    { label: 'Call Logging Active', status: 'ok' },
    { label: 'Template Library', status: AppState.savedMaps.length ? 'ok' : 'gray' },
    { label: 'Suite Engine Ready', status: 'ok' },
    { label: 'Conf Bridge Ready', status: 'ok' },
    { label: 'Tunnel Reachable', status: readiness.tunnel }
  ];

  root.innerHTML = items.map(item => `
    <div class="checklist-item">
      <div class="checklist-indicator tone-${item.status}" style="background-color: var(--${item.status === 'ok' ? 'success' : (item.status === 'error' ? 'danger' : (item.status === 'warn' ? 'warn' : 'text-4'))});"></div>
      <div class="checklist-label">${item.label}</div>
    </div>
  `).join('');
}

function renderPrepTriggers() {
  const root = $('prep-triggers-list');
  if (!root) return;

  root.innerHTML = AppState.prep.triggers.map((t, i) => `
    <div class="trigger-phrase-row">
      <input type="text" value="${escapeHtml(t.phrase)}" placeholder="Trigger Phrase" onchange="updateTrigger(${i}, 'phrase', this.value)">
      <input type="text" value="${escapeHtml(t.response)}" placeholder="Response" onchange="updateTrigger(${i}, 'response', this.value)">
      <select onchange="updateTrigger(${i}, 'type', this.value)">
        <option value="auto">Auto-detect</option>
        <option value="dtmf" ${detectInputType(t.response) === 'dtmf' ? 'selected' : ''}>DTMF</option>
        <option value="speech" ${detectInputType(t.response) === 'speech' ? 'selected' : ''}>Speech</option>
      </select>
      <button class="btn-ghost-xs" onclick="removeTrigger(${i})">✕</button>
    </div>
  `).join('');
}

window.updateTrigger = (index, field, value) => {
  AppState.prep.triggers[index][field] = value;
};

window.removeTrigger = (index) => {
  AppState.prep.triggers.splice(index, 1);
  renderPrepTriggers();
};

window.addTrigger = () => {
  AppState.prep.triggers.push({ phrase: '', response: '' });
  renderPrepTriggers();
};

function renderPrepReadyResponses() {
  const root = $('prep-ready-responses-list');
  if (!root) return;

  const responses = [
    'Representative', 'Billing', 'Technical Support', 'Yes', 'No', 
    'Repeat', 'Main Menu', 'Account Number', 'Press 0', 'ZIP Code'
  ];

  root.innerHTML = responses.map(r => `
    <button class="ready-chip">${escapeHtml(r)}</button>
  `).join('');
}

function renderDiscoverWorkspace() {
  const d = AppState.discover;
  if (!d.activeSessionId) {
    // Generate mock session for Slice 5 demo
    d.activeSessionId = 'discovery-' + Math.floor(Math.random() * 10000);
    d.targetIvr = $('f-target').value || '+18005550114';
    d.stats = {
      statesFound: 24,
      unknownStates: 8,
      coverage: 68,
      currentDepth: 3,
      runtime: '04:12',
      confidence: 85
    };
    d.explorationQueue = [
      { path: 'Main → 2 → 1', reason: 'Unexplored branch', confidence: 92, risk: 'Low' },
      { path: 'Main → 3', reason: 'Unknown prompt', confidence: 45, risk: 'Medium' }
    ];
    d.events = [
      { timestamp: '10:04:12', type: 'discovery', detail: 'New state discovered: Billing Info' },
      { timestamp: '10:04:35', type: 'loop', detail: 'Loop detected: Returns to Main Menu' },
      { timestamp: '10:05:01', type: 'unresolved', detail: 'Unknown prompt detected at depth 3' }
    ];
    d.unknownPrompts = [
      { id: 'p1', transcript: '“Please enter your 16-digit account number...”', confidence: 88, suggestedLabel: 'Account Entry' },
      { id: 'p2', transcript: '“I’m sorry, I didn’t catch that. Could you repeat?”', confidence: 95, suggestedLabel: 'Retry Prompt' }
    ];
  }

  renderDiscoverStatusStrip();
  renderDiscoverMap();
  renderProbeControl();
  renderExplorationQueue();
  renderDiscoveryEvents();
  renderUnknownPrompts();
  renderStateDetails();
}

function applyRunMockData() {
  AppState.run.stats = {
    activeRuns: 2,
    queuedRuns: 5,
    successRate: '94.2%',
    failedRuns: 1,
    escalations: 1,
    avgConfidence: '88%',
    driftAlerts: 1,
    workerAvailability: 'Ready'
  };

  AppState.run.activeRuns = [
    { 
      id: 'r1', 
      suiteName: 'Comcast Billing', 
      state: 'Navigating', 
      activePath: 'Main Menu → Billing → Payments', 
      confidence: '94%', 
      runtime: '02:15',
      drift: null
    },
    { 
      id: 'r2', 
      suiteName: 'Insurance Claim', 
      state: 'Verifying', 
      activePath: 'Main Menu → Claims → Policy # → Verification', 
      confidence: '68%', 
      runtime: '04:30',
      drift: 'Verification prompt wording changed'
    }
  ];
}

applyRunMockData();

function renderDiscoverStatusStrip() {
  const root = $('discovery-status-strip');
  if (!root) return;
  const s = AppState.discover.stats;
  const items = [
    { label: 'Session', value: AppState.discover.activeSessionId },
    { label: 'Target', value: AppState.discover.targetIvr },
    { label: 'States Found', value: s.statesFound },
    { label: 'Unknown', value: s.unknownStates, tone: 'warn' },
    { label: 'Coverage', value: s.coverage + '%' },
    { label: 'Depth', value: s.currentDepth },
    { label: 'Mode', value: AppState.discover.probeMode, tone: 'accent' },
    { label: 'Runtime', value: s.runtime },
    { label: 'Confidence', value: s.confidence + '%' }
  ];

  root.innerHTML = items.map(item => `
    <div class="discovery-stat">
      <div class="discovery-stat-label">${item.label}</div>
      <div class="discovery-stat-value ${item.tone ? 'tone-' + item.tone : ''}">${item.value}</div>
    </div>
  `).join('');
}

function renderDiscoverMap() {
  const root = $('discover-map-surface');
  if (!root) return;
  root.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🗺️</div>
      <p>Discovery Graph Intelligence</p>
      <span>65% Hero Map Area — Visualizing discovered states, loops, and unexplored branches.</span>
    </div>
  `;
}

function renderProbeControl() {
  const root = $('probe-control-panel');
  if (!root) return;
  const modes = ['Conservative', 'Balanced', 'Aggressive', 'Exhaustive'];
  root.innerHTML = `
    <div class="probe-mode-selector">
      ${modes.map(m => `
        <button class="probe-mode-btn ${AppState.discover.probeMode === m ? 'is-active' : ''}" onclick="setProbeMode('${m}')">
          ${m}
        </button>
      `).join('')}
    </div>
    <div style="padding: 0 12px 12px;">
      <div class="config-field">
        <label>Max Depth</label>
        <input type="number" value="5" readonly>
      </div>
      <div class="config-field">
        <label>Branch Timeout (ms)</label>
        <input type="number" value="10000" readonly>
      </div>
    </div>
  `;
}

function setProbeMode(mode) {
  AppState.discover.probeMode = mode;
  renderProbeControl();
  renderDiscoverStatusStrip();
}

function renderExplorationQueue() {
  const root = $('exploration-queue');
  if (!root) return;
  root.innerHTML = AppState.discover.explorationQueue.map(item => `
    <div class="queue-item">
      <div class="queue-item-header">
        <span class="queue-item-path">${escapeHtml(item.path)}</span>
        <span class="queue-item-confidence">${item.confidence}% Conf</span>
      </div>
      <div class="discovery-stat-label">${item.reason} — Risk: ${item.risk}</div>
    </div>
  `).join('');
}

function renderDiscoveryEvents() {
  const root = $('discovery-events');
  if (!root) return;
  root.innerHTML = AppState.discover.events.map(e => `
    <div class="event-item">
      <span class="event-timestamp">${e.timestamp}</span>
      <span class="event-detail">${escapeHtml(e.detail)}</span>
    </div>
  `).join('');
}

function renderUnknownPrompts() {
  const root = $('unknown-prompts');
  if (!root) return;
  const prompts = AppState.discover.unknownPrompts || [];
  if (!prompts.length) {
    root.innerHTML = '<div class="empty-state-sm">No discovered prompts yet</div>';
    return;
  }
  root.innerHTML = prompts.map((p, i) => `
    <div class="discovered-prompt-row" data-prompt-index="${i}">
      <div class="discovered-prompt-text">"${escapeHtml(p.transcript)}"</div>
      <div class="discovered-prompt-meta">Discovered · ${p.state_id || 'Unknown state'}</div>
      <div class="discovered-prompt-response">
        <input type="text" placeholder="Enter response for this prompt…" value="${escapeHtml(p.response || '')}" data-prompt-response="${i}">
        <button class="discovered-response-save" data-prompt-save="${i}">Save</button>
      </div>
    </div>
  `).join('');

  // Wire save buttons
  root.querySelectorAll('[data-prompt-save]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.promptSave);
      const input = root.querySelector(`[data-prompt-response="${idx}"]`);
      if (input && AppState.discover.unknownPrompts[idx]) {
        AppState.discover.unknownPrompts[idx].response = input.value;
        saveDiscoveredToLibrary([AppState.discover.unknownPrompts[idx]]);
        btn.textContent = 'Saved ✓';
        setTimeout(() => btn.textContent = 'Save', 1500);
      }
    });
  });
}

// Persist discovered prompts to in-memory library (survives tab switches, not page refresh)
const _promptLibrary = { discovered: [], manual: [] };

function saveDiscoveredToLibrary(prompts) {
  prompts.forEach(p => {
    const exists = _promptLibrary.discovered.find(e => e.transcript === p.transcript);
    if (exists) { exists.response = p.response; }
    else { _promptLibrary.discovered.push({ ...p }); }
  });
  renderPromptLibrary();
}

function renderPromptLibrary() {
  ['discovered','manual'].forEach(tab => {
    const el = $(`lib-${tab}`);
    if (!el) return;
    const entries = _promptLibrary[tab];
    if (!entries.length) {
      el.innerHTML = `<div class="library-empty">${tab === 'discovered' ? 'No discovered prompts yet — run IVR Discovery first.' : 'No pre-set prompts yet — add one above.'}</div>`;
      return;
    }
    el.innerHTML = entries.map(e => `
      <div class="library-entry">
        <div class="library-prompt-text">"${escapeHtml(e.transcript || e.prompt || '')}"</div>
        <div class="library-response-text">${escapeHtml(e.response || '—')}</div>
        <span class="library-entry-tag ${tab}">${tab === 'manual' ? 'Manual' : 'Discovered'}</span>
      </div>
    `).join('');
  });
}

function renderStateDetails() {
  const root = $('state-details');
  if (!root) return;
  if (!AppState.discover.selectedStateId) {
    root.innerHTML = '<div class="empty-state">Select a node to view state details</div>';
    return;
  }
}

function initDiscoverEvents() {
  $('btn-discover-refresh-map').addEventListener('click', () => {
    console.log('[discover] Refreshing discovery map...');
  });
}

function renderReviewWorkspace() {
  renderReviewHeader();
  renderReviewTimelineHero();
  renderReviewTranscript();
  renderReviewTemplateBuilder();
}

function renderReviewHeader() {
  const root = $('review-header');
  if (!root) return;

  const calls = [
    { id: 'call-101', date: '2024-05-13 09:12', target: '+18005550199', duration: '02:45', outcome: 'Success', states: 12, unknown: 1, template: 'None', recording: true, transcript: true },
    { id: 'call-100', date: '2024-05-13 08:45', target: '+18005550114', duration: '01:20', outcome: 'Failed', states: 4, unknown: 2, template: 'Draft', recording: true, transcript: true }
  ];

  const selected = calls[0]; // Mock selection

  root.innerHTML = `
    <div class="review-header-strip">
      <div class="review-call-selector">
        <label>Historical Evidence</label>
        <select id="review-call-select">
          ${calls.map(c => `<option value="${c.id}">${c.date} — ${c.target}</option>`).join('')}
        </select>
      </div>
      <div class="review-header-stats">
        <div class="header-stat">
          <span class="stat-label">Duration</span>
          <span class="stat-value">${selected.duration}</span>
        </div>
        <div class="header-stat">
          <span class="stat-label">Outcome</span>
          <span class="stat-value tone-ok">${selected.outcome}</span>
        </div>
        <div class="header-stat">
          <span class="stat-label">States</span>
          <span class="stat-value">${selected.states}</span>
        </div>
        <div class="header-stat">
          <span class="stat-label">Unknown</span>
          <span class="stat-value tone-warn">${selected.unknown}</span>
        </div>
        <div class="header-stat">
          <span class="stat-label">Template</span>
          <span class="stat-value">${selected.template}</span>
        </div>
        <div class="header-stat">
          <span class="stat-label">Evidence</span>
          <div class="stat-row">
            <span class="badge ${selected.recording ? 'tone-ok' : ''}">WAV</span>
            <span class="badge ${selected.transcript ? 'tone-ok' : ''}">TXT</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderReviewTimelineHero() {
  const root = $('review-timeline-hero');
  if (!root) return;

  // Mock timeline markers
  const markers = [
    { t: 0, type: 'start', label: 'Call Started' },
    { t: 5, type: 'prompt', label: 'Welcome to IVR' },
    { t: 12, type: 'dtmf', label: '1' },
    { t: 15, type: 'prompt', label: 'Billing Dept' },
    { t: 25, type: 'speech', label: 'Representative' },
    { t: 30, type: 'transition', label: 'Transfer detected', tone: 'warn' },
    { t: 45, type: 'end', label: 'Disconnected' }
  ];

  root.innerHTML = `
    <div class="timeline-viz">
      <div class="timeline-axis">
        ${[0, 10, 20, 30, 40, 50, 60].map(s => `<div class="axis-tick">0:${s.toString().padStart(2, '0')}</div>`).join('')}
      </div>
      <div class="timeline-track">
        ${markers.map(m => `
          <div class="timeline-marker ${m.type} ${m.tone || ''}" style="left: ${(m.t / 60) * 100}%" title="${m.label}">
            <div class="marker-pin"></div>
            <div class="marker-label">${m.label}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function renderReviewTranscript() {
  const root = $('review-transcript-list');
  if (!root) return;

  const items = [
    { time: '0:05', speaker: 'IVR', text: 'Welcome to global logistics. Please press 1 for billing or say representative.', confidence: 0.98, state: 'Main Menu' },
    { time: '0:12', speaker: 'User', text: '[DTMF 1]', confidence: 1.0, state: 'Action' },
    { time: '0:15', speaker: 'IVR', text: 'You have reached billing. To continue, say representative or enter your account number.', confidence: 0.94, state: 'Billing Menu' },
    { time: '0:25', speaker: 'User', text: 'representative', confidence: 0.88, state: 'Action' },
    { time: '0:30', speaker: 'System', text: '[Transfer Detected]', confidence: 1.0, state: 'Transfer', tone: 'warn' }
  ];

  root.innerHTML = items.map(item => `
    <div class="transcript-review-row ${item.tone || ''}">
      <div class="review-row-meta">
        <span class="review-time">${item.time}</span>
        <span class="review-speaker">${item.speaker}</span>
      </div>
      <div class="review-row-content">
        <div class="review-text" contenteditable="true">${escapeHtml(item.text)}</div>
        <div class="review-row-actions">
          <div class="review-state-label">${item.state}</div>
          <div class="review-confidence ${item.confidence < 0.9 ? 'tone-warn' : ''}">${Math.round(item.confidence * 100)}%</div>
          <button class="btn-ghost-xs">Note</button>
          <button class="btn-ghost-xs tone-ok">Verify</button>
        </div>
      </div>
    </div>
  `).join('');
}

function renderReviewTemplateBuilder() {
  const root = $('review-template-builder');
  if (!root) return;

  root.innerHTML = `
    <div class="template-builder-shell">
      <div class="config-group">
        <div class="config-field">
          <label>Template Name</label>
          <input type="text" placeholder="e.g., Billing Inquiry Flow">
        </div>
        <div class="config-field-row">
          <div class="config-field grow-1">
            <label>Provider</label>
            <input type="text" placeholder="Global Logistics">
          </div>
          <div class="config-field grow-1">
            <label>Intent</label>
            <input type="text" placeholder="Check balance">
          </div>
        </div>
      </div>

      <div class="template-section">
        <div class="section-title">Sequence Extraction</div>
        <div class="template-sequence">
          <div class="sequence-item">
            <span class="seq-num">1</span>
            <span class="seq-label">Main Menu</span>
            <span class="seq-arrow">→</span>
            <span class="seq-action">DTMF 1</span>
          </div>
          <div class="sequence-item">
            <span class="seq-num">2</span>
            <span class="seq-label">Billing Menu</span>
            <span class="seq-arrow">→</span>
            <span class="seq-action">Speech "Representative"</span>
          </div>
          <button class="btn-ghost-sm btn-full-sm">+ Add Sequence Step</button>
        </div>
      </div>

      <div class="template-section">
        <div class="section-title">Required Inputs</div>
        <div class="template-inputs">
          <div class="input-chip">account_number</div>
          <div class="input-chip">zip_code</div>
          <button class="btn-ghost-xs">+</button>
        </div>
      </div>
    </div>
  `;
}

function initPrepEvents() {
  const inputs = [
    'prep-target', 'prep-caller-id', 'prep-profile', 
    'prep-record', 'prep-transcript', 'prep-injection-mode', 
    'prep-silence-timeout', 'prep-retry-limit'
  ];
  
  inputs.forEach(id => {
    const el = $(id);
    if (el) {
      el.addEventListener('change', updatePrepState);
    }
  });

  $('btn-add-trigger').addEventListener('click', addTrigger);
  $('prep-btn-validate').addEventListener('click', () => {
    addLog('[system] Validating mission setup...');
    fetchDiagnose(true);
  });
  $('prep-btn-dry-run').addEventListener('click', () => {
    addLog('[system] Initiating dry run (no call)...');
  });
  $('prep-btn-discovery').addEventListener('click', () => {
    addLog('[system] Starting discovery mission...');
    startCall();
  });
  $('prep-btn-start').addEventListener('click', () => {
    addLog('[system] Starting live call mission...');
    startCall();
  });
}

function renderOperatorConsole() {
  if ($('hdr-status')) {
    $('hdr-status').textContent = AppState.callRunning ? 'Live Session' : 'Idle';
    $('hdr-status').className = 'status-pill ' + (AppState.callRunning ? 'tone-accent' : 'tone-warn');
  }
  renderHeaderStatus();
  renderStatusCard();
  renderTimeline();
  renderGraph();
  renderRecentEvents();
  renderUnresolvedStates();
  renderDrawer();

  // Workspace-specific rendering
  if (AppState.currentWorkspace === 'prep') {
    renderPrepWorkspace();
  } else if (AppState.currentWorkspace === 'review') {
    renderReviewWorkspace();
  }

  // Initialize controls if they don't exist
  if (!$('smart-input')) {
    renderInjectionBar();
    renderReadyResponses();
    renderPromptMarkers();
  }
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
  if (AppState.mode === 'replay') return;
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
    if (error.status === 401 || error.status === 403) {
        addLog('[error] Authentication failed. Please refresh.');
    } else if (error.message.includes('Failed to fetch')) {
        // Silent connection loss handling
    }
  }
}

async function fetchRuntimeMetrics() {
  if (AppState.mode === 'replay') return;
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
  if (AppState.mode === 'replay') return;
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

function setCallActiveUI(active, target) {
  const idle = $('call-idle-screen');
  const activeScreen = $('call-active-screen');
  if (idle) idle.classList.toggle('is-hidden', active);
  if (activeScreen) activeScreen.classList.toggle('is-hidden', !active);
  const ws = $('ws-live');
  if (ws) ws.classList.toggle('is-call-active', active);
  const numEl = $('live-active-number');
  if (numEl && target) numEl.textContent = target;
  const liveNavBtn = document.querySelector('.shell-nav-live');
  if (liveNavBtn) liveNavBtn.classList.toggle('is-on-call', active);
}

async function startCall() {
  const targetInput = document.querySelector('#call-number-display, #f-target');
  let target = normalizeTarget(targetInput ? targetInput.value : '');
  if (!target) {
    addLog('[error] Please enter a target phone number');
    return;
  }

  setCallActiveUI(true, target);
  addLog('[system] Starting call to ' + target + '...');

  const btn = $('btn-live-call');
  if (btn) { btn.disabled = true; btn.textContent = 'Calling…'; }

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
      if (btn) { btn.disabled = false; btn.textContent = 'Live'; }
    }, 1800);
  }
}

async function endCall() {
  const btn = $('btn-hangup-call');
  const originalText = btn ? btn.textContent : '';
  try {
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Hanging Up…';
    }
    await api.endCall();
    addLog('[system] End-session requested');
    setCallActiveUI(false);
    fetchStatus();
    fetchRuntimeMetrics();
    fetchRuntimeDiagnostics();
  } catch (error) {
    addLog('[error] Failed to end session: ' + error.message);
  } finally {
    if (btn) {
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = 'Hang Up';
      }, 1200);
    }
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
  const formatted = formatTimer(Math.max(0, Math.floor((elapsedMs || 0) / 1000)));
  const timerEl = $('hdr-call-timer') || $('timer');
  if (timerEl) timerEl.textContent = formatted;
  const activeTimer = $('live-active-timer');
  if (activeTimer) activeTimer.textContent = formatted;
}

async function setConferenceMode(mode) {
  try {
    const data = await api.setConferenceMode(mode);
    if (data.status === 'ok') {
      fetchStatus();
    }
  } catch (error) {
    addLog('[error] Failed to set monitor mode: ' + error.message);
  }
}

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    setConferenceMode(mode);
  });
});

function switchWorkspace(workspaceId) {
  AppState.currentWorkspace = workspaceId;

  // Update navigation buttons (including the live call circle button)
  document.querySelectorAll('.shell-nav-btn, .shell-nav-live').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.workspace === workspaceId);
  });

  // Update workspace containers
  document.querySelectorAll('.workspace').forEach(ws => {
    ws.classList.toggle('is-hidden', ws.id !== 'ws-' + workspaceId);
  });

  if (workspaceId === 'prep') {
    renderPrepWorkspace();
  } else if (workspaceId === 'review') {
    renderReviewWorkspace();
  } else if (workspaceId === 'discover') {
    renderDiscoverWorkspace();
  } else if (workspaceId === 'run') {
    renderRunWorkspace();
  }

  EventBus.emit('WORKSPACE_CHANGED', { workspaceId });
  console.log('[system] Switched to workspace:', workspaceId);
  renderOperatorConsole();
}

function renderRunWorkspace() {
  renderAutomationHealthStrip();
  renderSuiteLibrary();
  renderActiveRuns();
  renderRunIntelligence();
}

function renderAutomationHealthStrip() {
  const root = $('automation-health-strip');
  if (!root) return;
  const s = AppState.run.stats;
  const items = [
    { label: 'Active', value: s.activeRuns, tone: s.activeRuns > 0 ? 'accent' : 'neutral' },
    { label: 'Queued', value: s.queuedRuns, tone: 'neutral' },
    { label: 'Success', value: s.successRate, tone: 'ok' },
    { label: 'Failed', value: s.failedRuns, tone: s.failedRuns > 0 ? 'error' : 'neutral' },
    { label: 'Escalations', value: s.escalations, tone: s.escalations > 0 ? 'error' : 'neutral' },
    { label: 'Confidence', value: s.avgConfidence, tone: 'accent' },
    { label: 'Drift', value: s.driftAlerts, tone: s.driftAlerts > 0 ? 'warn' : 'neutral' },
    { label: 'Workers', value: s.workerAvailability, tone: 'ok' }
  ];

  root.innerHTML = items.map(item => `
    <div class="run-stat">
      <div class="run-stat-label">${item.label}</div>
      <div class="run-stat-value" style="color: var(--${item.tone === 'ok' ? 'success' : (item.tone === 'error' ? 'danger' : (item.tone === 'warn' ? 'warn' : (item.tone === 'accent' ? 'accent' : 'text-1')))});">${item.value}</div>
    </div>
  `).join('');
}

function renderSuiteLibrary() {
  const root = $('suite-library-list');
  if (!root) return;
  if (!AppState.run.suiteLibrary || AppState.run.suiteLibrary.length === 0) {
    root.innerHTML = '<div class="p-4 text-muted-sm-centered">No suites in library.</div>';
    return;
  }
  root.innerHTML = AppState.run.suiteLibrary.map(s => `
    <div class="suite-card">
      <div class="suite-card-header">
        <div>
          <div class="suite-name">${escapeHtml(s.name)}</div>
          <div class="suite-meta">${escapeHtml(s.provider)} • ${escapeHtml(s.intent)}</div>
        </div>
        <div class="badge-run ${s.driftStatus === 'Stable' ? 'status-active' : 'status-drift'}">${s.driftStatus}</div>
      </div>
      <div class="suite-stats">
        <div class="discovery-stat">
          <div class="discovery-stat-label">Success</div>
          <div class="discovery-stat-value">${s.successRate}</div>
        </div>
        <div class="discovery-stat">
          <div class="discovery-stat-label">Last Run</div>
          <div class="discovery-stat-value" style="font-size: 11px;">${s.lastRun}</div>
        </div>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 8px;">
        <button class="btn-primary btn-compact" style="flex: 1;">Run</button>
        <button class="btn-secondary btn-compact">View</button>
      </div>
    </div>
  `).join('');
}

function renderActiveRuns() {
  const root = $('active-runs-list');
  if (!root) return;
  if (AppState.run.activeRuns.length === 0) {
    root.innerHTML = `<div class="empty-state">No active autonomous runs</div>`;
    return;
  }
  root.innerHTML = AppState.run.activeRuns.map(r => `
    <div class="active-run-card ${AppState.run.selectedRunId === r.id ? 'is-selected' : ''}" onclick="selectRun('${r.id}')">
      <div class="run-state-row">
        <div class="suite-name">${escapeHtml(r.suiteName)}</div>
        <div class="badge-run status-active">${r.state}</div>
      </div>
      <div class="run-path-preview">${escapeHtml(r.activePath)}</div>
      <div class="suite-stats">
        <div class="discovery-stat">
          <div class="discovery-stat-label">Confidence</div>
          <div class="discovery-stat-value">${r.confidence}</div>
        </div>
        <div class="discovery-stat">
          <div class="discovery-stat-label">Runtime</div>
          <div class="discovery-stat-value">${r.runtime}</div>
        </div>
      </div>
      ${r.drift ? `
        <div class="drift-alert">
          <span>⚠️</span>
          <div>Potential drift detected: ${escapeHtml(r.drift)}</div>
        </div>
      ` : ''}
    </div>
  `).join('');
}

function renderRunIntelligence() {
  const root = $('run-intelligence-content');
  if (!root) return;
  const intel = AppState.run.intelligence;
  root.innerHTML = `
    <div class="intelligence-item">
      <div class="intelligence-label">Current Decision</div>
      <div class="intelligence-value">${escapeHtml(intel.currentDecision)}</div>
    </div>
    <div class="intelligence-item">
      <div class="intelligence-label">Detected Prompt</div>
      <div class="intelligence-value">${escapeHtml(intel.detectedPrompt)}</div>
    </div>
    <div class="intelligence-item">
      <div class="intelligence-label">Selected Response</div>
      <div class="intelligence-value">${escapeHtml(intel.selectedResponse)}</div>
    </div>
    <div class="intelligence-item">
      <div class="intelligence-label">Confidence</div>
      <div class="intelligence-value" style="font-size: 18px; font-weight: 600; color: var(--accent);">${intel.confidence}</div>
    </div>
    <div class="intelligence-item">
      <div class="intelligence-label">Fallback Plan</div>
      <div class="intelligence-value">${escapeHtml(intel.fallbackPlan)}</div>
    </div>
    <div class="intelligence-item">
      <div class="intelligence-label">Outcome Predictions</div>
      <div class="predictions-list">
        ${(intel.predictions || []).map(p => `
          <div class="prediction-item">
            <span>${escapeHtml(p.outcome)}</span>
            <span class="prediction-conf">${p.confidence}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

window.selectRun = (id) => {
  AppState.run.selectedRunId = id;
  // Mock intelligence update
  const run = AppState.run.activeRuns.find(r => r.id === id);
  if (run) {
    AppState.run.intelligence = {
      currentDecision: 'Navigating to ' + run.activePath.split('→').pop().trim(),
      detectedPrompt: 'Please hold while I connect your call...',
      selectedResponse: 'Silence (Wait)',
      confidence: run.confidence,
      fallbackPlan: 'Retry DTMF 0 after 5s',
      predictions: [
        { outcome: 'Successful Navigation', confidence: '92%' },
        { outcome: 'Transfer to Agent', confidence: '5%' },
        { outcome: 'Disconnect', confidence: '3%' }
      ]
    };
  }
  renderRunWorkspace();
};

document.querySelectorAll('.shell-nav-btn[data-workspace], .shell-nav-live[data-workspace]').forEach(btn => {
  btn.addEventListener('click', () => {
    switchWorkspace(btn.dataset.workspace);
  });
});

$('btn-interactive-call').addEventListener('click', () => switchWorkspace('live'));
$('btn-live-call').addEventListener('click', startCall);
$('btn-hangup-call').addEventListener('click', endCall);
$('btn-refresh-maps').addEventListener('click', fetchMaps);
// Guard optional elements that may be absent in trimmed layout
['btn-settings','btn-open-runtime','btn-open-artifacts','btn-open-smoke','btn-refresh-diagnostics','drawer-toggle'].forEach(id => {
  const el = document.getElementById(id);
  if (!el) return;
  if (id === 'btn-settings' || id === 'btn-open-runtime') el.addEventListener('click', () => openDrawer('runtime'));
  else if (id === 'btn-open-artifacts') el.addEventListener('click', () => openDrawer('artifacts'));
  else if (id === 'btn-open-smoke') el.addEventListener('click', () => openDrawer('smoke'));
  else if (id === 'btn-refresh-diagnostics') el.addEventListener('click', () => { fetchRuntimeMetrics(); fetchRuntimeDiagnostics(); fetchDiagnose(true); });
  else if (id === 'drawer-toggle') el.addEventListener('click', () => { AppState.drawerOpen = !AppState.drawerOpen; renderOperatorConsole(); });
});
// Guard optional legacy elements
['mode-toggle'].forEach(id => { const el = document.getElementById(id); if (el) el.addEventListener('click', toggleMode); });
const smartInputEl = document.getElementById('smart-input');
if (smartInputEl) {
  smartInputEl.addEventListener('input', updateInputChip);
  smartInputEl.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendInput(); }
  });
}
const sendBtnEl = document.querySelector('.send-btn');
if (sendBtnEl) sendBtnEl.addEventListener('click', sendInput);

// New DTMF pad (data-digit buttons)
document.querySelectorAll('[data-digit]').forEach((button) => {
  button.addEventListener('click', () => {
    const digit = button.dataset.digit;
    padBuffer += digit;
    const disp = $('pad-display');
    if (disp) disp.textContent = padBuffer;
  });
});

const dtmfDelBtn = document.getElementById('dtmf-del') || document.querySelector('.pad-del');
if (dtmfDelBtn) dtmfDelBtn.addEventListener('click', () => {
  padBuffer = padBuffer.slice(0, -1);
  const disp = $('pad-display');
  if (disp) disp.textContent = padBuffer || '—';
});

const dtmfSendBtn = document.getElementById('dtmf-send') || document.querySelector('.pad-send');
if (dtmfSendBtn) dtmfSendBtn.addEventListener('click', async () => {
  if (!padBuffer) return;
  try {
    await api.injectDtmf(padBuffer);
    addLog('[DTMF] You: ' + padBuffer);
    padBuffer = '';
    const disp = $('pad-display');
    if (disp) disp.textContent = '—';
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

$('btn-run-validation-test').addEventListener('click', runValidationTest);
$('btn-abort-validation-test').addEventListener('click', abortValidationTest);

applyModeUI();
updateInputChip();
initPrepEvents();
initDiscoverEvents();

// Operational Telemetry Bridge
const telemetryUrl = `ws://${window.location.hostname}:8081/ws/events`;
const telemetry = new WsManager(telemetryUrl);
telemetry.connect();

// Telemetry Debug Surface
const telemetryLog = [];
EventBus.onAny((event) => {
  telemetryLog.unshift({
    ts: Date.now(),
    type: event.type,
    payload: JSON.stringify(event.payload).substring(0, 100)
  });
  if (telemetryLog.length > 20) telemetryLog.pop();
  renderTelemetryMonitor();
});

function renderTelemetryMonitor() {
  const container = $('telemetry-monitor');
  if (!container) return;
  container.innerHTML = telemetryLog.map(log => `
    <div class="telemetry-log-item">
      <span class="telemetry-ts">${new Date(log.ts).toLocaleTimeString()}</span>
      <span class="telemetry-type">${log.type}</span>
      <span class="telemetry-payload">${escapeHtml(log.payload)}</span>
    </div>
  `).join('');
}

renderOperatorConsole();

// ── Dial main button (idle screen) ───────────────────────────────────────
const dialMainBtn = $('btn-dial-main');
if (dialMainBtn) dialMainBtn.addEventListener('click', startCall);

// ── Mic toggle ───────────────────────────────────────────────────────────
const micBtn = $('btn-mic-toggle');
let micMuted = false;
if (micBtn) micBtn.addEventListener('click', () => {
  micMuted = !micMuted;
  micBtn.classList.toggle('is-muted', micMuted);
  micBtn.setAttribute('aria-pressed', String(!micMuted));
  micBtn.title = micMuted ? 'Unmute microphone' : 'Mute microphone';
  addLog(micMuted ? '[mic] Muted' : '[mic] Unmuted');
});

// ── Prompt library tabs ───────────────────────────────────────────────────
document.querySelectorAll('.review-library-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.review-library-tab').forEach(t => t.classList.remove('is-active'));
    document.querySelectorAll('.library-tab-content').forEach(c => c.classList.remove('is-active'));
    tab.classList.add('is-active');
    const content = document.getElementById(`lib-${tab.dataset.libTab}`);
    if (content) content.classList.add('is-active');
  });
});

// "Save All to Library" button on discover panel
const saveAllBtn = $('btn-save-discovered');
if (saveAllBtn) saveAllBtn.addEventListener('click', () => {
  const prompts = AppState.discover.unknownPrompts || [];
  if (prompts.length) { saveDiscoveredToLibrary(prompts); saveAllBtn.textContent = 'Saved ✓'; setTimeout(() => saveAllBtn.textContent = 'Save All to Library', 2000); }
});

// Manual entry button in review
const addManualBtn = $('btn-library-add-manual');
if (addManualBtn) addManualBtn.addEventListener('click', () => {
  const prompt = window.prompt('Enter IVR prompt text:');
  if (!prompt) return;
  const response = window.prompt('Enter response for this prompt:');
  _promptLibrary.manual.push({ prompt, response: response || '' });
  renderPromptLibrary();
});

// ── Dropdowns ─────────────────────────────────────────────────────────────
['btn-notifications:notif-dropdown', 'btn-settings:settings-dropdown'].forEach(pair => {
  const [btnId, dropId] = pair.split(':');
  const btn = $(btnId), drop = $(dropId);
  if (!btn || !drop) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    drop.classList.toggle('is-open');
  });
});
document.addEventListener('click', () => {
  document.querySelectorAll('.hdr-dropdown.is-open').forEach(d => d.classList.remove('is-open'));
});

api.getConfig().then((cfg) => {
  if (cfg && cfg.target) {
    const target = cfg.target.replace(/^\+1/, '');
    $('f-target').value = target;
    AppState.prep.target = normalizeTarget(target);
  }
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
