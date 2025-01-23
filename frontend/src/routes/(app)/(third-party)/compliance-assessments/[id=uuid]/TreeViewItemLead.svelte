<script lang="ts">
	import { displayScoreColor } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { ProgressRadial } from '@skeletonlabs/skeleton';

	export let statusI18n: string;
	export let resultI18n: string;
	export let statusColor: string;
	export let resultColor: string;
	export let assessable: boolean;
	export let score: number | null;
	export let documentationScore: number | null;
	export let isScored: boolean;
	export let showDocumentationScore: boolean;
	export let max_score: number;

	const leadResult = safeTranslate(resultI18n);
	const lead = safeTranslate(statusI18n);

	$: classesText = resultColor == '#000000' ? 'text-white' : '';
</script>

{#if assessable}
	<div class="flex flex-row space-x-2 items-center">
		<span class="badge h-fit" style="color: {statusColor ?? '#d1d5db'};">
			{lead}
		</span>
		<span class="badge {classesText} h-fit" style="background-color: {resultColor ?? '#d1d5db'};">
			{leadResult}
		</span>
		{#if resultI18n !== 'notApplicable' && isScored}
			<ProgressRadial
				stroke={100}
				meter={displayScoreColor(score, max_score)}
				font={150}
				value={(score * 100) / max_score}
				width={'w-10'}>{score}</ProgressRadial
			>
			{#if showDocumentationScore}
				<ProgressRadial
					stroke={100}
					meter={displayScoreColor(documentationScore, max_score)}
					font={150}
					value={(documentationScore * 100) / max_score}
					width={'w-10'}>{documentationScore}</ProgressRadial
				>
			{/if}
		{/if}
	</div>
{/if}
