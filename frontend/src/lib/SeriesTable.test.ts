import { render, screen } from '@testing-library/svelte';
import { expect, it } from 'vitest';
import SeriesTable from './SeriesTable.svelte';

it('lists shows with coverage and links to them', () => {
  render(SeriesTable, {
    series: [
      { key: 'runningman', series: 'Running Man', items: 51, analyzed: 50, coverage: 0.9634, one_new: 812 },
      { key: '나혼자산다', series: '나 혼자 산다', items: 3, analyzed: 0, coverage: null, one_new: 0 }
    ]
  });
  const link = screen.getByRole('link', { name: /Running Man/ });
  expect(link).toHaveAttribute('href', '/library/runningman');
  expect(link).toHaveTextContent('50/51 episodes analysed · 812 one-new-word sentences');
  expect(screen.getByText('96%')).toBeInTheDocument();
  expect(screen.getByText('–')).toBeInTheDocument(); // nothing analysed yet
});

it('says when there is nothing', () => {
  render(SeriesTable, { series: [] });
  expect(screen.getByTestId('no-series')).toBeInTheDocument();
});
