<script>
  import { languageTag, onSetLanguageTag, setLanguageTag, sourceLanguageTag } from '$paraglide/runtime';
  import { onDestroy, onMount } from 'svelte';
  import { browser } from '$app/environment';

  onMount(() => {
    const valueFromSession = sessionStorage.getItem('lang') || sourceLanguageTag;
    // @ts-ignore
    setLanguageTag(valueFromSession);
  })

  onDestroy(() => {
    if (browser) {
      sessionStorage.removeItem('lang');
    }
  })

  // initialize the language tag
  $: _languageTag = languageTag;

  onSetLanguageTag((newLanguageTag) => {
    // @ts-ignore
    _languageTag = newLanguageTag;
  });
</script>

{#key _languageTag}
  <slot></slot>
{/key}