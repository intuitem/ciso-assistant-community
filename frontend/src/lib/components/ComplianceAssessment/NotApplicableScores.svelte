<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import ScoreControl from '#lib/components/Forms/ScoreControl.svelte';
	import { roundScore } from '#lib/utils/helpers.js';
	import ScorePair from './ScorePair.svelte';

	// What a not-applicable requirement counts for, greyed in place of its score
	// inputs: the audit's target on the requirement's scale (`anchored_score`),
	// for both layers and so for their average, the maturity. Nothing when the
	// audit leaves N/A out of its scores (value null).
	interface Props {
		value: number | null | undefined;
		min: number;
		max: number;
		scoresDefinition?: any[];
		showImplementation: boolean;
		showDocumentation: boolean;
		implementationLabel: string;
	}

	let {
		value,
		min,
		max,
		scoresDefinition = [],
		showImplementation,
		showDocumentation,
		implementationLabel
	}: Props = $props();

	// The target projected onto another scale can be any real number.
	const shown = $derived(value === null || value === undefined ? null : roundScore(value));
</script>

{#if shown !== null && (showImplementation || showDocumentation)}
	<div class="flex flex-col gap-1" data-testid="not-applicable-scores">
		<div class="flex flex-wrap gap-4 opacity-60">
			<ScorePair>
				{#snippet implementation()}
					{#if showImplementation}
						<ScoreControl
							editable={false}
							disabled
							value={shown}
							{min}
							{max}
							{scoresDefinition}
							label={implementationLabel}
						/>
					{/if}
				{/snippet}
				{#snippet documentation()}
					{#if showDocumentation}
						<ScoreControl
							editable={false}
							disabled
							value={shown}
							{min}
							{max}
							{scoresDefinition}
							label={m.documentationScore()}
							isDoc
						/>
					{/if}
				{/snippet}
			</ScorePair>
			{#if showImplementation && showDocumentation}
				<ScoreControl editable={false} disabled value={shown} {min} {max} label={m.maturity()} />
			{/if}
		</div>
		<p class="text-xs text-surface-600-400">
			{m.notApplicableCountsAsScore({ score: shown })}
		</p>
	</div>
{/if}
