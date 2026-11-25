<script lang="ts">
  let { children } = $props();
</script>

<main>{@render children()}</main>
<footer>
  Korean dictionary: <a href="https://krdict.korean.go.kr" rel="noreferrer">한국어기초사전 (KRDict)</a>, National Institute of
  Korean Language, CC BY-SA 3.0
</footer>

<style>
  :global(:root) {
    --bg: #f7f6f3; --card: #ffffff; --box: #ecebe7; --text: #1c1c1e; --muted: #6b6b70; --accent: #e5533d; --learning: #d99a00; --t1: rgba(46, 158, 91, 0.16);
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :global(:root) { --bg: #1c1c1e; --card: #2b2b2d; --box: #3a3a3c; --text: #f0f0f0; --muted: #a0a0a5; --learning: #f2c12e; --t1: rgba(46, 158, 91, 0.28); color-scheme: dark; }
  }
  :global(body) {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.45 -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  }
  :global(textarea) {
    width: 100%; box-sizing: border-box; font: inherit; border-radius: 10px; padding: 10px;
    border: 1px solid var(--box); background: var(--bg); color: var(--text);
  }
  :global(button) {
    font: 600 14px/1 inherit; border: 0; border-radius: 10px; padding: 9px 14px; cursor: pointer;
    background: var(--accent); color: #fff;
  }
  :global(button:disabled) { opacity: 0.45; cursor: default; }
  footer { max-width: 760px; margin: 0 auto; padding: 0 16px 24px; color: var(--muted); font-size: 12px; }
  footer a { color: inherit; }
  main { max-width: 760px; margin: 0 auto; padding: 16px 16px calc(24px + env(safe-area-inset-bottom)); display: grid; gap: 14px; }
</style>
