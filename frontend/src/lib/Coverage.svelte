<script lang="ts">
  import { band, pct } from './format';
  let { value }: { value: number | null | undefined } = $props();
</script>

<span class="cov {band(value)}" title="words you know">
  <span class="bar"><i style="width: {Math.round((value ?? 0) * 100)}%"></i></span>
  <b>{pct(value)}</b>
</span>

<style>
  .cov { display: inline-flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .bar { width: 56px; height: 6px; background: var(--box); border-radius: 3px; overflow: hidden; display: inline-block; }
  .bar i { display: block; height: 100%; background: var(--muted); }
  .easy .bar i { background: #2e9e5b; }
  .sweet .bar i { background: #2e9e5b; }
  .sweet b { color: #2e9e5b; }
  .hard .bar i { background: var(--learning); }
  .too-hard .bar i { background: var(--accent); }
  .none b { color: var(--muted); font-weight: 400; }
</style>
