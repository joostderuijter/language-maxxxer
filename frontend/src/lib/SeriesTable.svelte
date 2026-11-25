<script lang="ts">
  import type { SeriesInfo } from './api';
  import Coverage from './Coverage.svelte';

  let { series }: { series: SeriesInfo[] } = $props();
</script>

{#if series.length === 0}
  <p class="muted" data-testid="no-series">No Korean shows found yet.</p>
{:else}
  <ul class="list" aria-label="shows">
    {#each series as s (s.key)}
      <li>
        <a href={`/library/${encodeURIComponent(s.key)}`}>
          <span class="name">{s.series}</span>
          <span class="muted">{s.analyzed}/{s.items} episodes analysed{s.one_new ? ` · ${s.one_new} one-new-word sentences` : ''}</span>
        </a>
        <Coverage value={s.coverage} />
      </li>
    {/each}
  </ul>
{/if}

<style>
  .list { list-style: none; margin: 0; padding: 0; background: var(--card); border-radius: 14px; overflow: hidden; }
  li { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-top: 1px solid var(--box); }
  li:first-child { border-top: 0; }
  a { flex: 1; min-width: 0; color: inherit; text-decoration: none; display: grid; }
  .name { font-weight: 600; }
  .muted { color: var(--muted); font-size: 13px; }
</style>
