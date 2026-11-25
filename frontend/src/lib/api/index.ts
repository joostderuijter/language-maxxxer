/** Typed API client, generated from the backend's OpenAPI schema (ADR-7). Never call fetch on /api by hand. */
import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

export type Progress = components['schemas']['Progress'];
export type AnalyzedToken = components['schemas']['AnalyzedToken'];
export type WordState = components['schemas']['WordState'];
export type EventKind = components['schemas']['EventKind'];
export type ImportResult = components['schemas']['ImportResult'];
export type Lookup = components['schemas']['LookupResponse'];
export type Analysis = components['schemas']['AnalyzeResponse'];
export type SentenceInfo = components['schemas']['SentenceOut'];
export type LibraryStatus = components['schemas']['LibraryStatus'];
export type SeriesInfo = components['schemas']['SeriesOut'];
export type Episode = components['schemas']['ItemOut'];
export type NewWord = components['schemas']['NewWordOut'];
export type Sense = components['schemas']['SenseOut'];

// fetch is looked up per call (not captured at import), so tests can stub globalThis.fetch
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '', // same origin as the page (the API serves the frontend)
  fetch: (req) => globalThis.fetch(req)
});

export class ApiError extends Error {}

function unwrap<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined) {
    const detail = (r.error as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(typeof detail === 'string' ? detail : `request failed (${r.response.status})`);
  }
  return r.data;
}

export async function getProgress(code: string): Promise<Progress> {
  return unwrap(await api.GET('/api/progress/{code}', { params: { path: { code } } }));
}

export async function analyze(language: string, text: string): Promise<Analysis> {
  return unwrap(await api.POST('/api/analyze', { body: { language, text } }));
}

export async function markWord(language: string, lemma: string, kind: EventKind): Promise<WordState> {
  return unwrap(await api.POST('/api/knowledge/events', { body: { language, lemma, kind } })).state;
}

export async function importWords(language: string, csv: string): Promise<ImportResult> {
  return unwrap(await api.POST('/api/knowledge/import', { body: { language, csv, source: 'import:csv' } }));
}

/** Meanings of the first candidate (most specific first) the dictionary knows. */
export async function lookup(language: string, lemmas: string[]): Promise<Lookup> {
  return unwrap(await api.GET('/api/dictionary/{code}', { params: { path: { code: language }, query: { lemma: lemmas } } }));
}

export async function libraryStatus(): Promise<LibraryStatus> {
  return unwrap(await api.GET('/api/library/status'));
}

export async function librarySync(): Promise<void> {
  unwrap(await api.POST('/api/library/sync'));
}

export async function librarySeries(): Promise<SeriesInfo[]> {
  return unwrap(await api.GET('/api/library/series'));
}

export async function seriesEpisodes(key: string): Promise<Episode[]> {
  return unwrap(await api.GET('/api/library/series/{key}', { params: { path: { key } } }));
}

export async function episodeWords(id: number, limit = 30): Promise<NewWord[]> {
  return unwrap(await api.GET('/api/library/items/{item_id}/words', { params: { path: { item_id: id }, query: { limit } } }));
}
