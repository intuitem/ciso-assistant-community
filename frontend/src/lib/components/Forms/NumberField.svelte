<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';

	let _class = '';
	export { _class as class };
	export let label: string | undefined = undefined;
	export let step: number = 1;
	export let field: string;
	export let valuePath = field; // the place where the value is stored in the form. This is useful for nested objects
	export let helpText: string | undefined = undefined;
	export let cachedValue: string | undefined;
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let form;
	export let hidden = false;
	export let disabled = false;
	export let required = false;

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	$: cachedValue = $value;
	$: if ($value === '') {
		$value = null;
	}

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');
</script>

<div>
	<div class={classesDisabled(disabled)}>
		{#if label !== undefined && !hidden}
			{#if $constraints?.required || required}
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
	</div>
	<div class="control">
		<input
			type="number"
			{step}
			class="{'input ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			bind:value={$value}
			{...$constraints}
			{...$$restProps}
			{disabled}
			{required}
		/>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
