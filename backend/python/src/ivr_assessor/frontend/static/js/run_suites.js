// Requires: common/time.js, common/dom.js, common/api.js, common/events.js, common/state.js

(function() {
  let _suites = [];
  let _activeSuiteId = null;
  let _activeScenarioIdx = 0;
  let _stepStatuses = {};
  let _pollInterval = null;
  let _selectedStepId = null;

  const STATUS_ICONS = {
    pending: '○', running: '▶', passed: '✓', failed: '✗',
    timed_out: '⏱', retrying: '↺', skipped: '⏭', errored: '!',
  };

  function rsOpen() {
    $('rs-modal').style.display = 'flex';
    loadRunSuites();
  }

  function rsClose() {
    $('rs-modal').style.display = 'none';
    stopPoll();
  }

  // ── Suite list ─────────────────────────────────────────────────────────────

  async function loadRunSuites() {
    try {
      const d = await api.listRunSuites();
      _suites = d.suites || [];
      renderSuiteList();
    } catch(e) {
      console.error('loadRunSuites:', e);
    }
  }

  function renderSuiteList() {
    const el = $('rs-suite-list');
    if (!_suites.length) {
      el.innerHTML = '<div class="text-muted-xs-padded">No run suites saved</div>';
      return;
    }
    el.innerHTML = _suites.map(s =>
      '<div class="rs-suite-item ' + (_activeSuiteId === s.suite_id ? 'active' : '') + '"' +
      ' onclick="window._rsSelectSuite(\'' + s.suite_id + '\')">' +
        '<div class="rs-suite-item-name">' + s.name + '</div>' +
        '<div class="rs-suite-item-meta">' + s.scenario_count + ' scenario' + (s.scenario_count !== 1 ? 's' : '') + '</div>' +
      '</div>'
    ).join('');
  }

  window._rsSelectSuite = function(suite_id) {
    _activeSuiteId = suite_id;
    _activeScenarioIdx = 0;
    _stepStatuses = {};
    _selectedStepId = null;
    renderSuiteList();
    api.getRunSuite(suite_id)
      .then(data => renderSuiteDetail(data))
      .catch(() => {});
    $('rs-run-btn').disabled = false;
    $('rs-export-btn').disabled = false;
    $('rs-delete-btn').disabled = false;
  };

  function renderSuiteDetail(suite) {
    $('rs-suite-name').textContent = suite.name || suite.suite_id;
    $('rs-suite-desc').textContent = suite.description || '';
    const tabs = $('rs-scenario-tabs');
    const scenarios = suite.scenarios || [];
    tabs.innerHTML = scenarios.map((sc, i) =>
      '<div class="rs-tab ' + (i === _activeScenarioIdx ? 'active' : '') + '"' +
      ' onclick="window._rsSelectScenario(' + i + ')">' + sc.name + '</div>'
    ).join('');
    if (scenarios.length) renderScenarioSteps(scenarios[_activeScenarioIdx]);
    window._rsCurrentSuiteData = suite;
  }

  window._rsSelectScenario = function(idx) {
    _activeScenarioIdx = idx;
    const suite = window._rsCurrentSuiteData;
    if (!suite) return;
    document.querySelectorAll('.rs-tab').forEach((t, i) => t.classList.toggle('active', i === idx));
    renderScenarioSteps(suite.scenarios[idx]);
  };

  function renderScenarioSteps(scenario) {
    const el = $('rs-step-list');
    const steps = scenario.steps || [];
    if (!steps.length) {
      el.innerHTML = '<div class="text-muted-xs-padded">No steps defined</div>';
      return;
    }
    el.innerHTML = steps.map(step => {
      const st = _stepStatuses[step.step_id] || { status: 'pending' };
      const icon = STATUS_ICONS[st.status] || '○';
      const dur = st.duration_ms != null ? formatDuration(st.duration_ms) : '';
      const expected = step.expected_text_contains
        ? 'expects: "' + step.expected_text_contains + '"'
        : step.expected_event ? 'expects: ' + step.expected_event : '';
      return (
        '<div class="rs-step ' + (_selectedStepId === step.step_id ? 'active-step' : '') + '"' +
        ' onclick="window._rsSelectStep(\'' + step.step_id + '\')">' +
          '<div class="rs-step-status ' + st.status + '">' + icon + '</div>' +
          '<div style="flex:1;min-width:0">' +
            '<div class="rs-step-id">' + step.step_id + '</div>' +
            '<div class="rs-step-action">' + step.action + '</div>' +
            (expected ? '<div class="rs-step-expected">' + expected + '</div>' : '') +
            (st.error ? '<div class="rs-step-error">' + st.error + '</div>' : '') +
          '</div>' +
          (dur ? '<div class="rs-step-dur">' + dur + '</div>' : '') +
        '</div>'
      );
    }).join('');
  }

  window._rsSelectStep = function(step_id) {
    _selectedStepId = step_id;
    const st = _stepStatuses[step_id] || { status: 'pending' };
    const suite = window._rsCurrentSuiteData;
    let step = null;
    if (suite) {
      for (const sc of suite.scenarios) {
        step = sc.steps.find(s => s.step_id === step_id);
        if (step) break;
      }
    }
    const detail = $('rs-step-detail');
    const statusClass = st.status === 'passed' ? 'pass' : (st.status === 'failed' || st.status === 'timed_out') ? 'fail' : 'neutral';
    detail.innerHTML =
      row('Step ID',  step_id) +
      row('Action',   step ? step.action : '') +
      row('Status',   st.status, statusClass) +
      (step && step.expected_text_contains ? row('Expected', '"' + step.expected_text_contains + '"') : '') +
      (step && step.expected_event         ? row('Expect evt', step.expected_event) : '') +
      (st.actual != null        ? row('Actual',     st.actual, 'neutral') : '') +
      (st.duration_ms != null   ? row('Duration',   formatDuration(st.duration_ms)) : '') +
      (st.confidence != null    ? row('Confidence', (st.confidence * 100).toFixed(0) + '%') : '') +
      (st.error                 ? row('Error',      st.error, 'fail') : '') +
      (st.secure_card_token     ? row('Token',      st.secure_card_token) : '');

    const suite2 = window._rsCurrentSuiteData;
    if (suite2 && suite2.scenarios[_activeScenarioIdx]) {
      renderScenarioSteps(suite2.scenarios[_activeScenarioIdx]);
    }
  };

  function row(label, value, cls) {
    return '<div class="rs-detail-row">' +
      '<span class="rs-detail-label">' + label + '</span>' +
      '<span class="rs-detail-value' + (cls ? ' ' + cls : '') + '">' + value + '</span>' +
      '</div>';
  }

  // ── Run / poll ─────────────────────────────────────────────────────────────

  async function runSuite() {
    if (!_activeSuiteId || AppState.suiteRunning) return;
    _stepStatuses = {};
    AppState.suiteRunning = true;
    $('rs-run-btn').style.display = 'none';
    $('rs-abort-btn').style.display = 'inline-block';
    $('rs-progress-bar').style.display = 'block';
    $('rs-summary-chips').innerHTML = '';
    $('rs-live-feed').innerHTML = '';
    try {
      await api.runRunSuite(_activeSuiteId);
    } catch(e) {
      addLiveFeedLine('error', 'Failed to start: ' + e.message);
      finishRun();
      return;
    }
    startPoll();
  }

  function startPoll() {
    _pollInterval = setInterval(async () => {
      try {
        const d = await api.pollRunSuite(_activeSuiteId);
        processEvents(d.events || []);
        if (d.result) updateSummaryChips(d.result);
      } catch(_) {}
    }, 400);
  }

  function stopPoll() {
    if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
  }

  function processEvents(events) {
    for (const ev of events) {
      switch (ev.type) {
        case RUN_EVENTS.STEP_STARTED:
          _stepStatuses[ev.step_id] = { status: 'running' };
          addLiveFeedLine('info', '▶ ' + ev.step_id + ' — ' + ev.action);
          break;
        case RUN_EVENTS.STEP_UPDATED:
          _stepStatuses[ev.step_id] = {
            status: ev.status, actual: ev.actual, error: ev.error,
            confidence: ev.confidence, secure_card_token: ev.secure_card_token,
          };
          break;
        case RUN_EVENTS.STEP_PASSED:
          _stepStatuses[ev.step_id] = Object.assign(_stepStatuses[ev.step_id] || {}, {
            status: 'passed', duration_ms: ev.duration_ms, actual: ev.actual, confidence: ev.confidence,
          });
          addLiveFeedLine('pass', '✓ ' + ev.step_id + ' (' + formatDuration(ev.duration_ms) + ')');
          break;
        case RUN_EVENTS.STEP_FAILED:
          _stepStatuses[ev.step_id] = Object.assign(_stepStatuses[ev.step_id] || {}, {
            status: 'failed', duration_ms: ev.duration_ms, error: ev.error, actual: ev.actual,
          });
          addLiveFeedLine('fail', '✗ ' + ev.step_id + ': ' + (ev.error || ev.reason));
          break;
        case RUN_EVENTS.STEP_TIMED_OUT:
          _stepStatuses[ev.step_id] = Object.assign(_stepStatuses[ev.step_id] || {}, {
            status: 'timed_out', error: 'Timed out (' + ev.timeout_ms + 'ms)',
          });
          addLiveFeedLine('fail', '⏱ ' + ev.step_id + ' timed out');
          break;
        case RUN_EVENTS.RUN_SUITE_COMPLETED:
          finishRun();
          addLiveFeedLine(
            ev.status === 'passed' ? 'pass' : 'fail',
            'Suite ' + ev.status.toUpperCase() + ' — pass:' + ev.pass_count + ' fail:' + ev.fail_count
          );
          break;
      }
      const suite = window._rsCurrentSuiteData;
      if (suite && suite.scenarios[_activeScenarioIdx]) {
        renderScenarioSteps(suite.scenarios[_activeScenarioIdx]);
      }
    }
  }

  function updateSummaryChips(result) {
    const total = result.pass_count + result.fail_count + result.timeout_count;
    const pct = total > 0 ? Math.round((result.pass_count / total) * 100) : 0;
    $('rs-progress-fill').style.width = pct + '%';
    $('rs-summary-chips').innerHTML = [
      result.pass_count    ? '<span class="rs-chip pass">✓ ' + result.pass_count + ' passed</span>'     : '',
      result.fail_count    ? '<span class="rs-chip fail">✗ ' + result.fail_count + ' failed</span>'     : '',
      result.timeout_count ? '<span class="rs-chip time">⏱ ' + result.timeout_count + ' timeout</span>' : '',
    ].join('');
  }

  function finishRun() {
    AppState.suiteRunning = false;
    stopPoll();
    $('rs-run-btn').style.display = 'inline-block';
    $('rs-run-btn').disabled = false;
    $('rs-abort-btn').style.display = 'none';
  }

  // ── Import ─────────────────────────────────────────────────────────────────

  $('rs-import-toggle').onclick = () => {
    $('rs-import-area').classList.toggle('visible');
  };

  $('rs-import-btn').onclick = async () => {
    const raw = $('rs-import-ta').value.trim();
    if (!raw) return;
    try {
      const d = await api.importRunSuite(raw);
      if (d && d.status === 'ok') {
        $('rs-import-ta').value = '';
        $('rs-import-area').classList.remove('visible');
        await loadRunSuites();
        window._rsSelectSuite(d.suite_id);
      } else {
        alert('Import error: ' + (d && d.error ? d.error : JSON.stringify(d)));
      }
    } catch(e) {
      alert('Import error: ' + e.message);
    }
  };

  // ── Export / Delete ────────────────────────────────────────────────────────

  $('rs-export-btn').onclick = () => {
    if (!_activeSuiteId) return;
    window.open(api.exportRunSuiteUrl(_activeSuiteId), '_blank');
  };

  $('rs-delete-btn').onclick = async () => {
    if (!_activeSuiteId) return;
    if (!confirm('Delete run suite "' + _activeSuiteId + '"?')) return;
    await api.deleteRunSuite(_activeSuiteId);
    _activeSuiteId = null;
    $('rs-run-btn').disabled = true;
    $('rs-export-btn').disabled = true;
    $('rs-delete-btn').disabled = true;
    $('rs-suite-name').textContent = 'Select a suite →';
    $('rs-suite-desc').textContent = '';
    $('rs-scenario-tabs').innerHTML = '';
    $('rs-step-list').innerHTML = '<div class="text-muted-sm-centered">Select a run suite</div>';
    await loadRunSuites();
  };

  // ── Run / Abort ────────────────────────────────────────────────────────────

  $('rs-run-btn').onclick = runSuite;
  $('rs-abort-btn').onclick = async () => {
    await api.abortRunSuite();
    finishRun();
  };

  // ── Open / Close ──────────────────────────────────────────────────────────

  $('rs-close').onclick = rsClose;
  $('rs-modal').onclick = (e) => { if (e.target === $('rs-modal')) rsClose(); };

  $('btn-run-suites').onclick = rsOpen;
})();
