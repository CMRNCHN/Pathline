/**
 * Canvas Waveform Renderer for Pathline.
 * Responsibilities:
 * - Canvas waveform rendering
 * - Virtualized rendering (bounded)
 * - Chunk loading (future)
 * - Cursor overlay
 * - Event markers
 */
export class WaveformRenderer {
    constructor(canvasId, onSeek) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.onSeek = onSeek;
        this.metadata = null;
        this.currentTimeMs = 0;
        this.eventMarkers = [];

        this.canvas.addEventListener('click', (e) => {
            if (!this.metadata || this.metadata.duration_ms === 0) return;
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const percentage = x / rect.width;
            const seekTimeMs = percentage * this.metadata.duration_ms;
            this.onSeek(seekTimeMs);
        });

        // Handle resize
        window.addEventListener('resize', () => this.draw());
    }

    setMetadata(metadata) {
        this.metadata = metadata;
        this.draw();
    }

    setEventMarkers(markers) {
        this.eventMarkers = markers;
        this.draw();
    }

    updateCursor(timeMs) {
        this.currentTimeMs = timeMs;
        this.draw();
    }

    draw() {
        if (!this.canvas || !this.ctx) return;
        
        // Auto-resize canvas to match display size
        const displayWidth = this.canvas.clientWidth;
        const displayHeight = this.canvas.clientHeight;
        if (this.canvas.width !== displayWidth || this.canvas.height !== displayHeight) {
            this.canvas.width = displayWidth;
            this.canvas.height = displayHeight;
        }

        const width = this.canvas.width;
        const height = this.canvas.height;
        const ctx = this.ctx;

        ctx.clearRect(0, 0, width, height);

        if (!this.metadata || !this.metadata.peaks || this.metadata.peaks.length === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No waveform data available', width / 2, height / 2);
            return;
        }

        const peaks = this.metadata.peaks;
        const durationMs = this.metadata.duration_ms;
        const barWidth = width / peaks.length;

        // Draw Waveform
        ctx.fillStyle = '#4a90e2';
        for (let i = 0; i < peaks.length; i++) {
            const peak = peaks[i];
            const barHeight = peak * height;
            const x = i * barWidth;
            const y = (height - barHeight) / 2;
            ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
        }

        // Draw Event Markers
        this.eventMarkers.forEach(marker => {
            const offsetMs = marker.media_offset_ms;
            if (offsetMs === null || offsetMs === undefined) return;
            
            const x = (offsetMs / durationMs) * width;
            ctx.strokeStyle = marker.type === 'TRANSCRIPT_FINAL' ? 'rgba(0, 255, 0, 0.5)' : 'rgba(255, 255, 255, 0.3)';
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        });

        // Draw Cursor
        const cursorX = (this.currentTimeMs / durationMs) * width;
        ctx.strokeStyle = '#ff3b30';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cursorX, 0);
        ctx.lineTo(cursorX, height);
        ctx.stroke();
    }
}
