import { render, screen, within } from '@testing-library/svelte';
import { expect, it } from 'vitest';
import type { NextItem } from './api';
import NextUp from './NextUp.svelte';

const item = (id: number, extra: Partial<NextItem> = {}): NextItem => ({
  id, series: 'Running Man', series_key: 'runningman', season: 11, episode: id, title: `Episode ${id}`, coverage: 0.96,
  new_words: 12, one_new: 340, score: 0.9, reasons: ['96% known', '340 sentences with one new word'],
  open_url: `https://tv.example/web/#/details?id=j${id}`, ...extra
});

it('lists recommendations with reasons and actions', () => {
  render(NextUp, { items: [item(1), item(2, { open_url: null, reasons: ['80% known (a stretch)'] })] });
  const [first, second] = within(screen.getByLabelText('next up')).getAllByRole('listitem');
  expect(first).toHaveTextContent('Running Man');
  expect(first).toHaveTextContent('S11E01 · Episode 1');
  expect(first).toHaveTextContent('96% known · 340 sentences with one new word');
  expect(within(first!).getByRole('link', { name: 'Open in Jellyfin' })).toHaveAttribute('href', 'https://tv.example/web/#/details?id=j1');
  expect(within(first!).getByRole('link', { name: 'Words to learn' })).toHaveAttribute('href', '/library/runningman');
  expect(within(second!).queryByRole('link', { name: 'Open in Jellyfin' })).toBeNull(); // no public Jellyfin URL
});

it('explains an empty list', () => {
  render(NextUp, { items: [] });
  expect(screen.getByTestId('next-empty')).toBeInTheDocument();
});
