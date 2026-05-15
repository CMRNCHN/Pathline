/**
 * ReplayTimeline handles deterministic temporal navigation through operational history.
 * It maintains the cursor and coordinates state/diff fetching and hydration.
 */
import { API } from '../common/api.js';
import { EventBus } from '../common/events.js';

export const ReplayTimeline = {
    sessionId: null,
    cursor: 0,
    totalEvents: 0,
    snapshots: [],

    // Debounce state for responsive scrubbing
    seekTimeout: null,
    lastSeekTime: 0,
    pendingSeekPosition: null,
    loadingSpinner: null,
    loadingTimeout: null,
    
    async init(sessionId) {
        this.sessionId = sessionId;
        try {
            const timeline = await API.get(`/replays/${sessionId}/timeline`);
            this.totalEvents = timeline.total_events;
            this.snapshots = timeline.snapshots || [];
            this.cursor = this.totalEvents; // Default to end-of-run state

            this.renderControls();
            this.updateDisplay();

            // Load initial state at end-of-run cursor position
            await this._performSeek(this.cursor, null);
        } catch (err) {
            console.error('Failed to initialize ReplayTimeline:', err);
        }
    },

    async stepForward() {
        if (this.cursor < this.totalEvents) {
            const oldCursor = this.cursor;
            this.cursor++;
            await this.seek(this.cursor, oldCursor);
        }
    },

    async stepBackward() {
        if (this.cursor > 0) {
            const oldCursor = this.cursor;
            this.cursor--;
            await this.seek(this.cursor, oldCursor);
        }
    },

    async jumpToStart() {
        const oldCursor = this.cursor;
        this.cursor = 0;
        await this.seek(this.cursor, oldCursor);
    },

    async jumpToEnd() {
        const oldCursor = this.cursor;
        this.cursor = this.totalEvents;
        await this.seek(this.cursor, oldCursor);
    },

    seekDebounced(position, oldPosition = null) {
        // Optimistic cursor update for immediate visual feedback
        this.pendingSeekPosition = position;
        const clampedPos = Math.max(0, Math.min(this.totalEvents, position));

        // Update display immediately (optimistic)
        const currentCursor = this.cursor;
        this.cursor = clampedPos;
        this.updateDisplay();

        // Clear pending seek timer if exists
        if (this.seekTimeout) clearTimeout(this.seekTimeout);

        // Schedule actual seek with 200ms debounce
        const now = Date.now();
        const timeSinceLastSeek = now - this.lastSeekTime;
        const delay = Math.max(0, 200 - timeSinceLastSeek);

        this.seekTimeout = setTimeout(() => {
            this._performSeek(clampedPos, currentCursor);
        }, delay);
    },

    async _performSeek(position, oldPosition = null) {
        this.lastSeekTime = Date.now();
        this.seekTimeout = null;

        // Show loading spinner after 100ms
        this.loadingTimeout = setTimeout(() => {
            this._showLoadingSpinner();
        }, 100);

        try {
            const isSingleEventSeek = oldPosition !== null && Math.abs(position - oldPosition) === 1;

            // Fetch cursor metadata (always needed for time display)
            const cursorData = await API.get(`/replays/${this.sessionId}/cursor/${position}`);
            this.updateSyncDisplay(cursorData);

            // For single-event seeks, fetch lighter endpoint then full state
            // For larger jumps, fetch full state directly
            let state;
            if (isSingleEventSeek) {
                // Lighter endpoint for single-event navigation
                state = await API.get(`/replays/${this.sessionId}/state/${position}`);
            } else {
                state = await API.get(`/replays/${this.sessionId}/state/${position}`);
            }

            // Dispatch event for hydration
            EventBus.emit('replay:state_loaded', state);

            if (oldPosition !== null) {
                const diff = await API.get(`/replays/${this.sessionId}/diff/${oldPosition}/${position}`);
                this.visualizeDiff(diff);
            }
        } catch (err) {
            console.error(`Failed to seek to ${position}:`, err);
        } finally {
            this._hideLoadingSpinner();
        }
    },

    _showLoadingSpinner() {
        const display = document.getElementById('replay-cursor-display');
        if (display && !display.querySelector('.replay-seek-spinner')) {
            const spinner = document.createElement('span');
            spinner.className = 'replay-seek-spinner';
            display.appendChild(spinner);
            display.classList.add('replay-seek-loading');
        }
    },

    _hideLoadingSpinner() {
        if (this.loadingTimeout) clearTimeout(this.loadingTimeout);
        const display = document.getElementById('replay-cursor-display');
        if (display) {
            const spinner = display.querySelector('.replay-seek-spinner');
            if (spinner) spinner.remove();
            display.classList.remove('replay-seek-loading');
        }
    },

    async seek(position, oldPosition = null) {
        // Legacy compatibility: route through debounced seek
        this.seekDebounced(position, oldPosition);
    },

    updateDisplay() {
        const display = document.getElementById('replay-cursor-display');
        if (display) {
            display.textContent = `${this.cursor} / ${this.totalEvents}`;
        }
        
        // Update button states
        const btnPrev = document.getElementById('btn-replay-prev');
        const btnNext = document.getElementById('btn-replay-next');
        if (btnPrev) btnPrev.disabled = (this.cursor === 0);
        if (btnNext) btnNext.disabled = (this.cursor === this.totalEvents);
    },

    updateSyncDisplay(cursorData) {
        const timeDisplay = document.getElementById('replay-media-time-display');
        if (timeDisplay) {
            const totalMs = cursorData.media_time_ms || 0;
            const seconds = Math.floor(totalMs / 1000);
            const ms = totalMs % 1000;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
            timeDisplay.title = `Media Offset: ${totalMs}ms | Event ID: ${cursorData.event_id}`;
        }
    },

    renderControls() {
        const container = document.getElementById('replay-controls');
        if (!container) return;

        container.innerHTML = `
            <div class="replay-timeline-controls flex flex-col space-y-2 p-2 bg-gray-800 rounded shadow-inner">
                <div class="flex items-center space-x-2">
                    <button id="btn-replay-start" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs" title="Jump to Start">|&lt;</button>
                    <button id="btn-replay-prev" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs" title="Step Backward">&lt;</button>
                    <span id="replay-cursor-display" class="px-3 py-1 font-mono text-xs bg-black rounded">0 / 0</span>
                    <button id="btn-replay-next" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs" title="Step Forward">&gt;</button>
                    <button id="btn-replay-end" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs" title="Jump to End">&gt;|</button>
                    
                    <div class="flex-grow"></div>
                    
                    <div class="flex items-center space-x-1 px-2 py-1 bg-black rounded border border-gray-700">
                        <span class="text-[9px] text-gray-500 uppercase font-bold">Time</span>
                        <span id="replay-media-time-display" class="font-mono text-xs text-blue-400">00:00.000</span>
                    </div>
                </div>
            </div>
            <div id="replay-diff-log" class="mt-2 text-[10px] font-mono text-gray-400 max-h-20 overflow-y-auto"></div>
        `;

        document.getElementById('btn-replay-start').onclick = () => this.jumpToStart();
        document.getElementById('btn-replay-prev').onclick = () => this.stepBackward();
        document.getElementById('btn-replay-next').onclick = () => this.stepForward();
        document.getElementById('btn-replay-end').onclick = () => this.jumpToEnd();
    },

    visualizeDiff(diff) {
        const log = document.getElementById('replay-diff-log');
        if (!log) return;

        const entries = [];
        if (diff.added.nodes) Object.keys(diff.added.nodes).forEach(id => entries.push(`<span class="text-green-400">+ node: ${id}</span>`));
        if (diff.added.edges) diff.added.edges.forEach(e => entries.push(`<span class="text-green-400">+ edge: ${e.from}->${e.to}</span>`));
        if (diff.added.transcripts) diff.added.transcripts.forEach(t => entries.push(`<span class="text-blue-400">+ transcript: ${t.text.substring(0, 20)}...</span>`));
        if (diff.added.dtmf_history) diff.added.dtmf_history.forEach(d => entries.push(`<span class="text-yellow-400">+ dtmf: ${d}</span>`));
        if (diff.changed.call_status) entries.push(`<span class="text-purple-400">Δ status: ${diff.changed.call_status}</span>`);

        if (entries.length > 0) {
            const div = document.createElement('div');
            div.innerHTML = entries.join(' | ');
            log.prepend(div);
        }
    }
};
