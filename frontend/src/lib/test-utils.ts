import { vi } from 'vitest';

type Handler = (body: unknown) => { status?: number; json: unknown };

/** Stub fetch with handlers per "METHOD /path". Returns the mock, so tests can inspect the calls. */
export function mockApi(routes: Record<string, Handler>) {
  const mock = vi.fn(async (req: Request) => {
    const url = new URL(req.url);
    const key = `${req.method} ${url.pathname}`;
    const handler = routes[key];
    if (!handler) throw new Error(`unexpected request ${key}`);
    const text = await req.clone().text(); // leave the original readable for bodyOf()
    const { status = 200, json } = handler(text ? JSON.parse(text) : undefined);
    return new Response(JSON.stringify(json), { status, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', mock);
  return mock;
}

export async function bodyOf(mock: ReturnType<typeof mockApi>, call: number): Promise<unknown> {
  const req = mock.mock.calls[call]?.[0] as Request;
  return JSON.parse(await req.clone().text());
}
