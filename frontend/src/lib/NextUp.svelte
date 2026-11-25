<script lang="ts">
  import type { NextItem } from './api';
  import Coverage from './Coverage.svelte';
  import { episodeLabel } from './format';

  let { items }: { items: NextItem[] } = $props();
</script>

<section class="card" aria-label="next up">
  <h2>Next up</h2>
  {#if items.length === 0}
    <p class="muted" data-testid="next-empty">
      Nothing to recommend yet: once the library has analysed episodes you haven't watched, the best ones for your level
      show up here.
    </p>
  {:else}
    <ol class="list">
      {#each items as n (n.id)}
        <li>
          <div class="head">
            <span class="show">{n.series}</span>
            <span class="muted">{episodeLabel(n.season, n.episode)} · {n.title}</span>
            <Coverage value={n.coverage} />
          </div>
          <div class="why">{n.reasons.join(' · ')}</div>
          <div class="actions">
            {#if n.open_url}<a class="btn" href={n.open_url} target="_blank" rel="noreferrer">Open in Jellyfin</a>{/if}
            <a class="btn ghost" href={`/library/${encodeURIComponent(n.series_key)}`}>Words to learn</a>
          </div>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .card { background: var(--card); border-radius: 14px; padding: 14px 16px; display: grid; gap: 8px; }
  h2 { font-size: 17px; margin: 0; }
  .list { margin: 0; padding: 0; list-style: none; display: grid; gap: 12px; }
  li { display: grid; gap: 4px; padding-top: 10px; border-top: 1px solid var(--box); }
  li:first-child { border-top: 0; padding-top: 0; }
  .head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .show { font-weight: 600; }
  .muted, .why { color: var(--muted); font-size: 13px; }
  .head .muted { flex: 1; min-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 2px; }
  .btn { font: 600 13px/1 inherit; border-radius: 10px; padding: 8px 12px; background: var(--accent); color: #fff; text-decoration: none; }
  .btn.ghost { background: var(--box); color: var(--text); }
</style>
