import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import type { AnalyzedToken, Sense } from './api';
import { mockApi } from './test-utils';
import WordPanel from './WordPanel.svelte';

afterEach(() => vi.unstubAllGlobals());

const token: AnalyzedToken = {
  surface: '눈이', start: 0, end: 2, lemmas: ['눈'], pos: 'noun', key: '눈', weak: false, state: 'unknown', lemma: '눈'
};
const sense = (gloss: string, extra: Partial<Sense> = {}): Sense => ({
  headword: '눈', pos: 'noun', gloss, definition: `${gloss} definition`, native: '', level: '', origin: '',
  pronunciation: '', examples: [], ...extra
});

it('shows meanings, level, origin and an example', async () => {
  const api = mockApi({
    'GET /api/dictionary/ko': () => ({
      json: { lemma: '눈', idioms: [], senses: [sense('eye', { level: 'beginner', examples: ['눈이 크다.'] }), sense('snow', { origin: '雪' })] }
    })
  });
  render(WordPanel, { language: 'ko', token, onmark: vi.fn() });
  await waitFor(() => expect(screen.getByText('eye')).toBeInTheDocument());
  expect(screen.getByText('snow')).toBeInTheDocument();
  expect(screen.getByText('beginner')).toBeInTheDocument();
  expect(screen.getByText('雪')).toBeInTheDocument();
  expect(screen.getByText('눈이 크다.')).toBeInTheDocument();
  expect(new URL((api.mock.calls[0]?.[0] as Request).url).searchParams.getAll('lemma')).toEqual(['눈']);
});

it('says when a word is not in the dictionary', async () => {
  mockApi({ 'GET /api/dictionary/ko': () => ({ json: { lemma: '눈', senses: [], idioms: [] } }) });
  render(WordPanel, { language: 'ko', token, onmark: vi.fn() });
  await waitFor(() => expect(screen.getByTestId('no-entry')).toBeInTheDocument());
});

it('idioms are folded away until asked for', async () => {
  mockApi({
    'GET /api/dictionary/ko': () => ({
      json: { lemma: '눈', senses: [sense('eye')], idioms: [{ text: '눈이 높다', kind: 'idiom', gloss: 'have high standards', definition: '', native: '' }] }
    })
  });
  render(WordPanel, { language: 'ko', token, onmark: vi.fn() });
  const toggle = await screen.findByRole('button', { name: 'Show 1 idiom' });
  expect(screen.queryByText('눈이 높다')).toBeNull();
  await fireEvent.click(toggle);
  expect(screen.getByText('눈이 높다')).toBeInTheDocument();
  expect(screen.getByText('have high standards')).toBeInTheDocument();
});

it('shows at most 5 meanings', async () => {
  mockApi({ 'GET /api/dictionary/ko': () => ({ json: { lemma: '눈', idioms: [], senses: ['a', 'b', 'c', 'd', 'e', 'f', 'g'].map((g) => sense(g)) } }) });
  render(WordPanel, { language: 'ko', token, onmark: vi.fn() });
  await waitFor(() => expect(screen.getByText('+2 more meanings')).toBeInTheDocument());
  expect(screen.queryByText('f')).toBeNull();
});

it('buttons report the chosen action', async () => {
  mockApi({ 'GET /api/dictionary/ko': () => ({ json: { lemma: '눈', senses: [], idioms: [] } }) });
  const onmark = vi.fn();
  render(WordPanel, { language: 'ko', token: { ...token, state: 'known' }, onmark });
  await fireEvent.click(screen.getByRole('button', { name: 'Ignore' }));
  await fireEvent.click(screen.getByRole('button', { name: 'Reset' }));
  expect(onmark.mock.calls).toEqual([['ignored'], ['marked_unknown']]);
});

it('shows a lookup error', async () => {
  mockApi({ 'GET /api/dictionary/ko': () => ({ status: 500, json: {} }) });
  render(WordPanel, { language: 'ko', token, onmark: vi.fn() });
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('request failed (500)'));
});
