// Test Suite Editor — manages the suite list, editor panel, variables, and cases.
// Requires: common/time.js, common/dom.js, common/api.js

(function() {
  let _suites = [];
  let _currentFilename = null;

  const DEFAULT_SCHEMA = '_id|bin|base|level|cc|exp|expmonth|expyear|cvv|name|firstname|lastname|address|city|zip|state|country|bank|type|brand|phone|dob|ua|ssn|mmn|dl|other|email|ip';
  const DEFAULT_VARIABLE_LABELS = {
    _id:'ID', bin:'BIN', base:'Base', level:'Level',
    cc:'Card Number', exp:'Expiration', expmonth:'Exp Month', expyear:'Exp Year', cvv:'CVV',
    name:'Full Name', firstname:'First Name', lastname:'Last Name',
    address:'Address', city:'City', zip:'ZIP Code', state:'State', country:'Country',
    bank:'Bank', type:'Card Type', brand:'Brand', phone:'Phone', dob:'Date of Birth',
    ua:'User Agent', ssn:'SSN', mmn:"Mother's Maiden Name", dl:"Driver's License",
    other:'Other', email:'Email', ip:'IP Address',
  };
  const DEFAULT_VARIABLES = Object.fromEntries(
    Object.keys(DEFAULT_VARIABLE_LABELS).map(k => [k, ''])
  );

  // ── Suite list ─────────────────────────────────────────────────────────────

  async function loadSuites() {
    const data = await api.listSuites();
    _suites = data.suites || [];
    renderSuitesList();
  }

  function renderSuitesList() {
    const container = $('ts-list');
    container.innerHTML = '';
    _suites.forEach(s => {
      const el = document.createElement('div');
      el.className = 'ts-item' + (_currentFilename === s.filename ? ' active' : '');
      el.textContent = s.filename;
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
    renderSuitesList();
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
      '<input class="var-label" placeholder="Card Number" value="' + esc(label) + '">' +
      '<input class="var-key" placeholder="cc_num" value="' + esc(key) + '">' +
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
    if (!schemaRaw || !dataRaw) { status.textContent = 'Paste both header and data row first.'; return; }
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
      ? '✓ Filled ' + filled + ' variable' + (filled > 1 ? 's' : '') + ' from data row.'
      : 'No matching JSON keys found. Check key names match your header columns.';
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
        '<input type="text" class="trigger-input" value="' + (c.name || '') + '" placeholder="Case Name"' +
        ' style="font-weight:600;font-size:13px;border:none;background:transparent;padding:0;flex:none;width:200px;">' +
        '<button class="trigger-del" onclick="window._tsDeleteCase(' + cIdx + ')">🗑 Remove</button>';
      card.appendChild(hdr);

      const pathRow = document.createElement('div');
      pathRow.style.cssText = 'display:flex;gap:8px;align-items:center';
      pathRow.innerHTML =
        '<span style="font-size:11px;color:var(--text-3);width:80px;">Initial Path</span>' +
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
            '<span class="trigger-title-label">Title</span>' +
            '<input type="text" class="trigger-title-input t-title" value="' + esc(t.title) + '" placeholder="e.g. Account Number">' +
            '<button class="trigger-del" onclick="window._tsDeleteTrigger(' + cIdx + ',' + tIdx + ')" style="margin-left:4px;">✕</button>' +
          '</div>' +
          '<div class="trigger-row">' +
            '<input type="text" class="trigger-input t-phrase" value="' + esc(t.phrase) + '" placeholder="IVR says…">' +
            '<input type="text" class="trigger-input t-resp" value="' + esc(t.response) + '" placeholder="Reply (or $variable)">' +
            '<select class="trigger-select t-kind">' +
              '<option value="dtmf"' + (t.kind === 'dtmf' ? ' selected' : '') + '>DTMF</option>' +
              '<option value="speech"' + (t.kind === 'speech' ? ' selected' : '') + '>Speech</option>' +
            '</select>' +
          '</div>';
        triggersDiv.appendChild(tr);
      });
      card.appendChild(triggersDiv);

      const addTrigBtn = document.createElement('button');
      addTrigBtn.textContent = '+ Add Trigger';
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
      const name = card.querySelector('input[placeholder="Case Name"]').value.trim();
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
    return { filename, data };
  }

  // ── Save / Run ─────────────────────────────────────────────────────────────

  async function saveSuite() {
    const { filename, data } = getEditorData();
    if (!data.target_number) { alert('Please enter a default target number for the suite.'); return false; }
    if (!data.cases.length)  { alert('Please add at least one test case.'); return false; }
    for (const c of data.cases) {
      if (!c.name) { alert('Each test case must have a name.'); return false; }
      for (const t of (c.triggers || [])) {
        if (!t.phrase || !t.response) {
          alert('Case "' + c.name + '" has a trigger missing phrase or response.');
          return false;
        }
      }
    }
    try {
      await api.saveSuite(filename, data);
    } catch(e) {
      alert(e.message || 'Failed to save suite.');
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
      addLog('[system] Test suite ' + fname + ' started in background.');
    } catch(e) {
      addLog('[error] ' + (e.message || 'Failed to start test suite.'));
      alert(e.message || 'Failed to start test suite.');
    }
  }

  // ── Window-exposed mutation helpers (used by inline onclick in renderCases) ─

  window._tsDeleteCase = function(idx) {
    const { data } = getEditorData();
    data.cases.splice(idx, 1);
    renderCases(data.cases);
  };
  window._tsDeleteTrigger = function(cIdx, tIdx) {
    const { data } = getEditorData();
    data.cases[cIdx].triggers.splice(tIdx, 1);
    renderCases(data.cases);
  };
  window._tsAddTrigger = function(cIdx) {
    const { data } = getEditorData();
    data.cases[cIdx].triggers.push({ title: '', phrase: '', response: '', kind: 'dtmf' });
    renderCases(data.cases);
  };

  // ── Event wiring ───────────────────────────────────────────────────────────

  $('btn-test-suite').onclick = () => { $('ts-modal').style.display = 'flex'; loadSuites(); };
  $('ts-close').onclick      = () => { $('ts-modal').style.display = 'none'; };
  $('ts-new-btn').onclick    = () => openSuite('new_suite');
  $('ts-save-btn').onclick   = saveSuite;
  $('ts-run-btn').onclick    = runSuite;
  $('ts-parse-btn').onclick  = parseDataRow;

  $('ts-add-case').onclick = () => {
    const { data } = getEditorData();
    data.cases.push({ name: 'New Case', initial_path: [], triggers: [] });
    renderCases(data.cases);
  };
  $('ts-add-var').onclick = () => {
    $('ts-vars-container').appendChild(makeVarRow('', '', ''));
  };
})();
