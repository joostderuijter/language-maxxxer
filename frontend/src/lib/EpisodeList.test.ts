import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import type { Episode } from './api';
import EpisodeList from './EpisodeList.svelte';
import { mockApi } from './test-utils';

afterEach(() => vi.unstubAllGlobals());

const ep = (id: number, extra: Partial<Episode> = {}): Episode => ({
  id, series: 'Running Man', season: 11, episode: id, title: `Episode ${id}`, status: 'analyzed', subtitle: 'stream:3',
  duration_s: 4000, coverage: 0.95, new_words: 2, one_new: 5, sentences: 900, ...extra
});

it('shows episodes; unanalysed ones say why and cannot be opened', () => {
  render(EpisodeList, { language: 'ko', episodes: [ep(1), ep(2, { status: 'no_subtitles', coverage: null })], onchange: vi.fn() });
  const first = screen.getByRole('button', { name: /S11E01/ });
  expect(first).toHaveTextContent('2 new · 5 one-new');
  expect(first).toHaveTextContent('95%');
  const second = screen.getByRole('button', { name: /S11E02/ });
  expect(second).toHaveTextContent('no Korean subtitles');
  expect(second).toBeDisabled();
});

it('opens an episode, shows its new words, and marking one refreshes', async () => {
  let known = false;
  const api = mockApi({
    'GET /api/library/items/1/words': () => ({
      json: known ? [{ key: '쏟아지다', lemmas: ['쏟아지다'], count: 1, state: 'unknown' }]
        : [{ key: '소나기', lemmas: ['소나기'], count: 3, state: 'learning' }, { key: '쏟아지다', lemmas: ['쏟아지다'], count: 1, state: 'unknown' }]
    }),
    'GET /api/dictionary/ko': () => ({ json: { lemma: '소나기', idioms: [], senses: [] } }),
    'POST /api/knowledge/events': () => { known = true; return { json: { lemma: '소나기', state: 'known', confidence: 0.9 } }; }
  });
  const onchange = vi.fn();
  render(EpisodeList, { language: 'ko', episodes: [ep(1)], onchange });
  await fireEvent.click(screen.getByRole('button', { name: /S11E01/ }));
  const chip = await screen.findByRole('button', { name: /소나기 ×3/ });
  expect(chip).toHaveClass('learning');
  await fireEvent.click(chip);
  await fireEvent.click(await screen.findByRole('button', { name: 'Know' }));
  await waitFor(() => expect(screen.queryByRole('button', { name: /소나기/ })).toBeNull());
  expect(onchange).toHaveBeenCalledOnce();
  const ev = api.mock.calls.find((c) => new URL((c[0] as Request).url).pathname === '/api/knowledge/events');
  expect(JSON.parse(await (ev?.[0] as Request).clone().text())).toEqual({ language: 'ko', lemma: '소나기', kind: 'marked_known' });
});

it('closing an episode hides its words', async () => {
  mockApi({ 'GET /api/library/items/1/words': () => ({ json: [] }) });
  render(EpisodeList, { language: 'ko', episodes: [ep(1)], onchange: vi.fn() });
  const row = screen.getByRole('button', { name: /S11E01/ });
  await fireEvent.click(row);
  expect(await screen.findByText('No new words in this episode.')).toBeInTheDocument();
  await fireEvent.click(row);
  expect(screen.queryByTestId('episode-words')).toBeNull();
});
