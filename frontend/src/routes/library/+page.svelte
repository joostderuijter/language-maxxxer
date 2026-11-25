<script lang="ts">
  import { onMount } from 'svelte';
  import { libraryStatus, librarySeries, librarySync, type LibraryStatus, type SeriesInfo } from '#lib/api/index.ts';
  import SeriesTable from '#lib/SeriesTable.svelte';

  let status = $state<LibraryStatus | null>(null);
  let series = $state<SeriesInfo[]>([]);
  let error = $state('');
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function refresh() {
    clearTimeout(timer);
    try {
      [status, series] = await Promise.all([libraryStatus(), librarySeries()]);
      error = '';
      if (status.running || status.stats_pending) timer = setTimeout(refresh, 3000); // follow progress while it works
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function sync() {
    await librarySync();
    setTimeout(refresh, 500);
  }

  onMount(() => {
    refresh();
    return () => clearTimeout(timer);
  });
</script>

<h1>Library</h1>
{#if error}<p role="alert">{error}</p>{/if}
{#if status && !status.enabled}
  <p class="card" data-testid="library-disabled">The library isn't connected to Jellyfin yet (set <code>LMX_JELLYFIN_API_KEY</code>).</p>
{:else if status}
  <div class="status" data-testid="library-status">
    <span>
      {status.items['analyzed'] ?? 0} episodes analysed{status.items['new'] ? ` · ${status.items['new']} waiting` : ''}{status.items['no_subtitles']
        ? ` · ${status.items['no_subtitles']} without Korean subtitles`
        : ''}
    </span>
    {#if status.running}<span class="muted">working{status.current ? `: ${status.current}` : '…'}</span>
    {:else}<button type="button" onclick={sync}>Sync with Jellyfin</button>{/if}
    {#if status.stats_pending}<span class="muted">updating coverage for {status.stats_pending} episodes…</span>{/if}
    {#if status.error}<span role="alert">{status.error}</span>{/if}
  </div>
  <SeriesTable {series} />
{/if}

<style>
  h1 { font-size: 22px; margin: 8px 0 0; }
  .status { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 14px; }
  .muted { color: var(--muted); }
  .card { background: var(--card); border-radius: 14px; padding: 14px 16px; }
</style>
