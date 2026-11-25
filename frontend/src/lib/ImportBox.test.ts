import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import ImportBox from './ImportBox.svelte';
import { bodyOf, mockApi } from './test-utils';

afterEach(() => vi.unstubAllGlobals());

it('imports, reports and clears', async () => {
  const api = mockApi({ 'POST /api/knowledge/import': () => ({ json: { imported: 2, skipped: 1 } }) });
  const onimported = vi.fn();
  render(ImportBox, { language: 'ko', onimported });
  const box = screen.getByRole('textbox');
  await fireEvent.input(box, { target: { value: '먹다,known\n가다,2\nx,bogus' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Import' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Imported 2 words (1 lines skipped)'));
  expect(onimported).toHaveBeenCalledOnce();
  expect(box).toHaveValue('');
  expect(await bodyOf(api, 0)).toEqual({ language: 'ko', csv: '먹다,known\n가다,2\nx,bogus', source: 'import:csv' });
});

it('shows an error and keeps the text', async () => {
  mockApi({ 'POST /api/knowledge/import': () => ({ status: 500, json: {} }) });
  render(ImportBox, { language: 'ko', onimported: vi.fn() });
  await fireEvent.input(screen.getByRole('textbox'), { target: { value: '먹다,known' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Import' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('request failed (500)'));
  expect(screen.getByRole('textbox')).toHaveValue('먹다,known');
});
