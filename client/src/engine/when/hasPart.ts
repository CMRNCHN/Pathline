import type { When } from "./When";

const space = " ";

/** Passes sliding windows of the transcript to the inner predicate. */
export const hasPart = (when: When): When => (transcript: string): boolean => {
  const words = transcript.split(space);
  const totalWords = words.length;

  for (let start = 0; start <= totalWords; start++) {
    for (let end = start + 1; end <= totalWords; end++) {
      const sliceOfSentence = words.slice(start, end).join(space);
      if (when(sliceOfSentence)) {
        return true;
      }
    }
  }

  return false;
};
