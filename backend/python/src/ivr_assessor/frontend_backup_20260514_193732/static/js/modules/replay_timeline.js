/**
 * ReplayTimeline handles deterministic temporal navigation through operational history.
 * It maintains the cursor and coordinates state/diff fetching and hydration.
 */
import { API } from '../common/api.js';
import { EventBus } from '../common/events.js';
import { ReplayAudioEngine } from './replay_audio.js';
import { WaveformRenderer } from './replay_waveform.js';

export const ReplayTimeline = {
    sessionId: null,
    cursor: 0,
    totalEvents: 0,
    snapshots: [],
    audio: null,
    waveform: null,
    playbackRate: 1.0,
    
    async init(sessionId) {
        this.sessionId = sessionId;
        try {
            const timeline = await API.get(`/api/replays/${sessionId}/timeline`);
            this.totalEvents = timeline.total_events;
            this.snapshots = timeline.snapshots || [];
            this.cursor = this.totalEvents; // Default to end
            
            // Initialize Audio
            this.audio = new ReplayAudioEngine(
                sessionId, 
                (timeMs) => this.onAudioTimeUpdate(timeMs),
                (state) => this.onAudioStateChange(state)
            );
            await this.audio.load();

            // Initialize Waveform
            this.waveform = new WaveformRenderer('waveform-canvas', (timeMs) => this.seekToMediaTime(timeMs));
            const waveformData = await API.get(`/api/replays/${sessionId}/waveform`);
            this.waveform.setMetadata(waveformData);
            
            // Get event markers for waveform
            const alignment = await API.get(`/api/replays/${sessionId}/align`);
            this.waveform.setEventMarkers(alignment);

            this.renderControls();
            this.updateDisplay();
        } catch (err) {
            console.error('Failed to initialize ReplayTimeline:', err);
        }
    },

    async onAudioTimeUpdate(timeMs) {
        this.waveform.updateCursor(timeMs);
        this.updateTimeDisplay(timeMs);

        // Sync with events: find nearest event for this time
        try {
            const cursorData = await API.get(`/api/replays/${this.sessionId}/seek?t=${Math.floor(timeMs)}`);
            if (cursorData && cursorData.cursor && cursorData.cursor.event_index !== this.cursor) {
                this.cursor = cursorData.cursor.event_index;
                this.updateDisplay();
                // Hydrate state for the new active event
                EventBus.emit('replay:state_loaded', cursorData.state);
            }
        } catch (err) {
            // Ignore seek errors during polling
        }
    },

    onAudioStateChange(state) {
        const btnPlay = document.getElementById('btn-replay-play');
        if (btnPlay) {
            btnPlay.innerHTML = state === 'playing' ? 
                '<span class="icon">⏸</span>' : 
                '<span class="icon">▶</span>';
            btnPlay.title = state === 'playing' ? 'Pause' : 'Play';
        }
    },

    async seekToMediaTime(timeMs) {
        this.audio.seek(timeMs);
        // onAudioTimeUpdate will handle the rest
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
            const cursorData = await API.get(`/api/replays/${this.sessionId}/cursor/${this.cursor}`);
            
            // Sync audio if it's far off (e.g. manual step)
            if (this.audio) {
                const targetTimeMs = cursorData.media_time_ms || 0;
                if (Math.abs(this.audio.currentTimeMs - targetTimeMs) > 100) {
                    this.audio.seek(targetTimeMs);
                }
            }

            // Fetch state for hydration
            const state = await API.get(`/api/replays/${this.sessionId}/state/${this.cursor}`);
            
            // Dispatch event for hydration
            EventBus.emit('replay:state_loaded', state);
            
            if (oldPosition !== null) {
                const diff = await API.get(`/api/replays/${this.sessionId}/diff/${oldPosition}/${this.cursor}`);
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

    updateTimeDisplay(timeMs) {
        const timeDisplay = document.getElementById('replay-media-time-display');
        if (timeDisplay) {
            const seconds = Math.floor(timeMs / 1000);
            const ms = Math.floor(timeMs % 1000);
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
        }
    },

    renderControls() {
        const container = document.getElementById('replay-controls');
        if (!container) return;

        container.innerHTML = `
            <div class="replay-timeline-controls" style="display: flex; flex-direction: column; gap: 8px; padding: 12px; background: var(--panel-inset); border-radius: var(--radius-md); border: 1px solid var(--border);">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button id="btn-replay-start" class="btn-secondary btn-compact" title="Jump to Start">⇤</button>
                    <button id="btn-replay-prev" class="btn-secondary btn-compact" title="Step Backward">←</button>
                    
                    <button id="btn-replay-play" class="btn-primary" style="min-width: 48px; height: 32px; display: flex; align-items: center; justify-content: center;" title="Play">
                        <span class="icon">▶</span>
                    </button>

                    <button id="btn-replay-next" class="btn-secondary btn-compact" title="Step Forward">→</button>
                    <button id="btn-replay-end" class="btn-secondary btn-compact" title="Jump to End">⇥</button>
                    
                    <span id="replay-cursor-display" class="status-pill tone-accent" style="font-family: var(--font-mono); font-size: 11px;">0 / 0</span>

                    <div style="flex-grow: 1;"></div>
                    
                    <select id="replay-rate-selector" class="input-select btn-compact" style="width: auto;">
                        <option value="0.5">0.5x</option>
                        <option value="1.0" selected>1.0x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2.0">2.0x</option>
                    </select>

                    <div style="display: flex; align-items: center; gap: 4px; padding: 4px 12px; background: var(--panel-raised); border-radius: 8px; border: 1px solid var(--border);">
                        <span style="font-size: 9px; color: var(--text-4); text-transform: uppercase; font-weight: bold;">Time</span>
                        <span id="replay-media-time-display" style="font-family: var(--font-mono); font-size: 12px; color: var(--accent);">00:00.000</span>
                    </div>
                </div>
            </div>
            <div id="replay-diff-log" style="margin-top: 8px; font-family: var(--font-mono); font-size: 10px; color: var(--text-3); max-height: 80px; overflow-y: auto;"></div>
        `;

        document.getElementById('btn-replay-start').onclick = () => this.jumpToStart();
        document.getElementById('btn-replay-prev').onclick = () => this.stepBackward();
        document.getElementById('btn-replay-next').onclick = () => this.stepForward();
        document.getElementById('btn-replay-end').onclick = () => this.jumpToEnd();
        
        document.getElementById('btn-replay-play').onclick = () => {
            if (this.audio.playbackState === 'playing') {
                this.audio.pause();
            } else {
                this.audio.play();
            }
        };

        document.getElementById('replay-rate-selector').onchange = (e) => {
            const rate = parseFloat(e.target.value);
            this.audio.setRate(rate);
        };
    },

    visualizeDiff(diff) {
        const log = document.getElementById('replay-diff-log');
        if (!log) return;

        const entries = [];
        if (diff.added.nodes) Object.keys(diff.added.nodes).forEach(id => entries.push(`<span style="color: var(--success);">+ node: ${id}</span>`));
        if (diff.added.edges) diff.added.edges.forEach(e => entries.push(`<span style="color: var(--success);">+ edge: ${e.from}->${e.to}</span>`));
        if (diff.added.transcripts) diff.added.transcripts.forEach(t => entries.push(`<span style="color: var(--accent);">+ transcript: ${t.text.substring(0, 20)}...</span>`));
        if (diff.added.dtmf_history) diff.added.dtmf_history.forEach(d => entries.push(`<span style="color: var(--warn);">+ dtmf: ${d}</span>`));
        if (diff.changed.call_status) entries.push(`<span style="color: var(--text-1);">Δ status: ${diff.changed.call_status}</span>`);

        if (entries.length > 0) {
            const div = document.createElement('div');
            div.style.marginBottom = '4px';
            div.style.padding = '4px 8px';
            div.style.background = 'rgba(255,255,255,0.02)';
            div.style.borderRadius = '4px';
            div.innerHTML = entries.join(' <span style="opacity: 0.3">|</span> ');
            log.prepend(div);
        }
    }
};
