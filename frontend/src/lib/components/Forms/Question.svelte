<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	let _class = 'w-fit';

	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

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
		{#each $value.questions as question}
			<li class="flex justify-between items-center border rounded-xl p-2">
				{question.text}
				{#if question.type === 'unique_choice'}
					<RadioGroup active="variant-filled-primary" hover="hover:variant-soft-primary">
						{#each question.options as option}
							<RadioItem
								bind:group={question.answer}
								name="question"
								value={option}
								on:click={() => (question.answer = question.answer === option ? null : option)}
								>{option}</RadioItem
							>
						{/each}
					</RadioGroup>
				{:else if question.type === 'date'}
					<input
						type="date"
						placeholder=""
						class="{'input ' + _class} {classesTextField($errors)}"
						bind:value={question.answer}
						{...$constraints}
						{...$$restProps}
					/>
				{:else}
					<input
						type="text"
						placeholder=""
						class="{'input ' + _class} {classesTextField($errors)}"
						bind:value={question.answer}
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
