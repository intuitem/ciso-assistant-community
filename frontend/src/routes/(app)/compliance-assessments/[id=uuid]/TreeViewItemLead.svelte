<script lang="ts">
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let statusI18n: string;
	export let statusDisplay: string;
	export let statusColor: string;
	export let assessable: boolean;

	const lead = localItems(languageTag())[statusI18n] ?? statusDisplay ?? '';

	$: classesText = statusColor === '#000000' ? 'text-white' : '';
</script>

{#if assessable}
	<span class="badge {classesText}" style="background-color: {statusColor};">
		{lead}
	</span>
{/if}
