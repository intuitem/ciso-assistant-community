<script lang="ts">
	import { toCamelCase } from '$lib/utils/locales';

	export let value: string;

	export let field: string;
	export let helpText: string | undefined = undefined;

	export let defaultOptionName = 'undefined';
	export let label: string | undefined = defaultOptionName;
	export let optionLabels: { [key: string]: string } = {};

	export let multiple = true;

	export let option;

	export let hide = false;
	export let translateOptions = true;

	export let options: string[] = [];

	import * as m from '$paraglide/messages';

	export let multiSelectOptions = {
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	import MultiSelect from 'svelte-multiselect';

	$: console.log($$props);
</script>

<div hidden={hide}>
	<label class="text-sm font-semibold" for={field}>{m[label]()}</label>
	<div class="control" data-testid="form-input-{field.replaceAll('_', '-')}">
		{#if options.length > 0}
			<MultiSelect bind:value {options} {...multiSelectOptions} {...$$restProps} let:option>
				{#if translateOptions && Object.hasOwn(m, option)}
					{m[toCamelCase(option)]()}
				{:else if optionLabels[option]}
					{optionLabels[option]}
				{:else}
					{option}
				{/if}
			</MultiSelect>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
