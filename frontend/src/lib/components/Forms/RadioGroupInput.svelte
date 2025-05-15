<script lang="ts">
	import { run } from 'svelte/legacy';

	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { Segment } from '@skeletonlabs/skeleton-svelte';

	interface Option {
		label: string;
		value: string;
		suggested?: boolean;
	}

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
		cachedValue = $bindable(),
		options = []
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

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
			<Segment name={field} value={$value} onValueChange={(e) => ($value = e.value)}>
				{#each options as option}
					{#if option.label}
						<Segment.Item value={option.value} {disabled}
							>{translateOptions === true
								? safeTranslate(option.label)
								: option.label}</Segment.Item
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
