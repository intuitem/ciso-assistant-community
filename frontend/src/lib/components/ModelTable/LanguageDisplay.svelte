<script lang="ts">
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants.js';
	interface Props {
		cell: Array<any>;
		[key: string]: any
	}

	let { cell, ...rest }: Props = $props();
	let display = $derived(cell.map((lang) => LOCALE_DISPLAY_MAP[lang]));
</script>

<span {...rest}>
	{#each display as lang}
		<p>{lang}</p>
	{/each}
</span>
