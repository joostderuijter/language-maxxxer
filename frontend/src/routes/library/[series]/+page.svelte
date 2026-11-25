<script lang="ts">
  import { page } from '$app/state';
  import { seriesEpisodes, type Episode } from '#lib/api/index.ts';
  import EpisodeList from '#lib/EpisodeList.svelte';

  const name = $derived(page.params.series ?? '');
  let episodes = $state<Episode[]>([]);
  let error = $state('');

  async function refresh() {
    try {
      episodes = await seriesEpisodes(name);
      error = '';
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  $effect(() => {
    void name;
    refresh();
  });
</script>

<p><a href="/library">← Library</a></p>
<h1>{name}</h1>
{#if error}<p role="alert">{error}</p>{/if}
<EpisodeList language="ko" {episodes} onchange={refresh} />

<style>
  h1 { font-size: 22px; margin: 0; }
  p { margin: 4px 0 0; }
  a { color: var(--muted); }
</style>
