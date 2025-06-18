<script lang="ts">
	import { displayScoreColor } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		statusI18n: string;
		resultI18n: string;
		statusColor: string;
		resultColor: string;
		assessable: boolean;
		score: number | null;
		documentationScore: number | null;
		isScored: boolean;
		showDocumentationScore: boolean;
		max_score: number;
	}

	let {
		statusI18n,
		resultI18n,
		statusColor,
		resultColor,
		assessable,
		score,
		documentationScore,
		isScored,
		showDocumentationScore,
		max_score
	}: Props = $props();

	const leadResult = safeTranslate(resultI18n);
	const lead = safeTranslate(statusI18n);

	let classesText = $derived(resultColor == '#000000' ? 'text-white' : '');
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
			<ProgressRing
				strokeWidth="20px"
				meterStroke={displayScoreColor(score, max_score)}
				value={(score * 100) / max_score}
				size="size-12">{score}</ProgressRing
			>
			{#if showDocumentationScore}
				<ProgressRing
					strokeWidth="20px"
					meterStroke={displayScoreColor(documentationScore, max_score)}
					value={(documentationScore * 100) / max_score}
					size="size-12">{documentationScore}</ProgressRing
				>
			{/if}
		{/if}
	</div>
{/if}
