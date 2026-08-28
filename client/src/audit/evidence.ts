import { sha256Bytes } from "../callstate";
import type { RunRecord } from "../history/runHistory";
import type { RunInspectionReport } from "./types";
import { buildStoreZip, type ZipFile } from "./zip";

export interface EvidencePack {
  filename: string;
  bytes: Uint8Array;
  files: { name: string; sha256: string; sizeBytes: number }[];
}

function jsonBytes(value: unknown): Uint8Array {
  return new TextEncoder().encode(`${JSON.stringify(value, null, 2)}\n`);
}

function sanitizeRun(record: RunRecord): Record<string, unknown> {
  return {
    runId: record.runId,
    pathId: record.pathId,
    pathName: record.pathName,
    outcome: record.outcome,
    startedAt: record.startedAt,
    completedAt: record.completedAt,
    captured: record.captured,
    ledgerEvents: record.ledgerEvents ?? [],
    ledgerHead: record.ledgerHead,
    collectedHash: record.collectedHash,
    definedSteps: record.definedSteps ?? [],
    uploadState: record.uploadState,
  };
}

async function hashedFile(name: string, bytes: Uint8Array): Promise<{ file: ZipFile; sha256: string }> {
  const sha256 = await sha256Bytes(bytes);
  return { file: { name, bytes }, sha256 };
}

/** Local-only evidence zip. Never upload this pack to the Pathline API. */
export async function buildEvidencePack(
  record: RunRecord,
  report: RunInspectionReport
): Promise<EvidencePack> {
  const runFile = await hashedFile("run.json", jsonBytes(sanitizeRun(record)));
  const ledgerFile = await hashedFile("ledger.json", jsonBytes(record.ledgerEvents ?? []));
  const inspectionFile = await hashedFile("inspection.json", jsonBytes(report));

  const files = [
    { name: runFile.file.name, sha256: runFile.sha256, sizeBytes: runFile.file.bytes.byteLength },
    { name: ledgerFile.file.name, sha256: ledgerFile.sha256, sizeBytes: ledgerFile.file.bytes.byteLength },
    {
      name: inspectionFile.file.name,
      sha256: inspectionFile.sha256,
      sizeBytes: inspectionFile.file.bytes.byteLength,
    },
  ];

  const integrity = {
    bundleId: record.runId,
    createdAt: new Date().toISOString(),
    fileCount: files.length,
    files,
  };
  const integrityFile = await hashedFile("integrity.json", jsonBytes(integrity));
  files.push({
    name: integrityFile.file.name,
    sha256: integrityFile.sha256,
    sizeBytes: integrityFile.file.bytes.byteLength,
  });

  const bytes = buildStoreZip([
    runFile.file,
    ledgerFile.file,
    inspectionFile.file,
    integrityFile.file,
  ]);

  return {
    filename: `pathline-evidence-${record.runId.slice(0, 8)}.zip`,
    bytes,
    files,
  };
}

export function downloadEvidencePack(pack: EvidencePack): void {
  const blob = new Blob([pack.bytes], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = pack.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
