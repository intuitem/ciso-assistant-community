<script lang="ts">
	import { run } from 'svelte/legacy';

	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';

	interface Props {
		class?: string;
		label?: string | undefined;
		max?: number;
		allowNegative?: boolean;
		floatPrecision?: number;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		cachedValue: string | undefined;
		cacheLock?: CacheLock;
		form: any;
		hidden?: boolean;
		disabled?: boolean;
		required?: boolean;
		commaSupported?: boolean;
		[key: string]: any;
	}

	let {
		class: _class = '',
		label = $bindable(),
		max = Infinity,
		allowNegative = false,
		floatPrecision = 0,
		field,
		valuePath = field,
		helpText = undefined,
		cachedValue = $bindable(),
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		form,
		hidden = false,
		disabled = false,
		required = false,
		commaSupported = false,
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	run(() => {
		cachedValue = $value;
	});
	run(() => {
		if ($value === '') {
			$value = null;
		}
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	let stringifiedValueRegex =
		floatPrecision > 0
			? new RegExp(`^${allowNegative ? '\\-?' : ''}[0-9]((\\.|,)([0-9]{1,${floatPrecision}})?)?$`)
			: new RegExp(`^${allowNegative ? '\\-?' : ''}[0-9]+$`);
	let stringifiedValue = $state(`${$value === undefined ? '' : $value}`);

	if (commaSupported) {
		$effect(() => {
			if (stringifiedValue) {
				const newValue = Number(stringifiedValue.replace(',', '.'));
				value.set(newValue);
			}
		});
	}

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

<div>
	<div class={classesDisabled(disabled)}>
		{#if label !== undefined && !hidden}
			{#if $constraints?.required || required}
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
	</div>
	<div class="control">
		{#if commaSupported}
			<input
				type="text"
				class="{'input ' + _class} {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				placeholder=""
				bind:value={stringifiedValue}
				onbeforeinput={(e) => {
					if (e.inputType === 'deleteContentBackward') return;

					const targetElem = e.target as HTMLInputElement;
					const selectionStart = targetElem.selectionStart;
					const selectionEnd = targetElem.selectionEnd;

					const currentText = e.target.value;
					// const newText = currentText + e.data;

					const newText =
						currentText.slice(0, selectionStart) + e.data + currentText.slice(selectionEnd);
					console.log('===>', newText);

					const newNumber = Number(newText);

					if (newNumber !== newNumber || newNumber > max) {
						e.preventDefault();
					}
					if (newText && !stringifiedValueRegex.test(newText)) {
						e.preventDefault();
					}
				}}
				{...$constraints}
				{...rest}
				{disabled}
				{required}
			/>
		{:else}
			<!-- { step }-->
			<input
				type="number"
				class="{'input ' + _class} {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				placeholder=""
				bind:value={$value}
				{...$constraints}
				{...rest}
				{disabled}
				{required}
			/>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
