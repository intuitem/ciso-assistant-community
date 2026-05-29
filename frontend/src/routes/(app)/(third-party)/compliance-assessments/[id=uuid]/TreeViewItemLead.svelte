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
		showResult?: boolean;
		showScore?: boolean;
		showStatus?: boolean;
		scoringEnabled?: boolean;
		showDocumentationScore: boolean;
		max_score: number;
		min_score?: number;
		progressStatusEnabled?: boolean;
		extendedResultEnabled?: boolean;
		showExtendedResult?: boolean;
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
		showResult = true,
		showScore = true,
		showStatus = true,
		scoringEnabled = false,
		showDocumentationScore,
		max_score,
		min_score = 0,
		progressStatusEnabled = true,
		extendedResultEnabled = false,
		showExtendedResult = true,
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
		{#if showStatus}
			<span class="badge h-fit" style="color: {statusColor ?? '#d1d5db'};">
				{lead}
			</span>
		{/if}
		{#if showResult}
			<span class="badge {classesText} h-fit" style="background-color: {resultColor ?? '#d1d5db'};">
				{leadResult}
			</span>
		{/if}
		{#if showExtendedResult && leadExtendedResult && extendedResultColor}
			<span class="badge text-white h-fit" style="background-color: {extendedResultColor};">
				{leadExtendedResult}
			</span>
		{/if}
		{#if showScore && resultI18n !== 'notApplicable' && isScored}
			{@const range = max_score - min_score}
			{@const safeScore = score ?? min_score}
			<div class="relative">
				<Progress
					value={range > 0
						? Math.max(0, Math.min(100, ((safeScore - min_score) * 100) / range))
						: 0}
					min={0}
					max={100}
					data-testid="progress-ring-svg"
				>
					<Progress.Circle class="[--size:--spacing(12)]">
						<Progress.CircleTrack />
						<Progress.CircleRange class={displayScoreColor(score, max_score, false, min_score)} />
					</Progress.Circle>
					<div class="absolute inset-0 flex items-center justify-center">
						<span class="text-xs font-bold">{score}</span>
					</div>
				</Progress>
			</div>
			{#if showDocumentationScore}
				{@const safeDoc = documentationScore ?? min_score}
				<div class="relative">
					<Progress
						value={range > 0
							? Math.max(0, Math.min(100, ((safeDoc - min_score) * 100) / range))
							: 0}
						min={0}
						max={100}
					>
						<Progress.Circle class="[--size:--spacing(12)]">
							<Progress.CircleTrack />
							<Progress.CircleRange
								class={displayScoreColor(documentationScore, max_score, false, min_score)}
							/>
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
