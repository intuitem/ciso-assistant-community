<script lang="ts">
	import { run } from 'svelte/legacy';

	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';

	interface Props {
		class?: string;
		label?: string | undefined;
		field: string;
		helpText?: string | undefined;
		form: any;
		cachedValue?: string;
		cacheLock?: CacheLock;
		hidden?: boolean;
		disabled?: boolean;
		rows?: number;
		cols?: number;
		[key: string]: any;
	}

	let {
		class: _class = '',
		label = $bindable(),
		field,
		helpText = undefined,
		form,
		cachedValue = $bindable(),
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		hidden = false,
		disabled = false,
		rows = 5,
		cols = 50,
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, field);

	run(() => {
		cachedValue = $value;
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

<div class={classesDisabled(disabled)}>
	{#if label !== undefined && !hidden}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control">
		<textarea
			class="{'input ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			bind:value={$value}
			{...$constraints}
			{...rest}
			{rows}
			{cols}
			{disabled}
		></textarea>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500 whitespace-pre-line">{helpText}</p>
	{/if}
</div>
