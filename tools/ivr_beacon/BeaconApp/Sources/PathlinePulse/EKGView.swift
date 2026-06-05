import SwiftUI

/// Scrolling EKG waveform driven by a TimelineView — no state needed.
struct EKGView: View {
    var color: Color = .green
    /// Width of one full beat cycle in points.
    var cycleWidth: CGFloat = 90
    /// Speed in cycles per second.
    var speed: Double = 0.7

    var body: some View {
        TimelineView(.animation(minimumInterval: 1 / 30)) { ctx in
            let t = ctx.date.timeIntervalSinceReferenceDate
            Canvas { context, size in
                drawEKG(in: context, size: size, time: t)
            }
        }
    }

    private func drawEKG(in context: GraphicsContext, size: CGSize, time: Double) {
        let mid = size.height / 2
        // Phase offset scrolls the pattern leftward.
        let phaseOffset = CGFloat(time * speed * cycleWidth)
            .truncatingRemainder(dividingBy: cycleWidth)

        var path = Path()
        var x = -phaseOffset - cycleWidth   // start one cycle off-screen left

        path.move(to: CGPoint(x: x, y: mid))

        while x < size.width + cycleWidth {
            let cw = cycleWidth
            // ── flat lead-in (30 % of cycle) ─────────────────────────────────
            path.addLine(to: CGPoint(x: x + cw * 0.28, y: mid))
            // ── P wave — small rounded bump ───────────────────────────────────
            path.addQuadCurve(
                to:      CGPoint(x: x + cw * 0.42, y: mid),
                control: CGPoint(x: x + cw * 0.35, y: mid - size.height * 0.18)
            )
            // ── PR segment ────────────────────────────────────────────────────
            path.addLine(to: CGPoint(x: x + cw * 0.47, y: mid))
            // ── QRS: sharp down then spike up then back ───────────────────────
            path.addLine(to: CGPoint(x: x + cw * 0.50, y: mid + size.height * 0.22))
            path.addLine(to: CGPoint(x: x + cw * 0.53, y: mid - size.height * 0.70))
            path.addLine(to: CGPoint(x: x + cw * 0.56, y: mid + size.height * 0.10))
            path.addLine(to: CGPoint(x: x + cw * 0.60, y: mid))
            // ── T wave — smooth hump ──────────────────────────────────────────
            path.addQuadCurve(
                to:      CGPoint(x: x + cw * 0.80, y: mid),
                control: CGPoint(x: x + cw * 0.70, y: mid - size.height * 0.28)
            )
            // ── flat tail ─────────────────────────────────────────────────────
            path.addLine(to: CGPoint(x: x + cw, y: mid))
            x += cw
        }

        context.stroke(
            path,
            with: .color(color),
            style: StrokeStyle(lineWidth: 1.5, lineCap: .round, lineJoin: .round)
        )
    }
}
