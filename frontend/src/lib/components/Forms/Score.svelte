<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms/client';
	import { ProgressRadial, SlideToggle } from '@skeletonlabs/skeleton';
	import { RangeSlider } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';

	export let label: string | undefined = undefined;
	export let field: string;

	export let min_score = 0;
	export let max_score = 100;
	export let score_step = 1;

	interface ScoreDefinition {
		score: number;
		name: string;
		description: string;
	}

	export let score_definition: ScoreDefinition[] = [];

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
				{#if $isScored}
					<RangeSlider
						class="w-full"
						name="range-slider"
						bind:value={$value}
						min={min_score}
						max={max_score}
						step={score_step}
						ticked
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
							{#if score_definition && $value !== null}
								{#each score_definition as definition}
									{#if definition.score === $value}
										<p class="w-full max-w-[80ch]">
											{definition.name}: {definition.description}
										</p>
									{/if}
								{/each}
							{/if}
							<ProgressRadial
								stroke={100}
								meter={displayScoreColor($value, max_score)}
								value={formatScoreValue($value, max_score)}
								font={150}
								class="shrink-0"
								width={'w-12'}>{$value}</ProgressRadial
							>
						</div>
					</RangeSlider>
				{:else}
					<RangeSlider
						disabled
						class="w-full"
						name="range-slider"
						value={$value}
						min={min_score}
						max={max_score}
						step={score_step}
						ticked
					>
						<div class="flex justify-between items-center">
							<SlideToggle bind:checked={$isScored} active="bg-primary-500" name="score-slider">
								<p class="text-sm text-gray-500">{m.scoringHelpText()}</p></SlideToggle
							>
							<ProgressRadial stroke={100} value={0} font={150} width={'w-12'}>--</ProgressRadial>
						</div>
					</RangeSlider>
				{/if}
			</div>
		{:else}
			<p class="text-sm text-gray-500">
				You cannot score if the requirement assessment is not applicable
			</p>
		{/if}
	</div>
</div>
