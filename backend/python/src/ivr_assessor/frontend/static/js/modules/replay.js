/**
 * Replay workspace foundation.
 * Handles fetching replay data and hydrating the frontend.
 */
import { API } from '../common/api.js';
import { EventBus } from '../common/events.js';
import { REPLAY_EVENTS } from '../common/events.js';
import { AppState } from '../common/state.js';
import { ReplayTimeline } from './replay_timeline.js';

export const ReplayModule = {
    async loadReplay(sessionId) {
        console.log(`[replay] Loading session ${sessionId}`);
        EventBus.emit(REPLAY_EVENTS.REPLAY_LOADING, { sessionId });
        
        try {
            // Initialize timeline first, it will handle default end-of-run state
            await ReplayTimeline.init(sessionId);
            
            // ReplayTimeline.init calls ReplayTimeline.seek which emits 'replay:state_loaded'
            // We listen for that to hydrate
            
            AppState.mode = 'replay';
            EventBus.emit(REPLAY_EVENTS.REPLAY_LOADED, { sessionId });
        } catch (error) {
            console.error(`[replay] Failed to load replay:`, error);
            EventBus.emit(REPLAY_EVENTS.REPLAY_FAILED, { sessionId, error });
        }
    },

    hydrate(state) {
        // ... (rest of the hydrate function unchanged)
        // 0. Update Replay Metadata
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
                // Re-using offset badge to show current target offset in Slice 6
                offsetEl.textContent = state.metrics.target_offset !== undefined ? state.metrics.target_offset : (state.metrics.snapshot_offset || 0);
            }
            if (mediaRefEl) {
                mediaRefEl.textContent = state.recording_reference || 'No Media';
                mediaRefEl.title = state.recording_reference || 'No media recording associated with this session';
            }
        }

        // 1. Rebuild Graph
        if (state.nodes || state.edges) {
            AppState.latestGraph = {
                nodes: state.nodes,
                edges: state.edges
            };
            // Force graph render if renderGraph exists (usually in main.js)
            if (window.renderGraph) {
                window.renderGraph(AppState.latestGraph);
            }
        }

        // 2. Rebuild Transcript Timeline
        if (state.transcripts && window.updateTimeline) {
            // Convert replay transcripts to the format expected by UI
            // Assuming window.updateTimeline handles adding items to the list
            // We might need to clear it first or pass a full list
            const formattedLogs = state.transcripts.map(t => {
                const prefix = t.speaker === 'system' ? '[transcript]' : '[user]';
                return `${prefix} ${t.text}`;
            });
            
            // In live mode, main.js usually appends from STATE.logs.
            // For replay, we might need a way to swap the log source.
            AppState.legacyLogs = formattedLogs;
            if (window.renderLogs) {
                window.renderLogs(formattedLogs);
            }
        }

        // 3. Rebuild Operational Metrics
        if (state.metrics) {
            AppState.runtimeMetrics = state.metrics;
            if (window.renderMetrics) {
                window.renderMetrics(state.metrics);
            }
        }

        // 4. Update Status Cards
        if (window.updateStatusUI) {
            window.updateStatusUI({
                is_running: false,
                session_ended: state.call_status === 'completed',
                call_status: state.call_status,
                session_id: state.session_id
            });
        }
    },

    exitReplay() {
        AppState.mode = 'live';
        AppState.replayState = null;
        console.log('[replay] Exited replay mode');
        // main.js will resume live polling updates naturally if it checks AppState.mode
    },

    async refreshReplayList() {
        const selector = document.getElementById('replay-session-selector');
        if (!selector) return;

        try {
            const replays = await API.get('/api/replays');
            
            // Keep the first option
            selector.innerHTML = '<option value="">Select a session to replay...</option>';
            
            replays.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.session_id;
                const dateStr = r.created_at ? new Date(r.created_at * 1000).toLocaleString() : 'Unknown date';
                opt.textContent = `${dateStr} - ${r.session_id} (${r.event_count} events)`;
                selector.appendChild(opt);
            });
        } catch (error) {
            console.error('[replay] Failed to refresh replay list:', error);
        }
    }
};

// Hook into the UI if needed
document.addEventListener('DOMContentLoaded', () => {
    // Listen for timeline state changes
    EventBus.on('replay:state_loaded', (state) => {
        ReplayModule.hydrate(state);
    });

    // Initialize replay selector UI if present
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
