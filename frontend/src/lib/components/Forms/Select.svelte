<script lang="ts">
	import { toCamelCase } from '$lib/utils/locales';
	import * as m from '$paraglide/messages';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { onMount } from 'svelte';

	let _class = '';

	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let cachedValue: string | undefined = undefined;
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};

	export let color_map = {};

	export let form: SuperForm<AnyZodObject>;

	const { value, errors, constraints } = formFieldProxy(form, field);
	// $: value.set(cachedValue);
	$: cachedValue = $value; // I must add an initial value.set(cachedValue) to make the cache work after that, but i firstly want to see if i can pass the test with this.
	let selectElement: HTMLElement | null = null;

	onMount(async () => {
		if (!cacheLock) return;
		const cacheResult = await cacheLock.promise;
		if (cacheResult)
			$value = cacheResult;
	});

	interface Option {
		label: unknown;
		value: unknown;
	}

	export let options: Option[] = [];

	$: classesTextField = (errors: string[] | undefined) =>
		errors && errors.length > 0 ? 'input-error' : '';
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
			{...$$restProps}
		>
			{#if !$constraints?.required && !options.find( (o) => new Set( ['--', 'undefined'] ).has(o.label.toLowerCase()) )}
				<option value={null} selected>--</option>
			{/if}
			{#each options as option}
				<option value={option.value} style="background-color: {color_map[option.value]}">
					{#if Object.hasOwn(m, toCamelCase(option.label))}
						{m[toCamelCase(option.label)]()}
					{:else}
						{option.label}
					{/if}
				</option>
			{/each}
		</select>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
