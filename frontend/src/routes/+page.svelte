<script lang="ts">
  import { onMount } from 'svelte';
  import Analyzer from '#lib/Analyzer.svelte';
  import ImportBox from '#lib/ImportBox.svelte';
  import NextUp from '#lib/NextUp.svelte';
  import ProgressCard from '#lib/ProgressCard.svelte';
  import { getProgress, nextUp, type NextItem, type Progress } from '#lib/api/index.ts';

  const language = 'ko';
  let progress = $state<Progress | null>(null);
  let next = $state<NextItem[] | null>(null);
  let error = $state('');

  async function refresh() {
    try {
      [progress, next] = await Promise.all([getProgress(language), nextUp()]);
      error = '';
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
  }
  onMount(refresh);
</script>

<h1>language-maxxer <small>Korean</small></h1>
{#if error}<p role="alert">Can't reach the server: {error}</p>{/if}
{#if progress}<ProgressCard {progress} />{/if}
{#if next}<NextUp items={next} />{/if}
<Analyzer {language} onchange={refresh} />
<ImportBox {language} onimported={refresh} />

<style>
  h1 { font-size: 22px; margin: 8px 0 0; }
  small { color: var(--muted); font-weight: 400; font-size: 14px; }
</style>
