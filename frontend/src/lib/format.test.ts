import { describe, expect, it } from 'vitest';
import { band, episodeLabel, pct } from './format';

describe('format', () => {
  it('pct', () => {
    expect(pct(0.9634)).toBe('96%');
    expect(pct(0)).toBe('0%');
    expect(pct(null)).toBe('–');
    expect(pct(undefined)).toBe('–');
  });
  it('band', () => {
    expect([null, 0.99, 0.98, 0.96, 0.95, 0.93, 0.9, 0.5].map(band)).toEqual(
      ['none', 'easy', 'easy', 'sweet', 'sweet', 'hard', 'hard', 'too-hard']);
  });
  it('episodeLabel', () => {
    expect(episodeLabel(11, 3)).toBe('S11E03');
    expect(episodeLabel(null, 7)).toBe('E07');
    expect(episodeLabel(1, null)).toBe('');
  });
});
