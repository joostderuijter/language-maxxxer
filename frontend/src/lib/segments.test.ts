import { describe, expect, it } from 'vitest';
import type { AnalyzedToken } from './api';
import { segments } from './segments';

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
