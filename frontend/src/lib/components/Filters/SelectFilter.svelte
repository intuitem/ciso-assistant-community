<script lang="ts">
	import { toCamelCase } from '$lib/utils/locales';

	export let value: string;

	export let field: string;
	export let helpText: string | undefined = undefined;

	export let defaultOptionName = 'undefined';
	export let label: string = defaultOptionName;
	export let optionLabels: { [key: string]: string } = {};

	export let multiple = true;

	export let hide = false;

	export let translateOptions = true;

	export let options: string[];
	options = [...new Set(options.flat())];

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

	import * as m from '$paraglide/messages';

	export let multiSelectOptions = {
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	import MultiSelect from 'svelte-multiselect';
</script>

{#if !hide}
	<div>
		<label class="text-sm font-semibold" for={field}
			>{m[label]()} <span class="text-xs font-normal">({selectOptions.length})</span></label
		>
		<div class="control" data-testid="filter-input-{field.replaceAll('_', '-')}">
			<MultiSelect
				bind:value
				options={selectOptions}
				{...multiSelectOptions}
				{...$$restProps}
				let:option
			>
				{#if translateOptions && Object.hasOwn(m, option.label)}
					{m[toCamelCase(option.label)]()}
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
