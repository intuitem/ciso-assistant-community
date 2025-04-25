<script>
	import { getLocale, overwriteSetLocale, setLocale } from '$paraglide/runtime';
	import { onDestroy, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { getCookie, deleteCookie, setCookie } from '$lib/utils/cookies';
	import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

	onMount(() => {
		// const valueFromSession = sessionStorage.getItem('lang') || DEFAULT_LANGUAGE;
		const valueFromCookies = getCookie('PARAGLIDE_LOCALE') || DEFAULT_LANGUAGE;
		// @ts-ignore
		setCookie('PARAGLIDE_LOCALE', valueFromCookies);
		setLocale(valueFromCookies);
	});

	onDestroy(() => {
		if (browser) {
			deleteCookie('PARAGLIDE_LOCALE');
			// sessionStorage.removeItem('lang');
		}
	});

	// initialize the language tag
	$: _languageTag = getLocale;

	overwriteSetLocale((newLanguageTag) => {
		// @ts-ignore
		_languageTag = newLanguageTag;
	});
</script>

{#key _languageTag}
	<slot />
{/key}
