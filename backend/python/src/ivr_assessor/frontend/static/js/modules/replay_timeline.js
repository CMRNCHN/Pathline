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
    
    async init(sessionId) {
        this.sessionId = sessionId;
        try {
            const timeline = await API.get(`/replays/${sessionId}/timeline`);
            this.totalEvents = timeline.total_events;
            this.snapshots = timeline.snapshots || [];
            this.cursor = this.totalEvents; // Default to end
            
            this.renderControls();
            this.updateDisplay();
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

    async seek(position, oldPosition = null) {
        this.cursor = Math.max(0, Math.min(this.totalEvents, position));
        this.updateDisplay();
        
        try {
            // Fetch cursor metadata (includes media_time_ms)
            const cursorData = await API.get(`/replays/${this.sessionId}/cursor/${this.cursor}`);
            this.updateSyncDisplay(cursorData);

            // Fetch state for hydration
            const state = await API.get(`/replays/${this.sessionId}/state/${this.cursor}`);
            
            // Dispatch event for hydration
            EventBus.emit('replay:state_loaded', state);
            
            if (oldPosition !== null) {
                const diff = await API.get(`/replays/${this.sessionId}/diff/${oldPosition}/${this.cursor}`);
                this.visualizeDiff(diff);
            }
        } catch (err) {
            console.error(`Failed to seek to ${this.cursor}:`, err);
        }
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
