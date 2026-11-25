import { render, screen } from '@testing-library/svelte';
import { expect, it } from 'vitest';
import ProgressCard from './ProgressCard.svelte';

it('shows words known and the other states', () => {
  render(ProgressCard, {
    progress: { language: 'ko', words_known: 6829, by_state: { known: 6829, learning: 35, seen: 2720, ignored: 131, unknown: 0 } }
  });
  expect(screen.getByTestId('words-known')).toHaveTextContent('6,829');
  expect(screen.getByLabelText('progress')).toHaveTextContent('35 learning · 2,720 seen · 131 ignored');
});

it('copes with missing states', () => {
  render(ProgressCard, { progress: { language: 'ko', words_known: 0, by_state: {} } });
  expect(screen.getByLabelText('progress')).toHaveTextContent('0 learning · 0 seen · 0 ignored');
});
