import SwiftUI

// ── Semantic state — what a job IS ────────────────────────────────────────────

enum PulseMode {
    case healthy
    case running
    case warning
    case error
    case unknown

    static func from(status: String, isRunning: Bool = false) -> PulseMode {
        if isRunning { return .running }
        switch status.uppercased() {
        case "GREEN":           return .healthy
        case "YELLOW", "ORANGE": return .warning
        case "RED":             return .error
        default:                return .unknown
        }
    }

    var defaultColor: Color {
        switch self {
        case .healthy: return .green
        case .running: return .blue
        case .warning: return .orange
        case .error:   return .red
        case .unknown: return .gray
        }
    }
}

// ── Visual behavior — how to animate ─────────────────────────────────────────
// Mapping is deterministic and lives here — not in PulseMode, not in callers.

enum PulseAnimation {
    case heartbeat        // regular QRS
    case scanner          // fast beat + traveling highlight
    case reducedAmplitude // beat with skipped cycles
    case flatline         // flat with rare micro-blip
    case minimal          // slow, low-amplitude beat

    /// Exhaustive — no default. Every new PulseMode must declare its animation here.
    static func from(_ mode: PulseMode) -> PulseAnimation {
        switch mode {
        case .healthy: .heartbeat
        case .running: .scanner
        case .warning: .reducedAmplitude
        case .error:   .flatline
        case .unknown: .minimal
        }
    }

    var speed: Double {
        switch self {
        case .heartbeat:        return 0.70
        case .scanner:          return 1.80
        case .reducedAmplitude: return 0.55
        case .flatline:         return 0.00
        case .minimal:          return 0.30
        }
    }

    var lineWidth: CGFloat {
        self == .scanner ? 2.0 : 1.5
    }
}

// ── EKG canvas ────────────────────────────────────────────────────────────────

struct EKGView: View {
    var mode: PulseMode
    var color: Color
    var cycleWidth: CGFloat

    init(mode: PulseMode = .healthy, color: Color? = nil, cycleWidth: CGFloat = 90) {
        self.mode = mode
        self.cycleWidth = cycleWidth
        self.color = color ?? mode.defaultColor
    }

    var body: some View {
        let anim = PulseAnimation.from(mode)
        TimelineView(.animation(minimumInterval: 1.0 / 30)) { ctx in
            let t = ctx.date.timeIntervalSinceReferenceDate
            Canvas { context, size in
                draw(animation: anim, in: context, size: size, time: t)
            }
        }
    }

    // ── Dispatch to animation ──────────────────────────────────────────────────

    private func draw(animation: PulseAnimation, in context: GraphicsContext,
                      size: CGSize, time: Double) {
        switch animation {
        case .flatline:                          drawFlatline(in: context, size: size, time: time)
        case .reducedAmplitude:                  drawIrregular(in: context, size: size, time: time)
        case .heartbeat, .scanner, .minimal:     drawBeat(animation: animation, in: context, size: size, time: time)
        }
        if animation == .scanner {
            drawScanner(in: context, size: size, time: time)
        }
    }

    // ── Heartbeat / scanner / minimal ─────────────────────────────────────────

    private func drawBeat(animation: PulseAnimation, in context: GraphicsContext,
                          size: CGSize, time: Double) {
        let mid = size.height / 2
        let phase = CGFloat(time * animation.speed * cycleWidth)
            .truncatingRemainder(dividingBy: cycleWidth)

        var path = Path()
        var x = -phase - cycleWidth
        path.move(to: CGPoint(x: x, y: mid))
        while x < size.width + cycleWidth {
            appendBeat(to: &path, at: x, mid: mid, size: size)
            x += cycleWidth
        }
        context.stroke(path, with: .color(color),
                       style: StrokeStyle(lineWidth: animation.lineWidth,
                                          lineCap: .round, lineJoin: .round))
    }

    // ── Warning — every 3rd beat skipped ──────────────────────────────────────

    private func drawIrregular(in context: GraphicsContext, size: CGSize, time: Double) {
        let mid = size.height / 2
        let anim = PulseAnimation.reducedAmplitude
        let phase = CGFloat(time * anim.speed * cycleWidth)
            .truncatingRemainder(dividingBy: cycleWidth)

        var path = Path()
        var x = -phase - cycleWidth
        var beat = 0
        path.move(to: CGPoint(x: x, y: mid))
        while x < size.width + cycleWidth {
            if beat % 3 == 2 {
                path.addLine(to: CGPoint(x: x + cycleWidth, y: mid))
            } else {
                appendBeat(to: &path, at: x, mid: mid, size: size, scale: 0.75)
            }
            x += cycleWidth; beat += 1
        }
        context.stroke(path, with: .color(color),
                       style: StrokeStyle(lineWidth: anim.lineWidth,
                                          lineCap: .round, lineJoin: .round))
    }

    // ── Error — flatline + rare blip ──────────────────────────────────────────

    private func drawFlatline(in context: GraphicsContext, size: CGSize, time: Double) {
        let mid = size.height / 2
        let blipActive = time.truncatingRemainder(dividingBy: 4.0) < 0.15

        var path = Path()
        path.move(to: CGPoint(x: 0, y: mid))
        if blipActive {
            let bx = size.width * 0.3
            path.addLine(to: CGPoint(x: bx, y: mid))
            path.addLine(to: CGPoint(x: bx + 4, y: mid - size.height * 0.25))
            path.addLine(to: CGPoint(x: bx + 8, y: mid))
        }
        path.addLine(to: CGPoint(x: size.width, y: mid))
        context.stroke(path, with: .color(color),
                       style: StrokeStyle(lineWidth: 1.5, lineCap: .round, lineJoin: .round))
    }

    // ── Running — traveling scanner highlight ─────────────────────────────────

    private func drawScanner(in context: GraphicsContext, size: CGSize, time: Double) {
        let anim = PulseAnimation.scanner
        let period = 1.2 / anim.speed
        let pos = CGFloat(time.truncatingRemainder(dividingBy: period) / period)
            * (size.width + 40) - 20
        var p = Path()
        p.move(to: CGPoint(x: pos, y: 0))
        p.addLine(to: CGPoint(x: pos, y: size.height))
        context.stroke(p, with: .color(.white.opacity(0.35)),
                       style: StrokeStyle(lineWidth: 3, lineCap: .round))
    }

    // ── Shared QRS geometry ───────────────────────────────────────────────────

    private func appendBeat(to path: inout Path, at x: CGFloat,
                             mid: CGFloat, size: CGSize, scale: CGFloat = 1.0) {
        let cw = cycleWidth
        path.addLine(to: CGPoint(x: x + cw * 0.28, y: mid))
        path.addQuadCurve(
            to:      CGPoint(x: x + cw * 0.42, y: mid),
            control: CGPoint(x: x + cw * 0.35, y: mid - size.height * 0.18 * scale))
        path.addLine(to: CGPoint(x: x + cw * 0.47, y: mid))
        path.addLine(to: CGPoint(x: x + cw * 0.50, y: mid + size.height * 0.22 * scale))
        path.addLine(to: CGPoint(x: x + cw * 0.53, y: mid - size.height * 0.70 * scale))
        path.addLine(to: CGPoint(x: x + cw * 0.56, y: mid + size.height * 0.10 * scale))
        path.addLine(to: CGPoint(x: x + cw * 0.60, y: mid))
        path.addQuadCurve(
            to:      CGPoint(x: x + cw * 0.80, y: mid),
            control: CGPoint(x: x + cw * 0.70, y: mid - size.height * 0.28 * scale))
        path.addLine(to: CGPoint(x: x + cw, y: mid))
    }
}
