import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // a static single-page app, served by the FastAPI container (ADR-8)
  plugins: [sveltekit({ adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html' }) }), svelteTesting()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['src/test-setup.ts']
  }
});
