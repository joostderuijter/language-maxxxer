<script lang="ts">
  import { lookup, type AnalyzedToken, type EventKind, type Lookup } from './api';

  let { language, token, onmark }: { language: string; token: AnalyzedToken; onmark: (kind: EventKind) => void } =
    $props();

  let result = $state<Lookup | null>(null);
  let error = $state('');
  let showIdioms = $state(false);
  const LEVEL: Record<string, string> = { beginner: 'beginner', intermediate: 'intermediate', advanced: 'advanced' };

  $effect(() => {
    const lemmas = token.lemmas;
    result = null;
    error = '';
    showIdioms = false;
    lookup(language, lemmas)
      .then((r) => {
        if (token.lemmas === lemmas) result = r; // ignore a late answer for a word no longer selected
      })
      .catch((e: unknown) => (error = e instanceof Error ? e.message : String(e)));
  });
</script>

<div class="panel" data-testid="word-panel">
  <div class="head">
    <b class="lemma">{result?.lemma ?? token.lemma}</b>
    <span class="muted">{token.pos} · {token.state}</span>
  </div>

  {#if error}
    <p role="alert">{error}</p>
  {:else if !result}
    <p class="muted">Looking up…</p>
  {:else if result.senses.length === 0}
    <p class="muted" data-testid="no-entry">Not in the dictionary.</p>
  {:else}
    <ol class="senses">
      {#each result.senses.slice(0, 5) as s, i (i)}
        <li>
          <b>{s.gloss || s.definition}</b>
          {#if s.level}<span class="tag">{LEVEL[s.level] ?? s.level}</span>{/if}
          {#if s.origin}<span class="tag">{s.origin}</span>{/if}
          {#if s.gloss && s.definition}<div class="def">{s.definition}</div>{/if}
          {#if s.examples[0]}<div class="ex">{s.examples[0]}</div>{/if}
        </li>
      {/each}
    </ol>
    {#if result.senses.length > 5}<p class="muted">+{result.senses.length - 5} more meanings</p>{/if}
    {#if result.idioms.length}
      <button type="button" class="link" onclick={() => (showIdioms = !showIdioms)}>
        {showIdioms ? 'Hide' : 'Show'} {result.idioms.length} idiom{result.idioms.length === 1 ? '' : 's'}
      </button>
      {#if showIdioms}
        <ul class="idioms">
          {#each result.idioms as idiom, i (i)}
            <li><b>{idiom.text}</b> <span class="muted">{idiom.gloss || idiom.definition || idiom.native}</span></li>
          {/each}
        </ul>
      {/if}
    {/if}
  {/if}

  <div class="actions">
    <button type="button" onclick={() => onmark('marked_known')}>Know</button>
    <button type="button" onclick={() => onmark('ignored')}>Ignore</button>
    {#if token.state !== 'unknown'}<button type="button" onclick={() => onmark('marked_unknown')}>Reset</button>{/if}
  </div>
</div>

<style>
  .panel { border-top: 1px solid var(--box); padding-top: 10px; display: grid; gap: 8px; }
  .lemma { font-size: 20px; }
  .muted { color: var(--muted); font-size: 13px; }
  .senses { margin: 0; padding-left: 20px; display: grid; gap: 6px; }
  .def { color: var(--muted); font-size: 13px; }
  .ex { font-size: 14px; margin-top: 2px; }
  .tag { font-size: 11px; background: var(--box); border-radius: 99px; padding: 1px 7px; margin-left: 4px; }
  .idioms { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
  .link { background: none; color: var(--muted); padding: 0; font-weight: 400; justify-self: start; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
