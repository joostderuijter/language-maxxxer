import type { AnalyzedToken } from './api';

export type Segment = { text: string; token: AnalyzedToken | null };

/** Split `text` into plain runs and token runs (by the tokens' spans), so the original text renders unchanged. */
export function segments(text: string, tokens: AnalyzedToken[]): Segment[] {
  const out: Segment[] = [];
  let pos = 0;
  for (const t of [...tokens].sort((a, b) => a.start - b.start)) {
    if (t.start < pos) continue; // overlapping span (two words in one eojeol): keep the first
    if (t.start > pos) out.push({ text: text.slice(pos, t.start), token: null });
    out.push({ text: text.slice(t.start, t.end), token: t });
    pos = t.end;
  }
  if (pos < text.length) out.push({ text: text.slice(pos), token: null });
  return out;
}
