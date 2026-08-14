import type { When } from "./When";

export const or = (...whens: When[]): When => (transcript: string) =>
  whens.some((when) => when(transcript));

export const and = (...whens: When[]): When => (transcript: string) =>
  whens.every((when) => when(transcript));
