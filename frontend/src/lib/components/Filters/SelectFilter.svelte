<script lang="ts">
	import { localItems, toCamelCase } from '$lib/utils/locales';

	export let value: string;

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

	export let defaultOptionName = 'undefined';
	export let optionLabels: { [key: string]: string } = {};

	export let option;

	export let hide = false;
	export let translateOptions = true;

	export let options: string[] = [];

	import MultiSelect from 'svelte-multiselect';

	$: console.log($$props);
</script>

<div hidden={hide}>
	<div class="control" data-testid="form-input-{field.replaceAll('_', '-')}">
		{#if options.length > 0}
			<MultiSelect bind:value {options} {...$$restProps} let:option>
				{#if translateOptions && localItems()[toCamelCase(option)]}
					{localItems()[toCamelCase(option)]}
				{:else}
					{option}
				{/if}
			</MultiSelect>
		{:else}
			<!-- <MultiSelect {options} disabled /> -->
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
