<script lang="ts">
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { ProgressRadial, RangeSlider } from '@skeletonlabs/skeleton';
	import { createEventDispatcher } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	export let label: string | undefined = undefined;
	export let field: string;
	export let isDoc: boolean = false;
	export let fullDonut: boolean = false;
	export let inversedColors: boolean = false;
	export let styles: string = '';

	export let min_score = 0;
	export let max_score = 100;
	export let score_step = 1;
	export let helpText: string | undefined = undefined;

	export let disabled: boolean = false;

	interface ScoresDefinition {
		score: number;
		name: string;
		description: string;
	}

	export let scores_definition: ScoresDefinition[] = [];

	export let form: SuperForm<Record<string, any>>;
	const { value, errors, constraints } = formFieldProxy(form, field);

	const dispatch = createEventDispatcher();
	let previous = [$value];

	export let score = $value;
	$: score = $value;

	$: {
		if (previous[0] !== $value && previous[0] !== undefined) {
			dispatch('change', { score: $value });
		}
		previous = [$value];
	}

	$: if (max_score === 100) score_step = 5;

	$: $value = !disabled ? ($value ?? min_score) : $value;
</script>

<slot name="left" />
{#if !disabled}
	<div class={styles}>
		{#if $errors && $errors.length > 0}
			<div>
				{#each $errors as error}
					<p class="text-error-500 text-xs font-medium">{error}</p>
				{/each}
			</div>
		{/if}
		<div class="flex flex-row w-full items-center justify-evenly space-x-4">
			<div class="flex w-full items-center justify-center border-2 rounded-lg p-2">
				<RangeSlider
					class="w-full"
					data-testid="range-slider-input"
					name="range-slider"
					bind:value={$value}
					min={min_score}
					max={max_score}
					step={score_step}
					ticked
					{disabled}
				>
					<div class="flex justify-between space-x-8 w-full items-start">
						{#if label !== undefined}
							{#if $constraints?.required}
								<label class="text-sm font-semibold" for={field}
									>{label} <span class="text-red-500">*</span></label
								>
							{:else}
								<label class="text-sm font-semibold" for={field}>{label}</label>
							{/if}
						{/if}

						<div class="flex space-x-8 w-full justify-center">
							<p class="w-full max-w-[80ch] justify-center text-center whitespace-pre-wrap">
								{#if !disabled && scores_definition && $value !== null}
									{#each scores_definition as definition}
										{#if definition.score === $value}
											<p class="font-bold">{definition.name}</p>
											{#if isDoc && definition.description_doc}
												{definition.description_doc}
											{:else if definition.description}
												{definition.description}
											{/if}
										{/if}
									{/each}
								{/if}
							</p>
						</div>
						<ProgressRadial
							stroke={100}
							meter={displayScoreColor($value, max_score, inversedColors)}
							value={!disabled ? formatScoreValue($value, max_score, fullDonut) : min_score}
							font={150}
							class="shrink-0"
							border-4
							width={'w-12'}>{!disabled ? $value : '--'}</ProgressRadial
						>
					</div>
				</RangeSlider>
			</div>
		</div>
		{#if helpText}
			<p class="text-sm text-gray-500">{helpText}</p>
		{/if}
	</div>
{/if}
