/** 0.9634 -> '96%'; null -> '–' */
export function pct(x: number | null | undefined): string {
  return x == null ? '–' : `${Math.round(x * 100)}%`;
}

/** Coverage band, for colouring: comfortable >= 98%, sweet spot >= 95%, hard >= 90%, else too hard. */
export function band(x: number | null | undefined): 'none' | 'easy' | 'sweet' | 'hard' | 'too-hard' {
  if (x == null) return 'none';
  if (x >= 0.98) return 'easy';
  if (x >= 0.95) return 'sweet';
  if (x >= 0.9) return 'hard';
  return 'too-hard';
}

/** S11E03 / E03 / '' */
export function episodeLabel(season: number | null | undefined, episode: number | null | undefined): string {
  const two = (n: number) => String(n).padStart(2, '0');
  if (episode == null) return '';
  return season == null ? `E${two(episode)}` : `S${two(season)}E${two(episode)}`;
}
