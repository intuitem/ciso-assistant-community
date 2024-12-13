<script>
	import { languageTag, onSetLanguageTag, setLanguageTag } from '$paraglide/runtime';
	import { onDestroy, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { getCookie, deleteCookie, setCookie } from '$lib/utils/cookies';
	import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

	onMount(() => {
		// const valueFromSession = sessionStorage.getItem('lang') || DEFAULT_LANGUAGE;
		const valueFromCookies = getCookie('ciso_lang') || DEFAULT_LANGUAGE;
		// @ts-ignore
		setCookie('ciso_lang', valueFromCookies);
		setLanguageTag(valueFromCookies);
	});

	onDestroy(() => {
		if (browser) {
			deleteCookie('ciso_lang');
			// sessionStorage.removeItem('lang');
		}
	});

	// initialize the language tag
	$: _languageTag = languageTag;

	onSetLanguageTag((newLanguageTag) => {
		// @ts-ignore
		_languageTag = newLanguageTag;
	});
</script>

{#key _languageTag}
	<slot />
{/key}
