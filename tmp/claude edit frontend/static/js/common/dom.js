// Requires: time.js

function $(id) { return document.getElementById(id); }

const _seenLogs = new Set();

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderEmptyState(icon, title, detail) {
  return (
    '<div class="empty-state">' +
      '<div class="empty-icon">' + escapeHtml(icon || '•') + '</div>' +
      '<p>' + escapeHtml(title || 'No data yet') + '</p>' +
      (detail ? '<span>' + escapeHtml(detail) + '</span>' : '') +
    '</div>'
  );
}

function renderStatePill(text, tone) {
  return '<span class="state-pill tone-' + escapeHtml(tone || 'neutral') + '">' + escapeHtml(text) + '</span>';
}

function renderHeartbeatCards(cards) {
  return cards.map(card =>
    '<article class="heartbeat-card tone-' + escapeHtml(card.tone || 'neutral') + '">' +
      '<div class="heartbeat-label">' + escapeHtml(card.label || '') + '</div>' +
      '<div class="heartbeat-value">' + escapeHtml(card.value || 'Unknown') + '</div>' +
      '<div class="heartbeat-meta">' + escapeHtml(card.meta || 'Not surfaced') + '</div>' +
    '</article>'
  ).join('');
}

function renderTimelineRows(rows, selectedId) {
  return rows.map(row => (
    '<button class="timeline-row tone-' + escapeHtml(row.tone || 'neutral') +
      (selectedId === row.id ? ' is-selected' : '') + '"' +
      ' data-timeline-id="' + escapeHtml(row.id) + '">' +
      '<span class="timeline-marker"></span>' +
      '<span class="timeline-main">' +
        '<span class="timeline-title-row">' +
          '<span class="timeline-title">' + escapeHtml(row.title || row.kind || 'Event') + '</span>' +
          renderStatePill(row.badge || 'Event', row.tone || 'neutral') +
        '</span>' +
        '<span class="timeline-detail">' + escapeHtml(row.detail || 'No detail') + '</span>' +
      '</span>' +
      '<span class="timeline-meta">' + escapeHtml(row.meta || '') + '</span>' +
    '</button>'
  )).join('');
}

function renderKeyValueTable(rows) {
  return (
    '<div class="kv-table">' +
      rows.map(row =>
        '<div class="kv-row">' +
          '<span class="kv-key">' + escapeHtml(row.key || '') + '</span>' +
          '<span class="kv-value">' + escapeHtml(row.value || '—') + '</span>' +
        '</div>'
      ).join('') +
    '</div>'
  );
}

function renderGraphMeta(items) {
  return items.map(item =>
    '<span class="meta-chip">' +
      '<span class="meta-chip-label">' + escapeHtml(item.label || '') + '</span>' +
      '<span class="meta-chip-value">' + escapeHtml(item.value || '—') + '</span>' +
    '</span>'
  ).join('');
}

function addLog(message) {
  if (_seenLogs.has(message)) return;
  _seenLogs.add(message);
  AppState.legacyLogs.push({
    message,
    at: Date.now(),
    level: message.includes('[error]') || message.includes('Error')
      ? 'error'
      : (message.includes('[transcript]') ? 'accent' : 'neutral'),
  });
  AppState.legacyLogs = AppState.legacyLogs.slice(-60);
  if (typeof window.renderOperatorConsole === 'function') {
    window.renderOperatorConsole();
  }
}

function addLiveFeedLine(cls, text) {
  const el = $('rs-live-feed');
  const div = document.createElement('div');
  div.className = 'rs-event-line ' + cls;
  div.textContent = '[' + timestamp() + '] ' + text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}
