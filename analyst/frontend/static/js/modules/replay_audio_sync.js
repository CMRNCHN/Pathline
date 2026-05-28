/**
 * ReplayAudioSync — synchronizes the replay timeline cursor with audio playback.
 *
 * Subscribes to `replay:state_loaded` to discover the recording reference and
 * the deterministic event stream. Provides a scrubber handler that seeks the
 * audio element to the media offset of the currently-selected event.
 *
 * Design constraints:
 *  - Vanilla JS, no framework.
 *  - Additive only — existing replay behaviour is unaffected when no recording
 *    reference is present.
 *  - Pure mapping function (`eventIndexToMediaMs`) for deterministic testability.
 *  - Audio failures (load error, missing reference) log a warning but never throw.
 */
import { EventBus } from '../common/events.js';

const AUDIO_ELEMENT_ID = 'replay-audio';
const SCRUB_DEBOUNCE_MS = 100;

export const ReplayAudioSync = {
    events: [],
    recordingReference: null,
    audioElement: null,
    _debounceHandle: null,
    _initialized: false,

    /**
     * Pure mapping: given an event index and an events array, return the
     * media_offset_ms for that event. Returns null when the index is out of
     * bounds or the value is missing — callers decide how to fall back.
     */
    eventIndexToMediaMs(events, index) {
        if (!Array.isArray(events) || events.length === 0) return null;
        if (typeof index !== 'number' || index < 0 || index >= events.length) return null;
        const evt = events[index];
        if (!evt || typeof evt !== 'object') return null;
        const ms = evt.media_offset_ms;
        if (ms === undefined || ms === null) return null;
        if (typeof ms !== 'number' || Number.isNaN(ms)) return null;
        return ms;
    },

    /**
     * Resolve a media offset for an event index, falling back to linear
     * interpolation between the nearest known offsets when the target event
     * is missing its media_offset_ms.
     */
    resolveMediaMs(events, index) {
        const direct = this.eventIndexToMediaMs(events, index);
        if (direct !== null) return direct;
        if (!Array.isArray(events) || events.length === 0) return 0;
        const clamped = Math.max(0, Math.min(events.length - 1, index));

        let prevIdx = -1;
        let nextIdx = -1;
        for (let i = clamped - 1; i >= 0; i--) {
            if (this.eventIndexToMediaMs(events, i) !== null) { prevIdx = i; break; }
        }
        for (let i = clamped + 1; i < events.length; i++) {
            if (this.eventIndexToMediaMs(events, i) !== null) { nextIdx = i; break; }
        }

        const prevMs = prevIdx >= 0 ? this.eventIndexToMediaMs(events, prevIdx) : null;
        const nextMs = nextIdx >= 0 ? this.eventIndexToMediaMs(events, nextIdx) : null;

        if (prevMs !== null && nextMs !== null && nextIdx !== prevIdx) {
            const ratio = (clamped - prevIdx) / (nextIdx - prevIdx);
            return prevMs + (nextMs - prevMs) * ratio;
        }
        if (prevMs !== null) return prevMs;
        if (nextMs !== null) return nextMs;
        return 0;
    },

    ensureAudioElement() {
        if (typeof document === 'undefined') return null;
        let el = document.getElementById(AUDIO_ELEMENT_ID);
        if (!el) {
            el = document.createElement('audio');
            el.id = AUDIO_ELEMENT_ID;
            el.preload = 'metadata';
            el.controls = true;
            el.className = 'replay-audio-element';
            const host = document.getElementById('replay-controls') || document.body;
            host.appendChild(el);
        }
        this.audioElement = el;
        return el;
    },

    setAudioSource(reference) {
        const el = this.ensureAudioElement();
        if (!el) return;
        if (!reference) {
            el.removeAttribute('src');
            el.classList.add('is-hidden');
            return;
        }
        el.classList.remove('is-hidden');
        if (el.src !== reference) {
            el.src = reference;
            el.onerror = () => {
                console.warn('[replay_audio_sync] Audio failed to load:', reference);
            };
        }
    },

    seekToEventIndex(index) {
        if (!this.recordingReference) return;
        const el = this.audioElement || (typeof document !== 'undefined'
            ? document.getElementById(AUDIO_ELEMENT_ID)
            : null);
        if (!el) return;
        const ms = this.resolveMediaMs(this.events, index);
        try {
            el.currentTime = ms / 1000;
        } catch (err) {
            console.warn('[replay_audio_sync] Failed to seek audio:', err);
        }
    },

    debouncedSeek(index) {
        if (this._debounceHandle) clearTimeout(this._debounceHandle);
        this._debounceHandle = setTimeout(() => {
            this._debounceHandle = null;
            this.seekToEventIndex(index);
        }, SCRUB_DEBOUNCE_MS);
    },

    onStateLoaded(state, cursorIndex = null) {
        if (!state || typeof state !== 'object') return;
        this.events = Array.isArray(state.events) ? state.events : [];
        this.recordingReference = state.recording_reference || null;
        this.setAudioSource(this.recordingReference);
        if (!this.recordingReference) return;
        const idx = (typeof cursorIndex === 'number')
            ? cursorIndex
            : Math.max(0, this.events.length - 1);
        this.seekToEventIndex(idx);
    },

    init() {
        if (this._initialized) return;
        this._initialized = true;

        EventBus.on('replay:state_loaded', (state) => {
            this.onStateLoaded(state);
        });

        const scrubber = document.getElementById('replay-scrubber');
        if (scrubber) {
            scrubber.addEventListener('input', (e) => {
                const value = parseInt(e.target.value, 10);
                if (!Number.isNaN(value)) this.debouncedSeek(value);
            });
        }
    },
};

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ReplayAudioSync.init());
    } else {
        ReplayAudioSync.init();
    }
}
