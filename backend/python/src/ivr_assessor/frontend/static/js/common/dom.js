// Requires: time.js

function $(id) { return document.getElementById(id); }

const _seenLogs = new Set();

function addLog(message) {
  if (_seenLogs.has(message)) return;
  _seenLogs.add(message);
  const transcript = $('transcript');
  if (transcript.querySelector('.empty-state')) transcript.innerHTML = '';
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  const isTranscript = message.includes('[transcript]');
  const isError = message.includes('[error]') || message.includes('Error');
  const cls = isTranscript ? 'transcript' : isError ? 'error' : '';
  entry.innerHTML =
    '<span class="log-time">' + timestamp() + '</span>' +
    '<span class="log-text ' + cls + '">' +
    message.replace(/</g, '&lt;').replace(/>/g, '&gt;') +
    '</span>';
  transcript.appendChild(entry);
  transcript.scrollTop = transcript.scrollHeight;
}

function addLiveFeedLine(cls, text) {
  const el = $('rs-live-feed');
  const div = document.createElement('div');
  div.className = 'rs-event-line ' + cls;
  div.textContent = '[' + timestamp() + '] ' + text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}
