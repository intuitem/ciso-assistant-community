<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

	export let form;
	export let multiple = false;
	export let nullable = false;

	export let hide = false;

	const { value, errors, constraints } = formFieldProxy(form, field);

	export let options: { label: string; value: string; suggested?: boolean }[] = [];

	import MultiSelect from 'svelte-multiselect';
	import { createEventDispatcher } from 'svelte';

	let selected: typeof options = options.length === 1 && $constraints?.required ? [options[0]] : [];
	if ($value) {
		selected = options.filter((item) => $value.includes(item.value));
	}
	let selectedValues: (string | undefined)[] = [];

	$: selectedValues = selected.map((item) => item.value);

	const default_value = nullable ? null : selectedValues[0];

	$: ($value = multiple ? selectedValues : selectedValues[0] ?? default_value),
		handleSelectChange();

	$: disabled = selected.length && options.length === 1 && $constraints?.required;

	const multiSelectOptions = {
		minSelect: $constraints && $constraints.required === true ? 1 : 0,
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	const dispatch = createEventDispatcher();

	function handleSelectChange() {
		dispatch('change', $value);
	}
</script>

<div hidden={hide}>
	{#if label !== undefined}
		{#if $constraints?.required}
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
	<div class="control" data-testid="form-input-{field.replaceAll('_', '-')}">
		<input type="hidden" name={field} value={$value ? $value : ''} />
		{#if options.length > 0}
			<MultiSelect
				bind:selected
				{options}
				{...multiSelectOptions}
				disabled={disabled || $$restProps.disabled}
				{...$$restProps}
				let:option
			>
				{#if option.suggested}
					<span class="text-indigo-600">{option.label}</span>
					<span class="text-sm text-gray-500"> (suggested)</span>
				{:else if localItems(languageTag())[toCamelCase(option.label)]}
					{localItems(languageTag())[toCamelCase(option.label)]}
				{:else}
					{option.label}
				{/if}
			</MultiSelect>
		{:else}
			<MultiSelect {options} {...multiSelectOptions} disabled />
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
