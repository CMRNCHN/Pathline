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
    currentTranscripts: [], // Store transcripts for sync

    async loadReplay(sessionId) {
        console.log(`[replay] Loading session ${sessionId}`);

        // Show loading skeletons
        this.showLoadingSkeletons();
        this.updateLoadingProgress('Loading session...', 0);

        EventBus.emit(REPLAY_EVENTS.REPLAY_LOADING, { sessionId });

        try {
            this.updateLoadingProgress('Initializing timeline...', 25);
            // Initialize timeline first, it will handle default end-of-run state
            await ReplayTimeline.init(sessionId);

            this.updateLoadingProgress('Hydrating state...', 50);
            // ReplayTimeline.init calls ReplayTimeline.seek which emits 'replay:state_loaded'
            // We listen for that to hydrate

            this.updateLoadingProgress('Rendering interface...', 75);
            AppState.mode = 'replay';

            this.hideLoadingProgress();
            EventBus.emit(REPLAY_EVENTS.REPLAY_LOADED, { sessionId });
        } catch (error) {
            console.error(`[replay] Failed to load replay:`, error);
            this.hideLoadingProgress();
            EventBus.emit(REPLAY_EVENTS.REPLAY_FAILED, { sessionId, error });
        }
    },

    showLoadingSkeletons() {
        // Show skeleton for graph
        const graphContainer = document.getElementById('graph-container') || document.querySelector('[data-graph-root]');
        if (graphContainer) {
            graphContainer.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 300px;
                    padding: 20px;
                    background: rgba(128, 148, 182, 0.05);
                    border-radius: 10px;
                ">
                    <div style="
                        width: 100%;
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                    ">
                        <div style="
                            height: 20px;
                            background: linear-gradient(90deg, rgba(128, 148, 182, 0.2), rgba(128, 148, 182, 0.05));
                            border-radius: 4px;
                            animation: pulse 1.5s ease-in-out infinite;
                        "></div>
                        <div style="
                            height: 20px;
                            width: 80%;
                            background: linear-gradient(90deg, rgba(128, 148, 182, 0.2), rgba(128, 148, 182, 0.05));
                            border-radius: 4px;
                            animation: pulse 1.5s ease-in-out infinite 0.3s;
                        "></div>
                    </div>
                </div>
            `;
        }

        // Show skeleton for transcripts
        const transcriptContainer = document.getElementById('review-transcript-list');
        if (transcriptContainer) {
            transcriptContainer.innerHTML = `
                <div style="
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                ">
                    ${Array(3).fill().map(() => `
                        <div style="
                            height: 40px;
                            background: linear-gradient(90deg, rgba(128, 148, 182, 0.2), rgba(128, 148, 182, 0.05));
                            border-radius: 6px;
                            animation: pulse 1.5s ease-in-out infinite;
                        "></div>
                    `).join('')}
                </div>
            `;
        }
    },

    updateLoadingProgress(message, percent) {
        let progressBar = document.getElementById('replay-loading-progress');
        if (!progressBar) {
            const container = document.body;
            progressBar = document.createElement('div');
            progressBar.id = 'replay-loading-progress';
            progressBar.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: rgba(0, 0, 0, 0.7);
                padding: 16px;
                text-align: center;
                color: var(--text-1);
                font-size: 12px;
                z-index: 1000;
                animation: slideDown 200ms ease-out;
            `;
            container.appendChild(progressBar);
        }

        progressBar.innerHTML = `
            <div style="margin-bottom: 8px;">${this._escapeHtml(message)}</div>
            <div style="
                height: 3px;
                background: rgba(128, 148, 182, 0.2);
                border-radius: 2px;
                overflow: hidden;
            ">
                <div style="
                    height: 100%;
                    width: ${percent}%;
                    background: var(--accent);
                    transition: width 200ms ease-out;
                "></div>
            </div>
        `;
    },

    hideLoadingProgress() {
        const progressBar = document.getElementById('replay-loading-progress');
        if (progressBar) {
            progressBar.style.animation = 'slideUp 200ms ease-in';
            setTimeout(() => {
                if (progressBar.parentNode) {
                    progressBar.parentNode.removeChild(progressBar);
                }
            }, 200);
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

        // 1. Rebuild Graph (with empty state handling)
        if (state.nodes || state.edges) {
            AppState.latestGraph = {
                nodes: state.nodes || [],
                edges: state.edges || []
            };
            // Force graph render if renderGraph exists (usually in main.js)
            if (window.renderGraph) {
                window.renderGraph(AppState.latestGraph);
            }
        } else {
            // Empty graph state
            this.renderEmptyState('graph');
        }

        // 2. Rebuild Transcript Timeline (with clickable sync and empty state)
        if (state.transcripts && state.transcripts.length > 0) {
            this.currentTranscripts = state.transcripts;
            this.renderReplayTranscripts(state.transcripts);
            // Highlight the most recent transcript at current cursor position
            const mostRecentIndex = state.transcripts.length - 1;
            this.highlightCurrentTranscript(mostRecentIndex);
        } else {
            this.renderEmptyState('transcripts');
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

    renderReplayTranscripts(transcripts) {
        const container = document.getElementById('review-transcript-list');
        if (!container) return;

        // Clear existing content
        container.innerHTML = '';

        // Render each transcript item as clickable
        transcripts.forEach((transcript, index) => {
            const row = document.createElement('div');
            row.className = 'transcript-replay-row';
            row.dataset.transcriptIndex = index;
            row.style.cursor = 'pointer';
            row.style.padding = '8px 12px';
            row.style.borderLeft = '3px solid transparent';
            row.style.transition = 'all 100ms ease-in';
            row.innerHTML = `
                <div class="review-row-meta">
                    <span class="review-speaker">${transcript.speaker === 'system' ? 'IVR' : 'User'}</span>
                </div>
                <div class="review-row-content">
                    <div class="review-text">${this._escapeHtml(transcript.text)}</div>
                </div>
            `;

            // Click to seek to a cursor position where this transcript exists
            row.addEventListener('click', () => {
                // Estimate cursor position: distribute transcript indices across timeline
                const estimatedCursor = Math.floor((index / transcripts.length) * ReplayTimeline.totalEvents);
                ReplayTimeline.seekDebounced(estimatedCursor, ReplayTimeline.cursor);
            });

            // Hover effect
            row.addEventListener('mouseenter', () => {
                row.style.backgroundColor = 'rgba(128, 148, 182, 0.1)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.backgroundColor = 'transparent';
            });

            container.appendChild(row);
        });
    },

    highlightCurrentTranscript(cursorIndex) {
        // Highlight the transcript item matching the current timeline cursor
        const rows = document.querySelectorAll('.transcript-replay-row');
        rows.forEach(row => {
            const index = parseInt(row.dataset.transcriptIndex, 10);
            if (index === cursorIndex) {
                row.style.borderLeftColor = 'var(--accent)';
                row.style.backgroundColor = 'rgba(128, 148, 182, 0.15)';
                row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                row.style.borderLeftColor = 'transparent';
                row.style.backgroundColor = 'transparent';
            }
        });
    },

    renderEmptyState(type) {
        let container, title, description;

        if (type === 'transcripts') {
            container = document.getElementById('review-transcript-list');
            title = 'No transcripts recorded';
            description = 'This session has no transcript data available.';
        } else if (type === 'graph') {
            container = document.getElementById('graph-container') || document.querySelector('[data-graph-root]');
            title = 'No IVR states discovered';
            description = 'This session recorded no state transitions.';
        } else if (type === 'events') {
            container = document.querySelector('[data-timeline-root]');
            title = 'No events recorded';
            description = 'This session has no operational events.';
        }

        if (!container) return;

        container.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 120px;
                padding: 32px;
                background: rgba(128, 148, 182, 0.05);
                border: 1px dashed rgba(128, 148, 182, 0.2);
                border-radius: 10px;
                color: var(--text-3);
            ">
                <div style="font-size: 32px; margin-bottom: 12px;">📭</div>
                <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px;">${this._escapeHtml(title)}</div>
                <div style="font-size: 12px; text-align: center; max-width: 200px;">${this._escapeHtml(description)}</div>
            </div>
        `;
    },

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
