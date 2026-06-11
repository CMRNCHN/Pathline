// Suite Planning — manages planned suites, reusable inputs, and route checks.
// Requires: common/time.js, common/dom.js, common/api.js

(function() {
  let _suites = [];
  let _currentFilename = null;

  const DEFAULT_SCHEMA = 'account_number|phone_number|zip_code|case_id|date_of_birth|member_id|last_name|language';
  const DEFAULT_VARIABLE_LABELS = {
    account_number:'Account Number',
    phone_number:'Phone Number',
    zip_code:'ZIP Code',
    case_id:'Case ID',
    date_of_birth:'Date of Birth',
    member_id:'Member ID',
    last_name:'Last Name',
    language:'Language',
  };
  const DEFAULT_VARIABLES = Object.fromEntries(
    Object.keys(DEFAULT_VARIABLE_LABELS).map(k => [k, ''])
  );

  // ── Suite list ─────────────────────────────────────────────────────────────

  async function loadSuites() {
    const data = await api.listSuites();
    _suites = data.suites || [];
    renderSuitesList();
    renderPlanningEvidence();
  }

  function countPromptMatches(cases) {
    return (cases || []).reduce((total, item) => total + ((item.triggers || []).length), 0);
  }

  function renderSuitesList() {
    const container = $('ts-list');
    container.innerHTML = '';
    _suites.forEach(s => {
      const el = document.createElement('div');
      el.className = 'ts-item' + (_currentFilename === s.filename ? ' active' : '');
      const suiteData = s.data || {};
      const caseCount = (suiteData.cases || []).length;
      const promptCount = countPromptMatches(suiteData.cases || []);
      el.innerHTML =
        '<div class="ts-item-name">' + s.filename + '</div>' +
        '<div class="ts-item-meta">' + caseCount + ' route check' + (caseCount !== 1 ? 's' : '') + ' · ' + promptCount + ' prompt match' + (promptCount !== 1 ? 'es' : '') + '</div>';
      el.onclick = () => openSuite(s.filename);
      container.appendChild(el);
    });
  }

  // ── Editor ─────────────────────────────────────────────────────────────────

  function openSuite(filename) {
    _currentFilename = filename;
    const suite = _suites.find(s => s.filename === filename) || {
      filename,
      data: {
        name: filename.replace('.json', ''),
        target_number: '',
        cases: [],
        data_schema: DEFAULT_SCHEMA,
        variable_labels: DEFAULT_VARIABLE_LABELS,
        variables: DEFAULT_VARIABLES,
      },
    };
    $('ts-editor').style.display = 'block';
    $('ts-filename').value = suite.filename.replace('.json', '');
    $('ts-target').value = suite.data.target_number || '';
    $('ts-schema').value = suite.data.data_schema || '';
    $('ts-parse-status').textContent = '';
    renderVariables(suite.data.variables || {}, suite.data.variable_labels || {});
    renderCases(suite.data.cases || []);
    updateIntentField(suite.data.cases || []);
    renderPlanningEvidence(suite.data.target_number || '');
    renderSuitesList();
  }

  function updateIntentField(cases) {
    const promptMatches = countPromptMatches(cases);
    $('ts-intent').value = promptMatches > 0 ? 'Suite execution' : 'Route discovery';
  }

  async function ensureMapsLoaded() {
    if (typeof AppState !== 'undefined' && Array.isArray(AppState.savedMaps) && AppState.savedMaps.length) {
      return AppState.savedMaps;
    }
    try {
      const data = await api.getMaps();
      if (typeof AppState !== 'undefined') {
        AppState.savedMaps = data.maps || [];
      }
      return data.maps || [];
    } catch (_) {
      return [];
    }
  }

  async function renderPlanningEvidence(targetOverride) {
    const mapSummary = $('ts-map-summary');
    const reuseSummary = $('ts-reuse-summary');
    if (!mapSummary || !reuseSummary) return;

    const target = (targetOverride != null ? targetOverride : $('ts-target').value).trim();
    const suites = _suites || [];
    const activeSuite = suites.find((item) => item.filename === _currentFilename) || null;
    const editorData = $('ts-editor').style.display === 'block' ? getEditorData().data : null;
    const cases = (editorData && editorData.cases) || (activeSuite && activeSuite.data && activeSuite.data.cases) || [];
    const routeCheckCount = cases.length;
    const promptMatchCount = countPromptMatches(cases);
    const maps = await ensureMapsLoaded();
    const normalizedTarget = typeof normalizeTarget === 'function' ? normalizeTarget(target) : target;
    const savedMap = maps.find((item) => item.target === normalizedTarget) || null;

    if (!target) {
      mapSummary.textContent = 'Enter a target IVR to see whether saved IVR state mapping already exists.';
    } else if (savedMap) {
      mapSummary.textContent = 'Saved IVR state mapping found for ' + normalizedTarget + ' · ' + ((savedMap.session_count || 0) + ' prior run' + ((savedMap.session_count || 0) === 1 ? '' : 's')) + '.';
    } else {
      mapSummary.textContent = 'No saved IVR state mapping found yet for ' + normalizedTarget + '.';
    }

    reuseSummary.textContent =
      routeCheckCount + ' route check' + (routeCheckCount === 1 ? '' : 's') +
      ' · ' + promptMatchCount + ' prompt match' + (promptMatchCount === 1 ? '' : 'es') +
      (suites.length ? ' · ' + suites.length + ' saved suite' + (suites.length === 1 ? '' : 's') + ' available for reuse.' : ' · No saved suites yet.');
  }

  // ── Variables ──────────────────────────────────────────────────────────────

  function renderVariables(vars, labels) {
    const container = $('ts-vars-container');
    container.innerHTML = '';
    const entries = Object.keys(vars).length
      ? Object.entries(vars)
      : Object.entries(labels || {}).map(([k]) => [k, '']);
    const seen = new Set();
    entries.forEach(([k, v]) => { seen.add(k); container.appendChild(makeVarRow(labels?.[k] || '', k, v)); });
    Object.entries(labels || {}).forEach(([k, lbl]) => {
      if (!seen.has(k)) container.appendChild(makeVarRow(lbl, k, ''));
    });
  }

  function makeVarRow(label, key, val) {
    const esc = s => (s || '').replace(/"/g, '&quot;');
    const row = document.createElement('div');
    row.className = 'var-row';
    row.innerHTML =
      '<input class="var-label" placeholder="Account Number" value="' + esc(label) + '">' +
      '<input class="var-key" placeholder="account_number" value="' + esc(key) + '">' +
      '<input class="var-val' + (val ? ' filled' : '') + '" placeholder="value or auto-filled" value="' + esc(val) + '">' +
      '<button class="trigger-del" onclick="this.closest(\'.var-row\').remove()">✕</button>';
    return row;
  }

  function getVariables() {
    const vars = {}, labels = {};
    document.querySelectorAll('#ts-vars-container .var-row').forEach(row => {
      const lbl = row.querySelector('.var-label').value.trim();
      const k   = row.querySelector('.var-key').value.trim();
      const v   = row.querySelector('.var-val').value.trim();
      if (k) { vars[k] = v; if (lbl) labels[k] = lbl; }
    });
    return { vars, labels };
  }

  function parseDataRow() {
    const schemaRaw = $('ts-schema').value.trim();
    const dataRaw   = $('ts-datarow').value.trim();
    const status    = $('ts-parse-status');
    if (!schemaRaw || !dataRaw) { status.textContent = 'Paste both the input header row and input data row first.'; return; }
    const headers = schemaRaw.split('|').map(h => h.trim());
    const values  = dataRaw.split('|');
    const parsed  = {};
    headers.forEach((h, i) => { if (h) parsed[h] = (values[i] || '').trim(); });
    let filled = 0;
    document.querySelectorAll('#ts-vars-container .var-row').forEach(row => {
      const k = row.querySelector('.var-key').value.trim();
      if (k && parsed[k] !== undefined) {
        const inp = row.querySelector('.var-val');
        inp.value = parsed[k];
        inp.classList.add('filled');
        filled++;
      }
    });
    status.textContent = filled
      ? '✓ Filled ' + filled + ' reusable input' + (filled > 1 ? 's' : '') + ' from the imported row.'
      : 'No matching JSON keys found. Check that reusable input keys match your header columns.';
  }

  // ── Cases ──────────────────────────────────────────────────────────────────

  function renderCases(cases) {
    const container = $('ts-cases-container');
    container.innerHTML = '';
    cases.forEach((c, cIdx) => {
      const card = document.createElement('div');
      card.className = 'case-card';

      const hdr = document.createElement('div');
      hdr.style.cssText = 'display:flex;justify-content:space-between';
      hdr.innerHTML =
        '<input type="text" class="trigger-input case-name-input" value="' + (c.name || '') + '" placeholder="Route Check Name"' +
        ' style="font-weight:600;font-size:13px;border:none;background:transparent;padding:0;flex:none;width:200px;">' +
        '<button class="trigger-del" onclick="window._tsDeleteCase(' + cIdx + ')">🗑 Remove</button>';
      card.appendChild(hdr);

      const pathRow = document.createElement('div');
      pathRow.style.cssText = 'display:flex;gap:8px;align-items:center';
      pathRow.innerHTML =
        '<span style="font-size:11px;color:var(--text-3);width:112px;">Starting DTMF Path</span>' +
        '<input type="text" class="trigger-input path-input" value="' + (c.initial_path || []).join(', ') + '" placeholder="e.g. 1, 3, 2">';
      card.appendChild(pathRow);

      const triggersDiv = document.createElement('div');
      triggersDiv.className = 'triggers-container';
      (c.triggers || []).forEach((t, tIdx) => {
        const tr = document.createElement('div');
        tr.className = 'trigger-block';
        const esc = s => (s || '').replace(/"/g, '&quot;');
        tr.innerHTML =
          '<div class="trigger-title-row">' +
            '<span class="trigger-title-label">Checkpoint Name</span>' +
            '<input type="text" class="trigger-title-input t-title" value="' + esc(t.title) + '" placeholder="e.g. Account Number Check">' +
            '<button class="trigger-del" onclick="window._tsDeleteTrigger(' + cIdx + ',' + tIdx + ')" style="margin-left:4px;">✕</button>' +
          '</div>' +
          '<div class="trigger-row">' +
            '<input type="text" class="trigger-input t-phrase" value="' + esc(t.phrase) + '" placeholder="Prompt Match">' +
            '<input type="text" class="trigger-input t-resp" value="' + esc(t.response) + '" placeholder="Response Anchor">' +
            '<select class="trigger-select t-kind">' +
              '<option value="dtmf"' + (t.kind === 'dtmf' ? ' selected' : '') + '>DTMF</option>' +
              '<option value="speech"' + (t.kind === 'speech' ? ' selected' : '') + '>Speech</option>' +
            '</select>' +
          '</div>';
        triggersDiv.appendChild(tr);
      });
      card.appendChild(triggersDiv);

      const addTrigBtn = document.createElement('button');
      addTrigBtn.textContent = '+ Add Prompt Match';
      addTrigBtn.style.cssText = 'background:none;border:none;color:var(--accent);font-size:11px;cursor:pointer;text-align:left;margin-top:4px;';
      addTrigBtn.onclick = () => window._tsAddTrigger(cIdx);
      card.appendChild(addTrigBtn);

      container.appendChild(card);
    });
  }

  function getEditorData() {
    const filename = $('ts-filename').value.trim() || 'new_suite';
    const { vars, labels } = getVariables();
    const schema = $('ts-schema').value.trim();
    const data = {
      name: filename,
      target_number: $('ts-target').value.trim(),
      variables: vars,
      variable_labels: labels,
      ...(schema && { data_schema: schema }),
      cases: [],
    };
    document.querySelectorAll('.case-card').forEach(card => {
      const name = card.querySelector('.case-name-input').value.trim();
      const pathStr = card.querySelector('.path-input').value.trim();
      const initial_path = pathStr ? pathStr.split(',').map(s => s.trim()).filter(s => s) : [];
      const triggers = [];
      card.querySelectorAll('.trigger-block').forEach(tr => {
        const title    = tr.querySelector('.t-title')?.value.trim() || '';
        const phrase   = tr.querySelector('.t-phrase').value.trim();
        const response = tr.querySelector('.t-resp').value.trim();
        const kind     = tr.querySelector('.t-kind').value;
        const t = { phrase, response, kind };
        if (title) t.title = title;
        triggers.push(t);
      });
      data.cases.push({ name, initial_path, triggers });
    });
    updateIntentField(data.cases);
    return { filename, data };
  }

  // ── Save / Run ─────────────────────────────────────────────────────────────

  async function saveSuite() {
    const { filename, data } = getEditorData();
    if (!data.target_number) { alert('Please enter a target IVR for the planned suite.'); return false; }
    if (!data.cases.length)  { alert('Please add at least one route check.'); return false; }
    for (const c of data.cases) {
      if (!c.name) { alert('Each route check must have a name.'); return false; }
      for (const t of (c.triggers || [])) {
        if (!t.phrase || !t.response) {
          alert('Route check "' + c.name + '" has a prompt match missing its response anchor.');
          return false;
        }
      }
    }
    try {
      await api.saveSuite(filename, data);
      if (window.Telemetry) {
        window.Telemetry.track('map_saved', { filename, case_count: data.cases.length });
      }
    } catch(e) {
      alert(e.message || 'Failed to save the reusable suite.');
      return false;
    }
    await loadSuites();
    openSuite(filename + (filename.endsWith('.json') ? '' : '.json'));
    return true;
  }

  async function runSuite() {
    const saved = await saveSuite();
    if (!saved) return;
    const { filename } = getEditorData();
    const fname = filename + (filename.endsWith('.json') ? '' : '.json');
    $('ts-modal').style.display = 'none';
    try {
      await api.runSuite(fname);
      addLog('[system] Reusable suite ' + fname + ' started in background.');
    } catch(e) {
      addLog('[error] ' + (e.message || 'Failed to start reusable suite.'));
      alert(e.message || 'Failed to start reusable suite.');
    }
  }

  // ── Window-exposed mutation helpers (used by inline onclick in renderCases) ─

  window._tsDeleteCase = function(idx) {
    const { data } = getEditorData();
    data.cases.splice(idx, 1);
    renderCases(data.cases);
    renderPlanningEvidence();
  };
  window._tsDeleteTrigger = function(cIdx, tIdx) {
    const { data } = getEditorData();
    data.cases[cIdx].triggers.splice(tIdx, 1);
    renderCases(data.cases);
    renderPlanningEvidence();
  };
  window._tsAddTrigger = function(cIdx) {
    const { data } = getEditorData();
    data.cases[cIdx].triggers.push({ title: '', phrase: '', response: '', kind: 'dtmf' });
    renderCases(data.cases);
    renderPlanningEvidence();
  };

  // ── Event wiring ───────────────────────────────────────────────────────────

  $('btn-test-suite').onclick = () => { $('ts-modal').style.display = 'flex'; loadSuites(); };
  $('ts-close').onclick      = () => { $('ts-modal').style.display = 'none'; };
  $('ts-new-btn').onclick    = () => openSuite('new_suite');
  $('ts-save-btn').onclick   = saveSuite;
  $('ts-run-btn').onclick    = runSuite;
  $('ts-parse-btn').onclick  = parseDataRow;
  $('ts-target').addEventListener('input', () => renderPlanningEvidence());

  $('ts-add-case').onclick = () => {
    const { data } = getEditorData();
    data.cases.push({ name: 'New Route Check', initial_path: [], triggers: [] });
    renderCases(data.cases);
    renderPlanningEvidence();
  };
  $('ts-add-var').onclick = () => {
    $('ts-vars-container').appendChild(makeVarRow('', '', ''));
  };
})();
