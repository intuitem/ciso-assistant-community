<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';

	let _class = '';
	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let form;
	export let cachedValue: string = '';
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let hidden = false;
	export let disabled = false;
	export let rows = 5;
	export let cols = 50;

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, field);

	$: cachedValue = $value;

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');
</script>

<div class={classesDisabled(disabled)}>
	{#if label !== undefined && !hidden}
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
			{rows}
			{cols}
			{disabled}
		/>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
