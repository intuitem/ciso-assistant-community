<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms/client';
	import { ProgressRadial, SlideToggle } from '@skeletonlabs/skeleton';
	import { RangeSlider } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import type { AnyZodObject } from 'zod';
	import { displayScoreColor } from '$lib/utils/helpers';

	export let label: string | undefined = undefined;
	export let field: string;

	export let min_score: number = 0;
	export let max_score: number = 100;
	export let score_definition: string = '';

	export let form: SuperForm<AnyZodObject>;
	const { value, errors, constraints } = formFieldProxy(form, field);

	$: scoringEnabled = $value === null ? false : true;

	function formatValue(value: number) {
		if (value === null) {
			return 0;
		}
		return (value * 100) / max_score;
	}
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
				{#if scoringEnabled}
					<RangeSlider
						class="w-full"
						name="range-slider"
						bind:value={$value}
						min={min_score}
						max={max_score}
						step={1}
						ticked
					>
						<div class="flex justify-between items-center">
							<SlideToggle
								bind:checked={scoringEnabled}
								active="bg-primary-500"
								on:click={() => ($value = null)}
								name="score-slider"
							>
								<p class="text-sm text-gray-500">{m.scoringHelpText()}</p></SlideToggle
							>
							{#if score_definition && $value !== null}
								{#each score_definition as definition, index}
									{#if definition.score === $value}
										<p class="">{definition.name}: {definition.description}</p>
									{/if}
								{/each}
							{/if}
							<ProgressRadial
								stroke={100}
								meter={displayScoreColor($value, max_score)}
								value={formatValue($value)}
								font={150}
								width={'w-12'}>{$value}</ProgressRadial
							>
						</div>
					</RangeSlider>
				{:else}
					<RangeSlider
						disabled
						class="w-full"
						name="range-slider"
						value={min_score}
						min={min_score}
						max={max_score}
						step={1}
						ticked
					>
						<div class="flex justify-between items-center">
							<SlideToggle
								bind:checked={scoringEnabled}
								active="bg-primary-500"
								on:click={() => ($value = min_score)}
								name="score-slider"
							>
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
