<script lang="ts">
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants.js';
	export let cell: Array<any>;
	$: display = cell.map((lang) => LOCALE_DISPLAY_MAP[lang]);
</script>

<span {...$$restProps}>
	{#each display as lang}
		<p>{lang}</p>
	{/each}
</span>
