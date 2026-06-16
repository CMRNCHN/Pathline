#!/usr/bin/env node
//
// Standalone ARI controller — a disposable channel-holder + DTMF ground-truth
// logger for the DTMF transport probe (probe-ari-dtmf.sh).
//
// WHY THIS EXISTS (and why it is NOT the Swift Pulse client)
// ─────────────────────────────────────────────────────────────────────────────
// The probe answers one question: does ARI read `dtmf` from a JSON body, a
// form body, or neither? To answer it honestly you need a LIVE channel that is
// genuinely in a DTMF-capable state, and you need an INDEPENDENT witness of
// whether the digit actually arrived. Using the Swift Pulse client to supply
// that channel mixes the client-under-test into the test fixture — the same
// contamination the curl probe was built to avoid. This controller is that
// fixture, kept deliberately separate:
//
//   - it claims the Stasis app (default `pulse`),
//   - answers the channel,
//   - BRIDGES the channel into a mixing bridge so Asterisk pumps its media
//     (a bare answer() leaves a Local loopback without two-way media — this is
//     the "Down state" failure mode; see AsteriskClient.swift enterStasis),
//   - logs every DTMF digit and every lifecycle transition with timestamps.
//
// It DECIDES NOTHING about A/B/C. It only emits ground truth: "the channel went
// live", "a digit arrived", "the channel was destroyed". A human reads its log
// next to the curl probe's HTTP status and classifies by hand.
//
// RUN IT INSTEAD OF PULSE, NEVER ALONGSIDE IT
// ─────────────────────────────────────────────────────────────────────────────
// Two WebSocket subscribers on the same Stasis app fight over each channel
// (both try to answer/bridge). Run EITHER this controller OR the Swift Pulse
// app against `pulse`, not both.
//
// The repo dialplan is UNCHANGED: extension 1000 stays the native IVR
// (SayDigits menu + Read echo). That IVR is the "did the IVR advance" signal.
// You reach Stasis through the ORIGINATE call, not the dialplan:
//
//   1. Start Asterisk:
//        docker compose -f infrastructure/docker-compose.yml up asterisk -d
//
//   2. Start this controller (it subscribes to `pulse` and waits):
//        node tools/ivr_beacon/ari-controller.js
//
//   3. Originate a Local call whose far end runs the real IVR and whose near
//      end enters Stasis(pulse) under a chosen channel id:
//        curl -sS -X POST \
//          "http://127.0.0.1:8088/ari/channels?endpoint=Local/1000@ivr-test&app=pulse&channelId=probe-1&api_key=ari:ari"
//
//   4. While the call is up, run the probe with that id and watch THIS log for
//      the "DTMF RECEIVED" line as the independent witness:
//        ./tools/ivr_beacon/probe-ari-dtmf.sh probe-1
//
// Config (env, matching the probe + Swift client conventions):
//   PULSE_ARI_HOST     default 127.0.0.1
//   PULSE_ARI_PORT     default 8088
//   PULSE_ARI_API_KEY  default ari:ari   (form: user:pass)
//   PULSE_ARI_APP      default pulse
// ─────────────────────────────────────────────────────────────────────────────

'use strict';

const ari = require('ari-client');

const HOST = process.env.PULSE_ARI_HOST || '127.0.0.1';
const PORT = process.env.PULSE_ARI_PORT || '8088';
const API_KEY = process.env.PULSE_ARI_API_KEY || 'ari:ari';
const APP = process.env.PULSE_ARI_APP || 'pulse';

const [USER, PASS] = API_KEY.split(':');
const ARI_URL = `http://${HOST}:${PORT}`;

// One timestamped log line per event — deterministic, greppable ground truth.
function log(tag, fields) {
  const parts = [new Date().toISOString(), tag];
  if (fields) {
    for (const [k, v] of Object.entries(fields)) parts.push(`${k}=${v}`);
  }
  console.log(parts.join(' '));
}

// channelId -> bridgeId, so we can tear the bridge down when the channel dies.
const bridges = new Map();

async function main() {
  const client = await ari.connect(ARI_URL, USER, PASS);
  log('CONNECTED', { url: ARI_URL, app: APP });

  client.on('StasisStart', async (event, channel) => {
    log('STASIS_START', { channel: channel.id, name: channel.name });

    try {
      // Answer first so the channel leaves the Down state.
      await channel.answer();
      log('ANSWERED', { channel: channel.id });

      // Then hold it in a mixing bridge so Asterisk pumps its media. Without
      // this, a Local loopback has no two-way media and DTMF/IVR behaviour is
      // unreliable — this mirrors the Swift client's enterStasis bridge step.
      const bridgeId = `${channel.id}-bridge`;
      const bridge = await client.bridges.create({ type: 'mixing', bridgeId });
      await bridge.addChannel({ channel: channel.id });
      bridges.set(channel.id, bridgeId);
      log('BRIDGED', { channel: channel.id, bridge: bridgeId });
    } catch (err) {
      log('SETUP_ERROR', { channel: channel.id, error: err.message });
    }

    // Ground-truth DTMF witness — the line to watch when the probe fires.
    channel.on('ChannelDtmfReceived', (evt, dtmf) => {
      log('DTMF_RECEIVED', { channel: channel.id, digit: dtmf.digit });
    });

    // Talk-detect transitions aren't enabled here, but if the far-end IVR
    // hangs up or transitions we still want it on the record.
    channel.on('ChannelHangupRequest', (evt, ch) => {
      log('HANGUP_REQUEST', { channel: ch.id });
    });
  });

  // The channel left our app (e.g. far-end IVR finished). Record it.
  client.on('StasisEnd', (event, channel) => {
    log('STASIS_END', { channel: channel.id });
  });

  // Channel gone for good — tear down its bridge so we don't leak bridges
  // across repeated probe runs.
  client.on('ChannelDestroyed', async (event, channel) => {
    log('CHANNEL_DESTROYED', { channel: channel.id });
    const bridgeId = bridges.get(channel.id);
    if (bridgeId) {
      bridges.delete(channel.id);
      try {
        await client.bridges.destroy({ bridgeId });
        log('BRIDGE_DESTROYED', { bridge: bridgeId });
      } catch (err) {
        log('BRIDGE_DESTROY_ERROR', { bridge: bridgeId, error: err.message });
      }
    }
  });

  await client.start(APP);
  log('SUBSCRIBED', { app: APP });
}

main().catch((err) => {
  log('FATAL', { error: err.message });
  process.exit(1);
});
