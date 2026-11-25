<script lang="ts">
  import { episodeWords, markWord, type AnalyzedToken, type Episode, type EventKind, type NewWord } from './api';
  import Coverage from './Coverage.svelte';
  import { episodeLabel } from './format';
  import WordPanel from './WordPanel.svelte';

  let { language, episodes, onchange }: { language: string; episodes: Episode[]; onchange: () => void } = $props();
  let open = $state<number | null>(null);
  let words = $state<NewWord[]>([]);
  let selected = $state<AnalyzedToken | null>(null);
  let error = $state('');

  const STATUS: Record<string, string> = { new: 'waiting to be analysed', no_subtitles: 'no Korean subtitles', error: 'error' };

  async function load(id: number) {
    error = '';
    try {
      words = await episodeWords(id);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function toggle(ep: Episode) {
    selected = null;
    if (open === ep.id) {
      open = null;
      return;
    }
    open = ep.id;
    words = [];
    await load(ep.id);
  }

  // a word from the episode list, shaped like an analysed token so the word panel can show it
  function asToken(w: NewWord): AnalyzedToken {
    return { surface: w.key, start: 0, end: 0, lemmas: w.lemmas, pos: '', key: w.key, weak: false,
             state: w.state as AnalyzedToken['state'], lemma: w.lemmas[0] ?? w.key };
  }

  async function mark(kind: EventKind) {
    if (!selected || open === null) return;
    await markWord(language, selected.lemma, kind);
    selected = null;
    await load(open);
    onchange();
  }
</script>

<ul class="list" aria-label="episodes">
  {#each episodes as ep (ep.id)}
    <li>
      <button type="button" class="row" aria-expanded={open === ep.id} onclick={() => toggle(ep)}
              disabled={ep.status !== 'analyzed'}>
        <span class="label">{episodeLabel(ep.season, ep.episode)}</span>
        <span class="title">{ep.title}</span>
        {#if ep.status === 'analyzed'}
          <span class="muted">{ep.new_words} new · {ep.one_new} one-new</span>
          <Coverage value={ep.coverage} />
        {:else}
          <span class="muted status">{STATUS[ep.status] ?? ep.status}</span>
        {/if}
      </button>
      {#if open === ep.id}
        <div class="words" data-testid="episode-words">
          {#if error}<p role="alert">{error}</p>{/if}
          {#if words.length === 0 && !error}<p class="muted">No new words in this episode.</p>{/if}
          <p class="muted">New words, most frequent first: learning these first helps most.</p>
          <div class="chips">
            {#each words as w (w.key)}
              <button type="button" class="chip {w.state}" aria-pressed={selected?.key === w.key}
                      onclick={() => (selected = asToken(w))}>{w.lemmas[0] ?? w.key} <small>×{w.count}</small></button>
            {/each}
          </div>
          {#if selected}<WordPanel {language} token={selected} onmark={mark} />{/if}
        </div>
      {/if}
    </li>
  {/each}
</ul>

<style>
  .list { list-style: none; margin: 0; padding: 0; background: var(--card); border-radius: 14px; overflow: hidden; }
  li { border-top: 1px solid var(--box); }
  li:first-child { border-top: 0; }
  .row { all: unset; box-sizing: border-box; width: 100%; display: flex; align-items: center; gap: 10px; padding: 11px 16px;
         cursor: pointer; flex-wrap: wrap; }
  .row:disabled { cursor: default; opacity: 0.6; }
  .label { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 13px; min-width: 58px; }
  .title { flex: 1; min-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .muted { color: var(--muted); font-size: 13px; }
  .words { padding: 0 16px 14px; display: grid; gap: 8px; }
  .words p { margin: 0; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { background: var(--box); color: var(--text); font-weight: 500; padding: 6px 10px; border-bottom: 2px solid var(--accent); }
  .chip.learning { border-bottom: 2px dashed var(--learning); }
  .chip[aria-pressed='true'] { outline: 2px solid var(--accent); }
  .chip small { color: var(--muted); font-weight: 400; }
</style>
