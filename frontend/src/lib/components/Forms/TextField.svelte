<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';

	let _class = '';

	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let cachedValue: string | undefined; // = '';
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};

	export let form;

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, field);
	// $: value.set(cachedValue);
	// $value = cachedValue;
	$: cachedValue = $value;

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult)
			$value = cacheResult;
	});

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
	$: classesDisabled = (disabled: boolean) => (disabled ? 'opacity-50' : '');
</script>

<div>
	<div class={classesDisabled($$props.disabled)}>
		{#if label !== undefined && !$$props.hidden}
			{#if $constraints?.required || $$props.required}
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
			class="{'input ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			bind:value={$value}
			{...$constraints}
			{...$$restProps}
		/>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
