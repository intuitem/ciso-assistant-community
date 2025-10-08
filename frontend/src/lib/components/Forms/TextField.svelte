<script lang="ts">
	import { run } from 'svelte/legacy';

	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CssClasses } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		class?: string;
		type?: string;
		classesContainer?: CssClasses;
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		cachedValue?: string | undefined;
		cacheLock?: CacheLock;
		form: any;
		hidden?: boolean;
		disabled?: boolean;
		required?: boolean;
		[key: string]: any;
	}

	let {
		class: _class = '',
		type = 'text',
		classesContainer = '',
		label = $bindable(),
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
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	// Store the display value separately from the actual form value
	let displayValue: string = $state();

	$effect(() => {
		cachedValue = $value;
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) {
			$value = cacheResult;
			if (type === 'datetime-local') {
				displayValue = formatDateForInput($value);
			}
		}
	});

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));

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
	run(() => {
		if (type === 'datetime-local' && $value && !displayValue) {
			displayValue = formatDateForInput($value);
		}
	});
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
				oninput={handleDateTimeChange}
				{...$constraints}
				{...rest}
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
				{...rest}
				{disabled}
				{required}
			/>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500 whitespace-pre-line">{helpText}</p>
	{/if}
</div>
