<script lang="ts">
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import * as m from '$paraglide/messages';
	import { ProgressRadial, RangeSlider, SlideToggle } from '@skeletonlabs/skeleton';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	export let label: string | undefined = undefined;
	export let field: string;

	export let min_score = 0;
	export let max_score = 100;
	export let score_step = 1;

	interface ScoresDefinition {
		score: number;
		name: string;
		description: string;
	}

	export let scores_definition: ScoresDefinition[] = [];

	export let form: SuperForm<Record<string, any>>;
	const { value, errors, constraints } = formFieldProxy(form, field);

	$value = $value ?? min_score;

	const isScored = formFieldProxy(form, 'is_scored')['value'];

	$: if (max_score === 100) score_step = 5;

	const status = formFieldProxy(form, 'status')['value'];
	$: isApplicable = $status === 'not_applicable' ? false : true;
</script>

<div>
	{#if label !== undefined}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="flex flex-row w-full items-center justify-evenly space-x-4">
		{#if isApplicable}
			<div class="flex w-full items-center justify-center">
				<RangeSlider
					class="w-full"
					data-testid="range-slider-input"
					name="range-slider"
					bind:value={$value}
					min={min_score}
					max={max_score}
					step={score_step}
					ticked
					disabled={!$isScored}
				>
					<div class="flex justify-between space-x-8 items-center">
						<SlideToggle
							bind:checked={$isScored}
							class="shrink-0"
							active="bg-primary-500"
							name="score-slider"
						>
							<p class="text-sm text-gray-500">{m.scoringHelpText()}</p></SlideToggle
						>
						{#if $isScored && scores_definition && $value !== null}
							{#each scores_definition as definition}
								{#if definition.score === $value}
									<p class="w-full max-w-[80ch]">
										{definition.name}{definition.description ? `: ${definition.description}` : ''}
									</p>
								{/if}
							{/each}
						{/if}
						<ProgressRadial
							stroke={100}
							meter={displayScoreColor($value, max_score)}
							value={$isScored ? formatScoreValue($value, max_score) : 0}
							font={150}
							class="shrink-0"
							width={'w-12'}>{$isScored ? $value : '--'}</ProgressRadial
						>
					</div>
				</RangeSlider>
			</div>
		{:else}
			<p class="text-sm text-gray-500">
				You cannot score if the requirement assessment is not applicable
			</p>
		{/if}
	</div>
</div>
