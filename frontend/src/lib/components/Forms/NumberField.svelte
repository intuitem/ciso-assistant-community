<script lang="ts">
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
		cachedValue: number | undefined;
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

	let decimalNotation = $state('point');
	let internalValue = $state(typeof $value === 'number' ? $value.toString() : '');

	$effect(() => {
		cachedValue = $value;
	});

	$effect(() => {
		const normalizedInternalValue = internalValue.replace(',', '.');
		const newValue = Number(normalizedInternalValue);
		if (!isNaN(newValue)) {
			$value = newValue;
		} else {
			// This prevents invalid values to be considered as valid for good UX.
			// e.g. internvalValue="0.15XYZ12" would result in $value=0.15 as $value would stop being updated from the point internalValue becomes invalid.
			$value = internalValue;
		}
	});

	function decimalNotationFormat() {
		if (decimalNotation === 'point') {
			internalValue = internalValue.replace(',', '.');
		} else {
			internalValue = internalValue.replace('.', ',');
		}
	}

	onMount(() => {
		try {
			const storedPreferences = localStorage.getItem('preferences') ?? '{}';
			const preferences = JSON.parse(storedPreferences);
			decimalNotation = preferences.decimal_notation ?? 'point';
		} catch {}

		cacheLock.promise.then((cacheResult) => {
			if (!cacheResult) return;
			internalValue = cacheResult.toString();
			decimalNotationFormat();
		});
		decimalNotationFormat();
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
			type="text"
			inputmode="decimal"
			pattern="[0-9,\.]*"
			class="{'input ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			bind:value={internalValue}
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
