import XCTest
@testable import PathlinePulse

/// Cardholder-data leak regression tests.
///
/// These exist to make a PAN leak a *build break*, not a code-review catch. They
/// drive the FSM exactly as a live probe would — including the worst case where
/// the IVR (or a loopback) echoes every card digit back as DTMF — and assert that
/// no card number ever reaches the transcript or survives in memory after dialing.
@MainActor
final class PANLeakTests: XCTestCase {

    /// A realistic 16-digit PAN (the canonical Visa test number). Never a real card.
    private let pan = "4111111111111111"

    /// Matches any 13–19 digit run — the PAN length band per ISO/IEC 7812. If this
    /// matches anything operator-visible, cardholder data has leaked.
    private func containsPANShape(_ s: String) -> Bool {
        s.range(of: "[0-9]{13,19}", options: .regularExpression) != nil
    }

    /// Run a probe end to end, then simulate the IVR echoing the full card back.
    private func runFullProbe() -> PulseState {
        let state = PulseState()
        let ch = state.startProbe(number: "+18005551234", menu: "**11", card: pan)
        state.enterStasis(channelId: ch)
        _ = state.advance(channelId: ch)   // greeting ends → send menu
        _ = state.advance(channelId: ch)   // card prompt ends → send card (PAN handed off)
        _ = state.advance(channelId: ch)   // result prompt ends → hangup
        // Worst case: the far end echoes every card digit as DTMF.
        for digit in pan { state.noteDTMF(channelId: ch, digit: String(digit)) }
        state.finish(channelId: ch)
        return state
    }

    /// The card number must never appear in the transcript — not verbatim, and
    /// not reconstructed digit-by-digit from echoed DTMF.
    func testCardNumberNeverReachesTranscript() {
        let probe = runFullProbe().probes.first!
        XCTAssertFalse(probe.transcript.contains(pan),
                       "PAN appeared verbatim in transcript:\n\(probe.transcript)")
        XCTAssertFalse(containsPANShape(probe.transcript),
                       "A 13–19 digit run reached the transcript:\n\(probe.transcript)")
    }

    /// The PAN is handed to the dialer exactly once, then wiped from the probe.
    func testCardNumberIsWipedFromMemoryAfterDialing() {
        let state = PulseState()
        let ch = state.startProbe(number: "+18005551234", menu: "**11", card: pan)
        state.enterStasis(channelId: ch)
        _ = state.advance(channelId: ch)              // greeting → menu
        let action = state.advance(channelId: ch)     // card prompt → send card

        XCTAssertEqual(action, .sendDTMF(pan),
                       "The card send must carry the PAN to the dialer exactly once")
        XCTAssertEqual(state.probes.first?.cardDigits, "",
                       "PAN still retained in CallProbe after it was dialed")
    }

    /// A single received DTMF digit is recorded without its value.
    func testReceivedDTMFValueIsRedacted() {
        let state = PulseState()
        let ch = state.startProbe(number: "+18005551234", menu: "**11", card: pan)
        state.noteDTMF(channelId: ch, digit: "4")
        let transcript = state.probes.first!.transcript
        XCTAssertFalse(transcript.contains("4"),
                       "Received DTMF digit value leaked into transcript: \(transcript)")
        XCTAssertTrue(transcript.contains("dtmf received"),
                      "DTMF arrival should still be noted (without the value)")
    }
}
