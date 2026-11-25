<script lang="ts">
  import { analyze, markWord, type Analysis, type AnalyzedToken, type EventKind } from './api';
  import { sentenceRuns } from './segments';
  import WordPanel from './WordPanel.svelte';

  let { language, onchange }: { language: string; onchange: () => void } = $props();
  let text = $state('');
  let result = $state<Analysis | null>(null);
  let shown = $state('');
  let selected = $state<AnalyzedToken | null>(null);
  let error = $state('');

  const runs = $derived(result ? sentenceRuns(shown, result.tokens, result.sentences) : []);
  const oneT = $derived(result ? result.sentences.filter((s) => s.unknown === 1).length : 0);

  async function run(e?: SubmitEvent) {
    e?.preventDefault();
    error = '';
    try {
      result = await analyze(language, text);
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
  {#if result}
    <p class="text" data-testid="analysed">
      {#each runs as r, ri (ri)}<span class="sentence" class:t1={r.sentence?.unknown === 1}
          data-unknown={r.sentence?.unknown}
          >{#each r.segments as seg, i (i)}{#if seg.token}<button type="button" class="word {seg.token.state}"
                class:weak={seg.token.weak} aria-pressed={selected === seg.token}
                onclick={() => (selected = seg.token)}>{seg.text}</button>{:else}{seg.text}{/if}{/each}</span
        >{/each}
    </p>
    <div class="legend" data-testid="legend">
      <span><i class="word unknown">new</i></span>
      <span><i class="word learning">learning</i></span>
      <span><i class="word known">known</i></span>
      <span><i class="word ignored">ignored</i></span>
      <span><i class="sentence t1">one new word</i> {oneT} of {result.sentences.length} sentences</span>
    </div>
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
  .word.learning { border-bottom: 2px dashed var(--learning); }
  .word.ignored, .word.weak.unknown { color: var(--muted); border-bottom: 0; }
  .word[aria-pressed='true'] { background: var(--box); }
  .sentence.t1 { background: var(--t1); border-radius: 6px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
  .legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: var(--muted); align-items: center; }
  .legend i { font-style: normal; cursor: default; padding: 0 3px; color: var(--text); }
</style>
