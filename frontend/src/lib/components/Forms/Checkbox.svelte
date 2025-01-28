<script lang="ts">
	import { SlideToggle, type CssClasses } from '@skeletonlabs/skeleton';
	import { createEventDispatcher } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	export let label: string | undefined = undefined;
	export let field: string;
	export let valuePath = field; // the place where the value is stored in the form. This is useful for nested objects
	export let helpText: string | undefined = undefined;
	// The cachedValue isn't used in the ModelForm because we don't need it yet
	export let cachedValue: boolean | undefined = undefined;
	export let form: SuperForm<Record<string, boolean | undefined>>;
	export let hidden = false;
	export let disabled = false;
	export let checkboxComponent: 'checkbox' | 'switch' = 'checkbox';
	export let classesContainer: CssClasses = '';

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	const dispatch = createEventDispatcher();

	function handleChange() {
		dispatch('change', $value);
	}

	$: if (cachedValue !== undefined) {
		value.set(cachedValue);
	} else {
		cachedValue = $value;
	}

	$: classesHidden = (h: boolean) => (h ? 'hidden' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');
</script>

<div class={classesContainer}>
	<div
		class="flex flex-row space-x-2 items-center {classesHidden(hidden)} {classesDisabled(disabled)}"
	>
		{#if label !== undefined}
			{#if $constraints?.required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
		{/if}
		<div class="control">
			{#if checkboxComponent === 'checkbox'}
				<input
					name={field}
					type="checkbox"
					class="checkbox"
					data-testid="form-input-{field.replaceAll('_', '-')}"
					bind:checked={cachedValue}
					on:change={handleChange}
					{...$constraints}
					{...$$restProps}
					{disabled}
				/>
			{:else if checkboxComponent === 'switch'}
				<SlideToggle
					name={field}
					type="checkbox"
					data-testid="form-input-{field.replaceAll('_', '-')}"
					bind:checked={cachedValue}
					on:change={handleChange}
					{...$constraints}
					{...$$restProps}
					{disabled}
				/>
			{/if}
		</div>
	</div>
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
