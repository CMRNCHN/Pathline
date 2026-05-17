import { ReplayTimeline } from './replay_timeline.js';

export const ReplayModule = {
    async loadReplay(sessionId) {
        console.log(`[replay] Loading session ${sessionId}`);
        this.captureLiveSnapshot();
        this.setLoadingPhase('timeline', sessionId);
        window.EventBus.emit(window.REPLAY_EVENTS.REPLAY_LOADING, { sessionId });

        try {
            const [timeline, waveform, alignment] = await Promise.all([
                window.API.getReplayTimeline(sessionId),
                window.API.getReplayWaveform(sessionId),
                window.API.getReplayAlignment(sessionId),
            ]);
            window.AppState.review.selectedCallId = sessionId;
            window.AppState.review.timeline = timeline.events || [];
            window.AppState.review.waveform = waveform;
            window.AppState.review.mediaUrl = waveform.media_url || null;
            window.AppState.review.alignment = alignment.items || [];
            window.AppState.review.error = '';
            window.AppState.review.summary = this.buildSummary(sessionId, timeline, waveform, alignment.items || []);

            await ReplayTimeline.init(sessionId);
            this.setLoadingPhase('state', sessionId);
            await ReplayTimeline.seek(ReplayTimeline.totalEvents, ReplayTimeline.totalEvents);

            window.AppState.mode = 'replay';
            this.setLoadingPhase('ready', sessionId);
            window.EventBus.emit(window.REPLAY_EVENTS.REPLAY_LOADED, { sessionId });
        } catch (error) {
            console.error(`[replay] Failed to load replay:`, error);
            window.AppState.review.error = error.message || String(error);
            this.setLoadingPhase('failed', sessionId);
            window.EventBus.emit(window.REPLAY_EVENTS.REPLAY_FAILED, { sessionId, error });
            if (typeof window.renderOperatorConsole === 'function') {
                window.renderOperatorConsole();
            }
        }
    },

    hydrate(payload) {
        const state = payload.state;
        const cursor = payload.cursor || null;
        window.AppState.replayState = state;
        window.AppState.review.cursor = cursor;
        window.AppState.review.selectedCursorOffset = cursor ? cursor.event_index + 1 : 0;
        window.AppState.review.selectedCursorEventId = cursor ? cursor.event_id : null;
        window.AppState.review.transcript = state.transcripts || [];
        window.AppState.review.summary = {
            ...(window.AppState.review.summary || {}),
            callStatus: state.call_status || 'unknown',
            nodeCount: Object.keys(state.nodes || {}).length,
            edgeCount: (state.edges || []).length,
            transcriptCount: (state.transcripts || []).length,
            dtmfCount: (state.dtmf_history || []).length,
            reconstructedFromSnapshot: !!(state.metrics || {}).reconstructed_from_snapshot,
            currentOffset: (state.metrics || {}).target_offset || 0,
            totalEvents: (state.metrics || {}).total_event_count || (state.events || []).length,
        };

        const badge = document.getElementById('replay-metadata-badge');
        if (badge) {
            badge.classList.remove('is-hidden');
            const sourceType = document.getElementById('replay-source-type');
            const offsetEl = document.getElementById('replay-snapshot-offset');
            const mediaRefEl = document.getElementById('replay-media-reference');
            
            if (sourceType && state.metrics) {
                sourceType.textContent = state.metrics.reconstructed_from_snapshot ? 'Snapshot' : 'Full';
            }
            if (offsetEl && state.metrics) {
                offsetEl.textContent = state.metrics.target_offset !== undefined ? state.metrics.target_offset : (state.metrics.snapshot_offset || 0);
            }
            if (mediaRefEl) {
                mediaRefEl.textContent = state.recording_reference || 'No Media';
                mediaRefEl.title = state.recording_reference || 'No media recording associated with this session';
            }
        }

        if (state.nodes || state.edges) {
            window.AppState.latestGraph = {
                nodes: state.nodes,
                edges: state.edges
            };
            if (window.renderGraph) {
                window.renderGraph(window.AppState.latestGraph);
            }
        }

        if (state.metrics) {
            window.AppState.runtimeMetrics = state.metrics;
            if (window.renderMetrics) {
                window.renderMetrics(state.metrics);
            }
        }

        if (window.updateStatusUI) {
            window.updateStatusUI({
                is_running: false,
                session_ended: state.call_status === 'completed',
                call_status: state.call_status,
                session_id: state.session_id
            });
        }

        if (typeof window.renderOperatorConsole === 'function') {
            window.renderOperatorConsole();
        }
    },

    exitReplay() {
        window.AppState.mode = 'live';
        window.AppState.replayState = null;
        window.AppState.review.loadingPhase = 'idle';
        window.AppState.review.error = '';
        window.AppState.review.cursor = null;
        window.AppState.review.mediaUrl = null;
        window.AppState.review.selectedCursorEventId = null;
        window.AppState.review.selectedCursorOffset = 0;
        this.restoreLiveSnapshot();
        console.log('[replay] Exited replay mode');
        if (typeof window.renderOperatorConsole === 'function') {
            window.renderOperatorConsole();
        }
    },

    async refreshReplayList() {
        const selector = document.getElementById('replay-session-selector');
        if (!selector) return;
        this.setLoadingPhase('list', null);

        try {
            const replays = await window.API.listReplays();
            window.AppState.review.availableCalls = replays;
            
            selector.innerHTML = '<option value="">Select a session to replay...</option>';
            
            replays.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.session_id;
                const dateStr = r.created_at ? new Date(r.created_at * 1000).toLocaleString() : 'Unknown date';
                opt.textContent = `${dateStr} - ${r.session_id} (${r.event_count} events)`;
                selector.appendChild(opt);
            });
            this.setLoadingPhase(replays.length ? 'idle' : 'empty', null);
            if (typeof window.renderOperatorConsole === 'function') {
                window.renderOperatorConsole();
            }
        } catch (error) {
            console.error('[replay] Failed to refresh replay list:', error);
            window.AppState.review.availableCalls = [];
            window.AppState.review.error = error.message || String(error);
            this.setLoadingPhase('failed', null);
            if (typeof window.renderOperatorConsole === 'function') {
                window.renderOperatorConsole();
            }
        }
    },

    setLoadingPhase(phase, sessionId) {
        window.AppState.review.loadingPhase = phase;
        if (sessionId) {
            window.AppState.review.selectedCallId = sessionId;
        }
    },

    buildSummary(sessionId, timeline, waveform, alignment) {
        return {
            sessionId,
            totalEvents: timeline.total_events || 0,
            eventTypes: timeline.event_types || [],
            nodeCount: 0,
            edgeCount: 0,
            transcriptCount: 0,
            dtmfCount: 0,
            waveformStatus: (waveform || {}).status || 'missing',
            waveformReason: (waveform || {}).reason || '',
            mediaAvailable: !!(waveform || {}).media_available,
            alignmentCount: alignment.length,
        };
    },

    captureLiveSnapshot() {
        if (window.AppState.review.liveRestoreSnapshot) return;
        window.AppState.review.liveRestoreSnapshot = {
            latestGraph: window.AppState.latestGraph,
            runtimeMetrics: window.AppState.runtimeMetrics,
        };
    },

    restoreLiveSnapshot() {
        const snapshot = window.AppState.review.liveRestoreSnapshot;
        if (!snapshot) return;
        window.AppState.latestGraph = snapshot.latestGraph || {};
        window.AppState.runtimeMetrics = snapshot.runtimeMetrics || null;
        window.AppState.review.liveRestoreSnapshot = null;
    },
};

document.addEventListener('DOMContentLoaded', () => {
    window.EventBus.on(window.REPLAY_EVENTS.REPLAY_STATE_LOADED, (event) => {
        ReplayModule.hydrate(event.payload);
    });
    window.EventBus.on(window.REPLAY_EVENTS.REPLAY_CURSOR_CHANGED, (event) => {
        const audio = document.getElementById('replay-media-player');
        const mediaTimeMs = (event.payload && event.payload.cursor)
            ? Number(event.payload.cursor.media_time_ms) || 0
            : 0;
        if (audio && audio.src) {
            const targetSeconds = mediaTimeMs / 1000;
            if (Number.isFinite(targetSeconds) && Math.abs(audio.currentTime - targetSeconds) > 0.25) {
                audio.currentTime = targetSeconds;
            }
        }
    });

    const selector = document.getElementById('replay-session-selector');
    if (selector) {
        selector.addEventListener('change', (e) => {
            const sessionId = e.target.value;
            if (sessionId) {
                ReplayModule.loadReplay(sessionId);
            } else {
                ReplayModule.exitReplay();
            }
        });
        
        // Initial load
        ReplayModule.refreshReplayList();
    }

    const refreshBtn = document.getElementById('btn-refresh-replays');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => ReplayModule.refreshReplayList());
    }
});
