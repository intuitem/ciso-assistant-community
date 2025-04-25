<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CssClasses } from '@skeletonlabs/skeleton';

	let _class = '';
	export let type = 'text';
	export { _class as class };
	export let classesContainer: CssClasses = '';
	export let label: string | undefined = undefined;
	export let field: string;
	export let valuePath = field; // the place where the value is stored in the form. This is useful for nested objects
	export let helpText: string | undefined = undefined;
	export let cachedValue: string | undefined = undefined;
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let form;
	export let hidden = false;
	export let disabled = false;
	export let required = false;

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	// Store the display value separately from the actual form value
	let displayValue: string;

	$: cachedValue = $value;

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) {
			$value = cacheResult;
			if (type === 'datetime-local') {
				displayValue = formatDateForInput($value);
			}
		}
	});

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');

	// Function to convert local datetime to UTC format for storage
	function convertToUTC(dateTimeLocal: string): string {
		const date = new Date(dateTimeLocal);
		return date.toISOString();
	}

	// Function to format UTC date string for datetime-local input
	function formatDateForInput(utcDateString: string): string {
		if (!utcDateString) return '';
		const date = new Date(utcDateString);
		// Format as YYYY-MM-DDThh:mm (format required by datetime-local input)
		return (
			date.getFullYear() +
			'-' +
			String(date.getMonth() + 1).padStart(2, '0') +
			'-' +
			String(date.getDate()).padStart(2, '0') +
			'T' +
			String(date.getHours()).padStart(2, '0') +
			':' +
			String(date.getMinutes()).padStart(2, '0')
		);
	}

	// Handle value changes for datetime-local inputs
	function handleDateTimeChange(event: Event) {
		const inputValue = (event.target as HTMLInputElement).value;
		if (inputValue) {
			displayValue = inputValue;
			$value = convertToUTC(inputValue);
		} else {
			displayValue = '';
			$value = '';
		}
	}

	// Initialize display value if it's a datetime-local input
	$: if (type === 'datetime-local' && $value && !displayValue) {
		displayValue = formatDateForInput($value);
	}
</script>

<div class={classesContainer}>
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
					<p class="text-error-500 text-xs font-medium">{safeTranslate(error)}</p>
				{/each}
			</div>
		{/if}
	</div>
	<div class="control">
		{#if type === 'datetime-local'}
			<input
				type="datetime-local"
				class="{'input ' + _class} {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				id="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				placeholder=""
				value={displayValue}
				on:input={handleDateTimeChange}
				{...$constraints}
				{...$$restProps}
				{disabled}
				{required}
			/>
		{:else}
			<input
				{...{ type }}
				class="{'input ' + _class} {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				id="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				placeholder=""
				bind:value={$value}
				{...$constraints}
				{...$$restProps}
				{disabled}
				{required}
			/>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
