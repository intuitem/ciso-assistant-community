<script lang="ts">
	import { displayScoreColor } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Progress } from '@skeletonlabs/skeleton-svelte';

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
		progressStatusEnabled?: boolean;
		extendedResultEnabled?: boolean;
		extendedResult?: string | null;
		extendedResultColor?: string | null;
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
		max_score,
		progressStatusEnabled = true,
		extendedResultEnabled = false,
		extendedResult = null,
		extendedResultColor = null
	}: Props = $props();

	const leadResult = safeTranslate(resultI18n);
	const lead = safeTranslate(statusI18n);
	const leadExtendedResult = extendedResult ? safeTranslate(extendedResult) : null;

	let classesText = $derived(resultColor == '#000000' ? 'text-white' : '');
</script>

{#if assessable}
	<div class="flex flex-row space-x-2 items-center">
		{#if progressStatusEnabled}
			<span class="badge h-fit" style="color: {statusColor ?? '#d1d5db'};">
				{lead}
			</span>
		{/if}
		<span class="badge {classesText} h-fit" style="background-color: {resultColor ?? '#d1d5db'};">
			{leadResult}
		</span>
		{#if extendedResultEnabled && leadExtendedResult && extendedResultColor}
			<span class="badge text-white h-fit" style="background-color: {extendedResultColor};">
				{leadExtendedResult}
			</span>
		{/if}
		{#if resultI18n !== 'notApplicable' && isScored}
			<div class="relative">
				<Progress
					value={(score * 100) / max_score}
					min={0}
					max={100}
					data-testid="progress-ring-svg"
				>
					<Progress.Circle class="[--size:--spacing(12)]">
						<Progress.CircleTrack />
						<Progress.CircleRange class={displayScoreColor(score, max_score)} />
					</Progress.Circle>
					<div class="absolute inset-0 flex items-center justify-center">
						<span class="text-xs font-bold">{score}</span>
					</div>
				</Progress>
			</div>
			{#if showDocumentationScore}
				<div class="relative">
					<Progress value={(documentationScore * 100) / max_score} min={0} max={100}>
						<Progress.Circle class="[--size:--spacing(12)]">
							<Progress.CircleTrack />
							<Progress.CircleRange class={displayScoreColor(documentationScore, max_score)} />
						</Progress.Circle>
						<div class="absolute inset-0 flex items-center justify-center">
							<span class="text-xs font-bold">{documentationScore}</span>
						</div>
					</Progress>
				</div>
			{/if}
		{/if}
	</div>
{/if}
