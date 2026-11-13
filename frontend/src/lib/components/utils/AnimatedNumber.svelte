<script lang="ts">
	import { onMount } from 'svelte';
	import NumberFlow from '@number-flow/svelte';
	import { getLocale } from '#paraglide/runtime.js';

	interface Props {
		value: number;
		format?: Intl.NumberFormatOptions;
		/** Roll up from 0 once when first shown; otherwise only changes animate. */
		countUp?: boolean;
	}

	let { value, format, countUp = false }: Props = $props();

	// NumberFlow has no RTL / non-Latin digit support: those locales get the plain number.
	const RTL_LOCALES = ['ar', 'ur'];
	const locale = $derived(getLocale());

	let mounted = $state(false);
	onMount(() => requestAnimationFrame(() => (mounted = true)));
	const shown = $derived(countUp && !mounted ? 0 : value);
</script>

{#if RTL_LOCALES.includes(locale)}
	{value.toLocaleString(locale, format)}
{:else}
	<NumberFlow value={shown} locales={locale} {format} />
{/if}
