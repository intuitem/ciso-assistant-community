<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { beforeUpdate, onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Option {
		label: string;
		value: string;
		suggested?: boolean;
	}

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

	export let form;
	export let multiple = false;
	export let nullable = false;
	export let mandatory = false;

	export let hidden = false;
	export let translateOptions = true;

	export let options: Option[] = [];
	export let allowUserOptions: boolean | 'append' = false;

	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let cachedValue: any[] | undefined = undefined;

	const { value, errors, constraints } = formFieldProxy(form, field);

	import { createEventDispatcher } from 'svelte';
	import MultiSelect from 'svelte-multiselect';

	let selected: typeof options = options.length === 1 && $constraints?.required ? [options[0]] : [];
	let selectedValues: (string | undefined)[] = [];
	let isInternalUpdate = false;
	const default_value = nullable ? null : selectedValues[0];

	const multiSelectOptions = {
		minSelect: $constraints && $constraints.required === true ? 1 : 0,
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	const dispatch = createEventDispatcher();

	onMount(async () => {
		dispatch('mount', $value);
		const cacheResult = await cacheLock.promise;
		if (cacheResult && cacheResult.length > 0) {
			selected = cacheResult.map((value) => optionHashmap[value]);
		}
	});

	// Handle external updates to $value
	beforeUpdate(() => {
		if (!isInternalUpdate && $value) {
			selected = options.filter((item) =>
				Array.isArray($value) ? $value.includes(item.value) : item.value === $value
			);
		}
	});

	function handleSelectChange() {
		dispatch('change', $value);
		dispatch('cache', selected);
	}

	function arraysEqual(
		arr1: string | (string | undefined)[] | null | undefined,
		arr2: string | (string | undefined)[] | null | undefined
	): boolean {
		const normalize = (val: string | (string | undefined)[] | null | undefined) => {
			if (typeof val === 'string') return [val];
			return val ?? [];
		};

		const a1 = normalize(arr1);
		const a2 = normalize(arr2);

		if (a1.length !== a2.length) return false;

		const set1 = new Set(a1);
		const set2 = new Set(a2);

		for (const value of set1) {
			if (!set2.has(value)) return false;
		}

		return true;
	}

	if ($value) {
		selected = options.filter((item) => $value.includes(item.value));
	}

	$: optionHashmap = options.reduce((acc, option) => {
		acc[option.value] = option;
		return acc;
	}, {});

	$: cachedValue = selected.map((option) => option.value);

	$: selectedValues = selected.map((item) => item.value || item.label || item);

	$: {
		if (!isInternalUpdate && !arraysEqual(selectedValues, $value)) {
			isInternalUpdate = true;
			$value = multiple ? selectedValues : (selectedValues[0] ?? default_value);
			handleSelectChange();
			isInternalUpdate = false;
		}
	}

	$: disabled = selected.length && options.length === 1 && $constraints?.required;
</script>

<div {hidden}>
	{#if label !== undefined}
		{#if $constraints?.required || mandatory}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors._errors}
		<div>
			{#each $errors._errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{:else if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control overflow-x-clip" data-testid="form-input-{field.replaceAll('_', '-')}">
		<input type="hidden" name={field} value={$value ? $value : ''} />
		<MultiSelect
			bind:selected
			{options}
			{...multiSelectOptions}
			disabled={disabled || $$restProps.disabled}
			allowEmpty={true}
			{...$$restProps}
			let:option
			{allowUserOptions}
		>
			{#if option.suggested}
				<span class="text-indigo-600">{option.label}</span>
				<span class="text-sm text-gray-500"> (suggested)</span>
			{:else if translateOptions && option.label}
				{safeTranslate(option.label)}
			{:else}
				{option.label || option}
			{/if}
		</MultiSelect>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
