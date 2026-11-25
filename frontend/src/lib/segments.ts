import type { AnalyzedToken, SentenceInfo } from './api';

export type Segment = { text: string; token: AnalyzedToken | null };
export type Run = { sentence: SentenceInfo | null; segments: Segment[] };

/** Split text[from, to) into plain runs and token runs (by the tokens' absolute spans), so the original text renders
 *  unchanged. Tokens keep their identity (the same objects come back). */
export function segments(text: string, tokens: AnalyzedToken[], from = 0, to = text.length): Segment[] {
  const out: Segment[] = [];
  let pos = from;
  for (const t of [...tokens].sort((a, b) => a.start - b.start)) {
    if (t.start < pos || t.end > to) continue; // outside the range, or overlapping (배신당했어 -> 배신 + 당하다)
    if (t.start > pos) out.push({ text: text.slice(pos, t.start), token: null });
    out.push({ text: text.slice(t.start, t.end), token: t });
    pos = t.end;
  }
  if (pos < to) out.push({ text: text.slice(pos, to), token: null });
  return out;
}

/** Group the text by sentence; text between sentences (whitespace) becomes a run without a sentence. */
export function sentenceRuns(text: string, tokens: AnalyzedToken[], sentences: SentenceInfo[]): Run[] {
  const out: Run[] = [];
  let pos = 0;
  for (const s of [...sentences].sort((a, b) => a.start - b.start)) {
    if (s.start < pos) continue;
    if (s.start > pos) out.push({ sentence: null, segments: segments(text, [], pos, s.start) });
    out.push({ sentence: s, segments: segments(text, tokens, s.start, s.end) });
    pos = s.end;
  }
  if (pos < text.length) out.push({ sentence: null, segments: segments(text, [], pos, text.length) });
  return out;
}
