import { contains } from "./contains";
import { containsSimilarTo } from "./containsSimilarTo";
import { and, or } from "./combinators";
import { matches } from "./matches";
import type { When } from "./When";

const NEXT_UTTERANCE_DETECT = "__next_utterance__";
const END_NOW_DETECT = "__end_now__";
const FUZZY_PREFIX = "~";
const REGEX_PREFIX = "regex:";

function compilePipeOrContains(detect: string): When {
  const alternatives = detect
    .split("|")
    .map((part) => part.trim())
    .filter(Boolean);

  if (alternatives.length === 0) {
    return () => false;
  }

  return or(...alternatives.map((part) => contains(part)));
}

type DetectJson =
  | string
  | DetectJson[]
  | {
      and?: DetectJson[];
      or?: DetectJson[];
      contains?: string;
      fuzzy?: string;
      similarTo?: string;
      threshold?: number;
      regex?: string;
      flags?: string;
    };

function compileJsonDetectNode(node: DetectJson): When {
  if (typeof node === "string") {
    return compileDetect(node);
  }
  if (Array.isArray(node)) {
    return and(...node.map(compileJsonDetectNode));
  }
  if (node.and) {
    return and(...node.and.map(compileJsonDetectNode));
  }
  if (node.or) {
    return or(...node.or.map(compileJsonDetectNode));
  }
  if (typeof node.contains === "string") {
    return contains(node.contains);
  }
  const fuzzy = node.fuzzy ?? node.similarTo;
  if (typeof fuzzy === "string") {
    return containsSimilarTo(fuzzy, node.threshold);
  }
  if (typeof node.regex === "string") {
    return matches(new RegExp(node.regex, node.flags ?? ""));
  }
  return () => false;
}

function compileStructuredJsonDetect(detect: string): When | null {
  if (!detect.startsWith("{") && !detect.startsWith("[")) return null;
  try {
    return compileJsonDetectNode(JSON.parse(detect) as DetectJson);
  } catch {
    return () => false;
  }
}

/**
 * Compiles a Path detect string into an ivr-tester-style When predicate.
 *
 * Supported forms:
 * - `needle` or `a|b|c` — case-insensitive substring (legacy default)
 * - `{"and":["a",{"or":["b","c"]}]}` — structured nested detect JSON
 * - `~phrase` or `~0.85:phrase` — fuzzy substring match
 * - `regex:/pattern/i` — regular expression
 */
export function compileDetect(detect: string): When {
  const trimmed = detect.trim();
  if (!trimmed) {
    return () => false;
  }

  if (trimmed === NEXT_UTTERANCE_DETECT || trimmed === END_NOW_DETECT) {
    return () => false;
  }

  const structured = compileStructuredJsonDetect(trimmed);
  if (structured) {
    return structured;
  }

  if (trimmed.startsWith(REGEX_PREFIX)) {
    const spec = trimmed.slice(REGEX_PREFIX.length);
    const lastSlash = spec.lastIndexOf("/");
    if (lastSlash <= 0) {
      return () => false;
    }
    const pattern = spec.slice(1, lastSlash);
    const flags = spec.slice(lastSlash + 1);
    return matches(new RegExp(pattern, flags));
  }

  if (trimmed.startsWith(FUZZY_PREFIX)) {
    const body = trimmed.slice(FUZZY_PREFIX.length);
    const thresholdSplit = body.indexOf(":");
    if (thresholdSplit > 0) {
      const threshold = Number.parseFloat(body.slice(0, thresholdSplit));
      const text = body.slice(thresholdSplit + 1);
      if (!Number.isNaN(threshold) && text) {
        return containsSimilarTo(text, threshold);
      }
    }
    return containsSimilarTo(body);
  }

  return compilePipeOrContains(trimmed);
}

/** Evaluates a detect string against a transcript. */
export function evaluateDetect(transcript: string, detect: string): boolean {
  return compileDetect(detect)(transcript);
}
