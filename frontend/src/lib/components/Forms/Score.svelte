<script lang="ts">
	import { run } from 'svelte/legacy';

	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { ProgressRing, Slider } from '@skeletonlabs/skeleton-svelte';
	import { createEventDispatcher } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';




	interface ScoresDefinition {
		score: number;
		name: string;
		description: string;
	}


	const { value, errors, constraints } = formFieldProxy(form, field);

	const dispatch = createEventDispatcher();
	let previous = $state([$value]);

	interface Props {
		label?: string | undefined;
		field: string;
		isDoc?: boolean;
		fullDonut?: boolean;
		inversedColors?: boolean;
		styles?: string;
		min_score?: number;
		max_score?: number;
		score_step?: number;
		helpText?: string | undefined;
		disabled?: boolean;
		scores_definition?: ScoresDefinition[];
		form: SuperForm<Record<string, any>>;
		score?: any;
		left?: import('svelte').Snippet;
	}

	let {
		label = undefined,
		field,
		isDoc = false,
		fullDonut = false,
		inversedColors = false,
		styles = '',
		min_score = 0,
		max_score = 100,
		score_step = $bindable(1),
		helpText = undefined,
		disabled = false,
		scores_definition = [],
		form,
		score = $bindable($value),
		left
	}: Props = $props();
	run(() => {
		score = $value;
	});

	run(() => {
		if (previous[0] !== $value && previous[0] !== undefined) {
			dispatch('change', { score: $value });
		}
		previous = [$value];
	});

	run(() => {
		if (max_score === 100) score_step = 5;
	});

	run(() => {
		$value = !disabled ? ($value ?? min_score) : $value;
	});
</script>

{@render left?.()}
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
				<Slider
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
						<ProgressRing
							stroke={100}
							meter={displayScoreColor($value, max_score, inversedColors)}
							value={!disabled ? formatScoreValue($value, max_score, fullDonut) : min_score}
							font={150}
							class="shrink-0"
							border-4
							width={'w-12'}>{!disabled ? $value : '--'}</ProgressRing
						>
					</div>
				</Slider>
			</div>
		</div>
		{#if helpText}
			<p class="text-sm text-gray-500">{helpText}</p>
		{/if}
	</div>
{/if}
