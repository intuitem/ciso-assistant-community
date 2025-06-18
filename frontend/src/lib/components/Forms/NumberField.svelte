<script lang="ts">
	import { run } from 'svelte/legacy';

	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';

	interface Props {
		class?: string;
		label?: string | undefined;
		step?: number;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		cachedValue: string | undefined;
		cacheLock?: CacheLock;
		form: any;
		hidden?: boolean;
		disabled?: boolean;
		required?: boolean;
		[key: string]: any;
	}

	let {
		class: _class = '',
		label = $bindable(),
		step = 1,
		field,
		valuePath = field,
		helpText = undefined,
		cachedValue = $bindable(),
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		form,
		hidden = false,
		disabled = false,
		required = false,
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	run(() => {
		cachedValue = $value;
	});
	run(() => {
		if ($value === '') {
			$value = null;
		}
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
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
			{...rest}
			{disabled}
			{required}
		/>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
