<script lang="ts">
  import { importWords } from './api';

  let { language, onimported }: { language: string; onimported: () => void } = $props();
  let csv = $state('');
  let busy = $state(false);
  let message = $state('');

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    message = '';
    try {
      const r = await importWords(language, csv);
      message = `Imported ${r.imported} words` + (r.skipped ? ` (${r.skipped} lines skipped)` : '');
      csv = '';
      onimported();
    } catch (err) {
      message = err instanceof Error ? err.message : String(err);
    } finally {
      busy = false;
    }
  }
</script>

<form onsubmit={submit} class="card">
  <label for="csv">Import a word list <span class="muted">(one "word,state" per line: known, learning, seen, ignored)</span></label>
  <textarea id="csv" bind:value={csv} rows="4" placeholder={'먹다,known\n가다,known'}></textarea>
  <div class="row">
    <button type="submit" disabled={busy || !csv.trim()}>{busy ? 'Importing…' : 'Import'}</button>
    {#if message}<span role="status">{message}</span>{/if}
  </div>
</form>

<style>
  .card { background: var(--card); border-radius: 14px; padding: 14px 16px; display: grid; gap: 8px; }
  .muted { color: var(--muted); font-weight: 400; font-size: 13px; }
  .row { display: flex; gap: 10px; align-items: center; }
</style>
