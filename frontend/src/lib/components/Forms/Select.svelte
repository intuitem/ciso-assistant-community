<script lang="ts">
	import { run } from 'svelte/legacy';

	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import * as m from '$paraglide/messages.js';
	import { toCamelCase } from '$lib/utils/locales';

	let selectElement: HTMLElement | null = $state(null);

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	interface Option {
		label: unknown;
		value: unknown;
	}

	interface Props {
		class?: string;
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		cachedValue?: string | undefined;
		blank?: boolean;
		disableDoubleDash?: boolean;
		cacheLock?: CacheLock;
		color_map?: any;
		form: SuperForm<AnyZodObject>;
		options?: Option[];
		[key: string]: any;
		translateOptions?: boolean;
	}

	let {
		class: _class = '',
		label = undefined,
		field,
		valuePath = field,
		helpText = undefined,
		cachedValue = $bindable(),
		blank = false,
		disableDoubleDash = false,
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		color_map = {},
		form,
		options = [],
		translateOptions = true,
		...rest
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	let classesTextField = $derived((errors: string[] | undefined) =>
		errors && errors.length > 0 ? 'input-error' : ''
	);

	// $: value.set(cachedValue);
	run(() => {
		cachedValue = $value;
	}); // I must add an initial value.set(cachedValue) to make the cache work after that, but i firstly want to see if i can pass the test with this.
</script>

<div>
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
	<div class="control">
		<select
			class="{'select ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			style="background-color: {color_map[$value]}"
			bind:value={$value}
			bind:this={selectElement}
			{...$constraints}
			{...rest}
		>
			{#if !disableDoubleDash && !$constraints?.required && options && !options.find( (o) => new Set( ['--', 'undefined'] ).has(o.label.toLowerCase()) )}
				{@const defaultValue = blank ? '' : null}
				<option value={defaultValue} selected>--</option>
			{/if}
			{#each options || [] as option}
				{@const camelKey = toCamelCase(option.value)}
				<option value={option.value} style="background-color: {color_map[option.value]}">
					{#if !translateOptions}
						{option.label}
					{:else if camelKey !== 'm' && m[camelKey]}
						{safeTranslate(option.value)}
					{:else}
						{safeTranslate(option.label)}
					{/if}
				</option>
			{/each}
		</select>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
