<script lang="ts">
	import { run } from 'svelte/legacy';

	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { Segment } from '@skeletonlabs/skeleton-svelte';
	import RadioItem from '$lib/components/Forms/RadioItem.svelte';

	interface Option {
		label: string;
		value: string;
		suggested?: boolean;
	}

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	interface Props {
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		form: any;
		hidden?: boolean;
		disabled?: boolean;
		translateOptions?: boolean;
		cacheLock?: CacheLock;
		cachedValue?: any[] | undefined;
		options?: Option[];
	}

	let {
		label = undefined,
		field,
		valuePath = field,
		helpText = undefined,
		form,
		hidden = false,
		disabled = false,
		translateOptions = true,
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		cachedValue = $bindable(undefined),
		options = []
	}: Props = $props();

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	run(() => {
		cachedValue = $value;
	});
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
			<Segment>
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
			</Segment>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
