import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import Analyzer from './Analyzer.svelte';
import type { AnalyzedToken } from './api';
import { bodyOf, mockApi } from './test-utils';

const tok = (surface: string, start: number, state: AnalyzedToken['state'], lemma = surface): AnalyzedToken => ({
  surface, start, end: start + surface.length, lemmas: [lemma], pos: 'verb', key: lemma, weak: false, state, lemma
});

afterEach(() => vi.unstubAllGlobals());

it('analyses text, marks a word known and re-analyses', async () => {
  let known = false;
  const api = mockApi({
    'POST /api/analyze': () => ({
      json: { language: 'ko', tokens: [tok('밥을', 0, 'unknown', '밥'), tok('먹고', 3, known ? 'known' : 'unknown', '먹다')],
              sentences: [{ start: 0, end: 5, unknown: known ? 1 : 2 }] }
    }),
    'POST /api/knowledge/events': () => { known = true; return { json: { lemma: '먹다', state: 'known', confidence: 0.9 } }; },
    'GET /api/dictionary/ko': () => ({ json: { lemma: '먹다', idioms: [], senses: [{ headword: '먹다', pos: 'verb', gloss: 'eat',
      definition: '', native: '', level: 'beginner', origin: '', pronunciation: '', examples: [] }] } })
  });
  const onchange = vi.fn();
  render(Analyzer, { language: 'ko', onchange });

  await fireEvent.input(screen.getByLabelText('Paste some Korean'), { target: { value: '밥을 먹고' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
  await waitFor(() => expect(screen.getByTestId('analysed')).toHaveTextContent('밥을 먹고'));
  const word = screen.getByRole('button', { name: '먹고' });
  expect(word).toHaveClass('unknown');

  await fireEvent.click(word);
  expect(screen.getByTestId('word-panel')).toHaveTextContent('먹다');
  await waitFor(() => expect(screen.getByTestId('word-panel')).toHaveTextContent('eat'));
  await fireEvent.click(screen.getByRole('button', { name: 'Know' }));

  await waitFor(() => expect(screen.getByRole('button', { name: '먹고' })).toHaveClass('known'));
  // now only 밥 is new: the sentence is a 1T sentence
  expect(screen.getByRole('button', { name: '먹고' }).closest('.sentence')).toHaveClass('t1');
  expect(screen.getByTestId('legend')).toHaveTextContent('1 of 1 sentences');
  expect(onchange).toHaveBeenCalledOnce();
  const events = api.mock.calls.findIndex((c) => new URL((c[0] as Request).url).pathname === '/api/knowledge/events');
  expect(await bodyOf(api, events)).toEqual({ language: 'ko', lemma: '먹다', kind: 'marked_known' });
  expect(screen.queryByTestId('word-panel')).toBeNull();
});

it('shows the server error', async () => {
  mockApi({ 'POST /api/analyze': () => ({ status: 404, json: { detail: "unknown language 'xx'" } }) });
  render(Analyzer, { language: 'xx', onchange: vi.fn() });
  await fireEvent.input(screen.getByLabelText('Paste some Korean'), { target: { value: '안녕' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent("unknown language 'xx'"));
});

it('analyse is disabled for empty text', () => {
  render(Analyzer, { language: 'ko', onchange: vi.fn() });
  expect(screen.getByRole('button', { name: 'Analyse' })).toBeDisabled();
});

it('highlights only sentences with exactly one new word, and colours learning words differently', async () => {
  mockApi({
    'POST /api/analyze': () => ({
      json: {
        language: 'ko',
        tokens: [tok('가', 0, 'unknown'), tok('나', 3, 'learning'), tok('다', 5, 'unknown'), tok('라', 8, 'known')],
        sentences: [{ start: 0, end: 2, unknown: 1 }, { start: 3, end: 7, unknown: 2 }, { start: 8, end: 10, unknown: 0 }]
      }
    })
  });
  render(Analyzer, { language: 'ko', onchange: vi.fn() });
  await fireEvent.input(screen.getByLabelText('Paste some Korean'), { target: { value: '가. 나 다. 라.' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
  await waitFor(() => expect(screen.getByTestId('analysed')).toHaveTextContent('가. 나 다. 라.'));
  const sentenceOf = (w: string) => screen.getByRole('button', { name: w }).closest('.sentence');
  expect(sentenceOf('가')).toHaveClass('t1');
  expect(sentenceOf('나')).not.toHaveClass('t1');
  expect(sentenceOf('라')).not.toHaveClass('t1');
  expect(screen.getByRole('button', { name: '나' })).toHaveClass('learning');
  expect(screen.getByTestId('legend')).toHaveTextContent('1 of 3 sentences');
});
