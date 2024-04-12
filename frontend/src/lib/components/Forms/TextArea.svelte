<script lang="ts">
	import type { CssClasses } from '@skeletonlabs/skeleton';
	import { formFieldProxy } from 'sveltekit-superforms/client';
	import { onMount } from 'svelte';
	import { formSubmittedStore } from '$lib/utils/stores';

	let _class = '';

	export { _class as class };
	export let regionContainer: CssClasses = '';
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let form;
	export let origin: string;
	export let URLModel: string;

	const { value, errors, constraints } = formFieldProxy(form, field);
	const dataSaving = origin === "create";

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');

	let _sessionStorage = null;
	onMount(() => {
		if (!dataSaving) return;
		_sessionStorage = sessionStorage;
		const savedData = JSON.parse(_sessionStorage.getItem("create_form_saved_data") ?? "{}");
		const currentData = savedData[URLModel];
		if (currentData) {
			const savedValue = currentData[field];
			if (savedValue) {
				value.set(savedValue);
			}
		}
	});


	$: if (dataSaving && _sessionStorage && !$formSubmittedStore) {
		const savedData = JSON.parse(_sessionStorage.getItem("create_form_saved_data") ?? "{}");

		const currentData = savedData[URLModel] ?? {};
		if (!sessionStorage.hasOwnProperty(URLModel)) {
			currentData[field] = $value;
		}
		savedData[URLModel] = currentData;

		_sessionStorage.setItem("create_form_saved_data",JSON.stringify(savedData));
	}
</script>

<div class={regionContainer}>
	{#if label !== undefined}
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
			bind:value={$value}
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
