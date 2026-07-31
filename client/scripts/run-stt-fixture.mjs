/**
 * Headless runner for the on-device STT pipeline fixture.
 *
 * Bundles client/src/stt/fixture.ts with esbuild (the fixture imports browser-
 * typed src modules) and runs it under Node. A minimal `window` shim is enough:
 * the pipeline only touches `window.setTimeout`/`clearTimeout` and WebCrypto
 * (`crypto.subtle`), both available on Node 18+ globals.
 *
 * Usage: npm run stt:fixture  (from the client/ directory)
 */
import { build } from "esbuild";
import { pathToFileURL } from "node:url";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Shim the browser globals the pipeline expects. Node's global setTimeout /
// clearTimeout and WebCrypto satisfy the pipeline's needs.
globalThis.window ??= globalThis;

const outfile = join(tmpdir(), `stt-fixture-${Date.now()}.mjs`);

await build({
  entryPoints: ["src/stt/fixture.ts"],
  bundle: true,
  format: "esm",
  platform: "node",
  target: "node18",
  outfile,
  logLevel: "error",
});

const { runPipelineFixture, runPrepFixture, runSelectionFixture } = await import(pathToFileURL(outfile).href);

const prep = runPrepFixture();
console.log("=== Prep fixture (waits, timeouts, DTMF w, structured detect) ===");
console.log(JSON.stringify(prep, null, 2));

const pipeline = await runPipelineFixture();
console.log("\n=== Pipeline fixture (PCM -> AudioSession -> STT -> processPhrase -> DTMF) ===");
console.log(JSON.stringify(pipeline, null, 2));

const selection = runSelectionFixture();
console.log("\n=== Selection fixture (engine choice + Web Speech guard) ===");
console.log(JSON.stringify(selection, null, 2));

const ok = prep.ok && pipeline.ok && selection.ok;
console.log(ok ? "\nSTT fixtures: PASS" : "\nSTT fixtures: FAIL");
process.exit(ok ? 0 : 1);
