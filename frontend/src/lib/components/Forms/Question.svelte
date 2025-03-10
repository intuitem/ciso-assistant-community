<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
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
	<div class="control">
		{#each Object.entries(questions) as [urn, question]}
			<li class="flex flex-col justify-between border rounded-xl px-2 pb-2">
				<p class="font-semibold p-2">{question.text}</p>
				{#if question.type === 'unique_choice'}
					<RadioGroup
						class="flex-col"
						active="variant-filled-primary"
						hover="hover:variant-soft-primary"
					>
						{#each question.choices as option}
							<RadioItem
								class="shadow-md"
								bind:group={$value[urn]}
								name="question"
								value={option.urn}
								on:click={() => ($value[urn] = $value[urn] === option.urn ? null : option.urn)}
								>{option.value}</RadioItem
							>
						{/each}
					</RadioGroup>
				{:else if question.type === 'date'}
					<input
						type="date"
						placeholder=""
						class="{'input ' + _class} {classesTextField($errors)}"
						bind:value={$value[urn]}
						{...$constraints}
						{...$$restProps}
					/>
				{:else}
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
