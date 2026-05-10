function timestamp() {
  return new Date().toLocaleTimeString();
}

function formatTimer(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function formatDuration(ms) {
  return ms != null ? Math.round(ms) + 'ms' : '';
}
