<script lang="ts">
  import { analyze, markWord, type AnalyzedToken, type EventKind } from './api';
  import { segments } from './segments';
  import WordPanel from './WordPanel.svelte';

  let { language, onchange }: { language: string; onchange: () => void } = $props();
  let text = $state('');
  let tokens = $state<AnalyzedToken[]>([]);
  let shown = $state('');
  let selected = $state<AnalyzedToken | null>(null);
  let error = $state('');

  async function run(e?: SubmitEvent) {
    e?.preventDefault();
    error = '';
    try {
      tokens = await analyze(language, text);
      shown = text;
      selected = null;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  async function mark(kind: EventKind) {
    if (!selected) return;
    await markWord(language, selected.lemma, kind);
    onchange();
    await run();
  }
</script>

<form onsubmit={run} class="card">
  <label for="text">Paste some Korean</label>
  <textarea id="text" bind:value={text} rows="3" placeholder="오늘은 날씨가 정말 좋네요."></textarea>
  <div><button type="submit" disabled={!text.trim()}>Analyse</button></div>
  {#if error}<p role="alert">{error}</p>{/if}
  {#if tokens.length || shown}
    <p class="text" data-testid="analysed">
      {#each segments(shown, tokens) as seg, i (i)}
        {#if seg.token}
          <button type="button" class="word {seg.token.state}" class:weak={seg.token.weak}
                  aria-pressed={selected === seg.token} onclick={() => (selected = seg.token)}>{seg.text}</button>
        {:else}{seg.text}{/if}
      {/each}
    </p>
  {/if}
  {#if selected}
    <WordPanel {language} token={selected} onmark={mark} />
  {/if}
</form>

<style>
  .card { background: var(--card); border-radius: 14px; padding: 14px 16px; display: grid; gap: 8px; }
  .text { font-size: 20px; line-height: 1.9; margin: 4px 0 0; white-space: pre-wrap; }
  .word { all: unset; cursor: pointer; border-radius: 4px; padding: 0 1px; }
  .word.unknown, .word.seen { border-bottom: 2px solid var(--accent); }
  .word.learning { border-bottom: 2px dashed var(--accent); }
  .word.ignored, .word.weak.unknown { color: var(--muted); border-bottom: 0; }
  .word[aria-pressed='true'] { background: var(--box); }
</style>
