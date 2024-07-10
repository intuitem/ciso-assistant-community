<script lang="ts">
	import type { CssClasses } from '@skeletonlabs/skeleton';
	import { formFieldProxy } from 'sveltekit-superforms';

	let _class = '';

	export { _class as class };
	export let regionContainer: CssClasses = '';
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let form;
	export let cachedValue: string = '';

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, field);
	$: value.set(cachedValue);

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
</script>

<div class={regionContainer}>
	{#if label !== undefined && !$$props.hidden}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control">
		<textarea
			class="{'input ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			bind:value={cachedValue}
			{...$constraints}
			{...$$restProps}
			rows="5"
			cols="50"
		/>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
