export const ReplayTimeline = {
    sessionId: null,
    cursor: 0,
    totalEvents: 0,
    snapshots: [],
    isSeeking: false,
    requestSerial: 0,
    latestAppliedRequest: 0,
    lastCommittedCursor: 0,
    
    async init(sessionId) {
        this.sessionId = sessionId;
        this.cursor = 0;
        this.totalEvents = 0;
        this.snapshots = [];
        this.isSeeking = false;
        this.requestSerial = 0;
        this.latestAppliedRequest = 0;
        try {
            const timeline = await window.API.getReplayTimeline(sessionId);
            this.totalEvents = timeline.total_events;
            this.snapshots = timeline.snapshots || [];
            this.cursor = this.totalEvents; // Default to end
            this.lastCommittedCursor = this.cursor;
            
            this.renderControls();
            this.updateDisplay();
        } catch (err) {
            console.error('Failed to initialize ReplayTimeline:', err);
            throw err;
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
        const target = Math.max(0, Math.min(this.totalEvents, Number(position) || 0));
        const previousCursor = oldPosition === null ? this.lastCommittedCursor : oldPosition;
        this.cursor = target;
        this.updateDisplay();
        this.isSeeking = true;
        const requestId = ++this.requestSerial;
        this.toggleBusy(true);

        try {
            const cursorData = await window.API.getReplayCursor(this.sessionId, target);
            const state = await window.API.getReplayState(this.sessionId, target);
            const diff = previousCursor !== null
                ? await window.API.getReplayDiff(this.sessionId, previousCursor, target)
                : { added: {}, changed: {}, metrics: {} };

            if (requestId < this.latestAppliedRequest) {
                return;
            }
            this.latestAppliedRequest = requestId;
            this.lastCommittedCursor = target;
            this.updateSyncDisplay(cursorData);
            window.EventBus.emit(window.REPLAY_EVENTS.REPLAY_STATE_LOADED, {
                state,
                cursor: cursorData,
                diff,
                sessionId: this.sessionId,
            });
            window.EventBus.emit(window.REPLAY_EVENTS.REPLAY_CURSOR_CHANGED, { cursor: cursorData, sessionId: this.sessionId });
            this.visualizeDiff(diff);
        } catch (err) {
            this.cursor = this.lastCommittedCursor;
            this.updateDisplay();
            console.error(`Failed to seek to ${target}:`, err);
            throw err;
        } finally {
            if (requestId === this.requestSerial) {
                this.isSeeking = false;
                this.toggleBusy(false);
            }
        }
    },

    updateDisplay() {
        const display = document.getElementById('replay-cursor-display');
        if (display) {
            display.textContent = `${this.cursor} / ${this.totalEvents}`;
        }
        const slider = document.getElementById('replay-scrubber');
        if (slider) {
            slider.max = String(this.totalEvents);
            slider.value = String(this.cursor);
        }
        
        // Update button states
        const btnPrev = document.getElementById('btn-replay-prev');
        const btnNext = document.getElementById('btn-replay-next');
        const btnStart = document.getElementById('btn-replay-start');
        const btnEnd = document.getElementById('btn-replay-end');
        if (btnPrev) btnPrev.disabled = (this.cursor === 0 || this.isSeeking);
        if (btnNext) btnNext.disabled = (this.cursor === this.totalEvents || this.isSeeking);
        if (btnStart) btnStart.disabled = (this.cursor === 0 || this.isSeeking);
        if (btnEnd) btnEnd.disabled = (this.cursor === this.totalEvents || this.isSeeking);
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
            <div class="replay-timeline-controls">
                <div class="replay-timeline-toolbar">
                    <div class="replay-button-row">
                        <button id="btn-replay-start" class="btn-tertiary btn-compact" title="Jump to Start">|&lt;</button>
                        <button id="btn-replay-prev" class="btn-tertiary btn-compact" title="Step Backward">&lt;</button>
                        <span id="replay-cursor-display" class="replay-cursor-pill">0 / 0</span>
                        <button id="btn-replay-next" class="btn-tertiary btn-compact" title="Step Forward">&gt;</button>
                        <button id="btn-replay-end" class="btn-tertiary btn-compact" title="Jump to End">&gt;|</button>
                    </div>
                    <div class="replay-time-readout">
                        <span class="replay-time-label">Media</span>
                        <span id="replay-media-time-display" class="replay-time-value">00:00.000</span>
                    </div>
                </div>
                <div class="replay-scrubber-row">
                    <input id="replay-scrubber" class="replay-scrubber" type="range" min="0" max="0" value="0" aria-label="Replay timeline scrubber">
                </div>
            </div>
            <div id="replay-diff-log" class="replay-diff-log"></div>
        `;

        document.getElementById('btn-replay-start').onclick = () => this.jumpToStart();
        document.getElementById('btn-replay-prev').onclick = () => this.stepBackward();
        document.getElementById('btn-replay-next').onclick = () => this.stepForward();
        document.getElementById('btn-replay-end').onclick = () => this.jumpToEnd();
        const slider = document.getElementById('replay-scrubber');
        if (slider) {
            let scrubTimer = null;
            slider.addEventListener('input', (event) => {
                this.cursor = Math.max(0, Math.min(this.totalEvents, Number(event.target.value) || 0));
                this.updateDisplay();
            });
            slider.addEventListener('change', async (event) => {
                const next = Math.max(0, Math.min(this.totalEvents, Number(event.target.value) || 0));
                if (scrubTimer) clearTimeout(scrubTimer);
                scrubTimer = setTimeout(() => {
                    this.seek(next, this.lastCommittedCursor).catch((error) => console.error(error));
                }, 32);
            });
        }
    },

    toggleBusy(isBusy) {
        const root = document.querySelector('.replay-timeline-controls');
        if (root) root.classList.toggle('is-busy', !!isBusy);
        this.updateDisplay();
    },

    visualizeDiff(diff) {
        const log = document.getElementById('replay-diff-log');
        if (!log) return;

        const entries = [];
        if (diff.added.nodes) Object.keys(diff.added.nodes).forEach(id => entries.push(`+ node ${id}`));
        if (diff.added.edges) diff.added.edges.forEach(e => entries.push(`+ edge ${e.from}->${e.to}`));
        if (diff.added.transcripts) diff.added.transcripts.forEach(t => entries.push(`+ transcript ${String(t.text || '').slice(0, 32)}`));
        if (diff.added.dtmf_history) diff.added.dtmf_history.forEach(d => entries.push(`+ dtmf ${d}`));
        if (diff.changed.call_status) entries.push(`status ${diff.changed.call_status}`);

        if (entries.length > 0) {
            const div = document.createElement('div');
            div.className = 'replay-diff-entry';
            div.textContent = entries.join(' | ');
            log.prepend(div);
        }
    }
};
