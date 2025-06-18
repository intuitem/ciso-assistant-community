<script lang="ts">
	import { run } from 'svelte/legacy';

	import { displayScoreColor } from '$lib/utils/helpers';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface ScoresDefinition {
		score: number;
		name: string;
		description: string;
	}

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
		onChange?: (score: number) => void;
		left?: import('svelte').Snippet;
	}

	let {
		label = undefined,
		field,
		isDoc = false,
		inversedColors = false,
		styles = '',
		min_score = 0,
		max_score = 100,
		score_step = $bindable(max_score === 100 ? 5 : 1),
		helpText = undefined,
		disabled = false,
		scores_definition = [],
		form,
		onChange = () => {},
		left
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, field);
	let previous = $state($value);

	$effect(() => {
		if (previous !== $value && previous !== undefined) {
			onChange($value);
		}
		previous = $value;
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
			<div class="flex flex-col w-full align-top">
				{#if label !== undefined}
					{#if $constraints?.required}
						<label class="text-sm font-semibold" for={field}
							>{label} <span class="text-red-500">*</span></label
						>
					{:else}
						<label class="text-sm font-semibold" for={field}>{label}</label>
					{/if}
				{/if}
				<input
					data-testid="range-slider-input"
					name={field}
					type="range"
					class="input px-0"
					bind:value={$value}
					min={min_score}
					max={max_score}
					step={score_step}
					{disabled}
					{...constraints}
				/>
			</div>
			<ProgressRing
				meterStroke={displayScoreColor($value, max_score, inversedColors)}
				value={$value}
				label={$value}
				onValueChange={(e) => ($value = e.value)}
				classes="shrink-0"
				size="size-12"
				min={min_score}
				max={max_score}
				>{$value}
			</ProgressRing>
		</div>
		<div class="flex w-full items-center">
			<div class="flex space-x-8 w-full justify-center">
				<div class="w-full max-w-[80ch] justify-center text-center whitespace-pre-wrap">
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
				</div>
			</div>
		</div>
		{#if helpText}
			<p class="text-sm text-gray-500">{helpText}</p>
		{/if}
	</div>
{/if}
