<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	import { safeTranslate } from '$lib/utils/i18n';
	let _class = 'w-fit';

	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let questions = {};

	export let form: SuperForm<AnyZodObject>;

	const { value, errors, constraints } = formFieldProxy(form, field);

	$: classesTextField = (errors: string[] | undefined) =>
		errors && errors.length > 0 ? 'input-error' : '';

	function toggleSelection(urn, optionUrn) {
		// Initialize the array if it hasn't been already.
		if (!Array.isArray($value[urn])) {
			$value[urn] = [];
		}
		// Toggle the option's selection
		if ($value[urn].includes(optionUrn)) {
			$value[urn] = $value[urn].filter((val) => val !== optionUrn);
		} else {
			$value[urn] = [...$value[urn], optionUrn];
		}
	}
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
	<div class="control whitespace-pre-line">
		{#each Object.entries(questions) as [urn, question]}
			<li class="flex flex-col justify-between border rounded-xl px-2 pb-2">
				<p class="font-semibold p-2">{question.text} ({safeTranslate(question.type)})</p>
				{#if question.type === 'unique_choice'}
					<RadioGroup
						class="flex-col"
						active="variant-filled-primary"
						hover="hover:variant-soft-primary"
					>
						{#each question.choices as option}
							<RadioItem
								class="shadow-md flex"
								bind:group={$value[urn]}
								name="question"
								value={option.urn}
								on:click={() => ($value[urn] = $value[urn] === option.urn ? null : option.urn)}
								><span class="text-left">{option.value}</span></RadioItem
							>
						{/each}
					</RadioGroup>
				{:else if question.type === 'multiple_choice'}
					<div
						class="flex flex-col gap-1 p-1 bg-surface-200-700-token border-token border-surface-400-500-token rounded-token"
					>
						{#each question.choices as option}
							<button
								type="button"
								name="question"
								class="shadow-md p-1
									{$value[urn] && $value[urn].includes(option.urn)
									? 'variant-filled-primary rounded-token'
									: 'hover:variant-soft-primary bg-surface-200-700-token rounded-token'}"
								on:click={() => toggleSelection(urn, option.urn)}
							>
								{option.value}
							</button>
						{/each}
					</div>
				{:else if question.type === 'date'}
					<input
						type="date"
						placeholder=""
						class="{'input ' + _class} {classesTextField($errors)}"
						bind:value={$value[urn]}
						{...$constraints}
						{...$$restProps}
					/>
				{:else if question.type === 'text'}
					<textarea
						placeholder=""
						class="{'input w-full' + _class} {classesTextField($errors)}"
						bind:value={$value[urn]}
						{...$constraints}
						{...$$restProps}
					/>
				{/if}
			</li>
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
