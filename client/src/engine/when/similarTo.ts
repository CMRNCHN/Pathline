import { compareTwoStrings } from "string-similarity";
import type { When } from "./When";

/** Compares the full transcript to a reference string. */
export const similarTo = (
  similarText: string,
  similarityThreshold = 0.8
): When => (transcript: string) =>
  compareTwoStrings(similarText, transcript) >= similarityThreshold;
