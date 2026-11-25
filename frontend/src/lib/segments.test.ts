import { describe, expect, it } from 'vitest';
import type { AnalyzedToken } from './api';
import { segments, sentenceRuns } from './segments';

const tok = (surface: string, start: number, extra: Partial<AnalyzedToken> = {}): AnalyzedToken => ({
  surface, start, end: start + surface.length, lemmas: [surface], pos: 'noun', key: surface, weak: false,
  state: 'unknown', lemma: surface, ...extra
});

describe('segments', () => {
  it('keeps the original text exactly', () => {
    const text = '밥을 먹고 갔다.';
    const segs = segments(text, [tok('밥을', 0), tok('먹고', 3), tok('갔다', 6)]);
    expect(segs.map((s) => s.text).join('')).toBe(text);
    expect(segs.filter((s) => s.token).map((s) => s.text)).toEqual(['밥을', '먹고', '갔다']);
  });

  it('handles no tokens and empty text', () => {
    expect(segments('', [])).toEqual([]);
    expect(segments('ㅋㅋ', [])).toEqual([{ text: 'ㅋㅋ', token: null }]);
  });

  it('skips a second token on the same span (배신당했어 -> 배신 + 당하다)', () => {
    const segs = segments('배신당했어', [tok('배신당했어', 0, { lemma: '배신' }), tok('배신당했어', 0, { lemma: '당하다' })]);
    expect(segs).toHaveLength(1);
    expect(segs[0]?.token?.lemma).toBe('배신');
  });

  it('sorts tokens by position', () => {
    const segs = segments('a b', [tok('b', 2), tok('a', 0)]);
    expect(segs.map((s) => s.text)).toEqual(['a', ' ', 'b']);
  });
});

describe('segments in a range', () => {
  it('only covers text[from, to) and keeps token identity', () => {
    const a = tok('밥을', 0), b = tok('먹고', 3);
    const segs = segments('밥을 먹고 갔다', [a, b], 3, 5);
    expect(segs).toEqual([{ text: '먹고', token: b }]);
    expect(segs[0]?.token).toBe(b);
  });
});

describe('sentenceRuns', () => {
  const text = '밥을 먹었다. 소나기가 좋다.';
  const sentences = [{ start: 0, end: 7, unknown: 0 }, { start: 8, end: 16, unknown: 1 }];
  const tokens = [tok('밥을', 0), tok('먹었다', 3), tok('소나기가', 8), tok('좋다', 13)];

  it('groups segments per sentence and keeps the text exact', () => {
    const runs = sentenceRuns(text, tokens, sentences);
    expect(runs.map((r) => r.sentence?.unknown ?? null)).toEqual([0, null, 1]);
    expect(runs.flatMap((r) => r.segments.map((s) => s.text)).join('')).toBe(text);
    expect(runs[2]?.segments.filter((s) => s.token).map((s) => s.text)).toEqual(['소나기가', '좋다']);
  });

  it('keeps text before the first and after the last sentence', () => {
    const runs = sentenceRuns('  가. ', [], [{ start: 2, end: 4, unknown: 0 }]);
    expect(runs.map((r) => [r.sentence ? 's' : '-', r.segments.map((x) => x.text).join('')])).toEqual([
      ['-', '  '], ['s', '가.'], ['-', ' ']
    ]);
  });

  it('no sentences: everything is one plain run', () => {
    expect(sentenceRuns('abc', [], [])).toEqual([{ sentence: null, segments: [{ text: 'abc', token: null }] }]);
  });
});
