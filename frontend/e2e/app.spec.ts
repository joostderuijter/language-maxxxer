import { expect, test, type Page } from '@playwright/test';

// Runs against a real server (fresh or not): every test only checks CHANGES it causes itself.

async function wordsKnown(page: Page): Promise<number> {
  const el = page.getByTestId('words-known');
  await expect(el).toBeVisible();
  return Number((await el.textContent())?.replace(/,/g, ''));
}

test('landing page shows progress', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /language-maxxer/ })).toBeVisible();
  expect(await wordsKnown(page)).toBeGreaterThanOrEqual(0);
});

test('importing a word list raises words known', async ({ page }) => {
  await page.goto('/');
  const before = await wordsKnown(page);
  const words = Array.from({ length: 3 }, (_, i) => `e2e단어${Date.now()}${i},known`).join('\n');
  await page.getByLabel(/Import a word list/).fill(words);
  await page.getByRole('button', { name: 'Import' }).click();
  await expect(page.getByRole('status')).toHaveText('Imported 3 words');
  await expect.poll(() => wordsKnown(page)).toBe(before + 3);
});

test('analyse, then mark a word known', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Paste some Korean').fill('오늘은 날씨가 정말 좋네요.');
  await page.getByRole('button', { name: 'Analyse' }).click();
  const text = page.getByTestId('analysed');
  await expect(text).toHaveText('오늘은 날씨가 정말 좋네요.');
  const word = text.getByRole('button', { name: '날씨가' });
  if (!(await word.getAttribute('class'))?.includes('known')) {
    const before = await wordsKnown(page);
    await word.click();
    await expect(page.getByTestId('word-panel')).toContainText('날씨');
    await page.getByRole('button', { name: 'Know' }).click();
    await expect(text.getByRole('button', { name: '날씨가' })).toHaveClass(/known/);
    await expect.poll(() => wordsKnown(page)).toBe(before + 1);
  }
});

test('unknown pages show a not-found page with a way back', async ({ page }) => {
  const r = await page.goto('/some/route/that/does/not/exist');
  expect(r?.status()).toBe(200); // the server hands every path to the app; the app decides
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
  await page.getByRole('link', { name: 'Back to the start' }).click();
  await expect(page.getByRole('heading', { name: /language-maxxer/ })).toBeVisible();
});

test('no horizontal scrolling', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('words-known')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
