async function _fetch(path, opts) {
  const resp = await fetch(path, opts || {});
  if (!resp.ok) {
    let msg = 'HTTP ' + resp.status;
    try { const d = await resp.json(); if (d && d.error) msg = d.error; } catch(_) {}
    throw new Error(msg);
  }
  try { return await resp.json(); } catch(_) { return null; }
}

function _post(path, body) {
  return _fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const api = {
  // Status & config
  getStatus: () => _fetch('/api/status'),
  getConfig: () => _fetch('/api/config'),
  setMode:   (manual_mode) => _post('/api/set-mode', { manual_mode }),

  // Call control
  startCall:   (payload) => _post('/api/start', payload),
  injectDtmf:  (digits)  => _post('/api/inject-dtmf', { digits }),
  injectVoice: (text)    => _post('/api/inject-voice', { text }),

  // Test suite editor
  listSuites: () => _fetch('/api/suites'),
  saveSuite:  (filename, data) => _post('/api/suites', { filename, data }),
  runSuite:   (filename) => _post('/api/suites/run', { filename }),

  // Run suites
  listRunSuites:     () => _fetch('/api/run-suites'),
  getRunSuite:       (id) => _fetch('/api/run-suites/' + id + '/export'),
  runRunSuite:       (id) => _post('/api/run-suites/' + id + '/run', {}),
  pollRunSuite:      (id) => _fetch('/api/run-suites/' + id + '/poll'),
  importRunSuite:    (json) => _post('/api/run-suites/import', { json }),
  exportRunSuiteUrl: (id) => '/api/run-suites/' + id + '/export',
  deleteRunSuite:    (id) => _fetch('/api/run-suites/' + id, { method: 'DELETE' }),
  abortRunSuite:     () => _post('/api/run-suites/abort', {}),
};
