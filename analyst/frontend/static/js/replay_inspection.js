/**
 * replay_inspection.js — Analyst UI for Replay Inspection
 * Owned by Agent 4 (analyst UI). Vanilla JS, no framework.
 *
 * Boot data is injected by the server into:
 *   const RI_BOOT = { session_id: "<value>" };
 * RI_BOOT is already a JS object — no JSON.parse needed.
 */

/* global RI_BOOT */

(function () {
  'use strict';

  // ── Section anchor map ──────────────────────────────────────────────────────
  // Maps the first segment of field_path (or a reference kind) to a section ID.
  var FIELD_PREFIX_TO_ANCHOR = {
    identity:              '#section-identity',
    session_metadata:      '#section-identity',
    summary:               '#section-identity',
    anomalies:             '#section-anomalies',
    next_steps:            '#section-next-steps',
    chronology:            '#section-chronology',
    path:                  '#section-path',
    state_diagnostics:     '#section-diagnostics',
    correlation:           '#section-diagnostics',
    media_status:          '#section-diagnostics',
    artifact_availability: '#section-artifacts',
    bookmarks_annotations: '#section-bookmarks',
  };

  var KIND_TO_ANCHOR = {
    event:     '#section-chronology',
    timestamp: '#section-chronology',
    artifact:  '#section-artifacts',
    media:     '#section-diagnostics',
    snapshot:  '#section-diagnostics',
    session:   '#section-identity',
  };

  // ── Utilities ───────────────────────────────────────────────────────────────

  function $id(id) {
    return document.getElementById(id);
  }

  function show(el) {
    el && el.classList.remove('is-hidden');
  }

  function hide(el) {
    el && el.classList.add('is-hidden');
  }

  function esc(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtMs(ms) {
    if (ms == null) return '—';
    if (ms < 1000) return ms + ' ms';
    return (ms / 1000).toFixed(2) + ' s';
  }

  function fmtTimestamp(ts) {
    // ts is epoch float (seconds) or null
    if (ts == null) return '—';
    try {
      return new Date(ts * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
    } catch (_) {
      return String(ts);
    }
  }

  function fmtBool(val) {
    if (val == null) return '—';
    return val ? 'Yes' : 'No';
  }

  function nvl(val, fallback) {
    if (val == null || val === '') return fallback != null ? fallback : '—';
    return val;
  }

  // Derive anchor from a Reference object
  function refToAnchor(ref) {
    if (ref.field_path) {
      var prefix = ref.field_path.split('.')[0];
      if (FIELD_PREFIX_TO_ANCHOR[prefix]) return FIELD_PREFIX_TO_ANCHOR[prefix];
    }
    if (ref.kind && KIND_TO_ANCHOR[ref.kind]) return KIND_TO_ANCHOR[ref.kind];
    return null;
  }

  function kindBadgeClass(kind) {
    if (!kind) return '';
    var k = kind.toLowerCase();
    if (k === 'prompt') return 'kind-prompt';
    if (k === 'dtmf') return 'kind-dtmf';
    if (k === 'action') return 'kind-action';
    if (k === 'speech' || k === 'tts') return 'kind-speech';
    if (k === 'error') return 'kind-error';
    if (k.indexOf('warn') !== -1) return 'kind-warn';
    return '';
  }

  // ── DOM helpers ─────────────────────────────────────────────────────────────

  function makeStatCard(label, value, opts) {
    opts = opts || {};
    var extraClass = opts.extraClass || '';
    var mono = opts.mono !== false;
    var valueClass = 'ri-stat-value' + (mono ? '' : ' normal') + (opts.large ? ' large' : '');
    var div = document.createElement('div');
    div.className = 'ri-stat-card';
    div.innerHTML =
      '<div class="ri-stat-label">' + esc(label) + '</div>' +
      '<div class="' + valueClass + (extraClass ? ' ' + extraClass : '') + '">' + esc(String(value)) + '</div>';
    return div;
  }

  function makeKvPanel(title, rows) {
    // rows: [{key, val, tone}]
    var div = document.createElement('div');
    div.className = 'ri-kv-panel';
    var html = '<div class="ri-kv-label">' + esc(title) + '</div>';
    rows.forEach(function (r) {
      var toneClass = r.tone ? ' tone-' + r.tone : '';
      html +=
        '<div class="ri-kv-row">' +
        '<span class="ri-kv-key">' + esc(r.key) + '</span>' +
        '<span class="ri-kv-val' + toneClass + '">' + esc(nvl(r.val)) + '</span>' +
        '</div>';
    });
    div.innerHTML = html;
    return div;
  }

  function makeChipList(chips, chipClass) {
    var div = document.createElement('div');
    div.className = 'ri-chip-list';
    if (!chips || chips.length === 0) {
      div.innerHTML = '<span class="ri-empty">None</span>';
    } else {
      chips.forEach(function (c) {
        var span = document.createElement('span');
        span.className = 'ri-chip' + (chipClass ? ' ' + chipClass : '');
        span.textContent = c;
        div.appendChild(span);
      });
    }
    return div;
  }

  // ── Scroll-to highlight ─────────────────────────────────────────────────────

  function scrollToSection(anchor) {
    if (!anchor) return;
    var el = document.querySelector(anchor);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.add('ri-highlight');
    setTimeout(function () { el.classList.remove('ri-highlight'); }, 1400);
  }

  // ── State / error display ───────────────────────────────────────────────────

  function showError(title, msg) {
    hide($id('ri-loading'));
    var banner = $id('ri-error-banner');
    show(banner);
    $id('ri-error-msg').textContent = (title ? title + ': ' : '') + (msg || 'Unknown error');
  }

  function showLoading() {
    show($id('ri-loading'));
    hide($id('ri-error-banner'));
  }

  function hideLoading() {
    hide($id('ri-loading'));
  }

  // ── Render helpers ───────────────────────────────────────────────────────────

  // 1. Identity + Summary
  function renderIdentity(report) {
    var section = $id('section-identity');
    var grid = $id('ri-identity-grid');
    grid.innerHTML = '';

    var id = report.identity || {};
    var meta = report.session_metadata || {};
    var sum = report.summary || {};

    var cards = [
      { label: 'Session ID',    value: nvl(id.session_id),   extraClass: '', mono: true },
      { label: 'Call SID',      value: nvl(id.call_sid),     mono: true },
      { label: 'Target',        value: nvl(meta.target),     mono: false },
      { label: 'Source Kind',   value: nvl(id.source_kind),  mono: false },
      { label: 'Duration',      value: meta.duration_ms != null ? fmtMs(meta.duration_ms) : '—', mono: true },
      { label: 'Events',        value: sum.event_count != null ? sum.event_count : '—', large: true },
      { label: 'Prompts',       value: sum.prompt_count != null ? sum.prompt_count : '—', large: true },
      { label: 'Actions',       value: sum.action_count != null ? sum.action_count : '—', large: true },
      { label: 'Nodes',         value: sum.node_count   != null ? sum.node_count   : '—', large: true },
      { label: 'Manual Mode',   value: fmtBool(meta.manual_mode), mono: false },
      { label: 'Started At',    value: meta.started_at != null ? fmtTimestamp(meta.started_at) : nvl(meta.created_at), mono: false },
    ];

    if (sum.first_prompt) {
      cards.push({ label: 'First Prompt', value: sum.first_prompt, mono: false });
    }
    if (sum.last_prompt) {
      cards.push({ label: 'Last Prompt', value: sum.last_prompt, mono: false });
    }
    if (sum.last_action) {
      cards.push({ label: 'Last Action', value: sum.last_action, mono: false });
    }
    if (sum.largest_gap_ms != null) {
      cards.push({ label: 'Largest Gap', value: fmtMs(sum.largest_gap_ms), mono: true });
    }

    cards.forEach(function (c) {
      grid.appendChild(makeStatCard(c.label, c.value, { mono: c.mono !== false, large: !!c.large, extraClass: c.extraClass || '' }));
    });

    // Notes
    var notes = (sum.notes || []).filter(Boolean);
    var notesContainer = $id('ri-notes-container');
    var notesList = $id('ri-notes-list');
    if (notes.length > 0) {
      notesList.innerHTML = '';
      notes.forEach(function (n) {
        var div = document.createElement('div');
        div.className = 'ri-note-item';
        div.textContent = n;
        notesList.appendChild(div);
      });
      show(notesContainer);
    } else {
      hide(notesContainer);
    }

    // Update page title
    var sid = id.session_id || '';
    var titleEl = $id('ri-page-title');
    if (titleEl && sid) {
      titleEl.textContent = 'Replay Inspection — ' + sid;
      document.title = 'Pathline — Inspect ' + sid;
    }

    show(section);
  }

  // 2. Anomalies
  function renderAnomalies(anomalies) {
    var section = $id('section-anomalies');
    var list = $id('ri-anomaly-list');
    list.innerHTML = '';

    if (!anomalies || anomalies.length === 0) {
      list.innerHTML = '<div class="ri-empty">No anomalies detected.</div>';
      show(section);
      return;
    }

    anomalies.forEach(function (a) {
      var sev = a.severity || 'info';
      var div = document.createElement('div');
      div.className = 'ri-anomaly-item sev-' + esc(sev);

      var badgeText = sev.toUpperCase();
      var header =
        '<div class="ri-anomaly-header">' +
        '<span class="ri-anomaly-badge">' + esc(badgeText) + '</span>' +
        '<span class="ri-anomaly-code">' + esc(a.code || '') + '</span>' +
        '</div>';

      var explanation = a.explanation
        ? '<div class="ri-anomaly-explanation">' + esc(a.explanation) + '</div>'
        : '';

      var refsHtml = '';
      var refs = a.references || [];
      if (refs.length > 0) {
        var refItems = refs.map(function (r) {
          return '<span class="ri-anomaly-ref"><span class="ref-kind">' + esc(r.kind || '') + '</span>' + esc(r.label || '') + '</span>';
        }).join('');
        refsHtml = '<div class="ri-anomaly-refs">' + refItems + '</div>';
      }

      div.innerHTML = header + explanation + refsHtml;
      list.appendChild(div);
    });

    show(section);
  }

  // 3. Next Steps
  function renderNextSteps(nextSteps) {
    var section = $id('section-next-steps');
    var list = $id('ri-nextsteps-list');
    list.innerHTML = '';

    if (!nextSteps || nextSteps.length === 0) {
      list.innerHTML = '<div class="ri-empty">No next steps.</div>';
      show(section);
      return;
    }

    nextSteps.forEach(function (ns, idx) {
      var div = document.createElement('div');
      div.className = 'ri-nextstep-item';

      var header =
        '<div class="ri-nextstep-header">' +
        '<span class="ri-nextstep-num">' + (idx + 1) + '</span>' +
        '<div class="ri-nextstep-action">' + esc(ns.action || '') + '</div>' +
        '</div>';

      var rationale = ns.rationale
        ? '<div class="ri-nextstep-rationale">' + esc(ns.rationale) + '</div>'
        : '';

      var citesHtml = '';
      var cites = ns.cites || [];
      if (cites.length > 0) {
        var citeButtons = cites.map(function (c) {
          var anchor = refToAnchor(c);
          var label = c.label || c.field_path || c.kind || 'Reference';
          if (anchor) {
            return '<button type="button" class="ri-cite-btn" data-anchor="' + esc(anchor) + '">' +
              '<span class="ri-cite-arrow">&#8594;</span>' + esc(label) +
              '</button>';
          }
          return '<span class="ri-anomaly-ref"><span class="ref-kind">' + esc(c.kind || '') + '</span>' + esc(label) + '</span>';
        }).join('');
        citesHtml = '<div class="ri-nextstep-cites">' + citeButtons + '</div>';
      }

      div.innerHTML = header + rationale + citesHtml;

      // Attach click handlers for cite buttons after inserting HTML
      list.appendChild(div);
      div.querySelectorAll('.ri-cite-btn[data-anchor]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          scrollToSection(btn.getAttribute('data-anchor'));
        });
      });
    });

    show(section);
  }

  // 4. Chronology
  function renderChronology(chronology) {
    var section = $id('section-chronology');
    var tbody = $id('ri-chronology-body');
    tbody.innerHTML = '';

    var entries = (chronology && chronology.entries) ? chronology.entries : [];

    if (entries.length === 0) {
      var tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="ri-empty" style="text-align:center;padding:20px;">No chronology entries.</td>';
      tbody.appendChild(tr);
      show(section);
      return;
    }

    entries.forEach(function (e) {
      var tr = document.createElement('tr');

      var kindClass = kindBadgeClass(e.kind);
      var kindBadge = '<span class="ri-kind-badge' + (kindClass ? ' ' + kindClass : '') + '">' + esc(e.kind || '') + '</span>';

      // Text / preview column
      var text = e.text_preview || e.text || '';
      var textCell = '<span class="ri-text-preview">' + esc(text) + '</span>';
      if (e.dtmf) {
        textCell += '<span class="ri-dtmf-pill">' + esc(e.dtmf) + '</span>';
      }

      tr.innerHTML =
        '<td class="ri-seq-num">' + esc(String(e.seq != null ? e.seq : '')) + '</td>' +
        '<td>' + kindBadge + '</td>' +
        '<td class="ri-t-ms">' + esc(e.t_ms != null ? e.t_ms : '—') + '</td>' +
        '<td class="ri-delta">' + esc(e.delta_ms != null ? '+' + e.delta_ms : '—') + '</td>' +
        '<td>' + textCell + '</td>';

      tbody.appendChild(tr);
    });

    show(section);
  }

  // 5. Path
  function renderPath(path) {
    var section = $id('section-path');
    var grid = $id('ri-path-grid');
    grid.innerHTML = '';

    path = path || {};

    var panels = [
      { label: 'DTMF Path',       chips: path.dtmf_path,      chipClass: 'dtmf' },
      { label: 'Visited Nodes',   chips: path.visited_nodes,  chipClass: 'node' },
      { label: 'Root Prompts',    chips: path.root_prompts,   chipClass: '' },
      { label: 'Unique Actions',  chips: path.unique_actions, chipClass: '' },
    ];

    panels.forEach(function (p) {
      var div = document.createElement('div');
      div.className = 'ri-path-subpanel';
      div.innerHTML = '<div class="ri-path-sublabel">' + esc(p.label) + '</div>';
      div.appendChild(makeChipList(p.chips || [], p.chipClass));
      grid.appendChild(div);
    });

    // Active path
    if (path.active_path && path.active_path.length > 0) {
      var apDiv = document.createElement('div');
      apDiv.className = 'ri-path-subpanel';
      apDiv.style.gridColumn = '1 / -1';
      apDiv.innerHTML = '<div class="ri-path-sublabel">Active Path</div>';
      apDiv.appendChild(makeChipList(path.active_path, 'node'));
      grid.appendChild(apDiv);
    }

    // Steps
    var steps = path.steps || [];
    var stepsContainer = $id('ri-path-steps-container');
    var stepsEl = $id('ri-path-steps');
    stepsEl.innerHTML = '';

    if (steps.length > 0) {
      steps.forEach(function (s, idx) {
        var div = document.createElement('div');
        div.className = 'ri-step-row';
        div.innerHTML =
          '<span class="ri-step-idx">' + (s.event_index != null ? s.event_index : idx) + '</span>' +
          '<span class="ri-step-kind">' + esc(s.kind || '—') + '</span>' +
          '<span class="ri-step-value">' + esc(nvl(s.value)) + '</span>' +
          '<span class="ri-step-t">' + (s.t_ms != null ? s.t_ms + ' ms' : '') + '</span>';
        stepsEl.appendChild(div);
      });
      show(stepsContainer);
    } else {
      hide(stepsContainer);
    }

    show(section);
  }

  // 6. State diagnostics + media + correlation
  function renderDiagnostics(report) {
    var section = $id('section-diagnostics');
    var grid = $id('ri-diag-grid');
    grid.innerHTML = '';

    var sd = report.state_diagnostics || {};
    var ms = report.media_status || {};
    var co = report.correlation || {};

    // State Diagnostics panel
    var sdRows = [
      { key: 'Graph Nodes',     val: sd.graph_node_count != null ? sd.graph_node_count : '—' },
      { key: 'Transcript Count',val: sd.transcript_count != null ? sd.transcript_count : '—' },
      { key: 'Visited Nodes',   val: sd.visited_node_count != null ? sd.visited_node_count : '—' },
      { key: 'Total Events',    val: sd.total_event_count != null ? sd.total_event_count : '—' },
      { key: 'Call Status',     val: nvl(sd.call_status) },
      { key: 'Snapshot Offset', val: sd.snapshot_offset != null ? sd.snapshot_offset : '—' },
      { key: 'Target Offset',   val: sd.target_offset != null ? sd.target_offset : '—' },
    ];
    var sdPanel = makeKvPanel('State Diagnostics', sdRows);

    // Add error detail if present
    if (sd.error) {
      var errDiv = document.createElement('div');
      errDiv.className = 'ri-error-detail';
      errDiv.textContent = sd.error;
      sdPanel.appendChild(errDiv);
    }
    grid.appendChild(sdPanel);

    // Media Status panel
    var mediaRows = [
      { key: 'Recording',         val: ms.recording_available ? 'Available' : 'Unavailable', tone: ms.recording_available ? 'ok' : 'error' },
      { key: 'Waveform',          val: ms.waveform_available  ? 'Available' : 'Unavailable', tone: ms.waveform_available  ? 'ok' : 'error' },
      { key: 'Media Duration',    val: ms.media_duration_ms != null ? fmtMs(ms.media_duration_ms) : '—' },
      { key: 'Recording Ref',     val: nvl(ms.recording_reference) },
      { key: 'Waveform Ref',      val: nvl(ms.waveform_reference) },
      { key: 'Replay Anchor',     val: nvl(ms.replay_anchor_timestamp) },
    ];
    grid.appendChild(makeKvPanel('Media Status', mediaRows));

    // Correlation Timing panel
    var coRows = [
      { key: 'Session Duration',           val: co.session_duration_ms != null ? fmtMs(co.session_duration_ms) : '—' },
      { key: 'Startup → GUI Ready',        val: co.startup_to_gui_ready_ms != null ? fmtMs(co.startup_to_gui_ready_ms) : '—' },
      { key: 'Session Start → 1st Prompt', val: co.session_start_to_first_prompt_ms != null ? fmtMs(co.session_start_to_first_prompt_ms) : '—' },
      { key: 'Session Start → 1st Action', val: co.session_start_to_first_action_ms != null ? fmtMs(co.session_start_to_first_action_ms) : '—' },
      { key: 'Stream → 1st Prompt',        val: co.stream_connect_to_first_prompt_ms != null ? fmtMs(co.stream_connect_to_first_prompt_ms) : '—' },
      { key: 'Last Activity',              val: co.last_activity_at != null ? fmtTimestamp(co.last_activity_at) : '—' },
      { key: 'Idle For',                   val: co.idle_for_s != null ? co.idle_for_s.toFixed(1) + ' s' : '—' },
    ];
    grid.appendChild(makeKvPanel('Correlation Timing', coRows));

    show(section);
  }

  // 7. Artifact availability
  function renderArtifacts(availability) {
    var section = $id('section-artifacts');
    var tbody = $id('ri-artifacts-body');
    tbody.innerHTML = '';

    var entries = (availability && availability.entries) ? availability.entries : [];

    if (entries.length === 0) {
      var tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="ri-empty" style="text-align:center;padding:20px;">No artifact data.</td>';
      tbody.appendChild(tr);
      show(section);
      return;
    }

    entries.forEach(function (e) {
      var tr = document.createElement('tr');
      var dotClass = e.available ? 'avail' : 'missing';
      var statusText = e.available ? 'Available' : 'Missing';

      tr.innerHTML =
        '<td><span class="ri-avail-dot ' + dotClass + '"></span>' + esc(statusText) + '</td>' +
        '<td class="ri-artifact-name">' + esc(e.artifact || '') + '</td>' +
        '<td class="ri-artifact-location">' + esc(nvl(e.location)) + '</td>' +
        '<td>' + esc(e.file_count != null ? String(e.file_count) : '—') + '</td>' +
        '<td>' + esc(nvl(e.detail)) + '</td>';

      tbody.appendChild(tr);
    });

    show(section);
  }

  // 8. Bookmarks & Annotations
  function renderBookmarks(ba) {
    var section = $id('section-bookmarks');
    var grid = $id('ri-bookmarks-grid');
    grid.innerHTML = '';

    ba = ba || {};
    var bookmarks = ba.bookmarks || [];
    var annotations = ba.annotations || [];

    if (bookmarks.length === 0 && annotations.length === 0) {
      // Don't show section if empty
      return;
    }

    // Bookmarks column
    var bmDiv = document.createElement('div');
    bmDiv.innerHTML = '<div class="ri-kv-label" style="margin-bottom:8px;">Bookmarks (' + bookmarks.length + ')</div>';
    var bmList = document.createElement('div');
    bmList.className = 'ri-bm-list';

    if (bookmarks.length === 0) {
      bmList.innerHTML = '<div class="ri-empty">None</div>';
    } else {
      bookmarks.forEach(function (b) {
        var item = document.createElement('div');
        item.className = 'ri-bm-item';
        item.innerHTML =
          '<div class="ri-bm-label">' + esc(b.label || b.bookmark_id || '') + '</div>' +
          '<div class="ri-bm-meta">' +
            '<span>' + esc(b.category || '') + '</span>' +
            (b.media_time_ms != null ? '<span>' + fmtMs(b.media_time_ms) + '</span>' : '') +
          '</div>' +
          (b.note ? '<div class="ri-bm-note">' + esc(b.note) + '</div>' : '');
        bmList.appendChild(item);
      });
    }
    bmDiv.appendChild(bmList);
    grid.appendChild(bmDiv);

    // Annotations column
    var annDiv = document.createElement('div');
    annDiv.innerHTML = '<div class="ri-kv-label" style="margin-bottom:8px;">Annotations (' + annotations.length + ')</div>';
    var annList = document.createElement('div');
    annList.className = 'ri-bm-list';

    if (annotations.length === 0) {
      annList.innerHTML = '<div class="ri-empty">None</div>';
    } else {
      annotations.forEach(function (a) {
        var sev = (a.severity || '').toLowerCase();
        var item = document.createElement('div');
        item.className = 'ri-bm-item';
        item.innerHTML =
          '<div class="ri-bm-label" style="display:flex;align-items:center;gap:8px;">' +
            esc(a.type || a.annotation_id || '') +
            '<span class="ri-ann-sev-badge sev-' + esc(sev) + '">' + esc(a.severity || '') + '</span>' +
          '</div>' +
          '<div class="ri-bm-meta">' +
            (a.media_time_ms != null ? '<span>' + fmtMs(a.media_time_ms) + '</span>' : '') +
          '</div>' +
          (a.text ? '<div class="ri-bm-note">' + esc(a.text) + '</div>' : '');
        annList.appendChild(item);
      });
    }
    annDiv.appendChild(annList);
    grid.appendChild(annDiv);

    show(section);
  }

  // ── Main render ──────────────────────────────────────────────────────────────

  function renderReport(report) {
    renderIdentity(report);
    renderAnomalies(report.anomalies || []);
    renderNextSteps(report.next_steps || []);
    renderChronology(report.chronology || {});
    renderPath(report.path || {});
    renderDiagnostics(report);
    renderArtifacts(report.artifact_availability || {});
    renderBookmarks(report.bookmarks_annotations || {});
  }

  // ── Fetch ────────────────────────────────────────────────────────────────────

  function loadReport(sessionId) {
    showLoading();
    var url = '/api/replay-inspection/' + encodeURIComponent(sessionId);

    fetch(url)
      .then(function (res) {
        if (!res.ok) {
          return res.text().then(function (body) {
            var msg = body || res.statusText || ('HTTP ' + res.status);
            try { var parsed = JSON.parse(body); msg = parsed.error || parsed.message || msg; } catch (_) {}
            throw new Error(msg);
          });
        }
        return res.json();
      })
      .then(function (data) {
        hideLoading();
        renderReport(data);
      })
      .catch(function (err) {
        hideLoading();
        showError(null, err.message || String(err));
      });
  }

  // ── Session form ─────────────────────────────────────────────────────────────

  window.RI = {
    submitSessionForm: function (e) {
      e.preventDefault();
      var val = ($id('ri-sid-input').value || '').trim();
      if (!val) return;
      window.location.href = '/replay-inspection?session_id=' + encodeURIComponent(val);
    }
  };

  // ── Boot ──────────────────────────────────────────────────────────────────────

  (function boot() {
    var sessionId = (RI_BOOT && RI_BOOT.session_id) ? RI_BOOT.session_id.trim() : '';

    if (!sessionId) {
      show($id('ri-session-form-container'));
      // Pre-focus the input
      var inp = $id('ri-sid-input');
      if (inp) setTimeout(function () { inp.focus(); }, 60);
      return;
    }

    loadReport(sessionId);
  })();

})();
