<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { RadioGroup } from '@skeletonlabs/skeleton';
	import RadioItem from '$lib/components/Forms/RadioItem.svelte';

	interface Option {
		label: string;
		value: string;
		suggested?: boolean;
	}

	export let label: string | undefined = undefined;
	export let field: string;
	export let valuePath = field; // the place where the value is stored in the form. This is useful for nested objects
	export let helpText: string | undefined = undefined;

	export let form;

	export let hidden = false;
	export let disabled = false;

	export let translateOptions = true;
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let cachedValue: any[] | undefined = undefined;

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	export let options: Option[] = [];

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	$: cachedValue = $value;
</script>

<div {hidden}>
	{#if label !== undefined}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control overflow-x-clip" data-testid="form-input-{field.replaceAll('_', '-')}">
		{#if options.length > 0}
			<RadioGroup>
				{#each options as option, index}
					{#if option.label}
						<RadioItem
							bind:group={$value}
							name={field}
							value={option.value}
							displayChecked={(index < options.length - 1 &&
								$value === options[index + 1].value &&
								!options[index + 1].label) ||
								undefined}
							{disabled}
							>{translateOptions === true ? safeTranslate(option.label) : option.label}</RadioItem
						>
					{/if}
				{/each}
			</RadioGroup>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
