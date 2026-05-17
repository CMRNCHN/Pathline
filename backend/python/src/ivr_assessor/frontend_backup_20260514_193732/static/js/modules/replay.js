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
        
        // UI Loading state
        const header = document.getElementById('review-header');
        if (header) header.style.opacity = '0.5';
        
        try {
            // Initialize timeline first, it will handle default end-of-run state
            await ReplayTimeline.init(sessionId);
            
            AppState.mode = 'replay';
            EventBus.emit(REPLAY_EVENTS.REPLAY_LOADED, { sessionId });
        } catch (error) {
            console.error(`[replay] Failed to load replay:`, error);
            EventBus.emit(REPLAY_EVENTS.REPLAY_FAILED, { sessionId, error });
        } finally {
            if (header) header.style.opacity = '1';
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

        // 5. Load Bookmarks & Annotations
        this.refreshBookmarks(state.session_id);
        this.refreshAnnotations(state.session_id);
    },

    async refreshBookmarks(sessionId) {
        const list = document.getElementById('review-bookmarks-list');
        if (!list) return;
        try {
            const bookmarks = await API.get(`/api/replays/${sessionId}/bookmarks`);
            list.innerHTML = bookmarks.length ? '' : '<div class="p-4 text-muted">No bookmarks yet.</div>';
            bookmarks.forEach(b => {
                const item = document.createElement('div');
                item.className = 'review-item clickable';
                item.innerHTML = `
                    <div class="item-meta">
                        <span class="badge tone-accent">${b.category}</span>
                        <span class="time">${(b.media_time_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <div class="item-label">${b.label}</div>
                    <div class="item-note text-small">${b.note}</div>
                `;
                item.onclick = () => ReplayTimeline.seekToMediaTime(b.media_time_ms);
                list.appendChild(item);
            });
        } catch (e) { console.error('Failed to load bookmarks', e); }
    },

    async refreshAnnotations(sessionId) {
        const list = document.getElementById('review-annotations-list');
        if (!list) return;
        try {
            const annotations = await API.get(`/api/replays/${sessionId}/annotations`);
            list.innerHTML = annotations.length ? '' : '<div class="p-4 text-muted">No annotations yet.</div>';
            annotations.forEach(a => {
                const item = document.createElement('div');
                item.className = 'review-item clickable';
                const tone = a.severity === 'CRITICAL' ? 'tone-err' : (a.severity === 'WARNING' ? 'tone-warn' : 'tone-info');
                item.innerHTML = `
                    <div class="item-meta">
                        <span class="badge ${tone}">${a.severity}</span>
                        <span class="time">${(a.media_time_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <div class="item-text">${a.text}</div>
                    <div class="item-type text-small">${a.type}</div>
                `;
                item.onclick = () => ReplayTimeline.seekToMediaTime(a.media_time_ms);
                list.appendChild(item);
            });
        } catch (e) { console.error('Failed to load annotations', e); }
    },

    async searchTimeline(sessionId, query) {
        if (!query) return;
        try {
            const results = await API.get(`/api/replays/${sessionId}/search?query=${encodeURIComponent(query)}`);
            // Highlight results in transcript list or show search results panel
            // For now, let's just log and maybe we can find a way to jump to first result
            console.log('[replay] Search results:', results);
            if (results.length > 0) {
                ReplayTimeline.seek(results[0].index);
            }
        } catch (e) { console.error('Search failed', e); }
    },

    async compareSessions(leftId, rightId) {
        const summaryEl = document.getElementById('review-compare-summary');
        if (!summaryEl) return;
        try {
            summaryEl.innerHTML = '<div class="p-4 text-muted">Analyzing regression deltas...</div>';
            const summary = await API.get(`/api/replays/compare?left=${leftId}&right=${rightId}`);
            summaryEl.innerHTML = `
                <div class="compare-card" style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Event Delta:</span>
                        <span style="font-weight: 600; color: var(--${summary.event_count_delta >= 0 ? 'success' : 'danger'});">${summary.event_count_delta}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Duration Delta:</span>
                        <span style="font-weight: 600;">${(summary.duration_delta_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Path Divergence Index:</span>
                        <span style="font-weight: 600;">${summary.path_divergence_index === -1 ? 'None' : summary.path_divergence_index}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>New Nodes:</span>
                        <span style="font-weight: 600; color: var(--success);">${summary.node_delta_summary.added}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Avg Confidence Δ:</span>
                        <span style="font-weight: 600; color: var(--accent);">${(summary.confidence_delta_summary.right_avg - summary.confidence_delta_summary.left_avg).toFixed(2)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Failure Δ:</span>
                        <span style="font-weight: 600; color: var(--${summary.failure_event_delta > 0 ? 'danger' : 'success'});">${summary.failure_event_delta}</span>
                    </div>
                </div>
            `;
        } catch (e) { 
            console.error('Comparison failed', e);
            summaryEl.innerHTML = `<div class="p-4 tone-error">Comparison failed: ${e.message}</div>`;
        }
    },

    exitReplay() {
        if (ReplayTimeline.audio) {
            ReplayTimeline.audio.stop();
        }
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

    // Listen for workspace changes to refresh list
    EventBus.on('WORKSPACE_CHANGED', (event) => {
        if (event.payload && event.payload.workspaceId === 'review') {
            ReplayModule.refreshReplayList();
        }
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

    const searchBtn = document.getElementById('btn-review-search');
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const query = document.getElementById('review-search-input').value;
            if (ReplayTimeline.sessionId) {
                ReplayModule.searchTimeline(ReplayTimeline.sessionId, query);
            }
        });
    }

    const addBookmarkBtn = document.getElementById('btn-add-bookmark');
    if (addBookmarkBtn) {
        addBookmarkBtn.addEventListener('click', async () => {
            if (!ReplayTimeline.sessionId) return;
            const label = prompt('Bookmark Label:');
            if (!label) return;
            
            // Get current cursor info
            const cursor = await API.get(`/api/replays/${ReplayTimeline.sessionId}/cursor/${ReplayTimeline.cursor}`);
            
            await API.post(`/api/replays/${ReplayTimeline.sessionId}/bookmarks`, {
                event_id: cursor.event_id,
                event_index: cursor.event_index,
                media_time_ms: cursor.media_time_ms,
                label: label,
                category: 'OPERATOR_NOTE',
                note: ''
            });
            ReplayModule.refreshBookmarks(ReplayTimeline.sessionId);
        });
    }

    const addAnnotationBtn = document.getElementById('btn-add-annotation');
    if (addAnnotationBtn) {
        addAnnotationBtn.addEventListener('click', async () => {
            if (!ReplayTimeline.sessionId) return;
            const text = prompt('Annotation Text:');
            if (!text) return;
            
            const cursor = await API.get(`/api/replays/${ReplayTimeline.sessionId}/cursor/${ReplayTimeline.cursor}`);
            
            await API.post(`/api/replays/${ReplayTimeline.sessionId}/annotations`, {
                event_id: cursor.event_id,
                event_index: cursor.event_index,
                media_time_ms: cursor.media_time_ms,
                type: 'NOTE',
                text: text,
                severity: 'INFO'
            });
            ReplayModule.refreshAnnotations(ReplayTimeline.sessionId);
        });
    }

    const compareBtn = document.getElementById('btn-compare-sessions');
    if (compareBtn) {
        compareBtn.addEventListener('click', () => {
            const leftId = ReplayTimeline.sessionId;
            const selector = document.getElementById('replay-session-selector');
            const rightId = selector.value;
            if (leftId && rightId && leftId !== rightId) {
                ReplayModule.compareSessions(leftId, rightId);
            } else {
                alert('Select a different session to compare.');
            }
        });
    }
});
