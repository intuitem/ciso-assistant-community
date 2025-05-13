<!-- @migration-task Error while migrating Svelte code: Can't migrate code with beforeUpdate. Please migrate by hand. -->
<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	export let value: { label: string; value: string }[];

	export let field: string;
	export let helpText: string | undefined = undefined;

	export let defaultOptionName = 'undefined';
	export let label: string = defaultOptionName;
	export let optionLabels: { [key: string]: string } = {};

	export let multiple = true;

	export let hide = false;

	export let translateOptions = true;

	export let options: string[];
	options = [...new Set(options ? options.flat() : [])];
	options = options.filter((option) => option !== '');

	const selectOptions = options
		.map((option) => {
			const label = optionLabels[option] ?? option;
			return {
				label: label ?? m.undefined(),
				value: option
			};
		})
		.sort((a, b) => a.label.localeCompare(b.label));

	hide = hide || !(selectOptions && Object.entries(selectOptions).length > 1);

	import { m } from '$paraglide/messages';
	import { beforeUpdate, onMount } from 'svelte';

	export let multiSelectOptions = {
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	import MultiSelect from 'svelte-multiselect';

	let initialValue: typeof value;
	let isInitialized = false;

	beforeUpdate(() => {
		// Capture the initial value if we haven't already
		if (!isInitialized && value) {
			initialValue = Array.isArray(value) ? [...value] : value;
			isInitialized = true;
		}
	});

	onMount(() => {
		// Restore the initial value if it was lost
		if (initialValue && (!value || (Array.isArray(value) && value.length === 0))) {
			value = initialValue;
		}
	});

	$: value =
		value && Array.isArray(value)
			? value.map((v) => (v.label ? v : { label: v.value, value: v.value }))
			: value;
</script>

{#if !hide}
	<div>
		<label class="text-sm font-semibold" for={field}
			>{safeTranslate(label)}
			<span class="text-xs font-normal">({selectOptions.length})</span></label
		>
		<div class="control" data-testid="filter-input-{field.replaceAll('_', '-')}">
			<MultiSelect
				bind:value
				options={selectOptions}
				{...multiSelectOptions}
				{...$$restProps}
				let:option
			>
				{#if translateOptions}
					{safeTranslate(option.label)}
				{:else}
					{option.label}
				{/if}
			</MultiSelect>
		</div>
		{#if helpText}
			<p class="text-sm text-gray-500">{helpText}</p>
		{/if}
	</div>
{/if}
