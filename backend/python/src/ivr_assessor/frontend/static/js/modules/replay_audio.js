/**
 * HTML5 Audio Replay Engine for Pathline.
 * Responsibilities:
 * - HTML5 Audio wrapper
 * - Synchronized replay cursor updates
 * - Deterministic time polling
 * - Playback state transitions
 * - Jump-to-event
 * - Replay seeking
 */
export class ReplayAudioEngine {
    constructor(sessionId, onTimeUpdate, onStateChange) {
        this.sessionId = sessionId;
        this.audio = new Audio();
        this.onTimeUpdate = onTimeUpdate;
        this.onStateChange = onStateChange;
        this.playbackState = 'stopped';
        this.isSeeking = false;

        this.audio.addEventListener('timeupdate', () => {
            if (!this.isSeeking) {
                this.onTimeUpdate(this.audio.currentTime * 1000);
            }
        });

        this.audio.addEventListener('play', () => this.setState('playing'));
        this.audio.addEventListener('pause', () => this.setState('paused'));
        this.audio.addEventListener('ended', () => this.setState('stopped'));
        this.audio.addEventListener('error', (e) => {
            console.error('Audio playback error:', e);
            this.setState('error');
        });
    }

    async load() {
        this.audio.src = `/api/replays/${this.sessionId}/media/stream`;
        return new Promise((resolve, reject) => {
            this.audio.addEventListener('canplaythrough', resolve, { once: true });
            this.audio.addEventListener('error', reject, { once: true });
            this.audio.load();
        });
    }

    play() {
        this.audio.play().catch(e => console.error('Play failed:', e));
    }

    pause() {
        this.audio.pause();
    }

    stop() {
        this.audio.pause();
        this.audio.currentTime = 0;
        this.setState('stopped');
    }

    seek(timeMs) {
        this.isSeeking = true;
        this.audio.currentTime = timeMs / 1000;
        this.isSeeking = false;
        this.onTimeUpdate(timeMs);
    }

    setRate(rate) {
        this.audio.playbackRate = rate;
    }

    setState(state) {
        this.playbackState = state;
        if (this.onStateChange) {
            this.onStateChange(state);
        }
    }

    get durationMs() {
        return (this.audio.duration || 0) * 1000;
    }

    get currentTimeMs() {
        return this.audio.currentTime * 1000;
    }
}
