<script lang="ts">
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import { ProgressRadial } from '@skeletonlabs/skeleton';

	export let statusI18n: string;
	export let statusDisplay: string;
	export let statusColor: string;
	export let assessable: boolean;
	export let score: number;
	export let max_score: number;

	const lead = localItems(languageTag())[statusI18n] ?? statusDisplay ?? '';

	$: classesText = statusColor === '#000000' ? 'text-white' : '';
</script>

{#if assessable}
<div class="flex flex-row space-x-2 items-center">
	{#if score !== null}
		<span>
			<ProgressRadial stroke={100} font={150} value={score * 100 / max_score} width={'w-12'}>{score}</ProgressRadial>
		</span>
	{/if}
	<span class="badge {classesText} h-fit" style="background-color: {statusColor};">
		{lead}
	</span>
</div>
{/if}
