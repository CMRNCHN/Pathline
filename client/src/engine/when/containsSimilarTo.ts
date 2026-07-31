import type { When } from "./When";
import { hasPart } from "./hasPart";
import { similarTo } from "./similarTo";

/** Checks whether any substring of the transcript is similar to the reference. */
export const containsSimilarTo = (
  similarText: string,
  similarityThreshold = 0.8
): When => (transcript: string) =>
  hasPart(similarTo(similarText, similarityThreshold))(transcript);
