<script lang="ts">
  import type { Progress } from './api';

  let { progress }: { progress: Progress } = $props();
  const fmt = (n: number) => n.toLocaleString('en');
</script>

<section class="card" aria-label="progress">
  <div class="label">Words known</div>
  <div class="big" data-testid="words-known">{fmt(progress.words_known)}</div>
  <div class="small">
    {fmt(progress.by_state['learning'] ?? 0)} learning · {fmt(progress.by_state['seen'] ?? 0)} seen ·
    {fmt(progress.by_state['ignored'] ?? 0)} ignored
  </div>
</section>

<style>
  .card { background: var(--card); border-radius: 14px; padding: 16px 18px; }
  .label { color: var(--muted); font-size: 13px; }
  .big { font-size: 40px; font-weight: 700; line-height: 1.15; font-variant-numeric: tabular-nums; }
  .small { color: var(--muted); font-size: 13px; }
</style>
